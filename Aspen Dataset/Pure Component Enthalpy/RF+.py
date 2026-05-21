# import pandas as pd
# import numpy as np
#
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.linear_model import HuberRegressor
# from sklearn.preprocessing import PolynomialFeatures, StandardScaler
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split
#
#
# # ============================================================
# # 1. 数据加载
# # ============================================================
# df = pd.read_excel("Pure component enthalpy 209.xlsx", sheet_name="Sheet1").copy()
#
# material_id_col = df.columns[0]
#
# group_cols = df.columns[12:31]   # 19个基团
# temp_cols = df.columns[31:41]    # 10个温度点
# enthalpy_cols = df.columns[41:51]  # 10个焓值点
#
#
# # ============================================================
# # 2. 数值化主数据
# # ============================================================
# for col in list(group_cols) + list(temp_cols) + list(enthalpy_cols):
#     df[col] = pd.to_numeric(df[col], errors="coerce")
#
# df = df.dropna(subset=[material_id_col]).copy().reset_index(drop=True)
#
#
# # ============================================================
# # 3. 子模型 1：enthalpy at normal temperature
# #    子模型不划分训练集/测试集
# # ============================================================
# df_298 = pd.read_excel("selected_25_descriptors_normal.xlsx").copy()
#
# target_298 = "enthalpy at normal temperature"
#
# if len(df_298) != len(df):
#     raise ValueError(
#         f"selected_25_descriptors_normal.xlsx 与主文件行数不一致："
#         f"{len(df_298)} vs {len(df)}。当前代码默认逐行对应。"
#     )
#
# X_298_all = df_298.drop(columns=[target_298]).apply(pd.to_numeric, errors="coerce")
# y_298_all = pd.to_numeric(df_298[target_298], errors="coerce")
#
# valid_298_mask = (
#     np.isfinite(X_298_all).all(axis=1)
#     & np.isfinite(y_298_all)
# )
#
# rf_298 = RandomForestRegressor(
#     random_state=42,
#     n_jobs=-1
# )
#
# rf_298.fit(
#     X_298_all.loc[valid_298_mask],
#     y_298_all.loc[valid_298_mask]
# )
#
# H_298_pred_all = np.full(len(df), np.nan, dtype=float)
#
# predict_298_mask = np.isfinite(X_298_all).all(axis=1)
#
# H_298_pred_all[predict_298_mask] = rf_298.predict(
#     X_298_all.loc[predict_298_mask]
# )
#
#
# # ============================================================
# # 4. 子模型 2：enthalpy at boiling temperature
# #    子模型不划分训练集/测试集
# # ============================================================
# df_Tb = pd.read_excel("selected_25_descriptors_boiling.xlsx").copy()
#
# target_Tb = "enthalpy at boiling temperature"
#
# if len(df_Tb) != len(df):
#     raise ValueError(
#         f"selected_25_descriptors_boiling.xlsx 与主文件行数不一致："
#         f"{len(df_Tb)} vs {len(df)}。当前代码默认逐行对应。"
#     )
#
# X_Tb_all = df_Tb.drop(columns=[target_Tb]).apply(pd.to_numeric, errors="coerce")
# y_Tb_all = pd.to_numeric(df_Tb[target_Tb], errors="coerce")
#
# valid_H_Tb_mask = (
#     np.isfinite(X_Tb_all).all(axis=1)
#     & np.isfinite(y_Tb_all)
# )
#
# rf_Tb = RandomForestRegressor(
#     random_state=42,
#     n_jobs=-1
# )
#
# rf_Tb.fit(
#     X_Tb_all.loc[valid_H_Tb_mask],
#     y_Tb_all.loc[valid_H_Tb_mask]
# )
#
# H_Tb_pred_all = np.full(len(df), np.nan, dtype=float)
#
# predict_H_Tb_mask = np.isfinite(X_Tb_all).all(axis=1)
#
# H_Tb_pred_all[predict_H_Tb_mask] = rf_Tb.predict(
#     X_Tb_all.loc[predict_H_Tb_mask]
# )
#
#
# # ============================================================
# # 5. 子模型 3：Tb 预测模型
# #    子模型不划分训练集/测试集
# # ============================================================
# Nk_all_df = df[group_cols].apply(pd.to_numeric, errors="coerce")
# Tb_raw_all = pd.to_numeric(df.iloc[:, 5], errors="coerce").values
#
# Tb0 = 222.543
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
# scaler = StandardScaler()
#
# valid_tb_train_mask = (
#     np.isfinite(Tb_raw_all)
#     & np.isfinite(Nk_poly_all).all(axis=1)
# )
#
# Nk_scaled_train = scaler.fit_transform(
#     Nk_poly_all[valid_tb_train_mask]
# )
#
# model_Tb = HuberRegressor(max_iter=10000)
#
# model_Tb.fit(
#     Nk_scaled_train,
#     np.exp(Tb_raw_all[valid_tb_train_mask] / Tb0)
# )
#
# Tb_pred_all = np.full(len(df), np.nan, dtype=float)
#
# predict_tb_mask = np.isfinite(Nk_poly_all).all(axis=1)
#
# Nk_scaled_predict = scaler.transform(
#     Nk_poly_all[predict_tb_mask]
# )
#
# Tb_pred_all[predict_tb_mask] = Tb0 * np.log(
#     np.clip(
#         model_Tb.predict(Nk_scaled_predict),
#         1e-6,
#         None
#     )
# )
#
#
# # ============================================================
# # 6. 计算 slope
# # ============================================================
# T_ref = 298.15
#
# denom = Tb_pred_all - T_ref
#
# slope_values = np.full(len(df), np.nan, dtype=float)
#
# valid_slope_mask = (
#     np.isfinite(H_Tb_pred_all)
#     & np.isfinite(H_298_pred_all)
#     & np.isfinite(Tb_pred_all)
#     & (np.abs(denom) > 1e-12)
# )
#
# slope_values[valid_slope_mask] = (
#     H_Tb_pred_all[valid_slope_mask]
#     - H_298_pred_all[valid_slope_mask]
# ) / denom[valid_slope_mask]
#
# df["slope"] = slope_values
# df["H_298_pred"] = H_298_pred_all
# df["H_Tb_pred"] = H_Tb_pred_all
# df["Tb_pred"] = Tb_pred_all
#
#
# # ============================================================
# # 7. 子模型诊断评价
# #    注意：这里是全数据拟合后的诊断，不是独立测试集评价
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
#             "MSE": np.nan
#         }
#
#     r2 = r2_score(y_true[mask], y_pred[mask])
#     mse = mean_squared_error(y_true[mask], y_pred[mask])
#
#     print(f"\n{name}:")
#     print(f"R2  = {r2:.6f}")
#     print(f"MSE = {mse:.10f}")
#
#     return {
#         "Model": name,
#         "R2": r2,
#         "MSE": mse
#     }
#
#
# sub_298_metrics = eval_submodel(
#     y_298_all.values,
#     H_298_pred_all,
#     "enthalpy_normal_submodel_all_data"
# )
#
# sub_Tb_metrics = eval_submodel(
#     y_Tb_all.values,
#     H_Tb_pred_all,
#     "enthalpy_boiling_submodel_all_data"
# )
#
# sub_Tb_pred_metrics = eval_submodel(
#     Tb_raw_all,
#     Tb_pred_all,
#     "Tb_submodel_all_data"
# )
#
#
# # ============================================================
# # 8. 物质级有效筛选
# # ============================================================
# Nk_all = df[group_cols].to_numpy(dtype=float)
# T_all = df[temp_cols].to_numpy(dtype=float)
# H_all = df[enthalpy_cols].to_numpy(dtype=float)
# slope_all = df["slope"].to_numpy(dtype=float).reshape(-1, 1)
# material_ids_all = df[material_id_col].values
#
# valid_target_mask = np.isfinite(H_all)
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
# H_valid = H_all[valid_mask]
# slope_valid = slope_all[valid_mask]
# material_ids_valid = material_ids_all[valid_mask]
#
# H_298_pred_valid = H_298_pred_all[valid_mask]
# H_Tb_pred_valid = H_Tb_pred_all[valid_mask]
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
#     random_state=42
# )
#
# print("\n========== 最终 RF 模型按物质划分 ==========")
# print(f"训练集物质数: {len(train_idx)}")
# print(f"测试集物质数: {len(test_idx)}")
#
#
# # ============================================================
# # 10. 构建点级数据集
# # ============================================================
# def build_point_dataset(Nk, T, H, slope, material_ids):
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
#     y = H.flatten()
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
#     H_valid[train_idx],
#     slope_valid[train_idx],
#     material_ids_valid[train_idx]
# )
#
# X_test, y_test, id_test, temp_test, slope_test_point = build_point_dataset(
#     Nk_valid[test_idx],
#     T_valid[test_idx],
#     H_valid[test_idx],
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
# # 11. 定义最终随机森林模型
# # ============================================================
# model = RandomForestRegressor(
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
# # 12. 训练最终 RF 模型
# # ============================================================
# print("\n开始训练最终 RF 模型...")
# model.fit(X_train, y_train)
#
#
# # ============================================================
# # 13. 评价函数
# # ============================================================
# def evaluate_dataset(y_true, y_pred, name="数据集"):
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#
#     r2 = r2_score(y_true, y_pred)
#     mse = mean_squared_error(y_true, y_pred)
#
#     relative_error = np.full_like(y_true, np.nan, dtype=float)
#
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
# # 14. 训练集 / 测试集预测与评估
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
#     "Enthalpy_measured": y_train,
#     "Enthalpy_predicted": y_train_pred,
#     "Absolute Error": np.abs(y_train - y_train_pred),
#     "Relative Error (%)": train_relative_error
# })
#
# test_result = pd.DataFrame({
#     "Set": "Test",
#     "Material_ID": id_test,
#     "Temperature (K)": temp_test,
#     "slope": slope_test_point,
#     "Enthalpy_measured": y_test,
#     "Enthalpy_predicted": y_test_pred,
#     "Absolute Error": np.abs(y_test - y_test_pred),
#     "Relative Error (%)": test_relative_error
# })
#
# all_result = pd.concat(
#     [train_result, test_result],
#     ignore_index=True
# )
#
# result_file = "Enthalpy_RF_with_slope_train_test_by_material.xlsx"
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
#         "Final_RF_with_slope",
#         "train",
#         train_summary["R2"],
#         train_summary["MSE"],
#         train_summary["ARD_%"],
#         train_summary["within_1pct"],
#         train_summary["within_5pct"],
#         train_summary["within_10pct"]
#     ],
#     [
#         "Final_RF_with_slope",
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
# summary_file = "Enthalpy_RF_with_slope_summary.xlsx"
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
#     "H_298_pred": H_298_pred_valid,
#     "H_Tb_pred": H_Tb_pred_valid,
#     "Tb_pred": Tb_pred_valid,
#     "slope": slope_valid.flatten()
# })
#
# slope_file = "Enthalpy_RF_slope_values.xlsx"
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
#     sub_298_metrics,
#     sub_Tb_metrics,
#     sub_Tb_pred_metrics
# ])
#
# submodel_summary_file = "Enthalpy_RF_slope_submodel_summary.xlsx"
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
# importance_file = "Enthalpy_RF_with_slope_feature_importance.xlsx"
#
# feature_importance_df.to_excel(
#     importance_file,
#     index=False
# )
#
# print(f"特征重要性已保存为: {importance_file}")



import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import HuberRegressor
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


# ============================================================
# 1. 数据加载
# ============================================================
df = pd.read_excel("Pure component enthalpy 209.xlsx", sheet_name="Sheet1").copy()

material_id_col = df.columns[0]

group_cols = df.columns[12:31]      # 19个基团
temp_cols = df.columns[31:41]       # 10个温度点
enthalpy_cols = df.columns[41:51]   # 10个焓值点


# ============================================================
# 2. 数值化主数据
# ============================================================
for col in list(group_cols) + list(temp_cols) + list(enthalpy_cols):
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=[material_id_col]).copy().reset_index(drop=True)


# ============================================================
# 3. 子模型 1：enthalpy at normal temperature
#    子模型不划分训练集/测试集
# ============================================================
df_298 = pd.read_excel("selected_25_descriptors_normal.xlsx").copy()

target_298 = "enthalpy at normal temperature"

if len(df_298) != len(df):
    raise ValueError(
        f"selected_25_descriptors_normal.xlsx 与主文件行数不一致："
        f"{len(df_298)} vs {len(df)}。当前代码默认逐行对应。"
    )

X_298_all = df_298.drop(columns=[target_298]).apply(pd.to_numeric, errors="coerce")
y_298_all = pd.to_numeric(df_298[target_298], errors="coerce")

valid_298_mask = (
    np.isfinite(X_298_all).all(axis=1)
    & np.isfinite(y_298_all)
)

rf_298 = RandomForestRegressor(
    random_state=42,
    n_jobs=-1
)

rf_298.fit(
    X_298_all.loc[valid_298_mask],
    y_298_all.loc[valid_298_mask]
)

H_298_pred_all = np.full(len(df), np.nan, dtype=float)

predict_298_mask = np.isfinite(X_298_all).all(axis=1)

H_298_pred_all[predict_298_mask] = rf_298.predict(
    X_298_all.loc[predict_298_mask]
)


# ============================================================
# 4. 子模型 2：enthalpy at boiling temperature
#    子模型不划分训练集/测试集
# ============================================================
df_Tb = pd.read_excel("selected_25_descriptors_boiling.xlsx").copy()

target_Tb = "enthalpy at boiling temperature"

if len(df_Tb) != len(df):
    raise ValueError(
        f"selected_25_descriptors_boiling.xlsx 与主文件行数不一致："
        f"{len(df_Tb)} vs {len(df)}。当前代码默认逐行对应。"
    )

X_Tb_all = df_Tb.drop(columns=[target_Tb]).apply(pd.to_numeric, errors="coerce")
y_Tb_all = pd.to_numeric(df_Tb[target_Tb], errors="coerce")

valid_H_Tb_mask = (
    np.isfinite(X_Tb_all).all(axis=1)
    & np.isfinite(y_Tb_all)
)

rf_Tb = RandomForestRegressor(
    random_state=42,
    n_jobs=-1
)

rf_Tb.fit(
    X_Tb_all.loc[valid_H_Tb_mask],
    y_Tb_all.loc[valid_H_Tb_mask]
)

H_Tb_pred_all = np.full(len(df), np.nan, dtype=float)

predict_H_Tb_mask = np.isfinite(X_Tb_all).all(axis=1)

H_Tb_pred_all[predict_H_Tb_mask] = rf_Tb.predict(
    X_Tb_all.loc[predict_H_Tb_mask]
)


# ============================================================
# 5. 子模型 3：Tb 预测模型
#    子模型不划分训练集/测试集
# ============================================================
Nk_all_df = df[group_cols].apply(pd.to_numeric, errors="coerce")
Tb_raw_all = pd.to_numeric(df.iloc[:, 5], errors="coerce").values

Tb0 = 222.543

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

scaler = StandardScaler()

valid_tb_train_mask = (
    np.isfinite(Tb_raw_all)
    & np.isfinite(Nk_poly_all).all(axis=1)
)

Nk_scaled_train = scaler.fit_transform(
    Nk_poly_all[valid_tb_train_mask]
)

model_Tb = HuberRegressor(max_iter=10000)

model_Tb.fit(
    Nk_scaled_train,
    np.exp(Tb_raw_all[valid_tb_train_mask] / Tb0)
)

Tb_pred_all = np.full(len(df), np.nan, dtype=float)

predict_tb_mask = np.isfinite(Nk_poly_all).all(axis=1)

Nk_scaled_predict = scaler.transform(
    Nk_poly_all[predict_tb_mask]
)

Tb_pred_all[predict_tb_mask] = Tb0 * np.log(
    np.clip(
        model_Tb.predict(Nk_scaled_predict),
        1e-6,
        None
    )
)


# ============================================================
# 6. 计算 slope
# ============================================================
T_ref = 298.15

denom = Tb_pred_all - T_ref

slope_values = np.full(len(df), np.nan, dtype=float)

valid_slope_mask = (
    np.isfinite(H_Tb_pred_all)
    & np.isfinite(H_298_pred_all)
    & np.isfinite(Tb_pred_all)
    & (np.abs(denom) > 1e-12)
)

slope_values[valid_slope_mask] = (
    H_Tb_pred_all[valid_slope_mask]
    - H_298_pred_all[valid_slope_mask]
) / denom[valid_slope_mask]

df["slope"] = slope_values
df["H_298_pred"] = H_298_pred_all
df["H_Tb_pred"] = H_Tb_pred_all
df["Tb_pred"] = Tb_pred_all


# ============================================================
# 7. 子模型诊断评价
#    注意：这里是全数据拟合后的诊断，不是独立测试集评价
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
            "MSE": np.nan
        }

    r2 = r2_score(y_true[mask], y_pred[mask])
    mse = mean_squared_error(y_true[mask], y_pred[mask])

    print(f"\n{name}:")
    print(f"R2  = {r2:.6f}")
    print(f"MSE = {mse:.10f}")

    return {
        "Model": name,
        "Dataset": "all_data_diagnostic",
        "R2": r2,
        "MSE": mse
    }


sub_298_metrics = eval_submodel(
    y_298_all.values,
    H_298_pred_all,
    "enthalpy_normal_submodel_all_data"
)

sub_Tb_metrics = eval_submodel(
    y_Tb_all.values,
    H_Tb_pred_all,
    "enthalpy_boiling_submodel_all_data"
)

sub_Tb_pred_metrics = eval_submodel(
    Tb_raw_all,
    Tb_pred_all,
    "Tb_submodel_all_data"
)


# ============================================================
# 8. 物质级有效筛选
# ============================================================
Nk_all = df[group_cols].to_numpy(dtype=float)
T_all = df[temp_cols].to_numpy(dtype=float)
H_all = df[enthalpy_cols].to_numpy(dtype=float)
slope_all = df["slope"].to_numpy(dtype=float).reshape(-1, 1)
material_ids_all = df[material_id_col].values

valid_target_mask = np.isfinite(H_all)
valid_target_mask = valid_target_mask.all(axis=1)

valid_feature_mask = (
    np.isfinite(Nk_all).all(axis=1)
    & np.isfinite(T_all).all(axis=1)
    & np.isfinite(slope_all).flatten()
)

valid_mask = valid_target_mask & valid_feature_mask

Nk_valid = Nk_all[valid_mask]
T_valid = T_all[valid_mask]
H_valid = H_all[valid_mask]
slope_valid = slope_all[valid_mask]
material_ids_valid = material_ids_all[valid_mask]

H_298_pred_valid = H_298_pred_all[valid_mask]
H_Tb_pred_valid = H_Tb_pred_all[valid_mask]
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
    random_state=42
)

print("\n========== 最终 RF 模型按物质划分 ==========")
print(f"训练集物质数: {len(train_idx)}")
print(f"测试集物质数: {len(test_idx)}")


# ============================================================
# 10. 构建点级数据集
# ============================================================
def build_point_dataset(Nk, T, H, slope, material_ids):
    """
    最终 RF 特征：
        19个基团 + Temperature + slope
    """

    X = np.hstack([
        Nk.repeat(10, axis=0),
        T.flatten().reshape(-1, 1),
        slope.repeat(10, axis=0)
    ])

    y = H.flatten()

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
    H_valid[train_idx],
    slope_valid[train_idx],
    material_ids_valid[train_idx]
)

X_test, y_test, id_test, temp_test, slope_test_point = build_point_dataset(
    Nk_valid[test_idx],
    T_valid[test_idx],
    H_valid[test_idx],
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
# 11. 定义最终随机森林模型
# ============================================================
model = RandomForestRegressor(
    n_estimators=200,
    max_depth=10,
    min_samples_split=5,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1
)


# ============================================================
# 12. 训练最终 RF 模型
# ============================================================
print("\n开始训练最终 RF 模型...")
model.fit(X_train, y_train)

print("\n最终 RF 模型参数:")
print(model)


# ============================================================
# 13. 评价函数
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
# 14. 训练集 / 测试集预测与评估
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

print("\nEnthalpy RF + slope 完整数据集预测偏差 1%，5%，10%分别为：")
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
    "Enthalpy_measured": y_train,
    "Enthalpy_predicted": y_train_pred,
    "Absolute Error": np.abs(y_train - y_train_pred),
    "Relative Error (%)": train_relative_error
})

test_result = pd.DataFrame({
    "Set": "Test",
    "Material_ID": id_test,
    "Temperature (K)": temp_test,
    "slope": slope_test_point,
    "Enthalpy_measured": y_test,
    "Enthalpy_predicted": y_test_pred,
    "Absolute Error": np.abs(y_test - y_test_pred),
    "Relative Error (%)": test_relative_error
})

all_result = pd.DataFrame({
    "Set": "All_train_plus_test",
    "Material_ID": id_all,
    "Temperature (K)": temp_all,
    "slope": slope_all_point,
    "Enthalpy_measured": y_all_true,
    "Enthalpy_predicted": y_all_pred,
    "Absolute Error": np.abs(y_all_true - y_all_pred),
    "Relative Error (%)": all_relative_error
})


# ============================================================
# 16. 保存到 Excel
# ============================================================
result_file = "Enthalpy_RF_with_slope_train_test_by_material.xlsx"

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
        "Final_RF_with_slope",
        "train",
        train_summary["R2"],
        train_summary["MSE"],
        train_summary["ARD_%"],
        train_summary["within_1pct"],
        train_summary["within_5pct"],
        train_summary["within_10pct"]
    ],
    [
        "Final_RF_with_slope",
        "test",
        test_summary["R2"],
        test_summary["MSE"],
        test_summary["ARD_%"],
        test_summary["within_1pct"],
        test_summary["within_5pct"],
        test_summary["within_10pct"]
    ],
    [
        "Final_RF_with_slope",
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

summary_file = "Enthalpy_RF_with_slope_summary.xlsx"

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
    "H_298_pred": H_298_pred_valid,
    "H_Tb_pred": H_Tb_pred_valid,
    "Tb_pred": Tb_pred_valid,
    "slope": slope_valid.flatten()
})

slope_file = "Enthalpy_RF_slope_values.xlsx"

slope_info_df.to_excel(
    slope_file,
    index=False
)

print(f"slope 信息已保存为: {slope_file}")


# ============================================================
# 19. 保存子模型评价
# ============================================================
submodel_summary_df = pd.DataFrame([
    sub_298_metrics,
    sub_Tb_metrics,
    sub_Tb_pred_metrics
])

submodel_summary_file = "Enthalpy_RF_slope_submodel_summary.xlsx"

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

importance_file = "Enthalpy_RF_with_slope_feature_importance.xlsx"

feature_importance_df.to_excel(
    importance_file,
    index=False
)

print(f"特征重要性已保存为: {importance_file}")


# ============================================================
# 21. 输出模型结构记录
# ============================================================
print("\n当前 Enthalpy RF + slope 模型结构:")
print("enthalpy_normal_submodel: RandomForestRegressor(random_state=42, n_jobs=-1), input = selected_25_descriptors_normal.xlsx")
print("enthalpy_boiling_submodel: RandomForestRegressor(random_state=42, n_jobs=-1), input = selected_25_descriptors_boiling.xlsx")
print("Tb_submodel: HuberRegressor(max_iter=10000), input = StandardScaler(PolynomialFeatures(Nk, degree=2))")
print("slope = (H_Tb_pred - H_298_pred) / (Tb_pred - 298.15)")
print("Final target: ordinary Enthalpy")
print("Final model: RandomForestRegressor(n_estimators=200, max_depth=10, min_samples_split=5, min_samples_leaf=2, random_state=42, n_jobs=-1)")
print("Final input features: 19 group counts + Temperature + slope")
print("Split: material-level 8:2 split")
print("Final all-data statistics use strict thresholds: <1%, <5%, <10%")