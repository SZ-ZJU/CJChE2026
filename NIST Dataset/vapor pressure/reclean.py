import pandas as pd
import numpy as np
import re
from pathlib import Path


# =========================================================
# 1. 输入输出文件
# =========================================================
input_file = Path("thermoml_vapor_pressure_Liquid_with_clean_SMILES_no_charged_N.xlsx")
input_sheet = "Data_Clean_SMILES"

output_file = Path("thermoml_vapor_pressure_Liquid_final_n8_T80_noSi.xlsx")


# =========================================================
# 2. 筛选条件
# =========================================================
temp_col = "T_K"

min_points = 8
min_temp_range = 80.0

# 是否删除含 Si 的物质
remove_si = True


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

print("\n原始数据行数:", len(df))
print("原始列名:")
print(list(df.columns))

if temp_col not in df.columns:
    raise ValueError(f"没有找到温度列: {temp_col}")

df[temp_col] = pd.to_numeric(df[temp_col], errors="coerce")


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
# 5. 元素解析，用于判断是否含 Si
# =========================================================
def parse_elements(formula):
    """
    从分子式中提取元素符号。
    例如：
    C6H6Si -> {"C", "H", "Si"}
    CH4O -> {"C", "H", "O"}
    """
    if not is_valid_value(formula):
        return set()

    s = str(formula).strip()
    s = s.replace(" ", "")
    s = s.replace("·", ".")
    s = s.replace("-", "")

    return set(re.findall(r"[A-Z][a-z]?", s))


def material_contains_si(group):
    """
    判断一个物质是否含 Si。
    优先检查 formula，其次检查 pubchem_molecular_formula。
    """
    formula_candidates = []

    for col in ["formula", "pubchem_molecular_formula"]:
        if col in group.columns:
            vals = group[col].dropna().astype(str).str.strip().unique().tolist()
            formula_candidates.extend(vals)

    for formula in formula_candidates:
        elements = parse_elements(formula)
        if "Si" in elements:
            return True

    return False


# =========================================================
# 6. 按物质计算 n_points 和 T_range
# =========================================================
material_rows = []

for material_key, group in df.groupby("material_key", sort=False):
    g = group.copy()
    g_valid_t = g[g[temp_col].notna()].copy()

    n_points_current = len(g_valid_t)

    if n_points_current > 0:
        T_min = g_valid_t[temp_col].min()
        T_max = g_valid_t[temp_col].max()
        T_range = T_max - T_min
    else:
        T_min = np.nan
        T_max = np.nan
        T_range = np.nan

    contains_si = material_contains_si(g)

    remove_reasons = []

    if n_points_current < min_points:
        remove_reasons.append(f"n_points_less_than_{min_points}")

    if pd.isna(T_range) or T_range < min_temp_range:
        remove_reasons.append(f"T_range_less_than_{min_temp_range:g}K")

    if remove_si and contains_si:
        remove_reasons.append("contains_Si")

    if len(remove_reasons) == 0:
        filter_status = "keep"
    else:
        filter_status = "remove"

    row = {
        "material_key": material_key,
        "filter_status": filter_status,
        "remove_reason": "; ".join(remove_reasons),
        "n_points_current": n_points_current,
        "T_min_current": T_min,
        "T_max_current": T_max,
        "T_range_current": T_range,
        "contains_Si": contains_si,
    }

    # 保留一些物质信息
    for col in [
        "compound_name",
        "cas",
        "formula",
        "pubchem_molecular_formula",
        "SMILES",
        "inchikey",
        "pubchem_cid",
        "pubchem_iupac_name",
    ]:
        if col in g.columns:
            row[col] = g[col].iloc[0]

    # 如果原表里有 RSQ，也顺便保留
    for col in [
        "RSQ_P_vs_T",
        "RSQ_lnP_vs_T",
        "RSQ_lnP_vs_invT",
        "slope_P_vs_T",
        "slope_lnP_vs_invT",
    ]:
        if col in g.columns:
            row[col] = g[col].iloc[0]

    material_rows.append(row)


df_material_summary = pd.DataFrame(material_rows)


# =========================================================
# 7. 生成保留和删除数据
# =========================================================
kept_material_keys = df_material_summary.loc[
    df_material_summary["filter_status"] == "keep",
    "material_key"
]

removed_material_keys = df_material_summary.loc[
    df_material_summary["filter_status"] == "remove",
    "material_key"
]

df_kept = df[df["material_key"].isin(kept_material_keys)].copy()
df_removed = df[df["material_key"].isin(removed_material_keys)].copy()

# 合并筛选信息回数据
summary_merge_cols = [
    "material_key",
    "filter_status",
    "remove_reason",
    "n_points_current",
    "T_min_current",
    "T_max_current",
    "T_range_current",
    "contains_Si",
]

df_kept = df_kept.merge(
    df_material_summary[summary_merge_cols],
    on="material_key",
    how="left"
)

df_removed = df_removed.merge(
    df_material_summary[summary_merge_cols],
    on="material_key",
    how="left"
)

df_kept_materials = df_material_summary[
    df_material_summary["filter_status"] == "keep"
].copy()

df_removed_materials = df_material_summary[
    df_material_summary["filter_status"] == "remove"
].copy()


# =========================================================
# 8. 排序
# =========================================================
sort_cols = [c for c in ["material_key", temp_col] if c in df_kept.columns]
if sort_cols:
    df_kept = df_kept.sort_values(sort_cols).reset_index(drop=True)

sort_cols_removed = [c for c in ["material_key", temp_col] if c in df_removed.columns]
if sort_cols_removed:
    df_removed = df_removed.sort_values(sort_cols_removed).reset_index(drop=True)

df_kept_materials = df_kept_materials.sort_values(
    ["T_range_current", "n_points_current"],
    ascending=[False, False]
).reset_index(drop=True)

df_removed_materials = df_removed_materials.sort_values(
    ["remove_reason", "T_range_current", "n_points_current"],
    ascending=[True, False, False]
).reset_index(drop=True)


# =========================================================
# 9. 打印结果
# =========================================================
print("\n========== 最终筛选结果 ==========")
print("筛选前数据行数:", len(df))
print("筛选前物质数:", df["material_key"].nunique())

print("\n保留数据行数:", len(df_kept))
print("保留物质数:", df_kept["material_key"].nunique())

print("\n删除数据行数:", len(df_removed))
print("删除物质数:", df_removed["material_key"].nunique())

print("\n删除原因统计:")
print(df_removed_materials["remove_reason"].value_counts(dropna=False))

if remove_si:
    print("\n含 Si 被删除的物质数:")
    print(int((df_removed_materials["contains_Si"] == True).sum()))


# =========================================================
# 10. 保存 Excel
# =========================================================
run_info = pd.DataFrame([
    {"item": "input_file", "value": str(input_file)},
    {"item": "input_sheet", "value": input_sheet},
    {"item": "output_file", "value": str(output_file)},

    {"item": "min_points", "value": min_points},
    {"item": "min_temp_range_K", "value": min_temp_range},
    {"item": "remove_si", "value": remove_si},

    {"item": "original_rows", "value": len(df)},
    {"item": "original_materials", "value": df["material_key"].nunique()},

    {"item": "kept_rows", "value": len(df_kept)},
    {"item": "kept_materials", "value": df_kept["material_key"].nunique()},

    {"item": "removed_rows", "value": len(df_removed)},
    {"item": "removed_materials", "value": df_removed["material_key"].nunique()},

    {
        "item": "removed_by_n_points_less_than_8",
        "value": int(df_removed_materials["remove_reason"].str.contains("n_points_less_than_8", na=False).sum())
    },
    {
        "item": "removed_by_T_range_less_than_80K",
        "value": int(df_removed_materials["remove_reason"].str.contains("T_range_less_than_80K", na=False).sum())
    },
    {
        "item": "removed_by_contains_Si",
        "value": int((df_removed_materials["contains_Si"] == True).sum())
    },
])

with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_kept.to_excel(writer, sheet_name="Final_Selected_Data", index=False)
    df_kept_materials.to_excel(writer, sheet_name="Final_Materials", index=False)

    df_removed.to_excel(writer, sheet_name="Removed_Rows", index=False)
    df_removed_materials.to_excel(writer, sheet_name="Removed_Materials", index=False)

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
print("最终可用于建模的 sheet: Final_Selected_Data")