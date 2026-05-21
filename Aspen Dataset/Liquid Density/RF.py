# import pandas as pd
# import numpy as np
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split
#
# # 1. 读取数据
# file_path = "liquid density.xlsx"
# df = pd.read_excel(file_path, sheet_name="Sheet1")
#
# # 2. 定义列索引
# group_cols = df.columns[12:31]   # 基团列
# temp_cols = df.columns[31:41]    # 温度列
# v_cols = df.columns[41:51]       # 液体密度列（单位假设为 mol/m³ 或 kg/m³，根据实际数据）
#
# # 3. 构建全量点级数据集（保留物质 ID）
# X_total, y_total, material_ids, temperatures = [], [], [], []
#
# for i, row in df.iterrows():
#     material_id = row.iloc[0]                     # 第一列为物质 ID
#     Nk = row[group_cols].values.astype(float)
#     temps = row[temp_cols].values.astype(float)
#     vals = row[v_cols].values.astype(float)
#
#     for T, val in zip(temps, vals):
#         if np.isnan(T) or np.isnan(val):
#             continue
#         features = np.concatenate([Nk, [T]])
#         X_total.append(features)
#         y_total.append(val)
#         material_ids.append(material_id)
#         temperatures.append(T)
#
# X_total = np.array(X_total)
# y_total = np.array(y_total)
# material_ids = np.array(material_ids)
# temperatures = np.array(temperatures)
#
# # 4. 按物质 ID 划分训练集 (80%) 和测试集 (20%)
# unique_materials = np.unique(material_ids)
# train_materials, test_materials = train_test_split(
#     unique_materials, test_size=0.2, random_state=42
# )
#
# train_mask = np.isin(material_ids, train_materials)
# test_mask  = np.isin(material_ids, test_materials)
#
# X_train, y_train = X_total[train_mask], y_total[train_mask]
# X_test,  y_test  = X_total[test_mask],  y_total[test_mask]
#
# material_ids_train = material_ids[train_mask]
# temperatures_train = temperatures[train_mask]
# material_ids_test  = material_ids[test_mask]
# temperatures_test  = temperatures[test_mask]
#
# print("========== 按物质划分 ==========")
# print(f"总物质数: {len(unique_materials)}")
# print(f"训练集物质数: {len(train_materials)}")
# print(f"测试集物质数: {len(test_materials)}")
# print(f"训练集样本点数: {X_train.shape[0]}")
# print(f"测试集样本点数: {X_test.shape[0]}")
#
# # 5. 训练随机森林模型（仅用训练集）
# model = RandomForestRegressor(n_estimators=100, random_state=42)
# model.fit(X_train, y_train)
#
# # 6. 定义评估函数
# def evaluate(y_true, y_pred, name="数据集"):
#     r2 = r2_score(y_true, y_pred)
#     mse = mean_squared_error(y_true, y_pred)
#     rel_err = np.abs((y_pred - y_true) / y_true) * 100
#     ard = np.mean(rel_err)
#     within_1pct = np.sum(rel_err <= 1)
#     within_5pct = np.sum(rel_err <= 5)
#     within_10pct = np.sum(rel_err <= 10)
#
#     print(f"\n📊 {name} 结果：")
#     print(f"R²  = {r2:.4f}")
#     print(f"MSE = {mse:.6f}")
#     print(f"ARD = {ard:.2f}%")
#     print(f"相对误差 ≤ 1% 的点数: {within_1pct}")
#     print(f"相对误差 ≤ 5% 的点数: {within_5pct}")
#     print(f"相对误差 ≤ 10% 的点数: {within_10pct}")
#     return rel_err
#
# # 7. 训练集评估
# y_train_pred = model.predict(X_train)
# rel_err_train = evaluate(y_train, y_train_pred, "训练集")
#
# # 8. 测试集评估
# y_test_pred = model.predict(X_test)
# rel_err_test = evaluate(y_test, y_test_pred, "测试集")
#
# # 9. 保存预测结果（分别存入两个工作表）
# train_results = pd.DataFrame({
#     "Material_ID": material_ids_train,
#     "Temperature (K)": temperatures_train,
#     "Measured": y_train,
#     "Predicted": y_train_pred,
#     "Absolute Error": np.abs(y_train - y_train_pred),
#     "Relative Error (%)": rel_err_train
# })
#
# test_results = pd.DataFrame({
#     "Material_ID": material_ids_test,
#     "Temperature (K)": temperatures_test,
#     "Measured": y_test,
#     "Predicted": y_test_pred,
#     "Absolute Error": np.abs(y_test - y_test_pred),
#     "Relative Error (%)": rel_err_test
# })
#
# # 汇总指标表
# summary = pd.DataFrame([
#     {"Set": "Train", "R2": r2_score(y_train, y_train_pred),
#      "MSE": mean_squared_error(y_train, y_train_pred),
#      "ARD_%": np.mean(np.abs((y_train_pred - y_train)/y_train)*100)},
#     {"Set": "Test", "R2": r2_score(y_test, y_test_pred),
#      "MSE": mean_squared_error(y_test, y_test_pred),
#      "ARD_%": np.mean(np.abs((y_test_pred - y_test)/y_test)*100)}
# ])
#
# output_file = "LiquidDensity预测结果_基团加温度_RF_train_test_split.xlsx"
# with pd.ExcelWriter(output_file, engine="xlsxwriter") as writer:
#     train_results.to_excel(writer, sheet_name="Train_Predictions", index=False)
#     test_results.to_excel(writer, sheet_name="Test_Predictions", index=False)
#     summary.to_excel(writer, sheet_name="Summary", index=False)
#
# print(f"\n✅ 已保存预测结果为: {output_file}")


import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


# ============================================================
# 1. 读取数据
# ============================================================
file_path = "liquid density.xlsx"
df = pd.read_excel(file_path, sheet_name="Sheet1")


# ============================================================
# 2. 定义列索引
# ============================================================
material_id_col = df.columns[0]  # 第一列为物质 ID

group_cols = df.columns[12:31]   # 19个基团列
temp_cols = df.columns[31:41]    # 10个温度列
v_cols = df.columns[41:51]       # 10个液体密度列


# ============================================================
# 3. 数值化
# ============================================================
for col in list(group_cols) + list(temp_cols) + list(v_cols):
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=[material_id_col]).copy().reset_index(drop=True)


# ============================================================
# 4. 构建全量点级数据集
# ============================================================
X_total = []
y_total = []
material_ids = []
temperatures = []

for _, row in df.iterrows():
    material_id = row[material_id_col]

    Nk = row[group_cols].to_numpy(dtype=float)
    temps = row[temp_cols].to_numpy(dtype=float)
    vals = row[v_cols].to_numpy(dtype=float)

    # 基团缺失则跳过该物质
    if not np.isfinite(Nk).all():
        continue

    for T, val in zip(temps, vals):
        if not np.isfinite(T) or not np.isfinite(val):
            continue

        features = np.concatenate([
            Nk,
            [T]
        ])

        X_total.append(features)
        y_total.append(val)
        material_ids.append(material_id)
        temperatures.append(T)

X_total = np.array(X_total, dtype=float)
y_total = np.array(y_total, dtype=float)
material_ids = np.array(material_ids)
temperatures = np.array(temperatures, dtype=float)


# ============================================================
# 5. 按物质 ID 划分训练集 / 测试集
# ============================================================
unique_materials = np.unique(material_ids)

train_materials, test_materials = train_test_split(
    unique_materials,
    test_size=0.2,
    random_state=42
)

train_mask = np.isin(material_ids, train_materials)
test_mask = np.isin(material_ids, test_materials)

X_train = X_total[train_mask]
y_train = y_total[train_mask]

X_test = X_total[test_mask]
y_test = y_total[test_mask]

material_ids_train = material_ids[train_mask]
temperatures_train = temperatures[train_mask]

material_ids_test = material_ids[test_mask]
temperatures_test = temperatures[test_mask]

print("========== 按物质划分 ==========")
print(f"总物质数: {len(unique_materials)}")
print(f"训练集物质数: {len(train_materials)}")
print(f"测试集物质数: {len(test_materials)}")
print(f"训练集样本点数: {X_train.shape[0]}")
print(f"测试集样本点数: {X_test.shape[0]}")
print(f"最终模型特征数: {X_train.shape[1]}")


# ============================================================
# 6. 训练随机森林模型
# ============================================================
model = RandomForestRegressor(
    n_estimators=100,
    random_state=42,
    n_jobs=-1
)

print("\n开始训练 RF 模型...")
model.fit(X_train, y_train)

print("\nRF 模型参数:")
print(model)


# ============================================================
# 7. 评估函数
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
        print(f"\n{name} 结果：无有效样本")

        summary = {
            "Dataset": name,
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

    print(f"\n{name} 结果：")
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
        "Dataset": name,
        "R2": r2,
        "MSE": mse,
        "ARD_%": ard,
        "within_1pct": within_1pct,
        "within_5pct": within_5pct,
        "within_10pct": within_10pct
    }

    return relative_error, summary


# ============================================================
# 8. 训练集预测与评估
# ============================================================
y_train_pred = model.predict(X_train)

rel_err_train, train_summary = evaluate_dataset(
    y_train,
    y_train_pred,
    name="Train",
    strict_less=False
)


# ============================================================
# 9. 测试集预测与评估
# ============================================================
y_test_pred = model.predict(X_test)

rel_err_test, test_summary = evaluate_dataset(
    y_test,
    y_test_pred,
    name="Test",
    strict_less=False
)


# ============================================================
# 9.1 完整数据集统计：训练集 + 测试集
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

rel_err_all, all_summary = evaluate_dataset(
    y_all_true,
    y_all_pred,
    name="All_train_plus_test",
    strict_less=True
)

print("\nLiquid Density RF 完整数据集预测偏差 1%，5%，10%分别为：")
print(all_summary["within_1pct"])
print(all_summary["within_5pct"])
print(all_summary["within_10pct"])


# ============================================================
# 10. 保存训练集结果
# ============================================================
train_results = pd.DataFrame({
    "Set": "Train",
    "Material_ID": material_ids_train,
    "Temperature (K)": temperatures_train,
    "Liquid_Density_measured": y_train,
    "Liquid_Density_predicted": y_train_pred,
    "Absolute Error": np.abs(y_train - y_train_pred),
    "Relative Error (%)": rel_err_train
})


# ============================================================
# 11. 保存测试集结果
# ============================================================
test_results = pd.DataFrame({
    "Set": "Test",
    "Material_ID": material_ids_test,
    "Temperature (K)": temperatures_test,
    "Liquid_Density_measured": y_test,
    "Liquid_Density_predicted": y_test_pred,
    "Absolute Error": np.abs(y_test - y_test_pred),
    "Relative Error (%)": rel_err_test
})


# ============================================================
# 12. 保存完整数据集结果
# ============================================================
all_results = pd.DataFrame({
    "Set": "All_train_plus_test",
    "Material_ID": material_ids_all,
    "Temperature (K)": temperatures_all,
    "Liquid_Density_measured": y_all_true,
    "Liquid_Density_predicted": y_all_pred,
    "Absolute Error": np.abs(y_all_true - y_all_pred),
    "Relative Error (%)": rel_err_all
})


# ============================================================
# 13. 保存汇总指标
# ============================================================
summary = pd.DataFrame([
    train_summary,
    test_summary,
    all_summary
])


# ============================================================
# 14. 保存到 Excel
# ============================================================
output_file = "LiquidDensity预测结果_基团加温度_RF_train_test_split.xlsx"

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

    summary.to_excel(
        writer,
        sheet_name="Summary",
        index=False
    )

print(f"\n已保存预测结果为: {output_file}")


# ============================================================
# 15. 保存特征重要性
# ============================================================
feature_names = list(group_cols) + ["Temperature"]

feature_importance_df = pd.DataFrame({
    "Feature": feature_names,
    "Importance": model.feature_importances_
}).sort_values(
    by="Importance",
    ascending=False
)

importance_file = "LiquidDensity_RF_feature_importance.xlsx"

feature_importance_df.to_excel(
    importance_file,
    index=False
)

print(f"特征重要性已保存为: {importance_file}")


# ============================================================
# 16. 输出模型结构记录
# ============================================================
print("\n当前 Liquid Density RF 直接预测模型结构:")
print("Dataset: liquid density.xlsx, Sheet1")
print("Target: ordinary Liquid Density")
print("Model: RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)")
print("Input features: 19 group counts + Temperature")
print("Split: material-level 8:2 split, random_state=42")
print("Final all-data statistics use strict thresholds: <1%, <5%, <10%")