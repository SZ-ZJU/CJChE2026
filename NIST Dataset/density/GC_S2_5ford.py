# # import pandas as pd
# # import numpy as np
# # from pathlib import Path
# #
# # from sklearn.linear_model import Ridge
# # from sklearn.model_selection import GroupKFold
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
# # # 1. 输入输出设置
# # # =========================================================
# # main_input_file = Path("dataset_density_selected_by_two_k_with_density_T_interpolation_8points.xlsx")
# # data_sheet = "Data_selected"
# # groups_sheet = "Groups_selected"
# # anchor_sheet_candidates = ["Interpolated_k1_k2", "Final_Model_Table", "Material_selected"]
# # output_file = Path("Density_baseline_comparison.xlsx")
# #
# # material_key_col = "material_key"
# # temp_col = "T_K"
# # density_col_candidates = ["property_value", "value", "Density_kg_m3", "density_kg_m3", "rho_kg_m3", "rho", "density", "Density"]
# # anchor_temp_col_candidates = ["k1_times_boiling_T_K", "ref_T1_K", "reference_T1_K", "T_ref1_K", "T_anchor", "anchor_T", "anchor_T_ref1", "T_k1", "T1_K", "ref_T_K"]
# # anchor_density_col_candidates = ["property_interp_at_k1Tb", "density_interp_at_k1Tb", "Density_interp_at_k1Tb", "density_ref1", "Density_ref1", "ref_density_1", "rho_ref1", "property_ref1", "anchor_density", "anchor_value", "anchor_rho", "density_at_ref_T1", "Density_at_ref_T1", "density_ref_T1"]
# #
# # n_group_features_to_use = 220
# # use_fixed_group_position = True
# # group_start_col_1based = 3
# # group_end_col_1based = 222
# #
# # n_outer_folds = 5
# # random_state = 42
# # ridge_alpha = 1.0   # 统一的 Ridge 正则化强度
# #
# # # =========================================================
# # # 2. 工具函数（复用原有代码）
# # # =========================================================
# # def is_valid_value(x):
# #     if pd.isna(x): return False
# #     s = str(x).strip()
# #     if s == "" or s.lower() in ["nan","none","null","待定"]: return False
# #     return True
# #
# # def clean_key_value(x):
# #     if not is_valid_value(x): return np.nan
# #     s = str(x).strip()
# #     try:
# #         f = float(s)
# #         if np.isfinite(f) and abs(f - round(f)) < 1e-8:
# #             return str(int(round(f)))
# #     except Exception:
# #         pass
# #     return s
# #
# # def build_material_key(row):
# #     for col in ["material_key", "original_material_index", "inchikey", "InChIKey", "inchi_key",
# #                 "pubchem_inchikey", "PubChem_InChIKey", "cas", "compound_name", "formula"]:
# #         if col in row.index and is_valid_value(row[col]):
# #             if col == "material_key":
# #                 return clean_key_value(row[col])
# #             return f"{col}:{str(row[col]).strip()}"
# #     return "unknown_material"
# #
# # def normalize_colname(name):
# #     return str(name).lower().replace(" ", "").replace("_", "").replace("-", "").replace("/", "").replace("(", "").replace(")", "")
# #
# # def find_first_existing_col(df, candidates, col_type, required=True):
# #     for col in candidates:
# #         if col in df.columns: return col
# #     norm_map = {normalize_colname(c): c for c in df.columns}
# #     for col in candidates:
# #         key = normalize_colname(col)
# #         if key in norm_map: return norm_map[key]
# #     if required:
# #         raise ValueError(f"没有找到 {col_type} 列。候选: {candidates}")
# #     return None
# #
# # def identify_group_columns(df_groups, n=220):
# #     if use_fixed_group_position:
# #         start_idx = group_start_col_1based - 1
# #         end_excl = group_end_col_1based
# #         if len(df_groups.columns) < end_excl:
# #             raise ValueError(f"列数不足，需要到第 {group_end_col_1based} 列")
# #         group_cols = list(df_groups.columns[start_idx:end_excl])
# #         if len(group_cols) != n:
# #             raise ValueError(f"固定位置识别到 {len(group_cols)} 个基团，需要 {n}")
# #         return group_cols
# #     # 自动识别分支（略，用户已使用固定位置）
# #     raise ValueError("请设置 use_fixed_group_position=True")
# #
# # def average_relative_deviation(y_true, y_pred, eps=1e-12):
# #     y_true = np.asarray(y_true, dtype=float)
# #     y_pred = np.asarray(y_pred, dtype=float)
# #     mask = np.isfinite(y_true) & np.isfinite(y_pred) & (np.abs(y_true) > eps)
# #     if mask.sum() == 0:
# #         return np.nan
# #     return np.mean(np.abs((y_pred[mask] - y_true[mask]) / y_true[mask])) * 100.0
# #
# # def evaluate_metrics(y_true, y_pred):
# #     mask = np.isfinite(y_true) & np.isfinite(y_pred)
# #     y_true = y_true[mask]
# #     y_pred = y_pred[mask]
# #     if len(y_true) == 0:
# #         return {"R2": np.nan, "MSE": np.nan, "RMSE": np.nan, "MAE": np.nan, "ARD": np.nan}
# #     r2 = r2_score(y_true, y_pred)
# #     mse = mean_squared_error(y_true, y_pred)
# #     rmse = np.sqrt(mse)
# #     mae = mean_absolute_error(y_true, y_pred)
# #     ard = average_relative_deviation(y_true, y_pred)
# #     return {"R2": r2, "MSE": mse, "RMSE": rmse, "MAE": mae, "ARD": ard}
# #
# # # =========================================================
# # # 3. 读取数据与预处理（与原代码完全一致）
# # # =========================================================
# # xls_main = pd.ExcelFile(main_input_file)
# # if data_sheet not in xls_main.sheet_names or groups_sheet not in xls_main.sheet_names:
# #     raise ValueError("缺少必需 sheet")
# # anchor_sheet = None
# # for s in anchor_sheet_candidates:
# #     if s in xls_main.sheet_names:
# #         anchor_sheet = s
# #         break
# # if anchor_sheet is None:
# #     raise ValueError(f"没有找到锚点 sheet，候选: {anchor_sheet_candidates}")
# #
# # df_data = pd.read_excel(main_input_file, sheet_name=data_sheet)
# # df_groups = pd.read_excel(main_input_file, sheet_name=groups_sheet)
# # df_anchor = pd.read_excel(main_input_file, sheet_name=anchor_sheet)
# #
# # # 构造 material_key
# # for df in [df_data, df_groups, df_anchor]:
# #     if material_key_col not in df.columns:
# #         df[material_key_col] = df.apply(build_material_key, axis=1)
# #     df[material_key_col] = df[material_key_col].apply(clean_key_value)
# #
# # # 找到所需列
# # density_col = find_first_existing_col(df_data, density_col_candidates, "密度", required=True)
# # if temp_col not in df_data.columns:
# #     raise ValueError("没有找到温度列")
# # anchor_temp_col = find_first_existing_col(df_anchor, anchor_temp_col_candidates, "锚点温度", required=True)
# # anchor_density_col = find_first_existing_col(df_anchor, anchor_density_col_candidates, "锚点密度", required=True)
# #
# # df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
# # df_data[density_col] = pd.to_numeric(df_data[density_col], errors="coerce")
# # df_anchor[anchor_temp_col] = pd.to_numeric(df_anchor[anchor_temp_col], errors="coerce")
# # df_anchor[anchor_density_col] = pd.to_numeric(df_anchor[anchor_density_col], errors="coerce")
# #
# # # 基团列处理
# # group_cols_220 = identify_group_columns(df_groups, n_group_features_to_use)
# # df_groups_numeric = df_groups[group_cols_220].apply(pd.to_numeric, errors="coerce").fillna(0.0)
# # nonzero_mask = df_groups_numeric.abs().sum(axis=0) != 0
# # used_group_cols = df_groups_numeric.columns[nonzero_mask].tolist()
# # print(f"有效基团数: {len(used_group_cols)}")
# #
# # # 合并锚点信息（每个物质一个锚点）
# # anchor_info = df_anchor[[material_key_col, anchor_temp_col, anchor_density_col]].drop_duplicates()
# # anchor_info = anchor_info.rename(columns={anchor_temp_col: "anchor_T", anchor_density_col: "anchor_rho"})
# #
# # # 合并基团和锚点
# # df_long = df_data.merge(df_groups[[material_key_col] + used_group_cols], on=material_key_col, how="inner")
# # df_long = df_long.merge(anchor_info, on=material_key_col, how="inner")
# # df_long = df_long.dropna(subset=[temp_col, density_col] + used_group_cols + ["anchor_T", "anchor_rho"])
# # df_long = df_long[(df_long[temp_col] > 0) & (df_long[density_col] > 0)].copy()
# # df_long = df_long.reset_index(drop=True)
# #
# # # 提取数组
# # X_groups = df_long[used_group_cols].values.astype(float)
# # T = df_long[temp_col].values.astype(float)
# # rho_true = df_long[density_col].values.astype(float)
# # anchor_T = df_long["anchor_T"].values.astype(float)
# # anchor_rho = df_long["anchor_rho"].values.astype(float)
# # material_keys = df_long[material_key_col].values
# #
# # unique_materials = np.unique(material_keys)
# # print(f"总样本数: {len(rho_true)}, 总物质数: {len(unique_materials)}")
# #
# # # =========================================================
# # # 4. 为二阶拟合基线准备每个物质的真实系数 (A, B, C)
# # # =========================================================
# # material_to_ABC = {}
# # for mat in unique_materials:
# #     mask = material_keys == mat
# #     T_mat = T[mask]
# #     rho_mat = rho_true[mask]
# #     if len(T_mat) >= 3:
# #         coeff = np.polyfit(T_mat, rho_mat, 2)   # 返回 [C, B, A]
# #         C, B, A = coeff[0], coeff[1], coeff[2]
# #         material_to_ABC[mat] = (A, B, C)
# #     else:
# #         material_to_ABC[mat] = (np.nan, np.nan, np.nan)
# #
# # # =========================================================
# # # 5. 5 折交叉验证（按物质分组）
# # # =========================================================
# # gkf = GroupKFold(n_splits=n_outer_folds)
# # metrics_anchor = []   # 锚点线性基线
# # metrics_quad = []     # 二阶温度拟合基线
# #
# # for fold, (train_mat_idx, test_mat_idx) in enumerate(gkf.split(unique_materials, groups=unique_materials)):
# #     train_mats = unique_materials[train_mat_idx]
# #     test_mats = unique_materials[test_mat_idx]
# #
# #     train_mask = np.isin(material_keys, train_mats)
# #     test_mask = np.isin(material_keys, test_mats)
# #
# #     # ---------- 锚点线性基线 ----------
# #     delta_T_train = T[train_mask] - anchor_T[train_mask]
# #     X_base_train = X_groups[train_mask] * delta_T_train.reshape(-1, 1)
# #     y_base_train = rho_true[train_mask] - anchor_rho[train_mask]
# #     valid_base = np.isfinite(X_base_train).all(axis=1) & np.isfinite(y_base_train)
# #     if valid_base.sum() == 0:
# #         y_pred_anchor = np.full(rho_true[test_mask].shape, np.nan)
# #     else:
# #         base_model = Ridge(alpha=ridge_alpha, fit_intercept=False)
# #         base_model.fit(X_base_train[valid_base], y_base_train[valid_base])
# #         delta_T_test = T[test_mask] - anchor_T[test_mask]
# #         X_base_test = X_groups[test_mask] * delta_T_test.reshape(-1, 1)
# #         valid_test = np.isfinite(X_base_test).all(axis=1)
# #         baseline_delta = np.full(len(rho_true[test_mask]), np.nan)
# #         baseline_delta[valid_test] = base_model.predict(X_base_test[valid_test])
# #         y_pred_anchor = anchor_rho[test_mask] + baseline_delta
# #
# #     # ---------- 二阶拟合基线 ----------
# #     train_ABC = []
# #     train_X = []
# #     for mat in train_mats:
# #         if mat in material_to_ABC and not np.isnan(material_to_ABC[mat][0]):
# #             train_ABC.append(material_to_ABC[mat])
# #             idx = np.where(material_keys == mat)[0][0]
# #             train_X.append(X_groups[idx])
# #     if len(train_ABC) == 0:
# #         y_pred_quad = np.full(rho_true[test_mask].shape, np.nan)
# #     else:
# #         train_X = np.array(train_X)
# #         train_A = np.array([abc[0] for abc in train_ABC])
# #         train_B = np.array([abc[1] for abc in train_ABC])
# #         train_C = np.array([abc[2] for abc in train_ABC])
# #
# #         # 使用 Ridge 分别预测 A, B, C（带截距，alpha 相同）
# #         model_A = Ridge(alpha=ridge_alpha, fit_intercept=True)
# #         model_B = Ridge(alpha=ridge_alpha, fit_intercept=True)
# #         model_C = Ridge(alpha=ridge_alpha, fit_intercept=True)
# #         model_A.fit(train_X, train_A)
# #         model_B.fit(train_X, train_B)
# #         model_C.fit(train_X, train_C)
# #
# #         # 预测测试集物质的系数
# #         test_X = []
# #         for mat in test_mats:
# #             idx = np.where(material_keys == mat)[0][0]
# #             test_X.append(X_groups[idx])
# #         test_X = np.array(test_X)
# #         A_pred = model_A.predict(test_X)
# #         B_pred = model_B.predict(test_X)
# #         C_pred = model_C.predict(test_X)
# #
# #         # 计算测试集每个温度点的预测值
# #         y_pred_quad = np.zeros(len(rho_true[test_mask])) * np.nan
# #         for i, mat in enumerate(test_mats):
# #             sub_mask = material_keys[test_mask] == mat
# #             T_sub = T[test_mask][sub_mask]
# #             pred_vals = A_pred[i] + B_pred[i] * T_sub + C_pred[i] * (T_sub ** 2)
# #             y_pred_quad[sub_mask] = pred_vals
# #
# #     # 计算指标
# #     y_true_test = rho_true[test_mask]
# #     met_anchor = evaluate_metrics(y_true_test, y_pred_anchor)
# #     met_quad = evaluate_metrics(y_true_test, y_pred_quad)
# #     met_anchor["fold"] = fold+1
# #     met_quad["fold"] = fold+1
# #     metrics_anchor.append(met_anchor)
# #     metrics_quad.append(met_quad)
# #
# #     print(f"\nFold {fold+1}:")
# #     print(f"  锚点线性基线     - R2={met_anchor['R2']:.4f}, RMSE={met_anchor['RMSE']:.4f}, MAE={met_anchor['MAE']:.4f}, ARD={met_anchor['ARD']:.2f}%")
# #     print(f"  二阶拟合基线     - R2={met_quad['R2']:.4f}, RMSE={met_quad['RMSE']:.4f}, MAE={met_quad['MAE']:.4f}, ARD={met_quad['ARD']:.2f}%")
# #
# # # =========================================================
# # # 6. 汇总统计与配对 t 检验
# # # =========================================================
# # df_anchor = pd.DataFrame(metrics_anchor)
# # df_quad = pd.DataFrame(metrics_quad)
# #
# # def summarize(df, name):
# #     rows = []
# #     for metric in ["R2", "MSE", "RMSE", "MAE", "ARD"]:
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
# # summary_anchor = summarize(df_anchor, "Anchor linear baseline")
# # summary_quad = summarize(df_quad, "Quadratic baseline (ρ=A+BT+CT²)")
# # summary_all = pd.concat([summary_anchor, summary_quad], ignore_index=True)
# #
# # print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
# # print(summary_all.to_string(index=False))
# #
# # # 配对 t 检验
# # t_test_results = []
# # for metric in ["R2", "MSE", "RMSE", "MAE", "ARD"]:
# #     vals_anc = df_anchor[metric].dropna().values
# #     vals_quad = df_quad[metric].dropna().values
# #     if len(vals_anc) == len(vals_quad) and len(vals_anc) > 1:
# #         t_stat, p_val = ttest_rel(vals_anc, vals_quad)
# #         if metric == "R2":
# #             better = "quadratic" if np.mean(vals_quad) > np.mean(vals_anc) else "anchor"
# #             sig = p_val < 0.05
# #         else:
# #             better = "quadratic" if np.mean(vals_quad) < np.mean(vals_anc) else "anchor"
# #             sig = p_val < 0.05
# #         t_test_results.append({
# #             "Metric": metric,
# #             "Mean_anchor": f"{np.mean(vals_anc):.4f}",
# #             "Mean_quadratic": f"{np.mean(vals_quad):.4f}",
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
# # # 7. 保存结果到 Excel
# # # =========================================================
# # with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
# #     df_anchor.to_excel(writer, sheet_name="Fold_Metrics_Anchor", index=False)
# #     df_quad.to_excel(writer, sheet_name="Fold_Metrics_Quadratic", index=False)
# #     summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
# #     df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)
# #     pd.DataFrame([
# #         {"param": "n_outer_folds", "value": n_outer_folds},
# #         {"param": "random_state", "value": random_state},
# #         {"param": "ridge_alpha", "value": ridge_alpha},
# #         {"param": "anchor_definition", "value": "k1 * Tb (from Interpolated_k1_k2)"},
# #         {"param": "quadratic_model", "value": "ρ = A + B·T + C·T²"},
# #     ]).to_excel(writer, sheet_name="Run_Info", index=False)
# #
# # print(f"\n结果已保存至: {output_file}")
#
#
# import pandas as pd
# import numpy as np
# from pathlib import Path
#
# from sklearn.linear_model import Ridge
# from sklearn.model_selection import GroupKFold
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
# # 1. 输入输出设置
# # =========================================================
# main_input_file = Path("dataset_density_selected_by_two_k_with_density_T_interpolation_8points.xlsx")
# data_sheet = "Data_selected"
# groups_sheet = "Groups_selected"
# anchor_sheet_candidates = ["Interpolated_k1_k2", "Final_Model_Table", "Material_selected"]
# output_file = Path("Density_baseline_comparison_linear.xlsx")
#
# material_key_col = "material_key"
# temp_col = "T_K"
# density_col_candidates = ["property_value", "value", "Density_kg_m3", "density_kg_m3", "rho_kg_m3", "rho", "density", "Density"]
# anchor_temp_col_candidates = ["k1_times_boiling_T_K", "ref_T1_K", "reference_T1_K", "T_ref1_K", "T_anchor", "anchor_T", "anchor_T_ref1", "T_k1", "T1_K", "ref_T_K"]
# anchor_density_col_candidates = ["property_interp_at_k1Tb", "density_interp_at_k1Tb", "Density_interp_at_k1Tb", "density_ref1", "Density_ref1", "ref_density_1", "rho_ref1", "property_ref1", "anchor_density", "anchor_value", "anchor_rho", "density_at_ref_T1", "Density_at_ref_T1", "density_ref_T1"]
#
# n_group_features_to_use = 220
# use_fixed_group_position = True
# group_start_col_1based = 3
# group_end_col_1based = 222
#
# n_outer_folds = 5
# random_state = 42
# ridge_alpha = 1.0   # 统一的 Ridge 正则化强度
#
# # =========================================================
# # 2. 工具函数（复用原有代码）
# # =========================================================
# def is_valid_value(x):
#     if pd.isna(x): return False
#     s = str(x).strip()
#     if s == "" or s.lower() in ["nan","none","null","待定"]: return False
#     return True
#
# def clean_key_value(x):
#     if not is_valid_value(x): return np.nan
#     s = str(x).strip()
#     try:
#         f = float(s)
#         if np.isfinite(f) and abs(f - round(f)) < 1e-8:
#             return str(int(round(f)))
#     except Exception:
#         pass
#     return s
#
# def build_material_key(row):
#     for col in ["material_key", "original_material_index", "inchikey", "InChIKey", "inchi_key",
#                 "pubchem_inchikey", "PubChem_InChIKey", "cas", "compound_name", "formula"]:
#         if col in row.index and is_valid_value(row[col]):
#             if col == "material_key":
#                 return clean_key_value(row[col])
#             return f"{col}:{str(row[col]).strip()}"
#     return "unknown_material"
#
# def normalize_colname(name):
#     return str(name).lower().replace(" ", "").replace("_", "").replace("-", "").replace("/", "").replace("(", "").replace(")", "")
#
# def find_first_existing_col(df, candidates, col_type, required=True):
#     for col in candidates:
#         if col in df.columns: return col
#     norm_map = {normalize_colname(c): c for c in df.columns}
#     for col in candidates:
#         key = normalize_colname(col)
#         if key in norm_map: return norm_map[key]
#     if required:
#         raise ValueError(f"没有找到 {col_type} 列。候选: {candidates}")
#     return None
#
# def identify_group_columns(df_groups, n=220):
#     if use_fixed_group_position:
#         start_idx = group_start_col_1based - 1
#         end_excl = group_end_col_1based
#         if len(df_groups.columns) < end_excl:
#             raise ValueError(f"列数不足，需要到第 {group_end_col_1based} 列")
#         group_cols = list(df_groups.columns[start_idx:end_excl])
#         if len(group_cols) != n:
#             raise ValueError(f"固定位置识别到 {len(group_cols)} 个基团，需要 {n}")
#         return group_cols
#     raise ValueError("请设置 use_fixed_group_position=True")
#
# def average_relative_deviation(y_true, y_pred, eps=1e-12):
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#     mask = np.isfinite(y_true) & np.isfinite(y_pred) & (np.abs(y_true) > eps)
#     if mask.sum() == 0:
#         return np.nan
#     return np.mean(np.abs((y_pred[mask] - y_true[mask]) / y_true[mask])) * 100.0
#
# def evaluate_metrics(y_true, y_pred):
#     mask = np.isfinite(y_true) & np.isfinite(y_pred)
#     y_true = y_true[mask]
#     y_pred = y_pred[mask]
#     if len(y_true) == 0:
#         return {"R2": np.nan, "MSE": np.nan, "RMSE": np.nan, "MAE": np.nan, "ARD": np.nan}
#     r2 = r2_score(y_true, y_pred)
#     mse = mean_squared_error(y_true, y_pred)
#     rmse = np.sqrt(mse)
#     mae = mean_absolute_error(y_true, y_pred)
#     ard = average_relative_deviation(y_true, y_pred)
#     return {"R2": r2, "MSE": mse, "RMSE": rmse, "MAE": mae, "ARD": ard}
#
# # =========================================================
# # 3. 读取数据与预处理（与原代码完全一致）
# # =========================================================
# xls_main = pd.ExcelFile(main_input_file)
# if data_sheet not in xls_main.sheet_names or groups_sheet not in xls_main.sheet_names:
#     raise ValueError("缺少必需 sheet")
# anchor_sheet = None
# for s in anchor_sheet_candidates:
#     if s in xls_main.sheet_names:
#         anchor_sheet = s
#         break
# if anchor_sheet is None:
#     raise ValueError(f"没有找到锚点 sheet，候选: {anchor_sheet_candidates}")
#
# df_data = pd.read_excel(main_input_file, sheet_name=data_sheet)
# df_groups = pd.read_excel(main_input_file, sheet_name=groups_sheet)
# df_anchor = pd.read_excel(main_input_file, sheet_name=anchor_sheet)
#
# # 构造 material_key
# for df in [df_data, df_groups, df_anchor]:
#     if material_key_col not in df.columns:
#         df[material_key_col] = df.apply(build_material_key, axis=1)
#     df[material_key_col] = df[material_key_col].apply(clean_key_value)
#
# # 找到所需列
# density_col = find_first_existing_col(df_data, density_col_candidates, "密度", required=True)
# if temp_col not in df_data.columns:
#     raise ValueError("没有找到温度列")
# anchor_temp_col = find_first_existing_col(df_anchor, anchor_temp_col_candidates, "锚点温度", required=True)
# anchor_density_col = find_first_existing_col(df_anchor, anchor_density_col_candidates, "锚点密度", required=True)
#
# df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
# df_data[density_col] = pd.to_numeric(df_data[density_col], errors="coerce")
# df_anchor[anchor_temp_col] = pd.to_numeric(df_anchor[anchor_temp_col], errors="coerce")
# df_anchor[anchor_density_col] = pd.to_numeric(df_anchor[anchor_density_col], errors="coerce")
#
# # 基团列处理
# group_cols_220 = identify_group_columns(df_groups, n_group_features_to_use)
# df_groups_numeric = df_groups[group_cols_220].apply(pd.to_numeric, errors="coerce").fillna(0.0)
# nonzero_mask = df_groups_numeric.abs().sum(axis=0) != 0
# used_group_cols = df_groups_numeric.columns[nonzero_mask].tolist()
# print(f"有效基团数: {len(used_group_cols)}")
#
# # 合并锚点信息（每个物质一个锚点）
# anchor_info = df_anchor[[material_key_col, anchor_temp_col, anchor_density_col]].drop_duplicates()
# anchor_info = anchor_info.rename(columns={anchor_temp_col: "anchor_T", anchor_density_col: "anchor_rho"})
#
# # 合并基团和锚点
# df_long = df_data.merge(df_groups[[material_key_col] + used_group_cols], on=material_key_col, how="inner")
# df_long = df_long.merge(anchor_info, on=material_key_col, how="inner")
# df_long = df_long.dropna(subset=[temp_col, density_col] + used_group_cols + ["anchor_T", "anchor_rho"])
# df_long = df_long[(df_long[temp_col] > 0) & (df_long[density_col] > 0)].copy()
# df_long = df_long.reset_index(drop=True)
#
# # 提取数组
# X_groups = df_long[used_group_cols].values.astype(float)
# T = df_long[temp_col].values.astype(float)
# rho_true = df_long[density_col].values.astype(float)
# anchor_T = df_long["anchor_T"].values.astype(float)
# anchor_rho = df_long["anchor_rho"].values.astype(float)
# material_keys = df_long[material_key_col].values
#
# unique_materials = np.unique(material_keys)
# print(f"总样本数: {len(rho_true)}, 总物质数: {len(unique_materials)}")
#
# # =========================================================
# # 4. 为一阶线性基线准备每个物质的真实系数 (A, B)   ρ = A + B·T
# # =========================================================
# material_to_AB = {}
# for mat in unique_materials:
#     mask = material_keys == mat
#     T_mat = T[mask]
#     rho_mat = rho_true[mask]
#     if len(T_mat) >= 2:
#         coeff = np.polyfit(T_mat, rho_mat, 1)   # 返回 [B, A]
#         B, A = coeff[0], coeff[1]
#         material_to_AB[mat] = (A, B)
#     else:
#         material_to_AB[mat] = (np.nan, np.nan)
#
# # =========================================================
# # 5. 5 折交叉验证（按物质分组）
# # =========================================================
# gkf = GroupKFold(n_splits=n_outer_folds)
# metrics_anchor = []   # 锚点线性基线
# metrics_linear = []   # 一阶线性拟合基线
#
# for fold, (train_mat_idx, test_mat_idx) in enumerate(gkf.split(unique_materials, groups=unique_materials)):
#     train_mats = unique_materials[train_mat_idx]
#     test_mats = unique_materials[test_mat_idx]
#
#     train_mask = np.isin(material_keys, train_mats)
#     test_mask = np.isin(material_keys, test_mats)
#
#     # ---------- 锚点线性基线 ----------
#     delta_T_train = T[train_mask] - anchor_T[train_mask]
#     X_base_train = X_groups[train_mask] * delta_T_train.reshape(-1, 1)
#     y_base_train = rho_true[train_mask] - anchor_rho[train_mask]
#     valid_base = np.isfinite(X_base_train).all(axis=1) & np.isfinite(y_base_train)
#     if valid_base.sum() == 0:
#         y_pred_anchor = np.full(rho_true[test_mask].shape, np.nan)
#     else:
#         base_model = Ridge(alpha=ridge_alpha, fit_intercept=False)
#         base_model.fit(X_base_train[valid_base], y_base_train[valid_base])
#         delta_T_test = T[test_mask] - anchor_T[test_mask]
#         X_base_test = X_groups[test_mask] * delta_T_test.reshape(-1, 1)
#         valid_test = np.isfinite(X_base_test).all(axis=1)
#         baseline_delta = np.full(len(rho_true[test_mask]), np.nan)
#         baseline_delta[valid_test] = base_model.predict(X_base_test[valid_test])
#         y_pred_anchor = anchor_rho[test_mask] + baseline_delta
#
#     # ---------- 一阶线性拟合基线 ----------
#     train_AB = []
#     train_X = []
#     for mat in train_mats:
#         if mat in material_to_AB and not np.isnan(material_to_AB[mat][0]):
#             train_AB.append(material_to_AB[mat])
#             idx = np.where(material_keys == mat)[0][0]
#             train_X.append(X_groups[idx])
#     if len(train_AB) == 0:
#         y_pred_linear = np.full(rho_true[test_mask].shape, np.nan)
#     else:
#         train_X = np.array(train_X)
#         train_A = np.array([ab[0] for ab in train_AB])
#         train_B = np.array([ab[1] for ab in train_AB])
#
#         # 使用 Ridge 分别预测 A 和 B（带截距）
#         model_A = Ridge(alpha=ridge_alpha, fit_intercept=True)
#         model_B = Ridge(alpha=ridge_alpha, fit_intercept=True)
#         model_A.fit(train_X, train_A)
#         model_B.fit(train_X, train_B)
#
#         # 预测测试集物质的系数
#         test_X = []
#         for mat in test_mats:
#             idx = np.where(material_keys == mat)[0][0]
#             test_X.append(X_groups[idx])
#         test_X = np.array(test_X)
#         A_pred = model_A.predict(test_X)
#         B_pred = model_B.predict(test_X)
#
#         # 计算测试集每个温度点的预测密度
#         y_pred_linear = np.zeros(len(rho_true[test_mask])) * np.nan
#         for i, mat in enumerate(test_mats):
#             sub_mask = material_keys[test_mask] == mat
#             T_sub = T[test_mask][sub_mask]
#             pred_vals = A_pred[i] + B_pred[i] * T_sub
#             y_pred_linear[sub_mask] = pred_vals
#
#     # 计算指标
#     y_true_test = rho_true[test_mask]
#     met_anchor = evaluate_metrics(y_true_test, y_pred_anchor)
#     met_linear = evaluate_metrics(y_true_test, y_pred_linear)
#     met_anchor["fold"] = fold+1
#     met_linear["fold"] = fold+1
#     metrics_anchor.append(met_anchor)
#     metrics_linear.append(met_linear)
#
#     print(f"\nFold {fold+1}:")
#     print(f"  锚点线性基线     - R2={met_anchor['R2']:.4f}, RMSE={met_anchor['RMSE']:.4f}, MAE={met_anchor['MAE']:.4f}, ARD={met_anchor['ARD']:.2f}%")
#     print(f"  一阶线性基线     - R2={met_linear['R2']:.4f}, RMSE={met_linear['RMSE']:.4f}, MAE={met_linear['MAE']:.4f}, ARD={met_linear['ARD']:.2f}%")
#
# # =========================================================
# # 6. 汇总统计与配对 t 检验
# # =========================================================
# df_anchor = pd.DataFrame(metrics_anchor)
# df_linear = pd.DataFrame(metrics_linear)
#
# def summarize(df, name):
#     rows = []
#     for metric in ["R2", "MSE", "RMSE", "MAE", "ARD"]:
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
# summary_anchor = summarize(df_anchor, "Anchor linear baseline")
# summary_linear = summarize(df_linear, "Linear baseline (ρ=A+B·T)")
# summary_all = pd.concat([summary_anchor, summary_linear], ignore_index=True)
#
# print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
# print(summary_all.to_string(index=False))
#
# # 配对 t 检验
# t_test_results = []
# for metric in ["R2", "MSE", "RMSE", "MAE", "ARD"]:
#     vals_anc = df_anchor[metric].dropna().values
#     vals_lin = df_linear[metric].dropna().values
#     if len(vals_anc) == len(vals_lin) and len(vals_anc) > 1:
#         t_stat, p_val = ttest_rel(vals_anc, vals_lin)
#         if metric == "R2":
#             better = "linear" if np.mean(vals_lin) > np.mean(vals_anc) else "anchor"
#             sig = p_val < 0.05
#         else:
#             better = "linear" if np.mean(vals_lin) < np.mean(vals_anc) else "anchor"
#             sig = p_val < 0.05
#         t_test_results.append({
#             "Metric": metric,
#             "Mean_anchor": f"{np.mean(vals_anc):.4f}",
#             "Mean_linear": f"{np.mean(vals_lin):.4f}",
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
# # 7. 保存结果到 Excel
# # =========================================================
# with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
#     df_anchor.to_excel(writer, sheet_name="Fold_Metrics_Anchor", index=False)
#     df_linear.to_excel(writer, sheet_name="Fold_Metrics_Linear", index=False)
#     summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
#     df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)
#     pd.DataFrame([
#         {"param": "n_outer_folds", "value": n_outer_folds},
#         {"param": "random_state", "value": random_state},
#         {"param": "ridge_alpha", "value": ridge_alpha},
#         {"param": "anchor_definition", "value": "k1 * Tb (from Interpolated_k1_k2)"},
#         {"param": "linear_model", "value": "ρ = A + B·T"},
#     ]).to_excel(writer, sheet_name="Run_Info", index=False)
#
# print(f"\n结果已保存至: {output_file}")


import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from scipy.stats import ttest_rel

import warnings
warnings.filterwarnings("ignore")

pd.set_option("display.float_format", "{:.10f}".format)
np.set_printoptions(suppress=True, precision=10)


# =========================================================
# 1. 输入输出设置
# =========================================================
main_input_file = Path("dataset_density_selected_by_two_k_with_density_T_interpolation_8points.xlsx")

data_sheet = "Data_selected"
groups_sheet = "Groups_selected"
anchor_sheet_candidates = ["Interpolated_k1_k2", "Final_Model_Table", "Material_selected"]

output_file = Path("Density_baseline_comparison_linear.xlsx")

material_key_col = "material_key"
temp_col = "T_K"

density_col_candidates = [
    "property_value",
    "value",
    "Density_kg_m3",
    "density_kg_m3",
    "rho_kg_m3",
    "rho",
    "density",
    "Density",
]

anchor_temp_col_candidates = [
    "k1_times_boiling_T_K",
    "ref_T1_K",
    "reference_T1_K",
    "T_ref1_K",
    "T_anchor",
    "anchor_T",
    "anchor_T_ref1",
    "T_k1",
    "T1_K",
    "ref_T_K",
]

anchor_density_col_candidates = [
    "property_interp_at_k1Tb",
    "density_interp_at_k1Tb",
    "Density_interp_at_k1Tb",
    "density_ref1",
    "Density_ref1",
    "ref_density_1",
    "rho_ref1",
    "property_ref1",
    "anchor_density",
    "anchor_value",
    "anchor_rho",
    "density_at_ref_T1",
    "Density_at_ref_T1",
    "density_ref_T1",
]

n_group_features_to_use = 220
use_fixed_group_position = True
group_start_col_1based = 3
group_end_col_1based = 222

n_outer_folds = 5
random_state = 42
ridge_alpha = 1.0


# =========================================================
# 2. 工具函数
# =========================================================
def is_valid_value(x):
    if pd.isna(x):
        return False

    s = str(x).strip()

    if s == "" or s.lower() in ["nan", "none", "null", "待定"]:
        return False

    return True


def clean_key_value(x):
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


def build_material_key(row):
    for col in [
        "material_key",
        "original_material_index",
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
                return clean_key_value(row[col])
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


def find_first_existing_col(df, candidates, col_type, required=True):
    for col in candidates:
        if col in df.columns:
            return col

    norm_map = {normalize_colname(c): c for c in df.columns}

    for col in candidates:
        key = normalize_colname(col)
        if key in norm_map:
            return norm_map[key]

    if required:
        raise ValueError(f"没有找到 {col_type} 列。候选: {candidates}")

    return None


def identify_group_columns(df_groups, n=220):
    if use_fixed_group_position:
        start_idx = group_start_col_1based - 1
        end_excl = group_end_col_1based

        if len(df_groups.columns) < end_excl:
            raise ValueError(f"列数不足，需要到第 {group_end_col_1based} 列")

        group_cols = list(df_groups.columns[start_idx:end_excl])

        if len(group_cols) != n:
            raise ValueError(f"固定位置识别到 {len(group_cols)} 个基团，需要 {n}")

        return group_cols

    raise ValueError("请设置 use_fixed_group_position=True")


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


def average_relative_deviation(y_true, y_pred, eps=1e-12):
    rel_err = safe_relative_error_percent(y_true, y_pred, eps=eps)

    if np.any(np.isfinite(rel_err)):
        return float(np.nanmean(rel_err))

    return np.nan


def evaluate_metrics(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = np.isfinite(y_true) & np.isfinite(y_pred)

    y_true_valid = y_true[mask]
    y_pred_valid = y_pred[mask]

    if len(y_true_valid) == 0:
        return {
            "n_points": 0,
            "R2": np.nan,
            "MSE": np.nan,
            "RMSE": np.nan,
            "MAE": np.nan,
            "ARD": np.nan,
            "max_rel_err_percent": np.nan,
            "<1% ratio(%)": np.nan,
            "<5% ratio(%)": np.nan,
            "<10% ratio(%)": np.nan,
            "<1% count": 0.0,
            "<5% count": 0.0,
            "<10% count": 0.0,
        }

    r2 = r2_score(y_true_valid, y_pred_valid) if len(y_true_valid) > 1 else np.nan
    mse = mean_squared_error(y_true_valid, y_pred_valid)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_true_valid, y_pred_valid)
    ard = average_relative_deviation(y_true_valid, y_pred_valid)

    rel_err = safe_relative_error_percent(y_true_valid, y_pred_valid)
    n_valid_rel = int(np.sum(np.isfinite(rel_err)))

    if n_valid_rel > 0:
        c1 = float(np.nansum(rel_err < 1.0))
        c5 = float(np.nansum(rel_err < 5.0))
        c10 = float(np.nansum(rel_err < 10.0))

        r1 = c1 / n_valid_rel * 100.0
        r5 = c5 / n_valid_rel * 100.0
        r10 = c10 / n_valid_rel * 100.0

        max_rel = float(np.nanmax(rel_err))
    else:
        c1 = c5 = c10 = 0.0
        r1 = r5 = r10 = np.nan
        max_rel = np.nan

    return {
        "n_points": len(y_true_valid),
        "R2": r2,
        "MSE": mse,
        "RMSE": rmse,
        "MAE": mae,
        "ARD": ard,
        "max_rel_err_percent": max_rel,
        "<1% ratio(%)": r1,
        "<5% ratio(%)": r5,
        "<10% ratio(%)": r10,
        "<1% count": c1,
        "<5% count": c5,
        "<10% count": c10,
    }


def summarize(df, name):
    rows = []

    for metric in [
        "R2",
        "MSE",
        "RMSE",
        "MAE",
        "ARD",
        "max_rel_err_percent",
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

        rows.append({
            "Model": name,
            "Metric": metric,
            "Mean": mean_val,
            "Std": std_val,
            "Mean±Std": mean_std,
        })

    return pd.DataFrame(rows)


def make_prediction_df(
    fold,
    dataset_name,
    method,
    sample_indices,
    y_true,
    y_pred,
    baseline_delta=None,
    A_pred=None,
    B_pred=None,
):
    sample_indices = np.asarray(sample_indices, dtype=int)
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    rel_err = safe_relative_error_percent(y_true, y_pred)

    df_out = pd.DataFrame({
        "fold": fold,
        "dataset": dataset_name,
        "Method": method,
        "sample_index": sample_indices,
        material_key_col: material_keys[sample_indices],
        "T_K": T[sample_indices],
        "rho_true": y_true,
        "rho_pred": y_pred,
        "error": y_pred - y_true,
        "absolute_error": np.abs(y_pred - y_true),
        "relative_error_percent": rel_err,
        "anchor_T": anchor_T[sample_indices],
        "anchor_rho": anchor_rho[sample_indices],
        "delta_T": T[sample_indices] - anchor_T[sample_indices],
    })

    if baseline_delta is not None:
        df_out["baseline_delta_pred"] = baseline_delta

    if A_pred is not None:
        df_out["A_pred"] = A_pred

    if B_pred is not None:
        df_out["B_pred"] = B_pred

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
            df_out[col] = df_long[col].values[sample_indices]

    return df_out


def predict_anchor_baseline(indices, base_model):
    """
    锚点线性基线：
        rho_pred = anchor_rho + Ridge(Nk * (T - anchor_T))
    """
    indices = np.asarray(indices, dtype=int)

    delta_T = T[indices] - anchor_T[indices]
    X_base = X_groups[indices] * delta_T.reshape(-1, 1)

    baseline_delta = np.full(len(indices), np.nan, dtype=float)

    valid = np.isfinite(X_base).all(axis=1)

    if base_model is not None and valid.sum() > 0:
        baseline_delta[valid] = base_model.predict(X_base[valid])

    y_pred = anchor_rho[indices] + baseline_delta

    return y_pred, baseline_delta


def train_anchor_model(train_indices):
    train_indices = np.asarray(train_indices, dtype=int)

    delta_T_train = T[train_indices] - anchor_T[train_indices]
    X_base_train = X_groups[train_indices] * delta_T_train.reshape(-1, 1)
    y_base_train = rho_true[train_indices] - anchor_rho[train_indices]

    valid_base = (
        np.isfinite(X_base_train).all(axis=1)
        & np.isfinite(y_base_train)
    )

    if valid_base.sum() == 0:
        return None

    base_model = Ridge(alpha=ridge_alpha, fit_intercept=False)
    base_model.fit(X_base_train[valid_base], y_base_train[valid_base])

    return base_model


def train_linear_AB_models(train_mats):
    """
    一阶线性温度基线：
        对每个物质拟合 rho = A + B*T；
        再用基团 Nk 预测物质级 A 和 B。
    """
    train_AB = []
    train_X = []
    train_materials_used = []

    for mat in train_mats:
        if mat in material_to_AB and not np.isnan(material_to_AB[mat][0]):
            A_true, B_true = material_to_AB[mat]

            if not (np.isfinite(A_true) and np.isfinite(B_true)):
                continue

            train_AB.append((A_true, B_true))

            idx = np.where(material_keys == mat)[0][0]
            train_X.append(X_groups[idx])
            train_materials_used.append(mat)

    if len(train_AB) == 0:
        return None, None, [], np.nan, np.nan

    train_X = np.array(train_X, dtype=float)
    train_A = np.array([ab[0] for ab in train_AB], dtype=float)
    train_B = np.array([ab[1] for ab in train_AB], dtype=float)

    model_A = Ridge(alpha=ridge_alpha, fit_intercept=True)
    model_B = Ridge(alpha=ridge_alpha, fit_intercept=True)

    model_A.fit(train_X, train_A)
    model_B.fit(train_X, train_B)

    return model_A, model_B, train_materials_used, model_A.intercept_, model_B.intercept_


def predict_linear_baseline(indices, model_A, model_B):
    """
    对任意样本 indices 预测：
        rho_pred = A_pred + B_pred*T
    """
    indices = np.asarray(indices, dtype=int)

    y_pred = np.full(len(indices), np.nan, dtype=float)
    A_pred_rows = np.full(len(indices), np.nan, dtype=float)
    B_pred_rows = np.full(len(indices), np.nan, dtype=float)

    if model_A is None or model_B is None or len(indices) == 0:
        return y_pred, A_pred_rows, B_pred_rows

    mats = material_keys[indices]
    unique_mats_for_pred = np.unique(mats)

    mat_to_AB_pred = {}

    pred_X = []
    mat_order = []

    for mat in unique_mats_for_pred:
        idx = np.where(material_keys == mat)[0][0]
        pred_X.append(X_groups[idx])
        mat_order.append(mat)

    pred_X = np.array(pred_X, dtype=float)

    A_pred = model_A.predict(pred_X)
    B_pred = model_B.predict(pred_X)

    for mat, a, b in zip(mat_order, A_pred, B_pred):
        mat_to_AB_pred[mat] = (a, b)

    for i, sample_idx in enumerate(indices):
        mat = material_keys[sample_idx]

        if mat in mat_to_AB_pred:
            a, b = mat_to_AB_pred[mat]
            A_pred_rows[i] = a
            B_pred_rows[i] = b
            y_pred[i] = a + b * T[sample_idx]

    return y_pred, A_pred_rows, B_pred_rows


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
# 3. 读取数据与预处理
# =========================================================
xls_main = pd.ExcelFile(main_input_file)

if data_sheet not in xls_main.sheet_names or groups_sheet not in xls_main.sheet_names:
    raise ValueError("缺少必需 sheet")

anchor_sheet = None

for s in anchor_sheet_candidates:
    if s in xls_main.sheet_names:
        anchor_sheet = s
        break

if anchor_sheet is None:
    raise ValueError(f"没有找到锚点 sheet，候选: {anchor_sheet_candidates}")

df_data = pd.read_excel(main_input_file, sheet_name=data_sheet)
df_groups = pd.read_excel(main_input_file, sheet_name=groups_sheet)
df_anchor = pd.read_excel(main_input_file, sheet_name=anchor_sheet)

print("Data_selected 行数:", len(df_data))
print("Groups_selected 行数:", len(df_groups))
print(f"{anchor_sheet} 行数:", len(df_anchor))

# 构造 material_key
for df in [df_data, df_groups, df_anchor]:
    if material_key_col not in df.columns:
        df[material_key_col] = df.apply(build_material_key, axis=1)

    df[material_key_col] = df[material_key_col].apply(clean_key_value)

# 找到所需列
density_col = find_first_existing_col(
    df_data,
    density_col_candidates,
    "密度",
    required=True,
)

if temp_col not in df_data.columns:
    raise ValueError("没有找到温度列")

anchor_temp_col = find_first_existing_col(
    df_anchor,
    anchor_temp_col_candidates,
    "锚点温度",
    required=True,
)

anchor_density_col = find_first_existing_col(
    df_anchor,
    anchor_density_col_candidates,
    "锚点密度",
    required=True,
)

df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
df_data[density_col] = pd.to_numeric(df_data[density_col], errors="coerce")
df_anchor[anchor_temp_col] = pd.to_numeric(df_anchor[anchor_temp_col], errors="coerce")
df_anchor[anchor_density_col] = pd.to_numeric(df_anchor[anchor_density_col], errors="coerce")

# 基团列处理
group_cols_220 = identify_group_columns(df_groups, n_group_features_to_use)

df_groups_numeric = (
    df_groups[group_cols_220]
    .apply(pd.to_numeric, errors="coerce")
    .fillna(0.0)
)

nonzero_mask = df_groups_numeric.abs().sum(axis=0) != 0

used_group_cols = df_groups_numeric.columns[nonzero_mask].tolist()
removed_zero_group_cols = df_groups_numeric.columns[~nonzero_mask].tolist()

print(f"有效基团数: {len(used_group_cols)}")
print(f"删除全零基团数: {len(removed_zero_group_cols)}")

# 合并锚点信息
anchor_info = (
    df_anchor[[material_key_col, anchor_temp_col, anchor_density_col]]
    .drop_duplicates(subset=[material_key_col])
    .copy()
)

anchor_info = anchor_info.rename(
    columns={
        anchor_temp_col: "anchor_T",
        anchor_density_col: "anchor_rho",
    }
)

# 合并基团和锚点
df_long = df_data.merge(
    df_groups[[material_key_col] + used_group_cols],
    on=material_key_col,
    how="inner",
)

df_long = df_long.merge(
    anchor_info,
    on=material_key_col,
    how="inner",
)

df_long = df_long.dropna(
    subset=[temp_col, density_col] + used_group_cols + ["anchor_T", "anchor_rho"]
)

df_long = df_long[
    (df_long[temp_col] > 0)
    & (df_long[density_col] > 0)
].copy()

df_long = df_long.reset_index(drop=True)

# 提取数组
X_groups = df_long[used_group_cols].values.astype(float)
T = df_long[temp_col].values.astype(float)
rho_true = df_long[density_col].values.astype(float)
anchor_T = df_long["anchor_T"].values.astype(float)
anchor_rho = df_long["anchor_rho"].values.astype(float)
material_keys = df_long[material_key_col].values

unique_materials = np.unique(material_keys)
all_sample_indices = np.arange(len(rho_true))

print(f"总样本数: {len(rho_true)}, 总物质数: {len(unique_materials)}")

if len(unique_materials) < n_outer_folds:
    raise ValueError(
        f"物质数 {len(unique_materials)} 小于 n_outer_folds={n_outer_folds}，无法做 5-fold。"
    )


# =========================================================
# 4. 为一阶线性基线准备每个物质的真实系数 (A, B)
#    rho = A + B*T
# =========================================================
material_to_AB = {}

for mat in unique_materials:
    mask = material_keys == mat

    T_mat = T[mask]
    rho_mat = rho_true[mask]

    valid = np.isfinite(T_mat) & np.isfinite(rho_mat)

    T_mat = T_mat[valid]
    rho_mat = rho_mat[valid]

    if len(T_mat) >= 2 and np.std(T_mat) > 0:
        coeff = np.polyfit(T_mat, rho_mat, 1)  # 返回 [B, A]
        B, A = coeff[0], coeff[1]
        material_to_AB[mat] = (A, B)
    else:
        material_to_AB[mat] = (np.nan, np.nan)

df_true_ab_all = pd.DataFrame([
    {
        material_key_col: mat,
        "A_true": material_to_AB.get(mat, (np.nan, np.nan))[0],
        "B_true": material_to_AB.get(mat, (np.nan, np.nan))[1],
    }
    for mat in unique_materials
])


# =========================================================
# 5. 5 折交叉验证（按物质分组）
# =========================================================
gkf = GroupKFold(n_splits=n_outer_folds)

metrics_anchor = []
metrics_linear = []

fold_test_prediction_dfs = []
fold_all_data_prediction_dfs = []
fold_all_data_count_records = []

fold_info_records = []

anchor_param_records = []
linear_param_records = []
linear_ab_records = []

for fold, (train_mat_idx, test_mat_idx) in enumerate(
    gkf.split(unique_materials, groups=unique_materials),
    start=1,
):
    print(f"\n========== Fold {fold}/{n_outer_folds} ==========")

    train_mats = unique_materials[train_mat_idx]
    test_mats = unique_materials[test_mat_idx]

    train_mask = np.isin(material_keys, train_mats)
    test_mask = np.isin(material_keys, test_mats)

    train_indices = np.where(train_mask)[0]
    test_indices = np.where(test_mask)[0]

    print("训练物质数:", len(train_mats))
    print("测试物质数:", len(test_mats))
    print("训练样本数:", len(train_indices))
    print("测试样本数:", len(test_indices))

    # -----------------------------------------------------
    # 方法1：锚点线性基线
    # -----------------------------------------------------
    base_model = train_anchor_model(train_indices)

    if base_model is None:
        y_pred_anchor_test = np.full(len(test_indices), np.nan, dtype=float)
        baseline_delta_test = np.full(len(test_indices), np.nan, dtype=float)

        y_pred_anchor_all = np.full(len(all_sample_indices), np.nan, dtype=float)
        baseline_delta_all = np.full(len(all_sample_indices), np.nan, dtype=float)
    else:
        y_pred_anchor_test, baseline_delta_test = predict_anchor_baseline(
            test_indices,
            base_model,
        )

        y_pred_anchor_all, baseline_delta_all = predict_anchor_baseline(
            all_sample_indices,
            base_model,
        )

    # -----------------------------------------------------
    # 方法2：一阶线性温度基线 rho = A + B*T
    # -----------------------------------------------------
    model_A, model_B, train_mats_used_for_AB, intercept_A, intercept_B = train_linear_AB_models(
        train_mats
    )

    y_pred_linear_test, A_pred_test, B_pred_test = predict_linear_baseline(
        test_indices,
        model_A,
        model_B,
    )

    y_pred_linear_all, A_pred_all, B_pred_all = predict_linear_baseline(
        all_sample_indices,
        model_A,
        model_B,
    )

    # -----------------------------------------------------
    # 测试集评价
    # -----------------------------------------------------
    y_true_test = rho_true[test_indices]

    met_anchor = evaluate_metrics(y_true_test, y_pred_anchor_test)
    met_linear = evaluate_metrics(y_true_test, y_pred_linear_test)

    met_anchor["fold"] = fold
    met_linear["fold"] = fold

    metrics_anchor.append(met_anchor)
    metrics_linear.append(met_linear)

    print(f"\nFold {fold}:")
    print(
        "  锚点线性基线     - "
        f"R2={met_anchor['R2']:.4f}, "
        f"MSE={met_anchor['MSE']:.4f}, "
        f"RMSE={met_anchor['RMSE']:.4f}, "
        f"MAE={met_anchor['MAE']:.4f}, "
        f"ARD={met_anchor['ARD']:.2f}%"
    )

    print(
        "  一阶线性基线     - "
        f"R2={met_linear['R2']:.4f}, "
        f"MSE={met_linear['MSE']:.4f}, "
        f"RMSE={met_linear['RMSE']:.4f}, "
        f"MAE={met_linear['MAE']:.4f}, "
        f"ARD={met_linear['ARD']:.2f}%"
    )

    # -----------------------------------------------------
    # 新增：每个 fold 模型预测完整数据集，并统计完整数据集三档偏差数量
    # -----------------------------------------------------
    count_anchor_all = count_error_thresholds(rho_true, y_pred_anchor_all)
    count_linear_all = count_error_thresholds(rho_true, y_pred_linear_all)

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "Anchor_linear_baseline",
        **count_anchor_all,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "Linear_baseline_rho_A_plus_B_T",
        **count_linear_all,
    })

    print("\nAnchor fold model predicts ALL data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "Anchor_linear_baseline",
        **count_anchor_all,
    }]).to_string(index=False))

    print("\nLinear baseline fold model predicts ALL data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "Linear_baseline_rho_A_plus_B_T",
        **count_linear_all,
    }]).to_string(index=False))

    # -----------------------------------------------------
    # 保存测试集预测明细
    # -----------------------------------------------------
    df_test_anchor = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="Anchor_linear_baseline",
        sample_indices=test_indices,
        y_true=y_true_test,
        y_pred=y_pred_anchor_test,
        baseline_delta=baseline_delta_test,
    )

    df_test_linear = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="Linear_baseline_rho_A_plus_B_T",
        sample_indices=test_indices,
        y_true=y_true_test,
        y_pred=y_pred_linear_test,
        A_pred=A_pred_test,
        B_pred=B_pred_test,
    )

    fold_test_prediction_dfs.append(df_test_anchor)
    fold_test_prediction_dfs.append(df_test_linear)

    # -----------------------------------------------------
    # 保存完整数据集预测明细
    # -----------------------------------------------------
    df_all_anchor = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="Anchor_linear_baseline",
        sample_indices=all_sample_indices,
        y_true=rho_true,
        y_pred=y_pred_anchor_all,
        baseline_delta=baseline_delta_all,
    )

    df_all_linear = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="Linear_baseline_rho_A_plus_B_T",
        sample_indices=all_sample_indices,
        y_true=rho_true,
        y_pred=y_pred_linear_all,
        A_pred=A_pred_all,
        B_pred=B_pred_all,
    )

    fold_all_data_prediction_dfs.append(df_all_anchor)
    fold_all_data_prediction_dfs.append(df_all_linear)

    # -----------------------------------------------------
    # 保存模型参数
    # -----------------------------------------------------
    if base_model is not None and hasattr(base_model, "coef_"):
        for group_name, coef in zip(used_group_cols, base_model.coef_):
            anchor_param_records.append({
                "fold": fold,
                "group_name": group_name,
                "anchor_slope_coef_for_Nk_deltaT": coef,
                "abs_anchor_slope_coef": abs(coef),
            })

    if model_A is not None and model_B is not None:
        for group_name, coef_A, coef_B in zip(used_group_cols, model_A.coef_, model_B.coef_):
            linear_param_records.append({
                "fold": fold,
                "group_name": group_name,
                "coef_for_A": coef_A,
                "coef_for_B": coef_B,
                "abs_coef_for_A": abs(coef_A),
                "abs_coef_for_B": abs(coef_B),
                "intercept_A": model_A.intercept_,
                "intercept_B": model_B.intercept_,
            })

        # 保存测试物质 A/B 预测诊断
        unique_test_mats = np.unique(material_keys[test_indices])

        for mat in unique_test_mats:
            idx = np.where(material_keys == mat)[0][0]
            x_one = X_groups[idx].reshape(1, -1)

            A_pred_mat = float(model_A.predict(x_one)[0])
            B_pred_mat = float(model_B.predict(x_one)[0])

            A_true, B_true = material_to_AB.get(mat, (np.nan, np.nan))

            linear_ab_records.append({
                "fold": fold,
                material_key_col: mat,
                "A_true": A_true,
                "B_true": B_true,
                "A_pred": A_pred_mat,
                "B_pred": B_pred_mat,
                "A_error": A_pred_mat - A_true if np.isfinite(A_true) else np.nan,
                "B_error": B_pred_mat - B_true if np.isfinite(B_true) else np.nan,
                "A_abs_error": abs(A_pred_mat - A_true) if np.isfinite(A_true) else np.nan,
                "B_abs_error": abs(B_pred_mat - B_true) if np.isfinite(B_true) else np.nan,
            })

    fold_info_records.append({
        "fold": fold,
        "n_train_materials": len(train_mats),
        "n_test_materials": len(test_mats),
        "n_train_points": len(train_indices),
        "n_test_points": len(test_indices),
        "n_all_points": len(all_sample_indices),
        "n_group_features": len(used_group_cols),
        "anchor_model_trained": base_model is not None,
        "linear_model_trained": model_A is not None and model_B is not None,
        "n_train_materials_used_for_AB": len(train_mats_used_for_AB),
        "ridge_alpha": ridge_alpha,
    })


# =========================================================
# 6. 汇总统计与配对 t 检验
# =========================================================
df_anchor_metrics = pd.DataFrame(metrics_anchor)
df_linear_metrics = pd.DataFrame(metrics_linear)

# fold 放到第一列
df_anchor_metrics = df_anchor_metrics[["fold"] + [c for c in df_anchor_metrics.columns if c != "fold"]]
df_linear_metrics = df_linear_metrics[["fold"] + [c for c in df_linear_metrics.columns if c != "fold"]]

summary_anchor = summarize(df_anchor_metrics, "Anchor linear baseline")
summary_linear = summarize(df_linear_metrics, "Linear baseline (rho=A+B*T)")

summary_all = pd.concat(
    [summary_anchor, summary_linear],
    ignore_index=True,
)

print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
print(summary_all.to_string(index=False))

# 配对 t 检验
t_test_results = []

for metric in ["R2", "MSE", "RMSE", "MAE", "ARD"]:
    vals_anc = df_anchor_metrics[metric].values.astype(float)
    vals_lin = df_linear_metrics[metric].values.astype(float)

    valid = np.isfinite(vals_anc) & np.isfinite(vals_lin)

    vals_anc = vals_anc[valid]
    vals_lin = vals_lin[valid]

    if len(vals_anc) > 1:
        t_stat, p_val = ttest_rel(vals_anc, vals_lin)

        if metric == "R2":
            better = "linear" if np.mean(vals_lin) > np.mean(vals_anc) else "anchor"
        else:
            better = "linear" if np.mean(vals_lin) < np.mean(vals_anc) else "anchor"

        t_test_results.append({
            "Metric": metric,
            "Mean_anchor": f"{np.mean(vals_anc):.4f}",
            "Mean_linear": f"{np.mean(vals_lin):.4f}",
            "p-value": f"{p_val:.4e}",
            "Significant(p<0.05)": p_val < 0.05,
            "Better model": better,
            "n_valid_fold_pairs": len(vals_anc),
        })

df_ttest = pd.DataFrame(t_test_results)

print("\n========== Paired t-test ==========")
print(df_ttest.to_string(index=False))


# =========================================================
# 7. 新增：完整数据集预测偏差数量统计汇总
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
        "n_all_data_points": len(rho_true),
    })

df_final_average_summary = pd.DataFrame(final_average_records)

print("\n========== Fold all-data count summary ==========")
print(df_fold_all_data_count_summary.to_string(index=False))

print("\n========== Final average all-data count summary ==========")
print(df_final_average_summary.to_string(index=False))


# =========================================================
# 8. 整理保存表
# =========================================================
df_fold_test_predictions = pd.concat(fold_test_prediction_dfs, ignore_index=True)
df_fold_all_data_predictions = pd.concat(fold_all_data_prediction_dfs, ignore_index=True)

df_fold_info = pd.DataFrame(fold_info_records)

df_anchor_params = pd.DataFrame(anchor_param_records)
df_linear_params = pd.DataFrame(linear_param_records)
df_linear_ab_by_fold = pd.DataFrame(linear_ab_records)

df_used_groups = pd.DataFrame({
    "used_group": used_group_cols,
    "occurrence_all_materials": (df_groups_numeric[used_group_cols] != 0).sum(axis=0).values,
    "total_count_all": df_groups_numeric[used_group_cols].sum(axis=0).values,
})

df_removed_zero_groups = pd.DataFrame({
    "removed_zero_group": removed_zero_group_cols,
})

df_run_info = pd.DataFrame([
    {"param": "main_input_file", "value": str(main_input_file)},
    {"param": "data_sheet", "value": data_sheet},
    {"param": "groups_sheet", "value": groups_sheet},
    {"param": "anchor_sheet", "value": anchor_sheet},
    {"param": "density_col", "value": density_col},
    {"param": "temp_col", "value": temp_col},
    {"param": "anchor_temp_col", "value": anchor_temp_col},
    {"param": "anchor_density_col", "value": anchor_density_col},
    {"param": "n_outer_folds", "value": n_outer_folds},
    {"param": "random_state", "value": random_state},
    {"param": "ridge_alpha", "value": ridge_alpha},
    {"param": "n_group_features", "value": len(used_group_cols)},
    {"param": "n_all_data_points", "value": len(rho_true)},
    {"param": "n_materials", "value": len(unique_materials)},
    {"param": "method1", "value": "Anchor linear baseline: rho = anchor_rho + Ridge(Nk*(T-anchor_T))"},
    {"param": "method2", "value": "Linear baseline: rho = A + B*T; A and B predicted by Ridge(Nk)"},
    {
        "param": "relative_error_definition",
        "value": "abs((y_pred - y_true) / y_true) * 100; abs(y_true)<=1e-12 -> NaN",
    },
    {
        "param": "full_data_count_rule",
        "value": "Each fold model predicts the whole dataset; count rel_err <1%, <5%, <10%; then average counts over 5 folds.",
    },
])

df_model_structure = pd.DataFrame([
    {
        "项目": "预测对象",
        "内容": f"液体密度 rho，目标列 {density_col}",
    },
    {
        "项目": "数据文件",
        "内容": str(main_input_file),
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
        "内容": f"{n_outer_folds}-fold GroupKFold，按 material_key 物质划分",
    },
    {
        "项目": "方法1",
        "内容": "Anchor_linear_baseline：rho = anchor_rho + Ridge(Nk * (T - anchor_T))",
    },
    {
        "项目": "方法1训练目标",
        "内容": "rho_true - anchor_rho",
    },
    {
        "项目": "方法1输入特征",
        "内容": f"Nk * (T - anchor_T)，有效基团数 {len(used_group_cols)}",
    },
    {
        "项目": "方法1模型",
        "内容": f"Ridge(alpha={ridge_alpha}, fit_intercept=False)",
    },
    {
        "项目": "方法2",
        "内容": "Linear_baseline_rho_A_plus_B_T：rho = A + B*T",
    },
    {
        "项目": "方法2训练逻辑",
        "内容": "先对每个物质用温度点拟合真实 A/B，再用 Ridge 基于 Nk 分别预测 A 和 B",
    },
    {
        "项目": "方法2输入特征",
        "内容": f"Nk 预测 A；Nk 预测 B；有效基团数 {len(used_group_cols)}",
    },
    {
        "项目": "方法2模型",
        "内容": f"A 模型和 B 模型均为 Ridge(alpha={ridge_alpha}, fit_intercept=True)",
    },
    {
        "项目": "是否包含子模型",
        "内容": "包含物质级参数子模型：A 参数预测模型和 B 参数预测模型",
    },
    {
        "项目": "子模型预测对象",
        "内容": "rho = A + B*T 中的 A 和 B",
    },
    {
        "项目": "子模型类型",
        "内容": "Ridge",
    },
    {
        "项目": "子模型参数",
        "内容": f"Ridge(alpha={ridge_alpha}, fit_intercept=True)",
    },
    {
        "项目": "子模型输入特征",
        "内容": "Nk 基团向量",
    },
    {
        "项目": "slope 构造",
        "内容": "方法2中的 B 是物质级温度斜率，由每个物质 rho-T 一阶拟合得到，再由基团 Ridge 预测",
    },
    {
        "项目": "baseline 构造",
        "内容": "方法1为锚点线性基线；方法2为一阶温度显式基线",
    },
    {
        "项目": "residual 构造",
        "内容": "无 residual 修正模型",
    },
    {
        "项目": "最终模型",
        "内容": "方法1：anchor_rho + Ridge(Nk*(T-anchor_T))；方法2：A_pred + B_pred*T",
    },
    {
        "项目": "偏差数量统计口径",
        "内容": "每个 fold 模型预测完整数据集，统计 rho 相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 取平均",
    },
])


# =========================================================
# 9. 保存结果到 Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    # 原有核心输出
    df_anchor_metrics.to_excel(writer, sheet_name="Fold_Metrics_Anchor", index=False)
    df_linear_metrics.to_excel(writer, sheet_name="Fold_Metrics_Linear", index=False)
    summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
    df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)

    # 新增预测明细与全数据统计
    df_fold_test_predictions.to_excel(writer, sheet_name="fold_test_predictions", index=False)
    df_fold_all_data_predictions.to_excel(writer, sheet_name="fold_all_data_predictions", index=False)
    df_fold_all_data_count_summary.to_excel(writer, sheet_name="fold_all_data_count_summary", index=False)
    df_final_average_summary.to_excel(writer, sheet_name="final_average_summary", index=False)

    # 子模型 / 参数 / A-B 诊断
    df_true_ab_all.to_excel(writer, sheet_name="Linear_AB_True_All", index=False)
    df_linear_ab_by_fold.to_excel(writer, sheet_name="Linear_AB_By_Fold", index=False)
    df_anchor_params.to_excel(writer, sheet_name="anchor_params", index=False)
    df_linear_params.to_excel(writer, sheet_name="linear_params", index=False)

    # 运行信息
    df_fold_info.to_excel(writer, sheet_name="Fold_Info", index=False)
    df_used_groups.to_excel(writer, sheet_name="Used_Groups", index=False)
    df_removed_zero_groups.to_excel(writer, sheet_name="Removed_Zero_Groups", index=False)
    df_run_info.to_excel(writer, sheet_name="Run_Info", index=False)
    df_model_structure.to_excel(writer, sheet_name="model_structure", index=False)

    format_excel(writer)

print(f"\n结果已保存至: {output_file}")


# =========================================================
# 10. 最终方便复制输出
# =========================================================
def get_final_counts(method_name):
    row = df_final_average_summary[
        df_final_average_summary["Method"] == method_name
    ]

    if row.empty:
        return np.nan, np.nan, np.nan

    row = row.iloc[0]

    return (
        row["mean_count_rel_err_lt_1pct"],
        row["mean_count_rel_err_lt_5pct"],
        row["mean_count_rel_err_lt_10pct"],
    )


anchor_1, anchor_5, anchor_10 = get_final_counts("Anchor_linear_baseline")
linear_1, linear_5, linear_10 = get_final_counts("Linear_baseline_rho_A_plus_B_T")

print("\n方法1 全数据预测偏差 1%，5%，10%分别为：")
print(anchor_1)
print(anchor_5)
print(anchor_10)

print("\n方法2 全数据预测偏差 1%，5%，10%分别为：")
print(linear_1)
print(linear_5)
print(linear_10)


# =========================================================
# 11. 代码结构打印
# =========================================================
print("\n========== 当前代码结构简要汇总 ==========")
print(f"预测对象：液体密度 rho / {density_col}")
print(f"数据文件：{main_input_file}")
print(f"sheet 名称：{data_sheet}, {groups_sheet}, {anchor_sheet}")
print(f"交叉验证：{n_outer_folds}-fold GroupKFold，按 material_key 物质划分")
print("方法1：Anchor_linear_baseline，rho = anchor_rho + Ridge(Nk*(T-anchor_T))")
print("方法2：Linear_baseline_rho_A_plus_B_T，rho = A + B*T")
print("子模型：方法2包含 A 参数预测模型和 B 参数预测模型")
print(f"子模型参数：Ridge(alpha={ridge_alpha}, fit_intercept=True)")
print("子模型输入特征：Nk 基团向量")
print("slope 构造：B 为每个物质 rho-T 一阶拟合斜率，再由基团 Ridge 预测")
print("baseline 构造：方法1为锚点线性基线；方法2为一阶温度显式基线")
print("residual 模型：无")
print(f"方法1最终模型：Ridge(alpha={ridge_alpha}, fit_intercept=False)")
print(f"方法2最终模型：两个 Ridge(alpha={ridge_alpha}, fit_intercept=True) 分别预测 A 和 B")
print("方法1最终输入：Nk*(T-anchor_T)")
print("方法2最终输入：Nk 预测 A；Nk 预测 B；最终 rho=A+B*T")
print("偏差统计口径：每个 fold 模型预测完整数据集，统计 rho 相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 取平均")