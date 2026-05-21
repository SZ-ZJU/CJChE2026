import pandas as pd
import numpy as np
import re
from pathlib import Path


# =========================================================
# 1. 输入输出文件
# =========================================================
input_file = Path("thermoml_viscosity_Liquid_with_clean_SMILES.xlsx")
input_sheet = "Data_Clean_SMILES"

output_file = Path("thermoml_viscosity_Liquid_final_n8_Tgt30_noExcludedElements.xlsx")


# =========================================================
# 2. 筛选条件
# =========================================================
temp_col = "T_K"
viscosity_col = "Viscosity_Pa_s"
ln_viscosity_col = "lnViscosity_Pa_s"

# 每个物质至少多少个温度点
min_points = 8

# 温度跨度必须严格大于多少 K
min_temp_range = 30.0

# 删除包含这些元素的物质
# 默认先删除 Si；如需更多，写成 {"Si", "B", "P"} 这种形式
excluded_elements = {"Si"}

# 是否删除带电氮结构，例如 [N+], [N-], [n+], [n-]
# 如果前面 clean_SMILES 没有删这类物质，可以设为 True
remove_charged_nitrogen = False

# 是否删除黏度 <= 0 的数据点
remove_non_positive_viscosity = True


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

if temp_col not in df.columns:
    raise ValueError(f"没有找到温度列: {temp_col}")

if viscosity_col not in df.columns:
    raise ValueError(f"没有找到黏度列: {viscosity_col}")

df[temp_col] = pd.to_numeric(df[temp_col], errors="coerce")
df[viscosity_col] = pd.to_numeric(df[viscosity_col], errors="coerce")

# 删除 T 或 viscosity 为空的数据
before_drop_na = len(df)
df = df[
    df[temp_col].notna()
    & df[viscosity_col].notna()
].copy()

print("\n删除 T 或 viscosity 为空的数据点数:", before_drop_na - len(df))

# 删除非正黏度
if remove_non_positive_viscosity:
    before_drop_non_positive = len(df)
    df = df[df[viscosity_col] > 0].copy()
    print("删除 viscosity <= 0 的数据点数:", before_drop_non_positive - len(df))

# 自动生成 lnViscosity_Pa_s
df[ln_viscosity_col] = np.log(df[viscosity_col])


# =========================================================
# 4. material_key 工具函数
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
    1. material_key
    2. inchikey
    3. cas
    4. compound_name
    5. formula
    """
    for col in ["material_key", "inchikey", "cas", "compound_name", "formula"]:
        if col in row.index and is_valid_value(row[col]):
            if col == "material_key":
                return str(row[col]).strip()
            return f"{col}:{str(row[col]).strip()}"

    return "unknown_material"


if "material_key" not in df.columns:
    df["material_key"] = df.apply(build_material_key, axis=1)


# =========================================================
# 5. 元素解析
# =========================================================
def parse_elements(formula):
    """
    从分子式中提取元素符号。
    例如：
    C6H6Si -> {"C", "H", "Si"}
    C2H6O -> {"C", "H", "O"}
    """
    if not is_valid_value(formula):
        return set()

    s = str(formula).strip()
    s = s.replace(" ", "")
    s = s.replace("·", ".")
    s = s.replace("-", "")

    return set(re.findall(r"[A-Z][a-z]?", s))


def material_contains_excluded_elements(group):
    """
    判断一个物质是否含有 excluded_elements 中的元素。
    优先检查 formula，其次检查 pubchem_molecular_formula。
    """
    formula_candidates = []

    for col in ["formula", "pubchem_molecular_formula"]:
        if col in group.columns:
            vals = (
                group[col]
                .dropna()
                .astype(str)
                .str.strip()
                .unique()
                .tolist()
            )
            formula_candidates.extend(vals)

    detected_elements = set()

    for formula in formula_candidates:
        elements = parse_elements(formula)
        detected_elements |= elements

    hit_elements = detected_elements & excluded_elements

    return len(hit_elements) > 0, ";".join(sorted(hit_elements)), ";".join(sorted(detected_elements))


# =========================================================
# 6. 可选：带电氮判断
# =========================================================
def has_charged_nitrogen(smiles):
    """
    判断 SMILES 中是否存在带电氮。
    可匹配：
    [N+]
    [N-]
    [n+]
    [n-]
    [NH+]
    [NH-]
    [N@@+]
    """
    if not is_valid_value(smiles):
        return False

    s = str(smiles).strip()
    pattern = r"\[[^\]]*[Nn][^\]]*[+-][^\]]*\]"

    return re.search(pattern, s) is not None


def get_charged_nitrogen_fragments(smiles):
    if not is_valid_value(smiles):
        return ""

    s = str(smiles).strip()
    pattern = r"\[[^\]]*[Nn][^\]]*[+-][^\]]*\]"

    return "; ".join(re.findall(pattern, s))


def material_has_charged_nitrogen(group):
    smiles_cols = [
        "SMILES",
        "final_smiles",
        "pubchem_isomeric_smiles",
        "pubchem_canonical_smiles",
        "pubchem_connectivity_smiles",
        "smiles",
    ]

    smiles_values = []

    for col in smiles_cols:
        if col in group.columns:
            vals = group[col].dropna().astype(str).str.strip().unique().tolist()
            smiles_values.extend(vals)

    smiles_values = list(dict.fromkeys([s for s in smiles_values if is_valid_value(s)]))

    fragments = []

    for s in smiles_values:
        frag = get_charged_nitrogen_fragments(s)
        if frag:
            fragments.append(frag)

    fragments = list(dict.fromkeys(fragments))

    return any(has_charged_nitrogen(s) for s in smiles_values), "; ".join(fragments)


# =========================================================
# 7. 按物质计算 n_points / T_range / 元素状态
# =========================================================
material_rows = []

for material_key, group in df.groupby("material_key", sort=False):
    g = group.copy()
    g_valid_t = g[g[temp_col].notna()].copy()

    n_points_current = len(g_valid_t)

    if n_points_current > 0:
        T_min = g_valid_t[temp_col].min()
        T_max = g_valid_t[temp_col].max()
        T_range = T_max - T_min
    else:
        T_min = np.nan
        T_max = np.nan
        T_range = np.nan

    contains_excluded, excluded_hit, detected_elements = material_contains_excluded_elements(g)
    charged_n, charged_n_fragments = material_has_charged_nitrogen(g)

    remove_reasons = []

    if n_points_current < min_points:
        remove_reasons.append(f"n_points_less_than_{min_points}")

    if pd.isna(T_range) or T_range <= min_temp_range:
        remove_reasons.append(f"T_range_not_greater_than_{min_temp_range:g}K")

    if contains_excluded:
        remove_reasons.append(f"contains_excluded_elements_{excluded_hit}")

    if remove_charged_nitrogen and charged_n:
        remove_reasons.append("contains_charged_nitrogen")

    if len(remove_reasons) == 0:
        filter_status = "keep"
    else:
        filter_status = "remove"

    row = {
        "material_key": material_key,
        "filter_status": filter_status,
        "remove_reason": "; ".join(remove_reasons),
        "n_points_current": n_points_current,
        "T_min_current": T_min,
        "T_max_current": T_max,
        "T_range_current": T_range,
        "detected_elements": detected_elements,
        "excluded_elements_hit": excluded_hit,
        "contains_excluded_elements": contains_excluded,
        "contains_charged_nitrogen": charged_n,
        "charged_nitrogen_fragments": charged_n_fragments,
    }

    # 保留物质基本信息
    for col in [
        "compound_name",
        "cas",
        "formula",
        "pubchem_molecular_formula",
        "SMILES",
        "final_smiles",
        "inchikey",
        "pubchem_cid",
        "pubchem_iupac_name",
        "phase",
        "property_name",
    ]:
        if col in g.columns:
            row[col] = g[col].iloc[0]

    # 保留黏度范围
    if viscosity_col in g.columns:
        row["Viscosity_min_Pa_s"] = g[viscosity_col].min()
        row["Viscosity_max_Pa_s"] = g[viscosity_col].max()
        row["Viscosity_range_Pa_s"] = g[viscosity_col].max() - g[viscosity_col].min()

    if ln_viscosity_col in g.columns:
        row["lnViscosity_min_Pa_s"] = g[ln_viscosity_col].min()
        row["lnViscosity_max_Pa_s"] = g[ln_viscosity_col].max()
        row["lnViscosity_range_Pa_s"] = (
            g[ln_viscosity_col].max() - g[ln_viscosity_col].min()
        )

    # 如果前面线性度已经合并进表，也顺便保留
    for col in [
        "RSQ_viscosity_vs_T",
        "RSQ_lnViscosity_vs_T",
        "RSQ_lnViscosity_vs_invT",
        "slope_viscosity_vs_T",
        "slope_lnViscosity_vs_invT",
    ]:
        if col in g.columns:
            row[col] = g[col].iloc[0]

    material_rows.append(row)


df_material_summary = pd.DataFrame(material_rows)


# =========================================================
# 8. 生成保留和删除数据
# =========================================================
kept_material_keys = df_material_summary.loc[
    df_material_summary["filter_status"] == "keep",
    "material_key"
]

removed_material_keys = df_material_summary.loc[
    df_material_summary["filter_status"] == "remove",
    "material_key"
]

df_kept = df[df["material_key"].isin(kept_material_keys)].copy()
df_removed = df[df["material_key"].isin(removed_material_keys)].copy()

summary_merge_cols = [
    "material_key",
    "filter_status",
    "remove_reason",
    "n_points_current",
    "T_min_current",
    "T_max_current",
    "T_range_current",
    "detected_elements",
    "excluded_elements_hit",
    "contains_excluded_elements",
    "contains_charged_nitrogen",
    "charged_nitrogen_fragments",
]

df_kept = df_kept.merge(
    df_material_summary[summary_merge_cols],
    on="material_key",
    how="left"
)

df_removed = df_removed.merge(
    df_material_summary[summary_merge_cols],
    on="material_key",
    how="left"
)

df_kept_materials = df_material_summary[
    df_material_summary["filter_status"] == "keep"
].copy()

df_removed_materials = df_material_summary[
    df_material_summary["filter_status"] == "remove"
].copy()


# =========================================================
# 9. 排序
# =========================================================
sort_cols = [c for c in ["material_key", temp_col] if c in df_kept.columns]
if sort_cols:
    df_kept = df_kept.sort_values(sort_cols).reset_index(drop=True)

sort_cols_removed = [c for c in ["material_key", temp_col] if c in df_removed.columns]
if sort_cols_removed:
    df_removed = df_removed.sort_values(sort_cols_removed).reset_index(drop=True)

df_kept_materials = df_kept_materials.sort_values(
    ["T_range_current", "n_points_current"],
    ascending=[False, False]
).reset_index(drop=True)

df_removed_materials = df_removed_materials.sort_values(
    ["remove_reason", "T_range_current", "n_points_current"],
    ascending=[True, False, False]
).reset_index(drop=True)


# =========================================================
# 10. 打印结果
# =========================================================
print("\n========== Viscosity 最终筛选结果 ==========")
print("筛选前数据行数:", len(df))
print("筛选前物质数:", df["material_key"].nunique())

print("\n保留数据行数:", len(df_kept))
print("保留物质数:", df_kept["material_key"].nunique())

print("\n删除数据行数:", len(df_removed))
print("删除物质数:", df_removed["material_key"].nunique())

print("\n删除原因统计:")
print(df_removed_materials["remove_reason"].value_counts(dropna=False))

print("\n被固定元素筛掉的物质数:")
print(int(df_removed_materials["contains_excluded_elements"].sum()))

if remove_charged_nitrogen:
    print("\n被带电氮筛掉的物质数:")
    print(int(df_removed_materials["contains_charged_nitrogen"].sum()))

print("\n最终每个物质点数统计:")
print(df_kept.groupby("material_key").size().value_counts().sort_index())


# =========================================================
# 11. 保存 Excel
# =========================================================
run_info = pd.DataFrame([
    {"item": "input_file", "value": str(input_file)},
    {"item": "input_sheet", "value": input_sheet},
    {"item": "output_file", "value": str(output_file)},

    {"item": "min_points", "value": min_points},
    {"item": "min_temp_range_K_strictly_greater_than", "value": min_temp_range},
    {"item": "excluded_elements", "value": ";".join(sorted(excluded_elements))},
    {"item": "remove_charged_nitrogen", "value": remove_charged_nitrogen},
    {"item": "remove_non_positive_viscosity", "value": remove_non_positive_viscosity},

    {"item": "original_rows", "value": len(df)},
    {"item": "original_materials", "value": df["material_key"].nunique()},

    {"item": "kept_rows", "value": len(df_kept)},
    {"item": "kept_materials", "value": df_kept["material_key"].nunique()},

    {"item": "removed_rows", "value": len(df_removed)},
    {"item": "removed_materials", "value": df_removed["material_key"].nunique()},

    {
        "item": f"removed_by_n_points_less_than_{min_points}",
        "value": int(
            df_removed_materials["remove_reason"]
            .str.contains(f"n_points_less_than_{min_points}", na=False)
            .sum()
        )
    },
    {
        "item": f"removed_by_T_range_not_greater_than_{min_temp_range:g}K",
        "value": int(
            df_removed_materials["remove_reason"]
            .str.contains(f"T_range_not_greater_than_{min_temp_range:g}K", na=False)
            .sum()
        )
    },
    {
        "item": "removed_by_excluded_elements",
        "value": int(df_removed_materials["contains_excluded_elements"].sum())
    },
    {
        "item": "removed_by_charged_nitrogen",
        "value": int(df_removed_materials["contains_charged_nitrogen"].sum())
    },
])

with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_kept.to_excel(writer, sheet_name="Final_Selected_Data", index=False)
    df_kept_materials.to_excel(writer, sheet_name="Final_Materials", index=False)

    df_removed.to_excel(writer, sheet_name="Removed_Rows", index=False)
    df_removed_materials.to_excel(writer, sheet_name="Removed_Materials", index=False)

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