# # import pandas as pd
# # import numpy as np
# # from sklearn.ensemble import RandomForestRegressor
# # from sklearn.metrics import mean_squared_error, r2_score
# # from sklearn.model_selection import train_test_split
# #
# # # ========= 1. 读取数据 =========
# # df = pd.read_excel("Transformed_vp_Dataset.xlsx")
# #
# # target_col = "Vapor Pressure"
# #
# # # ========= 2. 构造“伪物质ID” =========
# # # 假设：每10行属于同一个物质，且这10行在表中连续排列
# # rows_per_material = 10
# # df = df.reset_index(drop=True).copy()
# # df["Pseudo_Material_ID"] = np.arange(len(df)) // rows_per_material
# #
# # # 检查是否正好是10的整数倍
# # if len(df) % rows_per_material != 0:
# #     print(f"⚠️ 总行数 {len(df)} 不是 {rows_per_material} 的整数倍，最后一个物质组可能不完整。")
# #
# # # ========= 3. 按“物质组”做 8:2 划分 =========
# # unique_materials = df["Pseudo_Material_ID"].unique()
# #
# # train_materials, test_materials = train_test_split(
# #     unique_materials,
# #     test_size=0.2,
# #     random_state=42
# # )
# #
# # train_df = df[df["Pseudo_Material_ID"].isin(train_materials)].copy()
# # test_df = df[df["Pseudo_Material_ID"].isin(test_materials)].copy()
# #
# # print("========== 数据划分 ==========")
# # print(f"总物质数: {len(unique_materials)}")
# # print(f"训练集物质数: {len(train_materials)}")
# # print(f"测试集物质数: {len(test_materials)}")
# # print(f"训练集样本点数: {len(train_df)}")
# # print(f"测试集样本点数: {len(test_df)}")
# #
# # # ========= 4. 划分特征和目标 =========
# # X_train = train_df.drop(columns=[target_col, "Pseudo_Material_ID"])
# # y_train = train_df[target_col]
# #
# # X_test = test_df.drop(columns=[target_col, "Pseudo_Material_ID"])
# # y_test = test_df[target_col]
# #
# # # ========= 5. 删除非数值列 =========
# # non_numeric_cols = X_train.select_dtypes(exclude=[np.number]).columns.tolist()
# # if len(non_numeric_cols) > 0:
# #     print(f"⚠️ 检测到非数值列，已删除: {non_numeric_cols}")
# #     X_train = X_train.drop(columns=non_numeric_cols)
# #     X_test = X_test.drop(columns=non_numeric_cols)
# #
# # # ========= 6. 模型训练 =========
# # model = RandomForestRegressor(
# #     n_estimators=300,
# #     random_state=42,
# #     n_jobs=-1
# # )
# # model.fit(X_train, y_train)
# #
# # # ========= 7. 定义评估函数 =========
# # def evaluate(y_true, y_pred, name="数据集"):
# #     y_true = np.asarray(y_true, dtype=float)
# #     y_pred = np.asarray(y_pred, dtype=float)
# #
# #     r2 = r2_score(y_true, y_pred)
# #     mse = mean_squared_error(y_true, y_pred)
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
# #     print(f"\n{name}结果:")
# #     print(f"R²: {r2:.4f}")
# #     print(f"MSE: {mse:.4f}")
# #     print(f"ARD: {ard:.2f}%")
# #     print(f"✅ 误差 ≤ 1% 的点数: {within_1pct}")
# #     print(f"✅ 误差 ≤ 5% 的点数: {within_5pct}")
# #     print(f"✅ 误差 ≤ 10% 的点数: {within_10pct}")
# #
# #     return {
# #         "R2": r2,
# #         "MSE": mse,
# #         "ARD_%": ard,
# #         "Relative_Error_%": relative_error,
# #         "within_1pct": within_1pct,
# #         "within_5pct": within_5pct,
# #         "within_10pct": within_10pct,
# #     }
# #
# # # ========= 8. 训练集预测 =========
# # y_train_pred = model.predict(X_train)
# # train_metrics = evaluate(y_train, y_train_pred, name="训练集")
# #
# # # ========= 9. 测试集预测 =========
# # y_test_pred = model.predict(X_test)
# # test_metrics = evaluate(y_test, y_test_pred, name="测试集")
# #
# # # ========= 10. 保存结果 =========
# # train_result = train_df.copy()
# # train_result["Predicted_Heat_Capacity"] = y_train_pred
# # train_result["Relative_Error (%)"] = train_metrics["Relative_Error_%"]
# # train_result.to_excel("train_prediction_vs_actual_grouped.xlsx", index=False)
# #
# # test_result = test_df.copy()
# # test_result["Predicted_Heat_Capacity"] = y_test_pred
# # test_result["Relative_Error (%)"] = test_metrics["Relative_Error_%"]
# # test_result.to_excel("test_prediction_vs_actual_grouped.xlsx", index=False)
# #
# # summary_df = pd.DataFrame([
# #     ["train", train_metrics["R2"], train_metrics["MSE"], train_metrics["ARD_%"],
# #      train_metrics["within_1pct"], train_metrics["within_5pct"], train_metrics["within_10pct"]],
# #     ["test", test_metrics["R2"], test_metrics["MSE"], test_metrics["ARD_%"],
# #      test_metrics["within_1pct"], test_metrics["within_5pct"], test_metrics["within_10pct"]],
# # ], columns=["Dataset", "R2", "MSE", "ARD_%", "within_1pct", "within_5pct", "within_10pct"])
# # summary_df.to_excel("model_summary_grouped.xlsx", index=False)
# #
# # print("\n✅ 已保存训练集结果: train_prediction_vs_actual_grouped.xlsx")
# # print("✅ 已保存测试集结果: test_prediction_vs_actual_grouped.xlsx")
# # print("✅ 已保存汇总结果: model_summary_grouped.xlsx")
#
# import pandas as pd
# import numpy as np
#
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
# from sklearn.model_selection import train_test_split
#
#
# # ========= 1. 读取数据 =========
# df = pd.read_excel("Transformed_vp_Dataset.xlsx")
#
# target_col = "Vapor Pressure"
#
#
# # ========= 2. 构造“伪物质ID” =========
# # 假设：每10行属于同一个物质，且这10行在表中连续排列
# rows_per_material = 10
# df = df.reset_index(drop=True).copy()
# df["Pseudo_Material_ID"] = np.arange(len(df)) // rows_per_material
#
# # 检查是否正好是10的整数倍
# if len(df) % rows_per_material != 0:
#     print(f"警告：总行数 {len(df)} 不是 {rows_per_material} 的整数倍，最后一个物质组可能不完整。")
#
#
# # ========= 3. 按“物质组”做 8:2 划分 =========
# unique_materials = df["Pseudo_Material_ID"].unique()
#
# train_materials, test_materials = train_test_split(
#     unique_materials,
#     test_size=0.2,
#     random_state=42
# )
#
# train_df = df[df["Pseudo_Material_ID"].isin(train_materials)].copy()
# test_df = df[df["Pseudo_Material_ID"].isin(test_materials)].copy()
#
# print("========== 数据划分 ==========")
# print(f"总物质数: {len(unique_materials)}")
# print(f"训练集物质数: {len(train_materials)}")
# print(f"测试集物质数: {len(test_materials)}")
# print(f"训练集样本点数: {len(train_df)}")
# print(f"测试集样本点数: {len(test_df)}")
#
#
# # ========= 4. 划分特征和目标 =========
# X_train = train_df.drop(columns=[target_col, "Pseudo_Material_ID"])
# y_train = train_df[target_col]
#
# X_test = test_df.drop(columns=[target_col, "Pseudo_Material_ID"])
# y_test = test_df[target_col]
#
#
# # ========= 5. 删除非数值列 =========
# non_numeric_cols = X_train.select_dtypes(exclude=[np.number]).columns.tolist()
#
# if len(non_numeric_cols) > 0:
#     print(f"检测到非数值列，已删除: {non_numeric_cols}")
#     X_train = X_train.drop(columns=non_numeric_cols)
#     X_test = X_test.drop(columns=non_numeric_cols)
#
#
# # ========= 6. 模型训练 =========
# # 注意：这里训练目标仍然是普通 Vapor Pressure，不是 ln(P)
# model = RandomForestRegressor(
#     n_estimators=300,
#     random_state=42,
#     n_jobs=-1
# )
#
# model.fit(X_train, y_train)
#
#
# # ========= 7. 定义评估函数：同时评价 P 和 ln(P) =========
# def evaluate(y_true, y_pred, name="数据集"):
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#
#     # ---------- 普通 P 空间评价 ----------
#     r2_P = r2_score(y_true, y_pred)
#     mse_P = mean_squared_error(y_true, y_pred)
#     mae_P = mean_absolute_error(y_true, y_pred)
#
#     nonzero_mask = np.abs(y_true) > 1e-12
#     relative_error = np.full_like(y_true, np.nan, dtype=float)
#
#     if np.any(nonzero_mask):
#         relative_error[nonzero_mask] = np.abs(
#             (y_true[nonzero_mask] - y_pred[nonzero_mask]) / y_true[nonzero_mask]
#         ) * 100
#         ard = np.nanmean(relative_error)
#     else:
#         ard = np.nan
#
#     within_1pct = np.sum(relative_error <= 1)
#     within_5pct = np.sum(relative_error <= 5)
#     within_10pct = np.sum(relative_error <= 10)
#
#     # ---------- ln(P) 空间评价 ----------
#     # 只有 y_true > 0 且 y_pred > 0 时，才能取 ln
#     log_mask = (
#         np.isfinite(y_true)
#         & np.isfinite(y_pred)
#         & (y_true > 0)
#         & (y_pred > 0)
#     )
#
#     lnP_true = np.full_like(y_true, np.nan, dtype=float)
#     lnP_pred = np.full_like(y_pred, np.nan, dtype=float)
#     abs_error_lnP = np.full_like(y_true, np.nan, dtype=float)
#
#     if np.any(log_mask):
#         lnP_true[log_mask] = np.log(y_true[log_mask])
#         lnP_pred[log_mask] = np.log(y_pred[log_mask])
#         abs_error_lnP[log_mask] = np.abs(lnP_true[log_mask] - lnP_pred[log_mask])
#
#         r2_lnP = r2_score(lnP_true[log_mask], lnP_pred[log_mask])
#         mse_lnP = mean_squared_error(lnP_true[log_mask], lnP_pred[log_mask])
#         mae_lnP = mean_absolute_error(lnP_true[log_mask], lnP_pred[log_mask])
#     else:
#         r2_lnP = np.nan
#         mse_lnP = np.nan
#         mae_lnP = np.nan
#
#     print(f"\n{name}结果:")
#
#     print("\n普通 P 空间指标:")
#     print(f"R2_P  = {r2_P:.6f}")
#     print(f"MSE_P = {mse_P:.10f}")
#     print(f"MAE_P = {mae_P:.10f}")
#     print(f"ARD_P = {ard:.4f}%")
#     print(f"误差 <= 1% 的点数: {within_1pct}")
#     print(f"误差 <= 5% 的点数: {within_5pct}")
#     print(f"误差 <= 10% 的点数: {within_10pct}")
#
#     print("\nln(P) 空间指标:")
#     print(f"R2_lnP  = {r2_lnP:.6f}")
#     print(f"MSE_lnP = {mse_lnP:.10f}")
#     print(f"MAE_lnP = {mae_lnP:.10f}")
#     print(f"可用于 ln(P) 评价的点数: {np.sum(log_mask)} / {len(y_true)}")
#
#     return {
#         "R2_P": r2_P,
#         "MSE_P": mse_P,
#         "MAE_P": mae_P,
#         "ARD_%": ard,
#         "Relative_Error_%": relative_error,
#         "within_1pct": within_1pct,
#         "within_5pct": within_5pct,
#         "within_10pct": within_10pct,
#
#         "R2_lnP": r2_lnP,
#         "MSE_lnP": mse_lnP,
#         "MAE_lnP": mae_lnP,
#         "lnP_true": lnP_true,
#         "lnP_pred": lnP_pred,
#         "Absolute_Error_lnP": abs_error_lnP,
#         "log_valid_count": np.sum(log_mask),
#     }
#
#
# # ========= 8. 训练集预测 =========
# y_train_pred = model.predict(X_train)
#
# train_metrics = evaluate(
#     y_train,
#     y_train_pred,
#     name="训练集"
# )
#
#
# # ========= 9. 测试集预测 =========
# y_test_pred = model.predict(X_test)
#
# test_metrics = evaluate(
#     y_test,
#     y_test_pred,
#     name="测试集"
# )
#
#
# # ========= 10. 保存训练集结果 =========
# train_result = train_df.copy()
#
# train_result["P_true"] = y_train.values
# train_result["P_pred"] = y_train_pred
#
# train_result["lnP_true"] = train_metrics["lnP_true"]
# train_result["lnP_pred"] = train_metrics["lnP_pred"]
# train_result["Absolute_Error_lnP"] = train_metrics["Absolute_Error_lnP"]
#
# train_result["Relative_Error_P (%)"] = train_metrics["Relative_Error_%"]
# train_result["Absolute_Error_P"] = np.abs(
#     train_result["P_pred"] - train_result["P_true"]
# )
#
# train_result.to_excel(
#     "train_prediction_vs_actual_grouped_with_lnP.xlsx",
#     index=False
# )
#
#
# # ========= 11. 保存测试集结果 =========
# test_result = test_df.copy()
#
# test_result["P_true"] = y_test.values
# test_result["P_pred"] = y_test_pred
#
# test_result["lnP_true"] = test_metrics["lnP_true"]
# test_result["lnP_pred"] = test_metrics["lnP_pred"]
# test_result["Absolute_Error_lnP"] = test_metrics["Absolute_Error_lnP"]
#
# test_result["Relative_Error_P (%)"] = test_metrics["Relative_Error_%"]
# test_result["Absolute_Error_P"] = np.abs(
#     test_result["P_pred"] - test_result["P_true"]
# )
#
# test_result.to_excel(
#     "test_prediction_vs_actual_grouped_with_lnP.xlsx",
#     index=False
# )
#
#
# # ========= 12. 保存汇总结果 =========
# summary_df = pd.DataFrame([
#     [
#         "train",
#         train_metrics["R2_P"],
#         train_metrics["MSE_P"],
#         train_metrics["MAE_P"],
#         train_metrics["ARD_%"],
#         train_metrics["within_1pct"],
#         train_metrics["within_5pct"],
#         train_metrics["within_10pct"],
#         train_metrics["R2_lnP"],
#         train_metrics["MSE_lnP"],
#         train_metrics["MAE_lnP"],
#         train_metrics["log_valid_count"],
#     ],
#     [
#         "test",
#         test_metrics["R2_P"],
#         test_metrics["MSE_P"],
#         test_metrics["MAE_P"],
#         test_metrics["ARD_%"],
#         test_metrics["within_1pct"],
#         test_metrics["within_5pct"],
#         test_metrics["within_10pct"],
#         test_metrics["R2_lnP"],
#         test_metrics["MSE_lnP"],
#         test_metrics["MAE_lnP"],
#         test_metrics["log_valid_count"],
#     ],
# ], columns=[
#     "Dataset",
#     "R2_P",
#     "MSE_P",
#     "MAE_P",
#     "ARD_%",
#     "within_1pct",
#     "within_5pct",
#     "within_10pct",
#     "R2_lnP",
#     "MSE_lnP",
#     "MAE_lnP",
#     "log_valid_count",
# ])
#
# summary_df.to_excel(
#     "model_summary_grouped_with_lnP.xlsx",
#     index=False
# )
#
#
# print("\n已保存训练集结果: train_prediction_vs_actual_grouped_with_lnP.xlsx")
# print("已保存测试集结果: test_prediction_vs_actual_grouped_with_lnP.xlsx")
# print("已保存汇总结果: model_summary_grouped_with_lnP.xlsx")

import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.model_selection import train_test_split


# ========= 1. 读取数据 =========
df = pd.read_excel("Transformed_vp_Dataset.xlsx")

target_col = "Vapor Pressure"


# ========= 2. 构造“伪物质ID” =========
# 假设：每10行属于同一个物质，且这10行在表中连续排列
rows_per_material = 10
df = df.reset_index(drop=True).copy()
df["Pseudo_Material_ID"] = np.arange(len(df)) // rows_per_material

# 检查是否正好是10的整数倍
if len(df) % rows_per_material != 0:
    print(f"警告：总行数 {len(df)} 不是 {rows_per_material} 的整数倍，最后一个物质组可能不完整。")


# ========= 3. 按“物质组”做 8:2 划分 =========
unique_materials = df["Pseudo_Material_ID"].unique()

train_materials, test_materials = train_test_split(
    unique_materials,
    test_size=0.2,
    random_state=42
)

train_df = df[df["Pseudo_Material_ID"].isin(train_materials)].copy()
test_df = df[df["Pseudo_Material_ID"].isin(test_materials)].copy()

print("========== 数据划分 ==========")
print(f"总物质数: {len(unique_materials)}")
print(f"训练集物质数: {len(train_materials)}")
print(f"测试集物质数: {len(test_materials)}")
print(f"训练集样本点数: {len(train_df)}")
print(f"测试集样本点数: {len(test_df)}")


# ========= 4. 划分特征和目标 =========
X_train = train_df.drop(columns=[target_col, "Pseudo_Material_ID"])
y_train = train_df[target_col]

X_test = test_df.drop(columns=[target_col, "Pseudo_Material_ID"])
y_test = test_df[target_col]


# ========= 5. 删除非数值列 =========
non_numeric_cols = X_train.select_dtypes(exclude=[np.number]).columns.tolist()

if len(non_numeric_cols) > 0:
    print(f"检测到非数值列，已删除: {non_numeric_cols}")
    X_train = X_train.drop(columns=non_numeric_cols)
    X_test = X_test.drop(columns=non_numeric_cols)


# ========= 6. 模型训练 =========
# 注意：这里训练目标仍然是普通 Vapor Pressure，不是 ln(P)
model = RandomForestRegressor(
    n_estimators=300,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)


# ========= 7. 定义评估函数：同时评价 P 和 ln(P) =========
def evaluate(y_true, y_pred, name="数据集", strict_less=False):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    # ---------- 普通 P 空间评价 ----------
    r2_P = r2_score(y_true, y_pred)
    mse_P = mean_squared_error(y_true, y_pred)
    mae_P = mean_absolute_error(y_true, y_pred)

    nonzero_mask = np.abs(y_true) > 1e-12
    relative_error = np.full_like(y_true, np.nan, dtype=float)

    if np.any(nonzero_mask):
        relative_error[nonzero_mask] = np.abs(
            (y_true[nonzero_mask] - y_pred[nonzero_mask]) / y_true[nonzero_mask]
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

    # ---------- ln(P) 空间评价 ----------
    # 只有 y_true > 0 且 y_pred > 0 时，才能取 ln
    log_mask = (
        np.isfinite(y_true)
        & np.isfinite(y_pred)
        & (y_true > 0)
        & (y_pred > 0)
    )

    lnP_true = np.full_like(y_true, np.nan, dtype=float)
    lnP_pred = np.full_like(y_pred, np.nan, dtype=float)
    abs_error_lnP = np.full_like(y_true, np.nan, dtype=float)

    if np.any(log_mask):
        lnP_true[log_mask] = np.log(y_true[log_mask])
        lnP_pred[log_mask] = np.log(y_pred[log_mask])
        abs_error_lnP[log_mask] = np.abs(lnP_true[log_mask] - lnP_pred[log_mask])

        r2_lnP = r2_score(lnP_true[log_mask], lnP_pred[log_mask])
        mse_lnP = mean_squared_error(lnP_true[log_mask], lnP_pred[log_mask])
        mae_lnP = mean_absolute_error(lnP_true[log_mask], lnP_pred[log_mask])
    else:
        r2_lnP = np.nan
        mse_lnP = np.nan
        mae_lnP = np.nan

    print(f"\n{name}结果:")

    print("\n普通 P 空间指标:")
    print(f"R2_P  = {r2_P:.6f}")
    print(f"MSE_P = {mse_P:.10f}")
    print(f"MAE_P = {mae_P:.10f}")
    print(f"ARD_P = {ard:.4f}%")

    if strict_less:
        print(f"误差 < 1% 的点数: {within_1pct}")
        print(f"误差 < 5% 的点数: {within_5pct}")
        print(f"误差 < 10% 的点数: {within_10pct}")
    else:
        print(f"误差 <= 1% 的点数: {within_1pct}")
        print(f"误差 <= 5% 的点数: {within_5pct}")
        print(f"误差 <= 10% 的点数: {within_10pct}")

    print("\nln(P) 空间指标:")
    print(f"R2_lnP  = {r2_lnP:.6f}")
    print(f"MSE_lnP = {mse_lnP:.10f}")
    print(f"MAE_lnP = {mae_lnP:.10f}")
    print(f"可用于 ln(P) 评价的点数: {np.sum(log_mask)} / {len(y_true)}")

    return {
        "R2_P": r2_P,
        "MSE_P": mse_P,
        "MAE_P": mae_P,
        "ARD_%": ard,
        "Relative_Error_%": relative_error,
        "within_1pct": within_1pct,
        "within_5pct": within_5pct,
        "within_10pct": within_10pct,

        "R2_lnP": r2_lnP,
        "MSE_lnP": mse_lnP,
        "MAE_lnP": mae_lnP,
        "lnP_true": lnP_true,
        "lnP_pred": lnP_pred,
        "Absolute_Error_lnP": abs_error_lnP,
        "log_valid_count": np.sum(log_mask),
    }


# ========= 8. 训练集预测 =========
y_train_pred = model.predict(X_train)

train_metrics = evaluate(
    y_train,
    y_train_pred,
    name="训练集",
    strict_less=False
)


# ========= 9. 测试集预测 =========
y_test_pred = model.predict(X_test)

test_metrics = evaluate(
    y_test,
    y_test_pred,
    name="测试集",
    strict_less=False
)


# ========= 9.1 完整数据集统计：训练集 + 测试集 =========
y_all_true = np.concatenate([
    np.asarray(y_train, dtype=float),
    np.asarray(y_test, dtype=float)
])

y_all_pred = np.concatenate([
    np.asarray(y_train_pred, dtype=float),
    np.asarray(y_test_pred, dtype=float)
])

all_metrics = evaluate(
    y_all_true,
    y_all_pred,
    name="完整数据集：训练集 + 测试集",
    strict_less=True
)

print("\n完整数据集 Vapor Pressure 预测偏差 1%，5%，10%分别为：")
print(all_metrics["within_1pct"])
print(all_metrics["within_5pct"])
print(all_metrics["within_10pct"])


# ========= 10. 保存训练集结果 =========
train_result = train_df.copy()

train_result["P_true"] = y_train.values
train_result["P_pred"] = y_train_pred

train_result["lnP_true"] = train_metrics["lnP_true"]
train_result["lnP_pred"] = train_metrics["lnP_pred"]
train_result["Absolute_Error_lnP"] = train_metrics["Absolute_Error_lnP"]

train_result["Relative_Error_P (%)"] = train_metrics["Relative_Error_%"]
train_result["Absolute_Error_P"] = np.abs(
    train_result["P_pred"] - train_result["P_true"]
)

train_result.to_excel(
    "train_prediction_vs_actual_grouped_with_lnP.xlsx",
    index=False
)


# ========= 11. 保存测试集结果 =========
test_result = test_df.copy()

test_result["P_true"] = y_test.values
test_result["P_pred"] = y_test_pred

test_result["lnP_true"] = test_metrics["lnP_true"]
test_result["lnP_pred"] = test_metrics["lnP_pred"]
test_result["Absolute_Error_lnP"] = test_metrics["Absolute_Error_lnP"]

test_result["Relative_Error_P (%)"] = test_metrics["Relative_Error_%"]
test_result["Absolute_Error_P"] = np.abs(
    test_result["P_pred"] - test_result["P_true"]
)

test_result.to_excel(
    "test_prediction_vs_actual_grouped_with_lnP.xlsx",
    index=False
)


# ========= 11.1 保存完整数据集结果 =========
all_result = pd.concat(
    [train_result, test_result],
    axis=0,
    ignore_index=True
)

all_result["P_true"] = y_all_true
all_result["P_pred"] = y_all_pred
all_result["lnP_true"] = all_metrics["lnP_true"]
all_result["lnP_pred"] = all_metrics["lnP_pred"]
all_result["Absolute_Error_lnP"] = all_metrics["Absolute_Error_lnP"]
all_result["Relative_Error_P (%)"] = all_metrics["Relative_Error_%"]
all_result["Absolute_Error_P"] = np.abs(y_all_pred - y_all_true)

all_result.to_excel(
    "all_prediction_vs_actual_grouped_with_lnP.xlsx",
    index=False
)


# ========= 12. 保存汇总结果 =========
summary_df = pd.DataFrame([
    [
        "train",
        train_metrics["R2_P"],
        train_metrics["MSE_P"],
        train_metrics["MAE_P"],
        train_metrics["ARD_%"],
        train_metrics["within_1pct"],
        train_metrics["within_5pct"],
        train_metrics["within_10pct"],
        train_metrics["R2_lnP"],
        train_metrics["MSE_lnP"],
        train_metrics["MAE_lnP"],
        train_metrics["log_valid_count"],
    ],
    [
        "test",
        test_metrics["R2_P"],
        test_metrics["MSE_P"],
        test_metrics["MAE_P"],
        test_metrics["ARD_%"],
        test_metrics["within_1pct"],
        test_metrics["within_5pct"],
        test_metrics["within_10pct"],
        test_metrics["R2_lnP"],
        test_metrics["MSE_lnP"],
        test_metrics["MAE_lnP"],
        test_metrics["log_valid_count"],
    ],
    [
        "all",
        all_metrics["R2_P"],
        all_metrics["MSE_P"],
        all_metrics["MAE_P"],
        all_metrics["ARD_%"],
        all_metrics["within_1pct"],
        all_metrics["within_5pct"],
        all_metrics["within_10pct"],
        all_metrics["R2_lnP"],
        all_metrics["MSE_lnP"],
        all_metrics["MAE_lnP"],
        all_metrics["log_valid_count"],
    ],
], columns=[
    "Dataset",
    "R2_P",
    "MSE_P",
    "MAE_P",
    "ARD_%",
    "within_1pct",
    "within_5pct",
    "within_10pct",
    "R2_lnP",
    "MSE_lnP",
    "MAE_lnP",
    "log_valid_count",
])

summary_df.to_excel(
    "model_summary_grouped_with_lnP.xlsx",
    index=False
)


print("\n已保存训练集结果: train_prediction_vs_actual_grouped_with_lnP.xlsx")
print("已保存测试集结果: test_prediction_vs_actual_grouped_with_lnP.xlsx")
print("已保存完整数据集结果: all_prediction_vs_actual_grouped_with_lnP.xlsx")
print("已保存汇总结果: model_summary_grouped_with_lnP.xlsx")


# ========= 13. 输出模型结构记录 =========
print("\n当前 Transformed VP RF 直接模型结构:")
print("Target: Vapor Pressure")
print("Evaluation target: Vapor Pressure and ln(P)")
print("Model: RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1)")
print("Split: Pseudo_Material_ID, every 10 rows as one material")
print("Input features: all numeric columns except Vapor Pressure and Pseudo_Material_ID")