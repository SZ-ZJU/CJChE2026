import pandas as pd
import numpy as np
from pathlib import Path


# =========================================================
# 1. 输入输出文件
# =========================================================
input_file = Path("Cp_dataset_selected_by_two_k_with_interpolation.xlsx")
input_sheet = "Interpolated_k1_k2"

output_file = Path("Cp_dataset_reference_slope_from_two_k.xlsx")


# =========================================================
# 2. 必要列名
# =========================================================
k1_col = "k1"
T1_col = "k1_times_boiling_T_K"
y1_col = "property_interp_at_k1Tb"

k2_col = "k2"
T2_col = "k2_times_boiling_T_K"
y2_col = "property_interp_at_k2Tb"

boiling_col = "boiling_T_K"


# =========================================================
# 3. 读取数据
# =========================================================
df = pd.read_excel(input_file, sheet_name=input_sheet)

print("读取行数:", len(df))

required_cols = [
    k1_col,
    T1_col,
    y1_col,
    k2_col,
    T2_col,
    y2_col,
    boiling_col,
]

missing_cols = [c for c in required_cols if c not in df.columns]

if missing_cols:
    raise ValueError(f"缺少必要列: {missing_cols}")


# =========================================================
# 4. 转为数值
# =========================================================
for col in required_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")


# =========================================================
# 5. 计算参考温度差、实验值差、参考斜率
# =========================================================
df["reference_temperature_difference_K"] = df[T2_col] - df[T1_col]

df["reference_property_difference"] = df[y2_col] - df[y1_col]

df["reference_slope"] = np.where(
    np.abs(df["reference_temperature_difference_K"]) > 1e-12,
    df["reference_property_difference"] / df["reference_temperature_difference_K"],
    np.nan
)

df["reference_slope_unit"] = "property_value/K"


# =========================================================
# 6. 检查有效性
# =========================================================
df["slope_valid"] = (
    df[T1_col].notna()
    & df[T2_col].notna()
    & df[y1_col].notna()
    & df[y2_col].notna()
    & np.isfinite(df["reference_slope"])
)

df_valid = df[df["slope_valid"]].copy()
df_invalid = df[~df["slope_valid"]].copy()

print("有效参考斜率物质数:", len(df_valid))
print("无效参考斜率物质数:", len(df_invalid))


# =========================================================
# 7. 整理输出列顺序
# =========================================================
front_cols = [
    "original_material_index" if "original_material_index" in df.columns else None,
    "compound_name" if "compound_name" in df.columns else None,
    "cas" if "cas" in df.columns else None,
    "formula" if "formula" in df.columns else None,
    "SMILES" if "SMILES" in df.columns else None,
    "smiles" if "smiles" in df.columns else None,
    "pubchem_cid" if "pubchem_cid" in df.columns else None,
    "material_key" if "material_key" in df.columns else None,
    boiling_col,
    k1_col,
    T1_col,
    y1_col,
    k2_col,
    T2_col,
    y2_col,
    "reference_temperature_difference_K",
    "reference_property_difference",
    "reference_slope",
    "reference_slope_unit",
    "slope_valid",
]

front_cols = [c for c in front_cols if c is not None and c in df.columns]

other_cols = [c for c in df.columns if c not in front_cols]

df_out = df[front_cols + other_cols].copy()
df_valid_out = df_valid[front_cols + other_cols].copy()
df_invalid_out = df_invalid[front_cols + other_cols].copy()


# =========================================================
# 8. Summary
# =========================================================
summary = pd.DataFrame([
    {"item": "input_file", "value": str(input_file)},
    {"item": "input_sheet", "value": input_sheet},
    {"item": "total_material_count", "value": len(df)},
    {"item": "valid_slope_count", "value": len(df_valid)},
    {"item": "invalid_slope_count", "value": len(df_invalid)},
    {"item": "mean_reference_slope", "value": df_valid["reference_slope"].mean() if len(df_valid) > 0 else np.nan},
    {"item": "std_reference_slope", "value": df_valid["reference_slope"].std() if len(df_valid) > 0 else np.nan},
    {"item": "min_reference_slope", "value": df_valid["reference_slope"].min() if len(df_valid) > 0 else np.nan},
    {"item": "max_reference_slope", "value": df_valid["reference_slope"].max() if len(df_valid) > 0 else np.nan},
])


# =========================================================
# 9. 保存 Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_out.to_excel(writer, sheet_name="Reference_Slope_All", index=False)
    df_valid_out.to_excel(writer, sheet_name="Reference_Slope_Valid", index=False)
    df_invalid_out.to_excel(writer, sheet_name="Reference_Slope_Invalid", index=False)
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

            ws.column_dimensions[col_letter].width = min(max_length + 2, 35)

print("\n保存完成:", output_file)