import pandas as pd
from pathlib import Path


# =========================================================
# 1. 输入输出文件
# =========================================================
input_file = Path("thermoml_vapor_pressure_Liquid_final_n8_T80_noSi.xlsx")
output_file = Path("thermoml_vapor_pressure_Liquid_final_n8_T80_noSi_remove_two.xlsx")

data_sheet_name = "Final_Selected_Data"
material_sheet_name = "Final_Materials"


# =========================================================
# 2. 要删除的物质
# =========================================================
target_names = {
    "methyl isocyanate",
    "carbon dioxide",
}

# 可选：用 CAS 辅助匹配，防止名称大小写或别名问题
target_cas = {
    "624-83-9",   # methyl isocyanate
    "124-38-9",   # carbon dioxide
}


# =========================================================
# 3. 读取数据
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
    raise ValueError("Final_Selected_Data 中没有 material_key 列。")

if "material_key" not in df_material.columns:
    raise ValueError("Final_Materials 中没有 material_key 列。")


# =========================================================
# 4. 在 Final_Materials 中定位要删除的物质
# =========================================================
def norm_text(x):
    if pd.isna(x):
        return ""
    return str(x).strip().lower()


remove_mask = pd.Series(False, index=df_material.index)

# 按 compound_name 精确匹配
if "compound_name" in df_material.columns:
    compound_name_norm = df_material["compound_name"].apply(norm_text)
    remove_mask |= compound_name_norm.isin(target_names)

    # 保险：如果名字中包含这些关键词，也删除
    for name in target_names:
        remove_mask |= compound_name_norm.str.contains(name, regex=False, na=False)

# 按 cas 匹配
if "cas" in df_material.columns:
    cas_norm = df_material["cas"].astype(str).str.strip()
    remove_mask |= cas_norm.isin(target_cas)

# 按 material_key 匹配
material_key_norm = df_material["material_key"].astype(str).str.strip().str.lower()
for name in target_names:
    remove_mask |= material_key_norm.str.contains(name, regex=False, na=False)

for cas in target_cas:
    remove_mask |= material_key_norm.str.contains(cas.lower(), regex=False, na=False)


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
    "T_range_current",
    "n_points_current",
]
show_cols = [c for c in show_cols if c in df_material_to_remove.columns]

print(df_material_to_remove[show_cols])


# =========================================================
# 5. 删除 Final_Selected_Data 和 Final_Materials 中对应物质
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
# 6. 保存新 Excel
# =========================================================
run_info = pd.DataFrame([
    {"item": "input_file", "value": str(input_file)},
    {"item": "output_file", "value": str(output_file)},
    {"item": "removed_target_names", "value": "; ".join(sorted(target_names))},
    {"item": "removed_target_cas", "value": "; ".join(sorted(target_cas))},
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

print("\n保存完成:", output_file)
print("最终可用于 vapor pressure 建模的 sheet: Final_Selected_Data")