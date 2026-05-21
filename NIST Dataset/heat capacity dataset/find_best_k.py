# import pandas as pd
# import numpy as np
# from pathlib import Path
#
#
# # =========================================================
# # 1. 输入输出文件
# # =========================================================
# file_path = Path("Cp_dataset_with_PubChem_Tb_Tc.xlsx")
#
# sheet1_name = "Sheet1_with_boiling"   # 每个物质 8 行
# sheet2_name = "Sheet2_with_boiling"   # 每个物质 1 行
#
# output_file = Path("best_k_for_boiling_temperature_scaling.xlsx")
#
#
# # =========================================================
# # 2. 基本设置
# # =========================================================
# n_points_per_material = 8
#
# temp_col = "T_K"
# boiling_col = "boiling_T_K"
#
# # 如果有多个最优 k，优先选择最接近这个值的 k
# # 通常 k=1 表示直接使用沸点本身
# prefer_k = 1.0
#
#
# # =========================================================
# # 3. 读取数据
# # =========================================================
# df1 = pd.read_excel(file_path, sheet_name=sheet1_name)
# df2 = pd.read_excel(file_path, sheet_name=sheet2_name)
#
# print("Sheet1 行数:", len(df1))
# print("Sheet2 物质数:", len(df2))
#
# if temp_col not in df1.columns:
#     raise ValueError(f"{sheet1_name} 中没有找到温度列: {temp_col}")
#
# if boiling_col not in df2.columns:
#     raise ValueError(f"{sheet2_name} 中没有找到沸点列: {boiling_col}")
#
# if len(df1) % n_points_per_material != 0:
#     raise ValueError(
#         f"{sheet1_name} 行数 {len(df1)} 不能被 {n_points_per_material} 整除。"
#     )
#
# n_materials_from_sheet1 = len(df1) // n_points_per_material
# n_materials_from_sheet2 = len(df2)
#
# if n_materials_from_sheet1 != n_materials_from_sheet2:
#     raise ValueError(
#         f"Sheet1 物质数 {n_materials_from_sheet1} 和 Sheet2 物质数 "
#         f"{n_materials_from_sheet2} 不一致。"
#     )
#
#
# # =========================================================
# # 4. 计算每个物质的温度范围和允许 k 区间
# # =========================================================
# records = []
#
# for material_idx in range(n_materials_from_sheet2):
#     start = material_idx * n_points_per_material
#     end = start + n_points_per_material
#
#     sub = df1.iloc[start:end].copy()
#
#     T_values = pd.to_numeric(sub[temp_col], errors="coerce").dropna().values
#     Tb = pd.to_numeric(pd.Series([df2.iloc[material_idx][boiling_col]]), errors="coerce").iloc[0]
#
#     row = {
#         "material_index": material_idx,
#         "T_min": np.nan,
#         "T_max": np.nan,
#         "T_range": np.nan,
#         "boiling_T_K": Tb,
#         "k_low": np.nan,
#         "k_high": np.nan,
#         "valid_interval": False,
#     }
#
#     # 带出一些物质信息，方便检查
#     for col in ["compound_name", "cas", "formula", "SMILES", "smiles", "material_key"]:
#         if col in df2.columns:
#             row[col] = df2.iloc[material_idx][col]
#
#     if len(T_values) > 0 and pd.notna(Tb) and np.isfinite(Tb) and Tb > 0:
#         T_min = float(np.min(T_values))
#         T_max = float(np.max(T_values))
#
#         k_low = T_min / Tb
#         k_high = T_max / Tb
#
#         if np.isfinite(k_low) and np.isfinite(k_high):
#             row["T_min"] = T_min
#             row["T_max"] = T_max
#             row["T_range"] = T_max - T_min
#             row["k_low"] = min(k_low, k_high)
#             row["k_high"] = max(k_low, k_high)
#             row["valid_interval"] = True
#
#     records.append(row)
#
# df_interval = pd.DataFrame(records)
#
# df_valid = df_interval[df_interval["valid_interval"]].copy()
#
# print("\n有效物质数:", len(df_valid))
# print("无有效沸点或温度范围的物质数:", len(df_interval) - len(df_valid))
#
# if len(df_valid) == 0:
#     raise ValueError("没有任何有效的 k 区间，无法寻找最优 k。")
#
#
# # =========================================================
# # 5. 构造候选 k
# # =========================================================
# # 最大重叠一定出现在：
# # 1. 某个区间端点；
# # 2. 相邻端点之间的任意点。
# # 因此用所有端点和相邻端点中点作为候选值即可。
# # =========================================================
# endpoints = np.unique(
#     np.concatenate([
#         df_valid["k_low"].values,
#         df_valid["k_high"].values,
#     ])
# )
#
# candidate_ks = list(endpoints)
#
# # 相邻端点中点
# if len(endpoints) >= 2:
#     midpoints = (endpoints[:-1] + endpoints[1:]) / 2.0
#     candidate_ks.extend(midpoints.tolist())
#
# # 加入 prefer_k，方便检查 k=1 是否可行
# candidate_ks.append(prefer_k)
#
# candidate_ks = np.array(sorted(set([float(k) for k in candidate_ks if np.isfinite(k)])))
#
#
# # =========================================================
# # 6. 计算每个候选 k 覆盖多少物质
# # =========================================================
# k_results = []
#
# k_low_arr = df_valid["k_low"].values
# k_high_arr = df_valid["k_high"].values
#
# for k in candidate_ks:
#     inside_mask = (k_low_arr <= k) & (k <= k_high_arr)
#     count = int(inside_mask.sum())
#
#     k_results.append({
#         "k": k,
#         "covered_material_count": count,
#         "covered_material_ratio_percent": count / len(df_valid) * 100,
#         "distance_to_prefer_k": abs(k - prefer_k),
#     })
#
# df_k_results = pd.DataFrame(k_results)
# df_k_results = df_k_results.sort_values(
#     ["covered_material_count", "distance_to_prefer_k"],
#     ascending=[False, True]
# ).reset_index(drop=True)
#
# best_count = int(df_k_results.loc[0, "covered_material_count"])
#
# df_best_candidates = df_k_results[
#     df_k_results["covered_material_count"] == best_count
# ].copy()
#
# # 在所有最优候选中，选择最接近 prefer_k 的 k
# best_k = float(df_best_candidates.sort_values("distance_to_prefer_k").iloc[0]["k"])
#
# print("\n========== 最优结果 ==========")
# print("最优 k:", f"{best_k:.10f}")
# print("最大覆盖物质数:", best_count)
# print("有效物质数:", len(df_valid))
# print("覆盖比例:", f"{best_count / len(df_valid) * 100:.2f}%")
#
# # 检查 k=1 的覆盖情况
# inside_k1 = (k_low_arr <= prefer_k) & (prefer_k <= k_high_arr)
# count_k1 = int(inside_k1.sum())
#
# print("\nk = 1.0 时覆盖物质数:", count_k1)
# print("k = 1.0 时覆盖比例:", f"{count_k1 / len(df_valid) * 100:.2f}%")
#
#
# # =========================================================
# # 7. 用最优 k 标记每个物质是否被覆盖
# # =========================================================
# df_interval["scaled_boiling_T_K"] = df_interval["boiling_T_K"] * best_k
#
# df_interval["covered_by_best_k"] = (
#     df_interval["valid_interval"] &
#     (df_interval["T_min"] <= df_interval["scaled_boiling_T_K"]) &
#     (df_interval["scaled_boiling_T_K"] <= df_interval["T_max"])
# )
#
# df_interval["covered_by_k_1"] = (
#     df_interval["valid_interval"] &
#     (df_interval["T_min"] <= df_interval["boiling_T_K"]) &
#     (df_interval["boiling_T_K"] <= df_interval["T_max"])
# )
#
# df_covered = df_interval[df_interval["covered_by_best_k"]].copy()
# df_not_covered = df_interval[
#     df_interval["valid_interval"] & (~df_interval["covered_by_best_k"])
# ].copy()
#
# df_invalid = df_interval[~df_interval["valid_interval"]].copy()
#
#
# # =========================================================
# # 8. 找出最优 k 的连续区间
# # =========================================================
# # 这里额外输出所有能够达到 best_count 的 k 区间。
# # =========================================================
# best_regions = []
#
# # 检查端点和端点之间区间
# sorted_points = np.unique(endpoints)
#
# # 单点端点
# for p in sorted_points:
#     count_p = int(((k_low_arr <= p) & (p <= k_high_arr)).sum())
#     if count_p == best_count:
#         best_regions.append({
#             "region_type": "point",
#             "k_low": p,
#             "k_high": p,
#             "representative_k": p,
#             "covered_material_count": count_p,
#         })
#
# # 开区间中点代表相邻端点之间的覆盖
# for a, b in zip(sorted_points[:-1], sorted_points[1:]):
#     mid = (a + b) / 2.0
#     count_mid = int(((k_low_arr <= mid) & (mid <= k_high_arr)).sum())
#
#     if count_mid == best_count:
#         best_regions.append({
#             "region_type": "interval_between_endpoints",
#             "k_low": a,
#             "k_high": b,
#             "representative_k": mid,
#             "covered_material_count": count_mid,
#         })
#
# df_best_regions = pd.DataFrame(best_regions)
#
#
# # =========================================================
# # 9. 保存结果
# # =========================================================
# with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
#     df_interval.to_excel(writer, sheet_name="Material_k_Intervals", index=False)
#     df_covered.to_excel(writer, sheet_name="Covered_By_Best_k", index=False)
#     df_not_covered.to_excel(writer, sheet_name="Not_Covered_By_Best_k", index=False)
#     df_invalid.to_excel(writer, sheet_name="Invalid_Materials", index=False)
#
#     df_k_results.to_excel(writer, sheet_name="Candidate_k_Results", index=False)
#     df_best_candidates.to_excel(writer, sheet_name="Best_k_Candidates", index=False)
#     df_best_regions.to_excel(writer, sheet_name="Best_k_Regions", index=False)
#
#     pd.DataFrame([
#         {"item": "best_k", "value": best_k},
#         {"item": "best_covered_material_count", "value": best_count},
#         {"item": "valid_material_count", "value": len(df_valid)},
#         {"item": "all_material_count", "value": len(df_interval)},
#         {"item": "best_covered_ratio_percent", "value": best_count / len(df_valid) * 100},
#         {"item": "k_1_covered_material_count", "value": count_k1},
#         {"item": "k_1_covered_ratio_percent", "value": count_k1 / len(df_valid) * 100},
#     ]).to_excel(writer, sheet_name="Summary", index=False)
#
# print("\n保存完成:", output_file)


import pandas as pd
import numpy as np
from pathlib import Path


# =========================================================
# 1. 输入输出文件
# =========================================================
file_path = Path("Cp_dataset_with_PubChem_Tb_Tc.xlsx")

sheet1_name = "Sheet1_with_boiling"   # 每个物质 8 行
sheet2_name = "Sheet2_with_boiling"   # 每个物质 1 行

output_file = Path("best_two_k_for_boiling_temperature_scaling.xlsx")


# =========================================================
# 2. 基本设置
# =========================================================
n_points_per_material = 8

temp_col = "T_K"
boiling_col = "boiling_T_K"

# 两个 k 至少相差多少
# 例如 0.05 表示 k2 - k1 >= 0.05
# 如果你希望两个参考温度更分散，可以改成 0.08 或 0.10
min_k_gap = 0.05

# 如果多个方案覆盖数一样、跨度也一样，优先让中心靠近这个值
prefer_center_k = 1.0


# =========================================================
# 3. 读取数据
# =========================================================
df1 = pd.read_excel(file_path, sheet_name=sheet1_name)
df2 = pd.read_excel(file_path, sheet_name=sheet2_name)

print("Sheet1 行数:", len(df1))
print("Sheet2 物质数:", len(df2))

if temp_col not in df1.columns:
    raise ValueError(f"{sheet1_name} 中没有找到温度列: {temp_col}")

if boiling_col not in df2.columns:
    raise ValueError(f"{sheet2_name} 中没有找到沸点列: {boiling_col}")

if len(df1) % n_points_per_material != 0:
    raise ValueError(
        f"{sheet1_name} 行数 {len(df1)} 不能被 {n_points_per_material} 整除。"
    )

n_materials_from_sheet1 = len(df1) // n_points_per_material
n_materials_from_sheet2 = len(df2)

if n_materials_from_sheet1 != n_materials_from_sheet2:
    raise ValueError(
        f"Sheet1 物质数 {n_materials_from_sheet1} 和 Sheet2 物质数 "
        f"{n_materials_from_sheet2} 不一致。"
    )


# =========================================================
# 4. 计算每个物质的温度范围和允许 k 区间
# =========================================================
records = []

for material_idx in range(n_materials_from_sheet2):
    start = material_idx * n_points_per_material
    end = start + n_points_per_material

    sub = df1.iloc[start:end].copy()

    T_values = pd.to_numeric(sub[temp_col], errors="coerce").dropna().values
    Tb = pd.to_numeric(
        pd.Series([df2.iloc[material_idx][boiling_col]]),
        errors="coerce"
    ).iloc[0]

    row = {
        "material_index": material_idx,
        "T_min": np.nan,
        "T_max": np.nan,
        "T_range": np.nan,
        "boiling_T_K": Tb,
        "k_low": np.nan,
        "k_high": np.nan,
        "valid_interval": False,
    }

    for col in [
        "compound_name",
        "cas",
        "formula",
        "SMILES",
        "smiles",
        "material_key",
        "pubchem_cid",
    ]:
        if col in df2.columns:
            row[col] = df2.iloc[material_idx][col]

    if len(T_values) > 0 and pd.notna(Tb) and np.isfinite(Tb) and Tb > 0:
        T_min = float(np.min(T_values))
        T_max = float(np.max(T_values))

        k_low = T_min / Tb
        k_high = T_max / Tb

        if np.isfinite(k_low) and np.isfinite(k_high):
            row["T_min"] = T_min
            row["T_max"] = T_max
            row["T_range"] = T_max - T_min
            row["k_low"] = min(k_low, k_high)
            row["k_high"] = max(k_low, k_high)
            row["valid_interval"] = True

    records.append(row)

df_interval = pd.DataFrame(records)
df_valid = df_interval[df_interval["valid_interval"]].copy()

print("\n有效物质数:", len(df_valid))
print("无有效沸点或温度范围的物质数:", len(df_interval) - len(df_valid))

if len(df_valid) == 0:
    raise ValueError("没有任何有效的 k 区间，无法寻找最优 k。")


# =========================================================
# 5. 构造候选 k
# =========================================================
# 对区间覆盖问题，最优解通常可以从端点或端点之间的代表点中找到。
# 这里使用：
# 1. 所有 k_low / k_high 端点
# 2. 相邻端点中点
# 3. prefer_center_k
# =========================================================
endpoints = np.unique(
    np.concatenate([
        df_valid["k_low"].values,
        df_valid["k_high"].values,
    ])
)

candidate_ks = list(endpoints)

if len(endpoints) >= 2:
    midpoints = (endpoints[:-1] + endpoints[1:]) / 2.0
    candidate_ks.extend(midpoints.tolist())

candidate_ks.append(prefer_center_k)

candidate_ks = np.array(
    sorted(set([float(k) for k in candidate_ks if np.isfinite(k)]))
)

print("候选 k 数量:", len(candidate_ks))


# =========================================================
# 6. 搜索最优 k1, k2
# =========================================================
k_low_arr = df_valid["k_low"].values
k_high_arr = df_valid["k_high"].values

pair_rows = []

for i, k1 in enumerate(candidate_ks):
    for k2 in candidate_ks[i + 1:]:
        if k2 <= k1:
            continue

        k_gap = k2 - k1

        if k_gap < min_k_gap:
            continue

        inside_mask = (
            (k_low_arr <= k1) &
            (k1 <= k_high_arr) &
            (k_low_arr <= k2) &
            (k2 <= k_high_arr)
        )

        covered_count = int(inside_mask.sum())

        center_k = (k1 + k2) / 2.0

        pair_rows.append({
            "k1": k1,
            "k2": k2,
            "k_gap": k_gap,
            "center_k": center_k,
            "covered_material_count": covered_count,
            "covered_material_ratio_percent": covered_count / len(df_valid) * 100,
            "distance_to_prefer_center_k": abs(center_k - prefer_center_k),
        })

df_pair_results = pd.DataFrame(pair_rows)

if len(df_pair_results) == 0:
    raise ValueError(
        "没有找到满足 min_k_gap 的 k1/k2 组合。"
        "请减小 min_k_gap，例如改成 0.02 或 0.01。"
    )

# 排序原则：
# 1. 覆盖物质数最多
# 2. k_gap 最大
# 3. 中心尽量接近 prefer_center_k
df_pair_results = df_pair_results.sort_values(
    ["covered_material_count", "k_gap", "distance_to_prefer_center_k"],
    ascending=[False, False, True]
).reset_index(drop=True)

best = df_pair_results.iloc[0]

best_k1 = float(best["k1"])
best_k2 = float(best["k2"])
best_count = int(best["covered_material_count"])
best_gap = float(best["k_gap"])

print("\n========== 最优两个 k ==========")
print("best_k1:", f"{best_k1:.10f}")
print("best_k2:", f"{best_k2:.10f}")
print("k2 - k1:", f"{best_gap:.10f}")
print("最大同时覆盖物质数:", best_count)
print("有效物质数:", len(df_valid))
print("覆盖比例:", f"{best_count / len(df_valid) * 100:.2f}%")


# =========================================================
# 7. 检查如果不要求 min_k_gap，理论最大覆盖是多少
# =========================================================
pair_rows_no_gap = []

for i, k1 in enumerate(candidate_ks):
    for k2 in candidate_ks[i + 1:]:
        if k2 <= k1:
            continue

        inside_mask = (
            (k_low_arr <= k1) &
            (k1 <= k_high_arr) &
            (k_low_arr <= k2) &
            (k2 <= k_high_arr)
        )

        covered_count = int(inside_mask.sum())
        k_gap = k2 - k1
        center_k = (k1 + k2) / 2.0

        pair_rows_no_gap.append({
            "k1": k1,
            "k2": k2,
            "k_gap": k_gap,
            "center_k": center_k,
            "covered_material_count": covered_count,
            "covered_material_ratio_percent": covered_count / len(df_valid) * 100,
            "distance_to_prefer_center_k": abs(center_k - prefer_center_k),
        })

df_pair_results_no_gap = pd.DataFrame(pair_rows_no_gap).sort_values(
    ["covered_material_count", "k_gap", "distance_to_prefer_center_k"],
    ascending=[False, False, True]
).reset_index(drop=True)

best_no_gap = df_pair_results_no_gap.iloc[0]

print("\n========== 不限制 k 间隔时的参考结果 ==========")
print("best_k1_no_gap:", f"{float(best_no_gap['k1']):.10f}")
print("best_k2_no_gap:", f"{float(best_no_gap['k2']):.10f}")
print("k_gap_no_gap:", f"{float(best_no_gap['k_gap']):.10f}")
print("covered_count_no_gap:", int(best_no_gap["covered_material_count"]))


# =========================================================
# 8. 用最优 k1/k2 标记每个物质
# =========================================================
df_interval["ref_T1_K"] = df_interval["boiling_T_K"] * best_k1
df_interval["ref_T2_K"] = df_interval["boiling_T_K"] * best_k2
df_interval["ref_T_gap_K"] = df_interval["ref_T2_K"] - df_interval["ref_T1_K"]

df_interval["covered_by_best_k1"] = (
    df_interval["valid_interval"] &
    (df_interval["T_min"] <= df_interval["ref_T1_K"]) &
    (df_interval["ref_T1_K"] <= df_interval["T_max"])
)

df_interval["covered_by_best_k2"] = (
    df_interval["valid_interval"] &
    (df_interval["T_min"] <= df_interval["ref_T2_K"]) &
    (df_interval["ref_T2_K"] <= df_interval["T_max"])
)

df_interval["covered_by_both_best_k"] = (
    df_interval["covered_by_best_k1"] &
    df_interval["covered_by_best_k2"]
)

df_covered_both = df_interval[df_interval["covered_by_both_best_k"]].copy()
df_not_covered_both = df_interval[
    df_interval["valid_interval"] & (~df_interval["covered_by_both_best_k"])
].copy()
df_invalid = df_interval[~df_interval["valid_interval"]].copy()


# =========================================================
# 9. 对每个物质，计算它允许的最大 k 跨度
# =========================================================
df_interval["allowed_k_width"] = df_interval["k_high"] - df_interval["k_low"]
df_interval["allowed_ref_T_width_at_Tb"] = (
    df_interval["allowed_k_width"] * df_interval["boiling_T_K"]
)


# =========================================================
# 10. 保存结果
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    pd.DataFrame([
        {"item": "best_k1", "value": best_k1},
        {"item": "best_k2", "value": best_k2},
        {"item": "k_gap", "value": best_gap},
        {"item": "min_k_gap_required", "value": min_k_gap},
        {"item": "prefer_center_k", "value": prefer_center_k},
        {"item": "covered_material_count", "value": best_count},
        {"item": "valid_material_count", "value": len(df_valid)},
        {"item": "all_material_count", "value": len(df_interval)},
        {"item": "covered_ratio_percent", "value": best_count / len(df_valid) * 100},
        {"item": "best_k1_no_gap", "value": float(best_no_gap["k1"])},
        {"item": "best_k2_no_gap", "value": float(best_no_gap["k2"])},
        {"item": "k_gap_no_gap", "value": float(best_no_gap["k_gap"])},
        {"item": "covered_count_no_gap", "value": int(best_no_gap["covered_material_count"])},
    ]).to_excel(writer, sheet_name="Summary", index=False)

    df_interval.to_excel(writer, sheet_name="Material_k_Intervals", index=False)
    df_covered_both.to_excel(writer, sheet_name="Covered_By_Both_k", index=False)
    df_not_covered_both.to_excel(writer, sheet_name="Not_Covered_By_Both_k", index=False)
    df_invalid.to_excel(writer, sheet_name="Invalid_Materials", index=False)

    df_pair_results.to_excel(writer, sheet_name="Pair_k_Results_With_Gap", index=False)
    df_pair_results_no_gap.to_excel(writer, sheet_name="Pair_k_Results_No_Gap", index=False)

print("\n保存完成:", output_file)