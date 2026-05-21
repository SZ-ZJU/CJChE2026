# import pandas as pd
# import numpy as np
#
# from sklearn.linear_model import HuberRegressor
# from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.preprocessing import PolynomialFeatures
# from sklearn.model_selection import train_test_split
#
#
# # ==== 常数与路径 ====
# HV0, HVB, Tb0 = 9612.7, 15419.9, 222.543
# T_ref = 298.15
#
# # ==== 读取主数据 ====
# df_main = pd.read_excel("heat of vaporization 204.xlsx", sheet_name="Sheet1").copy()
#
# id_col = df_main.columns[0]
# group_cols = list(df_main.columns[13:32])   # 19个基团
# temp_cols = list(df_main.columns[32:42])    # 10个温度列
# hvap_cols = list(df_main.columns[42:52])    # 10个汽化焓列
# tb_col = df_main.columns[5]
#
# # 数值化
# for col in group_cols + temp_cols + hvap_cols + [tb_col]:
#     df_main[col] = pd.to_numeric(df_main[col], errors="coerce")
#
# # 基团特征
# Nk_all = df_main[group_cols].fillna(0)
#
#
# # ==== 统一按物质做 8:2 划分 ====
# unique_materials = df_main[id_col].dropna().unique()
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
# row_train_mask = df_main[id_col].isin(train_materials).to_numpy()
# row_test_mask = df_main[id_col].isin(test_materials).to_numpy()
#
# df_train = df_main.loc[row_train_mask].copy().reset_index(drop=True)
# df_test = df_main.loc[row_test_mask].copy().reset_index(drop=True)
#
# print("========== 按物质划分 ==========")
# print(f"总物质数: {len(unique_materials)}")
# print(f"训练集物质数: {len(train_materials)}")
# print(f"测试集物质数: {len(test_materials)}")
# print(f"训练集行数: {len(df_train)}")
# print(f"测试集行数: {len(df_test)}")
#
#
# # ==== 多项式基团特征（仅用训练集 fit）====
# poly = PolynomialFeatures(degree=2, include_bias=False)
#
# X_groups_train = df_train[group_cols].fillna(0)
# X_groups_test = df_test[group_cols].fillna(0)
#
#
# # ==== baseline 组件1：Tb 模型（只在训练集训练）====
# Tb_train_raw = df_train[tb_col].to_numpy(dtype=float)
# valid_tb_train = ~np.isnan(Tb_train_raw)
#
# X_poly_train_valid = poly.fit_transform(X_groups_train.loc[valid_tb_train])
#
# model_Tb = HuberRegressor(max_iter=10000).fit(
#     X_poly_train_valid,
#     np.exp(Tb_train_raw[valid_tb_train] / Tb0)
# )
#
# Tb_pred_train = Tb0 * np.log(
#     np.clip(model_Tb.predict(poly.transform(X_groups_train)), 1e-6, None)
# )
#
# Tb_pred_test = Tb0 * np.log(
#     np.clip(model_Tb.predict(poly.transform(X_groups_test)), 1e-6, None)
# )
#
#
# # ==== baseline 组件2：HVap_Tb 模型（只在训练集训练）====
# df_Tb = pd.read_excel("selected_25_descriptors_data_boiling_point.xlsx").copy()
# target_Tb = "Heat of vaporization at boiling temperature"
#
# if len(df_Tb) != len(df_main):
#     raise ValueError(
#         "selected_25_descriptors_data_boiling_point.xlsx 与 heat of vaporization 204.xlsx 行数不一致。"
#         "当前代码默认两个文件逐行对应；若不是，请改成按 Material_ID 合并。"
#     )
#
# X_Tb_all = df_Tb.drop(columns=[target_Tb]).copy()
# y_Tb_all = pd.to_numeric(df_Tb[target_Tb], errors="coerce")
#
# # 数值化 descriptors
# for c in X_Tb_all.columns:
#     X_Tb_all[c] = pd.to_numeric(X_Tb_all[c], errors="coerce")
#
# # 只保留目标和特征都有效的行用于训练
# valid_rf_mask = (
#     (~X_Tb_all.isna().any(axis=1))
#     & (~y_Tb_all.isna())
#     & (~df_main[id_col].isna())
# )
#
# valid_rf_train_mask = valid_rf_mask & df_main[id_col].isin(train_materials)
# valid_rf_test_mask = valid_rf_mask & df_main[id_col].isin(test_materials)
#
# rf_Tb = RandomForestRegressor(
#     n_estimators=300,
#     random_state=42,
#     n_jobs=-1
# )
#
# rf_Tb.fit(
#     X_Tb_all.loc[valid_rf_train_mask],
#     y_Tb_all.loc[valid_rf_train_mask]
# )
#
# # 预测 train / test 的参考汽化焓
# HVap_Tb_pred_train = rf_Tb.predict(X_Tb_all.loc[row_train_mask])
# HVap_Tb_pred_test = rf_Tb.predict(X_Tb_all.loc[row_test_mask])
#
#
# # ==== baseline 组件3：A_k 系数（只在训练集训练）====
# G_train = X_groups_train.to_numpy(dtype=float)
# G_test = X_groups_test.to_numpy(dtype=float)
#
# X_A_train, y_A_train = [], []
#
# for i in range(len(df_train)):
#     Tb_i = Tb_pred_train[i]
#     HVap_Tb_i = HVap_Tb_pred_train[i]
#
#     for tcol, hvcol in zip(temp_cols, hvap_cols):
#         Tj = pd.to_numeric(df_train.at[i, tcol], errors="coerce")
#         Hvapj = pd.to_numeric(df_train.at[i, hvcol], errors="coerce")
#
#         if np.isnan(Tj) or np.isnan(Hvapj):
#             continue
#
#         Xj = (Tj - Tb_i) * G_train[i]
#         yj = Hvapj - HVap_Tb_i
#
#         X_A_train.append(Xj)
#         y_A_train.append(yj)
#
# X_A_train = np.array(X_A_train, dtype=float)
# y_A_train = np.array(y_A_train, dtype=float)
#
# A_solver = HuberRegressor(
#     fit_intercept=False,
#     max_iter=5000
# )
#
# A_solver.fit(X_A_train, y_A_train)
# A_vec = A_solver.coef_
#
#
# # ==== 生成 baseline 长表（训练集 / 测试集）====
# def build_baseline_long(sub_df, G, Tb_pred_sub, HVap_Tb_pred_sub, dataset_name):
#     rows = []
#
#     for i in range(len(sub_df)):
#         material_id = sub_df.at[i, id_col]
#         Tb_i = Tb_pred_sub[i]
#         HVap_Tb_i = HVap_Tb_pred_sub[i]
#
#         for j, (tcol, hvcol) in enumerate(zip(temp_cols, hvap_cols), start=1):
#             Tj = pd.to_numeric(sub_df.at[i, tcol], errors="coerce")
#             Hvapj = pd.to_numeric(sub_df.at[i, hvcol], errors="coerce")
#
#             if np.isnan(Tj) or np.isnan(Hvapj):
#                 continue
#
#             Xj = (Tj - Tb_i) * G[i]
#             HVap_baseline = HVap_Tb_i + Xj @ A_vec
#
#             rows.append({
#                 "Dataset": dataset_name,
#                 "row_idx_local": i,
#                 "Material_ID": material_id,
#                 "temp_index": j,
#                 "temp_col": tcol,
#                 "hvap_col": hvcol,
#                 "T": Tj,
#                 "HVap_actual": Hvapj,
#                 "HVap_baseline": HVap_baseline,
#                 "T_ref": Tb_i,
#                 "HVap_ref": HVap_Tb_i
#             })
#
#     return pd.DataFrame(rows)
#
#
# train_long = build_baseline_long(
#     df_train,
#     G_train,
#     Tb_pred_train,
#     HVap_Tb_pred_train,
#     "train"
# )
#
# test_long = build_baseline_long(
#     df_test,
#     G_test,
#     Tb_pred_test,
#     HVap_Tb_pred_test,
#     "test"
# )
#
# print(f"baseline训练样本点数: {len(train_long)}")
# print(f"baseline测试样本点数: {len(test_long)}")
#
#
# # ==== residual 特征构造 ====
# def add_residual_features(long_df, G, Tb_pred_sub, HVap_Tb_pred_sub):
#     feature_list = []
#     target_list = []
#
#     for _, row in long_df.iterrows():
#         i = int(row["row_idx_local"])
#
#         Tj = row["T"]
#         HVap_actual = row["HVap_actual"]
#         HVap_baseline = row["HVap_baseline"]
#
#         Tb_i = Tb_pred_sub[i]
#         HVap_Tb_i = HVap_Tb_pred_sub[i]
#
#         base_features = list(G[i])
#
#         temp_features = [
#             Tj,
#             Tj - Tb_i,
#             Tj / Tb_i if Tb_i > 0 else 0.0,
#             np.log(Tj) if Tj > 0 else 0.0,
#         ]
#
#         baseline_features = [HVap_baseline]
#         ref_features = [Tb_i, HVap_Tb_i]
#
#         x = base_features + temp_features + baseline_features + ref_features
#         y = HVap_actual - HVap_baseline
#
#         feature_list.append(x)
#         target_list.append(y)
#
#     X_res = np.array(feature_list, dtype=float)
#     y_res = np.array(target_list, dtype=float)
#
#     return X_res, y_res
#
#
# X_res_train, y_res_train = add_residual_features(
#     train_long,
#     G_train,
#     Tb_pred_train,
#     HVap_Tb_pred_train
# )
#
# X_res_test, y_res_test = add_residual_features(
#     test_long,
#     G_test,
#     Tb_pred_test,
#     HVap_Tb_pred_test
# )
#
# print(f"residual训练集形状: {X_res_train.shape}")
# print(f"residual测试集形状: {X_res_test.shape}")
#
#
# # ============================================================
# # residual 模型：GBDT（只在训练集训练）
# # ============================================================
# # 注意：
# # 1. 这里原来是 GPR + StandardScaler + y标准化
# # 2. 现在改成 GBDT
# # 3. GBDT 是树模型，不需要 StandardScaler
# # 4. 目标仍然是 residual = HVap_actual - HVap_baseline
#
# residual_model = GradientBoostingRegressor(
#     n_estimators=500,
#     learning_rate=0.03,
#     max_depth=3,
#     subsample=0.9,
#     min_samples_split=2,
#     min_samples_leaf=1,
#     loss="squared_error",
#     random_state=42
# )
#
# print("\n开始训练 residual GBDT 模型...")
# residual_model.fit(X_res_train, y_res_train)
#
# print("\nresidual GBDT 模型参数:")
# print(residual_model)
#
#
# # ==== residual 预测 ====
# train_res_pred = residual_model.predict(X_res_train)
# test_res_pred = residual_model.predict(X_res_test)
#
#
# # ==== 组合最终预测 ====
# train_long["Residual_true"] = y_res_train
# train_long["Residual_pred"] = train_res_pred
# train_long["HVap_final"] = train_long["HVap_baseline"] + train_long["Residual_pred"]
#
# test_long["Residual_true"] = y_res_test
# test_long["Residual_pred"] = test_res_pred
# test_long["HVap_final"] = test_long["HVap_baseline"] + test_long["Residual_pred"]
#
#
# # ==== 评估函数 ====
# def evaluate_regression(y_true, y_pred, name="dataset"):
#     y_true = np.array(y_true, dtype=float)
#     y_pred = np.array(y_pred, dtype=float)
#
#     mse = mean_squared_error(y_true, y_pred)
#     r2 = r2_score(y_true, y_pred)
#
#     relative_error = np.full_like(y_true, np.nan, dtype=float)
#
#     nonzero_mask = np.abs(y_true) > 1e-12
#     if np.any(nonzero_mask):
#         relative_error[nonzero_mask] = np.abs(
#             (y_true[nonzero_mask] - y_pred[nonzero_mask])
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
#     print(f"R2  = {r2:.6f}")
#     print(f"MSE = {mse:.10f}")
#     print(f"ARD = {ard:.4f}%")
#     print(f"<=1%  点数: {within_1pct}")
#     print(f"<=5%  点数: {within_5pct}")
#     print(f"<=10% 点数: {within_10pct}")
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
# # ==== baseline 与 final 在同一划分下评估 ====
# baseline_train_metrics = evaluate_regression(
#     train_long["HVap_actual"].to_numpy(),
#     train_long["HVap_baseline"].to_numpy(),
#     "baseline - 训练集"
# )
# train_long["Baseline_Relative_Error_%"] = baseline_train_metrics["relative_error"]
#
# baseline_test_metrics = evaluate_regression(
#     test_long["HVap_actual"].to_numpy(),
#     test_long["HVap_baseline"].to_numpy(),
#     "baseline - 测试集"
# )
# test_long["Baseline_Relative_Error_%"] = baseline_test_metrics["relative_error"]
#
# final_train_metrics = evaluate_regression(
#     train_long["HVap_actual"].to_numpy(),
#     train_long["HVap_final"].to_numpy(),
#     "final model GBDT residual - 训练集"
# )
# train_long["Final_Relative_Error_%"] = final_train_metrics["relative_error"]
#
# final_test_metrics = evaluate_regression(
#     test_long["HVap_actual"].to_numpy(),
#     test_long["HVap_final"].to_numpy(),
#     "final model GBDT residual - 测试集"
# )
# test_long["Final_Relative_Error_%"] = final_test_metrics["relative_error"]
#
#
# # ==== residual 层面评估 ====
# residual_train_metrics = evaluate_regression(
#     y_res_train,
#     train_res_pred,
#     "residual GBDT - 训练集"
# )
#
# residual_test_metrics = evaluate_regression(
#     y_res_test,
#     test_res_pred,
#     "residual GBDT - 测试集"
# )
#
#
# # ==== 分温度点评估（测试集 final）====
# print("\n=== 测试集分温度点评估（final GBDT residual） ===")
#
# for tcol, hvcol in zip(temp_cols, hvap_cols):
#     m = (test_long["temp_col"] == tcol)
#
#     if m.any():
#         y_true_temp = test_long.loc[m, "HVap_actual"].to_numpy()
#         y_pred_temp = test_long.loc[m, "HVap_final"].to_numpy()
#
#         mse_temp = mean_squared_error(y_true_temp, y_pred_temp)
#         r2_temp = r2_score(y_true_temp, y_pred_temp)
#
#         print(f"{tcol}: MSE = {mse_temp:.6f}, R2 = {r2_temp:.6f}")
#
#
# # ==== 保存结果 ====
# train_out = train_long.copy()
# test_out = test_long.copy()
#
# train_out["Baseline_Error"] = train_out["HVap_baseline"] - train_out["HVap_actual"]
# train_out["Final_Error"] = train_out["HVap_final"] - train_out["HVap_actual"]
#
# test_out["Baseline_Error"] = test_out["HVap_baseline"] - test_out["HVap_actual"]
# test_out["Final_Error"] = test_out["HVap_final"] - test_out["HVap_actual"]
#
# summary_df = pd.DataFrame([
#     [
#         "baseline",
#         "train",
#         baseline_train_metrics["R2"],
#         baseline_train_metrics["MSE"],
#         baseline_train_metrics["ARD_%"],
#         baseline_train_metrics["within_1pct"],
#         baseline_train_metrics["within_5pct"],
#         baseline_train_metrics["within_10pct"]
#     ],
#     [
#         "baseline",
#         "test",
#         baseline_test_metrics["R2"],
#         baseline_test_metrics["MSE"],
#         baseline_test_metrics["ARD_%"],
#         baseline_test_metrics["within_1pct"],
#         baseline_test_metrics["within_5pct"],
#         baseline_test_metrics["within_10pct"]
#     ],
#     [
#         "final_GBDT_residual",
#         "train",
#         final_train_metrics["R2"],
#         final_train_metrics["MSE"],
#         final_train_metrics["ARD_%"],
#         final_train_metrics["within_1pct"],
#         final_train_metrics["within_5pct"],
#         final_train_metrics["within_10pct"]
#     ],
#     [
#         "final_GBDT_residual",
#         "test",
#         final_test_metrics["R2"],
#         final_test_metrics["MSE"],
#         final_test_metrics["ARD_%"],
#         final_test_metrics["within_1pct"],
#         final_test_metrics["within_5pct"],
#         final_test_metrics["within_10pct"]
#     ],
#     [
#         "residual_GBDT",
#         "train",
#         residual_train_metrics["R2"],
#         residual_train_metrics["MSE"],
#         residual_train_metrics["ARD_%"],
#         residual_train_metrics["within_1pct"],
#         residual_train_metrics["within_5pct"],
#         residual_train_metrics["within_10pct"]
#     ],
#     [
#         "residual_GBDT",
#         "test",
#         residual_test_metrics["R2"],
#         residual_test_metrics["MSE"],
#         residual_test_metrics["ARD_%"],
#         residual_test_metrics["within_1pct"],
#         residual_test_metrics["within_5pct"],
#         residual_test_metrics["within_10pct"]
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
# out_path = "hvap_baseline_and_final_same_split_GBDT_residual.xlsx"
#
# with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
#     train_out.to_excel(writer, sheet_name="train_results", index=False)
#     test_out.to_excel(writer, sheet_name="test_results", index=False)
#     summary_df.to_excel(writer, sheet_name="summary", index=False)
#
# print(f"\n已保存结果到: {out_path}")


import pandas as pd
import numpy as np

from sklearn.linear_model import HuberRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import PolynomialFeatures
from sklearn.model_selection import train_test_split


# ============================================================
# 0. 常数与路径
# ============================================================

HV0, HVB, Tb0 = 9612.7, 15419.9, 222.543
T_ref = 298.15

main_file = "heat of vaporization 204.xlsx"
tb_descriptor_file = "selected_25_descriptors_data_boiling_point.xlsx"


# ============================================================
# 1. 读取主数据
# ============================================================

df_main = pd.read_excel(main_file, sheet_name="Sheet1").copy()

id_col = df_main.columns[0]
group_cols = list(df_main.columns[13:32])   # 19个基团
temp_cols = list(df_main.columns[32:42])    # 10个温度列
hvap_cols = list(df_main.columns[42:52])    # 10个汽化焓列
tb_col = df_main.columns[5]


# ============================================================
# 2. 数值化
# ============================================================

for col in group_cols + temp_cols + hvap_cols + [tb_col]:
    df_main[col] = pd.to_numeric(df_main[col], errors="coerce")

Nk_all = df_main[group_cols].fillna(0)


# ============================================================
# 3. 统一按物质做 8:2 划分
# ============================================================

unique_materials = df_main[id_col].dropna().unique()

train_materials, test_materials = train_test_split(
    unique_materials,
    test_size=0.2,
    random_state=42
)

train_materials = set(train_materials)
test_materials = set(test_materials)

row_train_mask = df_main[id_col].isin(train_materials).to_numpy()
row_test_mask = df_main[id_col].isin(test_materials).to_numpy()

df_train = df_main.loc[row_train_mask].copy().reset_index(drop=True)
df_test = df_main.loc[row_test_mask].copy().reset_index(drop=True)

print("========== 按物质划分 ==========")
print(f"总物质数: {len(unique_materials)}")
print(f"训练集物质数: {len(train_materials)}")
print(f"测试集物质数: {len(test_materials)}")
print(f"训练集行数: {len(df_train)}")
print(f"测试集行数: {len(df_test)}")


# ============================================================
# 4. 多项式基团特征：仅用训练集 fit
# ============================================================

poly = PolynomialFeatures(degree=2, include_bias=False)

X_groups_train = df_train[group_cols].fillna(0)
X_groups_test = df_test[group_cols].fillna(0)


# ============================================================
# 5. baseline 组件1：Tb 模型，只在训练集训练
# ============================================================

Tb_train_raw = df_train[tb_col].to_numpy(dtype=float)
valid_tb_train = ~np.isnan(Tb_train_raw)

X_poly_train_valid = poly.fit_transform(
    X_groups_train.loc[valid_tb_train]
)

model_Tb = HuberRegressor(
    max_iter=10000
)

model_Tb.fit(
    X_poly_train_valid,
    np.exp(Tb_train_raw[valid_tb_train] / Tb0)
)

Tb_pred_train = Tb0 * np.log(
    np.clip(
        model_Tb.predict(poly.transform(X_groups_train)),
        1e-6,
        None
    )
)

Tb_pred_test = Tb0 * np.log(
    np.clip(
        model_Tb.predict(poly.transform(X_groups_test)),
        1e-6,
        None
    )
)


# ============================================================
# 6. baseline 组件2：HVap_Tb 模型，只在训练集训练
# ============================================================

df_Tb = pd.read_excel(tb_descriptor_file).copy()
target_Tb = "Heat of vaporization at boiling temperature"

if len(df_Tb) != len(df_main):
    raise ValueError(
        "selected_25_descriptors_data_boiling_point.xlsx 与 heat of vaporization 204.xlsx 行数不一致。"
        "当前代码默认两个文件逐行对应；若不是，请改成按 Material_ID 合并。"
    )

X_Tb_all = df_Tb.drop(columns=[target_Tb]).copy()
y_Tb_all = pd.to_numeric(df_Tb[target_Tb], errors="coerce")

for c in X_Tb_all.columns:
    X_Tb_all[c] = pd.to_numeric(X_Tb_all[c], errors="coerce")

valid_rf_mask = (
    (~X_Tb_all.isna().any(axis=1))
    & (~y_Tb_all.isna())
    & (~df_main[id_col].isna())
)

valid_rf_train_mask = valid_rf_mask & df_main[id_col].isin(train_materials)
valid_rf_test_mask = valid_rf_mask & df_main[id_col].isin(test_materials)

rf_Tb = RandomForestRegressor(
    n_estimators=300,
    random_state=42,
    n_jobs=-1
)

rf_Tb.fit(
    X_Tb_all.loc[valid_rf_train_mask],
    y_Tb_all.loc[valid_rf_train_mask]
)

HVap_Tb_pred_train = rf_Tb.predict(
    X_Tb_all.loc[row_train_mask]
)

HVap_Tb_pred_test = rf_Tb.predict(
    X_Tb_all.loc[row_test_mask]
)


# ============================================================
# 7. baseline 组件3：A_k 系数，只在训练集训练
# ============================================================

G_train = X_groups_train.to_numpy(dtype=float)
G_test = X_groups_test.to_numpy(dtype=float)

X_A_train, y_A_train = [], []

for i in range(len(df_train)):
    Tb_i = Tb_pred_train[i]
    HVap_Tb_i = HVap_Tb_pred_train[i]

    for tcol, hvcol in zip(temp_cols, hvap_cols):
        Tj = pd.to_numeric(df_train.at[i, tcol], errors="coerce")
        Hvapj = pd.to_numeric(df_train.at[i, hvcol], errors="coerce")

        if np.isnan(Tj) or np.isnan(Hvapj):
            continue

        Xj = (Tj - Tb_i) * G_train[i]
        yj = Hvapj - HVap_Tb_i

        X_A_train.append(Xj)
        y_A_train.append(yj)

X_A_train = np.array(X_A_train, dtype=float)
y_A_train = np.array(y_A_train, dtype=float)

A_solver = HuberRegressor(
    fit_intercept=False,
    max_iter=5000
)

A_solver.fit(X_A_train, y_A_train)
A_vec = A_solver.coef_


# ============================================================
# 8. 生成 baseline 长表
# ============================================================

def build_baseline_long(sub_df, G, Tb_pred_sub, HVap_Tb_pred_sub, dataset_name):
    rows = []

    for i in range(len(sub_df)):
        material_id = sub_df.at[i, id_col]
        Tb_i = Tb_pred_sub[i]
        HVap_Tb_i = HVap_Tb_pred_sub[i]

        for j, (tcol, hvcol) in enumerate(zip(temp_cols, hvap_cols), start=1):
            Tj = pd.to_numeric(sub_df.at[i, tcol], errors="coerce")
            Hvapj = pd.to_numeric(sub_df.at[i, hvcol], errors="coerce")

            if np.isnan(Tj) or np.isnan(Hvapj):
                continue

            Xj = (Tj - Tb_i) * G[i]
            HVap_baseline = HVap_Tb_i + Xj @ A_vec

            rows.append({
                "Dataset": dataset_name,
                "row_idx_local": i,
                "Material_ID": material_id,
                "temp_index": j,
                "temp_col": tcol,
                "hvap_col": hvcol,
                "T": Tj,
                "HVap_actual": Hvapj,
                "HVap_baseline": HVap_baseline,
                "T_ref": Tb_i,
                "HVap_ref": HVap_Tb_i
            })

    return pd.DataFrame(rows)


train_long = build_baseline_long(
    df_train,
    G_train,
    Tb_pred_train,
    HVap_Tb_pred_train,
    "train"
)

test_long = build_baseline_long(
    df_test,
    G_test,
    Tb_pred_test,
    HVap_Tb_pred_test,
    "test"
)

print(f"baseline训练样本点数: {len(train_long)}")
print(f"baseline测试样本点数: {len(test_long)}")


# ============================================================
# 9. residual 特征构造
# ============================================================

def add_residual_features(long_df, G, Tb_pred_sub, HVap_Tb_pred_sub):
    feature_list = []
    target_list = []

    for _, row in long_df.iterrows():
        i = int(row["row_idx_local"])

        Tj = row["T"]
        HVap_actual = row["HVap_actual"]
        HVap_baseline = row["HVap_baseline"]

        Tb_i = Tb_pred_sub[i]
        HVap_Tb_i = HVap_Tb_pred_sub[i]

        base_features = list(G[i])

        temp_features = [
            Tj,
            Tj - Tb_i,
            Tj / Tb_i if Tb_i > 0 else 0.0,
            np.log(Tj) if Tj > 0 else 0.0,
        ]

        baseline_features = [
            HVap_baseline
        ]

        ref_features = [
            Tb_i,
            HVap_Tb_i
        ]

        x = (
            base_features
            + temp_features
            + baseline_features
            + ref_features
        )

        y = HVap_actual - HVap_baseline

        feature_list.append(x)
        target_list.append(y)

    X_res = np.array(feature_list, dtype=float)
    y_res = np.array(target_list, dtype=float)

    return X_res, y_res


X_res_train, y_res_train = add_residual_features(
    train_long,
    G_train,
    Tb_pred_train,
    HVap_Tb_pred_train
)

X_res_test, y_res_test = add_residual_features(
    test_long,
    G_test,
    Tb_pred_test,
    HVap_Tb_pred_test
)

print(f"residual训练集形状: {X_res_train.shape}")
print(f"residual测试集形状: {X_res_test.shape}")


# ============================================================
# 10. residual 模型：GBDT，只在训练集训练
# ============================================================

residual_model = GradientBoostingRegressor(
    n_estimators=500,
    learning_rate=0.03,
    max_depth=3,
    subsample=0.9,
    min_samples_split=2,
    min_samples_leaf=1,
    loss="squared_error",
    random_state=42
)

print("\n开始训练 residual GBDT 模型...")
residual_model.fit(X_res_train, y_res_train)

print("\nresidual GBDT 模型参数:")
print(residual_model)


# ============================================================
# 11. residual 预测 + final 组合
# ============================================================

train_res_pred = residual_model.predict(X_res_train)
test_res_pred = residual_model.predict(X_res_test)

train_long["Residual_true"] = y_res_train
train_long["Residual_pred"] = train_res_pred
train_long["HVap_final"] = train_long["HVap_baseline"] + train_long["Residual_pred"]

test_long["Residual_true"] = y_res_test
test_long["Residual_pred"] = test_res_pred
test_long["HVap_final"] = test_long["HVap_baseline"] + test_long["Residual_pred"]


# ============================================================
# 12. 评估函数
# ============================================================

def evaluate_regression(y_true, y_pred, name="dataset", strict_less=False):
    y_true = np.array(y_true, dtype=float)
    y_pred = np.array(y_pred, dtype=float)

    finite_mask = np.isfinite(y_true) & np.isfinite(y_pred)

    y_true_valid = y_true[finite_mask]
    y_pred_valid = y_pred[finite_mask]

    relative_error = np.full_like(y_true, np.nan, dtype=float)

    if len(y_true_valid) == 0:
        print(f"\n{name}: 无有效样本")
        return {
            "R2": np.nan,
            "MSE": np.nan,
            "ARD_%": np.nan,
            "within_1pct": 0,
            "within_5pct": 0,
            "within_10pct": 0,
            "relative_error": relative_error
        }

    mse = mean_squared_error(y_true_valid, y_pred_valid)
    r2 = r2_score(y_true_valid, y_pred_valid)

    relative_error_valid = np.full_like(y_true_valid, np.nan, dtype=float)

    nonzero_mask = np.abs(y_true_valid) > 1e-12

    if np.any(nonzero_mask):
        relative_error_valid[nonzero_mask] = np.abs(
            (y_true_valid[nonzero_mask] - y_pred_valid[nonzero_mask])
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

    print(f"\n{name}")
    print(f"R2  = {r2:.6f}")
    print(f"MSE = {mse:.10f}")
    print(f"ARD = {ard:.4f}%")

    if strict_less:
        print(f"<1%  点数: {within_1pct}")
        print(f"<5%  点数: {within_5pct}")
        print(f"<10% 点数: {within_10pct}")
    else:
        print(f"<=1%  点数: {within_1pct}")
        print(f"<=5%  点数: {within_5pct}")
        print(f"<=10% 点数: {within_10pct}")

    return {
        "R2": r2,
        "MSE": mse,
        "ARD_%": ard,
        "within_1pct": within_1pct,
        "within_5pct": within_5pct,
        "within_10pct": within_10pct,
        "relative_error": relative_error
    }


def evaluate_residual(y_true, y_pred, name="residual"):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    finite_mask = np.isfinite(y_true) & np.isfinite(y_pred)

    y_true_valid = y_true[finite_mask]
    y_pred_valid = y_pred[finite_mask]

    if len(y_true_valid) == 0:
        print(f"\n{name}: 无有效样本")
        return {
            "R2": np.nan,
            "MSE": np.nan
        }

    r2 = r2_score(y_true_valid, y_pred_valid)
    mse = mean_squared_error(y_true_valid, y_pred_valid)

    print(f"\n{name}")
    print(f"Residual R2  = {r2:.6f}")
    print(f"Residual MSE = {mse:.10f}")

    return {
        "R2": r2,
        "MSE": mse
    }


# ============================================================
# 13. baseline 与 final 在同一划分下评估
# ============================================================

baseline_train_metrics = evaluate_regression(
    train_long["HVap_actual"].to_numpy(),
    train_long["HVap_baseline"].to_numpy(),
    "baseline - 训练集",
    strict_less=False
)

train_long["Baseline_Relative_Error_%"] = baseline_train_metrics["relative_error"]

baseline_test_metrics = evaluate_regression(
    test_long["HVap_actual"].to_numpy(),
    test_long["HVap_baseline"].to_numpy(),
    "baseline - 测试集",
    strict_less=False
)

test_long["Baseline_Relative_Error_%"] = baseline_test_metrics["relative_error"]

final_train_metrics = evaluate_regression(
    train_long["HVap_actual"].to_numpy(),
    train_long["HVap_final"].to_numpy(),
    "final model GBDT residual - 训练集",
    strict_less=False
)

train_long["Final_Relative_Error_%"] = final_train_metrics["relative_error"]

final_test_metrics = evaluate_regression(
    test_long["HVap_actual"].to_numpy(),
    test_long["HVap_final"].to_numpy(),
    "final model GBDT residual - 测试集",
    strict_less=False
)

test_long["Final_Relative_Error_%"] = final_test_metrics["relative_error"]


# ============================================================
# 14. residual 层面评估
# ============================================================

residual_train_metrics = evaluate_residual(
    y_res_train,
    train_res_pred,
    "residual GBDT - 训练集"
)

residual_test_metrics = evaluate_residual(
    y_res_test,
    test_res_pred,
    "residual GBDT - 测试集"
)


# ============================================================
# 14.1 完整数据集统计：训练集 + 测试集
# ============================================================

baseline_all_true = np.concatenate([
    train_long["HVap_actual"].to_numpy(dtype=float),
    test_long["HVap_actual"].to_numpy(dtype=float)
])

baseline_all_pred = np.concatenate([
    train_long["HVap_baseline"].to_numpy(dtype=float),
    test_long["HVap_baseline"].to_numpy(dtype=float)
])

baseline_all_metrics = evaluate_regression(
    baseline_all_true,
    baseline_all_pred,
    "baseline - 完整数据集 train + test",
    strict_less=True
)

final_all_true = np.concatenate([
    train_long["HVap_actual"].to_numpy(dtype=float),
    test_long["HVap_actual"].to_numpy(dtype=float)
])

final_all_pred = np.concatenate([
    train_long["HVap_final"].to_numpy(dtype=float),
    test_long["HVap_final"].to_numpy(dtype=float)
])

final_all_metrics = evaluate_regression(
    final_all_true,
    final_all_pred,
    "final model GBDT residual - 完整数据集 train + test",
    strict_less=True
)

residual_all_true = np.concatenate([
    y_res_train,
    y_res_test
])

residual_all_pred = np.concatenate([
    train_res_pred,
    test_res_pred
])

residual_all_metrics = evaluate_residual(
    residual_all_true,
    residual_all_pred,
    "residual GBDT - 完整数据集 train + test"
)

print("\nfinal model GBDT residual 完整数据集 1%，5%，10%分别为：")
print(final_all_metrics["within_1pct"])
print(final_all_metrics["within_5pct"])
print(final_all_metrics["within_10pct"])


# ============================================================
# 15. 分温度点评估：测试集 final
# ============================================================

print("\n=== 测试集分温度点评估（final GBDT residual） ===")

for tcol, hvcol in zip(temp_cols, hvap_cols):
    m = (test_long["temp_col"] == tcol)

    if m.any():
        y_true_temp = test_long.loc[m, "HVap_actual"].to_numpy()
        y_pred_temp = test_long.loc[m, "HVap_final"].to_numpy()

        mse_temp = mean_squared_error(y_true_temp, y_pred_temp)
        r2_temp = r2_score(y_true_temp, y_pred_temp)

        print(f"{tcol}: MSE = {mse_temp:.6f}, R2 = {r2_temp:.6f}")


# ============================================================
# 16. 保存结果
# ============================================================

train_out = train_long.copy()
test_out = test_long.copy()

train_out["Baseline_Error"] = train_out["HVap_baseline"] - train_out["HVap_actual"]
train_out["Final_Error"] = train_out["HVap_final"] - train_out["HVap_actual"]

test_out["Baseline_Error"] = test_out["HVap_baseline"] - test_out["HVap_actual"]
test_out["Final_Error"] = test_out["HVap_final"] - test_out["HVap_actual"]

all_out = pd.concat(
    [train_out, test_out],
    axis=0,
    ignore_index=True
)

all_out["Dataset"] = "all_train_plus_test"


# ============================================================
# 17. 保存汇总
# ============================================================

summary_df = pd.DataFrame([
    [
        "baseline",
        "train",
        baseline_train_metrics["R2"],
        baseline_train_metrics["MSE"],
        baseline_train_metrics["ARD_%"],
        baseline_train_metrics["within_1pct"],
        baseline_train_metrics["within_5pct"],
        baseline_train_metrics["within_10pct"],
        np.nan,
        np.nan
    ],
    [
        "baseline",
        "test",
        baseline_test_metrics["R2"],
        baseline_test_metrics["MSE"],
        baseline_test_metrics["ARD_%"],
        baseline_test_metrics["within_1pct"],
        baseline_test_metrics["within_5pct"],
        baseline_test_metrics["within_10pct"],
        np.nan,
        np.nan
    ],
    [
        "baseline",
        "all_train_plus_test",
        baseline_all_metrics["R2"],
        baseline_all_metrics["MSE"],
        baseline_all_metrics["ARD_%"],
        baseline_all_metrics["within_1pct"],
        baseline_all_metrics["within_5pct"],
        baseline_all_metrics["within_10pct"],
        np.nan,
        np.nan
    ],
    [
        "final_GBDT_residual",
        "train",
        final_train_metrics["R2"],
        final_train_metrics["MSE"],
        final_train_metrics["ARD_%"],
        final_train_metrics["within_1pct"],
        final_train_metrics["within_5pct"],
        final_train_metrics["within_10pct"],
        residual_train_metrics["R2"],
        residual_train_metrics["MSE"]
    ],
    [
        "final_GBDT_residual",
        "test",
        final_test_metrics["R2"],
        final_test_metrics["MSE"],
        final_test_metrics["ARD_%"],
        final_test_metrics["within_1pct"],
        final_test_metrics["within_5pct"],
        final_test_metrics["within_10pct"],
        residual_test_metrics["R2"],
        residual_test_metrics["MSE"]
    ],
    [
        "final_GBDT_residual",
        "all_train_plus_test",
        final_all_metrics["R2"],
        final_all_metrics["MSE"],
        final_all_metrics["ARD_%"],
        final_all_metrics["within_1pct"],
        final_all_metrics["within_5pct"],
        final_all_metrics["within_10pct"],
        residual_all_metrics["R2"],
        residual_all_metrics["MSE"]
    ],
    [
        "residual_GBDT",
        "train",
        residual_train_metrics["R2"],
        residual_train_metrics["MSE"],
        np.nan,
        np.nan,
        np.nan,
        np.nan,
        residual_train_metrics["R2"],
        residual_train_metrics["MSE"]
    ],
    [
        "residual_GBDT",
        "test",
        residual_test_metrics["R2"],
        residual_test_metrics["MSE"],
        np.nan,
        np.nan,
        np.nan,
        np.nan,
        residual_test_metrics["R2"],
        residual_test_metrics["MSE"]
    ],
    [
        "residual_GBDT",
        "all_train_plus_test",
        residual_all_metrics["R2"],
        residual_all_metrics["MSE"],
        np.nan,
        np.nan,
        np.nan,
        np.nan,
        residual_all_metrics["R2"],
        residual_all_metrics["MSE"]
    ],
], columns=[
    "Model",
    "Dataset",
    "R2",
    "MSE",
    "ARD_%",
    "within_1pct",
    "within_5pct",
    "within_10pct",
    "Residual_R2",
    "Residual_MSE"
])


# ============================================================
# 18. 保存到 Excel
# ============================================================

out_path = "hvap_baseline_and_final_same_split_GBDT_residual.xlsx"

with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
    train_out.to_excel(
        writer,
        sheet_name="train_results",
        index=False
    )

    test_out.to_excel(
        writer,
        sheet_name="test_results",
        index=False
    )

    all_out.to_excel(
        writer,
        sheet_name="all_results",
        index=False
    )

    summary_df.to_excel(
        writer,
        sheet_name="summary",
        index=False
    )

print(f"\n已保存结果到: {out_path}")


# ============================================================
# 19. 输出模型结构记录
# ============================================================

print("\n当前 Hvap baseline + GBDT residual 模型结构:")
print("Tb_submodel: HuberRegressor(max_iter=10000), input = PolynomialFeatures(Nk, degree=2)")
print("HVap_Tb_submodel: RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1), input = selected 25 descriptors at boiling point")
print("Baseline: HVap_baseline = HVap_Tb_pred + (T - Tb_pred) * sum(Ak * Nk)")
print("A_solver: HuberRegressor(fit_intercept=False, max_iter=5000)")
print("Residual model: GradientBoostingRegressor(n_estimators=500, learning_rate=0.03, max_depth=3, subsample=0.9, random_state=42)")
print("Residual target: HVap_actual - HVap_baseline")
print("Residual features: Nk + T + (T-Tb) + T/Tb + ln(T) + HVap_baseline + Tb_pred + HVap_Tb_pred")
print("Final prediction: HVap_final = HVap_baseline + residual_pred")
print("Final all-data statistics use strict thresholds: <1%, <5%, <10%")