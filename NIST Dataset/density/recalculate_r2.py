import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error


# =========================================================
# 1. 输入输出文件
# =========================================================
input_file = Path("dataset_density_selected_by_two_k_with_density_T_interpolation_8points.xlsx")
output_file = Path("dataset_density_selected_by_two_k_with_density_T_linearity.xlsx")


# =========================================================
# 2. sheet 和列名设置
# =========================================================
data_sheet = "Data_selected"
material_sheet = "Material_selected"
groups_sheet = "Groups_Selected"

material_key_col = "material_key"
temp_col = "T_K"

# density 数值列候选
# 你前面已经确认 property_value 是真正的数值列，所以优先放第一位
density_col_candidates = [
    "property_value",
    "value",
    "Density_kg_m3",
    "density_kg_m3",
    "Density, kg/m3",
    "Mass density, kg/m3",
    "mass_density_kg_m3",
    "Mass_Density_kg_m3",
    "rho_kg_m3",
    "rho",
    "density",
    "Density",
]

# 每个物质至少多少个点才计算线性度
min_points_for_fit = 2


# =========================================================
# 3. 工具函数
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
    for col in [
        "material_key",
        "inchikey",
        "InChIKey",
        "inchi_key",
        "pubchem_inchikey",
        "PubChem_InChIKey",
        "cas",
        "compound_name",
        "formula",
    ]:
        if col in row.index and is_valid_value(row[col]):
            if col == "material_key":
                return str(row[col]).strip()
            return f"{col}:{str(row[col]).strip()}"

    return "unknown_material"


def find_first_existing_col(df, candidates, col_type, required=True):
    """
    自动寻找列名。
    先精确匹配，再小写匹配。
    """
    for col in candidates:
        if col in df.columns:
            return col

    lower_map = {str(c).lower(): c for c in df.columns}

    for col in candidates:
        if str(col).lower() in lower_map:
            return lower_map[str(col).lower()]

    if required:
        raise ValueError(
            f"没有找到 {col_type} 列。\n"
            f"候选列名: {candidates}\n"
            f"当前列名: {list(df.columns)}"
        )

    return None


def calc_ard_percent(y_true, y_pred, eps=1e-12):
    """
    ARD: Average Relative Deviation, %
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = (
        np.isfinite(y_true)
        & np.isfinite(y_pred)
        & (np.abs(y_true) > eps)
    )

    if mask.sum() == 0:
        return np.nan

    return np.mean(np.abs((y_pred[mask] - y_true[mask]) / y_true[mask])) * 100.0


def calc_error_band_counts(y_true, y_pred, bands=(1, 5, 10)):
    """
    统计相对误差在 1%、5%、10% 以内的点数和比例。
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = (
        np.isfinite(y_true)
        & np.isfinite(y_pred)
        & (np.abs(y_true) > 1e-12)
    )

    rel_error = np.full_like(y_true, np.nan, dtype=float)
    rel_error[mask] = np.abs((y_pred[mask] - y_true[mask]) / y_true[mask]) * 100.0

    result = {}

    for b in bands:
        result[f"within_{b}pct_count"] = int(np.nansum(rel_error <= b))
        result[f"within_{b}pct_ratio"] = (
            float(np.nanmean(rel_error <= b))
            if len(rel_error) > 0
            else np.nan
        )

    return result


def fit_one_material_linearity(group):
    """
    对单个物质拟合：

        density = intercept + slope * T

    即普通密度值对温度 T 的线性拟合。
    """
    g = group.copy()

    g[temp_col] = pd.to_numeric(g[temp_col], errors="coerce")
    g[density_col] = pd.to_numeric(g[density_col], errors="coerce")

    g = g.dropna(subset=[temp_col, density_col])
    g = g[
        np.isfinite(g[temp_col])
        & np.isfinite(g[density_col])
        & (g[temp_col] > 0)
        & (g[density_col] > 0)
    ].copy()

    if len(g) < min_points_for_fit:
        return None, None

    # 同一温度如果有重复点，对 density 取平均
    agg_dict = {
        density_col: "mean",
    }

    keep_meta_cols = [
        c for c in [
            material_key_col,
            "compound_name",
            "cas",
            "formula",
            "SMILES",
            "smiles",
            "final_smiles",
            "inchikey",
            "pubchem_cid",
            "pubchem_iupac_name",
            "boiling_T_K",
            "critical_T_K",
        ]
        if c in g.columns
    ]

    for col in keep_meta_cols:
        if col not in agg_dict and col != temp_col:
            agg_dict[col] = "first"

    g = (
        g
        .groupby(temp_col, as_index=False)
        .agg(agg_dict)
        .sort_values(temp_col)
        .reset_index(drop=True)
    )

    if len(g) < min_points_for_fit:
        return None, None

    X = g[[temp_col]].values
    y_density = g[density_col].values.astype(float)

    model = LinearRegression()
    model.fit(X, y_density)

    y_density_pred = model.predict(X)

    g["Density_fit"] = y_density_pred
    g["Density_residual"] = g[density_col] - g["Density_fit"]
    g["Density_abs_error"] = np.abs(g[density_col] - g["Density_fit"])
    g["Density_rel_error_percent"] = (
        np.abs(g["Density_fit"] - g[density_col])
        / g[density_col]
        * 100.0
    )

    r2_density = r2_score(y_density, y_density_pred) if len(g) >= 2 else np.nan
    mse_density = mean_squared_error(y_density, y_density_pred)
    rmse_density = np.sqrt(mse_density)
    mae_density = mean_absolute_error(y_density, y_density_pred)
    ard_density = calc_ard_percent(y_density, y_density_pred)

    band_stats = calc_error_band_counts(y_density, y_density_pred, bands=(1, 5, 10))

    material_key = (
        str(g[material_key_col].iloc[0]).strip()
        if material_key_col in g.columns
        else "unknown_material"
    )

    summary = {
        material_key_col: material_key,
        "n_points_used": len(g),

        "T_min_K": g[temp_col].min(),
        "T_max_K": g[temp_col].max(),
        "T_range_K": g[temp_col].max() - g[temp_col].min(),

        "Density_min": g[density_col].min(),
        "Density_max": g[density_col].max(),
        "Density_range": g[density_col].max() - g[density_col].min(),

        "linear_model": "density = intercept + slope * T",
        "intercept": float(model.intercept_),
        "slope_dDensity_dT": float(model.coef_[0]),

        "R2_Density_vs_T": r2_density,
        "MSE_Density": mse_density,
        "RMSE_Density": rmse_density,
        "MAE_Density": mae_density,
        "ARD_Density_percent": ard_density,
    }

    summary.update(band_stats)

    for col in [
        "compound_name",
        "cas",
        "formula",
        "SMILES",
        "smiles",
        "final_smiles",
        "inchikey",
        "pubchem_cid",
        "pubchem_iupac_name",
        "boiling_T_K",
        "critical_T_K",
    ]:
        if col in g.columns:
            summary[col] = g[col].iloc[0]

    return summary, g


# =========================================================
# 4. 读取 Excel
# =========================================================
if not input_file.exists():
    raise FileNotFoundError(f"没有找到输入文件: {input_file}")

xls = pd.ExcelFile(input_file)

print("输入文件包含的 sheet:")
print(xls.sheet_names)

if data_sheet not in xls.sheet_names:
    raise ValueError(f"没有找到 sheet: {data_sheet}")

df_data = pd.read_excel(input_file, sheet_name=data_sheet)

print("\nData_selected 原始行数:", len(df_data))

if material_key_col not in df_data.columns:
    df_data[material_key_col] = df_data.apply(build_material_key, axis=1)

df_data[material_key_col] = df_data[material_key_col].astype(str).str.strip()

if temp_col not in df_data.columns:
    raise ValueError(f"{data_sheet} 中没有找到温度列: {temp_col}")

density_col = find_first_existing_col(
    df_data,
    density_col_candidates,
    "density 目标",
    required=True
)

df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
df_data[density_col] = pd.to_numeric(df_data[density_col], errors="coerce")

print("\n使用温度列:", temp_col)
print("使用 density 列:", density_col)

print("\n========== 数值列检查 ==========")
print("T_K 非空数量:", df_data[temp_col].notna().sum())
print("T_K > 0 数量:", int((df_data[temp_col] > 0).sum()))
print("density 非空数量:", df_data[density_col].notna().sum())
print("density > 0 数量:", int((df_data[density_col] > 0).sum()))
print("density 前 10 个值:")
print(df_data[density_col].head(10).tolist())


# =========================================================
# 5. 按物质计算线性度
# =========================================================
summary_rows = []
fit_data_rows = []
failed_rows = []

for material_key, group in df_data.groupby(material_key_col, sort=False):
    summary, fit_data = fit_one_material_linearity(group)

    if summary is None:
        failed_rows.append({
            material_key_col: material_key,
            "failed_reason": f"valid_points_less_than_{min_points_for_fit}",
            "raw_rows": len(group),
        })
        continue

    summary_rows.append(summary)
    fit_data_rows.append(fit_data)

df_linearity = pd.DataFrame(summary_rows)

if len(fit_data_rows) > 0:
    df_fit_data = pd.concat(fit_data_rows, ignore_index=True)
else:
    df_fit_data = pd.DataFrame()

df_failed = pd.DataFrame(failed_rows)

print("\n========== 线性度计算结果 ==========")
print("成功计算线性度物质数:", len(df_linearity))
print("失败物质数:", len(df_failed))

if len(df_linearity) > 0:
    print("\nR2_Density_vs_T 描述统计:")
    print(df_linearity["R2_Density_vs_T"].describe())

    print("\nR2 分布:")
    print("R2 >= 0.99:", int((df_linearity["R2_Density_vs_T"] >= 0.99).sum()))
    print("R2 >= 0.95:", int((df_linearity["R2_Density_vs_T"] >= 0.95).sum()))
    print("R2 >= 0.90:", int((df_linearity["R2_Density_vs_T"] >= 0.90).sum()))
    print("R2 <  0.90:", int((df_linearity["R2_Density_vs_T"] < 0.90).sum()))


# =========================================================
# 6. 和 Material_selected 合并线性度统计
# =========================================================
sheet_tables = {}

for sheet in xls.sheet_names:
    if sheet == data_sheet:
        continue

    try:
        sheet_tables[sheet] = pd.read_excel(input_file, sheet_name=sheet)
    except Exception as e:
        print(f"读取 sheet 失败: {sheet}, error={e}")

if material_sheet in sheet_tables and len(df_linearity) > 0:
    df_material = sheet_tables[material_sheet].copy()

    if material_key_col not in df_material.columns:
        df_material[material_key_col] = df_material.apply(build_material_key, axis=1)

    df_material[material_key_col] = df_material[material_key_col].astype(str).str.strip()

    merge_cols = [
        material_key_col,
        "n_points_used",
        "T_min_K",
        "T_max_K",
        "T_range_K",
        "intercept",
        "slope_dDensity_dT",
        "R2_Density_vs_T",
        "RMSE_Density",
        "MAE_Density",
        "ARD_Density_percent",
        "within_1pct_count",
        "within_1pct_ratio",
        "within_5pct_count",
        "within_5pct_ratio",
        "within_10pct_count",
        "within_10pct_ratio",
    ]

    merge_cols = [c for c in merge_cols if c in df_linearity.columns]

    df_material = df_material.drop(
        columns=[
            c for c in merge_cols
            if c != material_key_col and c in df_material.columns
        ],
        errors="ignore"
    )

    df_material = df_material.merge(
        df_linearity[merge_cols],
        on=material_key_col,
        how="left"
    )

    sheet_tables[material_sheet] = df_material


# =========================================================
# 7. 生成 Summary
# =========================================================
summary = pd.DataFrame([
    {"item": "input_file", "value": str(input_file)},
    {"item": "output_file", "value": str(output_file)},
    {"item": "data_sheet", "value": data_sheet},
    {"item": "material_sheet", "value": material_sheet},
    {"item": "material_key_col", "value": material_key_col},
    {"item": "temp_col", "value": temp_col},
    {"item": "density_col", "value": density_col},
    {"item": "linearity_formula", "value": "density = intercept + slope * T"},
    {"item": "min_points_for_fit", "value": min_points_for_fit},
    {"item": "data_rows", "value": len(df_data)},
    {"item": "materials_total", "value": df_data[material_key_col].nunique()},
    {"item": "materials_linearity_success", "value": len(df_linearity)},
    {"item": "materials_linearity_failed", "value": len(df_failed)},
])

if len(df_linearity) > 0:
    extra_summary = pd.DataFrame([
        {"item": "R2_mean", "value": df_linearity["R2_Density_vs_T"].mean()},
        {"item": "R2_median", "value": df_linearity["R2_Density_vs_T"].median()},
        {"item": "R2_min", "value": df_linearity["R2_Density_vs_T"].min()},
        {"item": "R2_max", "value": df_linearity["R2_Density_vs_T"].max()},
        {"item": "R2_ge_0.99_count", "value": int((df_linearity["R2_Density_vs_T"] >= 0.99).sum())},
        {"item": "R2_ge_0.95_count", "value": int((df_linearity["R2_Density_vs_T"] >= 0.95).sum())},
        {"item": "R2_ge_0.90_count", "value": int((df_linearity["R2_Density_vs_T"] >= 0.90).sum())},
        {"item": "R2_lt_0.90_count", "value": int((df_linearity["R2_Density_vs_T"] < 0.90).sum())},
    ])

    summary = pd.concat([summary, extra_summary], ignore_index=True)


# =========================================================
# 8. 保存 Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_linearity.to_excel(writer, sheet_name="Linearity_Summary", index=False)
    df_fit_data.to_excel(writer, sheet_name="Data_with_Linearity_Fit", index=False)
    df_failed.to_excel(writer, sheet_name="Failed_Materials", index=False)

    # 原 Data_selected 保存一份
    df_data.to_excel(writer, sheet_name=data_sheet, index=False)

    # 复制其他 sheet，并更新 Material_selected
    for sheet in xls.sheet_names:
        if sheet == data_sheet:
            continue

        if sheet in sheet_tables:
            df_sheet = sheet_tables[sheet]
            df_sheet.to_excel(writer, sheet_name=sheet[:31], index=False)

    summary.to_excel(writer, sheet_name="Summary_Linearity", index=False)

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

            ws.column_dimensions[col_letter].width = min(max_length + 2, 45)


print("\n保存完成:", output_file)
print("主要输出 sheet:")
print("1. Linearity_Summary：每个物质 density vs T 的线性度")
print("2. Data_with_Linearity_Fit：每个温度点的线性拟合值和残差")
print("3. Material_selected：合并线性度统计后的物质表")
print("4. Summary_Linearity：总体统计")