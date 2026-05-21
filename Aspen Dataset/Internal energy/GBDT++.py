# import pandas as pd
# import numpy as np
# from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
# from sklearn.linear_model import HuberRegressor
# from sklearn.preprocessing import PolynomialFeatures
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split
#
# # =========================
# # 0. 参数区
# # =========================
# main_file = "internal energy 207.xlsx"
# main_sheet = "Sheet1"
#
# tb_descriptor_file = "selected_25_descriptors_boiling.xlsx"
# tb_descriptor_target = "internal energy at boiling temperature"
#
# random_state = 42
# Tb0 = 222.543
#
# # =========================
# # 1. 读取主数据表
# # =========================
# df = pd.read_excel(main_file, sheet_name=main_sheet).copy()
#
# id_col = df.columns[0]
# group_cols = list(df.columns[13:32])   # 第14~32列：基团
# temp_cols = list(df.columns[32:42])    # 第33~42列：温度
# hvap_cols = list(df.columns[42:52])    # 第43~52列：目标变量
#
# tb_col_idx = 5
#
# # 转数值
# for col in group_cols + temp_cols + hvap_cols:
#     df[col] = pd.to_numeric(df[col], errors="coerce")
# df.iloc[:, tb_col_idx] = pd.to_numeric(df.iloc[:, tb_col_idx], errors="coerce")
#
# # 只保留至少有一个有效目标点的物质
# valid_material_mask = df[hvap_cols].notna().any(axis=1)
# df = df.loc[valid_material_mask].copy().reset_index(drop=True)
#
# print(f"有效物质数: {len(df)}")
#
# # =========================
# # 2. 按物质 8:2 划分
# # =========================
# unique_materials = df[id_col].dropna().unique()
#
# train_materials, test_materials = train_test_split(
#     unique_materials,
#     test_size=0.2,
#     random_state=random_state
# )
#
# train_row_mask = df[id_col].isin(train_materials).values
# test_row_mask = df[id_col].isin(test_materials).values
#
# train_df = df.loc[train_row_mask].copy().reset_index(drop=True)
# test_df = df.loc[test_row_mask].copy().reset_index(drop=True)
#
# print(f"训练集物质数: {len(train_df)}")
# print(f"测试集物质数: {len(test_df)}")
#
# # =========================
# # 3. 读取并切分 Tb 描述符表
# #    若描述符表有 Material_ID 列，则按 ID 切分；
# #    否则默认与主表行顺序一一对应
# # =========================
# df_Tb = pd.read_excel(tb_descriptor_file).copy()
#
# if id_col in df_Tb.columns:
#     train_df_Tb = df_Tb[df_Tb[id_col].isin(train_materials)].copy().reset_index(drop=True)
#     test_df_Tb = df_Tb[df_Tb[id_col].isin(test_materials)].copy().reset_index(drop=True)
# else:
#     if len(df_Tb) != len(df):
#         raise ValueError(
#             f"{tb_descriptor_file} 没有 {id_col} 列，且行数 {len(df_Tb)} 与主表 {len(df)} 不一致，无法安全切分。"
#         )
#     train_df_Tb = df_Tb.loc[train_row_mask].copy().reset_index(drop=True)
#     test_df_Tb = df_Tb.loc[test_row_mask].copy().reset_index(drop=True)
#
# # =========================
# # 4. 工具函数
# # =========================
# def prepare_descriptor_xy(df_desc, target_col, id_col=None):
#     drop_cols = [target_col]
#     if id_col is not None and id_col in df_desc.columns:
#         drop_cols.append(id_col)
#
#     X = df_desc.drop(columns=drop_cols, errors="ignore").copy()
#     X = X.apply(pd.to_numeric, errors="coerce")
#
#     y = pd.to_numeric(df_desc[target_col], errors="coerce").values
#
#     feature_cols = X.columns.tolist()
#     return X, y, feature_cols
#
# def fill_with_train_median(X_train, X_test):
#     med = X_train.median(numeric_only=True)
#     X_train_filled = X_train.fillna(med)
#     X_test_filled = X_test.fillna(med)
#     return X_train_filled, X_test_filled
#
# def get_arrays(df_part):
#     return {
#         "ids": df_part[id_col].values,
#         "Nk": df_part[group_cols].apply(pd.to_numeric, errors="coerce").values,
#         "T": df_part[temp_cols].apply(pd.to_numeric, errors="coerce").values,
#         "Hvap": df_part[hvap_cols].apply(pd.to_numeric, errors="coerce").values,
#         "Tb": pd.to_numeric(df_part.iloc[:, tb_col_idx], errors="coerce").values,
#     }
#
# def evaluate_scalar_regression(y_true, y_pred, model_name, split_name):
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#
#     mask = np.isfinite(y_true) & np.isfinite(y_pred)
#     y_true = y_true[mask]
#     y_pred = y_pred[mask]
#
#     if len(y_true) == 0:
#         print(f"\n{model_name} - {split_name}: 无有效样本")
#         return {
#             "Model": model_name,
#             "Split": split_name,
#             "R2": np.nan,
#             "MSE": np.nan
#         }
#
#     r2 = r2_score(y_true, y_pred)
#     mse = mean_squared_error(y_true, y_pred)
#
#     print(f"\n{model_name} - {split_name}")
#     print(f"R²  = {r2:.6f}")
#     print(f"MSE = {mse:.6f}")
#
#     return {
#         "Model": model_name,
#         "Split": split_name,
#         "R2": r2,
#         "MSE": mse
#     }
#
# def eval_final_regression(y_true, y_pred, model_name, split_name):
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#
#     mask = np.isfinite(y_true) & np.isfinite(y_pred)
#     y_true = y_true[mask]
#     y_pred = y_pred[mask]
#
#     if len(y_true) == 0:
#         print(f"\n{model_name} - {split_name}: 无有效样本")
#         return {
#             "Model": model_name,
#             "Split": split_name,
#             "R2": np.nan,
#             "MSE": np.nan,
#             "ARD_%": np.nan,
#             "within_1pct": np.nan,
#             "within_5pct": np.nan,
#             "within_10pct": np.nan
#         }, np.array([])
#
#     r2 = r2_score(y_true, y_pred)
#     mse = mean_squared_error(y_true, y_pred)
#
#     relative_error = np.full_like(y_true, np.nan, dtype=float)
#     nonzero_mask = np.abs(y_true) > 1e-12
#     relative_error[nonzero_mask] = np.abs(
#         (y_pred[nonzero_mask] - y_true[nonzero_mask]) / y_true[nonzero_mask]
#     ) * 100
#
#     ard = np.nanmean(relative_error)
#     within_1pct = np.sum(relative_error <= 1)
#     within_5pct = np.sum(relative_error <= 5)
#     within_10pct = np.sum(relative_error <= 10)
#
#     print(f"\n{model_name} - {split_name}")
#     print(f"R²  = {r2:.6f}")
#     print(f"MSE = {mse:.6f}")
#     print(f"ARD = {ard:.2f}%")
#     print(f"误差 ≤ 1% 的点数: {within_1pct}")
#     print(f"误差 ≤ 5% 的点数: {within_5pct}")
#     print(f"误差 ≤ 10% 的点数: {within_10pct}")
#
#     return {
#         "Model": model_name,
#         "Split": split_name,
#         "R2": r2,
#         "MSE": mse,
#         "ARD_%": ard,
#         "within_1pct": within_1pct,
#         "within_5pct": within_5pct,
#         "within_10pct": within_10pct
#     }, relative_error
#
# def collect_true_pred(df_part, pred_df, hvap_cols):
#     y_true_all = []
#     y_pred_all = []
#
#     for hvcol in hvap_cols:
#         actual = pd.to_numeric(df_part[hvcol], errors="coerce").to_numpy(dtype=float)
#         pred = pd.to_numeric(pred_df[hvcol], errors="coerce").to_numpy(dtype=float)
#
#         m = np.isfinite(actual) & np.isfinite(pred)
#         if np.any(m):
#             y_true_all.append(actual[m])
#             y_pred_all.append(pred[m])
#
#     if len(y_true_all) == 0:
#         return np.array([]), np.array([])
#
#     return np.concatenate(y_true_all), np.concatenate(y_pred_all)
#
# # =========================
# # 5. 构造 train/test 数组
# # =========================
# train_arr = get_arrays(train_df)
# test_arr = get_arrays(test_df)
#
# # =========================
# # 6. HVap_Tb 子模型（只用训练集）
# # =========================
# X_Tb_train, y_Tb_train, feature_cols = prepare_descriptor_xy(train_df_Tb, tb_descriptor_target, id_col=id_col)
# X_Tb_test, y_Tb_test, _ = prepare_descriptor_xy(test_df_Tb, tb_descriptor_target, id_col=id_col)
#
# X_Tb_test = X_Tb_test.reindex(columns=feature_cols)
# X_Tb_train, X_Tb_test = fill_with_train_median(X_Tb_train, X_Tb_test)
#
# mask_hvap_tb_train = np.isfinite(y_Tb_train)
# mask_hvap_tb_test = np.isfinite(y_Tb_test)
#
# hvap_tb_model = RandomForestRegressor(
#     n_estimators=100,
#     random_state=random_state,
#     n_jobs=-1
# )
# hvap_tb_model.fit(X_Tb_train.loc[mask_hvap_tb_train], y_Tb_train[mask_hvap_tb_train])
#
# HVap_Tb_pred_train = hvap_tb_model.predict(X_Tb_train)
# HVap_Tb_pred_test = hvap_tb_model.predict(X_Tb_test)
#
# hvap_tb_metrics_train = evaluate_scalar_regression(
#     y_Tb_train[mask_hvap_tb_train],
#     HVap_Tb_pred_train[mask_hvap_tb_train],
#     "HVap_Tb_submodel",
#     "train"
# )
# hvap_tb_metrics_test = evaluate_scalar_regression(
#     y_Tb_test[mask_hvap_tb_test],
#     HVap_Tb_pred_test[mask_hvap_tb_test],
#     "HVap_Tb_submodel",
#     "test"
# )
#
# # =========================
# # 7. Tb 子模型（只用训练集）
# # =========================
# poly = PolynomialFeatures(degree=2, include_bias=False)
# Nk_poly_train = poly.fit_transform(train_arr["Nk"])
# Nk_poly_test = poly.transform(test_arr["Nk"])
#
# tb_train_mask = np.isfinite(train_arr["Tb"]) & np.isfinite(Nk_poly_train).all(axis=1)
# tb_test_mask = np.isfinite(test_arr["Tb"]) & np.isfinite(Nk_poly_test).all(axis=1)
#
# model_Tb = HuberRegressor(max_iter=10000)
# model_Tb.fit(
#     Nk_poly_train[tb_train_mask],
#     np.exp(train_arr["Tb"][tb_train_mask] / Tb0)
# )
#
# Tb_pred_train = Tb0 * np.log(np.clip(model_Tb.predict(Nk_poly_train), 1e-6, None))
# Tb_pred_test = Tb0 * np.log(np.clip(model_Tb.predict(Nk_poly_test), 1e-6, None))
#
# tb_metrics_train = evaluate_scalar_regression(
#     train_arr["Tb"][tb_train_mask],
#     Tb_pred_train[tb_train_mask],
#     "Tb_submodel",
#     "train"
# )
# tb_metrics_test = evaluate_scalar_regression(
#     test_arr["Tb"][tb_test_mask],
#     Tb_pred_test[tb_test_mask],
#     "Tb_submodel",
#     "test"
# )
#
# # =========================
# # 8. A_k 基线模型（只用训练集）
# # =========================
# G_train = train_arr["Nk"]
# G_test = test_arr["Nk"]
#
# X_rows_train = []
# y_rows_train = []
#
# for i in range(len(train_df)):
#     if not np.isfinite(Tb_pred_train[i]) or not np.isfinite(HVap_Tb_pred_train[i]) or not np.isfinite(G_train[i]).all():
#         continue
#
#     for tcol, hvcol in zip(temp_cols, hvap_cols):
#         Tj = train_df.at[i, tcol]
#         Hvapj = train_df.at[i, hvcol]
#
#         if np.isnan(Tj) or np.isnan(Hvapj):
#             continue
#
#         Xj = (Tj - Tb_pred_train[i]) * G_train[i]
#         yj = Hvapj - HVap_Tb_pred_train[i]
#
#         X_rows_train.append(Xj)
#         y_rows_train.append(yj)
#
# X_A_train = np.array(X_rows_train, dtype=float)
# y_A_train = np.array(y_rows_train, dtype=float)
#
# A_solver = HuberRegressor(fit_intercept=False, max_iter=5000)
# A_solver.fit(X_A_train, y_A_train)
# A_vec = A_solver.coef_
#
# # =========================
# # 9. 生成基准预测（train/test分别生成）
# # =========================
# def build_baseline_predictions(df_part, G_part, Tb_pred_part, Hvap_ref_part):
#     pred_df = pd.DataFrame(index=df_part.index, columns=hvap_cols, dtype=float)
#
#     for i in range(len(df_part)):
#         if not np.isfinite(Tb_pred_part[i]) or not np.isfinite(Hvap_ref_part[i]) or not np.isfinite(G_part[i]).all():
#             pred_df.loc[i, :] = np.nan
#             continue
#
#         for tcol, hvcol in zip(temp_cols, hvap_cols):
#             Tj = df_part.at[i, tcol]
#
#             if np.isnan(Tj):
#                 pred_df.at[i, hvcol] = np.nan
#                 continue
#
#             Xj = (Tj - Tb_pred_part[i]) * G_part[i]
#             pred_df.at[i, hvcol] = Hvap_ref_part[i] + Xj @ A_vec
#
#     return pred_df
#
# HVap_pred_baseline_train = build_baseline_predictions(train_df, G_train, Tb_pred_train, HVap_Tb_pred_train)
# HVap_pred_baseline_test = build_baseline_predictions(test_df, G_test, Tb_pred_test, HVap_Tb_pred_test)
#
# # =========================
# # 10. 残差数据集（只用训练集）
# # =========================
# def build_residual_dataset(df_part, G_part, Tb_pred_part, Hvap_ref_part, baseline_pred_df):
#     residual_features = []
#     residual_targets = []
#     sample_groups = []
#
#     for tcol, hvcol in zip(temp_cols, hvap_cols):
#         Tj = df_part[tcol].to_numpy(dtype=float)
#         Hvapj = df_part[hvcol].to_numpy(dtype=float)
#
#         msk = (~np.isnan(Tj)) & (~np.isnan(Hvapj)) & (~baseline_pred_df[hvcol].isna().to_numpy())
#
#         for i in np.where(msk)[0]:
#             baseline_pred = baseline_pred_df.at[i, hvcol]
#             if not np.isfinite(baseline_pred):
#                 continue
#
#             if not np.isfinite(G_part[i]).all() or not np.isfinite(Tb_pred_part[i]) or not np.isfinite(Hvap_ref_part[i]):
#                 continue
#
#             base_features = list(G_part[i])
#             temp_features = [
#                 Tj[i],
#                 Tj[i] - Tb_pred_part[i],
#                 Tj[i] / Tb_pred_part[i] if Tb_pred_part[i] > 0 else 0.0,
#                 np.log(Tj[i]) if Tj[i] > 0 else 0.0,
#             ]
#             baseline_features = [baseline_pred]
#             ref_features = [Tb_pred_part[i], Hvap_ref_part[i]]
#
#             all_features = base_features + temp_features + baseline_features + ref_features
#             residual_features.append(all_features)
#
#             residual = Hvapj[i] - baseline_pred
#             residual_targets.append(residual)
#
#             sample_groups.append(df_part.at[i, id_col])
#
#     residual_features = np.array(residual_features, dtype=float)
#     residual_targets = np.array(residual_targets, dtype=float)
#     sample_groups = np.array(sample_groups)
#
#     return residual_features, residual_targets, sample_groups
#
# residual_X_train, residual_y_train, residual_groups_train = build_residual_dataset(
#     train_df, G_train, Tb_pred_train, HVap_Tb_pred_train, HVap_pred_baseline_train
# )
#
# print(f"\n残差训练集形状: {residual_X_train.shape}")
# print(f"残差目标形状: {residual_y_train.shape}")
#
# # =========================
# # 11. 最终残差模型：GBDT
# # =========================
# residual_model = GradientBoostingRegressor(
#     n_estimators=200,
#     learning_rate=0.05,
#     max_depth=5,
#     min_samples_split=20,
#     min_samples_leaf=10,
#     random_state=41
# )
#
# print("\n🚀 训练最终残差 GBDT 模型...")
# residual_model.fit(residual_X_train, residual_y_train)
#
# # =========================
# # 12. 生成最终预测（基准 + 残差修正）
# # =========================
# def build_final_predictions(df_part, G_part, Tb_pred_part, Hvap_ref_part, baseline_pred_df):
#     final_pred_df = pd.DataFrame(index=df_part.index, columns=hvap_cols, dtype=float)
#
#     for tcol, hvcol in zip(temp_cols, hvap_cols):
#         Tj = df_part[tcol].to_numpy(dtype=float)
#
#         features_list = []
#         valid_indices = []
#
#         for i in range(len(df_part)):
#             if np.isnan(Tj[i]):
#                 continue
#
#             baseline_pred = baseline_pred_df.at[i, hvcol]
#             if pd.isna(baseline_pred) or not np.isfinite(baseline_pred):
#                 continue
#
#             if not np.isfinite(G_part[i]).all() or not np.isfinite(Tb_pred_part[i]) or not np.isfinite(Hvap_ref_part[i]):
#                 continue
#
#             base_features = list(G_part[i])
#             temp_features = [
#                 Tj[i],
#                 Tj[i] - Tb_pred_part[i],
#                 Tj[i] / Tb_pred_part[i] if Tb_pred_part[i] > 0 else 0.0,
#                 np.log(Tj[i]) if Tj[i] > 0 else 0.0,
#             ]
#             baseline_features = [baseline_pred]
#             ref_features = [Tb_pred_part[i], Hvap_ref_part[i]]
#
#             all_features = base_features + temp_features + baseline_features + ref_features
#             features_list.append(all_features)
#             valid_indices.append(i)
#
#         if len(features_list) > 0:
#             features_array = np.array(features_list, dtype=float)
#             residual_pred = residual_model.predict(features_array)
#
#             for idx, residual_val in zip(valid_indices, residual_pred):
#                 final_pred_df.at[idx, hvcol] = baseline_pred_df.at[idx, hvcol] + residual_val
#
#     return final_pred_df
#
# HVap_pred_final_train = build_final_predictions(
#     train_df, G_train, Tb_pred_train, HVap_Tb_pred_train, HVap_pred_baseline_train
# )
# HVap_pred_final_test = build_final_predictions(
#     test_df, G_test, Tb_pred_test, HVap_Tb_pred_test, HVap_pred_baseline_test
# )
#
# # =========================
# # 13. 评估：基线 / 最终（train/test分开）
# # =========================
# y_train_true_base, y_train_pred_base = collect_true_pred(train_df, HVap_pred_baseline_train, hvap_cols)
# y_test_true_base, y_test_pred_base = collect_true_pred(test_df, HVap_pred_baseline_test, hvap_cols)
#
# baseline_metrics_train, _ = eval_final_regression(
#     y_train_true_base, y_train_pred_base, "Baseline_model", "train"
# )
# baseline_metrics_test, _ = eval_final_regression(
#     y_test_true_base, y_test_pred_base, "Baseline_model", "test"
# )
#
# y_train_true_final, y_train_pred_final = collect_true_pred(train_df, HVap_pred_final_train, hvap_cols)
# y_test_true_final, y_test_pred_final = collect_true_pred(test_df, HVap_pred_final_test, hvap_cols)
#
# final_metrics_train, rel_err_train = eval_final_regression(
#     y_train_true_final, y_train_pred_final, "Final_GBDT_model", "train"
# )
# final_metrics_test, rel_err_test = eval_final_regression(
#     y_test_true_final, y_test_pred_final, "Final_GBDT_model", "test"
# )
#
# # =========================
# # 14. 分温度点评估（最终模型）
# # =========================
# print("\n=== 分温度点评估（最终模型，训练集）===")
# for tcol, hvcol in zip(temp_cols, hvap_cols):
#     actual = train_df[hvcol].to_numpy(dtype=float)
#     pred = HVap_pred_final_train[hvcol].to_numpy(dtype=float)
#     m = np.isfinite(actual) & np.isfinite(pred)
#     if np.any(m):
#         mse_temp = mean_squared_error(actual[m], pred[m])
#         r2_temp = r2_score(actual[m], pred[m])
#         print(f"{tcol}: MSE = {mse_temp:.6f}, R² = {r2_temp:.6f}")
#
# print("\n=== 分温度点评估（最终模型，测试集）===")
# for tcol, hvcol in zip(temp_cols, hvap_cols):
#     actual = test_df[hvcol].to_numpy(dtype=float)
#     pred = HVap_pred_final_test[hvcol].to_numpy(dtype=float)
#     m = np.isfinite(actual) & np.isfinite(pred)
#     if np.any(m):
#         mse_temp = mean_squared_error(actual[m], pred[m])
#         r2_temp = r2_score(actual[m], pred[m])
#         print(f"{tcol}: MSE = {mse_temp:.6f}, R² = {r2_temp:.6f}")
#
# # =========================
# # 15. 保存结果
# # =========================
# def build_long_compare(df_part, split_name, Tb_pred_part, Hvap_ref_part, baseline_pred_df, final_pred_df):
#     rows = []
#     for idx in range(len(df_part)):
#         ID = df_part.at[idx, id_col]
#         for j, (tcol, hvcol) in enumerate(zip(temp_cols, hvap_cols), start=1):
#             T_val = df_part.at[idx, tcol]
#             Hvap_act = df_part.at[idx, hvcol]
#             Hvap_base = baseline_pred_df.at[idx, hvcol] if pd.notna(baseline_pred_df.at[idx, hvcol]) else np.nan
#             Hvap_final = final_pred_df.at[idx, hvcol] if pd.notna(final_pred_df.at[idx, hvcol]) else np.nan
#
#             err_base = (Hvap_base - Hvap_act) if (pd.notna(Hvap_base) and pd.notna(Hvap_act)) else np.nan
#             err_final = (Hvap_final - Hvap_act) if (pd.notna(Hvap_final) and pd.notna(Hvap_act)) else np.nan
#             residual_correction = (Hvap_final - Hvap_base) if (pd.notna(Hvap_final) and pd.notna(Hvap_base)) else np.nan
#
#             rows.append({
#                 "Split": split_name,
#                 id_col: ID,
#                 "temp_index": j,
#                 "temp_col": tcol,
#                 "T": T_val,
#                 "HVap_actual": Hvap_act,
#                 "HVap_baseline": Hvap_base,
#                 "HVap_final": Hvap_final,
#                 "error_baseline": err_base,
#                 "error_final": err_final,
#                 "residual_correction": residual_correction,
#                 "T_ref": Tb_pred_part[idx],
#                 "HVap_ref": Hvap_ref_part[idx]
#             })
#     return pd.DataFrame(rows)
#
# long_train = build_long_compare(
#     train_df, "train", Tb_pred_train, HVap_Tb_pred_train, HVap_pred_baseline_train, HVap_pred_final_train
# )
# long_test = build_long_compare(
#     test_df, "test", Tb_pred_test, HVap_Tb_pred_test, HVap_pred_baseline_test, HVap_pred_final_test
# )
# long_compare = pd.concat([long_train, long_test], ignore_index=True).sort_values(["Split", id_col, "temp_index"])
#
# hvap_tb_out_train = pd.DataFrame({
#     "Split": "train",
#     id_col: train_df[id_col].values,
#     "HVap_Tb_true": y_Tb_train,
#     "HVap_Tb_pred": HVap_Tb_pred_train
# })
# hvap_tb_out_test = pd.DataFrame({
#     "Split": "test",
#     id_col: test_df[id_col].values,
#     "HVap_Tb_true": y_Tb_test,
#     "HVap_Tb_pred": HVap_Tb_pred_test
# })
#
# tb_out_train = pd.DataFrame({
#     "Split": "train",
#     id_col: train_df[id_col].values,
#     "Tb_true": train_arr["Tb"],
#     "Tb_pred": Tb_pred_train
# })
# tb_out_test = pd.DataFrame({
#     "Split": "test",
#     id_col: test_df[id_col].values,
#     "Tb_true": test_arr["Tb"],
#     "Tb_pred": Tb_pred_test
# })
#
# summary_rows = [
#     hvap_tb_metrics_train, hvap_tb_metrics_test,
#     tb_metrics_train, tb_metrics_test,
#     baseline_metrics_train, baseline_metrics_test,
#     final_metrics_train, final_metrics_test
# ]
# summary_df = pd.DataFrame(summary_rows)
#
# out_path = "internal_energy_actual_vs_pred_with_residual_GBDT_train_test_split.xlsx"
# with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
#     long_compare.to_excel(writer, sheet_name="compare_long", index=False)
#     summary_df.to_excel(writer, sheet_name="summary", index=False)
#     pd.concat([hvap_tb_out_train, hvap_tb_out_test], ignore_index=True).to_excel(writer, sheet_name="HVap_Tb_submodel", index=False)
#     pd.concat([tb_out_train, tb_out_test], ignore_index=True).to_excel(writer, sheet_name="Tb_submodel", index=False)
#
# print(f"\n✅ 结果已保存到: {out_path}")
#
# print("\n📊 总模型评估（基准 + 残差GBDT修正，测试集）：")
# print(f"R²  = {final_metrics_test['R2']:.4f}")
# print(f"MSE = {final_metrics_test['MSE']:.6f}")
# print(f"ARD = {final_metrics_test['ARD_%']:.2f}%")
# print(f"✅ 误差 ≤ 1% 的数据点数量: {final_metrics_test['within_1pct']}")
# print(f"✅ 误差 ≤ 5% 的数据点数量: {final_metrics_test['within_5pct']}")
# print(f"✅ 误差 ≤ 10% 的数据点数量: {final_metrics_test['within_10pct']}")



import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import HuberRegressor
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


# =========================
# 0. 参数区
# =========================
main_file = "internal energy 207.xlsx"
main_sheet = "Sheet1"

tb_descriptor_file = "selected_25_descriptors_boiling.xlsx"
tb_descriptor_target = "internal energy at boiling temperature"

random_state = 42
Tb0 = 222.543


# =========================
# 1. 读取主数据表
# =========================
df = pd.read_excel(main_file, sheet_name=main_sheet).copy()

id_col = df.columns[0]
group_cols = list(df.columns[13:32])   # 第14~32列：19个基团
temp_cols = list(df.columns[32:42])    # 第33~42列：10个温度
target_cols = list(df.columns[42:52])  # 第43~52列：内能目标变量

tb_col_idx = 5

# 转数值
for col in group_cols + temp_cols + target_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df.iloc[:, tb_col_idx] = pd.to_numeric(
    df.iloc[:, tb_col_idx],
    errors="coerce"
)

# 只保留至少有一个有效目标点的物质
valid_material_mask = df[target_cols].notna().any(axis=1)
df = df.loc[valid_material_mask].copy().reset_index(drop=True)

print(f"有效物质数: {len(df)}")


# =========================
# 2. 按物质 8:2 划分
# =========================
unique_materials = df[id_col].dropna().unique()

train_materials, test_materials = train_test_split(
    unique_materials,
    test_size=0.2,
    random_state=random_state
)

train_materials = set(train_materials)
test_materials = set(test_materials)

train_row_mask = df[id_col].isin(train_materials).values
test_row_mask = df[id_col].isin(test_materials).values

train_df = df.loc[train_row_mask].copy().reset_index(drop=True)
test_df = df.loc[test_row_mask].copy().reset_index(drop=True)

print("========== 按物质划分 ==========")
print(f"总物质数: {len(unique_materials)}")
print(f"训练集物质数: {len(train_materials)}")
print(f"测试集物质数: {len(test_materials)}")
print(f"训练集行数: {len(train_df)}")
print(f"测试集行数: {len(test_df)}")


# =========================
# 3. 读取并切分 Tb 描述符表
# =========================
df_Tb = pd.read_excel(tb_descriptor_file).copy()

if id_col in df_Tb.columns:
    train_df_Tb = df_Tb[df_Tb[id_col].isin(train_materials)].copy().reset_index(drop=True)
    test_df_Tb = df_Tb[df_Tb[id_col].isin(test_materials)].copy().reset_index(drop=True)
else:
    if len(df_Tb) != len(df):
        raise ValueError(
            f"{tb_descriptor_file} 没有 {id_col} 列，且行数 {len(df_Tb)} 与主表 {len(df)} 不一致，无法安全切分。"
        )

    train_df_Tb = df_Tb.loc[train_row_mask].copy().reset_index(drop=True)
    test_df_Tb = df_Tb.loc[test_row_mask].copy().reset_index(drop=True)


# =========================
# 4. 工具函数
# =========================
def prepare_descriptor_xy(df_desc, target_col, id_col=None):
    drop_cols = [target_col]

    if id_col is not None and id_col in df_desc.columns:
        drop_cols.append(id_col)

    X = df_desc.drop(columns=drop_cols, errors="ignore").copy()
    X = X.apply(pd.to_numeric, errors="coerce")

    y = pd.to_numeric(df_desc[target_col], errors="coerce").values

    feature_cols = X.columns.tolist()

    return X, y, feature_cols


def fill_with_train_median(X_train, X_test):
    med = X_train.median(numeric_only=True)

    X_train_filled = X_train.fillna(med)
    X_test_filled = X_test.fillna(med)

    return X_train_filled, X_test_filled


def get_arrays(df_part):
    return {
        "ids": df_part[id_col].values,
        "Nk": df_part[group_cols].apply(pd.to_numeric, errors="coerce").values,
        "T": df_part[temp_cols].apply(pd.to_numeric, errors="coerce").values,
        "Target": df_part[target_cols].apply(pd.to_numeric, errors="coerce").values,
        "Tb": pd.to_numeric(df_part.iloc[:, tb_col_idx], errors="coerce").values,
    }


def evaluate_scalar_regression(y_true, y_pred, model_name, split_name):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = np.isfinite(y_true) & np.isfinite(y_pred)

    y_true_valid = y_true[mask]
    y_pred_valid = y_pred[mask]

    if len(y_true_valid) == 0:
        print(f"\n{model_name} - {split_name}: 无有效样本")
        return {
            "Model": model_name,
            "Split": split_name,
            "R2": np.nan,
            "MSE": np.nan
        }

    r2 = r2_score(y_true_valid, y_pred_valid)
    mse = mean_squared_error(y_true_valid, y_pred_valid)

    print(f"\n{model_name} - {split_name}")
    print(f"R2  = {r2:.6f}")
    print(f"MSE = {mse:.6f}")

    return {
        "Model": model_name,
        "Split": split_name,
        "R2": r2,
        "MSE": mse
    }


def eval_final_regression(
    y_true,
    y_pred,
    model_name,
    split_name,
    strict_less=False
):
    """
    strict_less=False：统计 <=1%, <=5%, <=10%
    strict_less=True ：统计 <1%, <5%, <10%
    """

    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = np.isfinite(y_true) & np.isfinite(y_pred)

    y_true_valid = y_true[mask]
    y_pred_valid = y_pred[mask]

    relative_error_full = np.full_like(y_true, np.nan, dtype=float)

    if len(y_true_valid) == 0:
        print(f"\n{model_name} - {split_name}: 无有效样本")
        return {
            "Model": model_name,
            "Split": split_name,
            "R2": np.nan,
            "MSE": np.nan,
            "ARD_%": np.nan,
            "within_1pct": 0,
            "within_5pct": 0,
            "within_10pct": 0
        }, relative_error_full

    r2 = r2_score(y_true_valid, y_pred_valid)
    mse = mean_squared_error(y_true_valid, y_pred_valid)

    relative_error_valid = np.full_like(y_true_valid, np.nan, dtype=float)

    nonzero_mask = np.abs(y_true_valid) > 1e-12

    if np.any(nonzero_mask):
        relative_error_valid[nonzero_mask] = np.abs(
            (y_pred_valid[nonzero_mask] - y_true_valid[nonzero_mask])
            / y_true_valid[nonzero_mask]
        ) * 100

        ard = np.nanmean(relative_error_valid)
    else:
        ard = np.nan

    relative_error_full[mask] = relative_error_valid

    if strict_less:
        within_1pct = np.sum(relative_error_valid < 1)
        within_5pct = np.sum(relative_error_valid < 5)
        within_10pct = np.sum(relative_error_valid < 10)
    else:
        within_1pct = np.sum(relative_error_valid <= 1)
        within_5pct = np.sum(relative_error_valid <= 5)
        within_10pct = np.sum(relative_error_valid <= 10)

    print(f"\n{model_name} - {split_name}")
    print(f"R2  = {r2:.6f}")
    print(f"MSE = {mse:.6f}")
    print(f"ARD = {ard:.2f}%")

    if strict_less:
        print(f"误差 < 1% 的点数: {within_1pct}")
        print(f"误差 < 5% 的点数: {within_5pct}")
        print(f"误差 < 10% 的点数: {within_10pct}")
    else:
        print(f"误差 <= 1% 的点数: {within_1pct}")
        print(f"误差 <= 5% 的点数: {within_5pct}")
        print(f"误差 <= 10% 的点数: {within_10pct}")

    return {
        "Model": model_name,
        "Split": split_name,
        "R2": r2,
        "MSE": mse,
        "ARD_%": ard,
        "within_1pct": within_1pct,
        "within_5pct": within_5pct,
        "within_10pct": within_10pct
    }, relative_error_full


def eval_residual_regression(y_true, y_pred, model_name, split_name):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = np.isfinite(y_true) & np.isfinite(y_pred)

    y_true_valid = y_true[mask]
    y_pred_valid = y_pred[mask]

    if len(y_true_valid) == 0:
        print(f"\n{model_name} - {split_name}: 无有效样本")
        return {
            "Model": model_name,
            "Split": split_name,
            "R2": np.nan,
            "MSE": np.nan
        }

    r2 = r2_score(y_true_valid, y_pred_valid)
    mse = mean_squared_error(y_true_valid, y_pred_valid)

    print(f"\n{model_name} - {split_name}")
    print(f"Residual R2  = {r2:.6f}")
    print(f"Residual MSE = {mse:.6f}")

    return {
        "Model": model_name,
        "Split": split_name,
        "R2": r2,
        "MSE": mse
    }


def collect_true_pred(df_part, pred_df, value_cols):
    y_true_all = []
    y_pred_all = []

    for col in value_cols:
        actual = pd.to_numeric(df_part[col], errors="coerce").to_numpy(dtype=float)
        pred = pd.to_numeric(pred_df[col], errors="coerce").to_numpy(dtype=float)

        m = np.isfinite(actual) & np.isfinite(pred)

        if np.any(m):
            y_true_all.append(actual[m])
            y_pred_all.append(pred[m])

    if len(y_true_all) == 0:
        return np.array([]), np.array([])

    return np.concatenate(y_true_all), np.concatenate(y_pred_all)


# =========================
# 5. 构造 train/test 数组
# =========================
train_arr = get_arrays(train_df)
test_arr = get_arrays(test_df)


# =========================
# 6. Internal_energy_Tb 子模型：只用训练集
# =========================
X_Tb_train, y_Tb_train, feature_cols = prepare_descriptor_xy(
    train_df_Tb,
    tb_descriptor_target,
    id_col=id_col
)

X_Tb_test, y_Tb_test, _ = prepare_descriptor_xy(
    test_df_Tb,
    tb_descriptor_target,
    id_col=id_col
)

X_Tb_test = X_Tb_test.reindex(columns=feature_cols)

X_Tb_train, X_Tb_test = fill_with_train_median(
    X_Tb_train,
    X_Tb_test
)

mask_target_tb_train = np.isfinite(y_Tb_train)
mask_target_tb_test = np.isfinite(y_Tb_test)

target_tb_model = RandomForestRegressor(
    n_estimators=100,
    random_state=random_state,
    n_jobs=-1
)

target_tb_model.fit(
    X_Tb_train.loc[mask_target_tb_train],
    y_Tb_train[mask_target_tb_train]
)

Target_Tb_pred_train = target_tb_model.predict(X_Tb_train)
Target_Tb_pred_test = target_tb_model.predict(X_Tb_test)

target_tb_metrics_train = evaluate_scalar_regression(
    y_Tb_train[mask_target_tb_train],
    Target_Tb_pred_train[mask_target_tb_train],
    "Internal_energy_Tb_submodel",
    "train"
)

target_tb_metrics_test = evaluate_scalar_regression(
    y_Tb_test[mask_target_tb_test],
    Target_Tb_pred_test[mask_target_tb_test],
    "Internal_energy_Tb_submodel",
    "test"
)


# =========================
# 7. Tb 子模型：只用训练集
# =========================
poly = PolynomialFeatures(degree=2, include_bias=False)

Nk_poly_train = poly.fit_transform(train_arr["Nk"])
Nk_poly_test = poly.transform(test_arr["Nk"])

tb_train_mask = (
    np.isfinite(train_arr["Tb"])
    & np.isfinite(Nk_poly_train).all(axis=1)
)

tb_test_mask = (
    np.isfinite(test_arr["Tb"])
    & np.isfinite(Nk_poly_test).all(axis=1)
)

model_Tb = HuberRegressor(
    max_iter=10000
)

model_Tb.fit(
    Nk_poly_train[tb_train_mask],
    np.exp(train_arr["Tb"][tb_train_mask] / Tb0)
)

Tb_pred_train = Tb0 * np.log(
    np.clip(
        model_Tb.predict(Nk_poly_train),
        1e-6,
        None
    )
)

Tb_pred_test = Tb0 * np.log(
    np.clip(
        model_Tb.predict(Nk_poly_test),
        1e-6,
        None
    )
)

tb_metrics_train = evaluate_scalar_regression(
    train_arr["Tb"][tb_train_mask],
    Tb_pred_train[tb_train_mask],
    "Tb_submodel",
    "train"
)

tb_metrics_test = evaluate_scalar_regression(
    test_arr["Tb"][tb_test_mask],
    Tb_pred_test[tb_test_mask],
    "Tb_submodel",
    "test"
)


# =========================
# 8. A_k baseline 模型：只用训练集
# =========================
G_train = train_arr["Nk"]
G_test = test_arr["Nk"]

X_rows_train = []
y_rows_train = []

for i in range(len(train_df)):
    if (
        not np.isfinite(Tb_pred_train[i])
        or not np.isfinite(Target_Tb_pred_train[i])
        or not np.isfinite(G_train[i]).all()
    ):
        continue

    for tcol, col in zip(temp_cols, target_cols):
        Tj = train_df.at[i, tcol]
        yj_actual = train_df.at[i, col]

        if np.isnan(Tj) or np.isnan(yj_actual):
            continue

        Xj = (Tj - Tb_pred_train[i]) * G_train[i]
        yj = yj_actual - Target_Tb_pred_train[i]

        X_rows_train.append(Xj)
        y_rows_train.append(yj)

X_A_train = np.array(X_rows_train, dtype=float)
y_A_train = np.array(y_rows_train, dtype=float)

A_solver = HuberRegressor(
    fit_intercept=False,
    max_iter=5000
)

A_solver.fit(
    X_A_train,
    y_A_train
)

A_vec = A_solver.coef_


# =========================
# 9. 生成 baseline 预测
# =========================
def build_baseline_predictions(df_part, G_part, Tb_pred_part, target_ref_part):
    pred_df = pd.DataFrame(index=df_part.index, columns=target_cols, dtype=float)

    for i in range(len(df_part)):
        if (
            not np.isfinite(Tb_pred_part[i])
            or not np.isfinite(target_ref_part[i])
            or not np.isfinite(G_part[i]).all()
        ):
            pred_df.loc[i, :] = np.nan
            continue

        for tcol, col in zip(temp_cols, target_cols):
            Tj = df_part.at[i, tcol]

            if np.isnan(Tj):
                pred_df.at[i, col] = np.nan
                continue

            Xj = (Tj - Tb_pred_part[i]) * G_part[i]
            pred_df.at[i, col] = target_ref_part[i] + Xj @ A_vec

    return pred_df


Target_pred_baseline_train = build_baseline_predictions(
    train_df,
    G_train,
    Tb_pred_train,
    Target_Tb_pred_train
)

Target_pred_baseline_test = build_baseline_predictions(
    test_df,
    G_test,
    Tb_pred_test,
    Target_Tb_pred_test
)


# =========================
# 10. 残差数据集
# =========================
def build_residual_dataset(
    df_part,
    G_part,
    Tb_pred_part,
    target_ref_part,
    baseline_pred_df
):
    residual_features = []
    residual_targets = []
    sample_groups = []

    for tcol, col in zip(temp_cols, target_cols):
        Tj = df_part[tcol].to_numpy(dtype=float)
        yj_actual = df_part[col].to_numpy(dtype=float)

        msk = (
            (~np.isnan(Tj))
            & (~np.isnan(yj_actual))
            & (~baseline_pred_df[col].isna().to_numpy())
        )

        for i in np.where(msk)[0]:
            baseline_pred = baseline_pred_df.at[i, col]

            if not np.isfinite(baseline_pred):
                continue

            if (
                not np.isfinite(G_part[i]).all()
                or not np.isfinite(Tb_pred_part[i])
                or not np.isfinite(target_ref_part[i])
            ):
                continue

            base_features = list(G_part[i])

            temp_features = [
                Tj[i],
                Tj[i] - Tb_pred_part[i],
                Tj[i] / Tb_pred_part[i] if Tb_pred_part[i] > 0 else 0.0,
                np.log(Tj[i]) if Tj[i] > 0 else 0.0,
            ]

            baseline_features = [
                baseline_pred
            ]

            ref_features = [
                Tb_pred_part[i],
                target_ref_part[i]
            ]

            all_features = (
                base_features
                + temp_features
                + baseline_features
                + ref_features
            )

            residual_features.append(all_features)

            residual = yj_actual[i] - baseline_pred
            residual_targets.append(residual)

            sample_groups.append(df_part.at[i, id_col])

    residual_features = np.array(residual_features, dtype=float)
    residual_targets = np.array(residual_targets, dtype=float)
    sample_groups = np.array(sample_groups)

    return residual_features, residual_targets, sample_groups


residual_X_train, residual_y_train, residual_groups_train = build_residual_dataset(
    train_df,
    G_train,
    Tb_pred_train,
    Target_Tb_pred_train,
    Target_pred_baseline_train
)

residual_X_test, residual_y_test, residual_groups_test = build_residual_dataset(
    test_df,
    G_test,
    Tb_pred_test,
    Target_Tb_pred_test,
    Target_pred_baseline_test
)

print(f"\n残差训练集形状: {residual_X_train.shape}")
print(f"残差目标形状: {residual_y_train.shape}")
print(f"残差测试集形状: {residual_X_test.shape}")


# =========================
# 11. 最终残差模型：GBDT
# =========================
residual_model = GradientBoostingRegressor(
    n_estimators=200,
    learning_rate=0.05,
    max_depth=5,
    min_samples_split=20,
    min_samples_leaf=10,
    random_state=41
)

print("\n训练最终残差 GBDT 模型...")
residual_model.fit(
    residual_X_train,
    residual_y_train
)

residual_pred_train = residual_model.predict(residual_X_train)
residual_pred_test = residual_model.predict(residual_X_test)


# =========================
# 12. 生成最终预测
# =========================
def build_final_predictions(
    df_part,
    G_part,
    Tb_pred_part,
    target_ref_part,
    baseline_pred_df
):
    final_pred_df = pd.DataFrame(index=df_part.index, columns=target_cols, dtype=float)

    for tcol, col in zip(temp_cols, target_cols):
        Tj = df_part[tcol].to_numpy(dtype=float)

        features_list = []
        valid_indices = []

        for i in range(len(df_part)):
            if np.isnan(Tj[i]):
                continue

            baseline_pred = baseline_pred_df.at[i, col]

            if pd.isna(baseline_pred) or not np.isfinite(baseline_pred):
                continue

            if (
                not np.isfinite(G_part[i]).all()
                or not np.isfinite(Tb_pred_part[i])
                or not np.isfinite(target_ref_part[i])
            ):
                continue

            base_features = list(G_part[i])

            temp_features = [
                Tj[i],
                Tj[i] - Tb_pred_part[i],
                Tj[i] / Tb_pred_part[i] if Tb_pred_part[i] > 0 else 0.0,
                np.log(Tj[i]) if Tj[i] > 0 else 0.0,
            ]

            baseline_features = [
                baseline_pred
            ]

            ref_features = [
                Tb_pred_part[i],
                target_ref_part[i]
            ]

            all_features = (
                base_features
                + temp_features
                + baseline_features
                + ref_features
            )

            features_list.append(all_features)
            valid_indices.append(i)

        if len(features_list) > 0:
            features_array = np.array(features_list, dtype=float)
            residual_pred = residual_model.predict(features_array)

            for idx, residual_val in zip(valid_indices, residual_pred):
                final_pred_df.at[idx, col] = (
                    baseline_pred_df.at[idx, col]
                    + residual_val
                )

    return final_pred_df


Target_pred_final_train = build_final_predictions(
    train_df,
    G_train,
    Tb_pred_train,
    Target_Tb_pred_train,
    Target_pred_baseline_train
)

Target_pred_final_test = build_final_predictions(
    test_df,
    G_test,
    Tb_pred_test,
    Target_Tb_pred_test,
    Target_pred_baseline_test
)


# =========================
# 13. 评估
# =========================
print("\n=== 基线模型性能 ===")

y_train_true_base, y_train_pred_base = collect_true_pred(
    train_df,
    Target_pred_baseline_train,
    target_cols
)

y_test_true_base, y_test_pred_base = collect_true_pred(
    test_df,
    Target_pred_baseline_test,
    target_cols
)

baseline_metrics_train, rel_err_base_train = eval_final_regression(
    y_train_true_base,
    y_train_pred_base,
    "Baseline_model",
    "train",
    strict_less=False
)

baseline_metrics_test, rel_err_base_test = eval_final_regression(
    y_test_true_base,
    y_test_pred_base,
    "Baseline_model",
    "test",
    strict_less=False
)


print("\n=== 最终模型性能（baseline + residual GBDT）===")

y_train_true_final, y_train_pred_final = collect_true_pred(
    train_df,
    Target_pred_final_train,
    target_cols
)

y_test_true_final, y_test_pred_final = collect_true_pred(
    test_df,
    Target_pred_final_test,
    target_cols
)

final_metrics_train, rel_err_train = eval_final_regression(
    y_train_true_final,
    y_train_pred_final,
    "Final_GBDT_model",
    "train",
    strict_less=False
)

final_metrics_test, rel_err_test = eval_final_regression(
    y_test_true_final,
    y_test_pred_final,
    "Final_GBDT_model",
    "test",
    strict_less=False
)


# =========================
# 13.1 residual 层面评估
# =========================
residual_metrics_train = eval_residual_regression(
    residual_y_train,
    residual_pred_train,
    "Residual_GBDT",
    "train"
)

residual_metrics_test = eval_residual_regression(
    residual_y_test,
    residual_pred_test,
    "Residual_GBDT",
    "test"
)


# =========================
# 13.2 完整数据集统计：训练集 + 测试集
# =========================
y_all_true_base = np.concatenate([
    y_train_true_base,
    y_test_true_base
])

y_all_pred_base = np.concatenate([
    y_train_pred_base,
    y_test_pred_base
])

baseline_metrics_all, rel_err_base_all = eval_final_regression(
    y_all_true_base,
    y_all_pred_base,
    "Baseline_model",
    "all_train_plus_test",
    strict_less=True
)

y_all_true_final = np.concatenate([
    y_train_true_final,
    y_test_true_final
])

y_all_pred_final = np.concatenate([
    y_train_pred_final,
    y_test_pred_final
])

final_metrics_all, rel_err_final_all = eval_final_regression(
    y_all_true_final,
    y_all_pred_final,
    "Final_GBDT_model",
    "all_train_plus_test",
    strict_less=True
)

residual_y_all = np.concatenate([
    residual_y_train,
    residual_y_test
])

residual_pred_all = np.concatenate([
    residual_pred_train,
    residual_pred_test
])

residual_metrics_all = eval_residual_regression(
    residual_y_all,
    residual_pred_all,
    "Residual_GBDT",
    "all_train_plus_test"
)

print("\nFinal_GBDT_model 完整数据集 Internal Energy 预测偏差 1%，5%，10%分别为：")
print(final_metrics_all["within_1pct"])
print(final_metrics_all["within_5pct"])
print(final_metrics_all["within_10pct"])


# =========================
# 14. 分温度点评估
# =========================
print("\n=== 分温度点评估（最终模型，训练集）===")

for tcol, col in zip(temp_cols, target_cols):
    actual = train_df[col].to_numpy(dtype=float)
    pred = Target_pred_final_train[col].to_numpy(dtype=float)

    m = np.isfinite(actual) & np.isfinite(pred)

    if np.any(m):
        mse_temp = mean_squared_error(actual[m], pred[m])
        r2_temp = r2_score(actual[m], pred[m])

        print(f"{tcol}: MSE = {mse_temp:.6f}, R2 = {r2_temp:.6f}")


print("\n=== 分温度点评估（最终模型，测试集）===")

for tcol, col in zip(temp_cols, target_cols):
    actual = test_df[col].to_numpy(dtype=float)
    pred = Target_pred_final_test[col].to_numpy(dtype=float)

    m = np.isfinite(actual) & np.isfinite(pred)

    if np.any(m):
        mse_temp = mean_squared_error(actual[m], pred[m])
        r2_temp = r2_score(actual[m], pred[m])

        print(f"{tcol}: MSE = {mse_temp:.6f}, R2 = {r2_temp:.6f}")


# =========================
# 15. 保存结果
# =========================
def build_long_compare(
    df_part,
    split_name,
    Tb_pred_part,
    target_ref_part,
    baseline_pred_df,
    final_pred_df
):
    rows = []

    for idx in range(len(df_part)):
        ID = df_part.at[idx, id_col]

        for j, (tcol, col) in enumerate(zip(temp_cols, target_cols), start=1):
            T_val = df_part.at[idx, tcol]
            y_actual = df_part.at[idx, col]

            y_base = (
                baseline_pred_df.at[idx, col]
                if pd.notna(baseline_pred_df.at[idx, col])
                else np.nan
            )

            y_final = (
                final_pred_df.at[idx, col]
                if pd.notna(final_pred_df.at[idx, col])
                else np.nan
            )

            err_base = (
                y_base - y_actual
                if pd.notna(y_base) and pd.notna(y_actual)
                else np.nan
            )

            err_final = (
                y_final - y_actual
                if pd.notna(y_final) and pd.notna(y_actual)
                else np.nan
            )

            residual_correction = (
                y_final - y_base
                if pd.notna(y_final) and pd.notna(y_base)
                else np.nan
            )

            rel_err_base = (
                abs((y_base - y_actual) / y_actual) * 100
                if pd.notna(y_base) and pd.notna(y_actual) and abs(y_actual) > 1e-12
                else np.nan
            )

            rel_err_final = (
                abs((y_final - y_actual) / y_actual) * 100
                if pd.notna(y_final) and pd.notna(y_actual) and abs(y_actual) > 1e-12
                else np.nan
            )

            rows.append({
                "Split": split_name,
                id_col: ID,
                "temp_index": j,
                "temp_col": tcol,
                "T": T_val,
                "Internal_energy_actual": y_actual,
                "Internal_energy_baseline": y_base,
                "Internal_energy_final": y_final,
                "error_baseline": err_base,
                "error_final": err_final,
                "relative_error_baseline_%": rel_err_base,
                "relative_error_final_%": rel_err_final,
                "residual_correction": residual_correction,
                "T_ref": Tb_pred_part[idx],
                "Internal_energy_ref": target_ref_part[idx]
            })

    return pd.DataFrame(rows)


long_train = build_long_compare(
    train_df,
    "train",
    Tb_pred_train,
    Target_Tb_pred_train,
    Target_pred_baseline_train,
    Target_pred_final_train
)

long_test = build_long_compare(
    test_df,
    "test",
    Tb_pred_test,
    Target_Tb_pred_test,
    Target_pred_baseline_test,
    Target_pred_final_test
)

long_compare = pd.concat(
    [long_train, long_test],
    ignore_index=True
).sort_values(["Split", id_col, "temp_index"])

long_all = long_compare.copy()
long_all["Split"] = "all_train_plus_test"


# =========================
# 16. 子模型输出
# =========================
target_tb_out_train = pd.DataFrame({
    "Split": "train",
    id_col: train_df[id_col].values,
    "Internal_energy_Tb_true": y_Tb_train,
    "Internal_energy_Tb_pred": Target_Tb_pred_train
})

target_tb_out_test = pd.DataFrame({
    "Split": "test",
    id_col: test_df[id_col].values,
    "Internal_energy_Tb_true": y_Tb_test,
    "Internal_energy_Tb_pred": Target_Tb_pred_test
})

tb_out_train = pd.DataFrame({
    "Split": "train",
    id_col: train_df[id_col].values,
    "Tb_true": train_arr["Tb"],
    "Tb_pred": Tb_pred_train
})

tb_out_test = pd.DataFrame({
    "Split": "test",
    id_col: test_df[id_col].values,
    "Tb_true": test_arr["Tb"],
    "Tb_pred": Tb_pred_test
})


# =========================
# 17. 汇总表
# =========================
summary_rows = [
    target_tb_metrics_train,
    target_tb_metrics_test,
    tb_metrics_train,
    tb_metrics_test,
    baseline_metrics_train,
    baseline_metrics_test,
    baseline_metrics_all,
    final_metrics_train,
    final_metrics_test,
    final_metrics_all,
    residual_metrics_train,
    residual_metrics_test,
    residual_metrics_all
]

summary_df = pd.DataFrame(summary_rows)


# =========================
# 18. 保存 Excel
# =========================
out_path = "internal_energy_actual_vs_pred_with_residual_GBDT_train_test_split.xlsx"

with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
    long_compare.to_excel(
        writer,
        sheet_name="compare_long",
        index=False
    )

    long_all.to_excel(
        writer,
        sheet_name="all_compare_long",
        index=False
    )

    summary_df.to_excel(
        writer,
        sheet_name="summary",
        index=False
    )

    pd.concat(
        [target_tb_out_train, target_tb_out_test],
        ignore_index=True
    ).to_excel(
        writer,
        sheet_name="Internal_energy_Tb_submodel",
        index=False
    )

    pd.concat(
        [tb_out_train, tb_out_test],
        ignore_index=True
    ).to_excel(
        writer,
        sheet_name="Tb_submodel",
        index=False
    )

print(f"\n结果已保存到: {out_path}")


# =========================
# 19. 输出最终测试集和完整数据集指标
# =========================
print("\n总模型评估（baseline + residual GBDT，测试集）：")
print(f"R2  = {final_metrics_test['R2']:.4f}")
print(f"MSE = {final_metrics_test['MSE']:.6f}")
print(f"ARD = {final_metrics_test['ARD_%']:.2f}%")
print(f"误差 <= 1% 的数据点数量: {final_metrics_test['within_1pct']}")
print(f"误差 <= 5% 的数据点数量: {final_metrics_test['within_5pct']}")
print(f"误差 <= 10% 的数据点数量: {final_metrics_test['within_10pct']}")

print("\n总模型评估（baseline + residual GBDT，完整数据集 train + test）：")
print(f"R2  = {final_metrics_all['R2']:.4f}")
print(f"MSE = {final_metrics_all['MSE']:.6f}")
print(f"ARD = {final_metrics_all['ARD_%']:.2f}%")
print("1%，5%，10%分别为：")
print(final_metrics_all["within_1pct"])
print(final_metrics_all["within_5pct"])
print(final_metrics_all["within_10pct"])


# =========================
# 20. 输出模型结构记录
# =========================
print("\n当前 Internal Energy baseline + GBDT residual 模型结构:")
print("Internal_energy_Tb_submodel: RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1), input = selected_25_descriptors_boiling.xlsx")
print("Tb_submodel: HuberRegressor(max_iter=10000), input = PolynomialFeatures(Nk, degree=2)")
print("Baseline: Internal_energy_baseline = Internal_energy_Tb_pred + (T - Tb_pred) * sum(Ak * Nk)")
print("A_solver: HuberRegressor(fit_intercept=False, max_iter=5000)")
print("Residual model: GradientBoostingRegressor(n_estimators=200, learning_rate=0.05, max_depth=5, min_samples_split=20, min_samples_leaf=10, random_state=41)")
print("Residual target: Internal_energy_actual - Internal_energy_baseline")
print("Residual features: Nk + T + (T-Tb) + T/Tb + ln(T) + Internal_energy_baseline + Tb_pred + Internal_energy_Tb_pred")
print("Final prediction: Internal_energy_final = Internal_energy_baseline + residual_pred")
print("Final all-data statistics use strict thresholds: <1%, <5%, <10%")