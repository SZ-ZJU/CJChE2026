# import pandas as pd
# import numpy as np
#
# from sklearn.model_selection import train_test_split
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.preprocessing import PolynomialFeatures
# from sklearn.linear_model import HuberRegressor
# from sklearn.ensemble import GradientBoostingRegressor
#
#
# # ========= 1. 读取数据 =========
# file_path = "heat capacity 207.xlsx"
# sheet = "Sheet1"
#
# df = pd.read_excel(file_path, sheet_name=sheet).copy()
#
# df = df.dropna(subset=[df.columns[0]])
# df[df.columns[0]] = df[df.columns[0]].astype(int)
#
#
# # ========= 2. 列定义 =========
# material_id_col = df.columns[0]
#
# group_cols = list(df.columns[11:30])   # 19个基团列
# temp_cols = list(df.columns[30:40])    # 10个温度点
# cp_cols = list(df.columns[40:50])      # 10个 Cp 值
#
# target_column_T1 = "ASPEN Half Critical T"
#
#
# # ========= 3. 数值化 =========
# for cols in [group_cols, temp_cols, cp_cols]:
#     for c in cols:
#         df[c] = pd.to_numeric(df[c], errors="coerce")
#
# df[target_column_T1] = pd.to_numeric(df[target_column_T1], errors="coerce")
#
# # Cp_ref 使用原始代码中的第9列
# cp1_col = df.columns[9]
# df[cp1_col] = pd.to_numeric(df[cp1_col], errors="coerce")
#
#
# # ========= 4. 统一划分：按物质ID做 8:2 =========
# unique_materials = df[material_id_col].dropna().unique()
#
# train_materials, test_materials = train_test_split(
#     unique_materials,
#     test_size=0.2,
#     random_state=40
# )
#
# train_materials = set(train_materials)
# test_materials = set(test_materials)
#
# train_df = df[df[material_id_col].isin(train_materials)].copy().reset_index(drop=True)
# test_df = df[df[material_id_col].isin(test_materials)].copy().reset_index(drop=True)
#
# print("========== 统一划分（按物质ID） ==========")
# print(f"总物质数: {len(unique_materials)}")
# print(f"训练集物质数: {len(train_materials)}")
# print(f"测试集物质数: {len(test_materials)}")
# print(f"训练集行数: {len(train_df)}")
# print(f"测试集行数: {len(test_df)}")
#
#
# # ========= 5. baseline 子模型：只在训练集上训练 =========
# X_groups_train = train_df[group_cols].fillna(0).astype(float)
# X_groups_test = test_df[group_cols].fillna(0).astype(float)
#
#
# # ========= 5.1 T_ref = T1 子模型 =========
# valid_mask_train = ~train_df[target_column_T1].isna()
#
# poly = PolynomialFeatures(degree=2, include_bias=False)
#
# X_poly_train = poly.fit_transform(
#     X_groups_train.loc[valid_mask_train]
# )
#
# y_T1_train = train_df.loc[
#     valid_mask_train,
#     target_column_T1
# ].to_numpy(dtype=float)
#
# T1_model = GradientBoostingRegressor(
#     n_estimators=300,
#     learning_rate=0.05,
#     max_depth=4,
#     random_state=0
# )
#
# T1_model.fit(X_poly_train, y_T1_train)
#
# # 预测 train / test 的 T_ref
# T_ref_train = T1_model.predict(poly.transform(X_groups_train))
# T_ref_test = T1_model.predict(poly.transform(X_groups_test))
#
#
# # ========= 5.2 C_pref = Cp1 子模型 =========
# valid_cp1_mask_train = ~train_df[cp1_col].isna()
#
# Cp1_model = HuberRegressor(max_iter=9000)
#
# Cp1_model.fit(
#     X_groups_train.loc[valid_cp1_mask_train],
#     train_df.loc[valid_cp1_mask_train, cp1_col].to_numpy(dtype=float)
# )
#
# C_pref_train = Cp1_model.predict(X_groups_train)
# C_pref_test = Cp1_model.predict(X_groups_test)
#
#
# # ========= 6. A_k baseline 主体：只在训练集上训练 =========
# G_train = X_groups_train.to_numpy(dtype=float)
# G_test = X_groups_test.to_numpy(dtype=float)
#
# X_A_train, y_A_train = [], []
#
# for tcol, cpcol in zip(temp_cols, cp_cols):
#     Tj = train_df[tcol].to_numpy(dtype=float)
#     CPj = train_df[cpcol].to_numpy(dtype=float)
#
#     msk = (~np.isnan(Tj)) & (~np.isnan(CPj))
#
#     if msk.sum() == 0:
#         continue
#
#     Xj = ((Tj - T_ref_train)[:, None] * G_train)[msk]
#     yj = (CPj - C_pref_train)[msk]
#
#     X_A_train.append(Xj)
#     y_A_train.append(yj)
#
# X_A_train = np.vstack(X_A_train)
# y_A_train = np.concatenate(y_A_train)
#
# A_solver = HuberRegressor(
#     fit_intercept=False,
#     max_iter=5000
# )
#
# A_solver.fit(X_A_train, y_A_train)
#
# A_vec = A_solver.coef_
#
#
# # ========= 7. 生成 baseline 长表结果 =========
# def build_baseline_long(sub_df, G, T_ref_pred, C_pref_pred, dataset_name):
#     rows = []
#
#     for i in range(len(sub_df)):
#         material_id = sub_df.at[i, material_id_col]
#
#         for tcol, cpcol in zip(temp_cols, cp_cols):
#             T = sub_df.at[i, tcol]
#             Cp_actual = sub_df.at[i, cpcol]
#
#             if pd.isna(T) or pd.isna(Cp_actual):
#                 continue
#
#             deltaT = T - T_ref_pred[i]
#             Cp_baseline = C_pref_pred[i] + deltaT * np.dot(G[i], A_vec)
#
#             rows.append({
#                 "Dataset": dataset_name,
#                 "row_idx_local": i,
#                 "Material_ID": material_id,
#                 "temp_col": tcol,
#                 "cp_col": cpcol,
#                 "T": T,
#                 "Cp_actual": Cp_actual,
#                 "Cp_baseline": Cp_baseline,
#                 "T_ref": T_ref_pred[i],
#                 "Cp_ref": C_pref_pred[i]
#             })
#
#     return pd.DataFrame(rows)
#
#
# train_long = build_baseline_long(
#     train_df,
#     G_train,
#     T_ref_train,
#     C_pref_train,
#     "train"
# )
#
# test_long = build_baseline_long(
#     test_df,
#     G_test,
#     T_ref_test,
#     C_pref_test,
#     "test"
# )
#
# print(f"baseline训练样本点数: {len(train_long)}")
# print(f"baseline测试样本点数: {len(test_long)}")
#
#
# # ========= 8. 构造 final residual model 的训练 / 测试特征 =========
# def add_residual_features(long_df, G):
#     feature_list = []
#     target_list = []
#
#     for _, row in long_df.iterrows():
#         i = int(row["row_idx_local"])
#
#         T = float(row["T"])
#         Cp_actual = float(row["Cp_actual"])
#         Cp_baseline = float(row["Cp_baseline"])
#
#         base_features = list(G[i])
#
#         # 当前版本保持和你原代码一致：
#         # final residual 特征 = 19维基团 + 温度T + baseline预测值
#         temp_features = [T]
#         baseline_feature = [Cp_baseline]
#
#         x = base_features + temp_features + baseline_feature
#         y = Cp_actual - Cp_baseline
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
# X_res_train, y_res_train = add_residual_features(train_long, G_train)
# X_res_test, y_res_test = add_residual_features(test_long, G_test)
#
# print(f"residual训练集形状: {X_res_train.shape}")
# print(f"residual测试集形状: {X_res_test.shape}")
#
#
# # ========= 9. final residual model：GBDT，只在训练集上训练 =========
# # GBDT 是树模型，不需要 StandardScaler，也不需要 y 标准化
# final_model = GradientBoostingRegressor(
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
# final_model.fit(X_res_train, y_res_train)
#
#
# # ========= 10. residual 预测 =========
# train_res_pred = final_model.predict(X_res_train)
# test_res_pred = final_model.predict(X_res_test)
#
#
# # ========= 11. 得到最终预测 Cp_final =========
# train_long["Residual_true"] = y_res_train
# train_long["Residual_pred"] = train_res_pred
# train_long["Cp_final"] = train_long["Cp_baseline"] + train_long["Residual_pred"]
#
# test_long["Residual_true"] = y_res_test
# test_long["Residual_pred"] = test_res_pred
# test_long["Cp_final"] = test_long["Cp_baseline"] + test_long["Residual_pred"]
#
#
# # ========= 12. 评估函数 =========
# def evaluate_cp(y_true, y_pred, name="dataset"):
#     y_true = np.asarray(y_true, dtype=float)
#     y_pred = np.asarray(y_pred, dtype=float)
#
#     mse = mean_squared_error(y_true, y_pred)
#     r2 = r2_score(y_true, y_pred)
#
#     nonzero_mask = np.abs(y_true) > 1e-12
#     relative_error = np.full_like(y_true, np.nan, dtype=float)
#
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
#     return r2, mse, ard, within_1pct, within_5pct, within_10pct, relative_error
#
#
# def evaluate_residual(y_true, y_pred, name="residual model"):
#     mse = mean_squared_error(y_true, y_pred)
#     r2 = r2_score(y_true, y_pred)
#
#     print(f"\n{name}")
#     print(f"Residual R2  = {r2:.6f}")
#     print(f"Residual MSE = {mse:.10f}")
#
#     return r2, mse
#
#
# # ========= 13. residual 层面评估 =========
# residual_train_r2, residual_train_mse = evaluate_residual(
#     y_res_train,
#     train_res_pred,
#     "final residual GBDT - 训练集"
# )
#
# residual_test_r2, residual_test_mse = evaluate_residual(
#     y_res_test,
#     test_res_pred,
#     "final residual GBDT - 测试集"
# )
#
#
# # ========= 14. baseline 与 final 在同一划分下评估 =========
# baseline_train_metrics = evaluate_cp(
#     train_long["Cp_actual"].to_numpy(),
#     train_long["Cp_baseline"].to_numpy(),
#     "baseline - 训练集"
# )
# train_long["Baseline_Relative_Error_%"] = baseline_train_metrics[-1]
#
# baseline_test_metrics = evaluate_cp(
#     test_long["Cp_actual"].to_numpy(),
#     test_long["Cp_baseline"].to_numpy(),
#     "baseline - 测试集"
# )
# test_long["Baseline_Relative_Error_%"] = baseline_test_metrics[-1]
#
# final_train_metrics = evaluate_cp(
#     train_long["Cp_actual"].to_numpy(),
#     train_long["Cp_final"].to_numpy(),
#     "final model GBDT residual - 训练集"
# )
# train_long["Final_Relative_Error_%"] = final_train_metrics[-1]
#
# final_test_metrics = evaluate_cp(
#     test_long["Cp_actual"].to_numpy(),
#     test_long["Cp_final"].to_numpy(),
#     "final model GBDT residual - 测试集"
# )
# test_long["Final_Relative_Error_%"] = final_test_metrics[-1]
#
#
# # ========= 15. 保存结果 =========
# train_out = train_long.copy()
# test_out = test_long.copy()
#
# train_out["Baseline_Error"] = train_out["Cp_baseline"] - train_out["Cp_actual"]
# train_out["Final_Error"] = train_out["Cp_final"] - train_out["Cp_actual"]
#
# test_out["Baseline_Error"] = test_out["Cp_baseline"] - test_out["Cp_actual"]
# test_out["Final_Error"] = test_out["Cp_final"] - test_out["Cp_actual"]
#
# summary_df = pd.DataFrame([
#     [
#         "baseline",
#         "train",
#         baseline_train_metrics[0],
#         baseline_train_metrics[1],
#         baseline_train_metrics[2],
#         baseline_train_metrics[3],
#         baseline_train_metrics[4],
#         baseline_train_metrics[5],
#         np.nan,
#         np.nan
#     ],
#     [
#         "baseline",
#         "test",
#         baseline_test_metrics[0],
#         baseline_test_metrics[1],
#         baseline_test_metrics[2],
#         baseline_test_metrics[3],
#         baseline_test_metrics[4],
#         baseline_test_metrics[5],
#         np.nan,
#         np.nan
#     ],
#     [
#         "final_GBDT_residual",
#         "train",
#         final_train_metrics[0],
#         final_train_metrics[1],
#         final_train_metrics[2],
#         final_train_metrics[3],
#         final_train_metrics[4],
#         final_train_metrics[5],
#         residual_train_r2,
#         residual_train_mse
#     ],
#     [
#         "final_GBDT_residual",
#         "test",
#         final_test_metrics[0],
#         final_test_metrics[1],
#         final_test_metrics[2],
#         final_test_metrics[3],
#         final_test_metrics[4],
#         final_test_metrics[5],
#         residual_test_r2,
#         residual_test_mse
#     ],
# ], columns=[
#     "Model",
#     "Dataset",
#     "R2",
#     "MSE",
#     "ARD_%",
#     "within_1pct",
#     "within_5pct",
#     "within_10pct",
#     "Residual_R2",
#     "Residual_MSE"
# ])
#
# out_path = "Cp_baseline_and_final_same_split_GBDT_residual.xlsx"
#
# with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
#     train_out.to_excel(writer, sheet_name="train_results", index=False)
#     test_out.to_excel(writer, sheet_name="test_results", index=False)
#     summary_df.to_excel(writer, sheet_name="summary", index=False)
#
# print(f"\n已保存结果到: {out_path}")
#
# print("\n当前 final residual GBDT 模型参数:")
# print(final_model)


import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import HuberRegressor
from sklearn.ensemble import GradientBoostingRegressor


# ========= 1. 读取数据 =========
file_path = "heat capacity 207.xlsx"
sheet = "Sheet1"

df = pd.read_excel(file_path, sheet_name=sheet).copy()

df = df.dropna(subset=[df.columns[0]])
df[df.columns[0]] = df[df.columns[0]].astype(int)


# ========= 2. 列定义 =========
material_id_col = df.columns[0]

group_cols = list(df.columns[11:30])   # 19个基团列
temp_cols = list(df.columns[30:40])    # 10个温度点
cp_cols = list(df.columns[40:50])      # 10个 Cp 值

target_column_T1 = "ASPEN Half Critical T"


# ========= 3. 数值化 =========
for cols in [group_cols, temp_cols, cp_cols]:
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

df[target_column_T1] = pd.to_numeric(df[target_column_T1], errors="coerce")

# Cp_ref 使用原始代码中的第9列
cp1_col = df.columns[9]
df[cp1_col] = pd.to_numeric(df[cp1_col], errors="coerce")


# ========= 4. 统一划分：按物质ID做 8:2 =========
unique_materials = df[material_id_col].dropna().unique()

train_materials, test_materials = train_test_split(
    unique_materials,
    test_size=0.2,
    random_state=40
)

train_materials = set(train_materials)
test_materials = set(test_materials)

train_df = df[df[material_id_col].isin(train_materials)].copy().reset_index(drop=True)
test_df = df[df[material_id_col].isin(test_materials)].copy().reset_index(drop=True)

print("========== 统一划分（按物质ID） ==========")
print(f"总物质数: {len(unique_materials)}")
print(f"训练集物质数: {len(train_materials)}")
print(f"测试集物质数: {len(test_materials)}")
print(f"训练集行数: {len(train_df)}")
print(f"测试集行数: {len(test_df)}")


# ========= 5. baseline 子模型：只在训练集上训练 =========
X_groups_train = train_df[group_cols].fillna(0).astype(float)
X_groups_test = test_df[group_cols].fillna(0).astype(float)


# ========= 5.1 T_ref = T1 子模型 =========
valid_mask_train = ~train_df[target_column_T1].isna()

poly = PolynomialFeatures(degree=2, include_bias=False)

X_poly_train = poly.fit_transform(
    X_groups_train.loc[valid_mask_train]
)

y_T1_train = train_df.loc[
    valid_mask_train,
    target_column_T1
].to_numpy(dtype=float)

T1_model = GradientBoostingRegressor(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=4,
    random_state=0
)

T1_model.fit(X_poly_train, y_T1_train)

# 预测 train / test 的 T_ref
T_ref_train = T1_model.predict(poly.transform(X_groups_train))
T_ref_test = T1_model.predict(poly.transform(X_groups_test))


# ========= 5.2 C_pref = Cp1 子模型 =========
valid_cp1_mask_train = ~train_df[cp1_col].isna()

Cp1_model = HuberRegressor(max_iter=9000)

Cp1_model.fit(
    X_groups_train.loc[valid_cp1_mask_train],
    train_df.loc[valid_cp1_mask_train, cp1_col].to_numpy(dtype=float)
)

C_pref_train = Cp1_model.predict(X_groups_train)
C_pref_test = Cp1_model.predict(X_groups_test)


# ========= 6. A_k baseline 主体：只在训练集上训练 =========
G_train = X_groups_train.to_numpy(dtype=float)
G_test = X_groups_test.to_numpy(dtype=float)

X_A_train, y_A_train = [], []

for tcol, cpcol in zip(temp_cols, cp_cols):
    Tj = train_df[tcol].to_numpy(dtype=float)
    CPj = train_df[cpcol].to_numpy(dtype=float)

    msk = (~np.isnan(Tj)) & (~np.isnan(CPj))

    if msk.sum() == 0:
        continue

    Xj = ((Tj - T_ref_train)[:, None] * G_train)[msk]
    yj = (CPj - C_pref_train)[msk]

    X_A_train.append(Xj)
    y_A_train.append(yj)

X_A_train = np.vstack(X_A_train)
y_A_train = np.concatenate(y_A_train)

A_solver = HuberRegressor(
    fit_intercept=False,
    max_iter=5000
)

A_solver.fit(X_A_train, y_A_train)

A_vec = A_solver.coef_


# ========= 7. 生成 baseline 长表结果 =========
def build_baseline_long(sub_df, G, T_ref_pred, C_pref_pred, dataset_name):
    rows = []

    for i in range(len(sub_df)):
        material_id = sub_df.at[i, material_id_col]

        for tcol, cpcol in zip(temp_cols, cp_cols):
            T = sub_df.at[i, tcol]
            Cp_actual = sub_df.at[i, cpcol]

            if pd.isna(T) or pd.isna(Cp_actual):
                continue

            deltaT = T - T_ref_pred[i]
            Cp_baseline = C_pref_pred[i] + deltaT * np.dot(G[i], A_vec)

            rows.append({
                "Dataset": dataset_name,
                "row_idx_local": i,
                "Material_ID": material_id,
                "temp_col": tcol,
                "cp_col": cpcol,
                "T": T,
                "Cp_actual": Cp_actual,
                "Cp_baseline": Cp_baseline,
                "T_ref": T_ref_pred[i],
                "Cp_ref": C_pref_pred[i]
            })

    return pd.DataFrame(rows)


train_long = build_baseline_long(
    train_df,
    G_train,
    T_ref_train,
    C_pref_train,
    "train"
)

test_long = build_baseline_long(
    test_df,
    G_test,
    T_ref_test,
    C_pref_test,
    "test"
)

print(f"baseline训练样本点数: {len(train_long)}")
print(f"baseline测试样本点数: {len(test_long)}")


# ========= 8. 构造 final residual model 的训练 / 测试特征 =========
def add_residual_features(long_df, G):
    feature_list = []
    target_list = []

    for _, row in long_df.iterrows():
        i = int(row["row_idx_local"])

        T = float(row["T"])
        Cp_actual = float(row["Cp_actual"])
        Cp_baseline = float(row["Cp_baseline"])

        base_features = list(G[i])

        # final residual 特征 = 19维基团 + 温度T + baseline预测值
        temp_features = [T]
        baseline_feature = [Cp_baseline]

        x = base_features + temp_features + baseline_feature
        y = Cp_actual - Cp_baseline

        feature_list.append(x)
        target_list.append(y)

    X_res = np.array(feature_list, dtype=float)
    y_res = np.array(target_list, dtype=float)

    return X_res, y_res


X_res_train, y_res_train = add_residual_features(train_long, G_train)
X_res_test, y_res_test = add_residual_features(test_long, G_test)

print(f"residual训练集形状: {X_res_train.shape}")
print(f"residual测试集形状: {X_res_test.shape}")


# ========= 9. final residual model：GBDT，只在训练集上训练 =========
final_model = GradientBoostingRegressor(
    n_estimators=500,
    learning_rate=0.03,
    max_depth=3,
    subsample=0.9,
    min_samples_split=2,
    min_samples_leaf=1,
    loss="squared_error",
    random_state=42
)

final_model.fit(X_res_train, y_res_train)


# ========= 10. residual 预测 =========
train_res_pred = final_model.predict(X_res_train)
test_res_pred = final_model.predict(X_res_test)


# ========= 11. 得到最终预测 Cp_final =========
train_long["Residual_true"] = y_res_train
train_long["Residual_pred"] = train_res_pred
train_long["Cp_final"] = train_long["Cp_baseline"] + train_long["Residual_pred"]

test_long["Residual_true"] = y_res_test
test_long["Residual_pred"] = test_res_pred
test_long["Cp_final"] = test_long["Cp_baseline"] + test_long["Residual_pred"]


# ========= 12. 评估函数 =========
def evaluate_cp(y_true, y_pred, name="dataset", strict_less=False):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mse = mean_squared_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)

    nonzero_mask = np.abs(y_true) > 1e-12
    relative_error = np.full_like(y_true, np.nan, dtype=float)

    if np.any(nonzero_mask):
        relative_error[nonzero_mask] = np.abs(
            (y_true[nonzero_mask] - y_pred[nonzero_mask])
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

    return r2, mse, ard, within_1pct, within_5pct, within_10pct, relative_error


def evaluate_residual(y_true, y_pred, name="residual model"):
    mse = mean_squared_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)

    print(f"\n{name}")
    print(f"Residual R2  = {r2:.6f}")
    print(f"Residual MSE = {mse:.10f}")

    return r2, mse


# ========= 13. residual 层面评估 =========
residual_train_r2, residual_train_mse = evaluate_residual(
    y_res_train,
    train_res_pred,
    "final residual GBDT - 训练集"
)

residual_test_r2, residual_test_mse = evaluate_residual(
    y_res_test,
    test_res_pred,
    "final residual GBDT - 测试集"
)


# ========= 14. baseline 与 final 在同一划分下评估 =========
baseline_train_metrics = evaluate_cp(
    train_long["Cp_actual"].to_numpy(),
    train_long["Cp_baseline"].to_numpy(),
    "baseline - 训练集"
)
train_long["Baseline_Relative_Error_%"] = baseline_train_metrics[-1]

baseline_test_metrics = evaluate_cp(
    test_long["Cp_actual"].to_numpy(),
    test_long["Cp_baseline"].to_numpy(),
    "baseline - 测试集"
)
test_long["Baseline_Relative_Error_%"] = baseline_test_metrics[-1]

final_train_metrics = evaluate_cp(
    train_long["Cp_actual"].to_numpy(),
    train_long["Cp_final"].to_numpy(),
    "final model GBDT residual - 训练集"
)
train_long["Final_Relative_Error_%"] = final_train_metrics[-1]

final_test_metrics = evaluate_cp(
    test_long["Cp_actual"].to_numpy(),
    test_long["Cp_final"].to_numpy(),
    "final model GBDT residual - 测试集"
)
test_long["Final_Relative_Error_%"] = final_test_metrics[-1]


# ========= 14.1 baseline 与 final 的完整数据集统计：训练集 + 测试集 =========
baseline_all_true = np.concatenate([
    train_long["Cp_actual"].to_numpy(dtype=float),
    test_long["Cp_actual"].to_numpy(dtype=float)
])

baseline_all_pred = np.concatenate([
    train_long["Cp_baseline"].to_numpy(dtype=float),
    test_long["Cp_baseline"].to_numpy(dtype=float)
])

baseline_all_metrics = evaluate_cp(
    baseline_all_true,
    baseline_all_pred,
    "baseline - 完整数据集 train + test",
    strict_less=True
)

final_all_true = np.concatenate([
    train_long["Cp_actual"].to_numpy(dtype=float),
    test_long["Cp_actual"].to_numpy(dtype=float)
])

final_all_pred = np.concatenate([
    train_long["Cp_final"].to_numpy(dtype=float),
    test_long["Cp_final"].to_numpy(dtype=float)
])

final_all_metrics = evaluate_cp(
    final_all_true,
    final_all_pred,
    "final model GBDT residual - 完整数据集 train + test",
    strict_less=True
)

print("\nfinal model GBDT residual 完整数据集 1%，5%，10%分别为：")
print(final_all_metrics[3])
print(final_all_metrics[4])
print(final_all_metrics[5])


# ========= 15. 保存结果 =========
train_out = train_long.copy()
test_out = test_long.copy()

train_out["Baseline_Error"] = train_out["Cp_baseline"] - train_out["Cp_actual"]
train_out["Final_Error"] = train_out["Cp_final"] - train_out["Cp_actual"]

test_out["Baseline_Error"] = test_out["Cp_baseline"] - test_out["Cp_actual"]
test_out["Final_Error"] = test_out["Cp_final"] - test_out["Cp_actual"]

all_out = pd.concat([train_out, test_out], axis=0, ignore_index=True)

summary_df = pd.DataFrame([
    [
        "baseline",
        "train",
        baseline_train_metrics[0],
        baseline_train_metrics[1],
        baseline_train_metrics[2],
        baseline_train_metrics[3],
        baseline_train_metrics[4],
        baseline_train_metrics[5],
        np.nan,
        np.nan
    ],
    [
        "baseline",
        "test",
        baseline_test_metrics[0],
        baseline_test_metrics[1],
        baseline_test_metrics[2],
        baseline_test_metrics[3],
        baseline_test_metrics[4],
        baseline_test_metrics[5],
        np.nan,
        np.nan
    ],
    [
        "baseline",
        "all",
        baseline_all_metrics[0],
        baseline_all_metrics[1],
        baseline_all_metrics[2],
        baseline_all_metrics[3],
        baseline_all_metrics[4],
        baseline_all_metrics[5],
        np.nan,
        np.nan
    ],
    [
        "final_GBDT_residual",
        "train",
        final_train_metrics[0],
        final_train_metrics[1],
        final_train_metrics[2],
        final_train_metrics[3],
        final_train_metrics[4],
        final_train_metrics[5],
        residual_train_r2,
        residual_train_mse
    ],
    [
        "final_GBDT_residual",
        "test",
        final_test_metrics[0],
        final_test_metrics[1],
        final_test_metrics[2],
        final_test_metrics[3],
        final_test_metrics[4],
        final_test_metrics[5],
        residual_test_r2,
        residual_test_mse
    ],
    [
        "final_GBDT_residual",
        "all",
        final_all_metrics[0],
        final_all_metrics[1],
        final_all_metrics[2],
        final_all_metrics[3],
        final_all_metrics[4],
        final_all_metrics[5],
        np.nan,
        np.nan
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

out_path = "Cp_baseline_and_final_same_split_GBDT_residual.xlsx"

with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
    train_out.to_excel(writer, sheet_name="train_results", index=False)
    test_out.to_excel(writer, sheet_name="test_results", index=False)
    all_out.to_excel(writer, sheet_name="all_results", index=False)
    summary_df.to_excel(writer, sheet_name="summary", index=False)

print(f"\n已保存结果到: {out_path}")

print("\n当前 T1_model 参数:")
print(T1_model)

print("\n当前 Cp1_model 参数:")
print(Cp1_model)

print("\n当前 A_solver 参数:")
print(A_solver)

print("\n当前 final residual GBDT 模型参数:")
print(final_model)