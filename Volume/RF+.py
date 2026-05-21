# import pandas as pd
# import numpy as np
#
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.linear_model import HuberRegressor
# from sklearn.preprocessing import PolynomialFeatures
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split
#
#
# # ============================================================
# # 0. 参数区
# # ============================================================
# main_file = "volume208.xlsx"
# normal_file = "selected_25_descriptors_normal.xlsx"
# boiling_file = "selected_25_descriptors_boiling.xlsx"
#
# main_sheet = "Sheet1"
#
# target_normal = "volume at normal temperature"
# target_boiling = "volume at boiling temperature"
#
# rows_per_material = 10
# random_state = 42
# T_ref = 298.15
# Tb0 = 222.543
#
#
# # ============================================================
# # 1. 读取主数据
# # ============================================================
# df = pd.read_excel(main_file, sheet_name=main_sheet).copy()
#
# id_col = df.columns[0]
#
# group_cols = df.columns[13:32]   # 19个基团
# temp_cols = df.columns[32:42]    # 10个温度点
# v_cols = df.columns[42:52]       # 10个体积点
#
# tb_col = df.columns[5]
#
#
# # ============================================================
# # 2. 数值化主数据
# # ============================================================
# for col in list(group_cols) + list(temp_cols) + list(v_cols) + [tb_col]:
#     df[col] = pd.to_numeric(df[col], errors="coerce")
#
# df = df.dropna(subset=[id_col]).copy().reset_index(drop=True)
#
#
# # ============================================================
# # 3. 子模型 1：normal temperature volume
# #    子模型不划分训练集/测试集，使用全体数据训练
# # ============================================================
# df_298 = pd.read_excel(normal_file).copy()
#
# if len(df_298) != len(df):
#     raise ValueError(
#         f"{normal_file} 与 {main_file} 行数不一致："
#         f"{len(df_298)} vs {len(df)}。当前代码默认两个文件逐行对应。"
#     )
#
# X_298_all = df_298.drop(columns=[target_normal]).apply(pd.to_numeric, errors="coerce")
# y_298_all = pd.to_numeric(df_298[target_normal], errors="coerce")
#
# valid_298_mask = (
#     np.isfinite(X_298_all).all(axis=1)
#     & np.isfinite(y_298_all)
# )
#
# rf_298 = RandomForestRegressor(
#     n_estimators=500,
#     max_depth=None,
#     min_samples_split=2,
#     min_samples_leaf=1,
#     max_features="sqrt",
#     bootstrap=True,
#     random_state=42,
#     n_jobs=-1
# )
#
# rf_298.fit(
#     X_298_all.loc[valid_298_mask],
#     y_298_all.loc[valid_298_mask]
# )
#
# Vol_298_pred_all = np.full(len(df), np.nan, dtype=float)
# predict_298_mask = np.isfinite(X_298_all).all(axis=1)
#
# Vol_298_pred_all[predict_298_mask] = rf_298.predict(
#     X_298_all.loc[predict_298_mask]
# )
#
#
# # ============================================================
# # 4. 子模型 2：boiling temperature volume
# #    子模型不划分训练集/测试集，使用全体数据训练
# # ============================================================
# df_Tb = pd.read_excel(boiling_file).copy()
#
# if len(df_Tb) != len(df):
#     raise ValueError(
#         f"{boiling_file} 与 {main_file} 行数不一致："
#         f"{len(df_Tb)} vs {len(df)}。当前代码默认两个文件逐行对应。"
#     )
#
# X_Tb_all = df_Tb.drop(columns=[target_boiling]).apply(pd.to_numeric, errors="coerce")
# y_Tb_all = pd.to_numeric(df_Tb[target_boiling], errors="coerce")
#
# valid_Tb_volume_mask = (
#     np.isfinite(X_Tb_all).all(axis=1)
#     & np.isfinite(y_Tb_all)
# )
#
# rf_Tb_volume = RandomForestRegressor(
#     n_estimators=500,
#     max_depth=None,
#     min_samples_split=2,
#     min_samples_leaf=1,
#     max_features="sqrt",
#     bootstrap=True,
#     random_state=42,
#     n_jobs=-1
# )
#
# rf_Tb_volume.fit(
#     X_Tb_all.loc[valid_Tb_volume_mask],
#     y_Tb_all.loc[valid_Tb_volume_mask]
# )
#
# Vol_Tb_pred_all = np.full(len(df), np.nan, dtype=float)
# predict_Tb_volume_mask = np.isfinite(X_Tb_all).all(axis=1)
#
# Vol_Tb_pred_all[predict_Tb_volume_mask] = rf_Tb_volume.predict(
#     X_Tb_all.loc[predict_Tb_volume_mask]
# )
#
#
# # ============================================================
# # 5. 子模型 3：Tb 预测模型
# #    子模型不划分训练集/测试集，使用全体数据训练
# # ============================================================
# Nk_all_df = df[group_cols].apply(pd.to_numeric, errors="coerce")
# Tb_raw_all = pd.to_numeric(df[tb_col], errors="coerce").values
#
# poly = PolynomialFeatures(degree=2, include_bias=False)
#
# valid_group_mask = np.isfinite(Nk_all_df).all(axis=1)
# Nk_poly_all = np.full((len(df), 1), np.nan)
#
# Nk_poly_valid = poly.fit_transform(Nk_all_df.loc[valid_group_mask])
# Nk_poly_all = np.full((len(df), Nk_poly_valid.shape[1]), np.nan, dtype=float)
# Nk_poly_all[valid_group_mask] = Nk_poly_valid
#
# valid_tb_mask = (
#     np.isfinite(Tb_raw_all)
#     & np.isfinite(Nk_poly_all).all(axis=1)
# )
#
# model_Tb = HuberRegressor(max_iter=10000)
#
# model_Tb.fit(
#     Nk_poly_all[valid_tb_mask],
#     np.exp(Tb_raw_all[valid_tb_mask] / Tb0)
# )
#
# Tb_pred_all = np.full(len(df), np.nan, dtype=float)
# predict_tb_mask = np.isfinite(Nk_poly_all).all(axis=1)
#
# Tb_pred_all[predict_tb_mask] = Tb0 * np.log(
#     np.clip(
#         model_Tb.predict(Nk_poly_all[predict_tb_mask]),
#         1e-6,
#         None
#     )
# )
#
#
# # ============================================================
# # 6. 计算 slope 并加入主 DataFrame
# # ============================================================
# denom = Tb_pred_all - T_ref
#
# slope_values = np.full(len(df), np.nan, dtype=float)
#
# valid_slope_mask = (
#     np.isfinite(Vol_Tb_pred_all)
#     & np.isfinite(Vol_298_pred_all)
#     & np.isfinite(Tb_pred_all)
#     & (np.abs(denom) > 1e-12)
# )
#
# slope_values[valid_slope_mask] = (
#     Vol_Tb_pred_all[valid_slope_mask]
#     - Vol_298_pred_all[valid_slope_mask]
# ) / denom[valid_slope_mask]
#
# df["slope"] = slope_values
# df["Vol_298_pred"] = Vol_298_pred_all
# df["Vol_Tb_pred"] = Vol_Tb_pred_all
# df["Tb_pred"] = Tb_pred_all
#
#
# # ============================================================
# # 7. 物质级有效筛选
# # ============================================================
# Nk_all = df[group_cols].apply(pd.to_numeric, errors="coerce").values
# T_all = df[temp_cols].apply(pd.to_numeric, errors="coerce").values
# Vol_all = df[v_cols].apply(pd.to_numeric, errors="coerce").values
# slope_all = df["slope"].to_numpy(dtype=float).reshape(-1, 1)
# material_ids_all = df[id_col].values
#
# valid_volume_mask = np.isfinite(Vol_all)
# valid_volume_mask = valid_volume_mask.all(axis=1)
#
# valid_feature_mask = (
#     np.isfinite(Nk_all).all(axis=1)
#     & np.isfinite(T_all).all(axis=1)
#     & np.isfinite(slope_all).flatten()
# )
#
# valid_mask = valid_volume_mask & valid_feature_mask
#
# Nk_valid = Nk_all[valid_mask]
# T_valid = T_all[valid_mask]
# Vol_valid = Vol_all[valid_mask]
# slope_valid = slope_all[valid_mask]
# material_ids_valid = material_ids_all[valid_mask]
#
# Vol_298_pred_valid = Vol_298_pred_all[valid_mask]
# Vol_Tb_pred_valid = Vol_Tb_pred_all[valid_mask]
# Tb_pred_valid = Tb_pred_all[valid_mask]
#
# print("========== 数据清洗后 ==========")
# print(f"有效物质数: {len(material_ids_valid)}")
#
#
# # ============================================================
# # 8. 最终 RF 模型按物质 8:2 划分
# # ============================================================
# material_indices = np.arange(len(material_ids_valid))
#
# train_idx, test_idx = train_test_split(
#     material_indices,
#     test_size=0.2,
#     random_state=random_state
# )
#
# print("========== 最终 RF 模型按物质划分 ==========")
# print(f"训练集物质数: {len(train_idx)}")
# print(f"测试集物质数: {len(test_idx)}")
#
#
# # ============================================================
# # 9. 构建点级数据集
# # ============================================================
# def build_point_dataset(Nk, T, Vol, slope, material_ids):
#     """
#     最终 RF 特征：
#         19个基团 + 温度T + slope
#
#     slope 是物质级特征，同一个物质的 10 个温度点共享同一个 slope。
#     """
#
#     X = np.hstack([
#         Nk.repeat(10, axis=0),
#         T.flatten().reshape(-1, 1),
#         slope.repeat(10, axis=0)
#     ])
#
#     y = Vol.flatten()
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
#     Vol_valid[train_idx],
#     slope_valid[train_idx],
#     material_ids_valid[train_idx]
# )
#
# X_test, y_test, id_test, temp_test, slope_test_point = build_point_dataset(
#     Nk_valid[test_idx],
#     T_valid[test_idx],
#     Vol_valid[test_idx],
#     slope_valid[test_idx],
#     material_ids_valid[test_idx]
# )
#
# print("========== 最终 RF 点级数据 ==========")
# print(f"训练集样本点数: {len(X_train)}")
# print(f"测试集样本点数: {len(X_test)}")
# print(f"最终模型特征数: {X_train.shape[1]}")
#
# if X_train.shape[1] != 21:
#     raise ValueError(
#         f"当前特征数为 {X_train.shape[1]}，预期为 21：19个基团 + T + slope。"
#     )
#
#
# # ============================================================
# # 10. 训练最终 RF 模型
# # ============================================================
# # 5. 定义随机森林模型 (替换原 GBDT)
# model = RandomForestRegressor(
#     n_estimators=200,
#     max_depth=10,
#     min_samples_split=5,
#     min_samples_leaf=2,
#     random_state=42,
#     n_jobs=-1          # 使用所有CPU核心
# )
#
# model.fit(X_train, y_train)
#
#
# # ============================================================
# # 11. 评估函数
# # ============================================================
# def evaluate_dataset(y_true, y_pred, name="数据集"):
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#
#     r2 = r2_score(y_true, y_pred)
#     mse = mean_squared_error(y_true, y_pred)
#
#     nonzero_mask = np.abs(y_true) > 1e-12
#     relative_error = np.full_like(y_true, np.nan, dtype=float)
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
# # 12. 训练集 / 测试集预测与评估
# # ============================================================
# y_train_pred = model.predict(X_train)
# train_relative_error, train_summary = evaluate_dataset(
#     y_train,
#     y_train_pred,
#     "训练集"
# )
#
# y_test_pred = model.predict(X_test)
# test_relative_error, test_summary = evaluate_dataset(
#     y_test,
#     y_test_pred,
#     "测试集"
# )
#
#
# # ============================================================
# # 13. 保存预测结果
# # ============================================================
# train_result = pd.DataFrame({
#     "Set": "Train",
#     "Material_ID": id_train,
#     "Temperature (K)": temp_train,
#     "slope": slope_train_point,
#     "Vol_measured": y_train,
#     "Vol_predicted": y_train_pred,
#     "Absolute Error": np.abs(y_train - y_train_pred),
#     "Relative Error (%)": train_relative_error
# })
#
# test_result = pd.DataFrame({
#     "Set": "Test",
#     "Material_ID": id_test,
#     "Temperature (K)": temp_test,
#     "slope": slope_test_point,
#     "Vol_measured": y_test,
#     "Vol_predicted": y_test_pred,
#     "Absolute Error": np.abs(y_test - y_test_pred),
#     "Relative Error (%)": test_relative_error
# })
#
# all_result = pd.concat(
#     [train_result, test_result],
#     ignore_index=True
# )
#
# result_file = "Vol预测结果_加slope特征_RF_按物质划分.xlsx"
# all_result.to_excel(result_file, index=False)
#
# print(f"\n已保存预测结果为: {result_file}")
#
#
# # ============================================================
# # 14. 保存评估汇总
# # ============================================================
# summary_df = pd.DataFrame([
#     [
#         "train",
#         train_summary["R2"],
#         train_summary["MSE"],
#         train_summary["ARD_%"],
#         train_summary["within_1pct"],
#         train_summary["within_5pct"],
#         train_summary["within_10pct"]
#     ],
#     [
#         "test",
#         test_summary["R2"],
#         test_summary["MSE"],
#         test_summary["ARD_%"],
#         test_summary["within_1pct"],
#         test_summary["within_5pct"],
#         test_summary["within_10pct"]
#     ]
# ], columns=[
#     "Dataset",
#     "R2",
#     "MSE",
#     "ARD_%",
#     "within_1pct",
#     "within_5pct",
#     "within_10pct"
# ])
#
# summary_file = "Vol_RF_加slope特征_评估汇总.xlsx"
# summary_df.to_excel(summary_file, index=False)
#
# print(f"已保存评估汇总为: {summary_file}")
#
#
# # ============================================================
# # 15. 保存 slope 信息
# # ============================================================
# slope_info_df = pd.DataFrame({
#     "Material_ID": material_ids_valid,
#     "Vol_298_pred": Vol_298_pred_valid,
#     "Vol_Tb_pred": Vol_Tb_pred_valid,
#     "Tb_pred": Tb_pred_valid,
#     "slope": slope_valid.flatten()
# })
#
# slope_file = "Vol_RF_slope子模型信息.xlsx"
# slope_info_df.to_excel(slope_file, index=False)
#
# print(f"slope 子模型信息已保存为: {slope_file}")
#
#
# # ============================================================
# # 16. 保存特征重要性
# # ============================================================
# feature_names = [f"Group_{i + 1}" for i in range(19)] + ["Temperature", "slope"]
#
# feature_importance_df = pd.DataFrame({
#     "Feature": feature_names,
#     "Importance": model.feature_importances_
# }).sort_values(by="Importance", ascending=False)
#
# importance_file = "Vol_RF_加slope特征_特征重要性.xlsx"
# feature_importance_df.to_excel(importance_file, index=False)
#
# print(f"特征重要性已保存为: {importance_file}")



import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import HuberRegressor
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


# ============================================================
# 0. 参数区
# ============================================================
main_file = "volume208.xlsx"
normal_file = "selected_25_descriptors_normal.xlsx"
boiling_file = "selected_25_descriptors_boiling.xlsx"

main_sheet = "Sheet1"

target_normal = "volume at normal temperature"
target_boiling = "volume at boiling temperature"

rows_per_material = 10
random_state = 42
T_ref = 298.15
Tb0 = 222.543


# ============================================================
# 1. 读取主数据
# ============================================================
df = pd.read_excel(main_file, sheet_name=main_sheet).copy()

id_col = df.columns[0]

group_cols = df.columns[13:32]   # 19个基团
temp_cols = df.columns[32:42]    # 10个温度点
v_cols = df.columns[42:52]       # 10个体积点

tb_col = df.columns[5]


# ============================================================
# 2. 数值化主数据
# ============================================================
for col in list(group_cols) + list(temp_cols) + list(v_cols) + [tb_col]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=[id_col]).copy().reset_index(drop=True)


# ============================================================
# 3. 子模型 1：normal temperature volume
#    子模型不划分训练集/测试集，使用全体数据训练
# ============================================================
df_298 = pd.read_excel(normal_file).copy()

if len(df_298) != len(df):
    raise ValueError(
        f"{normal_file} 与 {main_file} 行数不一致："
        f"{len(df_298)} vs {len(df)}。当前代码默认两个文件逐行对应。"
    )

X_298_all = df_298.drop(columns=[target_normal]).apply(pd.to_numeric, errors="coerce")
y_298_all = pd.to_numeric(df_298[target_normal], errors="coerce")

valid_298_mask = (
    np.isfinite(X_298_all).all(axis=1)
    & np.isfinite(y_298_all)
)

rf_298 = RandomForestRegressor(
    n_estimators=500,
    max_depth=None,
    min_samples_split=2,
    min_samples_leaf=1,
    max_features="sqrt",
    bootstrap=True,
    random_state=42,
    n_jobs=-1
)

rf_298.fit(
    X_298_all.loc[valid_298_mask],
    y_298_all.loc[valid_298_mask]
)

Vol_298_pred_all = np.full(len(df), np.nan, dtype=float)
predict_298_mask = np.isfinite(X_298_all).all(axis=1)

Vol_298_pred_all[predict_298_mask] = rf_298.predict(
    X_298_all.loc[predict_298_mask]
)


# ============================================================
# 4. 子模型 2：boiling temperature volume
#    子模型不划分训练集/测试集，使用全体数据训练
# ============================================================
df_Tb = pd.read_excel(boiling_file).copy()

if len(df_Tb) != len(df):
    raise ValueError(
        f"{boiling_file} 与 {main_file} 行数不一致："
        f"{len(df_Tb)} vs {len(df)}。当前代码默认两个文件逐行对应。"
    )

X_Tb_all = df_Tb.drop(columns=[target_boiling]).apply(pd.to_numeric, errors="coerce")
y_Tb_all = pd.to_numeric(df_Tb[target_boiling], errors="coerce")

valid_Tb_volume_mask = (
    np.isfinite(X_Tb_all).all(axis=1)
    & np.isfinite(y_Tb_all)
)

rf_Tb_volume = RandomForestRegressor(
    n_estimators=500,
    max_depth=None,
    min_samples_split=2,
    min_samples_leaf=1,
    max_features="sqrt",
    bootstrap=True,
    random_state=42,
    n_jobs=-1
)

rf_Tb_volume.fit(
    X_Tb_all.loc[valid_Tb_volume_mask],
    y_Tb_all.loc[valid_Tb_volume_mask]
)

Vol_Tb_pred_all = np.full(len(df), np.nan, dtype=float)
predict_Tb_volume_mask = np.isfinite(X_Tb_all).all(axis=1)

Vol_Tb_pred_all[predict_Tb_volume_mask] = rf_Tb_volume.predict(
    X_Tb_all.loc[predict_Tb_volume_mask]
)


# ============================================================
# 5. 子模型 3：Tb 预测模型
#    子模型不划分训练集/测试集，使用全体数据训练
# ============================================================
Nk_all_df = df[group_cols].apply(pd.to_numeric, errors="coerce")
Tb_raw_all = pd.to_numeric(df[tb_col], errors="coerce").values

poly = PolynomialFeatures(degree=2, include_bias=False)

valid_group_mask = np.isfinite(Nk_all_df).all(axis=1)
Nk_poly_valid = poly.fit_transform(Nk_all_df.loc[valid_group_mask])

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

model_Tb = HuberRegressor(max_iter=10000)

model_Tb.fit(
    Nk_poly_all[valid_tb_mask],
    np.exp(Tb_raw_all[valid_tb_mask] / Tb0)
)

Tb_pred_all = np.full(len(df), np.nan, dtype=float)
predict_tb_mask = np.isfinite(Nk_poly_all).all(axis=1)

Tb_pred_all[predict_tb_mask] = Tb0 * np.log(
    np.clip(
        model_Tb.predict(Nk_poly_all[predict_tb_mask]),
        1e-6,
        None
    )
)


# ============================================================
# 6. 计算 slope 并加入主 DataFrame
# ============================================================
denom = Tb_pred_all - T_ref

slope_values = np.full(len(df), np.nan, dtype=float)

valid_slope_mask = (
    np.isfinite(Vol_Tb_pred_all)
    & np.isfinite(Vol_298_pred_all)
    & np.isfinite(Tb_pred_all)
    & (np.abs(denom) > 1e-12)
)

slope_values[valid_slope_mask] = (
    Vol_Tb_pred_all[valid_slope_mask]
    - Vol_298_pred_all[valid_slope_mask]
) / denom[valid_slope_mask]

df["slope"] = slope_values
df["Vol_298_pred"] = Vol_298_pred_all
df["Vol_Tb_pred"] = Vol_Tb_pred_all
df["Tb_pred"] = Tb_pred_all


# ============================================================
# 7. 物质级有效筛选
# ============================================================
Nk_all = df[group_cols].apply(pd.to_numeric, errors="coerce").values
T_all = df[temp_cols].apply(pd.to_numeric, errors="coerce").values
Vol_all = df[v_cols].apply(pd.to_numeric, errors="coerce").values
slope_all = df["slope"].to_numpy(dtype=float).reshape(-1, 1)
material_ids_all = df[id_col].values

valid_volume_mask = np.isfinite(Vol_all)
valid_volume_mask = valid_volume_mask.all(axis=1)

valid_feature_mask = (
    np.isfinite(Nk_all).all(axis=1)
    & np.isfinite(T_all).all(axis=1)
    & np.isfinite(slope_all).flatten()
)

valid_mask = valid_volume_mask & valid_feature_mask

Nk_valid = Nk_all[valid_mask]
T_valid = T_all[valid_mask]
Vol_valid = Vol_all[valid_mask]
slope_valid = slope_all[valid_mask]
material_ids_valid = material_ids_all[valid_mask]

Vol_298_pred_valid = Vol_298_pred_all[valid_mask]
Vol_Tb_pred_valid = Vol_Tb_pred_all[valid_mask]
Tb_pred_valid = Tb_pred_all[valid_mask]

print("========== 数据清洗后 ==========")
print(f"有效物质数: {len(material_ids_valid)}")


# ============================================================
# 8. 最终 RF 模型按物质 8:2 划分
# ============================================================
material_indices = np.arange(len(material_ids_valid))

train_idx, test_idx = train_test_split(
    material_indices,
    test_size=0.2,
    random_state=random_state
)

print("========== 最终 RF 模型按物质划分 ==========")
print(f"训练集物质数: {len(train_idx)}")
print(f"测试集物质数: {len(test_idx)}")


# ============================================================
# 9. 构建点级数据集
# ============================================================
def build_point_dataset(Nk, T, Vol, slope, material_ids):
    """
    最终 RF 特征：
        19个基团 + 温度T + slope

    slope 是物质级特征，同一个物质的 10 个温度点共享同一个 slope。
    """

    X = np.hstack([
        Nk.repeat(10, axis=0),
        T.flatten().reshape(-1, 1),
        slope.repeat(10, axis=0)
    ])

    y = Vol.flatten()

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
    Vol_valid[train_idx],
    slope_valid[train_idx],
    material_ids_valid[train_idx]
)

X_test, y_test, id_test, temp_test, slope_test_point = build_point_dataset(
    Nk_valid[test_idx],
    T_valid[test_idx],
    Vol_valid[test_idx],
    slope_valid[test_idx],
    material_ids_valid[test_idx]
)

print("========== 最终 RF 点级数据 ==========")
print(f"训练集样本点数: {len(X_train)}")
print(f"测试集样本点数: {len(X_test)}")
print(f"最终模型特征数: {X_train.shape[1]}")

if X_train.shape[1] != 21:
    raise ValueError(
        f"当前特征数为 {X_train.shape[1]}，预期为 21：19个基团 + T + slope。"
    )


# ============================================================
# 10. 训练最终 RF 模型
# ============================================================
model = RandomForestRegressor(
    n_estimators=200,
    max_depth=10,
    min_samples_split=5,
    min_samples_leaf=2,
    random_state=42,
    n_jobs=-1
)

print("\n开始训练最终 RF 模型...")
model.fit(X_train, y_train)

print("\n最终 RF 模型参数:")
print(model)


# ============================================================
# 11. 评估函数
# ============================================================
def evaluate_dataset(y_true, y_pred, name="数据集", strict_less=False):
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
# 12. 训练集 / 测试集预测与评估
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
# 12.1 完整数据集统计：训练集 + 测试集
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

print("\nVolume RF + slope 完整数据集预测偏差 1%，5%，10%分别为：")
print(all_summary["within_1pct"])
print(all_summary["within_5pct"])
print(all_summary["within_10pct"])


# ============================================================
# 13. 保存预测结果
# ============================================================
train_result = pd.DataFrame({
    "Set": "Train",
    "Material_ID": id_train,
    "Temperature (K)": temp_train,
    "slope": slope_train_point,
    "Vol_measured": y_train,
    "Vol_predicted": y_train_pred,
    "Absolute Error": np.abs(y_train - y_train_pred),
    "Relative Error (%)": train_relative_error
})

test_result = pd.DataFrame({
    "Set": "Test",
    "Material_ID": id_test,
    "Temperature (K)": temp_test,
    "slope": slope_test_point,
    "Vol_measured": y_test,
    "Vol_predicted": y_test_pred,
    "Absolute Error": np.abs(y_test - y_test_pred),
    "Relative Error (%)": test_relative_error
})

all_result = pd.DataFrame({
    "Set": "All_train_plus_test",
    "Material_ID": id_all,
    "Temperature (K)": temp_all,
    "slope": slope_all_point,
    "Vol_measured": y_all_true,
    "Vol_predicted": y_all_pred,
    "Absolute Error": np.abs(y_all_true - y_all_pred),
    "Relative Error (%)": all_relative_error
})


# ============================================================
# 14. 保存到 Excel
# ============================================================
result_file = "Vol预测结果_加slope特征_RF_按物质划分.xlsx"

with pd.ExcelWriter(result_file, engine="xlsxwriter") as writer:
    pd.concat(
        [train_result, test_result],
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

print(f"\n已保存预测结果为: {result_file}")


# ============================================================
# 15. 保存评估汇总
# ============================================================
summary_df = pd.DataFrame([
    [
        "train",
        train_summary["R2"],
        train_summary["MSE"],
        train_summary["ARD_%"],
        train_summary["within_1pct"],
        train_summary["within_5pct"],
        train_summary["within_10pct"]
    ],
    [
        "test",
        test_summary["R2"],
        test_summary["MSE"],
        test_summary["ARD_%"],
        test_summary["within_1pct"],
        test_summary["within_5pct"],
        test_summary["within_10pct"]
    ],
    [
        "all_train_plus_test",
        all_summary["R2"],
        all_summary["MSE"],
        all_summary["ARD_%"],
        all_summary["within_1pct"],
        all_summary["within_5pct"],
        all_summary["within_10pct"]
    ],
], columns=[
    "Dataset",
    "R2",
    "MSE",
    "ARD_%",
    "within_1pct",
    "within_5pct",
    "within_10pct"
])

summary_file = "Vol_RF_加slope特征_评估汇总.xlsx"

summary_df.to_excel(
    summary_file,
    index=False
)

print(f"已保存评估汇总为: {summary_file}")


# ============================================================
# 16. 保存 slope 信息
# ============================================================
slope_info_df = pd.DataFrame({
    "Material_ID": material_ids_valid,
    "Vol_298_pred": Vol_298_pred_valid,
    "Vol_Tb_pred": Vol_Tb_pred_valid,
    "Tb_pred": Tb_pred_valid,
    "slope": slope_valid.flatten()
})

slope_file = "Vol_RF_slope子模型信息.xlsx"

slope_info_df.to_excel(
    slope_file,
    index=False
)

print(f"slope 子模型信息已保存为: {slope_file}")


# ============================================================
# 17. 保存特征重要性
# ============================================================
feature_names = [f"Group_{i + 1}" for i in range(19)] + ["Temperature", "slope"]

feature_importance_df = pd.DataFrame({
    "Feature": feature_names,
    "Importance": model.feature_importances_
}).sort_values(by="Importance", ascending=False)

importance_file = "Vol_RF_加slope特征_特征重要性.xlsx"

feature_importance_df.to_excel(
    importance_file,
    index=False
)

print(f"特征重要性已保存为: {importance_file}")


# ============================================================
# 18. 输出模型结构记录
# ============================================================
print("\n当前 Volume RF + slope 模型结构:")
print("Vol_298_submodel: RandomForestRegressor(n_estimators=500, max_features='sqrt', random_state=42, n_jobs=-1)")
print("Vol_Tb_submodel: RandomForestRegressor(n_estimators=500, max_features='sqrt', random_state=42, n_jobs=-1)")
print("Tb_submodel: HuberRegressor(max_iter=10000), input = PolynomialFeatures(Nk, degree=2)")
print("slope = (Vol_Tb_pred - Vol_298_pred) / (Tb_pred - 298.15)")
print("Final target: ordinary Volume")
print("Final model: RandomForestRegressor(n_estimators=200, max_depth=10, min_samples_split=5, min_samples_leaf=2, random_state=42, n_jobs=-1)")
print("Final input features: 19 group counts + Temperature + slope")
print("Split: material-level 8:2 split")
print("Final all-data statistics use strict thresholds: <1%, <5%, <10%")