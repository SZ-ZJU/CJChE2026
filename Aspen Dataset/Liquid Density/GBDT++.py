# import pandas as pd
# import numpy as np
# from sklearn.ensemble import GradientBoostingRegressor
# from sklearn.preprocessing import PolynomialFeatures
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split
#
# # =========================
# # 0. 参数区
# # =========================
# main_file = "liquid density.xlsx"
# main_sheet = "Sheet1"
#
# tb_descriptor_file = "selected_25_descriptors_boiling.xlsx"
# tb_descriptor_sheet = "Sheet1"
# tb_descriptor_target = "ASPEN Liquid Density at BoilingTemperature(g/cc)"
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
# group_cols = list(df.columns[12:31])   # 第13~31列：基团
# temp_cols = list(df.columns[31:41])    # 第32~41列：温度
# v_cols = list(df.columns[41:51])       # 第42~51列：液体密度
# tb_col_idx = 5
#
# # 转数值
# for col in group_cols + temp_cols + v_cols:
#     df[col] = pd.to_numeric(df[col], errors="coerce")
# df.iloc[:, tb_col_idx] = pd.to_numeric(df.iloc[:, tb_col_idx], errors="coerce")
#
# # 只保留至少有一个有效目标点的物质
# valid_material_mask = df[v_cols].notna().any(axis=1)
# df = df.loc[valid_material_mask].copy().reset_index(drop=True)
#
# print(f"有效物质数: {len(df)}")
#
# # =========================
# # 2. 按物质 8:2 划分（只用于最终基线+残差模型）
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
# # 3. 工具函数
# # =========================
# def get_arrays(df_part):
#     return {
#         "ids": df_part[id_col].values,
#         "Nk": df_part[group_cols].apply(pd.to_numeric, errors="coerce").values,
#         "T": df_part[temp_cols].apply(pd.to_numeric, errors="coerce").values,
#         "V": df_part[v_cols].apply(pd.to_numeric, errors="coerce").values,
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
# def collect_true_pred(df_part, pred_df, value_cols):
#     y_true_all = []
#     y_pred_all = []
#
#     for col in value_cols:
#         actual = pd.to_numeric(df_part[col], errors="coerce").to_numpy(dtype=float)
#         pred = pd.to_numeric(pred_df[col], errors="coerce").to_numpy(dtype=float)
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
# # 4. 构造 train/test 数组
# # =========================
# train_arr = get_arrays(train_df)
# test_arr = get_arrays(test_df)
#
# # =========================
# # 5. Density_Tb 子模型（全数据训练，不划分）
# # =========================
# df_Tb = pd.read_excel(tb_descriptor_file, sheet_name=tb_descriptor_sheet).copy()
#
# X_Tb = df_Tb.drop(columns=[tb_descriptor_target], errors="ignore").copy()
# if id_col in X_Tb.columns:
#     X_Tb = X_Tb.drop(columns=[id_col], errors="ignore")
#
# X_Tb = X_Tb.apply(pd.to_numeric, errors="coerce")
# y_Tb = pd.to_numeric(df_Tb[tb_descriptor_target], errors="coerce").values
#
# X_Tb = X_Tb.replace([np.inf, -np.inf], np.nan)
# X_Tb = X_Tb.fillna(X_Tb.median(numeric_only=True))
#
# mask_density_tb = np.isfinite(y_Tb)
#
# density_tb_model = GradientBoostingRegressor(
#     n_estimators=300,
#     learning_rate=0.05,
#     max_depth=4,
#     min_samples_split=10,
#     min_samples_leaf=5,
#     random_state=random_state
# )
# density_tb_model.fit(X_Tb.loc[mask_density_tb], y_Tb[mask_density_tb])
#
# Density_Tb_pred_all = density_tb_model.predict(X_Tb)
#
# density_tb_metrics_all = evaluate_scalar_regression(
#     y_Tb[mask_density_tb],
#     Density_Tb_pred_all[mask_density_tb],
#     "Density_Tb_submodel_GBDT",
#     "all_data"
# )
#
# if len(Density_Tb_pred_all) != len(df):
#     raise ValueError(
#         f"{tb_descriptor_file} 预测行数 = {len(Density_Tb_pred_all)}，与主表物质数 = {len(df)} 不一致。"
#     )
#
# Density_Tb_pred_train = Density_Tb_pred_all[train_row_mask]
# Density_Tb_pred_test = Density_Tb_pred_all[test_row_mask]
#
# # =========================
# # 6. Tb 子模型（全数据训练，不划分）
# # =========================
# Nk_all = df[group_cols].apply(pd.to_numeric, errors="coerce").values
# Tb_raw_all = pd.to_numeric(df.iloc[:, tb_col_idx], errors="coerce").values
#
# poly = PolynomialFeatures(degree=2, include_bias=False)
# Nk_poly_all = poly.fit_transform(Nk_all)
#
# tb_fit_mask = np.isfinite(Tb_raw_all) & np.isfinite(Nk_poly_all).all(axis=1)
#
# tb_model = GradientBoostingRegressor(
#     n_estimators=300,
#     learning_rate=0.05,
#     max_depth=4,
#     min_samples_split=10,
#     min_samples_leaf=5,
#     random_state=random_state
# )
# tb_model.fit(
#     Nk_poly_all[tb_fit_mask],
#     np.exp(Tb_raw_all[tb_fit_mask] / Tb0)
# )
#
# Tb_pred_all_full = np.full(len(df), np.nan, dtype=float)
# tb_predict_mask = np.isfinite(Nk_poly_all).all(axis=1)
# Tb_pred_all_full[tb_predict_mask] = Tb0 * np.log(
#     np.clip(tb_model.predict(Nk_poly_all[tb_predict_mask]), 1e-6, None)
# )
#
# tb_metrics_all = evaluate_scalar_regression(
#     Tb_raw_all[tb_fit_mask],
#     Tb_pred_all_full[tb_fit_mask],
#     "Tb_submodel_GBDT",
#     "all_data"
# )
#
# Tb_pred_train = Tb_pred_all_full[train_row_mask]
# Tb_pred_test = Tb_pred_all_full[test_row_mask]
#
# # =========================
# # 7. A_k 基线模型（只用训练集）
# # =========================
# G_train = train_arr["Nk"]
# G_test = test_arr["Nk"]
#
# X_rows_train = []
# y_rows_train = []
#
# for i in range(len(train_df)):
#     if not np.isfinite(Tb_pred_train[i]) or not np.isfinite(Density_Tb_pred_train[i]) or not np.isfinite(G_train[i]).all():
#         continue
#
#     for tcol, vcol in zip(temp_cols, v_cols):
#         Tj = train_df.at[i, tcol]
#         Vj = train_df.at[i, vcol]
#
#         if np.isnan(Tj) or np.isnan(Vj):
#             continue
#
#         Xj = (Tj - Tb_pred_train[i]) * G_train[i]
#         yj = Vj - Density_Tb_pred_train[i]
#
#         X_rows_train.append(Xj)
#         y_rows_train.append(yj)
#
# X_A_train = np.array(X_rows_train, dtype=float)
# y_A_train = np.array(y_rows_train, dtype=float)
#
# A_solver = GradientBoostingRegressor(
#     n_estimators=300,
#     learning_rate=0.05,
#     max_depth=3,
#     min_samples_split=10,
#     min_samples_leaf=5,
#     random_state=random_state
# )
# A_solver.fit(X_A_train, y_A_train)
#
# # =========================
# # 8. 生成基准预测（train/test 分别生成）
# # =========================
# def build_baseline_predictions(df_part, G_part, Tb_pred_part, density_ref_part):
#     pred_df = pd.DataFrame(index=df_part.index, columns=v_cols, dtype=float)
#
#     for i in range(len(df_part)):
#         if not np.isfinite(Tb_pred_part[i]) or not np.isfinite(density_ref_part[i]) or not np.isfinite(G_part[i]).all():
#             pred_df.loc[i, :] = np.nan
#             continue
#
#         for tcol, vcol in zip(temp_cols, v_cols):
#             Tj = df_part.at[i, tcol]
#
#             if np.isnan(Tj):
#                 pred_df.at[i, vcol] = np.nan
#                 continue
#
#             Xj = ((Tj - Tb_pred_part[i]) * G_part[i]).reshape(1, -1)
#             pred_df.at[i, vcol] = density_ref_part[i] + A_solver.predict(Xj)[0]
#
#     return pred_df
#
# V_pred_baseline_train = build_baseline_predictions(train_df, G_train, Tb_pred_train, Density_Tb_pred_train)
# V_pred_baseline_test = build_baseline_predictions(test_df, G_test, Tb_pred_test, Density_Tb_pred_test)
#
# # =========================
# # 9. 构建残差训练集（只用训练集）
# # =========================
# def build_residual_dataset(df_part, G_part, Tb_pred_part, density_ref_part, baseline_pred_df):
#     residual_features = []
#     residual_targets = []
#
#     for tcol, vcol in zip(temp_cols, v_cols):
#         Tj = df_part[tcol].to_numpy(dtype=float)
#         Vj = df_part[vcol].to_numpy(dtype=float)
#
#         msk = (~np.isnan(Tj)) & (~np.isnan(Vj)) & (~baseline_pred_df[vcol].isna().to_numpy())
#
#         for i in np.where(msk)[0]:
#             baseline_pred = baseline_pred_df.at[i, vcol]
#             if not np.isfinite(baseline_pred):
#                 continue
#
#             if not np.isfinite(G_part[i]).all() or not np.isfinite(Tb_pred_part[i]) or not np.isfinite(density_ref_part[i]):
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
#             ref_features = [Tb_pred_part[i], density_ref_part[i]]
#
#             all_features = base_features + temp_features + baseline_features + ref_features
#             residual_features.append(all_features)
#
#             residual = Vj[i] - baseline_pred
#             residual_targets.append(residual)
#
#     residual_features = np.array(residual_features, dtype=float)
#     residual_targets = np.array(residual_targets, dtype=float)
#     return residual_features, residual_targets
#
# residual_X_train, residual_y_train = build_residual_dataset(
#     train_df, G_train, Tb_pred_train, Density_Tb_pred_train, V_pred_baseline_train
# )
#
# print(f"\n残差训练集形状: {residual_X_train.shape}")
# print(f"残差目标形状: {residual_y_train.shape}")
#
# # =========================
# # 10. 最终残差模型：GBDT
# # =========================
# residual_model = GradientBoostingRegressor(
#     n_estimators=200,
#     learning_rate=0.05,
#     max_depth=5,
#     min_samples_split=20,
#     min_samples_leaf=10,
#     random_state=44
# )
#
# print("\n🚀 训练最终残差 GBDT 模型...")
# residual_model.fit(residual_X_train, residual_y_train)
#
# # =========================
# # 11. 生成最终预测（基准 + 残差修正）
# # =========================
# def build_final_predictions(df_part, G_part, Tb_pred_part, density_ref_part, baseline_pred_df):
#     final_pred_df = pd.DataFrame(index=df_part.index, columns=v_cols, dtype=float)
#
#     for tcol, vcol in zip(temp_cols, v_cols):
#         Tj = df_part[tcol].to_numpy(dtype=float)
#
#         features_list = []
#         valid_indices = []
#
#         for i in range(len(df_part)):
#             if np.isnan(Tj[i]):
#                 continue
#
#             baseline_pred = baseline_pred_df.at[i, vcol]
#             if pd.isna(baseline_pred) or not np.isfinite(baseline_pred):
#                 continue
#
#             if not np.isfinite(G_part[i]).all() or not np.isfinite(Tb_pred_part[i]) or not np.isfinite(density_ref_part[i]):
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
#             ref_features = [Tb_pred_part[i], density_ref_part[i]]
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
#                 final_pred_df.at[idx, vcol] = baseline_pred_df.at[idx, vcol] + residual_val
#
#     return final_pred_df
#
# V_pred_final_train = build_final_predictions(
#     train_df, G_train, Tb_pred_train, Density_Tb_pred_train, V_pred_baseline_train
# )
# V_pred_final_test = build_final_predictions(
#     test_df, G_test, Tb_pred_test, Density_Tb_pred_test, V_pred_baseline_test
# )
#
# # =========================
# # 12. 评估：基线 / 最终（train/test 分开）
# # =========================
# y_train_true_base, y_train_pred_base = collect_true_pred(train_df, V_pred_baseline_train, v_cols)
# y_test_true_base, y_test_pred_base = collect_true_pred(test_df, V_pred_baseline_test, v_cols)
#
# baseline_metrics_train, _ = eval_final_regression(
#     y_train_true_base, y_train_pred_base, "Baseline_model", "train"
# )
# baseline_metrics_test, _ = eval_final_regression(
#     y_test_true_base, y_test_pred_base, "Baseline_model", "test"
# )
#
# y_train_true_final, y_train_pred_final = collect_true_pred(train_df, V_pred_final_train, v_cols)
# y_test_true_final, y_test_pred_final = collect_true_pred(test_df, V_pred_final_test, v_cols)
#
# final_metrics_train, rel_err_train = eval_final_regression(
#     y_train_true_final, y_train_pred_final, "Final_GBDT_model", "train"
# )
# final_metrics_test, rel_err_test = eval_final_regression(
#     y_test_true_final, y_test_pred_final, "Final_GBDT_model", "test"
# )
#
# # =========================
# # 13. 分温度点评估（最终模型）
# # =========================
# print("\n=== 分温度点评估（最终模型，训练集）===")
# for tcol, vcol in zip(temp_cols, v_cols):
#     actual = train_df[vcol].to_numpy(dtype=float)
#     pred = V_pred_final_train[vcol].to_numpy(dtype=float)
#     m = np.isfinite(actual) & np.isfinite(pred)
#     if np.any(m):
#         mse_temp = mean_squared_error(actual[m], pred[m])
#         r2_temp = r2_score(actual[m], pred[m])
#         print(f"{tcol}: MSE = {mse_temp:.6f}, R² = {r2_temp:.6f}")
#
# print("\n=== 分温度点评估（最终模型，测试集）===")
# for tcol, vcol in zip(temp_cols, v_cols):
#     actual = test_df[vcol].to_numpy(dtype=float)
#     pred = V_pred_final_test[vcol].to_numpy(dtype=float)
#     m = np.isfinite(actual) & np.isfinite(pred)
#     if np.any(m):
#         mse_temp = mean_squared_error(actual[m], pred[m])
#         r2_temp = r2_score(actual[m], pred[m])
#         print(f"{tcol}: MSE = {mse_temp:.6f}, R² = {r2_temp:.6f}")
#
# # =========================
# # 14. 保存结果
# # =========================
# def build_long_compare(df_part, split_name, Tb_pred_part, density_ref_part, baseline_pred_df, final_pred_df):
#     rows = []
#     for idx in range(len(df_part)):
#         ID = df_part.at[idx, id_col]
#         for j, (tcol, vcol) in enumerate(zip(temp_cols, v_cols), start=1):
#             T_val = df_part.at[idx, tcol]
#             V_act = df_part.at[idx, vcol]
#             V_base = baseline_pred_df.at[idx, vcol] if pd.notna(baseline_pred_df.at[idx, vcol]) else np.nan
#             V_final = final_pred_df.at[idx, vcol] if pd.notna(final_pred_df.at[idx, vcol]) else np.nan
#
#             err_base = (V_base - V_act) if (pd.notna(V_base) and pd.notna(V_act)) else np.nan
#             err_final = (V_final - V_act) if (pd.notna(V_final) and pd.notna(V_act)) else np.nan
#             residual_correction = (V_final - V_base) if (pd.notna(V_final) and pd.notna(V_base)) else np.nan
#
#             rows.append({
#                 "Split": split_name,
#                 id_col: ID,
#                 "temp_index": j,
#                 "temp_col": tcol,
#                 "T": T_val,
#                 "Density_actual": V_act,
#                 "Density_base": V_base,
#                 "Density_final": V_final,
#                 "error_base": err_base,
#                 "error_final": err_final,
#                 "residual_correction": residual_correction,
#                 "T_ref": Tb_pred_part[idx],
#                 "Density_ref": density_ref_part[idx]
#             })
#     return pd.DataFrame(rows)
#
# long_train = build_long_compare(
#     train_df, "train", Tb_pred_train, Density_Tb_pred_train, V_pred_baseline_train, V_pred_final_train
# )
# long_test = build_long_compare(
#     test_df, "test", Tb_pred_test, Density_Tb_pred_test, V_pred_baseline_test, V_pred_final_test
# )
# long_compare = pd.concat([long_train, long_test], ignore_index=True).sort_values(["Split", id_col, "temp_index"])
#
# density_tb_out = pd.DataFrame({
#     id_col: df[id_col].values,
#     "Density_Tb_true": y_Tb,
#     "Density_Tb_pred": Density_Tb_pred_all
# })
#
# tb_out = pd.DataFrame({
#     id_col: df[id_col].values,
#     "Tb_true": Tb_raw_all,
#     "Tb_pred": Tb_pred_all_full
# })
#
# summary_rows = [
#     density_tb_metrics_all,
#     tb_metrics_all,
#     baseline_metrics_train, baseline_metrics_test,
#     final_metrics_train, final_metrics_test
# ]
# summary_df = pd.DataFrame(summary_rows)
#
# out_path = "liquid_density_actual_vs_pred_with_residual_GBDT_train_test_split.xlsx"
# with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
#     long_compare.to_excel(writer, sheet_name="compare_long", index=False)
#     summary_df.to_excel(writer, sheet_name="summary", index=False)
#     density_tb_out.to_excel(writer, sheet_name="Density_Tb_submodel", index=False)
#     tb_out.to_excel(writer, sheet_name="Tb_submodel", index=False)
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

from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


# =========================
# 0. 参数区
# =========================
main_file = "liquid density.xlsx"
main_sheet = "Sheet1"

tb_descriptor_file = "selected_25_descriptors_boiling.xlsx"
tb_descriptor_sheet = "Sheet1"
tb_descriptor_target = "ASPEN Liquid Density at BoilingTemperature(g/cc)"

random_state = 42
Tb0 = 222.543


# =========================
# 1. 读取主数据表
# =========================
df = pd.read_excel(main_file, sheet_name=main_sheet).copy()

id_col = df.columns[0]
group_cols = list(df.columns[12:31])   # 第13~31列：19个基团
temp_cols = list(df.columns[31:41])    # 第32~41列：10个温度
v_cols = list(df.columns[41:51])       # 第42~51列：液体密度
tb_col_idx = 5

# 转数值
for col in group_cols + temp_cols + v_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df.iloc[:, tb_col_idx] = pd.to_numeric(
    df.iloc[:, tb_col_idx],
    errors="coerce"
)

# 只保留至少有一个有效目标点的物质
valid_material_mask = df[v_cols].notna().any(axis=1)
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

print("\n========== 按物质划分 ==========")
print(f"总物质数: {len(unique_materials)}")
print(f"训练集物质数: {len(train_materials)}")
print(f"测试集物质数: {len(test_materials)}")
print(f"训练集物质行数: {len(train_df)}")
print(f"测试集物质行数: {len(test_df)}")


# =========================
# 3. 工具函数
# =========================
def get_arrays(df_part):
    return {
        "ids": df_part[id_col].values,
        "Nk": df_part[group_cols].apply(pd.to_numeric, errors="coerce").values,
        "T": df_part[temp_cols].apply(pd.to_numeric, errors="coerce").values,
        "V": df_part[v_cols].apply(pd.to_numeric, errors="coerce").values,
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
    print(f"MSE = {mse:.10f}")

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

    relative_error = np.full_like(y_true, np.nan, dtype=float)

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
        }, relative_error

    r2 = r2_score(y_true_valid, y_pred_valid)
    mse = mean_squared_error(y_true_valid, y_pred_valid)

    rel_valid = np.full_like(y_true_valid, np.nan, dtype=float)
    nonzero_mask = np.abs(y_true_valid) > 1e-12

    if np.any(nonzero_mask):
        rel_valid[nonzero_mask] = np.abs(
            (y_pred_valid[nonzero_mask] - y_true_valid[nonzero_mask])
            / y_true_valid[nonzero_mask]
        ) * 100
        ard = np.nanmean(rel_valid)
    else:
        ard = np.nan

    relative_error[mask] = rel_valid

    if strict_less:
        within_1pct = np.sum(rel_valid < 1)
        within_5pct = np.sum(rel_valid < 5)
        within_10pct = np.sum(rel_valid < 10)
    else:
        within_1pct = np.sum(rel_valid <= 1)
        within_5pct = np.sum(rel_valid <= 5)
        within_10pct = np.sum(rel_valid <= 10)

    print(f"\n{model_name} - {split_name}")
    print(f"R2  = {r2:.6f}")
    print(f"MSE = {mse:.10f}")
    print(f"ARD = {ard:.4f}%")

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
    }, relative_error


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
    print(f"Residual MSE = {mse:.10f}")

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
# 4. 构造 train/test 数组
# =========================
train_arr = get_arrays(train_df)
test_arr = get_arrays(test_df)


# =========================
# 5. Density_Tb 子模型：全数据训练
# =========================
df_Tb = pd.read_excel(tb_descriptor_file, sheet_name=tb_descriptor_sheet).copy()

X_Tb = df_Tb.drop(columns=[tb_descriptor_target], errors="ignore").copy()

if id_col in X_Tb.columns:
    X_Tb = X_Tb.drop(columns=[id_col], errors="ignore")

X_Tb = X_Tb.apply(pd.to_numeric, errors="coerce")
y_Tb = pd.to_numeric(
    df_Tb[tb_descriptor_target],
    errors="coerce"
).values

X_Tb = X_Tb.replace([np.inf, -np.inf], np.nan)
X_Tb = X_Tb.fillna(X_Tb.median(numeric_only=True))

mask_density_tb = np.isfinite(y_Tb)

density_tb_model = GradientBoostingRegressor(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=4,
    min_samples_split=10,
    min_samples_leaf=5,
    random_state=random_state
)

density_tb_model.fit(
    X_Tb.loc[mask_density_tb],
    y_Tb[mask_density_tb]
)

Density_Tb_pred_all = density_tb_model.predict(X_Tb)

density_tb_metrics_all = evaluate_scalar_regression(
    y_Tb[mask_density_tb],
    Density_Tb_pred_all[mask_density_tb],
    "Density_Tb_submodel_GBDT",
    "all_data"
)

if len(Density_Tb_pred_all) != len(df):
    raise ValueError(
        f"{tb_descriptor_file} 预测行数 = {len(Density_Tb_pred_all)}，"
        f"与主表物质数 = {len(df)} 不一致。"
    )

Density_Tb_pred_train = Density_Tb_pred_all[train_row_mask]
Density_Tb_pred_test = Density_Tb_pred_all[test_row_mask]


# =========================
# 6. Tb 子模型：全数据训练
# =========================
Nk_all = df[group_cols].apply(pd.to_numeric, errors="coerce").values
Tb_raw_all = pd.to_numeric(df.iloc[:, tb_col_idx], errors="coerce").values

poly = PolynomialFeatures(
    degree=2,
    include_bias=False
)

Nk_poly_all = poly.fit_transform(Nk_all)

tb_fit_mask = (
    np.isfinite(Tb_raw_all)
    & np.isfinite(Nk_poly_all).all(axis=1)
)

tb_model = GradientBoostingRegressor(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=4,
    min_samples_split=10,
    min_samples_leaf=5,
    random_state=random_state
)

tb_model.fit(
    Nk_poly_all[tb_fit_mask],
    np.exp(Tb_raw_all[tb_fit_mask] / Tb0)
)

Tb_pred_all_full = np.full(len(df), np.nan, dtype=float)

tb_predict_mask = np.isfinite(Nk_poly_all).all(axis=1)

Tb_pred_all_full[tb_predict_mask] = Tb0 * np.log(
    np.clip(
        tb_model.predict(Nk_poly_all[tb_predict_mask]),
        1e-6,
        None
    )
)

tb_metrics_all = evaluate_scalar_regression(
    Tb_raw_all[tb_fit_mask],
    Tb_pred_all_full[tb_fit_mask],
    "Tb_submodel_GBDT",
    "all_data"
)

Tb_pred_train = Tb_pred_all_full[train_row_mask]
Tb_pred_test = Tb_pred_all_full[test_row_mask]


# =========================
# 7. A_k 基线模型：只用训练集
# =========================
G_train = train_arr["Nk"]
G_test = test_arr["Nk"]

X_rows_train = []
y_rows_train = []

for i in range(len(train_df)):
    if (
        not np.isfinite(Tb_pred_train[i])
        or not np.isfinite(Density_Tb_pred_train[i])
        or not np.isfinite(G_train[i]).all()
    ):
        continue

    for tcol, vcol in zip(temp_cols, v_cols):
        Tj = train_df.at[i, tcol]
        Vj = train_df.at[i, vcol]

        if np.isnan(Tj) or np.isnan(Vj):
            continue

        Xj = (Tj - Tb_pred_train[i]) * G_train[i]
        yj = Vj - Density_Tb_pred_train[i]

        X_rows_train.append(Xj)
        y_rows_train.append(yj)

X_A_train = np.array(X_rows_train, dtype=float)
y_A_train = np.array(y_rows_train, dtype=float)

A_solver = GradientBoostingRegressor(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=3,
    min_samples_split=10,
    min_samples_leaf=5,
    random_state=random_state
)

A_solver.fit(
    X_A_train,
    y_A_train
)


# =========================
# 8. 生成基准预测
# =========================
def build_baseline_predictions(df_part, G_part, Tb_pred_part, density_ref_part):
    pred_df = pd.DataFrame(index=df_part.index, columns=v_cols, dtype=float)

    for i in range(len(df_part)):
        if (
            not np.isfinite(Tb_pred_part[i])
            or not np.isfinite(density_ref_part[i])
            or not np.isfinite(G_part[i]).all()
        ):
            pred_df.loc[i, :] = np.nan
            continue

        for tcol, vcol in zip(temp_cols, v_cols):
            Tj = df_part.at[i, tcol]

            if np.isnan(Tj):
                pred_df.at[i, vcol] = np.nan
                continue

            Xj = ((Tj - Tb_pred_part[i]) * G_part[i]).reshape(1, -1)
            pred_df.at[i, vcol] = density_ref_part[i] + A_solver.predict(Xj)[0]

    return pred_df


V_pred_baseline_train = build_baseline_predictions(
    train_df,
    G_train,
    Tb_pred_train,
    Density_Tb_pred_train
)

V_pred_baseline_test = build_baseline_predictions(
    test_df,
    G_test,
    Tb_pred_test,
    Density_Tb_pred_test
)


# =========================
# 9. 构建 residual 数据集
# =========================
def build_residual_dataset(df_part, G_part, Tb_pred_part, density_ref_part, baseline_pred_df):
    residual_features = []
    residual_targets = []

    for tcol, vcol in zip(temp_cols, v_cols):
        Tj = df_part[tcol].to_numpy(dtype=float)
        Vj = df_part[vcol].to_numpy(dtype=float)

        msk = (
            (~np.isnan(Tj))
            & (~np.isnan(Vj))
            & (~baseline_pred_df[vcol].isna().to_numpy())
        )

        for i in np.where(msk)[0]:
            baseline_pred = baseline_pred_df.at[i, vcol]

            if not np.isfinite(baseline_pred):
                continue

            if (
                not np.isfinite(G_part[i]).all()
                or not np.isfinite(Tb_pred_part[i])
                or not np.isfinite(density_ref_part[i])
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
                density_ref_part[i]
            ]

            all_features = (
                base_features
                + temp_features
                + baseline_features
                + ref_features
            )

            residual_features.append(all_features)

            residual = Vj[i] - baseline_pred
            residual_targets.append(residual)

    return (
        np.array(residual_features, dtype=float),
        np.array(residual_targets, dtype=float)
    )


residual_X_train, residual_y_train = build_residual_dataset(
    train_df,
    G_train,
    Tb_pred_train,
    Density_Tb_pred_train,
    V_pred_baseline_train
)

residual_X_test, residual_y_test = build_residual_dataset(
    test_df,
    G_test,
    Tb_pred_test,
    Density_Tb_pred_test,
    V_pred_baseline_test
)

print(f"\n残差训练集形状: {residual_X_train.shape}")
print(f"残差目标形状: {residual_y_train.shape}")
print(f"残差测试集形状: {residual_X_test.shape}")
print(f"残差测试目标形状: {residual_y_test.shape}")


# =========================
# 10. 最终 residual GBDT 模型
# =========================
residual_model = GradientBoostingRegressor(
    n_estimators=200,
    learning_rate=0.05,
    max_depth=5,
    min_samples_split=20,
    min_samples_leaf=10,
    random_state=44
)

print("\n开始训练最终 residual GBDT 模型...")
residual_model.fit(
    residual_X_train,
    residual_y_train
)

residual_pred_train = residual_model.predict(residual_X_train)
residual_pred_test = residual_model.predict(residual_X_test)


# =========================
# 11. 生成最终预测：baseline + residual
# =========================
def build_final_predictions(df_part, G_part, Tb_pred_part, density_ref_part, baseline_pred_df):
    final_pred_df = pd.DataFrame(index=df_part.index, columns=v_cols, dtype=float)

    for tcol, vcol in zip(temp_cols, v_cols):
        Tj = df_part[tcol].to_numpy(dtype=float)

        features_list = []
        valid_indices = []

        for i in range(len(df_part)):
            if np.isnan(Tj[i]):
                continue

            baseline_pred = baseline_pred_df.at[i, vcol]

            if pd.isna(baseline_pred) or not np.isfinite(baseline_pred):
                continue

            if (
                not np.isfinite(G_part[i]).all()
                or not np.isfinite(Tb_pred_part[i])
                or not np.isfinite(density_ref_part[i])
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
                density_ref_part[i]
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
                final_pred_df.at[idx, vcol] = (
                    baseline_pred_df.at[idx, vcol]
                    + residual_val
                )

    return final_pred_df


V_pred_final_train = build_final_predictions(
    train_df,
    G_train,
    Tb_pred_train,
    Density_Tb_pred_train,
    V_pred_baseline_train
)

V_pred_final_test = build_final_predictions(
    test_df,
    G_test,
    Tb_pred_test,
    Density_Tb_pred_test,
    V_pred_baseline_test
)


# =========================
# 12. 评估：baseline / final / residual
# =========================
print("\n=== 基线模型性能 ===")

y_train_true_base, y_train_pred_base = collect_true_pred(
    train_df,
    V_pred_baseline_train,
    v_cols
)

y_test_true_base, y_test_pred_base = collect_true_pred(
    test_df,
    V_pred_baseline_test,
    v_cols
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


print("\n=== 最终模型性能（基准 + 残差 GBDT 修正）===")

y_train_true_final, y_train_pred_final = collect_true_pred(
    train_df,
    V_pred_final_train,
    v_cols
)

y_test_true_final, y_test_pred_final = collect_true_pred(
    test_df,
    V_pred_final_test,
    v_cols
)

final_metrics_train, rel_err_final_train = eval_final_regression(
    y_train_true_final,
    y_train_pred_final,
    "Final_GBDT_model",
    "train",
    strict_less=False
)

final_metrics_test, rel_err_final_test = eval_final_regression(
    y_test_true_final,
    y_test_pred_final,
    "Final_GBDT_model",
    "test",
    strict_less=False
)


print("\n=== residual GBDT 层面性能 ===")

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
# 12.1 完整数据集统计：训练集 + 测试集
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

print("\nFinal_GBDT_model 完整数据集 Liquid Density 预测偏差 1%，5%，10%分别为：")
print(final_metrics_all["within_1pct"])
print(final_metrics_all["within_5pct"])
print(final_metrics_all["within_10pct"])


# =========================
# 13. 分温度点评估：Final 模型
# =========================
print("\n=== 分温度点评估（最终模型，训练集）===")

for tcol, vcol in zip(temp_cols, v_cols):
    actual = train_df[vcol].to_numpy(dtype=float)
    pred = V_pred_final_train[vcol].to_numpy(dtype=float)

    m = np.isfinite(actual) & np.isfinite(pred)

    if np.any(m):
        mse_temp = mean_squared_error(actual[m], pred[m])
        r2_temp = r2_score(actual[m], pred[m])

        print(f"{tcol}: MSE = {mse_temp:.6f}, R2 = {r2_temp:.6f}")


print("\n=== 分温度点评估（最终模型，测试集）===")

for tcol, vcol in zip(temp_cols, v_cols):
    actual = test_df[vcol].to_numpy(dtype=float)
    pred = V_pred_final_test[vcol].to_numpy(dtype=float)

    m = np.isfinite(actual) & np.isfinite(pred)

    if np.any(m):
        mse_temp = mean_squared_error(actual[m], pred[m])
        r2_temp = r2_score(actual[m], pred[m])

        print(f"{tcol}: MSE = {mse_temp:.6f}, R2 = {r2_temp:.6f}")


# =========================
# 14. 保存结果
# =========================
def build_long_compare(
    df_part,
    split_name,
    Tb_pred_part,
    density_ref_part,
    baseline_pred_df,
    final_pred_df
):
    rows = []

    for idx in range(len(df_part)):
        ID = df_part.at[idx, id_col]

        for j, (tcol, vcol) in enumerate(zip(temp_cols, v_cols), start=1):
            T_val = df_part.at[idx, tcol]
            V_act = df_part.at[idx, vcol]

            V_base = (
                baseline_pred_df.at[idx, vcol]
                if pd.notna(baseline_pred_df.at[idx, vcol])
                else np.nan
            )

            V_final = (
                final_pred_df.at[idx, vcol]
                if pd.notna(final_pred_df.at[idx, vcol])
                else np.nan
            )

            err_base = (
                V_base - V_act
                if pd.notna(V_base) and pd.notna(V_act)
                else np.nan
            )

            err_final = (
                V_final - V_act
                if pd.notna(V_final) and pd.notna(V_act)
                else np.nan
            )

            rel_err_base = (
                abs((V_base - V_act) / V_act) * 100
                if pd.notna(V_base) and pd.notna(V_act) and abs(V_act) > 1e-12
                else np.nan
            )

            rel_err_final = (
                abs((V_final - V_act) / V_act) * 100
                if pd.notna(V_final) and pd.notna(V_act) and abs(V_act) > 1e-12
                else np.nan
            )

            residual_correction = (
                V_final - V_base
                if pd.notna(V_final) and pd.notna(V_base)
                else np.nan
            )

            rows.append({
                "Split": split_name,
                id_col: ID,
                "temp_index": j,
                "temp_col": tcol,
                "T": T_val,
                "Density_actual": V_act,
                "Density_base": V_base,
                "Density_final": V_final,
                "error_base": err_base,
                "error_final": err_final,
                "relative_error_base_%": rel_err_base,
                "relative_error_final_%": rel_err_final,
                "residual_correction": residual_correction,
                "T_ref": Tb_pred_part[idx],
                "Density_ref": density_ref_part[idx]
            })

    return pd.DataFrame(rows)


long_train = build_long_compare(
    train_df,
    "train",
    Tb_pred_train,
    Density_Tb_pred_train,
    V_pred_baseline_train,
    V_pred_final_train
)

long_test = build_long_compare(
    test_df,
    "test",
    Tb_pred_test,
    Density_Tb_pred_test,
    V_pred_baseline_test,
    V_pred_final_test
)

long_compare = pd.concat(
    [long_train, long_test],
    ignore_index=True
).sort_values(["Split", id_col, "temp_index"])

long_all = long_compare.copy()
long_all["Split"] = "all_train_plus_test"


density_tb_out = pd.DataFrame({
    id_col: df[id_col].values,
    "Density_Tb_true": y_Tb,
    "Density_Tb_pred": Density_Tb_pred_all
})

tb_out = pd.DataFrame({
    id_col: df[id_col].values,
    "Tb_true": Tb_raw_all,
    "Tb_pred": Tb_pred_all_full
})

summary_rows = [
    density_tb_metrics_all,
    tb_metrics_all,
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


out_path = "liquid_density_actual_vs_pred_with_residual_GBDT_train_test_split.xlsx"

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

    density_tb_out.to_excel(
        writer,
        sheet_name="Density_Tb_submodel",
        index=False
    )

    tb_out.to_excel(
        writer,
        sheet_name="Tb_submodel",
        index=False
    )

print(f"\n结果已保存到: {out_path}")


# =========================
# 15. 输出最终测试集和完整数据集指标
# =========================
print("\n总模型评估（基准 + 残差 GBDT 修正，测试集）：")
print(f"R2  = {final_metrics_test['R2']:.4f}")
print(f"MSE = {final_metrics_test['MSE']:.6f}")
print(f"ARD = {final_metrics_test['ARD_%']:.2f}%")
print(f"误差 <= 1% 的数据点数量: {final_metrics_test['within_1pct']}")
print(f"误差 <= 5% 的数据点数量: {final_metrics_test['within_5pct']}")
print(f"误差 <= 10% 的数据点数量: {final_metrics_test['within_10pct']}")

print("\n总模型评估（基准 + 残差 GBDT 修正，完整数据集 train + test）：")
print(f"R2  = {final_metrics_all['R2']:.4f}")
print(f"MSE = {final_metrics_all['MSE']:.6f}")
print(f"ARD = {final_metrics_all['ARD_%']:.2f}%")
print("1%，5%，10%分别为：")
print(final_metrics_all["within_1pct"])
print(final_metrics_all["within_5pct"])
print(final_metrics_all["within_10pct"])


# =========================
# 16. 输出模型结构记录
# =========================
print("\n当前 Liquid Density baseline + GBDT residual 模型结构:")
print("Density_Tb_submodel: GradientBoostingRegressor(n_estimators=300, learning_rate=0.05, max_depth=4, min_samples_split=10, min_samples_leaf=5, random_state=42)")
print("Tb_submodel: GradientBoostingRegressor(n_estimators=300, learning_rate=0.05, max_depth=4, min_samples_split=10, min_samples_leaf=5, random_state=42), input = PolynomialFeatures(Nk, degree=2)")
print("Baseline: Density_baseline = Density_Tb_pred + A_solver((T - Tb_pred) * Nk)")
print("A_solver: GradientBoostingRegressor(n_estimators=300, learning_rate=0.05, max_depth=3, min_samples_split=10, min_samples_leaf=5, random_state=42)")
print("Residual model: GradientBoostingRegressor(n_estimators=200, learning_rate=0.05, max_depth=5, min_samples_split=20, min_samples_leaf=10, random_state=44)")
print("Residual target: Density_actual - Density_baseline")
print("Residual features: Nk + T + (T-Tb) + T/Tb + ln(T) + Density_baseline + Tb_pred + Density_Tb_pred")
print("Final prediction: Density_final = Density_baseline + residual_pred")
print("Split: material-level 8:2 split, random_state=42")
print("Final all-data statistics use strict thresholds: <1%, <5%, <10%")