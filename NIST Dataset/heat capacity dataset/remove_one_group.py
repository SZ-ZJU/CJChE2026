# import pandas as pd
# import numpy as np
# from pathlib import Path
#
# from sklearn.linear_model import LinearRegression
# from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
# from sklearn.model_selection import train_test_split
#
#
# pd.set_option("display.float_format", "{:.10f}".format)
# np.set_printoptions(suppress=True, precision=10)
#
#
# # =========================================================
# # 1. 文件路径
# # =========================================================
# file_path = Path("Cp_dataset_with_PubChem_Tb_Tc.xlsx")
#
# groups_sheet = "groups_with_boiling"
# data_sheet = "Sheet1_with_boiling"
#
# output_file = Path("Cp_group_contribution_linear_model_results_iter_unique_removed.xlsx")
#
#
# # =========================================================
# # 2. 基本设置
# # =========================================================
# n_points_per_material = 8
#
# temp_col = "T_K"
# target_col = "property_value"
#
# test_size = 0.2
# random_state = 42
#
# # 基团列范围：保持你原来的写法
# # pandas 中 [2:221) 表示第 3 列到第 221 列之前
# # 如果你想取前 220 个一阶基团，通常应改成 [2:222)
# group_start_idx = 2
# group_end_idx = 221
#
#
# # =========================================================
# # 3. 读取数据
# # =========================================================
# df_groups_raw_original = pd.read_excel(file_path, sheet_name=groups_sheet)
# df_data_original = pd.read_excel(file_path, sheet_name=data_sheet)
#
# print("groups 表行数:", len(df_groups_raw_original))
# print("Sheet1 数据行数:", len(df_data_original))
#
#
# # =========================================================
# # 4. 读取基团列
# # =========================================================
# group_cols_raw = df_groups_raw_original.columns[group_start_idx:group_end_idx]
#
# df_groups_original = df_groups_raw_original[group_cols_raw].copy()
# df_groups_original = df_groups_original.apply(pd.to_numeric, errors="coerce").fillna(0.0)
#
# print("原始基团列数量:", len(group_cols_raw))
#
#
# # =========================================================
# # 5. 检查 Sheet1 和 groups 是否匹配
# # =========================================================
# if temp_col not in df_data_original.columns:
#     raise ValueError(f"Sheet1 中没有找到温度列: {temp_col}")
#
# if target_col not in df_data_original.columns:
#     raise ValueError(f"Sheet1 中没有找到热容列: {target_col}")
#
# if len(df_data_original) % n_points_per_material != 0:
#     raise ValueError(
#         f"Sheet1 行数 {len(df_data_original)} 不能被 {n_points_per_material} 整除。"
#         "请检查是否每个物质都是 8 行。"
#     )
#
# n_materials_data_original = len(df_data_original) // n_points_per_material
# n_materials_groups_original = len(df_groups_original)
#
# print("Sheet1 中物质数量:", n_materials_data_original)
# print("groups 中物质数量:", n_materials_groups_original)
#
# if n_materials_data_original != n_materials_groups_original:
#     raise ValueError(
#         "Sheet1 中的物质数量和 groups 表行数不一致。\n"
#         f"Sheet1 物质数 = {n_materials_data_original}, groups 行数 = {n_materials_groups_original}\n"
#         "当前代码默认 Sheet1 的物质顺序和 groups 的物质顺序一一对应。"
#     )
#
#
# # =========================================================
# # 6. 工具函数：从原始 Sheet1 中提取物质信息
# # =========================================================
# material_info_cols = [
#     "compound_name",
#     "cas",
#     "formula",
#     "SMILES",
#     "smiles",
#     "pubchem_cid",
#     "material_key",
#     "phase",
#     "boiling_T_K",
#     "critical_T_K",
# ]
#
#
# def get_material_info(material_original_index):
#     """
#     根据原始物质序号，从原始 Sheet1 的第一行温度点中提取物质信息。
#     """
#     info = {}
#     first_row_idx = material_original_index * n_points_per_material
#
#     if first_row_idx >= len(df_data_original):
#         return info
#
#     for col in material_info_cols:
#         if col in df_data_original.columns:
#             info[col] = df_data_original.iloc[first_row_idx][col]
#
#     return info
#
#
# # =========================================================
# # 7. 迭代筛选：
# #    1. 删除全零列；
# #    2. 删除只出现在 1 个物质中的基团列；
# #    3. 删除含这些唯一基团的物质；
# #    4. 重复，直到没有新的唯一基团。
# # =========================================================
# df_groups_current = df_groups_original.copy()
#
# # 保持原始物质索引，后面用于同步过滤 Sheet1
# df_groups_current.index = np.arange(len(df_groups_current))
#
# removed_zero_group_records = []
# removed_unique_group_records = []
# removed_material_records = []
# iteration_records = []
#
# iteration = 0
#
# print("\n========== 迭代删除唯一基团及对应物质 ==========")
#
# while True:
#     iteration += 1
#
#     n_materials_before = df_groups_current.shape[0]
#     n_groups_before = df_groups_current.shape[1]
#
#     if n_materials_before == 0:
#         raise ValueError("所有物质都被删除了，无法继续建模。")
#
#     if n_groups_before == 0:
#         raise ValueError("所有基团列都被删除了，无法继续建模。")
#
#     # -----------------------------------------------------
#     # 7.1 每轮先删除全零基团列
#     #     删除物质后，可能产生新的全零列。
#     # -----------------------------------------------------
#     zero_mask = df_groups_current.abs().sum(axis=0) == 0
#     zero_cols = df_groups_current.columns[zero_mask].tolist()
#
#     for col in zero_cols:
#         removed_zero_group_records.append({
#             "iteration": iteration,
#             "removed_all_zero_group": col,
#             "reason": "all_zero_after_material_filter" if iteration > 1 else "all_zero_initial",
#         })
#
#     if zero_cols:
#         df_groups_current = df_groups_current.drop(columns=zero_cols)
#
#     n_groups_after_zero = df_groups_current.shape[1]
#
#     if n_groups_after_zero == 0:
#         raise ValueError("删除全零列后没有剩余基团，无法建模。")
#
#     # -----------------------------------------------------
#     # 7.2 检查只出现在 1 个物质中的基团
#     # -----------------------------------------------------
#     occurrence = (df_groups_current != 0).sum(axis=0)
#     total_count = df_groups_current.sum(axis=0)
#
#     unique_group_cols = occurrence[occurrence == 1].index.tolist()
#
#     # 没有唯一基团，迭代结束
#     if len(unique_group_cols) == 0:
#         iteration_records.append({
#             "iteration": iteration,
#             "n_materials_before": n_materials_before,
#             "n_groups_before": n_groups_before,
#             "removed_zero_group_count": len(zero_cols),
#             "n_groups_after_zero": n_groups_after_zero,
#             "unique_group_count": 0,
#             "removed_material_count": 0,
#             "n_materials_after": df_groups_current.shape[0],
#             "n_groups_after": df_groups_current.shape[1],
#             "status": "stop_no_unique_group",
#         })
#
#         print(
#             f"第 {iteration} 轮：删除全零列 {len(zero_cols)} 个，"
#             f"唯一基团 0 个，停止迭代。"
#         )
#         break
#
#     # -----------------------------------------------------
#     # 7.3 找出这些唯一基团所在的物质
#     # -----------------------------------------------------
#     group_to_unique_material = {}
#
#     for col in unique_group_cols:
#         material_indices = df_groups_current.index[df_groups_current[col] != 0].tolist()
#
#         if len(material_indices) == 1:
#             material_original_index = material_indices[0]
#         else:
#             # 理论上不会发生，因为 occurrence == 1
#             material_original_index = None
#
#         group_to_unique_material[col] = material_original_index
#
#         record = {
#             "iteration": iteration,
#             "removed_unique_group": col,
#             "occurrence_material_count": int(occurrence[col]),
#             "total_count": float(total_count[col]),
#             "unique_material_original_index": material_original_index,
#         }
#
#         if material_original_index is not None:
#             record.update(get_material_info(material_original_index))
#
#         removed_unique_group_records.append(record)
#
#     # -----------------------------------------------------
#     # 7.4 删除所有含唯一基团的物质
#     # -----------------------------------------------------
#     has_unique_group = (df_groups_current[unique_group_cols] != 0).any(axis=1)
#     material_indices_to_remove = df_groups_current.index[has_unique_group].tolist()
#
#     for material_original_index in material_indices_to_remove:
#         unique_groups_in_material = [
#             col for col in unique_group_cols
#             if df_groups_current.loc[material_original_index, col] != 0
#         ]
#
#         record = {
#             "iteration": iteration,
#             "removed_material_original_index": material_original_index,
#             "unique_group_count_in_material": len(unique_groups_in_material),
#             "unique_groups_in_material": "; ".join(unique_groups_in_material),
#         }
#
#         record.update(get_material_info(material_original_index))
#         removed_material_records.append(record)
#
#     # 删除唯一基团列 + 对应物质行
#     df_groups_current = df_groups_current.drop(columns=unique_group_cols)
#     df_groups_current = df_groups_current.drop(index=material_indices_to_remove)
#
#     iteration_records.append({
#         "iteration": iteration,
#         "n_materials_before": n_materials_before,
#         "n_groups_before": n_groups_before,
#         "removed_zero_group_count": len(zero_cols),
#         "n_groups_after_zero": n_groups_after_zero,
#         "unique_group_count": len(unique_group_cols),
#         "removed_material_count": len(material_indices_to_remove),
#         "n_materials_after": df_groups_current.shape[0],
#         "n_groups_after": df_groups_current.shape[1],
#         "status": "continue_removed_unique_groups",
#     })
#
#     print(
#         f"第 {iteration} 轮：删除全零列 {len(zero_cols)} 个，"
#         f"删除唯一基团 {len(unique_group_cols)} 个，"
#         f"删除物质 {len(material_indices_to_remove)} 个，"
#         f"剩余物质 {df_groups_current.shape[0]} 个，"
#         f"剩余基团 {df_groups_current.shape[1]} 个。"
#     )
#
#
# # =========================================================
# # 8. 过滤后的 groups 和 Sheet1
# # =========================================================
# final_material_original_indices = df_groups_current.index.to_numpy()
# used_group_cols = df_groups_current.columns.tolist()
#
# df_groups_used = df_groups_current.reset_index(drop=True).copy()
#
# df_groups_raw_filtered = (
#     df_groups_raw_original
#     .iloc[final_material_original_indices]
#     .reset_index(drop=True)
#     .copy()
# )
#
# # 同步过滤 Sheet1：每个物质 8 行
# keep_data_indices = []
#
# for material_original_index in final_material_original_indices:
#     start = material_original_index * n_points_per_material
#     end = start + n_points_per_material
#     keep_data_indices.extend(range(start, end))
#
# df_data = df_data_original.iloc[keep_data_indices].reset_index(drop=True).copy()
#
# print("\n========== 最终筛选结果 ==========")
# print("原始物质数:", len(df_groups_original))
# print("最终保留物质数:", len(df_groups_used))
# print("原始基团数:", len(group_cols_raw))
# print("最终保留基团数:", len(used_group_cols))
# print("Sheet1 原始行数:", len(df_data_original))
# print("Sheet1 最终行数:", len(df_data))
#
#
# # =========================================================
# # 9. 生成筛选报告
# # =========================================================
# df_removed_zero_groups = pd.DataFrame(removed_zero_group_records)
# df_removed_unique_groups = pd.DataFrame(removed_unique_group_records)
# df_removed_materials = pd.DataFrame(removed_material_records)
# df_iteration_summary = pd.DataFrame(iteration_records)
#
# # 最终保留基团统计
# if len(used_group_cols) > 0:
#     final_occurrence = (df_groups_used != 0).sum(axis=0)
#     final_total_count = df_groups_used.sum(axis=0)
#
#     df_used_groups = pd.DataFrame({
#         "used_group": used_group_cols,
#         "final_occurrence_material_count": final_occurrence[used_group_cols].values,
#         "final_total_count": final_total_count[used_group_cols].values,
#     })
# else:
#     df_used_groups = pd.DataFrame(columns=[
#         "used_group",
#         "final_occurrence_material_count",
#         "final_total_count",
#     ])
#
# df_group_filter_summary = pd.DataFrame([
#     {"item": "original_material_count", "value": len(df_groups_original)},
#     {"item": "final_material_count", "value": len(df_groups_used)},
#     {"item": "removed_material_count", "value": len(df_groups_original) - len(df_groups_used)},
#     {"item": "original_group_count", "value": len(group_cols_raw)},
#     {"item": "final_group_count", "value": len(used_group_cols)},
#     {"item": "removed_all_zero_group_count", "value": len(df_removed_zero_groups)},
#     {"item": "removed_unique_group_count", "value": len(df_removed_unique_groups)},
#     {"item": "iteration_count", "value": len(df_iteration_summary)},
# ])
#
#
# # =========================================================
# # 10. 检查最终是否仍有唯一基团
# # =========================================================
# final_occurrence_check = (df_groups_used != 0).sum(axis=0)
#
# final_unique_cols = final_occurrence_check[final_occurrence_check == 1].index.tolist()
# final_zero_cols = df_groups_used.columns[df_groups_used.abs().sum(axis=0) == 0].tolist()
#
# if len(final_unique_cols) > 0:
#     raise ValueError(
#         "迭代筛选结束后仍然存在只出现在 1 个物质中的基团，逻辑异常："
#         + "; ".join(final_unique_cols)
#     )
#
# if len(final_zero_cols) > 0:
#     raise ValueError(
#         "迭代筛选结束后仍然存在全零基团，逻辑异常："
#         + "; ".join(final_zero_cols)
#     )
#
# print("\n最终检查：")
# print("最终全零基团数:", len(final_zero_cols))
# print("最终唯一基团数:", len(final_unique_cols))
#
#
# # =========================================================
# # 11. 检查删除后是否仍存在重复基团向量
# # =========================================================
# df_vector_check = df_groups_used.copy()
#
# if len(df_vector_check) > 0 and df_vector_check.shape[1] > 0:
#     df_vector_check["feature_vector_key"] = df_vector_check.apply(
#         lambda row: tuple(row.astype(float).values.tolist()),
#         axis=1
#     )
#
#     vector_counts = df_vector_check["feature_vector_key"].value_counts()
#     duplicate_vector_keys = vector_counts[vector_counts > 1].index
#
#     duplicate_rows = []
#
#     for dup_id, key in enumerate(duplicate_vector_keys, start=1):
#         filtered_indices = df_vector_check.index[df_vector_check["feature_vector_key"] == key].tolist()
#
#         for filtered_idx in filtered_indices:
#             original_idx = int(final_material_original_indices[filtered_idx])
#
#             row = {
#                 "duplicate_group_id": dup_id,
#                 "material_index_after_filter": filtered_idx,
#                 "material_index_original": original_idx,
#                 "same_vector_material_count": len(filtered_indices),
#             }
#
#             row.update(get_material_info(original_idx))
#             duplicate_rows.append(row)
#
#     df_duplicate_vector_report = pd.DataFrame(duplicate_rows)
#
# else:
#     df_duplicate_vector_report = pd.DataFrame(columns=[
#         "duplicate_group_id",
#         "material_index_after_filter",
#         "material_index_original",
#         "same_vector_material_count",
#     ])
#
# print("最终重复基团向量组数:",
#       df_duplicate_vector_report["duplicate_group_id"].nunique() if len(df_duplicate_vector_report) > 0 else 0)
# print("最终涉及重复向量的物质数:", len(df_duplicate_vector_report))
#
#
# # =========================================================
# # 12. 过滤后数据检查
# # =========================================================
# if len(df_data) % n_points_per_material != 0:
#     raise ValueError(
#         f"过滤后 Sheet1 行数 {len(df_data)} 不能被 {n_points_per_material} 整除。"
#     )
#
# n_materials_data = len(df_data) // n_points_per_material
# n_materials_groups = len(df_groups_used)
#
# print("\n========== 过滤后数据检查 ==========")
# print("过滤后 Sheet1 中物质数量:", n_materials_data)
# print("过滤后 groups 中物质数量:", n_materials_groups)
#
# if n_materials_data != n_materials_groups:
#     raise ValueError(
#         "过滤后 Sheet1 中的物质数量和 groups 表行数不一致。\n"
#         f"Sheet1 物质数 = {n_materials_data}, groups 行数 = {n_materials_groups}"
#     )
#
# if len(used_group_cols) == 0:
#     raise ValueError("迭代删除后没有剩余基团，无法建模。")
#
# if n_materials_groups < 3:
#     raise ValueError("迭代删除后剩余物质过少，无法进行稳定训练/测试划分。")
#
#
# # =========================================================
# # 13. 构造建模数据
# # 模型：
# # Cp = intercept + Σ Nk * Ak + Σ Nk * Bk * T
# # 特征：
# # [Nk, Nk*T]
# # =========================================================
# X_list = []
# y_list = []
# material_id_list = []
# temperature_list = []
# original_row_index_list = []
#
# for material_idx in range(n_materials_groups):
#     Nk = df_groups_used.iloc[material_idx].values.astype(float)
#
#     start = material_idx * n_points_per_material
#     end = start + n_points_per_material
#
#     sub_data = df_data.iloc[start:end].copy()
#
#     T_values = pd.to_numeric(sub_data[temp_col], errors="coerce").values.astype(float)
#     Cp_values = pd.to_numeric(sub_data[target_col], errors="coerce").values.astype(float)
#
#     for local_i, (T, Cp) in enumerate(zip(T_values, Cp_values)):
#         if not np.isfinite(T) or not np.isfinite(Cp):
#             continue
#
#         feature_A = Nk
#         feature_B = Nk * T
#
#         feature = np.concatenate([feature_A, feature_B])
#
#         X_list.append(feature)
#         y_list.append(Cp)
#         material_id_list.append(material_idx)
#         temperature_list.append(T)
#         original_row_index_list.append(start + local_i)
#
# X = np.array(X_list, dtype=float)
# y = np.array(y_list, dtype=float)
# material_ids = np.array(material_id_list)
# temperatures = np.array(temperature_list)
# original_row_indices = np.array(original_row_index_list)
#
# print("\n========== 建模矩阵 ==========")
# print("最终建模数据点数:", X.shape[0])
# print("最终特征数:", X.shape[1])
# print("A_k 参数数量:", len(used_group_cols))
# print("B_k 参数数量:", len(used_group_cols))
#
#
# # =========================================================
# # 14. 按物质 8:2 划分训练集和测试集
# # =========================================================
# unique_materials = np.unique(material_ids)
#
# train_materials, test_materials = train_test_split(
#     unique_materials,
#     test_size=test_size,
#     random_state=random_state
# )
#
# train_mask = np.isin(material_ids, train_materials)
# test_mask = np.isin(material_ids, test_materials)
#
# X_train = X[train_mask]
# X_test = X[test_mask]
#
# y_train = y[train_mask]
# y_test = y[test_mask]
#
# print("\n========== 训练/测试划分 ==========")
# print("训练物质数:", len(train_materials))
# print("测试物质数:", len(test_materials))
# print("训练数据点数:", len(y_train))
# print("测试数据点数:", len(y_test))
#
#
# # =========================================================
# # 15. 线性回归拟合
# # =========================================================
# model = LinearRegression(fit_intercept=True)
# model.fit(X_train, y_train)
#
# y_train_pred = model.predict(X_train)
# y_test_pred = model.predict(X_test)
# y_all_pred = model.predict(X)
#
#
# # =========================================================
# # 16. 评价指标
# # =========================================================
# def calc_metrics(y_true, y_pred, name):
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#
#     error = y_pred - y_true
#     abs_error = np.abs(error)
#
#     valid_mask = np.abs(y_true) > 1e-12
#
#     if valid_mask.sum() > 0:
#         relative_error_percent = np.abs(
#             (y_pred[valid_mask] - y_true[valid_mask]) / y_true[valid_mask]
#         ) * 100
#
#         ard = np.mean(relative_error_percent)
#         max_relative_error = np.max(relative_error_percent)
#
#         ratio_le_1 = np.mean(relative_error_percent <= 1) * 100
#         ratio_le_5 = np.mean(relative_error_percent <= 5) * 100
#         ratio_le_10 = np.mean(relative_error_percent <= 10) * 100
#     else:
#         ard = np.nan
#         max_relative_error = np.nan
#         ratio_le_1 = np.nan
#         ratio_le_5 = np.nan
#         ratio_le_10 = np.nan
#
#     mse = mean_squared_error(y_true, y_pred)
#     rmse = np.sqrt(mse)
#     mae = mean_absolute_error(y_true, y_pred)
#     r2 = r2_score(y_true, y_pred)
#
#     return {
#         "dataset": name,
#         "n_points": len(y_true),
#         "R2": r2,
#         "MSE": mse,
#         "RMSE": rmse,
#         "MAE": mae,
#         "ARD_percent": ard,
#         "max_abs_error": np.max(abs_error),
#         "max_relative_error_percent": max_relative_error,
#         "relative_error_le_1_percent_ratio": ratio_le_1,
#         "relative_error_le_5_percent_ratio": ratio_le_5,
#         "relative_error_le_10_percent_ratio": ratio_le_10,
#     }
#
#
# metrics = pd.DataFrame([
#     calc_metrics(y_train, y_train_pred, "train"),
#     calc_metrics(y_test, y_test_pred, "test"),
#     calc_metrics(y, y_all_pred, "all")
# ])
#
# print("\n================ 模型评价指标 ================")
# print(metrics.to_string(index=False))
#
# print("\n训练集 R2:", "{:.10f}".format(metrics.loc[metrics["dataset"] == "train", "R2"].values[0]))
# print("测试集 R2:", "{:.10f}".format(metrics.loc[metrics["dataset"] == "test", "R2"].values[0]))
# print("整体 R2:", "{:.10f}".format(metrics.loc[metrics["dataset"] == "all", "R2"].values[0]))
#
# print("\n训练集 ARD(%):", "{:.10f}".format(metrics.loc[metrics["dataset"] == "train", "ARD_percent"].values[0]))
# print("测试集 ARD(%):", "{:.10f}".format(metrics.loc[metrics["dataset"] == "test", "ARD_percent"].values[0]))
# print("整体 ARD(%):", "{:.10f}".format(metrics.loc[metrics["dataset"] == "all", "ARD_percent"].values[0]))
#
#
# # =========================================================
# # 17. 拆分参数 A_k 和 B_k
# # =========================================================
# coef = model.coef_
# intercept = model.intercept_
#
# n_groups = len(used_group_cols)
#
# A_params = coef[:n_groups]
# B_params = coef[n_groups:]
#
# df_params = pd.DataFrame({
#     "group_name": used_group_cols,
#     "A_k": A_params,
#     "B_k": B_params,
# })
#
# df_intercept = pd.DataFrame({
#     "parameter": ["intercept"],
#     "value": [intercept],
# })
#
# print("\n模型截距 intercept:")
# print("{:.10f}".format(intercept))
#
# print("\n前 10 个基团参数:")
# print(df_params.head(10))
#
#
# # =========================================================
# # 18. 整理逐点预测结果
# # =========================================================
# df_pred = pd.DataFrame({
#     "material_index_after_filter": material_ids,
#     "material_index_original": [
#         int(final_material_original_indices[m]) for m in material_ids
#     ],
#     "original_row_index_in_filtered_Sheet1": original_row_indices,
#     "T_K": temperatures,
#     "Cp_exp": y,
#     "Cp_pred": y_all_pred,
#     "error": y_all_pred - y,
#     "abs_error": np.abs(y_all_pred - y),
#     "relative_error_percent": np.where(
#         np.abs(y) > 1e-12,
#         np.abs((y_all_pred - y) / y) * 100,
#         np.nan
#     ),
#     "dataset": np.where(train_mask, "train", "test"),
# })
#
# extra_cols = [
#     "compound_name",
#     "cas",
#     "formula",
#     "SMILES",
#     "smiles",
#     "pubchem_cid",
#     "material_key",
#     "phase",
#     "boiling_T_K",
#     "critical_T_K",
# ]
#
# for col in extra_cols:
#     if col in df_data.columns:
#         values = []
#         for row_idx in original_row_indices:
#             values.append(df_data.iloc[row_idx][col])
#         df_pred[col] = values
#
#
# # =========================================================
# # 19. 整理物质级别划分信息
# # =========================================================
# df_material_split = pd.DataFrame({
#     "material_index_after_filter": unique_materials,
#     "material_index_original": [
#         int(final_material_original_indices[m]) for m in unique_materials
#     ],
#     "dataset": ["train" if m in train_materials else "test" for m in unique_materials],
# })
#
# for col in extra_cols:
#     if col in df_data.columns:
#         values = []
#         for material_idx in unique_materials:
#             row_idx = material_idx * n_points_per_material
#             values.append(df_data.iloc[row_idx][col])
#         df_material_split[col] = values
#
#
# # =========================================================
# # 20. 保存 Excel，不使用科学计数法显示
# # =========================================================
# with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
#     df_pred.to_excel(writer, sheet_name="Prediction", index=False)
#     df_params.to_excel(writer, sheet_name="Group_Params", index=False)
#     df_intercept.to_excel(writer, sheet_name="Intercept", index=False)
#     metrics.to_excel(writer, sheet_name="Metrics", index=False)
#     df_material_split.to_excel(writer, sheet_name="Material_Split", index=False)
#
#     df_used_groups.to_excel(writer, sheet_name="Used_Groups", index=False)
#     df_group_filter_summary.to_excel(writer, sheet_name="Group_Filter_Summary", index=False)
#     df_iteration_summary.to_excel(writer, sheet_name="Iteration_Summary", index=False)
#     df_removed_zero_groups.to_excel(writer, sheet_name="Removed_All_Zero_Groups", index=False)
#     df_removed_unique_groups.to_excel(writer, sheet_name="Removed_Unique_Groups", index=False)
#     df_removed_materials.to_excel(writer, sheet_name="Removed_Materials_Unique", index=False)
#     df_duplicate_vector_report.to_excel(writer, sheet_name="Duplicate_Vector_Report", index=False)
#
#     # 额外保存过滤后的数据，方便后续复用
#     df_data.to_excel(writer, sheet_name="Filtered_Sheet1", index=False)
#     df_groups_raw_filtered.to_excel(writer, sheet_name="Filtered_Groups_Raw", index=False)
#     df_groups_used.to_excel(writer, sheet_name="Filtered_Groups_Used", index=False)
#
#     number_format = "0.0000000000"
#
#     for sheet_name in writer.sheets:
#         ws = writer.sheets[sheet_name]
#
#         for row in ws.iter_rows():
#             for cell in row:
#                 if isinstance(cell.value, float):
#                     cell.number_format = number_format
#
#         for col_cells in ws.columns:
#             max_length = 0
#             col_letter = col_cells[0].column_letter
#
#             for cell in col_cells:
#                 if cell.value is not None:
#                     max_length = max(max_length, len(str(cell.value)))
#
#             ws.column_dimensions[col_letter].width = min(max_length + 2, 35)
#
# print("\n保存完成:", output_file)

import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.model_selection import train_test_split


pd.set_option("display.float_format", "{:.10f}".format)
np.set_printoptions(suppress=True, precision=10)


# =========================================================
# 1. 文件路径
# =========================================================
file_path = Path("Cp_dataset_with_PubChem_Tb_Tc.xlsx")

groups_sheet = "groups_with_boiling"
data_sheet = "Sheet1_with_boiling"

output_file = Path("Cp_group_contribution_linear_model_results_iter_lowocc_removed.xlsx")


# =========================================================
# 2. 基本设置
# =========================================================
n_points_per_material = 8

temp_col = "T_K"
target_col = "property_value"

test_size = 0.2
random_state = 42

# 基团列范围
# 你原来写的是 [2:221)，即 pandas 第3列到第220列
# 如果你想取前220个一阶基团，通常是 [2:222)
group_start_idx = 2
group_end_idx = 221

# =========================================================
# 2.1 低频基团迭代删除阈值
# =========================================================
# 至少出现在多少个物质中才保留
# 3 表示：出现在 1 或 2 个物质中的基团都会被删除，
# 同时删除包含这些基团的物质，然后重新检查。
min_occurrence_required = 3


# =========================================================
# 3. 读取数据
# =========================================================
df_groups_raw_original = pd.read_excel(file_path, sheet_name=groups_sheet)
df_data_original = pd.read_excel(file_path, sheet_name=data_sheet)

print("groups 表行数:", len(df_groups_raw_original))
print("Sheet1 数据行数:", len(df_data_original))


# =========================================================
# 4. 读取基团列
# =========================================================
group_cols_raw = df_groups_raw_original.columns[group_start_idx:group_end_idx]

df_groups_original = df_groups_raw_original[group_cols_raw].copy()
df_groups_original = df_groups_original.apply(pd.to_numeric, errors="coerce").fillna(0.0)

print("原始基团列数量:", len(group_cols_raw))


# =========================================================
# 5. 检查 Sheet1 和 groups 是否匹配
# =========================================================
if temp_col not in df_data_original.columns:
    raise ValueError(f"Sheet1 中没有找到温度列: {temp_col}")

if target_col not in df_data_original.columns:
    raise ValueError(f"Sheet1 中没有找到热容列: {target_col}")

if len(df_data_original) % n_points_per_material != 0:
    raise ValueError(
        f"Sheet1 行数 {len(df_data_original)} 不能被 {n_points_per_material} 整除。"
        "请检查是否每个物质都是 8 行。"
    )

n_materials_data_original = len(df_data_original) // n_points_per_material
n_materials_groups_original = len(df_groups_original)

print("Sheet1 中物质数量:", n_materials_data_original)
print("groups 中物质数量:", n_materials_groups_original)

if n_materials_data_original != n_materials_groups_original:
    raise ValueError(
        "Sheet1 中的物质数量和 groups 表行数不一致。\n"
        f"Sheet1 物质数 = {n_materials_data_original}, groups 行数 = {n_materials_groups_original}\n"
        "当前代码默认 Sheet1 的物质顺序和 groups 的物质顺序一一对应。"
    )


# =========================================================
# 6. 工具函数：从原始 Sheet1 中提取物质信息
# =========================================================
material_info_cols = [
    "compound_name",
    "cas",
    "formula",
    "SMILES",
    "smiles",
    "pubchem_cid",
    "material_key",
    "phase",
    "boiling_T_K",
    "critical_T_K",
]


def get_material_info(material_original_index):
    """
    根据原始物质序号，从原始 Sheet1 的第一行温度点中提取物质信息。
    """
    info = {}
    first_row_idx = material_original_index * n_points_per_material

    if first_row_idx >= len(df_data_original):
        return info

    for col in material_info_cols:
        if col in df_data_original.columns:
            info[col] = df_data_original.iloc[first_row_idx][col]

    return info


# =========================================================
# 7. 迭代筛选：
#    1. 删除全零列；
#    2. 删除出现物质数 < min_occurrence_required 的基团列；
#    3. 删除含这些低频基团的物质；
#    4. 重复，直到没有新的低频基团。
# =========================================================
df_groups_current = df_groups_original.copy()

# 保持原始物质索引，后面用于同步过滤 Sheet1
df_groups_current.index = np.arange(len(df_groups_current))

removed_zero_group_records = []
removed_lowocc_group_records = []
removed_material_records = []
iteration_records = []

iteration = 0

print("\n========== 迭代删除低频基团及对应物质 ==========")
print("低频定义：出现物质数 <", min_occurrence_required)
print("也就是：出现在 1 或 2 个物质中的基团都会被删除。")

while True:
    iteration += 1

    n_materials_before = df_groups_current.shape[0]
    n_groups_before = df_groups_current.shape[1]

    if n_materials_before == 0:
        raise ValueError("所有物质都被删除了，无法继续建模。")

    if n_groups_before == 0:
        raise ValueError("所有基团列都被删除了，无法继续建模。")

    # -----------------------------------------------------
    # 7.1 每轮先删除全零基团列
    #     删除物质后，可能产生新的全零列。
    # -----------------------------------------------------
    zero_mask = df_groups_current.abs().sum(axis=0) == 0
    zero_cols = df_groups_current.columns[zero_mask].tolist()

    for col in zero_cols:
        removed_zero_group_records.append({
            "iteration": iteration,
            "removed_all_zero_group": col,
            "reason": "all_zero_after_material_filter" if iteration > 1 else "all_zero_initial",
        })

    if zero_cols:
        df_groups_current = df_groups_current.drop(columns=zero_cols)

    n_groups_after_zero = df_groups_current.shape[1]

    if n_groups_after_zero == 0:
        raise ValueError("删除全零列后没有剩余基团，无法建模。")

    # -----------------------------------------------------
    # 7.2 检查低频基团：
    #     occurrence 是非零物质个数，不是列总和。
    # -----------------------------------------------------
    occurrence = (df_groups_current != 0).sum(axis=0)
    total_count = df_groups_current.sum(axis=0)

    lowocc_group_cols = occurrence[
        occurrence < min_occurrence_required
    ].index.tolist()

    # 没有低频基团，迭代结束
    if len(lowocc_group_cols) == 0:
        iteration_records.append({
            "iteration": iteration,
            "n_materials_before": n_materials_before,
            "n_groups_before": n_groups_before,
            "removed_zero_group_count": len(zero_cols),
            "n_groups_after_zero": n_groups_after_zero,
            "lowocc_group_count": 0,
            "removed_material_count": 0,
            "n_materials_after": df_groups_current.shape[0],
            "n_groups_after": df_groups_current.shape[1],
            "status": "stop_no_lowocc_group",
        })

        print(
            f"第 {iteration} 轮：删除全零列 {len(zero_cols)} 个，"
            f"低频基团 0 个，停止迭代。"
        )
        break

    # -----------------------------------------------------
    # 7.3 记录低频基团所在的物质
    # -----------------------------------------------------
    for col in lowocc_group_cols:
        material_indices = df_groups_current.index[df_groups_current[col] != 0].tolist()

        record = {
            "iteration": iteration,
            "removed_lowocc_group": col,
            "occurrence_material_count": int(occurrence[col]),
            "total_count": float(total_count[col]),
            "material_original_indices_with_this_group": "; ".join(map(str, material_indices)),
        }

        # 如果该低频基团只对应少数物质，把物质信息也展开记录
        for j, material_original_index in enumerate(material_indices, start=1):
            info = get_material_info(material_original_index)
            for k, v in info.items():
                record[f"material_{j}_{k}"] = v

        removed_lowocc_group_records.append(record)

    # -----------------------------------------------------
    # 7.4 删除所有含低频基团的物质
    # -----------------------------------------------------
    has_lowocc_group = (df_groups_current[lowocc_group_cols] != 0).any(axis=1)
    material_indices_to_remove = df_groups_current.index[has_lowocc_group].tolist()

    for material_original_index in material_indices_to_remove:
        lowocc_groups_in_material = [
            col for col in lowocc_group_cols
            if df_groups_current.loc[material_original_index, col] != 0
        ]

        record = {
            "iteration": iteration,
            "removed_material_original_index": material_original_index,
            "lowocc_group_count_in_material": len(lowocc_groups_in_material),
            "lowocc_groups_in_material": "; ".join(lowocc_groups_in_material),
        }

        record.update(get_material_info(material_original_index))
        removed_material_records.append(record)

    # 删除低频基团列 + 对应物质行
    df_groups_current = df_groups_current.drop(columns=lowocc_group_cols)
    df_groups_current = df_groups_current.drop(index=material_indices_to_remove)

    iteration_records.append({
        "iteration": iteration,
        "n_materials_before": n_materials_before,
        "n_groups_before": n_groups_before,
        "removed_zero_group_count": len(zero_cols),
        "n_groups_after_zero": n_groups_after_zero,
        "lowocc_group_count": len(lowocc_group_cols),
        "removed_material_count": len(material_indices_to_remove),
        "n_materials_after": df_groups_current.shape[0],
        "n_groups_after": df_groups_current.shape[1],
        "status": "continue_removed_lowocc_groups",
    })

    print(
        f"第 {iteration} 轮：删除全零列 {len(zero_cols)} 个，"
        f"删除低频基团 {len(lowocc_group_cols)} 个，"
        f"删除物质 {len(material_indices_to_remove)} 个，"
        f"剩余物质 {df_groups_current.shape[0]} 个，"
        f"剩余基团 {df_groups_current.shape[1]} 个。"
    )


# =========================================================
# 8. 过滤后的 groups 和 Sheet1
# =========================================================
final_material_original_indices = df_groups_current.index.to_numpy()
used_group_cols = df_groups_current.columns.tolist()

df_groups_used = df_groups_current.reset_index(drop=True).copy()

df_groups_raw_filtered = (
    df_groups_raw_original
    .iloc[final_material_original_indices]
    .reset_index(drop=True)
    .copy()
)

# 同步过滤 Sheet1：每个物质 8 行
keep_data_indices = []

for material_original_index in final_material_original_indices:
    start = material_original_index * n_points_per_material
    end = start + n_points_per_material
    keep_data_indices.extend(range(start, end))

df_data = df_data_original.iloc[keep_data_indices].reset_index(drop=True).copy()

print("\n========== 最终筛选结果 ==========")
print("原始物质数:", len(df_groups_original))
print("最终保留物质数:", len(df_groups_used))
print("原始基团数:", len(group_cols_raw))
print("最终保留基团数:", len(used_group_cols))
print("Sheet1 原始行数:", len(df_data_original))
print("Sheet1 最终行数:", len(df_data))


# =========================================================
# 9. 生成筛选报告
# =========================================================
df_removed_zero_groups = pd.DataFrame(removed_zero_group_records)
df_removed_lowocc_groups = pd.DataFrame(removed_lowocc_group_records)
df_removed_materials = pd.DataFrame(removed_material_records)
df_iteration_summary = pd.DataFrame(iteration_records)

# 最终保留基团统计
if len(used_group_cols) > 0:
    final_occurrence = (df_groups_used != 0).sum(axis=0)
    final_total_count = df_groups_used.sum(axis=0)

    df_used_groups = pd.DataFrame({
        "used_group": used_group_cols,
        "final_occurrence_material_count": final_occurrence[used_group_cols].values,
        "final_total_count": final_total_count[used_group_cols].values,
    })
else:
    df_used_groups = pd.DataFrame(columns=[
        "used_group",
        "final_occurrence_material_count",
        "final_total_count",
    ])

df_group_filter_summary = pd.DataFrame([
    {"item": "min_occurrence_required", "value": min_occurrence_required},
    {"item": "low_occurrence_definition", "value": f"occurrence < {min_occurrence_required}"},
    {"item": "original_material_count", "value": len(df_groups_original)},
    {"item": "final_material_count", "value": len(df_groups_used)},
    {"item": "removed_material_count", "value": len(df_groups_original) - len(df_groups_used)},
    {"item": "original_group_count", "value": len(group_cols_raw)},
    {"item": "final_group_count", "value": len(used_group_cols)},
    {"item": "removed_all_zero_group_count", "value": len(df_removed_zero_groups)},
    {"item": "removed_lowocc_group_count", "value": len(df_removed_lowocc_groups)},
    {"item": "iteration_count", "value": len(df_iteration_summary)},
])


# =========================================================
# 10. 检查最终是否仍有低频基团
# =========================================================
final_occurrence_check = (df_groups_used != 0).sum(axis=0)

final_lowocc_cols = final_occurrence_check[
    final_occurrence_check < min_occurrence_required
].index.tolist()

final_zero_cols = df_groups_used.columns[
    df_groups_used.abs().sum(axis=0) == 0
].tolist()

if len(final_lowocc_cols) > 0:
    raise ValueError(
        f"迭代筛选结束后仍然存在出现物质数 < {min_occurrence_required} 的基团，逻辑异常："
        + "; ".join(final_lowocc_cols)
    )

if len(final_zero_cols) > 0:
    raise ValueError(
        "迭代筛选结束后仍然存在全零基团，逻辑异常："
        + "; ".join(final_zero_cols)
    )

print("\n最终检查：")
print("最终全零基团数:", len(final_zero_cols))
print(f"最终出现物质数 < {min_occurrence_required} 的基团数:", len(final_lowocc_cols))


# =========================================================
# 11. 检查删除后是否仍存在重复基团向量
# =========================================================
df_vector_check = df_groups_used.copy()

if len(df_vector_check) > 0 and df_vector_check.shape[1] > 0:
    df_vector_check["feature_vector_key"] = df_vector_check.apply(
        lambda row: tuple(row.astype(float).values.tolist()),
        axis=1
    )

    vector_counts = df_vector_check["feature_vector_key"].value_counts()
    duplicate_vector_keys = vector_counts[vector_counts > 1].index

    duplicate_rows = []

    for dup_id, key in enumerate(duplicate_vector_keys, start=1):
        filtered_indices = df_vector_check.index[df_vector_check["feature_vector_key"] == key].tolist()

        for filtered_idx in filtered_indices:
            original_idx = int(final_material_original_indices[filtered_idx])

            row = {
                "duplicate_group_id": dup_id,
                "material_index_after_filter": filtered_idx,
                "material_index_original": original_idx,
                "same_vector_material_count": len(filtered_indices),
            }

            row.update(get_material_info(original_idx))
            duplicate_rows.append(row)

    df_duplicate_vector_report = pd.DataFrame(duplicate_rows)

else:
    df_duplicate_vector_report = pd.DataFrame(columns=[
        "duplicate_group_id",
        "material_index_after_filter",
        "material_index_original",
        "same_vector_material_count",
    ])

print("最终重复基团向量组数:",
      df_duplicate_vector_report["duplicate_group_id"].nunique() if len(df_duplicate_vector_report) > 0 else 0)
print("最终涉及重复向量的物质数:", len(df_duplicate_vector_report))


# =========================================================
# 12. 过滤后数据检查
# =========================================================
if len(df_data) % n_points_per_material != 0:
    raise ValueError(
        f"过滤后 Sheet1 行数 {len(df_data)} 不能被 {n_points_per_material} 整除。"
    )

n_materials_data = len(df_data) // n_points_per_material
n_materials_groups = len(df_groups_used)

print("\n========== 过滤后数据检查 ==========")
print("过滤后 Sheet1 中物质数量:", n_materials_data)
print("过滤后 groups 中物质数量:", n_materials_groups)

if n_materials_data != n_materials_groups:
    raise ValueError(
        "过滤后 Sheet1 中的物质数量和 groups 表行数不一致。\n"
        f"Sheet1 物质数 = {n_materials_data}, groups 行数 = {n_materials_groups}"
    )

if len(used_group_cols) == 0:
    raise ValueError("迭代删除后没有剩余基团，无法建模。")

if n_materials_groups < 3:
    raise ValueError("迭代删除后剩余物质过少，无法进行稳定训练/测试划分。")


# =========================================================
# 13. 构造建模数据
# 模型：
# Cp = intercept + Σ Nk * Ak + Σ Nk * Bk * T
# 特征：
# [Nk, Nk*T]
# =========================================================
X_list = []
y_list = []
material_id_list = []
temperature_list = []
original_row_index_list = []

for material_idx in range(n_materials_groups):
    Nk = df_groups_used.iloc[material_idx].values.astype(float)

    start = material_idx * n_points_per_material
    end = start + n_points_per_material

    sub_data = df_data.iloc[start:end].copy()

    T_values = pd.to_numeric(sub_data[temp_col], errors="coerce").values.astype(float)
    Cp_values = pd.to_numeric(sub_data[target_col], errors="coerce").values.astype(float)

    for local_i, (T, Cp) in enumerate(zip(T_values, Cp_values)):
        if not np.isfinite(T) or not np.isfinite(Cp):
            continue

        feature_A = Nk
        feature_B = Nk * T

        feature = np.concatenate([feature_A, feature_B])

        X_list.append(feature)
        y_list.append(Cp)
        material_id_list.append(material_idx)
        temperature_list.append(T)
        original_row_index_list.append(start + local_i)

X = np.array(X_list, dtype=float)
y = np.array(y_list, dtype=float)
material_ids = np.array(material_id_list)
temperatures = np.array(temperature_list)
original_row_indices = np.array(original_row_index_list)

print("\n========== 建模矩阵 ==========")
print("最终建模数据点数:", X.shape[0])
print("最终特征数:", X.shape[1])
print("A_k 参数数量:", len(used_group_cols))
print("B_k 参数数量:", len(used_group_cols))


# =========================================================
# 14. 按物质 8:2 划分训练集和测试集
# =========================================================
unique_materials = np.unique(material_ids)

train_materials, test_materials = train_test_split(
    unique_materials,
    test_size=test_size,
    random_state=random_state
)

train_mask = np.isin(material_ids, train_materials)
test_mask = np.isin(material_ids, test_materials)

X_train = X[train_mask]
X_test = X[test_mask]

y_train = y[train_mask]
y_test = y[test_mask]

print("\n========== 训练/测试划分 ==========")
print("训练物质数:", len(train_materials))
print("测试物质数:", len(test_materials))
print("训练数据点数:", len(y_train))
print("测试数据点数:", len(y_test))


# =========================================================
# 15. 线性回归拟合
# =========================================================
model = LinearRegression(fit_intercept=True)
model.fit(X_train, y_train)

y_train_pred = model.predict(X_train)
y_test_pred = model.predict(X_test)
y_all_pred = model.predict(X)


# =========================================================
# 16. 评价指标
# =========================================================
def calc_metrics(y_true, y_pred, name):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    error = y_pred - y_true
    abs_error = np.abs(error)

    valid_mask = np.abs(y_true) > 1e-12

    if valid_mask.sum() > 0:
        relative_error_percent = np.abs(
            (y_pred[valid_mask] - y_true[valid_mask]) / y_true[valid_mask]
        ) * 100

        ard = np.mean(relative_error_percent)
        max_relative_error = np.max(relative_error_percent)

        ratio_le_1 = np.mean(relative_error_percent <= 1) * 100
        ratio_le_5 = np.mean(relative_error_percent <= 5) * 100
        ratio_le_10 = np.mean(relative_error_percent <= 10) * 100
    else:
        ard = np.nan
        max_relative_error = np.nan
        ratio_le_1 = np.nan
        ratio_le_5 = np.nan
        ratio_le_10 = np.nan

    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)

    return {
        "dataset": name,
        "n_points": len(y_true),
        "R2": r2,
        "MSE": mse,
        "RMSE": rmse,
        "MAE": mae,
        "ARD_percent": ard,
        "max_abs_error": np.max(abs_error),
        "max_relative_error_percent": max_relative_error,
        "relative_error_le_1_percent_ratio": ratio_le_1,
        "relative_error_le_5_percent_ratio": ratio_le_5,
        "relative_error_le_10_percent_ratio": ratio_le_10,
    }


metrics = pd.DataFrame([
    calc_metrics(y_train, y_train_pred, "train"),
    calc_metrics(y_test, y_test_pred, "test"),
    calc_metrics(y, y_all_pred, "all")
])

print("\n================ 模型评价指标 ================")
print(metrics.to_string(index=False))

print("\n训练集 R2:", "{:.10f}".format(metrics.loc[metrics["dataset"] == "train", "R2"].values[0]))
print("测试集 R2:", "{:.10f}".format(metrics.loc[metrics["dataset"] == "test", "R2"].values[0]))
print("整体 R2:", "{:.10f}".format(metrics.loc[metrics["dataset"] == "all", "R2"].values[0]))

print("\n训练集 ARD(%):", "{:.10f}".format(metrics.loc[metrics["dataset"] == "train", "ARD_percent"].values[0]))
print("测试集 ARD(%):", "{:.10f}".format(metrics.loc[metrics["dataset"] == "test", "ARD_percent"].values[0]))
print("整体 ARD(%):", "{:.10f}".format(metrics.loc[metrics["dataset"] == "all", "ARD_percent"].values[0]))


# =========================================================
# 17. 拆分参数 A_k 和 B_k
# =========================================================
coef = model.coef_
intercept = model.intercept_

n_groups = len(used_group_cols)

A_params = coef[:n_groups]
B_params = coef[n_groups:]

df_params = pd.DataFrame({
    "group_name": used_group_cols,
    "A_k": A_params,
    "B_k": B_params,
})

df_intercept = pd.DataFrame({
    "parameter": ["intercept"],
    "value": [intercept],
})

print("\n模型截距 intercept:")
print("{:.10f}".format(intercept))

print("\n前 10 个基团参数:")
print(df_params.head(10))


# =========================================================
# 18. 整理逐点预测结果
# =========================================================
df_pred = pd.DataFrame({
    "material_index_after_filter": material_ids,
    "material_index_original": [
        int(final_material_original_indices[m]) for m in material_ids
    ],
    "original_row_index_in_filtered_Sheet1": original_row_indices,
    "T_K": temperatures,
    "Cp_exp": y,
    "Cp_pred": y_all_pred,
    "error": y_all_pred - y,
    "abs_error": np.abs(y_all_pred - y),
    "relative_error_percent": np.where(
        np.abs(y) > 1e-12,
        np.abs((y_all_pred - y) / y) * 100,
        np.nan
    ),
    "dataset": np.where(train_mask, "train", "test"),
})

extra_cols = [
    "compound_name",
    "cas",
    "formula",
    "SMILES",
    "smiles",
    "pubchem_cid",
    "material_key",
    "phase",
    "boiling_T_K",
    "critical_T_K",
]

for col in extra_cols:
    if col in df_data.columns:
        values = []
        for row_idx in original_row_indices:
            values.append(df_data.iloc[row_idx][col])
        df_pred[col] = values


# =========================================================
# 19. 整理物质级别划分信息
# =========================================================
df_material_split = pd.DataFrame({
    "material_index_after_filter": unique_materials,
    "material_index_original": [
        int(final_material_original_indices[m]) for m in unique_materials
    ],
    "dataset": ["train" if m in train_materials else "test" for m in unique_materials],
})

for col in extra_cols:
    if col in df_data.columns:
        values = []
        for material_idx in unique_materials:
            row_idx = material_idx * n_points_per_material
            values.append(df_data.iloc[row_idx][col])
        df_material_split[col] = values


# =========================================================
# 20. 保存 Excel，不使用科学计数法显示
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_pred.to_excel(writer, sheet_name="Prediction", index=False)
    df_params.to_excel(writer, sheet_name="Group_Params", index=False)
    df_intercept.to_excel(writer, sheet_name="Intercept", index=False)
    metrics.to_excel(writer, sheet_name="Metrics", index=False)
    df_material_split.to_excel(writer, sheet_name="Material_Split", index=False)

    df_used_groups.to_excel(writer, sheet_name="Used_Groups", index=False)
    df_group_filter_summary.to_excel(writer, sheet_name="Group_Filter_Summary", index=False)
    df_iteration_summary.to_excel(writer, sheet_name="Iteration_Summary", index=False)
    df_removed_zero_groups.to_excel(writer, sheet_name="Removed_All_Zero_Groups", index=False)
    df_removed_lowocc_groups.to_excel(writer, sheet_name="Removed_LowOccurrence_Groups", index=False)
    df_removed_materials.to_excel(writer, sheet_name="Removed_Materials_LowOccurrence", index=False)
    df_duplicate_vector_report.to_excel(writer, sheet_name="Duplicate_Vector_Report", index=False)

    # 额外保存过滤后的数据，方便后续复用
    df_data.to_excel(writer, sheet_name="Filtered_Sheet1", index=False)
    df_groups_raw_filtered.to_excel(writer, sheet_name="Filtered_Groups_Raw", index=False)
    df_groups_used.to_excel(writer, sheet_name="Filtered_Groups_Used", index=False)

    number_format = "0.0000000000"

    for sheet_name in writer.sheets:
        ws = writer.sheets[sheet_name]

        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, float):
                    cell.number_format = number_format

        for col_cells in ws.columns:
            max_length = 0
            col_letter = col_cells[0].column_letter

            for cell in col_cells:
                if cell.value is not None:
                    max_length = max(max_length, len(str(cell.value)))

            ws.column_dimensions[col_letter].width = min(max_length + 2, 35)

print("\n保存完成:", output_file)