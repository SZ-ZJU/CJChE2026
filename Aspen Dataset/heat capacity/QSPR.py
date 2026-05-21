# import pandas as pd
# import numpy as np
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split
#
# # ========= 1. 读取数据 =========
# df = pd.read_excel("Transformed_hp_Dataset.xlsx")
#
# target_col = "Heat Capacity"
#
# # ========= 2. 构造“伪物质ID” =========
# # 假设：每10行属于同一个物质，且这10行在表中连续排列
# rows_per_material = 10
# df = df.reset_index(drop=True).copy()
# df["Pseudo_Material_ID"] = np.arange(len(df)) // rows_per_material
#
# # 检查是否正好是10的整数倍
# if len(df) % rows_per_material != 0:
#     print(f"⚠️ 总行数 {len(df)} 不是 {rows_per_material} 的整数倍，最后一个物质组可能不完整。")
#
# # ========= 3. 按“物质组”做 8:2 划分 =========
# unique_materials = df["Pseudo_Material_ID"].unique()
#
# train_materials, test_materials = train_test_split(
#     unique_materials,
#     test_size=0.2,
#     random_state=41
# )
#
# train_df = df[df["Pseudo_Material_ID"].isin(train_materials)].copy()
# test_df = df[df["Pseudo_Material_ID"].isin(test_materials)].copy()
#
# print("========== 数据划分 ==========")
# print(f"总物质数: {len(unique_materials)}")
# print(f"训练集物质数: {len(train_materials)}")
# print(f"测试集物质数: {len(test_materials)}")
# print(f"训练集样本点数: {len(train_df)}")
# print(f"测试集样本点数: {len(test_df)}")
#
# # ========= 4. 划分特征和目标 =========
# X_train = train_df.drop(columns=[target_col, "Pseudo_Material_ID"])
# y_train = train_df[target_col]
#
# X_test = test_df.drop(columns=[target_col, "Pseudo_Material_ID"])
# y_test = test_df[target_col]
#
# # ========= 5. 删除非数值列 =========
# non_numeric_cols = X_train.select_dtypes(exclude=[np.number]).columns.tolist()
# if len(non_numeric_cols) > 0:
#     print(f"⚠️ 检测到非数值列，已删除: {non_numeric_cols}")
#     X_train = X_train.drop(columns=non_numeric_cols)
#     X_test = X_test.drop(columns=non_numeric_cols)
#
# # ========= 6. 模型训练 =========
# model = RandomForestRegressor(
#     n_estimators=300,
#     random_state=42,
#     n_jobs=-1
# )
# model.fit(X_train, y_train)
#
# # ========= 7. 定义评估函数 =========
# def evaluate(y_true, y_pred, name="数据集"):
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
#             (y_true[nonzero_mask] - y_pred[nonzero_mask]) / y_true[nonzero_mask]
#         ) * 100
#         ard = np.nanmean(relative_error)
#     else:
#         ard = np.nan
#
#     within_1pct = np.sum(relative_error <= 1)
#     within_5pct = np.sum(relative_error <= 5)
#     within_10pct = np.sum(relative_error <= 10)
#
#     print(f"\n{name}结果:")
#     print(f"R²: {r2:.4f}")
#     print(f"MSE: {mse:.4f}")
#     print(f"ARD: {ard:.2f}%")
#     print(f"✅ 误差 ≤ 1% 的点数: {within_1pct}")
#     print(f"✅ 误差 ≤ 5% 的点数: {within_5pct}")
#     print(f"✅ 误差 ≤ 10% 的点数: {within_10pct}")
#
#     return {
#         "R2": r2,
#         "MSE": mse,
#         "ARD_%": ard,
#         "Relative_Error_%": relative_error,
#         "within_1pct": within_1pct,
#         "within_5pct": within_5pct,
#         "within_10pct": within_10pct,
#     }
#
# # ========= 8. 训练集预测 =========
# y_train_pred = model.predict(X_train)
# train_metrics = evaluate(y_train, y_train_pred, name="训练集")
#
# # ========= 9. 测试集预测 =========
# y_test_pred = model.predict(X_test)
# test_metrics = evaluate(y_test, y_test_pred, name="测试集")
#
# # ========= 10. 保存结果 =========
# train_result = train_df.copy()
# train_result["Predicted_Heat_Capacity"] = y_train_pred
# train_result["Relative_Error (%)"] = train_metrics["Relative_Error_%"]
# train_result.to_excel("train_prediction_vs_actual_grouped.xlsx", index=False)
#
# test_result = test_df.copy()
# test_result["Predicted_Heat_Capacity"] = y_test_pred
# test_result["Relative_Error (%)"] = test_metrics["Relative_Error_%"]
# test_result.to_excel("test_prediction_vs_actual_grouped.xlsx", index=False)
#
# summary_df = pd.DataFrame([
#     ["train", train_metrics["R2"], train_metrics["MSE"], train_metrics["ARD_%"],
#      train_metrics["within_1pct"], train_metrics["within_5pct"], train_metrics["within_10pct"]],
#     ["test", test_metrics["R2"], test_metrics["MSE"], test_metrics["ARD_%"],
#      test_metrics["within_1pct"], test_metrics["within_5pct"], test_metrics["within_10pct"]],
# ], columns=["Dataset", "R2", "MSE", "ARD_%", "within_1pct", "within_5pct", "within_10pct"])
# summary_df.to_excel("model_summary_grouped.xlsx", index=False)
#
# print("\n✅ 已保存训练集结果: train_prediction_vs_actual_grouped.xlsx")
# print("✅ 已保存测试集结果: test_prediction_vs_actual_grouped.xlsx")
# print("✅ 已保存汇总结果: model_summary_grouped.xlsx")

import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


# ========= 1. 读取数据 =========

df = pd.read_excel("Transformed_hp_Dataset.xlsx")

target_col = "Heat Capacity"


# ========= 2. 构造“伪物质ID” =========
# 假设：每10行属于同一个物质，且这10行在表中连续排列

rows_per_material = 10
df = df.reset_index(drop=True).copy()
df["Pseudo_Material_ID"] = np.arange(len(df)) // rows_per_material

# 检查是否正好是10的整数倍
if len(df) % rows_per_material != 0:
    print(f"⚠️ 总行数 {len(df)} 不是 {rows_per_material} 的整数倍，最后一个物质组可能不完整。")


# ========= 3. 按“物质组”做 8:2 划分 =========

unique_materials = df["Pseudo_Material_ID"].unique()

train_materials, test_materials = train_test_split(
    unique_materials,
    test_size=0.2,
    random_state=41
)

train_df = df[df["Pseudo_Material_ID"].isin(train_materials)].copy()
test_df = df[df["Pseudo_Material_ID"].isin(test_materials)].copy()

print("========== 数据划分 ==========")
print(f"总物质数: {len(unique_materials)}")
print(f"训练集物质数: {len(train_materials)}")
print(f"测试集物质数: {len(test_materials)}")
print(f"训练集样本点数: {len(train_df)}")
print(f"测试集样本点数: {len(test_df)}")


# ========= 4. 划分特征和目标 =========

X_train = train_df.drop(columns=[target_col, "Pseudo_Material_ID"])
y_train = train_df[target_col]

X_test = test_df.drop(columns=[target_col, "Pseudo_Material_ID"])
y_test = test_df[target_col]


# ========= 5. 删除非数值列 =========

non_numeric_cols = X_train.select_dtypes(exclude=[np.number]).columns.tolist()

if len(non_numeric_cols) > 0:
    print(f"⚠️ 检测到非数值列，已删除: {non_numeric_cols}")
    X_train = X_train.drop(columns=non_numeric_cols)
    X_test = X_test.drop(columns=non_numeric_cols)


# ========= 6. 模型训练 =========

model = RandomForestRegressor(
    n_estimators=300,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)


# ========= 7. 定义评估函数 =========

def evaluate(y_true, y_pred, name="数据集"):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    r2 = r2_score(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)

    nonzero_mask = np.abs(y_true) > 1e-12
    relative_error = np.full_like(y_true, np.nan, dtype=float)

    if np.any(nonzero_mask):
        relative_error[nonzero_mask] = np.abs(
            (y_true[nonzero_mask] - y_pred[nonzero_mask]) / y_true[nonzero_mask]
        ) * 100
        ard = np.nanmean(relative_error)
    else:
        ard = np.nan

    within_1pct = np.sum(relative_error <= 1)
    within_5pct = np.sum(relative_error <= 5)
    within_10pct = np.sum(relative_error <= 10)

    print(f"\n{name}结果:")
    print(f"R²: {r2:.4f}")
    print(f"MSE: {mse:.4f}")
    print(f"ARD: {ard:.2f}%")
    print(f"误差 ≤ 1% 的点数: {within_1pct}")
    print(f"误差 ≤ 5% 的点数: {within_5pct}")
    print(f"误差 ≤ 10% 的点数: {within_10pct}")

    return {
        "R2": r2,
        "MSE": mse,
        "ARD_%": ard,
        "Relative_Error_%": relative_error,
        "within_1pct": within_1pct,
        "within_5pct": within_5pct,
        "within_10pct": within_10pct,
    }


# ========= 8. 训练集预测 =========

y_train_pred = model.predict(X_train)
train_metrics = evaluate(y_train, y_train_pred, name="训练集")


# ========= 9. 测试集预测 =========

y_test_pred = model.predict(X_test)
test_metrics = evaluate(y_test, y_test_pred, name="测试集")


# ========= 9.1 完整数据集统计：训练集 + 测试集 =========

y_all_true = np.concatenate([
    np.asarray(y_train, dtype=float),
    np.asarray(y_test, dtype=float)
])

y_all_pred = np.concatenate([
    np.asarray(y_train_pred, dtype=float),
    np.asarray(y_test_pred, dtype=float)
])

nonzero_mask_all = np.abs(y_all_true) > 1e-12
relative_error_all = np.full_like(y_all_true, np.nan, dtype=float)

relative_error_all[nonzero_mask_all] = np.abs(
    (y_all_true[nonzero_mask_all] - y_all_pred[nonzero_mask_all])
    / y_all_true[nonzero_mask_all]
) * 100

all_r2 = r2_score(y_all_true, y_all_pred)
all_mse = mean_squared_error(y_all_true, y_all_pred)
all_ard = np.nanmean(relative_error_all)

all_within_1pct = np.sum(relative_error_all < 1)
all_within_5pct = np.sum(relative_error_all < 5)
all_within_10pct = np.sum(relative_error_all < 10)

print("\n完整数据集结果：训练集 + 测试集")
print(f"R²: {all_r2:.4f}")
print(f"MSE: {all_mse:.4f}")
print(f"ARD: {all_ard:.2f}%")

print("1%，5%，10%分别为：")
print(all_within_1pct)
print(all_within_5pct)
print(all_within_10pct)


# ========= 10. 保存训练集结果 =========

train_result = train_df.copy()
train_result["Predicted_Heat_Capacity"] = y_train_pred
train_result["Relative_Error (%)"] = train_metrics["Relative_Error_%"]

train_result.to_excel(
    "train_prediction_vs_actual_grouped.xlsx",
    index=False
)


# ========= 11. 保存测试集结果 =========

test_result = test_df.copy()
test_result["Predicted_Heat_Capacity"] = y_test_pred
test_result["Relative_Error (%)"] = test_metrics["Relative_Error_%"]

test_result.to_excel(
    "test_prediction_vs_actual_grouped.xlsx",
    index=False
)


# ========= 12. 保存完整数据集结果：训练集 + 测试集 =========

all_result = pd.concat(
    [train_result, test_result],
    axis=0,
    ignore_index=True
)

# 重新写入完整数据集的相对误差，保证顺序和 y_all_true/y_all_pred 一致
all_result["Predicted_Heat_Capacity"] = y_all_pred
all_result["Relative_Error (%)"] = relative_error_all

all_result.to_excel(
    "all_prediction_vs_actual_grouped.xlsx",
    index=False
)


# ========= 13. 保存汇总结果 =========

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
        all_r2,
        all_mse,
        all_ard,
        all_within_1pct,
        all_within_5pct,
        all_within_10pct
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
    "model_summary_grouped.xlsx",
    index=False
)


# ========= 14. 打印保存信息 =========

print("\n已保存训练集结果: train_prediction_vs_actual_grouped.xlsx")
print("已保存测试集结果: test_prediction_vs_actual_grouped.xlsx")
print("已保存完整数据集结果: all_prediction_vs_actual_grouped.xlsx")
print("已保存汇总结果: model_summary_grouped.xlsx")