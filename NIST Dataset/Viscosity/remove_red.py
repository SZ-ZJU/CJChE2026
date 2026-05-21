import pandas as pd
from pathlib import Path


# =========================================================
# 1. 输入输出文件
# =========================================================
input_file = Path("thermoml_viscosity_Liquid_final_n8_Tgt30_noExcludedElements.xlsx")
output_file = Path("thermoml_viscosity_Liquid_final_n8_Tgt30_manual_remove3.xlsx")

data_sheet_name = "Final_Selected_Data"
material_sheet_name = "Final_Materials"


# =========================================================
# 2. 要删除的物质名称
# =========================================================
target_names = [
    "benzene phosphorus thiodichloride",
    "1-(2-azidoethyl)pyrrolidine",
    "1-octyl-3-methylpyridinium",
]

# 可选：如果实际 Excel 里的名称略有不同，可以在这里加别名
target_name_aliases = [
    "benzenephosphorus thiodichloride",
    "benzene phosphorus thiodichloride",
    "1-(2-azidoethyl)pyrrolidine",
    "1-octyl-3-methylpyridinium",
]


# =========================================================
# 3. 基础函数
# =========================================================
def norm_text(x):
    if pd.isna(x):
        return ""
    return str(x).strip().lower()


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
    如果表中没有 material_key，则自动生成。
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


# =========================================================
# 4. 读取 Excel
# =========================================================
if not input_file.exists():
    raise FileNotFoundError(f"没有找到输入文件: {input_file}")

xls = pd.ExcelFile(input_file)

print("输入文件包含的 sheet:")
print(xls.sheet_names)

if data_sheet_name not in xls.sheet_names:
    raise ValueError(f"没有找到 sheet: {data_sheet_name}")

if material_sheet_name not in xls.sheet_names:
    raise ValueError(f"没有找到 sheet: {material_sheet_name}")

df_data = pd.read_excel(input_file, sheet_name=data_sheet_name)
df_material = pd.read_excel(input_file, sheet_name=material_sheet_name)

if "material_key" not in df_data.columns:
    df_data["material_key"] = df_data.apply(build_material_key, axis=1)

if "material_key" not in df_material.columns:
    df_material["material_key"] = df_material.apply(build_material_key, axis=1)


# =========================================================
# 5. 在 Final_Materials 中定位要删除的物质
# =========================================================
target_terms = [norm_text(x) for x in target_name_aliases]

remove_mask = pd.Series(False, index=df_material.index)

# 1. compound_name 匹配
if "compound_name" in df_material.columns:
    name_norm = df_material["compound_name"].apply(norm_text)

    for term in target_terms:
        remove_mask |= name_norm.str.contains(term, regex=False, na=False)

# 2. pubchem_iupac_name 匹配
if "pubchem_iupac_name" in df_material.columns:
    iupac_norm = df_material["pubchem_iupac_name"].apply(norm_text)

    for term in target_terms:
        remove_mask |= iupac_norm.str.contains(term, regex=False, na=False)

# 3. material_key 匹配
material_key_norm = df_material["material_key"].apply(norm_text)

for term in target_terms:
    remove_mask |= material_key_norm.str.contains(term, regex=False, na=False)


df_material_to_remove = df_material[remove_mask].copy()

remove_material_keys = set(
    df_material_to_remove["material_key"].astype(str).str.strip()
)


print("\n========== 待删除物质 ==========")
print("待删除物质数:", len(remove_material_keys))

show_cols = [
    "material_key",
    "compound_name",
    "cas",
    "formula",
    "SMILES",
    "pubchem_iupac_name",
    "n_points_current",
    "T_range_current",
]

show_cols = [c for c in show_cols if c in df_material_to_remove.columns]

if len(df_material_to_remove) > 0:
    print(df_material_to_remove[show_cols])
else:
    print("没有匹配到目标物质。请检查 Excel 中 compound_name / pubchem_iupac_name 的实际写法。")


# =========================================================
# 6. 删除 Final_Selected_Data 和 Final_Materials 中对应物质
# =========================================================
df_data_filtered = df_data[
    ~df_data["material_key"].astype(str).str.strip().isin(remove_material_keys)
].copy()

df_material_filtered = df_material[
    ~df_material["material_key"].astype(str).str.strip().isin(remove_material_keys)
].copy()

df_data_removed = df_data[
    df_data["material_key"].astype(str).str.strip().isin(remove_material_keys)
].copy()

df_material_removed = df_material[
    df_material["material_key"].astype(str).str.strip().isin(remove_material_keys)
].copy()


print("\n========== 删除结果 ==========")
print("Final_Selected_Data 原始行数:", len(df_data))
print("Final_Selected_Data 删除后行数:", len(df_data_filtered))
print("Final_Selected_Data 删除行数:", len(df_data_removed))

print("\nFinal_Materials 原始物质数:", len(df_material))
print("Final_Materials 删除后物质数:", len(df_material_filtered))
print("Final_Materials 删除物质数:", len(df_material_removed))

print("\n删除后每个物质温度点数统计:")
print(df_data_filtered.groupby("material_key").size().value_counts().sort_index())


# =========================================================
# 7. 保存 Excel
# =========================================================
run_info = pd.DataFrame([
    {"item": "input_file", "value": str(input_file)},
    {"item": "output_file", "value": str(output_file)},
    {"item": "removed_target_names", "value": "; ".join(target_names)},
    {"item": "removed_materials", "value": len(remove_material_keys)},

    {"item": "Final_Selected_Data_original_rows", "value": len(df_data)},
    {"item": "Final_Selected_Data_filtered_rows", "value": len(df_data_filtered)},
    {"item": "Final_Selected_Data_removed_rows", "value": len(df_data_removed)},

    {"item": "Final_Materials_original_rows", "value": len(df_material)},
    {"item": "Final_Materials_filtered_rows", "value": len(df_material_filtered)},
    {"item": "Final_Materials_removed_rows", "value": len(df_material_removed)},
])

with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_data_filtered.to_excel(writer, sheet_name="Final_Selected_Data", index=False)
    df_material_filtered.to_excel(writer, sheet_name="Final_Materials", index=False)

    df_data_removed.to_excel(writer, sheet_name="Removed_Data_Rows", index=False)
    df_material_removed.to_excel(writer, sheet_name="Removed_Materials", index=False)

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


print("\n保存完成:", output_file)
print("最终可用于 viscosity 建模的 sheet: Final_Selected_Data")