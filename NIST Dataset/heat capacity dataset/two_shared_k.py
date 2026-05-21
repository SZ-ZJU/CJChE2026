import pandas as pd
import numpy as np
from pathlib import Path
from scipy.interpolate import CubicSpline


# =========================================================
# 1. 输入输出文件
# =========================================================
dataset_file = Path("Cp_dataset_with_PubChem_Tb_Tc.xlsx")
k_result_file = Path("best_two_k_for_boiling_temperature_scaling.xlsx")

output_file = Path("Cp_dataset_selected_by_two_k_with_interpolation.xlsx")


# =========================================================
# 2. 原始数据 sheet 名
# =========================================================
sheet1_name = "Sheet1_with_boiling"      # 每个物质 8 行
sheet2_name = "Sheet2_with_boiling"      # 每个物质 1 行
groups_sheet = "groups_with_boiling"     # 每个物质 1 行

n_points_per_material = 8

temp_col = "T_K"
target_col = "property_value"
boiling_col = "boiling_T_K"


# =========================================================
# 3. 读取原始数据
# =========================================================
df_sheet1 = pd.read_excel(dataset_file, sheet_name=sheet1_name)
df_sheet2 = pd.read_excel(dataset_file, sheet_name=sheet2_name)
df_groups = pd.read_excel(dataset_file, sheet_name=groups_sheet)

print("原始 Sheet1 行数:", len(df_sheet1))
print("原始 Sheet2 物质数:", len(df_sheet2))
print("原始 groups 物质数:", len(df_groups))


# =========================================================
# 4. 检查原始数据一致性
# =========================================================
if temp_col not in df_sheet1.columns:
    raise ValueError(f"{sheet1_name} 中没有找到温度列: {temp_col}")

if target_col not in df_sheet1.columns:
    raise ValueError(f"{sheet1_name} 中没有找到目标列: {target_col}")

if boiling_col not in df_sheet2.columns:
    raise ValueError(f"{sheet2_name} 中没有找到沸点列: {boiling_col}")

if len(df_sheet1) % n_points_per_material != 0:
    raise ValueError(
        f"{sheet1_name} 行数 {len(df_sheet1)} 不能被 {n_points_per_material} 整除。"
    )

n_materials_sheet1 = len(df_sheet1) // n_points_per_material

if n_materials_sheet1 != len(df_sheet2):
    raise ValueError(
        f"Sheet1 物质数 {n_materials_sheet1} 与 Sheet2 物质数 {len(df_sheet2)} 不一致。"
    )

if len(df_sheet2) != len(df_groups):
    raise ValueError(
        f"Sheet2 物质数 {len(df_sheet2)} 与 groups 物质数 {len(df_groups)} 不一致。"
    )


# =========================================================
# 5. 读取 k 筛选结果
# =========================================================
df_selected_info = pd.read_excel(k_result_file, sheet_name="Covered_By_Both_k")

if "material_index" not in df_selected_info.columns:
    raise ValueError("Covered_By_Both_k 中没有 material_index 列。")

selected_material_indices = (
    df_selected_info["material_index"]
    .dropna()
    .astype(int)
    .drop_duplicates()
    .sort_values()
    .tolist()
)

print("\n筛选出的物质数:", len(selected_material_indices))

if len(selected_material_indices) == 0:
    raise ValueError("没有筛选出任何物质。")

max_idx = max(selected_material_indices)
if max_idx >= len(df_sheet2):
    raise ValueError(
        f"筛选结果中的 material_index 最大为 {max_idx}，"
        f"但原始 Sheet2 只有 {len(df_sheet2)} 个物质。"
    )


# =========================================================
# 6. 从 k 结果 Summary 中读取 best_k1 / best_k2
# =========================================================
def get_summary_value(df_summary, item_name):
    if "item" not in df_summary.columns or "value" not in df_summary.columns:
        return None

    sub = df_summary[df_summary["item"].astype(str) == item_name]

    if len(sub) == 0:
        return None

    return sub["value"].iloc[0]


try:
    df_k_summary = pd.read_excel(k_result_file, sheet_name="Summary")
except Exception:
    df_k_summary = pd.DataFrame()

best_k1 = None
best_k2 = None

if len(df_k_summary) > 0:
    best_k1 = get_summary_value(df_k_summary, "best_k1")
    best_k2 = get_summary_value(df_k_summary, "best_k2")

# 如果 Summary 没有 best_k1 / best_k2，则从 Covered_By_Both_k 中反推
if best_k1 is None or pd.isna(best_k1):
    if "ref_T1_K" in df_selected_info.columns and boiling_col in df_selected_info.columns:
        ratio = pd.to_numeric(df_selected_info["ref_T1_K"], errors="coerce") / pd.to_numeric(
            df_selected_info[boiling_col], errors="coerce"
        )
        best_k1 = float(ratio.dropna().median())
    else:
        raise ValueError("无法从 Summary 或 Covered_By_Both_k 中获得 best_k1。")

if best_k2 is None or pd.isna(best_k2):
    if "ref_T2_K" in df_selected_info.columns and boiling_col in df_selected_info.columns:
        ratio = pd.to_numeric(df_selected_info["ref_T2_K"], errors="coerce") / pd.to_numeric(
            df_selected_info[boiling_col], errors="coerce"
        )
        best_k2 = float(ratio.dropna().median())
    else:
        raise ValueError("无法从 Summary 或 Covered_By_Both_k 中获得 best_k2。")

best_k1 = float(best_k1)
best_k2 = float(best_k2)

print("\n使用的 k1:", f"{best_k1:.10f}")
print("使用的 k2:", f"{best_k2:.10f}")


# =========================================================
# 7. 筛选 Sheet2 和 groups
# =========================================================
df_sheet2_selected = df_sheet2.iloc[selected_material_indices].copy()
df_groups_selected = df_groups.iloc[selected_material_indices].copy()

df_sheet2_selected.insert(0, "original_material_index", selected_material_indices)
df_groups_selected.insert(0, "original_material_index", selected_material_indices)


# =========================================================
# 8. 筛选 Sheet1：每个物质 8 行
# =========================================================
selected_sheet1_indices = []

for material_idx in selected_material_indices:
    start = material_idx * n_points_per_material
    end = start + n_points_per_material
    selected_sheet1_indices.extend(range(start, end))

df_sheet1_selected = df_sheet1.iloc[selected_sheet1_indices].copy()

original_material_index_col = []

for material_idx in selected_material_indices:
    original_material_index_col.extend([material_idx] * n_points_per_material)

df_sheet1_selected.insert(0, "original_material_index", original_material_index_col)


# =========================================================
# 9. 把 k1/k2 覆盖信息合并到 Sheet2
# =========================================================
merge_cols = [
    "material_index",
    "T_min",
    "T_max",
    "T_range",
    "boiling_T_K",
    "k_low",
    "k_high",
    "ref_T1_K",
    "ref_T2_K",
    "ref_T_gap_K",
    "covered_by_best_k1",
    "covered_by_best_k2",
    "covered_by_both_best_k",
    "allowed_k_width",
    "allowed_ref_T_width_at_Tb",
]

merge_cols = [c for c in merge_cols if c in df_selected_info.columns]

df_selected_info_merge = df_selected_info[merge_cols].copy()
df_selected_info_merge = df_selected_info_merge.rename(
    columns={"material_index": "original_material_index"}
)

df_sheet2_selected = df_sheet2_selected.merge(
    df_selected_info_merge,
    on="original_material_index",
    how="left",
    suffixes=("", "_from_k_result")
)


# =========================================================
# 10. 样条插值：计算 k1*Tb 和 k2*Tb 下的 property_value
# =========================================================
def spline_interpolate_one_material(T_values, y_values, target_T):
    """
    对单个物质的 T-y 数据进行 CubicSpline 插值。
    要求 target_T 在温度范围内。
    如果温度重复，则先对相同温度的 y 取平均。
    """
    T_values = np.asarray(T_values, dtype=float)
    y_values = np.asarray(y_values, dtype=float)

    mask = np.isfinite(T_values) & np.isfinite(y_values)

    T_values = T_values[mask]
    y_values = y_values[mask]

    if len(T_values) < 2:
        return np.nan, "failed_less_than_2_points"

    df_tmp = pd.DataFrame({
        "T": T_values,
        "y": y_values
    })

    # 去重：同一个温度出现多次时，对 property_value 求均值
    df_tmp = df_tmp.groupby("T", as_index=False)["y"].mean()
    df_tmp = df_tmp.sort_values("T")

    T_unique = df_tmp["T"].values.astype(float)
    y_unique = df_tmp["y"].values.astype(float)

    if len(T_unique) < 2:
        return np.nan, "failed_less_than_2_unique_T"

    T_min = float(np.min(T_unique))
    T_max = float(np.max(T_unique))

    if not (T_min <= target_T <= T_max):
        return np.nan, "failed_target_out_of_range"

    try:
        cs = CubicSpline(T_unique, y_unique, bc_type="not-a-knot", extrapolate=False)
        y_interp = float(cs(target_T))

        if not np.isfinite(y_interp):
            return np.nan, "failed_nonfinite_result"

        return y_interp, "ok_cubic_spline"

    except Exception as e:
        return np.nan, f"failed_spline_error: {e}"


interp_rows = []

for material_idx in selected_material_indices:
    start = material_idx * n_points_per_material
    end = start + n_points_per_material

    sub = df_sheet1.iloc[start:end].copy()

    T_values = pd.to_numeric(sub[temp_col], errors="coerce").values
    y_values = pd.to_numeric(sub[target_col], errors="coerce").values

    Tb = pd.to_numeric(
        pd.Series([df_sheet2.iloc[material_idx][boiling_col]]),
        errors="coerce"
    ).iloc[0]

    T_min = np.nan
    T_max = np.nan

    finite_T = pd.to_numeric(sub[temp_col], errors="coerce").dropna().values

    if len(finite_T) > 0:
        T_min = float(np.min(finite_T))
        T_max = float(np.max(finite_T))

    if pd.isna(Tb) or not np.isfinite(Tb) or Tb <= 0:
        T_k1Tb = np.nan
        T_k2Tb = np.nan
        y_k1 = np.nan
        y_k2 = np.nan
        status_k1 = "failed_invalid_boiling_T"
        status_k2 = "failed_invalid_boiling_T"
    else:
        T_k1Tb = best_k1 * float(Tb)
        T_k2Tb = best_k2 * float(Tb)

        y_k1, status_k1 = spline_interpolate_one_material(T_values, y_values, T_k1Tb)
        y_k2, status_k2 = spline_interpolate_one_material(T_values, y_values, T_k2Tb)

    row = {
        # 按你要求，把这 6 列放在最前面
        "k1": best_k1,
        "k1_times_boiling_T_K": T_k1Tb,
        "property_interp_at_k1Tb": y_k1,
        "k2": best_k2,
        "k2_times_boiling_T_K": T_k2Tb,
        "property_interp_at_k2Tb": y_k2,

        # 后面是辅助信息，便于检查
        "original_material_index": material_idx,
        "boiling_T_K": Tb,
        "T_min": T_min,
        "T_max": T_max,
        "status_k1": status_k1,
        "status_k2": status_k2,
    }

    for col in [
        "compound_name",
        "cas",
        "formula",
        "SMILES",
        "smiles",
        "pubchem_cid",
        "material_key",
        "phase",
    ]:
        if col in df_sheet2.columns:
            row[col] = df_sheet2.iloc[material_idx][col]

    interp_rows.append(row)

df_interpolated = pd.DataFrame(interp_rows)

print("\n插值结果统计：")
print("k1 插值成功物质数:", (df_interpolated["status_k1"] == "ok_cubic_spline").sum())
print("k2 插值成功物质数:", (df_interpolated["status_k2"] == "ok_cubic_spline").sum())


# =========================================================
# 11. Summary
# =========================================================
summary = pd.DataFrame([
    {"item": "original_material_count", "value": len(df_sheet2)},
    {"item": "selected_material_count", "value": len(df_sheet2_selected)},
    {"item": "selected_sheet1_row_count", "value": len(df_sheet1_selected)},
    {"item": "n_points_per_material", "value": n_points_per_material},
    {"item": "best_k1", "value": best_k1},
    {"item": "best_k2", "value": best_k2},
    {"item": "k1_interpolation_success_count", "value": int((df_interpolated["status_k1"] == "ok_cubic_spline").sum())},
    {"item": "k2_interpolation_success_count", "value": int((df_interpolated["status_k2"] == "ok_cubic_spline").sum())},
])


# =========================================================
# 12. 保存 Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_sheet1_selected.to_excel(writer, sheet_name="Sheet1_selected", index=False)
    df_sheet2_selected.to_excel(writer, sheet_name="Sheet2_selected", index=False)
    df_groups_selected.to_excel(writer, sheet_name="groups_selected", index=False)
    df_selected_info.to_excel(writer, sheet_name="Selected_Info", index=False)

    # 新增：k1/k2 对应参考温度下的样条插值值
    df_interpolated.to_excel(writer, sheet_name="Interpolated_k1_k2", index=False)

    summary.to_excel(writer, sheet_name="Summary", index=False)

    if len(df_k_summary) > 0:
        df_k_summary.to_excel(writer, sheet_name="k_Result_Summary", index=False)

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
print("筛选后 Sheet1 行数:", len(df_sheet1_selected))
print("筛选后 Sheet2 物质数:", len(df_sheet2_selected))
print("筛选后 groups 物质数:", len(df_groups_selected))
print("插值结果 sheet: Interpolated_k1_k2")