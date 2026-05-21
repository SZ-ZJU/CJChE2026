# import pandas as pd
# import numpy as np
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split
#
# # =========================
# # 1. 读取数据
# # =========================
# df = pd.read_excel("Transformed_density_Dataset.xlsx").copy()
#
# target_col = "Density"
# rows_per_material = 10
# random_state = 42
#
# # =========================
# # 2. 确定物质ID列
# #    若没有真实物质ID列，则默认每10行属于同一个物质
# # =========================
# candidate_id_cols = [
#     "Material_ID", "material_id", "Compound_ID", "compound_id",
#     "ID", "Smiles", "SMILES", "CAS", "Name"
# ]
#
# material_col = None
# for col in candidate_id_cols:
#     if col in df.columns:
#         material_col = col
#         break
#
# if material_col is None:
#     df = df.reset_index(drop=True).copy()
#     df["Pseudo_Material_ID"] = np.arange(len(df)) // rows_per_material
#     material_col = "Pseudo_Material_ID"
#
#     if len(df) % rows_per_material != 0:
#         print(f"⚠️ 总行数 {len(df)} 不是 {rows_per_material} 的整数倍，最后一个物质组可能不完整。")
#
#     print(f"⚠️ 未检测到真实物质ID列，当前按“每{rows_per_material}行一个物质”进行分组。")
# else:
#     print(f"✅ 检测到物质ID列：{material_col}")
#
# # =========================
# # 3. 清洗目标列
# # =========================
# df[target_col] = pd.to_numeric(df[target_col], errors="coerce")
# df = df.dropna(subset=[target_col]).copy()
#
# # =========================
# # 4. 按物质 8:2 划分
# # =========================
# unique_materials = df[material_col].dropna().unique()
#
# train_materials, test_materials = train_test_split(
#     unique_materials,
#     test_size=0.2,
#     random_state=random_state
# )
#
# train_df = df[df[material_col].isin(train_materials)].copy()
# test_df = df[df[material_col].isin(test_materials)].copy()
#
# print("\n========== 按物质划分 ==========")
# print(f"总物质数: {len(unique_materials)}")
# print(f"训练集物质数: {len(train_materials)}")
# print(f"测试集物质数: {len(test_materials)}")
# print(f"训练集样本点数: {len(train_df)}")
# print(f"测试集样本点数: {len(test_df)}")
#
# # =========================
# # 5. 构造特征和目标
# # =========================
# drop_cols = [target_col, material_col]
# X_train = train_df.drop(columns=drop_cols, errors="ignore").copy()
# X_test = test_df.drop(columns=drop_cols, errors="ignore").copy()
#
# y_train = train_df[target_col].astype(float).values
# y_test = test_df[target_col].astype(float).values
#
# # 只保留数值列
# numeric_cols = X_train.select_dtypes(include=[np.number]).columns.tolist()
# non_numeric_cols = [c for c in X_train.columns if c not in numeric_cols]
#
# if len(non_numeric_cols) > 0:
#     print(f"⚠️ 检测到非数值列，已删除: {non_numeric_cols}")
#
# X_train = X_train[numeric_cols].copy()
# X_test = X_test[numeric_cols].copy()
#
# # 处理 inf / nan
# X_train = X_train.replace([np.inf, -np.inf], np.nan)
# X_test = X_test.replace([np.inf, -np.inf], np.nan)
#
# train_mask = X_train.notna().all(axis=1) & np.isfinite(y_train)
# test_mask = X_test.notna().all(axis=1) & np.isfinite(y_test)
#
# X_train = X_train.loc[train_mask].copy()
# X_test = X_test.loc[test_mask].copy()
# y_train = y_train[train_mask]
# y_test = y_test[test_mask]
#
# train_df = train_df.loc[train_mask].copy()
# test_df = test_df.loc[test_mask].copy()
#
# print(f"\n清洗后训练集样本点数: {len(X_train)}")
# print(f"清洗后测试集样本点数: {len(X_test)}")
#
# # =========================
# # 6. 训练模型
# # =========================
# model = RandomForestRegressor(
#     n_estimators=100,
#     random_state=40,
#     n_jobs=-1
# )
# model.fit(X_train, y_train)
#
# # =========================
# # 7. 评估函数
# # =========================
# def evaluate_dataset(y_true, y_pred, name="数据集"):
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#
#     r2 = r2_score(y_true, y_pred)
#     mse = mean_squared_error(y_true, y_pred)
#
#     relative_error = np.full_like(y_true, np.nan, dtype=float)
#     nonzero_mask = np.abs(y_true) > 1e-12
#     relative_error[nonzero_mask] = np.abs(
#         (y_true[nonzero_mask] - y_pred[nonzero_mask]) / y_true[nonzero_mask]
#     ) * 100
#
#     ard = np.nanmean(relative_error)
#
#     error_1_percent = np.sum(relative_error < 1)
#     error_5_percent = np.sum(relative_error < 5)
#     error_10_percent = np.sum(relative_error < 10)
#
#     print(f"\n📊 {name} 模型评估结果：")
#     print(f"R²  = {r2:.4f}")
#     print(f"MSE = {mse:.8f}")
#     print(f"ARD = {ard:.2f}%")
#
#     print(f"\n📊 {name} 统计结果：")
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
# # =========================
# # 8. 训练集预测
# # =========================
# y_train_pred = model.predict(X_train)
# rel_err_train, train_summary = evaluate_dataset(y_train, y_train_pred, name="Train")
#
# # =========================
# # 9. 测试集预测
# # =========================
# y_test_pred = model.predict(X_test)
# rel_err_test, test_summary = evaluate_dataset(y_test, y_test_pred, name="Test")
#
# # =========================
# # 10. 保存结果
# # =========================
# train_result = train_df.copy()
# train_result["Predicted_Density"] = y_train_pred
# train_result["Absolute_Error"] = np.abs(y_train - y_train_pred)
# train_result["Relative_Error (%)"] = rel_err_train
# train_result["Set"] = "Train"
#
# test_result = test_df.copy()
# test_result["Predicted_Density"] = y_test_pred
# test_result["Absolute_Error"] = np.abs(y_test - y_test_pred)
# test_result["Relative_Error (%)"] = rel_err_test
# test_result["Set"] = "Test"
#
# summary_df = pd.DataFrame([train_summary, test_summary])
#
# output_file = "prediction_vs_actual_density_train_test_split_by_material.xlsx"
# with pd.ExcelWriter(output_file, engine="xlsxwriter") as writer:
#     train_result.to_excel(writer, sheet_name="Train_Predictions", index=False)
#     test_result.to_excel(writer, sheet_name="Test_Predictions", index=False)
#     summary_df.to_excel(writer, sheet_name="Summary", index=False)
#
# print(f"\n✅ 预测结果已保存为 {output_file}")



import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


# =========================
# 1. 读取数据
# =========================
df = pd.read_excel("Transformed_density_Dataset.xlsx").copy()

target_col = "Density"
rows_per_material = 10
random_state = 42


# =========================
# 2. 确定物质ID列
#    若没有真实物质ID列，则默认每10行属于同一个物质
# =========================
candidate_id_cols = [
    "Material_ID",
    "material_id",
    "Compound_ID",
    "compound_id",
    "ID",
    "Smiles",
    "SMILES",
    "CAS",
    "Name"
]

material_col = None

for col in candidate_id_cols:
    if col in df.columns:
        material_col = col
        break

if material_col is None:
    df = df.reset_index(drop=True).copy()
    df["Pseudo_Material_ID"] = np.arange(len(df)) // rows_per_material
    material_col = "Pseudo_Material_ID"

    if len(df) % rows_per_material != 0:
        print(f"警告：总行数 {len(df)} 不是 {rows_per_material} 的整数倍，最后一个物质组可能不完整。")

    print(f"未检测到真实物质ID列，当前按每 {rows_per_material} 行一个物质进行分组。")
else:
    print(f"检测到物质ID列：{material_col}")


# =========================
# 3. 清洗目标列
# =========================
df[target_col] = pd.to_numeric(
    df[target_col],
    errors="coerce"
)

df = df.dropna(subset=[target_col]).copy()


# =========================
# 4. 按物质 8:2 划分
# =========================
unique_materials = df[material_col].dropna().unique()

train_materials, test_materials = train_test_split(
    unique_materials,
    test_size=0.2,
    random_state=random_state
)

train_materials = set(train_materials)
test_materials = set(test_materials)

train_df = df[df[material_col].isin(train_materials)].copy()
test_df = df[df[material_col].isin(test_materials)].copy()

print("\n========== 按物质划分 ==========")
print(f"总物质数: {len(unique_materials)}")
print(f"训练集物质数: {len(train_materials)}")
print(f"测试集物质数: {len(test_materials)}")
print(f"训练集样本点数: {len(train_df)}")
print(f"测试集样本点数: {len(test_df)}")


# =========================
# 5. 构造特征和目标
# =========================
drop_cols = [
    target_col,
    material_col
]

X_train = train_df.drop(
    columns=drop_cols,
    errors="ignore"
).copy()

X_test = test_df.drop(
    columns=drop_cols,
    errors="ignore"
).copy()

y_train = train_df[target_col].astype(float).values
y_test = test_df[target_col].astype(float).values


# 只保留数值列
numeric_cols = X_train.select_dtypes(
    include=[np.number]
).columns.tolist()

non_numeric_cols = [
    c for c in X_train.columns
    if c not in numeric_cols
]

if len(non_numeric_cols) > 0:
    print(f"检测到非数值列，已删除: {non_numeric_cols}")

X_train = X_train[numeric_cols].copy()
X_test = X_test[numeric_cols].copy()


# 处理 inf / nan
X_train = X_train.replace(
    [np.inf, -np.inf],
    np.nan
)

X_test = X_test.replace(
    [np.inf, -np.inf],
    np.nan
)

train_mask = (
    X_train.notna().all(axis=1)
    & np.isfinite(y_train)
)

test_mask = (
    X_test.notna().all(axis=1)
    & np.isfinite(y_test)
)

X_train = X_train.loc[train_mask].copy()
X_test = X_test.loc[test_mask].copy()

y_train = y_train[train_mask]
y_test = y_test[test_mask]

train_df = train_df.loc[train_mask].copy()
test_df = test_df.loc[test_mask].copy()

print("\n========== 清洗后建模数据 ==========")
print(f"清洗后训练集样本点数: {len(X_train)}")
print(f"清洗后测试集样本点数: {len(X_test)}")
print(f"最终模型特征数: {X_train.shape[1]}")


# =========================
# 6. 训练模型
# =========================
model = RandomForestRegressor(
    n_estimators=100,
    random_state=40,
    n_jobs=-1
)

print("\n开始训练 RF 模型...")
model.fit(X_train, y_train)

print("\nRF 模型参数:")
print(model)


# =========================
# 7. 评估函数
# =========================
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
        print(f"\n{name} 模型评估结果：无有效样本")

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
        count_1 = np.sum(relative_error_valid < 1)
        count_5 = np.sum(relative_error_valid < 5)
        count_10 = np.sum(relative_error_valid < 10)
    else:
        count_1 = np.sum(relative_error_valid <= 1)
        count_5 = np.sum(relative_error_valid <= 5)
        count_10 = np.sum(relative_error_valid <= 10)

    print(f"\n{name} 模型评估结果：")
    print(f"R2  = {r2:.4f}")
    print(f"MSE = {mse:.8f}")
    print(f"ARD = {ard:.2f}%")

    print(f"\n{name} 统计结果：")

    if strict_less:
        print(f"数据点相对误差小于 1%: {count_1} 个")
        print(f"数据点相对误差小于 5%: {count_5} 个")
        print(f"数据点相对误差小于 10%: {count_10} 个")
    else:
        print(f"数据点相对误差小于等于 1%: {count_1} 个")
        print(f"数据点相对误差小于等于 5%: {count_5} 个")
        print(f"数据点相对误差小于等于 10%: {count_10} 个")

    summary = {
        "Dataset": name,
        "R2": r2,
        "MSE": mse,
        "ARD_%": ard,
        "Count_<1%": count_1,
        "Count_<5%": count_5,
        "Count_<10%": count_10
    }

    return relative_error, summary


# =========================
# 8. 训练集预测
# =========================
y_train_pred = model.predict(X_train)

rel_err_train, train_summary = evaluate_dataset(
    y_train,
    y_train_pred,
    name="Train",
    strict_less=True
)


# =========================
# 9. 测试集预测
# =========================
y_test_pred = model.predict(X_test)

rel_err_test, test_summary = evaluate_dataset(
    y_test,
    y_test_pred,
    name="Test",
    strict_less=True
)


# =========================
# 9.1 完整数据集统计：训练集 + 测试集
# =========================
y_all_true = np.concatenate([
    y_train,
    y_test
])

y_all_pred = np.concatenate([
    y_train_pred,
    y_test_pred
])

rel_err_all, all_summary = evaluate_dataset(
    y_all_true,
    y_all_pred,
    name="All_train_plus_test",
    strict_less=True
)

print("\nTransformed Density RF 完整数据集预测偏差 1%，5%，10%分别为：")
print(all_summary["Count_<1%"])
print(all_summary["Count_<5%"])
print(all_summary["Count_<10%"])


# =========================
# 10. 保存结果
# =========================
train_result = train_df.copy()
train_result["Predicted_Density"] = y_train_pred
train_result["Absolute_Error"] = np.abs(
    y_train - y_train_pred
)
train_result["Relative_Error (%)"] = rel_err_train
train_result["Set"] = "Train"

test_result = test_df.copy()
test_result["Predicted_Density"] = y_test_pred
test_result["Absolute_Error"] = np.abs(
    y_test - y_test_pred
)
test_result["Relative_Error (%)"] = rel_err_test
test_result["Set"] = "Test"

all_result = pd.concat(
    [train_result, test_result],
    axis=0,
    ignore_index=True
)

all_result["Set"] = "All_train_plus_test"
all_result["Predicted_Density"] = y_all_pred
all_result["Absolute_Error"] = np.abs(
    y_all_true - y_all_pred
)
all_result["Relative_Error (%)"] = rel_err_all


# =========================
# 11. 保存汇总
# =========================
summary_df = pd.DataFrame([
    train_summary,
    test_summary,
    all_summary
])


# =========================
# 12. 保存 Excel
# =========================
output_file = "prediction_vs_actual_density_train_test_split_by_material.xlsx"

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

print(f"\n预测结果已保存为 {output_file}")


# =========================
# 13. 保存特征重要性
# =========================
feature_importance_df = pd.DataFrame({
    "Feature": X_train.columns,
    "Importance": model.feature_importances_
}).sort_values(
    by="Importance",
    ascending=False
)

feature_importance_file = "Transformed_Density_RF_feature_importance.xlsx"

feature_importance_df.to_excel(
    feature_importance_file,
    index=False
)

print(f"特征重要性已保存为: {feature_importance_file}")


# =========================
# 14. 输出模型结构记录
# =========================
print("\n当前 Transformed Density RF 直接预测模型结构:")
print("Dataset: Transformed_density_Dataset.xlsx")
print("Target: Density")
print("Model: RandomForestRegressor(n_estimators=100, random_state=40, n_jobs=-1)")
print("Split: detected material ID column if available; otherwise Pseudo_Material_ID by every 10 rows")
print("Input features: all numeric columns except target and material identifier")
print("Final all-data statistics use strict thresholds: <1%, <5%, <10%")