# -*- coding: utf-8 -*-
"""
Surface tension liquid-gas 数据：寻找两个公共 k，并在 k1*Tb / k2*Tb 处插值表面张力

输入：
    dataset.xlsx

要求：
    1. dataset.xlsx 中包含：
        - Data_with_Tb_cleaned
        - Material_with_Tb_cleaned
        - 一个 groups sheet，行顺序与 Material_with_Tb_cleaned 完全一致
    2. groups sheet 中第 3 列到第 426 列为基团特征
    3. Data_with_Tb_cleaned 中每行一个温度点
    4. Material_with_Tb_cleaned 中每行一个物质
    5. 已经删除没有 boiling_T_K 的物质

输出：
    dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation.xlsx

主要功能：
    1. 根据每个物质的实验温度范围 [T_min, T_max] 和 Tb，计算允许 k 区间：
           k_low = T_min / Tb
           k_high = T_max / Tb
    2. 搜索两个公共 k1, k2，使得最大数量的物质同时满足：
           k_low <= k1 < k2 <= k_high
    3. 筛选出同时覆盖 k1 和 k2 的物质
    4. 在 k1*Tb 和 k2*Tb 处，对 SurfaceTension_N_m vs T_K 做线性插值
    5. 同步输出筛选后的 Data、Material、Groups 和最终建模表
"""

import pandas as pd
import numpy as np
from pathlib import Path


# =========================================================
# 1. 输入输出文件
# =========================================================

dataset_file = Path("dataset_drop78_fixed.xlsx")
output_file = Path(
    "dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation.xlsx"
)


# =========================================================
# 2. sheet 名设置
# =========================================================

data_sheet_name = "Data_with_Tb_cleaned"
material_sheet_name = "Material_with_Tb_cleaned"

# 如果你知道基团 sheet 名，可以直接写：
# groups_sheet_name = "groups"
# 如果不确定，保持 None，程序会自动找行数与 Material 一致、列数足够的 sheet
groups_sheet_name = None


# =========================================================
# 3. 关键列名设置
# =========================================================

temp_col = "T_K"
boiling_col = "boiling_T_K"

# Surface tension 列，优先自动识别
surface_col = None
surface_col_candidates = [
    "SurfaceTension_N_m",
    "surface_tension_N_m",
    "Surface_Tension_N_m",
    "SurfaceTension",
    "surface_tension",
    "property_value",
]

# material key 列
material_key_col = "material_key"


# =========================================================
# 4. 基团列位置
# 第 3 列到第 426 列为基团特征
# pandas iloc 使用 0-based，且右端不包含，所以是 2:426
# =========================================================

group_start_col_1based = 3
group_end_col_1based = 426

group_start_idx = group_start_col_1based - 1
group_end_idx_exclusive = group_end_col_1based


# =========================================================
# 5. k 搜索设置
# =========================================================

# k 搜索步长
# 0.001 较精细；如果运行慢，可改为 0.002 或 0.005
k_step = 0.001

# 为避免两个 k 几乎重合，默认要求 k2 - k1 >= 0.05
# 如果你想保留更多物质，可以改成 0.03 或 0.02
min_k_gap = 0.05

# 是否限制 k 的搜索范围。
# None 表示自动从所有物质允许区间 [T_min/Tb, T_max/Tb] 中确定
k_grid_min_user = None
k_grid_max_user = None

# 最多输出前多少组 k 候选结果
top_n_k_pairs = 50


# =========================================================
# 6. 工具函数
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


def auto_find_column(df, candidates, col_type):
    """
    自动识别列名，大小写不敏感。
    """
    lower_map = {str(c).lower(): c for c in df.columns}

    for col in candidates:
        if col in df.columns:
            return col

    for col in candidates:
        if col.lower() in lower_map:
            return lower_map[col.lower()]

    raise ValueError(
        f"没有找到 {col_type} 列。\n"
        f"候选列名为：{candidates}\n"
        f"当前表格列名为：{list(df.columns)}"
    )


def auto_find_groups_sheet(xls, df_material, data_sheet_name, material_sheet_name):
    """
    自动寻找 groups sheet。

    条件：
        1. 不是 Data sheet
        2. 不是 Material sheet
        3. 行数等于 Material 行数
        4. 列数至少达到 group_end_col_1based
    """
    candidate_sheets = []

    for sheet in xls.sheet_names:
        if sheet in [data_sheet_name, material_sheet_name]:
            continue

        try:
            tmp = pd.read_excel(dataset_file, sheet_name=sheet, nrows=5)
            n_cols = len(tmp.columns)

            tmp_rows = pd.read_excel(dataset_file, sheet_name=sheet, usecols=[0])
            n_rows = len(tmp_rows)

            if n_rows == len(df_material) and n_cols >= group_end_col_1based:
                candidate_sheets.append(sheet)

        except Exception:
            continue

    if len(candidate_sheets) == 1:
        return candidate_sheets[0]

    if len(candidate_sheets) == 0:
        raise ValueError(
            "没有自动找到基团组成 sheet。\n"
            "要求：该 sheet 行数等于 Material_with_Tb_cleaned，且列数至少 426。\n"
            "请手动设置 groups_sheet_name。"
        )

    raise ValueError(
        f"自动找到多个可能的基团 sheet: {candidate_sheets}\n"
        f"请手动设置 groups_sheet_name。"
    )


def interpolate_surface_vs_T_one_material(group, target_T, temp_col, surface_col):
    """
    对单个物质，在 SurfaceTension_N_m vs T_K 空间做线性插值。

    注意：
        液体表面张力通常随温度升高下降，在较窄温度区间内可近似线性。
        因此这里直接使用 y = SurfaceTension_N_m, x = T_K 插值。
    """
    g = group[[temp_col, surface_col]].copy()

    g[temp_col] = pd.to_numeric(g[temp_col], errors="coerce")
    g[surface_col] = pd.to_numeric(g[surface_col], errors="coerce")

    g = g.dropna(subset=[temp_col, surface_col])
    g = g[
        np.isfinite(g[temp_col])
        & np.isfinite(g[surface_col])
        & (g[surface_col] > 0)
    ]

    if len(g) < 2:
        return np.nan, "failed_less_than_2_points"

    # 同一个温度如果仍有重复值，对表面张力取平均
    g = (
        g
        .groupby(temp_col, as_index=False)[surface_col]
        .mean()
        .sort_values(temp_col)
    )

    if len(g) < 2:
        return np.nan, "failed_less_than_2_unique_T"

    T_values = g[temp_col].values.astype(float)
    surface_values = g[surface_col].values.astype(float)

    T_min = float(np.min(T_values))
    T_max = float(np.max(T_values))

    eps = 1e-9
    if not (T_min - eps <= target_T <= T_max + eps):
        return np.nan, "failed_target_T_out_of_range"

    try:
        surface_interp = float(np.interp(float(target_T), T_values, surface_values))

        if not np.isfinite(surface_interp):
            return np.nan, "failed_nonfinite_result"

        if surface_interp <= 0:
            return np.nan, "failed_nonpositive_interpolated_surface"

        return surface_interp, "ok_surface_T_linear_interpolation"

    except Exception as e:
        return np.nan, f"failed_interpolation_error: {e}"


# =========================================================
# 7. 读取 Excel
# =========================================================

if not dataset_file.exists():
    raise FileNotFoundError(f"没有找到输入文件: {dataset_file}")

xls = pd.ExcelFile(dataset_file)

print("输入文件包含的 sheet:")
print(xls.sheet_names)

if data_sheet_name not in xls.sheet_names:
    raise ValueError(f"没有找到 sheet: {data_sheet_name}")

if material_sheet_name not in xls.sheet_names:
    raise ValueError(f"没有找到 sheet: {material_sheet_name}")

df_data = pd.read_excel(dataset_file, sheet_name=data_sheet_name)
df_material = pd.read_excel(dataset_file, sheet_name=material_sheet_name)

print("\nData 行数:", len(df_data))
print("Material 物质数:", len(df_material))


# =========================================================
# 8. 自动识别 / 读取基团 sheet
# =========================================================

if groups_sheet_name is None:
    groups_sheet_name = auto_find_groups_sheet(
        xls,
        df_material,
        data_sheet_name,
        material_sheet_name
    )

print("使用的基团 sheet:", groups_sheet_name)

df_groups = pd.read_excel(dataset_file, sheet_name=groups_sheet_name)

if len(df_groups) != len(df_material):
    raise ValueError(
        f"基团 sheet 行数 {len(df_groups)} 与 Material sheet 行数 {len(df_material)} 不一致。"
    )

if len(df_groups.columns) < group_end_col_1based:
    raise ValueError(
        f"基团 sheet 列数只有 {len(df_groups.columns)}，不足 426 列。"
    )

group_cols = list(df_groups.columns[group_start_idx:group_end_idx_exclusive])

print("基团列数量:", len(group_cols))
print("基团列范围:", group_cols[0], "->", group_cols[-1])


# =========================================================
# 9. 生成 / 检查 material_key
# =========================================================

if material_key_col not in df_data.columns:
    df_data[material_key_col] = df_data.apply(build_material_key, axis=1)

if material_key_col not in df_material.columns:
    df_material[material_key_col] = df_material.apply(build_material_key, axis=1)

df_data[material_key_col] = df_data[material_key_col].astype(str).str.strip()
df_material[material_key_col] = df_material[material_key_col].astype(str).str.strip()

# groups sheet 如果没有 material_key，也按 Material 顺序补上
if material_key_col not in df_groups.columns:
    df_groups.insert(0, material_key_col, df_material[material_key_col].values)

df_groups[material_key_col] = df_groups[material_key_col].astype(str).str.strip()

df_material = df_material.copy()
df_groups = df_groups.copy()

# 原始物质索引，后面用于按顺序同步筛选 Material 和 groups
if "original_material_index" not in df_material.columns:
    df_material.insert(0, "original_material_index", np.arange(len(df_material)))

if "original_material_index" not in df_groups.columns:
    df_groups.insert(0, "original_material_index", np.arange(len(df_groups)))


# =========================================================
# 10. 自动识别 Surface tension 列
# =========================================================

if surface_col is None:
    surface_col = auto_find_column(df_data, surface_col_candidates, "Surface tension")

print("使用的 Surface tension 列:", surface_col)


# =========================================================
# 11. 数值化
# =========================================================

df_data[temp_col] = pd.to_numeric(df_data[temp_col], errors="coerce")
df_data[surface_col] = pd.to_numeric(df_data[surface_col], errors="coerce")

if boiling_col not in df_material.columns:
    raise ValueError(f"Material sheet 中没有找到沸点列: {boiling_col}")

df_material[boiling_col] = pd.to_numeric(df_material[boiling_col], errors="coerce")

# 如果 Data 中没有 boiling_T_K，合并一个进去
if boiling_col not in df_data.columns:
    df_data = df_data.merge(
        df_material[[material_key_col, boiling_col]],
        on=material_key_col,
        how="left"
    )


# =========================================================
# 12. 按物质计算温度区间和允许 k 区间
# =========================================================

material_rows = []

data_grouped = {
    str(key).strip(): group.copy()
    for key, group in df_data.groupby(material_key_col, sort=False)
}

for _, mat_row in df_material.iterrows():
    material_key = str(mat_row[material_key_col]).strip()
    group = data_grouped.get(material_key, pd.DataFrame())

    if len(group) == 0:
        n_points = 0
        T_min = np.nan
        T_max = np.nan
        T_range = np.nan
        surface_min = np.nan
        surface_max = np.nan
    else:
        g_valid = group.dropna(subset=[temp_col, surface_col]).copy()
        g_valid = g_valid[
            np.isfinite(g_valid[temp_col])
            & np.isfinite(g_valid[surface_col])
            & (g_valid[surface_col] > 0)
        ]

        n_points = len(g_valid)

        if n_points > 0:
            T_min = float(g_valid[temp_col].min())
            T_max = float(g_valid[temp_col].max())
            T_range = T_max - T_min
            surface_min = float(g_valid[surface_col].min())
            surface_max = float(g_valid[surface_col].max())
        else:
            T_min = np.nan
            T_max = np.nan
            T_range = np.nan
            surface_min = np.nan
            surface_max = np.nan

    Tb = mat_row[boiling_col]

    if (
        pd.notna(Tb)
        and np.isfinite(Tb)
        and Tb > 0
        and pd.notna(T_min)
        and pd.notna(T_max)
    ):
        k_low = T_min / Tb
        k_high = T_max / Tb
        allowed_k_width = k_high - k_low
        allowed_ref_T_width_at_Tb = T_max - T_min
    else:
        k_low = np.nan
        k_high = np.nan
        allowed_k_width = np.nan
        allowed_ref_T_width_at_Tb = np.nan

    row = {
        "original_material_index": int(mat_row["original_material_index"]),
        material_key_col: material_key,
        "n_points": n_points,
        "T_min": T_min,
        "T_max": T_max,
        "T_range": T_range,
        "SurfaceTension_min_N_m": surface_min,
        "SurfaceTension_max_N_m": surface_max,
        boiling_col: Tb,
        "k_low": k_low,
        "k_high": k_high,
        "allowed_k_width": allowed_k_width,
        "allowed_ref_T_width_at_Tb": allowed_ref_T_width_at_Tb,
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
        "pubchem_inchikey",
        "fit_status",
        "RSQ_Surface_vs_T",
        "slope_Surface_vs_T",
    ]:
        if col in df_material.columns:
            row[col] = mat_row[col]

    material_rows.append(row)

df_material_k = pd.DataFrame(material_rows)

valid_interval_mask = (
    df_material_k["k_low"].notna()
    & df_material_k["k_high"].notna()
    & np.isfinite(df_material_k["k_low"])
    & np.isfinite(df_material_k["k_high"])
    & (df_material_k["k_high"] > df_material_k["k_low"])
)

df_valid_k = df_material_k[valid_interval_mask].copy()

print("\n可用于 k 搜索的物质数:", len(df_valid_k))

if len(df_valid_k) == 0:
    raise ValueError("没有任何物质具有有效的温度区间和沸点，无法搜索 k。")


# =========================================================
# 13. 搜索两个最优 k
# 目标：最大化同时覆盖 k1 和 k2 的物质数
# 条件：k_low <= k1 < k2 <= k_high
# =========================================================

k_min_auto = float(np.floor(df_valid_k["k_low"].min() / k_step) * k_step)
k_max_auto = float(np.ceil(df_valid_k["k_high"].max() / k_step) * k_step)

k_grid_min = k_grid_min_user if k_grid_min_user is not None else k_min_auto
k_grid_max = k_grid_max_user if k_grid_max_user is not None else k_max_auto

if k_grid_max <= k_grid_min:
    raise ValueError("k 搜索范围无效。")

k_grid = np.arange(k_grid_min, k_grid_max + 0.5 * k_step, k_step)

k_low_arr = df_valid_k["k_low"].values.astype(float)
k_high_arr = df_valid_k["k_high"].values.astype(float)

# C[g, m] = 第 g 个 k 是否落在第 m 个物质允许区间内
C = (
    (k_grid[:, None] >= k_low_arr[None, :])
    & (k_grid[:, None] <= k_high_arr[None, :])
).astype(np.uint16)

coverage_matrix = C @ C.T

# 只考虑 k2 - k1 >= min_k_gap
gap_matrix = k_grid[None, :] - k_grid[:, None]
valid_pair_mask = gap_matrix >= min_k_gap

if not valid_pair_mask.any():
    raise ValueError(
        f"没有满足 min_k_gap={min_k_gap} 的 k 对。"
        f"可以把 min_k_gap 改小。"
    )

coverage_for_search = coverage_matrix.astype(float)
coverage_for_search[~valid_pair_mask] = -1

best_coverage = int(np.max(coverage_for_search))

if best_coverage <= 0:
    raise ValueError("没有任何 k 对能同时覆盖至少一个物质。")

best_pair_indices = np.argwhere(coverage_for_search == best_coverage)

# 如果覆盖数相同，优先选择 k 间隔更大的组合
best_gaps = gap_matrix[best_pair_indices[:, 0], best_pair_indices[:, 1]]
best_choice = best_pair_indices[np.argmax(best_gaps)]

best_i, best_j = int(best_choice[0]), int(best_choice[1])

best_k1 = float(k_grid[best_i])
best_k2 = float(k_grid[best_j])

if best_k1 > best_k2:
    best_k1, best_k2 = best_k2, best_k1

print("\n========== 最优 k 搜索结果 ==========")
print("best_k1:", f"{best_k1:.10f}")
print("best_k2:", f"{best_k2:.10f}")
print("k_gap:", f"{best_k2 - best_k1:.10f}")
print("同时覆盖物质数:", best_coverage)


# 输出 top k pairs
top_pairs = []

valid_i, valid_j = np.where(valid_pair_mask)
pair_coverages = coverage_matrix[valid_i, valid_j].astype(int)

if len(pair_coverages) > 0:
    order = np.lexsort((
        -(k_grid[valid_j] - k_grid[valid_i]),
        -pair_coverages,
    ))

    for idx in order[:top_n_k_pairs]:
        i = valid_i[idx]
        j = valid_j[idx]

        top_pairs.append({
            "k1": float(k_grid[i]),
            "k2": float(k_grid[j]),
            "k_gap": float(k_grid[j] - k_grid[i]),
            "covered_material_count": int(coverage_matrix[i, j]),
        })

df_top_k_pairs = pd.DataFrame(top_pairs)


# =========================================================
# 14. 根据 best_k1 / best_k2 筛选物质
# =========================================================

df_material_k["ref_T1_K"] = best_k1 * df_material_k[boiling_col]
df_material_k["ref_T2_K"] = best_k2 * df_material_k[boiling_col]
df_material_k["ref_T_gap_K"] = df_material_k["ref_T2_K"] - df_material_k["ref_T1_K"]

df_material_k["covered_by_best_k1"] = (
    df_material_k["k_low"].notna()
    & (df_material_k["k_low"] <= best_k1)
    & (best_k1 <= df_material_k["k_high"])
)

df_material_k["covered_by_best_k2"] = (
    df_material_k["k_low"].notna()
    & (df_material_k["k_low"] <= best_k2)
    & (best_k2 <= df_material_k["k_high"])
)

df_material_k["covered_by_both_best_k"] = (
    df_material_k["covered_by_best_k1"]
    & df_material_k["covered_by_best_k2"]
)

df_selected_info = df_material_k[
    df_material_k["covered_by_both_best_k"] == True
].copy()

selected_material_indices = (
    df_selected_info["original_material_index"]
    .astype(int)
    .sort_values()
    .tolist()
)

selected_material_keys = set(
    df_selected_info[material_key_col].astype(str).str.strip()
)

print("\n同时被两个 k 覆盖的物质数:", len(selected_material_indices))

if len(selected_material_indices) == 0:
    raise ValueError("没有筛选出任何同时覆盖 k1 和 k2 的物质。")


# =========================================================
# 15. 筛选 Data / Material / Groups
# =========================================================

df_data_selected = df_data[
    df_data[material_key_col].astype(str).str.strip().isin(selected_material_keys)
].copy()

df_material_selected = df_material.iloc[selected_material_indices].copy()
df_groups_selected = df_groups.iloc[selected_material_indices].copy()

# 将覆盖信息合并到 material selected
merge_cols = [
    "original_material_index",
    material_key_col,
    "n_points",
    "T_min",
    "T_max",
    "T_range",
    "SurfaceTension_min_N_m",
    "SurfaceTension_max_N_m",
    boiling_col,
    "k_low",
    "k_high",
    "allowed_k_width",
    "allowed_ref_T_width_at_Tb",
    "ref_T1_K",
    "ref_T2_K",
    "ref_T_gap_K",
    "covered_by_best_k1",
    "covered_by_best_k2",
    "covered_by_both_best_k",
]

merge_cols = [c for c in merge_cols if c in df_material_k.columns]

df_material_selected = df_material_selected.merge(
    df_material_k[merge_cols],
    on=["original_material_index", material_key_col],
    how="left",
    suffixes=("", "_from_k_search")
)


# =========================================================
# 16. 在 k1*Tb 和 k2*Tb 处计算 Surface tension 插值理论值
# =========================================================

interp_rows = []

for _, row in df_selected_info.sort_values("original_material_index").iterrows():
    material_key = str(row[material_key_col]).strip()
    material_idx = int(row["original_material_index"])

    group = data_grouped.get(material_key, pd.DataFrame()).copy()

    Tb = float(row[boiling_col])
    T_k1Tb = float(best_k1 * Tb)
    T_k2Tb = float(best_k2 * Tb)

    surface_k1, status_k1 = interpolate_surface_vs_T_one_material(
        group,
        T_k1Tb,
        temp_col=temp_col,
        surface_col=surface_col,
    )

    surface_k2, status_k2 = interpolate_surface_vs_T_one_material(
        group,
        T_k2Tb,
        temp_col=temp_col,
        surface_col=surface_col,
    )

    out = {
        "original_material_index": material_idx,
        material_key_col: material_key,

        "k1": best_k1,
        "k1_times_boiling_T_K": T_k1Tb,
        "SurfaceTension_N_m_interp_at_k1Tb": surface_k1,
        "interp_status_k1": status_k1,

        "k2": best_k2,
        "k2_times_boiling_T_K": T_k2Tb,
        "SurfaceTension_N_m_interp_at_k2Tb": surface_k2,
        "interp_status_k2": status_k2,

        "boiling_T_K": Tb,
        "T_min": row["T_min"],
        "T_max": row["T_max"],
        "T_range": row["T_range"],
        "n_points": row["n_points"],
        "k_low": row["k_low"],
        "k_high": row["k_high"],
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
        "pubchem_inchikey",
        "fit_status",
        "RSQ_Surface_vs_T",
        "slope_Surface_vs_T",
    ]:
        if col in row.index:
            out[col] = row[col]

    interp_rows.append(out)

df_interpolated = pd.DataFrame(interp_rows)

print("\n========== 插值结果 ==========")
print(
    "k1 插值成功物质数:",
    int((df_interpolated["interp_status_k1"] == "ok_surface_T_linear_interpolation").sum())
)
print(
    "k2 插值成功物质数:",
    int((df_interpolated["interp_status_k2"] == "ok_surface_T_linear_interpolation").sum())
)


# =========================================================
# 17. 生成最终建模表：基团 + 两个参考点表面张力值
# =========================================================

interp_cols_for_model = [
    "original_material_index",
    material_key_col,
    "k1",
    "k1_times_boiling_T_K",
    "SurfaceTension_N_m_interp_at_k1Tb",
    "k2",
    "k2_times_boiling_T_K",
    "SurfaceTension_N_m_interp_at_k2Tb",
    "boiling_T_K",
    "T_min",
    "T_max",
    "T_range",
    "n_points",
    "interp_status_k1",
    "interp_status_k2",
]

interp_cols_for_model = [
    c for c in interp_cols_for_model
    if c in df_interpolated.columns
]

df_final_model_table = df_groups_selected.merge(
    df_interpolated[interp_cols_for_model],
    on=["original_material_index", material_key_col],
    how="left"
)


# =========================================================
# 18. Summary
# =========================================================

summary = pd.DataFrame([
    {"item": "dataset_file", "value": str(dataset_file)},
    {"item": "data_sheet_name", "value": data_sheet_name},
    {"item": "material_sheet_name", "value": material_sheet_name},
    {"item": "groups_sheet_name", "value": groups_sheet_name},
    {"item": "output_file", "value": str(output_file)},

    {"item": "temp_col", "value": temp_col},
    {"item": "surface_col", "value": surface_col},
    {"item": "boiling_col", "value": boiling_col},

    {"item": "original_data_rows", "value": len(df_data)},
    {"item": "original_material_count", "value": len(df_material)},
    {"item": "group_feature_count", "value": len(group_cols)},

    {"item": "valid_material_count_for_k_search", "value": len(df_valid_k)},
    {"item": "k_step", "value": k_step},
    {"item": "min_k_gap", "value": min_k_gap},
    {"item": "k_grid_min", "value": k_grid_min},
    {"item": "k_grid_max", "value": k_grid_max},

    {"item": "best_k1", "value": best_k1},
    {"item": "best_k2", "value": best_k2},
    {"item": "best_k_gap", "value": best_k2 - best_k1},
    {"item": "covered_by_both_k_material_count", "value": len(df_selected_info)},

    {
        "item": "k1_interpolation_success_count",
        "value": int((df_interpolated["interp_status_k1"] == "ok_surface_T_linear_interpolation").sum())
    },
    {
        "item": "k2_interpolation_success_count",
        "value": int((df_interpolated["interp_status_k2"] == "ok_surface_T_linear_interpolation").sum())
    },
])


# =========================================================
# 19. 保存 Excel
# =========================================================

with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_data_selected.to_excel(writer, sheet_name="Data_selected", index=False)
    df_material_selected.to_excel(writer, sheet_name="Material_selected", index=False)
    df_groups_selected.to_excel(writer, sheet_name="Groups_selected", index=False)

    df_material_k.to_excel(writer, sheet_name="All_Material_k_Intervals", index=False)
    df_top_k_pairs.to_excel(writer, sheet_name="Top_k_Pairs", index=False)
    df_selected_info.to_excel(writer, sheet_name="Covered_By_Both_k", index=False)

    df_interpolated.to_excel(writer, sheet_name="Interpolated_k1_k2", index=False)
    df_final_model_table.to_excel(writer, sheet_name="Final_Model_Table", index=False)

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
print("1. Final_Model_Table：基团特征 + k1/k2 两个参考点表面张力")
print("2. Interpolated_k1_k2：每个物质两个参考点的插值结果")
print("3. Covered_By_Both_k：同时被 k1/k2 覆盖的物质")
print("4. All_Material_k_Intervals：所有物质允许的 k 区间")
print("5. Top_k_Pairs：覆盖物质数最多的 k 组合")