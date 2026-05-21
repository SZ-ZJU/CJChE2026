import pandas as pd
import numpy as np
from pathlib import Path


# =========================================================
# 1. 输入输出文件
# =========================================================
# 优先使用已经按相态分好的文件
input_file = Path("thermoml_density_mass_by_phase.xlsx")
input_sheet = "Liquid"

output_file = Path("thermoml_Density_Liquid_around_100kPa.xlsx")


# =========================================================
# 2. 基本设置
# =========================================================
temp_col = "T_K"
pressure_col = "P_kPa"

# 密度列
density_col = "Density_g_per_cm3"

# 允许的常压附近压力点
pressure_targets = [100.0, 101.0, 101.325]

# 压力容差，单位 kPa
# 例如 tolerance = 1.0，则 99~102.325 附近基本都会被保留
pressure_tolerance = 1.0

# 是否删除压力缺失的数据
drop_missing_pressure = True

# 是否删除温度缺失的数据
drop_missing_temperature = True

# 是否删除密度缺失的数据
drop_missing_density = True


# =========================================================
# 3. 读取 Liquid sheet
# =========================================================
df = pd.read_excel(input_file, sheet_name=input_sheet)

print("Liquid 原始数据点数:", len(df))
print("原始列名:")
print(list(df.columns))


# =========================================================
# 4. 检查必要列
# =========================================================
if temp_col not in df.columns:
    raise ValueError(f"没有找到温度列: {temp_col}")

if pressure_col not in df.columns:
    raise ValueError(f"没有找到压力列: {pressure_col}")

if density_col not in df.columns:
    if "Density_kg_per_m3" in df.columns:
        df[density_col] = pd.to_numeric(df["Density_kg_per_m3"], errors="coerce") / 1000.0
        print(f"没有找到 {density_col}，已由 Density_kg_per_m3 / 1000 生成。")
    else:
        raise ValueError(f"没有找到密度列: {density_col}")


# =========================================================
# 5. 转成数值
# =========================================================
df[temp_col] = pd.to_numeric(df[temp_col], errors="coerce")
df[pressure_col] = pd.to_numeric(df[pressure_col], errors="coerce")
df[density_col] = pd.to_numeric(df[density_col], errors="coerce")

print("\n温度缺失行数:", df[temp_col].isna().sum())
print("压力缺失行数:", df[pressure_col].isna().sum())
print("密度缺失行数:", df[density_col].isna().sum())


# =========================================================
# 6. 基础缺失值过滤
# =========================================================
mask = pd.Series(True, index=df.index)

if drop_missing_temperature:
    mask &= df[temp_col].notna()

if drop_missing_pressure:
    mask &= df[pressure_col].notna()

if drop_missing_density:
    mask &= df[density_col].notna()

df_basic = df.loc[mask].copy()

print("\n基础缺失值过滤后数据点数:", len(df_basic))


# =========================================================
# 7. 只保留常压附近数据
# =========================================================
pressure_values = df_basic[pressure_col].values.astype(float)

pressure_keep_mask = np.zeros(len(df_basic), dtype=bool)

for p0 in pressure_targets:
    pressure_keep_mask |= np.abs(pressure_values - p0) <= pressure_tolerance

df_filtered = df_basic.loc[pressure_keep_mask].copy()

# 记录匹配到哪个目标压力
def nearest_pressure_target(p):
    diffs = [abs(p - p0) for p0 in pressure_targets]
    idx = int(np.argmin(diffs))
    return pressure_targets[idx], diffs[idx]

nearest_targets = []
nearest_diffs = []

for p in df_filtered[pressure_col].values:
    target, diff = nearest_pressure_target(p)
    nearest_targets.append(target)
    nearest_diffs.append(diff)

df_filtered["matched_pressure_target_kPa"] = nearest_targets
df_filtered["pressure_diff_from_target_kPa"] = nearest_diffs


print("\n========== 常压筛选结果 ==========")
print("常压附近数据点数:", len(df_filtered))
print("删除数据点数:", len(df) - len(df_filtered))

print("\n保留压力统计:")
print(df_filtered[pressure_col].describe())

print("\n匹配目标压力统计:")
print(df_filtered["matched_pressure_target_kPa"].value_counts().sort_index())


# =========================================================
# 8. 自动生成 material_key，便于后续按物质筛选
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
    for col in ["inchikey", "cas", "compound_name", "formula"]:
        if col in row.index and is_valid_value(row[col]):
            return f"{col}:{str(row[col]).strip()}"
    return "unknown_material"


df_filtered["material_key"] = df_filtered.apply(build_material_key, axis=1)


# =========================================================
# 9. 物质级别统计
# =========================================================
summary_rows = []

for material_key, group in df_filtered.groupby("material_key", sort=False):
    temps = pd.to_numeric(group[temp_col], errors="coerce").values.astype(float)
    dens = pd.to_numeric(group[density_col], errors="coerce").values.astype(float)
    ps = pd.to_numeric(group[pressure_col], errors="coerce").values.astype(float)

    row = {
        "material_key": material_key,
        "n_points": len(group),
        "T_min": np.nanmin(temps),
        "T_max": np.nanmax(temps),
        "T_range": np.nanmax(temps) - np.nanmin(temps),
        "P_min_kPa": np.nanmin(ps),
        "P_max_kPa": np.nanmax(ps),
        "density_min_g_per_cm3": np.nanmin(dens),
        "density_max_g_per_cm3": np.nanmax(dens),
    }

    for col in ["compound_name", "cas", "formula", "inchikey", "smiles"]:
        if col in group.columns:
            row[col] = group[col].iloc[0]

    summary_rows.append(row)

df_material_summary = pd.DataFrame(summary_rows)

print("\n常压液相物质数:", df_filtered["material_key"].nunique())

if len(df_material_summary) > 0:
    print("\n每个物质温度点数统计:")
    print(df_material_summary["n_points"].describe())


# =========================================================
# 10. 保存结果
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_filtered.to_excel(writer, sheet_name="Liquid_around_100kPa", index=False)
    df_material_summary.to_excel(writer, sheet_name="Material_Summary", index=False)

    run_info = pd.DataFrame([
        {"item": "input_file", "value": str(input_file)},
        {"item": "input_sheet", "value": input_sheet},
        {"item": "output_file", "value": str(output_file)},
        {"item": "temperature_col", "value": temp_col},
        {"item": "pressure_col", "value": pressure_col},
        {"item": "density_col", "value": density_col},
        {"item": "pressure_targets_kPa", "value": str(pressure_targets)},
        {"item": "pressure_tolerance_kPa", "value": pressure_tolerance},
        {"item": "original_rows", "value": len(df)},
        {"item": "filtered_rows", "value": len(df_filtered)},
        {"item": "filtered_materials", "value": df_filtered["material_key"].nunique()},
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

print("\n保存完成:", output_file)