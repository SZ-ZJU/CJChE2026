import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score


# =========================
# 1. 输入输出文件
# =========================
# 读取上一步 Liquid sheet 清理后的结果
input_file = Path("thermoml_vapor_pressure_Liquid_deduplicated_min3_Tgt30.xlsx")
input_sheet = "VP_Liquid_Final"

output_file = Path("thermoml_vapor_pressure_Liquid_with_RSQ.xlsx")

# 基础列名
temp_col = "T_K"
vp_col = "VaporPressure_kPa"
lnp_col = "lnP_kPa"

# RSQ 阈值，低于该值的物质会单独输出
rsq_threshold = 0.95


# =========================
# 2. 读取数据
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

if vp_col not in df.columns:
    raise ValueError(f"没有找到蒸气压列: {vp_col}")

df[temp_col] = pd.to_numeric(df[temp_col], errors="coerce")
df[vp_col] = pd.to_numeric(df[vp_col], errors="coerce")

# 删除 T 或 vapor pressure 缺失的数据
before_drop = len(df)

df = df[
    df[temp_col].notna()
    & df[vp_col].notna()
].copy()

print("删除 T 或 vapor pressure 缺失的数据点数:", before_drop - len(df))

# 删除非正蒸气压，因为 lnP 无意义
before_drop_non_positive = len(df)

df = df[df[vp_col] > 0].copy()

print("删除 vapor pressure <= 0 的数据点数:", before_drop_non_positive - len(df))

# 自动生成 lnP_kPa
# 即使原表中已有 lnP_kPa，这里也重新按 VaporPressure_kPa 计算，避免旧值不一致
df[lnp_col] = np.log(df[vp_col])

# 生成 1/T
df["InvT_1_per_K"] = 1.0 / df[temp_col]

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
# 4. 单个线性拟合函数
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
            "fit_status": "less_than_2_points"
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
        "fit_status": "ok"
    }


# =========================
# 5. 计算每个物质的线性拟合 R²
# =========================
summary_rows = []

for material_key, group in df.groupby("material_key", sort=False):
    g = group.copy()

    g = g.dropna(subset=[temp_col, vp_col, lnp_col, "InvT_1_per_K"])

    compound_name = (
        g["compound_name"].iloc[0]
        if "compound_name" in g.columns and len(g) > 0
        else None
    )

    cas = (
        g["cas"].iloc[0]
        if "cas" in g.columns and len(g) > 0
        else None
    )

    formula = (
        g["formula"].iloc[0]
        if "formula" in g.columns and len(g) > 0
        else None
    )

    smiles = (
        g["smiles"].iloc[0]
        if "smiles" in g.columns and len(g) > 0
        else None
    )

    inchikey = (
        g["inchikey"].iloc[0]
        if "inchikey" in g.columns and len(g) > 0
        else None
    )

    phase = (
        g["phase"].iloc[0]
        if "phase" in g.columns and len(g) > 0
        else None
    )

    property_name = (
        g["property_name"].iloc[0]
        if "property_name" in g.columns and len(g) > 0
        else None
    )

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
            "n_points": len(g),
            "T_min": np.nan,
            "T_max": np.nan,
            "T_range": np.nan,
            "VaporPressure_min_kPa": np.nan,
            "VaporPressure_max_kPa": np.nan,
            "VaporPressure_range_kPa": np.nan,
            "lnP_min_kPa": np.nan,
            "lnP_max_kPa": np.nan,
            "lnP_range_kPa": np.nan,
            "RSQ_P_vs_T": np.nan,
            "slope_P_vs_T": np.nan,
            "intercept_P_vs_T": np.nan,
            "RSQ_lnP_vs_T": np.nan,
            "slope_lnP_vs_T": np.nan,
            "intercept_lnP_vs_T": np.nan,
            "RSQ_lnP_vs_invT": np.nan,
            "slope_lnP_vs_invT": np.nan,
            "intercept_lnP_vs_invT": np.nan,
            "fit_status": "less_than_2_points"
        })
        continue

    g = g.sort_values(temp_col)

    # 1. VaporPressure_kPa vs T_K
    fit_P_T = fit_linear_rsq(g, temp_col, vp_col)

    # 2. lnP_kPa vs T_K
    fit_lnP_T = fit_linear_rsq(g, temp_col, lnp_col)

    # 3. lnP_kPa vs 1/T_K
    fit_lnP_invT = fit_linear_rsq(g, "InvT_1_per_K", lnp_col)

    row = {
        "material_key": material_key,
        "compound_name": compound_name,
        "cas": cas,
        "formula": formula,
        "inchikey": inchikey,
        "smiles": smiles,
        "phase": phase,
        "property_name": property_name,

        "n_points": len(g),

        "T_min": g[temp_col].min(),
        "T_max": g[temp_col].max(),
        "T_range": g[temp_col].max() - g[temp_col].min(),

        "VaporPressure_min_kPa": g[vp_col].min(),
        "VaporPressure_max_kPa": g[vp_col].max(),
        "VaporPressure_range_kPa": g[vp_col].max() - g[vp_col].min(),

        "lnP_min_kPa": g[lnp_col].min(),
        "lnP_max_kPa": g[lnp_col].max(),
        "lnP_range_kPa": g[lnp_col].max() - g[lnp_col].min(),

        "RSQ_P_vs_T": fit_P_T["RSQ"],
        "slope_P_vs_T": fit_P_T["slope"],
        "intercept_P_vs_T": fit_P_T["intercept"],

        "RSQ_lnP_vs_T": fit_lnP_T["RSQ"],
        "slope_lnP_vs_T": fit_lnP_T["slope"],
        "intercept_lnP_vs_T": fit_lnP_T["intercept"],

        "RSQ_lnP_vs_invT": fit_lnP_invT["RSQ"],
        "slope_lnP_vs_invT": fit_lnP_invT["slope"],
        "intercept_lnP_vs_invT": fit_lnP_invT["intercept"],

        "fit_status": "ok"
    }

    if "P_kPa" in g.columns:
        row["P_min_kPa"] = g["P_kPa"].min()
        row["P_max_kPa"] = g["P_kPa"].max()

    # 蒸气压一般随温度升高而升高，所以 P vs T 的 slope 通常应大于 0
    if fit_P_T["slope"] > 0:
        row["slope_direction_P_vs_T"] = "vapor_pressure_increases_with_temperature"
    elif fit_P_T["slope"] < 0:
        row["slope_direction_P_vs_T"] = "vapor_pressure_decreases_with_temperature"
    else:
        row["slope_direction_P_vs_T"] = "zero_slope"

    # lnP vs 1/T 按 Clausius-Clapeyron 通常应为负斜率
    if fit_lnP_invT["slope"] < 0:
        row["slope_direction_lnP_vs_invT"] = "normal_negative_slope"
    elif fit_lnP_invT["slope"] > 0:
        row["slope_direction_lnP_vs_invT"] = "abnormal_positive_slope"
    else:
        row["slope_direction_lnP_vs_invT"] = "zero_slope"

    summary_rows.append(row)


df_rsq = pd.DataFrame(summary_rows)

# 按最重要的 RSQ 排序：lnP vs 1/T
df_rsq = df_rsq.sort_values(
    "RSQ_lnP_vs_invT",
    ascending=True,
    na_position="last"
)


# =========================
# 6. 把 RSQ 合并回原始数据
# =========================
merge_cols = [
    "material_key",

    "RSQ_P_vs_T",
    "slope_P_vs_T",
    "intercept_P_vs_T",

    "RSQ_lnP_vs_T",
    "slope_lnP_vs_T",
    "intercept_lnP_vs_T",

    "RSQ_lnP_vs_invT",
    "slope_lnP_vs_invT",
    "intercept_lnP_vs_invT",

    "fit_status",
    "slope_direction_P_vs_T",
    "slope_direction_lnP_vs_invT"
]

merge_cols = [c for c in merge_cols if c in df_rsq.columns]

df_with_rsq = df.merge(
    df_rsq[merge_cols],
    on="material_key",
    how="left"
)


# =========================
# 7. 筛选拟合度较差的物质
# =========================
# 重点使用 lnP vs 1/T 的 RSQ
df_low_rsq = df_rsq[
    (df_rsq["fit_status"] == "ok") &
    (df_rsq["RSQ_lnP_vs_invT"] < rsq_threshold)
].copy()


# =========================
# 8. 筛选斜率异常的物质
# =========================
# 1. P vs T 通常应该是正斜率
df_negative_slope_P_T = df_rsq[
    (df_rsq["fit_status"] == "ok") &
    (df_rsq["slope_P_vs_T"] < 0)
].copy()

# 2. lnP vs 1/T 通常应该是负斜率
df_positive_slope_lnP_invT = df_rsq[
    (df_rsq["fit_status"] == "ok") &
    (df_rsq["slope_lnP_vs_invT"] > 0)
].copy()


# =========================
# 9. 总体统计
# =========================
valid_rsq = df_rsq[
    (df_rsq["fit_status"] == "ok") &
    (df_rsq["RSQ_lnP_vs_invT"].notna())
].copy()

summary = pd.DataFrame([
    {"item": "input_file", "value": str(input_file)},
    {"item": "input_sheet", "value": input_sheet},
    {"item": "output_file", "value": str(output_file)},
    {"item": "temp_col", "value": temp_col},
    {"item": "vp_col", "value": vp_col},
    {"item": "lnp_col", "value": lnp_col},
    {"item": "main_rsq_used", "value": "RSQ_lnP_vs_invT"},
    {"item": "n_rows", "value": len(df)},
    {"item": "n_materials_total", "value": df["material_key"].nunique()},
    {"item": "n_materials_valid_rsq", "value": len(valid_rsq)},
    {"item": "rsq_threshold", "value": rsq_threshold},

    {"item": "n_low_rsq_materials_lnP_vs_invT", "value": len(df_low_rsq)},
    {"item": "n_negative_slope_P_vs_T_materials", "value": len(df_negative_slope_P_T)},
    {"item": "n_positive_slope_lnP_vs_invT_materials", "value": len(df_positive_slope_lnP_invT)},

    {"item": "RSQ_P_vs_T_mean", "value": valid_rsq["RSQ_P_vs_T"].mean()},
    {"item": "RSQ_P_vs_T_median", "value": valid_rsq["RSQ_P_vs_T"].median()},
    {"item": "RSQ_P_vs_T_min", "value": valid_rsq["RSQ_P_vs_T"].min()},
    {"item": "RSQ_P_vs_T_max", "value": valid_rsq["RSQ_P_vs_T"].max()},

    {"item": "RSQ_lnP_vs_T_mean", "value": valid_rsq["RSQ_lnP_vs_T"].mean()},
    {"item": "RSQ_lnP_vs_T_median", "value": valid_rsq["RSQ_lnP_vs_T"].median()},
    {"item": "RSQ_lnP_vs_T_min", "value": valid_rsq["RSQ_lnP_vs_T"].min()},
    {"item": "RSQ_lnP_vs_T_max", "value": valid_rsq["RSQ_lnP_vs_T"].max()},

    {"item": "RSQ_lnP_vs_invT_mean", "value": valid_rsq["RSQ_lnP_vs_invT"].mean()},
    {"item": "RSQ_lnP_vs_invT_median", "value": valid_rsq["RSQ_lnP_vs_invT"].median()},
    {"item": "RSQ_lnP_vs_invT_min", "value": valid_rsq["RSQ_lnP_vs_invT"].min()},
    {"item": "RSQ_lnP_vs_invT_max", "value": valid_rsq["RSQ_lnP_vs_invT"].max()},

    {"item": "slope_P_vs_T_mean", "value": valid_rsq["slope_P_vs_T"].mean()},
    {"item": "slope_P_vs_T_median", "value": valid_rsq["slope_P_vs_T"].median()},
    {"item": "slope_lnP_vs_invT_mean", "value": valid_rsq["slope_lnP_vs_invT"].mean()},
    {"item": "slope_lnP_vs_invT_median", "value": valid_rsq["slope_lnP_vs_invT"].median()},
])


# =========================
# 10. 保存 Excel
# =========================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_with_rsq.to_excel(writer, sheet_name="Data_With_RSQ", index=False)
    df_rsq.to_excel(writer, sheet_name="Material_RSQ", index=False)
    df_low_rsq.to_excel(writer, sheet_name="Low_RSQ_Materials", index=False)

    df_negative_slope_P_T.to_excel(
        writer,
        sheet_name="Negative_Slope_P_vs_T",
        index=False
    )

    df_positive_slope_lnP_invT.to_excel(
        writer,
        sheet_name="Positive_Slope_lnP_invT",
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


print("\n保存完成:", output_file)

print("\n物质数量:", df_rsq["material_key"].nunique())
print("有效 RSQ 物质数量:", len(valid_rsq))
print("RSQ_lnP_vs_invT 低于", rsq_threshold, "的物质数量:", len(df_low_rsq))
print("P vs T 斜率 < 0 的物质数量:", len(df_negative_slope_P_T))
print("lnP vs 1/T 斜率 > 0 的物质数量:", len(df_positive_slope_lnP_invT))

print("\nRSQ_lnP_vs_invT 描述统计:")
print(valid_rsq["RSQ_lnP_vs_invT"].describe())

print("\n所有物质平均 RSQ_lnP_vs_invT:")
print(valid_rsq["RSQ_lnP_vs_invT"].mean())

print("\nRSQ_lnP_vs_invT 最低的前 20 个物质:")
show_cols = [
    "compound_name",
    "cas",
    "formula",
    "phase",
    "property_name",
    "n_points",
    "T_range",
    "VaporPressure_min_kPa",
    "VaporPressure_max_kPa",
    "lnP_min_kPa",
    "lnP_max_kPa",
    "RSQ_P_vs_T",
    "RSQ_lnP_vs_T",
    "RSQ_lnP_vs_invT",
    "slope_P_vs_T",
    "slope_lnP_vs_invT",
    "slope_direction_P_vs_T",
    "slope_direction_lnP_vs_invT"
]

show_cols = [c for c in show_cols if c in df_rsq.columns]

print(df_rsq[show_cols].head(20))