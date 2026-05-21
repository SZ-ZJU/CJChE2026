# import pandas as pd
# import numpy as np
# from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
# from sklearn.linear_model import HuberRegressor
# from sklearn.preprocessing import PolynomialFeatures, StandardScaler
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split, cross_val_score
#
# # ==== 1. 数据加载 ====
# df = pd.read_excel("Gibbs free energy 205.xlsx", sheet_name="Sheet7")
#
# id_col = df.columns[0]
# group_cols = df.columns[12:31]   # 第13~31列：基团
# temp_cols = df.columns[31:41]    # 第32~41列：温度
# v_cols = df.columns[41:51]       # 第42~51列：目标变量（吉布斯自由能）
#
# # ==== 2. 数据预处理 ====
# for col in temp_cols.tolist() + v_cols.tolist():
#     df[col] = pd.to_numeric(df[col], errors='coerce')
#
# Nk_all = df[group_cols].apply(pd.to_numeric, errors='coerce')
#
# # 只保留至少有一个有效目标点的物质
# valid_material_mask = df[v_cols].notna().any(axis=1)
# df = df.loc[valid_material_mask].copy().reset_index(drop=True)
# Nk_all = df[group_cols].apply(pd.to_numeric, errors='coerce')
#
# print(f"有效物质数: {len(df)}")
#
# # ==== 3. Hvap 模型（Tb）====
# # 保持全数据训练不变
# df_Tb = pd.read_excel("selected_25_descriptors_boiling.xlsx")
# X_Tb = df_Tb.drop(columns=["ASPEN Vapor pressure at BoilingTemperature(bar)"])
# y_Tb = df_Tb["ASPEN Vapor pressure at BoilingTemperature(bar)"]
# rf_Tb = RandomForestRegressor(random_state=42)
# rf_Tb.fit(X_Tb, y_Tb)
# HVap_Tb_all = rf_Tb.predict(X_Tb)
#
# if len(HVap_Tb_all) != len(df):
#     raise ValueError(
#         f"selected_25_descriptors_boiling.xlsx 预测行数 = {len(HVap_Tb_all)}，与主表物质数 = {len(df)} 不一致。"
#     )
#
# # ==== 4. Tb 模型预测（标准化 + 多项式）====
# # 保持全数据训练不变
# Tb_raw = pd.to_numeric(df.iloc[:, 5], errors='coerce').values
# Tb0 = 222.543
#
# poly = PolynomialFeatures(degree=2, include_bias=False)
# Nk_poly = poly.fit_transform(Nk_all)
# scaler_tb = StandardScaler()
# Nk_scaled = scaler_tb.fit_transform(Nk_poly)
#
# mask_tb = ~np.isnan(Tb_raw)
# model_Tb = HuberRegressor(max_iter=10000)
# model_Tb.fit(Nk_scaled[mask_tb], np.exp(Tb_raw[mask_tb] / Tb0))
# Tb_pred_all = Tb0 * np.log(np.clip(model_Tb.predict(Nk_scaled), 1e-6, None))
#
# # ==== 5. 按物质 8:2 划分 ====
# # 只用于基线模型和残差模型
# unique_materials = df[id_col].dropna().unique()
#
# train_materials, test_materials = train_test_split(
#     unique_materials,
#     test_size=0.2,
#     random_state=42
# )
#
# train_row_mask = df[id_col].isin(train_materials).values
# test_row_mask = df[id_col].isin(test_materials).values
#
# train_df = df.loc[train_row_mask].copy().reset_index(drop=True)
# test_df = df.loc[test_row_mask].copy().reset_index(drop=True)
#
# print(f"训练集物质数: {len(train_df)}")
# print(f"测试集物质数: {len(test_df)}")
#
# # 全数据子模型预测切分到 train / test
# G_all = Nk_all.values
# G_train = G_all[train_row_mask]
# G_test = G_all[test_row_mask]
#
# Tb_pred_train = Tb_pred_all[train_row_mask]
# Tb_pred_test = Tb_pred_all[test_row_mask]
#
# HVap_Tb_train = HVap_Tb_all[train_row_mask]
# HVap_Tb_test = HVap_Tb_all[test_row_mask]
#
# # ==== 6. A_k 系数训练（只用训练集）====
# X_rows_train = []
# y_rows_train = []
#
# for i in range(len(train_df)):
#     for j, (tcol, vcol) in enumerate(zip(temp_cols, v_cols)):
#         Tj = train_df.at[i, tcol]
#         Vj = train_df.at[i, vcol]
#
#         if np.isnan(Tj) or np.isnan(Vj):
#             continue
#         if not np.isfinite(Tb_pred_train[i]) or not np.isfinite(HVap_Tb_train[i]) or not np.isfinite(G_train[i]).all():
#             continue
#
#         Tb_i = Tb_pred_train[i]
#         HVap_Tb_i = HVap_Tb_train[i]
#
#         Xj = (Tj - Tb_i) * G_train[i]
#         yj = Vj - HVap_Tb_i
#
#         X_rows_train.append(Xj)
#         y_rows_train.append(yj)
#
# X_A_train = np.array(X_rows_train)
# y_A_train = np.array(y_rows_train)
#
# A_solver = HuberRegressor(fit_intercept=False, max_iter=5000)
# A_solver.fit(X_A_train, y_A_train)
# A_vec = A_solver.coef_
#
# # ==== 7. 生成基准吉布斯自由能预测（分别对 train / test）====
# def build_baseline_predictions(df_part, G_part, Tb_pred_part, HVap_Tb_part):
#     pred_df = pd.DataFrame(index=df_part.index, columns=v_cols, dtype=float)
#
#     for i in range(len(df_part)):
#         if not np.isfinite(Tb_pred_part[i]) or not np.isfinite(HVap_Tb_part[i]) or not np.isfinite(G_part[i]).all():
#             pred_df.loc[i, :] = np.nan
#             continue
#
#         Tb_i = Tb_pred_part[i]
#         HVap_Tb_i = HVap_Tb_part[i]
#
#         for tcol, vcol in zip(temp_cols, v_cols):
#             Tj = df_part.at[i, tcol]
#             if np.isnan(Tj):
#                 pred_df.at[i, vcol] = np.nan
#                 continue
#
#             Xj = (Tj - Tb_i) * G_part[i]
#             pred_df.at[i, vcol] = HVap_Tb_i + Xj @ A_vec
#
#     return pred_df
#
# V_pred_baseline_train = build_baseline_predictions(train_df, G_train, Tb_pred_train, HVap_Tb_train)
# V_pred_baseline_test = build_baseline_predictions(test_df, G_test, Tb_pred_test, HVap_Tb_test)
#
# # ==== 8. 残差训练集（只用训练集）====
# print("训练残差机器学习模型...")
#
# def build_residual_dataset(df_part, G_part, Tb_pred_part, HVap_Tb_part, baseline_pred_df):
#     residual_features = []
#     residual_targets = []
#
#     for tcol, vcol in zip(temp_cols, v_cols):
#         Tj = df_part[tcol].to_numpy()
#         Vj = df_part[vcol].to_numpy()
#         msk = (~np.isnan(Tj)) & (~np.isnan(Vj)) & (~baseline_pred_df[vcol].isna().to_numpy())
#
#         for i in np.where(msk)[0]:
#             baseline_pred = baseline_pred_df.at[i, vcol]
#             if not np.isfinite(baseline_pred):
#                 continue
#
#             base_features = list(G_part[i])
#             temp_features = [
#                 Tj[i],
#                 Tj[i] - Tb_pred_part[i],
#                 Tj[i] / Tb_pred_part[i] if Tb_pred_part[i] > 0 else 0,
#                 np.log(Tj[i]) if Tj[i] > 0 else 0,
#             ]
#             baseline_features = [baseline_pred]
#             ref_features = [Tb_pred_part[i], HVap_Tb_part[i]]
#
#             all_features = base_features + temp_features + baseline_features + ref_features
#             residual_features.append(all_features)
#
#             residual_targets.append(Vj[i] - baseline_pred)
#
#     return np.array(residual_features), np.array(residual_targets)
#
# residual_X_train, residual_y_train = build_residual_dataset(
#     train_df, G_train, Tb_pred_train, HVap_Tb_train, V_pred_baseline_train
# )
#
# print(f"残差训练集形状: {residual_X_train.shape}")
# print(f"残差目标形状: {residual_y_train.shape}")
#
# # 标准化特征：只在训练集 fit
# scaler_residual = StandardScaler()
# residual_X_train_scaled = scaler_residual.fit_transform(residual_X_train)
#
# # 残差模型
# residual_model = GradientBoostingRegressor(
#     n_estimators=200,
#     learning_rate=0.05,
#     max_depth=5,
#     min_samples_split=20,
#     min_samples_leaf=10,
#     random_state=42
# )
#
# # 交叉验证：只在训练残差集上做
# cv_scores = cross_val_score(
#     residual_model,
#     residual_X_train_scaled,
#     residual_y_train,
#     cv=5,
#     scoring='r2'
# )
# print(f"残差模型交叉验证 R²: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
#
# # 训练最终残差模型
# residual_model.fit(residual_X_train_scaled, residual_y_train)
#
# # ==== 9. 生成最终预测（基准 + 残差修正），分别对 train / test ====
# def build_final_predictions(df_part, G_part, Tb_pred_part, HVap_Tb_part, baseline_pred_df):
#     pred_df = pd.DataFrame(index=df_part.index, columns=v_cols, dtype=float)
#
#     for tcol, vcol in zip(temp_cols, v_cols):
#         Tj = df_part[tcol].to_numpy()
#         features_list = []
#         valid_indices = []
#
#         for i in range(len(df_part)):
#             if np.isnan(Tj[i]):
#                 continue
#
#             baseline_pred = baseline_pred_df.at[i, vcol]
#             if not np.isfinite(baseline_pred):
#                 continue
#
#             base_features = list(G_part[i])
#             temp_features = [
#                 Tj[i],
#                 Tj[i] - Tb_pred_part[i],
#                 Tj[i] / Tb_pred_part[i] if Tb_pred_part[i] > 0 else 0,
#                 np.log(Tj[i]) if Tj[i] > 0 else 0,
#             ]
#             baseline_features = [baseline_pred]
#             ref_features = [Tb_pred_part[i], HVap_Tb_part[i]]
#
#             all_features = base_features + temp_features + baseline_features + ref_features
#             features_list.append(all_features)
#             valid_indices.append(i)
#
#         if len(features_list) > 0:
#             features_array = np.array(features_list)
#             features_scaled = scaler_residual.transform(features_array)
#             residual_pred = residual_model.predict(features_scaled)
#
#             for idx, residual_val in zip(valid_indices, residual_pred):
#                 pred_df.at[idx, vcol] = baseline_pred_df.at[idx, vcol] + residual_val
#
#     return pred_df
#
# V_pred_final_train = build_final_predictions(
#     train_df, G_train, Tb_pred_train, HVap_Tb_train, V_pred_baseline_train
# )
# V_pred_final_test = build_final_predictions(
#     test_df, G_test, Tb_pred_test, HVap_Tb_test, V_pred_baseline_test
# )
#
# # ==== 10. 评估函数 ====
# def collect_true_pred(df_part, pred_df, value_cols):
#     y_true_all, y_pred_all = [], []
#
#     for vcol in value_cols:
#         m = (~df_part[vcol].isna()) & (~pred_df[vcol].isna())
#         if m.any():
#             y_true_all.append(df_part.loc[m, vcol].to_numpy())
#             y_pred_all.append(pred_df.loc[m, vcol].to_numpy())
#
#     if len(y_true_all) == 0:
#         return np.array([]), np.array([])
#
#     return np.concatenate(y_true_all), np.concatenate(y_pred_all)
#
# def eval_final_regression(y_true, y_pred, model_name, split_name):
#     if len(y_true) == 0:
#         print(f"\n{model_name} - {split_name}: 无有效样本")
#         return {
#             "Model": model_name,
#             "Split": split_name,
#             "R2": np.nan,
#             "MSE": np.nan,
#             "ARD_%": np.nan,
#             "within_1pct": np.nan,
#             "within_5pct": np.nan,
#             "within_10pct": np.nan
#         }, np.array([])
#
#     mse = mean_squared_error(y_true, y_pred)
#     r2 = r2_score(y_true, y_pred)
#
#     relative_error = np.abs((y_pred - y_true) / y_true) * 100
#     within_1pct = np.sum(relative_error <= 1)
#     within_5pct = np.sum(relative_error <= 5)
#     within_10pct = np.sum(relative_error <= 10)
#     ard = np.mean(relative_error)
#
#     print(f"\n{model_name} - {split_name}")
#     print(f"R²  = {r2:.6f}")
#     print(f"MSE = {mse:.6f}")
#     print(f"ARD = {ard:.2f}%")
#     print(f"误差 ≤ 1% 的点数: {within_1pct}")
#     print(f"误差 ≤ 5% 的点数: {within_5pct}")
#     print(f"误差 ≤ 10% 的点数: {within_10pct}")
#
#     return {
#         "Model": model_name,
#         "Split": split_name,
#         "R2": r2,
#         "MSE": mse,
#         "ARD_%": ard,
#         "within_1pct": within_1pct,
#         "within_5pct": within_5pct,
#         "within_10pct": within_10pct
#     }, relative_error
#
# # ==== 11. 基线 / 最终模型评估（train/test 分开）====
# print("\n=== 基线模型性能 ===")
# y_train_true_base, y_train_pred_base = collect_true_pred(train_df, V_pred_baseline_train, v_cols)
# y_test_true_base, y_test_pred_base = collect_true_pred(test_df, V_pred_baseline_test, v_cols)
#
# baseline_metrics_train, _ = eval_final_regression(
#     y_train_true_base, y_train_pred_base, "Baseline_model", "train"
# )
# baseline_metrics_test, _ = eval_final_regression(
#     y_test_true_base, y_test_pred_base, "Baseline_model", "test"
# )
#
# print("\n=== 最终模型性能（基准 + 残差修正）===")
# y_train_true_final, y_train_pred_final = collect_true_pred(train_df, V_pred_final_train, v_cols)
# y_test_true_final, y_test_pred_final = collect_true_pred(test_df, V_pred_final_test, v_cols)
#
# final_metrics_train, rel_err_train = eval_final_regression(
#     y_train_true_final, y_train_pred_final, "Final_model", "train"
# )
# final_metrics_test, rel_err_test = eval_final_regression(
#     y_test_true_final, y_test_pred_final, "Final_model", "test"
# )
#
# # ==== 12. 分温度点评估（最终模型）====
# print("\n分温度点评估（最终模型，训练集）:")
# for tcol, vcol in zip(temp_cols, v_cols):
#     m = (~train_df[tcol].isna()) & (~train_df[vcol].isna()) & (~V_pred_final_train[vcol].isna())
#     if m.any():
#         v_true = train_df.loc[m, vcol].to_numpy()
#         v_pred = V_pred_final_train.loc[m, vcol].to_numpy()
#         mse_temp = mean_squared_error(v_true, v_pred)
#         r2_temp = r2_score(v_true, v_pred)
#         print(f"  {tcol}: MSE = {mse_temp:.6f}, R² = {r2_temp:.6f}")
#
# print("\n分温度点评估（最终模型，测试集）:")
# for tcol, vcol in zip(temp_cols, v_cols):
#     m = (~test_df[tcol].isna()) & (~test_df[vcol].isna()) & (~V_pred_final_test[vcol].isna())
#     if m.any():
#         v_true = test_df.loc[m, vcol].to_numpy()
#         v_pred = V_pred_final_test.loc[m, vcol].to_numpy()
#         mse_temp = mean_squared_error(v_true, v_pred)
#         r2_temp = r2_score(v_true, v_pred)
#         print(f"  {tcol}: MSE = {mse_temp:.6f}, R² = {r2_temp:.6f}")
#
# # ==== 13. 保存结果 ====
# out_path = "gibbs_free_energy_actual_vs_pred_with_residual_correction_train_test_split.xlsx"
#
# def build_long_compare(df_part, split_name, Tb_pred_part, HVap_ref_part, baseline_pred_df, final_pred_df):
#     rows = []
#     for idx in range(len(df_part)):
#         ID = df_part.at[idx, id_col]
#         for j, (tcol, vcol) in enumerate(zip(temp_cols, v_cols), start=1):
#             T = df_part.at[idx, tcol]
#             V_act = df_part.at[idx, vcol]
#             V_base = baseline_pred_df.at[idx, vcol] if pd.notna(baseline_pred_df.at[idx, vcol]) else np.nan
#             V_final = final_pred_df.at[idx, vcol] if pd.notna(final_pred_df.at[idx, vcol]) else np.nan
#
#             err_base = (V_base - V_act) if (pd.notna(V_base) and pd.notna(V_act)) else np.nan
#             err_final = (V_final - V_act) if (pd.notna(V_final) and pd.notna(V_act)) else np.nan
#             residual_correction = (V_final - V_base) if (pd.notna(V_final) and pd.notna(V_base)) else np.nan
#
#             rows.append({
#                 "Split": split_name,
#                 id_col: ID,
#                 "temp_index": j,
#                 "temp_col": tcol,
#                 "T": T,
#                 "Gibbs_Free_Energy_actual": V_act,
#                 "Gibbs_Free_Energy_baseline": V_base,
#                 "Gibbs_Free_Energy_final": V_final,
#                 "error_baseline": err_base,
#                 "error_final": err_final,
#                 "residual_correction": residual_correction,
#                 "T_ref": Tb_pred_part[idx],
#                 "Gibbs_Free_Energy_ref": HVap_ref_part[idx]
#             })
#     return pd.DataFrame(rows)
#
# long_train = build_long_compare(
#     train_df, "train", Tb_pred_train, HVap_Tb_train, V_pred_baseline_train, V_pred_final_train
# )
# long_test = build_long_compare(
#     test_df, "test", Tb_pred_test, HVap_Tb_test, V_pred_baseline_test, V_pred_final_test
# )
# long_compare = pd.concat([long_train, long_test], ignore_index=True).sort_values(["Split", id_col, "temp_index"])
#
# summary_df = pd.DataFrame([
#     baseline_metrics_train, baseline_metrics_test,
#     final_metrics_train, final_metrics_test
# ])
#
# with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
#     long_compare.to_excel(writer, sheet_name="compare_long", index=False)
#     summary_df.to_excel(writer, sheet_name="summary", index=False)
#
# print(f"\n✅ 结果已保存到: {out_path}")
#
# print("\n📊 总模型评估（基准 + 残差修正，测试集）：")
# print(f"R²  = {final_metrics_test['R2']:.4f}")
# print(f"MSE = {final_metrics_test['MSE']:.6f}")
# print(f"ARD = {final_metrics_test['ARD_%']:.2f}%")
# print(f"✅ 误差 ≤ 1% 的数据点数量: {final_metrics_test['within_1pct']}")
# print(f"✅ 误差 ≤ 5% 的数据点数量: {final_metrics_test['within_5pct']}")
# print(f"✅ 误差 ≤ 10% 的数据点数量: {final_metrics_test['within_10pct']}")


import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import HuberRegressor
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split, cross_val_score


# ============================================================
# 1. 数据加载
# ============================================================
df = pd.read_excel("Gibbs free energy 205.xlsx", sheet_name="Sheet7")

id_col = df.columns[0]
group_cols = df.columns[12:31]   # 第13~31列：19个基团
temp_cols = df.columns[31:41]    # 第32~41列：10个温度
v_cols = df.columns[41:51]       # 第42~51列：Gibbs free energy


# ============================================================
# 2. 数据预处理
# ============================================================
for col in list(group_cols) + list(temp_cols) + list(v_cols):
    df[col] = pd.to_numeric(df[col], errors="coerce")

Nk_all = df[group_cols].apply(pd.to_numeric, errors="coerce")

# 只保留至少有一个有效目标点的物质
valid_material_mask = df[v_cols].notna().any(axis=1)

df = df.loc[valid_material_mask].copy().reset_index(drop=True)
Nk_all = df[group_cols].apply(pd.to_numeric, errors="coerce")

print(f"有效物质数: {len(df)}")


# ============================================================
# 3. VP_Tb 子模型：全数据训练
# ============================================================
df_Tb = pd.read_excel("selected_25_descriptors_boiling.xlsx").copy()

target_Tb = "ASPEN Vapor pressure at BoilingTemperature(bar)"

X_Tb = df_Tb.drop(columns=[target_Tb], errors="ignore").copy()
X_Tb = X_Tb.apply(pd.to_numeric, errors="coerce")
X_Tb = X_Tb.replace([np.inf, -np.inf], np.nan)

y_Tb = pd.to_numeric(
    df_Tb[target_Tb],
    errors="coerce"
).values

valid_Tb_mask = (
    X_Tb.notna().all(axis=1)
    & np.isfinite(y_Tb)
)

rf_Tb = RandomForestRegressor(
    random_state=42,
    n_jobs=-1
)

rf_Tb.fit(
    X_Tb.loc[valid_Tb_mask],
    y_Tb[valid_Tb_mask]
)

X_Tb_predict = X_Tb.fillna(
    X_Tb.loc[valid_Tb_mask].median(numeric_only=True)
)

VP_Tb_all = rf_Tb.predict(X_Tb_predict)

if len(VP_Tb_all) != len(df):
    raise ValueError(
        f"selected_25_descriptors_boiling.xlsx 预测行数 = {len(VP_Tb_all)}，"
        f"与主表物质数 = {len(df)} 不一致。"
    )


# ============================================================
# 4. Tb 子模型预测：标准化 + 二阶基团特征，全数据训练
# ============================================================
Tb_raw = pd.to_numeric(df.iloc[:, 5], errors="coerce").values
Tb0 = 222.543

poly = PolynomialFeatures(
    degree=2,
    include_bias=False
)

Nk_poly = poly.fit_transform(Nk_all)

scaler_tb = StandardScaler()
Nk_scaled = scaler_tb.fit_transform(Nk_poly)

mask_tb = (
    np.isfinite(Tb_raw)
    & np.isfinite(Nk_scaled).all(axis=1)
)

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


# ============================================================
# 5. 按物质 8:2 划分
# ============================================================
unique_materials = df[id_col].dropna().unique()

train_materials, test_materials = train_test_split(
    unique_materials,
    test_size=0.2,
    random_state=42
)

train_materials = set(train_materials)
test_materials = set(test_materials)

train_row_mask = df[id_col].isin(train_materials).values
test_row_mask = df[id_col].isin(test_materials).values

train_df = df.loc[train_row_mask].copy().reset_index(drop=True)
test_df = df.loc[test_row_mask].copy().reset_index(drop=True)

print("\n========== 按物质划分 ==========")
print(f"总物质数: {len(unique_materials)}")
print(f"训练集物质数: {len(train_materials)}")
print(f"测试集物质数: {len(test_materials)}")
print(f"训练集物质行数: {len(train_df)}")
print(f"测试集物质行数: {len(test_df)}")


# 子模型预测切分到 train / test
G_all = Nk_all.values

G_train = G_all[train_row_mask]
G_test = G_all[test_row_mask]

Tb_pred_train = Tb_pred_all[train_row_mask]
Tb_pred_test = Tb_pred_all[test_row_mask]

VP_Tb_train = VP_Tb_all[train_row_mask]
VP_Tb_test = VP_Tb_all[test_row_mask]


# ============================================================
# 6. A_k 系数训练：只用训练集
# ============================================================
X_rows_train = []
y_rows_train = []

for i in range(len(train_df)):
    for tcol, vcol in zip(temp_cols, v_cols):
        Tj = train_df.at[i, tcol]
        Gj = train_df.at[i, vcol]

        if np.isnan(Tj) or np.isnan(Gj):
            continue

        if (
            not np.isfinite(Tb_pred_train[i])
            or not np.isfinite(VP_Tb_train[i])
            or not np.isfinite(G_train[i]).all()
        ):
            continue

        Tb_i = Tb_pred_train[i]
        VP_Tb_i = VP_Tb_train[i]

        Xj = (Tj - Tb_i) * G_train[i]
        yj = Gj - VP_Tb_i

        X_rows_train.append(Xj)
        y_rows_train.append(yj)

X_A_train = np.array(X_rows_train, dtype=float)
y_A_train = np.array(y_rows_train, dtype=float)

A_solver = HuberRegressor(
    fit_intercept=False,
    max_iter=5000
)

A_solver.fit(
    X_A_train,
    y_A_train
)

A_vec = A_solver.coef_


# ============================================================
# 7. 生成 baseline Gibbs free energy 预测
# ============================================================
def build_baseline_predictions(df_part, G_part, Tb_pred_part, VP_Tb_part):
    pred_df = pd.DataFrame(
        index=df_part.index,
        columns=v_cols,
        dtype=float
    )

    for i in range(len(df_part)):
        if (
            not np.isfinite(Tb_pred_part[i])
            or not np.isfinite(VP_Tb_part[i])
            or not np.isfinite(G_part[i]).all()
        ):
            pred_df.loc[i, :] = np.nan
            continue

        Tb_i = Tb_pred_part[i]
        VP_Tb_i = VP_Tb_part[i]

        for tcol, vcol in zip(temp_cols, v_cols):
            Tj = df_part.at[i, tcol]

            if np.isnan(Tj):
                pred_df.at[i, vcol] = np.nan
                continue

            Xj = (Tj - Tb_i) * G_part[i]
            pred_df.at[i, vcol] = VP_Tb_i + Xj @ A_vec

    return pred_df


Gibbs_pred_baseline_train = build_baseline_predictions(
    train_df,
    G_train,
    Tb_pred_train,
    VP_Tb_train
)

Gibbs_pred_baseline_test = build_baseline_predictions(
    test_df,
    G_test,
    Tb_pred_test,
    VP_Tb_test
)


# ============================================================
# 8. 构建 residual 数据集
# ============================================================
print("\n训练残差机器学习模型...")


def build_residual_dataset(df_part, G_part, Tb_pred_part, VP_Tb_part, baseline_pred_df):
    residual_features = []
    residual_targets = []

    for tcol, vcol in zip(temp_cols, v_cols):
        Tj = df_part[tcol].to_numpy(dtype=float)
        Gj = df_part[vcol].to_numpy(dtype=float)

        msk = (
            (~np.isnan(Tj))
            & (~np.isnan(Gj))
            & (~baseline_pred_df[vcol].isna().to_numpy())
        )

        for i in np.where(msk)[0]:
            baseline_pred = baseline_pred_df.at[i, vcol]

            if not np.isfinite(baseline_pred):
                continue

            base_features = list(G_part[i])

            temp_features = [
                Tj[i],
                Tj[i] - Tb_pred_part[i],
                Tj[i] / Tb_pred_part[i] if Tb_pred_part[i] > 0 else 0.0,
                np.log(Tj[i]) if Tj[i] > 0 else 0.0,
            ]

            baseline_features = [
                baseline_pred
            ]

            ref_features = [
                Tb_pred_part[i],
                VP_Tb_part[i]
            ]

            all_features = (
                base_features
                + temp_features
                + baseline_features
                + ref_features
            )

            residual_features.append(all_features)
            residual_targets.append(Gj[i] - baseline_pred)

    return (
        np.array(residual_features, dtype=float),
        np.array(residual_targets, dtype=float)
    )


residual_X_train, residual_y_train = build_residual_dataset(
    train_df,
    G_train,
    Tb_pred_train,
    VP_Tb_train,
    Gibbs_pred_baseline_train
)

residual_X_test, residual_y_test = build_residual_dataset(
    test_df,
    G_test,
    Tb_pred_test,
    VP_Tb_test,
    Gibbs_pred_baseline_test
)

print(f"残差训练集形状: {residual_X_train.shape}")
print(f"残差目标形状: {residual_y_train.shape}")
print(f"残差测试集形状: {residual_X_test.shape}")
print(f"残差测试目标形状: {residual_y_test.shape}")


# ============================================================
# 9. residual 模型：GBDT，只用训练集训练
# ============================================================
scaler_residual = StandardScaler()

residual_X_train_scaled = scaler_residual.fit_transform(residual_X_train)
residual_X_test_scaled = scaler_residual.transform(residual_X_test)

residual_model = GradientBoostingRegressor(
    n_estimators=200,
    learning_rate=0.05,
    max_depth=5,
    min_samples_split=20,
    min_samples_leaf=10,
    random_state=42
)

cv_scores = cross_val_score(
    residual_model,
    residual_X_train_scaled,
    residual_y_train,
    cv=5,
    scoring="r2"
)

print(f"残差模型交叉验证 R²: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")

print("\n开始训练 residual GBDT 模型...")
residual_model.fit(
    residual_X_train_scaled,
    residual_y_train
)

residual_pred_train = residual_model.predict(residual_X_train_scaled)
residual_pred_test = residual_model.predict(residual_X_test_scaled)


# ============================================================
# 10. 生成最终预测：baseline + residual
# ============================================================
def build_final_predictions(df_part, G_part, Tb_pred_part, VP_Tb_part, baseline_pred_df):
    pred_df = pd.DataFrame(
        index=df_part.index,
        columns=v_cols,
        dtype=float
    )

    for tcol, vcol in zip(temp_cols, v_cols):
        Tj = df_part[tcol].to_numpy(dtype=float)

        features_list = []
        valid_indices = []

        for i in range(len(df_part)):
            if np.isnan(Tj[i]):
                continue

            baseline_pred = baseline_pred_df.at[i, vcol]

            if not np.isfinite(baseline_pred):
                continue

            base_features = list(G_part[i])

            temp_features = [
                Tj[i],
                Tj[i] - Tb_pred_part[i],
                Tj[i] / Tb_pred_part[i] if Tb_pred_part[i] > 0 else 0.0,
                np.log(Tj[i]) if Tj[i] > 0 else 0.0,
            ]

            baseline_features = [
                baseline_pred
            ]

            ref_features = [
                Tb_pred_part[i],
                VP_Tb_part[i]
            ]

            all_features = (
                base_features
                + temp_features
                + baseline_features
                + ref_features
            )

            features_list.append(all_features)
            valid_indices.append(i)

        if len(features_list) > 0:
            features_array = np.array(features_list, dtype=float)
            features_scaled = scaler_residual.transform(features_array)
            residual_pred = residual_model.predict(features_scaled)

            for idx, residual_val in zip(valid_indices, residual_pred):
                pred_df.at[idx, vcol] = (
                    baseline_pred_df.at[idx, vcol]
                    + residual_val
                )

    return pred_df


Gibbs_pred_final_train = build_final_predictions(
    train_df,
    G_train,
    Tb_pred_train,
    VP_Tb_train,
    Gibbs_pred_baseline_train
)

Gibbs_pred_final_test = build_final_predictions(
    test_df,
    G_test,
    Tb_pred_test,
    VP_Tb_test,
    Gibbs_pred_baseline_test
)


# ============================================================
# 11. 评估函数
# ============================================================
def collect_true_pred(df_part, pred_df, value_cols):
    y_true_all = []
    y_pred_all = []

    for vcol in value_cols:
        m = (
            (~df_part[vcol].isna())
            & (~pred_df[vcol].isna())
        )

        if m.any():
            y_true_all.append(df_part.loc[m, vcol].to_numpy(dtype=float))
            y_pred_all.append(pred_df.loc[m, vcol].to_numpy(dtype=float))

    if len(y_true_all) == 0:
        return np.array([]), np.array([])

    return np.concatenate(y_true_all), np.concatenate(y_pred_all)


def eval_final_regression(
    y_true,
    y_pred,
    model_name,
    split_name,
    strict_less=False
):
    """
    strict_less=False：统计 <=1%, <=5%, <=10%
    strict_less=True ：统计 <1%, <5%, <10%
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
        print(f"\n{model_name} - {split_name}: 无有效样本")

        return {
            "Model": model_name,
            "Split": split_name,
            "R2": np.nan,
            "MSE": np.nan,
            "ARD_%": np.nan,
            "within_1pct": 0,
            "within_5pct": 0,
            "within_10pct": 0
        }, relative_error

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
        within_1pct = np.sum(relative_error_valid < 1)
        within_5pct = np.sum(relative_error_valid < 5)
        within_10pct = np.sum(relative_error_valid < 10)
    else:
        within_1pct = np.sum(relative_error_valid <= 1)
        within_5pct = np.sum(relative_error_valid <= 5)
        within_10pct = np.sum(relative_error_valid <= 10)

    print(f"\n{model_name} - {split_name}")
    print(f"R2  = {r2:.6f}")
    print(f"MSE = {mse:.10f}")
    print(f"ARD = {ard:.4f}%")

    if strict_less:
        print(f"误差 < 1% 的点数: {within_1pct}")
        print(f"误差 < 5% 的点数: {within_5pct}")
        print(f"误差 < 10% 的点数: {within_10pct}")
    else:
        print(f"误差 <= 1% 的点数: {within_1pct}")
        print(f"误差 <= 5% 的点数: {within_5pct}")
        print(f"误差 <= 10% 的点数: {within_10pct}")

    return {
        "Model": model_name,
        "Split": split_name,
        "R2": r2,
        "MSE": mse,
        "ARD_%": ard,
        "within_1pct": within_1pct,
        "within_5pct": within_5pct,
        "within_10pct": within_10pct
    }, relative_error


def eval_residual_regression(y_true, y_pred, model_name, split_name):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    finite_mask = (
        np.isfinite(y_true)
        & np.isfinite(y_pred)
    )

    y_true_valid = y_true[finite_mask]
    y_pred_valid = y_pred[finite_mask]

    if len(y_true_valid) == 0:
        print(f"\n{model_name} - {split_name}: 无有效样本")

        return {
            "Model": model_name,
            "Split": split_name,
            "R2": np.nan,
            "MSE": np.nan
        }

    r2 = r2_score(
        y_true_valid,
        y_pred_valid
    )

    mse = mean_squared_error(
        y_true_valid,
        y_pred_valid
    )

    print(f"\n{model_name} - {split_name}")
    print(f"Residual R2  = {r2:.6f}")
    print(f"Residual MSE = {mse:.10f}")

    return {
        "Model": model_name,
        "Split": split_name,
        "R2": r2,
        "MSE": mse
    }


# ============================================================
# 12. baseline / final / residual 评估
# ============================================================
print("\n=== 基线模型性能 ===")

y_train_true_base, y_train_pred_base = collect_true_pred(
    train_df,
    Gibbs_pred_baseline_train,
    v_cols
)

y_test_true_base, y_test_pred_base = collect_true_pred(
    test_df,
    Gibbs_pred_baseline_test,
    v_cols
)

baseline_metrics_train, rel_err_base_train = eval_final_regression(
    y_train_true_base,
    y_train_pred_base,
    "Baseline_model",
    "train",
    strict_less=False
)

baseline_metrics_test, rel_err_base_test = eval_final_regression(
    y_test_true_base,
    y_test_pred_base,
    "Baseline_model",
    "test",
    strict_less=False
)


print("\n=== 最终模型性能（基准 + 残差修正）===")

y_train_true_final, y_train_pred_final = collect_true_pred(
    train_df,
    Gibbs_pred_final_train,
    v_cols
)

y_test_true_final, y_test_pred_final = collect_true_pred(
    test_df,
    Gibbs_pred_final_test,
    v_cols
)

final_metrics_train, rel_err_final_train = eval_final_regression(
    y_train_true_final,
    y_train_pred_final,
    "Final_model",
    "train",
    strict_less=False
)

final_metrics_test, rel_err_final_test = eval_final_regression(
    y_test_true_final,
    y_test_pred_final,
    "Final_model",
    "test",
    strict_less=False
)


print("\n=== residual GBDT 层面性能 ===")

residual_metrics_train = eval_residual_regression(
    residual_y_train,
    residual_pred_train,
    "Residual_GBDT",
    "train"
)

residual_metrics_test = eval_residual_regression(
    residual_y_test,
    residual_pred_test,
    "Residual_GBDT",
    "test"
)


# ============================================================
# 12.1 完整数据集统计：训练集 + 测试集
# ============================================================
y_all_true_base = np.concatenate([
    y_train_true_base,
    y_test_true_base
])

y_all_pred_base = np.concatenate([
    y_train_pred_base,
    y_test_pred_base
])

baseline_metrics_all, rel_err_base_all = eval_final_regression(
    y_all_true_base,
    y_all_pred_base,
    "Baseline_model",
    "all_train_plus_test",
    strict_less=True
)

y_all_true_final = np.concatenate([
    y_train_true_final,
    y_test_true_final
])

y_all_pred_final = np.concatenate([
    y_train_pred_final,
    y_test_pred_final
])

final_metrics_all, rel_err_final_all = eval_final_regression(
    y_all_true_final,
    y_all_pred_final,
    "Final_model",
    "all_train_plus_test",
    strict_less=True
)

residual_y_all = np.concatenate([
    residual_y_train,
    residual_y_test
])

residual_pred_all = np.concatenate([
    residual_pred_train,
    residual_pred_test
])

residual_metrics_all = eval_residual_regression(
    residual_y_all,
    residual_pred_all,
    "Residual_GBDT",
    "all_train_plus_test"
)

print("\nFinal_model 完整数据集 Gibbs Free Energy 预测偏差 1%，5%，10%分别为：")
print(final_metrics_all["within_1pct"])
print(final_metrics_all["within_5pct"])
print(final_metrics_all["within_10pct"])


# ============================================================
# 13. 分温度点评估：Final 模型
# ============================================================
print("\n分温度点评估（最终模型，训练集）:")

for tcol, vcol in zip(temp_cols, v_cols):
    m = (
        (~train_df[tcol].isna())
        & (~train_df[vcol].isna())
        & (~Gibbs_pred_final_train[vcol].isna())
    )

    if m.any():
        v_true = train_df.loc[m, vcol].to_numpy(dtype=float)
        v_pred = Gibbs_pred_final_train.loc[m, vcol].to_numpy(dtype=float)

        mse_temp = mean_squared_error(
            v_true,
            v_pred
        )

        r2_temp = r2_score(
            v_true,
            v_pred
        )

        print(f"  {tcol}: MSE = {mse_temp:.6f}, R2 = {r2_temp:.6f}")


print("\n分温度点评估（最终模型，测试集）:")

for tcol, vcol in zip(temp_cols, v_cols):
    m = (
        (~test_df[tcol].isna())
        & (~test_df[vcol].isna())
        & (~Gibbs_pred_final_test[vcol].isna())
    )

    if m.any():
        v_true = test_df.loc[m, vcol].to_numpy(dtype=float)
        v_pred = Gibbs_pred_final_test.loc[m, vcol].to_numpy(dtype=float)

        mse_temp = mean_squared_error(
            v_true,
            v_pred
        )

        r2_temp = r2_score(
            v_true,
            v_pred
        )

        print(f"  {tcol}: MSE = {mse_temp:.6f}, R2 = {r2_temp:.6f}")


# ============================================================
# 14. 保存结果
# ============================================================
out_path = "gibbs_free_energy_actual_vs_pred_with_residual_correction_train_test_split.xlsx"


def build_long_compare(
    df_part,
    split_name,
    Tb_pred_part,
    VP_ref_part,
    baseline_pred_df,
    final_pred_df
):
    rows = []

    for idx in range(len(df_part)):
        ID = df_part.at[idx, id_col]

        for j, (tcol, vcol) in enumerate(zip(temp_cols, v_cols), start=1):
            T = df_part.at[idx, tcol]
            Gibbs_actual = df_part.at[idx, vcol]

            Gibbs_base = (
                baseline_pred_df.at[idx, vcol]
                if pd.notna(baseline_pred_df.at[idx, vcol])
                else np.nan
            )

            Gibbs_final = (
                final_pred_df.at[idx, vcol]
                if pd.notna(final_pred_df.at[idx, vcol])
                else np.nan
            )

            err_base = (
                Gibbs_base - Gibbs_actual
                if pd.notna(Gibbs_base) and pd.notna(Gibbs_actual)
                else np.nan
            )

            err_final = (
                Gibbs_final - Gibbs_actual
                if pd.notna(Gibbs_final) and pd.notna(Gibbs_actual)
                else np.nan
            )

            residual_correction = (
                Gibbs_final - Gibbs_base
                if pd.notna(Gibbs_final) and pd.notna(Gibbs_base)
                else np.nan
            )

            rel_err_base = (
                abs((Gibbs_base - Gibbs_actual) / Gibbs_actual) * 100
                if pd.notna(Gibbs_base) and pd.notna(Gibbs_actual) and abs(Gibbs_actual) > 1e-12
                else np.nan
            )

            rel_err_final = (
                abs((Gibbs_final - Gibbs_actual) / Gibbs_actual) * 100
                if pd.notna(Gibbs_final) and pd.notna(Gibbs_actual) and abs(Gibbs_actual) > 1e-12
                else np.nan
            )

            rows.append({
                "Split": split_name,
                id_col: ID,
                "temp_index": j,
                "temp_col": tcol,
                "T": T,
                "Gibbs_Free_Energy_actual": Gibbs_actual,
                "Gibbs_Free_Energy_baseline": Gibbs_base,
                "Gibbs_Free_Energy_final": Gibbs_final,
                "error_baseline": err_base,
                "error_final": err_final,
                "relative_error_baseline_%": rel_err_base,
                "relative_error_final_%": rel_err_final,
                "residual_correction": residual_correction,
                "T_ref": Tb_pred_part[idx],
                "VP_ref": VP_ref_part[idx]
            })

    return pd.DataFrame(rows)


long_train = build_long_compare(
    train_df,
    "train",
    Tb_pred_train,
    VP_Tb_train,
    Gibbs_pred_baseline_train,
    Gibbs_pred_final_train
)

long_test = build_long_compare(
    test_df,
    "test",
    Tb_pred_test,
    VP_Tb_test,
    Gibbs_pred_baseline_test,
    Gibbs_pred_final_test
)

long_compare = pd.concat(
    [long_train, long_test],
    ignore_index=True
).sort_values(["Split", id_col, "temp_index"])

long_all = long_compare.copy()
long_all["Split"] = "all_train_plus_test"

vp_tb_out = pd.DataFrame({
    id_col: df[id_col].values,
    "VP_Tb_true": y_Tb,
    "VP_Tb_pred": VP_Tb_all
})

tb_out = pd.DataFrame({
    id_col: df[id_col].values,
    "Tb_true": Tb_raw,
    "Tb_pred": Tb_pred_all
})

summary_df = pd.DataFrame([
    baseline_metrics_train,
    baseline_metrics_test,
    baseline_metrics_all,
    final_metrics_train,
    final_metrics_test,
    final_metrics_all,
    residual_metrics_train,
    residual_metrics_test,
    residual_metrics_all
])

with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
    long_compare.to_excel(
        writer,
        sheet_name="compare_long",
        index=False
    )

    long_all.to_excel(
        writer,
        sheet_name="all_compare_long",
        index=False
    )

    summary_df.to_excel(
        writer,
        sheet_name="summary",
        index=False
    )

    vp_tb_out.to_excel(
        writer,
        sheet_name="VP_Tb_submodel",
        index=False
    )

    tb_out.to_excel(
        writer,
        sheet_name="Tb_submodel",
        index=False
    )

print(f"\n结果已保存到: {out_path}")


# ============================================================
# 15. 输出最终测试集和完整数据集指标
# ============================================================
print("\n总模型评估（基准 + 残差修正，测试集）：")
print(f"R2  = {final_metrics_test['R2']:.4f}")
print(f"MSE = {final_metrics_test['MSE']:.6f}")
print(f"ARD = {final_metrics_test['ARD_%']:.2f}%")
print(f"误差 <= 1% 的数据点数量: {final_metrics_test['within_1pct']}")
print(f"误差 <= 5% 的数据点数量: {final_metrics_test['within_5pct']}")
print(f"误差 <= 10% 的数据点数量: {final_metrics_test['within_10pct']}")

print("\n总模型评估（基准 + 残差修正，完整数据集 train + test）：")
print(f"R2  = {final_metrics_all['R2']:.4f}")
print(f"MSE = {final_metrics_all['MSE']:.6f}")
print(f"ARD = {final_metrics_all['ARD_%']:.2f}%")
print("1%，5%，10%分别为：")
print(final_metrics_all["within_1pct"])
print(final_metrics_all["within_5pct"])
print(final_metrics_all["within_10pct"])


# ============================================================
# 16. 输出模型结构记录
# ============================================================
print("\n当前 Gibbs Free Energy baseline + GBDT residual 模型结构:")
print("VP_Tb_submodel: RandomForestRegressor(random_state=42, n_jobs=-1), input = selected_25_descriptors_boiling.xlsx")
print("Tb_submodel: HuberRegressor(max_iter=10000), input = StandardScaler(PolynomialFeatures(Nk, degree=2))")
print("Baseline: Gibbs_baseline = VP_Tb_pred + (T - Tb_pred) * sum(Ak * Nk)")
print("A_solver: HuberRegressor(fit_intercept=False, max_iter=5000)")
print("Residual model: GradientBoostingRegressor(n_estimators=200, learning_rate=0.05, max_depth=5, min_samples_split=20, min_samples_leaf=10, random_state=42)")
print("Residual target: Gibbs_actual - Gibbs_baseline")
print("Residual features: Nk + T + (T-Tb) + T/Tb + ln(T) + Gibbs_baseline + Tb_pred + VP_Tb_pred")
print("Final prediction: Gibbs_final = Gibbs_baseline + residual_pred")
print("Split: material-level 8:2 split, random_state=42")
print("Final all-data statistics use strict thresholds: <1%, <5%, <10%")