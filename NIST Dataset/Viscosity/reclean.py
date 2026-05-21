import pandas as pd
import numpy as np
from pathlib import Path


# =========================================================
# 1. 输入输出文件
# =========================================================
input_file = Path("thermoml_viscosity_Liquid_final_n8_Tgt30_manual_remove3_with_Tb.xlsx")
output_file = Path("thermoml_viscosity_Liquid_final_n8_Tgt30_manual_remove3_with_Tb_cleaned.xlsx")

material_sheet = "Material_with_Tb"
data_sheet = "Data_with_Tb"

tb_col = "boiling_T_K"

# 是否要求 Tb > 0
# 一般沸点必须为正，所以建议保持 True
require_positive_tb = True

# 如果你后面想手动删除某些 InChIKey，可以填在这里
manual_remove_inchikeys = {
    # "XXXXXXXXXXXXXX-XXXXXXXXXX-X",
}


# =========================================================
# 2. 工具函数
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


def find_col(df, candidates):
    lower_map = {str(c).lower(): c for c in df.columns}

    for c in candidates:
        if c in df.columns:
            return c

    for c in candidates:
        if c.lower() in lower_map:
            return lower_map[c.lower()]

    return None


def build_material_key(row):
    """
    构造物质唯一标识。
    优先级：
    1. material_key
    2. inchikey / InChIKey
    3. cas
    4. compound_name
    5. formula
    """
    for col in [
        "material_key",
        "inchikey",
        "InChIKey",
        "inchi_key",
        "pubchem_inchikey",
        "cas",
        "compound_name",
        "formula",
    ]:
        if col in row.index and is_valid_value(row[col]):
            if col == "material_key":
                return str(row[col]).strip()

            return f"{col}:{str(row[col]).strip()}"

    return "unknown_material"


def normalize_inchikey(x):
    if not is_valid_value(x):
        return None

    return str(x).strip().upper()


def make_tb_valid_mask(series):
    """
    判断 Tb 是否有效。
    """
    tb = pd.to_numeric(series, errors="coerce")

    mask = tb.notna() & np.isfinite(tb)

    if require_positive_tb:
        mask = mask & (tb > 0)

    return mask


# =========================================================
# 3. 读取 Excel
# =========================================================
if not input_file.exists():
    raise FileNotFoundError(f"没有找到输入文件: {input_file}")

xls = pd.ExcelFile(input_file)

print("输入文件包含的 sheet:")
print(xls.sheet_names)

if material_sheet not in xls.sheet_names:
    raise ValueError(
        f"没有找到 sheet: {material_sheet}\n"
        f"当前文件中的 sheet 为: {xls.sheet_names}"
    )

if data_sheet not in xls.sheet_names:
    raise ValueError(
        f"没有找到 sheet: {data_sheet}\n"
        f"当前文件中的 sheet 为: {xls.sheet_names}"
    )

df_material = pd.read_excel(input_file, sheet_name=material_sheet)
df_data = pd.read_excel(input_file, sheet_name=data_sheet)

print("\nMaterial_with_Tb 行数:", len(df_material))
print("Data_with_Tb 行数:", len(df_data))

if tb_col not in df_material.columns:
    raise ValueError(f"{material_sheet} 中没有找到列: {tb_col}")

if tb_col not in df_data.columns:
    print(f"提示：{data_sheet} 中没有 {tb_col} 列，这不影响按 Material 表筛选。")


# =========================================================
# 4. 构造 material_key
# =========================================================
if "material_key" not in df_material.columns:
    df_material["material_key"] = df_material.apply(build_material_key, axis=1)

if "material_key" not in df_data.columns:
    df_data["material_key"] = df_data.apply(build_material_key, axis=1)

df_material["material_key"] = df_material["material_key"].astype(str).str.strip()
df_data["material_key"] = df_data["material_key"].astype(str).str.strip()

if (df_material["material_key"] == "unknown_material").any():
    print("警告：Material_with_Tb 中存在 unknown_material。请检查物质标识列。")

if (df_data["material_key"] == "unknown_material").any():
    print("警告：Data_with_Tb 中存在 unknown_material。请检查物质标识列。")


# =========================================================
# 5. 找 InChIKey 列
# =========================================================
inchikey_col = find_col(
    df_material,
    [
        "inchikey",
        "InChIKey",
        "inchi_key",
        "pubchem_inchikey",
        "PubChem_InChIKey",
    ]
)

print("\n识别到的 InChIKey 列:", inchikey_col)


# =========================================================
# 6. 找出要删除的物质
# =========================================================
df_material[tb_col] = pd.to_numeric(df_material[tb_col], errors="coerce")

remove_reason_rows = []

# ---------- 6.1 删除 boiling_T_K 为空 / 无效的物质 ----------
valid_tb_mask = make_tb_valid_mask(df_material[tb_col])
invalid_tb_mask = ~valid_tb_mask

for _, row in df_material.loc[invalid_tb_mask].iterrows():
    remove_reason_rows.append({
        "material_key": row["material_key"],
        "remove_reason": "invalid_or_empty_boiling_T_K",
        "boiling_T_K": row.get(tb_col, np.nan),
        "Tb_status": row.get("Tb_status", None),
        "inchikey": row.get(inchikey_col, None) if inchikey_col else None,
        "compound_name": row.get("compound_name", None),
        "cas": row.get("cas", None),
        "formula": row.get("formula", None),
        "pubchem_cid_for_Tb": row.get("pubchem_cid_for_Tb", None),
        "boiling_T_count": row.get("boiling_T_count", None),
        "boiling_T_raw_examples": row.get("boiling_T_raw_examples", None),
    })


# ---------- 6.2 手动删除指定 InChIKey，可选 ----------
if len(manual_remove_inchikeys) > 0:
    if inchikey_col is not None:
        inchikey_norm = df_material[inchikey_col].apply(normalize_inchikey)
        manual_mask = inchikey_norm.isin(
            {normalize_inchikey(x) for x in manual_remove_inchikeys}
        )

        for _, row in df_material.loc[manual_mask].iterrows():
            remove_reason_rows.append({
                "material_key": row["material_key"],
                "remove_reason": "manual_remove_inchikey",
                "boiling_T_K": row.get(tb_col, np.nan),
                "Tb_status": row.get("Tb_status", None),
                "inchikey": row.get(inchikey_col, None),
                "compound_name": row.get("compound_name", None),
                "cas": row.get("cas", None),
                "formula": row.get("formula", None),
                "pubchem_cid_for_Tb": row.get("pubchem_cid_for_Tb", None),
                "boiling_T_count": row.get("boiling_T_count", None),
                "boiling_T_raw_examples": row.get("boiling_T_raw_examples", None),
            })

    else:
        print("警告：没有识别到 InChIKey 列，无法按指定 InChIKey 手动删除。")


df_removed_materials = pd.DataFrame(remove_reason_rows)

if len(df_removed_materials) > 0:
    df_removed_materials = df_removed_materials.drop_duplicates(
        subset=["material_key", "remove_reason"]
    ).reset_index(drop=True)

remove_material_keys = set(df_removed_materials["material_key"].dropna().astype(str))

print("\n需要删除的物质数:", len(remove_material_keys))

if len(df_removed_materials) > 0:
    print("\n删除原因统计:")
    print(df_removed_materials["remove_reason"].value_counts())


# =========================================================
# 7. 同步删除 Material 和 Data
# =========================================================
df_material_clean = df_material[
    ~df_material["material_key"].astype(str).isin(remove_material_keys)
].copy()

df_material_removed_rows = df_material[
    df_material["material_key"].astype(str).isin(remove_material_keys)
].copy()

df_data_clean = df_data[
    ~df_data["material_key"].astype(str).isin(remove_material_keys)
].copy()

df_data_removed_rows = df_data[
    df_data["material_key"].astype(str).isin(remove_material_keys)
].copy()


print("\n========== 删除结果 ==========")
print("Material 原始物质数:", len(df_material))
print("Material 删除物质数:", len(df_material_removed_rows))
print("Material 保留物质数:", len(df_material_clean))

print("Data 原始数据点数:", len(df_data))
print("Data 删除数据点数:", len(df_data_removed_rows))
print("Data 保留数据点数:", len(df_data_clean))


# =========================================================
# 8. 检查 Data 和 Material 是否还能对应
# =========================================================
material_keys_clean = set(df_material_clean["material_key"].astype(str))
data_keys_clean = set(df_data_clean["material_key"].astype(str))

keys_in_data_not_material = data_keys_clean - material_keys_clean
keys_in_material_not_data = material_keys_clean - data_keys_clean

print("\n========== 对应关系检查 ==========")
print("Data 中存在但 Material 中不存在的物质数:", len(keys_in_data_not_material))
print("Material 中存在但 Data 中不存在的物质数:", len(keys_in_material_not_data))

df_key_check = pd.DataFrame({
    "check_item": [
        "keys_in_data_not_material",
        "keys_in_material_not_data",
    ],
    "n_keys": [
        len(keys_in_data_not_material),
        len(keys_in_material_not_data),
    ],
    "keys_examples": [
        "; ".join(list(keys_in_data_not_material)[:20]),
        "; ".join(list(keys_in_material_not_data)[:20]),
    ]
})


# =========================================================
# 9. 点数统计
# =========================================================
df_point_count_before = (
    df_data
    .groupby("material_key")
    .size()
    .reset_index(name="n_points_before")
)

df_point_count_after = (
    df_data_clean
    .groupby("material_key")
    .size()
    .reset_index(name="n_points_after")
)

df_point_count = df_point_count_before.merge(
    df_point_count_after,
    on="material_key",
    how="left"
)

df_point_count["n_points_after"] = df_point_count["n_points_after"].fillna(0).astype(int)

print("\n========== 清洗后每个物质点数统计 ==========")
if len(df_data_clean) > 0:
    print(df_data_clean.groupby("material_key").size().value_counts().sort_index())
else:
    print("Data 清洗后为空。")


# =========================================================
# 10. 尝试复制其他辅助 sheet
# =========================================================
optional_sheet_names = [
    "PubChem_Raw_Tb_Values",
    "Failed_or_NotFound",
    "Summary",
]

optional_sheets = {}

for sheet in optional_sheet_names:
    if sheet in xls.sheet_names:
        try:
            optional_sheets[sheet] = pd.read_excel(input_file, sheet_name=sheet)
        except Exception as e:
            print(f"读取辅助 sheet 失败: {sheet}, error={e}")


# =========================================================
# 11. 生成 Summary
# =========================================================
summary = pd.DataFrame([
    {"item": "input_file", "value": str(input_file)},
    {"item": "output_file", "value": str(output_file)},
    {"item": "material_sheet", "value": material_sheet},
    {"item": "data_sheet", "value": data_sheet},
    {"item": "tb_col", "value": tb_col},
    {"item": "require_positive_tb", "value": require_positive_tb},
    {"item": "inchikey_col", "value": inchikey_col},
    {"item": "manual_remove_inchikeys", "value": "; ".join(sorted(manual_remove_inchikeys))},

    {"item": "material_original_rows", "value": len(df_material)},
    {"item": "material_removed_rows", "value": len(df_material_removed_rows)},
    {"item": "material_clean_rows", "value": len(df_material_clean)},

    {"item": "data_original_rows", "value": len(df_data)},
    {"item": "data_removed_rows", "value": len(df_data_removed_rows)},
    {"item": "data_clean_rows", "value": len(df_data_clean)},

    {"item": "removed_materials_total", "value": len(remove_material_keys)},
    {
        "item": "removed_invalid_or_empty_boiling_T_K_materials",
        "value": int((df_removed_materials["remove_reason"] == "invalid_or_empty_boiling_T_K").sum())
        if len(df_removed_materials) > 0 else 0
    },
    {
        "item": "removed_manual_inchikey_materials",
        "value": int((df_removed_materials["remove_reason"] == "manual_remove_inchikey").sum())
        if len(df_removed_materials) > 0 else 0
    },
    {"item": "keys_in_data_not_material_after_clean", "value": len(keys_in_data_not_material)},
    {"item": "keys_in_material_not_data_after_clean", "value": len(keys_in_material_not_data)},
])


# =========================================================
# 12. 保存新的 Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_data_clean.to_excel(writer, sheet_name="Data_with_Tb_cleaned", index=False)
    df_material_clean.to_excel(writer, sheet_name="Material_with_Tb_cleaned", index=False)

    df_removed_materials.to_excel(writer, sheet_name="Removed_Materials", index=False)
    df_data_removed_rows.to_excel(writer, sheet_name="Removed_Data_Rows", index=False)
    df_material_removed_rows.to_excel(writer, sheet_name="Removed_Material_Rows", index=False)

    df_point_count.to_excel(writer, sheet_name="Point_Count_Check", index=False)
    df_key_check.to_excel(writer, sheet_name="Key_Check", index=False)

    for sheet, df_sheet in optional_sheets.items():
        out_sheet = f"Original_{sheet}"[:31]
        df_sheet.to_excel(writer, sheet_name=out_sheet, index=False)

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

            ws.column_dimensions[col_letter].width = min(max_length + 2, 40)


print("\n保存完成:", output_file)
print("主要输出 sheet:")
print("1. Data_with_Tb_cleaned：只保留有 Tb 的 viscosity 数据点")
print("2. Material_with_Tb_cleaned：只保留有 Tb 的物质")
print("3. Removed_Materials：被删除的物质及原因")
print("4. Point_Count_Check：删除前后每个物质的数据点数量")
print("5. Summary：总体统计")