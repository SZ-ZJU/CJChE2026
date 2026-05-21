# import pandas as pd
# import numpy as np
#
# from sklearn.model_selection import train_test_split
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.metrics import mean_squared_error, r2_score
#
#
# # 1. 读取数据
# file_path = "internal energy 207.xlsx"
# df = pd.read_excel(file_path, sheet_name="Sheet6")
#
#
# # 2. 定义列索引
# material_id_col = df.columns[0]          # 第一列：物质ID
# group_cols = df.columns[13:32]           # 基团列
# temp_cols = df.columns[32:42]            # 温度列
# internal_energy_cols = df.columns[42:52] # 内能列
#
#
# # 3. 先按物质 8:2 划分
# unique_materials = df[material_id_col].dropna().unique()
#
# train_materials, test_materials = train_test_split(
#     unique_materials,
#     test_size=0.2,
#     random_state=42
# )
#
# train_df = df[df[material_id_col].isin(train_materials)].copy()
# test_df = df[df[material_id_col].isin(test_materials)].copy()
#
# print("========== 按物质划分 ==========")
# print(f"总物质数: {len(unique_materials)}")
# print(f"训练集物质数: {len(train_materials)}")
# print(f"测试集物质数: {len(test_materials)}")
#
#
# # 4. 构建点数据集
# def build_point_dataset(df_part):
#     X_total, y_total, material_ids, temperatures = [], [], [], []
#
#     for _, row in df_part.iterrows():
#         material_id = row[material_id_col]
#
#         Nk = pd.to_numeric(row[group_cols], errors="coerce").values
#         temps = pd.to_numeric(row[temp_cols], errors="coerce").values
#         ies = pd.to_numeric(row[internal_energy_cols], errors="coerce").values
#
#         # 基团有缺失则整行跳过
#         if not np.isfinite(Nk).all():
#             continue
#
#         for T, ien in zip(temps, ies):
#             if not np.isfinite(T) or not np.isfinite(ien):
#                 continue
#
#             features = np.concatenate([Nk, [T]])
#
#             X_total.append(features)
#             y_total.append(ien)
#             material_ids.append(material_id)
#             temperatures.append(T)
#
#     X_total = np.array(X_total, dtype=float)
#     y_total = np.array(y_total, dtype=float)
#
#     return X_total, y_total, material_ids, temperatures
#
#
# X_train, y_train, material_ids_train, temperatures_train = build_point_dataset(train_df)
# X_test, y_test, material_ids_test, temperatures_test = build_point_dataset(test_df)
#
# print(f"训练集样本点数: {len(X_train)}")
# print(f"测试集样本点数: {len(X_test)}")
#
#
# # 5. 定义随机森林模型
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
# # 6. 训练模型
# print("\n训练 RF 模型...")
# model.fit(X_train, y_train)
#
#
# # 7. 评估函数
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
#     relative_error[nonzero_mask] = np.abs(
#         (y_true[nonzero_mask] - y_pred[nonzero_mask])
#         / y_true[nonzero_mask]
#     ) * 100
#
#     ard = np.nanmean(relative_error)
#
#     error_1_percent = np.sum(relative_error < 1)
#     error_5_percent = np.sum(relative_error < 5)
#     error_10_percent = np.sum(relative_error < 10)
#
#     print(f"\n{name} 模型评估：")
#     print(f"R2  = {r2:.6f}")
#     print(f"MSE = {mse:.10f}")
#     print(f"ARD = {ard:.4f}%")
#
#     print(f"\n{name} 统计结果：")
#     print(f"数据点相对误差小于1%: {error_1_percent}个")
#     print(f"数据点相对误差小于5%: {error_5_percent}个")
#     print(f"数据点相对误差小于10%: {error_10_percent}个")
#
#     summary = {
#         "Dataset": name,
#         "R2": r2,
#         "MSE": mse,
#         "ARD_%": ard,
#         "Count_<1%": error_1_percent,
#         "Count_<5%": error_5_percent,
#         "Count_<10%": error_10_percent
#     }
#
#     return relative_error, summary
#
#
# # 8. 训练集预测
# y_train_pred = model.predict(X_train)
#
# rel_err_train, train_summary = evaluate_dataset(
#     y_train,
#     y_train_pred,
#     name="Train"
# )
#
#
# # 9. 测试集预测
# y_test_pred = model.predict(X_test)
#
# rel_err_test, test_summary = evaluate_dataset(
#     y_test,
#     y_test_pred,
#     name="Test"
# )
#
#
# # 10. 保存结果
# train_result = pd.DataFrame({
#     "Set": "Train",
#     "Material_ID": material_ids_train,
#     "Temperature (K)": temperatures_train,
#     "Internal_energy_measured (J/mol)": y_train,
#     "Internal_energy_predicted (J/mol)": y_train_pred,
#     "Absolute Error": np.abs(y_train - y_train_pred),
#     "Relative Error (%)": rel_err_train
# })
#
# test_result = pd.DataFrame({
#     "Set": "Test",
#     "Material_ID": material_ids_test,
#     "Temperature (K)": temperatures_test,
#     "Internal_energy_measured (J/mol)": y_test,
#     "Internal_energy_predicted (J/mol)": y_test_pred,
#     "Absolute Error": np.abs(y_test - y_test_pred),
#     "Relative Error (%)": rel_err_test
# })
#
# summary_df = pd.DataFrame([
#     train_summary,
#     test_summary
# ])
#
# output_file = "Internal_energy_RF_train_test_split_by_material.xlsx"
#
# with pd.ExcelWriter(output_file, engine="xlsxwriter") as writer:
#     train_result.to_excel(
#         writer,
#         sheet_name="Train_Predictions",
#         index=False
#     )
#
#     test_result.to_excel(
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
# print(f"\n已保存预测结果为: {output_file}")

import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score


# ============================================================
# 1. 读取数据
# ============================================================

file_path = "internal energy 207.xlsx"
df = pd.read_excel(file_path, sheet_name="Sheet6")


# ============================================================
# 2. 定义列索引
# ============================================================

material_id_col = df.columns[0]          # 第一列：物质ID
group_cols = df.columns[13:32]           # 19个基团列
temp_cols = df.columns[32:42]            # 10个温度列
internal_energy_cols = df.columns[42:52] # 10个内能列


# ============================================================
# 3. 数值化
# ============================================================

for col in list(group_cols) + list(temp_cols) + list(internal_energy_cols):
    df[col] = pd.to_numeric(df[col], errors="coerce")


# ============================================================
# 4. 按物质 8:2 划分
# ============================================================

unique_materials = df[material_id_col].dropna().unique()

train_materials, test_materials = train_test_split(
    unique_materials,
    test_size=0.2,
    random_state=42
)

train_materials = set(train_materials)
test_materials = set(test_materials)

train_df = df[df[material_id_col].isin(train_materials)].copy()
test_df = df[df[material_id_col].isin(test_materials)].copy()

print("========== 按物质划分 ==========")
print(f"总物质数: {len(unique_materials)}")
print(f"训练集物质数: {len(train_materials)}")
print(f"测试集物质数: {len(test_materials)}")


# ============================================================
# 5. 构建点级数据集
# ============================================================

def build_point_dataset(df_part):
    X_total, y_total = [], []
    material_ids, temperatures = [], []

    for _, row in df_part.iterrows():
        material_id = row[material_id_col]

        Nk = pd.to_numeric(row[group_cols], errors="coerce").values.astype(float)
        temps = pd.to_numeric(row[temp_cols], errors="coerce").values.astype(float)
        ies = pd.to_numeric(row[internal_energy_cols], errors="coerce").values.astype(float)

        # 基团有缺失则整行跳过
        if not np.isfinite(Nk).all():
            continue

        for T, ie in zip(temps, ies):
            if not np.isfinite(T) or not np.isfinite(ie):
                continue

            features = np.concatenate([Nk, [T]])

            X_total.append(features)
            y_total.append(ie)
            material_ids.append(material_id)
            temperatures.append(T)

    X_total = np.array(X_total, dtype=float)
    y_total = np.array(y_total, dtype=float)
    material_ids = np.array(material_ids)
    temperatures = np.array(temperatures, dtype=float)

    return X_total, y_total, material_ids, temperatures


X_train, y_train, material_ids_train, temperatures_train = build_point_dataset(train_df)
X_test, y_test, material_ids_test, temperatures_test = build_point_dataset(test_df)

print(f"训练集样本点数: {len(X_train)}")
print(f"测试集样本点数: {len(X_test)}")


# ============================================================
# 6. 定义随机森林模型
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
# 7. 训练模型
# ============================================================

print("\n训练 RF 模型...")
model.fit(X_train, y_train)

print("\nRF 模型参数:")
print(model)


# ============================================================
# 8. 评估函数
# ============================================================

def evaluate_dataset(y_true, y_pred, name="数据集", strict_less=True):
    """
    strict_less=True  : 统计 <1%, <5%, <10%
    strict_less=False : 统计 <=1%, <=5%, <=10%
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
        print(f"\n{name} 模型评估：无有效样本")

        summary = {
            "Dataset": name,
            "R2": np.nan,
            "MSE": np.nan,
            "ARD_%": np.nan,
            "Count_<1%": 0,
            "Count_<5%": 0,
            "Count_<10%": 0
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
                y_true_valid[nonzero_mask]
                - y_pred_valid[nonzero_mask]
            )
            / y_true_valid[nonzero_mask]
        ) * 100

        ard = np.nanmean(relative_error_valid)
    else:
        ard = np.nan

    relative_error[finite_mask] = relative_error_valid

    if strict_less:
        error_1_percent = np.sum(relative_error_valid < 1)
        error_5_percent = np.sum(relative_error_valid < 5)
        error_10_percent = np.sum(relative_error_valid < 10)
    else:
        error_1_percent = np.sum(relative_error_valid <= 1)
        error_5_percent = np.sum(relative_error_valid <= 5)
        error_10_percent = np.sum(relative_error_valid <= 10)

    print(f"\n{name} 模型评估：")
    print(f"R2  = {r2:.6f}")
    print(f"MSE = {mse:.10f}")
    print(f"ARD = {ard:.4f}%")

    print(f"\n{name} 统计结果：")
    if strict_less:
        print(f"数据点相对误差小于 1%: {error_1_percent} 个")
        print(f"数据点相对误差小于 5%: {error_5_percent} 个")
        print(f"数据点相对误差小于 10%: {error_10_percent} 个")
    else:
        print(f"数据点相对误差小于等于 1%: {error_1_percent} 个")
        print(f"数据点相对误差小于等于 5%: {error_5_percent} 个")
        print(f"数据点相对误差小于等于 10%: {error_10_percent} 个")

    summary = {
        "Dataset": name,
        "R2": r2,
        "MSE": mse,
        "ARD_%": ard,
        "Count_<1%": error_1_percent,
        "Count_<5%": error_5_percent,
        "Count_<10%": error_10_percent
    }

    return relative_error, summary


# ============================================================
# 9. 训练集预测
# ============================================================

y_train_pred = model.predict(X_train)

rel_err_train, train_summary = evaluate_dataset(
    y_train,
    y_train_pred,
    name="Train",
    strict_less=True
)


# ============================================================
# 10. 测试集预测
# ============================================================

y_test_pred = model.predict(X_test)

rel_err_test, test_summary = evaluate_dataset(
    y_test,
    y_test_pred,
    name="Test",
    strict_less=True
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

rel_err_all, all_summary = evaluate_dataset(
    y_all_true,
    y_all_pred,
    name="All_train_plus_test",
    strict_less=True
)

print("\nInternal Energy RF 完整数据集预测偏差 1%，5%，10%分别为：")
print(all_summary["Count_<1%"])
print(all_summary["Count_<5%"])
print(all_summary["Count_<10%"])


# ============================================================
# 11. 保存训练集结果
# ============================================================

train_result = pd.DataFrame({
    "Set": "Train",
    "Material_ID": material_ids_train,
    "Temperature (K)": temperatures_train,
    "Internal_energy_measured (J/mol)": y_train,
    "Internal_energy_predicted (J/mol)": y_train_pred,
    "Absolute Error": np.abs(y_train - y_train_pred),
    "Relative Error (%)": rel_err_train
})


# ============================================================
# 12. 保存测试集结果
# ============================================================

test_result = pd.DataFrame({
    "Set": "Test",
    "Material_ID": material_ids_test,
    "Temperature (K)": temperatures_test,
    "Internal_energy_measured (J/mol)": y_test,
    "Internal_energy_predicted (J/mol)": y_test_pred,
    "Absolute Error": np.abs(y_test - y_test_pred),
    "Relative Error (%)": rel_err_test
})


# ============================================================
# 13. 保存完整数据集结果
# ============================================================

all_result = pd.DataFrame({
    "Set": "All_train_plus_test",
    "Material_ID": material_ids_all,
    "Temperature (K)": temperatures_all,
    "Internal_energy_measured (J/mol)": y_all_true,
    "Internal_energy_predicted (J/mol)": y_all_pred,
    "Absolute Error": np.abs(y_all_true - y_all_pred),
    "Relative Error (%)": rel_err_all
})


# ============================================================
# 14. 保存结果
# ============================================================

summary_df = pd.DataFrame([
    train_summary,
    test_summary,
    all_summary
])

output_file = "Internal_energy_RF_train_test_split_by_material.xlsx"

with pd.ExcelWriter(output_file, engine="xlsxwriter") as writer:
    train_result.to_excel(
        writer,
        sheet_name="Train_Predictions",
        index=False
    )

    test_result.to_excel(
        writer,
        sheet_name="Test_Predictions",
        index=False
    )

    all_result.to_excel(
        writer,
        sheet_name="All_Predictions",
        index=False
    )

    summary_df.to_excel(
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

feature_importance_file = "Internal_energy_RF_feature_importance.xlsx"

feature_importance_df.to_excel(
    feature_importance_file,
    index=False
)

print(f"特征重要性已保存为: {feature_importance_file}")


# ============================================================
# 16. 输出模型结构记录
# ============================================================

print("\n当前 Internal Energy RF 直接预测模型结构:")
print("Dataset: internal energy 207.xlsx, Sheet6")
print("Target: ordinary Internal Energy")
print("Model: RandomForestRegressor")
print("Parameters:")
print(model)
print("Input features: 19 group counts + Temperature")
print("Split: material-level 8:2 split")
print("Final all-data statistics use strict thresholds: <1%, <5%, <10%")