# import pandas as pd
# import numpy as np
#
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.linear_model import LinearRegression
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split
#
#
# # ============================================================
# # 1. 读取数据
# # ============================================================
# df = pd.read_excel("internal energy 207.xlsx", sheet_name="Sheet6").copy()
#
#
# # ============================================================
# # 2. 定义列
# # ============================================================
# material_id_col = df.columns[0]
#
# group_cols = df.columns[13:32]   # 19个基团
# temp_cols = df.columns[32:42]    # 10个温度点
# target_cols = df.columns[42:52]  # 10个目标变量点，这里是 internal energy
#
#
# # ============================================================
# # 3. 数值化
# # ============================================================
# for col in list(group_cols) + list(temp_cols) + list(target_cols):
#     df[col] = pd.to_numeric(df[col], errors="coerce")
#
# df = df.dropna(subset=[material_id_col]).copy().reset_index(drop=True)
#
#
# # ============================================================
# # 4. 计算每个物质的目标 slope
# #    slope_target = 首末有效点目标值差 / 首末有效点温度差
# # ============================================================
# slope_targets = []
#
# for _, row in df.iterrows():
#     temps = row[temp_cols].to_numpy(dtype=float)
#     values = row[target_cols].to_numpy(dtype=float)
#
#     valid_idx = np.where(np.isfinite(temps) & np.isfinite(values))[0]
#
#     if len(valid_idx) >= 2:
#         first = valid_idx[0]
#         last = valid_idx[-1]
#
#         delta_T = temps[last] - temps[first]
#
#         if abs(delta_T) > 1e-12:
#             slope_target = (values[last] - values[first]) / delta_T
#         else:
#             slope_target = np.nan
#     else:
#         slope_target = np.nan
#
#     slope_targets.append(slope_target)
#
# df["slope_target"] = slope_targets
#
#
# # ============================================================
# # 5. 用基团训练 slope 子模型
# #    注意：子模型不划分训练集/测试集，使用全部有效物质训练
# # ============================================================
# X_slope_all = df[group_cols].to_numpy(dtype=float)
# y_slope_all = df["slope_target"].to_numpy(dtype=float)
#
# slope_train_mask = (
#     np.isfinite(X_slope_all).all(axis=1)
#     & np.isfinite(y_slope_all)
# )
#
# slope_model = LinearRegression()
#
# slope_model.fit(
#     X_slope_all[slope_train_mask],
#     y_slope_all[slope_train_mask]
# )
#
# # 对所有基团有效的物质预测 slope
# slope_pred_all = np.full(len(df), np.nan, dtype=float)
#
# slope_predict_mask = np.isfinite(X_slope_all).all(axis=1)
#
# slope_pred_all[slope_predict_mask] = slope_model.predict(
#     X_slope_all[slope_predict_mask]
# )
#
# df["slope_pred"] = slope_pred_all
#
#
# # ============================================================
# # 6. 评估 slope 子模型
# # ============================================================
# slope_eval_mask = (
#     np.isfinite(y_slope_all)
#     & np.isfinite(slope_pred_all)
# )
#
# if np.any(slope_eval_mask):
#     y_slope_true_eval = y_slope_all[slope_eval_mask]
#     y_slope_pred_eval = slope_pred_all[slope_eval_mask]
#
#     r2_slope = r2_score(y_slope_true_eval, y_slope_pred_eval)
#     mse_slope = mean_squared_error(y_slope_true_eval, y_slope_pred_eval)
#
#     slope_nonzero_mask = np.abs(y_slope_true_eval) > 1e-12
#     slope_rel_err = np.full_like(y_slope_true_eval, np.nan, dtype=float)
#
#     if np.any(slope_nonzero_mask):
#         slope_rel_err[slope_nonzero_mask] = np.abs(
#             (y_slope_pred_eval[slope_nonzero_mask] - y_slope_true_eval[slope_nonzero_mask])
#             / y_slope_true_eval[slope_nonzero_mask]
#         ) * 100
#         ard_slope = np.nanmean(slope_rel_err)
#     else:
#         ard_slope = np.nan
#
#     print("\n========== slope 子模型评估 ==========")
#     print(f"R2_slope  = {r2_slope:.6f}")
#     print(f"MSE_slope = {mse_slope:.10f}")
#     print(f"ARD_slope = {ard_slope:.4f}%")
# else:
#     r2_slope = np.nan
#     mse_slope = np.nan
#     ard_slope = np.nan
#     print("\n========== slope 子模型评估 ==========")
#     print("无有效 slope 评价样本")
#
#
# # ============================================================
# # 7. 物质级有效筛选
# #    要求：
# #    1. 基团有效
# #    2. slope_pred 有效
# #    3. 至少有一个有效温度-目标点
# # ============================================================
# group_array = df[group_cols].to_numpy(dtype=float)
# temp_array = df[temp_cols].to_numpy(dtype=float)
# target_array = df[target_cols].to_numpy(dtype=float)
# slope_array = df["slope_pred"].to_numpy(dtype=float)
#
# has_valid_point = (
#     np.isfinite(temp_array)
#     & np.isfinite(target_array)
# ).any(axis=1)
#
# valid_material_mask = (
#     np.isfinite(group_array).all(axis=1)
#     & np.isfinite(slope_array)
#     & has_valid_point
# )
#
# df_valid = df.loc[valid_material_mask].copy().reset_index(drop=True)
#
# print("\n========== 最终模型数据清洗后 ==========")
# print(f"有效物质数: {len(df_valid)}")
#
#
# # ============================================================
# # 8. 最终 RF 模型按物质做 8:2 划分
# # ============================================================
# unique_materials = df_valid[material_id_col].dropna().unique()
#
# train_materials, test_materials = train_test_split(
#     unique_materials,
#     test_size=0.2,
#     random_state=42
# )
#
# train_materials = set(train_materials)
# test_materials = set(test_materials)
#
# train_df = df_valid[df_valid[material_id_col].isin(train_materials)].copy().reset_index(drop=True)
# test_df = df_valid[df_valid[material_id_col].isin(test_materials)].copy().reset_index(drop=True)
#
# print("\n========== 最终 RF 模型按物质划分 ==========")
# print(f"总物质数: {len(unique_materials)}")
# print(f"训练集物质数: {len(train_materials)}")
# print(f"测试集物质数: {len(test_materials)}")
#
#
# # ============================================================
# # 9. 构建点级数据集
# # ============================================================
# def build_point_dataset(df_part):
#     X_total = []
#     y_total = []
#     material_ids = []
#     temperatures = []
#     slope_values = []
#
#     for _, row in df_part.iterrows():
#         material_id = row[material_id_col]
#
#         Nk = row[group_cols].to_numpy(dtype=float)
#         temps = row[temp_cols].to_numpy(dtype=float)
#         targets = row[target_cols].to_numpy(dtype=float)
#         slope_pred = float(row["slope_pred"])
#
#         if not np.isfinite(Nk).all():
#             continue
#
#         if not np.isfinite(slope_pred):
#             continue
#
#         for T, y in zip(temps, targets):
#             if not np.isfinite(T) or not np.isfinite(y):
#                 continue
#
#             # 特征 = 19个基团 + 温度T + slope_pred
#             features = np.concatenate([
#                 Nk,
#                 [T],
#                 [slope_pred]
#             ])
#
#             X_total.append(features)
#             y_total.append(y)
#             material_ids.append(material_id)
#             temperatures.append(T)
#             slope_values.append(slope_pred)
#
#     X_total = np.array(X_total, dtype=float)
#     y_total = np.array(y_total, dtype=float)
#
#     material_ids = np.array(material_ids)
#     temperatures = np.array(temperatures, dtype=float)
#     slope_values = np.array(slope_values, dtype=float)
#
#     return X_total, y_total, material_ids, temperatures, slope_values
#
#
# X_train, y_train, material_ids_train, temperatures_train, slope_train_points = build_point_dataset(train_df)
# X_test, y_test, material_ids_test, temperatures_test, slope_test_points = build_point_dataset(test_df)
#
# print("\n========== 最终 RF 点级数据 ==========")
# print(f"训练集样本点数: {len(X_train)}")
# print(f"测试集样本点数: {len(X_test)}")
# print(f"最终模型特征数: {X_train.shape[1]}")
#
# if X_train.shape[1] != 21:
#     raise ValueError(
#         f"当前特征数为 {X_train.shape[1]}，预期为 21：19个基团 + Temperature + slope_pred。"
#     )
#
#
# # ============================================================
# # 10. 定义最终随机森林模型
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
# # 11. 训练最终 RF 模型
# # ============================================================
# print("\n开始训练最终 RF 模型...")
# model.fit(X_train, y_train)
#
#
# # ============================================================
# # 12. 评价函数
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
# # 13. 训练集 / 测试集预测与评价
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
# # 14. 保存训练集预测结果
# # ============================================================
# train_result = pd.DataFrame({
#     "Set": "Train",
#     "Material_ID": material_ids_train,
#     "Temperature (K)": temperatures_train,
#     "slope_pred": slope_train_points,
#     "Internal_energy_measured": y_train,
#     "Internal_energy_predicted": y_train_pred,
#     "Absolute Error": np.abs(y_train - y_train_pred),
#     "Relative Error (%)": train_relative_error
# })
#
# test_result = pd.DataFrame({
#     "Set": "Test",
#     "Material_ID": material_ids_test,
#     "Temperature (K)": temperatures_test,
#     "slope_pred": slope_test_points,
#     "Internal_energy_measured": y_test,
#     "Internal_energy_predicted": y_test_pred,
#     "Absolute Error": np.abs(y_test - y_test_pred),
#     "Relative Error (%)": test_relative_error
# })
#
# all_result = pd.concat(
#     [train_result, test_result],
#     ignore_index=True
# )
#
# result_file = "Internal_energy_RF_with_slope_pred_train_test_by_material.xlsx"
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
# # 15. 保存最终 RF 汇总结果
# # ============================================================
# summary_df = pd.DataFrame([
#     [
#         "Final_RF_with_slope_pred",
#         "train",
#         train_summary["R2"],
#         train_summary["MSE"],
#         train_summary["ARD_%"],
#         train_summary["within_1pct"],
#         train_summary["within_5pct"],
#         train_summary["within_10pct"]
#     ],
#     [
#         "Final_RF_with_slope_pred",
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
# summary_file = "Internal_energy_RF_with_slope_pred_summary.xlsx"
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
# # 16. 保存 slope 子模型结果
# # ============================================================
# slope_result = pd.DataFrame({
#     "Material_ID": df[material_id_col].values,
#     "slope_target": df["slope_target"].values,
#     "slope_pred": df["slope_pred"].values
# })
#
# slope_file = "Internal_energy_slope_submodel_results.xlsx"
#
# slope_result.to_excel(
#     slope_file,
#     index=False
# )
#
# print(f"slope 子模型结果已保存为: {slope_file}")
#
#
# # ============================================================
# # 17. 保存 slope 子模型汇总
# # ============================================================
# slope_summary_df = pd.DataFrame([{
#     "Model": "slope_linear_regression_all_data",
#     "R2_slope": r2_slope,
#     "MSE_slope": mse_slope,
#     "ARD_slope_%": ard_slope
# }])
#
# slope_summary_file = "Internal_energy_slope_submodel_summary.xlsx"
#
# slope_summary_df.to_excel(
#     slope_summary_file,
#     index=False
# )
#
# print(f"slope 子模型汇总已保存为: {slope_summary_file}")
#
#
# # ============================================================
# # 18. 保存特征重要性
# # ============================================================
# feature_names = [f"Group_{i + 1}" for i in range(19)] + [
#     "Temperature",
#     "slope_pred"
# ]
#
# feature_importance_df = pd.DataFrame({
#     "Feature": feature_names,
#     "Importance": model.feature_importances_
# }).sort_values(by="Importance", ascending=False)
#
# importance_file = "Internal_energy_RF_with_slope_pred_feature_importance.xlsx"
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
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


# ============================================================
# 1. 读取数据
# ============================================================
df = pd.read_excel("internal energy 207.xlsx", sheet_name="Sheet6").copy()


# ============================================================
# 2. 定义列
# ============================================================
material_id_col = df.columns[0]

group_cols = df.columns[13:32]   # 19个基团
temp_cols = df.columns[32:42]    # 10个温度点
target_cols = df.columns[42:52]  # 10个目标变量点，这里是 internal energy


# ============================================================
# 3. 数值化
# ============================================================
for col in list(group_cols) + list(temp_cols) + list(target_cols):
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=[material_id_col]).copy().reset_index(drop=True)


# ============================================================
# 4. 计算每个物质的目标 slope
#    slope_target = 首末有效点目标值差 / 首末有效点温度差
# ============================================================
slope_targets = []

for _, row in df.iterrows():
    temps = row[temp_cols].to_numpy(dtype=float)
    values = row[target_cols].to_numpy(dtype=float)

    valid_idx = np.where(
        np.isfinite(temps)
        & np.isfinite(values)
    )[0]

    if len(valid_idx) >= 2:
        first = valid_idx[0]
        last = valid_idx[-1]

        delta_T = temps[last] - temps[first]

        if abs(delta_T) > 1e-12:
            slope_target = (values[last] - values[first]) / delta_T
        else:
            slope_target = np.nan
    else:
        slope_target = np.nan

    slope_targets.append(slope_target)

df["slope_target"] = slope_targets


# ============================================================
# 5. 用基团训练 slope 子模型
#    注意：子模型不划分训练集/测试集，使用全部有效物质训练
# ============================================================
X_slope_all = df[group_cols].to_numpy(dtype=float)
y_slope_all = df["slope_target"].to_numpy(dtype=float)

slope_train_mask = (
    np.isfinite(X_slope_all).all(axis=1)
    & np.isfinite(y_slope_all)
)

slope_model = LinearRegression()

slope_model.fit(
    X_slope_all[slope_train_mask],
    y_slope_all[slope_train_mask]
)

# 对所有基团有效的物质预测 slope
slope_pred_all = np.full(len(df), np.nan, dtype=float)

slope_predict_mask = np.isfinite(X_slope_all).all(axis=1)

slope_pred_all[slope_predict_mask] = slope_model.predict(
    X_slope_all[slope_predict_mask]
)

df["slope_pred"] = slope_pred_all


# ============================================================
# 6. 评估 slope 子模型
# ============================================================
slope_eval_mask = (
    np.isfinite(y_slope_all)
    & np.isfinite(slope_pred_all)
)

if np.any(slope_eval_mask):
    y_slope_true_eval = y_slope_all[slope_eval_mask]
    y_slope_pred_eval = slope_pred_all[slope_eval_mask]

    r2_slope = r2_score(
        y_slope_true_eval,
        y_slope_pred_eval
    )

    mse_slope = mean_squared_error(
        y_slope_true_eval,
        y_slope_pred_eval
    )

    slope_nonzero_mask = np.abs(y_slope_true_eval) > 1e-12
    slope_rel_err = np.full_like(
        y_slope_true_eval,
        np.nan,
        dtype=float
    )

    if np.any(slope_nonzero_mask):
        slope_rel_err[slope_nonzero_mask] = np.abs(
            (
                y_slope_pred_eval[slope_nonzero_mask]
                - y_slope_true_eval[slope_nonzero_mask]
            )
            / y_slope_true_eval[slope_nonzero_mask]
        ) * 100

        ard_slope = np.nanmean(slope_rel_err)
    else:
        ard_slope = np.nan

    print("\n========== slope 子模型评估 ==========")
    print(f"R2_slope  = {r2_slope:.6f}")
    print(f"MSE_slope = {mse_slope:.10f}")
    print(f"ARD_slope = {ard_slope:.4f}%")
else:
    r2_slope = np.nan
    mse_slope = np.nan
    ard_slope = np.nan

    print("\n========== slope 子模型评估 ==========")
    print("无有效 slope 评价样本")


# ============================================================
# 7. 物质级有效筛选
#    要求：
#    1. 基团有效
#    2. slope_pred 有效
#    3. 至少有一个有效温度-目标点
# ============================================================
group_array = df[group_cols].to_numpy(dtype=float)
temp_array = df[temp_cols].to_numpy(dtype=float)
target_array = df[target_cols].to_numpy(dtype=float)
slope_array = df["slope_pred"].to_numpy(dtype=float)

has_valid_point = (
    np.isfinite(temp_array)
    & np.isfinite(target_array)
).any(axis=1)

valid_material_mask = (
    np.isfinite(group_array).all(axis=1)
    & np.isfinite(slope_array)
    & has_valid_point
)

df_valid = df.loc[valid_material_mask].copy().reset_index(drop=True)

print("\n========== 最终模型数据清洗后 ==========")
print(f"有效物质数: {len(df_valid)}")


# ============================================================
# 8. 最终 RF 模型按物质做 8:2 划分
# ============================================================
unique_materials = df_valid[material_id_col].dropna().unique()

train_materials, test_materials = train_test_split(
    unique_materials,
    test_size=0.2,
    random_state=42
)

train_materials = set(train_materials)
test_materials = set(test_materials)

train_df = df_valid[
    df_valid[material_id_col].isin(train_materials)
].copy().reset_index(drop=True)

test_df = df_valid[
    df_valid[material_id_col].isin(test_materials)
].copy().reset_index(drop=True)

print("\n========== 最终 RF 模型按物质划分 ==========")
print(f"总物质数: {len(unique_materials)}")
print(f"训练集物质数: {len(train_materials)}")
print(f"测试集物质数: {len(test_materials)}")


# ============================================================
# 9. 构建点级数据集
# ============================================================
def build_point_dataset(df_part):
    X_total = []
    y_total = []
    material_ids = []
    temperatures = []
    slope_values = []

    for _, row in df_part.iterrows():
        material_id = row[material_id_col]

        Nk = row[group_cols].to_numpy(dtype=float)
        temps = row[temp_cols].to_numpy(dtype=float)
        targets = row[target_cols].to_numpy(dtype=float)
        slope_pred = float(row["slope_pred"])

        if not np.isfinite(Nk).all():
            continue

        if not np.isfinite(slope_pred):
            continue

        for T, y in zip(temps, targets):
            if not np.isfinite(T) or not np.isfinite(y):
                continue

            # 特征 = 19个基团 + 温度T + slope_pred
            features = np.concatenate([
                Nk,
                [T],
                [slope_pred]
            ])

            X_total.append(features)
            y_total.append(y)
            material_ids.append(material_id)
            temperatures.append(T)
            slope_values.append(slope_pred)

    X_total = np.array(X_total, dtype=float)
    y_total = np.array(y_total, dtype=float)

    material_ids = np.array(material_ids)
    temperatures = np.array(temperatures, dtype=float)
    slope_values = np.array(slope_values, dtype=float)

    return X_total, y_total, material_ids, temperatures, slope_values


X_train, y_train, material_ids_train, temperatures_train, slope_train_points = build_point_dataset(train_df)
X_test, y_test, material_ids_test, temperatures_test, slope_test_points = build_point_dataset(test_df)

print("\n========== 最终 RF 点级数据 ==========")
print(f"训练集样本点数: {len(X_train)}")
print(f"测试集样本点数: {len(X_test)}")
print(f"最终模型特征数: {X_train.shape[1]}")

if X_train.shape[1] != 21:
    raise ValueError(
        f"当前特征数为 {X_train.shape[1]}，预期为 21：19个基团 + Temperature + slope_pred。"
    )


# ============================================================
# 10. 定义最终随机森林模型
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
# 11. 训练最终 RF 模型
# ============================================================
print("\n开始训练最终 RF 模型...")
model.fit(X_train, y_train)

print("\n最终 RF 模型参数:")
print(model)


# ============================================================
# 12. 评价函数
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

        return relative_error, {
            "Dataset": name,
            "R2": np.nan,
            "MSE": np.nan,
            "ARD_%": np.nan,
            "within_1pct": 0,
            "within_5pct": 0,
            "within_10pct": 0
        }

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
# 13. 训练集 / 测试集预测与评价
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
# 13.1 完整数据集统计：训练集 + 测试集
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

slope_points_all = np.concatenate([
    slope_train_points,
    slope_test_points
])

all_relative_error, all_summary = evaluate_dataset(
    y_all_true,
    y_all_pred,
    "完整数据集 train + test",
    strict_less=True
)

print("\nInternal Energy RF + slope_pred 完整数据集预测偏差 1%，5%，10%分别为：")
print(all_summary["within_1pct"])
print(all_summary["within_5pct"])
print(all_summary["within_10pct"])


# ============================================================
# 14. 保存训练集 / 测试集 / 完整数据集预测结果
# ============================================================
train_result = pd.DataFrame({
    "Set": "Train",
    "Material_ID": material_ids_train,
    "Temperature (K)": temperatures_train,
    "slope_pred": slope_train_points,
    "Internal_energy_measured": y_train,
    "Internal_energy_predicted": y_train_pred,
    "Absolute Error": np.abs(y_train - y_train_pred),
    "Relative Error (%)": train_relative_error
})

test_result = pd.DataFrame({
    "Set": "Test",
    "Material_ID": material_ids_test,
    "Temperature (K)": temperatures_test,
    "slope_pred": slope_test_points,
    "Internal_energy_measured": y_test,
    "Internal_energy_predicted": y_test_pred,
    "Absolute Error": np.abs(y_test - y_test_pred),
    "Relative Error (%)": test_relative_error
})

all_result = pd.DataFrame({
    "Set": "All_train_plus_test",
    "Material_ID": material_ids_all,
    "Temperature (K)": temperatures_all,
    "slope_pred": slope_points_all,
    "Internal_energy_measured": y_all_true,
    "Internal_energy_predicted": y_all_pred,
    "Absolute Error": np.abs(y_all_true - y_all_pred),
    "Relative Error (%)": all_relative_error
})


# ============================================================
# 15. 保存最终 RF 汇总结果
# ============================================================
summary_df = pd.DataFrame([
    [
        "Final_RF_with_slope_pred",
        "train",
        train_summary["R2"],
        train_summary["MSE"],
        train_summary["ARD_%"],
        train_summary["within_1pct"],
        train_summary["within_5pct"],
        train_summary["within_10pct"]
    ],
    [
        "Final_RF_with_slope_pred",
        "test",
        test_summary["R2"],
        test_summary["MSE"],
        test_summary["ARD_%"],
        test_summary["within_1pct"],
        test_summary["within_5pct"],
        test_summary["within_10pct"]
    ],
    [
        "Final_RF_with_slope_pred",
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


# ============================================================
# 16. 保存 slope 子模型结果
# ============================================================
slope_result = pd.DataFrame({
    "Material_ID": df[material_id_col].values,
    "slope_target": df["slope_target"].values,
    "slope_pred": df["slope_pred"].values
})

slope_summary_df = pd.DataFrame([{
    "Model": "slope_linear_regression_all_data",
    "R2_slope": r2_slope,
    "MSE_slope": mse_slope,
    "ARD_slope_%": ard_slope
}])


# ============================================================
# 17. 保存特征重要性
# ============================================================
feature_names = [f"Group_{i + 1}" for i in range(19)] + [
    "Temperature",
    "slope_pred"
]

feature_importance_df = pd.DataFrame({
    "Feature": feature_names,
    "Importance": model.feature_importances_
}).sort_values(
    by="Importance",
    ascending=False
)


# ============================================================
# 18. 总保存
# ============================================================
result_file = "Internal_energy_RF_with_slope_pred_train_test_by_material.xlsx"

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

    summary_df.to_excel(
        writer,
        sheet_name="summary",
        index=False
    )

    slope_result.to_excel(
        writer,
        sheet_name="slope_submodel_results",
        index=False
    )

    slope_summary_df.to_excel(
        writer,
        sheet_name="slope_submodel_summary",
        index=False
    )

    feature_importance_df.to_excel(
        writer,
        sheet_name="feature_importance",
        index=False
    )

print(f"\n预测结果已保存为: {result_file}")


# ============================================================
# 19. 单独保存 slope 子模型结果
# ============================================================
slope_file = "Internal_energy_slope_submodel_results.xlsx"

slope_result.to_excel(
    slope_file,
    index=False
)

print(f"slope 子模型结果已保存为: {slope_file}")

slope_summary_file = "Internal_energy_slope_submodel_summary.xlsx"

slope_summary_df.to_excel(
    slope_summary_file,
    index=False
)

print(f"slope 子模型汇总已保存为: {slope_summary_file}")


# ============================================================
# 20. 单独保存特征重要性
# ============================================================
importance_file = "Internal_energy_RF_with_slope_pred_feature_importance.xlsx"

feature_importance_df.to_excel(
    importance_file,
    index=False
)

print(f"特征重要性已保存为: {importance_file}")


# ============================================================
# 21. 输出模型结构记录
# ============================================================
print("\n当前 Internal Energy RF + slope_pred 模型结构:")
print("slope_target = (last_valid_internal_energy - first_valid_internal_energy) / (last_valid_T - first_valid_T)")
print("slope_submodel: LinearRegression(), input = 19 group counts, trained on all valid materials")
print("Final target: ordinary Internal Energy")
print("Final model: RandomForestRegressor(n_estimators=200, max_depth=10, min_samples_split=5, min_samples_leaf=2, random_state=42, n_jobs=-1)")
print("Final input features: 19 group counts + Temperature + slope_pred")
print("Split: material-level 8:2 split")
print("Final all-data statistics use strict thresholds: <1%, <5%, <10%")