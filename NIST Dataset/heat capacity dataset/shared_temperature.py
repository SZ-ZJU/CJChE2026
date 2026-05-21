import pandas as pd
import numpy as np
from pathlib import Path

# =========================
# 1. 输入文件
# =========================
file_path = Path("dataset.xlsx")
sheet_name = "Sheet1"

temp_col = "T_K"
n_points_per_material = 8
target_T = 298.15

# =========================
# 2. 读取数据
# =========================
df = pd.read_excel(file_path, sheet_name=sheet_name)

if temp_col not in df.columns:
    raise ValueError(f"没有找到温度列: {temp_col}")

if len(df) % n_points_per_material != 0:
    raise ValueError(
        f"数据行数 {len(df)} 不能被 {n_points_per_material} 整除，"
        "请检查是否每 8 行一个物质。"
    )

df[temp_col] = pd.to_numeric(df[temp_col], errors="coerce")

n_materials = len(df) // n_points_per_material

summary_rows = []

for i in range(n_materials):
    start = i * n_points_per_material
    end = start + n_points_per_material

    group = df.iloc[start:end].copy()

    temps = group[temp_col].dropna().values

    if len(temps) == 0:
        T_min = np.nan
        T_max = np.nan
        contains_target = False
    else:
        T_min = np.min(temps)
        T_max = np.max(temps)
        contains_target = (T_min <= target_T <= T_max)

    row = {
        "material_index": i,
        "start_row_excel": start + 2,   # Excel 中数据起始行，假设第1行为表头
        "end_row_excel": end + 1,
        "T_min": T_min,
        "T_max": T_max,
        "T_range": T_max - T_min if np.isfinite(T_min) and np.isfinite(T_max) else np.nan,
        "contains_298_15K": contains_target,
    }

    # 如果有这些列，也带出来方便查看
    for col in ["compound_name", "cas", "formula", "SMILES", "material_key"]:
        if col in df.columns:
            row[col] = group.iloc[0][col]

    summary_rows.append(row)

summary = pd.DataFrame(summary_rows)

count_contains = summary["contains_298_15K"].sum()

print("总物质数:", n_materials)
print("298.15 K 在温度范围内的物质数:", count_contains)
print("比例:", f"{count_contains / n_materials * 100:.2f}%")

# 保存结果
output_file = Path("temperature_range_contains_298_15K.xlsx")

with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    summary.to_excel(writer, sheet_name="Summary", index=False)
    summary[summary["contains_298_15K"] == True].to_excel(
        writer, sheet_name="Contains_298_15K", index=False
    )
    summary[summary["contains_298_15K"] == False].to_excel(
        writer, sheet_name="Not_Contains_298_15K", index=False
    )

print("保存完成:", output_file)