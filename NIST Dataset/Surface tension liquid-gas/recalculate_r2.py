# -*- coding: utf-8 -*-
"""
Surface tension liquid-gas 最终 8points 数据线性度 R² 重新计算脚本

输入：
    dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points.xlsx

输入主 sheet：
    Data_selected

输出：
    dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points_with_RSQ.xlsx

功能：
    1. 读取最终抽点后的 Data_selected
    2. 按 material_key 分组
    3. 对每个物质重新计算：
        - SurfaceTension_N_m vs T_K 的 R²
        - SurfaceTension_N_m vs 1/T_K 的 R²
        - ln(SurfaceTension_N_m) vs T_K 的 R²
    4. 将 R²、斜率、截距合并回：
        - Data_selected
        - Material_selected
        - Final_Model_Table
    5. 保留原 Excel 中的其他 sheet
    6. 输出低 R² 物质、斜率异常物质、重复温度检查表和 Summary_RSQ
"""

import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score


# =========================================================
# 1. 输入输出文件
# =========================================================

input_file = Path(
    "dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points.xlsx"
)

output_file = Path(
    "dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points_with_RSQ.xlsx"
)


# =========================================================
# 2. sheet 名设置
# =========================================================

data_sheet = "Data_selected"
material_sheet = "Material_selected"
final_model_sheet = "Final_Model_Table"


# =========================================================
# 3. 基础列名与参数
# =========================================================

material_key_col = "material_key"
temp_col = "T_K"

# Surface tension 列自动识别
surface_col = None
surface_col_candidates = [
    "SurfaceTension_N_m",
    "surface_tension_N_m",
    "Surface_Tension_N_m",
    "SurfaceTension",
    "surface_tension",
    "property_value",
]

ln_surface_col = "lnSurfaceTension_N_m"
invT_col = "InvT_1_per_K"

# R² 阈值，低于该值的物质会进入 Low_RSQ_Materials
rsq_threshold = 0.95

# 温度重复判断精度
temp_round_decimals = 6

# 如果同一物质同一温度仍有重复点，拟合时是否先对重复温度点取均值
aggregate_duplicate_temperature_for_fit = True


# =========================================================
# 4. 工具函数
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
    如果表中没有 material_key，则自动构造。

    优先级：
        1. material_key
        2. inchikey
        3. pubchem_inchikey
        4. cas
        5. compound_name
        6. formula
    """
    for col in [
        "material_key",
        "inchikey",
        "pubchem_inchikey",
        "cas",
        "compound_name",
        "formula",
    ]:
        if col in row.index and is_valid_value(row[col]):
            if col == "material_key":
                return str(row[col]).strip()

            return f"{col}:{str(row[col]).strip()}"

    return "unknown_material"


def auto_find_column(df, candidates, col_type):
    """
    自动识别列名，大小写不敏感。
    """
    lower_map = {str(c).lower(): c for c in df.columns}

    for c in candidates:
        if c in df.columns:
            return c

    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]

    raise ValueError(
        f"没有找到 {col_type} 列。\n"
        f"候选列名为: {candidates}\n"
        f"当前表格列名为: {list(df.columns)}"
    )


def fit_linear_rsq(g, x_col, y_col):
    """
    对单个物质做 y = slope * x + intercept 线性拟合。
    """
    g_fit = g.dropna(subset=[x_col, y_col]).copy()

    if len(g_fit) < 2:
        return {
            "n_fit_points": len(g_fit),
            "RSQ": np.nan,
            "slope": np.nan,
            "intercept": np.nan,
            "fit_status": "less_than_2_points",
        }

    X = g_fit[[x_col]].values.astype(float)
    y = g_fit[y_col].values.astype(float)

    if len(np.unique(X.flatten())) < 2:
        return {
            "n_fit_points": len(g_fit),
            "RSQ": np.nan,
            "slope": np.nan,
            "intercept": np.nan,
            "fit_status": "less_than_2_unique_x",
        }

    model = LinearRegression()
    model.fit(X, y)

    y_pred = model.predict(X)

    return {
        "n_fit_points": len(g_fit),
        "RSQ": r2_score(y, y_pred),
        "slope": float(model.coef_[0]),
        "intercept": float(model.intercept_),
        "fit_status": "ok",
    }


def first_or_none(g, col):
    if col in g.columns and len(g) > 0:
        return g[col].iloc[0]
    return None


def prepare_group_for_fit(group, temp_col, surface_col):
    """
    准备用于拟合的单个物质数据。

    处理：
        1. 删除 T 或 surface tension 缺失
        2. 删除 surface tension <= 0
        3. 如果同温度重复，按温度聚合，表面张力取均值
        4. 构造 1/T 和 ln(surface tension)
    """
    g = group.copy()

    g[temp_col] = pd.to_numeric(g[temp_col], errors="coerce")
    g[surface_col] = pd.to_numeric(g[surface_col], errors="coerce")

    g = g.dropna(subset=[temp_col, surface_col])
    g = g[
        np.isfinite(g[temp_col])
        & np.isfinite(g[surface_col])
        & (g[surface_col] > 0)
    ].copy()

    if len(g) == 0:
        return g

    if aggregate_duplicate_temperature_for_fit:
        # 只保留拟合需要的数值列；元信息后面从原 group 取
        g = (
            g
            .groupby(temp_col, as_index=False)
            .agg(
                SurfaceTension_for_fit=(surface_col, "mean"),
                n_rows_at_same_T=(surface_col, "size"),
            )
        )

        g[surface_col] = g["SurfaceTension_for_fit"]
        g = g.drop(columns=["SurfaceTension_for_fit"])

    g = g.sort_values(temp_col).reset_index(drop=True)

    g[invT_col] = 1.0 / g[temp_col]
    g[ln_surface_col] = np.log(g[surface_col])

    return g


# =========================================================
# 5. 读取 Excel
# =========================================================

if not input_file.exists():
    raise FileNotFoundError(f"没有找到输入文件: {input_file}")

xls = pd.ExcelFile(input_file)

print("输入文件包含的 sheet:")
print(xls.sheet_names)

if data_sheet not in xls.sheet_names:
    raise ValueError(f"没有找到主数据 sheet: {data_sheet}")

df_data = pd.read_excel(input_file, sheet_name=data_sheet)

print("\n读取 Data_selected 行数:", len(df_data))
print("Data_selected 列名:")
print(list(df_data.columns))


# =========================================================
# 6. 基础列整理
# =========================================================

if material_key_col not in df_data.columns:
    df_data[material_key_col] = df_data.apply(build_material_key, axis=1)

df_data[material_key_col] = df_data[material_key_col].astype(str).str.strip()

if temp_col not in df_data.columns:
    raise ValueError(f"{data_sheet} 中没有找到温度列: {temp_col}")

if surface_col is None:
    surface_col = auto_find_column(
        df_data,
        surface_col_candidates,
        "Surface tension"
    )

print("\n使用的 Surface tension 列:", surface_col)

df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
df_data[surface_col] = pd.to_numeric(df_data[surface_col], errors="coerce")


# =========================================================
# 7. 重复温度检查
# =========================================================

df_data["_T_round"] = df_data[temp_col].round(temp_round_decimals)

dup_temp_mask = df_data.duplicated(
    subset=[material_key_col, "_T_round"],
    keep=False
)

df_dup_temp_related_rows = df_data.loc[dup_temp_mask].copy()

print("\n========== 重复温度检查 ==========")
print("重复温度相关行数:", len(df_dup_temp_related_rows))
print(
    "存在重复温度的物质数:",
    df_dup_temp_related_rows[material_key_col].nunique()
    if len(df_dup_temp_related_rows) > 0 else 0
)


# =========================================================
# 8. 按物质计算 R²
# =========================================================

summary_rows = []

for material_key, group in df_data.groupby(material_key_col, sort=False):
    g_raw = group.copy()
    g_fit = prepare_group_for_fit(g_raw, temp_col, surface_col)

    compound_name = first_or_none(g_raw, "compound_name")
    cas = first_or_none(g_raw, "cas")
    formula = first_or_none(g_raw, "formula")
    smiles = first_or_none(g_raw, "SMILES")
    if smiles is None:
        smiles = first_or_none(g_raw, "smiles")
    inchikey = first_or_none(g_raw, "inchikey")
    pubchem_inchikey = first_or_none(g_raw, "pubchem_inchikey")
    boiling_T_K = first_or_none(g_raw, "boiling_T_K")
    title = first_or_none(g_raw, "title")

    if len(g_fit) < 2:
        row = {
            material_key_col: material_key,
            "compound_name": compound_name,
            "cas": cas,
            "formula": formula,
            "SMILES": smiles,
            "inchikey": inchikey,
            "pubchem_inchikey": pubchem_inchikey,
            "boiling_T_K": boiling_T_K,
            "title": title,

            "n_points_raw": len(g_raw),
            "n_points_for_fit": len(g_fit),
            "n_unique_T_for_fit": g_fit[temp_col].nunique() if len(g_fit) > 0 else 0,

            "T_min": np.nan,
            "T_max": np.nan,
            "T_range": np.nan,

            "SurfaceTension_min_N_m": np.nan,
            "SurfaceTension_max_N_m": np.nan,
            "SurfaceTension_range_N_m": np.nan,

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
        }

        summary_rows.append(row)
        continue

    fit_surface_T = fit_linear_rsq(g_fit, temp_col, surface_col)
    fit_surface_invT = fit_linear_rsq(g_fit, invT_col, surface_col)
    fit_ln_surface_T = fit_linear_rsq(g_fit, temp_col, ln_surface_col)

    if fit_surface_T["slope"] < 0:
        slope_direction = "surface_tension_decreases_with_temperature"
    elif fit_surface_T["slope"] > 0:
        slope_direction = "surface_tension_increases_with_temperature"
    elif fit_surface_T["slope"] == 0:
        slope_direction = "zero_slope"
    else:
        slope_direction = "not_available"

    row = {
        material_key_col: material_key,
        "compound_name": compound_name,
        "cas": cas,
        "formula": formula,
        "SMILES": smiles,
        "inchikey": inchikey,
        "pubchem_inchikey": pubchem_inchikey,
        "boiling_T_K": boiling_T_K,
        "title": title,

        "n_points_raw": len(g_raw),
        "n_points_for_fit": len(g_fit),
        "n_unique_T_for_fit": g_fit[temp_col].nunique(),

        "T_min": g_fit[temp_col].min(),
        "T_max": g_fit[temp_col].max(),
        "T_range": g_fit[temp_col].max() - g_fit[temp_col].min(),

        "SurfaceTension_min_N_m": g_fit[surface_col].min(),
        "SurfaceTension_max_N_m": g_fit[surface_col].max(),
        "SurfaceTension_range_N_m": g_fit[surface_col].max() - g_fit[surface_col].min(),

        "RSQ_Surface_vs_T": fit_surface_T["RSQ"],
        "slope_Surface_vs_T": fit_surface_T["slope"],
        "intercept_Surface_vs_T": fit_surface_T["intercept"],

        "RSQ_Surface_vs_invT": fit_surface_invT["RSQ"],
        "slope_Surface_vs_invT": fit_surface_invT["slope"],
        "intercept_Surface_vs_invT": fit_surface_invT["intercept"],

        "RSQ_lnSurface_vs_T": fit_ln_surface_T["RSQ"],
        "slope_lnSurface_vs_T": fit_ln_surface_T["slope"],
        "intercept_lnSurface_vs_T": fit_ln_surface_T["intercept"],

        "fit_status": fit_surface_T["fit_status"],
        "slope_direction_Surface_vs_T": slope_direction,
    }

    summary_rows.append(row)


df_rsq = pd.DataFrame(summary_rows)

df_rsq = df_rsq.sort_values(
    "RSQ_Surface_vs_T",
    ascending=True,
    na_position="last"
).reset_index(drop=True)


# =========================================================
# 9. 合并 R² 到 Data_selected
# =========================================================

rsq_merge_cols = [
    material_key_col,

    "n_points_raw",
    "n_points_for_fit",
    "n_unique_T_for_fit",

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

rsq_merge_cols = [c for c in rsq_merge_cols if c in df_rsq.columns]

# 删除旧的 R² 列，避免重复
old_rsq_cols = [
    c for c in rsq_merge_cols
    if c != material_key_col and c in df_data.columns
]

df_data_out = df_data.drop(columns=old_rsq_cols, errors="ignore").copy()

df_data_out = df_data_out.merge(
    df_rsq[rsq_merge_cols],
    on=material_key_col,
    how="left"
)

# 删除内部临时列
if "_T_round" in df_data_out.columns:
    df_data_out = df_data_out.drop(columns=["_T_round"])


# =========================================================
# 10. 低 R² 和斜率异常表
# =========================================================

df_valid_rsq = df_rsq[
    (df_rsq["fit_status"] == "ok")
    & df_rsq["RSQ_Surface_vs_T"].notna()
].copy()

df_low_rsq = df_valid_rsq[
    df_valid_rsq["RSQ_Surface_vs_T"] < rsq_threshold
].copy()

# 表面张力通常随温度升高下降，所以正斜率通常需要检查
df_positive_slope = df_valid_rsq[
    df_valid_rsq["slope_Surface_vs_T"] > 0
].copy()

df_negative_slope = df_valid_rsq[
    df_valid_rsq["slope_Surface_vs_T"] < 0
].copy()


# =========================================================
# 11. 读取其他 sheet，并把 R² 合并到 Material / Final_Model_Table
# =========================================================

sheet_tables = {}

for sheet in xls.sheet_names:
    if sheet == data_sheet:
        continue

    sheet_tables[sheet] = pd.read_excel(input_file, sheet_name=sheet)


# 合并到 Material_selected
if material_sheet in sheet_tables:
    df_material = sheet_tables[material_sheet].copy()

    if material_key_col not in df_material.columns:
        df_material[material_key_col] = df_material.apply(build_material_key, axis=1)

    df_material[material_key_col] = df_material[material_key_col].astype(str).str.strip()

    cols_to_merge_material = [
        material_key_col,
        "n_points_raw",
        "n_points_for_fit",
        "n_unique_T_for_fit",
        "RSQ_Surface_vs_T",
        "slope_Surface_vs_T",
        "intercept_Surface_vs_T",
        "RSQ_Surface_vs_invT",
        "RSQ_lnSurface_vs_T",
        "fit_status",
        "slope_direction_Surface_vs_T",
    ]

    cols_to_merge_material = [
        c for c in cols_to_merge_material
        if c in df_rsq.columns
    ]

    df_material = df_material.drop(
        columns=[
            c for c in cols_to_merge_material
            if c != material_key_col and c in df_material.columns
        ],
        errors="ignore"
    )

    df_material = df_material.merge(
        df_rsq[cols_to_merge_material],
        on=material_key_col,
        how="left"
    )

    sheet_tables[material_sheet] = df_material


# 合并到 Final_Model_Table
if final_model_sheet in sheet_tables:
    df_final_model = sheet_tables[final_model_sheet].copy()

    if material_key_col in df_final_model.columns:
        df_final_model[material_key_col] = (
            df_final_model[material_key_col].astype(str).str.strip()
        )

        cols_to_merge_final = [
            material_key_col,
            "RSQ_Surface_vs_T",
            "slope_Surface_vs_T",
            "intercept_Surface_vs_T",
            "RSQ_Surface_vs_invT",
            "RSQ_lnSurface_vs_T",
            "fit_status",
            "slope_direction_Surface_vs_T",
        ]

        cols_to_merge_final = [
            c for c in cols_to_merge_final
            if c in df_rsq.columns
        ]

        df_final_model = df_final_model.drop(
            columns=[
                c for c in cols_to_merge_final
                if c != material_key_col and c in df_final_model.columns
            ],
            errors="ignore"
        )

        df_final_model = df_final_model.merge(
            df_rsq[cols_to_merge_final],
            on=material_key_col,
            how="left"
        )

        sheet_tables[final_model_sheet] = df_final_model


# =========================================================
# 12. Summary_RSQ
# =========================================================

summary_rsq = pd.DataFrame([
    {"item": "input_file", "value": str(input_file)},
    {"item": "output_file", "value": str(output_file)},
    {"item": "data_sheet", "value": data_sheet},
    {"item": "material_sheet", "value": material_sheet},
    {"item": "final_model_sheet", "value": final_model_sheet},

    {"item": "material_key_col", "value": material_key_col},
    {"item": "temp_col", "value": temp_col},
    {"item": "surface_col", "value": surface_col},
    {"item": "rsq_threshold", "value": rsq_threshold},
    {"item": "temp_round_decimals", "value": temp_round_decimals},
    {
        "item": "aggregate_duplicate_temperature_for_fit",
        "value": aggregate_duplicate_temperature_for_fit,
    },

    {"item": "data_rows", "value": len(df_data)},
    {"item": "material_count", "value": df_data[material_key_col].nunique()},
    {"item": "valid_rsq_material_count", "value": len(df_valid_rsq)},
    {"item": "low_rsq_material_count", "value": len(df_low_rsq)},
    {"item": "positive_slope_material_count", "value": len(df_positive_slope)},
    {"item": "negative_slope_material_count", "value": len(df_negative_slope)},

    {
        "item": "duplicate_temperature_related_rows",
        "value": len(df_dup_temp_related_rows),
    },
    {
        "item": "duplicate_temperature_material_count",
        "value": (
            df_dup_temp_related_rows[material_key_col].nunique()
            if len(df_dup_temp_related_rows) > 0 else 0
        ),
    },

    {
        "item": "RSQ_Surface_vs_T_mean",
        "value": df_valid_rsq["RSQ_Surface_vs_T"].mean()
        if len(df_valid_rsq) > 0 else np.nan,
    },
    {
        "item": "RSQ_Surface_vs_T_median",
        "value": df_valid_rsq["RSQ_Surface_vs_T"].median()
        if len(df_valid_rsq) > 0 else np.nan,
    },
    {
        "item": "RSQ_Surface_vs_T_min",
        "value": df_valid_rsq["RSQ_Surface_vs_T"].min()
        if len(df_valid_rsq) > 0 else np.nan,
    },
    {
        "item": "RSQ_Surface_vs_T_max",
        "value": df_valid_rsq["RSQ_Surface_vs_T"].max()
        if len(df_valid_rsq) > 0 else np.nan,
    },

    {
        "item": "RSQ_Surface_vs_invT_mean",
        "value": df_valid_rsq["RSQ_Surface_vs_invT"].mean()
        if len(df_valid_rsq) > 0 else np.nan,
    },
    {
        "item": "RSQ_lnSurface_vs_T_mean",
        "value": df_valid_rsq["RSQ_lnSurface_vs_T"].mean()
        if len(df_valid_rsq) > 0 else np.nan,
    },
])


# =========================================================
# 13. 保存新 Excel
# =========================================================

with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    # 主数据 sheet：带重新计算后的 R²
    df_data_out.to_excel(writer, sheet_name=data_sheet, index=False)

    # 新增 R² 诊断 sheet
    df_rsq.to_excel(writer, sheet_name="Material_RSQ", index=False)
    df_low_rsq.to_excel(writer, sheet_name="Low_RSQ_Materials", index=False)
    df_positive_slope.to_excel(writer, sheet_name="Positive_Slope_Surface_T", index=False)
    df_negative_slope.to_excel(writer, sheet_name="Negative_Slope_Surface_T", index=False)

    # 重复温度检查
    df_dup_temp_related_rows_out = df_dup_temp_related_rows.drop(
        columns=["_T_round"],
        errors="ignore"
    )
    df_dup_temp_related_rows_out.to_excel(
        writer,
        sheet_name="DupTemp_Rows_For_RSQ",
        index=False
    )

    # 原有其他 sheet
    for sheet in xls.sheet_names:
        if sheet == data_sheet:
            continue

        df_sheet = sheet_tables[sheet]
        df_sheet.to_excel(writer, sheet_name=sheet[:31], index=False)

    # Summary
    summary_rsq.to_excel(writer, sheet_name="Summary_RSQ", index=False)

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

            ws.column_dimensions[col_letter].width = min(max_length + 2, 40)


# =========================================================
# 14. 控制台输出
# =========================================================

print("\n保存完成:", output_file)

print("\n========== R² 重新计算结果 ==========")
print("数据点数:", len(df_data_out))
print("物质数:", df_data_out[material_key_col].nunique())
print("有效 R² 物质数:", len(df_valid_rsq))
print("RSQ_Surface_vs_T 低于", rsq_threshold, "的物质数:", len(df_low_rsq))
print("斜率 > 0 的物质数:", len(df_positive_slope))
print("斜率 < 0 的物质数:", len(df_negative_slope))

print("\nRSQ_Surface_vs_T 描述统计:")
if len(df_valid_rsq) > 0:
    print(df_valid_rsq["RSQ_Surface_vs_T"].describe())
else:
    print("没有有效 R²。")

print("\nR² 最低的前 20 个物质:")
show_cols = [
    material_key_col,
    "compound_name",
    "cas",
    "formula",
    "title",
    "n_points_for_fit",
    "T_min",
    "T_max",
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