# # # import numpy as np
# # # import pandas as pd
# # # from scipy.optimize import least_squares
# # # from sklearn.preprocessing import PolynomialFeatures
# # # from sklearn.linear_model import HuberRegressor
# # # from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
# # # from sklearn.metrics import mean_squared_error, r2_score
# # # from sklearn.model_selection import train_test_split
# # #
# # # # =========================
# # # # 0. 参数区
# # # # =========================
# # # vp_file = "vp209.xlsx"
# # # vp_sheet = "Sheet1"
# # # transformed_file = "Transformed_vp_Dataset.xlsx"
# # #
# # # rows_per_material = 10
# # # random_state = 42
# # # target_col_final = "Vapor Pressure"
# # # pb = 101325.0
# # # Tb0 = 222.543
# # #
# # # # =========================
# # # # 1. 读取 vp 原始数据
# # # # =========================
# # # df = pd.read_excel(vp_file, sheet_name=vp_sheet).copy()
# # #
# # # id_col = df.columns[0]
# # #
# # # # 提取基础特征
# # # MW_all = pd.to_numeric(df.iloc[:, 4], errors="coerce").values.reshape(-1, 1)
# # # Nc_all = pd.to_numeric(df.iloc[:, 10], errors="coerce").values.reshape(-1, 1)
# # # Ncs_all = pd.to_numeric(df.iloc[:, 9], errors="coerce").values.reshape(-1, 1)
# # # Nk_all = df.iloc[:, 12:31].apply(pd.to_numeric, errors="coerce").values   # 19个基团
# # # T_all = df.iloc[:, 31:41].apply(pd.to_numeric, errors="coerce").values
# # # P_vp_all = df.iloc[:, 41:51].apply(pd.to_numeric, errors="coerce").values
# # #
# # # Tb_all = pd.to_numeric(df.iloc[:, 5], errors="coerce").values
# # # Tc_half_all = pd.to_numeric(df["ASPEN Half Critical T"], errors="coerce").values
# # # Pc_bar_all = pd.to_numeric(df.iloc[:, 51], errors="coerce").values
# # # compound_ids_all = df[id_col].values
# # #
# # # # 过滤掉非法蒸汽压物质：10个点都必须有限且 > 0
# # # valid_mask = np.isfinite(P_vp_all) & (P_vp_all > 0)
# # # valid_mask = valid_mask.all(axis=1)
# # #
# # # df_valid = df.loc[valid_mask].copy().reset_index(drop=True)
# # #
# # # MW = MW_all[valid_mask]
# # # Nc = Nc_all[valid_mask]
# # # Ncs = Ncs_all[valid_mask]
# # # Nk = Nk_all[valid_mask]
# # # T = T_all[valid_mask]
# # # P_vp = P_vp_all[valid_mask]
# # #
# # # Tb = Tb_all[valid_mask]
# # # Tc_half = Tc_half_all[valid_mask]
# # # Pc_bar = Pc_bar_all[valid_mask]
# # # compound_ids = compound_ids_all[valid_mask]
# # #
# # # print("========== 数据清洗后 ==========")
# # # print(f"有效物质数: {len(df_valid)}")
# # #
# # # # =========================
# # # # 2. 按物质 8:2 划分
# # # # =========================
# # # unique_materials = df_valid[id_col].unique()
# # #
# # # train_materials, test_materials = train_test_split(
# # #     unique_materials,
# # #     test_size=0.2,
# # #     random_state=random_state
# # # )
# # #
# # # train_materials = set(train_materials)
# # # test_materials = set(test_materials)
# # #
# # # train_df = df_valid[df_valid[id_col].isin(train_materials)].copy().reset_index(drop=True)
# # # test_df = df_valid[df_valid[id_col].isin(test_materials)].copy().reset_index(drop=True)
# # #
# # # print("\n========== 按物质划分 ==========")
# # # print(f"训练集物质数: {len(train_df)}")
# # # print(f"测试集物质数: {len(test_df)}")
# # #
# # # # =========================
# # # # 3. 工具函数
# # # # =========================
# # # def evaluate_scalar_regression(y_true, y_pred, model_name, split_name):
# # #     y_true = np.asarray(y_true, dtype=float)
# # #     y_pred = np.asarray(y_pred, dtype=float)
# # #
# # #     mask = np.isfinite(y_true) & np.isfinite(y_pred)
# # #     y_true = y_true[mask]
# # #     y_pred = y_pred[mask]
# # #
# # #     if len(y_true) == 0:
# # #         print(f"\n{model_name} - {split_name}: 无有效样本")
# # #         return {
# # #             "Model": model_name,
# # #             "Split": split_name,
# # #             "R2": np.nan,
# # #             "MSE": np.nan
# # #         }
# # #
# # #     r2 = r2_score(y_true, y_pred)
# # #     mse = mean_squared_error(y_true, y_pred)
# # #
# # #     print(f"\n{model_name} - {split_name}")
# # #     print(f"R²  = {r2:.6f}")
# # #     print(f"MSE = {mse:.6f}")
# # #
# # #     return {
# # #         "Model": model_name,
# # #         "Split": split_name,
# # #         "R2": r2,
# # #         "MSE": mse
# # #     }
# # #
# # # def evaluate_final_regression(y_true, y_pred, model_name, split_name):
# # #     y_true = np.asarray(y_true, dtype=float)
# # #     y_pred = np.asarray(y_pred, dtype=float)
# # #
# # #     mask = np.isfinite(y_true) & np.isfinite(y_pred)
# # #     y_true = y_true[mask]
# # #     y_pred = y_pred[mask]
# # #
# # #     r2 = r2_score(y_true, y_pred)
# # #     mse = mean_squared_error(y_true, y_pred)
# # #
# # #     nonzero_mask = np.abs(y_true) > 1e-12
# # #     relative_error = np.full_like(y_true, np.nan, dtype=float)
# # #
# # #     if np.any(nonzero_mask):
# # #         relative_error[nonzero_mask] = np.abs((y_pred[nonzero_mask] - y_true[nonzero_mask]) / y_true[nonzero_mask]) * 100
# # #         ard = np.nanmean(relative_error)
# # #     else:
# # #         ard = np.nan
# # #
# # #     within_1pct = np.sum(relative_error <= 1)
# # #     within_5pct = np.sum(relative_error <= 5)
# # #     within_10pct = np.sum(relative_error <= 10)
# # #
# # #     print(f"\n{model_name} - {split_name}")
# # #     print(f"R²  = {r2:.6f}")
# # #     print(f"MSE = {mse:.6f}")
# # #     print(f"ARD = {ard:.2f}%")
# # #     print(f"误差 ≤ 1% 的点数: {within_1pct}")
# # #     print(f"误差 ≤ 5% 的点数: {within_5pct}")
# # #     print(f"误差 ≤ 10% 的点数: {within_10pct}")
# # #
# # #     return {
# # #         "Model": model_name,
# # #         "Split": split_name,
# # #         "R2": r2,
# # #         "MSE": mse,
# # #         "ARD_%": ard,
# # #         "within_1pct": within_1pct,
# # #         "within_5pct": within_5pct,
# # #         "within_10pct": within_10pct,
# # #         "relative_error_%": relative_error
# # #     }
# # #
# # # def get_arrays(df_part):
# # #     arrays = {
# # #         "ids": df_part[id_col].values,
# # #         "MW": pd.to_numeric(df_part.iloc[:, 4], errors="coerce").values.reshape(-1, 1),
# # #         "Nc": pd.to_numeric(df_part.iloc[:, 10], errors="coerce").values.reshape(-1, 1),
# # #         "Ncs": pd.to_numeric(df_part.iloc[:, 9], errors="coerce").values.reshape(-1, 1),
# # #         "Nk": df_part.iloc[:, 12:31].apply(pd.to_numeric, errors="coerce").values,
# # #         "T": df_part.iloc[:, 31:41].apply(pd.to_numeric, errors="coerce").values,
# # #         "P_vp": df_part.iloc[:, 41:51].apply(pd.to_numeric, errors="coerce").values,
# # #         "Tb": pd.to_numeric(df_part.iloc[:, 5], errors="coerce").values,
# # #         "Tc_half": pd.to_numeric(df_part["ASPEN Half Critical T"], errors="coerce").values,
# # #         "Pc_bar": pd.to_numeric(df_part.iloc[:, 51], errors="coerce").values,
# # #     }
# # #     return arrays
# # #
# # # train_arr = get_arrays(train_df)
# # # test_arr = get_arrays(test_df)
# # #
# # # # =========================
# # # # 4. 构造 poly 特征（只在训练集 fit）
# # # # =========================
# # # poly = PolynomialFeatures(degree=2, include_bias=False)
# # # Nk_poly_train = poly.fit_transform(train_arr["Nk"])
# # # Nk_poly_test = poly.transform(test_arr["Nk"])
# # #
# # # # =========================
# # # # 5. Tb 子模型（保持你的原逻辑）
# # # # =========================
# # # tb_train_mask = np.isfinite(train_arr["Tb"]) & np.isfinite(Nk_poly_train).all(axis=1)
# # # tb_test_mask = np.isfinite(test_arr["Tb"]) & np.isfinite(Nk_poly_test).all(axis=1)
# # #
# # # model_tb = HuberRegressor(max_iter=10000)
# # # model_tb.fit(Nk_poly_train[tb_train_mask], np.exp(train_arr["Tb"][tb_train_mask] / Tb0))
# # #
# # # Tb_pred_train = Tb0 * np.log(np.clip(model_tb.predict(Nk_poly_train), 1e-6, None))
# # # Tb_pred_test = Tb0 * np.log(np.clip(model_tb.predict(Nk_poly_test), 1e-6, None))
# # #
# # # tb_metrics_train = evaluate_scalar_regression(train_arr["Tb"][tb_train_mask], Tb_pred_train[tb_train_mask], "Tb_submodel", "train")
# # # tb_metrics_test = evaluate_scalar_regression(test_arr["Tb"][tb_test_mask], Tb_pred_test[tb_test_mask], "Tb_submodel", "test")
# # #
# # # # =========================
# # # # 6. Tc_half 子模型（保持你的原逻辑）
# # # # =========================
# # # tc_train_mask = np.isfinite(train_arr["Tc_half"]) & np.isfinite(Nk_poly_train).all(axis=1)
# # # tc_test_mask = np.isfinite(test_arr["Tc_half"]) & np.isfinite(Nk_poly_test).all(axis=1)
# # #
# # # gb_model_tc = GradientBoostingRegressor(
# # #     n_estimators=300,
# # #     learning_rate=0.05,
# # #     max_depth=4,
# # #     random_state=0
# # # )
# # # gb_model_tc.fit(Nk_poly_train[tc_train_mask], train_arr["Tc_half"][tc_train_mask])
# # #
# # # Tc_half_pred_train = gb_model_tc.predict(Nk_poly_train)
# # # Tc_half_pred_test = gb_model_tc.predict(Nk_poly_test)
# # #
# # # tc_metrics_train = evaluate_scalar_regression(train_arr["Tc_half"][tc_train_mask], Tc_half_pred_train[tc_train_mask], "Tc_half_submodel", "train")
# # # tc_metrics_test = evaluate_scalar_regression(test_arr["Tc_half"][tc_test_mask], Tc_half_pred_test[tc_test_mask], "Tc_half_submodel", "test")
# # #
# # # # 用于 slope 的完整临界温度近似
# # # Tc_pred_full_train = Tc_half_pred_train * 2.0
# # # Tc_pred_full_test = Tc_half_pred_test * 2.0
# # # # =========================
# # # # 7. Pc 子模型（不使用 poly，只用原始 19 个基团）
# # # # =========================
# # # MW_train_flat = train_arr["MW"].flatten()
# # # MW_test_flat = test_arr["MW"].flatten()
# # #
# # # Pc_bar_train = train_arr["Pc_bar"]
# # # Pc_bar_test = test_arr["Pc_bar"]
# # #
# # # # 这里改成用原始 Nk，不用 Nk_poly
# # # def residual_pc(params, X, MW, Pc_true):
# # #     beta = params[:-1]   # 19个基团系数
# # #     beta3 = params[-1]
# # #
# # #     y_pred = X @ beta
# # #     x_pred = y_pred + 0.108998
# # #
# # #     # 防止接近0导致 (1/x)^2 爆炸
# # #     x_pred = np.where(
# # #         np.abs(x_pred) < 1e-8,
# # #         np.sign(x_pred) * 1e-8 + (x_pred == 0) * 1e-8,
# # #         x_pred
# # #     )
# # #
# # #     Pc_pred = 5.9827 + (1.0 / x_pred) ** 2 + beta3 * np.exp(1.0 / np.clip(MW, 1e-8, None))
# # #     return Pc_pred - Pc_true
# # #
# # # pc_train_mask = (
# # #     np.isfinite(Pc_bar_train)
# # #     & np.isfinite(MW_train_flat)
# # #     & np.isfinite(train_arr["Nk"]).all(axis=1)
# # # )
# # #
# # # pc_test_mask = (
# # #     np.isfinite(Pc_bar_test)
# # #     & np.isfinite(MW_test_flat)
# # #     & np.isfinite(test_arr["Nk"]).all(axis=1)
# # # )
# # #
# # # # 参数个数 = 19个基团 + 1个 beta3
# # # params_init_pc = np.zeros(train_arr["Nk"].shape[1] + 1)
# # #
# # # result_pc = least_squares(
# # #     residual_pc,
# # #     x0=params_init_pc,
# # #     args=(
# # #         train_arr["Nk"][pc_train_mask],
# # #         MW_train_flat[pc_train_mask],
# # #         Pc_bar_train[pc_train_mask]
# # #     ),
# # #     max_nfev=5000
# # # )
# # #
# # # def predict_pc_pa(Nk_raw, MW, result_pc):
# # #     x_fit = Nk_raw @ result_pc.x[:-1] + 0.108998
# # #
# # #     x_fit = np.where(
# # #         np.abs(x_fit) < 1e-8,
# # #         np.sign(x_fit) * 1e-8 + (x_fit == 0) * 1e-8,
# # #         x_fit
# # #     )
# # #
# # #     Pc_pred_bar = 5.9827 + (1.0 / x_fit) ** 2 + result_pc.x[-1] * np.exp(1.0 / np.clip(MW, 1e-8, None))
# # #     return Pc_pred_bar * 1e5   # 转成 Pa
# # #
# # # Pc_pred_train = predict_pc_pa(train_arr["Nk"], MW_train_flat, result_pc)
# # # Pc_pred_test = predict_pc_pa(test_arr["Nk"], MW_test_flat, result_pc)
# # #
# # # pc_metrics_train = evaluate_scalar_regression(
# # #     Pc_bar_train[pc_train_mask] * 1e5,
# # #     Pc_pred_train[pc_train_mask],
# # #     "Pc_submodel",
# # #     "train"
# # # )
# # #
# # # pc_metrics_test = evaluate_scalar_regression(
# # #     Pc_bar_test[pc_test_mask] * 1e5,
# # #     Pc_pred_test[pc_test_mask],
# # #     "Pc_submodel",
# # #     "test"
# # # )
# # # # =========================
# # # # 8. 计算 slope（分别对训练集/测试集预测）
# # # # =========================
# # # def build_slope(Tb_pred, Tc_pred_full, Pc_pred_pa):
# # #     denom = Tc_pred_full - Tb_pred
# # #     slope = np.full_like(Tb_pred, np.nan, dtype=float)
# # #
# # #     valid = (
# # #         np.isfinite(Tb_pred)
# # #         & np.isfinite(Tc_pred_full)
# # #         & np.isfinite(Pc_pred_pa)
# # #         & (Pc_pred_pa > 0)
# # #         & (np.abs(denom) > 1e-12)
# # #     )
# # #     slope[valid] = (np.log(Pc_pred_pa[valid]) - np.log(pb)) / denom[valid]
# # #     return slope.reshape(-1, 1)
# # #
# # # slope_train = build_slope(Tb_pred_train, Tc_pred_full_train, Pc_pred_train)
# # # slope_test = build_slope(Tb_pred_test, Tc_pred_full_test, Pc_pred_test)
# # #
# # # slope_df = pd.DataFrame({
# # #     "Material_ID": np.concatenate([train_arr["ids"], test_arr["ids"]]),
# # #     "Split": ["train"] * len(train_arr["ids"]) + ["test"] * len(test_arr["ids"]),
# # #     "slope": np.concatenate([slope_train.flatten(), slope_test.flatten()])
# # # })
# # # slope_df.to_csv("vp_slope_values_train_test.csv", index=False)
# # # print("\n✅ slope 值已保存为: vp_slope_values_train_test.csv")
# # #
# # # # =========================
# # # # 9. 读取 transformed 数据，并映射 Material_ID
# # # # =========================
# # # trans_df = pd.read_excel(transformed_file).reset_index(drop=True).copy()
# # #
# # # if len(trans_df) % rows_per_material != 0:
# # #     raise ValueError(
# # #         f"{transformed_file} 的总行数 {len(trans_df)} 不是 {rows_per_material} 的整数倍，无法按每个物质 10 行映射。"
# # #     )
# # #
# # # n_materials_trans = len(trans_df) // rows_per_material
# # # n_materials_vp = len(df_valid)
# # #
# # # if n_materials_trans != n_materials_vp:
# # #     raise ValueError(
# # #         f"{transformed_file} 推断的物质数 = {n_materials_trans}，而 vp 有效物质数 = {n_materials_vp}，二者不一致。"
# # #     )
# # #
# # # ordered_material_ids = df_valid[id_col].values
# # # trans_df["Material_ID"] = np.repeat(ordered_material_ids, rows_per_material)
# # #
# # # # 合并 slope 和 split
# # # trans_with_slope = trans_df.merge(
# # #     slope_df[["Material_ID", "Split", "slope"]],
# # #     on="Material_ID",
# # #     how="left"
# # # )
# # #
# # # trans_with_slope.to_excel("Transformed_vp_with_slope_and_split.xlsx", index=False)
# # # print("✅ 已保存为: Transformed_vp_with_slope_and_split.xlsx")
# # #
# # # # =========================
# # # # 10. 最终随机森林模型（只用训练集）
# # # # =========================
# # # final_train_df = trans_with_slope[trans_with_slope["Split"] == "train"].copy()
# # # final_test_df = trans_with_slope[trans_with_slope["Split"] == "test"].copy()
# # #
# # # final_train_df[target_col_final] = pd.to_numeric(final_train_df[target_col_final], errors="coerce")
# # # final_test_df[target_col_final] = pd.to_numeric(final_test_df[target_col_final], errors="coerce")
# # #
# # # # 去掉目标缺失行
# # # final_train_df = final_train_df.dropna(subset=[target_col_final]).copy()
# # # final_test_df = final_test_df.dropna(subset=[target_col_final]).copy()
# # #
# # # drop_cols = [target_col_final, "Material_ID", "Split"]
# # # feature_cols = [c for c in final_train_df.columns if c not in drop_cols]
# # #
# # # X_train_final = final_train_df[feature_cols].copy()
# # # X_test_final = final_test_df[feature_cols].copy()
# # #
# # # # 只保留数值列
# # # numeric_cols = X_train_final.select_dtypes(include=[np.number]).columns.tolist()
# # # X_train_final = X_train_final[numeric_cols].copy()
# # # X_test_final = X_test_final[numeric_cols].copy()
# # #
# # # y_train_final = final_train_df[target_col_final].astype(float).values
# # # y_test_final = final_test_df[target_col_final].astype(float).values
# # #
# # # model_final = RandomForestRegressor(
# # #     n_estimators=300,
# # #     random_state=42,
# # #     n_jobs=-1
# # # )
# # # model_final.fit(X_train_final, y_train_final)
# # #
# # # y_train_pred = model_final.predict(X_train_final)
# # # y_test_pred = model_final.predict(X_test_final)
# # #
# # # final_metrics_train = evaluate_final_regression(y_train_final, y_train_pred, "Final_RF_model", "train")
# # # final_metrics_test = evaluate_final_regression(y_test_final, y_test_pred, "Final_RF_model", "test")
# # #
# # # # =========================
# # # # 11. 保存最终预测结果
# # # # =========================
# # # train_result = final_train_df.copy()
# # # train_result["Predicted_Vapor_Pressure"] = y_train_pred
# # # train_result["Absolute_Error"] = np.abs(y_train_final - y_train_pred)
# # # train_result["Relative_Error (%)"] = final_metrics_train["relative_error_%"]
# # #
# # # test_result = final_test_df.copy()
# # # test_result["Predicted_Vapor_Pressure"] = y_test_pred
# # # test_result["Absolute_Error"] = np.abs(y_test_final - y_test_pred)
# # # test_result["Relative_Error (%)"] = final_metrics_test["relative_error_%"]
# # #
# # # train_result.to_excel("train_prediction_vs_actual_vp_with_slope.xlsx", index=False)
# # # test_result.to_excel("test_prediction_vs_actual_vp_with_slope.xlsx", index=False)
# # #
# # # print("\n✅ 已保存训练集预测结果: train_prediction_vs_actual_vp_with_slope.xlsx")
# # # print("✅ 已保存测试集预测结果: test_prediction_vs_actual_vp_with_slope.xlsx")
# # #
# # # # =========================
# # # # 12. 子模型输出表
# # # # =========================
# # # tb_out_train = pd.DataFrame({
# # #     "Split": "train",
# # #     "Material_ID": train_arr["ids"],
# # #     "Tb_true": train_arr["Tb"],
# # #     "Tb_pred": Tb_pred_train
# # # })
# # # tb_out_test = pd.DataFrame({
# # #     "Split": "test",
# # #     "Material_ID": test_arr["ids"],
# # #     "Tb_true": test_arr["Tb"],
# # #     "Tb_pred": Tb_pred_test
# # # })
# # #
# # # tc_out_train = pd.DataFrame({
# # #     "Split": "train",
# # #     "Material_ID": train_arr["ids"],
# # #     "Tc_half_true": train_arr["Tc_half"],
# # #     "Tc_half_pred": Tc_half_pred_train,
# # #     "Tc_full_pred_approx": Tc_pred_full_train
# # # })
# # # tc_out_test = pd.DataFrame({
# # #     "Split": "test",
# # #     "Material_ID": test_arr["ids"],
# # #     "Tc_half_true": test_arr["Tc_half"],
# # #     "Tc_half_pred": Tc_half_pred_test,
# # #     "Tc_full_pred_approx": Tc_pred_full_test
# # # })
# # #
# # # pc_out_train = pd.DataFrame({
# # #     "Split": "train",
# # #     "Material_ID": train_arr["ids"],
# # #     "Pc_true_Pa": train_arr["Pc_bar"] * 1e5,
# # #     "Pc_pred_Pa": Pc_pred_train
# # # })
# # # pc_out_test = pd.DataFrame({
# # #     "Split": "test",
# # #     "Material_ID": test_arr["ids"],
# # #     "Pc_true_Pa": test_arr["Pc_bar"] * 1e5,
# # #     "Pc_pred_Pa": Pc_pred_test
# # # })
# # #
# # # # =========================
# # # # 13. 汇总表
# # # # =========================
# # # summary_rows = [
# # #     tb_metrics_train, tb_metrics_test,
# # #     tc_metrics_train, tc_metrics_test,
# # #     pc_metrics_train, pc_metrics_test,
# # #     final_metrics_train, final_metrics_test
# # # ]
# # # summary_df = pd.DataFrame(summary_rows)
# # #
# # # # =========================
# # # # 14. 总保存
# # # # =========================
# # # output_filename = "VP_pipeline_with_slope_train_test_split.xlsx"
# # # with pd.ExcelWriter(output_filename, engine="xlsxwriter") as writer:
# # #     summary_df.to_excel(writer, sheet_name="summary", index=False)
# # #     slope_df.to_excel(writer, sheet_name="slope_pred", index=False)
# # #     pd.concat([tb_out_train, tb_out_test], ignore_index=True).to_excel(writer, sheet_name="Tb_submodel", index=False)
# # #     pd.concat([tc_out_train, tc_out_test], ignore_index=True).to_excel(writer, sheet_name="Tc_half_submodel", index=False)
# # #     pd.concat([pc_out_train, pc_out_test], ignore_index=True).to_excel(writer, sheet_name="Pc_submodel", index=False)
# # #     pd.concat([train_result, test_result], ignore_index=True).to_excel(writer, sheet_name="final_predictions", index=False)
# # #     trans_with_slope.to_excel(writer, sheet_name="transformed_with_slope", index=False)
# # #
# # # print(f"\n✅ 全部结果已保存至: {output_filename}")
# #
# # import numpy as np
# # import pandas as pd
# #
# # from scipy.optimize import least_squares
# # from sklearn.preprocessing import PolynomialFeatures
# # from sklearn.linear_model import HuberRegressor
# # from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
# # from sklearn.metrics import mean_squared_error, r2_score
# # from sklearn.model_selection import train_test_split
# #
# #
# # # =========================
# # # 0. 参数区
# # # =========================
# # vp_file = "vp209.xlsx"
# # vp_sheet = "Sheet1"
# # transformed_file = "Transformed_vp_Dataset.xlsx"
# #
# # rows_per_material = 10
# # random_state = 42
# # target_col_final = "Vapor Pressure"
# #
# # pb = 101325.0
# # Tb0 = 222.543
# #
# #
# # # =========================
# # # 1. 读取 vp 原始数据
# # # =========================
# # df = pd.read_excel(vp_file, sheet_name=vp_sheet).copy()
# #
# # id_col = df.columns[0]
# #
# # # 提取基础特征
# # MW_all = pd.to_numeric(df.iloc[:, 4], errors="coerce").values.reshape(-1, 1)
# # Nc_all = pd.to_numeric(df.iloc[:, 10], errors="coerce").values.reshape(-1, 1)
# # Ncs_all = pd.to_numeric(df.iloc[:, 9], errors="coerce").values.reshape(-1, 1)
# #
# # Nk_all = df.iloc[:, 12:31].apply(pd.to_numeric, errors="coerce").values   # 19个基团
# # T_all = df.iloc[:, 31:41].apply(pd.to_numeric, errors="coerce").values
# # P_vp_all = df.iloc[:, 41:51].apply(pd.to_numeric, errors="coerce").values
# #
# # Tb_all = pd.to_numeric(df.iloc[:, 5], errors="coerce").values
# # Tc_half_all = pd.to_numeric(df["ASPEN Half Critical T"], errors="coerce").values
# # Pc_bar_all = pd.to_numeric(df.iloc[:, 51], errors="coerce").values
# # compound_ids_all = df[id_col].values
# #
# # # 过滤掉非法蒸汽压物质：10个点都必须有限且 > 0
# # valid_mask = np.isfinite(P_vp_all) & (P_vp_all > 0)
# # valid_mask = valid_mask.all(axis=1)
# #
# # df_valid = df.loc[valid_mask].copy().reset_index(drop=True)
# #
# # print("========== 数据清洗后 ==========")
# # print(f"有效物质数: {len(df_valid)}")
# #
# #
# # # =========================
# # # 2. 工具函数
# # # =========================
# # def evaluate_scalar_regression(y_true, y_pred, model_name, split_name):
# #     y_true = np.asarray(y_true, dtype=float)
# #     y_pred = np.asarray(y_pred, dtype=float)
# #
# #     mask = np.isfinite(y_true) & np.isfinite(y_pred)
# #     y_true_valid = y_true[mask]
# #     y_pred_valid = y_pred[mask]
# #
# #     if len(y_true_valid) == 0:
# #         print(f"\n{model_name} - {split_name}: 无有效样本")
# #         return {
# #             "Model": model_name,
# #             "Split": split_name,
# #             "R2": np.nan,
# #             "MSE": np.nan
# #         }
# #
# #     r2 = r2_score(y_true_valid, y_pred_valid)
# #     mse = mean_squared_error(y_true_valid, y_pred_valid)
# #
# #     print(f"\n{model_name} - {split_name}")
# #     print(f"R²  = {r2:.6f}")
# #     print(f"MSE = {mse:.6f}")
# #
# #     return {
# #         "Model": model_name,
# #         "Split": split_name,
# #         "R2": r2,
# #         "MSE": mse
# #     }
# #
# #
# # def evaluate_final_regression(y_true, y_pred, model_name, split_name):
# #     y_true = np.asarray(y_true, dtype=float)
# #     y_pred = np.asarray(y_pred, dtype=float)
# #
# #     mask = np.isfinite(y_true) & np.isfinite(y_pred)
# #     y_true_valid = y_true[mask]
# #     y_pred_valid = y_pred[mask]
# #
# #     r2 = r2_score(y_true_valid, y_pred_valid)
# #     mse = mean_squared_error(y_true_valid, y_pred_valid)
# #
# #     nonzero_mask = np.abs(y_true_valid) > 1e-12
# #     relative_error = np.full_like(y_true_valid, np.nan, dtype=float)
# #
# #     if np.any(nonzero_mask):
# #         relative_error[nonzero_mask] = np.abs(
# #             (y_pred_valid[nonzero_mask] - y_true_valid[nonzero_mask])
# #             / y_true_valid[nonzero_mask]
# #         ) * 100
# #         ard = np.nanmean(relative_error)
# #     else:
# #         ard = np.nan
# #
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
# #         "within_10pct": within_10pct,
# #         "relative_error_%": relative_error
# #     }
# #
# #
# # def get_arrays(df_part):
# #     arrays = {
# #         "ids": df_part[id_col].values,
# #         "MW": pd.to_numeric(df_part.iloc[:, 4], errors="coerce").values.reshape(-1, 1),
# #         "Nc": pd.to_numeric(df_part.iloc[:, 10], errors="coerce").values.reshape(-1, 1),
# #         "Ncs": pd.to_numeric(df_part.iloc[:, 9], errors="coerce").values.reshape(-1, 1),
# #         "Nk": df_part.iloc[:, 12:31].apply(pd.to_numeric, errors="coerce").values,
# #         "T": df_part.iloc[:, 31:41].apply(pd.to_numeric, errors="coerce").values,
# #         "P_vp": df_part.iloc[:, 41:51].apply(pd.to_numeric, errors="coerce").values,
# #         "Tb": pd.to_numeric(df_part.iloc[:, 5], errors="coerce").values,
# #         "Tc_half": pd.to_numeric(df_part["ASPEN Half Critical T"], errors="coerce").values,
# #         "Pc_bar": pd.to_numeric(df_part.iloc[:, 51], errors="coerce").values,
# #     }
# #     return arrays
# #
# #
# # # 全体有效物质数组
# # all_arr = get_arrays(df_valid)
# #
# #
# # # =========================
# # # 3. 构造 poly 特征
# # #    注意：子模型不划分训练/测试，因此 poly 在全体有效物质上 fit
# # # =========================
# # poly = PolynomialFeatures(degree=2, include_bias=False)
# # Nk_poly_all = poly.fit_transform(all_arr["Nk"])
# #
# #
# # # =========================
# # # 4. Tb 子模型
# # #    子模型不划分训练集/测试集，使用全体有效物质训练
# # # =========================
# # tb_all_mask = (
# #     np.isfinite(all_arr["Tb"])
# #     & np.isfinite(Nk_poly_all).all(axis=1)
# # )
# #
# # model_tb = HuberRegressor(max_iter=10000)
# #
# # model_tb.fit(
# #     Nk_poly_all[tb_all_mask],
# #     np.exp(all_arr["Tb"][tb_all_mask] / Tb0)
# # )
# #
# # Tb_pred_all = Tb0 * np.log(
# #     np.clip(model_tb.predict(Nk_poly_all), 1e-6, None)
# # )
# #
# # tb_metrics_all = evaluate_scalar_regression(
# #     all_arr["Tb"][tb_all_mask],
# #     Tb_pred_all[tb_all_mask],
# #     "Tb_submodel",
# #     "all_data"
# # )
# #
# #
# # # =========================
# # # 5. Tc_half 子模型
# # #    子模型不划分训练集/测试集，使用全体有效物质训练
# # # =========================
# # tc_all_mask = (
# #     np.isfinite(all_arr["Tc_half"])
# #     & np.isfinite(Nk_poly_all).all(axis=1)
# # )
# #
# # gb_model_tc = GradientBoostingRegressor(
# #     n_estimators=300,
# #     learning_rate=0.05,
# #     max_depth=4,
# #     random_state=0
# # )
# #
# # gb_model_tc.fit(
# #     Nk_poly_all[tc_all_mask],
# #     all_arr["Tc_half"][tc_all_mask]
# # )
# #
# # Tc_half_pred_all = gb_model_tc.predict(Nk_poly_all)
# #
# # tc_metrics_all = evaluate_scalar_regression(
# #     all_arr["Tc_half"][tc_all_mask],
# #     Tc_half_pred_all[tc_all_mask],
# #     "Tc_half_submodel",
# #     "all_data"
# # )
# #
# # # 用于 slope 的完整临界温度近似
# # Tc_pred_full_all = Tc_half_pred_all * 2.0
# #
# #
# # # =========================
# # # 6. Pc 子模型
# # #    子模型不划分训练集/测试集，使用全体有效物质训练
# # #    注意：Pc 子模型仍然保持原逻辑，不使用 poly，只用原始 19 个基团
# # # =========================
# # MW_all_flat = all_arr["MW"].flatten()
# # Pc_bar_all_valid = all_arr["Pc_bar"]
# #
# #
# # def residual_pc(params, X, MW, Pc_true):
# #     beta = params[:-1]   # 19个基团系数
# #     beta3 = params[-1]
# #
# #     y_pred = X @ beta
# #     x_pred = y_pred + 0.108998
# #
# #     # 防止接近0导致 (1/x)^2 爆炸
# #     x_pred = np.where(
# #         np.abs(x_pred) < 1e-8,
# #         np.sign(x_pred) * 1e-8 + (x_pred == 0) * 1e-8,
# #         x_pred
# #     )
# #
# #     Pc_pred = (
# #         5.9827
# #         + (1.0 / x_pred) ** 2
# #         + beta3 * np.exp(1.0 / np.clip(MW, 1e-8, None))
# #     )
# #
# #     return Pc_pred - Pc_true
# #
# #
# # pc_all_mask = (
# #     np.isfinite(Pc_bar_all_valid)
# #     & np.isfinite(MW_all_flat)
# #     & np.isfinite(all_arr["Nk"]).all(axis=1)
# # )
# #
# # # 参数个数 = 19个基团 + 1个 beta3
# # params_init_pc = np.zeros(all_arr["Nk"].shape[1] + 1)
# #
# # result_pc = least_squares(
# #     residual_pc,
# #     x0=params_init_pc,
# #     args=(
# #         all_arr["Nk"][pc_all_mask],
# #         MW_all_flat[pc_all_mask],
# #         Pc_bar_all_valid[pc_all_mask]
# #     ),
# #     max_nfev=5000
# # )
# #
# #
# # def predict_pc_pa(Nk_raw, MW, result_pc):
# #     x_fit = Nk_raw @ result_pc.x[:-1] + 0.108998
# #
# #     x_fit = np.where(
# #         np.abs(x_fit) < 1e-8,
# #         np.sign(x_fit) * 1e-8 + (x_fit == 0) * 1e-8,
# #         x_fit
# #     )
# #
# #     Pc_pred_bar = (
# #         5.9827
# #         + (1.0 / x_fit) ** 2
# #         + result_pc.x[-1] * np.exp(1.0 / np.clip(MW, 1e-8, None))
# #     )
# #
# #     return Pc_pred_bar * 1e5   # bar 转 Pa
# #
# #
# # Pc_pred_all = predict_pc_pa(
# #     all_arr["Nk"],
# #     MW_all_flat,
# #     result_pc
# # )
# #
# # pc_metrics_all = evaluate_scalar_regression(
# #     Pc_bar_all_valid[pc_all_mask] * 1e5,
# #     Pc_pred_all[pc_all_mask],
# #     "Pc_submodel",
# #     "all_data"
# # )
# #
# #
# # # =========================
# # # 7. 计算 slope
# # #    基于全数据训练出来的 Tb / Tc / Pc 子模型预测值
# # # =========================
# # def build_slope(Tb_pred, Tc_pred_full, Pc_pred_pa):
# #     denom = Tc_pred_full - Tb_pred
# #     slope = np.full_like(Tb_pred, np.nan, dtype=float)
# #
# #     valid = (
# #         np.isfinite(Tb_pred)
# #         & np.isfinite(Tc_pred_full)
# #         & np.isfinite(Pc_pred_pa)
# #         & (Pc_pred_pa > 0)
# #         & (np.abs(denom) > 1e-12)
# #     )
# #
# #     slope[valid] = (
# #         np.log(Pc_pred_pa[valid]) - np.log(pb)
# #     ) / denom[valid]
# #
# #     return slope.reshape(-1, 1)
# #
# #
# # slope_all = build_slope(
# #     Tb_pred_all,
# #     Tc_pred_full_all,
# #     Pc_pred_all
# # )
# #
# #
# # # =========================
# # # 8. 最终模型按物质 8:2 划分
# # #    注意：只有最终模型划分训练集/测试集
# # # =========================
# # unique_materials = df_valid[id_col].unique()
# #
# # train_materials, test_materials = train_test_split(
# #     unique_materials,
# #     test_size=0.2,
# #     random_state=random_state
# # )
# #
# # train_materials = set(train_materials)
# # test_materials = set(test_materials)
# #
# #
# # def assign_split(material_id):
# #     if material_id in train_materials:
# #         return "train"
# #     elif material_id in test_materials:
# #         return "test"
# #     else:
# #         return np.nan
# #
# #
# # split_all = [assign_split(mid) for mid in all_arr["ids"]]
# #
# # print("\n========== 最终模型按物质划分 ==========")
# # print(f"训练集物质数: {len(train_materials)}")
# # print(f"测试集物质数: {len(test_materials)}")
# #
# #
# # slope_df = pd.DataFrame({
# #     "Material_ID": all_arr["ids"],
# #     "Split": split_all,
# #     "slope": slope_all.flatten(),
# #     "Tb_pred": Tb_pred_all,
# #     "Tc_half_pred": Tc_half_pred_all,
# #     "Tc_full_pred_approx": Tc_pred_full_all,
# #     "Pc_pred_Pa": Pc_pred_all
# # })
# #
# # slope_df.to_csv("vp_slope_values_final_split.csv", index=False)
# # print("\n✅ slope 值已保存为: vp_slope_values_final_split.csv")
# #
# #
# # # =========================
# # # 9. 读取 transformed 数据，并映射 Material_ID
# # # =========================
# # trans_df = pd.read_excel(transformed_file).reset_index(drop=True).copy()
# #
# # if len(trans_df) % rows_per_material != 0:
# #     raise ValueError(
# #         f"{transformed_file} 的总行数 {len(trans_df)} 不是 {rows_per_material} 的整数倍，"
# #         f"无法按每个物质 {rows_per_material} 行映射。"
# #     )
# #
# # n_materials_trans = len(trans_df) // rows_per_material
# # n_materials_vp = len(df_valid)
# #
# # if n_materials_trans != n_materials_vp:
# #     raise ValueError(
# #         f"{transformed_file} 推断的物质数 = {n_materials_trans}，"
# #         f"而 vp 有效物质数 = {n_materials_vp}，二者不一致。"
# #     )
# #
# # ordered_material_ids = df_valid[id_col].values
# # trans_df["Material_ID"] = np.repeat(ordered_material_ids, rows_per_material)
# #
# # # 合并 slope 和最终模型的 train/test split
# # trans_with_slope = trans_df.merge(
# #     slope_df[[
# #         "Material_ID",
# #         "Split",
# #         "slope",
# #         "Tb_pred",
# #         "Tc_half_pred",
# #         "Tc_full_pred_approx",
# #         "Pc_pred_Pa"
# #     ]],
# #     on="Material_ID",
# #     how="left"
# # )
# #
# # trans_with_slope.to_excel("Transformed_vp_with_slope_and_final_split.xlsx", index=False)
# # print("✅ 已保存为: Transformed_vp_with_slope_and_final_split.xlsx")
# #
# #
# # # =========================
# # # 10. 最终随机森林模型
# # #     只有这里使用 train/test split
# # # =========================
# # final_train_df = trans_with_slope[trans_with_slope["Split"] == "train"].copy()
# # final_test_df = trans_with_slope[trans_with_slope["Split"] == "test"].copy()
# #
# # final_train_df[target_col_final] = pd.to_numeric(
# #     final_train_df[target_col_final],
# #     errors="coerce"
# # )
# #
# # final_test_df[target_col_final] = pd.to_numeric(
# #     final_test_df[target_col_final],
# #     errors="coerce"
# # )
# #
# # # 去掉目标缺失行
# # final_train_df = final_train_df.dropna(subset=[target_col_final]).copy()
# # final_test_df = final_test_df.dropna(subset=[target_col_final]).copy()
# #
# # drop_cols = [target_col_final, "Material_ID", "Split"]
# #
# # feature_cols = [
# #     c for c in final_train_df.columns
# #     if c not in drop_cols
# # ]
# #
# # X_train_final = final_train_df[feature_cols].copy()
# # X_test_final = final_test_df[feature_cols].copy()
# #
# # # 只保留数值列
# # numeric_cols = X_train_final.select_dtypes(include=[np.number]).columns.tolist()
# #
# # X_train_final = X_train_final[numeric_cols].copy()
# # X_test_final = X_test_final[numeric_cols].copy()
# #
# # # 转为数值，避免混入 object
# # X_train_final = X_train_final.apply(pd.to_numeric, errors="coerce")
# # X_test_final = X_test_final.apply(pd.to_numeric, errors="coerce")
# #
# # y_train_final = final_train_df[target_col_final].astype(float).values
# # y_test_final = final_test_df[target_col_final].astype(float).values
# #
# # # 去掉特征或目标中存在 NaN / inf 的行
# # train_valid_final_mask = (
# #     np.isfinite(X_train_final.values).all(axis=1)
# #     & np.isfinite(y_train_final)
# # )
# #
# # test_valid_final_mask = (
# #     np.isfinite(X_test_final.values).all(axis=1)
# #     & np.isfinite(y_test_final)
# # )
# #
# # final_train_df = final_train_df.loc[train_valid_final_mask].copy()
# # final_test_df = final_test_df.loc[test_valid_final_mask].copy()
# #
# # X_train_final = X_train_final.loc[train_valid_final_mask].copy()
# # X_test_final = X_test_final.loc[test_valid_final_mask].copy()
# #
# # y_train_final = y_train_final[train_valid_final_mask]
# # y_test_final = y_test_final[test_valid_final_mask]
# #
# # print("\n========== 最终 RF 模型数据 ==========")
# # print(f"最终训练集样本点数: {len(X_train_final)}")
# # print(f"最终测试集样本点数: {len(X_test_final)}")
# # print(f"最终模型特征数: {X_train_final.shape[1]}")
# #
# #
# # model_final = RandomForestRegressor(
# #     n_estimators=300,
# #     random_state=42,
# #     n_jobs=-1
# # )
# #
# # model_final.fit(X_train_final, y_train_final)
# #
# # y_train_pred = model_final.predict(X_train_final)
# # y_test_pred = model_final.predict(X_test_final)
# #
# # final_metrics_train = evaluate_final_regression(
# #     y_train_final,
# #     y_train_pred,
# #     "Final_RF_model",
# #     "train"
# # )
# #
# # final_metrics_test = evaluate_final_regression(
# #     y_test_final,
# #     y_test_pred,
# #     "Final_RF_model",
# #     "test"
# # )
# #
# #
# # # =========================
# # # 11. 保存最终预测结果
# # # =========================
# # train_result = final_train_df.copy()
# # train_result["Predicted_Vapor_Pressure"] = y_train_pred
# # train_result["Absolute_Error"] = np.abs(y_train_final - y_train_pred)
# # train_result["Relative_Error (%)"] = final_metrics_train["relative_error_%"]
# #
# # test_result = final_test_df.copy()
# # test_result["Predicted_Vapor_Pressure"] = y_test_pred
# # test_result["Absolute_Error"] = np.abs(y_test_final - y_test_pred)
# # test_result["Relative_Error (%)"] = final_metrics_test["relative_error_%"]
# #
# # train_result.to_excel(
# #     "train_prediction_vs_actual_vp_with_slope_submodels_all_data.xlsx",
# #     index=False
# # )
# #
# # test_result.to_excel(
# #     "test_prediction_vs_actual_vp_with_slope_submodels_all_data.xlsx",
# #     index=False
# # )
# #
# # print("\n✅ 已保存训练集预测结果: train_prediction_vs_actual_vp_with_slope_submodels_all_data.xlsx")
# # print("✅ 已保存测试集预测结果: test_prediction_vs_actual_vp_with_slope_submodels_all_data.xlsx")
# #
# #
# # # =========================
# # # 12. 子模型输出表
# # #     子模型不再有 train/test，只输出 all_data
# # # =========================
# # tb_out_all = pd.DataFrame({
# #     "Split": "all_data",
# #     "Material_ID": all_arr["ids"],
# #     "Tb_true": all_arr["Tb"],
# #     "Tb_pred": Tb_pred_all
# # })
# #
# # tc_out_all = pd.DataFrame({
# #     "Split": "all_data",
# #     "Material_ID": all_arr["ids"],
# #     "Tc_half_true": all_arr["Tc_half"],
# #     "Tc_half_pred": Tc_half_pred_all,
# #     "Tc_full_pred_approx": Tc_pred_full_all
# # })
# #
# # pc_out_all = pd.DataFrame({
# #     "Split": "all_data",
# #     "Material_ID": all_arr["ids"],
# #     "Pc_true_Pa": all_arr["Pc_bar"] * 1e5,
# #     "Pc_pred_Pa": Pc_pred_all
# # })
# #
# #
# # # =========================
# # # 13. 汇总表
# # # =========================
# # summary_rows = [
# #     tb_metrics_all,
# #     tc_metrics_all,
# #     pc_metrics_all,
# #     final_metrics_train,
# #     final_metrics_test
# # ]
# #
# # summary_df = pd.DataFrame(summary_rows)
# #
# #
# # # =========================
# # # 14. 保存最终 RF 特征重要性
# # # =========================
# # feature_importance_df = pd.DataFrame({
# #     "Feature": X_train_final.columns,
# #     "Importance": model_final.feature_importances_
# # }).sort_values(by="Importance", ascending=False)
# #
# #
# # # =========================
# # # 15. 总保存
# # # =========================
# # output_filename = "VP_pipeline_with_slope_submodels_all_data_final_train_test_split.xlsx"
# #
# # with pd.ExcelWriter(output_filename, engine="xlsxwriter") as writer:
# #     summary_df.to_excel(writer, sheet_name="summary", index=False)
# #
# #     slope_df.to_excel(writer, sheet_name="slope_pred", index=False)
# #
# #     tb_out_all.to_excel(writer, sheet_name="Tb_submodel", index=False)
# #     tc_out_all.to_excel(writer, sheet_name="Tc_half_submodel", index=False)
# #     pc_out_all.to_excel(writer, sheet_name="Pc_submodel", index=False)
# #
# #     pd.concat(
# #         [train_result, test_result],
# #         ignore_index=True
# #     ).to_excel(writer, sheet_name="final_predictions", index=False)
# #
# #     trans_with_slope.to_excel(
# #         writer,
# #         sheet_name="transformed_with_slope",
# #         index=False
# #     )
# #
# #     feature_importance_df.to_excel(
# #         writer,
# #         sheet_name="feature_importance",
# #         index=False
# #     )
# #
# # print(f"\n✅ 全部结果已保存至: {output_filename}")
#
#
# import numpy as np
# import pandas as pd
#
# from scipy.optimize import least_squares
# from sklearn.preprocessing import PolynomialFeatures
# from sklearn.linear_model import HuberRegressor
# from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split
#
#
# # =========================
# # 0. 参数区
# # =========================
# vp_file = "vp209.xlsx"
# vp_sheet = "Sheet1"
# transformed_file = "Transformed_vp_Dataset.xlsx"
#
# rows_per_material = 10
# random_state = 42
# target_col_final = "Vapor Pressure"
#
# pb = 101325.0
# Tb0 = 222.543
#
#
# # =========================
# # 1. 读取 vp 原始数据
# # =========================
# df = pd.read_excel(vp_file, sheet_name=vp_sheet).copy()
#
# id_col = df.columns[0]
#
# # 提取基础特征
# MW_all = pd.to_numeric(df.iloc[:, 4], errors="coerce").values.reshape(-1, 1)
# Nc_all = pd.to_numeric(df.iloc[:, 10], errors="coerce").values.reshape(-1, 1)
# Ncs_all = pd.to_numeric(df.iloc[:, 9], errors="coerce").values.reshape(-1, 1)
#
# Nk_all = df.iloc[:, 12:31].apply(pd.to_numeric, errors="coerce").values   # 19个基团
# T_all = df.iloc[:, 31:41].apply(pd.to_numeric, errors="coerce").values
# P_vp_all = df.iloc[:, 41:51].apply(pd.to_numeric, errors="coerce").values
#
# Tb_all = pd.to_numeric(df.iloc[:, 5], errors="coerce").values
# Tc_half_all = pd.to_numeric(df["ASPEN Half Critical T"], errors="coerce").values
# Pc_bar_all = pd.to_numeric(df.iloc[:, 51], errors="coerce").values
# compound_ids_all = df[id_col].values
#
# # 过滤掉非法蒸汽压物质：10个点都必须有限且 > 0
# valid_mask = np.isfinite(P_vp_all) & (P_vp_all > 0)
# valid_mask = valid_mask.all(axis=1)
#
# df_valid = df.loc[valid_mask].copy().reset_index(drop=True)
#
# print("========== 数据清洗后 ==========")
# print(f"有效物质数: {len(df_valid)}")
#
#
# # =========================
# # 2. 工具函数
# # =========================
# def evaluate_scalar_regression(y_true, y_pred, model_name, split_name):
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#
#     mask = np.isfinite(y_true) & np.isfinite(y_pred)
#     y_true_valid = y_true[mask]
#     y_pred_valid = y_pred[mask]
#
#     if len(y_true_valid) == 0:
#         print(f"\n{model_name} - {split_name}: 无有效样本")
#         return {
#             "Model": model_name,
#             "Split": split_name,
#             "R2": np.nan,
#             "MSE": np.nan
#         }
#
#     r2 = r2_score(y_true_valid, y_pred_valid)
#     mse = mean_squared_error(y_true_valid, y_pred_valid)
#
#     print(f"\n{model_name} - {split_name}")
#     print(f"R2  = {r2:.6f}")
#     print(f"MSE = {mse:.6f}")
#
#     return {
#         "Model": model_name,
#         "Split": split_name,
#         "R2": r2,
#         "MSE": mse
#     }
#
#
# def evaluate_final_regression(y_true, y_pred, model_name, split_name):
#     """
#     同时评价最终模型在两个空间中的表现：
#
#     1. 普通蒸汽压 P 空间：
#        R2_P, MSE_P, MAE_P, ARD, 误差阈值点数
#
#     2. 对数蒸汽压 ln(P) 空间：
#        R2_lnP, MSE_lnP, MAE_lnP
#
#     注意：
#     当前最终 RF 模型训练目标仍然是普通 Vapor Pressure。
#     这里的 ln(P) 指标只是评价阶段对 y_true 和 y_pred 取自然对数后计算。
#     """
#
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#
#     n = len(y_true)
#
#     finite_mask = np.isfinite(y_true) & np.isfinite(y_pred)
#
#     # 这些数组保持和原始输入等长，方便后面直接写回 DataFrame
#     relative_error_full = np.full(n, np.nan, dtype=float)
#     absolute_error_p_full = np.full(n, np.nan, dtype=float)
#
#     lnP_true_full = np.full(n, np.nan, dtype=float)
#     lnP_pred_full = np.full(n, np.nan, dtype=float)
#     absolute_error_lnP_full = np.full(n, np.nan, dtype=float)
#
#     if not np.any(finite_mask):
#         print(f"\n{model_name} - {split_name}: 无有效样本")
#         return {
#             "Model": model_name,
#             "Split": split_name,
#
#             "R2_P": np.nan,
#             "MSE_P": np.nan,
#             "MAE_P": np.nan,
#             "ARD_%": np.nan,
#             "within_1pct": 0,
#             "within_5pct": 0,
#             "within_10pct": 0,
#
#             "R2_lnP": np.nan,
#             "MSE_lnP": np.nan,
#             "MAE_lnP": np.nan,
#             "log_valid_count": 0,
#
#             "relative_error_%": relative_error_full,
#             "absolute_error_P": absolute_error_p_full,
#             "lnP_true": lnP_true_full,
#             "lnP_pred": lnP_pred_full,
#             "absolute_error_lnP": absolute_error_lnP_full
#         }
#
#     y_true_valid = y_true[finite_mask]
#     y_pred_valid = y_pred[finite_mask]
#
#     # =========================
#     # 2.1 普通 P 空间指标
#     # =========================
#     r2_P = r2_score(y_true_valid, y_pred_valid)
#     mse_P = mean_squared_error(y_true_valid, y_pred_valid)
#     mae_P = np.mean(np.abs(y_true_valid - y_pred_valid))
#
#     absolute_error_p_full[finite_mask] = np.abs(y_true_valid - y_pred_valid)
#
#     nonzero_valid = np.abs(y_true_valid) > 1e-12
#     relative_error_valid = np.full_like(y_true_valid, np.nan, dtype=float)
#
#     if np.any(nonzero_valid):
#         relative_error_valid[nonzero_valid] = np.abs(
#             (y_pred_valid[nonzero_valid] - y_true_valid[nonzero_valid])
#             / y_true_valid[nonzero_valid]
#         ) * 100
#         ard = np.nanmean(relative_error_valid)
#     else:
#         ard = np.nan
#
#     relative_error_full[finite_mask] = relative_error_valid
#
#     within_1pct = np.sum(relative_error_valid <= 1)
#     within_5pct = np.sum(relative_error_valid <= 5)
#     within_10pct = np.sum(relative_error_valid <= 10)
#
#     # =========================
#     # 2.2 ln(P) 空间指标
#     # =========================
#     log_mask = finite_mask & (y_true > 0) & (y_pred > 0)
#
#     if np.any(log_mask):
#         lnP_true_full[log_mask] = np.log(y_true[log_mask])
#         lnP_pred_full[log_mask] = np.log(y_pred[log_mask])
#
#         absolute_error_lnP_full[log_mask] = np.abs(
#             lnP_true_full[log_mask] - lnP_pred_full[log_mask]
#         )
#
#         r2_lnP = r2_score(
#             lnP_true_full[log_mask],
#             lnP_pred_full[log_mask]
#         )
#
#         mse_lnP = mean_squared_error(
#             lnP_true_full[log_mask],
#             lnP_pred_full[log_mask]
#         )
#
#         mae_lnP = np.mean(
#             absolute_error_lnP_full[log_mask]
#         )
#     else:
#         r2_lnP = np.nan
#         mse_lnP = np.nan
#         mae_lnP = np.nan
#
#     # =========================
#     # 2.3 打印结果
#     # =========================
#     print(f"\n{model_name} - {split_name}")
#
#     print("\n普通 P 空间指标:")
#     print(f"R2_P  = {r2_P:.6f}")
#     print(f"MSE_P = {mse_P:.6f}")
#     print(f"MAE_P = {mae_P:.6f}")
#     print(f"ARD_P = {ard:.2f}%")
#     print(f"误差 <= 1% 的点数: {within_1pct}")
#     print(f"误差 <= 5% 的点数: {within_5pct}")
#     print(f"误差 <= 10% 的点数: {within_10pct}")
#
#     print("\nln(P) 空间指标:")
#     print(f"R2_lnP  = {r2_lnP:.6f}")
#     print(f"MSE_lnP = {mse_lnP:.6f}")
#     print(f"MAE_lnP = {mae_lnP:.6f}")
#     print(f"可用于 ln(P) 评价的点数: {np.sum(log_mask)} / {n}")
#
#     return {
#         "Model": model_name,
#         "Split": split_name,
#
#         # 普通 P 空间
#         "R2_P": r2_P,
#         "MSE_P": mse_P,
#         "MAE_P": mae_P,
#         "ARD_%": ard,
#         "within_1pct": within_1pct,
#         "within_5pct": within_5pct,
#         "within_10pct": within_10pct,
#
#         # ln(P) 空间
#         "R2_lnP": r2_lnP,
#         "MSE_lnP": mse_lnP,
#         "MAE_lnP": mae_lnP,
#         "log_valid_count": np.sum(log_mask),
#
#         # 用于写入详细预测表
#         "relative_error_%": relative_error_full,
#         "absolute_error_P": absolute_error_p_full,
#         "lnP_true": lnP_true_full,
#         "lnP_pred": lnP_pred_full,
#         "absolute_error_lnP": absolute_error_lnP_full
#     }
#
#
# def get_arrays(df_part):
#     arrays = {
#         "ids": df_part[id_col].values,
#         "MW": pd.to_numeric(df_part.iloc[:, 4], errors="coerce").values.reshape(-1, 1),
#         "Nc": pd.to_numeric(df_part.iloc[:, 10], errors="coerce").values.reshape(-1, 1),
#         "Ncs": pd.to_numeric(df_part.iloc[:, 9], errors="coerce").values.reshape(-1, 1),
#         "Nk": df_part.iloc[:, 12:31].apply(pd.to_numeric, errors="coerce").values,
#         "T": df_part.iloc[:, 31:41].apply(pd.to_numeric, errors="coerce").values,
#         "P_vp": df_part.iloc[:, 41:51].apply(pd.to_numeric, errors="coerce").values,
#         "Tb": pd.to_numeric(df_part.iloc[:, 5], errors="coerce").values,
#         "Tc_half": pd.to_numeric(df_part["ASPEN Half Critical T"], errors="coerce").values,
#         "Pc_bar": pd.to_numeric(df_part.iloc[:, 51], errors="coerce").values,
#     }
#     return arrays
#
#
# def make_summary_row(metrics_dict):
#     """
#     汇总表只保留标量指标，不把逐样本误差数组写进 summary。
#     """
#     drop_keys = {
#         "relative_error_%",
#         "absolute_error_P",
#         "lnP_true",
#         "lnP_pred",
#         "absolute_error_lnP"
#     }
#     return {
#         k: v for k, v in metrics_dict.items()
#         if k not in drop_keys
#     }
#
#
# # 全体有效物质数组
# all_arr = get_arrays(df_valid)
#
#
# # =========================
# # 3. 构造 poly 特征
# #    注意：子模型不划分训练/测试，因此 poly 在全体有效物质上 fit
# # =========================
# poly = PolynomialFeatures(degree=2, include_bias=False)
# Nk_poly_all = poly.fit_transform(all_arr["Nk"])
#
#
# # =========================
# # 4. Tb 子模型
# #    子模型不划分训练集/测试集，使用全体有效物质训练
# # =========================
# tb_all_mask = (
#     np.isfinite(all_arr["Tb"])
#     & np.isfinite(Nk_poly_all).all(axis=1)
# )
#
# model_tb = HuberRegressor(max_iter=10000)
#
# model_tb.fit(
#     Nk_poly_all[tb_all_mask],
#     np.exp(all_arr["Tb"][tb_all_mask] / Tb0)
# )
#
# Tb_pred_all = Tb0 * np.log(
#     np.clip(model_tb.predict(Nk_poly_all), 1e-6, None)
# )
#
# tb_metrics_all = evaluate_scalar_regression(
#     all_arr["Tb"][tb_all_mask],
#     Tb_pred_all[tb_all_mask],
#     "Tb_submodel",
#     "all_data"
# )
#
#
# # =========================
# # 5. Tc_half 子模型
# #    子模型不划分训练集/测试集，使用全体有效物质训练
# # =========================
# tc_all_mask = (
#     np.isfinite(all_arr["Tc_half"])
#     & np.isfinite(Nk_poly_all).all(axis=1)
# )
#
# gb_model_tc = GradientBoostingRegressor(
#     n_estimators=300,
#     learning_rate=0.05,
#     max_depth=4,
#     random_state=0
# )
#
# gb_model_tc.fit(
#     Nk_poly_all[tc_all_mask],
#     all_arr["Tc_half"][tc_all_mask]
# )
#
# Tc_half_pred_all = gb_model_tc.predict(Nk_poly_all)
#
# tc_metrics_all = evaluate_scalar_regression(
#     all_arr["Tc_half"][tc_all_mask],
#     Tc_half_pred_all[tc_all_mask],
#     "Tc_half_submodel",
#     "all_data"
# )
#
# # 用于 slope 的完整临界温度近似
# Tc_pred_full_all = Tc_half_pred_all * 2.0
#
#
# # =========================
# # 6. Pc 子模型
# #    子模型不划分训练集/测试集，使用全体有效物质训练
# #    Pc 子模型保持原逻辑，不使用 poly，只用原始 19 个基团
# # =========================
# MW_all_flat = all_arr["MW"].flatten()
# Pc_bar_all_valid = all_arr["Pc_bar"]
#
#
# def residual_pc(params, X, MW, Pc_true):
#     beta = params[:-1]   # 19个基团系数
#     beta3 = params[-1]
#
#     y_pred = X @ beta
#     x_pred = y_pred + 0.108998
#
#     # 防止接近0导致 (1/x)^2 爆炸
#     x_pred = np.where(
#         np.abs(x_pred) < 1e-8,
#         np.sign(x_pred) * 1e-8 + (x_pred == 0) * 1e-8,
#         x_pred
#     )
#
#     Pc_pred = (
#         5.9827
#         + (1.0 / x_pred) ** 2
#         + beta3 * np.exp(1.0 / np.clip(MW, 1e-8, None))
#     )
#
#     return Pc_pred - Pc_true
#
#
# pc_all_mask = (
#     np.isfinite(Pc_bar_all_valid)
#     & np.isfinite(MW_all_flat)
#     & np.isfinite(all_arr["Nk"]).all(axis=1)
# )
#
# # 参数个数 = 19个基团 + 1个 beta3
# params_init_pc = np.zeros(all_arr["Nk"].shape[1] + 1)
#
# result_pc = least_squares(
#     residual_pc,
#     x0=params_init_pc,
#     args=(
#         all_arr["Nk"][pc_all_mask],
#         MW_all_flat[pc_all_mask],
#         Pc_bar_all_valid[pc_all_mask]
#     ),
#     max_nfev=5000
# )
#
#
# def predict_pc_pa(Nk_raw, MW, result_pc):
#     x_fit = Nk_raw @ result_pc.x[:-1] + 0.108998
#
#     x_fit = np.where(
#         np.abs(x_fit) < 1e-8,
#         np.sign(x_fit) * 1e-8 + (x_fit == 0) * 1e-8,
#         x_fit
#     )
#
#     Pc_pred_bar = (
#         5.9827
#         + (1.0 / x_fit) ** 2
#         + result_pc.x[-1] * np.exp(1.0 / np.clip(MW, 1e-8, None))
#     )
#
#     return Pc_pred_bar * 1e5   # bar 转 Pa
#
#
# Pc_pred_all = predict_pc_pa(
#     all_arr["Nk"],
#     MW_all_flat,
#     result_pc
# )
#
# pc_metrics_all = evaluate_scalar_regression(
#     Pc_bar_all_valid[pc_all_mask] * 1e5,
#     Pc_pred_all[pc_all_mask],
#     "Pc_submodel",
#     "all_data"
# )
#
#
# # =========================
# # 7. 计算 slope
# #    基于全数据训练出来的 Tb / Tc / Pc 子模型预测值
# # =========================
# def build_slope(Tb_pred, Tc_pred_full, Pc_pred_pa):
#     denom = Tc_pred_full - Tb_pred
#     slope = np.full_like(Tb_pred, np.nan, dtype=float)
#
#     valid = (
#         np.isfinite(Tb_pred)
#         & np.isfinite(Tc_pred_full)
#         & np.isfinite(Pc_pred_pa)
#         & (Pc_pred_pa > 0)
#         & (np.abs(denom) > 1e-12)
#     )
#
#     slope[valid] = (
#         np.log(Pc_pred_pa[valid]) - np.log(pb)
#     ) / denom[valid]
#
#     return slope.reshape(-1, 1)
#
#
# slope_all = build_slope(
#     Tb_pred_all,
#     Tc_pred_full_all,
#     Pc_pred_all
# )
#
#
# # =========================
# # 8. 最终模型按物质 8:2 划分
# #    注意：只有最终模型划分训练集/测试集
# # =========================
# unique_materials = df_valid[id_col].unique()
#
# train_materials, test_materials = train_test_split(
#     unique_materials,
#     test_size=0.2,
#     random_state=random_state
# )
#
# train_materials = set(train_materials)
# test_materials = set(test_materials)
#
#
# def assign_split(material_id):
#     if material_id in train_materials:
#         return "train"
#     elif material_id in test_materials:
#         return "test"
#     else:
#         return np.nan
#
#
# split_all = [assign_split(mid) for mid in all_arr["ids"]]
#
# print("\n========== 最终模型按物质划分 ==========")
# print(f"训练集物质数: {len(train_materials)}")
# print(f"测试集物质数: {len(test_materials)}")
#
#
# slope_df = pd.DataFrame({
#     "Material_ID": all_arr["ids"],
#     "Split": split_all,
#     "slope": slope_all.flatten(),
#     "Tb_pred": Tb_pred_all,
#     "Tc_half_pred": Tc_half_pred_all,
#     "Tc_full_pred_approx": Tc_pred_full_all,
#     "Pc_pred_Pa": Pc_pred_all
# })
#
# slope_df.to_csv("vp_slope_values_final_split.csv", index=False)
# print("\nslope 值已保存为: vp_slope_values_final_split.csv")
#
#
# # =========================
# # 9. 读取 transformed 数据，并映射 Material_ID
# # =========================
# trans_df = pd.read_excel(transformed_file).reset_index(drop=True).copy()
#
# if len(trans_df) % rows_per_material != 0:
#     raise ValueError(
#         f"{transformed_file} 的总行数 {len(trans_df)} 不是 {rows_per_material} 的整数倍，"
#         f"无法按每个物质 {rows_per_material} 行映射。"
#     )
#
# n_materials_trans = len(trans_df) // rows_per_material
# n_materials_vp = len(df_valid)
#
# if n_materials_trans != n_materials_vp:
#     raise ValueError(
#         f"{transformed_file} 推断的物质数 = {n_materials_trans}，"
#         f"而 vp 有效物质数 = {n_materials_vp}，二者不一致。"
#     )
#
# ordered_material_ids = df_valid[id_col].values
# trans_df["Material_ID"] = np.repeat(ordered_material_ids, rows_per_material)
#
# # 合并 slope 和最终模型的 train/test split
# trans_with_slope = trans_df.merge(
#     slope_df[[
#         "Material_ID",
#         "Split",
#         "slope",
#         "Tb_pred",
#         "Tc_half_pred",
#         "Tc_full_pred_approx",
#         "Pc_pred_Pa"
#     ]],
#     on="Material_ID",
#     how="left"
# )
#
# trans_with_slope.to_excel(
#     "Transformed_vp_with_slope_and_final_split.xlsx",
#     index=False
# )
#
# print("已保存为: Transformed_vp_with_slope_and_final_split.xlsx")
#
#
# # =========================
# # 10. 最终随机森林模型
# #     只有这里使用 train/test split
# # =========================
# final_train_df = trans_with_slope[
#     trans_with_slope["Split"] == "train"
# ].copy()
#
# final_test_df = trans_with_slope[
#     trans_with_slope["Split"] == "test"
# ].copy()
#
# final_train_df[target_col_final] = pd.to_numeric(
#     final_train_df[target_col_final],
#     errors="coerce"
# )
#
# final_test_df[target_col_final] = pd.to_numeric(
#     final_test_df[target_col_final],
#     errors="coerce"
# )
#
# # 去掉目标缺失行
# final_train_df = final_train_df.dropna(subset=[target_col_final]).copy()
# final_test_df = final_test_df.dropna(subset=[target_col_final]).copy()
#
# drop_cols = [
#     target_col_final,
#     "Material_ID",
#     "Split"
# ]
#
# feature_cols = [
#     c for c in final_train_df.columns
#     if c not in drop_cols
# ]
#
# X_train_final = final_train_df[feature_cols].copy()
# X_test_final = final_test_df[feature_cols].copy()
#
# # 只保留数值列
# numeric_cols = X_train_final.select_dtypes(include=[np.number]).columns.tolist()
#
# X_train_final = X_train_final[numeric_cols].copy()
# X_test_final = X_test_final[numeric_cols].copy()
#
# # 转为数值，避免混入 object
# X_train_final = X_train_final.apply(pd.to_numeric, errors="coerce")
# X_test_final = X_test_final.apply(pd.to_numeric, errors="coerce")
#
# y_train_final = final_train_df[target_col_final].astype(float).values
# y_test_final = final_test_df[target_col_final].astype(float).values
#
# # 去掉特征或目标中存在 NaN / inf 的行
# train_valid_final_mask = (
#     np.isfinite(X_train_final.values).all(axis=1)
#     & np.isfinite(y_train_final)
# )
#
# test_valid_final_mask = (
#     np.isfinite(X_test_final.values).all(axis=1)
#     & np.isfinite(y_test_final)
# )
#
# final_train_df = final_train_df.loc[train_valid_final_mask].copy()
# final_test_df = final_test_df.loc[test_valid_final_mask].copy()
#
# X_train_final = X_train_final.loc[train_valid_final_mask].copy()
# X_test_final = X_test_final.loc[test_valid_final_mask].copy()
#
# y_train_final = y_train_final[train_valid_final_mask]
# y_test_final = y_test_final[test_valid_final_mask]
#
# print("\n========== 最终 RF 模型数据 ==========")
# print(f"最终训练集样本点数: {len(X_train_final)}")
# print(f"最终测试集样本点数: {len(X_test_final)}")
# print(f"最终模型特征数: {X_train_final.shape[1]}")
#
#
# model_final = RandomForestRegressor(
#     n_estimators=300,
#     random_state=42,
#     n_jobs=-1
# )
#
# # 注意：这里训练目标仍然是普通 Vapor Pressure，而不是 ln(P)
# model_final.fit(X_train_final, y_train_final)
#
# y_train_pred = model_final.predict(X_train_final)
# y_test_pred = model_final.predict(X_test_final)
#
# final_metrics_train = evaluate_final_regression(
#     y_train_final,
#     y_train_pred,
#     "Final_RF_model",
#     "train"
# )
#
# final_metrics_test = evaluate_final_regression(
#     y_test_final,
#     y_test_pred,
#     "Final_RF_model",
#     "test"
# )
#
#
# # =========================
# # 11. 保存最终预测结果
# # =========================
# train_result = final_train_df.copy()
#
# train_result["Vapor_Pressure_true"] = y_train_final
# train_result["Predicted_Vapor_Pressure"] = y_train_pred
#
# train_result["Absolute_Error_P"] = final_metrics_train["absolute_error_P"]
# train_result["Relative_Error_P (%)"] = final_metrics_train["relative_error_%"]
#
# train_result["lnP_true"] = final_metrics_train["lnP_true"]
# train_result["lnP_pred"] = final_metrics_train["lnP_pred"]
# train_result["Absolute_Error_lnP"] = final_metrics_train["absolute_error_lnP"]
#
# test_result = final_test_df.copy()
#
# test_result["Vapor_Pressure_true"] = y_test_final
# test_result["Predicted_Vapor_Pressure"] = y_test_pred
#
# test_result["Absolute_Error_P"] = final_metrics_test["absolute_error_P"]
# test_result["Relative_Error_P (%)"] = final_metrics_test["relative_error_%"]
#
# test_result["lnP_true"] = final_metrics_test["lnP_true"]
# test_result["lnP_pred"] = final_metrics_test["lnP_pred"]
# test_result["Absolute_Error_lnP"] = final_metrics_test["absolute_error_lnP"]
#
# train_result.to_excel(
#     "train_prediction_vs_actual_vp_with_slope_submodels_all_data_with_lnP.xlsx",
#     index=False
# )
#
# test_result.to_excel(
#     "test_prediction_vs_actual_vp_with_slope_submodels_all_data_with_lnP.xlsx",
#     index=False
# )
#
# print("\n已保存训练集预测结果: train_prediction_vs_actual_vp_with_slope_submodels_all_data_with_lnP.xlsx")
# print("已保存测试集预测结果: test_prediction_vs_actual_vp_with_slope_submodels_all_data_with_lnP.xlsx")
#
#
# # =========================
# # 12. 子模型输出表
# #     子模型不再有 train/test，只输出 all_data
# # =========================
# tb_out_all = pd.DataFrame({
#     "Split": "all_data",
#     "Material_ID": all_arr["ids"],
#     "Tb_true": all_arr["Tb"],
#     "Tb_pred": Tb_pred_all
# })
#
# tc_out_all = pd.DataFrame({
#     "Split": "all_data",
#     "Material_ID": all_arr["ids"],
#     "Tc_half_true": all_arr["Tc_half"],
#     "Tc_half_pred": Tc_half_pred_all,
#     "Tc_full_pred_approx": Tc_pred_full_all
# })
#
# pc_out_all = pd.DataFrame({
#     "Split": "all_data",
#     "Material_ID": all_arr["ids"],
#     "Pc_true_Pa": all_arr["Pc_bar"] * 1e5,
#     "Pc_pred_Pa": Pc_pred_all
# })
#
#
# # =========================
# # 13. 汇总表
# # =========================
# summary_rows = [
#     make_summary_row(tb_metrics_all),
#     make_summary_row(tc_metrics_all),
#     make_summary_row(pc_metrics_all),
#     make_summary_row(final_metrics_train),
#     make_summary_row(final_metrics_test)
# ]
#
# summary_df = pd.DataFrame(summary_rows)
#
#
# # =========================
# # 14. 保存最终 RF 特征重要性
# # =========================
# feature_importance_df = pd.DataFrame({
#     "Feature": X_train_final.columns,
#     "Importance": model_final.feature_importances_
# }).sort_values(by="Importance", ascending=False)
#
#
# # =========================
# # 15. 总保存
# # =========================
# output_filename = "VP_pipeline_with_slope_submodels_all_data_final_train_test_split_with_lnP.xlsx"
#
# with pd.ExcelWriter(output_filename, engine="xlsxwriter") as writer:
#     summary_df.to_excel(
#         writer,
#         sheet_name="summary",
#         index=False
#     )
#
#     slope_df.to_excel(
#         writer,
#         sheet_name="slope_pred",
#         index=False
#     )
#
#     tb_out_all.to_excel(
#         writer,
#         sheet_name="Tb_submodel",
#         index=False
#     )
#
#     tc_out_all.to_excel(
#         writer,
#         sheet_name="Tc_half_submodel",
#         index=False
#     )
#
#     pc_out_all.to_excel(
#         writer,
#         sheet_name="Pc_submodel",
#         index=False
#     )
#
#     pd.concat(
#         [train_result, test_result],
#         ignore_index=True
#     ).to_excel(
#         writer,
#         sheet_name="final_predictions",
#         index=False
#     )
#
#     trans_with_slope.to_excel(
#         writer,
#         sheet_name="transformed_with_slope",
#         index=False
#     )
#
#     feature_importance_df.to_excel(
#         writer,
#         sheet_name="feature_importance",
#         index=False
#     )
#
# print(f"\n全部结果已保存至: {output_filename}")

import numpy as np
import pandas as pd

from scipy.optimize import least_squares
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import HuberRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


# =========================
# 0. 参数区
# =========================
vp_file = "vp209.xlsx"
vp_sheet = "Sheet1"
transformed_file = "Transformed_vp_Dataset.xlsx"

rows_per_material = 10
random_state = 42
target_col_final = "Vapor Pressure"

pb = 101325.0
Tb0 = 222.543


# =========================
# 1. 读取 vp 原始数据
# =========================
df = pd.read_excel(vp_file, sheet_name=vp_sheet).copy()

id_col = df.columns[0]

# 提取基础特征
MW_all = pd.to_numeric(df.iloc[:, 4], errors="coerce").values.reshape(-1, 1)
Nc_all = pd.to_numeric(df.iloc[:, 10], errors="coerce").values.reshape(-1, 1)
Ncs_all = pd.to_numeric(df.iloc[:, 9], errors="coerce").values.reshape(-1, 1)

Nk_all = df.iloc[:, 12:31].apply(pd.to_numeric, errors="coerce").values
T_all = df.iloc[:, 31:41].apply(pd.to_numeric, errors="coerce").values
P_vp_all = df.iloc[:, 41:51].apply(pd.to_numeric, errors="coerce").values

Tb_all = pd.to_numeric(df.iloc[:, 5], errors="coerce").values
Tc_half_all = pd.to_numeric(df["ASPEN Half Critical T"], errors="coerce").values
Pc_bar_all = pd.to_numeric(df.iloc[:, 51], errors="coerce").values
compound_ids_all = df[id_col].values

# 过滤掉非法蒸汽压物质：10个点都必须有限且 > 0
valid_mask = np.isfinite(P_vp_all) & (P_vp_all > 0)
valid_mask = valid_mask.all(axis=1)

df_valid = df.loc[valid_mask].copy().reset_index(drop=True)

print("========== 数据清洗后 ==========")
print(f"有效物质数: {len(df_valid)}")


# =========================
# 2. 工具函数
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


def evaluate_final_regression(y_true, y_pred, model_name, split_name, strict_less=False):
    """
    同时评价最终模型在两个空间中的表现：

    1. 普通蒸汽压 P 空间：
       R2_P, MSE_P, MAE_P, ARD, 误差阈值点数

    2. 对数蒸汽压 ln(P) 空间：
       R2_lnP, MSE_lnP, MAE_lnP

    strict_less=False：统计 <=1%, <=5%, <=10%
    strict_less=True ：统计 <1%, <5%, <10%

    注意：
    当前最终 RF 模型训练目标仍然是普通 Vapor Pressure。
    这里的 ln(P) 指标只是评价阶段对 y_true 和 y_pred 取自然对数后计算。
    """

    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    n = len(y_true)
    finite_mask = np.isfinite(y_true) & np.isfinite(y_pred)

    # 这些数组保持和原始输入等长，方便后面直接写回 DataFrame
    relative_error_full = np.full(n, np.nan, dtype=float)
    absolute_error_p_full = np.full(n, np.nan, dtype=float)

    lnP_true_full = np.full(n, np.nan, dtype=float)
    lnP_pred_full = np.full(n, np.nan, dtype=float)
    absolute_error_lnP_full = np.full(n, np.nan, dtype=float)

    if not np.any(finite_mask):
        print(f"\n{model_name} - {split_name}: 无有效样本")
        return {
            "Model": model_name,
            "Split": split_name,

            "R2_P": np.nan,
            "MSE_P": np.nan,
            "MAE_P": np.nan,
            "ARD_%": np.nan,
            "within_1pct": 0,
            "within_5pct": 0,
            "within_10pct": 0,

            "R2_lnP": np.nan,
            "MSE_lnP": np.nan,
            "MAE_lnP": np.nan,
            "log_valid_count": 0,

            "relative_error_%": relative_error_full,
            "absolute_error_P": absolute_error_p_full,
            "lnP_true": lnP_true_full,
            "lnP_pred": lnP_pred_full,
            "absolute_error_lnP": absolute_error_lnP_full
        }

    y_true_valid = y_true[finite_mask]
    y_pred_valid = y_pred[finite_mask]

    # =========================
    # 2.1 普通 P 空间指标
    # =========================
    r2_P = r2_score(y_true_valid, y_pred_valid)
    mse_P = mean_squared_error(y_true_valid, y_pred_valid)
    mae_P = np.mean(np.abs(y_true_valid - y_pred_valid))

    absolute_error_p_full[finite_mask] = np.abs(y_true_valid - y_pred_valid)

    nonzero_valid = np.abs(y_true_valid) > 1e-12
    relative_error_valid = np.full_like(y_true_valid, np.nan, dtype=float)

    if np.any(nonzero_valid):
        relative_error_valid[nonzero_valid] = np.abs(
            (y_pred_valid[nonzero_valid] - y_true_valid[nonzero_valid])
            / y_true_valid[nonzero_valid]
        ) * 100
        ard = np.nanmean(relative_error_valid)
    else:
        ard = np.nan

    relative_error_full[finite_mask] = relative_error_valid

    if strict_less:
        within_1pct = np.sum(relative_error_valid < 1)
        within_5pct = np.sum(relative_error_valid < 5)
        within_10pct = np.sum(relative_error_valid < 10)
    else:
        within_1pct = np.sum(relative_error_valid <= 1)
        within_5pct = np.sum(relative_error_valid <= 5)
        within_10pct = np.sum(relative_error_valid <= 10)

    # =========================
    # 2.2 ln(P) 空间指标
    # =========================
    log_mask = finite_mask & (y_true > 0) & (y_pred > 0)

    if np.any(log_mask):
        lnP_true_full[log_mask] = np.log(y_true[log_mask])
        lnP_pred_full[log_mask] = np.log(y_pred[log_mask])

        absolute_error_lnP_full[log_mask] = np.abs(
            lnP_true_full[log_mask] - lnP_pred_full[log_mask]
        )

        r2_lnP = r2_score(
            lnP_true_full[log_mask],
            lnP_pred_full[log_mask]
        )

        mse_lnP = mean_squared_error(
            lnP_true_full[log_mask],
            lnP_pred_full[log_mask]
        )

        mae_lnP = np.mean(
            absolute_error_lnP_full[log_mask]
        )
    else:
        r2_lnP = np.nan
        mse_lnP = np.nan
        mae_lnP = np.nan

    # =========================
    # 2.3 打印结果
    # =========================
    print(f"\n{model_name} - {split_name}")

    print("\n普通 P 空间指标:")
    print(f"R2_P  = {r2_P:.6f}")
    print(f"MSE_P = {mse_P:.6f}")
    print(f"MAE_P = {mae_P:.6f}")
    print(f"ARD_P = {ard:.2f}%")

    if strict_less:
        print(f"误差 < 1% 的点数: {within_1pct}")
        print(f"误差 < 5% 的点数: {within_5pct}")
        print(f"误差 < 10% 的点数: {within_10pct}")
    else:
        print(f"误差 <= 1% 的点数: {within_1pct}")
        print(f"误差 <= 5% 的点数: {within_5pct}")
        print(f"误差 <= 10% 的点数: {within_10pct}")

    print("\nln(P) 空间指标:")
    print(f"R2_lnP  = {r2_lnP:.6f}")
    print(f"MSE_lnP = {mse_lnP:.6f}")
    print(f"MAE_lnP = {mae_lnP:.6f}")
    print(f"可用于 ln(P) 评价的点数: {np.sum(log_mask)} / {n}")

    return {
        "Model": model_name,
        "Split": split_name,

        # 普通 P 空间
        "R2_P": r2_P,
        "MSE_P": mse_P,
        "MAE_P": mae_P,
        "ARD_%": ard,
        "within_1pct": within_1pct,
        "within_5pct": within_5pct,
        "within_10pct": within_10pct,

        # ln(P) 空间
        "R2_lnP": r2_lnP,
        "MSE_lnP": mse_lnP,
        "MAE_lnP": mae_lnP,
        "log_valid_count": np.sum(log_mask),

        # 用于写入详细预测表
        "relative_error_%": relative_error_full,
        "absolute_error_P": absolute_error_p_full,
        "lnP_true": lnP_true_full,
        "lnP_pred": lnP_pred_full,
        "absolute_error_lnP": absolute_error_lnP_full
    }


def get_arrays(df_part):
    arrays = {
        "ids": df_part[id_col].values,
        "MW": pd.to_numeric(df_part.iloc[:, 4], errors="coerce").values.reshape(-1, 1),
        "Nc": pd.to_numeric(df_part.iloc[:, 10], errors="coerce").values.reshape(-1, 1),
        "Ncs": pd.to_numeric(df_part.iloc[:, 9], errors="coerce").values.reshape(-1, 1),
        "Nk": df_part.iloc[:, 12:31].apply(pd.to_numeric, errors="coerce").values,
        "T": df_part.iloc[:, 31:41].apply(pd.to_numeric, errors="coerce").values,
        "P_vp": df_part.iloc[:, 41:51].apply(pd.to_numeric, errors="coerce").values,
        "Tb": pd.to_numeric(df_part.iloc[:, 5], errors="coerce").values,
        "Tc_half": pd.to_numeric(df_part["ASPEN Half Critical T"], errors="coerce").values,
        "Pc_bar": pd.to_numeric(df_part.iloc[:, 51], errors="coerce").values,
    }
    return arrays


def make_summary_row(metrics_dict):
    """
    汇总表只保留标量指标，不把逐样本误差数组写进 summary。
    """
    drop_keys = {
        "relative_error_%",
        "absolute_error_P",
        "lnP_true",
        "lnP_pred",
        "absolute_error_lnP"
    }

    return {
        k: v for k, v in metrics_dict.items()
        if k not in drop_keys
    }


# 全体有效物质数组
all_arr = get_arrays(df_valid)


# =========================
# 3. 构造 poly 特征
#    注意：子模型不划分训练/测试，因此 poly 在全体有效物质上 fit
# =========================
poly = PolynomialFeatures(degree=2, include_bias=False)
Nk_poly_all = poly.fit_transform(all_arr["Nk"])


# =========================
# 4. Tb 子模型
#    子模型不划分训练集/测试集，使用全体有效物质训练
# =========================
tb_all_mask = (
    np.isfinite(all_arr["Tb"])
    & np.isfinite(Nk_poly_all).all(axis=1)
)

model_tb = HuberRegressor(max_iter=10000)

model_tb.fit(
    Nk_poly_all[tb_all_mask],
    np.exp(all_arr["Tb"][tb_all_mask] / Tb0)
)

Tb_pred_all = Tb0 * np.log(
    np.clip(model_tb.predict(Nk_poly_all), 1e-6, None)
)

tb_metrics_all = evaluate_scalar_regression(
    all_arr["Tb"][tb_all_mask],
    Tb_pred_all[tb_all_mask],
    "Tb_submodel",
    "all_data"
)


# =========================
# 5. Tc_half 子模型
#    子模型不划分训练集/测试集，使用全体有效物质训练
# =========================
tc_all_mask = (
    np.isfinite(all_arr["Tc_half"])
    & np.isfinite(Nk_poly_all).all(axis=1)
)

gb_model_tc = GradientBoostingRegressor(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=4,
    random_state=0
)

gb_model_tc.fit(
    Nk_poly_all[tc_all_mask],
    all_arr["Tc_half"][tc_all_mask]
)

Tc_half_pred_all = gb_model_tc.predict(Nk_poly_all)

tc_metrics_all = evaluate_scalar_regression(
    all_arr["Tc_half"][tc_all_mask],
    Tc_half_pred_all[tc_all_mask],
    "Tc_half_submodel",
    "all_data"
)

# 用于 slope 的完整临界温度近似
Tc_pred_full_all = Tc_half_pred_all * 2.0


# =========================
# 6. Pc 子模型
#    子模型不划分训练集/测试集，使用全体有效物质训练
#    Pc 子模型保持原逻辑，不使用 poly，只用原始 19 个基团
# =========================
MW_all_flat = all_arr["MW"].flatten()
Pc_bar_all_valid = all_arr["Pc_bar"]


def residual_pc(params, X, MW, Pc_true):
    beta = params[:-1]
    beta3 = params[-1]

    y_pred = X @ beta
    x_pred = y_pred + 0.108998

    # 防止接近0导致 (1/x)^2 爆炸
    x_pred = np.where(
        np.abs(x_pred) < 1e-8,
        np.sign(x_pred) * 1e-8 + (x_pred == 0) * 1e-8,
        x_pred
    )

    Pc_pred = (
        5.9827
        + (1.0 / x_pred) ** 2
        + beta3 * np.exp(1.0 / np.clip(MW, 1e-8, None))
    )

    return Pc_pred - Pc_true


pc_all_mask = (
    np.isfinite(Pc_bar_all_valid)
    & np.isfinite(MW_all_flat)
    & np.isfinite(all_arr["Nk"]).all(axis=1)
)

# 参数个数 = 19个基团 + 1个 beta3
params_init_pc = np.zeros(all_arr["Nk"].shape[1] + 1)

result_pc = least_squares(
    residual_pc,
    x0=params_init_pc,
    args=(
        all_arr["Nk"][pc_all_mask],
        MW_all_flat[pc_all_mask],
        Pc_bar_all_valid[pc_all_mask]
    ),
    max_nfev=5000
)


def predict_pc_pa(Nk_raw, MW, result_pc):
    x_fit = Nk_raw @ result_pc.x[:-1] + 0.108998

    x_fit = np.where(
        np.abs(x_fit) < 1e-8,
        np.sign(x_fit) * 1e-8 + (x_fit == 0) * 1e-8,
        x_fit
    )

    Pc_pred_bar = (
        5.9827
        + (1.0 / x_fit) ** 2
        + result_pc.x[-1] * np.exp(1.0 / np.clip(MW, 1e-8, None))
    )

    return Pc_pred_bar * 1e5


Pc_pred_all = predict_pc_pa(
    all_arr["Nk"],
    MW_all_flat,
    result_pc
)

pc_metrics_all = evaluate_scalar_regression(
    Pc_bar_all_valid[pc_all_mask] * 1e5,
    Pc_pred_all[pc_all_mask],
    "Pc_submodel",
    "all_data"
)


# =========================
# 7. 计算 slope
#    基于全数据训练出来的 Tb / Tc / Pc 子模型预测值
# =========================
def build_slope(Tb_pred, Tc_pred_full, Pc_pred_pa):
    denom = Tc_pred_full - Tb_pred
    slope = np.full_like(Tb_pred, np.nan, dtype=float)

    valid = (
        np.isfinite(Tb_pred)
        & np.isfinite(Tc_pred_full)
        & np.isfinite(Pc_pred_pa)
        & (Pc_pred_pa > 0)
        & (np.abs(denom) > 1e-12)
    )

    slope[valid] = (
        np.log(Pc_pred_pa[valid]) - np.log(pb)
    ) / denom[valid]

    return slope.reshape(-1, 1)


slope_all = build_slope(
    Tb_pred_all,
    Tc_pred_full_all,
    Pc_pred_all
)


# =========================
# 8. 最终模型按物质 8:2 划分
#    注意：只有最终模型划分训练集/测试集
# =========================
unique_materials = df_valid[id_col].unique()

train_materials, test_materials = train_test_split(
    unique_materials,
    test_size=0.2,
    random_state=random_state
)

train_materials = set(train_materials)
test_materials = set(test_materials)


def assign_split(material_id):
    if material_id in train_materials:
        return "train"
    elif material_id in test_materials:
        return "test"
    else:
        return np.nan


split_all = [assign_split(mid) for mid in all_arr["ids"]]

print("\n========== 最终模型按物质划分 ==========")
print(f"训练集物质数: {len(train_materials)}")
print(f"测试集物质数: {len(test_materials)}")


slope_df = pd.DataFrame({
    "Material_ID": all_arr["ids"],
    "Split": split_all,
    "slope": slope_all.flatten(),
    "Tb_pred": Tb_pred_all,
    "Tc_half_pred": Tc_half_pred_all,
    "Tc_full_pred_approx": Tc_pred_full_all,
    "Pc_pred_Pa": Pc_pred_all
})

slope_df.to_csv("vp_slope_values_final_split.csv", index=False)
print("\nslope 值已保存为: vp_slope_values_final_split.csv")


# =========================
# 9. 读取 transformed 数据，并映射 Material_ID
# =========================
trans_df = pd.read_excel(transformed_file).reset_index(drop=True).copy()

if len(trans_df) % rows_per_material != 0:
    raise ValueError(
        f"{transformed_file} 的总行数 {len(trans_df)} 不是 {rows_per_material} 的整数倍，"
        f"无法按每个物质 {rows_per_material} 行映射。"
    )

n_materials_trans = len(trans_df) // rows_per_material
n_materials_vp = len(df_valid)

if n_materials_trans != n_materials_vp:
    raise ValueError(
        f"{transformed_file} 推断的物质数 = {n_materials_trans}，"
        f"而 vp 有效物质数 = {n_materials_vp}，二者不一致。"
    )

ordered_material_ids = df_valid[id_col].values
trans_df["Material_ID"] = np.repeat(ordered_material_ids, rows_per_material)

# 合并 slope 和最终模型的 train/test split
trans_with_slope = trans_df.merge(
    slope_df[[
        "Material_ID",
        "Split",
        "slope",
        "Tb_pred",
        "Tc_half_pred",
        "Tc_full_pred_approx",
        "Pc_pred_Pa"
    ]],
    on="Material_ID",
    how="left"
)

trans_with_slope.to_excel(
    "Transformed_vp_with_slope_and_final_split.xlsx",
    index=False
)

print("已保存为: Transformed_vp_with_slope_and_final_split.xlsx")


# =========================
# 10. 最终随机森林模型
#     只有这里使用 train/test split
# =========================
final_train_df = trans_with_slope[
    trans_with_slope["Split"] == "train"
].copy()

final_test_df = trans_with_slope[
    trans_with_slope["Split"] == "test"
].copy()

final_train_df[target_col_final] = pd.to_numeric(
    final_train_df[target_col_final],
    errors="coerce"
)

final_test_df[target_col_final] = pd.to_numeric(
    final_test_df[target_col_final],
    errors="coerce"
)

# 去掉目标缺失行
final_train_df = final_train_df.dropna(subset=[target_col_final]).copy()
final_test_df = final_test_df.dropna(subset=[target_col_final]).copy()

drop_cols = [
    target_col_final,
    "Material_ID",
    "Split"
]

feature_cols = [
    c for c in final_train_df.columns
    if c not in drop_cols
]

X_train_final = final_train_df[feature_cols].copy()
X_test_final = final_test_df[feature_cols].copy()

# 只保留数值列
numeric_cols = X_train_final.select_dtypes(include=[np.number]).columns.tolist()

X_train_final = X_train_final[numeric_cols].copy()
X_test_final = X_test_final[numeric_cols].copy()

# 转为数值，避免混入 object
X_train_final = X_train_final.apply(pd.to_numeric, errors="coerce")
X_test_final = X_test_final.apply(pd.to_numeric, errors="coerce")

y_train_final = final_train_df[target_col_final].astype(float).values
y_test_final = final_test_df[target_col_final].astype(float).values

# 去掉特征或目标中存在 NaN / inf 的行
train_valid_final_mask = (
    np.isfinite(X_train_final.values).all(axis=1)
    & np.isfinite(y_train_final)
)

test_valid_final_mask = (
    np.isfinite(X_test_final.values).all(axis=1)
    & np.isfinite(y_test_final)
)

final_train_df = final_train_df.loc[train_valid_final_mask].copy()
final_test_df = final_test_df.loc[test_valid_final_mask].copy()

X_train_final = X_train_final.loc[train_valid_final_mask].copy()
X_test_final = X_test_final.loc[test_valid_final_mask].copy()

y_train_final = y_train_final[train_valid_final_mask]
y_test_final = y_test_final[test_valid_final_mask]

print("\n========== 最终 RF 模型数据 ==========")
print(f"最终训练集样本点数: {len(X_train_final)}")
print(f"最终测试集样本点数: {len(X_test_final)}")
print(f"最终模型特征数: {X_train_final.shape[1]}")


model_final = RandomForestRegressor(
    n_estimators=300,
    random_state=42,
    n_jobs=-1
)

# 注意：这里训练目标仍然是普通 Vapor Pressure，而不是 ln(P)
model_final.fit(X_train_final, y_train_final)

y_train_pred = model_final.predict(X_train_final)
y_test_pred = model_final.predict(X_test_final)

final_metrics_train = evaluate_final_regression(
    y_train_final,
    y_train_pred,
    "Final_RF_model",
    "train",
    strict_less=False
)

final_metrics_test = evaluate_final_regression(
    y_test_final,
    y_test_pred,
    "Final_RF_model",
    "test",
    strict_less=False
)


# =========================
# 10.1 完整数据集统计：训练集 + 测试集
# =========================
y_all_final = np.concatenate([
    y_train_final,
    y_test_final
])

y_all_pred = np.concatenate([
    y_train_pred,
    y_test_pred
])

final_metrics_all = evaluate_final_regression(
    y_all_final,
    y_all_pred,
    "Final_RF_model",
    "all_train_plus_test",
    strict_less=True
)

print("\nFinal_RF_model 完整数据集 Vapor Pressure 预测偏差 1%，5%，10%分别为：")
print(final_metrics_all["within_1pct"])
print(final_metrics_all["within_5pct"])
print(final_metrics_all["within_10pct"])


# =========================
# 11. 保存最终预测结果
# =========================
train_result = final_train_df.copy()

train_result["Vapor_Pressure_true"] = y_train_final
train_result["Predicted_Vapor_Pressure"] = y_train_pred

train_result["Absolute_Error_P"] = final_metrics_train["absolute_error_P"]
train_result["Relative_Error_P (%)"] = final_metrics_train["relative_error_%"]

train_result["lnP_true"] = final_metrics_train["lnP_true"]
train_result["lnP_pred"] = final_metrics_train["lnP_pred"]
train_result["Absolute_Error_lnP"] = final_metrics_train["absolute_error_lnP"]

test_result = final_test_df.copy()

test_result["Vapor_Pressure_true"] = y_test_final
test_result["Predicted_Vapor_Pressure"] = y_test_pred

test_result["Absolute_Error_P"] = final_metrics_test["absolute_error_P"]
test_result["Relative_Error_P (%)"] = final_metrics_test["relative_error_%"]

test_result["lnP_true"] = final_metrics_test["lnP_true"]
test_result["lnP_pred"] = final_metrics_test["lnP_pred"]
test_result["Absolute_Error_lnP"] = final_metrics_test["absolute_error_lnP"]

train_result.to_excel(
    "train_prediction_vs_actual_vp_with_slope_submodels_all_data_with_lnP.xlsx",
    index=False
)

test_result.to_excel(
    "test_prediction_vs_actual_vp_with_slope_submodels_all_data_with_lnP.xlsx",
    index=False
)

print("\n已保存训练集预测结果: train_prediction_vs_actual_vp_with_slope_submodels_all_data_with_lnP.xlsx")
print("已保存测试集预测结果: test_prediction_vs_actual_vp_with_slope_submodels_all_data_with_lnP.xlsx")


# =========================
# 11.1 保存完整数据集预测结果
# =========================
all_result = pd.concat(
    [train_result, test_result],
    axis=0,
    ignore_index=True
)

all_result["Vapor_Pressure_true"] = y_all_final
all_result["Predicted_Vapor_Pressure"] = y_all_pred

all_result["Absolute_Error_P"] = final_metrics_all["absolute_error_P"]
all_result["Relative_Error_P (%)"] = final_metrics_all["relative_error_%"]

all_result["lnP_true"] = final_metrics_all["lnP_true"]
all_result["lnP_pred"] = final_metrics_all["lnP_pred"]
all_result["Absolute_Error_lnP"] = final_metrics_all["absolute_error_lnP"]

all_result.to_excel(
    "all_prediction_vs_actual_vp_with_slope_submodels_all_data_with_lnP.xlsx",
    index=False
)

print("已保存完整数据集预测结果: all_prediction_vs_actual_vp_with_slope_submodels_all_data_with_lnP.xlsx")


# =========================
# 12. 子模型输出表
#     子模型不再有 train/test，只输出 all_data
# =========================
tb_out_all = pd.DataFrame({
    "Split": "all_data",
    "Material_ID": all_arr["ids"],
    "Tb_true": all_arr["Tb"],
    "Tb_pred": Tb_pred_all
})

tc_out_all = pd.DataFrame({
    "Split": "all_data",
    "Material_ID": all_arr["ids"],
    "Tc_half_true": all_arr["Tc_half"],
    "Tc_half_pred": Tc_half_pred_all,
    "Tc_full_pred_approx": Tc_pred_full_all
})

pc_out_all = pd.DataFrame({
    "Split": "all_data",
    "Material_ID": all_arr["ids"],
    "Pc_true_Pa": all_arr["Pc_bar"] * 1e5,
    "Pc_pred_Pa": Pc_pred_all
})


# =========================
# 13. 汇总表
# =========================
summary_rows = [
    make_summary_row(tb_metrics_all),
    make_summary_row(tc_metrics_all),
    make_summary_row(pc_metrics_all),
    make_summary_row(final_metrics_train),
    make_summary_row(final_metrics_test),
    make_summary_row(final_metrics_all)
]

summary_df = pd.DataFrame(summary_rows)


# =========================
# 14. 保存最终 RF 特征重要性
# =========================
feature_importance_df = pd.DataFrame({
    "Feature": X_train_final.columns,
    "Importance": model_final.feature_importances_
}).sort_values(by="Importance", ascending=False)


# =========================
# 15. 总保存
# =========================
output_filename = "VP_pipeline_with_slope_submodels_all_data_final_train_test_split.xlsx"

with pd.ExcelWriter(output_filename, engine="xlsxwriter") as writer:
    summary_df.to_excel(
        writer,
        sheet_name="summary",
        index=False
    )

    slope_df.to_excel(
        writer,
        sheet_name="slope_pred",
        index=False
    )

    tb_out_all.to_excel(
        writer,
        sheet_name="Tb_submodel",
        index=False
    )

    tc_out_all.to_excel(
        writer,
        sheet_name="Tc_half_submodel",
        index=False
    )

    pc_out_all.to_excel(
        writer,
        sheet_name="Pc_submodel",
        index=False
    )

    pd.concat(
        [train_result, test_result],
        ignore_index=True
    ).to_excel(
        writer,
        sheet_name="final_predictions",
        index=False
    )

    all_result.to_excel(
        writer,
        sheet_name="final_all_predictions",
        index=False
    )

    trans_with_slope.to_excel(
        writer,
        sheet_name="transformed_with_slope",
        index=False
    )

    feature_importance_df.to_excel(
        writer,
        sheet_name="feature_importance",
        index=False
    )

print(f"\n全部结果已保存至: {output_filename}")


# =========================
# 16. 输出模型结构记录
# =========================
print("\n当前 Transformed VP + slope + RF 模型结构:")
print("Submodels are trained on all valid materials.")
print("Tb_submodel: HuberRegressor(max_iter=10000), input = PolynomialFeatures(Nk, degree=2)")
print("Tc_half_submodel: GradientBoostingRegressor(n_estimators=300, learning_rate=0.05, max_depth=4, random_state=0), input = PolynomialFeatures(Nk, degree=2)")
print("Pc_submodel: least_squares explicit Pc equation, input = Nk + MW")
print("slope = [ln(Pc_pred) - ln(Pb)] / [Tc_full_pred - Tb_pred]")
print("Final target: ordinary Vapor Pressure, not ln(P)")
print("Final model: RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1)")
print("Final input features: numeric transformed features + slope + Tb_pred + Tc_pred + Pc_pred")
print("Final all-data statistics use strict thresholds: <1%, <5%, <10%")