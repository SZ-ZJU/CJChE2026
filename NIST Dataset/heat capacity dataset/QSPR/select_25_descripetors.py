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
descriptor_file = Path("describe_word_cleaned.csv")

cp_excel_file = Path("Cp_dataset_selected_by_two_k_with_interpolation.xlsx")
cp_sheet_name = "Sheet1_selected"

output_excel = Path("selected_descriptors_with_Cp_mean_target.xlsx")
output_txt = Path("selected_descriptors.txt")


# =========================================================
# 2. 基本设置
# =========================================================
n_points_per_material = 8

target_col = "property_value"

k_features = 25

# 如果描述符有几千个，直接 SFS 会非常慢。
# 建议先用相关性预筛选到前 300 个，再做 SFS。
# 如果你想完全按照原始代码，对所有描述符做 SFS，把它改成 False。
use_correlation_prefilter = True
max_prefilter_features = 300

cv = 5


# =========================================================
# 3. 读取描述符数据
# =========================================================
df_desc_raw = pd.read_csv(descriptor_file)

print("描述符表原始行数:", len(df_desc_raw))
print("描述符表原始列数:", len(df_desc_raw.columns))


# =========================================================
# 4. 读取 Cp 数据，并按每 8 行计算一个物质的平均 property_value
# =========================================================
df_cp = pd.read_excel(cp_excel_file, sheet_name=cp_sheet_name)

print("Cp Sheet 行数:", len(df_cp))

if target_col not in df_cp.columns:
    raise ValueError(f"{cp_sheet_name} 中没有找到目标列: {target_col}")

if len(df_cp) % n_points_per_material != 0:
    raise ValueError(
        f"{cp_sheet_name} 行数 {len(df_cp)} 不能被 {n_points_per_material} 整除。"
        "请检查是否每个物质都是 8 行。"
    )

n_materials_cp = len(df_cp) // n_points_per_material
print("Cp 数据中的物质数:", n_materials_cp)

target_means = []

material_info_rows = []

for material_idx in range(n_materials_cp):
    start = material_idx * n_points_per_material
    end = start + n_points_per_material

    sub = df_cp.iloc[start:end].copy()

    values = pd.to_numeric(sub[target_col], errors="coerce").values.astype(float)

    if np.isfinite(values).sum() == 0:
        target_mean = np.nan
    else:
        target_mean = np.nanmean(values)

    target_means.append(target_mean)

    info = {
        "material_index": material_idx,
        "target_mean": target_mean,
        "target_n_valid_points": int(np.isfinite(values).sum()),
        "target_min": np.nanmin(values) if np.isfinite(values).sum() > 0 else np.nan,
        "target_max": np.nanmax(values) if np.isfinite(values).sum() > 0 else np.nan,
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
        "material_key",
        "phase",
        "boiling_T_K",
        "critical_T_K",
    ]:
        if col in df_cp.columns:
            info[col] = sub.iloc[0][col]

    material_info_rows.append(info)

y_all = np.array(target_means, dtype=float)
df_material_info = pd.DataFrame(material_info_rows)


# =========================================================
# 5. 检查描述符行数是否和物质数一致
# =========================================================
if len(df_desc_raw) != n_materials_cp:
    raise ValueError(
        "描述符表行数和 Cp 物质数不一致。\n"
        f"describe_word_cleaned.csv 行数 = {len(df_desc_raw)}\n"
        f"Cp 数据物质数 = {n_materials_cp}\n"
        "当前代码默认描述符表每一行和 Cp 数据每个物质按顺序一一对应。"
    )


# =========================================================
# 6. 删除目标值无效的物质
# =========================================================
valid_target_mask = np.isfinite(y_all)

df_desc_valid = df_desc_raw.loc[valid_target_mask].reset_index(drop=True)
df_material_info_valid = df_material_info.loc[valid_target_mask].reset_index(drop=True)
y = y_all[valid_target_mask]

print("有效目标物质数:", len(y))
print("无效目标物质数:", int((~valid_target_mask).sum()))

if len(y) == 0:
    raise ValueError("没有有效目标值，无法筛选描述符。")


# =========================================================
# 7. 构造数值描述符矩阵
# =========================================================
# 将所有列尝试转成数值，非数值列会变成 NaN
df_numeric = df_desc_valid.apply(pd.to_numeric, errors="coerce")

# 删除全 NaN 列
df_numeric = df_numeric.dropna(axis=1, how="all")

# 删除缺失率太高的列，可选
# 这里先不强制删除，只用均值填充
missing_ratio = df_numeric.isna().mean()

# 均值填充
df_numeric = df_numeric.fillna(df_numeric.mean())

# 如果某些列均值仍然是 NaN，说明整列无有效值，删除
df_numeric = df_numeric.dropna(axis=1, how="any")

print("数值描述符列数:", df_numeric.shape[1])

if df_numeric.shape[1] == 0:
    raise ValueError("没有可用的数值描述符列。")


# =========================================================
# 8. 删除零方差描述符
# =========================================================
selector_var = VarianceThreshold(threshold=0.0)
X_var = selector_var.fit_transform(df_numeric)

kept_var_cols = df_numeric.columns[selector_var.get_support()].tolist()

df_X = pd.DataFrame(X_var, columns=kept_var_cols)

print("删除零方差后描述符列数:", df_X.shape[1])


# =========================================================
# 9. 可选：相关性预筛选
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
# 10. 标准化
# =========================================================
scaler = StandardScaler()

X_scaled = pd.DataFrame(
    scaler.fit_transform(df_X_for_sfs),
    columns=df_X_for_sfs.columns
)


# =========================================================
# 11. 前向选择 SFS
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
# 12. 保存选中描述符名称
# =========================================================
with open(output_txt, "w", encoding="utf-8") as f:
    for feat in selected_features:
        f.write(feat + "\n")

print("\n描述符名称已保存:", output_txt)


# =========================================================
# 13. 保存筛选后的数据
# =========================================================
# 使用未标准化、但已完成缺失填充和零方差删除后的描述符值
result_df = df_X[selected_features].copy()

# 加入物质信息
front_info_cols = [
    "material_index",
    "original_material_index",
    "compound_name",
    "cas",
    "formula",
    "SMILES",
    "smiles",
    "inchikey",
    "InChIKey",
    "pubchem_cid",
    "material_key",
    "phase",
    "boiling_T_K",
    "critical_T_K",
]

front_info_cols = [c for c in front_info_cols if c in df_material_info_valid.columns]

df_output = pd.concat(
    [
        df_material_info_valid[front_info_cols].reset_index(drop=True),
        result_df.reset_index(drop=True),
        pd.DataFrame({"target_mean": y})
    ],
    axis=1
)


# =========================================================
# 14. 保存详细信息
# =========================================================
df_selected_features = pd.DataFrame({
    "selected_feature": selected_features
})

df_preselected_features = pd.DataFrame({
    "preselected_feature": preselected_cols
})

df_removed_info = pd.DataFrame([
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
])

with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
    df_output.to_excel(writer, sheet_name="Selected_Features_Target", index=False)
    df_selected_features.to_excel(writer, sheet_name="Selected_Features", index=False)
    df_preselected_features.to_excel(writer, sheet_name="Preselected_Features", index=False)
    df_material_info_valid.to_excel(writer, sheet_name="Material_Target_Info", index=False)
    df_removed_info.to_excel(writer, sheet_name="Summary", index=False)

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