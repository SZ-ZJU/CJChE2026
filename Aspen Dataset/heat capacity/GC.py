# import pandas as pd
# import numpy as np
# from sklearn.linear_model import LinearRegression
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split
#
# # 1. 数据读取
# file_path = "heat capacity 207.xlsx"  # 文件路径
# df = pd.read_excel(file_path)
#
# # 分组、温度、热容列索引
# group_cols = df.columns[11:30]   # 基团列
# temp_cols = df.columns[30:40]    # 10个温度点
# cp_cols = df.columns[40:50]      # 10个 Cp 值
#
# # 2. 先按“物质”划分训练集 / 测试集
# material_id_col = df.columns[0]   # 第1列作为物质ID
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
# print(f"总物质数: {len(unique_materials)}")
# print(f"训练集物质数: {len(train_materials)}")
# print(f"测试集物质数: {len(test_materials)}")
#
# # 3. 构建训练集和测试集样本
# X_train, y_train = [], []
# id_train, T_train = [], []
#
# X_test, y_test = [], []
# id_test, T_test = [], []
#
# for _, row in df.iterrows():
#     material_id = row.iloc[0]
#     Nk = row[group_cols].values
#     temps = row[temp_cols].values
#     cps = row[cp_cols].values
#
#     for T, cp in zip(temps, cps):
#         if pd.isna(T) or pd.isna(cp):
#             continue
#
#         features = np.concatenate([Nk, Nk * T])
#
#         if material_id in train_materials:
#             X_train.append(features)
#             y_train.append(cp)
#             id_train.append(material_id)
#             T_train.append(T)
#         elif material_id in test_materials:
#             X_test.append(features)
#             y_test.append(cp)
#             id_test.append(material_id)
#             T_test.append(T)
#
# X_train = np.array(X_train, dtype=float)
# y_train = np.array(y_train, dtype=float)
# id_train = np.array(id_train)
# T_train = np.array(T_train, dtype=float)
#
# X_test = np.array(X_test, dtype=float)
# y_test = np.array(y_test, dtype=float)
# id_test = np.array(id_test)
# T_test = np.array(T_test, dtype=float)
#
# print(f"\n训练集样本点数: {len(X_train)}")
# print(f"测试集样本点数: {len(X_test)}")
#
# # 4. 模型训练
# model = LinearRegression()
# model.fit(X_train, y_train)
#
# # 5. 定义评估函数
# def evaluate(y_true, y_pred, dataset_name="数据集"):
#     mse = mean_squared_error(y_true, y_pred)
#     r2 = r2_score(y_true, y_pred)
#
#     # 防止分母为0
#     nonzero_mask = y_true != 0
#     if np.any(nonzero_mask):
#         ard = np.mean(np.abs((y_true[nonzero_mask] - y_pred[nonzero_mask]) / y_true[nonzero_mask])) * 100
#         relative_error = np.full_like(y_true, np.nan, dtype=float)
#         relative_error[nonzero_mask] = np.abs((y_pred[nonzero_mask] - y_true[nonzero_mask]) / y_true[nonzero_mask]) * 100
#     else:
#         ard = np.nan
#         relative_error = np.full_like(y_true, np.nan, dtype=float)
#
#     within_1pct = np.sum(relative_error <= 1)
#     within_5pct = np.sum(relative_error <= 5)
#     within_10pct = np.sum(relative_error <= 10)
#
#     print(f"\n📊 {dataset_name}评估结果:")
#     print(f"R² = {r2:.4f}")
#     print(f"MSE = {mse:.4f}")
#     print(f"ARD = {ard:.2f}%")
#     print(f"误差 ≤ 1% 的点数: {within_1pct}")
#     print(f"误差 ≤ 5% 的点数: {within_5pct}")
#     print(f"误差 ≤ 10% 的点数: {within_10pct}")
#
#     return mse, r2, ard, relative_error
#
# # 6. 训练集预测与评估
# y_train_pred = model.predict(X_train)
# train_mse, train_r2, train_ard, train_relative_error = evaluate(
#     y_train, y_train_pred, dataset_name="训练集"
# )
#
# # 7. 测试集预测与评估
# y_test_pred = model.predict(X_test)
# test_mse, test_r2, test_ard, test_relative_error = evaluate(
#     y_test, y_test_pred, dataset_name="测试集"
# )
#
# # 8. 输出训练集预测结果
# results_train = pd.DataFrame({
#     'Material_ID': id_train,
#     'Temperature (K)': T_train,
#     'Cp_measured': y_train,
#     'Cp_predicted': y_train_pred,
#     'Relative_Error_%': train_relative_error
# })
# results_train.to_excel("训练集_按物质划分_线性Cp预测结果.xlsx", index=False)
# print("\n✅ 训练集结果已保存为: 训练集_按物质划分_线性Cp预测结果.xlsx")
#
# # 9. 输出测试集预测结果
# results_test = pd.DataFrame({
#     'Material_ID': id_test,
#     'Temperature (K)': T_test,
#     'Cp_measured': y_test,
#     'Cp_predicted': y_test_pred,
#     'Relative_Error_%': test_relative_error
# })
# results_test.to_excel("测试集_按物质划分_线性Cp预测结果.xlsx", index=False)
# print("✅ 测试集结果已保存为: 测试集_按物质划分_线性Cp预测结果.xlsx")
#
# # 10. 输出基团贡献系数（含温度项）
# coefficients = pd.DataFrame({
#     'Group': list(group_cols) + [f'{group}_T' for group in group_cols],
#     'Contribution': model.coef_
# })
#
# print("\n📈 基团贡献系数（包含乘温项）:")
# print(coefficients.sort_values(by='Contribution', ascending=False).to_string(index=False))


import pandas as pd
import numpy as np

from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


# ============================================================
# 1. 数据读取
# ============================================================

file_path = "heat capacity 207.xlsx"
df = pd.read_excel(file_path)

# 分组、温度、热容列索引
group_cols = df.columns[11:30]   # 基团列
temp_cols = df.columns[30:40]    # 10个温度点
cp_cols = df.columns[40:50]      # 10个 Cp 值


# ============================================================
# 2. 按“物质”划分训练集 / 测试集
# ============================================================

material_id_col = df.columns[0]   # 第1列作为物质ID
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
# 3. 构建训练集和测试集样本
#    特征 = Nk + Nk*T
# ============================================================

X_train, y_train = [], []
id_train, T_train = [], []

X_test, y_test = [], []
id_test, T_test = [], []

for _, row in df.iterrows():
    material_id = row.iloc[0]

    Nk = row[group_cols].astype(float).values
    temps = row[temp_cols].astype(float).values
    cps = row[cp_cols].astype(float).values

    for T, cp in zip(temps, cps):
        if pd.isna(T) or pd.isna(cp):
            continue

        features = np.concatenate([Nk, Nk * T])

        if material_id in train_materials:
            X_train.append(features)
            y_train.append(cp)
            id_train.append(material_id)
            T_train.append(T)

        elif material_id in test_materials:
            X_test.append(features)
            y_test.append(cp)
            id_test.append(material_id)
            T_test.append(T)

X_train = np.array(X_train, dtype=float)
y_train = np.array(y_train, dtype=float)
id_train = np.array(id_train)
T_train = np.array(T_train, dtype=float)

X_test = np.array(X_test, dtype=float)
y_test = np.array(y_test, dtype=float)
id_test = np.array(id_test)
T_test = np.array(T_test, dtype=float)

print(f"\n训练集样本点数: {len(X_train)}")
print(f"测试集样本点数: {len(X_test)}")


# ============================================================
# 4. 模型训练
# ============================================================

model = LinearRegression()
model.fit(X_train, y_train)


# ============================================================
# 5. 定义评估函数
# ============================================================

def evaluate(y_true, y_pred, dataset_name="数据集", strict_less=False):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mse = mean_squared_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)

    nonzero_mask = np.abs(y_true) > 1e-12
    relative_error = np.full_like(y_true, np.nan, dtype=float)

    if np.any(nonzero_mask):
        relative_error[nonzero_mask] = np.abs(
            (y_pred[nonzero_mask] - y_true[nonzero_mask])
            / y_true[nonzero_mask]
        ) * 100
        ard = np.nanmean(relative_error)
    else:
        ard = np.nan

    if strict_less:
        within_1pct = np.sum(relative_error < 1)
        within_5pct = np.sum(relative_error < 5)
        within_10pct = np.sum(relative_error < 10)
    else:
        within_1pct = np.sum(relative_error <= 1)
        within_5pct = np.sum(relative_error <= 5)
        within_10pct = np.sum(relative_error <= 10)

    print(f"\n{dataset_name}评估结果:")
    print(f"R² = {r2:.4f}")
    print(f"MSE = {mse:.4f}")
    print(f"ARD = {ard:.2f}%")

    if strict_less:
        print(f"误差 < 1% 的点数: {within_1pct}")
        print(f"误差 < 5% 的点数: {within_5pct}")
        print(f"误差 < 10% 的点数: {within_10pct}")
    else:
        print(f"误差 ≤ 1% 的点数: {within_1pct}")
        print(f"误差 ≤ 5% 的点数: {within_5pct}")
        print(f"误差 ≤ 10% 的点数: {within_10pct}")

    return {
        "MSE": mse,
        "R2": r2,
        "ARD_%": ard,
        "Relative_Error_%": relative_error,
        "within_1pct": within_1pct,
        "within_5pct": within_5pct,
        "within_10pct": within_10pct
    }


# ============================================================
# 6. 训练集预测与评估
# ============================================================

y_train_pred = model.predict(X_train)

train_metrics = evaluate(
    y_train,
    y_train_pred,
    dataset_name="训练集",
    strict_less=False
)


# ============================================================
# 7. 测试集预测与评估
# ============================================================

y_test_pred = model.predict(X_test)

test_metrics = evaluate(
    y_test,
    y_test_pred,
    dataset_name="测试集",
    strict_less=False
)


# ============================================================
# 7.1 完整数据集统计：训练集 + 测试集
# ============================================================

y_all_true = np.concatenate([y_train, y_test])
y_all_pred = np.concatenate([y_train_pred, y_test_pred])
id_all = np.concatenate([id_train, id_test])
T_all = np.concatenate([T_train, T_test])

all_metrics = evaluate(
    y_all_true,
    y_all_pred,
    dataset_name="完整数据集：训练集 + 测试集",
    strict_less=True
)

print("\n完整数据集 1%，5%，10%分别为：")
print(all_metrics["within_1pct"])
print(all_metrics["within_5pct"])
print(all_metrics["within_10pct"])


# ============================================================
# 8. 输出训练集预测结果
# ============================================================

results_train = pd.DataFrame({
    "Material_ID": id_train,
    "Temperature (K)": T_train,
    "Cp_measured": y_train,
    "Cp_predicted": y_train_pred,
    "Relative_Error_%": train_metrics["Relative_Error_%"]
})

results_train.to_excel(
    "训练集_按物质划分_线性Cp预测结果.xlsx",
    index=False
)

print("\n训练集结果已保存为: 训练集_按物质划分_线性Cp预测结果.xlsx")


# ============================================================
# 9. 输出测试集预测结果
# ============================================================

results_test = pd.DataFrame({
    "Material_ID": id_test,
    "Temperature (K)": T_test,
    "Cp_measured": y_test,
    "Cp_predicted": y_test_pred,
    "Relative_Error_%": test_metrics["Relative_Error_%"]
})

results_test.to_excel(
    "测试集_按物质划分_线性Cp预测结果.xlsx",
    index=False
)

print("测试集结果已保存为: 测试集_按物质划分_线性Cp预测结果.xlsx")


# ============================================================
# 10. 输出完整数据集预测结果
# ============================================================

results_all = pd.DataFrame({
    "Material_ID": id_all,
    "Temperature (K)": T_all,
    "Cp_measured": y_all_true,
    "Cp_predicted": y_all_pred,
    "Relative_Error_%": all_metrics["Relative_Error_%"]
})

results_all.to_excel(
    "完整数据集_按物质划分_线性Cp预测结果.xlsx",
    index=False
)

print("完整数据集结果已保存为: 完整数据集_按物质划分_线性Cp预测结果.xlsx")


# ============================================================
# 11. 保存评估汇总
# ============================================================

summary_df = pd.DataFrame([
    [
        "train",
        train_metrics["R2"],
        train_metrics["MSE"],
        train_metrics["ARD_%"],
        train_metrics["within_1pct"],
        train_metrics["within_5pct"],
        train_metrics["within_10pct"]
    ],
    [
        "test",
        test_metrics["R2"],
        test_metrics["MSE"],
        test_metrics["ARD_%"],
        test_metrics["within_1pct"],
        test_metrics["within_5pct"],
        test_metrics["within_10pct"]
    ],
    [
        "all",
        all_metrics["R2"],
        all_metrics["MSE"],
        all_metrics["ARD_%"],
        all_metrics["within_1pct"],
        all_metrics["within_5pct"],
        all_metrics["within_10pct"]
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

summary_df.to_excel(
    "线性Cp模型_按物质划分_评估汇总.xlsx",
    index=False
)

print("评估汇总已保存为: 线性Cp模型_按物质划分_评估汇总.xlsx")


# ============================================================
# 12. 输出基团贡献系数（含温度项）
# ============================================================

coefficients = pd.DataFrame({
    "Group": list(group_cols) + [f"{group}_T" for group in group_cols],
    "Contribution": model.coef_
})

coefficients_sorted = coefficients.sort_values(
    by="Contribution",
    ascending=False
)

coefficients_sorted.to_excel(
    "线性Cp模型_基团贡献系数.xlsx",
    index=False
)

print("\n基团贡献系数（包含乘温项）:")
print(coefficients_sorted.to_string(index=False))

print("\n基团贡献系数已保存为: 线性Cp模型_基团贡献系数.xlsx")


# ============================================================
# 13. 输出模型信息
# ============================================================

print("\n当前线性模型:")
print(model)