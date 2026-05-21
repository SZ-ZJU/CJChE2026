# import pandas as pd
# import numpy as np
#
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split
#
#
# # ============================================================
# # 0. 统一 RF 参数
# #    与第一个 RF 代码保持一致
# # ============================================================
#
# RF_PARAMS = dict(
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
# def make_rf_model():
#     return RandomForestRegressor(**RF_PARAMS)
#
#
# # ============================================================
# # 1. 读取数据
# # ============================================================
#
# file_path = "heat capacity 207.xlsx"
# df = pd.read_excel(file_path, sheet_name="Sheet1")
#
# df = df.dropna(subset=[df.columns[0]]).copy()
# df[df.columns[0]] = df[df.columns[0]].astype(int)
#
#
# # ============================================================
# # 2. 列定义
# # ============================================================
#
# material_id_col = df.columns[0]
#
# group_cols = df.columns[11:30]   # 19 个基团列
# temp_cols = df.columns[30:40]    # 10 个温度点
# cp_cols = df.columns[40:50]      # 10 个 Cp 点
#
# target_column_T1 = "ASPEN Half Critical T"
#
# cp1_col = df.columns[9]
# cp2_col = df.columns[50]
#
#
# # ============================================================
# # 3. 通用评估函数
# # ============================================================
#
# def safe_reg_metrics(y_true, y_pred, name="模型"):
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#
#     mse = mean_squared_error(y_true, y_pred)
#     r2 = r2_score(y_true, y_pred)
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
#     print(f"\n{name}")
#     print(f"R²  = {r2:.6f}")
#     print(f"MSE = {mse:.6f}")
#     print(f"ARD = {ard:.2f}%")
#     print(f"误差 ≤ 1% 的点数: {within_1pct}")
#     print(f"误差 ≤ 5% 的点数: {within_5pct}")
#     print(f"误差 ≤ 10% 的点数: {within_10pct}")
#
#     return {
#         "R2": r2,
#         "MSE": mse,
#         "ARD_%": ard,
#         "within_1pct": within_1pct,
#         "within_5pct": within_5pct,
#         "within_10pct": within_10pct,
#         "relative_error_%": relative_error
#     }
#
#
# # ============================================================
# # 4. 训练 T1 子模型
# #    注意：子模型不划分训练集/测试集，使用全部物质训练
# # ============================================================
#
# T1_df = df.dropna(subset=[target_column_T1]).copy()
#
# X_T1 = T1_df[group_cols].astype(float).values
# y_T1 = T1_df[target_column_T1].astype(float).values
#
# T1_model = make_rf_model()
# T1_model.fit(X_T1, y_T1)
#
# y_T1_pred = T1_model.predict(X_T1)
#
# metrics_T1_all = safe_reg_metrics(
#     y_T1,
#     y_T1_pred,
#     "T1_model RF 全数据"
# )
#
# t1_results = pd.DataFrame({
#     "Material_ID": T1_df[material_id_col].values,
#     "T1_true": y_T1,
#     "T1_pred": y_T1_pred,
#     "Relative_Error_%": metrics_T1_all["relative_error_%"]
# })
#
# t1_results.to_excel("RF_T1_model_全数据预测结果.xlsx", index=False)
#
#
# # ============================================================
# # 5. 训练 Cp1 子模型
# #    注意：子模型不划分训练集/测试集，使用全部物质训练
# # ============================================================
#
# Cp1_df = df.dropna(subset=[cp1_col]).copy()
#
# X_Cp1 = Cp1_df[group_cols].astype(float).values
# y_Cp1 = Cp1_df[cp1_col].astype(float).values
#
# Cp1_model = make_rf_model()
# Cp1_model.fit(X_Cp1, y_Cp1)
#
# y_Cp1_pred = Cp1_model.predict(X_Cp1)
#
# metrics_Cp1_all = safe_reg_metrics(
#     y_Cp1,
#     y_Cp1_pred,
#     "Cp1_model RF 全数据"
# )
#
# cp1_results = pd.DataFrame({
#     "Material_ID": Cp1_df[material_id_col].values,
#     "Cp1_true": y_Cp1,
#     "Cp1_pred": y_Cp1_pred,
#     "Relative_Error_%": metrics_Cp1_all["relative_error_%"]
# })
#
# cp1_results.to_excel("RF_Cp1_model_全数据预测结果.xlsx", index=False)
#
#
# # ============================================================
# # 6. 训练 Cp2 子模型
# #    注意：子模型不划分训练集/测试集，使用全部物质训练
# # ============================================================
#
# Cp2_df = df.dropna(subset=[cp2_col]).copy()
#
# X_Cp2 = Cp2_df[group_cols].astype(float).values
# y_Cp2 = Cp2_df[cp2_col].astype(float).values
#
# Cp2_model = make_rf_model()
# Cp2_model.fit(X_Cp2, y_Cp2)
#
# y_Cp2_pred = Cp2_model.predict(X_Cp2)
#
# metrics_Cp2_all = safe_reg_metrics(
#     y_Cp2,
#     y_Cp2_pred,
#     "Cp2_model RF 全数据"
# )
#
# cp2_results = pd.DataFrame({
#     "Material_ID": Cp2_df[material_id_col].values,
#     "Cp2_true": y_Cp2,
#     "Cp2_pred": y_Cp2_pred,
#     "Relative_Error_%": metrics_Cp2_all["relative_error_%"]
# })
#
# cp2_results.to_excel("RF_Cp2_model_全数据预测结果.xlsx", index=False)
#
#
# # ============================================================
# # 7. 最终模型按物质划分 8:2
# #    只有最终 Cp(T) 模型划分训练集 / 测试集
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
# print("\n========== 最终模型按物质划分 ==========")
# print(f"总物质数: {len(unique_materials)}")
# print(f"训练集物质数: {len(train_materials)}")
# print(f"测试集物质数: {len(test_materials)}")
#
#
# # ============================================================
# # 8. 构建最终 Cp(T) 模型训练集 / 测试集
# # ============================================================
#
# X_train, y_train, mat_train, temp_train = [], [], [], []
# X_test, y_test, mat_test, temp_test = [], [], [], []
#
# slope_train, T1_train_used, T2_train_used, Cp1_train_used, Cp2_train_used = [], [], [], [], []
# slope_test, T1_test_used, T2_test_used, Cp1_test_used, Cp2_test_used = [], [], [], [], []
#
# for _, row in df.iterrows():
#     material_id = row[material_id_col]
#
#     Nk = row[group_cols].astype(float).values
#     temps = row[temp_cols].astype(float).values
#     cps = row[cp_cols].astype(float).values
#
#     Nk_2d = Nk.reshape(1, -1)
#
#     try:
#         T1_pred = T1_model.predict(Nk_2d)[0]
#
#         if np.isnan(T1_pred) or T1_pred <= 0:
#             continue
#
#         T2_pred = T1_pred * 1.5
#
#         if np.isnan(T2_pred) or np.isclose(T2_pred, T1_pred):
#             continue
#
#         Cp1_pred = Cp1_model.predict(Nk_2d)[0]
#         Cp2_pred = Cp2_model.predict(Nk_2d)[0]
#
#         slope = (Cp2_pred - Cp1_pred) / (T2_pred - T1_pred)
#
#         if np.isnan(slope) or np.isinf(slope):
#             continue
#
#     except Exception:
#         continue
#
#     for T, Cp in zip(temps, cps):
#         if np.isnan(T) or np.isnan(Cp):
#             continue
#
#         features = np.concatenate([
#             Nk,
#             Nk * T,
#             [slope * T]
#         ])
#
#         if material_id in train_materials:
#             X_train.append(features)
#             y_train.append(Cp)
#             mat_train.append(material_id)
#             temp_train.append(T)
#
#             slope_train.append(slope)
#             T1_train_used.append(T1_pred)
#             T2_train_used.append(T2_pred)
#             Cp1_train_used.append(Cp1_pred)
#             Cp2_train_used.append(Cp2_pred)
#
#         elif material_id in test_materials:
#             X_test.append(features)
#             y_test.append(Cp)
#             mat_test.append(material_id)
#             temp_test.append(T)
#
#             slope_test.append(slope)
#             T1_test_used.append(T1_pred)
#             T2_test_used.append(T2_pred)
#             Cp1_test_used.append(Cp1_pred)
#             Cp2_test_used.append(Cp2_pred)
#
#
# X_train = np.array(X_train, dtype=float)
# y_train = np.array(y_train, dtype=float)
# mat_train = np.array(mat_train)
# temp_train = np.array(temp_train, dtype=float)
#
# X_test = np.array(X_test, dtype=float)
# y_test = np.array(y_test, dtype=float)
# mat_test = np.array(mat_test)
# temp_test = np.array(temp_test, dtype=float)
#
# slope_train = np.array(slope_train, dtype=float)
# T1_train_used = np.array(T1_train_used, dtype=float)
# T2_train_used = np.array(T2_train_used, dtype=float)
# Cp1_train_used = np.array(Cp1_train_used, dtype=float)
# Cp2_train_used = np.array(Cp2_train_used, dtype=float)
#
# slope_test = np.array(slope_test, dtype=float)
# T1_test_used = np.array(T1_test_used, dtype=float)
# T2_test_used = np.array(T2_test_used, dtype=float)
# Cp1_test_used = np.array(Cp1_test_used, dtype=float)
# Cp2_test_used = np.array(Cp2_test_used, dtype=float)
#
# print("\n========== 最终 Cp(T) 模型数据集 ==========")
# print(f"训练集样本点数: {len(X_train)}")
# print(f"测试集样本点数: {len(X_test)}")
#
#
# # ============================================================
# # 9. 训练最终 RF Cp(T) 模型
# # ============================================================
#
# final_model = make_rf_model()
# final_model.fit(X_train, y_train)
#
# y_train_pred = final_model.predict(X_train)
# y_test_pred = final_model.predict(X_test)
#
# metrics_final_train = safe_reg_metrics(
#     y_train,
#     y_train_pred,
#     "最终 Cp(T) RF 模型 训练集"
# )
#
# metrics_final_test = safe_reg_metrics(
#     y_test,
#     y_test_pred,
#     "最终 Cp(T) RF 模型 测试集"
# )
#
#
# # ============================================================
# # 10. 保存最终模型训练集预测结果
# # ============================================================
#
# train_results = pd.DataFrame({
#     "Material_ID": mat_train,
#     "Temperature (K)": temp_train,
#     "Cp_measured": y_train,
#     "Cp_predicted": y_train_pred,
#     "Relative_Error_%": metrics_final_train["relative_error_%"],
#     "Pred_T1": T1_train_used,
#     "Pred_T2": T2_train_used,
#     "Pred_Cp1": Cp1_train_used,
#     "Pred_Cp2": Cp2_train_used,
#     "Slope": slope_train
# })
#
# train_results.to_excel(
#     "RF_最终Cp模型_子模型全数据_slopeT特征_训练集预测结果.xlsx",
#     index=False
# )
#
#
# # ============================================================
# # 11. 保存最终模型测试集预测结果
# # ============================================================
#
# test_results = pd.DataFrame({
#     "Material_ID": mat_test,
#     "Temperature (K)": temp_test,
#     "Cp_measured": y_test,
#     "Cp_predicted": y_test_pred,
#     "Relative_Error_%": metrics_final_test["relative_error_%"],
#     "Pred_T1": T1_test_used,
#     "Pred_T2": T2_test_used,
#     "Pred_Cp1": Cp1_test_used,
#     "Pred_Cp2": Cp2_test_used,
#     "Slope": slope_test
# })
#
# test_results.to_excel(
#     "RF_最终Cp模型_子模型全数据_slopeT特征_测试集预测结果.xlsx",
#     index=False
# )
#
#
# # ============================================================
# # 12. 保存评估汇总
# # ============================================================
#
# summary_rows = [
#     [
#         "T1_model_RF",
#         "all_data",
#         metrics_T1_all["R2"],
#         metrics_T1_all["MSE"],
#         metrics_T1_all["ARD_%"],
#         metrics_T1_all["within_1pct"],
#         metrics_T1_all["within_5pct"],
#         metrics_T1_all["within_10pct"]
#     ],
#     [
#         "Cp1_model_RF",
#         "all_data",
#         metrics_Cp1_all["R2"],
#         metrics_Cp1_all["MSE"],
#         metrics_Cp1_all["ARD_%"],
#         metrics_Cp1_all["within_1pct"],
#         metrics_Cp1_all["within_5pct"],
#         metrics_Cp1_all["within_10pct"]
#     ],
#     [
#         "Cp2_model_RF",
#         "all_data",
#         metrics_Cp2_all["R2"],
#         metrics_Cp2_all["MSE"],
#         metrics_Cp2_all["ARD_%"],
#         metrics_Cp2_all["within_1pct"],
#         metrics_Cp2_all["within_5pct"],
#         metrics_Cp2_all["within_10pct"]
#     ],
#     [
#         "Final_Cp_T_model_RF_slopeT",
#         "train",
#         metrics_final_train["R2"],
#         metrics_final_train["MSE"],
#         metrics_final_train["ARD_%"],
#         metrics_final_train["within_1pct"],
#         metrics_final_train["within_5pct"],
#         metrics_final_train["within_10pct"]
#     ],
#     [
#         "Final_Cp_T_model_RF_slopeT",
#         "test",
#         metrics_final_test["R2"],
#         metrics_final_test["MSE"],
#         metrics_final_test["ARD_%"],
#         metrics_final_test["within_1pct"],
#         metrics_final_test["within_5pct"],
#         metrics_final_test["within_10pct"]
#     ]
# ]
#
# summary_df = pd.DataFrame(
#     summary_rows,
#     columns=[
#         "Model",
#         "Dataset",
#         "R2",
#         "MSE",
#         "ARD_%",
#         "within_1pct",
#         "within_5pct",
#         "within_10pct"
#     ]
# )
#
# summary_df.to_excel(
#     "RF_子模型全数据_最终模型划分_评估汇总.xlsx",
#     index=False
# )
#
#
# # ============================================================
# # 13. 保存最终 RF 模型特征重要性
# # ============================================================
#
# feature_labels = (
#     list(group_cols) +
#     [f"{g}_T" for g in group_cols] +
#     ["slope×T"]
# )
#
# feature_importance_df = pd.DataFrame({
#     "Feature": feature_labels,
#     "Importance": final_model.feature_importances_
# }).sort_values(by="Importance", ascending=False)
#
# feature_importance_df.to_excel(
#     "RF_最终Cp模型_子模型全数据_slopeT特征_特征重要性.xlsx",
#     index=False
# )
#
#
# # ============================================================
# # 14. 打印保存信息
# # ============================================================
#
# print("\n已保存:")
# print("1. RF_T1_model_全数据预测结果.xlsx")
# print("2. RF_Cp1_model_全数据预测结果.xlsx")
# print("3. RF_Cp2_model_全数据预测结果.xlsx")
# print("4. RF_最终Cp模型_子模型全数据_slopeT特征_训练集预测结果.xlsx")
# print("5. RF_最终Cp模型_子模型全数据_slopeT特征_测试集预测结果.xlsx")
# print("6. RF_子模型全数据_最终模型划分_评估汇总.xlsx")
# print("7. RF_最终Cp模型_子模型全数据_slopeT特征_特征重要性.xlsx")

import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


# ============================================================
# 0. 统一 RF 参数
#    与第一个 RF 代码保持一致
# ============================================================

RF_PARAMS = dict(
    n_estimators=500,
    max_depth=None,
    min_samples_split=2,
    min_samples_leaf=1,
    max_features="sqrt",
    bootstrap=True,
    random_state=42,
    n_jobs=-1
)


def make_rf_model():
    return RandomForestRegressor(**RF_PARAMS)


# ============================================================
# 1. 读取数据
# ============================================================

file_path = "heat capacity 207.xlsx"
df = pd.read_excel(file_path, sheet_name="Sheet1")

df = df.dropna(subset=[df.columns[0]]).copy()
df[df.columns[0]] = df[df.columns[0]].astype(int)


# ============================================================
# 2. 列定义
# ============================================================

material_id_col = df.columns[0]

group_cols = df.columns[11:30]   # 19 个基团列
temp_cols = df.columns[30:40]    # 10 个温度点
cp_cols = df.columns[40:50]      # 10 个 Cp 点

target_column_T1 = "ASPEN Half Critical T"

cp1_col = df.columns[9]
cp2_col = df.columns[50]


# ============================================================
# 3. 通用评估函数
# ============================================================

def safe_reg_metrics(y_true, y_pred, name="模型"):
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

    within_1pct = np.sum(relative_error <= 1)
    within_5pct = np.sum(relative_error <= 5)
    within_10pct = np.sum(relative_error <= 10)

    print(f"\n{name}")
    print(f"R²  = {r2:.6f}")
    print(f"MSE = {mse:.6f}")
    print(f"ARD = {ard:.2f}%")
    print(f"误差 ≤ 1% 的点数: {within_1pct}")
    print(f"误差 ≤ 5% 的点数: {within_5pct}")
    print(f"误差 ≤ 10% 的点数: {within_10pct}")

    return {
        "R2": r2,
        "MSE": mse,
        "ARD_%": ard,
        "within_1pct": within_1pct,
        "within_5pct": within_5pct,
        "within_10pct": within_10pct,
        "relative_error_%": relative_error
    }


# ============================================================
# 4. 训练 T1 子模型
#    注意：子模型不划分训练集/测试集，使用全部物质训练
# ============================================================

T1_df = df.dropna(subset=[target_column_T1]).copy()

X_T1 = T1_df[group_cols].astype(float).values
y_T1 = T1_df[target_column_T1].astype(float).values

T1_model = make_rf_model()
T1_model.fit(X_T1, y_T1)

y_T1_pred = T1_model.predict(X_T1)

metrics_T1_all = safe_reg_metrics(
    y_T1,
    y_T1_pred,
    "T1_model RF 全数据"
)

t1_results = pd.DataFrame({
    "Material_ID": T1_df[material_id_col].values,
    "T1_true": y_T1,
    "T1_pred": y_T1_pred,
    "Relative_Error_%": metrics_T1_all["relative_error_%"]
})

t1_results.to_excel("RF_T1_model_全数据预测结果.xlsx", index=False)


# ============================================================
# 5. 训练 Cp1 子模型
#    注意：子模型不划分训练集/测试集，使用全部物质训练
# ============================================================

Cp1_df = df.dropna(subset=[cp1_col]).copy()

X_Cp1 = Cp1_df[group_cols].astype(float).values
y_Cp1 = Cp1_df[cp1_col].astype(float).values

Cp1_model = make_rf_model()
Cp1_model.fit(X_Cp1, y_Cp1)

y_Cp1_pred = Cp1_model.predict(X_Cp1)

metrics_Cp1_all = safe_reg_metrics(
    y_Cp1,
    y_Cp1_pred,
    "Cp1_model RF 全数据"
)

cp1_results = pd.DataFrame({
    "Material_ID": Cp1_df[material_id_col].values,
    "Cp1_true": y_Cp1,
    "Cp1_pred": y_Cp1_pred,
    "Relative_Error_%": metrics_Cp1_all["relative_error_%"]
})

cp1_results.to_excel("RF_Cp1_model_全数据预测结果.xlsx", index=False)


# ============================================================
# 6. 训练 Cp2 子模型
#    注意：子模型不划分训练集/测试集，使用全部物质训练
# ============================================================

Cp2_df = df.dropna(subset=[cp2_col]).copy()

X_Cp2 = Cp2_df[group_cols].astype(float).values
y_Cp2 = Cp2_df[cp2_col].astype(float).values

Cp2_model = make_rf_model()
Cp2_model.fit(X_Cp2, y_Cp2)

y_Cp2_pred = Cp2_model.predict(X_Cp2)

metrics_Cp2_all = safe_reg_metrics(
    y_Cp2,
    y_Cp2_pred,
    "Cp2_model RF 全数据"
)

cp2_results = pd.DataFrame({
    "Material_ID": Cp2_df[material_id_col].values,
    "Cp2_true": y_Cp2,
    "Cp2_pred": y_Cp2_pred,
    "Relative_Error_%": metrics_Cp2_all["relative_error_%"]
})

cp2_results.to_excel("RF_Cp2_model_全数据预测结果.xlsx", index=False)


# ============================================================
# 7. 最终模型按物质划分 8:2
#    只有最终 Cp(T) 模型划分训练集 / 测试集
# ============================================================

unique_materials = df[material_id_col].dropna().unique()

train_materials, test_materials = train_test_split(
    unique_materials,
    test_size=0.2,
    random_state=42
)

train_materials = set(train_materials)
test_materials = set(test_materials)

print("\n========== 最终模型按物质划分 ==========")
print(f"总物质数: {len(unique_materials)}")
print(f"训练集物质数: {len(train_materials)}")
print(f"测试集物质数: {len(test_materials)}")


# ============================================================
# 8. 构建最终 Cp(T) 模型训练集 / 测试集
# ============================================================

X_train, y_train, mat_train, temp_train = [], [], [], []
X_test, y_test, mat_test, temp_test = [], [], [], []

slope_train, T1_train_used, T2_train_used, Cp1_train_used, Cp2_train_used = [], [], [], [], []
slope_test, T1_test_used, T2_test_used, Cp1_test_used, Cp2_test_used = [], [], [], [], []

for _, row in df.iterrows():
    material_id = row[material_id_col]

    Nk = row[group_cols].astype(float).values
    temps = row[temp_cols].astype(float).values
    cps = row[cp_cols].astype(float).values

    Nk_2d = Nk.reshape(1, -1)

    try:
        T1_pred = T1_model.predict(Nk_2d)[0]

        if np.isnan(T1_pred) or T1_pred <= 0:
            continue

        T2_pred = T1_pred * 1.5

        if np.isnan(T2_pred) or np.isclose(T2_pred, T1_pred):
            continue

        Cp1_pred = Cp1_model.predict(Nk_2d)[0]
        Cp2_pred = Cp2_model.predict(Nk_2d)[0]

        slope = (Cp2_pred - Cp1_pred) / (T2_pred - T1_pred)

        if np.isnan(slope) or np.isinf(slope):
            continue

    except Exception:
        continue

    for T, Cp in zip(temps, cps):
        if np.isnan(T) or np.isnan(Cp):
            continue

        features = np.concatenate([
            Nk,
            Nk * T,
            [slope * T]
        ])

        if material_id in train_materials:
            X_train.append(features)
            y_train.append(Cp)
            mat_train.append(material_id)
            temp_train.append(T)

            slope_train.append(slope)
            T1_train_used.append(T1_pred)
            T2_train_used.append(T2_pred)
            Cp1_train_used.append(Cp1_pred)
            Cp2_train_used.append(Cp2_pred)

        elif material_id in test_materials:
            X_test.append(features)
            y_test.append(Cp)
            mat_test.append(material_id)
            temp_test.append(T)

            slope_test.append(slope)
            T1_test_used.append(T1_pred)
            T2_test_used.append(T2_pred)
            Cp1_test_used.append(Cp1_pred)
            Cp2_test_used.append(Cp2_pred)


X_train = np.array(X_train, dtype=float)
y_train = np.array(y_train, dtype=float)
mat_train = np.array(mat_train)
temp_train = np.array(temp_train, dtype=float)

X_test = np.array(X_test, dtype=float)
y_test = np.array(y_test, dtype=float)
mat_test = np.array(mat_test)
temp_test = np.array(temp_test, dtype=float)

slope_train = np.array(slope_train, dtype=float)
T1_train_used = np.array(T1_train_used, dtype=float)
T2_train_used = np.array(T2_train_used, dtype=float)
Cp1_train_used = np.array(Cp1_train_used, dtype=float)
Cp2_train_used = np.array(Cp2_train_used, dtype=float)

slope_test = np.array(slope_test, dtype=float)
T1_test_used = np.array(T1_test_used, dtype=float)
T2_test_used = np.array(T2_test_used, dtype=float)
Cp1_test_used = np.array(Cp1_test_used, dtype=float)
Cp2_test_used = np.array(Cp2_test_used, dtype=float)

print("\n========== 最终 Cp(T) 模型数据集 ==========")
print(f"训练集样本点数: {len(X_train)}")
print(f"测试集样本点数: {len(X_test)}")


# ============================================================
# 9. 训练最终 RF Cp(T) 模型
# ============================================================

final_model = make_rf_model()
final_model.fit(X_train, y_train)

y_train_pred = final_model.predict(X_train)
y_test_pred = final_model.predict(X_test)

metrics_final_train = safe_reg_metrics(
    y_train,
    y_train_pred,
    "最终 Cp(T) RF 模型 训练集"
)

metrics_final_test = safe_reg_metrics(
    y_test,
    y_test_pred,
    "最终 Cp(T) RF 模型 测试集"
)


# ============================================================
# 9.1 统计最终模型完整数据集预测偏差：训练集 + 测试集
# ============================================================

y_all_true = np.concatenate([y_train, y_test])
y_all_pred = np.concatenate([y_train_pred, y_test_pred])
mat_all = np.concatenate([mat_train, mat_test])
temp_all = np.concatenate([temp_train, temp_test])

slope_all = np.concatenate([slope_train, slope_test])
T1_all_used = np.concatenate([T1_train_used, T1_test_used])
T2_all_used = np.concatenate([T2_train_used, T2_test_used])
Cp1_all_used = np.concatenate([Cp1_train_used, Cp1_test_used])
Cp2_all_used = np.concatenate([Cp2_train_used, Cp2_test_used])

nonzero_mask_all = np.abs(y_all_true) > 1e-12
relative_error_all = np.full_like(y_all_true, np.nan, dtype=float)

relative_error_all[nonzero_mask_all] = np.abs(
    (y_all_pred[nonzero_mask_all] - y_all_true[nonzero_mask_all])
    / y_all_true[nonzero_mask_all]
) * 100

all_r2 = r2_score(y_all_true, y_all_pred)
all_mse = mean_squared_error(y_all_true, y_all_pred)
all_ard = np.nanmean(relative_error_all)

all_within_1pct = np.sum(relative_error_all < 1)
all_within_5pct = np.sum(relative_error_all < 5)
all_within_10pct = np.sum(relative_error_all < 10)

print("\n最终 Cp(T) RF 模型 完整数据集：训练集 + 测试集")
print(f"R²  = {all_r2:.6f}")
print(f"MSE = {all_mse:.6f}")
print(f"ARD = {all_ard:.2f}%")

print("1%，5%，10%分别为：")
print(all_within_1pct)
print(all_within_5pct)
print(all_within_10pct)


# ============================================================
# 10. 保存最终模型训练集预测结果
# ============================================================

train_results = pd.DataFrame({
    "Material_ID": mat_train,
    "Temperature (K)": temp_train,
    "Cp_measured": y_train,
    "Cp_predicted": y_train_pred,
    "Relative_Error_%": metrics_final_train["relative_error_%"],
    "Pred_T1": T1_train_used,
    "Pred_T2": T2_train_used,
    "Pred_Cp1": Cp1_train_used,
    "Pred_Cp2": Cp2_train_used,
    "Slope": slope_train
})

train_results.to_excel(
    "RF_最终Cp模型_子模型全数据_slopeT特征_训练集预测结果.xlsx",
    index=False
)


# ============================================================
# 11. 保存最终模型测试集预测结果
# ============================================================

test_results = pd.DataFrame({
    "Material_ID": mat_test,
    "Temperature (K)": temp_test,
    "Cp_measured": y_test,
    "Cp_predicted": y_test_pred,
    "Relative_Error_%": metrics_final_test["relative_error_%"],
    "Pred_T1": T1_test_used,
    "Pred_T2": T2_test_used,
    "Pred_Cp1": Cp1_test_used,
    "Pred_Cp2": Cp2_test_used,
    "Slope": slope_test
})

test_results.to_excel(
    "RF_最终Cp模型_子模型全数据_slopeT特征_测试集预测结果.xlsx",
    index=False
)


# ============================================================
# 11.1 保存最终模型完整数据集预测结果
# ============================================================

all_results = pd.DataFrame({
    "Material_ID": mat_all,
    "Temperature (K)": temp_all,
    "Cp_measured": y_all_true,
    "Cp_predicted": y_all_pred,
    "Relative_Error_%": relative_error_all,
    "Pred_T1": T1_all_used,
    "Pred_T2": T2_all_used,
    "Pred_Cp1": Cp1_all_used,
    "Pred_Cp2": Cp2_all_used,
    "Slope": slope_all
})

all_results.to_excel(
    "RF_最终Cp模型_子模型全数据_slopeT特征_完整数据集预测结果.xlsx",
    index=False
)


# ============================================================
# 12. 保存评估汇总
# ============================================================

summary_rows = [
    [
        "T1_model_RF",
        "all_data",
        metrics_T1_all["R2"],
        metrics_T1_all["MSE"],
        metrics_T1_all["ARD_%"],
        metrics_T1_all["within_1pct"],
        metrics_T1_all["within_5pct"],
        metrics_T1_all["within_10pct"]
    ],
    [
        "Cp1_model_RF",
        "all_data",
        metrics_Cp1_all["R2"],
        metrics_Cp1_all["MSE"],
        metrics_Cp1_all["ARD_%"],
        metrics_Cp1_all["within_1pct"],
        metrics_Cp1_all["within_5pct"],
        metrics_Cp1_all["within_10pct"]
    ],
    [
        "Cp2_model_RF",
        "all_data",
        metrics_Cp2_all["R2"],
        metrics_Cp2_all["MSE"],
        metrics_Cp2_all["ARD_%"],
        metrics_Cp2_all["within_1pct"],
        metrics_Cp2_all["within_5pct"],
        metrics_Cp2_all["within_10pct"]
    ],
    [
        "Final_Cp_T_model_RF_slopeT",
        "train",
        metrics_final_train["R2"],
        metrics_final_train["MSE"],
        metrics_final_train["ARD_%"],
        metrics_final_train["within_1pct"],
        metrics_final_train["within_5pct"],
        metrics_final_train["within_10pct"]
    ],
    [
        "Final_Cp_T_model_RF_slopeT",
        "test",
        metrics_final_test["R2"],
        metrics_final_test["MSE"],
        metrics_final_test["ARD_%"],
        metrics_final_test["within_1pct"],
        metrics_final_test["within_5pct"],
        metrics_final_test["within_10pct"]
    ],
    [
        "Final_Cp_T_model_RF_slopeT",
        "train_plus_test_all",
        all_r2,
        all_mse,
        all_ard,
        all_within_1pct,
        all_within_5pct,
        all_within_10pct
    ]
]

summary_df = pd.DataFrame(
    summary_rows,
    columns=[
        "Model",
        "Dataset",
        "R2",
        "MSE",
        "ARD_%",
        "within_1pct",
        "within_5pct",
        "within_10pct"
    ]
)

summary_df.to_excel(
    "RF_子模型全数据_最终模型划分_评估汇总.xlsx",
    index=False
)


# ============================================================
# 13. 保存最终 RF 模型特征重要性
# ============================================================

feature_labels = (
    list(group_cols) +
    [f"{g}_T" for g in group_cols] +
    ["slope×T"]
)

feature_importance_df = pd.DataFrame({
    "Feature": feature_labels,
    "Importance": final_model.feature_importances_
}).sort_values(by="Importance", ascending=False)

feature_importance_df.to_excel(
    "RF_最终Cp模型_子模型全数据_slopeT特征_特征重要性.xlsx",
    index=False
)


# ============================================================
# 14. 打印保存信息
# ============================================================

print("\n已保存:")
print("1. RF_T1_model_全数据预测结果.xlsx")
print("2. RF_Cp1_model_全数据预测结果.xlsx")
print("3. RF_Cp2_model_全数据预测结果.xlsx")
print("4. RF_最终Cp模型_子模型全数据_slopeT特征_训练集预测结果.xlsx")
print("5. RF_最终Cp模型_子模型全数据_slopeT特征_测试集预测结果.xlsx")
print("6. RF_最终Cp模型_子模型全数据_slopeT特征_完整数据集预测结果.xlsx")
print("7. RF_子模型全数据_最终模型划分_评估汇总.xlsx")
print("8. RF_最终Cp模型_子模型全数据_slopeT特征_特征重要性.xlsx")