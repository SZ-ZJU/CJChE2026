import pandas as pd
import numpy as np
from pathlib import Path


# =========================================================
# 1. 输入输出文件
# =========================================================
input_file = Path("density_descriptors_mordred_2d.csv")

output_csv = Path("density_descriptors_mordred_2d_cleaned.csv")
output_excel = Path("density_descriptors_mordred_2d_cleaned.xlsx")

missing_threshold = 0.30


# =========================================================
# 2. 读取数据
# =========================================================
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
    "material_key",
    "original_material_index",
    "boiling_T_K",
    "critical_T_K",
    "T_min",
    "T_max",
    "n_points",
    "phase",
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
# 4. 删除缺失比例 >= 30% 的描述符列
# =========================================================
missing_ratio = desc_df.isnull().mean()

keep_missing_cols = missing_ratio[missing_ratio < missing_threshold].index.tolist()
drop_high_missing_cols = missing_ratio[missing_ratio >= missing_threshold].index.tolist()

desc_df = desc_df[keep_missing_cols].copy()

print("删除高缺失描述符列后:", desc_df.shape)
print("删除高缺失列数量:", len(drop_high_missing_cols))


# =========================================================
# 5. 一次性转成数值型，避免 DataFrame 碎片化警告
# =========================================================
desc_numeric = desc_df.apply(
    pd.to_numeric,
    errors="coerce"
)

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
# 6. 删除零方差列
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
# 7. 合并元信息列 + 清理后的描述符列
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
# 8. 删除列报告
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
# 9. 汇总信息
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
# 10. 保存结果
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

print("\n清理完成。")
print(f"CSV 已保存: {output_csv}")
print(f"Excel 已保存: {output_excel}")
print(f"最终保留描述符数量: {desc_clean.shape[1]}")