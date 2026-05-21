# # import pandas as pd
# # import numpy as np
# # from sklearn.linear_model import HuberRegressor
# # from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
# # from sklearn.preprocessing import PolynomialFeatures
# # from sklearn.metrics import mean_squared_error, r2_score
# # from sklearn.model_selection import train_test_split
# #
# # # =========================================================
# # # 0. 参数区
# # # =========================================================
# # gani_file = "heat capacity 207.xlsx"
# # gani_sheet = "Sheet1"
# # transformed_file = "Transformed_hp_Dataset.xlsx"
# #
# # target_col_final = "Heat Capacity"
# # target_column_T1 = "ASPEN Half Critical T"
# # rows_per_material = 10
# # random_state = 42
# #
# # # =========================================================
# # # 1. 读取 Gani 数据（用于训练三个子模型并预测 slope）
# # # =========================================================
# # gani_df = pd.read_excel(gani_file, sheet_name=gani_sheet)
# # gani_df = gani_df.dropna(subset=[gani_df.columns[0]]).copy()
# # gani_df[gani_df.columns[0]] = gani_df[gani_df.columns[0]].astype(int)
# #
# # material_id_col = gani_df.columns[0]
# # group_cols = gani_df.columns[11:30]   # 19个基团列
# # cp1_col = gani_df.columns[9]
# # cp2_col = gani_df.columns[50]
# #
# # # 物质顺序（后面要映射到 Transformed_hp_Dataset.xlsx）
# # ordered_material_ids = gani_df[material_id_col].drop_duplicates().tolist()
# #
# # # =========================================================
# # # 2. 读取最终回归数据，并构造 Material_ID
# # #    假设每10行是同一个物质，顺序与 gani_df 一致
# # # =========================================================
# # trans_df = pd.read_excel(transformed_file).reset_index(drop=True).copy()
# #
# # if len(trans_df) % rows_per_material != 0:
# #     raise ValueError(
# #         f"Transformed_hp_Dataset.xlsx 的总行数 {len(trans_df)} 不是 {rows_per_material} 的整数倍，"
# #         f"无法按每个物质 {rows_per_material} 行来分组。"
# #     )
# #
# # n_materials_trans = len(trans_df) // rows_per_material
# # n_materials_gani = len(ordered_material_ids)
# #
# # if n_materials_trans != n_materials_gani:
# #     raise ValueError(
# #         f"Transformed_hp_Dataset.xlsx 推断出的物质数 = {n_materials_trans}，"
# #         f"而 Gani 数据中的物质数 = {n_materials_gani}，二者不一致。"
# #     )
# #
# # trans_df["Material_ID"] = np.repeat(ordered_material_ids, rows_per_material)
# #
# # # =========================================================
# # # 3. 只做一次按物质 8:2 划分
# # # =========================================================
# # unique_materials = np.array(ordered_material_ids)
# #
# # train_materials, test_materials = train_test_split(
# #     unique_materials,
# #     test_size=0.2,
# #     random_state=random_state
# # )
# #
# # train_materials = set(train_materials)
# # test_materials = set(test_materials)
# #
# # gani_train_df = gani_df[gani_df[material_id_col].isin(train_materials)].copy()
# # gani_test_df = gani_df[gani_df[material_id_col].isin(test_materials)].copy()
# #
# # trans_train_df = trans_df[trans_df["Material_ID"].isin(train_materials)].copy()
# # trans_test_df = trans_df[trans_df["Material_ID"].isin(test_materials)].copy()
# #
# # print("========== 数据划分 ==========")
# # print(f"Gani 总物质数: {len(unique_materials)}")
# # print(f"训练集物质数: {len(train_materials)}")
# # print(f"测试集物质数: {len(test_materials)}")
# # print(f"Transformed 训练集行数: {len(trans_train_df)}")
# # print(f"Transformed 测试集行数: {len(trans_test_df)}")
# #
# # # =========================================================
# # # 4. 评估函数
# # # =========================================================
# # def evaluate_regression(y_true, y_pred, name="模型"):
# #     y_true = np.asarray(y_true, dtype=float)
# #     y_pred = np.asarray(y_pred, dtype=float)
# #
# #     mse = mean_squared_error(y_true, y_pred)
# #     r2 = r2_score(y_true, y_pred)
# #
# #     nonzero_mask = np.abs(y_true) > 1e-12
# #     relative_error = np.full_like(y_true, np.nan, dtype=float)
# #
# #     if np.any(nonzero_mask):
# #         relative_error[nonzero_mask] = np.abs(
# #             (y_true[nonzero_mask] - y_pred[nonzero_mask]) / y_true[nonzero_mask]
# #         ) * 100
# #         ard = np.nanmean(relative_error)
# #     else:
# #         ard = np.nan
# #
# #     within_1pct = np.sum(relative_error <= 1)
# #     within_5pct = np.sum(relative_error <= 5)
# #     within_10pct = np.sum(relative_error <= 10)
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
# #         "relative_error_%": relative_error
# #     }
# #
# # # =========================================================
# # # 5. 训练三个子模型（只用训练集）
# # # =========================================================
# # X_groups_train = gani_train_df[group_cols].astype(float)
# # X_groups_test = gani_test_df[group_cols].astype(float)
# #
# # # PolynomialFeatures 也只在训练集上 fit
# # poly = PolynomialFeatures(degree=2, include_bias=False)
# # poly.fit(X_groups_train)
# #
# # # ---- T1 模型 ----
# # train_valid_mask = ~gani_train_df[target_column_T1].isna()
# # test_valid_mask = ~gani_test_df[target_column_T1].isna()
# #
# # X_train_T1 = poly.transform(gani_train_df.loc[train_valid_mask, group_cols].astype(float))
# # X_test_T1 = poly.transform(gani_test_df.loc[test_valid_mask, group_cols].astype(float))
# #
# # y_train_T1 = gani_train_df.loc[train_valid_mask, target_column_T1].astype(float).values
# # y_test_T1 = gani_test_df.loc[test_valid_mask, target_column_T1].astype(float).values
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
# # metrics_T1_train = evaluate_regression(y_train_T1, y_train_T1_pred, "T1_model 训练集")
# # metrics_T1_test = evaluate_regression(y_test_T1, y_test_T1_pred, "T1_model 测试集")
# #
# # # ---- Cp1 模型 ----
# # y_train_Cp1 = gani_train_df[cp1_col].astype(float).values
# # y_test_Cp1 = gani_test_df[cp1_col].astype(float).values
# #
# # Cp1_model = HuberRegressor(max_iter=9000)
# # Cp1_model.fit(X_groups_train, y_train_Cp1)
# #
# # y_train_Cp1_pred = Cp1_model.predict(X_groups_train)
# # y_test_Cp1_pred = Cp1_model.predict(X_groups_test)
# #
# # metrics_Cp1_train = evaluate_regression(y_train_Cp1, y_train_Cp1_pred, "Cp1_model 训练集")
# # metrics_Cp1_test = evaluate_regression(y_test_Cp1, y_test_Cp1_pred, "Cp1_model 测试集")
# #
# # # ---- Cp2 模型 ----
# # y_train_Cp2 = gani_train_df[cp2_col].astype(float).values
# # y_test_Cp2 = gani_test_df[cp2_col].astype(float).values
# #
# # Cp2_model = HuberRegressor(max_iter=9000)
# # Cp2_model.fit(X_groups_train, y_train_Cp2)
# #
# # y_train_Cp2_pred = Cp2_model.predict(X_groups_train)
# # y_test_Cp2_pred = Cp2_model.predict(X_groups_test)
# #
# # metrics_Cp2_train = evaluate_regression(y_train_Cp2, y_train_Cp2_pred, "Cp2_model 训练集")
# # metrics_Cp2_test = evaluate_regression(y_test_Cp2, y_test_Cp2_pred, "Cp2_model 测试集")
# #
# # # =========================================================
# # # 6. 用子模型为所有物质预测 slope
# # #    注意：没有真实 slope 标签，所以这里只能“生成预测的 slope”
# # # =========================================================
# # def predict_slope_for_materials(input_df):
# #     X_groups = input_df[group_cols].astype(float)
# #     X_poly_all = poly.transform(X_groups)
# #
# #     records = []
# #
# #     for local_i, (_, row) in enumerate(input_df.iterrows()):
# #         material_id = int(row[material_id_col])
# #
# #         # 关键修改：
# #         # Cp1_model/Cp2_model 训练时用的是带列名的 DataFrame，
# #         # 这里预测时也保持一致，避免 feature names warning
# #         Nk_df = pd.DataFrame(
# #             [row[group_cols].astype(float).values],
# #             columns=group_cols
# #         )
# #
# #         try:
# #             T1 = T1_model.predict(X_poly_all[local_i:local_i+1])[0]
# #             if np.isnan(T1) or T1 <= 0:
# #                 continue
# #
# #             T2 = T1 * 1.5
# #             if np.isclose(T2, T1):
# #                 continue
# #
# #             Cp1 = Cp1_model.predict(Nk_df)[0]
# #             Cp2 = Cp2_model.predict(Nk_df)[0]
# #             slope = (Cp2 - Cp1) / (T2 - T1)
# #
# #             if np.isnan(slope) or np.isinf(slope):
# #                 continue
# #
# #             records.append({
# #                 "Material_ID": material_id,
# #                 "Pred_T1": T1,
# #                 "Pred_T2": T2,
# #                 "Pred_Cp1": Cp1,
# #                 "Pred_Cp2": Cp2,
# #                 "slope": slope
# #             })
# #         except Exception:
# #             continue
# #
# #     return pd.DataFrame(records)
# #
# # slope_train_df = predict_slope_for_materials(gani_train_df)
# # slope_test_df = predict_slope_for_materials(gani_test_df)
# # slope_all_df = pd.concat([slope_train_df, slope_test_df], ignore_index=True)
# #
# # slope_all_df["Split"] = np.where(
# #     slope_all_df["Material_ID"].isin(train_materials), "train", "test"
# # )
# #
# # slope_all_df.to_csv("slope_values_train_test.csv", index=False)
# # print("\n✅ slope 已保存为: slope_values_train_test.csv")
# #
# # # =========================================================
# # # 7. 把 slope 合并进最终回归数据
# # # =========================================================
# # trans_with_slope = trans_df.merge(
# #     slope_all_df[["Material_ID", "slope", "Pred_T1", "Pred_T2", "Pred_Cp1", "Pred_Cp2"]],
# #     on="Material_ID",
# #     how="left"
# # )
# #
# # trans_with_slope["Split"] = np.where(
# #     trans_with_slope["Material_ID"].isin(train_materials), "train", "test"
# # )
# #
# # # 删除没有成功生成 slope 的物质对应行
# # before_drop = len(trans_with_slope)
# # trans_with_slope = trans_with_slope.dropna(subset=["slope"]).copy()
# # after_drop = len(trans_with_slope)
# #
# # print(f"\n合并 slope 后总行数: {before_drop}")
# # print(f"去掉无 slope 行后剩余: {after_drop}")
# #
# # trans_with_slope.to_excel("Transformed_hp_with_slope_and_split.xlsx", index=False)
# # print("✅ 已保存为: Transformed_hp_with_slope_and_split.xlsx")
# #
# # # =========================================================
# # # 8. 最终随机森林模型（只用训练集）
# # # =========================================================
# # final_train_df = trans_with_slope[trans_with_slope["Split"] == "train"].copy()
# # final_test_df = trans_with_slope[trans_with_slope["Split"] == "test"].copy()
# #
# # drop_cols = [target_col_final, "Material_ID", "Split"]
# # feature_cols = [c for c in final_train_df.columns if c not in drop_cols]
# #
# # X_train_final = final_train_df[feature_cols].copy()
# # X_test_final = final_test_df[feature_cols].copy()
# #
# # # 只保留数值列
# # numeric_cols = X_train_final.select_dtypes(include=[np.number]).columns.tolist()
# # X_train_final = X_train_final[numeric_cols].copy()
# # X_test_final = X_test_final[numeric_cols].copy()
# #
# # y_train_final = final_train_df[target_col_final].astype(float).values
# # y_test_final = final_test_df[target_col_final].astype(float).values
# #
# # model = RandomForestRegressor(
# #     n_estimators=300,
# #     random_state=random_state,
# #     n_jobs=-1
# # )
# # model.fit(X_train_final, y_train_final)
# #
# # y_train_final_pred = model.predict(X_train_final)
# # y_test_final_pred = model.predict(X_test_final)
# #
# # metrics_final_train = evaluate_regression(y_train_final, y_train_final_pred, "最终随机森林模型 训练集")
# # metrics_final_test = evaluate_regression(y_test_final, y_test_final_pred, "最终随机森林模型 测试集")
# #
# # # =========================================================
# # # 9. 保存最终预测结果
# # # =========================================================
# # train_result = final_train_df.copy()
# # train_result["Predicted_Heat_Capacity"] = y_train_final_pred
# # train_result["Absolute_Error"] = np.abs(y_train_final - y_train_final_pred)
# # train_result["Relative_Error (%)"] = metrics_final_train["relative_error_%"]
# # train_result.to_excel("train_prediction_vs_actual_hp_with_slope.xlsx", index=False)
# #
# # test_result = final_test_df.copy()
# # test_result["Predicted_Heat_Capacity"] = y_test_final_pred
# # test_result["Absolute_Error"] = np.abs(y_test_final - y_test_final_pred)
# # test_result["Relative_Error (%)"] = metrics_final_test["relative_error_%"]
# # test_result.to_excel("test_prediction_vs_actual_hp_with_slope.xlsx", index=False)
# #
# # print("\n✅ 已保存训练集预测结果: train_prediction_vs_actual_hp_with_slope.xlsx")
# # print("✅ 已保存测试集预测结果: test_prediction_vs_actual_hp_with_slope.xlsx")
# #
# # # =========================================================
# # # 10. 保存评估汇总
# # # =========================================================
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
# #     ["Final_RF_model", "train", metrics_final_train["R2"], metrics_final_train["MSE"], metrics_final_train["ARD_%"],
# #      metrics_final_train["within_1pct"], metrics_final_train["within_5pct"], metrics_final_train["within_10pct"]],
# #     ["Final_RF_model", "test", metrics_final_test["R2"], metrics_final_test["MSE"], metrics_final_test["ARD_%"],
# #      metrics_final_test["within_1pct"], metrics_final_test["within_5pct"], metrics_final_test["within_10pct"]],
# # ]
# #
# # summary_df = pd.DataFrame(summary_rows, columns=[
# #     "Model", "Dataset", "R2", "MSE", "ARD_%", "within_1pct", "within_5pct", "within_10pct"
# # ])
# #
# # summary_df.to_excel("all_model_summary_train_test.xlsx", index=False)
# # print("✅ 已保存评估汇总: all_model_summary_train_test.xlsx")
# # import pandas as pd
# # import numpy as np
# # from sklearn.linear_model import HuberRegressor
# # from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
# # from sklearn.preprocessing import PolynomialFeatures
# # from sklearn.model_selection import train_test_split
# # from sklearn.metrics import mean_squared_error, r2_score
# #
# #
# # # =========================================================
# # # 0. 文件路径
# # # =========================================================
# # gani_file = "heat capacity 207.xlsx"
# # transformed_file = "Transformed_hp_Dataset.xlsx"
# #
# # slope_csv_out = "slope_values.csv"
# # merged_excel_out = "Transformed_hp_with_slope.xlsx"
# # prediction_out = "prediction_vs_actual_hp_with_slope.xlsx"
# # summary_out = "model_summary_hp_with_slope.xlsx"
# #
# #
# # # =========================================================
# # # 1. 读取 Gani 数据，并计算每个物质的 slope
# # # =========================================================
# # print("========== 第1步：计算 slope ==========")
# #
# # gani_df = pd.read_excel(gani_file, sheet_name="Sheet1")
# # gani_df = gani_df.dropna(subset=[gani_df.columns[0]]).copy()
# # gani_df[gani_df.columns[0]] = gani_df[gani_df.columns[0]].astype(int)
# #
# # material_id_col_gani = gani_df.columns[0]
# # group_cols = gani_df.columns[11:30]          # 19个基团列
# # target_column_T1 = "ASPEN Half Critical T"
# #
# # X_groups = gani_df[group_cols].copy()
# # valid_mask = ~gani_df[target_column_T1].isna()
# #
# # # 多项式特征
# # poly = PolynomialFeatures(degree=2, include_bias=False)
# # X_poly = poly.fit_transform(X_groups[valid_mask])
# # y_T1 = gani_df.loc[valid_mask, target_column_T1]
# #
# # # T1 子模型
# # T1_model = GradientBoostingRegressor(
# #     n_estimators=300,
# #     learning_rate=0.05,
# #     max_depth=4,
# #     random_state=0
# # ).fit(X_poly, y_T1)
# #
# # # Cp1 / Cp2 子模型
# # Cp1_model = HuberRegressor(max_iter=9000).fit(X_groups, gani_df.iloc[:, 9])
# # Cp2_model = HuberRegressor(max_iter=9000).fit(X_groups, gani_df.iloc[:, 50])
# #
# # # 对所有样本求 slope
# # X_poly_all = poly.transform(X_groups)
# # slope_dict = {}
# #
# # for i, row in gani_df.iterrows():
# #     material_id = row[material_id_col_gani]
# #     Nk = row[group_cols].values
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
# #
# #         if np.isnan(Cp1) or np.isnan(Cp2) or (T2 - T1) == 0:
# #             continue
# #
# #         slope = (Cp2 - Cp1) / (T2 - T1)
# #         slope_dict[material_id] = slope
# #
# #     except Exception:
# #         continue
# #
# # slope_df = pd.DataFrame(list(slope_dict.items()), columns=["Material_ID", "slope"])
# # slope_df.to_csv(slope_csv_out, index=False)
# #
# # print(f"✅ slope 已保存为: {slope_csv_out}")
# # print(f"✅ 成功计算 slope 的物质数: {len(slope_df)}")
# #
# #
# # # =========================================================
# # # 2. 读取 Transformed 数据，并合并 slope
# # # =========================================================
# # print("\n========== 第2步：合并 slope 到训练表 ==========")
# #
# # train_df = pd.read_excel(transformed_file).copy()
# #
# # # 优先按 Material_ID 合并；如果没有 Material_ID，就退回 repeat(10)
# # if "Material_ID" in train_df.columns:
# #     train_df_with_slope = train_df.merge(slope_df, on="Material_ID", how="left")
# #     print("✅ 检测到 Material_ID，已按 Material_ID 合并 slope")
# # else:
# #     expected_rows = len(slope_df) * 10
# #     if len(train_df) != expected_rows:
# #         print("⚠️ 警告：Transformed_hp_Dataset.xlsx 没有 Material_ID，且行数不等于 slope×10。")
# #         print("⚠️ 将仍然尝试按 repeat(10) 拼接，但请确认数据顺序完全一致。")
# #
# #     slope_expanded = pd.DataFrame({
# #         "slope": slope_df["slope"].repeat(10).values[:len(train_df)]
# #     })
# #     train_df_with_slope = pd.concat(
# #         [train_df.reset_index(drop=True), slope_expanded.reset_index(drop=True)],
# #         axis=1
# #     )
# #     print("✅ 未检测到 Material_ID，已按 repeat(10) 方式拼接 slope")
# #
# # train_df_with_slope.to_excel(merged_excel_out, index=False)
# # print(f"✅ 已成功保存为: {merged_excel_out}")
# #
# #
# # # =========================================================
# # # 3. 建模（仅这里做 8:2 划分）
# # # =========================================================
# # print("\n========== 第3步：最终建模（8:2划分） ==========")
# #
# # df = train_df_with_slope.copy()
# #
# # target_col = "Heat Capacity"
# # if target_col not in df.columns:
# #     raise ValueError(f"找不到目标列: {target_col}")
# #
# # # 去掉目标缺失
# # df = df.dropna(subset=[target_col]).copy()
# #
# # # 特征和目标
# # X = df.drop(columns=[target_col]).copy()
# # y = df[target_col].copy()
# #
# # # 数值化：如果有非数值列，尝试转数值
# # for col in X.columns:
# #     X[col] = pd.to_numeric(X[col], errors="coerce")
# #
# # # 删除包含缺失特征的样本
# # valid_mask = ~X.isna().any(axis=1)
# # X = X.loc[valid_mask].copy()
# # y = y.loc[valid_mask].copy()
# # df = df.loc[valid_mask].copy()
# #
# # print(f"总可用样本数: {len(X)}")
# #
# # # 8:2 划分
# # X_train, X_test, y_train, y_test, df_train, df_test = train_test_split(
# #     X, y, df,
# #     test_size=0.2,
# #     random_state=42
# # )
# #
# # print(f"训练集样本数: {len(X_train)}")
# # print(f"测试集样本数: {len(X_test)}")
# #
# # # 建模
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
# # def evaluate(y_true, y_pred, dataset_name="数据集"):
# #     mse = mean_squared_error(y_true, y_pred)
# #     r2 = r2_score(y_true, y_pred)
# #
# #     y_true = np.array(y_true, dtype=float)
# #     y_pred = np.array(y_pred, dtype=float)
# #
# #     relative_error = np.full_like(y_true, np.nan, dtype=float)
# #     nonzero_mask = np.abs(y_true) > 1e-12
# #     relative_error[nonzero_mask] = np.abs((y_true[nonzero_mask] - y_pred[nonzero_mask]) / y_true[nonzero_mask]) * 100
# #
# #     ard = np.nanmean(relative_error)
# #     within_1pct = np.sum(relative_error <= 1)
# #     within_5pct = np.sum(relative_error <= 5)
# #     within_10pct = np.sum(relative_error <= 10)
# #
# #     print(f"\n📊 {dataset_name}模型评估结果：")
# #     print(f"R²  = {r2:.4f}")
# #     print(f"MSE = {mse:.4f}")
# #     print(f"ARD = {ard:.2f}%")
# #     print(f"✅ 误差 ≤ 1% 的点数: {within_1pct}")
# #     print(f"✅ 误差 ≤ 5% 的点数: {within_5pct}")
# #     print(f"✅ 误差 ≤ 10% 的点数: {within_10pct}")
# #
# #     return {
# #         "R2": r2,
# #         "MSE": mse,
# #         "ARD_%": ard,
# #         "within_1pct": within_1pct,
# #         "within_5pct": within_5pct,
# #         "within_10pct": within_10pct,
# #         "relative_error": relative_error
# #     }
# #
# #
# # # =========================================================
# # # 5. 输出训练集 / 测试集评估
# # # =========================================================
# # train_metrics = evaluate(y_train, y_train_pred, "训练集")
# # test_metrics = evaluate(y_test, y_test_pred, "测试集")
# #
# #
# # # =========================================================
# # # 6. 保存预测结果
# # # =========================================================
# # train_result = df_train.copy()
# # train_result["Set"] = "train"
# # train_result["Predicted_Heat_Capacity"] = y_train_pred
# # train_result["Absolute_Error"] = np.abs(y_train.values - y_train_pred)
# # train_result["Relative_Error (%)"] = train_metrics["relative_error"]
# #
# # test_result = df_test.copy()
# # test_result["Set"] = "test"
# # test_result["Predicted_Heat_Capacity"] = y_test_pred
# # test_result["Absolute_Error"] = np.abs(y_test.values - y_test_pred)
# # test_result["Relative_Error (%)"] = test_metrics["relative_error"]
# #
# # comparison_df = pd.concat([train_result, test_result], axis=0).reset_index(drop=True)
# # comparison_df.to_excel(prediction_out, index=False)
# #
# # print(f"\n✅ 已保存预测结果为: {prediction_out}")
# #
# #
# # # =========================================================
# # # 7. 保存汇总结果
# # # =========================================================
# # summary_df = pd.DataFrame([
# #     ["train", train_metrics["R2"], train_metrics["MSE"], train_metrics["ARD_%"],
# #      train_metrics["within_1pct"], train_metrics["within_5pct"], train_metrics["within_10pct"]],
# #     ["test", test_metrics["R2"], test_metrics["MSE"], test_metrics["ARD_%"],
# #      test_metrics["within_1pct"], test_metrics["within_5pct"], test_metrics["within_10pct"]],
# # ], columns=[
# #     "Dataset", "R2", "MSE", "ARD_%", "within_1pct", "within_5pct", "within_10pct"
# # ])
# #
# # summary_df.to_excel(summary_out, index=False)
# # print(f"✅ 已保存评估汇总为: {summary_out}")
# import pandas as pd
# import numpy as np
#
# from sklearn.linear_model import HuberRegressor
# from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
# from sklearn.preprocessing import PolynomialFeatures
# from sklearn.model_selection import train_test_split
# from sklearn.metrics import mean_squared_error, r2_score
#
#
# # =========================================================
# # 0. 文件路径
# # =========================================================
# gani_file = "heat capacity 207.xlsx"
# transformed_file = "Transformed_hp_Dataset.xlsx"
#
# slope_csv_out = "slope_values.csv"
# merged_excel_out = "Transformed_hp_with_slope.xlsx"
# prediction_out = "prediction_vs_actual_hp_with_slope_by_material.xlsx"
# summary_out = "model_summary_hp_with_slope_by_material.xlsx"
# submodel_summary_out = "submodel_summary_hp_with_slope.xlsx"
#
#
# # =========================================================
# # 0.1 子模型评估函数
# # =========================================================
# def evaluate_submodel(y_true, y_pred, model_name="子模型"):
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#
#     mse = mean_squared_error(y_true, y_pred)
#     r2 = r2_score(y_true, y_pred)
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
#     print(f"\n📌 {model_name} 评估结果：")
#     print(f"R²  = {r2:.4f}")
#     print(f"MSE = {mse:.4f}")
#     print(f"ARD = {ard:.2f}%")
#     print(f"误差 ≤ 1% 的点数: {within_1pct}")
#     print(f"误差 ≤ 5% 的点数: {within_5pct}")
#     print(f"误差 ≤ 10% 的点数: {within_10pct}")
#
#     return {
#         "Model": model_name,
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
# # 1. 读取 Gani 数据，并计算每个物质的 slope
# # =========================================================
# print("========== 第1步：计算 slope ==========")
#
# gani_df = pd.read_excel(gani_file, sheet_name="Sheet1")
# gani_df = gani_df.dropna(subset=[gani_df.columns[0]]).copy()
# gani_df[gani_df.columns[0]] = gani_df[gani_df.columns[0]].astype(int)
#
# material_id_col_gani = gani_df.columns[0]
# group_cols = gani_df.columns[11:30]          # 19个基团列
# target_column_T1 = "ASPEN Half Critical T"
#
# X_groups = gani_df[group_cols].copy()
# valid_mask = ~gani_df[target_column_T1].isna()
#
# # 多项式特征
# poly = PolynomialFeatures(degree=2, include_bias=False)
# X_poly = poly.fit_transform(X_groups[valid_mask])
# y_T1 = gani_df.loc[valid_mask, target_column_T1]
#
# # T1 子模型
# T1_model = GradientBoostingRegressor(
#     n_estimators=300,
#     learning_rate=0.05,
#     max_depth=4,
#     random_state=0
# ).fit(X_poly, y_T1)
#
# # Cp1 / Cp2 子模型
# Cp1_model = HuberRegressor(max_iter=9000).fit(X_groups, gani_df.iloc[:, 9])
# Cp2_model = HuberRegressor(max_iter=9000).fit(X_groups, gani_df.iloc[:, 50])
#
# # =========================================================
# # 1.1 子模型评估
# # =========================================================
# # T1_model 只在 valid_mask 对应样本上评估
# y_T1_pred = T1_model.predict(X_poly)
# t1_metrics = evaluate_submodel(y_T1.values, y_T1_pred, "T1_model")
#
# # Cp1_model
# y_cp1_true = pd.to_numeric(gani_df.iloc[:, 9], errors="coerce").values
# valid_cp1 = np.isfinite(y_cp1_true)
# y_cp1_pred = Cp1_model.predict(X_groups.loc[valid_cp1])
# cp1_metrics = evaluate_submodel(y_cp1_true[valid_cp1], y_cp1_pred, "Cp1_model")
#
# # Cp2_model
# y_cp2_true = pd.to_numeric(gani_df.iloc[:, 50], errors="coerce").values
# valid_cp2 = np.isfinite(y_cp2_true)
# y_cp2_pred = Cp2_model.predict(X_groups.loc[valid_cp2])
# cp2_metrics = evaluate_submodel(y_cp2_true[valid_cp2], y_cp2_pred, "Cp2_model")
#
# # 保存子模型评估汇总
# submodel_summary_df = pd.DataFrame([t1_metrics, cp1_metrics, cp2_metrics])
# submodel_summary_df.to_excel(submodel_summary_out, index=False)
# print(f"\n✅ 已保存子模型评估汇总为: {submodel_summary_out}")
#
# # =========================================================
# # 1.2 对所有样本求 slope
# # =========================================================
# X_poly_all = poly.transform(X_groups)
# slope_dict = {}
#
# for i, row in gani_df.iterrows():
#     material_id = row[material_id_col_gani]
#     Nk = row[group_cols].values
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
#
#         if np.isnan(Cp1) or np.isnan(Cp2) or (T2 - T1) == 0:
#             continue
#
#         slope = (Cp2 - Cp1) / (T2 - T1)
#         slope_dict[material_id] = slope
#
#     except Exception:
#         continue
#
# slope_df = pd.DataFrame(list(slope_dict.items()), columns=["Material_ID", "slope"])
# slope_df.to_csv(slope_csv_out, index=False)
#
# print(f"\n✅ slope 已保存为: {slope_csv_out}")
# print(f"✅ 成功计算 slope 的物质数: {len(slope_df)}")
#
#
# # =========================================================
# # 2. 读取 Transformed 数据，并合并 slope
# # =========================================================
# print("\n========== 第2步：合并 slope 到训练表 ==========")
#
# train_df = pd.read_excel(transformed_file).copy()
#
# # 优先按 Material_ID 合并；如果没有 Material_ID，就退回 repeat(10)
# if "Material_ID" in train_df.columns:
#     train_df_with_slope = train_df.merge(slope_df, on="Material_ID", how="left")
#     print("✅ 检测到 Material_ID，已按 Material_ID 合并 slope")
# else:
#     expected_rows = len(slope_df) * 10
#     if len(train_df) != expected_rows:
#         print("⚠️ 警告：Transformed_hp_Dataset.xlsx 没有 Material_ID，且行数不等于 slope×10。")
#         print("⚠️ 将仍然尝试按 repeat(10) 拼接，但请确认数据顺序完全一致。")
#
#     slope_expanded = pd.DataFrame({
#         "slope": slope_df["slope"].repeat(10).values[:len(train_df)]
#     })
#     train_df_with_slope = pd.concat(
#         [train_df.reset_index(drop=True), slope_expanded.reset_index(drop=True)],
#         axis=1
#     )
#     print("✅ 未检测到 Material_ID，已按 repeat(10) 方式拼接 slope")
#
# train_df_with_slope.to_excel(merged_excel_out, index=False)
# print(f"✅ 已成功保存为: {merged_excel_out}")
#
#
# # =========================================================
# # 3. 建模（按物质做 8:2 划分）
# # =========================================================
# print("\n========== 第3步：最终建模（按物质划分 8:2） ==========")
#
# df = train_df_with_slope.copy()
#
# target_col = "Heat Capacity"
# if target_col not in df.columns:
#     raise ValueError(f"找不到目标列: {target_col}")
#
# # 去掉目标缺失
# df = df.dropna(subset=[target_col]).copy()
#
# # 先确定“物质ID列”
# if "Material_ID" in df.columns:
#     material_col = "Material_ID"
#     print("✅ 使用 Material_ID 按物质划分")
# else:
#     rows_per_material = 10
#     df = df.reset_index(drop=True).copy()
#     df["Pseudo_Material_ID"] = np.arange(len(df)) // rows_per_material
#     material_col = "Pseudo_Material_ID"
#     print("⚠️ 未检测到 Material_ID，改用 Pseudo_Material_ID 按每10行分组")
#
#     if len(df) % rows_per_material != 0:
#         print(f"⚠️ 总行数 {len(df)} 不是 {rows_per_material} 的整数倍，最后一个物质组可能不完整。")
#
# # 特征和目标
# X_all = df.drop(columns=[target_col]).copy()
# y_all = df[target_col].copy()
#
# # 数值化
# for col in X_all.columns:
#     X_all[col] = pd.to_numeric(X_all[col], errors="coerce")
# y_all = pd.to_numeric(y_all, errors="coerce")
#
# # 删除包含缺失特征的样本
# valid_mask = (~X_all.isna().any(axis=1)) & (~y_all.isna())
# X_all = X_all.loc[valid_mask].copy()
# y_all = y_all.loc[valid_mask].copy()
# df = df.loc[valid_mask].copy()
#
# print(f"总可用样本数: {len(X_all)}")
#
# # ========= 先按物质划分 =========
# unique_materials = df[material_col].dropna().unique()
#
# train_materials, test_materials = train_test_split(
#     unique_materials,
#     test_size=0.2,
#     random_state=41
# )
#
# train_materials = set(train_materials)
# test_materials = set(test_materials)
#
# df_train = df[df[material_col].isin(train_materials)].copy()
# df_test = df[df[material_col].isin(test_materials)].copy()
#
# print(f"总物质数: {len(unique_materials)}")
# print(f"训练集物质数: {len(train_materials)}")
# print(f"测试集物质数: {len(test_materials)}")
# print(f"训练集样本数: {len(df_train)}")
# print(f"测试集样本数: {len(df_test)}")
#
# # 再拆特征和目标
# X_train = df_train.drop(columns=[target_col]).copy()
# y_train = df_train[target_col].copy()
#
# X_test = df_test.drop(columns=[target_col]).copy()
# y_test = df_test[target_col].copy()
#
# # 删除非数值列（比如 Material_ID）
# non_numeric_cols = X_train.select_dtypes(exclude=[np.number]).columns.tolist()
# if len(non_numeric_cols) > 0:
#     print(f"⚠️ 检测到非数值列，已删除: {non_numeric_cols}")
#     X_train = X_train.drop(columns=non_numeric_cols)
#     X_test = X_test.drop(columns=non_numeric_cols)
#
# # ========= 模型训练 =========
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
# def evaluate(y_true, y_pred, dataset_name="数据集"):
#     mse = mean_squared_error(y_true, y_pred)
#     r2 = r2_score(y_true, y_pred)
#
#     y_true = np.array(y_true, dtype=float)
#     y_pred = np.array(y_pred, dtype=float)
#
#     relative_error = np.full_like(y_true, np.nan, dtype=float)
#     nonzero_mask = np.abs(y_true) > 1e-12
#     relative_error[nonzero_mask] = np.abs(
#         (y_true[nonzero_mask] - y_pred[nonzero_mask]) / y_true[nonzero_mask]
#     ) * 100
#
#     ard = np.nanmean(relative_error)
#     within_1pct = np.sum(relative_error <= 1)
#     within_5pct = np.sum(relative_error <= 5)
#     within_10pct = np.sum(relative_error <= 10)
#
#     print(f"\n📊 {dataset_name}模型评估结果：")
#     print(f"R²  = {r2:.4f}")
#     print(f"MSE = {mse:.4f}")
#     print(f"ARD = {ard:.2f}%")
#     print(f"✅ 误差 ≤ 1% 的点数: {within_1pct}")
#     print(f"✅ 误差 ≤ 5% 的点数: {within_5pct}")
#     print(f"✅ 误差 ≤ 10% 的点数: {within_10pct}")
#
#     return {
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
# # =========================================================
# # 5. 输出训练集 / 测试集评估
# # =========================================================
# train_metrics = evaluate(y_train, y_train_pred, "训练集")
# test_metrics = evaluate(y_test, y_test_pred, "测试集")
#
#
# # =========================================================
# # 6. 保存预测结果
# # =========================================================
# train_result = df_train.copy()
# train_result["Set"] = "train"
# train_result["Predicted_Heat_Capacity"] = y_train_pred
# train_result["Absolute_Error"] = np.abs(y_train.values - y_train_pred)
# train_result["Relative_Error (%)"] = train_metrics["relative_error"]
#
# test_result = df_test.copy()
# test_result["Set"] = "test"
# test_result["Predicted_Heat_Capacity"] = y_test_pred
# test_result["Absolute_Error"] = np.abs(y_test.values - y_test_pred)
# test_result["Relative_Error (%)"] = test_metrics["relative_error"]
#
# comparison_df = pd.concat([train_result, test_result], axis=0).reset_index(drop=True)
# comparison_df.to_excel(prediction_out, index=False)
#
# print(f"\n✅ 已保存预测结果为: {prediction_out}")
#
#
# # =========================================================
# # 7. 保存汇总结果
# # =========================================================
# summary_df = pd.DataFrame([
#     ["train", train_metrics["R2"], train_metrics["MSE"], train_metrics["ARD_%"],
#      train_metrics["within_1pct"], train_metrics["within_5pct"], train_metrics["within_10pct"]],
#     ["test", test_metrics["R2"], test_metrics["MSE"], test_metrics["ARD_%"],
#      test_metrics["within_1pct"], test_metrics["within_5pct"], test_metrics["within_10pct"]],
# ], columns=[
#     "Dataset", "R2", "MSE", "ARD_%", "within_1pct", "within_5pct", "within_10pct"
# ])
#
# summary_df.to_excel(summary_out, index=False)
# print(f"✅ 已保存评估汇总为: {summary_out}")


import pandas as pd
import numpy as np

from sklearn.linear_model import HuberRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.preprocessing import PolynomialFeatures
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score


# =========================================================
# 0. 文件路径
# =========================================================

gani_file = "heat capacity 207.xlsx"
transformed_file = "Transformed_hp_Dataset.xlsx"

slope_csv_out = "slope_values.csv"
merged_excel_out = "Transformed_hp_with_slope.xlsx"
prediction_out = "prediction_vs_actual_hp_with_slope_by_material.xlsx"
summary_out = "model_summary_hp_with_slope_by_material.xlsx"
submodel_summary_out = "submodel_summary_hp_with_slope.xlsx"


# =========================================================
# 0.1 子模型评估函数
# =========================================================

def evaluate_submodel(y_true, y_pred, model_name="子模型"):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mse = mean_squared_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)

    relative_error = np.full_like(y_true, np.nan, dtype=float)
    nonzero_mask = np.abs(y_true) > 1e-12

    if np.any(nonzero_mask):
        relative_error[nonzero_mask] = np.abs(
            (y_pred[nonzero_mask] - y_true[nonzero_mask]) / y_true[nonzero_mask]
        ) * 100
        ard = np.nanmean(relative_error)
    else:
        ard = np.nan

    within_1pct = np.sum(relative_error <= 1)
    within_5pct = np.sum(relative_error <= 5)
    within_10pct = np.sum(relative_error <= 10)

    print(f"\n{model_name} 评估结果：")
    print(f"R²  = {r2:.4f}")
    print(f"MSE = {mse:.4f}")
    print(f"ARD = {ard:.2f}%")
    print(f"误差 ≤ 1% 的点数: {within_1pct}")
    print(f"误差 ≤ 5% 的点数: {within_5pct}")
    print(f"误差 ≤ 10% 的点数: {within_10pct}")

    return {
        "Model": model_name,
        "R2": r2,
        "MSE": mse,
        "ARD_%": ard,
        "within_1pct": within_1pct,
        "within_5pct": within_5pct,
        "within_10pct": within_10pct
    }


# =========================================================
# 1. 读取 Gani 数据，并计算每个物质的 slope
# =========================================================

print("========== 第1步：计算 slope ==========")

gani_df = pd.read_excel(gani_file, sheet_name="Sheet1")
gani_df = gani_df.dropna(subset=[gani_df.columns[0]]).copy()
gani_df[gani_df.columns[0]] = gani_df[gani_df.columns[0]].astype(int)

material_id_col_gani = gani_df.columns[0]
group_cols = gani_df.columns[11:30]          # 19个基团列
target_column_T1 = "ASPEN Half Critical T"

X_groups = gani_df[group_cols].copy()
valid_mask = ~gani_df[target_column_T1].isna()

# 多项式特征
poly = PolynomialFeatures(degree=2, include_bias=False)
X_poly = poly.fit_transform(X_groups[valid_mask])
y_T1 = gani_df.loc[valid_mask, target_column_T1]

# T1 子模型
T1_model = GradientBoostingRegressor(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=4,
    random_state=0
).fit(X_poly, y_T1)

# Cp1 / Cp2 子模型
Cp1_model = HuberRegressor(max_iter=9000).fit(X_groups, gani_df.iloc[:, 9])
Cp2_model = HuberRegressor(max_iter=9000).fit(X_groups, gani_df.iloc[:, 50])


# =========================================================
# 1.1 子模型评估
# =========================================================

# T1_model 只在 valid_mask 对应样本上评估
y_T1_pred = T1_model.predict(X_poly)
t1_metrics = evaluate_submodel(y_T1.values, y_T1_pred, "T1_model")

# Cp1_model
y_cp1_true = pd.to_numeric(gani_df.iloc[:, 9], errors="coerce").values
valid_cp1 = np.isfinite(y_cp1_true)
y_cp1_pred = Cp1_model.predict(X_groups.loc[valid_cp1])
cp1_metrics = evaluate_submodel(y_cp1_true[valid_cp1], y_cp1_pred, "Cp1_model")

# Cp2_model
y_cp2_true = pd.to_numeric(gani_df.iloc[:, 50], errors="coerce").values
valid_cp2 = np.isfinite(y_cp2_true)
y_cp2_pred = Cp2_model.predict(X_groups.loc[valid_cp2])
cp2_metrics = evaluate_submodel(y_cp2_true[valid_cp2], y_cp2_pred, "Cp2_model")

# 保存子模型评估汇总
submodel_summary_df = pd.DataFrame([t1_metrics, cp1_metrics, cp2_metrics])
submodel_summary_df.to_excel(submodel_summary_out, index=False)
print(f"\n已保存子模型评估汇总为: {submodel_summary_out}")


# =========================================================
# 1.2 对所有样本求 slope
# =========================================================

X_poly_all = poly.transform(X_groups)
slope_dict = {}

for i, row in gani_df.iterrows():
    material_id = row[material_id_col_gani]
    Nk = row[group_cols].values
    Nk_df = pd.DataFrame([Nk], columns=group_cols)
    Nk_poly = X_poly_all[i:i + 1]

    try:
        T1 = T1_model.predict(Nk_poly)[0]
        if T1 <= 0 or np.isnan(T1):
            continue

        T2 = T1 * 1.5
        Cp1 = Cp1_model.predict(Nk_df)[0]
        Cp2 = Cp2_model.predict(Nk_df)[0]

        if np.isnan(Cp1) or np.isnan(Cp2) or (T2 - T1) == 0:
            continue

        slope = (Cp2 - Cp1) / (T2 - T1)
        slope_dict[material_id] = slope

    except Exception:
        continue

slope_df = pd.DataFrame(list(slope_dict.items()), columns=["Material_ID", "slope"])
slope_df.to_csv(slope_csv_out, index=False)

print(f"\nslope 已保存为: {slope_csv_out}")
print(f"成功计算 slope 的物质数: {len(slope_df)}")


# =========================================================
# 2. 读取 Transformed 数据，并合并 slope
# =========================================================

print("\n========== 第2步：合并 slope 到训练表 ==========")

train_df = pd.read_excel(transformed_file).copy()

# 优先按 Material_ID 合并；如果没有 Material_ID，就退回 repeat(10)
if "Material_ID" in train_df.columns:
    train_df_with_slope = train_df.merge(slope_df, on="Material_ID", how="left")
    print("检测到 Material_ID，已按 Material_ID 合并 slope")
else:
    expected_rows = len(slope_df) * 10
    if len(train_df) != expected_rows:
        print("警告：Transformed_hp_Dataset.xlsx 没有 Material_ID，且行数不等于 slope×10。")
        print("将仍然尝试按 repeat(10) 拼接，但请确认数据顺序完全一致。")

    slope_expanded = pd.DataFrame({
        "slope": slope_df["slope"].repeat(10).values[:len(train_df)]
    })

    train_df_with_slope = pd.concat(
        [train_df.reset_index(drop=True), slope_expanded.reset_index(drop=True)],
        axis=1
    )

    print("未检测到 Material_ID，已按 repeat(10) 方式拼接 slope")

train_df_with_slope.to_excel(merged_excel_out, index=False)
print(f"已成功保存为: {merged_excel_out}")


# =========================================================
# 3. 建模（按物质做 8:2 划分）
# =========================================================

print("\n========== 第3步：最终建模（按物质划分 8:2） ==========")

df = train_df_with_slope.copy()

target_col = "Heat Capacity"
if target_col not in df.columns:
    raise ValueError(f"找不到目标列: {target_col}")

# 去掉目标缺失
df = df.dropna(subset=[target_col]).copy()

# 先确定“物质ID列”
if "Material_ID" in df.columns:
    material_col = "Material_ID"
    print("使用 Material_ID 按物质划分")
else:
    rows_per_material = 10
    df = df.reset_index(drop=True).copy()
    df["Pseudo_Material_ID"] = np.arange(len(df)) // rows_per_material
    material_col = "Pseudo_Material_ID"
    print("未检测到 Material_ID，改用 Pseudo_Material_ID 按每10行分组")

    if len(df) % rows_per_material != 0:
        print(f"总行数 {len(df)} 不是 {rows_per_material} 的整数倍，最后一个物质组可能不完整。")

# 特征和目标
X_all = df.drop(columns=[target_col]).copy()
y_all = df[target_col].copy()

# 数值化
for col in X_all.columns:
    X_all[col] = pd.to_numeric(X_all[col], errors="coerce")

y_all = pd.to_numeric(y_all, errors="coerce")

# 删除包含缺失特征的样本
valid_mask = (~X_all.isna().any(axis=1)) & (~y_all.isna())
X_all = X_all.loc[valid_mask].copy()
y_all = y_all.loc[valid_mask].copy()
df = df.loc[valid_mask].copy()

print(f"总可用样本数: {len(X_all)}")

# 按物质划分
unique_materials = df[material_col].dropna().unique()

train_materials, test_materials = train_test_split(
    unique_materials,
    test_size=0.2,
    random_state=41
)

train_materials = set(train_materials)
test_materials = set(test_materials)

df_train = df[df[material_col].isin(train_materials)].copy()
df_test = df[df[material_col].isin(test_materials)].copy()

print(f"总物质数: {len(unique_materials)}")
print(f"训练集物质数: {len(train_materials)}")
print(f"测试集物质数: {len(test_materials)}")
print(f"训练集样本数: {len(df_train)}")
print(f"测试集样本数: {len(df_test)}")

# 再拆特征和目标
X_train = df_train.drop(columns=[target_col]).copy()
y_train = df_train[target_col].copy()

X_test = df_test.drop(columns=[target_col]).copy()
y_test = df_test[target_col].copy()

# 删除非数值列
non_numeric_cols = X_train.select_dtypes(exclude=[np.number]).columns.tolist()
if len(non_numeric_cols) > 0:
    print(f"检测到非数值列，已删除: {non_numeric_cols}")
    X_train = X_train.drop(columns=non_numeric_cols)
    X_test = X_test.drop(columns=non_numeric_cols)

# 模型训练
model = RandomForestRegressor(
    random_state=42,
    n_estimators=300,
    n_jobs=-1
)

model.fit(X_train, y_train)

# 训练集预测
y_train_pred = model.predict(X_train)

# 测试集预测
y_test_pred = model.predict(X_test)


# =========================================================
# 4. 评估函数
# =========================================================

def evaluate(y_true, y_pred, dataset_name="数据集"):
    mse = mean_squared_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)

    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)

    relative_error = np.full_like(y_true, np.nan, dtype=float)
    nonzero_mask = np.abs(y_true) > 1e-12

    relative_error[nonzero_mask] = np.abs(
        (y_true[nonzero_mask] - y_pred[nonzero_mask]) / y_true[nonzero_mask]
    ) * 100

    ard = np.nanmean(relative_error)
    within_1pct = np.sum(relative_error <= 1)
    within_5pct = np.sum(relative_error <= 5)
    within_10pct = np.sum(relative_error <= 10)

    print(f"\n{dataset_name}模型评估结果：")
    print(f"R²  = {r2:.4f}")
    print(f"MSE = {mse:.4f}")
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
        "relative_error": relative_error
    }


# =========================================================
# 5. 输出训练集 / 测试集评估
# =========================================================

train_metrics = evaluate(y_train, y_train_pred, "训练集")
test_metrics = evaluate(y_test, y_test_pred, "测试集")


# =========================================================
# 5.1 完整数据集统计：训练集 + 测试集
# =========================================================

y_all_true_final = np.concatenate([
    np.asarray(y_train, dtype=float),
    np.asarray(y_test, dtype=float)
])

y_all_pred_final = np.concatenate([
    np.asarray(y_train_pred, dtype=float),
    np.asarray(y_test_pred, dtype=float)
])

relative_error_all = np.full_like(y_all_true_final, np.nan, dtype=float)
nonzero_mask_all = np.abs(y_all_true_final) > 1e-12

relative_error_all[nonzero_mask_all] = np.abs(
    (y_all_true_final[nonzero_mask_all] - y_all_pred_final[nonzero_mask_all])
    / y_all_true_final[nonzero_mask_all]
) * 100

all_r2 = r2_score(y_all_true_final, y_all_pred_final)
all_mse = mean_squared_error(y_all_true_final, y_all_pred_final)
all_ard = np.nanmean(relative_error_all)

all_within_1pct = np.sum(relative_error_all < 1)
all_within_5pct = np.sum(relative_error_all < 5)
all_within_10pct = np.sum(relative_error_all < 10)

print("\n完整数据集结果：训练集 + 测试集")
print(f"R²  = {all_r2:.4f}")
print(f"MSE = {all_mse:.4f}")
print(f"ARD = {all_ard:.2f}%")

print("1%，5%，10%分别为：")
print(all_within_1pct)
print(all_within_5pct)
print(all_within_10pct)


# =========================================================
# 6. 保存预测结果
# =========================================================

train_result = df_train.copy()
train_result["Set"] = "train"
train_result["Predicted_Heat_Capacity"] = y_train_pred
train_result["Absolute_Error"] = np.abs(y_train.values - y_train_pred)
train_result["Relative_Error (%)"] = train_metrics["relative_error"]

test_result = df_test.copy()
test_result["Set"] = "test"
test_result["Predicted_Heat_Capacity"] = y_test_pred
test_result["Absolute_Error"] = np.abs(y_test.values - y_test_pred)
test_result["Relative_Error (%)"] = test_metrics["relative_error"]

comparison_df = pd.concat([train_result, test_result], axis=0).reset_index(drop=True)

# 这里重新添加完整数据的相对误差，保证和 train + test 拼接顺序一致
comparison_df["All_Relative_Error (%)"] = relative_error_all

comparison_df.to_excel(prediction_out, index=False)

print(f"\n已保存预测结果为: {prediction_out}")


# =========================================================
# 7. 保存汇总结果
# =========================================================

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

summary_df.to_excel(summary_out, index=False)
print(f"已保存评估汇总为: {summary_out}")