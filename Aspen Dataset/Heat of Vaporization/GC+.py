# # import numpy as np
# # import pandas as pd
# # from scipy.optimize import least_squares
# # from sklearn.linear_model import HuberRegressor
# # from sklearn.ensemble import RandomForestRegressor
# # from sklearn.metrics import mean_squared_error, r2_score
# # from sklearn.preprocessing import PolynomialFeatures
# # from sklearn.model_selection import train_test_split
# #
# # # ==== 常数与路径 ====
# # HV0, HVB, Tb0 = 9612.7, 15419.9, 222.543
# # T_ref = 298.15
# #
# # main_file = "heat of vaporization 204.xlsx"
# # file_298 = "selected_25_descriptors_data_298.xlsx"
# # file_tb = "selected_25_descriptors_data_boiling_point.xlsx"
# #
# # # ==== 读取数据 ====
# # df_main = pd.read_excel(main_file, sheet_name="Sheet1")
# # df_298 = pd.read_excel(file_298)
# # df_Tb = pd.read_excel(file_tb)
# #
# # id_col = df_main.columns[0]
# #
# # # 行数一致性检查
# # if not (len(df_main) == len(df_298) == len(df_Tb)):
# #     raise ValueError(
# #         f"三个文件行数不一致：main={len(df_main)}, 298={len(df_298)}, Tb={len(df_Tb)}。"
# #         f"如果它们不是严格按同一物质顺序排列，需要改成按 ID merge。"
# #     )
# #
# # # ==== 主文件特征 ====
# # Nk_all = df_main.iloc[:, 13:32].apply(pd.to_numeric, errors="coerce").values   # 19基团
# # Tb_raw_all = pd.to_numeric(df_main.iloc[:, 5], errors="coerce").values
# # MW_all = pd.to_numeric(df_main.iloc[:, 4], errors="coerce").values.reshape(-1, 1)
# # Nc_all = pd.to_numeric(df_main.iloc[:, 10], errors="coerce").values.reshape(-1, 1)
# # T_all = df_main.iloc[:, 32:42].apply(pd.to_numeric, errors="coerce").values
# # Hvap_all = df_main.iloc[:, 42:52].apply(pd.to_numeric, errors="coerce").values
# #
# # # ==== 298K 与 Tb 点数据 ====
# # target_298 = "Heat of vaporization at normal temperature"
# # target_tb = "Heat of vaporization at boiling temperature"
# #
# # X_298_all = df_298.drop(columns=[target_298]).apply(pd.to_numeric, errors="coerce")
# # y_298_all = pd.to_numeric(df_298[target_298], errors="coerce").values
# #
# # X_Tb_all = df_Tb.drop(columns=[target_tb]).apply(pd.to_numeric, errors="coerce")
# # y_Tb_all = pd.to_numeric(df_Tb[target_tb], errors="coerce").values
# #
# # # ==== 构造总有效掩码 ====
# # # 主模型必须要：Tb、Hvap(10点)、Nk、MW、Nc、T 都有效
# # mask_tb = np.isfinite(Tb_raw_all)
# # mask_hvap = np.isfinite(Hvap_all) & (Hvap_all > 0)
# # mask_hvap = mask_hvap.all(axis=1)
# # mask_main_features = (
# #     np.isfinite(Nk_all).all(axis=1)
# #     & np.isfinite(MW_all).flatten()
# #     & np.isfinite(Nc_all).flatten()
# #     & np.isfinite(T_all).all(axis=1)
# # )
# #
# # # 298K 和 Tb 点子模型也必须有效
# # mask_298 = np.isfinite(y_298_all) & np.isfinite(X_298_all).all(axis=1)
# # mask_tbpoint = np.isfinite(y_Tb_all) & np.isfinite(X_Tb_all).all(axis=1)
# #
# # master_mask = mask_tb & mask_hvap & mask_main_features & mask_298 & mask_tbpoint
# #
# # # ==== 应用总有效掩码 ====
# # df_main_valid = df_main.loc[master_mask].copy().reset_index(drop=True)
# # Nk_valid = Nk_all[master_mask]
# # Tb_raw_valid = Tb_raw_all[master_mask]
# # MW_valid = MW_all[master_mask]
# # Nc_valid = Nc_all[master_mask]
# # T_valid_full = T_all[master_mask]
# # Hvap_valid = Hvap_all[master_mask]
# # compound_ids_valid = df_main.loc[master_mask, id_col].values
# #
# # X_298_valid = X_298_all.loc[master_mask].reset_index(drop=True)
# # y_298_valid = y_298_all[master_mask]
# #
# # X_Tb_valid = X_Tb_all.loc[master_mask].reset_index(drop=True)
# # y_Tb_valid = y_Tb_all[master_mask]
# #
# # print("========== 数据清洗后 ==========")
# # print(f"有效物质数: {len(df_main_valid)}")
# #
# # # ==== 按物质 8:2 划分 ====
# # indices = np.arange(len(df_main_valid))
# # train_idx, test_idx = train_test_split(
# #     indices,
# #     test_size=0.2,
# #     random_state=42
# # )
# #
# # print("========== 按物质划分 ==========")
# # print(f"训练集物质数: {len(train_idx)}")
# # print(f"测试集物质数: {len(test_idx)}")
# #
# # # ==== 子集切分 ====
# # Nk_train, Nk_test = Nk_valid[train_idx], Nk_valid[test_idx]
# # Tb_raw_train, Tb_raw_test = Tb_raw_valid[train_idx], Tb_raw_valid[test_idx]
# # MW_train, MW_test = MW_valid[train_idx], MW_valid[test_idx]
# # Nc_train, Nc_test = Nc_valid[train_idx], Nc_valid[test_idx]
# # T_train_raw, T_test_raw = T_valid_full[train_idx], T_valid_full[test_idx]
# # Hvap_train_raw, Hvap_test_raw = Hvap_valid[train_idx], Hvap_valid[test_idx]
# # id_train, id_test = compound_ids_valid[train_idx], compound_ids_valid[test_idx]
# #
# # X_298_train, X_298_test = X_298_valid.iloc[train_idx].copy(), X_298_valid.iloc[test_idx].copy()
# # y_298_train, y_298_test = y_298_valid[train_idx], y_298_valid[test_idx]
# #
# # X_Tb_train, X_Tb_test = X_Tb_valid.iloc[train_idx].copy(), X_Tb_valid.iloc[test_idx].copy()
# # y_Tb_train, y_Tb_test = y_Tb_valid[train_idx], y_Tb_valid[test_idx]
# #
# # # ==== 评估函数 ====
# # def evaluate_scalar(y_true, y_pred, name, split):
# #     y_true = np.asarray(y_true, dtype=float)
# #     y_pred = np.asarray(y_pred, dtype=float)
# #
# #     mask = np.isfinite(y_true) & np.isfinite(y_pred)
# #     y_true = y_true[mask]
# #     y_pred = y_pred[mask]
# #
# #     mse = mean_squared_error(y_true, y_pred)
# #     r2 = r2_score(y_true, y_pred)
# #
# #     nonzero_mask = np.abs(y_true) > 1e-12
# #     rel_err = np.full_like(y_true, np.nan, dtype=float)
# #     if np.any(nonzero_mask):
# #         rel_err[nonzero_mask] = np.abs((y_pred[nonzero_mask] - y_true[nonzero_mask]) / y_true[nonzero_mask]) * 100
# #         ard = np.nanmean(rel_err)
# #         within_1pct = np.sum(rel_err <= 1)
# #         within_5pct = np.sum(rel_err <= 5)
# #         within_10pct = np.sum(rel_err <= 10)
# #     else:
# #         ard = np.nan
# #         within_1pct = within_5pct = within_10pct = 0
# #
# #     print(f"\n{name} - {split}")
# #     print(f"R²  = {r2:.6f}")
# #     print(f"MSE = {mse:.6f}")
# #     print(f"ARD = {ard:.2f}%")
# #     print(f"误差 ≤ 1% 的点数: {within_1pct}")
# #     print(f"误差 ≤ 5% 的点数: {within_5pct}")
# #     print(f"误差 ≤ 10% 的点数: {within_10pct}")
# #
# #     return {
# #         "Model": name,
# #         "Split": split,
# #         "R2": r2,
# #         "MSE": mse,
# #         "ARD_%": ard,
# #         "within_1pct": within_1pct,
# #         "within_5pct": within_5pct,
# #         "within_10pct": within_10pct
# #     }
# #
# # # ==== Nk 多项式特征（只在训练集 fit）====
# # poly = PolynomialFeatures(degree=2, include_bias=False)
# # Nk_poly_train = poly.fit_transform(Nk_train)
# # Nk_poly_test = poly.transform(Nk_test)
# #
# # # ==== Tb 模型 ====
# # model_Tb = HuberRegressor(max_iter=10000)
# # model_Tb.fit(Nk_poly_train, np.exp(Tb_raw_train / Tb0))
# #
# # Tb_pred_train = Tb0 * np.log(np.clip(model_Tb.predict(Nk_poly_train), 1e-6, None))
# # Tb_pred_test = Tb0 * np.log(np.clip(model_Tb.predict(Nk_poly_test), 1e-6, None))
# #
# # tb_metrics_train = evaluate_scalar(Tb_raw_train, Tb_pred_train, "Tb_submodel", "train")
# # tb_metrics_test = evaluate_scalar(Tb_raw_test, Tb_pred_test, "Tb_submodel", "test")
# #
# # # ==== HVap_298 子模型 ====
# # rf_298 = RandomForestRegressor(
# #     n_estimators=300,
# #     random_state=42,
# #     n_jobs=-1
# # )
# # rf_298.fit(X_298_train, y_298_train)
# #
# # HVap_298_pred_train = rf_298.predict(X_298_train)
# # HVap_298_pred_test = rf_298.predict(X_298_test)
# #
# # hv298_metrics_train = evaluate_scalar(y_298_train, HVap_298_pred_train, "HVap_298_submodel", "train")
# # hv298_metrics_test = evaluate_scalar(y_298_test, HVap_298_pred_test, "HVap_298_submodel", "test")
# #
# # # ==== HVap_Tb 子模型 ====
# # rf_Tb = RandomForestRegressor(
# #     n_estimators=300,
# #     random_state=42,
# #     n_jobs=-1
# # )
# # rf_Tb.fit(X_Tb_train, y_Tb_train)
# #
# # HVap_Tb_pred_train = rf_Tb.predict(X_Tb_train)
# # HVap_Tb_pred_test = rf_Tb.predict(X_Tb_test)
# #
# # hvtb_metrics_train = evaluate_scalar(y_Tb_train, HVap_Tb_pred_train, "HVap_Tb_submodel", "train")
# # hvtb_metrics_test = evaluate_scalar(y_Tb_test, HVap_Tb_pred_test, "HVap_Tb_submodel", "test")
# #
# # # ==== slope 特征 ====
# # def build_slope(hvap_tb_pred, hvap_298_pred, tb_pred):
# #     denom = tb_pred - T_ref
# #     slope = np.full_like(tb_pred, np.nan, dtype=float)
# #
# #     valid = np.isfinite(hvap_tb_pred) & np.isfinite(hvap_298_pred) & np.isfinite(tb_pred) & (np.abs(denom) > 1e-12)
# #     slope[valid] = (hvap_tb_pred[valid] - hvap_298_pred[valid]) / denom[valid]
# #     return slope.reshape(-1, 1)
# #
# # slope_train = build_slope(HVap_Tb_pred_train, HVap_298_pred_train, Tb_pred_train)
# # slope_test = build_slope(HVap_Tb_pred_test, HVap_298_pred_test, Tb_pred_test)
# #
# # # ==== 构造主模型点级数据 ====
# # def build_point_dataset(Nk, MW, Nc, T, Hvap, slope, compound_ids):
# #     X = np.hstack([
# #         Nk.repeat(10, axis=0),
# #         MW.repeat(10, axis=0),
# #         Nc.repeat(10, axis=0),
# #         T.flatten().reshape(-1, 1),
# #         slope.repeat(10, axis=0)
# #     ])
# #     y = Hvap.flatten()
# #     expanded_ids = np.repeat(compound_ids, 10)
# #     expanded_T = T.flatten()
# #
# #     mask = np.isfinite(y) & np.isfinite(X).all(axis=1)
# #
# #     return (
# #         X[mask],
# #         y[mask],
# #         expanded_ids[mask],
# #         expanded_T[mask]
# #     )
# #
# # X_train, y_train, id_point_train, T_used_train = build_point_dataset(
# #     Nk_train, MW_train, Nc_train, T_train_raw, Hvap_train_raw, slope_train, id_train
# # )
# #
# # X_test, y_test, id_point_test, T_used_test = build_point_dataset(
# #     Nk_test, MW_test, Nc_test, T_test_raw, Hvap_test_raw, slope_test, id_test
# # )
# #
# # print("\n========== 主模型点级数据 ==========")
# # print(f"训练集样本点数: {len(y_train)}")
# # print(f"测试集样本点数: {len(y_test)}")
# #
# # # ==== 主模型预测函数 ====
# # def predict_hvap(params, X):
# #     Nk = X[:, :19]
# #     MW = X[:, 19].reshape(-1, 1)
# #     Nc = X[:, 20].reshape(-1, 1)
# #     T = np.clip(X[:, 21].reshape(-1, 1), 1e-6, None)
# #     slope = X[:, 22].reshape(-1, 1)
# #
# #     B1k = params[0:19]
# #     B2k = params[19:38]
# #     C1k = params[38:57]
# #     C2k = params[57:76]
# #     D1k = params[76:95]
# #     D2k = params[95:114]
# #     beta, gamma, delta = params[114:117]
# #     f0, f1 = params[117:119]
# #     gamma_slope = params[119]
# #     intercept = params[120]
# #
# #     R = 8.3144
# #
# #     Bi = np.sum(Nk * (B1k + MW * B2k), axis=1, keepdims=True) + beta * (f0 + Nc * f1)
# #     Ci = np.sum(Nk * (C1k + MW * C2k), axis=1, keepdims=True) + gamma * (f0 + Nc * f1)
# #     Di = np.sum(Nk * (D1k + MW * D2k), axis=1, keepdims=True) + delta * (f0 + Nc * f1)
# #
# #     y_pred = -R * ((1.5 * Bi) / np.sqrt(T) + Ci * T + Di * T**2) + gamma_slope * slope * T + intercept
# #     return y_pred.flatten()
# #
# # def residuals(params, X, y):
# #     return predict_hvap(params, X) - y
# #
# # # ==== 主模型拟合 ====
# # params_init = np.zeros(121)
# #
# # print("\n🚀 主模型拟合中，请稍候...")
# # result = least_squares(
# #     residuals,
# #     x0=params_init,
# #     args=(X_train, y_train),
# #     max_nfev=10000
# # )
# #
# # # ==== 主模型评估 ====
# # def evaluate_main(X, y, ids, temps, split_name, params):
# #     y_pred = predict_hvap(params, X)
# #
# #     mse = mean_squared_error(y, y_pred)
# #     r2 = r2_score(y, y_pred)
# #     ard = np.mean(np.abs((y_pred - y) / y)) * 100
# #
# #     relative_error = np.abs((y_pred - y) / y) * 100
# #     within_1pct = np.sum(relative_error <= 1)
# #     within_5pct = np.sum(relative_error <= 5)
# #     within_10pct = np.sum(relative_error <= 10)
# #
# #     print(f"\n主模型 - {split_name}")
# #     print(f"R²  = {r2:.6f}")
# #     print(f"MSE = {mse:.6f}")
# #     print(f"ARD = {ard:.2f}%")
# #     print(f"相对误差 ≤ 1% 的点数: {within_1pct}")
# #     print(f"相对误差 ≤ 5% 的点数: {within_5pct}")
# #     print(f"相对误差 ≤ 10% 的点数: {within_10pct}")
# #
# #     result_df = pd.DataFrame({
# #         "Split": split_name,
# #         "Compound_ID": ids,
# #         "Temperature (K)": temps,
# #         "Hvap_true (J/mol)": y,
# #         "Hvap_pred (J/mol)": y_pred,
# #         "Absolute Error": np.abs(y - y_pred),
# #         "Relative Error (%)": relative_error
# #     })
# #
# #     summary = {
# #         "Model": "Hvap_main_model_with_slope",
# #         "Split": split_name,
# #         "R2": r2,
# #         "MSE": mse,
# #         "ARD_%": ard,
# #         "within_1pct": within_1pct,
# #         "within_5pct": within_5pct,
# #         "within_10pct": within_10pct
# #     }
# #
# #     return result_df, summary
# #
# # train_result_df, train_summary = evaluate_main(
# #     X_train, y_train, id_point_train, T_used_train, "train", result.x
# # )
# #
# # test_result_df, test_summary = evaluate_main(
# #     X_test, y_test, id_point_test, T_used_test, "test", result.x
# # )
# #
# # # ==== 参数输出 ====
# # param_names = (
# #     [f"B1_{i}" for i in range(19)] + [f"B2_{i}" for i in range(19)] +
# #     [f"C1_{i}" for i in range(19)] + [f"C2_{i}" for i in range(19)] +
# #     [f"D1_{i}" for i in range(19)] + [f"D2_{i}" for i in range(19)] +
# #     ["beta", "gamma", "delta", "f0", "f1", "gamma_slope", "intercept"]
# # )
# #
# # print("\n🔧 参数拟合结果:")
# # for name, val in zip(param_names, result.x):
# #     print(f"{name:14s}: {val:.6f}")
# #
# # # ==== 保存子模型结果 ====
# # tb_pred_df = pd.DataFrame({
# #     "Split": ["train"] * len(id_train) + ["test"] * len(id_test),
# #     "Compound_ID": np.concatenate([id_train, id_test]),
# #     "Tb_true": np.concatenate([Tb_raw_train, Tb_raw_test]),
# #     "Tb_pred": np.concatenate([Tb_pred_train, Tb_pred_test])
# # })
# #
# # hv298_pred_df = pd.DataFrame({
# #     "Split": ["train"] * len(id_train) + ["test"] * len(id_test),
# #     "Compound_ID": np.concatenate([id_train, id_test]),
# #     "HVap_298_true": np.concatenate([y_298_train, y_298_test]),
# #     "HVap_298_pred": np.concatenate([HVap_298_pred_train, HVap_298_pred_test])
# # })
# #
# # hvtb_pred_df = pd.DataFrame({
# #     "Split": ["train"] * len(id_train) + ["test"] * len(id_test),
# #     "Compound_ID": np.concatenate([id_train, id_test]),
# #     "HVap_Tb_true": np.concatenate([y_Tb_train, y_Tb_test]),
# #     "HVap_Tb_pred": np.concatenate([HVap_Tb_pred_train, HVap_Tb_pred_test])
# # })
# #
# # slope_df = pd.DataFrame({
# #     "Split": ["train"] * len(id_train) + ["test"] * len(id_test),
# #     "Compound_ID": np.concatenate([id_train, id_test]),
# #     "slope": np.concatenate([slope_train.flatten(), slope_test.flatten()])
# # })
# #
# # summary_df = pd.DataFrame([
# #     tb_metrics_train, tb_metrics_test,
# #     hv298_metrics_train, hv298_metrics_test,
# #     hvtb_metrics_train, hvtb_metrics_test,
# #     train_summary, test_summary
# # ])
# #
# # all_result_df = pd.concat([train_result_df, test_result_df], ignore_index=True)
# #
# # output_filename = "Hvap_prediction_with_slopeT_and_intercept_train_test_split.xlsx"
# # with pd.ExcelWriter(output_filename, engine="xlsxwriter") as writer:
# #     all_result_df.to_excel(writer, sheet_name="predictions", index=False)
# #     summary_df.to_excel(writer, sheet_name="summary", index=False)
# #     tb_pred_df.to_excel(writer, sheet_name="Tb_submodel", index=False)
# #     hv298_pred_df.to_excel(writer, sheet_name="HVap_298_submodel", index=False)
# #     hvtb_pred_df.to_excel(writer, sheet_name="HVap_Tb_submodel", index=False)
# #     slope_df.to_excel(writer, sheet_name="slope", index=False)
# #
# # print(f"\n✅ 预测结果已保存为 {output_filename}")
# # import pandas as pd
# # import numpy as np
# # from sklearn.linear_model import HuberRegressor
# # from sklearn.ensemble import RandomForestRegressor
# # from sklearn.metrics import mean_squared_error, r2_score
# # from sklearn.preprocessing import PolynomialFeatures
# # from sklearn.model_selection import train_test_split
# # from scipy.optimize import least_squares
# #
# # # ==== 常数与路径 ====
# # HV0, HVB, Tb0 = 9612.7, 15419.9, 222.543
# # T_ref = 298.15
# #
# # # ==== 通用评估函数 ====
# # def evaluate_metrics(y_true, y_pred, name="模型"):
# #     y_true = np.array(y_true, dtype=float).flatten()
# #     y_pred = np.array(y_pred, dtype=float).flatten()
# #
# #     mse = mean_squared_error(y_true, y_pred)
# #     r2 = r2_score(y_true, y_pred)
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
# #     print(f"\n📊 {name}评估结果:")
# #     print(f"R²  = {r2:.6f}")
# #     print(f"MSE = {mse:.6f}")
# #     print(f"ARD = {ard:.2f}%")
# #     print(f"✅ 相对误差 ≤ 1% 的点数: {within_1pct}")
# #     print(f"✅ 相对误差 ≤ 5% 的点数: {within_5pct}")
# #     print(f"✅ 相对误差 ≤ 10% 的点数: {within_10pct}")
# #
# #     return {
# #         "Model": name,
# #         "R2": r2,
# #         "MSE": mse,
# #         "ARD_%": ard,
# #         "within_1pct": within_1pct,
# #         "within_5pct": within_5pct,
# #         "within_10pct": within_10pct,
# #         "relative_error": relative_error
# #     }
# #
# # # ==== 读取数据 ====
# # df_main = pd.read_excel("heat of vaporization 204.xlsx", sheet_name="Sheet1")
# # Nk_all = df_main.iloc[:, 13:32].apply(pd.to_numeric, errors='coerce')  # 19基团
# # poly = PolynomialFeatures(degree=2, include_bias=False)
# # Nk_poly = poly.fit_transform(Nk_all)
# #
# # # ==== Tb 模型 ====
# # Tb_raw = df_main.iloc[:, 5].values
# # mask_tb = ~np.isnan(Tb_raw)
# # Nk_valid = Nk_all[mask_tb]
# # Nk_poly_valid = poly.transform(Nk_valid)
# #
# # model_Tb = HuberRegressor(max_iter=10000).fit(
# #     Nk_poly_valid,
# #     np.exp(Tb_raw[mask_tb] / Tb0)
# # )
# #
# # Tb_pred_exp = model_Tb.predict(Nk_poly_valid)
# # Tb_pred_all = Tb0 * np.log(np.clip(Tb_pred_exp, 1e-6, None))
# #
# # # ==== 子模型1：Tb 预测效果 ====
# # tb_metrics = evaluate_metrics(
# #     Tb_raw[mask_tb],
# #     Tb_pred_all,
# #     "Tb 子模型"
# # )
# #
# # # ==== 预测 HVap_298 和 HVap_Tb ====
# # df_298 = pd.read_excel("selected_25_descriptors_data_298.xlsx")
# # target_298 = "Heat of vaporization at normal temperature"
# # X_298 = df_298.drop(columns=[target_298])
# #
# # rf_298 = RandomForestRegressor(random_state=42).fit(
# #     X_298,
# #     df_298[target_298]
# # )
# # HVap_298_all = rf_298.predict(X_298)
# #
# # # ==== 子模型2：HVap_298 预测效果 ====
# # hv298_metrics = evaluate_metrics(
# #     df_298[target_298].values,
# #     HVap_298_all,
# #     "HVap_298 子模型"
# # )
# #
# # df_Tb = pd.read_excel("selected_25_descriptors_data_boiling_point.xlsx")
# # target_Tb = "Heat of vaporization at boiling temperature"
# # X_Tb = df_Tb.drop(columns=[target_Tb])
# #
# # rf_Tb = RandomForestRegressor(random_state=42).fit(
# #     X_Tb,
# #     df_Tb[target_Tb]
# # )
# # HVap_Tb_all = rf_Tb.predict(X_Tb)
# #
# # # ==== 子模型3：HVap_Tb 预测效果 ====
# # hvTb_metrics = evaluate_metrics(
# #     df_Tb[target_Tb].values,
# #     HVap_Tb_all,
# #     "HVap_Tb 子模型"
# # )
# #
# # # 如果长度与 mask_tb 后的数据一致，则直接使用
# # # 如果原始长度与 df_main 一致，则取 mask_tb 对应部分
# # if len(HVap_298_all) == len(df_main):
# #     HVap_298_used = HVap_298_all[mask_tb]
# # else:
# #     HVap_298_used = HVap_298_all
# #
# # if len(HVap_Tb_all) == len(df_main):
# #     HVap_Tb_used = HVap_Tb_all[mask_tb]
# # else:
# #     HVap_Tb_used = HVap_Tb_all
# #
# # # ==== slope × T 特征 ====
# # slope_pred = ((HVap_Tb_used - HVap_298_used) / (Tb_pred_all - T_ref)).reshape(-1, 1)
# #
# # # ==== 多温度点 ΔHvap ====
# # T = df_main.iloc[:, 32:42].values[mask_tb]
# # Hvap = df_main.iloc[:, 42:52].values[mask_tb]
# # MW = df_main.iloc[:, 4].values[mask_tb].reshape(-1, 1)
# # Nc = df_main.iloc[:, 10].values[mask_tb].reshape(-1, 1)
# # compound_ids_all = df_main.iloc[:, 0].values[mask_tb]
# #
# # # ==== 清洗有效样本 ====
# # valid_row_mask = np.isfinite(Hvap).all(axis=1)
# # Nk_valid = Nk_valid[valid_row_mask].values
# # MW = MW[valid_row_mask]
# # Nc = Nc[valid_row_mask]
# # T = T[valid_row_mask]
# # Hvap = Hvap[valid_row_mask]
# # slope_pred = slope_pred[valid_row_mask]
# # compound_ids_all = compound_ids_all[valid_row_mask]
# #
# # # ==== 构造训练数据 ====
# # X = np.hstack([
# #     Nk_valid.repeat(10, axis=0),
# #     MW.repeat(10, axis=0),
# #     Nc.repeat(10, axis=0),
# #     T.flatten().reshape(-1, 1),
# #     slope_pred.repeat(10, axis=0)
# # ])
# # y = Hvap.flatten()
# #
# # # 记录样本对应信息
# # compound_ids = np.repeat(compound_ids_all, 10)
# # T_valid = T.flatten()
# #
# # # ==== 清除非法值 ====
# # mask = np.isfinite(y) & np.isfinite(X).all(axis=1)
# # X = X[mask]
# # y = y[mask]
# # T_valid = T_valid[mask]
# # compound_ids = compound_ids[mask]
# #
# # print("\n========== 最终主模型样本划分 ==========")
# # print(f"总样本点数: {len(X)}")
# #
# # # ==== 8:2 划分（只对最终主模型） ====
# # X_train, X_test, y_train, y_test, T_train, T_test, id_train, id_test = train_test_split(
# #     X, y, T_valid, compound_ids,
# #     test_size=0.2,
# #     random_state=42
# # )
# #
# # print(f"训练集样本点数: {len(X_train)}")
# # print(f"测试集样本点数: {len(X_test)}")
# #
# # # ==== 前向预测函数 ====
# # def model_predict(params, X):
# #     Nk = X[:, :19]
# #     MW = X[:, 19].reshape(-1, 1)
# #     Nc = X[:, 20].reshape(-1, 1)
# #     T = np.clip(X[:, 21].reshape(-1, 1), 1e-6, None)
# #     slope = X[:, 22].reshape(-1, 1)
# #
# #     B1k = params[0:19]
# #     B2k = params[19:38]
# #     C1k = params[38:57]
# #     C2k = params[57:76]
# #     D1k = params[76:95]
# #     D2k = params[95:114]
# #     beta, gamma, delta = params[114:117]
# #     f0, f1 = params[117:119]
# #     gamma_slope = params[119]
# #     intercept = params[120]
# #
# #     R = 8.3144
# #     Bi = np.sum(Nk * (B1k + MW * B2k), axis=1, keepdims=True) + beta * (f0 + Nc * f1)
# #     Ci = np.sum(Nk * (C1k + MW * C2k), axis=1, keepdims=True) + gamma * (f0 + Nc * f1)
# #     Di = np.sum(Nk * (D1k + MW * D2k), axis=1, keepdims=True) + delta * (f0 + Nc * f1)
# #
# #     y_pred = -R * ((1.5 * Bi) / np.sqrt(T) + Ci * T + Di * T**2) + gamma_slope * slope * T + intercept
# #     return y_pred.flatten()
# #
# # # ==== 拟合函数 ====
# # def residuals(params, X, y):
# #     return model_predict(params, X) - y
# #
# # # ==== 模型拟合（只在训练集上） ====
# # params_init = np.zeros(121)
# # result = least_squares(
# #     residuals,
# #     x0=params_init,
# #     args=(X_train, y_train),
# #     max_nfev=10000
# # )
# #
# # # ==== 训练集 / 测试集预测 ====
# # y_train_pred = model_predict(result.x, X_train)
# # y_test_pred = model_predict(result.x, X_test)
# #
# # # ==== 主模型评估 ====
# # train_metrics = evaluate_metrics(y_train, y_train_pred, "最终主模型 - 训练集")
# # test_metrics = evaluate_metrics(y_test, y_test_pred, "最终主模型 - 测试集")
# #
# # # ==== 输出参数 ====
# # param_names = (
# #     [f"B1_{i}" for i in range(19)] + [f"B2_{i}" for i in range(19)] +
# #     [f"C1_{i}" for i in range(19)] + [f"C2_{i}" for i in range(19)] +
# #     [f"D1_{i}" for i in range(19)] + [f"D2_{i}" for i in range(19)] +
# #     ["beta", "gamma", "delta", "f0", "f1", "gamma_slope", "intercept"]
# # )
# #
# # print("\n🔧 参数拟合结果:")
# # for name, val in zip(param_names, result.x):
# #     print(f"{name:14s}: {val:.6f}")
# #
# # # ==== 保存训练集结果 ====
# # df_train_result = pd.DataFrame({
# #     "Set": "train",
# #     "Compound_ID": id_train,
# #     "Temperature (K)": T_train,
# #     "Hvap_true (J/mol)": y_train,
# #     "Hvap_pred (J/mol)": y_train_pred,
# #     "Absolute Error": np.abs(y_train - y_train_pred),
# #     "Relative Error (%)": train_metrics["relative_error"]
# # })
# #
# # # ==== 保存测试集结果 ====
# # df_test_result = pd.DataFrame({
# #     "Set": "test",
# #     "Compound_ID": id_test,
# #     "Temperature (K)": T_test,
# #     "Hvap_true (J/mol)": y_test,
# #     "Hvap_pred (J/mol)": y_test_pred,
# #     "Absolute Error": np.abs(y_test - y_test_pred),
# #     "Relative Error (%)": test_metrics["relative_error"]
# # })
# #
# # # ==== 合并保存最终模型结果 ====
# # df_result = pd.concat([df_train_result, df_test_result], axis=0).reset_index(drop=True)
# # df_result.to_excel("Hvap_prediction_with_slopeT_and_intercept_19group_8to2.xlsx", index=False)
# #
# # # ==== 保存主模型汇总 ====
# # summary_df = pd.DataFrame([
# #     ["final_main_model", "train", train_metrics["R2"], train_metrics["MSE"], train_metrics["ARD_%"],
# #      train_metrics["within_1pct"], train_metrics["within_5pct"], train_metrics["within_10pct"]],
# #     ["final_main_model", "test", test_metrics["R2"], test_metrics["MSE"], test_metrics["ARD_%"],
# #      test_metrics["within_1pct"], test_metrics["within_5pct"], test_metrics["within_10pct"]],
# # ], columns=[
# #     "Model", "Dataset", "R2", "MSE", "ARD_%", "within_1pct", "within_5pct", "within_10pct"
# # ])
# # summary_df.to_excel("Hvap_prediction_summary_8to2.xlsx", index=False)
# #
# # # ==== 保存子模型汇总 ====
# # submodel_summary_df = pd.DataFrame([
# #     [tb_metrics["Model"], tb_metrics["R2"], tb_metrics["MSE"], tb_metrics["ARD_%"],
# #      tb_metrics["within_1pct"], tb_metrics["within_5pct"], tb_metrics["within_10pct"]],
# #     [hv298_metrics["Model"], hv298_metrics["R2"], hv298_metrics["MSE"], hv298_metrics["ARD_%"],
# #      hv298_metrics["within_1pct"], hv298_metrics["within_5pct"], hv298_metrics["within_10pct"]],
# #     [hvTb_metrics["Model"], hvTb_metrics["R2"], hvTb_metrics["MSE"], hvTb_metrics["ARD_%"],
# #      hvTb_metrics["within_1pct"], hvTb_metrics["within_5pct"], hvTb_metrics["within_10pct"]],
# # ], columns=[
# #     "Model", "R2", "MSE", "ARD_%", "within_1pct", "within_5pct", "within_10pct"
# # ])
# # submodel_summary_df.to_excel("Hvap_submodel_summary.xlsx", index=False)
# #
# # print("\n✅ 预测结果已保存为 Hvap_prediction_with_slopeT_and_intercept_19group_8to2.xlsx")
# # print("✅ 主模型汇总已保存为 Hvap_prediction_summary_8to2.xlsx")
# # print("✅ 子模型汇总已保存为 Hvap_submodel_summary.xlsx")
#
# import pandas as pd
# import numpy as np
# from sklearn.linear_model import HuberRegressor
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.preprocessing import PolynomialFeatures
# from sklearn.model_selection import train_test_split
# from scipy.optimize import least_squares
#
# # ==== 常数与路径 ====
# HV0, HVB, Tb0 = 9612.7, 15419.9, 222.543
# T_ref = 298.15
#
# # ==== 通用评估函数 ====
# def evaluate_metrics(y_true, y_pred, name="模型"):
#     y_true = np.array(y_true, dtype=float).flatten()
#     y_pred = np.array(y_pred, dtype=float).flatten()
#
#     mse = mean_squared_error(y_true, y_pred)
#     r2 = r2_score(y_true, y_pred)
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
#     print(f"\n📊 {name}评估结果:")
#     print(f"R²  = {r2:.6f}")
#     print(f"MSE = {mse:.6f}")
#     print(f"ARD = {ard:.2f}%")
#     print(f"✅ 相对误差 ≤ 1% 的点数: {within_1pct}")
#     print(f"✅ 相对误差 ≤ 5% 的点数: {within_5pct}")
#     print(f"✅ 相对误差 ≤ 10% 的点数: {within_10pct}")
#
#     return {
#         "Model": name,
#         "R2": r2,
#         "MSE": mse,
#         "ARD_%": ard,
#         "within_1pct": within_1pct,
#         "within_5pct": within_5pct,
#         "within_10pct": within_10pct,
#         "relative_error": relative_error
#     }
#
# # ==== 读取数据 ====
# df_main = pd.read_excel("heat of vaporization 204.xlsx", sheet_name="Sheet1")
# Nk_all = df_main.iloc[:, 13:32].apply(pd.to_numeric, errors='coerce')  # 19基团
# poly = PolynomialFeatures(degree=2, include_bias=False)
# Nk_poly = poly.fit_transform(Nk_all)
#
# # ==== Tb 模型 ====
# Tb_raw = df_main.iloc[:, 5].values
# mask_tb = ~np.isnan(Tb_raw)
# Nk_valid_for_tb = Nk_all[mask_tb]
# Nk_poly_valid = poly.transform(Nk_valid_for_tb)
#
# model_Tb = HuberRegressor(max_iter=10000).fit(
#     Nk_poly_valid,
#     np.exp(Tb_raw[mask_tb] / Tb0)
# )
#
# Tb_pred_exp = model_Tb.predict(Nk_poly_valid)
# Tb_pred_all = Tb0 * np.log(np.clip(Tb_pred_exp, 1e-6, None))
#
# # ==== 子模型1：Tb 预测效果 ====
# tb_metrics = evaluate_metrics(
#     Tb_raw[mask_tb],
#     Tb_pred_all,
#     "Tb 子模型"
# )
#
# # ==== 预测 HVap_298 和 HVap_Tb ====
# df_298 = pd.read_excel("selected_25_descriptors_data_298.xlsx")
# target_298 = "Heat of vaporization at normal temperature"
# X_298 = df_298.drop(columns=[target_298])
#
# rf_298 = RandomForestRegressor(random_state=42).fit(
#     X_298,
#     df_298[target_298]
# )
# HVap_298_all = rf_298.predict(X_298)
#
# # ==== 子模型2：HVap_298 预测效果 ====
# hv298_metrics = evaluate_metrics(
#     df_298[target_298].values,
#     HVap_298_all,
#     "HVap_298 子模型"
# )
#
# df_Tb = pd.read_excel("selected_25_descriptors_data_boiling_point.xlsx")
# target_Tb = "Heat of vaporization at boiling temperature"
# X_Tb = df_Tb.drop(columns=[target_Tb])
#
# rf_Tb = RandomForestRegressor(random_state=42).fit(
#     X_Tb,
#     df_Tb[target_Tb]
# )
# HVap_Tb_all = rf_Tb.predict(X_Tb)
#
# # ==== 子模型3：HVap_Tb 预测效果 ====
# hvTb_metrics = evaluate_metrics(
#     df_Tb[target_Tb].values,
#     HVap_Tb_all,
#     "HVap_Tb 子模型"
# )
#
# # 如果长度与 mask_tb 后的数据一致，则直接使用
# # 如果原始长度与 df_main 一致，则取 mask_tb 对应部分
# if len(HVap_298_all) == len(df_main):
#     HVap_298_used = HVap_298_all[mask_tb]
# else:
#     HVap_298_used = HVap_298_all
#
# if len(HVap_Tb_all) == len(df_main):
#     HVap_Tb_used = HVap_Tb_all[mask_tb]
# else:
#     HVap_Tb_used = HVap_Tb_all
#
# # ==== slope × T 特征 ====
# slope_pred = ((HVap_Tb_used - HVap_298_used) / (Tb_pred_all - T_ref)).reshape(-1, 1)
#
# # ==== 多温度点 ΔHvap ====
# T = df_main.iloc[:, 32:42].values[mask_tb]
# Hvap = df_main.iloc[:, 42:52].values[mask_tb]
# MW = df_main.iloc[:, 4].values[mask_tb].reshape(-1, 1)
# Nc = df_main.iloc[:, 10].values[mask_tb].reshape(-1, 1)
# compound_ids_all = df_main.iloc[:, 0].values[mask_tb]
#
# # ==== 清洗有效样本（物质级）====
# valid_row_mask = np.isfinite(Hvap).all(axis=1)
# Nk_valid = Nk_valid_for_tb[valid_row_mask].values
# MW = MW[valid_row_mask]
# Nc = Nc[valid_row_mask]
# T = T[valid_row_mask]
# Hvap = Hvap[valid_row_mask]
# slope_pred = slope_pred[valid_row_mask]
# compound_ids_all = compound_ids_all[valid_row_mask]
#
# print("\n========== 按物质划分最终主模型 ==========")
# print(f"有效物质数: {len(compound_ids_all)}")
#
# # ==== 只对最终主模型按物质 8:2 划分 ====
# material_indices = np.arange(len(compound_ids_all))
# train_idx, test_idx = train_test_split(
#     material_indices,
#     test_size=0.2,
#     random_state=42
# )
#
# # 训练集物质级数据
# Nk_train, Nk_test = Nk_valid[train_idx], Nk_valid[test_idx]
# MW_train, MW_test = MW[train_idx], MW[test_idx]
# Nc_train, Nc_test = Nc[train_idx], Nc[test_idx]
# T_train_raw, T_test_raw = T[train_idx], T[test_idx]
# Hvap_train_raw, Hvap_test_raw = Hvap[train_idx], Hvap[test_idx]
# slope_train, slope_test = slope_pred[train_idx], slope_pred[test_idx]
# id_train_raw, id_test_raw = compound_ids_all[train_idx], compound_ids_all[test_idx]
#
# print(f"训练集物质数: {len(train_idx)}")
# print(f"测试集物质数: {len(test_idx)}")
#
# # ==== 把每个物质展开成10个温度点样本 ====
# def build_point_dataset(Nk, MW, Nc, T, Hvap, slope_pred, compound_ids):
#     X = np.hstack([
#         Nk.repeat(10, axis=0),
#         MW.repeat(10, axis=0),
#         Nc.repeat(10, axis=0),
#         T.flatten().reshape(-1, 1),
#         slope_pred.repeat(10, axis=0)
#     ])
#     y = Hvap.flatten()
#
#     expanded_ids = np.repeat(compound_ids, 10)
#     expanded_T = T.flatten()
#
#     mask = np.isfinite(y) & np.isfinite(X).all(axis=1)
#
#     return (
#         X[mask],
#         y[mask],
#         expanded_ids[mask],
#         expanded_T[mask]
#     )
#
# X_train, y_train, id_train, T_train = build_point_dataset(
#     Nk_train, MW_train, Nc_train, T_train_raw, Hvap_train_raw, slope_train, id_train_raw
# )
#
# X_test, y_test, id_test, T_test = build_point_dataset(
#     Nk_test, MW_test, Nc_test, T_test_raw, Hvap_test_raw, slope_test, id_test_raw
# )
#
# print(f"训练集样本点数: {len(X_train)}")
# print(f"测试集样本点数: {len(X_test)}")
#
# # ==== 前向预测函数 ====
# def model_predict(params, X):
#     Nk = X[:, :19]
#     MW = X[:, 19].reshape(-1, 1)
#     Nc = X[:, 20].reshape(-1, 1)
#     T = np.clip(X[:, 21].reshape(-1, 1), 1e-6, None)
#     slope = X[:, 22].reshape(-1, 1)
#
#     B1k = params[0:19]
#     B2k = params[19:38]
#     C1k = params[38:57]
#     C2k = params[57:76]
#     D1k = params[76:95]
#     D2k = params[95:114]
#     beta, gamma, delta = params[114:117]
#     f0, f1 = params[117:119]
#     gamma_slope = params[119]
#     intercept = params[120]
#
#     R = 8.3144
#     Bi = np.sum(Nk * (B1k + MW * B2k), axis=1, keepdims=True) + beta * (f0 + Nc * f1)
#     Ci = np.sum(Nk * (C1k + MW * C2k), axis=1, keepdims=True) + gamma * (f0 + Nc * f1)
#     Di = np.sum(Nk * (D1k + MW * D2k), axis=1, keepdims=True) + delta * (f0 + Nc * f1)
#
#     y_pred = -R * ((1.5 * Bi) / np.sqrt(T) + Ci * T + Di * T**2) + gamma_slope * slope * T + intercept
#     return y_pred.flatten()
#
# # ==== 拟合函数 ====
# def residuals(params, X, y):
#     return model_predict(params, X) - y
#
# # ==== 模型拟合（只在训练集上）====
# params_init = np.zeros(121)
# result = least_squares(
#     residuals,
#     x0=params_init,
#     args=(X_train, y_train),
#     max_nfev=10000
# )
#
# # ==== 训练集 / 测试集预测 ====
# y_train_pred = model_predict(result.x, X_train)
# y_test_pred = model_predict(result.x, X_test)
#
# # ==== 主模型评估 ====
# train_metrics = evaluate_metrics(y_train, y_train_pred, "最终主模型 - 训练集")
# test_metrics = evaluate_metrics(y_test, y_test_pred, "最终主模型 - 测试集")
#
# # ==== 输出参数 ====
# param_names = (
#     [f"B1_{i}" for i in range(19)] + [f"B2_{i}" for i in range(19)] +
#     [f"C1_{i}" for i in range(19)] + [f"C2_{i}" for i in range(19)] +
#     [f"D1_{i}" for i in range(19)] + [f"D2_{i}" for i in range(19)] +
#     ["beta", "gamma", "delta", "f0", "f1", "gamma_slope", "intercept"]
# )
#
# print("\n🔧 参数拟合结果:")
# for name, val in zip(param_names, result.x):
#     print(f"{name:14s}: {val:.6f}")
#
# # ==== 保存训练集结果 ====
# df_train_result = pd.DataFrame({
#     "Set": "train",
#     "Compound_ID": id_train,
#     "Temperature (K)": T_train,
#     "Hvap_true (J/mol)": y_train,
#     "Hvap_pred (J/mol)": y_train_pred,
#     "Absolute Error": np.abs(y_train - y_train_pred),
#     "Relative Error (%)": train_metrics["relative_error"]
# })
#
# # ==== 保存测试集结果 ====
# df_test_result = pd.DataFrame({
#     "Set": "test",
#     "Compound_ID": id_test,
#     "Temperature (K)": T_test,
#     "Hvap_true (J/mol)": y_test,
#     "Hvap_pred (J/mol)": y_test_pred,
#     "Absolute Error": np.abs(y_test - y_test_pred),
#     "Relative Error (%)": test_metrics["relative_error"]
# })
#
# # ==== 合并保存最终模型结果 ====
# df_result = pd.concat([df_train_result, df_test_result], axis=0).reset_index(drop=True)
# df_result.to_excel("Hvap_prediction_with_slopeT_and_intercept_19group_by_material.xlsx", index=False)
#
# # ==== 保存主模型汇总 ====
# summary_df = pd.DataFrame([
#     ["final_main_model", "train", train_metrics["R2"], train_metrics["MSE"], train_metrics["ARD_%"],
#      train_metrics["within_1pct"], train_metrics["within_5pct"], train_metrics["within_10pct"]],
#     ["final_main_model", "test", test_metrics["R2"], test_metrics["MSE"], test_metrics["ARD_%"],
#      test_metrics["within_1pct"], test_metrics["within_5pct"], test_metrics["within_10pct"]],
# ], columns=[
#     "Model", "Dataset", "R2", "MSE", "ARD_%", "within_1pct", "within_5pct", "within_10pct"
# ])
# summary_df.to_excel("Hvap_prediction_summary_by_material.xlsx", index=False)
#
# # ==== 保存子模型汇总 ====
# submodel_summary_df = pd.DataFrame([
#     [tb_metrics["Model"], tb_metrics["R2"], tb_metrics["MSE"], tb_metrics["ARD_%"],
#      tb_metrics["within_1pct"], tb_metrics["within_5pct"], tb_metrics["within_10pct"]],
#     [hv298_metrics["Model"], hv298_metrics["R2"], hv298_metrics["MSE"], hv298_metrics["ARD_%"],
#      hv298_metrics["within_1pct"], hv298_metrics["within_5pct"], hv298_metrics["within_10pct"]],
#     [hvTb_metrics["Model"], hvTb_metrics["R2"], hvTb_metrics["MSE"], hvTb_metrics["ARD_%"],
#      hvTb_metrics["within_1pct"], hvTb_metrics["within_5pct"], hvTb_metrics["within_10pct"]],
# ], columns=[
#     "Model", "R2", "MSE", "ARD_%", "within_1pct", "within_5pct", "within_10pct"
# ])
# submodel_summary_df.to_excel("Hvap_submodel_summary.xlsx", index=False)
#
# print("\n✅ 预测结果已保存为 Hvap_prediction_with_slopeT_and_intercept_19group_by_material.xlsx")
# print("✅ 主模型汇总已保存为 Hvap_prediction_summary_by_material.xlsx")
# print("✅ 子模型汇总已保存为 Hvap_submodel_summary.xlsx")


import pandas as pd
import numpy as np

from sklearn.linear_model import HuberRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import PolynomialFeatures
from sklearn.model_selection import train_test_split
from scipy.optimize import least_squares


# ============================================================
# 0. 常数与路径
# ============================================================

HV0, HVB, Tb0 = 9612.7, 15419.9, 222.543
T_ref = 298.15

main_file = "heat of vaporization 204.xlsx"
file_298 = "selected_25_descriptors_data_298.xlsx"
file_tb = "selected_25_descriptors_data_boiling_point.xlsx"


# ============================================================
# 1. 通用评估函数
# ============================================================

def evaluate_metrics(y_true, y_pred, name="模型", strict_less=False):
    y_true = np.asarray(y_true, dtype=float).flatten()
    y_pred = np.asarray(y_pred, dtype=float).flatten()

    finite_mask = np.isfinite(y_true) & np.isfinite(y_pred)

    y_true_valid = y_true[finite_mask]
    y_pred_valid = y_pred[finite_mask]

    if len(y_true_valid) == 0:
        print(f"\n{name}评估结果: 无有效样本")
        return {
            "Model": name,
            "R2": np.nan,
            "MSE": np.nan,
            "ARD_%": np.nan,
            "within_1pct": 0,
            "within_5pct": 0,
            "within_10pct": 0,
            "relative_error": np.full_like(y_true, np.nan, dtype=float),
        }

    mse = mean_squared_error(y_true_valid, y_pred_valid)
    r2 = r2_score(y_true_valid, y_pred_valid)

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

    if strict_less:
        within_1pct = np.sum(relative_error_valid < 1)
        within_5pct = np.sum(relative_error_valid < 5)
        within_10pct = np.sum(relative_error_valid < 10)
    else:
        within_1pct = np.sum(relative_error_valid <= 1)
        within_5pct = np.sum(relative_error_valid <= 5)
        within_10pct = np.sum(relative_error_valid <= 10)

    relative_error_full = np.full_like(y_true, np.nan, dtype=float)
    relative_error_full[finite_mask] = relative_error_valid

    print(f"\n{name}评估结果:")
    print(f"R2  = {r2:.6f}")
    print(f"MSE = {mse:.6f}")
    print(f"ARD = {ard:.2f}%")

    if strict_less:
        print(f"相对误差 < 1% 的点数: {within_1pct}")
        print(f"相对误差 < 5% 的点数: {within_5pct}")
        print(f"相对误差 < 10% 的点数: {within_10pct}")
    else:
        print(f"相对误差 <= 1% 的点数: {within_1pct}")
        print(f"相对误差 <= 5% 的点数: {within_5pct}")
        print(f"相对误差 <= 10% 的点数: {within_10pct}")

    return {
        "Model": name,
        "R2": r2,
        "MSE": mse,
        "ARD_%": ard,
        "within_1pct": within_1pct,
        "within_5pct": within_5pct,
        "within_10pct": within_10pct,
        "relative_error": relative_error_full,
    }


# ============================================================
# 2. 读取数据
# ============================================================

df_main = pd.read_excel(main_file, sheet_name="Sheet1")

Nk_all = df_main.iloc[:, 13:32].apply(pd.to_numeric, errors="coerce")
poly = PolynomialFeatures(degree=2, include_bias=False)
Nk_poly = poly.fit_transform(Nk_all)

id_col = df_main.columns[0]


# ============================================================
# 3. Tb 子模型
# ============================================================

Tb_raw = pd.to_numeric(df_main.iloc[:, 5], errors="coerce").values
mask_tb = np.isfinite(Tb_raw)

Nk_valid_for_tb = Nk_all.loc[mask_tb]
Nk_poly_valid = poly.transform(Nk_valid_for_tb)

model_Tb = HuberRegressor(max_iter=10000)

model_Tb.fit(
    Nk_poly_valid,
    np.exp(Tb_raw[mask_tb] / Tb0)
)

Tb_pred_exp = model_Tb.predict(Nk_poly_valid)
Tb_pred_all = Tb0 * np.log(np.clip(Tb_pred_exp, 1e-6, None))

tb_metrics = evaluate_metrics(
    Tb_raw[mask_tb],
    Tb_pred_all,
    "Tb 子模型",
    strict_less=False
)


# ============================================================
# 4. HVap_298 子模型
# ============================================================

df_298 = pd.read_excel(file_298)
target_298 = "Heat of vaporization at normal temperature"

X_298 = df_298.drop(columns=[target_298]).apply(pd.to_numeric, errors="coerce")
y_298 = pd.to_numeric(df_298[target_298], errors="coerce").values

valid_298_mask = np.isfinite(y_298) & np.isfinite(X_298).all(axis=1)

rf_298 = RandomForestRegressor(
    random_state=42
)

rf_298.fit(
    X_298.loc[valid_298_mask],
    y_298[valid_298_mask]
)

HVap_298_all = rf_298.predict(X_298)

hv298_metrics = evaluate_metrics(
    y_298[valid_298_mask],
    rf_298.predict(X_298.loc[valid_298_mask]),
    "HVap_298 子模型",
    strict_less=False
)


# ============================================================
# 5. HVap_Tb 子模型
# ============================================================

df_Tb = pd.read_excel(file_tb)
target_Tb = "Heat of vaporization at boiling temperature"

X_Tb = df_Tb.drop(columns=[target_Tb]).apply(pd.to_numeric, errors="coerce")
y_Tb = pd.to_numeric(df_Tb[target_Tb], errors="coerce").values

valid_hvtb_mask = np.isfinite(y_Tb) & np.isfinite(X_Tb).all(axis=1)

rf_Tb = RandomForestRegressor(
    random_state=42
)

rf_Tb.fit(
    X_Tb.loc[valid_hvtb_mask],
    y_Tb[valid_hvtb_mask]
)

HVap_Tb_all = rf_Tb.predict(X_Tb)

hvTb_metrics = evaluate_metrics(
    y_Tb[valid_hvtb_mask],
    rf_Tb.predict(X_Tb.loc[valid_hvtb_mask]),
    "HVap_Tb 子模型",
    strict_less=False
)


# ============================================================
# 6. 对齐 mask_tb 后的数据
# ============================================================

if len(HVap_298_all) == len(df_main):
    HVap_298_used = HVap_298_all[mask_tb]
else:
    HVap_298_used = HVap_298_all

if len(HVap_Tb_all) == len(df_main):
    HVap_Tb_used = HVap_Tb_all[mask_tb]
else:
    HVap_Tb_used = HVap_Tb_all

if len(HVap_298_used) != len(Tb_pred_all) or len(HVap_Tb_used) != len(Tb_pred_all):
    raise ValueError(
        "HVap_298/HVap_Tb 子模型输出长度与 Tb_pred_all 不一致，请检查三个文件是否按同一物质顺序排列。"
    )


# ============================================================
# 7. slope 特征
# ============================================================

denom = Tb_pred_all - T_ref
slope_pred = np.full_like(Tb_pred_all, np.nan, dtype=float)

valid_slope_mask = (
    np.isfinite(HVap_Tb_used)
    & np.isfinite(HVap_298_used)
    & np.isfinite(Tb_pred_all)
    & (np.abs(denom) > 1e-12)
)

slope_pred[valid_slope_mask] = (
    HVap_Tb_used[valid_slope_mask]
    - HVap_298_used[valid_slope_mask]
) / denom[valid_slope_mask]

slope_pred = slope_pred.reshape(-1, 1)


# ============================================================
# 8. 多温度点 ΔHvap 数据
# ============================================================

T = df_main.iloc[:, 32:42].apply(pd.to_numeric, errors="coerce").values[mask_tb]
Hvap = df_main.iloc[:, 42:52].apply(pd.to_numeric, errors="coerce").values[mask_tb]
MW = pd.to_numeric(df_main.iloc[:, 4], errors="coerce").values[mask_tb].reshape(-1, 1)
Nc = pd.to_numeric(df_main.iloc[:, 10], errors="coerce").values[mask_tb].reshape(-1, 1)
compound_ids_all = df_main.iloc[:, 0].values[mask_tb]

valid_row_mask = (
    np.isfinite(Hvap).all(axis=1)
    & (Hvap > 0).all(axis=1)
    & np.isfinite(T).all(axis=1)
    & np.isfinite(MW).flatten()
    & np.isfinite(Nc).flatten()
    & np.isfinite(slope_pred).flatten()
)

Nk_valid = Nk_valid_for_tb.loc[valid_row_mask].values
MW = MW[valid_row_mask]
Nc = Nc[valid_row_mask]
T = T[valid_row_mask]
Hvap = Hvap[valid_row_mask]
slope_pred = slope_pred[valid_row_mask]
compound_ids_all = compound_ids_all[valid_row_mask]

print("\n========== 按物质划分最终主模型 ==========")
print(f"有效物质数: {len(compound_ids_all)}")


# ============================================================
# 9. 只对最终主模型按物质 8:2 划分
# ============================================================

material_indices = np.arange(len(compound_ids_all))

train_idx, test_idx = train_test_split(
    material_indices,
    test_size=0.2,
    random_state=42
)

Nk_train, Nk_test = Nk_valid[train_idx], Nk_valid[test_idx]
MW_train, MW_test = MW[train_idx], MW[test_idx]
Nc_train, Nc_test = Nc[train_idx], Nc[test_idx]

T_train_raw, T_test_raw = T[train_idx], T[test_idx]
Hvap_train_raw, Hvap_test_raw = Hvap[train_idx], Hvap[test_idx]

slope_train, slope_test = slope_pred[train_idx], slope_pred[test_idx]
id_train_raw, id_test_raw = compound_ids_all[train_idx], compound_ids_all[test_idx]

print(f"训练集物质数: {len(train_idx)}")
print(f"测试集物质数: {len(test_idx)}")


# ============================================================
# 10. 把每个物质展开成 10 个温度点样本
# ============================================================

def build_point_dataset(Nk, MW, Nc, T, Hvap, slope_pred, compound_ids):
    X = np.hstack([
        Nk.repeat(10, axis=0),
        MW.repeat(10, axis=0),
        Nc.repeat(10, axis=0),
        T.flatten().reshape(-1, 1),
        slope_pred.repeat(10, axis=0)
    ])

    y = Hvap.flatten()

    expanded_ids = np.repeat(compound_ids, 10)
    expanded_T = T.flatten()
    expanded_slope = slope_pred.repeat(10, axis=0).flatten()

    mask = np.isfinite(y) & np.isfinite(X).all(axis=1)

    return (
        X[mask],
        y[mask],
        expanded_ids[mask],
        expanded_T[mask],
        expanded_slope[mask]
    )


X_train, y_train, id_train, T_train, slope_point_train = build_point_dataset(
    Nk_train,
    MW_train,
    Nc_train,
    T_train_raw,
    Hvap_train_raw,
    slope_train,
    id_train_raw
)

X_test, y_test, id_test, T_test, slope_point_test = build_point_dataset(
    Nk_test,
    MW_test,
    Nc_test,
    T_test_raw,
    Hvap_test_raw,
    slope_test,
    id_test_raw
)

print(f"训练集样本点数: {len(X_train)}")
print(f"测试集样本点数: {len(X_test)}")


# ============================================================
# 11. 前向预测函数
# ============================================================

def model_predict(params, X):
    Nk = X[:, :19]
    MW = X[:, 19].reshape(-1, 1)
    Nc = X[:, 20].reshape(-1, 1)
    T = np.clip(X[:, 21].reshape(-1, 1), 1e-6, None)
    slope = X[:, 22].reshape(-1, 1)

    B1k = params[0:19]
    B2k = params[19:38]

    C1k = params[38:57]
    C2k = params[57:76]

    D1k = params[76:95]
    D2k = params[95:114]

    beta, gamma, delta = params[114:117]
    f0, f1 = params[117:119]

    gamma_slope = params[119]
    intercept = params[120]

    R = 8.3144

    Bi = (
        np.sum(Nk * (B1k + MW * B2k), axis=1, keepdims=True)
        + beta * (f0 + Nc * f1)
    )

    Ci = (
        np.sum(Nk * (C1k + MW * C2k), axis=1, keepdims=True)
        + gamma * (f0 + Nc * f1)
    )

    Di = (
        np.sum(Nk * (D1k + MW * D2k), axis=1, keepdims=True)
        + delta * (f0 + Nc * f1)
    )

    y_pred = (
        -R * (
            (1.5 * Bi) / np.sqrt(T)
            + Ci * T
            + Di * T ** 2
        )
        + gamma_slope * slope * T
        + intercept
    )

    return y_pred.flatten()


def residuals(params, X, y):
    return model_predict(params, X) - y


# ============================================================
# 12. 主模型拟合
# ============================================================

params_init = np.zeros(121)

print("\n主模型拟合中，请稍候...")

result = least_squares(
    residuals,
    x0=params_init,
    args=(X_train, y_train),
    max_nfev=10000
)


# ============================================================
# 13. 训练集 / 测试集预测
# ============================================================

y_train_pred = model_predict(result.x, X_train)
y_test_pred = model_predict(result.x, X_test)


# ============================================================
# 14. 主模型评估
# ============================================================

train_metrics = evaluate_metrics(
    y_train,
    y_train_pred,
    "最终主模型 - 训练集",
    strict_less=False
)

test_metrics = evaluate_metrics(
    y_test,
    y_test_pred,
    "最终主模型 - 测试集",
    strict_less=False
)


# ============================================================
# 14.1 完整数据集统计：训练集 + 测试集
# ============================================================

X_all = np.vstack([
    X_train,
    X_test
])

y_all = np.concatenate([
    y_train,
    y_test
])

y_all_pred = np.concatenate([
    y_train_pred,
    y_test_pred
])

id_all = np.concatenate([
    id_train,
    id_test
])

T_all_used = np.concatenate([
    T_train,
    T_test
])

slope_point_all = np.concatenate([
    slope_point_train,
    slope_point_test
])

all_metrics = evaluate_metrics(
    y_all,
    y_all_pred,
    "最终主模型 - 完整数据集 train + test",
    strict_less=True
)

print("\n最终主模型完整数据集 Hvap 预测偏差 1%，5%，10%分别为：")
print(all_metrics["within_1pct"])
print(all_metrics["within_5pct"])
print(all_metrics["within_10pct"])


# ============================================================
# 15. 输出参数
# ============================================================

param_names = (
    [f"B1_{i}" for i in range(19)] +
    [f"B2_{i}" for i in range(19)] +
    [f"C1_{i}" for i in range(19)] +
    [f"C2_{i}" for i in range(19)] +
    [f"D1_{i}" for i in range(19)] +
    [f"D2_{i}" for i in range(19)] +
    ["beta", "gamma", "delta", "f0", "f1", "gamma_slope", "intercept"]
)

print("\n参数拟合结果:")
for name, val in zip(param_names, result.x):
    print(f"{name:14s}: {val:.6f}")


# ============================================================
# 16. 保存训练集结果
# ============================================================

df_train_result = pd.DataFrame({
    "Set": "train",
    "Compound_ID": id_train,
    "Temperature (K)": T_train,
    "slope": slope_point_train,
    "Hvap_true (J/mol)": y_train,
    "Hvap_pred (J/mol)": y_train_pred,
    "Absolute Error": np.abs(y_train - y_train_pred),
    "Relative Error (%)": train_metrics["relative_error"]
})


# ============================================================
# 17. 保存测试集结果
# ============================================================

df_test_result = pd.DataFrame({
    "Set": "test",
    "Compound_ID": id_test,
    "Temperature (K)": T_test,
    "slope": slope_point_test,
    "Hvap_true (J/mol)": y_test,
    "Hvap_pred (J/mol)": y_test_pred,
    "Absolute Error": np.abs(y_test - y_test_pred),
    "Relative Error (%)": test_metrics["relative_error"]
})


# ============================================================
# 18. 保存完整数据集结果
# ============================================================

df_all_result = pd.DataFrame({
    "Set": "all_train_plus_test",
    "Compound_ID": id_all,
    "Temperature (K)": T_all_used,
    "slope": slope_point_all,
    "Hvap_true (J/mol)": y_all,
    "Hvap_pred (J/mol)": y_all_pred,
    "Absolute Error": np.abs(y_all - y_all_pred),
    "Relative Error (%)": all_metrics["relative_error"]
})


# ============================================================
# 19. 汇总表
# ============================================================

main_summary_df = pd.DataFrame([
    [
        "final_main_model",
        "train",
        train_metrics["R2"],
        train_metrics["MSE"],
        train_metrics["ARD_%"],
        train_metrics["within_1pct"],
        train_metrics["within_5pct"],
        train_metrics["within_10pct"]
    ],
    [
        "final_main_model",
        "test",
        test_metrics["R2"],
        test_metrics["MSE"],
        test_metrics["ARD_%"],
        test_metrics["within_1pct"],
        test_metrics["within_5pct"],
        test_metrics["within_10pct"]
    ],
    [
        "final_main_model",
        "all_train_plus_test",
        all_metrics["R2"],
        all_metrics["MSE"],
        all_metrics["ARD_%"],
        all_metrics["within_1pct"],
        all_metrics["within_5pct"],
        all_metrics["within_10pct"]
    ],
], columns=[
    "Model",
    "Dataset",
    "R2",
    "MSE",
    "ARD_%",
    "within_1pct",
    "within_5pct",
    "within_10pct"
])


# ============================================================
# 20. 子模型汇总
# ============================================================

submodel_summary_df = pd.DataFrame([
    [
        tb_metrics["Model"],
        "all_data",
        tb_metrics["R2"],
        tb_metrics["MSE"],
        tb_metrics["ARD_%"],
        tb_metrics["within_1pct"],
        tb_metrics["within_5pct"],
        tb_metrics["within_10pct"]
    ],
    [
        hv298_metrics["Model"],
        "all_data",
        hv298_metrics["R2"],
        hv298_metrics["MSE"],
        hv298_metrics["ARD_%"],
        hv298_metrics["within_1pct"],
        hv298_metrics["within_5pct"],
        hv298_metrics["within_10pct"]
    ],
    [
        hvTb_metrics["Model"],
        "all_data",
        hvTb_metrics["R2"],
        hvTb_metrics["MSE"],
        hvTb_metrics["ARD_%"],
        hvTb_metrics["within_1pct"],
        hvTb_metrics["within_5pct"],
        hvTb_metrics["within_10pct"]
    ],
], columns=[
    "Model",
    "Dataset",
    "R2",
    "MSE",
    "ARD_%",
    "within_1pct",
    "within_5pct",
    "within_10pct"
])


# ============================================================
# 21. 子模型预测详情
# ============================================================

tb_pred_df = pd.DataFrame({
    "Dataset": "all_data",
    "Compound_ID": df_main.iloc[:, 0].values[mask_tb],
    "Tb_true": Tb_raw[mask_tb],
    "Tb_pred": Tb_pred_all
})

hv298_pred_df = pd.DataFrame({
    "Dataset": "all_data",
    "HVap_298_true": y_298,
    "HVap_298_pred": HVap_298_all
})

hvtb_pred_df = pd.DataFrame({
    "Dataset": "all_data",
    "HVap_Tb_true": y_Tb,
    "HVap_Tb_pred": HVap_Tb_all
})

slope_df = pd.DataFrame({
    "Dataset": "all_data_after_main_cleaning",
    "Compound_ID": compound_ids_all,
    "slope": slope_pred.flatten()
})


# ============================================================
# 22. 参数表
# ============================================================

param_df = pd.DataFrame({
    "Parameter": param_names,
    "Value": result.x
})


# ============================================================
# 23. 保存全部结果
# ============================================================

output_filename = "Hvap_prediction_with_slopeT_and_intercept_19group_by_material.xlsx"

with pd.ExcelWriter(output_filename, engine="xlsxwriter") as writer:
    pd.concat(
        [df_train_result, df_test_result],
        axis=0,
        ignore_index=True
    ).to_excel(
        writer,
        sheet_name="predictions_train_test",
        index=False
    )

    df_all_result.to_excel(
        writer,
        sheet_name="predictions_all",
        index=False
    )

    main_summary_df.to_excel(
        writer,
        sheet_name="main_summary",
        index=False
    )

    submodel_summary_df.to_excel(
        writer,
        sheet_name="submodel_summary",
        index=False
    )

    tb_pred_df.to_excel(
        writer,
        sheet_name="Tb_submodel",
        index=False
    )

    hv298_pred_df.to_excel(
        writer,
        sheet_name="HVap_298_submodel",
        index=False
    )

    hvtb_pred_df.to_excel(
        writer,
        sheet_name="HVap_Tb_submodel",
        index=False
    )

    slope_df.to_excel(
        writer,
        sheet_name="slope",
        index=False
    )

    param_df.to_excel(
        writer,
        sheet_name="parameters",
        index=False
    )

print(f"\n预测结果已保存为 {output_filename}")


# ============================================================
# 24. 输出模型结构记录
# ============================================================

print("\n当前 Hvap slopeT + intercept 显式模型结构:")
print("Tb_submodel: HuberRegressor(max_iter=10000), input = PolynomialFeatures(Nk, degree=2)")
print("HVap_298_submodel: RandomForestRegressor(random_state=42), input = selected 25 descriptors at 298.15 K")
print("HVap_Tb_submodel: RandomForestRegressor(random_state=42), input = selected 25 descriptors at boiling point")
print("slope = (HVap_Tb_pred - HVap_298_pred) / (Tb_pred - 298.15)")
print("Final target: ordinary Hvap, not ln(Hvap)")
print("Final model: least_squares explicit Hvap equation with 121 parameters")
print("Final input features: Nk + MW + Nc + T + slope")
print("Final expression: Hvap = -R*((1.5*Bi)/sqrt(T) + Ci*T + Di*T^2) + gamma_slope*slope*T + intercept")
print("Final all-data statistics use strict thresholds: <1%, <5%, <10%")