# import numpy as np
# import pandas as pd
#
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.preprocessing import PolynomialFeatures
# from sklearn.linear_model import HuberRegressor
# from sklearn.ensemble import GradientBoostingRegressor
# from scipy.optimize import least_squares
# from sklearn.model_selection import train_test_split, GroupKFold, cross_val_score
#
#
# # ========== 读取数据 ========== #
# df = pd.read_excel("vp209.xlsx", sheet_name="Sheet1").copy()
#
#
# # ========== 定义列 ========== #
# id_col = df.columns[0]
#
# group_cols = list(df.columns[12:31])   # 第13~31列：19个基团
# temp_cols = list(df.columns[31:41])    # 第32~41列：10个温度
# v_cols = list(df.columns[41:51])       # 第42~51列：10个蒸汽压
#
# tb_col_idx = 5
# mw_col_idx = 4
# pc_col_idx = 51
#
#
# # ========== 数据预处理 ========== #
# for col in temp_cols + v_cols:
#     df[col] = pd.to_numeric(df[col], errors="coerce")
#
# df.iloc[:, tb_col_idx] = pd.to_numeric(df.iloc[:, tb_col_idx], errors="coerce")
# df.iloc[:, mw_col_idx] = pd.to_numeric(df.iloc[:, mw_col_idx], errors="coerce")
# df.iloc[:, pc_col_idx] = pd.to_numeric(df.iloc[:, pc_col_idx], errors="coerce")
#
# Nk_all = df.iloc[:, 12:31].apply(pd.to_numeric, errors="coerce").values
# T_all = df.iloc[:, 31:41].apply(pd.to_numeric, errors="coerce").values
# P_vp_all = df.iloc[:, 41:51].apply(pd.to_numeric, errors="coerce").values
#
#
# # ========== 创建有效掩码 ==========
# valid_mask = np.isfinite(P_vp_all) & (P_vp_all > 0)
# valid_mask = valid_mask.all(axis=1)
#
# df_valid = df.loc[valid_mask].copy().reset_index(drop=True)
#
# print(f"有效物质数: {len(df_valid)}")
#
#
# # ========== 按物质 8:2 划分 ==========
# unique_materials = df_valid[id_col].values
#
# train_materials, test_materials = train_test_split(
#     unique_materials,
#     test_size=0.2,
#     random_state=44
# )
#
# train_materials = set(train_materials)
# test_materials = set(test_materials)
#
# train_df = df_valid[df_valid[id_col].isin(train_materials)].copy().reset_index(drop=True)
# test_df = df_valid[df_valid[id_col].isin(test_materials)].copy().reset_index(drop=True)
#
# print(f"训练集物质数: {len(train_df)}, 测试集物质数: {len(test_df)}")
#
#
# # ========== 工具函数 ==========
# def get_arrays(df_part):
#     return {
#         "ids": df_part[id_col].values,
#         "Nk": df_part.iloc[:, 12:31].apply(pd.to_numeric, errors="coerce").values,
#         "T": df_part.iloc[:, 31:41].apply(pd.to_numeric, errors="coerce").values,
#         "P_vp": df_part.iloc[:, 41:51].apply(pd.to_numeric, errors="coerce").values,
#         "Tb": pd.to_numeric(df_part.iloc[:, tb_col_idx], errors="coerce").values,
#         "MW": pd.to_numeric(df_part.iloc[:, mw_col_idx], errors="coerce").values.reshape(-1, 1),
#         "Pc_bar": pd.to_numeric(df_part.iloc[:, pc_col_idx], errors="coerce").values,
#     }
#
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
# def eval_pressure_metrics(y_true_log, y_pred_log, model_name, split_name):
#     y_true_log = np.asarray(y_true_log, dtype=float)
#     y_pred_log = np.asarray(y_pred_log, dtype=float)
#
#     mask = np.isfinite(y_true_log) & np.isfinite(y_pred_log)
#     y_true_log = y_true_log[mask]
#     y_pred_log = y_pred_log[mask]
#
#     P_true = np.exp(y_true_log)
#     P_pred = np.exp(y_pred_log)
#
#     r2_ln = r2_score(y_true_log, y_pred_log)
#     mse_ln = mean_squared_error(y_true_log, y_pred_log)
#
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
#     print(f"\n{model_name} - {split_name}")
#     print(f"ln(P)  R2 = {r2_ln:.6f}, MSE = {mse_ln:.6f}")
#     print(f"P      R2 = {r2_P:.6f}, MSE = {mse_P:.6f}, ARD = {ard:.2f}%")
#     print(f"误差 <= 1% : {within_1pct} 点")
#     print(f"误差 <= 5% : {within_5pct} 点")
#     print(f"误差 <= 10%: {within_10pct} 点")
#
#     return {
#         "Model": model_name,
#         "Split": split_name,
#         "R2_lnP": r2_ln,
#         "MSE_lnP": mse_ln,
#         "R2_P": r2_P,
#         "MSE_P": mse_P,
#         "ARD_%": ard,
#         "within_1pct": within_1pct,
#         "within_5pct": within_5pct,
#         "within_10pct": within_10pct
#     }, rel_err
#
#
# train_arr = get_arrays(train_df)
# test_arr = get_arrays(test_df)
#
#
# # ========== 构建 Nk_poly（只在训练集 fit） ==========
# poly = PolynomialFeatures(degree=2, include_bias=False)
#
# Nk_poly_train = poly.fit_transform(train_arr["Nk"])
# Nk_poly_test = poly.transform(test_arr["Nk"])
#
#
# # ========== Tb 模型（只用训练集） ==========
# Tb0 = 222.543
#
# tb_train_mask = np.isfinite(train_arr["Tb"]) & np.isfinite(Nk_poly_train).all(axis=1)
# tb_test_mask = np.isfinite(test_arr["Tb"]) & np.isfinite(Nk_poly_test).all(axis=1)
#
# model_tb = HuberRegressor(max_iter=10000)
#
# model_tb.fit(
#     Nk_poly_train[tb_train_mask],
#     np.exp(train_arr["Tb"][tb_train_mask] / Tb0)
# )
#
# Tb_pred_train = Tb0 * np.log(
#     np.clip(model_tb.predict(Nk_poly_train), 1e-6, None)
# )
#
# Tb_pred_test = Tb0 * np.log(
#     np.clip(model_tb.predict(Nk_poly_test), 1e-6, None)
# )
#
# tb_metrics_train = evaluate_scalar_regression(
#     train_arr["Tb"][tb_train_mask],
#     Tb_pred_train[tb_train_mask],
#     "Tb_submodel",
#     "train"
# )
#
# tb_metrics_test = evaluate_scalar_regression(
#     test_arr["Tb"][tb_test_mask],
#     Tb_pred_test[tb_test_mask],
#     "Tb_submodel",
#     "test"
# )
#
#
# # ========== Pc 模型（只用原始19个基团，不用 poly） ==========
# Pc_bar_train = train_arr["Pc_bar"]
# Pc_bar_test = test_arr["Pc_bar"]
#
# MW_train_flat = train_arr["MW"].flatten()
# MW_test_flat = test_arr["MW"].flatten()
#
# Pc_X_train = train_arr["Nk"]
# Pc_X_test = test_arr["Nk"]
#
#
# def residual_pc(params, X, MW, Pc_true):
#     beta = params[:-1]
#     beta3 = params[-1]
#
#     y_pred = X @ beta
#     x_pred = y_pred + 0.108998
#
#     x_pred = np.where(
#         np.abs(x_pred) < 1e-8,
#         np.sign(x_pred) * 1e-8 + (x_pred == 0) * 1e-8,
#         x_pred
#     )
#
#     Pc_pred = 5.9827 + (1 / x_pred) ** 2 + beta3 * np.exp(
#         1 / np.clip(MW, 1e-8, None)
#     )
#
#     return Pc_pred - Pc_true
#
#
# pc_train_mask = (
#     np.isfinite(Pc_bar_train)
#     & np.isfinite(MW_train_flat)
#     & np.isfinite(Pc_X_train).all(axis=1)
# )
#
# pc_test_mask = (
#     np.isfinite(Pc_bar_test)
#     & np.isfinite(MW_test_flat)
#     & np.isfinite(Pc_X_test).all(axis=1)
# )
#
# params_init_pc = np.zeros(Pc_X_train.shape[1] + 1)
#
# result_pc = least_squares(
#     residual_pc,
#     x0=params_init_pc,
#     args=(
#         Pc_X_train[pc_train_mask],
#         MW_train_flat[pc_train_mask],
#         Pc_bar_train[pc_train_mask]
#     ),
#     max_nfev=5000
# )
#
#
# def predict_pc_pa(Pc_X, MW_flat, result_pc):
#     x_fit = Pc_X @ result_pc.x[:-1] + 0.108998
#
#     x_fit = np.where(
#         np.abs(x_fit) < 1e-8,
#         np.sign(x_fit) * 1e-8 + (x_fit == 0) * 1e-8,
#         x_fit
#     )
#
#     Pc_pred = 5.9827 + (1 / x_fit) ** 2 + result_pc.x[-1] * np.exp(
#         1 / np.clip(MW_flat, 1e-8, None)
#     )
#
#     return Pc_pred * 1e5
#
#
# Pc_pred_train = predict_pc_pa(Pc_X_train, MW_train_flat, result_pc)
# Pc_pred_test = predict_pc_pa(Pc_X_test, MW_test_flat, result_pc)
#
# pc_metrics_train = evaluate_scalar_regression(
#     Pc_bar_train[pc_train_mask] * 1e5,
#     Pc_pred_train[pc_train_mask],
#     "Pc_submodel",
#     "train"
# )
#
# pc_metrics_test = evaluate_scalar_regression(
#     Pc_bar_test[pc_test_mask] * 1e5,
#     Pc_pred_test[pc_test_mask],
#     "Pc_submodel",
#     "test"
# )
#
#
# # ========== 蒸汽压主模型：基线 A_k（只用训练集） ==========
# G_train = train_arr["Nk"]
# G_test = test_arr["Nk"]
#
# X_rows_train = []
# y_rows_train = []
# group_ids_train = []
#
# for i in range(len(train_df)):
#     for j, (tcol, vcol) in enumerate(zip(temp_cols, v_cols)):
#         Tj = train_df.at[i, tcol]
#         Vj = train_df.at[i, vcol]
#
#         if np.isnan(Tj) or np.isnan(Vj) or Vj <= 0:
#             continue
#
#         Tb_i = Tb_pred_train[i]
#         V_ref = 101325.0
#
#         Xj = (Tj - Tb_i) * G_train[i]
#         yj = np.log(Vj) - np.log(V_ref)
#
#         X_rows_train.append(Xj)
#         y_rows_train.append(yj)
#         group_ids_train.append(train_df.at[i, id_col])
#
# X_A_train = np.array(X_rows_train, dtype=float)
# y_A_train = np.array(y_rows_train, dtype=float)
# group_ids_train = np.array(group_ids_train)
#
# A_solver = HuberRegressor(fit_intercept=False, max_iter=5000)
# A_solver.fit(X_A_train, y_A_train)
#
# A_vec = A_solver.coef_
#
#
# # ========== 生成基准蒸汽压预测（训练/测试分别生成） ==========
# def build_baseline_predictions(df_part, G_part, Tb_pred_part):
#     V_pred_baseline = pd.DataFrame(index=df_part.index, columns=v_cols, dtype=float)
#
#     for i in range(len(df_part)):
#         Tb_i = Tb_pred_part[i]
#         V_ref = 101325.0
#
#         for tcol, vcol in zip(temp_cols, v_cols):
#             Tj = df_part.at[i, tcol]
#
#             if np.isnan(Tj):
#                 V_pred_baseline.at[i, vcol] = np.nan
#                 continue
#
#             Xj = (Tj - Tb_i) * G_part[i]
#             ln_V_pred = np.log(V_ref) + Xj @ A_vec
#
#             V_pred_baseline.at[i, vcol] = np.exp(ln_V_pred)
#
#     return V_pred_baseline
#
#
# V_pred_baseline_train = build_baseline_predictions(
#     train_df,
#     G_train,
#     Tb_pred_train
# )
#
# V_pred_baseline_test = build_baseline_predictions(
#     test_df,
#     G_test,
#     Tb_pred_test
# )
#
#
# # ========== 残差 GBDT 模型（只用训练集） ==========
# print("\n训练残差 GBDT 模型...")
#
#
# def build_residual_dataset(
#     df_part,
#     G_part,
#     Tb_pred_part,
#     Pc_pred_part,
#     MW_part,
#     V_pred_baseline_part
# ):
#     residual_features = []
#     residual_targets = []
#     sample_info = []
#     sample_groups = []
#
#     for tcol, vcol in zip(temp_cols, v_cols):
#         Tj = df_part[tcol].to_numpy(dtype=float)
#         Vj = df_part[vcol].to_numpy(dtype=float)
#
#         msk = (
#             (~np.isnan(Tj))
#             & (~np.isnan(Vj))
#             & (Vj > 0)
#             & (~V_pred_baseline_part[vcol].isna().to_numpy())
#         )
#
#         for i in np.where(msk)[0]:
#             baseline_pred = V_pred_baseline_part.at[i, vcol]
#
#             if not np.isfinite(baseline_pred) or baseline_pred <= 0:
#                 continue
#
#             base_features = list(G_part[i])
#
#             temp_features = [
#                 Tj[i],
#                 Tj[i] - Tb_pred_part[i],
#                 Tj[i] / Tb_pred_part[i] if Tb_pred_part[i] > 0 else 0.0,
#                 np.log(Tj[i]) if Tj[i] > 0 else 0.0,
#             ]
#
#             baseline_features = [
#                 np.log(baseline_pred)
#             ]
#
#             ref_features = [
#                 Tb_pred_part[i],
#                 np.log(101325.0),
#                 Pc_pred_part[i] if i < len(Pc_pred_part) else 0.0,
#             ]
#
#             mw_features = [
#                 MW_part[i][0] if i < len(MW_part) else 0.0
#             ]
#
#             all_features = (
#                 base_features
#                 + temp_features
#                 + baseline_features
#                 + ref_features
#                 + mw_features
#             )
#
#             residual_features.append(all_features)
#
#             # 残差目标：ln(V_actual) - ln(V_baseline)
#             residual = np.log(Vj[i]) - np.log(baseline_pred)
#             residual_targets.append(residual)
#
#             sample_info.append((i, tcol, vcol))
#             sample_groups.append(df_part.at[i, id_col])
#
#     residual_features = np.array(residual_features, dtype=float)
#     residual_targets = np.array(residual_targets, dtype=float)
#     sample_groups = np.array(sample_groups)
#
#     return residual_features, residual_targets, sample_info, sample_groups
#
#
# residual_X_train, residual_y_train, sample_info_train, residual_groups_train = build_residual_dataset(
#     train_df,
#     G_train,
#     Tb_pred_train,
#     Pc_pred_train,
#     train_arr["MW"],
#     V_pred_baseline_train
# )
#
# print(f"训练集残差特征形状: {residual_X_train.shape}")
# print(f"训练集残差目标形状: {residual_y_train.shape}")
#
#
# # GBDT 是树模型，不需要 StandardScaler
# residual_model = GradientBoostingRegressor(
#     n_estimators=500,
#     learning_rate=0.03,
#     max_depth=3,
#     subsample=0.9,
#     min_samples_split=2,
#     min_samples_leaf=1,
#     loss="squared_error",
#     random_state=42
# )
#
#
# # ========== 残差 GBDT 的 GroupKFold 交叉验证 ==========
# n_groups = len(np.unique(residual_groups_train))
#
# if n_groups >= 2:
#     n_splits = min(5, n_groups)
#     group_cv = GroupKFold(n_splits=n_splits)
#
#     cv_scores = cross_val_score(
#         residual_model,
#         residual_X_train,
#         residual_y_train,
#         cv=group_cv,
#         groups=residual_groups_train,
#         scoring="r2"
#     )
#
#     print(
#         f"残差 GBDT 模型 GroupKFold R2: "
#         f"{cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})"
#     )
# else:
#     cv_scores = None
#     print("训练集物质数不足，跳过残差 GBDT 模型 GroupKFold 交叉验证。")
#
#
# print("\n开始训练残差 GBDT 模型...")
# residual_model.fit(residual_X_train, residual_y_train)
#
# print("\n残差 GBDT 模型参数:")
# print(residual_model)
#
#
# # ========== 生成最终预测（基准 + GBDT残差修正） ==========
# def build_final_predictions(
#     df_part,
#     G_part,
#     Tb_pred_part,
#     Pc_pred_part,
#     MW_part,
#     V_pred_baseline_part
# ):
#     V_pred_final = pd.DataFrame(index=df_part.index, columns=v_cols, dtype=float)
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
#             baseline_pred = V_pred_baseline_part.at[i, vcol]
#
#             if pd.isna(baseline_pred) or baseline_pred <= 0:
#                 continue
#
#             base_features = list(G_part[i])
#
#             temp_features = [
#                 Tj[i],
#                 Tj[i] - Tb_pred_part[i],
#                 Tj[i] / Tb_pred_part[i] if Tb_pred_part[i] > 0 else 0.0,
#                 np.log(Tj[i]) if Tj[i] > 0 else 0.0,
#             ]
#
#             baseline_features = [
#                 np.log(baseline_pred)
#             ]
#
#             ref_features = [
#                 Tb_pred_part[i],
#                 np.log(101325.0),
#                 Pc_pred_part[i] if i < len(Pc_pred_part) else 0.0,
#             ]
#
#             mw_features = [
#                 MW_part[i][0] if i < len(MW_part) else 0.0
#             ]
#
#             all_features = (
#                 base_features
#                 + temp_features
#                 + baseline_features
#                 + ref_features
#                 + mw_features
#             )
#
#             features_list.append(all_features)
#             valid_indices.append(i)
#
#         if len(features_list) > 0:
#             features_array = np.array(features_list, dtype=float)
#
#             # GBDT 直接预测残差，不需要 scaler.transform
#             residual_pred = residual_model.predict(features_array)
#
#             for idx, residual_val in zip(valid_indices, residual_pred):
#                 baseline_pred = V_pred_baseline_part.at[idx, vcol]
#
#                 # ln(V_final) = ln(V_baseline) + residual_pred
#                 ln_V_final = np.log(baseline_pred) + residual_val
#
#                 V_pred_final.at[idx, vcol] = np.exp(ln_V_final)
#
#     return V_pred_final
#
#
# V_pred_final_train = build_final_predictions(
#     train_df,
#     G_train,
#     Tb_pred_train,
#     Pc_pred_train,
#     train_arr["MW"],
#     V_pred_baseline_train
# )
#
# V_pred_final_test = build_final_predictions(
#     test_df,
#     G_test,
#     Tb_pred_test,
#     Pc_pred_test,
#     test_arr["MW"],
#     V_pred_baseline_test
# )
#
#
# # ========== 评估：基线模型 / 最终模型（训练集、测试集分开） ==========
# def collect_log_true_pred(df_part, pred_df):
#     y_true_log = []
#     y_pred_log = []
#
#     for vcol in v_cols:
#         actual = df_part[vcol].to_numpy(dtype=float)
#         pred = pred_df[vcol].to_numpy(dtype=float)
#
#         m = (
#             np.isfinite(actual)
#             & np.isfinite(pred)
#             & (actual > 0)
#             & (pred > 0)
#         )
#
#         if np.any(m):
#             y_true_log.append(np.log(actual[m]))
#             y_pred_log.append(np.log(pred[m]))
#
#     if len(y_true_log) == 0:
#         return np.array([]), np.array([])
#
#     return np.concatenate(y_true_log), np.concatenate(y_pred_log)
#
#
# y_train_true_base, y_train_pred_base = collect_log_true_pred(
#     train_df,
#     V_pred_baseline_train
# )
#
# y_test_true_base, y_test_pred_base = collect_log_true_pred(
#     test_df,
#     V_pred_baseline_test
# )
#
# baseline_metrics_train, _ = eval_pressure_metrics(
#     y_train_true_base,
#     y_train_pred_base,
#     "Baseline_model",
#     "train"
# )
#
# baseline_metrics_test, _ = eval_pressure_metrics(
#     y_test_true_base,
#     y_test_pred_base,
#     "Baseline_model",
#     "test"
# )
#
#
# y_train_true_final, y_train_pred_final = collect_log_true_pred(
#     train_df,
#     V_pred_final_train
# )
#
# y_test_true_final, y_test_pred_final = collect_log_true_pred(
#     test_df,
#     V_pred_final_test
# )
#
# final_metrics_train, rel_err_train = eval_pressure_metrics(
#     y_train_true_final,
#     y_train_pred_final,
#     "Final_model_GBDT_residual",
#     "train"
# )
#
# final_metrics_test, rel_err_test = eval_pressure_metrics(
#     y_test_true_final,
#     y_test_pred_final,
#     "Final_model_GBDT_residual",
#     "test"
# )
#
#
# print("\n=== 分温度点评估（最终模型，训练集）===")
#
# for tcol, vcol in zip(temp_cols, v_cols):
#     actual = train_df[vcol].to_numpy(dtype=float)
#     pred = V_pred_final_train[vcol].to_numpy(dtype=float)
#
#     m = (
#         np.isfinite(actual)
#         & np.isfinite(pred)
#         & (actual > 0)
#         & (pred > 0)
#     )
#
#     if np.any(m):
#         mse_temp = mean_squared_error(np.log(actual[m]), np.log(pred[m]))
#         r2_temp = r2_score(np.log(actual[m]), np.log(pred[m]))
#
#         print(f"{tcol}: MSE_ln = {mse_temp:.6f}, R2_ln = {r2_temp:.6f}")
#
#
# print("\n=== 分温度点评估（最终模型，测试集）===")
#
# for tcol, vcol in zip(temp_cols, v_cols):
#     actual = test_df[vcol].to_numpy(dtype=float)
#     pred = V_pred_final_test[vcol].to_numpy(dtype=float)
#
#     m = (
#         np.isfinite(actual)
#         & np.isfinite(pred)
#         & (actual > 0)
#         & (pred > 0)
#     )
#
#     if np.any(m):
#         mse_temp = mean_squared_error(np.log(actual[m]), np.log(pred[m]))
#         r2_temp = r2_score(np.log(actual[m]), np.log(pred[m]))
#
#         print(f"{tcol}: MSE_ln = {mse_temp:.6f}, R2_ln = {r2_temp:.6f}")
#
#
# # ========== 保存结果 ==========
# def build_long_compare(
#     df_part,
#     split_name,
#     Tb_pred_part,
#     Pc_pred_part,
#     V_pred_baseline_part,
#     V_pred_final_part
# ):
#     rows = []
#
#     for idx in range(len(df_part)):
#         ID = df_part.at[idx, id_col]
#
#         for j, (tcol, vcol) in enumerate(zip(temp_cols, v_cols), start=1):
#             T_val = df_part.at[idx, tcol]
#             V_act = df_part.at[idx, vcol]
#
#             V_base = (
#                 V_pred_baseline_part.at[idx, vcol]
#                 if pd.notna(V_pred_baseline_part.at[idx, vcol])
#                 else np.nan
#             )
#
#             V_final = (
#                 V_pred_final_part.at[idx, vcol]
#                 if pd.notna(V_pred_final_part.at[idx, vcol])
#                 else np.nan
#             )
#
#             if pd.notna(V_act) and pd.notna(V_base) and V_act > 0 and V_base > 0:
#                 err_base_log = np.log(V_base) - np.log(V_act)
#             else:
#                 err_base_log = np.nan
#
#             if pd.notna(V_act) and pd.notna(V_final) and V_act > 0 and V_final > 0:
#                 err_final_log = np.log(V_final) - np.log(V_act)
#             else:
#                 err_final_log = np.nan
#
#             residual_correction = (
#                 np.log(V_final) - np.log(V_base)
#                 if (
#                     pd.notna(V_final)
#                     and pd.notna(V_base)
#                     and V_final > 0
#                     and V_base > 0
#                 )
#                 else np.nan
#             )
#
#             rows.append({
#                 "Split": split_name,
#                 id_col: ID,
#                 "temp_index": j,
#                 "temp_col": tcol,
#                 "T": T_val,
#                 "Vapor_Pressure_actual": V_act,
#                 "Vapor_Pressure_baseline": V_base,
#                 "Vapor_Pressure_final": V_final,
#                 "error_baseline_log": err_base_log,
#                 "error_final_log": err_final_log,
#                 "residual_correction_log": residual_correction,
#                 "T_ref": Tb_pred_part[idx],
#                 "Pc_pred": Pc_pred_part[idx]
#             })
#
#     return pd.DataFrame(rows)
#
#
# long_train = build_long_compare(
#     train_df,
#     "train",
#     Tb_pred_train,
#     Pc_pred_train,
#     V_pred_baseline_train,
#     V_pred_final_train
# )
#
# long_test = build_long_compare(
#     test_df,
#     "test",
#     Tb_pred_test,
#     Pc_pred_test,
#     V_pred_baseline_test,
#     V_pred_final_test
# )
#
# long_compare = pd.concat(
#     [long_train, long_test],
#     ignore_index=True
# ).sort_values(["Split", id_col, "temp_index"])
#
#
# tb_train_out = pd.DataFrame({
#     "Split": "train",
#     id_col: train_df[id_col].values,
#     "Tb_true": train_arr["Tb"],
#     "Tb_pred": Tb_pred_train
# })
#
# tb_test_out = pd.DataFrame({
#     "Split": "test",
#     id_col: test_df[id_col].values,
#     "Tb_true": test_arr["Tb"],
#     "Tb_pred": Tb_pred_test
# })
#
# pc_train_out = pd.DataFrame({
#     "Split": "train",
#     id_col: train_df[id_col].values,
#     "Pc_true_Pa": train_arr["Pc_bar"] * 1e5,
#     "Pc_pred_Pa": Pc_pred_train
# })
#
# pc_test_out = pd.DataFrame({
#     "Split": "test",
#     id_col: test_df[id_col].values,
#     "Pc_true_Pa": test_arr["Pc_bar"] * 1e5,
#     "Pc_pred_Pa": Pc_pred_test
# })
#
#
# summary_rows = [
#     tb_metrics_train,
#     tb_metrics_test,
#     pc_metrics_train,
#     pc_metrics_test,
#     baseline_metrics_train,
#     baseline_metrics_test,
#     final_metrics_train,
#     final_metrics_test
# ]
#
# summary_df = pd.DataFrame(summary_rows)
#
# out_path = "vapor_pressure_actual_vs_pred_with_residual_GBDT_train_test_split.xlsx"
#
# with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
#     long_compare.to_excel(writer, sheet_name="compare_long", index=False)
#     summary_df.to_excel(writer, sheet_name="summary", index=False)
#
#     pd.concat(
#         [tb_train_out, tb_test_out],
#         ignore_index=True
#     ).to_excel(writer, sheet_name="Tb_submodel", index=False)
#
#     pd.concat(
#         [pc_train_out, pc_test_out],
#         ignore_index=True
#     ).to_excel(writer, sheet_name="Pc_submodel", index=False)
#
#
# print(f"\n结果已保存到: {out_path}")
#
# print("\n总模型评估（基准 + 残差GBDT修正，测试集）：")
# print(f"R2_ln = {final_metrics_test['R2_lnP']:.4f}")
# print(f"MSE_ln = {final_metrics_test['MSE_lnP']:.6f}")
# print(f"ARD = {final_metrics_test['ARD_%']:.2f}%")
# print(f"误差 <= 1% 的数据点数量: {final_metrics_test['within_1pct']}")
# print(f"误差 <= 5% 的数据点数量: {final_metrics_test['within_5pct']}")
# print(f"误差 <= 10% 的数据点数量: {final_metrics_test['within_10pct']}")

import numpy as np
import pandas as pd

from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import HuberRegressor
from sklearn.ensemble import GradientBoostingRegressor
from scipy.optimize import least_squares
from sklearn.model_selection import train_test_split, GroupKFold, cross_val_score


# ========== 读取数据 ========== #
df = pd.read_excel("vp209.xlsx", sheet_name="Sheet1").copy()


# ========== 定义列 ========== #
id_col = df.columns[0]

group_cols = list(df.columns[12:31])   # 第13~31列：19个基团
temp_cols = list(df.columns[31:41])    # 第32~41列：10个温度
v_cols = list(df.columns[41:51])       # 第42~51列：10个蒸汽压

tb_col_idx = 5
mw_col_idx = 4
pc_col_idx = 51


# ========== 数据预处理 ========== #
for col in temp_cols + v_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df.iloc[:, tb_col_idx] = pd.to_numeric(df.iloc[:, tb_col_idx], errors="coerce")
df.iloc[:, mw_col_idx] = pd.to_numeric(df.iloc[:, mw_col_idx], errors="coerce")
df.iloc[:, pc_col_idx] = pd.to_numeric(df.iloc[:, pc_col_idx], errors="coerce")

Nk_all = df.iloc[:, 12:31].apply(pd.to_numeric, errors="coerce").values
P_vp_all = df.iloc[:, 41:51].apply(pd.to_numeric, errors="coerce").values


# ========== 创建有效掩码 ==========
valid_mask = np.isfinite(P_vp_all) & (P_vp_all > 0)
valid_mask = valid_mask.all(axis=1)

df_valid = df.loc[valid_mask].copy().reset_index(drop=True)

print(f"有效物质数: {len(df_valid)}")


# ========== 按物质 8:2 划分 ==========
unique_materials = df_valid[id_col].values

train_materials, test_materials = train_test_split(
    unique_materials,
    test_size=0.2,
    random_state=44
)

train_materials = set(train_materials)
test_materials = set(test_materials)

train_df = df_valid[df_valid[id_col].isin(train_materials)].copy().reset_index(drop=True)
test_df = df_valid[df_valid[id_col].isin(test_materials)].copy().reset_index(drop=True)

print(f"训练集物质数: {len(train_df)}, 测试集物质数: {len(test_df)}")


# ========== 工具函数 ==========
def get_arrays(df_part):
    return {
        "ids": df_part[id_col].values,
        "Nk": df_part.iloc[:, 12:31].apply(pd.to_numeric, errors="coerce").values,
        "T": df_part.iloc[:, 31:41].apply(pd.to_numeric, errors="coerce").values,
        "P_vp": df_part.iloc[:, 41:51].apply(pd.to_numeric, errors="coerce").values,
        "Tb": pd.to_numeric(df_part.iloc[:, tb_col_idx], errors="coerce").values,
        "MW": pd.to_numeric(df_part.iloc[:, mw_col_idx], errors="coerce").values.reshape(-1, 1),
        "Pc_bar": pd.to_numeric(df_part.iloc[:, pc_col_idx], errors="coerce").values,
    }


def evaluate_scalar_regression(y_true, y_pred, model_name, split_name):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true = y_true[mask]
    y_pred = y_pred[mask]

    if len(y_true) == 0:
        print(f"\n{model_name} - {split_name}: 无有效样本")
        return {
            "Model": model_name,
            "Split": split_name,
            "R2": np.nan,
            "MSE": np.nan
        }

    r2 = r2_score(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)

    print(f"\n{model_name} - {split_name}")
    print(f"R2  = {r2:.6f}")
    print(f"MSE = {mse:.6f}")

    return {
        "Model": model_name,
        "Split": split_name,
        "R2": r2,
        "MSE": mse
    }


def eval_pressure_metrics(y_true_log, y_pred_log, model_name, split_name, strict_less=False):
    y_true_log = np.asarray(y_true_log, dtype=float)
    y_pred_log = np.asarray(y_pred_log, dtype=float)

    mask = np.isfinite(y_true_log) & np.isfinite(y_pred_log)
    y_true_log = y_true_log[mask]
    y_pred_log = y_pred_log[mask]

    P_true = np.exp(y_true_log)
    P_pred = np.exp(y_pred_log)

    r2_ln = r2_score(y_true_log, y_pred_log)
    mse_ln = mean_squared_error(y_true_log, y_pred_log)

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

    print(f"\n{model_name} - {split_name}")
    print(f"ln(P)  R2 = {r2_ln:.6f}, MSE = {mse_ln:.6f}")
    print(f"P      R2 = {r2_P:.6f}, MSE = {mse_P:.6f}, ARD = {ard:.2f}%")

    if strict_less:
        print(f"误差 < 1% : {within_1pct} 点")
        print(f"误差 < 5% : {within_5pct} 点")
        print(f"误差 < 10%: {within_10pct} 点")
    else:
        print(f"误差 <= 1% : {within_1pct} 点")
        print(f"误差 <= 5% : {within_5pct} 点")
        print(f"误差 <= 10%: {within_10pct} 点")

    return {
        "Model": model_name,
        "Split": split_name,
        "R2_lnP": r2_ln,
        "MSE_lnP": mse_ln,
        "R2_P": r2_P,
        "MSE_P": mse_P,
        "ARD_%": ard,
        "within_1pct": within_1pct,
        "within_5pct": within_5pct,
        "within_10pct": within_10pct
    }, rel_err


train_arr = get_arrays(train_df)
test_arr = get_arrays(test_df)


# ========== 构建 Nk_poly（只在训练集 fit） ==========
poly = PolynomialFeatures(degree=2, include_bias=False)

Nk_poly_train = poly.fit_transform(train_arr["Nk"])
Nk_poly_test = poly.transform(test_arr["Nk"])


# ========== Tb 模型（只用训练集） ==========
Tb0 = 222.543

tb_train_mask = np.isfinite(train_arr["Tb"]) & np.isfinite(Nk_poly_train).all(axis=1)
tb_test_mask = np.isfinite(test_arr["Tb"]) & np.isfinite(Nk_poly_test).all(axis=1)

model_tb = HuberRegressor(max_iter=10000)

model_tb.fit(
    Nk_poly_train[tb_train_mask],
    np.exp(train_arr["Tb"][tb_train_mask] / Tb0)
)

Tb_pred_train = Tb0 * np.log(
    np.clip(model_tb.predict(Nk_poly_train), 1e-6, None)
)

Tb_pred_test = Tb0 * np.log(
    np.clip(model_tb.predict(Nk_poly_test), 1e-6, None)
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


# ========== Pc 模型（只用原始19个基团，不用 poly） ==========
Pc_bar_train = train_arr["Pc_bar"]
Pc_bar_test = test_arr["Pc_bar"]

MW_train_flat = train_arr["MW"].flatten()
MW_test_flat = test_arr["MW"].flatten()

Pc_X_train = train_arr["Nk"]
Pc_X_test = test_arr["Nk"]


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

    Pc_pred = 5.9827 + (1 / x_pred) ** 2 + beta3 * np.exp(
        1 / np.clip(MW, 1e-8, None)
    )

    return Pc_pred - Pc_true


pc_train_mask = (
    np.isfinite(Pc_bar_train)
    & np.isfinite(MW_train_flat)
    & np.isfinite(Pc_X_train).all(axis=1)
)

pc_test_mask = (
    np.isfinite(Pc_bar_test)
    & np.isfinite(MW_test_flat)
    & np.isfinite(Pc_X_test).all(axis=1)
)

params_init_pc = np.zeros(Pc_X_train.shape[1] + 1)

result_pc = least_squares(
    residual_pc,
    x0=params_init_pc,
    args=(
        Pc_X_train[pc_train_mask],
        MW_train_flat[pc_train_mask],
        Pc_bar_train[pc_train_mask]
    ),
    max_nfev=5000
)


def predict_pc_pa(Pc_X, MW_flat, result_pc):
    x_fit = Pc_X @ result_pc.x[:-1] + 0.108998

    x_fit = np.where(
        np.abs(x_fit) < 1e-8,
        np.sign(x_fit) * 1e-8 + (x_fit == 0) * 1e-8,
        x_fit
    )

    Pc_pred = 5.9827 + (1 / x_fit) ** 2 + result_pc.x[-1] * np.exp(
        1 / np.clip(MW_flat, 1e-8, None)
    )

    return Pc_pred * 1e5


Pc_pred_train = predict_pc_pa(Pc_X_train, MW_train_flat, result_pc)
Pc_pred_test = predict_pc_pa(Pc_X_test, MW_test_flat, result_pc)

pc_metrics_train = evaluate_scalar_regression(
    Pc_bar_train[pc_train_mask] * 1e5,
    Pc_pred_train[pc_train_mask],
    "Pc_submodel",
    "train"
)

pc_metrics_test = evaluate_scalar_regression(
    Pc_bar_test[pc_test_mask] * 1e5,
    Pc_pred_test[pc_test_mask],
    "Pc_submodel",
    "test"
)


# ========== 蒸汽压主模型：基线 A_k（只用训练集） ==========
G_train = train_arr["Nk"]
G_test = test_arr["Nk"]

X_rows_train = []
y_rows_train = []
group_ids_train = []

for i in range(len(train_df)):
    for tcol, vcol in zip(temp_cols, v_cols):
        Tj = train_df.at[i, tcol]
        Vj = train_df.at[i, vcol]

        if np.isnan(Tj) or np.isnan(Vj) or Vj <= 0:
            continue

        Tb_i = Tb_pred_train[i]
        V_ref = 101325.0

        Xj = (Tj - Tb_i) * G_train[i]
        yj = np.log(Vj) - np.log(V_ref)

        X_rows_train.append(Xj)
        y_rows_train.append(yj)
        group_ids_train.append(train_df.at[i, id_col])

X_A_train = np.array(X_rows_train, dtype=float)
y_A_train = np.array(y_rows_train, dtype=float)
group_ids_train = np.array(group_ids_train)

A_solver = HuberRegressor(fit_intercept=False, max_iter=5000)
A_solver.fit(X_A_train, y_A_train)

A_vec = A_solver.coef_


# ========== 生成基准蒸汽压预测（训练/测试分别生成） ==========
def build_baseline_predictions(df_part, G_part, Tb_pred_part):
    V_pred_baseline = pd.DataFrame(index=df_part.index, columns=v_cols, dtype=float)

    for i in range(len(df_part)):
        Tb_i = Tb_pred_part[i]
        V_ref = 101325.0

        for tcol, vcol in zip(temp_cols, v_cols):
            Tj = df_part.at[i, tcol]

            if np.isnan(Tj):
                V_pred_baseline.at[i, vcol] = np.nan
                continue

            Xj = (Tj - Tb_i) * G_part[i]
            ln_V_pred = np.log(V_ref) + Xj @ A_vec

            V_pred_baseline.at[i, vcol] = np.exp(ln_V_pred)

    return V_pred_baseline


V_pred_baseline_train = build_baseline_predictions(
    train_df,
    G_train,
    Tb_pred_train
)

V_pred_baseline_test = build_baseline_predictions(
    test_df,
    G_test,
    Tb_pred_test
)


# ========== 残差 GBDT 模型（只用训练集） ==========
print("\n训练残差 GBDT 模型...")


def build_residual_dataset(
    df_part,
    G_part,
    Tb_pred_part,
    Pc_pred_part,
    MW_part,
    V_pred_baseline_part
):
    residual_features = []
    residual_targets = []
    sample_info = []
    sample_groups = []

    for tcol, vcol in zip(temp_cols, v_cols):
        Tj = df_part[tcol].to_numpy(dtype=float)
        Vj = df_part[vcol].to_numpy(dtype=float)

        msk = (
            (~np.isnan(Tj))
            & (~np.isnan(Vj))
            & (Vj > 0)
            & (~V_pred_baseline_part[vcol].isna().to_numpy())
        )

        for i in np.where(msk)[0]:
            baseline_pred = V_pred_baseline_part.at[i, vcol]

            if not np.isfinite(baseline_pred) or baseline_pred <= 0:
                continue

            base_features = list(G_part[i])

            temp_features = [
                Tj[i],
                Tj[i] - Tb_pred_part[i],
                Tj[i] / Tb_pred_part[i] if Tb_pred_part[i] > 0 else 0.0,
                np.log(Tj[i]) if Tj[i] > 0 else 0.0,
            ]

            baseline_features = [
                np.log(baseline_pred)
            ]

            ref_features = [
                Tb_pred_part[i],
                np.log(101325.0),
                Pc_pred_part[i] if i < len(Pc_pred_part) else 0.0,
            ]

            mw_features = [
                MW_part[i][0] if i < len(MW_part) else 0.0
            ]

            all_features = (
                base_features
                + temp_features
                + baseline_features
                + ref_features
                + mw_features
            )

            residual_features.append(all_features)

            # 残差目标：ln(V_actual) - ln(V_baseline)
            residual = np.log(Vj[i]) - np.log(baseline_pred)
            residual_targets.append(residual)

            sample_info.append((i, tcol, vcol))
            sample_groups.append(df_part.at[i, id_col])

    residual_features = np.array(residual_features, dtype=float)
    residual_targets = np.array(residual_targets, dtype=float)
    sample_groups = np.array(sample_groups)

    return residual_features, residual_targets, sample_info, sample_groups


residual_X_train, residual_y_train, sample_info_train, residual_groups_train = build_residual_dataset(
    train_df,
    G_train,
    Tb_pred_train,
    Pc_pred_train,
    train_arr["MW"],
    V_pred_baseline_train
)

print(f"训练集残差特征形状: {residual_X_train.shape}")
print(f"训练集残差目标形状: {residual_y_train.shape}")


residual_model = GradientBoostingRegressor(
    n_estimators=500,
    learning_rate=0.03,
    max_depth=3,
    subsample=0.9,
    min_samples_split=2,
    min_samples_leaf=1,
    loss="squared_error",
    random_state=42
)


# ========== 残差 GBDT 的 GroupKFold 交叉验证 ==========
n_groups = len(np.unique(residual_groups_train))

if n_groups >= 2:
    n_splits = min(5, n_groups)
    group_cv = GroupKFold(n_splits=n_splits)

    cv_scores = cross_val_score(
        residual_model,
        residual_X_train,
        residual_y_train,
        cv=group_cv,
        groups=residual_groups_train,
        scoring="r2"
    )

    print(
        f"残差 GBDT 模型 GroupKFold R2: "
        f"{cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})"
    )
else:
    cv_scores = None
    print("训练集物质数不足，跳过残差 GBDT 模型 GroupKFold 交叉验证。")


print("\n开始训练残差 GBDT 模型...")
residual_model.fit(residual_X_train, residual_y_train)

print("\n残差 GBDT 模型参数:")
print(residual_model)


# ========== 生成最终预测（基准 + GBDT残差修正） ==========
def build_final_predictions(
    df_part,
    G_part,
    Tb_pred_part,
    Pc_pred_part,
    MW_part,
    V_pred_baseline_part
):
    V_pred_final = pd.DataFrame(index=df_part.index, columns=v_cols, dtype=float)

    for tcol, vcol in zip(temp_cols, v_cols):
        Tj = df_part[tcol].to_numpy(dtype=float)

        features_list = []
        valid_indices = []

        for i in range(len(df_part)):
            if np.isnan(Tj[i]):
                continue

            baseline_pred = V_pred_baseline_part.at[i, vcol]

            if pd.isna(baseline_pred) or baseline_pred <= 0:
                continue

            base_features = list(G_part[i])

            temp_features = [
                Tj[i],
                Tj[i] - Tb_pred_part[i],
                Tj[i] / Tb_pred_part[i] if Tb_pred_part[i] > 0 else 0.0,
                np.log(Tj[i]) if Tj[i] > 0 else 0.0,
            ]

            baseline_features = [
                np.log(baseline_pred)
            ]

            ref_features = [
                Tb_pred_part[i],
                np.log(101325.0),
                Pc_pred_part[i] if i < len(Pc_pred_part) else 0.0,
            ]

            mw_features = [
                MW_part[i][0] if i < len(MW_part) else 0.0
            ]

            all_features = (
                base_features
                + temp_features
                + baseline_features
                + ref_features
                + mw_features
            )

            features_list.append(all_features)
            valid_indices.append(i)

        if len(features_list) > 0:
            features_array = np.array(features_list, dtype=float)

            residual_pred = residual_model.predict(features_array)

            for idx, residual_val in zip(valid_indices, residual_pred):
                baseline_pred = V_pred_baseline_part.at[idx, vcol]

                # ln(V_final) = ln(V_baseline) + residual_pred
                ln_V_final = np.log(baseline_pred) + residual_val

                V_pred_final.at[idx, vcol] = np.exp(ln_V_final)

    return V_pred_final


V_pred_final_train = build_final_predictions(
    train_df,
    G_train,
    Tb_pred_train,
    Pc_pred_train,
    train_arr["MW"],
    V_pred_baseline_train
)

V_pred_final_test = build_final_predictions(
    test_df,
    G_test,
    Tb_pred_test,
    Pc_pred_test,
    test_arr["MW"],
    V_pred_baseline_test
)


# ========== 评估：基线模型 / 最终模型（训练集、测试集分开） ==========
def collect_log_true_pred(df_part, pred_df):
    y_true_log = []
    y_pred_log = []

    for vcol in v_cols:
        actual = df_part[vcol].to_numpy(dtype=float)
        pred = pred_df[vcol].to_numpy(dtype=float)

        m = (
            np.isfinite(actual)
            & np.isfinite(pred)
            & (actual > 0)
            & (pred > 0)
        )

        if np.any(m):
            y_true_log.append(np.log(actual[m]))
            y_pred_log.append(np.log(pred[m]))

    if len(y_true_log) == 0:
        return np.array([]), np.array([])

    return np.concatenate(y_true_log), np.concatenate(y_pred_log)


y_train_true_base, y_train_pred_base = collect_log_true_pred(
    train_df,
    V_pred_baseline_train
)

y_test_true_base, y_test_pred_base = collect_log_true_pred(
    test_df,
    V_pred_baseline_test
)

baseline_metrics_train, _ = eval_pressure_metrics(
    y_train_true_base,
    y_train_pred_base,
    "Baseline_model",
    "train",
    strict_less=False
)

baseline_metrics_test, _ = eval_pressure_metrics(
    y_test_true_base,
    y_test_pred_base,
    "Baseline_model",
    "test",
    strict_less=False
)


y_train_true_final, y_train_pred_final = collect_log_true_pred(
    train_df,
    V_pred_final_train
)

y_test_true_final, y_test_pred_final = collect_log_true_pred(
    test_df,
    V_pred_final_test
)

final_metrics_train, rel_err_train = eval_pressure_metrics(
    y_train_true_final,
    y_train_pred_final,
    "Final_model_GBDT_residual",
    "train",
    strict_less=False
)

final_metrics_test, rel_err_test = eval_pressure_metrics(
    y_test_true_final,
    y_test_pred_final,
    "Final_model_GBDT_residual",
    "test",
    strict_less=False
)


# ========== 完整数据集统计：训练集 + 测试集 ==========
y_all_true_base = np.concatenate([y_train_true_base, y_test_true_base])
y_all_pred_base = np.concatenate([y_train_pred_base, y_test_pred_base])

baseline_metrics_all, rel_err_base_all = eval_pressure_metrics(
    y_all_true_base,
    y_all_pred_base,
    "Baseline_model",
    "all_train_plus_test",
    strict_less=True
)

y_all_true_final = np.concatenate([y_train_true_final, y_test_true_final])
y_all_pred_final = np.concatenate([y_train_pred_final, y_test_pred_final])

final_metrics_all, rel_err_final_all = eval_pressure_metrics(
    y_all_true_final,
    y_all_pred_final,
    "Final_model_GBDT_residual",
    "all_train_plus_test",
    strict_less=True
)

print("\nFinal_model_GBDT_residual 完整数据集实际蒸汽压 P 预测偏差 1%，5%，10%分别为：")
print(final_metrics_all["within_1pct"])
print(final_metrics_all["within_5pct"])
print(final_metrics_all["within_10pct"])


print("\n=== 分温度点评估（最终模型，训练集）===")

for tcol, vcol in zip(temp_cols, v_cols):
    actual = train_df[vcol].to_numpy(dtype=float)
    pred = V_pred_final_train[vcol].to_numpy(dtype=float)

    m = (
        np.isfinite(actual)
        & np.isfinite(pred)
        & (actual > 0)
        & (pred > 0)
    )

    if np.any(m):
        mse_temp = mean_squared_error(np.log(actual[m]), np.log(pred[m]))
        r2_temp = r2_score(np.log(actual[m]), np.log(pred[m]))

        print(f"{tcol}: MSE_ln = {mse_temp:.6f}, R2_ln = {r2_temp:.6f}")


print("\n=== 分温度点评估（最终模型，测试集）===")

for tcol, vcol in zip(temp_cols, v_cols):
    actual = test_df[vcol].to_numpy(dtype=float)
    pred = V_pred_final_test[vcol].to_numpy(dtype=float)

    m = (
        np.isfinite(actual)
        & np.isfinite(pred)
        & (actual > 0)
        & (pred > 0)
    )

    if np.any(m):
        mse_temp = mean_squared_error(np.log(actual[m]), np.log(pred[m]))
        r2_temp = r2_score(np.log(actual[m]), np.log(pred[m]))

        print(f"{tcol}: MSE_ln = {mse_temp:.6f}, R2_ln = {r2_temp:.6f}")


# ========== 保存结果 ==========
def build_long_compare(
    df_part,
    split_name,
    Tb_pred_part,
    Pc_pred_part,
    V_pred_baseline_part,
    V_pred_final_part
):
    rows = []

    for idx in range(len(df_part)):
        ID = df_part.at[idx, id_col]

        for j, (tcol, vcol) in enumerate(zip(temp_cols, v_cols), start=1):
            T_val = df_part.at[idx, tcol]
            V_act = df_part.at[idx, vcol]

            V_base = (
                V_pred_baseline_part.at[idx, vcol]
                if pd.notna(V_pred_baseline_part.at[idx, vcol])
                else np.nan
            )

            V_final = (
                V_pred_final_part.at[idx, vcol]
                if pd.notna(V_pred_final_part.at[idx, vcol])
                else np.nan
            )

            if pd.notna(V_act) and pd.notna(V_base) and V_act > 0 and V_base > 0:
                err_base_log = np.log(V_base) - np.log(V_act)
                rel_err_base = abs((V_base - V_act) / V_act) * 100
            else:
                err_base_log = np.nan
                rel_err_base = np.nan

            if pd.notna(V_act) and pd.notna(V_final) and V_act > 0 and V_final > 0:
                err_final_log = np.log(V_final) - np.log(V_act)
                rel_err_final = abs((V_final - V_act) / V_act) * 100
            else:
                err_final_log = np.nan
                rel_err_final = np.nan

            residual_correction = (
                np.log(V_final) - np.log(V_base)
                if (
                    pd.notna(V_final)
                    and pd.notna(V_base)
                    and V_final > 0
                    and V_base > 0
                )
                else np.nan
            )

            rows.append({
                "Split": split_name,
                id_col: ID,
                "temp_index": j,
                "temp_col": tcol,
                "T": T_val,
                "Vapor_Pressure_actual": V_act,
                "Vapor_Pressure_baseline": V_base,
                "Vapor_Pressure_final": V_final,
                "Relative_Error_Baseline_%": rel_err_base,
                "Relative_Error_Final_%": rel_err_final,
                "error_baseline_log": err_base_log,
                "error_final_log": err_final_log,
                "residual_correction_log": residual_correction,
                "T_ref": Tb_pred_part[idx],
                "Pc_pred": Pc_pred_part[idx]
            })

    return pd.DataFrame(rows)


long_train = build_long_compare(
    train_df,
    "train",
    Tb_pred_train,
    Pc_pred_train,
    V_pred_baseline_train,
    V_pred_final_train
)

long_test = build_long_compare(
    test_df,
    "test",
    Tb_pred_test,
    Pc_pred_test,
    V_pred_baseline_test,
    V_pred_final_test
)

long_compare = pd.concat(
    [long_train, long_test],
    ignore_index=True
).sort_values(["Split", id_col, "temp_index"])

long_all = long_compare.copy()
long_all["Split"] = "all_train_plus_test"


tb_train_out = pd.DataFrame({
    "Split": "train",
    id_col: train_df[id_col].values,
    "Tb_true": train_arr["Tb"],
    "Tb_pred": Tb_pred_train
})

tb_test_out = pd.DataFrame({
    "Split": "test",
    id_col: test_df[id_col].values,
    "Tb_true": test_arr["Tb"],
    "Tb_pred": Tb_pred_test
})

pc_train_out = pd.DataFrame({
    "Split": "train",
    id_col: train_df[id_col].values,
    "Pc_true_Pa": train_arr["Pc_bar"] * 1e5,
    "Pc_pred_Pa": Pc_pred_train
})

pc_test_out = pd.DataFrame({
    "Split": "test",
    id_col: test_df[id_col].values,
    "Pc_true_Pa": test_arr["Pc_bar"] * 1e5,
    "Pc_pred_Pa": Pc_pred_test
})


summary_rows = [
    tb_metrics_train,
    tb_metrics_test,
    pc_metrics_train,
    pc_metrics_test,
    baseline_metrics_train,
    baseline_metrics_test,
    baseline_metrics_all,
    final_metrics_train,
    final_metrics_test,
    final_metrics_all
]

summary_df = pd.DataFrame(summary_rows)

out_path = "vapor_pressure_actual_vs_pred_with_residual_GBDT_train_test_split.xlsx"

with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
    long_compare.to_excel(writer, sheet_name="compare_long", index=False)
    long_all.to_excel(writer, sheet_name="all_compare_long", index=False)
    summary_df.to_excel(writer, sheet_name="summary", index=False)

    pd.concat(
        [tb_train_out, tb_test_out],
        ignore_index=True
    ).to_excel(writer, sheet_name="Tb_submodel", index=False)

    pd.concat(
        [pc_train_out, pc_test_out],
        ignore_index=True
    ).to_excel(writer, sheet_name="Pc_submodel", index=False)


print(f"\n结果已保存到: {out_path}")

print("\n总模型评估（基准 + 残差GBDT修正，测试集）：")
print(f"R2_ln = {final_metrics_test['R2_lnP']:.4f}")
print(f"MSE_ln = {final_metrics_test['MSE_lnP']:.6f}")
print(f"ARD = {final_metrics_test['ARD_%']:.2f}%")
print(f"误差 <= 1% 的数据点数量: {final_metrics_test['within_1pct']}")
print(f"误差 <= 5% 的数据点数量: {final_metrics_test['within_5pct']}")
print(f"误差 <= 10% 的数据点数量: {final_metrics_test['within_10pct']}")

print("\n总模型评估（基准 + 残差GBDT修正，完整数据集 train + test）：")
print(f"R2_ln = {final_metrics_all['R2_lnP']:.4f}")
print(f"MSE_ln = {final_metrics_all['MSE_lnP']:.6f}")
print(f"ARD = {final_metrics_all['ARD_%']:.2f}%")
print("1%，5%，10%分别为：")
print(final_metrics_all["within_1pct"])
print(final_metrics_all["within_5pct"])
print(final_metrics_all["within_10pct"])

print("\n当前蒸汽压 baseline + GBDT residual 模型结构:")
print("Tb_submodel: HuberRegressor(max_iter=10000), input = PolynomialFeatures(Nk, degree=2)")
print("Pc_submodel: least_squares explicit Pc equation, input = Nk + MW")
print("Baseline: HuberRegressor(fit_intercept=False, max_iter=5000), target = ln(V)-ln(Pb), input = (T-Tb_pred)*Nk")
print("Residual model: GradientBoostingRegressor(n_estimators=500, learning_rate=0.03, max_depth=3, subsample=0.9, random_state=42)")
print("Residual target: ln(V_actual)-ln(V_baseline)")
print("Residual features: Nk + T + (T-Tb) + T/Tb + ln(T) + ln(V_baseline) + Tb_pred + ln(Pb) + Pc_pred + MW")
print("Final prediction: ln(V_final)=ln(V_baseline)+residual_pred")