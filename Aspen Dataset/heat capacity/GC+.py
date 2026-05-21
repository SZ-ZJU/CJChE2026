# # import pandas as pd
# # import numpy as np
# # from sklearn.linear_model import HuberRegressor
# # from sklearn.ensemble import GradientBoostingRegressor
# # from sklearn.preprocessing import PolynomialFeatures
# # from sklearn.metrics import mean_squared_error, r2_score
# # from sklearn.model_selection import train_test_split
# #
# # # ========= 1. 读取数据 =========
# # file_path = "heat capacity 207.xlsx"
# # df = pd.read_excel(file_path, sheet_name="Sheet1")
# #
# # # 删除没有物质ID的行
# # df = df.dropna(subset=[df.columns[0]]).copy()
# # df[df.columns[0]] = df[df.columns[0]].astype(int)
# #
# # # ========= 2. 列定义 =========
# # material_id_col = df.columns[0]
# # group_cols = df.columns[11:30]   # 19个基团列
# # temp_cols = df.columns[30:40]    # 10个温度点
# # cp_cols = df.columns[40:50]      # 10个 Cp 值
# # target_column_T1 = 'ASPEN Half Critical T'
# #
# # # 你原代码里用的是这两列
# # cp1_col = df.columns[9]
# # cp2_col = df.columns[50]
# #
# # # ========= 3. 按“物质”做 8:2 划分 =========
# # unique_materials = df[material_id_col].dropna().unique()
# #
# # train_materials, test_materials = train_test_split(
# #     unique_materials,
# #     test_size=0.2,
# #     random_state=42
# # )
# #
# # train_materials = set(train_materials)
# # test_materials = set(test_materials)
# #
# # train_df = df[df[material_id_col].isin(train_materials)].copy()
# # test_df = df[df[material_id_col].isin(test_materials)].copy()
# #
# # print("========== 数据划分 ==========")
# # print(f"总物质数: {len(unique_materials)}")
# # print(f"训练集物质数: {len(train_materials)}")
# # print(f"测试集物质数: {len(test_materials)}")
# # print(f"训练集行数: {len(train_df)}")
# # print(f"测试集行数: {len(test_df)}")
# #
# #
# # # ========= 4. 评估函数 =========
# # def safe_reg_metrics(y_true, y_pred, name="模型"):
# #     y_true = np.asarray(y_true, dtype=float)
# #     y_pred = np.asarray(y_pred, dtype=float)
# #
# #     mse = mean_squared_error(y_true, y_pred)
# #     r2 = r2_score(y_true, y_pred)
# #
# #     nonzero_mask = np.abs(y_true) > 1e-12
# #     if np.any(nonzero_mask):
# #         rel_err = np.full_like(y_true, np.nan, dtype=float)
# #         rel_err[nonzero_mask] = np.abs((y_pred[nonzero_mask] - y_true[nonzero_mask]) / y_true[nonzero_mask]) * 100
# #         ard = np.nanmean(rel_err)
# #         within_1pct = np.sum(rel_err <= 1)
# #         within_5pct = np.sum(rel_err <= 5)
# #         within_10pct = np.sum(rel_err <= 10)
# #     else:
# #         rel_err = np.full_like(y_true, np.nan, dtype=float)
# #         ard = np.nan
# #         within_1pct = 0
# #         within_5pct = 0
# #         within_10pct = 0
# #
# #     print(f"\n📊 {name}")
# #     print(f"R²  = {r2:.4f}")
# #     print(f"MSE = {mse:.4f}")
# #     print(f"ARD = {ard:.2f}%")
# #     print(f"误差 ≤ 1% 的点数: {within_1pct}")
# #     print(f"误差 ≤ 5% 的点数: {within_5pct}")
# #     print(f"误差 ≤ 10% 的点数: {within_10pct}")
# #
# #     return {
# #         "R2": r2,
# #         "MSE": mse,
# #         "ARD_%": ard,
# #         "within_1pct": within_1pct,
# #         "within_5pct": within_5pct,
# #         "within_10pct": within_10pct,
# #         "relative_error_%": rel_err
# #     }
# #
# #
# # # ========= 5. 训练 T1 子模型 =========
# # # 只在训练集里，用有 T1 标签的样本训练
# # train_T1_df = train_df.dropna(subset=[target_column_T1]).copy()
# # test_T1_df = test_df.dropna(subset=[target_column_T1]).copy()
# #
# # poly = PolynomialFeatures(degree=2, include_bias=False)
# #
# # X_train_T1_base = train_T1_df[group_cols].astype(float)
# # X_test_T1_base = test_T1_df[group_cols].astype(float)
# #
# # X_train_T1 = poly.fit_transform(X_train_T1_base)
# # X_test_T1 = poly.transform(X_test_T1_base)
# #
# # y_train_T1 = train_T1_df[target_column_T1].astype(float).values
# # y_test_T1 = test_T1_df[target_column_T1].astype(float).values
# #
# # T1_model = GradientBoostingRegressor(
# #     n_estimators=300,
# #     learning_rate=0.05,
# #     max_depth=4,
# #     random_state=0
# # )
# # T1_model.fit(X_train_T1, y_train_T1)
# #
# # y_train_T1_pred = T1_model.predict(X_train_T1)
# # y_test_T1_pred = T1_model.predict(X_test_T1)
# #
# # metrics_T1_train = safe_reg_metrics(y_train_T1, y_train_T1_pred, "T1_model 训练集")
# # metrics_T1_test = safe_reg_metrics(y_test_T1, y_test_T1_pred, "T1_model 测试集")
# #
# # # 保存 T1 结果
# # t1_train_results = train_T1_df[[material_id_col]].copy()
# # t1_train_results["T1_true"] = y_train_T1
# # t1_train_results["T1_pred"] = y_train_T1_pred
# # t1_train_results["Relative_Error_%"] = metrics_T1_train["relative_error_%"]
# # t1_train_results.to_excel("T1_model_训练集预测结果.xlsx", index=False)
# #
# # t1_test_results = test_T1_df[[material_id_col]].copy()
# # t1_test_results["T1_true"] = y_test_T1
# # t1_test_results["T1_pred"] = y_test_T1_pred
# # t1_test_results["Relative_Error_%"] = metrics_T1_test["relative_error_%"]
# # t1_test_results.to_excel("T1_model_测试集预测结果.xlsx", index=False)
# #
# #
# # # ========= 6. 训练 Cp1 子模型 =========
# # train_Cp1_df = train_df.dropna(subset=[cp1_col]).copy()
# # test_Cp1_df = test_df.dropna(subset=[cp1_col]).copy()
# #
# # X_train_Cp1 = train_Cp1_df[group_cols].astype(float)
# # X_test_Cp1 = test_Cp1_df[group_cols].astype(float)
# # y_train_Cp1 = train_Cp1_df[cp1_col].astype(float).values
# # y_test_Cp1 = test_Cp1_df[cp1_col].astype(float).values
# #
# # Cp1_model = HuberRegressor(max_iter=9000)
# # Cp1_model.fit(X_train_Cp1, y_train_Cp1)
# #
# # y_train_Cp1_pred = Cp1_model.predict(X_train_Cp1)
# # y_test_Cp1_pred = Cp1_model.predict(X_test_Cp1)
# #
# # metrics_Cp1_train = safe_reg_metrics(y_train_Cp1, y_train_Cp1_pred, "Cp1_model 训练集")
# # metrics_Cp1_test = safe_reg_metrics(y_test_Cp1, y_test_Cp1_pred, "Cp1_model 测试集")
# #
# # cp1_train_results = train_Cp1_df[[material_id_col]].copy()
# # cp1_train_results["Cp1_true"] = y_train_Cp1
# # cp1_train_results["Cp1_pred"] = y_train_Cp1_pred
# # cp1_train_results["Relative_Error_%"] = metrics_Cp1_train["relative_error_%"]
# # cp1_train_results.to_excel("Cp1_model_训练集预测结果.xlsx", index=False)
# #
# # cp1_test_results = test_Cp1_df[[material_id_col]].copy()
# # cp1_test_results["Cp1_true"] = y_test_Cp1
# # cp1_test_results["Cp1_pred"] = y_test_Cp1_pred
# # cp1_test_results["Relative_Error_%"] = metrics_Cp1_test["relative_error_%"]
# # cp1_test_results.to_excel("Cp1_model_测试集预测结果.xlsx", index=False)
# #
# #
# # # ========= 7. 训练 Cp2 子模型 =========
# # train_Cp2_df = train_df.dropna(subset=[cp2_col]).copy()
# # test_Cp2_df = test_df.dropna(subset=[cp2_col]).copy()
# #
# # X_train_Cp2 = train_Cp2_df[group_cols].astype(float)
# # X_test_Cp2 = test_Cp2_df[group_cols].astype(float)
# # y_train_Cp2 = train_Cp2_df[cp2_col].astype(float).values
# # y_test_Cp2 = test_Cp2_df[cp2_col].astype(float).values
# #
# # Cp2_model = HuberRegressor(max_iter=9000)
# # Cp2_model.fit(X_train_Cp2, y_train_Cp2)
# #
# # y_train_Cp2_pred = Cp2_model.predict(X_train_Cp2)
# # y_test_Cp2_pred = Cp2_model.predict(X_test_Cp2)
# #
# # metrics_Cp2_train = safe_reg_metrics(y_train_Cp2, y_train_Cp2_pred, "Cp2_model 训练集")
# # metrics_Cp2_test = safe_reg_metrics(y_test_Cp2, y_test_Cp2_pred, "Cp2_model 测试集")
# #
# # cp2_train_results = train_Cp2_df[[material_id_col]].copy()
# # cp2_train_results["Cp2_true"] = y_train_Cp2
# # cp2_train_results["Cp2_pred"] = y_train_Cp2_pred
# # cp2_train_results["Relative_Error_%"] = metrics_Cp2_train["relative_error_%"]
# # cp2_train_results.to_excel("Cp2_model_训练集预测结果.xlsx", index=False)
# #
# # cp2_test_results = test_Cp2_df[[material_id_col]].copy()
# # cp2_test_results["Cp2_true"] = y_test_Cp2
# # cp2_test_results["Cp2_pred"] = y_test_Cp2_pred
# # cp2_test_results["Relative_Error_%"] = metrics_Cp2_test["relative_error_%"]
# # cp2_test_results.to_excel("Cp2_model_测试集预测结果.xlsx", index=False)
# #
# #
# # # ========= 8. 构建“最终随温度变化模型”的样本 =========
# # def build_final_dataset(input_df, group_cols, temp_cols, cp_cols, poly, T1_model, Cp1_model, Cp2_model):
# #     X_total, y_total = [], []
# #     material_ids, temperatures = [], []
# #     slope_list, pred_T1_list, pred_T2_list, pred_Cp1_list, pred_Cp2_list = [], [], [], [], []
# #
# #     # 用于 T1 的多项式特征
# #     X_groups_base = input_df[group_cols].astype(float)
# #     X_poly_all = poly.transform(X_groups_base)
# #
# #     for local_i, (_, row) in enumerate(input_df.iterrows()):
# #         material_id = row[material_id_col]
# #         Nk = row[group_cols].astype(float).values
# #         temps = row[temp_cols].astype(float).values
# #         cps = row[cp_cols].astype(float).values
# #
# #         Nk_df = pd.DataFrame([Nk], columns=group_cols)
# #         Nk_poly = X_poly_all[local_i:local_i+1]
# #
# #         try:
# #             T1_pred = T1_model.predict(Nk_poly)[0]
# #             if np.isnan(T1_pred) or T1_pred <= 0:
# #                 continue
# #
# #             T2_pred = T1_pred * 1.5
# #             if np.isnan(T2_pred) or np.isclose(T2_pred, T1_pred):
# #                 continue
# #
# #             Cp1_pred = Cp1_model.predict(Nk_df)[0]
# #             Cp2_pred = Cp2_model.predict(Nk_df)[0]
# #             slope = (Cp2_pred - Cp1_pred) / (T2_pred - T1_pred)
# #
# #             if np.isnan(slope) or np.isinf(slope):
# #                 continue
# #         except Exception:
# #             continue
# #
# #         for T, Cp in zip(temps, cps):
# #             if np.isnan(T) or np.isnan(Cp):
# #                 continue
# #
# #             features = np.concatenate([
# #                 Nk,          # 19个基团
# #                 Nk * T,      # 19个基团 × T
# #                 [slope * T]  # slope × T
# #             ])
# #
# #             X_total.append(features)
# #             y_total.append(Cp)
# #             material_ids.append(material_id)
# #             temperatures.append(T)
# #             slope_list.append(slope)
# #             pred_T1_list.append(T1_pred)
# #             pred_T2_list.append(T2_pred)
# #             pred_Cp1_list.append(Cp1_pred)
# #             pred_Cp2_list.append(Cp2_pred)
# #
# #     return (
# #         np.array(X_total, dtype=float),
# #         np.array(y_total, dtype=float),
# #         np.array(material_ids),
# #         np.array(temperatures, dtype=float),
# #         np.array(slope_list, dtype=float),
# #         np.array(pred_T1_list, dtype=float),
# #         np.array(pred_T2_list, dtype=float),
# #         np.array(pred_Cp1_list, dtype=float),
# #         np.array(pred_Cp2_list, dtype=float),
# #     )
# #
# #
# # (
# #     X_train_final, y_train_final, id_train_final, T_train_final,
# #     slope_train, T1_train_pred_used, T2_train_pred_used,
# #     Cp1_train_pred_used, Cp2_train_pred_used
# # ) = build_final_dataset(
# #     train_df, group_cols, temp_cols, cp_cols, poly, T1_model, Cp1_model, Cp2_model
# # )
# #
# # (
# #     X_test_final, y_test_final, id_test_final, T_test_final,
# #     slope_test, T1_test_pred_used, T2_test_pred_used,
# #     Cp1_test_pred_used, Cp2_test_pred_used
# # ) = build_final_dataset(
# #     test_df, group_cols, temp_cols, cp_cols, poly, T1_model, Cp1_model, Cp2_model
# # )
# #
# # print("\n========== 最终模型数据集 ==========")
# # print(f"训练集样本点数: {len(X_train_final)}")
# # print(f"测试集样本点数: {len(X_test_final)}")
# #
# #
# # # ========= 9. 训练最终随温度变化模型 =========
# # final_model = HuberRegressor(max_iter=10000)
# # final_model.fit(X_train_final, y_train_final)
# #
# # y_train_final_pred = final_model.predict(X_train_final)
# # y_test_final_pred = final_model.predict(X_test_final)
# #
# # metrics_final_train = safe_reg_metrics(y_train_final, y_train_final_pred, "最终Cp(T)模型 训练集")
# # metrics_final_test = safe_reg_metrics(y_test_final, y_test_final_pred, "最终Cp(T)模型 测试集")
# #
# #
# # # ========= 10. 保存最终模型训练集/测试集预测结果 =========
# # train_results = pd.DataFrame({
# #     "Material_ID": id_train_final,
# #     "Temperature (K)": T_train_final,
# #     "Cp_measured": y_train_final,
# #     "Cp_predicted": y_train_final_pred,
# #     "Relative_Error_%": metrics_final_train["relative_error_%"],
# #     "Pred_T1": T1_train_pred_used,
# #     "Pred_T2": T2_train_pred_used,
# #     "Pred_Cp1": Cp1_train_pred_used,
# #     "Pred_Cp2": Cp2_train_pred_used,
# #     "Slope": slope_train
# # })
# # train_results.to_excel("最终Cp模型_训练集预测结果.xlsx", index=False)
# #
# # test_results = pd.DataFrame({
# #     "Material_ID": id_test_final,
# #     "Temperature (K)": T_test_final,
# #     "Cp_measured": y_test_final,
# #     "Cp_predicted": y_test_final_pred,
# #     "Relative_Error_%": metrics_final_test["relative_error_%"],
# #     "Pred_T1": T1_test_pred_used,
# #     "Pred_T2": T2_test_pred_used,
# #     "Pred_Cp1": Cp1_test_pred_used,
# #     "Pred_Cp2": Cp2_test_pred_used,
# #     "Slope": slope_test
# # })
# # test_results.to_excel("最终Cp模型_测试集预测结果.xlsx", index=False)
# #
# # print("\n✅ 已保存:")
# # print("   - T1_model_训练集预测结果.xlsx")
# # print("   - T1_model_测试集预测结果.xlsx")
# # print("   - Cp1_model_训练集预测结果.xlsx")
# # print("   - Cp1_model_测试集预测结果.xlsx")
# # print("   - Cp2_model_训练集预测结果.xlsx")
# # print("   - Cp2_model_测试集预测结果.xlsx")
# # print("   - 最终Cp模型_训练集预测结果.xlsx")
# # print("   - 最终Cp模型_测试集预测结果.xlsx")
# #
# #
# # # ========= 11. 保存最终模型系数 =========
# # feature_labels = (
# #     list(group_cols) +
# #     [f"{g}_T" for g in group_cols] +
# #     ["slope×T"]
# # )
# #
# # coefficients = pd.DataFrame({
# #     "Feature": feature_labels,
# #     "Contribution": final_model.coef_
# # })
# # coefficients.to_excel("最终Cp模型_系数表.xlsx", index=False)
# # print("📈 已保存模型系数为: 最终Cp模型_系数表.xlsx")
# #
# #
# # # ========= 12. 保存总评估汇总 =========
# # summary_rows = [
# #     ["T1_model", "train", metrics_T1_train["R2"], metrics_T1_train["MSE"], metrics_T1_train["ARD_%"],
# #      metrics_T1_train["within_1pct"], metrics_T1_train["within_5pct"], metrics_T1_train["within_10pct"]],
# #     ["T1_model", "test", metrics_T1_test["R2"], metrics_T1_test["MSE"], metrics_T1_test["ARD_%"],
# #      metrics_T1_test["within_1pct"], metrics_T1_test["within_5pct"], metrics_T1_test["within_10pct"]],
# #
# #     ["Cp1_model", "train", metrics_Cp1_train["R2"], metrics_Cp1_train["MSE"], metrics_Cp1_train["ARD_%"],
# #      metrics_Cp1_train["within_1pct"], metrics_Cp1_train["within_5pct"], metrics_Cp1_train["within_10pct"]],
# #     ["Cp1_model", "test", metrics_Cp1_test["R2"], metrics_Cp1_test["MSE"], metrics_Cp1_test["ARD_%"],
# #      metrics_Cp1_test["within_1pct"], metrics_Cp1_test["within_5pct"], metrics_Cp1_test["within_10pct"]],
# #
# #     ["Cp2_model", "train", metrics_Cp2_train["R2"], metrics_Cp2_train["MSE"], metrics_Cp2_train["ARD_%"],
# #      metrics_Cp2_train["within_1pct"], metrics_Cp2_train["within_5pct"], metrics_Cp2_train["within_10pct"]],
# #     ["Cp2_model", "test", metrics_Cp2_test["R2"], metrics_Cp2_test["MSE"], metrics_Cp2_test["ARD_%"],
# #      metrics_Cp2_test["within_1pct"], metrics_Cp2_test["within_5pct"], metrics_Cp2_test["within_10pct"]],
# #
# #     ["Final_Cp(T)_model", "train", metrics_final_train["R2"], metrics_final_train["MSE"], metrics_final_train["ARD_%"],
# #      metrics_final_train["within_1pct"], metrics_final_train["within_5pct"], metrics_final_train["within_10pct"]],
# #     ["Final_Cp(T)_model", "test", metrics_final_test["R2"], metrics_final_test["MSE"], metrics_final_test["ARD_%"],
# #      metrics_final_test["within_1pct"], metrics_final_test["within_5pct"], metrics_final_test["within_10pct"]],
# # ]
# #
# # summary_df = pd.DataFrame(summary_rows, columns=[
# #     "Model", "Dataset", "R2", "MSE", "ARD_%", "within_1pct", "within_5pct", "within_10pct"
# # ])
# # summary_df.to_excel("所有模型_训练测试评估汇总.xlsx", index=False)
# # print("📋 已保存评估汇总为: 所有模型_训练测试评估汇总.xlsx")
# #
# # import pandas as pd
# # import numpy as np
# # from sklearn.linear_model import HuberRegressor
# # from sklearn.ensemble import GradientBoostingRegressor
# # from sklearn.preprocessing import PolynomialFeatures
# # from sklearn.metrics import mean_squared_error, r2_score
# # from sklearn.model_selection import train_test_split
# #
# # # ========= 1. 读取数据 =========
# # file_path = "heat capacity 207.xlsx"
# # df = pd.read_excel(file_path, sheet_name="Sheet1")
# # df = df.dropna(subset=[df.columns[0]])
# # df[df.columns[0]] = df[df.columns[0]].astype(int)
# #
# # # ========= 2. 列定义 =========
# # group_cols = df.columns[11:30]   # 19个基团列
# # temp_cols = df.columns[30:40]    # 10个温度点
# # cp_cols = df.columns[40:50]      # 10个 Cp 值
# # target_column_T1 = 'ASPEN Half Critical T'
# #
# # # ========= 3. 子模型训练 =========
# # X_groups = df[group_cols]
# # valid_mask = ~df[target_column_T1].isna()
# #
# # poly = PolynomialFeatures(degree=2, include_bias=False)
# # X_poly = poly.fit_transform(X_groups[valid_mask])
# #
# # y_T1 = df.loc[valid_mask, target_column_T1].values
# # T1_model = GradientBoostingRegressor(
# #     n_estimators=300, learning_rate=0.05, max_depth=4, random_state=0
# # ).fit(X_poly, y_T1)
# #
# # Cp1_model = HuberRegressor(max_iter=9000).fit(X_groups, df.iloc[:, 9])
# # Cp2_model = HuberRegressor(max_iter=9000).fit(X_groups, df.iloc[:, 50])
# #
# # # ========= 3.1 子模型评估 =========
# # y_pred_T1 = T1_model.predict(X_poly)
# # r2_T1 = r2_score(y_T1, y_pred_T1)
# # mse_T1 = mean_squared_error(y_T1, y_pred_T1)
# #
# # y_Cp1_true = df.iloc[:, 9]
# # y_Cp1_pred = Cp1_model.predict(X_groups)
# # r2_Cp1 = r2_score(y_Cp1_true, y_Cp1_pred)
# # mse_Cp1 = mean_squared_error(y_Cp1_true, y_Cp1_pred)
# #
# # y_Cp2_true = df.iloc[:, 50]
# # y_Cp2_pred = Cp2_model.predict(X_groups)
# # r2_Cp2 = r2_score(y_Cp2_true, y_Cp2_pred)
# # mse_Cp2 = mean_squared_error(y_Cp2_true, y_Cp2_pred)
# #
# # print("\n📌 子模型评估结果：")
# # print(f"T1_model ->     R²: {r2_T1:.4f} | MSE: {mse_T1:.4f}")
# # print(f"Cp1_model ->    R²: {r2_Cp1:.4f} | MSE: {mse_Cp1:.4f}")
# # print(f"Cp2_model ->    R²: {r2_Cp2:.4f} | MSE: {mse_Cp2:.4f}")
# #
# # # ========= 4. 构建总数据 =========
# # X_total, y_total, material_ids, temperatures = [], [], [], []
# # X_poly_all = poly.transform(X_groups)
# #
# # for i, row in df.iterrows():
# #     material_id = row.iloc[0]
# #     Nk = row[group_cols].values
# #     temps = row[temp_cols].values
# #     cps = row[cp_cols].values
# #
# #     Nk_df = pd.DataFrame([Nk], columns=group_cols)
# #     Nk_poly = X_poly_all[i:i+1]
# #
# #     try:
# #         T1 = T1_model.predict(Nk_poly)[0]
# #         if T1 <= 0 or np.isnan(T1):
# #             continue
# #
# #         T2 = T1 * 1.5
# #         Cp1 = Cp1_model.predict(Nk_df)[0]
# #         Cp2 = Cp2_model.predict(Nk_df)[0]
# #         slope = (Cp2 - Cp1) / (T2 - T1)
# #     except:
# #         continue
# #
# #     for T, Cp in zip(temps, cps):
# #         if np.isnan(T) or np.isnan(Cp):
# #             continue
# #
# #         features = np.concatenate([
# #             Nk,
# #             Nk * T,
# #             [slope * T]
# #         ])
# #
# #         X_total.append(features)
# #         y_total.append(Cp)
# #         material_ids.append(material_id)
# #         temperatures.append(T)
# #
# # # ========= 5. 转成数组并 8:2 划分 =========
# # X_total = np.array(X_total)
# # y_total = np.array(y_total)
# # material_ids = np.array(material_ids)
# # temperatures = np.array(temperatures)
# #
# # X_train, X_test, y_train, y_test, mat_train, mat_test, temp_train, temp_test = train_test_split(
# #     X_total,
# #     y_total,
# #     material_ids,
# #     temperatures,
# #     test_size=0.2,
# #     random_state=42
# # )
# #
# # # ========= 6. 模型训练 =========
# # model = HuberRegressor(max_iter=10000)
# # model.fit(X_train, y_train)
# #
# # # ========= 7. 训练集 / 测试集预测 =========
# # y_train_pred = model.predict(X_train)
# # y_test_pred = model.predict(X_test)
# #
# # # 训练集指标
# # train_mse = mean_squared_error(y_train, y_train_pred)
# # train_r2 = r2_score(y_train, y_train_pred)
# # train_ard = np.mean(np.abs((y_train - y_train_pred) / y_train)) * 100
# #
# # # 测试集指标
# # test_mse = mean_squared_error(y_test, y_test_pred)
# # test_r2 = r2_score(y_test, y_test_pred)
# # test_ard = np.mean(np.abs((y_test - y_test_pred) / y_test)) * 100
# #
# # # 测试集误差统计
# # relative_error_test = np.abs((y_test_pred - y_test) / y_test) * 100
# # within_1pct = np.sum(relative_error_test <= 1)
# # within_5pct = np.sum(relative_error_test <= 5)
# # within_10pct = np.sum(relative_error_test <= 10)
# #
# # print("\n📊 训练集评估：")
# # print(f"R²  = {train_r2:.4f}")
# # print(f"MSE = {train_mse:.2f}")
# # print(f"ARD = {train_ard:.2f}%")
# #
# # print("\n📊 测试集评估：")
# # print(f"R²  = {test_r2:.4f}")
# # print(f"MSE = {test_mse:.2f}")
# # print(f"ARD = {test_ard:.2f}%")
# # print(f"✅ 测试集误差 ≤ 1% 的数据点数量: {within_1pct}")
# # print(f"✅ 测试集误差 ≤ 5% 的数据点数量: {within_5pct}")
# # print(f"✅ 测试集误差 ≤ 10% 的数据点数量: {within_10pct}")
# #
# # # ========= 8. 输出测试集预测结果 =========
# # results_test = pd.DataFrame({
# #     "Material_ID": mat_test,
# #     "Temperature (K)": temp_test,
# #     "Cp_measured": y_test,
# #     "Cp_predicted": y_test_pred
# # })
# # results_test.to_excel("Cp测试集预测结果_slopeT特征_β1回归.xlsx", index=False)
# # print("✅ 已保存测试集预测结果为: Cp测试集预测结果_slopeT特征_β1回归.xlsx")
# #
# # # ========= 9. 输出系数表 =========
# # feature_labels = (
# #     list(group_cols) +
# #     [f"{g}_T" for g in group_cols] +
# #     ["slope×T"]
# # )
# #
# # coefficients = pd.DataFrame({
# #     "Feature": feature_labels,
# #     "Contribution": model.coef_
# # })
# # coefficients.to_excel("Cp系数表_slopeT特征_β1回归.xlsx", index=False)
# # print("📈 已保存模型系数为: Cp系数表_slopeT特征_β1回归.xlsx")
#
# import pandas as pd
# import numpy as np
# from sklearn.linear_model import HuberRegressor
# from sklearn.ensemble import GradientBoostingRegressor
# from sklearn.preprocessing import PolynomialFeatures
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split
#
# # ========= 1. 读取数据 =========
# file_path = "heat capacity 207.xlsx"
# df = pd.read_excel(file_path, sheet_name="Sheet1")
# df = df.dropna(subset=[df.columns[0]]).copy()
# df[df.columns[0]] = df[df.columns[0]].astype(int)
#
# # ========= 2. 列定义 =========
# material_id_col = df.columns[0]
# group_cols = df.columns[11:30]   # 19个基团列
# temp_cols = df.columns[30:40]    # 10个温度点
# cp_cols = df.columns[40:50]      # 10个 Cp 值
# target_column_T1 = 'ASPEN Half Critical T'
#
# # ========= 3. 子模型训练 =========
# X_groups = df[group_cols]
# valid_mask = ~df[target_column_T1].isna()
#
# poly = PolynomialFeatures(degree=2, include_bias=False)
# X_poly = poly.fit_transform(X_groups[valid_mask])
#
# y_T1 = df.loc[valid_mask, target_column_T1].values
# T1_model = GradientBoostingRegressor(
#     n_estimators=300, learning_rate=0.05, max_depth=4, random_state=0
# ).fit(X_poly, y_T1)
#
# Cp1_model = HuberRegressor(max_iter=9000).fit(X_groups, df.iloc[:, 9])
# Cp2_model = HuberRegressor(max_iter=9000).fit(X_groups, df.iloc[:, 50])
#
# # ========= 3.1 子模型评估 =========
# y_pred_T1 = T1_model.predict(X_poly)
# r2_T1 = r2_score(y_T1, y_pred_T1)
# mse_T1 = mean_squared_error(y_T1, y_pred_T1)
#
# y_Cp1_true = df.iloc[:, 9]
# y_Cp1_pred = Cp1_model.predict(X_groups)
# r2_Cp1 = r2_score(y_Cp1_true, y_Cp1_pred)
# mse_Cp1 = mean_squared_error(y_Cp1_true, y_Cp1_pred)
#
# y_Cp2_true = df.iloc[:, 50]
# y_Cp2_pred = Cp2_model.predict(X_groups)
# r2_Cp2 = r2_score(y_Cp2_true, y_Cp2_pred)
# mse_Cp2 = mean_squared_error(y_Cp2_true, y_Cp2_pred)
#
# print("\n📌 子模型评估结果：")
# print(f"T1_model ->     R²: {r2_T1:.4f} | MSE: {mse_T1:.4f}")
# print(f"Cp1_model ->    R²: {r2_Cp1:.4f} | MSE: {mse_Cp1:.4f}")
# print(f"Cp2_model ->    R²: {r2_Cp2:.4f} | MSE: {mse_Cp2:.4f}")
#
# # ========= 4. 先按物质划分 8:2 =========
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
# print("\n========== 按物质划分 ==========")
# print(f"总物质数: {len(unique_materials)}")
# print(f"训练集物质数: {len(train_materials)}")
# print(f"测试集物质数: {len(test_materials)}")
#
# # ========= 5. 构建训练集 / 测试集 =========
# X_train, y_train, mat_train, temp_train = [], [], [], []
# X_test, y_test, mat_test, temp_test = [], [], [], []
#
# X_poly_all = poly.transform(X_groups)
#
# for i, row in df.iterrows():
#     material_id = row[material_id_col]
#     Nk = row[group_cols].values
#     temps = row[temp_cols].values
#     cps = row[cp_cols].values
#
#     Nk_df = pd.DataFrame([Nk], columns=group_cols)
#     Nk_poly = X_poly_all[i:i+1]
#
#     try:
#         T1 = T1_model.predict(Nk_poly)[0]
#         if T1 <= 0 or np.isnan(T1):
#             continue
#
#         T2 = T1 * 1.5
#         Cp1 = Cp1_model.predict(Nk_df)[0]
#         Cp2 = Cp2_model.predict(Nk_df)[0]
#         slope = (Cp2 - Cp1) / (T2 - T1)
#     except:
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
#         elif material_id in test_materials:
#             X_test.append(features)
#             y_test.append(Cp)
#             mat_test.append(material_id)
#             temp_test.append(T)
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
# print(f"训练集样本点数: {len(X_train)}")
# print(f"测试集样本点数: {len(X_test)}")
#
# # ========= 6. 模型训练 =========
# model = HuberRegressor(max_iter=10000)
# model.fit(X_train, y_train)
#
# # ========= 7. 训练集 / 测试集预测 =========
# y_train_pred = model.predict(X_train)
# y_test_pred = model.predict(X_test)
#
# # 训练集指标
# train_mse = mean_squared_error(y_train, y_train_pred)
# train_r2 = r2_score(y_train, y_train_pred)
# train_ard = np.mean(np.abs((y_train - y_train_pred) / y_train)) * 100
#
# # 测试集指标
# test_mse = mean_squared_error(y_test, y_test_pred)
# test_r2 = r2_score(y_test, y_test_pred)
# test_ard = np.mean(np.abs((y_test - y_test_pred) / y_test)) * 100
#
# # 测试集误差统计
# relative_error_test = np.abs((y_test_pred - y_test) / y_test) * 100
# within_1pct = np.sum(relative_error_test <= 1)
# within_5pct = np.sum(relative_error_test <= 5)
# within_10pct = np.sum(relative_error_test <= 10)
#
# print("\n📊 训练集评估：")
# print(f"R²  = {train_r2:.4f}")
# print(f"MSE = {train_mse:.2f}")
# print(f"ARD = {train_ard:.2f}%")
#
# print("\n📊 测试集评估：")
# print(f"R²  = {test_r2:.4f}")
# print(f"MSE = {test_mse:.2f}")
# print(f"ARD = {test_ard:.2f}%")
# print(f"✅ 测试集误差 ≤ 1% 的数据点数量: {within_1pct}")
# print(f"✅ 测试集误差 ≤ 5% 的数据点数量: {within_5pct}")
# print(f"✅ 测试集误差 ≤ 10% 的数据点数量: {within_10pct}")
#
# # ========= 8. 输出测试集预测结果 =========
# results_test = pd.DataFrame({
#     "Material_ID": mat_test,
#     "Temperature (K)": temp_test,
#     "Cp_measured": y_test,
#     "Cp_predicted": y_test_pred
# })
# results_test.to_excel("Cp测试集预测结果_按物质划分_slopeT特征_β1回归.xlsx", index=False)
# print("✅ 已保存测试集预测结果为: Cp测试集预测结果_按物质划分_slopeT特征_β1回归.xlsx")
#
# # ========= 9. 输出系数表 =========
# feature_labels = (
#     list(group_cols) +
#     [f"{g}_T" for g in group_cols] +
#     ["slope×T"]
# )
#
# coefficients = pd.DataFrame({
#     "Feature": feature_labels,
#     "Contribution": model.coef_
# })
# coefficients.to_excel("Cp系数表_按物质划分_slopeT特征_β1回归.xlsx", index=False)
# print("📈 已保存模型系数为: Cp系数表_按物质划分_slopeT特征_β1回归.xlsx")


import pandas as pd
import numpy as np

from sklearn.linear_model import HuberRegressor
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


# ========= 1. 读取数据 =========

file_path = "heat capacity 207.xlsx"
df = pd.read_excel(file_path, sheet_name="Sheet1")
df = df.dropna(subset=[df.columns[0]]).copy()
df[df.columns[0]] = df[df.columns[0]].astype(int)


# ========= 2. 列定义 =========

material_id_col = df.columns[0]

group_cols = df.columns[11:30]   # 19个基团列
temp_cols = df.columns[30:40]    # 10个温度点
cp_cols = df.columns[40:50]      # 10个 Cp 值

target_column_T1 = "ASPEN Half Critical T"

cp1_col = df.columns[9]
cp2_col = df.columns[50]


# ========= 3. 数值化 =========

for c in group_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")

for c in temp_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")

for c in cp_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")

df[target_column_T1] = pd.to_numeric(df[target_column_T1], errors="coerce")
df[cp1_col] = pd.to_numeric(df[cp1_col], errors="coerce")
df[cp2_col] = pd.to_numeric(df[cp2_col], errors="coerce")


# ========= 4. 子模型训练 =========
# 注意：这里保持原代码逻辑，子模型使用全数据训练

X_groups = df[group_cols].astype(float)

valid_mask = ~df[target_column_T1].isna()

poly = PolynomialFeatures(
    degree=2,
    include_bias=False
)

X_poly = poly.fit_transform(X_groups.loc[valid_mask])
y_T1 = df.loc[valid_mask, target_column_T1].astype(float).values

T1_model = GradientBoostingRegressor(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=4,
    random_state=0
)

T1_model.fit(X_poly, y_T1)

Cp1_model = HuberRegressor(
    max_iter=9000
)

Cp1_model.fit(
    X_groups,
    df[cp1_col].astype(float).values
)

Cp2_model = HuberRegressor(
    max_iter=9000
)

Cp2_model.fit(
    X_groups,
    df[cp2_col].astype(float).values
)


# ========= 4.1 子模型评估函数 =========

def evaluate_basic(y_true, y_pred, name="模型", strict_less=False):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mse = mean_squared_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)

    relative_error = np.full_like(y_true, np.nan, dtype=float)
    nonzero_mask = np.abs(y_true) > 1e-12

    if np.any(nonzero_mask):
        relative_error[nonzero_mask] = np.abs(
            (y_pred[nonzero_mask] - y_true[nonzero_mask])
            / y_true[nonzero_mask]
        ) * 100
        ard = np.nanmean(relative_error)
    else:
        ard = np.nan

    if strict_less:
        within_1pct = np.sum(relative_error < 1)
        within_5pct = np.sum(relative_error < 5)
        within_10pct = np.sum(relative_error < 10)
    else:
        within_1pct = np.sum(relative_error <= 1)
        within_5pct = np.sum(relative_error <= 5)
        within_10pct = np.sum(relative_error <= 10)

    print(f"\n{name}")
    print(f"R²  = {r2:.4f}")
    print(f"MSE = {mse:.4f}")
    print(f"ARD = {ard:.2f}%")

    if strict_less:
        print(f"误差 < 1% 的点数: {within_1pct}")
        print(f"误差 < 5% 的点数: {within_5pct}")
        print(f"误差 < 10% 的点数: {within_10pct}")
    else:
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


# ========= 4.2 子模型评估 =========

y_pred_T1 = T1_model.predict(X_poly)

metrics_T1 = evaluate_basic(
    y_T1,
    y_pred_T1,
    "T1_model 全数据"
)

y_Cp1_true = df[cp1_col].astype(float).values
y_Cp1_pred = Cp1_model.predict(X_groups)

metrics_Cp1 = evaluate_basic(
    y_Cp1_true,
    y_Cp1_pred,
    "Cp1_model 全数据"
)

y_Cp2_true = df[cp2_col].astype(float).values
y_Cp2_pred = Cp2_model.predict(X_groups)

metrics_Cp2 = evaluate_basic(
    y_Cp2_true,
    y_Cp2_pred,
    "Cp2_model 全数据"
)

print("\n子模型评估结果：")
print(f"T1_model  -> R²: {metrics_T1['R2']:.4f} | MSE: {metrics_T1['MSE']:.4f}")
print(f"Cp1_model -> R²: {metrics_Cp1['R2']:.4f} | MSE: {metrics_Cp1['MSE']:.4f}")
print(f"Cp2_model -> R²: {metrics_Cp2['R2']:.4f} | MSE: {metrics_Cp2['MSE']:.4f}")


# ========= 5. 按物质划分 8:2 =========

unique_materials = df[material_id_col].dropna().unique()

train_materials, test_materials = train_test_split(
    unique_materials,
    test_size=0.2,
    random_state=42
)

train_materials = set(train_materials)
test_materials = set(test_materials)

print("\n========== 按物质划分 ==========")
print(f"总物质数: {len(unique_materials)}")
print(f"训练集物质数: {len(train_materials)}")
print(f"测试集物质数: {len(test_materials)}")


# ========= 6. 构建训练集 / 测试集 =========

X_train, y_train, mat_train, temp_train = [], [], [], []
X_test, y_test, mat_test, temp_test = [], [], [], []

slope_train, T1_train_used, T2_train_used, Cp1_train_used, Cp2_train_used = [], [], [], [], []
slope_test, T1_test_used, T2_test_used, Cp1_test_used, Cp2_test_used = [], [], [], [], []

X_poly_all = poly.transform(X_groups)

for i, row in df.iterrows():
    material_id = row[material_id_col]

    Nk = row[group_cols].astype(float).values
    temps = row[temp_cols].astype(float).values
    cps = row[cp_cols].astype(float).values

    Nk_df = pd.DataFrame([Nk], columns=group_cols)
    Nk_poly = X_poly_all[i:i + 1]

    try:
        T1 = T1_model.predict(Nk_poly)[0]

        if T1 <= 0 or np.isnan(T1):
            continue

        T2 = T1 * 1.5

        if np.isnan(T2) or np.isclose(T2, T1):
            continue

        Cp1 = Cp1_model.predict(Nk_df)[0]
        Cp2 = Cp2_model.predict(Nk_df)[0]

        slope = (Cp2 - Cp1) / (T2 - T1)

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
            T1_train_used.append(T1)
            T2_train_used.append(T2)
            Cp1_train_used.append(Cp1)
            Cp2_train_used.append(Cp2)

        elif material_id in test_materials:
            X_test.append(features)
            y_test.append(Cp)
            mat_test.append(material_id)
            temp_test.append(T)

            slope_test.append(slope)
            T1_test_used.append(T1)
            T2_test_used.append(T2)
            Cp1_test_used.append(Cp1)
            Cp2_test_used.append(Cp2)

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

print(f"训练集样本点数: {len(X_train)}")
print(f"测试集样本点数: {len(X_test)}")


# ========= 7. 最终 Huber 模型训练 =========

model = HuberRegressor(
    max_iter=10000
)

model.fit(X_train, y_train)


# ========= 8. 训练集 / 测试集预测 =========

y_train_pred = model.predict(X_train)
y_test_pred = model.predict(X_test)


# ========= 9. 训练集 / 测试集评估 =========

train_metrics = evaluate_basic(
    y_train,
    y_train_pred,
    "最终 Huber Cp(T) 模型 训练集",
    strict_less=False
)

test_metrics = evaluate_basic(
    y_test,
    y_test_pred,
    "最终 Huber Cp(T) 模型 测试集",
    strict_less=False
)


# ========= 9.1 完整数据集统计：训练集 + 测试集 =========

y_all_true = np.concatenate([y_train, y_test])
y_all_pred = np.concatenate([y_train_pred, y_test_pred])

mat_all = np.concatenate([mat_train, mat_test])
temp_all = np.concatenate([temp_train, temp_test])

slope_all = np.concatenate([slope_train, slope_test])
T1_all_used = np.concatenate([T1_train_used, T1_test_used])
T2_all_used = np.concatenate([T2_train_used, T2_test_used])
Cp1_all_used = np.concatenate([Cp1_train_used, Cp1_test_used])
Cp2_all_used = np.concatenate([Cp2_train_used, Cp2_test_used])

all_metrics = evaluate_basic(
    y_all_true,
    y_all_pred,
    "最终 Huber Cp(T) 模型 完整数据集：训练集 + 测试集",
    strict_less=True
)

print("\n最终 Huber Cp(T) 模型完整数据集 1%，5%，10%分别为：")
print(all_metrics["within_1pct"])
print(all_metrics["within_5pct"])
print(all_metrics["within_10pct"])


# ========= 10. 输出训练集预测结果 =========

results_train = pd.DataFrame({
    "Material_ID": mat_train,
    "Temperature (K)": temp_train,
    "Cp_measured": y_train,
    "Cp_predicted": y_train_pred,
    "Relative_Error_%": train_metrics["relative_error_%"],
    "Pred_T1": T1_train_used,
    "Pred_T2": T2_train_used,
    "Pred_Cp1": Cp1_train_used,
    "Pred_Cp2": Cp2_train_used,
    "Slope": slope_train
})

results_train.to_excel(
    "Cp训练集预测结果_按物质划分_slopeT特征_Huber回归.xlsx",
    index=False
)

print("\n已保存训练集预测结果为: Cp训练集预测结果_按物质划分_slopeT特征_Huber回归.xlsx")


# ========= 11. 输出测试集预测结果 =========

results_test = pd.DataFrame({
    "Material_ID": mat_test,
    "Temperature (K)": temp_test,
    "Cp_measured": y_test,
    "Cp_predicted": y_test_pred,
    "Relative_Error_%": test_metrics["relative_error_%"],
    "Pred_T1": T1_test_used,
    "Pred_T2": T2_test_used,
    "Pred_Cp1": Cp1_test_used,
    "Pred_Cp2": Cp2_test_used,
    "Slope": slope_test
})

results_test.to_excel(
    "Cp测试集预测结果_按物质划分_slopeT特征_Huber回归.xlsx",
    index=False
)

print("已保存测试集预测结果为: Cp测试集预测结果_按物质划分_slopeT特征_Huber回归.xlsx")


# ========= 12. 输出完整数据集预测结果 =========

results_all = pd.DataFrame({
    "Material_ID": mat_all,
    "Temperature (K)": temp_all,
    "Cp_measured": y_all_true,
    "Cp_predicted": y_all_pred,
    "Relative_Error_%": all_metrics["relative_error_%"],
    "Pred_T1": T1_all_used,
    "Pred_T2": T2_all_used,
    "Pred_Cp1": Cp1_all_used,
    "Pred_Cp2": Cp2_all_used,
    "Slope": slope_all
})

results_all.to_excel(
    "Cp完整数据集预测结果_按物质划分_slopeT特征_Huber回归.xlsx",
    index=False
)

print("已保存完整数据集预测结果为: Cp完整数据集预测结果_按物质划分_slopeT特征_Huber回归.xlsx")


# ========= 13. 输出系数表 =========

feature_labels = (
    list(group_cols) +
    [f"{g}_T" for g in group_cols] +
    ["slope×T"]
)

coefficients = pd.DataFrame({
    "Feature": feature_labels,
    "Contribution": model.coef_
})

coefficients.to_excel(
    "Cp系数表_按物质划分_slopeT特征_Huber回归.xlsx",
    index=False
)

print("已保存模型系数为: Cp系数表_按物质划分_slopeT特征_Huber回归.xlsx")


# ========= 14. 保存汇总表 =========

summary_rows = [
    [
        "T1_model",
        "all_data",
        metrics_T1["R2"],
        metrics_T1["MSE"],
        metrics_T1["ARD_%"],
        metrics_T1["within_1pct"],
        metrics_T1["within_5pct"],
        metrics_T1["within_10pct"]
    ],
    [
        "Cp1_model",
        "all_data",
        metrics_Cp1["R2"],
        metrics_Cp1["MSE"],
        metrics_Cp1["ARD_%"],
        metrics_Cp1["within_1pct"],
        metrics_Cp1["within_5pct"],
        metrics_Cp1["within_10pct"]
    ],
    [
        "Cp2_model",
        "all_data",
        metrics_Cp2["R2"],
        metrics_Cp2["MSE"],
        metrics_Cp2["ARD_%"],
        metrics_Cp2["within_1pct"],
        metrics_Cp2["within_5pct"],
        metrics_Cp2["within_10pct"]
    ],
    [
        "Final_Huber_CpT_model",
        "train",
        train_metrics["R2"],
        train_metrics["MSE"],
        train_metrics["ARD_%"],
        train_metrics["within_1pct"],
        train_metrics["within_5pct"],
        train_metrics["within_10pct"]
    ],
    [
        "Final_Huber_CpT_model",
        "test",
        test_metrics["R2"],
        test_metrics["MSE"],
        test_metrics["ARD_%"],
        test_metrics["within_1pct"],
        test_metrics["within_5pct"],
        test_metrics["within_10pct"]
    ],
    [
        "Final_Huber_CpT_model",
        "all",
        all_metrics["R2"],
        all_metrics["MSE"],
        all_metrics["ARD_%"],
        all_metrics["within_1pct"],
        all_metrics["within_5pct"],
        all_metrics["within_10pct"]
    ],
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
    "所有模型_按物质划分_slopeT特征_Huber回归_评估汇总.xlsx",
    index=False
)

print("已保存评估汇总为: 所有模型_按物质划分_slopeT特征_Huber回归_评估汇总.xlsx")


# ========= 15. 输出模型参数 =========

print("\n当前 T1_model 参数:")
print(T1_model)

print("\n当前 Cp1_model 参数:")
print(Cp1_model)

print("\n当前 Cp2_model 参数:")
print(Cp2_model)

print("\n当前最终 Huber Cp(T) 模型参数:")
print(model)