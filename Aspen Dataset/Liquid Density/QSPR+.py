# import pandas as pd
# import numpy as np
# from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
# from sklearn.preprocessing import PolynomialFeatures
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split
#
# # =========================
# # 0. 参数区
# # =========================
# main_file = "liquid density.xlsx"
# main_sheet = "Sheet1"
#
# normal_desc_file = "selected_25_descriptors_normal.xlsx"
# normal_target = "ASPEN Liquid Density at Normal Temperature(g/cc)"
#
# boiling_desc_file = "selected_25_descriptors_boiling.xlsx"
# boiling_target = "ASPEN Liquid Density at BoilingTemperature(g/cc)"
#
# transformed_file = "Transformed_density_Dataset.xlsx"
# final_target_col = "Density"
#
# rows_per_material = 10
# random_state = 40
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
# # 2. 子模型评估函数
# # =========================
# def evaluate_scalar_model(y_true, y_pred, model_name="Submodel"):
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#
#     mask = np.isfinite(y_true) & np.isfinite(y_pred)
#     y_true = y_true[mask]
#     y_pred = y_pred[mask]
#
#     if len(y_true) == 0:
#         print(f"\n📊 {model_name}：无有效样本")
#         return {
#             "Model": model_name,
#             "R2": np.nan,
#             "MSE": np.nan,
#             "ARD_%": np.nan,
#             "Count_<1%": np.nan,
#             "Count_<5%": np.nan,
#             "Count_<10%": np.nan
#         }
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
#     error_1_percent = np.sum(relative_error < 1)
#     error_5_percent = np.sum(relative_error < 5)
#     error_10_percent = np.sum(relative_error < 10)
#
#     print(f"\n📊 {model_name} 预测效果：")
#     print(f"R²  = {r2:.4f}")
#     print(f"MSE = {mse:.8f}")
#     print(f"ARD = {ard:.2f}%")
#     print(f"误差 < 1%: {error_1_percent} 个")
#     print(f"误差 < 5%: {error_5_percent} 个")
#     print(f"误差 < 10%: {error_10_percent} 个")
#
#     return {
#         "Model": model_name,
#         "R2": r2,
#         "MSE": mse,
#         "ARD_%": ard,
#         "Count_<1%": error_1_percent,
#         "Count_<5%": error_5_percent,
#         "Count_<10%": error_10_percent
#     }
#
# # =========================
# # 3. 读取并训练 Normal Temperature 密度子模型（改为 GBDT）
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
# gbdt_298 = GradientBoostingRegressor(
#     n_estimators=300,
#     learning_rate=0.05,
#     max_depth=4,
#     min_samples_split=10,
#     min_samples_leaf=5,
#     random_state=random_state
# )
# gbdt_298.fit(X_298_valid, y_298_valid)
#
# X_298_full = X_298.fillna(X_298_valid.median(numeric_only=True))
# Density_298_all = gbdt_298.predict(X_298_full)
#
# normal_density_summary = evaluate_scalar_model(
#     y_298,
#     Density_298_all,
#     model_name="Normal_Temperature_Density_Submodel_GBDT"
# )
#
# normal_density_out = pd.DataFrame({
#     "Material_ID": material_ids[:len(df_298)],
#     "Density_298_true": y_298,
#     "Density_298_pred": Density_298_all,
#     "Absolute_Error": np.abs(Density_298_all - y_298),
#     "Relative_Error (%)": np.where(
#         np.abs(y_298) > 1e-12,
#         np.abs((Density_298_all - y_298) / y_298) * 100,
#         np.nan
#     )
# })
#
# # =========================
# # 4. 读取并训练 Boiling Temperature 密度子模型（改为 GBDT）
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
# gbdt_Tb = GradientBoostingRegressor(
#     n_estimators=300,
#     learning_rate=0.05,
#     max_depth=4,
#     min_samples_split=10,
#     min_samples_leaf=5,
#     random_state=random_state
# )
# gbdt_Tb.fit(X_Tb_valid, y_Tb_valid)
#
# X_Tb_full = X_Tb.fillna(X_Tb_valid.median(numeric_only=True))
# Density_Tb_all = gbdt_Tb.predict(X_Tb_full)
#
# boiling_density_summary = evaluate_scalar_model(
#     y_Tb,
#     Density_Tb_all,
#     model_name="Boiling_Temperature_Density_Submodel_GBDT"
# )
#
# boiling_density_out = pd.DataFrame({
#     "Material_ID": material_ids[:len(df_Tb)],
#     "Density_Tb_true": y_Tb,
#     "Density_Tb_pred": Density_Tb_all,
#     "Absolute_Error": np.abs(Density_Tb_all - y_Tb),
#     "Relative_Error (%)": np.where(
#         np.abs(y_Tb) > 1e-12,
#         np.abs((Density_Tb_all - y_Tb) / y_Tb) * 100,
#         np.nan
#     )
# })
#
# # =========================
# # 5. 拟合 Tb 子模型（改为 GBDT）
# # =========================
# mask_tb = np.isfinite(Tb_raw) & Nk_all.notna().all(axis=1).values
#
# poly = PolynomialFeatures(degree=2, include_bias=False)
# Nk_poly = poly.fit_transform(Nk_all)
#
# # GBDT 不依赖标准化，这里直接用 Nk_poly
# gbdt_tb_model = GradientBoostingRegressor(
#     n_estimators=300,
#     learning_rate=0.05,
#     max_depth=4,
#     min_samples_split=10,
#     min_samples_leaf=5,
#     random_state=random_state
# )
#
# gbdt_tb_model.fit(
#     Nk_poly[mask_tb],
#     np.exp(Tb_raw[mask_tb] / Tb0)
# )
#
# Tb_pred_all = Tb0 * np.log(np.clip(gbdt_tb_model.predict(Nk_poly), 1e-6, None))
#
# tb_summary = evaluate_scalar_model(
#     Tb_raw,
#     Tb_pred_all,
#     model_name="Tb_Submodel_GBDT"
# )
#
# tb_out = pd.DataFrame({
#     "Material_ID": material_ids,
#     "Tb_true": Tb_raw,
#     "Tb_pred": Tb_pred_all,
#     "Absolute_Error": np.abs(Tb_pred_all - Tb_raw),
#     "Relative_Error (%)": np.where(
#         np.abs(Tb_raw) > 1e-12,
#         np.abs((Tb_pred_all - Tb_raw) / Tb_raw) * 100,
#         np.nan
#     )
# })
#
# # =========================
# # 6. 长度一致性检查
# # =========================
# n_main = len(df_main)
# if len(Density_298_all) != n_main:
#     raise ValueError(
#         f"{normal_desc_file} 预测行数 = {len(Density_298_all)}，但主表物质数 = {n_main}，无法按顺序一一对应。"
#     )
# if len(Density_Tb_all) != n_main:
#     raise ValueError(
#         f"{boiling_desc_file} 预测行数 = {len(Density_Tb_all)}，但主表物质数 = {n_main}，无法按顺序一一对应。"
#     )
#
# # =========================
# # 7. 计算 slope
# # =========================
# denom = Tb_pred_all - T_ref
# safe_denom = np.where(np.abs(denom) < 1e-12, np.nan, denom)
#
# slope_all = (Density_Tb_all - Density_298_all) / safe_denom
#
# slope_df = pd.DataFrame({
#     "Material_ID": material_ids,
#     "Density_298_pred": Density_298_all,
#     "Density_Tb_pred": Density_Tb_all,
#     "Tb_pred": Tb_pred_all,
#     "slope": slope_all
# })
# slope_df.to_excel("slope_values.xlsx", index=False)
# print("✅ slope 已保存为 slope_values.xlsx")
#
# # =========================
# # 8. 读取 transformed 数据，并融合 slope
# # =========================
# trans_df = pd.read_excel(transformed_file).reset_index(drop=True).copy()
#
# if len(trans_df) % rows_per_material != 0:
#     raise ValueError(
#         f"{transformed_file} 总行数 {len(trans_df)} 不是 {rows_per_material} 的整数倍，无法按每物质 {rows_per_material} 行映射。"
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
# transformed_with_slope_path = "Transformed_density_with_slope.xlsx"
# trans_df.to_excel(transformed_with_slope_path, index=False)
# print(f"✅ 已成功保存为: {transformed_with_slope_path}")
#
# # =========================
# # 9. 最终模型：按物质 8:2 划分
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
# # 10. 构造特征和目标
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
# # 11. 最终 RF 模型训练（保持不变）
# # =========================
# final_model = RandomForestRegressor(
#     n_estimators=100,
#     random_state=random_state,
#     n_jobs=-1
# )
# final_model.fit(X_train, y_train)
#
# # =========================
# # 12. 最终模型评估函数
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
#     relative_error[nonzero_mask] = 100 * np.abs((y_true[nonzero_mask] - y_pred[nonzero_mask]) / y_true[nonzero_mask])
#
#     ard = np.nanmean(relative_error)
#     error_1_percent = np.sum(relative_error < 1)
#     error_5_percent = np.sum(relative_error < 5)
#     error_10_percent = np.sum(relative_error < 10)
#
#     print(f"\n📊 {name} 模型评估结果：")
#     print(f"R²  = {r2:.4f}")
#     print(f"MSE = {mse:.8f}")
#     print(f"ARD = {ard:.2f}%")
#     print(f"误差 < 1%: {error_1_percent} 个")
#     print(f"误差 < 5%: {error_5_percent} 个")
#     print(f"误差 < 10%: {error_10_percent} 个")
#
#     summary = {
#         "Model": name,
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
# # 13. 训练集 / 测试集预测
# # =========================
# y_train_pred = final_model.predict(X_train)
# rel_err_train, train_summary = evaluate_dataset(y_train, y_train_pred, name="Final_Train")
#
# y_test_pred = final_model.predict(X_test)
# rel_err_test, test_summary = evaluate_dataset(y_test, y_test_pred, name="Final_Test")
#
# # =========================
# # 14. 保存最终结果
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
# submodel_summary_df = pd.DataFrame([
#     normal_density_summary,
#     boiling_density_summary,
#     tb_summary
# ])
#
# final_summary_df = pd.DataFrame([train_summary, test_summary])
#
# final_output = "prediction_vs_actual_Density_with_slope_train_test_split.xlsx"
# with pd.ExcelWriter(final_output, engine="xlsxwriter") as writer:
#     slope_df.to_excel(writer, sheet_name="slope_values", index=False)
#     trans_df.to_excel(writer, sheet_name="transformed_with_slope", index=False)
#
#     normal_density_out.to_excel(writer, sheet_name="normal_density_submodel", index=False)
#     boiling_density_out.to_excel(writer, sheet_name="boiling_density_submodel", index=False)
#     tb_out.to_excel(writer, sheet_name="Tb_submodel", index=False)
#
#     submodel_summary_df.to_excel(writer, sheet_name="submodel_summary", index=False)
#
#     train_result.to_excel(writer, sheet_name="train_predictions", index=False)
#     test_result.to_excel(writer, sheet_name="test_predictions", index=False)
#     final_summary_df.to_excel(writer, sheet_name="final_summary", index=False)
#
# print(f"\n✅ 已保存最终结果为: {final_output}")



import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


# =========================
# 0. 参数区
# =========================
main_file = "liquid density.xlsx"
main_sheet = "Sheet1"

normal_desc_file = "selected_25_descriptors_normal.xlsx"
normal_target = "ASPEN Liquid Density at Normal Temperature(g/cc)"

boiling_desc_file = "selected_25_descriptors_boiling.xlsx"
boiling_target = "ASPEN Liquid Density at BoilingTemperature(g/cc)"

transformed_file = "Transformed_density_Dataset.xlsx"
final_target_col = "Density"

rows_per_material = 10
random_state = 40
T_ref = 298.15
Tb0 = 222.543


# =========================
# 1. 读取主数据表（包含物质ID、基团、Tb）
# =========================
df_main = pd.read_excel(main_file, sheet_name=main_sheet).copy()

material_id_col = df_main.columns[0]
material_ids = df_main[material_id_col].values

Nk_all = df_main.iloc[:, 12:31].apply(pd.to_numeric, errors="coerce")
Tb_raw = pd.to_numeric(df_main.iloc[:, 5], errors="coerce").values

print("========== 主表信息 ==========")
print(f"主表物质数: {len(df_main)}")


# =========================
# 2. 子模型评估函数
# =========================
def evaluate_scalar_model(y_true, y_pred, model_name="Submodel"):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true_valid = y_true[mask]
    y_pred_valid = y_pred[mask]

    relative_error_full = np.full_like(y_true, np.nan, dtype=float)

    if len(y_true_valid) == 0:
        print(f"\n📊 {model_name}：无有效样本")
        return {
            "Model": model_name,
            "Dataset": "all_data",
            "R2": np.nan,
            "MSE": np.nan,
            "ARD_%": np.nan,
            "Count_<1%": 0,
            "Count_<5%": 0,
            "Count_<10%": 0
        }, relative_error_full

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

    relative_error_full[mask] = relative_error_valid

    error_1_percent = np.sum(relative_error_valid < 1)
    error_5_percent = np.sum(relative_error_valid < 5)
    error_10_percent = np.sum(relative_error_valid < 10)

    print(f"\n📊 {model_name} 预测效果：")
    print(f"R2  = {r2:.4f}")
    print(f"MSE = {mse:.8f}")
    print(f"ARD = {ard:.2f}%")
    print(f"误差 < 1%: {error_1_percent} 个")
    print(f"误差 < 5%: {error_5_percent} 个")
    print(f"误差 < 10%: {error_10_percent} 个")

    return {
        "Model": model_name,
        "Dataset": "all_data",
        "R2": r2,
        "MSE": mse,
        "ARD_%": ard,
        "Count_<1%": error_1_percent,
        "Count_<5%": error_5_percent,
        "Count_<10%": error_10_percent
    }, relative_error_full


# =========================
# 3. 读取并训练 Normal Temperature 密度子模型：GBDT，全数据
# =========================
df_298 = pd.read_excel(normal_desc_file).copy()

X_298 = df_298.drop(columns=[normal_target], errors="ignore").copy()
X_298 = X_298.select_dtypes(include=[np.number]).replace([np.inf, -np.inf], np.nan)

y_298 = pd.to_numeric(
    df_298[normal_target],
    errors="coerce"
).values

mask_298 = (
    X_298.notna().all(axis=1)
    & np.isfinite(y_298)
)

X_298_valid = X_298.loc[mask_298].copy()
y_298_valid = y_298[mask_298]

gbdt_298 = GradientBoostingRegressor(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=4,
    min_samples_split=10,
    min_samples_leaf=5,
    random_state=random_state
)

gbdt_298.fit(
    X_298_valid,
    y_298_valid
)

X_298_full = X_298.fillna(
    X_298_valid.median(numeric_only=True)
)

Density_298_all = gbdt_298.predict(X_298_full)

normal_density_summary, normal_density_rel_err = evaluate_scalar_model(
    y_298,
    Density_298_all,
    model_name="Normal_Temperature_Density_Submodel_GBDT"
)

normal_density_out = pd.DataFrame({
    "Material_ID": material_ids[:len(df_298)],
    "Density_298_true": y_298,
    "Density_298_pred": Density_298_all,
    "Absolute_Error": np.abs(Density_298_all - y_298),
    "Relative_Error (%)": normal_density_rel_err
})


# =========================
# 4. 读取并训练 Boiling Temperature 密度子模型：GBDT，全数据
# =========================
df_Tb = pd.read_excel(boiling_desc_file).copy()

X_Tb = df_Tb.drop(columns=[boiling_target], errors="ignore").copy()
X_Tb = X_Tb.select_dtypes(include=[np.number]).replace([np.inf, -np.inf], np.nan)

y_Tb = pd.to_numeric(
    df_Tb[boiling_target],
    errors="coerce"
).values

mask_Tb = (
    X_Tb.notna().all(axis=1)
    & np.isfinite(y_Tb)
)

X_Tb_valid = X_Tb.loc[mask_Tb].copy()
y_Tb_valid = y_Tb[mask_Tb]

gbdt_Tb = GradientBoostingRegressor(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=4,
    min_samples_split=10,
    min_samples_leaf=5,
    random_state=random_state
)

gbdt_Tb.fit(
    X_Tb_valid,
    y_Tb_valid
)

X_Tb_full = X_Tb.fillna(
    X_Tb_valid.median(numeric_only=True)
)

Density_Tb_all = gbdt_Tb.predict(X_Tb_full)

boiling_density_summary, boiling_density_rel_err = evaluate_scalar_model(
    y_Tb,
    Density_Tb_all,
    model_name="Boiling_Temperature_Density_Submodel_GBDT"
)

boiling_density_out = pd.DataFrame({
    "Material_ID": material_ids[:len(df_Tb)],
    "Density_Tb_true": y_Tb,
    "Density_Tb_pred": Density_Tb_all,
    "Absolute_Error": np.abs(Density_Tb_all - y_Tb),
    "Relative_Error (%)": boiling_density_rel_err
})


# =========================
# 5. 拟合 Tb 子模型：GBDT，全数据
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

gbdt_tb_model = GradientBoostingRegressor(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=4,
    min_samples_split=10,
    min_samples_leaf=5,
    random_state=random_state
)

gbdt_tb_model.fit(
    Nk_poly[mask_tb],
    np.exp(Tb_raw[mask_tb] / Tb0)
)

Tb_pred_all = Tb0 * np.log(
    np.clip(
        gbdt_tb_model.predict(Nk_poly),
        1e-6,
        None
    )
)

tb_summary, tb_rel_err = evaluate_scalar_model(
    Tb_raw,
    Tb_pred_all,
    model_name="Tb_Submodel_GBDT"
)

tb_out = pd.DataFrame({
    "Material_ID": material_ids,
    "Tb_true": Tb_raw,
    "Tb_pred": Tb_pred_all,
    "Absolute_Error": np.abs(Tb_pred_all - Tb_raw),
    "Relative_Error (%)": tb_rel_err
})


# =========================
# 6. 长度一致性检查
# =========================
n_main = len(df_main)

if len(Density_298_all) != n_main:
    raise ValueError(
        f"{normal_desc_file} 预测行数 = {len(Density_298_all)}，"
        f"但主表物质数 = {n_main}，无法按顺序一一对应。"
    )

if len(Density_Tb_all) != n_main:
    raise ValueError(
        f"{boiling_desc_file} 预测行数 = {len(Density_Tb_all)}，"
        f"但主表物质数 = {n_main}，无法按顺序一一对应。"
    )


# =========================
# 7. 计算 slope
# =========================
denom = Tb_pred_all - T_ref

safe_denom = np.where(
    np.abs(denom) < 1e-12,
    np.nan,
    denom
)

slope_all = (
    Density_Tb_all
    - Density_298_all
) / safe_denom

slope_df = pd.DataFrame({
    "Material_ID": material_ids,
    "Density_298_pred": Density_298_all,
    "Density_Tb_pred": Density_Tb_all,
    "Tb_pred": Tb_pred_all,
    "slope": slope_all
})

slope_df.to_excel(
    "slope_values.xlsx",
    index=False
)

print("slope 已保存为 slope_values.xlsx")


# =========================
# 8. 读取 transformed 数据，并融合 slope
# =========================
trans_df = pd.read_excel(transformed_file).reset_index(drop=True).copy()

if len(trans_df) % rows_per_material != 0:
    raise ValueError(
        f"{transformed_file} 总行数 {len(trans_df)} 不是 {rows_per_material} 的整数倍，"
        f"无法按每物质 {rows_per_material} 行映射。"
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

# 保留三个参考预测量，便于解释；如果只想使用 slope，可在 drop_cols 里删除这三列
trans_df["Density_298_pred"] = np.repeat(
    slope_df["Density_298_pred"].values,
    rows_per_material
)

trans_df["Density_Tb_pred"] = np.repeat(
    slope_df["Density_Tb_pred"].values,
    rows_per_material
)

trans_df["Tb_pred"] = np.repeat(
    slope_df["Tb_pred"].values,
    rows_per_material
)

transformed_with_slope_path = "Transformed_density_with_slope.xlsx"

trans_df.to_excel(
    transformed_with_slope_path,
    index=False
)

print(f"已成功保存为: {transformed_with_slope_path}")


# =========================
# 9. 最终模型：按物质 8:2 划分
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
# 10. 构造特征和目标
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

print("\n========== 清洗后建模数据 ==========")
print(f"清洗后训练集样本点数: {len(X_train)}")
print(f"清洗后测试集样本点数: {len(X_test)}")
print(f"最终模型特征数: {X_train.shape[1]}")


# =========================
# 11. 最终 RF 模型训练
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
# 12. 最终模型评估函数
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
            "Model": name,
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

    print(f"\n📊 {name} 模型评估结果：")
    print(f"R2  = {r2:.4f}")
    print(f"MSE = {mse:.8f}")
    print(f"ARD = {ard:.2f}%")

    if strict_less:
        print(f"误差 < 1%: {error_1_percent} 个")
        print(f"误差 < 5%: {error_5_percent} 个")
        print(f"误差 < 10%: {error_10_percent} 个")
    else:
        print(f"误差 <= 1%: {error_1_percent} 个")
        print(f"误差 <= 5%: {error_5_percent} 个")
        print(f"误差 <= 10%: {error_10_percent} 个")

    summary = {
        "Model": name,
        "R2": r2,
        "MSE": mse,
        "ARD_%": ard,
        "Count_<1%": error_1_percent,
        "Count_<5%": error_5_percent,
        "Count_<10%": error_10_percent
    }

    return relative_error, summary


# =========================
# 13. 训练集 / 测试集预测
# =========================
y_train_pred = final_model.predict(X_train)

rel_err_train, train_summary = evaluate_dataset(
    y_train,
    y_train_pred,
    name="Final_Train",
    strict_less=True
)

y_test_pred = final_model.predict(X_test)

rel_err_test, test_summary = evaluate_dataset(
    y_test,
    y_test_pred,
    name="Final_Test",
    strict_less=True
)


# =========================
# 13.1 完整数据集统计：训练集 + 测试集
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

print("\nTransformed Density + slope + GBDT submodels 完整数据集预测偏差 1%，5%，10%分别为：")
print(all_summary["Count_<1%"])
print(all_summary["Count_<5%"])
print(all_summary["Count_<10%"])


# =========================
# 14. 保存最终结果
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
# 15. 汇总结果
# =========================
submodel_summary_df = pd.DataFrame([
    normal_density_summary,
    boiling_density_summary,
    tb_summary
])

final_summary_df = pd.DataFrame([
    train_summary,
    test_summary,
    all_summary
])


# =========================
# 16. 保存 Excel
# =========================
final_output = "prediction_vs_actual_Density_with_slope_train_test_split.xlsx"

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

    normal_density_out.to_excel(
        writer,
        sheet_name="normal_density_submodel",
        index=False
    )

    boiling_density_out.to_excel(
        writer,
        sheet_name="boiling_density_submodel",
        index=False
    )

    tb_out.to_excel(
        writer,
        sheet_name="Tb_submodel",
        index=False
    )

    submodel_summary_df.to_excel(
        writer,
        sheet_name="submodel_summary",
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

    final_summary_df.to_excel(
        writer,
        sheet_name="final_summary",
        index=False
    )

print(f"\n已保存最终结果为: {final_output}")


# =========================
# 17. 保存特征重要性
# =========================
feature_importance_df = pd.DataFrame({
    "Feature": X_train.columns,
    "Importance": final_model.feature_importances_
}).sort_values(
    by="Importance",
    ascending=False
)

feature_importance_file = "Transformed_Density_with_slope_RF_feature_importance.xlsx"

feature_importance_df.to_excel(
    feature_importance_file,
    index=False
)

print(f"特征重要性已保存为: {feature_importance_file}")


# =========================
# 18. 输出模型结构记录
# =========================
print("\n当前 Transformed Density + slope + RF 模型结构:")
print("Density_298_submodel: GradientBoostingRegressor(n_estimators=300, learning_rate=0.05, max_depth=4, min_samples_split=10, min_samples_leaf=5, random_state=40)")
print("Density_Tb_submodel: GradientBoostingRegressor(n_estimators=300, learning_rate=0.05, max_depth=4, min_samples_split=10, min_samples_leaf=5, random_state=40)")
print("Tb_submodel: GradientBoostingRegressor(n_estimators=300, learning_rate=0.05, max_depth=4, min_samples_split=10, min_samples_leaf=5, random_state=40), input = PolynomialFeatures(Nk, degree=2)")
print("slope = (Density_Tb_pred - Density_298_pred) / (Tb_pred - 298.15)")
print("Final target: Density")
print("Final model: RandomForestRegressor(n_estimators=100, random_state=40, n_jobs=-1)")
print("Final input features: transformed numeric features + slope + Density_298_pred + Density_Tb_pred + Tb_pred")
print("Split: material-level 8:2 split, random_state=40")
print("Final all-data statistics use strict thresholds: <1%, <5%, <10%")