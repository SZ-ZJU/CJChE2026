import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error


pd.set_option("display.float_format", "{:.10f}".format)
np.set_printoptions(suppress=True, precision=10)


# =========================================================
# 1. 输入输出文件
# =========================================================
input_file = Path("Cp_dataset_selected_by_two_k_with_interpolation.xlsx")

target_sheet = "Interpolated_k1_k2"
groups_sheet = "groups_selected"

output_file = Path("Group_prediction_for_k1_k2_boiling_GBDT_fixed_params.xlsx")


# =========================================================
# 2. 目标列
# =========================================================
target_cols = [
    "property_interp_at_k1Tb",
    "property_interp_at_k2Tb",
    "boiling_T_K",
]


# =========================================================
# 3. groups 中基团列范围
# =========================================================
# groups_selected 前面通常插入了 original_material_index。
# 如果原始 groups 表基团列是 columns[2:221]，
# 插入 original_material_index 后，通常变成 columns[3:222]。
group_start_idx = 3
group_end_idx = 222


# =========================================================
# 4. GBDT 模型参数
# =========================================================
gbdt_params = {
    "n_estimators": 200,
    "learning_rate": 0.1,
    "max_depth": 5,
    "random_state": 42,
}


# =========================================================
# 5. 读取数据
# =========================================================
df_target = pd.read_excel(input_file, sheet_name=target_sheet)
df_groups = pd.read_excel(input_file, sheet_name=groups_sheet)

print("target sheet 行数:", len(df_target))
print("groups sheet 行数:", len(df_groups))

for col in target_cols:
    if col not in df_target.columns:
        raise ValueError(f"{target_sheet} 中没有找到目标列: {col}")

if group_end_idx > len(df_groups.columns):
    raise ValueError(
        f"group_end_idx={group_end_idx} 超过 groups sheet 总列数 {len(df_groups.columns)}。"
        "请检查 group_start_idx / group_end_idx。"
    )


# =========================================================
# 6. 读取基团列
# =========================================================
group_cols_raw = df_groups.columns[group_start_idx:group_end_idx].tolist()

exclude_cols = {
    "original_material_index",
    "compound_name",
    "cas",
    "formula",
    "SMILES",
    "smiles",
    "pubchem_cid",
    "material_key",
    "phase",
    "boiling_T_K",
    "critical_T_K",
}

group_cols_raw = [c for c in group_cols_raw if c not in exclude_cols]

print("\n原始选取基团列数量:", len(group_cols_raw))
print("前 10 个基团列名:", group_cols_raw[:10])


# =========================================================
# 7. 对齐 target 和 groups
# =========================================================
if "original_material_index" in df_target.columns and "original_material_index" in df_groups.columns:
    df_groups_part = df_groups[["original_material_index"] + group_cols_raw].copy()

    df_model = df_target.merge(
        df_groups_part,
        on="original_material_index",
        how="inner",
        validate="one_to_one"
    )

    print("\n使用 original_material_index 对齐。")
    print("对齐后数据行数:", len(df_model))

else:
    if len(df_target) != len(df_groups):
        raise ValueError(
            "没有 original_material_index 可用于对齐，且两个 sheet 行数不一致。"
        )

    df_model = df_target.copy()

    for col in group_cols_raw:
        df_model[col] = df_groups[col].values

    print("\n没有 original_material_index，按行顺序对齐。")


# =========================================================
# 8. 构造 X 和 Y
# =========================================================
df_X_raw = df_model[group_cols_raw].copy()
df_X_raw = df_X_raw.apply(pd.to_numeric, errors="coerce").fillna(0.0)

df_Y = df_model[target_cols].copy()
df_Y = df_Y.apply(pd.to_numeric, errors="coerce")

# 删除目标列中有缺失值的物质
valid_y_mask = df_Y.notna().all(axis=1)

df_model_valid = df_model.loc[valid_y_mask].reset_index(drop=True)
df_X_raw = df_X_raw.loc[valid_y_mask].reset_index(drop=True)
df_Y = df_Y.loc[valid_y_mask].reset_index(drop=True)

print("\n删除目标缺失后的物质数:", len(df_model_valid))

if len(df_model_valid) == 0:
    raise ValueError("没有有效目标数据，无法建模。")


# =========================================================
# 9. 删除全零基团列
# =========================================================
nonzero_mask = df_X_raw.abs().sum(axis=0) != 0

used_group_cols = df_X_raw.columns[nonzero_mask].tolist()
removed_zero_group_cols = df_X_raw.columns[~nonzero_mask].tolist()

df_X = df_X_raw[used_group_cols].copy()

print("删除全零列后基团数量:", len(used_group_cols))
print("被删除全零基团数量:", len(removed_zero_group_cols))

X = df_X.values.astype(float)
Y = df_Y.values.astype(float)

print("X shape:", X.shape)
print("Y shape:", Y.shape)


# =========================================================
# 10. 分别训练 3 个 GBDT 模型
# =========================================================
models = {}
Y_pred = np.zeros_like(Y, dtype=float)

for j, target in enumerate(target_cols):
    print(f"\n正在训练 GBDT 目标: {target}")

    model = GradientBoostingRegressor(**gbdt_params)
    model.fit(X, Y[:, j])

    Y_pred[:, j] = model.predict(X)
    models[target] = model


# =========================================================
# 11. 评价指标
# =========================================================
def calc_metrics(y_true, y_pred, target_name):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    error = y_pred - y_true
    abs_error = np.abs(error)

    valid_mask = np.abs(y_true) > 1e-12

    if valid_mask.sum() > 0:
        relative_error_percent = np.abs(
            (y_pred[valid_mask] - y_true[valid_mask]) / y_true[valid_mask]
        ) * 100

        ard = np.mean(relative_error_percent)
        max_relative_error = np.max(relative_error_percent)

        ratio_le_1 = np.mean(relative_error_percent <= 1) * 100
        ratio_le_5 = np.mean(relative_error_percent <= 5) * 100
        ratio_le_10 = np.mean(relative_error_percent <= 10) * 100
    else:
        ard = np.nan
        max_relative_error = np.nan
        ratio_le_1 = np.nan
        ratio_le_5 = np.nan
        ratio_le_10 = np.nan

    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_true, y_pred)

    try:
        r2 = r2_score(y_true, y_pred)
    except Exception:
        r2 = np.nan

    return {
        "target": target_name,
        "n_points": len(y_true),
        "R2_all": r2,
        "MSE": mse,
        "RMSE": rmse,
        "MAE": mae,
        "ARD_percent": ard,
        "max_abs_error": np.max(abs_error),
        "max_relative_error_percent": max_relative_error,
        "relative_error_le_1_percent_ratio": ratio_le_1,
        "relative_error_le_5_percent_ratio": ratio_le_5,
        "relative_error_le_10_percent_ratio": ratio_le_10,
    }


metrics_rows = []

for j, target in enumerate(target_cols):
    metrics_rows.append(
        calc_metrics(
            Y[:, j],
            Y_pred[:, j],
            target
        )
    )

df_metrics = pd.DataFrame(metrics_rows)

print("\n================ GBDT 拟合评价指标 ================")
print(df_metrics.to_string(index=False))


# =========================================================
# 12. 预测结果表
# =========================================================
df_prediction = pd.DataFrame()

info_cols = [
    "original_material_index",
    "compound_name",
    "cas",
    "formula",
    "SMILES",
    "smiles",
    "pubchem_cid",
    "material_key",
    "phase",
    "k1",
    "k1_times_boiling_T_K",
    "k2",
    "k2_times_boiling_T_K",
]

for col in info_cols:
    if col in df_model_valid.columns:
        df_prediction[col] = df_model_valid[col].values

for j, target in enumerate(target_cols):
    df_prediction[f"{target}_exp"] = Y[:, j]
    df_prediction[f"{target}_pred"] = Y_pred[:, j]
    df_prediction[f"{target}_error"] = Y_pred[:, j] - Y[:, j]
    df_prediction[f"{target}_abs_error"] = np.abs(Y_pred[:, j] - Y[:, j])
    df_prediction[f"{target}_relative_error_percent"] = np.where(
        np.abs(Y[:, j]) > 1e-12,
        np.abs((Y_pred[:, j] - Y[:, j]) / Y[:, j]) * 100,
        np.nan
    )


# =========================================================
# 13. 特征重要性
# =========================================================
df_feature_importance = pd.DataFrame({
    "group_name": used_group_cols,
    "occurrence_material_count": (df_X != 0).sum(axis=0).values,
    "total_count": df_X.sum(axis=0).values,
})

for target in target_cols:
    model = models[target]
    df_feature_importance[f"importance_for_{target}"] = model.feature_importances_

importance_cols = [f"importance_for_{target}" for target in target_cols]

df_feature_importance["importance_sum"] = df_feature_importance[importance_cols].sum(axis=1)

df_feature_importance = df_feature_importance.sort_values(
    "importance_sum",
    ascending=False
).reset_index(drop=True)


# =========================================================
# 14. 模型参数和基团统计
# =========================================================
df_model_params = pd.DataFrame([
    {"parameter": k, "value": v}
    for k, v in gbdt_params.items()
])

df_model_params = pd.concat([
    pd.DataFrame([
        {"parameter": "model", "value": "GradientBoostingRegressor"},
        {"parameter": "n_samples", "value": X.shape[0]},
        {"parameter": "n_features", "value": X.shape[1]},
        {"parameter": "n_targets", "value": Y.shape[1]},
    ]),
    df_model_params
], axis=0).reset_index(drop=True)

df_used_groups = pd.DataFrame({
    "used_group": used_group_cols,
    "occurrence_material_count": (df_X != 0).sum(axis=0).values,
    "total_count": df_X.sum(axis=0).values,
})

df_removed_zero_groups = pd.DataFrame({
    "removed_all_zero_group": removed_zero_group_cols
})


# =========================================================
# 15. 保存 Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_prediction.to_excel(writer, sheet_name="Prediction", index=False)
    df_metrics.to_excel(writer, sheet_name="Metrics", index=False)
    df_feature_importance.to_excel(writer, sheet_name="Feature_Importance", index=False)
    df_model_params.to_excel(writer, sheet_name="GBDT_Params", index=False)
    df_used_groups.to_excel(writer, sheet_name="Used_Groups", index=False)
    df_removed_zero_groups.to_excel(writer, sheet_name="Removed_All_Zero_Groups", index=False)

    # 保存实际参与建模的数据，方便检查
    df_model_valid.to_excel(writer, sheet_name="Modeling_Data", index=False)

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
print("建模物质数:", len(df_model_valid))
print("使用基团数:", len(used_group_cols))
print("预测目标:", target_cols)
print("模型: GradientBoostingRegressor")