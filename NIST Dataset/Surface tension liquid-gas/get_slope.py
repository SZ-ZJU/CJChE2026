# -*- coding: utf-8 -*-
"""
Surface tension liquid-gas 三个子模型预测参考点表面张力、Tb，并组合成 slope 的脚本

输入：
    dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points_with_RSQ.xlsx

如果该文件不存在，会自动尝试读取：
    dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points.xlsx

输出：
    HistGB_submodels_predict_ref_surface_Tb_and_slope.xlsx

功能：
    1. 读取 Groups_selected 和 Interpolated_k1_k2
    2. 使用前 220 个基团特征作为输入
    3. 训练三个 HistGradientBoostingRegressor 子模型：
        - 子模型 1：预测 SurfaceTension_N_m_interp_at_k1Tb
        - 子模型 2：预测 SurfaceTension_N_m_interp_at_k2Tb
        - 子模型 3：预测 boiling_T_K
    4. 由三个预测结果组合得到：
        slope_pred_surface_over_T
    5. 输出三个子模型的训练集内预测效果：
        R2, MSE, RMSE, MAE, ARD%, 1%/5%/10% 内点数
    6. 输出真实参考点 slope 和预测 slope 供后续主模型使用
"""

import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error


# =========================================================
# 1. 输入输出文件
# =========================================================

preferred_input_file = Path(
    "dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points_with_RSQ.xlsx"
)

fallback_input_file = Path(
    "dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points.xlsx"
)

if preferred_input_file.exists():
    input_file = preferred_input_file
elif fallback_input_file.exists():
    input_file = fallback_input_file
else:
    raise FileNotFoundError(
        "没有找到输入文件：\n"
        f"1. {preferred_input_file}\n"
        f"2. {fallback_input_file}"
    )

output_file = Path("HistGB_submodels_predict_ref_surface_Tb_and_slope.xlsx")

groups_sheet = "Groups_selected"
ref_sheet = "Interpolated_k1_k2"


# =========================================================
# 2. 列名设置
# =========================================================

material_key_col = "material_key"

# 前 220 个基团：默认第 3 列到第 222 列
# 如果列数不足，会自动转为基于数值列识别基团列
n_group_features_to_use = 220
group_start_col_1based = 3
group_end_col_1based = 222
use_fixed_group_position = True

# 三个子模型的目标列
target_surface_k1_col = "SurfaceTension_N_m_interp_at_k1Tb"
target_surface_k2_col = "SurfaceTension_N_m_interp_at_k2Tb"
target_Tb_col = "boiling_T_K"

# 参考温度列，用于反推 k1/k2
T_k1_col = "k1_times_boiling_T_K"
T_k2_col = "k2_times_boiling_T_K"

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
    """
    构造物质唯一标识。

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


def identify_group_columns(df_groups, n=220):
    """
    识别基团列。

    优先：
        固定读取第 3 列到第 222 列，共 220 个基团。
    如果固定位置不可用：
        自动识别数值型基团列，并排除明显元信息列。
    """
    if use_fixed_group_position:
        start_idx = group_start_col_1based - 1
        end_idx_exclusive = group_end_col_1based

        if len(df_groups.columns) >= end_idx_exclusive:
            group_cols = list(df_groups.columns[start_idx:end_idx_exclusive])

            if len(group_cols) == n:
                return group_cols

        print(
            "\n警告：固定位置基团列不可用，转为自动识别数值型基团列。"
        )

    metadata_keywords = [
        "material_key",
        "original_material_index",
        "compound",
        "cas",
        "formula",
        "smiles",
        "inchikey",
        "pubchem",
        "phase",
        "boiling",
        "temperature",
        "temp",
        "t_k",
        "pressure",
        "surface",
        "tension",
        "k1",
        "k2",
        "interp",
        "status",
        "range",
        "rsq",
        "slope",
        "title",
        "doi",
        "source",
        "index",
    ]

    candidate_cols = []

    for col in df_groups.columns:
        col_lower = str(col).strip().lower()

        if any(key in col_lower for key in metadata_keywords):
            continue

        numeric_values = pd.to_numeric(df_groups[col], errors="coerce")

        if numeric_values.notna().sum() == 0:
            continue

        candidate_cols.append(col)

    if len(candidate_cols) == 0:
        raise ValueError(
            "没有识别到任何有效基团列。请检查 Groups_selected。"
        )

    if len(candidate_cols) >= n:
        return candidate_cols[:n]

    print(
        f"\n警告：自动识别到的基团列只有 {len(candidate_cols)} 个，"
        f"少于设定的 {n} 个，将使用全部识别到的基团列。"
    )

    return candidate_cols


def calc_regression_metrics(y_true, y_pred, label):
    """
    回归指标：
        R2
        MSE
        RMSE
        MAE
        ARD%
        预测相对误差在 1%、5%、10% 内的点数
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    abs_err = np.abs(y_pred - y_true)

    valid_rel_mask = np.isfinite(y_true) & (np.abs(y_true) > 1e-12)
    rel_err = np.full_like(y_true, np.nan, dtype=float)
    rel_err[valid_rel_mask] = abs_err[valid_rel_mask] / np.abs(y_true[valid_rel_mask])

    return {
        "target": label,
        "n_samples": len(y_true),
        "R2": r2_score(y_true, y_pred) if len(y_true) >= 2 else np.nan,
        "MSE": mean_squared_error(y_true, y_pred),
        "RMSE": np.sqrt(mean_squared_error(y_true, y_pred)),
        "MAE": mean_absolute_error(y_true, y_pred),
        "ARD_percent": np.nanmean(rel_err) * 100.0,
        "num_within_1_percent": int(np.nansum(rel_err <= 0.01)),
        "num_within_5_percent": int(np.nansum(rel_err <= 0.05)),
        "num_within_10_percent": int(np.nansum(rel_err <= 0.10)),
    }


def train_hgb_submodel(X, y, target_name):
    """
    全数据训练，全数据预测。

    注意：
        这里与参考代码保持一致，不划分训练集/测试集。
        输出的是训练集内拟合效果，用于判断子模型能否学习基团到参考点性质的映射。
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

xls = pd.ExcelFile(input_file)

print("输入文件:", input_file)
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
# 7. 检查目标列
# =========================================================

required_ref_cols = [
    target_surface_k1_col,
    target_surface_k2_col,
    target_Tb_col,
    T_k1_col,
    T_k2_col,
]

missing_cols = [c for c in required_ref_cols if c not in df_ref.columns]

if missing_cols:
    raise ValueError(
        f"{ref_sheet} 中缺少必要列: {missing_cols}\n"
        f"当前列名: {list(df_ref.columns)}"
    )

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

group_cols_raw = identify_group_columns(
    df_groups,
    n=n_group_features_to_use
)

print("\n识别到的候选基团列数量:", len(group_cols_raw))
print("第一个候选基团列:", group_cols_raw[0])
print("最后一个候选基团列:", group_cols_raw[-1])

for col in group_cols_raw:
    df_groups[col] = pd.to_numeric(df_groups[col], errors="coerce").fillna(0.0)

# 删除全零基团列
nonzero_group_cols = [
    col for col in group_cols_raw
    if not np.isclose(df_groups[col].abs().sum(), 0.0)
]

removed_zero_group_cols = [
    col for col in group_cols_raw
    if col not in nonzero_group_cols
]

print("\n删除全零基团列数量:", len(removed_zero_group_cols))
print("保留非零基团列数量:", len(nonzero_group_cols))

if len(nonzero_group_cols) == 0:
    raise ValueError("基团列全部为零，无法训练子模型。")


# =========================================================
# 10. 合并基团和参考点目标
# =========================================================

df_group_features = df_groups[
    [material_key_col] + nonzero_group_cols
].drop_duplicates(subset=[material_key_col]).copy()

ref_keep_cols = [
    material_key_col,
    target_surface_k1_col,
    target_surface_k2_col,
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
    "pubchem_inchikey",
    "RSQ_Surface_vs_T",
    "slope_Surface_vs_T",
    "title",
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
        target_surface_k1_col,
        target_surface_k2_col,
        target_Tb_col,
    ]
).copy()

df_submodel_clean = df_submodel_clean[
    np.isfinite(df_submodel_clean[target_surface_k1_col])
    & np.isfinite(df_submodel_clean[target_surface_k2_col])
    & np.isfinite(df_submodel_clean[target_Tb_col])
    & (df_submodel_clean[target_surface_k1_col] > 0)
    & (df_submodel_clean[target_surface_k2_col] > 0)
    & (df_submodel_clean[target_Tb_col] > 0)
].copy()

print("删除无法训练子模型的物质数:", before_drop - len(df_submodel_clean))
print("最终用于训练三个子模型的物质数:", len(df_submodel_clean))

if len(df_submodel_clean) == 0:
    raise ValueError("清理后没有可用于训练子模型的物质。")


# =========================================================
# 11. 训练三个 HistGradientBoosting 子模型，不划分训练集测试集
# =========================================================

X = df_submodel_clean[nonzero_group_cols].values

y_surface_k1 = df_submodel_clean[target_surface_k1_col].values
y_surface_k2 = df_submodel_clean[target_surface_k2_col].values
y_Tb = df_submodel_clean[target_Tb_col].values

model_surface_k1, pred_surface_k1, metrics_surface_k1 = train_hgb_submodel(
    X,
    y_surface_k1,
    "SurfaceTension_N_m_interp_at_k1Tb"
)

model_surface_k2, pred_surface_k2, metrics_surface_k2 = train_hgb_submodel(
    X,
    y_surface_k2,
    "SurfaceTension_N_m_interp_at_k2Tb"
)

model_Tb, pred_Tb, metrics_Tb = train_hgb_submodel(
    X,
    y_Tb,
    "boiling_T_K"
)

df_metrics = pd.DataFrame([
    metrics_surface_k1,
    metrics_surface_k2,
    metrics_Tb,
])


# =========================================================
# 12. 用三个子模型预测结果组合 slope
# =========================================================

meta_cols = [
    material_key_col,
    target_surface_k1_col,
    target_surface_k2_col,
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
    "pubchem_inchikey",
    "RSQ_Surface_vs_T",
    "slope_Surface_vs_T",
    "title",
]:
    if col in df_submodel_clean.columns:
        meta_cols.append(col)

df_slope = df_submodel_clean[meta_cols].copy()

# 三个子模型预测值
df_slope["surface_k1_pred_by_group_model"] = pred_surface_k1
df_slope["surface_k2_pred_by_group_model"] = pred_surface_k2
df_slope["boiling_T_K_pred_by_group_model"] = pred_Tb

# 由预测 Tb 生成预测参考温度
df_slope["k1"] = k1
df_slope["k2"] = k2

df_slope["T_k1_pred_K"] = df_slope["k1"] * df_slope["boiling_T_K_pred_by_group_model"]
df_slope["T_k2_pred_K"] = df_slope["k2"] * df_slope["boiling_T_K_pred_by_group_model"]

df_slope["delta_surface_pred"] = (
    df_slope["surface_k2_pred_by_group_model"]
    - df_slope["surface_k1_pred_by_group_model"]
)

df_slope["delta_T_pred_K"] = (
    df_slope["T_k2_pred_K"]
    - df_slope["T_k1_pred_K"]
)

df_slope["slope_pred_surface_over_T"] = (
    df_slope["delta_surface_pred"] / df_slope["delta_T_pred_K"]
)

df_slope.loc[
    ~np.isfinite(df_slope["slope_pred_surface_over_T"]),
    "slope_pred_surface_over_T"
] = np.nan


# =========================================================
# 13. 真实参考点 slope，用于对照
# =========================================================

df_slope["delta_surface_true_ref"] = (
    df_slope[target_surface_k2_col]
    - df_slope[target_surface_k1_col]
)

df_slope["delta_T_true_ref_K"] = (
    df_slope[T_k2_col]
    - df_slope[T_k1_col]
)

df_slope["slope_true_ref_surface_over_T"] = (
    df_slope["delta_surface_true_ref"] / df_slope["delta_T_true_ref_K"]
)

df_slope.loc[
    ~np.isfinite(df_slope["slope_true_ref_surface_over_T"]),
    "slope_true_ref_surface_over_T"
] = np.nan


# =========================================================
# 14. slope 预测效果评价
# =========================================================

valid_slope_mask = (
    df_slope["slope_true_ref_surface_over_T"].notna()
    & df_slope["slope_pred_surface_over_T"].notna()
    & np.isfinite(df_slope["slope_true_ref_surface_over_T"])
    & np.isfinite(df_slope["slope_pred_surface_over_T"])
)

if valid_slope_mask.sum() >= 2:
    slope_metrics = calc_regression_metrics(
        df_slope.loc[valid_slope_mask, "slope_true_ref_surface_over_T"].values,
        df_slope.loc[valid_slope_mask, "slope_pred_surface_over_T"].values,
        "slope_surface_over_T"
    )
else:
    slope_metrics = {
        "target": "slope_surface_over_T",
        "n_samples": int(valid_slope_mask.sum()),
        "R2": np.nan,
        "MSE": np.nan,
        "RMSE": np.nan,
        "MAE": np.nan,
        "ARD_percent": np.nan,
        "num_within_1_percent": 0,
        "num_within_5_percent": 0,
        "num_within_10_percent": 0,
    }

df_slope_metrics = pd.DataFrame([slope_metrics])

df_all_metrics = pd.concat(
    [
        df_metrics,
        df_slope_metrics,
    ],
    ignore_index=True
)


# =========================================================
# 15. 控制台输出统计
# =========================================================

print("\n" + "=" * 100)
print("三个 HistGradientBoosting 子模型训练集内评价指标")
print("=" * 100)
print(df_metrics.to_string(index=False))

print("\n" + "=" * 100)
print("组合 slope 评价指标")
print("=" * 100)
print(df_slope_metrics.to_string(index=False))

print("\n" + "=" * 100)
print("预测 slope 统计：slope_pred_surface_over_T，单位 N/m/K")
print("=" * 100)
print(df_slope["slope_pred_surface_over_T"].describe())

print("\n" + "=" * 100)
print("真实参考点 slope 统计：slope_true_ref_surface_over_T，单位 N/m/K")
print("=" * 100)
print(df_slope["slope_true_ref_surface_over_T"].describe())

print("\n" + "=" * 100)
print("表面张力 slope 方向统计")
print("=" * 100)
print("预测 slope < 0 的数量:", int((df_slope["slope_pred_surface_over_T"] < 0).sum()))
print("预测 slope > 0 的数量:", int((df_slope["slope_pred_surface_over_T"] > 0).sum()))
print("真实 slope < 0 的数量:", int((df_slope["slope_true_ref_surface_over_T"] < 0).sum()))
print("真实 slope > 0 的数量:", int((df_slope["slope_true_ref_surface_over_T"] > 0).sum()))


# =========================================================
# 16. 输出辅助表
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
    {
        "item": "submodel_input_features",
        "value": "first 220 group features or automatically detected numeric group columns after removing all-zero columns",
    },
    {"item": "submodel_1_target", "value": target_surface_k1_col},
    {"item": "submodel_2_target", "value": target_surface_k2_col},
    {"item": "submodel_3_target", "value": target_Tb_col},

    {"item": "k1", "value": k1},
    {"item": "k2", "value": k2},
    {
        "item": "slope_formula",
        "value": "(surface_k2_pred - surface_k1_pred) / (k2*Tb_pred - k1*Tb_pred)",
    },
    {"item": "slope_unit", "value": "N/m/K"},

    {"item": "n_group_features_requested", "value": n_group_features_to_use},
    {"item": "n_group_features_raw_identified", "value": len(group_cols_raw)},
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
# 17. 保存 Excel
# =========================================================

with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_slope.to_excel(writer, sheet_name="slope", index=False)
    df_metrics.to_excel(writer, sheet_name="Submodel_Metrics", index=False)
    df_slope_metrics.to_excel(writer, sheet_name="Slope_Metrics", index=False)
    df_all_metrics.to_excel(writer, sheet_name="All_Metrics", index=False)

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

            ws.column_dimensions[col_letter].width = min(max_length + 2, 40)


print("\n保存完成:", output_file)
print("重点输出 sheet:")
print("1. slope")
print("2. Submodel_Metrics")
print("3. Slope_Metrics")
print("4. All_Metrics")
print("\n后续主模型建议使用的 slope 特征列:")
print("slope_pred_surface_over_T")