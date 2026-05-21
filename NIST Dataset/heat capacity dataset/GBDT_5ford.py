# import pandas as pd
# import numpy as np
# from pathlib import Path
# from sklearn.ensemble import GradientBoostingRegressor
# from sklearn.linear_model import Ridge, LinearRegression
# from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
# from sklearn.model_selection import KFold
# from scipy.stats import ttest_rel
# import warnings
# warnings.filterwarnings("ignore")
#
# pd.set_option("display.float_format", "{:.10f}".format)
# np.set_printoptions(suppress=True, precision=10)
#
# # =========================================================
# # 0. 全局设置
# # =========================================================
# file_path = Path("Cp_dataset_selected_by_two_k_with_interpolation.xlsx")
# groups_sheet = "groups_selected"
# data_sheet = "Sheet1_selected"
# anchor_sheet = "Interpolated_k1_k2"
#
# output_file = Path("GBDT_direct_vs_GBDT_residual_5fold_CV.xlsx")
#
# n_points_per_material = 8
# temp_col = "T_K"
# target_col = "property_value"
#
# anchor_cp_target_col = "property_interp_at_k1Tb"
# boiling_col = "boiling_T_K"
# k1_col = "k1"
# k1_times_boiling_col = "k1_times_boiling_T_K"
#
# group_start_idx = 3
# group_end_idx = 222
#
# random_state = 42
# n_outer_folds = 5
#
# # 方法A: 直接GBDT参数（与原始代码1一致）
# gbdt_direct_params = {
#     "n_estimators": 300,
#     "learning_rate": 0.05,
#     "max_depth": 5,
#     "min_samples_split": 10,
#     "min_samples_leaf": 5,
#     "random_state": 44,
# }
#
# # 方法B: 残差GBDT参数
# residual_gbdt_params = {
#     "n_estimators": 300,
#     "learning_rate": 0.05,
#     "max_depth": 5,
#     "min_samples_split": 10,
#     "min_samples_leaf": 5,
#     "random_state": 44,
# }
#
# # 锚点预测子模型参数（全局训练）
# anchor_gbdt_params = {
#     "n_estimators": 200,
#     "learning_rate": 0.1,
#     "max_depth": 5,
#     "random_state": 42,
# }
#
# # 基线模型参数
# use_ridge_for_baseline = True
# baseline_ridge_alpha = 1.0
#
# # =========================================================
# # 1. 读取原始数据
# # =========================================================
# df_groups_raw = pd.read_excel(file_path, sheet_name=groups_sheet)
# df_data = pd.read_excel(file_path, sheet_name=data_sheet)
# df_anchor = pd.read_excel(file_path, sheet_name=anchor_sheet)
#
# print("groups 表行数:", len(df_groups_raw))
# print("Sheet1_selected 行数:", len(df_data))
# print("Interpolated_k1_k2 行数:", len(df_anchor))
#
# # =========================================================
# # 2. 基团列处理（与原始代码一致：删除全零列）
# # =========================================================
# if group_end_idx > len(df_groups_raw.columns):
#     raise ValueError(f"group_end_idx={group_end_idx} 超过总列数")
#
# group_cols_raw = df_groups_raw.columns[group_start_idx:group_end_idx].tolist()
# exclude_cols = {
#     "original_material_index", "compound_name", "cas", "formula",
#     "SMILES", "smiles", "pubchem_cid", "material_key", "phase",
#     "boiling_T_K", "critical_T_K",
# }
# group_cols_raw = [c for c in group_cols_raw if c not in exclude_cols]
#
# df_groups = df_groups_raw[group_cols_raw].copy()
# df_groups = df_groups.apply(pd.to_numeric, errors="coerce").fillna(0.0)
#
# nonzero_mask = df_groups.abs().sum(axis=0) != 0
# used_group_cols = df_groups.columns[nonzero_mask].tolist()
# df_groups_used = df_groups[used_group_cols].copy()
# X_groups = df_groups_used.values.astype(float)
#
# print("有效基团数量:", len(used_group_cols))
#
# # =========================================================
# # 3. 对齐锚点表（与原始代码2一致，全局对齐并训练锚点模型）
# # =========================================================
# if "original_material_index" in df_groups_raw.columns and "original_material_index" in df_anchor.columns:
#     df_model_anchor = df_groups_raw[["original_material_index"]].copy()
#     df_model_anchor = df_model_anchor.merge(
#         df_anchor,
#         on="original_material_index",
#         how="left",
#         validate="one_to_one"
#     )
#     print("使用 original_material_index 对齐 anchor sheet。")
# else:
#     if len(df_groups_raw) != len(df_anchor):
#         raise ValueError("无法对齐且行数不一致。")
#     df_model_anchor = df_anchor.copy().reset_index(drop=True)
#     print("按行顺序对齐 anchor sheet。")
#
# # 转换为数值
# df_model_anchor[anchor_cp_target_col] = pd.to_numeric(df_model_anchor[anchor_cp_target_col], errors="coerce")
# df_model_anchor[boiling_col] = pd.to_numeric(df_model_anchor[boiling_col], errors="coerce")
#
# # 获取 k1 值
# if k1_col in df_model_anchor.columns:
#     k1_values = pd.to_numeric(df_model_anchor[k1_col], errors="coerce").values.astype(float)
# else:
#     if k1_times_boiling_col in df_model_anchor.columns:
#         T1 = pd.to_numeric(df_model_anchor[k1_times_boiling_col], errors="coerce").values
#         Tb = pd.to_numeric(df_model_anchor[boiling_col], errors="coerce").values
#         k1_values = np.where(np.abs(Tb) > 1e-12, T1 / Tb, np.nan)
#     else:
#         raise ValueError("无法获得 k1 或 k1_times_boiling_T_K")
#
# # =========================================================
# # 4. 删除锚点或基团无效的物质
# # =========================================================
# valid_mask_anchor = (np.isfinite(df_model_anchor[anchor_cp_target_col].values) &
#                      np.isfinite(df_model_anchor[boiling_col].values) &
#                      np.isfinite(k1_values) &
#                      np.isfinite(X_groups).all(axis=1))
# if not valid_mask_anchor.all():
#     print(f"删除 {np.sum(~valid_mask_anchor)} 个无效物质")
#     keep_data_rows = []
#     for mat_idx, keep in enumerate(valid_mask_anchor):
#         if keep:
#             start = mat_idx * n_points_per_material
#             end = start + n_points_per_material
#             keep_data_rows.extend(range(start, end))
#     df_groups_used = df_groups_used.loc[valid_mask_anchor].reset_index(drop=True)
#     df_model_anchor = df_model_anchor.loc[valid_mask_anchor].reset_index(drop=True)
#     X_groups = df_groups_used.values.astype(float)
#     k1_values = k1_values[valid_mask_anchor]
#     df_data = df_data.iloc[keep_data_rows].reset_index(drop=True)
#
# n_materials = len(df_groups_used)
# print("最终有效物质数:", n_materials)
# print("热容数据行数:", len(df_data))
#
# # =========================================================
# # 5. 全局训练锚点预测模型（使用全部有效物质）
# # =========================================================
# X_anchor = X_groups
# y_anchor_cp = df_model_anchor[anchor_cp_target_col].values.astype(float)
# y_boiling = df_model_anchor[boiling_col].values.astype(float)
# valid_anchor_train = (np.isfinite(X_anchor).all(axis=1) &
#                       np.isfinite(y_anchor_cp) &
#                       np.isfinite(y_boiling))
# X_anchor_fit = X_anchor[valid_anchor_train]
# y_cp_fit = y_anchor_cp[valid_anchor_train]
# y_boiling_fit = y_boiling[valid_anchor_train]
#
# anchor_cp_model = GradientBoostingRegressor(**anchor_gbdt_params)
# anchor_boiling_model = GradientBoostingRegressor(**anchor_gbdt_params)
# anchor_cp_model.fit(X_anchor_fit, y_cp_fit)
# anchor_boiling_model.fit(X_anchor_fit, y_boiling_fit)
#
# # 预测所有物质的锚点
# cp_anchor_pred_all = anchor_cp_model.predict(X_groups)
# boiling_pred_all = anchor_boiling_model.predict(X_groups)
# # 注意：原始代码2中使用 k1 * 预测的沸点 作为 anchor_T
# anchor_T_pred_all = k1_values * boiling_pred_all
#
# # 确保锚点预测值有效
# valid_anchor_pred = np.isfinite(cp_anchor_pred_all) & np.isfinite(anchor_T_pred_all)
# if not valid_anchor_pred.all():
#     print(f"警告：{np.sum(~valid_anchor_pred)} 个物质锚点预测无效，将其排除")
#     # 这里简单处理：将无效锚点对应的物质排除（后续构建点时跳过）
#     # 但为了代码简洁，我们假设全部有效（数据应该都是有效的）
#
# # =========================================================
# # 6. 展开所有温度点数据（只保留锚点预测有效的物质）
# # =========================================================
# all_targets = []
# material_ids = []
# temperatures = []
# anchor_T_list = []
# anchor_Cp_list = []
# orig_row_indices = []
#
# for mat_idx in range(n_materials):
#     if not valid_anchor_pred[mat_idx]:
#         continue
#     start = mat_idx * n_points_per_material
#     end = start + n_points_per_material
#     sub = df_data.iloc[start:end]
#     T_vals = pd.to_numeric(sub[temp_col], errors="coerce").values.astype(float)
#     Cp_vals = pd.to_numeric(sub[target_col], errors="coerce").values.astype(float)
#     for local_i, (T, Cp) in enumerate(zip(T_vals, Cp_vals)):
#         if np.isfinite(T) and np.isfinite(Cp):
#             all_targets.append(Cp)
#             material_ids.append(mat_idx)
#             temperatures.append(T)
#             anchor_T_list.append(anchor_T_pred_all[mat_idx])
#             anchor_Cp_list.append(cp_anchor_pred_all[mat_idx])
#             orig_row_indices.append(start + local_i)
#
# y = np.array(all_targets)
# material_ids = np.array(material_ids, dtype=int)
# temperatures = np.array(temperatures)
# anchor_T_rows = np.array(anchor_T_list)
# anchor_Cp_rows = np.array(anchor_Cp_list)
# unique_materials = np.unique(material_ids)
# print("展开后样本点数:", len(y))
# print("有效物质数:", len(unique_materials))
#
# # =========================================================
# # 7. 辅助函数：构建特征矩阵
# # =========================================================
# def build_direct_features(sample_indices):
#     """方法A：基团 + 温度"""
#     indices = np.asarray(sample_indices)
#     mat_ids = material_ids[indices]
#     T = temperatures[indices]
#     group_feat = X_groups[mat_ids]
#     return np.hstack([group_feat, T.reshape(-1, 1)])
#
# def build_baseline_X(sample_indices):
#     """方法B基线特征：(T - anchor_T) * Nk"""
#     indices = np.asarray(sample_indices)
#     mat_ids = material_ids[indices]
#     T = temperatures[indices]
#     anchor_T = anchor_T_rows[indices]
#     delta_T = T - anchor_T
#     group_feat = X_groups[mat_ids]
#     return group_feat * delta_T.reshape(-1, 1)
#
# def build_residual_features(sample_indices):
#     """方法B残差GBDT特征：基团 + 温度"""
#     indices = np.asarray(sample_indices)
#     mat_ids = material_ids[indices]
#     T = temperatures[indices]
#     group_feat = X_groups[mat_ids]
#     return np.hstack([group_feat, T.reshape(-1, 1)])
#
# # =========================================================
# # 8. 外层5折交叉验证
# # =========================================================
# outer_kf = KFold(n_splits=n_outer_folds, shuffle=True, random_state=random_state)
#
# metrics_direct = []   # 方法A
# metrics_methodB = []  # 方法B
#
# for fold, (train_mat_idx, test_mat_idx) in enumerate(outer_kf.split(unique_materials)):
#     print(f"\n========== Fold {fold+1}/{n_outer_folds} ==========")
#     train_mats = unique_materials[train_mat_idx]
#     test_mats = unique_materials[test_mat_idx]
#
#     train_mask = np.isin(material_ids, train_mats)
#     test_mask = np.isin(material_ids, test_mats)
#     train_indices = np.where(train_mask)[0]
#     test_indices = np.where(test_mask)[0]
#
#     # ---------- 方法A：直接GBDT ----------
#     X_train_direct = build_direct_features(train_indices)
#     y_train_direct = y[train_indices]
#     valid_direct = np.isfinite(X_train_direct).all(axis=1) & np.isfinite(y_train_direct)
#     X_train_direct = X_train_direct[valid_direct]
#     y_train_direct = y_train_direct[valid_direct]
#     model_direct = GradientBoostingRegressor(**gbdt_direct_params)
#     model_direct.fit(X_train_direct, y_train_direct)
#
#     X_test_direct = build_direct_features(test_indices)
#     y_test = y[test_indices]
#     valid_test_direct = np.isfinite(X_test_direct).all(axis=1)
#     y_pred_direct = np.full(len(test_indices), np.nan)
#     y_pred_direct[valid_test_direct] = model_direct.predict(X_test_direct[valid_test_direct])
#
#     # ---------- 方法B：线性基线 + 残差GBDT ----------
#     # 基线模型训练
#     X_base_train = build_baseline_X(train_indices)
#     y_base_target = y[train_indices] - anchor_Cp_rows[train_indices]
#     valid_base = np.isfinite(X_base_train).all(axis=1) & np.isfinite(y_base_target)
#     X_base_train_fit = X_base_train[valid_base]
#     y_base_target_fit = y_base_target[valid_base]
#     if use_ridge_for_baseline:
#         base_model = Ridge(alpha=baseline_ridge_alpha, fit_intercept=False)
#     else:
#         base_model = LinearRegression(fit_intercept=False)
#     base_model.fit(X_base_train_fit, y_base_target_fit)
#
#     # 测试集基线预测
#     X_base_test = build_baseline_X(test_indices)
#     valid_base_test = np.isfinite(X_base_test).all(axis=1)
#     base_delta = np.full(len(test_indices), np.nan)
#     base_delta[valid_base_test] = base_model.predict(X_base_test[valid_base_test])
#     baseline_pred = anchor_Cp_rows[test_indices] + base_delta
#
#     # 残差模型训练
#     residual_X_train = build_residual_features(train_indices)
#     residual_y_train = y[train_indices] - (anchor_Cp_rows[train_indices] + base_model.predict(X_base_train))
#     valid_res = np.isfinite(residual_X_train).all(axis=1) & np.isfinite(residual_y_train)
#     residual_X_train_fit = residual_X_train[valid_res]
#     residual_y_train_fit = residual_y_train[valid_res]
#     if len(residual_y_train_fit) == 0:
#         residual_pred_test = np.zeros(len(test_indices))
#     else:
#         res_model = GradientBoostingRegressor(**residual_gbdt_params)
#         res_model.fit(residual_X_train_fit, residual_y_train_fit)
#         residual_X_test = build_residual_features(test_indices)
#         valid_res_test = np.isfinite(residual_X_test).all(axis=1)
#         residual_pred_test = np.full(len(test_indices), np.nan)
#         residual_pred_test[valid_res_test] = res_model.predict(residual_X_test[valid_res_test])
#     y_pred_methodB = baseline_pred + residual_pred_test
#
#     # 计算指标函数
#     def compute_metrics(y_true, y_pred):
#         mask = np.isfinite(y_true) & np.isfinite(y_pred)
#         y_true = y_true[mask]
#         y_pred = y_pred[mask]
#         if len(y_true) == 0:
#             return {k: np.nan for k in ["R2", "MSE", "RMSE", "MAE", "ARD(%)", "max_rel_err(%)",
#                                         "≤1% ratio(%)", "≤5% ratio(%)", "≤10% ratio(%)"]}
#         mse = mean_squared_error(y_true, y_pred)
#         rmse = np.sqrt(mse)
#         mae = mean_absolute_error(y_true, y_pred)
#         r2 = r2_score(y_true, y_pred)
#         valid_rel = np.abs(y_true) > 1e-12
#         if valid_rel.sum() > 0:
#             rel_err = np.abs((y_pred[valid_rel] - y_true[valid_rel]) / y_true[valid_rel]) * 100
#             ard = np.mean(rel_err)
#             max_rel = np.max(rel_err)
#             pct1 = np.mean(rel_err <= 1) * 100
#             pct5 = np.mean(rel_err <= 5) * 100
#             pct10 = np.mean(rel_err <= 10) * 100
#         else:
#             ard = max_rel = pct1 = pct5 = pct10 = np.nan
#         return {"R2": r2, "MSE": mse, "RMSE": rmse, "MAE": mae,
#                 "ARD(%)": ard, "max_rel_err(%)": max_rel,
#                 "≤1% ratio(%)": pct1, "≤5% ratio(%)": pct5, "≤10% ratio(%)": pct10}
#
#     m_direct = compute_metrics(y_test, y_pred_direct)
#     m_methodB = compute_metrics(y_test, y_pred_methodB)
#     m_direct["fold"] = fold+1
#     m_methodB["fold"] = fold+1
#     metrics_direct.append(m_direct)
#     metrics_methodB.append(m_methodB)
#
# # =========================================================
# # 9. 汇总统计
# # =========================================================
# df_direct = pd.DataFrame(metrics_direct)
# df_methodB = pd.DataFrame(metrics_methodB)
#
# def summarize(df, name):
#     stats = []
#     for metric in ["R2", "MSE", "RMSE", "MAE", "ARD(%)", "max_rel_err(%)",
#                    "≤1% ratio(%)", "≤5% ratio(%)", "≤10% ratio(%)"]:
#         vals = df[metric].dropna().values
#         if len(vals) == 0:
#             mean_std = "NaN"
#         else:
#             mean_val = np.mean(vals)
#             std_val = np.std(vals, ddof=1)
#             mean_std = f"{mean_val:.4f} ± {std_val:.4f}"
#         stats.append({"Model": name, "Metric": metric, "Mean±Std": mean_std})
#     return pd.DataFrame(stats)
#
# summary_direct = summarize(df_direct, "GBDT_Direct")
# summary_methodB = summarize(df_methodB, "MethodB_LinearBaseline+GBDT_residual")
# summary_all = pd.concat([summary_direct, summary_methodB], ignore_index=True)
#
# print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
# print(summary_all.to_string(index=False))
#
# # =========================================================
# # 10. 配对t检验
# # =========================================================
# t_test_results = []
# for metric in ["R2", "MSE", "RMSE", "MAE", "ARD(%)"]:
#     vals_direct = df_direct[metric].dropna().values
#     vals_methodB = df_methodB[metric].dropna().values
#     if len(vals_direct) == len(vals_methodB) and len(vals_direct) > 1:
#         t_stat, p_val = ttest_rel(vals_direct, vals_methodB)
#         if metric in ["MSE", "RMSE", "MAE", "ARD(%)"]:
#             better = "MethodB" if np.mean(vals_methodB) < np.mean(vals_direct) else "GBDT_Direct"
#             significant = p_val < 0.05
#         else:
#             better = "MethodB" if np.mean(vals_methodB) > np.mean(vals_direct) else "GBDT_Direct"
#             significant = p_val < 0.05
#         t_test_results.append({
#             "Metric": metric,
#             "Mean_GBDT_Direct": f"{np.mean(vals_direct):.4f}",
#             "Mean_MethodB": f"{np.mean(vals_methodB):.4f}",
#             "p-value": f"{p_val:.4e}",
#             "Significant (p<0.05)": significant,
#             "Better model": better
#         })
#
# df_ttest = pd.DataFrame(t_test_results)
# print("\n========== Paired t-test (GBDT_Direct vs MethodB) ==========")
# print(df_ttest.to_string(index=False))
#
# # =========================================================
# # 11. 保存Excel
# # =========================================================
# with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
#     df_direct.to_excel(writer, sheet_name="Fold_Metrics_GBDT_Direct", index=False)
#     df_methodB.to_excel(writer, sheet_name="Fold_Metrics_MethodB", index=False)
#     summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
#     df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)
#
#     # 参数信息
#     params = pd.DataFrame([
#         {"param": "n_outer_folds", "value": n_outer_folds},
#         {"param": "random_state", "value": random_state},
#         {"param": "gbdt_direct_params", "value": str(gbdt_direct_params)},
#         {"param": "residual_gbdt_params", "value": str(residual_gbdt_params)},
#         {"param": "anchor_gbdt_params", "value": str(anchor_gbdt_params)},
#         {"param": "use_ridge_for_baseline", "value": use_ridge_for_baseline},
#         {"param": "baseline_ridge_alpha", "value": baseline_ridge_alpha},
#     ])
#     params.to_excel(writer, sheet_name="Run_Params", index=False)
#
#     from openpyxl import load_workbook
#     workbook = writer.book
#     number_format = "0.0000000000"
#     for sheetname in writer.sheets:
#         ws = workbook[sheetname]
#         for row in ws.iter_rows():
#             for cell in row:
#                 if isinstance(cell.value, float):
#                     cell.number_format = number_format
#         for col in ws.columns:
#             max_len = 0
#             col_letter = col[0].column_letter
#             for cell in col:
#                 if cell.value:
#                     max_len = max(max_len, len(str(cell.value)))
#             ws.column_dimensions[col_letter].width = min(max_len+2, 40)
#
# print(f"\n所有结果已保存至: {output_file}")


import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge, LinearRegression
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.model_selection import KFold
from scipy.stats import ttest_rel

import warnings
warnings.filterwarnings("ignore")

pd.set_option("display.float_format", "{:.10f}".format)
np.set_printoptions(suppress=True, precision=10)


# =========================================================
# 0. 全局设置
# =========================================================
file_path = Path("Cp_dataset_selected_by_two_k_with_interpolation.xlsx")

groups_sheet = "groups_selected"
data_sheet = "Sheet1_selected"
anchor_sheet = "Interpolated_k1_k2"

output_file = Path("GBDT_direct_vs_GBDT_residual_5fold_CV.xlsx")

n_points_per_material = 8
temp_col = "T_K"
target_col = "property_value"

anchor_cp_target_col = "property_interp_at_k1Tb"
boiling_col = "boiling_T_K"
k1_col = "k1"
k1_times_boiling_col = "k1_times_boiling_T_K"

group_start_idx = 3
group_end_idx = 222

random_state = 42
n_outer_folds = 5

# 方法A: 直接GBDT参数（与原始代码1一致）
gbdt_direct_params = {
    "n_estimators": 300,
    "learning_rate": 0.05,
    "max_depth": 5,
    "min_samples_split": 10,
    "min_samples_leaf": 5,
    "random_state": 44,
}

# 方法B: 残差GBDT参数
residual_gbdt_params = {
    "n_estimators": 300,
    "learning_rate": 0.05,
    "max_depth": 5,
    "min_samples_split": 10,
    "min_samples_leaf": 5,
    "random_state": 44,
}

# 锚点预测子模型参数（全局训练，保留原代码设计）
anchor_gbdt_params = {
    "n_estimators": 200,
    "learning_rate": 0.1,
    "max_depth": 5,
    "random_state": 42,
}

# 基线模型参数
use_ridge_for_baseline = True
baseline_ridge_alpha = 1.0


# =========================================================
# 1. 工具函数
# =========================================================
def safe_relative_error_percent(y_true, y_pred):
    """
    relative_error = abs((y_pred - y_true) / y_true) * 100

    对 abs(y_true) <= 1e-12 的点，relative_error 记为 NaN。
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    rel_err = np.full_like(y_true, np.nan, dtype=float)
    valid = (
        np.isfinite(y_true)
        & np.isfinite(y_pred)
        & (np.abs(y_true) > 1e-12)
    )

    rel_err[valid] = np.abs((y_pred[valid] - y_true[valid]) / y_true[valid]) * 100.0

    return rel_err


def count_error_thresholds(y_true, y_pred):
    """
    统计相对误差 <1%、<5%、<10% 的数据点数量。
    NaN 自动忽略。

    注意：这里使用严格小于 <，不是 <=。
    """
    rel_err = safe_relative_error_percent(y_true, y_pred)

    return {
        "count_rel_err_lt_1pct": float(np.nansum(rel_err < 1.0)),
        "count_rel_err_lt_5pct": float(np.nansum(rel_err < 5.0)),
        "count_rel_err_lt_10pct": float(np.nansum(rel_err < 10.0)),
        "n_valid_for_relative_error": int(np.sum(np.isfinite(rel_err))),
    }


def compute_metrics(y_true, y_pred, fold=None, model_name=None, dataset_name=None):
    """
    计算 R2、MSE、RMSE、MAE、ARD、最大相对误差、误差区间比例和数量。
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = np.isfinite(y_true) & np.isfinite(y_pred)

    y_true = y_true[mask]
    y_pred = y_pred[mask]

    base = {}
    if fold is not None:
        base["fold"] = fold
    if model_name is not None:
        base["model"] = model_name
    if dataset_name is not None:
        base["dataset"] = dataset_name

    if len(y_true) == 0:
        base.update({
            "n_points": 0,
            "R2": np.nan,
            "MSE": np.nan,
            "RMSE": np.nan,
            "MAE": np.nan,
            "ARD(%)": np.nan,
            "max_rel_err(%)": np.nan,
            "<1% ratio(%)": np.nan,
            "<5% ratio(%)": np.nan,
            "<10% ratio(%)": np.nan,
            "<1% count": 0.0,
            "<5% count": 0.0,
            "<10% count": 0.0,
        })
        return base

    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred) if len(y_true) > 1 else np.nan

    rel_err = safe_relative_error_percent(y_true, y_pred)

    if np.any(np.isfinite(rel_err)):
        ard = np.nanmean(rel_err)
        max_rel = np.nanmax(rel_err)

        count_1 = float(np.nansum(rel_err < 1.0))
        count_5 = float(np.nansum(rel_err < 5.0))
        count_10 = float(np.nansum(rel_err < 10.0))

        n_valid_rel = int(np.sum(np.isfinite(rel_err)))

        pct1 = count_1 / n_valid_rel * 100.0
        pct5 = count_5 / n_valid_rel * 100.0
        pct10 = count_10 / n_valid_rel * 100.0
    else:
        ard = np.nan
        max_rel = np.nan
        pct1 = np.nan
        pct5 = np.nan
        pct10 = np.nan
        count_1 = 0.0
        count_5 = 0.0
        count_10 = 0.0

    base.update({
        "n_points": len(y_true),
        "R2": r2,
        "MSE": mse,
        "RMSE": rmse,
        "MAE": mae,
        "ARD(%)": ard,
        "max_rel_err(%)": max_rel,
        "<1% ratio(%)": pct1,
        "<5% ratio(%)": pct5,
        "<10% ratio(%)": pct10,
        "<1% count": count_1,
        "<5% count": count_5,
        "<10% count": count_10,
    })

    return base


def summarize(df, name):
    stats = []

    for metric in [
        "R2",
        "MSE",
        "RMSE",
        "MAE",
        "ARD(%)",
        "max_rel_err(%)",
        "<1% ratio(%)",
        "<5% ratio(%)",
        "<10% ratio(%)",
    ]:
        vals = df[metric].dropna().values

        if len(vals) == 0:
            mean_val = np.nan
            std_val = np.nan
            mean_std = "NaN"
        elif len(vals) == 1:
            mean_val = float(np.mean(vals))
            std_val = np.nan
            mean_std = f"{mean_val:.4f} ± NaN"
        else:
            mean_val = float(np.mean(vals))
            std_val = float(np.std(vals, ddof=1))
            mean_std = f"{mean_val:.4f} ± {std_val:.4f}"

        stats.append({
            "Model": name,
            "Metric": metric,
            "Mean": mean_val,
            "Std": std_val,
            "Mean±Std": mean_std,
        })

    return pd.DataFrame(stats)


def make_prediction_df(
    fold,
    dataset_name,
    method,
    sample_indices,
    y_true,
    y_pred,
    baseline_pred=None,
    residual_pred=None,
):
    sample_indices = np.asarray(sample_indices, dtype=int)
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    rel_err = safe_relative_error_percent(y_true, y_pred)

    df = pd.DataFrame({
        "fold": fold,
        "dataset": dataset_name,
        "Method": method,
        "sample_index": sample_indices,
        "material_id": material_ids[sample_indices],
        "original_data_row_index": orig_row_indices[sample_indices],
        "T_K": temperatures[sample_indices],
        "anchor_T_pred": anchor_T_rows[sample_indices],
        "anchor_Cp_pred": anchor_Cp_rows[sample_indices],
        "y_true": y_true,
        "y_pred": y_pred,
        "error": y_pred - y_true,
        "absolute_error": np.abs(y_pred - y_true),
        "relative_error_percent": rel_err,
    })

    if baseline_pred is not None:
        df["baseline_pred"] = baseline_pred
        df["baseline_error"] = baseline_pred - y_true
        df["baseline_relative_error_percent"] = safe_relative_error_percent(y_true, baseline_pred)

    if residual_pred is not None:
        df["residual_pred"] = residual_pred
        df["residual_target"] = y_true - baseline_pred if baseline_pred is not None else np.nan

    return df


def predict_baseline(sample_indices, base_model):
    X_base = build_baseline_X(sample_indices)
    pred_delta = np.full(len(sample_indices), np.nan, dtype=float)

    valid = np.isfinite(X_base).all(axis=1)

    if valid.sum() > 0:
        pred_delta[valid] = base_model.predict(X_base[valid])

    baseline_pred = anchor_Cp_rows[sample_indices] + pred_delta

    return baseline_pred, pred_delta


def predict_residual(sample_indices, res_model):
    X_res = build_residual_features(sample_indices)
    residual_pred = np.full(len(sample_indices), np.nan, dtype=float)

    valid = np.isfinite(X_res).all(axis=1)

    if res_model is None:
        residual_pred[valid] = 0.0
    elif valid.sum() > 0:
        residual_pred[valid] = res_model.predict(X_res[valid])

    return residual_pred


def format_excel(writer, number_format="0.0000000000"):
    workbook = writer.book

    for sheetname in writer.sheets:
        ws = workbook[sheetname]

        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, float):
                    cell.number_format = number_format

        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter

            for cell in col:
                if cell.value is not None:
                    max_len = max(max_len, len(str(cell.value)))

            ws.column_dimensions[col_letter].width = min(max_len + 2, 60)


# =========================================================
# 2. 读取原始数据
# =========================================================
df_groups_raw = pd.read_excel(file_path, sheet_name=groups_sheet)
df_data = pd.read_excel(file_path, sheet_name=data_sheet)
df_anchor = pd.read_excel(file_path, sheet_name=anchor_sheet)

print("groups 表行数:", len(df_groups_raw))
print("Sheet1_selected 行数:", len(df_data))
print("Interpolated_k1_k2 行数:", len(df_anchor))


# =========================================================
# 3. 基团列处理（与原始代码一致：删除全零列）
# =========================================================
if group_end_idx > len(df_groups_raw.columns):
    raise ValueError(f"group_end_idx={group_end_idx} 超过总列数")

group_cols_raw = df_groups_raw.columns[group_start_idx:group_end_idx].tolist()

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

df_groups = df_groups_raw[group_cols_raw].copy()
df_groups = df_groups.apply(pd.to_numeric, errors="coerce").fillna(0.0)

nonzero_mask = df_groups.abs().sum(axis=0) != 0

used_group_cols = df_groups.columns[nonzero_mask].tolist()
removed_zero_group_cols = df_groups.columns[~nonzero_mask].tolist()

df_groups_used = df_groups[used_group_cols].copy()
X_groups = df_groups_used.values.astype(float)

print("有效基团数量:", len(used_group_cols))
print("删除全零基团数量:", len(removed_zero_group_cols))


# =========================================================
# 4. 对齐锚点表（与原始代码2一致，全局对齐并训练锚点模型）
# =========================================================
if "original_material_index" in df_groups_raw.columns and "original_material_index" in df_anchor.columns:
    df_model_anchor = df_groups_raw[["original_material_index"]].copy()
    df_model_anchor = df_model_anchor.merge(
        df_anchor,
        on="original_material_index",
        how="left",
        validate="one_to_one",
    )
    print("使用 original_material_index 对齐 anchor sheet。")
else:
    if len(df_groups_raw) != len(df_anchor):
        raise ValueError("无法对齐且行数不一致。")
    df_model_anchor = df_anchor.copy().reset_index(drop=True)
    print("按行顺序对齐 anchor sheet。")

# 转换为数值
df_model_anchor[anchor_cp_target_col] = pd.to_numeric(
    df_model_anchor[anchor_cp_target_col],
    errors="coerce",
)
df_model_anchor[boiling_col] = pd.to_numeric(
    df_model_anchor[boiling_col],
    errors="coerce",
)

# 获取 k1 值
if k1_col in df_model_anchor.columns:
    k1_values = pd.to_numeric(
        df_model_anchor[k1_col],
        errors="coerce",
    ).values.astype(float)
else:
    if k1_times_boiling_col in df_model_anchor.columns:
        T1 = pd.to_numeric(
            df_model_anchor[k1_times_boiling_col],
            errors="coerce",
        ).values.astype(float)
        Tb = pd.to_numeric(
            df_model_anchor[boiling_col],
            errors="coerce",
        ).values.astype(float)
        k1_values = np.where(np.abs(Tb) > 1e-12, T1 / Tb, np.nan)
    else:
        raise ValueError("无法获得 k1 或 k1_times_boiling_T_K")


# =========================================================
# 5. 删除锚点或基团无效的物质
# =========================================================
valid_mask_anchor = (
    np.isfinite(df_model_anchor[anchor_cp_target_col].values)
    & np.isfinite(df_model_anchor[boiling_col].values)
    & np.isfinite(k1_values)
    & np.isfinite(X_groups).all(axis=1)
)

if not valid_mask_anchor.all():
    print(f"删除 {np.sum(~valid_mask_anchor)} 个无效物质")

    keep_data_rows = []
    for mat_idx, keep in enumerate(valid_mask_anchor):
        if keep:
            start = mat_idx * n_points_per_material
            end = start + n_points_per_material
            keep_data_rows.extend(range(start, end))

    df_groups_raw = df_groups_raw.loc[valid_mask_anchor].reset_index(drop=True)
    df_groups_used = df_groups_used.loc[valid_mask_anchor].reset_index(drop=True)
    df_model_anchor = df_model_anchor.loc[valid_mask_anchor].reset_index(drop=True)

    X_groups = df_groups_used.values.astype(float)
    k1_values = k1_values[valid_mask_anchor]
    df_data = df_data.iloc[keep_data_rows].reset_index(drop=True)

n_materials = len(df_groups_used)

print("最终有效物质数:", n_materials)
print("热容数据行数:", len(df_data))

if len(df_data) % n_points_per_material != 0:
    raise ValueError(
        f"热容数据行数 {len(df_data)} 不是 {n_points_per_material} 的倍数。"
    )


# =========================================================
# 6. 全局训练锚点预测模型（使用全部有效物质，保留原实验设计）
# =========================================================
X_anchor = X_groups
y_anchor_cp = df_model_anchor[anchor_cp_target_col].values.astype(float)
y_boiling = df_model_anchor[boiling_col].values.astype(float)

valid_anchor_train = (
    np.isfinite(X_anchor).all(axis=1)
    & np.isfinite(y_anchor_cp)
    & np.isfinite(y_boiling)
)

X_anchor_fit = X_anchor[valid_anchor_train]
y_cp_fit = y_anchor_cp[valid_anchor_train]
y_boiling_fit = y_boiling[valid_anchor_train]

anchor_cp_model = GradientBoostingRegressor(**anchor_gbdt_params)
anchor_boiling_model = GradientBoostingRegressor(**anchor_gbdt_params)

anchor_cp_model.fit(X_anchor_fit, y_cp_fit)
anchor_boiling_model.fit(X_anchor_fit, y_boiling_fit)

# 预测所有物质的锚点
cp_anchor_pred_all = anchor_cp_model.predict(X_groups)
boiling_pred_all = anchor_boiling_model.predict(X_groups)

# 注意：原始代码2中使用 k1 * 预测的沸点 作为 anchor_T
anchor_T_pred_all = k1_values * boiling_pred_all

# 锚点模型自身评价
anchor_cp_train_pred = anchor_cp_model.predict(X_anchor_fit)
anchor_boiling_train_pred = anchor_boiling_model.predict(X_anchor_fit)

df_anchor_submodel_summary = pd.DataFrame([
    compute_metrics(
        y_cp_fit,
        anchor_cp_train_pred,
        fold=None,
        model_name="anchor_cp_GBDT",
        dataset_name="anchor_training_all_valid_materials",
    ),
    compute_metrics(
        y_boiling_fit,
        anchor_boiling_train_pred,
        fold=None,
        model_name="anchor_boiling_GBDT",
        dataset_name="anchor_training_all_valid_materials",
    ),
])

df_anchor_submodel_predictions = pd.DataFrame({
    "material_id": np.arange(n_materials),
    "anchor_Cp_true": y_anchor_cp,
    "anchor_Cp_pred": cp_anchor_pred_all,
    "anchor_Cp_abs_error": np.abs(cp_anchor_pred_all - y_anchor_cp),
    "anchor_Cp_relative_error_percent": safe_relative_error_percent(y_anchor_cp, cp_anchor_pred_all),
    "boiling_T_true": y_boiling,
    "boiling_T_pred": boiling_pred_all,
    "boiling_T_abs_error": np.abs(boiling_pred_all - y_boiling),
    "boiling_T_relative_error_percent": safe_relative_error_percent(y_boiling, boiling_pred_all),
    "k1": k1_values,
    "anchor_T_pred": anchor_T_pred_all,
})

for col in [
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
]:
    if col in df_groups_raw.columns:
        df_anchor_submodel_predictions[col] = df_groups_raw[col].values

# 确保锚点预测值有效
valid_anchor_pred = np.isfinite(cp_anchor_pred_all) & np.isfinite(anchor_T_pred_all)

if not valid_anchor_pred.all():
    print(f"警告：{np.sum(~valid_anchor_pred)} 个物质锚点预测无效，展开样本时将跳过。")


# =========================================================
# 7. 展开所有温度点数据（只保留锚点预测有效的物质）
# =========================================================
all_targets = []
material_ids = []
temperatures = []
anchor_T_list = []
anchor_Cp_list = []
orig_row_indices = []

for mat_idx in range(n_materials):
    if not valid_anchor_pred[mat_idx]:
        continue

    start = mat_idx * n_points_per_material
    end = start + n_points_per_material

    sub = df_data.iloc[start:end]

    T_vals = pd.to_numeric(sub[temp_col], errors="coerce").values.astype(float)
    Cp_vals = pd.to_numeric(sub[target_col], errors="coerce").values.astype(float)

    for local_i, (T, Cp) in enumerate(zip(T_vals, Cp_vals)):
        if np.isfinite(T) and np.isfinite(Cp):
            all_targets.append(Cp)
            material_ids.append(mat_idx)
            temperatures.append(T)
            anchor_T_list.append(anchor_T_pred_all[mat_idx])
            anchor_Cp_list.append(cp_anchor_pred_all[mat_idx])
            orig_row_indices.append(start + local_i)

y = np.array(all_targets, dtype=float)
material_ids = np.array(material_ids, dtype=int)
temperatures = np.array(temperatures, dtype=float)
anchor_T_rows = np.array(anchor_T_list, dtype=float)
anchor_Cp_rows = np.array(anchor_Cp_list, dtype=float)
orig_row_indices = np.array(orig_row_indices, dtype=int)

unique_materials = np.unique(material_ids)
all_sample_indices = np.arange(len(y))

print("展开后样本点数:", len(y))
print("有效物质数:", len(unique_materials))


# =========================================================
# 8. 辅助函数：构建特征矩阵
# =========================================================
def build_direct_features(sample_indices):
    """
    方法A：基团 + 温度
    """
    indices = np.asarray(sample_indices, dtype=int)
    mat_ids = material_ids[indices]
    T = temperatures[indices]
    group_feat = X_groups[mat_ids]

    return np.hstack([group_feat, T.reshape(-1, 1)])


def build_baseline_X(sample_indices):
    """
    方法B基线特征：(T - anchor_T) * Nk
    """
    indices = np.asarray(sample_indices, dtype=int)
    mat_ids = material_ids[indices]
    T = temperatures[indices]
    anchor_T = anchor_T_rows[indices]

    delta_T = T - anchor_T
    group_feat = X_groups[mat_ids]

    return group_feat * delta_T.reshape(-1, 1)


def build_residual_features(sample_indices):
    """
    方法B残差GBDT特征：基团 + 温度
    """
    indices = np.asarray(sample_indices, dtype=int)
    mat_ids = material_ids[indices]
    T = temperatures[indices]
    group_feat = X_groups[mat_ids]

    return np.hstack([group_feat, T.reshape(-1, 1)])


X_direct_all = build_direct_features(all_sample_indices)
X_base_all = build_baseline_X(all_sample_indices)
X_residual_all = build_residual_features(all_sample_indices)

direct_feature_names = used_group_cols + [temp_col]
baseline_feature_names = [f"{g}*(T-anchor_T)" for g in used_group_cols]
residual_feature_names = used_group_cols + [temp_col]


# =========================================================
# 9. 外层5折交叉验证
# =========================================================
outer_kf = KFold(
    n_splits=n_outer_folds,
    shuffle=True,
    random_state=random_state,
)

metrics_direct = []   # 方法A
metrics_methodB = []  # 方法B final = baseline + residual

baseline_metrics_test = []
residual_metrics_test = []

fold_test_prediction_dfs = []
fold_all_data_prediction_dfs = []
fold_all_data_count_records = []
fold_info_records = []

baseline_param_records = []
direct_feature_importance_records = []
residual_feature_importance_records = []

for fold, (train_mat_idx, test_mat_idx) in enumerate(outer_kf.split(unique_materials), start=1):
    print(f"\n========== Fold {fold}/{n_outer_folds} ==========")

    train_mats = unique_materials[train_mat_idx]
    test_mats = unique_materials[test_mat_idx]

    train_mask = np.isin(material_ids, train_mats)
    test_mask = np.isin(material_ids, test_mats)

    train_indices = np.where(train_mask)[0]
    test_indices = np.where(test_mask)[0]

    print("训练物质数:", len(train_mats))
    print("测试物质数:", len(test_mats))
    print("训练样本点数:", len(train_indices))
    print("测试样本点数:", len(test_indices))

    # =====================================================
    # 方法A：直接GBDT
    # =====================================================
    X_train_direct = build_direct_features(train_indices)
    y_train_direct = y[train_indices]

    valid_direct = (
        np.isfinite(X_train_direct).all(axis=1)
        & np.isfinite(y_train_direct)
    )

    X_train_direct_fit = X_train_direct[valid_direct]
    y_train_direct_fit = y_train_direct[valid_direct]

    model_direct = GradientBoostingRegressor(**gbdt_direct_params)
    model_direct.fit(X_train_direct_fit, y_train_direct_fit)

    X_test_direct = build_direct_features(test_indices)
    y_test = y[test_indices]

    y_pred_direct_test = np.full(len(test_indices), np.nan, dtype=float)
    valid_test_direct = np.isfinite(X_test_direct).all(axis=1)

    if valid_test_direct.sum() > 0:
        y_pred_direct_test[valid_test_direct] = model_direct.predict(X_test_direct[valid_test_direct])

    y_pred_direct_all = np.full(len(all_sample_indices), np.nan, dtype=float)
    valid_all_direct = np.isfinite(X_direct_all).all(axis=1)

    if valid_all_direct.sum() > 0:
        y_pred_direct_all[valid_all_direct] = model_direct.predict(X_direct_all[valid_all_direct])

    # =====================================================
    # 方法B：线性基线 + 残差GBDT
    # =====================================================
    # ---------- 9.1 基线模型训练 ----------
    X_base_train = build_baseline_X(train_indices)
    y_base_target = y[train_indices] - anchor_Cp_rows[train_indices]

    valid_base = (
        np.isfinite(X_base_train).all(axis=1)
        & np.isfinite(y_base_target)
    )

    X_base_train_fit = X_base_train[valid_base]
    y_base_target_fit = y_base_target[valid_base]

    if use_ridge_for_baseline:
        base_model = Ridge(
            alpha=baseline_ridge_alpha,
            fit_intercept=False,
        )
        baseline_model_name = f"Ridge(alpha={baseline_ridge_alpha}, fit_intercept=False)"
    else:
        base_model = LinearRegression(fit_intercept=False)
        baseline_model_name = "LinearRegression(fit_intercept=False)"

    base_model.fit(X_base_train_fit, y_base_target_fit)

    # ---------- 9.2 基线预测：训练集、测试集、完整数据集 ----------
    baseline_pred_train, base_delta_train = predict_baseline(train_indices, base_model)
    baseline_pred_test, base_delta_test = predict_baseline(test_indices, base_model)
    baseline_pred_all, base_delta_all = predict_baseline(all_sample_indices, base_model)

    # ---------- 9.3 残差模型训练 ----------
    residual_X_train = build_residual_features(train_indices)
    residual_y_train = y[train_indices] - baseline_pred_train

    valid_res = (
        np.isfinite(residual_X_train).all(axis=1)
        & np.isfinite(residual_y_train)
    )

    residual_X_train_fit = residual_X_train[valid_res]
    residual_y_train_fit = residual_y_train[valid_res]

    if len(residual_y_train_fit) == 0:
        res_model = None
        print("警告：残差训练集为空，本 fold residual_pred 使用 0。")
    else:
        res_model = GradientBoostingRegressor(**residual_gbdt_params)
        res_model.fit(residual_X_train_fit, residual_y_train_fit)

    residual_pred_test = predict_residual(test_indices, res_model)
    residual_pred_all = predict_residual(all_sample_indices, res_model)

    y_pred_methodB_test = baseline_pred_test + residual_pred_test
    y_pred_methodB_all = baseline_pred_all + residual_pred_all

    # =====================================================
    # 9.4 测试集评价：保留原功能 + 增加 baseline / residual 信息
    # =====================================================
    m_direct = compute_metrics(
        y_test,
        y_pred_direct_test,
        fold=fold,
        model_name="GBDT_Direct",
        dataset_name="test",
    )

    m_methodB = compute_metrics(
        y_test,
        y_pred_methodB_test,
        fold=fold,
        model_name="MethodB_LinearBaseline+GBDT_residual",
        dataset_name="test",
    )

    m_baseline = compute_metrics(
        y_test,
        baseline_pred_test,
        fold=fold,
        model_name="MethodB_baseline_only",
        dataset_name="test",
    )

    residual_target_test = y_test - baseline_pred_test
    m_residual = compute_metrics(
        residual_target_test,
        residual_pred_test,
        fold=fold,
        model_name="MethodB_residual_model",
        dataset_name="test_residual",
    )

    metrics_direct.append(m_direct)
    metrics_methodB.append(m_methodB)
    baseline_metrics_test.append(m_baseline)
    residual_metrics_test.append(m_residual)

    print(
        "GBDT_Direct test: "
        f"R2={m_direct['R2']:.6f}, "
        f"MSE={m_direct['MSE']:.6f}, "
        f"RMSE={m_direct['RMSE']:.6f}, "
        f"MAE={m_direct['MAE']:.6f}, "
        f"ARD={m_direct['ARD(%)']:.6f}%"
    )

    print(
        "MethodB final test: "
        f"R2={m_methodB['R2']:.6f}, "
        f"MSE={m_methodB['MSE']:.6f}, "
        f"RMSE={m_methodB['RMSE']:.6f}, "
        f"MAE={m_methodB['MAE']:.6f}, "
        f"ARD={m_methodB['ARD(%)']:.6f}%"
    )

    print(
        "MethodB baseline only test: "
        f"R2={m_baseline['R2']:.6f}, "
        f"MSE={m_baseline['MSE']:.6f}, "
        f"RMSE={m_baseline['RMSE']:.6f}, "
        f"MAE={m_baseline['MAE']:.6f}, "
        f"ARD={m_baseline['ARD(%)']:.6f}%"
    )

    # =====================================================
    # 9.5 新增：每个 fold 模型预测完整数据集，统计完整数据集三档偏差数量
    # =====================================================
    count_direct_all = count_error_thresholds(y, y_pred_direct_all)
    count_methodB_all = count_error_thresholds(y, y_pred_methodB_all)

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "GBDT_Direct",
        **count_direct_all,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "MethodB_LinearBaseline+GBDT_residual",
        **count_methodB_all,
    })

    print("\nGBDT_Direct fold model predicts ALL data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "GBDT_Direct",
        **count_direct_all,
    }]).to_string(index=False))

    print("\nMethodB final fold model predicts ALL data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "MethodB_LinearBaseline+GBDT_residual",
        **count_methodB_all,
    }]).to_string(index=False))

    # =====================================================
    # 9.6 保存预测明细：测试集
    # =====================================================
    df_test_direct = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="GBDT_Direct",
        sample_indices=test_indices,
        y_true=y_test,
        y_pred=y_pred_direct_test,
    )

    df_test_methodB = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="MethodB_LinearBaseline+GBDT_residual",
        sample_indices=test_indices,
        y_true=y_test,
        y_pred=y_pred_methodB_test,
        baseline_pred=baseline_pred_test,
        residual_pred=residual_pred_test,
    )

    fold_test_prediction_dfs.append(df_test_direct)
    fold_test_prediction_dfs.append(df_test_methodB)

    # =====================================================
    # 9.7 保存预测明细：完整数据集
    # =====================================================
    df_all_direct = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="GBDT_Direct",
        sample_indices=all_sample_indices,
        y_true=y,
        y_pred=y_pred_direct_all,
    )

    df_all_methodB = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="MethodB_LinearBaseline+GBDT_residual",
        sample_indices=all_sample_indices,
        y_true=y,
        y_pred=y_pred_methodB_all,
        baseline_pred=baseline_pred_all,
        residual_pred=residual_pred_all,
    )

    fold_all_data_prediction_dfs.append(df_all_direct)
    fold_all_data_prediction_dfs.append(df_all_methodB)

    # =====================================================
    # 9.8 保存参数、特征重要性和 fold 信息
    # =====================================================
    if hasattr(base_model, "coef_"):
        for group_name, coef_value in zip(used_group_cols, base_model.coef_):
            baseline_param_records.append({
                "fold": fold,
                "group_name": group_name,
                "baseline_coef_for_Nk_deltaT": coef_value,
                "abs_baseline_coef": abs(coef_value),
            })

    if hasattr(model_direct, "feature_importances_"):
        for feature_name, importance in zip(direct_feature_names, model_direct.feature_importances_):
            direct_feature_importance_records.append({
                "fold": fold,
                "feature": feature_name,
                "importance": importance,
            })

    if res_model is not None and hasattr(res_model, "feature_importances_"):
        for feature_name, importance in zip(residual_feature_names, res_model.feature_importances_):
            residual_feature_importance_records.append({
                "fold": fold,
                "feature": feature_name,
                "importance": importance,
            })

    fold_info_records.append({
        "fold": fold,
        "n_train_materials": len(train_mats),
        "n_test_materials": len(test_mats),
        "n_train_points": len(train_indices),
        "n_test_points": len(test_indices),
        "n_all_data_points": len(y),
        "n_group_features": len(used_group_cols),
        "direct_n_features": X_train_direct.shape[1],
        "baseline_n_features": X_base_train.shape[1],
        "residual_n_features": residual_X_train.shape[1],
        "baseline_model": baseline_model_name,
        "residual_model_trained": res_model is not None,
    })


# =========================================================
# 10. 汇总统计
# =========================================================
df_direct = pd.DataFrame(metrics_direct)
df_methodB = pd.DataFrame(metrics_methodB)
df_baseline_metrics = pd.DataFrame(baseline_metrics_test)
df_residual_metrics = pd.DataFrame(residual_metrics_test)

summary_direct = summarize(df_direct, "GBDT_Direct")
summary_methodB = summarize(df_methodB, "MethodB_LinearBaseline+GBDT_residual")
summary_baseline = summarize(df_baseline_metrics, "MethodB_baseline_only")
summary_residual = summarize(df_residual_metrics, "MethodB_residual_model")

summary_all = pd.concat(
    [
        summary_direct,
        summary_methodB,
        summary_baseline,
        summary_residual,
    ],
    ignore_index=True,
)

print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
print(summary_all.to_string(index=False))


# =========================================================
# 11. 配对t检验
# =========================================================
t_test_results = []

for metric in ["R2", "MSE", "RMSE", "MAE", "ARD(%)"]:
    vals_direct = df_direct[metric].dropna().values
    vals_methodB = df_methodB[metric].dropna().values

    if len(vals_direct) == len(vals_methodB) and len(vals_direct) > 1:
        t_stat, p_val = ttest_rel(vals_direct, vals_methodB)

        if metric in ["MSE", "RMSE", "MAE", "ARD(%)"]:
            better = "MethodB" if np.mean(vals_methodB) < np.mean(vals_direct) else "GBDT_Direct"
        else:
            better = "MethodB" if np.mean(vals_methodB) > np.mean(vals_direct) else "GBDT_Direct"

        significant = p_val < 0.05

        t_test_results.append({
            "Metric": metric,
            "Mean_GBDT_Direct": f"{np.mean(vals_direct):.4f}",
            "Mean_MethodB": f"{np.mean(vals_methodB):.4f}",
            "p-value": f"{p_val:.4e}",
            "Significant (p<0.05)": significant,
            "Better model": better,
        })

df_ttest = pd.DataFrame(t_test_results)

print("\n========== Paired t-test (GBDT_Direct vs MethodB) ==========")
print(df_ttest.to_string(index=False))


# =========================================================
# 12. 新增：完整数据集预测偏差数量统计汇总
# =========================================================
df_fold_all_data_count_summary = pd.DataFrame(fold_all_data_count_records)

final_average_records = []

for method_name, sub in df_fold_all_data_count_summary.groupby("Method"):
    final_average_records.append({
        "Method": method_name,
        "mean_count_rel_err_lt_1pct": sub["count_rel_err_lt_1pct"].mean(),
        "mean_count_rel_err_lt_5pct": sub["count_rel_err_lt_5pct"].mean(),
        "mean_count_rel_err_lt_10pct": sub["count_rel_err_lt_10pct"].mean(),
        "std_count_rel_err_lt_1pct": sub["count_rel_err_lt_1pct"].std(ddof=1),
        "std_count_rel_err_lt_5pct": sub["count_rel_err_lt_5pct"].std(ddof=1),
        "std_count_rel_err_lt_10pct": sub["count_rel_err_lt_10pct"].std(ddof=1),
        "n_folds": len(sub),
        "n_all_data_points": len(y),
    })

df_final_average_summary = pd.DataFrame(final_average_records)

print("\n========== Fold all-data count summary ==========")
print(df_fold_all_data_count_summary.to_string(index=False))

print("\n========== Final average all-data count summary ==========")
print(df_final_average_summary.to_string(index=False))


# =========================================================
# 13. 整理输出表
# =========================================================
df_fold_test_predictions = pd.concat(fold_test_prediction_dfs, ignore_index=True)
df_fold_all_data_predictions = pd.concat(fold_all_data_prediction_dfs, ignore_index=True)

# 补充物质/原始数据信息
extra_cols = [
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
]

for df_pred in [df_fold_test_predictions, df_fold_all_data_predictions]:
    for col in extra_cols:
        if col in df_data.columns:
            values = []
            for row_idx in df_pred["original_data_row_index"].values:
                values.append(df_data.iloc[int(row_idx)][col])
            df_pred[col] = values

df_fold_info = pd.DataFrame(fold_info_records)
df_baseline_params = pd.DataFrame(baseline_param_records)
df_direct_feature_importance = pd.DataFrame(direct_feature_importance_records)
df_residual_feature_importance = pd.DataFrame(residual_feature_importance_records)

group_occurrence_all = (df_groups_used != 0).sum(axis=0)
group_total_count_all = df_groups_used.sum(axis=0)

df_used_groups = pd.DataFrame({
    "used_group": used_group_cols,
    "occurrence_all_materials": group_occurrence_all[used_group_cols].values,
    "total_count_all": group_total_count_all[used_group_cols].values,
})

df_removed_zero_groups = pd.DataFrame({
    "removed_all_zero_group": removed_zero_group_cols,
})

df_run_params = pd.DataFrame([
    {"param": "file_path", "value": str(file_path)},
    {"param": "groups_sheet", "value": groups_sheet},
    {"param": "data_sheet", "value": data_sheet},
    {"param": "anchor_sheet", "value": anchor_sheet},
    {"param": "n_outer_folds", "value": n_outer_folds},
    {"param": "random_state", "value": random_state},
    {"param": "n_points_per_material", "value": n_points_per_material},
    {"param": "n_materials", "value": n_materials},
    {"param": "n_all_data_points", "value": len(y)},
    {"param": "n_group_features", "value": len(used_group_cols)},
    {"param": "gbdt_direct_params", "value": str(gbdt_direct_params)},
    {"param": "residual_gbdt_params", "value": str(residual_gbdt_params)},
    {"param": "anchor_gbdt_params", "value": str(anchor_gbdt_params)},
    {"param": "use_ridge_for_baseline", "value": use_ridge_for_baseline},
    {"param": "baseline_ridge_alpha", "value": baseline_ridge_alpha},
    {
        "param": "relative_error_definition",
        "value": "abs((y_pred - y_true) / y_true) * 100; abs(y_true)<=1e-12 -> NaN",
    },
    {
        "param": "full_data_count_rule",
        "value": "Each fold model predicts the whole dataset; count rel_err <1%, <5%, <10%; then average counts over 5 folds.",
    },
])


# =========================================================
# 14. 模型结构汇总
# =========================================================
df_model_structure = pd.DataFrame([
    {
        "项目": "预测对象",
        "内容": "定压热容 Cp / property_value",
    },
    {
        "项目": "主数据文件",
        "内容": str(file_path),
    },
    {
        "项目": "groups sheet",
        "内容": groups_sheet,
    },
    {
        "项目": "data sheet",
        "内容": data_sheet,
    },
    {
        "项目": "anchor sheet",
        "内容": anchor_sheet,
    },
    {
        "项目": "温度列",
        "内容": temp_col,
    },
    {
        "项目": "目标列",
        "内容": target_col,
    },
    {
        "项目": "交叉验证方式",
        "内容": f"{n_outer_folds}-fold KFold，按物质划分，shuffle=True，random_state={random_state}",
    },
    {
        "项目": "方法1",
        "内容": "GBDT_Direct：直接 GBDT 预测 Cp",
    },
    {
        "项目": "方法1最终模型类型",
        "内容": "GradientBoostingRegressor",
    },
    {
        "项目": "方法1模型参数",
        "内容": str(gbdt_direct_params),
    },
    {
        "项目": "方法1输入特征",
        "内容": f"[Nk, T]，其中 Nk 为 {len(used_group_cols)} 个有效基团特征，总维度 {len(used_group_cols) + 1}",
    },
    {
        "项目": "方法2",
        "内容": "MethodB_LinearBaseline+GBDT_residual：锚点线性基线 + GBDT 残差修正",
    },
    {
        "项目": "方法2最终预测公式",
        "内容": "Cp_pred = baseline_pred + residual_pred",
    },
    {
        "项目": "锚点子模型",
        "内容": "全局训练两个 GBDT 子模型：一个预测 anchor_Cp，一个预测 boiling_T；anchor_T = k1 * boiling_T_pred",
    },
    {
        "项目": "锚点子模型参数",
        "内容": str(anchor_gbdt_params),
    },
    {
        "项目": "锚点子模型输入特征",
        "内容": f"Nk，有效基团特征数 {len(used_group_cols)}",
    },
    {
        "项目": "锚点 Cp 目标列",
        "内容": anchor_cp_target_col,
    },
    {
        "项目": "沸点目标列",
        "内容": boiling_col,
    },
    {
        "项目": "k1 来源",
        "内容": f"优先使用 {k1_col}；若无，则使用 {k1_times_boiling_col} / {boiling_col}",
    },
    {
        "项目": "baseline 构造方式",
        "内容": "baseline_pred = anchor_Cp_pred + base_model(Nk * (T - anchor_T_pred))",
    },
    {
        "项目": "baseline 模型",
        "内容": f"{'Ridge' if use_ridge_for_baseline else 'LinearRegression'}(fit_intercept=False)",
    },
    {
        "项目": "baseline 参数",
        "内容": f"baseline_ridge_alpha={baseline_ridge_alpha}" if use_ridge_for_baseline else "LinearRegression 无 alpha",
    },
    {
        "项目": "residual 构造方式",
        "内容": "residual_y = Cp_true - baseline_pred；residual_pred = GBDT([Nk, T])",
    },
    {
        "项目": "residual 模型",
        "内容": "GradientBoostingRegressor",
    },
    {
        "项目": "residual 模型参数",
        "内容": str(residual_gbdt_params),
    },
    {
        "项目": "residual 输入特征",
        "内容": f"[Nk, T]，总维度 {len(used_group_cols) + 1}",
    },
    {
        "项目": "最终模型",
        "内容": "方法1为直接 GBDT；方法2为 baseline + residual GBDT",
    },
    {
        "项目": "偏差数量统计口径",
        "内容": "每个 fold 训练出的最终模型都预测完整数据集，统计相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 取平均",
    },
])


# =========================================================
# 15. 保存Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    # 原有核心输出
    df_direct.to_excel(writer, sheet_name="Fold_Metrics_GBDT_Direct", index=False)
    df_methodB.to_excel(writer, sheet_name="Fold_Metrics_MethodB", index=False)
    summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
    df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)
    df_run_params.to_excel(writer, sheet_name="Run_Params", index=False)

    # 新增/扩展输出
    df_baseline_metrics.to_excel(writer, sheet_name="Baseline_Metrics_Test", index=False)
    df_residual_metrics.to_excel(writer, sheet_name="Residual_Metrics_Test", index=False)

    df_fold_test_predictions.to_excel(writer, sheet_name="fold_test_predictions", index=False)
    df_fold_all_data_predictions.to_excel(writer, sheet_name="fold_all_data_predictions", index=False)

    df_fold_all_data_count_summary.to_excel(writer, sheet_name="fold_all_data_count_summary", index=False)
    df_final_average_summary.to_excel(writer, sheet_name="final_average_summary", index=False)

    df_anchor_submodel_summary.to_excel(writer, sheet_name="submodel_summary", index=False)
    df_anchor_submodel_predictions.to_excel(writer, sheet_name="submodel_predictions", index=False)

    df_baseline_params.to_excel(writer, sheet_name="baseline_params", index=False)
    df_direct_feature_importance.to_excel(writer, sheet_name="direct_feature_importance", index=False)
    df_residual_feature_importance.to_excel(writer, sheet_name="residual_feature_importance", index=False)

    df_fold_info.to_excel(writer, sheet_name="Fold_Info", index=False)
    df_used_groups.to_excel(writer, sheet_name="Used_Groups", index=False)
    df_removed_zero_groups.to_excel(writer, sheet_name="Removed_Zero_Groups", index=False)
    df_model_structure.to_excel(writer, sheet_name="model_structure", index=False)

    format_excel(writer)

print(f"\n所有结果已保存至: {output_file}")


# =========================================================
# 16. 最终方便复制输出
# =========================================================
def get_final_counts(method_name):
    row = df_final_average_summary[df_final_average_summary["Method"] == method_name]

    if row.empty:
        return np.nan, np.nan, np.nan

    row = row.iloc[0]

    return (
        row["mean_count_rel_err_lt_1pct"],
        row["mean_count_rel_err_lt_5pct"],
        row["mean_count_rel_err_lt_10pct"],
    )


direct_1, direct_5, direct_10 = get_final_counts("GBDT_Direct")
methodB_1, methodB_5, methodB_10 = get_final_counts("MethodB_LinearBaseline+GBDT_residual")

print("\n方法1 全数据预测偏差 1%，5%，10%分别为：")
print(direct_1)
print(direct_5)
print(direct_10)

print("\n方法2 全数据预测偏差 1%，5%，10%分别为：")
print(methodB_1)
print(methodB_5)
print(methodB_10)


# =========================================================
# 17. 代码结构打印
# =========================================================
print("\n========== 当前代码结构简要汇总 ==========")
print("预测对象：Cp / property_value")
print(f"数据文件：{file_path}")
print(f"sheet 名称：{groups_sheet}, {data_sheet}, {anchor_sheet}")
print(f"交叉验证：{n_outer_folds}-fold，按物质划分")
print("方法1：GBDT_Direct，GradientBoostingRegressor，输入 [Nk, T]")
print("方法2：MethodB_LinearBaseline+GBDT_residual，锚点线性基线 + GBDT 残差修正")
print("锚点子模型：全局训练 GBDT，分别预测 anchor_Cp 与 boiling_T")
print(f"锚点子模型参数：{anchor_gbdt_params}")
print("slope / anchor_T 构造：anchor_T = k1 * boiling_T_pred")
print("baseline 构造：baseline_pred = anchor_Cp_pred + base_model(Nk * (T - anchor_T_pred))")
print(f"baseline 模型：{'Ridge' if use_ridge_for_baseline else 'LinearRegression'}(fit_intercept=False)")
print(f"baseline 参数：baseline_ridge_alpha={baseline_ridge_alpha}")
print("residual 构造：residual_y = Cp_true - baseline_pred")
print(f"residual 模型：GradientBoostingRegressor，参数：{residual_gbdt_params}")
print(f"方法1最终模型参数：{gbdt_direct_params}")
print("方法1最终输入：[Nk, T]")
print("方法2最终输入：baseline 使用 Nk*(T-anchor_T_pred)，residual 使用 [Nk, T]")
print("偏差统计口径：每个 fold 模型预测完整数据集，统计 <1%、<5%、<10% 点数，再对 5 个 fold 取平均")