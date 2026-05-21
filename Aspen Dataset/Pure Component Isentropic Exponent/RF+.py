# import pandas as pd
# import numpy as np
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split
# from sklearn.linear_model import HuberRegressor
# from sklearn.preprocessing import PolynomialFeatures
#
# # ==== 1. 读取数据 ====
# df = pd.read_excel("pure component isentropic exponent 207.xlsx", sheet_name="Sheet1")
#
# # ==== 2. 定义列 ====
# group_cols = df.columns[12:31]   # 基团列
# temp_cols = df.columns[31:41]    # 温度列
# v_cols = df.columns[41:51]       # 等熵指数列
#
# # ==== 3. 准备 slope 所需模型输入（子模型，全量训练）====
# df_298 = pd.read_excel("selected_25_descriptors_normal.xlsx")
# X_298 = df_298.drop(columns=["ASPEN isentropic exponent at normal Temperature(bar)"])
# rf_298 = RandomForestRegressor(random_state=42).fit(X_298, df_298["ASPEN isentropic exponent at normal Temperature(bar)"])
# HVap_298_all = rf_298.predict(X_298)
#
# df_Tb = pd.read_excel("selected_25_descriptors_boiling.xlsx")
# X_Tb = df_Tb.drop(columns=["ASPEN isentropic exponent at boiling Temperature(bar)"])
# rf_Tb = RandomForestRegressor(random_state=42).fit(X_Tb, df_Tb["ASPEN isentropic exponent at boiling Temperature(bar)"])
# HVap_Tb_all = rf_Tb.predict(X_Tb)
#
# # ==== 4. Tb 子模型预测（全量）====
# Nk_all = df.iloc[:, 12:31].apply(pd.to_numeric, errors='coerce')
# Tb_raw = df.iloc[:, 5].values
# Tb0 = 222.543
# poly = PolynomialFeatures(degree=2, include_bias=False)
# Nk_poly = poly.fit_transform(Nk_all)
#
# mask_tb = ~np.isnan(Tb_raw)
# model_Tb = HuberRegressor(max_iter=10000).fit(Nk_poly[mask_tb], np.exp(Tb_raw[mask_tb] / Tb0))
# Tb_pred_all = Tb0 * np.log(np.clip(model_Tb.predict(Nk_poly), 1e-6, None))
#
# # ==== 5. 计算 slope 并加入主 DataFrame ====
# T_ref = 298.15
# slope_values = (HVap_Tb_all - HVap_298_all) / (Tb_pred_all - T_ref)
# df["slope"] = slope_values
#
# # ==== 6. 构建全量点级数据集（保留物质ID）====
# X_total, y_total, material_ids, temperatures = [], [], [], []
#
# for i, row in df.iterrows():
#     material_id = row.iloc[0]                     # 物质ID（第一列）
#     Nk = row[group_cols].values.astype(float)
#     temps = row[temp_cols].values.astype(float)
#     vals = row[v_cols].values.astype(float)
#     slope = row["slope"]
#
#     for T, val in zip(temps, vals):
#         if np.isnan(T) or np.isnan(val) or np.isnan(slope):
#             continue
#         features = np.concatenate([Nk, [T], [slope]])
#         X_total.append(features)
#         y_total.append(val)
#         material_ids.append(material_id)
#         temperatures.append(T)
#
# X_total = np.array(X_total)
# y_total = np.array(y_total)
# material_ids = np.array(material_ids)
# temperatures = np.array(temperatures)
#
# # ==== 7. 按物质划分训练集/测试集（8:2）====
# unique_materials = np.unique(material_ids)
# train_materials, test_materials = train_test_split(
#     unique_materials, test_size=0.2, random_state=40
# )
#
# train_mask = np.isin(material_ids, train_materials)
# test_mask  = np.isin(material_ids, test_materials)
#
# X_train, y_train = X_total[train_mask], y_total[train_mask]
# X_test,  y_test  = X_total[test_mask],  y_total[test_mask]
#
# material_ids_train = material_ids[train_mask]
# temperatures_train = temperatures[train_mask]
# material_ids_test  = material_ids[test_mask]
# temperatures_test  = temperatures[test_mask]
#
# print("========== 按物质划分 ==========")
# print(f"总物质数: {len(unique_materials)}")
# print(f"训练集物质数: {len(train_materials)}")
# print(f"测试集物质数: {len(test_materials)}")
# print(f"训练集样本点数: {X_train.shape[0]}")
# print(f"测试集样本点数: {X_test.shape[0]}")
#
# # ==== 8. 训练最终随机森林模型（仅用训练集）====
# model = RandomForestRegressor(n_estimators=100, random_state=42)
# model.fit(X_train, y_train)
#
# # ==== 9. 定义评估函数 ====
# def evaluate(y_true, y_pred, name="数据集"):
#     r2 = r2_score(y_true, y_pred)
#     mse = mean_squared_error(y_true, y_pred)
#     rel_err = np.abs((y_pred - y_true) / y_true) * 100
#     ard = np.mean(rel_err)
#     within_1pct = np.sum(rel_err <= 1)
#     within_5pct = np.sum(rel_err <= 5)
#     within_10pct = np.sum(rel_err <= 10)
#
#     print(f"\n📊 {name} 结果：")
#     print(f"R²  = {r2:.4f}")
#     print(f"MSE = {mse:.4f}")
#     print(f"ARD = {ard:.2f}%")
#     print(f"相对误差 ≤ 1% 的点数: {within_1pct}")
#     print(f"相对误差 ≤ 5% 的点数: {within_5pct}")
#     print(f"相对误差 ≤ 10% 的点数: {within_10pct}")
#     return rel_err
#
# # ==== 10. 训练集评估 ====
# y_train_pred = model.predict(X_train)
# rel_err_train = evaluate(y_train, y_train_pred, "训练集")
#
# # ==== 11. 测试集评估 ====
# y_test_pred = model.predict(X_test)
# rel_err_test = evaluate(y_test, y_test_pred, "测试集")
#
# # ==== 12. 保存预测结果 ====
# train_results = pd.DataFrame({
#     "Material_ID": material_ids_train,
#     "Temperature (K)": temperatures_train,
#     "Measured": y_train,
#     "Predicted": y_train_pred,
#     "Absolute Error": np.abs(y_train - y_train_pred),
#     "Relative Error (%)": rel_err_train
# })
#
# test_results = pd.DataFrame({
#     "Material_ID": material_ids_test,
#     "Temperature (K)": temperatures_test,
#     "Measured": y_test,
#     "Predicted": y_test_pred,
#     "Absolute Error": np.abs(y_test - y_test_pred),
#     "Relative Error (%)": rel_err_test
# })
#
# # 汇总指标表
# summary = pd.DataFrame([
#     {"Set": "Train", "R2": r2_score(y_train, y_train_pred),
#      "MSE": mean_squared_error(y_train, y_train_pred),
#      "ARD_%": np.mean(np.abs((y_train_pred - y_train)/y_train)*100)},
#     {"Set": "Test", "R2": r2_score(y_test, y_test_pred),
#      "MSE": mean_squared_error(y_test, y_test_pred),
#      "ARD_%": np.mean(np.abs((y_test_pred - y_test)/y_test)*100)}
# ])
#
# output_file = "iex预测结果_加slope特征_RF_train_test_split.xlsx"
# with pd.ExcelWriter(output_file, engine="xlsxwriter") as writer:
#     train_results.to_excel(writer, sheet_name="Train_Predictions", index=False)
#     test_results.to_excel(writer, sheet_name="Test_Predictions", index=False)
#     summary.to_excel(writer, sheet_name="Summary", index=False)
#
# print(f"\n✅ 已保存预测结果为: {output_file}")


import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.linear_model import HuberRegressor
from sklearn.preprocessing import PolynomialFeatures


# ============================================================
# 1. 读取数据
# ============================================================
file_path = "pure component isentropic exponent 207.xlsx"
df = pd.read_excel(file_path, sheet_name="Sheet1")


# ============================================================
# 2. 定义列索引
# ============================================================
material_id_col = df.columns[0]

group_cols = df.columns[12:31]   # 19个基团列
temp_cols = df.columns[31:41]    # 10个温度列
v_cols = df.columns[41:51]       # 10个等熵指数列


# ============================================================
# 3. 数值化主数据
# ============================================================
for col in list(group_cols) + list(temp_cols) + list(v_cols):
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=[material_id_col]).copy().reset_index(drop=True)


# ============================================================
# 4. 准备 slope 所需子模型输入
#    子模型使用全量有效数据训练
# ============================================================
df_298 = pd.read_excel("selected_25_descriptors_normal.xlsx").copy()

target_298 = "ASPEN isentropic exponent at normal Temperature(bar)"

X_298 = df_298.drop(columns=[target_298], errors="ignore").copy()
X_298 = X_298.apply(pd.to_numeric, errors="coerce")
X_298 = X_298.replace([np.inf, -np.inf], np.nan)

y_298 = pd.to_numeric(df_298[target_298], errors="coerce").values

valid_298_mask = (
    X_298.notna().all(axis=1)
    & np.isfinite(y_298)
)

rf_298 = RandomForestRegressor(
    n_estimators=100,
    random_state=42,
    n_jobs=-1
)

rf_298.fit(
    X_298.loc[valid_298_mask],
    y_298[valid_298_mask]
)

X_298_predict = X_298.fillna(
    X_298.loc[valid_298_mask].median(numeric_only=True)
)

isentropic_298_pred_all = rf_298.predict(X_298_predict)


# ============================================================
# 5. 沸点等熵指数子模型
# ============================================================
df_Tb = pd.read_excel("selected_25_descriptors_boiling.xlsx").copy()

target_Tb = "ASPEN isentropic exponent at boiling Temperature(bar)"

X_Tb = df_Tb.drop(columns=[target_Tb], errors="ignore").copy()
X_Tb = X_Tb.apply(pd.to_numeric, errors="coerce")
X_Tb = X_Tb.replace([np.inf, -np.inf], np.nan)

y_Tb = pd.to_numeric(df_Tb[target_Tb], errors="coerce").values

valid_Tb_mask = (
    X_Tb.notna().all(axis=1)
    & np.isfinite(y_Tb)
)

rf_Tb = RandomForestRegressor(
    n_estimators=100,
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

isentropic_Tb_pred_all = rf_Tb.predict(X_Tb_predict)


# ============================================================
# 6. 长度一致性检查
# ============================================================
if len(isentropic_298_pred_all) != len(df):
    raise ValueError(
        f"selected_25_descriptors_normal.xlsx 行数 = {len(isentropic_298_pred_all)}，"
        f"主表物质数 = {len(df)}，二者不一致。"
    )

if len(isentropic_Tb_pred_all) != len(df):
    raise ValueError(
        f"selected_25_descriptors_boiling.xlsx 行数 = {len(isentropic_Tb_pred_all)}，"
        f"主表物质数 = {len(df)}，二者不一致。"
    )


# ============================================================
# 7. Tb 子模型预测
# ============================================================
Nk_all = df[group_cols].apply(pd.to_numeric, errors="coerce")
Tb_raw = pd.to_numeric(df.iloc[:, 5], errors="coerce").values

Tb0 = 222.543

poly = PolynomialFeatures(
    degree=2,
    include_bias=False
)

Nk_poly = poly.fit_transform(Nk_all.fillna(0))

mask_tb = (
    np.isfinite(Tb_raw)
    & np.isfinite(Nk_poly).all(axis=1)
)

model_Tb = HuberRegressor(
    max_iter=10000
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


# ============================================================
# 8. 计算 slope
# ============================================================
T_ref = 298.15

denom = Tb_pred_all - T_ref

slope_values = np.full(len(df), np.nan, dtype=float)

valid_slope_mask = (
    np.isfinite(isentropic_Tb_pred_all)
    & np.isfinite(isentropic_298_pred_all)
    & np.isfinite(Tb_pred_all)
    & (np.abs(denom) > 1e-12)
)

slope_values[valid_slope_mask] = (
    isentropic_Tb_pred_all[valid_slope_mask]
    - isentropic_298_pred_all[valid_slope_mask]
) / denom[valid_slope_mask]

df["slope"] = slope_values
df["isentropic_298_pred"] = isentropic_298_pred_all
df["isentropic_Tb_pred"] = isentropic_Tb_pred_all
df["Tb_pred"] = Tb_pred_all


# ============================================================
# 9. 子模型诊断评价
# ============================================================
def evaluate_submodel(y_true, y_pred, model_name="submodel"):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    finite_mask = (
        np.isfinite(y_true)
        & np.isfinite(y_pred)
    )

    y_true_valid = y_true[finite_mask]
    y_pred_valid = y_pred[finite_mask]

    if len(y_true_valid) == 0:
        print(f"\n{model_name}: 无有效样本")

        return {
            "Model": model_name,
            "Dataset": "all_data_diagnostic",
            "R2": np.nan,
            "MSE": np.nan,
            "ARD_%": np.nan,
            "within_1pct": 0,
            "within_5pct": 0,
            "within_10pct": 0
        }, np.full_like(y_true, np.nan, dtype=float)

    r2 = r2_score(
        y_true_valid,
        y_pred_valid
    )

    mse = mean_squared_error(
        y_true_valid,
        y_pred_valid
    )

    relative_error_full = np.full_like(
        y_true,
        np.nan,
        dtype=float
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

    relative_error_full[finite_mask] = relative_error_valid

    within_1pct = np.sum(relative_error_valid <= 1)
    within_5pct = np.sum(relative_error_valid <= 5)
    within_10pct = np.sum(relative_error_valid <= 10)

    print(f"\n========== {model_name} ==========")
    print(f"R2  = {r2:.6f}")
    print(f"MSE = {mse:.10f}")
    print(f"ARD = {ard:.4f}%")
    print(f"误差 <= 1% 的点数: {within_1pct}")
    print(f"误差 <= 5% 的点数: {within_5pct}")
    print(f"误差 <= 10% 的点数: {within_10pct}")

    return {
        "Model": model_name,
        "Dataset": "all_data_diagnostic",
        "R2": r2,
        "MSE": mse,
        "ARD_%": ard,
        "within_1pct": within_1pct,
        "within_5pct": within_5pct,
        "within_10pct": within_10pct
    }, relative_error_full


sub_298_summary, sub_298_rel_err = evaluate_submodel(
    y_298,
    isentropic_298_pred_all,
    model_name="Isentropic_298_submodel_RF"
)

sub_Tb_summary, sub_Tb_rel_err = evaluate_submodel(
    y_Tb,
    isentropic_Tb_pred_all,
    model_name="Isentropic_Tb_submodel_RF"
)

sub_Tb_pred_summary, sub_Tb_pred_rel_err = evaluate_submodel(
    Tb_raw,
    Tb_pred_all,
    model_name="Tb_submodel_Huber"
)


# ============================================================
# 10. 构建全量点级数据集
# ============================================================
X_total = []
y_total = []
material_ids = []
temperatures = []
slope_points = []

for _, row in df.iterrows():
    material_id = row[material_id_col]

    Nk = row[group_cols].to_numpy(dtype=float)
    temps = row[temp_cols].to_numpy(dtype=float)
    vals = row[v_cols].to_numpy(dtype=float)
    slope = float(row["slope"])

    if not np.isfinite(Nk).all():
        continue

    if not np.isfinite(slope):
        continue

    for T, val in zip(temps, vals):
        if not np.isfinite(T) or not np.isfinite(val):
            continue

        features = np.concatenate([
            Nk,
            [T],
            [slope]
        ])

        X_total.append(features)
        y_total.append(val)
        material_ids.append(material_id)
        temperatures.append(T)
        slope_points.append(slope)

X_total = np.array(X_total, dtype=float)
y_total = np.array(y_total, dtype=float)
material_ids = np.array(material_ids)
temperatures = np.array(temperatures, dtype=float)
slope_points = np.array(slope_points, dtype=float)


# ============================================================
# 11. 按物质 ID 划分训练集 / 测试集
# ============================================================
unique_materials = np.unique(material_ids)

train_materials, test_materials = train_test_split(
    unique_materials,
    test_size=0.2,
    random_state=40
)

train_mask = np.isin(material_ids, train_materials)
test_mask = np.isin(material_ids, test_materials)

X_train = X_total[train_mask]
y_train = y_total[train_mask]

X_test = X_total[test_mask]
y_test = y_total[test_mask]

material_ids_train = material_ids[train_mask]
temperatures_train = temperatures[train_mask]
slope_train = slope_points[train_mask]

material_ids_test = material_ids[test_mask]
temperatures_test = temperatures[test_mask]
slope_test = slope_points[test_mask]

print("\n========== 按物质划分 ==========")
print(f"总物质数: {len(unique_materials)}")
print(f"训练集物质数: {len(train_materials)}")
print(f"测试集物质数: {len(test_materials)}")
print(f"训练集样本点数: {X_train.shape[0]}")
print(f"测试集样本点数: {X_test.shape[0]}")
print(f"最终模型特征数: {X_train.shape[1]}")


# ============================================================
# 12. 训练最终随机森林模型
# ============================================================
model = RandomForestRegressor(
    n_estimators=100,
    random_state=42,
    n_jobs=-1
)

print("\n开始训练最终 RF 模型...")
model.fit(X_train, y_train)

print("\n最终 RF 模型参数:")
print(model)


# ============================================================
# 13. 评估函数
# ============================================================
def evaluate_dataset(y_true, y_pred, name="数据集", strict_less=False):
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
        print(f"\n{name} 结果：无有效样本")

        summary = {
            "Dataset": name,
            "R2": np.nan,
            "MSE": np.nan,
            "ARD_%": np.nan,
            "within_1pct": 0,
            "within_5pct": 0,
            "within_10pct": 0
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
        within_1pct = np.sum(relative_error_valid < 1)
        within_5pct = np.sum(relative_error_valid < 5)
        within_10pct = np.sum(relative_error_valid < 10)
    else:
        within_1pct = np.sum(relative_error_valid <= 1)
        within_5pct = np.sum(relative_error_valid <= 5)
        within_10pct = np.sum(relative_error_valid <= 10)

    print(f"\n{name} 结果：")
    print(f"R2  = {r2:.6f}")
    print(f"MSE = {mse:.10f}")
    print(f"ARD = {ard:.4f}%")

    if strict_less:
        print(f"相对误差 < 1% 的点数: {within_1pct}")
        print(f"相对误差 < 5% 的点数: {within_5pct}")
        print(f"相对误差 < 10% 的点数: {within_10pct}")
    else:
        print(f"相对误差 <= 1% 的点数: {within_1pct}")
        print(f"相对误差 <= 5% 的点数: {within_5pct}")
        print(f"相对误差 <= 10% 的点数: {within_10pct}")

    summary = {
        "Dataset": name,
        "R2": r2,
        "MSE": mse,
        "ARD_%": ard,
        "within_1pct": within_1pct,
        "within_5pct": within_5pct,
        "within_10pct": within_10pct
    }

    return relative_error, summary


# ============================================================
# 14. 训练集预测
# ============================================================
y_train_pred = model.predict(X_train)

rel_err_train, train_summary = evaluate_dataset(
    y_train,
    y_train_pred,
    name="Train",
    strict_less=False
)


# ============================================================
# 15. 测试集预测
# ============================================================
y_test_pred = model.predict(X_test)

rel_err_test, test_summary = evaluate_dataset(
    y_test,
    y_test_pred,
    name="Test",
    strict_less=False
)


# ============================================================
# 15.1 完整数据集统计：训练集 + 测试集
# ============================================================
y_all_true = np.concatenate([
    y_train,
    y_test
])

y_all_pred = np.concatenate([
    y_train_pred,
    y_test_pred
])

material_ids_all = np.concatenate([
    material_ids_train,
    material_ids_test
])

temperatures_all = np.concatenate([
    temperatures_train,
    temperatures_test
])

slope_all_points = np.concatenate([
    slope_train,
    slope_test
])

rel_err_all, all_summary = evaluate_dataset(
    y_all_true,
    y_all_pred,
    name="All_train_plus_test",
    strict_less=True
)

print("\nIsentropic Exponent RF + slope 完整数据集预测偏差 1%，5%，10%分别为：")
print(all_summary["within_1pct"])
print(all_summary["within_5pct"])
print(all_summary["within_10pct"])


# ============================================================
# 16. 保存训练集结果
# ============================================================
train_results = pd.DataFrame({
    "Set": "Train",
    "Material_ID": material_ids_train,
    "Temperature (K)": temperatures_train,
    "slope": slope_train,
    "Measured": y_train,
    "Predicted": y_train_pred,
    "Absolute Error": np.abs(y_train - y_train_pred),
    "Relative Error (%)": rel_err_train
})


# ============================================================
# 17. 保存测试集结果
# ============================================================
test_results = pd.DataFrame({
    "Set": "Test",
    "Material_ID": material_ids_test,
    "Temperature (K)": temperatures_test,
    "slope": slope_test,
    "Measured": y_test,
    "Predicted": y_test_pred,
    "Absolute Error": np.abs(y_test - y_test_pred),
    "Relative Error (%)": rel_err_test
})


# ============================================================
# 18. 保存完整数据集结果
# ============================================================
all_results = pd.DataFrame({
    "Set": "All_train_plus_test",
    "Material_ID": material_ids_all,
    "Temperature (K)": temperatures_all,
    "slope": slope_all_points,
    "Measured": y_all_true,
    "Predicted": y_all_pred,
    "Absolute Error": np.abs(y_all_true - y_all_pred),
    "Relative Error (%)": rel_err_all
})


# ============================================================
# 19. 保存 slope 信息
# ============================================================
slope_info = pd.DataFrame({
    "Material_ID": df[material_id_col].values,
    "isentropic_298_pred": isentropic_298_pred_all,
    "isentropic_Tb_pred": isentropic_Tb_pred_all,
    "Tb_pred": Tb_pred_all,
    "slope": slope_values
})


# ============================================================
# 20. 保存子模型结果
# ============================================================
submodel_298_result = pd.DataFrame({
    "Material_ID": df[material_id_col].values,
    "Isentropic_298_true": y_298,
    "Isentropic_298_pred": isentropic_298_pred_all,
    "Absolute Error": np.abs(y_298 - isentropic_298_pred_all),
    "Relative Error (%)": sub_298_rel_err
})

submodel_Tb_result = pd.DataFrame({
    "Material_ID": df[material_id_col].values,
    "Isentropic_Tb_true": y_Tb,
    "Isentropic_Tb_pred": isentropic_Tb_pred_all,
    "Absolute Error": np.abs(y_Tb - isentropic_Tb_pred_all),
    "Relative Error (%)": sub_Tb_rel_err
})

submodel_Tb_pred_result = pd.DataFrame({
    "Material_ID": df[material_id_col].values,
    "Tb_true": Tb_raw,
    "Tb_pred": Tb_pred_all,
    "Absolute Error": np.abs(Tb_raw - Tb_pred_all),
    "Relative Error (%)": sub_Tb_pred_rel_err
})


# ============================================================
# 21. 汇总指标表
# ============================================================
summary = pd.DataFrame([
    sub_298_summary,
    sub_Tb_summary,
    sub_Tb_pred_summary,
    {
        "Model": "Final_RF_with_slope",
        "Dataset": "Train",
        "R2": train_summary["R2"],
        "MSE": train_summary["MSE"],
        "ARD_%": train_summary["ARD_%"],
        "within_1pct": train_summary["within_1pct"],
        "within_5pct": train_summary["within_5pct"],
        "within_10pct": train_summary["within_10pct"]
    },
    {
        "Model": "Final_RF_with_slope",
        "Dataset": "Test",
        "R2": test_summary["R2"],
        "MSE": test_summary["MSE"],
        "ARD_%": test_summary["ARD_%"],
        "within_1pct": test_summary["within_1pct"],
        "within_5pct": test_summary["within_5pct"],
        "within_10pct": test_summary["within_10pct"]
    },
    {
        "Model": "Final_RF_with_slope",
        "Dataset": "All_train_plus_test",
        "R2": all_summary["R2"],
        "MSE": all_summary["MSE"],
        "ARD_%": all_summary["ARD_%"],
        "within_1pct": all_summary["within_1pct"],
        "within_5pct": all_summary["within_5pct"],
        "within_10pct": all_summary["within_10pct"]
    }
])


# ============================================================
# 22. 保存到 Excel
# ============================================================
output_file = "iex预测结果_加slope特征_RF_train_test_split.xlsx"

with pd.ExcelWriter(output_file, engine="xlsxwriter") as writer:
    train_results.to_excel(
        writer,
        sheet_name="Train_Predictions",
        index=False
    )

    test_results.to_excel(
        writer,
        sheet_name="Test_Predictions",
        index=False
    )

    all_results.to_excel(
        writer,
        sheet_name="All_Predictions",
        index=False
    )

    slope_info.to_excel(
        writer,
        sheet_name="slope_info",
        index=False
    )

    submodel_298_result.to_excel(
        writer,
        sheet_name="IE_298_submodel",
        index=False
    )

    submodel_Tb_result.to_excel(
        writer,
        sheet_name="IE_Tb_submodel",
        index=False
    )

    submodel_Tb_pred_result.to_excel(
        writer,
        sheet_name="Tb_submodel",
        index=False
    )

    summary.to_excel(
        writer,
        sheet_name="Summary",
        index=False
    )

print(f"\n已保存预测结果为: {output_file}")


# ============================================================
# 23. 保存特征重要性
# ============================================================
feature_names = list(group_cols) + [
    "Temperature",
    "slope"
]

feature_importance_df = pd.DataFrame({
    "Feature": feature_names,
    "Importance": model.feature_importances_
}).sort_values(
    by="Importance",
    ascending=False
)

importance_file = "Isentropic_Exponent_RF_with_slope_feature_importance.xlsx"

feature_importance_df.to_excel(
    importance_file,
    index=False
)

print(f"特征重要性已保存为: {importance_file}")


# ============================================================
# 24. 输出模型结构记录
# ============================================================
print("\n当前 Isentropic Exponent RF + slope 模型结构:")
print("Isentropic_298_submodel: RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)")
print("Isentropic_Tb_submodel: RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)")
print("Tb_submodel: HuberRegressor(max_iter=10000), input = PolynomialFeatures(Nk, degree=2)")
print("slope = (Isentropic_Tb_pred - Isentropic_298_pred) / (Tb_pred - 298.15)")
print("Final target: ordinary Isentropic Exponent")
print("Final model: RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)")
print("Final input features: 19 group counts + Temperature + slope")
print("Split: material-level 8:2 split, random_state=40")
print("Final all-data statistics use strict thresholds: <1%, <5%, <10%")