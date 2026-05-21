import pandas as pd
import numpy as np
from pathlib import Path


# =========================================================
# 1. 输入输出文件
# =========================================================
# 上一步 SDF -> Mordred 转化生成的文件
input_file = Path("vp_descriptors_mordred_2d.csv")

# 清理后的输出文件
output_csv = Path("vp_descriptors_mordred_2d_cleaned.csv")
output_excel = Path("vp_descriptors_mordred_2d_cleaned.xlsx")

# 缺失比例阈值：删除缺失比例 >= 30% 的描述符列
missing_threshold = 0.30


# =========================================================
# 2. 读取数据
# =========================================================
if not input_file.exists():
    raise FileNotFoundError(
        f"没有找到输入文件: {input_file}\n"
        "请先运行 SDF -> Mordred 描述符转化代码，生成 vp_descriptors_mordred_2d.csv。"
    )

df = pd.read_csv(input_file)

print("原始形状:", df.shape)


# =========================================================
# 3. 元信息列
#    这些列不作为 Mordred 描述符清理，但最终保留
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

    # 蒸汽压数据中可能有的额外信息
    "k1",
    "k2",
    "T_k1",
    "T_k2",
    "lnP_k1",
    "lnP_k2",
    "P_k1",
    "P_k2",
    "target_mean_lnP",
    "target_mean_P",
]

metadata_cols = [
    col for col in metadata_candidates
    if col in df.columns
]

descriptor_cols = [
    col for col in df.columns
    if col not in metadata_cols
]

metadata_df = df[metadata_cols].copy()
desc_df = df[descriptor_cols].copy()

print("元信息列数:", len(metadata_cols))
print("原始描述符列数:", len(descriptor_cols))


# =========================================================
# 4. 替换 inf / -inf 为 NaN
# =========================================================
desc_df = desc_df.replace([np.inf, -np.inf], np.nan)


# =========================================================
# 5. 删除缺失比例 >= 30% 的描述符列
# =========================================================
missing_ratio = desc_df.isnull().mean()

keep_missing_cols = missing_ratio[
    missing_ratio < missing_threshold
].index.tolist()

drop_high_missing_cols = missing_ratio[
    missing_ratio >= missing_threshold
].index.tolist()

desc_df = desc_df[keep_missing_cols].copy()

print("删除高缺失描述符列后:", desc_df.shape)
print("删除高缺失列数量:", len(drop_high_missing_cols))


# =========================================================
# 6. 一次性转成数值型
# =========================================================
desc_numeric = desc_df.apply(
    pd.to_numeric,
    errors="coerce"
)

desc_numeric = desc_numeric.replace([np.inf, -np.inf], np.nan)

# 删除转数值后全是 NaN 的列
valid_numeric_cols = desc_numeric.columns[
    desc_numeric.notna().sum(axis=0) > 0
].tolist()

drop_non_numeric_cols = [
    col for col in desc_numeric.columns
    if col not in valid_numeric_cols
]

desc_numeric = desc_numeric[valid_numeric_cols].copy()

print("删除非数值描述符列后:", desc_numeric.shape)
print("删除非数值列数量:", len(drop_non_numeric_cols))


# =========================================================
# 7. 删除零方差列
# =========================================================
var_series = desc_numeric.var(axis=0, skipna=True)

keep_var_cols = var_series[
    (var_series.notna()) & (var_series > 0)
].index.tolist()

drop_zero_var_cols = [
    col for col in desc_numeric.columns
    if col not in keep_var_cols
]

desc_clean = desc_numeric[keep_var_cols].copy()

print("删除零方差列后:", desc_clean.shape)
print("删除零方差列数量:", len(drop_zero_var_cols))


# =========================================================
# 8. 合并元信息列 + 清理后的描述符列
# =========================================================
df_clean = pd.concat(
    [
        metadata_df.reset_index(drop=True),
        desc_clean.reset_index(drop=True)
    ],
    axis=1
)

print("最终清理后形状:", df_clean.shape)


# =========================================================
# 9. 删除列报告
# =========================================================
drop_report = pd.DataFrame({
    "column": (
        drop_high_missing_cols
        + drop_non_numeric_cols
        + drop_zero_var_cols
    ),
    "reason": (
        ["missing_ratio_ge_30pct"] * len(drop_high_missing_cols)
        + ["non_numeric_after_conversion"] * len(drop_non_numeric_cols)
        + ["zero_variance"] * len(drop_zero_var_cols)
    )
})


# =========================================================
# 10. 汇总信息
# =========================================================
summary = pd.DataFrame([
    {"item": "input_file", "value": str(input_file)},
    {"item": "original_shape", "value": str(df.shape)},
    {"item": "metadata_cols", "value": len(metadata_cols)},
    {"item": "original_descriptor_cols", "value": len(descriptor_cols)},
    {"item": "missing_threshold", "value": missing_threshold},
    {"item": "dropped_high_missing_cols", "value": len(drop_high_missing_cols)},
    {"item": "dropped_non_numeric_cols", "value": len(drop_non_numeric_cols)},
    {"item": "dropped_zero_variance_cols", "value": len(drop_zero_var_cols)},
    {"item": "final_shape", "value": str(df_clean.shape)},
    {"item": "final_descriptor_cols", "value": desc_clean.shape[1]},
])


# =========================================================
# 11. 保存结果
# =========================================================
df_clean.to_csv(
    output_csv,
    index=False,
    encoding="utf-8-sig"
)

with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
    df_clean.to_excel(
        writer,
        sheet_name="cleaned_descriptors",
        index=False
    )

    metadata_df.to_excel(
        writer,
        sheet_name="metadata",
        index=False
    )

    drop_report.to_excel(
        writer,
        sheet_name="dropped_columns",
        index=False
    )

    summary.to_excel(
        writer,
        sheet_name="summary",
        index=False
    )

    # 设置 Excel 数值格式，避免科学计数法显示过多
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

            ws.column_dimensions[col_letter].width = min(max_length + 2, 45)

print("\n清理完成。")
print(f"CSV 已保存: {output_csv}")
print(f"Excel 已保存: {output_excel}")
print(f"最终保留描述符数量: {desc_clean.shape[1]}")