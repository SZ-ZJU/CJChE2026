import pandas as pd
import numpy as np
from pathlib import Path


# =========================================================
# 1. 输入输出文件
# =========================================================
input_file = Path("dataset.xlsx")
output_file = Path("dataset_density_with_Tb_Tc_cleaned.xlsx")

# Tb/Tc 脚本生成的两个核心 sheet
material_sheet = "Material_with_Tb_Tc"
data_sheet = "Data_with_Tb_Tc"

# 判断是否保留物质的列
tb_col = "boiling_T_K"

# 是否要求 Tb > 0
require_positive_tb = True

# 对这些辅助 sheet，如果没有 material_key 且行数不等于 material 表，就原样复制
copy_unmatched_sheets = True


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
        "PubChem_InChIKey",
        "cas",
        "compound_name",
        "formula",
    ]:
        if col in row.index and is_valid_value(row[col]):
            if col == "material_key":
                return str(row[col]).strip()

            return f"{col}:{str(row[col]).strip()}"

    return "unknown_material"


def find_col_case_insensitive(df, candidates):
    """
    大小写不敏感地寻找列名。
    """
    lower_map = {str(c).lower(): c for c in df.columns}

    for c in candidates:
        if c in df.columns:
            return c

    for c in candidates:
        if str(c).lower() in lower_map:
            return lower_map[str(c).lower()]

    return None


def normalize_material_key_series(s):
    return s.astype(str).str.strip()


def make_valid_tb_mask(df_material, tb_col):
    """
    有效 Tb 判定。
    """
    tb = pd.to_numeric(df_material[tb_col], errors="coerce")

    mask = tb.notna() & np.isfinite(tb)

    if require_positive_tb:
        mask = mask & (tb > 0)

    return mask, tb


def prepare_material_key(df):
    """
    如果没有 material_key，则自动构造。
    """
    if "material_key" not in df.columns:
        df = df.copy()
        df["material_key"] = df.apply(build_material_key, axis=1)

    df["material_key"] = normalize_material_key_series(df["material_key"])

    return df


def filter_sheet_by_materials(
    sheet_name,
    df_sheet,
    n_material_rows,
    keep_position_mask,
    keep_material_keys,
    removed_material_keys,
):
    """
    根据 sheet 类型进行筛选。

    规则：
    1. 如果是 material_sheet：按位置 mask 删除；
    2. 如果是 data_sheet：按 material_key 删除；
    3. 如果该 sheet 行数等于 Material 表行数：认为它是物质级 sheet，比如 groups，按位置 mask 删除；
    4. 如果该 sheet 有 material_key：按 material_key 删除；
    5. 否则原样复制。
    """
    df = df_sheet.copy()

    # ---------- 1. Material 表 ----------
    if sheet_name == material_sheet:
        df_out = df.loc[keep_position_mask].copy().reset_index(drop=True)
        df_removed = df.loc[~keep_position_mask].copy().reset_index(drop=True)
        method = "material_sheet_filter_by_position"
        return df_out, df_removed, method

    # ---------- 2. Data 表 ----------
    if sheet_name == data_sheet:
        if "material_key" not in df.columns:
            df = prepare_material_key(df)

        df["material_key"] = normalize_material_key_series(df["material_key"])

        keep_mask = df["material_key"].isin(keep_material_keys)

        df_out = df.loc[keep_mask].copy().reset_index(drop=True)
        df_removed = df.loc[~keep_mask].copy().reset_index(drop=True)
        method = "data_sheet_filter_by_material_key"
        return df_out, df_removed, method

    # ---------- 3. 行数等于 Material 表：认为是物质级同步 sheet ----------
    # 这里最重要，适合你手动添加的 groups sheet。
    if len(df) == n_material_rows:
        df_out = df.loc[keep_position_mask].copy().reset_index(drop=True)
        df_removed = df.loc[~keep_position_mask].copy().reset_index(drop=True)
        method = "row_aligned_material_level_sheet_filter_by_position"
        return df_out, df_removed, method

    # ---------- 4. 有 material_key 的其他 sheet ----------
    key_col = find_col_case_insensitive(
        df,
        ["material_key"]
    )

    if key_col is not None:
        df[key_col] = normalize_material_key_series(df[key_col])

        keep_mask = df[key_col].isin(keep_material_keys)

        df_out = df.loc[keep_mask].copy().reset_index(drop=True)
        df_removed = df.loc[~keep_mask].copy().reset_index(drop=True)
        method = "other_sheet_filter_by_material_key"
        return df_out, df_removed, method

    # ---------- 5. 无法判断，原样复制 ----------
    df_out = df.copy()
    df_removed = pd.DataFrame()
    method = "copied_without_filter"

    return df_out, df_removed, method


# =========================================================
# 3. 读取 Excel
# =========================================================
if not input_file.exists():
    raise FileNotFoundError(f"没有找到输入文件: {input_file}")

xls = pd.ExcelFile(input_file)

print("输入文件包含的 sheet:")
for s in xls.sheet_names:
    print(" -", s)

if material_sheet not in xls.sheet_names:
    raise ValueError(
        f"没有找到 material sheet: {material_sheet}\n"
        f"当前文件 sheet: {xls.sheet_names}"
    )

if data_sheet not in xls.sheet_names:
    raise ValueError(
        f"没有找到 data sheet: {data_sheet}\n"
        f"当前文件 sheet: {xls.sheet_names}"
    )

df_material = pd.read_excel(input_file, sheet_name=material_sheet)
df_data = pd.read_excel(input_file, sheet_name=data_sheet)

print("\nMaterial 原始行数:", len(df_material))
print("Data 原始行数:", len(df_data))

if tb_col not in df_material.columns:
    raise ValueError(
        f"{material_sheet} 中没有找到列 {tb_col}。\n"
        f"当前列名: {list(df_material.columns)}"
    )


# =========================================================
# 4. 构造 material_key
# =========================================================
df_material = prepare_material_key(df_material)
df_data = prepare_material_key(df_data)

if (df_material["material_key"] == "unknown_material").any():
    print("警告：Material 表中存在 unknown_material，请检查物质标识列。")

if (df_data["material_key"] == "unknown_material").any():
    print("警告：Data 表中存在 unknown_material，请检查物质标识列。")


# =========================================================
# 5. 找出没有 Tb 的物质
# =========================================================
valid_tb_mask, tb_numeric = make_valid_tb_mask(df_material, tb_col)
df_material[tb_col] = tb_numeric

keep_position_mask = valid_tb_mask.to_numpy()
remove_position_mask = ~keep_position_mask

keep_material_keys = set(
    df_material.loc[keep_position_mask, "material_key"]
    .dropna()
    .astype(str)
    .str.strip()
)

removed_material_keys = set(
    df_material.loc[remove_position_mask, "material_key"]
    .dropna()
    .astype(str)
    .str.strip()
)

print("\n========== Tb 筛选结果 ==========")
print("原始物质数:", len(df_material))
print("有 Tb 保留物质数:", len(keep_material_keys))
print("无 Tb 删除物质数:", len(removed_material_keys))

removed_reason_rows = []

for _, row in df_material.loc[remove_position_mask].iterrows():
    removed_reason_rows.append({
        "material_key": row.get("material_key", None),
        "remove_reason": "missing_or_invalid_boiling_T_K",
        "boiling_T_K": row.get(tb_col, np.nan),
        "critical_T_K": row.get("critical_T_K", np.nan),
        "Tb_Tc_status": row.get("Tb_Tc_status", None),
        "compound_name": row.get("compound_name", None),
        "cas": row.get("cas", None),
        "formula": row.get("formula", None),
        "inchikey": row.get("inchikey", None),
        "pubchem_cid_for_Tb_Tc": row.get("pubchem_cid_for_Tb_Tc", None),
        "boiling_T_count": row.get("boiling_T_count", None),
        "critical_T_count": row.get("critical_T_count", None),
        "boiling_T_raw_examples": row.get("boiling_T_raw_examples", None),
        "critical_T_raw_examples": row.get("critical_T_raw_examples", None),
    })

df_removed_materials = pd.DataFrame(removed_reason_rows)


# =========================================================
# 6. 筛选所有 sheet
# =========================================================
filtered_sheets = {}
removed_sheets = {}
filter_methods = []

for sheet_name in xls.sheet_names:
    df_sheet = pd.read_excel(input_file, sheet_name=sheet_name)

    df_filtered, df_removed, method = filter_sheet_by_materials(
        sheet_name=sheet_name,
        df_sheet=df_sheet,
        n_material_rows=len(df_material),
        keep_position_mask=keep_position_mask,
        keep_material_keys=keep_material_keys,
        removed_material_keys=removed_material_keys,
    )

    filtered_sheets[sheet_name] = df_filtered

    if len(df_removed) > 0:
        removed_sheets[sheet_name] = df_removed

    filter_methods.append({
        "sheet_name": sheet_name,
        "original_rows": len(df_sheet),
        "filtered_rows": len(df_filtered),
        "removed_rows": len(df_sheet) - len(df_filtered),
        "filter_method": method,
    })

df_filter_methods = pd.DataFrame(filter_methods)


# =========================================================
# 7. 对应关系检查
# =========================================================
df_material_clean = filtered_sheets[material_sheet]
df_data_clean = filtered_sheets[data_sheet]

material_keys_clean = set(
    df_material_clean["material_key"].astype(str).str.strip()
)

data_keys_clean = set(
    df_data_clean["material_key"].astype(str).str.strip()
)

keys_in_data_not_material = data_keys_clean - material_keys_clean
keys_in_material_not_data = material_keys_clean - data_keys_clean

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
    ],
})

print("\n========== 对应关系检查 ==========")
print("Data 中存在但 Material 中不存在的物质数:", len(keys_in_data_not_material))
print("Material 中存在但 Data 中不存在的物质数:", len(keys_in_material_not_data))


# =========================================================
# 8. Data 点数统计
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

df_point_count["n_points_after"] = (
    df_point_count["n_points_after"]
    .fillna(0)
    .astype(int)
)

print("\n========== Data 点数统计 ==========")
print("Data 原始行数:", len(df_data))
print("Data 保留行数:", len(df_data_clean))
print("Data 删除行数:", len(df_data) - len(df_data_clean))

print("\n清洗后每个物质数据点数量分布:")
print(
    df_data_clean
    .groupby("material_key")
    .size()
    .value_counts()
    .sort_index()
)


# =========================================================
# 9. Summary
# =========================================================
summary = pd.DataFrame([
    {"item": "input_file", "value": str(input_file)},
    {"item": "output_file", "value": str(output_file)},
    {"item": "material_sheet", "value": material_sheet},
    {"item": "data_sheet", "value": data_sheet},
    {"item": "tb_col", "value": tb_col},
    {"item": "require_positive_tb", "value": require_positive_tb},

    {"item": "original_material_rows", "value": len(df_material)},
    {"item": "kept_materials_with_Tb", "value": len(keep_material_keys)},
    {"item": "removed_materials_without_Tb", "value": len(removed_material_keys)},

    {"item": "original_data_rows", "value": len(df_data)},
    {"item": "kept_data_rows", "value": len(df_data_clean)},
    {"item": "removed_data_rows", "value": len(df_data) - len(df_data_clean)},

    {"item": "keys_in_data_not_material_after_clean", "value": len(keys_in_data_not_material)},
    {"item": "keys_in_material_not_data_after_clean", "value": len(keys_in_material_not_data)},
])


# =========================================================
# 10. 保存新的 Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    # 先写核心清洗结果
    filtered_sheets[data_sheet].to_excel(
        writer,
        sheet_name="Data_with_Tb_Tc_cleaned",
        index=False
    )

    filtered_sheets[material_sheet].to_excel(
        writer,
        sheet_name="Material_with_Tb_Tc_cleaned",
        index=False
    )

    # 其他 sheet，保持原 sheet 名或加 cleaned
    for sheet_name, df_sheet in filtered_sheets.items():
        if sheet_name in [data_sheet, material_sheet]:
            continue

        out_sheet_name = sheet_name[:31]
        df_sheet.to_excel(writer, sheet_name=out_sheet_name, index=False)

    # 删除记录和检查表
    df_removed_materials.to_excel(
        writer,
        sheet_name="Removed_Materials",
        index=False
    )

    for sheet_name, df_removed in removed_sheets.items():
        if sheet_name in [data_sheet, material_sheet]:
            continue

        removed_sheet_name = f"Removed_{sheet_name}"[:31]
        df_removed.to_excel(writer, sheet_name=removed_sheet_name, index=False)

    df_filter_methods.to_excel(writer, sheet_name="Sheet_Filter_Methods", index=False)
    df_key_check.to_excel(writer, sheet_name="Key_Check", index=False)
    df_point_count.to_excel(writer, sheet_name="Point_Count_Check", index=False)
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

            ws.column_dimensions[col_letter].width = min(max_length + 2, 45)


print("\n保存完成:", output_file)
print("核心输出 sheet:")
print("1. Data_with_Tb_Tc_cleaned：删除无 Tb 物质后的 density 数据点")
print("2. Material_with_Tb_Tc_cleaned：删除无 Tb 后的物质表")
print("3. groups 或其他物质级 sheet：已按相同物质顺序同步删除")
print("4. Removed_Materials：被删除的无 Tb 物质")
print("5. Sheet_Filter_Methods：每个 sheet 的筛选方式")