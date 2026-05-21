# # -*- coding: utf-8 -*-
# """
# Surface tension liquid-gas:
# QSPR 25 descriptors + T_K vs QSPR 25 descriptors + T_K + slope
# Random Forest 5-fold CV comparison
#
# 输入 1：
#     selected_descriptors_with_surface_mean_target.xlsx
#     sheet:
#         Selected_Features_Target
#         Selected_Features
#
# 输入 2：
#     dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points_with_RSQ.xlsx
#     或：
#     dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points.xlsx
#     sheet:
#         Data_selected
#
# 输入 3：
#     HistGB_submodels_predict_ref_surface_Tb_and_slope.xlsx
#     或：
#     HistGB_submodels_predict_ref_surface_Tb_and_slope.xls
#     sheet:
#         slope
#
# 比较模型：
#     模型 A：RF(desc + T_K)
#     模型 B：RF(desc + T_K + slope_pred_surface_over_T)
#
# 目标：
#     SurfaceTension_N_m
#
# 输出：
#     RF_surface_QSPR25_5fold_CV_comparison_with_slope.xlsx
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
# pd.set_option("display.float_format", "{:.10f}".format)
# np.set_printoptions(suppress=True, precision=10)
#
#
# # =========================================================
# # 0. 全局设置
# # =========================================================
#
# descriptor_file = Path("selected_descriptors_with_surface_mean_target.xlsx")
# descriptor_sheet = "Selected_Features_Target"
# selected_feature_sheet = "Selected_Features"
#
# preferred_data_file = Path(
#     "dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points_with_RSQ.xlsx"
# )
#
# fallback_data_file = Path(
#     "dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points.xlsx"
# )
#
# if preferred_data_file.exists():
#     data_file = preferred_data_file
# elif fallback_data_file.exists():
#     data_file = fallback_data_file
# else:
#     raise FileNotFoundError(
#         "没有找到表面张力数据文件：\n"
#         f"1. {preferred_data_file}\n"
#         f"2. {fallback_data_file}"
#     )
#
# data_sheet = "Data_selected"
#
# slope_file = Path("HistGB_submodels_predict_ref_surface_Tb_and_slope.xlsx")
# slope_sheet_candidates = ["slope", "Slope", "Predicted_Slope"]
# slope_col_candidates = [
#     "slope_pred_surface_over_T",
#     "slope_pred_Surface_over_T",
#     "slope_pred_surface_tension_over_T",
# ]
#
# output_file = Path("RF_surface_QSPR25_5fold_CV_comparison_with_slope.xlsx")
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
#     "Surface tension liquid-gas, N/m",
#     "Surface tension liquid-gas",
#     "property_value",
# ]
#
# n_outer_folds = 5
# random_state = 42
#
# rf_params = {
#     "n_estimators": 500,
#     "max_depth": None,
#     "min_samples_split": 2,
#     "min_samples_leaf": 1,
#     "max_features": "sqrt",
#     "bootstrap": True,
#     "random_state": random_state,
#     "n_jobs": -1,
# }
#
#
# # =========================================================
# # 1. 辅助函数
# # =========================================================
#
# def normalize_colname(name):
#     return (
#         str(name)
#         .lower()
#         .replace(" ", "")
#         .replace("_", "")
#         .replace("-", "")
#         .replace("(", "")
#         .replace(")", "")
#         .replace("/", "")
#         .replace(".", "")
#         .replace(",", "")
#     )
#
#
# def find_first_existing_col(df, candidates, required=True, col_type="列"):
#     norm_map = {normalize_colname(c): c for c in df.columns}
#
#     for c in candidates:
#         key = normalize_colname(c)
#         if key in norm_map:
#             return norm_map[key]
#
#     if required:
#         raise ValueError(
#             f"没有找到 {col_type}。\n"
#             f"候选列名: {candidates}\n"
#             f"当前列名: {list(df.columns)}"
#         )
#
#     return None
#
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
# def clean_key_value(x):
#     """
#     清理物质 ID：
#         123.0 -> '123'
#         其他字符串保留。
#     """
#     if not is_valid_value(x):
#         return np.nan
#
#     s = str(x).strip()
#
#     try:
#         f = float(s)
#
#         if np.isfinite(f) and abs(f - round(f)) < 1e-8:
#             return str(int(round(f)))
#
#     except Exception:
#         pass
#
#     return s
#
#
# def find_alignment_key(df_desc, df_data):
#     """
#     描述符表与 Data_selected 的对齐键。
#     """
#     candidate_pairs = [
#         ("material_key", "material_key"),
#         ("original_material_index", "original_material_index"),
#
#         ("pubchem_cid", "pubchem_cid"),
#         ("pubchem_cid_for_Tb", "pubchem_cid_for_Tb"),
#         ("CID", "pubchem_cid"),
#         ("CID_int", "pubchem_cid"),
#         ("sdf_pubchem_cid", "pubchem_cid"),
#
#         ("inchikey", "inchikey"),
#         ("InChIKey", "InChIKey"),
#         ("pubchem_inchikey", "pubchem_inchikey"),
#         ("inchikey_from_rdkit", "inchikey"),
#
#         ("cas", "cas"),
#         ("compound_name", "compound_name"),
#     ]
#
#     for dcol, dacol in candidate_pairs:
#         if dcol in df_desc.columns and dacol in df_data.columns:
#             return dcol, dacol
#
#     return None, None
#
#
# def choose_data_group_key(df_data):
#     for col in [
#         "material_key",
#         "original_material_index",
#         "pubchem_cid",
#         "pubchem_cid_for_Tb",
#         "CID",
#         "CID_int",
#         "inchikey",
#         "InChIKey",
#         "pubchem_inchikey",
#         "cas",
#         "compound_name",
#     ]:
#         if col in df_data.columns:
#             return col
#
#     return None
#
#
# def find_slope_key(df_slope, preferred_data_key_col):
#     if preferred_data_key_col is not None and preferred_data_key_col in df_slope.columns:
#         return preferred_data_key_col
#
#     for col in [
#         "material_key",
#         "original_material_index",
#         "pubchem_cid",
#         "pubchem_cid_for_Tb",
#         "CID",
#         "CID_int",
#         "sdf_pubchem_cid",
#         "inchikey",
#         "InChIKey",
#         "pubchem_inchikey",
#         "cas",
#         "compound_name",
#     ]:
#         if col in df_slope.columns:
#             return col
#
#     return None
#
#
# def read_slope_file(slope_path, sheet_candidates):
#     """
#     读取 slope 文件。
#     如果 .xlsx 不存在，自动尝试 .xls。
#     如果 .xls 不存在，自动尝试 .xlsx。
#     """
#     if not slope_path.exists():
#         if slope_path.suffix.lower() == ".xlsx":
#             alt = slope_path.with_suffix(".xls")
#         else:
#             alt = slope_path.with_suffix(".xlsx")
#
#         if alt.exists():
#             slope_path = alt
#         else:
#             raise FileNotFoundError(
#                 f"未找到 slope 文件: {slope_path}\n"
#                 f"也未找到备用文件: {alt}"
#             )
#
#     xls = pd.ExcelFile(slope_path)
#
#     sheet = None
#
#     for s in sheet_candidates:
#         if s in xls.sheet_names:
#             sheet = s
#             break
#
#     if sheet is None:
#         sheet = xls.sheet_names[0]
#
#     df = pd.read_excel(slope_path, sheet_name=sheet)
#
#     return df, slope_path, sheet
#
#
# def calc_metrics_surface(y_true, y_pred):
#     """
#     表面张力空间指标。
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
#             "leq1%": np.nan,
#             "leq5%": np.nan,
#             "leq10%": np.nan,
#             "max_rel%": np.nan,
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
#         le1 = np.mean(rel_err <= 1.0) * 100.0
#         le5 = np.mean(rel_err <= 5.0) * 100.0
#         le10 = np.mean(rel_err <= 10.0) * 100.0
#         max_rel = np.max(rel_err)
#     else:
#         ard = np.nan
#         le1 = np.nan
#         le5 = np.nan
#         le10 = np.nan
#         max_rel = np.nan
#
#     return {
#         "R2": r2,
#         "MSE": mse,
#         "RMSE": rmse,
#         "MAE": mae,
#         "ARD_percent": ard,
#         "leq1%": le1,
#         "leq5%": le5,
#         "leq10%": le10,
#         "max_rel%": max_rel,
#     }
#
#
# def format_metric_value(metric, value):
#     if pd.isna(value):
#         return "NaN"
#
#     if metric == "MSE":
#         return f"{value:.12f}"
#
#     if metric in ["RMSE", "MAE"]:
#         return f"{value:.10f}"
#
#     return f"{value:.6f}"
#
#
# def summarize(df, name):
#     metric_names = [c for c in df.columns if c != "fold"]
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
# # 2. 读取数据
# # =========================================================
#
# if not descriptor_file.exists():
#     raise FileNotFoundError(
#         f"没有找到描述符文件: {descriptor_file}\n"
#         "请先运行 25 个描述符筛选代码。"
#     )
#
# if not data_file.exists():
#     raise FileNotFoundError(f"没有找到表面张力数据文件: {data_file}")
#
# df_desc = pd.read_excel(descriptor_file, sheet_name=descriptor_sheet)
# df_data = pd.read_excel(data_file, sheet_name=data_sheet)
# df_slope, slope_path_used, slope_sheet_used = read_slope_file(
#     slope_file,
#     slope_sheet_candidates,
# )
#
# print("描述符表行数:", len(df_desc))
# print("原始数据行数:", len(df_data))
# print("Slope 表行数:", len(df_slope))
# print("Slope 文件:", slope_path_used)
# print("Slope sheet:", slope_sheet_used)
#
#
# # =========================================================
# # 3. 确定物质 ID 列
# # =========================================================
#
# desc_key_col, data_key_col = find_alignment_key(df_desc, df_data)
# data_group_col = choose_data_group_key(df_data)
# slope_key_col = find_slope_key(df_slope, data_key_col)
#
# print("\n物质对齐方式:")
# print("  desc_key_col:", desc_key_col)
# print("  data_key_col:", data_key_col)
# print("  data_group_col:", data_group_col)
# print("  slope_key_col:", slope_key_col)
#
# if slope_key_col is None:
#     raise ValueError("无法在 slope 表中找到物质 ID 列。")
#
#
# # =========================================================
# # 4. 读取 25 个描述符列表
# # =========================================================
#
# xls_desc = pd.ExcelFile(descriptor_file)
#
# if selected_feature_sheet in xls_desc.sheet_names:
#     df_selected = pd.read_excel(descriptor_file, sheet_name=selected_feature_sheet)
#
#     if "selected_feature" in df_selected.columns:
#         feature_cols = df_selected["selected_feature"].dropna().astype(str).tolist()
#     else:
#         feature_cols = df_selected.iloc[:, 0].dropna().astype(str).tolist()
#
# else:
#     meta = [
#         "material_index",
#         "original_material_index",
#         "material_key",
#         "compound_name",
#         "cas",
#         "formula",
#         "SMILES",
#         "smiles",
#         "final_smiles",
#         "inchikey",
#         "InChIKey",
#         "pubchem_inchikey",
#         "pubchem_cid",
#         "pubchem_cid_for_Tb",
#         "CID",
#         "CID_int",
#         "phase",
#         "boiling_T_K",
#         "T_min",
#         "T_max",
#         "T_range",
#         "n_points",
#         "target_n_valid_points",
#         "target_min_surface",
#         "target_max_surface",
#         "target_mean_surface",
#         "RSQ_Surface_vs_T",
#         "slope_Surface_vs_T",
#         "intercept_Surface_vs_T",
#         "RSQ_Surface_vs_invT",
#         "RSQ_lnSurface_vs_T",
#         "fit_status",
#         "slope_direction_Surface_vs_T",
#     ]
#
#     feature_cols = [c for c in df_desc.columns if c not in meta]
#
# missing_features = [c for c in feature_cols if c not in df_desc.columns]
#
# if len(missing_features) > 0:
#     raise ValueError(
#         "以下选中描述符不在描述符表中：\n"
#         f"{missing_features}"
#     )
#
# print("\n原始选中描述符数量:", len(feature_cols))
#
#
# # =========================================================
# # 5. 数值化描述符，删除无效列
# # =========================================================
#
# df_feature_raw = df_desc[feature_cols].copy()
#
# df_features = df_feature_raw.apply(
#     pd.to_numeric,
#     errors="coerce"
# )
#
# df_features = df_features.replace([np.inf, -np.inf], np.nan)
#
# # 均值填充
# df_features = df_features.fillna(df_features.mean())
#
# # 如果仍有 NaN，删除该列
# df_features = df_features.dropna(axis=1, how="any")
#
# # 删除全零列
# nonzero = df_features.abs().sum(axis=0) != 0
#
# used_feature_cols = df_features.columns[nonzero].tolist()
#
# print("有效描述符数量:", len(used_feature_cols))
#
# if len(used_feature_cols) == 0:
#     raise ValueError("没有有效描述符可用于建模。")
#
#
# # =========================================================
# # 6. 找到温度列、目标列、斜率列
# # =========================================================
#
# temp_col_actual = find_first_existing_col(
#     df_data,
#     [temp_col, "T_K", "Temperature", "temperature"],
#     required=True,
#     col_type="温度列",
# )
#
# target_col = find_first_existing_col(
#     df_data,
#     target_candidates,
#     required=True,
#     col_type="表面张力目标列",
# )
#
# slope_col = find_first_existing_col(
#     df_slope,
#     slope_col_candidates,
#     required=True,
#     col_type="斜率列",
# )
#
# print("\n温度列:", temp_col_actual)
# print("目标列:", target_col)
# print("斜率列:", slope_col)
#
# df_data[temp_col_actual] = pd.to_numeric(df_data[temp_col_actual], errors="coerce")
# df_data[target_col] = pd.to_numeric(df_data[target_col], errors="coerce")
# df_slope[slope_col] = pd.to_numeric(df_slope[slope_col], errors="coerce")
#
#
# # =========================================================
# # 7. 合并数据，构造按物质展开的特征矩阵
# # =========================================================
#
# X_no_slope = []
# X_with_slope = []
# y = []
# material_ids = []
# row_meta = []
#
# # ---------- 7.1 优先使用公共 ID 对齐 ----------
# if desc_key_col is not None and data_key_col is not None:
#     df_desc_work = df_desc.copy()
#     df_data_work = df_data.copy()
#     df_slope_work = df_slope.copy()
#
#     df_desc_work["_key"] = df_desc_work[desc_key_col].apply(clean_key_value)
#     df_data_work["_key"] = df_data_work[data_key_col].apply(clean_key_value)
#     df_slope_work["_key"] = df_slope_work[slope_key_col].apply(clean_key_value)
#
#     df_desc_work = df_desc_work.dropna(subset=["_key"]).copy()
#     df_data_work = df_data_work.dropna(subset=["_key"]).copy()
#     df_slope_work = df_slope_work.dropna(subset=["_key"]).copy()
#
#     df_desc_work = df_desc_work.drop_duplicates(subset=["_key"], keep="first")
#     df_slope_work = df_slope_work.drop_duplicates(subset=["_key"], keep="first")
#
#     # 同步描述符数值列
#     df_desc_work[used_feature_cols] = df_features.loc[df_desc_work.index, used_feature_cols].values
#
#     desc_map = {
#         row["_key"]: row[used_feature_cols].values.astype(float)
#         for _, row in df_desc_work.iterrows()
#     }
#
#     slope_map = (
#         df_slope_work
#         .set_index("_key")[slope_col]
#         .to_dict()
#     )
#
#     data_keys_in_order = df_data_work["_key"].drop_duplicates().tolist()
#
#     valid_keys = [
#         k for k in data_keys_in_order
#         if k in desc_map
#         and k in slope_map
#         and np.isfinite(slope_map[k])
#     ]
#
#     if len(valid_keys) == 0:
#         raise ValueError("没有同时拥有描述符、数据点和有效 slope 的物质。")
#
#     print("\n同时拥有描述符、数据点和 slope 的物质数:", len(valid_keys))
#
#     for key in valid_keys:
#         desc = np.asarray(desc_map[key], dtype=float)
#         slope_val = float(slope_map[key])
#
#         sub = df_data_work[df_data_work["_key"] == key].copy()
#
#         for _, row in sub.iterrows():
#             T = row[temp_col_actual]
#             yv = row[target_col]
#
#             if not (
#                 np.isfinite(T)
#                 and np.isfinite(yv)
#                 and yv > 0
#             ):
#                 continue
#
#             # 表面张力使用 T_K，不使用 1/T
#             X_no_slope.append(
#                 np.concatenate([desc, [T]])
#             )
#
#             X_with_slope.append(
#                 np.concatenate([desc, [T, slope_val]])
#             )
#
#             y.append(yv)
#             material_ids.append(key)
#
#             meta = {
#                 "_key": key,
#                 temp_col_actual: T,
#                 target_col: yv,
#                 slope_col: slope_val,
#             }
#
#             for c in [
#                 "material_key",
#                 "original_material_index",
#                 "compound_name",
#                 "cas",
#                 "formula",
#                 "SMILES",
#                 "smiles",
#                 "final_smiles",
#                 "inchikey",
#                 "pubchem_inchikey",
#                 "pubchem_cid",
#                 "pubchem_cid_for_Tb",
#                 "boiling_T_K",
#                 "T_min",
#                 "T_max",
#                 "T_range",
#                 "RSQ_Surface_vs_T",
#                 "slope_Surface_vs_T",
#             ]:
#                 if c in row.index:
#                     meta[c] = row[c]
#
#             row_meta.append(meta)
#
# # ---------- 7.2 备用：按物质顺序对齐 ----------
# else:
#     print("\n没有找到可用于描述符和数据对齐的共同 ID，尝试按物质顺序对齐。")
#
#     if data_group_col is None:
#         raise ValueError("无法确定 Data_selected 中的物质分组列。")
#
#     df_data_work = df_data.copy()
#     df_slope_work = df_slope.copy()
#
#     df_data_work["_group"] = df_data_work[data_group_col].apply(clean_key_value)
#     groups = df_data_work["_group"].drop_duplicates().tolist()
#
#     if len(groups) != len(df_features):
#         raise ValueError(
#             "物质分组数量与描述符行数不一致，无法按顺序对齐。\n"
#             f"Data 物质数 = {len(groups)}\n"
#             f"描述符行数 = {len(df_features)}"
#         )
#
#     df_slope_work["_key"] = df_slope_work[slope_key_col].apply(clean_key_value)
#     df_slope_work = df_slope_work.dropna(subset=["_key"]).drop_duplicates("_key")
#     slope_map = df_slope_work.set_index("_key")[slope_col].to_dict()
#
#     for i, key in enumerate(groups):
#         if key not in slope_map or not np.isfinite(slope_map[key]):
#             continue
#
#         desc = df_features.iloc[i][used_feature_cols].values.astype(float)
#         slope_val = float(slope_map[key])
#
#         sub = df_data_work[df_data_work["_group"] == key]
#
#         for _, row in sub.iterrows():
#             T = row[temp_col_actual]
#             yv = row[target_col]
#
#             if not (
#                 np.isfinite(T)
#                 and np.isfinite(yv)
#                 and yv > 0
#             ):
#                 continue
#
#             X_no_slope.append(
#                 np.concatenate([desc, [T]])
#             )
#
#             X_with_slope.append(
#                 np.concatenate([desc, [T, slope_val]])
#             )
#
#             y.append(yv)
#             material_ids.append(key)
#
#             meta = {
#                 "_key": key,
#                 temp_col_actual: T,
#                 target_col: yv,
#                 slope_col: slope_val,
#             }
#
#             for c in [
#                 "material_key",
#                 "original_material_index",
#                 "compound_name",
#                 "cas",
#                 "formula",
#                 "SMILES",
#                 "smiles",
#                 "final_smiles",
#                 "inchikey",
#                 "pubchem_inchikey",
#                 "pubchem_cid",
#                 "pubchem_cid_for_Tb",
#                 "boiling_T_K",
#                 "T_min",
#                 "T_max",
#                 "T_range",
#                 "RSQ_Surface_vs_T",
#                 "slope_Surface_vs_T",
#             ]:
#                 if c in row.index:
#                     meta[c] = row[c]
#
#             row_meta.append(meta)
#
#
# X_no_slope = np.array(X_no_slope, dtype=float)
# X_with_slope = np.array(X_with_slope, dtype=float)
# y = np.array(y, dtype=float)
# material_ids = np.array(material_ids, dtype=str)
#
# df_meta = pd.DataFrame(row_meta)
#
# unique_materials = np.unique(material_ids)
#
# print("\n========== 建模数据统计 ==========")
# print("总样本点数:", len(y))
# print("有效物质数:", len(unique_materials))
# print("无 slope 特征维度:", X_no_slope.shape[1])
# print("有 slope 特征维度:", X_with_slope.shape[1])
#
# if len(y) == 0:
#     raise ValueError("没有有效样本点。")
#
# if len(unique_materials) < n_outer_folds:
#     raise ValueError(
#         f"有效物质数 {len(unique_materials)} 小于 n_outer_folds={n_outer_folds}。"
#     )
#
#
# # =========================================================
# # 8. 5折交叉验证，按物质划分
# # =========================================================
#
# kf = KFold(
#     n_splits=n_outer_folds,
#     shuffle=True,
#     random_state=random_state,
# )
#
# metrics_no_slope = []
# metrics_with_slope = []
#
# pred_rows_no_slope = []
# pred_rows_with_slope = []
#
# for fold, (train_idx, test_idx) in enumerate(kf.split(unique_materials), start=1):
#     print(f"\n========== Fold {fold}/{n_outer_folds} ==========")
#
#     train_mats = unique_materials[train_idx]
#     test_mats = unique_materials[test_idx]
#
#     train_mask = np.isin(material_ids, train_mats)
#     test_mask = np.isin(material_ids, test_mats)
#
#     print("训练物质数:", len(train_mats))
#     print("测试物质数:", len(test_mats))
#     print("训练点数:", int(train_mask.sum()))
#     print("测试点数:", int(test_mask.sum()))
#
#     # ----- 模型A：无 slope -----
#     X_train_A = X_no_slope[train_mask]
#     y_train_A = y[train_mask]
#
#     X_test_A = X_no_slope[test_mask]
#     y_test_A = y[test_mask]
#
#     valid_train_A = np.isfinite(X_train_A).all(axis=1) & np.isfinite(y_train_A)
#     valid_test_A = np.isfinite(X_test_A).all(axis=1) & np.isfinite(y_test_A)
#
#     X_train_A = X_train_A[valid_train_A]
#     y_train_A = y_train_A[valid_train_A]
#
#     X_test_A_valid = X_test_A[valid_test_A]
#     y_test_A_valid = y_test_A[valid_test_A]
#
#     model_A = RandomForestRegressor(**rf_params)
#     model_A.fit(X_train_A, y_train_A)
#
#     y_pred_A_valid = model_A.predict(X_test_A_valid)
#
#     y_pred_A = np.full(len(y_test_A), np.nan)
#     y_pred_A[valid_test_A] = y_pred_A_valid
#
#     # ----- 模型B：有 slope -----
#     X_train_B = X_with_slope[train_mask]
#     y_train_B = y[train_mask]
#
#     X_test_B = X_with_slope[test_mask]
#     y_test_B = y[test_mask]
#
#     valid_train_B = np.isfinite(X_train_B).all(axis=1) & np.isfinite(y_train_B)
#     valid_test_B = np.isfinite(X_test_B).all(axis=1) & np.isfinite(y_test_B)
#
#     X_train_B = X_train_B[valid_train_B]
#     y_train_B = y_train_B[valid_train_B]
#
#     X_test_B_valid = X_test_B[valid_test_B]
#     y_test_B_valid = y_test_B[valid_test_B]
#
#     model_B = RandomForestRegressor(**rf_params)
#     model_B.fit(X_train_B, y_train_B)
#
#     y_pred_B_valid = model_B.predict(X_test_B_valid)
#
#     y_pred_B = np.full(len(y_test_B), np.nan)
#     y_pred_B[valid_test_B] = y_pred_B_valid
#
#     # ----- 指标 -----
#     m_A = calc_metrics_surface(y_test_A, y_pred_A)
#     m_B = calc_metrics_surface(y_test_B, y_pred_B)
#
#     m_A["fold"] = fold
#     m_B["fold"] = fold
#
#     metrics_no_slope.append(m_A)
#     metrics_with_slope.append(m_B)
#
#     print(
#         "RF(desc+T)       | R2:",
#         f"{m_A['R2']:.10f}",
#         "MSE:",
#         f"{m_A['MSE']:.12f}",
#         "ARD%:",
#         f"{m_A['ARD_percent']:.10f}",
#     )
#
#     print(
#         "RF(desc+T+slope) | R2:",
#         f"{m_B['R2']:.10f}",
#         "MSE:",
#         f"{m_B['MSE']:.12f}",
#         "ARD%:",
#         f"{m_B['ARD_percent']:.10f}",
#     )
#
#     # ----- 保存预测明细 -----
#     df_test_meta = df_meta.loc[test_mask].reset_index(drop=True).copy()
#
#     pred_A = df_test_meta.copy()
#     pred_A["fold"] = fold
#     pred_A["model"] = "RF_desc_T"
#     pred_A["y_true"] = y_test_A
#     pred_A["y_pred"] = y_pred_A
#     pred_A["abs_error"] = np.abs(pred_A["y_pred"] - pred_A["y_true"])
#     pred_A["rel_error_percent"] = (
#         pred_A["abs_error"] / np.abs(pred_A["y_true"]) * 100.0
#     )
#
#     pred_B = df_test_meta.copy()
#     pred_B["fold"] = fold
#     pred_B["model"] = "RF_desc_T_slope"
#     pred_B["y_true"] = y_test_B
#     pred_B["y_pred"] = y_pred_B
#     pred_B["abs_error"] = np.abs(pred_B["y_pred"] - pred_B["y_true"])
#     pred_B["rel_error_percent"] = (
#         pred_B["abs_error"] / np.abs(pred_B["y_true"]) * 100.0
#     )
#
#     pred_rows_no_slope.append(pred_A)
#     pred_rows_with_slope.append(pred_B)
#
#
# # =========================================================
# # 9. 汇总统计
# # =========================================================
#
# df_A = pd.DataFrame(metrics_no_slope)
# df_B = pd.DataFrame(metrics_with_slope)
#
# # fold 放到第一列
# df_A = df_A[["fold"] + [c for c in df_A.columns if c != "fold"]]
# df_B = df_B[["fold"] + [c for c in df_B.columns if c != "fold"]]
#
# metric_names = [c for c in df_A.columns if c != "fold"]
#
# summary_A = summarize(df_A, "RF(desc + T)")
# summary_B = summarize(df_B, "RF(desc + T + slope)")
#
# summary_all = pd.concat(
#     [summary_A, summary_B],
#     ignore_index=True,
# )
#
# print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
# print(summary_all.to_string(index=False))
#
#
# # =========================================================
# # 10. 配对 t 检验
# # =========================================================
#
# t_test_results = []
#
# for metric in metric_names:
#     vals_A = pd.to_numeric(df_A[metric], errors="coerce").dropna().values
#     vals_B = pd.to_numeric(df_B[metric], errors="coerce").dropna().values
#
#     if len(vals_A) == len(vals_B) and len(vals_A) > 1:
#         if SCIPY_AVAILABLE:
#             t_stat, p_val = ttest_rel(vals_A, vals_B)
#         else:
#             t_stat, p_val = np.nan, np.nan
#
#         if metric == "R2" or metric in ["leq1%", "leq5%", "leq10%"]:
#             better = "with_slope" if np.mean(vals_B) > np.mean(vals_A) else "no_slope"
#         else:
#             better = "with_slope" if np.mean(vals_B) < np.mean(vals_A) else "no_slope"
#
#         t_test_results.append({
#             "Metric": metric,
#             "Mean_no_slope": np.mean(vals_A),
#             "Mean_with_slope": np.mean(vals_B),
#             "Delta_with_minus_no": np.mean(vals_B) - np.mean(vals_A),
#             "t_stat": t_stat,
#             "p_value": p_val,
#             "Significant_p_lt_0.05": bool(p_val < 0.05) if np.isfinite(p_val) else False,
#             "Better_model": better,
#             "scipy_available": SCIPY_AVAILABLE,
#         })
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
#
# df_pred_A = pd.concat(pred_rows_no_slope, ignore_index=True)
# df_pred_B = pd.concat(pred_rows_with_slope, ignore_index=True)
#
# df_used_features = pd.DataFrame({
#     "used_descriptor_feature": used_feature_cols,
# })
#
# run_info = pd.DataFrame([
#     {"param": "descriptor_file", "value": str(descriptor_file)},
#     {"param": "descriptor_sheet", "value": descriptor_sheet},
#     {"param": "selected_feature_sheet", "value": selected_feature_sheet},
#     {"param": "data_file", "value": str(data_file)},
#     {"param": "data_sheet", "value": data_sheet},
#     {"param": "slope_file_used", "value": str(slope_path_used)},
#     {"param": "slope_sheet_used", "value": slope_sheet_used},
#
#     {"param": "desc_key_col", "value": desc_key_col},
#     {"param": "data_key_col", "value": data_key_col},
#     {"param": "data_group_col", "value": data_group_col},
#     {"param": "slope_key_col", "value": slope_key_col},
#
#     {"param": "temp_col_actual", "value": temp_col_actual},
#     {"param": "target_col", "value": target_col},
#     {"param": "slope_col", "value": slope_col},
#
#     {"param": "n_outer_folds", "value": n_outer_folds},
#     {"param": "random_state", "value": random_state},
#     {"param": "n_descriptor_features_original", "value": len(feature_cols)},
#     {"param": "n_descriptor_features_used", "value": len(used_feature_cols)},
#     {"param": "total_samples", "value": len(y)},
#     {"param": "n_materials", "value": len(unique_materials)},
#
#     {"param": "model_no_slope", "value": "RandomForestRegressor(desc + T_K)"},
#     {"param": "model_with_slope", "value": "RandomForestRegressor(desc + T_K + slope_pred_surface_over_T)"},
#     {"param": "rf_params", "value": str(rf_params)},
# ])
#
# with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
#     df_A.to_excel(writer, sheet_name="Fold_Metrics_No_Slope", index=False)
#     df_B.to_excel(writer, sheet_name="Fold_Metrics_With_Slope", index=False)
#
#     summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
#     df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)
#
#     df_pred_A.to_excel(writer, sheet_name="Predictions_No_Slope", index=False)
#     df_pred_B.to_excel(writer, sheet_name="Predictions_With_Slope", index=False)
#
#     df_used_features.to_excel(writer, sheet_name="Used_Descriptor_Features", index=False)
#     run_info.to_excel(writer, sheet_name="Run_Info", index=False)
#
#     workbook = writer.book
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
# print(f"\n保存完成: {output_file}")
# print("主要输出 sheet:")
# print("- Fold_Metrics_No_Slope")
# print("- Fold_Metrics_With_Slope")
# print("- Summary_Mean_Std")
# print("- Paired_T_Test")
# print("- Predictions_No_Slope")
# print("- Predictions_With_Slope")
# print("- Used_Descriptor_Features")
# print("- Run_Info")



# -*- coding: utf-8 -*-
"""
Surface tension liquid-gas:
QSPR 25 descriptors + T_K vs QSPR 25 descriptors + T_K + slope
Random Forest 5-fold CV comparison

输入 1：
    selected_descriptors_with_surface_mean_target.xlsx
    sheet:
        Selected_Features_Target
        Selected_Features

输入 2：
    dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points_with_RSQ.xlsx
    或：
    dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points.xlsx
    sheet:
        Data_selected

输入 3：
    HistGB_submodels_predict_ref_surface_Tb_and_slope.xlsx
    或：
    HistGB_submodels_predict_ref_surface_Tb_and_slope.xls
    sheet:
        slope

比较模型：
    模型 A：RF(desc + T_K)
    模型 B：RF(desc + T_K + slope_pred_surface_over_T)

目标：
    SurfaceTension_N_m

新增：
    1. 每个 fold 训练完成后，额外预测完整数据集；
    2. 对完整数据集统计相对误差 <1%、<5%、<10% 的点数；
    3. 对 5 个 fold 的完整数据集偏差数量取平均；
    4. 保存 fold_test_predictions、fold_all_data_predictions、
       fold_all_data_count_summary、final_average_summary；
    5. 最后输出方便复制到 Excel 的三行数字。

输出：
    RF_surface_QSPR25_5fold_CV_comparison_with_slope.xlsx
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


pd.set_option("display.float_format", "{:.10f}".format)
np.set_printoptions(suppress=True, precision=10)


# =========================================================
# 0. 全局设置
# =========================================================
descriptor_file = Path("selected_descriptors_with_surface_mean_target.xlsx")
descriptor_sheet = "Selected_Features_Target"
selected_feature_sheet = "Selected_Features"

preferred_data_file = Path(
    "dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points_with_RSQ.xlsx"
)

fallback_data_file = Path(
    "dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points.xlsx"
)

if preferred_data_file.exists():
    data_file = preferred_data_file
elif fallback_data_file.exists():
    data_file = fallback_data_file
else:
    raise FileNotFoundError(
        "没有找到表面张力数据文件：\n"
        f"1. {preferred_data_file}\n"
        f"2. {fallback_data_file}"
    )

data_sheet = "Data_selected"

slope_file = Path("HistGB_submodels_predict_ref_surface_Tb_and_slope.xlsx")
slope_sheet_candidates = ["slope", "Slope", "Predicted_Slope"]
slope_col_candidates = [
    "slope_pred_surface_over_T",
    "slope_pred_Surface_over_T",
    "slope_pred_surface_tension_over_T",
]

output_file = Path("RF_surface_QSPR25_5fold_CV_comparison_with_slope.xlsx")

material_key_col = "material_key"
temp_col = "T_K"

target_candidates = [
    "SurfaceTension_N_m",
    "surface_tension_N_m",
    "Surface_Tension_N_m",
    "SurfaceTension",
    "surface_tension",
    "Surface tension liquid-gas, N/m",
    "Surface tension liquid-gas",
    "property_value",
]

n_outer_folds = 5
random_state = 42

rf_params = {
    "n_estimators": 500,
    "max_depth": None,
    "min_samples_split": 2,
    "min_samples_leaf": 1,
    "max_features": "sqrt",
    "bootstrap": True,
    "random_state": random_state,
    "n_jobs": -1,
}


# =========================================================
# 1. 辅助函数
# =========================================================
def normalize_colname(name):
    return (
        str(name)
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "")
        .replace(".", "")
        .replace(",", "")
    )


def find_first_existing_col(df, candidates, required=True, col_type="列"):
    norm_map = {normalize_colname(c): c for c in df.columns}

    for c in candidates:
        key = normalize_colname(c)
        if key in norm_map:
            return norm_map[key]

    if required:
        raise ValueError(
            f"没有找到 {col_type}。\n"
            f"候选列名: {candidates}\n"
            f"当前列名: {list(df.columns)}"
        )

    return None


def is_valid_value(x):
    if pd.isna(x):
        return False

    s = str(x).strip()

    if s == "":
        return False

    if s.lower() in ["nan", "none", "null", "待定"]:
        return False

    return True


def clean_key_value(x):
    """
    清理物质 ID：
        123.0 -> '123'
        其他字符串保留。
    """
    if not is_valid_value(x):
        return np.nan

    s = str(x).strip()

    try:
        f = float(s)

        if np.isfinite(f) and abs(f - round(f)) < 1e-8:
            return str(int(round(f)))

    except Exception:
        pass

    return s


def find_alignment_key(df_desc, df_data):
    """
    描述符表与 Data_selected 的对齐键。
    """
    candidate_pairs = [
        ("material_key", "material_key"),
        ("original_material_index", "original_material_index"),

        ("pubchem_cid", "pubchem_cid"),
        ("pubchem_cid_for_Tb", "pubchem_cid_for_Tb"),
        ("CID", "pubchem_cid"),
        ("CID_int", "pubchem_cid"),
        ("sdf_pubchem_cid", "pubchem_cid"),

        ("inchikey", "inchikey"),
        ("InChIKey", "InChIKey"),
        ("pubchem_inchikey", "pubchem_inchikey"),
        ("inchikey_from_rdkit", "inchikey"),

        ("cas", "cas"),
        ("compound_name", "compound_name"),
    ]

    for dcol, dacol in candidate_pairs:
        if dcol in df_desc.columns and dacol in df_data.columns:
            return dcol, dacol

    return None, None


def choose_data_group_key(df_data):
    for col in [
        "material_key",
        "original_material_index",
        "pubchem_cid",
        "pubchem_cid_for_Tb",
        "CID",
        "CID_int",
        "inchikey",
        "InChIKey",
        "pubchem_inchikey",
        "cas",
        "compound_name",
    ]:
        if col in df_data.columns:
            return col

    return None


def find_slope_key(df_slope, preferred_data_key_col):
    if preferred_data_key_col is not None and preferred_data_key_col in df_slope.columns:
        return preferred_data_key_col

    for col in [
        "material_key",
        "original_material_index",
        "pubchem_cid",
        "pubchem_cid_for_Tb",
        "CID",
        "CID_int",
        "sdf_pubchem_cid",
        "inchikey",
        "InChIKey",
        "pubchem_inchikey",
        "cas",
        "compound_name",
    ]:
        if col in df_slope.columns:
            return col

    return None


def read_slope_file(slope_path, sheet_candidates):
    """
    读取 slope 文件。
    如果 .xlsx 不存在，自动尝试 .xls。
    如果 .xls 不存在，自动尝试 .xlsx。
    """
    if not slope_path.exists():
        if slope_path.suffix.lower() == ".xlsx":
            alt = slope_path.with_suffix(".xls")
        else:
            alt = slope_path.with_suffix(".xlsx")

        if alt.exists():
            slope_path = alt
        else:
            raise FileNotFoundError(
                f"未找到 slope 文件: {slope_path}\n"
                f"也未找到备用文件: {alt}"
            )

    xls = pd.ExcelFile(slope_path)

    sheet = None

    for s in sheet_candidates:
        if s in xls.sheet_names:
            sheet = s
            break

    if sheet is None:
        sheet = xls.sheet_names[0]

    df = pd.read_excel(slope_path, sheet_name=sheet)

    return df, slope_path, sheet


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


def calc_metrics_surface(y_true, y_pred):
    """
    表面张力空间指标。
    leq1%、leq5%、leq10% 是测试集上相对误差 <= 阈值的比例，保留原始展示口径。
    最终复制输出使用完整数据集上的严格 < 阈值点数。
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
            "leq1%": np.nan,
            "leq5%": np.nan,
            "leq10%": np.nan,
            "max_rel%": np.nan,
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
        le1_count = float(np.nansum(rel_err <= 1.0))
        le5_count = float(np.nansum(rel_err <= 5.0))
        le10_count = float(np.nansum(rel_err <= 10.0))
        max_rel = float(np.nanmax(rel_err))

        n_valid = int(np.sum(np.isfinite(rel_err)))
        le1 = le1_count / n_valid * 100.0
        le5 = le5_count / n_valid * 100.0
        le10 = le10_count / n_valid * 100.0
    else:
        ard = np.nan
        le1 = np.nan
        le5 = np.nan
        le10 = np.nan
        max_rel = np.nan
        le1_count = 0.0
        le5_count = 0.0
        le10_count = 0.0

    return {
        "n_points": len(y_true_valid),
        "R2": r2,
        "MSE": mse,
        "RMSE": rmse,
        "MAE": mae,
        "ARD_percent": ard,
        "leq1%": le1,
        "leq5%": le5,
        "leq10%": le10,
        "max_rel%": max_rel,
        "leq1_count": le1_count,
        "leq5_count": le5_count,
        "leq10_count": le10_count,
    }


def format_metric_value(metric, value):
    if pd.isna(value):
        return "NaN"

    if metric == "MSE":
        return f"{value:.12f}"

    if metric in ["RMSE", "MAE"]:
        return f"{value:.10f}"

    return f"{value:.6f}"


def summarize(df, name):
    metric_names = [c for c in df.columns if c != "fold"]

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


def make_prediction_df(fold, dataset_name, method, meta_df, y_true, y_pred):
    """
    保存测试集或完整数据集预测明细。
    """
    meta_df = meta_df.copy().reset_index(drop=True)

    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    df_out = meta_df.copy()

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
        "_key",
        material_key_col,
        "original_material_index",
        "compound_name",
        "cas",
        "formula",
        "SMILES",
        "smiles",
        "final_smiles",
        "inchikey",
        "pubchem_inchikey",
        "pubchem_cid",
        "pubchem_cid_for_Tb",
        "boiling_T_K",
        temp_col_actual,
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
if not descriptor_file.exists():
    raise FileNotFoundError(
        f"没有找到描述符文件: {descriptor_file}\n"
        "请先运行 25 个描述符筛选代码。"
    )

if not data_file.exists():
    raise FileNotFoundError(f"没有找到表面张力数据文件: {data_file}")

df_desc = pd.read_excel(descriptor_file, sheet_name=descriptor_sheet)
df_data = pd.read_excel(data_file, sheet_name=data_sheet)
df_slope, slope_path_used, slope_sheet_used = read_slope_file(
    slope_file,
    slope_sheet_candidates,
)

print("描述符表行数:", len(df_desc))
print("原始数据行数:", len(df_data))
print("Slope 表行数:", len(df_slope))
print("Slope 文件:", slope_path_used)
print("Slope sheet:", slope_sheet_used)


# =========================================================
# 3. 确定物质 ID 列
# =========================================================
desc_key_col, data_key_col = find_alignment_key(df_desc, df_data)
data_group_col = choose_data_group_key(df_data)
slope_key_col = find_slope_key(df_slope, data_key_col)

print("\n物质对齐方式:")
print("  desc_key_col:", desc_key_col)
print("  data_key_col:", data_key_col)
print("  data_group_col:", data_group_col)
print("  slope_key_col:", slope_key_col)

if slope_key_col is None:
    raise ValueError("无法在 slope 表中找到物质 ID 列。")


# =========================================================
# 4. 读取 25 个描述符列表
# =========================================================
xls_desc = pd.ExcelFile(descriptor_file)

if selected_feature_sheet in xls_desc.sheet_names:
    df_selected = pd.read_excel(descriptor_file, sheet_name=selected_feature_sheet)

    if "selected_feature" in df_selected.columns:
        feature_cols = df_selected["selected_feature"].dropna().astype(str).tolist()
    else:
        feature_cols = df_selected.iloc[:, 0].dropna().astype(str).tolist()

else:
    meta = [
        "material_index",
        "original_material_index",
        "material_key",
        "compound_name",
        "cas",
        "formula",
        "SMILES",
        "smiles",
        "final_smiles",
        "inchikey",
        "InChIKey",
        "pubchem_inchikey",
        "pubchem_cid",
        "pubchem_cid_for_Tb",
        "CID",
        "CID_int",
        "phase",
        "boiling_T_K",
        "T_min",
        "T_max",
        "T_range",
        "n_points",
        "target_n_valid_points",
        "target_min_surface",
        "target_max_surface",
        "target_mean_surface",
        "RSQ_Surface_vs_T",
        "slope_Surface_vs_T",
        "intercept_Surface_vs_T",
        "RSQ_Surface_vs_invT",
        "RSQ_lnSurface_vs_T",
        "fit_status",
        "slope_direction_Surface_vs_T",
    ]

    feature_cols = [c for c in df_desc.columns if c not in meta]

missing_features = [c for c in feature_cols if c not in df_desc.columns]

if len(missing_features) > 0:
    raise ValueError(
        "以下选中描述符不在描述符表中：\n"
        f"{missing_features}"
    )

print("\n原始选中描述符数量:", len(feature_cols))


# =========================================================
# 5. 数值化描述符，删除无效列
# =========================================================
df_feature_raw = df_desc[feature_cols].copy()

df_features = df_feature_raw.apply(
    pd.to_numeric,
    errors="coerce"
)

df_features = df_features.replace([np.inf, -np.inf], np.nan)

# 均值填充
df_features = df_features.fillna(df_features.mean())

# 如果仍有 NaN，删除该列
df_features = df_features.dropna(axis=1, how="any")

# 删除全零列
nonzero = df_features.abs().sum(axis=0) != 0

used_feature_cols = df_features.columns[nonzero].tolist()
removed_zero_feature_cols = df_features.columns[~nonzero].tolist()

print("有效描述符数量:", len(used_feature_cols))
print("删除全零描述符数量:", len(removed_zero_feature_cols))

if len(used_feature_cols) == 0:
    raise ValueError("没有有效描述符可用于建模。")


# =========================================================
# 6. 找到温度列、目标列、斜率列
# =========================================================
temp_col_actual = find_first_existing_col(
    df_data,
    [temp_col, "T_K", "Temperature", "temperature"],
    required=True,
    col_type="温度列",
)

target_col = find_first_existing_col(
    df_data,
    target_candidates,
    required=True,
    col_type="表面张力目标列",
)

slope_col = find_first_existing_col(
    df_slope,
    slope_col_candidates,
    required=True,
    col_type="斜率列",
)

print("\n温度列:", temp_col_actual)
print("目标列:", target_col)
print("斜率列:", slope_col)

df_data[temp_col_actual] = pd.to_numeric(df_data[temp_col_actual], errors="coerce")
df_data[target_col] = pd.to_numeric(df_data[target_col], errors="coerce")
df_slope[slope_col] = pd.to_numeric(df_slope[slope_col], errors="coerce")


# =========================================================
# 7. 合并数据，构造按物质展开的特征矩阵
# =========================================================
X_no_slope = []
X_with_slope = []
y = []
material_ids = []
row_meta = []

# ---------- 7.1 优先使用公共 ID 对齐 ----------
if desc_key_col is not None and data_key_col is not None:
    df_desc_work = df_desc.copy()
    df_data_work = df_data.copy()
    df_slope_work = df_slope.copy()

    df_desc_work["_key"] = df_desc_work[desc_key_col].apply(clean_key_value)
    df_data_work["_key"] = df_data_work[data_key_col].apply(clean_key_value)
    df_slope_work["_key"] = df_slope_work[slope_key_col].apply(clean_key_value)

    df_desc_work = df_desc_work.dropna(subset=["_key"]).copy()
    df_data_work = df_data_work.dropna(subset=["_key"]).copy()
    df_slope_work = df_slope_work.dropna(subset=["_key"]).copy()

    df_desc_work = df_desc_work.drop_duplicates(subset=["_key"], keep="first")
    df_slope_work = df_slope_work.drop_duplicates(subset=["_key"], keep="first")

    # 同步描述符数值列
    df_desc_work[used_feature_cols] = df_features.loc[
        df_desc_work.index,
        used_feature_cols
    ].values

    desc_map = {
        row["_key"]: row[used_feature_cols].values.astype(float)
        for _, row in df_desc_work.iterrows()
    }

    slope_map = (
        df_slope_work
        .set_index("_key")[slope_col]
        .to_dict()
    )

    data_keys_in_order = df_data_work["_key"].drop_duplicates().tolist()

    valid_keys = [
        k for k in data_keys_in_order
        if k in desc_map
        and k in slope_map
        and np.isfinite(slope_map[k])
    ]

    if len(valid_keys) == 0:
        raise ValueError("没有同时拥有描述符、数据点和有效 slope 的物质。")

    print("\n同时拥有描述符、数据点和 slope 的物质数:", len(valid_keys))

    for key in valid_keys:
        desc = np.asarray(desc_map[key], dtype=float)
        slope_val = float(slope_map[key])

        sub = df_data_work[df_data_work["_key"] == key].copy()

        for _, row in sub.iterrows():
            T = row[temp_col_actual]
            yv = row[target_col]

            if not (
                np.isfinite(T)
                and np.isfinite(yv)
                and yv > 0
            ):
                continue

            # 表面张力使用 T_K，不使用 1/T
            X_no_slope.append(
                np.concatenate([desc, [T]])
            )

            X_with_slope.append(
                np.concatenate([desc, [T, slope_val]])
            )

            y.append(yv)
            material_ids.append(key)

            meta = {
                "_key": key,
                temp_col_actual: T,
                target_col: yv,
                slope_col: slope_val,
            }

            for c in [
                "material_key",
                "original_material_index",
                "compound_name",
                "cas",
                "formula",
                "SMILES",
                "smiles",
                "final_smiles",
                "inchikey",
                "pubchem_inchikey",
                "pubchem_cid",
                "pubchem_cid_for_Tb",
                "boiling_T_K",
                "T_min",
                "T_max",
                "T_range",
                "RSQ_Surface_vs_T",
                "slope_Surface_vs_T",
            ]:
                if c in row.index:
                    meta[c] = row[c]

            row_meta.append(meta)

# ---------- 7.2 备用：按物质顺序对齐 ----------
else:
    print("\n没有找到可用于描述符和数据对齐的共同 ID，尝试按物质顺序对齐。")

    if data_group_col is None:
        raise ValueError("无法确定 Data_selected 中的物质分组列。")

    df_data_work = df_data.copy()
    df_slope_work = df_slope.copy()

    df_data_work["_group"] = df_data_work[data_group_col].apply(clean_key_value)
    groups = df_data_work["_group"].drop_duplicates().tolist()

    if len(groups) != len(df_features):
        raise ValueError(
            "物质分组数量与描述符行数不一致，无法按顺序对齐。\n"
            f"Data 物质数 = {len(groups)}\n"
            f"描述符行数 = {len(df_features)}"
        )

    df_slope_work["_key"] = df_slope_work[slope_key_col].apply(clean_key_value)
    df_slope_work = df_slope_work.dropna(subset=["_key"]).drop_duplicates("_key")
    slope_map = df_slope_work.set_index("_key")[slope_col].to_dict()

    for i, key in enumerate(groups):
        if key not in slope_map or not np.isfinite(slope_map[key]):
            continue

        desc = df_features.iloc[i][used_feature_cols].values.astype(float)
        slope_val = float(slope_map[key])

        sub = df_data_work[df_data_work["_group"] == key]

        for _, row in sub.iterrows():
            T = row[temp_col_actual]
            yv = row[target_col]

            if not (
                np.isfinite(T)
                and np.isfinite(yv)
                and yv > 0
            ):
                continue

            X_no_slope.append(
                np.concatenate([desc, [T]])
            )

            X_with_slope.append(
                np.concatenate([desc, [T, slope_val]])
            )

            y.append(yv)
            material_ids.append(key)

            meta = {
                "_key": key,
                temp_col_actual: T,
                target_col: yv,
                slope_col: slope_val,
            }

            for c in [
                "material_key",
                "original_material_index",
                "compound_name",
                "cas",
                "formula",
                "SMILES",
                "smiles",
                "final_smiles",
                "inchikey",
                "pubchem_inchikey",
                "pubchem_cid",
                "pubchem_cid_for_Tb",
                "boiling_T_K",
                "T_min",
                "T_max",
                "T_range",
                "RSQ_Surface_vs_T",
                "slope_Surface_vs_T",
            ]:
                if c in row.index:
                    meta[c] = row[c]

            row_meta.append(meta)


X_no_slope = np.array(X_no_slope, dtype=float)
X_with_slope = np.array(X_with_slope, dtype=float)
y = np.array(y, dtype=float)
material_ids = np.array(material_ids, dtype=str)

df_meta = pd.DataFrame(row_meta)

unique_materials = np.unique(material_ids)

print("\n========== 建模数据统计 ==========")
print("总样本点数:", len(y))
print("有效物质数:", len(unique_materials))
print("无 slope 特征维度:", X_no_slope.shape[1])
print("有 slope 特征维度:", X_with_slope.shape[1])

if len(y) == 0:
    raise ValueError("没有有效样本点。")

if len(unique_materials) < n_outer_folds:
    raise ValueError(
        f"有效物质数 {len(unique_materials)} 小于 n_outer_folds={n_outer_folds}。"
    )


# =========================================================
# 8. 5折交叉验证，按物质划分
# =========================================================
kf = KFold(
    n_splits=n_outer_folds,
    shuffle=True,
    random_state=random_state,
)

metrics_no_slope = []
metrics_with_slope = []

fold_test_prediction_dfs = []
fold_all_data_prediction_dfs = []
fold_all_data_count_records = []
fold_info_records = []

feature_importance_no_records = []
feature_importance_with_records = []

feature_names_no = used_feature_cols + [temp_col_actual]
feature_names_with = used_feature_cols + [temp_col_actual, slope_col]

all_sample_indices = np.arange(len(y))

for fold, (train_idx, test_idx) in enumerate(kf.split(unique_materials), start=1):
    print(f"\n========== Fold {fold}/{n_outer_folds} ==========")

    train_mats = unique_materials[train_idx]
    test_mats = unique_materials[test_idx]

    train_mask = np.isin(material_ids, train_mats)
    test_mask = np.isin(material_ids, test_mats)

    print("训练物质数:", len(train_mats))
    print("测试物质数:", len(test_mats))
    print("训练点数:", int(train_mask.sum()))
    print("测试点数:", int(test_mask.sum()))

    # ----- 模型A：无 slope -----
    X_train_A = X_no_slope[train_mask]
    y_train_A = y[train_mask]

    X_test_A = X_no_slope[test_mask]
    y_test_A = y[test_mask]

    valid_train_A = np.isfinite(X_train_A).all(axis=1) & np.isfinite(y_train_A)
    valid_test_A = np.isfinite(X_test_A).all(axis=1) & np.isfinite(y_test_A)

    X_train_A = X_train_A[valid_train_A]
    y_train_A = y_train_A[valid_train_A]

    X_test_A_valid = X_test_A[valid_test_A]

    model_A = RandomForestRegressor(**rf_params)
    model_A.fit(X_train_A, y_train_A)

    y_pred_A_valid = model_A.predict(X_test_A_valid)

    y_pred_A = np.full(len(y_test_A), np.nan)
    y_pred_A[valid_test_A] = y_pred_A_valid

    # 完整数据集预测
    valid_all_A = np.isfinite(X_no_slope).all(axis=1)

    y_pred_A_all = np.full(len(y), np.nan)
    y_pred_A_all[valid_all_A] = model_A.predict(X_no_slope[valid_all_A])

    # ----- 模型B：有 slope -----
    X_train_B = X_with_slope[train_mask]
    y_train_B = y[train_mask]

    X_test_B = X_with_slope[test_mask]
    y_test_B = y[test_mask]

    valid_train_B = np.isfinite(X_train_B).all(axis=1) & np.isfinite(y_train_B)
    valid_test_B = np.isfinite(X_test_B).all(axis=1) & np.isfinite(y_test_B)

    X_train_B = X_train_B[valid_train_B]
    y_train_B = y_train_B[valid_train_B]

    X_test_B_valid = X_test_B[valid_test_B]

    model_B = RandomForestRegressor(**rf_params)
    model_B.fit(X_train_B, y_train_B)

    y_pred_B_valid = model_B.predict(X_test_B_valid)

    y_pred_B = np.full(len(y_test_B), np.nan)
    y_pred_B[valid_test_B] = y_pred_B_valid

    # 完整数据集预测
    valid_all_B = np.isfinite(X_with_slope).all(axis=1)

    y_pred_B_all = np.full(len(y), np.nan)
    y_pred_B_all[valid_all_B] = model_B.predict(X_with_slope[valid_all_B])

    # ----- 测试集指标 -----
    m_A = calc_metrics_surface(y_test_A, y_pred_A)
    m_B = calc_metrics_surface(y_test_B, y_pred_B)

    m_A["fold"] = fold
    m_B["fold"] = fold

    metrics_no_slope.append(m_A)
    metrics_with_slope.append(m_B)

    print(
        "RF(desc+T)       | R2:",
        f"{m_A['R2']:.10f}",
        "MSE:",
        f"{m_A['MSE']:.12f}",
        "ARD%:",
        f"{m_A['ARD_percent']:.10f}",
    )

    print(
        "RF(desc+T+slope) | R2:",
        f"{m_B['R2']:.10f}",
        "MSE:",
        f"{m_B['MSE']:.12f}",
        "ARD%:",
        f"{m_B['ARD_percent']:.10f}",
    )

    # ----- 新增：每个 fold 模型预测完整数据集并统计数量 -----
    count_A_all = count_error_thresholds(y, y_pred_A_all)
    count_B_all = count_error_thresholds(y, y_pred_B_all)

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "RF_desc_T",
        **count_A_all,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "RF_desc_T_slope",
        **count_B_all,
    })

    print("\nRF(desc+T) fold model predicts ALL data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "RF_desc_T",
        **count_A_all,
    }]).to_string(index=False))

    print("\nRF(desc+T+slope) fold model predicts ALL data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "RF_desc_T_slope",
        **count_B_all,
    }]).to_string(index=False))

    # ----- 保存测试集预测明细 -----
    df_test_meta = df_meta.loc[test_mask].reset_index(drop=True).copy()
    df_all_meta = df_meta.copy().reset_index(drop=True)

    df_test_A = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="RF_desc_T",
        meta_df=df_test_meta,
        y_true=y_test_A,
        y_pred=y_pred_A,
    )

    df_test_B = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="RF_desc_T_slope",
        meta_df=df_test_meta,
        y_true=y_test_B,
        y_pred=y_pred_B,
    )

    fold_test_prediction_dfs.append(df_test_A)
    fold_test_prediction_dfs.append(df_test_B)

    # ----- 保存完整数据集预测明细 -----
    df_all_A = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="RF_desc_T",
        meta_df=df_all_meta,
        y_true=y,
        y_pred=y_pred_A_all,
    )

    df_all_B = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="RF_desc_T_slope",
        meta_df=df_all_meta,
        y_true=y,
        y_pred=y_pred_B_all,
    )

    fold_all_data_prediction_dfs.append(df_all_A)
    fold_all_data_prediction_dfs.append(df_all_B)

    # ----- 特征重要性 -----
    if hasattr(model_A, "feature_importances_"):
        for fname, imp in zip(feature_names_no, model_A.feature_importances_):
            feature_importance_no_records.append({
                "fold": fold,
                "model": "RF_desc_T",
                "feature": fname,
                "importance": imp,
            })

    if hasattr(model_B, "feature_importances_"):
        for fname, imp in zip(feature_names_with, model_B.feature_importances_):
            feature_importance_with_records.append({
                "fold": fold,
                "model": "RF_desc_T_slope",
                "feature": fname,
                "importance": imp,
            })

    fold_info_records.append({
        "fold": fold,
        "n_train_materials": len(train_mats),
        "n_test_materials": len(test_mats),
        "n_train_points": int(train_mask.sum()),
        "n_test_points": int(test_mask.sum()),
        "n_all_points": len(y),
        "n_features_no_slope": X_no_slope.shape[1],
        "n_features_with_slope": X_with_slope.shape[1],
        "n_valid_train_no_slope": int(valid_train_A.sum()),
        "n_valid_test_no_slope": int(valid_test_A.sum()),
        "n_valid_train_with_slope": int(valid_train_B.sum()),
        "n_valid_test_with_slope": int(valid_test_B.sum()),
    })


# =========================================================
# 9. 汇总统计
# =========================================================
df_A = pd.DataFrame(metrics_no_slope)
df_B = pd.DataFrame(metrics_with_slope)

# fold 放到第一列
df_A = df_A[["fold"] + [c for c in df_A.columns if c != "fold"]]
df_B = df_B[["fold"] + [c for c in df_B.columns if c != "fold"]]

metric_names = [c for c in df_A.columns if c != "fold"]

summary_A = summarize(df_A, "RF(desc + T)")
summary_B = summarize(df_B, "RF(desc + T + slope)")

summary_all = pd.concat(
    [summary_A, summary_B],
    ignore_index=True,
)

print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
print(summary_all.to_string(index=False))


# =========================================================
# 10. 配对 t 检验
# =========================================================
t_test_results = []

for metric in metric_names:
    vals_A = pd.to_numeric(df_A[metric], errors="coerce").values
    vals_B = pd.to_numeric(df_B[metric], errors="coerce").values

    valid = np.isfinite(vals_A) & np.isfinite(vals_B)

    vals_A = vals_A[valid]
    vals_B = vals_B[valid]

    if len(vals_A) == len(vals_B) and len(vals_A) > 1:
        if SCIPY_AVAILABLE:
            t_stat, p_val = ttest_rel(vals_A, vals_B)
        else:
            t_stat, p_val = np.nan, np.nan

        if metric == "R2" or metric in ["leq1%", "leq5%", "leq10%"]:
            better = "with_slope" if np.mean(vals_B) > np.mean(vals_A) else "no_slope"
        else:
            better = "with_slope" if np.mean(vals_B) < np.mean(vals_A) else "no_slope"

        t_test_results.append({
            "Metric": metric,
            "Mean_no_slope": np.mean(vals_A),
            "Mean_with_slope": np.mean(vals_B),
            "Delta_with_minus_no": np.mean(vals_B) - np.mean(vals_A),
            "t_stat": t_stat,
            "p_value": p_val,
            "Significant_p_lt_0.05": bool(p_val < 0.05) if np.isfinite(p_val) else False,
            "Better_model": better,
            "scipy_available": SCIPY_AVAILABLE,
            "n_valid_fold_pairs": len(vals_A),
        })

    else:
        t_test_results.append({
            "Metric": metric,
            "Mean_no_slope": np.nan,
            "Mean_with_slope": np.nan,
            "Delta_with_minus_no": np.nan,
            "t_stat": np.nan,
            "p_value": np.nan,
            "Significant_p_lt_0.05": False,
            "Better_model": "N/A",
            "scipy_available": SCIPY_AVAILABLE,
            "n_valid_fold_pairs": len(vals_A),
        })

df_ttest = pd.DataFrame(t_test_results)

print("\n========== Paired t-test ==========")
print(df_ttest.to_string(index=False))


# =========================================================
# 11. 完整数据集偏差数量统计汇总
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
        "n_all_data_points": len(y),
    })

df_final_average_summary = pd.DataFrame(final_average_records)

print("\n========== Fold all-data count summary ==========")
print(df_fold_all_data_count_summary.to_string(index=False))

print("\n========== Final average all-data count summary ==========")
print(df_final_average_summary.to_string(index=False))


# =========================================================
# 12. 整理保存结果
# =========================================================
df_fold_test_predictions = pd.concat(fold_test_prediction_dfs, ignore_index=True)
df_fold_all_data_predictions = pd.concat(fold_all_data_prediction_dfs, ignore_index=True)

df_pred_A = df_fold_test_predictions[
    df_fold_test_predictions["Method"] == "RF_desc_T"
].copy()

df_pred_B = df_fold_test_predictions[
    df_fold_test_predictions["Method"] == "RF_desc_T_slope"
].copy()

df_feature_importance_no = pd.DataFrame(feature_importance_no_records)
df_feature_importance_with = pd.DataFrame(feature_importance_with_records)

df_feature_importance_all = pd.concat(
    [df_feature_importance_no, df_feature_importance_with],
    ignore_index=True
)

if len(df_feature_importance_all) > 0:
    df_feature_importance_summary = (
        df_feature_importance_all
        .groupby(["model", "feature"], as_index=False)
        .agg(
            importance_mean=("importance", "mean"),
            importance_std=("importance", "std"),
        )
        .sort_values(["model", "importance_mean"], ascending=[True, False])
    )
else:
    df_feature_importance_summary = pd.DataFrame()

df_used_features = pd.DataFrame({
    "used_descriptor_feature": used_feature_cols,
})

df_removed_zero_features = pd.DataFrame({
    "removed_zero_descriptor_feature": removed_zero_feature_cols,
})

df_fold_info = pd.DataFrame(fold_info_records)

df_slope_info = pd.DataFrame([
    {
        "slope_file_used": str(slope_path_used),
        "slope_sheet_used": slope_sheet_used,
        "slope_key_col": slope_key_col,
        "slope_col": slope_col,
    }
])

run_info = pd.DataFrame([
    {"param": "descriptor_file", "value": str(descriptor_file)},
    {"param": "descriptor_sheet", "value": descriptor_sheet},
    {"param": "selected_feature_sheet", "value": selected_feature_sheet},
    {"param": "data_file", "value": str(data_file)},
    {"param": "data_sheet", "value": data_sheet},
    {"param": "slope_file_used", "value": str(slope_path_used)},
    {"param": "slope_sheet_used", "value": slope_sheet_used},

    {"param": "desc_key_col", "value": desc_key_col},
    {"param": "data_key_col", "value": data_key_col},
    {"param": "data_group_col", "value": data_group_col},
    {"param": "slope_key_col", "value": slope_key_col},

    {"param": "temp_col_actual", "value": temp_col_actual},
    {"param": "target_col", "value": target_col},
    {"param": "slope_col", "value": slope_col},

    {"param": "n_outer_folds", "value": n_outer_folds},
    {"param": "random_state", "value": random_state},
    {"param": "n_descriptor_features_original", "value": len(feature_cols)},
    {"param": "n_descriptor_features_used", "value": len(used_feature_cols)},
    {"param": "n_removed_zero_descriptor_features", "value": len(removed_zero_feature_cols)},
    {"param": "total_samples", "value": len(y)},
    {"param": "n_materials", "value": len(unique_materials)},

    {"param": "model_no_slope", "value": "RandomForestRegressor(desc + T_K)"},
    {"param": "model_with_slope", "value": "RandomForestRegressor(desc + T_K + slope_pred_surface_over_T)"},
    {"param": "rf_params", "value": str(rf_params)},

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
        "项目": "描述符文件",
        "内容": str(descriptor_file),
    },
    {
        "项目": "描述符 sheet",
        "内容": descriptor_sheet,
    },
    {
        "项目": "数据文件",
        "内容": str(data_file),
    },
    {
        "项目": "数据 sheet",
        "内容": data_sheet,
    },
    {
        "项目": "slope 文件",
        "内容": str(slope_path_used),
    },
    {
        "项目": "slope sheet",
        "内容": slope_sheet_used,
    },
    {
        "项目": "交叉验证方式",
        "内容": f"{n_outer_folds}-fold KFold，按物质 ID 划分，shuffle=True，random_state={random_state}",
    },
    {
        "项目": "方法1",
        "内容": "RF_desc_T：RandomForestRegressor，输入 [25 descriptors, T_K]",
    },
    {
        "项目": "方法2",
        "内容": "RF_desc_T_slope：RandomForestRegressor，输入 [25 descriptors, T_K, slope_pred_surface_over_T]",
    },
    {
        "项目": "是否包含子模型",
        "内容": "当前代码不训练子模型；读取外部 HistGB 子模型预测得到的 slope",
    },
    {
        "项目": "子模型预测对象",
        "内容": f"{slope_col}，用作方法2额外输入特征",
    },
    {
        "项目": "子模型类型",
        "内容": "外部文件名显示为 HistGB；本代码只读取预测结果，不在当前脚本内训练",
    },
    {
        "项目": "子模型参数",
        "内容": "当前代码无法从 slope 文件恢复；仅保存 slope 文件、sheet、列名和特征重要性",
    },
    {
        "项目": "slope 构造",
        "内容": "直接读取 slope_pred_surface_over_T，作为方法2额外输入特征；没有乘以 T",
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
        "内容": f"[{len(used_feature_cols)} 个描述符, T_K]，总维度 {len(used_feature_cols) + 1}",
    },
    {
        "项目": "方法2最终输入",
        "内容": f"[{len(used_feature_cols)} 个描述符, T_K, slope]，总维度 {len(used_feature_cols) + 2}",
    },
    {
        "项目": "偏差数量统计口径",
        "内容": "每个 fold 模型预测完整数据集，统计表面张力相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 取平均",
    },
])


# =========================================================
# 13. 保存结果到 Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    # 原有核心输出
    df_A.to_excel(writer, sheet_name="Fold_Metrics_No_Slope", index=False)
    df_B.to_excel(writer, sheet_name="Fold_Metrics_With_Slope", index=False)

    summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
    df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)

    df_pred_A.to_excel(writer, sheet_name="Predictions_No_Slope", index=False)
    df_pred_B.to_excel(writer, sheet_name="Predictions_With_Slope", index=False)

    # 新增输出
    df_fold_test_predictions.to_excel(writer, sheet_name="fold_test_predictions", index=False)
    df_fold_all_data_predictions.to_excel(writer, sheet_name="fold_all_data_predictions", index=False)
    df_fold_all_data_count_summary.to_excel(writer, sheet_name="fold_all_data_count_summary", index=False)
    df_final_average_summary.to_excel(writer, sheet_name="final_average_summary", index=False)

    # 特征和 slope 信息
    df_used_features.to_excel(writer, sheet_name="Used_Descriptor_Features", index=False)
    df_removed_zero_features.to_excel(writer, sheet_name="Removed_Zero_Descriptors", index=False)
    df_slope_info.to_excel(writer, sheet_name="slope_info", index=False)

    if len(df_feature_importance_all) > 0:
        df_feature_importance_all.to_excel(writer, sheet_name="Feature_Importance_AllFolds", index=False)
        df_feature_importance_summary.to_excel(writer, sheet_name="Feature_Importance_Summary", index=False)

    df_fold_info.to_excel(writer, sheet_name="Fold_Info", index=False)
    run_info.to_excel(writer, sheet_name="Run_Info", index=False)
    df_model_structure.to_excel(writer, sheet_name="model_structure", index=False)

    format_excel(writer)

print(f"\n保存完成: {output_file}")
print("主要输出 sheet:")
print("- Fold_Metrics_No_Slope")
print("- Fold_Metrics_With_Slope")
print("- Summary_Mean_Std")
print("- Paired_T_Test")
print("- Predictions_No_Slope")
print("- Predictions_With_Slope")
print("- fold_test_predictions")
print("- fold_all_data_predictions")
print("- fold_all_data_count_summary")
print("- final_average_summary")
print("- Used_Descriptor_Features")
print("- slope_info")
print("- Run_Info")
print("- model_structure")


# =========================================================
# 14. 最终方便复制输出
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


no_1, no_5, no_10 = get_final_counts("RF_desc_T")
with_1, with_5, with_10 = get_final_counts("RF_desc_T_slope")

print("\n方法1 全数据预测偏差 1%，5%，10%分别为：")
print(no_1)
print(no_5)
print(no_10)

print("\n方法2 全数据预测偏差 1%，5%，10%分别为：")
print(with_1)
print(with_5)
print(with_10)


# =========================================================
# 15. 代码结构打印
# =========================================================
print("\n========== 当前代码结构简要汇总 ==========")
print(f"预测对象：液体表面张力 sigma / {target_col}")
print(f"描述符文件：{descriptor_file}")
print(f"数据文件：{data_file}")
print(f"slope 文件：{slope_path_used}")
print(f"sheet 名称：{descriptor_sheet}, {data_sheet}, {slope_sheet_used}")
print(f"交叉验证：{n_outer_folds}-fold KFold，按物质 ID 划分")
print("方法1：RF_desc_T，RandomForestRegressor，输入 [descriptors, T_K]")
print("方法2：RF_desc_T_slope，RandomForestRegressor，输入 [descriptors, T_K, slope_pred_surface_over_T]")
print("子模型：当前代码不训练子模型，读取外部 HistGB 预测的 slope_pred_surface_over_T")
print(f"子模型预测列：{slope_col}")
print("子模型参数：当前代码无法从 slope 文件恢复，仅保存 slope 文件信息和特征重要性")
print("slope 构造：直接读取 slope_pred_surface_over_T，作为方法2额外输入特征；没有乘以 T")
print("baseline 构造：无")
print("residual 模型：无")
print(f"最终模型：RandomForestRegressor，参数：{rf_params}")
print("方法1最终输入：[descriptors, T_K]")
print("方法2最终输入：[descriptors, T_K, slope_pred_surface_over_T]")
print("偏差统计口径：每个 fold 模型预测完整数据集，统计表面张力相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 取平均")