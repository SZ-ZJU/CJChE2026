# import pandas as pd
# import numpy as np
# from pathlib import Path
# from sklearn.model_selection import GroupKFold
# from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
# from xgboost import XGBRegressor
# from scipy.stats import ttest_rel
#
# pd.set_option("display.float_format", "{:.10f}".format)
# np.set_printoptions(suppress=True, precision=10)
#
# # =========================================================
# # 0. 全局设置（与原始代码保持一致）
# # =========================================================
# descriptor_file = Path("selected_descriptors_with_density_mean_target.xlsx")
# descriptor_sheet = "Selected_Features_Target"
# selected_feature_sheet = "Selected_Features"
#
# data_file = Path("dataset_density_selected_by_two_k_with_density_T_interpolation_8points.xlsx")
# data_sheet = "Data_selected"
#
# slope_file = Path("HistGB_submodels_predict_ref_density_Tb_and_slope.xlsx")
# slope_sheet = "slope"
# slope_col = "slope_pred_density_over_T"
#
# output_file = Path("XGB_density_5fold_CV_comparison.xlsx")
#
# material_key_col = "material_key"
# temp_col = "T_K"
#
# # 密度目标列候选
# density_col_candidates = [
#     "property_value", "value", "Density_kg_m3", "density_kg_m3",
#     "Density, kg/m3", "Mass density, kg/m3", "mass_density_kg_m3",
#     "Mass_Density_kg_m3", "rho_kg_m3", "rho", "density", "Density"
# ]
#
# data_material_key_candidates = [
#     "material_key", "original_material_index", "pubchem_cid", "CID_int",
#     "sdf_pubchem_cid", "existing_pubchem_cid", "inchikey", "InChIKey", "cas", "compound_name"
# ]
#
# n_outer_folds = 5
# random_state = 42
#
# # XGBoost 参数（与原始代码一致）
# xgb_params = {
#     "n_estimators": 300,
#     "learning_rate": 0.1,
#     "max_depth": 6,
#     "random_state": 42,
#     "verbosity": 0,
#     "n_jobs": -1,
#     "objective": "reg:squarederror"
# }
#
# # =========================================================
# # 1. 工具函数（与原始代码保持一致）
# # =========================================================
# def normalize_colname(name):
#     return str(name).lower().replace(" ", "").replace("_", "").replace("-", "")
#
# def find_first_existing_col(df, candidates, required=True, col_type="列"):
#     norm_map = {normalize_colname(c): c for c in df.columns}
#     for c in candidates:
#         key = normalize_colname(c)
#         if key in norm_map:
#             return norm_map[key]
#     if required:
#         raise ValueError(f"没有找到 {col_type}。候选: {candidates}")
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
# def choose_alignment_key(df_desc, df_data):
#     candidate_pairs = [
#         ("material_key", "material_key"),
#         ("original_material_index", "original_material_index"),
#         ("pubchem_cid", "pubchem_cid"),
#         ("CID_int", "pubchem_cid"),
#         ("sdf_pubchem_cid", "pubchem_cid"),
#         ("existing_pubchem_cid", "pubchem_cid"),
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
# def choose_data_group_key(df_data):
#     for col in data_material_key_candidates:
#         if col in df_data.columns:
#             return col
#     return None
#
# def choose_slope_key(df_slope, data_key_col):
#     if data_key_col is not None and data_key_col in df_slope.columns:
#         return data_key_col
#     for col in data_material_key_candidates:
#         if col in df_slope.columns:
#             return col
#     return None
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
# # 2. 读取数据并预处理（一次性）
# # =========================================================
# print("读取数据...")
# df_desc = pd.read_excel(descriptor_file, sheet_name=descriptor_sheet)
# df_data = pd.read_excel(data_file, sheet_name=data_sheet)
# df_slope = pd.read_excel(slope_file, sheet_name=slope_sheet)
#
# # 读 selected descriptor 列表
# xls_desc = pd.ExcelFile(descriptor_file)
# if selected_feature_sheet in xls_desc.sheet_names:
#     df_selected = pd.read_excel(descriptor_file, sheet_name=selected_feature_sheet)
#     if "selected_feature" not in df_selected.columns:
#         raise ValueError(f"{selected_feature_sheet} 中没有 selected_feature 列。")
#     feature_cols = df_selected["selected_feature"].dropna().astype(str).tolist()
# else:
#     # 后备：自动取非元数据列
#     meta = ["material_index","original_material_index","material_key","compound_name","cas","formula","SMILES","smiles","inchikey","InChIKey","pubchem_cid","phase","boiling_T_K","critical_T_K","target_n_valid_points","target_min_density","target_max_density","target_mean_density"]
#     feature_cols = [c for c in df_desc.columns if c not in meta]
#
# # 数值化描述符
# df_features = df_desc[feature_cols].apply(pd.to_numeric, errors="coerce").fillna(df_desc[feature_cols].mean())
# df_features = df_features.dropna(axis=1, how="any")
# nonzero = df_features.abs().sum(axis=0) != 0
# used_feature_cols = df_features.columns[nonzero].tolist()
# print(f"有效描述符数量: {len(used_feature_cols)}")
#
# # 找到密度列和温度列
# density_col = find_first_existing_col(df_data, density_col_candidates, required=True, col_type="density")
# if temp_col not in df_data.columns:
#     raise ValueError(f"Data_selected 中没有找到温度列: {temp_col}")
# df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
# df_data[density_col] = pd.to_numeric(df_data[density_col], errors="coerce")
#
# # 处理 slope 列
# if slope_col not in df_slope.columns:
#     raise ValueError(f"slope 表中没有列: {slope_col}")
# df_slope[slope_col] = pd.to_numeric(df_slope[slope_col], errors="coerce")
#
# # 对齐物质 ID
# desc_key_col, data_key_col = choose_alignment_key(df_desc, df_data)
# data_group_col = choose_data_group_key(df_data)
# slope_key_col = choose_slope_key(df_slope, data_key_col)
#
# if desc_key_col is not None and data_key_col is not None:
#     # 使用公共 ID 对齐
#     df_desc["_key"] = df_desc[desc_key_col].apply(clean_key_value)
#     df_data["_key"] = df_data[data_key_col].apply(clean_key_value)
#     df_desc = df_desc.dropna(subset=["_key"]).drop_duplicates("_key")
#     df_data = df_data.dropna(subset=["_key"])
#     desc_map = {row["_key"]: row[used_feature_cols].values for _, row in df_desc.iterrows()}
#     df_slope["_key"] = df_slope[slope_key_col].apply(clean_key_value)
#     df_slope = df_slope.dropna(subset=["_key"]).drop_duplicates("_key")
#     slope_map = df_slope.set_index("_key")[slope_col].to_dict()
#     common_keys = set(desc_map.keys()) & set(df_data["_key"].unique()) & set(slope_map.keys())
#     valid_keys = [k for k in common_keys if np.isfinite(slope_map.get(k, np.nan))]
#     if not valid_keys:
#         raise ValueError("没有同时拥有描述符、数据点和有效斜率的物质")
#     # 构建特征矩阵
#     X_no_slope = []
#     X_with_slope = []
#     y = []
#     material_ids = []
#     for key in valid_keys:
#         desc = desc_map[key]
#         slope_val = slope_map[key]
#         sub = df_data[df_data["_key"] == key]
#         for _, row in sub.iterrows():
#             T = row[temp_col]
#             yv = row[density_col]
#             if not (np.isfinite(T) and np.isfinite(yv)):
#                 continue
#             X_no_slope.append(np.concatenate([desc, [T]]))
#             X_with_slope.append(np.concatenate([desc, [T, slope_val]]))
#             y.append(yv)
#             material_ids.append(key)
# else:
#     # 备用：按顺序对齐（仅当物质数一致且顺序相同）
#     if data_group_col is None:
#         raise ValueError("无法确定物质分组列")
#     df_data["_group"] = df_data[data_group_col].apply(clean_key_value)
#     groups = df_data["_group"].drop_duplicates().tolist()
#     if len(groups) != len(df_features):
#         raise ValueError("物质分组数与描述符行数不一致")
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
#             T = row[temp_col]
#             yv = row[density_col]
#             if not (np.isfinite(T) and np.isfinite(yv)):
#                 continue
#             X_no_slope.append(np.concatenate([desc, [T]]))
#             X_with_slope.append(np.concatenate([desc, [T, slope_val]]))
#             y.append(yv)
#             material_ids.append(key)
#
# X_no_slope = np.array(X_no_slope, dtype=float)
# X_with_slope = np.array(X_with_slope, dtype=float)
# y = np.array(y, dtype=float)
# material_ids = np.array(material_ids, dtype=str)
#
# unique_materials = np.unique(material_ids)
# print(f"总样本数: {len(y)}, 总物质数: {len(unique_materials)}")
#
# # =========================================================
# # 3. 5折交叉验证（按物质划分）
# # =========================================================
# # 为每个样本分配物质索引（整数）
# mat_to_int = {m: i for i, m in enumerate(unique_materials)}
# mat_indices = np.array([mat_to_int[m] for m in material_ids])
#
# gkf = GroupKFold(n_splits=n_outer_folds)
# metrics_no_slope = []
# metrics_with_slope = []
#
# for fold, (train_idx, test_idx) in enumerate(gkf.split(X_no_slope, y, groups=mat_indices)):
#     print(f"\n========== Fold {fold+1}/{n_outer_folds} ==========")
#     # 注意：train_idx/test_idx 是基于无 slope 数据集的样本索引，但两个数据集样本顺序相同吗？
#     # 由于我们是用相同顺序构建的，X_with_slope 的样本顺序与 X_no_slope 一致，所以可以直接复用。
#     X_train_no = X_no_slope[train_idx]
#     X_test_no = X_no_slope[test_idx]
#     y_train = y[train_idx]
#     y_test = y[test_idx]
#
#     X_train_with = X_with_slope[train_idx]
#     X_test_with = X_with_slope[test_idx]
#
#     # 训练模型A（无斜率）
#     model_no = XGBRegressor(**xgb_params)
#     model_no.fit(X_train_no, y_train)
#     y_pred_no = model_no.predict(X_test_no)
#     met_no = evaluate_metrics(y_test, y_pred_no)
#
#     # 训练模型B（有斜率）
#     model_with = XGBRegressor(**xgb_params)
#     model_with.fit(X_train_with, y_train)
#     y_pred_with = model_with.predict(X_test_with)
#     met_with = evaluate_metrics(y_test, y_pred_with)
#
#     met_no["fold"] = fold+1
#     met_with["fold"] = fold+1
#     metrics_no_slope.append(met_no)
#     metrics_with_slope.append(met_with)
#
#     print(f"  No slope   - R2={met_no['R2']:.4f}, RMSE={met_no['RMSE']:.4f}, MAE={met_no['MAE']:.4f}, ARD={met_no['ARD']:.2f}%")
#     print(f"  With slope - R2={met_with['R2']:.4f}, RMSE={met_with['RMSE']:.4f}, MAE={met_with['MAE']:.4f}, ARD={met_with['ARD']:.2f}%")
#
# # =========================================================
# # 4. 汇总统计（均值±标准差）
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
# summary_no = summarize(df_no, "XGB (desc+T)")
# summary_with = summarize(df_with, "XGB (desc+T+slope)")
# summary_all = pd.concat([summary_no, summary_with], ignore_index=True)
#
# print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
# print(summary_all.to_string(index=False))
#
# # =========================================================
# # 5. 配对 t 检验
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
#
# df_ttest = pd.DataFrame(t_test_results)
# print("\n========== Paired t-test ==========")
# print(df_ttest.to_string(index=False))
#
# # =========================================================
# # 6. 保存结果到 Excel
# # =========================================================
# with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
#     df_no.to_excel(writer, sheet_name="Fold_Metrics_No_Slope", index=False)
#     df_with.to_excel(writer, sheet_name="Fold_Metrics_With_Slope", index=False)
#     summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
#     df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)
#
#     pd.DataFrame([
#         {"param": "n_outer_folds", "value": n_outer_folds},
#         {"param": "random_state", "value": random_state},
#         {"param": "xgb_params", "value": str(xgb_params)},
#         {"param": "n_descriptors", "value": len(used_feature_cols)},
#         {"param": "total_samples", "value": len(y)},
#         {"param": "n_materials", "value": len(unique_materials)},
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
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from xgboost import XGBRegressor
from scipy.stats import ttest_rel

import warnings
warnings.filterwarnings("ignore")

pd.set_option("display.float_format", "{:.10f}".format)
np.set_printoptions(suppress=True, precision=10)


# =========================================================
# 0. 全局设置（与原始代码保持一致）
# =========================================================
descriptor_file = Path("selected_descriptors_with_density_mean_target.xlsx")
descriptor_sheet = "Selected_Features_Target"
selected_feature_sheet = "Selected_Features"

data_file = Path("dataset_density_selected_by_two_k_with_density_T_interpolation_8points.xlsx")
data_sheet = "Data_selected"

slope_file = Path("HistGB_submodels_predict_ref_density_Tb_and_slope.xlsx")
slope_sheet = "slope"
slope_col = "slope_pred_density_over_T"

output_file = Path("XGB_density_5fold_CV_comparison.xlsx")

material_key_col = "material_key"
temp_col = "T_K"

density_col_candidates = [
    "property_value", "value", "Density_kg_m3", "density_kg_m3",
    "Density, kg/m3", "Mass density, kg/m3", "mass_density_kg_m3",
    "Mass_Density_kg_m3", "rho_kg_m3", "rho", "density", "Density"
]

data_material_key_candidates = [
    "material_key", "original_material_index", "pubchem_cid", "CID_int",
    "sdf_pubchem_cid", "existing_pubchem_cid", "inchikey",
    "InChIKey", "cas", "compound_name"
]

n_outer_folds = 5
random_state = 42

# XGBoost 参数（与原始代码一致）
xgb_params = {
    "n_estimators": 300,
    "learning_rate": 0.1,
    "max_depth": 6,
    "random_state": 42,
    "verbosity": 0,
    "n_jobs": -1,
    "objective": "reg:squarederror",
}


# =========================================================
# 1. 工具函数
# =========================================================
def normalize_colname(name):
    return str(name).lower().replace(" ", "").replace("_", "").replace("-", "")


def find_first_existing_col(df, candidates, required=True, col_type="列"):
    norm_map = {normalize_colname(c): c for c in df.columns}

    for c in candidates:
        key = normalize_colname(c)
        if key in norm_map:
            return norm_map[key]

    if required:
        raise ValueError(f"没有找到 {col_type}。候选: {candidates}")

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


def choose_alignment_key(df_desc, df_data):
    candidate_pairs = [
        ("material_key", "material_key"),
        ("original_material_index", "original_material_index"),
        ("pubchem_cid", "pubchem_cid"),
        ("CID_int", "pubchem_cid"),
        ("sdf_pubchem_cid", "pubchem_cid"),
        ("existing_pubchem_cid", "pubchem_cid"),
        ("inchikey", "inchikey"),
        ("InChIKey", "InChIKey"),
        ("cas", "cas"),
        ("compound_name", "compound_name"),
    ]

    for dcol, dacol in candidate_pairs:
        if dcol in df_desc.columns and dacol in df_data.columns:
            return dcol, dacol

    return None, None


def choose_data_group_key(df_data):
    for col in data_material_key_candidates:
        if col in df_data.columns:
            return col

    return None


def choose_slope_key(df_slope, data_key_col):
    if data_key_col is not None and data_key_col in df_slope.columns:
        return data_key_col

    for col in data_material_key_candidates:
        if col in df_slope.columns:
            return col

    return None


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
    统计相对误差 <1%、<5%、<10% 的点数。
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


def make_prediction_df(fold, dataset_name, method, meta_df, y_true, y_pred):
    """
    保存测试集或完整数据集预测明细。
    """
    meta_df = meta_df.copy().reset_index(drop=True)

    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    rel_err = safe_relative_error_percent(y_true, y_pred)

    df_out = meta_df.copy()
    df_out.insert(0, "fold", fold)
    df_out.insert(1, "dataset", dataset_name)
    df_out.insert(2, "Method", method)

    df_out["rho_true"] = y_true
    df_out["rho_pred"] = y_pred
    df_out["error"] = y_pred - y_true
    df_out["absolute_error"] = np.abs(y_pred - y_true)
    df_out["relative_error_percent"] = rel_err

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
# 2. 读取数据并预处理
# =========================================================
print("读取数据...")

if not descriptor_file.exists():
    raise FileNotFoundError(f"没有找到描述符文件: {descriptor_file}")

if not data_file.exists():
    raise FileNotFoundError(f"没有找到数据文件: {data_file}")

if not slope_file.exists():
    raise FileNotFoundError(f"没有找到 slope 文件: {slope_file}")

df_desc = pd.read_excel(descriptor_file, sheet_name=descriptor_sheet)
df_data = pd.read_excel(data_file, sheet_name=data_sheet)
df_slope = pd.read_excel(slope_file, sheet_name=slope_sheet)

print("描述符表行数:", len(df_desc))
print("数据表行数:", len(df_data))
print("slope 表行数:", len(df_slope))


# =========================================================
# 3. 读取 selected descriptor 列表
# =========================================================
xls_desc = pd.ExcelFile(descriptor_file)

if selected_feature_sheet in xls_desc.sheet_names:
    df_selected = pd.read_excel(descriptor_file, sheet_name=selected_feature_sheet)

    if "selected_feature" not in df_selected.columns:
        raise ValueError(f"{selected_feature_sheet} 中没有 selected_feature 列。")

    feature_cols = df_selected["selected_feature"].dropna().astype(str).tolist()

else:
    meta = [
        "material_index", "original_material_index", "material_key",
        "compound_name", "cas", "formula", "SMILES", "smiles",
        "inchikey", "InChIKey", "pubchem_cid", "phase",
        "boiling_T_K", "critical_T_K", "target_n_valid_points",
        "target_min_density", "target_max_density", "target_mean_density"
    ]

    feature_cols = [c for c in df_desc.columns if c not in meta]

missing_features = [c for c in feature_cols if c not in df_desc.columns]

if len(missing_features) > 0:
    raise ValueError(f"以下选中描述符不在描述符表中: {missing_features}")

# 数值化描述符
df_features = df_desc[feature_cols].apply(pd.to_numeric, errors="coerce")
df_features = df_features.replace([np.inf, -np.inf], np.nan)
df_features = df_features.fillna(df_features.mean())
df_features = df_features.dropna(axis=1, how="any")

nonzero = df_features.abs().sum(axis=0) != 0

used_feature_cols = df_features.columns[nonzero].tolist()
removed_zero_feature_cols = df_features.columns[~nonzero].tolist()

print(f"有效描述符数量: {len(used_feature_cols)}")
print(f"删除全零描述符数量: {len(removed_zero_feature_cols)}")

if len(used_feature_cols) == 0:
    raise ValueError("没有有效描述符可用于建模。")


# =========================================================
# 4. 找到密度列、温度列、slope 列
# =========================================================
density_col = find_first_existing_col(
    df_data,
    density_col_candidates,
    required=True,
    col_type="density",
)

if temp_col not in df_data.columns:
    raise ValueError(f"Data_selected 中没有找到温度列: {temp_col}")

if slope_col not in df_slope.columns:
    raise ValueError(f"slope 表中没有列: {slope_col}")

df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
df_data[density_col] = pd.to_numeric(df_data[density_col], errors="coerce")
df_slope[slope_col] = pd.to_numeric(df_slope[slope_col], errors="coerce")

print("密度列:", density_col)
print("温度列:", temp_col)
print("slope 列:", slope_col)


# =========================================================
# 5. 对齐物质 ID
# =========================================================
desc_key_col, data_key_col = choose_alignment_key(df_desc, df_data)
data_group_col = choose_data_group_key(df_data)
slope_key_col = choose_slope_key(df_slope, data_key_col)

print("\n物质对齐方式:")
print("desc_key_col:", desc_key_col)
print("data_key_col:", data_key_col)
print("data_group_col:", data_group_col)
print("slope_key_col:", slope_key_col)

if slope_key_col is None:
    raise ValueError("无法确定 slope 表中的物质 ID 列。")


# =========================================================
# 6. 构造特征矩阵和元数据
# =========================================================
X_no_slope = []
X_with_slope = []
y = []
material_ids = []
meta_rows = []

# ---------- 6.1 优先使用公共 ID 对齐 ----------
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

    # 同步有效描述符列
    df_desc_work[used_feature_cols] = df_features.loc[
        df_desc_work.index,
        used_feature_cols,
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

    if not valid_keys:
        raise ValueError("没有同时拥有描述符、数据点和有效斜率的物质")

    print("同时拥有描述符、数据点和有效 slope 的物质数:", len(valid_keys))

    for key in valid_keys:
        desc = np.asarray(desc_map[key], dtype=float)
        slope_val = float(slope_map[key])

        sub = df_data_work[df_data_work["_key"] == key].copy()

        for _, row in sub.iterrows():
            T = row[temp_col]
            yv = row[density_col]

            if not (
                np.isfinite(T)
                and np.isfinite(yv)
                and T > 0
                and yv > 0
            ):
                continue

            X_no_slope.append(np.concatenate([desc, [T]]))
            X_with_slope.append(np.concatenate([desc, [T, slope_val]]))
            y.append(yv)
            material_ids.append(key)

            meta = {
                "_key": key,
                material_key_col: key,
                temp_col: T,
                density_col: yv,
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
                "inchikey",
                "InChIKey",
                "pubchem_cid",
                "phase",
                "boiling_T_K",
                "critical_T_K",
                "T_min",
                "T_max",
                "T_range",
            ]:
                if c in row.index:
                    meta[c] = row[c]

            meta_rows.append(meta)

# ---------- 6.2 备用：按顺序对齐 ----------
else:
    if data_group_col is None:
        raise ValueError("无法确定物质分组列")

    df_data_work = df_data.copy()
    df_slope_work = df_slope.copy()

    df_data_work["_group"] = df_data_work[data_group_col].apply(clean_key_value)
    groups = df_data_work["_group"].drop_duplicates().tolist()

    if len(groups) != len(df_features):
        raise ValueError("物质分组数与描述符行数不一致")

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
            T = row[temp_col]
            yv = row[density_col]

            if not (
                np.isfinite(T)
                and np.isfinite(yv)
                and T > 0
                and yv > 0
            ):
                continue

            X_no_slope.append(np.concatenate([desc, [T]]))
            X_with_slope.append(np.concatenate([desc, [T, slope_val]]))
            y.append(yv)
            material_ids.append(key)

            meta = {
                "_key": key,
                material_key_col: key,
                temp_col: T,
                density_col: yv,
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
                "inchikey",
                "InChIKey",
                "pubchem_cid",
                "phase",
                "boiling_T_K",
                "critical_T_K",
                "T_min",
                "T_max",
                "T_range",
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

print("\n========== 建模数据统计 ==========")
print("总样本数:", len(y))
print("总物质数:", len(unique_materials))
print("无 slope 特征维度:", X_no_slope.shape[1])
print("有 slope 特征维度:", X_with_slope.shape[1])

if len(y) == 0:
    raise ValueError("没有有效样本点。")

if len(unique_materials) < n_outer_folds:
    raise ValueError(
        f"有效物质数 {len(unique_materials)} 小于 n_outer_folds={n_outer_folds}。"
    )


# =========================================================
# 7. 5 折交叉验证（按物质划分）
# =========================================================
mat_to_int = {m: i for i, m in enumerate(unique_materials)}
mat_indices = np.array([mat_to_int[m] for m in material_ids])

gkf = GroupKFold(n_splits=n_outer_folds)

metrics_no_slope = []
metrics_with_slope = []

fold_test_prediction_dfs = []
fold_all_data_prediction_dfs = []
fold_all_data_count_records = []
fold_info_records = []

feature_importance_no_records = []
feature_importance_with_records = []

feature_names_no = used_feature_cols + [temp_col]
feature_names_with = used_feature_cols + [temp_col, slope_col]

all_sample_indices = np.arange(len(y))

for fold, (train_idx, test_idx) in enumerate(
    gkf.split(X_no_slope, y, groups=mat_indices),
    start=1,
):
    print(f"\n========== Fold {fold}/{n_outer_folds} ==========")

    train_materials = np.unique(material_ids[train_idx])
    test_materials = np.unique(material_ids[test_idx])

    print("训练物质数:", len(train_materials))
    print("测试物质数:", len(test_materials))
    print("训练样本数:", len(train_idx))
    print("测试样本数:", len(test_idx))

    # -----------------------------------------------------
    # 方法1：XGB desc + T
    # -----------------------------------------------------
    X_train_no = X_no_slope[train_idx]
    X_test_no = X_no_slope[test_idx]
    y_train = y[train_idx]
    y_test = y[test_idx]

    model_no = XGBRegressor(**xgb_params)
    model_no.fit(X_train_no, y_train)

    y_pred_no_test = model_no.predict(X_test_no)
    y_pred_no_all = model_no.predict(X_no_slope)

    met_no = evaluate_metrics(y_test, y_pred_no_test)
    met_no["fold"] = fold
    metrics_no_slope.append(met_no)

    # -----------------------------------------------------
    # 方法2：XGB desc + T + slope
    # -----------------------------------------------------
    X_train_with = X_with_slope[train_idx]
    X_test_with = X_with_slope[test_idx]

    model_with = XGBRegressor(**xgb_params)
    model_with.fit(X_train_with, y_train)

    y_pred_with_test = model_with.predict(X_test_with)
    y_pred_with_all = model_with.predict(X_with_slope)

    met_with = evaluate_metrics(y_test, y_pred_with_test)
    met_with["fold"] = fold
    metrics_with_slope.append(met_with)

    print(
        "  No slope   - "
        f"R2={met_no['R2']:.4f}, "
        f"MSE={met_no['MSE']:.4f}, "
        f"RMSE={met_no['RMSE']:.4f}, "
        f"MAE={met_no['MAE']:.4f}, "
        f"ARD={met_no['ARD']:.2f}%"
    )
    print(
        "  With slope - "
        f"R2={met_with['R2']:.4f}, "
        f"MSE={met_with['MSE']:.4f}, "
        f"RMSE={met_with['RMSE']:.4f}, "
        f"MAE={met_with['MAE']:.4f}, "
        f"ARD={met_with['ARD']:.2f}%"
    )

    # -----------------------------------------------------
    # 新增：每个 fold 模型预测完整数据集，统计三档偏差数量
    # -----------------------------------------------------
    count_no_all = count_error_thresholds(y, y_pred_no_all)
    count_with_all = count_error_thresholds(y, y_pred_with_all)

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "XGB_desc_T",
        **count_no_all,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "XGB_desc_T_slope",
        **count_with_all,
    })

    print("\nXGB(desc+T) fold model predicts ALL data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "XGB_desc_T",
        **count_no_all,
    }]).to_string(index=False))

    print("\nXGB(desc+T+slope) fold model predicts ALL data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "XGB_desc_T_slope",
        **count_with_all,
    }]).to_string(index=False))

    # -----------------------------------------------------
    # 保存测试集预测明细
    # -----------------------------------------------------
    df_test_meta = df_meta.iloc[test_idx].copy().reset_index(drop=True)
    df_all_meta = df_meta.copy().reset_index(drop=True)

    df_test_no = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="XGB_desc_T",
        meta_df=df_test_meta,
        y_true=y_test,
        y_pred=y_pred_no_test,
    )

    df_test_with = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="XGB_desc_T_slope",
        meta_df=df_test_meta,
        y_true=y_test,
        y_pred=y_pred_with_test,
    )

    fold_test_prediction_dfs.append(df_test_no)
    fold_test_prediction_dfs.append(df_test_with)

    # -----------------------------------------------------
    # 保存完整数据集预测明细
    # -----------------------------------------------------
    df_all_no = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="XGB_desc_T",
        meta_df=df_all_meta,
        y_true=y,
        y_pred=y_pred_no_all,
    )

    df_all_with = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="XGB_desc_T_slope",
        meta_df=df_all_meta,
        y_true=y,
        y_pred=y_pred_with_all,
    )

    fold_all_data_prediction_dfs.append(df_all_no)
    fold_all_data_prediction_dfs.append(df_all_with)

    # -----------------------------------------------------
    # 保存特征重要性
    # -----------------------------------------------------
    if hasattr(model_no, "feature_importances_"):
        for fname, imp in zip(feature_names_no, model_no.feature_importances_):
            feature_importance_no_records.append({
                "fold": fold,
                "feature": fname,
                "importance": imp,
            })

    if hasattr(model_with, "feature_importances_"):
        for fname, imp in zip(feature_names_with, model_with.feature_importances_):
            feature_importance_with_records.append({
                "fold": fold,
                "feature": fname,
                "importance": imp,
            })

    fold_info_records.append({
        "fold": fold,
        "n_train_materials": len(train_materials),
        "n_test_materials": len(test_materials),
        "n_train_points": len(train_idx),
        "n_test_points": len(test_idx),
        "n_all_points": len(y),
        "n_features_no_slope": X_no_slope.shape[1],
        "n_features_with_slope": X_with_slope.shape[1],
    })


# =========================================================
# 8. 汇总统计
# =========================================================
df_no = pd.DataFrame(metrics_no_slope)
df_with = pd.DataFrame(metrics_with_slope)

df_no = df_no[["fold"] + [c for c in df_no.columns if c != "fold"]]
df_with = df_with[["fold"] + [c for c in df_with.columns if c != "fold"]]

summary_no = summarize(df_no, "XGB (desc+T)")
summary_with = summarize(df_with, "XGB (desc+T+slope)")

summary_all = pd.concat(
    [summary_no, summary_with],
    ignore_index=True,
)

print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
print(summary_all.to_string(index=False))


# =========================================================
# 9. 配对 t 检验
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
# 10. 完整数据集偏差数量统计汇总
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
# 11. 整理输出表
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
    "slope_file": [str(slope_file)],
    "slope_sheet": [slope_sheet],
    "slope_col": [slope_col],
    "slope_key_col": [slope_key_col],
})

df_run_info = pd.DataFrame([
    {"param": "descriptor_file", "value": str(descriptor_file)},
    {"param": "descriptor_sheet", "value": descriptor_sheet},
    {"param": "selected_feature_sheet", "value": selected_feature_sheet},
    {"param": "data_file", "value": str(data_file)},
    {"param": "data_sheet", "value": data_sheet},
    {"param": "slope_file", "value": str(slope_file)},
    {"param": "slope_sheet", "value": slope_sheet},
    {"param": "slope_col", "value": slope_col},
    {"param": "density_col", "value": density_col},
    {"param": "temp_col", "value": temp_col},
    {"param": "desc_key_col", "value": desc_key_col},
    {"param": "data_key_col", "value": data_key_col},
    {"param": "data_group_col", "value": data_group_col},
    {"param": "slope_key_col", "value": slope_key_col},
    {"param": "n_outer_folds", "value": n_outer_folds},
    {"param": "random_state", "value": random_state},
    {"param": "xgb_params", "value": str(xgb_params)},
    {"param": "n_descriptors_original", "value": len(feature_cols)},
    {"param": "n_descriptors_used", "value": len(used_feature_cols)},
    {"param": "total_samples", "value": len(y)},
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
        "内容": str(slope_file),
    },
    {
        "项目": "slope sheet",
        "内容": slope_sheet,
    },
    {
        "项目": "slope 列",
        "内容": slope_col,
    },
    {
        "项目": "交叉验证方式",
        "内容": f"{n_outer_folds}-fold GroupKFold，按物质 ID 划分",
    },
    {
        "项目": "方法1",
        "内容": "XGB_desc_T：XGBRegressor，输入 [descriptors, T]",
    },
    {
        "项目": "方法2",
        "内容": "XGB_desc_T_slope：XGBRegressor，输入 [descriptors, T, slope_pred_density_over_T]",
    },
    {
        "项目": "是否包含子模型",
        "内容": "当前代码不训练子模型；读取外部 HistGB 子模型预测得到的 slope",
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
        "内容": "当前代码无法从 slope 文件恢复；仅保存 slope 预测结果",
    },
    {
        "项目": "slope 构造",
        "内容": "直接读取 slope_pred_density_over_T，作为方法2额外输入特征；没有乘以 T",
    },
    {
        "项目": "baseline 构造",
        "内容": "无 baseline + residual 结构；两个方法均为直接 XGB 回归",
    },
    {
        "项目": "residual 构造",
        "内容": "无",
    },
    {
        "项目": "最终模型类型",
        "内容": "XGBRegressor",
    },
    {
        "项目": "最终模型参数",
        "内容": str(xgb_params),
    },
    {
        "项目": "方法1最终输入",
        "内容": f"[{len(used_feature_cols)} 个描述符, T]，总维度 {len(used_feature_cols) + 1}",
    },
    {
        "项目": "方法2最终输入",
        "内容": f"[{len(used_feature_cols)} 个描述符, T, slope]，总维度 {len(used_feature_cols) + 2}",
    },
    {
        "项目": "偏差数量统计口径",
        "内容": "每个 fold 模型预测完整数据集，统计 rho 相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 取平均",
    },
])


# =========================================================
# 12. 保存结果到 Excel
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

    df_used_features.to_excel(writer, sheet_name="Used_Descriptor_Features", index=False)
    df_removed_zero_features.to_excel(writer, sheet_name="Removed_Zero_Descriptors", index=False)
    df_slope_info.to_excel(writer, sheet_name="slope_info", index=False)
    df_fold_info.to_excel(writer, sheet_name="Fold_Info", index=False)

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


no_1, no_5, no_10 = get_final_counts("XGB_desc_T")
with_1, with_5, with_10 = get_final_counts("XGB_desc_T_slope")

print("\n方法1 全数据预测偏差 1%，5%，10%分别为：")
print(no_1)
print(no_5)
print(no_10)

print("\n方法2 全数据预测偏差 1%，5%，10%分别为：")
print(with_1)
print(with_5)
print(with_10)


# =========================================================
# 14. 代码结构打印
# =========================================================
print("\n========== 当前代码结构简要汇总 ==========")
print(f"预测对象：液体密度 rho / {density_col}")
print(f"描述符文件：{descriptor_file}")
print(f"数据文件：{data_file}")
print(f"slope 文件：{slope_file}")
print(f"sheet 名称：{descriptor_sheet}, {data_sheet}, {slope_sheet}")
print(f"交叉验证：{n_outer_folds}-fold GroupKFold，按物质 ID 划分")
print("方法1：XGB_desc_T，XGBRegressor，输入 [descriptors, T]")
print("方法2：XGB_desc_T_slope，XGBRegressor，输入 [descriptors, T, slope_pred_density_over_T]")
print("子模型：当前代码不训练子模型，读取外部 HistGB 预测的 slope_pred_density_over_T")
print(f"子模型预测列：{slope_col}")
print("子模型参数：当前代码无法从 slope 文件恢复，仅保存 slope 预测值")
print("slope 构造：直接读取 slope_pred_density_over_T，作为方法2额外输入特征；没有乘以 T")
print("baseline 构造：无")
print("residual 模型：无")
print(f"最终模型：XGBRegressor，参数：{xgb_params}")
print("方法1最终输入：[descriptors, T]")
print("方法2最终输入：[descriptors, T, slope]")
print("偏差统计口径：每个 fold 模型预测完整数据集，统计 rho 相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 取平均")