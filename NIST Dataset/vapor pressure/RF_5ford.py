# import pandas as pd
# import numpy as np
# from pathlib import Path
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.model_selection import KFold
# from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
# from scipy.stats import ttest_rel
#
# # =========================================================
# # 0. 全局设置
# # =========================================================
# main_input_file = Path("dataset_selected_by_two_k_with_lnP_invT_interpolation_8points.xlsx")
# slope_file = Path("HistGB_submodels_predict_ref_lnP_Tb_and_slope.xlsx")
# data_sheet = "Data_selected"
# groups_sheet = "Groups_selected"
# slope_sheet = "slope"
# slope_col = "slope_pred_lnP_over_invT"
#
# output_file = Path("RF_lnP_5fold_CV_comparison.xlsx")
#
# material_key_col = "material_key"
# temp_col = "T_K"
# target_candidates = ["lnP_kPa", "lnP", "ln_VaporPressure_kPa", "ln_pressure"]
# n_points_per_material = 8   # 仅用于校验，实际不依赖
# n_group_features_to_use = 220
# use_fixed_group_position = True
# group_start_col_1based = 3
# group_end_col_1based = 222
#
# test_size_global = 0.2    # 仅用于记录，交叉验证不使用
# random_state = 42
# n_outer_folds = 5
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
# # 1. 工具函数（与原始代码相同）
# # =========================================================
# def is_valid_value(x):
#     if pd.isna(x):
#         return False
#     s = str(x).strip()
#     if s == "" or s.lower() in ["nan", "none", "null", "待定"]:
#         return False
#     return True
#
# def build_material_key(row):
#     for col in ["material_key", "inchikey", "cas", "compound_name", "formula"]:
#         if col in row.index and is_valid_value(row[col]):
#             if col == "material_key":
#                 return str(row[col]).strip()
#             return f"{col}:{str(row[col]).strip()}"
#     return "unknown_material"
#
# def find_first_existing_col(df, candidates, col_type):
#     for col in candidates:
#         if col in df.columns:
#             return col
#     raise ValueError(f"没有找到 {col_type} 列。候选: {candidates}")
#
# def average_relative_deviation(y_true, y_pred, eps=1e-12):
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#     mask = (np.isfinite(y_true) & np.isfinite(y_pred) & (np.abs(y_true) > eps))
#     if mask.sum() == 0:
#         return np.nan
#     return float(np.mean(np.abs((y_pred[mask] - y_true[mask]) / y_true[mask])) * 100.0)
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
# def calc_metrics(y_true_lnP, y_pred_lnP, label_prefix=""):
#     """返回字典，包含 lnP 和 P 的指标"""
#     metrics = {
#         "n_points": len(y_true_lnP),
#         "R2_lnP": r2_score(y_true_lnP, y_pred_lnP) if len(y_true_lnP)>0 else np.nan,
#         "MSE_lnP": mean_squared_error(y_true_lnP, y_pred_lnP),
#         "RMSE_lnP": np.sqrt(mean_squared_error(y_true_lnP, y_pred_lnP)),
#         "MAE_lnP": mean_absolute_error(y_true_lnP, y_pred_lnP),
#         "ARD_lnP_percent": average_relative_deviation(y_true_lnP, y_pred_lnP),
#     }
#     P_true = np.exp(y_true_lnP)
#     P_pred = np.exp(y_pred_lnP)
#     metrics.update({
#         "R2_P": r2_score(P_true, P_pred),
#         "MSE_P": mean_squared_error(P_true, P_pred),
#         "RMSE_P": np.sqrt(mean_squared_error(P_true, P_pred)),
#         "MAE_P": mean_absolute_error(P_true, P_pred),
#         "ARD_P_percent": average_relative_deviation(P_true, P_pred),
#     })
#     metrics.update(error_band_counts(P_true, P_pred))
#     return metrics
#
# def identify_group_columns(df_groups, n=220):
#     if use_fixed_group_position:
#         start_idx = group_start_col_1based - 1
#         end_excl = group_end_col_1based
#         if len(df_groups.columns) < end_excl:
#             raise ValueError(f"Groups_selected 列数不足，需要取到第 {group_end_col_1based} 列")
#         group_cols = list(df_groups.columns[start_idx:end_excl])
#         if len(group_cols) != n:
#             raise ValueError(f"固定位置识别到 {len(group_cols)} 个基团，需要 {n} 个")
#         return group_cols
#     # 自动识别逻辑（略，但保留兼容）
#     metadata_keywords = ["material_key","compound","cas","formula","smiles","inchikey","pubchem","phase","boiling","temperature","temp","t_k","pressure","lnp","vapor","k1","k2","interp","status","range"]
#     candidate_cols = []
#     for col in df_groups.columns:
#         col_lower = str(col).strip().lower()
#         if any(k in col_lower for k in metadata_keywords):
#             continue
#         num = pd.to_numeric(df_groups[col], errors="coerce")
#         if num.notna().sum()>0:
#             candidate_cols.append(col)
#     if len(candidate_cols) < n:
#         raise ValueError(f"自动识别基团仅 {len(candidate_cols)} 个，少于 {n}")
#     return candidate_cols[:n]
#
# # =========================================================
# # 2. 读取数据
# # =========================================================
# df_data = pd.read_excel(main_input_file, sheet_name=data_sheet)
# df_groups = pd.read_excel(main_input_file, sheet_name=groups_sheet)
# df_slope = pd.read_excel(slope_file, sheet_name=slope_sheet)
#
# print("原始数据行数:", len(df_data))
# print("Groups 物质数:", len(df_groups))
# print("Slope sheet 行数:", len(df_slope))
#
# # 处理 material_key
# for df in [df_data, df_groups]:
#     if material_key_col not in df.columns:
#         df[material_key_col] = df.apply(build_material_key, axis=1)
#     df[material_key_col] = df[material_key_col].astype(str).str.strip()
#
# # 准备斜率数据
# if material_key_col not in df_slope.columns:
#     df_slope[material_key_col] = df_slope.apply(build_material_key, axis=1)
# df_slope[material_key_col] = df_slope[material_key_col].astype(str).str.strip()
# if slope_col not in df_slope.columns:
#     raise ValueError(f"Slope sheet 中缺少列 {slope_col}")
# df_slope[slope_col] = pd.to_numeric(df_slope[slope_col], errors="coerce")
# slope_df = df_slope[[material_key_col, slope_col]].drop_duplicates(subset=[material_key_col])
#
# # 找到目标列和温度列
# target_col = find_first_existing_col(df_data, target_candidates, "lnP 目标")
# print("目标列:", target_col)
# print("温度列:", temp_col)
#
# # 处理基团列
# group_cols_220 = identify_group_columns(df_groups, n_group_features_to_use)
# for col in group_cols_220:
#     df_groups[col] = pd.to_numeric(df_groups[col], errors="coerce").fillna(0.0)
# nonzero_group_cols = [col for col in group_cols_220 if not np.isclose(df_groups[col].abs().sum(), 0.0)]
# print("有效基团数:", len(nonzero_group_cols))
#
# # =========================================================
# # 3. 合并所有数据，构造温度点级别的完整表
# # =========================================================
# group_features = df_groups[[material_key_col] + nonzero_group_cols].drop_duplicates(subset=[material_key_col])
# # 合并基团
# df_model = df_data.merge(group_features, on=material_key_col, how="inner")
# # 合并斜率
# df_model = df_model.merge(slope_df, on=material_key_col, how="left")
#
# # 添加 1/T 特征
# df_model[temp_col] = pd.to_numeric(df_model[temp_col], errors="coerce")
# df_model[target_col] = pd.to_numeric(df_model[target_col], errors="coerce")
# df_model["InvT_1_per_K"] = 1.0 / df_model[temp_col]
#
# # 清理缺失值
# base_features = nonzero_group_cols + ["InvT_1_per_K"]
# features_no_slope = base_features
# features_with_slope = base_features + [slope_col]
#
# df_model_clean = df_model.dropna(subset=features_with_slope + [target_col, material_key_col]).copy()
# print("清理后样本点数:", len(df_model_clean))
# print("涉及物质数:", df_model_clean[material_key_col].nunique())
#
# # 提取物质列表
# unique_materials = df_model_clean[material_key_col].drop_duplicates().values
#
# # =========================================================
# # 4. 辅助函数：根据物质索引构建 X, y
# # =========================================================
# def get_data_for_materials(material_list, use_slope):
#     """返回 (X, y) 特征矩阵和目标"""
#     mask = df_model_clean[material_key_col].isin(material_list)
#     sub = df_model_clean[mask]
#     if use_slope:
#         X = sub[features_with_slope].values
#     else:
#         X = sub[features_no_slope].values
#     y = sub[target_col].values
#     return X, y
#
# # =========================================================
# # 5. 外层 5 折交叉验证
# # =========================================================
# kf = KFold(n_splits=n_outer_folds, shuffle=True, random_state=random_state)
#
# metrics_no_slope = []   # 每折指标
# metrics_with_slope = []
#
# for fold, (train_idx, test_idx) in enumerate(kf.split(unique_materials)):
#     print(f"\n========== Fold {fold+1}/{n_outer_folds} ==========")
#     train_mats = unique_materials[train_idx]
#     test_mats = unique_materials[test_idx]
#
#     # 模型A: 无斜率
#     X_train_no, y_train_no = get_data_for_materials(train_mats, use_slope=False)
#     X_test_no, y_test_no = get_data_for_materials(test_mats, use_slope=False)
#     if len(y_train_no) == 0:
#         print("  无训练样本，跳过")
#         continue
#     rf_no = RandomForestRegressor(**rf_params)
#     rf_no.fit(X_train_no, y_train_no)
#     y_pred_no = rf_no.predict(X_test_no)
#
#     # 模型B: 有斜率
#     X_train_with, y_train_with = get_data_for_materials(train_mats, use_slope=True)
#     X_test_with, y_test_with = get_data_for_materials(test_mats, use_slope=True)
#     if len(y_train_with) == 0:
#         print("  有斜率模型无训练样本，跳过")
#         continue
#     rf_with = RandomForestRegressor(**rf_params)
#     rf_with.fit(X_train_with, y_train_with)
#     y_pred_with = rf_with.predict(X_test_with)
#
#     # 计算指标
#     met_no = calc_metrics(y_test_no, y_pred_no, "no_slope")
#     met_with = calc_metrics(y_test_with, y_pred_with, "with_slope")
#     met_no["fold"] = fold+1
#     met_with["fold"] = fold+1
#     metrics_no_slope.append(met_no)
#     metrics_with_slope.append(met_with)
#
# # =========================================================
# # 6. 汇总统计（均值±标准差）
# # =========================================================
# df_no = pd.DataFrame(metrics_no_slope)
# df_with = pd.DataFrame(metrics_with_slope)
#
# # 需要汇总的指标列（排除 fold 和 n_points）
# metric_cols = [c for c in df_no.columns if c not in ["fold", "n_points"]]
#
# def summarize(df, name):
#     rows = []
#     for metric in metric_cols:
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
# summary_no = summarize(df_no, "RF (groups + 1/T)")
# summary_with = summarize(df_with, "RF (groups + 1/T + slope)")
# summary_all = pd.concat([summary_no, summary_with], ignore_index=True)
#
# print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
# print(summary_all.to_string(index=False))
#
# # =========================================================
# # 7. 配对 t 检验（对每一折相同指标）
# # =========================================================
# t_test_results = []
# for metric in metric_cols:
#     vals_no = df_no[metric].dropna().values
#     vals_with = df_with[metric].dropna().values
#     if len(vals_no) == len(vals_with) and len(vals_no) > 1:
#         t_stat, p_val = ttest_rel(vals_no, vals_with)
#         # 判断哪个更好（对于误差类指标越小越好，对于R2越大越好）
#         if "R2" in metric:
#             better = "with_slope" if np.mean(vals_with) > np.mean(vals_no) else "no_slope"
#             sig = p_val < 0.05
#         else:
#             better = "with_slope" if np.mean(vals_with) < np.mean(vals_no) else "no_slope"
#             sig = p_val < 0.05
#         t_test_results.append({
#             "Metric": metric,
#             "Mean_no_slope": f"{np.mean(vals_no):.4f}",
#             "Mean_with_slope": f"{np.mean(vals_with):.4f}",
#             "p-value": f"{p_val:.4e}",
#             "Significant (p<0.05)": sig,
#             "Better model": better
#         })
#
# df_ttest = pd.DataFrame(t_test_results)
# print("\n========== Paired t-test ==========")
# print(df_ttest.to_string(index=False))
#
# # =========================================================
# # 8. 保存 Excel
# # =========================================================
# with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
#     df_no.to_excel(writer, sheet_name="Fold_Metrics_No_Slope", index=False)
#     df_with.to_excel(writer, sheet_name="Fold_Metrics_With_Slope", index=False)
#     summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
#     df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)
#
#     # 保存运行信息
#     run_info = pd.DataFrame([
#         {"param": "n_outer_folds", "value": n_outer_folds},
#         {"param": "random_state", "value": random_state},
#         {"param": "rf_params", "value": str(rf_params)},
#         {"param": "n_group_features", "value": len(nonzero_group_cols)},
#         {"param": "total_samples", "value": len(df_model_clean)},
#         {"param": "n_materials", "value": len(unique_materials)},
#     ])
#     run_info.to_excel(writer, sheet_name="Run_Info", index=False)
#
#     # 格式化浮点数
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
# print("主要输出表格:")
# print("- Fold_Metrics_No_Slope: 每折无斜率模型指标")
# print("- Fold_Metrics_With_Slope: 每折有斜率模型指标")
# print("- Summary_Mean_Std: 均值±标准差汇总")
# print("- Paired_T_Test: 配对t检验结果")


import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from scipy.stats import ttest_rel


# =========================================================
# 0. 全局设置
# =========================================================
pd.set_option("display.float_format", "{:.10f}".format)
np.set_printoptions(suppress=True, precision=10)

main_input_file = Path("dataset_selected_by_two_k_with_lnP_invT_interpolation_8points.xlsx")
slope_file = Path("HistGB_submodels_predict_ref_lnP_Tb_and_slope.xlsx")

data_sheet = "Data_selected"
groups_sheet = "Groups_selected"
slope_sheet = "slope"
slope_col = "slope_pred_lnP_over_invT"

output_file = Path("RF_lnP_5fold_CV_comparison.xlsx")

material_key_col = "material_key"
temp_col = "T_K"
target_candidates = ["lnP_kPa", "lnP", "ln_VaporPressure_kPa", "ln_pressure"]

n_points_per_material = 8
n_group_features_to_use = 220
use_fixed_group_position = True
group_start_col_1based = 3
group_end_col_1based = 222

test_size_global = 0.2
random_state = 42
n_outer_folds = 5

# RF 参数（与原始代码一致）
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


def safe_exp(x):
    return np.exp(np.clip(np.asarray(x, dtype=float), -700, 700))


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


def average_relative_deviation(y_true, y_pred, eps=1e-12):
    rel_err = safe_relative_error_percent(y_true, y_pred, eps=eps)

    if np.any(np.isfinite(rel_err)):
        return float(np.nanmean(rel_err))

    return np.nan


def error_band_counts(y_true, y_pred, bands=(1, 5, 10), prefix=""):
    """
    统计相对误差 <1%、<5%、<10% 的数量和比例。
    注意：这里使用严格小于 <，不是 <=。
    """
    rel_err = safe_relative_error_percent(y_true, y_pred)

    out = {}
    n_valid = int(np.sum(np.isfinite(rel_err)))

    for b in bands:
        out[f"{prefix}within_{b}pct_count"] = float(np.nansum(rel_err < b))
        out[f"{prefix}within_{b}pct_ratio"] = (
            float(np.nansum(rel_err < b) / n_valid)
            if n_valid > 0
            else np.nan
        )

    out[f"{prefix}n_valid_relative_error"] = n_valid

    return out


def count_error_thresholds(y_true, y_pred):
    """
    用于最终全数据偏差数量统计。
    返回 <1%、<5%、<10% 的点数。
    """
    rel_err = safe_relative_error_percent(y_true, y_pred)

    return {
        "count_rel_err_lt_1pct": float(np.nansum(rel_err < 1.0)),
        "count_rel_err_lt_5pct": float(np.nansum(rel_err < 5.0)),
        "count_rel_err_lt_10pct": float(np.nansum(rel_err < 10.0)),
        "n_valid_for_relative_error": int(np.sum(np.isfinite(rel_err))),
    }


def calc_metrics(y_true_lnP, y_pred_lnP, label_prefix=""):
    """
    返回字典，包含 lnP 和 P 空间指标。

    lnP 指标:
        R2_lnP, MSE_lnP, RMSE_lnP, MAE_lnP, ARD_lnP_percent

    P 指标:
        R2_P, MSE_P, RMSE_P, MAE_P, ARD_P_percent

    误差区间:
        在 P = exp(lnP) 空间中统计。
    """
    y_true_lnP = np.asarray(y_true_lnP, dtype=float)
    y_pred_lnP = np.asarray(y_pred_lnP, dtype=float)

    mask = np.isfinite(y_true_lnP) & np.isfinite(y_pred_lnP)

    y_true_lnP = y_true_lnP[mask]
    y_pred_lnP = y_pred_lnP[mask]

    if len(y_true_lnP) == 0:
        metrics = {
            "n_points": 0,
            "R2_lnP": np.nan,
            "MSE_lnP": np.nan,
            "RMSE_lnP": np.nan,
            "MAE_lnP": np.nan,
            "ARD_lnP_percent": np.nan,
            "R2_P": np.nan,
            "MSE_P": np.nan,
            "RMSE_P": np.nan,
            "MAE_P": np.nan,
            "ARD_P_percent": np.nan,
        }
        metrics.update(error_band_counts([], [], prefix="P_"))
        metrics.update(error_band_counts([], [], prefix="lnP_"))
        return metrics

    metrics = {
        "n_points": len(y_true_lnP),
        "R2_lnP": r2_score(y_true_lnP, y_pred_lnP) if len(y_true_lnP) > 1 else np.nan,
        "MSE_lnP": mean_squared_error(y_true_lnP, y_pred_lnP),
        "RMSE_lnP": np.sqrt(mean_squared_error(y_true_lnP, y_pred_lnP)),
        "MAE_lnP": mean_absolute_error(y_true_lnP, y_pred_lnP),
        "ARD_lnP_percent": average_relative_deviation(y_true_lnP, y_pred_lnP),
    }

    P_true = safe_exp(y_true_lnP)
    P_pred = safe_exp(y_pred_lnP)

    metrics.update({
        "R2_P": r2_score(P_true, P_pred) if len(P_true) > 1 else np.nan,
        "MSE_P": mean_squared_error(P_true, P_pred),
        "RMSE_P": np.sqrt(mean_squared_error(P_true, P_pred)),
        "MAE_P": mean_absolute_error(P_true, P_pred),
        "ARD_P_percent": average_relative_deviation(P_true, P_pred),
    })

    # 保留 P 空间误差区间，作为主要偏差数量统计
    metrics.update(error_band_counts(P_true, P_pred, prefix="P_"))

    # 额外保留 lnP 空间误差区间，便于追溯
    metrics.update(error_band_counts(y_true_lnP, y_pred_lnP, prefix="lnP_"))

    return metrics


def identify_group_columns(df_groups, n=220):
    if use_fixed_group_position:
        start_idx = group_start_col_1based - 1
        end_excl = group_end_col_1based

        if len(df_groups.columns) < end_excl:
            raise ValueError(f"Groups_selected 列数不足，需要取到第 {group_end_col_1based} 列")

        group_cols = list(df_groups.columns[start_idx:end_excl])

        if len(group_cols) != n:
            raise ValueError(f"固定位置识别到 {len(group_cols)} 个基团，需要 {n} 个")

        return group_cols

    # 自动识别逻辑，保留兼容
    metadata_keywords = [
        "material_key", "compound", "cas", "formula", "smiles", "inchikey",
        "pubchem", "phase", "boiling", "temperature", "temp", "t_k",
        "pressure", "lnp", "vapor", "k1", "k2", "interp", "status", "range"
    ]

    candidate_cols = []

    for col in df_groups.columns:
        col_lower = str(col).strip().lower()

        if any(k in col_lower for k in metadata_keywords):
            continue

        num = pd.to_numeric(df_groups[col], errors="coerce")

        if num.notna().sum() > 0:
            candidate_cols.append(col)

    if len(candidate_cols) < n:
        raise ValueError(f"自动识别基团仅 {len(candidate_cols)} 个，少于 {n}")

    return candidate_cols[:n]


def get_data_for_materials(material_list, use_slope, return_df=False):
    """
    根据物质列表返回 X, y。
    """
    mask = df_model_clean[material_key_col].isin(material_list)
    sub = df_model_clean[mask].copy()

    if use_slope:
        X = sub[features_with_slope].values
    else:
        X = sub[features_no_slope].values

    y = sub[target_col].values

    if return_df:
        return X, y, sub

    return X, y


def make_prediction_df(fold, dataset_name, method, sub_df, y_true_lnP, y_pred_lnP):
    """
    保存测试集或完整数据集预测明细。
    """
    y_true_lnP = np.asarray(y_true_lnP, dtype=float)
    y_pred_lnP = np.asarray(y_pred_lnP, dtype=float)

    P_true = safe_exp(y_true_lnP)
    P_pred = safe_exp(y_pred_lnP)

    df_out = pd.DataFrame({
        "fold": fold,
        "dataset": dataset_name,
        "Method": method,
        material_key_col: sub_df[material_key_col].values,
        temp_col: sub_df[temp_col].values,
        "InvT_1_per_K": sub_df["InvT_1_per_K"].values,
        "slope_pred": sub_df[slope_col].values if slope_col in sub_df.columns else np.nan,
        "lnP_true": y_true_lnP,
        "lnP_pred": y_pred_lnP,
        "lnP_error": y_pred_lnP - y_true_lnP,
        "lnP_abs_error": np.abs(y_pred_lnP - y_true_lnP),
        "lnP_relative_error_percent": safe_relative_error_percent(y_true_lnP, y_pred_lnP),
        "P_true": P_true,
        "P_pred": P_pred,
        "P_error": P_pred - P_true,
        "P_abs_error": np.abs(P_pred - P_true),
        "P_relative_error_percent": safe_relative_error_percent(P_true, P_pred),
    })

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
        if col in sub_df.columns:
            df_out[col] = sub_df[col].values

    return df_out


def summarize(df, name, metric_cols):
    rows = []

    for metric in metric_cols:
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
df_data = pd.read_excel(main_input_file, sheet_name=data_sheet)
df_groups = pd.read_excel(main_input_file, sheet_name=groups_sheet)
df_slope = pd.read_excel(slope_file, sheet_name=slope_sheet)

print("原始数据行数:", len(df_data))
print("Groups 物质数:", len(df_groups))
print("Slope sheet 行数:", len(df_slope))


# =========================================================
# 3. 处理 material_key
# =========================================================
for df in [df_data, df_groups]:
    if material_key_col not in df.columns:
        df[material_key_col] = df.apply(build_material_key, axis=1)

    df[material_key_col] = df[material_key_col].astype(str).str.strip()


# =========================================================
# 4. 准备斜率数据
# =========================================================
if material_key_col not in df_slope.columns:
    df_slope[material_key_col] = df_slope.apply(build_material_key, axis=1)

df_slope[material_key_col] = df_slope[material_key_col].astype(str).str.strip()

if slope_col not in df_slope.columns:
    raise ValueError(f"Slope sheet 中缺少列 {slope_col}")

df_slope[slope_col] = pd.to_numeric(df_slope[slope_col], errors="coerce")

slope_df = (
    df_slope[[material_key_col, slope_col]]
    .drop_duplicates(subset=[material_key_col])
    .copy()
)


# =========================================================
# 5. 找到目标列和温度列
# =========================================================
target_col = find_first_existing_col(df_data, target_candidates, "lnP 目标")

print("目标列:", target_col)
print("温度列:", temp_col)


# =========================================================
# 6. 处理基团列
# =========================================================
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

print("有效基团数:", len(nonzero_group_cols))
print("删除全零基团数:", len(removed_zero_group_cols))


# =========================================================
# 7. 合并所有数据，构造温度点级别完整表
# =========================================================
group_features = (
    df_groups[[material_key_col] + nonzero_group_cols]
    .drop_duplicates(subset=[material_key_col])
)

df_model = df_data.merge(
    group_features,
    on=material_key_col,
    how="inner",
)

df_model = df_model.merge(
    slope_df,
    on=material_key_col,
    how="left",
)

df_model[temp_col] = pd.to_numeric(df_model[temp_col], errors="coerce")
df_model[target_col] = pd.to_numeric(df_model[target_col], errors="coerce")
df_model["InvT_1_per_K"] = 1.0 / df_model[temp_col]

base_features = nonzero_group_cols + ["InvT_1_per_K"]
features_no_slope = base_features
features_with_slope = base_features + [slope_col]

df_model_clean = df_model.dropna(
    subset=features_with_slope + [target_col, material_key_col]
).copy()

df_model_clean = df_model_clean.reset_index(drop=True)

print("清理后样本点数:", len(df_model_clean))
print("涉及物质数:", df_model_clean[material_key_col].nunique())

unique_materials = df_model_clean[material_key_col].drop_duplicates().values

if len(unique_materials) < n_outer_folds:
    raise ValueError(
        f"物质数 {len(unique_materials)} 小于 n_outer_folds={n_outer_folds}，无法做 5-fold。"
    )

# 完整数据集
X_all_no = df_model_clean[features_no_slope].values
X_all_with = df_model_clean[features_with_slope].values
y_all_lnP = df_model_clean[target_col].values

P_all_true = safe_exp(y_all_lnP)


# =========================================================
# 8. 外层 5 折交叉验证
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

for fold, (train_idx, test_idx) in enumerate(kf.split(unique_materials), start=1):
    print(f"\n========== Fold {fold}/{n_outer_folds} ==========")

    train_mats = unique_materials[train_idx]
    test_mats = unique_materials[test_idx]

    # -----------------------------------------------------
    # 模型A: 无斜率
    # -----------------------------------------------------
    X_train_no, y_train_no, df_train_no = get_data_for_materials(
        train_mats,
        use_slope=False,
        return_df=True,
    )
    X_test_no, y_test_no, df_test_no = get_data_for_materials(
        test_mats,
        use_slope=False,
        return_df=True,
    )

    if len(y_train_no) == 0:
        print("  无斜率模型无训练样本，跳过该 fold")
        continue

    rf_no = RandomForestRegressor(**rf_params)
    rf_no.fit(X_train_no, y_train_no)

    y_pred_no_test = rf_no.predict(X_test_no)
    y_pred_no_all = rf_no.predict(X_all_no)

    # -----------------------------------------------------
    # 模型B: 有斜率
    # -----------------------------------------------------
    X_train_with, y_train_with, df_train_with = get_data_for_materials(
        train_mats,
        use_slope=True,
        return_df=True,
    )
    X_test_with, y_test_with, df_test_with = get_data_for_materials(
        test_mats,
        use_slope=True,
        return_df=True,
    )

    if len(y_train_with) == 0:
        print("  有斜率模型无训练样本，跳过该 fold")
        continue

    rf_with = RandomForestRegressor(**rf_params)
    rf_with.fit(X_train_with, y_train_with)

    y_pred_with_test = rf_with.predict(X_test_with)
    y_pred_with_all = rf_with.predict(X_all_with)

    # -----------------------------------------------------
    # 测试集指标：保留原有 lnP 和 P 空间指标
    # -----------------------------------------------------
    met_no = calc_metrics(y_test_no, y_pred_no_test, "no_slope")
    met_with = calc_metrics(y_test_with, y_pred_with_test, "with_slope")

    met_no["fold"] = fold
    met_with["fold"] = fold

    metrics_no_slope.append(met_no)
    metrics_with_slope.append(met_with)

    print(
        "RF no_slope test: "
        f"R2_lnP={met_no['R2_lnP']:.6f}, "
        f"MSE_lnP={met_no['MSE_lnP']:.6f}, "
        f"MAE_lnP={met_no['MAE_lnP']:.6f}, "
        f"ARD_P={met_no['ARD_P_percent']:.6f}%"
    )

    print(
        "RF with_slope test: "
        f"R2_lnP={met_with['R2_lnP']:.6f}, "
        f"MSE_lnP={met_with['MSE_lnP']:.6f}, "
        f"MAE_lnP={met_with['MAE_lnP']:.6f}, "
        f"ARD_P={met_with['ARD_P_percent']:.6f}%"
    )

    # -----------------------------------------------------
    # 新增：每个 fold 模型预测完整数据集，并统计 P 空间偏差数量
    # -----------------------------------------------------
    P_pred_no_all = safe_exp(y_pred_no_all)
    P_pred_with_all = safe_exp(y_pred_with_all)

    count_no_all_P = count_error_thresholds(P_all_true, P_pred_no_all)
    count_with_all_P = count_error_thresholds(P_all_true, P_pred_with_all)

    # 额外保留 lnP 空间全数据偏差数量，方便追溯；最终复制输出仍使用 P 空间。
    count_no_all_lnP = count_error_thresholds(y_all_lnP, y_pred_no_all)
    count_with_all_lnP = count_error_thresholds(y_all_lnP, y_pred_with_all)

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "RF_groups_InvT",
        "count_space": "P",
        **count_no_all_P,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "RF_groups_InvT_slope",
        "count_space": "P",
        **count_with_all_P,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "RF_groups_InvT",
        "count_space": "lnP",
        **count_no_all_lnP,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "RF_groups_InvT_slope",
        "count_space": "lnP",
        **count_with_all_lnP,
    })

    print("\nRF no_slope fold model predicts ALL data count summary in P space:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "RF_groups_InvT",
        "count_space": "P",
        **count_no_all_P,
    }]).to_string(index=False))

    print("\nRF with_slope fold model predicts ALL data count summary in P space:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "RF_groups_InvT_slope",
        "count_space": "P",
        **count_with_all_P,
    }]).to_string(index=False))

    # -----------------------------------------------------
    # 保存测试集预测明细
    # -----------------------------------------------------
    df_test_pred_no = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="RF_groups_InvT",
        sub_df=df_test_no,
        y_true_lnP=y_test_no,
        y_pred_lnP=y_pred_no_test,
    )

    df_test_pred_with = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="RF_groups_InvT_slope",
        sub_df=df_test_with,
        y_true_lnP=y_test_with,
        y_pred_lnP=y_pred_with_test,
    )

    fold_test_prediction_dfs.append(df_test_pred_no)
    fold_test_prediction_dfs.append(df_test_pred_with)

    # -----------------------------------------------------
    # 保存完整数据集预测明细
    # -----------------------------------------------------
    df_all_pred_no = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="RF_groups_InvT",
        sub_df=df_model_clean,
        y_true_lnP=y_all_lnP,
        y_pred_lnP=y_pred_no_all,
    )

    df_all_pred_with = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="RF_groups_InvT_slope",
        sub_df=df_model_clean,
        y_true_lnP=y_all_lnP,
        y_pred_lnP=y_pred_with_all,
    )

    fold_all_data_prediction_dfs.append(df_all_pred_no)
    fold_all_data_prediction_dfs.append(df_all_pred_with)

    # -----------------------------------------------------
    # 保存特征重要性
    # -----------------------------------------------------
    if hasattr(rf_no, "feature_importances_"):
        for feature_name, importance in zip(features_no_slope, rf_no.feature_importances_):
            feature_importance_no_records.append({
                "fold": fold,
                "feature": feature_name,
                "importance": importance,
            })

    if hasattr(rf_with, "feature_importances_"):
        for feature_name, importance in zip(features_with_slope, rf_with.feature_importances_):
            feature_importance_with_records.append({
                "fold": fold,
                "feature": feature_name,
                "importance": importance,
            })

    fold_info_records.append({
        "fold": fold,
        "n_train_materials": len(train_mats),
        "n_test_materials": len(test_mats),
        "n_train_points_no_slope": len(y_train_no),
        "n_test_points_no_slope": len(y_test_no),
        "n_train_points_with_slope": len(y_train_with),
        "n_test_points_with_slope": len(y_test_with),
        "n_all_data_points": len(y_all_lnP),
        "n_features_no_slope": X_train_no.shape[1],
        "n_features_with_slope": X_train_with.shape[1],
    })


# =========================================================
# 9. 汇总统计（均值±标准差）
# =========================================================
df_no = pd.DataFrame(metrics_no_slope)
df_with = pd.DataFrame(metrics_with_slope)

if df_no.empty or df_with.empty:
    raise RuntimeError("没有成功完成任何 fold，请检查数据或特征。")

metric_cols = [c for c in df_no.columns if c not in ["fold", "n_points"]]

summary_no = summarize(df_no, "RF (groups + 1/T)", metric_cols)
summary_with = summarize(df_with, "RF (groups + 1/T + slope)", metric_cols)

summary_all = pd.concat([summary_no, summary_with], ignore_index=True)

print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
print(summary_all.to_string(index=False))


# =========================================================
# 10. 配对 t 检验
# =========================================================
t_test_results = []

for metric in metric_cols:
    vals_no = df_no[metric].values.astype(float)
    vals_with = df_with[metric].values.astype(float)

    valid = np.isfinite(vals_no) & np.isfinite(vals_with)

    vals_no = vals_no[valid]
    vals_with = vals_with[valid]

    if len(vals_no) > 1:
        t_stat, p_val = ttest_rel(vals_no, vals_with)

        # 判断哪个更好：R2 越大越好，其余误差类越小越好
        if "R2" in metric:
            better = "with_slope" if np.mean(vals_with) > np.mean(vals_no) else "no_slope"
        else:
            better = "with_slope" if np.mean(vals_with) < np.mean(vals_no) else "no_slope"

        sig = p_val < 0.05

        t_test_results.append({
            "Metric": metric,
            "Mean_no_slope": f"{np.mean(vals_no):.4f}",
            "Mean_with_slope": f"{np.mean(vals_with):.4f}",
            "p-value": f"{p_val:.4e}",
            "Significant (p<0.05)": sig,
            "Better model": better,
            "n_valid_fold_pairs": len(vals_no),
        })

df_ttest = pd.DataFrame(t_test_results)

print("\n========== Paired t-test ==========")
print(df_ttest.to_string(index=False))


# =========================================================
# 11. 完整数据集偏差数量统计汇总
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
        "n_all_data_points": len(y_all_lnP),
    })

df_final_average_summary = pd.DataFrame(final_average_records)

print("\n========== Fold all-data count summary ==========")
print(df_fold_all_data_count_summary.to_string(index=False))

print("\n========== Final average all-data count summary ==========")
print(df_final_average_summary.to_string(index=False))


# =========================================================
# 12. 整理输出表
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
    {"param": "target_col", "value": target_col},
    {"param": "temp_col", "value": temp_col},
    {"param": "slope_col", "value": slope_col},
    {"param": "n_outer_folds", "value": n_outer_folds},
    {"param": "random_state", "value": random_state},
    {"param": "test_size_global_record_only", "value": test_size_global},
    {"param": "rf_params", "value": str(rf_params)},
    {"param": "n_group_features", "value": len(nonzero_group_cols)},
    {"param": "total_samples", "value": len(df_model_clean)},
    {"param": "n_materials", "value": len(unique_materials)},
    {
        "param": "relative_error_definition",
        "value": "abs((y_pred - y_true) / y_true) * 100; abs(y_true)<=1e-12 -> NaN",
    },
    {
        "param": "final_count_space",
        "value": "P space, where P=exp(lnP)",
    },
    {
        "param": "full_data_count_rule",
        "value": "Each fold model predicts the whole dataset; count P-space relative error <1%, <5%, <10%; then average counts over 5 folds.",
    },
])


df_model_structure = pd.DataFrame([
    {
        "项目": "预测对象",
        "内容": f"蒸汽压 lnP，目标列 {target_col}；同时保存 P=exp(lnP) 空间指标",
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
        "内容": "RF_groups_InvT：RandomForestRegressor，输入 [Nk, 1/T]",
    },
    {
        "项目": "方法2",
        "内容": "RF_groups_InvT_slope：RandomForestRegressor，输入 [Nk, 1/T, slope_pred_lnP_over_invT]",
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
        "内容": "slope_pred_lnP_over_invT，用作方法2额外输入特征",
    },
    {
        "项目": "子模型类型",
        "内容": "外部文件名显示为 HistGB；本代码只读取预测结果，不在当前脚本内训练",
    },
    {
        "项目": "子模型参数",
        "内容": "当前脚本无法从 slope 文件恢复；仅保存 slope 预测结果",
    },
    {
        "项目": "slope 构造",
        "内容": "直接读取 slope_pred_lnP_over_invT，作为方法2额外输入特征；不再乘以 1/T",
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
        "内容": f"[{len(nonzero_group_cols)} 个 Nk, 1/T, slope_pred_lnP_over_invT]，总维度 {len(nonzero_group_cols) + 2}",
    },
    {
        "项目": "偏差数量统计口径",
        "内容": "每个 fold 模型预测完整数据集，在 P=exp(lnP) 空间统计相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 取平均",
    },
])


# =========================================================
# 13. 保存 Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    # 原有核心输出
    df_no.to_excel(writer, sheet_name="Fold_Metrics_No_Slope", index=False)
    df_with.to_excel(writer, sheet_name="Fold_Metrics_With_Slope", index=False)
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

print("主要输出表格:")
print("- Fold_Metrics_No_Slope: 每折无斜率模型指标")
print("- Fold_Metrics_With_Slope: 每折有斜率模型指标")
print("- Summary_Mean_Std: 均值±标准差汇总")
print("- Paired_T_Test: 配对t检验结果")
print("- fold_test_predictions: 每折测试集预测明细")
print("- fold_all_data_predictions: 每折模型预测完整数据集明细")
print("- fold_all_data_count_summary: 每折完整数据集偏差数量")
print("- final_average_summary: 5-fold 完整数据集偏差数量平均")
print("- model_structure: 模型结构汇总")


# =========================================================
# 14. 最终方便复制输出
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


no_1, no_5, no_10 = get_final_counts("RF_groups_InvT", count_space="P")
with_1, with_5, with_10 = get_final_counts("RF_groups_InvT_slope", count_space="P")

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
print(f"预测对象：蒸汽压 lnP / {target_col}，并保存 P=exp(lnP) 空间指标")
print(f"主数据文件：{main_input_file}")
print(f"slope 文件：{slope_file}")
print(f"sheet 名称：{data_sheet}, {groups_sheet}, {slope_sheet}")
print(f"交叉验证：{n_outer_folds}-fold，按 material_key 物质划分")
print("方法1：RF_groups_InvT，RandomForestRegressor，输入 [Nk, 1/T]")
print("方法2：RF_groups_InvT_slope，RandomForestRegressor，输入 [Nk, 1/T, slope_pred_lnP_over_invT]")
print("子模型：当前代码不训练子模型，读取外部 HistGB 预测的 slope_pred_lnP_over_invT")
print(f"子模型预测列：{slope_col}")
print("子模型参数：当前代码无法从 slope 文件恢复，仅保存 slope 预测值")
print("slope 构造：直接读取 slope_pred_lnP_over_invT，作为方法2额外输入特征")
print("baseline 构造：无")
print("residual 模型：无")
print(f"最终模型：RandomForestRegressor，参数：{rf_params}")
print("方法1最终输入：[Nk, 1/T]")
print("方法2最终输入：[Nk, 1/T, slope_pred_lnP_over_invT]")
print("偏差统计口径：每个 fold 模型预测完整数据集，在 P=exp(lnP) 空间统计 <1%、<5%、<10% 点数，再对 5 个 fold 取平均")