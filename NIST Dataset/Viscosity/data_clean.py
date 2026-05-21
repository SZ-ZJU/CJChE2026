import pandas as pd
import numpy as np
from pathlib import Path


# =========================================================
# 1. 输入输出文件
# =========================================================
# 只读取按相态划分后的 viscosity 文件中的 Liquid sheet
input_file = Path("thermoml_viscosity_by_phase.xlsx")
input_sheet = "Liquid"

output_file = Path("thermoml_viscosity_Liquid_deduplicated_min3_Tgt30.xlsx")


# =========================================================
# 2. 基本设置
# =========================================================
temp_col = "T_K"
viscosity_col = "Viscosity_Pa_s"
ln_viscosity_col = "lnViscosity_Pa_s"

# 如果表里有 P_kPa，就额外统计；没有也不影响
pressure_col = "P_kPa"

# 温度去重精度
temp_round_decimals = 6

# 每个物质去重后至少需要几个温度点
min_points_per_material = 3

# 每个物质去重后温度区间必须严格大于多少 K
min_temp_range = 30.0

# 是否删除非正黏度
# 因为后面如果使用 ln(viscosity)，viscosity <= 0 没有意义
remove_non_positive_viscosity = True


# =========================================================
# 3. 读取数据
# =========================================================
if not input_file.exists():
    raise FileNotFoundError(f"没有找到输入文件: {input_file}")

xls = pd.ExcelFile(input_file)

print("输入文件包含的 sheet:")
print(xls.sheet_names)

if input_sheet not in xls.sheet_names:
    raise ValueError(
        f"没有找到 sheet: {input_sheet}\n"
        f"当前文件中可用的 sheet 为: {xls.sheet_names}"
    )

df = pd.read_excel(input_file, sheet_name=input_sheet)

print("\n读取 sheet:", input_sheet)
print("原始数据点数:", len(df))
print("原始列名:")
print(list(df.columns))

if temp_col not in df.columns:
    raise ValueError(f"没有找到温度列: {temp_col}")

if viscosity_col not in df.columns:
    raise ValueError(f"没有找到黏度列: {viscosity_col}")

if ln_viscosity_col not in df.columns:
    print(f"提示：没有找到 {ln_viscosity_col}，后面会根据 {viscosity_col} 自动生成。")


# =========================================================
# 4. 自动生成 material_key
# =========================================================
def is_valid_value(x):
    if pd.isna(x):
        return False

    s = str(x).strip()

    if s == "":
        return False

    if s.lower() in ["nan", "none", "null", "待定"]:
        return False

    return True


def build_material_key(row):
    """
    优先级：
    1. inchikey
    2. cas
    3. compound_name
    4. formula
    """
    for col in ["inchikey", "cas", "compound_name", "formula"]:
        if col in row.index and is_valid_value(row[col]):
            return f"{col}:{str(row[col]).strip()}"

    return "unknown_material"


if "material_key" not in df.columns:
    df["material_key"] = df.apply(build_material_key, axis=1)


# =========================================================
# 5. 数值化并构造温度去重键
# =========================================================
df[temp_col] = pd.to_numeric(df[temp_col], errors="coerce")
df[viscosity_col] = pd.to_numeric(df[viscosity_col], errors="coerce")

if pressure_col in df.columns:
    df[pressure_col] = pd.to_numeric(df[pressure_col], errors="coerce")

# 删除 T 或 viscosity 为空的数据
before_drop_na = len(df)

df = df[
    df[temp_col].notna()
    & df[viscosity_col].notna()
].copy()

print("\n删除 T 或 viscosity 为空的数据点数:", before_drop_na - len(df))

# 删除非正黏度
if remove_non_positive_viscosity:
    before_drop_non_positive = len(df)

    df = df[df[viscosity_col] > 0].copy()

    print("删除 viscosity <= 0 的数据点数:", before_drop_non_positive - len(df))

# 自动生成 lnViscosity_Pa_s
df[ln_viscosity_col] = np.log(df[viscosity_col])

df["_original_order"] = np.arange(len(df))
df["_T_round"] = df[temp_col].round(temp_round_decimals)


# =========================================================
# 6. 删除同一物质下重复温度点
# 规则：同一个 material_key + T_round，只保留第一行
# =========================================================
duplicate_mask = df.duplicated(
    subset=["material_key", "_T_round"],
    keep="first"
)

df_removed_duplicates = df.loc[duplicate_mask].copy()
df_dedup = df.loc[~duplicate_mask].copy()

print("\n========== 温度重复去重结果 ==========")
print("去重后数据点数:", len(df_dedup))
print("删除重复温度点数:", len(df_removed_duplicates))
print("去重后物质数:", df_dedup["material_key"].nunique())


# =========================================================
# 7. 删除去重后数据点数少于 min_points_per_material 的物质
# =========================================================
material_counts = (
    df_dedup
    .groupby("material_key")
    .size()
    .reset_index(name="n_points_after_dedup")
)

valid_material_keys_min_points = material_counts.loc[
    material_counts["n_points_after_dedup"] >= min_points_per_material,
    "material_key"
]

too_few_material_keys = material_counts.loc[
    material_counts["n_points_after_dedup"] < min_points_per_material,
    "material_key"
]

df_removed_too_few_points = df_dedup[
    df_dedup["material_key"].isin(too_few_material_keys)
].copy()

df_removed_too_few_points["remove_reason"] = (
    f"points_less_than_{min_points_per_material}_after_dedup"
)

df_after_min_points = df_dedup[
    df_dedup["material_key"].isin(valid_material_keys_min_points)
].copy()

print("\n========== 数据点数筛选结果 ==========")
print(f"删除去重后点数 < {min_points_per_material} 的物质数:", len(too_few_material_keys))
print("删除对应数据点数:", len(df_removed_too_few_points))
print("点数筛选后保留数据点数:", len(df_after_min_points))
print("点数筛选后保留物质数:", df_after_min_points["material_key"].nunique())


# =========================================================
# 8. 删除温度区间不大于 min_temp_range 的物质
# 要求：T_max - T_min > 30 K
# =========================================================
temp_range_rows = []

for material_key, group in df_after_min_points.groupby("material_key", sort=False):
    temps = pd.to_numeric(group[temp_col], errors="coerce").values.astype(float)
    viscosities = pd.to_numeric(group[viscosity_col], errors="coerce").values.astype(float)
    ln_viscosities = pd.to_numeric(group[ln_viscosity_col], errors="coerce").values.astype(float)

    if np.all(np.isnan(temps)):
        T_min = np.nan
        T_max = np.nan
        T_range = np.nan
    else:
        T_min = np.nanmin(temps)
        T_max = np.nanmax(temps)
        T_range = T_max - T_min

    row = {
        "material_key": material_key,
        "n_points_after_dedup_and_min3": len(group),
        "T_min": T_min,
        "T_max": T_max,
        "T_range": T_range,
        "Viscosity_min_Pa_s": (
            np.nanmin(viscosities) if not np.all(np.isnan(viscosities)) else np.nan
        ),
        "Viscosity_max_Pa_s": (
            np.nanmax(viscosities) if not np.all(np.isnan(viscosities)) else np.nan
        ),
        "Viscosity_range_Pa_s": (
            np.nanmax(viscosities) - np.nanmin(viscosities)
            if not np.all(np.isnan(viscosities))
            else np.nan
        ),
        "lnViscosity_min_Pa_s": (
            np.nanmin(ln_viscosities) if not np.all(np.isnan(ln_viscosities)) else np.nan
        ),
        "lnViscosity_max_Pa_s": (
            np.nanmax(ln_viscosities) if not np.all(np.isnan(ln_viscosities)) else np.nan
        ),
        "lnViscosity_range_Pa_s": (
            np.nanmax(ln_viscosities) - np.nanmin(ln_viscosities)
            if not np.all(np.isnan(ln_viscosities))
            else np.nan
        ),
    }

    if pressure_col in group.columns:
        ps = pd.to_numeric(group[pressure_col], errors="coerce").values.astype(float)
        row["P_min_kPa"] = np.nanmin(ps) if not np.all(np.isnan(ps)) else np.nan
        row["P_max_kPa"] = np.nanmax(ps) if not np.all(np.isnan(ps)) else np.nan

    for col in [
        "compound_name",
        "cas",
        "formula",
        "inchikey",
        "smiles",
        "phase",
        "property_name",
        "property_unit",
        "method",
        "doi",
        "year",
        "journal"
    ]:
        if col in group.columns:
            row[col] = group[col].iloc[0]

    temp_range_rows.append(row)

df_temp_range_summary = pd.DataFrame(temp_range_rows)

valid_temp_range_keys = df_temp_range_summary.loc[
    df_temp_range_summary["T_range"] > min_temp_range,
    "material_key"
]

small_temp_range_keys = df_temp_range_summary.loc[
    (df_temp_range_summary["T_range"].isna()) |
    (df_temp_range_summary["T_range"] <= min_temp_range),
    "material_key"
]

df_removed_small_temp_range = df_after_min_points[
    df_after_min_points["material_key"].isin(small_temp_range_keys)
].copy()

df_removed_small_temp_range["remove_reason"] = (
    f"temperature_range_not_greater_than_{min_temp_range:g}K"
)

df_removed_small_temp_range_summary = df_temp_range_summary[
    df_temp_range_summary["material_key"].isin(small_temp_range_keys)
].copy()

df_removed_small_temp_range_summary["remove_reason"] = (
    f"temperature_range_not_greater_than_{min_temp_range:g}K"
)

df_final = df_after_min_points[
    df_after_min_points["material_key"].isin(valid_temp_range_keys)
].copy()

print("\n========== 温度区间筛选结果 ==========")
print(f"删除温度区间 <= {min_temp_range:g} K 的物质数:", len(small_temp_range_keys))
print("删除对应数据点数:", len(df_removed_small_temp_range))
print("最终保留数据点数:", len(df_final))
print("最终保留物质数:", df_final["material_key"].nunique())


# =========================================================
# 9. 物质级别汇总
# =========================================================
def build_material_summary(df_in):
    summary_rows = []

    if len(df_in) == 0:
        return pd.DataFrame()

    for material_key, group in df_in.groupby("material_key", sort=False):
        temps = pd.to_numeric(group[temp_col], errors="coerce").values.astype(float)
        viscosities = pd.to_numeric(group[viscosity_col], errors="coerce").values.astype(float)
        ln_viscosities = pd.to_numeric(group[ln_viscosity_col], errors="coerce").values.astype(float)

        row = {
            "material_key": material_key,
            "n_points": len(group),
            "T_min": np.nanmin(temps),
            "T_max": np.nanmax(temps),
            "T_range": np.nanmax(temps) - np.nanmin(temps),
            "Viscosity_min_Pa_s": np.nanmin(viscosities),
            "Viscosity_max_Pa_s": np.nanmax(viscosities),
            "Viscosity_range_Pa_s": np.nanmax(viscosities) - np.nanmin(viscosities),
            "lnViscosity_min_Pa_s": np.nanmin(ln_viscosities),
            "lnViscosity_max_Pa_s": np.nanmax(ln_viscosities),
            "lnViscosity_range_Pa_s": np.nanmax(ln_viscosities) - np.nanmin(ln_viscosities),
        }

        if pressure_col in group.columns:
            ps = pd.to_numeric(group[pressure_col], errors="coerce").values.astype(float)
            row["P_min_kPa"] = np.nanmin(ps) if not np.all(np.isnan(ps)) else np.nan
            row["P_max_kPa"] = np.nanmax(ps) if not np.all(np.isnan(ps)) else np.nan

        for col in [
            "compound_name",
            "cas",
            "formula",
            "inchikey",
            "smiles",
            "phase",
            "property_name",
            "property_unit",
            "method",
            "doi",
            "year",
            "journal"
        ]:
            if col in group.columns:
                row[col] = group[col].iloc[0]

        summary_rows.append(row)

    return pd.DataFrame(summary_rows)


df_material_summary = build_material_summary(df_final)


# =========================================================
# 10. 重复温度点统计
# =========================================================
duplicate_summary = (
    df_removed_duplicates
    .groupby("material_key")
    .size()
    .reset_index(name="removed_duplicate_temperature_rows")
)

if len(duplicate_summary) > 0:
    material_info_cols = [
        "material_key",
        "compound_name",
        "cas",
        "formula",
        "inchikey",
        "smiles",
        "phase",
        "property_name"
    ]
    material_info_cols = [c for c in material_info_cols if c in df.columns]

    material_info = (
        df[material_info_cols]
        .drop_duplicates(subset=["material_key"])
        .copy()
    )

    duplicate_summary = duplicate_summary.merge(
        material_info,
        on="material_key",
        how="left"
    )


# =========================================================
# 11. 数据点不足物质统计
# =========================================================
too_few_summary = (
    material_counts[
        material_counts["n_points_after_dedup"] < min_points_per_material
    ]
    .copy()
    .reset_index(drop=True)
)

if len(too_few_summary) > 0:
    info_rows = []

    for material_key, group in df_removed_too_few_points.groupby("material_key", sort=False):
        row = {
            "material_key": material_key,
            "n_points_after_dedup": len(group),
            "remove_reason": f"points_less_than_{min_points_per_material}_after_dedup",
        }

        for col in [
            "compound_name",
            "cas",
            "formula",
            "inchikey",
            "smiles",
            "phase",
            "property_name"
        ]:
            if col in group.columns:
                row[col] = group[col].iloc[0]

        temps = pd.to_numeric(group[temp_col], errors="coerce").values.astype(float)
        viscosities = pd.to_numeric(group[viscosity_col], errors="coerce").values.astype(float)
        ln_viscosities = pd.to_numeric(group[ln_viscosity_col], errors="coerce").values.astype(float)

        row["T_min"] = np.nanmin(temps) if not np.all(np.isnan(temps)) else np.nan
        row["T_max"] = np.nanmax(temps) if not np.all(np.isnan(temps)) else np.nan
        row["T_range"] = (
            np.nanmax(temps) - np.nanmin(temps)
            if not np.all(np.isnan(temps))
            else np.nan
        )

        row["Viscosity_min_Pa_s"] = (
            np.nanmin(viscosities) if not np.all(np.isnan(viscosities)) else np.nan
        )
        row["Viscosity_max_Pa_s"] = (
            np.nanmax(viscosities) if not np.all(np.isnan(viscosities)) else np.nan
        )
        row["lnViscosity_min_Pa_s"] = (
            np.nanmin(ln_viscosities) if not np.all(np.isnan(ln_viscosities)) else np.nan
        )
        row["lnViscosity_max_Pa_s"] = (
            np.nanmax(ln_viscosities) if not np.all(np.isnan(ln_viscosities)) else np.nan
        )

        if pressure_col in group.columns:
            ps = pd.to_numeric(group[pressure_col], errors="coerce").values.astype(float)
            row["P_min_kPa"] = np.nanmin(ps) if not np.all(np.isnan(ps)) else np.nan
            row["P_max_kPa"] = np.nanmax(ps) if not np.all(np.isnan(ps)) else np.nan

        info_rows.append(row)

    too_few_summary = pd.DataFrame(info_rows)


# =========================================================
# 12. 删除临时列
# =========================================================
for temp_internal_col in ["_original_order", "_T_round"]:
    for table in [
        df_final,
        df_removed_duplicates,
        df_removed_too_few_points,
        df_removed_small_temp_range,
    ]:
        if temp_internal_col in table.columns:
            table.drop(columns=[temp_internal_col], inplace=True)


# =========================================================
# 13. 保存结果
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_final.to_excel(writer, sheet_name="Viscosity_Liquid_Final", index=False)
    df_material_summary.to_excel(writer, sheet_name="Material_Summary", index=False)

    df_removed_duplicates.to_excel(writer, sheet_name="Removed_Duplicate_Rows", index=False)
    duplicate_summary.to_excel(writer, sheet_name="Duplicate_Summary", index=False)

    df_removed_too_few_points.to_excel(writer, sheet_name="Removed_LessThan3_Rows", index=False)
    too_few_summary.to_excel(writer, sheet_name="Removed_LessThan3_Materials", index=False)

    df_removed_small_temp_range.to_excel(writer, sheet_name="Removed_TRange_Rows", index=False)
    df_removed_small_temp_range_summary.to_excel(writer, sheet_name="Removed_TRange_Materials", index=False)

    run_info = pd.DataFrame([
        {"item": "input_file", "value": str(input_file)},
        {"item": "input_sheet", "value": str(input_sheet)},
        {"item": "output_file", "value": str(output_file)},
        {"item": "temperature_col", "value": temp_col},
        {"item": "viscosity_col", "value": viscosity_col},
        {"item": "ln_viscosity_col", "value": ln_viscosity_col},
        {"item": "temp_round_decimals", "value": temp_round_decimals},
        {"item": "min_points_per_material_after_dedup", "value": min_points_per_material},
        {"item": "min_temp_range_K_strictly_greater_than", "value": min_temp_range},
        {"item": "remove_non_positive_viscosity", "value": remove_non_positive_viscosity},
        {"item": "original_rows_after_basic_numeric_filter", "value": len(df)},
        {"item": "rows_after_temperature_dedup", "value": len(df_dedup)},
        {"item": "removed_duplicate_rows", "value": len(df_removed_duplicates)},
        {"item": "removed_less_than_3_rows", "value": len(df_removed_too_few_points)},
        {"item": "removed_less_than_3_materials", "value": len(too_few_material_keys)},
        {"item": "removed_small_temp_range_rows", "value": len(df_removed_small_temp_range)},
        {"item": "removed_small_temp_range_materials", "value": len(small_temp_range_keys)},
        {"item": "final_rows", "value": len(df_final)},
        {"item": "final_materials", "value": df_final["material_key"].nunique()},
    ])

    run_info.to_excel(writer, sheet_name="Run_Info", index=False)

    number_format = "0.0000000000"

    for sheet_name in writer.sheets:
        ws = writer.sheets[sheet_name]

        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, float):
                    cell.number_format = number_format

        for col_cells in ws.columns:
            max_length = 0
            col_letter = col_cells[0].column_letter

            for cell in col_cells:
                if cell.value is not None:
                    max_length = max(max_length, len(str(cell.value)))

            ws.column_dimensions[col_letter].width = min(max_length + 2, 35)


print("\n保存完成:", output_file)
print("最终主表 sheet 名: Viscosity_Liquid_Final")