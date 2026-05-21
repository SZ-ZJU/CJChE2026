# # import numpy as np
# # import pandas as pd
# # from scipy.optimize import least_squares
# # from sklearn.linear_model import HuberRegressor
# # from sklearn.preprocessing import PolynomialFeatures
# # from sklearn.metrics import mean_squared_error, r2_score
# # from sklearn.ensemble import GradientBoostingRegressor
# # from sklearn.model_selection import train_test_split
# #
# # # ========= 1. 数据加载 =========
# # df = pd.read_excel("vp209.xlsx", sheet_name="Sheet1").copy()
# #
# # # 物质ID
# # id_col = df.columns[0]
# # df = df.dropna(subset=[id_col]).copy()
# #
# # # ========= 2. 按物质 8:2 划分 =========
# # unique_materials = df[id_col].unique()
# # train_materials, test_materials = train_test_split(
# #     unique_materials,
# #     test_size=0.2,
# #     random_state=42
# # )
# #
# # train_materials = set(train_materials)
# # test_materials = set(test_materials)
# #
# # train_df = df[df[id_col].isin(train_materials)].copy().reset_index(drop=True)
# # test_df = df[df[id_col].isin(test_materials)].copy().reset_index(drop=True)
# #
# # print("========== 按物质划分 ==========")
# # print(f"总物质数: {len(unique_materials)}")
# # print(f"训练集物质数: {len(train_materials)}")
# # print(f"测试集物质数: {len(test_materials)}")
# # print(f"训练集行数: {len(train_df)}")
# # print(f"测试集行数: {len(test_df)}")
# #
# # # ========= 3. 列定义 =========
# # group_slice = slice(12, 31)   # 19个基团
# # Tb_col_idx = 5
# # MW_col_idx = 4
# # Ncs_col_idx = 9
# # Nc_col_idx = 10
# # temp_slice = slice(31, 41)
# # vp_slice = slice(41, 51)
# # Pc_col_idx = 51
# # Tc_col_name = "ASPEN Half Critical T"
# #
# # Pb = 101325.0  # Pa
# # Tb0 = 222.543
# #
# # # ========= 4. 子模型辅助函数 =========
# # def get_group_poly_features(df_part, poly=None, fit_poly=False):
# #     Nk = df_part.iloc[:, group_slice].apply(pd.to_numeric, errors="coerce").fillna(0).values
# #     if fit_poly:
# #         poly = PolynomialFeatures(degree=2, include_bias=False)
# #         Nk_poly = poly.fit_transform(Nk)
# #         return Nk, Nk_poly, poly
# #     else:
# #         Nk_poly = poly.transform(Nk)
# #         return Nk, Nk_poly
# #
# # def evaluate_scalar_regression(y_true, y_pred, model_name, split_name):
# #     y_true = np.asarray(y_true, dtype=float)
# #     y_pred = np.asarray(y_pred, dtype=float)
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
# #             "MSE": np.nan
# #         }
# #
# #     r2 = r2_score(y_true, y_pred)
# #     mse = mean_squared_error(y_true, y_pred)
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
# # #
# # # # ========= 5. 训练 Tb 子模型（只用训练集） =========
# # # Nk_train, Nk_poly_train, poly = get_group_poly_features(train_df, fit_poly=True)
# # # Nk_test, Nk_poly_test = get_group_poly_features(test_df, poly=poly, fit_poly=False)
# # #
# # # Tb_train = pd.to_numeric(train_df.iloc[:, Tb_col_idx], errors="coerce").values
# # # Tb_test = pd.to_numeric(test_df.iloc[:, Tb_col_idx], errors="coerce").values
# # #
# # # tb_train_mask = np.isfinite(Tb_train) & np.isfinite(Nk_poly_train).all(axis=1)
# # # tb_test_mask = np.isfinite(Tb_test) & np.isfinite(Nk_poly_test).all(axis=1)
# # #
# # # model_tb = HuberRegressor(max_iter=10000)
# # # model_tb.fit(Nk_poly_train[tb_train_mask], np.exp(Tb_train[tb_train_mask] / Tb0))
# # #
# # # Tb_pred_train = Tb0 * np.log(np.clip(model_tb.predict(Nk_poly_train), 1e-6, None))
# # # Tb_pred_test = Tb0 * np.log(np.clip(model_tb.predict(Nk_poly_test), 1e-6, None))
# # #
# # # tb_metrics_train = evaluate_scalar_regression(Tb_train[tb_train_mask], Tb_pred_train[tb_train_mask], "Tb_submodel", "train")
# # # tb_metrics_test = evaluate_scalar_regression(Tb_test[tb_test_mask], Tb_pred_test[tb_test_mask], "Tb_submodel", "test")
# # from sklearn.ensemble import RandomForestRegressor
# #
# # # ========= 5. 训练 Tb 子模型（只用训练集，改为 RF，且不使用 poly） =========
# # Nk_train, Nk_poly_train, poly = get_group_poly_features(train_df, fit_poly=True)
# # Nk_test, Nk_poly_test = get_group_poly_features(test_df, poly=poly, fit_poly=False)
# #
# # Tb_train = pd.to_numeric(train_df.iloc[:, Tb_col_idx], errors="coerce").values
# # Tb_test = pd.to_numeric(test_df.iloc[:, Tb_col_idx], errors="coerce").values
# #
# # # Tb 子模型改成使用原始 19 个基团
# # tb_train_mask = np.isfinite(Tb_train) & np.isfinite(Nk_train).all(axis=1)
# # tb_test_mask = np.isfinite(Tb_test) & np.isfinite(Nk_test).all(axis=1)
# #
# # model_tb = RandomForestRegressor(
# #     n_estimators=300,
# #     max_depth=None,
# #     min_samples_split=4,
# #     min_samples_leaf=2,
# #     random_state=42,
# #     n_jobs=-1
# # )
# #
# # model_tb.fit(Nk_train[tb_train_mask], Tb_train[tb_train_mask])
# #
# # Tb_pred_train = model_tb.predict(Nk_train)
# # Tb_pred_test = model_tb.predict(Nk_test)
# #
# # tb_metrics_train = evaluate_scalar_regression(
# #     Tb_train[tb_train_mask],
# #     Tb_pred_train[tb_train_mask],
# #     "Tb_submodel",
# #     "train"
# # )
# #
# # tb_metrics_test = evaluate_scalar_regression(
# #     Tb_test[tb_test_mask],
# #     Tb_pred_test[tb_test_mask],
# #     "Tb_submodel",
# #     "test"
# # )
# # # ========= 6. 训练 Tc 子模型（只用训练集） =========
# # Tc_train = pd.to_numeric(train_df[Tc_col_name], errors="coerce").values
# # Tc_test = pd.to_numeric(test_df[Tc_col_name], errors="coerce").values
# #
# # tc_train_mask = np.isfinite(Tc_train) & np.isfinite(Nk_poly_train).all(axis=1)
# # tc_test_mask = np.isfinite(Tc_test) & np.isfinite(Nk_poly_test).all(axis=1)
# #
# # gb_model_tc = GradientBoostingRegressor(
# #     n_estimators=300,
# #     learning_rate=0.05,
# #     max_depth=4,
# #     random_state=0
# # )
# # gb_model_tc.fit(Nk_poly_train[tc_train_mask], Tc_train[tc_train_mask])
# #
# # Tc_pred_train = gb_model_tc.predict(Nk_poly_train)
# # Tc_pred_test = gb_model_tc.predict(Nk_poly_test)
# #
# # tc_metrics_train = evaluate_scalar_regression(Tc_train[tc_train_mask], Tc_pred_train[tc_train_mask], "Tc_submodel", "train")
# # tc_metrics_test = evaluate_scalar_regression(Tc_test[tc_test_mask], Tc_pred_test[tc_test_mask], "Tc_submodel", "test")
# #
# # # ========= 7. 训练 Pc 子模型（只用训练集） =========
# # # ========= 7. 训练 Pc 子模型（只用训练集，不使用 poly 基团） =========
# # MW_train = pd.to_numeric(train_df.iloc[:, MW_col_idx], errors="coerce").values.flatten()
# # MW_test = pd.to_numeric(test_df.iloc[:, MW_col_idx], errors="coerce").values.flatten()
# #
# # Pc_bar_train = pd.to_numeric(train_df.iloc[:, Pc_col_idx], errors="coerce").values
# # Pc_bar_test = pd.to_numeric(test_df.iloc[:, Pc_col_idx], errors="coerce").values
# #
# # # 这里改成原始19个基团，不用 Nk_poly_train / Nk_poly_test
# # # 注意：Nk_train、Nk_test 是你前面 get_group_poly_features(...) 返回的原始基团矩阵
# # # Nk_train.shape = (n_train, 19)
# # # Nk_test.shape = (n_test, 19)
# #
# # def residual_pc(params, X, MW, Pc_true_bar):
# #     beta = params[:-1]   # 19个基团系数
# #     beta3 = params[-1]   # MW项系数
# #
# #     y_pred = X @ beta
# #     x_pred = y_pred + 0.108998
# #
# #     # 防止除零/接近零爆炸
# #     x_pred = np.where(
# #         np.abs(x_pred) < 1e-8,
# #         np.sign(x_pred) * 1e-8 + (x_pred == 0) * 1e-8,
# #         x_pred
# #     )
# #
# #     Pc_pred_bar = 5.9827 + (1.0 / x_pred) ** 2 + beta3 * np.exp(1.0 / np.clip(MW, 1e-8, None))
# #     return Pc_pred_bar - Pc_true_bar
# #
# # # mask 也改成检查 Nk_train / Nk_test，而不是 Nk_poly_train / Nk_poly_test
# # pc_train_mask = (
# #     np.isfinite(Pc_bar_train)
# #     & np.isfinite(MW_train)
# #     & np.isfinite(Nk_train).all(axis=1)
# # )
# #
# # pc_test_mask = (
# #     np.isfinite(Pc_bar_test)
# #     & np.isfinite(MW_test)
# #     & np.isfinite(Nk_test).all(axis=1)
# # )
# #
# # # 参数个数 = 原始19个基团 + 1个 beta3
# # params_init_pc = np.zeros(Nk_train.shape[1] + 1)
# #
# # result_pc = least_squares(
# #     residual_pc,
# #     x0=params_init_pc,
# #     args=(Nk_train[pc_train_mask], MW_train[pc_train_mask], Pc_bar_train[pc_train_mask]),
# #     max_nfev=5000
# # )
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
# #     Pc_pred_bar = 5.9827 + (1.0 / x_fit) ** 2 + result_pc.x[-1] * np.exp(1.0 / np.clip(MW, 1e-8, None))
# #     return Pc_pred_bar * 1e5   # 转成 Pa
# #
# # Pc_pred_train = predict_pc_pa(Nk_train, MW_train, result_pc)
# # Pc_pred_test = predict_pc_pa(Nk_test, MW_test, result_pc)
# #
# # pc_metrics_train = evaluate_scalar_regression(
# #     Pc_bar_train[pc_train_mask] * 1e5,
# #     Pc_pred_train[pc_train_mask],
# #     "Pc_submodel",
# #     "train"
# # )
# #
# # pc_metrics_test = evaluate_scalar_regression(
# #     Pc_bar_test[pc_test_mask] * 1e5,
# #     Pc_pred_test[pc_test_mask],
# #     "Pc_submodel",
# #     "test"
# # )
# # # ========= 8. 构造 slope（分别对训练集/测试集预测） =========
# # def build_slope(Tb_pred, Tc_pred, Pc_pred_pa):
# #     denom = Tc_pred * 2.0 - Tb_pred
# #     slope = np.full_like(Tb_pred, np.nan, dtype=float)
# #
# #     valid = np.isfinite(Tb_pred) & np.isfinite(Tc_pred) & np.isfinite(Pc_pred_pa) & (Pc_pred_pa > 0) & (np.abs(denom) > 1e-12)
# #     slope[valid] = (np.log(Pc_pred_pa[valid]) - np.log(Pb)) / denom[valid]
# #     return slope.reshape(-1, 1)
# #
# # slope_train = build_slope(Tb_pred_train, Tc_pred_train, Pc_pred_train)
# # slope_test = build_slope(Tb_pred_test, Tc_pred_test, Pc_pred_test)
# #
# # # ========= 9. 构建最终蒸汽压模型数据集 =========
# # def build_final_dataset(df_part, slope_all):
# #     ids = df_part.iloc[:, 0].values
# #     Nk = df_part.iloc[:, group_slice].apply(pd.to_numeric, errors="coerce").values
# #     T = df_part.iloc[:, temp_slice].apply(pd.to_numeric, errors="coerce").values
# #     P_vp = df_part.iloc[:, vp_slice].apply(pd.to_numeric, errors="coerce").values
# #     MW = pd.to_numeric(df_part.iloc[:, MW_col_idx], errors="coerce").values.reshape(-1, 1)
# #     Nc = pd.to_numeric(df_part.iloc[:, Nc_col_idx], errors="coerce").values.reshape(-1, 1)
# #     Ncs = pd.to_numeric(df_part.iloc[:, Ncs_col_idx], errors="coerce").values.reshape(-1, 1)
# #
# #     # 和你原逻辑保持一致：每个物质10个蒸汽压点都必须有效
# #     valid_mask = np.isfinite(P_vp) & (P_vp > 0)
# #     valid_mask = valid_mask.all(axis=1)
# #
# #     # 还要求 slope、MW、Nc、Ncs、Nk、T 有效
# #     extra_mask = (
# #         np.isfinite(slope_all).flatten()
# #         & np.isfinite(MW).flatten()
# #         & np.isfinite(Nc).flatten()
# #         & np.isfinite(Ncs).flatten()
# #         & np.isfinite(Nk).all(axis=1)
# #         & np.isfinite(T).all(axis=1)
# #     )
# #
# #     final_mask = valid_mask & extra_mask
# #
# #     ids = ids[final_mask]
# #     Nk = Nk[final_mask]
# #     T = T[final_mask]
# #     P_vp = P_vp[final_mask]
# #     MW = MW[final_mask]
# #     Nc = Nc[final_mask]
# #     Ncs = Ncs[final_mask]
# #     slope_all = slope_all[final_mask]
# #
# #     y = np.log(P_vp).flatten()
# #
# #     X = np.hstack([
# #         Nk.repeat(10, axis=0),
# #         MW.repeat(10, axis=0),
# #         Nc.repeat(10, axis=0),
# #         Ncs.repeat(10, axis=0),
# #         T.flatten().reshape(-1, 1),
# #         slope_all.repeat(10, axis=0) * T.flatten().reshape(-1, 1)
# #     ])
# #
# #     expanded_ids = np.repeat(ids, 10)
# #     expanded_T = T.flatten()
# #
# #     finite_mask = np.isfinite(y) & np.isfinite(X).all(axis=1)
# #
# #     return (
# #         X[finite_mask],
# #         y[finite_mask],
# #         expanded_ids[finite_mask],
# #         expanded_T[finite_mask]
# #     )
# #
# # X_train, y_train, id_train, temp_train = build_final_dataset(train_df, slope_train)
# # X_test, y_test, id_test, temp_test = build_final_dataset(test_df, slope_test)
# #
# # print("\n========== 最终模型数据集 ==========")
# # print(f"训练集样本点数: {len(y_train)}")
# # print(f"测试集样本点数: {len(y_test)}")
# #
# # # ========= 10. 残差函数（19基团+斜率项） =========
# # def residuals(params, X, y):
# #     Nk = X[:, :19]
# #     MW = X[:, 19].reshape(-1, 1)
# #     Nc = X[:, 20].reshape(-1, 1)
# #     Ncs = X[:, 21].reshape(-1, 1)
# #     T = np.clip(X[:, 22].reshape(-1, 1), 1e-6, None)
# #     slope_T = X[:, 23].reshape(-1, 1)
# #
# #     A1k = params[:19]
# #     A2k = params[19:38]
# #     s0, s1 = params[38], params[39]
# #     alpha, f0, f1 = params[40], params[41], params[42]
# #     B1k = params[43:62]
# #     B2k = params[62:81]
# #     beta = params[81]
# #     C1k = params[82:101]
# #     C2k = params[101:120]
# #     gamma = params[120]
# #
# #     term_A = np.sum(Nk * (A1k + MW * A2k), axis=1) + s0 + s1 * Ncs.flatten() + alpha * (f0 + f1 * Nc.flatten())
# #     term_B = np.sum(Nk * (B1k + MW * B2k), axis=1) + beta * (f0 + f1 * Nc.flatten())
# #     term_C = np.sum(Nk * (C1k + MW * C2k), axis=1)
# #
# #     y_pred = term_A + term_B / T.flatten() + term_C * np.log(T.flatten()) + gamma * slope_T.flatten()
# #     return y - y_pred
# #
# # # ========= 11. 初始参数设置 =========
# # params_init = np.zeros(121)
# #
# # params_init[:19] = [
# #     13.65853808, 3.28418546, -659.6444719, 12.37483133, 4.81265536,
# #     2.91551829, 97.31954706, 87.70370771, 95.98266611, 3.887261236,
# #     27.43160868, 207.1319101, 47.22447225, 4687.002401, 3.637088127,
# #     1523.380387, 3162.746842, 12062.07738, -8900.847866
# # ]
# #
# # params_init[19:38] = [
# #     -0.015716978, 0.009075383, 11.48620132, -21.10261532, -0.011767963,
# #     0.002675368, -0.109835685, -0.010236179, -0.171652319, 0.005908914,
# #     10.467947, -5.994107293, -0.112649727, -17.43861742, 0.001820612,
# #     -12.29192011, -5.831333421, -30.99113155, 26.51752291
# # ]
# #
# # params_init[38:43] = [17.60905342, -0.000738906, 0.018089414, 0.0, 1.0]
# #
# # params_init[43:62] = [
# #     -1346.02436, -683.1104648, 67218.65971, -1384.512471, -884.3388538,
# #     -1241.799972, -8807.96886, -9868.206835, -9972.171472, -764.4721254,
# #     -2768.98, -22960.24319, -4496.012972, -507785.7608, -2221.349576,
# #     -157397.6395, -350388.1207, -1307700.942, 957312.8216
# # ]
# #
# # params_init[62:81] = [
# #     1.451298512, -0.736859315, -584.0308556, 3.123573902, 0.887401846,
# #     0.122658761, 8.501979442, 0.898999866, 15.05201845, -0.396917177,
# #     6.455487385, 318.8958283, 9.649044453, 2010.74563, 0.550921963,
# #     1486.747823, 523.9930512, 3372.517851, -2848.526234
# # ]
# #
# # params_init[81] = -6.750229278
# #
# # params_init[82:101] = [
# #     -1.846676986, -0.38538898, 85.74714557, -1.76399843, -0.569402352,
# #     -0.250943128, -13.054703, -11.40790845, -12.58276815, -0.468789896,
# #     -3.52337599, -26.44154671, -6.353423865, -606.0715674, -0.130106514,
# #     -198.3318276, -407.7121286, -1560.004645, 1152.427648
# # ]
# #
# # params_init[101:120] = [
# #     0.002016846, -0.001221385, 7.344413404, 0.894155383, 0.001594902,
# #     -0.000468558, 0.01491123, 0.001327088, 0.022906548, -0.0008161,
# #     -0.43609896, -3.639773727, 0.015093667, 11.71908672, -0.000385519,
# #     -3.450680198, -14.53413618, 9.827970088, 2.387602073
# # ]
# #
# # params_init[120] = 1.0
# #
# # # ========= 12. 最终模型拟合（只用训练集） =========
# # print("\n🚀 最终模型拟合中，请稍候...")
# # result = least_squares(
# #     residuals,
# #     x0=params_init,
# #     args=(X_train, y_train),
# #     max_nfev=10000
# # )
# #
# # # ========= 13. 最终评估函数 =========
# # def evaluate_final(name, X, y, compound_ids, temp_values, params):
# #     y_pred = y - residuals(params, X, y)
# #
# #     P_true = np.exp(y)
# #     P_pred = np.exp(y_pred)
# #
# #     r2_lnP = r2_score(y, y_pred)
# #     mse_lnP = mean_squared_error(y, y_pred)
# #
# #     r2_P = r2_score(P_true, P_pred)
# #     mse_P = mean_squared_error(P_true, P_pred)
# #     ard_P = np.mean(np.abs((P_pred - P_true) / P_true)) * 100
# #
# #     relative_error = np.abs((P_pred - P_true) / P_true) * 100
# #     within_1pct = np.sum(relative_error <= 1)
# #     within_5pct = np.sum(relative_error <= 5)
# #     within_10pct = np.sum(relative_error <= 10)
# #
# #     print(f"\n========== 最终模型 {name} ==========")
# #     print("ln(P) 指标:")
# #     print(f"R² = {r2_lnP:.6f}")
# #     print(f"MSE = {mse_lnP:.6f}")
# #
# #     print("\nP 指标:")
# #     print(f"R² = {r2_P:.6f}")
# #     print(f"MSE = {mse_P:.6f}")
# #     print(f"ARD = {ard_P:.2f}%")
# #     print(f"误差 ≤ 1% 的点数: {within_1pct}")
# #     print(f"误差 ≤ 5% 的点数: {within_5pct}")
# #     print(f"误差 ≤ 10% 的点数: {within_10pct}")
# #
# #     compare_df = pd.DataFrame({
# #         "Split": name,
# #         "Compound_ID": compound_ids,
# #         "Temperature_K": temp_values,
# #         "ln(P)_true": y,
# #         "ln(P)_pred": y_pred,
# #         "P_true": P_true,
# #         "P_pred": P_pred,
# #         "Absolute_Error_P": np.abs(P_pred - P_true),
# #         "Relative_Error_P (%)": relative_error,
# #         "Slope_Term": X[:, 23]
# #     })
# #
# #     summary = {
# #         "Model": "Final_vp_model_with_slope",
# #         "Split": name,
# #         "R2_lnP": r2_lnP,
# #         "MSE_lnP": mse_lnP,
# #         "R2_P": r2_P,
# #         "MSE_P": mse_P,
# #         "ARD_P_%": ard_P,
# #         "within_1pct": within_1pct,
# #         "within_5pct": within_5pct,
# #         "within_10pct": within_10pct
# #     }
# #
# #     return compare_df, summary
# #
# # train_compare_df, train_summary = evaluate_final("train", X_train, y_train, id_train, temp_train, result.x)
# # test_compare_df, test_summary = evaluate_final("test", X_test, y_test, id_test, temp_test, result.x)
# #
# # # ========= 14. 子模型预测结果表 =========
# # tb_out_train = pd.DataFrame({
# #     "Split": "train",
# #     "Compound_ID": train_df[id_col].values,
# #     "Tb_true": Tb_train,
# #     "Tb_pred": Tb_pred_train
# # })
# # tb_out_test = pd.DataFrame({
# #     "Split": "test",
# #     "Compound_ID": test_df[id_col].values,
# #     "Tb_true": Tb_test,
# #     "Tb_pred": Tb_pred_test
# # })
# #
# # tc_out_train = pd.DataFrame({
# #     "Split": "train",
# #     "Compound_ID": train_df[id_col].values,
# #     "Tc_true": Tc_train,
# #     "Tc_pred": Tc_pred_train
# # })
# # tc_out_test = pd.DataFrame({
# #     "Split": "test",
# #     "Compound_ID": test_df[id_col].values,
# #     "Tc_true": Tc_test,
# #     "Tc_pred": Tc_pred_test
# # })
# #
# # pc_out_train = pd.DataFrame({
# #     "Split": "train",
# #     "Compound_ID": train_df[id_col].values,
# #     "Pc_true_Pa": Pc_bar_train * 1e5,
# #     "Pc_pred_Pa": Pc_pred_train
# # })
# # pc_out_test = pd.DataFrame({
# #     "Split": "test",
# #     "Compound_ID": test_df[id_col].values,
# #     "Pc_true_Pa": Pc_bar_test * 1e5,
# #     "Pc_pred_Pa": Pc_pred_test
# # })
# #
# # slope_out_train = pd.DataFrame({
# #     "Split": "train",
# #     "Compound_ID": train_df[id_col].values,
# #     "Slope_pred": slope_train.flatten()
# # })
# # slope_out_test = pd.DataFrame({
# #     "Split": "test",
# #     "Compound_ID": test_df[id_col].values,
# #     "Slope_pred": slope_test.flatten()
# # })
# #
# # # ========= 15. 汇总表 =========
# # summary_df = pd.DataFrame([
# #     tb_metrics_train, tb_metrics_test,
# #     tc_metrics_train, tc_metrics_test,
# #     pc_metrics_train, pc_metrics_test,
# #     train_summary, test_summary
# # ])
# #
# # # ========= 16. 保存 =========
# # all_compare_df = pd.concat([train_compare_df, test_compare_df], ignore_index=True)
# # all_tb_df = pd.concat([tb_out_train, tb_out_test], ignore_index=True)
# # all_tc_df = pd.concat([tc_out_train, tc_out_test], ignore_index=True)
# # all_pc_df = pd.concat([pc_out_train, pc_out_test], ignore_index=True)
# # all_slope_df = pd.concat([slope_out_train, slope_out_test], ignore_index=True)
# #
# # output_filename = "Vapor_Pressure_With_Slope_Train_Test_Split.xlsx"
# # with pd.ExcelWriter(output_filename, engine="xlsxwriter") as writer:
# #     all_compare_df.to_excel(writer, sheet_name="final_predictions", index=False)
# #     summary_df.to_excel(writer, sheet_name="summary", index=False)
# #     all_tb_df.to_excel(writer, sheet_name="Tb_submodel", index=False)
# #     all_tc_df.to_excel(writer, sheet_name="Tc_submodel", index=False)
# #     all_pc_df.to_excel(writer, sheet_name="Pc_submodel", index=False)
# #     all_slope_df.to_excel(writer, sheet_name="slope_pred", index=False)
# #
# # print(f"\n✅ 结果已保存至 {output_filename}")
# import numpy as np
# import pandas as pd
# from scipy.optimize import least_squares
# from sklearn.linear_model import HuberRegressor
# from sklearn.preprocessing import PolynomialFeatures
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.ensemble import GradientBoostingRegressor
# from sklearn.model_selection import train_test_split
#
# # ========= 1. 数据加载 =========
# df = pd.read_excel("vp209.xlsx", sheet_name='Sheet1')
#
# # 保存物质ID
# compound_ids_all_raw = df.iloc[:, 0].values
#
# # 19个基团
# Nk = df.iloc[:, 12:31].values
# poly = PolynomialFeatures(degree=2, include_bias=False)
# Nk_poly = poly.fit_transform(Nk)
#
# # ========= 2. 沸点(Tb)模型 =========
# Tb0 = 222.543
# Tb = df.iloc[:, 5].values
# model_tb = HuberRegressor(max_iter=10000).fit(Nk_poly, np.exp(Tb / Tb0))
# Tb_pred = Tb0 * np.log(np.clip(model_tb.predict(Nk_poly), 1e-6, None))
#
# # ========= 3. 临界温度(Tc)模型 =========
# Tc_half = df['ASPEN Half Critical T'].values
# gb_model_tc = GradientBoostingRegressor(
#     n_estimators=300,
#     learning_rate=0.05,
#     max_depth=4,
#     random_state=0
# )
# gb_model_tc.fit(Nk_poly, Tc_half)
# Tc_pred = gb_model_tc.predict(Nk_poly)
#
# # ========= 4. 临界压力(Pc)模型 =========
# Pc_bar = df.iloc[:, 51].values
# MW = df.iloc[:, 4].values.flatten()
#
# def residual_pc(params, X, MW, Pc_true):
#     beta = params[:-1]
#     beta3 = params[-1]
#     y_pred = X @ beta
#     x_pred = y_pred + 0.108998
#     Pc_pred = 5.9827 + (1 / x_pred) ** 2 + beta3 * np.exp(1 / MW)
#     return Pc_pred - Pc_true
#
# params_init_pc = np.zeros(Nk_poly.shape[1] + 1)
# result_pc = least_squares(
#     residual_pc,
#     x0=params_init_pc,
#     args=(Nk_poly, MW, Pc_bar),
#     max_nfev=5000
# )
#
# x_fit = Nk_poly @ result_pc.x[:-1] + 0.108998
# Pc_pred = (5.9827 + (1 / x_fit) ** 2 + result_pc.x[-1] * np.exp(1 / MW)) * 1e5
#
# # ========= 5. 斜率特征构建 =========
# Pb = 101325
# slope_all = (np.log(Pc_pred) - np.log(Pb)) / (Tc_pred * 2 - Tb_pred)
# slope_all = slope_all.reshape(-1, 1)
#
# # ========= 6. 准备数据集 =========
# T = df.iloc[:, 31:41].values
# P_vp = df.iloc[:, 41:51].values
# MW = MW.reshape(-1, 1)
# Nc = df.iloc[:, 10].values.reshape(-1, 1)
# Ncs = df.iloc[:, 9].values.reshape(-1, 1)
#
# valid_mask = np.isfinite(P_vp) & (P_vp > 0)
# valid_mask = valid_mask.all(axis=1)
#
# Nk = Nk[valid_mask]
# T = T[valid_mask]
# P_vp = P_vp[valid_mask]
# MW = MW[valid_mask]
# Nc = Nc[valid_mask]
# Ncs = Ncs[valid_mask]
# slope_all = slope_all[valid_mask]
# compound_ids_all = compound_ids_all_raw[valid_mask]
#
# print("========== 数据清洗后 ==========")
# print(f"有效物质数: {len(compound_ids_all)}")
#
# # ========= 7. 按物质 8:2 划分 =========
# indices = np.arange(len(compound_ids_all))
#
# train_idx, test_idx = train_test_split(
#     indices,
#     test_size=0.2,
#     random_state=50
# )
#
# Nk_train, Nk_test = Nk[train_idx], Nk[test_idx]
# MW_train, MW_test = MW[train_idx], MW[test_idx]
# Nc_train, Nc_test = Nc[train_idx], Nc[test_idx]
# Ncs_train, Ncs_test = Ncs[train_idx], Ncs[test_idx]
# T_train_raw, T_test_raw = T[train_idx], T[test_idx]
# P_train_raw, P_test_raw = P_vp[train_idx], P_vp[test_idx]
# slope_train, slope_test = slope_all[train_idx], slope_all[test_idx]
# id_train_raw, id_test_raw = compound_ids_all[train_idx], compound_ids_all[test_idx]
#
# print("========== 按物质划分 ==========")
# print(f"训练集物质数: {len(train_idx)}")
# print(f"测试集物质数: {len(test_idx)}")
#
# # ========= 8. 把每个物质展开成10个温度点 =========
# def build_point_dataset(Nk, MW, Nc, Ncs, T, P_vp, slope_all, compound_ids):
#     y = np.log(P_vp).flatten()
#
#     X = np.hstack([
#         Nk.repeat(10, axis=0),
#         MW.repeat(10, axis=0),
#         Nc.repeat(10, axis=0),
#         Ncs.repeat(10, axis=0),
#         T.flatten().reshape(-1, 1),
#         slope_all.repeat(10, axis=0) * T.flatten().reshape(-1, 1)
#     ])
#
#     expanded_ids = np.repeat(compound_ids, 10)
#     expanded_T = T.flatten()
#     expanded_MW = MW.repeat(10, axis=0).flatten()
#     expanded_Nc = Nc.repeat(10, axis=0).flatten()
#     expanded_slopeT = (slope_all.repeat(10, axis=0) * T.flatten().reshape(-1, 1)).flatten()
#
#     finite_mask = np.isfinite(y) & np.isfinite(X).all(axis=1)
#
#     return (
#         X[finite_mask, :],
#         y[finite_mask],
#         expanded_ids[finite_mask],
#         expanded_T[finite_mask],
#         expanded_MW[finite_mask],
#         expanded_Nc[finite_mask],
#         expanded_slopeT[finite_mask]
#     )
#
# X_train, y_train, id_train, T_train, MW_train_out, Nc_train_out, Slope_train_out = build_point_dataset(
#     Nk_train, MW_train, Nc_train, Ncs_train, T_train_raw, P_train_raw, slope_train, id_train_raw
# )
#
# X_test, y_test, id_test, T_test, MW_test_out, Nc_test_out, Slope_test_out = build_point_dataset(
#     Nk_test, MW_test, Nc_test, Ncs_test, T_test_raw, P_test_raw, slope_test, id_test_raw
# )
#
# print(f"训练集样本点数: {len(X_train)}")
# print(f"测试集样本点数: {len(X_test)}")
#
# # ========= 9. 前向预测函数 =========
# def model_predict(params, X):
#     Nk = X[:, :19]
#     MW = X[:, 19].reshape(-1, 1)
#     Nc = X[:, 20].reshape(-1, 1)
#     Ncs = X[:, 21].reshape(-1, 1)
#     T = np.clip(X[:, 22].reshape(-1, 1), 1e-6, None)
#     slope_T = X[:, 23].reshape(-1, 1)
#
#     A1k = params[:19]
#     A2k = params[19:38]
#     s0, s1 = params[38], params[39]
#     alpha, f0, f1 = params[40], params[41], params[42]
#     B1k = params[43:62]
#     B2k = params[62:81]
#     beta = params[81]
#     C1k = params[82:101]
#     C2k = params[101:120]
#     gamma = params[120]
#
#     term_A = np.sum(Nk * (A1k + MW * A2k), axis=1) + s0 + s1 * Ncs.flatten() + alpha * (f0 + f1 * Nc.flatten())
#     term_B = np.sum(Nk * (B1k + MW * B2k), axis=1) + beta * (f0 + f1 * Nc.flatten())
#     term_C = np.sum(Nk * (C1k + MW * C2k), axis=1)
#
#     y_pred = term_A + term_B / T.flatten() + term_C * np.log(T.flatten()) + gamma * slope_T.flatten()
#     return y_pred
#
# # ========= 10. 残差函数 =========
# def residuals(params, X, y):
#     return y - model_predict(params, X)
#
# # ========= 11. 初始参数设置 =========
# params_init = np.zeros(121)
#
# params_init[:19] = [
#     13.65853808, 3.28418546, -659.6444719, 12.37483133, 4.81265536,
#     2.91551829, 97.31954706, 87.70370771, 95.98266611, 3.887261236,
#     27.43160868, 207.1319101, 47.22447225, 4687.002401, 3.637088127,
#     1523.380387, 3162.746842, 12062.07738, -8900.847866
# ]
#
# params_init[19:38] = [
#     -0.015716978, 0.009075383, 11.48620132, -21.10261532, -0.011767963,
#     0.002675368, -0.109835685, -0.010236179, -0.171652319, 0.005908914,
#     10.467947, -5.994107293, -0.112649727, -17.43861742, 0.001820612,
#     -12.29192011, -5.831333421, -30.99113155, 26.51752291
# ]
#
# params_init[38:43] = [17.60905342, -0.000738906, 0.018089414, 0.0, 1.0]
#
# params_init[43:62] = [
#     -1346.02436, -683.1104648, 67218.65971, -1384.512471, -884.3388538,
#     -1241.799972, -8807.96886, -9868.206835, -9972.171472, -764.4721254,
#     -2768.98, -22960.24319, -4496.012972, -507785.7608, -2221.349576,
#     -157397.6395, -350388.1207, -1307700.942, 957312.8216
# ]
#
# params_init[62:81] = [
#     1.451298512, -0.736859315, -584.0308556, 3.123573902, 0.887401846,
#     0.122658761, 8.501979442, 0.898999866, 15.05201845, -0.396917177,
#     6.455487385, 318.8958283, 9.649044453, 2010.74563, 0.550921963,
#     1486.747823, 523.9930512, 3372.517851, -2848.526234
# ]
#
# params_init[81] = -6.750229278
#
# params_init[82:101] = [
#     -1.846676986, -0.38538898, 85.74714557, -1.76399843, -0.569402352,
#     -0.250943128, -13.054703, -11.40790845, -12.58276815, -0.468789896,
#     -3.52337599, -26.44154671, -6.353423865, -606.0715674, -0.130106514,
#     -198.3318276, -407.7121286, -1560.004645, 1152.427648
# ]
#
# params_init[101:120] = [
#     0.002016846, -0.001221385, 7.344413404, 0.894155383, 0.001594902,
#     -0.000468558, 0.01491123, 0.001327088, 0.022906548, -0.0008161,
#     -0.43609896, -3.639773727, 0.015093667, 11.71908672, -0.000385519,
#     -3.450680198, -14.53413618, 9.827970088, 2.387602073
# ]
#
# params_init[120] = 1.0
#
# # ========= 12. 拟合（只用训练集） =========
# print("\n🚀 使用训练集拟合中，请稍候...")
# result = least_squares(
#     residuals,
#     x0=params_init,
#     args=(X_train, y_train),
#     max_nfev=10000
# )
#
# # ========= 13. 评估函数 =========
# def evaluate_dataset(name, X, y, compound_ids, temp_values, mw_values, nc_values, slope_values, params):
#     y_pred = model_predict(params, X)
#
#     # ln(P) 指标
#     mse_ln = mean_squared_error(y, y_pred)
#     r2_ln = r2_score(y, y_pred)
#
#     # 实际蒸汽压 P 指标
#     P_true = np.exp(y)
#     P_pred = np.exp(y_pred)
#
#     mse_real = mean_squared_error(P_true, P_pred)
#     r2_real = r2_score(P_true, P_pred)
#     ard_real = np.mean(np.abs((P_pred - P_true) / P_true)) * 100
#
#     relative_error = np.abs((P_pred - P_true) / P_true) * 100
#     within_1pct = np.sum(relative_error <= 1)
#     within_5pct = np.sum(relative_error <= 5)
#     within_10pct = np.sum(relative_error <= 10)
#
#     print(f"\n========== {name} ==========")
#     print("ln(P) 指标:")
#     print(f"R²  = {r2_ln:.6f}")
#     print(f"MSE = {mse_ln:.6f}")
#
#     print("\n实际蒸汽压 P 指标:")
#     print(f"R² (P)  = {r2_real:.6f}")
#     print(f"MSE (P) = {mse_real:.6f}")
#     print(f"ARD (P) = {ard_real:.2f}%")
#     print(f"误差 ≤ 1% 的点数: {within_1pct}")
#     print(f"误差 ≤ 5% 的点数: {within_5pct}")
#     print(f"误差 ≤ 10% 的点数: {within_10pct}")
#
#     compare_df = pd.DataFrame({
#         "Split": name,
#         "Compound_ID": compound_ids,
#         "Temperature_K": temp_values,
#         "ln(P)_true": y,
#         "ln(P)_pred": y_pred,
#         "Absolute_Error_lnP": np.abs(y - y_pred),
#         "Relative_Error_lnP (%)": 100 * np.abs((y - y_pred) / y),
#         "P_true": P_true,
#         "P_pred": P_pred,
#         "Absolute_Error_P": np.abs(P_true - P_pred),
#         "Relative_Error_P (%)": relative_error,
#         "Molecular_Weight": mw_values,
#         "Carbon_Number": nc_values,
#         "Slope_Term": slope_values
#     })
#
#     summary = {
#         "Split": name,
#         "R2_lnP": r2_ln,
#         "MSE_lnP": mse_ln,
#         "R2_P": r2_real,
#         "MSE_P": mse_real,
#         "ARD_P_%": ard_real,
#         "within_1pct": within_1pct,
#         "within_5pct": within_5pct,
#         "within_10pct": within_10pct
#     }
#
#     return compare_df, summary
#
# # ========= 14. 训练集 / 测试集评估 =========
# train_compare_df, train_summary = evaluate_dataset(
#     "train", X_train, y_train, id_train, T_train, MW_train_out, Nc_train_out, Slope_train_out, result.x
# )
#
# test_compare_df, test_summary = evaluate_dataset(
#     "test", X_test, y_test, id_test, T_test, MW_test_out, Nc_test_out, Slope_test_out, result.x
# )
#
# # ========= 15. 保存结果 =========
# all_compare_df = pd.concat([train_compare_df, test_compare_df], ignore_index=True)
# summary_df = pd.DataFrame([train_summary, test_summary])
#
# output_filename = "Gani_lnP_prediction_results_19group_train_test_split_by_compound.xlsx"
# with pd.ExcelWriter(output_filename, engine="xlsxwriter") as writer:
#     all_compare_df.to_excel(writer, sheet_name="predictions", index=False)
#     summary_df.to_excel(writer, sheet_name="summary", index=False)
#
# print(f"\n✅ 已保存预测结果为 {output_filename}")


import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from sklearn.linear_model import HuberRegressor
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split


# ========= 1. 数据加载 =========
df = pd.read_excel("vp209.xlsx", sheet_name="Sheet1")

# 保存物质ID
compound_ids_all_raw = df.iloc[:, 0].values

# 19个基团
Nk = df.iloc[:, 12:31].values
poly = PolynomialFeatures(degree=2, include_bias=False)
Nk_poly = poly.fit_transform(Nk)


# ========= 2. 沸点 Tb 子模型 =========
Tb0 = 222.543
Tb = df.iloc[:, 5].values

model_tb = HuberRegressor(max_iter=10000).fit(
    Nk_poly,
    np.exp(Tb / Tb0)
)

Tb_pred = Tb0 * np.log(
    np.clip(model_tb.predict(Nk_poly), 1e-6, None)
)


# ========= 3. 临界温度 Tc 子模型 =========
Tc_half = df["ASPEN Half Critical T"].values

gb_model_tc = GradientBoostingRegressor(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=4,
    random_state=0
)

gb_model_tc.fit(Nk_poly, Tc_half)
Tc_pred = gb_model_tc.predict(Nk_poly)


# ========= 4. 临界压力 Pc 子模型 =========
Pc_bar = df.iloc[:, 51].values
MW = df.iloc[:, 4].values.flatten()


def residual_pc(params, X, MW, Pc_true):
    beta = params[:-1]
    beta3 = params[-1]

    y_pred = X @ beta
    x_pred = y_pred + 0.108998

    x_pred = np.where(
        np.abs(x_pred) < 1e-8,
        np.sign(x_pred) * 1e-8 + (x_pred == 0) * 1e-8,
        x_pred
    )

    Pc_pred = (
        5.9827
        + (1 / x_pred) ** 2
        + beta3 * np.exp(1 / np.clip(MW, 1e-8, None))
    )

    return Pc_pred - Pc_true


params_init_pc = np.zeros(Nk_poly.shape[1] + 1)

result_pc = least_squares(
    residual_pc,
    x0=params_init_pc,
    args=(Nk_poly, MW, Pc_bar),
    max_nfev=5000
)

x_fit = Nk_poly @ result_pc.x[:-1] + 0.108998

x_fit = np.where(
    np.abs(x_fit) < 1e-8,
    np.sign(x_fit) * 1e-8 + (x_fit == 0) * 1e-8,
    x_fit
)

Pc_pred = (
    5.9827
    + (1 / x_fit) ** 2
    + result_pc.x[-1] * np.exp(1 / np.clip(MW, 1e-8, None))
) * 1e5


# ========= 5. 斜率特征构建 =========
Pb = 101325

denom = Tc_pred * 2 - Tb_pred
slope_all = np.full_like(Tb_pred, np.nan, dtype=float)

valid_slope_mask = (
    np.isfinite(Pc_pred)
    & (Pc_pred > 0)
    & np.isfinite(Tc_pred)
    & np.isfinite(Tb_pred)
    & (np.abs(denom) > 1e-12)
)

slope_all[valid_slope_mask] = (
    np.log(Pc_pred[valid_slope_mask]) - np.log(Pb)
) / denom[valid_slope_mask]

slope_all = slope_all.reshape(-1, 1)


# ========= 6. 准备数据集 =========
T = df.iloc[:, 31:41].values
P_vp = df.iloc[:, 41:51].values

MW = MW.reshape(-1, 1)
Nc = df.iloc[:, 10].values.reshape(-1, 1)
Ncs = df.iloc[:, 9].values.reshape(-1, 1)

valid_mask = np.isfinite(P_vp) & (P_vp > 0)
valid_mask = valid_mask.all(axis=1)

extra_valid_mask = (
    np.isfinite(Nk).all(axis=1)
    & np.isfinite(T).all(axis=1)
    & np.isfinite(MW).flatten()
    & np.isfinite(Nc).flatten()
    & np.isfinite(Ncs).flatten()
    & np.isfinite(slope_all).flatten()
)

final_valid_mask = valid_mask & extra_valid_mask

Nk = Nk[final_valid_mask]
T = T[final_valid_mask]
P_vp = P_vp[final_valid_mask]
MW = MW[final_valid_mask]
Nc = Nc[final_valid_mask]
Ncs = Ncs[final_valid_mask]
slope_all = slope_all[final_valid_mask]
compound_ids_all = compound_ids_all_raw[final_valid_mask]

print("========== 数据清洗后 ==========")
print(f"有效物质数: {len(compound_ids_all)}")


# ========= 7. 按物质 8:2 划分 =========
indices = np.arange(len(compound_ids_all))

train_idx, test_idx = train_test_split(
    indices,
    test_size=0.2,
    random_state=50
)

Nk_train, Nk_test = Nk[train_idx], Nk[test_idx]
MW_train, MW_test = MW[train_idx], MW[test_idx]
Nc_train, Nc_test = Nc[train_idx], Nc[test_idx]
Ncs_train, Ncs_test = Ncs[train_idx], Ncs[test_idx]
T_train_raw, T_test_raw = T[train_idx], T[test_idx]
P_train_raw, P_test_raw = P_vp[train_idx], P_vp[test_idx]
slope_train, slope_test = slope_all[train_idx], slope_all[test_idx]
id_train_raw, id_test_raw = compound_ids_all[train_idx], compound_ids_all[test_idx]

print("========== 按物质划分 ==========")
print(f"训练集物质数: {len(train_idx)}")
print(f"测试集物质数: {len(test_idx)}")


# ========= 8. 把每个物质展开成10个温度点 =========
def build_point_dataset(Nk, MW, Nc, Ncs, T, P_vp, slope_all, compound_ids):
    y = np.log(P_vp).flatten()

    slope_T = slope_all.repeat(10, axis=0) * T.flatten().reshape(-1, 1)

    X = np.hstack([
        Nk.repeat(10, axis=0),
        MW.repeat(10, axis=0),
        Nc.repeat(10, axis=0),
        Ncs.repeat(10, axis=0),
        T.flatten().reshape(-1, 1),
        slope_T
    ])

    expanded_ids = np.repeat(compound_ids, 10)
    expanded_T = T.flatten()
    expanded_MW = MW.repeat(10, axis=0).flatten()
    expanded_Nc = Nc.repeat(10, axis=0).flatten()
    expanded_slopeT = slope_T.flatten()

    finite_mask = np.isfinite(y) & np.isfinite(X).all(axis=1)

    return (
        X[finite_mask, :],
        y[finite_mask],
        expanded_ids[finite_mask],
        expanded_T[finite_mask],
        expanded_MW[finite_mask],
        expanded_Nc[finite_mask],
        expanded_slopeT[finite_mask]
    )


X_train, y_train, id_train, T_train, MW_train_out, Nc_train_out, Slope_train_out = build_point_dataset(
    Nk_train,
    MW_train,
    Nc_train,
    Ncs_train,
    T_train_raw,
    P_train_raw,
    slope_train,
    id_train_raw
)

X_test, y_test, id_test, T_test, MW_test_out, Nc_test_out, Slope_test_out = build_point_dataset(
    Nk_test,
    MW_test,
    Nc_test,
    Ncs_test,
    T_test_raw,
    P_test_raw,
    slope_test,
    id_test_raw
)

print(f"训练集样本点数: {len(X_train)}")
print(f"测试集样本点数: {len(X_test)}")


# ========= 9. 前向预测函数 =========
def model_predict(params, X):
    Nk = X[:, :19]
    MW = X[:, 19].reshape(-1, 1)
    Nc = X[:, 20].reshape(-1, 1)
    Ncs = X[:, 21].reshape(-1, 1)
    T = np.clip(X[:, 22].reshape(-1, 1), 1e-6, None)
    slope_T = X[:, 23].reshape(-1, 1)

    A1k = params[:19]
    A2k = params[19:38]
    s0, s1 = params[38], params[39]
    alpha, f0, f1 = params[40], params[41], params[42]
    B1k = params[43:62]
    B2k = params[62:81]
    beta = params[81]
    C1k = params[82:101]
    C2k = params[101:120]
    gamma = params[120]

    term_A = (
        np.sum(Nk * (A1k + MW * A2k), axis=1)
        + s0
        + s1 * Ncs.flatten()
        + alpha * (f0 + f1 * Nc.flatten())
    )

    term_B = (
        np.sum(Nk * (B1k + MW * B2k), axis=1)
        + beta * (f0 + f1 * Nc.flatten())
    )

    term_C = np.sum(Nk * (C1k + MW * C2k), axis=1)

    y_pred = (
        term_A
        + term_B / T.flatten()
        + term_C * np.log(T.flatten())
        + gamma * slope_T.flatten()
    )

    return y_pred


# ========= 10. 残差函数 =========
def residuals(params, X, y):
    return y - model_predict(params, X)


# ========= 11. 初始参数设置 =========
params_init = np.zeros(121)

params_init[:19] = [
    13.65853808, 3.28418546, -659.6444719, 12.37483133, 4.81265536,
    2.91551829, 97.31954706, 87.70370771, 95.98266611, 3.887261236,
    27.43160868, 207.1319101, 47.22447225, 4687.002401, 3.637088127,
    1523.380387, 3162.746842, 12062.07738, -8900.847866
]

params_init[19:38] = [
    -0.015716978, 0.009075383, 11.48620132, -21.10261532, -0.011767963,
    0.002675368, -0.109835685, -0.010236179, -0.171652319, 0.005908914,
    10.467947, -5.994107293, -0.112649727, -17.43861742, 0.001820612,
    -12.29192011, -5.831333421, -30.99113155, 26.51752291
]

params_init[38:43] = [17.60905342, -0.000738906, 0.018089414, 0.0, 1.0]

params_init[43:62] = [
    -1346.02436, -683.1104648, 67218.65971, -1384.512471, -884.3388538,
    -1241.799972, -8807.96886, -9868.206835, -9972.171472, -764.4721254,
    -2768.98, -22960.24319, -4496.012972, -507785.7608, -2221.349576,
    -157397.6395, -350388.1207, -1307700.942, 957312.8216
]

params_init[62:81] = [
    1.451298512, -0.736859315, -584.0308556, 3.123573902, 0.887401846,
    0.122658761, 8.501979442, 0.898999866, 15.05201845, -0.396917177,
    6.455487385, 318.8958283, 9.649044453, 2010.74563, 0.550921963,
    1486.747823, 523.9930512, 3372.517851, -2848.526234
]

params_init[81] = -6.750229278

params_init[82:101] = [
    -1.846676986, -0.38538898, 85.74714557, -1.76399843, -0.569402352,
    -0.250943128, -13.054703, -11.40790845, -12.58276815, -0.468789896,
    -3.52337599, -26.44154671, -6.353423865, -606.0715674, -0.130106514,
    -198.3318276, -407.7121286, -1560.004645, 1152.427648
]

params_init[101:120] = [
    0.002016846, -0.001221385, 7.344413404, 0.894155383, 0.001594902,
    -0.000468558, 0.01491123, 0.001327088, 0.022906548, -0.0008161,
    -0.43609896, -3.639773727, 0.015093667, 11.71908672, -0.000385519,
    -3.450680198, -14.53413618, 9.827970088, 2.387602073
]

params_init[120] = 1.0


# ========= 12. 拟合（只用训练集） =========
print("\n使用训练集拟合中，请稍候...")

result = least_squares(
    residuals,
    x0=params_init,
    args=(X_train, y_train),
    max_nfev=10000
)


# ========= 13. 评估函数 =========
def evaluate_dataset(
    name,
    X,
    y,
    compound_ids,
    temp_values,
    mw_values,
    nc_values,
    slope_values,
    params,
    strict_less=False
):
    y_pred = model_predict(params, X)

    # ln(P) 指标
    mse_ln = mean_squared_error(y, y_pred)
    r2_ln = r2_score(y, y_pred)

    # 实际蒸汽压 P 指标
    P_true = np.exp(y)
    P_pred = np.exp(y_pred)

    mse_real = mean_squared_error(P_true, P_pred)
    r2_real = r2_score(P_true, P_pred)

    relative_error = np.abs((P_pred - P_true) / P_true) * 100
    ard_real = np.mean(relative_error)

    if strict_less:
        within_1pct = np.sum(relative_error < 1)
        within_5pct = np.sum(relative_error < 5)
        within_10pct = np.sum(relative_error < 10)
    else:
        within_1pct = np.sum(relative_error <= 1)
        within_5pct = np.sum(relative_error <= 5)
        within_10pct = np.sum(relative_error <= 10)

    print(f"\n========== {name} ==========")
    print("ln(P) 指标:")
    print(f"R²  = {r2_ln:.6f}")
    print(f"MSE = {mse_ln:.6f}")

    print("\n实际蒸汽压 P 指标:")
    print(f"R² (P)  = {r2_real:.6f}")
    print(f"MSE (P) = {mse_real:.6f}")
    print(f"ARD (P) = {ard_real:.2f}%")

    if strict_less:
        print(f"误差 < 1% 的点数: {within_1pct}")
        print(f"误差 < 5% 的点数: {within_5pct}")
        print(f"误差 < 10% 的点数: {within_10pct}")
    else:
        print(f"误差 ≤ 1% 的点数: {within_1pct}")
        print(f"误差 ≤ 5% 的点数: {within_5pct}")
        print(f"误差 ≤ 10% 的点数: {within_10pct}")

    compare_df = pd.DataFrame({
        "Split": name,
        "Compound_ID": compound_ids,
        "Temperature_K": temp_values,
        "ln(P)_true": y,
        "ln(P)_pred": y_pred,
        "Absolute_Error_lnP": np.abs(y - y_pred),
        "Relative_Error_lnP (%)": 100 * np.abs((y - y_pred) / y),
        "P_true": P_true,
        "P_pred": P_pred,
        "Absolute_Error_P": np.abs(P_true - P_pred),
        "Relative_Error_P (%)": relative_error,
        "Molecular_Weight": mw_values,
        "Carbon_Number": nc_values,
        "Slope_Term": slope_values
    })

    summary = {
        "Split": name,
        "R2_lnP": r2_ln,
        "MSE_lnP": mse_ln,
        "R2_P": r2_real,
        "MSE_P": mse_real,
        "ARD_P_%": ard_real,
        "within_1pct": within_1pct,
        "within_5pct": within_5pct,
        "within_10pct": within_10pct
    }

    return compare_df, summary


# ========= 14. 训练集 / 测试集评估 =========
train_compare_df, train_summary = evaluate_dataset(
    "train",
    X_train,
    y_train,
    id_train,
    T_train,
    MW_train_out,
    Nc_train_out,
    Slope_train_out,
    result.x,
    strict_less=False
)

test_compare_df, test_summary = evaluate_dataset(
    "test",
    X_test,
    y_test,
    id_test,
    T_test,
    MW_test_out,
    Nc_test_out,
    Slope_test_out,
    result.x,
    strict_less=False
)


# ========= 14.1 完整数据集统计：训练集 + 测试集 =========
X_all = np.vstack([X_train, X_test])
y_all = np.concatenate([y_train, y_test])
id_all = np.concatenate([id_train, id_test])
T_all = np.concatenate([T_train, T_test])
MW_all_out = np.concatenate([MW_train_out, MW_test_out])
Nc_all_out = np.concatenate([Nc_train_out, Nc_test_out])
Slope_all_out = np.concatenate([Slope_train_out, Slope_test_out])

all_compare_df, all_summary = evaluate_dataset(
    "all_train_plus_test",
    X_all,
    y_all,
    id_all,
    T_all,
    MW_all_out,
    Nc_all_out,
    Slope_all_out,
    result.x,
    strict_less=True
)

print("\n完整数据集实际蒸汽压 P 预测偏差 1%，5%，10%分别为：")
print(all_summary["within_1pct"])
print(all_summary["within_5pct"])
print(all_summary["within_10pct"])


# ========= 15. 保存结果 =========
prediction_df = pd.concat(
    [train_compare_df, test_compare_df],
    ignore_index=True
)

summary_df = pd.DataFrame([
    train_summary,
    test_summary,
    all_summary
])

output_filename = "Gani_lnP_prediction_results_19group_train_test_split_by_compound.xlsx"

with pd.ExcelWriter(output_filename, engine="xlsxwriter") as writer:
    prediction_df.to_excel(writer, sheet_name="predictions", index=False)
    all_compare_df.to_excel(writer, sheet_name="all_predictions", index=False)
    summary_df.to_excel(writer, sheet_name="summary", index=False)

print(f"\n已保存预测结果为 {output_filename}")


# ========= 16. 输出模型结构记录 =========
print("\n当前蒸汽压 slope 显式模型结构:")
print("Tb_submodel: HuberRegressor(max_iter=10000), input = PolynomialFeatures(Nk, degree=2)")
print("Tc_submodel: GradientBoostingRegressor(n_estimators=300, learning_rate=0.05, max_depth=4, random_state=0), input = PolynomialFeatures(Nk, degree=2)")
print("Pc_submodel: least_squares explicit Pc equation, input = PolynomialFeatures(Nk, degree=2) + MW")
print("Final model: least_squares explicit lnP equation with 121 parameters")
print("Final input = Nk + MW + Nc + Ncs + T + slope*T")
print("Final lnP = A(Nk,MW,Nc,Ncs) + B(Nk,MW,Nc)/T + C(Nk,MW)*ln(T) + gamma*slope*T")