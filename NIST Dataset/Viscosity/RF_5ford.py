# import pandas as pd
# import numpy as np
# from pathlib import Path
#
# from sklearn.ensemble import RandomForestRegressor
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
# # 0. 全局设置
# # =========================================================
# main_input_file = Path("dataset_viscosity_selected_by_two_k_with_lnVisc_invT_interpolation_8points.xlsx")
# slope_file = Path("HistGB_submodels_predict_ref_lnVisc_Tb_and_slope.xlsx")
# data_sheet = "Data_selected"
# groups_sheet = "Groups_selected"
# slope_sheet = "slope"
# slope_col = "slope_pred_lnVisc_over_invT"
#
# output_file = Path("RF_lnViscosity_5fold_CV_comparison.xlsx")
#
# material_key_col = "material_key"
# temp_col = "T_K"
#
# # 原始粘度列候选
# viscosity_col_candidates = [
#     "Viscosity_Pa_s", "viscosity_Pa_s", "Viscosity_Pa*s", "viscosity_Pa*s",
#     "Viscosity, Pa*s", "viscosity", "Viscosity", "eta_Pa_s", "eta",
#     "property_value", "value"
# ]
# lnvisc_col_candidates = [
#     "lnViscosity_Pa_s", "ln_viscosity_Pa_s", "lnViscosity", "ln_viscosity",
#     "ln_eta", "lnEta", "ln_property_value"
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
# # RF 参数（与原始代码一致）
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
# # =========================================================
# # 1. 工具函数（与原始代码一致）
# # =========================================================
# def is_valid_value(x):
#     if pd.isna(x): return False
#     s = str(x).strip()
#     if s == "" or s.lower() in ["nan","none","null","待定"]: return False
#     return True
#
# def build_material_key(row):
#     for col in ["material_key","inchikey","InChIKey","inchi_key","pubchem_inchikey","cas","compound_name","formula"]:
#         if col in row.index and is_valid_value(row[col]):
#             if col == "material_key":
#                 return str(row[col]).strip()
#             return f"{col}:{str(row[col]).strip()}"
#     return "unknown_material"
#
# def find_first_existing_col(df, candidates, col_type, required=True):
#     for col in candidates:
#         if col in df.columns:
#             return col
#     lower_map = {str(c).lower(): c for c in df.columns}
#     for col in candidates:
#         if str(col).lower() in lower_map:
#             return lower_map[str(col).lower()]
#     if required:
#         raise ValueError(f"没有找到 {col_type} 列。候选: {candidates}")
#     return None
#
# def safe_exp(x):
#     x = np.asarray(x, dtype=float)
#     return np.exp(np.clip(x, -700, 700))
#
# def average_relative_deviation(y_true, y_pred, eps=1e-12):
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#     mask = (np.isfinite(y_true) & np.isfinite(y_pred) & (np.abs(y_true) > eps))
#     if mask.sum() == 0:
#         return np.nan
#     return np.mean(np.abs((y_pred[mask] - y_true[mask]) / y_true[mask])) * 100.0
#
# def error_band_counts(y_true, y_pred, bands=(1,5,10)):
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#     mask = (np.isfinite(y_true) & np.isfinite(y_pred) & (np.abs(y_true) > 1e-12))
#     rel_err = np.full_like(y_true, np.nan)
#     if mask.sum() > 0:
#         rel_err[mask] = np.abs((y_pred[mask] - y_true[mask]) / y_true[mask]) * 100.0
#     out = {}
#     for b in bands:
#         out[f"within_{b}pct_count"] = int(np.nansum(rel_err <= b))
#         out[f"within_{b}pct_ratio"] = float(np.nanmean(rel_err <= b)) if len(rel_err)>0 else np.nan
#     return out
#
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
#         metadata_keywords = ["original_material_index","material_key","compound","name","cas","formula","smiles","inchi","inchikey","pubchem","phase","property","boiling","temperature","temp","t_k","pressure","lnp","lnviscosity","viscosity","density","k1","k2","interp","status","range","min","max"]
#         candidate_cols = []
#         for col in df_groups.columns:
#             if any(k in col.lower() for k in metadata_keywords):
#                 continue
#             if pd.to_numeric(df_groups[col], errors="coerce").notna().sum()>0:
#                 candidate_cols.append(col)
#         if len(candidate_cols) < n:
#             raise ValueError(f"自动识别基团仅 {len(candidate_cols)} 个，少于 {n}")
#         return candidate_cols[:n]
#
# def calc_metrics(y_true_ln, y_pred_ln):
#     """返回 ln 空间和还原后 P 空间的各项指标（单个数据集）"""
#     mask = np.isfinite(y_true_ln) & np.isfinite(y_pred_ln)
#     y_true_ln = y_true_ln[mask]
#     y_pred_ln = y_pred_ln[mask]
#     if len(y_true_ln) == 0:
#         return {k: np.nan for k in ["R2_ln","MSE_ln","RMSE_ln","MAE_ln","ARD_ln_percent",
#                                     "R2_visc","MSE_visc","RMSE_visc","MAE_visc","ARD_visc_percent",
#                                     "leq1%","leq5%","leq10%","max_rel%"]}
#     # ln 空间
#     r2_ln = r2_score(y_true_ln, y_pred_ln)
#     mse_ln = mean_squared_error(y_true_ln, y_pred_ln)
#     rmse_ln = np.sqrt(mse_ln)
#     mae_ln = mean_absolute_error(y_true_ln, y_pred_ln)
#     ard_ln = average_relative_deviation(y_true_ln, y_pred_ln)
#
#     # 还原到粘度
#     visc_true = safe_exp(y_true_ln)
#     visc_pred = safe_exp(y_pred_ln)
#     r2_visc = r2_score(visc_true, visc_pred)
#     mse_visc = mean_squared_error(visc_true, visc_pred)
#     rmse_visc = np.sqrt(mse_visc)
#     mae_visc = mean_absolute_error(visc_true, visc_pred)
#     ard_visc = average_relative_deviation(visc_true, visc_pred)
#
#     # 相对误差带
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
#         "R2_visc": r2_visc, "MSE_visc": mse_visc, "RMSE_visc": rmse_visc, "MAE_visc": mae_visc, "ARD_visc_percent": ard_visc,
#         "leq1%": le1, "leq5%": le5, "leq10%": le10, "max_rel%": max_rel
#     }
#
# # =========================================================
# # 2. 读取数据并准备
# # =========================================================
# # 读取主数据
# df_data = pd.read_excel(main_input_file, sheet_name=data_sheet)
# df_groups = pd.read_excel(main_input_file, sheet_name=groups_sheet)
# df_slope = pd.read_excel(slope_file, sheet_name=slope_sheet)
#
# print("Data_selected 行数:", len(df_data))
# print("Groups_selected 物质数:", len(df_groups))
# print("Slope 表行数:", len(df_slope))
#
# # 准备 material_key
# for df in [df_data, df_groups, df_slope]:
#     if material_key_col not in df.columns:
#         df[material_key_col] = df.apply(build_material_key, axis=1)
#     df[material_key_col] = df[material_key_col].astype(str).str.strip()
#
# # 找到或生成 ln(viscosity) 目标列
# viscosity_col = find_first_existing_col(df_data, viscosity_col_candidates, "原始粘度", required=True)
# lnvisc_col = find_first_existing_col(df_data, lnvisc_col_candidates, "ln(viscosity)", required=False)
# if lnvisc_col is None:
#     lnvisc_col = "lnViscosity_Pa_s"
#     df_data[lnvisc_col] = np.where(df_data[viscosity_col] > 0, np.log(df_data[viscosity_col]), np.nan)
#     print("已自动生成 ln(viscosity) 列:", lnvisc_col)
# else:
#     df_data[lnvisc_col] = pd.to_numeric(df_data[lnvisc_col], errors="coerce")
# print("使用温度列:", temp_col)
# print("使用原始粘度列:", viscosity_col)
# print("ln(viscosity) 目标列:", lnvisc_col)
#
# # 处理基团列
# group_cols_220 = identify_group_columns(df_groups, n_group_features_to_use)
# for col in group_cols_220:
#     df_groups[col] = pd.to_numeric(df_groups[col], errors="coerce").fillna(0.0)
# nonzero_group_cols = [col for col in group_cols_220 if not np.isclose(df_groups[col].abs().sum(), 0.0)]
# print("有效基团数量:", len(nonzero_group_cols))
#
# # 处理斜率列
# if slope_col not in df_slope.columns:
#     raise ValueError(f"斜率表中没有列 {slope_col}")
# df_slope[slope_col] = pd.to_numeric(df_slope[slope_col], errors="coerce")
# slope_df = df_slope[[material_key_col, slope_col]].drop_duplicates(subset=[material_key_col])
# slope_df[slope_col] = slope_df[slope_col].values  # 确保数值
#
# # 合并数据
# df_model = df_data.merge(df_groups[[material_key_col] + nonzero_group_cols], on=material_key_col, how="inner")
# df_model = df_model.merge(slope_df, on=material_key_col, how="inner")
# df_model[temp_col] = pd.to_numeric(df_model[temp_col], errors="coerce")
# df_model[lnvisc_col] = pd.to_numeric(df_model[lnvisc_col], errors="coerce")
# df_model[slope_col] = pd.to_numeric(df_model[slope_col], errors="coerce")
# df_model = df_model[(df_model[temp_col] > 0) & (df_model[viscosity_col] > 0) &
#                     np.isfinite(df_model[temp_col]) & np.isfinite(df_model[lnvisc_col]) &
#                     np.isfinite(df_model[slope_col])]
# df_model["InvT"] = 1.0 / df_model[temp_col]
#
# # 最终过滤缺失值
# feature_cols_no_slope = nonzero_group_cols + ["InvT"]
# feature_cols_with_slope = nonzero_group_cols + ["InvT", slope_col]
# df_model_clean = df_model.dropna(subset=feature_cols_with_slope + [lnvisc_col]).copy()
# print("最终建模样本点数:", len(df_model_clean))
# print("最终物质数:", df_model_clean[material_key_col].nunique())
#
# # 获取物质列表
# unique_materials = df_model_clean[material_key_col].drop_duplicates().values
# material_keys = df_model_clean[material_key_col].values
#
# # 准备特征数组
# X_groups = df_model_clean[nonzero_group_cols].values.astype(float)
# InvT_all = df_model_clean["InvT"].values.astype(float)
# slope_all = df_model_clean[slope_col].values.astype(float)
# y_ln = df_model_clean[lnvisc_col].values.astype(float)
#
# # 特征构建函数
# def build_X_no_slope(mask):
#     return np.hstack([X_groups[mask], InvT_all[mask].reshape(-1,1)])
#
# def build_X_with_slope(mask):
#     return np.hstack([X_groups[mask], InvT_all[mask].reshape(-1,1), slope_all[mask].reshape(-1,1)])
#
# # =========================================================
# # 3. 5折交叉验证（按物质）
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
#     train_mask = np.isin(material_keys, train_mats)
#     test_mask = np.isin(material_keys, test_mats)
#
#     # 模型A：无斜率
#     X_train_A = build_X_no_slope(train_mask)
#     y_train = y_ln[train_mask]
#     valid_A = np.isfinite(X_train_A).all(axis=1) & np.isfinite(y_train)
#     X_train_A = X_train_A[valid_A]
#     y_train_A = y_train[valid_A]
#     model_A = RandomForestRegressor(**rf_params)
#     model_A.fit(X_train_A, y_train_A)
#
#     X_test_A = build_X_no_slope(test_mask)
#     y_test = y_ln[test_mask]
#     valid_test_A = np.isfinite(X_test_A).all(axis=1)
#     y_pred_A = np.full(len(y_test), np.nan)
#     y_pred_A[valid_test_A] = model_A.predict(X_test_A[valid_test_A])
#
#     # 模型B：有斜率
#     X_train_B = build_X_with_slope(train_mask)
#     valid_B = np.isfinite(X_train_B).all(axis=1) & np.isfinite(y_train)
#     X_train_B = X_train_B[valid_B]
#     y_train_B = y_train[valid_B]
#     model_B = RandomForestRegressor(**rf_params)
#     model_B.fit(X_train_B, y_train_B)
#
#     X_test_B = build_X_with_slope(test_mask)
#     valid_test_B = np.isfinite(X_test_B).all(axis=1)
#     y_pred_B = np.full(len(y_test), np.nan)
#     y_pred_B[valid_test_B] = model_B.predict(X_test_B[valid_test_B])
#
#     # 计算指标
#     m_A = calc_metrics(y_test, y_pred_A)
#     m_B = calc_metrics(y_test, y_pred_B)
#     m_A["fold"] = fold+1
#     m_B["fold"] = fold+1
#     metrics_no_slope.append(m_A)
#     metrics_with_slope.append(m_B)
#
# # =========================================================
# # 4. 汇总统计（均值±标准差）
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
# summary_A = summarize(df_A, "RF (groups+InvT)")
# summary_B = summarize(df_B, "RF (groups+InvT+slope)")
# summary_all = pd.concat([summary_A, summary_B], ignore_index=True)
#
# print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
# print(summary_all.to_string(index=False))
#
# # =========================================================
# # 5. 配对 t 检验
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
# # 6. 保存结果
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
#         {"param": "n_group_features", "value": len(nonzero_group_cols)},
#         {"param": "total_samples", "value": len(y_ln)},
#         {"param": "n_materials", "value": len(unique_materials)},
#         {"param": "RF_params", "value": str(rf_params)},
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
main_input_file = Path("dataset_viscosity_selected_by_two_k_with_lnVisc_invT_interpolation_8points.xlsx")
slope_file = Path("HistGB_submodels_predict_ref_lnVisc_Tb_and_slope.xlsx")

data_sheet = "Data_selected"
groups_sheet = "Groups_selected"
slope_sheet = "slope"
slope_col = "slope_pred_lnVisc_over_invT"

output_file = Path("RF_lnViscosity_5fold_CV_comparison.xlsx")

material_key_col = "material_key"
temp_col = "T_K"

viscosity_col_candidates = [
    "Viscosity_Pa_s", "viscosity_Pa_s", "Viscosity_Pa*s", "viscosity_Pa*s",
    "Viscosity, Pa*s", "viscosity", "Viscosity", "eta_Pa_s", "eta",
    "property_value", "value"
]

lnvisc_col_candidates = [
    "lnViscosity_Pa_s", "ln_viscosity_Pa_s", "lnViscosity", "ln_viscosity",
    "ln_eta", "lnEta", "ln_property_value"
]

n_group_features_to_use = 220
use_fixed_group_position = True
group_start_col_1based = 3
group_end_col_1based = 222

n_outer_folds = 5
random_state = 42

# RF 参数：保持原始代码设置
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
    for col in [
        "material_key", "inchikey", "InChIKey", "inchi_key",
        "pubchem_inchikey", "cas", "compound_name", "formula"
    ]:
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


def safe_exp(x):
    x = np.asarray(x, dtype=float)
    return np.exp(np.clip(x, -700, 700))


def safe_log(x):
    x = np.asarray(x, dtype=float)
    out = np.full_like(x, np.nan, dtype=float)
    valid = np.isfinite(x) & (x > 0)
    out[valid] = np.log(x[valid])
    return out


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


def average_relative_deviation(y_true, y_pred):
    rel_err = safe_relative_error_percent(y_true, y_pred)

    if np.any(np.isfinite(rel_err)):
        return float(np.nanmean(rel_err))

    return np.nan


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


def error_band_counts(y_true, y_pred, bands=(1, 5, 10), prefix=""):
    """
    保留原始误差区间比例逻辑，但改为同时输出 count 和 ratio。
    注意：这里为了与旧代码兼容，ratio 使用 <=。
    最终复制输出使用 count_error_thresholds 中的严格 <。
    """
    rel_err = safe_relative_error_percent(y_true, y_pred)

    out = {}
    n_valid = int(np.sum(np.isfinite(rel_err)))

    for b in bands:
        out[f"{prefix}within_{b}pct_count"] = float(np.nansum(rel_err <= b))
        out[f"{prefix}within_{b}pct_ratio"] = (
            float(np.nanmean(rel_err <= b))
            if len(rel_err) > 0
            else np.nan
        )

    out[f"{prefix}n_valid_relative_error"] = n_valid

    return out


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
        "lnp", "lnviscosity", "viscosity", "density", "k1", "k2",
        "interp", "status", "range", "min", "max"
    ]

    candidate_cols = []

    for col in df_groups.columns:
        if any(k in str(col).lower() for k in metadata_keywords):
            continue

        if pd.to_numeric(df_groups[col], errors="coerce").notna().sum() > 0:
            candidate_cols.append(col)

    if len(candidate_cols) < n:
        raise ValueError(f"自动识别基团仅 {len(candidate_cols)} 个，少于 {n}")

    return candidate_cols[:n]


def calc_metrics(y_true_ln, y_pred_ln):
    """
    返回 ln 空间和还原后粘度 eta 空间的各项指标。
    """
    y_true_ln = np.asarray(y_true_ln, dtype=float)
    y_pred_ln = np.asarray(y_pred_ln, dtype=float)

    mask = np.isfinite(y_true_ln) & np.isfinite(y_pred_ln)

    y_true_ln = y_true_ln[mask]
    y_pred_ln = y_pred_ln[mask]

    if len(y_true_ln) == 0:
        return {
            "n_points": 0,

            "R2_ln": np.nan,
            "MSE_ln": np.nan,
            "RMSE_ln": np.nan,
            "MAE_ln": np.nan,
            "ARD_ln_percent": np.nan,

            "R2_visc": np.nan,
            "MSE_visc": np.nan,
            "RMSE_visc": np.nan,
            "MAE_visc": np.nan,
            "ARD_visc_percent": np.nan,

            "leq1%": np.nan,
            "leq5%": np.nan,
            "leq10%": np.nan,
            "max_rel%": np.nan,

            "ln_within_1pct_count": 0.0,
            "ln_within_5pct_count": 0.0,
            "ln_within_10pct_count": 0.0,
            "visc_within_1pct_count": 0.0,
            "visc_within_5pct_count": 0.0,
            "visc_within_10pct_count": 0.0,
        }

    # ln 空间
    r2_ln = r2_score(y_true_ln, y_pred_ln) if len(y_true_ln) > 1 else np.nan
    mse_ln = mean_squared_error(y_true_ln, y_pred_ln)
    rmse_ln = np.sqrt(mse_ln)
    mae_ln = mean_absolute_error(y_true_ln, y_pred_ln)
    ard_ln = average_relative_deviation(y_true_ln, y_pred_ln)

    # 还原到粘度
    visc_true = safe_exp(y_true_ln)
    visc_pred = safe_exp(y_pred_ln)

    r2_visc = r2_score(visc_true, visc_pred) if len(visc_true) > 1 else np.nan
    mse_visc = mean_squared_error(visc_true, visc_pred)
    rmse_visc = np.sqrt(mse_visc)
    mae_visc = mean_absolute_error(visc_true, visc_pred)
    ard_visc = average_relative_deviation(visc_true, visc_pred)

    # 原始代码中的相对误差带：粘度空间 <= 阈值比例
    rel_err_visc = safe_relative_error_percent(visc_true, visc_pred)

    if np.any(np.isfinite(rel_err_visc)):
        le1 = np.nanmean(rel_err_visc <= 1.0) * 100.0
        le5 = np.nanmean(rel_err_visc <= 5.0) * 100.0
        le10 = np.nanmean(rel_err_visc <= 10.0) * 100.0
        max_rel = np.nanmax(rel_err_visc)
    else:
        le1 = le5 = le10 = max_rel = np.nan

    ln_counts = error_band_counts(y_true_ln, y_pred_ln, prefix="ln_")
    visc_counts = error_band_counts(visc_true, visc_pred, prefix="visc_")

    out = {
        "n_points": len(y_true_ln),

        "R2_ln": r2_ln,
        "MSE_ln": mse_ln,
        "RMSE_ln": rmse_ln,
        "MAE_ln": mae_ln,
        "ARD_ln_percent": ard_ln,

        "R2_visc": r2_visc,
        "MSE_visc": mse_visc,
        "RMSE_visc": rmse_visc,
        "MAE_visc": mae_visc,
        "ARD_visc_percent": ard_visc,

        "leq1%": le1,
        "leq5%": le5,
        "leq10%": le10,
        "max_rel%": max_rel,
    }

    out.update(ln_counts)
    out.update(visc_counts)

    return out


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


def make_prediction_df(fold, dataset_name, method, sub_df, y_true_ln, y_pred_ln):
    """
    保存测试集或完整数据集预测明细。
    """
    y_true_ln = np.asarray(y_true_ln, dtype=float)
    y_pred_ln = np.asarray(y_pred_ln, dtype=float)

    visc_true = safe_exp(y_true_ln)
    visc_pred = safe_exp(y_pred_ln)

    df_out = sub_df.copy().reset_index(drop=True)

    df_out.insert(0, "fold", fold)
    df_out.insert(1, "dataset", dataset_name)
    df_out.insert(2, "Method", method)

    df_out["lnVisc_true"] = y_true_ln
    df_out["lnVisc_pred"] = y_pred_ln
    df_out["lnVisc_error"] = y_pred_ln - y_true_ln
    df_out["lnVisc_absolute_error"] = np.abs(y_pred_ln - y_true_ln)
    df_out["lnVisc_relative_error_percent"] = safe_relative_error_percent(y_true_ln, y_pred_ln)

    df_out["visc_true"] = visc_true
    df_out["visc_pred"] = visc_pred
    df_out["visc_error"] = visc_pred - visc_true
    df_out["visc_absolute_error"] = np.abs(visc_pred - visc_true)
    df_out["visc_relative_error_percent"] = safe_relative_error_percent(visc_true, visc_pred)

    keep_front = [
        "fold",
        "dataset",
        "Method",
        material_key_col,
        temp_col,
        "InvT",
        lnvisc_col,
        viscosity_col,
        slope_col,
        "lnVisc_true",
        "lnVisc_pred",
        "lnVisc_error",
        "lnVisc_absolute_error",
        "lnVisc_relative_error_percent",
        "visc_true",
        "visc_pred",
        "visc_error",
        "visc_absolute_error",
        "visc_relative_error_percent",
    ]

    keep_front_existing = [c for c in keep_front if c in df_out.columns]
    other_cols = [c for c in df_out.columns if c not in keep_front_existing]

    df_out = df_out[keep_front_existing + other_cols]

    return df_out


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
# 2. 读取数据并准备
# =========================================================
if not main_input_file.exists():
    raise FileNotFoundError(f"没有找到主输入文件: {main_input_file}")

if not slope_file.exists():
    raise FileNotFoundError(f"没有找到 slope 文件: {slope_file}")

df_data = pd.read_excel(main_input_file, sheet_name=data_sheet)
df_groups = pd.read_excel(main_input_file, sheet_name=groups_sheet)
df_slope = pd.read_excel(slope_file, sheet_name=slope_sheet)

print("Data_selected 行数:", len(df_data))
print("Groups_selected 物质数:", len(df_groups))
print("Slope 表行数:", len(df_slope))

# 准备 material_key
for df in [df_data, df_groups, df_slope]:
    if material_key_col not in df.columns:
        df[material_key_col] = df.apply(build_material_key, axis=1)

    df[material_key_col] = df[material_key_col].astype(str).str.strip()

# 找到或生成 ln(viscosity) 目标列
viscosity_col = find_first_existing_col(
    df_data,
    viscosity_col_candidates,
    "原始粘度",
    required=True,
)

lnvisc_col = find_first_existing_col(
    df_data,
    lnvisc_col_candidates,
    "ln(viscosity)",
    required=False,
)

df_data[viscosity_col] = pd.to_numeric(df_data[viscosity_col], errors="coerce")

if lnvisc_col is None:
    lnvisc_col = "lnViscosity_Pa_s"
    df_data[lnvisc_col] = np.where(
        df_data[viscosity_col] > 0,
        np.log(df_data[viscosity_col]),
        np.nan,
    )
    print("已自动生成 ln(viscosity) 列:", lnvisc_col)
else:
    df_data[lnvisc_col] = pd.to_numeric(df_data[lnvisc_col], errors="coerce")

if temp_col not in df_data.columns:
    raise ValueError(f"Data_selected 中没有找到温度列: {temp_col}")

df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")

print("使用温度列:", temp_col)
print("使用原始粘度列:", viscosity_col)
print("ln(viscosity) 目标列:", lnvisc_col)

# 处理基团列
group_cols_220 = identify_group_columns(df_groups, n_group_features_to_use)

for col in group_cols_220:
    df_groups[col] = pd.to_numeric(df_groups[col], errors="coerce").fillna(0.0)

nonzero_group_cols = [
    col for col in group_cols_220
    if not np.isclose(df_groups[col].abs().sum(), 0.0)
]

removed_zero_group_cols = [
    col for col in group_cols_220
    if np.isclose(df_groups[col].abs().sum(), 0.0)
]

print("有效基团数量:", len(nonzero_group_cols))
print("删除全零基团数量:", len(removed_zero_group_cols))

# 处理斜率列
if slope_col not in df_slope.columns:
    raise ValueError(f"斜率表中没有列 {slope_col}")

df_slope[slope_col] = pd.to_numeric(df_slope[slope_col], errors="coerce")

slope_df = (
    df_slope[[material_key_col, slope_col]]
    .drop_duplicates(subset=[material_key_col])
    .copy()
)

# 合并数据
df_model = df_data.merge(
    df_groups[[material_key_col] + nonzero_group_cols],
    on=material_key_col,
    how="inner",
)

df_model = df_model.merge(
    slope_df,
    on=material_key_col,
    how="inner",
)

df_model[temp_col] = pd.to_numeric(df_model[temp_col], errors="coerce")
df_model[lnvisc_col] = pd.to_numeric(df_model[lnvisc_col], errors="coerce")
df_model[viscosity_col] = pd.to_numeric(df_model[viscosity_col], errors="coerce")
df_model[slope_col] = pd.to_numeric(df_model[slope_col], errors="coerce")

df_model = df_model[
    (df_model[temp_col] > 0)
    & (df_model[viscosity_col] > 0)
    & np.isfinite(df_model[temp_col])
    & np.isfinite(df_model[lnvisc_col])
    & np.isfinite(df_model[slope_col])
].copy()

df_model["InvT"] = 1.0 / df_model[temp_col]

feature_cols_no_slope = nonzero_group_cols + ["InvT"]
feature_cols_with_slope = nonzero_group_cols + ["InvT", slope_col]

df_model_clean = df_model.dropna(
    subset=feature_cols_with_slope + [lnvisc_col, viscosity_col]
).copy()

df_model_clean = df_model_clean.reset_index(drop=True)

print("最终建模样本点数:", len(df_model_clean))
print("最终物质数:", df_model_clean[material_key_col].nunique())

# 获取物质列表
unique_materials = df_model_clean[material_key_col].drop_duplicates().values
material_keys = df_model_clean[material_key_col].values.astype(str)

if len(unique_materials) < n_outer_folds:
    raise ValueError(
        f"有效物质数 {len(unique_materials)} 小于 n_outer_folds={n_outer_folds}，无法做 5-fold。"
    )

# 准备特征数组
X_groups = df_model_clean[nonzero_group_cols].values.astype(float)
InvT_all = df_model_clean["InvT"].values.astype(float)
slope_all = df_model_clean[slope_col].values.astype(float)
y_ln = df_model_clean[lnvisc_col].values.astype(float)
y_visc = safe_exp(y_ln)

all_sample_indices = np.arange(len(y_ln))


def build_X_no_slope(mask):
    return np.hstack([
        X_groups[mask],
        InvT_all[mask].reshape(-1, 1),
    ])


def build_X_with_slope(mask):
    return np.hstack([
        X_groups[mask],
        InvT_all[mask].reshape(-1, 1),
        slope_all[mask].reshape(-1, 1),
    ])


X_all_no_slope = build_X_no_slope(np.ones(len(y_ln), dtype=bool))
X_all_with_slope = build_X_with_slope(np.ones(len(y_ln), dtype=bool))


# =========================================================
# 3. 5折交叉验证（按物质）
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

feature_names_no = nonzero_group_cols + ["InvT"]
feature_names_with = nonzero_group_cols + ["InvT", slope_col]

for fold, (train_idx, test_idx) in enumerate(kf.split(unique_materials), start=1):
    print(f"\n========== Fold {fold}/{n_outer_folds} ==========")

    train_mats = unique_materials[train_idx]
    test_mats = unique_materials[test_idx]

    train_mask = np.isin(material_keys, train_mats)
    test_mask = np.isin(material_keys, test_mats)

    print("训练物质数:", len(train_mats))
    print("测试物质数:", len(test_mats))
    print("训练样本点数:", int(train_mask.sum()))
    print("测试样本点数:", int(test_mask.sum()))

    # -----------------------------------------------------
    # 模型A：无斜率 RF
    # -----------------------------------------------------
    X_train_A = build_X_no_slope(train_mask)
    y_train = y_ln[train_mask]

    valid_A = np.isfinite(X_train_A).all(axis=1) & np.isfinite(y_train)

    X_train_A = X_train_A[valid_A]
    y_train_A = y_train[valid_A]

    model_A = RandomForestRegressor(**rf_params)
    model_A.fit(X_train_A, y_train_A)

    X_test_A = build_X_no_slope(test_mask)
    y_test = y_ln[test_mask]

    valid_test_A = np.isfinite(X_test_A).all(axis=1)

    y_pred_A = np.full(len(y_test), np.nan, dtype=float)
    y_pred_A[valid_test_A] = model_A.predict(X_test_A[valid_test_A])

    # 完整数据集预测
    valid_all_A = np.isfinite(X_all_no_slope).all(axis=1)

    y_pred_A_all = np.full(len(y_ln), np.nan, dtype=float)
    y_pred_A_all[valid_all_A] = model_A.predict(X_all_no_slope[valid_all_A])

    # -----------------------------------------------------
    # 模型B：有斜率 RF
    # -----------------------------------------------------
    X_train_B = build_X_with_slope(train_mask)

    valid_B = np.isfinite(X_train_B).all(axis=1) & np.isfinite(y_train)

    X_train_B = X_train_B[valid_B]
    y_train_B = y_train[valid_B]

    model_B = RandomForestRegressor(**rf_params)
    model_B.fit(X_train_B, y_train_B)

    X_test_B = build_X_with_slope(test_mask)

    valid_test_B = np.isfinite(X_test_B).all(axis=1)

    y_pred_B = np.full(len(y_test), np.nan, dtype=float)
    y_pred_B[valid_test_B] = model_B.predict(X_test_B[valid_test_B])

    # 完整数据集预测
    valid_all_B = np.isfinite(X_all_with_slope).all(axis=1)

    y_pred_B_all = np.full(len(y_ln), np.nan, dtype=float)
    y_pred_B_all[valid_all_B] = model_B.predict(X_all_with_slope[valid_all_B])

    # -----------------------------------------------------
    # 测试集指标：保留 ln 空间和 viscosity 空间
    # -----------------------------------------------------
    m_A = calc_metrics(y_test, y_pred_A)
    m_B = calc_metrics(y_test, y_pred_B)

    m_A["fold"] = fold
    m_B["fold"] = fold

    metrics_no_slope.append(m_A)
    metrics_with_slope.append(m_B)

    print(
        "  RF(groups+InvT)       - "
        f"R2_ln={m_A['R2_ln']:.4f}, "
        f"MSE_ln={m_A['MSE_ln']:.6f}, "
        f"RMSE_ln={m_A['RMSE_ln']:.6f}, "
        f"MAE_ln={m_A['MAE_ln']:.6f}, "
        f"ARD_visc={m_A['ARD_visc_percent']:.2f}%"
    )

    print(
        "  RF(groups+InvT+slope) - "
        f"R2_ln={m_B['R2_ln']:.4f}, "
        f"MSE_ln={m_B['MSE_ln']:.6f}, "
        f"RMSE_ln={m_B['RMSE_ln']:.6f}, "
        f"MAE_ln={m_B['MAE_ln']:.6f}, "
        f"ARD_visc={m_B['ARD_visc_percent']:.2f}%"
    )

    # -----------------------------------------------------
    # 新增：每个 fold 模型预测完整数据集，并统计完整数据集三档偏差数量
    # 最终复制输出使用 viscosity 空间；同时保存 ln 空间。
    # -----------------------------------------------------
    count_A_all_visc = count_error_thresholds(
        y_visc,
        safe_exp(y_pred_A_all),
    )

    count_B_all_visc = count_error_thresholds(
        y_visc,
        safe_exp(y_pred_B_all),
    )

    count_A_all_ln = count_error_thresholds(
        y_ln,
        y_pred_A_all,
    )

    count_B_all_ln = count_error_thresholds(
        y_ln,
        y_pred_B_all,
    )

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "RF_groups_InvT",
        "count_space": "viscosity",
        **count_A_all_visc,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "RF_groups_InvT_slope",
        "count_space": "viscosity",
        **count_B_all_visc,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "RF_groups_InvT",
        "count_space": "lnVisc",
        **count_A_all_ln,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "RF_groups_InvT_slope",
        "count_space": "lnVisc",
        **count_B_all_ln,
    })

    print("\nRF(groups+InvT) fold model predicts ALL data count summary in viscosity space:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "RF_groups_InvT",
        "count_space": "viscosity",
        **count_A_all_visc,
    }]).to_string(index=False))

    print("\nRF(groups+InvT+slope) fold model predicts ALL data count summary in viscosity space:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "RF_groups_InvT_slope",
        "count_space": "viscosity",
        **count_B_all_visc,
    }]).to_string(index=False))

    # -----------------------------------------------------
    # 保存测试集预测明细
    # -----------------------------------------------------
    df_test_meta = df_model_clean.loc[test_mask].copy().reset_index(drop=True)
    df_all_meta = df_model_clean.copy().reset_index(drop=True)

    df_test_A = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="RF_groups_InvT",
        sub_df=df_test_meta,
        y_true_ln=y_test,
        y_pred_ln=y_pred_A,
    )

    df_test_B = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="RF_groups_InvT_slope",
        sub_df=df_test_meta,
        y_true_ln=y_test,
        y_pred_ln=y_pred_B,
    )

    fold_test_prediction_dfs.append(df_test_A)
    fold_test_prediction_dfs.append(df_test_B)

    # -----------------------------------------------------
    # 保存完整数据集预测明细
    # -----------------------------------------------------
    df_all_A = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="RF_groups_InvT",
        sub_df=df_all_meta,
        y_true_ln=y_ln,
        y_pred_ln=y_pred_A_all,
    )

    df_all_B = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="RF_groups_InvT_slope",
        sub_df=df_all_meta,
        y_true_ln=y_ln,
        y_pred_ln=y_pred_B_all,
    )

    fold_all_data_prediction_dfs.append(df_all_A)
    fold_all_data_prediction_dfs.append(df_all_B)

    # -----------------------------------------------------
    # 保存特征重要性
    # -----------------------------------------------------
    if hasattr(model_A, "feature_importances_"):
        for fname, imp in zip(feature_names_no, model_A.feature_importances_):
            feature_importance_no_records.append({
                "fold": fold,
                "feature": fname,
                "importance": imp,
            })

    if hasattr(model_B, "feature_importances_"):
        for fname, imp in zip(feature_names_with, model_B.feature_importances_):
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
        "n_all_points": len(y_ln),
        "n_features_no_slope": X_train_A.shape[1],
        "n_features_with_slope": X_train_B.shape[1],
        "n_valid_train_no_slope": len(y_train_A),
        "n_valid_train_with_slope": len(y_train_B),
        "n_valid_test_no_slope": int(valid_test_A.sum()),
        "n_valid_test_with_slope": int(valid_test_B.sum()),
    })


# =========================================================
# 4. 汇总统计
# =========================================================
df_A = pd.DataFrame(metrics_no_slope)
df_B = pd.DataFrame(metrics_with_slope)

df_A = df_A[["fold"] + [c for c in df_A.columns if c != "fold"]]
df_B = df_B[["fold"] + [c for c in df_B.columns if c != "fold"]]

summary_A = summarize(df_A, "RF (groups+InvT)")
summary_B = summarize(df_B, "RF (groups+InvT+slope)")

summary_all = pd.concat(
    [summary_A, summary_B],
    ignore_index=True,
)

print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
print(summary_all.to_string(index=False))


# =========================================================
# 5. 配对 t 检验
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
# 6. 完整数据集偏差数量统计汇总
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
        "n_all_data_points": len(y_ln),
    })

df_final_average_summary = pd.DataFrame(final_average_records)

print("\n========== Fold all-data count summary ==========")
print(df_fold_all_data_count_summary.to_string(index=False))

print("\n========== Final average all-data count summary ==========")
print(df_final_average_summary.to_string(index=False))


# =========================================================
# 7. 整理输出表
# =========================================================
df_fold_test_predictions = pd.concat(fold_test_prediction_dfs, ignore_index=True)
df_fold_all_data_predictions = pd.concat(fold_all_data_prediction_dfs, ignore_index=True)

df_fold_info = pd.DataFrame(fold_info_records)
df_feature_importance_no = pd.DataFrame(feature_importance_no_records)
df_feature_importance_with = pd.DataFrame(feature_importance_with_records)

df_used_groups = pd.DataFrame({
    "used_group": nonzero_group_cols,
    "occurrence_all_materials": (df_groups[nonzero_group_cols] != 0).sum(axis=0).values,
    "total_count_all": df_groups[nonzero_group_cols].sum(axis=0).values,
})

df_removed_zero_groups = pd.DataFrame({
    "removed_zero_group": removed_zero_group_cols,
})

df_slope_info = slope_df.copy()

df_run_info = pd.DataFrame([
    {"param": "main_input_file", "value": str(main_input_file)},
    {"param": "slope_file", "value": str(slope_file)},
    {"param": "data_sheet", "value": data_sheet},
    {"param": "groups_sheet", "value": groups_sheet},
    {"param": "slope_sheet", "value": slope_sheet},
    {"param": "viscosity_col", "value": viscosity_col},
    {"param": "lnvisc_col", "value": lnvisc_col},
    {"param": "temp_col", "value": temp_col},
    {"param": "slope_col", "value": slope_col},
    {"param": "n_outer_folds", "value": n_outer_folds},
    {"param": "random_state", "value": random_state},
    {"param": "rf_params", "value": str(rf_params)},
    {"param": "n_group_features", "value": len(nonzero_group_cols)},
    {"param": "total_samples", "value": len(y_ln)},
    {"param": "n_materials", "value": len(unique_materials)},
    {
        "param": "relative_error_definition",
        "value": "abs((y_pred - y_true) / y_true) * 100; abs(y_true)<=1e-12 -> NaN",
    },
    {
        "param": "final_count_space",
        "value": "viscosity space, eta=exp(lnVisc)",
    },
    {
        "param": "full_data_count_rule",
        "value": "Each fold model predicts the whole dataset; count viscosity-space rel_err <1%, <5%, <10%; then average counts over 5 folds.",
    },
])

df_model_structure = pd.DataFrame([
    {
        "项目": "预测对象",
        "内容": f"液体粘度 lnη，目标列 {lnvisc_col}；最终偏差数量按 η=exp(lnη) 空间统计",
    },
    {
        "项目": "主数据文件",
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
        "内容": "RF_groups_InvT：RandomForestRegressor 直接预测 lnη，输入 [Nk, 1/T]",
    },
    {
        "项目": "方法2",
        "内容": "RF_groups_InvT_slope：RandomForestRegressor 直接预测 lnη，输入 [Nk, 1/T, slope_pred_lnVisc_over_invT]",
    },
    {
        "项目": "是否包含子模型",
        "内容": "当前代码不训练子模型，但读取外部 HistGB 子模型预测得到的 slope",
    },
    {
        "项目": "子模型文件",
        "内容": str(slope_file),
    },
    {
        "项目": "子模型输出列",
        "内容": slope_col,
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
        "内容": "无显式 baseline + residual 结构；两个方法均为直接 RF 回归",
    },
    {
        "项目": "residual 构造",
        "内容": "无 residual 修正模型",
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
        "内容": f"[{len(nonzero_group_cols)} 个 Nk, 1/T]，总维度 {len(nonzero_group_cols) + 1}",
    },
    {
        "项目": "方法2最终输入",
        "内容": f"[{len(nonzero_group_cols)} 个 Nk, 1/T, slope_pred_lnVisc_over_invT]，总维度 {len(nonzero_group_cols) + 2}",
    },
    {
        "项目": "偏差数量统计口径",
        "内容": "每个 fold 模型预测完整数据集，在 η=exp(lnη) 空间统计相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 取平均",
    },
])


# =========================================================
# 8. 保存结果
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    # 原有核心输出
    df_A.to_excel(writer, sheet_name="Fold_Metrics_No_Slope", index=False)
    df_B.to_excel(writer, sheet_name="Fold_Metrics_With_Slope", index=False)
    summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
    df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)

    # 新增输出
    df_fold_test_predictions.to_excel(writer, sheet_name="fold_test_predictions", index=False)
    df_fold_all_data_predictions.to_excel(writer, sheet_name="fold_all_data_predictions", index=False)
    df_fold_all_data_count_summary.to_excel(writer, sheet_name="fold_all_data_count_summary", index=False)
    df_final_average_summary.to_excel(writer, sheet_name="final_average_summary", index=False)

    df_feature_importance_no.to_excel(writer, sheet_name="feature_importance_no", index=False)
    df_feature_importance_with.to_excel(writer, sheet_name="feature_importance_with", index=False)

    df_slope_info.to_excel(writer, sheet_name="slope_info", index=False)
    df_fold_info.to_excel(writer, sheet_name="Fold_Info", index=False)
    df_used_groups.to_excel(writer, sheet_name="Used_Groups", index=False)
    df_removed_zero_groups.to_excel(writer, sheet_name="Removed_Zero_Groups", index=False)

    df_run_info.to_excel(writer, sheet_name="Run_Info", index=False)
    df_model_structure.to_excel(writer, sheet_name="model_structure", index=False)

    format_excel(writer)

print(f"\n保存完成: {output_file}")


# =========================================================
# 9. 最终方便复制输出
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


no_1, no_5, no_10 = get_final_counts("RF_groups_InvT", count_space="viscosity")
with_1, with_5, with_10 = get_final_counts("RF_groups_InvT_slope", count_space="viscosity")

print("\n方法1 全数据预测偏差 1%，5%，10%分别为：")
print(no_1)
print(no_5)
print(no_10)

print("\n方法2 全数据预测偏差 1%，5%，10%分别为：")
print(with_1)
print(with_5)
print(with_10)


# =========================================================
# 10. 代码结构打印
# =========================================================
print("\n========== 当前代码结构简要汇总 ==========")
print(f"预测对象：液体粘度 lnη / {lnvisc_col}，最终偏差数量按 η=exp(lnη) 空间统计")
print(f"主数据文件：{main_input_file}")
print(f"slope 文件：{slope_file}")
print(f"sheet 名称：{data_sheet}, {groups_sheet}, {slope_sheet}")
print(f"交叉验证：{n_outer_folds}-fold KFold，按 material_key 物质划分")
print("方法1：RF_groups_InvT，RandomForestRegressor，输入 [Nk, 1/T]")
print("方法2：RF_groups_InvT_slope，RandomForestRegressor，输入 [Nk, 1/T, slope_pred_lnVisc_over_invT]")
print("子模型：当前代码不训练子模型，读取外部 HistGB 预测的 slope_pred_lnVisc_over_invT")
print(f"子模型预测列：{slope_col}")
print("子模型参数：当前代码无法从 slope 文件恢复，仅保存 slope 预测值")
print("slope 构造：直接读取 slope_pred_lnVisc_over_invT，作为方法2额外输入特征；没有乘以 1/T")
print("baseline 构造：无")
print("residual 模型：无")
print(f"最终模型：RandomForestRegressor，参数：{rf_params}")
print("方法1最终输入：[Nk, 1/T]")
print("方法2最终输入：[Nk, 1/T, slope_pred_lnVisc_over_invT]")
print("偏差统计口径：每个 fold 模型预测完整数据集，在 η=exp(lnη) 空间统计 <1%、<5%、<10% 点数，再对 5 个 fold 取平均")
