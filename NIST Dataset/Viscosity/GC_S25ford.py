# import pandas as pd
# import numpy as np
# from pathlib import Path
# from sklearn.linear_model import Ridge
# from sklearn.model_selection import GroupKFold
# from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
# from scipy.stats import ttest_rel
# import warnings
# warnings.filterwarnings("ignore")
#
# pd.set_option("display.float_format", "{:.10f}".format)
# np.set_printoptions(suppress=True, precision=10)
#
# # =========================================================
# # 0. 全局配置
# # =========================================================
# input_file = Path("dataset_viscosity_selected_by_two_k_with_lnVisc_invT_interpolation_8points.xlsx")
# data_sheet = "Data_selected"
# groups_sheet = "Groups_selected"
#
# material_key_col = "material_key"
# temp_col = "T_K"
#
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
# random_state = 43
#
# # 常温（开尔文）
# ANCHOR_TEMP = 298.15
# ANCHOR_TEMP_TOLERANCE = 0.1   # 允许的绝对误差，用于匹配实测点
#
# # 统一使用 Ridge 回归
# ridge_alpha = 1.0
#
# # =========================================================
# # 1. 工具函数
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
#             if col == "material_key": return str(row[col]).strip()
#             return f"{col}:{str(row[col]).strip()}"
#     return "unknown_material"
#
# def find_first_existing_col(df, candidates, col_type, required=True):
#     for col in candidates:
#         if col in df.columns: return col
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
#     raise ValueError("请设置 use_fixed_group_position=True")
#
# def safe_exp(x):
#     return np.exp(np.clip(x, -700, 700))
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
#         return {"R2": np.nan, "RMSE": np.nan, "MAE": np.nan, "ARD": np.nan}
#     r2 = r2_score(y_true, y_pred)
#     rmse = np.sqrt(mean_squared_error(y_true, y_pred))
#     mae = mean_absolute_error(y_true, y_pred)
#     ard = average_relative_deviation(y_true, y_pred)
#     return {"R2": r2, "RMSE": rmse, "MAE": mae, "ARD": ard}
#
# def interpolate_lnvisc_at_target_T(group, target_T, temp_col, lnvisc_col):
#     """
#     在 ln(viscosity) vs 1/T 空间线性插值得到目标温度下的 ln(viscosity)
#     """
#     g = group[[temp_col, lnvisc_col]].copy()
#     g[temp_col] = pd.to_numeric(g[temp_col], errors="coerce")
#     g[lnvisc_col] = pd.to_numeric(g[lnvisc_col], errors="coerce")
#     g = g.dropna(subset=[temp_col, lnvisc_col])
#     g = g[np.isfinite(g[temp_col]) & np.isfinite(g[lnvisc_col])]
#     if len(g) < 2:
#         return np.nan
#     # 同一温度可能有多点，取平均
#     g = g.groupby(temp_col, as_index=False)[lnvisc_col].mean().sort_values(temp_col)
#     if len(g) < 2:
#         return np.nan
#     T_vals = g[temp_col].values
#     lnvisc_vals = g[lnvisc_col].values
#     # 如果目标温度恰好有实测点，直接返回
#     for T, lnv in zip(T_vals, lnvisc_vals):
#         if abs(T - target_T) <= ANCHOR_TEMP_TOLERANCE:
#             return lnv
#     # 否则进行插值（在 1/T 空间）
#     x = 1.0 / T_vals
#     y = lnvisc_vals
#     x_target = 1.0 / target_T
#     # 插值要求 x 单调递增
#     order = np.argsort(x)
#     x_sorted = x[order]
#     y_sorted = y[order]
#     if x_target < x_sorted[0] or x_target > x_sorted[-1]:
#         return np.nan   # 超出范围，不进行外推
#     return np.interp(x_target, x_sorted, y_sorted)
#
# # =========================================================
# # 2. 读取数据
# # =========================================================
# df_data = pd.read_excel(input_file, sheet_name=data_sheet)
# df_groups_raw = pd.read_excel(input_file, sheet_name=groups_sheet)
#
# for df in [df_data, df_groups_raw]:
#     if material_key_col not in df.columns:
#         df[material_key_col] = df.apply(build_material_key, axis=1)
#     df[material_key_col] = df[material_key_col].astype(str).str.strip()
#
# # 目标列
# target_col = find_first_existing_col(df_data, lnvisc_col_candidates, "lnViscosity", required=True)
# viscosity_col = find_first_existing_col(df_data, viscosity_col_candidates, "原始粘度", required=False)
# if temp_col not in df_data.columns:
#     raise ValueError(f"Data_selected 中没有找到温度列: {temp_col}")
# df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
# df_data[target_col] = pd.to_numeric(df_data[target_col], errors="coerce")
#
# # 基团列处理
# group_cols_220 = identify_group_columns(df_groups_raw, n_group_features_to_use)
# df_groups_numeric = df_groups_raw[group_cols_220].apply(pd.to_numeric, errors="coerce").fillna(0.0)
# nonzero_mask = df_groups_numeric.abs().sum(axis=0) != 0
# used_group_cols = df_groups_numeric.columns[nonzero_mask].tolist()
# df_groups_used = df_groups_numeric[used_group_cols].copy()
# print(f"有效基团数: {len(used_group_cols)}")
#
# # =========================================================
# # 3. 为每个物质计算常温锚点 lnη_anchor 和 1/T_anchor
# # =========================================================
# data_grouped = {key: group for key, group in df_data.groupby(material_key_col, sort=False)}
# anchor_dict = {}   # 存储每个物质的 (lnVisc_anchor, invT_anchor)
#
# for mat in data_grouped.keys():
#     group = data_grouped[mat]
#     lnv_anchor = interpolate_lnvisc_at_target_T(group, ANCHOR_TEMP, temp_col, target_col)
#     if np.isfinite(lnv_anchor):
#         anchor_dict[mat] = (lnv_anchor, 1.0 / ANCHOR_TEMP)
#     else:
#         anchor_dict[mat] = (np.nan, np.nan)
#
# # 将锚点信息合并到 df_long
# df_long = df_data.merge(df_groups_raw[[material_key_col] + used_group_cols], on=material_key_col, how="inner")
# df_long["anchor_lnVisc"] = df_long[material_key_col].map(lambda x: anchor_dict.get(x, (np.nan, np.nan))[0])
# df_long["invT_anchor"] = df_long[material_key_col].map(lambda x: anchor_dict.get(x, (np.nan, np.nan))[1])
# df_long["T_anchor"] = 1.0 / df_long["invT_anchor"]
#
# # 过滤掉锚点无效的物质
# df_long = df_long.dropna(subset=[target_col, temp_col, "anchor_lnVisc", "invT_anchor"])
# df_long = df_long[df_long[temp_col] > 0].copy()
# df_long["InvT"] = 1.0 / df_long[temp_col]
# df_long = df_long.reset_index(drop=True)
#
# # 提取数组
# X_groups = df_long[used_group_cols].values.astype(float)
# InvT = df_long["InvT"].values.astype(float)
# lnVisc_true = df_long[target_col].values.astype(float)
# lnVisc_anchor = df_long["anchor_lnVisc"].values.astype(float)
# invT_anchor = df_long["invT_anchor"].values.astype(float)
# material_keys = df_long[material_key_col].values
#
# unique_materials = np.unique(material_keys)
# print(f"总温度点数: {len(lnVisc_true)}, 总物质数: {len(unique_materials)}")
#
# # =========================================================
# # 4. 准备物理基线的物质真实参数 (A, B)
# # =========================================================
# material_to_AB = {}
# for mat in unique_materials:
#     mask = material_keys == mat
#     T_mat = 1.0 / InvT[mask]   # 温度 (K)
#     lnVisc_mat = lnVisc_true[mask]
#     if len(T_mat) >= 2:
#         B, A = np.polyfit(1.0 / T_mat, lnVisc_mat, 1)  # polyfit返回 [斜率, 截距] = [B, A]
#         material_to_AB[mat] = (A, B)
#     else:
#         material_to_AB[mat] = (np.nan, np.nan)
#
# # =========================================================
# # 5. 5 折交叉验证（两个模型均使用 Ridge 回归）
# # =========================================================
# gkf = GroupKFold(n_splits=n_outer_folds)
# metrics_anchor = []   # 锚点线性基线（Ridge 无截距）
# metrics_physical = [] # 物理基线（Ridge 预测 A、B，带截距）
#
# for fold, (train_mat_idx, test_mat_idx) in enumerate(gkf.split(unique_materials, groups=unique_materials)):
#     train_mats = unique_materials[train_mat_idx]
#     test_mats = unique_materials[test_mat_idx]
#
#     train_mask = np.isin(material_keys, train_mats)
#     test_mask = np.isin(material_keys, test_mats)
#
#     # ---------- 锚点线性基线（常温锚点，Ridge 无截距） ----------
#     delta_invT_train = InvT[train_mask] - invT_anchor[train_mask]
#     X_base_train = X_groups[train_mask] * delta_invT_train.reshape(-1,1)
#     y_base_train = lnVisc_true[train_mask] - lnVisc_anchor[train_mask]
#     valid_base = np.isfinite(X_base_train).all(axis=1) & np.isfinite(y_base_train)
#     if valid_base.sum() == 0:
#         y_pred_anchor = np.full(lnVisc_true[test_mask].shape, np.nan)
#     else:
#         base_model = Ridge(alpha=ridge_alpha, fit_intercept=False)
#         base_model.fit(X_base_train[valid_base], y_base_train[valid_base])
#         delta_invT_test = InvT[test_mask] - invT_anchor[test_mask]
#         X_base_test = X_groups[test_mask] * delta_invT_test.reshape(-1,1)
#         valid_test = np.isfinite(X_base_test).all(axis=1)
#         baseline_delta = np.full(len(lnVisc_true[test_mask]), np.nan)
#         baseline_delta[valid_test] = base_model.predict(X_base_test[valid_test])
#         y_pred_anchor = lnVisc_anchor[test_mask] + baseline_delta
#
#     # ---------- 物理基线（Ridge 预测 A、B，带截距） ----------
#     train_AB = []
#     train_X = []
#     for mat in train_mats:
#         if mat in material_to_AB and not np.isnan(material_to_AB[mat][0]):
#             train_AB.append(material_to_AB[mat])
#             idx = np.where(material_keys == mat)[0][0]
#             train_X.append(X_groups[idx])
#     if len(train_AB) == 0:
#         y_pred_physical = np.full(lnVisc_true[test_mask].shape, np.nan)
#     else:
#         train_X = np.array(train_X)
#         train_A = np.array([ab[0] for ab in train_AB])
#         train_B = np.array([ab[1] for ab in train_AB])
#
#         # 使用 Ridge 预测 A 和 B（带截距）
#         model_A = Ridge(alpha=ridge_alpha, fit_intercept=True)
#         model_B = Ridge(alpha=ridge_alpha, fit_intercept=True)
#         model_A.fit(train_X, train_A)
#         model_B.fit(train_X, train_B)
#
#         # 预测测试集物质的 A、B
#         test_X = []
#         for mat in test_mats:
#             idx = np.where(material_keys == mat)[0][0]
#             test_X.append(X_groups[idx])
#         test_X = np.array(test_X)
#         A_pred = model_A.predict(test_X)
#         B_pred = model_B.predict(test_X)
#
#         # 计算测试集每个温度点的预测 lnVisc
#         y_pred_physical = np.zeros(len(lnVisc_true[test_mask])) * np.nan
#         for i, mat in enumerate(test_mats):
#             sub_mask = material_keys[test_mask] == mat
#             T_sub = 1.0 / InvT[test_mask][sub_mask]  # 温度
#             pred_vals = A_pred[i] + B_pred[i] / T_sub
#             y_pred_physical[sub_mask] = pred_vals
#
#     # 评估
#     y_true_test = lnVisc_true[test_mask]
#     met_anchor = evaluate_metrics(y_true_test, y_pred_anchor)
#     met_physical = evaluate_metrics(y_true_test, y_pred_physical)
#     met_anchor["fold"] = fold+1
#     met_physical["fold"] = fold+1
#     metrics_anchor.append(met_anchor)
#     metrics_physical.append(met_physical)
#
#     print(f"\nFold {fold+1}:")
#     print(f"  锚点线性基线(常温) - R2={met_anchor['R2']:.4f}, RMSE={met_anchor['RMSE']:.4f}, MAE={met_anchor['MAE']:.4f}, ARD={met_anchor['ARD']:.2f}%")
#     print(f"  物理基线(Ridge)    - R2={met_physical['R2']:.4f}, RMSE={met_physical['RMSE']:.4f}, MAE={met_physical['MAE']:.4f}, ARD={met_physical['ARD']:.2f}%")
#
# # =========================================================
# # 6. 汇总统计与配对 t 检验
# # =========================================================
# df_anchor = pd.DataFrame(metrics_anchor)
# df_physical = pd.DataFrame(metrics_physical)
#
# def summarize(df, name):
#     rows = []
#     for metric in ["R2", "RMSE", "MAE", "ARD"]:
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
# summary_anchor = summarize(df_anchor, "Anchor linear baseline (298K Ridge)")
# summary_physical = summarize(df_physical, "Physical baseline (Ridge)")
# summary_all = pd.concat([summary_anchor, summary_physical], ignore_index=True)
#
# print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
# print(summary_all.to_string(index=False))
#
# # 配对 t 检验
# t_test_results = []
# for metric in ["R2", "RMSE", "MAE", "ARD"]:
#     vals_anc = df_anchor[metric].dropna().values
#     vals_phy = df_physical[metric].dropna().values
#     if len(vals_anc) == len(vals_phy) and len(vals_anc) > 1:
#         t_stat, p_val = ttest_rel(vals_anc, vals_phy)
#         if metric == "R2":
#             better = "anchor" if np.mean(vals_anc) > np.mean(vals_phy) else "physical"
#             sig = p_val < 0.05
#         else:
#             better = "anchor" if np.mean(vals_anc) < np.mean(vals_phy) else "physical"
#             sig = p_val < 0.05
#         t_test_results.append({
#             "Metric": metric,
#             "Mean_anchor": f"{np.mean(vals_anc):.4f}",
#             "Mean_physical": f"{np.mean(vals_phy):.4f}",
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
# output_file = "viscosity_anchor_298K_baseline_ridge_unified.xlsx"
# with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
#     df_anchor.to_excel(writer, sheet_name="Fold_Metrics_Anchor_Ridge", index=False)
#     df_physical.to_excel(writer, sheet_name="Fold_Metrics_Physical_Ridge", index=False)
#     summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
#     df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)
#     pd.DataFrame([
#         {"param": "n_outer_folds", "value": n_outer_folds},
#         {"param": "random_state", "value": random_state},
#         {"param": "anchor_temp_K", "value": ANCHOR_TEMP},
#         {"param": "ridge_alpha", "value": ridge_alpha},
#     ]).to_excel(writer, sheet_name="Run_Info", index=False)
#
# print(f"\n结果已保存至: {output_file}")



import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupKFold
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from scipy.stats import ttest_rel

import warnings
warnings.filterwarnings("ignore")

pd.set_option("display.float_format", "{:.10f}".format)
np.set_printoptions(suppress=True, precision=10)


# =========================================================
# 0. 全局配置
# =========================================================
input_file = Path("dataset_viscosity_selected_by_two_k_with_lnVisc_invT_interpolation_8points.xlsx")
data_sheet = "Data_selected"
groups_sheet = "Groups_selected"

output_file = Path("viscosity_anchor_298K_baseline_ridge_unified.xlsx")

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
random_state = 43

# 常温锚点
ANCHOR_TEMP = 298.15
ANCHOR_TEMP_TOLERANCE = 0.1

# 统一 Ridge 回归
ridge_alpha = 1.0


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


def safe_exp(x):
    return np.exp(np.clip(np.asarray(x, dtype=float), -700, 700))


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

    注意：严格使用 <，不是 <=。
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
    原始 lnVisc 空间评价指标。
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = np.isfinite(y_true) & np.isfinite(y_pred)

    y_true = y_true[mask]
    y_pred = y_pred[mask]

    if len(y_true) == 0:
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

    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred) if len(y_true) > 1 else np.nan

    rel_err = safe_relative_error_percent(y_true, y_pred)
    n_valid = int(np.sum(np.isfinite(rel_err)))

    if n_valid > 0:
        c1 = float(np.nansum(rel_err < 1.0))
        c5 = float(np.nansum(rel_err < 5.0))
        c10 = float(np.nansum(rel_err < 10.0))

        r1 = c1 / n_valid * 100.0
        r5 = c5 / n_valid * 100.0
        r10 = c10 / n_valid * 100.0

        ard = float(np.nanmean(rel_err))
        max_rel = float(np.nanmax(rel_err))
    else:
        c1 = c5 = c10 = 0.0
        r1 = r5 = r10 = np.nan
        ard = np.nan
        max_rel = np.nan

    return {
        "n_points": len(y_true),
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


def evaluate_metrics_eta_from_lnvisc(y_true_lnvisc, y_pred_lnvisc):
    """
    η = exp(lnη) 空间评价指标。
    """
    eta_true = safe_exp(y_true_lnvisc)
    eta_pred = safe_exp(y_pred_lnvisc)

    return evaluate_metrics(eta_true, eta_pred)


def interpolate_lnvisc_at_target_T(group, target_T, temp_col, lnvisc_col):
    """
    在 ln(viscosity) vs 1/T 空间线性插值得到目标温度下的 ln(viscosity)。
    """
    g = group[[temp_col, lnvisc_col]].copy()
    g[temp_col] = pd.to_numeric(g[temp_col], errors="coerce")
    g[lnvisc_col] = pd.to_numeric(g[lnvisc_col], errors="coerce")

    g = g.dropna(subset=[temp_col, lnvisc_col])
    g = g[np.isfinite(g[temp_col]) & np.isfinite(g[lnvisc_col])]

    if len(g) < 2:
        return np.nan

    # 同一温度可能有多点，取平均
    g = g.groupby(temp_col, as_index=False)[lnvisc_col].mean().sort_values(temp_col)

    if len(g) < 2:
        return np.nan

    T_vals = g[temp_col].values
    lnvisc_vals = g[lnvisc_col].values

    # 如果目标温度恰好有实测点，直接返回
    for T_val, lnv in zip(T_vals, lnvisc_vals):
        if abs(T_val - target_T) <= ANCHOR_TEMP_TOLERANCE:
            return lnv

    # 否则在 1/T 空间插值，不外推
    x = 1.0 / T_vals
    y = lnvisc_vals
    x_target = 1.0 / target_T

    order = np.argsort(x)
    x_sorted = x[order]
    y_sorted = y[order]

    if x_target < x_sorted[0] or x_target > x_sorted[-1]:
        return np.nan

    return np.interp(x_target, x_sorted, y_sorted)


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


def predict_anchor_baseline(indices, base_model):
    """
    锚点线性基线：
        lnη_pred = lnη_anchor + Ridge(Nk * (1/T - 1/T_anchor))
    """
    indices = np.asarray(indices, dtype=int)

    delta_invT = InvT[indices] - invT_anchor[indices]
    X_base = X_groups[indices] * delta_invT.reshape(-1, 1)

    baseline_delta = np.full(len(indices), np.nan, dtype=float)

    valid = np.isfinite(X_base).all(axis=1)

    if base_model is not None and valid.sum() > 0:
        baseline_delta[valid] = base_model.predict(X_base[valid])

    y_pred = lnVisc_anchor[indices] + baseline_delta

    return y_pred, baseline_delta


def train_anchor_model(train_indices):
    train_indices = np.asarray(train_indices, dtype=int)

    delta_invT_train = InvT[train_indices] - invT_anchor[train_indices]
    X_base_train = X_groups[train_indices] * delta_invT_train.reshape(-1, 1)
    y_base_train = lnVisc_true[train_indices] - lnVisc_anchor[train_indices]

    valid_base = (
        np.isfinite(X_base_train).all(axis=1)
        & np.isfinite(y_base_train)
    )

    if valid_base.sum() == 0:
        return None

    base_model = Ridge(alpha=ridge_alpha, fit_intercept=False)
    base_model.fit(X_base_train[valid_base], y_base_train[valid_base])

    return base_model


def train_physical_AB_models(train_mats):
    """
    物理基线：
        单物质 lnη = A + B/T = A + B * InvT；
        先对每个训练物质拟合真实 A、B；
        再用 Ridge(Nk) 分别预测 A 和 B。
    """
    train_AB = []
    train_X = []
    train_materials_used = []

    for mat in train_mats:
        if mat in material_to_AB:
            A_true, B_true = material_to_AB[mat]

            if np.isfinite(A_true) and np.isfinite(B_true):
                train_AB.append((A_true, B_true))

                idx = np.where(material_keys == mat)[0][0]
                train_X.append(X_groups[idx])
                train_materials_used.append(mat)

    if len(train_AB) == 0:
        return None, None, [], np.nan, np.nan

    train_X = np.array(train_X, dtype=float)
    train_A = np.array([ab[0] for ab in train_AB], dtype=float)
    train_B = np.array([ab[1] for ab in train_AB], dtype=float)

    model_A = Ridge(alpha=ridge_alpha, fit_intercept=True)
    model_B = Ridge(alpha=ridge_alpha, fit_intercept=True)

    model_A.fit(train_X, train_A)
    model_B.fit(train_X, train_B)

    return model_A, model_B, train_materials_used, model_A.intercept_, model_B.intercept_


def predict_physical_baseline(indices, model_A, model_B):
    """
    对任意样本 indices 预测：
        lnη_pred = A_pred + B_pred * InvT
    """
    indices = np.asarray(indices, dtype=int)

    y_pred = np.full(len(indices), np.nan, dtype=float)
    A_pred_rows = np.full(len(indices), np.nan, dtype=float)
    B_pred_rows = np.full(len(indices), np.nan, dtype=float)

    if model_A is None or model_B is None or len(indices) == 0:
        return y_pred, A_pred_rows, B_pred_rows

    mats = material_keys[indices]
    unique_mats_for_pred = np.unique(mats)

    mat_to_AB_pred = {}

    pred_X = []
    mat_order = []

    for mat in unique_mats_for_pred:
        idx = np.where(material_keys == mat)[0][0]
        pred_X.append(X_groups[idx])
        mat_order.append(mat)

    pred_X = np.array(pred_X, dtype=float)

    A_pred = model_A.predict(pred_X)
    B_pred = model_B.predict(pred_X)

    for mat, a, b in zip(mat_order, A_pred, B_pred):
        mat_to_AB_pred[mat] = (a, b)

    for i, sample_idx in enumerate(indices):
        mat = material_keys[sample_idx]

        if mat in mat_to_AB_pred:
            a, b = mat_to_AB_pred[mat]
            A_pred_rows[i] = a
            B_pred_rows[i] = b
            y_pred[i] = a + b * InvT[sample_idx]

    return y_pred, A_pred_rows, B_pred_rows


def make_prediction_df(
    fold,
    dataset_name,
    method,
    sample_indices,
    y_true_lnvisc,
    y_pred_lnvisc,
    baseline_delta=None,
    A_pred=None,
    B_pred=None,
):
    sample_indices = np.asarray(sample_indices, dtype=int)
    y_true_lnvisc = np.asarray(y_true_lnvisc, dtype=float)
    y_pred_lnvisc = np.asarray(y_pred_lnvisc, dtype=float)

    eta_true = safe_exp(y_true_lnvisc)
    eta_pred = safe_exp(y_pred_lnvisc)

    df_out = pd.DataFrame({
        "fold": fold,
        "dataset": dataset_name,
        "Method": method,
        "sample_index": sample_indices,
        material_key_col: material_keys[sample_indices],
        "T_K": 1.0 / InvT[sample_indices],
        "InvT": InvT[sample_indices],
        "lnVisc_true": y_true_lnvisc,
        "lnVisc_pred": y_pred_lnvisc,
        "lnVisc_error": y_pred_lnvisc - y_true_lnvisc,
        "lnVisc_absolute_error": np.abs(y_pred_lnvisc - y_true_lnvisc),
        "lnVisc_relative_error_percent": safe_relative_error_percent(y_true_lnvisc, y_pred_lnvisc),
        "eta_true": eta_true,
        "eta_pred": eta_pred,
        "eta_error": eta_pred - eta_true,
        "eta_absolute_error": np.abs(eta_pred - eta_true),
        "eta_relative_error_percent": safe_relative_error_percent(eta_true, eta_pred),
        "anchor_lnVisc": lnVisc_anchor[sample_indices],
        "anchor_eta": safe_exp(lnVisc_anchor[sample_indices]),
        "T_anchor": 1.0 / invT_anchor[sample_indices],
        "invT_anchor": invT_anchor[sample_indices],
        "delta_invT": InvT[sample_indices] - invT_anchor[sample_indices],
    })

    if viscosity_col is not None and viscosity_col in df_long.columns:
        df_out["viscosity_raw"] = df_long[viscosity_col].values[sample_indices]

    if baseline_delta is not None:
        df_out["baseline_delta_pred"] = baseline_delta

    if A_pred is not None:
        df_out["A_pred"] = A_pred

    if B_pred is not None:
        df_out["B_pred"] = B_pred

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
if not input_file.exists():
    raise FileNotFoundError(f"没有找到输入文件: {input_file}")

df_data = pd.read_excel(input_file, sheet_name=data_sheet)
df_groups_raw = pd.read_excel(input_file, sheet_name=groups_sheet)

print("Data_selected 行数:", len(df_data))
print("Groups_selected 行数:", len(df_groups_raw))

for df in [df_data, df_groups_raw]:
    if material_key_col not in df.columns:
        df[material_key_col] = df.apply(build_material_key, axis=1)

    df[material_key_col] = df[material_key_col].astype(str).str.strip()

# 目标列
target_col = find_first_existing_col(
    df_data,
    lnvisc_col_candidates,
    "lnViscosity",
    required=True,
)

viscosity_col = find_first_existing_col(
    df_data,
    viscosity_col_candidates,
    "原始粘度",
    required=False,
)

if temp_col not in df_data.columns:
    raise ValueError(f"Data_selected 中没有找到温度列: {temp_col}")

df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
df_data[target_col] = pd.to_numeric(df_data[target_col], errors="coerce")

print("lnVisc 目标列:", target_col)
print("原始粘度列:", viscosity_col if viscosity_col is not None else "未找到")


# =========================================================
# 3. 基团列处理
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

print(f"有效基团数: {len(used_group_cols)}")
print(f"删除全零基团数: {len(removed_zero_group_cols)}")


# =========================================================
# 4. 为每个物质计算 298K 常温锚点 lnη_anchor 和 1/T_anchor
# =========================================================
data_grouped = {
    key: group
    for key, group in df_data.groupby(material_key_col, sort=False)
}

anchor_dict = {}

for mat in data_grouped.keys():
    group = data_grouped[mat]
    lnv_anchor = interpolate_lnvisc_at_target_T(
        group,
        ANCHOR_TEMP,
        temp_col,
        target_col,
    )

    if np.isfinite(lnv_anchor):
        anchor_dict[mat] = (lnv_anchor, 1.0 / ANCHOR_TEMP)
    else:
        anchor_dict[mat] = (np.nan, np.nan)

df_anchor_info = pd.DataFrame([
    {
        material_key_col: mat,
        "anchor_lnVisc": vals[0],
        "invT_anchor": vals[1],
        "T_anchor": 1.0 / vals[1] if np.isfinite(vals[1]) and vals[1] != 0 else np.nan,
        "anchor_eta": safe_exp(vals[0]) if np.isfinite(vals[0]) else np.nan,
        "anchor_valid": np.isfinite(vals[0]) and np.isfinite(vals[1]),
    }
    for mat, vals in anchor_dict.items()
])

print("锚点有效物质数:", int(df_anchor_info["anchor_valid"].sum()))


# =========================================================
# 5. 合并长表
# =========================================================
df_long = df_data.merge(
    df_groups_raw[[material_key_col] + used_group_cols],
    on=material_key_col,
    how="inner",
)

df_long["anchor_lnVisc"] = df_long[material_key_col].map(
    lambda x: anchor_dict.get(x, (np.nan, np.nan))[0]
)

df_long["invT_anchor"] = df_long[material_key_col].map(
    lambda x: anchor_dict.get(x, (np.nan, np.nan))[1]
)

df_long["T_anchor"] = 1.0 / df_long["invT_anchor"]

df_long = df_long.dropna(
    subset=[
        target_col,
        temp_col,
        "anchor_lnVisc",
        "invT_anchor",
    ]
    + used_group_cols
)

df_long = df_long[df_long[temp_col] > 0].copy()
df_long["InvT"] = 1.0 / df_long[temp_col]
df_long = df_long.reset_index(drop=True)

# 提取数组
X_groups = df_long[used_group_cols].values.astype(float)
InvT = df_long["InvT"].values.astype(float)
lnVisc_true = df_long[target_col].values.astype(float)
lnVisc_anchor = df_long["anchor_lnVisc"].values.astype(float)
invT_anchor = df_long["invT_anchor"].values.astype(float)
material_keys = df_long[material_key_col].values.astype(str)

unique_materials = np.unique(material_keys)
all_sample_indices = np.arange(len(lnVisc_true))

eta_true = safe_exp(lnVisc_true)

print(f"总温度点数: {len(lnVisc_true)}, 总物质数: {len(unique_materials)}")

if len(unique_materials) < n_outer_folds:
    raise ValueError(
        f"物质数 {len(unique_materials)} 小于 n_outer_folds={n_outer_folds}，无法做 5-fold。"
    )


# =========================================================
# 6. 准备物理基线的物质真实参数 A, B
#    lnη = A + B/T = A + B * InvT
# =========================================================
material_to_AB = {}

for mat in unique_materials:
    mask = material_keys == mat

    invT_mat = InvT[mask]
    lnVisc_mat = lnVisc_true[mask]

    valid = np.isfinite(invT_mat) & np.isfinite(lnVisc_mat)

    invT_mat = invT_mat[valid]
    lnVisc_mat = lnVisc_mat[valid]

    if len(invT_mat) >= 2 and np.std(invT_mat) > 0:
        B, A = np.polyfit(invT_mat, lnVisc_mat, 1)
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
# 7. 5 折交叉验证
# =========================================================
gkf = GroupKFold(n_splits=n_outer_folds)

metrics_anchor_ln = []
metrics_physical_ln = []

metrics_anchor_eta = []
metrics_physical_eta = []

fold_test_prediction_dfs = []
fold_all_data_prediction_dfs = []
fold_all_data_count_records = []
fold_info_records = []

anchor_param_records = []
physical_param_records = []
physical_ab_records = []

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

    # -----------------------------------------------------
    # 方法1：锚点线性基线，Ridge 无截距
    # -----------------------------------------------------
    base_model = train_anchor_model(train_indices)

    if base_model is None:
        y_pred_anchor_test = np.full(len(test_indices), np.nan, dtype=float)
        baseline_delta_test = np.full(len(test_indices), np.nan, dtype=float)

        y_pred_anchor_all = np.full(len(all_sample_indices), np.nan, dtype=float)
        baseline_delta_all = np.full(len(all_sample_indices), np.nan, dtype=float)
    else:
        y_pred_anchor_test, baseline_delta_test = predict_anchor_baseline(
            test_indices,
            base_model,
        )

        y_pred_anchor_all, baseline_delta_all = predict_anchor_baseline(
            all_sample_indices,
            base_model,
        )

    # -----------------------------------------------------
    # 方法2：物理基线，Ridge 预测 A/B
    # -----------------------------------------------------
    model_A, model_B, train_mats_used_for_AB, intercept_A, intercept_B = train_physical_AB_models(
        train_mats
    )

    y_pred_physical_test, A_pred_test, B_pred_test = predict_physical_baseline(
        test_indices,
        model_A,
        model_B,
    )

    y_pred_physical_all, A_pred_all, B_pred_all = predict_physical_baseline(
        all_sample_indices,
        model_A,
        model_B,
    )

    # -----------------------------------------------------
    # 测试集评价：保留 lnVisc 空间；额外保存 eta 空间
    # -----------------------------------------------------
    y_true_test = lnVisc_true[test_indices]

    met_anchor_ln = evaluate_metrics(y_true_test, y_pred_anchor_test)
    met_physical_ln = evaluate_metrics(y_true_test, y_pred_physical_test)

    met_anchor_eta = evaluate_metrics_eta_from_lnvisc(y_true_test, y_pred_anchor_test)
    met_physical_eta = evaluate_metrics_eta_from_lnvisc(y_true_test, y_pred_physical_test)

    met_anchor_ln["fold"] = fold
    met_physical_ln["fold"] = fold
    met_anchor_eta["fold"] = fold
    met_physical_eta["fold"] = fold

    metrics_anchor_ln.append(met_anchor_ln)
    metrics_physical_ln.append(met_physical_ln)
    metrics_anchor_eta.append(met_anchor_eta)
    metrics_physical_eta.append(met_physical_eta)

    print(f"\nFold {fold}:")
    print(
        "  锚点线性基线(常温, lnη空间) - "
        f"R2={met_anchor_ln['R2']:.4f}, "
        f"MSE={met_anchor_ln['MSE']:.4f}, "
        f"RMSE={met_anchor_ln['RMSE']:.4f}, "
        f"MAE={met_anchor_ln['MAE']:.4f}, "
        f"ARD={met_anchor_ln['ARD']:.2f}%"
    )

    print(
        "  物理基线(Ridge, lnη空间)    - "
        f"R2={met_physical_ln['R2']:.4f}, "
        f"MSE={met_physical_ln['MSE']:.4f}, "
        f"RMSE={met_physical_ln['RMSE']:.4f}, "
        f"MAE={met_physical_ln['MAE']:.4f}, "
        f"ARD={met_physical_ln['ARD']:.2f}%"
    )

    print(
        "  锚点线性基线(η空间)          - "
        f"R2={met_anchor_eta['R2']:.4f}, "
        f"MSE={met_anchor_eta['MSE']:.4e}, "
        f"RMSE={met_anchor_eta['RMSE']:.4e}, "
        f"MAE={met_anchor_eta['MAE']:.4e}, "
        f"ARD={met_anchor_eta['ARD']:.2f}%"
    )

    print(
        "  物理基线(Ridge, η空间)       - "
        f"R2={met_physical_eta['R2']:.4f}, "
        f"MSE={met_physical_eta['MSE']:.4e}, "
        f"RMSE={met_physical_eta['RMSE']:.4e}, "
        f"MAE={met_physical_eta['MAE']:.4e}, "
        f"ARD={met_physical_eta['ARD']:.2f}%"
    )

    # -----------------------------------------------------
    # 新增：每个 fold 模型预测完整数据集，并统计完整数据集三档偏差数量
    # 最终复制输出使用 eta 空间；同时保存 lnVisc 空间。
    # -----------------------------------------------------
    count_anchor_all_eta = count_error_thresholds(
        eta_true,
        safe_exp(y_pred_anchor_all),
    )

    count_physical_all_eta = count_error_thresholds(
        eta_true,
        safe_exp(y_pred_physical_all),
    )

    count_anchor_all_ln = count_error_thresholds(
        lnVisc_true,
        y_pred_anchor_all,
    )

    count_physical_all_ln = count_error_thresholds(
        lnVisc_true,
        y_pred_physical_all,
    )

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "Anchor_linear_baseline_298K_Ridge",
        "count_space": "eta",
        **count_anchor_all_eta,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "Physical_baseline_Ridge",
        "count_space": "eta",
        **count_physical_all_eta,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "Anchor_linear_baseline_298K_Ridge",
        "count_space": "lnVisc",
        **count_anchor_all_ln,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "Physical_baseline_Ridge",
        "count_space": "lnVisc",
        **count_physical_all_ln,
    })

    print("\nAnchor baseline fold model predicts ALL data count summary in eta space:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "Anchor_linear_baseline_298K_Ridge",
        "count_space": "eta",
        **count_anchor_all_eta,
    }]).to_string(index=False))

    print("\nPhysical baseline fold model predicts ALL data count summary in eta space:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "Physical_baseline_Ridge",
        "count_space": "eta",
        **count_physical_all_eta,
    }]).to_string(index=False))

    # -----------------------------------------------------
    # 保存测试集预测明细
    # -----------------------------------------------------
    df_test_anchor = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="Anchor_linear_baseline_298K_Ridge",
        sample_indices=test_indices,
        y_true_lnvisc=y_true_test,
        y_pred_lnvisc=y_pred_anchor_test,
        baseline_delta=baseline_delta_test,
    )

    df_test_physical = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="Physical_baseline_Ridge",
        sample_indices=test_indices,
        y_true_lnvisc=y_true_test,
        y_pred_lnvisc=y_pred_physical_test,
        A_pred=A_pred_test,
        B_pred=B_pred_test,
    )

    fold_test_prediction_dfs.append(df_test_anchor)
    fold_test_prediction_dfs.append(df_test_physical)

    # -----------------------------------------------------
    # 保存完整数据集预测明细
    # -----------------------------------------------------
    df_all_anchor = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="Anchor_linear_baseline_298K_Ridge",
        sample_indices=all_sample_indices,
        y_true_lnvisc=lnVisc_true,
        y_pred_lnvisc=y_pred_anchor_all,
        baseline_delta=baseline_delta_all,
    )

    df_all_physical = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="Physical_baseline_Ridge",
        sample_indices=all_sample_indices,
        y_true_lnvisc=lnVisc_true,
        y_pred_lnvisc=y_pred_physical_all,
        A_pred=A_pred_all,
        B_pred=B_pred_all,
    )

    fold_all_data_prediction_dfs.append(df_all_anchor)
    fold_all_data_prediction_dfs.append(df_all_physical)

    # -----------------------------------------------------
    # 保存模型参数
    # -----------------------------------------------------
    if base_model is not None and hasattr(base_model, "coef_"):
        for group_name, coef in zip(used_group_cols, base_model.coef_):
            anchor_param_records.append({
                "fold": fold,
                "group_name": group_name,
                "anchor_slope_coef_for_Nk_deltaInvT": coef,
                "abs_anchor_slope_coef": abs(coef),
                "ridge_alpha": ridge_alpha,
            })

    if model_A is not None and model_B is not None:
        for group_name, coef_A, coef_B in zip(used_group_cols, model_A.coef_, model_B.coef_):
            physical_param_records.append({
                "fold": fold,
                "group_name": group_name,
                "coef_for_A": coef_A,
                "coef_for_B": coef_B,
                "abs_coef_for_A": abs(coef_A),
                "abs_coef_for_B": abs(coef_B),
                "intercept_A": model_A.intercept_,
                "intercept_B": model_B.intercept_,
                "ridge_alpha": ridge_alpha,
            })

        unique_test_mats = np.unique(material_keys[test_indices])

        for mat in unique_test_mats:
            idx = np.where(material_keys == mat)[0][0]
            x_one = X_groups[idx].reshape(1, -1)

            A_pred_mat = float(model_A.predict(x_one)[0])
            B_pred_mat = float(model_B.predict(x_one)[0])

            A_true, B_true = material_to_AB.get(mat, (np.nan, np.nan))

            physical_ab_records.append({
                "fold": fold,
                material_key_col: mat,
                "A_true": A_true,
                "B_true": B_true,
                "A_pred": A_pred_mat,
                "B_pred": B_pred_mat,
                "A_error": A_pred_mat - A_true if np.isfinite(A_true) else np.nan,
                "B_error": B_pred_mat - B_true if np.isfinite(B_true) else np.nan,
                "A_abs_error": abs(A_pred_mat - A_true) if np.isfinite(A_true) else np.nan,
                "B_abs_error": abs(B_pred_mat - B_true) if np.isfinite(B_true) else np.nan,
            })

    fold_info_records.append({
        "fold": fold,
        "n_train_materials": len(train_mats),
        "n_test_materials": len(test_mats),
        "n_train_points": len(train_indices),
        "n_test_points": len(test_indices),
        "n_all_points": len(all_sample_indices),
        "n_group_features": len(used_group_cols),
        "anchor_model_trained": base_model is not None,
        "physical_model_trained": model_A is not None and model_B is not None,
        "n_train_materials_used_for_AB": len(train_mats_used_for_AB),
        "ridge_alpha": ridge_alpha,
    })


# =========================================================
# 8. 汇总统计与配对 t 检验
# =========================================================
df_anchor_ln = pd.DataFrame(metrics_anchor_ln)
df_physical_ln = pd.DataFrame(metrics_physical_ln)

df_anchor_eta = pd.DataFrame(metrics_anchor_eta)
df_physical_eta = pd.DataFrame(metrics_physical_eta)

df_anchor_ln = df_anchor_ln[["fold"] + [c for c in df_anchor_ln.columns if c != "fold"]]
df_physical_ln = df_physical_ln[["fold"] + [c for c in df_physical_ln.columns if c != "fold"]]
df_anchor_eta = df_anchor_eta[["fold"] + [c for c in df_anchor_eta.columns if c != "fold"]]
df_physical_eta = df_physical_eta[["fold"] + [c for c in df_physical_eta.columns if c != "fold"]]

summary_anchor_ln = summarize(df_anchor_ln, "Anchor linear baseline (298K Ridge, lnVisc)")
summary_physical_ln = summarize(df_physical_ln, "Physical baseline (Ridge, lnVisc)")

summary_anchor_eta = summarize(df_anchor_eta, "Anchor linear baseline (298K Ridge, eta)")
summary_physical_eta = summarize(df_physical_eta, "Physical baseline (Ridge, eta)")

summary_ln = pd.concat(
    [summary_anchor_ln, summary_physical_ln],
    ignore_index=True,
)

summary_eta = pd.concat(
    [summary_anchor_eta, summary_physical_eta],
    ignore_index=True,
)

summary_all = pd.concat(
    [summary_ln, summary_eta],
    ignore_index=True,
)

print("\n========== lnVisc 空间 5-Fold CV Summary (Mean ± Std) ==========")
print(summary_ln.to_string(index=False))

print("\n========== eta 空间 5-Fold CV Summary (Mean ± Std) ==========")
print(summary_eta.to_string(index=False))


# =========================================================
# 9. 配对 t 检验
# =========================================================
def paired_ttest(df_a, df_b, metric_list, name_a, name_b):
    results = []

    for metric in metric_list:
        vals_a = df_a[metric].values.astype(float)
        vals_b = df_b[metric].values.astype(float)

        valid = np.isfinite(vals_a) & np.isfinite(vals_b)

        vals_a = vals_a[valid]
        vals_b = vals_b[valid]

        if len(vals_a) > 1:
            t_stat, p_val = ttest_rel(vals_a, vals_b)

            if metric == "R2":
                better = name_a if np.mean(vals_a) > np.mean(vals_b) else name_b
            else:
                better = name_a if np.mean(vals_a) < np.mean(vals_b) else name_b

            results.append({
                "Metric": metric,
                f"Mean_{name_a}": f"{np.mean(vals_a):.4f}",
                f"Mean_{name_b}": f"{np.mean(vals_b):.4f}",
                "p-value": f"{p_val:.4e}",
                "Significant(p<0.05)": p_val < 0.05,
                "Better model": better,
                "n_valid_fold_pairs": len(vals_a),
            })

    return pd.DataFrame(results)


metric_list_for_ttest = ["R2", "MSE", "RMSE", "MAE", "ARD"]

df_ttest_ln = paired_ttest(
    df_anchor_ln,
    df_physical_ln,
    metric_list_for_ttest,
    "anchor_lnVisc",
    "physical_lnVisc",
)

df_ttest_eta = paired_ttest(
    df_anchor_eta,
    df_physical_eta,
    metric_list_for_ttest,
    "anchor_eta",
    "physical_eta",
)

print("\n========== Paired t-test (lnVisc 空间) ==========")
print(df_ttest_ln.to_string(index=False))

print("\n========== Paired t-test (eta 空间) ==========")
print(df_ttest_eta.to_string(index=False))


# =========================================================
# 10. 完整数据集偏差数量统计汇总
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
        "n_all_data_points": len(lnVisc_true),
    })

df_final_average_summary = pd.DataFrame(final_average_records)

print("\n========== Fold all-data count summary ==========")
print(df_fold_all_data_count_summary.to_string(index=False))

print("\n========== Final average all-data count summary ==========")
print(df_final_average_summary.to_string(index=False))


# =========================================================
# 11. 整理保存表
# =========================================================
df_fold_test_predictions = pd.concat(fold_test_prediction_dfs, ignore_index=True)
df_fold_all_data_predictions = pd.concat(fold_all_data_prediction_dfs, ignore_index=True)

df_fold_info = pd.DataFrame(fold_info_records)

df_anchor_params = pd.DataFrame(anchor_param_records)
df_physical_params = pd.DataFrame(physical_param_records)
df_physical_ab_by_fold = pd.DataFrame(physical_ab_records)

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
    {"param": "target_col", "value": target_col},
    {"param": "viscosity_col", "value": viscosity_col if viscosity_col is not None else "not_found"},
    {"param": "temp_col", "value": temp_col},
    {"param": "n_outer_folds", "value": n_outer_folds},
    {"param": "random_state", "value": random_state},
    {"param": "anchor_temp_K", "value": ANCHOR_TEMP},
    {"param": "anchor_temp_tolerance_K", "value": ANCHOR_TEMP_TOLERANCE},
    {"param": "ridge_alpha", "value": ridge_alpha},
    {"param": "n_group_features", "value": len(used_group_cols)},
    {"param": "n_all_data_points", "value": len(lnVisc_true)},
    {"param": "n_materials", "value": len(unique_materials)},
    {"param": "method1", "value": "Anchor linear baseline: lnVisc = anchor_lnVisc + Ridge(Nk*(InvT-invT_anchor))"},
    {"param": "method2", "value": "Physical baseline: lnVisc = A + B/T = A + B*InvT; A and B predicted by Ridge(Nk)"},
    {
        "param": "relative_error_definition",
        "value": "abs((y_pred - y_true) / y_true) * 100; abs(y_true)<=1e-12 -> NaN",
    },
    {
        "param": "final_count_space",
        "value": "eta space, eta=exp(lnVisc)",
    },
    {
        "param": "full_data_count_rule",
        "value": "Each fold model predicts the whole dataset; count eta-space rel_err <1%, <5%, <10%; then average counts over 5 folds.",
    },
])

df_model_structure = pd.DataFrame([
    {
        "项目": "预测对象",
        "内容": f"液体粘度 lnη，目标列 {target_col}；最终偏差数量按 η=exp(lnη) 空间统计",
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
        "项目": "交叉验证方式",
        "内容": f"{n_outer_folds}-fold GroupKFold，按 material_key 物质划分",
    },
    {
        "项目": "方法1",
        "内容": "Anchor_linear_baseline_298K_Ridge：lnη = lnη_anchor + Ridge(Nk * (InvT - InvT_anchor))",
    },
    {
        "项目": "方法1锚点",
        "内容": f"298.15 K 常温锚点；若无实测点，则在 lnη vs 1/T 空间插值；不外推；容差 {ANCHOR_TEMP_TOLERANCE} K",
    },
    {
        "项目": "方法1训练目标",
        "内容": "lnη_true - lnη_anchor",
    },
    {
        "项目": "方法1输入特征",
        "内容": f"Nk * (InvT - InvT_anchor)，有效基团数 {len(used_group_cols)}",
    },
    {
        "项目": "方法1模型",
        "内容": f"Ridge(alpha={ridge_alpha}, fit_intercept=False)",
    },
    {
        "项目": "方法2",
        "内容": "Physical_baseline_Ridge：lnη = A + B/T = A + B*InvT",
    },
    {
        "项目": "方法2训练逻辑",
        "内容": "先对每个物质用 lnη-InvT 一阶拟合真实 A/B，再用 Ridge 基于 Nk 分别预测 A 和 B",
    },
    {
        "项目": "方法2输入特征",
        "内容": f"Nk 预测 A；Nk 预测 B；有效基团数 {len(used_group_cols)}",
    },
    {
        "项目": "方法2模型",
        "内容": f"A 模型和 B 模型均为 Ridge(alpha={ridge_alpha}, fit_intercept=True)",
    },
    {
        "项目": "是否包含子模型",
        "内容": "包含物质级参数子模型：A 参数预测模型和 B 参数预测模型",
    },
    {
        "项目": "子模型预测对象",
        "内容": "lnη = A + B/T 中的 A 和 B",
    },
    {
        "项目": "子模型类型",
        "内容": "Ridge",
    },
    {
        "项目": "子模型参数",
        "内容": f"Ridge(alpha={ridge_alpha}, fit_intercept=True)",
    },
    {
        "项目": "子模型输入特征",
        "内容": "Nk 基团向量",
    },
    {
        "项目": "slope 构造",
        "内容": "方法2中的 B 是每个物质 lnη-1/T 一阶拟合斜率，再由基团 Ridge 预测",
    },
    {
        "项目": "baseline 构造",
        "内容": "方法1为 298K 锚点线性基线；方法2为 lnη=A+B/T 物理显式基线",
    },
    {
        "项目": "residual 构造",
        "内容": "无 residual 修正模型",
    },
    {
        "项目": "最终模型",
        "内容": "方法1：anchor_lnVisc + Ridge(Nk*(InvT-invT_anchor))；方法2：A_pred + B_pred*InvT",
    },
    {
        "项目": "偏差数量统计口径",
        "内容": "每个 fold 模型预测完整数据集，在 η=exp(lnη) 空间统计相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 取平均",
    },
])


# =========================================================
# 12. 保存结果到 Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    # 原始 lnVisc 空间核心输出
    df_anchor_ln.to_excel(writer, sheet_name="Fold_Metrics_Anchor_lnVisc", index=False)
    df_physical_ln.to_excel(writer, sheet_name="Fold_Metrics_Physical_lnVisc", index=False)
    summary_ln.to_excel(writer, sheet_name="Summary_lnVisc_Mean_Std", index=False)
    df_ttest_ln.to_excel(writer, sheet_name="Paired_T_Test_lnVisc", index=False)

    # eta 空间额外输出
    df_anchor_eta.to_excel(writer, sheet_name="Fold_Metrics_Anchor_eta", index=False)
    df_physical_eta.to_excel(writer, sheet_name="Fold_Metrics_Physical_eta", index=False)
    summary_eta.to_excel(writer, sheet_name="Summary_eta_Mean_Std", index=False)
    df_ttest_eta.to_excel(writer, sheet_name="Paired_T_Test_eta", index=False)

    # 新增预测明细与全数据统计
    df_fold_test_predictions.to_excel(writer, sheet_name="fold_test_predictions", index=False)
    df_fold_all_data_predictions.to_excel(writer, sheet_name="fold_all_data_predictions", index=False)
    df_fold_all_data_count_summary.to_excel(writer, sheet_name="fold_all_data_count_summary", index=False)
    df_final_average_summary.to_excel(writer, sheet_name="final_average_summary", index=False)

    # 子模型 / 参数 / A-B 诊断
    df_true_ab_all.to_excel(writer, sheet_name="Physical_AB_True_All", index=False)
    df_physical_ab_by_fold.to_excel(writer, sheet_name="Physical_AB_By_Fold", index=False)
    df_anchor_params.to_excel(writer, sheet_name="anchor_params", index=False)
    df_physical_params.to_excel(writer, sheet_name="physical_params", index=False)

    # 锚点信息
    df_anchor_info.to_excel(writer, sheet_name="anchor_298K_info", index=False)

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
def get_final_counts(method_name, count_space="eta"):
    row = df_final_average_summary[
        (df_final_average_summary["Method"] == method_name)
        & (df_final_average_summary["count_space"] == count_space)
    ]

    if row.empty:
        return np.nan, np.nan, np.nan

    row = row.iloc[0]

    return (
        row["mean_count_rel_err_lt_1pct"],
        row["mean_count_rel _err_lt_5pct"],
        row["mean_count_rel_err_lt_10pct"],
    )


anchor_1, anchor_5, anchor_10 = get_final_counts(
    "Anchor_linear_baseline_298K_Ridge",
    count_space="eta",
)

physical_1, physical_5, physical_10 = get_final_counts(
    "Physical_baseline_Ridge",
    count_space="eta",
)

print("\n方法1 全数据预测偏差 1%，5%，10%分别为：")
print(anchor_1)
print(anchor_5)
print(anchor_10)

print("\n方法2 全数据预测偏差 1%，5%，10%分别为：")
print(physical_1)
print(physical_5)
print(physical_10)


# =========================================================
# 14. 代码结构打印
# =========================================================
print("\n========== 当前代码结构简要汇总 ==========")
print(f"预测对象：液体粘度 lnη / {target_col}，最终偏差数量按 η=exp(lnη) 空间统计")
print(f"数据文件：{input_file}")
print(f"sheet 名称：{data_sheet}, {groups_sheet}")
print(f"交叉验证：{n_outer_folds}-fold GroupKFold，按 material_key 物质划分")
print("方法1：Anchor_linear_baseline_298K_Ridge，lnη = lnη_anchor + Ridge(Nk*(InvT-invT_anchor))")
print(f"方法1锚点：298.15 K；在 lnη vs 1/T 空间插值；容差 {ANCHOR_TEMP_TOLERANCE} K；不外推")
print("方法2：Physical_baseline_Ridge，lnη = A + B/T = A + B*InvT")
print("子模型：方法2包含 A 参数预测模型和 B 参数预测模型")
print(f"子模型参数：Ridge(alpha={ridge_alpha}, fit_intercept=True)")
print("子模型输入特征：Nk 基团向量")
print("slope 构造：B 为每个物质 lnη-1/T 一阶拟合斜率，再由基团 Ridge 预测")
print("baseline 构造：方法1为 298K 锚点线性基线；方法2为物理显式基线")
print("residual 模型：无")
print(f"方法1最终模型：Ridge(alpha={ridge_alpha}, fit_intercept=False)")
print(f"方法2最终模型：两个 Ridge(alpha={ridge_alpha}, fit_intercept=True) 分别预测 A 和 B")
print("方法1最终输入：Nk*(InvT-invT_anchor)")
print("方法2最终输入：Nk 预测 A；Nk 预测 B；最终 lnη=A+B*InvT")
print("偏差统计口径：每个 fold 模型预测完整数据集，在 η=exp(lnη) 空间统计 <1%、<5%、<10% 点数，再对 5 个 fold 取平均")