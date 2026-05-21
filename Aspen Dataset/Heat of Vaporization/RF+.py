# import pandas as pd
# import numpy as np
#
# from sklearn.linear_model import HuberRegressor
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.preprocessing import PolynomialFeatures
# from sklearn.model_selection import train_test_split
#
#
# # ============================================================
# # 常数与路径
# # ============================================================
# HV0, HVB, Tb0 = 9612.7, 15419.9, 222.543
# T_ref = 298.15
#
# main_file = "heat of vaporization 204.xlsx"
# file_298 = "selected_25_descriptors_data_298.xlsx"
# file_tb = "selected_25_descriptors_data_boiling_point.xlsx"
#
#
# # ============================================================
# # 通用评估函数
# # ============================================================
# def evaluate_metrics(y_true, y_pred, name="模型"):
#     y_true = np.asarray(y_true, dtype=float).flatten()
#     y_pred = np.asarray(y_pred, dtype=float).flatten()
#
#     mask = np.isfinite(y_true) & np.isfinite(y_pred)
#     y_true = y_true[mask]
#     y_pred = y_pred[mask]
#
#     if len(y_true) == 0:
#         print(f"\n{name} 无有效样本")
#         return {
#             "Model": name,
#             "R2": np.nan,
#             "MSE": np.nan,
#             "ARD_%": np.nan,
#             "within_1pct": 0,
#             "within_5pct": 0,
#             "within_10pct": 0,
#             "relative_error": np.array([])
#         }
#
#     mse = mean_squared_error(y_true, y_pred)
#     r2 = r2_score(y_true, y_pred)
#
#     relative_error = np.full_like(y_true, np.nan, dtype=float)
#     nonzero_mask = np.abs(y_true) > 1e-12
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
#     print(f"\n{name}评估结果:")
#     print(f"R2  = {r2:.6f}")
#     print(f"MSE = {mse:.6f}")
#     print(f"ARD = {ard:.2f}%")
#     print(f"相对误差 <= 1% 的点数: {within_1pct}")
#     print(f"相对误差 <= 5% 的点数: {within_5pct}")
#     print(f"相对误差 <= 10% 的点数: {within_10pct}")
#
#     return {
#         "Model": name,
#         "R2": r2,
#         "MSE": mse,
#         "ARD_%": ard,
#         "within_1pct": within_1pct,
#         "within_5pct": within_5pct,
#         "within_10pct": within_10pct,
#         "relative_error": relative_error
#     }
#
#
# # ============================================================
# # 读取数据
# # ============================================================
# df_main = pd.read_excel(main_file, sheet_name="Sheet1")
# df_298 = pd.read_excel(file_298)
# df_Tb = pd.read_excel(file_tb)
#
# id_col = df_main.columns[0]
#
# if not (len(df_main) == len(df_298) == len(df_Tb)):
#     raise ValueError(
#         f"三个文件行数不一致：main={len(df_main)}, "
#         f"298={len(df_298)}, Tb={len(df_Tb)}。"
#         f"如果它们不是严格按同一物质顺序排列，需要改成按 ID merge。"
#     )
#
#
# # ============================================================
# # 主文件特征
# # ============================================================
# Nk_all = df_main.iloc[:, 13:32].apply(pd.to_numeric, errors="coerce").values
# Tb_raw_all = pd.to_numeric(df_main.iloc[:, 5], errors="coerce").values
# MW_all = pd.to_numeric(df_main.iloc[:, 4], errors="coerce").values.reshape(-1, 1)
# Nc_all = pd.to_numeric(df_main.iloc[:, 10], errors="coerce").values.reshape(-1, 1)
#
# T_all = df_main.iloc[:, 32:42].apply(pd.to_numeric, errors="coerce").values
# Hvap_all = df_main.iloc[:, 42:52].apply(pd.to_numeric, errors="coerce").values
#
# compound_ids_all = df_main.iloc[:, 0].values
#
#
# # ============================================================
# # 298K 与 Tb 点数据
# # ============================================================
# target_298 = "Heat of vaporization at normal temperature"
# target_tb = "Heat of vaporization at boiling temperature"
#
# X_298_all = df_298.drop(columns=[target_298]).apply(pd.to_numeric, errors="coerce")
# y_298_all = pd.to_numeric(df_298[target_298], errors="coerce").values
#
# X_Tb_all = df_Tb.drop(columns=[target_tb]).apply(pd.to_numeric, errors="coerce")
# y_Tb_all = pd.to_numeric(df_Tb[target_tb], errors="coerce").values
#
#
# # ============================================================
# # 构造总有效掩码
# # ============================================================
# mask_tb = np.isfinite(Tb_raw_all)
#
# mask_hvap = np.isfinite(Hvap_all) & (Hvap_all > 0)
# mask_hvap = mask_hvap.all(axis=1)
#
# mask_main_features = (
#     np.isfinite(Nk_all).all(axis=1)
#     & np.isfinite(MW_all).flatten()
#     & np.isfinite(Nc_all).flatten()
#     & np.isfinite(T_all).all(axis=1)
# )
#
# mask_298 = (
#     np.isfinite(y_298_all)
#     & np.isfinite(X_298_all).all(axis=1)
# )
#
# mask_tbpoint = (
#     np.isfinite(y_Tb_all)
#     & np.isfinite(X_Tb_all).all(axis=1)
# )
#
# master_mask = (
#     mask_tb
#     & mask_hvap
#     & mask_main_features
#     & mask_298
#     & mask_tbpoint
# )
#
#
# # ============================================================
# # 应用有效掩码
# # ============================================================
# df_main_valid = df_main.loc[master_mask].copy().reset_index(drop=True)
#
# Nk_valid = Nk_all[master_mask]
# Tb_raw_valid = Tb_raw_all[master_mask]
# MW_valid = MW_all[master_mask]
# Nc_valid = Nc_all[master_mask]
# T_valid_full = T_all[master_mask]
# Hvap_valid = Hvap_all[master_mask]
# compound_ids_valid = compound_ids_all[master_mask]
#
# X_298_valid = X_298_all.loc[master_mask].reset_index(drop=True)
# y_298_valid = y_298_all[master_mask]
#
# X_Tb_valid = X_Tb_all.loc[master_mask].reset_index(drop=True)
# y_Tb_valid = y_Tb_all[master_mask]
#
# print("========== 数据清洗后 ==========")
# print(f"有效物质数: {len(df_main_valid)}")
#
#
# # ============================================================
# # 按物质 8:2 划分
# # ============================================================
# indices = np.arange(len(df_main_valid))
#
# train_idx, test_idx = train_test_split(
#     indices,
#     test_size=0.2,
#     random_state=42
# )
#
# print("========== 按物质划分 ==========")
# print(f"训练集物质数: {len(train_idx)}")
# print(f"测试集物质数: {len(test_idx)}")
#
#
# # ============================================================
# # 子集切分
# # ============================================================
# Nk_train, Nk_test = Nk_valid[train_idx], Nk_valid[test_idx]
#
# Tb_raw_train = Tb_raw_valid[train_idx]
# Tb_raw_test = Tb_raw_valid[test_idx]
#
# MW_train, MW_test = MW_valid[train_idx], MW_valid[test_idx]
# Nc_train, Nc_test = Nc_valid[train_idx], Nc_valid[test_idx]
#
# T_train_raw = T_valid_full[train_idx]
# T_test_raw = T_valid_full[test_idx]
#
# Hvap_train_raw = Hvap_valid[train_idx]
# Hvap_test_raw = Hvap_valid[test_idx]
#
# id_train_raw = compound_ids_valid[train_idx]
# id_test_raw = compound_ids_valid[test_idx]
#
# X_298_train = X_298_valid.iloc[train_idx].copy()
# X_298_test = X_298_valid.iloc[test_idx].copy()
#
# y_298_train = y_298_valid[train_idx]
# y_298_test = y_298_valid[test_idx]
#
# X_Tb_train = X_Tb_valid.iloc[train_idx].copy()
# X_Tb_test = X_Tb_valid.iloc[test_idx].copy()
#
# y_Tb_train = y_Tb_valid[train_idx]
# y_Tb_test = y_Tb_valid[test_idx]
#
#
# # ============================================================
# # Nk 多项式特征，只在训练集 fit
# # ============================================================
# poly = PolynomialFeatures(degree=2, include_bias=False)
#
# Nk_poly_train = poly.fit_transform(Nk_train)
# Nk_poly_test = poly.transform(Nk_test)
#
#
# # ============================================================
# # Tb 子模型
# # ============================================================
# model_Tb = HuberRegressor(max_iter=10000)
#
# model_Tb.fit(
#     Nk_poly_train,
#     np.exp(Tb_raw_train / Tb0)
# )
#
# Tb_pred_train = Tb0 * np.log(
#     np.clip(model_Tb.predict(Nk_poly_train), 1e-6, None)
# )
#
# Tb_pred_test = Tb0 * np.log(
#     np.clip(model_Tb.predict(Nk_poly_test), 1e-6, None)
# )
#
# tb_metrics_train = evaluate_metrics(
#     Tb_raw_train,
#     Tb_pred_train,
#     "Tb_submodel - train"
# )
#
# tb_metrics_test = evaluate_metrics(
#     Tb_raw_test,
#     Tb_pred_test,
#     "Tb_submodel - test"
# )
#
#
# # ============================================================
# # HVap_298 子模型
# # ============================================================
# rf_298 = RandomForestRegressor(
#     n_estimators=300,
#     random_state=42,
#     n_jobs=-1
# )
#
# rf_298.fit(X_298_train, y_298_train)
#
# HVap_298_pred_train = rf_298.predict(X_298_train)
# HVap_298_pred_test = rf_298.predict(X_298_test)
#
# hv298_metrics_train = evaluate_metrics(
#     y_298_train,
#     HVap_298_pred_train,
#     "HVap_298_submodel - train"
# )
#
# hv298_metrics_test = evaluate_metrics(
#     y_298_test,
#     HVap_298_pred_test,
#     "HVap_298_submodel - test"
# )
#
#
# # ============================================================
# # HVap_Tb 子模型
# # ============================================================
# rf_Tb = RandomForestRegressor(
#     n_estimators=300,
#     random_state=42,
#     n_jobs=-1
# )
#
# rf_Tb.fit(X_Tb_train, y_Tb_train)
#
# HVap_Tb_pred_train = rf_Tb.predict(X_Tb_train)
# HVap_Tb_pred_test = rf_Tb.predict(X_Tb_test)
#
# hvtb_metrics_train = evaluate_metrics(
#     y_Tb_train,
#     HVap_Tb_pred_train,
#     "HVap_Tb_submodel - train"
# )
#
# hvtb_metrics_test = evaluate_metrics(
#     y_Tb_test,
#     HVap_Tb_pred_test,
#     "HVap_Tb_submodel - test"
# )
#
#
# # ============================================================
# # slope 特征
# # ============================================================
# def build_slope(hvap_tb_pred, hvap_298_pred, tb_pred):
#     denom = tb_pred - T_ref
#
#     slope = np.full_like(tb_pred, np.nan, dtype=float)
#
#     valid = (
#         np.isfinite(hvap_tb_pred)
#         & np.isfinite(hvap_298_pred)
#         & np.isfinite(tb_pred)
#         & (np.abs(denom) > 1e-12)
#     )
#
#     slope[valid] = (
#         hvap_tb_pred[valid] - hvap_298_pred[valid]
#     ) / denom[valid]
#
#     return slope.reshape(-1, 1)
#
#
# slope_train = build_slope(
#     HVap_Tb_pred_train,
#     HVap_298_pred_train,
#     Tb_pred_train
# )
#
# slope_test = build_slope(
#     HVap_Tb_pred_test,
#     HVap_298_pred_test,
#     Tb_pred_test
# )
#
#
# # ============================================================
# # 构造最终 RF 点级数据
# # ============================================================
# def build_point_dataset(Nk, MW, Nc, T, Hvap, slope, compound_ids):
#     """
#     最终 RF 特征：
#     19个基团 + MW + Nc + T + slope
#
#     与不加 slope 的版本相比，这里最后多了一列 slope。
#     """
#
#     X = np.hstack([
#         Nk.repeat(10, axis=0),
#         MW.repeat(10, axis=0),
#         Nc.repeat(10, axis=0),
#         T.flatten().reshape(-1, 1),
#         slope.repeat(10, axis=0)
#     ])
#
#     y = Hvap.flatten()
#
#     expanded_ids = np.repeat(compound_ids, 10)
#     expanded_T = T.flatten()
#
#     mask = (
#         np.isfinite(y)
#         & np.isfinite(X).all(axis=1)
#     )
#
#     return (
#         X[mask],
#         y[mask],
#         expanded_ids[mask],
#         expanded_T[mask]
#     )
#
#
# X_train, y_train, id_train, T_train = build_point_dataset(
#     Nk_train,
#     MW_train,
#     Nc_train,
#     T_train_raw,
#     Hvap_train_raw,
#     slope_train,
#     id_train_raw
# )
#
# X_test, y_test, id_test, T_test = build_point_dataset(
#     Nk_test,
#     MW_test,
#     Nc_test,
#     T_test_raw,
#     Hvap_test_raw,
#     slope_test,
#     id_test_raw
# )
#
# print("\n========== 最终 RF 主模型点级数据 ==========")
# print(f"训练集样本点数: {len(X_train)}")
# print(f"测试集样本点数: {len(X_test)}")
# print(f"最终模型特征数: {X_train.shape[1]}")
#
# if X_train.shape[1] != 23:
#     raise ValueError(
#         f"当前特征数为 {X_train.shape[1]}，预期为 23："
#         f"19个基团 + MW + Nc + T + slope。"
#     )
#
#
# # ============================================================
# # 最终 RF 主模型
# # ============================================================
# final_rf = RandomForestRegressor(
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
# final_rf.fit(X_train, y_train)
#
# y_train_pred = final_rf.predict(X_train)
# y_test_pred = final_rf.predict(X_test)
#
#
# # ============================================================
# # 最终 RF 主模型评估
# # ============================================================
# train_metrics = evaluate_metrics(
#     y_train,
#     y_train_pred,
#     "Final_RF_with_slope - train"
# )
#
# test_metrics = evaluate_metrics(
#     y_test,
#     y_test_pred,
#     "Final_RF_with_slope - test"
# )
#
#
# # ============================================================
# # 保存训练集结果
# # ============================================================
# df_train_result = pd.DataFrame({
#     "Set": "train",
#     "Compound_ID": id_train,
#     "Temperature (K)": T_train,
#     "Hvap_true (J/mol)": y_train,
#     "Hvap_pred (J/mol)": y_train_pred,
#     "Absolute Error": np.abs(y_train - y_train_pred),
#     "Relative Error (%)": train_metrics["relative_error"]
# })
#
#
# # ============================================================
# # 保存测试集结果
# # ============================================================
# df_test_result = pd.DataFrame({
#     "Set": "test",
#     "Compound_ID": id_test,
#     "Temperature (K)": T_test,
#     "Hvap_true (J/mol)": y_test,
#     "Hvap_pred (J/mol)": y_test_pred,
#     "Absolute Error": np.abs(y_test - y_test_pred),
#     "Relative Error (%)": test_metrics["relative_error"]
# })
#
#
# # ============================================================
# # 保存最终模型结果
# # ============================================================
# df_result = pd.concat(
#     [df_train_result, df_test_result],
#     axis=0
# ).reset_index(drop=True)
#
# result_file = "Hvap_RF_with_slope_prediction_by_material.xlsx"
#
# df_result.to_excel(
#     result_file,
#     index=False
# )
#
#
# # ============================================================
# # 保存最终主模型汇总
# # ============================================================
# summary_df = pd.DataFrame([
#     [
#         "Final_RF_with_slope",
#         "train",
#         train_metrics["R2"],
#         train_metrics["MSE"],
#         train_metrics["ARD_%"],
#         train_metrics["within_1pct"],
#         train_metrics["within_5pct"],
#         train_metrics["within_10pct"]
#     ],
#     [
#         "Final_RF_with_slope",
#         "test",
#         test_metrics["R2"],
#         test_metrics["MSE"],
#         test_metrics["ARD_%"],
#         test_metrics["within_1pct"],
#         test_metrics["within_5pct"],
#         test_metrics["within_10pct"]
#     ]
# ], columns=[
#     "Model",
#     "Dataset",
#     "R2",
#     "MSE",
#     "ARD_%",
#     "within_1pct",
#     "within_5pct",
#     "within_10pct"
# ])
#
# summary_file = "Hvap_RF_with_slope_summary_by_material.xlsx"
#
# summary_df.to_excel(
#     summary_file,
#     index=False
# )
#
#
# # ============================================================
# # 保存子模型汇总
# # ============================================================
# submodel_summary_df = pd.DataFrame([
#     [
#         "Tb_submodel",
#         "train",
#         tb_metrics_train["R2"],
#         tb_metrics_train["MSE"],
#         tb_metrics_train["ARD_%"],
#         tb_metrics_train["within_1pct"],
#         tb_metrics_train["within_5pct"],
#         tb_metrics_train["within_10pct"]
#     ],
#     [
#         "Tb_submodel",
#         "test",
#         tb_metrics_test["R2"],
#         tb_metrics_test["MSE"],
#         tb_metrics_test["ARD_%"],
#         tb_metrics_test["within_1pct"],
#         tb_metrics_test["within_5pct"],
#         tb_metrics_test["within_10pct"]
#     ],
#     [
#         "HVap_298_submodel",
#         "train",
#         hv298_metrics_train["R2"],
#         hv298_metrics_train["MSE"],
#         hv298_metrics_train["ARD_%"],
#         hv298_metrics_train["within_1pct"],
#         hv298_metrics_train["within_5pct"],
#         hv298_metrics_train["within_10pct"]
#     ],
#     [
#         "HVap_298_submodel",
#         "test",
#         hv298_metrics_test["R2"],
#         hv298_metrics_test["MSE"],
#         hv298_metrics_test["ARD_%"],
#         hv298_metrics_test["within_1pct"],
#         hv298_metrics_test["within_5pct"],
#         hv298_metrics_test["within_10pct"]
#     ],
#     [
#         "HVap_Tb_submodel",
#         "train",
#         hvtb_metrics_train["R2"],
#         hvtb_metrics_train["MSE"],
#         hvtb_metrics_train["ARD_%"],
#         hvtb_metrics_train["within_1pct"],
#         hvtb_metrics_train["within_5pct"],
#         hvtb_metrics_train["within_10pct"]
#     ],
#     [
#         "HVap_Tb_submodel",
#         "test",
#         hvtb_metrics_test["R2"],
#         hvtb_metrics_test["MSE"],
#         hvtb_metrics_test["ARD_%"],
#         hvtb_metrics_test["within_1pct"],
#         hvtb_metrics_test["within_5pct"],
#         hvtb_metrics_test["within_10pct"]
#     ],
# ], columns=[
#     "Model",
#     "Dataset",
#     "R2",
#     "MSE",
#     "ARD_%",
#     "within_1pct",
#     "within_5pct",
#     "within_10pct"
# ])
#
# submodel_summary_file = "Hvap_RF_with_slope_submodel_summary.xlsx"
#
# submodel_summary_df.to_excel(
#     submodel_summary_file,
#     index=False
# )
#
#
# # ============================================================
# # 保存 slope 表，方便和无 slope 版本对比
# # ============================================================
# slope_df = pd.DataFrame({
#     "Set": ["train"] * len(id_train_raw) + ["test"] * len(id_test_raw),
#     "Compound_ID": np.concatenate([id_train_raw, id_test_raw]),
#     "Tb_pred": np.concatenate([Tb_pred_train, Tb_pred_test]),
#     "HVap_298_pred": np.concatenate([HVap_298_pred_train, HVap_298_pred_test]),
#     "HVap_Tb_pred": np.concatenate([HVap_Tb_pred_train, HVap_Tb_pred_test]),
#     "slope": np.concatenate([slope_train.flatten(), slope_test.flatten()])
# })
#
# slope_file = "Hvap_RF_with_slope_values.xlsx"
#
# slope_df.to_excel(
#     slope_file,
#     index=False
# )
#
#
# # ============================================================
# # 保存特征重要性
# # ============================================================
# feature_names = (
#     [f"Group_{i + 1}" for i in range(19)]
#     + ["MW", "Nc", "Temperature", "slope"]
# )
#
# feature_importance_df = pd.DataFrame({
#     "Feature": feature_names,
#     "Importance": final_rf.feature_importances_
# }).sort_values(by="Importance", ascending=False)
#
# importance_file = "Hvap_RF_with_slope_feature_importance.xlsx"
#
# feature_importance_df.to_excel(
#     importance_file,
#     index=False
# )
#
#
# print(f"\n预测结果已保存为: {result_file}")
# print(f"主模型汇总已保存为: {summary_file}")
# print(f"子模型汇总已保存为: {submodel_summary_file}")
# print(f"slope 值已保存为: {slope_file}")
# print(f"特征重要性已保存为: {importance_file}")


import pandas as pd
import numpy as np

from sklearn.linear_model import HuberRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import PolynomialFeatures
from sklearn.model_selection import train_test_split


# ============================================================
# 常数与路径
# ============================================================
HV0, HVB, Tb0 = 9612.7, 15419.9, 222.543
T_ref = 298.15

main_file = "heat of vaporization 204.xlsx"
file_298 = "selected_25_descriptors_data_298.xlsx"
file_tb = "selected_25_descriptors_data_boiling_point.xlsx"


# ============================================================
# 通用评估函数
# ============================================================
def evaluate_metrics(y_true, y_pred, name="模型", strict_less=False):
    y_true = np.asarray(y_true, dtype=float).flatten()
    y_pred = np.asarray(y_pred, dtype=float).flatten()

    original_len = len(y_true)

    finite_mask = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true_valid = y_true[finite_mask]
    y_pred_valid = y_pred[finite_mask]

    relative_error_full = np.full(original_len, np.nan, dtype=float)

    if len(y_true_valid) == 0:
        print(f"\n{name} 无有效样本")
        return {
            "Model": name,
            "R2": np.nan,
            "MSE": np.nan,
            "ARD_%": np.nan,
            "within_1pct": 0,
            "within_5pct": 0,
            "within_10pct": 0,
            "relative_error": relative_error_full
        }

    mse = mean_squared_error(y_true_valid, y_pred_valid)
    r2 = r2_score(y_true_valid, y_pred_valid)

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

    relative_error_full[finite_mask] = relative_error_valid

    if strict_less:
        within_1pct = np.sum(relative_error_valid < 1)
        within_5pct = np.sum(relative_error_valid < 5)
        within_10pct = np.sum(relative_error_valid < 10)
    else:
        within_1pct = np.sum(relative_error_valid <= 1)
        within_5pct = np.sum(relative_error_valid <= 5)
        within_10pct = np.sum(relative_error_valid <= 10)

    print(f"\n{name}评估结果:")
    print(f"R2  = {r2:.6f}")
    print(f"MSE = {mse:.6f}")
    print(f"ARD = {ard:.2f}%")

    if strict_less:
        print(f"相对误差 < 1% 的点数: {within_1pct}")
        print(f"相对误差 < 5% 的点数: {within_5pct}")
        print(f"相对误差 < 10% 的点数: {within_10pct}")
    else:
        print(f"相对误差 <= 1% 的点数: {within_1pct}")
        print(f"相对误差 <= 5% 的点数: {within_5pct}")
        print(f"相对误差 <= 10% 的点数: {within_10pct}")

    return {
        "Model": name,
        "R2": r2,
        "MSE": mse,
        "ARD_%": ard,
        "within_1pct": within_1pct,
        "within_5pct": within_5pct,
        "within_10pct": within_10pct,
        "relative_error": relative_error_full
    }


# ============================================================
# 读取数据
# ============================================================
df_main = pd.read_excel(main_file, sheet_name="Sheet1")
df_298 = pd.read_excel(file_298)
df_Tb = pd.read_excel(file_tb)

id_col = df_main.columns[0]

if not (len(df_main) == len(df_298) == len(df_Tb)):
    raise ValueError(
        f"三个文件行数不一致：main={len(df_main)}, "
        f"298={len(df_298)}, Tb={len(df_Tb)}。"
        f"如果它们不是严格按同一物质顺序排列，需要改成按 ID merge。"
    )


# ============================================================
# 主文件特征
# ============================================================
Nk_all = df_main.iloc[:, 13:32].apply(pd.to_numeric, errors="coerce").values
Tb_raw_all = pd.to_numeric(df_main.iloc[:, 5], errors="coerce").values
MW_all = pd.to_numeric(df_main.iloc[:, 4], errors="coerce").values.reshape(-1, 1)
Nc_all = pd.to_numeric(df_main.iloc[:, 10], errors="coerce").values.reshape(-1, 1)

T_all = df_main.iloc[:, 32:42].apply(pd.to_numeric, errors="coerce").values
Hvap_all = df_main.iloc[:, 42:52].apply(pd.to_numeric, errors="coerce").values

compound_ids_all = df_main.iloc[:, 0].values


# ============================================================
# 298K 与 Tb 点数据
# ============================================================
target_298 = "Heat of vaporization at normal temperature"
target_tb = "Heat of vaporization at boiling temperature"

X_298_all = df_298.drop(columns=[target_298]).apply(pd.to_numeric, errors="coerce")
y_298_all = pd.to_numeric(df_298[target_298], errors="coerce").values

X_Tb_all = df_Tb.drop(columns=[target_tb]).apply(pd.to_numeric, errors="coerce")
y_Tb_all = pd.to_numeric(df_Tb[target_tb], errors="coerce").values


# ============================================================
# 构造总有效掩码
# ============================================================
mask_tb = np.isfinite(Tb_raw_all)

mask_hvap = np.isfinite(Hvap_all) & (Hvap_all > 0)
mask_hvap = mask_hvap.all(axis=1)

mask_main_features = (
    np.isfinite(Nk_all).all(axis=1)
    & np.isfinite(MW_all).flatten()
    & np.isfinite(Nc_all).flatten()
    & np.isfinite(T_all).all(axis=1)
)

mask_298 = (
    np.isfinite(y_298_all)
    & np.isfinite(X_298_all).all(axis=1)
)

mask_tbpoint = (
    np.isfinite(y_Tb_all)
    & np.isfinite(X_Tb_all).all(axis=1)
)

master_mask = (
    mask_tb
    & mask_hvap
    & mask_main_features
    & mask_298
    & mask_tbpoint
)


# ============================================================
# 应用有效掩码
# ============================================================
df_main_valid = df_main.loc[master_mask].copy().reset_index(drop=True)

Nk_valid = Nk_all[master_mask]
Tb_raw_valid = Tb_raw_all[master_mask]
MW_valid = MW_all[master_mask]
Nc_valid = Nc_all[master_mask]
T_valid_full = T_all[master_mask]
Hvap_valid = Hvap_all[master_mask]
compound_ids_valid = compound_ids_all[master_mask]

X_298_valid = X_298_all.loc[master_mask].reset_index(drop=True)
y_298_valid = y_298_all[master_mask]

X_Tb_valid = X_Tb_all.loc[master_mask].reset_index(drop=True)
y_Tb_valid = y_Tb_all[master_mask]

print("========== 数据清洗后 ==========")
print(f"有效物质数: {len(df_main_valid)}")


# ============================================================
# 按物质 8:2 划分
# ============================================================
indices = np.arange(len(df_main_valid))

train_idx, test_idx = train_test_split(
    indices,
    test_size=0.2,
    random_state=42
)

print("========== 按物质划分 ==========")
print(f"训练集物质数: {len(train_idx)}")
print(f"测试集物质数: {len(test_idx)}")


# ============================================================
# 子集切分
# ============================================================
Nk_train, Nk_test = Nk_valid[train_idx], Nk_valid[test_idx]

Tb_raw_train = Tb_raw_valid[train_idx]
Tb_raw_test = Tb_raw_valid[test_idx]

MW_train, MW_test = MW_valid[train_idx], MW_valid[test_idx]
Nc_train, Nc_test = Nc_valid[train_idx], Nc_valid[test_idx]

T_train_raw = T_valid_full[train_idx]
T_test_raw = T_valid_full[test_idx]

Hvap_train_raw = Hvap_valid[train_idx]
Hvap_test_raw = Hvap_valid[test_idx]

id_train_raw = compound_ids_valid[train_idx]
id_test_raw = compound_ids_valid[test_idx]

X_298_train = X_298_valid.iloc[train_idx].copy()
X_298_test = X_298_valid.iloc[test_idx].copy()

y_298_train = y_298_valid[train_idx]
y_298_test = y_298_valid[test_idx]

X_Tb_train = X_Tb_valid.iloc[train_idx].copy()
X_Tb_test = X_Tb_valid.iloc[test_idx].copy()

y_Tb_train = y_Tb_valid[train_idx]
y_Tb_test = y_Tb_valid[test_idx]


# ============================================================
# Nk 多项式特征，只在训练集 fit
# ============================================================
poly = PolynomialFeatures(degree=2, include_bias=False)

Nk_poly_train = poly.fit_transform(Nk_train)
Nk_poly_test = poly.transform(Nk_test)


# ============================================================
# Tb 子模型
# ============================================================
model_Tb = HuberRegressor(max_iter=10000)

model_Tb.fit(
    Nk_poly_train,
    np.exp(Tb_raw_train / Tb0)
)

Tb_pred_train = Tb0 * np.log(
    np.clip(model_Tb.predict(Nk_poly_train), 1e-6, None)
)

Tb_pred_test = Tb0 * np.log(
    np.clip(model_Tb.predict(Nk_poly_test), 1e-6, None)
)

tb_metrics_train = evaluate_metrics(
    Tb_raw_train,
    Tb_pred_train,
    "Tb_submodel - train",
    strict_less=False
)

tb_metrics_test = evaluate_metrics(
    Tb_raw_test,
    Tb_pred_test,
    "Tb_submodel - test",
    strict_less=False
)


# ============================================================
# HVap_298 子模型
# ============================================================
rf_298 = RandomForestRegressor(
    n_estimators=300,
    random_state=42,
    n_jobs=-1
)

rf_298.fit(X_298_train, y_298_train)

HVap_298_pred_train = rf_298.predict(X_298_train)
HVap_298_pred_test = rf_298.predict(X_298_test)

hv298_metrics_train = evaluate_metrics(
    y_298_train,
    HVap_298_pred_train,
    "HVap_298_submodel - train",
    strict_less=False
)

hv298_metrics_test = evaluate_metrics(
    y_298_test,
    HVap_298_pred_test,
    "HVap_298_submodel - test",
    strict_less=False
)


# ============================================================
# HVap_Tb 子模型
# ============================================================
rf_Tb = RandomForestRegressor(
    n_estimators=300,
    random_state=42,
    n_jobs=-1
)

rf_Tb.fit(X_Tb_train, y_Tb_train)

HVap_Tb_pred_train = rf_Tb.predict(X_Tb_train)
HVap_Tb_pred_test = rf_Tb.predict(X_Tb_test)

hvtb_metrics_train = evaluate_metrics(
    y_Tb_train,
    HVap_Tb_pred_train,
    "HVap_Tb_submodel - train",
    strict_less=False
)

hvtb_metrics_test = evaluate_metrics(
    y_Tb_test,
    HVap_Tb_pred_test,
    "HVap_Tb_submodel - test",
    strict_less=False
)


# ============================================================
# slope 特征
# ============================================================
def build_slope(hvap_tb_pred, hvap_298_pred, tb_pred):
    denom = tb_pred - T_ref

    slope = np.full_like(tb_pred, np.nan, dtype=float)

    valid = (
        np.isfinite(hvap_tb_pred)
        & np.isfinite(hvap_298_pred)
        & np.isfinite(tb_pred)
        & (np.abs(denom) > 1e-12)
    )

    slope[valid] = (
        hvap_tb_pred[valid] - hvap_298_pred[valid]
    ) / denom[valid]

    return slope.reshape(-1, 1)


slope_train = build_slope(
    HVap_Tb_pred_train,
    HVap_298_pred_train,
    Tb_pred_train
)

slope_test = build_slope(
    HVap_Tb_pred_test,
    HVap_298_pred_test,
    Tb_pred_test
)


# ============================================================
# 构造最终 RF 点级数据
# ============================================================
def build_point_dataset(Nk, MW, Nc, T, Hvap, slope, compound_ids):
    """
    最终 RF 特征：
    19个基团 + MW + Nc + T + slope
    """

    X = np.hstack([
        Nk.repeat(10, axis=0),
        MW.repeat(10, axis=0),
        Nc.repeat(10, axis=0),
        T.flatten().reshape(-1, 1),
        slope.repeat(10, axis=0)
    ])

    y = Hvap.flatten()

    expanded_ids = np.repeat(compound_ids, 10)
    expanded_T = T.flatten()
    expanded_slope = slope.repeat(10, axis=0).flatten()

    mask = (
        np.isfinite(y)
        & np.isfinite(X).all(axis=1)
    )

    return (
        X[mask],
        y[mask],
        expanded_ids[mask],
        expanded_T[mask],
        expanded_slope[mask]
    )


X_train, y_train, id_train, T_train, slope_point_train = build_point_dataset(
    Nk_train,
    MW_train,
    Nc_train,
    T_train_raw,
    Hvap_train_raw,
    slope_train,
    id_train_raw
)

X_test, y_test, id_test, T_test, slope_point_test = build_point_dataset(
    Nk_test,
    MW_test,
    Nc_test,
    T_test_raw,
    Hvap_test_raw,
    slope_test,
    id_test_raw
)

print("\n========== 最终 RF 主模型点级数据 ==========")
print(f"训练集样本点数: {len(X_train)}")
print(f"测试集样本点数: {len(X_test)}")
print(f"最终模型特征数: {X_train.shape[1]}")

if X_train.shape[1] != 23:
    raise ValueError(
        f"当前特征数为 {X_train.shape[1]}，预期为 23："
        f"19个基团 + MW + Nc + T + slope。"
    )


# ============================================================
# 最终 RF 主模型
# ============================================================
final_rf = RandomForestRegressor(
    n_estimators=500,
    max_depth=None,
    min_samples_split=2,
    min_samples_leaf=1,
    max_features="sqrt",
    bootstrap=True,
    random_state=42,
    n_jobs=-1
)

final_rf.fit(X_train, y_train)

y_train_pred = final_rf.predict(X_train)
y_test_pred = final_rf.predict(X_test)


# ============================================================
# 最终 RF 主模型评估
# ============================================================
train_metrics = evaluate_metrics(
    y_train,
    y_train_pred,
    "Final_RF_with_slope - train",
    strict_less=False
)

test_metrics = evaluate_metrics(
    y_test,
    y_test_pred,
    "Final_RF_with_slope - test",
    strict_less=False
)


# ============================================================
# 完整数据集统计：训练集 + 测试集
# ============================================================
X_all = np.vstack([
    X_train,
    X_test
])

y_all = np.concatenate([
    y_train,
    y_test
])

y_all_pred = np.concatenate([
    y_train_pred,
    y_test_pred
])

id_all = np.concatenate([
    id_train,
    id_test
])

T_all_used = np.concatenate([
    T_train,
    T_test
])

slope_point_all = np.concatenate([
    slope_point_train,
    slope_point_test
])

all_metrics = evaluate_metrics(
    y_all,
    y_all_pred,
    "Final_RF_with_slope - all_train_plus_test",
    strict_less=True
)

print("\nFinal_RF_with_slope 完整数据集 Hvap 预测偏差 1%，5%，10%分别为：")
print(all_metrics["within_1pct"])
print(all_metrics["within_5pct"])
print(all_metrics["within_10pct"])


# ============================================================
# 保存训练集结果
# ============================================================
df_train_result = pd.DataFrame({
    "Set": "train",
    "Compound_ID": id_train,
    "Temperature (K)": T_train,
    "slope": slope_point_train,
    "Hvap_true (J/mol)": y_train,
    "Hvap_pred (J/mol)": y_train_pred,
    "Absolute Error": np.abs(y_train - y_train_pred),
    "Relative Error (%)": train_metrics["relative_error"]
})


# ============================================================
# 保存测试集结果
# ============================================================
df_test_result = pd.DataFrame({
    "Set": "test",
    "Compound_ID": id_test,
    "Temperature (K)": T_test,
    "slope": slope_point_test,
    "Hvap_true (J/mol)": y_test,
    "Hvap_pred (J/mol)": y_test_pred,
    "Absolute Error": np.abs(y_test - y_test_pred),
    "Relative Error (%)": test_metrics["relative_error"]
})


# ============================================================
# 保存完整数据集结果
# ============================================================
df_all_result = pd.DataFrame({
    "Set": "all_train_plus_test",
    "Compound_ID": id_all,
    "Temperature (K)": T_all_used,
    "slope": slope_point_all,
    "Hvap_true (J/mol)": y_all,
    "Hvap_pred (J/mol)": y_all_pred,
    "Absolute Error": np.abs(y_all - y_all_pred),
    "Relative Error (%)": all_metrics["relative_error"]
})


# ============================================================
# 保存最终模型结果
# ============================================================
result_file = "Hvap_RF_with_slope_prediction_by_material.xlsx"

with pd.ExcelWriter(result_file, engine="xlsxwriter") as writer:
    pd.concat(
        [df_train_result, df_test_result],
        axis=0,
        ignore_index=True
    ).to_excel(
        writer,
        sheet_name="train_test_predictions",
        index=False
    )

    df_all_result.to_excel(
        writer,
        sheet_name="all_predictions",
        index=False
    )


# ============================================================
# 保存最终主模型汇总
# ============================================================
summary_df = pd.DataFrame([
    [
        "Final_RF_with_slope",
        "train",
        train_metrics["R2"],
        train_metrics["MSE"],
        train_metrics["ARD_%"],
        train_metrics["within_1pct"],
        train_metrics["within_5pct"],
        train_metrics["within_10pct"]
    ],
    [
        "Final_RF_with_slope",
        "test",
        test_metrics["R2"],
        test_metrics["MSE"],
        test_metrics["ARD_%"],
        test_metrics["within_1pct"],
        test_metrics["within_5pct"],
        test_metrics["within_10pct"]
    ],
    [
        "Final_RF_with_slope",
        "all_train_plus_test",
        all_metrics["R2"],
        all_metrics["MSE"],
        all_metrics["ARD_%"],
        all_metrics["within_1pct"],
        all_metrics["within_5pct"],
        all_metrics["within_10pct"]
    ],
], columns=[
    "Model",
    "Dataset",
    "R2",
    "MSE",
    "ARD_%",
    "within_1pct",
    "within_5pct",
    "within_10pct"
])

summary_file = "Hvap_RF_with_slope_summary_by_material.xlsx"

summary_df.to_excel(
    summary_file,
    index=False
)


# ============================================================
# 保存子模型汇总
# ============================================================
submodel_summary_df = pd.DataFrame([
    [
        "Tb_submodel",
        "train",
        tb_metrics_train["R2"],
        tb_metrics_train["MSE"],
        tb_metrics_train["ARD_%"],
        tb_metrics_train["within_1pct"],
        tb_metrics_train["within_5pct"],
        tb_metrics_train["within_10pct"]
    ],
    [
        "Tb_submodel",
        "test",
        tb_metrics_test["R2"],
        tb_metrics_test["MSE"],
        tb_metrics_test["ARD_%"],
        tb_metrics_test["within_1pct"],
        tb_metrics_test["within_5pct"],
        tb_metrics_test["within_10pct"]
    ],
    [
        "HVap_298_submodel",
        "train",
        hv298_metrics_train["R2"],
        hv298_metrics_train["MSE"],
        hv298_metrics_train["ARD_%"],
        hv298_metrics_train["within_1pct"],
        hv298_metrics_train["within_5pct"],
        hv298_metrics_train["within_10pct"]
    ],
    [
        "HVap_298_submodel",
        "test",
        hv298_metrics_test["R2"],
        hv298_metrics_test["MSE"],
        hv298_metrics_test["ARD_%"],
        hv298_metrics_test["within_1pct"],
        hv298_metrics_test["within_5pct"],
        hv298_metrics_test["within_10pct"]
    ],
    [
        "HVap_Tb_submodel",
        "train",
        hvtb_metrics_train["R2"],
        hvtb_metrics_train["MSE"],
        hvtb_metrics_train["ARD_%"],
        hvtb_metrics_train["within_1pct"],
        hvtb_metrics_train["within_5pct"],
        hvtb_metrics_train["within_10pct"]
    ],
    [
        "HVap_Tb_submodel",
        "test",
        hvtb_metrics_test["R2"],
        hvtb_metrics_test["MSE"],
        hvtb_metrics_test["ARD_%"],
        hvtb_metrics_test["within_1pct"],
        hvtb_metrics_test["within_5pct"],
        hvtb_metrics_test["within_10pct"]
    ],
], columns=[
    "Model",
    "Dataset",
    "R2",
    "MSE",
    "ARD_%",
    "within_1pct",
    "within_5pct",
    "within_10pct"
])

submodel_summary_file = "Hvap_RF_with_slope_submodel_summary.xlsx"

submodel_summary_df.to_excel(
    submodel_summary_file,
    index=False
)


# ============================================================
# 保存 slope 表，方便和无 slope 版本对比
# ============================================================
slope_df = pd.DataFrame({
    "Set": ["train"] * len(id_train_raw) + ["test"] * len(id_test_raw),
    "Compound_ID": np.concatenate([id_train_raw, id_test_raw]),
    "Tb_pred": np.concatenate([Tb_pred_train, Tb_pred_test]),
    "HVap_298_pred": np.concatenate([HVap_298_pred_train, HVap_298_pred_test]),
    "HVap_Tb_pred": np.concatenate([HVap_Tb_pred_train, HVap_Tb_pred_test]),
    "slope": np.concatenate([slope_train.flatten(), slope_test.flatten()])
})

slope_file = "Hvap_RF_with_slope_values.xlsx"

slope_df.to_excel(
    slope_file,
    index=False
)


# ============================================================
# 保存特征重要性
# ============================================================
feature_names = (
    [f"Group_{i + 1}" for i in range(19)]
    + ["MW", "Nc", "Temperature", "slope"]
)

feature_importance_df = pd.DataFrame({
    "Feature": feature_names,
    "Importance": final_rf.feature_importances_
}).sort_values(by="Importance", ascending=False)

importance_file = "Hvap_RF_with_slope_feature_importance.xlsx"

feature_importance_df.to_excel(
    importance_file,
    index=False
)


print(f"\n预测结果已保存为: {result_file}")
print(f"主模型汇总已保存为: {summary_file}")
print(f"子模型汇总已保存为: {submodel_summary_file}")
print(f"slope 值已保存为: {slope_file}")
print(f"特征重要性已保存为: {importance_file}")


# ============================================================
# 输出模型结构记录
# ============================================================
print("\n当前 Hvap RF + slope 模型结构:")
print("Tb_submodel: HuberRegressor(max_iter=10000), input = PolynomialFeatures(Nk, degree=2)")
print("HVap_298_submodel: RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1), input = selected 25 descriptors at 298.15 K")
print("HVap_Tb_submodel: RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1), input = selected 25 descriptors at boiling point")
print("slope = (HVap_Tb_pred - HVap_298_pred) / (Tb_pred - 298.15)")
print("Final target: ordinary Hvap, not ln(Hvap)")
print("Final model: RandomForestRegressor(n_estimators=500, max_features='sqrt', bootstrap=True, random_state=42, n_jobs=-1)")
print("Final input features: 19 group counts + MW + Nc + Temperature + slope")
print("Final all-data statistics use strict thresholds: <1%, <5%, <10%")