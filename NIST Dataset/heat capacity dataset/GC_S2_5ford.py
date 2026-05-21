# import pandas as pd
# import numpy as np
# from pathlib import Path
#
# from sklearn.linear_model import Ridge
# from sklearn.preprocessing import StandardScaler
# from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
# from sklearn.model_selection import KFold
# from scipy.stats import ttest_rel
#
# import warnings
# warnings.filterwarnings("ignore")
#
# pd.set_option("display.float_format", "{:.10f}".format)
# np.set_printoptions(suppress=True, precision=10)
#
#
# # =========================================================
# # 1. 文件路径与 sheet 设置
# # =========================================================
# file_path = Path("Cp_dataset_selected_by_two_k_with_interpolation.xlsx")
#
# groups_sheet = "groups_selected"
# data_sheet = "Sheet1_selected"
# anchor_sheet = "Interpolated_k1_k2"
#
# output_file = Path("Cp_5fold_anchor_vs_explicit_linear_T_same_fixed_Ridge.xlsx")
#
#
# # =========================================================
# # 2. 基本设置
# # =========================================================
# n_points_per_material = 8
#
# temp_col = "T_K"
# target_col = "property_value"
#
# # 锚点：温度与该温度下的热容
# anchor_temp_col = "k1_times_boiling_T_K"
# anchor_value_col = "property_interp_at_k1Tb"
#
# random_state = 42
# n_outer_folds = 5
#
# # groups_selected 中基团列范围
# # 如果你的 groups_selected 因插入 original_material_index 后基团从第4列开始，
# # 可以改成 group_start_idx = 3, group_end_idx = 222
# group_start_idx = 2
# group_end_idx = 221
#
# # =========================================================
# # 统一回归参数
# # 两个基线完全相同
# # =========================================================
# common_ridge_alpha = 1.0
# common_fit_intercept = False
# common_with_mean = False
#
# common_regressor_name = (
#     f"StandardScaler(with_mean={common_with_mean}) + "
#     f"Ridge(alpha={common_ridge_alpha}, fit_intercept={common_fit_intercept})"
# )
#
#
# # =========================================================
# # 3. 工具函数
# # =========================================================
# def calc_metrics(y_true, y_pred, dataset_name, model_name):
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#
#     mask = np.isfinite(y_true) & np.isfinite(y_pred)
#
#     y_true = y_true[mask]
#     y_pred = y_pred[mask]
#
#     if len(y_true) == 0:
#         return {
#             "model": model_name,
#             "dataset": dataset_name,
#             "n_points": 0,
#             "R2": np.nan,
#             "MSE": np.nan,
#             "RMSE": np.nan,
#             "MAE": np.nan,
#             "ARD_percent": np.nan,
#             "max_abs_error": np.nan,
#             "max_relative_error_percent": np.nan,
#             "relative_error_le_1_percent_ratio": np.nan,
#             "relative_error_le_5_percent_ratio": np.nan,
#             "relative_error_le_10_percent_ratio": np.nan,
#             "relative_error_le_1_percent_count": 0,
#             "relative_error_le_5_percent_count": 0,
#             "relative_error_le_10_percent_count": 0,
#         }
#
#     error = y_pred - y_true
#     abs_error = np.abs(error)
#
#     valid_rel = np.abs(y_true) > 1e-12
#
#     if valid_rel.sum() > 0:
#         rel_err = np.abs((y_pred[valid_rel] - y_true[valid_rel]) / y_true[valid_rel]) * 100
#
#         ard = np.mean(rel_err)
#         max_rel = np.max(rel_err)
#
#         count_1 = int(np.sum(rel_err <= 1))
#         count_5 = int(np.sum(rel_err <= 5))
#         count_10 = int(np.sum(rel_err <= 10))
#
#         ratio_1 = count_1 / len(rel_err) * 100
#         ratio_5 = count_5 / len(rel_err) * 100
#         ratio_10 = count_10 / len(rel_err) * 100
#
#     else:
#         ard = np.nan
#         max_rel = np.nan
#
#         count_1 = 0
#         count_5 = 0
#         count_10 = 0
#
#         ratio_1 = np.nan
#         ratio_5 = np.nan
#         ratio_10 = np.nan
#
#     mse = mean_squared_error(y_true, y_pred)
#     rmse = np.sqrt(mse)
#     mae = mean_absolute_error(y_true, y_pred)
#
#     try:
#         r2 = r2_score(y_true, y_pred)
#     except Exception:
#         r2 = np.nan
#
#     return {
#         "model": model_name,
#         "dataset": dataset_name,
#         "n_points": len(y_true),
#         "R2": r2,
#         "MSE": mse,
#         "RMSE": rmse,
#         "MAE": mae,
#         "ARD_percent": ard,
#         "max_abs_error": np.max(abs_error),
#         "max_relative_error_percent": max_rel,
#         "relative_error_le_1_percent_ratio": ratio_1,
#         "relative_error_le_5_percent_ratio": ratio_5,
#         "relative_error_le_10_percent_ratio": ratio_10,
#         "relative_error_le_1_percent_count": count_1,
#         "relative_error_le_5_percent_count": count_5,
#         "relative_error_le_10_percent_count": count_10,
#     }
#
#
# def fit_fixed_ridge_same_params(X_train, y_train, X_pred, model_label):
#     """
#     统一回归器：
#         StandardScaler(with_mean=False)
#         Ridge(alpha=common_ridge_alpha, fit_intercept=False)
#
#     说明：
#     1. 两个模型使用完全相同的 alpha。
#     2. 两个模型使用完全相同的 fit_intercept 设置。
#     3. 两个模型使用完全相同的标准化方式。
#     4. 显式一阶 T 模型不额外添加常数列，因此没有全局截距 b0。
#     """
#     X_train = np.asarray(X_train, dtype=float)
#     y_train = np.asarray(y_train, dtype=float)
#     X_pred = np.asarray(X_pred, dtype=float)
#
#     valid_train = (
#         np.isfinite(X_train).all(axis=1)
#         & np.isfinite(y_train)
#     )
#
#     X_train_fit = X_train[valid_train]
#     y_train_fit = y_train[valid_train]
#
#     if len(y_train_fit) == 0:
#         raise ValueError(f"{model_label}: 没有有效训练样本。")
#
#     scaler = StandardScaler(with_mean=common_with_mean)
#
#     X_train_scaled = scaler.fit_transform(X_train_fit)
#     X_pred_scaled = scaler.transform(X_pred)
#
#     model = Ridge(
#         alpha=common_ridge_alpha,
#         fit_intercept=common_fit_intercept,
#     )
#
#     model.fit(X_train_scaled, y_train_fit)
#
#     y_pred = model.predict(X_pred_scaled)
#
#     # 还原到原始特征尺度
#     coef_scaled = model.coef_.astype(float)
#
#     x_scale = scaler.scale_.astype(float)
#     x_scale_safe = np.where(x_scale == 0, 1.0, x_scale)
#
#     coef_original = coef_scaled / x_scale_safe
#
#     model_info = {
#         "model_label": model_label,
#         "regressor": common_regressor_name,
#         "common_ridge_alpha": common_ridge_alpha,
#         "common_fit_intercept": common_fit_intercept,
#         "common_with_mean": common_with_mean,
#         "n_train_samples": len(y_train_fit),
#         "n_features": X_train.shape[1],
#         "model": model,
#         "scaler": scaler,
#         "coef_scaled": coef_scaled,
#         "coef_original": coef_original,
#     }
#
#     return y_pred, model_info
#
#
# def summarize_fold_metrics(df_metrics, model_name):
#     rows = []
#
#     sub = df_metrics[
#         (df_metrics["model"] == model_name)
#         & (df_metrics["dataset"] == "test")
#     ].copy()
#
#     for metric in [
#         "R2",
#         "MSE",
#         "RMSE",
#         "MAE",
#         "ARD_percent",
#         "relative_error_le_1_percent_ratio",
#         "relative_error_le_5_percent_ratio",
#         "relative_error_le_10_percent_ratio",
#     ]:
#         vals = sub[metric].dropna().values
#
#         if len(vals) == 0:
#             mean_val = np.nan
#             std_val = np.nan
#             mean_std = "NaN"
#         elif len(vals) == 1:
#             mean_val = float(np.mean(vals))
#             std_val = np.nan
#             mean_std = f"{mean_val:.10f} ± NaN"
#         else:
#             mean_val = float(np.mean(vals))
#             std_val = float(np.std(vals, ddof=1))
#             mean_std = f"{mean_val:.10f} ± {std_val:.10f}"
#
#         rows.append({
#             "model": model_name,
#             "metric": metric,
#             "mean": mean_val,
#             "std": std_val,
#             "mean±std": mean_std,
#         })
#
#     return pd.DataFrame(rows)
#
#
# def paired_t_test_fold_metrics(df_metrics, model_a, model_b):
#     rows = []
#
#     sub_a = df_metrics[
#         (df_metrics["model"] == model_a)
#         & (df_metrics["dataset"] == "test")
#     ].sort_values("fold")
#
#     sub_b = df_metrics[
#         (df_metrics["model"] == model_b)
#         & (df_metrics["dataset"] == "test")
#     ].sort_values("fold")
#
#     for metric in [
#         "R2",
#         "MSE",
#         "RMSE",
#         "MAE",
#         "ARD_percent",
#         "relative_error_le_1_percent_ratio",
#         "relative_error_le_5_percent_ratio",
#         "relative_error_le_10_percent_ratio",
#     ]:
#         vals_a = sub_a[metric].values.astype(float)
#         vals_b = sub_b[metric].values.astype(float)
#
#         valid = np.isfinite(vals_a) & np.isfinite(vals_b)
#
#         vals_a = vals_a[valid]
#         vals_b = vals_b[valid]
#
#         if len(vals_a) > 1:
#             t_stat, p_value = ttest_rel(vals_a, vals_b)
#
#             if metric in ["R2", "relative_error_le_1_percent_ratio", "relative_error_le_5_percent_ratio", "relative_error_le_10_percent_ratio"]:
#                 better = model_a if np.mean(vals_a) > np.mean(vals_b) else model_b
#             else:
#                 better = model_a if np.mean(vals_a) < np.mean(vals_b) else model_b
#
#             rows.append({
#                 "metric": metric,
#                 "model_a": model_a,
#                 "model_b": model_b,
#                 "mean_model_a": np.mean(vals_a),
#                 "mean_model_b": np.mean(vals_b),
#                 "t_stat": t_stat,
#                 "p_value": p_value,
#                 "significant_p_lt_0.05": p_value < 0.05,
#                 "better_model_by_mean": better,
#             })
#
#         else:
#             rows.append({
#                 "metric": metric,
#                 "model_a": model_a,
#                 "model_b": model_b,
#                 "mean_model_a": np.nan,
#                 "mean_model_b": np.nan,
#                 "t_stat": np.nan,
#                 "p_value": np.nan,
#                 "significant_p_lt_0.05": False,
#                 "better_model_by_mean": "insufficient_valid_folds",
#             })
#
#     return pd.DataFrame(rows)
#
#
# def format_excel(writer, number_format="0.0000000000"):
#     for sheet_name in writer.sheets:
#         ws = writer.sheets[sheet_name]
#
#         for row in ws.iter_rows():
#             for cell in row:
#                 if isinstance(cell.value, float):
#                     cell.number_format = number_format
#
#         for col_cells in ws.columns:
#             max_length = 0
#             col_letter = col_cells[0].column_letter
#
#             for cell in col_cells:
#                 if cell.value is not None:
#                     max_length = max(max_length, len(str(cell.value)))
#
#             ws.column_dimensions[col_letter].width = min(max_length + 2, 35)
#
#
# # =========================================================
# # 4. 读取数据
# # =========================================================
# df_groups_raw = pd.read_excel(file_path, sheet_name=groups_sheet)
# df_data = pd.read_excel(file_path, sheet_name=data_sheet)
# df_anchor = pd.read_excel(file_path, sheet_name=anchor_sheet)
#
# print("groups 表行数:", len(df_groups_raw))
# print("Sheet1_selected 行数:", len(df_data))
# print("anchor sheet 行数:", len(df_anchor))
#
#
# # =========================================================
# # 5. 读取并对齐锚点
# # =========================================================
# for col in [anchor_temp_col, anchor_value_col]:
#     if col not in df_anchor.columns:
#         raise ValueError(f"{anchor_sheet} 中没有找到列: {col}")
#
# df_anchor[anchor_temp_col] = pd.to_numeric(df_anchor[anchor_temp_col], errors="coerce")
# df_anchor[anchor_value_col] = pd.to_numeric(df_anchor[anchor_value_col], errors="coerce")
#
# if "original_material_index" in df_groups_raw.columns and "original_material_index" in df_anchor.columns:
#     anchor_temp_map = (
#         df_anchor[["original_material_index", anchor_temp_col]]
#         .drop_duplicates(subset=["original_material_index"])
#         .set_index("original_material_index")[anchor_temp_col]
#     )
#
#     anchor_value_map = (
#         df_anchor[["original_material_index", anchor_value_col]]
#         .drop_duplicates(subset=["original_material_index"])
#         .set_index("original_material_index")[anchor_value_col]
#     )
#
#     df_groups_raw["anchor_T_ref1"] = df_groups_raw["original_material_index"].map(anchor_temp_map)
#     df_groups_raw["anchor_Cp_ref1"] = df_groups_raw["original_material_index"].map(anchor_value_map)
#
#     print("使用 original_material_index 对齐锚点。")
#
# else:
#     if len(df_groups_raw) != len(df_anchor):
#         raise ValueError(
#             "无法使用 original_material_index 对齐锚点，"
#             "且 groups 表与 anchor sheet 行数不一致。"
#         )
#
#     df_groups_raw["anchor_T_ref1"] = df_anchor[anchor_temp_col].values
#     df_groups_raw["anchor_Cp_ref1"] = df_anchor[anchor_value_col].values
#
#     print("没有 original_material_index，按行顺序对齐锚点。")
#
#
# # =========================================================
# # 6. 删除无效锚点对应物质
# # =========================================================
# anchor_T_raw = pd.to_numeric(df_groups_raw["anchor_T_ref1"], errors="coerce").values.astype(float)
# anchor_Cp_raw = pd.to_numeric(df_groups_raw["anchor_Cp_ref1"], errors="coerce").values.astype(float)
#
# valid_anchor_mask = np.isfinite(anchor_T_raw) & np.isfinite(anchor_Cp_raw)
#
# invalid_anchor_count = int((~valid_anchor_mask).sum())
# print("无效锚点物质数:", invalid_anchor_count)
#
# if invalid_anchor_count > 0:
#     keep_data_indices = []
#
#     for material_idx, keep in enumerate(valid_anchor_mask):
#         if keep:
#             start = material_idx * n_points_per_material
#             end = start + n_points_per_material
#             keep_data_indices.extend(range(start, end))
#
#     df_groups_raw = df_groups_raw.loc[valid_anchor_mask].reset_index(drop=True)
#     df_data = df_data.iloc[keep_data_indices].reset_index(drop=True)
#
# print("过滤后 groups 表行数:", len(df_groups_raw))
# print("过滤后 Sheet1_selected 行数:", len(df_data))
#
#
# # =========================================================
# # 7. 读取基团列，并删除全零列
# # =========================================================
# group_cols_raw = df_groups_raw.columns[group_start_idx:group_end_idx].tolist()
#
# exclude_cols = {
#     "original_material_index",
#     "compound_name",
#     "cas",
#     "formula",
#     "SMILES",
#     "smiles",
#     "pubchem_cid",
#     "material_key",
#     "phase",
#     "boiling_T_K",
#     "critical_T_K",
#     "anchor_T",
#     "anchor_Cp",
#     "anchor_T_ref1",
#     "anchor_Cp_ref1",
# }
#
# group_cols_raw = [c for c in group_cols_raw if c not in exclude_cols]
#
# df_groups = df_groups_raw[group_cols_raw].copy()
# df_groups = df_groups.apply(pd.to_numeric, errors="coerce").fillna(0.0)
#
# print("原始基团列数量:", len(group_cols_raw))
#
# nonzero_mask = df_groups.abs().sum(axis=0) != 0
#
# used_group_cols = df_groups.columns[nonzero_mask].tolist()
# removed_zero_group_cols = df_groups.columns[~nonzero_mask].tolist()
#
# df_groups_used = df_groups[used_group_cols].copy()
# X_groups = df_groups_used.values.astype(float)
#
# print("删除全零列后基团列数量:", len(used_group_cols))
# print("被删除全零基团列数量:", len(removed_zero_group_cols))
#
#
# # =========================================================
# # 8. 检查 Sheet1_selected
# # =========================================================
# if temp_col not in df_data.columns:
#     raise ValueError(f"{data_sheet} 中没有找到温度列: {temp_col}")
#
# if target_col not in df_data.columns:
#     raise ValueError(f"{data_sheet} 中没有找到热容列: {target_col}")
#
# if len(df_data) % n_points_per_material != 0:
#     raise ValueError(
#         f"{data_sheet} 行数 {len(df_data)} 不能被 {n_points_per_material} 整除。"
#         "请检查是否每个物质都是 8 行。"
#     )
#
# n_materials_data = len(df_data) // n_points_per_material
# n_materials_groups = len(df_groups_used)
#
# print("Sheet1_selected 中物质数量:", n_materials_data)
# print("groups 中物质数量:", n_materials_groups)
#
# if n_materials_data != n_materials_groups:
#     raise ValueError(
#         "Sheet1_selected 中物质数量和 groups 表行数不一致。\n"
#         f"Sheet1_selected 物质数 = {n_materials_data}, groups 行数 = {n_materials_groups}"
#     )
#
#
# # =========================================================
# # 9. 展开温度点数据
# # =========================================================
# all_targets = []
# material_ids = []
# temperatures = []
# anchor_T_rows = []
# anchor_Cp_rows = []
# original_row_indices = []
#
# anchor_T_per_material = pd.to_numeric(
#     df_groups_raw["anchor_T_ref1"],
#     errors="coerce",
# ).values.astype(float)
#
# anchor_Cp_per_material = pd.to_numeric(
#     df_groups_raw["anchor_Cp_ref1"],
#     errors="coerce",
# ).values.astype(float)
#
# for material_idx in range(n_materials_groups):
#     start = material_idx * n_points_per_material
#     end = start + n_points_per_material
#
#     sub_data = df_data.iloc[start:end].copy()
#
#     T_values = pd.to_numeric(sub_data[temp_col], errors="coerce").values.astype(float)
#     Cp_values = pd.to_numeric(sub_data[target_col], errors="coerce").values.astype(float)
#
#     anchor_T = anchor_T_per_material[material_idx]
#     anchor_Cp = anchor_Cp_per_material[material_idx]
#
#     for local_i, (T, Cp) in enumerate(zip(T_values, Cp_values)):
#         if not np.isfinite(T) or not np.isfinite(Cp):
#             continue
#
#         if not np.isfinite(anchor_T) or not np.isfinite(anchor_Cp):
#             continue
#
#         all_targets.append(Cp)
#         material_ids.append(material_idx)
#         temperatures.append(T)
#         anchor_T_rows.append(anchor_T)
#         anchor_Cp_rows.append(anchor_Cp)
#         original_row_indices.append(start + local_i)
#
# y = np.array(all_targets, dtype=float)
# material_ids = np.array(material_ids, dtype=int)
# temperatures = np.array(temperatures, dtype=float)
# anchor_T_rows = np.array(anchor_T_rows, dtype=float)
# anchor_Cp_rows = np.array(anchor_Cp_rows, dtype=float)
# original_row_indices = np.array(original_row_indices, dtype=int)
#
# print("展开后样本点数:", len(y))
#
#
# # =========================================================
# # 10. 构造两个基线的特征矩阵
# # =========================================================
# all_sample_indices = np.arange(len(y))
#
#
# def build_anchor_baseline_X(sample_indices):
#     """
#     锚点基线：
#         Cp = Cp_anchor + (T - T_anchor) * sum(Nk * Ak)
#
#     训练目标：
#         Cp - Cp_anchor
#
#     特征：
#         Nk * (T - T_anchor)
#     """
#     sample_indices = np.asarray(sample_indices, dtype=int)
#
#     mat_ids = material_ids[sample_indices]
#     T = temperatures[sample_indices]
#     anchor_T = anchor_T_rows[sample_indices]
#
#     delta_T = T - anchor_T
#     group_feat = X_groups[mat_ids]
#
#     X_base = group_feat * delta_T.reshape(-1, 1)
#
#     return X_base
#
#
# def build_explicit_linear_T_X(sample_indices):
#     """
#     显式一阶 T 模型：
#         Cp = sum(Nk * Ak) + sum(Nk * Bk * T)
#
#     不加全局截距 b0。
#
#     特征：
#         [Nk, Nk*T]
#     """
#     sample_indices = np.asarray(sample_indices, dtype=int)
#
#     mat_ids = material_ids[sample_indices]
#     T = temperatures[sample_indices]
#
#     group_feat = X_groups[mat_ids]
#
#     feature_A = group_feat
#     feature_B = group_feat * T.reshape(-1, 1)
#
#     X_explicit = np.hstack([
#         feature_A,
#         feature_B,
#     ])
#
#     return X_explicit
#
#
# X_anchor_all = build_anchor_baseline_X(all_sample_indices)
# X_explicit_all = build_explicit_linear_T_X(all_sample_indices)
#
# print("锚点基线特征数:", X_anchor_all.shape[1])
# print("显式一阶 T 模型特征数:", X_explicit_all.shape[1])
#
#
# # =========================================================
# # 11. 外层 5-fold by material
# # =========================================================
# unique_materials = np.unique(material_ids)
#
# if len(unique_materials) < n_outer_folds:
#     raise ValueError(
#         f"物质数 {len(unique_materials)} 小于 n_outer_folds={n_outer_folds}，无法做 5-fold。"
#     )
#
# outer_kf = KFold(
#     n_splits=n_outer_folds,
#     shuffle=True,
#     random_state=random_state,
# )
#
# # out-of-fold 预测
# oof_pred_anchor = np.full_like(y, np.nan, dtype=float)
# oof_pred_explicit = np.full_like(y, np.nan, dtype=float)
#
# fold_metrics = []
# prediction_records = []
# anchor_param_records = []
# explicit_param_records = []
# fold_info_records = []
#
# for fold, (train_mat_idx, test_mat_idx) in enumerate(outer_kf.split(unique_materials), start=1):
#     train_materials = unique_materials[train_mat_idx]
#     test_materials = unique_materials[test_mat_idx]
#
#     train_mask = np.isin(material_ids, train_materials)
#     test_mask = np.isin(material_ids, test_materials)
#
#     print(f"\n========== Fold {fold} ==========")
#     print("训练物质数:", len(train_materials))
#     print("测试物质数:", len(test_materials))
#     print("训练样本点数:", int(train_mask.sum()))
#     print("测试样本点数:", int(test_mask.sum()))
#
#     # -----------------------------------------------------
#     # 11.1 锚点基线
#     # -----------------------------------------------------
#     X_anchor_train = X_anchor_all[train_mask]
#     X_anchor_test = X_anchor_all[test_mask]
#
#     y_anchor_train_target = y[train_mask] - anchor_Cp_rows[train_mask]
#
#     anchor_delta_test, anchor_model_info = fit_fixed_ridge_same_params(
#         X_train=X_anchor_train,
#         y_train=y_anchor_train_target,
#         X_pred=X_anchor_test,
#         model_label="Anchor_baseline",
#     )
#
#     Cp_pred_anchor_test = anchor_Cp_rows[test_mask] + anchor_delta_test
#
#     # -----------------------------------------------------
#     # 11.2 显式一阶 T 模型
#     # -----------------------------------------------------
#     X_explicit_train = X_explicit_all[train_mask]
#     X_explicit_test = X_explicit_all[test_mask]
#
#     y_explicit_train_target = y[train_mask]
#
#     Cp_pred_explicit_test, explicit_model_info = fit_fixed_ridge_same_params(
#         X_train=X_explicit_train,
#         y_train=y_explicit_train_target,
#         X_pred=X_explicit_test,
#         model_label="Explicit_linear_T",
#     )
#
#     # -----------------------------------------------------
#     # 11.3 保存 out-of-fold 预测
#     # -----------------------------------------------------
#     oof_pred_anchor[test_mask] = Cp_pred_anchor_test
#     oof_pred_explicit[test_mask] = Cp_pred_explicit_test
#
#     # -----------------------------------------------------
#     # 11.4 每折评价
#     # -----------------------------------------------------
#     y_train = y[train_mask]
#     y_test = y[test_mask]
#
#     # 为了记录 train 指标，也生成 train prediction
#     anchor_delta_train, _ = fit_fixed_ridge_same_params(
#         X_train=X_anchor_train,
#         y_train=y_anchor_train_target,
#         X_pred=X_anchor_train,
#         model_label="Anchor_baseline_train_eval",
#     )
#     Cp_pred_anchor_train = anchor_Cp_rows[train_mask] + anchor_delta_train
#
#     Cp_pred_explicit_train, _ = fit_fixed_ridge_same_params(
#         X_train=X_explicit_train,
#         y_train=y_explicit_train_target,
#         X_pred=X_explicit_train,
#         model_label="Explicit_linear_T_train_eval",
#     )
#
#     met_anchor_train = calc_metrics(
#         y_train,
#         Cp_pred_anchor_train,
#         "train",
#         "Anchor_baseline",
#     )
#     met_anchor_test = calc_metrics(
#         y_test,
#         Cp_pred_anchor_test,
#         "test",
#         "Anchor_baseline",
#     )
#
#     met_explicit_train = calc_metrics(
#         y_train,
#         Cp_pred_explicit_train,
#         "train",
#         "Explicit_linear_T",
#     )
#     met_explicit_test = calc_metrics(
#         y_test,
#         Cp_pred_explicit_test,
#         "test",
#         "Explicit_linear_T",
#     )
#
#     for met in [met_anchor_train, met_anchor_test, met_explicit_train, met_explicit_test]:
#         met["fold"] = fold
#         fold_metrics.append(met)
#
#     print(
#         "Anchor_baseline test: "
#         f"R2={met_anchor_test['R2']:.6f}, "
#         f"RMSE={met_anchor_test['RMSE']:.6f}, "
#         f"MAE={met_anchor_test['MAE']:.6f}, "
#         f"ARD={met_anchor_test['ARD_percent']:.6f}%"
#     )
#
#     print(
#         "Explicit_linear_T test: "
#         f"R2={met_explicit_test['R2']:.6f}, "
#         f"RMSE={met_explicit_test['RMSE']:.6f}, "
#         f"MAE={met_explicit_test['MAE']:.6f}, "
#         f"ARD={met_explicit_test['ARD_percent']:.6f}%"
#     )
#
#     # -----------------------------------------------------
#     # 11.5 保存逐点预测结果
#     # -----------------------------------------------------
#     fold_pred_df = pd.DataFrame({
#         "fold": fold,
#         "material_index": material_ids[test_mask],
#         "original_row_index_in_Sheet1": original_row_indices[test_mask],
#         "T_K": temperatures[test_mask],
#         "anchor_T_ref1": anchor_T_rows[test_mask],
#         "anchor_Cp_ref1": anchor_Cp_rows[test_mask],
#         "Cp_exp": y[test_mask],
#         "Cp_pred_anchor_baseline": Cp_pred_anchor_test,
#         "Cp_pred_explicit_linear_T": Cp_pred_explicit_test,
#         "anchor_baseline_error": Cp_pred_anchor_test - y[test_mask],
#         "explicit_linear_T_error": Cp_pred_explicit_test - y[test_mask],
#         "anchor_baseline_abs_error": np.abs(Cp_pred_anchor_test - y[test_mask]),
#         "explicit_linear_T_abs_error": np.abs(Cp_pred_explicit_test - y[test_mask]),
#         "anchor_baseline_relative_error_percent": np.where(
#             np.abs(y[test_mask]) > 1e-12,
#             np.abs((Cp_pred_anchor_test - y[test_mask]) / y[test_mask]) * 100,
#             np.nan,
#         ),
#         "explicit_linear_T_relative_error_percent": np.where(
#             np.abs(y[test_mask]) > 1e-12,
#             np.abs((Cp_pred_explicit_test - y[test_mask]) / y[test_mask]) * 100,
#             np.nan,
#         ),
#         "delta_T": temperatures[test_mask] - anchor_T_rows[test_mask],
#     })
#
#     prediction_records.append(fold_pred_df)
#
#     # -----------------------------------------------------
#     # 11.6 保存每折参数
#     # -----------------------------------------------------
#     anchor_coef = anchor_model_info["coef_original"]
#
#     for group_name, coef_value in zip(used_group_cols, anchor_coef):
#         anchor_param_records.append({
#             "fold": fold,
#             "group_name": group_name,
#             "anchor_slope_Ak": coef_value,
#             "abs_anchor_slope_Ak": abs(coef_value),
#         })
#
#     explicit_coef = explicit_model_info["coef_original"]
#
#     n_groups = len(used_group_cols)
#
#     explicit_A_params = explicit_coef[:n_groups]
#     explicit_B_params = explicit_coef[n_groups:2 * n_groups]
#
#     for group_name, A_value, B_value in zip(used_group_cols, explicit_A_params, explicit_B_params):
#         explicit_param_records.append({
#             "fold": fold,
#             "group_name": group_name,
#             "explicit_Ak": A_value,
#             "explicit_Bk": B_value,
#             "abs_explicit_Ak": abs(A_value),
#             "abs_explicit_Bk": abs(B_value),
#         })
#
#     fold_info_records.append({
#         "fold": fold,
#         "n_train_materials": len(train_materials),
#         "n_test_materials": len(test_materials),
#         "n_train_points": int(train_mask.sum()),
#         "n_test_points": int(test_mask.sum()),
#         "anchor_n_features": anchor_model_info["n_features"],
#         "explicit_n_features": explicit_model_info["n_features"],
#         "common_regressor": common_regressor_name,
#         "common_ridge_alpha": common_ridge_alpha,
#         "common_fit_intercept": common_fit_intercept,
#         "common_with_mean": common_with_mean,
#     })
#
#
# # =========================================================
# # 12. 汇总评价
# # =========================================================
# df_fold_metrics = pd.DataFrame(fold_metrics)
#
# # 调整列顺序
# metric_col_order = [
#     "fold",
#     "model",
#     "dataset",
#     "n_points",
#     "R2",
#     "MSE",
#     "RMSE",
#     "MAE",
#     "ARD_percent",
#     "max_abs_error",
#     "max_relative_error_percent",
#     "relative_error_le_1_percent_ratio",
#     "relative_error_le_5_percent_ratio",
#     "relative_error_le_10_percent_ratio",
#     "relative_error_le_1_percent_count",
#     "relative_error_le_5_percent_count",
#     "relative_error_le_10_percent_count",
# ]
#
# df_fold_metrics = df_fold_metrics[metric_col_order]
#
# summary_anchor = summarize_fold_metrics(df_fold_metrics, "Anchor_baseline")
# summary_explicit = summarize_fold_metrics(df_fold_metrics, "Explicit_linear_T")
#
# df_summary = pd.concat(
#     [summary_anchor, summary_explicit],
#     ignore_index=True,
# )
#
# df_ttest = paired_t_test_fold_metrics(
#     df_fold_metrics,
#     "Anchor_baseline",
#     "Explicit_linear_T",
# )
#
# # OOF 全体指标
# df_oof_metrics = pd.DataFrame([
#     calc_metrics(
#         y,
#         oof_pred_anchor,
#         "oof_all",
#         "Anchor_baseline",
#     ),
#     calc_metrics(
#         y,
#         oof_pred_explicit,
#         "oof_all",
#         "Explicit_linear_T",
#     ),
# ])
#
# print("\n========== 5-Fold Test Summary ==========")
# print(df_summary.to_string(index=False))
#
# print("\n========== OOF Metrics ==========")
# print(df_oof_metrics.to_string(index=False))
#
# print("\n========== Paired t-test on Fold Test Metrics ==========")
# print(df_ttest.to_string(index=False))
#
#
# # =========================================================
# # 13. 整理输出表
# # =========================================================
# df_prediction = pd.concat(prediction_records, ignore_index=True)
#
# extra_cols = [
#     "original_material_index",
#     "compound_name",
#     "cas",
#     "formula",
#     "SMILES",
#     "smiles",
#     "pubchem_cid",
#     "material_key",
#     "phase",
#     "boiling_T_K",
#     "critical_T_K",
# ]
#
# for col in extra_cols:
#     if col in df_data.columns:
#         values = []
#         for row_idx in df_prediction["original_row_index_in_Sheet1"].values:
#             values.append(df_data.iloc[int(row_idx)][col])
#         df_prediction[col] = values
#
# df_anchor_params = pd.DataFrame(anchor_param_records)
# df_explicit_params = pd.DataFrame(explicit_param_records)
#
# group_occurrence_all = (df_groups_used != 0).sum(axis=0)
# group_total_count_all = df_groups_used.sum(axis=0)
#
# df_used_groups = pd.DataFrame({
#     "used_group": used_group_cols,
#     "occurrence_all_materials": group_occurrence_all[used_group_cols].values,
#     "total_count_all": group_total_count_all[used_group_cols].values,
# })
#
# df_removed_zero_groups = pd.DataFrame({
#     "removed_all_zero_group": removed_zero_group_cols,
# })
#
# df_fold_info = pd.DataFrame(fold_info_records)
#
# df_run_info = pd.DataFrame([
#     {"item": "file_path", "value": str(file_path)},
#     {"item": "groups_sheet", "value": groups_sheet},
#     {"item": "data_sheet", "value": data_sheet},
#     {"item": "anchor_sheet", "value": anchor_sheet},
#     {"item": "n_points_per_material", "value": n_points_per_material},
#     {"item": "n_outer_folds", "value": n_outer_folds},
#     {"item": "random_state", "value": random_state},
#     {"item": "n_materials", "value": n_materials_groups},
#     {"item": "n_samples_after_filtering", "value": len(y)},
#     {"item": "n_group_features", "value": len(used_group_cols)},
#     {
#         "item": "anchor_baseline_formula",
#         "value": "Cp = Cp_anchor + (T - T_anchor) * sum(Nk * Ak)",
#     },
#     {
#         "item": "explicit_linear_T_formula",
#         "value": "Cp = sum(Nk * Ak) + sum(Nk * Bk * T)",
#     },
#     {
#         "item": "explicit_global_intercept_b0",
#         "value": "not_used",
#     },
#     {
#         "item": "common_regressor",
#         "value": common_regressor_name,
#     },
#     {
#         "item": "common_ridge_alpha",
#         "value": common_ridge_alpha,
#     },
#     {
#         "item": "common_fit_intercept",
#         "value": common_fit_intercept,
#     },
#     {
#         "item": "common_with_mean",
#         "value": common_with_mean,
#     },
# ])
#
#
# # =========================================================
# # 14. 保存 Excel
# # =========================================================
# with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
#     df_prediction.to_excel(
#         writer,
#         sheet_name="OOF_Prediction",
#         index=False,
#     )
#
#     df_fold_metrics.to_excel(
#         writer,
#         sheet_name="Fold_Metrics",
#         index=False,
#     )
#
#     df_summary.to_excel(
#         writer,
#         sheet_name="Summary_Test_MeanStd",
#         index=False,
#     )
#
#     df_oof_metrics.to_excel(
#         writer,
#         sheet_name="OOF_Metrics",
#         index=False,
#     )
#
#     df_ttest.to_excel(
#         writer,
#         sheet_name="Paired_T_Test",
#         index=False,
#     )
#
#     df_anchor_params.to_excel(
#         writer,
#         sheet_name="Anchor_Params_By_Fold",
#         index=False,
#     )
#
#     df_explicit_params.to_excel(
#         writer,
#         sheet_name="Explicit_Params_By_Fold",
#         index=False,
#     )
#
#     df_fold_info.to_excel(
#         writer,
#         sheet_name="Fold_Info",
#         index=False,
#     )
#
#     df_used_groups.to_excel(
#         writer,
#         sheet_name="Used_Groups",
#         index=False,
#     )
#
#     df_removed_zero_groups.to_excel(
#         writer,
#         sheet_name="Removed_Zero_Groups",
#         index=False,
#     )
#
#     df_run_info.to_excel(
#         writer,
#         sheet_name="Run_Info",
#         index=False,
#     )
#
#     format_excel(writer)
#
# print("\n保存完成:", output_file)
#
# print("\n1%, 5%, 10% 测试集覆盖率可在 Summary_Test_MeanStd 或 OOF_Metrics 中查看。")


import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.model_selection import KFold
from scipy.stats import ttest_rel

import warnings
warnings.filterwarnings("ignore")

pd.set_option("display.float_format", "{:.10f}".format)
np.set_printoptions(suppress=True, precision=10)


# =========================================================
# 1. 文件路径与 sheet 设置
# =========================================================
file_path = Path("Cp_dataset_selected_by_two_k_with_interpolation.xlsx")

groups_sheet = "groups_selected"
data_sheet = "Sheet1_selected"
anchor_sheet = "Interpolated_k1_k2"

output_file = Path("Cp_5fold_anchor_vs_explicit_linear_T_same_fixed_Ridge.xlsx")


# =========================================================
# 2. 基本设置
# =========================================================
n_points_per_material = 8

temp_col = "T_K"
target_col = "property_value"

# 锚点：温度与该温度下的热容
anchor_temp_col = "k1_times_boiling_T_K"
anchor_value_col = "property_interp_at_k1Tb"

random_state = 42
n_outer_folds = 5

# groups_selected 中基团列范围
# 如果你的 groups_selected 因插入 original_material_index 后基团从第4列开始，
# 可以改成 group_start_idx = 3, group_end_idx = 222
group_start_idx = 2
group_end_idx = 221

# =========================================================
# 统一回归参数
# 两个基线完全相同
# =========================================================
common_ridge_alpha = 1.0
common_fit_intercept = False
common_with_mean = False

common_regressor_name = (
    f"StandardScaler(with_mean={common_with_mean}) + "
    f"Ridge(alpha={common_ridge_alpha}, fit_intercept={common_fit_intercept})"
)


# =========================================================
# 3. 工具函数
# =========================================================
def safe_relative_error_percent(y_true, y_pred):
    """
    relative_error = abs((y_pred - y_true) / y_true) * 100

    对 abs(y_true) <= 1e-12 的点，relative_error 记为 NaN。
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    rel_err = np.full_like(y_true, np.nan, dtype=float)
    valid = np.isfinite(y_true) & np.isfinite(y_pred) & (np.abs(y_true) > 1e-12)

    rel_err[valid] = np.abs((y_pred[valid] - y_true[valid]) / y_true[valid]) * 100.0

    return rel_err


def count_error_thresholds(y_true, y_pred):
    """
    统计相对误差 <1%、<5%、<10% 的数据点数量。
    NaN 自动忽略。

    注意：
    这里使用严格小于 <，不是 <=。
    """
    rel_err = safe_relative_error_percent(y_true, y_pred)

    return {
        "count_rel_err_lt_1pct": float(np.nansum(rel_err < 1.0)),
        "count_rel_err_lt_5pct": float(np.nansum(rel_err < 5.0)),
        "count_rel_err_lt_10pct": float(np.nansum(rel_err < 10.0)),
        "n_valid_for_relative_error": int(np.sum(np.isfinite(rel_err))),
    }


def calc_metrics(y_true, y_pred, dataset_name, model_name):
    """
    保留原代码评价指标，同时使用统一相对误差定义：
        abs((y_pred - y_true) / y_true) * 100

    abs(y_true) <= 1e-12 的点 relative_error 记为 NaN。
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = np.isfinite(y_true) & np.isfinite(y_pred)

    y_true = y_true[mask]
    y_pred = y_pred[mask]

    if len(y_true) == 0:
        return {
            "model": model_name,
            "dataset": dataset_name,
            "n_points": 0,
            "R2": np.nan,
            "MSE": np.nan,
            "RMSE": np.nan,
            "MAE": np.nan,
            "ARD_percent": np.nan,
            "max_abs_error": np.nan,
            "max_relative_error_percent": np.nan,
            "relative_error_lt_1_percent_ratio": np.nan,
            "relative_error_lt_5_percent_ratio": np.nan,
            "relative_error_lt_10_percent_ratio": np.nan,
            "relative_error_lt_1_percent_count": 0,
            "relative_error_lt_5_percent_count": 0,
            "relative_error_lt_10_percent_count": 0,
        }

    error = y_pred - y_true
    abs_error = np.abs(error)

    rel_err = safe_relative_error_percent(y_true, y_pred)

    if np.any(np.isfinite(rel_err)):
        ard = np.nanmean(rel_err)
        max_rel = np.nanmax(rel_err)

        count_1 = float(np.nansum(rel_err < 1.0))
        count_5 = float(np.nansum(rel_err < 5.0))
        count_10 = float(np.nansum(rel_err < 10.0))

        n_valid_rel = int(np.sum(np.isfinite(rel_err)))

        ratio_1 = count_1 / n_valid_rel * 100.0
        ratio_5 = count_5 / n_valid_rel * 100.0
        ratio_10 = count_10 / n_valid_rel * 100.0
    else:
        ard = np.nan
        max_rel = np.nan

        count_1 = 0.0
        count_5 = 0.0
        count_10 = 0.0

        ratio_1 = np.nan
        ratio_5 = np.nan
        ratio_10 = np.nan

    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_true, y_pred)

    try:
        r2 = r2_score(y_true, y_pred)
    except Exception:
        r2 = np.nan

    return {
        "model": model_name,
        "dataset": dataset_name,
        "n_points": len(y_true),
        "R2": r2,
        "MSE": mse,
        "RMSE": rmse,
        "MAE": mae,
        "ARD_percent": ard,
        "max_abs_error": np.max(abs_error),
        "max_relative_error_percent": max_rel,
        "relative_error_lt_1_percent_ratio": ratio_1,
        "relative_error_lt_5_percent_ratio": ratio_5,
        "relative_error_lt_10_percent_ratio": ratio_10,
        "relative_error_lt_1_percent_count": count_1,
        "relative_error_lt_5_percent_count": count_5,
        "relative_error_lt_10_percent_count": count_10,
    }


def fit_fixed_ridge_same_params(X_train, y_train, X_pred, model_label):
    """
    统一回归器：
        StandardScaler(with_mean=False)
        Ridge(alpha=common_ridge_alpha, fit_intercept=False)

    说明：
    1. 两个模型使用完全相同的 alpha。
    2. 两个模型使用完全相同的 fit_intercept 设置。
    3. 两个模型使用完全相同的标准化方式。
    4. 显式一阶 T 模型不额外添加常数列，因此没有全局截距 b0。
    """
    X_train = np.asarray(X_train, dtype=float)
    y_train = np.asarray(y_train, dtype=float)
    X_pred = np.asarray(X_pred, dtype=float)

    valid_train = (
        np.isfinite(X_train).all(axis=1)
        & np.isfinite(y_train)
    )

    X_train_fit = X_train[valid_train]
    y_train_fit = y_train[valid_train]

    if len(y_train_fit) == 0:
        raise ValueError(f"{model_label}: 没有有效训练样本。")

    scaler = StandardScaler(with_mean=common_with_mean)

    X_train_scaled = scaler.fit_transform(X_train_fit)
    X_pred_scaled = scaler.transform(X_pred)

    model = Ridge(
        alpha=common_ridge_alpha,
        fit_intercept=common_fit_intercept,
    )

    model.fit(X_train_scaled, y_train_fit)

    y_pred = model.predict(X_pred_scaled)

    # 还原到原始特征尺度
    coef_scaled = model.coef_.astype(float)

    x_scale = scaler.scale_.astype(float)
    x_scale_safe = np.where(x_scale == 0, 1.0, x_scale)

    coef_original = coef_scaled / x_scale_safe

    model_info = {
        "model_label": model_label,
        "regressor": common_regressor_name,
        "common_ridge_alpha": common_ridge_alpha,
        "common_fit_intercept": common_fit_intercept,
        "common_with_mean": common_with_mean,
        "n_train_samples": len(y_train_fit),
        "n_features": X_train.shape[1],
        "model": model,
        "scaler": scaler,
        "coef_scaled": coef_scaled,
        "coef_original": coef_original,
    }

    return y_pred, model_info


def predict_fixed_ridge_from_info(X_pred, model_info):
    """
    使用已经训练好的 Ridge + scaler 对新特征进行预测。
    """
    X_pred = np.asarray(X_pred, dtype=float)

    scaler = model_info["scaler"]
    model = model_info["model"]

    X_pred_scaled = scaler.transform(X_pred)
    y_pred = model.predict(X_pred_scaled)

    return y_pred


def summarize_fold_metrics(df_metrics, model_name):
    rows = []

    sub = df_metrics[
        (df_metrics["model"] == model_name)
        & (df_metrics["dataset"] == "test")
    ].copy()

    for metric in [
        "R2",
        "MSE",
        "RMSE",
        "MAE",
        "ARD_percent",
        "relative_error_lt_1_percent_ratio",
        "relative_error_lt_5_percent_ratio",
        "relative_error_lt_10_percent_ratio",
    ]:
        vals = sub[metric].dropna().values

        if len(vals) == 0:
            mean_val = np.nan
            std_val = np.nan
            mean_std = "NaN"
        elif len(vals) == 1:
            mean_val = float(np.mean(vals))
            std_val = np.nan
            mean_std = f"{mean_val:.10f} ± NaN"
        else:
            mean_val = float(np.mean(vals))
            std_val = float(np.std(vals, ddof=1))
            mean_std = f"{mean_val:.10f} ± {std_val:.10f}"

        rows.append({
            "model": model_name,
            "metric": metric,
            "mean": mean_val,
            "std": std_val,
            "mean±std": mean_std,
        })

    return pd.DataFrame(rows)


def paired_t_test_fold_metrics(df_metrics, model_a, model_b):
    rows = []

    sub_a = df_metrics[
        (df_metrics["model"] == model_a)
        & (df_metrics["dataset"] == "test")
    ].sort_values("fold")

    sub_b = df_metrics[
        (df_metrics["model"] == model_b)
        & (df_metrics["dataset"] == "test")
    ].sort_values("fold")

    for metric in [
        "R2",
        "MSE",
        "RMSE",
        "MAE",
        "ARD_percent",
        "relative_error_lt_1_percent_ratio",
        "relative_error_lt_5_percent_ratio",
        "relative_error_lt_10_percent_ratio",
    ]:
        vals_a = sub_a[metric].values.astype(float)
        vals_b = sub_b[metric].values.astype(float)

        valid = np.isfinite(vals_a) & np.isfinite(vals_b)

        vals_a = vals_a[valid]
        vals_b = vals_b[valid]

        if len(vals_a) > 1:
            t_stat, p_value = ttest_rel(vals_a, vals_b)

            if metric in [
                "R2",
                "relative_error_lt_1_percent_ratio",
                "relative_error_lt_5_percent_ratio",
                "relative_error_lt_10_percent_ratio",
            ]:
                better = model_a if np.mean(vals_a) > np.mean(vals_b) else model_b
            else:
                better = model_a if np.mean(vals_a) < np.mean(vals_b) else model_b

            rows.append({
                "metric": metric,
                "model_a": model_a,
                "model_b": model_b,
                "mean_model_a": np.mean(vals_a),
                "mean_model_b": np.mean(vals_b),
                "t_stat": t_stat,
                "p_value": p_value,
                "significant_p_lt_0.05": p_value < 0.05,
                "better_model_by_mean": better,
            })

        else:
            rows.append({
                "metric": metric,
                "model_a": model_a,
                "model_b": model_b,
                "mean_model_a": np.nan,
                "mean_model_b": np.nan,
                "t_stat": np.nan,
                "p_value": np.nan,
                "significant_p_lt_0.05": False,
                "better_model_by_mean": "insufficient_valid_folds",
            })

    return pd.DataFrame(rows)


def make_long_prediction_df(
    fold,
    dataset_name,
    model_name,
    sample_indices,
    y_true,
    y_pred,
):
    """
    用于保存每个 fold 的测试集预测结果和完整数据集预测结果。
    """
    sample_indices = np.asarray(sample_indices, dtype=int)
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    rel_err = safe_relative_error_percent(y_true, y_pred)

    df = pd.DataFrame({
        "fold": fold,
        "dataset": dataset_name,
        "model": model_name,
        "sample_index": sample_indices,
        "material_index": material_ids[sample_indices],
        "original_row_index_in_Sheet1": original_row_indices[sample_indices],
        "T_K": temperatures[sample_indices],
        "anchor_T_ref1": anchor_T_rows[sample_indices],
        "anchor_Cp_ref1": anchor_Cp_rows[sample_indices],
        "Cp_exp": y_true,
        "Cp_pred": y_pred,
        "error": y_pred - y_true,
        "abs_error": np.abs(y_pred - y_true),
        "relative_error_percent": rel_err,
        "delta_T": temperatures[sample_indices] - anchor_T_rows[sample_indices],
    })

    return df


def format_excel(writer, number_format="0.0000000000"):
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

            ws.column_dimensions[col_letter].width = min(max_length + 2, 60)


# =========================================================
# 4. 读取数据
# =========================================================
df_groups_raw = pd.read_excel(file_path, sheet_name=groups_sheet)
df_data = pd.read_excel(file_path, sheet_name=data_sheet)
df_anchor = pd.read_excel(file_path, sheet_name=anchor_sheet)

print("groups 表行数:", len(df_groups_raw))
print("Sheet1_selected 行数:", len(df_data))
print("anchor sheet 行数:", len(df_anchor))


# =========================================================
# 5. 读取并对齐锚点
# =========================================================
for col in [anchor_temp_col, anchor_value_col]:
    if col not in df_anchor.columns:
        raise ValueError(f"{anchor_sheet} 中没有找到列: {col}")

df_anchor[anchor_temp_col] = pd.to_numeric(df_anchor[anchor_temp_col], errors="coerce")
df_anchor[anchor_value_col] = pd.to_numeric(df_anchor[anchor_value_col], errors="coerce")

if "original_material_index" in df_groups_raw.columns and "original_material_index" in df_anchor.columns:
    anchor_temp_map = (
        df_anchor[["original_material_index", anchor_temp_col]]
        .drop_duplicates(subset=["original_material_index"])
        .set_index("original_material_index")[anchor_temp_col]
    )

    anchor_value_map = (
        df_anchor[["original_material_index", anchor_value_col]]
        .drop_duplicates(subset=["original_material_index"])
        .set_index("original_material_index")[anchor_value_col]
    )

    df_groups_raw["anchor_T_ref1"] = df_groups_raw["original_material_index"].map(anchor_temp_map)
    df_groups_raw["anchor_Cp_ref1"] = df_groups_raw["original_material_index"].map(anchor_value_map)

    print("使用 original_material_index 对齐锚点。")

else:
    if len(df_groups_raw) != len(df_anchor):
        raise ValueError(
            "无法使用 original_material_index 对齐锚点，"
            "且 groups 表与 anchor sheet 行数不一致。"
        )

    df_groups_raw["anchor_T_ref1"] = df_anchor[anchor_temp_col].values
    df_groups_raw["anchor_Cp_ref1"] = df_anchor[anchor_value_col].values

    print("没有 original_material_index，按行顺序对齐锚点。")


# =========================================================
# 6. 删除无效锚点对应物质
# =========================================================
anchor_T_raw = pd.to_numeric(df_groups_raw["anchor_T_ref1"], errors="coerce").values.astype(float)
anchor_Cp_raw = pd.to_numeric(df_groups_raw["anchor_Cp_ref1"], errors="coerce").values.astype(float)

valid_anchor_mask = np.isfinite(anchor_T_raw) & np.isfinite(anchor_Cp_raw)

invalid_anchor_count = int((~valid_anchor_mask).sum())
print("无效锚点物质数:", invalid_anchor_count)

if invalid_anchor_count > 0:
    keep_data_indices = []

    for material_idx, keep in enumerate(valid_anchor_mask):
        if keep:
            start = material_idx * n_points_per_material
            end = start + n_points_per_material
            keep_data_indices.extend(range(start, end))

    df_groups_raw = df_groups_raw.loc[valid_anchor_mask].reset_index(drop=True)
    df_data = df_data.iloc[keep_data_indices].reset_index(drop=True)

print("过滤后 groups 表行数:", len(df_groups_raw))
print("过滤后 Sheet1_selected 行数:", len(df_data))


# =========================================================
# 7. 读取基团列，并删除全零列
# =========================================================
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
    "anchor_T",
    "anchor_Cp",
    "anchor_T_ref1",
    "anchor_Cp_ref1",
}

group_cols_raw = [c for c in group_cols_raw if c not in exclude_cols]

df_groups = df_groups_raw[group_cols_raw].copy()
df_groups = df_groups.apply(pd.to_numeric, errors="coerce").fillna(0.0)

print("原始基团列数量:", len(group_cols_raw))

nonzero_mask = df_groups.abs().sum(axis=0) != 0

used_group_cols = df_groups.columns[nonzero_mask].tolist()
removed_zero_group_cols = df_groups.columns[~nonzero_mask].tolist()

df_groups_used = df_groups[used_group_cols].copy()
X_groups = df_groups_used.values.astype(float)

print("删除全零列后基团列数量:", len(used_group_cols))
print("被删除全零基团列数量:", len(removed_zero_group_cols))


# =========================================================
# 8. 检查 Sheet1_selected
# =========================================================
if temp_col not in df_data.columns:
    raise ValueError(f"{data_sheet} 中没有找到温度列: {temp_col}")

if target_col not in df_data.columns:
    raise ValueError(f"{data_sheet} 中没有找到热容列: {target_col}")

if len(df_data) % n_points_per_material != 0:
    raise ValueError(
        f"{data_sheet} 行数 {len(df_data)} 不能被 {n_points_per_material} 整除。"
        "请检查是否每个物质都是 8 行。"
    )

n_materials_data = len(df_data) // n_points_per_material
n_materials_groups = len(df_groups_used)

print("Sheet1_selected 中物质数量:", n_materials_data)
print("groups 中物质数量:", n_materials_groups)

if n_materials_data != n_materials_groups:
    raise ValueError(
        "Sheet1_selected 中物质数量和 groups 表行数不一致。\n"
        f"Sheet1_selected 物质数 = {n_materials_data}, groups 行数 = {n_materials_groups}"
    )


# =========================================================
# 9. 展开温度点数据
# =========================================================
all_targets = []
material_ids = []
temperatures = []
anchor_T_rows = []
anchor_Cp_rows = []
original_row_indices = []

anchor_T_per_material = pd.to_numeric(
    df_groups_raw["anchor_T_ref1"],
    errors="coerce",
).values.astype(float)

anchor_Cp_per_material = pd.to_numeric(
    df_groups_raw["anchor_Cp_ref1"],
    errors="coerce",
).values.astype(float)

for material_idx in range(n_materials_groups):
    start = material_idx * n_points_per_material
    end = start + n_points_per_material

    sub_data = df_data.iloc[start:end].copy()

    T_values = pd.to_numeric(sub_data[temp_col], errors="coerce").values.astype(float)
    Cp_values = pd.to_numeric(sub_data[target_col], errors="coerce").values.astype(float)

    anchor_T = anchor_T_per_material[material_idx]
    anchor_Cp = anchor_Cp_per_material[material_idx]

    for local_i, (T, Cp) in enumerate(zip(T_values, Cp_values)):
        if not np.isfinite(T) or not np.isfinite(Cp):
            continue

        if not np.isfinite(anchor_T) or not np.isfinite(anchor_Cp):
            continue

        all_targets.append(Cp)
        material_ids.append(material_idx)
        temperatures.append(T)
        anchor_T_rows.append(anchor_T)
        anchor_Cp_rows.append(anchor_Cp)
        original_row_indices.append(start + local_i)

y = np.array(all_targets, dtype=float)
material_ids = np.array(material_ids, dtype=int)
temperatures = np.array(temperatures, dtype=float)
anchor_T_rows = np.array(anchor_T_rows, dtype=float)
anchor_Cp_rows = np.array(anchor_Cp_rows, dtype=float)
original_row_indices = np.array(original_row_indices, dtype=int)

print("展开后样本点数:", len(y))


# =========================================================
# 10. 构造两个基线的特征矩阵
# =========================================================
all_sample_indices = np.arange(len(y))


def build_anchor_baseline_X(sample_indices):
    """
    锚点基线：
        Cp = Cp_anchor + (T - T_anchor) * sum(Nk * Ak)

    训练目标：
        Cp - Cp_anchor

    特征：
        Nk * (T - T_anchor)
    """
    sample_indices = np.asarray(sample_indices, dtype=int)

    mat_ids = material_ids[sample_indices]
    T = temperatures[sample_indices]
    anchor_T = anchor_T_rows[sample_indices]

    delta_T = T - anchor_T
    group_feat = X_groups[mat_ids]

    X_base = group_feat * delta_T.reshape(-1, 1)

    return X_base


def build_explicit_linear_T_X(sample_indices):
    """
    显式一阶 T 模型：
        Cp = sum(Nk * Ak) + sum(Nk * Bk * T)

    不加全局截距 b0。

    特征：
        [Nk, Nk*T]
    """
    sample_indices = np.asarray(sample_indices, dtype=int)

    mat_ids = material_ids[sample_indices]
    T = temperatures[sample_indices]

    group_feat = X_groups[mat_ids]

    feature_A = group_feat
    feature_B = group_feat * T.reshape(-1, 1)

    X_explicit = np.hstack([
        feature_A,
        feature_B,
    ])

    return X_explicit


X_anchor_all = build_anchor_baseline_X(all_sample_indices)
X_explicit_all = build_explicit_linear_T_X(all_sample_indices)

print("锚点基线特征数:", X_anchor_all.shape[1])
print("显式一阶 T 模型特征数:", X_explicit_all.shape[1])


# =========================================================
# 11. 外层 5-fold by material
# =========================================================
unique_materials = np.unique(material_ids)

if len(unique_materials) < n_outer_folds:
    raise ValueError(
        f"物质数 {len(unique_materials)} 小于 n_outer_folds={n_outer_folds}，无法做 5-fold。"
    )

outer_kf = KFold(
    n_splits=n_outer_folds,
    shuffle=True,
    random_state=random_state,
)

# out-of-fold 预测
oof_pred_anchor = np.full_like(y, np.nan, dtype=float)
oof_pred_explicit = np.full_like(y, np.nan, dtype=float)

fold_metrics = []
prediction_records = []
fold_test_prediction_records_long = []
fold_all_data_prediction_records_long = []

anchor_param_records = []
explicit_param_records = []
fold_info_records = []
fold_all_data_count_records = []

for fold, (train_mat_idx, test_mat_idx) in enumerate(outer_kf.split(unique_materials), start=1):
    train_materials = unique_materials[train_mat_idx]
    test_materials = unique_materials[test_mat_idx]

    train_mask = np.isin(material_ids, train_materials)
    test_mask = np.isin(material_ids, test_materials)

    train_sample_indices = all_sample_indices[train_mask]
    test_sample_indices = all_sample_indices[test_mask]

    print(f"\n========== Fold {fold} ==========")
    print("训练物质数:", len(train_materials))
    print("测试物质数:", len(test_materials))
    print("训练样本点数:", int(train_mask.sum()))
    print("测试样本点数:", int(test_mask.sum()))

    # -----------------------------------------------------
    # 11.1 锚点基线
    # -----------------------------------------------------
    X_anchor_train = X_anchor_all[train_mask]
    X_anchor_test = X_anchor_all[test_mask]

    y_anchor_train_target = y[train_mask] - anchor_Cp_rows[train_mask]

    anchor_delta_test, anchor_model_info = fit_fixed_ridge_same_params(
        X_train=X_anchor_train,
        y_train=y_anchor_train_target,
        X_pred=X_anchor_test,
        model_label="Anchor_baseline",
    )

    Cp_pred_anchor_test = anchor_Cp_rows[test_mask] + anchor_delta_test

    # -----------------------------------------------------
    # 11.2 显式一阶 T 模型
    # -----------------------------------------------------
    X_explicit_train = X_explicit_all[train_mask]
    X_explicit_test = X_explicit_all[test_mask]

    y_explicit_train_target = y[train_mask]

    Cp_pred_explicit_test, explicit_model_info = fit_fixed_ridge_same_params(
        X_train=X_explicit_train,
        y_train=y_explicit_train_target,
        X_pred=X_explicit_test,
        model_label="Explicit_linear_T",
    )

    # -----------------------------------------------------
    # 11.3 保存 out-of-fold 预测
    # -----------------------------------------------------
    oof_pred_anchor[test_mask] = Cp_pred_anchor_test
    oof_pred_explicit[test_mask] = Cp_pred_explicit_test

    # -----------------------------------------------------
    # 11.4 每折评价
    # -----------------------------------------------------
    y_train = y[train_mask]
    y_test = y[test_mask]

    # 为了记录 train 指标，也生成 train prediction
    # 这里使用同一折已经训练好的模型，不再重复训练。
    anchor_delta_train = predict_fixed_ridge_from_info(
        X_anchor_train,
        anchor_model_info,
    )
    Cp_pred_anchor_train = anchor_Cp_rows[train_mask] + anchor_delta_train

    Cp_pred_explicit_train = predict_fixed_ridge_from_info(
        X_explicit_train,
        explicit_model_info,
    )

    met_anchor_train = calc_metrics(
        y_train,
        Cp_pred_anchor_train,
        "train",
        "Anchor_baseline",
    )
    met_anchor_test = calc_metrics(
        y_test,
        Cp_pred_anchor_test,
        "test",
        "Anchor_baseline",
    )

    met_explicit_train = calc_metrics(
        y_train,
        Cp_pred_explicit_train,
        "train",
        "Explicit_linear_T",
    )
    met_explicit_test = calc_metrics(
        y_test,
        Cp_pred_explicit_test,
        "test",
        "Explicit_linear_T",
    )

    for met in [met_anchor_train, met_anchor_test, met_explicit_train, met_explicit_test]:
        met["fold"] = fold
        fold_metrics.append(met)

    print(
        "Anchor_baseline test: "
        f"R2={met_anchor_test['R2']:.6f}, "
        f"MSE={met_anchor_test['MSE']:.6f}, "
        f"RMSE={met_anchor_test['RMSE']:.6f}, "
        f"MAE={met_anchor_test['MAE']:.6f}, "
        f"ARD={met_anchor_test['ARD_percent']:.6f}%"
    )

    print(
        "Explicit_linear_T test: "
        f"R2={met_explicit_test['R2']:.6f}, "
        f"MSE={met_explicit_test['MSE']:.6f}, "
        f"RMSE={met_explicit_test['RMSE']:.6f}, "
        f"MAE={met_explicit_test['MAE']:.6f}, "
        f"ARD={met_explicit_test['ARD_percent']:.6f}%"
    )

    # -----------------------------------------------------
    # 11.5 新增：每个 fold 训练出的模型预测完整数据集
    # -----------------------------------------------------
    anchor_delta_all = predict_fixed_ridge_from_info(
        X_anchor_all,
        anchor_model_info,
    )
    Cp_pred_anchor_all = anchor_Cp_rows + anchor_delta_all

    Cp_pred_explicit_all = predict_fixed_ridge_from_info(
        X_explicit_all,
        explicit_model_info,
    )

    anchor_all_counts = count_error_thresholds(y, Cp_pred_anchor_all)
    explicit_all_counts = count_error_thresholds(y, Cp_pred_explicit_all)

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "Anchor_baseline",
        **anchor_all_counts,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "Explicit_linear_T",
        **explicit_all_counts,
    })

    print("\nAnchor_baseline fold model predicts ALL data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "Anchor_baseline",
        **anchor_all_counts,
    }]).to_string(index=False))

    print("\nExplicit_linear_T fold model predicts ALL data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "Explicit_linear_T",
        **explicit_all_counts,
    }]).to_string(index=False))

    # -----------------------------------------------------
    # 11.6 保存逐点测试集预测结果：保留原始宽表
    # -----------------------------------------------------
    fold_pred_df = pd.DataFrame({
        "fold": fold,
        "material_index": material_ids[test_mask],
        "original_row_index_in_Sheet1": original_row_indices[test_mask],
        "T_K": temperatures[test_mask],
        "anchor_T_ref1": anchor_T_rows[test_mask],
        "anchor_Cp_ref1": anchor_Cp_rows[test_mask],
        "Cp_exp": y[test_mask],
        "Cp_pred_anchor_baseline": Cp_pred_anchor_test,
        "Cp_pred_explicit_linear_T": Cp_pred_explicit_test,
        "anchor_baseline_error": Cp_pred_anchor_test - y[test_mask],
        "explicit_linear_T_error": Cp_pred_explicit_test - y[test_mask],
        "anchor_baseline_abs_error": np.abs(Cp_pred_anchor_test - y[test_mask]),
        "explicit_linear_T_abs_error": np.abs(Cp_pred_explicit_test - y[test_mask]),
        "anchor_baseline_relative_error_percent": safe_relative_error_percent(
            y[test_mask],
            Cp_pred_anchor_test,
        ),
        "explicit_linear_T_relative_error_percent": safe_relative_error_percent(
            y[test_mask],
            Cp_pred_explicit_test,
        ),
        "delta_T": temperatures[test_mask] - anchor_T_rows[test_mask],
    })

    prediction_records.append(fold_pred_df)

    # -----------------------------------------------------
    # 11.7 新增：保存测试集预测结果，长表格式
    # -----------------------------------------------------
    fold_test_prediction_records_long.append(
        make_long_prediction_df(
            fold=fold,
            dataset_name="test",
            model_name="Anchor_baseline",
            sample_indices=test_sample_indices,
            y_true=y[test_mask],
            y_pred=Cp_pred_anchor_test,
        )
    )

    fold_test_prediction_records_long.append(
        make_long_prediction_df(
            fold=fold,
            dataset_name="test",
            model_name="Explicit_linear_T",
            sample_indices=test_sample_indices,
            y_true=y[test_mask],
            y_pred=Cp_pred_explicit_test,
        )
    )

    # -----------------------------------------------------
    # 11.8 新增：保存完整数据集预测结果，长表格式
    # -----------------------------------------------------
    fold_all_data_prediction_records_long.append(
        make_long_prediction_df(
            fold=fold,
            dataset_name="all_data",
            model_name="Anchor_baseline",
            sample_indices=all_sample_indices,
            y_true=y,
            y_pred=Cp_pred_anchor_all,
        )
    )

    fold_all_data_prediction_records_long.append(
        make_long_prediction_df(
            fold=fold,
            dataset_name="all_data",
            model_name="Explicit_linear_T",
            sample_indices=all_sample_indices,
            y_true=y,
            y_pred=Cp_pred_explicit_all,
        )
    )

    # -----------------------------------------------------
    # 11.9 保存每折参数
    # -----------------------------------------------------
    anchor_coef = anchor_model_info["coef_original"]

    for group_name, coef_value in zip(used_group_cols, anchor_coef):
        anchor_param_records.append({
            "fold": fold,
            "group_name": group_name,
            "anchor_slope_Ak": coef_value,
            "abs_anchor_slope_Ak": abs(coef_value),
        })

    explicit_coef = explicit_model_info["coef_original"]

    n_groups = len(used_group_cols)

    explicit_A_params = explicit_coef[:n_groups]
    explicit_B_params = explicit_coef[n_groups:2 * n_groups]

    for group_name, A_value, B_value in zip(used_group_cols, explicit_A_params, explicit_B_params):
        explicit_param_records.append({
            "fold": fold,
            "group_name": group_name,
            "explicit_Ak": A_value,
            "explicit_Bk": B_value,
            "abs_explicit_Ak": abs(A_value),
            "abs_explicit_Bk": abs(B_value),
        })

    fold_info_records.append({
        "fold": fold,
        "n_train_materials": len(train_materials),
        "n_test_materials": len(test_materials),
        "n_train_points": int(train_mask.sum()),
        "n_test_points": int(test_mask.sum()),
        "anchor_n_features": anchor_model_info["n_features"],
        "explicit_n_features": explicit_model_info["n_features"],
        "common_regressor": common_regressor_name,
        "common_ridge_alpha": common_ridge_alpha,
        "common_fit_intercept": common_fit_intercept,
        "common_with_mean": common_with_mean,
    })


# =========================================================
# 12. 汇总评价
# =========================================================
df_fold_metrics = pd.DataFrame(fold_metrics)

# 调整列顺序
metric_col_order = [
    "fold",
    "model",
    "dataset",
    "n_points",
    "R2",
    "MSE",
    "RMSE",
    "MAE",
    "ARD_percent",
    "max_abs_error",
    "max_relative_error_percent",
    "relative_error_lt_1_percent_ratio",
    "relative_error_lt_5_percent_ratio",
    "relative_error_lt_10_percent_ratio",
    "relative_error_lt_1_percent_count",
    "relative_error_lt_5_percent_count",
    "relative_error_lt_10_percent_count",
]

df_fold_metrics = df_fold_metrics[metric_col_order]

summary_anchor = summarize_fold_metrics(df_fold_metrics, "Anchor_baseline")
summary_explicit = summarize_fold_metrics(df_fold_metrics, "Explicit_linear_T")

df_summary = pd.concat(
    [summary_anchor, summary_explicit],
    ignore_index=True,
)

df_ttest = paired_t_test_fold_metrics(
    df_fold_metrics,
    "Anchor_baseline",
    "Explicit_linear_T",
)

# OOF 全体指标：保留原代码功能
df_oof_metrics = pd.DataFrame([
    calc_metrics(
        y,
        oof_pred_anchor,
        "oof_all",
        "Anchor_baseline",
    ),
    calc_metrics(
        y,
        oof_pred_explicit,
        "oof_all",
        "Explicit_linear_T",
    ),
])

print("\n========== 5-Fold Test Summary ==========")
print(df_summary.to_string(index=False))

print("\n========== OOF Metrics ==========")
print(df_oof_metrics.to_string(index=False))

print("\n========== Paired t-test on Fold Test Metrics ==========")
print(df_ttest.to_string(index=False))


# =========================================================
# 13. 新增：完整数据集预测偏差数量统计汇总
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
# 14. 整理输出表
# =========================================================
df_prediction = pd.concat(prediction_records, ignore_index=True)

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

for col in extra_cols:
    if col in df_data.columns:
        values = []
        for row_idx in df_prediction["original_row_index_in_Sheet1"].values:
            values.append(df_data.iloc[int(row_idx)][col])
        df_prediction[col] = values

df_fold_test_predictions = pd.concat(fold_test_prediction_records_long, ignore_index=True)
df_fold_all_data_predictions = pd.concat(fold_all_data_prediction_records_long, ignore_index=True)

# 给长表预测结果补充物质信息
for df_pred_long in [df_fold_test_predictions, df_fold_all_data_predictions]:
    for col in extra_cols:
        if col in df_data.columns:
            values = []
            for row_idx in df_pred_long["original_row_index_in_Sheet1"].values:
                values.append(df_data.iloc[int(row_idx)][col])
            df_pred_long[col] = values

df_anchor_params = pd.DataFrame(anchor_param_records)
df_explicit_params = pd.DataFrame(explicit_param_records)

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

df_fold_info = pd.DataFrame(fold_info_records)

df_run_info = pd.DataFrame([
    {"item": "file_path", "value": str(file_path)},
    {"item": "groups_sheet", "value": groups_sheet},
    {"item": "data_sheet", "value": data_sheet},
    {"item": "anchor_sheet", "value": anchor_sheet},
    {"item": "n_points_per_material", "value": n_points_per_material},
    {"item": "n_outer_folds", "value": n_outer_folds},
    {"item": "random_state", "value": random_state},
    {"item": "n_materials", "value": n_materials_groups},
    {"item": "n_samples_after_filtering", "value": len(y)},
    {"item": "n_group_features", "value": len(used_group_cols)},
    {
        "item": "anchor_baseline_formula",
        "value": "Cp = Cp_anchor + (T - T_anchor) * sum(Nk * Ak)",
    },
    {
        "item": "explicit_linear_T_formula",
        "value": "Cp = sum(Nk * Ak) + sum(Nk * Bk * T)",
    },
    {
        "item": "explicit_global_intercept_b0",
        "value": "not_used",
    },
    {
        "item": "common_regressor",
        "value": common_regressor_name,
    },
    {
        "item": "common_ridge_alpha",
        "value": common_ridge_alpha,
    },
    {
        "item": "common_fit_intercept",
        "value": common_fit_intercept,
    },
    {
        "item": "common_with_mean",
        "value": common_with_mean,
    },
    {
        "item": "relative_error_definition",
        "value": "abs((y_pred - y_true) / y_true) * 100; abs(y_true)<=1e-12 -> NaN",
    },
    {
        "item": "full_data_count_rule",
        "value": "Each fold model predicts the whole dataset; count rel_err <1%, <5%, <10%; then average counts over 5 folds.",
    },
])


# =========================================================
# 15. 模型结构汇总
# =========================================================
df_model_structure = pd.DataFrame([
    {
        "项目": "预测对象",
        "内容": "定压热容 Cp / property_value",
    },
    {
        "项目": "数据文件",
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
        "项目": "锚点温度列",
        "内容": anchor_temp_col,
    },
    {
        "项目": "锚点物性列",
        "内容": anchor_value_col,
    },
    {
        "项目": "交叉验证方式",
        "内容": f"{n_outer_folds}-fold KFold，按物质划分，shuffle=True，random_state={random_state}",
    },
    {
        "项目": "方法1",
        "内容": "Anchor_baseline：Cp = Cp_anchor + (T - T_anchor) * sum(Nk * Ak)",
    },
    {
        "项目": "方法1训练目标",
        "内容": "Cp - Cp_anchor",
    },
    {
        "项目": "方法1输入特征",
        "内容": f"Nk * (T - T_anchor)，特征数 {len(used_group_cols)}",
    },
    {
        "项目": "方法2",
        "内容": "Explicit_linear_T：Cp = sum(Nk * Ak) + sum(Nk * Bk * T)",
    },
    {
        "项目": "方法2训练目标",
        "内容": "Cp",
    },
    {
        "项目": "方法2输入特征",
        "内容": f"[Nk, Nk*T]，特征数 {2 * len(used_group_cols)}",
    },
    {
        "项目": "是否包含子模型",
        "内容": "不包含子模型；锚点来自 Interpolated_k1_k2 sheet 的插值结果",
    },
    {
        "项目": "子模型预测对象",
        "内容": "无",
    },
    {
        "项目": "子模型类型",
        "内容": "无",
    },
    {
        "项目": "子模型参数",
        "内容": "无",
    },
    {
        "项目": "子模型输入特征",
        "内容": "无",
    },
    {
        "项目": "slope 构造",
        "内容": "方法1中的斜率由 sum(Nk * Ak) 学习得到，对应锚点线性斜率；无外部 slope 子模型",
    },
    {
        "项目": "baseline 构造",
        "内容": "方法1为锚点基线；方法2为显式一阶 T 基线",
    },
    {
        "项目": "residual 构造",
        "内容": "无 residual 修正",
    },
    {
        "项目": "最终模型类型",
        "内容": "StandardScaler(with_mean=False) + Ridge",
    },
    {
        "项目": "最终模型参数",
        "内容": f"Ridge(alpha={common_ridge_alpha}, fit_intercept={common_fit_intercept})",
    },
    {
        "项目": "偏差数量统计口径",
        "内容": "每个 fold 模型预测完整数据集，统计相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 取平均",
    },
])


# =========================================================
# 16. 保存 Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    # 保留原有输出
    df_prediction.to_excel(
        writer,
        sheet_name="OOF_Prediction",
        index=False,
    )

    df_fold_metrics.to_excel(
        writer,
        sheet_name="Fold_Metrics",
        index=False,
    )

    df_summary.to_excel(
        writer,
        sheet_name="Summary_Test_MeanStd",
        index=False,
    )

    df_oof_metrics.to_excel(
        writer,
        sheet_name="OOF_Metrics",
        index=False,
    )

    df_ttest.to_excel(
        writer,
        sheet_name="Paired_T_Test",
        index=False,
    )

    df_anchor_params.to_excel(
        writer,
        sheet_name="Anchor_Params_By_Fold",
        index=False,
    )

    df_explicit_params.to_excel(
        writer,
        sheet_name="Explicit_Params_By_Fold",
        index=False,
    )

    df_fold_info.to_excel(
        writer,
        sheet_name="Fold_Info",
        index=False,
    )

    df_used_groups.to_excel(
        writer,
        sheet_name="Used_Groups",
        index=False,
    )

    df_removed_zero_groups.to_excel(
        writer,
        sheet_name="Removed_Zero_Groups",
        index=False,
    )

    df_run_info.to_excel(
        writer,
        sheet_name="Run_Info",
        index=False,
    )

    # 新增输出
    df_fold_test_predictions.to_excel(
        writer,
        sheet_name="fold_test_predictions",
        index=False,
    )

    df_fold_all_data_predictions.to_excel(
        writer,
        sheet_name="fold_all_data_predictions",
        index=False,
    )

    df_fold_all_data_count_summary.to_excel(
        writer,
        sheet_name="fold_all_data_count_summary",
        index=False,
    )

    df_final_average_summary.to_excel(
        writer,
        sheet_name="final_average_summary",
        index=False,
    )

    df_model_structure.to_excel(
        writer,
        sheet_name="model_structure",
        index=False,
    )

    format_excel(writer)

print("\n保存完成:", output_file)


# =========================================================
# 17. 最终方便复制输出
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


anchor_1, anchor_5, anchor_10 = get_final_counts("Anchor_baseline")
explicit_1, explicit_5, explicit_10 = get_final_counts("Explicit_linear_T")

print("\n方法1 全数据预测偏差 1%，5%，10%分别为：")
print(anchor_1)
print(anchor_5)
print(anchor_10)

print("\n方法2 全数据预测偏差 1%，5%，10%分别为：")
print(explicit_1)
print(explicit_5)
print(explicit_10)


# =========================================================
# 18. 代码结构打印
# =========================================================
print("\n========== 当前代码结构简要汇总 ==========")
print("预测对象：Cp / property_value")
print(f"数据文件：{file_path}")
print(f"sheet 名称：{groups_sheet}, {data_sheet}, {anchor_sheet}")
print(f"交叉验证：{n_outer_folds}-fold，按物质划分")
print("方法1：Anchor_baseline，Cp = Cp_anchor + (T - T_anchor) * sum(Nk * Ak)")
print("方法2：Explicit_linear_T，Cp = sum(Nk * Ak) + sum(Nk * Bk * T)")
print("子模型：无；锚点来自 Interpolated_k1_k2 sheet 的插值结果")
print("子模型参数：无")
print("slope 构造：方法1中的 sum(Nk * Ak) 可理解为锚点线性斜率，不读取外部 slope")
print("baseline 构造：方法1为锚点基线；方法2为显式一阶 T 基线")
print("residual 模型：无")
print(f"最终模型：{common_regressor_name}")
print("方法1最终输入：Nk * (T - T_anchor)")
print("方法2最终输入：[Nk, Nk*T]")
print("偏差统计口径：每个 fold 模型预测完整数据集，统计 <1%、<5%、<10% 点数，再对 5 个 fold 取平均")