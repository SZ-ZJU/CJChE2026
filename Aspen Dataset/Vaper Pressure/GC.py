# import numpy as np
# import pandas as pd
# from scipy.optimize import least_squares
# from sklearn.metrics import mean_squared_error, r2_score
# from sklearn.model_selection import train_test_split
#
# # ==================== 数据加载 ====================
# file_path = "vp209.xlsx"
# df = pd.read_excel(file_path, sheet_name="Sheet1")
#
# # 基本属性提取（适配19个基团）
# compound_ids_all = df.iloc[:, 0].values
# MW = df.iloc[:, 4].values.reshape(-1, 1)
# Nc = df.iloc[:, 10].values.reshape(-1, 1)
# Ncs = df.iloc[:, 9].values.reshape(-1, 1)
# Nk = df.iloc[:, 12:31].values          # 19个基团
# T = df.iloc[:, 31:41].values           # 10个温度点
# P_vp = df.iloc[:, 41:51].values        # 10个蒸汽压点
#
# # ==================== 清洗非法值 ====================
# # 保留该物质10个蒸汽压点都有限且 > 0 的物质
# valid_mask = np.isfinite(P_vp) & (P_vp > 0)
# valid_mask = valid_mask.all(axis=1)
#
# compound_ids = compound_ids_all[valid_mask]
# MW = MW[valid_mask]
# Nc = Nc[valid_mask]
# Ncs = Ncs[valid_mask]
# Nk = Nk[valid_mask]
# T = T[valid_mask]
# P_vp = P_vp[valid_mask]
#
# print("========== 数据清洗后 ==========")
# print(f"有效物质数: {len(compound_ids)}")
#
# # ==================== 按物质 8:2 划分 ====================
# indices = np.arange(len(compound_ids))
#
# train_idx, test_idx = train_test_split(
#     indices,
#     test_size=0.2,
#     random_state=50
# )
#
# MW_train, MW_test = MW[train_idx], MW[test_idx]
# Nc_train, Nc_test = Nc[train_idx], Nc[test_idx]
# Ncs_train, Ncs_test = Ncs[train_idx], Ncs[test_idx]
# Nk_train, Nk_test = Nk[train_idx], Nk[test_idx]
# T_train_raw, T_test_raw = T[train_idx], T[test_idx]
# P_train_raw, P_test_raw = P_vp[train_idx], P_vp[test_idx]
# id_train_raw, id_test_raw = compound_ids[train_idx], compound_ids[test_idx]
#
# print("========== 按物质划分 ==========")
# print(f"训练集物质数: {len(train_idx)}")
# print(f"测试集物质数: {len(test_idx)}")
#
# # ==================== 构造点级数据集（每个物质展开10个温度点） ====================
# def build_point_dataset(MW, Nc, Ncs, Nk, T, P_vp, compound_ids):
#     y = np.log(P_vp).flatten()
#
#     X = np.hstack([
#         Nk.repeat(10, axis=0),
#         MW.repeat(10, axis=0),
#         Nc.repeat(10, axis=0),
#         Ncs.repeat(10, axis=0),
#         T.flatten().reshape(-1, 1)
#     ])
#
#     expanded_ids = np.repeat(compound_ids, 10)
#     expanded_T = T.flatten()
#
#     finite_mask = np.isfinite(y) & np.isfinite(X).all(axis=1)
#
#     return (
#         X[finite_mask, :],
#         y[finite_mask],
#         expanded_ids[finite_mask],
#         expanded_T[finite_mask]
#     )
#
# X_train, y_train, id_train, temp_train = build_point_dataset(
#     MW_train, Nc_train, Ncs_train, Nk_train, T_train_raw, P_train_raw, id_train_raw
# )
#
# X_test, y_test, id_test, temp_test = build_point_dataset(
#     MW_test, Nc_test, Ncs_test, Nk_test, T_test_raw, P_test_raw, id_test_raw
# )
#
# print(f"训练集样本点数: {len(y_train)}")
# print(f"测试集样本点数: {len(y_test)}")
#
# # ==================== 残差函数（适配19个基团） ====================
# def residuals(params, X, y):
#     Nk = X[:, :19]
#     MW = X[:, 19].reshape(-1, 1)
#     Nc = X[:, 20].reshape(-1, 1)
#     Ncs = X[:, 21].reshape(-1, 1)
#     # T = np.clip(X[:, 22].reshape(-1, ].reshape(-1, 1)
#     T = np.clip(X[:, 22].reshape(-1, 1), 1e-6, None)
#
#     A1k = params[:19]
#     A2k = params[19:38]
#     s0, s1 = params[38], params[39]
#     alpha, f0, f1 = params[40], params[41], params[42]
#     B1k = params[43:62]
#     B2k = params[62:81]
#     beta = params[81]
#     C1k = params[82:101]
#     C2k = params[101:120]
#
#     term_A = np.sum(Nk * (A1k + MW * A2k), axis=1) + (s0 + Ncs.flatten() * s1) + alpha * (f0 + Nc.flatten() * f1)
#     term_B = np.sum(Nk * (B1k + MW * B2k), axis=1) + beta * (f0 + Nc.flatten() * f1)
#     term_C = np.sum(Nk * (C1k + MW * C2k), axis=1)
#
#     y_pred = term_A + term_B / T.flatten() + term_C * np.log(T.flatten())
#     return y - y_pred
#
# # ==================== 初始参数设置 ====================
# params_init = np.zeros(120)
#
# # A1k (N_0 到 N_18)
# params_init[:19] = [
#     13.65853808, 3.28418546, -659.6444719, 12.37483133, 4.81265536,
#     2.91551829, 97.31954706, 87.70370771, 95.98266611, 3.887261236,
#     27.43160868, 207.1319101, 47.22447225, 4687.002401, 3.637088127,
#     1523.380387, 3162.746842, 12062.07738, -8900.847866
# ]
#
# # A2k (N_0*M 到 N_18*M)
# params_init[19:38] = [
#     -0.015716978, 0.009075383, 11.48620132, -21.10261532, -0.011767963,
#     0.002675368, -0.109835685, -0.010236179, -0.171652319, 0.005908914,
#     10.467947, -5.994107293, -0.112649727, -17.43861742, 0.001820612,
#     -12.29192011, -5.831333421, -30.99113155, 26.51752291
# ]
#
# # s0, s1, alpha, f0, f1
# params_init[38:43] = [17.60905342, -0.000738906, 0.018089414, 0.0, 1.0]
#
# # B1k (N_0/T 到 N_18/T)
# params_init[43:62] = [
#     -1346.02436, -683.1104648, 67218.65971, -1384.512471, -884.3388538,
#     -1241.799972, -8807.96886, -9868.206835, -9972.171472, -764.4721254,
#     -2768.98, -22960.24319, -4496.012972, -507785.7608, -2221.349576,
#     -157397.6395, -350388.1207, -1307700.942, 957312.8216
# ]
#
# # B2k (N_0*M/T 到 N_18*M/T)
# params_init[62:81] = [
#     1.451298512, -0.736859315, -584.0308556, 3.123573902, 0.887401846,
#     0.122658761, 8.501979442, 0.898999866, 15.05201845, -0.396917177,
#     6.455487385, 318.8958283, 9.649044453, 2010.74563, 0.550921963,
#     1486.747823, 523.9930512, 3372.517851, -2848.526234
# ]
#
# # beta
# params_init[81] = -6.750229278
#
# # C1k (N_0*ln(T) 到 N_18*ln(T))
# params_init[82:101] = [
#     -1.846676986, -0.38538898, 85.74714557, -1.76399843, -0.569402352,
#     -0.250943128, -13.054703, -11.40790845, -12.58276815, -0.468789896,
#     -3.52337599, -26.44154671, -6.353423865, -606.0715674, -0.130106514,
#     -198.3318276, -407.7121286, -1560.004645, 1152.427648
# ]
#
# # C2k (N_0*M*ln(T) 到 N_18*M*ln(T))
# params_init[101:120] = [
#     0.002016846, -0.001221385, 7.344413404, 0.894155383, 0.001594902,
#     -0.000468558, 0.01491123, 0.001327088, 0.022906548, -0.0008161,
#     -0.43609896, -3.639773727, 0.015093667, 11.71908672, -0.000385519,
#     -3.450680198, -14.53413618, 9.827970088, 2.387602073
# ]
#
# # ==================== 拟合（只用训练集） ====================
# print("\n🚀 使用训练集拟合中，请稍候...")
# result = least_squares(
#     residuals,
#     x0=params_init,
#     args=(X_train, y_train),
#     max_nfev=10000
# )
#
# # ==================== 评估函数 ====================
# def evaluate_dataset(name, X, y, compound_ids, temp_values, params):
#     y_pred = y - residuals(params, X, y)
#
#     # lnP 指标
#     mse_ln = mean_squared_error(y, y_pred)
#     r2_ln = r2_score(y, y_pred)
#
#     # 实际蒸汽压指标
#     P_true = np.exp(y)
#     P_pred = np.exp(y_pred)
#
#     mse_real = mean_squared_error(P_true, P_pred)
#     r2_real = r2_score(P_true, P_pred)
#     ard_real = np.mean(np.abs((P_pred - P_true) / P_true)) * 100
#
#     relative_error = np.abs((P_pred - P_true) / P_true) * 100
#     within_1pct = np.sum(relative_error <= 1)
#     within_5pct = np.sum(relative_error <= 5)
#     within_10pct = np.sum(relative_error <= 10)
#
#     print(f"\n========== {name} ==========")
#     print("ln(P) 指标:")
#     print(f"R²  = {r2_ln:.6f}")
#     print(f"MSE = {mse_ln:.6f}")
#
#     print("\n实际蒸汽压 P 指标:")
#     print(f"R² (P)  = {r2_real:.6f}")
#     print(f"MSE (P) = {mse_real:.6f}")
#     print(f"ARD (P) = {ard_real:.2f}%")
#     print(f"误差 ≤ 1% 的点数: {within_1pct}")
#     print(f"误差 ≤ 5% 的点数: {within_5pct}")
#     print(f"误差 ≤ 10% 的点数: {within_10pct}")
#
#     compare_df = pd.DataFrame({
#         "Split": name,
#         "Compound_ID": compound_ids,
#         "Temperature_K": temp_values,
#         "ln(P)_true": y,
#         "ln(P)_pred": y_pred,
#         "Absolute_Error_lnP": np.abs(y - y_pred),
#         "Relative_Error_lnP (%)": 100 * np.abs((y - y_pred) / y),
#         "P_true": P_true,
#         "P_pred": P_pred,
#         "Absolute_Error_P": np.abs(P_true - P_pred),
#         "Relative_Error_P (%)": relative_error
#     })
#
#     summary = {
#         "Split": name,
#         "R2_lnP": r2_ln,
#         "MSE_lnP": mse_ln,
#         "R2_P": r2_real,
#         "MSE_P": mse_real,
#         "ARD_P_%": ard_real,
#         "within_1pct": within_1pct,
#         "within_5pct": within_5pct,
#         "within_10pct": within_10pct
#     }
#
#     return compare_df, summary
#
# # ==================== 训练集 / 测试集评估 ====================
# train_compare_df, train_summary = evaluate_dataset(
#     "train", X_train, y_train, id_train, temp_train, result.x
# )
#
# test_compare_df, test_summary = evaluate_dataset(
#     "test", X_test, y_test, id_test, temp_test, result.x
# )
#
# # ==================== 保存结果 ====================
# all_compare_df = pd.concat([train_compare_df, test_compare_df], ignore_index=True)
# summary_df = pd.DataFrame([train_summary, test_summary])
#
# output_filename = "Gani_lnP_prediction_results_19group_train_test_split.xlsx"
# with pd.ExcelWriter(output_filename, engine="xlsxwriter") as writer:
#     all_compare_df.to_excel(writer, sheet_name="predictions", index=False)
#     summary_df.to_excel(writer, sheet_name="summary", index=False)
#
# print(f"\n✅ 已保存预测结果为 {output_filename}")

import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


# ==================== 数据加载 ====================
file_path = "vp209.xlsx"
df = pd.read_excel(file_path, sheet_name="Sheet1")

# 基本属性提取（适配19个基团）
compound_ids_all = df.iloc[:, 0].values
MW = df.iloc[:, 4].values.reshape(-1, 1)
Nc = df.iloc[:, 10].values.reshape(-1, 1)
Ncs = df.iloc[:, 9].values.reshape(-1, 1)
Nk = df.iloc[:, 12:31].values          # 19个基团
T = df.iloc[:, 31:41].values           # 10个温度点
P_vp = df.iloc[:, 41:51].values        # 10个蒸汽压点


# ==================== 清洗非法值 ====================
# 保留该物质10个蒸汽压点都有限且 > 0 的物质
valid_mask = np.isfinite(P_vp) & (P_vp > 0)
valid_mask = valid_mask.all(axis=1)

compound_ids = compound_ids_all[valid_mask]
MW = MW[valid_mask]
Nc = Nc[valid_mask]
Ncs = Ncs[valid_mask]
Nk = Nk[valid_mask]
T = T[valid_mask]
P_vp = P_vp[valid_mask]

print("========== 数据清洗后 ==========")
print(f"有效物质数: {len(compound_ids)}")


# ==================== 按物质 8:2 划分 ====================
indices = np.arange(len(compound_ids))

train_idx, test_idx = train_test_split(
    indices,
    test_size=0.2,
    random_state=50
)

MW_train, MW_test = MW[train_idx], MW[test_idx]
Nc_train, Nc_test = Nc[train_idx], Nc[test_idx]
Ncs_train, Ncs_test = Ncs[train_idx], Ncs[test_idx]
Nk_train, Nk_test = Nk[train_idx], Nk[test_idx]
T_train_raw, T_test_raw = T[train_idx], T[test_idx]
P_train_raw, P_test_raw = P_vp[train_idx], P_vp[test_idx]
id_train_raw, id_test_raw = compound_ids[train_idx], compound_ids[test_idx]

print("========== 按物质划分 ==========")
print(f"训练集物质数: {len(train_idx)}")
print(f"测试集物质数: {len(test_idx)}")


# ==================== 构造点级数据集（每个物质展开10个温度点） ====================
def build_point_dataset(MW, Nc, Ncs, Nk, T, P_vp, compound_ids):
    y = np.log(P_vp).flatten()

    X = np.hstack([
        Nk.repeat(10, axis=0),
        MW.repeat(10, axis=0),
        Nc.repeat(10, axis=0),
        Ncs.repeat(10, axis=0),
        T.flatten().reshape(-1, 1)
    ])

    expanded_ids = np.repeat(compound_ids, 10)
    expanded_T = T.flatten()

    finite_mask = np.isfinite(y) & np.isfinite(X).all(axis=1)

    return (
        X[finite_mask, :],
        y[finite_mask],
        expanded_ids[finite_mask],
        expanded_T[finite_mask]
    )


X_train, y_train, id_train, temp_train = build_point_dataset(
    MW_train, Nc_train, Ncs_train, Nk_train, T_train_raw, P_train_raw, id_train_raw
)

X_test, y_test, id_test, temp_test = build_point_dataset(
    MW_test, Nc_test, Ncs_test, Nk_test, T_test_raw, P_test_raw, id_test_raw
)

print(f"训练集样本点数: {len(y_train)}")
print(f"测试集样本点数: {len(y_test)}")


# ==================== 残差函数（适配19个基团） ====================
def residuals(params, X, y):
    Nk = X[:, :19]
    MW = X[:, 19].reshape(-1, 1)
    Nc = X[:, 20].reshape(-1, 1)
    Ncs = X[:, 21].reshape(-1, 1)
    T = np.clip(X[:, 22].reshape(-1, 1), 1e-6, None)

    A1k = params[:19]
    A2k = params[19:38]
    s0, s1 = params[38], params[39]
    alpha, f0, f1 = params[40], params[41], params[42]
    B1k = params[43:62]
    B2k = params[62:81]
    beta = params[81]
    C1k = params[82:101]
    C2k = params[101:120]

    term_A = (
        np.sum(Nk * (A1k + MW * A2k), axis=1)
        + (s0 + Ncs.flatten() * s1)
        + alpha * (f0 + Nc.flatten() * f1)
    )

    term_B = (
        np.sum(Nk * (B1k + MW * B2k), axis=1)
        + beta * (f0 + Nc.flatten() * f1)
    )

    term_C = np.sum(Nk * (C1k + MW * C2k), axis=1)

    y_pred = term_A + term_B / T.flatten() + term_C * np.log(T.flatten())

    return y - y_pred


# ==================== 初始参数设置 ====================
params_init = np.zeros(120)

# A1k (N_0 到 N_18)
params_init[:19] = [
    13.65853808, 3.28418546, -659.6444719, 12.37483133, 4.81265536,
    2.91551829, 97.31954706, 87.70370771, 95.98266611, 3.887261236,
    27.43160868, 207.1319101, 47.22447225, 4687.002401, 3.637088127,
    1523.380387, 3162.746842, 12062.07738, -8900.847866
]

# A2k (N_0*M 到 N_18*M)
params_init[19:38] = [
    -0.015716978, 0.009075383, 11.48620132, -21.10261532, -0.011767963,
    0.002675368, -0.109835685, -0.010236179, -0.171652319, 0.005908914,
    10.467947, -5.994107293, -0.112649727, -17.43861742, 0.001820612,
    -12.29192011, -5.831333421, -30.99113155, 26.51752291
]

# s0, s1, alpha, f0, f1
params_init[38:43] = [17.60905342, -0.000738906, 0.018089414, 0.0, 1.0]

# B1k (N_0/T 到 N_18/T)
params_init[43:62] = [
    -1346.02436, -683.1104648, 67218.65971, -1384.512471, -884.3388538,
    -1241.799972, -8807.96886, -9868.206835, -9972.171472, -764.4721254,
    -2768.98, -22960.24319, -4496.012972, -507785.7608, -2221.349576,
    -157397.6395, -350388.1207, -1307700.942, 957312.8216
]

# B2k (N_0*M/T 到 N_18*M/T)
params_init[62:81] = [
    1.451298512, -0.736859315, -584.0308556, 3.123573902, 0.887401846,
    0.122658761, 8.501979442, 0.898999866, 15.05201845, -0.396917177,
    6.455487385, 318.8958283, 9.649044453, 2010.74563, 0.550921963,
    1486.747823, 523.9930512, 3372.517851, -2848.526234
]

# beta
params_init[81] = -6.750229278

# C1k (N_0*ln(T) 到 N_18*ln(T))
params_init[82:101] = [
    -1.846676986, -0.38538898, 85.74714557, -1.76399843, -0.569402352,
    -0.250943128, -13.054703, -11.40790845, -12.58276815, -0.468789896,
    -3.52337599, -26.44154671, -6.353423865, -606.0715674, -0.130106514,
    -198.3318276, -407.7121286, -1560.004645, 1152.427648
]

# C2k (N_0*M*ln(T) 到 N_18*M*ln(T))
params_init[101:120] = [
    0.002016846, -0.001221385, 7.344413404, 0.894155383, 0.001594902,
    -0.000468558, 0.01491123, 0.001327088, 0.022906548, -0.0008161,
    -0.43609896, -3.639773727, 0.015093667, 11.71908672, -0.000385519,
    -3.450680198, -14.53413618, 9.827970088, 2.387602073
]


# ==================== 拟合（只用训练集） ====================
print("\n使用训练集拟合中，请稍候...")

result = least_squares(
    residuals,
    x0=params_init,
    args=(X_train, y_train),
    max_nfev=10000
)


# ==================== 评估函数 ====================
def evaluate_dataset(name, X, y, compound_ids, temp_values, params, strict_less=False):
    y_pred = y - residuals(params, X, y)

    # lnP 指标
    mse_ln = mean_squared_error(y, y_pred)
    r2_ln = r2_score(y, y_pred)

    # 实际蒸汽压指标
    P_true = np.exp(y)
    P_pred = np.exp(y_pred)

    mse_real = mean_squared_error(P_true, P_pred)
    r2_real = r2_score(P_true, P_pred)

    relative_error = np.abs((P_pred - P_true) / P_true) * 100
    ard_real = np.mean(relative_error)

    if strict_less:
        within_1pct = np.sum(relative_error < 1)
        within_5pct = np.sum(relative_error < 5)
        within_10pct = np.sum(relative_error < 10)
    else:
        within_1pct = np.sum(relative_error <= 1)
        within_5pct = np.sum(relative_error <= 5)
        within_10pct = np.sum(relative_error <= 10)

    print(f"\n========== {name} ==========")
    print("ln(P) 指标:")
    print(f"R²  = {r2_ln:.6f}")
    print(f"MSE = {mse_ln:.6f}")

    print("\n实际蒸汽压 P 指标:")
    print(f"R² (P)  = {r2_real:.6f}")
    print(f"MSE (P) = {mse_real:.6f}")
    print(f"ARD (P) = {ard_real:.2f}%")

    if strict_less:
        print(f"误差 < 1% 的点数: {within_1pct}")
        print(f"误差 < 5% 的点数: {within_5pct}")
        print(f"误差 < 10% 的点数: {within_10pct}")
    else:
        print(f"误差 ≤ 1% 的点数: {within_1pct}")
        print(f"误差 ≤ 5% 的点数: {within_5pct}")
        print(f"误差 ≤ 10% 的点数: {within_10pct}")

    compare_df = pd.DataFrame({
        "Split": name,
        "Compound_ID": compound_ids,
        "Temperature_K": temp_values,
        "ln(P)_true": y,
        "ln(P)_pred": y_pred,
        "Absolute_Error_lnP": np.abs(y - y_pred),
        "Relative_Error_lnP (%)": 100 * np.abs((y - y_pred) / y),
        "P_true": P_true,
        "P_pred": P_pred,
        "Absolute_Error_P": np.abs(P_true - P_pred),
        "Relative_Error_P (%)": relative_error
    })

    summary = {
        "Split": name,
        "R2_lnP": r2_ln,
        "MSE_lnP": mse_ln,
        "R2_P": r2_real,
        "MSE_P": mse_real,
        "ARD_P_%": ard_real,
        "within_1pct": within_1pct,
        "within_5pct": within_5pct,
        "within_10pct": within_10pct
    }

    return compare_df, summary


# ==================== 训练集 / 测试集评估 ====================
train_compare_df, train_summary = evaluate_dataset(
    "train",
    X_train,
    y_train,
    id_train,
    temp_train,
    result.x,
    strict_less=False
)

test_compare_df, test_summary = evaluate_dataset(
    "test",
    X_test,
    y_test,
    id_test,
    temp_test,
    result.x,
    strict_less=False
)


# ==================== 完整数据集评估：训练集 + 测试集 ====================
X_all = np.vstack([X_train, X_test])
y_all = np.concatenate([y_train, y_test])
id_all = np.concatenate([id_train, id_test])
temp_all = np.concatenate([temp_train, temp_test])

all_compare_df, all_summary = evaluate_dataset(
    "all_train_plus_test",
    X_all,
    y_all,
    id_all,
    temp_all,
    result.x,
    strict_less=True
)

print("\n完整数据集实际蒸汽压 P 预测偏差 1%，5%，10%分别为：")
print(all_summary["within_1pct"])
print(all_summary["within_5pct"])
print(all_summary["within_10pct"])


# ==================== 保存结果 ====================
all_compare_df_save = pd.concat(
    [train_compare_df, test_compare_df],
    ignore_index=True
)

summary_df = pd.DataFrame([
    train_summary,
    test_summary,
    all_summary
])

output_filename = "Gani_lnP_prediction_results_19group_train_test_split.xlsx"

with pd.ExcelWriter(output_filename, engine="xlsxwriter") as writer:
    all_compare_df_save.to_excel(writer, sheet_name="predictions", index=False)
    all_compare_df.to_excel(writer, sheet_name="all_predictions", index=False)
    summary_df.to_excel(writer, sheet_name="summary", index=False)

print(f"\n已保存预测结果为 {output_filename}")