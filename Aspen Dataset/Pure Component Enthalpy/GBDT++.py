# import pandas as pd
# import numpy as np
# from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
# from sklearn.linear_model import HuberRegressor
# from sklearn.preprocessing import PolynomialFeatures, StandardScaler
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split
#
# # =========================
# # 0. 参数区
# # =========================
# main_file = "Pure component enthalpy 209.xlsx"
# main_sheet = "Sheet1"
# tb_descriptor_file = "selected_25_descriptors_boiling.xlsx"
# tb_target_col = "enthalpy at boiling temperature"
#
# random_state = 42
# Tb0 = 222.543
#
# # =========================
# # 1. 数据加载
# # =========================
# df = pd.read_excel(main_file, sheet_name=main_sheet).copy()
#
# id_col = df.columns[0]
# group_cols = list(df.columns[12:31])  # 第13~31列：基团
# temp_cols = list(df.columns[31:41])   # 第32~41列：温度
# v_cols = list(df.columns[41:51])      # 第42~51列：目标变量（焓值）
#
# # =========================
# # 2. 数据预处理
# # =========================
# for col in group_cols + temp_cols + v_cols:
#     df[col] = pd.to_numeric(df[col], errors="coerce")
#
# Nk_all = df[group_cols].apply(pd.to_numeric, errors="coerce")
# Tb_raw = pd.to_numeric(df.iloc[:, 5], errors="coerce").values
#
# # 只保留至少有一个有效焓值点的物质
# valid_material_mask = df[v_cols].notna().any(axis=1)
# df = df.loc[valid_material_mask].copy().reset_index(drop=True)
# Nk_all = df[group_cols].apply(pd.to_numeric, errors="coerce")
# Tb_raw = pd.to_numeric(df.iloc[:, 5], errors="coerce").values
#
# print(f"有效物质数: {len(df)}")
#
# # =========================
# # 3. 子模型：HVap_Tb（全数据训练，不划分）
# # =========================
# df_Tb = pd.read_excel(tb_descriptor_file).copy()
#
# X_Tb = df_Tb.drop(columns=[tb_target_col], errors="ignore").copy()
# if id_col in X_Tb.columns:
#     X_Tb = X_Tb.drop(columns=[id_col], errors="ignore")
#
# X_Tb = X_Tb.apply(pd.to_numeric, errors="coerce")
# y_Tb = pd.to_numeric(df_Tb[tb_target_col], errors="coerce").values
#
# X_Tb = X_Tb.replace([np.inf, -np.inf], np.nan)
# X_Tb = X_Tb.fillna(X_Tb.median(numeric_only=True))
#
# mask_hvap_tb = np.isfinite(y_Tb)
#
# rf_Tb = RandomForestRegressor(
#     n_estimators=100,
#     random_state=random_state,
#     n_jobs=1
# )
# rf_Tb.fit(X_Tb.loc[mask_hvap_tb], y_Tb[mask_hvap_tb])
#
# HVap_Tb_all = rf_Tb.predict(X_Tb)
#
# if len(HVap_Tb_all) != len(df):
#     raise ValueError(
#         f"{tb_descriptor_file} 预测行数 = {len(HVap_Tb_all)}，与主表物质数 = {len(df)} 不一致。"
#     )
#
# # =========================
# # 4. 子模型：Tb（全数据训练，不划分）
# # =========================
# poly = PolynomialFeatures(degree=2, include_bias=False)
# Nk_poly = poly.fit_transform(Nk_all)
#
# scaler_tb = StandardScaler()
# Nk_scaled = scaler_tb.fit_transform(Nk_poly)
#
# mask_tb = np.isfinite(Tb_raw)
# model_Tb = HuberRegressor(max_iter=10000)
# model_Tb.fit(Nk_scaled[mask_tb], np.exp(Tb_raw[mask_tb] / Tb0))
# Tb_pred_all = Tb0 * np.log(np.clip(model_Tb.predict(Nk_scaled), 1e-6, None))
#
# # =========================
# # 5. 按物质 8:2 划分
# #    只用于基线模型和残差模型
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
# # 全数据预测结果切到 train / test
# G_all = Nk_all.values
# G_train = G_all[train_row_mask]
# G_test = G_all[test_row_mask]
#
# Tb_pred_train = Tb_pred_all[train_row_mask]
# Tb_pred_test = Tb_pred_all[test_row_mask]
#
# HVap_Tb_train = HVap_Tb_all[train_row_mask]
# HVap_Tb_test = HVap_Tb_all[test_row_mask]
#
# # =========================
# # 6. 基线模型 A_k：只用训练集
# # =========================
# X_rows_train = []
# y_rows_train = []
#
# for i in range(len(train_df)):
#     if not np.isfinite(Tb_pred_train[i]) or not np.isfinite(HVap_Tb_train[i]) or not np.isfinite(G_train[i]).all():
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
#         yj = Vj - HVap_Tb_train[i]
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
# # 7. 生成基准焓值预测（分别对 train / test）
# # =========================
# def build_baseline_predictions(df_part, G_part, Tb_pred_part, Hvap_ref_part):
#     pred_df = pd.DataFrame(index=df_part.index, columns=v_cols, dtype=float)
#
#     for i in range(len(df_part)):
#         if not np.isfinite(Tb_pred_part[i]) or not np.isfinite(Hvap_ref_part[i]) or not np.isfinite(G_part[i]).all():
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
#             Xj = (Tj - Tb_pred_part[i]) * G_part[i]
#             pred_df.at[i, vcol] = Hvap_ref_part[i] + Xj @ A_vec
#
#     return pred_df
#
# V_pred_baseline_train = build_baseline_predictions(train_df, G_train, Tb_pred_train, HVap_Tb_train)
# V_pred_baseline_test = build_baseline_predictions(test_df, G_test, Tb_pred_test, HVap_Tb_test)
#
# # =========================
# # 8. 残差训练集：只用训练集
# # =========================
# def build_residual_dataset(df_part, G_part, Tb_pred_part, Hvap_ref_part, baseline_pred_df):
#     residual_features = []
#     residual_targets = []
#
#     for tcol, vcol in zip(temp_cols, v_cols):
#         Tj = df_part[tcol].to_numpy(dtype=float)
#         Vj = df_part[vcol].to_numpy(dtype=float)
#         msk = (~np.isnan(Tj)) & (~np.isnan(Vj)) & (~baseline_pred_df[vcol].isna().to_numpy())
#
#         for i in np.where(msk)[0]:
#             baseline_pred = baseline_pred_df.at[i, vcol]
#             if not np.isfinite(baseline_pred):
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
#             residual_targets.append(Vj[i] - baseline_pred)
#
#     residual_features = np.array(residual_features, dtype=float)
#     residual_targets = np.array(residual_targets, dtype=float)
#     return residual_features, residual_targets
#
# residual_X_train, residual_y_train = build_residual_dataset(
#     train_df, G_train, Tb_pred_train, HVap_Tb_train, V_pred_baseline_train
# )
#
# print(f"\n残差训练集形状: {residual_X_train.shape}")
# print(f"残差目标形状: {residual_y_train.shape}")
#
# # 标准化残差特征（只在训练集 fit）
# scaler_residual = StandardScaler()
# residual_X_train_scaled = scaler_residual.fit_transform(residual_X_train)
#
# # =========================
# # 9. 残差模型：只用训练集
# # =========================
# residual_model = GradientBoostingRegressor(
#     n_estimators=200,
#     learning_rate=0.05,
#     max_depth=5,
#     min_samples_split=20,
#     min_samples_leaf=10,
#     random_state=42
# )
# residual_model.fit(residual_X_train_scaled, residual_y_train)
#
# # =========================
# # 10. 生成最终预测（基准 + 残差修正）
# # =========================
# def build_final_predictions(df_part, G_part, Tb_pred_part, Hvap_ref_part, baseline_pred_df):
#     pred_df = pd.DataFrame(index=df_part.index, columns=v_cols, dtype=float)
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
#             if not np.isfinite(baseline_pred):
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
#             features_scaled = scaler_residual.transform(features_array)
#             residual_pred = residual_model.predict(features_scaled)
#
#             for idx, residual_val in zip(valid_indices, residual_pred):
#                 pred_df.at[idx, vcol] = baseline_pred_df.at[idx, vcol] + residual_val
#
#     return pred_df
#
# V_pred_final_train = build_final_predictions(
#     train_df, G_train, Tb_pred_train, HVap_Tb_train, V_pred_baseline_train
# )
# V_pred_final_test = build_final_predictions(
#     test_df, G_test, Tb_pred_test, HVap_Tb_test, V_pred_baseline_test
# )
#
# # =========================
# # 11. 评估函数
# # =========================
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
#     relative_error[nonzero_mask] = np.abs((y_pred[nonzero_mask] - y_true[nonzero_mask]) / y_true[nonzero_mask]) * 100
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
# # =========================
# # 12. 基线 / 最终模型评估（train/test 分开）
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
#     y_train_true_final, y_train_pred_final, "Final_model", "train"
# )
# final_metrics_test, rel_err_test = eval_final_regression(
#     y_test_true_final, y_test_pred_final, "Final_model", "test"
# )
#
# # =========================
# # 13. 保存结果
# # =========================
# out_path = "enthalpy_actual_vs_pred_with_residual_correction_train_test_split.xlsx"
#
# def build_long_compare(df_part, split_name, Tb_pred_part, Hvap_ref_part, baseline_pred_df, final_pred_df):
#     rows = []
#     for idx in range(len(df_part)):
#         ID = df_part.at[idx, id_col]
#         for j, (tcol, vcol) in enumerate(zip(temp_cols, v_cols), start=1):
#             T = df_part.at[idx, tcol]
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
#                 "T": T,
#                 "Enthalpy_actual": V_act,
#                 "Enthalpy_base": V_base,
#                 "Enthalpy_final": V_final,
#                 "error_base": err_base,
#                 "error_final": err_final,
#                 "residual_correction": residual_correction,
#                 "T_ref": Tb_pred_part[idx],
#                 "Enthalpy_ref": Hvap_ref_part[idx]
#             })
#     return pd.DataFrame(rows)
#
# long_train = build_long_compare(
#     train_df, "train", Tb_pred_train, HVap_Tb_train, V_pred_baseline_train, V_pred_final_train
# )
# long_test = build_long_compare(
#     test_df, "test", Tb_pred_test, HVap_Tb_test, V_pred_baseline_test, V_pred_final_test
# )
# long_compare = pd.concat([long_train, long_test], ignore_index=True).sort_values(["Split", id_col, "temp_index"])
#
# summary_df = pd.DataFrame([
#     baseline_metrics_train, baseline_metrics_test,
#     final_metrics_train, final_metrics_test
# ])
#
# with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
#     long_compare.to_excel(writer, sheet_name="compare_long", index=False)
#     summary_df.to_excel(writer, sheet_name="summary", index=False)
#
# print(f"\n✅ 结果已保存到: {out_path}")
#
# print("\n📊 总模型评估（基准 + 残差修正，测试集）：")
# print(f"R²  = {final_metrics_test['R2']:.4f}")
# print(f"MSE = {final_metrics_test['MSE']:.6f}")
# print(f"ARD = {final_metrics_test['ARD_%']:.2f}%")
# print(f"✅ 误差 ≤ 1% 的数据点数量: {final_metrics_test['within_1pct']}")
# print(f"✅ 误差 ≤ 5% 的数据点数量: {final_metrics_test['within_5pct']}")
# print(f"✅ 误差 ≤ 10% 的数据点数量: {final_metrics_test['within_10pct']}")
# # import pandas as pd
# # import numpy as np
# # from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
# # from sklearn.linear_model import HuberRegressor
# # from sklearn.preprocessing import PolynomialFeatures, StandardScaler
# # from sklearn.metrics import mean_squared_error, r2_score
# # from sklearn.model_selection import train_test_split
# #
# # # =========================
# # # 0. 参数区
# # # =========================
# # main_file = "Pure component enthalpy 209.xlsx"
# # main_sheet = "Sheet1"
# # tb_descriptor_file = "selected_25_descriptors_boiling.xlsx"
# # tb_target_col = "enthalpy at boiling temperature"
# #
# # random_state = 42
# # Tb0 = 222.543
# #
# # # =========================
# # # 1. 数据加载
# # # =========================
# # df = pd.read_excel(main_file, sheet_name=main_sheet).copy()
# #
# # id_col = df.columns[0]
# # group_cols = list(df.columns[12:31])  # 第13~31列：基团
# # temp_cols = list(df.columns[31:41])   # 第32~41列：温度
# # v_cols = list(df.columns[41:51])      # 第42~51列：目标变量（焓值）
# #
# # # =========================
# # # 2. 数据预处理
# # # =========================
# # for col in group_cols + temp_cols + v_cols:
# #     df[col] = pd.to_numeric(df[col], errors="coerce")
# #
# # Nk_all = df[group_cols].apply(pd.to_numeric, errors="coerce")
# # Tb_raw = pd.to_numeric(df.iloc[:, 5], errors="coerce").values
# #
# # # 只保留至少有一个有效焓值点的物质
# # valid_material_mask = df[v_cols].notna().any(axis=1)
# # df = df.loc[valid_material_mask].copy().reset_index(drop=True)
# # Nk_all = df[group_cols].apply(pd.to_numeric, errors="coerce")
# # Tb_raw = pd.to_numeric(df.iloc[:, 5], errors="coerce").values
# #
# # print(f"有效物质数: {len(df)}")
# #
# # # =========================
# # # 3. 子模型评估函数
# # # =========================
# # def evaluate_scalar_regression(y_true, y_pred, model_name, split_name):
# #     y_true = np.asarray(y_true, dtype=float)
# #     y_pred = np.asarray(y_pred, dtype=float)
# #
# #     mask = np.isfinite(y_true) & np.isfinite(y_pred)
# #     y_true = y_true[mask]
# #     y_pred = y_pred[mask]
# #
# #     if len(y_true) == 0:
# #         print(f"\n{model_name} - {split_name}: 无有效样本")
# #         return {
# #             "Model": model_name,
# #             "Split": split_name,
# #             "R2": np.nan,
# #             "MSE": np.nan,
# #             "ARD_%": np.nan,
# #             "within_1pct": np.nan,
# #             "within_5pct": np.nan,
# #             "within_10pct": np.nan
# #         }, np.array([])
# #
# #     r2 = r2_score(y_true, y_pred)
# #     mse = mean_squared_error(y_true, y_pred)
# #
# #     relative_error = np.full_like(y_true, np.nan, dtype=float)
# #     nonzero_mask = np.abs(y_true) > 1e-12
# #     relative_error[nonzero_mask] = np.abs(
# #         (y_pred[nonzero_mask] - y_true[nonzero_mask]) / y_true[nonzero_mask]
# #     ) * 100
# #
# #     ard = np.nanmean(relative_error)
# #     within_1pct = np.sum(relative_error <= 1)
# #     within_5pct = np.sum(relative_error <= 5)
# #     within_10pct = np.sum(relative_error <= 10)
# #
# #     print(f"\n{model_name} - {split_name}")
# #     print(f"R²  = {r2:.6f}")
# #     print(f"MSE = {mse:.6f}")
# #     print(f"ARD = {ard:.2f}%")
# #     print(f"误差 ≤ 1% 的点数: {within_1pct}")
# #     print(f"误差 ≤ 5% 的点数: {within_5pct}")
# #     print(f"误差 ≤ 10% 的点数: {within_10pct}")
# #
# #     return {
# #         "Model": model_name,
# #         "Split": split_name,
# #         "R2": r2,
# #         "MSE": mse,
# #         "ARD_%": ard,
# #         "within_1pct": within_1pct,
# #         "within_5pct": within_5pct,
# #         "within_10pct": within_10pct
# #     }, relative_error
# #
# # # =========================
# # # 4. 子模型：HVap_Tb（全数据训练，不划分）
# # # =========================
# # df_Tb = pd.read_excel(tb_descriptor_file).copy()
# #
# # X_Tb = df_Tb.drop(columns=[tb_target_col], errors="ignore").copy()
# # if id_col in X_Tb.columns:
# #     X_Tb = X_Tb.drop(columns=[id_col], errors="ignore")
# #
# # X_Tb = X_Tb.apply(pd.to_numeric, errors="coerce")
# # y_Tb = pd.to_numeric(df_Tb[tb_target_col], errors="coerce").values
# #
# # X_Tb = X_Tb.replace([np.inf, -np.inf], np.nan)
# # X_Tb = X_Tb.fillna(X_Tb.median(numeric_only=True))
# #
# # mask_hvap_tb = np.isfinite(y_Tb)
# #
# # rf_Tb = RandomForestRegressor(
# #     n_estimators=100,
# #     random_state=random_state,
# #     n_jobs=-1
# # )
# # rf_Tb.fit(X_Tb.loc[mask_hvap_tb], y_Tb[mask_hvap_tb])
# #
# # HVap_Tb_all = rf_Tb.predict(X_Tb)
# #
# # if len(HVap_Tb_all) != len(df):
# #     raise ValueError(
# #         f"{tb_descriptor_file} 预测行数 = {len(HVap_Tb_all)}，与主表物质数 = {len(df)} 不一致。"
# #     )
# #
# # hvap_tb_metrics_all, hvap_tb_rel_err_all = evaluate_scalar_regression(
# #     y_Tb[mask_hvap_tb],
# #     HVap_Tb_all[mask_hvap_tb],
# #     "HVap_Tb_submodel",
# #     "all_data"
# # )
# #
# # hvap_tb_result = pd.DataFrame({
# #     id_col: df[id_col].values,
# #     "Enthalpy_Tb_true": y_Tb,
# #     "Enthalpy_Tb_pred": HVap_Tb_all,
# #     "Absolute_Error": np.abs(HVap_Tb_all - y_Tb),
# #     "Relative_Error (%)": np.where(
# #         np.abs(y_Tb) > 1e-12,
# #         np.abs((HVap_Tb_all - y_Tb) / y_Tb) * 100,
# #         np.nan
# #     )
# # })
# #
# # # =========================
# # # 5. 子模型：Tb（全数据训练，不划分）
# # # =========================
# # poly = PolynomialFeatures(degree=2, include_bias=False)
# # Nk_poly = poly.fit_transform(Nk_all)
# #
# # scaler_tb = StandardScaler()
# # Nk_scaled = scaler_tb.fit_transform(Nk_poly)
# #
# # mask_tb = np.isfinite(Tb_raw)
# # model_Tb = HuberRegressor(max_iter=10000)
# # model_Tb.fit(Nk_scaled[mask_tb], np.exp(Tb_raw[mask_tb] / Tb0))
# # Tb_pred_all = Tb0 * np.log(np.clip(model_Tb.predict(Nk_scaled), 1e-6, None))
# #
# # tb_metrics_all, tb_rel_err_all = evaluate_scalar_regression(
# #     Tb_raw[mask_tb],
# #     Tb_pred_all[mask_tb],
# #     "Tb_submodel",
# #     "all_data"
# # )
# #
# # tb_result = pd.DataFrame({
# #     id_col: df[id_col].values,
# #     "Tb_true": Tb_raw,
# #     "Tb_pred": Tb_pred_all,
# #     "Absolute_Error": np.abs(Tb_pred_all - Tb_raw),
# #     "Relative_Error (%)": np.where(
# #         np.abs(Tb_raw) > 1e-12,
# #         np.abs((Tb_pred_all - Tb_raw) / Tb_raw) * 100,
# #         np.nan
# #     )
# # })
# #
# # # =========================
# # # 6. 按物质 8:2 划分
# # #    只用于基线模型和残差模型
# # # =========================
# # unique_materials = df[id_col].dropna().unique()
# #
# # train_materials, test_materials = train_test_split(
# #     unique_materials,
# #     test_size=0.2,
# #     random_state=random_state
# # )
# #
# # train_row_mask = df[id_col].isin(train_materials).values
# # test_row_mask = df[id_col].isin(test_materials).values
# #
# # train_df = df.loc[train_row_mask].copy().reset_index(drop=True)
# # test_df = df.loc[test_row_mask].copy().reset_index(drop=True)
# #
# # print(f"\n训练集物质数: {len(train_df)}")
# # print(f"测试集物质数: {len(test_df)}")
# #
# # # 全数据预测结果切到 train / test
# # G_all = Nk_all.values
# # G_train = G_all[train_row_mask]
# # G_test = G_all[test_row_mask]
# #
# # Tb_pred_train = Tb_pred_all[train_row_mask]
# # Tb_pred_test = Tb_pred_all[test_row_mask]
# #
# # HVap_Tb_train = HVap_Tb_all[train_row_mask]
# # HVap_Tb_test = HVap_Tb_all[test_row_mask]
# #
# # # =========================
# # # 7. 基线模型 A_k：只用训练集
# # # =========================
# # X_rows_train = []
# # y_rows_train = []
# #
# # for i in range(len(train_df)):
# #     if not np.isfinite(Tb_pred_train[i]) or not np.isfinite(HVap_Tb_train[i]) or not np.isfinite(G_train[i]).all():
# #         continue
# #
# #     for tcol, vcol in zip(temp_cols, v_cols):
# #         Tj = train_df.at[i, tcol]
# #         Vj = train_df.at[i, vcol]
# #
# #         if np.isnan(Tj) or np.isnan(Vj):
# #             continue
# #
# #         Xj = (Tj - Tb_pred_train[i]) * G_train[i]
# #         yj = Vj - HVap_Tb_train[i]
# #
# #         X_rows_train.append(Xj)
# #         y_rows_train.append(yj)
# #
# # X_A_train = np.array(X_rows_train, dtype=float)
# # y_A_train = np.array(y_rows_train, dtype=float)
# #
# # A_solver = HuberRegressor(fit_intercept=False, max_iter=5000)
# # A_solver.fit(X_A_train, y_A_train)
# # A_vec = A_solver.coef_
# #
# # # =========================
# # # 8. 生成基准焓值预测（分别对 train / test）
# # # =========================
# # def build_baseline_predictions(df_part, G_part, Tb_pred_part, Hvap_ref_part):
# #     pred_df = pd.DataFrame(index=df_part.index, columns=v_cols, dtype=float)
# #
# #     for i in range(len(df_part)):
# #         if not np.isfinite(Tb_pred_part[i]) or not np.isfinite(Hvap_ref_part[i]) or not np.isfinite(G_part[i]).all():
# #             pred_df.loc[i, :] = np.nan
# #             continue
# #
# #         for tcol, vcol in zip(temp_cols, v_cols):
# #             Tj = df_part.at[i, tcol]
# #
# #             if np.isnan(Tj):
# #                 pred_df.at[i, vcol] = np.nan
# #                 continue
# #
# #             Xj = (Tj - Tb_pred_part[i]) * G_part[i]
# #             pred_df.at[i, vcol] = Hvap_ref_part[i] + Xj @ A_vec
# #
# #     return pred_df
# #
# # V_pred_baseline_train = build_baseline_predictions(train_df, G_train, Tb_pred_train, HVap_Tb_train)
# # V_pred_baseline_test = build_baseline_predictions(test_df, G_test, Tb_pred_test, HVap_Tb_test)
# #
# # # =========================
# # # 9. 残差训练集：只用训练集
# # # =========================
# # def build_residual_dataset(df_part, G_part, Tb_pred_part, Hvap_ref_part, baseline_pred_df):
# #     residual_features = []
# #     residual_targets = []
# #
# #     for tcol, vcol in zip(temp_cols, v_cols):
# #         Tj = df_part[tcol].to_numpy(dtype=float)
# #         Vj = df_part[vcol].to_numpy(dtype=float)
# #         msk = (~np.isnan(Tj)) & (~np.isnan(Vj)) & (~baseline_pred_df[vcol].isna().to_numpy())
# #
# #         for i in np.where(msk)[0]:
# #             baseline_pred = baseline_pred_df.at[i, vcol]
# #             if not np.isfinite(baseline_pred):
# #                 continue
# #
# #             base_features = list(G_part[i])
# #             temp_features = [
# #                 Tj[i],
# #                 Tj[i] - Tb_pred_part[i],
# #                 Tj[i] / Tb_pred_part[i] if Tb_pred_part[i] > 0 else 0.0,
# #                 np.log(Tj[i]) if Tj[i] > 0 else 0.0,
# #             ]
# #             baseline_features = [baseline_pred]
# #             ref_features = [Tb_pred_part[i], Hvap_ref_part[i]]
# #
# #             all_features = base_features + temp_features + baseline_features + ref_features
# #             residual_features.append(all_features)
# #
# #             residual_targets.append(Vj[i] - baseline_pred)
# #
# #     residual_features = np.array(residual_features, dtype=float)
# #     residual_targets = np.array(residual_targets, dtype=float)
# #     return residual_features, residual_targets
# #
# # residual_X_train, residual_y_train = build_residual_dataset(
# #     train_df, G_train, Tb_pred_train, HVap_Tb_train, V_pred_baseline_train
# # )
# #
# # print(f"\n残差训练集形状: {residual_X_train.shape}")
# # print(f"残差目标形状: {residual_y_train.shape}")
# #
# # # 标准化残差特征（只在训练集 fit）
# # scaler_residual = StandardScaler()
# # residual_X_train_scaled = scaler_residual.fit_transform(residual_X_train)
# #
# # # =========================
# # # 10. 残差模型：只用训练集
# # # =========================
# # residual_model = GradientBoostingRegressor(
# #     n_estimators=200,
# #     learning_rate=0.05,
# #     max_depth=5,
# #     min_samples_split=20,
# #     min_samples_leaf=10,
# #     random_state=42
# # )
# # residual_model.fit(residual_X_train_scaled, residual_y_train)
# #
# # # =========================
# # # 11. 生成最终预测（基准 + 残差修正）
# # # =========================
# # def build_final_predictions(df_part, G_part, Tb_pred_part, Hvap_ref_part, baseline_pred_df):
# #     pred_df = pd.DataFrame(index=df_part.index, columns=v_cols, dtype=float)
# #
# #     for tcol, vcol in zip(temp_cols, v_cols):
# #         Tj = df_part[tcol].to_numpy(dtype=float)
# #
# #         features_list = []
# #         valid_indices = []
# #
# #         for i in range(len(df_part)):
# #             if np.isnan(Tj[i]):
# #                 continue
# #
# #             baseline_pred = baseline_pred_df.at[i, vcol]
# #             if not np.isfinite(baseline_pred):
# #                 continue
# #
# #             base_features = list(G_part[i])
# #             temp_features = [
# #                 Tj[i],
# #                 Tj[i] - Tb_pred_part[i],
# #                 Tj[i] / Tb_pred_part[i] if Tb_pred_part[i] > 0 else 0.0,
# #                 np.log(Tj[i]) if Tj[i] > 0 else 0.0,
# #             ]
# #             baseline_features = [baseline_pred]
# #             ref_features = [Tb_pred_part[i], Hvap_ref_part[i]]
# #
# #             all_features = base_features + temp_features + baseline_features + ref_features
# #             features_list.append(all_features)
# #             valid_indices.append(i)
# #
# #         if len(features_list) > 0:
# #             features_array = np.array(features_list, dtype=float)
# #             features_scaled = scaler_residual.transform(features_array)
# #             residual_pred = residual_model.predict(features_scaled)
# #
# #             for idx, residual_val in zip(valid_indices, residual_pred):
# #                 pred_df.at[idx, vcol] = baseline_pred_df.at[idx, vcol] + residual_val
# #
# #     return pred_df
# #
# # V_pred_final_train = build_final_predictions(
# #     train_df, G_train, Tb_pred_train, HVap_Tb_train, V_pred_baseline_train
# # )
# # V_pred_final_test = build_final_predictions(
# #     test_df, G_test, Tb_pred_test, HVap_Tb_test, V_pred_baseline_test
# # )
# #
# # # =========================
# # # 12. 最终模型评估函数
# # # =========================
# # def collect_true_pred(df_part, pred_df, value_cols):
# #     y_true_all = []
# #     y_pred_all = []
# #
# #     for col in value_cols:
# #         actual = pd.to_numeric(df_part[col], errors="coerce").to_numpy(dtype=float)
# #         pred = pd.to_numeric(pred_df[col], errors="coerce").to_numpy(dtype=float)
# #
# #         m = np.isfinite(actual) & np.isfinite(pred)
# #         if np.any(m):
# #             y_true_all.append(actual[m])
# #             y_pred_all.append(pred[m])
# #
# #     if len(y_true_all) == 0:
# #         return np.array([]), np.array([])
# #
# #     return np.concatenate(y_true_all), np.concatenate(y_pred_all)
# #
# # def eval_final_regression(y_true, y_pred, model_name, split_name):
# #     y_true = np.asarray(y_true, dtype=float)
# #     y_pred = np.asarray(y_pred, dtype=float)
# #
# #     mask = np.isfinite(y_true) & np.isfinite(y_pred)
# #     y_true = y_true[mask]
# #     y_pred = y_pred[mask]
# #
# #     if len(y_true) == 0:
# #         print(f"\n{model_name} - {split_name}: 无有效样本")
# #         return {
# #             "Model": model_name,
# #             "Split": split_name,
# #             "R2": np.nan,
# #             "MSE": np.nan,
# #             "ARD_%": np.nan,
# #             "within_1pct": np.nan,
# #             "within_5pct": np.nan,
# #             "within_10pct": np.nan
# #         }, np.array([])
# #
# #     r2 = r2_score(y_true, y_pred)
# #     mse = mean_squared_error(y_true, y_pred)
# #
# #     relative_error = np.full_like(y_true, np.nan, dtype=float)
# #     nonzero_mask = np.abs(y_true) > 1e-12
# #     relative_error[nonzero_mask] = np.abs((y_pred[nonzero_mask] - y_true[nonzero_mask]) / y_true[nonzero_mask]) * 100
# #
# #     ard = np.nanmean(relative_error)
# #     within_1pct = np.sum(relative_error <= 1)
# #     within_5pct = np.sum(relative_error <= 5)
# #     within_10pct = np.sum(relative_error <= 10)
# #
# #     print(f"\n{model_name} - {split_name}")
# #     print(f"R²  = {r2:.6f}")
# #     print(f"MSE = {mse:.6f}")
# #     print(f"ARD = {ard:.2f}%")
# #     print(f"误差 ≤ 1% 的点数: {within_1pct}")
# #     print(f"误差 ≤ 5% 的点数: {within_5pct}")
# #     print(f"误差 ≤ 10% 的点数: {within_10pct}")
# #
# #     return {
# #         "Model": model_name,
# #         "Split": split_name,
# #         "R2": r2,
# #         "MSE": mse,
# #         "ARD_%": ard,
# #         "within_1pct": within_1pct,
# #         "within_5pct": within_5pct,
# #         "within_10pct": within_10pct
# #     }, relative_error
# #
# # # =========================
# # # 13. 基线 / 最终模型评估（train/test 分开）
# # # =========================
# # y_train_true_base, y_train_pred_base = collect_true_pred(train_df, V_pred_baseline_train, v_cols)
# # y_test_true_base, y_test_pred_base = collect_true_pred(test_df, V_pred_baseline_test, v_cols)
# #
# # baseline_metrics_train, _ = eval_final_regression(
# #     y_train_true_base, y_train_pred_base, "Baseline_model", "train"
# # )
# # baseline_metrics_test, _ = eval_final_regression(
# #     y_test_true_base, y_test_pred_base, "Baseline_model", "test"
# # )
# #
# # y_train_true_final, y_train_pred_final = collect_true_pred(train_df, V_pred_final_train, v_cols)
# # y_test_true_final, y_test_pred_final = collect_true_pred(test_df, V_pred_final_test, v_cols)
# #
# # final_metrics_train, rel_err_train = eval_final_regression(
# #     y_train_true_final, y_train_pred_final, "Final_model", "train"
# # )
# # final_metrics_test, rel_err_test = eval_final_regression(
# #     y_test_true_final, y_test_pred_final, "Final_model", "test"
# # )
# #
# # # =========================
# # # 14. 保存结果
# # # =========================
# # out_path = "enthalpy_actual_vs_pred_with_residual_correction_train_test_split.xlsx"
# #
# # def build_long_compare(df_part, split_name, Tb_pred_part, Hvap_ref_part, baseline_pred_df, final_pred_df):
# #     rows = []
# #     for idx in range(len(df_part)):
# #         ID = df_part.at[idx, id_col]
# #         for j, (tcol, vcol) in enumerate(zip(temp_cols, v_cols), start=1):
# #             T = df_part.at[idx, tcol]
# #             V_act = df_part.at[idx, vcol]
# #             V_base = baseline_pred_df.at[idx, vcol] if pd.notna(baseline_pred_df.at[idx, vcol]) else np.nan
# #             V_final = final_pred_df.at[idx, vcol] if pd.notna(final_pred_df.at[idx, vcol]) else np.nan
# #
# #             err_base = (V_base - V_act) if (pd.notna(V_base) and pd.notna(V_act)) else np.nan
# #             err_final = (V_final - V_act) if (pd.notna(V_final) and pd.notna(V_act)) else np.nan
# #             residual_correction = (V_final - V_base) if (pd.notna(V_final) and pd.notna(V_base)) else np.nan
# #
# #             rows.append({
# #                 "Split": split_name,
# #                 id_col: ID,
# #                 "temp_index": j,
# #                 "temp_col": tcol,
# #                 "T": T,
# #                 "Enthalpy_actual": V_act,
# #                 "Enthalpy_base": V_base,
# #                 "Enthalpy_final": V_final,
# #                 "error_base": err_base,
# #                 "error_final": err_final,
# #                 "residual_correction": residual_correction,
# #                 "T_ref": Tb_pred_part[idx],
# #                 "Enthalpy_ref": Hvap_ref_part[idx]
# #             })
# #     return pd.DataFrame(rows)
# #
# # long_train = build_long_compare(
# #     train_df, "train", Tb_pred_train, HVap_Tb_train, V_pred_baseline_train, V_pred_final_train
# # )
# # long_test = build_long_compare(
# #     test_df, "test", Tb_pred_test, HVap_Tb_test, V_pred_baseline_test, V_pred_final_test
# # )
# # long_compare = pd.concat([long_train, long_test], ignore_index=True).sort_values(["Split", id_col, "temp_index"])
# #
# # # 子模型预测结果表
# # hvap_tb_result = pd.DataFrame({
# #     id_col: df[id_col].values,
# #     "Enthalpy_Tb_true": y_Tb,
# #     "Enthalpy_Tb_pred": HVap_Tb_all,
# #     "Absolute_Error": np.abs(HVap_Tb_all - y_Tb),
# #     "Relative_Error (%)": np.where(
# #         np.abs(y_Tb) > 1e-12,
# #         np.abs((HVap_Tb_all - y_Tb) / y_Tb) * 100,
# #         np.nan
# #     )
# # })
# #
# # tb_result = pd.DataFrame({
# #     id_col: df[id_col].values,
# #     "Tb_true": Tb_raw,
# #     "Tb_pred": Tb_pred_all,
# #     "Absolute_Error": np.abs(Tb_pred_all - Tb_raw),
# #     "Relative_Error (%)": np.where(
# #         np.abs(Tb_raw) > 1e-12,
# #         np.abs((Tb_pred_all - Tb_raw) / Tb_raw) * 100,
# #         np.nan
# #     )
# # })
# #
# # summary_df = pd.DataFrame([
# #     hvap_tb_metrics_all,
# #     tb_metrics_all,
# #     baseline_metrics_train, baseline_metrics_test,
# #     final_metrics_train, final_metrics_test
# # ])
# #
# # with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
# #     long_compare.to_excel(writer, sheet_name="compare_long", index=False)
# #     hvap_tb_result.to_excel(writer, sheet_name="Hvap_Tb_submodel", index=False)
# #     tb_result.to_excel(writer, sheet_name="Tb_submodel", index=False)
# #     summary_df.to_excel(writer, sheet_name="summary", index=False)
# #
# # print(f"\n✅ 结果已保存到: {out_path}")
# #
# # print("\n📊 总模型评估（基准 + 残差修正，测试集）：")
# # print(f"R²  = {final_metrics_test['R2']:.4f}")
# # print(f"MSE = {final_metrics_test['MSE']:.6f}")
# # print(f"ARD = {final_metrics_test['ARD_%']:.2f}%")
# # print(f"✅ 误差 ≤ 1% 的数据点数量: {final_metrics_test['within_1pct']}")
# # print(f"✅ 误差 ≤ 5% 的数据点数量: {final_metrics_test['within_5pct']}")
# # print(f"✅ 误差 ≤ 10% 的数据点数量: {final_metrics_test['within_10pct']}")



import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import HuberRegressor
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


# =========================
# 0. 参数区
# =========================
main_file = "Pure component enthalpy 209.xlsx"
main_sheet = "Sheet1"

tb_descriptor_file = "selected_25_descriptors_boiling.xlsx"
tb_target_col = "enthalpy at boiling temperature"

random_state = 42
Tb0 = 222.543


# =========================
# 1. 数据加载
# =========================
df = pd.read_excel(main_file, sheet_name=main_sheet).copy()

id_col = df.columns[0]
group_cols = list(df.columns[12:31])  # 第13~31列：19个基团
temp_cols = list(df.columns[31:41])   # 第32~41列：10个温度
v_cols = list(df.columns[41:51])      # 第42~51列：目标变量，这里是焓值


# =========================
# 2. 数据预处理
# =========================
for col in group_cols + temp_cols + v_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

Nk_all = df[group_cols].apply(pd.to_numeric, errors="coerce")
Tb_raw = pd.to_numeric(df.iloc[:, 5], errors="coerce").values

# 只保留至少有一个有效焓值点的物质
valid_material_mask = df[v_cols].notna().any(axis=1)

df = df.loc[valid_material_mask].copy().reset_index(drop=True)
Nk_all = df[group_cols].apply(pd.to_numeric, errors="coerce")
Tb_raw = pd.to_numeric(df.iloc[:, 5], errors="coerce").values

print(f"有效物质数: {len(df)}")


# =========================
# 3. 通用评价函数
# =========================
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
            "MSE": np.nan,
            "ARD_%": np.nan,
            "within_1pct": 0,
            "within_5pct": 0,
            "within_10pct": 0
        }, np.full_like(y_true, np.nan, dtype=float)

    r2 = r2_score(y_true_valid, y_pred_valid)
    mse = mean_squared_error(y_true_valid, y_pred_valid)

    relative_error_full = np.full_like(y_true, np.nan, dtype=float)
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

    within_1pct = np.sum(relative_error_valid <= 1)
    within_5pct = np.sum(relative_error_valid <= 5)
    within_10pct = np.sum(relative_error_valid <= 10)

    print(f"\n{model_name} - {split_name}")
    print(f"R2  = {r2:.6f}")
    print(f"MSE = {mse:.10f}")
    print(f"ARD = {ard:.4f}%")
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


def eval_final_regression(y_true, y_pred, model_name, split_name, strict_less=False):
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
# 4. 子模型：Enthalpy_Tb，全数据训练
# =========================
df_Tb = pd.read_excel(tb_descriptor_file).copy()

X_Tb = df_Tb.drop(columns=[tb_target_col], errors="ignore").copy()

if id_col in X_Tb.columns:
    X_Tb = X_Tb.drop(columns=[id_col], errors="ignore")

X_Tb = X_Tb.apply(pd.to_numeric, errors="coerce")
y_Tb = pd.to_numeric(df_Tb[tb_target_col], errors="coerce").values

X_Tb = X_Tb.replace([np.inf, -np.inf], np.nan)
X_Tb = X_Tb.fillna(X_Tb.median(numeric_only=True))

mask_enthalpy_tb = np.isfinite(y_Tb)

rf_Tb = RandomForestRegressor(
    n_estimators=100,
    random_state=random_state,
    n_jobs=1
)

rf_Tb.fit(
    X_Tb.loc[mask_enthalpy_tb],
    y_Tb[mask_enthalpy_tb]
)

Enthalpy_Tb_all = rf_Tb.predict(X_Tb)

if len(Enthalpy_Tb_all) != len(df):
    raise ValueError(
        f"{tb_descriptor_file} 预测行数 = {len(Enthalpy_Tb_all)}，"
        f"与主表物质数 = {len(df)} 不一致。"
    )

enthalpy_tb_metrics_all, enthalpy_tb_rel_err_all = evaluate_scalar_regression(
    y_Tb,
    Enthalpy_Tb_all,
    "Enthalpy_Tb_submodel",
    "all_data"
)

enthalpy_tb_result = pd.DataFrame({
    id_col: df[id_col].values,
    "Enthalpy_Tb_true": y_Tb,
    "Enthalpy_Tb_pred": Enthalpy_Tb_all,
    "Absolute_Error": np.abs(Enthalpy_Tb_all - y_Tb),
    "Relative_Error (%)": enthalpy_tb_rel_err_all
})


# =========================
# 5. 子模型：Tb，全数据训练
# =========================
poly = PolynomialFeatures(
    degree=2,
    include_bias=False
)

Nk_poly = poly.fit_transform(Nk_all.fillna(0))

scaler_tb = StandardScaler()
Nk_scaled = scaler_tb.fit_transform(Nk_poly)

mask_tb = np.isfinite(Tb_raw)

model_Tb = HuberRegressor(
    max_iter=10000
)

model_Tb.fit(
    Nk_scaled[mask_tb],
    np.exp(Tb_raw[mask_tb] / Tb0)
)

Tb_pred_all = Tb0 * np.log(
    np.clip(
        model_Tb.predict(Nk_scaled),
        1e-6,
        None
    )
)

tb_metrics_all, tb_rel_err_all = evaluate_scalar_regression(
    Tb_raw,
    Tb_pred_all,
    "Tb_submodel",
    "all_data"
)

tb_result = pd.DataFrame({
    id_col: df[id_col].values,
    "Tb_true": Tb_raw,
    "Tb_pred": Tb_pred_all,
    "Absolute_Error": np.abs(Tb_pred_all - Tb_raw),
    "Relative_Error (%)": tb_rel_err_all
})


# =========================
# 6. 按物质 8:2 划分
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


# 全数据子模型预测结果切到 train / test
G_all = Nk_all.values

G_train = G_all[train_row_mask]
G_test = G_all[test_row_mask]

Tb_pred_train = Tb_pred_all[train_row_mask]
Tb_pred_test = Tb_pred_all[test_row_mask]

Enthalpy_Tb_train = Enthalpy_Tb_all[train_row_mask]
Enthalpy_Tb_test = Enthalpy_Tb_all[test_row_mask]


# =========================
# 7. 基线模型 A_k：只用训练集
# =========================
X_rows_train = []
y_rows_train = []

for i in range(len(train_df)):
    if (
        not np.isfinite(Tb_pred_train[i])
        or not np.isfinite(Enthalpy_Tb_train[i])
        or not np.isfinite(G_train[i]).all()
    ):
        continue

    for tcol, vcol in zip(temp_cols, v_cols):
        Tj = train_df.at[i, tcol]
        Hj = train_df.at[i, vcol]

        if np.isnan(Tj) or np.isnan(Hj):
            continue

        Xj = (Tj - Tb_pred_train[i]) * G_train[i]
        yj = Hj - Enthalpy_Tb_train[i]

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
# 8. 生成 baseline 焓值预测
# =========================
def build_baseline_predictions(df_part, G_part, Tb_pred_part, enthalpy_ref_part):
    pred_df = pd.DataFrame(
        index=df_part.index,
        columns=v_cols,
        dtype=float
    )

    for i in range(len(df_part)):
        if (
            not np.isfinite(Tb_pred_part[i])
            or not np.isfinite(enthalpy_ref_part[i])
            or not np.isfinite(G_part[i]).all()
        ):
            pred_df.loc[i, :] = np.nan
            continue

        for tcol, vcol in zip(temp_cols, v_cols):
            Tj = df_part.at[i, tcol]

            if np.isnan(Tj):
                pred_df.at[i, vcol] = np.nan
                continue

            Xj = (Tj - Tb_pred_part[i]) * G_part[i]
            pred_df.at[i, vcol] = enthalpy_ref_part[i] + Xj @ A_vec

    return pred_df


Enthalpy_pred_baseline_train = build_baseline_predictions(
    train_df,
    G_train,
    Tb_pred_train,
    Enthalpy_Tb_train
)

Enthalpy_pred_baseline_test = build_baseline_predictions(
    test_df,
    G_test,
    Tb_pred_test,
    Enthalpy_Tb_test
)


# =========================
# 9. 残差数据集
# =========================
def build_residual_dataset(df_part, G_part, Tb_pred_part, enthalpy_ref_part, baseline_pred_df):
    residual_features = []
    residual_targets = []

    for tcol, vcol in zip(temp_cols, v_cols):
        Tj = df_part[tcol].to_numpy(dtype=float)
        Hj = df_part[vcol].to_numpy(dtype=float)

        msk = (
            (~np.isnan(Tj))
            & (~np.isnan(Hj))
            & (~baseline_pred_df[vcol].isna().to_numpy())
        )

        for i in np.where(msk)[0]:
            baseline_pred = baseline_pred_df.at[i, vcol]

            if not np.isfinite(baseline_pred):
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
                enthalpy_ref_part[i]
            ]

            all_features = (
                base_features
                + temp_features
                + baseline_features
                + ref_features
            )

            residual_features.append(all_features)
            residual_targets.append(Hj[i] - baseline_pred)

    residual_features = np.array(residual_features, dtype=float)
    residual_targets = np.array(residual_targets, dtype=float)

    return residual_features, residual_targets


residual_X_train, residual_y_train = build_residual_dataset(
    train_df,
    G_train,
    Tb_pred_train,
    Enthalpy_Tb_train,
    Enthalpy_pred_baseline_train
)

residual_X_test, residual_y_test = build_residual_dataset(
    test_df,
    G_test,
    Tb_pred_test,
    Enthalpy_Tb_test,
    Enthalpy_pred_baseline_test
)

print(f"\n残差训练集形状: {residual_X_train.shape}")
print(f"残差测试集形状: {residual_X_test.shape}")


# 标准化残差特征，只在训练集 fit
scaler_residual = StandardScaler()
residual_X_train_scaled = scaler_residual.fit_transform(residual_X_train)
residual_X_test_scaled = scaler_residual.transform(residual_X_test)


# =========================
# 10. 残差模型：GBDT，只用训练集
# =========================
residual_model = GradientBoostingRegressor(
    n_estimators=200,
    learning_rate=0.05,
    max_depth=5,
    min_samples_split=20,
    min_samples_leaf=10,
    random_state=42
)

print("\n训练 residual GBDT 模型...")
residual_model.fit(
    residual_X_train_scaled,
    residual_y_train
)

residual_pred_train = residual_model.predict(residual_X_train_scaled)
residual_pred_test = residual_model.predict(residual_X_test_scaled)


# =========================
# 11. 生成最终预测：baseline + residual
# =========================
def build_final_predictions(df_part, G_part, Tb_pred_part, enthalpy_ref_part, baseline_pred_df):
    pred_df = pd.DataFrame(
        index=df_part.index,
        columns=v_cols,
        dtype=float
    )

    for tcol, vcol in zip(temp_cols, v_cols):
        Tj = df_part[tcol].to_numpy(dtype=float)

        features_list = []
        valid_indices = []

        for i in range(len(df_part)):
            if np.isnan(Tj[i]):
                continue

            baseline_pred = baseline_pred_df.at[i, vcol]

            if not np.isfinite(baseline_pred):
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
                enthalpy_ref_part[i]
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
            features_scaled = scaler_residual.transform(features_array)
            residual_pred = residual_model.predict(features_scaled)

            for idx, residual_val in zip(valid_indices, residual_pred):
                pred_df.at[idx, vcol] = (
                    baseline_pred_df.at[idx, vcol]
                    + residual_val
                )

    return pred_df


Enthalpy_pred_final_train = build_final_predictions(
    train_df,
    G_train,
    Tb_pred_train,
    Enthalpy_Tb_train,
    Enthalpy_pred_baseline_train
)

Enthalpy_pred_final_test = build_final_predictions(
    test_df,
    G_test,
    Tb_pred_test,
    Enthalpy_Tb_test,
    Enthalpy_pred_baseline_test
)


# =========================
# 12. 评估 baseline / final / residual
# =========================
print("\n=== Baseline 模型性能 ===")

y_train_true_base, y_train_pred_base = collect_true_pred(
    train_df,
    Enthalpy_pred_baseline_train,
    v_cols
)

y_test_true_base, y_test_pred_base = collect_true_pred(
    test_df,
    Enthalpy_pred_baseline_test,
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


print("\n=== Final 模型性能：baseline + residual GBDT ===")

y_train_true_final, y_train_pred_final = collect_true_pred(
    train_df,
    Enthalpy_pred_final_train,
    v_cols
)

y_test_true_final, y_test_pred_final = collect_true_pred(
    test_df,
    Enthalpy_pred_final_test,
    v_cols
)

final_metrics_train, rel_err_final_train = eval_final_regression(
    y_train_true_final,
    y_train_pred_final,
    "Final_GBDT_residual_model",
    "train",
    strict_less=False
)

final_metrics_test, rel_err_final_test = eval_final_regression(
    y_test_true_final,
    y_test_pred_final,
    "Final_GBDT_residual_model",
    "test",
    strict_less=False
)


print("\n=== Residual GBDT 层面性能 ===")

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
    "Final_GBDT_residual_model",
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

print("\nFinal_GBDT_residual_model 完整数据集 Enthalpy 预测偏差 1%，5%，10%分别为：")
print(final_metrics_all["within_1pct"])
print(final_metrics_all["within_5pct"])
print(final_metrics_all["within_10pct"])


# =========================
# 13. 分温度点评估：final 模型
# =========================
print("\n=== 分温度点评估：Final 模型，训练集 ===")

for tcol, vcol in zip(temp_cols, v_cols):
    actual = pd.to_numeric(train_df[vcol], errors="coerce").to_numpy(dtype=float)
    pred = pd.to_numeric(Enthalpy_pred_final_train[vcol], errors="coerce").to_numpy(dtype=float)

    m = np.isfinite(actual) & np.isfinite(pred)

    if np.any(m):
        mse_temp = mean_squared_error(actual[m], pred[m])
        r2_temp = r2_score(actual[m], pred[m])

        print(f"{tcol}: MSE = {mse_temp:.6f}, R2 = {r2_temp:.6f}")


print("\n=== 分温度点评估：Final 模型，测试集 ===")

for tcol, vcol in zip(temp_cols, v_cols):
    actual = pd.to_numeric(test_df[vcol], errors="coerce").to_numpy(dtype=float)
    pred = pd.to_numeric(Enthalpy_pred_final_test[vcol], errors="coerce").to_numpy(dtype=float)

    m = np.isfinite(actual) & np.isfinite(pred)

    if np.any(m):
        mse_temp = mean_squared_error(actual[m], pred[m])
        r2_temp = r2_score(actual[m], pred[m])

        print(f"{tcol}: MSE = {mse_temp:.6f}, R2 = {r2_temp:.6f}")


# =========================
# 14. 保存结果
# =========================
out_path = "enthalpy_actual_vs_pred_with_residual_correction_train_test_split.xlsx"


def build_long_compare(df_part, split_name, Tb_pred_part, enthalpy_ref_part, baseline_pred_df, final_pred_df):
    rows = []

    for idx in range(len(df_part)):
        ID = df_part.at[idx, id_col]

        for j, (tcol, vcol) in enumerate(zip(temp_cols, v_cols), start=1):
            T = df_part.at[idx, tcol]
            H_actual = df_part.at[idx, vcol]

            H_base = (
                baseline_pred_df.at[idx, vcol]
                if pd.notna(baseline_pred_df.at[idx, vcol])
                else np.nan
            )

            H_final = (
                final_pred_df.at[idx, vcol]
                if pd.notna(final_pred_df.at[idx, vcol])
                else np.nan
            )

            err_base = (
                H_base - H_actual
                if pd.notna(H_base) and pd.notna(H_actual)
                else np.nan
            )

            err_final = (
                H_final - H_actual
                if pd.notna(H_final) and pd.notna(H_actual)
                else np.nan
            )

            residual_correction = (
                H_final - H_base
                if pd.notna(H_final) and pd.notna(H_base)
                else np.nan
            )

            rel_err_base = (
                abs((H_base - H_actual) / H_actual) * 100
                if pd.notna(H_base) and pd.notna(H_actual) and abs(H_actual) > 1e-12
                else np.nan
            )

            rel_err_final = (
                abs((H_final - H_actual) / H_actual) * 100
                if pd.notna(H_final) and pd.notna(H_actual) and abs(H_actual) > 1e-12
                else np.nan
            )

            rows.append({
                "Split": split_name,
                id_col: ID,
                "temp_index": j,
                "temp_col": tcol,
                "T": T,
                "Enthalpy_actual": H_actual,
                "Enthalpy_baseline": H_base,
                "Enthalpy_final": H_final,
                "error_baseline": err_base,
                "error_final": err_final,
                "relative_error_baseline_%": rel_err_base,
                "relative_error_final_%": rel_err_final,
                "residual_correction": residual_correction,
                "T_ref": Tb_pred_part[idx],
                "Enthalpy_ref": enthalpy_ref_part[idx]
            })

    return pd.DataFrame(rows)


long_train = build_long_compare(
    train_df,
    "train",
    Tb_pred_train,
    Enthalpy_Tb_train,
    Enthalpy_pred_baseline_train,
    Enthalpy_pred_final_train
)

long_test = build_long_compare(
    test_df,
    "test",
    Tb_pred_test,
    Enthalpy_Tb_test,
    Enthalpy_pred_baseline_test,
    Enthalpy_pred_final_test
)

long_compare = pd.concat(
    [long_train, long_test],
    ignore_index=True
).sort_values(["Split", id_col, "temp_index"])

long_all = long_compare.copy()
long_all["Split"] = "all_train_plus_test"


# =========================
# 15. 汇总表
# =========================
summary_df = pd.DataFrame([
    enthalpy_tb_metrics_all,
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
])


# =========================
# 16. 保存 Excel
# =========================
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

    enthalpy_tb_result.to_excel(
        writer,
        sheet_name="Enthalpy_Tb_submodel",
        index=False
    )

    tb_result.to_excel(
        writer,
        sheet_name="Tb_submodel",
        index=False
    )

    summary_df.to_excel(
        writer,
        sheet_name="summary",
        index=False
    )

print(f"\n结果已保存到: {out_path}")


# =========================
# 17. 输出最终测试集和完整数据集指标
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
# 18. 输出模型结构记录
# =========================
print("\n当前 Enthalpy baseline + GBDT residual 模型结构:")
print("Enthalpy_Tb_submodel: RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=1), input = selected_25_descriptors_boiling.xlsx")
print("Tb_submodel: HuberRegressor(max_iter=10000), input = StandardScaler(PolynomialFeatures(Nk, degree=2))")
print("Baseline: Enthalpy_baseline = Enthalpy_Tb_pred + (T - Tb_pred) * sum(Ak * Nk)")
print("A_solver: HuberRegressor(fit_intercept=False, max_iter=5000)")
print("Residual model: GradientBoostingRegressor(n_estimators=200, learning_rate=0.05, max_depth=5, min_samples_split=20, min_samples_leaf=10, random_state=42)")
print("Residual target: Enthalpy_actual - Enthalpy_baseline")
print("Residual features: Nk + T + (T-Tb) + T/Tb + ln(T) + Enthalpy_baseline + Tb_pred + Enthalpy_Tb_pred")
print("Final prediction: Enthalpy_final = Enthalpy_baseline + residual_pred")
print("Final all-data statistics use strict thresholds: <1%, <5%, <10%")