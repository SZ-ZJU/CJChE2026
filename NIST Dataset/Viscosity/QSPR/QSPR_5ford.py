# import pandas as pd
# import numpy as np
# from pathlib import Path
#
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.model_selection import KFold
# from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
# from scipy.stats import ttest_rel
#
# pd.set_option("display.float_format", "{:.10f}".format)
# np.set_printoptions(suppress=True, precision=10)
#
# # =========================================================
# # 0. 全局设置
# # =========================================================
# descriptor_file = Path("selected_descriptors_with_viscosity_mean_target.xlsx")
# descriptor_sheet = "Selected_Features_Target"
# selected_feature_sheet = "Selected_Features"
#
# data_file = Path("dataset_viscosity_selected_by_two_k_with_lnVisc_invT_interpolation_8points.xlsx")
# data_sheet = "Data_selected"
#
# slope_file = Path("HistGB_submodels_predict_ref_lnVisc_Tb_and_slope.xls")   # 如果实际是 .xlsx 会自动适配
# slope_sheet_candidates = ["slope", "Slope", "Predicted_Slope"]
# slope_col_candidates = ["slope_pred_lnVisc_over_invT"]
#
# output_file = Path("RF_viscosity_5fold_CV_comparison.xlsx")
#
# material_key_col = "material_key"
# temp_col = "T_K"
#
# # 目标列候选（优先 lnViscosity）
# target_candidates = [
#     "lnViscosity", "lnViscosity_Pa_s", "ln_viscosity", "ln_viscosity_Pa_s",
#     "ln(Viscosity)", "ln_mu", "lnmu", "property_value",
#     "Viscosity", "viscosity", "Viscosity_Pa_s", "viscosity_Pa_s"
# ]
#
# n_outer_folds = 5
# random_state = 42
#
# # Random Forest 参数（与原始代码一致）
# rf_params = {
#     "n_estimators": 500,
#     "max_depth": None,
#     "min_samples_split": 2,
#     "min_samples_leaf": 1,
#     "max_features": "sqrt",
#     "bootstrap": True,
#     "random_state": 42,
#     "n_jobs": -1
# }
#
# # =========================================================
# # 1. 辅助函数（与原始代码保持一致）
# # =========================================================
# def normalize_colname(name):
#     return str(name).lower().replace(" ", "").replace("_", "").replace("-", "").replace("(", "").replace(")", "").replace("/", "")
#
# def find_first_existing_col(df, candidates, required=True, col_type="列"):
#     norm_map = {normalize_colname(c): c for c in df.columns}
#     for c in candidates:
#         key = normalize_colname(c)
#         if key in norm_map:
#             return norm_map[key]
#     if required:
#         raise ValueError(f"没有找到 {col_type}。候选: {candidates}\n当前列: {list(df.columns)}")
#     return None
#
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
# def safe_exp(x):
#     x = np.asarray(x, dtype=float)
#     return np.exp(np.clip(x, -700, 700))
#
# def infer_target_is_log(target_col):
#     col_norm = normalize_colname(target_col)
#     if "ln" in col_norm or "log" in col_norm:
#         return True
#     if col_norm == "propertyvalue":
#         return True
#     return False
#
# def find_alignment_key(df_desc, df_data):
#     candidate_pairs = [
#         ("material_key", "material_key"),
#         ("original_material_index", "original_material_index"),
#         ("pubchem_cid", "pubchem_cid"),
#         ("CID", "pubchem_cid"),
#         ("inchikey", "inchikey"),
#         ("InChIKey", "InChIKey"),
#         ("cas", "cas"),
#         ("compound_name", "compound_name"),
#     ]
#     for dcol, dacol in candidate_pairs:
#         if dcol in df_desc.columns and dacol in df_data.columns:
#             return dcol, dacol
#     return None, None
#
# def find_slope_key(df_slope, data_key_col):
#     if data_key_col is not None and data_key_col in df_slope.columns:
#         return data_key_col
#     for col in ["material_key", "original_material_index", "pubchem_cid", "CID", "inchikey", "InChIKey", "cas", "compound_name"]:
#         if col in df_slope.columns:
#             return col
#     return None
#
# def choose_data_group_key(df_data):
#     for col in ["material_key", "original_material_index", "pubchem_cid", "CID", "inchikey", "InChIKey", "cas", "compound_name"]:
#         if col in df_data.columns:
#             return col
#     return None
#
# def read_slope_file(slope_path, sheet_candidates):
#     if not slope_path.exists():
#         alt = slope_path.with_suffix(".xlsx")
#         if alt.exists():
#             slope_path = alt
#         else:
#             raise FileNotFoundError(f"未找到 slope 文件: {slope_path}")
#     xls = pd.ExcelFile(slope_path)
#     sheet = None
#     for s in sheet_candidates:
#         if s in xls.sheet_names:
#             sheet = s
#             break
#     if sheet is None:
#         sheet = xls.sheet_names[0]
#     df = pd.read_excel(slope_path, sheet_name=sheet)
#     return df, slope_path, sheet
#
# def calc_metrics_group(y_true, y_pred, target_is_log):
#     """计算一个数据集（如测试集）的 ln 空间和粘度空间指标"""
#     mask = np.isfinite(y_true) & np.isfinite(y_pred)
#     y_true = y_true[mask]
#     y_pred = y_pred[mask]
#     if len(y_true) == 0:
#         return {k: np.nan for k in ["R2_ln","MSE_ln","RMSE_ln","MAE_ln","ARD_ln",
#                                     "R2_vis","MSE_vis","RMSE_vis","MAE_vis","ARD_vis",
#                                     "leq1%","leq5%","leq10%","max_rel%"]}
#     # ln 空间
#     r2_ln = r2_score(y_true, y_pred)
#     mse_ln = mean_squared_error(y_true, y_pred)
#     rmse_ln = np.sqrt(mse_ln)
#     mae_ln = mean_absolute_error(y_true, y_pred)
#     with np.errstate(divide='ignore', invalid='ignore'):
#         ard_ln = np.mean(np.abs((y_pred - y_true) / y_true)) * 100 if np.abs(y_true).mean() > 0 else np.nan
#
#     if target_is_log:
#         visc_true = safe_exp(y_true)
#         visc_pred = safe_exp(y_pred)
#     else:
#         visc_true = y_true
#         visc_pred = y_pred
#
#     r2_vis = r2_score(visc_true, visc_pred)
#     mse_vis = mean_squared_error(visc_true, visc_pred)
#     rmse_vis = np.sqrt(mse_vis)
#     mae_vis = mean_absolute_error(visc_true, visc_pred)
#     with np.errstate(divide='ignore', invalid='ignore'):
#         ard_vis = np.mean(np.abs((visc_pred - visc_true) / visc_true)) * 100 if np.abs(visc_true).mean() > 0 else np.nan
#
#     valid = np.abs(visc_true) > 1e-12
#     if valid.sum() > 0:
#         rel_err = np.abs((visc_pred[valid] - visc_true[valid]) / visc_true[valid]) * 100
#         le1 = np.mean(rel_err <= 1) * 100
#         le5 = np.mean(rel_err <= 5) * 100
#         le10 = np.mean(rel_err <= 10) * 100
#         max_rel = np.max(rel_err)
#     else:
#         le1 = le5 = le10 = max_rel = np.nan
#
#     return {
#         "R2_ln": r2_ln, "MSE_ln": mse_ln, "RMSE_ln": rmse_ln, "MAE_ln": mae_ln, "ARD_ln_percent": ard_ln,
#         "R2_vis": r2_vis, "MSE_vis": mse_vis, "RMSE_vis": rmse_vis, "MAE_vis": mae_vis, "ARD_vis_percent": ard_vis,
#         "leq1%": le1, "leq5%": le5, "leq10%": le10, "max_rel%": max_rel
#     }
#
# # =========================================================
# # 2. 读取数据
# # =========================================================
# df_desc = pd.read_excel(descriptor_file, sheet_name=descriptor_sheet)
# df_data = pd.read_excel(data_file, sheet_name=data_sheet)
# df_slope, slope_path_used, slope_sheet_used = read_slope_file(slope_file, slope_sheet_candidates)
#
# print("描述符表行数:", len(df_desc))
# print("原始数据行数:", len(df_data))
# print("Slope 表行数:", len(df_slope))
#
# # 确定物质 ID 列
# desc_key_col, data_key_col = find_alignment_key(df_desc, df_data)
# data_group_col = choose_data_group_key(df_data)
# slope_key_col = find_slope_key(df_slope, data_key_col)
#
# print("物质对齐方式:")
# print("  desc_key_col:", desc_key_col)
# print("  data_key_col:", data_key_col)
# print("  data_group_col:", data_group_col)
# print("  slope_key_col:", slope_key_col)
#
# # 读取描述符列表
# xls_desc = pd.ExcelFile(descriptor_file)
# if selected_feature_sheet in xls_desc.sheet_names:
#     df_selected = pd.read_excel(descriptor_file, sheet_name=selected_feature_sheet)
#     if "selected_feature" not in df_selected.columns:
#         raise ValueError(f"{selected_feature_sheet} 缺少 selected_feature 列")
#     feature_cols = df_selected["selected_feature"].dropna().astype(str).tolist()
# else:
#     meta = ["material_index","original_material_index","material_key","compound_name","cas","formula","SMILES","smiles","final_smiles","inchikey","InChIKey","pubchem_cid","CID","phase","boiling_T_K","critical_T_K","T_min","T_max","T_range","n_points","target_n_valid_points"]
#     feature_cols = [c for c in df_desc.columns if c not in meta]
#
# print("描述符数量:", len(feature_cols))
#
# # 数值化描述符，删除全零列
# df_features = df_desc[feature_cols].apply(pd.to_numeric, errors="coerce").fillna(df_desc[feature_cols].mean())
# df_features = df_features.dropna(axis=1, how="any")
# nonzero = df_features.abs().sum(axis=0) != 0
# used_feature_cols = df_features.columns[nonzero].tolist()
# print("有效描述符数量:", len(used_feature_cols))
#
# # 找到温度列和目标列
# temp_col_actual = find_first_existing_col(df_data, [temp_col, "T_K", "Temperature"], required=True, col_type="温度")
# target_col = find_first_existing_col(df_data, target_candidates, required=True, col_type="目标列")
# target_is_log = infer_target_is_log(target_col)
# print("温度列:", temp_col_actual)
# print("目标列:", target_col, "是否为 ln(viscosity):", target_is_log)
#
# # 数值化温度和粘度
# df_data[temp_col_actual] = pd.to_numeric(df_data[temp_col_actual], errors="coerce")
# df_data[target_col] = pd.to_numeric(df_data[target_col], errors="coerce")
#
# # 找到斜率列
# slope_col = find_first_existing_col(df_slope, slope_col_candidates, required=True, col_type="斜率")
# df_slope[slope_col] = pd.to_numeric(df_slope[slope_col], errors="coerce")
# print("斜率列:", slope_col)
#
# # 温度特征使用 1/T
# inv_temp_feature_name = f"inv_{temp_col_actual}"
#
# # =========================================================
# # 3. 合并数据，构造按物质展开的特征矩阵
# # =========================================================
# if desc_key_col is not None and data_key_col is not None:
#     # 使用公共ID
#     df_desc["_key"] = df_desc[desc_key_col].apply(clean_key_value)
#     df_data["_key"] = df_data[data_key_col].apply(clean_key_value)
#     df_desc = df_desc.dropna(subset=["_key"]).drop_duplicates("_key")
#     df_data = df_data.dropna(subset=["_key"])
#     desc_map = {row["_key"]: row[used_feature_cols].values for _, row in df_desc.iterrows()}
#     # 斜率映射
#     df_slope["_key"] = df_slope[slope_key_col].apply(clean_key_value)
#     df_slope = df_slope.dropna(subset=["_key"]).drop_duplicates("_key")
#     slope_map = df_slope.set_index("_key")[slope_col].to_dict()
#     # 找出所有共同物质
#     common_keys = set(desc_map.keys()) & set(df_data["_key"].unique()) & set(slope_map.keys())
#     valid_keys = [k for k in common_keys if np.isfinite(slope_map.get(k, np.nan))]
#     if not valid_keys:
#         raise ValueError("没有同时拥有描述符、数据点和有效斜率的物质")
#     # 构建特征
#     X_no_slope = []
#     X_with_slope = []
#     y = []
#     material_ids = []
#     for key in valid_keys:
#         desc = desc_map[key]
#         slope_val = slope_map[key]
#         sub = df_data[df_data["_key"] == key]
#         for _, row in sub.iterrows():
#             T = row[temp_col_actual]
#             yv = row[target_col]
#             if not (np.isfinite(T) and np.isfinite(yv) and abs(T) > 1e-12):
#                 continue
#             invT = 1.0 / T
#             X_no_slope.append(np.concatenate([desc, [invT]]))
#             X_with_slope.append(np.concatenate([desc, [invT, slope_val]]))
#             y.append(yv)
#             material_ids.append(key)
# else:
#     # 备用：按顺序对齐（假设描述符表行数与物质数一致）
#     if data_group_col is None:
#         raise ValueError("无法确定物质分组列")
#     df_data["_group"] = df_data[data_group_col].apply(clean_key_value)
#     groups = df_data["_group"].drop_duplicates().tolist()
#     if len(groups) != len(df_features):
#         raise ValueError("物质分组数量与描述符行数不一致")
#     df_slope["_key"] = df_slope[slope_key_col].apply(clean_key_value)
#     df_slope = df_slope.dropna(subset=["_key"]).drop_duplicates("_key")
#     slope_map = df_slope.set_index("_key")[slope_col].to_dict()
#     X_no_slope = []
#     X_with_slope = []
#     y = []
#     material_ids = []
#     for i, key in enumerate(groups):
#         if key not in slope_map or not np.isfinite(slope_map[key]):
#             continue
#         desc = df_features.iloc[i].values
#         slope_val = slope_map[key]
#         sub = df_data[df_data["_group"] == key]
#         for _, row in sub.iterrows():
#             T = row[temp_col_actual]
#             yv = row[target_col]
#             if not (np.isfinite(T) and np.isfinite(yv) and abs(T) > 1e-12):
#                 continue
#             invT = 1.0 / T
#             X_no_slope.append(np.concatenate([desc, [invT]]))
#             X_with_slope.append(np.concatenate([desc, [invT, slope_val]]))
#             y.append(yv)
#             material_ids.append(key)
#
# X_no_slope = np.array(X_no_slope, dtype=float)
# X_with_slope = np.array(X_with_slope, dtype=float)
# y = np.array(y, dtype=float)
# material_ids = np.array(material_ids, dtype=str)
#
# unique_materials = np.unique(material_ids)
# print(f"总样本数: {len(y)}, 有效物质数: {len(unique_materials)}")
#
# # =========================================================
# # 4. 5折交叉验证（按物质）
# # =========================================================
# kf = KFold(n_splits=n_outer_folds, shuffle=True, random_state=random_state)
# metrics_no_slope = []
# metrics_with_slope = []
#
# for fold, (train_idx, test_idx) in enumerate(kf.split(unique_materials)):
#     print(f"\n========== Fold {fold+1}/{n_outer_folds} ==========")
#     train_mats = unique_materials[train_idx]
#     test_mats = unique_materials[test_idx]
#
#     train_mask = np.isin(material_ids, train_mats)
#     test_mask = np.isin(material_ids, test_mats)
#
#     # ----- 模型A：无斜率 -----
#     X_train = X_no_slope[train_mask]
#     y_train = y[train_mask]
#     X_test = X_no_slope[test_mask]
#     y_test = y[test_mask]
#
#     # 清除无效样本
#     valid_train = np.isfinite(X_train).all(axis=1) & np.isfinite(y_train)
#     X_train = X_train[valid_train]
#     y_train = y_train[valid_train]
#     valid_test = np.isfinite(X_test).all(axis=1)
#     X_test = X_test[valid_test]
#     y_test = y_test[valid_test]
#
#     modelA = RandomForestRegressor(**rf_params)
#     modelA.fit(X_train, y_train)
#     y_predA = modelA.predict(X_test)
#
#     # ----- 模型B：有斜率 -----
#     X_trainB = X_with_slope[train_mask]
#     y_trainB = y[train_mask]
#     X_testB = X_with_slope[test_mask]
#     y_testB = y[test_mask]
#
#     valid_trainB = np.isfinite(X_trainB).all(axis=1) & np.isfinite(y_trainB)
#     X_trainB = X_trainB[valid_trainB]
#     y_trainB = y_trainB[valid_trainB]
#     valid_testB = np.isfinite(X_testB).all(axis=1)
#     X_testB = X_testB[valid_testB]
#     y_testB = y_testB[valid_testB]
#
#     modelB = RandomForestRegressor(**rf_params)
#     modelB.fit(X_trainB, y_trainB)
#     y_predB = modelB.predict(X_testB)
#
#     # 计算指标
#     m_A = calc_metrics_group(y_test, y_predA, target_is_log)
#     m_B = calc_metrics_group(y_testB, y_predB, target_is_log)
#     m_A["fold"] = fold+1
#     m_B["fold"] = fold+1
#     metrics_no_slope.append(m_A)
#     metrics_with_slope.append(m_B)
#
# # =========================================================
# # 5. 汇总统计（均值±标准差）
# # =========================================================
# df_A = pd.DataFrame(metrics_no_slope)
# df_B = pd.DataFrame(metrics_with_slope)
#
# metric_names = [c for c in df_A.columns if c != "fold"]
#
# def summarize(df, name):
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
# summary_A = summarize(df_A, "RF (desc+1/T)")
# summary_B = summarize(df_B, "RF (desc+1/T+slope)")
# summary_all = pd.concat([summary_A, summary_B], ignore_index=True)
#
# print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
# print(summary_all.to_string(index=False))
#
# # =========================================================
# # 6. 配对 t 检验
# # =========================================================
# t_test_results = []
# for metric in metric_names:
#     vals_A = df_A[metric].dropna().values
#     vals_B = df_B[metric].dropna().values
#     if len(vals_A) == len(vals_B) and len(vals_A) > 1:
#         t_stat, p_val = ttest_rel(vals_A, vals_B)
#         if metric.startswith("R2"):
#             better = "with_slope" if np.mean(vals_B) > np.mean(vals_A) else "no_slope"
#             sig = p_val < 0.05
#         else:
#             better = "with_slope" if np.mean(vals_B) < np.mean(vals_A) else "no_slope"
#             sig = p_val < 0.05
#         t_test_results.append({
#             "Metric": metric,
#             "Mean_no_slope": f"{np.mean(vals_A):.4f}",
#             "Mean_with_slope": f"{np.mean(vals_B):.4f}",
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
# # 7. 保存结果到 Excel
# # =========================================================
# with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
#     df_A.to_excel(writer, sheet_name="Fold_Metrics_No_Slope", index=False)
#     df_B.to_excel(writer, sheet_name="Fold_Metrics_With_Slope", index=False)
#     summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
#     df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)
#
#     pd.DataFrame([
#         {"param": "n_outer_folds", "value": n_outer_folds},
#         {"param": "random_state", "value": random_state},
#         {"param": "n_descriptor_features", "value": len(used_feature_cols)},
#         {"param": "total_samples", "value": len(y)},
#         {"param": "n_materials", "value": len(unique_materials)},
#         {"param": "target_is_log", "value": target_is_log},
#         {"param": "rf_params", "value": str(rf_params)},
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
# print(f"\n保存完成: {output_file}")



import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from scipy.stats import ttest_rel

import warnings
warnings.filterwarnings("ignore")

pd.set_option("display.float_format", "{:.10f}".format)
np.set_printoptions(suppress=True, precision=10)

# =========================================================
# 0. 全局设置
# =========================================================
descriptor_file = Path("selected_descriptors_with_viscosity_mean_target.xlsx")
descriptor_sheet = "Selected_Features_Target"
selected_feature_sheet = "Selected_Features"

data_file = Path("dataset_viscosity_selected_by_two_k_with_lnVisc_invT_interpolation_8points.xlsx")
data_sheet = "Data_selected"

slope_file = Path("HistGB_submodels_predict_ref_lnVisc_Tb_and_slope.xls")   # 如果实际是 .xlsx 会自动适配
slope_sheet_candidates = ["slope", "Slope", "Predicted_Slope"]
slope_col_candidates = ["slope_pred_lnVisc_over_invT"]

output_file = Path("RF_viscosity_5fold_CV_comparison.xlsx")

material_key_col = "material_key"
temp_col = "T_K"

# 目标列候选（优先 lnViscosity）
target_candidates = [
    "lnViscosity", "lnViscosity_Pa_s", "ln_viscosity", "ln_viscosity_Pa_s",
    "ln(Viscosity)", "ln_mu", "lnmu", "property_value",
    "Viscosity", "viscosity", "Viscosity_Pa_s", "viscosity_Pa_s"
]

n_outer_folds = 5
random_state = 42

# Random Forest 参数（与原始代码一致）
rf_params = {
    "n_estimators": 500,
    "max_depth": None,
    "min_samples_split": 2,
    "min_samples_leaf": 1,
    "max_features": "sqrt",
    "bootstrap": True,
    "random_state": 42,
    "n_jobs": -1
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
    )


def find_first_existing_col(df, candidates, required=True, col_type="列"):
    norm_map = {normalize_colname(c): c for c in df.columns}
    for c in candidates:
        key = normalize_colname(c)
        if key in norm_map:
            return norm_map[key]

    if required:
        raise ValueError(
            f"没有找到 {col_type}。候选: {candidates}\n当前列: {list(df.columns)}"
        )

    return None


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


def safe_exp(x):
    x = np.asarray(x, dtype=float)
    return np.exp(np.clip(x, -700, 700))


def safe_log(x):
    x = np.asarray(x, dtype=float)
    out = np.full_like(x, np.nan, dtype=float)
    valid = np.isfinite(x) & (x > 0)
    out[valid] = np.log(x[valid])
    return out


def infer_target_is_log(target_col):
    col_norm = normalize_colname(target_col)

    if "ln" in col_norm or "log" in col_norm:
        return True

    # 该类数据中 property_value 通常是 lnVisc
    if col_norm == "propertyvalue":
        return True

    return False


def find_alignment_key(df_desc, df_data):
    candidate_pairs = [
        ("material_key", "material_key"),
        ("original_material_index", "original_material_index"),
        ("pubchem_cid", "pubchem_cid"),
        ("CID", "pubchem_cid"),
        ("CID_int", "pubchem_cid"),
        ("sdf_pubchem_cid", "pubchem_cid"),
        ("inchikey", "inchikey"),
        ("InChIKey", "InChIKey"),
        ("cas", "cas"),
        ("compound_name", "compound_name"),
    ]

    for dcol, dacol in candidate_pairs:
        if dcol in df_desc.columns and dacol in df_data.columns:
            return dcol, dacol

    return None, None


def find_slope_key(df_slope, data_key_col):
    if data_key_col is not None and data_key_col in df_slope.columns:
        return data_key_col

    for col in [
        "material_key", "original_material_index", "pubchem_cid",
        "CID", "CID_int", "sdf_pubchem_cid",
        "inchikey", "InChIKey", "cas", "compound_name"
    ]:
        if col in df_slope.columns:
            return col

    return None


def choose_data_group_key(df_data):
    for col in [
        "material_key", "original_material_index", "pubchem_cid",
        "CID", "CID_int", "sdf_pubchem_cid",
        "inchikey", "InChIKey", "cas", "compound_name"
    ]:
        if col in df_data.columns:
            return col

    return None


def read_slope_file(slope_path, sheet_candidates):
    if not slope_path.exists():
        alt = slope_path.with_suffix(".xlsx")
        if alt.exists():
            slope_path = alt
        else:
            raise FileNotFoundError(f"未找到 slope 文件: {slope_path}")

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

    mask = (
        np.isfinite(y_true)
        & np.isfinite(y_pred)
        & (np.abs(y_true) > eps)
    )

    rel_err[mask] = np.abs((y_pred[mask] - y_true[mask]) / y_true[mask]) * 100.0

    return rel_err


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


def average_relative_deviation(y_true, y_pred):
    rel_err = safe_relative_error_percent(y_true, y_pred)

    if np.any(np.isfinite(rel_err)):
        return float(np.nanmean(rel_err))

    return np.nan


def calc_metrics_group(y_true, y_pred, target_is_log):
    """
    计算测试集指标：
    - 如果 target_is_log=True，y_true/y_pred 视为 lnη，同时计算 η=exp(lnη) 空间指标；
    - 如果 target_is_log=False，y_true/y_pred 视为 η，同时计算 lnη 空间指标。
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = np.isfinite(y_true) & np.isfinite(y_pred)

    y_true = y_true[mask]
    y_pred = y_pred[mask]

    if len(y_true) == 0:
        return {
            "n_points": 0,

            "R2_ln": np.nan,
            "MSE_ln": np.nan,
            "RMSE_ln": np.nan,
            "MAE_ln": np.nan,
            "ARD_ln_percent": np.nan,

            "R2_vis": np.nan,
            "MSE_vis": np.nan,
            "RMSE_vis": np.nan,
            "MAE_vis": np.nan,
            "ARD_vis_percent": np.nan,

            "leq1%": np.nan,
            "leq5%": np.nan,
            "leq10%": np.nan,
            "max_rel%": np.nan,

            "visc_within_1pct_count": 0.0,
            "visc_within_5pct_count": 0.0,
            "visc_within_10pct_count": 0.0,
        }

    if target_is_log:
        ln_true = y_true
        ln_pred = y_pred
        visc_true = safe_exp(y_true)
        visc_pred = safe_exp(y_pred)
    else:
        visc_true = y_true
        visc_pred = y_pred
        ln_true = safe_log(y_true)
        ln_pred = safe_log(y_pred)

    # ln 空间
    ln_mask = np.isfinite(ln_true) & np.isfinite(ln_pred)

    if ln_mask.sum() > 1:
        r2_ln = r2_score(ln_true[ln_mask], ln_pred[ln_mask])
        mse_ln = mean_squared_error(ln_true[ln_mask], ln_pred[ln_mask])
        rmse_ln = np.sqrt(mse_ln)
        mae_ln = mean_absolute_error(ln_true[ln_mask], ln_pred[ln_mask])
        ard_ln = average_relative_deviation(ln_true[ln_mask], ln_pred[ln_mask])
    else:
        r2_ln = np.nan
        mse_ln = np.nan
        rmse_ln = np.nan
        mae_ln = np.nan
        ard_ln = np.nan

    # viscosity 空间
    vis_mask = np.isfinite(visc_true) & np.isfinite(visc_pred)

    if vis_mask.sum() > 1:
        r2_vis = r2_score(visc_true[vis_mask], visc_pred[vis_mask])
        mse_vis = mean_squared_error(visc_true[vis_mask], visc_pred[vis_mask])
        rmse_vis = np.sqrt(mse_vis)
        mae_vis = mean_absolute_error(visc_true[vis_mask], visc_pred[vis_mask])
        ard_vis = average_relative_deviation(visc_true[vis_mask], visc_pred[vis_mask])

        rel_err = safe_relative_error_percent(visc_true[vis_mask], visc_pred[vis_mask])

        if np.any(np.isfinite(rel_err)):
            le1 = np.nanmean(rel_err <= 1.0) * 100.0
            le5 = np.nanmean(rel_err <= 5.0) * 100.0
            le10 = np.nanmean(rel_err <= 10.0) * 100.0
            max_rel = np.nanmax(rel_err)

            c1 = float(np.nansum(rel_err <= 1.0))
            c5 = float(np.nansum(rel_err <= 5.0))
            c10 = float(np.nansum(rel_err <= 10.0))
        else:
            le1 = le5 = le10 = max_rel = np.nan
            c1 = c5 = c10 = 0.0
    else:
        r2_vis = np.nan
        mse_vis = np.nan
        rmse_vis = np.nan
        mae_vis = np.nan
        ard_vis = np.nan
        le1 = le5 = le10 = max_rel = np.nan
        c1 = c5 = c10 = 0.0

    return {
        "n_points": len(y_true),

        "R2_ln": r2_ln,
        "MSE_ln": mse_ln,
        "RMSE_ln": rmse_ln,
        "MAE_ln": mae_ln,
        "ARD_ln_percent": ard_ln,

        "R2_vis": r2_vis,
        "MSE_vis": mse_vis,
        "RMSE_vis": rmse_vis,
        "MAE_vis": mae_vis,
        "ARD_vis_percent": ard_vis,

        "leq1%": le1,
        "leq5%": le5,
        "leq10%": le10,
        "max_rel%": max_rel,

        "visc_within_1pct_count": c1,
        "visc_within_5pct_count": c5,
        "visc_within_10pct_count": c10,
    }


def make_prediction_df(fold, dataset_name, method, meta_df, y_true, y_pred, target_is_log):
    """
    保存测试集或完整数据集预测明细。
    """
    meta_df = meta_df.copy().reset_index(drop=True)

    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    if target_is_log:
        ln_true = y_true
        ln_pred = y_pred
        visc_true = safe_exp(y_true)
        visc_pred = safe_exp(y_pred)
    else:
        visc_true = y_true
        visc_pred = y_pred
        ln_true = safe_log(y_true)
        ln_pred = safe_log(y_pred)

    df_out = meta_df.copy()

    df_out.insert(0, "fold", fold)
    df_out.insert(1, "dataset", dataset_name)
    df_out.insert(2, "Method", method)

    df_out["target_true"] = y_true
    df_out["target_pred"] = y_pred

    df_out["lnVisc_true"] = ln_true
    df_out["lnVisc_pred"] = ln_pred
    df_out["lnVisc_error"] = ln_pred - ln_true
    df_out["lnVisc_absolute_error"] = np.abs(ln_pred - ln_true)
    df_out["lnVisc_relative_error_percent"] = safe_relative_error_percent(ln_true, ln_pred)

    df_out["visc_true"] = visc_true
    df_out["visc_pred"] = visc_pred
    df_out["visc_error"] = visc_pred - visc_true
    df_out["visc_absolute_error"] = np.abs(visc_pred - visc_true)
    df_out["visc_relative_error_percent"] = safe_relative_error_percent(visc_true, visc_pred)

    front_cols = [
        "fold", "dataset", "Method",
        "_key", material_key_col,
        temp_col_actual, "InvT",
        target_col, slope_col,
        "target_true", "target_pred",
        "lnVisc_true", "lnVisc_pred", "lnVisc_error",
        "lnVisc_absolute_error", "lnVisc_relative_error_percent",
        "visc_true", "visc_pred", "visc_error",
        "visc_absolute_error", "visc_relative_error_percent",
    ]

    front_cols = [c for c in front_cols if c in df_out.columns]
    other_cols = [c for c in df_out.columns if c not in front_cols]

    return df_out[front_cols + other_cols]


def summarize(df, name):
    rows = []

    metric_names = [c for c in df.columns if c != "fold"]

    for metric in metric_names:
        vals = pd.to_numeric(df[metric], errors="coerce").dropna().values

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
df_desc = pd.read_excel(descriptor_file, sheet_name=descriptor_sheet)
df_data = pd.read_excel(data_file, sheet_name=data_sheet)
df_slope, slope_path_used, slope_sheet_used = read_slope_file(slope_file, slope_sheet_candidates)

print("描述符表行数:", len(df_desc))
print("原始数据行数:", len(df_data))
print("Slope 表行数:", len(df_slope))
print("Slope 文件:", slope_path_used)
print("Slope sheet:", slope_sheet_used)

# 确定物质 ID 列
desc_key_col, data_key_col = find_alignment_key(df_desc, df_data)
data_group_col = choose_data_group_key(df_data)
slope_key_col = find_slope_key(df_slope, data_key_col)

print("物质对齐方式:")
print("  desc_key_col:", desc_key_col)
print("  data_key_col:", data_key_col)
print("  data_group_col:", data_group_col)
print("  slope_key_col:", slope_key_col)

if slope_key_col is None:
    raise ValueError("无法确定 slope 表中的物质 ID 列。")

# 读取描述符列表
xls_desc = pd.ExcelFile(descriptor_file)

if selected_feature_sheet in xls_desc.sheet_names:
    df_selected = pd.read_excel(descriptor_file, sheet_name=selected_feature_sheet)

    if "selected_feature" not in df_selected.columns:
        raise ValueError(f"{selected_feature_sheet} 缺少 selected_feature 列")

    feature_cols = df_selected["selected_feature"].dropna().astype(str).tolist()

else:
    meta = [
        "material_index", "original_material_index", "material_key",
        "compound_name", "cas", "formula", "SMILES", "smiles", "final_smiles",
        "inchikey", "InChIKey", "pubchem_cid", "CID", "phase",
        "boiling_T_K", "critical_T_K", "T_min", "T_max", "T_range",
        "n_points", "target_n_valid_points"
    ]

    feature_cols = [c for c in df_desc.columns if c not in meta]

missing_features = [c for c in feature_cols if c not in df_desc.columns]
if len(missing_features) > 0:
    raise ValueError(f"以下选中描述符不在描述符表中: {missing_features}")

print("描述符数量:", len(feature_cols))

# 数值化描述符，删除全零列
df_feature_raw = df_desc[feature_cols].copy()
df_features = df_feature_raw.apply(pd.to_numeric, errors="coerce")
df_features = df_features.replace([np.inf, -np.inf], np.nan)
df_features = df_features.fillna(df_features.mean())
df_features = df_features.dropna(axis=1, how="any")

nonzero = df_features.abs().sum(axis=0) != 0

used_feature_cols = df_features.columns[nonzero].tolist()
removed_zero_feature_cols = df_features.columns[~nonzero].tolist()

print("有效描述符数量:", len(used_feature_cols))
print("删除全零描述符数量:", len(removed_zero_feature_cols))

if len(used_feature_cols) == 0:
    raise ValueError("没有有效描述符可用于建模。")

# 找到温度列和目标列
temp_col_actual = find_first_existing_col(
    df_data,
    [temp_col, "T_K", "Temperature"],
    required=True,
    col_type="温度"
)

target_col = find_first_existing_col(
    df_data,
    target_candidates,
    required=True,
    col_type="目标列"
)

target_is_log = infer_target_is_log(target_col)

print("温度列:", temp_col_actual)
print("目标列:", target_col, "是否为 ln(viscosity):", target_is_log)

df_data[temp_col_actual] = pd.to_numeric(df_data[temp_col_actual], errors="coerce")
df_data[target_col] = pd.to_numeric(df_data[target_col], errors="coerce")

# 找到斜率列
slope_col = find_first_existing_col(
    df_slope,
    slope_col_candidates,
    required=True,
    col_type="斜率"
)

df_slope[slope_col] = pd.to_numeric(df_slope[slope_col], errors="coerce")
print("斜率列:", slope_col)

# 温度特征使用 1/T
inv_temp_feature_name = f"inv_{temp_col_actual}"


# =========================================================
# 3. 合并数据，构造按物质展开的特征矩阵
# =========================================================
X_no_slope = []
X_with_slope = []
y = []
material_ids = []
meta_rows = []

# ---------- 3.1 优先使用公共 ID ----------
if desc_key_col is not None and data_key_col is not None:
    df_desc_work = df_desc.copy()
    df_data_work = df_data.copy()
    df_slope_work = df_slope.copy()

    df_desc_work["_key"] = df_desc_work[desc_key_col].apply(clean_key_value)
    df_data_work["_key"] = df_data_work[data_key_col].apply(clean_key_value)
    df_slope_work["_key"] = df_slope_work[slope_key_col].apply(clean_key_value)

    df_desc_work = df_desc_work.dropna(subset=["_key"]).drop_duplicates("_key").copy()
    df_data_work = df_data_work.dropna(subset=["_key"]).copy()
    df_slope_work = df_slope_work.dropna(subset=["_key"]).drop_duplicates("_key").copy()

    # 同步有效描述符
    df_desc_work[used_feature_cols] = df_features.loc[
        df_desc_work.index,
        used_feature_cols
    ].values

    desc_map = {
        row["_key"]: row[used_feature_cols].values.astype(float)
        for _, row in df_desc_work.iterrows()
    }

    slope_map = df_slope_work.set_index("_key")[slope_col].to_dict()

    data_keys_in_order = df_data_work["_key"].drop_duplicates().tolist()

    valid_keys = [
        k for k in data_keys_in_order
        if k in desc_map
        and k in slope_map
        and np.isfinite(slope_map.get(k, np.nan))
    ]

    if len(valid_keys) == 0:
        raise ValueError("没有同时拥有描述符、数据点和有效斜率的物质")

    print("同时拥有描述符、数据点和有效 slope 的物质数:", len(valid_keys))

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
                and abs(T) > 1e-12
                and T > 0
            ):
                continue

            invT = 1.0 / T

            X_no_slope.append(np.concatenate([desc, [invT]]))
            X_with_slope.append(np.concatenate([desc, [invT, slope_val]]))
            y.append(yv)
            material_ids.append(key)

            meta = {
                "_key": key,
                material_key_col: key,
                temp_col_actual: T,
                "InvT": invT,
                target_col: yv,
                slope_col: slope_val,
            }

            for c in [
                "material_key", "original_material_index", "compound_name",
                "cas", "formula", "SMILES", "smiles", "final_smiles",
                "inchikey", "InChIKey", "pubchem_cid", "CID",
                "phase", "boiling_T_K", "critical_T_K",
                "T_min", "T_max", "T_range"
            ]:
                if c in row.index:
                    meta[c] = row[c]

            meta_rows.append(meta)

# ---------- 3.2 备用：按顺序对齐 ----------
else:
    if data_group_col is None:
        raise ValueError("无法确定物质分组列")

    df_data_work = df_data.copy()
    df_slope_work = df_slope.copy()

    df_data_work["_group"] = df_data_work[data_group_col].apply(clean_key_value)
    groups = df_data_work["_group"].drop_duplicates().tolist()

    if len(groups) != len(df_features):
        raise ValueError("物质分组数量与描述符行数不一致")

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
                and abs(T) > 1e-12
                and T > 0
            ):
                continue

            invT = 1.0 / T

            X_no_slope.append(np.concatenate([desc, [invT]]))
            X_with_slope.append(np.concatenate([desc, [invT, slope_val]]))
            y.append(yv)
            material_ids.append(key)

            meta = {
                "_key": key,
                material_key_col: key,
                temp_col_actual: T,
                "InvT": invT,
                target_col: yv,
                slope_col: slope_val,
            }

            for c in [
                "material_key", "original_material_index", "compound_name",
                "cas", "formula", "SMILES", "smiles", "final_smiles",
                "inchikey", "InChIKey", "pubchem_cid", "CID",
                "phase", "boiling_T_K", "critical_T_K",
                "T_min", "T_max", "T_range"
            ]:
                if c in row.index:
                    meta[c] = row[c]

            meta_rows.append(meta)

X_no_slope = np.array(X_no_slope, dtype=float)
X_with_slope = np.array(X_with_slope, dtype=float)
y = np.array(y, dtype=float)
material_ids = np.array(material_ids, dtype=str)

df_meta = pd.DataFrame(meta_rows)

unique_materials = np.unique(material_ids)
all_sample_indices = np.arange(len(y))

print(f"总样本数: {len(y)}, 有效物质数: {len(unique_materials)}")
print("无 slope 特征维度:", X_no_slope.shape[1])
print("有 slope 特征维度:", X_with_slope.shape[1])

if len(y) == 0:
    raise ValueError("没有有效样本点。")

if len(unique_materials) < n_outer_folds:
    raise ValueError(
        f"有效物质数 {len(unique_materials)} 小于 n_outer_folds={n_outer_folds}，无法做 5-fold。"
    )

# 完整数据集粘度真值
if target_is_log:
    visc_true_all = safe_exp(y)
else:
    visc_true_all = y


# =========================================================
# 4. 5折交叉验证（按物质）
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

feature_importance_no_records = []
feature_importance_with_records = []

feature_names_no = used_feature_cols + [inv_temp_feature_name]
feature_names_with = used_feature_cols + [inv_temp_feature_name, slope_col]

for fold, (train_idx, test_idx) in enumerate(kf.split(unique_materials), start=1):
    print(f"\n========== Fold {fold}/{n_outer_folds} ==========")

    train_mats = unique_materials[train_idx]
    test_mats = unique_materials[test_idx]

    train_mask = np.isin(material_ids, train_mats)
    test_mask = np.isin(material_ids, test_mats)

    print("训练物质数:", len(train_mats))
    print("测试物质数:", len(test_mats))
    print("训练样本数:", int(train_mask.sum()))
    print("测试样本数:", int(test_mask.sum()))

    # -----------------------------------------------------
    # 模型A：无斜率
    # -----------------------------------------------------
    X_train_A = X_no_slope[train_mask]
    y_train_A = y[train_mask]

    X_test_A = X_no_slope[test_mask]
    y_test_A = y[test_mask]

    valid_train_A = np.isfinite(X_train_A).all(axis=1) & np.isfinite(y_train_A)
    valid_test_A = np.isfinite(X_test_A).all(axis=1)

    X_train_A_valid = X_train_A[valid_train_A]
    y_train_A_valid = y_train_A[valid_train_A]

    X_test_A_valid = X_test_A[valid_test_A]
    y_test_A_valid = y_test_A[valid_test_A]

    modelA = RandomForestRegressor(**rf_params)
    modelA.fit(X_train_A_valid, y_train_A_valid)

    y_pred_A_test_valid = modelA.predict(X_test_A_valid)

    y_pred_A_test = np.full(len(y_test_A), np.nan, dtype=float)
    y_pred_A_test[valid_test_A] = y_pred_A_test_valid

    valid_all_A = np.isfinite(X_no_slope).all(axis=1)
    y_pred_A_all = np.full(len(y), np.nan, dtype=float)
    y_pred_A_all[valid_all_A] = modelA.predict(X_no_slope[valid_all_A])

    # -----------------------------------------------------
    # 模型B：有斜率
    # -----------------------------------------------------
    X_train_B = X_with_slope[train_mask]
    y_train_B = y[train_mask]

    X_test_B = X_with_slope[test_mask]
    y_test_B = y[test_mask]

    valid_train_B = np.isfinite(X_train_B).all(axis=1) & np.isfinite(y_train_B)
    valid_test_B = np.isfinite(X_test_B).all(axis=1)

    X_train_B_valid = X_train_B[valid_train_B]
    y_train_B_valid = y_train_B[valid_train_B]

    X_test_B_valid = X_test_B[valid_test_B]
    y_test_B_valid = y_test_B[valid_test_B]

    modelB = RandomForestRegressor(**rf_params)
    modelB.fit(X_train_B_valid, y_train_B_valid)

    y_pred_B_test_valid = modelB.predict(X_test_B_valid)

    y_pred_B_test = np.full(len(y_test_B), np.nan, dtype=float)
    y_pred_B_test[valid_test_B] = y_pred_B_test_valid

    valid_all_B = np.isfinite(X_with_slope).all(axis=1)
    y_pred_B_all = np.full(len(y), np.nan, dtype=float)
    y_pred_B_all[valid_all_B] = modelB.predict(X_with_slope[valid_all_B])

    # -----------------------------------------------------
    # 测试集指标
    # -----------------------------------------------------
    m_A = calc_metrics_group(y_test_A, y_pred_A_test, target_is_log)
    m_B = calc_metrics_group(y_test_B, y_pred_B_test, target_is_log)

    m_A["fold"] = fold
    m_B["fold"] = fold

    metrics_no_slope.append(m_A)
    metrics_with_slope.append(m_B)

    print(
        "  RF(desc+1/T)       - "
        f"R2_ln={m_A['R2_ln']:.4f}, "
        f"MSE_ln={m_A['MSE_ln']:.6f}, "
        f"RMSE_ln={m_A['RMSE_ln']:.6f}, "
        f"MAE_ln={m_A['MAE_ln']:.6f}, "
        f"ARD_vis={m_A['ARD_vis_percent']:.2f}%"
    )

    print(
        "  RF(desc+1/T+slope) - "
        f"R2_ln={m_B['R2_ln']:.4f}, "
        f"MSE_ln={m_B['MSE_ln']:.6f}, "
        f"RMSE_ln={m_B['RMSE_ln']:.6f}, "
        f"MAE_ln={m_B['MAE_ln']:.6f}, "
        f"ARD_vis={m_B['ARD_vis_percent']:.2f}%"
    )

    # -----------------------------------------------------
    # 新增：每个 fold 模型预测完整数据集，统计完整数据集三档偏差数量
    # 最终复制输出使用 viscosity 空间，同时保存 lnVisc 空间。
    # -----------------------------------------------------
    if target_is_log:
        visc_pred_A_all = safe_exp(y_pred_A_all)
        visc_pred_B_all = safe_exp(y_pred_B_all)

        ln_true_all = y
        ln_pred_A_all = y_pred_A_all
        ln_pred_B_all = y_pred_B_all
    else:
        visc_pred_A_all = y_pred_A_all
        visc_pred_B_all = y_pred_B_all

        ln_true_all = safe_log(y)
        ln_pred_A_all = safe_log(y_pred_A_all)
        ln_pred_B_all = safe_log(y_pred_B_all)

    count_A_all_visc = count_error_thresholds(visc_true_all, visc_pred_A_all)
    count_B_all_visc = count_error_thresholds(visc_true_all, visc_pred_B_all)

    count_A_all_ln = count_error_thresholds(ln_true_all, ln_pred_A_all)
    count_B_all_ln = count_error_thresholds(ln_true_all, ln_pred_B_all)

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "RF_desc_InvT",
        "count_space": "viscosity",
        **count_A_all_visc,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "RF_desc_InvT_slope",
        "count_space": "viscosity",
        **count_B_all_visc,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "RF_desc_InvT",
        "count_space": "lnVisc",
        **count_A_all_ln,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "RF_desc_InvT_slope",
        "count_space": "lnVisc",
        **count_B_all_ln,
    })

    print("\nRF(desc+1/T) fold model predicts ALL data count summary in viscosity space:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "RF_desc_InvT",
        "count_space": "viscosity",
        **count_A_all_visc,
    }]).to_string(index=False))

    print("\nRF(desc+1/T+slope) fold model predicts ALL data count summary in viscosity space:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "RF_desc_InvT_slope",
        "count_space": "viscosity",
        **count_B_all_visc,
    }]).to_string(index=False))

    # -----------------------------------------------------
    # 保存测试集预测明细
    # -----------------------------------------------------
    df_test_meta = df_meta.loc[test_mask].copy().reset_index(drop=True)
    df_all_meta = df_meta.copy().reset_index(drop=True)

    df_test_A = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="RF_desc_InvT",
        meta_df=df_test_meta,
        y_true=y_test_A,
        y_pred=y_pred_A_test,
        target_is_log=target_is_log,
    )

    df_test_B = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="RF_desc_InvT_slope",
        meta_df=df_test_meta,
        y_true=y_test_B,
        y_pred=y_pred_B_test,
        target_is_log=target_is_log,
    )

    fold_test_prediction_dfs.append(df_test_A)
    fold_test_prediction_dfs.append(df_test_B)

    # -----------------------------------------------------
    # 保存完整数据集预测明细
    # -----------------------------------------------------
    df_all_A = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="RF_desc_InvT",
        meta_df=df_all_meta,
        y_true=y,
        y_pred=y_pred_A_all,
        target_is_log=target_is_log,
    )

    df_all_B = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="RF_desc_InvT_slope",
        meta_df=df_all_meta,
        y_true=y,
        y_pred=y_pred_B_all,
        target_is_log=target_is_log,
    )

    fold_all_data_prediction_dfs.append(df_all_A)
    fold_all_data_prediction_dfs.append(df_all_B)

    # -----------------------------------------------------
    # 保存特征重要性
    # -----------------------------------------------------
    if hasattr(modelA, "feature_importances_"):
        for fname, imp in zip(feature_names_no, modelA.feature_importances_):
            feature_importance_no_records.append({
                "fold": fold,
                "feature": fname,
                "importance": imp,
            })

    if hasattr(modelB, "feature_importances_"):
        for fname, imp in zip(feature_names_with, modelB.feature_importances_):
            feature_importance_with_records.append({
                "fold": fold,
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
# 5. 汇总统计（均值±标准差）
# =========================================================
df_A = pd.DataFrame(metrics_no_slope)
df_B = pd.DataFrame(metrics_with_slope)

df_A = df_A[["fold"] + [c for c in df_A.columns if c != "fold"]]
df_B = df_B[["fold"] + [c for c in df_B.columns if c != "fold"]]

summary_A = summarize(df_A, "RF (desc+1/T)")
summary_B = summarize(df_B, "RF (desc+1/T+slope)")
summary_all = pd.concat([summary_A, summary_B], ignore_index=True)

print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
print(summary_all.to_string(index=False))


# =========================================================
# 6. 配对 t 检验
# =========================================================
metric_names = [c for c in df_A.columns if c != "fold"]

t_test_results = []

for metric in metric_names:
    vals_A = df_A[metric].values.astype(float)
    vals_B = df_B[metric].values.astype(float)

    valid = np.isfinite(vals_A) & np.isfinite(vals_B)

    vals_A_valid = vals_A[valid]
    vals_B_valid = vals_B[valid]

    if len(vals_A_valid) > 1:
        t_stat, p_val = ttest_rel(vals_A_valid, vals_B_valid)

        if metric.startswith("R2") or metric in ["leq1%", "leq5%", "leq10%"]:
            better = "with_slope" if np.mean(vals_B_valid) > np.mean(vals_A_valid) else "no_slope"
        else:
            better = "with_slope" if np.mean(vals_B_valid) < np.mean(vals_A_valid) else "no_slope"

        t_test_results.append({
            "Metric": metric,
            "Mean_no_slope": f"{np.mean(vals_A_valid):.4f}",
            "Mean_with_slope": f"{np.mean(vals_B_valid):.4f}",
            "p-value": f"{p_val:.4e}",
            "Significant(p<0.05)": p_val < 0.05,
            "Better model": better,
            "n_valid_fold_pairs": len(vals_A_valid),
        })

    else:
        t_test_results.append({
            "Metric": metric,
            "Mean_no_slope": np.nan,
            "Mean_with_slope": np.nan,
            "p-value": np.nan,
            "Significant(p<0.05)": False,
            "Better model": "N/A",
            "n_valid_fold_pairs": len(vals_A_valid),
        })

df_ttest = pd.DataFrame(t_test_results)

print("\n========== Paired t-test ==========")
print(df_ttest.to_string(index=False))


# =========================================================
# 7. 完整数据集偏差数量统计汇总
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
        "n_all_data_points": len(y),
    })

df_final_average_summary = pd.DataFrame(final_average_records)

print("\n========== Fold all-data count summary ==========")
print(df_fold_all_data_count_summary.to_string(index=False))

print("\n========== Final average all-data count summary ==========")
print(df_final_average_summary.to_string(index=False))


# =========================================================
# 8. 整理保存表
# =========================================================
df_fold_test_predictions = pd.concat(fold_test_prediction_dfs, ignore_index=True)
df_fold_all_data_predictions = pd.concat(fold_all_data_prediction_dfs, ignore_index=True)

df_fold_info = pd.DataFrame(fold_info_records)
df_feature_importance_no = pd.DataFrame(feature_importance_no_records)
df_feature_importance_with = pd.DataFrame(feature_importance_with_records)

df_used_features = pd.DataFrame({
    "used_descriptor_feature": used_feature_cols,
})

df_removed_zero_features = pd.DataFrame({
    "removed_zero_descriptor_feature": removed_zero_feature_cols,
})

df_slope_info = pd.DataFrame({
    "slope_file_used": [str(slope_path_used)],
    "slope_sheet_used": [slope_sheet_used],
    "slope_key_col": [slope_key_col],
    "slope_col": [slope_col],
})

df_run_info = pd.DataFrame([
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
    {"param": "target_is_log", "value": target_is_log},
    {"param": "slope_col", "value": slope_col},
    {"param": "n_outer_folds", "value": n_outer_folds},
    {"param": "random_state", "value": random_state},
    {"param": "rf_params", "value": str(rf_params)},
    {"param": "n_descriptor_features_original", "value": len(feature_cols)},
    {"param": "n_descriptor_features_used", "value": len(used_feature_cols)},
    {"param": "total_samples", "value": len(y)},
    {"param": "n_materials", "value": len(unique_materials)},
    {
        "param": "relative_error_definition",
        "value": "abs((y_pred - y_true) / y_true) * 100; abs(y_true)<=1e-12 -> NaN",
    },
    {
        "param": "final_count_space",
        "value": "viscosity space, eta=exp(lnVisc) if target is lnVisc",
    },
    {
        "param": "full_data_count_rule",
        "value": "Each fold model predicts the whole dataset; count viscosity-space rel_err <1%, <5%, <10%; then average counts over 5 folds.",
    },
])

df_model_structure = pd.DataFrame([
    {
        "项目": "预测对象",
        "内容": f"液体粘度；目标列 {target_col}；target_is_log={target_is_log}；最终偏差数量按 η=exp(lnη) 空间统计",
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
        "项目": "slope 列",
        "内容": slope_col,
    },
    {
        "项目": "交叉验证方式",
        "内容": f"{n_outer_folds}-fold KFold，按物质 ID 划分，shuffle=True，random_state={random_state}",
    },
    {
        "项目": "方法1",
        "内容": "RF_desc_InvT：RandomForestRegressor，输入 [descriptors, 1/T]",
    },
    {
        "项目": "方法2",
        "内容": "RF_desc_InvT_slope：RandomForestRegressor，输入 [descriptors, 1/T, slope_pred_lnVisc_over_invT]",
    },
    {
        "项目": "是否包含子模型",
        "内容": "当前代码不训练子模型；读取外部 HistGB 子模型预测得到的 slope",
    },
    {
        "项目": "子模型预测对象",
        "内容": "slope_pred_lnVisc_over_invT，用作方法2额外输入特征",
    },
    {
        "项目": "子模型类型",
        "内容": "外部文件名显示为 HistGB；本代码只读取预测结果，不在当前脚本内训练",
    },
    {
        "项目": "子模型参数",
        "内容": "当前代码无法从 slope 文件恢复；仅保存 slope 预测结果",
    },
    {
        "项目": "slope 构造",
        "内容": "直接读取 slope_pred_lnVisc_over_invT，作为方法2额外输入特征；不再乘以 1/T",
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
        "内容": f"[{len(used_feature_cols)} 个描述符, 1/T]，总维度 {len(used_feature_cols) + 1}",
    },
    {
        "项目": "方法2最终输入",
        "内容": f"[{len(used_feature_cols)} 个描述符, 1/T, slope]，总维度 {len(used_feature_cols) + 2}",
    },
    {
        "项目": "偏差数量统计口径",
        "内容": "每个 fold 模型预测完整数据集，在 η=exp(lnη) 空间统计相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 取平均",
    },
])


# =========================================================
# 9. 保存结果到 Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_A.to_excel(writer, sheet_name="Fold_Metrics_No_Slope", index=False)
    df_B.to_excel(writer, sheet_name="Fold_Metrics_With_Slope", index=False)
    summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
    df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)

    df_fold_test_predictions.to_excel(writer, sheet_name="fold_test_predictions", index=False)
    df_fold_all_data_predictions.to_excel(writer, sheet_name="fold_all_data_predictions", index=False)
    df_fold_all_data_count_summary.to_excel(writer, sheet_name="fold_all_data_count_summary", index=False)
    df_final_average_summary.to_excel(writer, sheet_name="final_average_summary", index=False)

    df_feature_importance_no.to_excel(writer, sheet_name="feature_importance_no", index=False)
    df_feature_importance_with.to_excel(writer, sheet_name="feature_importance_with", index=False)

    df_used_features.to_excel(writer, sheet_name="Used_Descriptor_Features", index=False)
    df_removed_zero_features.to_excel(writer, sheet_name="Removed_Zero_Descriptors", index=False)
    df_slope_info.to_excel(writer, sheet_name="slope_info", index=False)
    df_fold_info.to_excel(writer, sheet_name="Fold_Info", index=False)

    df_run_info.to_excel(writer, sheet_name="Run_Info", index=False)
    df_model_structure.to_excel(writer, sheet_name="model_structure", index=False)

    format_excel(writer)

print(f"\n保存完成: {output_file}")


# =========================================================
# 10. 最终方便复制输出
# =========================================================
def get_final_counts(method_name, count_space="viscosity"):
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


no_1, no_5, no_10 = get_final_counts("RF_desc_InvT", count_space="viscosity")
with_1, with_5, with_10 = get_final_counts("RF_desc_InvT_slope", count_space="viscosity")

print("\n方法1 全数据预测偏差 1%，5%，10%分别为：")
print(no_1)
print(no_5)
print(no_10)

print("\n方法2 全数据预测偏差 1%，5%，10%分别为：")
print(with_1)
print(with_5)
print(with_10)


# =========================================================
# 11. 代码结构打印
# =========================================================
print("\n========== 当前代码结构简要汇总 ==========")
print(f"预测对象：液体粘度；目标列 {target_col}；target_is_log={target_is_log}；最终偏差数量按 η=exp(lnη) 空间统计")
print(f"描述符文件：{descriptor_file}")
print(f"数据文件：{data_file}")
print(f"slope 文件：{slope_path_used}")
print(f"sheet 名称：{descriptor_sheet}, {data_sheet}, {slope_sheet_used}")
print(f"交叉验证：{n_outer_folds}-fold KFold，按物质 ID 划分")
print("方法1：RF_desc_InvT，RandomForestRegressor，输入 [descriptors, 1/T]")
print("方法2：RF_desc_InvT_slope，RandomForestRegressor，输入 [descriptors, 1/T, slope_pred_lnVisc_over_invT]")
print("子模型：当前代码不训练子模型，读取外部 HistGB 预测的 slope_pred_lnVisc_over_invT")
print(f"子模型预测列：{slope_col}")
print("子模型参数：当前代码无法从 slope 文件恢复，仅保存 slope 预测值")
print("slope 构造：直接读取 slope_pred_lnVisc_over_invT，作为方法2额外输入特征；没有乘以 1/T")
print("baseline 构造：无")
print("residual 模型：无")
print(f"最终模型：RandomForestRegressor，参数：{rf_params}")
print("方法1最终输入：[descriptors, 1/T]")
print("方法2最终输入：[descriptors, 1/T, slope_pred_lnVisc_over_invT]")
print("偏差统计口径：每个 fold 模型预测完整数据集，在 η=exp(lnη) 空间统计 <1%、<5%、<10% 点数，再对 5 个 fold 取平均")