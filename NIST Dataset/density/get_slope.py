import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error


# =========================================================
# 1. 输入输出文件
# =========================================================
input_file = Path("dataset_density_selected_by_two_k_with_density_T_interpolation_8points.xlsx")
output_file = Path("HistGB_submodels_predict_ref_density_Tb_and_slope.xlsx")

groups_sheet = "Groups_selected"
ref_sheet = "Interpolated_k1_k2"


# =========================================================
# 2. 列名设置
# =========================================================
material_key_col = "material_key"

# 前 220 个基团：第 3 列到第 222 列
n_group_features_to_use = 220
group_start_col_1based = 3
group_end_col_1based = 222

# density 两个参考点目标列候选
target_density_k1_candidates = [
    "Density_interp_at_k1Tb",
    "density_interp_at_k1Tb",
    "rho_interp_at_k1Tb",
    "Density_k1",
    "density_k1",
]

target_density_k2_candidates = [
    "Density_interp_at_k2Tb",
    "density_interp_at_k2Tb",
    "rho_interp_at_k2Tb",
    "Density_k2",
    "density_k2",
]

# Tb 目标列候选
target_Tb_candidates = [
    "boiling_T_K",
    "Tb_K",
    "boiling_point_K",
]

# 真实参考点温度列，用于反推出 k1/k2
T_k1_candidates = [
    "k1_times_boiling_T_K",
    "T_k1Tb",
    "T_k1_K",
    "ref_T1_K",
]

T_k2_candidates = [
    "k2_times_boiling_T_K",
    "T_k2Tb",
    "T_k2_K",
    "ref_T2_K",
]

random_state = 42


# =========================================================
# 3. HistGradientBoosting 参数
# =========================================================
hgb_max_iter = 1200
hgb_learning_rate = 0.03
hgb_max_leaf_nodes = 63
hgb_min_samples_leaf = 2
hgb_l2_regularization = 0.0
hgb_early_stopping = False


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


def find_first_existing_col(df, candidates, col_type):
    """
    先精确匹配，再小写匹配。
    """
    for col in candidates:
        if col in df.columns:
            return col

    lower_map = {str(c).lower(): c for c in df.columns}

    for col in candidates:
        if str(col).lower() in lower_map:
            return lower_map[str(col).lower()]

    raise ValueError(
        f"没有找到 {col_type} 列。\n"
        f"候选列名: {candidates}\n"
        f"当前列名: {list(df.columns)}"
    )


def identify_group_columns(df_groups, n=220):
    """
    固定读取第 3 列到第 222 列，共 220 个基团。
    """
    start_idx = group_start_col_1based - 1
    end_idx_exclusive = group_end_col_1based

    if len(df_groups.columns) < end_idx_exclusive:
        raise ValueError(
            f"Groups_selected 总列数为 {len(df_groups.columns)}，"
            f"不足以取第 {group_start_col_1based} 到第 {group_end_col_1based} 列。"
        )

    group_cols = list(df_groups.columns[start_idx:end_idx_exclusive])

    if len(group_cols) != n:
        raise ValueError(
            f"固定列位置识别到 {len(group_cols)} 个基团列，"
            f"但要求 {n} 个。请检查 group_end_col_1based。"
        )

    return group_cols


def calc_ard_percent(y_true, y_pred, eps=1e-12):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = (
        np.isfinite(y_true)
        & np.isfinite(y_pred)
        & (np.abs(y_true) > eps)
    )

    if mask.sum() == 0:
        return np.nan

    return float(
        np.mean(np.abs((y_pred[mask] - y_true[mask]) / y_true[mask])) * 100.0
    )


def calc_regression_metrics(y_true, y_pred, label):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = np.isfinite(y_true) & np.isfinite(y_pred)

    y_true = y_true[mask]
    y_pred = y_pred[mask]

    if len(y_true) == 0:
        return {
            "target": label,
            "n_samples": 0,
            "R2": np.nan,
            "MSE": np.nan,
            "RMSE": np.nan,
            "MAE": np.nan,
            "ARD_percent": np.nan,
        }

    mse = mean_squared_error(y_true, y_pred)

    return {
        "target": label,
        "n_samples": len(y_true),
        "R2": r2_score(y_true, y_pred),
        "MSE": mse,
        "RMSE": np.sqrt(mse),
        "MAE": mean_absolute_error(y_true, y_pred),
        "ARD_percent": calc_ard_percent(y_true, y_pred),
    }


def train_hgb_submodel(X, y, target_name):
    """
    全数据训练，全数据预测。
    """
    model = HistGradientBoostingRegressor(
        loss="squared_error",
        max_iter=hgb_max_iter,
        learning_rate=hgb_learning_rate,
        max_leaf_nodes=hgb_max_leaf_nodes,
        min_samples_leaf=hgb_min_samples_leaf,
        l2_regularization=hgb_l2_regularization,
        early_stopping=hgb_early_stopping,
        random_state=random_state,
    )

    model.fit(X, y)
    y_pred = model.predict(X)

    metrics = calc_regression_metrics(y, y_pred, target_name)

    return model, y_pred, metrics


# =========================================================
# 5. 读取数据
# =========================================================
if not input_file.exists():
    raise FileNotFoundError(f"没有找到输入文件: {input_file}")

xls = pd.ExcelFile(input_file)

print("输入文件包含的 sheet:")
print(xls.sheet_names)

if groups_sheet not in xls.sheet_names:
    raise ValueError(f"没有找到 sheet: {groups_sheet}")

if ref_sheet not in xls.sheet_names:
    raise ValueError(f"没有找到 sheet: {ref_sheet}")

df_groups = pd.read_excel(input_file, sheet_name=groups_sheet)
df_ref = pd.read_excel(input_file, sheet_name=ref_sheet)

print("\nGroups_selected 物质数:", len(df_groups))
print("Interpolated_k1_k2 物质数:", len(df_ref))


# =========================================================
# 6. 检查 material_key
# =========================================================
if material_key_col not in df_groups.columns:
    df_groups[material_key_col] = df_groups.apply(build_material_key, axis=1)

if material_key_col not in df_ref.columns:
    df_ref[material_key_col] = df_ref.apply(build_material_key, axis=1)

df_groups[material_key_col] = df_groups[material_key_col].astype(str).str.strip()
df_ref[material_key_col] = df_ref[material_key_col].astype(str).str.strip()


# =========================================================
# 7. 自动识别目标列和参考温度列
# =========================================================
target_density_k1_col = find_first_existing_col(
    df_ref,
    target_density_k1_candidates,
    "k1 参考点 density"
)

target_density_k2_col = find_first_existing_col(
    df_ref,
    target_density_k2_candidates,
    "k2 参考点 density"
)

target_Tb_col = find_first_existing_col(
    df_ref,
    target_Tb_candidates,
    "boiling temperature"
)

T_k1_col = find_first_existing_col(
    df_ref,
    T_k1_candidates,
    "k1 参考温度"
)

T_k2_col = find_first_existing_col(
    df_ref,
    T_k2_candidates,
    "k2 参考温度"
)

print("\n使用 k1 density 目标列:", target_density_k1_col)
print("使用 k2 density 目标列:", target_density_k2_col)
print("使用 Tb 目标列:", target_Tb_col)
print("使用 k1 参考温度列:", T_k1_col)
print("使用 k2 参考温度列:", T_k2_col)

required_ref_cols = [
    target_density_k1_col,
    target_density_k2_col,
    target_Tb_col,
    T_k1_col,
    T_k2_col,
]

for col in required_ref_cols:
    df_ref[col] = pd.to_numeric(df_ref[col], errors="coerce")


# =========================================================
# 8. 读取 k1 / k2
# =========================================================
valid_k = df_ref[
    df_ref[target_Tb_col].notna()
    & (df_ref[target_Tb_col] > 0)
    & df_ref[T_k1_col].notna()
    & df_ref[T_k2_col].notna()
].copy()

if len(valid_k) == 0:
    raise ValueError("无法从 Interpolated_k1_k2 中反推出 k1/k2。")

k1 = float((valid_k[T_k1_col] / valid_k[target_Tb_col]).median())
k2 = float((valid_k[T_k2_col] / valid_k[target_Tb_col]).median())

print("\n使用 k1:", f"{k1:.10f}")
print("使用 k2:", f"{k2:.10f}")


# =========================================================
# 9. 构造基团输入特征
# =========================================================
group_cols_220 = identify_group_columns(
    df_groups,
    n=n_group_features_to_use
)

print("\n前 220 个基团列数量:", len(group_cols_220))
print("第一个基团列:", group_cols_220[0])
print("第 220 个基团列:", group_cols_220[-1])

for col in group_cols_220:
    df_groups[col] = pd.to_numeric(df_groups[col], errors="coerce").fillna(0.0)

# 删除全零基团列
nonzero_group_cols = [
    col for col in group_cols_220
    if not np.isclose(df_groups[col].abs().sum(), 0.0)
]

removed_zero_group_cols = [
    col for col in group_cols_220
    if col not in nonzero_group_cols
]

print("\n删除全零基团列数量:", len(removed_zero_group_cols))
print("保留非零基团列数量:", len(nonzero_group_cols))

if len(nonzero_group_cols) == 0:
    raise ValueError("前 220 个基团列全部为零，无法训练子模型。")


# =========================================================
# 10. 合并基团和参考点目标
# =========================================================
df_group_features = df_groups[
    [material_key_col] + nonzero_group_cols
].drop_duplicates(subset=[material_key_col]).copy()

ref_keep_cols = [
    material_key_col,
    target_density_k1_col,
    target_density_k2_col,
    target_Tb_col,
    T_k1_col,
    T_k2_col,
]

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
    "critical_T_K",
]:
    if col in df_ref.columns:
        ref_keep_cols.append(col)

df_ref_targets = df_ref[ref_keep_cols].drop_duplicates(subset=[material_key_col]).copy()

df_submodel = df_ref_targets.merge(
    df_group_features,
    on=material_key_col,
    how="left"
)

print("\n合并后物质数:", len(df_submodel))

before_drop = len(df_submodel)

df_submodel_clean = df_submodel.dropna(
    subset=nonzero_group_cols + [
        target_density_k1_col,
        target_density_k2_col,
        target_Tb_col,
    ]
).copy()

df_submodel_clean = df_submodel_clean[
    np.isfinite(df_submodel_clean[target_density_k1_col])
    & np.isfinite(df_submodel_clean[target_density_k2_col])
    & np.isfinite(df_submodel_clean[target_Tb_col])
    & (df_submodel_clean[target_density_k1_col] > 0)
    & (df_submodel_clean[target_density_k2_col] > 0)
    & (df_submodel_clean[target_Tb_col] > 0)
].copy()

print("删除无法训练子模型的物质数:", before_drop - len(df_submodel_clean))
print("最终用于训练三个子模型的物质数:", len(df_submodel_clean))

if len(df_submodel_clean) == 0:
    raise ValueError("清理后没有可用于训练子模型的物质。")


# =========================================================
# 11. 训练三个 HistGradientBoosting 子模型
# =========================================================
X = df_submodel_clean[nonzero_group_cols].values

# 三个目标：
# 1. Nk -> Density_k1
# 2. Nk -> Density_k2
# 3. Nk -> Tb
y_density_k1 = df_submodel_clean[target_density_k1_col].values
y_density_k2 = df_submodel_clean[target_density_k2_col].values
y_Tb = df_submodel_clean[target_Tb_col].values

model_density_k1, pred_density_k1, metrics_density_k1 = train_hgb_submodel(
    X,
    y_density_k1,
    "Density_interp_at_k1Tb"
)

model_density_k2, pred_density_k2, metrics_density_k2 = train_hgb_submodel(
    X,
    y_density_k2,
    "Density_interp_at_k2Tb"
)

model_Tb, pred_Tb, metrics_Tb = train_hgb_submodel(
    X,
    y_Tb,
    "boiling_T_K"
)

df_metrics = pd.DataFrame([
    metrics_density_k1,
    metrics_density_k2,
    metrics_Tb,
])


# =========================================================
# 12. 用三个子模型预测结果组合 slope
# =========================================================
df_slope = df_submodel_clean[
    [
        material_key_col,
        target_density_k1_col,
        target_density_k2_col,
        target_Tb_col,
        T_k1_col,
        T_k2_col,
    ] + [
        c for c in [
            "compound_name",
            "cas",
            "formula",
            "SMILES",
            "smiles",
            "final_smiles",
            "inchikey",
            "pubchem_cid",
            "pubchem_iupac_name",
            "critical_T_K",
        ]
        if c in df_submodel_clean.columns
    ]
].copy()

# 三个子模型预测值
df_slope["Density_k1_pred_by_group_model"] = pred_density_k1
df_slope["Density_k2_pred_by_group_model"] = pred_density_k2
df_slope["boiling_T_K_pred_by_group_model"] = pred_Tb

# 由预测 Tb 生成预测参考温度
df_slope["k1"] = k1
df_slope["k2"] = k2

df_slope["T_k1_pred_K"] = (
    df_slope["k1"] * df_slope["boiling_T_K_pred_by_group_model"]
)

df_slope["T_k2_pred_K"] = (
    df_slope["k2"] * df_slope["boiling_T_K_pred_by_group_model"]
)

# 预测值组合 slope：这是后续主模型应该使用的 slope 特征
df_slope["delta_Density_pred"] = (
    df_slope["Density_k2_pred_by_group_model"]
    - df_slope["Density_k1_pred_by_group_model"]
)

df_slope["delta_T_pred_K"] = (
    df_slope["T_k2_pred_K"]
    - df_slope["T_k1_pred_K"]
)

df_slope["slope_pred_density_over_T"] = (
    df_slope["delta_Density_pred"] / df_slope["delta_T_pred_K"]
)

df_slope.loc[
    ~np.isfinite(df_slope["slope_pred_density_over_T"]),
    "slope_pred_density_over_T"
] = np.nan


# =========================================================
# 13. 仅作对照：真实参考点直接 slope
# 注意：后续建模如果要避免直接用插值答案，应使用 slope_pred_density_over_T
# =========================================================
df_slope["delta_Density_true_ref"] = (
    df_slope[target_density_k2_col]
    - df_slope[target_density_k1_col]
)

df_slope["delta_T_true_ref_K"] = (
    df_slope[T_k2_col]
    - df_slope[T_k1_col]
)

df_slope["slope_true_ref_density_over_T"] = (
    df_slope["delta_Density_true_ref"] / df_slope["delta_T_true_ref_K"]
)

df_slope.loc[
    ~np.isfinite(df_slope["slope_true_ref_density_over_T"]),
    "slope_true_ref_density_over_T"
] = np.nan

df_slope["slope_pred_sign"] = np.where(
    df_slope["slope_pred_density_over_T"] > 0,
    "positive",
    np.where(
        df_slope["slope_pred_density_over_T"] < 0,
        "negative",
        "zero_or_nan"
    )
)

df_slope["slope_true_ref_sign"] = np.where(
    df_slope["slope_true_ref_density_over_T"] > 0,
    "positive",
    np.where(
        df_slope["slope_true_ref_density_over_T"] < 0,
        "negative",
        "zero_or_nan"
    )
)


# =========================================================
# 14. 输出运行框统计
# =========================================================
print("\n" + "=" * 90)
print("三个 HistGradientBoosting density 子模型训练集内评价指标")
print("=" * 90)
print(df_metrics.to_string(index=False))

print("\n" + "=" * 90)
print("预测 slope 统计：slope_pred_density_over_T")
print("=" * 90)
print(df_slope["slope_pred_density_over_T"].describe())

print("\n" + "=" * 90)
print("真实参考点 slope 统计：slope_true_ref_density_over_T")
print("=" * 90)
print(df_slope["slope_true_ref_density_over_T"].describe())

print("\n" + "=" * 90)
print("预测 slope 符号统计")
print("=" * 90)
print(df_slope["slope_pred_sign"].value_counts(dropna=False))

print("\n" + "=" * 90)
print("真实参考点 slope 符号统计")
print("=" * 90)
print(df_slope["slope_true_ref_sign"].value_counts(dropna=False))


# =========================================================
# 15. 输出辅助表
# =========================================================
df_used_group_cols = pd.DataFrame({
    "used_group_col": nonzero_group_cols
})

df_removed_zero_group_cols = pd.DataFrame({
    "removed_zero_group_col": removed_zero_group_cols
})

df_run_info = pd.DataFrame([
    {"item": "input_file", "value": str(input_file)},
    {"item": "groups_sheet", "value": groups_sheet},
    {"item": "ref_sheet", "value": ref_sheet},
    {"item": "output_file", "value": str(output_file)},

    {"item": "submodel_type", "value": "HistGradientBoostingRegressor"},
    {"item": "submodel_input_features", "value": "first 220 group features after removing all-zero columns"},
    {"item": "submodel_1_target", "value": target_density_k1_col},
    {"item": "submodel_2_target", "value": target_density_k2_col},
    {"item": "submodel_3_target", "value": target_Tb_col},

    {"item": "k1", "value": k1},
    {"item": "k2", "value": k2},
    {
        "item": "slope_formula_pred",
        "value": "(Density_k2_pred - Density_k1_pred) / (k2*Tb_pred - k1*Tb_pred)"
    },
    {
        "item": "slope_formula_true_ref",
        "value": "(Density_k2_true_ref - Density_k1_true_ref) / (T_k2_true_ref - T_k1_true_ref)"
    },
    {"item": "slope_feature_for_main_model", "value": "slope_pred_density_over_T"},
    {"item": "slope_unit", "value": "kg/(m3*K) if density unit is kg/m3"},

    {"item": "n_group_features_requested", "value": n_group_features_to_use},
    {"item": "n_group_features_after_remove_zero", "value": len(nonzero_group_cols)},
    {"item": "n_removed_zero_group_cols", "value": len(removed_zero_group_cols)},

    {"item": "n_materials_before_dropna", "value": len(df_submodel)},
    {"item": "n_materials_used_for_submodels", "value": len(df_submodel_clean)},
    {"item": "train_test_split", "value": "None, all materials used for fitting and prediction"},

    {"item": "HistGB_max_iter", "value": hgb_max_iter},
    {"item": "HistGB_learning_rate", "value": hgb_learning_rate},
    {"item": "HistGB_max_leaf_nodes", "value": hgb_max_leaf_nodes},
    {"item": "HistGB_min_samples_leaf", "value": hgb_min_samples_leaf},
    {"item": "HistGB_l2_regularization", "value": hgb_l2_regularization},
    {"item": "HistGB_early_stopping", "value": hgb_early_stopping},
    {"item": "random_state", "value": random_state},
])


# =========================================================
# 16. 保存 Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_slope.to_excel(writer, sheet_name="slope", index=False)
    df_metrics.to_excel(writer, sheet_name="Submodel_Metrics", index=False)

    df_used_group_cols.to_excel(writer, sheet_name="Used_Group_Cols", index=False)
    df_removed_zero_group_cols.to_excel(writer, sheet_name="Removed_Zero_Group_Cols", index=False)
    df_run_info.to_excel(writer, sheet_name="Run_Info", index=False)

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
print("重点输出 sheet:")
print("1. Submodel_Metrics：三个子模型的训练集内评价指标")
print("2. slope：三个子模型预测值、预测 slope、真实参考点 slope 对照")
print("后续主模型建议使用的预测 slope 特征列: slope_pred_density_over_T")