# import pandas as pd
# import numpy as np
# from pathlib import Path
# from sklearn.model_selection import KFold
# from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
# from xgboost import XGBRegressor
# from scipy.stats import ttest_rel
#
# pd.set_option("display.float_format", "{:.10f}".format)
# np.set_printoptions(suppress=True, precision=10)
#
# # =========================================================
# # 0. 全局设置
# # =========================================================
# descriptor_file = Path("selected_descriptors_with_Cp_mean_target.xlsx")
# descriptor_sheet = "Selected_Features_Target"
# data_file = Path("Cp_dataset_selected_by_two_k_with_interpolation.xlsx")
# data_sheet = "Sheet1_selected"
# predicted_slope_file = Path("Group_prediction_for_k1_k2_boiling_GBDT_with_predicted_slope.xlsx")
# predicted_slope_sheet = "Predicted_Reference_Slope"
# predicted_slope_col = "reference_slope_pred"
#
# output_file = Path("XGB_descriptor_vs_descriptor_slope_5fold_CV.xlsx")
#
# n_points_per_material = 8
# temp_col = "T_K"
# target_col = "property_value"
#
# # 外层交叉验证折数
# n_outer_folds = 5
# random_state = 42
#
# # XGBoost 固定参数（与原始代码一致）
# xgb_params = {
#     "n_estimators": 300,
#     "learning_rate": 0.1,
#     "max_depth": 6,
#     "random_state": 42,          # 固定模型内部随机性
#     "verbosity": 0,
#     "n_jobs": -1,
#     "objective": "reg:squarederror"
# }
#
# # =========================================================
# # 1. 读取数据
# # =========================================================
# df_desc = pd.read_excel(descriptor_file, sheet_name=descriptor_sheet)
# df_data = pd.read_excel(data_file, sheet_name=data_sheet)
# df_slope = pd.read_excel(predicted_slope_file, sheet_name=predicted_slope_sheet)
#
# print("描述符表行数:", len(df_desc))
# print("Sheet1_selected 行数:", len(df_data))
# print("预测斜率表行数:", len(df_slope))
#
# # =========================================================
# # 2. 描述符处理（与原始代码一致：第14-38列，删除全零列）
# # =========================================================
# feature_cols = df_desc.columns[13:38].tolist()   # 0-based, 13:38 对应 14-38列
# df_features = df_desc[feature_cols].copy()
# df_features = df_features.apply(pd.to_numeric, errors="coerce").fillna(df_features.mean())
# df_features = df_features.dropna(axis=1, how="any")
# nonzero_mask = df_features.abs().sum(axis=0) != 0
# used_feature_cols = df_features.columns[nonzero_mask].tolist()
# df_features = df_features[used_feature_cols].copy()
# print("有效描述符数量:", len(used_feature_cols))
#
# # =========================================================
# # 3. 对齐预测斜率（仅用于模型B）
# # =========================================================
# if predicted_slope_col not in df_slope.columns:
#     raise ValueError(f"斜率表中没有列: {predicted_slope_col}")
# df_slope[predicted_slope_col] = pd.to_numeric(df_slope[predicted_slope_col], errors="coerce")
#
# if "original_material_index" in df_desc.columns and "original_material_index" in df_slope.columns:
#     slope_map = (df_slope[["original_material_index", predicted_slope_col]]
#                  .drop_duplicates(subset=["original_material_index"])
#                  .set_index("original_material_index")[predicted_slope_col])
#     predicted_slope_per_material = df_desc["original_material_index"].map(slope_map).values.astype(float)
#     print("使用 original_material_index 对齐预测斜率")
# else:
#     if len(df_desc) != len(df_slope):
#         raise ValueError("描述符表与斜率表行数不一致且无法通过索引对齐")
#     predicted_slope_per_material = df_slope[predicted_slope_col].values.astype(float)
#     print("按行顺序对齐预测斜率")
#
# valid_slope_mask = np.isfinite(predicted_slope_per_material)
# print(f"有效斜率物质数: {valid_slope_mask.sum()}, 无效: {(~valid_slope_mask).sum()}")
#
# # =========================================================
# # 4. 检查实验数据完整性
# # =========================================================
# if len(df_data) % n_points_per_material != 0:
#     raise ValueError("Sheet1 行数不是每个物质8行的整数倍")
# n_materials_data = len(df_data) // n_points_per_material
# n_materials_desc = len(df_features)
# print(f"实验数据物质数: {n_materials_data}, 描述符物质数: {n_materials_desc}")
#
# # 两者必须相等，并且与斜率数组长度一致
# if n_materials_data != n_materials_desc:
#     raise ValueError("描述符与实验数据物质数量不一致")
#
# # =========================================================
# # 5. 展开所有温度点数据（同时准备模型A和模型B的特征）
# # 模型A特征: [描述符, T]
# # 模型B特征: [描述符, T, 斜率]
# # 注意：过滤掉斜率无效的物质（模型B会跳过这些点）
# # =========================================================
# all_targets = []
# material_ids = []
# temperatures = []
# desc_feat_list = []      # 描述符向量（物质级）
# slope_list = []          # 斜率（物质级）
#
# for mat_idx in range(n_materials_desc):
#     desc = df_features.iloc[mat_idx].values.astype(float)
#     slope = predicted_slope_per_material[mat_idx]
#
#     start = mat_idx * n_points_per_material
#     end = start + n_points_per_material
#     sub = df_data.iloc[start:end]
#     T_vals = pd.to_numeric(sub[temp_col], errors="coerce").values.astype(float)
#     Cp_vals = pd.to_numeric(sub[target_col], errors="coerce").values.astype(float)
#
#     for local_i, (T, Cp) in enumerate(zip(T_vals, Cp_vals)):
#         if not (np.isfinite(T) and np.isfinite(Cp)):
#             continue
#         all_targets.append(Cp)
#         material_ids.append(mat_idx)
#         temperatures.append(T)
#         desc_feat_list.append(desc)
#         slope_list.append(slope)
#
# y = np.array(all_targets)
# material_ids = np.array(material_ids, dtype=int)
# temperatures = np.array(temperatures)
# desc_feat_array = np.array(desc_feat_list)          # shape (n_samples, n_desc)
# slope_array = np.array(slope_list)                  # shape (n_samples,)
#
# # 构建模型A的特征矩阵
# X_A = np.hstack([desc_feat_array, temperatures.reshape(-1, 1)])
#
# # 构建模型B的特征矩阵（需要过滤掉斜率为 nan 的点）
# valid_slope_sample = np.isfinite(slope_array)
# if not valid_slope_sample.all():
#     print(f"警告: {np.sum(~valid_slope_sample)} 个样本因斜率无效将被模型B排除")
# X_B_full = np.hstack([desc_feat_array, temperatures.reshape(-1, 1), slope_array.reshape(-1, 1)])
# X_B = X_B_full[valid_slope_sample]
# y_B = y[valid_slope_sample]
# material_ids_B = material_ids[valid_slope_sample]
#
# # 模型A使用所有样本（因为无斜率依赖）
# X_A_all = X_A
# y_A_all = y
# material_ids_A = material_ids
#
# print(f"模型A总样本数: {len(y_A_all)}")
# print(f"模型B总样本数: {len(y_B)} (过滤后)")
#
# # =========================================================
# # 6. 定义辅助函数：按物质索引列表构建训练/测试数据
# # =========================================================
# def get_data_for_materials(model_type, material_indices):
#     """
#     model_type: 'A' 或 'B'
#     material_indices: 物质索引列表
#     返回 (X, y)
#     """
#     if model_type == 'A':
#         mask = np.isin(material_ids_A, material_indices)
#         return X_A_all[mask], y_A_all[mask]
#     else:  # 'B'
#         mask = np.isin(material_ids_B, material_indices)
#         return X_B[mask], y_B[mask]
#
# # =========================================================
# # 7. 外层5折交叉验证（按物质划分，对两个模型使用相同的物质划分）
# # =========================================================
# unique_materials = np.unique(material_ids_A)   # 模型A和B的物质集合应该相同，但B可能少一些物质（斜率无效）
# # 为保证公平，划分时基于所有物质（模型A的物质集合），但模型B只使用其中有有效斜率的物质
# all_materials = np.unique(material_ids_A)
# kf = KFold(n_splits=n_outer_folds, shuffle=True, random_state=random_state)
#
# metrics_A = []   # 每折指标
# metrics_B = []
#
# for fold, (train_mat_idx, test_mat_idx) in enumerate(kf.split(all_materials)):
#     print(f"\n========== Fold {fold+1}/{n_outer_folds} ==========")
#     train_mats = all_materials[train_mat_idx]
#     test_mats = all_materials[test_mat_idx]
#
#     # ---------- 模型A ----------
#     X_train_A, y_train_A = get_data_for_materials('A', train_mats)
#     X_test_A, y_test_A = get_data_for_materials('A', test_mats)
#
#     model_A = XGBRegressor(**xgb_params)
#     model_A.fit(X_train_A, y_train_A)
#     y_pred_A = model_A.predict(X_test_A)
#
#     # ---------- 模型B ----------
#     # 注意：模型B只使用训练集和测试集中斜率有效的样本
#     # 先获取测试集物质中斜率有效的样本索引
#     test_mask_B = np.isin(material_ids_B, test_mats)
#     X_test_B, y_test_B = X_B[test_mask_B], y_B[test_mask_B]
#     # 训练集同样只取斜率有效的样本
#     train_mask_B = np.isin(material_ids_B, train_mats)
#     X_train_B, y_train_B = X_B[train_mask_B], y_B[train_mask_B]
#
#     if len(y_train_B) == 0:
#         print(f"  警告: 折 {fold+1} 模型B无训练样本，跳过")
#         y_pred_B = np.full_like(y_test_B, np.nan)
#     else:
#         model_B = XGBRegressor(**xgb_params)
#         model_B.fit(X_train_B, y_train_B)
#         y_pred_B = model_B.predict(X_test_B)
#
#     # ---------- 指标计算函数 ----------
#     def compute_metrics(y_true, y_pred):
#         mask = np.isfinite(y_true) & np.isfinite(y_pred)
#         y_true = y_true[mask]
#         y_pred = y_pred[mask]
#         if len(y_true) == 0:
#             return {k: np.nan for k in ["R2", "MSE", "RMSE", "MAE", "ARD(%)",
#                                         "max_rel_err(%)", "≤1%", "≤5%", "≤10%"]}
#         mse = mean_squared_error(y_true, y_pred)
#         rmse = np.sqrt(mse)
#         mae = mean_absolute_error(y_true, y_pred)
#         r2 = r2_score(y_true, y_pred)
#         valid = np.abs(y_true) > 1e-12
#         if valid.sum() > 0:
#             rel_err = np.abs((y_pred[valid] - y_true[valid]) / y_true[valid]) * 100
#             ard = np.mean(rel_err)
#             max_rel = np.max(rel_err)
#             pct1 = np.mean(rel_err <= 1) * 100
#             pct5 = np.mean(rel_err <= 5) * 100
#             pct10 = np.mean(rel_err <= 10) * 100
#         else:
#             ard = max_rel = pct1 = pct5 = pct10 = np.nan
#         return {
#             "R2": r2, "MSE": mse, "RMSE": rmse, "MAE": mae,
#             "ARD(%)": ard, "max_rel_err(%)": max_rel,
#             "≤1% ratio(%)": pct1, "≤5% ratio(%)": pct5, "≤10% ratio(%)": pct10
#         }
#
#     m_A = compute_metrics(y_test_A, y_pred_A)
#     m_B = compute_metrics(y_test_B, y_pred_B)
#     m_A["fold"] = fold+1
#     m_B["fold"] = fold+1
#     metrics_A.append(m_A)
#     metrics_B.append(m_B)
#
# # =========================================================
# # 8. 汇总统计（均值±标准差）
# # =========================================================
# df_A = pd.DataFrame(metrics_A)
# df_B = pd.DataFrame(metrics_B)
#
# def summarize(df, name):
#     stats = []
#     for metric in ["R2", "MSE", "RMSE", "MAE", "ARD(%)", "max_rel_err(%)",
#                    "≤1% ratio(%)", "≤5% ratio(%)", "≤10% ratio(%)"]:
#         vals = df[metric].dropna().values
#         if len(vals) == 0:
#             mean_std = "NaN"
#         else:
#             mean_val = np.mean(vals)
#             std_val = np.std(vals, ddof=1)
#             mean_std = f"{mean_val:.4f} ± {std_val:.4f}"
#         stats.append({"Model": name, "Metric": metric, "Mean±Std": mean_std})
#     return pd.DataFrame(stats)
#
# summary_A = summarize(df_A, "XGB_Desc+Temp")
# summary_B = summarize(df_B, "XGB_Desc+Temp+Slope")
# summary_all = pd.concat([summary_A, summary_B], ignore_index=True)
#
# print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
# print(summary_all.to_string(index=False))
#
# # =========================================================
# # 9. 配对t检验（只对都有值的指标，且折数一致）
# # =========================================================
# t_test_results = []
# for metric in ["R2", "MSE", "RMSE", "MAE", "ARD(%)"]:
#     vals_A = df_A[metric].dropna().values
#     vals_B = df_B[metric].dropna().values
#     if len(vals_A) == len(vals_B) and len(vals_A) > 1:
#         t_stat, p_val = ttest_rel(vals_A, vals_B)
#         if metric in ["MSE", "RMSE", "MAE", "ARD(%)"]:
#             better = "ModelB" if np.mean(vals_B) < np.mean(vals_A) else "ModelA"
#             sig = p_val < 0.05
#         else:
#             better = "ModelB" if np.mean(vals_B) > np.mean(vals_A) else "ModelA"
#             sig = p_val < 0.05
#         t_test_results.append({
#             "Metric": metric,
#             "Mean_ModelA": f"{np.mean(vals_A):.4f}",
#             "Mean_ModelB": f"{np.mean(vals_B):.4f}",
#             "p-value": f"{p_val:.4e}",
#             "Significant(p<0.05)": sig,
#             "Better Model": better
#         })
#
# df_ttest = pd.DataFrame(t_test_results)
# print("\n========== Paired t-test (ModelA vs ModelB) ==========")
# print(df_ttest.to_string(index=False))
#
# # =========================================================
# # 10. 保存Excel
# # =========================================================
# with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
#     df_A.to_excel(writer, sheet_name="Fold_Metrics_ModelA", index=False)
#     df_B.to_excel(writer, sheet_name="Fold_Metrics_ModelB", index=False)
#     summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
#     df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)
#
#     # 保存运行参数
#     run_info = pd.DataFrame([
#         {"param": "n_outer_folds", "value": n_outer_folds},
#         {"param": "random_state", "value": random_state},
#         {"param": "xgb_params", "value": str(xgb_params)},
#         {"param": "n_desc_features", "value": len(used_feature_cols)},
#         {"param": "total_samples_modelA", "value": len(y_A_all)},
#         {"param": "total_samples_modelB", "value": len(y_B)},
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
# print(f"\n所有结果已保存至: {output_file}")


import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.model_selection import KFold
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from xgboost import XGBRegressor
from scipy.stats import ttest_rel

pd.set_option("display.float_format", "{:.10f}".format)
np.set_printoptions(suppress=True, precision=10)


# =========================================================
# 0. 全局设置
# =========================================================
descriptor_file = Path("selected_descriptors_with_Cp_mean_target.xlsx")
descriptor_sheet = "Selected_Features_Target"

data_file = Path("Cp_dataset_selected_by_two_k_with_interpolation.xlsx")
data_sheet = "Sheet1_selected"

predicted_slope_file = Path("Group_prediction_for_k1_k2_boiling_GBDT_with_predicted_slope.xlsx")
predicted_slope_sheet = "Predicted_Reference_Slope"
predicted_slope_col = "reference_slope_pred"

output_file = Path("XGB_descriptor_vs_descriptor_slope_5fold_CV.xlsx")

n_points_per_material = 8
temp_col = "T_K"
target_col = "property_value"

n_outer_folds = 5
random_state = 42

# XGBoost 固定参数（与原始代码一致）
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
def safe_relative_error_percent(y_true, y_pred):
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
        & (np.abs(y_true) > 1e-12)
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


def compute_metrics(y_true, y_pred, fold=None, model_name=None, dataset_name=None):
    """
    计算 R2、MSE、RMSE、MAE、ARD、最大相对误差、误差区间比例和数量。
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = np.isfinite(y_true) & np.isfinite(y_pred)

    y_true = y_true[mask]
    y_pred = y_pred[mask]

    base = {}
    if fold is not None:
        base["fold"] = fold
    if model_name is not None:
        base["model"] = model_name
    if dataset_name is not None:
        base["dataset"] = dataset_name

    if len(y_true) == 0:
        base.update({
            "n_points": 0,
            "R2": np.nan,
            "MSE": np.nan,
            "RMSE": np.nan,
            "MAE": np.nan,
            "ARD(%)": np.nan,
            "max_rel_err(%)": np.nan,
            "<1% ratio(%)": np.nan,
            "<5% ratio(%)": np.nan,
            "<10% ratio(%)": np.nan,
            "<1% count": 0.0,
            "<5% count": 0.0,
            "<10% count": 0.0,
        })
        return base

    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred) if len(y_true) > 1 else np.nan

    rel_err = safe_relative_error_percent(y_true, y_pred)

    if np.any(np.isfinite(rel_err)):
        ard = np.nanmean(rel_err)
        max_rel = np.nanmax(rel_err)

        count_1 = float(np.nansum(rel_err < 1.0))
        count_5 = float(np.nansum(rel_err < 5.0))
        count_10 = float(np.nansum(rel_err < 10.0))

        n_valid_rel = int(np.sum(np.isfinite(rel_err)))

        pct1 = count_1 / n_valid_rel * 100.0
        pct5 = count_5 / n_valid_rel * 100.0
        pct10 = count_10 / n_valid_rel * 100.0
    else:
        ard = np.nan
        max_rel = np.nan
        pct1 = np.nan
        pct5 = np.nan
        pct10 = np.nan
        count_1 = 0.0
        count_5 = 0.0
        count_10 = 0.0

    base.update({
        "n_points": len(y_true),
        "R2": r2,
        "MSE": mse,
        "RMSE": rmse,
        "MAE": mae,
        "ARD(%)": ard,
        "max_rel_err(%)": max_rel,
        "<1% ratio(%)": pct1,
        "<5% ratio(%)": pct5,
        "<10% ratio(%)": pct10,
        "<1% count": count_1,
        "<5% count": count_5,
        "<10% count": count_10,
    })

    return base


def summarize(df, name):
    stats = []

    for metric in [
        "R2",
        "MSE",
        "RMSE",
        "MAE",
        "ARD(%)",
        "max_rel_err(%)",
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

        stats.append({
            "Model": name,
            "Metric": metric,
            "Mean": mean_val,
            "Std": std_val,
            "Mean±Std": mean_std,
        })

    return pd.DataFrame(stats)


def make_prediction_df(
    fold,
    dataset_name,
    method,
    sample_indices,
    material_ids_array,
    temperatures_array,
    slope_array_for_samples,
    y_true,
    y_pred,
    original_row_indices_array,
):
    sample_indices = np.asarray(sample_indices, dtype=int)
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    rel_err = safe_relative_error_percent(y_true, y_pred)

    df = pd.DataFrame({
        "fold": fold,
        "dataset": dataset_name,
        "Method": method,
        "sample_index": sample_indices,
        "material_id": material_ids_array[sample_indices],
        "original_data_row_index": original_row_indices_array[sample_indices],
        "T_K": temperatures_array[sample_indices],
        "slope_pred": slope_array_for_samples[sample_indices],
        "y_true": y_true,
        "y_pred": y_pred,
        "error": y_pred - y_true,
        "absolute_error": np.abs(y_pred - y_true),
        "relative_error_percent": rel_err,
    })

    return df


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
df_slope = pd.read_excel(predicted_slope_file, sheet_name=predicted_slope_sheet)

print("描述符表行数:", len(df_desc))
print("Sheet1_selected 行数:", len(df_data))
print("预测斜率表行数:", len(df_slope))


# =========================================================
# 3. 描述符处理（与原始代码一致：第14-38列，删除全零列）
# =========================================================
feature_cols = df_desc.columns[13:38].tolist()   # 0-based, 13:38 对应 14-38列

df_features = df_desc[feature_cols].copy()
df_features = df_features.apply(pd.to_numeric, errors="coerce").fillna(df_features.mean())
df_features = df_features.dropna(axis=1, how="any")

nonzero_mask = df_features.abs().sum(axis=0) != 0

used_feature_cols = df_features.columns[nonzero_mask].tolist()
removed_zero_feature_cols = df_features.columns[~nonzero_mask].tolist()

df_features = df_features[used_feature_cols].copy()

print("有效描述符数量:", len(used_feature_cols))
print("删除全零描述符数量:", len(removed_zero_feature_cols))


# =========================================================
# 4. 对齐预测斜率（仅用于模型B）
# =========================================================
if predicted_slope_col not in df_slope.columns:
    raise ValueError(f"斜率表中没有列: {predicted_slope_col}")

df_slope[predicted_slope_col] = pd.to_numeric(
    df_slope[predicted_slope_col],
    errors="coerce",
)

if "original_material_index" in df_desc.columns and "original_material_index" in df_slope.columns:
    slope_map = (
        df_slope[["original_material_index", predicted_slope_col]]
        .drop_duplicates(subset=["original_material_index"])
        .set_index("original_material_index")[predicted_slope_col]
    )
    predicted_slope_per_material = df_desc["original_material_index"].map(slope_map).values.astype(float)
    print("使用 original_material_index 对齐预测斜率")
else:
    if len(df_desc) != len(df_slope):
        raise ValueError("描述符表与斜率表行数不一致且无法通过索引对齐")
    predicted_slope_per_material = df_slope[predicted_slope_col].values.astype(float)
    print("按行顺序对齐预测斜率")

valid_slope_mask = np.isfinite(predicted_slope_per_material)

print(f"有效斜率物质数: {valid_slope_mask.sum()}, 无效: {(~valid_slope_mask).sum()}")


# =========================================================
# 5. 检查实验数据完整性
# =========================================================
if len(df_data) % n_points_per_material != 0:
    raise ValueError("Sheet1 行数不是每个物质8行的整数倍")

n_materials_data = len(df_data) // n_points_per_material
n_materials_desc = len(df_features)

print(f"实验数据物质数: {n_materials_data}, 描述符物质数: {n_materials_desc}")

if n_materials_data != n_materials_desc:
    raise ValueError("描述符与实验数据物质数量不一致")


# =========================================================
# 6. 展开所有温度点数据
# 模型A特征: [描述符, T]
# 模型B特征: [描述符, T, 斜率]
# =========================================================
all_targets = []
material_ids = []
temperatures = []
desc_feat_list = []
slope_list = []
original_row_indices = []
point_id_in_material_list = []

for mat_idx in range(n_materials_desc):
    desc = df_features.iloc[mat_idx].values.astype(float)
    slope = predicted_slope_per_material[mat_idx]

    start = mat_idx * n_points_per_material
    end = start + n_points_per_material

    sub = df_data.iloc[start:end]

    T_vals = pd.to_numeric(sub[temp_col], errors="coerce").values.astype(float)
    Cp_vals = pd.to_numeric(sub[target_col], errors="coerce").values.astype(float)

    for local_i, (T, Cp) in enumerate(zip(T_vals, Cp_vals)):
        if not (np.isfinite(T) and np.isfinite(Cp)):
            continue

        all_targets.append(Cp)
        material_ids.append(mat_idx)
        temperatures.append(T)
        desc_feat_list.append(desc)
        slope_list.append(slope)
        original_row_indices.append(start + local_i)
        point_id_in_material_list.append(local_i)

y = np.array(all_targets, dtype=float)
material_ids = np.array(material_ids, dtype=int)
temperatures = np.array(temperatures, dtype=float)
desc_feat_array = np.array(desc_feat_list, dtype=float)
slope_array = np.array(slope_list, dtype=float)
original_row_indices = np.array(original_row_indices, dtype=int)
point_id_in_material_array = np.array(point_id_in_material_list, dtype=int)

# 构建模型A的特征矩阵
X_A = np.hstack([
    desc_feat_array,
    temperatures.reshape(-1, 1),
])

# 构建模型B的特征矩阵（需要过滤掉 slope 为 NaN 的点）
valid_slope_sample = np.isfinite(slope_array)

if not valid_slope_sample.all():
    print(f"警告: {np.sum(~valid_slope_sample)} 个样本因斜率无效将被模型B排除")

X_B_full = np.hstack([
    desc_feat_array,
    temperatures.reshape(-1, 1),
    slope_array.reshape(-1, 1),
])

X_B = X_B_full[valid_slope_sample]
y_B = y[valid_slope_sample]
material_ids_B = material_ids[valid_slope_sample]
temperatures_B = temperatures[valid_slope_sample]
slope_array_B = slope_array[valid_slope_sample]
original_row_indices_B = original_row_indices[valid_slope_sample]
point_id_in_material_B = point_id_in_material_array[valid_slope_sample]

# 模型A使用所有样本
X_A_all = X_A
y_A_all = y
material_ids_A = material_ids
temperatures_A = temperatures
slope_array_A = slope_array
original_row_indices_A = original_row_indices
point_id_in_material_A = point_id_in_material_array

print(f"模型A总样本数: {len(y_A_all)}")
print(f"模型B总样本数: {len(y_B)} (过滤后)")

A_feature_names = used_feature_cols + [temp_col]
B_feature_names = used_feature_cols + [temp_col, predicted_slope_col]

all_sample_indices_A = np.arange(len(y_A_all))
all_sample_indices_B = np.arange(len(y_B))


# =========================================================
# 7. 定义辅助函数：按物质索引列表构建训练/测试数据
# =========================================================
def get_data_for_materials(model_type, material_indices, return_indices=False):
    """
    model_type: 'A' 或 'B'
    material_indices: 物质索引列表

    返回:
        return_indices=False: X, y
        return_indices=True : X, y, sample_indices
    """
    material_indices = np.asarray(material_indices, dtype=int)

    if model_type == "A":
        mask = np.isin(material_ids_A, material_indices)
        sample_indices = np.where(mask)[0]

        if return_indices:
            return X_A_all[mask], y_A_all[mask], sample_indices
        return X_A_all[mask], y_A_all[mask]

    elif model_type == "B":
        mask = np.isin(material_ids_B, material_indices)
        sample_indices = np.where(mask)[0]

        if return_indices:
            return X_B[mask], y_B[mask], sample_indices
        return X_B[mask], y_B[mask]

    else:
        raise ValueError("model_type 必须是 'A' 或 'B'")


# =========================================================
# 8. 外层5折交叉验证（按物质划分，对两个模型使用相同的物质划分）
# =========================================================
all_materials = np.unique(material_ids_A)

if len(all_materials) < n_outer_folds:
    raise ValueError(
        f"物质数 {len(all_materials)} 小于 n_outer_folds={n_outer_folds}，无法做 5-fold。"
    )

kf = KFold(
    n_splits=n_outer_folds,
    shuffle=True,
    random_state=random_state,
)

metrics_A = []
metrics_B = []

fold_test_prediction_dfs = []
fold_all_data_prediction_dfs = []
fold_all_data_count_records = []
fold_info_records = []

feature_importance_A_records = []
feature_importance_B_records = []

for fold, (train_mat_idx, test_mat_idx) in enumerate(kf.split(all_materials), start=1):
    print(f"\n========== Fold {fold}/{n_outer_folds} ==========")

    train_mats = all_materials[train_mat_idx]
    test_mats = all_materials[test_mat_idx]

    print("训练物质数:", len(train_mats))
    print("测试物质数:", len(test_mats))

    # -----------------------------------------------------
    # 模型A：XGB_Desc+Temp
    # -----------------------------------------------------
    X_train_A, y_train_A, train_sample_indices_A = get_data_for_materials(
        "A",
        train_mats,
        return_indices=True,
    )
    X_test_A, y_test_A, test_sample_indices_A = get_data_for_materials(
        "A",
        test_mats,
        return_indices=True,
    )

    model_A = XGBRegressor(**xgb_params)
    model_A.fit(X_train_A, y_train_A)

    y_pred_A_test = model_A.predict(X_test_A)
    y_pred_A_all = model_A.predict(X_A_all)

    # -----------------------------------------------------
    # 模型B：XGB_Desc+Temp+Slope
    # 只使用斜率有效样本
    # -----------------------------------------------------
    X_train_B, y_train_B, train_sample_indices_B = get_data_for_materials(
        "B",
        train_mats,
        return_indices=True,
    )
    X_test_B, y_test_B, test_sample_indices_B = get_data_for_materials(
        "B",
        test_mats,
        return_indices=True,
    )

    if len(y_train_B) == 0:
        print(f"  警告: 折 {fold} 模型B无训练样本，跳过")
        model_B = None
        y_pred_B_test = np.full_like(y_test_B, np.nan, dtype=float)
        y_pred_B_all = np.full_like(y_B, np.nan, dtype=float)
    else:
        model_B = XGBRegressor(**xgb_params)
        model_B.fit(X_train_B, y_train_B)

        y_pred_B_test = model_B.predict(X_test_B) if len(y_test_B) > 0 else np.array([], dtype=float)
        y_pred_B_all = model_B.predict(X_B)

    # -----------------------------------------------------
    # 测试集评价指标
    # -----------------------------------------------------
    m_A = compute_metrics(
        y_test_A,
        y_pred_A_test,
        fold=fold,
        model_name="XGB_Desc+Temp",
        dataset_name="test",
    )

    m_B = compute_metrics(
        y_test_B,
        y_pred_B_test,
        fold=fold,
        model_name="XGB_Desc+Temp+Slope",
        dataset_name="test",
    )

    metrics_A.append(m_A)
    metrics_B.append(m_B)

    print(
        "ModelA XGB_Desc+Temp test: "
        f"R2={m_A['R2']:.6f}, "
        f"MSE={m_A['MSE']:.6f}, "
        f"RMSE={m_A['RMSE']:.6f}, "
        f"MAE={m_A['MAE']:.6f}, "
        f"ARD={m_A['ARD(%)']:.6f}%"
    )

    print(
        "ModelB XGB_Desc+Temp+Slope test: "
        f"R2={m_B['R2']:.6f}, "
        f"MSE={m_B['MSE']:.6f}, "
        f"RMSE={m_B['RMSE']:.6f}, "
        f"MAE={m_B['MAE']:.6f}, "
        f"ARD={m_B['ARD(%)']:.6f}%"
    )

    # -----------------------------------------------------
    # 新增：每个 fold 模型预测完整数据集并统计偏差数量
    # 模型A：完整数据集为所有有效 Cp/T 点
    # 模型B：完整数据集为 slope 有效的 Cp/T 点
    # -----------------------------------------------------
    count_A_all = count_error_thresholds(y_A_all, y_pred_A_all)
    count_B_all = count_error_thresholds(y_B, y_pred_B_all)

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "XGB_Desc+Temp",
        **count_A_all,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "XGB_Desc+Temp+Slope",
        **count_B_all,
    })

    print("\nModelA fold model predicts ALL available data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "XGB_Desc+Temp",
        **count_A_all,
    }]).to_string(index=False))

    print("\nModelB fold model predicts ALL slope-valid data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "XGB_Desc+Temp+Slope",
        **count_B_all,
    }]).to_string(index=False))

    # -----------------------------------------------------
    # 保存测试集预测明细
    # -----------------------------------------------------
    df_test_A = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="XGB_Desc+Temp",
        sample_indices=test_sample_indices_A,
        material_ids_array=material_ids_A,
        temperatures_array=temperatures_A,
        slope_array_for_samples=slope_array_A,
        y_true=y_test_A,
        y_pred=y_pred_A_test,
        original_row_indices_array=original_row_indices_A,
    )
    df_test_A["point_id_in_material"] = point_id_in_material_A[test_sample_indices_A]

    df_test_B = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="XGB_Desc+Temp+Slope",
        sample_indices=test_sample_indices_B,
        material_ids_array=material_ids_B,
        temperatures_array=temperatures_B,
        slope_array_for_samples=slope_array_B,
        y_true=y_test_B,
        y_pred=y_pred_B_test,
        original_row_indices_array=original_row_indices_B,
    )
    df_test_B["point_id_in_material"] = point_id_in_material_B[test_sample_indices_B]

    fold_test_prediction_dfs.append(df_test_A)
    fold_test_prediction_dfs.append(df_test_B)

    # -----------------------------------------------------
    # 保存完整数据集预测明细
    # -----------------------------------------------------
    df_all_A = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="XGB_Desc+Temp",
        sample_indices=all_sample_indices_A,
        material_ids_array=material_ids_A,
        temperatures_array=temperatures_A,
        slope_array_for_samples=slope_array_A,
        y_true=y_A_all,
        y_pred=y_pred_A_all,
        original_row_indices_array=original_row_indices_A,
    )
    df_all_A["point_id_in_material"] = point_id_in_material_A[all_sample_indices_A]

    df_all_B = make_prediction_df(
        fold=fold,
        dataset_name="all_data_slope_valid",
        method="XGB_Desc+Temp+Slope",
        sample_indices=all_sample_indices_B,
        material_ids_array=material_ids_B,
        temperatures_array=temperatures_B,
        slope_array_for_samples=slope_array_B,
        y_true=y_B,
        y_pred=y_pred_B_all,
        original_row_indices_array=original_row_indices_B,
    )
    df_all_B["point_id_in_material"] = point_id_in_material_B[all_sample_indices_B]

    fold_all_data_prediction_dfs.append(df_all_A)
    fold_all_data_prediction_dfs.append(df_all_B)

    # -----------------------------------------------------
    # 保存特征重要性
    # -----------------------------------------------------
    if hasattr(model_A, "feature_importances_"):
        for feature_name, importance in zip(A_feature_names, model_A.feature_importances_):
            feature_importance_A_records.append({
                "fold": fold,
                "feature": feature_name,
                "importance": importance,
            })

    if model_B is not None and hasattr(model_B, "feature_importances_"):
        for feature_name, importance in zip(B_feature_names, model_B.feature_importances_):
            feature_importance_B_records.append({
                "fold": fold,
                "feature": feature_name,
                "importance": importance,
            })

    fold_info_records.append({
        "fold": fold,
        "n_train_materials": len(train_mats),
        "n_test_materials": len(test_mats),
        "n_train_samples_ModelA": len(y_train_A),
        "n_test_samples_ModelA": len(y_test_A),
        "n_train_samples_ModelB": len(y_train_B),
        "n_test_samples_ModelB": len(y_test_B),
        "n_features_ModelA": X_train_A.shape[1],
        "n_features_ModelB": X_train_B.shape[1] if len(X_train_B) > 0 else len(B_feature_names),
        "ModelB_has_training_samples": len(y_train_B) > 0,
    })


# =========================================================
# 9. 汇总统计（均值±标准差）
# =========================================================
df_A = pd.DataFrame(metrics_A)
df_B = pd.DataFrame(metrics_B)

summary_A = summarize(df_A, "XGB_Desc+Temp")
summary_B = summarize(df_B, "XGB_Desc+Temp+Slope")

summary_all = pd.concat(
    [summary_A, summary_B],
    ignore_index=True,
)

print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
print(summary_all.to_string(index=False))


# =========================================================
# 10. 配对t检验
# =========================================================
t_test_results = []

for metric in ["R2", "MSE", "RMSE", "MAE", "ARD(%)"]:
    vals_A = df_A[metric].values.astype(float)
    vals_B = df_B[metric].values.astype(float)

    valid = np.isfinite(vals_A) & np.isfinite(vals_B)

    vals_A_valid = vals_A[valid]
    vals_B_valid = vals_B[valid]

    if len(vals_A_valid) > 1:
        t_stat, p_val = ttest_rel(vals_A_valid, vals_B_valid)

        if metric in ["MSE", "RMSE", "MAE", "ARD(%)"]:
            better = "ModelB" if np.mean(vals_B_valid) < np.mean(vals_A_valid) else "ModelA"
        else:
            better = "ModelB" if np.mean(vals_B_valid) > np.mean(vals_A_valid) else "ModelA"

        sig = p_val < 0.05

        t_test_results.append({
            "Metric": metric,
            "Mean_ModelA": f"{np.mean(vals_A_valid):.4f}",
            "Mean_ModelB": f"{np.mean(vals_B_valid):.4f}",
            "p-value": f"{p_val:.4e}",
            "Significant(p<0.05)": sig,
            "Better Model": better,
            "n_valid_fold_pairs": len(vals_A_valid),
        })

df_ttest = pd.DataFrame(t_test_results)

print("\n========== Paired t-test (ModelA vs ModelB) ==========")
print(df_ttest.to_string(index=False))


# =========================================================
# 11. 完整数据集预测偏差数量统计汇总
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
# 12. 整理输出表
# =========================================================
df_fold_test_predictions = pd.concat(fold_test_prediction_dfs, ignore_index=True)
df_fold_all_data_predictions = pd.concat(fold_all_data_prediction_dfs, ignore_index=True)

# 补充物质/原始数据信息
extra_cols = [
    "original_material_index",
    "compound_name",
    "cas",
    "formula",
    "SMILES",
    "smiles",
    "pubchem_cid",
    "material_key",
    "phase",
    "boiling_T_K",
    "critical_T_K",
]

for df_pred in [df_fold_test_predictions, df_fold_all_data_predictions]:
    for col in extra_cols:
        if col in df_data.columns:
            values = []
            for row_idx in df_pred["original_data_row_index"].values:
                values.append(df_data.iloc[int(row_idx)][col])
            df_pred[col] = values

df_fold_info = pd.DataFrame(fold_info_records)
df_feature_importance_A = pd.DataFrame(feature_importance_A_records)
df_feature_importance_B = pd.DataFrame(feature_importance_B_records)

df_used_features = pd.DataFrame({
    "used_feature": used_feature_cols,
})

df_removed_zero_features = pd.DataFrame({
    "removed_zero_feature": removed_zero_feature_cols,
})

df_slope_info = pd.DataFrame({
    "material_id": np.arange(n_materials_desc),
    "slope_pred": predicted_slope_per_material,
    "valid_slope": valid_slope_mask,
})

for col in extra_cols:
    if col in df_desc.columns:
        df_slope_info[col] = df_desc[col].values


# =========================================================
# 13. 模型结构汇总
# =========================================================
df_model_structure = pd.DataFrame([
    {
        "项目": "预测对象",
        "内容": "定压热容 Cp / property_value",
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
        "项目": "实验数据文件",
        "内容": str(data_file),
    },
    {
        "项目": "实验数据 sheet",
        "内容": data_sheet,
    },
    {
        "项目": "slope 文件",
        "内容": str(predicted_slope_file),
    },
    {
        "项目": "slope sheet",
        "内容": predicted_slope_sheet,
    },
    {
        "项目": "slope 列",
        "内容": predicted_slope_col,
    },
    {
        "项目": "交叉验证方式",
        "内容": f"{n_outer_folds}-fold KFold，按物质划分，shuffle=True，random_state={random_state}",
    },
    {
        "项目": "方法1",
        "内容": "XGB_Desc+Temp：XGBRegressor 直接预测 Cp，输入 [descriptors, T]",
    },
    {
        "项目": "方法2",
        "内容": "XGB_Desc+Temp+Slope：XGBRegressor 直接预测 Cp，输入 [descriptors, T, reference_slope_pred]",
    },
    {
        "项目": "是否包含子模型",
        "内容": "当前代码不训练子模型；只读取外部 GBDT 预测得到的 reference_slope_pred",
    },
    {
        "项目": "子模型预测对象",
        "内容": "reference_slope_pred，用作方法2额外输入特征",
    },
    {
        "项目": "子模型类型",
        "内容": "外部文件名显示为 GBDT；本代码只读取其预测结果，不在当前脚本内训练",
    },
    {
        "项目": "子模型参数",
        "内容": "当前脚本无法从 Excel 预测结果文件中恢复 GBDT 参数；仅保存 slope 预测结果",
    },
    {
        "项目": "子模型输入特征",
        "内容": "当前脚本无法从 Excel 预测结果文件中恢复；一般应来自基团信息、沸点参考点或 k1/k2 插值相关特征",
    },
    {
        "项目": "slope 构造方式",
        "内容": "从外部文件读取 reference_slope_pred，作为方法2的独立输入特征；本代码没有再乘以 T",
    },
    {
        "项目": "baseline 构造方式",
        "内容": "无显式 baseline + residual 结构；两个方法均为直接 XGB 回归",
    },
    {
        "项目": "residual 构造方式",
        "内容": "无 residual 修正模型",
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
        "项目": "方法1最终输入特征",
        "内容": f"[{len(used_feature_cols)} 个描述符, T]，总维度 {len(used_feature_cols) + 1}",
    },
    {
        "项目": "方法2最终输入特征",
        "内容": f"[{len(used_feature_cols)} 个描述符, T, reference_slope_pred]，总维度 {len(used_feature_cols) + 2}",
    },
    {
        "项目": "模型B样本过滤",
        "内容": "模型B 仅使用 slope 有效样本；完整数据预测统计也基于 slope 有效样本",
    },
    {
        "项目": "偏差数量统计口径",
        "内容": "每个 fold 训练出的模型都预测对应方法的完整可用数据集，统计相对误差 <1%、<5%、<10% 点数，再对 5 个 fold 的数量取平均",
    },
])


df_run_info = pd.DataFrame([
    {"param": "descriptor_file", "value": str(descriptor_file)},
    {"param": "descriptor_sheet", "value": descriptor_sheet},
    {"param": "data_file", "value": str(data_file)},
    {"param": "data_sheet", "value": data_sheet},
    {"param": "predicted_slope_file", "value": str(predicted_slope_file)},
    {"param": "predicted_slope_sheet", "value": predicted_slope_sheet},
    {"param": "predicted_slope_col", "value": predicted_slope_col},
    {"param": "n_outer_folds", "value": n_outer_folds},
    {"param": "random_state", "value": random_state},
    {"param": "xgb_params", "value": str(xgb_params)},
    {"param": "n_desc_features", "value": len(used_feature_cols)},
    {"param": "total_samples_modelA", "value": len(y_A_all)},
    {"param": "total_samples_modelB_slope_valid", "value": len(y_B)},
    {"param": "n_materials_data", "value": n_materials_data},
    {"param": "n_materials_desc", "value": n_materials_desc},
    {"param": "n_valid_slope_materials", "value": int(valid_slope_mask.sum())},
    {"param": "n_invalid_slope_materials", "value": int((~valid_slope_mask).sum())},
    {
        "param": "relative_error_definition",
        "value": "abs((y_pred - y_true) / y_true) * 100; abs(y_true)<=1e-12 -> NaN",
    },
    {
        "param": "full_data_count_rule",
        "value": "Each fold model predicts the whole available dataset for that method; count rel_err <1%, <5%, <10%; then average counts over 5 folds.",
    },
])


# =========================================================
# 14. 保存Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    # 原有核心输出
    df_A.to_excel(writer, sheet_name="Fold_Metrics_ModelA", index=False)
    df_B.to_excel(writer, sheet_name="Fold_Metrics_ModelB", index=False)
    summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
    df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)
    df_run_info.to_excel(writer, sheet_name="Run_Info", index=False)

    # 新增输出
    df_fold_test_predictions.to_excel(writer, sheet_name="fold_test_predictions", index=False)
    df_fold_all_data_predictions.to_excel(writer, sheet_name="fold_all_data_predictions", index=False)
    df_fold_all_data_count_summary.to_excel(writer, sheet_name="fold_all_data_count_summary", index=False)
    df_final_average_summary.to_excel(writer, sheet_name="final_average_summary", index=False)

    df_feature_importance_A.to_excel(writer, sheet_name="feature_importance_ModelA", index=False)
    df_feature_importance_B.to_excel(writer, sheet_name="feature_importance_ModelB", index=False)

    df_fold_info.to_excel(writer, sheet_name="Fold_Info", index=False)
    df_used_features.to_excel(writer, sheet_name="Used_Descriptors", index=False)
    df_removed_zero_features.to_excel(writer, sheet_name="Removed_Zero_Descriptors", index=False)
    df_slope_info.to_excel(writer, sheet_name="slope_info", index=False)
    df_model_structure.to_excel(writer, sheet_name="model_structure", index=False)

    format_excel(writer)

print(f"\n所有结果已保存至: {output_file}")


# =========================================================
# 15. 最终方便复制输出
# =========================================================
def get_final_counts(method_name):
    row = df_final_average_summary[df_final_average_summary["Method"] == method_name]

    if row.empty:
        return np.nan, np.nan, np.nan

    row = row.iloc[0]

    return (
        row["mean_count_rel_err_lt_1pct"],
        row["mean_count_rel_err_lt_5pct"],
        row["mean_count_rel_err_lt_10pct"],
    )


modelA_1, modelA_5, modelA_10 = get_final_counts("XGB_Desc+Temp")
modelB_1, modelB_5, modelB_10 = get_final_counts("XGB_Desc+Temp+Slope")

print("\n方法1 全数据预测偏差 1%，5%，10%分别为：")
print(modelA_1)
print(modelA_5)
print(modelA_10)

print("\n方法2 全数据预测偏差 1%，5%，10%分别为：")
print(modelB_1)
print(modelB_5)
print(modelB_10)


# =========================================================
# 16. 代码结构打印
# =========================================================
print("\n========== 当前代码结构简要汇总 ==========")
print("预测对象：Cp / property_value")
print(f"描述符文件：{descriptor_file}")
print(f"实验数据文件：{data_file}")
print(f"slope 文件：{predicted_slope_file}")
print(f"sheet 名称：{descriptor_sheet}, {data_sheet}, {predicted_slope_sheet}")
print(f"交叉验证：{n_outer_folds}-fold，按物质划分")
print("方法1：XGB_Desc+Temp，XGBRegressor，输入 [descriptors, T]")
print("方法2：XGB_Desc+Temp+Slope，XGBRegressor，输入 [descriptors, T, reference_slope_pred]")
print("子模型：当前代码不训练子模型，读取外部 GBDT 预测的 reference_slope_pred")
print(f"子模型预测列：{predicted_slope_col}")
print("子模型参数：当前代码无法从预测结果文件恢复，仅保存 slope 预测值")
print("slope 构造：直接读取 reference_slope_pred，作为方法2额外输入特征；没有乘以 T")
print("baseline 构造：无")
print("residual 模型：无")
print(f"最终模型：XGBRegressor，参数：{xgb_params}")
print("方法1最终输入：[descriptors, T]")
print("方法2最终输入：[descriptors, T, reference_slope_pred]")
print("模型B样本口径：模型B 仅使用 slope 有效样本；完整数据预测统计也基于 slope 有效样本")
print("偏差统计口径：每个 fold 模型预测对应方法的完整可用数据集，统计 <1%、<5%、<10% 点数，再对 5 个 fold 取平均")