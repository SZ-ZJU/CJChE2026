# import pandas as pd
# import numpy as np
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.linear_model import HuberRegressor
# from sklearn.preprocessing import PolynomialFeatures, StandardScaler
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split
#
# # =========================
# # 0. 参数区
# # =========================
# main_file = "Pure component enthalpy 209.xlsx"
# main_sheet = "Sheet1"
#
# normal_desc_file = "selected_25_descriptors_normal.xlsx"
# normal_target = "enthalpy at normal temperature"
#
# boiling_desc_file = "selected_25_descriptors_boiling.xlsx"
# boiling_target = "enthalpy at boiling temperature"
#
# transformed_file = "Transformed_enthalpy_Dataset.xlsx"
# final_target_col = "Enthalpy"
#
# rows_per_material = 10
# random_state = 42
# T_ref = 298.15
# Tb0 = 222.543
#
# # =========================
# # 1. 读取主数据表（包含物质ID、基团、Tb）
# # =========================
# df_main = pd.read_excel(main_file, sheet_name=main_sheet).copy()
#
# material_id_col = df_main.columns[0]
# material_ids = df_main[material_id_col].values
#
# Nk_all = df_main.iloc[:, 12:31].apply(pd.to_numeric, errors="coerce")
# Tb_raw = pd.to_numeric(df_main.iloc[:, 5], errors="coerce").values
#
# print("========== 主表信息 ==========")
# print(f"主表物质数: {len(df_main)}")
#
# # =========================
# # 2. 训练 normal temperature 子模型（全数据）
# # =========================
# df_298 = pd.read_excel(normal_desc_file).copy()
#
# X_298 = df_298.drop(columns=[normal_target], errors="ignore").copy()
# X_298 = X_298.select_dtypes(include=[np.number]).replace([np.inf, -np.inf], np.nan)
# y_298 = pd.to_numeric(df_298[normal_target], errors="coerce").values
#
# mask_298 = X_298.notna().all(axis=1) & np.isfinite(y_298)
# X_298_valid = X_298.loc[mask_298].copy()
# y_298_valid = y_298[mask_298]
#
# rf_298 = RandomForestRegressor(
#     n_estimators=100,
#     random_state=random_state,
#     n_jobs=-1
# )
# rf_298.fit(X_298_valid, y_298_valid)
#
# X_298_full = X_298.fillna(X_298_valid.median(numeric_only=True))
# HVap_298_all = rf_298.predict(X_298_full)
#
# # =========================
# # 3. 训练 boiling temperature 子模型（全数据）
# # =========================
# df_Tb = pd.read_excel(boiling_desc_file).copy()
#
# X_Tb = df_Tb.drop(columns=[boiling_target], errors="ignore").copy()
# X_Tb = X_Tb.select_dtypes(include=[np.number]).replace([np.inf, -np.inf], np.nan)
# y_Tb = pd.to_numeric(df_Tb[boiling_target], errors="coerce").values
#
# mask_Tb = X_Tb.notna().all(axis=1) & np.isfinite(y_Tb)
# X_Tb_valid = X_Tb.loc[mask_Tb].copy()
# y_Tb_valid = y_Tb[mask_Tb]
#
# rf_Tb = RandomForestRegressor(
#     n_estimators=100,
#     random_state=random_state,
#     n_jobs=-1
# )
# rf_Tb.fit(X_Tb_valid, y_Tb_valid)
#
# X_Tb_full = X_Tb.fillna(X_Tb_valid.median(numeric_only=True))
# HVap_Tb_all = rf_Tb.predict(X_Tb_full)
#
# # =========================
# # 4. 拟合 Tb 模型（全数据）
# # =========================
# mask_tb = np.isfinite(Tb_raw) & Nk_all.notna().all(axis=1).values
#
# poly = PolynomialFeatures(degree=2, include_bias=False)
# Nk_poly = poly.fit_transform(Nk_all)
#
# scaler = StandardScaler()
# Nk_scaled = scaler.fit_transform(Nk_poly)
#
# model_Tb = HuberRegressor(max_iter=10000)
# model_Tb.fit(Nk_scaled[mask_tb], np.exp(Tb_raw[mask_tb] / Tb0))
#
# Tb_pred_all = Tb0 * np.log(np.clip(model_Tb.predict(Nk_scaled), 1e-6, None))
#
# # =========================
# # 5. 一致性检查
# # =========================
# n_main = len(df_main)
# if len(HVap_298_all) != n_main:
#     raise ValueError(
#         f"{normal_desc_file} 预测行数 = {len(HVap_298_all)}，但主表物质数 = {n_main}，无法按顺序一一对应。"
#     )
# if len(HVap_Tb_all) != n_main:
#     raise ValueError(
#         f"{boiling_desc_file} 预测行数 = {len(HVap_Tb_all)}，但主表物质数 = {n_main}，无法按顺序一一对应。"
#     )
#
# # =========================
# # 6. 计算 slope
# # =========================
# denom = Tb_pred_all - T_ref
# safe_denom = np.where(np.abs(denom) < 1e-12, np.nan, denom)
#
# slope_all = (HVap_Tb_all - HVap_298_all) / safe_denom
#
# slope_df = pd.DataFrame({
#     "Material_ID": material_ids,
#     "enthalpy_298_pred": HVap_298_all,
#     "enthalpy_Tb_pred": HVap_Tb_all,
#     "Tb_pred": Tb_pred_all,
#     "slope": slope_all
# })
# slope_df.to_excel("slope_values.xlsx", index=False)
# print("✅ slope 已保存为 slope_values.xlsx")
#
# # =========================
# # 7. 把 slope 合并进 transformed 数据
# # =========================
# trans_df = pd.read_excel(transformed_file).reset_index(drop=True).copy()
#
# if len(trans_df) % rows_per_material != 0:
#     raise ValueError(
#         f"{transformed_file} 总行数 {len(trans_df)} 不是 {rows_per_material} 的整数倍，无法按每个物质 {rows_per_material} 行映射。"
#     )
#
# n_materials_trans = len(trans_df) // rows_per_material
# if n_materials_trans != len(slope_df):
#     raise ValueError(
#         f"{transformed_file} 推断物质数 = {n_materials_trans}，但 slope 物质数 = {len(slope_df)}，二者不一致。"
#     )
#
# trans_df["Material_ID"] = np.repeat(slope_df["Material_ID"].values, rows_per_material)
# trans_df["slope"] = np.repeat(slope_df["slope"].values, rows_per_material)
#
# transformed_with_slope_path = "Transformed_enthalpy_with_slope.xlsx"
# trans_df.to_excel(transformed_with_slope_path, index=False)
# print(f"✅ 已成功保存为: {transformed_with_slope_path}")
#
# # =========================
# # 8. 最终模型：按物质 8:2 划分
# # =========================
# df_final = trans_df.copy()
#
# df_final[final_target_col] = pd.to_numeric(df_final[final_target_col], errors="coerce")
# df_final = df_final.dropna(subset=[final_target_col]).copy()
#
# unique_materials = df_final["Material_ID"].dropna().unique()
#
# train_materials, test_materials = train_test_split(
#     unique_materials,
#     test_size=0.2,
#     random_state=random_state
# )
#
# train_df = df_final[df_final["Material_ID"].isin(train_materials)].copy()
# test_df = df_final[df_final["Material_ID"].isin(test_materials)].copy()
#
# print("\n========== 按物质划分 ==========")
# print(f"总物质数: {len(unique_materials)}")
# print(f"训练集物质数: {len(train_materials)}")
# print(f"测试集物质数: {len(test_materials)}")
# print(f"训练集样本点数: {len(train_df)}")
# print(f"测试集样本点数: {len(test_df)}")
#
# # =========================
# # 9. 构造特征和目标
# # =========================
# drop_cols = [final_target_col, "Material_ID"]
#
# X_train = train_df.drop(columns=drop_cols, errors="ignore").copy()
# X_test = test_df.drop(columns=drop_cols, errors="ignore").copy()
#
# y_train = train_df[final_target_col].astype(float).values
# y_test = test_df[final_target_col].astype(float).values
#
# numeric_cols = X_train.select_dtypes(include=[np.number]).columns.tolist()
# non_numeric_cols = [c for c in X_train.columns if c not in numeric_cols]
#
# if len(non_numeric_cols) > 0:
#     print(f"⚠️ 检测到非数值列，已删除: {non_numeric_cols}")
#
# X_train = X_train[numeric_cols].replace([np.inf, -np.inf], np.nan)
# X_test = X_test[numeric_cols].replace([np.inf, -np.inf], np.nan)
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
# # 10. 最终 RF 模型训练
# # =========================
# final_model = RandomForestRegressor(
#     n_estimators=100,
#     random_state=random_state,
#     n_jobs=-1
# )
# final_model.fit(X_train, y_train)
#
# # =========================
# # 11. 评估函数
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
#     relative_error[nonzero_mask] = 100 * np.abs(
#         (y_true[nonzero_mask] - y_pred[nonzero_mask]) / y_true[nonzero_mask]
#     )
#
#     ard = np.nanmean(relative_error)
#     error_1_percent = np.sum(relative_error < 1)
#     error_5_percent = np.sum(relative_error < 5)
#     error_10_percent = np.sum(relative_error < 10)
#
#     print(f"\n📊 {name} 模型评估结果：")
#     print(f"R²  = {r2:.4f}")
#     print(f"MSE = {mse:.4f}")
#     print(f"ARD = {ard:.2f}%")
#     print(f"误差 < 1%: {error_1_percent} 个")
#     print(f"误差 < 5%: {error_5_percent} 个")
#     print(f"误差 < 10%: {error_10_percent} 个")
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
# # 12. 训练集 / 测试集预测
# # =========================
# y_train_pred = final_model.predict(X_train)
# rel_err_train, train_summary = evaluate_dataset(y_train, y_train_pred, name="Train")
#
# y_test_pred = final_model.predict(X_test)
# rel_err_test, test_summary = evaluate_dataset(y_test, y_test_pred, name="Test")
#
# # =========================
# # 13. 保存最终结果
# # =========================
# train_result = train_df.copy()
# train_result["Predicted_Enthalpy"] = y_train_pred
# train_result["Absolute_Error"] = np.abs(y_train - y_train_pred)
# train_result["Relative_Error (%)"] = rel_err_train
# train_result["Set"] = "Train"
#
# test_result = test_df.copy()
# test_result["Predicted_Enthalpy"] = y_test_pred
# test_result["Absolute_Error"] = np.abs(y_test - y_test_pred)
# test_result["Relative_Error (%)"] = rel_err_test
# test_result["Set"] = "Test"
#
# summary_df = pd.DataFrame([train_summary, test_summary])
#
# final_output = "prediction_vs_actual_Enthalpy_with_slope_train_test_split.xlsx"
# with pd.ExcelWriter(final_output, engine="xlsxwriter") as writer:
#     slope_df.to_excel(writer, sheet_name="slope_values", index=False)
#     trans_df.to_excel(writer, sheet_name="transformed_with_slope", index=False)
#     train_result.to_excel(writer, sheet_name="train_predictions", index=False)
#     test_result.to_excel(writer, sheet_name="test_predictions", index=False)
#     summary_df.to_excel(writer, sheet_name="summary", index=False)
#
# print(f"\n✅ 已保存最终结果为: {final_output}")



import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import HuberRegressor
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


# =========================
# 0. 参数区
# =========================
main_file = "Pure component enthalpy 209.xlsx"
main_sheet = "Sheet1"

normal_desc_file = "selected_25_descriptors_normal.xlsx"
normal_target = "enthalpy at normal temperature"

boiling_desc_file = "selected_25_descriptors_boiling.xlsx"
boiling_target = "enthalpy at boiling temperature"

transformed_file = "Transformed_enthalpy_Dataset.xlsx"
final_target_col = "Enthalpy"

rows_per_material = 10
random_state = 42
T_ref = 298.15
Tb0 = 222.543


# =========================
# 1. 读取主数据表：包含物质ID、基团、Tb
# =========================
df_main = pd.read_excel(main_file, sheet_name=main_sheet).copy()

material_id_col = df_main.columns[0]
material_ids = df_main[material_id_col].values

Nk_all = df_main.iloc[:, 12:31].apply(pd.to_numeric, errors="coerce")
Tb_raw = pd.to_numeric(df_main.iloc[:, 5], errors="coerce").values

print("========== 主表信息 ==========")
print(f"主表物质数: {len(df_main)}")


# =========================
# 2. 训练 normal temperature enthalpy 子模型：全数据
# =========================
df_298 = pd.read_excel(normal_desc_file).copy()

X_298 = df_298.drop(columns=[normal_target], errors="ignore").copy()
X_298 = X_298.select_dtypes(include=[np.number]).replace([np.inf, -np.inf], np.nan)

y_298 = pd.to_numeric(df_298[normal_target], errors="coerce").values

mask_298 = (
    X_298.notna().all(axis=1)
    & np.isfinite(y_298)
)

X_298_valid = X_298.loc[mask_298].copy()
y_298_valid = y_298[mask_298]

rf_298 = RandomForestRegressor(
    n_estimators=100,
    random_state=random_state,
    n_jobs=-1
)

rf_298.fit(
    X_298_valid,
    y_298_valid
)

X_298_full = X_298.fillna(
    X_298_valid.median(numeric_only=True)
)

enthalpy_298_all = rf_298.predict(X_298_full)


# =========================
# 3. 训练 boiling temperature enthalpy 子模型：全数据
# =========================
df_Tb = pd.read_excel(boiling_desc_file).copy()

X_Tb = df_Tb.drop(columns=[boiling_target], errors="ignore").copy()
X_Tb = X_Tb.select_dtypes(include=[np.number]).replace([np.inf, -np.inf], np.nan)

y_Tb = pd.to_numeric(df_Tb[boiling_target], errors="coerce").values

mask_Tb = (
    X_Tb.notna().all(axis=1)
    & np.isfinite(y_Tb)
)

X_Tb_valid = X_Tb.loc[mask_Tb].copy()
y_Tb_valid = y_Tb[mask_Tb]

rf_Tb = RandomForestRegressor(
    n_estimators=100,
    random_state=random_state,
    n_jobs=-1
)

rf_Tb.fit(
    X_Tb_valid,
    y_Tb_valid
)

X_Tb_full = X_Tb.fillna(
    X_Tb_valid.median(numeric_only=True)
)

enthalpy_Tb_all = rf_Tb.predict(X_Tb_full)


# =========================
# 4. 拟合 Tb 子模型：全数据
# =========================
mask_tb = (
    np.isfinite(Tb_raw)
    & Nk_all.notna().all(axis=1).values
)

poly = PolynomialFeatures(
    degree=2,
    include_bias=False
)

Nk_poly = poly.fit_transform(Nk_all)

scaler = StandardScaler()
Nk_scaled = scaler.fit_transform(Nk_poly)

model_Tb = HuberRegressor(
    max_iter=10000
)

model_Tb.fit(
    Nk_scaled[mask_tb],
    np.exp(Tb_raw[mask_tb] / Tb0)
)

Tb_pred_all = Tb0 * np.log(
    np.clip(
        model_Tb.predict(Nk_scaled),
        1e-6,
        None
    )
)


# =========================
# 5. 一致性检查
# =========================
n_main = len(df_main)

if len(enthalpy_298_all) != n_main:
    raise ValueError(
        f"{normal_desc_file} 预测行数 = {len(enthalpy_298_all)}，"
        f"但主表物质数 = {n_main}，无法按顺序一一对应。"
    )

if len(enthalpy_Tb_all) != n_main:
    raise ValueError(
        f"{boiling_desc_file} 预测行数 = {len(enthalpy_Tb_all)}，"
        f"但主表物质数 = {n_main}，无法按顺序一一对应。"
    )


# =========================
# 6. 计算 slope
# =========================
denom = Tb_pred_all - T_ref

safe_denom = np.where(
    np.abs(denom) < 1e-12,
    np.nan,
    denom
)

slope_all = (
    enthalpy_Tb_all
    - enthalpy_298_all
) / safe_denom

slope_df = pd.DataFrame({
    "Material_ID": material_ids,
    "enthalpy_298_pred": enthalpy_298_all,
    "enthalpy_Tb_pred": enthalpy_Tb_all,
    "Tb_pred": Tb_pred_all,
    "slope": slope_all
})

slope_df.to_excel(
    "slope_values.xlsx",
    index=False
)

print("slope 已保存为 slope_values.xlsx")


# =========================
# 7. 把 slope 合并进 transformed 数据
# =========================
trans_df = pd.read_excel(transformed_file).reset_index(drop=True).copy()

if len(trans_df) % rows_per_material != 0:
    raise ValueError(
        f"{transformed_file} 总行数 {len(trans_df)} 不是 {rows_per_material} 的整数倍，"
        f"无法按每个物质 {rows_per_material} 行映射。"
    )

n_materials_trans = len(trans_df) // rows_per_material

if n_materials_trans != len(slope_df):
    raise ValueError(
        f"{transformed_file} 推断物质数 = {n_materials_trans}，"
        f"但 slope 物质数 = {len(slope_df)}，二者不一致。"
    )

trans_df["Material_ID"] = np.repeat(
    slope_df["Material_ID"].values,
    rows_per_material
)

trans_df["slope"] = np.repeat(
    slope_df["slope"].values,
    rows_per_material
)

# 建议也把三个参考预测值并入最终特征，方便对比和解释
trans_df["enthalpy_298_pred"] = np.repeat(
    slope_df["enthalpy_298_pred"].values,
    rows_per_material
)

trans_df["enthalpy_Tb_pred"] = np.repeat(
    slope_df["enthalpy_Tb_pred"].values,
    rows_per_material
)

trans_df["Tb_pred"] = np.repeat(
    slope_df["Tb_pred"].values,
    rows_per_material
)

transformed_with_slope_path = "Transformed_enthalpy_with_slope.xlsx"

trans_df.to_excel(
    transformed_with_slope_path,
    index=False
)

print(f"已成功保存为: {transformed_with_slope_path}")


# =========================
# 8. 最终模型：按物质 8:2 划分
# =========================
df_final = trans_df.copy()

df_final[final_target_col] = pd.to_numeric(
    df_final[final_target_col],
    errors="coerce"
)

df_final = df_final.dropna(subset=[final_target_col]).copy()

unique_materials = df_final["Material_ID"].dropna().unique()

train_materials, test_materials = train_test_split(
    unique_materials,
    test_size=0.2,
    random_state=random_state
)

train_materials = set(train_materials)
test_materials = set(test_materials)

train_df = df_final[
    df_final["Material_ID"].isin(train_materials)
].copy()

test_df = df_final[
    df_final["Material_ID"].isin(test_materials)
].copy()

print("\n========== 按物质划分 ==========")
print(f"总物质数: {len(unique_materials)}")
print(f"训练集物质数: {len(train_materials)}")
print(f"测试集物质数: {len(test_materials)}")
print(f"训练集样本点数: {len(train_df)}")
print(f"测试集样本点数: {len(test_df)}")


# =========================
# 9. 构造特征和目标
# =========================
drop_cols = [
    final_target_col,
    "Material_ID"
]

X_train = train_df.drop(
    columns=drop_cols,
    errors="ignore"
).copy()

X_test = test_df.drop(
    columns=drop_cols,
    errors="ignore"
).copy()

y_train = train_df[final_target_col].astype(float).values
y_test = test_df[final_target_col].astype(float).values

numeric_cols = X_train.select_dtypes(
    include=[np.number]
).columns.tolist()

non_numeric_cols = [
    c for c in X_train.columns
    if c not in numeric_cols
]

if len(non_numeric_cols) > 0:
    print(f"检测到非数值列，已删除: {non_numeric_cols}")

X_train = X_train[numeric_cols].replace(
    [np.inf, -np.inf],
    np.nan
)

X_test = X_test[numeric_cols].replace(
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

print(f"\n清洗后训练集样本点数: {len(X_train)}")
print(f"清洗后测试集样本点数: {len(X_test)}")
print(f"最终模型特征数: {X_train.shape[1]}")


# =========================
# 10. 最终 RF 模型训练
# =========================
final_model = RandomForestRegressor(
    n_estimators=100,
    random_state=random_state,
    n_jobs=-1
)

print("\n开始训练最终 RF 模型...")
final_model.fit(X_train, y_train)

print("\n最终 RF 模型参数:")
print(final_model)


# =========================
# 11. 评估函数
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
        error_1_percent = np.sum(relative_error_valid < 1)
        error_5_percent = np.sum(relative_error_valid < 5)
        error_10_percent = np.sum(relative_error_valid < 10)
    else:
        error_1_percent = np.sum(relative_error_valid <= 1)
        error_5_percent = np.sum(relative_error_valid <= 5)
        error_10_percent = np.sum(relative_error_valid <= 10)

    print(f"\n{name} 模型评估结果：")
    print(f"R2  = {r2:.4f}")
    print(f"MSE = {mse:.4f}")
    print(f"ARD = {ard:.2f}%")

    print(f"\n{name} 统计结果：")

    if strict_less:
        print(f"误差 < 1%: {error_1_percent} 个")
        print(f"误差 < 5%: {error_5_percent} 个")
        print(f"误差 < 10%: {error_10_percent} 个")
    else:
        print(f"误差 <= 1%: {error_1_percent} 个")
        print(f"误差 <= 5%: {error_5_percent} 个")
        print(f"误差 <= 10%: {error_10_percent} 个")

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


# =========================
# 12. 训练集 / 测试集预测
# =========================
y_train_pred = final_model.predict(X_train)

rel_err_train, train_summary = evaluate_dataset(
    y_train,
    y_train_pred,
    name="Train",
    strict_less=True
)

y_test_pred = final_model.predict(X_test)

rel_err_test, test_summary = evaluate_dataset(
    y_test,
    y_test_pred,
    name="Test",
    strict_less=True
)


# =========================
# 12.1 完整数据集统计：训练集 + 测试集
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

print("\nTransformed Enthalpy + slope RF 完整数据集预测偏差 1%，5%，10%分别为：")
print(all_summary["Count_<1%"])
print(all_summary["Count_<5%"])
print(all_summary["Count_<10%"])


# =========================
# 13. 保存最终结果
# =========================
train_result = train_df.copy()
train_result["Predicted_Enthalpy"] = y_train_pred
train_result["Absolute_Error"] = np.abs(
    y_train - y_train_pred
)
train_result["Relative_Error (%)"] = rel_err_train
train_result["Set"] = "Train"

test_result = test_df.copy()
test_result["Predicted_Enthalpy"] = y_test_pred
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
all_result["Predicted_Enthalpy"] = y_all_pred
all_result["Absolute_Error"] = np.abs(
    y_all_true - y_all_pred
)
all_result["Relative_Error (%)"] = rel_err_all

summary_df = pd.DataFrame([
    train_summary,
    test_summary,
    all_summary
])


# =========================
# 14. 保存 Excel
# =========================
final_output = "prediction_vs_actual_Enthalpy_with_slope_train_test_split.xlsx"

with pd.ExcelWriter(final_output, engine="xlsxwriter") as writer:
    slope_df.to_excel(
        writer,
        sheet_name="slope_values",
        index=False
    )

    trans_df.to_excel(
        writer,
        sheet_name="transformed_with_slope",
        index=False
    )

    train_result.to_excel(
        writer,
        sheet_name="train_predictions",
        index=False
    )

    test_result.to_excel(
        writer,
        sheet_name="test_predictions",
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

print(f"\n已保存最终结果为: {final_output}")


# =========================
# 15. 保存特征重要性
# =========================
feature_importance_df = pd.DataFrame({
    "Feature": X_train.columns,
    "Importance": final_model.feature_importances_
}).sort_values(
    by="Importance",
    ascending=False
)

feature_importance_file = "Transformed_Enthalpy_with_slope_RF_feature_importance.xlsx"

feature_importance_df.to_excel(
    feature_importance_file,
    index=False
)

print(f"特征重要性已保存为: {feature_importance_file}")


# =========================
# 16. 输出模型结构记录
# =========================
print("\n当前 Transformed Enthalpy + slope + RF 模型结构:")
print("enthalpy_298_submodel: RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)")
print("enthalpy_Tb_submodel: RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)")
print("Tb_submodel: HuberRegressor(max_iter=10000), input = StandardScaler(PolynomialFeatures(Nk, degree=2))")
print("slope = (enthalpy_Tb_pred - enthalpy_298_pred) / (Tb_pred - 298.15)")
print("Final target: Enthalpy")
print("Final model: RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)")
print("Final input features: transformed numeric features + slope + enthalpy_298_pred + enthalpy_Tb_pred + Tb_pred")
print("Split: material-level 8:2 split")
print("Final all-data statistics use strict thresholds: <1%, <5%, <10%")