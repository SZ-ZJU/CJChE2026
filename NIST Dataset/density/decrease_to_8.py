import pandas as pd
import numpy as np
from pathlib import Path


# =========================================================
# 1. 输入输出文件
# =========================================================
input_file = Path("dataset_density_selected_by_two_k_with_density_T_interpolation.xlsx")
output_file = Path("dataset_density_selected_by_two_k_with_density_T_interpolation_8points.xlsx")


# =========================================================
# 2. sheet 名
# =========================================================
data_sheet = "Data_selected"
material_sheet = "Material_selected"
groups_sheet = "Groups_selected"
interpolated_sheet = "Interpolated_k1_k2"
final_model_sheet = "Final_Model_Table"

# 其他辅助 sheet，如果存在就一起复制
optional_sheets = [
    "All_Material_k_Intervals",
    "Top_k_Pairs",
    "Covered_By_Both_k",
    "Summary",
]


# =========================================================
# 3. 基础列名
# =========================================================
material_key_col = "material_key"
temp_col = "T_K"

# 每个物质最多保留多少个温度点
max_points_per_material = 8


# =========================================================
# 4. 工具函数
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
    如果 Data_selected 里面没有 material_key，就自动构造。

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


def select_evenly_with_max_temperature_range(group, temp_col, max_points=8):
    """
    对单个物质的数据点抽样。

    规则：
    1. 按温度升序排序。
    2. 如果点数 <= max_points，全部保留。
    3. 如果点数 > max_points，强制保留首尾点，也就是 Tmin 和 Tmax。
    4. 中间点用 np.linspace 在排序后的索引上均匀取值。
    """
    g = group.copy()
    g[temp_col] = pd.to_numeric(g[temp_col], errors="coerce")

    # 按温度升序排列
    # 如果存在 NaN 温度，放到最后；正常清洗后一般不会有
    g = g.sort_values(temp_col, na_position="last").reset_index(drop=False)
    original_index_col = "index"

    n = len(g)

    # 点数不超过 max_points，全部保留
    if n <= max_points:
        selected = g.copy()
        selected["point_selection_status"] = "kept_all_less_or_equal_8"
        selected["selected_point_rank"] = np.arange(1, len(selected) + 1)
        return selected.drop(columns=[original_index_col])

    # 初步用 linspace 均匀抽样，天然包含首尾
    raw_indices = np.linspace(0, n - 1, max_points)
    selected_indices = np.round(raw_indices).astype(int)
    selected_indices = np.unique(selected_indices)

    # 如果 round 后有重复，导致不足 max_points，则补齐
    if len(selected_indices) < max_points:
        selected_set = set(selected_indices.tolist())

        candidate_indices = list(range(n))
        candidate_indices = sorted(
            candidate_indices,
            key=lambda idx: min(abs(idx - x) for x in raw_indices)
        )

        for idx in candidate_indices:
            selected_set.add(idx)
            if len(selected_set) >= max_points:
                break

        selected_indices = np.array(sorted(selected_set), dtype=int)

    # 强制保留最低温和最高温
    selected_set = set(selected_indices.tolist())
    selected_set.add(0)
    selected_set.add(n - 1)

    # 如果因为补首尾导致超过 max_points，则中间只保留 max_points - 2 个
    if len(selected_set) > max_points:
        middle_candidates = sorted(
            [idx for idx in selected_set if idx not in [0, n - 1]]
        )

        if max_points > 2:
            if len(middle_candidates) <= max_points - 2:
                middle_selected = middle_candidates
            else:
                middle_pos = np.linspace(
                    0,
                    len(middle_candidates) - 1,
                    max_points - 2
                )
                middle_selected = [
                    middle_candidates[int(round(p))]
                    for p in middle_pos
                ]
                middle_selected = sorted(set(middle_selected))

                # 如果去重后不足，再补齐
                if len(middle_selected) < max_points - 2:
                    for idx in middle_candidates:
                        if idx not in middle_selected:
                            middle_selected.append(idx)
                        if len(middle_selected) >= max_points - 2:
                            break
                    middle_selected = sorted(middle_selected)

            final_indices = [0] + middle_selected[:max_points - 2] + [n - 1]
        else:
            final_indices = [0, n - 1][:max_points]

        selected_indices = np.array(sorted(set(final_indices)), dtype=int)

    else:
        selected_indices = np.array(sorted(selected_set), dtype=int)

    selected = g.iloc[selected_indices].copy()
    selected["point_selection_status"] = "selected_8_evenly_keep_Tmin_Tmax"
    selected["selected_point_rank"] = np.arange(1, len(selected) + 1)

    return selected.drop(columns=[original_index_col])


def build_point_summary(df_data_before, df_data_after):
    rows = []

    before_grouped = {
        k: g.copy()
        for k, g in df_data_before.groupby(material_key_col, sort=False)
    }

    after_grouped = {
        k: g.copy()
        for k, g in df_data_after.groupby(material_key_col, sort=False)
    }

    all_keys = list(before_grouped.keys())

    for material_key in all_keys:
        g_before = before_grouped[material_key]
        g_after = after_grouped.get(material_key, pd.DataFrame())

        T_before = pd.to_numeric(g_before[temp_col], errors="coerce").dropna()
        T_after = pd.to_numeric(g_after[temp_col], errors="coerce").dropna()

        row = {
            material_key_col: material_key,

            "n_points_before": len(g_before),
            "n_points_after": len(g_after),

            "T_min_before": T_before.min() if len(T_before) > 0 else np.nan,
            "T_max_before": T_before.max() if len(T_before) > 0 else np.nan,
            "T_range_before": (
                T_before.max() - T_before.min()
                if len(T_before) > 0
                else np.nan
            ),

            "T_min_after": T_after.min() if len(T_after) > 0 else np.nan,
            "T_max_after": T_after.max() if len(T_after) > 0 else np.nan,
            "T_range_after": (
                T_after.max() - T_after.min()
                if len(T_after) > 0
                else np.nan
            ),
        }

        for col in [
            "compound_name",
            "cas",
            "formula",
            "SMILES",
            "smiles",
            "final_smiles",
            "inchikey",
            "pubchem_cid",
            "pubchem_iupac_name",
            "boiling_T_K",
            "critical_T_K",
        ]:
            if col in g_before.columns:
                row[col] = g_before[col].iloc[0]

        rows.append(row)

    return pd.DataFrame(rows)


# =========================================================
# 5. 读取 Excel
# =========================================================
if not input_file.exists():
    raise FileNotFoundError(f"没有找到输入文件: {input_file}")

xls = pd.ExcelFile(input_file)

print("输入文件包含的 sheet:")
print(xls.sheet_names)

if data_sheet not in xls.sheet_names:
    raise ValueError(f"没有找到 sheet: {data_sheet}")

df_data = pd.read_excel(input_file, sheet_name=data_sheet)

if temp_col not in df_data.columns:
    raise ValueError(f"{data_sheet} 中没有找到温度列: {temp_col}")

if material_key_col not in df_data.columns:
    df_data[material_key_col] = df_data.apply(build_material_key, axis=1)

df_data[material_key_col] = df_data[material_key_col].astype(str).str.strip()
df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")

print("\n原始 Data_selected 行数:", len(df_data))
print("原始物质数:", df_data[material_key_col].nunique())

if (df_data[material_key_col] == "unknown_material").any():
    print("警告：Data_selected 中存在 unknown_material，请检查物质标识列。")


# =========================================================
# 6. 按物质抽点
# =========================================================
df_data_8points = (
    df_data
    .groupby(material_key_col, group_keys=False, sort=False)
    .apply(
        lambda g: select_evenly_with_max_temperature_range(
            g,
            temp_col=temp_col,
            max_points=max_points_per_material
        )
    )
    .reset_index(drop=True)
)

df_point_summary = build_point_summary(df_data, df_data_8points)

print("\n========== 抽点结果 ==========")
print("抽点后 Data_selected 行数:", len(df_data_8points))
print("抽点后物质数:", df_data_8points[material_key_col].nunique())

print("\n抽点前每个物质点数统计:")
print(df_data.groupby(material_key_col).size().value_counts().sort_index())

print("\n抽点后每个物质点数统计:")
print(df_data_8points.groupby(material_key_col).size().value_counts().sort_index())

# 检查是否有物质超过 8 个点
n_after_check = df_data_8points.groupby(material_key_col).size()
too_many = n_after_check[n_after_check > max_points_per_material]

if len(too_many) > 0:
    print("\n仍超过 8 个点的物质:")
    print(too_many)
    raise RuntimeError("仍有物质超过 8 个点，请检查抽点逻辑。")


# =========================================================
# 7. 读取其他 sheet 并合并抽点统计
# =========================================================
sheet_tables = {}

for sheet in xls.sheet_names:
    if sheet == data_sheet:
        continue

    sheet_tables[sheet] = pd.read_excel(input_file, sheet_name=sheet)


# 如果 Material_selected 存在，把抽点后的统计合并进去
if material_sheet in sheet_tables:
    df_material = sheet_tables[material_sheet].copy()

    if material_key_col not in df_material.columns:
        df_material[material_key_col] = df_material.apply(build_material_key, axis=1)

    df_material[material_key_col] = df_material[material_key_col].astype(str).str.strip()

    summary_cols = [
        material_key_col,
        "n_points_before",
        "n_points_after",
        "T_min_after",
        "T_max_after",
        "T_range_after",
    ]

    df_material = df_material.drop(
        columns=[
            c for c in summary_cols
            if c != material_key_col and c in df_material.columns
        ],
        errors="ignore"
    )

    df_material = df_material.merge(
        df_point_summary[summary_cols],
        on=material_key_col,
        how="left"
    )

    sheet_tables[material_sheet] = df_material


# Interpolated_k1_k2、Final_Model_Table、Covered_By_Both_k 等是物质级信息，
# 不需要按温度点抽样，直接复制即可。


# =========================================================
# 8. Run_Info
# =========================================================
run_info = pd.DataFrame([
    {"item": "input_file", "value": str(input_file)},
    {"item": "output_file", "value": str(output_file)},
    {"item": "data_sheet_processed", "value": data_sheet},
    {"item": "material_key_col", "value": material_key_col},
    {"item": "temp_col", "value": temp_col},
    {"item": "max_points_per_material", "value": max_points_per_material},
    {
        "item": "selection_rule",
        "value": "if n<=8 keep all; if n>8 keep Tmin/Tmax and choose middle points evenly by sorted temperature"
    },
    {"item": "original_data_rows", "value": len(df_data)},
    {"item": "resampled_data_rows", "value": len(df_data_8points)},
    {"item": "original_materials", "value": df_data[material_key_col].nunique()},
    {"item": "resampled_materials", "value": df_data_8points[material_key_col].nunique()},
    {
        "item": "materials_with_more_than_8_before",
        "value": int((df_data.groupby(material_key_col).size() > 8).sum())
    },
    {
        "item": "materials_with_more_than_8_after",
        "value": int((df_data_8points.groupby(material_key_col).size() > 8).sum())
    },
])


# =========================================================
# 9. 保存新 Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_data_8points.to_excel(writer, sheet_name=data_sheet, index=False)
    df_point_summary.to_excel(writer, sheet_name="Point_Selection_Summary", index=False)

    for sheet in xls.sheet_names:
        if sheet == data_sheet:
            continue

        df_sheet = sheet_tables[sheet]
        df_sheet.to_excel(writer, sheet_name=sheet[:31], index=False)

    run_info.to_excel(writer, sheet_name="Run_Info_8points", index=False)

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
print("最终每个物质点数已经限制为最多 8 个。")
print("主数据 sheet:", data_sheet)
print("抽点统计 sheet: Point_Selection_Summary")