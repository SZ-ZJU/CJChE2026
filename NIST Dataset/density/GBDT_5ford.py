# import pandas as pd
# import numpy as np
# from pathlib import Path
# from sklearn.model_selection import GroupKFold
# from sklearn.ensemble import GradientBoostingRegressor
# from sklearn.linear_model import Ridge
# from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
# from scipy.stats import ttest_rel
# import warnings
# warnings.filterwarnings("ignore")
#
# pd.set_option("display.float_format", "{:.10f}".format)
# np.set_printoptions(suppress=True, precision=10)
#
# # =========================================================
# # 0. 全局配置（与原始代码保持一致）
# # =========================================================
# input_file = Path("dataset_density_selected_by_two_k_with_density_T_interpolation_8points.xlsx")
# data_sheet = "Data_selected"
# groups_sheet = "Groups_selected"
# anchor_sheet_candidates = ["Interpolated_k1_k2", "Final_Model_Table", "Material_selected"]
#
# material_key_col = "material_key"
# temp_col = "T_K"
#
# density_col_candidates = [
#     "property_value", "value", "Density_kg_m3", "density_kg_m3",
#     "Density, kg/m3", "Mass density, kg/m3", "mass_density_kg_m3",
#     "Mass_Density_kg_m3", "rho_kg_m3", "rho", "density", "Density"
# ]
# anchor_temp_col_candidates = ["k1_times_boiling_T_K", "ref_T1_K", "reference_T1_K",
#                               "T_ref1_K", "T_anchor", "anchor_T", "anchor_T_ref1", "T_k1", "T1_K", "ref_T_K"]
# anchor_density_col_candidates = [
#     "property_interp_at_k1Tb", "density_interp_at_k1Tb", "Density_interp_at_k1Tb",
#     "density_ref1", "Density_ref1", "ref_density_1", "rho_ref1", "property_ref1",
#     "anchor_density", "anchor_value", "anchor_rho", "density_at_ref_T1", "Density_at_ref_T1", "density_ref_T1"
# ]
#
# n_group_features_to_use = 220
# use_fixed_group_position = True
# group_start_col_1based = 3
# group_end_col_1based = 222
#
# n_outer_folds = 5
# random_state = 42
#
# # GBDT 参数（直接模型）
# gbdt_params_direct = {
#     "n_estimators": 500,
#     "learning_rate": 0.03,
#     "max_depth": 3,
#     "min_samples_leaf": 3,
#     "subsample": 0.9,
#     "random_state": random_state,
# }
#
# # 锚点基线斜率模型参数
# use_ridge_for_slope = True
# slope_ridge_alpha = 1.0
#
# # 残差 GBDT 参数
# residual_gbdt_params = {
#     "n_estimators": 500,
#     "learning_rate": 0.03,
#     "max_depth": 3,
#     "min_samples_leaf": 3,
#     "subsample": 0.9,
#     "random_state": random_state,
# }
#
# # =========================================================
# # 1. 工具函数（复用原始代码）
# # =========================================================
# def is_valid_value(x):
#     if pd.isna(x): return False
#     s = str(x).strip()
#     if s == "" or s.lower() in ["nan","none","null","待定"]: return False
#     return True
#
# def clean_key_value(x):
#     if not is_valid_value(x): return np.nan
#     s = str(x).strip()
#     try:
#         f = float(s)
#         if np.isfinite(f) and abs(f - round(f)) < 1e-8:
#             return str(int(round(f)))
#     except Exception:
#         pass
#     return s
#
# def build_material_key(row):
#     for col in ["material_key", "original_material_index", "inchikey", "InChIKey",
#                 "inchi_key", "pubchem_inchikey", "PubChem_InChIKey", "cas",
#                 "compound_name", "formula"]:
#         if col in row.index and is_valid_value(row[col]):
#             if col == "material_key":
#                 return clean_key_value(row[col])
#             return f"{col}:{str(row[col]).strip()}"
#     return "unknown_material"
#
# def find_first_existing_col(df, candidates, col_type, required=True):
#     for col in candidates:
#         if col in df.columns:
#             return col
#     norm_map = {str(c).lower().replace(" ", "").replace("_", ""): c for c in df.columns}
#     for col in candidates:
#         key = str(col).lower().replace(" ", "").replace("_", "")
#         if key in norm_map:
#             return norm_map[key]
#     if required:
#         raise ValueError(f"没有找到 {col_type} 列。候选: {candidates}")
#     return None
#
# def identify_group_columns(df_groups, n=220):
#     if use_fixed_group_position:
#         start_idx = group_start_col_1based - 1
#         end_excl = group_end_col_1based
#         if len(df_groups.columns) < end_excl:
#             raise ValueError(f"基团列数不足，需要到第 {group_end_col_1based} 列")
#         group_cols = list(df_groups.columns[start_idx:end_excl])
#         if len(group_cols) != n:
#             raise ValueError(f"固定位置识别 {len(group_cols)} 个基团，需要 {n}")
#         return group_cols
#     else:
#         raise ValueError("请设置 use_fixed_group_position=True")
#
# def average_relative_deviation(y_true, y_pred, eps=1e-12):
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#     mask = np.isfinite(y_true) & np.isfinite(y_pred) & (np.abs(y_true) > eps)
#     if mask.sum() == 0:
#         return np.nan
#     return np.mean(np.abs((y_pred[mask] - y_true[mask]) / y_true[mask])) * 100.0
#
# def evaluate_metrics(y_true, y_pred):
#     mask = np.isfinite(y_true) & np.isfinite(y_pred)
#     y_true = y_true[mask]
#     y_pred = y_pred[mask]
#     if len(y_true) == 0:
#         return {"R2": np.nan, "MSE": np.nan, "RMSE": np.nan, "MAE": np.nan, "ARD": np.nan}
#     r2 = r2_score(y_true, y_pred)
#     mse = mean_squared_error(y_true, y_pred)
#     rmse = np.sqrt(mse)
#     mae = mean_absolute_error(y_true, y_pred)
#     ard = average_relative_deviation(y_true, y_pred)
#     return {"R2": r2, "MSE": mse, "RMSE": rmse, "MAE": mae, "ARD": ard}
#
# # =========================================================
# # 2. 读取原始数据
# # =========================================================
# xls = pd.ExcelFile(input_file)
# print("输入文件包含的 sheet:", xls.sheet_names)
#
# if data_sheet not in xls.sheet_names:
#     raise ValueError(f"没有找到 sheet: {data_sheet}")
# if groups_sheet not in xls.sheet_names:
#     raise ValueError(f"没有找到 sheet: {groups_sheet}")
#
# anchor_sheet = None
# for s in anchor_sheet_candidates:
#     if s in xls.sheet_names:
#         anchor_sheet = s
#         break
# if anchor_sheet is None:
#     raise ValueError(f"没有找到锚点 sheet，候选: {anchor_sheet_candidates}")
#
# df_data = pd.read_excel(input_file, sheet_name=data_sheet)
# df_groups = pd.read_excel(input_file, sheet_name=groups_sheet)
# df_anchor = pd.read_excel(input_file, sheet_name=anchor_sheet)
#
# print(f"Data_selected 行数: {len(df_data)}")
# print(f"Groups_selected 物质数: {len(df_groups)}")
# print(f"Anchor sheet: {anchor_sheet}, 行数: {len(df_anchor)}")
#
# # 构造 / 清洗 material_key
# for df in [df_data, df_groups, df_anchor]:
#     if material_key_col not in df.columns:
#         df[material_key_col] = df.apply(build_material_key, axis=1)
#     df[material_key_col] = df[material_key_col].apply(clean_key_value)
#
# # 找到列名
# density_col = find_first_existing_col(df_data, density_col_candidates, "density", required=True)
# anchor_temp_col = find_first_existing_col(df_anchor, anchor_temp_col_candidates, "锚点温度", required=True)
# anchor_density_col = find_first_existing_col(df_anchor, anchor_density_col_candidates, "锚点密度", required=True)
#
# print(f"密度列: {density_col}, 温度列: {temp_col}")
# print(f"锚点温度列: {anchor_temp_col}, 锚点密度列: {anchor_density_col}")
#
# # 数值转换
# df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
# df_data[density_col] = pd.to_numeric(df_data[density_col], errors="coerce")
# df_anchor[anchor_temp_col] = pd.to_numeric(df_anchor[anchor_temp_col], errors="coerce")
# df_anchor[anchor_density_col] = pd.to_numeric(df_anchor[anchor_density_col], errors="coerce")
#
# # 基团列处理
# group_cols_220 = identify_group_columns(df_groups, n_group_features_to_use)
# df_groups_numeric = df_groups[group_cols_220].apply(pd.to_numeric, errors="coerce").fillna(0.0)
# nonzero_mask = df_groups_numeric.abs().sum(axis=0) != 0
# used_group_cols = df_groups_numeric.columns[nonzero_mask].tolist()
# print(f"有效基团数: {len(used_group_cols)}")
#
# # 合并锚点信息（每个物质一个 anchor 值）
# anchor_info = df_anchor[[material_key_col, anchor_temp_col, anchor_density_col]].drop_duplicates()
# anchor_info = anchor_info.rename(columns={anchor_temp_col: "anchor_T", anchor_density_col: "anchor_rho"})
#
# # 合并基团和锚点到数据表
# df_long = df_data.merge(df_groups[[material_key_col] + used_group_cols], on=material_key_col, how="inner")
# df_long = df_long.merge(anchor_info, on=material_key_col, how="inner")
# df_long = df_long.dropna(subset=[temp_col, density_col] + used_group_cols + ["anchor_T", "anchor_rho"])
# df_long = df_long[(df_long[temp_col] > 0) & (df_long[density_col] > 0)].copy()
#
# # 提取数组
# X_groups = df_long[used_group_cols].values.astype(float)
# T = df_long[temp_col].values.astype(float)
# rho_true = df_long[density_col].values.astype(float)
# anchor_T_vals = df_long["anchor_T"].values.astype(float)
# anchor_rho_vals = df_long["anchor_rho"].values.astype(float)
# material_keys = df_long[material_key_col].values
#
# unique_materials = np.unique(material_keys)
# print(f"总样本点数: {len(rho_true)}, 总物质数: {len(unique_materials)}")
#
# # =========================================================
# # 3. 5 折交叉验证（按物质）
# # =========================================================
# gkf = GroupKFold(n_splits=n_outer_folds)
# metrics_direct = []
# metrics_residual = []
#
# for fold, (train_mat_idx, test_mat_idx) in enumerate(gkf.split(unique_materials, groups=unique_materials)):
#     train_mats = unique_materials[train_mat_idx]
#     test_mats = unique_materials[test_mat_idx]
#
#     train_mask = np.isin(material_keys, train_mats)
#     test_mask = np.isin(material_keys, test_mats)
#
#     X_train_groups = X_groups[train_mask]
#     X_test_groups = X_groups[test_mask]
#     y_train = rho_true[train_mask]
#     y_test = rho_true[test_mask]
#     T_train = T[train_mask]
#     T_test = T[test_mask]
#     anchor_T_train = anchor_T_vals[train_mask]
#     anchor_T_test = anchor_T_vals[test_mask]
#     anchor_rho_train = anchor_rho_vals[train_mask]
#     anchor_rho_test = anchor_rho_vals[test_mask]
#     material_train = material_keys[train_mask]
#
#     # ---------- 模型A：直接 GBDT ----------
#     X_train_A = np.hstack([X_train_groups, T_train.reshape(-1,1)])
#     X_test_A = np.hstack([X_test_groups, T_test.reshape(-1,1)])
#     model_A = GradientBoostingRegressor(**gbdt_params_direct)
#     model_A.fit(X_train_A, y_train)
#     y_pred_A = model_A.predict(X_test_A)
#
#     # ---------- 模型B：锚点基线 + 残差 GBDT ----------
#     # 步骤1：计算训练集每个物质的真实斜率（基于 anchor 点）
#     mat_slope_true = {}
#     for mat in train_mats:
#         mat_idx = material_train == mat
#         if mat_idx.sum() >= 2:
#             T_mat = T_train[mat_idx]
#             rho_mat = y_train[mat_idx]
#             aT = anchor_T_train[mat_idx][0]
#             arho = anchor_rho_train[mat_idx][0]
#             dx = T_mat - aT
#             dy = rho_mat - arho
#             valid = (np.abs(dx) > 1e-10) & np.isfinite(dx) & np.isfinite(dy)
#             if valid.sum() >= 2:
#                 slope = np.sum(dx[valid] * dy[valid]) / np.sum(dx[valid]**2)
#                 mat_slope_true[mat] = slope
#             else:
#                 mat_slope_true[mat] = np.nan
#         else:
#             mat_slope_true[mat] = np.nan
#
#     # 收集有效训练数据（有斜率的物质）
#     train_slope_mats = [m for m in train_mats if not np.isnan(mat_slope_true[m])]
#     X_slope_train = []
#     y_slope_train = []
#     for m in train_slope_mats:
#         idx = np.where(material_train == m)[0][0]
#         X_slope_train.append(X_train_groups[idx])
#         y_slope_train.append(mat_slope_true[m])
#     X_slope_train = np.array(X_slope_train)
#     y_slope_train = np.array(y_slope_train)
#
#     if len(y_slope_train) == 0:
#         # 无法训练斜率模型，该折模型B失败
#         y_pred_B = np.full(len(y_test), np.nan)
#     else:
#         # 训练斜率模型（Ridge 预测 slope）
#         slope_model = Ridge(alpha=slope_ridge_alpha, fit_intercept=True)
#         slope_model.fit(X_slope_train, y_slope_train)
#
#         # 预测测试集物质的 slope
#         test_mats_list = list(test_mats)
#         X_test_groups_unique = []
#         for m in test_mats_list:
#             idx = np.where(material_keys[test_mask] == m)[0][0]
#             X_test_groups_unique.append(X_test_groups[idx])
#         X_test_groups_unique = np.array(X_test_groups_unique)
#         pred_slope = slope_model.predict(X_test_groups_unique)
#         mat_to_slope = dict(zip(test_mats_list, pred_slope))
#
#         # 测试集基线预测
#         baseline_rho_test = []
#         for i, m in enumerate(material_keys[test_mask]):
#             slope = mat_to_slope.get(m, np.nan)
#             if np.isfinite(slope):
#                 base = anchor_rho_test[i] + slope * (T_test[i] - anchor_T_test[i])
#             else:
#                 base = np.nan
#             baseline_rho_test.append(base)
#         baseline_rho_test = np.array(baseline_rho_test)
#
#         # 训练集基线预测（用于残差模型训练）
#         train_baseline = []
#         for i, m in enumerate(material_train):
#             slope = mat_slope_true.get(m, np.nan)
#             if np.isfinite(slope):
#                 base = anchor_rho_train[i] + slope * (T_train[i] - anchor_T_train[i])
#             else:
#                 base = np.nan
#             train_baseline.append(base)
#         train_baseline = np.array(train_baseline)
#
#         # 残差 GBDT 训练（用训练集数据）
#         delta_T_train = T_train - anchor_T_train
#         X_res_train = np.hstack([X_train_groups, T_train.reshape(-1,1), delta_T_train.reshape(-1,1),
#                                  anchor_T_train.reshape(-1,1), anchor_rho_train.reshape(-1,1)])
#         y_res_train = y_train - train_baseline
#
#         valid_res = np.isfinite(X_res_train).all(axis=1) & np.isfinite(y_res_train)
#         if valid_res.sum() == 0:
#             y_pred_B = np.full(len(y_test), np.nan)
#         else:
#             res_model = GradientBoostingRegressor(**residual_gbdt_params)
#             res_model.fit(X_res_train[valid_res], y_res_train[valid_res])
#
#             # 测试集残差预测
#             delta_T_test = T_test - anchor_T_test
#             X_res_test = np.hstack([X_test_groups, T_test.reshape(-1,1), delta_T_test.reshape(-1,1),
#                                     anchor_T_test.reshape(-1,1), anchor_rho_test.reshape(-1,1)])
#             valid_res_test = np.isfinite(X_res_test).all(axis=1)
#             res_pred = np.full(len(y_test), np.nan)
#             res_pred[valid_res_test] = res_model.predict(X_res_test[valid_res_test])
#             y_pred_B = baseline_rho_test + res_pred
#
#     # 计算指标
#     met_A = evaluate_metrics(y_test, y_pred_A)
#     met_B = evaluate_metrics(y_test, y_pred_B)
#     met_A["fold"] = fold+1
#     met_B["fold"] = fold+1
#     metrics_direct.append(met_A)
#     metrics_residual.append(met_B)
#
#     print(f"\nFold {fold+1}:")
#     print(f"  Direct GBDT       - R2={met_A['R2']:.4f}, RMSE={met_A['RMSE']:.4f}, MAE={met_A['MAE']:.4f}, ARD={met_A['ARD']:.2f}%")
#     print(f"  Anchor+Residual   - R2={met_B['R2']:.4f}, RMSE={met_B['RMSE']:.4f}, MAE={met_B['MAE']:.4f}, ARD={met_B['ARD']:.2f}%")
#
# # =========================================================
# # 4. 汇总统计与配对 t 检验
# # =========================================================
# df_direct = pd.DataFrame(metrics_direct)
# df_residual = pd.DataFrame(metrics_residual)
#
# def summarize(df, name):
#     rows = []
#     for metric in ["R2", "MSE", "RMSE", "MAE", "ARD"]:
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
# summary_direct = summarize(df_direct, "Direct GBDT")
# summary_residual = summarize(df_residual, "Anchor+Residual GBDT")
# summary_all = pd.concat([summary_direct, summary_residual], ignore_index=True)
#
# print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
# print(summary_all.to_string(index=False))
#
# # 配对 t 检验
# t_test_results = []
# for metric in ["R2", "MSE", "RMSE", "MAE", "ARD"]:
#     vals_d = df_direct[metric].dropna().values
#     vals_r = df_residual[metric].dropna().values
#     if len(vals_d) == len(vals_r) and len(vals_d) > 1:
#         t_stat, p_val = ttest_rel(vals_d, vals_r)
#         if metric == "R2":
#             better = "residual" if np.mean(vals_r) > np.mean(vals_d) else "direct"
#             sig = p_val < 0.05
#         else:
#             better = "residual" if np.mean(vals_r) < np.mean(vals_d) else "direct"
#             sig = p_val < 0.05
#         t_test_results.append({
#             "Metric": metric,
#             "Mean_direct": f"{np.mean(vals_d):.4f}",
#             "Mean_residual": f"{np.mean(vals_r):.4f}",
#             "p-value": f"{p_val:.4e}",
#             "Significant(p<0.05)": sig,
#             "Better model": better
#         })
#
# df_ttest = pd.DataFrame(t_test_results)
# print("\n========== Paired t-test ==========")
# print(df_ttest.to_string(index=False))
#
# # =========================================================
# # 5. 保存结果到 Excel
# # =========================================================
# output_file = "density_5fold_CV_comparison.xlsx"
# with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
#     df_direct.to_excel(writer, sheet_name="Fold_Metrics_Direct", index=False)
#     df_residual.to_excel(writer, sheet_name="Fold_Metrics_Residual", index=False)
#     summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
#     df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)
#
#     pd.DataFrame([
#         {"param": "n_outer_folds", "value": n_outer_folds},
#         {"param": "random_state", "value": random_state},
#         {"param": "direct_GBDT_params", "value": str(gbdt_params_direct)},
#         {"param": "residual_GBDT_params", "value": str(residual_gbdt_params)},
#         {"param": "slope_ridge_alpha", "value": slope_ridge_alpha},
#     ]).to_excel(writer, sheet_name="Run_Info", index=False)
#
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
#             ws.column_dimensions[col_letter].width = min(max_len+2, 40)
#
# print(f"\n结果已保存至: {output_file}")


import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.model_selection import GroupKFold
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from scipy.stats import ttest_rel

import warnings
warnings.filterwarnings("ignore")

pd.set_option("display.float_format", "{:.10f}".format)
np.set_printoptions(suppress=True, precision=10)


# =========================================================
# 0. 全局配置（与原始代码保持一致）
# =========================================================
input_file = Path("dataset_density_selected_by_two_k_with_density_T_interpolation_8points.xlsx")

data_sheet = "Data_selected"
groups_sheet = "Groups_selected"
anchor_sheet_candidates = ["Interpolated_k1_k2", "Final_Model_Table", "Material_selected"]

output_file = Path("density_5fold_CV_comparison.xlsx")

material_key_col = "material_key"
temp_col = "T_K"

density_col_candidates = [
    "property_value", "value", "Density_kg_m3", "density_kg_m3",
    "Density, kg/m3", "Mass density, kg/m3", "mass_density_kg_m3",
    "Mass_Density_kg_m3", "rho_kg_m3", "rho", "density", "Density"
]

anchor_temp_col_candidates = [
    "k1_times_boiling_T_K", "ref_T1_K", "reference_T1_K",
    "T_ref1_K", "T_anchor", "anchor_T", "anchor_T_ref1",
    "T_k1", "T1_K", "ref_T_K"
]

anchor_density_col_candidates = [
    "property_interp_at_k1Tb", "density_interp_at_k1Tb", "Density_interp_at_k1Tb",
    "density_ref1", "Density_ref1", "ref_density_1", "rho_ref1", "property_ref1",
    "anchor_density", "anchor_value", "anchor_rho", "density_at_ref_T1",
    "Density_at_ref_T1", "density_ref_T1"
]

n_group_features_to_use = 220
use_fixed_group_position = True
group_start_col_1based = 3
group_end_col_1based = 222

n_outer_folds = 5
random_state = 42

# GBDT 参数（直接模型）
gbdt_params_direct = {
    "n_estimators": 500,
    "learning_rate": 0.03,
    "max_depth": 3,
    "min_samples_leaf": 3,
    "subsample": 0.9,
    "random_state": random_state,
}

# 锚点基线 slope 模型参数
use_ridge_for_slope = True
slope_ridge_alpha = 1.0

# 残差 GBDT 参数
residual_gbdt_params = {
    "n_estimators": 500,
    "learning_rate": 0.03,
    "max_depth": 3,
    "min_samples_leaf": 3,
    "subsample": 0.9,
    "random_state": random_state,
}


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


def clean_key_value(x):
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


def build_material_key(row):
    for col in [
        "material_key", "original_material_index", "inchikey", "InChIKey",
        "inchi_key", "pubchem_inchikey", "PubChem_InChIKey", "cas",
        "compound_name", "formula"
    ]:
        if col in row.index and is_valid_value(row[col]):
            if col == "material_key":
                return clean_key_value(row[col])
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


def find_first_existing_col(df, candidates, col_type, required=True):
    for col in candidates:
        if col in df.columns:
            return col

    norm_map = {normalize_colname(c): c for c in df.columns}

    for col in candidates:
        key = normalize_colname(col)
        if key in norm_map:
            return norm_map[key]

    if required:
        raise ValueError(f"没有找到 {col_type} 列。候选: {candidates}")

    return None


def identify_group_columns(df_groups, n=220):
    if use_fixed_group_position:
        start_idx = group_start_col_1based - 1
        end_excl = group_end_col_1based

        if len(df_groups.columns) < end_excl:
            raise ValueError(f"基团列数不足，需要到第 {group_end_col_1based} 列")

        group_cols = list(df_groups.columns[start_idx:end_excl])

        if len(group_cols) != n:
            raise ValueError(f"固定位置识别 {len(group_cols)} 个基团，需要 {n}")

        return group_cols

    raise ValueError("请设置 use_fixed_group_position=True")


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


def average_relative_deviation(y_true, y_pred):
    rel_err = safe_relative_error_percent(y_true, y_pred)

    if np.any(np.isfinite(rel_err)):
        return float(np.nanmean(rel_err))

    return np.nan


def evaluate_metrics(y_true, y_pred):
    """
    返回 R2, MSE, RMSE, MAE, ARD (%)，并保留误差区间比例和数量。
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
            "ARD": np.nan,
            "max_rel_err_percent": np.nan,
            "<1% ratio(%)": np.nan,
            "<5% ratio(%)": np.nan,
            "<10% ratio(%)": np.nan,
            "<1% count": 0.0,
            "<5% count": 0.0,
            "<10% count": 0.0,
        }

    r2 = r2_score(y_true_valid, y_pred_valid) if len(y_true_valid) > 1 else np.nan
    mse = mean_squared_error(y_true_valid, y_pred_valid)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_true_valid, y_pred_valid)
    ard = average_relative_deviation(y_true_valid, y_pred_valid)

    rel_err = safe_relative_error_percent(y_true_valid, y_pred_valid)
    n_valid_rel = int(np.sum(np.isfinite(rel_err)))

    if n_valid_rel > 0:
        c1 = float(np.nansum(rel_err < 1.0))
        c5 = float(np.nansum(rel_err < 5.0))
        c10 = float(np.nansum(rel_err < 10.0))

        r1 = c1 / n_valid_rel * 100.0
        r5 = c5 / n_valid_rel * 100.0
        r10 = c10 / n_valid_rel * 100.0

        max_rel = float(np.nanmax(rel_err))
    else:
        c1 = c5 = c10 = 0.0
        r1 = r5 = r10 = np.nan
        max_rel = np.nan

    return {
        "n_points": len(y_true_valid),
        "R2": r2,
        "MSE": mse,
        "RMSE": rmse,
        "MAE": mae,
        "ARD": ard,
        "max_rel_err_percent": max_rel,
        "<1% ratio(%)": r1,
        "<5% ratio(%)": r5,
        "<10% ratio(%)": r10,
        "<1% count": c1,
        "<5% count": c5,
        "<10% count": c10,
    }


def summarize(df, name):
    rows = []

    for metric in [
        "R2",
        "MSE",
        "RMSE",
        "MAE",
        "ARD",
        "max_rel_err_percent",
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


def make_prediction_df(
    fold,
    dataset_name,
    method,
    sample_indices,
    y_true,
    y_pred,
    baseline_pred=None,
    residual_pred=None,
    slope_pred=None,
):
    sample_indices = np.asarray(sample_indices, dtype=int)
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    rel_err = safe_relative_error_percent(y_true, y_pred)

    df_out = pd.DataFrame({
        "fold": fold,
        "dataset": dataset_name,
        "Method": method,
        "sample_index": sample_indices,
        material_key_col: material_keys[sample_indices],
        "T_K": T[sample_indices],
        "rho_true": y_true,
        "rho_pred": y_pred,
        "error": y_pred - y_true,
        "absolute_error": np.abs(y_pred - y_true),
        "relative_error_percent": rel_err,
        "anchor_T": anchor_T_vals[sample_indices],
        "anchor_rho": anchor_rho_vals[sample_indices],
        "delta_T": T[sample_indices] - anchor_T_vals[sample_indices],
    })

    if slope_pred is not None:
        df_out["slope_pred"] = slope_pred

    if baseline_pred is not None:
        df_out["baseline_rho_pred"] = baseline_pred
        df_out["baseline_error"] = baseline_pred - y_true
        df_out["baseline_relative_error_percent"] = safe_relative_error_percent(y_true, baseline_pred)

    if residual_pred is not None:
        df_out["residual_pred"] = residual_pred
        if baseline_pred is not None:
            df_out["residual_target"] = y_true - baseline_pred

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
            df_out[col] = df_long[col].values[sample_indices]

    return df_out


def build_direct_features(indices):
    indices = np.asarray(indices, dtype=int)

    return np.hstack([
        X_groups[indices],
        T[indices].reshape(-1, 1),
    ])


def build_residual_features(indices):
    indices = np.asarray(indices, dtype=int)
    delta_T = T[indices] - anchor_T_vals[indices]

    return np.hstack([
        X_groups[indices],
        T[indices].reshape(-1, 1),
        delta_T.reshape(-1, 1),
        anchor_T_vals[indices].reshape(-1, 1),
        anchor_rho_vals[indices].reshape(-1, 1),
    ])


def compute_true_anchor_slopes(train_mats, train_indices):
    """
    对训练集每个物质计算真实锚点 slope：
        slope = sum((T-anchor_T)*(rho-anchor_rho)) / sum((T-anchor_T)^2)

    只使用训练集物质，避免测试物质信息泄露。
    """
    train_mats = np.asarray(train_mats)
    train_indices = np.asarray(train_indices, dtype=int)

    mat_slope_true = {}

    for mat in train_mats:
        idx = train_indices[material_keys[train_indices] == mat]

        if len(idx) >= 2:
            T_mat = T[idx]
            rho_mat = rho_true[idx]
            aT = anchor_T_vals[idx][0]
            arho = anchor_rho_vals[idx][0]

            dx = T_mat - aT
            dy = rho_mat - arho

            valid = (
                (np.abs(dx) > 1e-10)
                & np.isfinite(dx)
                & np.isfinite(dy)
            )

            if valid.sum() >= 2:
                slope = np.sum(dx[valid] * dy[valid]) / np.sum(dx[valid] ** 2)
                mat_slope_true[mat] = slope
            else:
                mat_slope_true[mat] = np.nan
        else:
            mat_slope_true[mat] = np.nan

    return mat_slope_true


def train_slope_model(train_mats, train_indices, mat_slope_true):
    """
    用训练物质的真实 slope 训练 Ridge slope 模型。
    """
    train_slope_mats = [
        m for m in train_mats
        if m in mat_slope_true and np.isfinite(mat_slope_true[m])
    ]

    X_slope_train = []
    y_slope_train = []

    for m in train_slope_mats:
        idx = train_indices[material_keys[train_indices] == m][0]
        X_slope_train.append(X_groups[idx])
        y_slope_train.append(mat_slope_true[m])

    X_slope_train = np.asarray(X_slope_train, dtype=float)
    y_slope_train = np.asarray(y_slope_train, dtype=float)

    if len(y_slope_train) == 0:
        return None, train_slope_mats, X_slope_train, y_slope_train

    if use_ridge_for_slope:
        slope_model = Ridge(alpha=slope_ridge_alpha, fit_intercept=True)
    else:
        raise ValueError("当前代码保留原始设计：使用 Ridge slope model。")

    slope_model.fit(X_slope_train, y_slope_train)

    return slope_model, train_slope_mats, X_slope_train, y_slope_train


def predict_slope_for_indices(indices, slope_model):
    """
    对任意样本 indices 根据物质预测 slope。
    每个物质只预测一次，再映射到该物质所有温度点。
    """
    indices = np.asarray(indices, dtype=int)

    slope_pred_rows = np.full(len(indices), np.nan, dtype=float)

    if slope_model is None or len(indices) == 0:
        return slope_pred_rows

    mats = material_keys[indices]
    unique_mats_for_pred = np.unique(mats)

    mat_to_slope_pred = {}

    X_unique = []
    mat_order = []

    for mat in unique_mats_for_pred:
        idx_first = indices[mats == mat][0]
        X_unique.append(X_groups[idx_first])
        mat_order.append(mat)

    X_unique = np.asarray(X_unique, dtype=float)

    valid_unique = np.isfinite(X_unique).all(axis=1)

    pred_unique = np.full(len(mat_order), np.nan, dtype=float)

    if valid_unique.sum() > 0:
        pred_unique[valid_unique] = slope_model.predict(X_unique[valid_unique])

    for mat, slope in zip(mat_order, pred_unique):
        mat_to_slope_pred[mat] = slope

    for i, sample_idx in enumerate(indices):
        mat = material_keys[sample_idx]
        slope_pred_rows[i] = mat_to_slope_pred.get(mat, np.nan)

    return slope_pred_rows


def make_baseline_from_slope(indices, slope_pred_rows):
    indices = np.asarray(indices, dtype=int)
    slope_pred_rows = np.asarray(slope_pred_rows, dtype=float)

    baseline = (
        anchor_rho_vals[indices]
        + slope_pred_rows * (T[indices] - anchor_T_vals[indices])
    )

    return baseline


def train_and_predict_methodB(train_mats, train_indices, pred_indices):
    """
    方法B：
    1. 训练集内计算真实锚点 slope；
    2. 用 Ridge 基于 Nk 预测 slope；
    3. 用预测 slope 构造 baseline；
    4. 用 GBDT 拟合 residual；
    5. 对 pred_indices 输出 final、baseline、residual、slope。
    """
    train_mats = np.asarray(train_mats)
    train_indices = np.asarray(train_indices, dtype=int)
    pred_indices = np.asarray(pred_indices, dtype=int)

    mat_slope_true = compute_true_anchor_slopes(train_mats, train_indices)

    slope_model, train_slope_mats, X_slope_train, y_slope_train = train_slope_model(
        train_mats=train_mats,
        train_indices=train_indices,
        mat_slope_true=mat_slope_true,
    )

    if slope_model is None:
        final_pred = np.full(len(pred_indices), np.nan, dtype=float)
        baseline_pred = np.full(len(pred_indices), np.nan, dtype=float)
        residual_pred = np.full(len(pred_indices), np.nan, dtype=float)
        slope_pred = np.full(len(pred_indices), np.nan, dtype=float)

        return {
            "final_pred": final_pred,
            "baseline_pred": baseline_pred,
            "residual_pred": residual_pred,
            "slope_pred": slope_pred,
            "slope_model": None,
            "res_model": None,
            "mat_slope_true": mat_slope_true,
            "train_slope_mats": train_slope_mats,
            "X_slope_train": X_slope_train,
            "y_slope_train": y_slope_train,
        }

    # ---------- 训练集 baseline ----------
    slope_train_pred = predict_slope_for_indices(train_indices, slope_model)
    baseline_train = make_baseline_from_slope(train_indices, slope_train_pred)

    # ---------- 残差模型训练 ----------
    X_res_train = build_residual_features(train_indices)
    y_res_train = rho_true[train_indices] - baseline_train

    valid_res = (
        np.isfinite(X_res_train).all(axis=1)
        & np.isfinite(y_res_train)
    )

    if valid_res.sum() == 0:
        final_pred = np.full(len(pred_indices), np.nan, dtype=float)
        baseline_pred = np.full(len(pred_indices), np.nan, dtype=float)
        residual_pred = np.full(len(pred_indices), np.nan, dtype=float)
        slope_pred = np.full(len(pred_indices), np.nan, dtype=float)

        return {
            "final_pred": final_pred,
            "baseline_pred": baseline_pred,
            "residual_pred": residual_pred,
            "slope_pred": slope_pred,
            "slope_model": slope_model,
            "res_model": None,
            "mat_slope_true": mat_slope_true,
            "train_slope_mats": train_slope_mats,
            "X_slope_train": X_slope_train,
            "y_slope_train": y_slope_train,
        }

    res_model = GradientBoostingRegressor(**residual_gbdt_params)
    res_model.fit(X_res_train[valid_res], y_res_train[valid_res])

    # ---------- pred_indices baseline + residual ----------
    slope_pred = predict_slope_for_indices(pred_indices, slope_model)
    baseline_pred = make_baseline_from_slope(pred_indices, slope_pred)

    X_res_pred = build_residual_features(pred_indices)
    residual_pred = np.full(len(pred_indices), np.nan, dtype=float)

    valid_pred = (
        np.isfinite(X_res_pred).all(axis=1)
        & np.isfinite(baseline_pred)
    )

    if valid_pred.sum() > 0:
        residual_pred[valid_pred] = res_model.predict(X_res_pred[valid_pred])

    final_pred = baseline_pred + residual_pred

    return {
        "final_pred": final_pred,
        "baseline_pred": baseline_pred,
        "residual_pred": residual_pred,
        "slope_pred": slope_pred,
        "slope_model": slope_model,
        "res_model": res_model,
        "mat_slope_true": mat_slope_true,
        "train_slope_mats": train_slope_mats,
        "X_slope_train": X_slope_train,
        "y_slope_train": y_slope_train,
    }


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
# 2. 读取原始数据
# =========================================================
xls = pd.ExcelFile(input_file)

print("输入文件包含的 sheet:", xls.sheet_names)

if data_sheet not in xls.sheet_names:
    raise ValueError(f"没有找到 sheet: {data_sheet}")

if groups_sheet not in xls.sheet_names:
    raise ValueError(f"没有找到 sheet: {groups_sheet}")

anchor_sheet = None

for s in anchor_sheet_candidates:
    if s in xls.sheet_names:
        anchor_sheet = s
        break

if anchor_sheet is None:
    raise ValueError(f"没有找到锚点 sheet，候选: {anchor_sheet_candidates}")

df_data = pd.read_excel(input_file, sheet_name=data_sheet)
df_groups = pd.read_excel(input_file, sheet_name=groups_sheet)
df_anchor = pd.read_excel(input_file, sheet_name=anchor_sheet)

print(f"Data_selected 行数: {len(df_data)}")
print(f"Groups_selected 物质数: {len(df_groups)}")
print(f"Anchor sheet: {anchor_sheet}, 行数: {len(df_anchor)}")


# =========================================================
# 3. 构造 / 清洗 material_key
# =========================================================
for df in [df_data, df_groups, df_anchor]:
    if material_key_col not in df.columns:
        df[material_key_col] = df.apply(build_material_key, axis=1)

    df[material_key_col] = df[material_key_col].apply(clean_key_value)


# =========================================================
# 4. 找到列名
# =========================================================
density_col = find_first_existing_col(
    df_data,
    density_col_candidates,
    "density",
    required=True,
)

anchor_temp_col = find_first_existing_col(
    df_anchor,
    anchor_temp_col_candidates,
    "锚点温度",
    required=True,
)

anchor_density_col = find_first_existing_col(
    df_anchor,
    anchor_density_col_candidates,
    "锚点密度",
    required=True,
)

print(f"密度列: {density_col}, 温度列: {temp_col}")
print(f"锚点温度列: {anchor_temp_col}, 锚点密度列: {anchor_density_col}")

df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
df_data[density_col] = pd.to_numeric(df_data[density_col], errors="coerce")
df_anchor[anchor_temp_col] = pd.to_numeric(df_anchor[anchor_temp_col], errors="coerce")
df_anchor[anchor_density_col] = pd.to_numeric(df_anchor[anchor_density_col], errors="coerce")


# =========================================================
# 5. 基团列处理
# =========================================================
group_cols_220 = identify_group_columns(
    df_groups,
    n_group_features_to_use,
)

df_groups_numeric = (
    df_groups[group_cols_220]
    .apply(pd.to_numeric, errors="coerce")
    .fillna(0.0)
)

nonzero_mask = df_groups_numeric.abs().sum(axis=0) != 0

used_group_cols = df_groups_numeric.columns[nonzero_mask].tolist()
removed_zero_group_cols = df_groups_numeric.columns[~nonzero_mask].tolist()

print(f"有效基团数: {len(used_group_cols)}")
print(f"删除全零基团数: {len(removed_zero_group_cols)}")


# =========================================================
# 6. 合并锚点信息
# =========================================================
anchor_info = (
    df_anchor[[material_key_col, anchor_temp_col, anchor_density_col]]
    .drop_duplicates(subset=[material_key_col])
    .copy()
)

anchor_info = anchor_info.rename(
    columns={
        anchor_temp_col: "anchor_T",
        anchor_density_col: "anchor_rho",
    }
)

# 合并基团和锚点到数据表
df_long = df_data.merge(
    df_groups[[material_key_col] + used_group_cols],
    on=material_key_col,
    how="inner",
)

df_long = df_long.merge(
    anchor_info,
    on=material_key_col,
    how="inner",
)

df_long = df_long.dropna(
    subset=[temp_col, density_col] + used_group_cols + ["anchor_T", "anchor_rho"]
)

df_long = df_long[
    (df_long[temp_col] > 0)
    & (df_long[density_col] > 0)
].copy()

df_long = df_long.reset_index(drop=True)

# 提取数组
X_groups = df_long[used_group_cols].values.astype(float)
T = df_long[temp_col].values.astype(float)
rho_true = df_long[density_col].values.astype(float)
anchor_T_vals = df_long["anchor_T"].values.astype(float)
anchor_rho_vals = df_long["anchor_rho"].values.astype(float)
material_keys = df_long[material_key_col].values.astype(str)

unique_materials = np.unique(material_keys)
all_sample_indices = np.arange(len(rho_true))

print(f"总样本点数: {len(rho_true)}, 总物质数: {len(unique_materials)}")

if len(unique_materials) < n_outer_folds:
    raise ValueError(
        f"物质数 {len(unique_materials)} 小于 n_outer_folds={n_outer_folds}，无法做 5-fold。"
    )


# =========================================================
# 7. 5 折交叉验证（按物质）
# =========================================================
gkf = GroupKFold(n_splits=n_outer_folds)

metrics_direct = []
metrics_residual = []
metrics_baseline = []
metrics_residual_model = []

fold_test_prediction_dfs = []
fold_all_data_prediction_dfs = []
fold_all_data_count_records = []
fold_info_records = []

direct_feature_importance_records = []
residual_feature_importance_records = []
slope_param_records = []
slope_prediction_records = []

direct_feature_names = used_group_cols + [temp_col]
residual_feature_names = (
    used_group_cols
    + [temp_col, "delta_T", "anchor_T", "anchor_rho"]
)

for fold, (train_mat_idx, test_mat_idx) in enumerate(
    gkf.split(unique_materials, groups=unique_materials),
    start=1,
):
    print(f"\n========== Fold {fold}/{n_outer_folds} ==========")

    train_mats = unique_materials[train_mat_idx]
    test_mats = unique_materials[test_mat_idx]

    train_mask = np.isin(material_keys, train_mats)
    test_mask = np.isin(material_keys, test_mats)

    train_indices = np.where(train_mask)[0]
    test_indices = np.where(test_mask)[0]

    print("训练物质数:", len(train_mats))
    print("测试物质数:", len(test_mats))
    print("训练样本点数:", len(train_indices))
    print("测试样本点数:", len(test_indices))

    # =====================================================
    # 方法A：直接 GBDT
    # =====================================================
    X_train_A = build_direct_features(train_indices)
    y_train_A = rho_true[train_indices]

    valid_train_A = (
        np.isfinite(X_train_A).all(axis=1)
        & np.isfinite(y_train_A)
    )

    model_A = GradientBoostingRegressor(**gbdt_params_direct)
    model_A.fit(X_train_A[valid_train_A], y_train_A[valid_train_A])

    X_test_A = build_direct_features(test_indices)
    y_test = rho_true[test_indices]

    y_pred_A_test = np.full(len(test_indices), np.nan, dtype=float)
    valid_test_A = np.isfinite(X_test_A).all(axis=1)

    if valid_test_A.sum() > 0:
        y_pred_A_test[valid_test_A] = model_A.predict(X_test_A[valid_test_A])

    X_all_A = build_direct_features(all_sample_indices)
    y_pred_A_all = np.full(len(all_sample_indices), np.nan, dtype=float)
    valid_all_A = np.isfinite(X_all_A).all(axis=1)

    if valid_all_A.sum() > 0:
        y_pred_A_all[valid_all_A] = model_A.predict(X_all_A[valid_all_A])

    # =====================================================
    # 方法B：锚点基线 + 残差 GBDT
    # =====================================================
    result_test_B = train_and_predict_methodB(
        train_mats=train_mats,
        train_indices=train_indices,
        pred_indices=test_indices,
    )

    result_all_B = train_and_predict_methodB(
        train_mats=train_mats,
        train_indices=train_indices,
        pred_indices=all_sample_indices,
    )

    y_pred_B_test = result_test_B["final_pred"]
    baseline_B_test = result_test_B["baseline_pred"]
    residual_B_test = result_test_B["residual_pred"]
    slope_B_test = result_test_B["slope_pred"]

    y_pred_B_all = result_all_B["final_pred"]
    baseline_B_all = result_all_B["baseline_pred"]
    residual_B_all = result_all_B["residual_pred"]
    slope_B_all = result_all_B["slope_pred"]

    slope_model = result_test_B["slope_model"]
    res_model = result_test_B["res_model"]
    mat_slope_true = result_test_B["mat_slope_true"]
    train_slope_mats = result_test_B["train_slope_mats"]

    # =====================================================
    # 测试集评价
    # =====================================================
    met_A = evaluate_metrics(y_test, y_pred_A_test)
    met_B = evaluate_metrics(y_test, y_pred_B_test)
    met_baseline = evaluate_metrics(y_test, baseline_B_test)

    residual_target_test = y_test - baseline_B_test
    met_residual_model = evaluate_metrics(residual_target_test, residual_B_test)

    met_A["fold"] = fold
    met_B["fold"] = fold
    met_baseline["fold"] = fold
    met_residual_model["fold"] = fold

    metrics_direct.append(met_A)
    metrics_residual.append(met_B)
    metrics_baseline.append(met_baseline)
    metrics_residual_model.append(met_residual_model)

    print(f"\nFold {fold}:")
    print(
        "  Direct GBDT       - "
        f"R2={met_A['R2']:.4f}, "
        f"MSE={met_A['MSE']:.4f}, "
        f"RMSE={met_A['RMSE']:.4f}, "
        f"MAE={met_A['MAE']:.4f}, "
        f"ARD={met_A['ARD']:.2f}%"
    )
    print(
        "  Anchor+Residual   - "
        f"R2={met_B['R2']:.4f}, "
        f"MSE={met_B['MSE']:.4f}, "
        f"RMSE={met_B['RMSE']:.4f}, "
        f"MAE={met_B['MAE']:.4f}, "
        f"ARD={met_B['ARD']:.2f}%"
    )
    print(
        "  Baseline only     - "
        f"R2={met_baseline['R2']:.4f}, "
        f"MSE={met_baseline['MSE']:.4f}, "
        f"RMSE={met_baseline['RMSE']:.4f}, "
        f"MAE={met_baseline['MAE']:.4f}, "
        f"ARD={met_baseline['ARD']:.2f}%"
    )

    # =====================================================
    # 新增：每个 fold 模型预测完整数据集，并统计完整数据集三档偏差数量
    # =====================================================
    count_A_all = count_error_thresholds(rho_true, y_pred_A_all)
    count_B_all = count_error_thresholds(rho_true, y_pred_B_all)

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "Direct_GBDT",
        **count_A_all,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "Anchor_baseline_plus_Residual_GBDT",
        **count_B_all,
    })

    print("\nDirect GBDT fold model predicts ALL data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "Direct_GBDT",
        **count_A_all,
    }]).to_string(index=False))

    print("\nAnchor+Residual fold model predicts ALL data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "Anchor_baseline_plus_Residual_GBDT",
        **count_B_all,
    }]).to_string(index=False))

    # =====================================================
    # 保存测试集预测明细
    # =====================================================
    df_test_A = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="Direct_GBDT",
        sample_indices=test_indices,
        y_true=y_test,
        y_pred=y_pred_A_test,
    )

    df_test_B = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="Anchor_baseline_plus_Residual_GBDT",
        sample_indices=test_indices,
        y_true=y_test,
        y_pred=y_pred_B_test,
        baseline_pred=baseline_B_test,
        residual_pred=residual_B_test,
        slope_pred=slope_B_test,
    )

    fold_test_prediction_dfs.append(df_test_A)
    fold_test_prediction_dfs.append(df_test_B)

    # =====================================================
    # 保存完整数据集预测明细
    # =====================================================
    df_all_A = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="Direct_GBDT",
        sample_indices=all_sample_indices,
        y_true=rho_true,
        y_pred=y_pred_A_all,
    )

    df_all_B = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="Anchor_baseline_plus_Residual_GBDT",
        sample_indices=all_sample_indices,
        y_true=rho_true,
        y_pred=y_pred_B_all,
        baseline_pred=baseline_B_all,
        residual_pred=residual_B_all,
        slope_pred=slope_B_all,
    )

    fold_all_data_prediction_dfs.append(df_all_A)
    fold_all_data_prediction_dfs.append(df_all_B)

    # =====================================================
    # 保存 slope 真实值 / 预测值
    # =====================================================
    for mat, slope_true in mat_slope_true.items():
        slope_prediction_records.append({
            "fold": fold,
            material_key_col: mat,
            "dataset": "train",
            "slope_true_from_anchor": slope_true,
            "slope_pred_by_Ridge": slope_true,
            "slope_error": 0.0 if np.isfinite(slope_true) else np.nan,
            "note": "training-material true slope used as target",
        })

    # 记录所有物质的预测 slope
    unique_all_mats_this_fold = np.unique(material_keys[all_sample_indices])
    for mat in unique_all_mats_this_fold:
        idx_first = np.where(material_keys == mat)[0][0]
        slope_pred_mat = slope_B_all[np.where(material_keys[all_sample_indices] == mat)[0][0]]

        slope_true_mat = mat_slope_true.get(mat, np.nan)

        slope_prediction_records.append({
            "fold": fold,
            material_key_col: mat,
            "dataset": "all_data_prediction",
            "slope_true_from_anchor": slope_true_mat,
            "slope_pred_by_Ridge": slope_pred_mat,
            "slope_error": slope_pred_mat - slope_true_mat if np.isfinite(slope_true_mat) else np.nan,
            "note": "slope predicted by Ridge for all available materials",
        })

    # =====================================================
    # 保存特征重要性和参数
    # =====================================================
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

    if slope_model is not None and hasattr(slope_model, "coef_"):
        for fname, coef in zip(used_group_cols, slope_model.coef_):
            slope_param_records.append({
                "fold": fold,
                "feature": fname,
                "slope_model_coef": coef,
                "abs_slope_model_coef": abs(coef),
                "slope_model_intercept": slope_model.intercept_,
            })

    fold_info_records.append({
        "fold": fold,
        "n_train_materials": len(train_mats),
        "n_test_materials": len(test_mats),
        "n_train_points": len(train_indices),
        "n_test_points": len(test_indices),
        "n_all_points": len(all_sample_indices),
        "n_group_features": len(used_group_cols),
        "direct_n_features": len(direct_feature_names),
        "residual_n_features": len(residual_feature_names),
        "n_train_materials_used_for_slope": len(train_slope_mats),
        "slope_model_trained": slope_model is not None,
        "residual_model_trained": res_model is not None,
    })


# =========================================================
# 8. 汇总统计与配对 t 检验
# =========================================================
df_direct = pd.DataFrame(metrics_direct)
df_residual = pd.DataFrame(metrics_residual)
df_baseline = pd.DataFrame(metrics_baseline)
df_residual_model = pd.DataFrame(metrics_residual_model)

df_direct = df_direct[["fold"] + [c for c in df_direct.columns if c != "fold"]]
df_residual = df_residual[["fold"] + [c for c in df_residual.columns if c != "fold"]]
df_baseline = df_baseline[["fold"] + [c for c in df_baseline.columns if c != "fold"]]
df_residual_model = df_residual_model[["fold"] + [c for c in df_residual_model.columns if c != "fold"]]

summary_direct = summarize(df_direct, "Direct GBDT")
summary_residual = summarize(df_residual, "Anchor+Residual GBDT")
summary_baseline = summarize(df_baseline, "Baseline only")
summary_residual_model = summarize(df_residual_model, "Residual model")

summary_all = pd.concat(
    [
        summary_direct,
        summary_residual,
        summary_baseline,
        summary_residual_model,
    ],
    ignore_index=True,
)

print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
print(summary_all.to_string(index=False))


# =========================================================
# 9. 配对 t 检验
# =========================================================
t_test_results = []

for metric in ["R2", "MSE", "RMSE", "MAE", "ARD"]:
    vals_d = df_direct[metric].values.astype(float)
    vals_r = df_residual[metric].values.astype(float)

    valid = np.isfinite(vals_d) & np.isfinite(vals_r)

    vals_d = vals_d[valid]
    vals_r = vals_r[valid]

    if len(vals_d) > 1:
        t_stat, p_val = ttest_rel(vals_d, vals_r)

        if metric == "R2":
            better = "residual" if np.mean(vals_r) > np.mean(vals_d) else "direct"
        else:
            better = "residual" if np.mean(vals_r) < np.mean(vals_d) else "direct"

        sig = p_val < 0.05

        t_test_results.append({
            "Metric": metric,
            "Mean_direct": f"{np.mean(vals_d):.4f}",
            "Mean_residual": f"{np.mean(vals_r):.4f}",
            "p-value": f"{p_val:.4e}",
            "Significant(p<0.05)": sig,
            "Better model": better,
            "n_valid_fold_pairs": len(vals_d),
        })
    else:
        t_test_results.append({
            "Metric": metric,
            "Mean_direct": np.nan,
            "Mean_residual": np.nan,
            "p-value": np.nan,
            "Significant(p<0.05)": False,
            "Better model": "N/A",
            "n_valid_fold_pairs": len(vals_d),
        })

df_ttest = pd.DataFrame(t_test_results)

print("\n========== Paired t-test ==========")
print(df_ttest.to_string(index=False))


# =========================================================
# 10. 完整数据集预测偏差数量统计汇总
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
        "n_all_data_points": len(rho_true),
    })

df_final_average_summary = pd.DataFrame(final_average_records)

print("\n========== Fold all-data count summary ==========")
print(df_fold_all_data_count_summary.to_string(index=False))

print("\n========== Final average all-data count summary ==========")
print(df_final_average_summary.to_string(index=False))


# =========================================================
# 11. 整理输出表
# =========================================================
df_fold_test_predictions = pd.concat(fold_test_prediction_dfs, ignore_index=True)
df_fold_all_data_predictions = pd.concat(fold_all_data_prediction_dfs, ignore_index=True)

df_fold_info = pd.DataFrame(fold_info_records)
df_direct_feature_importance = pd.DataFrame(direct_feature_importance_records)
df_residual_feature_importance = pd.DataFrame(residual_feature_importance_records)
df_slope_params = pd.DataFrame(slope_param_records)
df_slope_predictions = pd.DataFrame(slope_prediction_records)

df_used_groups = pd.DataFrame({
    "used_group": used_group_cols,
    "occurrence_all_materials": (df_groups_numeric[used_group_cols] != 0).sum(axis=0).values,
    "total_count_all": df_groups_numeric[used_group_cols].sum(axis=0).values,
})

df_removed_zero_groups = pd.DataFrame({
    "removed_zero_group": removed_zero_group_cols,
})

df_run_info = pd.DataFrame([
    {"param": "input_file", "value": str(input_file)},
    {"param": "data_sheet", "value": data_sheet},
    {"param": "groups_sheet", "value": groups_sheet},
    {"param": "anchor_sheet", "value": anchor_sheet},
    {"param": "density_col", "value": density_col},
    {"param": "temp_col", "value": temp_col},
    {"param": "anchor_temp_col", "value": anchor_temp_col},
    {"param": "anchor_density_col", "value": anchor_density_col},
    {"param": "n_outer_folds", "value": n_outer_folds},
    {"param": "random_state", "value": random_state},
    {"param": "direct_GBDT_params", "value": str(gbdt_params_direct)},
    {"param": "residual_GBDT_params", "value": str(residual_gbdt_params)},
    {"param": "use_ridge_for_slope", "value": use_ridge_for_slope},
    {"param": "slope_ridge_alpha", "value": slope_ridge_alpha},
    {"param": "n_group_features", "value": len(used_group_cols)},
    {"param": "n_all_data_points", "value": len(rho_true)},
    {"param": "n_materials", "value": len(unique_materials)},
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
        "内容": f"液体密度 rho，目标列 {density_col}",
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
        "内容": f"{n_outer_folds}-fold GroupKFold，按 material_key 物质划分",
    },
    {
        "项目": "方法1",
        "内容": "Direct_GBDT：GradientBoostingRegressor 直接预测 rho",
    },
    {
        "项目": "方法1输入特征",
        "内容": f"[Nk, T]，有效基团数 {len(used_group_cols)}，总维度 {len(used_group_cols) + 1}",
    },
    {
        "项目": "方法1模型参数",
        "内容": str(gbdt_params_direct),
    },
    {
        "项目": "方法2",
        "内容": "Anchor_baseline_plus_Residual_GBDT：锚点线性基线 + GBDT 残差修正",
    },
    {
        "项目": "方法2最终公式",
        "内容": "rho_pred = baseline_rho + residual_pred",
    },
    {
        "项目": "slope 构造",
        "内容": "训练集每个物质基于 anchor 点计算真实 slope = sum(dx*dy)/sum(dx^2)，再用 Ridge(Nk) 预测测试/全数据物质 slope",
    },
    {
        "项目": "slope 子模型",
        "内容": f"Ridge(alpha={slope_ridge_alpha}, fit_intercept=True)",
    },
    {
        "项目": "slope 子模型输入特征",
        "内容": f"Nk，有效基团数 {len(used_group_cols)}",
    },
    {
        "项目": "baseline 构造",
        "内容": "baseline_rho = anchor_rho + slope_pred * (T - anchor_T)",
    },
    {
        "项目": "residual 构造",
        "内容": "residual_y = rho_true - baseline_rho；residual_pred = GBDT([Nk, T, delta_T, anchor_T, anchor_rho])",
    },
    {
        "项目": "residual 模型参数",
        "内容": str(residual_gbdt_params),
    },
    {
        "项目": "最终模型",
        "内容": "方法1为直接 GBDT；方法2为 anchor baseline + residual GBDT",
    },
    {
        "项目": "偏差数量统计口径",
        "内容": "每个 fold 训练出的最终模型预测完整数据集，统计 rho 相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 取平均",
    },
])


# =========================================================
# 12. 保存结果到 Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    # 原有核心输出
    df_direct.to_excel(writer, sheet_name="Fold_Metrics_Direct", index=False)
    df_residual.to_excel(writer, sheet_name="Fold_Metrics_Residual", index=False)
    summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
    df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)

    # baseline / residual 额外评价
    df_baseline.to_excel(writer, sheet_name="Baseline_Metrics_Test", index=False)
    df_residual_model.to_excel(writer, sheet_name="Residual_Model_Metrics", index=False)

    # 新增预测明细与全数据统计
    df_fold_test_predictions.to_excel(writer, sheet_name="fold_test_predictions", index=False)
    df_fold_all_data_predictions.to_excel(writer, sheet_name="fold_all_data_predictions", index=False)
    df_fold_all_data_count_summary.to_excel(writer, sheet_name="fold_all_data_count_summary", index=False)
    df_final_average_summary.to_excel(writer, sheet_name="final_average_summary", index=False)

    # slope / 参数 / 特征重要性
    df_slope_predictions.to_excel(writer, sheet_name="slope_info", index=False)
    df_slope_params.to_excel(writer, sheet_name="slope_model_params", index=False)
    df_direct_feature_importance.to_excel(writer, sheet_name="direct_feature_importance", index=False)
    df_residual_feature_importance.to_excel(writer, sheet_name="residual_feature_importance", index=False)

    # 运行信息
    df_fold_info.to_excel(writer, sheet_name="Fold_Info", index=False)
    df_used_groups.to_excel(writer, sheet_name="Used_Groups", index=False)
    df_removed_zero_groups.to_excel(writer, sheet_name="Removed_Zero_Groups", index=False)
    df_run_info.to_excel(writer, sheet_name="Run_Info", index=False)
    df_model_structure.to_excel(writer, sheet_name="model_structure", index=False)

    format_excel(writer)

print(f"\n结果已保存至: {output_file}")


# =========================================================
# 13. 最终方便复制输出
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


direct_1, direct_5, direct_10 = get_final_counts("Direct_GBDT")
residual_1, residual_5, residual_10 = get_final_counts("Anchor_baseline_plus_Residual_GBDT")

print("\n方法1 全数据预测偏差 1%，5%，10%分别为：")
print(direct_1)
print(direct_5)
print(direct_10)

print("\n方法2 全数据预测偏差 1%，5%，10%分别为：")
print(residual_1)
print(residual_5)
print(residual_10)


# =========================================================
# 14. 代码结构打印
# =========================================================
print("\n========== 当前代码结构简要汇总 ==========")
print(f"预测对象：液体密度 rho / {density_col}")
print(f"数据文件：{input_file}")
print(f"sheet 名称：{data_sheet}, {groups_sheet}, {anchor_sheet}")
print(f"交叉验证：{n_outer_folds}-fold GroupKFold，按 material_key 物质划分")
print("方法1：Direct_GBDT，GradientBoostingRegressor，输入 [Nk, T]")
print("方法2：Anchor_baseline_plus_Residual_GBDT，锚点线性基线 + GBDT 残差修正")
print("slope 构造：训练物质基于 anchor 点计算真实 slope，再用 Ridge(Nk) 预测测试/全数据物质 slope")
print(f"slope 子模型：Ridge(alpha={slope_ridge_alpha}, fit_intercept=True)")
print("baseline 构造：baseline_rho = anchor_rho + slope_pred * (T - anchor_T)")
print("residual 构造：residual_y = rho_true - baseline_rho")
print(f"residual 模型：GradientBoostingRegressor，参数：{residual_gbdt_params}")
print(f"方法1模型参数：{gbdt_params_direct}")
print("方法1最终输入：[Nk, T]")
print("方法2最终输入：baseline 使用 slope_pred*(T-anchor_T)，residual 使用 [Nk, T, delta_T, anchor_T, anchor_rho]")
print("偏差统计口径：每个 fold 模型预测完整数据集，统计 rho 相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 取平均")