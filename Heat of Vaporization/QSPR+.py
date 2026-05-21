# # import pandas as pd
# # import numpy as np
# #
# # from sklearn.ensemble import RandomForestRegressor
# # from sklearn.linear_model import HuberRegressor
# # from sklearn.preprocessing import PolynomialFeatures
# # from sklearn.model_selection import train_test_split
# # from sklearn.metrics import mean_squared_error, r2_score
# #
# #
# # # =========================================================
# # # 0. 文件路径
# # # =========================================================
# # main_file = "heat of vaporization 204.xlsx"
# # file_298 = "selected_25_descriptors_data_298.xlsx"
# # file_tb = "selected_25_descriptors_data_boiling_point.xlsx"
# # transformed_file = "Transformed_hv_Dataset.xlsx"
# #
# # slope_csv_out = "slope_values.csv"
# # merged_excel_out = "Transformed_hv_with_slope.xlsx"
# # prediction_out = "prediction_vs_actual_hv_with_slope_8to2.xlsx"
# # summary_out = "prediction_summary_hv_with_slope_8to2.xlsx"
# #
# #
# # # =========================================================
# # # 1. 先预测生成 slope
# # # =========================================================
# # print("========== 第1步：预测并生成 slope ==========")
# #
# # df = pd.read_excel(main_file, sheet_name="Sheet1").copy()
# #
# # # 物质ID、基团列
# # material_id_col = df.columns[0]
# # material_ids = df[material_id_col].values
# # Nk_all = df.iloc[:, 13:32].apply(pd.to_numeric, errors='coerce')  # 19个基团
# #
# # # ---- 1.1 训练 HVap_298 模型 ----
# # df_298 = pd.read_excel(file_298).copy()
# # target_298 = "Heat of vaporization at normal temperature"
# # X_298 = df_298.drop(columns=[target_298])
# # y_298 = df_298[target_298]
# #
# # for c in X_298.columns:
# #     X_298[c] = pd.to_numeric(X_298[c], errors="coerce")
# # y_298 = pd.to_numeric(y_298, errors="coerce")
# #
# # valid_298 = (~X_298.isna().any(axis=1)) & (~y_298.isna())
# # rf_298 = RandomForestRegressor(random_state=42, n_estimators=300, n_jobs=-1)
# # rf_298.fit(X_298.loc[valid_298], y_298.loc[valid_298])
# #
# # HVap_298_all = rf_298.predict(X_298.loc[valid_298])
# #
# # # ---- 1.2 训练 HVap_Tb 模型 ----
# # df_Tb = pd.read_excel(file_tb).copy()
# # target_Tb = "Heat of vaporization at boiling temperature"
# # X_Tb = df_Tb.drop(columns=[target_Tb])
# # y_Tb = df_Tb[target_Tb]
# #
# # for c in X_Tb.columns:
# #     X_Tb[c] = pd.to_numeric(X_Tb[c], errors="coerce")
# # y_Tb = pd.to_numeric(y_Tb, errors="coerce")
# #
# # valid_Tb = (~X_Tb.isna().any(axis=1)) & (~y_Tb.isna())
# # rf_Tb = RandomForestRegressor(random_state=42, n_estimators=300, n_jobs=-1)
# # rf_Tb.fit(X_Tb.loc[valid_Tb], y_Tb.loc[valid_Tb])
# #
# # HVap_Tb_all = rf_Tb.predict(X_Tb.loc[valid_Tb])
# #
# # # ---- 1.3 拟合 Tb 模型 ----
# # Tb_raw = pd.to_numeric(df.iloc[:, 5], errors="coerce").values
# # Tb0 = 222.543
# #
# # poly = PolynomialFeatures(degree=2, include_bias=False)
# # Nk_poly = poly.fit_transform(Nk_all.fillna(0))
# #
# # mask_tb = ~np.isnan(Tb_raw)
# #
# # model_Tb = HuberRegressor(max_iter=5000).fit(
# #     Nk_poly[mask_tb],
# #     np.exp(Tb_raw[mask_tb] / Tb0)
# # )
# #
# # Tb_pred_all = Tb0 * np.log(np.clip(model_Tb.predict(Nk_poly), 1e-6, None))
# #
# # # ---- 1.4 对齐长度并计算 slope ----
# # # 这里默认三个数据源顺序是一一对应的；如果不是，需要按 Material_ID 对齐
# # n_main = len(df)
# # n_298 = len(HVap_298_all)
# # n_tb = len(HVap_Tb_all)
# #
# # if not (n_298 == n_main and n_tb == n_main):
# #     # 尝试用“有效行长度最短值”截断，避免直接报错
# #     n = min(n_main, n_298, n_tb)
# #     print("⚠️ 警告：三个数据源长度不完全一致，已按最短长度截断。")
# #     material_ids_use = material_ids[:n]
# #     Tb_pred_use = Tb_pred_all[:n]
# #     HVap_298_use = HVap_298_all[:n]
# #     HVap_Tb_use = HVap_Tb_all[:n]
# # else:
# #     material_ids_use = material_ids
# #     Tb_pred_use = Tb_pred_all
# #     HVap_298_use = HVap_298_all
# #     HVap_Tb_use = HVap_Tb_all
# #
# # T_ref = 298.15
# # denominator = Tb_pred_use - T_ref
# #
# # # 避免分母太小
# # safe_mask = np.abs(denominator) > 1e-12
# # slope_all = np.full_like(Tb_pred_use, np.nan, dtype=float)
# # slope_all[safe_mask] = (HVap_Tb_use[safe_mask] - HVap_298_use[safe_mask]) / denominator[safe_mask]
# #
# # slope_df = pd.DataFrame({
# #     "Material_ID": material_ids_use,
# #     "slope": slope_all
# # })
# #
# # slope_df.to_csv(slope_csv_out, index=False)
# # print(f"✅ slope 已保存为: {slope_csv_out}")
# #
# #
# # # =========================================================
# # # 2. 将预测的 slope 合并到新的表格
# # # =========================================================
# # print("\n========== 第2步：合并 slope 到新表格 ==========")
# #
# # train_df = pd.read_excel(transformed_file).copy()
# #
# # if "Material_ID" in train_df.columns:
# #     # 优先按 Material_ID 合并
# #     train_df_with_slope = train_df.merge(slope_df, on="Material_ID", how="left")
# #     print("✅ 检测到 Material_ID，已按 Material_ID 合并 slope")
# # else:
# #     # 没有 Material_ID 时，使用你原来的 repeat(10) 方式
# #     slope_expanded = pd.DataFrame({
# #         "slope": slope_df["slope"].repeat(10).values[:len(train_df)]
# #     })
# #     train_df_with_slope = pd.concat(
# #         [train_df.reset_index(drop=True), slope_expanded.reset_index(drop=True)],
# #         axis=1
# #     )
# #     print("⚠️ 未检测到 Material_ID，已按 repeat(10) 方式拼接 slope。请确认行顺序完全对应。")
# #
# # train_df_with_slope.to_excel(merged_excel_out, index=False)
# # print(f"✅ 已成功保存为: {merged_excel_out}")
# #
# #
# # # =========================================================
# # # 3. 将 slope 作为额外输入特征融入模型，并做 8:2 划分
# # # =========================================================
# # print("\n========== 第3步：建模（8:2划分训练/测试集） ==========")
# #
# # df_model = train_df_with_slope.copy()
# #
# # target_col = "Heat of Vaporization"
# # if target_col not in df_model.columns:
# #     raise ValueError(f"找不到目标列: {target_col}")
# #
# # # 分离特征和目标
# # X = df_model.drop(columns=[target_col]).copy()
# # y = df_model[target_col].copy()
# #
# # # 数值化
# # for col in X.columns:
# #     X[col] = pd.to_numeric(X[col], errors="coerce")
# # y = pd.to_numeric(y, errors="coerce")
# #
# # # 删除含缺失的样本
# # valid_mask = (~X.isna().any(axis=1)) & (~y.isna())
# # X = X.loc[valid_mask].copy()
# # y = y.loc[valid_mask].copy()
# # df_model = df_model.loc[valid_mask].copy()
# #
# # print(f"总可用样本数: {len(X)}")
# #
# # # 8:2 划分
# # X_train, X_test, y_train, y_test, df_train_out, df_test_out = train_test_split(
# #     X, y, df_model,
# #     test_size=0.2,
# #     random_state=42
# # )
# #
# # print(f"训练集样本数: {len(X_train)}")
# # print(f"测试集样本数: {len(X_test)}")
# #
# # # 训练模型
# # model = RandomForestRegressor(
# #     random_state=42,
# #     n_estimators=300,
# #     n_jobs=-1
# # )
# # model.fit(X_train, y_train)
# #
# # # 训练集预测
# # y_train_pred = model.predict(X_train)
# #
# # # 测试集预测
# # y_test_pred = model.predict(X_test)
# #
# #
# # # =========================================================
# # # 4. 评估函数
# # # =========================================================
# # def evaluate_dataset(y_true, y_pred, name="数据集"):
# #     y_true = np.array(y_true, dtype=float)
# #     y_pred = np.array(y_pred, dtype=float)
# #
# #     r2 = r2_score(y_true, y_pred)
# #     mse = mean_squared_error(y_true, y_pred)
# #
# #     relative_error = np.full_like(y_true, np.nan, dtype=float)
# #     nonzero_mask = np.abs(y_true) > 1e-12
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
# #     print(f"\n📊 {name}评估结果：")
# #     print(f"R²  = {r2:.4f}")
# #     print(f"MSE = {mse:.4f}")
# #     print(f"ARD = {ard:.2f}%")
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
# #
# # # =========================================================
# # # 5. 输出训练集 / 测试集结果
# # # =========================================================
# # train_relative_error, train_summary = evaluate_dataset(y_train, y_train_pred, "训练集")
# # test_relative_error, test_summary = evaluate_dataset(y_test, y_test_pred, "测试集")
# #
# #
# # # =========================================================
# # # 6. 保存预测结果
# # # =========================================================
# # train_result = df_train_out.copy()
# # train_result["Set"] = "Train"
# # train_result["Predicted_Heat_of_Vaporization"] = y_train_pred
# # train_result["Absolute_Error"] = np.abs(y_train.values - y_train_pred)
# # train_result["Relative_Error (%)"] = train_relative_error
# #
# # test_result = df_test_out.copy()
# # test_result["Set"] = "Test"
# # test_result["Predicted_Heat_of_Vaporization"] = y_test_pred
# # test_result["Absolute_Error"] = np.abs(y_test.values - y_test_pred)
# # test_result["Relative_Error (%)"] = test_relative_error
# #
# # comparison_df = pd.concat([train_result, test_result], axis=0).reset_index(drop=True)
# # comparison_df.to_excel(prediction_out, index=False)
# # print(f"\n✅ 已保存预测结果为: {prediction_out}")
# #
# # summary_df = pd.DataFrame([train_summary, test_summary])
# # summary_df.to_excel(summary_out, index=False)
# # print(f"✅ 已保存评估汇总为: {summary_out}")
#
# import pandas as pd
# import numpy as np
#
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.linear_model import HuberRegressor
# from sklearn.preprocessing import PolynomialFeatures
# from sklearn.model_selection import train_test_split
# from sklearn.metrics import mean_squared_error, r2_score
#
#
# # =========================================================
# # 0. 文件路径
# # =========================================================
# main_file = "heat of vaporization 204.xlsx"
# file_298 = "selected_25_descriptors_data_298.xlsx"
# file_tb = "selected_25_descriptors_data_boiling_point.xlsx"
# transformed_file = "Transformed_hv_Dataset.xlsx"
#
# slope_csv_out = "slope_values.csv"
# merged_excel_out = "Transformed_hv_with_slope.xlsx"
# prediction_out = "prediction_vs_actual_hv_with_slope_by_material.xlsx"
# summary_out = "prediction_summary_hv_with_slope_by_material.xlsx"
#
#
# # =========================================================
# # 1. 先预测生成 slope
# # =========================================================
# print("========== 第1步：预测并生成 slope ==========")
#
# df = pd.read_excel(main_file, sheet_name="Sheet1").copy()
#
# material_id_col = df.columns[0]
# material_ids = df[material_id_col].values
# Nk_all = df.iloc[:, 13:32].apply(pd.to_numeric, errors='coerce')  # 19个基团
#
# # ---- 1.1 训练 HVap_298 模型 ----
# df_298 = pd.read_excel(file_298).copy()
# target_298 = "Heat of vaporization at normal temperature"
# X_298 = df_298.drop(columns=[target_298])
# y_298 = df_298[target_298]
#
# for c in X_298.columns:
#     X_298[c] = pd.to_numeric(X_298[c], errors="coerce")
# y_298 = pd.to_numeric(y_298, errors="coerce")
#
# valid_298 = (~X_298.isna().any(axis=1)) & (~y_298.isna())
# rf_298 = RandomForestRegressor(random_state=42, n_estimators=300, n_jobs=-1)
# rf_298.fit(X_298.loc[valid_298], y_298.loc[valid_298])
#
# HVap_298_all = rf_298.predict(X_298.loc[valid_298])
#
# # ---- 1.2 训练 HVap_Tb 模型 ----
# df_Tb = pd.read_excel(file_tb).copy()
# target_Tb = "Heat of vaporization at boiling temperature"
# X_Tb = df_Tb.drop(columns=[target_Tb])
# y_Tb = df_Tb[target_Tb]
#
# for c in X_Tb.columns:
#     X_Tb[c] = pd.to_numeric(X_Tb[c], errors="coerce")
# y_Tb = pd.to_numeric(y_Tb, errors="coerce")
#
# valid_Tb = (~X_Tb.isna().any(axis=1)) & (~y_Tb.isna())
# rf_Tb = RandomForestRegressor(random_state=42, n_estimators=300, n_jobs=-1)
# rf_Tb.fit(X_Tb.loc[valid_Tb], y_Tb.loc[valid_Tb])
#
# HVap_Tb_all = rf_Tb.predict(X_Tb.loc[valid_Tb])
#
# # ---- 1.3 拟合 Tb 模型 ----
# Tb_raw = pd.to_numeric(df.iloc[:, 5], errors="coerce").values
# Tb0 = 222.543
#
# poly = PolynomialFeatures(degree=2, include_bias=False)
# Nk_poly = poly.fit_transform(Nk_all.fillna(0))
#
# mask_tb = ~np.isnan(Tb_raw)
#
# model_Tb = HuberRegressor(max_iter=5000).fit(
#     Nk_poly[mask_tb],
#     np.exp(Tb_raw[mask_tb] / Tb0)
# )
#
# Tb_pred_all = Tb0 * np.log(np.clip(model_Tb.predict(Nk_poly), 1e-6, None))
#
# # ---- 1.4 对齐长度并计算 slope ----
# n_main = len(df)
# n_298 = len(HVap_298_all)
# n_tb = len(HVap_Tb_all)
#
# if not (n_298 == n_main and n_tb == n_main):
#     n = min(n_main, n_298, n_tb)
#     print("⚠️ 警告：三个数据源长度不完全一致，已按最短长度截断。")
#     material_ids_use = material_ids[:n]
#     Tb_pred_use = Tb_pred_all[:n]
#     HVap_298_use = HVap_298_all[:n]
#     HVap_Tb_use = HVap_Tb_all[:n]
# else:
#     material_ids_use = material_ids
#     Tb_pred_use = Tb_pred_all
#     HVap_298_use = HVap_298_all
#     HVap_Tb_use = HVap_Tb_all
#
# T_ref = 298.15
# denominator = Tb_pred_use - T_ref
#
# safe_mask = np.abs(denominator) > 1e-12
# slope_all = np.full_like(Tb_pred_use, np.nan, dtype=float)
# slope_all[safe_mask] = (HVap_Tb_use[safe_mask] - HVap_298_use[safe_mask]) / denominator[safe_mask]
#
# slope_df = pd.DataFrame({
#     "Material_ID": material_ids_use,
#     "slope": slope_all
# })
#
# slope_df.to_csv(slope_csv_out, index=False)
# print(f"✅ slope 已保存为: {slope_csv_out}")
#
#
# # =========================================================
# # 2. 将预测的 slope 合并到新的表格
# # =========================================================
# print("\n========== 第2步：合并 slope 到新表格 ==========")
#
# train_df = pd.read_excel(transformed_file).copy()
#
# if "Material_ID" in train_df.columns:
#     train_df_with_slope = train_df.merge(slope_df, on="Material_ID", how="left")
#     print("✅ 检测到 Material_ID，已按 Material_ID 合并 slope")
# else:
#     slope_expanded = pd.DataFrame({
#         "slope": slope_df["slope"].repeat(10).values[:len(train_df)]
#     })
#     train_df_with_slope = pd.concat(
#         [train_df.reset_index(drop=True), slope_expanded.reset_index(drop=True)],
#         axis=1
#     )
#     print("⚠️ 未检测到 Material_ID，已按 repeat(10) 方式拼接 slope。请确认行顺序完全对应。")
#
# train_df_with_slope.to_excel(merged_excel_out, index=False)
# print(f"✅ 已成功保存为: {merged_excel_out}")
#
#
# # =========================================================
# # 3. 将 slope 作为额外输入特征融入模型，并按物质做 8:2 划分
# # =========================================================
# print("\n========== 第3步：建模（按物质划分训练/测试集） ==========")
#
# df_model = train_df_with_slope.copy()
#
# target_col = "Heat of Vaporization"
# if target_col not in df_model.columns:
#     raise ValueError(f"找不到目标列: {target_col}")
#
# # 先确定物质列
# if "Material_ID" in df_model.columns:
#     material_col = "Material_ID"
#     print("✅ 使用 Material_ID 按物质划分")
# else:
#     rows_per_material = 10
#     df_model = df_model.reset_index(drop=True).copy()
#     df_model["Pseudo_Material_ID"] = np.arange(len(df_model)) // rows_per_material
#     material_col = "Pseudo_Material_ID"
#     print("⚠️ 未检测到 Material_ID，改用 Pseudo_Material_ID 按每10行分组")
#
#     if len(df_model) % rows_per_material != 0:
#         print(f"⚠️ 总行数 {len(df_model)} 不是 {rows_per_material} 的整数倍，最后一个物质组可能不完整。")
#
# # 分离特征和目标
# X_all = df_model.drop(columns=[target_col]).copy()
# y_all = df_model[target_col].copy()
#
# # 数值化
# for col in X_all.columns:
#     X_all[col] = pd.to_numeric(X_all[col], errors="coerce")
# y_all = pd.to_numeric(y_all, errors="coerce")
#
# # 删除含缺失的样本
# valid_mask = (~X_all.isna().any(axis=1)) & (~y_all.isna())
# X_all = X_all.loc[valid_mask].copy()
# y_all = y_all.loc[valid_mask].copy()
# df_model = df_model.loc[valid_mask].copy()
#
# print(f"总可用样本数: {len(X_all)}")
#
# # ========= 先按物质划分 =========
# unique_materials = df_model[material_col].dropna().unique()
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
# df_train_out = df_model[df_model[material_col].isin(train_materials)].copy()
# df_test_out = df_model[df_model[material_col].isin(test_materials)].copy()
#
# print("========== 按物质划分 ==========")
# print(f"总物质数: {len(unique_materials)}")
# print(f"训练集物质数: {len(train_materials)}")
# print(f"测试集物质数: {len(test_materials)}")
# print(f"训练集样本数: {len(df_train_out)}")
# print(f"测试集样本数: {len(df_test_out)}")
#
# # 再拆特征和目标
# X_train = df_train_out.drop(columns=[target_col]).copy()
# y_train = df_train_out[target_col].copy()
#
# X_test = df_test_out.drop(columns=[target_col]).copy()
# y_test = df_test_out[target_col].copy()
#
# # 删除非数值列（比如 Material_ID）
# non_numeric_cols = X_train.select_dtypes(exclude=[np.number]).columns.tolist()
# if len(non_numeric_cols) > 0:
#     print(f"⚠️ 检测到非数值列，已删除: {non_numeric_cols}")
#     X_train = X_train.drop(columns=non_numeric_cols)
#     X_test = X_test.drop(columns=non_numeric_cols)
#
# # 训练模型
# model = RandomForestRegressor(
#     random_state=42,
#     n_estimators=300,
#     n_jobs=-1
# )
# model.fit(X_train, y_train)
#
# # 训练集预测
# y_train_pred = model.predict(X_train)
#
# # 测试集预测
# y_test_pred = model.predict(X_test)
#
#
# # =========================================================
# # 4. 评估函数
# # =========================================================
# def evaluate_dataset(y_true, y_pred, name="数据集"):
#     y_true = np.array(y_true, dtype=float)
#     y_pred = np.array(y_pred, dtype=float)
#
#     r2 = r2_score(y_true, y_pred)
#     mse = mean_squared_error(y_true, y_pred)
#
#     relative_error = np.full_like(y_true, np.nan, dtype=float)
#     nonzero_mask = np.abs(y_true) > 1e-12
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
#     print(f"\n📊 {name}评估结果：")
#     print(f"R²  = {r2:.4f}")
#     print(f"MSE = {mse:.4f}")
#     print(f"ARD = {ard:.2f}%")
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
#
# # =========================================================
# # 5. 输出训练集 / 测试集结果
# # =========================================================
# train_relative_error, train_summary = evaluate_dataset(y_train, y_train_pred, "训练集")
# test_relative_error, test_summary = evaluate_dataset(y_test, y_test_pred, "测试集")
#
#
# # =========================================================
# # 6. 保存预测结果
# # =========================================================
# train_result = df_train_out.copy()
# train_result["Set"] = "Train"
# train_result["Predicted_Heat_of_Vaporization"] = y_train_pred
# train_result["Absolute_Error"] = np.abs(y_train.values - y_train_pred)
# train_result["Relative_Error (%)"] = train_relative_error
#
# test_result = df_test_out.copy()
# test_result["Set"] = "Test"
# test_result["Predicted_Heat_of_Vaporization"] = y_test_pred
# test_result["Absolute_Error"] = np.abs(y_test.values - y_test_pred)
# test_result["Relative_Error (%)"] = test_relative_error
#
# comparison_df = pd.concat([train_result, test_result], axis=0).reset_index(drop=True)
# comparison_df.to_excel(prediction_out, index=False)
# print(f"\n✅ 已保存预测结果为: {prediction_out}")
#
# summary_df = pd.DataFrame([train_summary, test_summary])
# summary_df.to_excel(summary_out, index=False)
# print(f"✅ 已保存评估汇总为: {summary_out}")



import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import HuberRegressor
from sklearn.preprocessing import PolynomialFeatures
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score


# =========================================================
# 0. 文件路径
# =========================================================
main_file = "heat of vaporization 204.xlsx"
file_298 = "selected_25_descriptors_data_298.xlsx"
file_tb = "selected_25_descriptors_data_boiling_point.xlsx"
transformed_file = "Transformed_hv_Dataset.xlsx"

slope_csv_out = "slope_values.csv"
merged_excel_out = "Transformed_hv_with_slope.xlsx"
prediction_out = "prediction_vs_actual_hv_with_slope_by_material.xlsx"
summary_out = "prediction_summary_hv_with_slope_by_material.xlsx"


# =========================================================
# 1. 先预测生成 slope
# =========================================================
print("========== 第1步：预测并生成 slope ==========")

df = pd.read_excel(main_file, sheet_name="Sheet1").copy()

material_id_col = df.columns[0]
material_ids = df[material_id_col].values

Nk_all = df.iloc[:, 13:32].apply(
    pd.to_numeric,
    errors="coerce"
)  # 19个基团


# ---------------------------------------------------------
# 1.1 训练 HVap_298 子模型
# ---------------------------------------------------------
df_298 = pd.read_excel(file_298).copy()

target_298 = "Heat of vaporization at normal temperature"

X_298 = df_298.drop(columns=[target_298]).copy()
y_298 = df_298[target_298].copy()

for c in X_298.columns:
    X_298[c] = pd.to_numeric(X_298[c], errors="coerce")

y_298 = pd.to_numeric(y_298, errors="coerce")

valid_298 = (
    ~X_298.isna().any(axis=1)
    & ~y_298.isna()
)

rf_298 = RandomForestRegressor(
    random_state=42,
    n_estimators=300,
    n_jobs=-1
)

rf_298.fit(
    X_298.loc[valid_298],
    y_298.loc[valid_298]
)

# 注意：这里保持原逻辑，若有效行少于主表行数，后面按最短长度截断
HVap_298_all = rf_298.predict(
    X_298.loc[valid_298]
)


# ---------------------------------------------------------
# 1.2 训练 HVap_Tb 子模型
# ---------------------------------------------------------
df_Tb = pd.read_excel(file_tb).copy()

target_Tb = "Heat of vaporization at boiling temperature"

X_Tb = df_Tb.drop(columns=[target_Tb]).copy()
y_Tb = df_Tb[target_Tb].copy()

for c in X_Tb.columns:
    X_Tb[c] = pd.to_numeric(X_Tb[c], errors="coerce")

y_Tb = pd.to_numeric(y_Tb, errors="coerce")

valid_Tb = (
    ~X_Tb.isna().any(axis=1)
    & ~y_Tb.isna()
)

rf_Tb = RandomForestRegressor(
    random_state=42,
    n_estimators=300,
    n_jobs=-1
)

rf_Tb.fit(
    X_Tb.loc[valid_Tb],
    y_Tb.loc[valid_Tb]
)

# 注意：这里保持原逻辑，若有效行少于主表行数，后面按最短长度截断
HVap_Tb_all = rf_Tb.predict(
    X_Tb.loc[valid_Tb]
)


# ---------------------------------------------------------
# 1.3 训练 Tb 子模型
# ---------------------------------------------------------
Tb_raw = pd.to_numeric(
    df.iloc[:, 5],
    errors="coerce"
).values

Tb0 = 222.543

poly = PolynomialFeatures(
    degree=2,
    include_bias=False
)

Nk_poly = poly.fit_transform(
    Nk_all.fillna(0)
)

mask_tb = ~np.isnan(Tb_raw)

model_Tb = HuberRegressor(
    max_iter=5000
)

model_Tb.fit(
    Nk_poly[mask_tb],
    np.exp(Tb_raw[mask_tb] / Tb0)
)

Tb_pred_all = Tb0 * np.log(
    np.clip(
        model_Tb.predict(Nk_poly),
        1e-6,
        None
    )
)


# ---------------------------------------------------------
# 1.4 对齐长度并计算 slope
# ---------------------------------------------------------
n_main = len(df)
n_298 = len(HVap_298_all)
n_tb = len(HVap_Tb_all)

if not (n_298 == n_main and n_tb == n_main):
    n = min(n_main, n_298, n_tb)

    print("警告：三个数据源长度不完全一致，已按最短长度截断。")
    print(f"主表长度: {n_main}, HVap_298长度: {n_298}, HVap_Tb长度: {n_tb}, 使用长度: {n}")

    material_ids_use = material_ids[:n]
    Tb_pred_use = Tb_pred_all[:n]
    HVap_298_use = HVap_298_all[:n]
    HVap_Tb_use = HVap_Tb_all[:n]
else:
    material_ids_use = material_ids
    Tb_pred_use = Tb_pred_all
    HVap_298_use = HVap_298_all
    HVap_Tb_use = HVap_Tb_all

T_ref = 298.15
denominator = Tb_pred_use - T_ref

safe_mask = np.abs(denominator) > 1e-12

slope_all = np.full_like(
    Tb_pred_use,
    np.nan,
    dtype=float
)

slope_all[safe_mask] = (
    HVap_Tb_use[safe_mask]
    - HVap_298_use[safe_mask]
) / denominator[safe_mask]

slope_df = pd.DataFrame({
    "Material_ID": material_ids_use,
    "slope": slope_all,
    "Tb_pred": Tb_pred_use,
    "HVap_298_pred": HVap_298_use,
    "HVap_Tb_pred": HVap_Tb_use
})

slope_df.to_csv(
    slope_csv_out,
    index=False
)

print(f"slope 已保存为: {slope_csv_out}")


# =========================================================
# 2. 将预测的 slope 合并到 transformed 表格
# =========================================================
print("\n========== 第2步：合并 slope 到新表格 ==========")

train_df = pd.read_excel(transformed_file).copy()

if "Material_ID" in train_df.columns:
    train_df_with_slope = train_df.merge(
        slope_df,
        on="Material_ID",
        how="left"
    )

    print("检测到 Material_ID，已按 Material_ID 合并 slope")

else:
    rows_per_material = 10

    slope_expanded = pd.DataFrame({
        "slope": slope_df["slope"].repeat(rows_per_material).values[:len(train_df)],
        "Tb_pred": slope_df["Tb_pred"].repeat(rows_per_material).values[:len(train_df)],
        "HVap_298_pred": slope_df["HVap_298_pred"].repeat(rows_per_material).values[:len(train_df)],
        "HVap_Tb_pred": slope_df["HVap_Tb_pred"].repeat(rows_per_material).values[:len(train_df)]
    })

    train_df_with_slope = pd.concat(
        [
            train_df.reset_index(drop=True),
            slope_expanded.reset_index(drop=True)
        ],
        axis=1
    )

    print("未检测到 Material_ID，已按 repeat(10) 方式拼接 slope。请确认行顺序完全对应。")

train_df_with_slope.to_excel(
    merged_excel_out,
    index=False
)

print(f"已成功保存为: {merged_excel_out}")


# =========================================================
# 3. 将 slope 作为额外输入特征融入模型，并按物质做 8:2 划分
# =========================================================
print("\n========== 第3步：建模（按物质划分训练/测试集） ==========")

df_model = train_df_with_slope.copy()

target_col = "Heat of Vaporization"

if target_col not in df_model.columns:
    raise ValueError(f"找不到目标列: {target_col}")


# ---------------------------------------------------------
# 3.1 确定物质列
# ---------------------------------------------------------
if "Material_ID" in df_model.columns:
    material_col = "Material_ID"
    print("使用 Material_ID 按物质划分")
else:
    rows_per_material = 10

    df_model = df_model.reset_index(drop=True).copy()
    df_model["Pseudo_Material_ID"] = np.arange(len(df_model)) // rows_per_material
    material_col = "Pseudo_Material_ID"

    print("未检测到 Material_ID，改用 Pseudo_Material_ID 按每10行分组")

    if len(df_model) % rows_per_material != 0:
        print(f"警告：总行数 {len(df_model)} 不是 {rows_per_material} 的整数倍，最后一个物质组可能不完整。")


# ---------------------------------------------------------
# 3.2 分离特征和目标
# ---------------------------------------------------------
X_all = df_model.drop(columns=[target_col]).copy()
y_all = df_model[target_col].copy()

# 数值化
for col in X_all.columns:
    X_all[col] = pd.to_numeric(X_all[col], errors="coerce")

y_all = pd.to_numeric(y_all, errors="coerce")

# 删除含缺失的样本
valid_mask = (
    ~X_all.isna().any(axis=1)
    & ~y_all.isna()
)

X_all = X_all.loc[valid_mask].copy()
y_all = y_all.loc[valid_mask].copy()
df_model = df_model.loc[valid_mask].copy()

# 再删除 inf
finite_mask = (
    np.isfinite(X_all.values).all(axis=1)
    & np.isfinite(y_all.values)
)

X_all = X_all.loc[finite_mask].copy()
y_all = y_all.loc[finite_mask].copy()
df_model = df_model.loc[finite_mask].copy()

print(f"总可用样本数: {len(X_all)}")


# ---------------------------------------------------------
# 3.3 按物质划分
# ---------------------------------------------------------
unique_materials = df_model[material_col].dropna().unique()

train_materials, test_materials = train_test_split(
    unique_materials,
    test_size=0.2,
    random_state=50
)

train_materials = set(train_materials)
test_materials = set(test_materials)

df_train_out = df_model[
    df_model[material_col].isin(train_materials)
].copy()

df_test_out = df_model[
    df_model[material_col].isin(test_materials)
].copy()

print("========== 按物质划分 ==========")
print(f"总物质数: {len(unique_materials)}")
print(f"训练集物质数: {len(train_materials)}")
print(f"测试集物质数: {len(test_materials)}")
print(f"训练集样本数: {len(df_train_out)}")
print(f"测试集样本数: {len(df_test_out)}")


# ---------------------------------------------------------
# 3.4 拆特征和目标
# ---------------------------------------------------------
X_train = df_train_out.drop(columns=[target_col]).copy()
y_train = df_train_out[target_col].copy()

X_test = df_test_out.drop(columns=[target_col]).copy()
y_test = df_test_out[target_col].copy()

# 删除非数值列，例如 Material_ID
non_numeric_cols = X_train.select_dtypes(exclude=[np.number]).columns.tolist()

if len(non_numeric_cols) > 0:
    print(f"检测到非数值列，已删除: {non_numeric_cols}")
    X_train = X_train.drop(columns=non_numeric_cols)
    X_test = X_test.drop(columns=non_numeric_cols)

# 转数值
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

df_train_out = df_train_out.loc[train_valid_mask].copy()
df_test_out = df_test_out.loc[test_valid_mask].copy()

X_train = X_train.loc[train_valid_mask].copy()
X_test = X_test.loc[test_valid_mask].copy()

y_train = y_train.loc[train_valid_mask].copy()
y_test = y_test.loc[test_valid_mask].copy()

print("\n========== 最终 RF 数据 ==========")
print(f"训练集有效样本数: {len(X_train)}")
print(f"测试集有效样本数: {len(X_test)}")
print(f"最终模型特征数: {X_train.shape[1]}")


# =========================================================
# 4. 训练最终 RF 模型
# =========================================================
model = RandomForestRegressor(
    random_state=42,
    n_estimators=300,
    n_jobs=-1
)

model.fit(X_train, y_train)

y_train_pred = model.predict(X_train)
y_test_pred = model.predict(X_test)


# =========================================================
# 5. 评估函数
# =========================================================
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
    print(f"R2  = {r2:.4f}")
    print(f"MSE = {mse:.4f}")
    print(f"ARD = {ard:.2f}%")

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


# =========================================================
# 6. 输出训练集 / 测试集 / 完整数据集结果
# =========================================================
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

y_all_final = np.concatenate([
    y_train.values,
    y_test.values
])

y_all_pred = np.concatenate([
    y_train_pred,
    y_test_pred
])

all_relative_error, all_summary = evaluate_dataset(
    y_all_final,
    y_all_pred,
    "完整数据集 train + test",
    strict_less=True
)

print("\nTransformed Hvap + slope RF 完整数据集预测偏差 1%，5%，10%分别为：")
print(all_summary["within_1pct"])
print(all_summary["within_5pct"])
print(all_summary["within_10pct"])


# =========================================================
# 7. 保存预测结果
# =========================================================
train_result = df_train_out.copy()
train_result["Set"] = "Train"
train_result["Actual_Heat_of_Vaporization"] = y_train.values
train_result["Predicted_Heat_of_Vaporization"] = y_train_pred
train_result["Absolute_Error"] = np.abs(y_train.values - y_train_pred)
train_result["Relative_Error (%)"] = train_relative_error

test_result = df_test_out.copy()
test_result["Set"] = "Test"
test_result["Actual_Heat_of_Vaporization"] = y_test.values
test_result["Predicted_Heat_of_Vaporization"] = y_test_pred
test_result["Absolute_Error"] = np.abs(y_test.values - y_test_pred)
test_result["Relative_Error (%)"] = test_relative_error

all_result = pd.concat(
    [train_result, test_result],
    axis=0,
    ignore_index=True
)

all_result["Set"] = "All_train_plus_test"
all_result["Actual_Heat_of_Vaporization"] = y_all_final
all_result["Predicted_Heat_of_Vaporization"] = y_all_pred
all_result["Absolute_Error"] = np.abs(y_all_final - y_all_pred)
all_result["Relative_Error (%)"] = all_relative_error


# ---------------------------------------------------------
# 7.1 保存到 Excel
# ---------------------------------------------------------
with pd.ExcelWriter(prediction_out, engine="xlsxwriter") as writer:
    pd.concat(
        [train_result, test_result],
        axis=0,
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

print(f"\n已保存预测结果为: {prediction_out}")


# =========================================================
# 8. 保存评估汇总
# =========================================================
summary_df = pd.DataFrame([
    train_summary,
    test_summary,
    all_summary
])

summary_df.to_excel(
    summary_out,
    index=False
)

print(f"已保存评估汇总为: {summary_out}")


# =========================================================
# 9. 保存特征重要性
# =========================================================
feature_importance_df = pd.DataFrame({
    "Feature": X_train.columns,
    "Importance": model.feature_importances_
}).sort_values(by="Importance", ascending=False)

feature_importance_file = "Transformed_Hvap_with_slope_RF_feature_importance.xlsx"

feature_importance_df.to_excel(
    feature_importance_file,
    index=False
)

print(f"已保存特征重要性为: {feature_importance_file}")


# =========================================================
# 10. 输出模型结构记录
# =========================================================
print("\n当前 Transformed Hvap + slope + RF 模型结构:")
print("HVap_298_submodel: RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1)")
print("HVap_Tb_submodel: RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1)")
print("Tb_submodel: HuberRegressor(max_iter=5000), input = PolynomialFeatures(Nk, degree=2)")
print("slope = (HVap_Tb_pred - HVap_298_pred) / (Tb_pred - 298.15)")
print("Final target: Heat of Vaporization")
print("Final model: RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1)")
print("Final input features: numeric transformed features + slope + Tb_pred + HVap_298_pred + HVap_Tb_pred")
print("Split: Material_ID if available; otherwise Pseudo_Material_ID by every 10 rows")
print("Final all-data statistics use strict thresholds: <1%, <5%, <10%")