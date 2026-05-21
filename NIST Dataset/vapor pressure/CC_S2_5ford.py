# # import pandas as pd
# # import numpy as np
# # from pathlib import Path
# #
# # from sklearn.linear_model import RidgeCV
# # from sklearn.model_selection import KFold
# # from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
# # from sklearn.pipeline import make_pipeline
# # from sklearn.preprocessing import StandardScaler
# #
# # from scipy.stats import ttest_rel
# # import warnings
# #
# # warnings.filterwarnings("ignore")
# #
# # pd.set_option("display.float_format", "{:.10f}".format)
# # np.set_printoptions(suppress=True, precision=10)
# #
# #
# # # =========================================================
# # # 0. 用户配置
# # # =========================================================
# # input_file = Path("dataset_selected_by_two_k_with_lnP_invT_interpolation_8points.xlsx")
# #
# # data_sheet = "Data_selected"
# # groups_sheet = "Groups_selected"
# # anchor_sheet = "Interpolated_k1_k2"
# #
# # material_key_col = "material_key"
# # temp_col = "T_K"
# #
# # target_candidates = [
# #     "lnP_kPa",
# #     "lnP",
# #     "ln_VaporPressure_kPa",
# #     "ln_pressure",
# # ]
# #
# # pressure_candidates = [
# #     "VaporPressure_kPa",
# #     "vapor_pressure_kPa",
# #     "Vapor_Pressure_kPa",
# #     "P_vapor_kPa",
# #     "property_value",
# # ]
# #
# # anchor_lnp_col = "lnP_kPa_interp_at_k1Tb"
# # anchor_T_col = "k1_times_boiling_T_K"
# # boiling_col = "boiling_T_K"
# # k1_col = "k1"
# #
# # n_group_features_to_use = 220
# # use_fixed_group_position = True
# # group_start_col_1based = 3
# # group_end_col_1based = 222
# #
# # random_state = 42
# # n_outer_folds = 5
# #
# # # 锚点子模型参数：保持原设定
# # hgb_params = dict(
# #     loss="squared_error",
# #     max_iter=1200,
# #     learning_rate=0.03,
# #     max_leaf_nodes=63,
# #     min_samples_leaf=2,
# #     l2_regularization=0.0,
# #     early_stopping=False,
# #     random_state=random_state,
# # )
# #
# # # 统一回归器参数
# # ridgecv_alphas = np.logspace(-4, 5, 60)
# #
# # # 是否保存更详细的逐物质 A/B 诊断结果
# # save_ab_diagnostics = True
# #
# #
# # # =========================================================
# # # 1. 工具函数
# # # =========================================================
# # def is_valid_value(x):
# #     if pd.isna(x):
# #         return False
# #
# #     s = str(x).strip()
# #
# #     if s == "" or s.lower() in ["nan", "none", "null", "待定"]:
# #         return False
# #
# #     return True
# #
# #
# # def build_material_key(row):
# #     for col in ["material_key", "inchikey", "cas", "compound_name", "formula"]:
# #         if col in row.index and is_valid_value(row[col]):
# #             if col == "material_key":
# #                 return str(row[col]).strip()
# #             return f"{col}:{str(row[col]).strip()}"
# #
# #     return "unknown_material"
# #
# #
# # def find_first_existing_col(df, candidates, col_type, required=True):
# #     for col in candidates:
# #         if col in df.columns:
# #             return col
# #
# #     lower_map = {str(c).lower(): c for c in df.columns}
# #
# #     for col in candidates:
# #         if str(col).lower() in lower_map:
# #             return lower_map[str(col).lower()]
# #
# #     if required:
# #         raise ValueError(f"没有找到 {col_type} 列。候选: {candidates}")
# #
# #     return None
# #
# #
# # def identify_group_columns(df_groups, n=220):
# #     if use_fixed_group_position:
# #         start_idx = group_start_col_1based - 1
# #         end_excl = group_end_col_1based
# #
# #         if len(df_groups.columns) < end_excl:
# #             raise ValueError(
# #                 f"基团列数不足，需要到第 {group_end_col_1based} 列，"
# #                 f"但当前只有 {len(df_groups.columns)} 列。"
# #             )
# #
# #         group_cols = list(df_groups.columns[start_idx:end_excl])
# #
# #         if len(group_cols) != n:
# #             raise ValueError(f"固定位置识别 {len(group_cols)} 个基团，需要 {n} 个。")
# #
# #         return group_cols
# #
# #     raise ValueError("请设置 use_fixed_group_position=True")
# #
# #
# # def safe_exp(x):
# #     return np.exp(np.clip(x, -700, 700))
# #
# #
# # def evaluate_metrics(y_true, y_pred):
# #     """
# #     计算 R2, RMSE, MAE, ARD(%)
# #
# #     注意：
# #     当前 y_true/y_pred 是 lnP，因此 ARD 是基于 lnP 的相对误差。
# #     如果需要蒸汽压 P 空间的 ARD，需要对 lnP 取 exp 后再算。
# #     """
# #     y_true = np.asarray(y_true, dtype=float)
# #     y_pred = np.asarray(y_pred, dtype=float)
# #
# #     mask = np.isfinite(y_true) & np.isfinite(y_pred)
# #
# #     y_true = y_true[mask]
# #     y_pred = y_pred[mask]
# #
# #     if len(y_true) == 0:
# #         return {
# #             "R2": np.nan,
# #             "RMSE": np.nan,
# #             "MAE": np.nan,
# #             "ARD": np.nan,
# #         }
# #
# #     r2 = r2_score(y_true, y_pred)
# #     rmse = np.sqrt(mean_squared_error(y_true, y_pred))
# #     mae = mean_absolute_error(y_true, y_pred)
# #
# #     denom_mask = np.abs(y_true) > 1e-12
# #
# #     if denom_mask.sum() == 0:
# #         ard = np.nan
# #     else:
# #         ard = (
# #             np.mean(
# #                 np.abs(
# #                     (y_pred[denom_mask] - y_true[denom_mask])
# #                     / y_true[denom_mask]
# #                 )
# #             )
# #             * 100
# #         )
# #
# #     return {
# #         "R2": r2,
# #         "RMSE": rmse,
# #         "MAE": mae,
# #         "ARD": ard,
# #     }
# #
# #
# # def train_anchor_submodel(X, y):
# #     """
# #     锚点子模型。
# #     这里保留你的原始设定：HistGradientBoostingRegressor。
# #     """
# #     from sklearn.ensemble import HistGradientBoostingRegressor
# #
# #     model = HistGradientBoostingRegressor(**hgb_params)
# #     model.fit(X, y)
# #
# #     return model
# #
# #
# # def add_constant_feature(X):
# #     """
# #     给特征矩阵前面添加一列常数 1。
# #
# #     目的：
# #     1. 统一使用 fit_intercept=False。
# #     2. Clausius A/B 模型仍然可以学习常数项。
# #     3. 锚点基线中，常数列乘以 delta_InvT 后，相当于学习一个全局 slope 项。
# #     """
# #     X = np.asarray(X, dtype=float)
# #
# #     if X.ndim != 2:
# #         raise ValueError("X 必须是二维数组。")
# #
# #     ones = np.ones((X.shape[0], 1), dtype=float)
# #
# #     return np.hstack([ones, X])
# #
# #
# # def make_common_regressor():
# #     """
# #     两个基线统一使用的回归器。
# #
# #     StandardScaler(with_mean=False):
# #         不做中心化，保证零输入仍然映射为零输入。
# #         对锚点基线很重要，因为 delta_InvT = 0 时，
# #         修正项必须为 0。
# #
# #     RidgeCV(fit_intercept=False):
# #         不使用内置截距。
# #         截距由 add_constant_feature() 添加的常数列承担。
# #     """
# #     return make_pipeline(
# #         StandardScaler(with_mean=False),
# #         RidgeCV(
# #             alphas=ridgecv_alphas,
# #             fit_intercept=False,
# #         ),
# #     )
# #
# #
# # # =========================================================
# # # 2. 读取数据
# # # =========================================================
# # df_data = pd.read_excel(input_file, sheet_name=data_sheet)
# # df_groups_raw = pd.read_excel(input_file, sheet_name=groups_sheet)
# # df_anchor = pd.read_excel(input_file, sheet_name=anchor_sheet)
# #
# # # 物质 ID 对齐
# # for df in [df_data, df_groups_raw, df_anchor]:
# #     if material_key_col not in df.columns:
# #         df[material_key_col] = df.apply(build_material_key, axis=1)
# #
# #     df[material_key_col] = df[material_key_col].astype(str).str.strip()
# #
# # # 找目标列
# # target_col = find_first_existing_col(
# #     df_data,
# #     target_candidates,
# #     "lnP",
# #     required=True,
# # )
# #
# # pressure_col = find_first_existing_col(
# #     df_data,
# #     pressure_candidates,
# #     "压力",
# #     required=False,
# # )
# #
# # print(f"使用目标列: {target_col}")
# #
# # if pressure_col is not None:
# #     print(f"检测到压力列: {pressure_col}")
# #
# #
# # # =========================================================
# # # 3. 基团列处理
# # # =========================================================
# # group_cols_220 = identify_group_columns(
# #     df_groups_raw,
# #     n=n_group_features_to_use,
# # )
# #
# # df_groups_numeric = (
# #     df_groups_raw[group_cols_220]
# #     .apply(pd.to_numeric, errors="coerce")
# #     .fillna(0.0)
# # )
# #
# # # 删除全零基团列
# # nonzero_mask = df_groups_numeric.abs().sum(axis=0) != 0
# # used_group_cols = df_groups_numeric.columns[nonzero_mask].tolist()
# # df_groups_used = df_groups_numeric[used_group_cols].copy()
# #
# # print("有效基团数:", len(used_group_cols))
# #
# #
# # # =========================================================
# # # 4. 锚点数据准备
# # # =========================================================
# # if k1_col in df_anchor.columns:
# #     df_anchor["k1_for_anchor"] = pd.to_numeric(
# #         df_anchor[k1_col],
# #         errors="coerce",
# #     )
# #
# # elif anchor_T_col in df_anchor.columns:
# #     df_anchor["k1_for_anchor"] = (
# #         pd.to_numeric(df_anchor[anchor_T_col], errors="coerce")
# #         / pd.to_numeric(df_anchor[boiling_col], errors="coerce")
# #     )
# #
# # else:
# #     raise ValueError("无法获得 k1。请检查 k1 或 k1_times_boiling_T_K / boiling_T_K 列。")
# #
# # k1_median = df_anchor["k1_for_anchor"].median()
# # df_anchor["k1_for_anchor"] = df_anchor["k1_for_anchor"].fillna(k1_median)
# #
# # required_anchor_cols = [
# #     material_key_col,
# #     anchor_lnp_col,
# #     boiling_col,
# #     "k1_for_anchor",
# # ]
# #
# # for col in required_anchor_cols:
# #     if col not in df_anchor.columns:
# #         raise ValueError(f"锚点表中缺少必要列: {col}")
# #
# #
# # # =========================================================
# # # 5. 构造物质级数据
# # # =========================================================
# # df_material = df_groups_used.reset_index().rename(columns={"index": "orig_idx"})
# # df_material[material_key_col] = df_groups_raw.loc[
# #     df_material.index,
# #     material_key_col,
# # ].values
# #
# # df_material = df_material.merge(
# #     df_anchor[
# #         [
# #             material_key_col,
# #             anchor_lnp_col,
# #             boiling_col,
# #             "k1_for_anchor",
# #         ]
# #     ],
# #     on=material_key_col,
# #     how="left",
# # )
# #
# # df_material = df_material.dropna(
# #     subset=used_group_cols + [anchor_lnp_col, boiling_col, "k1_for_anchor"]
# # )
# #
# # df_material = df_material.reset_index(drop=True)
# #
# # print("可用于物质级建模的物质数:", len(df_material))
# #
# #
# # # =========================================================
# # # 6. 训练全局锚点模型
# # # =========================================================
# # # 注意：
# # # 根据你的实验设定，这里允许使用全数据训练锚点模型。
# # # 即测试集物质也可以拥有特定锚点信息或由全局锚点模块给出锚点约束。
# # X_anchor_mat = df_material[used_group_cols].values.astype(float)
# # y_anchor_lnp = df_material[anchor_lnp_col].values.astype(float)
# # y_boiling = df_material[boiling_col].values.astype(float)
# #
# # valid_anchor = (
# #     np.isfinite(X_anchor_mat).all(axis=1)
# #     & np.isfinite(y_anchor_lnp)
# #     & np.isfinite(y_boiling)
# #     & (y_boiling > 0)
# # )
# #
# # X_anchor_mat_valid = X_anchor_mat[valid_anchor]
# # y_anchor_lnp_valid = y_anchor_lnp[valid_anchor]
# # y_boiling_valid = y_boiling[valid_anchor]
# #
# # anchor_lnP_model = train_anchor_submodel(
# #     X_anchor_mat_valid,
# #     y_anchor_lnp_valid,
# # )
# #
# # anchor_boiling_model = train_anchor_submodel(
# #     X_anchor_mat_valid,
# #     y_boiling_valid,
# # )
# #
# # # 预测所有物质的锚点
# # X_all_groups = df_material[used_group_cols].values.astype(float)
# #
# # df_material["lnP_anchor_pred"] = anchor_lnP_model.predict(X_all_groups)
# # df_material["boiling_T_K_pred"] = anchor_boiling_model.predict(X_all_groups)
# # df_material["anchor_T_pred_K"] = (
# #     df_material["k1_for_anchor"] * df_material["boiling_T_K_pred"]
# # )
# # df_material["invT_anchor_pred_1_per_K"] = 1.0 / df_material["anchor_T_pred_K"]
# #
# #
# # # =========================================================
# # # 7. 展开温度点数据
# # # =========================================================
# # df_data[temp_col] = pd.to_numeric(
# #     df_data[temp_col],
# #     errors="coerce",
# # )
# #
# # df_data[target_col] = pd.to_numeric(
# #     df_data[target_col],
# #     errors="coerce",
# # )
# #
# # df_data["InvT"] = 1.0 / df_data[temp_col]
# #
# # df_long = df_data.merge(
# #     df_material[
# #         [material_key_col]
# #         + used_group_cols
# #         + [
# #             "lnP_anchor_pred",
# #             "boiling_T_K_pred",
# #             "anchor_T_pred_K",
# #             "invT_anchor_pred_1_per_K",
# #             "k1_for_anchor",
# #         ]
# #     ],
# #     on=material_key_col,
# #     how="inner",
# # )
# #
# # df_long = df_long.dropna(
# #     subset=[
# #         target_col,
# #         temp_col,
# #         "InvT",
# #         "lnP_anchor_pred",
# #         "invT_anchor_pred_1_per_K",
# #     ]
# #     + used_group_cols
# # )
# #
# # df_long = df_long.reset_index(drop=True)
# #
# # # 提取数组
# # X_groups = df_long[used_group_cols].values.astype(float)
# # InvT = df_long["InvT"].values.astype(float)
# # T_values = df_long[temp_col].values.astype(float)
# #
# # lnP_true = df_long[target_col].values.astype(float)
# # lnP_anchor = df_long["lnP_anchor_pred"].values.astype(float)
# # boiling_T_pred = df_long["boiling_T_K_pred"].values.astype(float)
# # anchor_T_pred = df_long["anchor_T_pred_K"].values.astype(float)
# # invT_anchor = df_long["invT_anchor_pred_1_per_K"].values.astype(float)
# #
# # material_keys = df_long[material_key_col].values.astype(str)
# # unique_materials = np.unique(material_keys)
# #
# # print(f"总温度点数: {len(lnP_true)}")
# # print(f"物质数: {len(unique_materials)}")
# #
# #
# # # =========================================================
# # # 8. 为每个物质拟合真实 Clausius-Clapeyron 参数
# # #    lnP = A + B * InvT
# # # =========================================================
# # material_to_AB = {}
# #
# # for mat in unique_materials:
# #     mask = material_keys == mat
# #
# #     x_mat = InvT[mask]        # x = 1 / T
# #     y_mat = lnP_true[mask]    # y = lnP
# #
# #     valid = np.isfinite(x_mat) & np.isfinite(y_mat)
# #
# #     x_mat = x_mat[valid]
# #     y_mat = y_mat[valid]
# #
# #     if len(x_mat) >= 2 and np.std(x_mat) > 0:
# #         # 关键修正：
# #         # np.polyfit(x, y, 1) 返回 [slope, intercept]
# #         # 对 lnP = A + B * InvT：
# #         # B = slope
# #         # A = intercept
# #         B, A = np.polyfit(x_mat, y_mat, 1)
# #         material_to_AB[mat] = (A, B)
# #     else:
# #         material_to_AB[mat] = (np.nan, np.nan)
# #
# #
# # # =========================================================
# # # 9. 5 折交叉验证：按物质划分
# # # =========================================================
# # kf = KFold(
# #     n_splits=n_outer_folds,
# #     shuffle=True,
# #     random_state=random_state,
# # )
# #
# # metrics_anchor = []
# # metrics_clausius = []
# #
# # prediction_records = []
# # ab_records = []
# #
# # for fold, (train_idx, test_idx) in enumerate(kf.split(unique_materials), start=1):
# #     train_mats = unique_materials[train_idx]
# #     test_mats = unique_materials[test_idx]
# #
# #     train_mask = np.isin(material_keys, train_mats)
# #     test_mask = np.isin(material_keys, test_mats)
# #
# #     y_true_test = lnP_true[test_mask]
# #
# #     # -----------------------------------------------------
# #     # 9.1 带锚点线性基线
# #     #
# #     # 模型形式：
# #     # lnP(T) = lnP_anchor + (c0 + c1*G1 + ... + cn*Gn) * (InvT - InvT_anchor)
# #     #
# #     # 为了与 Clausius 基线回归器一致：
# #     # 统一使用 make_common_regressor()
# #     # -----------------------------------------------------
# #     delta_invT_train = InvT[train_mask] - invT_anchor[train_mask]
# #
# #     X_group_train_aug = add_constant_feature(X_groups[train_mask])
# #     X_base_train = X_group_train_aug * delta_invT_train.reshape(-1, 1)
# #
# #     y_base_train = lnP_true[train_mask] - lnP_anchor[train_mask]
# #
# #     valid_base = (
# #         np.isfinite(X_base_train).all(axis=1)
# #         & np.isfinite(y_base_train)
# #     )
# #
# #     if valid_base.sum() == 0:
# #         print(f"Fold {fold}: 锚点基线无有效训练样本，跳过。")
# #         y_pred_anchor = np.full(y_true_test.shape, np.nan)
# #
# #     else:
# #         base_model = make_common_regressor()
# #
# #         base_model.fit(
# #             X_base_train[valid_base],
# #             y_base_train[valid_base],
# #         )
# #
# #         delta_invT_test = InvT[test_mask] - invT_anchor[test_mask]
# #
# #         X_group_test_aug = add_constant_feature(X_groups[test_mask])
# #         X_base_test = X_group_test_aug * delta_invT_test.reshape(-1, 1)
# #
# #         valid_test = np.isfinite(X_base_test).all(axis=1)
# #
# #         baseline_delta = np.full(len(y_true_test), np.nan)
# #         baseline_delta[valid_test] = base_model.predict(X_base_test[valid_test])
# #
# #         y_pred_anchor = lnP_anchor[test_mask] + baseline_delta
# #
# #     # -----------------------------------------------------
# #     # 9.2 Clausius-Clapeyron 参数基线
# #     #
# #     # 单个物质内：
# #     # lnP = A + B * InvT
# #     #
# #     # 物质级参数预测：
# #     # A = a0 + a1*G1 + ... + an*Gn
# #     # B = b0 + b1*G1 + ... + bn*Gn
# #     #
# #     # 为了与锚点基线回归器一致：
# #     # 统一使用 make_common_regressor()
# #     # -----------------------------------------------------
# #     train_AB = []
# #     train_X = []
# #
# #     for mat in train_mats:
# #         if mat not in material_to_AB:
# #             continue
# #
# #         A_true, B_true = material_to_AB[mat]
# #
# #         if not (np.isfinite(A_true) and np.isfinite(B_true)):
# #             continue
# #
# #         # 每个物质只取一行基团特征
# #         idx_first = np.where(material_keys == mat)[0][0]
# #
# #         train_X.append(X_groups[idx_first])
# #         train_AB.append((A_true, B_true))
# #
# #     if len(train_AB) == 0:
# #         print(f"Fold {fold}: Clausius-Clapeyron 基线训练数据不足，跳过。")
# #         y_pred_clausius = np.full(y_true_test.shape, np.nan)
# #
# #     else:
# #         train_X = np.array(train_X, dtype=float)
# #         train_X_aug = add_constant_feature(train_X)
# #
# #         train_A = np.array([ab[0] for ab in train_AB], dtype=float)
# #         train_B = np.array([ab[1] for ab in train_AB], dtype=float)
# #
# #         model_A = make_common_regressor()
# #         model_B = make_common_regressor()
# #
# #         model_A.fit(train_X_aug, train_A)
# #         model_B.fit(train_X_aug, train_B)
# #
# #         # 对测试集物质预测 A 和 B
# #         test_X = []
# #
# #         for mat in test_mats:
# #             idx_first = np.where(material_keys == mat)[0][0]
# #             test_X.append(X_groups[idx_first])
# #
# #         test_X = np.array(test_X, dtype=float)
# #         test_X_aug = add_constant_feature(test_X)
# #
# #         A_pred = model_A.predict(test_X_aug)
# #         B_pred = model_B.predict(test_X_aug)
# #
# #         mat_to_AB_pred = {
# #             mat: (a, b)
# #             for mat, a, b in zip(test_mats, A_pred, B_pred)
# #         }
# #
# #         # 可选：保存每个测试物质的 A/B 诊断结果
# #         if save_ab_diagnostics:
# #             for mat, a_pred, b_pred in zip(test_mats, A_pred, B_pred):
# #                 A_true, B_true = material_to_AB.get(mat, (np.nan, np.nan))
# #
# #                 ab_records.append({
# #                     "fold": fold,
# #                     material_key_col: mat,
# #                     "A_true": A_true,
# #                     "B_true": B_true,
# #                     "A_pred": a_pred,
# #                     "B_pred": b_pred,
# #                     "A_error": a_pred - A_true if np.isfinite(A_true) else np.nan,
# #                     "B_error": b_pred - B_true if np.isfinite(B_true) else np.nan,
# #                 })
# #
# #         # 关键修正：
# #         # 按 test_mask 的原始行顺序生成预测值，
# #         # 保证 y_pred_clausius[i] 对应 y_true_test[i]
# #         test_material_rows = material_keys[test_mask]
# #         test_InvT_rows = InvT[test_mask]
# #
# #         y_pred_clausius = np.full(len(test_material_rows), np.nan)
# #
# #         for i, mat in enumerate(test_material_rows):
# #             if mat in mat_to_AB_pred:
# #                 A_sub, B_sub = mat_to_AB_pred[mat]
# #                 y_pred_clausius[i] = A_sub + B_sub * test_InvT_rows[i]
# #
# #     # -----------------------------------------------------
# #     # 9.3 评价
# #     # -----------------------------------------------------
# #     met_anchor = evaluate_metrics(y_true_test, y_pred_anchor)
# #     met_clausius = evaluate_metrics(y_true_test, y_pred_clausius)
# #
# #     met_anchor["fold"] = fold
# #     met_clausius["fold"] = fold
# #
# #     metrics_anchor.append(met_anchor)
# #     metrics_clausius.append(met_clausius)
# #
# #     print(f"\nFold {fold}:")
# #     print(
# #         f"  锚点基线               - "
# #         f"R2={met_anchor['R2']:.4f}, "
# #         f"RMSE={met_anchor['RMSE']:.4f}, "
# #         f"MAE={met_anchor['MAE']:.4f}, "
# #         f"ARD={met_anchor['ARD']:.2f}%"
# #     )
# #     print(
# #         f"  Clausius-Clapeyron基线 - "
# #         f"R2={met_clausius['R2']:.4f}, "
# #         f"RMSE={met_clausius['RMSE']:.4f}, "
# #         f"MAE={met_clausius['MAE']:.4f}, "
# #         f"ARD={met_clausius['ARD']:.2f}%"
# #     )
# #
# #     # 保存每一行预测，方便检查是否对齐
# #     fold_df = pd.DataFrame({
# #         "fold": fold,
# #         material_key_col: material_keys[test_mask],
# #         "T_K": T_values[test_mask],
# #         "InvT": InvT[test_mask],
# #         "lnP_true": y_true_test,
# #         "lnP_pred_anchor": y_pred_anchor,
# #         "lnP_pred_clausius": y_pred_clausius,
# #         "anchor_error": y_pred_anchor - y_true_test,
# #         "clausius_error": y_pred_clausius - y_true_test,
# #         "lnP_anchor_pred": lnP_anchor[test_mask],
# #         "boiling_T_K_pred": boiling_T_pred[test_mask],
# #         "anchor_T_pred_K": anchor_T_pred[test_mask],
# #         "invT_anchor_pred_1_per_K": invT_anchor[test_mask],
# #     })
# #
# #     prediction_records.append(fold_df)
# #
# #
# # # =========================================================
# # # 10. 汇总统计与配对 t 检验
# # # =========================================================
# # df_anchor_metrics = pd.DataFrame(metrics_anchor)
# # df_clausius_metrics = pd.DataFrame(metrics_clausius)
# #
# # metric_cols = ["fold", "R2", "RMSE", "MAE", "ARD"]
# #
# # df_anchor_metrics = df_anchor_metrics[metric_cols]
# # df_clausius_metrics = df_clausius_metrics[metric_cols]
# #
# #
# # def summarize(df, name):
# #     rows = []
# #
# #     for metric in ["R2", "RMSE", "MAE", "ARD"]:
# #         vals = df[metric].dropna().values
# #
# #         if len(vals) == 0:
# #             mean_val = np.nan
# #             std_val = np.nan
# #             mean_std = "NaN"
# #
# #         elif len(vals) == 1:
# #             mean_val = np.mean(vals)
# #             std_val = np.nan
# #             mean_std = f"{mean_val:.4f} ± NaN"
# #
# #         else:
# #             mean_val = np.mean(vals)
# #             std_val = np.std(vals, ddof=1)
# #             mean_std = f"{mean_val:.4f} ± {std_val:.4f}"
# #
# #         rows.append({
# #             "Model": name,
# #             "Metric": metric,
# #             "Mean": mean_val,
# #             "Std": std_val,
# #             "Mean±Std": mean_std,
# #         })
# #
# #     return pd.DataFrame(rows)
# #
# #
# # summary_anchor = summarize(
# #     df_anchor_metrics,
# #     "Anchor linear baseline",
# # )
# #
# # summary_clausius = summarize(
# #     df_clausius_metrics,
# #     "Clausius-Clapeyron baseline",
# # )
# #
# # summary_all = pd.concat(
# #     [summary_anchor, summary_clausius],
# #     ignore_index=True,
# # )
# #
# # print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
# # print(summary_all[["Model", "Metric", "Mean±Std"]].to_string(index=False))
# #
# #
# # # 配对 t 检验
# # t_test_results = []
# #
# # for metric in ["R2", "RMSE", "MAE", "ARD"]:
# #     vals_anc = df_anchor_metrics[metric].values
# #     vals_cla = df_clausius_metrics[metric].values
# #
# #     valid = np.isfinite(vals_anc) & np.isfinite(vals_cla)
# #
# #     vals_anc = vals_anc[valid]
# #     vals_cla = vals_cla[valid]
# #
# #     if len(vals_anc) > 1:
# #         t_stat, p_val = ttest_rel(vals_anc, vals_cla)
# #
# #         if metric == "R2":
# #             better = "anchor" if np.mean(vals_anc) > np.mean(vals_cla) else "clausius"
# #         else:
# #             better = "anchor" if np.mean(vals_anc) < np.mean(vals_cla) else "clausius"
# #
# #         sig = p_val < 0.05
# #
# #         t_test_results.append({
# #             "Metric": metric,
# #             "Mean_anchor": np.mean(vals_anc),
# #             "Mean_clausius": np.mean(vals_cla),
# #             "t_stat": t_stat,
# #             "p_value": p_val,
# #             "Significant_p_lt_0.05": sig,
# #             "Better_model": better,
# #         })
# #
# #     else:
# #         t_test_results.append({
# #             "Metric": metric,
# #             "Mean_anchor": np.nan,
# #             "Mean_clausius": np.nan,
# #             "t_stat": np.nan,
# #             "p_value": np.nan,
# #             "Significant_p_lt_0.05": False,
# #             "Better_model": "insufficient_valid_folds",
# #         })
# #
# #
# # df_ttest = pd.DataFrame(t_test_results)
# #
# # print("\n========== Paired t-test ==========")
# # print(df_ttest.to_string(index=False))
# #
# #
# # # =========================================================
# # # 11. 保存结果到 Excel
# # # =========================================================
# # df_predictions = pd.concat(prediction_records, ignore_index=True)
# #
# # if len(ab_records) > 0:
# #     df_ab = pd.DataFrame(ab_records)
# # else:
# #     df_ab = pd.DataFrame(
# #         columns=[
# #             "fold",
# #             material_key_col,
# #             "A_true",
# #             "B_true",
# #             "A_pred",
# #             "B_pred",
# #             "A_error",
# #             "B_error",
# #         ]
# #     )
# #
# # output_file = "baseline_comparison_5fold_common_regressor.xlsx"
# #
# # with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
# #     df_anchor_metrics.to_excel(
# #         writer,
# #         sheet_name="Fold_Metrics_Anchor",
# #         index=False,
# #     )
# #
# #     df_clausius_metrics.to_excel(
# #         writer,
# #         sheet_name="Fold_Metrics_Clausius",
# #         index=False,
# #     )
# #
# #     summary_all.to_excel(
# #         writer,
# #         sheet_name="Summary_Mean_Std",
# #         index=False,
# #     )
# #
# #     df_ttest.to_excel(
# #         writer,
# #         sheet_name="Paired_T_Test",
# #         index=False,
# #     )
# #
# #     df_predictions.to_excel(
# #         writer,
# #         sheet_name="Predictions_By_Row",
# #         index=False,
# #     )
# #
# #     df_ab.to_excel(
# #         writer,
# #         sheet_name="Clausius_AB_By_Fold",
# #         index=False,
# #     )
# #
# #     pd.DataFrame([
# #         {"param": "input_file", "value": str(input_file)},
# #         {"param": "data_sheet", "value": data_sheet},
# #         {"param": "groups_sheet", "value": groups_sheet},
# #         {"param": "anchor_sheet", "value": anchor_sheet},
# #         {"param": "target_col", "value": target_col},
# #         {"param": "n_folds", "value": n_outer_folds},
# #         {"param": "random_state", "value": random_state},
# #         {"param": "ridgecv_alpha_min", "value": ridgecv_alphas.min()},
# #         {"param": "ridgecv_alpha_max", "value": ridgecv_alphas.max()},
# #         {"param": "ridgecv_alpha_count", "value": len(ridgecv_alphas)},
# #         {"param": "common_regressor", "value": "StandardScaler(with_mean=False) + RidgeCV(fit_intercept=False)"},
# #         {"param": "constant_feature_added", "value": True},
# #         {"param": "anchor_model_training", "value": "global_all_materials"},
# #         {"param": "n_used_group_cols", "value": len(used_group_cols)},
# #         {"param": "n_temperature_points", "value": len(lnP_true)},
# #         {"param": "n_unique_materials", "value": len(unique_materials)},
# #     ]).to_excel(
# #         writer,
# #         sheet_name="Run_Info",
# #         index=False,
# #     )
# #
# # print(f"\n结果已保存至: {output_file}")
#
# import pandas as pd
# import numpy as np
# from pathlib import Path
#
# from sklearn.linear_model import RidgeCV
# from sklearn.model_selection import KFold
# from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
# from sklearn.pipeline import make_pipeline
# from sklearn.preprocessing import StandardScaler
#
# from scipy.stats import ttest_rel
# import warnings
#
# warnings.filterwarnings("ignore")
#
# pd.set_option("display.float_format", "{:.10f}".format)
# np.set_printoptions(suppress=True, precision=10)
#
#
# # =========================================================
# # 0. 用户配置
# # =========================================================
# input_file = Path("dataset_selected_by_two_k_with_lnP_invT_interpolation_8points.xlsx")
#
# data_sheet = "Data_selected"
# groups_sheet = "Groups_selected"
# anchor_sheet = "Interpolated_k1_k2"
#
# material_key_col = "material_key"
# temp_col = "T_K"
#
# target_candidates = [
#     "lnP_kPa",
#     "lnP",
#     "ln_VaporPressure_kPa",
#     "ln_pressure",
# ]
#
# pressure_candidates = [
#     "VaporPressure_kPa",
#     "vapor_pressure_kPa",
#     "Vapor_Pressure_kPa",
#     "P_vapor_kPa",
#     "property_value",
# ]
#
# anchor_lnp_col = "lnP_kPa_interp_at_k1Tb"
# anchor_T_col = "k1_times_boiling_T_K"
# boiling_col = "boiling_T_K"
# k1_col = "k1"
#
# n_group_features_to_use = 220
# use_fixed_group_position = True
# group_start_col_1based = 3
# group_end_col_1based = 222
#
# random_state = 42
# n_outer_folds = 5
#
# # 锚点子模型参数：保持原设定
# hgb_params = dict(
#     loss="squared_error",
#     max_iter=1200,
#     learning_rate=0.03,
#     max_leaf_nodes=63,
#     min_samples_leaf=2,
#     l2_regularization=0.0,
#     early_stopping=False,
#     random_state=random_state,
# )
#
# # 统一回归器参数
# ridgecv_alphas = np.logspace(-4, 5, 60)
#
# # 是否保存更详细的逐物质 A/B 诊断结果
# save_ab_diagnostics = True
#
#
# # =========================================================
# # 1. 工具函数
# # =========================================================
# def is_valid_value(x):
#     if pd.isna(x):
#         return False
#
#     s = str(x).strip()
#
#     if s == "" or s.lower() in ["nan", "none", "null", "待定"]:
#         return False
#
#     return True
#
#
# def build_material_key(row):
#     for col in ["material_key", "inchikey", "cas", "compound_name", "formula"]:
#         if col in row.index and is_valid_value(row[col]):
#             if col == "material_key":
#                 return str(row[col]).strip()
#             return f"{col}:{str(row[col]).strip()}"
#
#     return "unknown_material"
#
#
# def find_first_existing_col(df, candidates, col_type, required=True):
#     for col in candidates:
#         if col in df.columns:
#             return col
#
#     lower_map = {str(c).lower(): c for c in df.columns}
#
#     for col in candidates:
#         if str(col).lower() in lower_map:
#             return lower_map[str(col).lower()]
#
#     if required:
#         raise ValueError(f"没有找到 {col_type} 列。候选: {candidates}")
#
#     return None
#
#
# def identify_group_columns(df_groups, n=220):
#     if use_fixed_group_position:
#         start_idx = group_start_col_1based - 1
#         end_excl = group_end_col_1based
#
#         if len(df_groups.columns) < end_excl:
#             raise ValueError(
#                 f"基团列数不足，需要到第 {group_end_col_1based} 列，"
#                 f"但当前只有 {len(df_groups.columns)} 列。"
#             )
#
#         group_cols = list(df_groups.columns[start_idx:end_excl])
#
#         if len(group_cols) != n:
#             raise ValueError(f"固定位置识别 {len(group_cols)} 个基团，需要 {n} 个。")
#
#         return group_cols
#
#     raise ValueError("请设置 use_fixed_group_position=True")
#
#
# def safe_exp(x):
#     return np.exp(np.clip(x, -700, 700))
#
#
# def evaluate_metrics(y_true, y_pred):
#     """
#     计算 R2, RMSE, MSE, MAE, ARD(%)
#
#     注意：
#     当前 y_true/y_pred 是 lnP，因此 ARD 是基于 lnP 的相对误差。
#     如果需要蒸汽压 P 空间的 ARD，需要对 lnP 取 exp 后再算。
#     """
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#
#     mask = np.isfinite(y_true) & np.isfinite(y_pred)
#
#     y_true = y_true[mask]
#     y_pred = y_pred[mask]
#
#     if len(y_true) == 0:
#         return {
#             "R2": np.nan,
#             "RMSE": np.nan,
#             "MSE": np.nan,
#             "MAE": np.nan,
#             "ARD": np.nan,
#         }
#
#     r2 = r2_score(y_true, y_pred)
#     rmse = np.sqrt(mean_squared_error(y_true, y_pred))
#     mse = rmse ** 2
#     mae = mean_absolute_error(y_true, y_pred)
#
#     denom_mask = np.abs(y_true) > 1e-12
#
#     if denom_mask.sum() == 0:
#         ard = np.nan
#     else:
#         ard = (
#             np.mean(
#                 np.abs(
#                     (y_pred[denom_mask] - y_true[denom_mask])
#                     / y_true[denom_mask]
#                 )
#             )
#             * 100
#         )
#
#     return {
#         "R2": r2,
#         "RMSE": rmse,
#         "MSE": mse,
#         "MAE": mae,
#         "ARD": ard,
#     }
#
#
# def train_anchor_submodel(X, y):
#     """
#     锚点子模型。
#     这里保留你的原始设定：HistGradientBoostingRegressor。
#     """
#     from sklearn.ensemble import HistGradientBoostingRegressor
#
#     model = HistGradientBoostingRegressor(**hgb_params)
#     model.fit(X, y)
#
#     return model
#
#
# def add_constant_feature(X):
#     """
#     给特征矩阵前面添加一列常数 1。
#
#     目的：
#     1. 统一使用 fit_intercept=False。
#     2. Clausius A/B 模型仍然可以学习常数项。
#     3. 锚点基线中，常数列乘以 delta_InvT 后，相当于学习一个全局 slope 项。
#     """
#     X = np.asarray(X, dtype=float)
#
#     if X.ndim != 2:
#         raise ValueError("X 必须是二维数组。")
#
#     ones = np.ones((X.shape[0], 1), dtype=float)
#
#     return np.hstack([ones, X])
#
#
# def make_common_regressor():
#     """
#     两个基线统一使用的回归器。
#
#     StandardScaler(with_mean=False):
#         不做中心化，保证零输入仍然映射为零输入。
#         对锚点基线很重要，因为 delta_InvT = 0 时，
#         修正项必须为 0。
#
#     RidgeCV(fit_intercept=False):
#         不使用内置截距。
#         截距由 add_constant_feature() 添加的常数列承担。
#     """
#     return make_pipeline(
#         StandardScaler(with_mean=False),
#         RidgeCV(
#             alphas=ridgecv_alphas,
#             fit_intercept=False,
#         ),
#     )
#
#
# # =========================================================
# # 2. 读取数据
# # =========================================================
# df_data = pd.read_excel(input_file, sheet_name=data_sheet)
# df_groups_raw = pd.read_excel(input_file, sheet_name=groups_sheet)
# df_anchor = pd.read_excel(input_file, sheet_name=anchor_sheet)
#
# # 物质 ID 对齐
# for df in [df_data, df_groups_raw, df_anchor]:
#     if material_key_col not in df.columns:
#         df[material_key_col] = df.apply(build_material_key, axis=1)
#
#     df[material_key_col] = df[material_key_col].astype(str).str.strip()
#
# # 找目标列
# target_col = find_first_existing_col(
#     df_data,
#     target_candidates,
#     "lnP",
#     required=True,
# )
#
# pressure_col = find_first_existing_col(
#     df_data,
#     pressure_candidates,
#     "压力",
#     required=False,
# )
#
# print(f"使用目标列: {target_col}")
#
# if pressure_col is not None:
#     print(f"检测到压力列: {pressure_col}")
#
#
# # =========================================================
# # 3. 基团列处理
# # =========================================================
# group_cols_220 = identify_group_columns(
#     df_groups_raw,
#     n=n_group_features_to_use,
# )
#
# df_groups_numeric = (
#     df_groups_raw[group_cols_220]
#     .apply(pd.to_numeric, errors="coerce")
#     .fillna(0.0)
# )
#
# # 删除全零基团列
# nonzero_mask = df_groups_numeric.abs().sum(axis=0) != 0
# used_group_cols = df_groups_numeric.columns[nonzero_mask].tolist()
# df_groups_used = df_groups_numeric[used_group_cols].copy()
#
# print("有效基团数:", len(used_group_cols))
#
#
# # =========================================================
# # 4. 锚点数据准备
# # =========================================================
# if k1_col in df_anchor.columns:
#     df_anchor["k1_for_anchor"] = pd.to_numeric(
#         df_anchor[k1_col],
#         errors="coerce",
#     )
#
# elif anchor_T_col in df_anchor.columns:
#     df_anchor["k1_for_anchor"] = (
#         pd.to_numeric(df_anchor[anchor_T_col], errors="coerce")
#         / pd.to_numeric(df_anchor[boiling_col], errors="coerce")
#     )
#
# else:
#     raise ValueError("无法获得 k1。请检查 k1 或 k1_times_boiling_T_K / boiling_T_K 列。")
#
# k1_median = df_anchor["k1_for_anchor"].median()
# df_anchor["k1_for_anchor"] = df_anchor["k1_for_anchor"].fillna(k1_median)
#
# required_anchor_cols = [
#     material_key_col,
#     anchor_lnp_col,
#     boiling_col,
#     "k1_for_anchor",
# ]
#
# for col in required_anchor_cols:
#     if col not in df_anchor.columns:
#         raise ValueError(f"锚点表中缺少必要列: {col}")
#
#
# # =========================================================
# # 5. 构造物质级数据
# # =========================================================
# df_material = df_groups_used.reset_index().rename(columns={"index": "orig_idx"})
# df_material[material_key_col] = df_groups_raw.loc[
#     df_material.index,
#     material_key_col,
# ].values
#
# df_material = df_material.merge(
#     df_anchor[
#         [
#             material_key_col,
#             anchor_lnp_col,
#             boiling_col,
#             "k1_for_anchor",
#         ]
#     ],
#     on=material_key_col,
#     how="left",
# )
#
# df_material = df_material.dropna(
#     subset=used_group_cols + [anchor_lnp_col, boiling_col, "k1_for_anchor"]
# )
#
# df_material = df_material.reset_index(drop=True)
#
# print("可用于物质级建模的物质数:", len(df_material))
#
#
# # =========================================================
# # 6. 训练全局锚点模型
# # =========================================================
# # 注意：
# # 根据你的实验设定，这里允许使用全数据训练锚点模型。
# # 即测试集物质也可以拥有特定锚点信息或由全局锚点模块给出锚点约束。
# X_anchor_mat = df_material[used_group_cols].values.astype(float)
# y_anchor_lnp = df_material[anchor_lnp_col].values.astype(float)
# y_boiling = df_material[boiling_col].values.astype(float)
#
# valid_anchor = (
#     np.isfinite(X_anchor_mat).all(axis=1)
#     & np.isfinite(y_anchor_lnp)
#     & np.isfinite(y_boiling)
#     & (y_boiling > 0)
# )
#
# X_anchor_mat_valid = X_anchor_mat[valid_anchor]
# y_anchor_lnp_valid = y_anchor_lnp[valid_anchor]
# y_boiling_valid = y_boiling[valid_anchor]
#
# anchor_lnP_model = train_anchor_submodel(
#     X_anchor_mat_valid,
#     y_anchor_lnp_valid,
# )
#
# anchor_boiling_model = train_anchor_submodel(
#     X_anchor_mat_valid,
#     y_boiling_valid,
# )
#
# # 预测所有物质的锚点
# X_all_groups = df_material[used_group_cols].values.astype(float)
#
# df_material["lnP_anchor_pred"] = anchor_lnP_model.predict(X_all_groups)
# df_material["boiling_T_K_pred"] = anchor_boiling_model.predict(X_all_groups)
# df_material["anchor_T_pred_K"] = (
#     df_material["k1_for_anchor"] * df_material["boiling_T_K_pred"]
# )
# df_material["invT_anchor_pred_1_per_K"] = 1.0 / df_material["anchor_T_pred_K"]
#
#
# # =========================================================
# # 7. 展开温度点数据
# # =========================================================
# df_data[temp_col] = pd.to_numeric(
#     df_data[temp_col],
#     errors="coerce",
# )
#
# df_data[target_col] = pd.to_numeric(
#     df_data[target_col],
#     errors="coerce",
# )
#
# df_data["InvT"] = 1.0 / df_data[temp_col]
#
# df_long = df_data.merge(
#     df_material[
#         [material_key_col]
#         + used_group_cols
#         + [
#             "lnP_anchor_pred",
#             "boiling_T_K_pred",
#             "anchor_T_pred_K",
#             "invT_anchor_pred_1_per_K",
#             "k1_for_anchor",
#         ]
#     ],
#     on=material_key_col,
#     how="inner",
# )
#
# df_long = df_long.dropna(
#     subset=[
#         target_col,
#         temp_col,
#         "InvT",
#         "lnP_anchor_pred",
#         "invT_anchor_pred_1_per_K",
#     ]
#     + used_group_cols
# )
#
# df_long = df_long.reset_index(drop=True)
#
# # 提取数组
# X_groups = df_long[used_group_cols].values.astype(float)
# InvT = df_long["InvT"].values.astype(float)
# T_values = df_long[temp_col].values.astype(float)
#
# lnP_true = df_long[target_col].values.astype(float)
# lnP_anchor = df_long["lnP_anchor_pred"].values.astype(float)
# boiling_T_pred = df_long["boiling_T_K_pred"].values.astype(float)
# anchor_T_pred = df_long["anchor_T_pred_K"].values.astype(float)
# invT_anchor = df_long["invT_anchor_pred_1_per_K"].values.astype(float)
#
# material_keys = df_long[material_key_col].values.astype(str)
# unique_materials = np.unique(material_keys)
#
# print(f"总温度点数: {len(lnP_true)}")
# print(f"物质数: {len(unique_materials)}")
#
#
# # =========================================================
# # 8. 为每个物质拟合真实 Clausius-Clapeyron 参数
# #    lnP = A + B * InvT
# # =========================================================
# material_to_AB = {}
#
# for mat in unique_materials:
#     mask = material_keys == mat
#
#     x_mat = InvT[mask]        # x = 1 / T
#     y_mat = lnP_true[mask]    # y = lnP
#
#     valid = np.isfinite(x_mat) & np.isfinite(y_mat)
#
#     x_mat = x_mat[valid]
#     y_mat = y_mat[valid]
#
#     if len(x_mat) >= 2 and np.std(x_mat) > 0:
#         # 关键修正：
#         # np.polyfit(x, y, 1) 返回 [slope, intercept]
#         # 对 lnP = A + B * InvT：
#         # B = slope
#         # A = intercept
#         B, A = np.polyfit(x_mat, y_mat, 1)
#         material_to_AB[mat] = (A, B)
#     else:
#         material_to_AB[mat] = (np.nan, np.nan)
#
#
# # =========================================================
# # 9. 5 折交叉验证：按物质划分
# # =========================================================
# kf = KFold(
#     n_splits=n_outer_folds,
#     shuffle=True,
#     random_state=random_state,
# )
#
# metrics_anchor = []
# metrics_clausius = []
#
# prediction_records = []
# ab_records = []
#
# for fold, (train_idx, test_idx) in enumerate(kf.split(unique_materials), start=1):
#     train_mats = unique_materials[train_idx]
#     test_mats = unique_materials[test_idx]
#
#     train_mask = np.isin(material_keys, train_mats)
#     test_mask = np.isin(material_keys, test_mats)
#
#     y_true_test = lnP_true[test_mask]
#
#     # -----------------------------------------------------
#     # 9.1 带锚点线性基线
#     #
#     # 模型形式：
#     # lnP(T) = lnP_anchor + (c0 + c1*G1 + ... + cn*Gn) * (InvT - InvT_anchor)
#     #
#     # 为了与 Clausius 基线回归器一致：
#     # 统一使用 make_common_regressor()
#     # -----------------------------------------------------
#     delta_invT_train = InvT[train_mask] - invT_anchor[train_mask]
#
#     X_group_train_aug = add_constant_feature(X_groups[train_mask])
#     X_base_train = X_group_train_aug * delta_invT_train.reshape(-1, 1)
#
#     y_base_train = lnP_true[train_mask] - lnP_anchor[train_mask]
#
#     valid_base = (
#         np.isfinite(X_base_train).all(axis=1)
#         & np.isfinite(y_base_train)
#     )
#
#     if valid_base.sum() == 0:
#         print(f"Fold {fold}: 锚点基线无有效训练样本，跳过。")
#         y_pred_anchor = np.full(y_true_test.shape, np.nan)
#
#     else:
#         base_model = make_common_regressor()
#
#         base_model.fit(
#             X_base_train[valid_base],
#             y_base_train[valid_base],
#         )
#
#         delta_invT_test = InvT[test_mask] - invT_anchor[test_mask]
#
#         X_group_test_aug = add_constant_feature(X_groups[test_mask])
#         X_base_test = X_group_test_aug * delta_invT_test.reshape(-1, 1)
#
#         valid_test = np.isfinite(X_base_test).all(axis=1)
#
#         baseline_delta = np.full(len(y_true_test), np.nan)
#         baseline_delta[valid_test] = base_model.predict(X_base_test[valid_test])
#
#         y_pred_anchor = lnP_anchor[test_mask] + baseline_delta
#
#     # -----------------------------------------------------
#     # 9.2 Clausius-Clapeyron 参数基线
#     #
#     # 单个物质内：
#     # lnP = A + B * InvT
#     #
#     # 物质级参数预测：
#     # A = a0 + a1*G1 + ... + an*Gn
#     # B = b0 + b1*G1 + ... + bn*Gn
#     #
#     # 为了与锚点基线回归器一致：
#     # 统一使用 make_common_regressor()
#     # -----------------------------------------------------
#     train_AB = []
#     train_X = []
#
#     for mat in train_mats:
#         if mat not in material_to_AB:
#             continue
#
#         A_true, B_true = material_to_AB[mat]
#
#         if not (np.isfinite(A_true) and np.isfinite(B_true)):
#             continue
#
#         # 每个物质只取一行基团特征
#         idx_first = np.where(material_keys == mat)[0][0]
#
#         train_X.append(X_groups[idx_first])
#         train_AB.append((A_true, B_true))
#
#     if len(train_AB) == 0:
#         print(f"Fold {fold}: Clausius-Clapeyron 基线训练数据不足，跳过。")
#         y_pred_clausius = np.full(y_true_test.shape, np.nan)
#
#     else:
#         train_X = np.array(train_X, dtype=float)
#         train_X_aug = add_constant_feature(train_X)
#
#         train_A = np.array([ab[0] for ab in train_AB], dtype=float)
#         train_B = np.array([ab[1] for ab in train_AB], dtype=float)
#
#         model_A = make_common_regressor()
#         model_B = make_common_regressor()
#
#         model_A.fit(train_X_aug, train_A)
#         model_B.fit(train_X_aug, train_B)
#
#         # 对测试集物质预测 A 和 B
#         test_X = []
#
#         for mat in test_mats:
#             idx_first = np.where(material_keys == mat)[0][0]
#             test_X.append(X_groups[idx_first])
#
#         test_X = np.array(test_X, dtype=float)
#         test_X_aug = add_constant_feature(test_X)
#
#         A_pred = model_A.predict(test_X_aug)
#         B_pred = model_B.predict(test_X_aug)
#
#         mat_to_AB_pred = {
#             mat: (a, b)
#             for mat, a, b in zip(test_mats, A_pred, B_pred)
#         }
#
#         # 可选：保存每个测试物质的 A/B 诊断结果
#         if save_ab_diagnostics:
#             for mat, a_pred, b_pred in zip(test_mats, A_pred, B_pred):
#                 A_true, B_true = material_to_AB.get(mat, (np.nan, np.nan))
#
#                 ab_records.append({
#                     "fold": fold,
#                     material_key_col: mat,
#                     "A_true": A_true,
#                     "B_true": B_true,
#                     "A_pred": a_pred,
#                     "B_pred": b_pred,
#                     "A_error": a_pred - A_true if np.isfinite(A_true) else np.nan,
#                     "B_error": b_pred - B_true if np.isfinite(B_true) else np.nan,
#                 })
#
#         # 关键修正：
#         # 按 test_mask 的原始行顺序生成预测值，
#         # 保证 y_pred_clausius[i] 对应 y_true_test[i]
#         test_material_rows = material_keys[test_mask]
#         test_InvT_rows = InvT[test_mask]
#
#         y_pred_clausius = np.full(len(test_material_rows), np.nan)
#
#         for i, mat in enumerate(test_material_rows):
#             if mat in mat_to_AB_pred:
#                 A_sub, B_sub = mat_to_AB_pred[mat]
#                 y_pred_clausius[i] = A_sub + B_sub * test_InvT_rows[i]
#
#     # -----------------------------------------------------
#     # 9.3 评价
#     # -----------------------------------------------------
#     met_anchor = evaluate_metrics(y_true_test, y_pred_anchor)
#     met_clausius = evaluate_metrics(y_true_test, y_pred_clausius)
#
#     met_anchor["fold"] = fold
#     met_clausius["fold"] = fold
#
#     metrics_anchor.append(met_anchor)
#     metrics_clausius.append(met_clausius)
#
#     print(f"\nFold {fold}:")
#     print(
#         f"  锚点基线               - "
#         f"R2={met_anchor['R2']:.4f}, "
#         f"RMSE={met_anchor['RMSE']:.4f}, "
#         f"MSE={met_anchor['MSE']:.4f}, "
#         f"MAE={met_anchor['MAE']:.4f}, "
#         f"ARD={met_anchor['ARD']:.2f}%"
#     )
#     print(
#         f"  Clausius-Clapeyron基线 - "
#         f"R2={met_clausius['R2']:.4f}, "
#         f"RMSE={met_clausius['RMSE']:.4f}, "
#         f"MSE={met_clausius['MSE']:.4f}, "
#         f"MAE={met_clausius['MAE']:.4f}, "
#         f"ARD={met_clausius['ARD']:.2f}%"
#     )
#
#     # 保存每一行预测，方便检查是否对齐
#     fold_df = pd.DataFrame({
#         "fold": fold,
#         material_key_col: material_keys[test_mask],
#         "T_K": T_values[test_mask],
#         "InvT": InvT[test_mask],
#         "lnP_true": y_true_test,
#         "lnP_pred_anchor": y_pred_anchor,
#         "lnP_pred_clausius": y_pred_clausius,
#         "anchor_error": y_pred_anchor - y_true_test,
#         "clausius_error": y_pred_clausius - y_true_test,
#         "lnP_anchor_pred": lnP_anchor[test_mask],
#         "boiling_T_K_pred": boiling_T_pred[test_mask],
#         "anchor_T_pred_K": anchor_T_pred[test_mask],
#         "invT_anchor_pred_1_per_K": invT_anchor[test_mask],
#     })
#
#     prediction_records.append(fold_df)
#
#
# # =========================================================
# # 10. 汇总统计与配对 t 检验
# # =========================================================
# df_anchor_metrics = pd.DataFrame(metrics_anchor)
# df_clausius_metrics = pd.DataFrame(metrics_clausius)
#
# metric_cols = ["fold", "R2", "RMSE", "MSE", "MAE", "ARD"]
#
# df_anchor_metrics = df_anchor_metrics[metric_cols]
# df_clausius_metrics = df_clausius_metrics[metric_cols]
#
#
# def summarize(df, name):
#     rows = []
#
#     for metric in ["R2", "RMSE", "MSE", "MAE", "ARD"]:
#         vals = df[metric].dropna().values
#
#         if len(vals) == 0:
#             mean_val = np.nan
#             std_val = np.nan
#             mean_std = "NaN"
#
#         elif len(vals) == 1:
#             mean_val = np.mean(vals)
#             std_val = np.nan
#             mean_std = f"{mean_val:.4f} ± NaN"
#
#         else:
#             mean_val = np.mean(vals)
#             std_val = np.std(vals, ddof=1)
#             mean_std = f"{mean_val:.4f} ± {std_val:.4f}"
#
#         rows.append({
#             "Model": name,
#             "Metric": metric,
#             "Mean": mean_val,
#             "Std": std_val,
#             "Mean±Std": mean_std,
#         })
#
#     return pd.DataFrame(rows)
#
#
# summary_anchor = summarize(
#     df_anchor_metrics,
#     "Anchor linear baseline",
# )
#
# summary_clausius = summarize(
#     df_clausius_metrics,
#     "Clausius-Clapeyron baseline",
# )
#
# summary_all = pd.concat(
#     [summary_anchor, summary_clausius],
#     ignore_index=True,
# )
#
# print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
# print(summary_all[["Model", "Metric", "Mean±Std"]].to_string(index=False))
#
#
# # 配对 t 检验
# t_test_results = []
#
# for metric in ["R2", "RMSE", "MSE", "MAE", "ARD"]:
#     vals_anc = df_anchor_metrics[metric].values
#     vals_cla = df_clausius_metrics[metric].values
#
#     valid = np.isfinite(vals_anc) & np.isfinite(vals_cla)
#
#     vals_anc = vals_anc[valid]
#     vals_cla = vals_cla[valid]
#
#     if len(vals_anc) > 1:
#         t_stat, p_val = ttest_rel(vals_anc, vals_cla)
#
#         if metric == "R2":
#             better = "anchor" if np.mean(vals_anc) > np.mean(vals_cla) else "clausius"
#         else:
#             better = "anchor" if np.mean(vals_anc) < np.mean(vals_cla) else "clausius"
#
#         sig = p_val < 0.05
#
#         t_test_results.append({
#             "Metric": metric,
#             "Mean_anchor": np.mean(vals_anc),
#             "Mean_clausius": np.mean(vals_cla),
#             "t_stat": t_stat,
#             "p_value": p_val,
#             "Significant_p_lt_0.05": sig,
#             "Better_model": better,
#         })
#
#     else:
#         t_test_results.append({
#             "Metric": metric,
#             "Mean_anchor": np.nan,
#             "Mean_clausius": np.nan,
#             "t_stat": np.nan,
#             "p_value": np.nan,
#             "Significant_p_lt_0.05": False,
#             "Better_model": "insufficient_valid_folds",
#         })
#
#
# df_ttest = pd.DataFrame(t_test_results)
#
# print("\n========== Paired t-test ==========")
# print(df_ttest.to_string(index=False))
#
#
# # =========================================================
# # 11. 保存结果到 Excel
# # =========================================================
# df_predictions = pd.concat(prediction_records, ignore_index=True)
#
# if len(ab_records) > 0:
#     df_ab = pd.DataFrame(ab_records)
# else:
#     df_ab = pd.DataFrame(
#         columns=[
#             "fold",
#             material_key_col,
#             "A_true",
#             "B_true",
#             "A_pred",
#             "B_pred",
#             "A_error",
#             "B_error",
#         ]
#     )
#
# output_file = "baseline_comparison_5fold_common_regressor.xlsx"
#
# with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
#     df_anchor_metrics.to_excel(
#         writer,
#         sheet_name="Fold_Metrics_Anchor",
#         index=False,
#     )
#
#     df_clausius_metrics.to_excel(
#         writer,
#         sheet_name="Fold_Metrics_Clausius",
#         index=False,
#     )
#
#     summary_all.to_excel(
#         writer,
#         sheet_name="Summary_Mean_Std",
#         index=False,
#     )
#
#     df_ttest.to_excel(
#         writer,
#         sheet_name="Paired_T_Test",
#         index=False,
#     )
#
#     df_predictions.to_excel(
#         writer,
#         sheet_name="Predictions_By_Row",
#         index=False,
#     )
#
#     df_ab.to_excel(
#         writer,
#         sheet_name="Clausius_AB_By_Fold",
#         index=False,
#     )
#
#     pd.DataFrame([
#         {"param": "input_file", "value": str(input_file)},
#         {"param": "data_sheet", "value": data_sheet},
#         {"param": "groups_sheet", "value": groups_sheet},
#         {"param": "anchor_sheet", "value": anchor_sheet},
#         {"param": "target_col", "value": target_col},
#         {"param": "n_folds", "value": n_outer_folds},
#         {"param": "random_state", "value": random_state},
#         {"param": "ridgecv_alpha_min", "value": ridgecv_alphas.min()},
#         {"param": "ridgecv_alpha_max", "value": ridgecv_alphas.max()},
#         {"param": "ridgecv_alpha_count", "value": len(ridgecv_alphas)},
#         {"param": "common_regressor", "value": "StandardScaler(with_mean=False) + RidgeCV(fit_intercept=False)"},
#         {"param": "constant_feature_added", "value": True},
#         {"param": "anchor_model_training", "value": "global_all_materials"},
#         {"param": "n_used_group_cols", "value": len(used_group_cols)},
#         {"param": "n_temperature_points", "value": len(lnP_true)},
#         {"param": "n_unique_materials", "value": len(unique_materials)},
#     ]).to_excel(
#         writer,
#         sheet_name="Run_Info",
#         index=False,
#     )
#
# print(f"\n结果已保存至: {output_file}")


import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.linear_model import RidgeCV
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from scipy.stats import ttest_rel
import warnings

warnings.filterwarnings("ignore")

pd.set_option("display.float_format", "{:.10f}".format)
np.set_printoptions(suppress=True, precision=10)


# =========================================================
# 0. 用户配置
# =========================================================
input_file = Path("dataset_selected_by_two_k_with_lnP_invT_interpolation_8points.xlsx")

data_sheet = "Data_selected"
groups_sheet = "Groups_selected"
anchor_sheet = "Interpolated_k1_k2"

material_key_col = "material_key"
temp_col = "T_K"

target_candidates = [
    "lnP_kPa",
    "lnP",
    "ln_VaporPressure_kPa",
    "ln_pressure",
]

pressure_candidates = [
    "VaporPressure_kPa",
    "vapor_pressure_kPa",
    "Vapor_Pressure_kPa",
    "P_vapor_kPa",
    "property_value",
]

anchor_lnp_col = "lnP_kPa_interp_at_k1Tb"
anchor_T_col = "k1_times_boiling_T_K"
boiling_col = "boiling_T_K"
k1_col = "k1"

n_group_features_to_use = 220
use_fixed_group_position = True
group_start_col_1based = 3
group_end_col_1based = 222

random_state = 42
n_outer_folds = 5

# 锚点子模型参数：保持原设定
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

# 统一回归器参数
ridgecv_alphas = np.logspace(-4, 5, 60)

# 是否保存更详细的逐物质 A/B 诊断结果
save_ab_diagnostics = True

output_file = "baseline_comparison_5fold_common_regressor.xlsx"


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
    for col in ["material_key", "inchikey", "cas", "compound_name", "formula"]:
        if col in row.index and is_valid_value(row[col]):
            if col == "material_key":
                return str(row[col]).strip()
            return f"{col}:{str(row[col]).strip()}"

    return "unknown_material"


def find_first_existing_col(df, candidates, col_type, required=True):
    for col in candidates:
        if col in df.columns:
            return col

    lower_map = {str(c).lower(): c for c in df.columns}

    for col in candidates:
        if str(col).lower() in lower_map:
            return lower_map[str(col).lower()]

    if required:
        raise ValueError(f"没有找到 {col_type} 列。候选: {candidates}")

    return None


def identify_group_columns(df_groups, n=220):
    if use_fixed_group_position:
        start_idx = group_start_col_1based - 1
        end_excl = group_end_col_1based

        if len(df_groups.columns) < end_excl:
            raise ValueError(
                f"基团列数不足，需要到第 {group_end_col_1based} 列，"
                f"但当前只有 {len(df_groups.columns)} 列。"
            )

        group_cols = list(df_groups.columns[start_idx:end_excl])

        if len(group_cols) != n:
            raise ValueError(f"固定位置识别 {len(group_cols)} 个基团，需要 {n} 个。")

        return group_cols

    raise ValueError("请设置 use_fixed_group_position=True")


def safe_exp(x):
    return np.exp(np.clip(x, -700, 700))


def safe_relative_error_percent(y_true, y_pred):
    """
    relative_error = abs((y_pred - y_true) / y_true) * 100

    对 abs(y_true) <= 1e-12 的点，relative_error 记为 NaN。
    当前代码中 y_true / y_pred 默认是 lnP。
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    rel_err = np.full_like(y_true, np.nan, dtype=float)
    valid = (
        np.isfinite(y_true)
        & np.isfinite(y_pred)
        & (np.abs(y_true) > 1e-12)
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


def evaluate_metrics(y_true, y_pred):
    """
    计算 R2, RMSE, MSE, MAE, ARD(%)

    注意：
    当前 y_true/y_pred 是 lnP，因此 ARD 是基于 lnP 的相对误差。
    如果需要蒸汽压 P 空间的 ARD，需要对 lnP 取 exp 后再算。
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = np.isfinite(y_true) & np.isfinite(y_pred)

    y_true = y_true[mask]
    y_pred = y_pred[mask]

    if len(y_true) == 0:
        return {
            "R2": np.nan,
            "RMSE": np.nan,
            "MSE": np.nan,
            "MAE": np.nan,
            "ARD": np.nan,
            "max_rel_err": np.nan,
            "<1% ratio(%)": np.nan,
            "<5% ratio(%)": np.nan,
            "<10% ratio(%)": np.nan,
            "<1% count": 0.0,
            "<5% count": 0.0,
            "<10% count": 0.0,
        }

    r2 = r2_score(y_true, y_pred) if len(y_true) > 1 else np.nan
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_true, y_pred)

    rel_err = safe_relative_error_percent(y_true, y_pred)

    if np.any(np.isfinite(rel_err)):
        ard = np.nanmean(rel_err)
        max_rel = np.nanmax(rel_err)

        count_1 = float(np.nansum(rel_err < 1.0))
        count_5 = float(np.nansum(rel_err < 5.0))
        count_10 = float(np.nansum(rel_err < 10.0))

        n_valid_rel = int(np.sum(np.isfinite(rel_err)))

        pct1 = count_1 / n_valid_rel * 100.0
        pct5 = count_5 / n_valid_rel * 100.0
        pct10 = count_10 / n_valid_rel * 100.0
    else:
        ard = np.nan
        max_rel = np.nan
        pct1 = np.nan
        pct5 = np.nan
        pct10 = np.nan
        count_1 = 0.0
        count_5 = 0.0
        count_10 = 0.0

    return {
        "R2": r2,
        "RMSE": rmse,
        "MSE": mse,
        "MAE": mae,
        "ARD": ard,
        "max_rel_err": max_rel,
        "<1% ratio(%)": pct1,
        "<5% ratio(%)": pct5,
        "<10% ratio(%)": pct10,
        "<1% count": count_1,
        "<5% count": count_5,
        "<10% count": count_10,
    }


def train_anchor_submodel(X, y):
    """
    锚点子模型。
    这里保留你的原始设定：HistGradientBoostingRegressor。
    """
    from sklearn.ensemble import HistGradientBoostingRegressor

    model = HistGradientBoostingRegressor(**hgb_params)
    model.fit(X, y)

    return model


def add_constant_feature(X):
    """
    给特征矩阵前面添加一列常数 1。

    目的：
    1. 统一使用 fit_intercept=False。
    2. Clausius A/B 模型仍然可以学习常数项。
    3. 锚点基线中，常数列乘以 delta_InvT 后，相当于学习一个全局 slope 项。
    """
    X = np.asarray(X, dtype=float)

    if X.ndim != 2:
        raise ValueError("X 必须是二维数组。")

    ones = np.ones((X.shape[0], 1), dtype=float)

    return np.hstack([ones, X])


def make_common_regressor():
    """
    两个基线统一使用的回归器。

    StandardScaler(with_mean=False):
        不做中心化，保证零输入仍然映射为零输入。
        对锚点基线很重要，因为 delta_InvT = 0 时，
        修正项必须为 0。

    RidgeCV(fit_intercept=False):
        不使用内置截距。
        截距由 add_constant_feature() 添加的常数列承担。
    """
    return make_pipeline(
        StandardScaler(with_mean=False),
        RidgeCV(
            alphas=ridgecv_alphas,
            fit_intercept=False,
        ),
    )


def get_ridgecv_alpha(model_pipeline):
    """
    从 make_pipeline(StandardScaler, RidgeCV) 中提取 alpha。
    """
    try:
        return model_pipeline.named_steps["ridgecv"].alpha_
    except Exception:
        return np.nan


def build_anchor_X_for_indices(indices):
    """
    锚点线性基线特征：
        X = [1, Nk] * (InvT - InvT_anchor)
    """
    indices = np.asarray(indices, dtype=int)

    delta_invT = InvT[indices] - invT_anchor[indices]
    X_group_aug = add_constant_feature(X_groups[indices])
    X_base = X_group_aug * delta_invT.reshape(-1, 1)

    return X_base


def predict_anchor_baseline(indices, base_model):
    """
    使用训练好的锚点线性基线模型预测指定样本。
    """
    indices = np.asarray(indices, dtype=int)
    X_base = build_anchor_X_for_indices(indices)

    pred_delta = np.full(len(indices), np.nan, dtype=float)

    valid = np.isfinite(X_base).all(axis=1)

    if valid.sum() > 0:
        pred_delta[valid] = base_model.predict(X_base[valid])

    y_pred = lnP_anchor[indices] + pred_delta

    return y_pred, pred_delta


def fit_clausius_models(train_mats):
    """
    训练 Clausius-Clapeyron A/B 参数预测模型：
        lnP = A + B * InvT

    A = f_A([1, Nk])
    B = f_B([1, Nk])
    """
    train_AB = []
    train_X = []
    train_materials_used = []

    for mat in train_mats:
        if mat not in material_to_AB:
            continue

        A_true, B_true = material_to_AB[mat]

        if not (np.isfinite(A_true) and np.isfinite(B_true)):
            continue

        idx_first = np.where(material_keys == mat)[0][0]

        train_X.append(X_groups[idx_first])
        train_AB.append((A_true, B_true))
        train_materials_used.append(mat)

    if len(train_AB) == 0:
        return None, None, [], np.nan, np.nan

    train_X = np.array(train_X, dtype=float)
    train_X_aug = add_constant_feature(train_X)

    train_A = np.array([ab[0] for ab in train_AB], dtype=float)
    train_B = np.array([ab[1] for ab in train_AB], dtype=float)

    model_A = make_common_regressor()
    model_B = make_common_regressor()

    model_A.fit(train_X_aug, train_A)
    model_B.fit(train_X_aug, train_B)

    alpha_A = get_ridgecv_alpha(model_A)
    alpha_B = get_ridgecv_alpha(model_B)

    return model_A, model_B, train_materials_used, alpha_A, alpha_B


def predict_clausius_for_materials(indices, model_A, model_B):
    """
    对任意样本 indices 进行 Clausius 参数预测。

    对每个样本所在物质：
        A_pred = model_A([1, Nk])
        B_pred = model_B([1, Nk])
        lnP_pred = A_pred + B_pred * InvT
    """
    indices = np.asarray(indices, dtype=int)

    y_pred = np.full(len(indices), np.nan, dtype=float)
    A_pred_rows = np.full(len(indices), np.nan, dtype=float)
    B_pred_rows = np.full(len(indices), np.nan, dtype=float)

    if model_A is None or model_B is None or len(indices) == 0:
        return y_pred, A_pred_rows, B_pred_rows

    mats = material_keys[indices]
    unique_mats = np.unique(mats)

    mat_to_AB_pred = {}

    test_X = []
    mat_order = []

    for mat in unique_mats:
        idx_first = np.where(material_keys == mat)[0][0]
        test_X.append(X_groups[idx_first])
        mat_order.append(mat)

    test_X = np.array(test_X, dtype=float)
    test_X_aug = add_constant_feature(test_X)

    A_pred = model_A.predict(test_X_aug)
    B_pred = model_B.predict(test_X_aug)

    for mat, a, b in zip(mat_order, A_pred, B_pred):
        mat_to_AB_pred[mat] = (a, b)

    for i, sample_idx in enumerate(indices):
        mat = material_keys[sample_idx]

        if mat in mat_to_AB_pred:
            A_sub, B_sub = mat_to_AB_pred[mat]
            A_pred_rows[i] = A_sub
            B_pred_rows[i] = B_sub
            y_pred[i] = A_sub + B_sub * InvT[sample_idx]

    return y_pred, A_pred_rows, B_pred_rows


def make_prediction_df(
    fold,
    dataset_name,
    indices,
    y_pred_anchor,
    y_pred_clausius,
    anchor_delta=None,
    A_pred_rows=None,
    B_pred_rows=None,
):
    indices = np.asarray(indices, dtype=int)

    y_true = lnP_true[indices]

    rel_anchor = safe_relative_error_percent(y_true, y_pred_anchor)
    rel_clausius = safe_relative_error_percent(y_true, y_pred_clausius)

    df = pd.DataFrame({
        "fold": fold,
        "dataset": dataset_name,
        material_key_col: material_keys[indices],
        "T_K": T_values[indices],
        "InvT": InvT[indices],
        "lnP_true": y_true,
        "lnP_pred_anchor": y_pred_anchor,
        "lnP_pred_clausius": y_pred_clausius,
        "anchor_error": y_pred_anchor - y_true,
        "clausius_error": y_pred_clausius - y_true,
        "anchor_abs_error": np.abs(y_pred_anchor - y_true),
        "clausius_abs_error": np.abs(y_pred_clausius - y_true),
        "anchor_relative_error_percent": rel_anchor,
        "clausius_relative_error_percent": rel_clausius,
        "lnP_anchor_pred": lnP_anchor[indices],
        "boiling_T_K_pred": boiling_T_pred[indices],
        "anchor_T_pred_K": anchor_T_pred[indices],
        "invT_anchor_pred_1_per_K": invT_anchor[indices],
        "k1_for_anchor": df_long["k1_for_anchor"].values[indices],
    })

    if pressure_col is not None and pressure_col in df_long.columns:
        df["pressure_true_raw"] = df_long[pressure_col].values[indices]

    if anchor_delta is not None:
        df["anchor_delta_pred"] = anchor_delta

    if A_pred_rows is not None:
        df["A_pred"] = A_pred_rows

    if B_pred_rows is not None:
        df["B_pred"] = B_pred_rows

    return df


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

# 物质 ID 对齐
for df in [df_data, df_groups_raw, df_anchor]:
    if material_key_col not in df.columns:
        df[material_key_col] = df.apply(build_material_key, axis=1)

    df[material_key_col] = df[material_key_col].astype(str).str.strip()

# 找目标列
target_col = find_first_existing_col(
    df_data,
    target_candidates,
    "lnP",
    required=True,
)

pressure_col = find_first_existing_col(
    df_data,
    pressure_candidates,
    "压力",
    required=False,
)

print(f"使用目标列: {target_col}")

if pressure_col is not None:
    print(f"检测到压力列: {pressure_col}")


# =========================================================
# 3. 基团列处理
# =========================================================
group_cols_220 = identify_group_columns(
    df_groups_raw,
    n=n_group_features_to_use,
)

df_groups_numeric = (
    df_groups_raw[group_cols_220]
    .apply(pd.to_numeric, errors="coerce")
    .fillna(0.0)
)

# 删除全零基团列
nonzero_mask = df_groups_numeric.abs().sum(axis=0) != 0

used_group_cols = df_groups_numeric.columns[nonzero_mask].tolist()
removed_zero_group_cols = df_groups_numeric.columns[~nonzero_mask].tolist()

df_groups_used = df_groups_numeric[used_group_cols].copy()

print("有效基团数:", len(used_group_cols))
print("删除全零基团数:", len(removed_zero_group_cols))


# =========================================================
# 4. 锚点数据准备
# =========================================================
if k1_col in df_anchor.columns:
    df_anchor["k1_for_anchor"] = pd.to_numeric(
        df_anchor[k1_col],
        errors="coerce",
    )

elif anchor_T_col in df_anchor.columns:
    df_anchor["k1_for_anchor"] = (
        pd.to_numeric(df_anchor[anchor_T_col], errors="coerce")
        / pd.to_numeric(df_anchor[boiling_col], errors="coerce")
    )

else:
    raise ValueError("无法获得 k1。请检查 k1 或 k1_times_boiling_T_K / boiling_T_K 列。")

k1_median = df_anchor["k1_for_anchor"].median()
df_anchor["k1_for_anchor"] = df_anchor["k1_for_anchor"].fillna(k1_median)

required_anchor_cols = [
    material_key_col,
    anchor_lnp_col,
    boiling_col,
    "k1_for_anchor",
]

for col in required_anchor_cols:
    if col not in df_anchor.columns:
        raise ValueError(f"锚点表中缺少必要列: {col}")


# =========================================================
# 5. 构造物质级数据
# =========================================================
df_material = df_groups_used.reset_index().rename(columns={"index": "orig_idx"})
df_material[material_key_col] = df_groups_raw.loc[
    df_material.index,
    material_key_col,
].values

df_material = df_material.merge(
    df_anchor[
        [
            material_key_col,
            anchor_lnp_col,
            boiling_col,
            "k1_for_anchor",
        ]
    ],
    on=material_key_col,
    how="left",
)

df_material = df_material.dropna(
    subset=used_group_cols + [anchor_lnp_col, boiling_col, "k1_for_anchor"]
)

df_material = df_material.reset_index(drop=True)

print("可用于物质级建模的物质数:", len(df_material))


# =========================================================
# 6. 训练全局锚点模型
# =========================================================
# 注意：
# 根据你的实验设定，这里允许使用全数据训练锚点模型。
# 即测试集物质也可以拥有特定锚点信息或由全局锚点模块给出锚点约束。
X_anchor_mat = df_material[used_group_cols].values.astype(float)
y_anchor_lnp = df_material[anchor_lnp_col].values.astype(float)
y_boiling = df_material[boiling_col].values.astype(float)

valid_anchor = (
    np.isfinite(X_anchor_mat).all(axis=1)
    & np.isfinite(y_anchor_lnp)
    & np.isfinite(y_boiling)
    & (y_boiling > 0)
)

X_anchor_mat_valid = X_anchor_mat[valid_anchor]
y_anchor_lnp_valid = y_anchor_lnp[valid_anchor]
y_boiling_valid = y_boiling[valid_anchor]

anchor_lnP_model = train_anchor_submodel(
    X_anchor_mat_valid,
    y_anchor_lnp_valid,
)

anchor_boiling_model = train_anchor_submodel(
    X_anchor_mat_valid,
    y_boiling_valid,
)

# 预测所有物质的锚点
X_all_groups = df_material[used_group_cols].values.astype(float)

df_material["lnP_anchor_pred"] = anchor_lnP_model.predict(X_all_groups)
df_material["boiling_T_K_pred"] = anchor_boiling_model.predict(X_all_groups)
df_material["anchor_T_pred_K"] = (
    df_material["k1_for_anchor"] * df_material["boiling_T_K_pred"]
)
df_material["invT_anchor_pred_1_per_K"] = 1.0 / df_material["anchor_T_pred_K"]

# 锚点子模型预测与评价
anchor_lnp_pred_train = anchor_lnP_model.predict(X_anchor_mat_valid)
boiling_pred_train = anchor_boiling_model.predict(X_anchor_mat_valid)

df_submodel_summary = pd.DataFrame([
    {
        "submodel": "anchor_lnP_model",
        "target": anchor_lnp_col,
        **evaluate_metrics(y_anchor_lnp_valid, anchor_lnp_pred_train),
        "model_type": "HistGradientBoostingRegressor",
        "params": str(hgb_params),
    },
    {
        "submodel": "anchor_boiling_model",
        "target": boiling_col,
        **evaluate_metrics(y_boiling_valid, boiling_pred_train),
        "model_type": "HistGradientBoostingRegressor",
        "params": str(hgb_params),
    },
])

df_submodel_predictions = pd.DataFrame({
    material_key_col: df_material[material_key_col].values,
    "anchor_lnp_true": y_anchor_lnp,
    "anchor_lnp_pred": df_material["lnP_anchor_pred"].values,
    "anchor_lnp_abs_error": np.abs(df_material["lnP_anchor_pred"].values - y_anchor_lnp),
    "anchor_lnp_relative_error_percent": safe_relative_error_percent(
        y_anchor_lnp,
        df_material["lnP_anchor_pred"].values,
    ),
    "boiling_T_true": y_boiling,
    "boiling_T_pred": df_material["boiling_T_K_pred"].values,
    "boiling_T_abs_error": np.abs(df_material["boiling_T_K_pred"].values - y_boiling),
    "boiling_T_relative_error_percent": safe_relative_error_percent(
        y_boiling,
        df_material["boiling_T_K_pred"].values,
    ),
    "k1_for_anchor": df_material["k1_for_anchor"].values,
    "anchor_T_pred_K": df_material["anchor_T_pred_K"].values,
    "invT_anchor_pred_1_per_K": df_material["invT_anchor_pred_1_per_K"].values,
})


# =========================================================
# 7. 展开温度点数据
# =========================================================
df_data[temp_col] = pd.to_numeric(
    df_data[temp_col],
    errors="coerce",
)

df_data[target_col] = pd.to_numeric(
    df_data[target_col],
    errors="coerce",
)

df_data["InvT"] = 1.0 / df_data[temp_col]

df_long = df_data.merge(
    df_material[
        [material_key_col]
        + used_group_cols
        + [
            "lnP_anchor_pred",
            "boiling_T_K_pred",
            "anchor_T_pred_K",
            "invT_anchor_pred_1_per_K",
            "k1_for_anchor",
        ]
    ],
    on=material_key_col,
    how="inner",
)

df_long = df_long.dropna(
    subset=[
        target_col,
        temp_col,
        "InvT",
        "lnP_anchor_pred",
        "invT_anchor_pred_1_per_K",
    ]
    + used_group_cols
)

df_long = df_long.reset_index(drop=True)

# 提取数组
X_groups = df_long[used_group_cols].values.astype(float)
InvT = df_long["InvT"].values.astype(float)
T_values = df_long[temp_col].values.astype(float)

lnP_true = df_long[target_col].values.astype(float)
lnP_anchor = df_long["lnP_anchor_pred"].values.astype(float)
boiling_T_pred = df_long["boiling_T_K_pred"].values.astype(float)
anchor_T_pred = df_long["anchor_T_pred_K"].values.astype(float)
invT_anchor = df_long["invT_anchor_pred_1_per_K"].values.astype(float)

material_keys = df_long[material_key_col].values.astype(str)
unique_materials = np.unique(material_keys)
all_sample_indices = np.arange(len(lnP_true))

print(f"总温度点数: {len(lnP_true)}")
print(f"物质数: {len(unique_materials)}")


# =========================================================
# 8. 为每个物质拟合真实 Clausius-Clapeyron 参数
#    lnP = A + B * InvT
# =========================================================
material_to_AB = {}

for mat in unique_materials:
    mask = material_keys == mat

    x_mat = InvT[mask]        # x = 1 / T
    y_mat = lnP_true[mask]    # y = lnP

    valid = np.isfinite(x_mat) & np.isfinite(y_mat)

    x_mat = x_mat[valid]
    y_mat = y_mat[valid]

    if len(x_mat) >= 2 and np.std(x_mat) > 0:
        # np.polyfit(x, y, 1) 返回 [slope, intercept]
        # 对 lnP = A + B * InvT：
        # B = slope
        # A = intercept
        B, A = np.polyfit(x_mat, y_mat, 1)
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
# 9. 5 折交叉验证：按物质划分
# =========================================================
kf = KFold(
    n_splits=n_outer_folds,
    shuffle=True,
    random_state=random_state,
)

metrics_anchor = []
metrics_clausius = []

prediction_records = []
all_data_prediction_records = []
ab_records = []
fold_all_data_count_records = []
fold_info_records = []

anchor_param_records = []
clausius_param_records = []

for fold, (train_idx, test_idx) in enumerate(kf.split(unique_materials), start=1):
    train_mats = unique_materials[train_idx]
    test_mats = unique_materials[test_idx]

    train_mask = np.isin(material_keys, train_mats)
    test_mask = np.isin(material_keys, test_mats)

    train_indices = np.where(train_mask)[0]
    test_indices = np.where(test_mask)[0]

    y_true_test = lnP_true[test_indices]

    # -----------------------------------------------------
    # 9.1 带锚点线性基线
    #
    # 模型形式：
    # lnP(T) = lnP_anchor + (c0 + c1*G1 + ... + cn*Gn) * (InvT - InvT_anchor)
    # -----------------------------------------------------
    X_base_train = build_anchor_X_for_indices(train_indices)
    y_base_train = lnP_true[train_indices] - lnP_anchor[train_indices]

    valid_base = (
        np.isfinite(X_base_train).all(axis=1)
        & np.isfinite(y_base_train)
    )

    if valid_base.sum() == 0:
        print(f"Fold {fold}: 锚点基线无有效训练样本，跳过。")
        base_model = None
        y_pred_anchor_test = np.full(y_true_test.shape, np.nan)
        anchor_delta_test = np.full(y_true_test.shape, np.nan)
        y_pred_anchor_all = np.full(lnP_true.shape, np.nan)
        anchor_delta_all = np.full(lnP_true.shape, np.nan)

    else:
        base_model = make_common_regressor()

        base_model.fit(
            X_base_train[valid_base],
            y_base_train[valid_base],
        )

        y_pred_anchor_test, anchor_delta_test = predict_anchor_baseline(
            test_indices,
            base_model,
        )

        y_pred_anchor_all, anchor_delta_all = predict_anchor_baseline(
            all_sample_indices,
            base_model,
        )

    # -----------------------------------------------------
    # 9.2 Clausius-Clapeyron 参数基线
    #
    # 单个物质内：
    # lnP = A + B * InvT
    #
    # 物质级参数预测：
    # A = a0 + a1*G1 + ... + an*Gn
    # B = b0 + b1*G1 + ... + bn*Gn
    # -----------------------------------------------------
    model_A, model_B, train_materials_used_for_ab, alpha_A, alpha_B = fit_clausius_models(train_mats)

    if model_A is None or model_B is None:
        print(f"Fold {fold}: Clausius-Clapeyron 基线训练数据不足，跳过。")
        y_pred_clausius_test = np.full(y_true_test.shape, np.nan)
        A_pred_test = np.full(y_true_test.shape, np.nan)
        B_pred_test = np.full(y_true_test.shape, np.nan)

        y_pred_clausius_all = np.full(lnP_true.shape, np.nan)
        A_pred_all = np.full(lnP_true.shape, np.nan)
        B_pred_all = np.full(lnP_true.shape, np.nan)

    else:
        y_pred_clausius_test, A_pred_test, B_pred_test = predict_clausius_for_materials(
            test_indices,
            model_A,
            model_B,
        )

        y_pred_clausius_all, A_pred_all, B_pred_all = predict_clausius_for_materials(
            all_sample_indices,
            model_A,
            model_B,
        )

        # 保存每个测试物质的 A/B 诊断结果
        if save_ab_diagnostics:
            test_X = []
            mat_order = []

            for mat in test_mats:
                idx_first = np.where(material_keys == mat)[0][0]
                test_X.append(X_groups[idx_first])
                mat_order.append(mat)

            test_X = np.array(test_X, dtype=float)
            test_X_aug = add_constant_feature(test_X)

            A_pred_mat = model_A.predict(test_X_aug)
            B_pred_mat = model_B.predict(test_X_aug)

            for mat, a_pred, b_pred in zip(mat_order, A_pred_mat, B_pred_mat):
                A_true, B_true = material_to_AB.get(mat, (np.nan, np.nan))

                ab_records.append({
                    "fold": fold,
                    material_key_col: mat,
                    "A_true": A_true,
                    "B_true": B_true,
                    "A_pred": a_pred,
                    "B_pred": b_pred,
                    "A_error": a_pred - A_true if np.isfinite(A_true) else np.nan,
                    "B_error": b_pred - B_true if np.isfinite(B_true) else np.nan,
                    "A_abs_error": abs(a_pred - A_true) if np.isfinite(A_true) else np.nan,
                    "B_abs_error": abs(b_pred - B_true) if np.isfinite(B_true) else np.nan,
                })

    # -----------------------------------------------------
    # 9.3 评价：测试集
    # -----------------------------------------------------
    met_anchor = evaluate_metrics(y_true_test, y_pred_anchor_test)
    met_clausius = evaluate_metrics(y_true_test, y_pred_clausius_test)

    met_anchor["fold"] = fold
    met_clausius["fold"] = fold

    metrics_anchor.append(met_anchor)
    metrics_clausius.append(met_clausius)

    print(f"\nFold {fold}:")
    print(
        f"  锚点基线               - "
        f"R2={met_anchor['R2']:.4f}, "
        f"RMSE={met_anchor['RMSE']:.4f}, "
        f"MSE={met_anchor['MSE']:.4f}, "
        f"MAE={met_anchor['MAE']:.4f}, "
        f"ARD={met_anchor['ARD']:.2f}%"
    )
    print(
        f"  Clausius-Clapeyron基线 - "
        f"R2={met_clausius['R2']:.4f}, "
        f"RMSE={met_clausius['RMSE']:.4f}, "
        f"MSE={met_clausius['MSE']:.4f}, "
        f"MAE={met_clausius['MAE']:.4f}, "
        f"ARD={met_clausius['ARD']:.2f}%"
    )

    # -----------------------------------------------------
    # 9.4 新增：每个 fold 模型预测完整数据集，并统计完整数据集偏差数量
    # -----------------------------------------------------
    count_anchor_all = count_error_thresholds(lnP_true, y_pred_anchor_all)
    count_clausius_all = count_error_thresholds(lnP_true, y_pred_clausius_all)

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "Anchor linear baseline",
        **count_anchor_all,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "Clausius-Clapeyron baseline",
        **count_clausius_all,
    })

    print("\nAnchor fold model predicts ALL data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "Anchor linear baseline",
        **count_anchor_all,
    }]).to_string(index=False))

    print("\nClausius fold model predicts ALL data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "Clausius-Clapeyron baseline",
        **count_clausius_all,
    }]).to_string(index=False))

    # -----------------------------------------------------
    # 9.5 保存测试集预测
    # -----------------------------------------------------
    fold_df = make_prediction_df(
        fold=fold,
        dataset_name="test",
        indices=test_indices,
        y_pred_anchor=y_pred_anchor_test,
        y_pred_clausius=y_pred_clausius_test,
        anchor_delta=anchor_delta_test,
        A_pred_rows=A_pred_test,
        B_pred_rows=B_pred_test,
    )

    prediction_records.append(fold_df)

    # -----------------------------------------------------
    # 9.6 保存完整数据集预测
    # -----------------------------------------------------
    all_df = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        indices=all_sample_indices,
        y_pred_anchor=y_pred_anchor_all,
        y_pred_clausius=y_pred_clausius_all,
        anchor_delta=anchor_delta_all,
        A_pred_rows=A_pred_all,
        B_pred_rows=B_pred_all,
    )

    all_data_prediction_records.append(all_df)

    # -----------------------------------------------------
    # 9.7 保存参数信息
    # -----------------------------------------------------
    if base_model is not None:
        alpha_anchor = get_ridgecv_alpha(base_model)

        try:
            ridge_anchor = base_model.named_steps["ridgecv"]
            coef_anchor = ridge_anchor.coef_
            feature_names_anchor = ["constant"] + used_group_cols

            for fname, coef in zip(feature_names_anchor, coef_anchor):
                anchor_param_records.append({
                    "fold": fold,
                    "feature": fname,
                    "coef_scaled_space": coef,
                    "selected_alpha": alpha_anchor,
                })
        except Exception:
            alpha_anchor = np.nan
    else:
        alpha_anchor = np.nan

    if model_A is not None and model_B is not None:
        try:
            ridge_A = model_A.named_steps["ridgecv"]
            ridge_B = model_B.named_steps["ridgecv"]

            feature_names_ab = ["constant"] + used_group_cols

            for fname, coef_A, coef_B in zip(feature_names_ab, ridge_A.coef_, ridge_B.coef_):
                clausius_param_records.append({
                    "fold": fold,
                    "feature": fname,
                    "coef_A_scaled_space": coef_A,
                    "coef_B_scaled_space": coef_B,
                    "selected_alpha_A": alpha_A,
                    "selected_alpha_B": alpha_B,
                })
        except Exception:
            pass

    fold_info_records.append({
        "fold": fold,
        "n_train_materials": len(train_mats),
        "n_test_materials": len(test_mats),
        "n_train_points": int(train_mask.sum()),
        "n_test_points": int(test_mask.sum()),
        "n_all_points": len(lnP_true),
        "n_used_group_cols": len(used_group_cols),
        "anchor_alpha": alpha_anchor,
        "clausius_alpha_A": alpha_A,
        "clausius_alpha_B": alpha_B,
        "anchor_model_trained": base_model is not None,
        "clausius_model_trained": model_A is not None and model_B is not None,
        "n_train_materials_used_for_AB": len(train_materials_used_for_ab),
    })


# =========================================================
# 10. 汇总统计与配对 t 检验
# =========================================================
df_anchor_metrics = pd.DataFrame(metrics_anchor)
df_clausius_metrics = pd.DataFrame(metrics_clausius)

metric_cols = [
    "fold",
    "R2",
    "RMSE",
    "MSE",
    "MAE",
    "ARD",
    "max_rel_err",
    "<1% ratio(%)",
    "<5% ratio(%)",
    "<10% ratio(%)",
    "<1% count",
    "<5% count",
    "<10% count",
]

df_anchor_metrics = df_anchor_metrics[metric_cols]
df_clausius_metrics = df_clausius_metrics[metric_cols]


def summarize(df, name):
    rows = []

    for metric in [
        "R2",
        "RMSE",
        "MSE",
        "MAE",
        "ARD",
        "max_rel_err",
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
            mean_val = np.mean(vals)
            std_val = np.nan
            mean_std = f"{mean_val:.4f} ± NaN"

        else:
            mean_val = np.mean(vals)
            std_val = np.std(vals, ddof=1)
            mean_std = f"{mean_val:.4f} ± {std_val:.4f}"

        rows.append({
            "Model": name,
            "Metric": metric,
            "Mean": mean_val,
            "Std": std_val,
            "Mean±Std": mean_std,
        })

    return pd.DataFrame(rows)


summary_anchor = summarize(
    df_anchor_metrics,
    "Anchor linear baseline",
)

summary_clausius = summarize(
    df_clausius_metrics,
    "Clausius-Clapeyron baseline",
)

summary_all = pd.concat(
    [summary_anchor, summary_clausius],
    ignore_index=True,
)

print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
print(summary_all[["Model", "Metric", "Mean±Std"]].to_string(index=False))


# 配对 t 检验
t_test_results = []

for metric in ["R2", "RMSE", "MSE", "MAE", "ARD"]:
    vals_anc = df_anchor_metrics[metric].values
    vals_cla = df_clausius_metrics[metric].values

    valid = np.isfinite(vals_anc) & np.isfinite(vals_cla)

    vals_anc = vals_anc[valid]
    vals_cla = vals_cla[valid]

    if len(vals_anc) > 1:
        t_stat, p_val = ttest_rel(vals_anc, vals_cla)

        if metric == "R2":
            better = "anchor" if np.mean(vals_anc) > np.mean(vals_cla) else "clausius"
        else:
            better = "anchor" if np.mean(vals_anc) < np.mean(vals_cla) else "clausius"

        sig = p_val < 0.05

        t_test_results.append({
            "Metric": metric,
            "Mean_anchor": np.mean(vals_anc),
            "Mean_clausius": np.mean(vals_cla),
            "t_stat": t_stat,
            "p_value": p_val,
            "Significant_p_lt_0.05": sig,
            "Better_model": better,
        })

    else:
        t_test_results.append({
            "Metric": metric,
            "Mean_anchor": np.nan,
            "Mean_clausius": np.nan,
            "t_stat": np.nan,
            "p_value": np.nan,
            "Significant_p_lt_0.05": False,
            "Better_model": "insufficient_valid_folds",
        })


df_ttest = pd.DataFrame(t_test_results)

print("\n========== Paired t-test ==========")
print(df_ttest.to_string(index=False))


# =========================================================
# 11. 新增：完整数据集预测偏差数量统计汇总
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
        "n_all_data_points": len(lnP_true),
    })

df_final_average_summary = pd.DataFrame(final_average_records)

print("\n========== Fold all-data count summary ==========")
print(df_fold_all_data_count_summary.to_string(index=False))

print("\n========== Final average all-data count summary ==========")
print(df_final_average_summary.to_string(index=False))


# =========================================================
# 12. 整理保存表
# =========================================================
df_predictions = pd.concat(prediction_records, ignore_index=True)
df_all_data_predictions = pd.concat(all_data_prediction_records, ignore_index=True)

if len(ab_records) > 0:
    df_ab = pd.DataFrame(ab_records)
else:
    df_ab = pd.DataFrame(
        columns=[
            "fold",
            material_key_col,
            "A_true",
            "B_true",
            "A_pred",
            "B_pred",
            "A_error",
            "B_error",
            "A_abs_error",
            "B_abs_error",
        ]
    )

df_fold_info = pd.DataFrame(fold_info_records)
df_anchor_params = pd.DataFrame(anchor_param_records)
df_clausius_params = pd.DataFrame(clausius_param_records)

df_used_groups = pd.DataFrame({
    "used_group": used_group_cols,
    "occurrence_all_materials": (df_groups_used != 0).sum(axis=0).values,
    "total_count_all": df_groups_used.sum(axis=0).values,
})

df_removed_zero_groups = pd.DataFrame({
    "removed_zero_group": removed_zero_group_cols,
})


df_run_info = pd.DataFrame([
    {"param": "input_file", "value": str(input_file)},
    {"param": "data_sheet", "value": data_sheet},
    {"param": "groups_sheet", "value": groups_sheet},
    {"param": "anchor_sheet", "value": anchor_sheet},
    {"param": "target_col", "value": target_col},
    {"param": "pressure_col", "value": pressure_col if pressure_col is not None else "not_found"},
    {"param": "n_folds", "value": n_outer_folds},
    {"param": "random_state", "value": random_state},
    {"param": "ridgecv_alpha_min", "value": ridgecv_alphas.min()},
    {"param": "ridgecv_alpha_max", "value": ridgecv_alphas.max()},
    {"param": "ridgecv_alpha_count", "value": len(ridgecv_alphas)},
    {"param": "common_regressor", "value": "StandardScaler(with_mean=False) + RidgeCV(fit_intercept=False)"},
    {"param": "constant_feature_added", "value": True},
    {"param": "anchor_model_training", "value": "global_all_materials"},
    {"param": "anchor_submodel_type", "value": "HistGradientBoostingRegressor"},
    {"param": "anchor_submodel_params", "value": str(hgb_params)},
    {"param": "n_used_group_cols", "value": len(used_group_cols)},
    {"param": "n_temperature_points", "value": len(lnP_true)},
    {"param": "n_unique_materials", "value": len(unique_materials)},
    {
        "param": "relative_error_definition",
        "value": "abs((y_pred - y_true) / y_true) * 100; abs(y_true)<=1e-12 -> NaN; y is lnP",
    },
    {
        "param": "full_data_count_rule",
        "value": "Each fold model predicts the whole dataset; count rel_err <1%, <5%, <10%; then average counts over 5 folds.",
    },
])


df_model_structure = pd.DataFrame([
    {
        "项目": "预测对象",
        "内容": f"蒸汽压对数 lnP，目标列 {target_col}",
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
        "内容": f"{n_outer_folds}-fold KFold，按物质 material_key 划分，shuffle=True，random_state={random_state}",
    },
    {
        "项目": "方法1",
        "内容": "Anchor linear baseline：lnP = lnP_anchor + f([1,Nk]) * (InvT - InvT_anchor)",
    },
    {
        "项目": "方法1输入特征",
        "内容": "[1, Nk] * (InvT - InvT_anchor)",
    },
    {
        "项目": "方法2",
        "内容": "Clausius-Clapeyron baseline：lnP = A + B * InvT，先按物质拟合真实 A/B，再用基团预测 A/B",
    },
    {
        "项目": "方法2输入特征",
        "内容": "[1, Nk] 预测 A；[1, Nk] 预测 B",
    },
    {
        "项目": "是否包含子模型",
        "内容": "包含锚点子模型",
    },
    {
        "项目": "子模型预测对象",
        "内容": f"lnP_anchor: {anchor_lnp_col}；boiling_T: {boiling_col}",
    },
    {
        "项目": "子模型类型",
        "内容": "HistGradientBoostingRegressor",
    },
    {
        "项目": "子模型参数",
        "内容": str(hgb_params),
    },
    {
        "项目": "子模型输入特征",
        "内容": f"Nk，有效基团数 {len(used_group_cols)}",
    },
    {
        "项目": "anchor_T 构造",
        "内容": "anchor_T_pred_K = k1_for_anchor * boiling_T_K_pred；invT_anchor = 1 / anchor_T_pred_K",
    },
    {
        "项目": "baseline 构造",
        "内容": "方法1为锚点线性基线；方法2为 Clausius-Clapeyron 参数基线",
    },
    {
        "项目": "residual 构造",
        "内容": "无 residual 修正模型",
    },
    {
        "项目": "最终模型类型",
        "内容": "StandardScaler(with_mean=False) + RidgeCV(fit_intercept=False)",
    },
    {
        "项目": "最终模型参数",
        "内容": f"ridgecv_alphas=np.logspace(-4, 5, 60)，alpha_count={len(ridgecv_alphas)}",
    },
    {
        "项目": "偏差数量统计口径",
        "内容": "每个 fold 训练出的模型预测完整数据集，统计 lnP 相对误差 <1%、<5%、<10% 的点数，再对 5 个 fold 取平均",
    },
])


# =========================================================
# 13. 保存结果到 Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_anchor_metrics.to_excel(
        writer,
        sheet_name="Fold_Metrics_Anchor",
        index=False,
    )

    df_clausius_metrics.to_excel(
        writer,
        sheet_name="Fold_Metrics_Clausius",
        index=False,
    )

    summary_all.to_excel(
        writer,
        sheet_name="Summary_Mean_Std",
        index=False,
    )

    df_ttest.to_excel(
        writer,
        sheet_name="Paired_T_Test",
        index=False,
    )

    df_predictions.to_excel(
        writer,
        sheet_name="fold_test_predictions",
        index=False,
    )

    df_all_data_predictions.to_excel(
        writer,
        sheet_name="fold_all_data_predictions",
        index=False,
    )

    df_fold_all_data_count_summary.to_excel(
        writer,
        sheet_name="fold_all_data_count_summary",
        index=False,
    )

    df_final_average_summary.to_excel(
        writer,
        sheet_name="final_average_summary",
        index=False,
    )

    df_ab.to_excel(
        writer,
        sheet_name="Clausius_AB_By_Fold",
        index=False,
    )

    df_true_ab_all.to_excel(
        writer,
        sheet_name="Clausius_AB_True_All",
        index=False,
    )

    df_submodel_summary.to_excel(
        writer,
        sheet_name="submodel_summary",
        index=False,
    )

    df_submodel_predictions.to_excel(
        writer,
        sheet_name="submodel_predictions",
        index=False,
    )

    df_anchor_params.to_excel(
        writer,
        sheet_name="anchor_params",
        index=False,
    )

    df_clausius_params.to_excel(
        writer,
        sheet_name="clausius_params",
        index=False,
    )

    df_fold_info.to_excel(
        writer,
        sheet_name="Fold_Info",
        index=False,
    )

    df_used_groups.to_excel(
        writer,
        sheet_name="Used_Groups",
        index=False,
    )

    df_removed_zero_groups.to_excel(
        writer,
        sheet_name="Removed_Zero_Groups",
        index=False,
    )

    df_run_info.to_excel(
        writer,
        sheet_name="Run_Info",
        index=False,
    )

    df_model_structure.to_excel(
        writer,
        sheet_name="model_structure",
        index=False,
    )

    format_excel(writer)

print(f"\n结果已保存至: {output_file}")


# =========================================================
# 14. 最终方便复制输出
# =========================================================
def get_final_counts(method_name):
    row = df_final_average_summary[df_final_average_summary["Method"] == method_name]

    if row.empty:
        return np.nan, np.nan, np.nan

    row = row.iloc[0]

    return (
        row["mean_count_rel_err_lt_1pct"],
        row["mean_count_rel_err_lt_5pct"],
        row["mean_count_rel_err_lt_10pct"],
    )


anchor_1, anchor_5, anchor_10 = get_final_counts("Anchor linear baseline")
clausius_1, clausius_5, clausius_10 = get_final_counts("Clausius-Clapeyron baseline")

print("\n方法1 全数据预测偏差 1%，5%，10%分别为：")
print(anchor_1)
print(anchor_5)
print(anchor_10)

print("\n方法2 全数据预测偏差 1%，5%，10%分别为：")
print(clausius_1)
print(clausius_5)
print(clausius_10)


# =========================================================
# 15. 代码结构打印
# =========================================================
print("\n========== 当前代码结构简要汇总 ==========")
print(f"预测对象：蒸汽压对数 lnP / {target_col}")
print(f"数据文件：{input_file}")
print(f"sheet 名称：{data_sheet}, {groups_sheet}, {anchor_sheet}")
print(f"交叉验证：{n_outer_folds}-fold，按 material_key 物质划分")
print("方法1：Anchor linear baseline，lnP = lnP_anchor + f([1,Nk]) * (InvT - InvT_anchor)")
print("方法2：Clausius-Clapeyron baseline，lnP = A + B * InvT，先拟合每个物质真实 A/B，再用基团预测 A/B")
print("子模型：HistGradientBoostingRegressor，全局训练，分别预测 lnP_anchor 与 boiling_T")
print(f"子模型参数：{hgb_params}")
print("anchor_T 构造：anchor_T_pred_K = k1_for_anchor * boiling_T_K_pred；invT_anchor = 1 / anchor_T_pred_K")
print("baseline 构造：方法1为锚点线性基线；方法2为 Clausius-Clapeyron 参数基线")
print("residual 模型：无")
print("最终模型：StandardScaler(with_mean=False) + RidgeCV(fit_intercept=False)")
print(f"最终模型参数：ridgecv_alphas=np.logspace(-4, 5, 60)，alpha_count={len(ridgecv_alphas)}")
print("方法1最终输入：[1, Nk] * (InvT - InvT_anchor)")
print("方法2最终输入：[1, Nk] 预测 A；[1, Nk] 预测 B")
print("偏差统计口径：每个 fold 模型预测完整数据集，统计 lnP 相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 取平均")