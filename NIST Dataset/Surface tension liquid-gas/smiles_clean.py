import pandas as pd
from pathlib import Path


# =========================================================
# 1. 输入输出文件
# =========================================================
input_file = Path("thermoml_vapor_pressure_Liquid_with_PubChem_SMILES.xlsx")
input_sheet = "Data_With_SMILES"

output_file = Path("thermoml_vapor_pressure_Liquid_with_clean_SMILES.xlsx")


# =========================================================
# 2. 基本设置
# =========================================================
# 优先使用这个列作为最终 SMILES
smiles_col = "SMILES"

# 如果没有 SMILES 列，就按这个顺序找
smiles_candidate_cols = [
    "SMILES",
    "final_smiles",
    "pubchem_isomeric_smiles",
    "pubchem_canonical_smiles",
    "pubchem_connectivity_smiles",
    "pubchem_smiles",
    "smiles",
]


# =========================================================
# 3. 读取数据
# =========================================================
if not input_file.exists():
    raise FileNotFoundError(f"没有找到输入文件: {input_file}")

xls = pd.ExcelFile(input_file)

print("输入文件包含的 sheet:")
print(xls.sheet_names)

if input_sheet not in xls.sheet_names:
    raise ValueError(
        f"没有找到 sheet: {input_sheet}\n"
        f"当前文件中可用的 sheet 为: {xls.sheet_names}"
    )

df = pd.read_excel(input_file, sheet_name=input_sheet)

print("\n原始数据行数:", len(df))
print("原始列名:")
print(list(df.columns))


# =========================================================
# 4. 找到可用的 SMILES 列
# =========================================================
available_smiles_cols = [c for c in smiles_candidate_cols if c in df.columns]

if not available_smiles_cols:
    raise ValueError(
        "没有找到任何 SMILES 相关列。请检查 Excel 中是否存在 "
        "SMILES / final_smiles / pubchem_isomeric_smiles 等列。"
    )

if smiles_col not in df.columns:
    smiles_col = available_smiles_cols[0]
    print(f"\n没有找到 SMILES 列，改用 {smiles_col} 作为清洗依据。")
else:
    print(f"\n使用 {smiles_col} 作为清洗依据。")


# =========================================================
# 5. 自动生成 material_key
# =========================================================
def is_valid_value(x):
    if pd.isna(x):
        return False

    s = str(x).strip()

    if s == "":
        return False

    if s.lower() in ["nan", "none", "null", "待定"]:
        return False

    return True


def build_material_key(row):
    """
    优先级：
    1. inchikey
    2. cas
    3. compound_name
    4. formula
    """
    for col in ["inchikey", "cas", "compound_name", "formula"]:
        if col in row.index and is_valid_value(row[col]):
            return f"{col}:{str(row[col]).strip()}"

    return "unknown_material"


if "material_key" not in df.columns:
    df["material_key"] = df.apply(build_material_key, axis=1)


# =========================================================
# 6. 判断 SMILES 状态
# =========================================================
def check_smiles_status(smiles):
    """
    返回：
    keep
    empty_smiles
    smiles_contains_dot
    """
    if not is_valid_value(smiles):
        return "empty_smiles"

    s = str(smiles).strip()

    # 含有 "." 的通常是盐、离子对、混合物、多组分结构
    if "." in s:
        return "smiles_contains_dot"

    return "keep"


# =========================================================
# 7. 按物质整体判断是否删除
# =========================================================
material_rows = []

for material_key, group in df.groupby("material_key", sort=False):
    smiles_values = []

    for val in group[smiles_col].tolist():
        if is_valid_value(val):
            smiles_values.append(str(val).strip())

    # 去重但保持原顺序
    unique_smiles_values = list(dict.fromkeys(smiles_values))

    if len(unique_smiles_values) == 0:
        status = "empty_smiles"
        representative_smiles = None

    elif any("." in s for s in unique_smiles_values):
        status = "smiles_contains_dot"
        representative_smiles = "; ".join(unique_smiles_values)

    else:
        status = "keep"
        representative_smiles = unique_smiles_values[0]

    row = {
        "material_key": material_key,
        "n_rows": len(group),
        "smiles_status": status,
        "representative_smiles": representative_smiles,
        "n_unique_smiles": len(unique_smiles_values),
        "all_unique_smiles": "; ".join(unique_smiles_values),
    }

    for col in [
        "compound_name",
        "cas",
        "formula",
        "inchikey",
        "smiles",
        "pubchem_cid",
        "pubchem_molecular_formula",
        "pubchem_iupac_name",
        "pubchem_inchikey",
    ]:
        if col in group.columns:
            row[col] = group[col].iloc[0]

    material_rows.append(row)

df_material_check = pd.DataFrame(material_rows)


# =========================================================
# 8. 分成保留和删除
# =========================================================
kept_material_keys = df_material_check.loc[
    df_material_check["smiles_status"] == "keep",
    "material_key"
]

removed_material_keys = df_material_check.loc[
    df_material_check["smiles_status"] != "keep",
    "material_key"
]

df_kept = df[df["material_key"].isin(kept_material_keys)].copy()
df_removed = df[df["material_key"].isin(removed_material_keys)].copy()

df_removed = df_removed.merge(
    df_material_check[
        [
            "material_key",
            "smiles_status",
            "representative_smiles",
            "n_unique_smiles",
            "all_unique_smiles",
        ]
    ],
    on="material_key",
    how="left"
)

df_removed_materials = df_material_check[
    df_material_check["smiles_status"] != "keep"
].copy()

df_kept_materials = df_material_check[
    df_material_check["smiles_status"] == "keep"
].copy()


print("\n========== SMILES 清洗结果 ==========")
print("保留数据行数:", len(df_kept))
print("删除数据行数:", len(df_removed))
print("保留物质数:", df_kept["material_key"].nunique())
print("删除物质数:", df_removed["material_key"].nunique())

print("\n删除原因统计:")
print(df_removed_materials["smiles_status"].value_counts(dropna=False))


# =========================================================
# 9. 保存 Excel
# =========================================================
summary = pd.DataFrame([
    {"item": "input_file", "value": str(input_file)},
    {"item": "input_sheet", "value": input_sheet},
    {"item": "output_file", "value": str(output_file)},
    {"item": "smiles_col_used", "value": smiles_col},

    {"item": "original_rows", "value": len(df)},
    {"item": "original_materials", "value": df["material_key"].nunique()},

    {"item": "kept_rows", "value": len(df_kept)},
    {"item": "kept_materials", "value": df_kept["material_key"].nunique()},

    {"item": "removed_rows", "value": len(df_removed)},
    {"item": "removed_materials", "value": df_removed["material_key"].nunique()},

    {
        "item": "removed_empty_smiles_materials",
        "value": int((df_removed_materials["smiles_status"] == "empty_smiles").sum())
    },
    {
        "item": "removed_dot_smiles_materials",
        "value": int((df_removed_materials["smiles_status"] == "smiles_contains_dot").sum())
    },
])

with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_kept.to_excel(writer, sheet_name="Data_Clean_SMILES", index=False)
    df_kept_materials.to_excel(writer, sheet_name="Kept_Materials", index=False)
    df_removed_materials.to_excel(writer, sheet_name="Removed_Materials", index=False)
    df_removed.to_excel(writer, sheet_name="Removed_Rows", index=False)
    summary.to_excel(writer, sheet_name="Summary", index=False)

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


print("\n保存完成:", output_file)
print("最终可用于蒸气压建模的 sheet: Data_Clean_SMILES")