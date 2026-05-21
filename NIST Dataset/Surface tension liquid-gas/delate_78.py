# -*- coding: utf-8 -*-
"""
修复 dataset.xlsx 中 groups 少第 78 个物质的问题

目标：
    删除 Material_with_Tb_cleaned 中第 78 个物质，
    并同步删除 Data_with_Tb_cleaned 中该物质的所有数据点。

输入：
    dataset.xlsx

输出：
    dataset_drop78_fixed.xlsx

说明：
    这里的第 78 个物质是指 Excel 数据区第 78 行，不包括表头。
    pandas 中对应 iloc[77]。
"""

import pandas as pd
import numpy as np
from pathlib import Path


# =========================================================
# 1. 输入输出
# =========================================================

input_file = Path("dataset.xlsx")
output_file = Path("dataset_drop78_fixed.xlsx")

data_sheet = "Data_with_Tb_cleaned"
material_sheet = "Material_with_Tb_cleaned"
groups_sheet = "groups"

material_key_col = "material_key"

# 要删除第几个物质，1-based，不包括表头
drop_material_position_1based = 78
drop_material_index_0based = drop_material_position_1based - 1


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


def build_material_key(row):
    """
    构造物质唯一标识。

    优先级：
        1. material_key
        2. inchikey
        3. pubchem_inchikey
        4. cas
        5. compound_name
        6. formula
    """
    for col in [
        "material_key",
        "inchikey",
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


# =========================================================
# 3. 读取 Excel
# =========================================================

if not input_file.exists():
    raise FileNotFoundError(f"没有找到输入文件: {input_file}")

xls = pd.ExcelFile(input_file)

print("输入文件包含的 sheet:")
print(xls.sheet_names)

if data_sheet not in xls.sheet_names:
    raise ValueError(f"没有找到 sheet: {data_sheet}")

if material_sheet not in xls.sheet_names:
    raise ValueError(f"没有找到 sheet: {material_sheet}")

if groups_sheet not in xls.sheet_names:
    raise ValueError(f"没有找到 sheet: {groups_sheet}")

df_data = pd.read_excel(input_file, sheet_name=data_sheet)
df_material = pd.read_excel(input_file, sheet_name=material_sheet)
df_groups = pd.read_excel(input_file, sheet_name=groups_sheet)

print("\n原始行数：")
print("Data 行数:", len(df_data))
print("Material 行数:", len(df_material))
print("groups 行数:", len(df_groups))


# =========================================================
# 4. 构造 material_key
# =========================================================

if material_key_col not in df_material.columns:
    df_material[material_key_col] = df_material.apply(build_material_key, axis=1)

if material_key_col not in df_data.columns:
    df_data[material_key_col] = df_data.apply(build_material_key, axis=1)

df_material[material_key_col] = df_material[material_key_col].astype(str).str.strip()
df_data[material_key_col] = df_data[material_key_col].astype(str).str.strip()


# =========================================================
# 5. 找到第 78 个物质
# =========================================================

if drop_material_index_0based < 0 or drop_material_index_0based >= len(df_material):
    raise ValueError(
        f"要删除的第 {drop_material_position_1based} 个物质超出范围。"
        f"当前 Material 物质数为 {len(df_material)}。"
    )

drop_row = df_material.iloc[drop_material_index_0based].copy()
drop_material_key = str(drop_row[material_key_col]).strip()

print("\n准备删除的物质：")
print("位置:", drop_material_position_1based)
print("material_key:", drop_material_key)

for col in ["compound_name", "cas", "formula", "inchikey", "SMILES", "smiles", "boiling_T_K"]:
    if col in df_material.columns:
        print(f"{col}:", drop_row.get(col, None))


# =========================================================
# 6. 删除 Material 第 78 个物质
# =========================================================

df_material_fixed = df_material.drop(
    index=df_material.index[drop_material_index_0based]
).reset_index(drop=True)

# 如果有 original_material_index，重新生成，避免后续 iloc 顺序出问题
if "original_material_index" in df_material_fixed.columns:
    df_material_fixed = df_material_fixed.drop(columns=["original_material_index"])

df_material_fixed.insert(0, "original_material_index", np.arange(len(df_material_fixed)))


# =========================================================
# 7. 同步删除 Data 中该物质的所有数据点
# =========================================================

df_data_removed = df_data[
    df_data[material_key_col] == drop_material_key
].copy()

df_data_fixed = df_data[
    df_data[material_key_col] != drop_material_key
].copy().reset_index(drop=True)

print("\n删除 Data 数据点数:", len(df_data_removed))


# =========================================================
# 8. groups 处理
# =========================================================
# 你的情况是 groups 已经自动跳过了第 78 个物质，
# 因此这里默认不再删除 groups 的任何行。
# 如果你的 groups 实际还有 137 行，则代码会自动删除第 78 行。

if len(df_groups) == len(df_material):
    print("\ngroups 行数与原 Material 一致，说明 groups 没有少行，将同步删除第 78 行。")

    df_groups_fixed = df_groups.drop(
        index=df_groups.index[drop_material_index_0based]
    ).reset_index(drop=True)

elif len(df_groups) == len(df_material) - 1:
    print("\ngroups 行数已经比原 Material 少 1，认为它已经跳过了第 78 个物质，groups 保持不变。")

    df_groups_fixed = df_groups.copy().reset_index(drop=True)

else:
    raise ValueError(
        "groups 行数既不等于原 Material 行数，也不等于原 Material 行数 - 1。\n"
        f"Material 行数: {len(df_material)}\n"
        f"groups 行数: {len(df_groups)}\n"
        "请先检查 groups sheet 是否还有其他缺失或多余物质。"
    )

# 重新生成 original_material_index，保证和修复后的 Material 对齐
if "original_material_index" in df_groups_fixed.columns:
    df_groups_fixed = df_groups_fixed.drop(columns=["original_material_index"])

df_groups_fixed.insert(0, "original_material_index", np.arange(len(df_groups_fixed)))

# 如果 groups 里面没有 material_key，就按修复后的 Material 顺序补上
if material_key_col in df_groups_fixed.columns:
    df_groups_fixed[material_key_col] = df_material_fixed[material_key_col].values
else:
    df_groups_fixed.insert(1, material_key_col, df_material_fixed[material_key_col].values)


# =========================================================
# 9. 一致性检查
# =========================================================

print("\n修复后行数：")
print("Data 行数:", len(df_data_fixed))
print("Material 行数:", len(df_material_fixed))
print("groups 行数:", len(df_groups_fixed))

if len(df_material_fixed) != len(df_groups_fixed):
    raise ValueError(
        "修复后 Material 和 groups 行数仍然不一致：\n"
        f"Material: {len(df_material_fixed)}\n"
        f"groups: {len(df_groups_fixed)}"
    )

material_keys = df_material_fixed[material_key_col].astype(str).str.strip().tolist()
group_keys = df_groups_fixed[material_key_col].astype(str).str.strip().tolist()

if material_keys != group_keys:
    raise ValueError(
        "修复后 Material 和 groups 的 material_key 顺序仍然不一致。\n"
        "请检查 groups 是否除了第 78 个物质外还有其他错位。"
    )

data_keys = set(df_data_fixed[material_key_col].astype(str).str.strip())
material_keys_set = set(df_material_fixed[material_key_col].astype(str).str.strip())

keys_in_data_not_material = data_keys - material_keys_set
keys_in_material_not_data = material_keys_set - data_keys

print("\n对应关系检查：")
print("Data 中存在但 Material 中不存在的物质数:", len(keys_in_data_not_material))
print("Material 中存在但 Data 中不存在的物质数:", len(keys_in_material_not_data))


# =========================================================
# 10. 生成诊断表
# =========================================================

df_removed_material = pd.DataFrame([drop_row.to_dict()])
df_removed_material["remove_reason"] = f"manual_remove_{drop_material_position_1based}th_material_to_match_groups"

df_key_check = pd.DataFrame([
    {
        "check_item": "removed_material_position_1based",
        "value": drop_material_position_1based,
    },
    {
        "check_item": "removed_material_key",
        "value": drop_material_key,
    },
    {
        "check_item": "data_rows_removed",
        "value": len(df_data_removed),
    },
    {
        "check_item": "material_rows_after_fix",
        "value": len(df_material_fixed),
    },
    {
        "check_item": "groups_rows_after_fix",
        "value": len(df_groups_fixed),
    },
    {
        "check_item": "keys_in_data_not_material",
        "value": len(keys_in_data_not_material),
    },
    {
        "check_item": "keys_in_material_not_data",
        "value": len(keys_in_material_not_data),
    },
])

summary = pd.DataFrame([
    {"item": "input_file", "value": str(input_file)},
    {"item": "output_file", "value": str(output_file)},
    {"item": "deleted_material_position_1based", "value": drop_material_position_1based},
    {"item": "deleted_material_key", "value": drop_material_key},
    {"item": "original_data_rows", "value": len(df_data)},
    {"item": "fixed_data_rows", "value": len(df_data_fixed)},
    {"item": "removed_data_rows", "value": len(df_data_removed)},
    {"item": "original_material_rows", "value": len(df_material)},
    {"item": "fixed_material_rows", "value": len(df_material_fixed)},
    {"item": "original_groups_rows", "value": len(df_groups)},
    {"item": "fixed_groups_rows", "value": len(df_groups_fixed)},
])


# =========================================================
# 11. 保存新 Excel
# =========================================================

with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_data_fixed.to_excel(writer, sheet_name=data_sheet, index=False)
    df_material_fixed.to_excel(writer, sheet_name=material_sheet, index=False)
    df_groups_fixed.to_excel(writer, sheet_name=groups_sheet, index=False)

    df_removed_material.to_excel(writer, sheet_name="Removed_78th_Material", index=False)
    df_data_removed.to_excel(writer, sheet_name="Removed_78th_Data_Rows", index=False)
    df_key_check.to_excel(writer, sheet_name="Key_Check_Drop78", index=False)
    summary.to_excel(writer, sheet_name="Summary_Drop78", index=False)

    # 保留原文件中其他 sheet
    for sheet in xls.sheet_names:
        if sheet in [data_sheet, material_sheet, groups_sheet]:
            continue

        df_other = pd.read_excel(input_file, sheet_name=sheet)
        df_other.to_excel(writer, sheet_name=sheet[:31], index=False)

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
print("后续 two-k 脚本请读取这个文件，并把 dataset_file 改成：")
print(output_file)