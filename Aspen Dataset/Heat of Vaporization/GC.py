# import numpy as np
# import pandas as pd
# from scipy.optimize import least_squares
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split
#
# # ==================== 1. 读取数据 ====================
# df = pd.read_excel("heat of vaporization 204.xlsx", sheet_name="Sheet1")
#
# id_col = df.columns[0]
#
# Nk_all = df.iloc[:, 13:32].apply(pd.to_numeric, errors="coerce").values   # 19个基团
# MW_all = pd.to_numeric(df.iloc[:, 4], errors="coerce").values.reshape(-1, 1)
# Nc_all = pd.to_numeric(df.iloc[:, 10], errors="coerce").values.reshape(-1, 1)
# T_all = df.iloc[:, 32:42].apply(pd.to_numeric, errors="coerce").values     # 温度 10列
# Hvap_all = df.iloc[:, 42:52].apply(pd.to_numeric, errors="coerce").values  # ΔHvap 10列
#
# # ==================== 2. 清洗非法值 ====================
# # 保留10个 Hvap 点都有限且 > 0 的物质
# valid_mask = np.isfinite(Hvap_all) & (Hvap_all > 0)
# valid_mask = valid_mask.all(axis=1)
#
# df_valid = df.loc[valid_mask].copy().reset_index(drop=True)
#
# Nk = Nk_all[valid_mask]
# MW = MW_all[valid_mask]
# Nc = Nc_all[valid_mask]
# T = T_all[valid_mask]
# Hvap = Hvap_all[valid_mask]
# compound_ids = df.loc[valid_mask, id_col].values
#
# print("========== 数据清洗后 ==========")
# print(f"有效物质数: {len(Nk)}")
#
# # ==================== 3. 按物质 8:2 划分 ====================
# material_indices = np.arange(len(Nk))
# train_idx, test_idx = train_test_split(
#     material_indices,
#     test_size=0.2,
#     random_state=42
# )
#
# print("========== 按物质划分 ==========")
# print(f"训练集物质数: {len(train_idx)}")
# print(f"测试集物质数: {len(test_idx)}")
#
# Nk_train, Nk_test = Nk[train_idx], Nk[test_idx]
# MW_train, MW_test = MW[train_idx], MW[test_idx]
# Nc_train, Nc_test = Nc[train_idx], Nc[test_idx]
# T_train_raw, T_test_raw = T[train_idx], T[test_idx]
# Hvap_train_raw, Hvap_test_raw = Hvap[train_idx], Hvap[test_idx]
# id_train_raw, id_test_raw = compound_ids[train_idx], compound_ids[test_idx]
#
# # ==================== 4. 展开为温度点级样本 ====================
# def build_point_dataset(Nk, MW, Nc, T, Hvap, compound_ids):
#     X = np.hstack([
#         Nk.repeat(10, axis=0),
#         MW.repeat(10, axis=0),
#         Nc.repeat(10, axis=0),
#         T.flatten().reshape(-1, 1)
#     ])
#     y = Hvap.flatten()
#
#     expanded_ids = np.repeat(compound_ids, 10)
#     expanded_T = T.flatten()
#
#     mask = np.isfinite(y) & np.isfinite(X).all(axis=1)
#
#     return (
#         X[mask],
#         y[mask],
#         expanded_ids[mask],
#         expanded_T[mask]
#     )
#
# X_train, y_train, id_train, T_used_train = build_point_dataset(
#     Nk_train, MW_train, Nc_train, T_train_raw, Hvap_train_raw, id_train_raw
# )
#
# X_test, y_test, id_test, T_used_test = build_point_dataset(
#     Nk_test, MW_test, Nc_test, T_test_raw, Hvap_test_raw, id_test_raw
# )
#
# print(f"训练集样本点数: {len(y_train)}")
# print(f"测试集样本点数: {len(y_test)}")
#
# # ==================== 5. 预测函数（适配19个基团） ====================
# def predict_hvap(params, X):
#     Nk = X[:, :19]
#     MW = X[:, 19].reshape(-1, 1)
#     Nc = X[:, 20].reshape(-1, 1)
#     T = np.clip(X[:, 21].reshape(-1, 1), 1e-6, None)
#
#     B1k = params[0:19]
#     B2k = params[19:38]
#     C1k = params[38:57]
#     C2k = params[57:76]
#     D1k = params[76:95]
#     D2k = params[95:114]
#     beta, gamma, delta = params[114:117]
#     f0, f1 = params[117:119]
#
#     R = 8.3144
#
#     Bi = np.sum(Nk * (B1k + MW * B2k), axis=1, keepdims=True) + beta * (f0 + Nc * f1)
#     Ci = np.sum(Nk * (C1k + MW * C2k), axis=1, keepdims=True) + gamma * (f0 + Nc * f1)
#     Di = np.sum(Nk * (D1k + MW * D2k), axis=1, keepdims=True) + delta * (f0 + Nc * f1)
#
#     y_pred = -R * ((1.5 * Bi) / np.sqrt(T) + Ci * T + Di * T**2)
#     return y_pred.flatten()
#
# def residuals(params, X, y):
#     y_pred = predict_hvap(params, X)
#     return y_pred - y
#
# # ==================== 6. 参数初始化 ====================
# # 19*6 + 3 + 2 = 119
# params_init = np.zeros(119)
#
# # ==================== 7. 最小二乘拟合（只用训练集） ====================
# print("\n🚀 使用训练集拟合中，请稍候...")
# result = least_squares(
#     residuals,
#     x0=params_init,
#     args=(X_train, y_train),
#     max_nfev=10000
# )
#
# # ==================== 8. 输出参数 ====================
# param_names = (
#     [f"B1_{i}" for i in range(19)] +
#     [f"B2_{i}" for i in range(19)] +
#     [f"C1_{i}" for i in range(19)] +
#     [f"C2_{i}" for i in range(19)] +
#     [f"D1_{i}" for i in range(19)] +
#     [f"D2_{i}" for i in range(19)] +
#     ["beta", "gamma", "delta", "f0", "f1"]
# )
#
# print("\n🔧 参数拟合结果：")
# for name, val in zip(param_names, result.x):
#     print(f"{name:10s}: {val:.6f}")
#
# # ==================== 9. 评估函数 ====================
# def evaluate_dataset(name, X, y, compound_ids, temp_values, params):
#     y_pred = predict_hvap(params, X)
#
#     mse = mean_squared_error(y, y_pred)
#     r2 = r2_score(y, y_pred)
#     ard = np.mean(np.abs((y_pred - y) / y)) * 100
#
#     relative_error = np.abs((y_pred - y) / y) * 100
#     within_1pct = np.sum(relative_error <= 1)
#     within_5pct = np.sum(relative_error <= 5)
#     within_10pct = np.sum(relative_error <= 10)
#
#     print(f"\n========== {name} ==========")
#     print(f"R²  = {r2:.6f}")
#     print(f"MSE = {mse:.4f}")
#     print(f"ARD = {ard:.2f}%")
#     print(f"误差 ≤ 1% 的点数: {within_1pct}")
#     print(f"误差 ≤ 5% 的点数: {within_5pct}")
#     print(f"误差 ≤ 10% 的点数: {within_10pct}")
#
#     result_df = pd.DataFrame({
#         "Split": name,
#         "Compound_ID": compound_ids,
#         "Temperature (K)": temp_values,
#         "Hvap_true (J/mol)": y,
#         "Hvap_pred (J/mol)": y_pred,
#         "Absolute Error": np.abs(y - y_pred),
#         "Relative Error (%)": relative_error
#     })
#
#     summary = {
#         "Split": name,
#         "R2": r2,
#         "MSE": mse,
#         "ARD_%": ard,
#         "within_1pct": within_1pct,
#         "within_5pct": within_5pct,
#         "within_10pct": within_10pct
#     }
#
#     return result_df, summary
#
# # ==================== 10. 训练集 / 测试集评估 ====================
# train_result_df, train_summary = evaluate_dataset(
#     "train", X_train, y_train, id_train, T_used_train, result.x
# )
#
# test_result_df, test_summary = evaluate_dataset(
#     "test", X_test, y_test, id_test, T_used_test, result.x
# )
#
# # ==================== 11. 保存结果 ====================
# all_result_df = pd.concat([train_result_df, test_result_df], ignore_index=True)
# summary_df = pd.DataFrame([train_summary, test_summary])
#
# output_filename = "Hvap_prediction_results_train_test_split.xlsx"
# with pd.ExcelWriter(output_filename, engine="xlsxwriter") as writer:
#     all_result_df.to_excel(writer, sheet_name="predictions", index=False)
#     summary_df.to_excel(writer, sheet_name="summary", index=False)
#
# print(f"\n✅ 已保存预测结果为 {output_filename}")


import numpy as np
import pandas as pd

from scipy.optimize import least_squares
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


# ==================== 1. 读取数据 ====================
df = pd.read_excel("heat of vaporization 204.xlsx", sheet_name="Sheet1")

id_col = df.columns[0]

Nk_all = df.iloc[:, 13:32].apply(pd.to_numeric, errors="coerce").values   # 19个基团
MW_all = pd.to_numeric(df.iloc[:, 4], errors="coerce").values.reshape(-1, 1)
Nc_all = pd.to_numeric(df.iloc[:, 10], errors="coerce").values.reshape(-1, 1)
T_all = df.iloc[:, 32:42].apply(pd.to_numeric, errors="coerce").values     # 温度 10列
Hvap_all = df.iloc[:, 42:52].apply(pd.to_numeric, errors="coerce").values  # ΔHvap 10列


# ==================== 2. 清洗非法值 ====================
# 保留10个 Hvap 点都有限且 > 0 的物质
valid_mask = np.isfinite(Hvap_all) & (Hvap_all > 0)
valid_mask = valid_mask.all(axis=1)

df_valid = df.loc[valid_mask].copy().reset_index(drop=True)

Nk = Nk_all[valid_mask]
MW = MW_all[valid_mask]
Nc = Nc_all[valid_mask]
T = T_all[valid_mask]
Hvap = Hvap_all[valid_mask]
compound_ids = df.loc[valid_mask, id_col].values

print("========== 数据清洗后 ==========")
print(f"有效物质数: {len(Nk)}")


# ==================== 3. 按物质 8:2 划分 ====================
material_indices = np.arange(len(Nk))

train_idx, test_idx = train_test_split(
    material_indices,
    test_size=0.2,
    random_state=42
)

print("========== 按物质划分 ==========")
print(f"训练集物质数: {len(train_idx)}")
print(f"测试集物质数: {len(test_idx)}")

Nk_train, Nk_test = Nk[train_idx], Nk[test_idx]
MW_train, MW_test = MW[train_idx], MW[test_idx]
Nc_train, Nc_test = Nc[train_idx], Nc[test_idx]

T_train_raw, T_test_raw = T[train_idx], T[test_idx]
Hvap_train_raw, Hvap_test_raw = Hvap[train_idx], Hvap[test_idx]

id_train_raw, id_test_raw = compound_ids[train_idx], compound_ids[test_idx]


# ==================== 4. 展开为温度点级样本 ====================
def build_point_dataset(Nk, MW, Nc, T, Hvap, compound_ids):
    X = np.hstack([
        Nk.repeat(10, axis=0),
        MW.repeat(10, axis=0),
        Nc.repeat(10, axis=0),
        T.flatten().reshape(-1, 1)
    ])

    y = Hvap.flatten()

    expanded_ids = np.repeat(compound_ids, 10)
    expanded_T = T.flatten()

    mask = np.isfinite(y) & np.isfinite(X).all(axis=1)

    return (
        X[mask],
        y[mask],
        expanded_ids[mask],
        expanded_T[mask]
    )


X_train, y_train, id_train, T_used_train = build_point_dataset(
    Nk_train,
    MW_train,
    Nc_train,
    T_train_raw,
    Hvap_train_raw,
    id_train_raw
)

X_test, y_test, id_test, T_used_test = build_point_dataset(
    Nk_test,
    MW_test,
    Nc_test,
    T_test_raw,
    Hvap_test_raw,
    id_test_raw
)

print(f"训练集样本点数: {len(y_train)}")
print(f"测试集样本点数: {len(y_test)}")


# ==================== 5. 预测函数（适配19个基团） ====================
def predict_hvap(params, X):
    Nk = X[:, :19]
    MW = X[:, 19].reshape(-1, 1)
    Nc = X[:, 20].reshape(-1, 1)
    T = np.clip(X[:, 21].reshape(-1, 1), 1e-6, None)

    B1k = params[0:19]
    B2k = params[19:38]

    C1k = params[38:57]
    C2k = params[57:76]

    D1k = params[76:95]
    D2k = params[95:114]

    beta, gamma, delta = params[114:117]
    f0, f1 = params[117:119]

    R = 8.3144

    Bi = (
        np.sum(Nk * (B1k + MW * B2k), axis=1, keepdims=True)
        + beta * (f0 + Nc * f1)
    )

    Ci = (
        np.sum(Nk * (C1k + MW * C2k), axis=1, keepdims=True)
        + gamma * (f0 + Nc * f1)
    )

    Di = (
        np.sum(Nk * (D1k + MW * D2k), axis=1, keepdims=True)
        + delta * (f0 + Nc * f1)
    )

    y_pred = -R * (
        (1.5 * Bi) / np.sqrt(T)
        + Ci * T
        + Di * T ** 2
    )

    return y_pred.flatten()


def residuals(params, X, y):
    y_pred = predict_hvap(params, X)
    return y_pred - y


# ==================== 6. 参数初始化 ====================
# 19*6 + 3 + 2 = 119
params_init = np.zeros(119)


# ==================== 7. 最小二乘拟合（只用训练集） ====================
print("\n使用训练集拟合中，请稍候...")

result = least_squares(
    residuals,
    x0=params_init,
    args=(X_train, y_train),
    max_nfev=10000
)


# ==================== 8. 输出参数 ====================
param_names = (
    [f"B1_{i}" for i in range(19)] +
    [f"B2_{i}" for i in range(19)] +
    [f"C1_{i}" for i in range(19)] +
    [f"C2_{i}" for i in range(19)] +
    [f"D1_{i}" for i in range(19)] +
    [f"D2_{i}" for i in range(19)] +
    ["beta", "gamma", "delta", "f0", "f1"]
)

print("\n参数拟合结果：")
for name, val in zip(param_names, result.x):
    print(f"{name:10s}: {val:.6f}")


# ==================== 9. 评估函数 ====================
def evaluate_dataset(
    name,
    X,
    y,
    compound_ids,
    temp_values,
    params,
    strict_less=False
):
    y_pred = predict_hvap(params, X)

    mse = mean_squared_error(y, y_pred)
    r2 = r2_score(y, y_pred)

    nonzero_mask = np.abs(y) > 1e-12
    relative_error = np.full_like(y, np.nan, dtype=float)

    if np.any(nonzero_mask):
        relative_error[nonzero_mask] = np.abs(
            (y_pred[nonzero_mask] - y[nonzero_mask])
            / y[nonzero_mask]
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

    print(f"\n========== {name} ==========")
    print(f"R²  = {r2:.6f}")
    print(f"MSE = {mse:.4f}")
    print(f"ARD = {ard:.2f}%")

    if strict_less:
        print(f"误差 < 1% 的点数: {within_1pct}")
        print(f"误差 < 5% 的点数: {within_5pct}")
        print(f"误差 < 10% 的点数: {within_10pct}")
    else:
        print(f"误差 <= 1% 的点数: {within_1pct}")
        print(f"误差 <= 5% 的点数: {within_5pct}")
        print(f"误差 <= 10% 的点数: {within_10pct}")

    result_df = pd.DataFrame({
        "Split": name,
        "Compound_ID": compound_ids,
        "Temperature (K)": temp_values,
        "Hvap_true (J/mol)": y,
        "Hvap_pred (J/mol)": y_pred,
        "Absolute Error": np.abs(y - y_pred),
        "Relative Error (%)": relative_error
    })

    summary = {
        "Split": name,
        "R2": r2,
        "MSE": mse,
        "ARD_%": ard,
        "within_1pct": within_1pct,
        "within_5pct": within_5pct,
        "within_10pct": within_10pct
    }

    return result_df, summary


# ==================== 10. 训练集 / 测试集评估 ====================
train_result_df, train_summary = evaluate_dataset(
    "train",
    X_train,
    y_train,
    id_train,
    T_used_train,
    result.x,
    strict_less=False
)

test_result_df, test_summary = evaluate_dataset(
    "test",
    X_test,
    y_test,
    id_test,
    T_used_test,
    result.x,
    strict_less=False
)


# ==================== 10.1 完整数据集统计：训练集 + 测试集 ====================
X_all = np.vstack([
    X_train,
    X_test
])

y_all = np.concatenate([
    y_train,
    y_test
])

id_all = np.concatenate([
    id_train,
    id_test
])

T_used_all = np.concatenate([
    T_used_train,
    T_used_test
])

all_result_df, all_summary = evaluate_dataset(
    "all_train_plus_test",
    X_all,
    y_all,
    id_all,
    T_used_all,
    result.x,
    strict_less=True
)

print("\nHvap 完整数据集预测偏差 1%，5%，10%分别为：")
print(all_summary["within_1pct"])
print(all_summary["within_5pct"])
print(all_summary["within_10pct"])


# ==================== 11. 保存结果 ====================
train_test_result_df = pd.concat(
    [train_result_df, test_result_df],
    ignore_index=True
)

summary_df = pd.DataFrame([
    train_summary,
    test_summary,
    all_summary
])

output_filename = "Hvap_prediction_results_train_test_split.xlsx"

with pd.ExcelWriter(output_filename, engine="xlsxwriter") as writer:
    train_test_result_df.to_excel(
        writer,
        sheet_name="predictions",
        index=False
    )

    all_result_df.to_excel(
        writer,
        sheet_name="all_predictions",
        index=False
    )

    summary_df.to_excel(
        writer,
        sheet_name="summary",
        index=False
    )

    pd.DataFrame({
        "Parameter": param_names,
        "Value": result.x
    }).to_excel(
        writer,
        sheet_name="parameters",
        index=False
    )

print(f"\n已保存预测结果为 {output_filename}")


# ==================== 12. 输出模型结构记录 ====================
print("\n当前 Hvap 显式模型结构:")
print("Target: Heat of Vaporization, ordinary Hvap, not ln(Hvap)")
print("Model: least_squares explicit Hvap equation")
print("Parameter count: 119")
print("Input features: Nk + MW + Nc + T")
print("Expression:")
print("Hvap = -R * [(1.5*Bi)/sqrt(T) + Ci*T + Di*T^2]")
print("Bi, Ci, Di are group-contribution terms with MW and Nc corrections.")
print("Final all-data statistics use strict thresholds: <1%, <5%, <10%")