# # import numpy as np
# # import pandas as pd
# #
# # from sklearn.metrics import mean_squared_error, r2_score
# # from sklearn.preprocessing import PolynomialFeatures
# # from sklearn.linear_model import HuberRegressor
# # from sklearn.ensemble import RandomForestRegressor
# # from scipy.optimize import least_squares
# # from sklearn.model_selection import train_test_split, GroupKFold, cross_val_score
# #
# #
# # # ========== 读取数据 ========== #
# # df = pd.read_excel("vp209.xlsx", sheet_name="Sheet1").copy()
# #
# #
# # # ========== 定义列 ========== #
# # id_col = df.columns[0]
# #
# # group_cols = list(df.columns[12:31])   # 第13~31列：19个基团
# # temp_cols = list(df.columns[31:41])    # 第32~41列：10个温度
# # v_cols = list(df.columns[41:51])       # 第42~51列：10个蒸汽压
# #
# # tb_col_idx = 5
# # mw_col_idx = 4
# # pc_col_idx = 51
# #
# #
# # # ========== 数据预处理 ========== #
# # for col in temp_cols + v_cols:
# #     df[col] = pd.to_numeric(df[col], errors="coerce")
# #
# # df.iloc[:, tb_col_idx] = pd.to_numeric(df.iloc[:, tb_col_idx], errors="coerce")
# # df.iloc[:, mw_col_idx] = pd.to_numeric(df.iloc[:, mw_col_idx], errors="coerce")
# # df.iloc[:, pc_col_idx] = pd.to_numeric(df.iloc[:, pc_col_idx], errors="coerce")
# #
# # Nk_all = df.iloc[:, 12:31].apply(pd.to_numeric, errors="coerce").values
# # T_all = df.iloc[:, 31:41].apply(pd.to_numeric, errors="coerce").values
# # P_vp_all = df.iloc[:, 41:51].apply(pd.to_numeric, errors="coerce").values
# #
# #
# # # ========== 创建有效掩码 ==========
# # valid_mask = np.isfinite(P_vp_all) & (P_vp_all > 0)
# # valid_mask = valid_mask.all(axis=1)
# #
# # df_valid = df.loc[valid_mask].copy().reset_index(drop=True)
# #
# # print(f"有效物质数: {len(df_valid)}")
# #
# #
# # # ========== 按物质 8:2 划分 ==========
# # unique_materials = df_valid[id_col].values
# #
# # train_materials, test_materials = train_test_split(
# #     unique_materials,
# #     test_size=0.2,
# #     random_state=42
# # )
# #
# # train_materials = set(train_materials)
# # test_materials = set(test_materials)
# #
# # train_df = df_valid[df_valid[id_col].isin(train_materials)].copy().reset_index(drop=True)
# # test_df = df_valid[df_valid[id_col].isin(test_materials)].copy().reset_index(drop=True)
# #
# # print(f"训练集物质数: {len(train_df)}, 测试集物质数: {len(test_df)}")
# #
# #
# # # ========== 工具函数 ==========
# # def get_arrays(df_part):
# #     return {
# #         "ids": df_part[id_col].values,
# #         "Nk": df_part.iloc[:, 12:31].apply(pd.to_numeric, errors="coerce").values,
# #         "T": df_part.iloc[:, 31:41].apply(pd.to_numeric, errors="coerce").values,
# #         "P_vp": df_part.iloc[:, 41:51].apply(pd.to_numeric, errors="coerce").values,
# #         "Tb": pd.to_numeric(df_part.iloc[:, tb_col_idx], errors="coerce").values,
# #         "MW": pd.to_numeric(df_part.iloc[:, mw_col_idx], errors="coerce").values.reshape(-1, 1),
# #         "Pc_bar": pd.to_numeric(df_part.iloc[:, pc_col_idx], errors="coerce").values,
# #     }
# #
# #
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
# #
# #
# # def eval_pressure_metrics(y_true_log, y_pred_log, model_name, split_name):
# #     y_true_log = np.asarray(y_true_log, dtype=float)
# #     y_pred_log = np.asarray(y_pred_log, dtype=float)
# #
# #     mask = np.isfinite(y_true_log) & np.isfinite(y_pred_log)
# #     y_true_log = y_true_log[mask]
# #     y_pred_log = y_pred_log[mask]
# #
# #     P_true = np.exp(y_true_log)
# #     P_pred = np.exp(y_pred_log)
# #
# #     r2_ln = r2_score(y_true_log, y_pred_log)
# #     mse_ln = mean_squared_error(y_true_log, y_pred_log)
# #
# #     r2_P = r2_score(P_true, P_pred)
# #     mse_P = mean_squared_error(P_true, P_pred)
# #
# #     rel_err = np.abs((P_pred - P_true) / P_true) * 100
# #     ard = np.mean(rel_err)
# #
# #     within_1pct = np.sum(rel_err <= 1)
# #     within_5pct = np.sum(rel_err <= 5)
# #     within_10pct = np.sum(rel_err <= 10)
# #
# #     print(f"\n{model_name} - {split_name}")
# #     print(f"ln(P)  R² = {r2_ln:.6f}, MSE = {mse_ln:.6f}")
# #     print(f"P      R² = {r2_P:.6f}, MSE = {mse_P:.6f}, ARD = {ard:.2f}%")
# #     print(f"误差 ≤ 1% : {within_1pct} 点")
# #     print(f"误差 ≤ 5% : {within_5pct} 点")
# #     print(f"误差 ≤ 10%: {within_10pct} 点")
# #
# #     return {
# #         "Model": model_name,
# #         "Split": split_name,
# #         "R2_lnP": r2_ln,
# #         "MSE_lnP": mse_ln,
# #         "R2_P": r2_P,
# #         "MSE_P": mse_P,
# #         "ARD_%": ard,
# #         "within_1pct": within_1pct,
# #         "within_5pct": within_5pct,
# #         "within_10pct": within_10pct
# #     }, rel_err
# #
# #
# # train_arr = get_arrays(train_df)
# # test_arr = get_arrays(test_df)
# #
# #
# # # ========== 构建 Nk_poly（只在训练集 fit） ==========
# # poly = PolynomialFeatures(degree=2, include_bias=False)
# #
# # Nk_poly_train = poly.fit_transform(train_arr["Nk"])
# # Nk_poly_test = poly.transform(test_arr["Nk"])
# #
# #
# # # ========== Tb 模型（只用训练集） ==========
# # Tb0 = 222.543
# #
# # tb_train_mask = np.isfinite(train_arr["Tb"]) & np.isfinite(Nk_poly_train).all(axis=1)
# # tb_test_mask = np.isfinite(test_arr["Tb"]) & np.isfinite(Nk_poly_test).all(axis=1)
# #
# # model_tb = HuberRegressor(max_iter=10000)
# #
# # model_tb.fit(
# #     Nk_poly_train[tb_train_mask],
# #     np.exp(train_arr["Tb"][tb_train_mask] / Tb0)
# # )
# #
# # Tb_pred_train = Tb0 * np.log(
# #     np.clip(model_tb.predict(Nk_poly_train), 1e-6, None)
# # )
# #
# # Tb_pred_test = Tb0 * np.log(
# #     np.clip(model_tb.predict(Nk_poly_test), 1e-6, None)
# # )
# #
# # tb_metrics_train = evaluate_scalar_regression(
# #     train_arr["Tb"][tb_train_mask],
# #     Tb_pred_train[tb_train_mask],
# #     "Tb_submodel",
# #     "train"
# # )
# #
# # tb_metrics_test = evaluate_scalar_regression(
# #     test_arr["Tb"][tb_test_mask],
# #     Tb_pred_test[tb_test_mask],
# #     "Tb_submodel",
# #     "test"
# # )
# #
# #
# # # ========== Pc 模型（只用原始19个基团，不用 poly） ==========
# # Pc_bar_train = train_arr["Pc_bar"]
# # Pc_bar_test = test_arr["Pc_bar"]
# #
# # MW_train_flat = train_arr["MW"].flatten()
# # MW_test_flat = test_arr["MW"].flatten()
# #
# # Pc_X_train = train_arr["Nk"]
# # Pc_X_test = test_arr["Nk"]
# #
# #
# # def residual_pc(params, X, MW, Pc_true):
# #     beta = params[:-1]
# #     beta3 = params[-1]
# #
# #     y_pred = X @ beta
# #     x_pred = y_pred + 0.108998
# #
# #     x_pred = np.where(
# #         np.abs(x_pred) < 1e-8,
# #         np.sign(x_pred) * 1e-8 + (x_pred == 0) * 1e-8,
# #         x_pred
# #     )
# #
# #     Pc_pred = (
# #         5.9827
# #         + (1 / x_pred) ** 2
# #         + beta3 * np.exp(1 / np.clip(MW, 1e-8, None))
# #     )
# #
# #     return Pc_pred - Pc_true
# #
# #
# # pc_train_mask = (
# #     np.isfinite(Pc_bar_train)
# #     & np.isfinite(MW_train_flat)
# #     & np.isfinite(Pc_X_train).all(axis=1)
# # )
# #
# # pc_test_mask = (
# #     np.isfinite(Pc_bar_test)
# #     & np.isfinite(MW_test_flat)
# #     & np.isfinite(Pc_X_test).all(axis=1)
# # )
# #
# # params_init_pc = np.zeros(Pc_X_train.shape[1] + 1)
# #
# # result_pc = least_squares(
# #     residual_pc,
# #     x0=params_init_pc,
# #     args=(
# #         Pc_X_train[pc_train_mask],
# #         MW_train_flat[pc_train_mask],
# #         Pc_bar_train[pc_train_mask]
# #     ),
# #     max_nfev=5000
# # )
# #
# #
# # def predict_pc_pa(Pc_X, MW_flat, result_pc):
# #     x_fit = Pc_X @ result_pc.x[:-1] + 0.108998
# #
# #     x_fit = np.where(
# #         np.abs(x_fit) < 1e-8,
# #         np.sign(x_fit) * 1e-8 + (x_fit == 0) * 1e-8,
# #         x_fit
# #     )
# #
# #     Pc_pred = (
# #         5.9827
# #         + (1 / x_fit) ** 2
# #         + result_pc.x[-1] * np.exp(1 / np.clip(MW_flat, 1e-8, None))
# #     )
# #
# #     return Pc_pred * 1e5
# #
# #
# # Pc_pred_train = predict_pc_pa(Pc_X_train, MW_train_flat, result_pc)
# # Pc_pred_test = predict_pc_pa(Pc_X_test, MW_test_flat, result_pc)
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
# #
# #
# # # ========== 蒸汽压主模型：基线 A_k（只用训练集） ==========
# # G_train = train_arr["Nk"]
# # G_test = test_arr["Nk"]
# #
# # X_rows_train = []
# # y_rows_train = []
# # group_ids_train = []
# #
# # for i in range(len(train_df)):
# #     for j, (tcol, vcol) in enumerate(zip(temp_cols, v_cols)):
# #         Tj = train_df.at[i, tcol]
# #         Vj = train_df.at[i, vcol]
# #
# #         if np.isnan(Tj) or np.isnan(Vj) or Vj <= 0:
# #             continue
# #
# #         Tb_i = Tb_pred_train[i]
# #         V_ref = 101325.0
# #
# #         Xj = (Tj - Tb_i) * G_train[i]
# #         yj = np.log(Vj) - np.log(V_ref)
# #
# #         X_rows_train.append(Xj)
# #         y_rows_train.append(yj)
# #         group_ids_train.append(train_df.at[i, id_col])
# #
# # X_A_train = np.array(X_rows_train, dtype=float)
# # y_A_train = np.array(y_rows_train, dtype=float)
# # group_ids_train = np.array(group_ids_train)
# #
# # A_solver = HuberRegressor(fit_intercept=False, max_iter=5000)
# # A_solver.fit(X_A_train, y_A_train)
# #
# # A_vec = A_solver.coef_
# #
# #
# # # ========== 生成基准蒸汽压预测（训练/测试分别生成） ==========
# # def build_baseline_predictions(df_part, G_part, Tb_pred_part):
# #     V_pred_baseline = pd.DataFrame(index=df_part.index, columns=v_cols, dtype=float)
# #
# #     for i in range(len(df_part)):
# #         Tb_i = Tb_pred_part[i]
# #         V_ref = 101325.0
# #
# #         for tcol, vcol in zip(temp_cols, v_cols):
# #             Tj = df_part.at[i, tcol]
# #
# #             if np.isnan(Tj):
# #                 V_pred_baseline.at[i, vcol] = np.nan
# #                 continue
# #
# #             Xj = (Tj - Tb_i) * G_part[i]
# #             ln_V_pred = np.log(V_ref) + Xj @ A_vec
# #
# #             V_pred_baseline.at[i, vcol] = np.exp(ln_V_pred)
# #
# #     return V_pred_baseline
# #
# #
# # V_pred_baseline_train = build_baseline_predictions(
# #     train_df,
# #     G_train,
# #     Tb_pred_train
# # )
# #
# # V_pred_baseline_test = build_baseline_predictions(
# #     test_df,
# #     G_test,
# #     Tb_pred_test
# # )
# #
# #
# # # ========== 残差 RF 模型（只用训练集） ==========
# # print("\n训练残差 RF 模型...")
# #
# #
# # def build_residual_dataset(
# #     df_part,
# #     G_part,
# #     Tb_pred_part,
# #     Pc_pred_part,
# #     MW_part,
# #     V_pred_baseline_part
# # ):
# #     residual_features = []
# #     residual_targets = []
# #     sample_info = []
# #     sample_groups = []
# #
# #     for tcol, vcol in zip(temp_cols, v_cols):
# #         Tj = df_part[tcol].to_numpy(dtype=float)
# #         Vj = df_part[vcol].to_numpy(dtype=float)
# #
# #         msk = (
# #             (~np.isnan(Tj))
# #             & (~np.isnan(Vj))
# #             & (Vj > 0)
# #             & (~V_pred_baseline_part[vcol].isna().to_numpy())
# #         )
# #
# #         for i in np.where(msk)[0]:
# #             baseline_pred = V_pred_baseline_part.at[i, vcol]
# #
# #             if not np.isfinite(baseline_pred) or baseline_pred <= 0:
# #                 continue
# #
# #             base_features = list(G_part[i])
# #
# #             temp_features = [
# #                 Tj[i],
# #                 Tj[i] - Tb_pred_part[i],
# #                 Tj[i] / Tb_pred_part[i] if Tb_pred_part[i] > 0 else 0.0,
# #                 np.log(Tj[i]) if Tj[i] > 0 else 0.0,
# #             ]
# #
# #             baseline_features = [
# #                 np.log(baseline_pred)
# #             ]
# #
# #             ref_features = [
# #                 Tb_pred_part[i],
# #                 np.log(101325.0),
# #                 Pc_pred_part[i] if i < len(Pc_pred_part) else 0.0,
# #             ]
# #
# #             mw_features = [
# #                 MW_part[i][0] if i < len(MW_part) else 0.0
# #             ]
# #
# #             all_features = (
# #                 base_features
# #                 + temp_features
# #                 + baseline_features
# #                 + ref_features
# #                 + mw_features
# #             )
# #
# #             residual_features.append(all_features)
# #
# #             # 残差目标：ln(V_actual) - ln(V_baseline)
# #             residual = np.log(Vj[i]) - np.log(baseline_pred)
# #             residual_targets.append(residual)
# #
# #             sample_info.append((i, tcol, vcol))
# #             sample_groups.append(df_part.at[i, id_col])
# #
# #     residual_features = np.array(residual_features, dtype=float)
# #     residual_targets = np.array(residual_targets, dtype=float)
# #     sample_groups = np.array(sample_groups)
# #
# #     return residual_features, residual_targets, sample_info, sample_groups
# #
# #
# # residual_X_train, residual_y_train, sample_info_train, residual_groups_train = build_residual_dataset(
# #     train_df,
# #     G_train,
# #     Tb_pred_train,
# #     Pc_pred_train,
# #     train_arr["MW"],
# #     V_pred_baseline_train
# # )
# #
# # print(f"训练集残差特征形状: {residual_X_train.shape}")
# # print(f"训练集残差目标形状: {residual_y_train.shape}")
# #
# #
# # # RF 是树模型，不需要 StandardScaler
# # residual_model = RandomForestRegressor(
# #     n_estimators=500,
# #     max_depth=None,
# #     min_samples_split=2,
# #     min_samples_leaf=1,
# #     max_features="sqrt",
# #     bootstrap=True,
# #     random_state=42,
# #     n_jobs=-1
# # )
# #
# #
# # # ========== 残差 RF 的 GroupKFold 交叉验证 ==========
# # n_groups = len(np.unique(residual_groups_train))
# #
# # if n_groups >= 2:
# #     n_splits = min(5, n_groups)
# #     group_cv = GroupKFold(n_splits=n_splits)
# #
# #     cv_scores = cross_val_score(
# #         residual_model,
# #         residual_X_train,
# #         residual_y_train,
# #         cv=group_cv,
# #         groups=residual_groups_train,
# #         scoring="r2",
# #         n_jobs=-1
# #     )
# #
# #     print(
# #         f"残差 RF 模型 GroupKFold R²: "
# #         f"{cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})"
# #     )
# # else:
# #     cv_scores = None
# #     print("训练集物质数不足，跳过残差 RF 模型 GroupKFold 交叉验证。")
# #
# #
# # print("\n开始训练残差 RF 模型...")
# # residual_model.fit(residual_X_train, residual_y_train)
# #
# # print("\n残差 RF 模型参数:")
# # print(residual_model)
# #
# #
# # # ========== 生成最终预测（基准 + RF残差修正） ==========
# # def build_final_predictions(
# #     df_part,
# #     G_part,
# #     Tb_pred_part,
# #     Pc_pred_part,
# #     MW_part,
# #     V_pred_baseline_part
# # ):
# #     V_pred_final = pd.DataFrame(index=df_part.index, columns=v_cols, dtype=float)
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
# #             baseline_pred = V_pred_baseline_part.at[i, vcol]
# #
# #             if pd.isna(baseline_pred) or baseline_pred <= 0:
# #                 continue
# #
# #             base_features = list(G_part[i])
# #
# #             temp_features = [
# #                 Tj[i],
# #                 Tj[i] - Tb_pred_part[i],
# #                 Tj[i] / Tb_pred_part[i] if Tb_pred_part[i] > 0 else 0.0,
# #                 np.log(Tj[i]) if Tj[i] > 0 else 0.0,
# #             ]
# #
# #             baseline_features = [
# #                 np.log(baseline_pred)
# #             ]
# #
# #             ref_features = [
# #                 Tb_pred_part[i],
# #                 np.log(101325.0),
# #                 Pc_pred_part[i] if i < len(Pc_pred_part) else 0.0,
# #             ]
# #
# #             mw_features = [
# #                 MW_part[i][0] if i < len(MW_part) else 0.0
# #             ]
# #
# #             all_features = (
# #                 base_features
# #                 + temp_features
# #                 + baseline_features
# #                 + ref_features
# #                 + mw_features
# #             )
# #
# #             features_list.append(all_features)
# #             valid_indices.append(i)
# #
# #         if len(features_list) > 0:
# #             features_array = np.array(features_list, dtype=float)
# #
# #             # RF 直接预测残差，不需要 scaler.transform
# #             residual_pred = residual_model.predict(features_array)
# #
# #             for idx, residual_val in zip(valid_indices, residual_pred):
# #                 baseline_pred = V_pred_baseline_part.at[idx, vcol]
# #
# #                 # ln(V_final) = ln(V_baseline) + residual_pred
# #                 ln_V_final = np.log(baseline_pred) + residual_val
# #
# #                 V_pred_final.at[idx, vcol] = np.exp(ln_V_final)
# #
# #     return V_pred_final
# #
# #
# # V_pred_final_train = build_final_predictions(
# #     train_df,
# #     G_train,
# #     Tb_pred_train,
# #     Pc_pred_train,
# #     train_arr["MW"],
# #     V_pred_baseline_train
# # )
# #
# # V_pred_final_test = build_final_predictions(
# #     test_df,
# #     G_test,
# #     Tb_pred_test,
# #     Pc_pred_test,
# #     test_arr["MW"],
# #     V_pred_baseline_test
# # )
# #
# #
# # # ========== 评估：基线模型 / 最终模型（训练集、测试集分开） ==========
# # def collect_log_true_pred(df_part, pred_df):
# #     y_true_log = []
# #     y_pred_log = []
# #
# #     for vcol in v_cols:
# #         actual = df_part[vcol].to_numpy(dtype=float)
# #         pred = pred_df[vcol].to_numpy(dtype=float)
# #
# #         m = (
# #             np.isfinite(actual)
# #             & np.isfinite(pred)
# #             & (actual > 0)
# #             & (pred > 0)
# #         )
# #
# #         if np.any(m):
# #             y_true_log.append(np.log(actual[m]))
# #             y_pred_log.append(np.log(pred[m]))
# #
# #     if len(y_true_log) == 0:
# #         return np.array([]), np.array([])
# #
# #     return np.concatenate(y_true_log), np.concatenate(y_pred_log)
# #
# #
# # y_train_true_base, y_train_pred_base = collect_log_true_pred(
# #     train_df,
# #     V_pred_baseline_train
# # )
# #
# # y_test_true_base, y_test_pred_base = collect_log_true_pred(
# #     test_df,
# #     V_pred_baseline_test
# # )
# #
# # baseline_metrics_train, _ = eval_pressure_metrics(
# #     y_train_true_base,
# #     y_train_pred_base,
# #     "Baseline_model",
# #     "train"
# # )
# #
# # baseline_metrics_test, _ = eval_pressure_metrics(
# #     y_test_true_base,
# #     y_test_pred_base,
# #     "Baseline_model",
# #     "test"
# # )
# #
# #
# # y_train_true_final, y_train_pred_final = collect_log_true_pred(
# #     train_df,
# #     V_pred_final_train
# # )
# #
# # y_test_true_final, y_test_pred_final = collect_log_true_pred(
# #     test_df,
# #     V_pred_final_test
# # )
# #
# # final_metrics_train, rel_err_train = eval_pressure_metrics(
# #     y_train_true_final,
# #     y_train_pred_final,
# #     "Final_model_RF_residual",
# #     "train"
# # )
# #
# # final_metrics_test, rel_err_test = eval_pressure_metrics(
# #     y_test_true_final,
# #     y_test_pred_final,
# #     "Final_model_RF_residual",
# #     "test"
# # )
# #
# #
# # print("\n=== 分温度点评估（最终模型，训练集）===")
# #
# # for tcol, vcol in zip(temp_cols, v_cols):
# #     actual = train_df[vcol].to_numpy(dtype=float)
# #     pred = V_pred_final_train[vcol].to_numpy(dtype=float)
# #
# #     m = (
# #         np.isfinite(actual)
# #         & np.isfinite(pred)
# #         & (actual > 0)
# #         & (pred > 0)
# #     )
# #
# #     if np.any(m):
# #         mse_temp = mean_squared_error(np.log(actual[m]), np.log(pred[m]))
# #         r2_temp = r2_score(np.log(actual[m]), np.log(pred[m]))
# #
# #         print(f"{tcol}: MSE_ln = {mse_temp:.6f}, R²_ln = {r2_temp:.6f}")
# #
# #
# # print("\n=== 分温度点评估（最终模型，测试集）===")
# #
# # for tcol, vcol in zip(temp_cols, v_cols):
# #     actual = test_df[vcol].to_numpy(dtype=float)
# #     pred = V_pred_final_test[vcol].to_numpy(dtype=float)
# #
# #     m = (
# #         np.isfinite(actual)
# #         & np.isfinite(pred)
# #         & (actual > 0)
# #         & (pred > 0)
# #     )
# #
# #     if np.any(m):
# #         mse_temp = mean_squared_error(np.log(actual[m]), np.log(pred[m]))
# #         r2_temp = r2_score(np.log(actual[m]), np.log(pred[m]))
# #
# #         print(f"{tcol}: MSE_ln = {mse_temp:.6f}, R²_ln = {r2_temp:.6f}")
# #
# #
# # # ========== 保存结果 ==========
# # def build_long_compare(
# #     df_part,
# #     split_name,
# #     Tb_pred_part,
# #     Pc_pred_part,
# #     V_pred_baseline_part,
# #     V_pred_final_part
# # ):
# #     rows = []
# #
# #     for idx in range(len(df_part)):
# #         ID = df_part.at[idx, id_col]
# #
# #         for j, (tcol, vcol) in enumerate(zip(temp_cols, v_cols), start=1):
# #             T_val = df_part.at[idx, tcol]
# #             V_act = df_part.at[idx, vcol]
# #
# #             V_base = (
# #                 V_pred_baseline_part.at[idx, vcol]
# #                 if pd.notna(V_pred_baseline_part.at[idx, vcol])
# #                 else np.nan
# #             )
# #
# #             V_final = (
# #                 V_pred_final_part.at[idx, vcol]
# #                 if pd.notna(V_pred_final_part.at[idx, vcol])
# #                 else np.nan
# #             )
# #
# #             if pd.notna(V_act) and pd.notna(V_base) and V_act > 0 and V_base > 0:
# #                 err_base_log = np.log(V_base) - np.log(V_act)
# #             else:
# #                 err_base_log = np.nan
# #
# #             if pd.notna(V_act) and pd.notna(V_final) and V_act > 0 and V_final > 0:
# #                 err_final_log = np.log(V_final) - np.log(V_act)
# #             else:
# #                 err_final_log = np.nan
# #
# #             residual_correction = (
# #                 np.log(V_final) - np.log(V_base)
# #                 if (
# #                     pd.notna(V_final)
# #                     and pd.notna(V_base)
# #                     and V_final > 0
# #                     and V_base > 0
# #                 )
# #                 else np.nan
# #             )
# #
# #             rows.append({
# #                 "Split": split_name,
# #                 id_col: ID,
# #                 "temp_index": j,
# #                 "temp_col": tcol,
# #                 "T": T_val,
# #                 "Vapor_Pressure_actual": V_act,
# #                 "Vapor_Pressure_baseline": V_base,
# #                 "Vapor_Pressure_final": V_final,
# #                 "error_baseline_log": err_base_log,
# #                 "error_final_log": err_final_log,
# #                 "residual_correction_log": residual_correction,
# #                 "T_ref": Tb_pred_part[idx],
# #                 "Pc_pred": Pc_pred_part[idx]
# #             })
# #
# #     return pd.DataFrame(rows)
# #
# #
# # long_train = build_long_compare(
# #     train_df,
# #     "train",
# #     Tb_pred_train,
# #     Pc_pred_train,
# #     V_pred_baseline_train,
# #     V_pred_final_train
# # )
# #
# # long_test = build_long_compare(
# #     test_df,
# #     "test",
# #     Tb_pred_test,
# #     Pc_pred_test,
# #     V_pred_baseline_test,
# #     V_pred_final_test
# # )
# #
# # long_compare = pd.concat(
# #     [long_train, long_test],
# #     ignore_index=True
# # ).sort_values(["Split", id_col, "temp_index"])
# #
# #
# # tb_train_out = pd.DataFrame({
# #     "Split": "train",
# #     id_col: train_df[id_col].values,
# #     "Tb_true": train_arr["Tb"],
# #     "Tb_pred": Tb_pred_train
# # })
# #
# # tb_test_out = pd.DataFrame({
# #     "Split": "test",
# #     id_col: test_df[id_col].values,
# #     "Tb_true": test_arr["Tb"],
# #     "Tb_pred": Tb_pred_test
# # })
# #
# # pc_train_out = pd.DataFrame({
# #     "Split": "train",
# #     id_col: train_df[id_col].values,
# #     "Pc_true_Pa": train_arr["Pc_bar"] * 1e5,
# #     "Pc_pred_Pa": Pc_pred_train
# # })
# #
# # pc_test_out = pd.DataFrame({
# #     "Split": "test",
# #     id_col: test_df[id_col].values,
# #     "Pc_true_Pa": test_arr["Pc_bar"] * 1e5,
# #     "Pc_pred_Pa": Pc_pred_test
# # })
# #
# #
# # summary_rows = [
# #     tb_metrics_train,
# #     tb_metrics_test,
# #     pc_metrics_train,
# #     pc_metrics_test,
# #     baseline_metrics_train,
# #     baseline_metrics_test,
# #     final_metrics_train,
# #     final_metrics_test
# # ]
# #
# # summary_df = pd.DataFrame(summary_rows)
# #
# # out_path = "vapor_pressure_actual_vs_pred_with_residual_RF_train_test_split.xlsx"
# #
# # with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
# #     long_compare.to_excel(writer, sheet_name="compare_long", index=False)
# #     summary_df.to_excel(writer, sheet_name="summary", index=False)
# #
# #     pd.concat(
# #         [tb_train_out, tb_test_out],
# #         ignore_index=True
# #     ).to_excel(writer, sheet_name="Tb_submodel", index=False)
# #
# #     pd.concat(
# #         [pc_train_out, pc_test_out],
# #         ignore_index=True
# #     ).to_excel(writer, sheet_name="Pc_submodel", index=False)
# #
# #
# # print(f"\n结果已保存到: {out_path}")
# #
# # print("\n总模型评估（基准 + 残差RF修正，测试集）：")
# # print(f"R²_ln = {final_metrics_test['R2_lnP']:.4f}")
# # print(f"MSE_ln = {final_metrics_test['MSE_lnP']:.6f}")
# # print(f"ARD = {final_metrics_test['ARD_%']:.2f}%")
# # print(f"误差 ≤ 1% 的数据点数量: {final_metrics_test['within_1pct']}")
# # print(f"误差 ≤ 5% 的数据点数量: {final_metrics_test['within_5pct']}")
# # print(f"误差 ≤ 10% 的数据点数量: {final_metrics_test['within_10pct']}")
#
# import numpy as np
# import pandas as pd
#
# from scipy.optimize import least_squares
# from sklearn.linear_model import HuberRegressor
# from sklearn.preprocessing import PolynomialFeatures
# from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split
#
#
# # ============================================================
# # 0. 参数设置
# # ============================================================
# file_path = "vp209.xlsx"
# sheet_name = "Sheet1"
#
# random_state = 41
#
# Pb = 101325.0
# Tb0 = 222.543
#
# # 列索引
# id_col_idx = 0
# MW_col_idx = 4
# Tb_col_idx = 5
# Nc_col_idx = 10
# group_start = 12
# group_end = 31
# temp_start = 31
# temp_end = 41
# vp_start = 41
# vp_end = 51
# Pc_col_idx = 51
# Tc_half_col_name = "ASPEN Half Critical T"
#
#
# # ============================================================
# # 1. 读取数据
# # ============================================================
# df = pd.read_excel(file_path, sheet_name=sheet_name).copy()
#
# compound_ids_all = df.iloc[:, id_col_idx].values
#
# Nk_all = df.iloc[:, group_start:group_end].apply(
#     pd.to_numeric,
#     errors="coerce"
# ).values
#
# T_all = df.iloc[:, temp_start:temp_end].apply(
#     pd.to_numeric,
#     errors="coerce"
# ).values
#
# P_vp_all = df.iloc[:, vp_start:vp_end].apply(
#     pd.to_numeric,
#     errors="coerce"
# ).values
#
# MW_all = pd.to_numeric(
#     df.iloc[:, MW_col_idx],
#     errors="coerce"
# ).values
#
# Tb_all = pd.to_numeric(
#     df.iloc[:, Tb_col_idx],
#     errors="coerce"
# ).values
#
# Tc_half_all = pd.to_numeric(
#     df[Tc_half_col_name],
#     errors="coerce"
# ).values
#
# Pc_bar_all = pd.to_numeric(
#     df.iloc[:, Pc_col_idx],
#     errors="coerce"
# ).values
#
#
# # ============================================================
# # 2. 有效物质过滤
# #    要求：
# #    1. 10个蒸汽压点都有效且 > 0
# #    2. 10个温度点都有效
# #    3. 19个基团有效
# #    4. 子模型需要的 Tb / Tc_half / Pc / MW 有效
# # ============================================================
# valid_p_mask = np.isfinite(P_vp_all) & (P_vp_all > 0)
# valid_p_mask = valid_p_mask.all(axis=1)
#
# valid_feature_mask = (
#     np.isfinite(Nk_all).all(axis=1)
#     & np.isfinite(T_all).all(axis=1)
#     & np.isfinite(MW_all)
#     & np.isfinite(Tb_all)
#     & np.isfinite(Tc_half_all)
#     & np.isfinite(Pc_bar_all)
# )
#
# valid_mask = valid_p_mask & valid_feature_mask
#
# compound_ids = compound_ids_all[valid_mask]
# Nk = Nk_all[valid_mask]
# T = T_all[valid_mask]
# P_vp = P_vp_all[valid_mask]
# MW = MW_all[valid_mask]
# Tb_true = Tb_all[valid_mask]
# Tc_half_true = Tc_half_all[valid_mask]
# Pc_bar_true = Pc_bar_all[valid_mask]
#
# print("========== 数据清洗后 ==========")
# print(f"有效物质数量: {len(Nk)}")
#
#
# # ============================================================
# # 3. 子模型：不划分训练集/测试集，直接用全部有效物质训练
# # ============================================================
#
# # ---------- 3.1 Tb 子模型 ----------
# poly = PolynomialFeatures(degree=2, include_bias=False)
# Nk_poly = poly.fit_transform(Nk)
#
# model_tb = HuberRegressor(max_iter=10000)
#
# model_tb.fit(
#     Nk_poly,
#     np.exp(Tb_true / Tb0)
# )
#
# Tb_pred = Tb0 * np.log(
#     np.clip(model_tb.predict(Nk_poly), 1e-6, None)
# )
#
#
# # ---------- 3.2 Tc_half 子模型 ----------
# model_tc = GradientBoostingRegressor(
#     n_estimators=300,
#     learning_rate=0.05,
#     max_depth=4,
#     random_state=0
# )
#
# model_tc.fit(Nk_poly, Tc_half_true)
#
# Tc_half_pred = model_tc.predict(Nk_poly)
#
# # 近似完整临界温度
# Tc_pred_full = Tc_half_pred * 2.0
#
#
# # ---------- 3.3 Pc 子模型 ----------
# def residual_pc(params, X, MW_value, Pc_true_bar):
#     beta = params[:-1]
#     beta3 = params[-1]
#
#     y_pred = X @ beta
#     x_pred = y_pred + 0.108998
#
#     # 防止接近 0 导致爆炸
#     x_pred = np.where(
#         np.abs(x_pred) < 1e-8,
#         np.sign(x_pred) * 1e-8 + (x_pred == 0) * 1e-8,
#         x_pred
#     )
#
#     Pc_pred_bar = (
#         5.9827
#         + (1.0 / x_pred) ** 2
#         + beta3 * np.exp(1.0 / np.clip(MW_value, 1e-8, None))
#     )
#
#     return Pc_pred_bar - Pc_true_bar
#
#
# params_init_pc = np.zeros(Nk.shape[1] + 1)
#
# result_pc = least_squares(
#     residual_pc,
#     x0=params_init_pc,
#     args=(Nk, MW, Pc_bar_true),
#     max_nfev=5000
# )
#
#
# def predict_pc_pa(Nk_raw, MW_value, result_pc):
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
#         + result_pc.x[-1] * np.exp(1.0 / np.clip(MW_value, 1e-8, None))
#     )
#
#     return Pc_pred_bar * 1e5
#
#
# Pc_pred_pa = predict_pc_pa(
#     Nk,
#     MW,
#     result_pc
# )
#
#
# # ============================================================
# # 4. 由子模型构造 slope 特征
# #    slope = [ln(Pc_pred) - ln(Pb)] / [Tc_pred_full - Tb_pred]
# # ============================================================
# def build_slope(Tb_pred, Tc_pred_full, Pc_pred_pa):
#     denom = Tc_pred_full - Tb_pred
#
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
#         np.log(Pc_pred_pa[valid]) - np.log(Pb)
#     ) / denom[valid]
#
#     return slope.reshape(-1, 1)
#
#
# slope = build_slope(
#     Tb_pred,
#     Tc_pred_full,
#     Pc_pred_pa
# )
#
# # 二次过滤：要求 slope 有效
# slope_valid_mask = np.isfinite(slope).flatten()
#
# compound_ids = compound_ids[slope_valid_mask]
# Nk = Nk[slope_valid_mask]
# T = T[slope_valid_mask]
# P_vp = P_vp[slope_valid_mask]
# slope = slope[slope_valid_mask]
#
# Tb_pred = Tb_pred[slope_valid_mask]
# Tc_half_pred = Tc_half_pred[slope_valid_mask]
# Tc_pred_full = Tc_pred_full[slope_valid_mask]
# Pc_pred_pa = Pc_pred_pa[slope_valid_mask]
#
# print("========== slope 构造后 ==========")
# print(f"最终可用物质数量: {len(Nk)}")
#
#
# # ============================================================
# # 5. 最终 RF 模型按物质划分训练集 / 测试集
# # ============================================================
# material_indices = np.arange(len(Nk))
#
# train_materials, test_materials = train_test_split(
#     material_indices,
#     test_size=0.2,
#     random_state=random_state
# )
#
# print("========== 最终 RF 模型按物质划分 ==========")
# print(f"训练集物质数: {len(train_materials)}")
# print(f"测试集物质数: {len(test_materials)}")
#
#
# # ============================================================
# # 6. 构建展开后的点级数据集
# # ============================================================
# def build_flat_data(Nk_sub, T_sub, P_vp_sub, slope_sub, material_ids_sub):
#     """
#     将物质级数据展开为温度点级数据。
#
#     原模型特征：
#         19个基团 + T
#
#     当前模型特征：
#         19个基团 + T + slope
#
#     其中 slope 是物质级特征，因此同一物质的10个温度点共享同一个 slope。
#     """
#
#     X = np.hstack([
#         Nk_sub.repeat(10, axis=0),
#         T_sub.flatten().reshape(-1, 1),
#         slope_sub.repeat(10, axis=0)
#     ])
#
#     y = np.log(P_vp_sub).flatten()
#
#     expanded_ids = np.repeat(material_ids_sub, 10)
#     expanded_T = T_sub.flatten()
#     expanded_slope = slope_sub.repeat(10, axis=0).flatten()
#
#     finite_mask = (
#         np.isfinite(y)
#         & np.isfinite(X).all(axis=1)
#     )
#
#     return (
#         X[finite_mask],
#         y[finite_mask],
#         expanded_ids[finite_mask],
#         expanded_T[finite_mask],
#         expanded_slope[finite_mask]
#     )
#
#
# X_train, y_train, id_train, temp_train, slope_train_point = build_flat_data(
#     Nk[train_materials],
#     T[train_materials],
#     P_vp[train_materials],
#     slope[train_materials],
#     compound_ids[train_materials]
# )
#
# X_test, y_test, id_test, temp_test, slope_test_point = build_flat_data(
#     Nk[test_materials],
#     T[test_materials],
#     P_vp[test_materials],
#     slope[test_materials],
#     compound_ids[test_materials]
# )
#
# print(f"训练集样本点数: {X_train.shape[0]}")
# print(f"测试集样本点数: {X_test.shape[0]}")
# print(f"最终 RF 特征数: {X_train.shape[1]}")
#
# if X_train.shape[1] != 21:
#     raise ValueError(
#         f"当前特征数为 {X_train.shape[1]}，预期为 21：19个基团 + T + slope。"
#     )
#
#
# # ============================================================
# # 7. 定义并训练最终 RF 模型
# # ============================================================
# rf = RandomForestRegressor(
#     n_estimators=500,
#     max_depth=None,
#     min_samples_split=2,
#     min_samples_leaf=1,
#     max_features="sqrt",
#     bootstrap=True,
#     random_state=42,
#     n_jobs=-1
# )
#
# print("\n开始训练最终 RF 模型...")
# rf.fit(X_train, y_train)
#
#
# # ============================================================
# # 8. 预测与评估函数
# # ============================================================
# def evaluate_model(model, X, y_true, set_name):
#     """
#     模型预测目标是 ln(P)，同时评估 ln(P) 和还原后的 P。
#     """
#
#     y_pred = model.predict(X)
#
#     P_true = np.exp(y_true)
#     P_pred = np.exp(y_pred)
#
#     # ln(P) 指标
#     r2_ln = r2_score(y_true, y_pred)
#     mse_ln = mean_squared_error(y_true, y_pred)
#
#     # P 指标
#     r2_P = r2_score(P_true, P_pred)
#     mse_P = mean_squared_error(P_true, P_pred)
#
#     rel_err = np.abs((P_pred - P_true) / P_true) * 100
#     ard = np.mean(rel_err)
#
#     within_1pct = np.sum(rel_err <= 1)
#     within_5pct = np.sum(rel_err <= 5)
#     within_10pct = np.sum(rel_err <= 10)
#
#     print(f"\n{set_name} 结果:")
#     print(f"ln(P)  R2  = {r2_ln:.6f}")
#     print(f"ln(P)  MSE = {mse_ln:.10f}")
#     print(f"P      R2  = {r2_P:.6f}")
#     print(f"P      MSE = {mse_P:.10f}")
#     print(f"P      ARD = {ard:.4f}%")
#     print(f"误差 <= 1%  : {within_1pct} 点")
#     print(f"误差 <= 5%  : {within_5pct} 点")
#     print(f"误差 <= 10% : {within_10pct} 点")
#
#     metrics = {
#         "R2_lnP": r2_ln,
#         "MSE_lnP": mse_ln,
#         "R2_P": r2_P,
#         "MSE_P": mse_P,
#         "ARD_%": ard,
#         "within_1pct": within_1pct,
#         "within_5pct": within_5pct,
#         "within_10pct": within_10pct
#     }
#
#     return y_pred, P_pred, rel_err, metrics
#
#
# # ============================================================
# # 9. 训练集和测试集评估
# # ============================================================
# y_train_pred, P_train_pred, rel_err_train, train_metrics = evaluate_model(
#     rf,
#     X_train,
#     y_train,
#     "训练集"
# )
#
# y_test_pred, P_test_pred, rel_err_test, test_metrics = evaluate_model(
#     rf,
#     X_test,
#     y_test,
#     "测试集"
# )
#
#
# # ============================================================
# # 10. 保存预测结果
# # ============================================================
# def build_result_df(X_orig, y_true, y_pred, rel_err, material_ids, temperatures, slope_point, set_label):
#     """
#     构建长表结果。
#     """
#
#     df_res = pd.DataFrame({
#         "Set": set_label,
#         "Material_ID": material_ids,
#         "Temperature_K": temperatures,
#         "slope": slope_point,
#         "ln(P)_true": y_true,
#         "ln(P)_pred": y_pred,
#         "P_true": np.exp(y_true),
#         "P_pred": np.exp(y_pred),
#         "Relative_Error_P (%)": rel_err
#     })
#
#     for i in range(19):
#         df_res[f"Group_{i + 1}"] = X_orig[:, i]
#
#     return df_res
#
#
# train_res = build_result_df(
#     X_train,
#     y_train,
#     y_train_pred,
#     rel_err_train,
#     id_train,
#     temp_train,
#     slope_train_point,
#     "Train"
# )
#
# test_res = build_result_df(
#     X_test,
#     y_test,
#     y_test_pred,
#     rel_err_test,
#     id_test,
#     temp_test,
#     slope_test_point,
#     "Test"
# )
#
# all_res = pd.concat(
#     [train_res, test_res],
#     ignore_index=True
# )
#
# output_file = "VaporPressure_RF_with_slope_TrainTestSplit.xlsx"
#
# all_res.to_excel(
#     output_file,
#     index=False
# )
#
# print(f"\n预测结果已保存至: {output_file}")
#
#
# # ============================================================
# # 11. 保存评估汇总表
# # ============================================================
# summary = pd.DataFrame([
#     [
#         "Train",
#         train_metrics["R2_lnP"],
#         train_metrics["MSE_lnP"],
#         train_metrics["R2_P"],
#         train_metrics["MSE_P"],
#         train_metrics["ARD_%"],
#         train_metrics["within_1pct"],
#         train_metrics["within_5pct"],
#         train_metrics["within_10pct"]
#     ],
#     [
#         "Test",
#         test_metrics["R2_lnP"],
#         test_metrics["MSE_lnP"],
#         test_metrics["R2_P"],
#         test_metrics["MSE_P"],
#         test_metrics["ARD_%"],
#         test_metrics["within_1pct"],
#         test_metrics["within_5pct"],
#         test_metrics["within_10pct"]
#     ]
# ], columns=[
#     "Split",
#     "R2_lnP",
#     "MSE_lnP",
#     "R2_P",
#     "MSE_P",
#     "ARD_%",
#     "within_1pct",
#     "within_5pct",
#     "within_10pct"
# ])
#
# summary_file = "RF_with_slope_Summary.xlsx"
#
# summary.to_excel(
#     summary_file,
#     index=False
# )
#
# print(f"评估汇总已保存至: {summary_file}")
#
#
# # ============================================================
# # 12. 保存子模型产生的 slope 信息
# # ============================================================
# slope_info_df = pd.DataFrame({
#     "Material_ID": compound_ids,
#     "Tb_pred": Tb_pred,
#     "Tc_half_pred": Tc_half_pred,
#     "Tc_full_pred": Tc_pred_full,
#     "Pc_pred_Pa": Pc_pred_pa,
#     "slope": slope.flatten()
# })
#
# slope_info_file = "RF_with_slope_submodel_slope_values.xlsx"
#
# slope_info_df.to_excel(
#     slope_info_file,
#     index=False
# )
#
# print(f"slope 信息已保存至: {slope_info_file}")
#
#
# # ============================================================
# # 13. 保存特征重要性
# # ============================================================
# feature_names = [f"Group_{i + 1}" for i in range(19)] + ["Temperature_K", "slope"]
#
# feature_importance_df = pd.DataFrame({
#     "Feature": feature_names,
#     "Importance": rf.feature_importances_
# }).sort_values(by="Importance", ascending=False)
#
# feature_importance_file = "RF_with_slope_feature_importance.xlsx"
#
# feature_importance_df.to_excel(
#     feature_importance_file,
#     index=False
# )
#
# print(f"特征重要性已保存至: {feature_importance_file}")


import numpy as np
import pandas as pd

from scipy.optimize import least_squares
from sklearn.linear_model import HuberRegressor
from sklearn.preprocessing import PolynomialFeatures
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


# ============================================================
# 0. 参数设置
# ============================================================
file_path = "vp209.xlsx"
sheet_name = "Sheet1"

random_state = 41

Pb = 101325.0
Tb0 = 222.543

# 列索引
id_col_idx = 0
MW_col_idx = 4
Tb_col_idx = 5
Nc_col_idx = 10
group_start = 12
group_end = 31
temp_start = 31
temp_end = 41
vp_start = 41
vp_end = 51
Pc_col_idx = 51
Tc_half_col_name = "ASPEN Half Critical T"


# ============================================================
# 1. 读取数据
# ============================================================
df = pd.read_excel(file_path, sheet_name=sheet_name).copy()

compound_ids_all = df.iloc[:, id_col_idx].values

Nk_all = df.iloc[:, group_start:group_end].apply(
    pd.to_numeric,
    errors="coerce"
).values

T_all = df.iloc[:, temp_start:temp_end].apply(
    pd.to_numeric,
    errors="coerce"
).values

P_vp_all = df.iloc[:, vp_start:vp_end].apply(
    pd.to_numeric,
    errors="coerce"
).values

MW_all = pd.to_numeric(
    df.iloc[:, MW_col_idx],
    errors="coerce"
).values

Tb_all = pd.to_numeric(
    df.iloc[:, Tb_col_idx],
    errors="coerce"
).values

Tc_half_all = pd.to_numeric(
    df[Tc_half_col_name],
    errors="coerce"
).values

Pc_bar_all = pd.to_numeric(
    df.iloc[:, Pc_col_idx],
    errors="coerce"
).values


# ============================================================
# 2. 有效物质过滤
# ============================================================
valid_p_mask = np.isfinite(P_vp_all) & (P_vp_all > 0)
valid_p_mask = valid_p_mask.all(axis=1)

valid_feature_mask = (
    np.isfinite(Nk_all).all(axis=1)
    & np.isfinite(T_all).all(axis=1)
    & np.isfinite(MW_all)
    & np.isfinite(Tb_all)
    & np.isfinite(Tc_half_all)
    & np.isfinite(Pc_bar_all)
)

valid_mask = valid_p_mask & valid_feature_mask

compound_ids = compound_ids_all[valid_mask]
Nk = Nk_all[valid_mask]
T = T_all[valid_mask]
P_vp = P_vp_all[valid_mask]
MW = MW_all[valid_mask]
Tb_true = Tb_all[valid_mask]
Tc_half_true = Tc_half_all[valid_mask]
Pc_bar_true = Pc_bar_all[valid_mask]

print("========== 数据清洗后 ==========")
print(f"有效物质数量: {len(Nk)}")


# ============================================================
# 3. 子模型：不划分训练集/测试集，直接用全部有效物质训练
# ============================================================

# ---------- 3.1 Tb 子模型 ----------
poly = PolynomialFeatures(degree=2, include_bias=False)
Nk_poly = poly.fit_transform(Nk)

model_tb = HuberRegressor(max_iter=10000)

model_tb.fit(
    Nk_poly,
    np.exp(Tb_true / Tb0)
)

Tb_pred = Tb0 * np.log(
    np.clip(model_tb.predict(Nk_poly), 1e-6, None)
)


# ---------- 3.2 Tc_half 子模型 ----------
model_tc = GradientBoostingRegressor(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=4,
    random_state=0
)

model_tc.fit(Nk_poly, Tc_half_true)

Tc_half_pred = model_tc.predict(Nk_poly)

# 近似完整临界温度
Tc_pred_full = Tc_half_pred * 2.0


# ---------- 3.3 Pc 子模型 ----------
def residual_pc(params, X, MW_value, Pc_true_bar):
    beta = params[:-1]
    beta3 = params[-1]

    y_pred = X @ beta
    x_pred = y_pred + 0.108998

    x_pred = np.where(
        np.abs(x_pred) < 1e-8,
        np.sign(x_pred) * 1e-8 + (x_pred == 0) * 1e-8,
        x_pred
    )

    Pc_pred_bar = (
        5.9827
        + (1.0 / x_pred) ** 2
        + beta3 * np.exp(1.0 / np.clip(MW_value, 1e-8, None))
    )

    return Pc_pred_bar - Pc_true_bar


params_init_pc = np.zeros(Nk.shape[1] + 1)

result_pc = least_squares(
    residual_pc,
    x0=params_init_pc,
    args=(Nk, MW, Pc_bar_true),
    max_nfev=5000
)


def predict_pc_pa(Nk_raw, MW_value, result_pc):
    x_fit = Nk_raw @ result_pc.x[:-1] + 0.108998

    x_fit = np.where(
        np.abs(x_fit) < 1e-8,
        np.sign(x_fit) * 1e-8 + (x_fit == 0) * 1e-8,
        x_fit
    )

    Pc_pred_bar = (
        5.9827
        + (1.0 / x_fit) ** 2
        + result_pc.x[-1] * np.exp(1.0 / np.clip(MW_value, 1e-8, None))
    )

    return Pc_pred_bar * 1e5


Pc_pred_pa = predict_pc_pa(
    Nk,
    MW,
    result_pc
)


# ============================================================
# 4. 由子模型构造 slope 特征
#    slope = [ln(Pc_pred) - ln(Pb)] / [Tc_pred_full - Tb_pred]
# ============================================================
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
        np.log(Pc_pred_pa[valid]) - np.log(Pb)
    ) / denom[valid]

    return slope.reshape(-1, 1)


slope = build_slope(
    Tb_pred,
    Tc_pred_full,
    Pc_pred_pa
)

# 二次过滤：要求 slope 有效
slope_valid_mask = np.isfinite(slope).flatten()

compound_ids = compound_ids[slope_valid_mask]
Nk = Nk[slope_valid_mask]
T = T[slope_valid_mask]
P_vp = P_vp[slope_valid_mask]
slope = slope[slope_valid_mask]

Tb_pred = Tb_pred[slope_valid_mask]
Tc_half_pred = Tc_half_pred[slope_valid_mask]
Tc_pred_full = Tc_pred_full[slope_valid_mask]
Pc_pred_pa = Pc_pred_pa[slope_valid_mask]

print("========== slope 构造后 ==========")
print(f"最终可用物质数量: {len(Nk)}")


# ============================================================
# 5. 最终 RF 模型按物质划分训练集 / 测试集
# ============================================================
material_indices = np.arange(len(Nk))

train_materials, test_materials = train_test_split(
    material_indices,
    test_size=0.2,
    random_state=random_state
)

print("========== 最终 RF 模型按物质划分 ==========")
print(f"训练集物质数: {len(train_materials)}")
print(f"测试集物质数: {len(test_materials)}")


# ============================================================
# 6. 构建展开后的点级数据集
# ============================================================
def build_flat_data(Nk_sub, T_sub, P_vp_sub, slope_sub, material_ids_sub):
    """
    将物质级数据展开为温度点级数据。

    当前模型特征：
        19个基团 + T + slope

    其中 slope 是物质级特征，因此同一物质的10个温度点共享同一个 slope。
    """

    X = np.hstack([
        Nk_sub.repeat(10, axis=0),
        T_sub.flatten().reshape(-1, 1),
        slope_sub.repeat(10, axis=0)
    ])

    y = np.log(P_vp_sub).flatten()

    expanded_ids = np.repeat(material_ids_sub, 10)
    expanded_T = T_sub.flatten()
    expanded_slope = slope_sub.repeat(10, axis=0).flatten()

    finite_mask = (
        np.isfinite(y)
        & np.isfinite(X).all(axis=1)
    )

    return (
        X[finite_mask],
        y[finite_mask],
        expanded_ids[finite_mask],
        expanded_T[finite_mask],
        expanded_slope[finite_mask]
    )


X_train, y_train, id_train, temp_train, slope_train_point = build_flat_data(
    Nk[train_materials],
    T[train_materials],
    P_vp[train_materials],
    slope[train_materials],
    compound_ids[train_materials]
)

X_test, y_test, id_test, temp_test, slope_test_point = build_flat_data(
    Nk[test_materials],
    T[test_materials],
    P_vp[test_materials],
    slope[test_materials],
    compound_ids[test_materials]
)

print(f"训练集样本点数: {X_train.shape[0]}")
print(f"测试集样本点数: {X_test.shape[0]}")
print(f"最终 RF 特征数: {X_train.shape[1]}")

if X_train.shape[1] != 21:
    raise ValueError(
        f"当前特征数为 {X_train.shape[1]}，预期为 21：19个基团 + T + slope。"
    )


# ============================================================
# 7. 定义并训练最终 RF 模型
# ============================================================
rf = RandomForestRegressor(
    n_estimators=500,
    max_depth=None,
    min_samples_split=2,
    min_samples_leaf=1,
    max_features="sqrt",
    bootstrap=True,
    random_state=42,
    n_jobs=-1
)

print("\n开始训练最终 RF 模型...")
rf.fit(X_train, y_train)


# ============================================================
# 8. 预测与评估函数
# ============================================================
def evaluate_model(model, X, y_true, set_name, strict_less=False):
    """
    模型预测目标是 ln(P)，同时评估 ln(P) 和还原后的 P。
    strict_less=False: <=1%, <=5%, <=10%
    strict_less=True : <1%, <5%, <10%
    """

    y_pred = model.predict(X)

    P_true = np.exp(y_true)
    P_pred = np.exp(y_pred)

    # ln(P) 指标
    r2_ln = r2_score(y_true, y_pred)
    mse_ln = mean_squared_error(y_true, y_pred)

    # P 指标
    r2_P = r2_score(P_true, P_pred)
    mse_P = mean_squared_error(P_true, P_pred)

    rel_err = np.abs((P_pred - P_true) / P_true) * 100
    ard = np.mean(rel_err)

    if strict_less:
        within_1pct = np.sum(rel_err < 1)
        within_5pct = np.sum(rel_err < 5)
        within_10pct = np.sum(rel_err < 10)
    else:
        within_1pct = np.sum(rel_err <= 1)
        within_5pct = np.sum(rel_err <= 5)
        within_10pct = np.sum(rel_err <= 10)

    print(f"\n{set_name} 结果:")
    print(f"ln(P)  R2  = {r2_ln:.6f}")
    print(f"ln(P)  MSE = {mse_ln:.10f}")
    print(f"P      R2  = {r2_P:.6f}")
    print(f"P      MSE = {mse_P:.10f}")
    print(f"P      ARD = {ard:.4f}%")

    if strict_less:
        print(f"误差 < 1%  : {within_1pct} 点")
        print(f"误差 < 5%  : {within_5pct} 点")
        print(f"误差 < 10% : {within_10pct} 点")
    else:
        print(f"误差 <= 1%  : {within_1pct} 点")
        print(f"误差 <= 5%  : {within_5pct} 点")
        print(f"误差 <= 10% : {within_10pct} 点")

    metrics = {
        "R2_lnP": r2_ln,
        "MSE_lnP": mse_ln,
        "R2_P": r2_P,
        "MSE_P": mse_P,
        "ARD_%": ard,
        "within_1pct": within_1pct,
        "within_5pct": within_5pct,
        "within_10pct": within_10pct
    }

    return y_pred, P_pred, rel_err, metrics


# ============================================================
# 9. 训练集和测试集评估
# ============================================================
y_train_pred, P_train_pred, rel_err_train, train_metrics = evaluate_model(
    rf,
    X_train,
    y_train,
    "训练集",
    strict_less=False
)

y_test_pred, P_test_pred, rel_err_test, test_metrics = evaluate_model(
    rf,
    X_test,
    y_test,
    "测试集",
    strict_less=False
)


# ============================================================
# 9.1 完整数据集统计：训练集 + 测试集
# ============================================================
X_all = np.vstack([X_train, X_test])
y_all = np.concatenate([y_train, y_test])
id_all = np.concatenate([id_train, id_test])
temp_all = np.concatenate([temp_train, temp_test])
slope_all_point = np.concatenate([slope_train_point, slope_test_point])

y_all_pred, P_all_pred, rel_err_all, all_metrics = evaluate_model(
    rf,
    X_all,
    y_all,
    "完整数据集：训练集 + 测试集",
    strict_less=True
)

print("\n完整数据集实际蒸汽压 P 预测偏差 1%，5%，10%分别为：")
print(all_metrics["within_1pct"])
print(all_metrics["within_5pct"])
print(all_metrics["within_10pct"])


# ============================================================
# 10. 保存预测结果
# ============================================================
def build_result_df(X_orig, y_true, y_pred, rel_err, material_ids, temperatures, slope_point, set_label):
    """
    构建长表结果。
    """

    df_res = pd.DataFrame({
        "Set": set_label,
        "Material_ID": material_ids,
        "Temperature_K": temperatures,
        "slope": slope_point,
        "ln(P)_true": y_true,
        "ln(P)_pred": y_pred,
        "P_true": np.exp(y_true),
        "P_pred": np.exp(y_pred),
        "Relative_Error_P (%)": rel_err
    })

    for i in range(19):
        df_res[f"Group_{i + 1}"] = X_orig[:, i]

    return df_res


train_res = build_result_df(
    X_train,
    y_train,
    y_train_pred,
    rel_err_train,
    id_train,
    temp_train,
    slope_train_point,
    "Train"
)

test_res = build_result_df(
    X_test,
    y_test,
    y_test_pred,
    rel_err_test,
    id_test,
    temp_test,
    slope_test_point,
    "Test"
)

all_res = build_result_df(
    X_all,
    y_all,
    y_all_pred,
    rel_err_all,
    id_all,
    temp_all,
    slope_all_point,
    "All"
)

output_file = "VaporPressure_RF_with_slope_TrainTestSplit.xlsx"

with pd.ExcelWriter(output_file, engine="xlsxwriter") as writer:
    pd.concat([train_res, test_res], ignore_index=True).to_excel(
        writer,
        sheet_name="predictions",
        index=False
    )
    all_res.to_excel(
        writer,
        sheet_name="all_predictions",
        index=False
    )

print(f"\n预测结果已保存至: {output_file}")


# ============================================================
# 11. 保存评估汇总表
# ============================================================
summary = pd.DataFrame([
    [
        "Train",
        train_metrics["R2_lnP"],
        train_metrics["MSE_lnP"],
        train_metrics["R2_P"],
        train_metrics["MSE_P"],
        train_metrics["ARD_%"],
        train_metrics["within_1pct"],
        train_metrics["within_5pct"],
        train_metrics["within_10pct"]
    ],
    [
        "Test",
        test_metrics["R2_lnP"],
        test_metrics["MSE_lnP"],
        test_metrics["R2_P"],
        test_metrics["MSE_P"],
        test_metrics["ARD_%"],
        test_metrics["within_1pct"],
        test_metrics["within_5pct"],
        test_metrics["within_10pct"]
    ],
    [
        "All",
        all_metrics["R2_lnP"],
        all_metrics["MSE_lnP"],
        all_metrics["R2_P"],
        all_metrics["MSE_P"],
        all_metrics["ARD_%"],
        all_metrics["within_1pct"],
        all_metrics["within_5pct"],
        all_metrics["within_10pct"]
    ]
], columns=[
    "Split",
    "R2_lnP",
    "MSE_lnP",
    "R2_P",
    "MSE_P",
    "ARD_%",
    "within_1pct",
    "within_5pct",
    "within_10pct"
])

summary_file = "RF_with_slope_Summary.xlsx"

summary.to_excel(
    summary_file,
    index=False
)

print(f"评估汇总已保存至: {summary_file}")


# ============================================================
# 12. 保存子模型产生的 slope 信息
# ============================================================
slope_info_df = pd.DataFrame({
    "Material_ID": compound_ids,
    "Tb_pred": Tb_pred,
    "Tc_half_pred": Tc_half_pred,
    "Tc_full_pred": Tc_pred_full,
    "Pc_pred_Pa": Pc_pred_pa,
    "slope": slope.flatten()
})

slope_info_file = "RF_with_slope_submodel_slope_values.xlsx"

slope_info_df.to_excel(
    slope_info_file,
    index=False
)

print(f"slope 信息已保存至: {slope_info_file}")


# ============================================================
# 13. 保存特征重要性
# ============================================================
feature_names = [f"Group_{i + 1}" for i in range(19)] + ["Temperature_K", "slope"]

feature_importance_df = pd.DataFrame({
    "Feature": feature_names,
    "Importance": rf.feature_importances_
}).sort_values(by="Importance", ascending=False)

feature_importance_file = "RF_with_slope_feature_importance.xlsx"

feature_importance_df.to_excel(
    feature_importance_file,
    index=False
)

print(f"特征重要性已保存至: {feature_importance_file}")


# ============================================================
# 14. 输出模型结构记录
# ============================================================
print("\n当前蒸汽压 RF + slope 模型结构:")
print("Tb_submodel: HuberRegressor(max_iter=10000), input = PolynomialFeatures(Nk, degree=2)")
print("Tc_half_submodel: GradientBoostingRegressor(n_estimators=300, learning_rate=0.05, max_depth=4, random_state=0), input = PolynomialFeatures(Nk, degree=2)")
print("Pc_submodel: least_squares explicit Pc equation, input = Nk + MW")
print("slope = [ln(Pc_pred) - ln(Pb)] / [Tc_full_pred - Tb_pred]")
print("Final target: ln(P_vp)")
print("Final evaluation target: P = exp(lnP)")
print("Final model: RandomForestRegressor")
print("Final parameters:")
print(rf)
print("Final input features: Nk + T + slope")