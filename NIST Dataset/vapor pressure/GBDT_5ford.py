# # # import pandas as pd
# # # import numpy as np
# # # from pathlib import Path
# # #
# # # from sklearn.ensemble import GradientBoostingRegressor, HistGradientBoostingRegressor
# # # from sklearn.linear_model import Ridge
# # # from sklearn.model_selection import KFold
# # # from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
# # # from scipy.stats import ttest_rel
# # #
# # # import warnings
# # # warnings.filterwarnings("ignore")
# # #
# # # pd.set_option("display.float_format", "{:.10f}".format)
# # # np.set_printoptions(suppress=True, precision=10)
# # #
# # # # =========================================================
# # # # 0. 全局设置（目标改为 P）
# # # # =========================================================
# # # input_file = Path("dataset_selected_by_two_k_with_lnP_invT_interpolation_8points.xlsx")
# # # data_sheet = "Data_selected"
# # # groups_sheet = "Groups_selected"
# # # anchor_sheet = "Interpolated_k1_k2"
# # #
# # # output_file = Path("GBDT_direct_vs_anchor_baseline_residual_5fold_CV_P_target.xlsx")
# # #
# # # material_key_col = "material_key"
# # # temp_col = "T_K"
# # #
# # # # 目标列：优先使用已有蒸汽压列，否则用 lnP 计算
# # # pressure_candidates = [
# # #     "VaporPressure_kPa",
# # #     "vapor_pressure_kPa",
# # #     "Vapor_Pressure_kPa",
# # #     "P_vapor_kPa",
# # #     "property_value",
# # # ]
# # # lnp_candidates = ["lnP_kPa", "lnP", "ln_VaporPressure_kPa", "ln_pressure"]
# # #
# # # n_group_features_to_use = 220
# # # use_fixed_group_position = True
# # # group_start_col_1based = 3
# # # group_end_col_1based = 222
# # #
# # # # 锚点相关列（原始为 lnP 形式，需转换为 P）
# # # anchor_lnp_col = "lnP_kPa_interp_at_k1Tb"  # 对数锚点
# # # boiling_col = "boiling_T_K"
# # # k1_col = "k1"
# # # anchor_T_col = "k1_times_boiling_T_K"
# # #
# # # n_outer_folds = 5
# # # random_state = 42
# # #
# # # # 锚点子模型参数（全数据训练，目标改为 P_anchor）
# # # hgb_params = dict(
# # #     loss="squared_error", max_iter=1200, learning_rate=0.03,
# # #     max_leaf_nodes=63, min_samples_leaf=2, l2_regularization=0.0,
# # #     early_stopping=False, random_state=random_state
# # # )
# # #
# # # # 残差 GBDT 参数（与直接GBDT相同，每折内训练）
# # # gbdt_params = {
# # #     "n_estimators": 500,
# # #     "learning_rate": 0.03,
# # #     "max_depth": 3,
# # #     "min_samples_split": 10,
# # #     "min_samples_leaf": 5,
# # #     "subsample": 0.9,
# # #     "random_state": random_state
# # # }
# # #
# # # # =========================================================
# # # # 1. 读取数据
# # # # =========================================================
# # # xls = pd.ExcelFile(input_file)
# # # df_data = pd.read_excel(input_file, sheet_name=data_sheet)
# # # df_groups_raw = pd.read_excel(input_file, sheet_name=groups_sheet)
# # # df_anchor = pd.read_excel(input_file, sheet_name=anchor_sheet)
# # #
# # # print("Data_selected 行数:", len(df_data))
# # # print("Groups_selected 物质数:", len(df_groups_raw))
# # # print("Interpolated_k1_k2 物质数:", len(df_anchor))
# # #
# # # # =========================================================
# # # # 2. 准备 material_key
# # # # =========================================================
# # # def is_valid_value(x):
# # #     if pd.isna(x): return False
# # #     s = str(x).strip()
# # #     if s == "" or s.lower() in ["nan","none","null","待定"]: return False
# # #     return True
# # #
# # # def build_material_key(row):
# # #     for col in ["material_key","inchikey","cas","compound_name","formula"]:
# # #         if col in row.index and is_valid_value(row[col]):
# # #             if col=="material_key": return str(row[col]).strip()
# # #             return f"{col}:{str(row[col]).strip()}"
# # #     return "unknown_material"
# # #
# # # for df in [df_data, df_groups_raw, df_anchor]:
# # #     if material_key_col not in df.columns:
# # #         df[material_key_col] = df.apply(build_material_key, axis=1)
# # #     df[material_key_col] = df[material_key_col].astype(str).str.strip()
# # #
# # # # =========================================================
# # # # 3. 找到目标列（优先使用原始压力列，否则从 lnP 计算）
# # # # =========================================================
# # # def find_first_existing_col(df, candidates, col_type):
# # #     for col in candidates:
# # #         if col in df.columns:
# # #             return col
# # #     raise ValueError(f"没有找到 {col_type} 列。候选: {candidates}")
# # #
# # # def find_pressure_column(df):
# # #     # 先找原始压力列
# # #     for col in pressure_candidates:
# # #         if col in df.columns:
# # #             return col, "direct"
# # #     # 找不到则找 lnP 列，后续计算 exp
# # #     for col in lnp_candidates:
# # #         if col in df.columns:
# # #             return col, "lnP"
# # #     raise ValueError("未找到蒸汽压或 lnP 列")
# # #
# # # target_col, target_type = find_pressure_column(df_data)
# # # print("目标蒸汽压列:", target_col, "类型:", target_type)
# # #
# # # # 如果只有 lnP，则计算 P 列
# # # if target_type == "lnP":
# # #     df_data["P_kPa"] = np.exp(df_data[target_col])
# # #     target_col = "P_kPa"
# # #     print("已从 lnP 计算 P_kPa 作为目标")
# # #
# # # # 温度列
# # # if temp_col not in df_data.columns:
# # #     raise ValueError(f"Data_selected 中没有找到温度列: {temp_col}")
# # #
# # # # 锚点列（同样需要转换为 P_anchor）
# # # if anchor_lnp_col in df_anchor.columns:
# # #     # 计算 P_anchor
# # #     df_anchor["P_anchor_kPa"] = np.exp(df_anchor[anchor_lnp_col])
# # #     anchor_p_col = "P_anchor_kPa"
# # # else:
# # #     # 如果已有直接的压力锚点列，可在此添加
# # #     raise ValueError(f"锚点表中没有找到 {anchor_lnp_col}，无法计算 P_anchor")
# # #
# # # print("使用蒸汽压锚点列:", anchor_p_col)
# # #
# # # # =========================================================
# # # # 4. 识别基团列
# # # # =========================================================
# # # def identify_group_columns(df_groups, n=220):
# # #     if use_fixed_group_position:
# # #         start_idx = group_start_col_1based - 1
# # #         end_excl = group_end_col_1based
# # #         if len(df_groups.columns) < end_excl:
# # #             raise ValueError(f"基团列数不足，需要到第 {group_end_col_1based} 列")
# # #         group_cols = list(df_groups.columns[start_idx:end_excl])
# # #         if len(group_cols) != n:
# # #             raise ValueError(f"固定列位置识别到 {len(group_cols)} 个基团，需要 {n}")
# # #         return group_cols
# # #     else:
# # #         metadata_keywords = ["original_material_index","material_key","compound","name","cas","formula","smiles","inchi","inchikey","pubchem","phase","property","boiling","temperature","temp","t_k","pressure","lnp","vapor","k1","k2","interp","status","range"]
# # #         candidate_cols = []
# # #         for col in df_groups.columns:
# # #             if any(k in col.lower() for k in metadata_keywords):
# # #                 continue
# # #             if pd.to_numeric(df_groups[col], errors="coerce").notna().sum()>0:
# # #                 candidate_cols.append(col)
# # #         if len(candidate_cols) < n:
# # #             raise ValueError(f"自动识别基团仅 {len(candidate_cols)} 个，少于 {n}")
# # #         return candidate_cols[:n]
# # #
# # # group_cols_220 = identify_group_columns(df_groups_raw, n_group_features_to_use)
# # # df_groups_numeric = df_groups_raw[group_cols_220].apply(pd.to_numeric, errors="coerce").fillna(0.0)
# # # nonzero_mask = df_groups_numeric.abs().sum(axis=0) != 0
# # # used_group_cols = df_groups_numeric.columns[nonzero_mask].tolist()
# # # df_groups_used = df_groups_numeric[used_group_cols].copy()
# # # print("有效基团数量:", len(used_group_cols))
# # #
# # # # =========================================================
# # # # 5. 准备锚点数据（每个物质一个，全数据）
# # # # =========================================================
# # # anchor_keep = [material_key_col, anchor_p_col, boiling_col]
# # # if k1_col in df_anchor.columns:
# # #     anchor_keep.append(k1_col)
# # # if anchor_T_col in df_anchor.columns:
# # #     anchor_keep.append(anchor_T_col)
# # # df_anchor_slim = df_anchor[anchor_keep].drop_duplicates(subset=[material_key_col])
# # # df_anchor_slim[anchor_p_col] = pd.to_numeric(df_anchor_slim[anchor_p_col], errors="coerce")
# # # df_anchor_slim[boiling_col] = pd.to_numeric(df_anchor_slim[boiling_col], errors="coerce")
# # # if k1_col in df_anchor_slim.columns:
# # #     df_anchor_slim["k1_valid"] = pd.to_numeric(df_anchor_slim[k1_col], errors="coerce")
# # # else:
# # #     df_anchor_slim["k1_valid"] = df_anchor_slim[anchor_T_col] / df_anchor_slim[boiling_col]
# # # k1_median = df_anchor_slim["k1_valid"].replace([np.inf,-np.inf],np.nan).median()
# # # df_anchor_slim["k1_valid"] = df_anchor_slim["k1_valid"].fillna(k1_median)
# # #
# # # valid_anchor = (df_anchor_slim[anchor_p_col].notna() &
# # #                 df_anchor_slim[boiling_col].notna() &
# # #                 (df_anchor_slim[boiling_col] > 0) &
# # #                 np.isfinite(df_anchor_slim["k1_valid"]))
# # # df_anchor_valid = df_anchor_slim[valid_anchor].copy()
# # # print("有效锚点物质数:", len(df_anchor_valid))
# # #
# # # # =========================================================
# # # # 6. 全数据训练锚点子模型（预测 P_anchor）
# # # # =========================================================
# # # # 合并物质级基团和锚点
# # # df_material = df_groups_used.reset_index().rename(columns={"index":"orig_idx"})
# # # df_material[material_key_col] = df_groups_raw.loc[df_material.index, material_key_col].values
# # # df_material = df_material.merge(df_anchor_valid, on=material_key_col, how="inner")
# # # df_material = df_material.dropna(subset=used_group_cols+[anchor_p_col, boiling_col, "k1_valid"])
# # # df_material = df_material.reset_index(drop=True)
# # # print("合并后物质数:", len(df_material))
# # #
# # # X_anchor = df_material[used_group_cols].values.astype(float)
# # # y_P_anchor = df_material[anchor_p_col].values.astype(float)
# # # y_boiling = df_material[boiling_col].values.astype(float)
# # #
# # # anchor_P_model = HistGradientBoostingRegressor(**hgb_params)
# # # anchor_boiling_model = HistGradientBoostingRegressor(**hgb_params)
# # # anchor_P_model.fit(X_anchor, y_P_anchor)
# # # anchor_boiling_model.fit(X_anchor, y_boiling)
# # #
# # # # 预测所有物质的锚点
# # # df_material["P_anchor_pred"] = anchor_P_model.predict(X_anchor)
# # # df_material["boiling_T_pred"] = anchor_boiling_model.predict(X_anchor)
# # # df_material["anchor_T_pred"] = df_material["k1_valid"] * df_material["boiling_T_pred"]
# # # df_material["invT_anchor_pred"] = 1.0 / df_material["anchor_T_pred"]
# # #
# # # # =========================================================
# # # # 7. 展开温度点数据，匹配物质信息（包括锚点预测值）
# # # # =========================================================
# # # df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
# # # df_data[target_col] = pd.to_numeric(df_data[target_col], errors="coerce")
# # # df_data["InvT"] = 1.0 / df_data[temp_col]
# # #
# # # # 将物质级锚点预测合并到每个温度点
# # # df_long = df_data.merge(df_material[[material_key_col] + used_group_cols + ["P_anchor_pred", "invT_anchor_pred"]],
# # #                         on=material_key_col, how="inner")
# # # df_long = df_long.dropna(subset=[target_col, temp_col, "InvT"] + used_group_cols + ["P_anchor_pred", "invT_anchor_pred"])
# # # df_long = df_long.reset_index(drop=True)
# # # print("最终温度点总数:", len(df_long))
# # #
# # # # 提取数组
# # # X_groups = df_long[used_group_cols].values.astype(float)
# # # invT_all = df_long["InvT"].values.astype(float)
# # # P_true = df_long[target_col].values.astype(float)
# # # P_anchor_pred = df_long["P_anchor_pred"].values.astype(float)
# # # invT_anchor_pred = df_long["invT_anchor_pred"].values.astype(float)
# # # material_keys = df_long[material_key_col].values
# # #
# # # unique_materials = np.unique(material_keys)
# # # material_to_idx = {k:i for i,k in enumerate(unique_materials)}
# # # material_ids = np.array([material_to_idx[k] for k in material_keys])
# # #
# # # # =========================================================
# # # # 8. 辅助函数：构建方法A（直接GBDT）特征
# # # # =========================================================
# # # def build_direct_features(sample_mask):
# # #     return np.hstack([X_groups[sample_mask], invT_all[sample_mask].reshape(-1,1)])
# # #
# # # # =========================================================
# # # # 9. 方法B：基于全局锚点预测，每折内训练基线和残差模型（P 空间）
# # # # =========================================================
# # # def train_and_predict_methodB(train_mask, test_mask):
# # #     df_train = df_long[train_mask].copy()
# # #     df_test = df_long[test_mask].copy()
# # #
# # #     # 基线模型：P_base = P_anchor_pred + (1/T - 1/T_anchor_pred) * Σ Nk Ak
# # #     delta_invT_train = df_train["InvT"].values - df_train["invT_anchor_pred"].values
# # #     X_base_train = df_train[used_group_cols].values * delta_invT_train.reshape(-1, 1)
# # #     y_base_train = df_train[target_col].values - df_train["P_anchor_pred"].values
# # #
# # #     valid_base = np.isfinite(X_base_train).all(axis=1) & np.isfinite(y_base_train)
# # #     if valid_base.sum() == 0:
# # #         raise ValueError("基线模型无有效训练样本")
# # #     base_model = Ridge(alpha=1.0, fit_intercept=False)
# # #     base_model.fit(X_base_train[valid_base], y_base_train[valid_base])
# # #
# # #     # 测试集基线预测
# # #     delta_invT_test = df_test["InvT"].values - df_test["invT_anchor_pred"].values
# # #     X_base_test = df_test[used_group_cols].values * delta_invT_test.reshape(-1, 1)
# # #     valid_base_test = np.isfinite(X_base_test).all(axis=1)
# # #     baseline_delta = np.full(len(df_test), np.nan)
# # #     baseline_delta[valid_base_test] = base_model.predict(X_base_test[valid_base_test])
# # #     baseline_P = df_test["P_anchor_pred"].values + baseline_delta
# # #
# # #     # 残差模型训练
# # #     delta_invT_train2 = df_train["InvT"].values - df_train["invT_anchor_pred"].values
# # #     X_base_train2 = df_train[used_group_cols].values * delta_invT_train2.reshape(-1, 1)
# # #     baseline_delta_train = base_model.predict(X_base_train2)
# # #     baseline_P_train = df_train["P_anchor_pred"].values + baseline_delta_train
# # #     residual_y_train = df_train[target_col].values - baseline_P_train
# # #
# # #     residual_X_train = np.hstack([df_train[used_group_cols].values, df_train["InvT"].values.reshape(-1, 1)])
# # #     valid_res = np.isfinite(residual_X_train).all(axis=1) & np.isfinite(residual_y_train)
# # #     if valid_res.sum() == 0:
# # #         raise ValueError("残差模型无有效训练样本")
# # #     res_model = GradientBoostingRegressor(**gbdt_params)
# # #     res_model.fit(residual_X_train[valid_res], residual_y_train[valid_res])
# # #
# # #     # 测试集残差预测
# # #     residual_X_test = np.hstack([df_test[used_group_cols].values, df_test["InvT"].values.reshape(-1, 1)])
# # #     valid_res_test = np.isfinite(residual_X_test).all(axis=1)
# # #     residual_pred = np.full(len(df_test), np.nan)
# # #     residual_pred[valid_res_test] = res_model.predict(residual_X_test[valid_res_test])
# # #
# # #     final_P = baseline_P + residual_pred
# # #     return final_P
# # #
# # # # =========================================================
# # # # 10. 5折交叉验证（按物质划分）
# # # # =========================================================
# # # kf = KFold(n_splits=n_outer_folds, shuffle=True, random_state=random_state)
# # # metrics_direct = []
# # # metrics_methodB = []
# # #
# # # # 定义评价函数（仅针对 P 空间）
# # # def compute_metrics_P(y_true, y_pred):
# # #     mask = np.isfinite(y_true) & np.isfinite(y_pred)
# # #     y_true = y_true[mask]
# # #     y_pred = y_pred[mask]
# # #     if len(y_true) == 0:
# # #         return {k: np.nan for k in ["R2", "MSE", "RMSE", "MAE", "ARD_percent",
# # #                                     "leq1%", "leq5%", "leq10%", "max_rel%"]}
# # #     r2 = r2_score(y_true, y_pred)
# # #     mse = mean_squared_error(y_true, y_pred)
# # #     rmse = np.sqrt(mse)
# # #     mae = mean_absolute_error(y_true, y_pred)
# # #
# # #     valid = np.abs(y_true) > 1e-12
# # #     if valid.sum() > 0:
# # #         rel_err = np.abs((y_pred[valid] - y_true[valid]) / y_true[valid]) * 100
# # #         ard = np.mean(rel_err)
# # #         max_rel = np.max(rel_err)
# # #         le1 = np.mean(rel_err <= 1) * 100
# # #         le5 = np.mean(rel_err <= 5) * 100
# # #         le10 = np.mean(rel_err <= 10) * 100
# # #     else:
# # #         ard = max_rel = le1 = le5 = le10 = np.nan
# # #     return {
# # #         "R2": r2, "MSE": mse, "RMSE": rmse, "MAE": mae,
# # #         "ARD_percent": ard, "max_rel%": max_rel,
# # #         "leq1%": le1, "leq5%": le5, "leq10%": le10
# # #     }
# # #
# # # for fold, (train_idx, test_idx) in enumerate(kf.split(unique_materials)):
# # #     print(f"\n========== Fold {fold+1}/{n_outer_folds} ==========")
# # #     train_materials = unique_materials[train_idx]
# # #     test_materials = unique_materials[test_idx]
# # #
# # #     train_mask = np.isin(material_keys, train_materials)
# # #     test_mask = np.isin(material_keys, test_materials)
# # #
# # #     # ---------- 方法A：直接GBDT ----------
# # #     X_train_A = build_direct_features(train_mask)
# # #     y_train_A = P_true[train_mask]
# # #     valid_A = np.isfinite(X_train_A).all(axis=1) & np.isfinite(y_train_A)
# # #     X_train_A = X_train_A[valid_A]
# # #     y_train_A = y_train_A[valid_A]
# # #     model_A = GradientBoostingRegressor(**gbdt_params)
# # #     model_A.fit(X_train_A, y_train_A)
# # #
# # #     X_test_A = build_direct_features(test_mask)
# # #     y_test_A = P_true[test_mask]
# # #     valid_test_A = np.isfinite(X_test_A).all(axis=1)
# # #     y_pred_A = np.full(len(y_test_A), np.nan)
# # #     y_pred_A[valid_test_A] = model_A.predict(X_test_A[valid_test_A])
# # #
# # #     # ---------- 方法B ----------
# # #     try:
# # #         y_pred_B = train_and_predict_methodB(train_mask, test_mask)
# # #     except Exception as e:
# # #         print(f"  Fold {fold+1} 方法B失败: {e}")
# # #         y_pred_B = np.full(len(y_test_A), np.nan)
# # #
# # #     m_A = compute_metrics_P(y_test_A, y_pred_A)
# # #     m_B = compute_metrics_P(y_test_A, y_pred_B)
# # #     m_A["fold"] = fold+1
# # #     m_B["fold"] = fold+1
# # #     metrics_direct.append(m_A)
# # #     metrics_methodB.append(m_B)
# # #
# # # # =========================================================
# # # # 11. 汇总统计
# # # # =========================================================
# # # df_direct = pd.DataFrame(metrics_direct)
# # # df_methodB = pd.DataFrame(metrics_methodB)
# # #
# # # metric_names = [c for c in df_direct.columns if c not in ["fold"]]
# # #
# # # def summarize(df, name):
# # #     rows = []
# # #     for metric in metric_names:
# # #         vals = df[metric].dropna().values
# # #         if len(vals) == 0:
# # #             mean_std = "NaN"
# # #         else:
# # #             mean_val = np.mean(vals)
# # #             std_val = np.std(vals, ddof=1)
# # #             mean_std = f"{mean_val:.4f} ± {std_val:.4f}"
# # #         rows.append({"Model": name, "Metric": metric, "Mean±Std": mean_std})
# # #     return pd.DataFrame(rows)
# # #
# # # summary_direct = summarize(df_direct, "GBDT_direct (P)")
# # # summary_methodB = summarize(df_methodB, "Anchor+linear+GBDT_residual (P)")
# # # summary_all = pd.concat([summary_direct, summary_methodB], ignore_index=True)
# # #
# # # print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
# # # print(summary_all.to_string(index=False))
# # #
# # # # =========================================================
# # # # 12. 配对 t 检验
# # # # =========================================================
# # # t_test_results = []
# # # for metric in metric_names:
# # #     vals_A = df_direct[metric].dropna().values
# # #     vals_B = df_methodB[metric].dropna().values
# # #     if len(vals_A) == len(vals_B) and len(vals_A) > 1:
# # #         t_stat, p_val = ttest_rel(vals_A, vals_B)
# # #         # 对于误差类指标越小越好，R2 越大越好
# # #         if metric == "R2":
# # #             better = "methodB" if np.mean(vals_B) > np.mean(vals_A) else "direct"
# # #             sig = p_val < 0.05
# # #         else:
# # #             better = "methodB" if np.mean(vals_B) < np.mean(vals_A) else "direct"
# # #             sig = p_val < 0.05
# # #         t_test_results.append({
# # #             "Metric": metric,
# # #             "Mean_direct": f"{np.mean(vals_A):.4f}",
# # #             "Mean_methodB": f"{np.mean(vals_B):.4f}",
# # #             "p-value": f"{p_val:.4e}",
# # #             "Significant(p<0.05)": sig,
# # #             "Better model": better
# # #         })
# # #
# # # df_ttest = pd.DataFrame(t_test_results)
# # # print("\n========== Paired t-test ==========")
# # # print(df_ttest.to_string(index=False))
# # #
# # # # =========================================================
# # # # 13. 保存结果
# # # # =========================================================
# # # with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
# # #     df_direct.to_excel(writer, sheet_name="Fold_Metrics_Direct", index=False)
# # #     df_methodB.to_excel(writer, sheet_name="Fold_Metrics_MethodB", index=False)
# # #     summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
# # #     df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)
# # #
# # #     pd.DataFrame([
# # #         {"param": "n_outer_folds", "value": n_outer_folds},
# # #         {"param": "random_state", "value": random_state},
# # #         {"param": "n_group_features", "value": len(used_group_cols)},
# # #         {"param": "total_samples", "value": len(P_true)},
# # #         {"param": "n_materials", "value": len(unique_materials)},
# # #         {"param": "direct_GBDT_params", "value": str(gbdt_params)},
# # #         {"param": "methodB_baseline", "value": "Ridge(alpha=1.0, fit_intercept=False) in P space"},
# # #         {"param": "methodB_residual_gbdt", "value": "same as direct GBDT"},
# # #         {"param": "anchor_submodel", "value": "HistGradientBoostingRegressor trained on P_anchor"},
# # #         {"param": "target", "value": "Vapor Pressure (P, kPa)"},
# # #     ]).to_excel(writer, sheet_name="Run_Info", index=False)
# # #
# # #     from openpyxl import load_workbook
# # #     workbook = writer.book
# # #     number_format = "0.0000000000"
# # #     for sheetname in writer.sheets:
# # #         ws = workbook[sheetname]
# # #         for row in ws.iter_rows():
# # #             for cell in row:
# # #                 if isinstance(cell.value, float):
# # #                     cell.number_format = number_format
# # #         for col in ws.columns:
# # #             max_len = 0
# # #             col_letter = col[0].column_letter
# # #             for cell in col:
# # #                 if cell.value:
# # #                     max_len = max(max_len, len(str(cell.value)))
# # #             ws.column_dimensions[col_letter].width = min(max_len+2, 40)
# # #
# # # print(f"\n保存完成: {output_file}")
# #
# # import pandas as pd
# # import numpy as np
# # from pathlib import Path
# #
# # from sklearn.ensemble import GradientBoostingRegressor, HistGradientBoostingRegressor
# # from sklearn.linear_model import Ridge
# # from sklearn.model_selection import KFold
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
# # # 0. 全局设置（目标为 P，同时评估 lnP）
# # # =========================================================
# # input_file = Path("dataset_selected_by_two_k_with_lnP_invT_interpolation_8points.xlsx")
# # data_sheet = "Data_selected"
# # groups_sheet = "Groups_selected"
# # anchor_sheet = "Interpolated_k1_k2"
# #
# # output_file = Path("GBDT_direct_vs_anchor_baseline_residual_5fold_CV_P_target_with_lnP_metrics.xlsx")
# #
# # material_key_col = "material_key"
# # temp_col = "T_K"
# #
# # pressure_candidates = [
# #     "VaporPressure_kPa",
# #     "vapor_pressure_kPa",
# #     "Vapor_Pressure_kPa",
# #     "P_vapor_kPa",
# #     "property_value",
# # ]
# # lnp_candidates = ["lnP_kPa", "lnP", "ln_VaporPressure_kPa", "ln_pressure"]
# #
# # n_group_features_to_use = 220
# # use_fixed_group_position = True
# # group_start_col_1based = 3
# # group_end_col_1based = 222
# #
# # anchor_lnp_col = "lnP_kPa_interp_at_k1Tb"
# # boiling_col = "boiling_T_K"
# # k1_col = "k1"
# # anchor_T_col = "k1_times_boiling_T_K"
# #
# # n_outer_folds = 5
# # random_state = 42
# #
# # hgb_params = dict(
# #     loss="squared_error", max_iter=1200, learning_rate=0.03,
# #     max_leaf_nodes=63, min_samples_leaf=2, l2_regularization=0.0,
# #     early_stopping=False, random_state=random_state
# # )
# #
# # gbdt_params = {
# #     "n_estimators": 500,
# #     "learning_rate": 0.03,
# #     "max_depth": 3,
# #     "min_samples_split": 10,
# #     "min_samples_leaf": 5,
# #     "subsample": 0.9,
# #     "random_state": random_state
# # }
# #
# # # =========================================================
# # # 1. 读取数据
# # # =========================================================
# # df_data = pd.read_excel(input_file, sheet_name=data_sheet)
# # df_groups_raw = pd.read_excel(input_file, sheet_name=groups_sheet)
# # df_anchor = pd.read_excel(input_file, sheet_name=anchor_sheet)
# #
# # print("Data_selected 行数:", len(df_data))
# # print("Groups_selected 物质数:", len(df_groups_raw))
# # print("Interpolated_k1_k2 物质数:", len(df_anchor))
# #
# # # =========================================================
# # # 2. 准备 material_key
# # # =========================================================
# # def is_valid_value(x):
# #     if pd.isna(x): return False
# #     s = str(x).strip()
# #     if s == "" or s.lower() in ["nan","none","null","待定"]: return False
# #     return True
# #
# # def build_material_key(row):
# #     for col in ["material_key","inchikey","cas","compound_name","formula"]:
# #         if col in row.index and is_valid_value(row[col]):
# #             if col=="material_key": return str(row[col]).strip()
# #             return f"{col}:{str(row[col]).strip()}"
# #     return "unknown_material"
# #
# # for df in [df_data, df_groups_raw, df_anchor]:
# #     if material_key_col not in df.columns:
# #         df[material_key_col] = df.apply(build_material_key, axis=1)
# #     df[material_key_col] = df[material_key_col].astype(str).str.strip()
# #
# # # =========================================================
# # # 3. 找到目标列（优先使用原始压力列，否则从 lnP 计算）
# # # =========================================================
# # def find_first_existing_col(df, candidates, col_type):
# #     for col in candidates:
# #         if col in df.columns:
# #             return col
# #     raise ValueError(f"没有找到 {col_type} 列。候选: {candidates}")
# #
# # def find_pressure_column(df):
# #     for col in pressure_candidates:
# #         if col in df.columns:
# #             return col, "direct"
# #     for col in lnp_candidates:
# #         if col in df.columns:
# #             return col, "lnP"
# #     raise ValueError("未找到蒸汽压或 lnP 列")
# #
# # target_col, target_type = find_pressure_column(df_data)
# # print("目标蒸汽压列:", target_col, "类型:", target_type)
# #
# # if target_type == "lnP":
# #     df_data["P_kPa"] = np.exp(df_data[target_col])
# #     target_col = "P_kPa"
# #     print("已从 lnP 计算 P_kPa 作为目标")
# #
# # if temp_col not in df_data.columns:
# #     raise ValueError(f"Data_selected 中没有找到温度列: {temp_col}")
# #
# # # 锚点列转换为 P_anchor
# # if anchor_lnp_col in df_anchor.columns:
# #     df_anchor["P_anchor_kPa"] = np.exp(df_anchor[anchor_lnp_col])
# #     anchor_p_col = "P_anchor_kPa"
# # else:
# #     raise ValueError(f"锚点表中没有找到 {anchor_lnp_col}，无法计算 P_anchor")
# # print("使用蒸汽压锚点列:", anchor_p_col)
# #
# # # =========================================================
# # # 4. 识别基团列
# # # =========================================================
# # def identify_group_columns(df_groups, n=220):
# #     if use_fixed_group_position:
# #         start_idx = group_start_col_1based - 1
# #         end_excl = group_end_col_1based
# #         if len(df_groups.columns) < end_excl:
# #             raise ValueError(f"基团列数不足，需要到第 {group_end_col_1based} 列")
# #         group_cols = list(df_groups.columns[start_idx:end_excl])
# #         if len(group_cols) != n:
# #             raise ValueError(f"固定列位置识别到 {len(group_cols)} 个基团，需要 {n}")
# #         return group_cols
# #     else:
# #         metadata_keywords = ["original_material_index","material_key","compound","name","cas","formula","smiles","inchi","inchikey","pubchem","phase","property","boiling","temperature","temp","t_k","pressure","lnp","vapor","k1","k2","interp","status","range"]
# #         candidate_cols = []
# #         for col in df_groups.columns:
# #             if any(k in col.lower() for k in metadata_keywords):
# #                 continue
# #             if pd.to_numeric(df_groups[col], errors="coerce").notna().sum()>0:
# #                 candidate_cols.append(col)
# #         if len(candidate_cols) < n:
# #             raise ValueError(f"自动识别基团仅 {len(candidate_cols)} 个，少于 {n}")
# #         return candidate_cols[:n]
# #
# # group_cols_220 = identify_group_columns(df_groups_raw, n_group_features_to_use)
# # df_groups_numeric = df_groups_raw[group_cols_220].apply(pd.to_numeric, errors="coerce").fillna(0.0)
# # nonzero_mask = df_groups_numeric.abs().sum(axis=0) != 0
# # used_group_cols = df_groups_numeric.columns[nonzero_mask].tolist()
# # df_groups_used = df_groups_numeric[used_group_cols].copy()
# # print("有效基团数量:", len(used_group_cols))
# #
# # # =========================================================
# # # 5. 准备锚点数据
# # # =========================================================
# # anchor_keep = [material_key_col, anchor_p_col, boiling_col]
# # if k1_col in df_anchor.columns:
# #     anchor_keep.append(k1_col)
# # if anchor_T_col in df_anchor.columns:
# #     anchor_keep.append(anchor_T_col)
# # df_anchor_slim = df_anchor[anchor_keep].drop_duplicates(subset=[material_key_col])
# # df_anchor_slim[anchor_p_col] = pd.to_numeric(df_anchor_slim[anchor_p_col], errors="coerce")
# # df_anchor_slim[boiling_col] = pd.to_numeric(df_anchor_slim[boiling_col], errors="coerce")
# # if k1_col in df_anchor_slim.columns:
# #     df_anchor_slim["k1_valid"] = pd.to_numeric(df_anchor_slim[k1_col], errors="coerce")
# # else:
# #     df_anchor_slim["k1_valid"] = df_anchor_slim[anchor_T_col] / df_anchor_slim[boiling_col]
# # k1_median = df_anchor_slim["k1_valid"].replace([np.inf,-np.inf],np.nan).median()
# # df_anchor_slim["k1_valid"] = df_anchor_slim["k1_valid"].fillna(k1_median)
# #
# # valid_anchor = (df_anchor_slim[anchor_p_col].notna() &
# #                 df_anchor_slim[boiling_col].notna() &
# #                 (df_anchor_slim[boiling_col] > 0) &
# #                 np.isfinite(df_anchor_slim["k1_valid"]))
# # df_anchor_valid = df_anchor_slim[valid_anchor].copy()
# # print("有效锚点物质数:", len(df_anchor_valid))
# #
# # # =========================================================
# # # 6. 全数据训练锚点子模型（预测 P_anchor）
# # # =========================================================
# # df_material = df_groups_used.reset_index().rename(columns={"index":"orig_idx"})
# # df_material[material_key_col] = df_groups_raw.loc[df_material.index, material_key_col].values
# # df_material = df_material.merge(df_anchor_valid, on=material_key_col, how="inner")
# # df_material = df_material.dropna(subset=used_group_cols+[anchor_p_col, boiling_col, "k1_valid"])
# # df_material = df_material.reset_index(drop=True)
# # print("合并后物质数:", len(df_material))
# #
# # X_anchor = df_material[used_group_cols].values.astype(float)
# # y_P_anchor = df_material[anchor_p_col].values.astype(float)
# # y_boiling = df_material[boiling_col].values.astype(float)
# #
# # anchor_P_model = HistGradientBoostingRegressor(**hgb_params)
# # anchor_boiling_model = HistGradientBoostingRegressor(**hgb_params)
# # anchor_P_model.fit(X_anchor, y_P_anchor)
# # anchor_boiling_model.fit(X_anchor, y_boiling)
# #
# # df_material["P_anchor_pred"] = anchor_P_model.predict(X_anchor)
# # df_material["boiling_T_pred"] = anchor_boiling_model.predict(X_anchor)
# # df_material["anchor_T_pred"] = df_material["k1_valid"] * df_material["boiling_T_pred"]
# # df_material["invT_anchor_pred"] = 1.0 / df_material["anchor_T_pred"]
# #
# # # =========================================================
# # # 7. 展开温度点数据
# # # =========================================================
# # df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
# # df_data[target_col] = pd.to_numeric(df_data[target_col], errors="coerce")
# # df_data["InvT"] = 1.0 / df_data[temp_col]
# #
# # df_long = df_data.merge(df_material[[material_key_col] + used_group_cols + ["P_anchor_pred", "invT_anchor_pred"]],
# #                         on=material_key_col, how="inner")
# # df_long = df_long.dropna(subset=[target_col, temp_col, "InvT"] + used_group_cols + ["P_anchor_pred", "invT_anchor_pred"])
# # df_long = df_long.reset_index(drop=True)
# # print("最终温度点总数:", len(df_long))
# #
# # X_groups = df_long[used_group_cols].values.astype(float)
# # invT_all = df_long["InvT"].values.astype(float)
# # P_true = df_long[target_col].values.astype(float)
# # P_anchor_pred = df_long["P_anchor_pred"].values.astype(float)
# # invT_anchor_pred = df_long["invT_anchor_pred"].values.astype(float)
# # material_keys = df_long[material_key_col].values
# #
# # unique_materials = np.unique(material_keys)
# # material_to_idx = {k:i for i,k in enumerate(unique_materials)}
# # material_ids = np.array([material_to_idx[k] for k in material_keys])
# #
# # # =========================================================
# # # 8. 辅助函数：构建特征
# # # =========================================================
# # def build_direct_features(sample_mask):
# #     return np.hstack([X_groups[sample_mask], invT_all[sample_mask].reshape(-1,1)])
# #
# # # =========================================================
# # # 9. 方法B：基于锚点的基线+残差GBDT
# # # =========================================================
# # def train_and_predict_methodB(train_mask, test_mask):
# #     df_train = df_long[train_mask].copy()
# #     df_test = df_long[test_mask].copy()
# #
# #     delta_invT_train = df_train["InvT"].values - df_train["invT_anchor_pred"].values
# #     X_base_train = df_train[used_group_cols].values * delta_invT_train.reshape(-1, 1)
# #     y_base_train = df_train[target_col].values - df_train["P_anchor_pred"].values
# #
# #     valid_base = np.isfinite(X_base_train).all(axis=1) & np.isfinite(y_base_train)
# #     if valid_base.sum() == 0:
# #         raise ValueError("基线模型无有效训练样本")
# #     base_model = Ridge(alpha=1.0, fit_intercept=False)
# #     base_model.fit(X_base_train[valid_base], y_base_train[valid_base])
# #
# #     delta_invT_test = df_test["InvT"].values - df_test["invT_anchor_pred"].values
# #     X_base_test = df_test[used_group_cols].values * delta_invT_test.reshape(-1, 1)
# #     valid_base_test = np.isfinite(X_base_test).all(axis=1)
# #     baseline_delta = np.full(len(df_test), np.nan)
# #     baseline_delta[valid_base_test] = base_model.predict(X_base_test[valid_base_test])
# #     baseline_P = df_test["P_anchor_pred"].values + baseline_delta
# #
# #     # 残差模型
# #     delta_invT_train2 = df_train["InvT"].values - df_train["invT_anchor_pred"].values
# #     X_base_train2 = df_train[used_group_cols].values * delta_invT_train2.reshape(-1, 1)
# #     baseline_delta_train = base_model.predict(X_base_train2)
# #     baseline_P_train = df_train["P_anchor_pred"].values + baseline_delta_train
# #     residual_y_train = df_train[target_col].values - baseline_P_train
# #
# #     residual_X_train = np.hstack([df_train[used_group_cols].values, df_train["InvT"].values.reshape(-1, 1)])
# #     valid_res = np.isfinite(residual_X_train).all(axis=1) & np.isfinite(residual_y_train)
# #     if valid_res.sum() == 0:
# #         raise ValueError("残差模型无有效训练样本")
# #     res_model = GradientBoostingRegressor(**gbdt_params)
# #     res_model.fit(residual_X_train[valid_res], residual_y_train[valid_res])
# #
# #     residual_X_test = np.hstack([df_test[used_group_cols].values, df_test["InvT"].values.reshape(-1, 1)])
# #     valid_res_test = np.isfinite(residual_X_test).all(axis=1)
# #     residual_pred = np.full(len(df_test), np.nan)
# #     residual_pred[valid_res_test] = res_model.predict(residual_X_test[valid_res_test])
# #
# #     final_P = baseline_P + residual_pred
# #     return final_P
# #
# # # =========================================================
# # # 10. 评价函数（P 空间 + lnP 空间）
# # # =========================================================
# # def compute_metrics_P(y_true, y_pred):
# #     mask = np.isfinite(y_true) & np.isfinite(y_pred)
# #     y_true = y_true[mask]
# #     y_pred = y_pred[mask]
# #     if len(y_true) == 0:
# #         return {k: np.nan for k in ["R2", "MSE", "RMSE", "MAE", "ARD_percent",
# #                                     "leq1%", "leq5%", "leq10%", "max_rel%"]}
# #     r2 = r2_score(y_true, y_pred)
# #     mse = mean_squared_error(y_true, y_pred)
# #     rmse = np.sqrt(mse)
# #     mae = mean_absolute_error(y_true, y_pred)
# #
# #     valid = np.abs(y_true) > 1e-12
# #     if valid.sum() > 0:
# #         rel_err = np.abs((y_pred[valid] - y_true[valid]) / y_true[valid]) * 100
# #         ard = np.mean(rel_err)
# #         max_rel = np.max(rel_err)
# #         le1 = np.mean(rel_err <= 1) * 100
# #         le5 = np.mean(rel_err <= 5) * 100
# #         le10 = np.mean(rel_err <= 10) * 100
# #     else:
# #         ard = max_rel = le1 = le5 = le10 = np.nan
# #     return {
# #         "R2": r2, "MSE": mse, "RMSE": rmse, "MAE": mae,
# #         "ARD_percent": ard, "max_rel%": max_rel,
# #         "leq1%": le1, "leq5%": le5, "leq10%": le10
# #     }
# #
# # def compute_metrics_lnP(y_true_P, y_pred_P):
# #     eps = 1e-12
# #     y_true_lnP = np.log(np.clip(y_true_P, eps, None))
# #     y_pred_lnP = np.log(np.clip(y_pred_P, eps, None))
# #     mask = np.isfinite(y_true_lnP) & np.isfinite(y_pred_lnP)
# #     y_true_lnP = y_true_lnP[mask]
# #     y_pred_lnP = y_pred_lnP[mask]
# #     if len(y_true_lnP) == 0:
# #         return {k: np.nan for k in ["R2_lnP", "MSE_lnP", "RMSE_lnP", "MAE_lnP", "ARD_lnP_percent"]}
# #     r2 = r2_score(y_true_lnP, y_pred_lnP)
# #     mse = mean_squared_error(y_true_lnP, y_pred_lnP)
# #     rmse = np.sqrt(mse)
# #     mae = mean_absolute_error(y_true_lnP, y_pred_lnP)
# #     denom = np.abs(y_true_lnP)
# #     denom_mask = denom > 1e-12
# #     if denom_mask.sum() > 0:
# #         ard = np.mean(np.abs((y_pred_lnP[denom_mask] - y_true_lnP[denom_mask]) / denom[denom_mask])) * 100
# #     else:
# #         ard = np.nan
# #     return {
# #         "R2_lnP": r2,
# #         "MSE_lnP": mse,
# #         "RMSE_lnP": rmse,
# #         "MAE_lnP": mae,
# #         "ARD_lnP_percent": ard,
# #     }
# #
# # # =========================================================
# # # 11. 5折交叉验证
# # # =========================================================
# # kf = KFold(n_splits=n_outer_folds, shuffle=True, random_state=random_state)
# # metrics_direct_P = []
# # metrics_methodB_P = []
# # metrics_direct_lnP = []
# # metrics_methodB_lnP = []
# #
# # for fold, (train_idx, test_idx) in enumerate(kf.split(unique_materials)):
# #     print(f"\n========== Fold {fold+1}/{n_outer_folds} ==========")
# #     train_materials = unique_materials[train_idx]
# #     test_materials = unique_materials[test_idx]
# #
# #     train_mask = np.isin(material_keys, train_materials)
# #     test_mask = np.isin(material_keys, test_materials)
# #
# #     # ---------- 方法A：直接GBDT ----------
# #     X_train_A = build_direct_features(train_mask)
# #     y_train_A = P_true[train_mask]
# #     valid_A = np.isfinite(X_train_A).all(axis=1) & np.isfinite(y_train_A)
# #     X_train_A = X_train_A[valid_A]
# #     y_train_A = y_train_A[valid_A]
# #     model_A = GradientBoostingRegressor(**gbdt_params)
# #     model_A.fit(X_train_A, y_train_A)
# #
# #     X_test_A = build_direct_features(test_mask)
# #     y_test_A = P_true[test_mask]
# #     valid_test_A = np.isfinite(X_test_A).all(axis=1)
# #     y_pred_A = np.full(len(y_test_A), np.nan)
# #     y_pred_A[valid_test_A] = model_A.predict(X_test_A[valid_test_A])
# #
# #     # ---------- 方法B ----------
# #     try:
# #         y_pred_B = train_and_predict_methodB(train_mask, test_mask)
# #     except Exception as e:
# #         print(f"  Fold {fold+1} 方法B失败: {e}")
# #         y_pred_B = np.full(len(y_test_A), np.nan)
# #
# #     # 计算 P 空间指标
# #     mP_A = compute_metrics_P(y_test_A, y_pred_A)
# #     mP_B = compute_metrics_P(y_test_A, y_pred_B)
# #     mP_A["fold"] = fold+1
# #     mP_B["fold"] = fold+1
# #     metrics_direct_P.append(mP_A)
# #     metrics_methodB_P.append(mP_B)
# #
# #     # 计算 lnP 空间指标
# #     mlnP_A = compute_metrics_lnP(y_test_A, y_pred_A)
# #     mlnP_B = compute_metrics_lnP(y_test_A, y_pred_B)
# #     mlnP_A["fold"] = fold+1
# #     mlnP_B["fold"] = fold+1
# #     metrics_direct_lnP.append(mlnP_A)
# #     metrics_methodB_lnP.append(mlnP_B)
# #
# # # =========================================================
# # # 12. 汇总统计 (P 空间 和 lnP 空间)
# # # =========================================================
# # df_direct_P = pd.DataFrame(metrics_direct_P)
# # df_methodB_P = pd.DataFrame(metrics_methodB_P)
# # df_direct_lnP = pd.DataFrame(metrics_direct_lnP)
# # df_methodB_lnP = pd.DataFrame(metrics_methodB_lnP)
# #
# # def summarize(df, name, metric_names):
# #     rows = []
# #     for metric in metric_names:
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
# # metric_names_P = [c for c in df_direct_P.columns if c != "fold"]
# # metric_names_lnP = [c for c in df_direct_lnP.columns if c != "fold"]
# #
# # summary_P_direct = summarize(df_direct_P, "GBDT_direct (P)", metric_names_P)
# # summary_P_methodB = summarize(df_methodB_P, "Anchor+linear+GBDT_residual (P)", metric_names_P)
# # summary_P = pd.concat([summary_P_direct, summary_P_methodB], ignore_index=True)
# #
# # summary_lnP_direct = summarize(df_direct_lnP, "GBDT_direct (lnP)", metric_names_lnP)
# # summary_lnP_methodB = summarize(df_methodB_lnP, "Anchor+linear+GBDT_residual (lnP)", metric_names_lnP)
# # summary_lnP = pd.concat([summary_lnP_direct, summary_lnP_methodB], ignore_index=True)
# #
# # print("\n========== P 空间 5-Fold CV Summary ==========")
# # print(summary_P.to_string(index=False))
# # print("\n========== lnP 空间 5-Fold CV Summary ==========")
# # print(summary_lnP.to_string(index=False))
# #
# # # =========================================================
# # # 13. 配对 t 检验 (分别对 P 和 lnP)
# # # =========================================================
# # def ttest_pair(df_A, df_B, metric_names, better_is_higher_for_R2=True):
# #     results = []
# #     for metric in metric_names:
# #         vals_A = df_A[metric].dropna().values
# #         vals_B = df_B[metric].dropna().values
# #         if len(vals_A) == len(vals_B) and len(vals_A) > 1:
# #             t_stat, p_val = ttest_rel(vals_A, vals_B)
# #             if metric == "R2" or metric == "R2_lnP":
# #                 better = "methodB" if np.mean(vals_B) > np.mean(vals_A) else "direct"
# #             else:
# #                 better = "methodB" if np.mean(vals_B) < np.mean(vals_A) else "direct"
# #             results.append({
# #                 "Metric": metric,
# #                 "Mean_direct": f"{np.mean(vals_A):.4f}",
# #                 "Mean_methodB": f"{np.mean(vals_B):.4f}",
# #                 "p-value": f"{p_val:.4e}",
# #                 "Significant(p<0.05)": p_val < 0.05,
# #                 "Better_model": better
# #             })
# #         else:
# #             results.append({
# #                 "Metric": metric,
# #                 "Mean_direct": "NaN",
# #                 "Mean_methodB": "NaN",
# #                 "p-value": "NaN",
# #                 "Significant(p<0.05)": False,
# #                 "Better_model": "insufficient_folds"
# #             })
# #     return pd.DataFrame(results)
# #
# # ttest_P = ttest_pair(df_direct_P, df_methodB_P, metric_names_P, better_is_higher_for_R2=True)
# # ttest_lnP = ttest_pair(df_direct_lnP, df_methodB_lnP, metric_names_lnP, better_is_higher_for_R2=True)
# #
# # print("\n========== Paired t-test (P空间) ==========")
# # print(ttest_P.to_string(index=False))
# # print("\n========== Paired t-test (lnP空间) ==========")
# # print(ttest_lnP.to_string(index=False))
# #
# # # =========================================================
# # # 14. 保存结果到 Excel
# # # =========================================================
# # with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
# #     df_direct_P.to_excel(writer, sheet_name="Fold_Metrics_Direct_P", index=False)
# #     df_methodB_P.to_excel(writer, sheet_name="Fold_Metrics_MethodB_P", index=False)
# #     summary_P.to_excel(writer, sheet_name="Summary_P_Mean_Std", index=False)
# #     ttest_P.to_excel(writer, sheet_name="Paired_T_Test_P", index=False)
# #
# #     df_direct_lnP.to_excel(writer, sheet_name="Fold_Metrics_Direct_lnP", index=False)
# #     df_methodB_lnP.to_excel(writer, sheet_name="Fold_Metrics_MethodB_lnP", index=False)
# #     summary_lnP.to_excel(writer, sheet_name="Summary_lnP_Mean_Std", index=False)
# #     ttest_lnP.to_excel(writer, sheet_name="Paired_T_Test_lnP", index=False)
# #
# #     pd.DataFrame([
# #         {"param": "n_outer_folds", "value": n_outer_folds},
# #         {"param": "random_state", "value": random_state},
# #         {"param": "n_group_features", "value": len(used_group_cols)},
# #         {"param": "total_samples", "value": len(P_true)},
# #         {"param": "n_materials", "value": len(unique_materials)},
# #         {"param": "direct_GBDT_params", "value": str(gbdt_params)},
# #         {"param": "methodB_baseline", "value": "Ridge(alpha=1.0, fit_intercept=False) in P space"},
# #         {"param": "methodB_residual_gbdt", "value": "same as direct GBDT"},
# #         {"param": "anchor_submodel", "value": "HistGradientBoostingRegressor trained on P_anchor"},
# #         {"param": "target", "value": "Vapor Pressure (P, kPa) and ln(P)"},
# #     ]).to_excel(writer, sheet_name="Run_Info", index=False)
# #
# #     from openpyxl import load_workbook
# #     workbook = writer.book
# #     number_format = "0.0000000000"
# #     for sheetname in writer.sheets:
# #         ws = workbook[sheetname]
# #         for row in ws.iter_rows():
# #             for cell in row:
# #                 if isinstance(cell.value, float):
# #                     cell.number_format = number_format
# #         for col in ws.columns:
# #             max_len = 0
# #             col_letter = col[0].column_letter
# #             for cell in col:
# #                 if cell.value:
# #                     max_len = max(max_len, len(str(cell.value)))
# #             ws.column_dimensions[col_letter].width = min(max_len+2, 40)
# #
# # print(f"\n保存完成: {output_file}")
#
# import pandas as pd
# import numpy as np
# from pathlib import Path
#
# from sklearn.ensemble import GradientBoostingRegressor, HistGradientBoostingRegressor
# from sklearn.linear_model import Ridge
# from sklearn.model_selection import KFold
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
# # 0. 全局设置（目标为 lnP，同时评估 P 空间）
# # =========================================================
# input_file = Path("dataset_selected_by_two_k_with_lnP_invT_interpolation_8points.xlsx")
# data_sheet = "Data_selected"
# groups_sheet = "Groups_selected"
# anchor_sheet = "Interpolated_k1_k2"
#
# output_file = Path("lnP_model_comparison_5fold_CV.xlsx")   # 输出文件名可自定义
#
# material_key_col = "material_key"
# temp_col = "T_K"
#
# # 目标列：优先使用 lnP 列，否则从压力列计算
# lnp_candidates = ["lnP_kPa", "lnP", "ln_VaporPressure_kPa", "ln_pressure"]
# pressure_candidates = [
#     "VaporPressure_kPa", "vapor_pressure_kPa",
#     "Vapor_Pressure_kPa", "P_vapor_kPa", "property_value"
# ]
#
# n_group_features_to_use = 220
# use_fixed_group_position = True
# group_start_col_1based = 3
# group_end_col_1based = 222
#
# # 锚点相关列（原始为 lnP 形式，直接使用）
# anchor_lnp_col = "lnP_kPa_interp_at_k1Tb"
# boiling_col = "boiling_T_K"
# k1_col = "k1"
# anchor_T_col = "k1_times_boiling_T_K"
#
# n_outer_folds = 5
# random_state = 42
#
# # 锚点子模型参数（预测 lnP_anchor 和 boiling_T）
# hgb_params = dict(
#     loss="squared_error", max_iter=1200, learning_rate=0.03,
#     max_leaf_nodes=63, min_samples_leaf=2, l2_regularization=0.0,
#     early_stopping=False, random_state=random_state
# )
#
# # 通用 GBDT 参数（直接 GBDT 和残差 GBDT）
# gbdt_params = {
#     "n_estimators": 500,
#     "learning_rate": 0.03,
#     "max_depth": 3,
#     "min_samples_split": 10,
#     "min_samples_leaf": 5,
#     "subsample": 0.9,
#     "random_state": random_state
# }
#
# # =========================================================
# # 1. 读取数据
# # =========================================================
# df_data = pd.read_excel(input_file, sheet_name=data_sheet)
# df_groups_raw = pd.read_excel(input_file, sheet_name=groups_sheet)
# df_anchor = pd.read_excel(input_file, sheet_name=anchor_sheet)
#
# print("Data_selected 行数:", len(df_data))
# print("Groups_selected 物质数:", len(df_groups_raw))
# print("Interpolated_k1_k2 物质数:", len(df_anchor))
#
# # =========================================================
# # 2. 准备 material_key
# # =========================================================
# def is_valid_value(x):
#     if pd.isna(x): return False
#     s = str(x).strip()
#     if s == "" or s.lower() in ["nan","none","null","待定"]: return False
#     return True
#
# def build_material_key(row):
#     for col in ["material_key","inchikey","cas","compound_name","formula"]:
#         if col in row.index and is_valid_value(row[col]):
#             if col == "material_key":
#                 return str(row[col]).strip()
#             return f"{col}:{str(row[col]).strip()}"
#     return "unknown_material"
#
# for df in [df_data, df_groups_raw, df_anchor]:
#     if material_key_col not in df.columns:
#         df[material_key_col] = df.apply(build_material_key, axis=1)
#     df[material_key_col] = df[material_key_col].astype(str).str.strip()
#
# # =========================================================
# # 3. 找到目标列（lnP）
# # =========================================================
# def find_first_existing_col(df, candidates, col_type):
#     for col in candidates:
#         if col in df.columns:
#             return col
#     raise ValueError(f"没有找到 {col_type} 列。候选: {candidates}")
#
# def find_lnp_column(df):
#     # 优先 lnP 列
#     for col in lnp_candidates:
#         if col in df.columns:
#             return col, "lnP"
#     # 否则从压力列计算 lnP
#     for col in pressure_candidates:
#         if col in df.columns:
#             return col, "pressure"
#     raise ValueError("未找到 lnP 或蒸汽压列")
#
# target_col, target_type = find_lnp_column(df_data)
# print("目标列:", target_col, "类型:", target_type)
#
# # 确保 df_data 中有 lnP 列（如果只有压力，则计算 lnP）
# if target_type == "pressure":
#     df_data["lnP_calculated"] = np.log(df_data[target_col])
#     target_col = "lnP_calculated"
#     print("已从压力列计算 lnP 作为目标")
# else:
#     # 已经是 lnP，直接使用
#     pass
#
# # 温度列检查
# if temp_col not in df_data.columns:
#     raise ValueError(f"Data_selected 中没有找到温度列: {temp_col}")
#
# # 锚点列（原始就是 lnP，无需转换）
# if anchor_lnp_col not in df_anchor.columns:
#     raise ValueError(f"锚点表中没有找到 {anchor_lnp_col}，无法获得 lnP_anchor")
# anchor_lnp_col_used = anchor_lnp_col
# print("使用锚点 lnP 列:", anchor_lnp_col_used)
#
# # =========================================================
# # 4. 识别基团列
# # =========================================================
# def identify_group_columns(df_groups, n=220):
#     if use_fixed_group_position:
#         start_idx = group_start_col_1based - 1
#         end_excl = group_end_col_1based
#         if len(df_groups.columns) < end_excl:
#             raise ValueError(f"基团列数不足，需要到第 {group_end_col_1based} 列")
#         group_cols = list(df_groups.columns[start_idx:end_excl])
#         if len(group_cols) != n:
#             raise ValueError(f"固定列位置识别到 {len(group_cols)} 个基团，需要 {n}")
#         return group_cols
#     else:
#         metadata_keywords = ["original_material_index","material_key","compound","name","cas","formula","smiles","inchi","inchikey","pubchem","phase","property","boiling","temperature","temp","t_k","pressure","lnp","vapor","k1","k2","interp","status","range"]
#         candidate_cols = []
#         for col in df_groups.columns:
#             if any(k in col.lower() for k in metadata_keywords):
#                 continue
#             if pd.to_numeric(df_groups[col], errors="coerce").notna().sum() > 0:
#                 candidate_cols.append(col)
#         if len(candidate_cols) < n:
#             raise ValueError(f"自动识别基团仅 {len(candidate_cols)} 个，少于 {n}")
#         return candidate_cols[:n]
#
# group_cols_220 = identify_group_columns(df_groups_raw, n_group_features_to_use)
# df_groups_numeric = df_groups_raw[group_cols_220].apply(pd.to_numeric, errors="coerce").fillna(0.0)
# nonzero_mask = df_groups_numeric.abs().sum(axis=0) != 0
# used_group_cols = df_groups_numeric.columns[nonzero_mask].tolist()
# df_groups_used = df_groups_numeric[used_group_cols].copy()
# print("有效基团数量:", len(used_group_cols))
#
# # =========================================================
# # 5. 准备锚点数据（每个物质一个，全数据）
# # =========================================================
# anchor_keep = [material_key_col, anchor_lnp_col_used, boiling_col]
# if k1_col in df_anchor.columns:
#     anchor_keep.append(k1_col)
# if anchor_T_col in df_anchor.columns:
#     anchor_keep.append(anchor_T_col)
# df_anchor_slim = df_anchor[anchor_keep].drop_duplicates(subset=[material_key_col])
# df_anchor_slim[anchor_lnp_col_used] = pd.to_numeric(df_anchor_slim[anchor_lnp_col_used], errors="coerce")
# df_anchor_slim[boiling_col] = pd.to_numeric(df_anchor_slim[boiling_col], errors="coerce")
# if k1_col in df_anchor_slim.columns:
#     df_anchor_slim["k1_valid"] = pd.to_numeric(df_anchor_slim[k1_col], errors="coerce")
# else:
#     df_anchor_slim["k1_valid"] = df_anchor_slim[anchor_T_col] / df_anchor_slim[boiling_col]
# k1_median = df_anchor_slim["k1_valid"].replace([np.inf, -np.inf], np.nan).median()
# df_anchor_slim["k1_valid"] = df_anchor_slim["k1_valid"].fillna(k1_median)
#
# valid_anchor = (df_anchor_slim[anchor_lnp_col_used].notna() &
#                 df_anchor_slim[boiling_col].notna() &
#                 (df_anchor_slim[boiling_col] > 0) &
#                 np.isfinite(df_anchor_slim["k1_valid"]))
# df_anchor_valid = df_anchor_slim[valid_anchor].copy()
# print("有效锚点物质数:", len(df_anchor_valid))
#
# # =========================================================
# # 6. 全数据训练锚点子模型（预测 lnP_anchor 和 boiling_T）
# # =========================================================
# df_material = df_groups_used.reset_index().rename(columns={"index": "orig_idx"})
# df_material[material_key_col] = df_groups_raw.loc[df_material.index, material_key_col].values
# df_material = df_material.merge(df_anchor_valid, on=material_key_col, how="inner")
# df_material = df_material.dropna(subset=used_group_cols + [anchor_lnp_col_used, boiling_col, "k1_valid"])
# df_material = df_material.reset_index(drop=True)
# print("合并后物质数:", len(df_material))
#
# X_anchor = df_material[used_group_cols].values.astype(float)
# y_lnP_anchor = df_material[anchor_lnp_col_used].values.astype(float)
# y_boiling = df_material[boiling_col].values.astype(float)
#
# anchor_lnP_model = HistGradientBoostingRegressor(**hgb_params)
# anchor_boiling_model = HistGradientBoostingRegressor(**hgb_params)
# anchor_lnP_model.fit(X_anchor, y_lnP_anchor)
# anchor_boiling_model.fit(X_anchor, y_boiling)
#
# df_material["lnP_anchor_pred"] = anchor_lnP_model.predict(X_anchor)
# df_material["boiling_T_pred"] = anchor_boiling_model.predict(X_anchor)
# df_material["anchor_T_pred"] = df_material["k1_valid"] * df_material["boiling_T_pred"]
# df_material["invT_anchor_pred"] = 1.0 / df_material["anchor_T_pred"]
#
# # =========================================================
# # 7. 展开温度点数据
# # =========================================================
# df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
# df_data[target_col] = pd.to_numeric(df_data[target_col], errors="coerce")
# df_data["InvT"] = 1.0 / df_data[temp_col]
#
# df_long = df_data.merge(
#     df_material[[material_key_col] + used_group_cols +
#                 ["lnP_anchor_pred", "invT_anchor_pred"]],
#     on=material_key_col, how="inner"
# )
# df_long = df_long.dropna(subset=[target_col, temp_col, "InvT"] + used_group_cols +
#                          ["lnP_anchor_pred", "invT_anchor_pred"])
# df_long = df_long.reset_index(drop=True)
# print("最终温度点总数:", len(df_long))
#
# X_groups = df_long[used_group_cols].values.astype(float)
# invT_all = df_long["InvT"].values.astype(float)
# lnP_true = df_long[target_col].values.astype(float)          # 真实 lnP
# lnP_anchor_pred = df_long["lnP_anchor_pred"].values.astype(float)
# invT_anchor_pred = df_long["invT_anchor_pred"].values.astype(float)
# material_keys = df_long[material_key_col].values
#
# unique_materials = np.unique(material_keys)
#
# # =========================================================
# # 8. 辅助函数：构建直接GBDT特征 ([groups, InvT])
# # =========================================================
# def build_direct_features(sample_mask):
#     return np.hstack([X_groups[sample_mask], invT_all[sample_mask].reshape(-1, 1)])
#
# # =========================================================
# # 9. 方法B：基于锚点的基线+残差GBDT（均在 lnP 空间）
# # =========================================================
# def train_and_predict_methodB(train_mask, test_mask):
#     df_train = df_long[train_mask].copy()
#     df_test = df_long[test_mask].copy()
#
#     # 基线模型：lnP_base = lnP_anchor + (InvT - InvT_anchor) * Σ Nk Ak
#     delta_invT_train = df_train["InvT"].values - df_train["invT_anchor_pred"].values
#     X_base_train = df_train[used_group_cols].values * delta_invT_train.reshape(-1, 1)
#     y_base_train = df_train[target_col].values - df_train["lnP_anchor_pred"].values   # lnP残差目标
#
#     valid_base = np.isfinite(X_base_train).all(axis=1) & np.isfinite(y_base_train)
#     if valid_base.sum() == 0:
#         raise ValueError("基线模型无有效训练样本")
#     base_model = Ridge(alpha=1.0, fit_intercept=False)
#     base_model.fit(X_base_train[valid_base], y_base_train[valid_base])
#
#     # 测试集基线预测
#     delta_invT_test = df_test["InvT"].values - df_test["invT_anchor_pred"].values
#     X_base_test = df_test[used_group_cols].values * delta_invT_test.reshape(-1, 1)
#     valid_base_test = np.isfinite(X_base_test).all(axis=1)
#     baseline_delta = np.full(len(df_test), np.nan)
#     baseline_delta[valid_base_test] = base_model.predict(X_base_test[valid_base_test])
#     baseline_lnP = df_test["lnP_anchor_pred"].values + baseline_delta
#
#     # 残差模型训练
#     # 使用训练集基线预测
#     delta_invT_train2 = df_train["InvT"].values - df_train["invT_anchor_pred"].values
#     X_base_train2 = df_train[used_group_cols].values * delta_invT_train2.reshape(-1, 1)
#     baseline_delta_train = base_model.predict(X_base_train2)
#     baseline_lnP_train = df_train["lnP_anchor_pred"].values + baseline_delta_train
#     residual_y_train = df_train[target_col].values - baseline_lnP_train
#
#     residual_X_train = np.hstack([df_train[used_group_cols].values,
#                                   df_train["InvT"].values.reshape(-1, 1)])
#     valid_res = np.isfinite(residual_X_train).all(axis=1) & np.isfinite(residual_y_train)
#     if valid_res.sum() == 0:
#         raise ValueError("残差模型无有效训练样本")
#     res_model = GradientBoostingRegressor(**gbdt_params)
#     res_model.fit(residual_X_train[valid_res], residual_y_train[valid_res])
#
#     # 测试集残差预测
#     residual_X_test = np.hstack([df_test[used_group_cols].values,
#                                  df_test["InvT"].values.reshape(-1, 1)])
#     valid_res_test = np.isfinite(residual_X_test).all(axis=1)
#     residual_pred = np.full(len(df_test), np.nan)
#     residual_pred[valid_res_test] = res_model.predict(residual_X_test[valid_res_test])
#
#     final_lnP = baseline_lnP + residual_pred
#     return final_lnP
#
# # =========================================================
# # 10. 评价函数：lnP 空间 + P 空间（通过 exp 转换）
# # =========================================================
# def compute_metrics_lnP(y_true_lnP, y_pred_lnP):
#     mask = np.isfinite(y_true_lnP) & np.isfinite(y_pred_lnP)
#     y_true = y_true_lnP[mask]
#     y_pred = y_pred_lnP[mask]
#     if len(y_true) == 0:
#         return {k: np.nan for k in ["R2_lnP", "MSE_lnP", "RMSE_lnP", "MAE_lnP", "ARD_lnP_percent"]}
#     r2 = r2_score(y_true, y_pred)
#     mse = mean_squared_error(y_true, y_pred)
#     rmse = np.sqrt(mse)
#     mae = mean_absolute_error(y_true, y_pred)
#     # 相对误差（在 lnP 空间）：|ΔlnP| / |lnP|
#     denom = np.abs(y_true)
#     denom_mask = denom > 1e-12
#     if denom_mask.sum() > 0:
#         ard = np.mean(np.abs((y_pred[denom_mask] - y_true[denom_mask]) / denom[denom_mask])) * 100
#     else:
#         ard = np.nan
#     return {"R2_lnP": r2, "MSE_lnP": mse, "RMSE_lnP": rmse,
#             "MAE_lnP": mae, "ARD_lnP_percent": ard}
#
# def compute_metrics_P_from_lnP(y_true_lnP, y_pred_lnP):
#     # 转换为压力空间
#     eps = 1e-12
#     y_true_P = np.exp(np.clip(y_true_lnP, -700, 700))
#     y_pred_P = np.exp(np.clip(y_pred_lnP, -700, 700))
#     mask = np.isfinite(y_true_P) & np.isfinite(y_pred_P) & (y_true_P > 0)
#     y_true = y_true_P[mask]
#     y_pred = y_pred_P[mask]
#     if len(y_true) == 0:
#         return {k: np.nan for k in ["R2_P", "MSE_P", "RMSE_P", "MAE_P",
#                                     "ARD_P_percent", "leq1%_P", "leq5%_P", "leq10%_P", "max_rel%_P"]}
#     r2 = r2_score(y_true, y_pred)
#     mse = mean_squared_error(y_true, y_pred)
#     rmse = np.sqrt(mse)
#     mae = mean_absolute_error(y_true, y_pred)
#
#     valid = y_true > 1e-12
#     if valid.sum() > 0:
#         rel_err = np.abs((y_pred[valid] - y_true[valid]) / y_true[valid]) * 100
#         ard = np.mean(rel_err)
#         max_rel = np.max(rel_err)
#         le1 = np.mean(rel_err <= 1) * 100
#         le5 = np.mean(rel_err <= 5) * 100
#         le10 = np.mean(rel_err <= 10) * 100
#     else:
#         ard = max_rel = le1 = le5 = le10 = np.nan
#     return {"R2_P": r2, "MSE_P": mse, "RMSE_P": rmse, "MAE_P": mae,
#             "ARD_P_percent": ard, "max_rel%_P": max_rel,
#             "leq1%_P": le1, "leq5%_P": le5, "leq10%_P": le10}
#
# # =========================================================
# # 11. 5折交叉验证（按物质划分）
# # =========================================================
# kf = KFold(n_splits=n_outer_folds, shuffle=True, random_state=random_state)
# metrics_direct_lnP = []    # 直接 GBDT 的 lnP 指标
# metrics_direct_P = []      # 直接 GBDT 的 P 指标
# metrics_methodB_lnP = []   # 方法B 的 lnP 指标
# metrics_methodB_P = []     # 方法B 的 P 指标
#
# for fold, (train_idx, test_idx) in enumerate(kf.split(unique_materials)):
#     print(f"\n========== Fold {fold+1}/{n_outer_folds} ==========")
#     train_materials = unique_materials[train_idx]
#     test_materials = unique_materials[test_idx]
#
#     train_mask = np.isin(material_keys, train_materials)
#     test_mask = np.isin(material_keys, test_materials)
#
#     # ---------- 方法A：直接GBDT（预测 lnP）----------
#     X_train_A = build_direct_features(train_mask)
#     y_train_A = lnP_true[train_mask]
#     valid_A = np.isfinite(X_train_A).all(axis=1) & np.isfinite(y_train_A)
#     X_train_A = X_train_A[valid_A]
#     y_train_A = y_train_A[valid_A]
#     model_A = GradientBoostingRegressor(**gbdt_params)
#     model_A.fit(X_train_A, y_train_A)
#
#     X_test_A = build_direct_features(test_mask)
#     y_test_A_lnP = lnP_true[test_mask]
#     valid_test_A = np.isfinite(X_test_A).all(axis=1)
#     y_pred_A_lnP = np.full(len(y_test_A_lnP), np.nan)
#     y_pred_A_lnP[valid_test_A] = model_A.predict(X_test_A[valid_test_A])
#
#     # ---------- 方法B：锚点线性基线 + 残差GBDT（预测 lnP）----------
#     try:
#         y_pred_B_lnP = train_and_predict_methodB(train_mask, test_mask)
#     except Exception as e:
#         print(f"  Fold {fold+1} 方法B失败: {e}")
#         y_pred_B_lnP = np.full(len(y_test_A_lnP), np.nan)
#
#     # 计算 lnP 空间指标
#     m_lnP_A = compute_metrics_lnP(y_test_A_lnP, y_pred_A_lnP)
#     m_lnP_B = compute_metrics_lnP(y_test_A_lnP, y_pred_B_lnP)
#     m_lnP_A["fold"] = fold+1
#     m_lnP_B["fold"] = fold+1
#     metrics_direct_lnP.append(m_lnP_A)
#     metrics_methodB_lnP.append(m_lnP_B)
#
#     # 计算 P 空间指标（通过 exp 转换）
#     m_P_A = compute_metrics_P_from_lnP(y_test_A_lnP, y_pred_A_lnP)
#     m_P_B = compute_metrics_P_from_lnP(y_test_A_lnP, y_pred_B_lnP)
#     m_P_A["fold"] = fold+1
#     m_P_B["fold"] = fold+1
#     metrics_direct_P.append(m_P_A)
#     metrics_methodB_P.append(m_P_B)
#
# # =========================================================
# # 12. 汇总统计
# # =========================================================
# df_direct_lnP = pd.DataFrame(metrics_direct_lnP)
# df_methodB_lnP = pd.DataFrame(metrics_methodB_lnP)
# df_direct_P = pd.DataFrame(metrics_direct_P)
# df_methodB_P = pd.DataFrame(metrics_methodB_P)
#
# def summarize(df, name, metric_names):
#     rows = []
#     for metric in metric_names:
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
# metric_names_lnP = [c for c in df_direct_lnP.columns if c != "fold"]
# metric_names_P   = [c for c in df_direct_P.columns   if c != "fold"]
#
# summary_lnP_direct = summarize(df_direct_lnP, "GBDT_direct (lnP)", metric_names_lnP)
# summary_lnP_methodB = summarize(df_methodB_lnP, "Anchor+linear+GBDT_residual (lnP)", metric_names_lnP)
# summary_lnP = pd.concat([summary_lnP_direct, summary_lnP_methodB], ignore_index=True)
#
# summary_P_direct = summarize(df_direct_P, "GBDT_direct (P via exp)", metric_names_P)
# summary_P_methodB = summarize(df_methodB_P, "Anchor+linear+GBDT_residual (P via exp)", metric_names_P)
# summary_P = pd.concat([summary_P_direct, summary_P_methodB], ignore_index=True)
#
# print("\n========== lnP 空间 5-Fold CV Summary ==========")
# print(summary_lnP.to_string(index=False))
# print("\n========== P 空间 (exp) 5-Fold CV Summary ==========")
# print(summary_P.to_string(index=False))
#
# # =========================================================
# # 13. 配对 t 检验
# # =========================================================
# def ttest_pair(df_A, df_B, metric_names, higher_is_better_metrics):
#     results = []
#     for metric in metric_names:
#         vals_A = df_A[metric].dropna().values
#         vals_B = df_B[metric].dropna().values
#         if len(vals_A) == len(vals_B) and len(vals_A) > 1:
#             t_stat, p_val = ttest_rel(vals_A, vals_B)
#             if metric in higher_is_better_metrics:
#                 better = "methodB" if np.mean(vals_B) > np.mean(vals_A) else "direct"
#             else:
#                 better = "methodB" if np.mean(vals_B) < np.mean(vals_A) else "direct"
#             results.append({
#                 "Metric": metric,
#                 "Mean_direct": f"{np.mean(vals_A):.4f}",
#                 "Mean_methodB": f"{np.mean(vals_B):.4f}",
#                 "p-value": f"{p_val:.4e}",
#                 "Significant(p<0.05)": p_val < 0.05,
#                 "Better_model": better
#             })
#         else:
#             results.append({
#                 "Metric": metric,
#                 "Mean_direct": "NaN",
#                 "Mean_methodB": "NaN",
#                 "p-value": "NaN",
#                 "Significant(p<0.05)": False,
#                 "Better_model": "insufficient_folds"
#             })
#     return pd.DataFrame(results)
#
# higher_is_better = ["R2_lnP", "R2_P"]
# ttest_lnP = ttest_pair(df_direct_lnP, df_methodB_lnP, metric_names_lnP, higher_is_better)
# ttest_P   = ttest_pair(df_direct_P,   df_methodB_P,   metric_names_P,   higher_is_better)
#
# print("\n========== Paired t-test (lnP空间) ==========")
# print(ttest_lnP.to_string(index=False))
# print("\n========== Paired t-test (P空间) ==========")
# print(ttest_P.to_string(index=False))
#
# # =========================================================
# # 14. 保存结果到 Excel
# # =========================================================
# with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
#     # lnP 空间指标
#     df_direct_lnP.to_excel(writer, sheet_name="Fold_Metrics_Direct_lnP", index=False)
#     df_methodB_lnP.to_excel(writer, sheet_name="Fold_Metrics_MethodB_lnP", index=False)
#     summary_lnP.to_excel(writer, sheet_name="Summary_lnP_Mean_Std", index=False)
#     ttest_lnP.to_excel(writer, sheet_name="Paired_T_Test_lnP", index=False)
#
#     # P 空间指标
#     df_direct_P.to_excel(writer, sheet_name="Fold_Metrics_Direct_P", index=False)
#     df_methodB_P.to_excel(writer, sheet_name="Fold_Metrics_MethodB_P", index=False)
#     summary_P.to_excel(writer, sheet_name="Summary_P_Mean_Std", index=False)
#     ttest_P.to_excel(writer, sheet_name="Paired_T_Test_P", index=False)
#
#     # 运行信息
#     pd.DataFrame([
#         {"param": "n_outer_folds", "value": n_outer_folds},
#         {"param": "random_state", "value": random_state},
#         {"param": "n_group_features", "value": len(used_group_cols)},
#         {"param": "total_samples", "value": len(lnP_true)},
#         {"param": "n_materials", "value": len(unique_materials)},
#         {"param": "direct_GBDT_params", "value": str(gbdt_params)},
#         {"param": "methodB_baseline", "value": "Ridge(alpha=1.0, fit_intercept=False) in lnP space"},
#         {"param": "methodB_residual_gbdt", "value": "same as direct GBDT"},
#         {"param": "anchor_submodel", "value": "HistGradientBoostingRegressor trained on lnP_anchor"},
#         {"param": "target", "value": "lnP (natural log of vapor pressure in kPa)"},
#     ]).to_excel(writer, sheet_name="Run_Info", index=False)
#
#     # 格式化
#     from openpyxl import load_workbook
#     workbook = writer.book
#     number_format = "0.0000000000"
#     for sheetname in writer.sheets:
#         ws = workbook[sheetname]
#         for row in ws.iter_rows():
#             for cell in row:
#                 if isinstance(cell.value, float):
#                     cell.number_format = number_format
#         for col in ws.columns:
#             max_len = 0
#             col_letter = col[0].column_letter
#             for cell in col:
#                 if cell.value:
#                     max_len = max(max_len, len(str(cell.value)))
#             ws.column_dimensions[col_letter].width = min(max_len + 2, 40)
#
# print(f"\n保存完成: {output_file}")


import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.ensemble import GradientBoostingRegressor, HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from scipy.stats import ttest_rel

import warnings
warnings.filterwarnings("ignore")

pd.set_option("display.float_format", "{:.10f}".format)
np.set_printoptions(suppress=True, precision=10)


# =========================================================
# 0. 全局设置（目标为 lnP，同时评估 P 空间）
# =========================================================
input_file = Path("dataset_selected_by_two_k_with_lnP_invT_interpolation_8points.xlsx")

data_sheet = "Data_selected"
groups_sheet = "Groups_selected"
anchor_sheet = "Interpolated_k1_k2"

output_file = Path("lnP_model_comparison_5fold_CV.xlsx")

material_key_col = "material_key"
temp_col = "T_K"

# 目标列：优先使用 lnP 列，否则从压力列计算
lnp_candidates = [
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

n_group_features_to_use = 220
use_fixed_group_position = True
group_start_col_1based = 3
group_end_col_1based = 222

# 锚点相关列（原始为 lnP 形式，直接使用）
anchor_lnp_col = "lnP_kPa_interp_at_k1Tb"
boiling_col = "boiling_T_K"
k1_col = "k1"
anchor_T_col = "k1_times_boiling_T_K"

n_outer_folds = 5
random_state = 42

# 锚点子模型参数（预测 lnP_anchor 和 boiling_T）
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

# 通用 GBDT 参数（直接 GBDT 和残差 GBDT）
gbdt_params = {
    "n_estimators": 500,
    "learning_rate": 0.03,
    "max_depth": 3,
    "min_samples_split": 10,
    "min_samples_leaf": 5,
    "subsample": 0.9,
    "random_state": random_state,
}

baseline_ridge_alpha = 1.0


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


def find_first_existing_col(df, candidates, col_type):
    for col in candidates:
        if col in df.columns:
            return col
    raise ValueError(f"没有找到 {col_type} 列。候选: {candidates}")


def find_lnp_column(df):
    for col in lnp_candidates:
        if col in df.columns:
            return col, "lnP"

    for col in pressure_candidates:
        if col in df.columns:
            return col, "pressure"

    raise ValueError("未找到 lnP 或蒸汽压列")


def identify_group_columns(df_groups, n=220):
    if use_fixed_group_position:
        start_idx = group_start_col_1based - 1
        end_excl = group_end_col_1based

        if len(df_groups.columns) < end_excl:
            raise ValueError(f"基团列数不足，需要到第 {group_end_col_1based} 列")

        group_cols = list(df_groups.columns[start_idx:end_excl])

        if len(group_cols) != n:
            raise ValueError(f"固定列位置识别到 {len(group_cols)} 个基团，需要 {n}")

        return group_cols

    metadata_keywords = [
        "original_material_index", "material_key", "compound", "name", "cas",
        "formula", "smiles", "inchi", "inchikey", "pubchem", "phase",
        "property", "boiling", "temperature", "temp", "t_k", "pressure",
        "lnp", "vapor", "k1", "k2", "interp", "status", "range",
    ]

    candidate_cols = []
    for col in df_groups.columns:
        col_lower = str(col).lower()
        if any(k in col_lower for k in metadata_keywords):
            continue
        if pd.to_numeric(df_groups[col], errors="coerce").notna().sum() > 0:
            candidate_cols.append(col)

    if len(candidate_cols) < n:
        raise ValueError(f"自动识别基团仅 {len(candidate_cols)} 个，少于 {n}")

    return candidate_cols[:n]


def safe_exp(x):
    return np.exp(np.clip(np.asarray(x, dtype=float), -700, 700))


def safe_log(x):
    x = np.asarray(x, dtype=float)
    return np.log(np.clip(x, 1e-300, None))


def safe_relative_error_percent(y_true, y_pred, eps=1e-12):
    """
    relative_error = abs((y_pred - y_true) / y_true) * 100
    abs(y_true) <= 1e-12 的点记为 NaN。
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
    """
    rel_err = safe_relative_error_percent(y_true, y_pred)

    return {
        "count_rel_err_lt_1pct": float(np.nansum(rel_err < 1.0)),
        "count_rel_err_lt_5pct": float(np.nansum(rel_err < 5.0)),
        "count_rel_err_lt_10pct": float(np.nansum(rel_err < 10.0)),
        "n_valid_for_relative_error": int(np.sum(np.isfinite(rel_err))),
    }


def average_relative_deviation(y_true, y_pred):
    rel_err = safe_relative_error_percent(y_true, y_pred)
    if np.any(np.isfinite(rel_err)):
        return float(np.nanmean(rel_err))
    return np.nan


def compute_metrics_lnP(y_true_lnP, y_pred_lnP):
    y_true_lnP = np.asarray(y_true_lnP, dtype=float)
    y_pred_lnP = np.asarray(y_pred_lnP, dtype=float)

    mask = np.isfinite(y_true_lnP) & np.isfinite(y_pred_lnP)
    y_true_lnP = y_true_lnP[mask]
    y_pred_lnP = y_pred_lnP[mask]

    if len(y_true_lnP) == 0:
        return {
            "R2_lnP": np.nan,
            "MSE_lnP": np.nan,
            "RMSE_lnP": np.nan,
            "MAE_lnP": np.nan,
            "ARD_lnP_percent": np.nan,
            "max_rel_err_lnP_percent": np.nan,
            "lt1_lnP_ratio_percent": np.nan,
            "lt5_lnP_ratio_percent": np.nan,
            "lt10_lnP_ratio_percent": np.nan,
            "lt1_lnP_count": 0.0,
            "lt5_lnP_count": 0.0,
            "lt10_lnP_count": 0.0,
        }

    mse = mean_squared_error(y_true_lnP, y_pred_lnP)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_true_lnP, y_pred_lnP)
    r2 = r2_score(y_true_lnP, y_pred_lnP) if len(y_true_lnP) > 1 else np.nan

    rel_err = safe_relative_error_percent(y_true_lnP, y_pred_lnP)
    n_valid = int(np.sum(np.isfinite(rel_err)))

    if n_valid > 0:
        c1 = float(np.nansum(rel_err < 1.0))
        c5 = float(np.nansum(rel_err < 5.0))
        c10 = float(np.nansum(rel_err < 10.0))
        ard = float(np.nanmean(rel_err))
        max_rel = float(np.nanmax(rel_err))
        r1 = c1 / n_valid * 100.0
        r5 = c5 / n_valid * 100.0
        r10 = c10 / n_valid * 100.0
    else:
        c1 = c5 = c10 = 0.0
        ard = max_rel = r1 = r5 = r10 = np.nan

    return {
        "R2_lnP": r2,
        "MSE_lnP": mse,
        "RMSE_lnP": rmse,
        "MAE_lnP": mae,
        "ARD_lnP_percent": ard,
        "max_rel_err_lnP_percent": max_rel,
        "lt1_lnP_ratio_percent": r1,
        "lt5_lnP_ratio_percent": r5,
        "lt10_lnP_ratio_percent": r10,
        "lt1_lnP_count": c1,
        "lt5_lnP_count": c5,
        "lt10_lnP_count": c10,
    }


def compute_metrics_P_from_lnP(y_true_lnP, y_pred_lnP):
    y_true_P = safe_exp(y_true_lnP)
    y_pred_P = safe_exp(y_pred_lnP)

    mask = np.isfinite(y_true_P) & np.isfinite(y_pred_P)
    y_true_P = y_true_P[mask]
    y_pred_P = y_pred_P[mask]

    if len(y_true_P) == 0:
        return {
            "R2_P": np.nan,
            "MSE_P": np.nan,
            "RMSE_P": np.nan,
            "MAE_P": np.nan,
            "ARD_P_percent": np.nan,
            "max_rel_err_P_percent": np.nan,
            "lt1_P_ratio_percent": np.nan,
            "lt5_P_ratio_percent": np.nan,
            "lt10_P_ratio_percent": np.nan,
            "lt1_P_count": 0.0,
            "lt5_P_count": 0.0,
            "lt10_P_count": 0.0,
        }

    mse = mean_squared_error(y_true_P, y_pred_P)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_true_P, y_pred_P)
    r2 = r2_score(y_true_P, y_pred_P) if len(y_true_P) > 1 else np.nan

    rel_err = safe_relative_error_percent(y_true_P, y_pred_P)
    n_valid = int(np.sum(np.isfinite(rel_err)))

    if n_valid > 0:
        c1 = float(np.nansum(rel_err < 1.0))
        c5 = float(np.nansum(rel_err < 5.0))
        c10 = float(np.nansum(rel_err < 10.0))
        ard = float(np.nanmean(rel_err))
        max_rel = float(np.nanmax(rel_err))
        r1 = c1 / n_valid * 100.0
        r5 = c5 / n_valid * 100.0
        r10 = c10 / n_valid * 100.0
    else:
        c1 = c5 = c10 = 0.0
        ard = max_rel = r1 = r5 = r10 = np.nan

    return {
        "R2_P": r2,
        "MSE_P": mse,
        "RMSE_P": rmse,
        "MAE_P": mae,
        "ARD_P_percent": ard,
        "max_rel_err_P_percent": max_rel,
        "lt1_P_ratio_percent": r1,
        "lt5_P_ratio_percent": r5,
        "lt10_P_ratio_percent": r10,
        "lt1_P_count": c1,
        "lt5_P_count": c5,
        "lt10_P_count": c10,
    }


def compute_metrics_target_space(y_true, y_pred, prefix):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true = y_true[mask]
    y_pred = y_pred[mask]

    if len(y_true) == 0:
        return {
            f"R2_{prefix}": np.nan,
            f"MSE_{prefix}": np.nan,
            f"RMSE_{prefix}": np.nan,
            f"MAE_{prefix}": np.nan,
            f"ARD_{prefix}_percent": np.nan,
        }

    mse = mean_squared_error(y_true, y_pred)
    return {
        f"R2_{prefix}": r2_score(y_true, y_pred) if len(y_true) > 1 else np.nan,
        f"MSE_{prefix}": mse,
        f"RMSE_{prefix}": np.sqrt(mse),
        f"MAE_{prefix}": mean_absolute_error(y_true, y_pred),
        f"ARD_{prefix}_percent": average_relative_deviation(y_true, y_pred),
    }


def summarize(df, name, metric_names):
    rows = []

    for metric in metric_names:
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


def paired_ttest(df_A, df_B, metric_names, model_A_name, model_B_name):
    results = []

    for metric in metric_names:
        vals_A = df_A[metric].values.astype(float)
        vals_B = df_B[metric].values.astype(float)

        valid = np.isfinite(vals_A) & np.isfinite(vals_B)

        vals_A = vals_A[valid]
        vals_B = vals_B[valid]

        if len(vals_A) > 1:
            t_stat, p_val = ttest_rel(vals_A, vals_B)

            if "R2" in metric:
                better = model_B_name if np.mean(vals_B) > np.mean(vals_A) else model_A_name
            else:
                better = model_B_name if np.mean(vals_B) < np.mean(vals_A) else model_A_name

            results.append({
                "Metric": metric,
                f"Mean_{model_A_name}": np.mean(vals_A),
                f"Mean_{model_B_name}": np.mean(vals_B),
                "t_stat": t_stat,
                "p_value": p_val,
                "Significant_p_lt_0.05": p_val < 0.05,
                "Better_model": better,
                "n_valid_fold_pairs": len(vals_A),
            })
        else:
            results.append({
                "Metric": metric,
                f"Mean_{model_A_name}": np.nan,
                f"Mean_{model_B_name}": np.nan,
                "t_stat": np.nan,
                "p_value": np.nan,
                "Significant_p_lt_0.05": False,
                "Better_model": "insufficient_valid_folds",
                "n_valid_fold_pairs": len(vals_A),
            })

    return pd.DataFrame(results)


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

print("Data_selected 行数:", len(df_data))
print("Groups_selected 物质数:", len(df_groups_raw))
print("Interpolated_k1_k2 物质数:", len(df_anchor))


# =========================================================
# 3. 准备 material_key
# =========================================================
for df in [df_data, df_groups_raw, df_anchor]:
    if material_key_col not in df.columns:
        df[material_key_col] = df.apply(build_material_key, axis=1)

    df[material_key_col] = df[material_key_col].astype(str).str.strip()


# =========================================================
# 4. 找到目标列（lnP）
# =========================================================
target_col, target_type = find_lnp_column(df_data)

print("目标列:", target_col, "类型:", target_type)

if target_type == "pressure":
    df_data[target_col] = pd.to_numeric(df_data[target_col], errors="coerce")
    df_data["lnP_calculated"] = safe_log(df_data[target_col].values)
    target_col = "lnP_calculated"
    print("已从压力列计算 lnP 作为目标")

if temp_col not in df_data.columns:
    raise ValueError(f"Data_selected 中没有找到温度列: {temp_col}")

if anchor_lnp_col not in df_anchor.columns:
    raise ValueError(f"锚点表中没有找到 {anchor_lnp_col}，无法获得 lnP_anchor")

anchor_lnp_col_used = anchor_lnp_col

print("使用锚点 lnP 列:", anchor_lnp_col_used)


# =========================================================
# 5. 识别基团列
# =========================================================
group_cols_220 = identify_group_columns(df_groups_raw, n_group_features_to_use)

df_groups_numeric = (
    df_groups_raw[group_cols_220]
    .apply(pd.to_numeric, errors="coerce")
    .fillna(0.0)
)

nonzero_mask = df_groups_numeric.abs().sum(axis=0) != 0

used_group_cols = df_groups_numeric.columns[nonzero_mask].tolist()
removed_zero_group_cols = df_groups_numeric.columns[~nonzero_mask].tolist()

df_groups_used = df_groups_numeric[used_group_cols].copy()

print("有效基团数量:", len(used_group_cols))
print("删除全零基团数量:", len(removed_zero_group_cols))


# =========================================================
# 6. 准备锚点数据（每个物质一个，全数据）
# =========================================================
anchor_keep = [material_key_col, anchor_lnp_col_used, boiling_col]

if k1_col in df_anchor.columns:
    anchor_keep.append(k1_col)

if anchor_T_col in df_anchor.columns:
    anchor_keep.append(anchor_T_col)

df_anchor_slim = (
    df_anchor[anchor_keep]
    .drop_duplicates(subset=[material_key_col])
    .copy()
)

df_anchor_slim[anchor_lnp_col_used] = pd.to_numeric(
    df_anchor_slim[anchor_lnp_col_used],
    errors="coerce",
)

df_anchor_slim[boiling_col] = pd.to_numeric(
    df_anchor_slim[boiling_col],
    errors="coerce",
)

if k1_col in df_anchor_slim.columns:
    df_anchor_slim["k1_valid"] = pd.to_numeric(
        df_anchor_slim[k1_col],
        errors="coerce",
    )
else:
    df_anchor_slim["k1_valid"] = (
        pd.to_numeric(df_anchor_slim[anchor_T_col], errors="coerce")
        / pd.to_numeric(df_anchor_slim[boiling_col], errors="coerce")
    )

k1_median = df_anchor_slim["k1_valid"].replace([np.inf, -np.inf], np.nan).median()
df_anchor_slim["k1_valid"] = df_anchor_slim["k1_valid"].fillna(k1_median)

valid_anchor = (
    df_anchor_slim[anchor_lnp_col_used].notna()
    & df_anchor_slim[boiling_col].notna()
    & (df_anchor_slim[boiling_col] > 0)
    & np.isfinite(df_anchor_slim["k1_valid"])
)

df_anchor_valid = df_anchor_slim[valid_anchor].copy()

print("有效锚点物质数:", len(df_anchor_valid))


# =========================================================
# 7. 全数据训练锚点子模型（预测 lnP_anchor 和 boiling_T）
# =========================================================
df_material = df_groups_used.reset_index().rename(columns={"index": "orig_idx"})
df_material[material_key_col] = df_groups_raw.loc[
    df_material.index,
    material_key_col,
].values

df_material = df_material.merge(
    df_anchor_valid,
    on=material_key_col,
    how="inner",
)

df_material = df_material.dropna(
    subset=used_group_cols + [anchor_lnp_col_used, boiling_col, "k1_valid"]
)

df_material = df_material.reset_index(drop=True)

print("合并后物质数:", len(df_material))

X_anchor = df_material[used_group_cols].values.astype(float)
y_lnP_anchor = df_material[anchor_lnp_col_used].values.astype(float)
y_boiling = df_material[boiling_col].values.astype(float)

anchor_lnP_model = HistGradientBoostingRegressor(**hgb_params)
anchor_boiling_model = HistGradientBoostingRegressor(**hgb_params)

anchor_lnP_model.fit(X_anchor, y_lnP_anchor)
anchor_boiling_model.fit(X_anchor, y_boiling)

df_material["lnP_anchor_pred"] = anchor_lnP_model.predict(X_anchor)
df_material["boiling_T_pred"] = anchor_boiling_model.predict(X_anchor)
df_material["anchor_T_pred"] = df_material["k1_valid"] * df_material["boiling_T_pred"]
df_material["invT_anchor_pred"] = 1.0 / df_material["anchor_T_pred"]

# 子模型评价与预测保存
df_submodel_summary = pd.DataFrame([
    {
        "submodel": "anchor_lnP_model",
        "target": anchor_lnp_col_used,
        "model_type": "HistGradientBoostingRegressor",
        "params": str(hgb_params),
        **compute_metrics_target_space(
            y_lnP_anchor,
            df_material["lnP_anchor_pred"].values,
            "lnP_anchor",
        ),
    },
    {
        "submodel": "anchor_boiling_model",
        "target": boiling_col,
        "model_type": "HistGradientBoostingRegressor",
        "params": str(hgb_params),
        **compute_metrics_target_space(
            y_boiling,
            df_material["boiling_T_pred"].values,
            "boiling_T",
        ),
    },
])

df_submodel_predictions = pd.DataFrame({
    material_key_col: df_material[material_key_col].values,
    "lnP_anchor_true": y_lnP_anchor,
    "lnP_anchor_pred": df_material["lnP_anchor_pred"].values,
    "lnP_anchor_abs_error": np.abs(df_material["lnP_anchor_pred"].values - y_lnP_anchor),
    "lnP_anchor_relative_error_percent": safe_relative_error_percent(
        y_lnP_anchor,
        df_material["lnP_anchor_pred"].values,
    ),
    "P_anchor_true": safe_exp(y_lnP_anchor),
    "P_anchor_pred": safe_exp(df_material["lnP_anchor_pred"].values),
    "P_anchor_relative_error_percent": safe_relative_error_percent(
        safe_exp(y_lnP_anchor),
        safe_exp(df_material["lnP_anchor_pred"].values),
    ),
    "boiling_T_true": y_boiling,
    "boiling_T_pred": df_material["boiling_T_pred"].values,
    "boiling_T_abs_error": np.abs(df_material["boiling_T_pred"].values - y_boiling),
    "boiling_T_relative_error_percent": safe_relative_error_percent(
        y_boiling,
        df_material["boiling_T_pred"].values,
    ),
    "k1_valid": df_material["k1_valid"].values,
    "anchor_T_pred": df_material["anchor_T_pred"].values,
    "invT_anchor_pred": df_material["invT_anchor_pred"].values,
})


# =========================================================
# 8. 展开温度点数据
# =========================================================
df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
df_data[target_col] = pd.to_numeric(df_data[target_col], errors="coerce")
df_data["InvT"] = 1.0 / df_data[temp_col]

df_long = df_data.merge(
    df_material[
        [material_key_col]
        + used_group_cols
        + ["lnP_anchor_pred", "boiling_T_pred", "anchor_T_pred", "invT_anchor_pred", "k1_valid"]
    ],
    on=material_key_col,
    how="inner",
)

df_long = df_long.dropna(
    subset=[target_col, temp_col, "InvT"]
    + used_group_cols
    + ["lnP_anchor_pred", "invT_anchor_pred"]
)

df_long = df_long.reset_index(drop=True)

print("最终温度点总数:", len(df_long))

X_groups = df_long[used_group_cols].values.astype(float)
invT_all = df_long["InvT"].values.astype(float)
lnP_true = df_long[target_col].values.astype(float)
P_true = safe_exp(lnP_true)

lnP_anchor_pred = df_long["lnP_anchor_pred"].values.astype(float)
invT_anchor_pred = df_long["invT_anchor_pred"].values.astype(float)
boiling_T_pred = df_long["boiling_T_pred"].values.astype(float)
anchor_T_pred = df_long["anchor_T_pred"].values.astype(float)

material_keys = df_long[material_key_col].values.astype(str)
unique_materials = np.unique(material_keys)

all_sample_indices = np.arange(len(df_long))

if len(unique_materials) < n_outer_folds:
    raise ValueError(f"物质数 {len(unique_materials)} 小于 n_outer_folds={n_outer_folds}，无法做 5-fold。")


# =========================================================
# 9. 特征构造与方法B训练/预测函数
# =========================================================
def build_direct_features_by_indices(indices):
    indices = np.asarray(indices, dtype=int)
    return np.hstack([
        X_groups[indices],
        invT_all[indices].reshape(-1, 1),
    ])


def build_residual_features_by_indices(indices):
    indices = np.asarray(indices, dtype=int)
    return np.hstack([
        X_groups[indices],
        invT_all[indices].reshape(-1, 1),
    ])


def build_baseline_features_by_indices(indices):
    indices = np.asarray(indices, dtype=int)
    delta_invT = invT_all[indices] - invT_anchor_pred[indices]
    return X_groups[indices] * delta_invT.reshape(-1, 1)


def train_methodB(train_indices):
    """
    方法B：
        baseline_lnP = lnP_anchor_pred + Ridge(Nk * (InvT - InvT_anchor))
        residual_y = lnP_true - baseline_lnP
        residual_pred = GBDT([Nk, InvT])
        final_lnP = baseline_lnP + residual_pred
    """
    train_indices = np.asarray(train_indices, dtype=int)

    # 1. 训练基线 Ridge
    X_base_train = build_baseline_features_by_indices(train_indices)
    y_base_train = lnP_true[train_indices] - lnP_anchor_pred[train_indices]

    valid_base = (
        np.isfinite(X_base_train).all(axis=1)
        & np.isfinite(y_base_train)
    )

    if valid_base.sum() == 0:
        raise ValueError("基线模型无有效训练样本")

    base_model = Ridge(alpha=baseline_ridge_alpha, fit_intercept=False)
    base_model.fit(X_base_train[valid_base], y_base_train[valid_base])

    # 2. 用训练集基线预测构造残差目标
    baseline_delta_train = np.full(len(train_indices), np.nan, dtype=float)
    valid_base_all_train = np.isfinite(X_base_train).all(axis=1)
    baseline_delta_train[valid_base_all_train] = base_model.predict(X_base_train[valid_base_all_train])

    baseline_lnP_train = lnP_anchor_pred[train_indices] + baseline_delta_train
    residual_y_train = lnP_true[train_indices] - baseline_lnP_train

    X_res_train = build_residual_features_by_indices(train_indices)

    valid_res = (
        np.isfinite(X_res_train).all(axis=1)
        & np.isfinite(residual_y_train)
    )

    if valid_res.sum() == 0:
        raise ValueError("残差模型无有效训练样本")

    res_model = GradientBoostingRegressor(**gbdt_params)
    res_model.fit(X_res_train[valid_res], residual_y_train[valid_res])

    return base_model, res_model


def predict_methodB(indices, base_model, res_model):
    indices = np.asarray(indices, dtype=int)

    # baseline
    X_base = build_baseline_features_by_indices(indices)
    baseline_delta = np.full(len(indices), np.nan, dtype=float)

    valid_base = np.isfinite(X_base).all(axis=1)
    if valid_base.sum() > 0:
        baseline_delta[valid_base] = base_model.predict(X_base[valid_base])

    baseline_lnP = lnP_anchor_pred[indices] + baseline_delta

    # residual
    X_res = build_residual_features_by_indices(indices)
    residual_pred = np.full(len(indices), np.nan, dtype=float)

    valid_res = np.isfinite(X_res).all(axis=1)
    if valid_res.sum() > 0:
        residual_pred[valid_res] = res_model.predict(X_res[valid_res])

    final_lnP = baseline_lnP + residual_pred

    return final_lnP, baseline_lnP, residual_pred


def make_prediction_df(
    fold,
    dataset_name,
    method,
    indices,
    y_pred_lnP,
    baseline_lnP=None,
    residual_pred=None,
):
    indices = np.asarray(indices, dtype=int)

    y_true_lnP = lnP_true[indices]
    y_true_P = safe_exp(y_true_lnP)
    y_pred_P = safe_exp(y_pred_lnP)

    df_out = pd.DataFrame({
        "fold": fold,
        "dataset": dataset_name,
        "Method": method,
        material_key_col: material_keys[indices],
        "T_K": df_long[temp_col].values[indices],
        "InvT": invT_all[indices],
        "lnP_true": y_true_lnP,
        "lnP_pred": y_pred_lnP,
        "lnP_error": y_pred_lnP - y_true_lnP,
        "lnP_abs_error": np.abs(y_pred_lnP - y_true_lnP),
        "lnP_relative_error_percent": safe_relative_error_percent(y_true_lnP, y_pred_lnP),
        "P_true": y_true_P,
        "P_pred": y_pred_P,
        "P_error": y_pred_P - y_true_P,
        "P_abs_error": np.abs(y_pred_P - y_true_P),
        "P_relative_error_percent": safe_relative_error_percent(y_true_P, y_pred_P),
        "lnP_anchor_pred": lnP_anchor_pred[indices],
        "P_anchor_pred": safe_exp(lnP_anchor_pred[indices]),
        "boiling_T_pred": boiling_T_pred[indices],
        "anchor_T_pred": anchor_T_pred[indices],
        "invT_anchor_pred": invT_anchor_pred[indices],
    })

    if baseline_lnP is not None:
        df_out["baseline_lnP"] = baseline_lnP
        df_out["baseline_P"] = safe_exp(baseline_lnP)
        df_out["baseline_lnP_error"] = baseline_lnP - y_true_lnP
        df_out["baseline_P_relative_error_percent"] = safe_relative_error_percent(y_true_P, safe_exp(baseline_lnP))

    if residual_pred is not None:
        df_out["residual_pred_lnP"] = residual_pred
        df_out["residual_target_lnP"] = y_true_lnP - baseline_lnP if baseline_lnP is not None else np.nan

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
            df_out[col] = df_long[col].values[indices]

    return df_out


# =========================================================
# 10. 5折交叉验证
# =========================================================
kf = KFold(n_splits=n_outer_folds, shuffle=True, random_state=random_state)

metrics_direct_lnP = []
metrics_methodB_lnP = []

metrics_direct_P = []
metrics_methodB_P = []

metrics_baseline_lnP = []
metrics_baseline_P = []
metrics_residual_lnP = []

fold_test_prediction_dfs = []
fold_all_data_prediction_dfs = []
fold_all_data_count_records = []
fold_info_records = []

direct_feature_importance_records = []
residual_feature_importance_records = []
baseline_param_records = []

direct_feature_names = used_group_cols + ["InvT"]
residual_feature_names = used_group_cols + ["InvT"]
baseline_feature_names = [f"{g}*(InvT-invT_anchor)" for g in used_group_cols]

for fold, (train_idx, test_idx) in enumerate(kf.split(unique_materials), start=1):
    print(f"\n========== Fold {fold}/{n_outer_folds} ==========")

    train_materials = unique_materials[train_idx]
    test_materials = unique_materials[test_idx]

    train_mask = np.isin(material_keys, train_materials)
    test_mask = np.isin(material_keys, test_materials)

    train_indices = np.where(train_mask)[0]
    test_indices = np.where(test_mask)[0]

    print("训练物质数:", len(train_materials))
    print("测试物质数:", len(test_materials))
    print("训练样本点数:", len(train_indices))
    print("测试样本点数:", len(test_indices))

    # -----------------------------------------------------
    # 方法1：直接 GBDT，预测 lnP
    # -----------------------------------------------------
    X_train_A = build_direct_features_by_indices(train_indices)
    y_train_A = lnP_true[train_indices]

    valid_A = (
        np.isfinite(X_train_A).all(axis=1)
        & np.isfinite(y_train_A)
    )

    model_A = GradientBoostingRegressor(**gbdt_params)
    model_A.fit(X_train_A[valid_A], y_train_A[valid_A])

    X_test_A = build_direct_features_by_indices(test_indices)
    y_test_lnP = lnP_true[test_indices]

    y_pred_A_test = np.full(len(test_indices), np.nan, dtype=float)
    valid_test_A = np.isfinite(X_test_A).all(axis=1)
    y_pred_A_test[valid_test_A] = model_A.predict(X_test_A[valid_test_A])

    X_all_A = build_direct_features_by_indices(all_sample_indices)
    y_pred_A_all = np.full(len(all_sample_indices), np.nan, dtype=float)
    valid_all_A = np.isfinite(X_all_A).all(axis=1)
    y_pred_A_all[valid_all_A] = model_A.predict(X_all_A[valid_all_A])

    # -----------------------------------------------------
    # 方法2：锚点线性基线 + 残差 GBDT
    # -----------------------------------------------------
    try:
        base_model, res_model = train_methodB(train_indices)

        y_pred_B_test, baseline_lnP_test, residual_pred_test = predict_methodB(
            test_indices,
            base_model,
            res_model,
        )

        y_pred_B_all, baseline_lnP_all, residual_pred_all = predict_methodB(
            all_sample_indices,
            base_model,
            res_model,
        )

    except Exception as e:
        print(f"  Fold {fold} 方法B失败: {e}")

        base_model = None
        res_model = None

        y_pred_B_test = np.full(len(test_indices), np.nan, dtype=float)
        baseline_lnP_test = np.full(len(test_indices), np.nan, dtype=float)
        residual_pred_test = np.full(len(test_indices), np.nan, dtype=float)

        y_pred_B_all = np.full(len(all_sample_indices), np.nan, dtype=float)
        baseline_lnP_all = np.full(len(all_sample_indices), np.nan, dtype=float)
        residual_pred_all = np.full(len(all_sample_indices), np.nan, dtype=float)

    # -----------------------------------------------------
    # 测试集指标：lnP 空间和 P 空间
    # -----------------------------------------------------
    m_lnP_A = compute_metrics_lnP(y_test_lnP, y_pred_A_test)
    m_lnP_B = compute_metrics_lnP(y_test_lnP, y_pred_B_test)

    m_lnP_A["fold"] = fold
    m_lnP_B["fold"] = fold

    metrics_direct_lnP.append(m_lnP_A)
    metrics_methodB_lnP.append(m_lnP_B)

    m_P_A = compute_metrics_P_from_lnP(y_test_lnP, y_pred_A_test)
    m_P_B = compute_metrics_P_from_lnP(y_test_lnP, y_pred_B_test)

    m_P_A["fold"] = fold
    m_P_B["fold"] = fold

    metrics_direct_P.append(m_P_A)
    metrics_methodB_P.append(m_P_B)

    # baseline only 指标
    mb_lnP = compute_metrics_lnP(y_test_lnP, baseline_lnP_test)
    mb_P = compute_metrics_P_from_lnP(y_test_lnP, baseline_lnP_test)
    mb_lnP["fold"] = fold
    mb_P["fold"] = fold

    metrics_baseline_lnP.append(mb_lnP)
    metrics_baseline_P.append(mb_P)

    # residual 模型自身指标：目标是 lnP residual
    residual_target_test = y_test_lnP - baseline_lnP_test
    mr_lnP = compute_metrics_lnP(residual_target_test, residual_pred_test)
    mr_lnP["fold"] = fold
    metrics_residual_lnP.append(mr_lnP)

    print(
        "Direct GBDT test: "
        f"R2_lnP={m_lnP_A['R2_lnP']:.6f}, "
        f"MSE_lnP={m_lnP_A['MSE_lnP']:.6f}, "
        f"MAE_lnP={m_lnP_A['MAE_lnP']:.6f}, "
        f"ARD_P={m_P_A['ARD_P_percent']:.6f}%"
    )

    print(
        "MethodB final test: "
        f"R2_lnP={m_lnP_B['R2_lnP']:.6f}, "
        f"MSE_lnP={m_lnP_B['MSE_lnP']:.6f}, "
        f"MAE_lnP={m_lnP_B['MAE_lnP']:.6f}, "
        f"ARD_P={m_P_B['ARD_P_percent']:.6f}%"
    )

    # -----------------------------------------------------
    # 新增：每个 fold 模型预测完整数据集，并统计 P 空间偏差数量
    # -----------------------------------------------------
    count_A_all_P = count_error_thresholds(P_true, safe_exp(y_pred_A_all))
    count_B_all_P = count_error_thresholds(P_true, safe_exp(y_pred_B_all))

    count_A_all_lnP = count_error_thresholds(lnP_true, y_pred_A_all)
    count_B_all_lnP = count_error_thresholds(lnP_true, y_pred_B_all)

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "GBDT_direct_lnP",
        "count_space": "P",
        **count_A_all_P,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "Anchor_linear_baseline_plus_GBDT_residual_lnP",
        "count_space": "P",
        **count_B_all_P,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "GBDT_direct_lnP",
        "count_space": "lnP",
        **count_A_all_lnP,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "Anchor_linear_baseline_plus_GBDT_residual_lnP",
        "count_space": "lnP",
        **count_B_all_lnP,
    })

    print("\nDirect GBDT fold model predicts ALL data count summary in P space:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "GBDT_direct_lnP",
        "count_space": "P",
        **count_A_all_P,
    }]).to_string(index=False))

    print("\nMethodB fold model predicts ALL data count summary in P space:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "Anchor_linear_baseline_plus_GBDT_residual_lnP",
        "count_space": "P",
        **count_B_all_P,
    }]).to_string(index=False))

    # -----------------------------------------------------
    # 保存测试集预测明细
    # -----------------------------------------------------
    df_test_A = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="GBDT_direct_lnP",
        indices=test_indices,
        y_pred_lnP=y_pred_A_test,
    )

    df_test_B = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="Anchor_linear_baseline_plus_GBDT_residual_lnP",
        indices=test_indices,
        y_pred_lnP=y_pred_B_test,
        baseline_lnP=baseline_lnP_test,
        residual_pred=residual_pred_test,
    )

    fold_test_prediction_dfs.append(df_test_A)
    fold_test_prediction_dfs.append(df_test_B)

    # -----------------------------------------------------
    # 保存完整数据集预测明细
    # -----------------------------------------------------
    df_all_A = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="GBDT_direct_lnP",
        indices=all_sample_indices,
        y_pred_lnP=y_pred_A_all,
    )

    df_all_B = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="Anchor_linear_baseline_plus_GBDT_residual_lnP",
        indices=all_sample_indices,
        y_pred_lnP=y_pred_B_all,
        baseline_lnP=baseline_lnP_all,
        residual_pred=residual_pred_all,
    )

    fold_all_data_prediction_dfs.append(df_all_A)
    fold_all_data_prediction_dfs.append(df_all_B)

    # -----------------------------------------------------
    # 保存特征重要性和参数
    # -----------------------------------------------------
    if hasattr(model_A, "feature_importances_"):
        for fname, imp in zip(direct_feature_names, model_A.feature_importances_):
            direct_feature_importance_records.append({
                "fold": fold,
                "feature": fname,
                "importance": imp,
            })

    if res_model is not None and hasattr(res_model, "feature_importances_"):
        for fname, imp in zip(residual_feature_names, res_model.feature_importances_):
            residual_feature_importance_records.append({
                "fold": fold,
                "feature": fname,
                "importance": imp,
            })

    if base_model is not None and hasattr(base_model, "coef_"):
        for fname, coef in zip(baseline_feature_names, base_model.coef_):
            baseline_param_records.append({
                "fold": fold,
                "feature": fname,
                "baseline_coef": coef,
                "abs_baseline_coef": abs(coef),
            })

    fold_info_records.append({
        "fold": fold,
        "n_train_materials": len(train_materials),
        "n_test_materials": len(test_materials),
        "n_train_points": len(train_indices),
        "n_test_points": len(test_indices),
        "n_all_points": len(all_sample_indices),
        "n_group_features": len(used_group_cols),
        "direct_n_features": len(direct_feature_names),
        "baseline_n_features": len(baseline_feature_names),
        "residual_n_features": len(residual_feature_names),
        "methodB_success": base_model is not None and res_model is not None,
    })


# =========================================================
# 11. 汇总统计
# =========================================================
df_direct_lnP = pd.DataFrame(metrics_direct_lnP)
df_methodB_lnP = pd.DataFrame(metrics_methodB_lnP)

df_direct_P = pd.DataFrame(metrics_direct_P)
df_methodB_P = pd.DataFrame(metrics_methodB_P)

df_baseline_lnP = pd.DataFrame(metrics_baseline_lnP)
df_baseline_P = pd.DataFrame(metrics_baseline_P)
df_residual_lnP = pd.DataFrame(metrics_residual_lnP)

metric_names_lnP = [c for c in df_direct_lnP.columns if c != "fold"]
metric_names_P = [c for c in df_direct_P.columns if c != "fold"]

summary_lnP_direct = summarize(df_direct_lnP, "GBDT_direct_lnP", metric_names_lnP)
summary_lnP_methodB = summarize(df_methodB_lnP, "Anchor_linear_baseline_plus_GBDT_residual_lnP", metric_names_lnP)
summary_lnP_baseline = summarize(df_baseline_lnP, "MethodB_baseline_only_lnP", metric_names_lnP)
summary_lnP_residual = summarize(df_residual_lnP, "MethodB_residual_model_lnP", metric_names_lnP)

summary_lnP = pd.concat(
    [
        summary_lnP_direct,
        summary_lnP_methodB,
        summary_lnP_baseline,
        summary_lnP_residual,
    ],
    ignore_index=True,
)

summary_P_direct = summarize(df_direct_P, "GBDT_direct_P", metric_names_P)
summary_P_methodB = summarize(df_methodB_P, "Anchor_linear_baseline_plus_GBDT_residual_P", metric_names_P)
summary_P_baseline = summarize(df_baseline_P, "MethodB_baseline_only_P", metric_names_P)

summary_P = pd.concat(
    [
        summary_P_direct,
        summary_P_methodB,
        summary_P_baseline,
    ],
    ignore_index=True,
)

print("\n========== lnP 空间 5-Fold CV Summary ==========")
print(summary_lnP.to_string(index=False))

print("\n========== P 空间 5-Fold CV Summary ==========")
print(summary_P.to_string(index=False))


# =========================================================
# 12. 配对 t 检验
# =========================================================
ttest_lnP = paired_ttest(
    df_direct_lnP,
    df_methodB_lnP,
    metric_names_lnP,
    "direct",
    "methodB",
)

ttest_P = paired_ttest(
    df_direct_P,
    df_methodB_P,
    metric_names_P,
    "direct",
    "methodB",
)

print("\n========== Paired t-test (lnP空间) ==========")
print(ttest_lnP.to_string(index=False))

print("\n========== Paired t-test (P空间) ==========")
print(ttest_P.to_string(index=False))


# =========================================================
# 13. 完整数据集偏差数量统计汇总
# =========================================================
df_fold_all_data_count_summary = pd.DataFrame(fold_all_data_count_records)

final_average_records = []

for (method_name, count_space), sub in df_fold_all_data_count_summary.groupby(["Method", "count_space"]):
    final_average_records.append({
        "Method": method_name,
        "count_space": count_space,
        "mean_count_rel_err_lt_1pct": sub["count_rel_err_lt_1pct"].mean(),
        "mean_count_rel_err_lt_5pct": sub["count_rel_err_lt_5pct"].mean(),
        "mean_count_rel_err_lt_10pct": sub["count_rel_err_lt_10pct"].mean(),
        "std_count_rel_err_lt_1pct": sub["count_rel_err_lt_1pct"].std(ddof=1),
        "std_count_rel_err_lt_5pct": sub["count_rel_err_lt_5pct"].std(ddof=1),
        "std_count_rel_err_lt_10pct": sub["count_rel_err_lt_10pct"].std(ddof=1),
        "n_folds": len(sub),
        "n_all_data_points": len(all_sample_indices),
    })

df_final_average_summary = pd.DataFrame(final_average_records)

print("\n========== Fold all-data count summary ==========")
print(df_fold_all_data_count_summary.to_string(index=False))

print("\n========== Final average all-data count summary ==========")
print(df_final_average_summary.to_string(index=False))


# =========================================================
# 14. 整理输出表
# =========================================================
df_fold_test_predictions = pd.concat(fold_test_prediction_dfs, ignore_index=True)
df_fold_all_data_predictions = pd.concat(fold_all_data_prediction_dfs, ignore_index=True)

df_fold_info = pd.DataFrame(fold_info_records)
df_direct_feature_importance = pd.DataFrame(direct_feature_importance_records)
df_residual_feature_importance = pd.DataFrame(residual_feature_importance_records)
df_baseline_params = pd.DataFrame(baseline_param_records)

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
    {"param": "target_type", "value": target_type},
    {"param": "n_outer_folds", "value": n_outer_folds},
    {"param": "random_state", "value": random_state},
    {"param": "n_group_features", "value": len(used_group_cols)},
    {"param": "n_temperature_points", "value": len(df_long)},
    {"param": "n_materials", "value": len(unique_materials)},
    {"param": "direct_GBDT_params", "value": str(gbdt_params)},
    {"param": "methodB_baseline", "value": f"Ridge(alpha={baseline_ridge_alpha}, fit_intercept=False) in lnP space"},
    {"param": "methodB_residual_gbdt", "value": str(gbdt_params)},
    {"param": "anchor_submodel", "value": "HistGradientBoostingRegressor trained globally on lnP_anchor and boiling_T"},
    {"param": "anchor_submodel_params", "value": str(hgb_params)},
    {"param": "final_count_space", "value": "P space, where P=exp(lnP)"},
    {
        "param": "relative_error_definition",
        "value": "abs((y_pred - y_true) / y_true) * 100; abs(y_true)<=1e-12 -> NaN",
    },
    {
        "param": "full_data_count_rule",
        "value": "Each fold model predicts the whole dataset; count P-space relative error <1%, <5%, <10%; then average counts over 5 folds.",
    },
])

df_model_structure = pd.DataFrame([
    {
        "项目": "预测对象",
        "内容": f"蒸汽压对数 lnP，目标列 {target_col}；同时保存 P=exp(lnP) 空间指标",
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
        "内容": f"{n_outer_folds}-fold KFold，按 material_key 物质划分，shuffle=True，random_state={random_state}",
    },
    {
        "项目": "方法1",
        "内容": "GBDT_direct_lnP：直接 GBDT 预测 lnP",
    },
    {
        "项目": "方法1输入特征",
        "内容": f"[Nk, InvT]，有效基团数 {len(used_group_cols)}，总维度 {len(used_group_cols) + 1}",
    },
    {
        "项目": "方法1模型",
        "内容": "GradientBoostingRegressor",
    },
    {
        "项目": "方法1参数",
        "内容": str(gbdt_params),
    },
    {
        "项目": "方法2",
        "内容": "Anchor_linear_baseline_plus_GBDT_residual_lnP：锚点线性基线 + GBDT 残差修正",
    },
    {
        "项目": "方法2最终公式",
        "内容": "lnP_pred = baseline_lnP + residual_pred",
    },
    {
        "项目": "锚点子模型",
        "内容": "全局训练两个 HistGradientBoostingRegressor：一个预测 lnP_anchor，一个预测 boiling_T",
    },
    {
        "项目": "锚点子模型参数",
        "内容": str(hgb_params),
    },
    {
        "项目": "锚点子模型输入特征",
        "内容": f"Nk，有效基团数 {len(used_group_cols)}",
    },
    {
        "项目": "anchor_T 构造",
        "内容": "anchor_T_pred = k1_valid * boiling_T_pred；invT_anchor_pred = 1 / anchor_T_pred",
    },
    {
        "项目": "baseline 构造",
        "内容": "baseline_lnP = lnP_anchor_pred + Ridge(Nk * (InvT - invT_anchor_pred))",
    },
    {
        "项目": "baseline 模型",
        "内容": f"Ridge(alpha={baseline_ridge_alpha}, fit_intercept=False)",
    },
    {
        "项目": "residual 构造",
        "内容": "residual_y = lnP_true - baseline_lnP；residual_pred = GBDT([Nk, InvT])",
    },
    {
        "项目": "residual 模型",
        "内容": "GradientBoostingRegressor",
    },
    {
        "项目": "residual 参数",
        "内容": str(gbdt_params),
    },
    {
        "项目": "最终模型",
        "内容": "方法1为直接 GBDT；方法2为 baseline + residual GBDT",
    },
    {
        "项目": "偏差数量统计口径",
        "内容": "每个 fold 训练出的最终模型预测完整数据集，在 P=exp(lnP) 空间统计相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 取平均",
    },
])


# =========================================================
# 15. 保存 Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    # 原有核心指标
    df_direct_lnP.to_excel(writer, sheet_name="Fold_Metrics_Direct_lnP", index=False)
    df_methodB_lnP.to_excel(writer, sheet_name="Fold_Metrics_MethodB_lnP", index=False)
    summary_lnP.to_excel(writer, sheet_name="Summary_lnP_Mean_Std", index=False)
    ttest_lnP.to_excel(writer, sheet_name="Paired_T_Test_lnP", index=False)

    df_direct_P.to_excel(writer, sheet_name="Fold_Metrics_Direct_P", index=False)
    df_methodB_P.to_excel(writer, sheet_name="Fold_Metrics_MethodB_P", index=False)
    summary_P.to_excel(writer, sheet_name="Summary_P_Mean_Std", index=False)
    ttest_P.to_excel(writer, sheet_name="Paired_T_Test_P", index=False)

    # baseline / residual
    df_baseline_lnP.to_excel(writer, sheet_name="Baseline_Metrics_lnP", index=False)
    df_baseline_P.to_excel(writer, sheet_name="Baseline_Metrics_P", index=False)
    df_residual_lnP.to_excel(writer, sheet_name="Residual_Metrics_lnP", index=False)

    # 新增预测明细和全数据统计
    df_fold_test_predictions.to_excel(writer, sheet_name="fold_test_predictions", index=False)
    df_fold_all_data_predictions.to_excel(writer, sheet_name="fold_all_data_predictions", index=False)
    df_fold_all_data_count_summary.to_excel(writer, sheet_name="fold_all_data_count_summary", index=False)
    df_final_average_summary.to_excel(writer, sheet_name="final_average_summary", index=False)

    # 子模型、参数、结构
    df_submodel_summary.to_excel(writer, sheet_name="submodel_summary", index=False)
    df_submodel_predictions.to_excel(writer, sheet_name="submodel_predictions", index=False)

    df_baseline_params.to_excel(writer, sheet_name="baseline_params", index=False)
    df_direct_feature_importance.to_excel(writer, sheet_name="direct_feature_importance", index=False)
    df_residual_feature_importance.to_excel(writer, sheet_name="residual_feature_importance", index=False)

    df_fold_info.to_excel(writer, sheet_name="Fold_Info", index=False)
    df_used_groups.to_excel(writer, sheet_name="Used_Groups", index=False)
    df_removed_zero_groups.to_excel(writer, sheet_name="Removed_Zero_Groups", index=False)

    df_run_info.to_excel(writer, sheet_name="Run_Info", index=False)
    df_model_structure.to_excel(writer, sheet_name="model_structure", index=False)

    format_excel(writer)

print(f"\n保存完成: {output_file}")


# =========================================================
# 16. 最终方便复制输出
# =========================================================
def get_final_counts(method_name, count_space="P"):
    row = df_final_average_summary[
        (df_final_average_summary["Method"] == method_name)
        & (df_final_average_summary["count_space"] == count_space)
    ]

    if row.empty:
        return np.nan, np.nan, np.nan

    row = row.iloc[0]

    return (
        row["mean_count_rel_err_lt_1pct"],
        row["mean_count_rel_err_lt_5pct"],
        row["mean_count_rel_err_lt_10pct"],
    )


direct_1, direct_5, direct_10 = get_final_counts("GBDT_direct_lnP", count_space="P")
methodB_1, methodB_5, methodB_10 = get_final_counts(
    "Anchor_linear_baseline_plus_GBDT_residual_lnP",
    count_space="P",
)

print("\n方法1 全数据预测偏差 1%，5%，10%分别为：")
print(direct_1)
print(direct_5)
print(direct_10)

print("\n方法2 全数据预测偏差 1%，5%，10%分别为：")
print(methodB_1)
print(methodB_5)
print(methodB_10)


# =========================================================
# 17. 代码结构打印
# =========================================================
print("\n========== 当前代码结构简要汇总 ==========")
print(f"预测对象：蒸汽压 lnP / {target_col}，并保存 P=exp(lnP) 空间指标")
print(f"数据文件：{input_file}")
print(f"sheet 名称：{data_sheet}, {groups_sheet}, {anchor_sheet}")
print(f"交叉验证：{n_outer_folds}-fold，按 material_key 物质划分")
print("方法1：GBDT_direct_lnP，GradientBoostingRegressor，输入 [Nk, InvT]")
print("方法2：Anchor_linear_baseline_plus_GBDT_residual_lnP，锚点线性基线 + GBDT 残差修正")
print("锚点子模型：HistGradientBoostingRegressor，全局训练，分别预测 lnP_anchor 与 boiling_T")
print(f"锚点子模型参数：{hgb_params}")
print("anchor_T 构造：anchor_T_pred = k1_valid * boiling_T_pred；invT_anchor_pred = 1 / anchor_T_pred")
print("baseline 构造：baseline_lnP = lnP_anchor_pred + Ridge(Nk * (InvT - invT_anchor_pred))")
print(f"baseline 模型：Ridge(alpha={baseline_ridge_alpha}, fit_intercept=False)")
print("residual 构造：residual_y = lnP_true - baseline_lnP")
print(f"residual 模型：GradientBoostingRegressor，参数：{gbdt_params}")
print(f"方法1最终模型参数：{gbdt_params}")
print("方法1最终输入：[Nk, InvT]")
print("方法2最终输入：baseline 使用 Nk*(InvT-invT_anchor_pred)，residual 使用 [Nk, InvT]")
print("偏差统计口径：每个 fold 模型预测完整数据集，在 P=exp(lnP) 空间统计 <1%、<5%、<10% 点数，再对 5 个 fold 取平均")