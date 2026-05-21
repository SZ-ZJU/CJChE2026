import pandas as pd
import requests
import time
from pathlib import Path
from urllib.parse import quote


# =========================================================
# 1. 输入输出文件
# =========================================================
input_file = Path("thermoml_Density_Liquid_around_100kPa_deduplicated_min3_Tgt30.xlsx")
input_sheet = "Liquid_100kPa_Final"

output_file = Path("thermoml_Density_Liquid_100kPa_with_PubChem_SMILES.xlsx")


# =========================================================
# 2. PubChem 请求设置
# =========================================================
SLEEP_SECONDS = 0.25
TIMEOUT = 20
MAX_RETRY = 3


# =========================================================
# 3. 基础工具函数
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


# =========================================================
# 4. PubChem 查询函数
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
# 5. 读取筛选后的 density 数据
# =========================================================
df = pd.read_excel(input_file, sheet_name=input_sheet)

print("原始数据行数:", len(df))
print("原始列名:")
print(list(df.columns))


# 如果原始表里有 SMILES 但没有 smiles，统一成 smiles
if "smiles" not in df.columns and "SMILES" in df.columns:
    df["smiles"] = df["SMILES"]


if "material_key" not in df.columns:
    df["material_key"] = df.apply(build_material_key, axis=1)


# =========================================================
# 6. 提取唯一物质表
# =========================================================
material_cols = [
    "material_key",
    "compound_name",
    "cas",
    "formula",
    "inchikey",
    "inchi",
    "smiles",
]

material_cols = [c for c in material_cols if c in df.columns]

materials = (
    df[material_cols]
    .drop_duplicates(subset=["material_key"])
    .reset_index(drop=True)
)

print("\n需要查询的唯一物质数:", len(materials))


# =========================================================
# 7. 查询 PubChem
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
# 8. 合并回原始 density 数据
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

# 删除旧 PubChem / SMILES 输出列，防止重复
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


# =========================================================
# 9. 公式一致性检查
# =========================================================
if "formula" in df_out.columns and "pubchem_molecular_formula" in df_out.columns:
    df_out["formula_match_pubchem"] = (
        df_out["formula"].astype(str).str.strip()
        == df_out["pubchem_molecular_formula"].astype(str).str.strip()
    )


# =========================================================
# 10. 结果汇总
# =========================================================
ok_materials = pubchem_df[pubchem_df["pubchem_status"] == "ok"].copy()
failed_materials = pubchem_df[pubchem_df["pubchem_status"] != "ok"].copy()

with_smiles_materials = pubchem_df[
    pubchem_df["pubchem_isomeric_smiles"].notna()
    | pubchem_df["pubchem_canonical_smiles"].notna()
    | pubchem_df["pubchem_connectivity_smiles"].notna()
].copy()

summary = pd.DataFrame([
    {"item": "input_file", "value": str(input_file)},
    {"item": "input_sheet", "value": input_sheet},
    {"item": "output_file", "value": str(output_file)},
    {"item": "n_rows", "value": len(df)},
    {"item": "n_unique_materials", "value": len(materials)},
    {"item": "n_pubchem_ok_materials", "value": len(ok_materials)},
    {"item": "n_pubchem_failed_materials", "value": len(failed_materials)},
    {"item": "n_materials_with_pubchem_smiles", "value": len(with_smiles_materials)},
    {"item": "query_priority", "value": "inchikey -> cas -> compound_name"},
])


# =========================================================
# 11. 保存 Excel
# =========================================================
with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
    df_out.to_excel(writer, sheet_name="Data_With_SMILES", index=False)
    pubchem_df.to_excel(writer, sheet_name="PubChem_Material_Map", index=False)
    ok_materials.to_excel(writer, sheet_name="PubChem_OK", index=False)
    failed_materials.to_excel(writer, sheet_name="PubChem_Failed", index=False)
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

print("\nPubChem 查询状态统计:")
print(pubchem_df["pubchem_status"].value_counts(dropna=False))

print("\n成功获取 PubChem SMILES 的物质数:")
print(len(with_smiles_materials))

print("\n前几行结果:")
show_cols = [
    "compound_name",
    "cas",
    "formula",
    "inchikey",
    "pubchem_cid",
    "pubchem_isomeric_smiles",
    "pubchem_canonical_smiles",
    "SMILES",
]

show_cols = [c for c in show_cols if c in df_out.columns]

print(df_out[show_cols].head(20))