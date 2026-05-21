# import numpy as np
# import pandas as pd
#
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split
#
#
# # ========== 1. 读取数据，过滤有效物质 ==========
# file_path = "vp209.xlsx"
# df = pd.read_excel(file_path, sheet_name="Sheet1")
#
# # 特征提取
# Nk = df.iloc[:, 12:31].values       # 19个基团
# T = df.iloc[:, 31:41].values        # 10个温度点
# P_vp = df.iloc[:, 41:51].values     # 10个蒸汽压
#
# # 保留所有10个蒸汽压均有效、有限且 > 0 的物质
# valid_mask = np.isfinite(P_vp) & (P_vp > 0)
# valid_mask = valid_mask.all(axis=1)
#
# Nk = Nk[valid_mask]
# T = T[valid_mask]
# P_vp = P_vp[valid_mask]
#
# print(f"有效物质数量: {len(Nk)}")
#
#
# # ========== 2. 按物质划分训练集 / 测试集 ==========
# material_indices = np.arange(len(Nk))
#
# train_materials, test_materials = train_test_split(
#     material_indices,
#     test_size=0.2,
#     random_state=41
# )
#
# print(f"训练集物质数: {len(train_materials)}")
# print(f"测试集物质数: {len(test_materials)}")
#
#
# # ========== 3. 构建展开后的数据集 ==========
# def build_flat_data(Nk_sub, T_sub, P_vp_sub):
#     """
#     将物质级数据展开为温度点级数据。
#
#     输入：
#         Nk_sub:    shape = (n_materials, 19)
#         T_sub:     shape = (n_materials, 10)
#         P_vp_sub:  shape = (n_materials, 10)
#
#     输出：
#         X: shape = (n_materials * 10, 20)
#            前19列为基团特征，最后1列为温度T
#
#         y: shape = (n_materials * 10,)
#            目标值为 ln(P)
#     """
#
#     X = np.hstack([
#         Nk_sub.repeat(10, axis=0),
#         T_sub.flatten().reshape(-1, 1)
#     ])
#
#     y = np.log(P_vp_sub).flatten()
#
#     finite_mask = np.isfinite(y) & np.isfinite(X).all(axis=1)
#
#     return X[finite_mask], y[finite_mask]
#
#
# X_train, y_train = build_flat_data(
#     Nk[train_materials],
#     T[train_materials],
#     P_vp[train_materials]
# )
#
# X_test, y_test = build_flat_data(
#     Nk[test_materials],
#     T[test_materials],
#     P_vp[test_materials]
# )
#
# print(f"训练集样本点数: {X_train.shape[0]}")
# print(f"测试集样本点数: {X_test.shape[0]}")
#
#
# # ========== 4. 定义 RF 模型 ==========
# # RF 是树模型，不需要 StandardScaler
# rf = RandomForestRegressor(
#     n_estimators=500,
#     max_depth=None,
#     min_samples_split=2,
#     min_samples_leaf=1,
#     max_features="sqrt",
#     bootstrap=True,
#     random_state=42,
#     n_jobs=-1
# )
#
#
# # ========== 5. 训练模型 ==========
# print("\n开始训练 RF 模型...")
# rf.fit(X_train, y_train)
#
# print("\nRF 模型参数:")
# print(rf)
#
#
# # ========== 6. 预测与评估函数 ==========
# def evaluate_model(model, X, y_true, set_name):
#     """
#     模型预测目标是 ln(P)，同时评估 ln(P) 和还原后的 P。
#     """
#
#     y_pred = model.predict(X)
#
#     P_true = np.exp(y_true)
#     P_pred = np.exp(y_pred)
#
#     # ln(P) 指标
#     r2_ln = r2_score(y_true, y_pred)
#     mse_ln = mean_squared_error(y_true, y_pred)
#
#     # P 指标
#     r2_P = r2_score(P_true, P_pred)
#     mse_P = mean_squared_error(P_true, P_pred)
#
#     rel_err = np.abs((P_pred - P_true) / P_true) * 100
#     ard = np.mean(rel_err)
#
#     within_1pct = np.sum(rel_err <= 1)
#     within_5pct = np.sum(rel_err <= 5)
#     within_10pct = np.sum(rel_err <= 10)
#
#     print(f"\n{set_name} 结果:")
#     print(f"ln(P)  R2  = {r2_ln:.6f}")
#     print(f"ln(P)  MSE = {mse_ln:.10f}")
#     print(f"P      R2  = {r2_P:.6f}")
#     print(f"P      MSE = {mse_P:.10f}")
#     print(f"P      ARD = {ard:.4f}%")
#     print(f"误差 <= 1%  : {within_1pct} 点")
#     print(f"误差 <= 5%  : {within_5pct} 点")
#     print(f"误差 <= 10% : {within_10pct} 点")
#
#     metrics = {
#         "R2_lnP": r2_ln,
#         "MSE_lnP": mse_ln,
#         "R2_P": r2_P,
#         "MSE_P": mse_P,
#         "ARD_%": ard,
#         "within_1pct": within_1pct,
#         "within_5pct": within_5pct,
#         "within_10pct": within_10pct
#     }
#
#     return y_pred, P_pred, rel_err, metrics
#
#
# # ========== 7. 训练集和测试集评估 ==========
# y_train_pred, P_train_pred, rel_err_train, train_metrics = evaluate_model(
#     rf,
#     X_train,
#     y_train,
#     "训练集"
# )
#
# y_test_pred, P_test_pred, rel_err_test, test_metrics = evaluate_model(
#     rf,
#     X_test,
#     y_test,
#     "测试集"
# )
#
#
# # ========== 8. 保存预测结果 ==========
# def build_result_df(X_orig, y_true, y_pred, rel_err, set_label):
#     """
#     构建长表结果。
#     X_orig 未标准化，包含 19 个基团特征 + 温度。
#     """
#
#     df_res = pd.DataFrame({
#         "Set": set_label,
#         "Temperature_K": X_orig[:, -1],
#         "ln(P)_true": y_true,
#         "ln(P)_pred": y_pred,
#         "P_true": np.exp(y_true),
#         "P_pred": np.exp(y_pred),
#         "Relative_Error_P (%)": rel_err
#     })
#
#     for i in range(19):
#         df_res[f"Group_{i + 1}"] = X_orig[:, i]
#
#     return df_res
#
#
# train_res = build_result_df(
#     X_train,
#     y_train,
#     y_train_pred,
#     rel_err_train,
#     "Train"
# )
#
# test_res = build_result_df(
#     X_test,
#     y_test,
#     y_test_pred,
#     rel_err_test,
#     "Test"
# )
#
# all_res = pd.concat([train_res, test_res], ignore_index=True)
#
# output_file = "VaporPressure_RF_TrainTestSplit.xlsx"
# all_res.to_excel(output_file, index=False)
#
# print(f"\n预测结果已保存至: {output_file}")
#
#
# # ========== 9. 保存评估汇总表 ==========
# summary = pd.DataFrame([
#     [
#         "Train",
#         train_metrics["R2_lnP"],
#         train_metrics["MSE_lnP"],
#         train_metrics["R2_P"],
#         train_metrics["MSE_P"],
#         train_metrics["ARD_%"],
#         train_metrics["within_1pct"],
#         train_metrics["within_5pct"],
#         train_metrics["within_10pct"]
#     ],
#     [
#         "Test",
#         test_metrics["R2_lnP"],
#         test_metrics["MSE_lnP"],
#         test_metrics["R2_P"],
#         test_metrics["MSE_P"],
#         test_metrics["ARD_%"],
#         test_metrics["within_1pct"],
#         test_metrics["within_5pct"],
#         test_metrics["within_10pct"]
#     ]
# ], columns=[
#     "Split",
#     "R2_lnP",
#     "MSE_lnP",
#     "R2_P",
#     "MSE_P",
#     "ARD_%",
#     "within_1pct",
#     "within_5pct",
#     "within_10pct"
# ])
#
# summary_file = "RF_Summary.xlsx"
# summary.to_excel(summary_file, index=False)
#
# print(f"评估汇总已保存至: {summary_file}")

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


# ========== 1. 读取数据，过滤有效物质 ==========
file_path = "vp209.xlsx"
df = pd.read_excel(file_path, sheet_name="Sheet1")

# 特征提取
Nk = df.iloc[:, 12:31].values       # 19个基团
T = df.iloc[:, 31:41].values        # 10个温度点
P_vp = df.iloc[:, 41:51].values     # 10个蒸汽压

# 保留所有10个蒸汽压均有效、有限且 > 0 的物质
valid_mask = np.isfinite(P_vp) & (P_vp > 0)
valid_mask = valid_mask.all(axis=1)

Nk = Nk[valid_mask]
T = T[valid_mask]
P_vp = P_vp[valid_mask]

print(f"有效物质数量: {len(Nk)}")


# ========== 2. 按物质划分训练集 / 测试集 ==========
material_indices = np.arange(len(Nk))

train_materials, test_materials = train_test_split(
    material_indices,
    test_size=0.2,
    random_state=41
)

print(f"训练集物质数: {len(train_materials)}")
print(f"测试集物质数: {len(test_materials)}")


# ========== 3. 构建展开后的数据集 ==========
def build_flat_data(Nk_sub, T_sub, P_vp_sub):
    """
    将物质级数据展开为温度点级数据。

    输入：
        Nk_sub:    shape = (n_materials, 19)
        T_sub:     shape = (n_materials, 10)
        P_vp_sub:  shape = (n_materials, 10)

    输出：
        X: shape = (n_materials * 10, 20)
           前19列为基团特征，最后1列为温度T

        y: shape = (n_materials * 10,)
           目标值为 ln(P)
    """

    X = np.hstack([
        Nk_sub.repeat(10, axis=0),
        T_sub.flatten().reshape(-1, 1)
    ])

    y = np.log(P_vp_sub).flatten()

    finite_mask = np.isfinite(y) & np.isfinite(X).all(axis=1)

    return X[finite_mask], y[finite_mask]


X_train, y_train = build_flat_data(
    Nk[train_materials],
    T[train_materials],
    P_vp[train_materials]
)

X_test, y_test = build_flat_data(
    Nk[test_materials],
    T[test_materials],
    P_vp[test_materials]
)

print(f"训练集样本点数: {X_train.shape[0]}")
print(f"测试集样本点数: {X_test.shape[0]}")


# ========== 4. 定义 RF 模型 ==========
# RF 是树模型，不需要 StandardScaler
rf = RandomForestRegressor(
    n_estimators=500,
    max_depth=None,
    min_samples_split=2,
    min_samples_leaf=1,
    max_features="sqrt",
    bootstrap=True,
    random_state=42,
    n_jobs=-1
)


# ========== 5. 训练模型 ==========
print("\n开始训练 RF 模型...")
rf.fit(X_train, y_train)

print("\nRF 模型参数:")
print(rf)


# ========== 6. 预测与评估函数 ==========
def evaluate_model(model, X, y_true, set_name, strict_less=False):
    """
    模型预测目标是 ln(P)，同时评估 ln(P) 和还原后的 P。
    strict_less=False 时统计 <=1%, <=5%, <=10%
    strict_less=True 时统计 <1%, <5%, <10%
    """

    y_pred = model.predict(X)

    P_true = np.exp(y_true)
    P_pred = np.exp(y_pred)

    # ln(P) 指标
    r2_ln = r2_score(y_true, y_pred)
    mse_ln = mean_squared_error(y_true, y_pred)

    # P 指标
    r2_P = r2_score(P_true, P_pred)
    mse_P = mean_squared_error(P_true, P_pred)

    rel_err = np.abs((P_pred - P_true) / P_true) * 100
    ard = np.mean(rel_err)

    if strict_less:
        within_1pct = np.sum(rel_err < 1)
        within_5pct = np.sum(rel_err < 5)
        within_10pct = np.sum(rel_err < 10)
    else:
        within_1pct = np.sum(rel_err <= 1)
        within_5pct = np.sum(rel_err <= 5)
        within_10pct = np.sum(rel_err <= 10)

    print(f"\n{set_name} 结果:")
    print(f"ln(P)  R2  = {r2_ln:.6f}")
    print(f"ln(P)  MSE = {mse_ln:.10f}")
    print(f"P      R2  = {r2_P:.6f}")
    print(f"P      MSE = {mse_P:.10f}")
    print(f"P      ARD = {ard:.4f}%")

    if strict_less:
        print(f"误差 < 1%  : {within_1pct} 点")
        print(f"误差 < 5%  : {within_5pct} 点")
        print(f"误差 < 10% : {within_10pct} 点")
    else:
        print(f"误差 <= 1%  : {within_1pct} 点")
        print(f"误差 <= 5%  : {within_5pct} 点")
        print(f"误差 <= 10% : {within_10pct} 点")

    metrics = {
        "R2_lnP": r2_ln,
        "MSE_lnP": mse_ln,
        "R2_P": r2_P,
        "MSE_P": mse_P,
        "ARD_%": ard,
        "within_1pct": within_1pct,
        "within_5pct": within_5pct,
        "within_10pct": within_10pct
    }

    return y_pred, P_pred, rel_err, metrics


# ========== 7. 训练集和测试集评估 ==========
y_train_pred, P_train_pred, rel_err_train, train_metrics = evaluate_model(
    rf,
    X_train,
    y_train,
    "训练集",
    strict_less=False
)

y_test_pred, P_test_pred, rel_err_test, test_metrics = evaluate_model(
    rf,
    X_test,
    y_test,
    "测试集",
    strict_less=False
)


# ========== 7.1 完整数据集统计：训练集 + 测试集 ==========
X_all = np.vstack([X_train, X_test])
y_all = np.concatenate([y_train, y_test])

y_all_pred, P_all_pred, rel_err_all, all_metrics = evaluate_model(
    rf,
    X_all,
    y_all,
    "完整数据集：训练集 + 测试集",
    strict_less=True
)

print("\n完整数据集实际蒸汽压 P 预测偏差 1%，5%，10%分别为：")
print(all_metrics["within_1pct"])
print(all_metrics["within_5pct"])
print(all_metrics["within_10pct"])


# ========== 8. 保存预测结果 ==========
def build_result_df(X_orig, y_true, y_pred, rel_err, set_label):
    """
    构建长表结果。
    X_orig 未标准化，包含 19 个基团特征 + 温度。
    """

    df_res = pd.DataFrame({
        "Set": set_label,
        "Temperature_K": X_orig[:, -1],
        "ln(P)_true": y_true,
        "ln(P)_pred": y_pred,
        "P_true": np.exp(y_true),
        "P_pred": np.exp(y_pred),
        "Relative_Error_P (%)": rel_err
    })

    for i in range(19):
        df_res[f"Group_{i + 1}"] = X_orig[:, i]

    return df_res


train_res = build_result_df(
    X_train,
    y_train,
    y_train_pred,
    rel_err_train,
    "Train"
)

test_res = build_result_df(
    X_test,
    y_test,
    y_test_pred,
    rel_err_test,
    "Test"
)

all_res = build_result_df(
    X_all,
    y_all,
    y_all_pred,
    rel_err_all,
    "All"
)

output_file = "VaporPressure_RF_TrainTestSplit.xlsx"

with pd.ExcelWriter(output_file, engine="xlsxwriter") as writer:
    pd.concat([train_res, test_res], ignore_index=True).to_excel(
        writer,
        sheet_name="predictions",
        index=False
    )
    all_res.to_excel(
        writer,
        sheet_name="all_predictions",
        index=False
    )

print(f"\n预测结果已保存至: {output_file}")


# ========== 9. 保存评估汇总表 ==========
summary = pd.DataFrame([
    [
        "Train",
        train_metrics["R2_lnP"],
        train_metrics["MSE_lnP"],
        train_metrics["R2_P"],
        train_metrics["MSE_P"],
        train_metrics["ARD_%"],
        train_metrics["within_1pct"],
        train_metrics["within_5pct"],
        train_metrics["within_10pct"]
    ],
    [
        "Test",
        test_metrics["R2_lnP"],
        test_metrics["MSE_lnP"],
        test_metrics["R2_P"],
        test_metrics["MSE_P"],
        test_metrics["ARD_%"],
        test_metrics["within_1pct"],
        test_metrics["within_5pct"],
        test_metrics["within_10pct"]
    ],
    [
        "All",
        all_metrics["R2_lnP"],
        all_metrics["MSE_lnP"],
        all_metrics["R2_P"],
        all_metrics["MSE_P"],
        all_metrics["ARD_%"],
        all_metrics["within_1pct"],
        all_metrics["within_5pct"],
        all_metrics["within_10pct"]
    ]
], columns=[
    "Split",
    "R2_lnP",
    "MSE_lnP",
    "R2_P",
    "MSE_P",
    "ARD_%",
    "within_1pct",
    "within_5pct",
    "within_10pct"
])

summary_file = "RF_Summary.xlsx"
summary.to_excel(summary_file, index=False)

print(f"评估汇总已保存至: {summary_file}")


# ========== 10. 输出模型结构记录 ==========
print("\n当前蒸汽压 RF 直接模型结构:")
print("Target: ln(P_vp)")
print("Evaluation target: P = exp(lnP)")
print("Model: RandomForestRegressor")
print("Parameters:")
print(rf)
print("Input features: Nk + T")