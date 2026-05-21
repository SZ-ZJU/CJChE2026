# # import pandas as pd
# # from sklearn.ensemble import RandomForestRegressor
# # from sklearn.metrics import mean_squared_error, r2_score
# # from sklearn.model_selection import train_test_split
# # import numpy as np
# #
# # # 读取数据
# # df = pd.read_excel("Transformed_hv_Dataset.xlsx")
# #
# # # 分离特征和目标变量
# # X = df.drop(columns=["Heat of Vaporization"])
# # y = df["Heat of Vaporization"]
# #
# # # 8:2 划分训练集和测试集
# # X_train, X_test, y_train, y_test = train_test_split(
# #     X, y,
# #     test_size=0.2,
# #     random_state=42
# # )
# #
# # # 模型训练
# # model = RandomForestRegressor(random_state=42)
# # model.fit(X_train, y_train)
# #
# # # 训练集预测
# # y_train_pred = model.predict(X_train)
# #
# # # 测试集预测
# # y_test_pred = model.predict(X_test)
# #
# # # 定义评估函数
# # def evaluate_dataset(y_true, y_pred, name="数据集"):
# #     r2 = r2_score(y_true, y_pred)
# #     mse = mean_squared_error(y_true, y_pred)
# #
# #     nonzero_mask = np.abs(y_true) > 1e-12
# #     relative_error = np.full_like(y_true, np.nan, dtype=float)
# #
# #     if np.any(nonzero_mask):
# #         relative_error[nonzero_mask] = np.abs(
# #             (y_pred[nonzero_mask] - y_true[nonzero_mask]) / y_true[nonzero_mask]
# #         ) * 100
# #         ard = np.nanmean(relative_error)
# #     else:
# #         ard = np.nan
# #
# #     within_1pct = np.sum(relative_error <= 1)
# #     within_5pct = np.sum(relative_error <= 5)
# #     within_10pct = np.sum(relative_error <= 10)
# #
# #     print(f"\n{name}评估结果：")
# #     print(f"R²: {r2:.4f}")
# #     print(f"MSE: {mse:.4f}")
# #     print(f"ARD: {ard:.2f}%")
# #     print(f"相对误差 ≤ 1% 的点数: {within_1pct}")
# #     print(f"相对误差 ≤ 5% 的点数: {within_5pct}")
# #     print(f"相对误差 ≤ 10% 的点数: {within_10pct}")
# #
# #     return relative_error, {
# #         "Dataset": name,
# #         "R2": r2,
# #         "MSE": mse,
# #         "ARD_%": ard,
# #         "within_1pct": within_1pct,
# #         "within_5pct": within_5pct,
# #         "within_10pct": within_10pct
# #     }
# #
# # # 输出训练集指标
# # train_relative_error, train_summary = evaluate_dataset(y_train.values, y_train_pred, "训练集")
# #
# # # 输出测试集指标
# # test_relative_error, test_summary = evaluate_dataset(y_test.values, y_test_pred, "测试集")
# #
# # # 保存训练集结果
# # train_comparison_df = X_train.copy()
# # train_comparison_df["Set"] = "Train"
# # train_comparison_df["Actual_Heat_of_Vaporization"] = y_train
# # train_comparison_df["Predicted_Heat_of_Vaporization"] = y_train_pred
# # train_comparison_df["Absolute_Error"] = np.abs(y_train - y_train_pred)
# # train_comparison_df["Relative_Error (%)"] = train_relative_error
# #
# # # 保存测试集结果
# # test_comparison_df = X_test.copy()
# # test_comparison_df["Set"] = "Test"
# # test_comparison_df["Actual_Heat_of_Vaporization"] = y_test
# # test_comparison_df["Predicted_Heat_of_Vaporization"] = y_test_pred
# # test_comparison_df["Absolute_Error"] = np.abs(y_test - y_test_pred)
# # test_comparison_df["Relative_Error (%)"] = test_relative_error
# #
# # # 合并保存详细结果
# # comparison_df = pd.concat([train_comparison_df, test_comparison_df], axis=0)
# # comparison_df.to_excel("prediction_vs_actual_with_error_analysis_8to2.xlsx", index=False)
# # print("\n✅ 已保存预测结果为: prediction_vs_actual_with_error_analysis_8to2.xlsx")
# #
# # # 保存评估汇总
# # summary_df = pd.DataFrame([train_summary, test_summary])
# # summary_df.to_excel("prediction_summary_8to2.xlsx", index=False)
# # print("✅ 已保存评估汇总为: prediction_summary_8to2.xlsx")
#
# import pandas as pd
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split
# import numpy as np
#
# # 读取数据
# df = pd.read_excel("Transformed_hv_Dataset.xlsx").copy()
#
# target_col = "Heat of Vaporization"
#
# # ========= 1. 构造物质ID =========
# if "Material_ID" in df.columns:
#     material_col = "Material_ID"
#     print("✅ 检测到 Material_ID，将按真实物质ID划分")
# else:
#     rows_per_material = 10
#     df = df.reset_index(drop=True).copy()
#     df["Pseudo_Material_ID"] = np.arange(len(df)) // rows_per_material
#     material_col = "Pseudo_Material_ID"
#     print("⚠️ 未检测到 Material_ID，将按每10行一个物质进行划分")
#
#     if len(df) % rows_per_material != 0:
#         print(f"⚠️ 总行数 {len(df)} 不是 {rows_per_material} 的整数倍，最后一个物质组可能不完整。")
#
# # ========= 2. 去掉目标缺失 =========
# df = df.dropna(subset=[target_col]).copy()
#
# # ========= 3. 先按物质划分 =========
# unique_materials = df[material_col].dropna().unique()
#
# train_materials, test_materials = train_test_split(
#     unique_materials,
#     test_size=0.2,
#     random_state=50
# )
#
# train_materials = set(train_materials)
# test_materials = set(test_materials)
#
# train_df = df[df[material_col].isin(train_materials)].copy()
# test_df = df[df[material_col].isin(test_materials)].copy()
#
# print("========== 按物质划分 ==========")
# print(f"总物质数: {len(unique_materials)}")
# print(f"训练集物质数: {len(train_materials)}")
# print(f"测试集物质数: {len(test_materials)}")
# print(f"训练集样本点数: {len(train_df)}")
# print(f"测试集样本点数: {len(test_df)}")
#
# # ========= 4. 分离特征和目标 =========
# X_train = train_df.drop(columns=[target_col]).copy()
# y_train = train_df[target_col].copy()
#
# X_test = test_df.drop(columns=[target_col]).copy()
# y_test = test_df[target_col].copy()
#
# # 删除非数值列（比如 Material_ID）
# non_numeric_cols = X_train.select_dtypes(exclude=[np.number]).columns.tolist()
# if len(non_numeric_cols) > 0:
#     print(f"⚠️ 检测到非数值列，已删除: {non_numeric_cols}")
#     X_train = X_train.drop(columns=non_numeric_cols)
#     X_test = X_test.drop(columns=non_numeric_cols)
#
# # ========= 5. 模型训练 =========
# model = RandomForestRegressor(
#     random_state=50,
#     n_estimators=300,
#     n_jobs=-1
# )
# model.fit(X_train, y_train)
#
#
# # ========= 6. 训练集预测 =========
# y_train_pred = model.predict(X_train)
#
# # ========= 7. 测试集预测 =========
# y_test_pred = model.predict(X_test)
#
# # ========= 8. 定义评估函数 =========
# def evaluate_dataset(y_true, y_pred, name="数据集"):
#     r2 = r2_score(y_true, y_pred)
#     mse = mean_squared_error(y_true, y_pred)
#
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#
#     nonzero_mask = np.abs(y_true) > 1e-12
#     relative_error = np.full_like(y_true, np.nan, dtype=float)
#
#     if np.any(nonzero_mask):
#         relative_error[nonzero_mask] = np.abs(
#             (y_pred[nonzero_mask] - y_true[nonzero_mask]) / y_true[nonzero_mask]
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
#     print(f"R²: {r2:.4f}")
#     print(f"MSE: {mse:.4f}")
#     print(f"ARD: {ard:.2f}%")
#     print(f"相对误差 ≤ 1% 的点数: {within_1pct}")
#     print(f"相对误差 ≤ 5% 的点数: {within_5pct}")
#     print(f"相对误差 ≤ 10% 的点数: {within_10pct}")
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
# # ========= 9. 输出训练集指标 =========
# train_relative_error, train_summary = evaluate_dataset(
#     y_train.values, y_train_pred, "训练集"
# )
#
# # ========= 10. 输出测试集指标 =========
# test_relative_error, test_summary = evaluate_dataset(
#     y_test.values, y_test_pred, "测试集"
# )
#
# # ========= 11. 保存训练集结果 =========
# train_comparison_df = train_df.copy()
# train_comparison_df["Set"] = "Train"
# train_comparison_df["Actual_Heat_of_Vaporization"] = y_train
# train_comparison_df["Predicted_Heat_of_Vaporization"] = y_train_pred
# train_comparison_df["Absolute_Error"] = np.abs(y_train - y_train_pred)
# train_comparison_df["Relative_Error (%)"] = train_relative_error
#
# # ========= 12. 保存测试集结果 =========
# test_comparison_df = test_df.copy()
# test_comparison_df["Set"] = "Test"
# test_comparison_df["Actual_Heat_of_Vaporization"] = y_test
# test_comparison_df["Predicted_Heat_of_Vaporization"] = y_test_pred
# test_comparison_df["Absolute_Error"] = np.abs(y_test - y_test_pred)
# test_comparison_df["Relative_Error (%)"] = test_relative_error
#
# # ========= 13. 合并保存详细结果 =========
# comparison_df = pd.concat([train_comparison_df, test_comparison_df], axis=0)
# comparison_df.to_excel("prediction_vs_actual_with_error_analysis_by_material.xlsx", index=False)
# print("\n✅ 已保存预测结果为: prediction_vs_actual_with_error_analysis_by_material.xlsx")
#
# # ========= 14. 保存评估汇总 =========
# summary_df = pd.DataFrame([train_summary, test_summary])
# summary_df.to_excel("prediction_summary_by_material.xlsx", index=False)
# print("✅ 已保存评估汇总为: prediction_summary_by_material.xlsx")

import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


# ============================================================
# 1. 读取数据
# ============================================================

df = pd.read_excel("Transformed_hv_Dataset.xlsx").copy()

target_col = "Heat of Vaporization"


# ============================================================
# 2. 构造物质ID
# ============================================================

if "Material_ID" in df.columns:
    material_col = "Material_ID"
    print("检测到 Material_ID，将按真实物质ID划分")
else:
    rows_per_material = 10
    df = df.reset_index(drop=True).copy()
    df["Pseudo_Material_ID"] = np.arange(len(df)) // rows_per_material
    material_col = "Pseudo_Material_ID"
    print("未检测到 Material_ID，将按每10行一个物质进行划分")

    if len(df) % rows_per_material != 0:
        print(f"警告：总行数 {len(df)} 不是 {rows_per_material} 的整数倍，最后一个物质组可能不完整。")


# ============================================================
# 3. 去掉目标缺失
# ============================================================

df = df.dropna(subset=[target_col]).copy()


# ============================================================
# 4. 按物质划分训练集 / 测试集
# ============================================================

unique_materials = df[material_col].dropna().unique()

train_materials, test_materials = train_test_split(
    unique_materials,
    test_size=0.2,
    random_state=50
)

train_materials = set(train_materials)
test_materials = set(test_materials)

train_df = df[df[material_col].isin(train_materials)].copy()
test_df = df[df[material_col].isin(test_materials)].copy()

print("========== 按物质划分 ==========")
print(f"总物质数: {len(unique_materials)}")
print(f"训练集物质数: {len(train_materials)}")
print(f"测试集物质数: {len(test_materials)}")
print(f"训练集样本点数: {len(train_df)}")
print(f"测试集样本点数: {len(test_df)}")


# ============================================================
# 5. 分离特征和目标
# ============================================================

X_train = train_df.drop(columns=[target_col]).copy()
y_train = train_df[target_col].copy()

X_test = test_df.drop(columns=[target_col]).copy()
y_test = test_df[target_col].copy()


# ============================================================
# 6. 删除非数值列
# ============================================================

non_numeric_cols = X_train.select_dtypes(exclude=[np.number]).columns.tolist()

if len(non_numeric_cols) > 0:
    print(f"检测到非数值列，已删除: {non_numeric_cols}")
    X_train = X_train.drop(columns=non_numeric_cols)
    X_test = X_test.drop(columns=non_numeric_cols)


# ============================================================
# 7. 删除或过滤特征中的 NaN / inf
# ============================================================

X_train = X_train.apply(pd.to_numeric, errors="coerce")
X_test = X_test.apply(pd.to_numeric, errors="coerce")

y_train = pd.to_numeric(y_train, errors="coerce")
y_test = pd.to_numeric(y_test, errors="coerce")

train_valid_mask = (
    np.isfinite(X_train.values).all(axis=1)
    & np.isfinite(y_train.values)
)

test_valid_mask = (
    np.isfinite(X_test.values).all(axis=1)
    & np.isfinite(y_test.values)
)

train_df = train_df.loc[train_valid_mask].copy()
test_df = test_df.loc[test_valid_mask].copy()

X_train = X_train.loc[train_valid_mask].copy()
X_test = X_test.loc[test_valid_mask].copy()

y_train = y_train.loc[train_valid_mask].copy()
y_test = y_test.loc[test_valid_mask].copy()

print("\n========== 有效建模样本 ==========")
print(f"训练集有效样本点数: {len(X_train)}")
print(f"测试集有效样本点数: {len(X_test)}")
print(f"最终模型特征数: {X_train.shape[1]}")


# ============================================================
# 8. 模型训练
# ============================================================

model = RandomForestRegressor(
    random_state=50,
    n_estimators=300,
    n_jobs=-1
)

model.fit(X_train, y_train)


# ============================================================
# 9. 预测
# ============================================================

y_train_pred = model.predict(X_train)
y_test_pred = model.predict(X_test)


# ============================================================
# 10. 定义评估函数
# ============================================================

def evaluate_dataset(y_true, y_pred, name="数据集", strict_less=False):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    finite_mask = np.isfinite(y_true) & np.isfinite(y_pred)

    y_true_valid = y_true[finite_mask]
    y_pred_valid = y_pred[finite_mask]

    relative_error = np.full_like(y_true, np.nan, dtype=float)

    if len(y_true_valid) == 0:
        print(f"\n{name}评估结果：无有效样本")

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

    print(f"\n{name}评估结果：")
    print(f"R²: {r2:.4f}")
    print(f"MSE: {mse:.4f}")
    print(f"ARD: {ard:.2f}%")

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
# 11. 训练集 / 测试集评估
# ============================================================

train_relative_error, train_summary = evaluate_dataset(
    y_train.values,
    y_train_pred,
    "训练集",
    strict_less=False
)

test_relative_error, test_summary = evaluate_dataset(
    y_test.values,
    y_test_pred,
    "测试集",
    strict_less=False
)


# ============================================================
# 12. 完整数据集统计：训练集 + 测试集
# ============================================================

y_all_true = np.concatenate([
    y_train.values,
    y_test.values
])

y_all_pred = np.concatenate([
    y_train_pred,
    y_test_pred
])

all_relative_error, all_summary = evaluate_dataset(
    y_all_true,
    y_all_pred,
    "完整数据集 train + test",
    strict_less=True
)

print("\nTransformed Hvap RF 完整数据集预测偏差 1%，5%，10%分别为：")
print(all_summary["within_1pct"])
print(all_summary["within_5pct"])
print(all_summary["within_10pct"])


# ============================================================
# 13. 保存训练集结果
# ============================================================

train_comparison_df = train_df.copy()
train_comparison_df["Set"] = "Train"
train_comparison_df["Actual_Heat_of_Vaporization"] = y_train.values
train_comparison_df["Predicted_Heat_of_Vaporization"] = y_train_pred
train_comparison_df["Absolute_Error"] = np.abs(y_train.values - y_train_pred)
train_comparison_df["Relative_Error (%)"] = train_relative_error


# ============================================================
# 14. 保存测试集结果
# ============================================================

test_comparison_df = test_df.copy()
test_comparison_df["Set"] = "Test"
test_comparison_df["Actual_Heat_of_Vaporization"] = y_test.values
test_comparison_df["Predicted_Heat_of_Vaporization"] = y_test_pred
test_comparison_df["Absolute_Error"] = np.abs(y_test.values - y_test_pred)
test_comparison_df["Relative_Error (%)"] = test_relative_error


# ============================================================
# 15. 保存完整数据集结果
# ============================================================

all_comparison_df = pd.concat(
    [train_comparison_df, test_comparison_df],
    axis=0,
    ignore_index=True
)

all_comparison_df["Set"] = "All_train_plus_test"
all_comparison_df["Actual_Heat_of_Vaporization"] = y_all_true
all_comparison_df["Predicted_Heat_of_Vaporization"] = y_all_pred
all_comparison_df["Absolute_Error"] = np.abs(y_all_true - y_all_pred)
all_comparison_df["Relative_Error (%)"] = all_relative_error


# ============================================================
# 16. 保存详细结果
# ============================================================

output_prediction_file = "prediction_vs_actual_with_error_analysis_by_material.xlsx"

with pd.ExcelWriter(output_prediction_file, engine="xlsxwriter") as writer:
    pd.concat(
        [train_comparison_df, test_comparison_df],
        axis=0,
        ignore_index=True
    ).to_excel(
        writer,
        sheet_name="train_test_predictions",
        index=False
    )

    all_comparison_df.to_excel(
        writer,
        sheet_name="all_predictions",
        index=False
    )

print(f"\n已保存预测结果为: {output_prediction_file}")


# ============================================================
# 17. 保存评估汇总
# ============================================================

summary_df = pd.DataFrame([
    train_summary,
    test_summary,
    all_summary
])

output_summary_file = "prediction_summary_by_material.xlsx"

summary_df.to_excel(
    output_summary_file,
    index=False
)

print(f"已保存评估汇总为: {output_summary_file}")


# ============================================================
# 18. 保存特征重要性
# ============================================================

feature_importance_df = pd.DataFrame({
    "Feature": X_train.columns,
    "Importance": model.feature_importances_
}).sort_values(by="Importance", ascending=False)

feature_importance_file = "Transformed_Hvap_RF_feature_importance.xlsx"

feature_importance_df.to_excel(
    feature_importance_file,
    index=False
)

print(f"已保存特征重要性为: {feature_importance_file}")


# ============================================================
# 19. 输出模型结构记录
# ============================================================

print("\n当前 Transformed Hvap RF 直接预测模型结构:")
print("Dataset: Transformed_hv_Dataset.xlsx")
print("Target: Heat of Vaporization")
print("Model: RandomForestRegressor(n_estimators=300, random_state=50, n_jobs=-1)")
print("Split: Material_ID if available; otherwise Pseudo_Material_ID by every 10 rows")
print("Input features: all numeric columns except target and material identifier")
print("Final all-data statistics use strict thresholds: <1%, <5%, <10%")