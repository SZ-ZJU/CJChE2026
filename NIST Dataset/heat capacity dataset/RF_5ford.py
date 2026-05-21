# import pandas as pd
# import numpy as np
# from pathlib import Path
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
# from sklearn.model_selection import KFold
# from scipy.stats import ttest_rel
#
# # =========================================================
# # 0. 设置与路径
# # =========================================================
# pd.set_option("display.float_format", "{:.10f}".format)
# np.set_printoptions(suppress=True, precision=10)
#
# file_path = Path("Cp_dataset_selected_by_two_k_with_interpolation.xlsx")
# groups_sheet = "groups_selected"
# data_sheet = "Sheet1_selected"
#
# predicted_slope_file = Path("Group_prediction_for_k1_k2_boiling_GBDT_with_predicted_slope.xlsx")
# predicted_slope_sheet = "Predicted_Reference_Slope"
# predicted_slope_col = "reference_slope_pred"
#
# output_file = Path("Cp_RF_5fold_CV_comparison.xlsx")
#
# n_points_per_material = 8
# temp_col = "T_K"
# target_col = "property_value"
# random_state = 42
#
# rf_params = {
#     "n_estimators": 500,
#     "max_depth": None,
#     "min_samples_split": 2,
#     "min_samples_leaf": 1,
#     "max_features": "sqrt",
#     "bootstrap": True,
#     "random_state": 43,
#     "n_jobs": -1,
# }
#
# n_splits = 5
#
# # =========================================================
# # 1. 读取并准备原始数据
# # =========================================================
# df_groups_raw = pd.read_excel(file_path, sheet_name=groups_sheet)
# df_data = pd.read_excel(file_path, sheet_name=data_sheet)
#
# print("groups 表行数:", len(df_groups_raw))
# print("Sheet1 数据行数:", len(df_data))
#
# group_start_idx = 2
# group_end_idx = 221
# group_cols_raw = df_groups_raw.columns[group_start_idx:group_end_idx].tolist()
#
# exclude_cols = {
#     "original_material_index", "compound_name", "cas", "formula",
#     "SMILES", "smiles", "pubchem_cid", "material_key", "phase",
#     "boiling_T_K", "critical_T_K"
# }
# group_cols_raw = [c for c in group_cols_raw if c not in exclude_cols]
#
# df_groups = df_groups_raw[group_cols_raw].copy()
# df_groups = df_groups.apply(pd.to_numeric, errors="coerce").fillna(0.0)
#
# nonzero_mask = df_groups.abs().sum(axis=0) != 0
# used_group_cols = df_groups.columns[nonzero_mask].tolist()
# df_groups_used = df_groups[used_group_cols].copy()
# print("有效基团数量:", len(used_group_cols))
#
# if len(df_data) % n_points_per_material != 0:
#     raise ValueError(f"数据行数 {len(df_data)} 不是 {n_points_per_material} 的倍数")
# n_materials = len(df_data) // n_points_per_material
# print("物质总数:", n_materials)
#
# # =========================================================
# # 2. 读取并准备预测斜率
# # =========================================================
# if not predicted_slope_file.exists():
#     raise FileNotFoundError(f"未找到预测斜率文件: {predicted_slope_file}")
#
# df_slope = pd.read_excel(predicted_slope_file, sheet_name=predicted_slope_sheet)
# if predicted_slope_col not in df_slope.columns:
#     raise ValueError(f"斜率文件中没有列: {predicted_slope_col}")
#
# df_slope[predicted_slope_col] = pd.to_numeric(df_slope[predicted_slope_col], errors="coerce")
#
# if "original_material_index" in df_groups_raw.columns and "original_material_index" in df_slope.columns:
#     slope_map = (df_slope[["original_material_index", predicted_slope_col]]
#                  .drop_duplicates(subset=["original_material_index"])
#                  .set_index("original_material_index")[predicted_slope_col])
#     df_groups_raw["slope_pred"] = df_groups_raw["original_material_index"].map(slope_map)
# else:
#     if len(df_groups_raw) != len(df_slope):
#         raise ValueError("无法对齐斜率表且行数不一致")
#     df_groups_raw["slope_pred"] = df_slope[predicted_slope_col].values
#
# valid_slope = np.isfinite(df_groups_raw["slope_pred"].values)
# if not valid_slope.all():
#     print(f"删除 {np.sum(~valid_slope)} 个斜率无效的物质")
#     keep_indices = np.where(valid_slope)[0]
#     df_groups_raw = df_groups_raw.iloc[keep_indices].reset_index(drop=True)
#     df_groups_used = df_groups_used.iloc[keep_indices].reset_index(drop=True)
#     keep_data_rows = []
#     for mat_idx in keep_indices:
#         start = mat_idx * n_points_per_material
#         end = start + n_points_per_material
#         keep_data_rows.extend(range(start, end))
#     df_data = df_data.iloc[keep_data_rows].reset_index(drop=True)
#     n_materials = len(keep_indices)
#     slope_values = df_groups_raw["slope_pred"].values
# else:
#     slope_values = df_groups_raw["slope_pred"].values
#
# print("最终有效物质数:", n_materials)
#
# # =========================================================
# # 3. 构建每个物质的数据块
# # =========================================================
# material_features = []
# material_targets = []
# material_ids = list(range(n_materials))
#
# for mat_idx in range(n_materials):
#     group_vec = df_groups_used.iloc[mat_idx].values.astype(float)
#     slope = slope_values[mat_idx]
#     material_features.append((group_vec, slope))
#
#     start = mat_idx * n_points_per_material
#     end = start + n_points_per_material
#     sub = df_data.iloc[start:end]
#     T_vals = pd.to_numeric(sub[temp_col], errors="coerce").values
#     Cp_vals = pd.to_numeric(sub[target_col], errors="coerce").values
#     points = [(t, cp) for t, cp in zip(T_vals, Cp_vals) if np.isfinite(t) and np.isfinite(cp)]
#     material_targets.append(points)
#
# # =========================================================
# # 4. 辅助函数：根据物质索引构建 X, y
# # =========================================================
# def build_Xy(material_indices, use_slope=True):
#     X_list = []
#     y_list = []
#     for mid in material_indices:
#         group_vec, slope = material_features[mid]
#         points = material_targets[mid]
#         for T, Cp in points:
#             if use_slope:
#                 feat = np.concatenate([group_vec, [T, slope]])
#             else:
#                 feat = np.concatenate([group_vec, [T]])
#             X_list.append(feat)
#             y_list.append(Cp)
#     return np.array(X_list, dtype=float), np.array(y_list, dtype=float)
#
# feat_names_no_slope = used_group_cols + [temp_col]
# feat_names_with_slope = used_group_cols + [temp_col, predicted_slope_col]
#
# # =========================================================
# # 5. 5 折交叉验证（按物质）
# # =========================================================
# kf = KFold(n_splits=n_splits, shuffle=True, random_state=random_state)
#
# metrics_no_slope = []
# metrics_with_slope = []
# fold_results = []
#
# for fold, (train_idx, test_idx) in enumerate(kf.split(material_ids)):
#     print(f"\n========== Fold {fold+1}/{n_splits} ==========")
#     train_materials = [material_ids[i] for i in train_idx]
#     test_materials = [material_ids[i] for i in test_idx]
#
#     X_train_no, y_train_no = build_Xy(train_materials, use_slope=False)
#     X_test_no, y_test_no = build_Xy(test_materials, use_slope=False)
#     X_train_with, y_train_with = build_Xy(train_materials, use_slope=True)
#     X_test_with, y_test_with = build_Xy(test_materials, use_slope=True)
#
#     model_no = RandomForestRegressor(**rf_params)
#     model_no.fit(X_train_no, y_train_no)
#     y_pred_no = model_no.predict(X_test_no)
#
#     model_with = RandomForestRegressor(**rf_params)
#     model_with.fit(X_train_with, y_train_with)
#     y_pred_with = model_with.predict(X_test_with)
#
#     def compute_metrics(y_true, y_pred, name_prefix=""):
#         y_true = np.asarray(y_true)
#         y_pred = np.asarray(y_pred)
#         mse = mean_squared_error(y_true, y_pred)
#         rmse = np.sqrt(mse)
#         mae = mean_absolute_error(y_true, y_pred)
#         r2 = r2_score(y_true, y_pred) if len(y_true) > 1 else np.nan
#
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
#             "fold": fold+1,
#             "model": name_prefix,
#             "n_test": len(y_true),
#             "R2": r2,
#             "MSE": mse,
#             "RMSE": rmse,
#             "MAE": mae,
#             "ARD(%)": ard,
#             "max_rel_err(%)": max_rel,
#             "≤1% ratio(%)": pct1,
#             "≤5% ratio(%)": pct5,
#             "≤10% ratio(%)": pct10,
#         }
#
#     m_no = compute_metrics(y_test_no, y_pred_no, "no_slope")
#     m_with = compute_metrics(y_test_with, y_pred_with, "with_slope")
#     metrics_no_slope.append(m_no)
#     metrics_with_slope.append(m_with)
#
#     fold_results.append({
#         "fold": fold+1,
#         "train_materials": train_materials,
#         "test_materials": test_materials,
#         "y_test_no": y_test_no,
#         "y_pred_no": y_pred_no,
#         "y_test_with": y_test_with,
#         "y_pred_with": y_pred_with,
#     })
#
# # =========================================================
# # 6. 汇总指标并计算均值±标准差
# # =========================================================
# df_no = pd.DataFrame(metrics_no_slope)
# df_with = pd.DataFrame(metrics_with_slope)
#
# def summarize(df, model_name):
#     stats = []
#     for metric in ["R2", "MSE", "RMSE", "MAE", "ARD(%)", "max_rel_err(%)", "≤1% ratio(%)", "≤5% ratio(%)", "≤10% ratio(%)"]:
#         values = df[metric].dropna().values
#         if len(values) == 0:
#             mean_std = "NaN"
#         else:
#             mean_val = np.mean(values)
#             std_val = np.std(values, ddof=1)
#             mean_std = f"{mean_val:.4f} ± {std_val:.4f}"
#         stats.append({"Model": model_name, "Metric": metric, "Mean±Std": mean_std})
#     return pd.DataFrame(stats)
#
# summary_no = summarize(df_no, "No Slope")
# summary_with = summarize(df_with, "With Slope")
# summary_all = pd.concat([summary_no, summary_with], ignore_index=True)
#
# print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
# print(summary_all.to_string(index=False))
#
# # =========================================================
# # 7. 配对 t 检验（可选加入 MSE 检验）
# # =========================================================
# t_test_results = []
# for metric in ["R2", "MSE", "RMSE", "MAE", "ARD(%)"]:
#     val_no = df_no[metric].dropna().values
#     val_with = df_with[metric].dropna().values
#     if len(val_no) == len(val_with) and len(val_no) > 1:
#         t_stat, p_val = ttest_rel(val_no, val_with)
#         # 判断哪个模型更好（对于 MSE/RMSE/MAE/ARD 越小越好，R2越大越好）
#         if metric in ["MSE", "RMSE", "MAE", "ARD(%)"]:
#             better = "with_slope" if np.mean(val_with) < np.mean(val_no) else "no_slope"
#             significant = p_val < 0.05
#         else:
#             better = "with_slope" if np.mean(val_with) > np.mean(val_no) else "no_slope"
#             significant = p_val < 0.05
#         t_test_results.append({
#             "Metric": metric,
#             "Mean_no_slope": f"{np.mean(val_no):.4f}",
#             "Mean_with_slope": f"{np.mean(val_with):.4f}",
#             "p-value": f"{p_val:.4e}",
#             "Significant (p<0.05)": significant,
#             "Better model": better
#         })
#
# df_ttest = pd.DataFrame(t_test_results)
# print("\n========== Paired t-test between No Slope vs With Slope ==========")
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
#     # 保存每折预测值（可选）
#     all_preds = []
#     for fr in fold_results:
#         f = fr["fold"]
#         for yt, yp in zip(fr["y_test_no"], fr["y_pred_no"]):
#             all_preds.append({"fold": f, "model": "no_slope", "true": yt, "pred": yp})
#         for yt, yp in zip(fr["y_test_with"], fr["y_pred_with"]):
#             all_preds.append({"fold": f, "model": "with_slope", "true": yt, "pred": yp})
#     df_preds = pd.DataFrame(all_preds)
#     df_preds.to_excel(writer, sheet_name="All_Fold_Predictions", index=False)
#
#     # 全数据最终模型的特征重要性（with_slope）
#     X_all_with, y_all_with = build_Xy(material_ids, use_slope=True)
#     final_model = RandomForestRegressor(**rf_params)
#     final_model.fit(X_all_with, y_all_with)
#     imp = pd.DataFrame({"feature": feat_names_with_slope, "importance": final_model.feature_importances_})
#     imp = imp.sort_values("importance", ascending=False)
#     imp.to_excel(writer, sheet_name="Feature_Importance_FullData", index=False)
#
#     params_df = pd.DataFrame([{"param": k, "value": v} for k, v in rf_params.items()])
#     params_df.to_excel(writer, sheet_name="RF_Params", index=False)
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

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.model_selection import KFold
from scipy.stats import ttest_rel

# =========================================================
# 0. 设置与路径
# =========================================================
pd.set_option("display.float_format", "{:.10f}".format)
np.set_printoptions(suppress=True, precision=10)

file_path = Path("Cp_dataset_selected_by_two_k_with_interpolation.xlsx")
groups_sheet = "groups_selected"
data_sheet = "Sheet1_selected"

predicted_slope_file = Path("Group_prediction_for_k1_k2_boiling_GBDT_with_predicted_slope.xlsx")
predicted_slope_sheet = "Predicted_Reference_Slope"
predicted_slope_col = "reference_slope_pred"

output_file = Path("Cp_RF_5fold_CV_comparison.xlsx")

n_points_per_material = 8
temp_col = "T_K"
target_col = "property_value"
random_state = 42

rf_params = {
    "n_estimators": 500,
    "max_depth": None,
    "min_samples_split": 2,
    "min_samples_leaf": 1,
    "max_features": "sqrt",
    "bootstrap": True,
    "random_state": 43,
    "n_jobs": -1,
}

n_splits = 5


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
    valid = np.isfinite(y_true) & np.isfinite(y_pred) & (np.abs(y_true) > 1e-12)

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


def compute_metrics(y_true, y_pred, fold, name_prefix=""):
    """
    保留原始测试集评价指标，同时使用统一相对误差定义：
        abs((y_pred - y_true) / y_true) * 100

    abs(y_true) <= 1e-12 的点 relative_error 记为 NaN。
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true = y_true[mask]
    y_pred = y_pred[mask]

    if len(y_true) == 0:
        return {
            "fold": fold,
            "model": name_prefix,
            "n_test": 0,
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
        }

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

    return {
        "fold": fold,
        "model": name_prefix,
        "n_test": len(y_true),
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
    }


def summarize(df, model_name):
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
        values = df[metric].dropna().values

        if len(values) == 0:
            mean_val = np.nan
            std_val = np.nan
            mean_std = "NaN"
        elif len(values) == 1:
            mean_val = float(np.mean(values))
            std_val = np.nan
            mean_std = f"{mean_val:.4f} ± NaN"
        else:
            mean_val = float(np.mean(values))
            std_val = float(np.std(values, ddof=1))
            mean_std = f"{mean_val:.4f} ± {std_val:.4f}"

        stats.append({
            "Model": model_name,
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
    meta_list,
    y_true,
    y_pred,
):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    rel_err = safe_relative_error_percent(y_true, y_pred)

    rows = []

    for i, meta in enumerate(meta_list):
        rows.append({
            "fold": fold,
            "dataset": dataset_name,
            "Method": method,
            "material_id": meta["material_id"],
            "point_id_in_material": meta["point_id_in_material"],
            "original_data_row_index": meta["original_data_row_index"],
            "T_K": meta["T_K"],
            "slope_pred": meta["slope_pred"],
            "y_true": y_true[i],
            "y_pred": y_pred[i],
            "error": y_pred[i] - y_true[i],
            "absolute_error": abs(y_pred[i] - y_true[i]),
            "relative_error_percent": rel_err[i],
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
# 2. 读取并准备原始数据
# =========================================================
df_groups_raw = pd.read_excel(file_path, sheet_name=groups_sheet)
df_data = pd.read_excel(file_path, sheet_name=data_sheet)

print("groups 表行数:", len(df_groups_raw))
print("Sheet1 数据行数:", len(df_data))

group_start_idx = 2
group_end_idx = 221
group_cols_raw = df_groups_raw.columns[group_start_idx:group_end_idx].tolist()

exclude_cols = {
    "original_material_index", "compound_name", "cas", "formula",
    "SMILES", "smiles", "pubchem_cid", "material_key", "phase",
    "boiling_T_K", "critical_T_K"
}

group_cols_raw = [c for c in group_cols_raw if c not in exclude_cols]

df_groups = df_groups_raw[group_cols_raw].copy()
df_groups = df_groups.apply(pd.to_numeric, errors="coerce").fillna(0.0)

nonzero_mask = df_groups.abs().sum(axis=0) != 0
used_group_cols = df_groups.columns[nonzero_mask].tolist()
removed_zero_group_cols = df_groups.columns[~nonzero_mask].tolist()
df_groups_used = df_groups[used_group_cols].copy()

print("有效基团数量:", len(used_group_cols))
print("删除全零基团数量:", len(removed_zero_group_cols))

if len(df_data) % n_points_per_material != 0:
    raise ValueError(f"数据行数 {len(df_data)} 不是 {n_points_per_material} 的倍数")

n_materials = len(df_data) // n_points_per_material
print("物质总数:", n_materials)

if len(df_groups_raw) != n_materials:
    print("警告：groups 表行数与 Sheet1 按 8 点推断的物质数不一致。")
    print("groups 表行数:", len(df_groups_raw))
    print("Sheet1 推断物质数:", n_materials)


# =========================================================
# 3. 读取并准备预测斜率
# =========================================================
if not predicted_slope_file.exists():
    raise FileNotFoundError(f"未找到预测斜率文件: {predicted_slope_file}")

df_slope = pd.read_excel(predicted_slope_file, sheet_name=predicted_slope_sheet)

if predicted_slope_col not in df_slope.columns:
    raise ValueError(f"斜率文件中没有列: {predicted_slope_col}")

df_slope[predicted_slope_col] = pd.to_numeric(df_slope[predicted_slope_col], errors="coerce")

if "original_material_index" in df_groups_raw.columns and "original_material_index" in df_slope.columns:
    slope_map = (
        df_slope[["original_material_index", predicted_slope_col]]
        .drop_duplicates(subset=["original_material_index"])
        .set_index("original_material_index")[predicted_slope_col]
    )
    df_groups_raw["slope_pred"] = df_groups_raw["original_material_index"].map(slope_map)
else:
    if len(df_groups_raw) != len(df_slope):
        raise ValueError("无法对齐斜率表且行数不一致")
    df_groups_raw["slope_pred"] = df_slope[predicted_slope_col].values

valid_slope = np.isfinite(df_groups_raw["slope_pred"].values)

if not valid_slope.all():
    print(f"删除 {np.sum(~valid_slope)} 个斜率无效的物质")

    keep_indices = np.where(valid_slope)[0]

    df_groups_raw = df_groups_raw.iloc[keep_indices].reset_index(drop=True)
    df_groups_used = df_groups_used.iloc[keep_indices].reset_index(drop=True)

    keep_data_rows = []
    for mat_idx in keep_indices:
        start = mat_idx * n_points_per_material
        end = start + n_points_per_material
        keep_data_rows.extend(range(start, end))

    df_data = df_data.iloc[keep_data_rows].reset_index(drop=True)
    n_materials = len(keep_indices)
    slope_values = df_groups_raw["slope_pred"].values
else:
    slope_values = df_groups_raw["slope_pred"].values

print("最终有效物质数:", n_materials)

# 保存 slope 对齐信息
slope_info_rows = []
for mat_idx in range(n_materials):
    row = {
        "material_id": mat_idx,
        "slope_pred": slope_values[mat_idx],
    }

    for col in [
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
    ]:
        if col in df_groups_raw.columns:
            row[col] = df_groups_raw.loc[mat_idx, col]

    slope_info_rows.append(row)

df_slope_info = pd.DataFrame(slope_info_rows)


# =========================================================
# 4. 构建每个物质的数据块
# =========================================================
material_features = []
material_targets = []
material_ids = list(range(n_materials))

for mat_idx in range(n_materials):
    group_vec = df_groups_used.iloc[mat_idx].values.astype(float)
    slope = slope_values[mat_idx]

    material_features.append((group_vec, slope))

    start = mat_idx * n_points_per_material
    end = start + n_points_per_material

    sub = df_data.iloc[start:end]
    T_vals = pd.to_numeric(sub[temp_col], errors="coerce").values
    Cp_vals = pd.to_numeric(sub[target_col], errors="coerce").values

    points = []
    for local_i, (t, cp) in enumerate(zip(T_vals, Cp_vals)):
        if np.isfinite(t) and np.isfinite(cp):
            points.append({
                "material_id": mat_idx,
                "point_id_in_material": local_i,
                "original_data_row_index": start + local_i,
                "T_K": float(t),
                "Cp": float(cp),
                "slope_pred": float(slope),
            })

    material_targets.append(points)


# =========================================================
# 5. 辅助函数：根据物质索引构建 X, y
# =========================================================
def build_Xy(material_indices, use_slope=True, return_meta=False):
    X_list = []
    y_list = []
    meta_list = []

    for mid in material_indices:
        group_vec, slope = material_features[mid]
        points = material_targets[mid]

        for point in points:
            T = point["T_K"]
            Cp = point["Cp"]

            if use_slope:
                feat = np.concatenate([group_vec, [T, slope]])
            else:
                feat = np.concatenate([group_vec, [T]])

            X_list.append(feat)
            y_list.append(Cp)

            if return_meta:
                meta_list.append({
                    "material_id": point["material_id"],
                    "point_id_in_material": point["point_id_in_material"],
                    "original_data_row_index": point["original_data_row_index"],
                    "T_K": point["T_K"],
                    "slope_pred": point["slope_pred"],
                })

    X = np.array(X_list, dtype=float)
    y = np.array(y_list, dtype=float)

    if return_meta:
        return X, y, meta_list

    return X, y


feat_names_no_slope = used_group_cols + [temp_col]
feat_names_with_slope = used_group_cols + [temp_col, predicted_slope_col]

# 完整数据集特征
X_all_no, y_all_no, meta_all_no = build_Xy(material_ids, use_slope=False, return_meta=True)
X_all_with, y_all_with, meta_all_with = build_Xy(material_ids, use_slope=True, return_meta=True)

if not np.allclose(y_all_no, y_all_with):
    raise ValueError("no_slope 与 with_slope 构造出的完整数据集 y 不一致。")

y_all = y_all_no

print("完整数据集有效点数:", len(y_all))


# =========================================================
# 6. 5 折交叉验证（按物质）
# =========================================================
kf = KFold(n_splits=n_splits, shuffle=True, random_state=random_state)

metrics_no_slope = []
metrics_with_slope = []

fold_results = []
fold_info_records = []

fold_test_prediction_dfs = []
fold_all_data_prediction_dfs = []

fold_all_data_count_records = []

for fold, (train_idx, test_idx) in enumerate(kf.split(material_ids), start=1):
    print(f"\n========== Fold {fold}/{n_splits} ==========")

    train_materials = [material_ids[i] for i in train_idx]
    test_materials = [material_ids[i] for i in test_idx]

    print("训练物质数:", len(train_materials))
    print("测试物质数:", len(test_materials))

    X_train_no, y_train_no = build_Xy(train_materials, use_slope=False)
    X_test_no, y_test_no, meta_test_no = build_Xy(test_materials, use_slope=False, return_meta=True)

    X_train_with, y_train_with = build_Xy(train_materials, use_slope=True)
    X_test_with, y_test_with, meta_test_with = build_Xy(test_materials, use_slope=True, return_meta=True)

    if not np.allclose(y_train_no, y_train_with):
        raise ValueError(f"Fold {fold}: no_slope 与 with_slope 的训练集 y 不一致。")

    if not np.allclose(y_test_no, y_test_with):
        raise ValueError(f"Fold {fold}: no_slope 与 with_slope 的测试集 y 不一致。")

    print("训练样本点数:", len(y_train_no))
    print("测试样本点数:", len(y_test_no))

    # -----------------------------------------------------
    # 方法1：不加 slope 的 RF 模型
    # -----------------------------------------------------
    model_no = RandomForestRegressor(**rf_params)
    model_no.fit(X_train_no, y_train_no)

    y_pred_no_test = model_no.predict(X_test_no)
    y_pred_no_all = model_no.predict(X_all_no)

    # -----------------------------------------------------
    # 方法2：加 slope 的 RF 模型
    # -----------------------------------------------------
    model_with = RandomForestRegressor(**rf_params)
    model_with.fit(X_train_with, y_train_with)

    y_pred_with_test = model_with.predict(X_test_with)
    y_pred_with_all = model_with.predict(X_all_with)

    # -----------------------------------------------------
    # 测试集评价指标：保留原功能
    # -----------------------------------------------------
    m_no = compute_metrics(y_test_no, y_pred_no_test, fold, "no_slope")
    m_with = compute_metrics(y_test_with, y_pred_with_test, fold, "with_slope")

    metrics_no_slope.append(m_no)
    metrics_with_slope.append(m_with)

    print(
        "No slope test: "
        f"R2={m_no['R2']:.6f}, "
        f"MSE={m_no['MSE']:.6f}, "
        f"RMSE={m_no['RMSE']:.6f}, "
        f"MAE={m_no['MAE']:.6f}, "
        f"ARD={m_no['ARD(%)']:.6f}%"
    )

    print(
        "With slope test: "
        f"R2={m_with['R2']:.6f}, "
        f"MSE={m_with['MSE']:.6f}, "
        f"RMSE={m_with['RMSE']:.6f}, "
        f"MAE={m_with['MAE']:.6f}, "
        f"ARD={m_with['ARD(%)']:.6f}%"
    )

    # -----------------------------------------------------
    # 新增：每个 fold 模型预测完整数据集，并统计完整数据集偏差数量
    # -----------------------------------------------------
    count_no_all = count_error_thresholds(y_all, y_pred_no_all)
    count_with_all = count_error_thresholds(y_all, y_pred_with_all)

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "no_slope",
        **count_no_all,
    })

    fold_all_data_count_records.append({
        "fold": fold,
        "Method": "with_slope",
        **count_with_all,
    })

    print("\nNo slope fold model predicts ALL data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "no_slope",
        **count_no_all,
    }]).to_string(index=False))

    print("\nWith slope fold model predicts ALL data count summary:")
    print(pd.DataFrame([{
        "fold": fold,
        "Method": "with_slope",
        **count_with_all,
    }]).to_string(index=False))

    # -----------------------------------------------------
    # 保存测试集预测明细
    # -----------------------------------------------------
    df_test_no = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="no_slope",
        meta_list=meta_test_no,
        y_true=y_test_no,
        y_pred=y_pred_no_test,
    )

    df_test_with = make_prediction_df(
        fold=fold,
        dataset_name="test",
        method="with_slope",
        meta_list=meta_test_with,
        y_true=y_test_with,
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
        method="no_slope",
        meta_list=meta_all_no,
        y_true=y_all,
        y_pred=y_pred_no_all,
    )

    df_all_with = make_prediction_df(
        fold=fold,
        dataset_name="all_data",
        method="with_slope",
        meta_list=meta_all_with,
        y_true=y_all,
        y_pred=y_pred_with_all,
    )

    fold_all_data_prediction_dfs.append(df_all_no)
    fold_all_data_prediction_dfs.append(df_all_with)

    # -----------------------------------------------------
    # 保留原 fold_results 结构
    # -----------------------------------------------------
    fold_results.append({
        "fold": fold,
        "train_materials": train_materials,
        "test_materials": test_materials,
        "y_test_no": y_test_no,
        "y_pred_no": y_pred_no_test,
        "y_test_with": y_test_with,
        "y_pred_with": y_pred_with_test,
    })

    fold_info_records.append({
        "fold": fold,
        "n_train_materials": len(train_materials),
        "n_test_materials": len(test_materials),
        "n_train_points": len(y_train_no),
        "n_test_points": len(y_test_no),
        "n_features_no_slope": X_train_no.shape[1],
        "n_features_with_slope": X_train_with.shape[1],
        **{f"rf_{k}": v for k, v in rf_params.items()},
    })


# =========================================================
# 7. 汇总指标并计算均值±标准差
# =========================================================
df_no = pd.DataFrame(metrics_no_slope)
df_with = pd.DataFrame(metrics_with_slope)

summary_no = summarize(df_no, "No Slope")
summary_with = summarize(df_with, "With Slope")
summary_all = pd.concat([summary_no, summary_with], ignore_index=True)

print("\n========== 5-Fold CV Summary (Mean ± Std) ==========")
print(summary_all.to_string(index=False))


# =========================================================
# 8. 配对 t 检验
# =========================================================
t_test_results = []

for metric in ["R2", "MSE", "RMSE", "MAE", "ARD(%)"]:
    val_no = df_no[metric].dropna().values
    val_with = df_with[metric].dropna().values

    if len(val_no) == len(val_with) and len(val_no) > 1:
        t_stat, p_val = ttest_rel(val_no, val_with)

        # 判断哪个模型更好：MSE/RMSE/MAE/ARD 越小越好，R2 越大越好
        if metric in ["MSE", "RMSE", "MAE", "ARD(%)"]:
            better = "with_slope" if np.mean(val_with) < np.mean(val_no) else "no_slope"
        else:
            better = "with_slope" if np.mean(val_with) > np.mean(val_no) else "no_slope"

        significant = p_val < 0.05

        t_test_results.append({
            "Metric": metric,
            "Mean_no_slope": f"{np.mean(val_no):.4f}",
            "Mean_with_slope": f"{np.mean(val_with):.4f}",
            "p-value": f"{p_val:.4e}",
            "Significant (p<0.05)": significant,
            "Better model": better,
        })

df_ttest = pd.DataFrame(t_test_results)

print("\n========== Paired t-test between No Slope vs With Slope ==========")
print(df_ttest.to_string(index=False))


# =========================================================
# 9. 新增：完整数据集预测偏差数量统计汇总
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
        "n_all_data_points": len(y_all),
    })

df_final_average_summary = pd.DataFrame(final_average_records)

print("\n========== Fold all-data count summary ==========")
print(df_fold_all_data_count_summary.to_string(index=False))

print("\n========== Final average all-data count summary ==========")
print(df_final_average_summary.to_string(index=False))


# =========================================================
# 10. 整理预测明细和附加信息
# =========================================================
df_fold_test_predictions = pd.concat(fold_test_prediction_dfs, ignore_index=True)
df_fold_all_data_predictions = pd.concat(fold_all_data_prediction_dfs, ignore_index=True)

# 保留原来的 All_Fold_Predictions 形式
all_preds = []
for fr in fold_results:
    f = fr["fold"]

    for yt, yp in zip(fr["y_test_no"], fr["y_pred_no"]):
        all_preds.append({
            "fold": f,
            "model": "no_slope",
            "true": yt,
            "pred": yp,
            "relative_error_percent": safe_relative_error_percent([yt], [yp])[0],
        })

    for yt, yp in zip(fr["y_test_with"], fr["y_pred_with"]):
        all_preds.append({
            "fold": f,
            "model": "with_slope",
            "true": yt,
            "pred": yp,
            "relative_error_percent": safe_relative_error_percent([yt], [yp])[0],
        })

df_preds = pd.DataFrame(all_preds)

# 补充物质信息
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

group_occurrence_all = (df_groups_used != 0).sum(axis=0)
group_total_count_all = df_groups_used.sum(axis=0)

df_used_groups = pd.DataFrame({
    "used_group": used_group_cols,
    "occurrence_all_materials": group_occurrence_all[used_group_cols].values,
    "total_count_all": group_total_count_all[used_group_cols].values,
})

df_removed_zero_groups = pd.DataFrame({
    "removed_all_zero_group": removed_zero_group_cols,
})

params_df = pd.DataFrame([{"param": k, "value": v} for k, v in rf_params.items()])


# =========================================================
# 11. 全数据最终模型的特征重要性
# =========================================================
final_model_no = RandomForestRegressor(**rf_params)
final_model_no.fit(X_all_no, y_all)

imp_no = pd.DataFrame({
    "feature": feat_names_no_slope,
    "importance": final_model_no.feature_importances_,
})
imp_no = imp_no.sort_values("importance", ascending=False)

final_model_with = RandomForestRegressor(**rf_params)
final_model_with.fit(X_all_with, y_all)

imp_with = pd.DataFrame({
    "feature": feat_names_with_slope,
    "importance": final_model_with.feature_importances_,
})
imp_with = imp_with.sort_values("importance", ascending=False)


# =========================================================
# 12. 模型结构汇总
# =========================================================
df_model_structure = pd.DataFrame([
    {
        "项目": "预测对象",
        "内容": "定压热容 Cp / property_value",
    },
    {
        "项目": "主数据文件",
        "内容": str(file_path),
    },
    {
        "项目": "groups sheet",
        "内容": groups_sheet,
    },
    {
        "项目": "data sheet",
        "内容": data_sheet,
    },
    {
        "项目": "温度列",
        "内容": temp_col,
    },
    {
        "项目": "目标列",
        "内容": target_col,
    },
    {
        "项目": "交叉验证方式",
        "内容": f"{n_splits}-fold KFold，按物质划分，shuffle=True，random_state={random_state}",
    },
    {
        "项目": "方法1",
        "内容": "No Slope：RandomForestRegressor 直接预测 Cp，输入特征为 [Nk, T]",
    },
    {
        "项目": "方法2",
        "内容": "With Slope：RandomForestRegressor 直接预测 Cp，输入特征为 [Nk, T, reference_slope_pred]",
    },
    {
        "项目": "是否包含子模型",
        "内容": "当前代码不训练子模型，但读取外部 GBDT 子模型预测得到的 reference_slope_pred",
    },
    {
        "项目": "子模型文件",
        "内容": str(predicted_slope_file),
    },
    {
        "项目": "子模型 sheet",
        "内容": predicted_slope_sheet,
    },
    {
        "项目": "子模型输出列",
        "内容": predicted_slope_col,
    },
    {
        "项目": "子模型预测对象",
        "内容": "reference_slope_pred，用作方法2的额外输入特征",
    },
    {
        "项目": "子模型类型",
        "内容": "外部文件名显示为 GBDT；本代码只读取其预测结果，不在当前脚本内训练",
    },
    {
        "项目": "子模型参数",
        "内容": "当前脚本无法从 Excel 预测结果文件中恢复 GBDT 参数；仅保留 slope 预测结果",
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
        "内容": "无显式 baseline + residual 结构；两个方法均为直接 RF 回归",
    },
    {
        "项目": "residual 构造方式",
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
        "项目": "方法1最终输入特征",
        "内容": f"[{len(used_group_cols)} 个 Nk, T]，总维度 {len(used_group_cols) + 1}",
    },
    {
        "项目": "方法2最终输入特征",
        "内容": f"[{len(used_group_cols)} 个 Nk, T, reference_slope_pred]，总维度 {len(used_group_cols) + 2}",
    },
    {
        "项目": "偏差数量统计口径",
        "内容": "每个 fold 训练出的模型都预测完整数据集，统计相对误差 <1%、<5%、<10% 的点数，再对 5 个 fold 的数量取平均",
    },
])


df_run_info = pd.DataFrame([
    {"item": "file_path", "value": str(file_path)},
    {"item": "groups_sheet", "value": groups_sheet},
    {"item": "data_sheet", "value": data_sheet},
    {"item": "predicted_slope_file", "value": str(predicted_slope_file)},
    {"item": "predicted_slope_sheet", "value": predicted_slope_sheet},
    {"item": "predicted_slope_col", "value": predicted_slope_col},
    {"item": "n_points_per_material", "value": n_points_per_material},
    {"item": "n_splits", "value": n_splits},
    {"item": "random_state", "value": random_state},
    {"item": "n_materials", "value": n_materials},
    {"item": "n_all_data_points", "value": len(y_all)},
    {"item": "n_group_features", "value": len(used_group_cols)},
    {"item": "method1", "value": "No Slope: [Nk, T]"},
    {"item": "method2", "value": "With Slope: [Nk, T, reference_slope_pred]"},
    {"item": "relative_error_definition", "value": "abs((y_pred - y_true) / y_true) * 100; abs(y_true)<=1e-12 -> NaN"},
    {"item": "full_data_count_rule", "value": "Each fold model predicts the whole dataset; count rel_err <1%, <5%, <10%; then average counts over 5 folds."},
])


# =========================================================
# 13. 保存结果到 Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    # 原有输出
    df_no.to_excel(writer, sheet_name="Fold_Metrics_No_Slope", index=False)
    df_with.to_excel(writer, sheet_name="Fold_Metrics_With_Slope", index=False)
    summary_all.to_excel(writer, sheet_name="Summary_Mean_Std", index=False)
    df_ttest.to_excel(writer, sheet_name="Paired_T_Test", index=False)
    df_preds.to_excel(writer, sheet_name="All_Fold_Predictions", index=False)

    # 原有特征重要性扩展为 no_slope 和 with_slope 都保存
    imp_no.to_excel(writer, sheet_name="Feature_Imp_No_Slope", index=False)
    imp_with.to_excel(writer, sheet_name="Feature_Imp_With_Slope", index=False)

    params_df.to_excel(writer, sheet_name="RF_Params", index=False)

    # 新增输出
    df_fold_test_predictions.to_excel(writer, sheet_name="fold_test_predictions", index=False)
    df_fold_all_data_predictions.to_excel(writer, sheet_name="fold_all_data_predictions", index=False)
    df_fold_all_data_count_summary.to_excel(writer, sheet_name="fold_all_data_count_summary", index=False)
    df_final_average_summary.to_excel(writer, sheet_name="final_average_summary", index=False)

    df_slope_info.to_excel(writer, sheet_name="slope_info", index=False)
    df_fold_info.to_excel(writer, sheet_name="Fold_Info", index=False)
    df_used_groups.to_excel(writer, sheet_name="Used_Groups", index=False)
    df_removed_zero_groups.to_excel(writer, sheet_name="Removed_Zero_Groups", index=False)
    df_run_info.to_excel(writer, sheet_name="Run_Info", index=False)
    df_model_structure.to_excel(writer, sheet_name="model_structure", index=False)

    format_excel(writer)

print(f"\n所有结果已保存至: {output_file}")


# =========================================================
# 14. 最终方便复制输出
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


no_1, no_5, no_10 = get_final_counts("no_slope")
with_1, with_5, with_10 = get_final_counts("with_slope")

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
print("预测对象：Cp / property_value")
print(f"数据文件：{file_path}")
print(f"sheet 名称：{groups_sheet}, {data_sheet}")
print(f"交叉验证：{n_splits}-fold，按物质划分")
print("方法1：No Slope，RandomForestRegressor，输入 [Nk, T]")
print("方法2：With Slope，RandomForestRegressor，输入 [Nk, T, reference_slope_pred]")
print("子模型：当前代码不训练子模型，读取外部 GBDT 预测的 reference_slope_pred")
print(f"子模型预测文件：{predicted_slope_file}")
print(f"子模型预测 sheet：{predicted_slope_sheet}")
print(f"子模型预测列：{predicted_slope_col}")
print("子模型参数：当前代码无法从预测结果文件恢复，仅保存 slope 预测值")
print("slope 构造：直接读取 reference_slope_pred，作为方法2额外输入特征；没有乘以 T")
print("baseline 构造：无")
print("residual 模型：无")
print(f"最终模型：RandomForestRegressor，参数：{rf_params}")
print("方法1最终输入：[Nk, T]")
print("方法2最终输入：[Nk, T, reference_slope_pred]")
print("偏差统计口径：每个 fold 模型预测完整数据集，统计 <1%、<5%、<10% 点数，再对 5 个 fold 取平均")