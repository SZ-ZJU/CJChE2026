import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.kernel_ridge import KernelRidge
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error


pd.set_option("display.float_format", "{:.10f}".format)
np.set_printoptions(suppress=True, precision=10)


# =========================================================
# 1. 输入输出文件
# =========================================================
input_file = Path("Cp_dataset_selected_by_two_k_with_interpolation.xlsx")

target_sheet = "Interpolated_k1_k2"
groups_sheet = "groups_selected"

output_file = Path("Group_prediction_for_k1_k2_boiling_KernelRidge.xlsx")


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
# groups_selected 前面插入了 original_material_index。
# 如果原始 groups 表基团列是 columns[2:221]，
# 插入 original_material_index 后，通常变成 columns[3:222]。
group_start_idx = 3
group_end_idx = 222     # 不包含 end


# =========================================================
# 4. Kernel Ridge 超参数范围
# =========================================================
# alpha 越大，正则越强，模型越平滑
alpha_grid = np.logspace(-4, 4, 25)

# gamma 控制 RBF 核宽度
# gamma 太大容易过拟合，太小容易欠拟合
gamma_grid = np.logspace(-5, 1, 25)

n_splits = 5
random_state = 42


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

# 删除全零基团列
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
# 9. KFold 选择 alpha 和 gamma
# =========================================================
n_samples = X.shape[0]

if n_samples < 5:
    n_splits_effective = max(2, n_samples)
else:
    n_splits_effective = min(n_splits, n_samples)

kf = KFold(
    n_splits=n_splits_effective,
    shuffle=True,
    random_state=random_state
)

cv_rows = []

print("\n开始 Kernel Ridge 超参数搜索...")

for alpha in alpha_grid:
    for gamma in gamma_grid:
        fold_mse_scaled_list = []
        fold_r2_list = []

        for train_idx, val_idx in kf.split(X):
            X_train = X[train_idx]
            X_val = X[val_idx]

            Y_train = Y[train_idx]
            Y_val = Y[val_idx]

            # X 标准化
            x_scaler = StandardScaler()
            X_train_scaled = x_scaler.fit_transform(X_train)
            X_val_scaled = x_scaler.transform(X_val)

            # Y 也标准化，避免 boiling_T_K 数值尺度主导损失
            y_scaler = StandardScaler()
            Y_train_scaled = y_scaler.fit_transform(Y_train)
            Y_val_scaled = y_scaler.transform(Y_val)

            model = KernelRidge(
                kernel="rbf",
                alpha=alpha,
                gamma=gamma
            )

            model.fit(X_train_scaled, Y_train_scaled)

            Y_val_pred_scaled = model.predict(X_val_scaled)
            Y_val_pred = y_scaler.inverse_transform(Y_val_pred_scaled)

            # 用标准化空间 MSE 选参数，三个目标权重相近
            fold_mse_scaled = mean_squared_error(Y_val_scaled, Y_val_pred_scaled)
            fold_mse_scaled_list.append(fold_mse_scaled)

            # 原始空间整体 R2 只是辅助参考
            try:
                fold_r2 = r2_score(Y_val, Y_val_pred, multioutput="uniform_average")
            except Exception:
                fold_r2 = np.nan

            fold_r2_list.append(fold_r2)

        cv_rows.append({
            "alpha": alpha,
            "gamma": gamma,
            "cv_mse_scaled_mean": np.mean(fold_mse_scaled_list),
            "cv_mse_scaled_std": np.std(fold_mse_scaled_list),
            "cv_r2_original_mean": np.nanmean(fold_r2_list),
            "cv_r2_original_std": np.nanstd(fold_r2_list),
        })

df_cv = pd.DataFrame(cv_rows)

df_cv = df_cv.sort_values(
    ["cv_mse_scaled_mean", "alpha"],
    ascending=[True, True]
).reset_index(drop=True)

best_alpha = float(df_cv.loc[0, "alpha"])
best_gamma = float(df_cv.loc[0, "gamma"])

print("\n========== 最优参数 ==========")
print("best_alpha:", f"{best_alpha:.10f}")
print("best_gamma:", f"{best_gamma:.10f}")
print("best_cv_mse_scaled:", f"{df_cv.loc[0, 'cv_mse_scaled_mean']:.10f}")
print("best_cv_r2_original:", f"{df_cv.loc[0, 'cv_r2_original_mean']:.10f}")


# =========================================================
# 10. 用全部数据重新训练最终 Kernel Ridge 模型
# =========================================================
x_scaler_final = StandardScaler()
X_scaled = x_scaler_final.fit_transform(X)

y_scaler_final = StandardScaler()
Y_scaled = y_scaler_final.fit_transform(Y)

final_model = KernelRidge(
    kernel="rbf",
    alpha=best_alpha,
    gamma=best_gamma
)

final_model.fit(X_scaled, Y_scaled)

Y_pred_scaled = final_model.predict(X_scaled)
Y_pred = y_scaler_final.inverse_transform(Y_pred_scaled)


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
    r2 = r2_score(y_true, y_pred)

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

print("\n================ Kernel Ridge 拟合评价指标 ================")
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
# 13. 基团统计表
# =========================================================
df_used_groups = pd.DataFrame({
    "used_group": used_group_cols,
    "occurrence_material_count": (df_X != 0).sum(axis=0).values,
    "total_count": df_X.sum(axis=0).values,
})

df_removed_zero_groups = pd.DataFrame({
    "removed_all_zero_group": removed_zero_group_cols
})

df_model_params = pd.DataFrame([
    {"parameter": "model", "value": "KernelRidge_RBF"},
    {"parameter": "best_alpha", "value": best_alpha},
    {"parameter": "best_gamma", "value": best_gamma},
    {"parameter": "n_samples", "value": n_samples},
    {"parameter": "n_features", "value": X.shape[1]},
    {"parameter": "n_targets", "value": Y.shape[1]},
])


# =========================================================
# 14. 保存 Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_prediction.to_excel(writer, sheet_name="Prediction", index=False)
    df_metrics.to_excel(writer, sheet_name="Metrics", index=False)
    df_model_params.to_excel(writer, sheet_name="Model_Params", index=False)
    df_cv.to_excel(writer, sheet_name="CV_Results", index=False)
    df_used_groups.to_excel(writer, sheet_name="Used_Groups", index=False)
    df_removed_zero_groups.to_excel(writer, sheet_name="Removed_All_Zero_Groups", index=False)

    # 保存实际参与建模的数据
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
print("模型: Kernel Ridge Regression with RBF kernel")