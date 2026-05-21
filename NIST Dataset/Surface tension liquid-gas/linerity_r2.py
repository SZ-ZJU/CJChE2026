# -*- coding: utf-8 -*-
"""
Surface tension liquid-gas 线性度分析脚本

输入：
    thermoml_surface_tension_liquid_gas_Liquid_remove_dupT_materials_min3_Tgt20.xlsx
    sheet: Surface_Liquid_Final

输出：
    thermoml_surface_tension_liquid_gas_Liquid_remove_dupT_materials_min3_Tgt20_with_RSQ.xlsx

功能：
    1. 读取已经清洗后的 Surface tension liquid-gas 数据
    2. 再次检查 material_key + T_round 是否重复
    3. 如果仍存在重复温度点，则删除该物质全部数据
    4. 对每个物质计算线性度：
       - SurfaceTension_N_m vs T_K
       - SurfaceTension_N_m vs 1/T_K
       - ln(SurfaceTension_N_m) vs T_K
    5. 输出：
       - Data_With_RSQ
       - Material_RSQ
       - Low_RSQ_Materials
       - Positive_Slope_Surface_T
       - Negative_Slope_Surface_T
       - DupTemp_Rows_Before_RSQ
       - Removed_DupTemp_RSQ
       - Summary
"""

import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score


# =========================
# 1. 输入输出文件
# =========================

input_file = Path("thermoml_surface_tension_liquid_gas_Liquid_remove_dupT_materials_min3_Tgt20.xlsx")
input_sheet = "Surface_Liquid_Final"

output_file = Path("thermoml_surface_tension_liquid_gas_Liquid_remove_dupT_materials_min3_Tgt20_with_RSQ.xlsx")


# =========================
# 2. 基础列名与参数
# =========================

temp_col = "T_K"
surface_col = "SurfaceTension_N_m"
ln_surface_col = "lnSurfaceTension_N_m"

pressure_col = "P_kPa"

# R² 阈值，低于该值的物质会单独输出
rsq_threshold = 0.95

# 是否删除非正表面张力
remove_non_positive_surface_tension = True

# 温度重复判断精度，需要和清洗脚本保持一致
# 你前面的 Surface tension 清洗脚本里使用的是 0.1 K 精度，所以这里设为 1。
temp_round_decimals = 1

# 线性度计算前是否再次删除存在重复温度的整组物质
remove_duplicate_temperature_materials_before_rsq = True


# =========================
# 3. 读取数据
# =========================

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

if surface_col not in df.columns:
    if "property_value" in df.columns:
        print(f"警告：没有找到 {surface_col}，将使用 property_value 作为表面张力列。")
        df[surface_col] = df["property_value"]
    else:
        raise ValueError(f"没有找到表面张力列: {surface_col}，且没有 property_value 可替代。")


# =========================
# 4. 数值化与基础过滤
# =========================

df[temp_col] = pd.to_numeric(df[temp_col], errors="coerce")
df[surface_col] = pd.to_numeric(df[surface_col], errors="coerce")

if pressure_col in df.columns:
    df[pressure_col] = pd.to_numeric(df[pressure_col], errors="coerce")

before_drop = len(df)

df = df[
    df[temp_col].notna()
    & df[surface_col].notna()
].copy()

print("\n删除 T 或 SurfaceTension 缺失的数据点数:", before_drop - len(df))

if remove_non_positive_surface_tension:
    before_drop_non_positive = len(df)

    df = df[df[surface_col] > 0].copy()

    print("删除 SurfaceTension <= 0 的数据点数:", before_drop_non_positive - len(df))


# =========================
# 5. 如果没有 material_key，就自动生成
# =========================

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
    material_key 优先级：
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


# =========================
# 6. 线性度计算前重复温度检查
# =========================

df["_T_round"] = df[temp_col].round(temp_round_decimals)

dup_temp_mask = df.duplicated(
    subset=["material_key", "_T_round"],
    keep=False
)

df_dup_temp_related_rows = df.loc[dup_temp_mask].copy()

dup_temp_material_keys = (
    df_dup_temp_related_rows["material_key"]
    .dropna()
    .unique()
)

df_removed_dup_temp_materials_in_rsq = df[
    df["material_key"].isin(dup_temp_material_keys)
].copy()

if len(df_removed_dup_temp_materials_in_rsq) > 0:
    df_removed_dup_temp_materials_in_rsq["remove_reason"] = (
        "material_has_duplicate_temperature_points_before_rsq"
    )

print("\n========== 线性度计算前重复温度检查 ==========")
print("重复温度相关行数:", len(df_dup_temp_related_rows))
print("存在重复温度点的物质数:", len(dup_temp_material_keys))
print("涉及的全部数据点数:", len(df_removed_dup_temp_materials_in_rsq))

if remove_duplicate_temperature_materials_before_rsq:
    before_remove_dup_temp_materials = len(df)

    df = df[
        ~df["material_key"].isin(dup_temp_material_keys)
    ].copy()

    print("已删除存在重复温度点的物质全部数据点数:", before_remove_dup_temp_materials - len(df))
    print("删除后用于 RSQ 的数据点数:", len(df))
    print("删除后用于 RSQ 的物质数:", df["material_key"].nunique())
else:
    print("未在线性度脚本中删除重复温度物质，仅输出检查表。")


# =========================
# 7. 生成 1/T 和 ln(SurfaceTension)
# =========================

df["InvT_1_per_K"] = 1.0 / df[temp_col]
df[ln_surface_col] = np.log(df[surface_col])


# =========================
# 8. 单个线性拟合函数
# =========================

def fit_linear_rsq(g, x_col, y_col):
    """
    对单个物质的数据做 y = slope * x + intercept 线性拟合。
    """
    g_fit = g.dropna(subset=[x_col, y_col]).copy()

    if len(g_fit) < 2:
        return {
            "n_points": len(g_fit),
            "RSQ": np.nan,
            "slope": np.nan,
            "intercept": np.nan,
            "fit_status": "less_than_2_points",
        }

    g_fit = g_fit.sort_values(x_col)

    X = g_fit[[x_col]].values
    y = g_fit[y_col].values

    model = LinearRegression()
    model.fit(X, y)

    y_pred = model.predict(X)

    return {
        "n_points": len(g_fit),
        "RSQ": r2_score(y, y_pred),
        "slope": model.coef_[0],
        "intercept": model.intercept_,
        "fit_status": "ok",
    }


def first_or_none(g, col):
    if col in g.columns and len(g) > 0:
        return g[col].iloc[0]
    return None


# =========================
# 9. 计算每个物质的线性拟合 R²
# =========================

summary_rows = []

for material_key, group in df.groupby("material_key", sort=False):
    g = group.copy()

    g = g.dropna(subset=[temp_col, surface_col, "InvT_1_per_K", ln_surface_col])

    compound_name = first_or_none(g, "compound_name")
    cas = first_or_none(g, "cas")
    formula = first_or_none(g, "formula")
    smiles = first_or_none(g, "smiles")
    inchikey = first_or_none(g, "inchikey")
    phase = first_or_none(g, "phase")
    property_name = first_or_none(g, "property_name")
    property_unit = first_or_none(g, "property_unit")
    method = first_or_none(g, "method")
    doi = first_or_none(g, "doi")
    year = first_or_none(g, "year")
    journal = first_or_none(g, "journal")
    source_file = first_or_none(g, "source_file")

    if len(g) < 2:
        summary_rows.append({
            "material_key": material_key,
            "compound_name": compound_name,
            "cas": cas,
            "formula": formula,
            "inchikey": inchikey,
            "smiles": smiles,
            "phase": phase,
            "property_name": property_name,
            "property_unit": property_unit,
            "method": method,
            "doi": doi,
            "year": year,
            "journal": journal,
            "source_file": source_file,

            "n_points": len(g),
            "T_min": np.nan,
            "T_max": np.nan,
            "T_range": np.nan,

            "SurfaceTension_min_N_m": np.nan,
            "SurfaceTension_max_N_m": np.nan,
            "SurfaceTension_range_N_m": np.nan,

            "lnSurface_min": np.nan,
            "lnSurface_max": np.nan,
            "lnSurface_range": np.nan,

            "RSQ_Surface_vs_T": np.nan,
            "slope_Surface_vs_T": np.nan,
            "intercept_Surface_vs_T": np.nan,

            "RSQ_Surface_vs_invT": np.nan,
            "slope_Surface_vs_invT": np.nan,
            "intercept_Surface_vs_invT": np.nan,

            "RSQ_lnSurface_vs_T": np.nan,
            "slope_lnSurface_vs_T": np.nan,
            "intercept_lnSurface_vs_T": np.nan,

            "fit_status": "less_than_2_points",
            "slope_direction_Surface_vs_T": "not_available",
        })
        continue

    g = g.sort_values(temp_col)

    # 1. SurfaceTension_N_m vs T_K
    # 主线性度指标
    fit_surface_T = fit_linear_rsq(g, temp_col, surface_col)

    # 2. SurfaceTension_N_m vs 1/T_K
    fit_surface_invT = fit_linear_rsq(g, "InvT_1_per_K", surface_col)

    # 3. ln(SurfaceTension_N_m) vs T_K
    fit_ln_surface_T = fit_linear_rsq(g, temp_col, ln_surface_col)

    row = {
        "material_key": material_key,
        "compound_name": compound_name,
        "cas": cas,
        "formula": formula,
        "inchikey": inchikey,
        "smiles": smiles,
        "phase": phase,
        "property_name": property_name,
        "property_unit": property_unit,
        "method": method,
        "doi": doi,
        "year": year,
        "journal": journal,
        "source_file": source_file,

        "n_points": len(g),

        "T_min": g[temp_col].min(),
        "T_max": g[temp_col].max(),
        "T_range": g[temp_col].max() - g[temp_col].min(),

        "SurfaceTension_min_N_m": g[surface_col].min(),
        "SurfaceTension_max_N_m": g[surface_col].max(),
        "SurfaceTension_range_N_m": g[surface_col].max() - g[surface_col].min(),

        "lnSurface_min": g[ln_surface_col].min(),
        "lnSurface_max": g[ln_surface_col].max(),
        "lnSurface_range": g[ln_surface_col].max() - g[ln_surface_col].min(),

        "RSQ_Surface_vs_T": fit_surface_T["RSQ"],
        "slope_Surface_vs_T": fit_surface_T["slope"],
        "intercept_Surface_vs_T": fit_surface_T["intercept"],

        "RSQ_Surface_vs_invT": fit_surface_invT["RSQ"],
        "slope_Surface_vs_invT": fit_surface_invT["slope"],
        "intercept_Surface_vs_invT": fit_surface_invT["intercept"],

        "RSQ_lnSurface_vs_T": fit_ln_surface_T["RSQ"],
        "slope_lnSurface_vs_T": fit_ln_surface_T["slope"],
        "intercept_lnSurface_vs_T": fit_ln_surface_T["intercept"],

        "fit_status": "ok",
    }

    if "P_kPa" in g.columns:
        row["P_min_kPa"] = g["P_kPa"].min()
        row["P_max_kPa"] = g["P_kPa"].max()

    # 一般情况下，液体表面张力随温度升高下降。
    if fit_surface_T["slope"] < 0:
        row["slope_direction_Surface_vs_T"] = "surface_tension_decreases_with_temperature"
    elif fit_surface_T["slope"] > 0:
        row["slope_direction_Surface_vs_T"] = "surface_tension_increases_with_temperature"
    else:
        row["slope_direction_Surface_vs_T"] = "zero_slope"

    summary_rows.append(row)


df_rsq = pd.DataFrame(summary_rows)

if len(df_rsq) > 0:
    df_rsq = df_rsq.sort_values(
        "RSQ_Surface_vs_T",
        ascending=True,
        na_position="last"
    )


# =========================
# 10. 把 RSQ 合并回数据点表
# =========================

merge_cols = [
    "material_key",

    "RSQ_Surface_vs_T",
    "slope_Surface_vs_T",
    "intercept_Surface_vs_T",

    "RSQ_Surface_vs_invT",
    "slope_Surface_vs_invT",
    "intercept_Surface_vs_invT",

    "RSQ_lnSurface_vs_T",
    "slope_lnSurface_vs_T",
    "intercept_lnSurface_vs_T",

    "fit_status",
    "slope_direction_Surface_vs_T",
]

merge_cols = [c for c in merge_cols if c in df_rsq.columns]

df_with_rsq = df.merge(
    df_rsq[merge_cols],
    on="material_key",
    how="left"
)


# =========================
# 11. 筛选低 R² 和斜率异常物质
# =========================

df_low_rsq = df_rsq[
    (df_rsq["fit_status"] == "ok")
    & (df_rsq["RSQ_Surface_vs_T"] < rsq_threshold)
].copy()

df_positive_slope_surface_T = df_rsq[
    (df_rsq["fit_status"] == "ok")
    & (df_rsq["slope_Surface_vs_T"] > 0)
].copy()

df_negative_slope_surface_T = df_rsq[
    (df_rsq["fit_status"] == "ok")
    & (df_rsq["slope_Surface_vs_T"] < 0)
].copy()


# =========================
# 12. 总体统计
# =========================

valid_rsq = df_rsq[
    (df_rsq["fit_status"] == "ok")
    & (df_rsq["RSQ_Surface_vs_T"].notna())
].copy()

summary = pd.DataFrame([
    {"item": "input_file", "value": str(input_file)},
    {"item": "input_sheet", "value": input_sheet},
    {"item": "output_file", "value": str(output_file)},

    {"item": "temp_col", "value": temp_col},
    {"item": "surface_col", "value": surface_col},
    {"item": "ln_surface_col", "value": ln_surface_col},
    {"item": "main_rsq_used", "value": "RSQ_Surface_vs_T"},

    {"item": "temp_round_decimals", "value": temp_round_decimals},
    {"item": "remove_non_positive_surface_tension", "value": remove_non_positive_surface_tension},
    {"item": "remove_duplicate_temperature_materials_before_rsq", "value": remove_duplicate_temperature_materials_before_rsq},

    {"item": "duplicate_temperature_related_rows_before_rsq", "value": len(df_dup_temp_related_rows)},
    {"item": "duplicate_temperature_materials_before_rsq", "value": len(dup_temp_material_keys)},
    {"item": "removed_duplicate_temperature_material_rows_before_rsq", "value": len(df_removed_dup_temp_materials_in_rsq)},

    {"item": "n_rows_used_for_rsq", "value": len(df)},
    {"item": "n_materials_total_used_for_rsq", "value": df["material_key"].nunique() if len(df) > 0 else 0},
    {"item": "n_materials_valid_rsq", "value": len(valid_rsq)},
    {"item": "rsq_threshold", "value": rsq_threshold},

    {"item": "n_low_rsq_materials_Surface_vs_T", "value": len(df_low_rsq)},
    {"item": "n_positive_slope_Surface_vs_T_materials", "value": len(df_positive_slope_surface_T)},
    {"item": "n_negative_slope_Surface_vs_T_materials", "value": len(df_negative_slope_surface_T)},

    {"item": "n_RSQ_Surface_vs_T_ge_0.99", "value": int((valid_rsq["RSQ_Surface_vs_T"] >= 0.99).sum()) if len(valid_rsq) > 0 else 0},
    {"item": "n_RSQ_Surface_vs_T_ge_0.95", "value": int((valid_rsq["RSQ_Surface_vs_T"] >= 0.95).sum()) if len(valid_rsq) > 0 else 0},
    {"item": "n_RSQ_Surface_vs_T_lt_0.95", "value": int((valid_rsq["RSQ_Surface_vs_T"] < 0.95).sum()) if len(valid_rsq) > 0 else 0},

    {"item": "RSQ_Surface_vs_T_mean", "value": valid_rsq["RSQ_Surface_vs_T"].mean() if len(valid_rsq) > 0 else np.nan},
    {"item": "RSQ_Surface_vs_T_median", "value": valid_rsq["RSQ_Surface_vs_T"].median() if len(valid_rsq) > 0 else np.nan},
    {"item": "RSQ_Surface_vs_T_min", "value": valid_rsq["RSQ_Surface_vs_T"].min() if len(valid_rsq) > 0 else np.nan},
    {"item": "RSQ_Surface_vs_T_max", "value": valid_rsq["RSQ_Surface_vs_T"].max() if len(valid_rsq) > 0 else np.nan},

    {"item": "RSQ_Surface_vs_invT_mean", "value": valid_rsq["RSQ_Surface_vs_invT"].mean() if len(valid_rsq) > 0 else np.nan},
    {"item": "RSQ_Surface_vs_invT_median", "value": valid_rsq["RSQ_Surface_vs_invT"].median() if len(valid_rsq) > 0 else np.nan},
    {"item": "RSQ_Surface_vs_invT_min", "value": valid_rsq["RSQ_Surface_vs_invT"].min() if len(valid_rsq) > 0 else np.nan},
    {"item": "RSQ_Surface_vs_invT_max", "value": valid_rsq["RSQ_Surface_vs_invT"].max() if len(valid_rsq) > 0 else np.nan},

    {"item": "RSQ_lnSurface_vs_T_mean", "value": valid_rsq["RSQ_lnSurface_vs_T"].mean() if len(valid_rsq) > 0 else np.nan},
    {"item": "RSQ_lnSurface_vs_T_median", "value": valid_rsq["RSQ_lnSurface_vs_T"].median() if len(valid_rsq) > 0 else np.nan},
    {"item": "RSQ_lnSurface_vs_T_min", "value": valid_rsq["RSQ_lnSurface_vs_T"].min() if len(valid_rsq) > 0 else np.nan},
    {"item": "RSQ_lnSurface_vs_T_max", "value": valid_rsq["RSQ_lnSurface_vs_T"].max() if len(valid_rsq) > 0 else np.nan},

    {"item": "slope_Surface_vs_T_mean", "value": valid_rsq["slope_Surface_vs_T"].mean() if len(valid_rsq) > 0 else np.nan},
    {"item": "slope_Surface_vs_T_median", "value": valid_rsq["slope_Surface_vs_T"].median() if len(valid_rsq) > 0 else np.nan},
    {"item": "slope_Surface_vs_T_min", "value": valid_rsq["slope_Surface_vs_T"].min() if len(valid_rsq) > 0 else np.nan},
    {"item": "slope_Surface_vs_T_max", "value": valid_rsq["slope_Surface_vs_T"].max() if len(valid_rsq) > 0 else np.nan},
])


# =========================
# 13. 保存 Excel
# =========================

for table in [
    df_with_rsq,
    df_rsq,
    df_low_rsq,
    df_positive_slope_surface_T,
    df_negative_slope_surface_T,
    df_dup_temp_related_rows,
    df_removed_dup_temp_materials_in_rsq,
]:
    for c in ["_T_round"]:
        if c in table.columns:
            table.drop(columns=[c], inplace=True)

with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_with_rsq.to_excel(writer, sheet_name="Data_With_RSQ", index=False)
    df_rsq.to_excel(writer, sheet_name="Material_RSQ", index=False)
    df_low_rsq.to_excel(writer, sheet_name="Low_RSQ_Materials", index=False)

    df_positive_slope_surface_T.to_excel(
        writer,
        sheet_name="Positive_Slope_Surface_T",
        index=False
    )

    df_negative_slope_surface_T.to_excel(
        writer,
        sheet_name="Negative_Slope_Surface_T",
        index=False
    )

    df_dup_temp_related_rows.to_excel(
        writer,
        sheet_name="DupTemp_Rows_Before_RSQ",
        index=False
    )

    df_removed_dup_temp_materials_in_rsq.to_excel(
        writer,
        sheet_name="Removed_DupTemp_RSQ",
        index=False
    )

    summary.to_excel(writer, sheet_name="Summary", index=False)

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


# =========================
# 14. 控制台输出
# =========================

print("\n保存完成:", output_file)

print("\n========== RSQ 数据概况 ==========")
print("用于 RSQ 的数据点数:", len(df))
print("用于 RSQ 的物质数量:", df["material_key"].nunique() if len(df) > 0 else 0)
print("有效 RSQ 物质数量:", len(valid_rsq))

print("\n========== 重复温度检查 ==========")
print("RSQ 前重复温度相关行数:", len(df_dup_temp_related_rows))
print("RSQ 前存在重复温度点的物质数:", len(dup_temp_material_keys))
print("RSQ 前删除的重复温度污染物质数据点数:", len(df_removed_dup_temp_materials_in_rsq))

print("\n========== 线性度统计 ==========")
print("RSQ_Surface_vs_T 低于", rsq_threshold, "的物质数量:", len(df_low_rsq))
print("Surface vs T 斜率 > 0 的物质数量:", len(df_positive_slope_surface_T))
print("Surface vs T 斜率 < 0 的物质数量:", len(df_negative_slope_surface_T))

if len(valid_rsq) > 0:
    print("\nRSQ_Surface_vs_T 描述统计:")
    print(valid_rsq["RSQ_Surface_vs_T"].describe())

    print("\n所有物质平均 RSQ_Surface_vs_T:")
    print(valid_rsq["RSQ_Surface_vs_T"].mean())

    print("\nRSQ_Surface_vs_invT 描述统计:")
    print(valid_rsq["RSQ_Surface_vs_invT"].describe())

    print("\nRSQ_lnSurface_vs_T 描述统计:")
    print(valid_rsq["RSQ_lnSurface_vs_T"].describe())

    print("\nRSQ_Surface_vs_T 最低的前 20 个物质:")
    show_cols = [
        "compound_name",
        "cas",
        "formula",
        "phase",
        "property_name",
        "n_points",
        "T_range",

        "SurfaceTension_min_N_m",
        "SurfaceTension_max_N_m",
        "SurfaceTension_range_N_m",

        "RSQ_Surface_vs_T",
        "RSQ_Surface_vs_invT",
        "RSQ_lnSurface_vs_T",

        "slope_Surface_vs_T",
        "slope_direction_Surface_vs_T",
    ]

    show_cols = [c for c in show_cols if c in df_rsq.columns]

    print(df_rsq[show_cols].head(20).to_string(index=False))
else:
    print("\n没有可用于计算 RSQ 的物质。请检查输入文件或筛选规则。")