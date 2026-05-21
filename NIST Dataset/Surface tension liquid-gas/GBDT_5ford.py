# # -*- coding: utf-8 -*-
# """
# Surface tension liquid-gas:
# GBDT_direct vs Anchor + linear baseline + GBDT residual 5-fold CV
#
# 输入：
#     dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points_with_RSQ.xlsx
#
# 如果该文件不存在，自动尝试：
#     dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points.xlsx
#
# 需要的 sheet：
#     Data_selected
#     Groups_selected
#     Interpolated_k1_k2
#
# 输出：
#     GBDT_direct_vs_anchor_baseline_residual_5fold_CV_SurfaceTension_target.xlsx
#
# 比较模型：
#     方法 A：
#         GBDT_direct
#         输入特征 = groups + T_K
#         目标 = SurfaceTension_N_m
#
#     方法 B：
#         Anchor + linear baseline + GBDT residual
#
#         先用基团子模型预测：
#             Surface_anchor_pred = f_group(k1*Tb 处表面张力)
#             boiling_T_pred = f_group(Tb)
#
#         得到：
#             T_anchor_pred = k1 * boiling_T_pred
#
#         基线：
#             Surface_base = Surface_anchor_pred
#                            + (T - T_anchor_pred) * sum_k(N_k * A_k)
#
#         残差：
#             residual = Surface_true - Surface_base
#
#         最终：
#             Surface_pred = Surface_base + GBDT_residual(groups + T_K)
#
# 交叉验证：
#     按 material_key 做 5-fold CV，避免同一物质的不同温度点同时进入训练集和测试集。
#
# 注意：
#     为了和原始参考代码保持一致，锚点子模型使用全数据训练。
# """
#
# import warnings
# warnings.filterwarnings("ignore")
#
# import pandas as pd
# import numpy as np
# from pathlib import Path
#
# from sklearn.ensemble import GradientBoostingRegressor, HistGradientBoostingRegressor
# from sklearn.linear_model import Ridge
# from sklearn.model_selection import KFold
# from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
#
# try:
#     from scipy.stats import ttest_rel
#     SCIPY_AVAILABLE = True
# except Exception:
#     SCIPY_AVAILABLE = False
#
#
# # =========================================================
# # 0. 全局显示设置
# # =========================================================
#
# pd.set_option("display.float_format", "{:.10f}".format)
# np.set_printoptions(suppress=True, precision=10)
#
#
# # =========================================================
# # 1. 输入输出设置
# # =========================================================
#
# preferred_input_file = Path(
#     "dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points_with_RSQ.xlsx"
# )
#
# fallback_input_file = Path(
#     "dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points.xlsx"
# )
#
# if preferred_input_file.exists():
#     input_file = preferred_input_file
# elif fallback_input_file.exists():
#     input_file = fallback_input_file
# else:
#     raise FileNotFoundError(
#         "没有找到输入文件：\n"
#         f"1. {preferred_input_file}\n"
#         f"2. {fallback_input_file}"
#     )
#
# data_sheet = "Data_selected"
# groups_sheet = "Groups_selected"
# anchor_sheet = "Interpolated_k1_k2"
#
# output_file = Path(
#     "GBDT_direct_vs_anchor_baseline_residual_5fold_CV_SurfaceTension_target.xlsx"
# )
#
#
# # =========================================================
# # 2. 基础列名设置
# # =========================================================
#
# material_key_col = "material_key"
# temp_col = "T_K"
#
# # 表面张力目标列候选
# surface_candidates = [
#     "SurfaceTension_N_m",
#     "surface_tension_N_m",
#     "Surface_Tension_N_m",
#     "SurfaceTension",
#     "surface_tension",
#     "property_value",
# ]
#
# # 表面张力锚点列
# anchor_surface_col = "SurfaceTension_N_m_interp_at_k1Tb"
#
# boiling_col = "boiling_T_K"
# k1_col = "k1"
# anchor_T_col = "k1_times_boiling_T_K"
#
# # 基团列设置
# # 默认按第 3 列到第 222 列取前 220 个基团；
# # 如果固定位置不可用，则自动识别数值型基团列。
# n_group_features_to_use = 220
# use_fixed_group_position = True
# group_start_col_1based = 3
# group_end_col_1based = 222
#
# # 交叉验证设置
# n_outer_folds = 5
# random_state = 42
#
#
# # =========================================================
# # 3. 模型参数
# # =========================================================
#
# # 锚点子模型参数：用于预测 Surface_anchor 和 Tb
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
# # 直接 GBDT 和残差 GBDT 参数
# gbdt_params = {
#     "n_estimators": 500,
#     "learning_rate": 0.03,
#     "max_depth": 3,
#     "min_samples_split": 10,
#     "min_samples_leaf": 5,
#     "subsample": 0.9,
#     "random_state": random_state,
# }
#
#
# # =========================================================
# # 4. 工具函数
# # =========================================================
#
# def is_valid_value(x):
#     if pd.isna(x):
#         return False
#
#     s = str(x).strip()
#
#     if s == "":
#         return False
#
#     if s.lower() in ["nan", "none", "null", "待定"]:
#         return False
#
#     return True
#
#
# def build_material_key(row):
#     """
#     构造物质唯一标识。
#
#     优先级：
#         1. material_key
#         2. inchikey
#         3. pubchem_inchikey
#         4. cas
#         5. compound_name
#         6. formula
#     """
#     for col in [
#         "material_key",
#         "inchikey",
#         "pubchem_inchikey",
#         "cas",
#         "compound_name",
#         "formula",
#     ]:
#         if col in row.index and is_valid_value(row[col]):
#             if col == "material_key":
#                 return str(row[col]).strip()
#
#             return f"{col}:{str(row[col]).strip()}"
#
#     return "unknown_material"
#
#
# def find_first_existing_col(df, candidates, col_type):
#     """
#     从候选列名中找第一个存在的列，支持大小写不敏感。
#     """
#     lower_map = {str(c).lower(): c for c in df.columns}
#
#     for col in candidates:
#         if col in df.columns:
#             return col
#
#     for col in candidates:
#         if col.lower() in lower_map:
#             return lower_map[col.lower()]
#
#     raise ValueError(
#         f"没有找到 {col_type} 列。\n"
#         f"候选列名: {candidates}\n"
#         f"当前列名: {list(df.columns)}"
#     )
#
#
# def identify_group_columns(df_groups, n=220):
#     """
#     识别基团列。
#
#     优先：
#         固定读取第 3 列到第 222 列，共 220 个基团。
#     如果固定位置不可用：
#         自动识别数值型基团列，并排除明显元信息列。
#     """
#     if use_fixed_group_position:
#         start_idx = group_start_col_1based - 1
#         end_excl = group_end_col_1based
#
#         if len(df_groups.columns) >= end_excl:
#             group_cols = list(df_groups.columns[start_idx:end_excl])
#
#             if len(group_cols) == n:
#                 return group_cols
#
#         print("\n警告：固定位置基团列不可用，转为自动识别数值型基团列。")
#
#     metadata_keywords = [
#         "original_material_index",
#         "material_key",
#         "compound",
#         "name",
#         "cas",
#         "formula",
#         "smiles",
#         "inchi",
#         "inchikey",
#         "pubchem",
#         "phase",
#         "property",
#         "boiling",
#         "temperature",
#         "temp",
#         "t_k",
#         "pressure",
#         "surface",
#         "tension",
#         "k1",
#         "k2",
#         "interp",
#         "status",
#         "range",
#         "rsq",
#         "slope",
#         "title",
#         "doi",
#         "source",
#         "index",
#     ]
#
#     candidate_cols = []
#
#     for col in df_groups.columns:
#         col_lower = str(col).strip().lower()
#
#         if any(k in col_lower for k in metadata_keywords):
#             continue
#
#         num = pd.to_numeric(df_groups[col], errors="coerce")
#
#         if num.notna().sum() > 0:
#             candidate_cols.append(col)
#
#     if len(candidate_cols) == 0:
#         raise ValueError("没有识别到任何有效基团列。请检查 Groups_selected。")
#
#     if len(candidate_cols) >= n:
#         return candidate_cols[:n]
#
#     print(
#         f"\n警告：自动识别到的基团列只有 {len(candidate_cols)} 个，"
#         f"少于设定的 {n} 个，将使用全部识别到的基团列。"
#     )
#
#     return candidate_cols
#
#
# def compute_metrics_surface(y_true, y_pred):
#     """
#     表面张力预测评价指标。
#
#     输出：
#         R2
#         MSE
#         RMSE
#         MAE
#         ARD_percent
#         max_rel%
#         leq1%, leq5%, leq10% 这里是百分比，不是点数
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
#             "MSE": np.nan,
#             "RMSE": np.nan,
#             "MAE": np.nan,
#             "ARD_percent": np.nan,
#             "max_rel%": np.nan,
#             "leq1%": np.nan,
#             "leq5%": np.nan,
#             "leq10%": np.nan,
#         }
#
#     r2 = r2_score(y_true, y_pred) if len(y_true) >= 2 else np.nan
#     mse = mean_squared_error(y_true, y_pred)
#     rmse = np.sqrt(mse)
#     mae = mean_absolute_error(y_true, y_pred)
#
#     valid = np.abs(y_true) > 1e-12
#
#     if valid.sum() > 0:
#         rel_err = np.abs((y_pred[valid] - y_true[valid]) / y_true[valid]) * 100.0
#         ard = np.mean(rel_err)
#         max_rel = np.max(rel_err)
#         le1 = np.mean(rel_err <= 1.0) * 100.0
#         le5 = np.mean(rel_err <= 5.0) * 100.0
#         le10 = np.mean(rel_err <= 10.0) * 100.0
#     else:
#         ard = np.nan
#         max_rel = np.nan
#         le1 = np.nan
#         le5 = np.nan
#         le10 = np.nan
#
#     return {
#         "R2": r2,
#         "MSE": mse,
#         "RMSE": rmse,
#         "MAE": mae,
#         "ARD_percent": ard,
#         "max_rel%": max_rel,
#         "leq1%": le1,
#         "leq5%": le5,
#         "leq10%": le10,
#     }
#
#
# def format_metric_value(metric, value):
#     """
#     控制 Summary 中 Mean±Std 的显示精度。
#     表面张力 MSE 常较小，所以 MSE 多保留几位。
#     """
#     if pd.isna(value):
#         return "NaN"
#
#     if metric == "MSE":
#         return f"{value:.10f}"
#
#     if metric in ["RMSE", "MAE"]:
#         return f"{value:.8f}"
#
#     if metric in ["R2", "ARD_percent", "max_rel%", "leq1%", "leq5%", "leq10%"]:
#         return f"{value:.6f}"
#
#     return f"{value:.8f}"
#
#
# def summarize(df, name):
#     """
#     对 5 折指标计算 Mean ± Std。
#     """
#     metric_names = [c for c in df.columns if c not in ["fold"]]
#
#     rows = []
#
#     for metric in metric_names:
#         vals = pd.to_numeric(df[metric], errors="coerce").dropna().values
#
#         if len(vals) == 0:
#             mean_val = np.nan
#             std_val = np.nan
#             mean_std = "NaN"
#
#         elif len(vals) == 1:
#             mean_val = float(np.mean(vals))
#             std_val = np.nan
#             mean_std = f"{format_metric_value(metric, mean_val)} ± NaN"
#
#         else:
#             mean_val = float(np.mean(vals))
#             std_val = float(np.std(vals, ddof=1))
#             mean_std = (
#                 f"{format_metric_value(metric, mean_val)} ± "
#                 f"{format_metric_value(metric, std_val)}"
#             )
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
# # =========================================================
# # 5. 读取数据
# # =========================================================
#
# xls = pd.ExcelFile(input_file)
#
# print("输入文件:", input_file)
# print("输入文件包含 sheet:")
# print(xls.sheet_names)
#
# for sheet in [data_sheet, groups_sheet, anchor_sheet]:
#     if sheet not in xls.sheet_names:
#         raise ValueError(f"输入文件中没有找到 sheet: {sheet}")
#
# df_data = pd.read_excel(input_file, sheet_name=data_sheet)
# df_groups_raw = pd.read_excel(input_file, sheet_name=groups_sheet)
# df_anchor = pd.read_excel(input_file, sheet_name=anchor_sheet)
#
# print("\nData_selected 行数:", len(df_data))
# print("Groups_selected 物质数:", len(df_groups_raw))
# print("Interpolated_k1_k2 物质数:", len(df_anchor))
#
#
# # =========================================================
# # 6. 准备 material_key
# # =========================================================
#
# for df_name, df in [
#     ("Data_selected", df_data),
#     ("Groups_selected", df_groups_raw),
#     ("Interpolated_k1_k2", df_anchor),
# ]:
#     if material_key_col not in df.columns:
#         df[material_key_col] = df.apply(build_material_key, axis=1)
#
#     df[material_key_col] = df[material_key_col].astype(str).str.strip()
#
#     unknown_count = int((df[material_key_col] == "unknown_material").sum())
#
#     if unknown_count > 0:
#         print(f"警告：{df_name} 中存在 unknown_material 数量:", unknown_count)
#
#
# # =========================================================
# # 7. 找到目标列和锚点列
# # =========================================================
#
# target_col = find_first_existing_col(
#     df_data,
#     surface_candidates,
#     "Surface tension 目标"
# )
#
# print("\n目标表面张力列:", target_col)
#
# if temp_col not in df_data.columns:
#     raise ValueError(f"Data_selected 中没有找到温度列: {temp_col}")
#
# if anchor_surface_col not in df_anchor.columns:
#     raise ValueError(
#         f"锚点表中没有找到 {anchor_surface_col}。\n"
#         f"当前锚点表列名: {list(df_anchor.columns)}"
#     )
#
# anchor_y_col = anchor_surface_col
#
# print("使用表面张力锚点列:", anchor_y_col)
#
# if boiling_col not in df_anchor.columns:
#     raise ValueError(f"Interpolated_k1_k2 中没有找到沸点列: {boiling_col}")
#
# if k1_col not in df_anchor.columns and anchor_T_col not in df_anchor.columns:
#     raise ValueError(
#         f"Interpolated_k1_k2 中既没有 {k1_col}，也没有 {anchor_T_col}，无法确定 k1。"
#     )
#
#
# # =========================================================
# # 8. 识别并处理基团列
# # =========================================================
#
# group_cols_raw = identify_group_columns(
#     df_groups_raw,
#     n=n_group_features_to_use
# )
#
# print("\n识别到的候选基团列数量:", len(group_cols_raw))
# print("第一个候选基团列:", group_cols_raw[0])
# print("最后一个候选基团列:", group_cols_raw[-1])
#
# df_groups_numeric = (
#     df_groups_raw[group_cols_raw]
#     .apply(pd.to_numeric, errors="coerce")
#     .fillna(0.0)
# )
#
# nonzero_mask = df_groups_numeric.abs().sum(axis=0) != 0
# used_group_cols = df_groups_numeric.columns[nonzero_mask].tolist()
# removed_zero_group_cols = df_groups_numeric.columns[~nonzero_mask].tolist()
#
# print("删除全零基团数量:", len(removed_zero_group_cols))
# print("有效基团数量:", len(used_group_cols))
#
# if len(used_group_cols) == 0:
#     raise ValueError("有效基团数量为 0，无法建模。")
#
# df_group_features = pd.concat(
#     [
#         df_groups_raw[[material_key_col]].reset_index(drop=True),
#         df_groups_numeric[used_group_cols].reset_index(drop=True),
#     ],
#     axis=1
# )
#
# df_group_features = df_group_features.drop_duplicates(subset=[material_key_col])
#
#
# # =========================================================
# # 9. 准备锚点数据
# # =========================================================
#
# anchor_keep = [material_key_col, anchor_y_col, boiling_col]
#
# if k1_col in df_anchor.columns:
#     anchor_keep.append(k1_col)
#
# if anchor_T_col in df_anchor.columns:
#     anchor_keep.append(anchor_T_col)
#
# df_anchor_slim = (
#     df_anchor[anchor_keep]
#     .drop_duplicates(subset=[material_key_col])
#     .copy()
# )
#
# df_anchor_slim[anchor_y_col] = pd.to_numeric(
#     df_anchor_slim[anchor_y_col],
#     errors="coerce"
# )
#
# df_anchor_slim[boiling_col] = pd.to_numeric(
#     df_anchor_slim[boiling_col],
#     errors="coerce"
# )
#
# if k1_col in df_anchor_slim.columns:
#     df_anchor_slim["k1_valid"] = pd.to_numeric(
#         df_anchor_slim[k1_col],
#         errors="coerce"
#     )
# else:
#     df_anchor_slim[anchor_T_col] = pd.to_numeric(
#         df_anchor_slim[anchor_T_col],
#         errors="coerce"
#     )
#
#     df_anchor_slim["k1_valid"] = (
#         df_anchor_slim[anchor_T_col]
#         / df_anchor_slim[boiling_col]
#     )
#
# k1_median = (
#     df_anchor_slim["k1_valid"]
#     .replace([np.inf, -np.inf], np.nan)
#     .median()
# )
#
# df_anchor_slim["k1_valid"] = df_anchor_slim["k1_valid"].fillna(k1_median)
#
# valid_anchor = (
#     df_anchor_slim[anchor_y_col].notna()
#     & (df_anchor_slim[anchor_y_col] > 0)
#     & df_anchor_slim[boiling_col].notna()
#     & (df_anchor_slim[boiling_col] > 0)
#     & np.isfinite(df_anchor_slim["k1_valid"])
# )
#
# df_anchor_valid = df_anchor_slim[valid_anchor].copy()
#
# print("\n有效锚点物质数:", len(df_anchor_valid))
#
# if len(df_anchor_valid) == 0:
#     raise ValueError("没有有效锚点物质，无法训练锚点子模型。")
#
#
# # =========================================================
# # 10. 全数据训练锚点子模型
# # =========================================================
#
# df_material = df_group_features.merge(
#     df_anchor_valid,
#     on=material_key_col,
#     how="inner"
# )
#
# df_material = df_material.dropna(
#     subset=used_group_cols + [anchor_y_col, boiling_col, "k1_valid"]
# ).copy()
#
# df_material = df_material[
#     np.isfinite(df_material[anchor_y_col])
#     & np.isfinite(df_material[boiling_col])
#     & np.isfinite(df_material["k1_valid"])
#     & (df_material[anchor_y_col] > 0)
#     & (df_material[boiling_col] > 0)
# ].copy()
#
# df_material = df_material.reset_index(drop=True)
#
# print("合并基团和锚点后的物质数:", len(df_material))
#
# if len(df_material) == 0:
#     raise ValueError("合并基团和锚点后没有有效物质。")
#
# X_anchor = df_material[used_group_cols].values.astype(float)
# y_surface_anchor = df_material[anchor_y_col].values.astype(float)
# y_boiling = df_material[boiling_col].values.astype(float)
#
# anchor_surface_model = HistGradientBoostingRegressor(**hgb_params)
# anchor_boiling_model = HistGradientBoostingRegressor(**hgb_params)
#
# anchor_surface_model.fit(X_anchor, y_surface_anchor)
# anchor_boiling_model.fit(X_anchor, y_boiling)
#
# df_material["surface_anchor_pred"] = anchor_surface_model.predict(X_anchor)
# df_material["boiling_T_pred"] = anchor_boiling_model.predict(X_anchor)
# df_material["anchor_T_pred"] = df_material["k1_valid"] * df_material["boiling_T_pred"]
#
# df_material = df_material[
#     np.isfinite(df_material["surface_anchor_pred"])
#     & np.isfinite(df_material["anchor_T_pred"])
#     & (df_material["surface_anchor_pred"] > 0)
# ].copy()
#
#
# # =========================================================
# # 11. 展开温度点数据，匹配物质级锚点预测
# # =========================================================
#
# df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
# df_data[target_col] = pd.to_numeric(df_data[target_col], errors="coerce")
#
# df_long = df_data.merge(
#     df_material[
#         [material_key_col]
#         + used_group_cols
#         + ["surface_anchor_pred", "anchor_T_pred"]
#     ],
#     on=material_key_col,
#     how="inner"
# )
#
# df_long = df_long.dropna(
#     subset=[target_col, temp_col]
#     + used_group_cols
#     + ["surface_anchor_pred", "anchor_T_pred"]
# ).copy()
#
# df_long = df_long[
#     np.isfinite(df_long[target_col])
#     & np.isfinite(df_long[temp_col])
#     & np.isfinite(df_long["surface_anchor_pred"])
#     & np.isfinite(df_long["anchor_T_pred"])
#     & (df_long[target_col] > 0)
#     & (df_long["surface_anchor_pred"] > 0)
# ].copy()
#
# df_long = df_long.reset_index(drop=True)
#
# print("\n最终温度点总数:", len(df_long))
# print("最终物质数:", df_long[material_key_col].nunique())
#
# if len(df_long) == 0:
#     raise ValueError("最终温度点数据为空，无法交叉验证。")
#
#
# # =========================================================
# # 12. 提取数组
# # =========================================================
#
# X_groups = df_long[used_group_cols].values.astype(float)
# T_all = df_long[temp_col].values.astype(float)
# surface_true = df_long[target_col].values.astype(float)
# material_keys = df_long[material_key_col].values
#
# unique_materials = np.unique(material_keys)
#
# if len(unique_materials) < n_outer_folds:
#     raise ValueError(
#         f"物质数 {len(unique_materials)} 小于 n_outer_folds={n_outer_folds}，无法做 5-fold CV。"
#     )
#
#
# # =========================================================
# # 13. 方法 A：直接 GBDT 特征
# # =========================================================
#
# def build_direct_features(sample_mask):
#     """
#     方法 A：
#         groups + T_K
#     """
#     return np.hstack([
#         X_groups[sample_mask],
#         T_all[sample_mask].reshape(-1, 1),
#     ])
#
#
# # =========================================================
# # 14. 方法 B：锚点线性基线 + GBDT 残差
# # =========================================================
#
# def train_and_predict_methodB(train_mask, test_mask):
#     df_train = df_long[train_mask].copy()
#     df_test = df_long[test_mask].copy()
#
#     # -----------------------------------------------------
#     # 基线模型：
#     # Surface_base = Surface_anchor_pred
#     #                + (T - T_anchor_pred) * sum(Nk * Ak)
#     # -----------------------------------------------------
#     delta_T_train = (
#         df_train[temp_col].values
#         - df_train["anchor_T_pred"].values
#     )
#
#     X_base_train = (
#         df_train[used_group_cols].values
#         * delta_T_train.reshape(-1, 1)
#     )
#
#     y_base_train = (
#         df_train[target_col].values
#         - df_train["surface_anchor_pred"].values
#     )
#
#     valid_base = (
#         np.isfinite(X_base_train).all(axis=1)
#         & np.isfinite(y_base_train)
#     )
#
#     if valid_base.sum() == 0:
#         raise ValueError("基线模型无有效训练样本")
#
#     base_model = Ridge(alpha=1.0, fit_intercept=False)
#
#     base_model.fit(
#         X_base_train[valid_base],
#         y_base_train[valid_base]
#     )
#
#     # -----------------------------------------------------
#     # 测试集基线预测
#     # -----------------------------------------------------
#     delta_T_test = (
#         df_test[temp_col].values
#         - df_test["anchor_T_pred"].values
#     )
#
#     X_base_test = (
#         df_test[used_group_cols].values
#         * delta_T_test.reshape(-1, 1)
#     )
#
#     valid_base_test = np.isfinite(X_base_test).all(axis=1)
#
#     baseline_delta = np.full(len(df_test), np.nan)
#
#     baseline_delta[valid_base_test] = base_model.predict(
#         X_base_test[valid_base_test]
#     )
#
#     baseline_surface = (
#         df_test["surface_anchor_pred"].values
#         + baseline_delta
#     )
#
#     # -----------------------------------------------------
#     # 训练集基线预测，构造残差
#     # -----------------------------------------------------
#     baseline_delta_train = np.full(len(df_train), np.nan)
#
#     baseline_delta_train[valid_base] = base_model.predict(
#         X_base_train[valid_base]
#     )
#
#     baseline_surface_train = (
#         df_train["surface_anchor_pred"].values
#         + baseline_delta_train
#     )
#
#     residual_y_train = (
#         df_train[target_col].values
#         - baseline_surface_train
#     )
#
#     # -----------------------------------------------------
#     # 残差模型：
#     # residual = GBDT(groups + T_K)
#     # -----------------------------------------------------
#     residual_X_train = np.hstack([
#         df_train[used_group_cols].values,
#         df_train[temp_col].values.reshape(-1, 1),
#     ])
#
#     valid_res = (
#         np.isfinite(residual_X_train).all(axis=1)
#         & np.isfinite(residual_y_train)
#     )
#
#     if valid_res.sum() == 0:
#         raise ValueError("残差模型无有效训练样本")
#
#     res_model = GradientBoostingRegressor(**gbdt_params)
#
#     res_model.fit(
#         residual_X_train[valid_res],
#         residual_y_train[valid_res]
#     )
#
#     residual_X_test = np.hstack([
#         df_test[used_group_cols].values,
#         df_test[temp_col].values.reshape(-1, 1),
#     ])
#
#     valid_res_test = np.isfinite(residual_X_test).all(axis=1)
#
#     residual_pred = np.full(len(df_test), np.nan)
#
#     residual_pred[valid_res_test] = res_model.predict(
#         residual_X_test[valid_res_test]
#     )
#
#     final_surface = baseline_surface + residual_pred
#
#     return final_surface, baseline_surface, residual_pred
#
#
# # =========================================================
# # 15. 5-fold CV，按物质划分
# # =========================================================
#
# kf = KFold(
#     n_splits=n_outer_folds,
#     shuffle=True,
#     random_state=random_state
# )
#
# metrics_direct = []
# metrics_methodB = []
#
# pred_rows_direct = []
# pred_rows_methodB = []
#
# for fold, (train_idx, test_idx) in enumerate(kf.split(unique_materials), start=1):
#     print(f"\n========== Fold {fold}/{n_outer_folds} ==========")
#
#     train_materials = unique_materials[train_idx]
#     test_materials = unique_materials[test_idx]
#
#     train_mask = np.isin(material_keys, train_materials)
#     test_mask = np.isin(material_keys, test_materials)
#
#     print("训练物质数:", len(train_materials))
#     print("测试物质数:", len(test_materials))
#     print("训练点数:", int(train_mask.sum()))
#     print("测试点数:", int(test_mask.sum()))
#
#     # -----------------------------------------------------
#     # 方法 A：直接 GBDT
#     # -----------------------------------------------------
#     X_train_A = build_direct_features(train_mask)
#     y_train_A = surface_true[train_mask]
#
#     valid_A = (
#         np.isfinite(X_train_A).all(axis=1)
#         & np.isfinite(y_train_A)
#     )
#
#     X_train_A = X_train_A[valid_A]
#     y_train_A = y_train_A[valid_A]
#
#     model_A = GradientBoostingRegressor(**gbdt_params)
#     model_A.fit(X_train_A, y_train_A)
#
#     X_test_A = build_direct_features(test_mask)
#     y_test_A = surface_true[test_mask]
#
#     valid_test_A = np.isfinite(X_test_A).all(axis=1)
#
#     y_pred_A = np.full(len(y_test_A), np.nan)
#     y_pred_A[valid_test_A] = model_A.predict(X_test_A[valid_test_A])
#
#     # -----------------------------------------------------
#     # 方法 B：锚点线性基线 + 残差 GBDT
#     # -----------------------------------------------------
#     try:
#         y_pred_B, baseline_surface_B, residual_pred_B = train_and_predict_methodB(
#             train_mask,
#             test_mask
#         )
#     except Exception as e:
#         print(f"  Fold {fold} 方法B失败: {e}")
#         y_pred_B = np.full(len(y_test_A), np.nan)
#         baseline_surface_B = np.full(len(y_test_A), np.nan)
#         residual_pred_B = np.full(len(y_test_A), np.nan)
#
#     # -----------------------------------------------------
#     # 指标
#     # -----------------------------------------------------
#     m_A = compute_metrics_surface(y_test_A, y_pred_A)
#     m_B = compute_metrics_surface(y_test_A, y_pred_B)
#
#     m_A["fold"] = fold
#     m_B["fold"] = fold
#
#     metrics_direct.append(m_A)
#     metrics_methodB.append(m_B)
#
#     print(
#         "Direct GBDT | R2:",
#         f"{m_A['R2']:.10f}",
#         "MSE:",
#         f"{m_A['MSE']:.10f}",
#         "ARD%:",
#         f"{m_A['ARD_percent']:.10f}",
#     )
#
#     print(
#         "MethodB     | R2:",
#         f"{m_B['R2']:.10f}",
#         "MSE:",
#         f"{m_B['MSE']:.10f}",
#         "ARD%:",
#         f"{m_B['ARD_percent']:.10f}",
#     )
#
#     # -----------------------------------------------------
#     # 保存预测明细
#     # -----------------------------------------------------
#     df_test = df_long[test_mask].copy().reset_index(drop=True)
#
#     meta_cols = [
#         c for c in [
#             material_key_col,
#             "compound_name",
#             "cas",
#             "formula",
#             "SMILES",
#             "smiles",
#             "final_smiles",
#             "inchikey",
#             "pubchem_inchikey",
#             "boiling_T_K",
#             temp_col,
#             target_col,
#             "surface_anchor_pred",
#             "anchor_T_pred",
#         ]
#         if c in df_test.columns
#     ]
#
#     pred_A = df_test[meta_cols].copy()
#     pred_A["fold"] = fold
#     pred_A["model"] = "GBDT_direct"
#     pred_A["y_true"] = y_test_A
#     pred_A["y_pred"] = y_pred_A
#     pred_A["abs_error"] = np.abs(pred_A["y_pred"] - pred_A["y_true"])
#     pred_A["rel_error_percent"] = (
#         pred_A["abs_error"] / np.abs(pred_A["y_true"]) * 100.0
#     )
#
#     pred_B = df_test[meta_cols].copy()
#     pred_B["fold"] = fold
#     pred_B["model"] = "Anchor_linear_GBDT_residual"
#     pred_B["y_true"] = y_test_A
#     pred_B["baseline_surface"] = baseline_surface_B
#     pred_B["residual_pred"] = residual_pred_B
#     pred_B["y_pred"] = y_pred_B
#     pred_B["abs_error"] = np.abs(pred_B["y_pred"] - pred_B["y_true"])
#     pred_B["rel_error_percent"] = (
#         pred_B["abs_error"] / np.abs(pred_B["y_true"]) * 100.0
#     )
#
#     pred_rows_direct.append(pred_A)
#     pred_rows_methodB.append(pred_B)
#
#
# # =========================================================
# # 16. 汇总统计
# # =========================================================
#
# df_direct = pd.DataFrame(metrics_direct)
# df_methodB = pd.DataFrame(metrics_methodB)
#
# # 调整 fold 列到第一列
# for df_tmp in [df_direct, df_methodB]:
#     cols = ["fold"] + [c for c in df_tmp.columns if c != "fold"]
#     df_tmp = df_tmp[cols]
#
# df_direct = df_direct[["fold"] + [c for c in df_direct.columns if c != "fold"]]
# df_methodB = df_methodB[["fold"] + [c for c in df_methodB.columns if c != "fold"]]
#
# summary_direct = summarize(df_direct, "GBDT_direct (SurfaceTension)")
# summary_methodB = summarize(
#     df_methodB,
#     "Anchor+linear+GBDT_residual (SurfaceTension)"
# )
#
# summary_all = pd.concat(
#     [summary_direct, summary_methodB],
#     ignore_index=True
# )
#
# print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
# print(summary_all.to_string(index=False))
#
#
# # =========================================================
# # 17. 配对 t 检验
# # =========================================================
#
# metric_names = [c for c in df_direct.columns if c != "fold"]
#
# t_test_results = []
#
# for metric in metric_names:
#     tmp = df_direct[["fold", metric]].merge(
#         df_methodB[["fold", metric]],
#         on="fold",
#         how="inner",
#         suffixes=("_direct", "_methodB")
#     )
#
#     vals_A = pd.to_numeric(tmp[f"{metric}_direct"], errors="coerce").values
#     vals_B = pd.to_numeric(tmp[f"{metric}_methodB"], errors="coerce").values
#
#     mask = np.isfinite(vals_A) & np.isfinite(vals_B)
#
#     vals_A = vals_A[mask]
#     vals_B = vals_B[mask]
#
#     if len(vals_A) > 1 and SCIPY_AVAILABLE:
#         t_stat, p_val = ttest_rel(vals_A, vals_B)
#     else:
#         t_stat, p_val = np.nan, np.nan
#
#     mean_A = float(np.mean(vals_A)) if len(vals_A) > 0 else np.nan
#     mean_B = float(np.mean(vals_B)) if len(vals_B) > 0 else np.nan
#
#     if metric == "R2":
#         better = "methodB" if mean_B > mean_A else "direct"
#     else:
#         better = "methodB" if mean_B < mean_A else "direct"
#
#     t_test_results.append({
#         "Metric": metric,
#         "Mean_direct": mean_A,
#         "Mean_methodB": mean_B,
#         "Delta_methodB_minus_direct": mean_B - mean_A,
#         "t_stat": t_stat,
#         "p_value": p_val,
#         "Significant_p_lt_0.05": bool(p_val < 0.05) if np.isfinite(p_val) else False,
#         "Better_model": better,
#         "scipy_available": SCIPY_AVAILABLE,
#     })
#
# df_ttest = pd.DataFrame(t_test_results)
#
# print("\n========== Paired t-test ==========")
# print(df_ttest.to_string(index=False))
#
#
# # =========================================================
# # 18. 预测明细表
# # =========================================================
#
# df_pred_direct = pd.concat(pred_rows_direct, ignore_index=True)
# df_pred_methodB = pd.concat(pred_rows_methodB, ignore_index=True)
#
#
# # =========================================================
# # 19. Run Info
# # =========================================================
#
# df_used_group_cols = pd.DataFrame({
#     "used_group_col": used_group_cols
# })
#
# df_removed_zero_group_cols = pd.DataFrame({
#     "removed_zero_group_col": removed_zero_group_cols
# })
#
# run_info = pd.DataFrame([
#     {"param": "input_file", "value": str(input_file)},
#     {"param": "output_file", "value": str(output_file)},
#     {"param": "data_sheet", "value": data_sheet},
#     {"param": "groups_sheet", "value": groups_sheet},
#     {"param": "anchor_sheet", "value": anchor_sheet},
#
#     {"param": "target_col", "value": target_col},
#     {"param": "temp_col", "value": temp_col},
#     {"param": "anchor_surface_col", "value": anchor_surface_col},
#     {"param": "boiling_col", "value": boiling_col},
#     {"param": "k1_col", "value": k1_col},
#     {"param": "anchor_T_col", "value": anchor_T_col},
#
#     {"param": "n_outer_folds", "value": n_outer_folds},
#     {"param": "random_state", "value": random_state},
#
#     {"param": "n_group_features_requested", "value": n_group_features_to_use},
#     {"param": "n_group_features_raw_identified", "value": len(group_cols_raw)},
#     {"param": "n_group_features_after_remove_zero", "value": len(used_group_cols)},
#     {"param": "n_removed_zero_group_cols", "value": len(removed_zero_group_cols)},
#
#     {"param": "total_temperature_points", "value": len(surface_true)},
#     {"param": "n_materials", "value": len(unique_materials)},
#     {"param": "n_anchor_materials", "value": len(df_material)},
#
#     {"param": "direct_model", "value": "GradientBoostingRegressor(groups + T_K)"},
#     {
#         "param": "methodB_baseline",
#         "value": "Ridge(alpha=1.0, fit_intercept=False) in SurfaceTension space",
#     },
#     {
#         "param": "methodB_baseline_formula",
#         "value": "Surface_base = Surface_anchor_pred + (T - T_anchor_pred) * sum(Nk*Ak)",
#     },
#     {
#         "param": "methodB_residual_model",
#         "value": "GradientBoostingRegressor(groups + T_K), same params as direct model",
#     },
#     {
#         "param": "anchor_submodel",
#         "value": "HistGradientBoostingRegressor trained on SurfaceTension_anchor and boiling_T_K",
#     },
#     {"param": "target", "value": "Surface tension liquid-gas (N/m)"},
#
#     {"param": "hgb_params", "value": str(hgb_params)},
#     {"param": "gbdt_params", "value": str(gbdt_params)},
# ])
#
#
# # =========================================================
# # 20. 保存结果
# # =========================================================
#
# with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
#     df_direct.to_excel(writer, sheet_name="Fold_Metrics_Direct", index=False)
#     df_methodB.to_excel(writer, sheet_name="Fold_Metrics_MethodB", index=False)
#
#     summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
#     df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)
#
#     df_pred_direct.to_excel(writer, sheet_name="Predictions_Direct", index=False)
#     df_pred_methodB.to_excel(writer, sheet_name="Predictions_MethodB", index=False)
#
#     df_used_group_cols.to_excel(writer, sheet_name="Used_Group_Cols", index=False)
#     df_removed_zero_group_cols.to_excel(
#         writer,
#         sheet_name="Removed_Zero_Group_Cols",
#         index=False
#     )
#
#     run_info.to_excel(writer, sheet_name="Run_Info", index=False)
#
#     workbook = writer.book
#
#     number_format = "0.000000000000"
#
#     for sheetname in writer.sheets:
#         ws = workbook[sheetname]
#
#         for row in ws.iter_rows():
#             for cell in row:
#                 if isinstance(cell.value, float):
#                     cell.number_format = number_format
#
#         for col in ws.columns:
#             max_len = 0
#             col_letter = col[0].column_letter
#
#             for cell in col:
#                 if cell.value is not None:
#                     max_len = max(max_len, len(str(cell.value)))
#
#             ws.column_dimensions[col_letter].width = min(max_len + 2, 45)
#
#
# print(f"\n保存完成: {output_file}")
# print("\n主要输出 sheet:")
# print("- Fold_Metrics_Direct")
# print("- Fold_Metrics_MethodB")
# print("- Summary_Mean_Std")
# print("- Paired_T_Test")
# print("- Predictions_Direct")
# print("- Predictions_MethodB")
# print("- Run_Info")



# -*- coding: utf-8 -*-
"""
Surface tension liquid-gas:
GBDT_direct vs Anchor + linear baseline + GBDT residual 5-fold CV

比较模型：
    方法 A：
        GBDT_direct
        输入特征 = groups + T_K
        目标 = SurfaceTension_N_m

    方法 B：
        Anchor + linear baseline + GBDT residual

新增：
    1. 每个 fold 模型训练后，额外预测完整数据集；
    2. 对完整数据集统计相对误差 <1%、<5%、<10% 的点数；
    3. 对 5 个 fold 的完整数据集点数取平均；
    4. 保存 fold_test_predictions、fold_all_data_predictions、
       fold_all_data_count_summary、final_average_summary；
    5. 保留 baseline、residual、全局锚点子模型信息；
    6. 最后输出方便复制的三行数字。
"""

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.ensemble import GradientBoostingRegressor, HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

try:
    from scipy.stats import ttest_rel
    SCIPY_AVAILABLE = True
except Exception:
    SCIPY_AVAILABLE = False


# =========================================================
# 0. 全局显示设置
# =========================================================
pd.set_option("display.float_format", "{:.10f}".format)
np.set_printoptions(suppress=True, precision=10)


# =========================================================
# 1. 输入输出设置
# =========================================================
preferred_input_file = Path(
    "dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points_with_RSQ.xlsx"
)

fallback_input_file = Path(
    "dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points.xlsx"
)

if preferred_input_file.exists():
    input_file = preferred_input_file
elif fallback_input_file.exists():
    input_file = fallback_input_file
else:
    raise FileNotFoundError(
        "没有找到输入文件：\n"
        f"1. {preferred_input_file}\n"
        f"2. {fallback_input_file}"
    )

data_sheet = "Data_selected"
groups_sheet = "Groups_selected"
anchor_sheet = "Interpolated_k1_k2"

output_file = Path(
    "GBDT_direct_vs_anchor_baseline_residual_5fold_CV_SurfaceTension_target.xlsx"
)


# =========================================================
# 2. 基础列名设置
# =========================================================
material_key_col = "material_key"
temp_col = "T_K"

surface_candidates = [
    "SurfaceTension_N_m",
    "surface_tension_N_m",
    "Surface_Tension_N_m",
    "SurfaceTension",
    "surface_tension",
    "property_value",
]

anchor_surface_col = "SurfaceTension_N_m_interp_at_k1Tb"

boiling_col = "boiling_T_K"
k1_col = "k1"
anchor_T_col = "k1_times_boiling_T_K"

n_group_features_to_use = 220
use_fixed_group_position = True
group_start_col_1based = 3
group_end_col_1based = 222

n_outer_folds = 5
random_state = 42


# =========================================================
# 3. 模型参数
# =========================================================
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
# 4. 工具函数
# =========================================================
def is_valid_value(x):
    if pd.isna(x):
        return False

    s = str(x).strip()

    if s == "":
        return False

    if s.lower() in ["nan", "none", "null", "待定"]:
        return False

    return True


def build_material_key(row):
    for col in [
        "material_key",
        "inchikey",
        "pubchem_inchikey",
        "cas",
        "compound_name",
        "formula",
    ]:
        if col in row.index and is_valid_value(row[col]):
            if col == "material_key":
                return str(row[col]).strip()

            return f"{col}:{str(row[col]).strip()}"

    return "unknown_material"


def normalize_colname(name):
    return (
        str(name)
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
        .replace("/", "")
        .replace("(", "")
        .replace(")", "")
    )


def find_first_existing_col(df, candidates, col_type):
    lower_map = {str(c).lower(): c for c in df.columns}
    norm_map = {normalize_colname(c): c for c in df.columns}

    for col in candidates:
        if col in df.columns:
            return col

    for col in candidates:
        if str(col).lower() in lower_map:
            return lower_map[str(col).lower()]

    for col in candidates:
        key = normalize_colname(col)
        if key in norm_map:
            return norm_map[key]

    raise ValueError(
        f"没有找到 {col_type} 列。\n"
        f"候选列名: {candidates}\n"
        f"当前列名: {list(df.columns)}"
    )


def identify_group_columns(df_groups, n=220):
    if use_fixed_group_position:
        start_idx = group_start_col_1based - 1
        end_excl = group_end_col_1based

        if len(df_groups.columns) >= end_excl:
            group_cols = list(df_groups.columns[start_idx:end_excl])

            if len(group_cols) == n:
                return group_cols

        print("\n警告：固定位置基团列不可用，转为自动识别数值型基团列。")

    metadata_keywords = [
        "original_material_index",
        "material_key",
        "compound",
        "name",
        "cas",
        "formula",
        "smiles",
        "inchi",
        "inchikey",
        "pubchem",
        "phase",
        "property",
        "boiling",
        "temperature",
        "temp",
        "t_k",
        "pressure",
        "surface",
        "tension",
        "k1",
        "k2",
        "interp",
        "status",
        "range",
        "rsq",
        "slope",
        "title",
        "doi",
        "source",
        "index",
    ]

    candidate_cols = []

    for col in df_groups.columns:
        col_lower = str(col).strip().lower()

        if any(k in col_lower for k in metadata_keywords):
            continue

        num = pd.to_numeric(df_groups[col], errors="coerce")

        if num.notna().sum() > 0:
            candidate_cols.append(col)

    if len(candidate_cols) == 0:
        raise ValueError("没有识别到任何有效基团列。请检查 Groups_selected。")

    if len(candidate_cols) >= n:
        return candidate_cols[:n]

    print(
        f"\n警告：自动识别到的基团列只有 {len(candidate_cols)} 个，"
        f"少于设定的 {n} 个，将使用全部识别到的基团列。"
    )

    return candidate_cols


def safe_relative_error_percent(y_true, y_pred, eps=1e-12):
    """
    relative_error = abs((y_pred - y_true) / y_true) * 100

    对 abs(y_true) <= 1e-12 的点，relative_error 记为 NaN。
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


def average_relative_deviation(y_true, y_pred):
    rel_err = safe_relative_error_percent(y_true, y_pred)

    if np.any(np.isfinite(rel_err)):
        return float(np.nanmean(rel_err))

    return np.nan


def count_error_thresholds(y_true, y_pred):
    """
    统计相对误差 <1%、<5%、<10% 的数据点数量。
    NaN 自动忽略。

    注意：最终复制输出使用严格小于 <，不是 <=。
    """
    rel_err = safe_relative_error_percent(y_true, y_pred)

    return {
        "count_rel_err_lt_1pct": float(np.nansum(rel_err < 1.0)),
        "count_rel_err_lt_5pct": float(np.nansum(rel_err < 5.0)),
        "count_rel_err_lt_10pct": float(np.nansum(rel_err < 10.0)),
        "n_valid_for_relative_error": int(np.sum(np.isfinite(rel_err))),
    }


def compute_metrics_surface(y_true, y_pred):
    """
    表面张力预测评价指标。
    leq1%、leq5%、leq10% 为测试集相对误差 <= 阈值的比例，保留原始展示口径。
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = np.isfinite(y_true) & np.isfinite(y_pred)

    y_true_valid = y_true[mask]
    y_pred_valid = y_pred[mask]

    if len(y_true_valid) == 0:
        return {
            "n_points": 0,
            "R2": np.nan,
            "MSE": np.nan,
            "RMSE": np.nan,
            "MAE": np.nan,
            "ARD_percent": np.nan,
            "max_rel%": np.nan,
            "leq1%": np.nan,
            "leq5%": np.nan,
            "leq10%": np.nan,
            "leq1_count": 0.0,
            "leq5_count": 0.0,
            "leq10_count": 0.0,
        }

    r2 = r2_score(y_true_valid, y_pred_valid) if len(y_true_valid) >= 2 else np.nan
    mse = mean_squared_error(y_true_valid, y_pred_valid)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_true_valid, y_pred_valid)

    rel_err = safe_relative_error_percent(y_true_valid, y_pred_valid)

    if np.any(np.isfinite(rel_err)):
        ard = float(np.nanmean(rel_err))
        max_rel = float(np.nanmax(rel_err))

        le1_count = float(np.nansum(rel_err <= 1.0))
        le5_count = float(np.nansum(rel_err <= 5.0))
        le10_count = float(np.nansum(rel_err <= 10.0))

        n_valid = int(np.sum(np.isfinite(rel_err)))

        le1 = le1_count / n_valid * 100.0
        le5 = le5_count / n_valid * 100.0
        le10 = le10_count / n_valid * 100.0
    else:
        ard = np.nan
        max_rel = np.nan
        le1 = le5 = le10 = np.nan
        le1_count = le5_count = le10_count = 0.0

    return {
        "n_points": len(y_true_valid),
        "R2": r2,
        "MSE": mse,
        "RMSE": rmse,
        "MAE": mae,
        "ARD_percent": ard,
        "max_rel%": max_rel,
        "leq1%": le1,
        "leq5%": le5,
        "leq10%": le10,
        "leq1_count": le1_count,
        "leq5_count": le5_count,
        "leq10_count": le10_count,
    }


def format_metric_value(metric, value):
    if pd.isna(value):
        return "NaN"

    if metric == "MSE":
        return f"{value:.10f}"

    if metric in ["RMSE", "MAE"]:
        return f"{value:.8f}"

    if metric in ["R2", "ARD_percent", "max_rel%", "leq1%", "leq5%", "leq10%"]:
        return f"{value:.6f}"

    return f"{value:.8f}"


def summarize(df, name):
    metric_names = [c for c in df.columns if c not in ["fold"]]

    rows = []

    for metric in metric_names:
        vals = pd.to_numeric(df[metric], errors="coerce").dropna().values

        if len(vals) == 0:
            mean_val = np.nan
            std_val = np.nan
            mean_std = "NaN"

        elif len(vals) == 1:
            mean_val = float(np.mean(vals))
            std_val = np.nan
            mean_std = f"{format_metric_value(metric, mean_val)} ± NaN"

        else:
            mean_val = float(np.mean(vals))
            std_val = float(np.std(vals, ddof=1))
            mean_std = (
                f"{format_metric_value(metric, mean_val)} ± "
                f"{format_metric_value(metric, std_val)}"
            )

        rows.append({
            "Model": name,
            "Metric": metric,
            "Mean": mean_val,
            "Std": std_val,
            "Mean±Std": mean_std,
        })

    return pd.DataFrame(rows)


def format_excel(writer, number_format="0.000000000000"):
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
# 5. 读取数据
# =========================================================
xls = pd.ExcelFile(input_file)

print("输入文件:", input_file)
print("输入文件包含 sheet:")
print(xls.sheet_names)

for sheet in [data_sheet, groups_sheet, anchor_sheet]:
    if sheet not in xls.sheet_names:
        raise ValueError(f"输入文件中没有找到 sheet: {sheet}")

df_data = pd.read_excel(input_file, sheet_name=data_sheet)
df_groups_raw = pd.read_excel(input_file, sheet_name=groups_sheet)
df_anchor = pd.read_excel(input_file, sheet_name=anchor_sheet)

print("\nData_selected 行数:", len(df_data))
print("Groups_selected 物质数:", len(df_groups_raw))
print("Interpolated_k1_k2 物质数:", len(df_anchor))


# =========================================================
# 6. 准备 material_key
# =========================================================
for df_name, df in [
    ("Data_selected", df_data),
    ("Groups_selected", df_groups_raw),
    ("Interpolated_k1_k2", df_anchor),
]:
    if material_key_col not in df.columns:
        df[material_key_col] = df.apply(build_material_key, axis=1)

    df[material_key_col] = df[material_key_col].astype(str).str.strip()

    unknown_count = int((df[material_key_col] == "unknown_material").sum())

    if unknown_count > 0:
        print(f"警告：{df_name} 中存在 unknown_material 数量:", unknown_count)


# =========================================================
# 7. 找到目标列和锚点列
# =========================================================
target_col = find_first_existing_col(
    df_data,
    surface_candidates,
    "Surface tension 目标"
)

print("\n目标表面张力列:", target_col)

if temp_col not in df_data.columns:
    raise ValueError(f"Data_selected 中没有找到温度列: {temp_col}")

if anchor_surface_col not in df_anchor.columns:
    raise ValueError(
        f"锚点表中没有找到 {anchor_surface_col}。\n"
        f"当前锚点表列名: {list(df_anchor.columns)}"
    )

anchor_y_col = anchor_surface_col

print("使用表面张力锚点列:", anchor_y_col)

if boiling_col not in df_anchor.columns:
    raise ValueError(f"Interpolated_k1_k2 中没有找到沸点列: {boiling_col}")

if k1_col not in df_anchor.columns and anchor_T_col not in df_anchor.columns:
    raise ValueError(
        f"Interpolated_k1_k2 中既没有 {k1_col}，也没有 {anchor_T_col}，无法确定 k1。"
    )


# =========================================================
# 8. 识别并处理基团列
# =========================================================
group_cols_raw = identify_group_columns(
    df_groups_raw,
    n=n_group_features_to_use
)

print("\n识别到的候选基团列数量:", len(group_cols_raw))
print("第一个候选基团列:", group_cols_raw[0])
print("最后一个候选基团列:", group_cols_raw[-1])

df_groups_numeric = (
    df_groups_raw[group_cols_raw]
    .apply(pd.to_numeric, errors="coerce")
    .fillna(0.0)
)

nonzero_mask = df_groups_numeric.abs().sum(axis=0) != 0
used_group_cols = df_groups_numeric.columns[nonzero_mask].tolist()
removed_zero_group_cols = df_groups_numeric.columns[~nonzero_mask].tolist()

print("删除全零基团数量:", len(removed_zero_group_cols))
print("有效基团数量:", len(used_group_cols))

if len(used_group_cols) == 0:
    raise ValueError("有效基团数量为 0，无法建模。")

df_group_features = pd.concat(
    [
        df_groups_raw[[material_key_col]].reset_index(drop=True),
        df_groups_numeric[used_group_cols].reset_index(drop=True),
    ],
    axis=1
)

df_group_features = df_group_features.drop_duplicates(subset=[material_key_col])


# =========================================================
# 9. 准备锚点数据
# =========================================================
anchor_keep = [material_key_col, anchor_y_col, boiling_col]

if k1_col in df_anchor.columns:
    anchor_keep.append(k1_col)

if anchor_T_col in df_anchor.columns:
    anchor_keep.append(anchor_T_col)

df_anchor_slim = (
    df_anchor[anchor_keep]
    .drop_duplicates(subset=[material_key_col])
    .copy()
)

df_anchor_slim[anchor_y_col] = pd.to_numeric(
    df_anchor_slim[anchor_y_col],
    errors="coerce"
)

df_anchor_slim[boiling_col] = pd.to_numeric(
    df_anchor_slim[boiling_col],
    errors="coerce"
)

if k1_col in df_anchor_slim.columns:
    df_anchor_slim["k1_valid"] = pd.to_numeric(
        df_anchor_slim[k1_col],
        errors="coerce"
    )
else:
    df_anchor_slim[anchor_T_col] = pd.to_numeric(
        df_anchor_slim[anchor_T_col],
        errors="coerce"
    )

    df_anchor_slim["k1_valid"] = (
        df_anchor_slim[anchor_T_col]
        / df_anchor_slim[boiling_col]
    )

k1_median = (
    df_anchor_slim["k1_valid"]
    .replace([np.inf, -np.inf], np.nan)
    .median()
)

df_anchor_slim["k1_valid"] = df_anchor_slim["k1_valid"].fillna(k1_median)

valid_anchor = (
    df_anchor_slim[anchor_y_col].notna()
    & (df_anchor_slim[anchor_y_col] > 0)
    & df_anchor_slim[boiling_col].notna()
    & (df_anchor_slim[boiling_col] > 0)
    & np.isfinite(df_anchor_slim["k1_valid"])
)

df_anchor_valid = df_anchor_slim[valid_anchor].copy()

print("\n有效锚点物质数:", len(df_anchor_valid))

if len(df_anchor_valid) == 0:
    raise ValueError("没有有效锚点物质，无法训练锚点子模型。")


# =========================================================
# 10. 全数据训练锚点子模型
# =========================================================
df_material = df_group_features.merge(
    df_anchor_valid,
    on=material_key_col,
    how="inner"
)

df_material = df_material.dropna(
    subset=used_group_cols + [anchor_y_col, boiling_col, "k1_valid"]
).copy()

df_material = df_material[
    np.isfinite(df_material[anchor_y_col])
    & np.isfinite(df_material[boiling_col])
    & np.isfinite(df_material["k1_valid"])
    & (df_material[anchor_y_col] > 0)
    & (df_material[boiling_col] > 0)
].copy()

df_material = df_material.reset_index(drop=True)

print("合并基团和锚点后的物质数:", len(df_material))

if len(df_material) == 0:
    raise ValueError("合并基团和锚点后没有有效物质。")

X_anchor = df_material[used_group_cols].values.astype(float)
y_surface_anchor = df_material[anchor_y_col].values.astype(float)
y_boiling = df_material[boiling_col].values.astype(float)

anchor_surface_model = HistGradientBoostingRegressor(**hgb_params)
anchor_boiling_model = HistGradientBoostingRegressor(**hgb_params)

anchor_surface_model.fit(X_anchor, y_surface_anchor)
anchor_boiling_model.fit(X_anchor, y_boiling)

df_material["surface_anchor_pred"] = anchor_surface_model.predict(X_anchor)
df_material["boiling_T_pred"] = anchor_boiling_model.predict(X_anchor)
df_material["anchor_T_pred"] = df_material["k1_valid"] * df_material["boiling_T_pred"]

df_material = df_material[
    np.isfinite(df_material["surface_anchor_pred"])
    & np.isfinite(df_material["anchor_T_pred"])
    & (df_material["surface_anchor_pred"] > 0)
].copy()

anchor_surface_train_pred = anchor_surface_model.predict(X_anchor)
boiling_train_pred = anchor_boiling_model.predict(X_anchor)

df_submodel_summary = pd.DataFrame([
    {
        "submodel": "global_surface_anchor_model",
        "target": anchor_y_col,
        "model_type": "HistGradientBoostingRegressor",
        "params": str(hgb_params),
        "R2": r2_score(y_surface_anchor, anchor_surface_train_pred) if len(y_surface_anchor) > 1 else np.nan,
        "MSE": mean_squared_error(y_surface_anchor, anchor_surface_train_pred),
        "RMSE": np.sqrt(mean_squared_error(y_surface_anchor, anchor_surface_train_pred)),
        "MAE": mean_absolute_error(y_surface_anchor, anchor_surface_train_pred),
        "ARD_percent": average_relative_deviation(y_surface_anchor, anchor_surface_train_pred),
    },
    {
        "submodel": "global_boiling_model",
        "target": boiling_col,
        "model_type": "HistGradientBoostingRegressor",
        "params": str(hgb_params),
        "R2": r2_score(y_boiling, boiling_train_pred) if len(y_boiling) > 1 else np.nan,
        "MSE": mean_squared_error(y_boiling, boiling_train_pred),
        "RMSE": np.sqrt(mean_squared_error(y_boiling, boiling_train_pred)),
        "MAE": mean_absolute_error(y_boiling, boiling_train_pred),
        "ARD_percent": average_relative_deviation(y_boiling, boiling_train_pred),
    },
])

df_submodel_predictions = df_material[
    [
        material_key_col,
        anchor_y_col,
        boiling_col,
        "k1_valid",
        "surface_anchor_pred",
        "boiling_T_pred",
        "anchor_T_pred",
    ]
].copy()

df_submodel_predictions["surface_anchor_abs_error"] = (
    df_submodel_predictions["surface_anchor_pred"] - df_submodel_predictions[anchor_y_col]
).abs()

df_submodel_predictions["surface_anchor_relative_error_percent"] = safe_relative_error_percent(
    df_submodel_predictions[anchor_y_col].values,
    df_submodel_predictions["surface_anchor_pred"].values,
)

df_submodel_predictions["boiling_abs_error"] = (
    df_submodel_predictions["boiling_T_pred"] - df_submodel_predictions[boiling_col]
).abs()

df_submodel_predictions["boiling_relative_error_percent"] = safe_relative_error_percent(
    df_submodel_predictions[boiling_col].values,
    df_submodel_predictions["boiling_T_pred"].values,
)


# =========================================================
# 11. 展开温度点数据，匹配物质级锚点预测
# =========================================================
df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
df_data[target_col] = pd.to_numeric(df_data[target_col], errors="coerce")

df_long = df_data.merge(
    df_material[
        [material_key_col]
        + used_group_cols
        + ["surface_anchor_pred", "anchor_T_pred", "boiling_T_pred", "k1_valid"]
    ],
    on=material_key_col,
    how="inner"
)

df_long = df_long.dropna(
    subset=[target_col, temp_col]
    + used_group_cols
    + ["surface_anchor_pred", "anchor_T_pred"]
).copy()

df_long = df_long[
    np.isfinite(df_long[target_col])
    & np.isfinite(df_long[temp_col])
    & np.isfinite(df_long["surface_anchor_pred"])
    & np.isfinite(df_long["anchor_T_pred"])
    & (df_long[target_col] > 0)
    & (df_long["surface_anchor_pred"] > 0)
].copy()

df_long = df_long.reset_index(drop=True)

print("\n最终温度点总数:", len(df_long))
print("最终物质数:", df_long[material_key_col].nunique())

if len(df_long) == 0:
    raise ValueError("最终温度点数据为空，无法交叉验证。")


# =========================================================
# 12. 提取数组
# =========================================================
X_groups = df_long[used_group_cols].values.astype(float)
T_all = df_long[temp_col].values.astype(float)
surface_true = df_long[target_col].values.astype(float)
material_keys = df_long[material_key_col].values.astype(str)

surface_anchor_pred_all = df_long["surface_anchor_pred"].values.astype(float)
anchor_T_pred_all = df_long["anchor_T_pred"].values.astype(float)

unique_materials = np.unique(material_keys)
all_sample_indices = np.arange(len(surface_true))

if len(unique_materials) < n_outer_folds:
    raise ValueError(
        f"物质数 {len(unique_materials)} 小于 n_outer_folds={n_outer_folds}，无法做 5-fold CV。"
    )


# =========================================================
# 13. 方法 A：直接 GBDT 特征
# =========================================================
def build_direct_features(indices):
    indices = np.asarray(indices, dtype=int)

    return np.hstack([
        X_groups[indices],
        T_all[indices].reshape(-1, 1),
    ])


# =========================================================
# 14. 方法 B：锚点线性基线 + GBDT 残差
# =========================================================
def build_baseline_features(indices):
    indices = np.asarray(indices, dtype=int)

    delta_T = T_all[indices] - anchor_T_pred_all[indices]

    return X_groups[indices] * delta_T.reshape(-1, 1)


def build_residual_features(indices):
    indices = np.asarray(indices, dtype=int)

    return np.hstack([
        X_groups[indices],
        T_all[indices].reshape(-1, 1),
    ])


def train_methodB(train_indices):
    train_indices = np.asarray(train_indices, dtype=int)

    # -----------------------------------------------------
    # 基线模型：
    # Surface_base = Surface_anchor_pred
    #                + (T - T_anchor_pred) * sum(Nk * Ak)
    # -----------------------------------------------------
    X_base_train = build_baseline_features(train_indices)

    y_base_train = (
        surface_true[train_indices]
        - surface_anchor_pred_all[train_indices]
    )

    valid_base = (
        np.isfinite(X_base_train).all(axis=1)
        & np.isfinite(y_base_train)
    )

    if valid_base.sum() == 0:
        raise ValueError("基线模型无有效训练样本")

    base_model = Ridge(alpha=baseline_ridge_alpha, fit_intercept=False)

    base_model.fit(
        X_base_train[valid_base],
        y_base_train[valid_base]
    )

    # -----------------------------------------------------
    # 训练集基线预测，构造残差
    # -----------------------------------------------------
    base_delta_train = np.full(len(train_indices), np.nan, dtype=float)

    valid_base_full = np.isfinite(X_base_train).all(axis=1)

    base_delta_train[valid_base_full] = base_model.predict(
        X_base_train[valid_base_full]
    )

    baseline_surface_train = (
        surface_anchor_pred_all[train_indices]
        + base_delta_train
    )

    residual_y_train = (
        surface_true[train_indices]
        - baseline_surface_train
    )

    residual_X_train = build_residual_features(train_indices)

    valid_res = (
        np.isfinite(residual_X_train).all(axis=1)
        & np.isfinite(residual_y_train)
    )

    if valid_res.sum() == 0:
        raise ValueError("残差模型无有效训练样本")

    res_model = GradientBoostingRegressor(**gbdt_params)

    res_model.fit(
        residual_X_train[valid_res],
        residual_y_train[valid_res]
    )

    return base_model, res_model


def predict_methodB(indices, base_model, res_model):
    indices = np.asarray(indices, dtype=int)

    # baseline
    X_base = build_baseline_features(indices)
    baseline_delta = np.full(len(indices), np.nan, dtype=float)

    valid_base = np.isfinite(X_base).all(axis=1)

    if valid_base.sum() > 0:
        baseline_delta[valid_base] = base_model.predict(X_base[valid_base])

    baseline_surface = (
        surface_anchor_pred_all[indices]
        + baseline_delta
    )

    # residual
    residual_X = build_residual_features(indices)
    residual_pred = np.full(len(indices), np.nan, dtype=float)

    valid_res = (
        np.isfinite(residual_X).all(axis=1)
        & np.isfinite(baseline_surface)
    )

    if valid_res.sum() > 0:
        residual_pred[valid_res] = res_model.predict(residual_X[valid_res])

    final_surface = baseline_surface + residual_pred

    return final_surface, baseline_surface, residual_pred


def make_prediction_df(
    fold,
    dataset_name,
    method,
    indices,
    y_pred,
    baseline_surface=None,
    residual_pred=None,
):
    indices = np.asarray(indices, dtype=int)

    y_true = surface_true[indices]
    y_pred = np.asarray(y_pred, dtype=float)

    df_out = pd.DataFrame({
        "fold": fold,
        "dataset": dataset_name,
        "Method": method,
        "sample_index": indices,
        material_key_col: material_keys[indices],
        temp_col: T_all[indices],
        "surface_true": y_true,
        "surface_pred": y_pred,
        "error": y_pred - y_true,
        "absolute_error": np.abs(y_pred - y_true),
        "relative_error_percent": safe_relative_error_percent(y_true, y_pred),
        "surface_anchor_pred": surface_anchor_pred_all[indices],
        "anchor_T_pred": anchor_T_pred_all[indices],
        "delta_T": T_all[indices] - anchor_T_pred_all[indices],
    })

    if baseline_surface is not None:
        df_out["baseline_surface"] = baseline_surface
        df_out["baseline_error"] = baseline_surface - y_true
        df_out["baseline_relative_error_percent"] = safe_relative_error_percent(
            y_true,
            baseline_surface,
        )

    if residual_pred is not None:
        df_out["residual_pred"] = residual_pred
        if baseline_surface is not None:
            df_out["residual_target"] = y_true - baseline_surface

    meta_cols = [
        "compound_name",
        "cas",
        "formula",
        "SMILES",
        "smiles",
        "final_smiles",
        "inchikey",
        "pubchem_inchikey",
        "boiling_T_K",
        "critical_T_K",
        "phase",
    ]

    for col in meta_cols:
        if col in df_long.columns:
            df_out[col] = df_long[col].values[indices]

    return df_out


# =========================================================
# 15. 5-fold CV，按物质划分
# =========================================================
kf = KFold(
    n_splits=n_outer_folds,
    shuffle=True,
    random_state=random_state
)

metrics_direct = []
metrics_methodB = []
metrics_baseline = []
metrics_residual_model = []

fold_test_prediction_dfs = []
fold_all_data_prediction_dfs = []
fold_all_data_count_records = []
fold_info_records = []

direct_feature_importance_records = []
residual_feature_importance_records = []
baseline_param_records = []

direct_feature_names = used_group_cols + [temp_col]
residual_feature_names = used_group_cols + [temp_col]
baseline_feature_names = [f"{g}*(T-anchor_T_pred)" for g in used_group_cols]

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
    print("训练点数:", len(train_indices))
    print("测试点数:", len(test_indices))

    # -----------------------------------------------------
    # 方法 A：直接 GBDT
    # -----------------------------------------------------
    X_train_A = build_direct_features(train_indices)
    y_train_A = surface_true[train_indices]

    valid_A = (
        np.isfinite(X_train_A).all(axis=1)
        & np.isfinite(y_train_A)
    )

    model_A = GradientBoostingRegressor(**gbdt_params)
    model_A.fit(X_train_A[valid_A], y_train_A[valid_A])

    X_test_A = build_direct_features(test_indices)
    y_test_A = surface_true[test_indices]

    valid_test_A = np.isfinite(X_test_A).all(axis=1)

    y_pred_A_test = np.full(len(test_indices), np.nan, dtype=float)

    if valid_test_A.sum() > 0:
        y_pred_A_test[valid_test_A] = model_A.predict(X_test_A[valid_test_A])

    X_all_A = build_direct_features(all_sample_indices)
    y_pred_A_all = np.full(len(all_sample_indices), np.nan, dtype=float)

    valid_all_A = np.isfinite(X_all_A).all(axis=1)

    if valid_all_A.sum() > 0:
        y_pred_A_all[valid_all_A] = model_A.predict(X_all_A[valid_all_A])

    # -----------------------------------------------------
    # 方法 B：锚点线性基线 + 残差 GBDT
    # -----------------------------------------------------
    try:
        base_model, res_model = train_methodB(train_indices)

        y_pred_B_test, baseline_B_test, residual_B_test = predict_methodB(
            test_indices,
            base_model,
            res_model,
        )

        y_pred_B_all, baseline_B_all, residual_B_all = predict_methodB(
            all_sample_indices,
            base_model,
            res_model,
        )

    except Exception as e:
        print(f"  Fold {fold} 方法B失败: {e}")

        base_model = None
        res_model = None

        y_pred_B_test = np.full(len(test_indices), np.nan, dtype=float)
        baseline_B_test = np.full(len(test_indices), np.nan, dtype=float)
        residual_B_test = np.full(len(test_indices), np.nan, dtype=float)

        y_pred_B_all = np.full(len(all_sample_indices), np.nan, dtype=float)
        baseline_B_all = np.full(len(all_sample_indices), np.nan, dtype=float)
        residual_B_all = np.full(len(all_sample_indices), np.nan, dtype=float)

    # -----------------------------------------------------
    # 测试集指标
    # -----------------------------------------------------
    m_A = compute_metrics_surface(y_test_A, y_pred_A_test)
    m_B = compute_metrics_surface(y_test_A, y_pred_B_test)
    m_baseline = compute_metrics_surface(y_test_A, baseline_B_test)

    residual_target_test = y_test_A - baseline_B_test
    m_residual_model = compute_metrics_surface(residual_target_test, residual_B_test)

    m_A["fold"] = fold
    m_B["fold"] = fold
    m_baseline["fold"] = fold
    m_residual_model["fold"] = fold

    metrics_direct.append(m_A)
    metrics_methodB.append(m_B)
    metrics_baseline.append(m_baseline)
    metrics_residual_model.append(m_residual_model)

    print(
        "Direct GBDT | R2:",
        f"{m_A['R2']:.10f}",
        "MSE:",
        f"{m_A['MSE']:.10f}",
        "ARD%:",
        f"{m_A['ARD_percent']:.10f}",
    )

    print(
        "MethodB     | R2:",
        f"{m_B['R2']:.10f}",
        "MSE:",
        f"{m_B['MSE']:.10f}",
        "ARD%:",
        f"{m_B['ARD_percent']:.10f}",
    )

    print(
        "Baseline    | R2:",
        f"{m_baseline['R2']:.10f}",
        "MSE:",
        f"{m_baseline['MSE']:.10f}",
        "ARD%:",
        f"{m_baseline['ARD_percent']:.10f}",
    )

    # -----------------------------------------------------
    # 新增：每个 fold 模型预测完整数据集，并统计完整数据集偏差数量
    # -----------------------------------------------------
    count_A_all = count_error_thresholds(surface_true, y_pred_A_all)
    count_B_all = count_error_thresholds(surface_true, y_pred_B_all)

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "GBDT_direct",
        **count_A_all,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "Anchor_linear_GBDT_residual",
        **count_B_all,
    })

    print("\nDirect GBDT fold model predicts ALL data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "GBDT_direct",
        **count_A_all,
    }]).to_string(index=False))

    print("\nAnchor+linear+GBDT residual fold model predicts ALL data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "Anchor_linear_GBDT_residual",
        **count_B_all,
    }]).to_string(index=False))

    # -----------------------------------------------------
    # 保存预测明细
    # -----------------------------------------------------
    df_test_A = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="GBDT_direct",
        indices=test_indices,
        y_pred=y_pred_A_test,
    )

    df_test_B = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="Anchor_linear_GBDT_residual",
        indices=test_indices,
        y_pred=y_pred_B_test,
        baseline_surface=baseline_B_test,
        residual_pred=residual_B_test,
    )

    fold_test_prediction_dfs.append(df_test_A)
    fold_test_prediction_dfs.append(df_test_B)

    df_all_A = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="GBDT_direct",
        indices=all_sample_indices,
        y_pred=y_pred_A_all,
    )

    df_all_B = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="Anchor_linear_GBDT_residual",
        indices=all_sample_indices,
        y_pred=y_pred_B_all,
        baseline_surface=baseline_B_all,
        residual_pred=residual_B_all,
    )

    fold_all_data_prediction_dfs.append(df_all_A)
    fold_all_data_prediction_dfs.append(df_all_B)

    # -----------------------------------------------------
    # 保存特征重要性和 baseline 参数
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
                "ridge_alpha": baseline_ridge_alpha,
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
        "baseline_model_trained": base_model is not None,
        "residual_model_trained": res_model is not None,
        "anchor_submodel_training": "global_all_materials",
    })


# =========================================================
# 16. 汇总统计
# =========================================================
df_direct = pd.DataFrame(metrics_direct)
df_methodB = pd.DataFrame(metrics_methodB)
df_baseline_metrics = pd.DataFrame(metrics_baseline)
df_residual_model_metrics = pd.DataFrame(metrics_residual_model)

df_direct = df_direct[["fold"] + [c for c in df_direct.columns if c != "fold"]]
df_methodB = df_methodB[["fold"] + [c for c in df_methodB.columns if c != "fold"]]
df_baseline_metrics = df_baseline_metrics[["fold"] + [c for c in df_baseline_metrics.columns if c != "fold"]]
df_residual_model_metrics = df_residual_model_metrics[["fold"] + [c for c in df_residual_model_metrics.columns if c != "fold"]]

summary_direct = summarize(df_direct, "GBDT_direct (SurfaceTension)")
summary_methodB = summarize(
    df_methodB,
    "Anchor+linear+GBDT_residual (SurfaceTension)"
)
summary_baseline = summarize(
    df_baseline_metrics,
    "Baseline only (SurfaceTension)"
)
summary_residual_model = summarize(
    df_residual_model_metrics,
    "Residual model"
)

summary_all = pd.concat(
    [
        summary_direct,
        summary_methodB,
        summary_baseline,
        summary_residual_model,
    ],
    ignore_index=True
)

print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
print(summary_all.to_string(index=False))


# =========================================================
# 17. 配对 t 检验
# =========================================================
metric_names = [c for c in df_direct.columns if c != "fold"]

t_test_results = []

for metric in metric_names:
    tmp = df_direct[["fold", metric]].merge(
        df_methodB[["fold", metric]],
        on="fold",
        how="inner",
        suffixes=("_direct", "_methodB")
    )

    vals_A = pd.to_numeric(tmp[f"{metric}_direct"], errors="coerce").values
    vals_B = pd.to_numeric(tmp[f"{metric}_methodB"], errors="coerce").values

    mask = np.isfinite(vals_A) & np.isfinite(vals_B)

    vals_A = vals_A[mask]
    vals_B = vals_B[mask]

    if len(vals_A) > 1 and SCIPY_AVAILABLE:
        t_stat, p_val = ttest_rel(vals_A, vals_B)
    else:
        t_stat, p_val = np.nan, np.nan

    mean_A = float(np.mean(vals_A)) if len(vals_A) > 0 else np.nan
    mean_B = float(np.mean(vals_B)) if len(vals_B) > 0 else np.nan

    if metric == "R2" or metric in ["leq1%", "leq5%", "leq10%"]:
        better = "methodB" if mean_B > mean_A else "direct"
    else:
        better = "methodB" if mean_B < mean_A else "direct"

    t_test_results.append({
        "Metric": metric,
        "Mean_direct": mean_A,
        "Mean_methodB": mean_B,
        "Delta_methodB_minus_direct": mean_B - mean_A,
        "t_stat": t_stat,
        "p_value": p_val,
        "Significant_p_lt_0.05": bool(p_val < 0.05) if np.isfinite(p_val) else False,
        "Better_model": better,
        "scipy_available": SCIPY_AVAILABLE,
    })

df_ttest = pd.DataFrame(t_test_results)

print("\n========== Paired t-test ==========")
print(df_ttest.to_string(index=False))


# =========================================================
# 18. 完整数据集偏差数量统计汇总
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
        "n_all_data_points": len(surface_true),
    })

df_final_average_summary = pd.DataFrame(final_average_records)

print("\n========== Fold all-data count summary ==========")
print(df_fold_all_data_count_summary.to_string(index=False))

print("\n========== Final average all-data count summary ==========")
print(df_final_average_summary.to_string(index=False))


# =========================================================
# 19. 整理输出表
# =========================================================
df_fold_test_predictions = pd.concat(fold_test_prediction_dfs, ignore_index=True)
df_fold_all_data_predictions = pd.concat(fold_all_data_prediction_dfs, ignore_index=True)

df_pred_direct = df_fold_test_predictions[
    df_fold_test_predictions["Method"] == "GBDT_direct"
].copy()

df_pred_methodB = df_fold_test_predictions[
    df_fold_test_predictions["Method"] == "Anchor_linear_GBDT_residual"
].copy()

df_used_group_cols = pd.DataFrame({
    "used_group_col": used_group_cols
})

df_removed_zero_group_cols = pd.DataFrame({
    "removed_zero_group_col": removed_zero_group_cols
})

df_direct_feature_importance = pd.DataFrame(direct_feature_importance_records)
df_residual_feature_importance = pd.DataFrame(residual_feature_importance_records)
df_baseline_params = pd.DataFrame(baseline_param_records)
df_fold_info = pd.DataFrame(fold_info_records)

run_info = pd.DataFrame([
    {"param": "input_file", "value": str(input_file)},
    {"param": "output_file", "value": str(output_file)},
    {"param": "data_sheet", "value": data_sheet},
    {"param": "groups_sheet", "value": groups_sheet},
    {"param": "anchor_sheet", "value": anchor_sheet},

    {"param": "target_col", "value": target_col},
    {"param": "temp_col", "value": temp_col},
    {"param": "anchor_surface_col", "value": anchor_surface_col},
    {"param": "boiling_col", "value": boiling_col},
    {"param": "k1_col", "value": k1_col},
    {"param": "anchor_T_col", "value": anchor_T_col},

    {"param": "n_outer_folds", "value": n_outer_folds},
    {"param": "random_state", "value": random_state},

    {"param": "n_group_features_requested", "value": n_group_features_to_use},
    {"param": "n_group_features_raw_identified", "value": len(group_cols_raw)},
    {"param": "n_group_features_after_remove_zero", "value": len(used_group_cols)},
    {"param": "n_removed_zero_group_cols", "value": len(removed_zero_group_cols)},

    {"param": "total_temperature_points", "value": len(surface_true)},
    {"param": "n_materials", "value": len(unique_materials)},
    {"param": "n_anchor_materials", "value": len(df_material)},

    {"param": "direct_model", "value": "GradientBoostingRegressor(groups + T_K)"},
    {
        "param": "methodB_baseline",
        "value": f"Ridge(alpha={baseline_ridge_alpha}, fit_intercept=False) in SurfaceTension space",
    },
    {
        "param": "methodB_baseline_formula",
        "value": "Surface_base = Surface_anchor_pred + (T - T_anchor_pred) * sum(Nk*Ak)",
    },
    {
        "param": "methodB_residual_model",
        "value": "GradientBoostingRegressor(groups + T_K), same params as direct model",
    },
    {
        "param": "anchor_submodel",
        "value": "HistGradientBoostingRegressor trained on SurfaceTension_anchor and boiling_T_K",
    },
    {"param": "target", "value": "Surface tension liquid-gas (N/m)"},

    {"param": "hgb_params", "value": str(hgb_params)},
    {"param": "gbdt_params", "value": str(gbdt_params)},
    {
        "param": "relative_error_definition",
        "value": "abs((y_pred - y_true) / y_true) * 100; abs(y_true)<=1e-12 -> NaN",
    },
    {
        "param": "full_data_count_rule",
        "value": "Each fold model predicts the whole dataset; count rel_err <1%, <5%, <10%; then average counts over 5 folds.",
    },
])

df_model_structure = pd.DataFrame([
    {
        "项目": "预测对象",
        "内容": f"液体表面张力 sigma，目标列 {target_col}",
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
        "内容": "GBDT_direct：GradientBoostingRegressor 直接预测表面张力",
    },
    {
        "项目": "方法1输入特征",
        "内容": f"[Nk, T_K]，有效基团数 {len(used_group_cols)}，总维度 {len(used_group_cols) + 1}",
    },
    {
        "项目": "方法1模型参数",
        "内容": str(gbdt_params),
    },
    {
        "项目": "方法2",
        "内容": "Anchor_linear_GBDT_residual：全局锚点线性基线 + GBDT 残差修正",
    },
    {
        "项目": "子模型",
        "内容": "两个全局 HistGradientBoostingRegressor：一个预测 k1Tb 处表面张力锚点，一个预测沸点 Tb",
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
        "内容": "T_anchor_pred = k1_valid * boiling_T_pred",
    },
    {
        "项目": "baseline 构造",
        "内容": "Surface_base = Surface_anchor_pred + Ridge(Nk*(T - T_anchor_pred))",
    },
    {
        "项目": "baseline 模型",
        "内容": f"Ridge(alpha={baseline_ridge_alpha}, fit_intercept=False)",
    },
    {
        "项目": "residual 构造",
        "内容": "residual = Surface_true - Surface_base；residual_pred = GBDT([Nk, T_K])",
    },
    {
        "项目": "residual 模型参数",
        "内容": str(gbdt_params),
    },
    {
        "项目": "最终模型",
        "内容": "方法1为直接 GBDT；方法2为 global anchor baseline + residual GBDT",
    },
    {
        "项目": "偏差数量统计口径",
        "内容": "每个 fold 模型预测完整数据集，统计表面张力相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 取平均",
    },
])


# =========================================================
# 20. 保存结果
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_direct.to_excel(writer, sheet_name="Fold_Metrics_Direct", index=False)
    df_methodB.to_excel(writer, sheet_name="Fold_Metrics_MethodB", index=False)
    df_baseline_metrics.to_excel(writer, sheet_name="Baseline_Metrics", index=False)
    df_residual_model_metrics.to_excel(writer, sheet_name="Residual_Model_Metrics", index=False)

    summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
    df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)

    df_pred_direct.to_excel(writer, sheet_name="Predictions_Direct", index=False)
    df_pred_methodB.to_excel(writer, sheet_name="Predictions_MethodB", index=False)

    df_fold_test_predictions.to_excel(writer, sheet_name="fold_test_predictions", index=False)
    df_fold_all_data_predictions.to_excel(writer, sheet_name="fold_all_data_predictions", index=False)
    df_fold_all_data_count_summary.to_excel(writer, sheet_name="fold_all_data_count_summary", index=False)
    df_final_average_summary.to_excel(writer, sheet_name="final_average_summary", index=False)

    df_submodel_summary.to_excel(writer, sheet_name="submodel_summary", index=False)
    df_submodel_predictions.to_excel(writer, sheet_name="submodel_predictions", index=False)

    df_baseline_params.to_excel(writer, sheet_name="baseline_params", index=False)
    df_direct_feature_importance.to_excel(writer, sheet_name="direct_feature_importance", index=False)
    df_residual_feature_importance.to_excel(writer, sheet_name="residual_feature_importance", index=False)

    df_used_group_cols.to_excel(writer, sheet_name="Used_Group_Cols", index=False)
    df_removed_zero_group_cols.to_excel(
        writer,
        sheet_name="Removed_Zero_Group_Cols",
        index=False
    )

    df_fold_info.to_excel(writer, sheet_name="Fold_Info", index=False)
    run_info.to_excel(writer, sheet_name="Run_Info", index=False)
    df_model_structure.to_excel(writer, sheet_name="model_structure", index=False)

    format_excel(writer)

print(f"\n保存完成: {output_file}")
print("\n主要输出 sheet:")
print("- Fold_Metrics_Direct")
print("- Fold_Metrics_MethodB")
print("- Baseline_Metrics")
print("- Residual_Model_Metrics")
print("- Summary_Mean_Std")
print("- Paired_T_Test")
print("- Predictions_Direct")
print("- Predictions_MethodB")
print("- fold_test_predictions")
print("- fold_all_data_predictions")
print("- fold_all_data_count_summary")
print("- final_average_summary")
print("- submodel_summary")
print("- submodel_predictions")
print("- baseline_params")
print("- Run_Info")
print("- model_structure")


# =========================================================
# 21. 最终方便复制输出
# =========================================================
def get_final_counts(method_name):
    row = df_final_average_summary[
        df_final_average_summary["Method"] == method_name
    ]

    if row.empty:
        return np.nan, np.nan, np.nan

    row = row.iloc[0]

    return (
        row["mean_count_rel_err_lt_1pct"],
        row["mean_count_rel_err_lt_5pct"],
        row["mean_count_rel_err_lt_10pct"],
    )


direct_1, direct_5, direct_10 = get_final_counts("GBDT_direct")
methodB_1, methodB_5, methodB_10 = get_final_counts("Anchor_linear_GBDT_residual")

print("\n方法1 全数据预测偏差 1%，5%，10%分别为：")
print(direct_1)
print(direct_5)
print(direct_10)

print("\n方法2 全数据预测偏差 1%，5%，10%分别为：")
print(methodB_1)
print(methodB_5)
print(methodB_10)


# =========================================================
# 22. 代码结构打印
# =========================================================
print("\n========== 当前代码结构简要汇总 ==========")
print(f"预测对象：液体表面张力 sigma / {target_col}")
print(f"数据文件：{input_file}")
print(f"sheet 名称：{data_sheet}, {groups_sheet}, {anchor_sheet}")
print(f"交叉验证：{n_outer_folds}-fold KFold，按 material_key 物质划分")
print("方法1：GBDT_direct，GradientBoostingRegressor，输入 [Nk, T_K]")
print("方法2：Anchor_linear_GBDT_residual，全局锚点线性基线 + GBDT 残差修正")
print("锚点子模型：全局 HistGradientBoostingRegressor，分别预测 k1Tb 处表面张力锚点和 boiling_T")
print(f"锚点子模型参数：{hgb_params}")
print("anchor_T 构造：T_anchor_pred = k1_valid * boiling_T_pred")
print("baseline 构造：Surface_base = Surface_anchor_pred + Ridge(Nk*(T - T_anchor_pred))")
print(f"baseline 模型：Ridge(alpha={baseline_ridge_alpha}, fit_intercept=False)")
print("residual 构造：residual = Surface_true - Surface_base")
print(f"residual 模型：GradientBoostingRegressor，参数：{gbdt_params}")
print(f"方法1模型参数：{gbdt_params}")
print("方法1最终输入：[Nk, T_K]")
print("方法2最终输入：baseline 使用 Nk*(T - T_anchor_pred)，residual 使用 [Nk, T_K]")
print("偏差统计口径：每个 fold 模型预测完整数据集，统计表面张力相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 取平均")