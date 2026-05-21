# import pandas as pd
# import numpy as np
#
# from sklearn.model_selection import train_test_split
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.ensemble import RandomForestRegressor
#
#
# # ============================================================
# # 1. 读取数据
# # ============================================================
#
# file_path = "heat capacity 207.xlsx"
# df = pd.read_excel(file_path, sheet_name="Sheet1")
#
# # 删除第一列为空的行
# df = df.dropna(subset=[df.columns[0]]).copy()
# df[df.columns[0]] = df[df.columns[0]].astype(int)
#
#
# # ============================================================
# # 2. 定义列
# # ============================================================
#
# material_id_col = df.columns[0]
#
# group_cols = df.columns[11:30]   # 19个基团列
# temp_cols = df.columns[30:40]    # 10个温度点
# cp_cols = df.columns[40:50]      # 10个Cp点
#
#
# # ============================================================
# # 3. 按“物质”做 8:2 划分，避免同一物质同时出现在训练集和测试集
# # ============================================================
#
# unique_materials = df[material_id_col].dropna().unique()
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
# print("========== 按物质划分 ==========")
# print(f"总物质数: {len(unique_materials)}")
# print(f"训练集物质数: {len(train_materials)}")
# print(f"测试集物质数: {len(test_materials)}")
#
#
# # ============================================================
# # 4. 构建训练集 / 测试集样本
# #    每个物质最多有10个温度点，每个温度点作为一个样本
# #    特征 = 基团组成 Nk + 温度 T
# # ============================================================
#
# X_train, y_train, id_train, T_train = [], [], [], []
# X_test, y_test, id_test, T_test = [], [], [], []
#
# for _, row in df.iterrows():
#     material_id = row[material_id_col]
#
#     Nk = row[group_cols].astype(float).values
#     temps = row[temp_cols].astype(float).values
#     cps = row[cp_cols].astype(float).values
#
#     for T, Cp in zip(temps, cps):
#         if np.isnan(T) or np.isnan(Cp):
#             continue
#
#         features = np.concatenate([Nk, [T]])
#
#         if material_id in train_materials:
#             X_train.append(features)
#             y_train.append(Cp)
#             id_train.append(material_id)
#             T_train.append(T)
#
#         elif material_id in test_materials:
#             X_test.append(features)
#             y_test.append(Cp)
#             id_test.append(material_id)
#             T_test.append(T)
#
#
# X_train = np.array(X_train, dtype=float)
# y_train = np.array(y_train, dtype=float)
#
# X_test = np.array(X_test, dtype=float)
# y_test = np.array(y_test, dtype=float)
#
# id_train = np.array(id_train)
# id_test = np.array(id_test)
#
# T_train = np.array(T_train, dtype=float)
# T_test = np.array(T_test, dtype=float)
#
# print(f"训练集样本点数: {len(X_train)}")
# print(f"测试集样本点数: {len(X_test)}")
#
#
# # ============================================================
# # 5. 定义 RF 模型
# # ============================================================
#
# model = RandomForestRegressor(
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
#
# # ============================================================
# # 6. 模型训练
# # ============================================================
#
# model.fit(X_train, y_train)
#
#
# # ============================================================
# # 7. 训练集 / 测试集预测
# # ============================================================
#
# y_train_pred = model.predict(X_train)
# y_test_pred = model.predict(X_test)
#
#
# # ============================================================
# # 8. 定义评估函数
# # ============================================================
#
# def evaluate(y_true, y_pred, dataset_name="数据集"):
#     mse = mean_squared_error(y_true, y_pred)
#     r2 = r2_score(y_true, y_pred)
#
#     nonzero_mask = np.abs(y_true) > 1e-12
#     relative_error = np.full_like(y_true, np.nan, dtype=float)
#
#     if np.any(nonzero_mask):
#         relative_error[nonzero_mask] = np.abs(
#             (y_true[nonzero_mask] - y_pred[nonzero_mask])
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
#     print(f"\n{dataset_name}评估结果:")
#     print(f"R²  = {r2:.6f}")
#     print(f"MSE = {mse:.6f}")
#     print(f"ARD = {ard:.2f}%")
#     print(f"误差 ≤ 1% 的点数: {within_1pct}")
#     print(f"误差 ≤ 5% 的点数: {within_5pct}")
#     print(f"误差 ≤ 10% 的点数: {within_10pct}")
#
#     return relative_error, r2, mse, ard, within_1pct, within_5pct, within_10pct
#
#
# # ============================================================
# # 9. 评估训练集和测试集
# # ============================================================
#
# train_relative_error, train_r2, train_mse, train_ard, train_1, train_5, train_10 = evaluate(
#     y_train, y_train_pred, "训练集"
# )
#
# test_relative_error, test_r2, test_mse, test_ard, test_1, test_5, test_10 = evaluate(
#     y_test, y_test_pred, "测试集"
# )
#
#
# # ============================================================
# # 10. 保存训练集预测结果
# # ============================================================
#
# train_results = pd.DataFrame({
#     "Material_ID": id_train,
#     "Temperature (K)": T_train,
#     "Cp_measured": y_train,
#     "Cp_predicted": y_train_pred,
#     "Relative_Error (%)": train_relative_error
# })
#
# train_results.to_excel(
#     "Cp预测结果_基团加温度_RF_训练集.xlsx",
#     index=False
# )
#
#
# # ============================================================
# # 11. 保存测试集预测结果
# # ============================================================
#
# test_results = pd.DataFrame({
#     "Material_ID": id_test,
#     "Temperature (K)": T_test,
#     "Cp_measured": y_test,
#     "Cp_predicted": y_test_pred,
#     "Relative_Error (%)": test_relative_error
# })
#
# test_results.to_excel(
#     "Cp预测结果_基团加温度_RF_测试集.xlsx",
#     index=False
# )
#
#
# # ============================================================
# # 12. 保存评估汇总
# # ============================================================
#
# summary_df = pd.DataFrame([
#     ["train", train_r2, train_mse, train_ard, train_1, train_5, train_10],
#     ["test", test_r2, test_mse, test_ard, test_1, test_5, test_10]
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
# summary_df.to_excel(
#     "Cp预测结果_基团加温度_RF_评估汇总.xlsx",
#     index=False
# )
#
#
# # ============================================================
# # 13. 保存特征重要性
# # ============================================================
#
# feature_names = list(group_cols) + ["Temperature (K)"]
#
# feature_importance_df = pd.DataFrame({
#     "Feature": feature_names,
#     "Importance": model.feature_importances_
# }).sort_values(by="Importance", ascending=False)
#
# feature_importance_df.to_excel(
#     "Cp预测结果_基团加温度_RF_特征重要性.xlsx",
#     index=False
# )
#
#
# print("\n已保存训练集结果: Cp预测结果_基团加温度_RF_训练集.xlsx")
# print("已保存测试集结果: Cp预测结果_基团加温度_RF_测试集.xlsx")
# print("已保存评估汇总: Cp预测结果_基团加温度_RF_评估汇总.xlsx")
# print("已保存特征重要性: Cp预测结果_基团加温度_RF_特征重要性.xlsx")

import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.ensemble import RandomForestRegressor


# ============================================================
# 1. 读取数据
# ============================================================

file_path = "heat capacity 207.xlsx"
df = pd.read_excel(file_path, sheet_name="Sheet1")

# 删除第一列为空的行
df = df.dropna(subset=[df.columns[0]]).copy()
df[df.columns[0]] = df[df.columns[0]].astype(int)


# ============================================================
# 2. 定义列
# ============================================================

material_id_col = df.columns[0]

group_cols = df.columns[11:30]   # 19个基团列
temp_cols = df.columns[30:40]    # 10个温度点
cp_cols = df.columns[40:50]      # 10个Cp点


# ============================================================
# 3. 按“物质”做 8:2 划分，避免同一物质同时出现在训练集和测试集
# ============================================================

unique_materials = df[material_id_col].dropna().unique()

train_materials, test_materials = train_test_split(
    unique_materials,
    test_size=0.2,
    random_state=42
)

train_materials = set(train_materials)
test_materials = set(test_materials)

print("========== 按物质划分 ==========")
print(f"总物质数: {len(unique_materials)}")
print(f"训练集物质数: {len(train_materials)}")
print(f"测试集物质数: {len(test_materials)}")


# ============================================================
# 4. 构建训练集 / 测试集样本
#    每个物质最多有10个温度点，每个温度点作为一个样本
#    特征 = 基团组成 Nk + 温度 T
# ============================================================

X_train, y_train, id_train, T_train = [], [], [], []
X_test, y_test, id_test, T_test = [], [], [], []

for _, row in df.iterrows():
    material_id = row[material_id_col]

    Nk = row[group_cols].astype(float).values
    temps = row[temp_cols].astype(float).values
    cps = row[cp_cols].astype(float).values

    for T, Cp in zip(temps, cps):
        if np.isnan(T) or np.isnan(Cp):
            continue

        features = np.concatenate([Nk, [T]])

        if material_id in train_materials:
            X_train.append(features)
            y_train.append(Cp)
            id_train.append(material_id)
            T_train.append(T)

        elif material_id in test_materials:
            X_test.append(features)
            y_test.append(Cp)
            id_test.append(material_id)
            T_test.append(T)


X_train = np.array(X_train, dtype=float)
y_train = np.array(y_train, dtype=float)

X_test = np.array(X_test, dtype=float)
y_test = np.array(y_test, dtype=float)

id_train = np.array(id_train)
id_test = np.array(id_test)

T_train = np.array(T_train, dtype=float)
T_test = np.array(T_test, dtype=float)

print(f"训练集样本点数: {len(X_train)}")
print(f"测试集样本点数: {len(X_test)}")


# ============================================================
# 5. 定义 RF 模型
# ============================================================

model = RandomForestRegressor(
    n_estimators=500,
    max_depth=None,
    min_samples_split=2,
    min_samples_leaf=1,
    max_features="sqrt",
    bootstrap=True,
    random_state=42,
    n_jobs=-1
)


# ============================================================
# 6. 模型训练
# ============================================================

model.fit(X_train, y_train)


# ============================================================
# 7. 训练集 / 测试集预测
# ============================================================

y_train_pred = model.predict(X_train)
y_test_pred = model.predict(X_test)


# ============================================================
# 8. 定义评估函数
# ============================================================

def evaluate(y_true, y_pred, dataset_name="数据集"):
    mse = mean_squared_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)

    nonzero_mask = np.abs(y_true) > 1e-12
    relative_error = np.full_like(y_true, np.nan, dtype=float)

    if np.any(nonzero_mask):
        relative_error[nonzero_mask] = np.abs(
            (y_true[nonzero_mask] - y_pred[nonzero_mask])
            / y_true[nonzero_mask]
        ) * 100
        ard = np.nanmean(relative_error)
    else:
        ard = np.nan

    within_1pct = np.sum(relative_error <= 1)
    within_5pct = np.sum(relative_error <= 5)
    within_10pct = np.sum(relative_error <= 10)

    print(f"\n{dataset_name}评估结果:")
    print(f"R²  = {r2:.6f}")
    print(f"MSE = {mse:.6f}")
    print(f"ARD = {ard:.2f}%")
    print(f"误差 ≤ 1% 的点数: {within_1pct}")
    print(f"误差 ≤ 5% 的点数: {within_5pct}")
    print(f"误差 ≤ 10% 的点数: {within_10pct}")

    return relative_error, r2, mse, ard, within_1pct, within_5pct, within_10pct


# ============================================================
# 9. 分别评估训练集和测试集
# ============================================================

train_relative_error, train_r2, train_mse, train_ard, train_1, train_5, train_10 = evaluate(
    y_train, y_train_pred, "训练集"
)

test_relative_error, test_r2, test_mse, test_ard, test_1, test_5, test_10 = evaluate(
    y_test, y_test_pred, "测试集"
)


# ============================================================
# 10. 统计完整数据集上的预测偏差数量：训练集 + 测试集
# ============================================================

y_all_true = np.concatenate([y_train, y_test])
y_all_pred = np.concatenate([y_train_pred, y_test_pred])
id_all = np.concatenate([id_train, id_test])
T_all = np.concatenate([T_train, T_test])

nonzero_mask_all = np.abs(y_all_true) > 1e-12
relative_error_all = np.full_like(y_all_true, np.nan, dtype=float)

relative_error_all[nonzero_mask_all] = np.abs(
    (y_all_true[nonzero_mask_all] - y_all_pred[nonzero_mask_all])
    / y_all_true[nonzero_mask_all]
) * 100

all_within_1pct = np.sum(relative_error_all < 1)
all_within_5pct = np.sum(relative_error_all < 5)
all_within_10pct = np.sum(relative_error_all < 10)

all_mse = mean_squared_error(y_all_true, y_all_pred)
all_r2 = r2_score(y_all_true, y_all_pred)
all_ard = np.nanmean(relative_error_all)

print("\n完整数据集评估结果：训练集 + 测试集")
print(f"R²  = {all_r2:.6f}")
print(f"MSE = {all_mse:.6f}")
print(f"ARD = {all_ard:.2f}%")

print("1%，5%，10%分别为：")
print(all_within_1pct)
print(all_within_5pct)
print(all_within_10pct)


# ============================================================
# 11. 保存训练集预测结果
# ============================================================

train_results = pd.DataFrame({
    "Material_ID": id_train,
    "Temperature (K)": T_train,
    "Cp_measured": y_train,
    "Cp_predicted": y_train_pred,
    "Relative_Error (%)": train_relative_error
})

train_results.to_excel(
    "Cp预测结果_基团加温度_RF_训练集.xlsx",
    index=False
)


# ============================================================
# 12. 保存测试集预测结果
# ============================================================

test_results = pd.DataFrame({
    "Material_ID": id_test,
    "Temperature (K)": T_test,
    "Cp_measured": y_test,
    "Cp_predicted": y_test_pred,
    "Relative_Error (%)": test_relative_error
})

test_results.to_excel(
    "Cp预测结果_基团加温度_RF_测试集.xlsx",
    index=False
)


# ============================================================
# 13. 保存完整数据集预测结果：训练集 + 测试集
# ============================================================

all_results = pd.DataFrame({
    "Material_ID": id_all,
    "Temperature (K)": T_all,
    "Cp_measured": y_all_true,
    "Cp_predicted": y_all_pred,
    "Relative_Error (%)": relative_error_all
})

all_results.to_excel(
    "Cp预测结果_基团加温度_RF_完整数据集.xlsx",
    index=False
)


# ============================================================
# 14. 保存评估汇总
# ============================================================

summary_df = pd.DataFrame([
    ["train", train_r2, train_mse, train_ard, train_1, train_5, train_10],
    ["test", test_r2, test_mse, test_ard, test_1, test_5, test_10],
    ["all", all_r2, all_mse, all_ard, all_within_1pct, all_within_5pct, all_within_10pct]
], columns=[
    "Dataset",
    "R2",
    "MSE",
    "ARD_%",
    "within_1pct",
    "within_5pct",
    "within_10pct"
])

summary_df.to_excel(
    "Cp预测结果_基团加温度_RF_评估汇总.xlsx",
    index=False
)


# ============================================================
# 15. 保存特征重要性
# ============================================================

feature_names = list(group_cols) + ["Temperature (K)"]

feature_importance_df = pd.DataFrame({
    "Feature": feature_names,
    "Importance": model.feature_importances_
}).sort_values(by="Importance", ascending=False)

feature_importance_df.to_excel(
    "Cp预测结果_基团加温度_RF_特征重要性.xlsx",
    index=False
)


# ============================================================
# 16. 输出保存信息
# ============================================================

print("\n已保存训练集结果: Cp预测结果_基团加温度_RF_训练集.xlsx")
print("已保存测试集结果: Cp预测结果_基团加温度_RF_测试集.xlsx")
print("已保存完整数据集结果: Cp预测结果_基团加温度_RF_完整数据集.xlsx")
print("已保存评估汇总: Cp预测结果_基团加温度_RF_评估汇总.xlsx")
print("已保存特征重要性: Cp预测结果_基团加温度_RF_特征重要性.xlsx")