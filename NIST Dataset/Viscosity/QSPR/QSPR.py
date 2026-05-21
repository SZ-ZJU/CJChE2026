import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from xgboost import XGBRegressor


pd.set_option("display.float_format", "{:.10f}".format)
np.set_printoptions(suppress=True, precision=10)


# =========================================================
# 1. 文件路径
# =========================================================
# 上一步筛选出的 25 个 viscosity Mordred 描述符
descriptor_file = Path("selected_descriptors_with_viscosity_mean_target.xlsx")
descriptor_sheet = "Selected_Features_Target"
selected_feature_sheet = "Selected_Features"

# 粘度原始实验数据，一行一个温度点
# 如果你的原始 Excel 文件名不同，只改这里
data_file = Path("dataset_viscosity_selected_by_two_k_with_lnVisc_invT_interpolation_8points.xlsx")
data_sheet = "Data_selected"

# 输出文件
output_file = Path("xgb_viscosity_100_seed_average_metrics_variable_points.xlsx")


# =========================================================
# 2. 基本设置
# =========================================================
temp_col_candidates = [
    "T_K",
    "Temperature",
    "Temperature_K",
    "temperature",
    "Temp_K",
    "T",
]

# 粘度目标列候选
# 优先使用 lnViscosity；如果没有，就使用 property_value / Viscosity
viscosity_col_candidates = [
    "lnViscosity",
    "lnViscosity_Pa_s",
    "ln_viscosity",
    "ln_viscosity_Pa_s",
    "ln(Viscosity)",
    "ln_mu",
    "lnmu",
    "property_value",
    "Viscosity",
    "viscosity",
    "Viscosity_Pa_s",
    "viscosity_Pa_s",
    "dynamic_viscosity",
    "Dynamic_Viscosity",
    "mu",
]

# 用于识别物质分组的候选列
data_material_key_candidates = [
    "material_key",
    "original_material_index",
    "pubchem_cid",
    "CID_int",
    "sdf_pubchem_cid",
    "existing_pubchem_cid",
    "inchikey",
    "InChIKey",
    "cas",
    "compound_name",
]

# 如果你明确知道目标是不是 lnViscosity，可以手动指定：
# True  = 目标是 lnViscosity，额外输出 Viscosity = exp(lnViscosity) 指标
# False = 目标是普通 viscosity
# None  = 根据列名自动判断；property_value 默认按 lnViscosity 处理
force_target_is_log = None

test_size = 0.2

seed_start = 0
n_seeds = 100
seed_list = list(range(seed_start, seed_start + n_seeds))

model_random_state = 42


# =========================================================
# 3. 工具函数
# =========================================================
def normalize_colname(name):
    return (
        str(name)
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "")
    )


def find_first_existing_col(df, candidates, required=True, col_type="列"):
    norm_map = {
        normalize_colname(c): c
        for c in df.columns
    }

    for c in candidates:
        key = normalize_colname(c)
        if key in norm_map:
            return norm_map[key]

    if required:
        raise ValueError(
            f"没有找到 {col_type}。\n"
            f"候选列名: {candidates}\n"
            f"当前列名: {list(df.columns)}"
        )

    return None


def is_valid_value(x):
    if pd.isna(x):
        return False

    s = str(x).strip()

    if s == "":
        return False

    if s.lower() in ["nan", "none", "null", "待定"]:
        return False

    return True


def clean_key_value(x):
    """
    将各种物质 ID 清洗成字符串 key。
    例如 123.0 -> '123'
    """
    if not is_valid_value(x):
        return np.nan

    s = str(x).strip()

    try:
        f = float(s)
        if np.isfinite(f) and abs(f - round(f)) < 1e-8:
            return str(int(round(f)))
    except Exception:
        pass

    return s


def choose_alignment_key(df_desc, df_data):
    """
    优先使用稳定 ID 对齐描述符表和原始 viscosity 数据。
    """
    candidate_pairs = [
        ("material_key", "material_key"),
        ("original_material_index", "original_material_index"),
        ("pubchem_cid", "pubchem_cid"),
        ("CID", "pubchem_cid"),
        ("CID_int", "pubchem_cid"),
        ("sdf_pubchem_cid", "pubchem_cid"),
        ("existing_pubchem_cid", "pubchem_cid"),
        ("inchikey", "inchikey"),
        ("InChIKey", "InChIKey"),
        ("cas", "cas"),
        ("compound_name", "compound_name"),
    ]

    for desc_col, data_col in candidate_pairs:
        if desc_col in df_desc.columns and data_col in df_data.columns:
            return desc_col, data_col

    return None, None


def choose_data_group_key(df_data):
    """
    用于将 Data_selected 按物质分组。
    不假设每个物质固定 8 行。
    """
    for col in data_material_key_candidates:
        if col in df_data.columns:
            return col

    return None


def infer_target_is_log(target_col):
    """
    根据列名判断目标是否为 lnViscosity。
    property_value 在当前流程中通常是 lnViscosity。
    """
    col_norm = normalize_colname(target_col)

    if "ln" in col_norm or "log" in col_norm:
        return True

    if col_norm == "propertyvalue":
        return True

    return False


def safe_exp(x):
    """
    防止 exp 溢出。
    """
    x = np.asarray(x, dtype=float)
    return np.exp(np.clip(x, -700, 700))


def calc_basic_metrics(y_true, y_pred, prefix):
    """
    返回 R2、MSE、RMSE、MAE、ARD、误差区间。
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    finite_mask = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true = y_true[finite_mask]
    y_pred = y_pred[finite_mask]

    if len(y_true) == 0:
        return {
            f"R2_{prefix}": np.nan,
            f"MSE_{prefix}": np.nan,
            f"RMSE_{prefix}": np.nan,
            f"MAE_{prefix}": np.nan,
            f"ARD_{prefix}_percent": np.nan,
            f"max_abs_error_{prefix}": np.nan,
            f"max_relative_error_{prefix}_percent": np.nan,
            f"relative_error_{prefix}_le_1_percent_ratio": np.nan,
            f"relative_error_{prefix}_le_5_percent_ratio": np.nan,
            f"relative_error_{prefix}_le_10_percent_ratio": np.nan,
        }

    error = y_pred - y_true
    abs_error = np.abs(error)

    try:
        r2 = r2_score(y_true, y_pred)
    except Exception:
        r2 = np.nan

    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_true, y_pred)

    valid_mask = np.abs(y_true) > 1e-12

    if valid_mask.sum() > 0:
        relative_error_percent = np.abs(
            (y_pred[valid_mask] - y_true[valid_mask]) / y_true[valid_mask]
        ) * 100.0

        ard = np.mean(relative_error_percent)
        max_relative_error = np.max(relative_error_percent)

        ratio_le_1 = np.mean(relative_error_percent <= 1) * 100.0
        ratio_le_5 = np.mean(relative_error_percent <= 5) * 100.0
        ratio_le_10 = np.mean(relative_error_percent <= 10) * 100.0
    else:
        ard = np.nan
        max_relative_error = np.nan
        ratio_le_1 = np.nan
        ratio_le_5 = np.nan
        ratio_le_10 = np.nan

    return {
        f"R2_{prefix}": r2,
        f"MSE_{prefix}": mse,
        f"RMSE_{prefix}": rmse,
        f"MAE_{prefix}": mae,
        f"ARD_{prefix}_percent": ard,
        f"max_abs_error_{prefix}": np.max(abs_error),
        f"max_relative_error_{prefix}_percent": max_relative_error,
        f"relative_error_{prefix}_le_1_percent_ratio": ratio_le_1,
        f"relative_error_{prefix}_le_5_percent_ratio": ratio_le_5,
        f"relative_error_{prefix}_le_10_percent_ratio": ratio_le_10,
    }


def calc_metrics(y_true_model_space, y_pred_model_space, dataset_name, seed, target_is_log=True):
    """
    如果 target_is_log=True:
        同时输出 lnViscosity 空间指标和 Viscosity=exp(lnViscosity) 空间指标。
    如果 target_is_log=False:
        只输出 Viscosity 原始空间指标。
    """
    y_true_model_space = np.asarray(y_true_model_space, dtype=float)
    y_pred_model_space = np.asarray(y_pred_model_space, dtype=float)

    out = {
        "seed": seed,
        "dataset": dataset_name,
        "n_points": len(y_true_model_space),
    }

    if target_is_log:
        out.update(
            calc_basic_metrics(
                y_true_model_space,
                y_pred_model_space,
                "lnViscosity"
            )
        )

        y_true_vis = safe_exp(y_true_model_space)
        y_pred_vis = safe_exp(y_pred_model_space)

        out.update(
            calc_basic_metrics(
                y_true_vis,
                y_pred_vis,
                "Viscosity"
            )
        )

    else:
        out.update(
            calc_basic_metrics(
                y_true_model_space,
                y_pred_model_space,
                "Viscosity"
            )
        )

    return out


# =========================================================
# 4. 读取数据
# =========================================================
df_desc = pd.read_excel(descriptor_file, sheet_name=descriptor_sheet)
df_data = pd.read_excel(data_file, sheet_name=data_sheet)

print("描述符表行数:", len(df_desc))
print("描述符表列数:", len(df_desc.columns))
print("Data_selected 行数:", len(df_data))
print("Data_selected 列数:", len(df_data.columns))


# =========================================================
# 5. 读取 25 个 selected descriptor 列名
# =========================================================
xls_desc = pd.ExcelFile(descriptor_file)

if selected_feature_sheet in xls_desc.sheet_names:
    df_selected = pd.read_excel(
        descriptor_file,
        sheet_name=selected_feature_sheet
    )

    if "selected_feature" not in df_selected.columns:
        raise ValueError(
            f"{selected_feature_sheet} 中没有 selected_feature 列。"
        )

    feature_cols = (
        df_selected["selected_feature"]
        .dropna()
        .astype(str)
        .tolist()
    )

    missing_features = [
        c for c in feature_cols
        if c not in df_desc.columns
    ]

    if len(missing_features) > 0:
        raise ValueError(
            "Selected_Features 中部分描述符不在 Selected_Features_Target 中。\n"
            f"缺失列: {missing_features}"
        )

else:
    metadata_cols = [
        "material_index",
        "original_material_index",
        "material_key",
        "compound_name",
        "cas",
        "formula",
        "SMILES",
        "smiles",
        "final_smiles",
        "inchikey",
        "InChIKey",
        "pubchem_cid",
        "CID",
        "phase",
        "boiling_T_K",
        "critical_T_K",
        "T_min",
        "T_max",
        "T_range",
        "n_points",
        "target_n_valid_points",
        "target_min_viscosity",
        "target_max_viscosity",
        "target_mean_viscosity",
    ]

    feature_cols = [
        c for c in df_desc.columns
        if c not in metadata_cols
    ]

    numeric_feature_cols = []

    for c in feature_cols:
        tmp = pd.to_numeric(df_desc[c], errors="coerce")
        if tmp.notna().sum() > 0:
            numeric_feature_cols.append(c)

    feature_cols = numeric_feature_cols

print("\n选取的描述符数量:", len(feature_cols))
print("描述符列名:")
for col in feature_cols:
    print(col)


# =========================================================
# 6. 数值化描述符
# =========================================================
df_features = df_desc[feature_cols].copy()
df_features = df_features.apply(pd.to_numeric, errors="coerce")

df_features = df_features.fillna(df_features.mean())
df_features = df_features.dropna(axis=1, how="any")

nonzero_mask = df_features.abs().sum(axis=0) != 0
used_feature_cols = df_features.columns[nonzero_mask].tolist()
removed_zero_feature_cols = df_features.columns[~nonzero_mask].tolist()

df_features = df_features[used_feature_cols].copy()

print("\n删除全零列后描述符数量:", len(used_feature_cols))
print("被删除的全零描述符数量:", len(removed_zero_feature_cols))


# =========================================================
# 7. 检查 temperature 和 viscosity 目标列
# =========================================================
temp_col = find_first_existing_col(
    df_data,
    temp_col_candidates,
    required=True,
    col_type="温度列"
)

viscosity_col = find_first_existing_col(
    df_data,
    viscosity_col_candidates,
    required=True,
    col_type="粘度目标列"
)

if force_target_is_log is None:
    target_is_log = infer_target_is_log(viscosity_col)
else:
    target_is_log = bool(force_target_is_log)

print("\n使用温度列:", temp_col)
print("使用粘度目标列:", viscosity_col)
print("目标是否按 lnViscosity 处理:", target_is_log)

df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
df_data[viscosity_col] = pd.to_numeric(df_data[viscosity_col], errors="coerce")


# =========================================================
# 8. 构造物质级描述符表
# =========================================================
df_desc_for_align = df_desc.copy()
df_desc_for_align[used_feature_cols] = df_features[used_feature_cols]

desc_key_col, data_key_col = choose_alignment_key(
    df_desc_for_align,
    df_data
)

data_group_col = choose_data_group_key(df_data)

print("\n描述符与原始数据对齐方式:")
print("desc_key_col:", desc_key_col)
print("data_key_col:", data_key_col)
print("data_group_col:", data_group_col)


# =========================================================
# 9. 构造长格式建模数据
# =========================================================
all_features = []
all_targets = []
material_ids = []
temp_values = []
original_row_indices = []

material_info_rows = []

# ---------- 情况 A：描述符表和 Data_selected 有共同 ID，可以直接对齐 ----------
if desc_key_col is not None and data_key_col is not None:
    df_desc_for_align["_align_key"] = df_desc_for_align[desc_key_col].apply(clean_key_value)
    df_data["_align_key"] = df_data[data_key_col].apply(clean_key_value)

    df_desc_for_align = df_desc_for_align.dropna(subset=["_align_key"]).copy()
    df_data = df_data.dropna(subset=["_align_key"]).copy()

    df_desc_for_align = df_desc_for_align.drop_duplicates(
        subset=["_align_key"],
        keep="first"
    )

    desc_map = {
        row["_align_key"]: row[used_feature_cols].values.astype(float)
        for _, row in df_desc_for_align.iterrows()
    }

    data_keys = df_data["_align_key"].drop_duplicates().tolist()

    matched_keys = [
        key for key in data_keys
        if key in desc_map
    ]

    material_key_to_index = {
        key: i
        for i, key in enumerate(matched_keys)
    }

    print("Data_selected 中物质 key 数:", len(data_keys))
    print("成功匹配描述符的物质数:", len(matched_keys))

    if len(matched_keys) == 0:
        raise ValueError(
            "使用 ID 对齐后没有任何物质匹配成功。"
            "请检查描述符文件和 viscosity 原始数据的 ID 列。"
        )

    for key in matched_keys:
        material_idx = material_key_to_index[key]

        sub = df_data[df_data["_align_key"] == key].copy()
        desc = desc_map[key]

        valid_point_count = 0

        for _, row in sub.iterrows():
            T = pd.to_numeric(row[temp_col], errors="coerce")
            y_val = pd.to_numeric(row[viscosity_col], errors="coerce")

            if not np.isfinite(T) or not np.isfinite(y_val):
                continue

            sample_features = np.concatenate([
                desc,
                np.array([T], dtype=float)
            ])

            all_features.append(sample_features)
            all_targets.append(y_val)
            material_ids.append(material_idx)
            temp_values.append(T)
            original_row_indices.append(row.name)

            valid_point_count += 1

        info = {
            "material_index": material_idx,
            "align_key": key,
            "n_points": len(sub),
            "n_valid_points": valid_point_count,
        }

        first_row = sub.iloc[0]

        for col in [
            "original_material_index",
            "material_key",
            "compound_name",
            "cas",
            "formula",
            "SMILES",
            "smiles",
            "final_smiles",
            "inchikey",
            "InChIKey",
            "pubchem_cid",
            "CID",
            "phase",
            "boiling_T_K",
            "critical_T_K",
            "T_min",
            "T_max",
            "T_range",
            "n_points",
        ]:
            if col in sub.columns:
                info[col] = first_row[col]

        material_info_rows.append(info)

# ---------- 情况 B：没有共同 ID，但 Data_selected 有物质分组列 ----------
else:
    if data_group_col is None:
        raise ValueError(
            "没有找到可用于物质分组的列。\n"
            "如果数据不是每个物质固定 8 个点，不能按每 8 行切分。\n"
            "请在 Data_selected 中保留 material_key 或 original_material_index。"
        )

    print(
        "没有可用于描述符和原始数据直接对齐的共同 ID，"
        f"但将使用 {data_group_col} 按物质分组，并按描述符表行顺序对齐。"
    )

    df_data["_group_key"] = df_data[data_group_col].apply(clean_key_value)
    df_data = df_data.dropna(subset=["_group_key"]).copy()

    group_keys = df_data["_group_key"].drop_duplicates().tolist()

    n_materials_data = len(group_keys)
    n_materials_desc = len(df_features)

    print("Data_selected 中物质数:", n_materials_data)
    print("描述符表中的物质数:", n_materials_desc)

    if n_materials_data != n_materials_desc:
        raise ValueError(
            "描述符表行数和 Data_selected 中的物质数不一致，无法按顺序对齐。\n"
            f"描述符表物质数 = {n_materials_desc}\n"
            f"Data_selected 物质数 = {n_materials_data}\n"
            "建议保留 material_key 或 original_material_index，使两个表可以按 ID 对齐。"
        )

    material_key_to_index = {
        key: i
        for i, key in enumerate(group_keys)
    }

    for key in group_keys:
        material_idx = material_key_to_index[key]

        sub = df_data[df_data["_group_key"] == key].copy()
        desc = df_features.iloc[material_idx].values.astype(float)

        valid_point_count = 0

        for _, row in sub.iterrows():
            T = pd.to_numeric(row[temp_col], errors="coerce")
            y_val = pd.to_numeric(row[viscosity_col], errors="coerce")

            if not np.isfinite(T) or not np.isfinite(y_val):
                continue

            sample_features = np.concatenate([
                desc,
                np.array([T], dtype=float)
            ])

            all_features.append(sample_features)
            all_targets.append(y_val)
            material_ids.append(material_idx)
            temp_values.append(T)
            original_row_indices.append(row.name)

            valid_point_count += 1

        info = {
            "material_index": material_idx,
            "align_key": key,
            "n_points": len(sub),
            "n_valid_points": valid_point_count,
        }

        first_row = sub.iloc[0]

        for col in [
            "original_material_index",
            "material_key",
            "compound_name",
            "cas",
            "formula",
            "SMILES",
            "smiles",
            "final_smiles",
            "inchikey",
            "InChIKey",
            "pubchem_cid",
            "CID",
            "phase",
            "boiling_T_K",
            "critical_T_K",
            "T_min",
            "T_max",
            "T_range",
            "n_points",
        ]:
            if col in sub.columns:
                info[col] = first_row[col]

        material_info_rows.append(info)


X = np.array(all_features, dtype=float)
y = np.array(all_targets, dtype=float)
material_ids = np.array(material_ids, dtype=int)
temp_values = np.array(temp_values, dtype=float)
original_row_indices = np.array(original_row_indices, dtype=int)

df_material_info = pd.DataFrame(material_info_rows)

model_feature_names = used_feature_cols + [temp_col]

print("\n最终样本点数:", X.shape[0])
print("最终输入特征数:", X.shape[1])
print("描述符特征数:", len(used_feature_cols))
print("温度特征数:", 1)
print("最终建模物质数:", len(np.unique(material_ids)))

if X.shape[0] == 0:
    raise ValueError(
        "没有构造出任何建模样本，请检查描述符和 viscosity 数据是否能对齐。"
    )

print("\n每个物质的数据点数量统计:")
print(df_material_info["n_valid_points"].describe())


# =========================================================
# 10. 100 个 seed 循环训练与评价
# =========================================================
unique_materials = np.unique(material_ids)

all_metrics_rows = []
split_rows = []
feature_importance_rows = []
prediction_rows = []

for seed in seed_list:
    print(f"\n========== Seed {seed} / {seed_list[-1]} ==========")

    train_materials, test_materials = train_test_split(
        unique_materials,
        test_size=test_size,
        random_state=seed
    )

    train_idx = np.isin(material_ids, train_materials)
    test_idx = np.isin(material_ids, test_materials)

    X_train = X[train_idx]
    X_test = X[test_idx]

    y_train = y[train_idx]
    y_test = y[test_idx]

    print("训练物质数:", len(train_materials))
    print("测试物质数:", len(test_materials))
    print("训练样本点数:", len(y_train))
    print("测试样本点数:", len(y_test))

    model = XGBRegressor(
        n_estimators=300,
        learning_rate=0.1,
        max_depth=6,
        random_state=model_random_state,
        verbosity=0,
        n_jobs=-1,
        objective="reg:squarederror"
    )

    model.fit(X_train, y_train)

    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)
    y_all_pred = model.predict(X)

    all_metrics_rows.append(
        calc_metrics(y_train, y_train_pred, "train", seed, target_is_log=target_is_log)
    )
    all_metrics_rows.append(
        calc_metrics(y_test, y_test_pred, "test", seed, target_is_log=target_is_log)
    )
    all_metrics_rows.append(
        calc_metrics(y, y_all_pred, "all", seed, target_is_log=target_is_log)
    )

    for m in train_materials:
        split_rows.append({
            "seed": seed,
            "material_index": int(m),
            "dataset": "train"
        })

    for m in test_materials:
        split_rows.append({
            "seed": seed,
            "material_index": int(m),
            "dataset": "test"
        })

    for feat, imp in zip(model_feature_names, model.feature_importances_):
        feature_importance_rows.append({
            "seed": seed,
            "feature_name": feat,
            "importance": imp
        })

    # 保存第一个 seed 的逐点预测，避免 Excel 过大
    if seed == seed_list[0]:
        if target_is_log:
            y_all_pred_vis = safe_exp(y_all_pred)
            y_true_vis = safe_exp(y)
        else:
            y_all_pred_vis = y_all_pred
            y_true_vis = y

        for i in range(len(y)):
            row = {
                "seed": seed,
                "material_index": int(material_ids[i]),
                "original_row_index": int(original_row_indices[i]),
                "Temperature": temp_values[i],
                "target_model_space_true": y[i],
                "target_model_space_pred": y_all_pred[i],
                "Abs_Error_model_space": abs(y_all_pred[i] - y[i]),
                "Viscosity_true": y_true_vis[i],
                "Viscosity_pred": y_all_pred_vis[i],
                "Abs_Error_Viscosity": abs(y_all_pred_vis[i] - y_true_vis[i]),
                "Relative_Error_Viscosity_%": (
                    abs((y_all_pred_vis[i] - y_true_vis[i]) / y_true_vis[i]) * 100
                    if abs(y_true_vis[i]) > 1e-12
                    else np.nan
                ),
                "dataset": "train" if train_idx[i] else "test"
            }

            prediction_rows.append(row)


df_metrics_all = pd.DataFrame(all_metrics_rows)
df_splits = pd.DataFrame(split_rows)
df_feature_importance_all = pd.DataFrame(feature_importance_rows)
df_predictions_seed0 = pd.DataFrame(prediction_rows)


# =========================================================
# 11. 统计平均指标
# =========================================================
metric_cols = [
    c for c in df_metrics_all.columns
    if c not in ["seed", "dataset", "n_points"]
]

summary_rows = []

for dataset_name, sub in df_metrics_all.groupby("dataset"):
    for metric in metric_cols:
        values = pd.to_numeric(sub[metric], errors="coerce")

        summary_rows.append({
            "dataset": dataset_name,
            "metric": metric,
            "mean": values.mean(),
            "std": values.std(),
            "min": values.min(),
            "median": values.median(),
            "max": values.max(),
        })

df_metrics_summary = pd.DataFrame(summary_rows)

df_metrics_summary_wide = (
    df_metrics_all
    .groupby("dataset")[metric_cols]
    .agg(["mean", "std", "min", "median", "max"])
)

df_metrics_summary_wide.columns = [
    f"{metric}_{stat}"
    for metric, stat in df_metrics_summary_wide.columns
]

df_metrics_summary_wide = df_metrics_summary_wide.reset_index()


# =========================================================
# 12. 单独整理 test 指标排名
# =========================================================
if target_is_log and "ARD_Viscosity_percent" in df_metrics_all.columns:
    sort_metric = "ARD_Viscosity_percent"
elif "ARD_Viscosity_percent" in df_metrics_all.columns:
    sort_metric = "ARD_Viscosity_percent"
else:
    sort_metric = "ARD_lnViscosity_percent"

df_test_metrics = (
    df_metrics_all[df_metrics_all["dataset"] == "test"]
    .copy()
    .sort_values(sort_metric, ascending=True)
    .reset_index(drop=True)
)

df_best_test = df_test_metrics.head(10).copy()
df_worst_test = df_test_metrics.tail(10).copy()


# =========================================================
# 13. 特征重要性平均
# =========================================================
df_feature_importance_summary = (
    df_feature_importance_all
    .groupby("feature_name")["importance"]
    .agg(["mean", "std", "min", "median", "max"])
    .reset_index()
    .sort_values("mean", ascending=False)
    .reset_index(drop=True)
)


# =========================================================
# 14. 物质进入测试集频率
# =========================================================
df_test_frequency = (
    df_splits[df_splits["dataset"] == "test"]
    .groupby("material_index")
    .size()
    .reset_index(name="test_count")
)

df_test_frequency["test_ratio"] = df_test_frequency["test_count"] / n_seeds

all_material_df = pd.DataFrame({
    "material_index": unique_materials.astype(int)
})

df_test_frequency = all_material_df.merge(
    df_test_frequency,
    on="material_index",
    how="left"
)

df_test_frequency["test_count"] = df_test_frequency["test_count"].fillna(0).astype(int)
df_test_frequency["test_ratio"] = df_test_frequency["test_ratio"].fillna(0.0)

if len(df_material_info) > 0:
    df_test_frequency = df_test_frequency.merge(
        df_material_info,
        on="material_index",
        how="left"
    )


# =========================================================
# 15. 保存 Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_metrics_all.to_excel(writer, sheet_name="Metrics_Per_Seed", index=False)
    df_metrics_summary.to_excel(writer, sheet_name="Metrics_Summary_Long", index=False)
    df_metrics_summary_wide.to_excel(writer, sheet_name="Metrics_Summary_Wide", index=False)

    df_test_metrics.to_excel(writer, sheet_name="Test_Metrics_All_Seeds", index=False)
    df_best_test.to_excel(writer, sheet_name="Best_10_Test", index=False)
    df_worst_test.to_excel(writer, sheet_name="Worst_10_Test", index=False)

    df_feature_importance_all.to_excel(writer, sheet_name="Feature_Importance_All", index=False)
    df_feature_importance_summary.to_excel(writer, sheet_name="Feature_Importance_Summary", index=False)

    df_splits.to_excel(writer, sheet_name="Splits_All_Seeds", index=False)
    df_test_frequency.to_excel(writer, sheet_name="Test_Frequency", index=False)

    df_predictions_seed0.to_excel(writer, sheet_name="Predictions_Seed0", index=False)
    df_material_info.to_excel(writer, sheet_name="Material_Info", index=False)

    pd.DataFrame({
        "used_descriptor": used_feature_cols
    }).to_excel(writer, sheet_name="Used_Descriptors", index=False)

    pd.DataFrame({
        "removed_zero_descriptor": removed_zero_feature_cols
    }).to_excel(writer, sheet_name="Removed_Zero_Descriptors", index=False)

    run_info = pd.DataFrame([
        {"item": "descriptor_file", "value": str(descriptor_file)},
        {"item": "descriptor_sheet", "value": descriptor_sheet},
        {"item": "selected_feature_sheet", "value": selected_feature_sheet},
        {"item": "data_file", "value": str(data_file)},
        {"item": "data_sheet", "value": data_sheet},
        {"item": "viscosity_col", "value": viscosity_col},
        {"item": "target_is_log", "value": target_is_log},
        {"item": "force_target_is_log", "value": force_target_is_log},
        {"item": "temp_col", "value": temp_col},
        {"item": "n_seeds", "value": n_seeds},
        {"item": "seed_start", "value": seed_start},
        {"item": "seed_end", "value": seed_list[-1]},
        {"item": "test_size", "value": test_size},
        {"item": "n_materials", "value": len(unique_materials)},
        {"item": "n_samples", "value": X.shape[0]},
        {"item": "n_descriptor_features", "value": len(used_feature_cols)},
        {"item": "n_total_features", "value": X.shape[1]},
        {"item": "alignment_desc_key_col", "value": desc_key_col},
        {"item": "alignment_data_key_col", "value": data_key_col},
        {"item": "data_group_col", "value": data_group_col},
        {"item": "model", "value": "XGBRegressor"},
        {"item": "model_random_state", "value": model_random_state},
        {"item": "n_estimators", "value": 300},
        {"item": "learning_rate", "value": 0.1},
        {"item": "max_depth", "value": 6},
        {"item": "note", "value": "viscosity model; features are 25 Mordred descriptors + temperature; variable number of points per material supported"},
    ])

    run_info.to_excel(writer, sheet_name="Run_Info", index=False)

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


# =========================================================
# 16. 终端打印核心结果
# =========================================================
print("\n================ 100 seed 平均评价指标 ================")
print(df_metrics_summary_wide.to_string(index=False))

print("\n================ 测试集核心指标 ================")
test_summary = df_metrics_summary_wide[
    df_metrics_summary_wide["dataset"] == "test"
]
print(test_summary.to_string(index=False))

print("\n保存完成:", output_file)