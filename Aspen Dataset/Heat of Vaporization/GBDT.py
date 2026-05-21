# import pandas as pd
# import numpy as np
#
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split
# from sklearn.ensemble import GradientBoostingRegressor
#
#
# # ============================================================
# # 1. 读取数据
# # ============================================================
# file_path = "heat of vaporization 204.xlsx"
# df = pd.read_excel(file_path, sheet_name="Sheet1")
#
#
# # ============================================================
# # 2. 定义列索引
# # ============================================================
# id_col = df.columns[0]           # 物质ID列
# group_cols = df.columns[13:32]   # 19个基团
# temp_cols = df.columns[32:42]    # 10个温度点
# hv_cols = df.columns[42:52]      # 10个Hvap点
#
#
# # ============================================================
# # 3. 数值化
# # ============================================================
# for col in list(group_cols) + list(temp_cols) + list(hv_cols):
#     df[col] = pd.to_numeric(df[col], errors="coerce")
#
#
# # ============================================================
# # 4. 按“物质”划分 8:2
# # ============================================================
# unique_materials = df[id_col].dropna().unique()
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
# # 5. 构建训练集 / 测试集样本
# # ============================================================
# X_train, y_train, material_ids_train, temperatures_train = [], [], [], []
# X_test, y_test, material_ids_test, temperatures_test = [], [], [], []
#
# for _, row in df.iterrows():
#     material_id = row[id_col]
#
#     if pd.isna(material_id):
#         continue
#
#     Nk = row[group_cols].values.astype(float)
#     temps = row[temp_cols].values.astype(float)
#     hvaps = row[hv_cols].values.astype(float)
#
#     for T, Hv in zip(temps, hvaps):
#         if np.isnan(T) or np.isnan(Hv):
#             continue
#
#         # 特征 = 19维基团 + 当前温度
#         features = np.concatenate([Nk, [T]])
#
#         if material_id in train_materials:
#             X_train.append(features)
#             y_train.append(Hv)
#             material_ids_train.append(material_id)
#             temperatures_train.append(T)
#
#         elif material_id in test_materials:
#             X_test.append(features)
#             y_test.append(Hv)
#             material_ids_test.append(material_id)
#             temperatures_test.append(T)
#
#
# X_train = np.array(X_train, dtype=float)
# y_train = np.array(y_train, dtype=float)
#
# X_test = np.array(X_test, dtype=float)
# y_test = np.array(y_test, dtype=float)
#
# material_ids_train = np.array(material_ids_train)
# material_ids_test = np.array(material_ids_test)
#
# temperatures_train = np.array(temperatures_train, dtype=float)
# temperatures_test = np.array(temperatures_test, dtype=float)
#
# print(f"训练集样本点数: {len(X_train)}")
# print(f"测试集样本点数: {len(X_test)}")
#
#
# # ============================================================
# # 6. 定义 GBDT 模型
# # ============================================================
# # GBDT 是树模型，通常不需要 StandardScaler
# model = GradientBoostingRegressor(
#     n_estimators=500,
#     learning_rate=0.03,
#     max_depth=3,
#     subsample=0.9,
#     min_samples_split=2,
#     min_samples_leaf=1,
#     loss="squared_error",
#     random_state=42
# )
#
#
# # ============================================================
# # 7. 模型训练
# # ============================================================
# print("\n开始训练 GBDT 模型...")
# model.fit(X_train, y_train)
#
# print("\nGBDT 模型参数:")
# print(model)
#
#
# # ============================================================
# # 8. 评估函数
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
#     print(f"\n{name}评估结果：")
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
# # 9. 训练集预测与评估
# # ============================================================
# y_train_pred = model.predict(X_train)
#
# train_relative_error, train_summary = evaluate_dataset(
#     y_train,
#     y_train_pred,
#     "训练集"
# )
#
#
# # ============================================================
# # 10. 测试集预测与评估
# # ============================================================
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
# # 11. 保存训练集结果
# # ============================================================
# train_result = pd.DataFrame({
#     "Set": "Train",
#     "Material_ID": material_ids_train,
#     "Temperature (K)": temperatures_train,
#     "Hvap_measured (J/mol)": y_train,
#     "Hvap_predicted (J/mol)": y_train_pred,
#     "Absolute Error": np.abs(y_train - y_train_pred),
#     "Relative Error (%)": train_relative_error
# })
#
#
# # ============================================================
# # 12. 保存测试集结果
# # ============================================================
# test_result = pd.DataFrame({
#     "Set": "Test",
#     "Material_ID": material_ids_test,
#     "Temperature (K)": temperatures_test,
#     "Hvap_measured (J/mol)": y_test,
#     "Hvap_predicted (J/mol)": y_test_pred,
#     "Absolute Error": np.abs(y_test - y_test_pred),
#     "Relative Error (%)": test_relative_error
# })
#
#
# # ============================================================
# # 13. 合并保存预测结果
# # ============================================================
# all_result = pd.concat(
#     [train_result, test_result],
#     ignore_index=True
# )
#
# output_result_file = "Hvap预测结果_基团加温度_GBDT_TrainTestSplit.xlsx"
#
# all_result.to_excel(
#     output_result_file,
#     index=False
# )
#
# print(f"\n已保存预测结果为: {output_result_file}")
#
#
# # ============================================================
# # 14. 保存评估汇总
# # ============================================================
# summary_df = pd.DataFrame([
#     train_summary,
#     test_summary
# ])
#
# output_summary_file = "Hvap预测结果_基团加温度_GBDT_评估汇总.xlsx"
#
# summary_df.to_excel(
#     output_summary_file,
#     index=False
# )
#
# print(f"已保存评估汇总为: {output_summary_file}")


import pandas as pd
import numpy as np

from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor


# ============================================================
# 1. 读取数据
# ============================================================
file_path = "heat of vaporization 204.xlsx"
df = pd.read_excel(file_path, sheet_name="Sheet1")


# ============================================================
# 2. 定义列索引
# ============================================================
id_col = df.columns[0]           # 物质ID列
group_cols = df.columns[13:32]   # 19个基团
temp_cols = df.columns[32:42]    # 10个温度点
hv_cols = df.columns[42:52]      # 10个Hvap点


# ============================================================
# 3. 数值化
# ============================================================
for col in list(group_cols) + list(temp_cols) + list(hv_cols):
    df[col] = pd.to_numeric(df[col], errors="coerce")


# ============================================================
# 4. 按“物质”划分 8:2
# ============================================================
unique_materials = df[id_col].dropna().unique()

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
# 5. 构建训练集 / 测试集样本
# ============================================================
X_train, y_train, material_ids_train, temperatures_train = [], [], [], []
X_test, y_test, material_ids_test, temperatures_test = [], [], [], []

for _, row in df.iterrows():
    material_id = row[id_col]

    if pd.isna(material_id):
        continue

    Nk = row[group_cols].values.astype(float)
    temps = row[temp_cols].values.astype(float)
    hvaps = row[hv_cols].values.astype(float)

    for T, Hv in zip(temps, hvaps):
        if np.isnan(T) or np.isnan(Hv):
            continue

        # 特征 = 19维基团 + 当前温度
        features = np.concatenate([Nk, [T]])

        if not np.isfinite(features).all():
            continue

        if material_id in train_materials:
            X_train.append(features)
            y_train.append(Hv)
            material_ids_train.append(material_id)
            temperatures_train.append(T)

        elif material_id in test_materials:
            X_test.append(features)
            y_test.append(Hv)
            material_ids_test.append(material_id)
            temperatures_test.append(T)


X_train = np.array(X_train, dtype=float)
y_train = np.array(y_train, dtype=float)

X_test = np.array(X_test, dtype=float)
y_test = np.array(y_test, dtype=float)

material_ids_train = np.array(material_ids_train)
material_ids_test = np.array(material_ids_test)

temperatures_train = np.array(temperatures_train, dtype=float)
temperatures_test = np.array(temperatures_test, dtype=float)

print(f"训练集样本点数: {len(X_train)}")
print(f"测试集样本点数: {len(X_test)}")


# ============================================================
# 6. 定义 GBDT 模型
# ============================================================
# GBDT 是树模型，通常不需要 StandardScaler
model = GradientBoostingRegressor(
    n_estimators=500,
    learning_rate=0.03,
    max_depth=3,
    subsample=0.9,
    min_samples_split=2,
    min_samples_leaf=1,
    loss="squared_error",
    random_state=42
)


# ============================================================
# 7. 模型训练
# ============================================================
print("\n开始训练 GBDT 模型...")
model.fit(X_train, y_train)

print("\nGBDT 模型参数:")
print(model)


# ============================================================
# 8. 评估函数
# ============================================================
def evaluate_dataset(y_true, y_pred, name="数据集", strict_less=False):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    r2 = r2_score(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)

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

    print(f"\n{name}评估结果：")
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
# 9. 训练集预测与评估
# ============================================================
y_train_pred = model.predict(X_train)

train_relative_error, train_summary = evaluate_dataset(
    y_train,
    y_train_pred,
    "训练集",
    strict_less=False
)


# ============================================================
# 10. 测试集预测与评估
# ============================================================
y_test_pred = model.predict(X_test)

test_relative_error, test_summary = evaluate_dataset(
    y_test,
    y_test_pred,
    "测试集",
    strict_less=False
)


# ============================================================
# 10.1 完整数据集统计：训练集 + 测试集
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

all_relative_error, all_summary = evaluate_dataset(
    y_all_true,
    y_all_pred,
    "完整数据集 train + test",
    strict_less=True
)

print("\nHvap GBDT 完整数据集预测偏差 1%，5%，10%分别为：")
print(all_summary["within_1pct"])
print(all_summary["within_5pct"])
print(all_summary["within_10pct"])


# ============================================================
# 11. 保存训练集结果
# ============================================================
train_result = pd.DataFrame({
    "Set": "Train",
    "Material_ID": material_ids_train,
    "Temperature (K)": temperatures_train,
    "Hvap_measured (J/mol)": y_train,
    "Hvap_predicted (J/mol)": y_train_pred,
    "Absolute Error": np.abs(y_train - y_train_pred),
    "Relative Error (%)": train_relative_error
})


# ============================================================
# 12. 保存测试集结果
# ============================================================
test_result = pd.DataFrame({
    "Set": "Test",
    "Material_ID": material_ids_test,
    "Temperature (K)": temperatures_test,
    "Hvap_measured (J/mol)": y_test,
    "Hvap_predicted (J/mol)": y_test_pred,
    "Absolute Error": np.abs(y_test - y_test_pred),
    "Relative Error (%)": test_relative_error
})


# ============================================================
# 13. 保存完整数据集结果
# ============================================================
all_result = pd.DataFrame({
    "Set": "All_train_plus_test",
    "Material_ID": material_ids_all,
    "Temperature (K)": temperatures_all,
    "Hvap_measured (J/mol)": y_all_true,
    "Hvap_predicted (J/mol)": y_all_pred,
    "Absolute Error": np.abs(y_all_true - y_all_pred),
    "Relative Error (%)": all_relative_error
})


# ============================================================
# 14. 保存预测结果
# ============================================================
output_result_file = "Hvap预测结果_基团加温度_GBDT_TrainTestSplit.xlsx"

with pd.ExcelWriter(output_result_file, engine="xlsxwriter") as writer:
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

print(f"\n已保存预测结果为: {output_result_file}")


# ============================================================
# 15. 保存评估汇总
# ============================================================
summary_df = pd.DataFrame([
    train_summary,
    test_summary,
    all_summary
])

output_summary_file = "Hvap预测结果_基团加温度_GBDT_评估汇总.xlsx"

summary_df.to_excel(
    output_summary_file,
    index=False
)

print(f"已保存评估汇总为: {output_summary_file}")


# ============================================================
# 16. 输出模型结构记录
# ============================================================
print("\n当前 Hvap GBDT 直接预测模型结构:")
print("Target: ordinary Hvap, not ln(Hvap)")
print("Model: GradientBoostingRegressor")
print("Parameters:")
print(model)
print("Input features: 19 group counts + Temperature")
print("Split: material-level 8:2 split")
print("Final all-data statistics use strict thresholds: <1%, <5%, <10%")