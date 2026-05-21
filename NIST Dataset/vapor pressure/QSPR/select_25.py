import pandas as pd
import numpy as np
from pathlib import Path

from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import VarianceThreshold
from mlxtend.feature_selection import SequentialFeatureSelector as SFS


# =========================================================
# 1. 文件路径
# =========================================================
# 清理后的 vapor pressure Mordred 描述符文件
descriptor_file = Path("vp_descriptors_mordred_2d_cleaned.csv")

# 蒸汽压原始数据文件
vp_excel_file = Path("dataset_selected_by_two_k_with_lnP_invT_interpolation_8points.xlsx")

# 优先使用 Data_selected，因为它是一行一个温度点，包含原始 lnP / P 数值
vp_sheet_name = "Data_selected"

# 输出文件
output_excel = Path("selected_descriptors_with_vp_mean_target.xlsx")
output_txt = Path("selected_vp_descriptors.txt")


# =========================================================
# 2. 基本设置
# =========================================================
# 如果没有 material_key / original_material_index，才会退回每 8 行一个物质
n_points_per_material = 8

# 目标列候选
# 优先使用 lnP，因为你的文件名是 lnP_invT_interpolation
vp_target_col_candidates = [
    "lnP",
    "ln_P",
    "lnP_kPa",
    "lnP_value",
    "ln_pressure",
    "lnVaporPressure",
    "ln vapor pressure",
    "ln(P)",
    "ln_P_kPa",
    "property_value",
    "Vapor Pressure",
    "vapor pressure",
    "vapor_pressure",
    "P",
    "P_kPa",
    "pressure",
    "Pressure",
]

# 用于对齐物质的优先列
material_key_candidates = [
    "material_key",
    "original_material_index",
    "sdf_pubchem_cid",
    "CID_int",
    "pubchem_cid",
    "existing_pubchem_cid",
    "compound_name",
    "cas",
    "inchikey",
    "InChIKey",
    "smiles",
    "SMILES",
]

# 最终筛选描述符数量
k_features = 25

# 如果描述符很多，先用相关性预筛选到前 300 个，再做 SFS
use_correlation_prefilter = True
max_prefilter_features = 300

# SFS 交叉验证折数
cv = 5


# =========================================================
# 3. 工具函数
# =========================================================
def normalize_colname(name):
    return str(name).lower().replace(" ", "").replace("_", "").replace("-", "").replace("(", "").replace(")", "")


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
    清理物质 ID：
    123.0 -> '123'
    其他字符串保留。
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


def choose_alignment_key(df_desc, df_info):
    """
    优先用稳定 ID 对齐：
    material_key > original_material_index > CID/pubchem_cid > inchikey > cas > compound_name
    如果找不到共同列，则退回按行顺序对齐。
    """
    candidate_pairs = [
        ("material_key", "material_key"),
        ("original_material_index", "original_material_index"),
        ("CID_int", "pubchem_cid"),
        ("sdf_pubchem_cid", "pubchem_cid"),
        ("existing_pubchem_cid", "pubchem_cid"),
        ("inchikey", "inchikey"),
        ("inchikey_from_rdkit", "inchikey"),
        ("cas", "cas"),
        ("compound_name", "compound_name"),
    ]

    for desc_col, info_col in candidate_pairs:
        if desc_col in df_desc.columns and info_col in df_info.columns:
            return desc_col, info_col

    return None, None


# =========================================================
# 4. 读取描述符数据
# =========================================================
if not descriptor_file.exists():
    raise FileNotFoundError(
        f"没有找到描述符文件: {descriptor_file}\n"
        "请先完成 SDF -> Mordred 描述符提取和清理。"
    )

df_desc_raw = pd.read_csv(descriptor_file)

print("描述符表原始行数:", len(df_desc_raw))
print("描述符表原始列数:", len(df_desc_raw.columns))


# =========================================================
# 5. 读取蒸汽压原始数据
# =========================================================
if not vp_excel_file.exists():
    raise FileNotFoundError(f"没有找到蒸汽压原始数据文件: {vp_excel_file}")

xls = pd.ExcelFile(vp_excel_file)

if vp_sheet_name not in xls.sheet_names:
    raise ValueError(
        f"没有找到 sheet: {vp_sheet_name}\n"
        f"当前文件包含 sheet: {xls.sheet_names}"
    )

df_vp = pd.read_excel(vp_excel_file, sheet_name=vp_sheet_name)

print("VP Sheet 行数:", len(df_vp))
print("VP Sheet 列数:", len(df_vp.columns))

vp_target_col = find_first_existing_col(
    df_vp,
    vp_target_col_candidates,
    required=True,
    col_type="蒸汽压目标列"
)

print("使用蒸汽压目标列:", vp_target_col)

df_vp[vp_target_col] = pd.to_numeric(
    df_vp[vp_target_col],
    errors="coerce"
)


# =========================================================
# 6. 按物质计算蒸汽压平均目标值
#    对于 lnP 数据，推荐这里计算 mean lnP。
# =========================================================
if "material_key" in df_vp.columns:
    group_col = "material_key"
    df_vp[group_col] = df_vp[group_col].apply(clean_key_value)
    grouped = df_vp.groupby(group_col, sort=False)

    material_info_rows = []

    for material_idx, (key, sub) in enumerate(grouped):
        values = pd.to_numeric(sub[vp_target_col], errors="coerce").values.astype(float)
        valid_values = values[np.isfinite(values)]

        if len(valid_values) == 0:
            target_mean = np.nan
            target_min = np.nan
            target_max = np.nan
        else:
            target_mean = np.mean(valid_values)
            target_min = np.min(valid_values)
            target_max = np.max(valid_values)

        info = {
            "material_index": material_idx,
            "material_key": key,
            "target_mean_vp": target_mean,
            "target_n_valid_points": len(valid_values),
            "target_min_vp": target_min,
            "target_max_vp": target_max,
        }

        for col in [
            "original_material_index",
            "compound_name",
            "cas",
            "formula",
            "SMILES",
            "smiles",
            "inchikey",
            "InChIKey",
            "pubchem_cid",
            "phase",
            "boiling_T_K",
            "critical_T_K",
            "T_min",
            "T_max",
        ]:
            if col in df_vp.columns:
                info[col] = sub.iloc[0][col]

        material_info_rows.append(info)

    df_material_info = pd.DataFrame(material_info_rows)

elif "original_material_index" in df_vp.columns:
    group_col = "original_material_index"
    grouped = df_vp.groupby(group_col, sort=False)

    material_info_rows = []

    for material_idx, (key, sub) in enumerate(grouped):
        values = pd.to_numeric(sub[vp_target_col], errors="coerce").values.astype(float)
        valid_values = values[np.isfinite(values)]

        if len(valid_values) == 0:
            target_mean = np.nan
            target_min = np.nan
            target_max = np.nan
        else:
            target_mean = np.mean(valid_values)
            target_min = np.min(valid_values)
            target_max = np.max(valid_values)

        info = {
            "material_index": material_idx,
            "original_material_index": key,
            "target_mean_vp": target_mean,
            "target_n_valid_points": len(valid_values),
            "target_min_vp": target_min,
            "target_max_vp": target_max,
        }

        for col in [
            "material_key",
            "compound_name",
            "cas",
            "formula",
            "SMILES",
            "smiles",
            "inchikey",
            "InChIKey",
            "pubchem_cid",
            "phase",
            "boiling_T_K",
            "critical_T_K",
            "T_min",
            "T_max",
        ]:
            if col in df_vp.columns:
                info[col] = sub.iloc[0][col]

        material_info_rows.append(info)

    df_material_info = pd.DataFrame(material_info_rows)

else:
    if len(df_vp) % n_points_per_material != 0:
        raise ValueError(
            f"{vp_sheet_name} 行数 {len(df_vp)} 不能被 {n_points_per_material} 整除，"
            "且没有 material_key 或 original_material_index，无法确定每个物质。"
        )

    n_materials_vp = len(df_vp) // n_points_per_material
    print("按每 8 行一个物质处理，物质数:", n_materials_vp)

    material_info_rows = []

    for material_idx in range(n_materials_vp):
        start = material_idx * n_points_per_material
        end = start + n_points_per_material

        sub = df_vp.iloc[start:end].copy()

        values = pd.to_numeric(sub[vp_target_col], errors="coerce").values.astype(float)
        valid_values = values[np.isfinite(values)]

        if len(valid_values) == 0:
            target_mean = np.nan
            target_min = np.nan
            target_max = np.nan
        else:
            target_mean = np.mean(valid_values)
            target_min = np.min(valid_values)
            target_max = np.max(valid_values)

        info = {
            "material_index": material_idx,
            "target_mean_vp": target_mean,
            "target_n_valid_points": len(valid_values),
            "target_min_vp": target_min,
            "target_max_vp": target_max,
        }

        for col in [
            "material_key",
            "original_material_index",
            "compound_name",
            "cas",
            "formula",
            "SMILES",
            "smiles",
            "inchikey",
            "InChIKey",
            "pubchem_cid",
            "phase",
            "boiling_T_K",
            "critical_T_K",
            "T_min",
            "T_max",
        ]:
            if col in df_vp.columns:
                info[col] = sub.iloc[0][col]

        material_info_rows.append(info)

    df_material_info = pd.DataFrame(material_info_rows)

print("VP 数据中的物质数:", len(df_material_info))


# =========================================================
# 7. 对齐描述符表和 VP 目标表
# =========================================================
desc_key_col, info_key_col = choose_alignment_key(df_desc_raw, df_material_info)

if desc_key_col is not None and info_key_col is not None:
    print(f"使用键对齐描述符和 VP 目标: {desc_key_col} <-> {info_key_col}")

    df_desc_aligned = df_desc_raw.copy()
    df_material_info_aligned = df_material_info.copy()

    df_desc_aligned["_align_key"] = df_desc_aligned[desc_key_col].apply(clean_key_value)
    df_material_info_aligned["_align_key"] = df_material_info_aligned[info_key_col].apply(clean_key_value)

    df_desc_aligned = df_desc_aligned.dropna(subset=["_align_key"]).copy()
    df_material_info_aligned = df_material_info_aligned.dropna(subset=["_align_key"]).copy()

    df_desc_aligned = df_desc_aligned.drop_duplicates(subset=["_align_key"], keep="first")
    df_material_info_aligned = df_material_info_aligned.drop_duplicates(subset=["_align_key"], keep="first")

    df_merged = df_material_info_aligned.merge(
        df_desc_aligned,
        on="_align_key",
        how="inner",
        suffixes=("_target", "_desc")
    )

    if len(df_merged) == 0:
        raise ValueError(
            "使用键对齐后没有匹配到任何物质。"
            "请检查描述符表和 VP 原始表中的 ID 是否一致。"
        )

    print("对齐后物质数:", len(df_merged))

    target_info_cols = list(df_material_info_aligned.columns)

    desc_cols_all = [
        c for c in df_desc_raw.columns
        if c in df_merged.columns
    ]

    df_material_info_valid = df_merged[
        [c for c in target_info_cols if c in df_merged.columns]
    ].copy()

    df_desc_valid = df_merged[desc_cols_all].copy()

else:
    print("没有找到可用于对齐的共同 ID 列，退回按行顺序对齐。")

    if len(df_desc_raw) != len(df_material_info):
        raise ValueError(
            "描述符表行数和 VP 物质数不一致，且没有可用 ID 列对齐。\n"
            f"描述符表行数 = {len(df_desc_raw)}\n"
            f"VP 物质数 = {len(df_material_info)}"
        )

    df_desc_valid = df_desc_raw.copy().reset_index(drop=True)
    df_material_info_valid = df_material_info.copy().reset_index(drop=True)


# =========================================================
# 8. 删除目标值无效的物质
# =========================================================
y_all = pd.to_numeric(
    df_material_info_valid["target_mean_vp"],
    errors="coerce"
).values.astype(float)

valid_target_mask = np.isfinite(y_all)

df_desc_valid = df_desc_valid.loc[valid_target_mask].reset_index(drop=True)
df_material_info_valid = df_material_info_valid.loc[valid_target_mask].reset_index(drop=True)
y = y_all[valid_target_mask]

print("有效目标物质数:", len(y))
print("无效目标物质数:", int((~valid_target_mask).sum()))

if len(y) == 0:
    raise ValueError("没有有效 VP 平均目标值，无法筛选描述符。")


# =========================================================
# 9. 构造数值描述符矩阵
# =========================================================
metadata_candidates = [
    "source_sdf",
    "mol_index_in_file",
    "global_mol_index",
    "sdf_pubchem_cid",
    "CID_int",
    "compound_name",
    "cas",
    "formula",
    "inchikey",
    "smiles",
    "existing_pubchem_cid",
    "query_source",
    "query_identifier",
    "query_status",
    "canonical_smiles_from_sdf",
    "inchikey_from_rdkit",
    "PUBCHEM_COMPOUND_CID",
    "PUBCHEM_IUPAC_NAME",
    "PUBCHEM_MOLECULAR_FORMULA",
    "PUBCHEM_MOLECULAR_WEIGHT",
    "PUBCHEM_OPENEYE_CAN_SMILES",
    "PUBCHEM_OPENEYE_ISO_SMILES",
    "material_key",
    "original_material_index",
    "boiling_T_K",
    "critical_T_K",
    "T_min",
    "T_max",
    "n_points",
    "phase",
    "_align_key",
]

metadata_cols_desc = [
    c for c in metadata_candidates
    if c in df_desc_valid.columns
]

descriptor_candidate_cols = [
    c for c in df_desc_valid.columns
    if c not in metadata_cols_desc
]

df_numeric = df_desc_valid[descriptor_candidate_cols].apply(
    pd.to_numeric,
    errors="coerce"
)

df_numeric = df_numeric.replace([np.inf, -np.inf], np.nan)

# 删除全 NaN 列
df_numeric = df_numeric.dropna(axis=1, how="all")

# 均值填充缺失值
df_numeric = df_numeric.fillna(df_numeric.mean())

# 如果均值填充后仍有 NaN，说明该列有问题，删除
df_numeric = df_numeric.dropna(axis=1, how="any")

print("可用数值描述符列数:", df_numeric.shape[1])

if df_numeric.shape[1] == 0:
    raise ValueError("没有可用的数值描述符列。")


# =========================================================
# 10. 删除零方差描述符
# =========================================================
selector_var = VarianceThreshold(threshold=0.0)
X_var = selector_var.fit_transform(df_numeric)

kept_var_cols = df_numeric.columns[selector_var.get_support()].tolist()

df_X = pd.DataFrame(
    X_var,
    columns=kept_var_cols
)

print("删除零方差后描述符列数:", df_X.shape[1])


# =========================================================
# 11. 可选：相关性预筛选
# =========================================================
if use_correlation_prefilter and df_X.shape[1] > max_prefilter_features:
    corr_values = []

    for col in df_X.columns:
        x_col = df_X[col].values.astype(float)

        if np.std(x_col) < 1e-12:
            corr = 0.0
        else:
            corr = np.corrcoef(x_col, y)[0, 1]

            if not np.isfinite(corr):
                corr = 0.0

        corr_values.append(abs(corr))

    corr_series = pd.Series(corr_values, index=df_X.columns)

    preselected_cols = (
        corr_series
        .sort_values(ascending=False)
        .head(max_prefilter_features)
        .index
        .tolist()
    )

    df_X_for_sfs = df_X[preselected_cols].copy()

    print(
        f"相关性预筛选: {df_X.shape[1]} 个描述符 -> "
        f"{df_X_for_sfs.shape[1]} 个描述符"
    )

else:
    df_X_for_sfs = df_X.copy()
    preselected_cols = df_X_for_sfs.columns.tolist()

    print("未使用相关性预筛选。")


# =========================================================
# 12. 标准化
# =========================================================
scaler = StandardScaler()

X_scaled = pd.DataFrame(
    scaler.fit_transform(df_X_for_sfs),
    columns=df_X_for_sfs.columns
)


# =========================================================
# 13. 前向选择 SFS
# =========================================================
lr = LinearRegression()

if X_scaled.shape[1] <= k_features:
    selected_features = list(X_scaled.columns)
    print(
        f"候选描述符数量 {X_scaled.shape[1]} <= {k_features}，"
        "直接全部保留。"
    )

else:
    print("开始 SFS 前向选择...")
    print("候选描述符数量:", X_scaled.shape[1])
    print("目标选择数量:", k_features)

    sfs = SFS(
        lr,
        k_features=k_features,
        forward=True,
        floating=False,
        scoring="r2",
        cv=cv,
        n_jobs=-1
    )

    sfs = sfs.fit(X_scaled, y)

    selected_features = list(sfs.k_feature_names_)

print("\n最终选中描述符数量:", len(selected_features))
print("选中描述符:")
for feat in selected_features:
    print(feat)


# =========================================================
# 14. 保存选中描述符名称
# =========================================================
with open(output_txt, "w", encoding="utf-8") as f:
    for feat in selected_features:
        f.write(feat + "\n")

print("\n描述符名称已保存:", output_txt)


# =========================================================
# 15. 保存筛选后的数据
# =========================================================
result_df = df_X[selected_features].copy()

front_info_cols = [
    "material_index",
    "original_material_index",
    "material_key",
    "compound_name",
    "cas",
    "formula",
    "SMILES",
    "smiles",
    "inchikey",
    "InChIKey",
    "pubchem_cid",
    "phase",
    "boiling_T_K",
    "critical_T_K",
    "T_min",
    "T_max",
    "target_n_valid_points",
    "target_min_vp",
    "target_max_vp",
]

front_info_cols = [
    c for c in front_info_cols
    if c in df_material_info_valid.columns
]

df_output = pd.concat(
    [
        df_material_info_valid[front_info_cols].reset_index(drop=True),
        result_df.reset_index(drop=True),
        pd.DataFrame({"target_mean_vp": y})
    ],
    axis=1
)


# =========================================================
# 16. 保存详细信息
# =========================================================
df_selected_features = pd.DataFrame({
    "selected_feature": selected_features
})

df_preselected_features = pd.DataFrame({
    "preselected_feature": preselected_cols
})

df_summary = pd.DataFrame([
    {"item": "descriptor_file", "value": str(descriptor_file)},
    {"item": "vp_excel_file", "value": str(vp_excel_file)},
    {"item": "vp_sheet_name", "value": vp_sheet_name},
    {"item": "vp_target_col", "value": vp_target_col},
    {"item": "raw_descriptor_cols", "value": len(df_desc_raw.columns)},
    {"item": "numeric_descriptor_cols", "value": df_numeric.shape[1]},
    {"item": "after_variance_filter_cols", "value": df_X.shape[1]},
    {"item": "after_prefilter_cols", "value": df_X_for_sfs.shape[1]},
    {"item": "selected_feature_count", "value": len(selected_features)},
    {"item": "valid_material_count", "value": len(y)},
    {"item": "invalid_target_material_count", "value": int((~valid_target_mask).sum())},
    {"item": "use_correlation_prefilter", "value": use_correlation_prefilter},
    {"item": "max_prefilter_features", "value": max_prefilter_features},
    {"item": "cv", "value": cv},
    {"item": "alignment_desc_key_col", "value": desc_key_col},
    {"item": "alignment_info_key_col", "value": info_key_col},
])

with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
    df_output.to_excel(
        writer,
        sheet_name="Selected_Features_Target",
        index=False
    )

    df_selected_features.to_excel(
        writer,
        sheet_name="Selected_Features",
        index=False
    )

    df_preselected_features.to_excel(
        writer,
        sheet_name="Preselected_Features",
        index=False
    )

    df_material_info_valid.to_excel(
        writer,
        sheet_name="Material_Target_Info",
        index=False
    )

    df_summary.to_excel(
        writer,
        sheet_name="Summary",
        index=False
    )

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

print("\n保存完成:", output_excel)
print("选中特征 txt:", output_txt)