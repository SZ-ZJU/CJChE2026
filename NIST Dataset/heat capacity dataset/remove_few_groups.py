import pandas as pd
import numpy as np
from pathlib import Path


# =========================================================
# 1. 输入输出设置
# =========================================================
input_file = Path("dataset.xlsx")
output_file = Path("dataset_after_lowfreq_group_filter.xlsx")

sheet1_name = "Sheet1"      # 每个物质 8 行
sheet2_name = "Sheet2"      # 每个物质 1 行
groups_sheet = "groups"    # 每个物质 1 行

n_points_per_material = 8

# groups 中基团列范围
# 如果第3列开始，前220个一阶基团：
group_start_idx = 2          # pandas 从0开始，第3列就是2
group_end_idx = 2 + 220      # 不包含 end，所以这里是222

# 如果你想用第3列到第426列，可以改成：
# group_start_idx = 2
# group_end_idx = 426

# 低频基团筛选阈值
min_occurrence = 2       # 至少出现在多少个物质中
min_total_count = 1     # 所有物质中该基团总出现次数至少为多少

# 删除低频基团后，如果某个物质所有保留基团都为0，是否删除该物质
# 如果你想尽量保留物质，设为 False
# 如果你认为全零物质无法建模，设为 True
delete_all_zero_materials_after_filter = False


# =========================================================
# 2. 读取数据
# =========================================================
df_sheet1 = pd.read_excel(input_file, sheet_name=sheet1_name)
df_sheet2 = pd.read_excel(input_file, sheet_name=sheet2_name)
df_groups_raw = pd.read_excel(input_file, sheet_name=groups_sheet)

print("Sheet1 行数:", len(df_sheet1))
print("Sheet2 物质数:", len(df_sheet2))
print("groups 物质数:", len(df_groups_raw))

if len(df_sheet2) != len(df_groups_raw):
    raise ValueError(
        f"Sheet2 物质数 {len(df_sheet2)} 与 groups 行数 {len(df_groups_raw)} 不一致。"
    )

if len(df_sheet1) != len(df_sheet2) * n_points_per_material:
    raise ValueError(
        f"Sheet1 行数 {len(df_sheet1)} 不等于 Sheet2 物质数 × {n_points_per_material}。"
    )


# =========================================================
# 3. 拆分 groups 表：前置信息列 + 基团列 + 后续列
# =========================================================
prefix_cols = df_groups_raw.columns[:group_start_idx]
group_cols_raw = df_groups_raw.columns[group_start_idx:group_end_idx]
suffix_cols = df_groups_raw.columns[group_end_idx:]

df_group_info_prefix = df_groups_raw[prefix_cols].copy()
df_group_info_suffix = df_groups_raw[suffix_cols].copy()

df_groups = df_groups_raw[group_cols_raw].copy()
df_groups = df_groups.apply(pd.to_numeric, errors="coerce").fillna(0.0)

print("\n原始基团列数量:", df_groups.shape[1])


# =========================================================
# 4. 计算低频基团
# =========================================================
occurrence = (df_groups != 0).sum(axis=0)     # 出现在多少个物质中
total_count = df_groups.sum(axis=0)           # 总出现次数

keep_group_mask = (occurrence >= min_occurrence) & (total_count >= min_total_count)

keep_group_cols = df_groups.columns[keep_group_mask].tolist()
removed_group_cols = df_groups.columns[~keep_group_mask].tolist()

df_groups_filtered_core = df_groups[keep_group_cols].copy()

print("保留基团数量:", len(keep_group_cols))
print("删除低频基团数量:", len(removed_group_cols))


# =========================================================
# 5. 物质层面的低频基团影响报告
# =========================================================
df_removed_part = df_groups[removed_group_cols].copy()

lowfreq_group_count_per_material = (df_removed_part != 0).sum(axis=1)
lowfreq_group_total_per_material = df_removed_part.sum(axis=1)

remaining_group_count_per_material = (df_groups_filtered_core != 0).sum(axis=1)
remaining_group_total_per_material = df_groups_filtered_core.sum(axis=1)

all_zero_after_filter = remaining_group_total_per_material == 0

df_material_report = pd.DataFrame({
    "material_index": np.arange(len(df_groups)),
    "lowfreq_group_type_count": lowfreq_group_count_per_material,
    "lowfreq_group_total_count": lowfreq_group_total_per_material,
    "remaining_group_type_count": remaining_group_count_per_material,
    "remaining_group_total_count": remaining_group_total_per_material,
    "all_zero_after_filter": all_zero_after_filter,
})

for col in ["compound_name", "cas", "formula", "SMILES", "smiles", "material_key"]:
    if col in df_sheet2.columns:
        df_material_report[col] = df_sheet2[col].values

print("\n删除低频基团后，全零物质数:", int(all_zero_after_filter.sum()))


# =========================================================
# 6. 可选：删除全零物质
# =========================================================
if delete_all_zero_materials_after_filter:
    keep_material_mask = ~all_zero_after_filter.to_numpy()
else:
    keep_material_mask = np.ones(len(df_groups), dtype=bool)

df_groups_filtered_core = df_groups_filtered_core.loc[keep_material_mask].copy()
df_sheet2_filtered = df_sheet2.loc[keep_material_mask].copy()
df_group_info_prefix_filtered = df_group_info_prefix.loc[keep_material_mask].copy()
df_group_info_suffix_filtered = df_group_info_suffix.loc[keep_material_mask].copy()

# Sheet1 每个物质 8 行，同步保留
keep_sheet1_indices = []

for material_idx, keep in enumerate(keep_material_mask):
    if keep:
        start = material_idx * n_points_per_material
        end = start + n_points_per_material
        keep_sheet1_indices.extend(range(start, end))

df_sheet1_filtered = df_sheet1.iloc[keep_sheet1_indices].copy()

# 重新拼回 groups 表
df_groups_filtered = pd.concat(
    [
        df_group_info_prefix_filtered.reset_index(drop=True),
        df_groups_filtered_core.reset_index(drop=True),
        df_group_info_suffix_filtered.reset_index(drop=True),
    ],
    axis=1
)


# =========================================================
# 7. 检查删除低频基团后，哪些物质变成相同基团向量
# =========================================================
df_vector_check = df_groups_filtered_core.copy()
df_vector_check["feature_vector_key"] = df_vector_check.apply(
    lambda row: tuple(row.astype(float).values.tolist()),
    axis=1
)

vector_counts = df_vector_check["feature_vector_key"].value_counts()

duplicate_vector_keys = vector_counts[vector_counts > 1].index

duplicate_rows = []

for dup_id, key in enumerate(duplicate_vector_keys, start=1):
    indices = df_vector_check.index[df_vector_check["feature_vector_key"] == key].tolist()

    for idx in indices:
        row = {
            "duplicate_group_id": dup_id,
            "material_filtered_index": idx,
            "same_vector_material_count": len(indices),
        }

        for col in ["compound_name", "cas", "formula", "SMILES", "smiles", "material_key"]:
            if col in df_sheet2_filtered.columns:
                row[col] = df_sheet2_filtered.iloc[idx][col]

        duplicate_rows.append(row)

df_duplicate_report = pd.DataFrame(duplicate_rows)

print("\n删除低频基团后，基团向量重复的物质组数:", len(duplicate_vector_keys))
print("涉及重复向量的物质数:", len(df_duplicate_report))


# =========================================================
# 8. 删除基团报告
# =========================================================
df_removed_groups = pd.DataFrame({
    "removed_group": removed_group_cols,
    "occurrence_material_count": occurrence[removed_group_cols].values,
    "total_count": total_count[removed_group_cols].values,
})

df_kept_groups = pd.DataFrame({
    "kept_group": keep_group_cols,
    "occurrence_material_count": occurrence[keep_group_cols].values,
    "total_count": total_count[keep_group_cols].values,
})

df_summary = pd.DataFrame([
    {"item": "original_material_count", "value": len(df_groups)},
    {"item": "filtered_material_count", "value": len(df_groups_filtered_core)},
    {"item": "original_group_count", "value": len(group_cols_raw)},
    {"item": "kept_group_count", "value": len(keep_group_cols)},
    {"item": "removed_lowfreq_group_count", "value": len(removed_group_cols)},
    {"item": "min_occurrence", "value": min_occurrence},
    {"item": "min_total_count", "value": min_total_count},
    {"item": "delete_all_zero_materials_after_filter", "value": delete_all_zero_materials_after_filter},
    {"item": "all_zero_material_count_after_filter", "value": int(all_zero_after_filter.sum())},
    {"item": "duplicate_feature_vector_group_count", "value": len(duplicate_vector_keys)},
    {"item": "duplicate_feature_vector_material_count", "value": len(df_duplicate_report)},
])


# =========================================================
# 9. 保存结果
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_sheet1_filtered.to_excel(writer, sheet_name="Sheet1_filtered", index=False)
    df_sheet2_filtered.to_excel(writer, sheet_name="Sheet2_filtered", index=False)
    df_groups_filtered.to_excel(writer, sheet_name="groups_filtered", index=False)

    df_removed_groups.to_excel(writer, sheet_name="Removed_LowFreq_Groups", index=False)
    df_kept_groups.to_excel(writer, sheet_name="Kept_Groups", index=False)
    df_material_report.to_excel(writer, sheet_name="Material_LowFreq_Report", index=False)
    df_duplicate_report.to_excel(writer, sheet_name="Duplicate_Vector_Report", index=False)
    df_summary.to_excel(writer, sheet_name="Summary", index=False)

print("\n保存完成:", output_file)
print("\n后续建模请使用：")
print("Sheet1_filtered")
print("groups_filtered")