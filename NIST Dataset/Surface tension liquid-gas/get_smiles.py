# -*- coding: utf-8 -*-
"""
Surface tension liquid-gas 线性度结果之后获取 PubChem SMILES 脚本

输入：
    thermoml_surface_tension_liquid_gas_Liquid_remove_dupT_materials_min3_Tgt20_with_RSQ.xlsx
    sheet: Data_With_RSQ

输出：
    thermoml_surface_tension_liquid_gas_Liquid_remove_dupT_materials_min3_Tgt20_RSQ_with_PubChem_SMILES.xlsx

功能：
    1. 读取已经完成线性度分析后的 Surface tension 数据
    2. 可选：只保留 fit_status == ok 的物质
    3. 可选：只保留 RSQ_Surface_vs_T >= 指定阈值的物质
    4. 按 material_key 提取唯一物质
    5. 优先用 inchikey 查询 PubChem
    6. inchikey 查询失败则用 cas
    7. cas 查询失败则用 compound_name
    8. 获取 CanonicalSMILES / IsomericSMILES / ConnectivitySMILES
    9. 生成 final_smiles 和 SMILES 列
    10. 输出有效 SMILES 数据和诊断表
"""

import pandas as pd
import requests
import time
from pathlib import Path
from urllib.parse import quote


# =========================================================
# 1. 输入输出文件
# =========================================================

input_file = Path(
    "thermoml_surface_tension_liquid_gas_Liquid_remove_dupT_materials_min3_Tgt20_with_RSQ.xlsx"
)
input_sheet = "Data_With_RSQ"

output_file = Path(
    "thermoml_surface_tension_liquid_gas_Liquid_remove_dupT_materials_min3_Tgt20_RSQ_with_PubChem_SMILES.xlsx"
)


# =========================================================
# 2. 是否基于线性度筛选“有效物质”
# =========================================================

# 是否只保留线性拟合成功的物质
KEEP_ONLY_FIT_STATUS_OK = True

# 是否只保留 R² 高于阈值的物质
# 如果你想保留所有 fit_status == ok 的物质，就设为 False
KEEP_ONLY_RSQ_ABOVE_THRESHOLD = False

# 主 R² 列
RSQ_COL = "RSQ_Surface_vs_T"

# R² 阈值
RSQ_THRESHOLD = 0.95


# =========================================================
# 3. PubChem 请求设置
# =========================================================

SLEEP_SECONDS = 0.25
TIMEOUT = 20
MAX_RETRY = 3


# =========================================================
# 4. 基础工具函数
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


def empty_pubchem_result(status):
    return {
        "pubchem_status": status,
        "pubchem_query_used": None,
        "pubchem_query_value": None,
        "pubchem_cid": None,
        "pubchem_canonical_smiles": None,
        "pubchem_isomeric_smiles": None,
        "pubchem_connectivity_smiles": None,
        "pubchem_molecular_formula": None,
        "pubchem_iupac_name": None,
        "pubchem_inchikey": None,
    }


def is_valid_smiles(smiles):
    """
    判断最终 SMILES 是否适合单分子 QSPR 建模。

    当前是弱验证：
        1. 非空
        2. 不是 待定 / nan / none / null
        3. 不含 "."，即排除多组分 SMILES
    """
    if not is_valid_value(smiles):
        return False

    s = str(smiles).strip()

    if "." in s:
        return False

    return True


def choose_final_smiles(row):
    """
    最终 SMILES 优先级：
    1. PubChem IsomericSMILES
    2. PubChem CanonicalSMILES
    3. PubChem ConnectivitySMILES
    4. 原始 smiles
    """
    for col in [
        "pubchem_isomeric_smiles",
        "pubchem_canonical_smiles",
        "pubchem_connectivity_smiles",
        "smiles",
    ]:
        if col in row.index and is_valid_value(row.get(col, None)):
            return row[col]

    return None


# =========================================================
# 5. PubChem 查询函数
# =========================================================

def pubchem_get_properties(namespace, identifier):
    """
    namespace:
        - inchikey
        - name

    CAS 号也使用 name namespace 查询。
    """

    if not is_valid_value(identifier):
        return empty_pubchem_result("empty_query")

    query = quote(str(identifier).strip())

    url = (
        f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/{namespace}/"
        f"{query}/property/"
        "CanonicalSMILES,IsomericSMILES,ConnectivitySMILES,"
        "MolecularFormula,IUPACName,InChIKey/JSON"
    )

    last_status = None

    for attempt in range(1, MAX_RETRY + 1):
        try:
            r = requests.get(url, timeout=TIMEOUT)

            if r.status_code == 404:
                return empty_pubchem_result("not_found")

            if r.status_code in [429, 500, 502, 503, 504]:
                last_status = f"http_{r.status_code}"
                time.sleep(1.0 * attempt)
                continue

            if r.status_code != 200:
                return empty_pubchem_result(f"http_{r.status_code}")

            data = r.json()
            props = data.get("PropertyTable", {}).get("Properties", [])

            if not props:
                return empty_pubchem_result("no_property")

            p = props[0]

            return {
                "pubchem_status": "ok",
                "pubchem_query_used": None,
                "pubchem_query_value": None,
                "pubchem_cid": p.get("CID"),
                "pubchem_canonical_smiles": p.get("CanonicalSMILES"),
                "pubchem_isomeric_smiles": p.get("IsomericSMILES"),
                "pubchem_connectivity_smiles": p.get("ConnectivitySMILES"),
                "pubchem_molecular_formula": p.get("MolecularFormula"),
                "pubchem_iupac_name": p.get("IUPACName"),
                "pubchem_inchikey": p.get("InChIKey"),
            }

        except requests.exceptions.Timeout:
            last_status = "timeout"
            time.sleep(1.0 * attempt)

        except Exception as e:
            last_status = f"error: {e}"
            time.sleep(1.0 * attempt)

    return empty_pubchem_result(f"failed_after_retry_{last_status}")


def query_pubchem_for_one_material(row):
    """
    查询优先级：
    1. inchikey
    2. cas
    3. compound_name
    """

    inchikey = row.get("inchikey", None)
    cas = row.get("cas", None)
    compound_name = row.get("compound_name", None)

    # 1. 优先 InChIKey
    if is_valid_value(inchikey):
        res = pubchem_get_properties("inchikey", inchikey)
        res["pubchem_query_used"] = "inchikey"
        res["pubchem_query_value"] = inchikey

        if res["pubchem_status"] == "ok":
            return res

    # 2. CAS
    if is_valid_value(cas):
        res = pubchem_get_properties("name", cas)
        res["pubchem_query_used"] = "cas"
        res["pubchem_query_value"] = cas

        if res["pubchem_status"] == "ok":
            return res

    # 3. compound_name
    if is_valid_value(compound_name):
        res = pubchem_get_properties("name", compound_name)
        res["pubchem_query_used"] = "compound_name"
        res["pubchem_query_value"] = compound_name

        if res["pubchem_status"] == "ok":
            return res

    return empty_pubchem_result("not_found_by_inchikey_cas_or_name")


# =========================================================
# 6. 读取 Surface tension 线性度结果数据
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

print("\n读取 sheet:", input_sheet)
print("原始数据行数:", len(df))
print("原始列名:")
print(list(df.columns))


# =========================================================
# 7. 基础列整理
# =========================================================

# 如果原始表里有 SMILES 但没有 smiles，统一成 smiles
if "smiles" not in df.columns and "SMILES" in df.columns:
    df["smiles"] = df["SMILES"]

if "smiles" not in df.columns:
    df["smiles"] = None

if "material_key" not in df.columns:
    df["material_key"] = df.apply(build_material_key, axis=1)

df["material_key"] = df["material_key"].fillna("unknown_material")


# =========================================================
# 8. 基于线性度筛选有效物质
# =========================================================

df_before_rsq_filter = df.copy()

if KEEP_ONLY_FIT_STATUS_OK:
    if "fit_status" not in df.columns:
        print("\n警告：没有 fit_status 列，跳过 fit_status 筛选。")
    else:
        before = len(df)
        df = df[df["fit_status"] == "ok"].copy()
        print(f"\nfit_status == ok 筛选后数据行数: {len(df)}，删除: {before - len(df)}")

if KEEP_ONLY_RSQ_ABOVE_THRESHOLD:
    if RSQ_COL not in df.columns:
        print(f"\n警告：没有 {RSQ_COL} 列，跳过 R² 阈值筛选。")
    else:
        df[RSQ_COL] = pd.to_numeric(df[RSQ_COL], errors="coerce")
        before = len(df)
        df = df[df[RSQ_COL] >= RSQ_THRESHOLD].copy()
        print(
            f"\n{RSQ_COL} >= {RSQ_THRESHOLD} 筛选后数据行数: {len(df)}，删除: {before - len(df)}"
        )

df_removed_by_rsq_filter = df_before_rsq_filter[
    ~df_before_rsq_filter["material_key"].isin(df["material_key"].unique())
].copy()

if len(df_removed_by_rsq_filter) > 0:
    df_removed_by_rsq_filter["remove_reason"] = "removed_by_fit_status_or_rsq_filter"

print("\n========== 线性度有效物质筛选结果 ==========")
print("筛选前数据行数:", len(df_before_rsq_filter))
print("筛选前物质数:", df_before_rsq_filter["material_key"].nunique())
print("筛选后数据行数:", len(df))
print("筛选后物质数:", df["material_key"].nunique())
print("被线性度筛选删除的数据行数:", len(df_removed_by_rsq_filter))


# =========================================================
# 9. 提取唯一物质表
# =========================================================

material_cols = [
    "material_key",
    "compound_name",
    "cas",
    "formula",
    "inchikey",
    "inchi",
    "smiles",
    "RSQ_Surface_vs_T",
    "slope_Surface_vs_T",
    "intercept_Surface_vs_T",
    "fit_status",
]

material_cols = [c for c in material_cols if c in df.columns]

materials = (
    df[material_cols]
    .drop_duplicates(subset=["material_key"])
    .reset_index(drop=True)
)

print("\n需要查询的唯一物质数:", len(materials))


# =========================================================
# 10. 查询 PubChem
# =========================================================

results = []

for i, row in materials.iterrows():
    if (i + 1) % 20 == 0 or (i + 1) == len(materials):
        print(f"已查询 {i + 1}/{len(materials)}")

    res = query_pubchem_for_one_material(row)
    results.append(res)

    time.sleep(SLEEP_SECONDS)


pubchem_df = pd.concat(
    [materials.reset_index(drop=True), pd.DataFrame(results)],
    axis=1
)


# =========================================================
# 11. 合并回 Surface tension 数据
# =========================================================

merge_cols = [
    "material_key",
    "pubchem_status",
    "pubchem_query_used",
    "pubchem_query_value",
    "pubchem_cid",
    "pubchem_canonical_smiles",
    "pubchem_isomeric_smiles",
    "pubchem_connectivity_smiles",
    "pubchem_molecular_formula",
    "pubchem_iupac_name",
    "pubchem_inchikey",
]

old_pubchem_cols = [
    "pubchem_status",
    "pubchem_query_used",
    "pubchem_query_value",
    "pubchem_cid",
    "pubchem_canonical_smiles",
    "pubchem_isomeric_smiles",
    "pubchem_smiles",
    "pubchem_connectivity_smiles",
    "pubchem_molecular_formula",
    "pubchem_iupac_name",
    "pubchem_inchikey",
    "final_smiles",
    "final_smiles_valid",
    "SMILES",
]

df_base = df.drop(columns=[c for c in old_pubchem_cols if c in df.columns])

df_out = df_base.merge(
    pubchem_df[merge_cols],
    on="material_key",
    how="left"
)

df_out["final_smiles"] = df_out.apply(choose_final_smiles, axis=1)
df_out["SMILES"] = df_out["final_smiles"]
df_out["final_smiles_valid"] = df_out["final_smiles"].apply(is_valid_smiles)


# =========================================================
# 12. 公式与 InChIKey 一致性检查
# =========================================================

if "formula" in df_out.columns and "pubchem_molecular_formula" in df_out.columns:
    df_out["formula_match_pubchem"] = (
        df_out["formula"].astype(str).str.strip()
        == df_out["pubchem_molecular_formula"].astype(str).str.strip()
    )

if "inchikey" in df_out.columns and "pubchem_inchikey" in df_out.columns:
    df_out["inchikey_match_pubchem"] = (
        df_out["inchikey"].astype(str).str.strip()
        == df_out["pubchem_inchikey"].astype(str).str.strip()
    )


# =========================================================
# 13. 结果汇总
# =========================================================

ok_materials = pubchem_df[pubchem_df["pubchem_status"] == "ok"].copy()
failed_materials = pubchem_df[pubchem_df["pubchem_status"] != "ok"].copy()

with_smiles_materials = pubchem_df[
    pubchem_df["pubchem_isomeric_smiles"].notna()
    | pubchem_df["pubchem_canonical_smiles"].notna()
    | pubchem_df["pubchem_connectivity_smiles"].notna()
].copy()

material_smiles_map_cols = [
    "material_key",
    "compound_name",
    "cas",
    "formula",
    "inchikey",
    "smiles",
    "fit_status",
    "RSQ_Surface_vs_T",
    "slope_Surface_vs_T",
    "intercept_Surface_vs_T",
    "pubchem_status",
    "pubchem_query_used",
    "pubchem_query_value",
    "pubchem_cid",
    "pubchem_isomeric_smiles",
    "pubchem_canonical_smiles",
    "pubchem_connectivity_smiles",
    "pubchem_molecular_formula",
    "pubchem_iupac_name",
    "pubchem_inchikey",
    "final_smiles",
    "SMILES",
    "final_smiles_valid",
]

material_smiles_map_cols = [
    c for c in material_smiles_map_cols
    if c in df_out.columns
]

material_smiles_map = (
    df_out[material_smiles_map_cols]
    .drop_duplicates(subset=["material_key"])
    .reset_index(drop=True)
)

valid_smiles_materials = material_smiles_map[
    material_smiles_map["final_smiles_valid"] == True
].copy()

invalid_smiles_materials = material_smiles_map[
    material_smiles_map["final_smiles_valid"] != True
].copy()

df_valid_smiles_only = df_out[df_out["final_smiles_valid"] == True].copy()


# 公式不匹配 / InChIKey 不匹配的物质诊断
if "formula_match_pubchem" in df_out.columns:
    formula_mismatch_materials = (
        df_out[df_out["formula_match_pubchem"] == False]
        .drop_duplicates(subset=["material_key"])
        .copy()
    )
else:
    formula_mismatch_materials = pd.DataFrame()

if "inchikey_match_pubchem" in df_out.columns:
    inchikey_mismatch_materials = (
        df_out[df_out["inchikey_match_pubchem"] == False]
        .drop_duplicates(subset=["material_key"])
        .copy()
    )
else:
    inchikey_mismatch_materials = pd.DataFrame()


summary = pd.DataFrame([
    {"item": "input_file", "value": str(input_file)},
    {"item": "input_sheet", "value": input_sheet},
    {"item": "output_file", "value": str(output_file)},

    {"item": "KEEP_ONLY_FIT_STATUS_OK", "value": KEEP_ONLY_FIT_STATUS_OK},
    {"item": "KEEP_ONLY_RSQ_ABOVE_THRESHOLD", "value": KEEP_ONLY_RSQ_ABOVE_THRESHOLD},
    {"item": "RSQ_COL", "value": RSQ_COL},
    {"item": "RSQ_THRESHOLD", "value": RSQ_THRESHOLD},

    {"item": "n_rows_before_rsq_filter", "value": len(df_before_rsq_filter)},
    {"item": "n_materials_before_rsq_filter", "value": df_before_rsq_filter["material_key"].nunique()},
    {"item": "n_rows_after_rsq_filter", "value": len(df)},
    {"item": "n_materials_after_rsq_filter", "value": df["material_key"].nunique()},

    {"item": "n_unique_materials_for_pubchem_query", "value": len(materials)},

    {"item": "n_pubchem_ok_materials", "value": len(ok_materials)},
    {"item": "n_pubchem_failed_materials", "value": len(failed_materials)},
    {"item": "n_materials_with_pubchem_smiles", "value": len(with_smiles_materials)},

    {"item": "n_materials_with_valid_final_smiles", "value": len(valid_smiles_materials)},
    {"item": "n_materials_with_invalid_or_missing_final_smiles", "value": len(invalid_smiles_materials)},
    {"item": "n_rows_with_valid_final_smiles", "value": len(df_valid_smiles_only)},

    {"item": "n_formula_mismatch_materials", "value": len(formula_mismatch_materials)},
    {"item": "n_inchikey_mismatch_materials", "value": len(inchikey_mismatch_materials)},

    {"item": "query_priority", "value": "inchikey -> cas -> compound_name"},
    {
        "item": "final_smiles_priority",
        "value": "PubChem IsomericSMILES -> CanonicalSMILES -> ConnectivitySMILES -> original smiles",
    },
    {"item": "valid_smiles_rule", "value": "not empty and not containing '.'"},
])


# =========================================================
# 14. 保存 Excel
# =========================================================

with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_out.to_excel(writer, sheet_name="Data_With_SMILES", index=False)
    df_valid_smiles_only.to_excel(writer, sheet_name="Data_Valid_SMILES_Only", index=False)

    material_smiles_map.to_excel(writer, sheet_name="Material_SMILES_Map", index=False)
    valid_smiles_materials.to_excel(writer, sheet_name="Valid_SMILES_Materials", index=False)
    invalid_smiles_materials.to_excel(writer, sheet_name="Invalid_SMILES_Materials", index=False)

    pubchem_df.to_excel(writer, sheet_name="PubChem_Material_Map", index=False)
    ok_materials.to_excel(writer, sheet_name="PubChem_OK", index=False)
    failed_materials.to_excel(writer, sheet_name="PubChem_Failed", index=False)

    formula_mismatch_materials.to_excel(writer, sheet_name="Formula_Mismatch", index=False)
    inchikey_mismatch_materials.to_excel(writer, sheet_name="InChIKey_Mismatch", index=False)

    df_removed_by_rsq_filter.to_excel(
        writer,
        sheet_name="Removed_By_RSQ_Filter",
        index=False
    )

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


# =========================================================
# 15. 控制台输出
# =========================================================

print("\n保存完成:", output_file)

print("\n========== 线性度筛选统计 ==========")
print("筛选前数据行数:", len(df_before_rsq_filter))
print("筛选前物质数:", df_before_rsq_filter["material_key"].nunique())
print("筛选后数据行数:", len(df))
print("筛选后物质数:", df["material_key"].nunique())

print("\nPubChem 查询状态统计:")
print(pubchem_df["pubchem_status"].value_counts(dropna=False))

print("\n成功获取 PubChem SMILES 的物质数:")
print(len(with_smiles_materials))

print("\n有效 final_smiles 物质数:")
print(len(valid_smiles_materials))

print("\n无效或缺失 final_smiles 物质数:")
print(len(invalid_smiles_materials))

print("\n公式不匹配物质数:")
print(len(formula_mismatch_materials))

print("\nInChIKey 不匹配物质数:")
print(len(inchikey_mismatch_materials))

print("\n前几行结果:")
show_cols = [
    "compound_name",
    "cas",
    "formula",
    "inchikey",
    "RSQ_Surface_vs_T",
    "fit_status",
    "pubchem_cid",
    "pubchem_isomeric_smiles",
    "pubchem_canonical_smiles",
    "SMILES",
    "final_smiles_valid",
]

show_cols = [c for c in show_cols if c in df_out.columns]

print(df_out[show_cols].head(20).to_string(index=False))