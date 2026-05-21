# import pandas as pd
# import numpy as np
#
# from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
# from sklearn.preprocessing import PolynomialFeatures
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split
#
#
# # ============================================================
# # 0. 参数区
# # ============================================================
# main_file = "Pure component exergy 205.xlsx"
# main_sheet = "Sheet1"
#
# normal_file = "selected_25_descriptors_normal.xlsx"
# boiling_file = "selected_25_descriptors_boiling.xlsx"
#
# target_500 = "ASPEN Exergy at 500k Temperature(j/mol)"
# target_Tb_exergy = "ASPEN Exergy at BoilingTemperature(j/mol)"
#
# T_ref = 500.0
# random_state = 49
#
#
# # ============================================================
# # 最终 RF 参数：和无 slope 模型保持一致
# # ============================================================
# FINAL_RF_PARAMS = dict(
#     n_estimators=200,
#     max_depth=10,
#     min_samples_split=5,
#     min_samples_leaf=2,
#     random_state=42,
#     n_jobs=-1
# )
#
#
# # ============================================================
# # 子模型参数：这次换成 ExtraTreesRegressor
# # ============================================================
# SUBMODEL_ET_PARAMS = dict(
#     n_estimators=1000,
#     max_depth=None,
#     min_samples_split=2,
#     min_samples_leaf=1,
#     max_features=1.0,
#     bootstrap=False,
#     random_state=42,
#     n_jobs=-1
# )
#
#
# # ============================================================
# # 1. 读取主数据
# # ============================================================
# df = pd.read_excel(main_file, sheet_name=main_sheet).copy()
#
# material_id_col = df.columns[0]
#
# group_cols = df.columns[12:31]   # 19个基团
# temp_cols = df.columns[31:41]    # 10个温度点
# exergy_cols = df.columns[41:51]  # 10个 Exergy 点
#
# tb_col = df.columns[5]
#
#
# # ============================================================
# # 2. 数值化主数据
# # ============================================================
# for col in list(group_cols) + list(temp_cols) + list(exergy_cols) + [tb_col]:
#     df[col] = pd.to_numeric(df[col], errors="coerce")
#
# df = df.dropna(subset=[material_id_col]).copy().reset_index(drop=True)
#
#
# # ============================================================
# # 3. 子模型 1：500 K Exergy
# #    子模型不划分训练集/测试集，使用全体数据训练
# # ============================================================
# df_500 = pd.read_excel(normal_file).copy()
#
# if len(df_500) != len(df):
#     raise ValueError(
#         f"{normal_file} 与主文件行数不一致：{len(df_500)} vs {len(df)}。"
#         f"当前代码默认两个文件逐行对应。"
#     )
#
# X_500_all = df_500.drop(columns=[target_500]).apply(pd.to_numeric, errors="coerce")
# y_500_all = pd.to_numeric(df_500[target_500], errors="coerce")
#
# valid_500_mask = (
#     np.isfinite(X_500_all).all(axis=1)
#     & np.isfinite(y_500_all)
# )
#
# et_500 = ExtraTreesRegressor(**SUBMODEL_ET_PARAMS)
#
# et_500.fit(
#     X_500_all.loc[valid_500_mask],
#     y_500_all.loc[valid_500_mask]
# )
#
# Exergy_500_pred_all = np.full(len(df), np.nan, dtype=float)
#
# predict_500_mask = np.isfinite(X_500_all).all(axis=1)
#
# Exergy_500_pred_all[predict_500_mask] = et_500.predict(
#     X_500_all.loc[predict_500_mask]
# )
#
#
# # ============================================================
# # 4. 子模型 2：Boiling Temperature Exergy
# #    子模型不划分训练集/测试集，使用全体数据训练
# # ============================================================
# df_Tb = pd.read_excel(boiling_file).copy()
#
# if len(df_Tb) != len(df):
#     raise ValueError(
#         f"{boiling_file} 与主文件行数不一致：{len(df_Tb)} vs {len(df)}。"
#         f"当前代码默认两个文件逐行对应。"
#     )
#
# X_Tb_all = df_Tb.drop(columns=[target_Tb_exergy]).apply(pd.to_numeric, errors="coerce")
# y_Tb_all = pd.to_numeric(df_Tb[target_Tb_exergy], errors="coerce")
#
# valid_Tb_exergy_mask = (
#     np.isfinite(X_Tb_all).all(axis=1)
#     & np.isfinite(y_Tb_all)
# )
#
# et_Tb = ExtraTreesRegressor(**SUBMODEL_ET_PARAMS)
#
# et_Tb.fit(
#     X_Tb_all.loc[valid_Tb_exergy_mask],
#     y_Tb_all.loc[valid_Tb_exergy_mask]
# )
#
# Exergy_Tb_pred_all = np.full(len(df), np.nan, dtype=float)
#
# predict_Tb_exergy_mask = np.isfinite(X_Tb_all).all(axis=1)
#
# Exergy_Tb_pred_all[predict_Tb_exergy_mask] = et_Tb.predict(
#     X_Tb_all.loc[predict_Tb_exergy_mask]
# )
#
#
# # ============================================================
# # 5. 子模型 3：Tb 预测模型
# #    这里也换成 ExtraTreesRegressor
# # ============================================================
# Nk_all_df = df[group_cols].apply(pd.to_numeric, errors="coerce")
# Tb_raw_all = pd.to_numeric(df[tb_col], errors="coerce").values
#
# poly = PolynomialFeatures(degree=2, include_bias=False)
#
# valid_group_mask = np.isfinite(Nk_all_df).all(axis=1)
#
# Nk_poly_valid = poly.fit_transform(
#     Nk_all_df.loc[valid_group_mask]
# )
#
# Nk_poly_all = np.full(
#     (len(df), Nk_poly_valid.shape[1]),
#     np.nan,
#     dtype=float
# )
#
# Nk_poly_all[valid_group_mask] = Nk_poly_valid
#
# valid_tb_mask = (
#     np.isfinite(Tb_raw_all)
#     & np.isfinite(Nk_poly_all).all(axis=1)
# )
#
# et_Tb_pred = ExtraTreesRegressor(**SUBMODEL_ET_PARAMS)
#
# et_Tb_pred.fit(
#     Nk_poly_all[valid_tb_mask],
#     Tb_raw_all[valid_tb_mask]
# )
#
# Tb_pred_all = np.full(len(df), np.nan, dtype=float)
#
# predict_tb_mask = np.isfinite(Nk_poly_all).all(axis=1)
#
# Tb_pred_all[predict_tb_mask] = et_Tb_pred.predict(
#     Nk_poly_all[predict_tb_mask]
# )
#
#
# # ============================================================
# # 6. 计算 slope
# #    slope = (Exergy_Tb_pred - Exergy_500_pred) / (Tb_pred - 500)
# # ============================================================
# denom = Tb_pred_all - T_ref
#
# slope_values = np.full(len(df), np.nan, dtype=float)
#
# valid_slope_mask = (
#     np.isfinite(Exergy_Tb_pred_all)
#     & np.isfinite(Exergy_500_pred_all)
#     & np.isfinite(Tb_pred_all)
#     & (np.abs(denom) > 1e-12)
# )
#
# slope_values[valid_slope_mask] = (
#     Exergy_Tb_pred_all[valid_slope_mask]
#     - Exergy_500_pred_all[valid_slope_mask]
# ) / denom[valid_slope_mask]
#
# df["slope"] = slope_values
# df["Exergy_500_pred"] = Exergy_500_pred_all
# df["Exergy_Tb_pred"] = Exergy_Tb_pred_all
# df["Tb_pred"] = Tb_pred_all
#
#
# # ============================================================
# # 7. 子模型诊断评价
# # ============================================================
# def eval_submodel(y_true, y_pred, name):
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#
#     mask = np.isfinite(y_true) & np.isfinite(y_pred)
#
#     if not np.any(mask):
#         print(f"\n{name}: 无有效评价样本")
#         return {
#             "Model": name,
#             "R2": np.nan,
#             "MSE": np.nan,
#             "ARD_%": np.nan,
#             "within_1pct": 0,
#             "within_5pct": 0,
#             "within_10pct": 0
#         }
#
#     y_true_valid = y_true[mask]
#     y_pred_valid = y_pred[mask]
#
#     r2 = r2_score(y_true_valid, y_pred_valid)
#     mse = mean_squared_error(y_true_valid, y_pred_valid)
#
#     relative_error = np.full_like(y_true_valid, np.nan, dtype=float)
#     nonzero_mask = np.abs(y_true_valid) > 1e-12
#
#     if np.any(nonzero_mask):
#         relative_error[nonzero_mask] = np.abs(
#             (y_pred_valid[nonzero_mask] - y_true_valid[nonzero_mask])
#             / y_true_valid[nonzero_mask]
#         ) * 100
#         ard = np.nanmean(relative_error)
#     else:
#         ard = np.nan
#
#     within_1pct = np.sum(relative_error <= 1)
#     within_5pct = np.sum(relative_error <= 5)
#     within_10pct = np.sum(relative_error <= 10)
#
#     print(f"\n{name}:")
#     print(f"R2  = {r2:.6f}")
#     print(f"MSE = {mse:.10f}")
#     print(f"ARD = {ard:.4f}%")
#     print(f"误差 <= 1%  点数: {within_1pct}")
#     print(f"误差 <= 5%  点数: {within_5pct}")
#     print(f"误差 <= 10% 点数: {within_10pct}")
#
#     return {
#         "Model": name,
#         "R2": r2,
#         "MSE": mse,
#         "ARD_%": ard,
#         "within_1pct": within_1pct,
#         "within_5pct": within_5pct,
#         "within_10pct": within_10pct
#     }
#
#
# sub_500_metrics = eval_submodel(
#     y_500_all.values,
#     Exergy_500_pred_all,
#     "Exergy_500K_ExtraTrees_submodel_all_data"
# )
#
# sub_Tb_metrics = eval_submodel(
#     y_Tb_all.values,
#     Exergy_Tb_pred_all,
#     "Exergy_boiling_ExtraTrees_submodel_all_data"
# )
#
# sub_Tb_pred_metrics = eval_submodel(
#     Tb_raw_all,
#     Tb_pred_all,
#     "Tb_ExtraTrees_submodel_all_data"
# )
#
#
# # ============================================================
# # 8. 物质级有效筛选
# # ============================================================
# Nk_all = df[group_cols].to_numpy(dtype=float)
# T_all = df[temp_cols].to_numpy(dtype=float)
# Exergy_all = df[exergy_cols].to_numpy(dtype=float)
# slope_all = df["slope"].to_numpy(dtype=float).reshape(-1, 1)
# material_ids_all = df[material_id_col].values
#
# valid_target_mask = np.isfinite(Exergy_all)
# valid_target_mask = valid_target_mask.all(axis=1)
#
# valid_feature_mask = (
#     np.isfinite(Nk_all).all(axis=1)
#     & np.isfinite(T_all).all(axis=1)
#     & np.isfinite(slope_all).flatten()
# )
#
# valid_mask = valid_target_mask & valid_feature_mask
#
# Nk_valid = Nk_all[valid_mask]
# T_valid = T_all[valid_mask]
# Exergy_valid = Exergy_all[valid_mask]
# slope_valid = slope_all[valid_mask]
# material_ids_valid = material_ids_all[valid_mask]
#
# Exergy_500_pred_valid = Exergy_500_pred_all[valid_mask]
# Exergy_Tb_pred_valid = Exergy_Tb_pred_all[valid_mask]
# Tb_pred_valid = Tb_pred_all[valid_mask]
#
# print("\n========== 数据清洗后 ==========")
# print(f"有效物质数: {len(material_ids_valid)}")
#
#
# # ============================================================
# # 9. 最终 RF 模型按物质 8:2 划分
# # ============================================================
# material_indices = np.arange(len(material_ids_valid))
#
# train_idx, test_idx = train_test_split(
#     material_indices,
#     test_size=0.2,
#     random_state=random_state
# )
#
# print("\n========== 最终 RF 模型按物质划分 ==========")
# print(f"训练集物质数: {len(train_idx)}")
# print(f"测试集物质数: {len(test_idx)}")
#
#
# # ============================================================
# # 10. 构建最终点级数据集
# # ============================================================
# def build_point_dataset(Nk, T, Exergy, slope, material_ids):
#     """
#     最终 RF 特征：
#         19个基团 + Temperature + slope
#     """
#
#     X = np.hstack([
#         Nk.repeat(10, axis=0),
#         T.flatten().reshape(-1, 1),
#         slope.repeat(10, axis=0)
#     ])
#
#     y = Exergy.flatten()
#
#     expanded_ids = np.repeat(material_ids, 10)
#     expanded_T = T.flatten()
#     expanded_slope = slope.repeat(10, axis=0).flatten()
#
#     finite_mask = (
#         np.isfinite(y)
#         & np.isfinite(X).all(axis=1)
#     )
#
#     return (
#         X[finite_mask],
#         y[finite_mask],
#         expanded_ids[finite_mask],
#         expanded_T[finite_mask],
#         expanded_slope[finite_mask]
#     )
#
#
# X_train, y_train, id_train, temp_train, slope_train_point = build_point_dataset(
#     Nk_valid[train_idx],
#     T_valid[train_idx],
#     Exergy_valid[train_idx],
#     slope_valid[train_idx],
#     material_ids_valid[train_idx]
# )
#
# X_test, y_test, id_test, temp_test, slope_test_point = build_point_dataset(
#     Nk_valid[test_idx],
#     T_valid[test_idx],
#     Exergy_valid[test_idx],
#     slope_valid[test_idx],
#     material_ids_valid[test_idx]
# )
#
# print("\n========== 最终 RF 点级数据 ==========")
# print(f"训练集样本点数: {len(X_train)}")
# print(f"测试集样本点数: {len(X_test)}")
# print(f"最终模型特征数: {X_train.shape[1]}")
#
# if X_train.shape[1] != 21:
#     raise ValueError(
#         f"当前特征数为 {X_train.shape[1]}，预期为 21：19个基团 + Temperature + slope。"
#     )
#
#
# # ============================================================
# # 11. 最终 RF 模型
# #    注意：这里参数和无 slope 模型保持一致
# # ============================================================
# model = RandomForestRegressor(**FINAL_RF_PARAMS)
#
#
# # ============================================================
# # 12. 训练最终 RF 模型
# # ============================================================
# print("\n开始训练最终 RF 模型...")
# model.fit(X_train, y_train)
#
#
# # ============================================================
# # 13. 最终模型评价函数
# # ============================================================
# def evaluate_dataset(y_true, y_pred, name="数据集"):
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#
#     r2 = r2_score(y_true, y_pred)
#     mse = mean_squared_error(y_true, y_pred)
#
#     relative_error = np.full_like(y_true, np.nan, dtype=float)
#     nonzero_mask = np.abs(y_true) > 1e-12
#
#     if np.any(nonzero_mask):
#         relative_error[nonzero_mask] = np.abs(
#             (y_pred[nonzero_mask] - y_true[nonzero_mask])
#             / y_true[nonzero_mask]
#         ) * 100
#         ard = np.nanmean(relative_error)
#     else:
#         ard = np.nan
#
#     within_1pct = np.sum(relative_error <= 1)
#     within_5pct = np.sum(relative_error <= 5)
#     within_10pct = np.sum(relative_error <= 10)
#
#     print(f"\n{name}评估结果:")
#     print(f"R2  = {r2:.6f}")
#     print(f"MSE = {mse:.10f}")
#     print(f"ARD = {ard:.4f}%")
#     print(f"相对误差 <= 1% 的点数: {within_1pct}")
#     print(f"相对误差 <= 5% 的点数: {within_5pct}")
#     print(f"相对误差 <= 10% 的点数: {within_10pct}")
#
#     return relative_error, {
#         "Dataset": name,
#         "R2": r2,
#         "MSE": mse,
#         "ARD_%": ard,
#         "within_1pct": within_1pct,
#         "within_5pct": within_5pct,
#         "within_10pct": within_10pct
#     }
#
#
# # ============================================================
# # 14. 训练集 / 测试集预测与评价
# # ============================================================
# y_train_pred = model.predict(X_train)
#
# train_relative_error, train_summary = evaluate_dataset(
#     y_train,
#     y_train_pred,
#     "训练集"
# )
#
# y_test_pred = model.predict(X_test)
#
# test_relative_error, test_summary = evaluate_dataset(
#     y_test,
#     y_test_pred,
#     "测试集"
# )
#
#
# # ============================================================
# # 15. 保存预测结果
# # ============================================================
# train_result = pd.DataFrame({
#     "Set": "Train",
#     "Material_ID": id_train,
#     "Temperature (K)": temp_train,
#     "slope": slope_train_point,
#     "Exergy_measured": y_train,
#     "Exergy_predicted": y_train_pred,
#     "Absolute Error": np.abs(y_train - y_train_pred),
#     "Relative Error (%)": train_relative_error
# })
#
# test_result = pd.DataFrame({
#     "Set": "Test",
#     "Material_ID": id_test,
#     "Temperature (K)": temp_test,
#     "slope": slope_test_point,
#     "Exergy_measured": y_test,
#     "Exergy_predicted": y_test_pred,
#     "Absolute Error": np.abs(y_test - y_test_pred),
#     "Relative Error (%)": test_relative_error
# })
#
# all_result = pd.concat(
#     [train_result, test_result],
#     ignore_index=True
# )
#
# result_file = "Exergy_RF_with_slope_ExtraTrees_submodels_train_test_by_material.xlsx"
#
# all_result.to_excel(
#     result_file,
#     index=False
# )
#
# print(f"\n预测结果已保存为: {result_file}")
#
#
# # ============================================================
# # 16. 保存最终 RF 汇总
# # ============================================================
# summary_df = pd.DataFrame([
#     [
#         "Final_RF_with_slope_ExtraTrees_submodels",
#         "train",
#         train_summary["R2"],
#         train_summary["MSE"],
#         train_summary["ARD_%"],
#         train_summary["within_1pct"],
#         train_summary["within_5pct"],
#         train_summary["within_10pct"]
#     ],
#     [
#         "Final_RF_with_slope_ExtraTrees_submodels",
#         "test",
#         test_summary["R2"],
#         test_summary["MSE"],
#         test_summary["ARD_%"],
#         test_summary["within_1pct"],
#         test_summary["within_5pct"],
#         test_summary["within_10pct"]
#     ]
# ], columns=[
#     "Model",
#     "Dataset",
#     "R2",
#     "MSE",
#     "ARD_%",
#     "within_1pct",
#     "within_5pct",
#     "within_10pct"
# ])
#
# summary_file = "Exergy_RF_with_slope_ExtraTrees_submodels_summary.xlsx"
#
# summary_df.to_excel(
#     summary_file,
#     index=False
# )
#
# print(f"最终 RF 汇总结果已保存为: {summary_file}")
#
#
# # ============================================================
# # 17. 保存 slope 信息
# # ============================================================
# slope_info_df = pd.DataFrame({
#     "Material_ID": material_ids_valid,
#     "Exergy_500_pred": Exergy_500_pred_valid,
#     "Exergy_Tb_pred": Exergy_Tb_pred_valid,
#     "Tb_pred": Tb_pred_valid,
#     "slope": slope_valid.flatten()
# })
#
# slope_file = "Exergy_RF_slope_values_ExtraTrees_submodels.xlsx"
#
# slope_info_df.to_excel(
#     slope_file,
#     index=False
# )
#
# print(f"slope 信息已保存为: {slope_file}")
#
#
# # ============================================================
# # 18. 保存子模型评价
# # ============================================================
# submodel_summary_df = pd.DataFrame([
#     sub_500_metrics,
#     sub_Tb_metrics,
#     sub_Tb_pred_metrics
# ])
#
# submodel_summary_file = "Exergy_RF_slope_submodel_summary_ExtraTrees.xlsx"
#
# submodel_summary_df.to_excel(
#     submodel_summary_file,
#     index=False
# )
#
# print(f"子模型评价已保存为: {submodel_summary_file}")
#
#
# # ============================================================
# # 19. 保存特征重要性
# # ============================================================
# feature_names = [f"Group_{i + 1}" for i in range(19)] + [
#     "Temperature",
#     "slope"
# ]
#
# feature_importance_df = pd.DataFrame({
#     "Feature": feature_names,
#     "Importance": model.feature_importances_
# }).sort_values(by="Importance", ascending=False)
#
# importance_file = "Exergy_RF_with_slope_ExtraTrees_submodels_feature_importance.xlsx"
#
# feature_importance_df.to_excel(
#     importance_file,
#     index=False
# )
#
# print(f"特征重要性已保存为: {importance_file}")



import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


# ============================================================
# 0. 参数区
# ============================================================
main_file = "Pure component exergy 205.xlsx"
main_sheet = "Sheet1"

normal_file = "selected_25_descriptors_normal.xlsx"
boiling_file = "selected_25_descriptors_boiling.xlsx"

target_500 = "ASPEN Exergy at 500k Temperature(j/mol)"
target_Tb_exergy = "ASPEN Exergy at BoilingTemperature(j/mol)"

T_ref = 500.0
random_state = 49


# ============================================================
# 最终 RF 参数：和无 slope 模型保持一致
# ============================================================
FINAL_RF_PARAMS = dict(
    n_estimators=200,
    max_depth=10,
    min_samples_split=5,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1
)


# ============================================================
# 子模型参数：ExtraTreesRegressor
# ============================================================
SUBMODEL_ET_PARAMS = dict(
    n_estimators=1000,
    max_depth=None,
    min_samples_split=2,
    min_samples_leaf=1,
    max_features=1.0,
    bootstrap=False,
    random_state=42,
    n_jobs=-1
)


# ============================================================
# 1. 读取主数据
# ============================================================
df = pd.read_excel(main_file, sheet_name=main_sheet).copy()

material_id_col = df.columns[0]

group_cols = df.columns[12:31]   # 19个基团
temp_cols = df.columns[31:41]    # 10个温度点
exergy_cols = df.columns[41:51]  # 10个 Exergy 点

tb_col = df.columns[5]


# ============================================================
# 2. 数值化主数据
# ============================================================
for col in list(group_cols) + list(temp_cols) + list(exergy_cols) + [tb_col]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=[material_id_col]).copy().reset_index(drop=True)


# ============================================================
# 3. 子模型 1：500 K Exergy
#    子模型不划分训练集/测试集，使用全体数据训练
# ============================================================
df_500 = pd.read_excel(normal_file).copy()

if len(df_500) != len(df):
    raise ValueError(
        f"{normal_file} 与主文件行数不一致：{len(df_500)} vs {len(df)}。"
        f"当前代码默认两个文件逐行对应。"
    )

X_500_all = df_500.drop(columns=[target_500]).apply(pd.to_numeric, errors="coerce")
y_500_all = pd.to_numeric(df_500[target_500], errors="coerce")

valid_500_mask = (
    np.isfinite(X_500_all).all(axis=1)
    & np.isfinite(y_500_all)
)

et_500 = ExtraTreesRegressor(**SUBMODEL_ET_PARAMS)

et_500.fit(
    X_500_all.loc[valid_500_mask],
    y_500_all.loc[valid_500_mask]
)

Exergy_500_pred_all = np.full(len(df), np.nan, dtype=float)

predict_500_mask = np.isfinite(X_500_all).all(axis=1)

Exergy_500_pred_all[predict_500_mask] = et_500.predict(
    X_500_all.loc[predict_500_mask]
)


# ============================================================
# 4. 子模型 2：Boiling Temperature Exergy
#    子模型不划分训练集/测试集，使用全体数据训练
# ============================================================
df_Tb = pd.read_excel(boiling_file).copy()

if len(df_Tb) != len(df):
    raise ValueError(
        f"{boiling_file} 与主文件行数不一致：{len(df_Tb)} vs {len(df)}。"
        f"当前代码默认两个文件逐行对应。"
    )

X_Tb_all = df_Tb.drop(columns=[target_Tb_exergy]).apply(pd.to_numeric, errors="coerce")
y_Tb_all = pd.to_numeric(df_Tb[target_Tb_exergy], errors="coerce")

valid_Tb_exergy_mask = (
    np.isfinite(X_Tb_all).all(axis=1)
    & np.isfinite(y_Tb_all)
)

et_Tb = ExtraTreesRegressor(**SUBMODEL_ET_PARAMS)

et_Tb.fit(
    X_Tb_all.loc[valid_Tb_exergy_mask],
    y_Tb_all.loc[valid_Tb_exergy_mask]
)

Exergy_Tb_pred_all = np.full(len(df), np.nan, dtype=float)

predict_Tb_exergy_mask = np.isfinite(X_Tb_all).all(axis=1)

Exergy_Tb_pred_all[predict_Tb_exergy_mask] = et_Tb.predict(
    X_Tb_all.loc[predict_Tb_exergy_mask]
)


# ============================================================
# 5. 子模型 3：Tb 预测模型
# ============================================================
Nk_all_df = df[group_cols].apply(pd.to_numeric, errors="coerce")
Tb_raw_all = pd.to_numeric(df[tb_col], errors="coerce").values

poly = PolynomialFeatures(degree=2, include_bias=False)

valid_group_mask = np.isfinite(Nk_all_df).all(axis=1)

Nk_poly_valid = poly.fit_transform(
    Nk_all_df.loc[valid_group_mask]
)

Nk_poly_all = np.full(
    (len(df), Nk_poly_valid.shape[1]),
    np.nan,
    dtype=float
)

Nk_poly_all[valid_group_mask] = Nk_poly_valid

valid_tb_mask = (
    np.isfinite(Tb_raw_all)
    & np.isfinite(Nk_poly_all).all(axis=1)
)

et_Tb_pred = ExtraTreesRegressor(**SUBMODEL_ET_PARAMS)

et_Tb_pred.fit(
    Nk_poly_all[valid_tb_mask],
    Tb_raw_all[valid_tb_mask]
)

Tb_pred_all = np.full(len(df), np.nan, dtype=float)

predict_tb_mask = np.isfinite(Nk_poly_all).all(axis=1)

Tb_pred_all[predict_tb_mask] = et_Tb_pred.predict(
    Nk_poly_all[predict_tb_mask]
)


# ============================================================
# 6. 计算 slope
#    slope = (Exergy_Tb_pred - Exergy_500_pred) / (Tb_pred - 500)
# ============================================================
denom = Tb_pred_all - T_ref

slope_values = np.full(len(df), np.nan, dtype=float)

valid_slope_mask = (
    np.isfinite(Exergy_Tb_pred_all)
    & np.isfinite(Exergy_500_pred_all)
    & np.isfinite(Tb_pred_all)
    & (np.abs(denom) > 1e-12)
)

slope_values[valid_slope_mask] = (
    Exergy_Tb_pred_all[valid_slope_mask]
    - Exergy_500_pred_all[valid_slope_mask]
) / denom[valid_slope_mask]

df["slope"] = slope_values
df["Exergy_500_pred"] = Exergy_500_pred_all
df["Exergy_Tb_pred"] = Exergy_Tb_pred_all
df["Tb_pred"] = Tb_pred_all


# ============================================================
# 7. 子模型诊断评价
# ============================================================
def eval_submodel(y_true, y_pred, name):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = np.isfinite(y_true) & np.isfinite(y_pred)

    if not np.any(mask):
        print(f"\n{name}: 无有效评价样本")
        return {
            "Model": name,
            "Dataset": "all_data_diagnostic",
            "R2": np.nan,
            "MSE": np.nan,
            "ARD_%": np.nan,
            "within_1pct": 0,
            "within_5pct": 0,
            "within_10pct": 0
        }

    y_true_valid = y_true[mask]
    y_pred_valid = y_pred[mask]

    r2 = r2_score(y_true_valid, y_pred_valid)
    mse = mean_squared_error(y_true_valid, y_pred_valid)

    relative_error = np.full_like(y_true_valid, np.nan, dtype=float)
    nonzero_mask = np.abs(y_true_valid) > 1e-12

    if np.any(nonzero_mask):
        relative_error[nonzero_mask] = np.abs(
            (y_pred_valid[nonzero_mask] - y_true_valid[nonzero_mask])
            / y_true_valid[nonzero_mask]
        ) * 100
        ard = np.nanmean(relative_error)
    else:
        ard = np.nan

    within_1pct = np.sum(relative_error <= 1)
    within_5pct = np.sum(relative_error <= 5)
    within_10pct = np.sum(relative_error <= 10)

    print(f"\n{name}:")
    print(f"R2  = {r2:.6f}")
    print(f"MSE = {mse:.10f}")
    print(f"ARD = {ard:.4f}%")
    print(f"误差 <= 1%  点数: {within_1pct}")
    print(f"误差 <= 5%  点数: {within_5pct}")
    print(f"误差 <= 10% 点数: {within_10pct}")

    return {
        "Model": name,
        "Dataset": "all_data_diagnostic",
        "R2": r2,
        "MSE": mse,
        "ARD_%": ard,
        "within_1pct": within_1pct,
        "within_5pct": within_5pct,
        "within_10pct": within_10pct
    }


sub_500_metrics = eval_submodel(
    y_500_all.values,
    Exergy_500_pred_all,
    "Exergy_500K_ExtraTrees_submodel_all_data"
)

sub_Tb_metrics = eval_submodel(
    y_Tb_all.values,
    Exergy_Tb_pred_all,
    "Exergy_boiling_ExtraTrees_submodel_all_data"
)

sub_Tb_pred_metrics = eval_submodel(
    Tb_raw_all,
    Tb_pred_all,
    "Tb_ExtraTrees_submodel_all_data"
)


# ============================================================
# 8. 物质级有效筛选
# ============================================================
Nk_all = df[group_cols].to_numpy(dtype=float)
T_all = df[temp_cols].to_numpy(dtype=float)
Exergy_all = df[exergy_cols].to_numpy(dtype=float)
slope_all = df["slope"].to_numpy(dtype=float).reshape(-1, 1)
material_ids_all = df[material_id_col].values

valid_target_mask = np.isfinite(Exergy_all)
valid_target_mask = valid_target_mask.all(axis=1)

valid_feature_mask = (
    np.isfinite(Nk_all).all(axis=1)
    & np.isfinite(T_all).all(axis=1)
    & np.isfinite(slope_all).flatten()
)

valid_mask = valid_target_mask & valid_feature_mask

Nk_valid = Nk_all[valid_mask]
T_valid = T_all[valid_mask]
Exergy_valid = Exergy_all[valid_mask]
slope_valid = slope_all[valid_mask]
material_ids_valid = material_ids_all[valid_mask]

Exergy_500_pred_valid = Exergy_500_pred_all[valid_mask]
Exergy_Tb_pred_valid = Exergy_Tb_pred_all[valid_mask]
Tb_pred_valid = Tb_pred_all[valid_mask]

print("\n========== 数据清洗后 ==========")
print(f"有效物质数: {len(material_ids_valid)}")


# ============================================================
# 9. 最终 RF 模型按物质 8:2 划分
# ============================================================
material_indices = np.arange(len(material_ids_valid))

train_idx, test_idx = train_test_split(
    material_indices,
    test_size=0.2,
    random_state=random_state
)

print("\n========== 最终 RF 模型按物质划分 ==========")
print(f"训练集物质数: {len(train_idx)}")
print(f"测试集物质数: {len(test_idx)}")


# ============================================================
# 10. 构建最终点级数据集
# ============================================================
def build_point_dataset(Nk, T, Exergy, slope, material_ids):
    """
    最终 RF 特征：
        19个基团 + Temperature + slope
    """

    X = np.hstack([
        Nk.repeat(10, axis=0),
        T.flatten().reshape(-1, 1),
        slope.repeat(10, axis=0)
    ])

    y = Exergy.flatten()

    expanded_ids = np.repeat(material_ids, 10)
    expanded_T = T.flatten()
    expanded_slope = slope.repeat(10, axis=0).flatten()

    finite_mask = (
        np.isfinite(y)
        & np.isfinite(X).all(axis=1)
    )

    return (
        X[finite_mask],
        y[finite_mask],
        expanded_ids[finite_mask],
        expanded_T[finite_mask],
        expanded_slope[finite_mask]
    )


X_train, y_train, id_train, temp_train, slope_train_point = build_point_dataset(
    Nk_valid[train_idx],
    T_valid[train_idx],
    Exergy_valid[train_idx],
    slope_valid[train_idx],
    material_ids_valid[train_idx]
)

X_test, y_test, id_test, temp_test, slope_test_point = build_point_dataset(
    Nk_valid[test_idx],
    T_valid[test_idx],
    Exergy_valid[test_idx],
    slope_valid[test_idx],
    material_ids_valid[test_idx]
)

print("\n========== 最终 RF 点级数据 ==========")
print(f"训练集样本点数: {len(X_train)}")
print(f"测试集样本点数: {len(X_test)}")
print(f"最终模型特征数: {X_train.shape[1]}")

if X_train.shape[1] != 21:
    raise ValueError(
        f"当前特征数为 {X_train.shape[1]}，预期为 21：19个基团 + Temperature + slope。"
    )


# ============================================================
# 11. 最终 RF 模型
# ============================================================
model = RandomForestRegressor(**FINAL_RF_PARAMS)


# ============================================================
# 12. 训练最终 RF 模型
# ============================================================
print("\n开始训练最终 RF 模型...")
model.fit(X_train, y_train)

print("\n最终 RF 模型参数:")
print(model)


# ============================================================
# 13. 最终模型评价函数
# ============================================================
def evaluate_dataset(y_true, y_pred, name="数据集", strict_less=False):
    """
    strict_less=False：统计 <=1%, <=5%, <=10%
    strict_less=True ：统计 <1%, <5%, <10%
    """

    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    finite_mask = np.isfinite(y_true) & np.isfinite(y_pred)

    y_true_valid = y_true[finite_mask]
    y_pred_valid = y_pred[finite_mask]

    relative_error = np.full_like(y_true, np.nan, dtype=float)

    if len(y_true_valid) == 0:
        print(f"\n{name}评估结果: 无有效样本")

        return relative_error, {
            "Dataset": name,
            "R2": np.nan,
            "MSE": np.nan,
            "ARD_%": np.nan,
            "within_1pct": 0,
            "within_5pct": 0,
            "within_10pct": 0
        }

    r2 = r2_score(y_true_valid, y_pred_valid)
    mse = mean_squared_error(y_true_valid, y_pred_valid)

    relative_error_valid = np.full_like(y_true_valid, np.nan, dtype=float)

    nonzero_mask = np.abs(y_true_valid) > 1e-12

    if np.any(nonzero_mask):
        relative_error_valid[nonzero_mask] = np.abs(
            (y_pred_valid[nonzero_mask] - y_true_valid[nonzero_mask])
            / y_true_valid[nonzero_mask]
        ) * 100
        ard = np.nanmean(relative_error_valid)
    else:
        ard = np.nan

    relative_error[finite_mask] = relative_error_valid

    if strict_less:
        within_1pct = np.sum(relative_error_valid < 1)
        within_5pct = np.sum(relative_error_valid < 5)
        within_10pct = np.sum(relative_error_valid < 10)
    else:
        within_1pct = np.sum(relative_error_valid <= 1)
        within_5pct = np.sum(relative_error_valid <= 5)
        within_10pct = np.sum(relative_error_valid <= 10)

    print(f"\n{name}评估结果:")
    print(f"R2  = {r2:.6f}")
    print(f"MSE = {mse:.10f}")
    print(f"ARD = {ard:.4f}%")

    if strict_less:
        print(f"相对误差 < 1% 的点数: {within_1pct}")
        print(f"相对误差 < 5% 的点数: {within_5pct}")
        print(f"相对误差 < 10% 的点数: {within_10pct}")
    else:
        print(f"相对误差 <= 1% 的点数: {within_1pct}")
        print(f"相对误差 <= 5% 的点数: {within_5pct}")
        print(f"相对误差 <= 10% 的点数: {within_10pct}")

    return relative_error, {
        "Dataset": name,
        "R2": r2,
        "MSE": mse,
        "ARD_%": ard,
        "within_1pct": within_1pct,
        "within_5pct": within_5pct,
        "within_10pct": within_10pct
    }


# ============================================================
# 14. 训练集 / 测试集预测与评价
# ============================================================
y_train_pred = model.predict(X_train)

train_relative_error, train_summary = evaluate_dataset(
    y_train,
    y_train_pred,
    "训练集",
    strict_less=False
)

y_test_pred = model.predict(X_test)

test_relative_error, test_summary = evaluate_dataset(
    y_test,
    y_test_pred,
    "测试集",
    strict_less=False
)


# ============================================================
# 14.1 完整数据集统计：训练集 + 测试集
# ============================================================
y_all_true = np.concatenate([
    y_train,
    y_test
])

y_all_pred = np.concatenate([
    y_train_pred,
    y_test_pred
])

id_all = np.concatenate([
    id_train,
    id_test
])

temp_all = np.concatenate([
    temp_train,
    temp_test
])

slope_all_point = np.concatenate([
    slope_train_point,
    slope_test_point
])

all_relative_error, all_summary = evaluate_dataset(
    y_all_true,
    y_all_pred,
    "完整数据集 train + test",
    strict_less=True
)

print("\nExergy RF + slope ExtraTrees 完整数据集预测偏差 1%，5%，10%分别为：")
print(all_summary["within_1pct"])
print(all_summary["within_5pct"])
print(all_summary["within_10pct"])


# ============================================================
# 15. 保存预测结果
# ============================================================
train_result = pd.DataFrame({
    "Set": "Train",
    "Material_ID": id_train,
    "Temperature (K)": temp_train,
    "slope": slope_train_point,
    "Exergy_measured": y_train,
    "Exergy_predicted": y_train_pred,
    "Absolute Error": np.abs(y_train - y_train_pred),
    "Relative Error (%)": train_relative_error
})

test_result = pd.DataFrame({
    "Set": "Test",
    "Material_ID": id_test,
    "Temperature (K)": temp_test,
    "slope": slope_test_point,
    "Exergy_measured": y_test,
    "Exergy_predicted": y_test_pred,
    "Absolute Error": np.abs(y_test - y_test_pred),
    "Relative Error (%)": test_relative_error
})

all_result = pd.DataFrame({
    "Set": "All_train_plus_test",
    "Material_ID": id_all,
    "Temperature (K)": temp_all,
    "slope": slope_all_point,
    "Exergy_measured": y_all_true,
    "Exergy_predicted": y_all_pred,
    "Absolute Error": np.abs(y_all_true - y_all_pred),
    "Relative Error (%)": all_relative_error
})


# ============================================================
# 16. 保存到 Excel
# ============================================================
result_file = "Exergy_RF_with_slope_ExtraTrees_submodels_train_test_by_material.xlsx"

with pd.ExcelWriter(result_file, engine="xlsxwriter") as writer:
    pd.concat(
        [train_result, test_result],
        axis=0,
        ignore_index=True
    ).to_excel(
        writer,
        sheet_name="train_test_predictions",
        index=False
    )

    all_result.to_excel(
        writer,
        sheet_name="all_predictions",
        index=False
    )

print(f"\n预测结果已保存为: {result_file}")


# ============================================================
# 17. 保存最终 RF 汇总
# ============================================================
summary_df = pd.DataFrame([
    [
        "Final_RF_with_slope_ExtraTrees_submodels",
        "train",
        train_summary["R2"],
        train_summary["MSE"],
        train_summary["ARD_%"],
        train_summary["within_1pct"],
        train_summary["within_5pct"],
        train_summary["within_10pct"]
    ],
    [
        "Final_RF_with_slope_ExtraTrees_submodels",
        "test",
        test_summary["R2"],
        test_summary["MSE"],
        test_summary["ARD_%"],
        test_summary["within_1pct"],
        test_summary["within_5pct"],
        test_summary["within_10pct"]
    ],
    [
        "Final_RF_with_slope_ExtraTrees_submodels",
        "all_train_plus_test",
        all_summary["R2"],
        all_summary["MSE"],
        all_summary["ARD_%"],
        all_summary["within_1pct"],
        all_summary["within_5pct"],
        all_summary["within_10pct"]
    ]
], columns=[
    "Model",
    "Dataset",
    "R2",
    "MSE",
    "ARD_%",
    "within_1pct",
    "within_5pct",
    "within_10pct"
])

summary_file = "Exergy_RF_with_slope_ExtraTrees_submodels_summary.xlsx"

summary_df.to_excel(
    summary_file,
    index=False
)

print(f"最终 RF 汇总结果已保存为: {summary_file}")


# ============================================================
# 18. 保存 slope 信息
# ============================================================
slope_info_df = pd.DataFrame({
    "Material_ID": material_ids_valid,
    "Exergy_500_pred": Exergy_500_pred_valid,
    "Exergy_Tb_pred": Exergy_Tb_pred_valid,
    "Tb_pred": Tb_pred_valid,
    "slope": slope_valid.flatten()
})

slope_file = "Exergy_RF_slope_values_ExtraTrees_submodels.xlsx"

slope_info_df.to_excel(
    slope_file,
    index=False
)

print(f"slope 信息已保存为: {slope_file}")


# ============================================================
# 19. 保存子模型评价
# ============================================================
submodel_summary_df = pd.DataFrame([
    sub_500_metrics,
    sub_Tb_metrics,
    sub_Tb_pred_metrics
])

submodel_summary_file = "Exergy_RF_slope_submodel_summary_ExtraTrees.xlsx"

submodel_summary_df.to_excel(
    submodel_summary_file,
    index=False
)

print(f"子模型评价已保存为: {submodel_summary_file}")


# ============================================================
# 20. 保存特征重要性
# ============================================================
feature_names = [f"Group_{i + 1}" for i in range(19)] + [
    "Temperature",
    "slope"
]

feature_importance_df = pd.DataFrame({
    "Feature": feature_names,
    "Importance": model.feature_importances_
}).sort_values(by="Importance", ascending=False)

importance_file = "Exergy_RF_with_slope_ExtraTrees_submodels_feature_importance.xlsx"

feature_importance_df.to_excel(
    importance_file,
    index=False
)

print(f"特征重要性已保存为: {importance_file}")


# ============================================================
# 21. 输出模型结构记录
# ============================================================
print("\n当前 Exergy RF + slope ExtraTrees 模型结构:")
print("Exergy_500K_submodel: ExtraTreesRegressor(n_estimators=1000, max_features=1.0, random_state=42, n_jobs=-1)")
print("Exergy_Tb_submodel: ExtraTreesRegressor(n_estimators=1000, max_features=1.0, random_state=42, n_jobs=-1)")
print("Tb_submodel: ExtraTreesRegressor(n_estimators=1000, max_features=1.0, random_state=42, n_jobs=-1), input = PolynomialFeatures(Nk, degree=2)")
print("slope = (Exergy_Tb_pred - Exergy_500_pred) / (Tb_pred - 500)")
print("Final target: ordinary Exergy")
print("Final model: RandomForestRegressor(n_estimators=200, max_depth=10, min_samples_split=5, min_samples_leaf=2, random_state=42, n_jobs=-1)")
print("Final input features: 19 group counts + Temperature + slope")
print("Split: material-level 8:2 split, random_state=49")
print("Final all-data statistics use strict thresholds: <1%, <5%, <10%")