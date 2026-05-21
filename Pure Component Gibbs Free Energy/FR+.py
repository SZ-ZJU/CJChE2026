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
# main_file = "Gibbs free energy 205.xlsx"
# main_sheet = "Sheet6"
#
# normal_file = "selected_25_descriptors_normal.xlsx"
# boiling_file = "selected_25_descriptors_boiling.xlsx"
#
# target_298 = "ASPEN Vapor pressure at Normal Temperature(bar)"
# target_Tb = "ASPEN Vapor pressure at BoilingTemperature(bar)"
#
# T_ref = 298.15
# random_state = 42
#
#
# # ============================================================
# # 子模型参数：ExtraTreesRegressor
# # ============================================================
# SUBMODEL_ET_PARAMS = dict(
#     n_estimators=800,
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
# # 最终 RF 主模型参数：保持原模型不变
# # ============================================================
# FINAL_RF_PARAMS = dict(
#     n_estimators=100,
#     random_state=42,
#     n_jobs=-1
# )
#
#
# # ============================================================
# # 1. 数据加载
# # ============================================================
# df = pd.read_excel(main_file, sheet_name=main_sheet).copy()
#
# material_id_col = df.columns[0]
#
# group_cols = df.columns[12:31]   # 19个基团
# temp_cols = df.columns[31:41]    # 10个温度点
# gibbs_cols = df.columns[41:51]   # 10个 Gibbs free energy 点
# tb_col = df.columns[5]
#
#
# # ============================================================
# # 2. 数值化主数据
# # ============================================================
# for col in list(group_cols) + list(temp_cols) + list(gibbs_cols) + [tb_col]:
#     df[col] = pd.to_numeric(df[col], errors="coerce")
#
# df = df.dropna(subset=[material_id_col]).copy().reset_index(drop=True)
#
#
# # ============================================================
# # 3. 子模型 1：Vapor pressure at normal temperature
# #    子模型不划分训练集/测试集，使用全量数据训练
# # ============================================================
# df_298 = pd.read_excel(normal_file).copy()
#
# if len(df_298) != len(df):
#     raise ValueError(
#         f"{normal_file} 与主文件行数不一致："
#         f"{len(df_298)} vs {len(df)}。当前代码默认逐行对应。"
#     )
#
# X_298 = df_298.drop(columns=[target_298]).apply(pd.to_numeric, errors="coerce")
# y_298 = pd.to_numeric(df_298[target_298], errors="coerce")
#
# valid_298_mask = (
#     np.isfinite(X_298).all(axis=1)
#     & np.isfinite(y_298)
# )
#
# model_298 = ExtraTreesRegressor(**SUBMODEL_ET_PARAMS)
#
# model_298.fit(
#     X_298.loc[valid_298_mask],
#     y_298.loc[valid_298_mask]
# )
#
# VP_298_pred_all = np.full(len(df), np.nan, dtype=float)
#
# predict_298_mask = np.isfinite(X_298).all(axis=1)
#
# VP_298_pred_all[predict_298_mask] = model_298.predict(
#     X_298.loc[predict_298_mask]
# )
#
#
# # ============================================================
# # 4. 子模型 2：Vapor pressure at boiling temperature
# #    子模型不划分训练集/测试集，使用全量数据训练
# # ============================================================
# df_Tb = pd.read_excel(boiling_file).copy()
#
# if len(df_Tb) != len(df):
#     raise ValueError(
#         f"{boiling_file} 与主文件行数不一致："
#         f"{len(df_Tb)} vs {len(df)}。当前代码默认逐行对应。"
#     )
#
# X_Tb = df_Tb.drop(columns=[target_Tb]).apply(pd.to_numeric, errors="coerce")
# y_Tb = pd.to_numeric(df_Tb[target_Tb], errors="coerce")
#
# valid_Tb_mask = (
#     np.isfinite(X_Tb).all(axis=1)
#     & np.isfinite(y_Tb)
# )
#
# model_Tb_vp = ExtraTreesRegressor(**SUBMODEL_ET_PARAMS)
#
# model_Tb_vp.fit(
#     X_Tb.loc[valid_Tb_mask],
#     y_Tb.loc[valid_Tb_mask]
# )
#
# VP_Tb_pred_all = np.full(len(df), np.nan, dtype=float)
#
# predict_Tb_mask = np.isfinite(X_Tb).all(axis=1)
#
# VP_Tb_pred_all[predict_Tb_mask] = model_Tb_vp.predict(
#     X_Tb.loc[predict_Tb_mask]
# )
#
#
# # ============================================================
# # 5. 子模型 3：Tb 预测模型
# #    原来是 HuberRegressor，这里改成 ExtraTreesRegressor
# # ============================================================
# Nk_all = df[group_cols].apply(pd.to_numeric, errors="coerce")
# Tb_raw = pd.to_numeric(df[tb_col], errors="coerce").values
#
# poly = PolynomialFeatures(degree=2, include_bias=False)
#
# valid_group_mask = np.isfinite(Nk_all).all(axis=1)
#
# Nk_poly_valid = poly.fit_transform(
#     Nk_all.loc[valid_group_mask]
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
# valid_tb_train_mask = (
#     np.isfinite(Tb_raw)
#     & np.isfinite(Nk_poly_all).all(axis=1)
# )
#
# model_Tb = ExtraTreesRegressor(**SUBMODEL_ET_PARAMS)
#
# model_Tb.fit(
#     Nk_poly_all[valid_tb_train_mask],
#     Tb_raw[valid_tb_train_mask]
# )
#
# Tb_pred_all = np.full(len(df), np.nan, dtype=float)
#
# predict_tb_mask = np.isfinite(Nk_poly_all).all(axis=1)
#
# Tb_pred_all[predict_tb_mask] = model_Tb.predict(
#     Nk_poly_all[predict_tb_mask]
# )
#
#
# # ============================================================
# # 6. Slope 计算
# #    slope = (VP_Tb_pred - VP_298_pred) / (Tb_pred - 298.15)
# # ============================================================
# denom = Tb_pred_all - T_ref
#
# slope_values = np.full(len(df), np.nan, dtype=float)
#
# valid_slope_mask = (
#     np.isfinite(VP_Tb_pred_all)
#     & np.isfinite(VP_298_pred_all)
#     & np.isfinite(Tb_pred_all)
#     & (np.abs(denom) > 1e-12)
# )
#
# slope_values[valid_slope_mask] = (
#     VP_Tb_pred_all[valid_slope_mask]
#     - VP_298_pred_all[valid_slope_mask]
# ) / denom[valid_slope_mask]
#
# df["slope"] = slope_values
# df["VP_298_pred"] = VP_298_pred_all
# df["VP_Tb_pred"] = VP_Tb_pred_all
# df["Tb_pred"] = Tb_pred_all
#
#
# # ============================================================
# # 7. 构建点级数据集
# # ============================================================
# X_total = []
# y_total = []
# material_ids = []
# temperatures = []
# slope_points = []
#
# for _, row in df.iterrows():
#     material_id = row[material_id_col]
#
#     Nk = row[group_cols].to_numpy(dtype=float)
#     temps = row[temp_cols].to_numpy(dtype=float)
#     gibbs_values = row[gibbs_cols].to_numpy(dtype=float)
#     slope = float(row["slope"])
#
#     if not np.isfinite(Nk).all():
#         continue
#
#     if not np.isfinite(slope):
#         continue
#
#     for T, G in zip(temps, gibbs_values):
#         if not np.isfinite(T) or not np.isfinite(G):
#             continue
#
#         # 最终特征 = 19个基团 + Temperature + slope
#         features = np.concatenate([
#             Nk,
#             [T],
#             [slope]
#         ])
#
#         X_total.append(features)
#         y_total.append(G)
#         material_ids.append(material_id)
#         temperatures.append(T)
#         slope_points.append(slope)
#
# X_total = np.array(X_total, dtype=float)
# y_total = np.array(y_total, dtype=float)
# material_ids = np.array(material_ids)
# temperatures = np.array(temperatures, dtype=float)
# slope_points = np.array(slope_points, dtype=float)
#
# print("========== 点级数据构建完成 ==========")
# print(f"总样本点数: {len(X_total)}")
# print(f"最终特征数: {X_total.shape[1]}")
#
#
# # ============================================================
# # 8. 最终 RF 模型按物质 8:2 划分
# # ============================================================
# unique_materials = np.unique(material_ids)
#
# train_materials, test_materials = train_test_split(
#     unique_materials,
#     test_size=0.2,
#     random_state=random_state
# )
#
# train_mask = np.isin(material_ids, train_materials)
# test_mask = np.isin(material_ids, test_materials)
#
# X_train = X_total[train_mask]
# y_train = y_total[train_mask]
#
# X_test = X_total[test_mask]
# y_test = y_total[test_mask]
#
# material_ids_train = material_ids[train_mask]
# temperatures_train = temperatures[train_mask]
# slope_train = slope_points[train_mask]
#
# material_ids_test = material_ids[test_mask]
# temperatures_test = temperatures[test_mask]
# slope_test = slope_points[test_mask]
#
# print("\n========== 按物质划分 ==========")
# print(f"总物质数: {len(unique_materials)}")
# print(f"训练集物质数: {len(train_materials)}")
# print(f"测试集物质数: {len(test_materials)}")
# print(f"训练集样本点数: {len(X_train)}")
# print(f"测试集样本点数: {len(X_test)}")
#
#
# # ============================================================
# # 9. 最终随机森林模型训练
# # ============================================================
# model = RandomForestRegressor(**FINAL_RF_PARAMS)
#
# print("\n开始训练最终 RF 模型...")
# model.fit(X_train, y_train)
#
#
# # ============================================================
# # 10. 评估函数
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
#         "Set": name,
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
# # 11. 训练集 / 测试集预测与评估
# # ============================================================
# y_train_pred = model.predict(X_train)
#
# train_relative_error, train_summary = evaluate_dataset(
#     y_train,
#     y_train_pred,
#     "Train"
# )
#
# y_test_pred = model.predict(X_test)
#
# test_relative_error, test_summary = evaluate_dataset(
#     y_test,
#     y_test_pred,
#     "Test"
# )
#
#
# # ============================================================
# # 12. 子模型精度评价
# # ============================================================
# def evaluate_submodel(y_true, y_pred, name):
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
# vp_298_summary = evaluate_submodel(
#     y_298.values,
#     VP_298_pred_all,
#     "VP_298_ExtraTrees_submodel_all_data"
# )
#
# vp_Tb_summary = evaluate_submodel(
#     y_Tb.values,
#     VP_Tb_pred_all,
#     "VP_Tb_ExtraTrees_submodel_all_data"
# )
#
# Tb_summary = evaluate_submodel(
#     Tb_raw,
#     Tb_pred_all,
#     "Tb_ExtraTrees_submodel_all_data"
# )
#
#
# # ============================================================
# # 13. 保存预测结果
# # ============================================================
# train_results = pd.DataFrame({
#     "Set": "Train",
#     "Material_ID": material_ids_train,
#     "Temperature (K)": temperatures_train,
#     "slope": slope_train,
#     "Gibbs_measured": y_train,
#     "Gibbs_predicted": y_train_pred,
#     "Absolute Error": np.abs(y_train - y_train_pred),
#     "Relative Error (%)": train_relative_error
# })
#
# test_results = pd.DataFrame({
#     "Set": "Test",
#     "Material_ID": material_ids_test,
#     "Temperature (K)": temperatures_test,
#     "slope": slope_test,
#     "Gibbs_measured": y_test,
#     "Gibbs_predicted": y_test_pred,
#     "Absolute Error": np.abs(y_test - y_test_pred),
#     "Relative Error (%)": test_relative_error
# })
#
# summary_df = pd.DataFrame([
#     train_summary,
#     test_summary
# ])
#
# submodel_summary_df = pd.DataFrame([
#     vp_298_summary,
#     vp_Tb_summary,
#     Tb_summary
# ])
#
# slope_info_df = pd.DataFrame({
#     "Material_ID": df[material_id_col],
#     "VP_298_pred": VP_298_pred_all,
#     "VP_Tb_pred": VP_Tb_pred_all,
#     "Tb_pred": Tb_pred_all,
#     "slope": slope_values
# })
#
#
# # ============================================================
# # 14. 保存到 Excel
# # ============================================================
# output_file = "Gibbs_RF_with_slope_ExtraTrees_submodels_train_test_split_by_material.xlsx"
#
# with pd.ExcelWriter(output_file, engine="xlsxwriter") as writer:
#     train_results.to_excel(
#         writer,
#         sheet_name="Train_Predictions",
#         index=False
#     )
#
#     test_results.to_excel(
#         writer,
#         sheet_name="Test_Predictions",
#         index=False
#     )
#
#     summary_df.to_excel(
#         writer,
#         sheet_name="Summary",
#         index=False
#     )
#
#     submodel_summary_df.to_excel(
#         writer,
#         sheet_name="Submodel_Summary",
#         index=False
#     )
#
#     slope_info_df.to_excel(
#         writer,
#         sheet_name="Slope_Info",
#         index=False
#     )
#
# print(f"\n已保存预测结果为: {output_file}")
#
#
# # ============================================================
# # 15. 保存特征重要性
# # ============================================================
# feature_names = [f"Group_{i + 1}" for i in range(19)] + [
#     "Temperature",
#     "slope"
# ]
#
# feature_importance_df = pd.DataFrame({
#     "Feature": feature_names,
#     "Importance": model.feature_importances_
# }).sort_values(
#     by="Importance",
#     ascending=False
# )
#
# importance_file = "Gibbs_RF_with_slope_ExtraTrees_feature_importance.xlsx"
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
main_file = "Gibbs free energy 205.xlsx"
main_sheet = "Sheet6"

normal_file = "selected_25_descriptors_normal.xlsx"
boiling_file = "selected_25_descriptors_boiling.xlsx"

target_298 = "ASPEN Vapor pressure at Normal Temperature(bar)"
target_Tb = "ASPEN Vapor pressure at BoilingTemperature(bar)"

T_ref = 298.15
random_state = 42


# ============================================================
# 子模型参数：ExtraTreesRegressor
# ============================================================
SUBMODEL_ET_PARAMS = dict(
    n_estimators=800,
    max_depth=None,
    min_samples_split=2,
    min_samples_leaf=1,
    max_features=1.0,
    bootstrap=False,
    random_state=42,
    n_jobs=-1
)


# ============================================================
# 最终 RF 主模型参数
# ============================================================
FINAL_RF_PARAMS = dict(
    n_estimators=100,
    random_state=42,
    n_jobs=-1
)


# ============================================================
# 1. 数据加载
# ============================================================
df = pd.read_excel(main_file, sheet_name=main_sheet).copy()

material_id_col = df.columns[0]

group_cols = df.columns[12:31]   # 19个基团
temp_cols = df.columns[31:41]    # 10个温度点
gibbs_cols = df.columns[41:51]   # 10个 Gibbs free energy 点
tb_col = df.columns[5]


# ============================================================
# 2. 数值化主数据
# ============================================================
for col in list(group_cols) + list(temp_cols) + list(gibbs_cols) + [tb_col]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=[material_id_col]).copy().reset_index(drop=True)


# ============================================================
# 3. 子模型 1：Vapor pressure at normal temperature
#    子模型不划分训练集/测试集，使用全量数据训练
# ============================================================
df_298 = pd.read_excel(normal_file).copy()

if len(df_298) != len(df):
    raise ValueError(
        f"{normal_file} 与主文件行数不一致："
        f"{len(df_298)} vs {len(df)}。当前代码默认逐行对应。"
    )

X_298 = df_298.drop(columns=[target_298]).apply(pd.to_numeric, errors="coerce")
y_298 = pd.to_numeric(df_298[target_298], errors="coerce")

valid_298_mask = (
    np.isfinite(X_298).all(axis=1)
    & np.isfinite(y_298)
)

model_298 = ExtraTreesRegressor(**SUBMODEL_ET_PARAMS)

model_298.fit(
    X_298.loc[valid_298_mask],
    y_298.loc[valid_298_mask]
)

VP_298_pred_all = np.full(len(df), np.nan, dtype=float)

predict_298_mask = np.isfinite(X_298).all(axis=1)

VP_298_pred_all[predict_298_mask] = model_298.predict(
    X_298.loc[predict_298_mask]
)


# ============================================================
# 4. 子模型 2：Vapor pressure at boiling temperature
#    子模型不划分训练集/测试集，使用全量数据训练
# ============================================================
df_Tb = pd.read_excel(boiling_file).copy()

if len(df_Tb) != len(df):
    raise ValueError(
        f"{boiling_file} 与主文件行数不一致："
        f"{len(df_Tb)} vs {len(df)}。当前代码默认逐行对应。"
    )

X_Tb = df_Tb.drop(columns=[target_Tb]).apply(pd.to_numeric, errors="coerce")
y_Tb = pd.to_numeric(df_Tb[target_Tb], errors="coerce")

valid_Tb_mask = (
    np.isfinite(X_Tb).all(axis=1)
    & np.isfinite(y_Tb)
)

model_Tb_vp = ExtraTreesRegressor(**SUBMODEL_ET_PARAMS)

model_Tb_vp.fit(
    X_Tb.loc[valid_Tb_mask],
    y_Tb.loc[valid_Tb_mask]
)

VP_Tb_pred_all = np.full(len(df), np.nan, dtype=float)

predict_Tb_mask = np.isfinite(X_Tb).all(axis=1)

VP_Tb_pred_all[predict_Tb_mask] = model_Tb_vp.predict(
    X_Tb.loc[predict_Tb_mask]
)


# ============================================================
# 5. 子模型 3：Tb 预测模型
#    ExtraTreesRegressor + 二阶基团特征
# ============================================================
Nk_all = df[group_cols].apply(pd.to_numeric, errors="coerce")
Tb_raw = pd.to_numeric(df[tb_col], errors="coerce").values

poly = PolynomialFeatures(degree=2, include_bias=False)

valid_group_mask = np.isfinite(Nk_all).all(axis=1)

Nk_poly_valid = poly.fit_transform(
    Nk_all.loc[valid_group_mask]
)

Nk_poly_all = np.full(
    (len(df), Nk_poly_valid.shape[1]),
    np.nan,
    dtype=float
)

Nk_poly_all[valid_group_mask] = Nk_poly_valid

valid_tb_train_mask = (
    np.isfinite(Tb_raw)
    & np.isfinite(Nk_poly_all).all(axis=1)
)

model_Tb = ExtraTreesRegressor(**SUBMODEL_ET_PARAMS)

model_Tb.fit(
    Nk_poly_all[valid_tb_train_mask],
    Tb_raw[valid_tb_train_mask]
)

Tb_pred_all = np.full(len(df), np.nan, dtype=float)

predict_tb_mask = np.isfinite(Nk_poly_all).all(axis=1)

Tb_pred_all[predict_tb_mask] = model_Tb.predict(
    Nk_poly_all[predict_tb_mask]
)


# ============================================================
# 6. Slope 计算
#    slope = (VP_Tb_pred - VP_298_pred) / (Tb_pred - 298.15)
# ============================================================
denom = Tb_pred_all - T_ref

slope_values = np.full(len(df), np.nan, dtype=float)

valid_slope_mask = (
    np.isfinite(VP_Tb_pred_all)
    & np.isfinite(VP_298_pred_all)
    & np.isfinite(Tb_pred_all)
    & (np.abs(denom) > 1e-12)
)

slope_values[valid_slope_mask] = (
    VP_Tb_pred_all[valid_slope_mask]
    - VP_298_pred_all[valid_slope_mask]
) / denom[valid_slope_mask]

df["slope"] = slope_values
df["VP_298_pred"] = VP_298_pred_all
df["VP_Tb_pred"] = VP_Tb_pred_all
df["Tb_pred"] = Tb_pred_all


# ============================================================
# 7. 构建点级数据集
# ============================================================
X_total = []
y_total = []
material_ids = []
temperatures = []
slope_points = []

for _, row in df.iterrows():
    material_id = row[material_id_col]

    Nk = row[group_cols].to_numpy(dtype=float)
    temps = row[temp_cols].to_numpy(dtype=float)
    gibbs_values = row[gibbs_cols].to_numpy(dtype=float)
    slope = float(row["slope"])

    if not np.isfinite(Nk).all():
        continue

    if not np.isfinite(slope):
        continue

    for T, G in zip(temps, gibbs_values):
        if not np.isfinite(T) or not np.isfinite(G):
            continue

        # 最终特征 = 19个基团 + Temperature + slope
        features = np.concatenate([
            Nk,
            [T],
            [slope]
        ])

        X_total.append(features)
        y_total.append(G)
        material_ids.append(material_id)
        temperatures.append(T)
        slope_points.append(slope)

X_total = np.array(X_total, dtype=float)
y_total = np.array(y_total, dtype=float)
material_ids = np.array(material_ids)
temperatures = np.array(temperatures, dtype=float)
slope_points = np.array(slope_points, dtype=float)

print("========== 点级数据构建完成 ==========")
print(f"总样本点数: {len(X_total)}")
print(f"最终特征数: {X_total.shape[1]}")


# ============================================================
# 8. 最终 RF 模型按物质 8:2 划分
# ============================================================
unique_materials = np.unique(material_ids)

train_materials, test_materials = train_test_split(
    unique_materials,
    test_size=0.2,
    random_state=random_state
)

train_mask = np.isin(material_ids, train_materials)
test_mask = np.isin(material_ids, test_materials)

X_train = X_total[train_mask]
y_train = y_total[train_mask]

X_test = X_total[test_mask]
y_test = y_total[test_mask]

material_ids_train = material_ids[train_mask]
temperatures_train = temperatures[train_mask]
slope_train = slope_points[train_mask]

material_ids_test = material_ids[test_mask]
temperatures_test = temperatures[test_mask]
slope_test = slope_points[test_mask]

print("\n========== 按物质划分 ==========")
print(f"总物质数: {len(unique_materials)}")
print(f"训练集物质数: {len(train_materials)}")
print(f"测试集物质数: {len(test_materials)}")
print(f"训练集样本点数: {len(X_train)}")
print(f"测试集样本点数: {len(X_test)}")


# ============================================================
# 9. 最终随机森林模型训练
# ============================================================
model = RandomForestRegressor(**FINAL_RF_PARAMS)

print("\n开始训练最终 RF 模型...")
model.fit(X_train, y_train)

print("\n最终 RF 模型参数:")
print(model)


# ============================================================
# 10. 评估函数
# ============================================================
def evaluate_dataset(y_true, y_pred, name="数据集", strict_less=False):
    """
    strict_less=False：统计 <=1%, <=5%, <=10%
    strict_less=True ：统计 <1%, <5%, <10%
    """

    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    finite_mask = (
        np.isfinite(y_true)
        & np.isfinite(y_pred)
    )

    y_true_valid = y_true[finite_mask]
    y_pred_valid = y_pred[finite_mask]

    relative_error = np.full_like(
        y_true,
        np.nan,
        dtype=float
    )

    if len(y_true_valid) == 0:
        print(f"\n{name}评估结果: 无有效样本")

        summary = {
            "Set": name,
            "R2": np.nan,
            "MSE": np.nan,
            "ARD_%": np.nan,
            "within_1pct": 0,
            "within_5pct": 0,
            "within_10pct": 0
        }

        return relative_error, summary

    r2 = r2_score(
        y_true_valid,
        y_pred_valid
    )

    mse = mean_squared_error(
        y_true_valid,
        y_pred_valid
    )

    relative_error_valid = np.full_like(
        y_true_valid,
        np.nan,
        dtype=float
    )

    nonzero_mask = np.abs(y_true_valid) > 1e-12

    if np.any(nonzero_mask):
        relative_error_valid[nonzero_mask] = np.abs(
            (
                y_pred_valid[nonzero_mask]
                - y_true_valid[nonzero_mask]
            )
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

    summary = {
        "Set": name,
        "R2": r2,
        "MSE": mse,
        "ARD_%": ard,
        "within_1pct": within_1pct,
        "within_5pct": within_5pct,
        "within_10pct": within_10pct
    }

    return relative_error, summary


# ============================================================
# 11. 训练集 / 测试集预测与评估
# ============================================================
y_train_pred = model.predict(X_train)

train_relative_error, train_summary = evaluate_dataset(
    y_train,
    y_train_pred,
    "Train",
    strict_less=False
)

y_test_pred = model.predict(X_test)

test_relative_error, test_summary = evaluate_dataset(
    y_test,
    y_test_pred,
    "Test",
    strict_less=False
)


# ============================================================
# 11.1 完整数据集统计：训练集 + 测试集
# ============================================================
y_all_true = np.concatenate([
    y_train,
    y_test
])

y_all_pred = np.concatenate([
    y_train_pred,
    y_test_pred
])

material_ids_all = np.concatenate([
    material_ids_train,
    material_ids_test
])

temperatures_all = np.concatenate([
    temperatures_train,
    temperatures_test
])

slope_all = np.concatenate([
    slope_train,
    slope_test
])

all_relative_error, all_summary = evaluate_dataset(
    y_all_true,
    y_all_pred,
    "All_train_plus_test",
    strict_less=True
)

print("\nGibbs RF + slope ExtraTrees 完整数据集预测偏差 1%，5%，10%分别为：")
print(all_summary["within_1pct"])
print(all_summary["within_5pct"])
print(all_summary["within_10pct"])


# ============================================================
# 12. 子模型精度评价
# ============================================================
def evaluate_submodel(y_true, y_pred, name):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = np.isfinite(y_true) & np.isfinite(y_pred)

    if not np.any(mask):
        print(f"\n{name}: 无有效评价样本")
        return {
            "Model": name,
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
        "R2": r2,
        "MSE": mse
    }


vp_298_summary = evaluate_submodel(
    y_298.values,
    VP_298_pred_all,
    "VP_298_ExtraTrees_submodel_all_data"
)

vp_Tb_summary = evaluate_submodel(
    y_Tb.values,
    VP_Tb_pred_all,
    "VP_Tb_ExtraTrees_submodel_all_data"
)

Tb_summary = evaluate_submodel(
    Tb_raw,
    Tb_pred_all,
    "Tb_ExtraTrees_submodel_all_data"
)


# ============================================================
# 13. 保存预测结果
# ============================================================
train_results = pd.DataFrame({
    "Set": "Train",
    "Material_ID": material_ids_train,
    "Temperature (K)": temperatures_train,
    "slope": slope_train,
    "Gibbs_measured": y_train,
    "Gibbs_predicted": y_train_pred,
    "Absolute Error": np.abs(y_train - y_train_pred),
    "Relative Error (%)": train_relative_error
})

test_results = pd.DataFrame({
    "Set": "Test",
    "Material_ID": material_ids_test,
    "Temperature (K)": temperatures_test,
    "slope": slope_test,
    "Gibbs_measured": y_test,
    "Gibbs_predicted": y_test_pred,
    "Absolute Error": np.abs(y_test - y_test_pred),
    "Relative Error (%)": test_relative_error
})

all_results = pd.DataFrame({
    "Set": "All_train_plus_test",
    "Material_ID": material_ids_all,
    "Temperature (K)": temperatures_all,
    "slope": slope_all,
    "Gibbs_measured": y_all_true,
    "Gibbs_predicted": y_all_pred,
    "Absolute Error": np.abs(y_all_true - y_all_pred),
    "Relative Error (%)": all_relative_error
})

summary_df = pd.DataFrame([
    train_summary,
    test_summary,
    all_summary
])

submodel_summary_df = pd.DataFrame([
    vp_298_summary,
    vp_Tb_summary,
    Tb_summary
])

slope_info_df = pd.DataFrame({
    "Material_ID": df[material_id_col],
    "VP_298_pred": VP_298_pred_all,
    "VP_Tb_pred": VP_Tb_pred_all,
    "Tb_pred": Tb_pred_all,
    "slope": slope_values
})


# ============================================================
# 14. 保存到 Excel
# ============================================================
output_file = "Gibbs_RF_with_slope_ExtraTrees_submodels_train_test_split_by_material.xlsx"

with pd.ExcelWriter(output_file, engine="xlsxwriter") as writer:
    train_results.to_excel(
        writer,
        sheet_name="Train_Predictions",
        index=False
    )

    test_results.to_excel(
        writer,
        sheet_name="Test_Predictions",
        index=False
    )

    all_results.to_excel(
        writer,
        sheet_name="All_Predictions",
        index=False
    )

    summary_df.to_excel(
        writer,
        sheet_name="Summary",
        index=False
    )

    submodel_summary_df.to_excel(
        writer,
        sheet_name="Submodel_Summary",
        index=False
    )

    slope_info_df.to_excel(
        writer,
        sheet_name="Slope_Info",
        index=False
    )

print(f"\n已保存预测结果为: {output_file}")


# ============================================================
# 15. 保存特征重要性
# ============================================================
feature_names = [f"Group_{i + 1}" for i in range(19)] + [
    "Temperature",
    "slope"
]

feature_importance_df = pd.DataFrame({
    "Feature": feature_names,
    "Importance": model.feature_importances_
}).sort_values(
    by="Importance",
    ascending=False
)

importance_file = "Gibbs_RF_with_slope_ExtraTrees_feature_importance.xlsx"

feature_importance_df.to_excel(
    importance_file,
    index=False
)

print(f"特征重要性已保存为: {importance_file}")


# ============================================================
# 16. 输出模型结构记录
# ============================================================
print("\n当前 Gibbs Free Energy RF + slope ExtraTrees 模型结构:")
print("VP_298_submodel: ExtraTreesRegressor(n_estimators=800, max_features=1.0, random_state=42, n_jobs=-1)")
print("VP_Tb_submodel: ExtraTreesRegressor(n_estimators=800, max_features=1.0, random_state=42, n_jobs=-1)")
print("Tb_submodel: ExtraTreesRegressor(n_estimators=800, max_features=1.0, random_state=42, n_jobs=-1), input = PolynomialFeatures(Nk, degree=2)")
print("slope = (VP_Tb_pred - VP_298_pred) / (Tb_pred - 298.15)")
print("Final target: ordinary Gibbs free energy")
print("Final model: RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)")
print("Final input features: 19 group counts + Temperature + slope")
print("Split: material-level 8:2 split, random_state=42")
print("Final all-data statistics use strict thresholds: <1%, <5%, <10%")