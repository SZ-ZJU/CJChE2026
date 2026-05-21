# # import pandas as pd
# # import numpy as np
# # from pathlib import Path
# #
# # from sklearn.ensemble import GradientBoostingRegressor, HistGradientBoostingRegressor
# # from sklearn.linear_model import Ridge
# # from sklearn.model_selection import KFold
# # from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
# # from scipy.stats import ttest_rel
# #
# # import warnings
# # warnings.filterwarnings("ignore")
# #
# # pd.set_option("display.float_format", "{:.10f}".format)
# # np.set_printoptions(suppress=True, precision=10)
# #
# # # =========================================================
# # # 0. 全局设置
# # # =========================================================
# # input_file = Path("dataset_selected_by_two_k_with_lnP_invT_interpolation_8points.xlsx")
# # data_sheet = "Data_selected"
# # groups_sheet = "Groups_selected"
# # anchor_sheet = "Interpolated_k1_k2"
# #
# # output_file = Path("GBDT_direct_vs_anchor_baseline_residual_5fold_CV.xlsx")
# #
# # material_key_col = "material_key"
# # temp_col = "T_K"
# # target_candidates = ["lnP_kPa", "lnP", "ln_VaporPressure_kPa", "ln_pressure"]
# #
# # n_group_features_to_use = 220
# # use_fixed_group_position = True
# # group_start_col_1based = 3
# # group_end_col_1based = 222
# #
# # anchor_lnp_col = "lnP_kPa_interp_at_k1Tb"
# # boiling_col = "boiling_T_K"
# # k1_col = "k1"
# # anchor_T_col = "k1_times_boiling_T_K"
# #
# # n_outer_folds = 5
# # random_state = 42
# #
# # # 锚点子模型参数
# # hgb_params = dict(
# #     loss="squared_error", max_iter=1200, learning_rate=0.03,
# #     max_leaf_nodes=63, min_samples_leaf=2, l2_regularization=0.0,
# #     early_stopping=False, random_state=random_state
# # )
# #
# # # 残差 GBDT 参数
# # gbdt_params = {
# #     "n_estimators": 500,
# #     "learning_rate": 0.03,
# #     "max_depth": 3,
# #     "min_samples_split": 10,
# #     "min_samples_leaf": 5,
# #     "subsample": 0.9,
# #     "random_state": random_state
# # }
# #
# # # =========================================================
# # # 1. 读取数据
# # # =========================================================
# # xls = pd.ExcelFile(input_file)
# # df_data = pd.read_excel(input_file, sheet_name=data_sheet)
# # df_groups_raw = pd.read_excel(input_file, sheet_name=groups_sheet)
# # df_anchor = pd.read_excel(input_file, sheet_name=anchor_sheet)
# #
# # print("Data_selected 行数:", len(df_data))
# # print("Groups_selected 物质数:", len(df_groups_raw))
# # print("Interpolated_k1_k2 物质数:", len(df_anchor))
# #
# # # =========================================================
# # # 2. 准备 material_key
# # # =========================================================
# # def is_valid_value(x):
# #     if pd.isna(x): return False
# #     s = str(x).strip()
# #     if s == "" or s.lower() in ["nan","none","null","待定"]: return False
# #     return True
# #
# # def build_material_key(row):
# #     for col in ["material_key","inchikey","cas","compound_name","formula"]:
# #         if col in row.index and is_valid_value(row[col]):
# #             if col=="material_key": return str(row[col]).strip()
# #             return f"{col}:{str(row[col]).strip()}"
# #     return "unknown_material"
# #
# # for df in [df_data, df_groups_raw, df_anchor]:
# #     if material_key_col not in df.columns:
# #         df[material_key_col] = df.apply(build_material_key, axis=1)
# #     df[material_key_col] = df[material_key_col].astype(str).str.strip()
# #
# # # =========================================================
# # # 3. 找到目标列（lnP）
# # # =========================================================
# # def find_first_existing_col(df, candidates, col_type):
# #     for col in candidates:
# #         if col in df.columns:
# #             return col
# #     raise ValueError(f"没有找到 {col_type} 列。候选: {candidates}")
# #
# # target_col = find_first_existing_col(df_data, target_candidates, "target")
# # print("目标列 (lnP):", target_col)
# #
# # # =========================================================
# # # 4. 识别基团列
# # # =========================================================
# # def identify_group_columns(df_groups, n=220):
# #     if use_fixed_group_position:
# #         start_idx = group_start_col_1based - 1
# #         end_excl = group_end_col_1based
# #         if len(df_groups.columns) < end_excl:
# #             raise ValueError(f"基团列数不足，需要到第 {group_end_col_1based} 列")
# #         group_cols = list(df_groups.columns[start_idx:end_excl])
# #         if len(group_cols) != n:
# #             raise ValueError(f"固定列位置识别到 {len(group_cols)} 个基团，需要 {n}")
# #         return group_cols
# #     else:
# #         metadata_keywords = ["original_material_index","material_key","compound","name","cas","formula","smiles","inchi","inchikey","pubchem","phase","property","boiling","temperature","temp","t_k","pressure","lnp","vapor","k1","k2","interp","status","range"]
# #         candidate_cols = []
# #         for col in df_groups.columns:
# #             if any(k in col.lower() for k in metadata_keywords):
# #                 continue
# #             if pd.to_numeric(df_groups[col], errors="coerce").notna().sum()>0:
# #                 candidate_cols.append(col)
# #         if len(candidate_cols) < n:
# #             raise ValueError(f"自动识别基团仅 {len(candidate_cols)} 个，少于 {n}")
# #         return candidate_cols[:n]
# #
# # group_cols_220 = identify_group_columns(df_groups_raw, n_group_features_to_use)
# # df_groups_numeric = df_groups_raw[group_cols_220].apply(pd.to_numeric, errors="coerce").fillna(0.0)
# # nonzero_mask = df_groups_numeric.abs().sum(axis=0) != 0
# # used_group_cols = df_groups_numeric.columns[nonzero_mask].tolist()
# # df_groups_used = df_groups_numeric[used_group_cols].copy()
# # print("有效基团数量:", len(used_group_cols))
# #
# # # =========================================================
# # # 5. 准备锚点数据（每个物质一个，全数据）
# # # =========================================================
# # anchor_keep = [material_key_col, anchor_lnp_col, boiling_col]
# # if k1_col in df_anchor.columns:
# #     anchor_keep.append(k1_col)
# # if anchor_T_col in df_anchor.columns:
# #     anchor_keep.append(anchor_T_col)
# # df_anchor_slim = df_anchor[anchor_keep].drop_duplicates(subset=[material_key_col])
# # df_anchor_slim[anchor_lnp_col] = pd.to_numeric(df_anchor_slim[anchor_lnp_col], errors="coerce")
# # df_anchor_slim[boiling_col] = pd.to_numeric(df_anchor_slim[boiling_col], errors="coerce")
# # if k1_col in df_anchor_slim.columns:
# #     df_anchor_slim["k1_valid"] = pd.to_numeric(df_anchor_slim[k1_col], errors="coerce")
# # else:
# #     df_anchor_slim["k1_valid"] = df_anchor_slim[anchor_T_col] / df_anchor_slim[boiling_col]
# # k1_median = df_anchor_slim["k1_valid"].replace([np.inf,-np.inf],np.nan).median()
# # df_anchor_slim["k1_valid"] = df_anchor_slim["k1_valid"].fillna(k1_median)
# #
# # valid_anchor = (df_anchor_slim[anchor_lnp_col].notna() &
# #                 df_anchor_slim[boiling_col].notna() &
# #                 (df_anchor_slim[boiling_col] > 0) &
# #                 np.isfinite(df_anchor_slim["k1_valid"]))
# # df_anchor_valid = df_anchor_slim[valid_anchor].copy()
# # print("有效锚点物质数:", len(df_anchor_valid))
# #
# # # =========================================================
# # # 6. 全数据训练锚点子模型（预测 lnP_anchor）
# # # =========================================================
# # df_material = df_groups_used.reset_index().rename(columns={"index":"orig_idx"})
# # df_material[material_key_col] = df_groups_raw.loc[df_material.index, material_key_col].values
# # df_material = df_material.merge(df_anchor_valid, on=material_key_col, how="inner")
# # df_material = df_material.dropna(subset=used_group_cols+[anchor_lnp_col, boiling_col, "k1_valid"])
# # df_material = df_material.reset_index(drop=True)
# # print("合并后物质数:", len(df_material))
# #
# # X_anchor = df_material[used_group_cols].values.astype(float)
# # y_lnP_anchor = df_material[anchor_lnp_col].values.astype(float)
# # y_boiling = df_material[boiling_col].values.astype(float)
# #
# # anchor_lnP_model = HistGradientBoostingRegressor(**hgb_params)
# # anchor_boiling_model = HistGradientBoostingRegressor(**hgb_params)
# # anchor_lnP_model.fit(X_anchor, y_lnP_anchor)
# # anchor_boiling_model.fit(X_anchor, y_boiling)
# #
# # df_material["lnP_anchor_pred"] = anchor_lnP_model.predict(X_anchor)
# # df_material["boiling_T_pred"] = anchor_boiling_model.predict(X_anchor)
# # df_material["anchor_T_pred"] = df_material["k1_valid"] * df_material["boiling_T_pred"]
# # df_material["invT_anchor_pred"] = 1.0 / df_material["anchor_T_pred"]
# #
# # # =========================================================
# # # 7. 展开温度点数据
# # # =========================================================
# # df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
# # df_data[target_col] = pd.to_numeric(df_data[target_col], errors="coerce")
# # df_data["InvT"] = 1.0 / df_data[temp_col]
# #
# # df_long = df_data.merge(df_material[[material_key_col] + used_group_cols + ["lnP_anchor_pred", "invT_anchor_pred"]],
# #                         on=material_key_col, how="inner")
# # df_long = df_long.dropna(subset=[target_col, temp_col, "InvT"] + used_group_cols + ["lnP_anchor_pred", "invT_anchor_pred"])
# # df_long = df_long.reset_index(drop=True)
# # print("最终温度点总数:", len(df_long))
# #
# # X_groups = df_long[used_group_cols].values.astype(float)
# # invT_all = df_long["InvT"].values.astype(float)
# # lnP_true = df_long[target_col].values.astype(float)
# # lnP_anchor_pred = df_long["lnP_anchor_pred"].values.astype(float)
# # invT_anchor_pred = df_long["invT_anchor_pred"].values.astype(float)
# # material_keys = df_long[material_key_col].values
# #
# # unique_materials = np.unique(material_keys)
# # material_to_idx = {k:i for i,k in enumerate(unique_materials)}
# # material_ids = np.array([material_to_idx[k] for k in material_keys])
# #
# # # =========================================================
# # # 8. 构建方法A特征
# # # =========================================================
# # def build_direct_features(sample_mask):
# #     return np.hstack([X_groups[sample_mask], invT_all[sample_mask].reshape(-1,1)])
# #
# # # =========================================================
# # # 9. 方法B：锚点+线性基线+残差GBDT
# # # =========================================================
# # def train_and_predict_methodB(train_mask, test_mask):
# #     df_train = df_long[train_mask].copy()
# #     df_test = df_long[test_mask].copy()
# #
# #     delta_invT_train = df_train["InvT"].values - df_train["invT_anchor_pred"].values
# #     X_base_train = df_train[used_group_cols].values * delta_invT_train.reshape(-1, 1)
# #     y_base_train = df_train[target_col].values - df_train["lnP_anchor_pred"].values
# #
# #     valid_base = np.isfinite(X_base_train).all(axis=1) & np.isfinite(y_base_train)
# #     if valid_base.sum() == 0:
# #         raise ValueError("基线模型无有效训练样本")
# #     base_model = Ridge(alpha=1.0, fit_intercept=False)
# #     base_model.fit(X_base_train[valid_base], y_base_train[valid_base])
# #
# #     delta_invT_test = df_test["InvT"].values - df_test["invT_anchor_pred"].values
# #     X_base_test = df_test[used_group_cols].values * delta_invT_test.reshape(-1, 1)
# #     valid_base_test = np.isfinite(X_base_test).all(axis=1)
# #     baseline_delta = np.full(len(df_test), np.nan)
# #     baseline_delta[valid_base_test] = base_model.predict(X_base_test[valid_base_test])
# #     baseline_lnP = df_test["lnP_anchor_pred"].values + baseline_delta
# #
# #     # 残差训练
# #     delta_invT_train2 = df_train["InvT"].values - df_train["invT_anchor_pred"].values
# #     X_base_train2 = df_train[used_group_cols].values * delta_invT_train2.reshape(-1, 1)
# #     baseline_delta_train = base_model.predict(X_base_train2)
# #     baseline_lnP_train = df_train["lnP_anchor_pred"].values + baseline_delta_train
# #     residual_y_train = df_train[target_col].values - baseline_lnP_train
# #
# #     residual_X_train = np.hstack([df_train[used_group_cols].values, df_train["InvT"].values.reshape(-1, 1)])
# #     valid_res = np.isfinite(residual_X_train).all(axis=1) & np.isfinite(residual_y_train)
# #     if valid_res.sum() == 0:
# #         raise ValueError("残差模型无有效训练样本")
# #     res_model = GradientBoostingRegressor(**gbdt_params)
# #     res_model.fit(residual_X_train[valid_res], residual_y_train[valid_res])
# #
# #     residual_X_test = np.hstack([df_test[used_group_cols].values, df_test["InvT"].values.reshape(-1, 1)])
# #     valid_res_test = np.isfinite(residual_X_test).all(axis=1)
# #     residual_pred = np.full(len(df_test), np.nan)
# #     residual_pred[valid_res_test] = res_model.predict(residual_X_test[valid_res_test])
# #
# #     final_lnP = baseline_lnP + residual_pred
# #     return final_lnP
# #
# # # =========================================================
# # # 10. 5折交叉验证（只计算 lnP 指标）
# # # =========================================================
# # kf = KFold(n_splits=n_outer_folds, shuffle=True, random_state=random_state)
# # metrics_direct = []
# # metrics_methodB = []
# #
# # def compute_metrics_lnP(y_true, y_pred):
# #     """只计算 lnP 空间的指标"""
# #     mask = np.isfinite(y_true) & np.isfinite(y_pred)
# #     y_true = y_true[mask]
# #     y_pred = y_pred[mask]
# #     if len(y_true) == 0:
# #         return {k: np.nan for k in ["R2", "MSE", "RMSE", "MAE"]}
# #     r2 = r2_score(y_true, y_pred)
# #     mse = mean_squared_error(y_true, y_pred)
# #     rmse = np.sqrt(mse)
# #     mae = mean_absolute_error(y_true, y_pred)
# #     return {"R2": r2, "MSE": mse, "RMSE": rmse, "MAE": mae}
# #
# # for fold, (train_idx, test_idx) in enumerate(kf.split(unique_materials)):
# #     print(f"\n========== Fold {fold+1}/{n_outer_folds} ==========")
# #     train_materials = unique_materials[train_idx]
# #     test_materials = unique_materials[test_idx]
# #
# #     train_mask = np.isin(material_keys, train_materials)
# #     test_mask = np.isin(material_keys, test_materials)
# #
# #     # ---- 方法A ----
# #     X_train_A = build_direct_features(train_mask)
# #     y_train_A = lnP_true[train_mask]
# #     valid_A = np.isfinite(X_train_A).all(axis=1) & np.isfinite(y_train_A)
# #     X_train_A = X_train_A[valid_A]
# #     y_train_A = y_train_A[valid_A]
# #     model_A = GradientBoostingRegressor(**gbdt_params)
# #     model_A.fit(X_train_A, y_train_A)
# #
# #     X_test_A = build_direct_features(test_mask)
# #     y_test_A = lnP_true[test_mask]
# #     valid_test_A = np.isfinite(X_test_A).all(axis=1)
# #     y_pred_A = np.full(len(y_test_A), np.nan)
# #     y_pred_A[valid_test_A] = model_A.predict(X_test_A[valid_test_A])
# #
# #     # ---- 方法B ----
# #     try:
# #         y_pred_B = train_and_predict_methodB(train_mask, test_mask)
# #     except Exception as e:
# #         print(f"  Fold {fold+1} 方法B失败: {e}")
# #         y_pred_B = np.full(len(y_test_A), np.nan)
# #
# #     m_A = compute_metrics_lnP(y_test_A, y_pred_A)
# #     m_B = compute_metrics_lnP(y_test_A, y_pred_B)
# #     m_A["fold"] = fold+1
# #     m_B["fold"] = fold+1
# #     metrics_direct.append(m_A)
# #     metrics_methodB.append(m_B)
# #
# # # =========================================================
# # # 11. 汇总统计
# # # =========================================================
# # df_direct = pd.DataFrame(metrics_direct)
# # df_methodB = pd.DataFrame(metrics_methodB)
# #
# # metric_names = [c for c in df_direct.columns if c != "fold"]
# #
# # def summarize(df, name):
# #     rows = []
# #     for metric in metric_names:
# #         vals = df[metric].dropna().values
# #         if len(vals) == 0:
# #             mean_std = "NaN"
# #         else:
# #             mean_val = np.mean(vals)
# #             std_val = np.std(vals, ddof=1)
# #             mean_std = f"{mean_val:.4f} ± {std_val:.4f}"
# #         rows.append({"Model": name, "Metric": metric, "Mean±Std": mean_std})
# #     return pd.DataFrame(rows)
# #
# # summary_direct = summarize(df_direct, "GBDT_direct")
# # summary_methodB = summarize(df_methodB, "Anchor+linear+GBDT_residual")
# # summary_all = pd.concat([summary_direct, summary_methodB], ignore_index=True)
# #
# # print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
# # print(summary_all.to_string(index=False))
# #
# # # =========================================================
# # # 12. 配对 t 检验
# # # =========================================================
# # t_test_results = []
# # for metric in metric_names:
# #     vals_A = df_direct[metric].dropna().values
# #     vals_B = df_methodB[metric].dropna().values
# #     if len(vals_A) == len(vals_B) and len(vals_A) > 1:
# #         t_stat, p_val = ttest_rel(vals_A, vals_B)
# #         if metric == "R2":
# #             better = "methodB" if np.mean(vals_B) > np.mean(vals_A) else "direct"
# #             sig = p_val < 0.05
# #         else:
# #             better = "methodB" if np.mean(vals_B) < np.mean(vals_A) else "direct"
# #             sig = p_val < 0.05
# #         t_test_results.append({
# #             "Metric": metric,
# #             "Mean_direct": f"{np.mean(vals_A):.4f}",
# #             "Mean_methodB": f"{np.mean(vals_B):.4f}",
# #             "p-value": f"{p_val:.4e}",
# #             "Significant(p<0.05)": sig,
# #             "Better model": better
# #         })
# #
# # df_ttest = pd.DataFrame(t_test_results)
# # print("\n========== Paired t-test ==========")
# # print(df_ttest.to_string(index=False))
# #
# # # =========================================================
# # # 13. 保存结果
# # # =========================================================
# # with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
# #     df_direct.to_excel(writer, sheet_name="Fold_Metrics_Direct", index=False)
# #     df_methodB.to_excel(writer, sheet_name="Fold_Metrics_MethodB", index=False)
# #     summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
# #     df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)
# #
# #     pd.DataFrame([
# #         {"param": "n_outer_folds", "value": n_outer_folds},
# #         {"param": "random_state", "value": random_state},
# #         {"param": "n_group_features", "value": len(used_group_cols)},
# #         {"param": "total_samples", "value": len(lnP_true)},
# #         {"param": "n_materials", "value": len(unique_materials)},
# #         {"param": "direct_GBDT_params", "value": str(gbdt_params)},
# #         {"param": "methodB_baseline", "value": "Ridge(alpha=1.0, fit_intercept=False)"},
# #         {"param": "methodB_residual_gbdt", "value": "same as direct GBDT"},
# #         {"param": "anchor_submodel", "value": "HistGradientBoostingRegressor"},
# #     ]).to_excel(writer, sheet_name="Run_Info", index=False)
# #
# #     from openpyxl import load_workbook
# #     workbook = writer.book
# #     number_format = "0.0000000000"
# #     for sheetname in writer.sheets:
# #         ws = workbook[sheetname]
# #         for row in ws.iter_rows():
# #             for cell in row:
# #                 if isinstance(cell.value, float):
# #                     cell.number_format = number_format
# #         for col in ws.columns:
# #             max_len = 0
# #             col_letter = col[0].column_letter
# #             for cell in col:
# #                 if cell.value:
# #                     max_len = max(max_len, len(str(cell.value)))
# #             ws.column_dimensions[col_letter].width = min(max_len+2, 40)
# #
# # print(f"\n保存完成: {output_file}")
#
#
# # -*- coding: utf-8 -*-
# """
# Vapor pressure:
# QSPR 25 descriptors + 1/T vs QSPR 25 descriptors + 1/T + slope
# Random Forest 5-fold CV comparison
#
# 输入 1：
#     selected_descriptors_with_vp_mean_target.xlsx
#     sheet:
#         Selected_Features_Target
#         Selected_Features
#
# 输入 2：
#     dataset_selected_by_two_k_with_lnP_invT_interpolation_8points.xlsx
#     sheet:
#         Data_selected
#
# 输入 3：
#     HistGB_submodels_predict_ref_lnP_Tb_and_slope.xlsx / .xls
#     或其他候选 slope 文件
#     sheet:
#         slope
#
# 比较模型：
#     模型 A：RF(desc + 1/T)
#     模型 B：RF(desc + 1/T + slope_pred_lnP_over_invT)
#
# 目标：
#     优先使用 lnP_kPa / lnP
#     如果目标是 lnP，则同时输出 lnP 空间指标和 P 空间指标。
#
# 输出：
#     RF_vp_QSPR25_5fold_CV_comparison_with_slope.xlsx
# """
#
# import pandas as pd
# import numpy as np
# from pathlib import Path
#
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.model_selection import KFold
# from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
#
# try:
#     from scipy.stats import ttest_rel
#     SCIPY_AVAILABLE = True
# except Exception:
#     SCIPY_AVAILABLE = False
#
#
# pd.set_option("display.float_format", "{:.10f}".format)
# np.set_printoptions(suppress=True, precision=10)
#
#
# # =========================================================
# # 0. 全局设置
# # =========================================================
#
# descriptor_file = Path("selected_descriptors_with_vp_mean_target.xlsx")
# descriptor_sheet = "Selected_Features_Target"
# selected_feature_sheet = "Selected_Features"
#
# data_file = Path("dataset_selected_by_two_k_with_lnP_invT_interpolation_8points.xlsx")
# data_sheet = "Data_selected"
#
# # slope 文件候选。如果你的真实文件名不同，在这里加进去即可。
# slope_file_candidates = [
#     Path("HistGB_submodels_predict_ref_lnP_Tb_and_slope.xlsx"),
#     Path("HistGB_submodels_predict_ref_lnP_Tb_and_slope.xls"),
#     Path("HistGB_submodels_predict_ref_vp_Tb_and_slope.xlsx"),
#     Path("HistGB_submodels_predict_ref_vp_Tb_and_slope.xls"),
#     Path("HistGB_submodels_predict_ref_lnP_invT_Tb_and_slope.xlsx"),
#     Path("HistGB_submodels_predict_ref_lnP_invT_Tb_and_slope.xls"),
# ]
#
# slope_sheet_candidates = [
#     "slope",
#     "Slope",
#     "Predicted_Slope",
# ]
#
# slope_col_candidates = [
#     "slope_pred_lnP_over_invT",
#     "slope_pred_lnp_over_invT",
#     "slope_pred_lnP_over_InvT",
#     "slope_pred_lnP_over_inverse_T",
#     "slope_pred_vp_over_invT",
#     "slope_pred_P_over_invT",
#     "slope_true_ref_lnP_over_invT",
# ]
#
# output_file = Path("RF_vp_QSPR25_5fold_CV_comparison_with_slope.xlsx")
#
# material_key_col = "material_key"
# temp_col = "T_K"
#
# # 目标列候选：优先 lnP
# target_candidates = [
#     "lnP_kPa",
#     "lnP",
#     "ln_P",
#     "lnP_value",
#     "ln_pressure",
#     "ln_VaporPressure_kPa",
#     "lnVaporPressure",
#     "ln vapor pressure",
#     "ln(P)",
#     "ln_P_kPa",
#     "property_value",
#     "VaporPressure_kPa",
#     "vapor_pressure_kPa",
#     "Vapor_Pressure_kPa",
#     "P_vapor_kPa",
#     "P_kPa",
#     "P",
#     "pressure",
#     "Pressure",
# ]
#
# n_outer_folds = 5
# random_state = 42
#
# # Random Forest 参数，与之前 viscosity 示例保持一致
# rf_params = {
#     "n_estimators": 500,
#     "max_depth": None,
#     "min_samples_split": 2,
#     "min_samples_leaf": 1,
#     "max_features": "sqrt",
#     "bootstrap": True,
#     "random_state": random_state,
#     "n_jobs": -1,
# }
#
#
# # =========================================================
# # 1. 辅助函数
# # =========================================================
#
# def normalize_colname(name):
#     return (
#         str(name)
#         .lower()
#         .replace(" ", "")
#         .replace("_", "")
#         .replace("-", "")
#         .replace("(", "")
#         .replace(")", "")
#         .replace("/", "")
#         .replace(".", "")
#         .replace(",", "")
#     )
#
#
# def find_first_existing_col(df, candidates, required=True, col_type="列"):
#     norm_map = {normalize_colname(c): c for c in df.columns}
#
#     for c in candidates:
#         key = normalize_colname(c)
#         if key in norm_map:
#             return norm_map[key]
#
#     if required:
#         raise ValueError(
#             f"没有找到 {col_type}。\n"
#             f"候选列名: {candidates}\n"
#             f"当前列名: {list(df.columns)}"
#         )
#
#     return None
#
#
# def is_valid_value(x):
#     if pd.isna(x):
#         return False
#
#     s = str(x).strip()
#
#     if s == "":
#         return False
#
#     if s.lower() in ["nan", "none", "null", "待定"]:
#         return False
#
#     return True
#
#
# def clean_key_value(x):
#     """
#     清理物质 ID：
#         123.0 -> '123'
#         其他字符串保留。
#     """
#     if not is_valid_value(x):
#         return np.nan
#
#     s = str(x).strip()
#
#     try:
#         f = float(s)
#
#         if np.isfinite(f) and abs(f - round(f)) < 1e-8:
#             return str(int(round(f)))
#
#     except Exception:
#         pass
#
#     return s
#
#
# def safe_exp(x):
#     x = np.asarray(x, dtype=float)
#     return np.exp(np.clip(x, -700, 700))
#
#
# def safe_log(x):
#     x = np.asarray(x, dtype=float)
#     out = np.full_like(x, np.nan, dtype=float)
#
#     mask = np.isfinite(x) & (x > 0)
#
#     out[mask] = np.log(x[mask])
#
#     return out
#
#
# def infer_target_is_log(target_col):
#     col_norm = normalize_colname(target_col)
#
#     if "ln" in col_norm or "log" in col_norm:
#         return True
#
#     # 对你的当前数据，property_value 通常就是 lnP
#     if col_norm == "propertyvalue":
#         return True
#
#     return False
#
#
# def find_alignment_key(df_desc, df_data):
#     """
#     描述符表与 Data_selected 的对齐键。
#     """
#     candidate_pairs = [
#         ("material_key", "material_key"),
#         ("original_material_index", "original_material_index"),
#
#         ("pubchem_cid", "pubchem_cid"),
#         ("pubchem_cid_for_Tb", "pubchem_cid_for_Tb"),
#         ("CID", "pubchem_cid"),
#         ("CID_int", "pubchem_cid"),
#         ("sdf_pubchem_cid", "pubchem_cid"),
#
#         ("inchikey", "inchikey"),
#         ("InChIKey", "InChIKey"),
#         ("pubchem_inchikey", "pubchem_inchikey"),
#         ("inchikey_from_rdkit", "inchikey"),
#
#         ("cas", "cas"),
#         ("compound_name", "compound_name"),
#     ]
#
#     for dcol, dacol in candidate_pairs:
#         if dcol in df_desc.columns and dacol in df_data.columns:
#             return dcol, dacol
#
#     return None, None
#
#
# def choose_data_group_key(df_data):
#     for col in [
#         "material_key",
#         "original_material_index",
#         "pubchem_cid",
#         "pubchem_cid_for_Tb",
#         "CID",
#         "CID_int",
#         "inchikey",
#         "InChIKey",
#         "pubchem_inchikey",
#         "cas",
#         "compound_name",
#     ]:
#         if col in df_data.columns:
#             return col
#
#     return None
#
#
# def find_slope_key(df_slope, preferred_data_key_col):
#     if preferred_data_key_col is not None and preferred_data_key_col in df_slope.columns:
#         return preferred_data_key_col
#
#     for col in [
#         "material_key",
#         "original_material_index",
#         "pubchem_cid",
#         "pubchem_cid_for_Tb",
#         "CID",
#         "CID_int",
#         "sdf_pubchem_cid",
#         "inchikey",
#         "InChIKey",
#         "pubchem_inchikey",
#         "cas",
#         "compound_name",
#     ]:
#         if col in df_slope.columns:
#             return col
#
#     return None
#
#
# def read_slope_file(slope_paths, sheet_candidates):
#     """
#     从候选 slope 文件中读取第一个存在的文件。
#     """
#     slope_path_used = None
#
#     for p in slope_paths:
#         if p.exists():
#             slope_path_used = p
#             break
#
#     if slope_path_used is None:
#         msg = "没有找到 slope 文件，已尝试以下路径：\n"
#         msg += "\n".join([str(p) for p in slope_paths])
#         raise FileNotFoundError(msg)
#
#     xls = pd.ExcelFile(slope_path_used)
#
#     sheet = None
#
#     for s in sheet_candidates:
#         if s in xls.sheet_names:
#             sheet = s
#             break
#
#     if sheet is None:
#         sheet = xls.sheet_names[0]
#
#     df = pd.read_excel(slope_path_used, sheet_name=sheet)
#
#     return df, slope_path_used, sheet
#
#
# def calc_metrics_vp(y_true, y_pred, target_is_log):
#     """
#     计算 vapor pressure 指标。
#
#     如果 target_is_log=True：
#         y_true/y_pred 是 lnP
#         同时输出 lnP 空间指标和 P 空间指标
#
#     如果 target_is_log=False：
#         y_true/y_pred 是 P
#         同时输出 P 空间指标和 lnP 空间指标
#     """
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
#             "R2_lnP": np.nan,
#             "MSE_lnP": np.nan,
#             "RMSE_lnP": np.nan,
#             "MAE_lnP": np.nan,
#             "ARD_lnP_percent": np.nan,
#
#             "R2_P": np.nan,
#             "MSE_P": np.nan,
#             "RMSE_P": np.nan,
#             "MAE_P": np.nan,
#             "ARD_P_percent": np.nan,
#
#             "leq1%": np.nan,
#             "leq5%": np.nan,
#             "leq10%": np.nan,
#             "max_rel%": np.nan,
#         }
#
#     if target_is_log:
#         ln_true = y_true
#         ln_pred = y_pred
#
#         P_true = safe_exp(y_true)
#         P_pred = safe_exp(y_pred)
#
#     else:
#         P_true = y_true
#         P_pred = y_pred
#
#         ln_true = safe_log(y_true)
#         ln_pred = safe_log(y_pred)
#
#     # ---------- lnP 空间 ----------
#     ln_mask = np.isfinite(ln_true) & np.isfinite(ln_pred)
#
#     if ln_mask.sum() >= 2:
#         R2_lnP = r2_score(ln_true[ln_mask], ln_pred[ln_mask])
#         MSE_lnP = mean_squared_error(ln_true[ln_mask], ln_pred[ln_mask])
#         RMSE_lnP = np.sqrt(MSE_lnP)
#         MAE_lnP = mean_absolute_error(ln_true[ln_mask], ln_pred[ln_mask])
#
#         valid_ln_rel = np.abs(ln_true[ln_mask]) > 1e-12
#
#         if valid_ln_rel.sum() > 0:
#             ARD_lnP = (
#                 np.mean(
#                     np.abs(
#                         (ln_pred[ln_mask][valid_ln_rel] - ln_true[ln_mask][valid_ln_rel])
#                         / ln_true[ln_mask][valid_ln_rel]
#                     )
#                 )
#                 * 100.0
#             )
#         else:
#             ARD_lnP = np.nan
#     else:
#         R2_lnP = np.nan
#         MSE_lnP = np.nan
#         RMSE_lnP = np.nan
#         MAE_lnP = np.nan
#         ARD_lnP = np.nan
#
#     # ---------- P 空间 ----------
#     P_mask = np.isfinite(P_true) & np.isfinite(P_pred)
#
#     if P_mask.sum() >= 2:
#         R2_P = r2_score(P_true[P_mask], P_pred[P_mask])
#         MSE_P = mean_squared_error(P_true[P_mask], P_pred[P_mask])
#         RMSE_P = np.sqrt(MSE_P)
#         MAE_P = mean_absolute_error(P_true[P_mask], P_pred[P_mask])
#
#         valid_P_rel = np.abs(P_true[P_mask]) > 1e-12
#
#         if valid_P_rel.sum() > 0:
#             rel_err = (
#                 np.abs(
#                     (P_pred[P_mask][valid_P_rel] - P_true[P_mask][valid_P_rel])
#                     / P_true[P_mask][valid_P_rel]
#                 )
#                 * 100.0
#             )
#
#             ARD_P = np.mean(rel_err)
#             le1 = np.mean(rel_err <= 1.0) * 100.0
#             le5 = np.mean(rel_err <= 5.0) * 100.0
#             le10 = np.mean(rel_err <= 10.0) * 100.0
#             max_rel = np.max(rel_err)
#         else:
#             ARD_P = np.nan
#             le1 = np.nan
#             le5 = np.nan
#             le10 = np.nan
#             max_rel = np.nan
#
#     else:
#         R2_P = np.nan
#         MSE_P = np.nan
#         RMSE_P = np.nan
#         MAE_P = np.nan
#         ARD_P = np.nan
#         le1 = np.nan
#         le5 = np.nan
#         le10 = np.nan
#         max_rel = np.nan
#
#     return {
#         "R2_lnP": R2_lnP,
#         "MSE_lnP": MSE_lnP,
#         "RMSE_lnP": RMSE_lnP,
#         "MAE_lnP": MAE_lnP,
#         "ARD_lnP_percent": ARD_lnP,
#
#         "R2_P": R2_P,
#         "MSE_P": MSE_P,
#         "RMSE_P": RMSE_P,
#         "MAE_P": MAE_P,
#         "ARD_P_percent": ARD_P,
#
#         "leq1%": le1,
#         "leq5%": le5,
#         "leq10%": le10,
#         "max_rel%": max_rel,
#     }
#
#
# def format_metric_value(metric, value):
#     if pd.isna(value):
#         return "NaN"
#
#     if metric in ["MSE_lnP", "MSE_P"]:
#         return f"{value:.12f}"
#
#     if metric in ["RMSE_lnP", "RMSE_P", "MAE_lnP", "MAE_P"]:
#         return f"{value:.10f}"
#
#     return f"{value:.6f}"
#
#
# def summarize(df, name):
#     metric_names = [c for c in df.columns if c != "fold"]
#
#     rows = []
#
#     for metric in metric_names:
#         vals = pd.to_numeric(df[metric], errors="coerce").dropna().values
#
#         if len(vals) == 0:
#             mean_val = np.nan
#             std_val = np.nan
#             mean_std = "NaN"
#
#         elif len(vals) == 1:
#             mean_val = float(np.mean(vals))
#             std_val = np.nan
#             mean_std = f"{format_metric_value(metric, mean_val)} ± NaN"
#
#         else:
#             mean_val = float(np.mean(vals))
#             std_val = float(np.std(vals, ddof=1))
#             mean_std = (
#                 f"{format_metric_value(metric, mean_val)} ± "
#                 f"{format_metric_value(metric, std_val)}"
#             )
#
#         rows.append({
#             "Model": name,
#             "Metric": metric,
#             "Mean": mean_val,
#             "Std": std_val,
#             "Mean±Std": mean_std,
#         })
#
#     return pd.DataFrame(rows)
#
#
# # =========================================================
# # 2. 读取数据
# # =========================================================
#
# if not descriptor_file.exists():
#     raise FileNotFoundError(
#         f"没有找到描述符文件: {descriptor_file}\n"
#         "请先运行 vapor pressure 的 25 个描述符筛选代码。"
#     )
#
# if not data_file.exists():
#     raise FileNotFoundError(f"没有找到 vapor pressure 数据文件: {data_file}")
#
# df_desc = pd.read_excel(descriptor_file, sheet_name=descriptor_sheet)
# df_data = pd.read_excel(data_file, sheet_name=data_sheet)
# df_slope, slope_path_used, slope_sheet_used = read_slope_file(
#     slope_file_candidates,
#     slope_sheet_candidates,
# )
#
# print("描述符表行数:", len(df_desc))
# print("原始数据行数:", len(df_data))
# print("Slope 表行数:", len(df_slope))
# print("Slope 文件:", slope_path_used)
# print("Slope sheet:", slope_sheet_used)
#
#
# # =========================================================
# # 3. 确定物质 ID 列
# # =========================================================
#
# desc_key_col, data_key_col = find_alignment_key(df_desc, df_data)
# data_group_col = choose_data_group_key(df_data)
# slope_key_col = find_slope_key(df_slope, data_key_col)
#
# print("\n物质对齐方式:")
# print("  desc_key_col:", desc_key_col)
# print("  data_key_col:", data_key_col)
# print("  data_group_col:", data_group_col)
# print("  slope_key_col:", slope_key_col)
#
# if slope_key_col is None:
#     raise ValueError("无法在 slope 表中找到物质 ID 列。")
#
#
# # =========================================================
# # 4. 读取 25 个描述符列表
# # =========================================================
#
# xls_desc = pd.ExcelFile(descriptor_file)
#
# if selected_feature_sheet in xls_desc.sheet_names:
#     df_selected = pd.read_excel(descriptor_file, sheet_name=selected_feature_sheet)
#
#     if "selected_feature" in df_selected.columns:
#         feature_cols = df_selected["selected_feature"].dropna().astype(str).tolist()
#     else:
#         feature_cols = df_selected.iloc[:, 0].dropna().astype(str).tolist()
#
# else:
#     meta = [
#         "material_index",
#         "original_material_index",
#         "material_key",
#         "compound_name",
#         "cas",
#         "formula",
#         "SMILES",
#         "smiles",
#         "final_smiles",
#         "inchikey",
#         "InChIKey",
#         "pubchem_inchikey",
#         "pubchem_cid",
#         "pubchem_cid_for_Tb",
#         "CID",
#         "CID_int",
#         "phase",
#         "boiling_T_K",
#         "critical_T_K",
#         "T_min",
#         "T_max",
#         "T_range",
#         "n_points",
#         "target_n_valid_points",
#         "target_min_vp",
#         "target_max_vp",
#         "target_mean_vp",
#     ]
#
#     feature_cols = [c for c in df_desc.columns if c not in meta]
#
# missing_features = [c for c in feature_cols if c not in df_desc.columns]
#
# if len(missing_features) > 0:
#     raise ValueError(
#         "以下选中描述符不在描述符表中：\n"
#         f"{missing_features}"
#     )
#
# print("\n原始选中描述符数量:", len(feature_cols))
#
#
# # =========================================================
# # 5. 数值化描述符，删除无效列
# # =========================================================
#
# df_feature_raw = df_desc[feature_cols].copy()
#
# df_features = df_feature_raw.apply(
#     pd.to_numeric,
#     errors="coerce"
# )
#
# df_features = df_features.replace([np.inf, -np.inf], np.nan)
#
# # 均值填充
# df_features = df_features.fillna(df_features.mean())
#
# # 如果仍有 NaN，删除该列
# df_features = df_features.dropna(axis=1, how="any")
#
# # 删除全零列
# nonzero = df_features.abs().sum(axis=0) != 0
#
# used_feature_cols = df_features.columns[nonzero].tolist()
#
# print("有效描述符数量:", len(used_feature_cols))
#
# if len(used_feature_cols) == 0:
#     raise ValueError("没有有效描述符可用于建模。")
#
#
# # =========================================================
# # 6. 找到温度列、目标列、斜率列
# # =========================================================
#
# temp_col_actual = find_first_existing_col(
#     df_data,
#     [temp_col, "T_K", "Temperature", "temperature"],
#     required=True,
#     col_type="温度列",
# )
#
# target_col = find_first_existing_col(
#     df_data,
#     target_candidates,
#     required=True,
#     col_type="vapor pressure 目标列",
# )
#
# slope_col = find_first_existing_col(
#     df_slope,
#     slope_col_candidates,
#     required=True,
#     col_type="斜率列",
# )
#
# target_is_log = infer_target_is_log(target_col)
#
# print("\n温度列:", temp_col_actual)
# print("目标列:", target_col)
# print("目标是否为 lnP:", target_is_log)
# print("斜率列:", slope_col)
#
# df_data[temp_col_actual] = pd.to_numeric(df_data[temp_col_actual], errors="coerce")
# df_data[target_col] = pd.to_numeric(df_data[target_col], errors="coerce")
# df_slope[slope_col] = pd.to_numeric(df_slope[slope_col], errors="coerce")
#
#
# # =========================================================
# # 7. 合并数据，构造按物质展开的特征矩阵
# # =========================================================
#
# X_no_slope = []
# X_with_slope = []
# y = []
# material_ids = []
# row_meta = []
#
# # ---------- 7.1 优先使用公共 ID 对齐 ----------
# if desc_key_col is not None and data_key_col is not None:
#     df_desc_work = df_desc.copy()
#     df_data_work = df_data.copy()
#     df_slope_work = df_slope.copy()
#
#     df_desc_work["_key"] = df_desc_work[desc_key_col].apply(clean_key_value)
#     df_data_work["_key"] = df_data_work[data_key_col].apply(clean_key_value)
#     df_slope_work["_key"] = df_slope_work[slope_key_col].apply(clean_key_value)
#
#     df_desc_work = df_desc_work.dropna(subset=["_key"]).copy()
#     df_data_work = df_data_work.dropna(subset=["_key"]).copy()
#     df_slope_work = df_slope_work.dropna(subset=["_key"]).copy()
#
#     df_desc_work = df_desc_work.drop_duplicates(subset=["_key"], keep="first")
#     df_slope_work = df_slope_work.drop_duplicates(subset=["_key"], keep="first")
#
#     # 同步描述符数值列
#     df_desc_work[used_feature_cols] = df_features.loc[
#         df_desc_work.index,
#         used_feature_cols
#     ].values
#
#     desc_map = {
#         row["_key"]: row[used_feature_cols].values.astype(float)
#         for _, row in df_desc_work.iterrows()
#     }
#
#     slope_map = (
#         df_slope_work
#         .set_index("_key")[slope_col]
#         .to_dict()
#     )
#
#     data_keys_in_order = df_data_work["_key"].drop_duplicates().tolist()
#
#     valid_keys = [
#         k for k in data_keys_in_order
#         if k in desc_map
#         and k in slope_map
#         and np.isfinite(slope_map[k])
#     ]
#
#     if len(valid_keys) == 0:
#         raise ValueError("没有同时拥有描述符、数据点和有效 slope 的物质。")
#
#     print("\n同时拥有描述符、数据点和 slope 的物质数:", len(valid_keys))
#
#     for key in valid_keys:
#         desc = np.asarray(desc_map[key], dtype=float)
#         slope_val = float(slope_map[key])
#
#         sub = df_data_work[df_data_work["_key"] == key].copy()
#
#         for _, row in sub.iterrows():
#             T = row[temp_col_actual]
#             yv = row[target_col]
#
#             if not (
#                 np.isfinite(T)
#                 and np.isfinite(yv)
#                 and abs(T) > 1e-12
#             ):
#                 continue
#
#             invT = 1.0 / T
#
#             X_no_slope.append(
#                 np.concatenate([desc, [invT]])
#             )
#
#             X_with_slope.append(
#                 np.concatenate([desc, [invT, slope_val]])
#             )
#
#             y.append(yv)
#             material_ids.append(key)
#
#             meta = {
#                 "_key": key,
#                 temp_col_actual: T,
#                 "InvT": invT,
#                 target_col: yv,
#                 slope_col: slope_val,
#             }
#
#             for c in [
#                 "material_key",
#                 "original_material_index",
#                 "compound_name",
#                 "cas",
#                 "formula",
#                 "SMILES",
#                 "smiles",
#                 "final_smiles",
#                 "inchikey",
#                 "pubchem_inchikey",
#                 "pubchem_cid",
#                 "pubchem_cid_for_Tb",
#                 "boiling_T_K",
#                 "critical_T_K",
#                 "T_min",
#                 "T_max",
#                 "T_range",
#                 "RSQ_lnP_vs_invT",
#                 "slope_lnP_vs_invT",
#                 "RSQ_lnP_vs_T",
#             ]:
#                 if c in row.index:
#                     meta[c] = row[c]
#
#             row_meta.append(meta)
#
# # ---------- 7.2 备用：按物质顺序对齐 ----------
# else:
#     print("\n没有找到可用于描述符和数据对齐的共同 ID，尝试按物质顺序对齐。")
#
#     if data_group_col is None:
#         raise ValueError("无法确定 Data_selected 中的物质分组列。")
#
#     df_data_work = df_data.copy()
#     df_slope_work = df_slope.copy()
#
#     df_data_work["_group"] = df_data_work[data_group_col].apply(clean_key_value)
#     groups = df_data_work["_group"].drop_duplicates().tolist()
#
#     if len(groups) != len(df_features):
#         raise ValueError(
#             "物质分组数量与描述符行数不一致，无法按顺序对齐。\n"
#             f"Data 物质数 = {len(groups)}\n"
#             f"描述符行数 = {len(df_features)}"
#         )
#
#     df_slope_work["_key"] = df_slope_work[slope_key_col].apply(clean_key_value)
#     df_slope_work = df_slope_work.dropna(subset=["_key"]).drop_duplicates("_key")
#
#     slope_map = df_slope_work.set_index("_key")[slope_col].to_dict()
#
#     for i, key in enumerate(groups):
#         if key not in slope_map or not np.isfinite(slope_map[key]):
#             continue
#
#         desc = df_features.iloc[i][used_feature_cols].values.astype(float)
#         slope_val = float(slope_map[key])
#
#         sub = df_data_work[df_data_work["_group"] == key]
#
#         for _, row in sub.iterrows():
#             T = row[temp_col_actual]
#             yv = row[target_col]
#
#             if not (
#                 np.isfinite(T)
#                 and np.isfinite(yv)
#                 and abs(T) > 1e-12
#             ):
#                 continue
#
#             invT = 1.0 / T
#
#             X_no_slope.append(
#                 np.concatenate([desc, [invT]])
#             )
#
#             X_with_slope.append(
#                 np.concatenate([desc, [invT, slope_val]])
#             )
#
#             y.append(yv)
#             material_ids.append(key)
#
#             meta = {
#                 "_key": key,
#                 temp_col_actual: T,
#                 "InvT": invT,
#                 target_col: yv,
#                 slope_col: slope_val,
#             }
#
#             for c in [
#                 "material_key",
#                 "original_material_index",
#                 "compound_name",
#                 "cas",
#                 "formula",
#                 "SMILES",
#                 "smiles",
#                 "final_smiles",
#                 "inchikey",
#                 "pubchem_inchikey",
#                 "pubchem_cid",
#                 "pubchem_cid_for_Tb",
#                 "boiling_T_K",
#                 "critical_T_K",
#                 "T_min",
#                 "T_max",
#                 "T_range",
#                 "RSQ_lnP_vs_invT",
#                 "slope_lnP_vs_invT",
#                 "RSQ_lnP_vs_T",
#             ]:
#                 if c in row.index:
#                     meta[c] = row[c]
#
#             row_meta.append(meta)
#
#
# X_no_slope = np.array(X_no_slope, dtype=float)
# X_with_slope = np.array(X_with_slope, dtype=float)
# y = np.array(y, dtype=float)
# material_ids = np.array(material_ids, dtype=str)
#
# df_meta = pd.DataFrame(row_meta)
#
# unique_materials = np.unique(material_ids)
#
# print("\n========== 建模数据统计 ==========")
# print("总样本点数:", len(y))
# print("有效物质数:", len(unique_materials))
# print("无 slope 特征维度:", X_no_slope.shape[1])
# print("有 slope 特征维度:", X_with_slope.shape[1])
#
# if len(y) == 0:
#     raise ValueError("没有有效样本点。")
#
# if len(unique_materials) < n_outer_folds:
#     raise ValueError(
#         f"有效物质数 {len(unique_materials)} 小于 n_outer_folds={n_outer_folds}。"
#     )
#
#
# # =========================================================
# # 8. 5折交叉验证，按物质划分
# # =========================================================
#
# kf = KFold(
#     n_splits=n_outer_folds,
#     shuffle=True,
#     random_state=random_state,
# )
#
# metrics_no_slope = []
# metrics_with_slope = []
#
# pred_rows_no_slope = []
# pred_rows_with_slope = []
#
# for fold, (train_idx, test_idx) in enumerate(kf.split(unique_materials), start=1):
#     print(f"\n========== Fold {fold}/{n_outer_folds} ==========")
#
#     train_mats = unique_materials[train_idx]
#     test_mats = unique_materials[test_idx]
#
#     train_mask = np.isin(material_ids, train_mats)
#     test_mask = np.isin(material_ids, test_mats)
#
#     print("训练物质数:", len(train_mats))
#     print("测试物质数:", len(test_mats))
#     print("训练点数:", int(train_mask.sum()))
#     print("测试点数:", int(test_mask.sum()))
#
#     # ----- 模型A：无 slope -----
#     X_train_A = X_no_slope[train_mask]
#     y_train_A = y[train_mask]
#
#     X_test_A = X_no_slope[test_mask]
#     y_test_A = y[test_mask]
#
#     valid_train_A = np.isfinite(X_train_A).all(axis=1) & np.isfinite(y_train_A)
#     valid_test_A = np.isfinite(X_test_A).all(axis=1) & np.isfinite(y_test_A)
#
#     X_train_A = X_train_A[valid_train_A]
#     y_train_A = y_train_A[valid_train_A]
#
#     X_test_A_valid = X_test_A[valid_test_A]
#     y_test_A_valid = y_test_A[valid_test_A]
#
#     model_A = RandomForestRegressor(**rf_params)
#     model_A.fit(X_train_A, y_train_A)
#
#     y_pred_A_valid = model_A.predict(X_test_A_valid)
#
#     y_pred_A = np.full(len(y_test_A), np.nan)
#     y_pred_A[valid_test_A] = y_pred_A_valid
#
#     # ----- 模型B：有 slope -----
#     X_train_B = X_with_slope[train_mask]
#     y_train_B = y[train_mask]
#
#     X_test_B = X_with_slope[test_mask]
#     y_test_B = y[test_mask]
#
#     valid_train_B = np.isfinite(X_train_B).all(axis=1) & np.isfinite(y_train_B)
#     valid_test_B = np.isfinite(X_test_B).all(axis=1) & np.isfinite(y_test_B)
#
#     X_train_B = X_train_B[valid_train_B]
#     y_train_B = y_train_B[valid_train_B]
#
#     X_test_B_valid = X_test_B[valid_test_B]
#     y_test_B_valid = y_test_B[valid_test_B]
#
#     model_B = RandomForestRegressor(**rf_params)
#     model_B.fit(X_train_B, y_train_B)
#
#     y_pred_B_valid = model_B.predict(X_test_B_valid)
#
#     y_pred_B = np.full(len(y_test_B), np.nan)
#     y_pred_B[valid_test_B] = y_pred_B_valid
#
#     # ----- 指标 -----
#     m_A = calc_metrics_vp(y_test_A, y_pred_A, target_is_log)
#     m_B = calc_metrics_vp(y_test_B, y_pred_B, target_is_log)
#
#     m_A["fold"] = fold
#     m_B["fold"] = fold
#
#     metrics_no_slope.append(m_A)
#     metrics_with_slope.append(m_B)
#
#     print(
#         "RF(desc+1/T)       | R2_lnP:",
#         f"{m_A['R2_lnP']:.10f}",
#         "MSE_lnP:",
#         f"{m_A['MSE_lnP']:.12f}",
#         "ARD_P%:",
#         f"{m_A['ARD_P_percent']:.10f}",
#     )
#
#     print(
#         "RF(desc+1/T+slope) | R2_lnP:",
#         f"{m_B['R2_lnP']:.10f}",
#         "MSE_lnP:",
#         f"{m_B['MSE_lnP']:.12f}",
#         "ARD_P%:",
#         f"{m_B['ARD_P_percent']:.10f}",
#     )
#
#     # ----- 保存预测明细 -----
#     df_test_meta = df_meta.loc[test_mask].reset_index(drop=True).copy()
#
#     pred_A = df_test_meta.copy()
#     pred_A["fold"] = fold
#     pred_A["model"] = "RF_desc_invT"
#     pred_A["y_true_target"] = y_test_A
#     pred_A["y_pred_target"] = y_pred_A
#
#     if target_is_log:
#         pred_A["lnP_true"] = y_test_A
#         pred_A["lnP_pred"] = y_pred_A
#         pred_A["P_true"] = safe_exp(y_test_A)
#         pred_A["P_pred"] = safe_exp(y_pred_A)
#     else:
#         pred_A["P_true"] = y_test_A
#         pred_A["P_pred"] = y_pred_A
#         pred_A["lnP_true"] = safe_log(y_test_A)
#         pred_A["lnP_pred"] = safe_log(y_pred_A)
#
#     pred_A["abs_error_P"] = np.abs(pred_A["P_pred"] - pred_A["P_true"])
#     pred_A["rel_error_P_percent"] = (
#         pred_A["abs_error_P"] / np.abs(pred_A["P_true"]) * 100.0
#     )
#
#     pred_B = df_test_meta.copy()
#     pred_B["fold"] = fold
#     pred_B["model"] = "RF_desc_invT_slope"
#     pred_B["y_true_target"] = y_test_B
#     pred_B["y_pred_target"] = y_pred_B
#
#     if target_is_log:
#         pred_B["lnP_true"] = y_test_B
#         pred_B["lnP_pred"] = y_pred_B
#         pred_B["P_true"] = safe_exp(y_test_B)
#         pred_B["P_pred"] = safe_exp(y_pred_B)
#     else:
#         pred_B["P_true"] = y_test_B
#         pred_B["P_pred"] = y_pred_B
#         pred_B["lnP_true"] = safe_log(y_test_B)
#         pred_B["lnP_pred"] = safe_log(y_pred_B)
#
#     pred_B["abs_error_P"] = np.abs(pred_B["P_pred"] - pred_B["P_true"])
#     pred_B["rel_error_P_percent"] = (
#         pred_B["abs_error_P"] / np.abs(pred_B["P_true"]) * 100.0
#     )
#
#     pred_rows_no_slope.append(pred_A)
#     pred_rows_with_slope.append(pred_B)
#
#
# # =========================================================
# # 9. 汇总统计
# # =========================================================
#
# df_A = pd.DataFrame(metrics_no_slope)
# df_B = pd.DataFrame(metrics_with_slope)
#
# # fold 放到第一列
# df_A = df_A[["fold"] + [c for c in df_A.columns if c != "fold"]]
# df_B = df_B[["fold"] + [c for c in df_B.columns if c != "fold"]]
#
# metric_names = [c for c in df_A.columns if c != "fold"]
#
# summary_A = summarize(df_A, "RF(desc + 1/T)")
# summary_B = summarize(df_B, "RF(desc + 1/T + slope)")
#
# summary_all = pd.concat(
#     [summary_A, summary_B],
#     ignore_index=True,
# )
#
# print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
# print(summary_all.to_string(index=False))
#
#
# # =========================================================
# # 10. 配对 t 检验
# # =========================================================
#
# t_test_results = []
#
# for metric in metric_names:
#     vals_A = pd.to_numeric(df_A[metric], errors="coerce").dropna().values
#     vals_B = pd.to_numeric(df_B[metric], errors="coerce").dropna().values
#
#     if len(vals_A) == len(vals_B) and len(vals_A) > 1:
#         if SCIPY_AVAILABLE:
#             t_stat, p_val = ttest_rel(vals_A, vals_B)
#         else:
#             t_stat, p_val = np.nan, np.nan
#
#         if metric.startswith("R2") or metric in ["leq1%", "leq5%", "leq10%"]:
#             better = "with_slope" if np.mean(vals_B) > np.mean(vals_A) else "no_slope"
#         else:
#             better = "with_slope" if np.mean(vals_B) < np.mean(vals_A) else "no_slope"
#
#         t_test_results.append({
#             "Metric": metric,
#             "Mean_no_slope": np.mean(vals_A),
#             "Mean_with_slope": np.mean(vals_B),
#             "Delta_with_minus_no": np.mean(vals_B) - np.mean(vals_A),
#             "t_stat": t_stat,
#             "p_value": p_val,
#             "Significant_p_lt_0.05": bool(p_val < 0.05) if np.isfinite(p_val) else False,
#             "Better_model": better,
#             "scipy_available": SCIPY_AVAILABLE,
#         })
#
# df_ttest = pd.DataFrame(t_test_results)
#
# print("\n========== Paired t-test ==========")
# print(df_ttest.to_string(index=False))
#
#
# # =========================================================
# # 11. 保存结果到 Excel
# # =========================================================
#
# df_pred_A = pd.concat(pred_rows_no_slope, ignore_index=True)
# df_pred_B = pd.concat(pred_rows_with_slope, ignore_index=True)
#
# df_used_features = pd.DataFrame({
#     "used_descriptor_feature": used_feature_cols,
# })
#
# run_info = pd.DataFrame([
#     {"param": "descriptor_file", "value": str(descriptor_file)},
#     {"param": "descriptor_sheet", "value": descriptor_sheet},
#     {"param": "selected_feature_sheet", "value": selected_feature_sheet},
#     {"param": "data_file", "value": str(data_file)},
#     {"param": "data_sheet", "value": data_sheet},
#     {"param": "slope_file_used", "value": str(slope_path_used)},
#     {"param": "slope_sheet_used", "value": slope_sheet_used},
#
#     {"param": "desc_key_col", "value": desc_key_col},
#     {"param": "data_key_col", "value": data_key_col},
#     {"param": "data_group_col", "value": data_group_col},
#     {"param": "slope_key_col", "value": slope_key_col},
#
#     {"param": "temp_col_actual", "value": temp_col_actual},
#     {"param": "target_col", "value": target_col},
#     {"param": "target_is_log", "value": target_is_log},
#     {"param": "slope_col", "value": slope_col},
#
#     {"param": "n_outer_folds", "value": n_outer_folds},
#     {"param": "random_state", "value": random_state},
#     {"param": "n_descriptor_features_original", "value": len(feature_cols)},
#     {"param": "n_descriptor_features_used", "value": len(used_feature_cols)},
#     {"param": "total_samples", "value": len(y)},
#     {"param": "n_materials", "value": len(unique_materials)},
#
#     {"param": "model_no_slope", "value": "RandomForestRegressor(desc + 1/T)"},
#     {"param": "model_with_slope", "value": "RandomForestRegressor(desc + 1/T + slope_pred_lnP_over_invT)"},
#     {"param": "rf_params", "value": str(rf_params)},
# ])
#
# with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
#     df_A.to_excel(writer, sheet_name="Fold_Metrics_No_Slope", index=False)
#     df_B.to_excel(writer, sheet_name="Fold_Metrics_With_Slope", index=False)
#
#     summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
#     df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)
#
#     df_pred_A.to_excel(writer, sheet_name="Predictions_No_Slope", index=False)
#     df_pred_B.to_excel(writer, sheet_name="Predictions_With_Slope", index=False)
#
#     df_used_features.to_excel(writer, sheet_name="Used_Descriptor_Features", index=False)
#     run_info.to_excel(writer, sheet_name="Run_Info", index=False)
#
#     workbook = writer.book
#     number_format = "0.000000000000"
#
#     for sheetname in writer.sheets:
#         ws = workbook[sheetname]
#
#         for row in ws.iter_rows():
#             for cell in row:
#                 if isinstance(cell.value, float):
#                     cell.number_format = number_format
#
#         for col in ws.columns:
#             max_len = 0
#             col_letter = col[0].column_letter
#
#             for cell in col:
#                 if cell.value is not None:
#                     max_len = max(max_len, len(str(cell.value)))
#
#             ws.column_dimensions[col_letter].width = min(max_len + 2, 45)
#
# print(f"\n保存完成: {output_file}")
# print("主要输出 sheet:")
# print("- Fold_Metrics_No_Slope")
# print("- Fold_Metrics_With_Slope")
# print("- Summary_Mean_Std")
# print("- Paired_T_Test")
# print("- Predictions_No_Slope")
# print("- Predictions_With_Slope")
# print("- Used_Descriptor_Features")
# print("- Run_Info")



# -*- coding: utf-8 -*-
"""
Vapor pressure:
QSPR 25 descriptors + 1/T vs QSPR 25 descriptors + 1/T + slope
Random Forest 5-fold CV comparison

新增：
1. 每个 fold 训练出的模型额外预测完整数据集；
2. 在 P=exp(lnP) 空间统计完整数据集相对误差 <1%、<5%、<10% 的点数；
3. 对 5 个 fold 的完整数据集偏差数量取平均；
4. 保留原有 5-fold 测试集评价、P/lnP 双空间指标、t 检验、预测明细和 Excel 保存；
5. 增加 fold_all_data_predictions、fold_all_data_count_summary、final_average_summary、model_structure 等 sheet。
"""

import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

try:
    from scipy.stats import ttest_rel
    SCIPY_AVAILABLE = True
except Exception:
    SCIPY_AVAILABLE = False


pd.set_option("display.float_format", "{:.10f}".format)
np.set_printoptions(suppress=True, precision=10)


# =========================================================
# 0. 全局设置
# =========================================================
descriptor_file = Path("selected_descriptors_with_vp_mean_target.xlsx")
descriptor_sheet = "Selected_Features_Target"
selected_feature_sheet = "Selected_Features"

data_file = Path("dataset_selected_by_two_k_with_lnP_invT_interpolation_8points.xlsx")
data_sheet = "Data_selected"

# slope 文件候选。如果真实文件名不同，在这里加进去即可。
slope_file_candidates = [
    Path("HistGB_submodels_predict_ref_lnP_Tb_and_slope.xlsx"),
    Path("HistGB_submodels_predict_ref_lnP_Tb_and_slope.xls"),
    Path("HistGB_submodels_predict_ref_vp_Tb_and_slope.xlsx"),
    Path("HistGB_submodels_predict_ref_vp_Tb_and_slope.xls"),
    Path("HistGB_submodels_predict_ref_lnP_invT_Tb_and_slope.xlsx"),
    Path("HistGB_submodels_predict_ref_lnP_invT_Tb_and_slope.xls"),
]

slope_sheet_candidates = [
    "slope",
    "Slope",
    "Predicted_Slope",
]

slope_col_candidates = [
    "slope_pred_lnP_over_invT",
    "slope_pred_lnp_over_invT",
    "slope_pred_lnP_over_InvT",
    "slope_pred_lnP_over_inverse_T",
    "slope_pred_vp_over_invT",
    "slope_pred_P_over_invT",
    "slope_true_ref_lnP_over_invT",
]

output_file = Path("RF_vp_QSPR25_5fold_CV_comparison_with_slope.xlsx")

material_key_col = "material_key"
temp_col = "T_K"

# 目标列候选：优先 lnP
target_candidates = [
    "lnP_kPa",
    "lnP",
    "ln_P",
    "lnP_value",
    "ln_pressure",
    "ln_VaporPressure_kPa",
    "lnVaporPressure",
    "ln vapor pressure",
    "ln(P)",
    "ln_P_kPa",
    "property_value",
    "VaporPressure_kPa",
    "vapor_pressure_kPa",
    "Vapor_Pressure_kPa",
    "P_vapor_kPa",
    "P_kPa",
    "P",
    "pressure",
    "Pressure",
]

n_outer_folds = 5
random_state = 42

# Random Forest 参数，与原始代码一致
rf_params = {
    "n_estimators": 500,
    "max_depth": None,
    "min_samples_split": 2,
    "min_samples_leaf": 1,
    "max_features": "sqrt",
    "bootstrap": True,
    "random_state": random_state,
    "n_jobs": -1,
}


# =========================================================
# 1. 辅助函数
# =========================================================
def normalize_colname(name):
    return (
        str(name)
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "")
        .replace(".", "")
        .replace(",", "")
    )


def find_first_existing_col(df, candidates, required=True, col_type="列"):
    norm_map = {normalize_colname(c): c for c in df.columns}

    for c in candidates:
        key = normalize_colname(c)
        if key in norm_map:
            return norm_map[key]

    if required:
        raise ValueError(
            f"没有找到 {col_type}。\n"
            f"候选列名: {candidates}\n"
            f"当前列名: {list(df.columns)}"
        )

    return None


def is_valid_value(x):
    if pd.isna(x):
        return False

    s = str(x).strip()

    if s == "":
        return False

    if s.lower() in ["nan", "none", "null", "待定"]:
        return False

    return True


def clean_key_value(x):
    """
    清理物质 ID：
        123.0 -> '123'
        其他字符串保留。
    """
    if not is_valid_value(x):
        return np.nan

    s = str(x).strip()

    try:
        f = float(s)

        if np.isfinite(f) and abs(f - round(f)) < 1e-8:
            return str(int(round(f)))

    except Exception:
        pass

    return s


def safe_exp(x):
    x = np.asarray(x, dtype=float)
    return np.exp(np.clip(x, -700, 700))


def safe_log(x):
    x = np.asarray(x, dtype=float)
    out = np.full_like(x, np.nan, dtype=float)

    mask = np.isfinite(x) & (x > 0)
    out[mask] = np.log(x[mask])

    return out


def safe_relative_error_percent(y_true, y_pred, eps=1e-12):
    """
    relative_error = abs((y_pred - y_true) / y_true) * 100

    对 abs(y_true) <= 1e-12 的点，relative_error 记为 NaN。
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    rel_err = np.full_like(y_true, np.nan, dtype=float)

    mask = (
        np.isfinite(y_true)
        & np.isfinite(y_pred)
        & (np.abs(y_true) > eps)
    )

    rel_err[mask] = np.abs((y_pred[mask] - y_true[mask]) / y_true[mask]) * 100.0

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


def infer_target_is_log(target_col):
    col_norm = normalize_colname(target_col)

    if "ln" in col_norm or "log" in col_norm:
        return True

    # 对当前数据，property_value 通常是 lnP
    if col_norm == "propertyvalue":
        return True

    return False


def find_alignment_key(df_desc, df_data):
    """
    描述符表与 Data_selected 的对齐键。
    """
    candidate_pairs = [
        ("material_key", "material_key"),
        ("original_material_index", "original_material_index"),

        ("pubchem_cid", "pubchem_cid"),
        ("pubchem_cid_for_Tb", "pubchem_cid_for_Tb"),
        ("CID", "pubchem_cid"),
        ("CID_int", "pubchem_cid"),
        ("sdf_pubchem_cid", "pubchem_cid"),

        ("inchikey", "inchikey"),
        ("InChIKey", "InChIKey"),
        ("pubchem_inchikey", "pubchem_inchikey"),
        ("inchikey_from_rdkit", "inchikey"),

        ("cas", "cas"),
        ("compound_name", "compound_name"),
    ]

    for dcol, dacol in candidate_pairs:
        if dcol in df_desc.columns and dacol in df_data.columns:
            return dcol, dacol

    return None, None


def choose_data_group_key(df_data):
    for col in [
        "material_key",
        "original_material_index",
        "pubchem_cid",
        "pubchem_cid_for_Tb",
        "CID",
        "CID_int",
        "inchikey",
        "InChIKey",
        "pubchem_inchikey",
        "cas",
        "compound_name",
    ]:
        if col in df_data.columns:
            return col

    return None


def find_slope_key(df_slope, preferred_data_key_col):
    if preferred_data_key_col is not None and preferred_data_key_col in df_slope.columns:
        return preferred_data_key_col

    for col in [
        "material_key",
        "original_material_index",
        "pubchem_cid",
        "pubchem_cid_for_Tb",
        "CID",
        "CID_int",
        "sdf_pubchem_cid",
        "inchikey",
        "InChIKey",
        "pubchem_inchikey",
        "cas",
        "compound_name",
    ]:
        if col in df_slope.columns:
            return col

    return None


def read_slope_file(slope_paths, sheet_candidates):
    """
    从候选 slope 文件中读取第一个存在的文件。
    """
    slope_path_used = None

    for p in slope_paths:
        if p.exists():
            slope_path_used = p
            break

    if slope_path_used is None:
        msg = "没有找到 slope 文件，已尝试以下路径：\n"
        msg += "\n".join([str(p) for p in slope_paths])
        raise FileNotFoundError(msg)

    xls = pd.ExcelFile(slope_path_used)

    sheet = None
    for s in sheet_candidates:
        if s in xls.sheet_names:
            sheet = s
            break

    if sheet is None:
        sheet = xls.sheet_names[0]

    df = pd.read_excel(slope_path_used, sheet_name=sheet)

    return df, slope_path_used, sheet


def calc_metrics_vp(y_true, y_pred, target_is_log):
    """
    计算 vapor pressure 指标。

    如果 target_is_log=True：
        y_true/y_pred 是 lnP
        同时输出 lnP 空间指标和 P 空间指标。

    如果 target_is_log=False：
        y_true/y_pred 是 P
        同时输出 P 空间指标和 lnP 空间指标。

    误差区间 leq1/leq5/leq10 保留原代码含义：P 空间 <= 阈值比例。
    新增最终复制输出另行使用严格 < 阈值的数量。
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true = y_true[mask]
    y_pred = y_pred[mask]

    if len(y_true) == 0:
        return {
            "R2_lnP": np.nan,
            "MSE_lnP": np.nan,
            "RMSE_lnP": np.nan,
            "MAE_lnP": np.nan,
            "ARD_lnP_percent": np.nan,

            "R2_P": np.nan,
            "MSE_P": np.nan,
            "RMSE_P": np.nan,
            "MAE_P": np.nan,
            "ARD_P_percent": np.nan,

            "leq1%": np.nan,
            "leq5%": np.nan,
            "leq10%": np.nan,
            "max_rel%": np.nan,
        }

    if target_is_log:
        ln_true = y_true
        ln_pred = y_pred

        P_true = safe_exp(y_true)
        P_pred = safe_exp(y_pred)

    else:
        P_true = y_true
        P_pred = y_pred

        ln_true = safe_log(y_true)
        ln_pred = safe_log(y_pred)

    # ---------- lnP 空间 ----------
    ln_mask = np.isfinite(ln_true) & np.isfinite(ln_pred)

    if ln_mask.sum() >= 2:
        R2_lnP = r2_score(ln_true[ln_mask], ln_pred[ln_mask])
        MSE_lnP = mean_squared_error(ln_true[ln_mask], ln_pred[ln_mask])
        RMSE_lnP = np.sqrt(MSE_lnP)
        MAE_lnP = mean_absolute_error(ln_true[ln_mask], ln_pred[ln_mask])

        rel_ln = safe_relative_error_percent(ln_true[ln_mask], ln_pred[ln_mask])
        ARD_lnP = np.nanmean(rel_ln) if np.any(np.isfinite(rel_ln)) else np.nan
    else:
        R2_lnP = np.nan
        MSE_lnP = np.nan
        RMSE_lnP = np.nan
        MAE_lnP = np.nan
        ARD_lnP = np.nan

    # ---------- P 空间 ----------
    P_mask = np.isfinite(P_true) & np.isfinite(P_pred)

    if P_mask.sum() >= 2:
        R2_P = r2_score(P_true[P_mask], P_pred[P_mask])
        MSE_P = mean_squared_error(P_true[P_mask], P_pred[P_mask])
        RMSE_P = np.sqrt(MSE_P)
        MAE_P = mean_absolute_error(P_true[P_mask], P_pred[P_mask])

        rel_err = safe_relative_error_percent(P_true[P_mask], P_pred[P_mask])

        if np.any(np.isfinite(rel_err)):
            ARD_P = np.nanmean(rel_err)
            le1 = np.nanmean(rel_err <= 1.0) * 100.0
            le5 = np.nanmean(rel_err <= 5.0) * 100.0
            le10 = np.nanmean(rel_err <= 10.0) * 100.0
            max_rel = np.nanmax(rel_err)
        else:
            ARD_P = np.nan
            le1 = np.nan
            le5 = np.nan
            le10 = np.nan
            max_rel = np.nan
    else:
        R2_P = np.nan
        MSE_P = np.nan
        RMSE_P = np.nan
        MAE_P = np.nan
        ARD_P = np.nan
        le1 = np.nan
        le5 = np.nan
        le10 = np.nan
        max_rel = np.nan

    return {
        "R2_lnP": R2_lnP,
        "MSE_lnP": MSE_lnP,
        "RMSE_lnP": RMSE_lnP,
        "MAE_lnP": MAE_lnP,
        "ARD_lnP_percent": ARD_lnP,

        "R2_P": R2_P,
        "MSE_P": MSE_P,
        "RMSE_P": RMSE_P,
        "MAE_P": MAE_P,
        "ARD_P_percent": ARD_P,

        "leq1%": le1,
        "leq5%": le5,
        "leq10%": le10,
        "max_rel%": max_rel,
    }


def format_metric_value(metric, value):
    if pd.isna(value):
        return "NaN"

    if metric in ["MSE_lnP", "MSE_P"]:
        return f"{value:.12f}"

    if metric in ["RMSE_lnP", "RMSE_P", "MAE_lnP", "MAE_P"]:
        return f"{value:.10f}"

    return f"{value:.6f}"


def summarize(df, name):
    metric_names = [c for c in df.columns if c != "fold"]
    rows = []

    for metric in metric_names:
        vals = pd.to_numeric(df[metric], errors="coerce").dropna().values

        if len(vals) == 0:
            mean_val = np.nan
            std_val = np.nan
            mean_std = "NaN"

        elif len(vals) == 1:
            mean_val = float(np.mean(vals))
            std_val = np.nan
            mean_std = f"{format_metric_value(metric, mean_val)} ± NaN"

        else:
            mean_val = float(np.mean(vals))
            std_val = float(np.std(vals, ddof=1))
            mean_std = (
                f"{format_metric_value(metric, mean_val)} ± "
                f"{format_metric_value(metric, std_val)}"
            )

        rows.append({
            "Model": name,
            "Metric": metric,
            "Mean": mean_val,
            "Std": std_val,
            "Mean±Std": mean_std,
        })

    return pd.DataFrame(rows)


def make_prediction_df(fold, dataset_name, model_name, meta_df, y_true, y_pred, target_is_log):
    """
    保存测试集或完整数据集预测明细。
    """
    out = meta_df.copy().reset_index(drop=True)

    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    out["fold"] = fold
    out["dataset"] = dataset_name
    out["model"] = model_name
    out["y_true_target"] = y_true
    out["y_pred_target"] = y_pred

    if target_is_log:
        out["lnP_true"] = y_true
        out["lnP_pred"] = y_pred
        out["P_true"] = safe_exp(y_true)
        out["P_pred"] = safe_exp(y_pred)
    else:
        out["P_true"] = y_true
        out["P_pred"] = y_pred
        out["lnP_true"] = safe_log(y_true)
        out["lnP_pred"] = safe_log(y_pred)

    out["abs_error_P"] = np.abs(out["P_pred"] - out["P_true"])
    out["rel_error_P_percent"] = safe_relative_error_percent(out["P_true"], out["P_pred"])

    out["abs_error_lnP"] = np.abs(out["lnP_pred"] - out["lnP_true"])
    out["rel_error_lnP_percent"] = safe_relative_error_percent(out["lnP_true"], out["lnP_pred"])

    return out


def get_P_values_from_target(y_values, target_is_log):
    y_values = np.asarray(y_values, dtype=float)
    if target_is_log:
        return safe_exp(y_values)
    return y_values


def format_excel(writer, number_format="0.000000000000"):
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
# 2. 读取数据
# =========================================================
if not descriptor_file.exists():
    raise FileNotFoundError(
        f"没有找到描述符文件: {descriptor_file}\n"
        "请先运行 vapor pressure 的 25 个描述符筛选代码。"
    )

if not data_file.exists():
    raise FileNotFoundError(f"没有找到 vapor pressure 数据文件: {data_file}")

df_desc = pd.read_excel(descriptor_file, sheet_name=descriptor_sheet)
df_data = pd.read_excel(data_file, sheet_name=data_sheet)

df_slope, slope_path_used, slope_sheet_used = read_slope_file(
    slope_file_candidates,
    slope_sheet_candidates,
)

print("描述符表行数:", len(df_desc))
print("原始数据行数:", len(df_data))
print("Slope 表行数:", len(df_slope))
print("Slope 文件:", slope_path_used)
print("Slope sheet:", slope_sheet_used)


# =========================================================
# 3. 确定物质 ID 列
# =========================================================
desc_key_col, data_key_col = find_alignment_key(df_desc, df_data)
data_group_col = choose_data_group_key(df_data)
slope_key_col = find_slope_key(df_slope, data_key_col)

print("\n物质对齐方式:")
print("  desc_key_col:", desc_key_col)
print("  data_key_col:", data_key_col)
print("  data_group_col:", data_group_col)
print("  slope_key_col:", slope_key_col)

if slope_key_col is None:
    raise ValueError("无法在 slope 表中找到物质 ID 列。")


# =========================================================
# 4. 读取 25 个描述符列表
# =========================================================
xls_desc = pd.ExcelFile(descriptor_file)

if selected_feature_sheet in xls_desc.sheet_names:
    df_selected = pd.read_excel(descriptor_file, sheet_name=selected_feature_sheet)

    if "selected_feature" in df_selected.columns:
        feature_cols = df_selected["selected_feature"].dropna().astype(str).tolist()
    else:
        feature_cols = df_selected.iloc[:, 0].dropna().astype(str).tolist()

else:
    meta = [
        "material_index",
        "original_material_index",
        "material_key",
        "compound_name",
        "cas",
        "formula",
        "SMILES",
        "smiles",
        "final_smiles",
        "inchikey",
        "InChIKey",
        "pubchem_inchikey",
        "pubchem_cid",
        "pubchem_cid_for_Tb",
        "CID",
        "CID_int",
        "phase",
        "boiling_T_K",
        "critical_T_K",
        "T_min",
        "T_max",
        "T_range",
        "n_points",
        "target_n_valid_points",
        "target_min_vp",
        "target_max_vp",
        "target_mean_vp",
    ]

    feature_cols = [c for c in df_desc.columns if c not in meta]

missing_features = [c for c in feature_cols if c not in df_desc.columns]

if len(missing_features) > 0:
    raise ValueError(
        "以下选中描述符不在描述符表中：\n"
        f"{missing_features}"
    )

print("\n原始选中描述符数量:", len(feature_cols))


# =========================================================
# 5. 数值化描述符，删除无效列
# =========================================================
df_feature_raw = df_desc[feature_cols].copy()

df_features = df_feature_raw.apply(
    pd.to_numeric,
    errors="coerce",
)

df_features = df_features.replace([np.inf, -np.inf], np.nan)

# 均值填充
df_features = df_features.fillna(df_features.mean())

# 如果仍有 NaN，删除该列
df_features = df_features.dropna(axis=1, how="any")

# 删除全零列
nonzero = df_features.abs().sum(axis=0) != 0

used_feature_cols = df_features.columns[nonzero].tolist()
removed_zero_feature_cols = df_features.columns[~nonzero].tolist()

print("有效描述符数量:", len(used_feature_cols))
print("删除全零描述符数量:", len(removed_zero_feature_cols))

if len(used_feature_cols) == 0:
    raise ValueError("没有有效描述符可用于建模。")


# =========================================================
# 6. 找到温度列、目标列、斜率列
# =========================================================
temp_col_actual = find_first_existing_col(
    df_data,
    [temp_col, "T_K", "Temperature", "temperature"],
    required=True,
    col_type="温度列",
)

target_col = find_first_existing_col(
    df_data,
    target_candidates,
    required=True,
    col_type="vapor pressure 目标列",
)

slope_col = find_first_existing_col(
    df_slope,
    slope_col_candidates,
    required=True,
    col_type="斜率列",
)

target_is_log = infer_target_is_log(target_col)

print("\n温度列:", temp_col_actual)
print("目标列:", target_col)
print("目标是否为 lnP:", target_is_log)
print("斜率列:", slope_col)

df_data[temp_col_actual] = pd.to_numeric(df_data[temp_col_actual], errors="coerce")
df_data[target_col] = pd.to_numeric(df_data[target_col], errors="coerce")
df_slope[slope_col] = pd.to_numeric(df_slope[slope_col], errors="coerce")


# =========================================================
# 7. 合并数据，构造按物质展开的特征矩阵
# =========================================================
X_no_slope = []
X_with_slope = []
y = []
material_ids = []
row_meta = []

# ---------- 7.1 优先使用公共 ID 对齐 ----------
if desc_key_col is not None and data_key_col is not None:
    df_desc_work = df_desc.copy()
    df_data_work = df_data.copy()
    df_slope_work = df_slope.copy()

    df_desc_work["_key"] = df_desc_work[desc_key_col].apply(clean_key_value)
    df_data_work["_key"] = df_data_work[data_key_col].apply(clean_key_value)
    df_slope_work["_key"] = df_slope_work[slope_key_col].apply(clean_key_value)

    df_desc_work = df_desc_work.dropna(subset=["_key"]).copy()
    df_data_work = df_data_work.dropna(subset=["_key"]).copy()
    df_slope_work = df_slope_work.dropna(subset=["_key"]).copy()

    df_desc_work = df_desc_work.drop_duplicates(subset=["_key"], keep="first")
    df_slope_work = df_slope_work.drop_duplicates("_key", keep="first")

    # 同步描述符数值列
    df_desc_work[used_feature_cols] = df_features.loc[
        df_desc_work.index,
        used_feature_cols
    ].values

    desc_map = {
        row["_key"]: row[used_feature_cols].values.astype(float)
        for _, row in df_desc_work.iterrows()
    }

    slope_map = (
        df_slope_work
        .set_index("_key")[slope_col]
        .to_dict()
    )

    data_keys_in_order = df_data_work["_key"].drop_duplicates().tolist()

    valid_keys = [
        k for k in data_keys_in_order
        if k in desc_map
        and k in slope_map
        and np.isfinite(slope_map[k])
    ]

    if len(valid_keys) == 0:
        raise ValueError("没有同时拥有描述符、数据点和有效 slope 的物质。")

    print("\n同时拥有描述符、数据点和 slope 的物质数:", len(valid_keys))

    for key in valid_keys:
        desc = np.asarray(desc_map[key], dtype=float)
        slope_val = float(slope_map[key])

        sub = df_data_work[df_data_work["_key"] == key].copy()

        for _, row in sub.iterrows():
            T = row[temp_col_actual]
            yv = row[target_col]

            if not (
                np.isfinite(T)
                and np.isfinite(yv)
                and abs(T) > 1e-12
            ):
                continue

            invT = 1.0 / T

            X_no_slope.append(np.concatenate([desc, [invT]]))
            X_with_slope.append(np.concatenate([desc, [invT, slope_val]]))

            y.append(yv)
            material_ids.append(key)

            meta = {
                "_key": key,
                temp_col_actual: T,
                "InvT": invT,
                target_col: yv,
                slope_col: slope_val,
            }

            for c in [
                "material_key",
                "original_material_index",
                "compound_name",
                "cas",
                "formula",
                "SMILES",
                "smiles",
                "final_smiles",
                "inchikey",
                "pubchem_inchikey",
                "pubchem_cid",
                "pubchem_cid_for_Tb",
                "boiling_T_K",
                "critical_T_K",
                "T_min",
                "T_max",
                "T_range",
                "RSQ_lnP_vs_invT",
                "slope_lnP_vs_invT",
                "RSQ_lnP_vs_T",
            ]:
                if c in row.index:
                    meta[c] = row[c]

            row_meta.append(meta)

# ---------- 7.2 备用：按物质顺序对齐 ----------
else:
    print("\n没有找到可用于描述符和数据对齐的共同 ID，尝试按物质顺序对齐。")

    if data_group_col is None:
        raise ValueError("无法确定 Data_selected 中的物质分组列。")

    df_data_work = df_data.copy()
    df_slope_work = df_slope.copy()

    df_data_work["_group"] = df_data_work[data_group_col].apply(clean_key_value)
    groups = df_data_work["_group"].drop_duplicates().tolist()

    if len(groups) != len(df_features):
        raise ValueError(
            "物质分组数量与描述符行数不一致，无法按顺序对齐。\n"
            f"Data 物质数 = {len(groups)}\n"
            f"描述符行数 = {len(df_features)}"
        )

    df_slope_work["_key"] = df_slope_work[slope_key_col].apply(clean_key_value)
    df_slope_work = df_slope_work.dropna(subset=["_key"]).drop_duplicates("_key")

    slope_map = df_slope_work.set_index("_key")[slope_col].to_dict()

    for i, key in enumerate(groups):
        if key not in slope_map or not np.isfinite(slope_map[key]):
            continue

        desc = df_features.iloc[i][used_feature_cols].values.astype(float)
        slope_val = float(slope_map[key])

        sub = df_data_work[df_data_work["_group"] == key]

        for _, row in sub.iterrows():
            T = row[temp_col_actual]
            yv = row[target_col]

            if not (
                np.isfinite(T)
                and np.isfinite(yv)
                and abs(T) > 1e-12
            ):
                continue

            invT = 1.0 / T

            X_no_slope.append(np.concatenate([desc, [invT]]))
            X_with_slope.append(np.concatenate([desc, [invT, slope_val]]))

            y.append(yv)
            material_ids.append(key)

            meta = {
                "_key": key,
                temp_col_actual: T,
                "InvT": invT,
                target_col: yv,
                slope_col: slope_val,
            }

            for c in [
                "material_key",
                "original_material_index",
                "compound_name",
                "cas",
                "formula",
                "SMILES",
                "smiles",
                "final_smiles",
                "inchikey",
                "pubchem_inchikey",
                "pubchem_cid",
                "pubchem_cid_for_Tb",
                "boiling_T_K",
                "critical_T_K",
                "T_min",
                "T_max",
                "T_range",
                "RSQ_lnP_vs_invT",
                "slope_lnP_vs_invT",
                "RSQ_lnP_vs_T",
            ]:
                if c in row.index:
                    meta[c] = row[c]

            row_meta.append(meta)


X_no_slope = np.array(X_no_slope, dtype=float)
X_with_slope = np.array(X_with_slope, dtype=float)
y = np.array(y, dtype=float)
material_ids = np.array(material_ids, dtype=str)

df_meta = pd.DataFrame(row_meta)

unique_materials = np.unique(material_ids)

print("\n========== 建模数据统计 ==========")
print("总样本点数:", len(y))
print("有效物质数:", len(unique_materials))
print("无 slope 特征维度:", X_no_slope.shape[1])
print("有 slope 特征维度:", X_with_slope.shape[1])

if len(y) == 0:
    raise ValueError("没有有效样本点。")

if len(unique_materials) < n_outer_folds:
    raise ValueError(
        f"有效物质数 {len(unique_materials)} 小于 n_outer_folds={n_outer_folds}。"
    )

# 完整数据集 P 空间真值
P_all_true = get_P_values_from_target(y, target_is_log)

all_sample_indices = np.arange(len(y))


# =========================================================
# 8. 5折交叉验证，按物质划分
# =========================================================
kf = KFold(
    n_splits=n_outer_folds,
    shuffle=True,
    random_state=random_state,
)

metrics_no_slope = []
metrics_with_slope = []

pred_rows_no_slope = []
pred_rows_with_slope = []

fold_test_prediction_dfs = []
fold_all_data_prediction_dfs = []
fold_all_data_count_records = []
fold_info_records = []

feature_importance_no_records = []
feature_importance_with_records = []

for fold, (train_idx, test_idx) in enumerate(kf.split(unique_materials), start=1):
    print(f"\n========== Fold {fold}/{n_outer_folds} ==========")

    train_mats = unique_materials[train_idx]
    test_mats = unique_materials[test_idx]

    train_mask = np.isin(material_ids, train_mats)
    test_mask = np.isin(material_ids, test_mats)

    print("训练物质数:", len(train_mats))
    print("测试物质数:", len(test_mats))
    print("训练点数:", int(train_mask.sum()))
    print("测试点数:", int(test_mask.sum()))

    # ----- 模型A：无 slope -----
    X_train_A = X_no_slope[train_mask]
    y_train_A = y[train_mask]

    X_test_A = X_no_slope[test_mask]
    y_test_A = y[test_mask]

    valid_train_A = np.isfinite(X_train_A).all(axis=1) & np.isfinite(y_train_A)
    valid_test_A = np.isfinite(X_test_A).all(axis=1) & np.isfinite(y_test_A)

    X_train_A = X_train_A[valid_train_A]
    y_train_A = y_train_A[valid_train_A]

    X_test_A_valid = X_test_A[valid_test_A]
    y_test_A_valid = y_test_A[valid_test_A]

    model_A = RandomForestRegressor(**rf_params)
    model_A.fit(X_train_A, y_train_A)

    y_pred_A_valid = model_A.predict(X_test_A_valid)

    y_pred_A = np.full(len(y_test_A), np.nan, dtype=float)
    y_pred_A[valid_test_A] = y_pred_A_valid

    # 完整数据集预测
    valid_all_A = np.isfinite(X_no_slope).all(axis=1)
    y_pred_A_all = np.full(len(y), np.nan, dtype=float)
    y_pred_A_all[valid_all_A] = model_A.predict(X_no_slope[valid_all_A])

    # ----- 模型B：有 slope -----
    X_train_B = X_with_slope[train_mask]
    y_train_B = y[train_mask]

    X_test_B = X_with_slope[test_mask]
    y_test_B = y[test_mask]

    valid_train_B = np.isfinite(X_train_B).all(axis=1) & np.isfinite(y_train_B)
    valid_test_B = np.isfinite(X_test_B).all(axis=1) & np.isfinite(y_test_B)

    X_train_B = X_train_B[valid_train_B]
    y_train_B = y_train_B[valid_train_B]

    X_test_B_valid = X_test_B[valid_test_B]
    y_test_B_valid = y_test_B[valid_test_B]

    model_B = RandomForestRegressor(**rf_params)
    model_B.fit(X_train_B, y_train_B)

    y_pred_B_valid = model_B.predict(X_test_B_valid)

    y_pred_B = np.full(len(y_test_B), np.nan, dtype=float)
    y_pred_B[valid_test_B] = y_pred_B_valid

    # 完整数据集预测
    valid_all_B = np.isfinite(X_with_slope).all(axis=1)
    y_pred_B_all = np.full(len(y), np.nan, dtype=float)
    y_pred_B_all[valid_all_B] = model_B.predict(X_with_slope[valid_all_B])

    # ----- 测试集指标 -----
    m_A = calc_metrics_vp(y_test_A, y_pred_A, target_is_log)
    m_B = calc_metrics_vp(y_test_B, y_pred_B, target_is_log)

    m_A["fold"] = fold
    m_B["fold"] = fold

    metrics_no_slope.append(m_A)
    metrics_with_slope.append(m_B)

    print(
        "RF(desc+1/T)       | R2_lnP:",
        f"{m_A['R2_lnP']:.10f}",
        "MSE_lnP:",
        f"{m_A['MSE_lnP']:.12f}",
        "ARD_P%:",
        f"{m_A['ARD_P_percent']:.10f}",
    )

    print(
        "RF(desc+1/T+slope) | R2_lnP:",
        f"{m_B['R2_lnP']:.10f}",
        "MSE_lnP:",
        f"{m_B['MSE_lnP']:.12f}",
        "ARD_P%:",
        f"{m_B['ARD_P_percent']:.10f}",
    )

    # =====================================================
    # 新增：每个 fold 模型预测完整数据集，统计 P 空间三档偏差数量
    # =====================================================
    P_pred_A_all = get_P_values_from_target(y_pred_A_all, target_is_log)
    P_pred_B_all = get_P_values_from_target(y_pred_B_all, target_is_log)

    count_A_all_P = count_error_thresholds(P_all_true, P_pred_A_all)
    count_B_all_P = count_error_thresholds(P_all_true, P_pred_B_all)

    # 同时保存 lnP 空间计数，最终复制输出仍使用 P 空间
    if target_is_log:
        lnP_true_all = y
        lnP_pred_A_all = y_pred_A_all
        lnP_pred_B_all = y_pred_B_all
    else:
        lnP_true_all = safe_log(y)
        lnP_pred_A_all = safe_log(y_pred_A_all)
        lnP_pred_B_all = safe_log(y_pred_B_all)

    count_A_all_lnP = count_error_thresholds(lnP_true_all, lnP_pred_A_all)
    count_B_all_lnP = count_error_thresholds(lnP_true_all, lnP_pred_B_all)

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "RF_desc_invT",
        "count_space": "P",
        **count_A_all_P,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "RF_desc_invT_slope",
        "count_space": "P",
        **count_B_all_P,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "RF_desc_invT",
        "count_space": "lnP",
        **count_A_all_lnP,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "RF_desc_invT_slope",
        "count_space": "lnP",
        **count_B_all_lnP,
    })

    print("\nRF(desc+1/T) fold model predicts ALL data count summary in P space:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "RF_desc_invT",
        "count_space": "P",
        **count_A_all_P,
    }]).to_string(index=False))

    print("\nRF(desc+1/T+slope) fold model predicts ALL data count summary in P space:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "RF_desc_invT_slope",
        "count_space": "P",
        **count_B_all_P,
    }]).to_string(index=False))

    # ----- 保存测试集预测明细：保留原逻辑 -----
    df_test_meta = df_meta.loc[test_mask].reset_index(drop=True).copy()

    pred_A = make_prediction_df(
        fold=fold,
        dataset_name="test",
        model_name="RF_desc_invT",
        meta_df=df_test_meta,
        y_true=y_test_A,
        y_pred=y_pred_A,
        target_is_log=target_is_log,
    )

    pred_B = make_prediction_df(
        fold=fold,
        dataset_name="test",
        model_name="RF_desc_invT_slope",
        meta_df=df_test_meta,
        y_true=y_test_B,
        y_pred=y_pred_B,
        target_is_log=target_is_log,
    )

    pred_rows_no_slope.append(pred_A)
    pred_rows_with_slope.append(pred_B)

    fold_test_prediction_dfs.append(pred_A)
    fold_test_prediction_dfs.append(pred_B)

    # ----- 新增：保存完整数据集预测明细 -----
    df_all_meta = df_meta.reset_index(drop=True).copy()

    all_pred_A = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        model_name="RF_desc_invT",
        meta_df=df_all_meta,
        y_true=y,
        y_pred=y_pred_A_all,
        target_is_log=target_is_log,
    )

    all_pred_B = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        model_name="RF_desc_invT_slope",
        meta_df=df_all_meta,
        y_true=y,
        y_pred=y_pred_B_all,
        target_is_log=target_is_log,
    )

    fold_all_data_prediction_dfs.append(all_pred_A)
    fold_all_data_prediction_dfs.append(all_pred_B)

    # ----- 特征重要性 -----
    feature_names_no = used_feature_cols + ["InvT"]
    feature_names_with = used_feature_cols + ["InvT", slope_col]

    if hasattr(model_A, "feature_importances_"):
        for fname, imp in zip(feature_names_no, model_A.feature_importances_):
            feature_importance_no_records.append({
                "fold": fold,
                "feature": fname,
                "importance": imp,
            })

    if hasattr(model_B, "feature_importances_"):
        for fname, imp in zip(feature_names_with, model_B.feature_importances_):
            feature_importance_with_records.append({
                "fold": fold,
                "feature": fname,
                "importance": imp,
            })

    fold_info_records.append({
        "fold": fold,
        "n_train_materials": len(train_mats),
        "n_test_materials": len(test_mats),
        "n_train_points": int(train_mask.sum()),
        "n_test_points": int(test_mask.sum()),
        "n_all_points": len(y),
        "n_features_no_slope": X_no_slope.shape[1],
        "n_features_with_slope": X_with_slope.shape[1],
        "n_train_valid_no_slope": int(valid_train_A.sum()),
        "n_test_valid_no_slope": int(valid_test_A.sum()),
        "n_train_valid_with_slope": int(valid_train_B.sum()),
        "n_test_valid_with_slope": int(valid_test_B.sum()),
    })


# =========================================================
# 9. 汇总统计
# =========================================================
df_A = pd.DataFrame(metrics_no_slope)
df_B = pd.DataFrame(metrics_with_slope)

# fold 放到第一列
df_A = df_A[["fold"] + [c for c in df_A.columns if c != "fold"]]
df_B = df_B[["fold"] + [c for c in df_B.columns if c != "fold"]]

metric_names = [c for c in df_A.columns if c != "fold"]

summary_A = summarize(df_A, "RF(desc + 1/T)")
summary_B = summarize(df_B, "RF(desc + 1/T + slope)")

summary_all = pd.concat(
    [summary_A, summary_B],
    ignore_index=True,
)

print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
print(summary_all.to_string(index=False))


# =========================================================
# 10. 配对 t 检验
# =========================================================
t_test_results = []

for metric in metric_names:
    vals_A = pd.to_numeric(df_A[metric], errors="coerce").dropna().values
    vals_B = pd.to_numeric(df_B[metric], errors="coerce").dropna().values

    if len(vals_A) == len(vals_B) and len(vals_A) > 1:
        if SCIPY_AVAILABLE:
            t_stat, p_val = ttest_rel(vals_A, vals_B)
        else:
            t_stat, p_val = np.nan, np.nan

        if metric.startswith("R2") or metric in ["leq1%", "leq5%", "leq10%"]:
            better = "with_slope" if np.mean(vals_B) > np.mean(vals_A) else "no_slope"
        else:
            better = "with_slope" if np.mean(vals_B) < np.mean(vals_A) else "no_slope"

        t_test_results.append({
            "Metric": metric,
            "Mean_no_slope": np.mean(vals_A),
            "Mean_with_slope": np.mean(vals_B),
            "Delta_with_minus_no": np.mean(vals_B) - np.mean(vals_A),
            "t_stat": t_stat,
            "p_value": p_val,
            "Significant_p_lt_0.05": bool(p_val < 0.05) if np.isfinite(p_val) else False,
            "Better_model": better,
            "scipy_available": SCIPY_AVAILABLE,
        })

df_ttest = pd.DataFrame(t_test_results)

print("\n========== Paired t-test ==========")
print(df_ttest.to_string(index=False))


# =========================================================
# 11. 新增：完整数据集偏差数量统计汇总
# =========================================================
df_fold_all_data_count_summary = pd.DataFrame(fold_all_data_count_records)

final_average_records = []

for (method_name, count_space), sub in df_fold_all_data_count_summary.groupby(["Method", "count_space"]):
    final_average_records.append({
        "Method": method_name,
        "count_space": count_space,
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
# 12. 保存结果到 Excel
# =========================================================
df_pred_A = pd.concat(pred_rows_no_slope, ignore_index=True)
df_pred_B = pd.concat(pred_rows_with_slope, ignore_index=True)

df_fold_test_predictions = pd.concat(fold_test_prediction_dfs, ignore_index=True)
df_fold_all_data_predictions = pd.concat(fold_all_data_prediction_dfs, ignore_index=True)

df_feature_importance_no = pd.DataFrame(feature_importance_no_records)
df_feature_importance_with = pd.DataFrame(feature_importance_with_records)
df_fold_info = pd.DataFrame(fold_info_records)

df_used_features = pd.DataFrame({
    "used_descriptor_feature": used_feature_cols,
})

df_removed_zero_features = pd.DataFrame({
    "removed_zero_descriptor_feature": removed_zero_feature_cols,
})

df_slope_info = pd.DataFrame({
    "slope_file_used": [str(slope_path_used)],
    "slope_sheet_used": [slope_sheet_used],
    "slope_col": [slope_col],
    "slope_key_col": [slope_key_col],
})

run_info = pd.DataFrame([
    {"param": "descriptor_file", "value": str(descriptor_file)},
    {"param": "descriptor_sheet", "value": descriptor_sheet},
    {"param": "selected_feature_sheet", "value": selected_feature_sheet},
    {"param": "data_file", "value": str(data_file)},
    {"param": "data_sheet", "value": data_sheet},
    {"param": "slope_file_used", "value": str(slope_path_used)},
    {"param": "slope_sheet_used", "value": slope_sheet_used},

    {"param": "desc_key_col", "value": desc_key_col},
    {"param": "data_key_col", "value": data_key_col},
    {"param": "data_group_col", "value": data_group_col},
    {"param": "slope_key_col", "value": slope_key_col},

    {"param": "temp_col_actual", "value": temp_col_actual},
    {"param": "target_col", "value": target_col},
    {"param": "target_is_log", "value": target_is_log},
    {"param": "slope_col", "value": slope_col},

    {"param": "n_outer_folds", "value": n_outer_folds},
    {"param": "random_state", "value": random_state},
    {"param": "n_descriptor_features_original", "value": len(feature_cols)},
    {"param": "n_descriptor_features_used", "value": len(used_feature_cols)},
    {"param": "total_samples", "value": len(y)},
    {"param": "n_materials", "value": len(unique_materials)},

    {"param": "model_no_slope", "value": "RandomForestRegressor(desc + 1/T)"},
    {"param": "model_with_slope", "value": "RandomForestRegressor(desc + 1/T + slope_pred_lnP_over_invT)"},
    {"param": "rf_params", "value": str(rf_params)},
    {
        "param": "relative_error_definition",
        "value": "abs((y_pred - y_true) / y_true) * 100; abs(y_true)<=1e-12 -> NaN",
    },
    {
        "param": "final_count_space",
        "value": "P space, where P=exp(lnP) if target is lnP",
    },
    {
        "param": "full_data_count_rule",
        "value": "Each fold model predicts the whole dataset; count P-space relative error <1%, <5%, <10%; then average counts over 5 folds.",
    },
])

df_model_structure = pd.DataFrame([
    {
        "项目": "预测对象",
        "内容": f"蒸汽压；目标列 {target_col}；target_is_log={target_is_log}；同时保存 lnP 和 P 空间指标",
    },
    {
        "项目": "描述符文件",
        "内容": str(descriptor_file),
    },
    {
        "项目": "描述符 sheet",
        "内容": descriptor_sheet,
    },
    {
        "项目": "数据文件",
        "内容": str(data_file),
    },
    {
        "项目": "数据 sheet",
        "内容": data_sheet,
    },
    {
        "项目": "slope 文件",
        "内容": str(slope_path_used),
    },
    {
        "项目": "slope sheet",
        "内容": slope_sheet_used,
    },
    {
        "项目": "slope 列",
        "内容": slope_col,
    },
    {
        "项目": "交叉验证方式",
        "内容": f"{n_outer_folds}-fold KFold，按物质 ID 划分，shuffle=True，random_state={random_state}",
    },
    {
        "项目": "方法1",
        "内容": "RF_desc_invT：RandomForestRegressor，输入 [25 descriptors, 1/T]",
    },
    {
        "项目": "方法2",
        "内容": "RF_desc_invT_slope：RandomForestRegressor，输入 [25 descriptors, 1/T, slope_pred_lnP_over_invT]",
    },
    {
        "项目": "是否包含子模型",
        "内容": "当前代码不训练子模型；读取外部 HistGB 子模型预测得到的 slope",
    },
    {
        "项目": "子模型预测对象",
        "内容": "slope_pred_lnP_over_invT，用作方法2额外输入特征",
    },
    {
        "项目": "子模型类型",
        "内容": "外部文件名显示为 HistGB；本代码只读取预测结果，不在当前脚本内训练",
    },
    {
        "项目": "子模型参数",
        "内容": "当前代码无法从 slope 文件恢复；仅保存 slope 预测结果",
    },
    {
        "项目": "slope 构造",
        "内容": "直接读取 slope_pred_lnP_over_invT，作为方法2额外输入特征；不再乘以 1/T",
    },
    {
        "项目": "baseline 构造",
        "内容": "无 baseline + residual 结构；两个方法均为直接 RF 回归",
    },
    {
        "项目": "residual 构造",
        "内容": "无",
    },
    {
        "项目": "最终模型类型",
        "内容": "RandomForestRegressor",
    },
    {
        "项目": "最终模型参数",
        "内容": str(rf_params),
    },
    {
        "项目": "方法1最终输入",
        "内容": f"[{len(used_feature_cols)} 个描述符, 1/T]，总维度 {len(used_feature_cols) + 1}",
    },
    {
        "项目": "方法2最终输入",
        "内容": f"[{len(used_feature_cols)} 个描述符, 1/T, slope]，总维度 {len(used_feature_cols) + 2}",
    },
    {
        "项目": "偏差数量统计口径",
        "内容": "每个 fold 模型预测完整数据集，在 P 空间统计相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 取平均",
    },
])

with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_A.to_excel(writer, sheet_name="Fold_Metrics_No_Slope", index=False)
    df_B.to_excel(writer, sheet_name="Fold_Metrics_With_Slope", index=False)

    summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
    df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)

    # 保留原预测输出
    df_pred_A.to_excel(writer, sheet_name="Predictions_No_Slope", index=False)
    df_pred_B.to_excel(writer, sheet_name="Predictions_With_Slope", index=False)

    # 新增输出
    df_fold_test_predictions.to_excel(writer, sheet_name="fold_test_predictions", index=False)
    df_fold_all_data_predictions.to_excel(writer, sheet_name="fold_all_data_predictions", index=False)
    df_fold_all_data_count_summary.to_excel(writer, sheet_name="fold_all_data_count_summary", index=False)
    df_final_average_summary.to_excel(writer, sheet_name="final_average_summary", index=False)

    df_feature_importance_no.to_excel(writer, sheet_name="feature_importance_no", index=False)
    df_feature_importance_with.to_excel(writer, sheet_name="feature_importance_with", index=False)

    df_used_features.to_excel(writer, sheet_name="Used_Descriptor_Features", index=False)
    df_removed_zero_features.to_excel(writer, sheet_name="Removed_Zero_Descriptors", index=False)
    df_slope_info.to_excel(writer, sheet_name="slope_info", index=False)
    df_fold_info.to_excel(writer, sheet_name="Fold_Info", index=False)

    run_info.to_excel(writer, sheet_name="Run_Info", index=False)
    df_model_structure.to_excel(writer, sheet_name="model_structure", index=False)

    format_excel(writer)

print(f"\n保存完成: {output_file}")
print("主要输出 sheet:")
print("- Fold_Metrics_No_Slope")
print("- Fold_Metrics_With_Slope")
print("- Summary_Mean_Std")
print("- Paired_T_Test")
print("- Predictions_No_Slope")
print("- Predictions_With_Slope")
print("- fold_test_predictions")
print("- fold_all_data_predictions")
print("- fold_all_data_count_summary")
print("- final_average_summary")
print("- feature_importance_no")
print("- feature_importance_with")
print("- Used_Descriptor_Features")
print("- Run_Info")
print("- model_structure")


# =========================================================
# 13. 最终方便复制输出
# =========================================================
def get_final_counts(method_name, count_space="P"):
    row = df_final_average_summary[
        (df_final_average_summary["Method"] == method_name)
        & (df_final_average_summary["count_space"] == count_space)
    ]

    if row.empty:
        return np.nan, np.nan, np.nan

    row = row.iloc[0]

    return (
        row["mean_count_rel_err_lt_1pct"],
        row["mean_count_rel_err_lt_5pct"],
        row["mean_count_rel_err_lt_10pct"],
    )


no_1, no_5, no_10 = get_final_counts("RF_desc_invT", count_space="P")
with_1, with_5, with_10 = get_final_counts("RF_desc_invT_slope", count_space="P")

print("\n方法1 全数据预测偏差 1%，5%，10%分别为：")
print(no_1)
print(no_5)
print(no_10)

print("\n方法2 全数据预测偏差 1%，5%，10%分别为：")
print(with_1)
print(with_5)
print(with_10)


# =========================================================
# 14. 代码结构打印
# =========================================================
print("\n========== 当前代码结构简要汇总 ==========")
print(f"预测对象：蒸汽压；目标列 {target_col}；target_is_log={target_is_log}")
print(f"描述符文件：{descriptor_file}")
print(f"数据文件：{data_file}")
print(f"slope 文件：{slope_path_used}")
print(f"sheet 名称：{descriptor_sheet}, {data_sheet}, {slope_sheet_used}")
print(f"交叉验证：{n_outer_folds}-fold，按物质 ID 划分")
print("方法1：RF_desc_invT，RandomForestRegressor，输入 [descriptors, 1/T]")
print("方法2：RF_desc_invT_slope，RandomForestRegressor，输入 [descriptors, 1/T, slope_pred_lnP_over_invT]")
print("子模型：当前代码不训练子模型，读取外部 HistGB 预测的 slope")
print(f"子模型预测列：{slope_col}")
print("子模型参数：当前代码无法从 slope 文件恢复，仅保存 slope 预测值")
print("slope 构造：直接读取 slope_pred_lnP_over_invT，作为方法2额外输入特征")
print("baseline 构造：无")
print("residual 模型：无")
print(f"最终模型：RandomForestRegressor，参数：{rf_params}")
print("方法1最终输入：[descriptors, 1/T]")
print("方法2最终输入：[descriptors, 1/T, slope]")
print("偏差统计口径：每个 fold 模型预测完整数据集，在 P 空间统计 <1%、<5%、<10% 点数，再对 5 个 fold 取平均")