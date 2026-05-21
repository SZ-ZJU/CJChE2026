# # -*- coding: utf-8 -*-
# """
# Surface tension liquid-gas RF 5-fold CV 对比脚本：
# 比较是否引入 slope_pred_surface_over_T 特征
#
# 输入 1：
#     dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points_with_RSQ.xlsx
#
# 如果输入 1 不存在，则自动尝试：
#     dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points.xlsx
#
# 输入 2：
#     HistGB_submodels_predict_ref_surface_Tb_and_slope.xlsx
#     sheet = slope
#
# 输出：
#     RF_surface_5fold_CV_comparison_with_slope.xlsx
#
# 比较模型：
#     模型 A：RF(groups + T_K)
#     模型 B：RF(groups + T_K + slope_pred_surface_over_T)
#
# 目标：
#     SurfaceTension_N_m
#
# 交叉验证：
#     按 material_key 做 5-fold CV。
#     即同一物质的所有温度点只能同时在训练集或测试集，避免数据泄漏。
#
# 本版修改：
#     1. 控制台输出 float 保留 10 位小数
#     2. MSE 的 mean±std 字符串保留 10 位小数
#     3. RMSE / MAE 保留 8 位小数
#     4. Excel 数值显示格式改为 12 位小数
# """
#
# import pandas as pd
# import numpy as np
# from pathlib import Path
#
# from sklearn.ensemble import RandomForestRegressor
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
# # 0. 全局显示格式
# # =========================================================
#
# pd.set_option("display.float_format", lambda x: f"{x:.10f}")
#
#
# # =========================================================
# # 1. 输入输出设置
# # =========================================================
#
# preferred_main_input_file = Path(
#     "dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points_with_RSQ.xlsx"
# )
#
# fallback_main_input_file = Path(
#     "dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points.xlsx"
# )
#
# if preferred_main_input_file.exists():
#     main_input_file = preferred_main_input_file
# elif fallback_main_input_file.exists():
#     main_input_file = fallback_main_input_file
# else:
#     raise FileNotFoundError(
#         "没有找到主输入文件：\n"
#         f"1. {preferred_main_input_file}\n"
#         f"2. {fallback_main_input_file}"
#     )
#
# slope_file = Path("HistGB_submodels_predict_ref_surface_Tb_and_slope.xlsx")
#
# output_file = Path("RF_surface_5fold_CV_comparison_with_slope.xlsx")
#
#
# # =========================================================
# # 2. sheet 名设置
# # =========================================================
#
# data_sheet = "Data_selected"
# groups_sheet = "Groups_selected"
# slope_sheet = "slope"
#
#
# # =========================================================
# # 3. 关键列名设置
# # =========================================================
#
# material_key_col = "material_key"
# temp_col = "T_K"
#
# target_candidates = [
#     "SurfaceTension_N_m",
#     "surface_tension_N_m",
#     "Surface_Tension_N_m",
#     "SurfaceTension",
#     "surface_tension",
#     "property_value",
# ]
#
# slope_col = "slope_pred_surface_over_T"
#
# # 默认尝试第 3 列到第 222 列，共 220 个基团；
# # 如果固定列位置不可用，会自动改为数值型基团列识别。
# n_group_features_to_use = 220
# use_fixed_group_position = True
# group_start_col_1based = 3
# group_end_col_1based = 222
#
# random_state = 42
# n_outer_folds = 5
#
# # "T"：使用 T_K
# # "InvT"：使用 1/T_K
# temperature_feature_mode = "T"
#
#
# # =========================================================
# # 4. RF 参数
# # =========================================================
#
# rf_params = {
#     "n_estimators": 800,
#     "max_depth": None,
#     "min_samples_split": 2,
#     "min_samples_leaf": 1,
#     "max_features": 1.0,
#     "bootstrap": True,
#     "n_jobs": -1,
#     "random_state": random_state,
# }
#
#
# # =========================================================
# # 5. 工具函数
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
#     自动构造 material_key。
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
#     从候选列名中寻找第一个存在的列，支持大小写不敏感。
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
# def average_relative_deviation(y_true, y_pred, eps=1e-12):
#     """
#     平均相对偏差，单位 %。
#     """
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#
#     mask = (
#         np.isfinite(y_true)
#         & np.isfinite(y_pred)
#         & (np.abs(y_true) > eps)
#     )
#
#     if mask.sum() == 0:
#         return np.nan
#
#     return float(
#         np.mean(
#             np.abs((y_pred[mask] - y_true[mask]) / y_true[mask])
#         ) * 100.0
#     )
#
#
# def error_band_counts(y_true, y_pred, bands=(1, 5, 10)):
#     """
#     统计相对误差在 1%、5%、10% 内的点数和比例。
#     """
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#
#     mask = (
#         np.isfinite(y_true)
#         & np.isfinite(y_pred)
#         & (np.abs(y_true) > 1e-12)
#     )
#
#     rel_err_percent = np.full_like(y_true, np.nan, dtype=float)
#
#     if mask.sum() > 0:
#         rel_err_percent[mask] = (
#             np.abs((y_pred[mask] - y_true[mask]) / y_true[mask]) * 100.0
#         )
#
#     out = {}
#
#     for b in bands:
#         valid_count = int(np.nansum(rel_err_percent <= b))
#         valid_ratio = (
#             float(valid_count / len(y_true))
#             if len(y_true) > 0
#             else np.nan
#         )
#
#         out[f"within_{b}pct_count"] = valid_count
#         out[f"within_{b}pct_ratio"] = valid_ratio
#
#     return out
#
#
# def calc_metrics(y_true, y_pred, model_name, fold=None):
#     """
#     计算 Surface tension 预测指标。
#     """
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#
#     out = {
#         "model": model_name,
#         "fold": fold,
#         "n_points": len(y_true),
#         "R2": r2_score(y_true, y_pred) if len(y_true) >= 2 else np.nan,
#         "MSE": mean_squared_error(y_true, y_pred),
#         "RMSE": np.sqrt(mean_squared_error(y_true, y_pred)),
#         "MAE": mean_absolute_error(y_true, y_pred),
#         "ARD_percent": average_relative_deviation(y_true, y_pred),
#     }
#
#     out.update(error_band_counts(y_true, y_pred))
#
#     return out
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
#         "material_key",
#         "original_material_index",
#         "compound",
#         "cas",
#         "formula",
#         "smiles",
#         "inchikey",
#         "pubchem",
#         "phase",
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
# def format_metric_value(metric, value):
#     """
#     按指标类型控制显示精度。
#     MSE 数值通常很小，所以保留更多位。
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
#     if metric in ["R2", "ARD_percent"]:
#         return f"{value:.6f}"
#
#     if "within_" in metric:
#         return f"{value:.6f}"
#
#     return f"{value:.8f}"
#
#
# def summarize_metrics(df, model_name):
#     """
#     对 5 折指标计算均值、标准差。
#     MSE 保留更多小数位。
#     """
#     metric_cols = [
#         c for c in df.columns
#         if c not in ["model", "fold", "n_points"]
#     ]
#
#     rows = []
#
#     for metric in metric_cols:
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
#             "model": model_name,
#             "metric": metric,
#             "mean": mean_val,
#             "std": std_val,
#             "mean±std": mean_std,
#         })
#
#     return pd.DataFrame(rows)
#
#
# def paired_t_test_metrics(df_no, df_with):
#     """
#     对每个折上的同一指标做配对 t 检验。
#     """
#     metric_cols = [
#         c for c in df_no.columns
#         if c not in ["model", "fold", "n_points"]
#     ]
#
#     rows = []
#
#     for metric in metric_cols:
#         tmp = df_no[["fold", metric]].merge(
#             df_with[["fold", metric]],
#             on="fold",
#             how="inner",
#             suffixes=("_no_slope", "_with_slope")
#         )
#
#         vals_no = pd.to_numeric(
#             tmp[f"{metric}_no_slope"],
#             errors="coerce"
#         ).values
#
#         vals_with = pd.to_numeric(
#             tmp[f"{metric}_with_slope"],
#             errors="coerce"
#         ).values
#
#         mask = np.isfinite(vals_no) & np.isfinite(vals_with)
#
#         vals_no = vals_no[mask]
#         vals_with = vals_with[mask]
#
#         if len(vals_no) > 1 and SCIPY_AVAILABLE:
#             t_stat, p_val = ttest_rel(vals_no, vals_with)
#         else:
#             t_stat, p_val = np.nan, np.nan
#
#         mean_no = float(np.mean(vals_no)) if len(vals_no) > 0 else np.nan
#         mean_with = float(np.mean(vals_with)) if len(vals_with) > 0 else np.nan
#
#         if "R2" in metric:
#             better_model = "with_slope" if mean_with > mean_no else "no_slope"
#         else:
#             better_model = "with_slope" if mean_with < mean_no else "no_slope"
#
#         rows.append({
#             "metric": metric,
#             "mean_no_slope": mean_no,
#             "mean_with_slope": mean_with,
#             "delta_with_minus_no": mean_with - mean_no,
#             "t_stat": t_stat,
#             "p_value": p_val,
#             "significant_p_lt_0.05": bool(p_val < 0.05) if np.isfinite(p_val) else False,
#             "better_model": better_model,
#             "scipy_available": SCIPY_AVAILABLE,
#         })
#
#     return pd.DataFrame(rows)
#
#
# # =========================================================
# # 6. 读取数据
# # =========================================================
#
# if not main_input_file.exists():
#     raise FileNotFoundError(f"没有找到主输入文件: {main_input_file}")
#
# if not slope_file.exists():
#     raise FileNotFoundError(f"没有找到 slope 文件: {slope_file}")
#
# xls_main = pd.ExcelFile(main_input_file)
# xls_slope = pd.ExcelFile(slope_file)
#
# print("主输入文件:", main_input_file)
# print("主输入文件包含 sheet:")
# print(xls_main.sheet_names)
#
# print("\nslope 文件:", slope_file)
# print("slope 文件包含 sheet:")
# print(xls_slope.sheet_names)
#
# if data_sheet not in xls_main.sheet_names:
#     raise ValueError(f"主输入文件中没有 sheet: {data_sheet}")
#
# if groups_sheet not in xls_main.sheet_names:
#     raise ValueError(f"主输入文件中没有 sheet: {groups_sheet}")
#
# if slope_sheet not in xls_slope.sheet_names:
#     raise ValueError(f"slope 文件中没有 sheet: {slope_sheet}")
#
# df_data = pd.read_excel(main_input_file, sheet_name=data_sheet)
# df_groups = pd.read_excel(main_input_file, sheet_name=groups_sheet)
# df_slope = pd.read_excel(slope_file, sheet_name=slope_sheet)
#
# print("\n原始 Data_selected 行数:", len(df_data))
# print("Groups_selected 物质数:", len(df_groups))
# print("slope sheet 行数:", len(df_slope))
#
#
# # =========================================================
# # 7. material_key 处理
# # =========================================================
#
# for df_name, df in [
#     ("Data_selected", df_data),
#     ("Groups_selected", df_groups),
#     ("slope", df_slope),
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
# # 8. 目标列、温度列、slope 列检查
# # =========================================================
#
# if temp_col not in df_data.columns:
#     raise ValueError(f"Data_selected 中没有温度列: {temp_col}")
#
# target_col = find_first_existing_col(
#     df_data,
#     target_candidates,
#     "Surface tension 目标"
# )
#
# print("\n目标列:", target_col)
# print("温度列:", temp_col)
#
# if slope_col not in df_slope.columns:
#     raise ValueError(
#         f"slope sheet 中缺少列: {slope_col}\n"
#         f"当前 slope sheet 列名: {list(df_slope.columns)}"
#     )
#
# df_slope[slope_col] = pd.to_numeric(df_slope[slope_col], errors="coerce")
#
# slope_df = (
#     df_slope[[material_key_col, slope_col]]
#     .drop_duplicates(subset=[material_key_col])
#     .copy()
# )
#
#
# # =========================================================
# # 9. 处理基团列
# # =========================================================
#
# group_cols_raw = identify_group_columns(
#     df_groups,
#     n=n_group_features_to_use
# )
#
# print("\n识别到的基团列数量:", len(group_cols_raw))
# print("第一个基团列:", group_cols_raw[0])
# print("最后一个基团列:", group_cols_raw[-1])
#
# for col in group_cols_raw:
#     df_groups[col] = pd.to_numeric(df_groups[col], errors="coerce").fillna(0.0)
#
# nonzero_group_cols = [
#     col for col in group_cols_raw
#     if not np.isclose(df_groups[col].abs().sum(), 0.0)
# ]
#
# removed_zero_group_cols = [
#     col for col in group_cols_raw
#     if col not in nonzero_group_cols
# ]
#
# print("\n删除全零基团列数量:", len(removed_zero_group_cols))
# print("有效基团列数量:", len(nonzero_group_cols))
#
# if len(nonzero_group_cols) == 0:
#     raise ValueError("有效基团列数量为 0，无法训练 RF。")
#
#
# # =========================================================
# # 10. 合并数据，构造温度点级别建模表
# # =========================================================
#
# group_features = (
#     df_groups[[material_key_col] + nonzero_group_cols]
#     .drop_duplicates(subset=[material_key_col])
#     .copy()
# )
#
# df_model = df_data.merge(
#     group_features,
#     on=material_key_col,
#     how="inner"
# )
#
# df_model = df_model.merge(
#     slope_df,
#     on=material_key_col,
#     how="left"
# )
#
# df_model[temp_col] = pd.to_numeric(df_model[temp_col], errors="coerce")
# df_model[target_col] = pd.to_numeric(df_model[target_col], errors="coerce")
#
# if temperature_feature_mode == "T":
#     temperature_feature_col = "T_K_feature"
#     df_model[temperature_feature_col] = df_model[temp_col]
# elif temperature_feature_mode == "InvT":
#     temperature_feature_col = "InvT_1_per_K"
#     df_model[temperature_feature_col] = 1.0 / df_model[temp_col]
# else:
#     raise ValueError("temperature_feature_mode 只能是 'T' 或 'InvT'。")
#
# base_features = nonzero_group_cols + [temperature_feature_col]
# features_no_slope = base_features
# features_with_slope = base_features + [slope_col]
#
# df_model_clean = df_model.dropna(
#     subset=features_with_slope + [target_col, material_key_col]
# ).copy()
#
# df_model_clean = df_model_clean[
#     np.isfinite(df_model_clean[target_col])
#     & np.isfinite(df_model_clean[temperature_feature_col])
#     & (df_model_clean[target_col] > 0)
# ].copy()
#
# print("\n========== 建模数据统计 ==========")
# print("合并后样本点数:", len(df_model))
# print("清理后样本点数:", len(df_model_clean))
# print("清理后物质数:", df_model_clean[material_key_col].nunique())
#
# missing_slope_count = int(df_model[slope_col].isna().sum())
# print("合并后 slope 缺失数据点数:", missing_slope_count)
#
# if len(df_model_clean) == 0:
#     raise ValueError("清理后没有可用于建模的数据。")
#
# unique_materials = df_model_clean[material_key_col].drop_duplicates().values
#
# if len(unique_materials) < n_outer_folds:
#     raise ValueError(
#         f"物质数 {len(unique_materials)} 小于 n_outer_folds={n_outer_folds}，"
#         f"无法做 {n_outer_folds} 折交叉验证。"
#     )
#
#
# # =========================================================
# # 11. 辅助函数：按物质列表取 X / y
# # =========================================================
#
# def get_data_for_materials(material_list, use_slope):
#     mask = df_model_clean[material_key_col].isin(material_list)
#     sub = df_model_clean[mask].copy()
#
#     if use_slope:
#         X = sub[features_with_slope].values
#     else:
#         X = sub[features_no_slope].values
#
#     y = sub[target_col].values
#
#     return X, y, sub
#
#
# # =========================================================
# # 12. 外层 5 折交叉验证
# # =========================================================
#
# kf = KFold(
#     n_splits=n_outer_folds,
#     shuffle=True,
#     random_state=random_state
# )
#
# metrics_no_slope = []
# metrics_with_slope = []
#
# pred_rows_no_slope = []
# pred_rows_with_slope = []
#
# feature_importance_no_rows = []
# feature_importance_with_rows = []
#
# for fold, (train_idx, test_idx) in enumerate(kf.split(unique_materials), start=1):
#     print(f"\n========== Fold {fold}/{n_outer_folds} ==========")
#
#     train_mats = unique_materials[train_idx]
#     test_mats = unique_materials[test_idx]
#
#     print("训练物质数:", len(train_mats))
#     print("测试物质数:", len(test_mats))
#
#     # ---------- 模型 A：无 slope ----------
#     X_train_no, y_train_no, sub_train_no = get_data_for_materials(
#         train_mats,
#         use_slope=False
#     )
#
#     X_test_no, y_test_no, sub_test_no = get_data_for_materials(
#         test_mats,
#         use_slope=False
#     )
#
#     rf_no = RandomForestRegressor(**rf_params)
#     rf_no.fit(X_train_no, y_train_no)
#
#     y_pred_no = rf_no.predict(X_test_no)
#
#     met_no = calc_metrics(
#         y_test_no,
#         y_pred_no,
#         model_name="RF_groups_T",
#         fold=fold
#     )
#
#     metrics_no_slope.append(met_no)
#
#     pred_no_cols = [
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
#         ]
#         if c in sub_test_no.columns
#     ]
#
#     pred_no = sub_test_no[pred_no_cols].copy()
#     pred_no["fold"] = fold
#     pred_no["model"] = "RF_groups_T"
#     pred_no["y_true"] = y_test_no
#     pred_no["y_pred"] = y_pred_no
#     pred_no["abs_error"] = np.abs(pred_no["y_pred"] - pred_no["y_true"])
#     pred_no["rel_error_percent"] = (
#         pred_no["abs_error"] / np.abs(pred_no["y_true"]) * 100.0
#     )
#
#     pred_rows_no_slope.append(pred_no)
#
#     for feat, imp in zip(features_no_slope, rf_no.feature_importances_):
#         feature_importance_no_rows.append({
#             "fold": fold,
#             "model": "RF_groups_T",
#             "feature": feat,
#             "importance": imp,
#         })
#
#     # ---------- 模型 B：有 slope ----------
#     X_train_with, y_train_with, sub_train_with = get_data_for_materials(
#         train_mats,
#         use_slope=True
#     )
#
#     X_test_with, y_test_with, sub_test_with = get_data_for_materials(
#         test_mats,
#         use_slope=True
#     )
#
#     rf_with = RandomForestRegressor(**rf_params)
#     rf_with.fit(X_train_with, y_train_with)
#
#     y_pred_with = rf_with.predict(X_test_with)
#
#     met_with = calc_metrics(
#         y_test_with,
#         y_pred_with,
#         model_name="RF_groups_T_slope",
#         fold=fold
#     )
#
#     metrics_with_slope.append(met_with)
#
#     pred_with_cols = [
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
#             slope_col,
#         ]
#         if c in sub_test_with.columns
#     ]
#
#     pred_with = sub_test_with[pred_with_cols].copy()
#     pred_with["fold"] = fold
#     pred_with["model"] = "RF_groups_T_slope"
#     pred_with["y_true"] = y_test_with
#     pred_with["y_pred"] = y_pred_with
#     pred_with["abs_error"] = np.abs(pred_with["y_pred"] - pred_with["y_true"])
#     pred_with["rel_error_percent"] = (
#         pred_with["abs_error"] / np.abs(pred_with["y_true"]) * 100.0
#     )
#
#     pred_rows_with_slope.append(pred_with)
#
#     for feat, imp in zip(features_with_slope, rf_with.feature_importances_):
#         feature_importance_with_rows.append({
#             "fold": fold,
#             "model": "RF_groups_T_slope",
#             "feature": feat,
#             "importance": imp,
#         })
#
#     print(
#         "Fold",
#         fold,
#         "无 slope R2:",
#         f"{met_no['R2']:.10f}",
#         "MSE:",
#         f"{met_no['MSE']:.10f}",
#         "ARD%:",
#         f"{met_no['ARD_percent']:.10f}",
#     )
#     print(
#         "Fold",
#         fold,
#         "有 slope R2:",
#         f"{met_with['R2']:.10f}",
#         "MSE:",
#         f"{met_with['MSE']:.10f}",
#         "ARD%:",
#         f"{met_with['ARD_percent']:.10f}",
#     )
#
#
# # =========================================================
# # 13. 汇总统计
# # =========================================================
#
# df_no = pd.DataFrame(metrics_no_slope)
# df_with = pd.DataFrame(metrics_with_slope)
#
# summary_no = summarize_metrics(df_no, "RF(groups + T_K)")
# summary_with = summarize_metrics(df_with, "RF(groups + T_K + slope)")
#
# summary_all = pd.concat(
#     [
#         summary_no,
#         summary_with,
#     ],
#     ignore_index=True
# )
#
# df_ttest = paired_t_test_metrics(df_no, df_with)
#
# df_pred_no = pd.concat(pred_rows_no_slope, ignore_index=True)
# df_pred_with = pd.concat(pred_rows_with_slope, ignore_index=True)
#
# df_feature_importance_no = pd.DataFrame(feature_importance_no_rows)
# df_feature_importance_with = pd.DataFrame(feature_importance_with_rows)
#
# df_feature_importance_all = pd.concat(
#     [
#         df_feature_importance_no,
#         df_feature_importance_with,
#     ],
#     ignore_index=True
# )
#
# df_feature_importance_summary = (
#     df_feature_importance_all
#     .groupby(["model", "feature"], as_index=False)
#     .agg(
#         importance_mean=("importance", "mean"),
#         importance_std=("importance", "std"),
#     )
#     .sort_values(
#         ["model", "importance_mean"],
#         ascending=[True, False]
#     )
# )
#
#
# # =========================================================
# # 14. 控制台输出
# # =========================================================
#
# print("\n========== 5-Fold CV 每折指标：无 slope ==========")
# print(df_no.to_string(index=False))
#
# print("\n========== 5-Fold CV 每折指标：有 slope ==========")
# print(df_with.to_string(index=False))
#
# print("\n========== 5-Fold CV Summary Mean ± Std ==========")
# print(summary_all.to_string(index=False))
#
# print("\n========== Paired t-test ==========")
# print(df_ttest.to_string(index=False))
#
# print("\n========== slope 特征重要性 ==========")
# slope_importance = df_feature_importance_summary[
#     df_feature_importance_summary["feature"] == slope_col
# ].copy()
#
# if len(slope_importance) > 0:
#     print(slope_importance.to_string(index=False))
# else:
#     print("没有找到 slope 特征重要性。")
#
#
# # =========================================================
# # 15. 保存 Excel
# # =========================================================
#
# run_info = pd.DataFrame([
#     {"item": "main_input_file", "value": str(main_input_file)},
#     {"item": "slope_file", "value": str(slope_file)},
#     {"item": "output_file", "value": str(output_file)},
#
#     {"item": "data_sheet", "value": data_sheet},
#     {"item": "groups_sheet", "value": groups_sheet},
#     {"item": "slope_sheet", "value": slope_sheet},
#
#     {"item": "target_col", "value": target_col},
#     {"item": "temp_col", "value": temp_col},
#     {"item": "temperature_feature_mode", "value": temperature_feature_mode},
#     {"item": "temperature_feature_col", "value": temperature_feature_col},
#     {"item": "slope_col", "value": slope_col},
#
#     {"item": "n_outer_folds", "value": n_outer_folds},
#     {"item": "random_state", "value": random_state},
#     {"item": "rf_params", "value": str(rf_params)},
#
#     {"item": "n_group_features_requested", "value": n_group_features_to_use},
#     {"item": "n_group_features_raw_identified", "value": len(group_cols_raw)},
#     {"item": "n_group_features_after_remove_zero", "value": len(nonzero_group_cols)},
#     {"item": "n_removed_zero_group_cols", "value": len(removed_zero_group_cols)},
#
#     {"item": "total_samples_after_clean", "value": len(df_model_clean)},
#     {"item": "n_materials_after_clean", "value": len(unique_materials)},
#
#     {"item": "model_no_slope_features", "value": "groups + T_K"},
#     {"item": "model_with_slope_features", "value": "groups + T_K + slope_pred_surface_over_T"},
#     {"item": "cv_split_level", "value": "material_key"},
#     {"item": "display_float_format", "value": "10 decimal places in console"},
#     {"item": "excel_float_format", "value": "12 decimal places"},
# ])
#
# df_used_group_cols = pd.DataFrame({
#     "used_group_col": nonzero_group_cols
# })
#
# df_removed_zero_group_cols = pd.DataFrame({
#     "removed_zero_group_col": removed_zero_group_cols
# })
#
# with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
#     df_no.to_excel(writer, sheet_name="Fold_Metrics_No_Slope", index=False)
#     df_with.to_excel(writer, sheet_name="Fold_Metrics_With_Slope", index=False)
#
#     summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
#     df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)
#
#     df_pred_no.to_excel(writer, sheet_name="Predictions_No_Slope", index=False)
#     df_pred_with.to_excel(writer, sheet_name="Predictions_With_Slope", index=False)
#
#     df_feature_importance_summary.to_excel(
#         writer,
#         sheet_name="Feature_Importance_Summary",
#         index=False
#     )
#
#     df_feature_importance_all.to_excel(
#         writer,
#         sheet_name="Feature_Importance_AllFolds",
#         index=False
#     )
#
#     df_used_group_cols.to_excel(writer, sheet_name="Used_Group_Cols", index=False)
#
#     df_removed_zero_group_cols.to_excel(
#         writer,
#         sheet_name="Removed_Zero_Group_Cols",
#         index=False
#     )
#
#     run_info.to_excel(writer, sheet_name="Run_Info", index=False)
#
#     number_format = "0.000000000000"
#
#     for sheet_name in writer.sheets:
#         ws = writer.sheets[sheet_name]
#
#         for row in ws.iter_rows():
#             for cell in row:
#                 if isinstance(cell.value, float):
#                     cell.number_format = number_format
#
#         for col_cells in ws.columns:
#             max_length = 0
#             col_letter = col_cells[0].column_letter
#
#             for cell in col_cells:
#                 if cell.value is not None:
#                     max_length = max(max_length, len(str(cell.value)))
#
#             ws.column_dimensions[col_letter].width = min(max_length + 2, 45)
#
#
# print("\n保存完成:", output_file)
# print("主要输出 sheet:")
# print("- Fold_Metrics_No_Slope：每折无 slope 模型指标")
# print("- Fold_Metrics_With_Slope：每折有 slope 模型指标")
# print("- Summary_Mean_Std：均值 ± 标准差汇总")
# print("- Paired_T_Test：配对 t 检验结果")
# print("- Predictions_No_Slope：无 slope 每个测试点预测结果")
# print("- Predictions_With_Slope：有 slope 每个测试点预测结果")
# print("- Feature_Importance_Summary：特征重要性汇总")
# print("\n重点查看 slope 特征重要性:")
# print(slope_col)



# -*- coding: utf-8 -*-
"""
Surface tension liquid-gas RF 5-fold CV 对比脚本：
比较是否引入 slope_pred_surface_over_T 特征

模型 A：RF(groups + T_K)
模型 B：RF(groups + T_K + slope_pred_surface_over_T)

新增：
    1. 每个 fold 模型预测完整数据集；
    2. 统计完整数据集相对误差 <1%、<5%、<10% 点数；
    3. 对 5 个 fold 的完整数据集点数取平均；
    4. 保存测试集预测、完整数据集预测、完整数据集偏差数量汇总；
    5. 最后输出方便复制的三行数字。
"""

import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

try:
    from scipy.stats import ttest_rel
    SCIPY_AVAILABLE = True
except Exception:
    SCIPY_AVAILABLE = False


# =========================================================
# 0. 全局显示格式
# =========================================================
pd.set_option("display.float_format", lambda x: f"{x:.10f}")
np.set_printoptions(suppress=True, precision=10)


# =========================================================
# 1. 输入输出设置
# =========================================================
preferred_main_input_file = Path(
    "dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points_with_RSQ.xlsx"
)

fallback_main_input_file = Path(
    "dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points.xlsx"
)

if preferred_main_input_file.exists():
    main_input_file = preferred_main_input_file
elif fallback_main_input_file.exists():
    main_input_file = fallback_main_input_file
else:
    raise FileNotFoundError(
        "没有找到主输入文件：\n"
        f"1. {preferred_main_input_file}\n"
        f"2. {fallback_main_input_file}"
    )

slope_file = Path("HistGB_submodels_predict_ref_surface_Tb_and_slope.xlsx")

output_file = Path("RF_surface_5fold_CV_comparison_with_slope.xlsx")


# =========================================================
# 2. sheet 名设置
# =========================================================
data_sheet = "Data_selected"
groups_sheet = "Groups_selected"
slope_sheet = "slope"


# =========================================================
# 3. 关键列名设置
# =========================================================
material_key_col = "material_key"
temp_col = "T_K"

target_candidates = [
    "SurfaceTension_N_m",
    "surface_tension_N_m",
    "Surface_Tension_N_m",
    "SurfaceTension",
    "surface_tension",
    "property_value",
]

slope_col = "slope_pred_surface_over_T"

n_group_features_to_use = 220
use_fixed_group_position = True
group_start_col_1based = 3
group_end_col_1based = 222

random_state = 42
n_outer_folds = 5

# "T"：使用 T_K
# "InvT"：使用 1/T_K
temperature_feature_mode = "T"


# =========================================================
# 4. RF 参数
# =========================================================
rf_params = {
    "n_estimators": 800,
    "max_depth": None,
    "min_samples_split": 2,
    "min_samples_leaf": 1,
    "max_features": 1.0,
    "bootstrap": True,
    "n_jobs": -1,
    "random_state": random_state,
}


# =========================================================
# 5. 工具函数
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


def safe_relative_error_percent(y_true, y_pred, eps=1e-12):
    """
    relative_error = abs((y_pred - y_true) / y_true) * 100

    对 abs(y_true) <= 1e-12 的点，relative_error 记为 NaN。
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    rel_err_percent = np.full_like(y_true, np.nan, dtype=float)

    mask = (
        np.isfinite(y_true)
        & np.isfinite(y_pred)
        & (np.abs(y_true) > eps)
    )

    rel_err_percent[mask] = (
        np.abs((y_pred[mask] - y_true[mask]) / y_true[mask]) * 100.0
    )

    return rel_err_percent


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


def error_band_counts(y_true, y_pred, bands=(1, 5, 10)):
    """
    保留原始代码的 <= 统计口径，用于测试集指标展示。
    最终复制输出使用 count_error_thresholds 的严格 <。
    """
    rel_err_percent = safe_relative_error_percent(y_true, y_pred)

    out = {}

    for b in bands:
        valid_count = float(np.nansum(rel_err_percent <= b))
        n_valid = int(np.sum(np.isfinite(rel_err_percent)))

        valid_ratio = (
            float(valid_count / n_valid)
            if n_valid > 0
            else np.nan
        )

        out[f"within_{b}pct_count"] = valid_count
        out[f"within_{b}pct_ratio"] = valid_ratio

    out["n_valid_relative_error"] = int(np.sum(np.isfinite(rel_err_percent)))

    return out


def calc_metrics(y_true, y_pred, model_name, fold=None):
    """
    计算 Surface tension 预测指标。
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = np.isfinite(y_true) & np.isfinite(y_pred)

    y_true_valid = y_true[mask]
    y_pred_valid = y_pred[mask]

    if len(y_true_valid) == 0:
        out = {
            "model": model_name,
            "fold": fold,
            "n_points": 0,
            "R2": np.nan,
            "MSE": np.nan,
            "RMSE": np.nan,
            "MAE": np.nan,
            "ARD_percent": np.nan,
            "max_rel_err_percent": np.nan,
        }

        out.update({
            "within_1pct_count": 0.0,
            "within_1pct_ratio": np.nan,
            "within_5pct_count": 0.0,
            "within_5pct_ratio": np.nan,
            "within_10pct_count": 0.0,
            "within_10pct_ratio": np.nan,
            "n_valid_relative_error": 0,
        })

        return out

    rel_err = safe_relative_error_percent(y_true_valid, y_pred_valid)

    if np.any(np.isfinite(rel_err)):
        max_rel = float(np.nanmax(rel_err))
    else:
        max_rel = np.nan

    out = {
        "model": model_name,
        "fold": fold,
        "n_points": len(y_true_valid),
        "R2": r2_score(y_true_valid, y_pred_valid) if len(y_true_valid) >= 2 else np.nan,
        "MSE": mean_squared_error(y_true_valid, y_pred_valid),
        "RMSE": np.sqrt(mean_squared_error(y_true_valid, y_pred_valid)),
        "MAE": mean_absolute_error(y_true_valid, y_pred_valid),
        "ARD_percent": average_relative_deviation(y_true_valid, y_pred_valid),
        "max_rel_err_percent": max_rel,
    }

    out.update(error_band_counts(y_true_valid, y_pred_valid))

    return out


def identify_group_columns(df_groups, n=220):
    """
    识别基团列。

    优先固定读取第 3 列到第 222 列，共 220 个基团。
    如果固定位置不可用，自动识别数值型基团列，并排除明显元信息列。
    """
    if use_fixed_group_position:
        start_idx = group_start_col_1based - 1
        end_excl = group_end_col_1based

        if len(df_groups.columns) >= end_excl:
            group_cols = list(df_groups.columns[start_idx:end_excl])

            if len(group_cols) == n:
                return group_cols

        print("\n警告：固定位置基团列不可用，转为自动识别数值型基团列。")

    metadata_keywords = [
        "material_key",
        "original_material_index",
        "compound",
        "cas",
        "formula",
        "smiles",
        "inchikey",
        "pubchem",
        "phase",
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


def format_metric_value(metric, value):
    if pd.isna(value):
        return "NaN"

    if metric == "MSE":
        return f"{value:.10f}"

    if metric in ["RMSE", "MAE"]:
        return f"{value:.8f}"

    if metric in ["R2", "ARD_percent", "max_rel_err_percent"]:
        return f"{value:.6f}"

    if "within_" in metric:
        return f"{value:.6f}"

    return f"{value:.8f}"


def summarize_metrics(df, model_name):
    metric_cols = [
        c for c in df.columns
        if c not in ["model", "fold", "n_points"]
    ]

    rows = []

    for metric in metric_cols:
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
            "model": model_name,
            "metric": metric,
            "mean": mean_val,
            "std": std_val,
            "mean±std": mean_std,
        })

    return pd.DataFrame(rows)


def paired_t_test_metrics(df_no, df_with):
    metric_cols = [
        c for c in df_no.columns
        if c not in ["model", "fold", "n_points"]
    ]

    rows = []

    for metric in metric_cols:
        tmp = df_no[["fold", metric]].merge(
            df_with[["fold", metric]],
            on="fold",
            how="inner",
            suffixes=("_no_slope", "_with_slope")
        )

        vals_no = pd.to_numeric(
            tmp[f"{metric}_no_slope"],
            errors="coerce"
        ).values

        vals_with = pd.to_numeric(
            tmp[f"{metric}_with_slope"],
            errors="coerce"
        ).values

        mask = np.isfinite(vals_no) & np.isfinite(vals_with)

        vals_no = vals_no[mask]
        vals_with = vals_with[mask]

        if len(vals_no) > 1 and SCIPY_AVAILABLE:
            t_stat, p_val = ttest_rel(vals_no, vals_with)
        else:
            t_stat, p_val = np.nan, np.nan

        mean_no = float(np.mean(vals_no)) if len(vals_no) > 0 else np.nan
        mean_with = float(np.mean(vals_with)) if len(vals_with) > 0 else np.nan

        if "R2" in metric or "within_" in metric:
            better_model = "with_slope" if mean_with > mean_no else "no_slope"
        else:
            better_model = "with_slope" if mean_with < mean_no else "no_slope"

        rows.append({
            "metric": metric,
            "mean_no_slope": mean_no,
            "mean_with_slope": mean_with,
            "delta_with_minus_no": mean_with - mean_no,
            "t_stat": t_stat,
            "p_value": p_val,
            "significant_p_lt_0.05": bool(p_val < 0.05) if np.isfinite(p_val) else False,
            "better_model": better_model,
            "scipy_available": SCIPY_AVAILABLE,
        })

    return pd.DataFrame(rows)


def make_prediction_df(fold, dataset_name, method, sub_df, y_true, y_pred):
    sub_df = sub_df.copy().reset_index(drop=True)

    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    df_out = sub_df.copy()

    df_out.insert(0, "fold", fold)
    df_out.insert(1, "dataset", dataset_name)
    df_out.insert(2, "Method", method)

    df_out["surface_true"] = y_true
    df_out["surface_pred"] = y_pred
    df_out["error"] = y_pred - y_true
    df_out["absolute_error"] = np.abs(y_pred - y_true)
    df_out["relative_error_percent"] = safe_relative_error_percent(y_true, y_pred)

    front_cols = [
        "fold",
        "dataset",
        "Method",
        material_key_col,
        "compound_name",
        "cas",
        "formula",
        "SMILES",
        "smiles",
        "final_smiles",
        "inchikey",
        "pubchem_inchikey",
        "boiling_T_K",
        temp_col,
        temperature_feature_col,
        target_col,
        slope_col,
        "surface_true",
        "surface_pred",
        "error",
        "absolute_error",
        "relative_error_percent",
    ]

    front_cols = [c for c in front_cols if c in df_out.columns]
    other_cols = [c for c in df_out.columns if c not in front_cols]

    return df_out[front_cols + other_cols]


def format_excel(writer, number_format="0.000000000000"):
    for sheet_name in writer.sheets:
        ws = writer.sheets[sheet_name]

        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, float):
                    cell.number_format = number_format

        for col_cells in ws.columns:
            max_length = 0
            col_letter = col_cells[0].column_letter

            for cell in col_cells:
                if cell.value is not None:
                    max_length = max(max_length, len(str(cell.value)))

            ws.column_dimensions[col_letter].width = min(max_length + 2, 60)


# =========================================================
# 6. 读取数据
# =========================================================
if not main_input_file.exists():
    raise FileNotFoundError(f"没有找到主输入文件: {main_input_file}")

if not slope_file.exists():
    raise FileNotFoundError(f"没有找到 slope 文件: {slope_file}")

xls_main = pd.ExcelFile(main_input_file)
xls_slope = pd.ExcelFile(slope_file)

print("主输入文件:", main_input_file)
print("主输入文件包含 sheet:")
print(xls_main.sheet_names)

print("\nslope 文件:", slope_file)
print("slope 文件包含 sheet:")
print(xls_slope.sheet_names)

if data_sheet not in xls_main.sheet_names:
    raise ValueError(f"主输入文件中没有 sheet: {data_sheet}")

if groups_sheet not in xls_main.sheet_names:
    raise ValueError(f"主输入文件中没有 sheet: {groups_sheet}")

if slope_sheet not in xls_slope.sheet_names:
    raise ValueError(f"slope 文件中没有 sheet: {slope_sheet}")

df_data = pd.read_excel(main_input_file, sheet_name=data_sheet)
df_groups = pd.read_excel(main_input_file, sheet_name=groups_sheet)
df_slope = pd.read_excel(slope_file, sheet_name=slope_sheet)

print("\n原始 Data_selected 行数:", len(df_data))
print("Groups_selected 物质数:", len(df_groups))
print("slope sheet 行数:", len(df_slope))


# =========================================================
# 7. material_key 处理
# =========================================================
for df_name, df in [
    ("Data_selected", df_data),
    ("Groups_selected", df_groups),
    ("slope", df_slope),
]:
    if material_key_col not in df.columns:
        df[material_key_col] = df.apply(build_material_key, axis=1)

    df[material_key_col] = df[material_key_col].astype(str).str.strip()

    unknown_count = int((df[material_key_col] == "unknown_material").sum())

    if unknown_count > 0:
        print(f"警告：{df_name} 中存在 unknown_material 数量:", unknown_count)


# =========================================================
# 8. 目标列、温度列、slope 列检查
# =========================================================
if temp_col not in df_data.columns:
    raise ValueError(f"Data_selected 中没有温度列: {temp_col}")

target_col = find_first_existing_col(
    df_data,
    target_candidates,
    "Surface tension 目标"
)

print("\n目标列:", target_col)
print("温度列:", temp_col)

if slope_col not in df_slope.columns:
    raise ValueError(
        f"slope sheet 中缺少列: {slope_col}\n"
        f"当前 slope sheet 列名: {list(df_slope.columns)}"
    )

df_slope[slope_col] = pd.to_numeric(df_slope[slope_col], errors="coerce")

slope_df = (
    df_slope[[material_key_col, slope_col]]
    .drop_duplicates(subset=[material_key_col])
    .copy()
)


# =========================================================
# 9. 处理基团列
# =========================================================
group_cols_raw = identify_group_columns(
    df_groups,
    n=n_group_features_to_use
)

print("\n识别到的基团列数量:", len(group_cols_raw))
print("第一个基团列:", group_cols_raw[0])
print("最后一个基团列:", group_cols_raw[-1])

for col in group_cols_raw:
    df_groups[col] = pd.to_numeric(df_groups[col], errors="coerce").fillna(0.0)

nonzero_group_cols = [
    col for col in group_cols_raw
    if not np.isclose(df_groups[col].abs().sum(), 0.0)
]

removed_zero_group_cols = [
    col for col in group_cols_raw
    if col not in nonzero_group_cols
]

print("\n删除全零基团列数量:", len(removed_zero_group_cols))
print("有效基团列数量:", len(nonzero_group_cols))

if len(nonzero_group_cols) == 0:
    raise ValueError("有效基团列数量为 0，无法训练 RF。")


# =========================================================
# 10. 合并数据，构造温度点级别建模表
# =========================================================
group_features = (
    df_groups[[material_key_col] + nonzero_group_cols]
    .drop_duplicates(subset=[material_key_col])
    .copy()
)

df_model = df_data.merge(
    group_features,
    on=material_key_col,
    how="inner"
)

df_model = df_model.merge(
    slope_df,
    on=material_key_col,
    how="left"
)

df_model[temp_col] = pd.to_numeric(df_model[temp_col], errors="coerce")
df_model[target_col] = pd.to_numeric(df_model[target_col], errors="coerce")
df_model[slope_col] = pd.to_numeric(df_model[slope_col], errors="coerce")

if temperature_feature_mode == "T":
    temperature_feature_col = "T_K_feature"
    df_model[temperature_feature_col] = df_model[temp_col]
elif temperature_feature_mode == "InvT":
    temperature_feature_col = "InvT_1_per_K"
    df_model[temperature_feature_col] = 1.0 / df_model[temp_col]
else:
    raise ValueError("temperature_feature_mode 只能是 'T' 或 'InvT'。")

base_features = nonzero_group_cols + [temperature_feature_col]
features_no_slope = base_features
features_with_slope = base_features + [slope_col]

df_model_clean = df_model.dropna(
    subset=features_with_slope + [target_col, material_key_col]
).copy()

df_model_clean = df_model_clean[
    np.isfinite(df_model_clean[target_col])
    & np.isfinite(df_model_clean[temperature_feature_col])
    & (df_model_clean[target_col] > 0)
].copy()

df_model_clean = df_model_clean.reset_index(drop=True)

print("\n========== 建模数据统计 ==========")
print("合并后样本点数:", len(df_model))
print("清理后样本点数:", len(df_model_clean))
print("清理后物质数:", df_model_clean[material_key_col].nunique())

missing_slope_count = int(df_model[slope_col].isna().sum())
print("合并后 slope 缺失数据点数:", missing_slope_count)

if len(df_model_clean) == 0:
    raise ValueError("清理后没有可用于建模的数据。")

unique_materials = df_model_clean[material_key_col].drop_duplicates().values

if len(unique_materials) < n_outer_folds:
    raise ValueError(
        f"物质数 {len(unique_materials)} 小于 n_outer_folds={n_outer_folds}，"
        f"无法做 {n_outer_folds} 折交叉验证。"
    )


# =========================================================
# 11. 辅助函数：按物质列表取 X / y
# =========================================================
def get_data_for_materials(material_list, use_slope):
    mask = df_model_clean[material_key_col].isin(material_list)
    sub = df_model_clean[mask].copy()

    if use_slope:
        X = sub[features_with_slope].values.astype(float)
    else:
        X = sub[features_no_slope].values.astype(float)

    y = sub[target_col].values.astype(float)

    return X, y, sub


def get_all_data(use_slope):
    if use_slope:
        X = df_model_clean[features_with_slope].values.astype(float)
    else:
        X = df_model_clean[features_no_slope].values.astype(float)

    y = df_model_clean[target_col].values.astype(float)
    sub = df_model_clean.copy()

    return X, y, sub


# =========================================================
# 12. 外层 5 折交叉验证
# =========================================================
kf = KFold(
    n_splits=n_outer_folds,
    shuffle=True,
    random_state=random_state
)

metrics_no_slope = []
metrics_with_slope = []

fold_test_prediction_dfs = []
fold_all_data_prediction_dfs = []
fold_all_data_count_records = []
fold_info_records = []

feature_importance_no_rows = []
feature_importance_with_rows = []

for fold, (train_idx, test_idx) in enumerate(kf.split(unique_materials), start=1):
    print(f"\n========== Fold {fold}/{n_outer_folds} ==========")

    train_mats = unique_materials[train_idx]
    test_mats = unique_materials[test_idx]

    print("训练物质数:", len(train_mats))
    print("测试物质数:", len(test_mats))

    # ---------- 模型 A：无 slope ----------
    X_train_no, y_train_no, sub_train_no = get_data_for_materials(
        train_mats,
        use_slope=False
    )

    X_test_no, y_test_no, sub_test_no = get_data_for_materials(
        test_mats,
        use_slope=False
    )

    X_all_no, y_all_no, sub_all_no = get_all_data(use_slope=False)

    rf_no = RandomForestRegressor(**rf_params)
    rf_no.fit(X_train_no, y_train_no)

    y_pred_no_test = rf_no.predict(X_test_no)
    y_pred_no_all = rf_no.predict(X_all_no)

    met_no = calc_metrics(
        y_test_no,
        y_pred_no_test,
        model_name="RF_groups_T",
        fold=fold
    )

    metrics_no_slope.append(met_no)

    count_no_all = count_error_thresholds(y_all_no, y_pred_no_all)

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "RF_groups_T",
        **count_no_all,
    })

    # ---------- 模型 B：有 slope ----------
    X_train_with, y_train_with, sub_train_with = get_data_for_materials(
        train_mats,
        use_slope=True
    )

    X_test_with, y_test_with, sub_test_with = get_data_for_materials(
        test_mats,
        use_slope=True
    )

    X_all_with, y_all_with, sub_all_with = get_all_data(use_slope=True)

    rf_with = RandomForestRegressor(**rf_params)
    rf_with.fit(X_train_with, y_train_with)

    y_pred_with_test = rf_with.predict(X_test_with)
    y_pred_with_all = rf_with.predict(X_all_with)

    met_with = calc_metrics(
        y_test_with,
        y_pred_with_test,
        model_name="RF_groups_T_slope",
        fold=fold
    )

    metrics_with_slope.append(met_with)

    count_with_all = count_error_thresholds(y_all_with, y_pred_with_all)

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "RF_groups_T_slope",
        **count_with_all,
    })

    # ---------- 预测明细 ----------
    df_test_no = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="RF_groups_T",
        sub_df=sub_test_no,
        y_true=y_test_no,
        y_pred=y_pred_no_test,
    )

    df_test_with = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="RF_groups_T_slope",
        sub_df=sub_test_with,
        y_true=y_test_with,
        y_pred=y_pred_with_test,
    )

    fold_test_prediction_dfs.append(df_test_no)
    fold_test_prediction_dfs.append(df_test_with)

    df_all_no = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="RF_groups_T",
        sub_df=sub_all_no,
        y_true=y_all_no,
        y_pred=y_pred_no_all,
    )

    df_all_with = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="RF_groups_T_slope",
        sub_df=sub_all_with,
        y_true=y_all_with,
        y_pred=y_pred_with_all,
    )

    fold_all_data_prediction_dfs.append(df_all_no)
    fold_all_data_prediction_dfs.append(df_all_with)

    # ---------- 特征重要性 ----------
    for feat, imp in zip(features_no_slope, rf_no.feature_importances_):
        feature_importance_no_rows.append({
            "fold": fold,
            "model": "RF_groups_T",
            "feature": feat,
            "importance": imp,
        })

    for feat, imp in zip(features_with_slope, rf_with.feature_importances_):
        feature_importance_with_rows.append({
            "fold": fold,
            "model": "RF_groups_T_slope",
            "feature": feat,
            "importance": imp,
        })

    fold_info_records.append({
        "fold": fold,
        "n_train_materials": len(train_mats),
        "n_test_materials": len(test_mats),
        "n_train_points_no_slope": len(y_train_no),
        "n_test_points_no_slope": len(y_test_no),
        "n_train_points_with_slope": len(y_train_with),
        "n_test_points_with_slope": len(y_test_with),
        "n_all_points": len(y_all_no),
        "n_features_no_slope": X_train_no.shape[1],
        "n_features_with_slope": X_train_with.shape[1],
    })

    print(
        "Fold",
        fold,
        "无 slope R2:",
        f"{met_no['R2']:.10f}",
        "MSE:",
        f"{met_no['MSE']:.10f}",
        "ARD%:",
        f"{met_no['ARD_percent']:.10f}",
    )

    print(
        "Fold",
        fold,
        "有 slope R2:",
        f"{met_with['R2']:.10f}",
        "MSE:",
        f"{met_with['MSE']:.10f}",
        "ARD%:",
        f"{met_with['ARD_percent']:.10f}",
    )

    print("\nRF(groups+T) fold model predicts ALL data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "RF_groups_T",
        **count_no_all,
    }]).to_string(index=False))

    print("\nRF(groups+T+slope) fold model predicts ALL data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "RF_groups_T_slope",
        **count_with_all,
    }]).to_string(index=False))


# =========================================================
# 13. 汇总统计
# =========================================================
df_no = pd.DataFrame(metrics_no_slope)
df_with = pd.DataFrame(metrics_with_slope)

summary_no = summarize_metrics(df_no, "RF(groups + T_K)")
summary_with = summarize_metrics(df_with, "RF(groups + T_K + slope)")
summary_all = pd.concat([summary_no, summary_with], ignore_index=True)

df_ttest = paired_t_test_metrics(df_no, df_with)

df_fold_test_predictions = pd.concat(fold_test_prediction_dfs, ignore_index=True)
df_fold_all_data_predictions = pd.concat(fold_all_data_prediction_dfs, ignore_index=True)

df_feature_importance_no = pd.DataFrame(feature_importance_no_rows)
df_feature_importance_with = pd.DataFrame(feature_importance_with_rows)

df_feature_importance_all = pd.concat(
    [df_feature_importance_no, df_feature_importance_with],
    ignore_index=True
)

df_feature_importance_summary = (
    df_feature_importance_all
    .groupby(["model", "feature"], as_index=False)
    .agg(
        importance_mean=("importance", "mean"),
        importance_std=("importance", "std"),
    )
    .sort_values(["model", "importance_mean"], ascending=[True, False])
)

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
        "n_all_data_points": len(df_model_clean),
    })

df_final_average_summary = pd.DataFrame(final_average_records)

df_fold_info = pd.DataFrame(fold_info_records)


# =========================================================
# 14. 控制台输出
# =========================================================
print("\n========== 5-Fold CV 每折指标：无 slope ==========")
print(df_no.to_string(index=False))

print("\n========== 5-Fold CV 每折指标：有 slope ==========")
print(df_with.to_string(index=False))

print("\n========== 5-Fold CV Summary Mean ± Std ==========")
print(summary_all.to_string(index=False))

print("\n========== Paired t-test ==========")
print(df_ttest.to_string(index=False))

print("\n========== Fold all-data count summary ==========")
print(df_fold_all_data_count_summary.to_string(index=False))

print("\n========== Final average all-data count summary ==========")
print(df_final_average_summary.to_string(index=False))

print("\n========== slope 特征重要性 ==========")
slope_importance = df_feature_importance_summary[
    df_feature_importance_summary["feature"] == slope_col
].copy()

if len(slope_importance) > 0:
    print(slope_importance.to_string(index=False))
else:
    print("没有找到 slope 特征重要性。")


# =========================================================
# 15. 保存 Excel
# =========================================================
run_info = pd.DataFrame([
    {"item": "main_input_file", "value": str(main_input_file)},
    {"item": "slope_file", "value": str(slope_file)},
    {"item": "output_file", "value": str(output_file)},

    {"item": "data_sheet", "value": data_sheet},
    {"item": "groups_sheet", "value": groups_sheet},
    {"item": "slope_sheet", "value": slope_sheet},

    {"item": "target_col", "value": target_col},
    {"item": "temp_col", "value": temp_col},
    {"item": "temperature_feature_mode", "value": temperature_feature_mode},
    {"item": "temperature_feature_col", "value": temperature_feature_col},
    {"item": "slope_col", "value": slope_col},

    {"item": "n_outer_folds", "value": n_outer_folds},
    {"item": "random_state", "value": random_state},
    {"item": "rf_params", "value": str(rf_params)},

    {"item": "n_group_features_requested", "value": n_group_features_to_use},
    {"item": "n_group_features_raw_identified", "value": len(group_cols_raw)},
    {"item": "n_group_features_after_remove_zero", "value": len(nonzero_group_cols)},
    {"item": "n_removed_zero_group_cols", "value": len(removed_zero_group_cols)},

    {"item": "total_samples_after_clean", "value": len(df_model_clean)},
    {"item": "n_materials_after_clean", "value": len(unique_materials)},

    {"item": "model_no_slope_features", "value": "groups + T_K"},
    {"item": "model_with_slope_features", "value": "groups + T_K + slope_pred_surface_over_T"},
    {"item": "cv_split_level", "value": "material_key"},
    {
        "item": "relative_error_definition",
        "value": "abs((y_pred - y_true) / y_true) * 100; abs(y_true)<=1e-12 -> NaN",
    },
    {
        "item": "full_data_count_rule",
        "value": "Each fold model predicts the whole dataset; count rel_err <1%, <5%, <10%; then average counts over 5 folds.",
    },
    {"item": "display_float_format", "value": "10 decimal places in console"},
    {"item": "excel_float_format", "value": "12 decimal places"},
])

df_used_group_cols = pd.DataFrame({
    "used_group_col": nonzero_group_cols
})

df_removed_zero_group_cols = pd.DataFrame({
    "removed_zero_group_col": removed_zero_group_cols
})

df_model_structure = pd.DataFrame([
    {
        "项目": "预测对象",
        "内容": f"液体表面张力 sigma，目标列 {target_col}",
    },
    {
        "项目": "数据文件",
        "内容": str(main_input_file),
    },
    {
        "项目": "slope 文件",
        "内容": str(slope_file),
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
        "项目": "slope sheet",
        "内容": slope_sheet,
    },
    {
        "项目": "交叉验证方式",
        "内容": f"{n_outer_folds}-fold KFold，按 material_key 物质划分，shuffle=True，random_state={random_state}",
    },
    {
        "项目": "方法1",
        "内容": "RF_groups_T：RandomForestRegressor，输入 [Nk, T_K]",
    },
    {
        "项目": "方法2",
        "内容": "RF_groups_T_slope：RandomForestRegressor，输入 [Nk, T_K, slope_pred_surface_over_T]",
    },
    {
        "项目": "是否包含子模型",
        "内容": "当前代码不训练子模型；读取外部 HistGB 子模型预测得到的 slope",
    },
    {
        "项目": "子模型预测对象",
        "内容": "slope_pred_surface_over_T，用作方法2额外输入特征",
    },
    {
        "项目": "子模型类型",
        "内容": "外部文件名显示为 HistGB；本代码只读取预测结果，不在当前脚本内训练",
    },
    {
        "项目": "子模型参数",
        "内容": "当前代码无法从 slope 文件恢复；仅保存 slope 预测结果和 slope 特征重要性",
    },
    {
        "项目": "slope 构造",
        "内容": "直接读取 slope_pred_surface_over_T，作为方法2额外输入特征；不再乘以 T",
    },
    {
        "项目": "baseline 构造",
        "内容": "无 baseline + residual 结构；两个方法均为直接 RF 回归",
    },
    {
        "项目": "residual 构造",
        "内容": "无",
    },
    {
        "项目": "最终模型类型",
        "内容": "RandomForestRegressor",
    },
    {
        "项目": "最终模型参数",
        "内容": str(rf_params),
    },
    {
        "项目": "方法1最终输入",
        "内容": f"[{len(nonzero_group_cols)} 个 Nk, T_K]，总维度 {len(nonzero_group_cols) + 1}",
    },
    {
        "项目": "方法2最终输入",
        "内容": f"[{len(nonzero_group_cols)} 个 Nk, T_K, slope_pred_surface_over_T]，总维度 {len(nonzero_group_cols) + 2}",
    },
    {
        "项目": "偏差数量统计口径",
        "内容": "每个 fold 模型预测完整数据集，统计表面张力相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 取平均",
    },
])

with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    # 原有核心输出
    df_no.to_excel(writer, sheet_name="Fold_Metrics_No_Slope", index=False)
    df_with.to_excel(writer, sheet_name="Fold_Metrics_With_Slope", index=False)

    summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
    df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)

    # 新增预测明细和完整数据统计
    df_fold_test_predictions.to_excel(writer, sheet_name="fold_test_predictions", index=False)
    df_fold_all_data_predictions.to_excel(writer, sheet_name="fold_all_data_predictions", index=False)
    df_fold_all_data_count_summary.to_excel(writer, sheet_name="fold_all_data_count_summary", index=False)
    df_final_average_summary.to_excel(writer, sheet_name="final_average_summary", index=False)

    # 保留原预测输出命名，方便兼容旧习惯
    df_fold_test_predictions[
        df_fold_test_predictions["Method"] == "RF_groups_T"
    ].to_excel(writer, sheet_name="Predictions_No_Slope", index=False)

    df_fold_test_predictions[
        df_fold_test_predictions["Method"] == "RF_groups_T_slope"
    ].to_excel(writer, sheet_name="Predictions_With_Slope", index=False)

    # 特征重要性
    df_feature_importance_summary.to_excel(
        writer,
        sheet_name="Feature_Importance_Summary",
        index=False
    )

    df_feature_importance_all.to_excel(
        writer,
        sheet_name="Feature_Importance_AllFolds",
        index=False
    )

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

print("\n保存完成:", output_file)
print("主要输出 sheet:")
print("- Fold_Metrics_No_Slope：每折无 slope 模型指标")
print("- Fold_Metrics_With_Slope：每折有 slope 模型指标")
print("- Summary_Mean_Std：均值 ± 标准差汇总")
print("- Paired_T_Test：配对 t 检验结果")
print("- fold_test_predictions：每折测试集预测结果")
print("- fold_all_data_predictions：每折模型预测完整数据集结果")
print("- fold_all_data_count_summary：每折完整数据集偏差数量")
print("- final_average_summary：完整数据集偏差数量 5-fold 平均")
print("- Feature_Importance_Summary：特征重要性汇总")
print("\n重点查看 slope 特征重要性:")
print(slope_col)


# =========================================================
# 16. 最终方便复制输出
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


no_1, no_5, no_10 = get_final_counts("RF_groups_T")
with_1, with_5, with_10 = get_final_counts("RF_groups_T_slope")

print("\n方法1 全数据预测偏差 1%，5%，10%分别为：")
print(no_1)
print(no_5)
print(no_10)

print("\n方法2 全数据预测偏差 1%，5%，10%分别为：")
print(with_1)
print(with_5)
print(with_10)


# =========================================================
# 17. 代码结构打印
# =========================================================
print("\n========== 当前代码结构简要汇总 ==========")
print(f"预测对象：液体表面张力 sigma / {target_col}")
print(f"主数据文件：{main_input_file}")
print(f"slope 文件：{slope_file}")
print(f"sheet 名称：{data_sheet}, {groups_sheet}, {slope_sheet}")
print(f"交叉验证：{n_outer_folds}-fold KFold，按 material_key 物质划分")
print("方法1：RF_groups_T，RandomForestRegressor，输入 [Nk, T_K]")
print("方法2：RF_groups_T_slope，RandomForestRegressor，输入 [Nk, T_K, slope_pred_surface_over_T]")
print("子模型：当前代码不训练子模型，读取外部 HistGB 预测的 slope_pred_surface_over_T")
print(f"子模型预测列：{slope_col}")
print("子模型参数：当前代码无法从 slope 文件恢复，仅保存 slope 预测结果和 slope 特征重要性")
print("slope 构造：直接读取 slope_pred_surface_over_T，作为方法2额外输入特征；没有乘以 T")
print("baseline 构造：无")
print("residual 模型：无")
print(f"最终模型：RandomForestRegressor，参数：{rf_params}")
print("方法1最终输入：[Nk, T_K]")
print("方法2最终输入：[Nk, T_K, slope_pred_surface_over_T]")
print("偏差统计口径：每个 fold 模型预测完整数据集，统计表面张力相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 取平均")