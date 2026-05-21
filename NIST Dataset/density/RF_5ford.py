# import pandas as pd
# import numpy as np
# from pathlib import Path
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.model_selection import GroupKFold
# from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
# from scipy.stats import ttest_rel
#
# # =========================================================
# # 0. 全局设置
# # =========================================================
# main_input_file = Path("dataset_density_selected_by_two_k_with_density_T_interpolation_8points.xlsx")
# slope_file = Path("HistGB_submodels_predict_ref_density_Tb_and_slope.xlsx")
# data_sheet = "Data_selected"
# groups_sheet = "Groups_selected"
# slope_sheet = "slope"
# slope_col = "slope_pred_density_over_T"
#
# output_file = Path("RF_density_5fold_CV_comparison.xlsx")
#
# material_key_col = "material_key"
# temp_col = "T_K"
#
# density_col_candidates = [
#     "property_value", "value", "Density_kg_m3", "density_kg_m3",
#     "Density, kg/m3", "Mass density, kg/m3", "mass_density_kg_m3",
#     "Mass_Density_kg_m3", "rho_kg_m3", "rho", "density", "Density"
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
# # 随机森林参数（与原始代码一致，但固定随机种子）
# rf_params = {
#     "n_estimators": 800,
#     "max_depth": None,
#     "min_samples_split": 2,
#     "min_samples_leaf": 1,
#     "max_features": 1.0,
#     "bootstrap": True,
#     "n_jobs": -1,
#     "random_state": 42,
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
# def build_material_key(row):
#     for col in ["material_key","inchikey","InChIKey","inchi_key",
#                 "pubchem_inchikey","PubChem_InChIKey","cas","compound_name","formula"]:
#         if col in row.index and is_valid_value(row[col]):
#             if col == "material_key": return str(row[col]).strip()
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
#         # 自动识别（略，实际使用固定位置）
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
#     """返回 R2, MSE, RMSE, MAE, ARD (%)"""
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
# # 2. 读取主数据并预处理（一次性）
# # =========================================================
# print("读取主数据...")
# if not main_input_file.exists():
#     raise FileNotFoundError(f"没有找到主输入文件: {main_input_file}")
# df_data = pd.read_excel(main_input_file, sheet_name=data_sheet)
# df_groups = pd.read_excel(main_input_file, sheet_name=groups_sheet)
# print(f"Data_selected 行数: {len(df_data)}, Groups_selected 物质数: {len(df_groups)}")
#
# # 物质ID对齐
# for df in [df_data, df_groups]:
#     if material_key_col not in df.columns:
#         df[material_key_col] = df.apply(build_material_key, axis=1)
#     df[material_key_col] = df[material_key_col].astype(str).str.strip()
#
# # 找到密度目标列和温度列
# density_col = find_first_existing_col(df_data, density_col_candidates, "density", required=True)
# if temp_col not in df_data.columns:
#     raise ValueError(f"Data_selected 中没有找到温度列: {temp_col}")
# df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
# df_data[density_col] = pd.to_numeric(df_data[density_col], errors="coerce")
# print(f"使用 density 目标列: {density_col}, 温度列: {temp_col}")
#
# # 基团列处理
# group_cols_220 = identify_group_columns(df_groups, n_group_features_to_use)
# df_groups_numeric = df_groups[group_cols_220].apply(pd.to_numeric, errors="coerce").fillna(0.0)
# nonzero_mask = df_groups_numeric.abs().sum(axis=0) != 0
# used_group_cols = df_groups_numeric.columns[nonzero_mask].tolist()
# df_groups_used = df_groups_numeric[used_group_cols].copy()
# print(f"有效基团数: {len(used_group_cols)}")
#
# # =========================================================
# # 3. 读取 slope 数据（仅用于有斜率模型）
# # =========================================================
# print("\n读取 slope 文件...")
# if not slope_file.exists():
#     raise FileNotFoundError(f"没有找到 slope 文件: {slope_file}")
# df_slope = pd.read_excel(slope_file, sheet_name=slope_sheet)
# if material_key_col not in df_slope.columns:
#     df_slope[material_key_col] = df_slope.apply(build_material_key, axis=1)
# if slope_col not in df_slope.columns:
#     raise ValueError(f"slope sheet 中没有找到列: {slope_col}")
# df_slope[material_key_col] = df_slope[material_key_col].astype(str).str.strip()
# df_slope[slope_col] = pd.to_numeric(df_slope[slope_col], errors="coerce")
# df_slope = df_slope[[material_key_col, slope_col]].drop_duplicates(subset=[material_key_col])
# print(f"有效斜率物质数: {df_slope[slope_col].notna().sum()}")
#
# # =========================================================
# # 4. 合并数据，获得最终长格式数据集（无 slope 和有 slope 两个版本）
# # =========================================================
# # 先合并基团和密度数据
# group_feature_df = df_groups[[material_key_col] + used_group_cols].drop_duplicates(subset=[material_key_col])
# df_long = df_data.merge(group_feature_df, on=material_key_col, how="inner")
# # 合并斜率
# df_long = df_long.merge(df_slope, on=material_key_col, how="left")
#
# # 清洗数据：只保留温度>0，密度>0，且有限值
# df_long = df_long[
#     (df_long[temp_col] > 0) &
#     (df_long[density_col] > 0) &
#     np.isfinite(df_long[temp_col]) &
#     np.isfinite(df_long[density_col])
# ].copy()
#
# # 有斜率模型需要额外的过滤（斜率必须有限）
# df_long_with_slope = df_long[np.isfinite(df_long[slope_col])].copy()
# df_long_no_slope = df_long.copy()  # 无斜率模型不需要斜率列，但保留所有样品
#
# # 特征构造
# feature_cols_no_slope = used_group_cols + [temp_col]
# feature_cols_with_slope = used_group_cols + [temp_col, slope_col]
#
# # 提取数组（用于交叉验证）
# def prepare_data(df, feature_cols):
#     X = df[feature_cols].values.astype(float)
#     y = df[density_col].values.astype(float)
#     materials = df[material_key_col].values
#     return X, y, materials
#
# X_no, y_no, mats_no = prepare_data(df_long_no_slope, feature_cols_no_slope)
# X_with, y_with, mats_with = prepare_data(df_long_with_slope, feature_cols_with_slope)
#
# # 获取所有物质（两个数据集可能物质稍有不同，取并集确保划分一致）
# all_materials = np.unique(np.concatenate([mats_no, mats_with]))
# # 创建物质到整数的映射（用于 GroupKFold）
# mat_to_int = {m: i for i, m in enumerate(all_materials)}
# material_indices_no = np.array([mat_to_int[m] for m in mats_no])
# material_indices_with = np.array([mat_to_int[m] for m in mats_with])
#
# print(f"\n无 slope 数据集样本数: {len(y_no)}, 物质数: {len(np.unique(mats_no))}")
# print(f"有 slope 数据集样本数: {len(y_with)}, 物质数: {len(np.unique(mats_with))}")
#
# # =========================================================
# # 5. 5 折交叉验证（按物质分组）
# # =========================================================
# gkf = GroupKFold(n_splits=n_outer_folds)
# metrics_no_slope = []
# metrics_with_slope = []
#
# for fold, (train_idx, test_idx) in enumerate(gkf.split(all_materials, groups=all_materials)):
#     # 注意：gkf.split 返回的是物质索引，需要根据物质 ID 筛选两个数据集的样本
#     train_materials = all_materials[train_idx]
#     test_materials = all_materials[test_idx]
#
#     # 无 slope 模型
#     train_mask_no = np.isin(mats_no, train_materials)
#     test_mask_no = np.isin(mats_no, test_materials)
#     X_train_no = X_no[train_mask_no]
#     y_train_no = y_no[train_mask_no]
#     X_test_no = X_no[test_mask_no]
#     y_test_no = y_no[test_mask_no]
#
#     # 训练模型
#     rf_no = RandomForestRegressor(**rf_params)
#     rf_no.fit(X_train_no, y_train_no)
#     y_pred_no = rf_no.predict(X_test_no)
#     m_no = evaluate_metrics(y_test_no, y_pred_no)
#
#     # 有 slope 模型
#     train_mask_with = np.isin(mats_with, train_materials)
#     test_mask_with = np.isin(mats_with, test_materials)
#     X_train_with = X_with[train_mask_with]
#     y_train_with = y_with[train_mask_with]
#     X_test_with = X_with[test_mask_with]
#     y_test_with = y_with[test_mask_with]
#
#     if len(y_train_with) == 0:
#         print(f"Fold {fold+1}: 有 slope 模型无训练样本，跳过")
#         m_with = {k: np.nan for k in ["R2","MSE","RMSE","MAE","ARD"]}
#     else:
#         rf_with = RandomForestRegressor(**rf_params)
#         rf_with.fit(X_train_with, y_train_with)
#         y_pred_with = rf_with.predict(X_test_with)
#         m_with = evaluate_metrics(y_test_with, y_pred_with)
#
#     m_no["fold"] = fold+1
#     m_with["fold"] = fold+1
#     metrics_no_slope.append(m_no)
#     metrics_with_slope.append(m_with)
#
#     print(f"\nFold {fold+1}:")
#     print(f"  No slope   - R2={m_no['R2']:.4f}, RMSE={m_no['RMSE']:.4f}, MAE={m_no['MAE']:.4f}, ARD={m_no['ARD']:.2f}%")
#     if not np.isnan(m_with['R2']):
#         print(f"  With slope - R2={m_with['R2']:.4f}, RMSE={m_with['RMSE']:.4f}, MAE={m_with['MAE']:.4f}, ARD={m_with['ARD']:.2f}%")
#     else:
#         print(f"  With slope - 无有效训练样本")
#
# # =========================================================
# # 6. 汇总统计（均值±标准差）
# # =========================================================
# df_no = pd.DataFrame(metrics_no_slope)
# df_with = pd.DataFrame(metrics_with_slope)
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
# summary_no = summarize(df_no, "RF (no slope)")
# summary_with = summarize(df_with, "RF (with slope)")
# summary_all = pd.concat([summary_no, summary_with], ignore_index=True)
#
# print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
# print(summary_all.to_string(index=False))
#
# # =========================================================
# # 7. 配对 t 检验（只对有值的折）
# # =========================================================
# t_test_results = []
# for metric in ["R2", "MSE", "RMSE", "MAE", "ARD"]:
#     vals_no = df_no[metric].dropna().values
#     vals_with = df_with[metric].dropna().values
#     if len(vals_no) == len(vals_with) and len(vals_no) > 1:
#         t_stat, p_val = ttest_rel(vals_no, vals_with)
#         if metric == "R2":
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
#             "Significant(p<0.05)": sig,
#             "Better model": better
#         })
#     else:
#         t_test_results.append({
#             "Metric": metric,
#             "Mean_no_slope": np.nan,
#             "Mean_with_slope": np.nan,
#             "p-value": np.nan,
#             "Significant(p<0.05)": False,
#             "Better model": "N/A"
#         })
#
# df_ttest = pd.DataFrame(t_test_results)
# print("\n========== Paired t-test ==========")
# print(df_ttest.to_string(index=False))
#
# # =========================================================
# # 8. 保存结果到 Excel
# # =========================================================
# with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
#     df_no.to_excel(writer, sheet_name="Fold_Metrics_No_Slope", index=False)
#     df_with.to_excel(writer, sheet_name="Fold_Metrics_With_Slope", index=False)
#     summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
#     df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)
#
#     params = pd.DataFrame([
#         {"param": "n_outer_folds", "value": n_outer_folds},
#         {"param": "random_state", "value": random_state},
#         {"param": "rf_params", "value": str(rf_params)},
#         {"param": "n_group_features", "value": len(used_group_cols)},
#         {"param": "total_samples_no_slope", "value": len(y_no)},
#         {"param": "total_samples_with_slope", "value": len(y_with)},
#         {"param": "n_materials", "value": len(all_materials)},
#     ])
#     params.to_excel(writer, sheet_name="Run_Info", index=False)
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

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupKFold
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from scipy.stats import ttest_rel

import warnings
warnings.filterwarnings("ignore")

# =========================================================
# 0. 全局设置
# =========================================================
pd.set_option("display.float_format", "{:.10f}".format)
np.set_printoptions(suppress=True, precision=10)

main_input_file = Path("dataset_density_selected_by_two_k_with_density_T_interpolation_8points.xlsx")
slope_file = Path("HistGB_submodels_predict_ref_density_Tb_and_slope.xlsx")

data_sheet = "Data_selected"
groups_sheet = "Groups_selected"
slope_sheet = "slope"
slope_col = "slope_pred_density_over_T"

output_file = Path("RF_density_5fold_CV_comparison.xlsx")

material_key_col = "material_key"
temp_col = "T_K"

density_col_candidates = [
    "property_value",
    "value",
    "Density_kg_m3",
    "density_kg_m3",
    "Density, kg/m3",
    "Mass density, kg/m3",
    "mass_density_kg_m3",
    "Mass_Density_kg_m3",
    "rho_kg_m3",
    "rho",
    "density",
    "Density",
]

n_group_features_to_use = 220
use_fixed_group_position = True
group_start_col_1based = 3
group_end_col_1based = 222

n_outer_folds = 5
random_state = 42

# 随机森林参数：保持原始代码设置
rf_params = {
    "n_estimators": 800,
    "max_depth": None,
    "min_samples_split": 2,
    "min_samples_leaf": 1,
    "max_features": 1.0,
    "bootstrap": True,
    "n_jobs": -1,
    "random_state": 42,
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
        "material_key",
        "inchikey",
        "InChIKey",
        "inchi_key",
        "pubchem_inchikey",
        "PubChem_InChIKey",
        "cas",
        "compound_name",
        "formula",
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


def make_prediction_df(fold, dataset_name, method, sub_df, y_true, y_pred):
    """
    保存测试集或完整数据集预测明细。
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    rel_err = safe_relative_error_percent(y_true, y_pred)

    df_out = sub_df.copy().reset_index(drop=True)

    df_out.insert(0, "fold", fold)
    df_out.insert(1, "dataset", dataset_name)
    df_out.insert(2, "Method", method)

    df_out["rho_true"] = y_true
    df_out["rho_pred"] = y_pred
    df_out["error"] = y_pred - y_true
    df_out["absolute_error"] = np.abs(y_pred - y_true)
    df_out["relative_error_percent"] = rel_err

    keep_cols_front = [
        "fold",
        "dataset",
        "Method",
        material_key_col,
        temp_col,
        density_col,
        "rho_true",
        "rho_pred",
        "error",
        "absolute_error",
        "relative_error_percent",
    ]

    if slope_col in df_out.columns:
        keep_cols_front.append(slope_col)

    other_cols = [c for c in df_out.columns if c not in keep_cols_front]

    df_out = df_out[keep_cols_front + other_cols]

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
# 2. 读取主数据并预处理
# =========================================================
print("读取主数据...")

if not main_input_file.exists():
    raise FileNotFoundError(f"没有找到主输入文件: {main_input_file}")

df_data = pd.read_excel(main_input_file, sheet_name=data_sheet)
df_groups = pd.read_excel(main_input_file, sheet_name=groups_sheet)

print(f"Data_selected 行数: {len(df_data)}, Groups_selected 物质数: {len(df_groups)}")

# 物质 ID 对齐
for df in [df_data, df_groups]:
    if material_key_col not in df.columns:
        df[material_key_col] = df.apply(build_material_key, axis=1)

    df[material_key_col] = df[material_key_col].astype(str).str.strip()

# 找到密度目标列和温度列
density_col = find_first_existing_col(
    df_data,
    density_col_candidates,
    "density",
    required=True,
)

if temp_col not in df_data.columns:
    raise ValueError(f"Data_selected 中没有找到温度列: {temp_col}")

df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
df_data[density_col] = pd.to_numeric(df_data[density_col], errors="coerce")

print(f"使用 density 目标列: {density_col}, 温度列: {temp_col}")

# 基团列处理
group_cols_220 = identify_group_columns(df_groups, n_group_features_to_use)

df_groups_numeric = (
    df_groups[group_cols_220]
    .apply(pd.to_numeric, errors="coerce")
    .fillna(0.0)
)

nonzero_mask = df_groups_numeric.abs().sum(axis=0) != 0

used_group_cols = df_groups_numeric.columns[nonzero_mask].tolist()
removed_zero_group_cols = df_groups_numeric.columns[~nonzero_mask].tolist()

df_groups_used = df_groups_numeric[used_group_cols].copy()

print(f"有效基团数: {len(used_group_cols)}")
print(f"删除全零基团数: {len(removed_zero_group_cols)}")


# =========================================================
# 3. 读取 slope 数据
# =========================================================
print("\n读取 slope 文件...")

if not slope_file.exists():
    raise FileNotFoundError(f"没有找到 slope 文件: {slope_file}")

df_slope = pd.read_excel(slope_file, sheet_name=slope_sheet)

if material_key_col not in df_slope.columns:
    df_slope[material_key_col] = df_slope.apply(build_material_key, axis=1)

if slope_col not in df_slope.columns:
    raise ValueError(f"slope sheet 中没有找到列: {slope_col}")

df_slope[material_key_col] = df_slope[material_key_col].astype(str).str.strip()
df_slope[slope_col] = pd.to_numeric(df_slope[slope_col], errors="coerce")

df_slope = (
    df_slope[[material_key_col, slope_col]]
    .drop_duplicates(subset=[material_key_col])
    .copy()
)

print(f"有效斜率物质数: {df_slope[slope_col].notna().sum()}")


# =========================================================
# 4. 合并数据，获得最终长格式数据集
# =========================================================
group_feature_df = (
    df_groups[[material_key_col] + used_group_cols]
    .drop_duplicates(subset=[material_key_col])
    .copy()
)

df_long = df_data.merge(
    group_feature_df,
    on=material_key_col,
    how="inner",
)

df_long = df_long.merge(
    df_slope,
    on=material_key_col,
    how="left",
)

# 清洗数据：只保留温度>0，密度>0，且有限值
df_long = df_long[
    (df_long[temp_col] > 0)
    & (df_long[density_col] > 0)
    & np.isfinite(df_long[temp_col])
    & np.isfinite(df_long[density_col])
].copy()

df_long = df_long.reset_index(drop=True)

# 有 slope 模型需要额外过滤 slope
df_long_no_slope = df_long.copy()
df_long_with_slope = df_long[np.isfinite(df_long[slope_col])].copy().reset_index(drop=True)

feature_cols_no_slope = used_group_cols + [temp_col]
feature_cols_with_slope = used_group_cols + [temp_col, slope_col]


def prepare_data(df, feature_cols):
    X = df[feature_cols].values.astype(float)
    y = df[density_col].values.astype(float)
    materials = df[material_key_col].values.astype(str)
    return X, y, materials


X_no, y_no, mats_no = prepare_data(df_long_no_slope, feature_cols_no_slope)
X_with, y_with, mats_with = prepare_data(df_long_with_slope, feature_cols_with_slope)

# 按物质划分时用两个数据集的并集，保持原实验设计
all_materials = np.unique(np.concatenate([mats_no, mats_with]))

print(f"\n无 slope 数据集样本数: {len(y_no)}, 物质数: {len(np.unique(mats_no))}")
print(f"有 slope 数据集样本数: {len(y_with)}, 物质数: {len(np.unique(mats_with))}")
print(f"物质并集数量: {len(all_materials)}")

if len(all_materials) < n_outer_folds:
    raise ValueError(
        f"物质数 {len(all_materials)} 小于 n_outer_folds={n_outer_folds}，无法做 5-fold。"
    )

# 完整数据集用于每个 fold 模型预测
X_all_no = X_no
y_all_no = y_no
df_all_no = df_long_no_slope.copy().reset_index(drop=True)

X_all_with = X_with
y_all_with = y_with
df_all_with = df_long_with_slope.copy().reset_index(drop=True)


# =========================================================
# 5. 5 折交叉验证（按物质分组）
# =========================================================
gkf = GroupKFold(n_splits=n_outer_folds)

metrics_no_slope = []
metrics_with_slope = []

fold_test_prediction_dfs = []
fold_all_data_prediction_dfs = []
fold_all_data_count_records = []

fold_info_records = []

feature_importance_no_records = []
feature_importance_with_records = []

for fold, (train_idx, test_idx) in enumerate(
    gkf.split(all_materials, groups=all_materials),
    start=1,
):
    print(f"\n========== Fold {fold}/{n_outer_folds} ==========")

    train_materials = all_materials[train_idx]
    test_materials = all_materials[test_idx]

    print("训练物质数:", len(train_materials))
    print("测试物质数:", len(test_materials))

    # -----------------------------------------------------
    # 方法1：无 slope RF
    # -----------------------------------------------------
    train_mask_no = np.isin(mats_no, train_materials)
    test_mask_no = np.isin(mats_no, test_materials)

    X_train_no = X_no[train_mask_no]
    y_train_no = y_no[train_mask_no]
    X_test_no = X_no[test_mask_no]
    y_test_no = y_no[test_mask_no]

    df_test_no = df_long_no_slope.loc[test_mask_no].copy().reset_index(drop=True)

    print("No slope 训练样本数:", len(y_train_no))
    print("No slope 测试样本数:", len(y_test_no))

    rf_no = RandomForestRegressor(**rf_params)
    rf_no.fit(X_train_no, y_train_no)

    y_pred_no_test = rf_no.predict(X_test_no)
    y_pred_no_all = rf_no.predict(X_all_no)

    m_no = evaluate_metrics(y_test_no, y_pred_no_test)
    m_no["fold"] = fold

    metrics_no_slope.append(m_no)

    # -----------------------------------------------------
    # 方法2：有 slope RF
    # -----------------------------------------------------
    train_mask_with = np.isin(mats_with, train_materials)
    test_mask_with = np.isin(mats_with, test_materials)

    X_train_with = X_with[train_mask_with]
    y_train_with = y_with[train_mask_with]
    X_test_with = X_with[test_mask_with]
    y_test_with = y_with[test_mask_with]

    df_test_with = df_long_with_slope.loc[test_mask_with].copy().reset_index(drop=True)

    print("With slope 训练样本数:", len(y_train_with))
    print("With slope 测试样本数:", len(y_test_with))

    if len(y_train_with) == 0:
        print(f"Fold {fold}: 有 slope 模型无训练样本，跳过")

        rf_with = None
        y_pred_with_test = np.full(len(y_test_with), np.nan, dtype=float)
        y_pred_with_all = np.full(len(y_all_with), np.nan, dtype=float)

        m_with = {
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

    else:
        rf_with = RandomForestRegressor(**rf_params)
        rf_with.fit(X_train_with, y_train_with)

        if len(y_test_with) > 0:
            y_pred_with_test = rf_with.predict(X_test_with)
        else:
            y_pred_with_test = np.array([], dtype=float)

        y_pred_with_all = rf_with.predict(X_all_with)

        m_with = evaluate_metrics(y_test_with, y_pred_with_test)

    m_with["fold"] = fold
    metrics_with_slope.append(m_with)

    print(f"\nFold {fold}:")
    print(
        "  No slope   - "
        f"R2={m_no['R2']:.4f}, "
        f"MSE={m_no['MSE']:.4f}, "
        f"RMSE={m_no['RMSE']:.4f}, "
        f"MAE={m_no['MAE']:.4f}, "
        f"ARD={m_no['ARD']:.2f}%"
    )

    if not np.isnan(m_with["R2"]):
        print(
            "  With slope - "
            f"R2={m_with['R2']:.4f}, "
            f"MSE={m_with['MSE']:.4f}, "
            f"RMSE={m_with['RMSE']:.4f}, "
            f"MAE={m_with['MAE']:.4f}, "
            f"ARD={m_with['ARD']:.2f}%"
        )
    else:
        print("  With slope - 无有效测试结果")

    # -----------------------------------------------------
    # 新增：每个 fold 模型预测完整数据集，统计完整数据集偏差数量
    # -----------------------------------------------------
    count_no_all = count_error_thresholds(y_all_no, y_pred_no_all)
    count_with_all = count_error_thresholds(y_all_with, y_pred_with_all)

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "RF_density_no_slope",
        **count_no_all,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "RF_density_with_slope",
        **count_with_all,
    })

    print("\nRF no_slope fold model predicts ALL available data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "RF_density_no_slope",
        **count_no_all,
    }]).to_string(index=False))

    print("\nRF with_slope fold model predicts ALL slope-valid data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "RF_density_with_slope",
        **count_with_all,
    }]).to_string(index=False))

    # -----------------------------------------------------
    # 保存测试集预测明细
    # -----------------------------------------------------
    df_test_pred_no = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="RF_density_no_slope",
        sub_df=df_test_no,
        y_true=y_test_no,
        y_pred=y_pred_no_test,
    )

    df_test_pred_with = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="RF_density_with_slope",
        sub_df=df_test_with,
        y_true=y_test_with,
        y_pred=y_pred_with_test,
    )

    fold_test_prediction_dfs.append(df_test_pred_no)
    fold_test_prediction_dfs.append(df_test_pred_with)

    # -----------------------------------------------------
    # 保存完整数据集预测明细
    # -----------------------------------------------------
    df_all_pred_no = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="RF_density_no_slope",
        sub_df=df_all_no,
        y_true=y_all_no,
        y_pred=y_pred_no_all,
    )

    df_all_pred_with = make_prediction_df(
        fold=fold,
        dataset_name="all_data_slope_valid",
        method="RF_density_with_slope",
        sub_df=df_all_with,
        y_true=y_all_with,
        y_pred=y_pred_with_all,
    )

    fold_all_data_prediction_dfs.append(df_all_pred_no)
    fold_all_data_prediction_dfs.append(df_all_pred_with)

    # -----------------------------------------------------
    # 保存特征重要性
    # -----------------------------------------------------
    if hasattr(rf_no, "feature_importances_"):
        for feature_name, importance in zip(feature_cols_no_slope, rf_no.feature_importances_):
            feature_importance_no_records.append({
                "fold": fold,
                "feature": feature_name,
                "importance": importance,
            })

    if rf_with is not None and hasattr(rf_with, "feature_importances_"):
        for feature_name, importance in zip(feature_cols_with_slope, rf_with.feature_importances_):
            feature_importance_with_records.append({
                "fold": fold,
                "feature": feature_name,
                "importance": importance,
            })

    fold_info_records.append({
        "fold": fold,
        "n_train_materials": len(train_materials),
        "n_test_materials": len(test_materials),
        "n_train_points_no_slope": len(y_train_no),
        "n_test_points_no_slope": len(y_test_no),
        "n_train_points_with_slope": len(y_train_with),
        "n_test_points_with_slope": len(y_test_with),
        "n_all_points_no_slope": len(y_all_no),
        "n_all_points_with_slope": len(y_all_with),
        "n_features_no_slope": X_train_no.shape[1],
        "n_features_with_slope": X_train_with.shape[1] if len(X_train_with) > 0 else len(feature_cols_with_slope),
        "with_slope_model_trained": rf_with is not None,
    })


# =========================================================
# 6. 汇总统计
# =========================================================
df_no = pd.DataFrame(metrics_no_slope)
df_with = pd.DataFrame(metrics_with_slope)

# fold 放第一列
df_no = df_no[["fold"] + [c for c in df_no.columns if c != "fold"]]
df_with = df_with[["fold"] + [c for c in df_with.columns if c != "fold"]]

summary_no = summarize(df_no, "RF (no slope)")
summary_with = summarize(df_with, "RF (with slope)")

summary_all = pd.concat(
    [summary_no, summary_with],
    ignore_index=True,
)

print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
print(summary_all.to_string(index=False))


# =========================================================
# 7. 配对 t 检验
# =========================================================
t_test_results = []

for metric in ["R2", "MSE", "RMSE", "MAE", "ARD"]:
    vals_no = df_no[metric].values.astype(float)
    vals_with = df_with[metric].values.astype(float)

    valid = np.isfinite(vals_no) & np.isfinite(vals_with)

    vals_no_valid = vals_no[valid]
    vals_with_valid = vals_with[valid]

    if len(vals_no_valid) > 1:
        t_stat, p_val = ttest_rel(vals_no_valid, vals_with_valid)

        if metric == "R2":
            better = "with_slope" if np.mean(vals_with_valid) > np.mean(vals_no_valid) else "no_slope"
        else:
            better = "with_slope" if np.mean(vals_with_valid) < np.mean(vals_no_valid) else "no_slope"

        t_test_results.append({
            "Metric": metric,
            "Mean_no_slope": f"{np.mean(vals_no_valid):.4f}",
            "Mean_with_slope": f"{np.mean(vals_with_valid):.4f}",
            "p-value": f"{p_val:.4e}",
            "Significant(p<0.05)": p_val < 0.05,
            "Better model": better,
            "n_valid_fold_pairs": len(vals_no_valid),
        })

    else:
        t_test_results.append({
            "Metric": metric,
            "Mean_no_slope": np.nan,
            "Mean_with_slope": np.nan,
            "p-value": np.nan,
            "Significant(p<0.05)": False,
            "Better model": "N/A",
            "n_valid_fold_pairs": len(vals_no_valid),
        })

df_ttest = pd.DataFrame(t_test_results)

print("\n========== Paired t-test ==========")
print(df_ttest.to_string(index=False))


# =========================================================
# 8. 完整数据集偏差数量统计汇总
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
        "n_all_data_points_for_this_method": sub["n_valid_for_relative_error"].iloc[0] if len(sub) > 0 else np.nan,
    })

df_final_average_summary = pd.DataFrame(final_average_records)

print("\n========== Fold all-data count summary ==========")
print(df_fold_all_data_count_summary.to_string(index=False))

print("\n========== Final average all-data count summary ==========")
print(df_final_average_summary.to_string(index=False))


# =========================================================
# 9. 整理输出表
# =========================================================
df_fold_test_predictions = pd.concat(fold_test_prediction_dfs, ignore_index=True)
df_fold_all_data_predictions = pd.concat(fold_all_data_prediction_dfs, ignore_index=True)

df_fold_info = pd.DataFrame(fold_info_records)
df_feature_importance_no = pd.DataFrame(feature_importance_no_records)
df_feature_importance_with = pd.DataFrame(feature_importance_with_records)

df_used_groups = pd.DataFrame({
    "used_group": used_group_cols,
    "occurrence_all_materials": (df_groups_numeric[used_group_cols] != 0).sum(axis=0).values,
    "total_count_all": df_groups_numeric[used_group_cols].sum(axis=0).values,
})

df_removed_zero_groups = pd.DataFrame({
    "removed_zero_group": removed_zero_group_cols,
})

df_slope_info = df_slope.copy()

df_run_info = pd.DataFrame([
    {"param": "main_input_file", "value": str(main_input_file)},
    {"param": "slope_file", "value": str(slope_file)},
    {"param": "data_sheet", "value": data_sheet},
    {"param": "groups_sheet", "value": groups_sheet},
    {"param": "slope_sheet", "value": slope_sheet},
    {"param": "density_col", "value": density_col},
    {"param": "temp_col", "value": temp_col},
    {"param": "slope_col", "value": slope_col},
    {"param": "n_outer_folds", "value": n_outer_folds},
    {"param": "random_state", "value": random_state},
    {"param": "rf_params", "value": str(rf_params)},
    {"param": "n_group_features", "value": len(used_group_cols)},
    {"param": "total_samples_no_slope", "value": len(y_no)},
    {"param": "total_samples_with_slope", "value": len(y_with)},
    {"param": "n_materials_union", "value": len(all_materials)},
    {"param": "n_materials_no_slope", "value": len(np.unique(mats_no))},
    {"param": "n_materials_with_slope", "value": len(np.unique(mats_with))},
    {
        "param": "relative_error_definition",
        "value": "abs((y_pred - y_true) / y_true) * 100; abs(y_true)<=1e-12 -> NaN",
    },
    {
        "param": "full_data_count_rule",
        "value": "Each fold model predicts the whole available dataset for that method; count rel_err <1%, <5%, <10%; then average counts over 5 folds.",
    },
])

df_model_structure = pd.DataFrame([
    {
        "项目": "预测对象",
        "内容": f"液体密度 rho，目标列 {density_col}",
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
        "内容": f"{n_outer_folds}-fold GroupKFold，按 material_key 物质划分；使用 no_slope 和 with_slope 物质并集构造 fold",
    },
    {
        "项目": "方法1",
        "内容": "RF_density_no_slope：RandomForestRegressor 直接预测 rho，输入 [Nk, T]",
    },
    {
        "项目": "方法2",
        "内容": "RF_density_with_slope：RandomForestRegressor 直接预测 rho，输入 [Nk, T, slope_pred_density_over_T]",
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
        "内容": "slope_pred_density_over_T，用作方法2额外输入特征",
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
        "内容": "直接读取 slope_pred_density_over_T，作为方法2额外输入特征；不再乘以 T",
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
        "内容": f"[{len(used_group_cols)} 个 Nk, T]，总维度 {len(used_group_cols) + 1}",
    },
    {
        "项目": "方法2最终输入",
        "内容": f"[{len(used_group_cols)} 个 Nk, T, slope_pred_density_over_T]，总维度 {len(used_group_cols) + 2}",
    },
    {
        "项目": "模型2样本口径",
        "内容": "with_slope 模型仅使用 slope 有效样本；完整数据预测统计也基于 slope 有效样本",
    },
    {
        "项目": "偏差数量统计口径",
        "内容": "每个 fold 模型预测对应方法的完整可用数据集，统计 rho 相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 取平均",
    },
])


# =========================================================
# 10. 保存结果到 Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    # 原有输出
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

print(f"\n结果已保存至: {output_file}")


# =========================================================
# 11. 最终方便复制输出
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


no_1, no_5, no_10 = get_final_counts("RF_density_no_slope")
with_1, with_5, with_10 = get_final_counts("RF_density_with_slope")

print("\n方法1 全数据预测偏差 1%，5%，10%分别为：")
print(no_1)
print(no_5)
print(no_10)

print("\n方法2 全数据预测偏差 1%，5%，10%分别为：")
print(with_1)
print(with_5)
print(with_10)


# =========================================================
# 12. 代码结构打印
# =========================================================
print("\n========== 当前代码结构简要汇总 ==========")
print(f"预测对象：液体密度 rho / {density_col}")
print(f"主数据文件：{main_input_file}")
print(f"slope 文件：{slope_file}")
print(f"sheet 名称：{data_sheet}, {groups_sheet}, {slope_sheet}")
print(f"交叉验证：{n_outer_folds}-fold GroupKFold，按 material_key 物质划分")
print("方法1：RF_density_no_slope，RandomForestRegressor，输入 [Nk, T]")
print("方法2：RF_density_with_slope，RandomForestRegressor，输入 [Nk, T, slope_pred_density_over_T]")
print("子模型：当前代码不训练子模型，读取外部 HistGB 预测的 slope_pred_density_over_T")
print(f"子模型预测列：{slope_col}")
print("子模型参数：当前代码无法从 slope 文件恢复，仅保存 slope 预测值")
print("slope 构造：直接读取 slope_pred_density_over_T，作为方法2额外输入特征；没有乘以 T")
print("baseline 构造：无")
print("residual 模型：无")
print(f"最终模型：RandomForestRegressor，参数：{rf_params}")
print("方法1最终输入：[Nk, T]")
print("方法2最终输入：[Nk, T, slope_pred_density_over_T]")
print("模型2样本口径：with_slope 模型仅使用 slope 有效样本；完整数据预测统计也基于 slope 有效样本")
print("偏差统计口径：每个 fold 模型预测对应方法的完整可用数据集，统计 <1%、<5%、<10% 点数，再对 5 个 fold 取平均")