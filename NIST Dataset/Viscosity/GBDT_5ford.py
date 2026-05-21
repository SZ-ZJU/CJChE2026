# import pandas as pd
# import numpy as np
# from pathlib import Path
#
# from sklearn.ensemble import GradientBoostingRegressor, HistGradientBoostingRegressor
# from sklearn.linear_model import Ridge
# from sklearn.model_selection import KFold
# from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
# from scipy.stats import ttest_rel
#
# import warnings
# warnings.filterwarnings("ignore")
#
# pd.set_option("display.float_format", "{:.10f}".format)
# np.set_printoptions(suppress=True, precision=10)
#
# # =========================================================
# # 0. 全局设置
# # =========================================================
# input_file = Path("dataset_viscosity_selected_by_two_k_with_lnVisc_invT_interpolation_8points.xlsx")
# data_sheet = "Data_selected"
# groups_sheet = "Groups_selected"
# anchor_sheet = "Interpolated_k1_k2"
#
# output_file = Path("GBDT_direct_vs_anchor_residual_5fold_CV_global_anchor.xlsx")
#
# material_key_col = "material_key"
# temp_col = "T_K"
#
# viscosity_col_candidates = ["Viscosity_Pa_s", "viscosity_Pa_s", "Viscosity_Pa*s", "viscosity_Pa*s",
#                              "Viscosity, Pa*s", "viscosity", "Viscosity", "eta_Pa_s", "eta",
#                              "property_value", "value"]
# lnvisc_col_candidates = ["lnViscosity_Pa_s", "ln_viscosity_Pa_s", "lnViscosity", "ln_viscosity",
#                          "ln_eta", "lnEta", "ln_property_value"]
#
# anchor_lnvisc_candidates = ["lnViscosity_Pa_s_interp_at_k1Tb", "lnViscosity_interp_at_k1Tb",
#                             "ln_viscosity_interp_at_k1Tb", "ln_eta_interp_at_k1Tb"]
# anchor_viscosity_candidates = ["Viscosity_Pa_s_interp_at_k1Tb", "Viscosity_interp_at_k1Tb",
#                                "viscosity_interp_at_k1Tb", "eta_interp_at_k1Tb"]
# anchor_T_candidates = ["k1_times_boiling_T_K", "T_k1Tb", "T_k1_K", "ref_T1_K"]
# boiling_col_candidates = ["boiling_T_K", "Tb_K", "boiling_point_K"]
# k1_col_candidates = ["k1"]
#
# n_group_features_to_use = 220
# use_fixed_group_position = True
# group_start_col_1based = 3
# group_end_col_1based = 222
#
# n_outer_folds = 5
# random_state = 42
#
# # 锚点子模型参数（全局训练）
# hgb_params = dict(loss="squared_error", max_iter=1200, learning_rate=0.03,
#                   max_leaf_nodes=63, min_samples_leaf=2, l2_regularization=0.0,
#                   early_stopping=False, random_state=random_state)
#
# # 直接 GBDT 与残差 GBDT 参数
# gbdt_params = {"n_estimators": 500, "learning_rate": 0.03, "max_depth": 3,
#                "min_samples_split": 10, "min_samples_leaf": 5, "subsample": 0.9,
#                "random_state": random_state}
#
# use_ridge_for_baseline = True
# baseline_ridge_alpha = 1.0
#
# # =========================================================
# # 1. 读取数据
# # =========================================================
# df_data = pd.read_excel(input_file, sheet_name=data_sheet)
# df_groups_raw = pd.read_excel(input_file, sheet_name=groups_sheet)
# df_anchor = pd.read_excel(input_file, sheet_name=anchor_sheet)
#
# # =========================================================
# # 2. 统一物质 ID
# # =========================================================
# def is_valid_value(x):
#     if pd.isna(x): return False
#     s = str(x).strip()
#     if s == "" or s.lower() in ["nan","none","null","待定"]: return False
#     return True
#
# def build_material_key(row):
#     for col in ["material_key","inchikey","InChIKey","inchi_key","pubchem_inchikey","cas","compound_name","formula"]:
#         if col in row.index and is_valid_value(row[col]):
#             if col == "material_key":
#                 return str(row[col]).strip()
#             return f"{col}:{str(row[col]).strip()}"
#     return "unknown_material"
#
# for df in [df_data, df_groups_raw, df_anchor]:
#     if material_key_col not in df.columns:
#         df[material_key_col] = df.apply(build_material_key, axis=1)
#     df[material_key_col] = df[material_key_col].astype(str).str.strip()
#
# # =========================================================
# # 3. 自动查找列名（大小写不敏感）
# # =========================================================
# def find_first_existing_col(df, candidates, required=True, col_type="列"):
#     for c in candidates:
#         if c in df.columns:
#             return c
#     low_map = {str(c).lower(): c for c in df.columns}
#     for c in candidates:
#         if str(c).lower() in low_map:
#             return low_map[str(c).lower()]
#     if required:
#         raise ValueError(f"未找到 {col_type} : {candidates}")
#     return None
#
# viscosity_col = find_first_existing_col(df_data, viscosity_col_candidates, required=True)
# lnvisc_col = find_first_existing_col(df_data, lnvisc_col_candidates, required=False)
# if lnvisc_col is None:
#     lnvisc_col = "lnViscosity"
#     df_data[lnvisc_col] = np.where(df_data[viscosity_col] > 0, np.log(df_data[viscosity_col]), np.nan)
# else:
#     df_data[lnvisc_col] = pd.to_numeric(df_data[lnvisc_col], errors="coerce")
#
# anchor_lnvisc_col = find_first_existing_col(df_anchor, anchor_lnvisc_candidates, required=False)
# if anchor_lnvisc_col is None:
#     anchor_visc_col = find_first_existing_col(df_anchor, anchor_viscosity_candidates, required=False)
#     if anchor_visc_col is None:
#         raise ValueError("未找到锚点 lnViscosity 或粘度列")
#     df_anchor[anchor_visc_col] = pd.to_numeric(df_anchor[anchor_visc_col], errors="coerce")
#     anchor_lnvisc_col = "lnViscosity_anchor"
#     df_anchor[anchor_lnvisc_col] = np.where(df_anchor[anchor_visc_col] > 0, np.log(df_anchor[anchor_visc_col]), np.nan)
#
# boiling_col = find_first_existing_col(df_anchor, boiling_col_candidates, required=True)
# df_anchor[boiling_col] = pd.to_numeric(df_anchor[boiling_col], errors="coerce")
# k1_col = find_first_existing_col(df_anchor, k1_col_candidates, required=False)
# if k1_col is None:
#     anchor_T_col = find_first_existing_col(df_anchor, anchor_T_candidates, required=False)
#     if anchor_T_col is None:
#         raise ValueError("无法获取 k1")
#     df_anchor[anchor_T_col] = pd.to_numeric(df_anchor[anchor_T_col], errors="coerce")
#     df_anchor["k1"] = df_anchor[anchor_T_col] / df_anchor[boiling_col]
#     k1_col = "k1"
# else:
#     df_anchor[k1_col] = pd.to_numeric(df_anchor[k1_col], errors="coerce")
#
# print(f"目标列: {lnvisc_col}")
# print(f"锚点 lnViscosity 列: {anchor_lnvisc_col}")
# print(f"沸点列: {boiling_col}")
# print(f"k1 列: {k1_col}")
#
# # =========================================================
# # 4. 基团列
# # =========================================================
# def identify_group_columns(df_groups, n=220):
#     if use_fixed_group_position:
#         start = group_start_col_1based - 1
#         end_excl = group_end_col_1based
#         if len(df_groups.columns) < end_excl:
#             raise ValueError(f"列数不足 {group_end_col_1based}")
#         group_cols = list(df_groups.columns[start:end_excl])
#         if len(group_cols) != n:
#             raise ValueError(f"固定位置识别 {len(group_cols)} 个基团，需要 {n}")
#         return group_cols
#     else:
#         meta = ["original_material_index","material_key","compound","name","cas","formula","smiles","inchi","inchikey","pubchem","phase","property","boiling","temperature","temp","t_k","pressure","lnp","lnviscosity","viscosity","density","k1","k2","interp","status","range"]
#         candidate = []
#         for col in df_groups.columns:
#             if any(k in col.lower() for k in meta):
#                 continue
#             if pd.to_numeric(df_groups[col], errors="coerce").notna().sum() > 0:
#                 candidate.append(col)
#         if len(candidate) < n:
#             raise ValueError(f"自动识别仅 {len(candidate)} 个基团，少于 {n}")
#         return candidate[:n]
#
# group_cols_220 = identify_group_columns(df_groups_raw, n_group_features_to_use)
# for col in group_cols_220:
#     df_groups_raw[col] = pd.to_numeric(df_groups_raw[col], errors="coerce").fillna(0.0)
# nonzero_group_cols = [c for c in group_cols_220 if not np.isclose(df_groups_raw[c].abs().sum(), 0.0)]
# used_group_cols = nonzero_group_cols
# print(f"有效基团数: {len(used_group_cols)}")
#
# # =========================================================
# # 5. 构造物质级 k1 映射和全局锚点模型
# # =========================================================
# df_material_temp = df_groups_raw[[material_key_col] + used_group_cols].drop_duplicates()
# df_material_temp = df_material_temp.merge(df_anchor[[material_key_col, boiling_col, k1_col]], on=material_key_col, how="inner")
# k1_median = df_material_temp[k1_col].replace([np.inf,-np.inf], np.nan).median()
# df_material_temp[k1_col] = df_material_temp[k1_col].fillna(k1_median)
# k1_map = df_material_temp.set_index(material_key_col)[k1_col].to_dict()
#
# # 构建全局锚点模型需要的物质级数据
# # 注意：锚点模型的训练目标是锚点表的 lnViscosity 和沸点（真值）
# anchor_true = df_anchor.set_index(material_key_col)[[anchor_lnvisc_col, boiling_col]].dropna()
# common_materials = set(anchor_true.index) & set(df_material_temp[material_key_col])
# X_global = []
# y_lnv = []
# y_boil = []
# for m in common_materials:
#     X_global.append(df_material_temp[df_material_temp[material_key_col]==m][used_group_cols].values[0])
#     y_lnv.append(anchor_true.loc[m, anchor_lnvisc_col])
#     y_boil.append(anchor_true.loc[m, boiling_col])
# X_global = np.array(X_global)
# y_lnv = np.array(y_lnv)
# y_boil = np.array(y_boil)
#
# valid = (np.isfinite(X_global).all(axis=1) & np.isfinite(y_lnv) & np.isfinite(y_boil) & (y_boil>0))
# X_global = X_global[valid]
# y_lnv = y_lnv[valid]
# y_boil = y_boil[valid]
#
# global_anchor_model = HistGradientBoostingRegressor(**hgb_params)
# global_boiling_model = HistGradientBoostingRegressor(**hgb_params)
# global_anchor_model.fit(X_global, y_lnv)
# global_boiling_model.fit(X_global, y_boil)
#
# # 物质到基团矩阵的映射
# material_to_groups = {row[material_key_col]: row[used_group_cols].values for _, row in df_material_temp.iterrows()}
#
# # 计算所有物质的全局锚点预测
# material_anchor_pred = {}
# material_invT_anchor = {}
# for m in common_materials:
#     if m not in material_to_groups:
#         continue
#     Xm = material_to_groups[m].reshape(1, -1)
#     anch = global_anchor_model.predict(Xm)[0]
#     boil_pred = global_boiling_model.predict(Xm)[0]
#     k1m = k1_map.get(m, np.nan)
#     if np.isfinite(k1m) and boil_pred > 0:
#         T_anch = k1m * boil_pred
#         invT = 1.0 / T_anch
#     else:
#         invT = np.nan
#     material_anchor_pred[m] = anch
#     material_invT_anchor[m] = invT
#
# # =========================================================
# # 6. 展开温度点数据
# # =========================================================
# df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
# df_data[lnvisc_col] = pd.to_numeric(df_data[lnvisc_col], errors="coerce")
# df_data["InvT"] = 1.0 / df_data[temp_col]
#
# if "boiling_T_K" in df_data.columns:
#     df_data = df_data.drop(columns=["boiling_T_K"])
#
# df_long = df_data.merge(df_groups_raw[[material_key_col] + used_group_cols], on=material_key_col, how="inner")
# df_long["k1_use"] = df_long[material_key_col].map(k1_map)
# df_long["anchor_lnVisc_global"] = df_long[material_key_col].map(material_anchor_pred)
# df_long["invT_anchor_global"] = df_long[material_key_col].map(material_invT_anchor)
#
# df_long = df_long[
#     (df_long[temp_col] > 0) &
#     (df_long[viscosity_col] > 0) &
#     np.isfinite(df_long[lnvisc_col]) &
#     np.isfinite(df_long["InvT"]) &
#     np.isfinite(df_long["anchor_lnVisc_global"]) &
#     np.isfinite(df_long["invT_anchor_global"]) &
#     np.isfinite(df_long["k1_use"])
# ].reset_index(drop=True)
#
# X_groups = df_long[used_group_cols].values.astype(float)
# InvT = df_long["InvT"].values.astype(float)
# y = df_long[lnvisc_col].values.astype(float)
# material_keys = df_long[material_key_col].values
# anchor_lnVisc_global = df_long["anchor_lnVisc_global"].values.astype(float)
# invT_anchor_global = df_long["invT_anchor_global"].values.astype(float)
#
# unique_materials = np.unique(material_keys)
# print(f"总样本数: {len(y)}, 总物质数: {len(unique_materials)}")
#
# # =========================================================
# # 7. 5折交叉验证
# # =========================================================
# kf = KFold(n_splits=n_outer_folds, shuffle=True, random_state=random_state)
# metrics_direct = []
# metrics_residual = []
#
# for fold, (train_idx, test_idx) in enumerate(kf.split(unique_materials)):
#     print(f"\n========== Fold {fold+1}/{n_outer_folds} ==========")
#     train_mats = unique_materials[train_idx]
#     test_mats = unique_materials[test_idx]
#
#     train_mask = np.isin(material_keys, train_mats)
#     test_mask = np.isin(material_keys, test_mats)
#
#     # 方法A：直接GBDT
#     X_train_A = np.hstack([X_groups[train_mask], InvT[train_mask].reshape(-1,1)])
#     y_train_A = y[train_mask]
#     valid_A = np.isfinite(X_train_A).all(axis=1) & np.isfinite(y_train_A)
#     X_train_A = X_train_A[valid_A]
#     y_train_A = y_train_A[valid_A]
#     model_A = GradientBoostingRegressor(**gbdt_params)
#     model_A.fit(X_train_A, y_train_A)
#
#     X_test_A = np.hstack([X_groups[test_mask], InvT[test_mask].reshape(-1,1)])
#     y_test_A = y[test_mask]
#     valid_test_A = np.isfinite(X_test_A).all(axis=1)
#     y_pred_A = np.full(len(y_test_A), np.nan)
#     y_pred_A[valid_test_A] = model_A.predict(X_test_A[valid_test_A])
#
#     # 方法B：使用全局锚点
#     anchor_vals = anchor_lnVisc_global[test_mask]
#     invT_anchor_vals = invT_anchor_global[test_mask]
#     anchor_train_vals = anchor_lnVisc_global[train_mask]
#     invT_anchor_train_vals = invT_anchor_global[train_mask]
#
#     delta_invT_train = InvT[train_mask] - invT_anchor_train_vals
#     X_base_train = X_groups[train_mask] * delta_invT_train.reshape(-1,1)
#     y_base_train = y[train_mask] - anchor_train_vals
#     valid_base = np.isfinite(X_base_train).all(axis=1) & np.isfinite(y_base_train)
#     if valid_base.sum() == 0:
#         y_pred_B = np.full(len(y_test_A), np.nan)
#     else:
#         base_model = Ridge(alpha=baseline_ridge_alpha, fit_intercept=False)
#         base_model.fit(X_base_train[valid_base], y_base_train[valid_base])
#
#         delta_invT_test = InvT[test_mask] - invT_anchor_vals
#         X_base_test = X_groups[test_mask] * delta_invT_test.reshape(-1,1)
#         valid_base_test = np.isfinite(X_base_test).all(axis=1)
#         base_delta = np.full(len(y_test_A), np.nan)
#         base_delta[valid_base_test] = base_model.predict(X_base_test[valid_base_test])
#         baseline_pred = anchor_vals + base_delta
#
#         # 残差模型
#         residual_X_train = np.hstack([X_groups[train_mask], InvT[train_mask].reshape(-1,1)])
#         delta_invT_train_full = InvT[train_mask] - invT_anchor_train_vals
#         X_base_train_full = X_groups[train_mask] * delta_invT_train_full.reshape(-1,1)
#         base_delta_train = base_model.predict(X_base_train_full)
#         baseline_pred_train = anchor_train_vals + base_delta_train
#         residual_y_train = y[train_mask] - baseline_pred_train
#
#         valid_res = np.isfinite(residual_X_train).all(axis=1) & np.isfinite(residual_y_train)
#         if valid_res.sum() == 0:
#             y_pred_B = np.full(len(y_test_A), np.nan)
#         else:
#             res_model = GradientBoostingRegressor(**gbdt_params)
#             res_model.fit(residual_X_train[valid_res], residual_y_train[valid_res])
#
#             residual_X_test = np.hstack([X_groups[test_mask], InvT[test_mask].reshape(-1,1)])
#             valid_res_test = np.isfinite(residual_X_test).all(axis=1)
#             residual_pred = np.full(len(y_test_A), np.nan)
#             residual_pred[valid_res_test] = res_model.predict(residual_X_test[valid_res_test])
#             y_pred_B = baseline_pred + residual_pred
#
#     def compute_metrics(y_true, y_pred):
#         mask = np.isfinite(y_true) & np.isfinite(y_pred)
#         y_true = y_true[mask]
#         y_pred = y_pred[mask]
#         if len(y_true) == 0:
#             return {k: np.nan for k in ["R2_ln","MSE_ln","RMSE_ln","MAE_ln","ARD_ln",
#                                         "R2_vis","MSE_vis","RMSE_vis","MAE_vis","ARD_vis",
#                                         "leq1%","leq5%","leq10%","max_rel%"]}
#         r2_ln = r2_score(y_true, y_pred)
#         mse_ln = mean_squared_error(y_true, y_pred)
#         rmse_ln = np.sqrt(mse_ln)
#         mae_ln = mean_absolute_error(y_true, y_pred)
#         with np.errstate(divide='ignore', invalid='ignore'):
#             ard_ln = np.mean(np.abs((y_pred - y_true) / y_true)) * 100 if np.abs(y_true).mean() > 0 else np.nan
#
#         visc_true = np.exp(y_true)
#         visc_pred = np.exp(y_pred)
#         r2_vis = r2_score(visc_true, visc_pred)
#         mse_vis = mean_squared_error(visc_true, visc_pred)
#         rmse_vis = np.sqrt(mse_vis)
#         mae_vis = mean_absolute_error(visc_true, visc_pred)
#         with np.errstate(divide='ignore', invalid='ignore'):
#             ard_vis = np.mean(np.abs((visc_pred - visc_true) / visc_true)) * 100 if np.abs(visc_true).mean() > 0 else np.nan
#
#         valid = np.abs(visc_true) > 1e-12
#         if valid.sum() > 0:
#             rel_err = np.abs((visc_pred[valid] - visc_true[valid]) / visc_true[valid]) * 100
#             le1 = np.mean(rel_err <= 1) * 100
#             le5 = np.mean(rel_err <= 5) * 100
#             le10 = np.mean(rel_err <= 10) * 100
#             max_rel = np.max(rel_err)
#         else:
#             le1 = le5 = le10 = max_rel = np.nan
#
#         return {
#             "R2_ln": r2_ln, "MSE_ln": mse_ln, "RMSE_ln": rmse_ln, "MAE_ln": mae_ln, "ARD_ln_percent": ard_ln,
#             "R2_vis": r2_vis, "MSE_vis": mse_vis, "RMSE_vis": rmse_vis, "MAE_vis": mae_vis, "ARD_vis_percent": ard_vis,
#             "leq1%": le1, "leq5%": le5, "leq10%": le10, "max_rel%": max_rel
#         }
#
#     m_A = compute_metrics(y_test_A, y_pred_A)
#     m_B = compute_metrics(y_test_A, y_pred_B)
#     m_A["fold"] = fold+1
#     m_B["fold"] = fold+1
#     metrics_direct.append(m_A)
#     metrics_residual.append(m_B)
#
# # =========================================================
# # 8. 汇总统计
# # =========================================================
# df_A = pd.DataFrame(metrics_direct)
# df_B = pd.DataFrame(metrics_residual)
#
# metric_names = [c for c in df_A.columns if c != "fold"]
#
# def summarize(df, name):
#     rows = []
#     for metric in metric_names:
#         vals = df[metric].dropna().values
#         if len(vals) == 0:
#             mean_std = "NaN"
#         else:
#             mean_val = np.mean(vals)
#             std_val = np.std(vals, ddof=1)
#             mean_std = f"{mean_val:.4f} ± {std_val:.4f}"
#         rows.append({"Model": name, "Metric": metric, "Mean±Std": mean_std})
#     return pd.DataFrame(rows)
#
# summary_A = summarize(df_A, "GBDT_direct (groups+1/T)")
# summary_B = summarize(df_B, "Anchor+linear+GBDT_residual (global anchor)")
# summary_all = pd.concat([summary_A, summary_B], ignore_index=True)
#
# print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
# print(summary_all.to_string(index=False))
#
# # =========================================================
# # 9. 配对 t 检验
# # =========================================================
# t_test_results = []
# for metric in metric_names:
#     vals_A = df_A[metric].dropna().values
#     vals_B = df_B[metric].dropna().values
#     if len(vals_A) == len(vals_B) and len(vals_A) > 1:
#         t_stat, p_val = ttest_rel(vals_A, vals_B)
#         if metric.startswith("R2"):
#             better = "methodB" if np.mean(vals_B) > np.mean(vals_A) else "methodA"
#             sig = p_val < 0.05
#         else:
#             better = "methodB" if np.mean(vals_B) < np.mean(vals_A) else "methodA"
#             sig = p_val < 0.05
#         t_test_results.append({
#             "Metric": metric,
#             "Mean_direct": f"{np.mean(vals_A):.4f}",
#             "Mean_residual": f"{np.mean(vals_B):.4f}",
#             "p-value": f"{p_val:.4e}",
#             "Significant(p<0.05)": sig,
#             "Better model": better
#         })
#
# df_ttest = pd.DataFrame(t_test_results)
# print("\n========== Paired t-test ==========")
# print(df_ttest.to_string(index=False))
#
# # =========================================================
# # 10. 保存结果
# # =========================================================
# with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
#     df_A.to_excel(writer, sheet_name="Fold_Metrics_Direct", index=False)
#     df_B.to_excel(writer, sheet_name="Fold_Metrics_Residual", index=False)
#     summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
#     df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)
#
#     pd.DataFrame([
#         {"param": "n_outer_folds", "value": n_outer_folds},
#         {"param": "random_state", "value": random_state},
#         {"param": "n_group_features", "value": len(used_group_cols)},
#         {"param": "total_samples", "value": len(y)},
#         {"param": "n_materials", "value": len(unique_materials)},
#         {"param": "anchor_model_training", "value": "global (all materials)"},
#     ]).to_excel(writer, sheet_name="Run_Info", index=False)
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
# print(f"\n保存完成: {output_file}")



import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.ensemble import GradientBoostingRegressor, HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from scipy.stats import ttest_rel

import warnings
warnings.filterwarnings("ignore")

pd.set_option("display.float_format", "{:.10f}".format)
np.set_printoptions(suppress=True, precision=10)


# =========================================================
# 0. 全局设置
# =========================================================
input_file = Path("dataset_viscosity_selected_by_two_k_with_lnVisc_invT_interpolation_8points.xlsx")
data_sheet = "Data_selected"
groups_sheet = "Groups_selected"
anchor_sheet = "Interpolated_k1_k2"

output_file = Path("GBDT_direct_vs_anchor_residual_5fold_CV_global_anchor.xlsx")

material_key_col = "material_key"
temp_col = "T_K"

viscosity_col_candidates = [
    "Viscosity_Pa_s", "viscosity_Pa_s", "Viscosity_Pa*s", "viscosity_Pa*s",
    "Viscosity, Pa*s", "viscosity", "Viscosity", "eta_Pa_s", "eta",
    "property_value", "value"
]

lnvisc_col_candidates = [
    "lnViscosity_Pa_s", "ln_viscosity_Pa_s", "lnViscosity", "ln_viscosity",
    "ln_eta", "lnEta", "ln_property_value"
]

anchor_lnvisc_candidates = [
    "lnViscosity_Pa_s_interp_at_k1Tb", "lnViscosity_interp_at_k1Tb",
    "ln_viscosity_interp_at_k1Tb", "ln_eta_interp_at_k1Tb"
]

anchor_viscosity_candidates = [
    "Viscosity_Pa_s_interp_at_k1Tb", "Viscosity_interp_at_k1Tb",
    "viscosity_interp_at_k1Tb", "eta_interp_at_k1Tb"
]

anchor_T_candidates = [
    "k1_times_boiling_T_K", "T_k1Tb", "T_k1_K", "ref_T1_K"
]

boiling_col_candidates = [
    "boiling_T_K", "Tb_K", "boiling_point_K"
]

k1_col_candidates = ["k1"]

n_group_features_to_use = 220
use_fixed_group_position = True
group_start_col_1based = 3
group_end_col_1based = 222

n_outer_folds = 5
random_state = 42

# 锚点子模型参数（全局训练，保留原始设计）
hgb_params = dict(
    loss="squared_error",
    max_iter=1200,
    learning_rate=0.03,
    max_leaf_nodes=63,
    min_samples_leaf=2,
    l2_regularization=0.0,
    early_stopping=False,
    random_state=random_state,
)

# 直接 GBDT 与残差 GBDT 参数
gbdt_params = {
    "n_estimators": 500,
    "learning_rate": 0.03,
    "max_depth": 3,
    "min_samples_split": 10,
    "min_samples_leaf": 5,
    "subsample": 0.9,
    "random_state": random_state,
}

use_ridge_for_baseline = True
baseline_ridge_alpha = 1.0


# =========================================================
# 1. 工具函数
# =========================================================
def is_valid_value(x):
    if pd.isna(x):
        return False
    s = str(x).strip()
    if s == "" or s.lower() in ["nan", "none", "null", "待定"]:
        return False
    return True


def build_material_key(row):
    for col in [
        "material_key", "inchikey", "InChIKey", "inchi_key",
        "pubchem_inchikey", "cas", "compound_name", "formula"
    ]:
        if col in row.index and is_valid_value(row[col]):
            if col == "material_key":
                return str(row[col]).strip()
            return f"{col}:{str(row[col]).strip()}"
    return "unknown_material"


def normalize_colname(name):
    return (
        str(name)
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
        .replace("/", "")
        .replace("(", "")
        .replace(")", "")
    )


def find_first_existing_col(df, candidates, required=True, col_type="列"):
    for c in candidates:
        if c in df.columns:
            return c

    norm_map = {normalize_colname(c): c for c in df.columns}

    for c in candidates:
        key = normalize_colname(c)
        if key in norm_map:
            return norm_map[key]

    if required:
        raise ValueError(f"未找到 {col_type}: {candidates}")

    return None


def safe_exp(x):
    return np.exp(np.clip(np.asarray(x, dtype=float), -700, 700))


def safe_log(x):
    x = np.asarray(x, dtype=float)
    out = np.full_like(x, np.nan, dtype=float)
    valid = np.isfinite(x) & (x > 0)
    out[valid] = np.log(x[valid])
    return out


def safe_relative_error_percent(y_true, y_pred, eps=1e-12):
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
        & (np.abs(y_true) > eps)
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


def average_relative_deviation(y_true, y_pred):
    rel_err = safe_relative_error_percent(y_true, y_pred)

    if np.any(np.isfinite(rel_err)):
        return float(np.nanmean(rel_err))

    return np.nan


def compute_metrics(y_true_ln, y_pred_ln):
    """
    同时返回 lnη 空间和 η=exp(lnη) 空间指标。
    原始代码中 leq1/leq5/leq10 在 η 空间按 <= 统计比例。
    """
    y_true_ln = np.asarray(y_true_ln, dtype=float)
    y_pred_ln = np.asarray(y_pred_ln, dtype=float)

    mask = np.isfinite(y_true_ln) & np.isfinite(y_pred_ln)

    y_true_ln = y_true_ln[mask]
    y_pred_ln = y_pred_ln[mask]

    if len(y_true_ln) == 0:
        return {
            "n_points": 0,

            "R2_ln": np.nan,
            "MSE_ln": np.nan,
            "RMSE_ln": np.nan,
            "MAE_ln": np.nan,
            "ARD_ln_percent": np.nan,

            "R2_vis": np.nan,
            "MSE_vis": np.nan,
            "RMSE_vis": np.nan,
            "MAE_vis": np.nan,
            "ARD_vis_percent": np.nan,

            "leq1%": np.nan,
            "leq5%": np.nan,
            "leq10%": np.nan,
            "max_rel%": np.nan,
        }

    r2_ln = r2_score(y_true_ln, y_pred_ln) if len(y_true_ln) > 1 else np.nan
    mse_ln = mean_squared_error(y_true_ln, y_pred_ln)
    rmse_ln = np.sqrt(mse_ln)
    mae_ln = mean_absolute_error(y_true_ln, y_pred_ln)
    ard_ln = average_relative_deviation(y_true_ln, y_pred_ln)

    visc_true = safe_exp(y_true_ln)
    visc_pred = safe_exp(y_pred_ln)

    r2_vis = r2_score(visc_true, visc_pred) if len(visc_true) > 1 else np.nan
    mse_vis = mean_squared_error(visc_true, visc_pred)
    rmse_vis = np.sqrt(mse_vis)
    mae_vis = mean_absolute_error(visc_true, visc_pred)
    ard_vis = average_relative_deviation(visc_true, visc_pred)

    rel_err = safe_relative_error_percent(visc_true, visc_pred)

    if np.any(np.isfinite(rel_err)):
        le1 = np.nanmean(rel_err <= 1.0) * 100.0
        le5 = np.nanmean(rel_err <= 5.0) * 100.0
        le10 = np.nanmean(rel_err <= 10.0) * 100.0
        max_rel = np.nanmax(rel_err)
    else:
        le1 = le5 = le10 = max_rel = np.nan

    return {
        "n_points": len(y_true_ln),

        "R2_ln": r2_ln,
        "MSE_ln": mse_ln,
        "RMSE_ln": rmse_ln,
        "MAE_ln": mae_ln,
        "ARD_ln_percent": ard_ln,

        "R2_vis": r2_vis,
        "MSE_vis": mse_vis,
        "RMSE_vis": rmse_vis,
        "MAE_vis": mae_vis,
        "ARD_vis_percent": ard_vis,

        "leq1%": le1,
        "leq5%": le5,
        "leq10%": le10,
        "max_rel%": max_rel,
    }


def summarize(df, name):
    rows = []

    metric_names = [c for c in df.columns if c != "fold"]

    for metric in metric_names:
        vals = pd.to_numeric(df[metric], errors="coerce").dropna().values

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

        rows.append({
            "Model": name,
            "Metric": metric,
            "Mean": mean_val,
            "Std": std_val,
            "Mean±Std": mean_std,
        })

    return pd.DataFrame(rows)


def identify_group_columns(df_groups, n=220):
    if use_fixed_group_position:
        start = group_start_col_1based - 1
        end_excl = group_end_col_1based

        if len(df_groups.columns) < end_excl:
            raise ValueError(f"列数不足 {group_end_col_1based}")

        group_cols = list(df_groups.columns[start:end_excl])

        if len(group_cols) != n:
            raise ValueError(f"固定位置识别 {len(group_cols)} 个基团，需要 {n}")

        return group_cols

    meta = [
        "original_material_index", "material_key", "compound", "name", "cas",
        "formula", "smiles", "inchi", "inchikey", "pubchem", "phase",
        "property", "boiling", "temperature", "temp", "t_k", "pressure",
        "lnp", "lnviscosity", "viscosity", "density", "k1", "k2",
        "interp", "status", "range"
    ]

    candidate = []

    for col in df_groups.columns:
        if any(k in str(col).lower() for k in meta):
            continue

        if pd.to_numeric(df_groups[col], errors="coerce").notna().sum() > 0:
            candidate.append(col)

    if len(candidate) < n:
        raise ValueError(f"自动识别仅 {len(candidate)} 个基团，少于 {n}")

    return candidate[:n]


def build_direct_features(indices):
    indices = np.asarray(indices, dtype=int)

    return np.hstack([
        X_groups[indices],
        InvT[indices].reshape(-1, 1),
    ])


def build_baseline_features(indices):
    indices = np.asarray(indices, dtype=int)

    delta_invT = InvT[indices] - invT_anchor_global[indices]

    return X_groups[indices] * delta_invT.reshape(-1, 1)


def build_residual_features(indices):
    indices = np.asarray(indices, dtype=int)

    return np.hstack([
        X_groups[indices],
        InvT[indices].reshape(-1, 1),
    ])


def train_methodB(train_indices):
    """
    方法B：
        1. baseline_delta = Ridge(Nk * (InvT - InvT_anchor))
        2. baseline_lnVisc = anchor_lnVisc_global + baseline_delta
        3. residual_y = lnVisc_true - baseline_lnVisc
        4. residual_pred = GBDT([Nk, InvT])
        5. final = baseline + residual
    """
    train_indices = np.asarray(train_indices, dtype=int)

    # baseline Ridge
    X_base_train = build_baseline_features(train_indices)
    y_base_train = y[train_indices] - anchor_lnVisc_global[train_indices]

    valid_base = (
        np.isfinite(X_base_train).all(axis=1)
        & np.isfinite(y_base_train)
    )

    if valid_base.sum() == 0:
        return None, None

    if use_ridge_for_baseline:
        base_model = Ridge(alpha=baseline_ridge_alpha, fit_intercept=False)
    else:
        raise ValueError("当前代码保留原设计：baseline 使用 Ridge。")

    base_model.fit(X_base_train[valid_base], y_base_train[valid_base])

    # 训练集 baseline
    base_delta_train = np.full(len(train_indices), np.nan, dtype=float)

    valid_base_full = np.isfinite(X_base_train).all(axis=1)

    if valid_base_full.sum() > 0:
        base_delta_train[valid_base_full] = base_model.predict(X_base_train[valid_base_full])

    baseline_train = anchor_lnVisc_global[train_indices] + base_delta_train

    residual_y_train = y[train_indices] - baseline_train
    X_res_train = build_residual_features(train_indices)

    valid_res = (
        np.isfinite(X_res_train).all(axis=1)
        & np.isfinite(residual_y_train)
    )

    if valid_res.sum() == 0:
        return base_model, None

    res_model = GradientBoostingRegressor(**gbdt_params)
    res_model.fit(X_res_train[valid_res], residual_y_train[valid_res])

    return base_model, res_model


def predict_methodB(indices, base_model, res_model):
    indices = np.asarray(indices, dtype=int)

    baseline_pred = np.full(len(indices), np.nan, dtype=float)
    residual_pred = np.full(len(indices), np.nan, dtype=float)
    final_pred = np.full(len(indices), np.nan, dtype=float)

    if base_model is None:
        return final_pred, baseline_pred, residual_pred

    # baseline
    X_base = build_baseline_features(indices)
    base_delta = np.full(len(indices), np.nan, dtype=float)

    valid_base = np.isfinite(X_base).all(axis=1)

    if valid_base.sum() > 0:
        base_delta[valid_base] = base_model.predict(X_base[valid_base])

    baseline_pred = anchor_lnVisc_global[indices] + base_delta

    if res_model is None:
        return final_pred, baseline_pred, residual_pred

    # residual
    X_res = build_residual_features(indices)

    valid_res = (
        np.isfinite(X_res).all(axis=1)
        & np.isfinite(baseline_pred)
    )

    if valid_res.sum() > 0:
        residual_pred[valid_res] = res_model.predict(X_res[valid_res])

    final_pred = baseline_pred + residual_pred

    return final_pred, baseline_pred, residual_pred


def make_prediction_df(
    fold,
    dataset_name,
    method,
    indices,
    y_pred_ln,
    baseline_pred=None,
    residual_pred=None,
):
    indices = np.asarray(indices, dtype=int)

    y_true_ln = y[indices]
    eta_true = safe_exp(y_true_ln)
    eta_pred = safe_exp(y_pred_ln)

    df_out = pd.DataFrame({
        "fold": fold,
        "dataset": dataset_name,
        "Method": method,
        "sample_index": indices,
        material_key_col: material_keys[indices],
        "T_K": 1.0 / InvT[indices],
        "InvT": InvT[indices],
        "lnVisc_true": y_true_ln,
        "lnVisc_pred": y_pred_ln,
        "lnVisc_error": y_pred_ln - y_true_ln,
        "lnVisc_absolute_error": np.abs(y_pred_ln - y_true_ln),
        "lnVisc_relative_error_percent": safe_relative_error_percent(y_true_ln, y_pred_ln),
        "eta_true": eta_true,
        "eta_pred": eta_pred,
        "eta_error": eta_pred - eta_true,
        "eta_absolute_error": np.abs(eta_pred - eta_true),
        "eta_relative_error_percent": safe_relative_error_percent(eta_true, eta_pred),
        "anchor_lnVisc_global": anchor_lnVisc_global[indices],
        "anchor_eta_global": safe_exp(anchor_lnVisc_global[indices]),
        "invT_anchor_global": invT_anchor_global[indices],
        "T_anchor_global": 1.0 / invT_anchor_global[indices],
        "delta_invT": InvT[indices] - invT_anchor_global[indices],
        "k1_use": df_long["k1_use"].values[indices],
    })

    if viscosity_col in df_long.columns:
        df_out["viscosity_raw"] = df_long[viscosity_col].values[indices]

    if baseline_pred is not None:
        df_out["baseline_lnVisc"] = baseline_pred
        df_out["baseline_eta"] = safe_exp(baseline_pred)
        df_out["baseline_lnVisc_error"] = baseline_pred - y_true_ln
        df_out["baseline_eta_relative_error_percent"] = safe_relative_error_percent(
            eta_true,
            safe_exp(baseline_pred),
        )

    if residual_pred is not None:
        df_out["residual_pred_lnVisc"] = residual_pred
        if baseline_pred is not None:
            df_out["residual_target_lnVisc"] = y_true_ln - baseline_pred

    extra_cols = [
        "original_material_index",
        "compound_name",
        "cas",
        "formula",
        "SMILES",
        "smiles",
        "pubchem_cid",
        "phase",
        "boiling_T_K",
        "critical_T_K",
    ]

    for col in extra_cols:
        if col in df_long.columns:
            df_out[col] = df_long[col].values[indices]

    return df_out


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
# 2. 读取数据
# =========================================================
df_data = pd.read_excel(input_file, sheet_name=data_sheet)
df_groups_raw = pd.read_excel(input_file, sheet_name=groups_sheet)
df_anchor = pd.read_excel(input_file, sheet_name=anchor_sheet)

print("Data_selected 行数:", len(df_data))
print("Groups_selected 物质数:", len(df_groups_raw))
print("Anchor sheet 行数:", len(df_anchor))


# =========================================================
# 3. 统一物质 ID
# =========================================================
for df in [df_data, df_groups_raw, df_anchor]:
    if material_key_col not in df.columns:
        df[material_key_col] = df.apply(build_material_key, axis=1)

    df[material_key_col] = df[material_key_col].astype(str).str.strip()


# =========================================================
# 4. 自动查找列名
# =========================================================
viscosity_col = find_first_existing_col(
    df_data,
    viscosity_col_candidates,
    required=True,
    col_type="viscosity",
)

lnvisc_col = find_first_existing_col(
    df_data,
    lnvisc_col_candidates,
    required=False,
    col_type="lnViscosity",
)

df_data[viscosity_col] = pd.to_numeric(df_data[viscosity_col], errors="coerce")

if lnvisc_col is None:
    lnvisc_col = "lnViscosity"
    df_data[lnvisc_col] = np.where(
        df_data[viscosity_col] > 0,
        np.log(df_data[viscosity_col]),
        np.nan,
    )
else:
    df_data[lnvisc_col] = pd.to_numeric(df_data[lnvisc_col], errors="coerce")

anchor_lnvisc_col = find_first_existing_col(
    df_anchor,
    anchor_lnvisc_candidates,
    required=False,
    col_type="anchor lnViscosity",
)

if anchor_lnvisc_col is None:
    anchor_visc_col = find_first_existing_col(
        df_anchor,
        anchor_viscosity_candidates,
        required=False,
        col_type="anchor viscosity",
    )

    if anchor_visc_col is None:
        raise ValueError("未找到锚点 lnViscosity 或粘度列")

    df_anchor[anchor_visc_col] = pd.to_numeric(df_anchor[anchor_visc_col], errors="coerce")

    anchor_lnvisc_col = "lnViscosity_anchor"
    df_anchor[anchor_lnvisc_col] = np.where(
        df_anchor[anchor_visc_col] > 0,
        np.log(df_anchor[anchor_visc_col]),
        np.nan,
    )
else:
    df_anchor[anchor_lnvisc_col] = pd.to_numeric(df_anchor[anchor_lnvisc_col], errors="coerce")

boiling_col = find_first_existing_col(
    df_anchor,
    boiling_col_candidates,
    required=True,
    col_type="boiling temperature",
)

df_anchor[boiling_col] = pd.to_numeric(df_anchor[boiling_col], errors="coerce")

k1_col = find_first_existing_col(
    df_anchor,
    k1_col_candidates,
    required=False,
    col_type="k1",
)

if k1_col is None:
    anchor_T_col = find_first_existing_col(
        df_anchor,
        anchor_T_candidates,
        required=False,
        col_type="anchor temperature",
    )

    if anchor_T_col is None:
        raise ValueError("无法获取 k1")

    df_anchor[anchor_T_col] = pd.to_numeric(df_anchor[anchor_T_col], errors="coerce")
    df_anchor["k1"] = df_anchor[anchor_T_col] / df_anchor[boiling_col]
    k1_col = "k1"
else:
    df_anchor[k1_col] = pd.to_numeric(df_anchor[k1_col], errors="coerce")

df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")

print(f"目标列: {lnvisc_col}")
print(f"原始粘度列: {viscosity_col}")
print(f"锚点 lnViscosity 列: {anchor_lnvisc_col}")
print(f"沸点列: {boiling_col}")
print(f"k1 列: {k1_col}")


# =========================================================
# 5. 基团列
# =========================================================
group_cols_220 = identify_group_columns(df_groups_raw, n_group_features_to_use)

for col in group_cols_220:
    df_groups_raw[col] = pd.to_numeric(df_groups_raw[col], errors="coerce").fillna(0.0)

nonzero_group_cols = [
    c for c in group_cols_220
    if not np.isclose(df_groups_raw[c].abs().sum(), 0.0)
]

removed_zero_group_cols = [
    c for c in group_cols_220
    if np.isclose(df_groups_raw[c].abs().sum(), 0.0)
]

used_group_cols = nonzero_group_cols

print(f"有效基团数: {len(used_group_cols)}")
print(f"删除全零基团数: {len(removed_zero_group_cols)}")


# =========================================================
# 6. 构造物质级 k1 映射和全局锚点模型
# =========================================================
df_material_temp = (
    df_groups_raw[[material_key_col] + used_group_cols]
    .drop_duplicates(subset=[material_key_col])
    .copy()
)

df_material_temp = df_material_temp.merge(
    df_anchor[[material_key_col, boiling_col, k1_col]],
    on=material_key_col,
    how="inner",
)

k1_median = df_material_temp[k1_col].replace([np.inf, -np.inf], np.nan).median()
df_material_temp[k1_col] = df_material_temp[k1_col].fillna(k1_median)

k1_map = df_material_temp.set_index(material_key_col)[k1_col].to_dict()

# 锚点模型训练目标：锚点表中的 lnViscosity 和沸点
anchor_true = (
    df_anchor
    .set_index(material_key_col)[[anchor_lnvisc_col, boiling_col]]
    .dropna()
)

common_materials = set(anchor_true.index) & set(df_material_temp[material_key_col])

X_global = []
y_lnv = []
y_boil = []
global_material_order = []

for m in common_materials:
    row = df_material_temp[df_material_temp[material_key_col] == m]

    if row.empty:
        continue

    X_global.append(row[used_group_cols].values[0])
    y_lnv.append(anchor_true.loc[m, anchor_lnvisc_col])
    y_boil.append(anchor_true.loc[m, boiling_col])
    global_material_order.append(m)

X_global = np.array(X_global, dtype=float)
y_lnv = np.array(y_lnv, dtype=float)
y_boil = np.array(y_boil, dtype=float)
global_material_order = np.array(global_material_order, dtype=str)

valid = (
    np.isfinite(X_global).all(axis=1)
    & np.isfinite(y_lnv)
    & np.isfinite(y_boil)
    & (y_boil > 0)
)

X_global = X_global[valid]
y_lnv = y_lnv[valid]
y_boil = y_boil[valid]
global_material_order = global_material_order[valid]

print("全局锚点子模型训练物质数:", len(y_lnv))

global_anchor_model = HistGradientBoostingRegressor(**hgb_params)
global_boiling_model = HistGradientBoostingRegressor(**hgb_params)

global_anchor_model.fit(X_global, y_lnv)
global_boiling_model.fit(X_global, y_boil)

global_anchor_pred_train = global_anchor_model.predict(X_global)
global_boiling_pred_train = global_boiling_model.predict(X_global)

df_submodel_summary = pd.DataFrame([
    {
        "submodel": "global_anchor_lnVisc_model",
        "target": anchor_lnvisc_col,
        "model_type": "HistGradientBoostingRegressor",
        "params": str(hgb_params),
        "R2": r2_score(y_lnv, global_anchor_pred_train) if len(y_lnv) > 1 else np.nan,
        "MSE": mean_squared_error(y_lnv, global_anchor_pred_train),
        "RMSE": np.sqrt(mean_squared_error(y_lnv, global_anchor_pred_train)),
        "MAE": mean_absolute_error(y_lnv, global_anchor_pred_train),
        "ARD_percent": average_relative_deviation(y_lnv, global_anchor_pred_train),
    },
    {
        "submodel": "global_boiling_model",
        "target": boiling_col,
        "model_type": "HistGradientBoostingRegressor",
        "params": str(hgb_params),
        "R2": r2_score(y_boil, global_boiling_pred_train) if len(y_boil) > 1 else np.nan,
        "MSE": mean_squared_error(y_boil, global_boiling_pred_train),
        "RMSE": np.sqrt(mean_squared_error(y_boil, global_boiling_pred_train)),
        "MAE": mean_absolute_error(y_boil, global_boiling_pred_train),
        "ARD_percent": average_relative_deviation(y_boil, global_boiling_pred_train),
    },
])

df_submodel_predictions = pd.DataFrame({
    material_key_col: global_material_order,
    "anchor_lnVisc_true": y_lnv,
    "anchor_lnVisc_pred": global_anchor_pred_train,
    "anchor_lnVisc_abs_error": np.abs(global_anchor_pred_train - y_lnv),
    "anchor_lnVisc_relative_error_percent": safe_relative_error_percent(y_lnv, global_anchor_pred_train),
    "anchor_eta_true": safe_exp(y_lnv),
    "anchor_eta_pred": safe_exp(global_anchor_pred_train),
    "anchor_eta_relative_error_percent": safe_relative_error_percent(safe_exp(y_lnv), safe_exp(global_anchor_pred_train)),
    "boiling_T_true": y_boil,
    "boiling_T_pred": global_boiling_pred_train,
    "boiling_T_abs_error": np.abs(global_boiling_pred_train - y_boil),
    "boiling_T_relative_error_percent": safe_relative_error_percent(y_boil, global_boiling_pred_train),
})

# 物质到基团矩阵映射
material_to_groups = {
    row[material_key_col]: row[used_group_cols].values.astype(float)
    for _, row in df_material_temp.iterrows()
}

# 计算所有可用物质的全局锚点预测
material_anchor_pred = {}
material_invT_anchor = {}
material_boiling_pred = {}

for m in df_material_temp[material_key_col].drop_duplicates().values:
    if m not in material_to_groups:
        continue

    Xm = material_to_groups[m].reshape(1, -1)

    anch = global_anchor_model.predict(Xm)[0]
    boil_pred = global_boiling_model.predict(Xm)[0]

    k1m = k1_map.get(m, np.nan)

    if np.isfinite(k1m) and np.isfinite(boil_pred) and boil_pred > 0:
        T_anch = k1m * boil_pred
        invT = 1.0 / T_anch
    else:
        invT = np.nan

    material_anchor_pred[m] = anch
    material_invT_anchor[m] = invT
    material_boiling_pred[m] = boil_pred


# =========================================================
# 7. 展开温度点数据
# =========================================================
df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
df_data[lnvisc_col] = pd.to_numeric(df_data[lnvisc_col], errors="coerce")
df_data[viscosity_col] = pd.to_numeric(df_data[viscosity_col], errors="coerce")
df_data["InvT"] = 1.0 / df_data[temp_col]

if "boiling_T_K" in df_data.columns:
    df_data = df_data.drop(columns=["boiling_T_K"])

df_long = df_data.merge(
    df_groups_raw[[material_key_col] + used_group_cols],
    on=material_key_col,
    how="inner",
)

df_long["k1_use"] = df_long[material_key_col].map(k1_map)
df_long["anchor_lnVisc_global"] = df_long[material_key_col].map(material_anchor_pred)
df_long["boiling_T_pred_global"] = df_long[material_key_col].map(material_boiling_pred)
df_long["invT_anchor_global"] = df_long[material_key_col].map(material_invT_anchor)

df_long = df_long[
    (df_long[temp_col] > 0)
    & (df_long[viscosity_col] > 0)
    & np.isfinite(df_long[lnvisc_col])
    & np.isfinite(df_long["InvT"])
    & np.isfinite(df_long["anchor_lnVisc_global"])
    & np.isfinite(df_long["invT_anchor_global"])
    & np.isfinite(df_long["k1_use"])
].copy()

df_long = df_long.reset_index(drop=True)

X_groups = df_long[used_group_cols].values.astype(float)
InvT = df_long["InvT"].values.astype(float)
y = df_long[lnvisc_col].values.astype(float)
eta_true_all = safe_exp(y)

material_keys = df_long[material_key_col].values.astype(str)
anchor_lnVisc_global = df_long["anchor_lnVisc_global"].values.astype(float)
invT_anchor_global = df_long["invT_anchor_global"].values.astype(float)

unique_materials = np.unique(material_keys)
all_sample_indices = np.arange(len(y))

print(f"总样本数: {len(y)}, 总物质数: {len(unique_materials)}")

if len(unique_materials) < n_outer_folds:
    raise ValueError(
        f"物质数 {len(unique_materials)} 小于 n_outer_folds={n_outer_folds}，无法做 5-fold。"
    )


# =========================================================
# 8. 5折交叉验证
# =========================================================
kf = KFold(
    n_splits=n_outer_folds,
    shuffle=True,
    random_state=random_state,
)

metrics_direct = []
metrics_residual = []
metrics_baseline = []
metrics_residual_model = []

fold_test_prediction_dfs = []
fold_all_data_prediction_dfs = []
fold_all_data_count_records = []

fold_info_records = []

direct_feature_importance_records = []
residual_feature_importance_records = []
baseline_param_records = []

direct_feature_names = used_group_cols + ["InvT"]
residual_feature_names = used_group_cols + ["InvT"]
baseline_feature_names = [f"{g}*(InvT-invT_anchor_global)" for g in used_group_cols]

for fold, (train_idx, test_idx) in enumerate(kf.split(unique_materials), start=1):
    print(f"\n========== Fold {fold}/{n_outer_folds} ==========")

    train_mats = unique_materials[train_idx]
    test_mats = unique_materials[test_idx]

    train_mask = np.isin(material_keys, train_mats)
    test_mask = np.isin(material_keys, test_mats)

    train_indices = np.where(train_mask)[0]
    test_indices = np.where(test_mask)[0]

    print("训练物质数:", len(train_mats))
    print("测试物质数:", len(test_mats))
    print("训练样本点数:", len(train_indices))
    print("测试样本点数:", len(test_indices))

    # -----------------------------------------------------
    # 方法A：直接 GBDT
    # -----------------------------------------------------
    X_train_A = build_direct_features(train_indices)
    y_train_A = y[train_indices]

    valid_A = (
        np.isfinite(X_train_A).all(axis=1)
        & np.isfinite(y_train_A)
    )

    model_A = GradientBoostingRegressor(**gbdt_params)
    model_A.fit(X_train_A[valid_A], y_train_A[valid_A])

    X_test_A = build_direct_features(test_indices)
    y_test = y[test_indices]

    y_pred_A_test = np.full(len(test_indices), np.nan, dtype=float)

    valid_test_A = np.isfinite(X_test_A).all(axis=1)

    if valid_test_A.sum() > 0:
        y_pred_A_test[valid_test_A] = model_A.predict(X_test_A[valid_test_A])

    X_all_A = build_direct_features(all_sample_indices)
    y_pred_A_all = np.full(len(all_sample_indices), np.nan, dtype=float)

    valid_all_A = np.isfinite(X_all_A).all(axis=1)

    if valid_all_A.sum() > 0:
        y_pred_A_all[valid_all_A] = model_A.predict(X_all_A[valid_all_A])

    # -----------------------------------------------------
    # 方法B：全局锚点 baseline + residual GBDT
    # -----------------------------------------------------
    base_model, res_model = train_methodB(train_indices)

    y_pred_B_test, baseline_B_test, residual_B_test = predict_methodB(
        test_indices,
        base_model,
        res_model,
    )

    y_pred_B_all, baseline_B_all, residual_B_all = predict_methodB(
        all_sample_indices,
        base_model,
        res_model,
    )

    # -----------------------------------------------------
    # 测试集评价
    # -----------------------------------------------------
    m_A = compute_metrics(y_test, y_pred_A_test)
    m_B = compute_metrics(y_test, y_pred_B_test)
    m_baseline = compute_metrics(y_test, baseline_B_test)

    residual_target_test = y_test - baseline_B_test
    m_residual_model = compute_metrics(residual_target_test, residual_B_test)

    m_A["fold"] = fold
    m_B["fold"] = fold
    m_baseline["fold"] = fold
    m_residual_model["fold"] = fold

    metrics_direct.append(m_A)
    metrics_residual.append(m_B)
    metrics_baseline.append(m_baseline)
    metrics_residual_model.append(m_residual_model)

    print(
        "  Direct GBDT       - "
        f"R2_ln={m_A['R2_ln']:.4f}, "
        f"MSE_ln={m_A['MSE_ln']:.6f}, "
        f"RMSE_ln={m_A['RMSE_ln']:.6f}, "
        f"MAE_ln={m_A['MAE_ln']:.6f}, "
        f"ARD_vis={m_A['ARD_vis_percent']:.2f}%"
    )

    print(
        "  Anchor+Residual   - "
        f"R2_ln={m_B['R2_ln']:.4f}, "
        f"MSE_ln={m_B['MSE_ln']:.6f}, "
        f"RMSE_ln={m_B['RMSE_ln']:.6f}, "
        f"MAE_ln={m_B['MAE_ln']:.6f}, "
        f"ARD_vis={m_B['ARD_vis_percent']:.2f}%"
    )

    print(
        "  Baseline only     - "
        f"R2_ln={m_baseline['R2_ln']:.4f}, "
        f"MSE_ln={m_baseline['MSE_ln']:.6f}, "
        f"RMSE_ln={m_baseline['RMSE_ln']:.6f}, "
        f"MAE_ln={m_baseline['MAE_ln']:.6f}, "
        f"ARD_vis={m_baseline['ARD_vis_percent']:.2f}%"
    )

    # -----------------------------------------------------
    # 新增：每个 fold 模型预测完整数据集，统计完整数据集偏差数量
    # 最终复制输出使用 eta 空间，同时保存 lnVisc 空间。
    # -----------------------------------------------------
    count_A_all_eta = count_error_thresholds(
        eta_true_all,
        safe_exp(y_pred_A_all),
    )

    count_B_all_eta = count_error_thresholds(
        eta_true_all,
        safe_exp(y_pred_B_all),
    )

    count_A_all_ln = count_error_thresholds(
        y,
        y_pred_A_all,
    )

    count_B_all_ln = count_error_thresholds(
        y,
        y_pred_B_all,
    )

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "GBDT_direct_groups_InvT",
        "count_space": "eta",
        **count_A_all_eta,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "Global_anchor_linear_baseline_plus_GBDT_residual",
        "count_space": "eta",
        **count_B_all_eta,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "GBDT_direct_groups_InvT",
        "count_space": "lnVisc",
        **count_A_all_ln,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "Global_anchor_linear_baseline_plus_GBDT_residual",
        "count_space": "lnVisc",
        **count_B_all_ln,
    })

    print("\nDirect GBDT fold model predicts ALL data count summary in eta space:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "GBDT_direct_groups_InvT",
        "count_space": "eta",
        **count_A_all_eta,
    }]).to_string(index=False))

    print("\nGlobal anchor+residual fold model predicts ALL data count summary in eta space:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "Global_anchor_linear_baseline_plus_GBDT_residual",
        "count_space": "eta",
        **count_B_all_eta,
    }]).to_string(index=False))

    # -----------------------------------------------------
    # 保存测试集预测明细
    # -----------------------------------------------------
    df_test_A = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="GBDT_direct_groups_InvT",
        indices=test_indices,
        y_pred_ln=y_pred_A_test,
    )

    df_test_B = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="Global_anchor_linear_baseline_plus_GBDT_residual",
        indices=test_indices,
        y_pred_ln=y_pred_B_test,
        baseline_pred=baseline_B_test,
        residual_pred=residual_B_test,
    )

    fold_test_prediction_dfs.append(df_test_A)
    fold_test_prediction_dfs.append(df_test_B)

    # -----------------------------------------------------
    # 保存完整数据集预测明细
    # -----------------------------------------------------
    df_all_A = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="GBDT_direct_groups_InvT",
        indices=all_sample_indices,
        y_pred_ln=y_pred_A_all,
    )

    df_all_B = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="Global_anchor_linear_baseline_plus_GBDT_residual",
        indices=all_sample_indices,
        y_pred_ln=y_pred_B_all,
        baseline_pred=baseline_B_all,
        residual_pred=residual_B_all,
    )

    fold_all_data_prediction_dfs.append(df_all_A)
    fold_all_data_prediction_dfs.append(df_all_B)

    # -----------------------------------------------------
    # 保存特征重要性 / 参数
    # -----------------------------------------------------
    if hasattr(model_A, "feature_importances_"):
        for fname, imp in zip(direct_feature_names, model_A.feature_importances_):
            direct_feature_importance_records.append({
                "fold": fold,
                "feature": fname,
                "importance": imp,
            })

    if res_model is not None and hasattr(res_model, "feature_importances_"):
        for fname, imp in zip(residual_feature_names, res_model.feature_importances_):
            residual_feature_importance_records.append({
                "fold": fold,
                "feature": fname,
                "importance": imp,
            })

    if base_model is not None and hasattr(base_model, "coef_"):
        for fname, coef in zip(baseline_feature_names, base_model.coef_):
            baseline_param_records.append({
                "fold": fold,
                "feature": fname,
                "baseline_coef": coef,
                "abs_baseline_coef": abs(coef),
                "ridge_alpha": baseline_ridge_alpha,
            })

    fold_info_records.append({
        "fold": fold,
        "n_train_materials": len(train_mats),
        "n_test_materials": len(test_mats),
        "n_train_points": len(train_indices),
        "n_test_points": len(test_indices),
        "n_all_points": len(all_sample_indices),
        "n_group_features": len(used_group_cols),
        "direct_n_features": len(direct_feature_names),
        "baseline_n_features": len(baseline_feature_names),
        "residual_n_features": len(residual_feature_names),
        "baseline_model_trained": base_model is not None,
        "residual_model_trained": res_model is not None,
        "anchor_model_training": "global_all_materials",
    })


# =========================================================
# 9. 汇总统计
# =========================================================
df_A = pd.DataFrame(metrics_direct)
df_B = pd.DataFrame(metrics_residual)
df_baseline = pd.DataFrame(metrics_baseline)
df_residual_model = pd.DataFrame(metrics_residual_model)

df_A = df_A[["fold"] + [c for c in df_A.columns if c != "fold"]]
df_B = df_B[["fold"] + [c for c in df_B.columns if c != "fold"]]
df_baseline = df_baseline[["fold"] + [c for c in df_baseline.columns if c != "fold"]]
df_residual_model = df_residual_model[["fold"] + [c for c in df_residual_model.columns if c != "fold"]]

summary_A = summarize(df_A, "GBDT_direct (groups+1/T)")
summary_B = summarize(df_B, "Anchor+linear+GBDT_residual (global anchor)")
summary_baseline = summarize(df_baseline, "Baseline only (global anchor)")
summary_residual_model = summarize(df_residual_model, "Residual model")

summary_all = pd.concat(
    [
        summary_A,
        summary_B,
        summary_baseline,
        summary_residual_model,
    ],
    ignore_index=True,
)

print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
print(summary_all.to_string(index=False))


# =========================================================
# 10. 配对 t 检验
# =========================================================
metric_names = [c for c in df_A.columns if c != "fold"]

t_test_results = []

for metric in metric_names:
    vals_A = df_A[metric].values.astype(float)
    vals_B = df_B[metric].values.astype(float)

    valid = np.isfinite(vals_A) & np.isfinite(vals_B)

    vals_A_valid = vals_A[valid]
    vals_B_valid = vals_B[valid]

    if len(vals_A_valid) > 1:
        t_stat, p_val = ttest_rel(vals_A_valid, vals_B_valid)

        if metric.startswith("R2") or metric in ["leq1%", "leq5%", "leq10%"]:
            better = "methodB" if np.mean(vals_B_valid) > np.mean(vals_A_valid) else "methodA"
        else:
            better = "methodB" if np.mean(vals_B_valid) < np.mean(vals_A_valid) else "methodA"

        t_test_results.append({
            "Metric": metric,
            "Mean_direct": f"{np.mean(vals_A_valid):.4f}",
            "Mean_residual": f"{np.mean(vals_B_valid):.4f}",
            "p-value": f"{p_val:.4e}",
            "Significant(p<0.05)": p_val < 0.05,
            "Better model": better,
            "n_valid_fold_pairs": len(vals_A_valid),
        })

    else:
        t_test_results.append({
            "Metric": metric,
            "Mean_direct": np.nan,
            "Mean_residual": np.nan,
            "p-value": np.nan,
            "Significant(p<0.05)": False,
            "Better model": "N/A",
            "n_valid_fold_pairs": len(vals_A_valid),
        })

df_ttest = pd.DataFrame(t_test_results)

print("\n========== Paired t-test ==========")
print(df_ttest.to_string(index=False))


# =========================================================
# 11. 完整数据集偏差数量统计汇总
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
# 12. 整理输出表
# =========================================================
df_fold_test_predictions = pd.concat(fold_test_prediction_dfs, ignore_index=True)
df_fold_all_data_predictions = pd.concat(fold_all_data_prediction_dfs, ignore_index=True)

df_fold_info = pd.DataFrame(fold_info_records)

df_direct_feature_importance = pd.DataFrame(direct_feature_importance_records)
df_residual_feature_importance = pd.DataFrame(residual_feature_importance_records)
df_baseline_params = pd.DataFrame(baseline_param_records)

df_used_groups = pd.DataFrame({
    "used_group": used_group_cols,
    "occurrence_all_materials": (df_groups_raw[used_group_cols] != 0).sum(axis=0).values,
    "total_count_all": df_groups_raw[used_group_cols].sum(axis=0).values,
})

df_removed_zero_groups = pd.DataFrame({
    "removed_zero_group": removed_zero_group_cols,
})

df_anchor_global_info = pd.DataFrame([
    {
        material_key_col: m,
        "k1_use": k1_map.get(m, np.nan),
        "anchor_lnVisc_global": material_anchor_pred.get(m, np.nan),
        "anchor_eta_global": safe_exp(material_anchor_pred.get(m, np.nan)) if np.isfinite(material_anchor_pred.get(m, np.nan)) else np.nan,
        "boiling_T_pred_global": material_boiling_pred.get(m, np.nan),
        "invT_anchor_global": material_invT_anchor.get(m, np.nan),
        "T_anchor_global": 1.0 / material_invT_anchor.get(m, np.nan)
        if np.isfinite(material_invT_anchor.get(m, np.nan)) and material_invT_anchor.get(m, np.nan) != 0
        else np.nan,
    }
    for m in df_material_temp[material_key_col].drop_duplicates().values
])

df_run_info = pd.DataFrame([
    {"param": "input_file", "value": str(input_file)},
    {"param": "data_sheet", "value": data_sheet},
    {"param": "groups_sheet", "value": groups_sheet},
    {"param": "anchor_sheet", "value": anchor_sheet},
    {"param": "viscosity_col", "value": viscosity_col},
    {"param": "lnvisc_col", "value": lnvisc_col},
    {"param": "anchor_lnvisc_col", "value": anchor_lnvisc_col},
    {"param": "boiling_col", "value": boiling_col},
    {"param": "k1_col", "value": k1_col},
    {"param": "n_outer_folds", "value": n_outer_folds},
    {"param": "random_state", "value": random_state},
    {"param": "hgb_params_global_anchor", "value": str(hgb_params)},
    {"param": "gbdt_params", "value": str(gbdt_params)},
    {"param": "baseline_ridge_alpha", "value": baseline_ridge_alpha},
    {"param": "anchor_model_training", "value": "global_all_materials"},
    {"param": "n_group_features", "value": len(used_group_cols)},
    {"param": "n_all_data_points", "value": len(y)},
    {"param": "n_materials", "value": len(unique_materials)},
    {
        "param": "relative_error_definition",
        "value": "abs((y_pred - y_true) / y_true) * 100; abs(y_true)<=1e-12 -> NaN",
    },
    {
        "param": "final_count_space",
        "value": "eta space, eta=exp(lnVisc)",
    },
    {
        "param": "full_data_count_rule",
        "value": "Each fold model predicts the whole dataset; count eta-space rel_err <1%, <5%, <10%; then average counts over 5 folds.",
    },
])

df_model_structure = pd.DataFrame([
    {
        "项目": "预测对象",
        "内容": f"液体粘度 lnη，目标列 {lnvisc_col}；最终偏差数量按 η=exp(lnη) 空间统计",
    },
    {
        "项目": "数据文件",
        "内容": str(input_file),
    },
    {
        "项目": "data sheet",
        "内容": data_sheet,
    },
    {
        "项目": "groups sheet",
        "内容": groups_sheet,
    },
    {
        "项目": "anchor sheet",
        "内容": anchor_sheet,
    },
    {
        "项目": "交叉验证方式",
        "内容": f"{n_outer_folds}-fold KFold，按 material_key 物质划分，shuffle=True，random_state={random_state}",
    },
    {
        "项目": "方法1",
        "内容": "GBDT_direct_groups_InvT：GradientBoostingRegressor 直接预测 lnη",
    },
    {
        "项目": "方法1输入特征",
        "内容": f"[Nk, 1/T]，有效基团数 {len(used_group_cols)}，总维度 {len(used_group_cols) + 1}",
    },
    {
        "项目": "方法1模型参数",
        "内容": str(gbdt_params),
    },
    {
        "项目": "方法2",
        "内容": "Global_anchor_linear_baseline_plus_GBDT_residual：全局锚点线性基线 + GBDT 残差修正",
    },
    {
        "项目": "全局锚点子模型",
        "内容": "两个 HistGradientBoostingRegressor 全局训练：一个预测 anchor lnη，一个预测 boiling_T",
    },
    {
        "项目": "全局锚点子模型参数",
        "内容": str(hgb_params),
    },
    {
        "项目": "全局锚点子模型输入",
        "内容": f"Nk，有效基团数 {len(used_group_cols)}",
    },
    {
        "项目": "anchor_T 构造",
        "内容": "T_anchor_global = k1 * boiling_T_pred_global；invT_anchor_global = 1 / T_anchor_global",
    },
    {
        "项目": "baseline 构造",
        "内容": "baseline_lnVisc = anchor_lnVisc_global + Ridge(Nk * (InvT - invT_anchor_global))",
    },
    {
        "项目": "baseline 模型",
        "内容": f"Ridge(alpha={baseline_ridge_alpha}, fit_intercept=False)",
    },
    {
        "项目": "residual 构造",
        "内容": "residual_y = lnVisc_true - baseline_lnVisc；residual_pred = GBDT([Nk, InvT])",
    },
    {
        "项目": "residual 模型参数",
        "内容": str(gbdt_params),
    },
    {
        "项目": "最终模型",
        "内容": "方法1为直接 GBDT；方法2为 global anchor baseline + residual GBDT",
    },
    {
        "项目": "偏差数量统计口径",
        "内容": "每个 fold 训练出的最终模型预测完整数据集，在 η=exp(lnη) 空间统计相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 取平均",
    },
])


# =========================================================
# 13. 保存结果
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_A.to_excel(writer, sheet_name="Fold_Metrics_Direct", index=False)
    df_B.to_excel(writer, sheet_name="Fold_Metrics_Residual", index=False)
    summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
    df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)

    df_baseline.to_excel(writer, sheet_name="Baseline_Metrics", index=False)
    df_residual_model.to_excel(writer, sheet_name="Residual_Model_Metrics", index=False)

    df_fold_test_predictions.to_excel(writer, sheet_name="fold_test_predictions", index=False)
    df_fold_all_data_predictions.to_excel(writer, sheet_name="fold_all_data_predictions", index=False)
    df_fold_all_data_count_summary.to_excel(writer, sheet_name="fold_all_data_count_summary", index=False)
    df_final_average_summary.to_excel(writer, sheet_name="final_average_summary", index=False)

    df_submodel_summary.to_excel(writer, sheet_name="submodel_summary", index=False)
    df_submodel_predictions.to_excel(writer, sheet_name="submodel_predictions", index=False)
    df_anchor_global_info.to_excel(writer, sheet_name="global_anchor_info", index=False)

    df_baseline_params.to_excel(writer, sheet_name="baseline_params", index=False)
    df_direct_feature_importance.to_excel(writer, sheet_name="direct_feature_importance", index=False)
    df_residual_feature_importance.to_excel(writer, sheet_name="residual_feature_importance", index=False)

    df_fold_info.to_excel(writer, sheet_name="Fold_Info", index=False)
    df_used_groups.to_excel(writer, sheet_name="Used_Groups", index=False)
    df_removed_zero_groups.to_excel(writer, sheet_name="Removed_Zero_Groups", index=False)

    df_run_info.to_excel(writer, sheet_name="Run_Info", index=False)
    df_model_structure.to_excel(writer, sheet_name="model_structure", index=False)

    format_excel(writer)

print(f"\n保存完成: {output_file}")


# =========================================================
# 14. 最终方便复制输出
# =========================================================
def get_final_counts(method_name, count_space="eta"):
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


direct_1, direct_5, direct_10 = get_final_counts(
    "GBDT_direct_groups_InvT",
    count_space="eta",
)

residual_1, residual_5, residual_10 = get_final_counts(
    "Global_anchor_linear_baseline_plus_GBDT_residual",
    count_space="eta",
)

print("\n方法1 全数据预测偏差 1%，5%，10%分别为：")
print(direct_1)
print(direct_5)
print(direct_10)

print("\n方法2 全数据预测偏差 1%，5%，10%分别为：")
print(residual_1)
print(residual_5)
print(residual_10)


# =========================================================
# 15. 代码结构打印
# =========================================================
print("\n========== 当前代码结构简要汇总 ==========")
print(f"预测对象：液体粘度 lnη / {lnvisc_col}，最终偏差数量按 η=exp(lnη) 空间统计")
print(f"数据文件：{input_file}")
print(f"sheet 名称：{data_sheet}, {groups_sheet}, {anchor_sheet}")
print(f"交叉验证：{n_outer_folds}-fold KFold，按 material_key 物质划分")
print("方法1：GBDT_direct_groups_InvT，GradientBoostingRegressor，输入 [Nk, 1/T]")
print("方法2：Global_anchor_linear_baseline_plus_GBDT_residual，全局锚点线性基线 + GBDT 残差修正")
print("锚点子模型：全局 HistGradientBoostingRegressor，分别预测 anchor lnη 和 boiling_T")
print(f"锚点子模型参数：{hgb_params}")
print("anchor_T 构造：T_anchor_global = k1 * boiling_T_pred_global；invT_anchor_global = 1/T_anchor_global")
print("baseline 构造：baseline_lnVisc = anchor_lnVisc_global + Ridge(Nk*(InvT-invT_anchor_global))")
print(f"baseline 模型：Ridge(alpha={baseline_ridge_alpha}, fit_intercept=False)")
print("residual 构造：residual_y = lnVisc_true - baseline_lnVisc")
print(f"residual 模型：GradientBoostingRegressor，参数：{gbdt_params}")
print(f"方法1模型参数：{gbdt_params}")
print("方法1最终输入：[Nk, 1/T]")
print("方法2最终输入：baseline 使用 Nk*(InvT-invT_anchor_global)，residual 使用 [Nk, 1/T]")
print("偏差统计口径：每个 fold 模型预测完整数据集，在 η=exp(lnη) 空间统计 <1%、<5%、<10% 点数，再对 5 个 fold 取平均")