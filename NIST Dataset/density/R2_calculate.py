import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score


# =========================
# 1. 输入输出文件
# =========================
input_file = Path("thermoml_Density_Liquid_around_100kPa_deduplicated_min3_Tgt30.xlsx")
input_sheet = "Liquid_100kPa_Final"

output_file = Path("thermoml_Density_Liquid_100kPa_with_RSQ.xlsx")

# 自变量：温度
x_col = "T_K"

# 因变量：密度
y_col = "Density_g_per_cm3"

# RSQ 阈值，低于该值的物质会单独输出
rsq_threshold = 0.95


# =========================
# 2. 读取数据
# =========================
df = pd.read_excel(input_file, sheet_name=input_sheet)

print("原始数据点数:", len(df))
print("原始列名:")
print(list(df.columns))

if x_col not in df.columns:
    raise ValueError(f"没有找到温度列: {x_col}")

if y_col not in df.columns:
    if "Density_kg_per_m3" in df.columns:
        df[y_col] = pd.to_numeric(df["Density_kg_per_m3"], errors="coerce") / 1000.0
        print(f"没有找到 {y_col}，已由 Density_kg_per_m3 / 1000 生成。")
    else:
        raise ValueError(f"没有找到密度列: {y_col}")

df[x_col] = pd.to_numeric(df[x_col], errors="coerce")
df[y_col] = pd.to_numeric(df[y_col], errors="coerce")

if "P_kPa" in df.columns:
    df["P_kPa"] = pd.to_numeric(df["P_kPa"], errors="coerce")


# =========================
# 3. 如果没有 material_key，就自动生成
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


# =========================
# 4. 计算每个物质的线性拟合 R²
# =========================
summary_rows = []

for material_key, group in df.groupby("material_key", sort=False):
    g = group.copy()

    # 去掉温度或密度缺失的点
    g = g.dropna(subset=[x_col, y_col])

    compound_name = g["compound_name"].iloc[0] if "compound_name" in g.columns and len(g) > 0 else None
    cas = g["cas"].iloc[0] if "cas" in g.columns and len(g) > 0 else None
    formula = g["formula"].iloc[0] if "formula" in g.columns and len(g) > 0 else None
    smiles = g["smiles"].iloc[0] if "smiles" in g.columns and len(g) > 0 else None
    inchikey = g["inchikey"].iloc[0] if "inchikey" in g.columns and len(g) > 0 else None

    if len(g) < 2:
        summary_rows.append({
            "material_key": material_key,
            "compound_name": compound_name,
            "cas": cas,
            "formula": formula,
            "inchikey": inchikey,
            "smiles": smiles,
            "n_points": len(g),
            "T_min": np.nan,
            "T_max": np.nan,
            "T_range": np.nan,
            "Density_min_g_per_cm3": np.nan,
            "Density_max_g_per_cm3": np.nan,
            "Density_range_g_per_cm3": np.nan,
            "P_min_kPa": np.nan,
            "P_max_kPa": np.nan,
            "RSQ": np.nan,
            "slope": np.nan,
            "intercept": np.nan,
            "fit_status": "less_than_2_points"
        })
        continue

    # 按温度排序
    g = g.sort_values(x_col)

    X = g[[x_col]].values
    y = g[y_col].values

    model = LinearRegression()
    model.fit(X, y)

    y_pred = model.predict(X)

    rsq = r2_score(y, y_pred)
    slope = model.coef_[0]
    intercept = model.intercept_

    row = {
        "material_key": material_key,
        "compound_name": compound_name,
        "cas": cas,
        "formula": formula,
        "inchikey": inchikey,
        "smiles": smiles,
        "n_points": len(g),
        "T_min": g[x_col].min(),
        "T_max": g[x_col].max(),
        "T_range": g[x_col].max() - g[x_col].min(),
        "Density_min_g_per_cm3": g[y_col].min(),
        "Density_max_g_per_cm3": g[y_col].max(),
        "Density_range_g_per_cm3": g[y_col].max() - g[y_col].min(),
        "RSQ": rsq,
        "slope": slope,
        "intercept": intercept,
        "fit_status": "ok"
    }

    if "P_kPa" in g.columns:
        row["P_min_kPa"] = g["P_kPa"].min()
        row["P_max_kPa"] = g["P_kPa"].max()

    # 液体密度通常随温度升高而降低，所以 slope 通常应小于 0
    if slope < 0:
        row["slope_direction"] = "density_decreases_with_temperature"
    elif slope > 0:
        row["slope_direction"] = "density_increases_with_temperature"
    else:
        row["slope_direction"] = "zero_slope"

    summary_rows.append(row)


df_rsq = pd.DataFrame(summary_rows)

# 按 RSQ 从小到大排序，方便优先检查拟合差的物质
df_rsq = df_rsq.sort_values("RSQ", ascending=True, na_position="last")


# =========================
# 5. 把 RSQ 合并回原始数据
# =========================
merge_cols = [
    "material_key",
    "RSQ",
    "slope",
    "intercept",
    "fit_status",
    "slope_direction"
]

merge_cols = [c for c in merge_cols if c in df_rsq.columns]

df_with_rsq = df.merge(
    df_rsq[merge_cols],
    on="material_key",
    how="left"
)


# =========================
# 6. 筛选拟合度较差的物质
# =========================
df_low_rsq = df_rsq[
    (df_rsq["fit_status"] == "ok") &
    (df_rsq["RSQ"] < rsq_threshold)
].copy()


# =========================
# 7. 筛选斜率异常的物质
# =========================
# 液体密度一般随温度升高降低，因此 slope > 0 的物质需要重点检查
df_positive_slope = df_rsq[
    (df_rsq["fit_status"] == "ok") &
    (df_rsq["slope"] > 0)
].copy()


# =========================
# 8. 总体统计
# =========================
valid_rsq = df_rsq[
    (df_rsq["fit_status"] == "ok") &
    (df_rsq["RSQ"].notna())
].copy()

summary = pd.DataFrame([
    {"item": "input_file", "value": str(input_file)},
    {"item": "input_sheet", "value": input_sheet},
    {"item": "output_file", "value": str(output_file)},
    {"item": "x_col", "value": x_col},
    {"item": "y_col", "value": y_col},
    {"item": "n_rows", "value": len(df)},
    {"item": "n_materials_total", "value": df["material_key"].nunique()},
    {"item": "n_materials_valid_rsq", "value": len(valid_rsq)},
    {"item": "rsq_threshold", "value": rsq_threshold},
    {"item": "n_low_rsq_materials", "value": len(df_low_rsq)},
    {"item": "n_positive_slope_materials", "value": len(df_positive_slope)},
    {"item": "RSQ_mean", "value": valid_rsq["RSQ"].mean()},
    {"item": "RSQ_median", "value": valid_rsq["RSQ"].median()},
    {"item": "RSQ_min", "value": valid_rsq["RSQ"].min()},
    {"item": "RSQ_max", "value": valid_rsq["RSQ"].max()},
    {"item": "slope_mean", "value": valid_rsq["slope"].mean()},
    {"item": "slope_median", "value": valid_rsq["slope"].median()},
])


# =========================
# 9. 保存 Excel
# =========================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_with_rsq.to_excel(writer, sheet_name="Data_With_RSQ", index=False)
    df_rsq.to_excel(writer, sheet_name="Material_RSQ", index=False)
    df_low_rsq.to_excel(writer, sheet_name="Low_RSQ_Materials", index=False)
    df_positive_slope.to_excel(writer, sheet_name="Positive_Slope_Materials", index=False)
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

print("保存完成:", output_file)

print("\n物质数量:", df_rsq["material_key"].nunique())
print("有效 RSQ 物质数量:", len(valid_rsq))
print("RSQ 低于", rsq_threshold, "的物质数量:", len(df_low_rsq))
print("slope > 0 的物质数量:", len(df_positive_slope))

print("\nRSQ 描述统计:")
print(valid_rsq["RSQ"].describe())

print("\n所有物质平均 RSQ:")
print(valid_rsq["RSQ"].mean())

print("\nRSQ 最低的前 20 个物质:")
show_cols = [
    "compound_name",
    "cas",
    "formula",
    "n_points",
    "T_range",
    "Density_min_g_per_cm3",
    "Density_max_g_per_cm3",
    "RSQ",
    "slope",
    "slope_direction"
]
show_cols = [c for c in show_cols if c in df_rsq.columns]

print(df_rsq[show_cols].head(20))