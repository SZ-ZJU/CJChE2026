# -*- coding: utf-8 -*-
"""
Surface tension liquid-gas 数据重新清洗脚本：
增加“同一物质只保留数据点最多的 1 个 title 来源”的版本

输入：
    thermoml_surface_tension_liquid_gas_pure_organic_liquid.xlsx

输出：
    thermoml_surface_tension_liquid_gas_Liquid_remove_dupT_materials_min3_Tgt20.xlsx

主表 sheet：
    Surface_Liquid_Final

新增清洗规则：
    0. 来源一致性筛选：
       对同一 material_key，按 title 区分数据来源；
       每个物质只保留数据点最多的 1 个 title 来源；
       被保留后的数据继续执行后续规则。

原有清洗规则：
    1. 删除 T_K 或 SurfaceTension_N_m 为空的数据点
    2. 删除 SurfaceTension_N_m <= 0 的数据点
    3. 对同一 material_key + T_round 的重复温度点：
        - 如果同温度下表面张力差异不大，则聚合为一个点，表面张力取平均值
        - 如果同温度下表面张力差异过大，则只删除这个重复温度点
        - 不再因为一个重复温度点直接删除整个物质
    4. 每个物质至少保留 min_points_per_material 个温度点
    5. 每个物质温度区间要求 T_range > min_temp_range
"""

import pandas as pd
import numpy as np
from pathlib import Path


# =========================================================
# 1. 输入输出文件
# =========================================================

input_file = Path("thermoml_surface_tension_liquid_gas_pure_organic_liquid.xlsx")

# 如果文件只有一个 sheet，就保持 None，会自动读取第一个 sheet
input_sheet = None

output_file = Path("thermoml_surface_tension_liquid_gas_Liquid_remove_dupT_materials_min3_Tgt20.xlsx")


# =========================================================
# 2. 基本设置
# =========================================================

temp_col = "T_K"
surface_col = "SurfaceTension_N_m"

# 以 title 区分来源
source_col = "title"

# 每个物质最多保留几个 title 来源
# 你当前要求只保留 1 个 title
max_titles_per_material = 1

# 如果 title 缺失，是否允许用 source_file 兜底
# True：title 缺失时使用 source_file 作为来源键
# False：title 缺失统一记为 UNKNOWN_TITLE
use_source_file_when_title_missing = True

# 如果表里有 P_kPa，就额外统计；没有也不影响
pressure_col = "P_kPa"

# 温度去重精度
# 1 表示按 0.1 K 判断重复温度；如果你想更严格，可以改成 6
temp_round_decimals = 1

# 每个物质至少需要几个温度点
min_points_per_material = 3

# 温度区间阈值
min_temp_range = 20.0

# 是否删除非正表面张力
remove_non_positive_surface_tension = True

# 重复温度点聚合规则
# 相对差异阈值：0.01 表示 1%
duplicate_relative_tolerance = 0.01

# 绝对差异阈值，单位 N/m
# 0.0005 N/m = 0.5 mN/m
duplicate_absolute_tolerance_N_m = 0.0005

# 对可接受重复点的处理方式：
# mean: 表面张力取均值，温度取均值，其余元数据保留第一条
# first: 保留第一条
duplicate_aggregate_method = "mean"


# =========================================================
# 3. 读取数据
# =========================================================

if not input_file.exists():
    raise FileNotFoundError(f"没有找到输入文件: {input_file}")

xls = pd.ExcelFile(input_file)

print("输入文件包含的 sheet:")
print(xls.sheet_names)

if input_sheet is None:
    input_sheet_used = xls.sheet_names[0]
else:
    input_sheet_used = input_sheet

if input_sheet_used not in xls.sheet_names:
    raise ValueError(
        f"没有找到 sheet: {input_sheet_used}\n"
        f"当前文件中可用的 sheet 为: {xls.sheet_names}"
    )

df = pd.read_excel(input_file, sheet_name=input_sheet_used)

print("\n读取 sheet:", input_sheet_used)
print("原始数据点数:", len(df))
print("原始列名:")
print(list(df.columns))

if temp_col not in df.columns:
    raise ValueError(f"没有找到温度列: {temp_col}")

if surface_col not in df.columns:
    if "property_value" in df.columns:
        print(f"警告：没有找到 {surface_col}，将使用 property_value 作为表面张力列。")
        df[surface_col] = df["property_value"]
    else:
        raise ValueError(f"没有找到表面张力列: {surface_col}，且没有 property_value 可替代。")


# =========================================================
# 4. 自动生成 material_key
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
    material_key 优先级：
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
# 5. 数值化并构造温度重复判断键
# =========================================================

df[temp_col] = pd.to_numeric(df[temp_col], errors="coerce")
df[surface_col] = pd.to_numeric(df[surface_col], errors="coerce")

if pressure_col in df.columns:
    df[pressure_col] = pd.to_numeric(df[pressure_col], errors="coerce")

before_drop_na = len(df)

df = df[
    df[temp_col].notna()
    & df[surface_col].notna()
].copy()

print("\n删除 T 或 SurfaceTension 为空的数据点数:", before_drop_na - len(df))

if remove_non_positive_surface_tension:
    before_drop_non_positive = len(df)
    df = df[df[surface_col] > 0].copy()
    print("删除 SurfaceTension <= 0 的数据点数:", before_drop_non_positive - len(df))


# =========================================================
# 5.5 来源一致性筛选：每个物质只保留数据点最多的 1 个 title
# =========================================================

def build_source_title(row):
    """
    用 title 区分数据来源。
    如果 title 缺失，可以用 source_file 兜底。
    """
    if source_col in row.index and is_valid_value(row[source_col]):
        return str(row[source_col]).strip()

    if use_source_file_when_title_missing and "source_file" in row.index and is_valid_value(row["source_file"]):
        return f"SOURCE_FILE::{str(row['source_file']).strip()}"

    return "UNKNOWN_TITLE"


df["_source_title"] = df.apply(build_source_title, axis=1)

source_summary_rows = []
kept_source_keys = []

for material_key, group in df.groupby("material_key", sort=False):
    g = group.copy()

    source_stats = (
        g.groupby("_source_title", dropna=False)
        .agg(
            n_rows=("_source_title", "size"),
            T_min=(temp_col, "min"),
            T_max=(temp_col, "max"),
            SurfaceTension_min_N_m=(surface_col, "min"),
            SurfaceTension_max_N_m=(surface_col, "max"),
            first_original_index=("_source_title", lambda x: x.index.min()),
        )
        .reset_index()
    )

    source_stats["T_range"] = source_stats["T_max"] - source_stats["T_min"]

    # 排序规则：
    # 1. 数据点数最多
    # 2. 温度区间最大
    # 3. 原始顺序靠前
    source_stats = source_stats.sort_values(
        ["n_rows", "T_range", "first_original_index"],
        ascending=[False, False, True]
    ).reset_index(drop=True)

    keep_titles = source_stats["_source_title"].head(max_titles_per_material).tolist()

    for _, r in source_stats.iterrows():
        row = {
            "material_key": material_key,
            "source_title": r["_source_title"],
            "n_rows": r["n_rows"],
            "T_min": r["T_min"],
            "T_max": r["T_max"],
            "T_range": r["T_range"],
            "SurfaceTension_min_N_m": r["SurfaceTension_min_N_m"],
            "SurfaceTension_max_N_m": r["SurfaceTension_max_N_m"],
            "source_rank_by_n_rows": int(source_stats.index[source_stats["_source_title"] == r["_source_title"]][0]) + 1,
            "source_decision": "kept" if r["_source_title"] in keep_titles else "removed_by_title_source_filter",
        }

        for col in [
            "compound_name",
            "cas",
            "formula",
            "inchikey",
            "smiles",
            "phase",
            "property_name",
            "property_unit",
        ]:
            if col in g.columns:
                row[col] = g[col].iloc[0]

        source_summary_rows.append(row)

    for title in keep_titles:
        kept_source_keys.append((material_key, title))


kept_source_key_df = pd.DataFrame(
    kept_source_keys,
    columns=["material_key", "_source_title"]
)

df_source_summary = pd.DataFrame(source_summary_rows)

df_before_source_filter = df.copy()

df_after_source_filter = df.merge(
    kept_source_key_df,
    on=["material_key", "_source_title"],
    how="inner"
).copy()

df_removed_by_source = df_before_source_filter.merge(
    kept_source_key_df,
    on=["material_key", "_source_title"],
    how="left",
    indicator=True
)

df_removed_by_source = df_removed_by_source[
    df_removed_by_source["_merge"] == "left_only"
].drop(columns=["_merge"]).copy()

df_removed_by_source["remove_reason"] = (
    f"source_title_not_top_{max_titles_per_material}_by_n_rows"
)

print("\n========== 来源一致性筛选结果 ==========")
print("来源筛选前数据点数:", len(df_before_source_filter))
print("来源筛选前物质数:", df_before_source_filter["material_key"].nunique())
print("来源筛选后数据点数:", len(df_after_source_filter))
print("来源筛选后物质数:", df_after_source_filter["material_key"].nunique())
print("来源筛选删除数据点数:", len(df_removed_by_source))
print("每个物质最多保留 title 数:", max_titles_per_material)

df = df_after_source_filter.copy()

df["_original_order"] = np.arange(len(df))
df["_T_round"] = df[temp_col].round(temp_round_decimals)


# =========================================================
# 6. 放宽版重复温度处理
# =========================================================
# 对同一 material_key + _T_round：
#   - 只有一条：直接保留
#   - 多条且表面张力差异小：聚合为一条
#   - 多条且表面张力差异大：删除该温度点，不删除整个物质
# =========================================================

def aggregate_duplicate_group(group):
    """
    对同一 material_key + _T_round 的重复组进行聚合。
    默认保留第一条元信息，数值列中 T_K 和 SurfaceTension_N_m 用均值。
    """
    group = group.sort_values("_original_order").copy()
    row = group.iloc[0].copy()

    if duplicate_aggregate_method == "mean":
        row[temp_col] = group[temp_col].mean()
        row[surface_col] = group[surface_col].mean()

        if "property_value" in group.columns:
            row["property_value"] = pd.to_numeric(
                group["property_value"],
                errors="coerce"
            ).mean()

        if "property_uncertainty" in group.columns:
            row["property_uncertainty"] = pd.to_numeric(
                group["property_uncertainty"],
                errors="coerce"
            ).mean()

        if "T_uncertainty" in group.columns:
            row["T_uncertainty"] = pd.to_numeric(
                group["T_uncertainty"],
                errors="coerce"
            ).mean()

        if pressure_col in group.columns:
            valid_p = pd.to_numeric(group[pressure_col], errors="coerce")
            if valid_p.notna().any():
                row[pressure_col] = valid_p.mean()

    row["duplicate_temperature_handling"] = "aggregated_duplicate_temperature"
    row["duplicate_temperature_n_rows"] = len(group)
    row["duplicate_temperature_surface_min_N_m"] = group[surface_col].min()
    row["duplicate_temperature_surface_max_N_m"] = group[surface_col].max()
    row["duplicate_temperature_surface_range_N_m"] = group[surface_col].max() - group[surface_col].min()

    return row


kept_rows = []
aggregated_rows = []
removed_conflict_rows = []
duplicate_summary_rows = []

for (material_key, t_round), group in df.groupby(["material_key", "_T_round"], sort=False):
    group = group.sort_values("_original_order").copy()

    if len(group) == 1:
        row = group.iloc[0].copy()
        row["duplicate_temperature_handling"] = "single"
        row["duplicate_temperature_n_rows"] = 1
        row["duplicate_temperature_surface_min_N_m"] = row[surface_col]
        row["duplicate_temperature_surface_max_N_m"] = row[surface_col]
        row["duplicate_temperature_surface_range_N_m"] = 0.0
        kept_rows.append(row)
        continue

    surface_values = pd.to_numeric(group[surface_col], errors="coerce").dropna()

    if len(surface_values) == 0:
        conflict_group = group.copy()
        conflict_group["remove_reason"] = "duplicate_temperature_no_valid_surface_tension"
        removed_conflict_rows.append(conflict_group)
        continue

    surface_min = float(surface_values.min())
    surface_max = float(surface_values.max())
    surface_mean = float(surface_values.mean())
    surface_range = surface_max - surface_min

    if abs(surface_mean) > 0:
        rel_range = surface_range / abs(surface_mean)
    else:
        rel_range = np.inf

    can_aggregate = (
        (rel_range <= duplicate_relative_tolerance)
        or (surface_range <= duplicate_absolute_tolerance_N_m)
    )

    summary_base = {
        "material_key": material_key,
        "_T_round": t_round,
        "n_rows_at_same_temperature": len(group),
        "T_min": group[temp_col].min(),
        "T_max": group[temp_col].max(),
        "SurfaceTension_min_N_m": surface_min,
        "SurfaceTension_max_N_m": surface_max,
        "SurfaceTension_mean_N_m": surface_mean,
        "SurfaceTension_range_N_m": surface_range,
        "SurfaceTension_relative_range": rel_range,
        "decision": "aggregate" if can_aggregate else "remove_this_temperature_point",
    }

    for col in [
        "compound_name",
        "cas",
        "formula",
        "inchikey",
        "smiles",
        "phase",
        "property_name",
        "property_unit",
        "method",
        "doi",
        "year",
        "journal",
        "source_file",
        "title",
        "_source_title",
    ]:
        if col in group.columns:
            summary_base[col] = group[col].iloc[0]

    duplicate_summary_rows.append(summary_base)

    if can_aggregate:
        agg_row = aggregate_duplicate_group(group)
        kept_rows.append(agg_row)
        aggregated_rows.append(group.copy())
    else:
        conflict_group = group.copy()
        conflict_group["remove_reason"] = "duplicate_temperature_surface_tension_conflict"
        conflict_group["SurfaceTension_range_N_m_at_same_T"] = surface_range
        conflict_group["SurfaceTension_relative_range_at_same_T"] = rel_range
        removed_conflict_rows.append(conflict_group)


df_after_dup_temp_rule = pd.DataFrame(kept_rows)

if len(df_after_dup_temp_rule) > 0:
    df_after_dup_temp_rule = df_after_dup_temp_rule.sort_values(
        ["material_key", temp_col, "_original_order"],
        na_position="last"
    ).reset_index(drop=True)

if len(aggregated_rows) > 0:
    df_aggregated_duplicate_source_rows = pd.concat(aggregated_rows, ignore_index=True)
else:
    df_aggregated_duplicate_source_rows = pd.DataFrame(columns=df.columns)

if len(removed_conflict_rows) > 0:
    df_removed_duplicate_materials = pd.concat(removed_conflict_rows, ignore_index=True)
else:
    df_removed_duplicate_materials = pd.DataFrame(columns=list(df.columns) + ["remove_reason"])

df_duplicate_temperature_all_rows = df[
    df.duplicated(subset=["material_key", "_T_round"], keep=False)
].copy()

duplicate_summary = pd.DataFrame(duplicate_summary_rows)

polluted_material_keys = (
    df_duplicate_temperature_all_rows["material_key"]
    .dropna()
    .unique()
)

print("\n========== 放宽版重复温度处理结果 ==========")
print("存在重复温度点的物质数:", len(polluted_material_keys))
print("重复温度相关原始行数:", len(df_duplicate_temperature_all_rows))
print("可聚合重复温度源行数:", len(df_aggregated_duplicate_source_rows))
print("冲突重复温度删除行数:", len(df_removed_duplicate_materials))
print("重复温度处理后保留数据点数:", len(df_after_dup_temp_rule))
print(
    "重复温度处理后保留物质数:",
    df_after_dup_temp_rule["material_key"].nunique() if len(df_after_dup_temp_rule) > 0 else 0
)


# =========================================================
# 7. 删除剩余数据中点数少于 min_points_per_material 的物质
# =========================================================

material_counts = (
    df_after_dup_temp_rule
    .groupby("material_key")
    .size()
    .reset_index(name="n_points_after_duplicate_temperature_processing")
)

valid_material_keys_min_points = material_counts.loc[
    material_counts["n_points_after_duplicate_temperature_processing"] >= min_points_per_material,
    "material_key"
]

too_few_material_keys = material_counts.loc[
    material_counts["n_points_after_duplicate_temperature_processing"] < min_points_per_material,
    "material_key"
]

df_removed_too_few_points = df_after_dup_temp_rule[
    df_after_dup_temp_rule["material_key"].isin(too_few_material_keys)
].copy()

df_removed_too_few_points["remove_reason"] = (
    f"points_less_than_{min_points_per_material}_after_duplicate_temperature_processing"
)

df_after_min_points = df_after_dup_temp_rule[
    df_after_dup_temp_rule["material_key"].isin(valid_material_keys_min_points)
].copy()

print("\n========== 数据点数筛选结果 ==========")
print(f"删除点数 < {min_points_per_material} 的物质数:", len(too_few_material_keys))
print("删除对应数据点数:", len(df_removed_too_few_points))
print("点数筛选后保留数据点数:", len(df_after_min_points))
print(
    "点数筛选后保留物质数:",
    df_after_min_points["material_key"].nunique() if len(df_after_min_points) > 0 else 0
)


# =========================================================
# 8. 删除温度区间不大于 min_temp_range 的物质
# =========================================================

temp_range_rows = []

for material_key, group in df_after_min_points.groupby("material_key", sort=False):
    temps = pd.to_numeric(group[temp_col], errors="coerce").values.astype(float)
    surfaces = pd.to_numeric(group[surface_col], errors="coerce").values.astype(float)

    if np.all(np.isnan(temps)):
        T_min = np.nan
        T_max = np.nan
        T_range = np.nan
    else:
        T_min = np.nanmin(temps)
        T_max = np.nanmax(temps)
        T_range = T_max - T_min

    row = {
        "material_key": material_key,
        "n_points_after_min_points_filter": len(group),
        "T_min": T_min,
        "T_max": T_max,
        "T_range": T_range,
        "SurfaceTension_min_N_m": np.nanmin(surfaces) if not np.all(np.isnan(surfaces)) else np.nan,
        "SurfaceTension_max_N_m": np.nanmax(surfaces) if not np.all(np.isnan(surfaces)) else np.nan,
        "SurfaceTension_range_N_m": (
            np.nanmax(surfaces) - np.nanmin(surfaces)
            if not np.all(np.isnan(surfaces))
            else np.nan
        ),
    }

    if pressure_col in group.columns:
        ps = pd.to_numeric(group[pressure_col], errors="coerce").values.astype(float)
        row["P_min_kPa"] = np.nanmin(ps) if not np.all(np.isnan(ps)) else np.nan
        row["P_max_kPa"] = np.nanmax(ps) if not np.all(np.isnan(ps)) else np.nan

    for col in [
        "compound_name",
        "cas",
        "formula",
        "inchikey",
        "smiles",
        "phase",
        "property_name",
        "property_unit",
        "method",
        "doi",
        "year",
        "journal",
        "source_file",
        "title",
        "_source_title",
    ]:
        if col in group.columns:
            row[col] = group[col].iloc[0]

    temp_range_rows.append(row)

df_temp_range_summary = pd.DataFrame(temp_range_rows)

valid_temp_range_keys = df_temp_range_summary.loc[
    df_temp_range_summary["T_range"] > min_temp_range,
    "material_key"
]

small_temp_range_keys = df_temp_range_summary.loc[
    (df_temp_range_summary["T_range"].isna())
    | (df_temp_range_summary["T_range"] <= min_temp_range),
    "material_key"
]

df_removed_small_temp_range = df_after_min_points[
    df_after_min_points["material_key"].isin(small_temp_range_keys)
].copy()

df_removed_small_temp_range["remove_reason"] = (
    f"temperature_range_not_greater_than_{min_temp_range:g}K"
)

df_removed_small_temp_range_summary = df_temp_range_summary[
    df_temp_range_summary["material_key"].isin(small_temp_range_keys)
].copy()

df_removed_small_temp_range_summary["remove_reason"] = (
    f"temperature_range_not_greater_than_{min_temp_range:g}K"
)

df_final = df_after_min_points[
    df_after_min_points["material_key"].isin(valid_temp_range_keys)
].copy()

print("\n========== 温度区间筛选结果 ==========")
print(f"删除温度区间 <= {min_temp_range:g} K 的物质数:", len(small_temp_range_keys))
print("删除对应数据点数:", len(df_removed_small_temp_range))
print("最终保留数据点数:", len(df_final))
print("最终保留物质数:", df_final["material_key"].nunique() if len(df_final) > 0 else 0)


# =========================================================
# 9. 物质级别汇总
# =========================================================

def build_material_summary(df_in):
    summary_rows = []

    if len(df_in) == 0:
        return pd.DataFrame()

    for material_key, group in df_in.groupby("material_key", sort=False):
        temps = pd.to_numeric(group[temp_col], errors="coerce").values.astype(float)
        surfaces = pd.to_numeric(group[surface_col], errors="coerce").values.astype(float)

        row = {
            "material_key": material_key,
            "n_points": len(group),
            "T_min": np.nanmin(temps),
            "T_max": np.nanmax(temps),
            "T_range": np.nanmax(temps) - np.nanmin(temps),
            "SurfaceTension_min_N_m": np.nanmin(surfaces),
            "SurfaceTension_max_N_m": np.nanmax(surfaces),
            "SurfaceTension_range_N_m": np.nanmax(surfaces) - np.nanmin(surfaces),
        }

        if pressure_col in group.columns:
            ps = pd.to_numeric(group[pressure_col], errors="coerce").values.astype(float)
            row["P_min_kPa"] = np.nanmin(ps) if not np.all(np.isnan(ps)) else np.nan
            row["P_max_kPa"] = np.nanmax(ps) if not np.all(np.isnan(ps)) else np.nan

        for col in [
            "compound_name",
            "cas",
            "formula",
            "inchikey",
            "smiles",
            "phase",
            "property_name",
            "property_unit",
            "method",
            "doi",
            "year",
            "journal",
            "source_file",
            "title",
            "_source_title",
        ]:
            if col in group.columns:
                row[col] = group[col].iloc[0]

        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)

    if len(summary_df) > 0:
        summary_df = summary_df.sort_values(
            ["n_points", "T_range"],
            ascending=[False, False]
        )

    return summary_df


df_material_summary = build_material_summary(df_final)


# =========================================================
# 10. 数据点不足物质统计
# =========================================================

too_few_summary_rows = []

if len(df_removed_too_few_points) > 0:
    for material_key, group in df_removed_too_few_points.groupby("material_key", sort=False):
        temps = pd.to_numeric(group[temp_col], errors="coerce").values.astype(float)
        surfaces = pd.to_numeric(group[surface_col], errors="coerce").values.astype(float)

        row = {
            "material_key": material_key,
            "n_points_after_duplicate_temperature_processing": len(group),
            "remove_reason": f"points_less_than_{min_points_per_material}_after_duplicate_temperature_processing",
            "T_min": np.nanmin(temps) if not np.all(np.isnan(temps)) else np.nan,
            "T_max": np.nanmax(temps) if not np.all(np.isnan(temps)) else np.nan,
            "T_range": (
                np.nanmax(temps) - np.nanmin(temps)
                if not np.all(np.isnan(temps))
                else np.nan
            ),
            "SurfaceTension_min_N_m": (
                np.nanmin(surfaces)
                if not np.all(np.isnan(surfaces))
                else np.nan
            ),
            "SurfaceTension_max_N_m": (
                np.nanmax(surfaces)
                if not np.all(np.isnan(surfaces))
                else np.nan
            ),
        }

        if pressure_col in group.columns:
            ps = pd.to_numeric(group[pressure_col], errors="coerce").values.astype(float)
            row["P_min_kPa"] = np.nanmin(ps) if not np.all(np.isnan(ps)) else np.nan
            row["P_max_kPa"] = np.nanmax(ps) if not np.all(np.isnan(ps)) else np.nan

        for col in [
            "compound_name",
            "cas",
            "formula",
            "inchikey",
            "smiles",
            "phase",
            "property_name",
            "property_unit",
            "method",
            "doi",
            "year",
            "journal",
            "source_file",
            "title",
            "_source_title",
        ]:
            if col in group.columns:
                row[col] = group[col].iloc[0]

        too_few_summary_rows.append(row)

too_few_summary = pd.DataFrame(too_few_summary_rows)


# =========================================================
# 11. 最终重复温度检查
# =========================================================

if len(df_final) > 0:
    final_duplicate_check = df_final[
        df_final.duplicated(subset=["material_key", "_T_round"], keep=False)
    ].copy()
else:
    final_duplicate_check = pd.DataFrame()

print("\n========== 最终重复温度检查 ==========")
print("最终表中 material_key + T_round 重复行数:", len(final_duplicate_check))
print(
    "最终表中存在重复温度的物质数:",
    final_duplicate_check["material_key"].nunique() if len(final_duplicate_check) > 0 else 0
)


# =========================================================
# 12. 删除临时列
# =========================================================

for temp_internal_col in ["_original_order", "_T_round"]:
    for table in [
        df_final,
        df_removed_duplicate_materials,
        df_duplicate_temperature_all_rows,
        df_aggregated_duplicate_source_rows,
        df_removed_too_few_points,
        df_removed_small_temp_range,
        final_duplicate_check,
        df_removed_by_source,
    ]:
        if temp_internal_col in table.columns:
            table.drop(columns=[temp_internal_col], inplace=True)


# =========================================================
# 13. 保存结果
# =========================================================

with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_final.to_excel(writer, sheet_name="Surface_Liquid_Final", index=False)
    df_material_summary.to_excel(writer, sheet_name="Material_Summary", index=False)

    # 新增来源筛选诊断表
    df_source_summary.to_excel(
        writer,
        sheet_name="Source_Title_Summary",
        index=False
    )

    df_removed_by_source.to_excel(
        writer,
        sheet_name="Removed_Source_Title_Rows",
        index=False
    )

    df_removed_duplicate_materials.to_excel(
        writer,
        sheet_name="Removed_DupTemp_Materials",
        index=False
    )

    df_duplicate_temperature_all_rows.to_excel(
        writer,
        sheet_name="DupTemp_Related_Rows",
        index=False
    )

    duplicate_summary.to_excel(
        writer,
        sheet_name="DupTemp_Summary",
        index=False
    )

    df_aggregated_duplicate_source_rows.to_excel(
        writer,
        sheet_name="Aggregated_DupTemp_Rows",
        index=False
    )

    less_than_sheet_rows = f"Removed_LessThan{min_points_per_material}_Rows"
    less_than_sheet_mat = f"Removed_LessThan{min_points_per_material}_Materials"

    less_than_sheet_rows = less_than_sheet_rows[:31]
    less_than_sheet_mat = less_than_sheet_mat[:31]

    df_removed_too_few_points.to_excel(
        writer,
        sheet_name=less_than_sheet_rows,
        index=False
    )

    too_few_summary.to_excel(
        writer,
        sheet_name=less_than_sheet_mat,
        index=False
    )

    df_removed_small_temp_range.to_excel(
        writer,
        sheet_name="Removed_TRange_Rows",
        index=False
    )

    df_removed_small_temp_range_summary.to_excel(
        writer,
        sheet_name="Removed_TRange_Materials",
        index=False
    )

    final_duplicate_check.to_excel(
        writer,
        sheet_name="Final_DupTemp_Check",
        index=False
    )

    run_info = pd.DataFrame([
        {"item": "input_file", "value": str(input_file)},
        {"item": "input_sheet", "value": str(input_sheet_used)},
        {"item": "output_file", "value": str(output_file)},

        {"item": "temperature_col", "value": temp_col},
        {"item": "surface_tension_col", "value": surface_col},
        {"item": "source_col", "value": source_col},
        {"item": "max_titles_per_material", "value": max_titles_per_material},
        {"item": "use_source_file_when_title_missing", "value": use_source_file_when_title_missing},

        {"item": "temp_round_decimals", "value": temp_round_decimals},
        {"item": "min_points_per_material_after_dup_temp_rule", "value": min_points_per_material},
        {"item": "min_temp_range_K_strictly_greater_than", "value": min_temp_range},
        {"item": "remove_non_positive_surface_tension", "value": remove_non_positive_surface_tension},

        {"item": "source_filter_rule", "value": "keep_top_1_title_by_n_rows_for_each_material_key"},
        {"item": "rows_before_source_title_filter", "value": len(df_before_source_filter)},
        {"item": "materials_before_source_title_filter", "value": df_before_source_filter["material_key"].nunique()},
        {"item": "rows_after_source_title_filter", "value": len(df_after_source_filter)},
        {"item": "materials_after_source_title_filter", "value": df_after_source_filter["material_key"].nunique()},
        {"item": "removed_source_title_rows", "value": len(df_removed_by_source)},

        {"item": "duplicate_temperature_rule", "value": "aggregate_small_difference_duplicates_remove_conflict_temperature_points_only"},
        {"item": "duplicate_relative_tolerance", "value": duplicate_relative_tolerance},
        {"item": "duplicate_absolute_tolerance_N_m", "value": duplicate_absolute_tolerance_N_m},
        {"item": "duplicate_aggregate_method", "value": duplicate_aggregate_method},

        {"item": "rows_after_basic_numeric_and_source_filter", "value": len(df)},
        {"item": "materials_after_basic_numeric_and_source_filter", "value": df["material_key"].nunique()},

        {"item": "duplicate_temperature_related_rows", "value": len(df_duplicate_temperature_all_rows)},
        {"item": "duplicate_temperature_affected_materials", "value": len(polluted_material_keys)},
        {"item": "aggregated_duplicate_temperature_source_rows", "value": len(df_aggregated_duplicate_source_rows)},
        {"item": "removed_conflict_duplicate_temperature_rows", "value": len(df_removed_duplicate_materials)},

        {"item": "rows_after_duplicate_temperature_processing", "value": len(df_after_dup_temp_rule)},
        {
            "item": "materials_after_duplicate_temperature_processing",
            "value": df_after_dup_temp_rule["material_key"].nunique() if len(df_after_dup_temp_rule) > 0 else 0,
        },

        {"item": f"removed_less_than_{min_points_per_material}_rows", "value": len(df_removed_too_few_points)},
        {"item": f"removed_less_than_{min_points_per_material}_materials", "value": len(too_few_material_keys)},

        {"item": "removed_small_temp_range_rows", "value": len(df_removed_small_temp_range)},
        {"item": "removed_small_temp_range_materials", "value": len(small_temp_range_keys)},

        {"item": "final_rows", "value": len(df_final)},
        {"item": "final_materials", "value": df_final["material_key"].nunique() if len(df_final) > 0 else 0},

        {"item": "final_duplicate_temperature_rows", "value": len(final_duplicate_check)},
        {
            "item": "final_duplicate_temperature_materials",
            "value": final_duplicate_check["material_key"].nunique() if len(final_duplicate_check) > 0 else 0,
        },
    ])

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


# =========================================================
# 14. 控制台输出最终结果
# =========================================================

print("\n保存完成:", output_file)
print("最终主表 sheet 名: Surface_Liquid_Final")

print("\n========== 最终结果 ==========")
print("最终数据点数:", len(df_final))
print("最终物质数:", df_final["material_key"].nunique() if len(df_final) > 0 else 0)

print("\n========== 来源筛选统计 ==========")
print("来源筛选前数据点数:", len(df_before_source_filter))
print("来源筛选后数据点数:", len(df_after_source_filter))
print("来源筛选删除数据点数:", len(df_removed_by_source))
print("每个物质最多保留 title 数:", max_titles_per_material)

print("\n========== 删除统计 ==========")
print("基础数值过滤 + 来源筛选后数据点数:", len(df))
print("基础数值过滤 + 来源筛选后物质数:", df["material_key"].nunique())
print("存在重复温度点的物质数:", len(polluted_material_keys))
print("重复温度相关原始行数:", len(df_duplicate_temperature_all_rows))
print("聚合重复温度源行数:", len(df_aggregated_duplicate_source_rows))
print("删除冲突重复温度行数:", len(df_removed_duplicate_materials))
print(f"删除点数 < {min_points_per_material} 的物质数:", len(too_few_material_keys))
print("删除温度区间不足的物质数:", len(small_temp_range_keys))
print(f"当前温度区间阈值: T_range > {min_temp_range:g} K")

if len(df_final) > 0:
    print("\n温度范围：")
    print("T_min:", df_final[temp_col].min())
    print("T_max:", df_final[temp_col].max())

    print("\nSurface tension 范围，单位 N/m：")
    print("SurfaceTension_min:", df_final[surface_col].min())
    print("SurfaceTension_max:", df_final[surface_col].max())

    print("\n最终重复温度检查：")
    print("重复行数:", len(final_duplicate_check))
    print(
        "重复物质数:",
        final_duplicate_check["material_key"].nunique() if len(final_duplicate_check) > 0 else 0
    )

    print("\n数据点数最多的前 30 个物质：")
    show_cols = [
        "material_key",
        "compound_name",
        "formula",
        "cas",
        "inchikey",
        "n_points",
        "T_min",
        "T_max",
        "T_range",
        "SurfaceTension_min_N_m",
        "SurfaceTension_max_N_m",
        "title",
    ]
    show_cols = [c for c in show_cols if c in df_material_summary.columns]

    print(df_material_summary[show_cols].head(30).to_string(index=False))