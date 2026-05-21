# -*- coding: utf-8 -*-
"""
Surface tension liquid-gas QSPR 前处理脚本：
从最终表面张力数据中提取物质信息，查询 PubChem CID，并下载 2D SDF 文件。

输入：
    dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points_with_RSQ.xlsx

如果该文件不存在，自动尝试：
    dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points.xlsx

优先读取 sheet：
    Material_selected

如果没有 Material_selected，则读取：
    Data_selected

输出：
    1. surface_tension_pubchem_cid_mapping_results.xlsx
    2. surface_tension_pubchem_2d_batch_01.sdf, surface_tension_pubchem_2d_batch_02.sdf, ...
    3. surface_tension_pubchem_2d_all.sdf

功能：
    1. 从表面张力数据中整理出一行一个物质的 Material 表
    2. 自动识别 compound_name / inchikey / SMILES / cas / pubchem_cid
    3. 按优先级查询 PubChem CID：
        existing_pubchem_cid -> inchikey -> SMILES -> cas -> compound_name
    4. 保存 CID 查询结果
    5. 批量下载 PubChem 2D SDF
"""

import re
import time
from pathlib import Path
from urllib.parse import quote

import requests
import pandas as pd
import numpy as np


# =========================================================
# 1. 输入文件与基本设置
# =========================================================

preferred_input_file = Path(
    "dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points_with_RSQ.xlsx"
)

fallback_input_file = Path(
    "dataset_surface_tension_selected_by_two_k_with_surface_T_interpolation_8points.xlsx"
)

if preferred_input_file.exists():
    input_file = preferred_input_file
elif fallback_input_file.exists():
    input_file = fallback_input_file
else:
    raise FileNotFoundError(
        "没有找到输入文件：\n"
        f"1. {preferred_input_file}\n"
        f"2. {fallback_input_file}"
    )

# 表面张力表格中推荐使用 Material_selected：
# 这个 sheet 通常是一行一个物质，适合做 PubChem 结构查询
preferred_sheet_name = "Material_selected"

# 如果没有 Material_selected，则退回 Data_selected
fallback_sheet_name = "Data_selected"

# 如果 Data_selected 中没有 material_key / original_material_index，
# 才会使用每个物质的数据点数进行兜底切分。
n_points_per_material = 8

# 输出文件
mapping_output = Path("surface_tension_pubchem_cid_mapping_results.xlsx")

# SDF 输出
sdf_prefix = "surface_tension_pubchem_2d_batch"
combined_sdf_file = Path("surface_tension_pubchem_2d_all.sdf")

# 批量下载 SDF 的 batch size
batch_size = 100

# PubChem 请求间隔，避免请求过快
query_sleep = 0.25
download_sleep = 0.5


# =========================================================
# 2. 自动识别列名
# =========================================================

def normalize_colname(name):
    """
    标准化列名：忽略大小写、空格、下划线、特殊字符。
    """
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def find_column(df, candidate_names):
    """
    根据候选列名自动匹配真实列名。
    忽略大小写、空格、下划线等。
    """
    norm_to_real = {
        normalize_colname(col): col
        for col in df.columns
    }

    for name in candidate_names:
        key = normalize_colname(name)

        if key in norm_to_real:
            return norm_to_real[key]

    return None


compound_name_candidates = [
    "compound_name",
    "Compound Name",
    "compound name",
    "name",
    "Name",
    "material_name",
    "material_key",
    "pubchem_iupac_name",
]

inchikey_candidates = [
    "inchikey",
    "InChIKey",
    "InChI Key",
    "inchi_key",
    "standard_inchikey",
    "pubchem_inchikey",
    "PubChem_InChIKey",
]

smiles_candidates = [
    "SMILES",
    "smiles",
    "final_smiles",
    "canonical_smiles",
    "pubchem_smiles",
    "pubchem_isomeric_smiles",
    "pubchem_canonical_smiles",
    "pubchem_connectivity_smiles",
]

cas_candidates = [
    "cas",
    "CAS",
    "CASRN",
    "component_cas",
]

cid_candidates = [
    "pubchem_cid",
    "PubChem CID",
    "CID",
    "cid",
    "pubchem_cid_for_Tb",
    "pubchem_cid_for_Tb_Tc",
]


# =========================================================
# 3. 读取表面张力 Excel，并整理成每个物质一行
# =========================================================

if not input_file.exists():
    raise FileNotFoundError(f"没有找到输入文件: {input_file}")

xls = pd.ExcelFile(input_file)

print("输入文件:", input_file)
print("输入文件包含的 sheet:")
print(xls.sheet_names)

if preferred_sheet_name in xls.sheet_names:
    sheet_name = preferred_sheet_name
elif fallback_sheet_name in xls.sheet_names:
    sheet_name = fallback_sheet_name
else:
    raise ValueError(
        f"没有找到推荐 sheet: {preferred_sheet_name}，"
        f"也没有找到备用 sheet: {fallback_sheet_name}。\n"
        f"当前 sheet: {xls.sheet_names}"
    )

df = pd.read_excel(input_file, sheet_name=sheet_name)

print(f"\n当前使用 sheet: {sheet_name}")
print("原始行数:", len(df))
print("原始列名:")
print(list(df.columns))


compound_name_col = find_column(df, compound_name_candidates)
inchikey_col = find_column(df, inchikey_candidates)
smiles_col = find_column(df, smiles_candidates)
cas_col = find_column(df, cas_candidates)
cid_col = find_column(df, cid_candidates)

print("\n识别到的列:")
print("compound_name_col:", compound_name_col)
print("inchikey_col     :", inchikey_col)
print("smiles_col       :", smiles_col)
print("cas_col          :", cas_col)
print("cid_col          :", cid_col)


# =========================================================
# 4. 整理为每个物质一行
# =========================================================

if sheet_name == preferred_sheet_name:
    material_df = df.copy().reset_index(drop=True)

    if "original_material_index" in material_df.columns:
        material_index_col = "original_material_index"
    elif "material_key" in material_df.columns:
        material_index_col = "material_key"
    else:
        material_df.insert(0, "material_index", np.arange(len(material_df)))
        material_index_col = "material_index"

else:
    # 如果使用 Data_selected，优先按物质 ID 分组。
    # 这样支持每个物质不固定 8 个点。
    if "original_material_index" in df.columns:
        material_df = (
            df.groupby("original_material_index", sort=False)
            .first()
            .reset_index()
        )
        material_index_col = "original_material_index"

    elif "material_key" in df.columns:
        material_df = (
            df.groupby("material_key", sort=False)
            .first()
            .reset_index()
        )
        material_index_col = "material_key"

    elif "pubchem_cid" in df.columns:
        material_df = (
            df.groupby("pubchem_cid", sort=False)
            .first()
            .reset_index()
        )
        material_index_col = "pubchem_cid"

    elif "pubchem_cid_for_Tb" in df.columns:
        material_df = (
            df.groupby("pubchem_cid_for_Tb", sort=False)
            .first()
            .reset_index()
        )
        material_index_col = "pubchem_cid_for_Tb"

    elif "inchikey" in df.columns:
        material_df = (
            df.groupby("inchikey", sort=False)
            .first()
            .reset_index()
        )
        material_index_col = "inchikey"

    elif "pubchem_inchikey" in df.columns:
        material_df = (
            df.groupby("pubchem_inchikey", sort=False)
            .first()
            .reset_index()
        )
        material_index_col = "pubchem_inchikey"

    elif "cas" in df.columns:
        material_df = (
            df.groupby("cas", sort=False)
            .first()
            .reset_index()
        )
        material_index_col = "cas"

    elif "compound_name" in df.columns:
        material_df = (
            df.groupby("compound_name", sort=False)
            .first()
            .reset_index()
        )
        material_index_col = "compound_name"

    else:
        # 最后兜底：只有在没有任何物质 ID 且确实固定点数时使用。
        if len(df) % n_points_per_material != 0:
            raise ValueError(
                f"{sheet_name} 行数 {len(df)} 不能被 {n_points_per_material} 整除，"
                "且没有 original_material_index / material_key / pubchem_cid / "
                "inchikey / cas / compound_name，无法确定每个物质。"
            )

        material_df = df.iloc[::n_points_per_material].copy().reset_index(drop=True)
        material_df.insert(0, "material_index", np.arange(len(material_df)))
        material_index_col = "material_index"


print("\n物质数量:", len(material_df))
print("物质索引列:", material_index_col)

if (
    compound_name_col is None
    and inchikey_col is None
    and smiles_col is None
    and cas_col is None
    and cid_col is None
):
    raise ValueError(
        "没有找到 compound_name / inchikey / smiles / cas / pubchem_cid 相关列。\n"
        "请检查 Excel 列名，或在候选列名列表中补充真实列名。"
    )


# =========================================================
# 5. PubChem 查询函数
# =========================================================

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0"
})


def is_valid_text(x):
    if x is None or pd.isna(x):
        return False

    s = str(x).strip()

    if s == "":
        return False

    if s.lower() in ["nan", "none", "null", "待定"]:
        return False

    return True


def parse_existing_cid(x):
    """
    解析表格中已有的 PubChem CID。
    支持 int、float、字符串。
    """
    if not is_valid_text(x):
        return None

    s = str(x).strip()

    try:
        f = float(s)

        if np.isfinite(f) and f > 0:
            return int(f)

    except Exception:
        pass

    m = re.search(r"\d+", s)

    if m:
        return int(m.group(0))

    return None


def query_cid_by_namespace(namespace, identifier, timeout=20, max_retry=3):
    """
    使用 PubChem PUG REST 查询 CID。

    namespace 常用:
        - inchikey
        - name
        - smiles
    """
    if not is_valid_text(identifier):
        return None, [], "empty_identifier"

    identifier = str(identifier).strip()
    encoded_identifier = quote(identifier, safe="")

    url = (
        f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/"
        f"compound/{namespace}/{encoded_identifier}/cids/JSON"
    )

    last_status = None

    for attempt in range(1, max_retry + 1):
        try:
            r = session.get(url, timeout=timeout)

            if r.status_code == 200:
                data = r.json()
                cids = data.get("IdentifierList", {}).get("CID", [])

                if len(cids) == 0:
                    return None, [], "no_cid"

                if len(cids) == 1:
                    return cids[0], cids, "unique"

                return cids[0], cids, "multiple"

            if r.status_code == 404:
                return None, [], "not_found"

            if r.status_code in [429, 500, 502, 503, 504]:
                last_status = f"http_{r.status_code}"
                time.sleep(1.0 * attempt)
                continue

            return None, [], f"http_{r.status_code}"

        except Exception as e:
            last_status = f"exception: {type(e).__name__}"
            time.sleep(1.0 * attempt)

    return None, [], f"failed_after_retry_{last_status}"


def query_cid_for_material(row):
    """
    CID 查询优先级：
        1. Excel 中已有 pubchem_cid / pubchem_cid_for_Tb
        2. InChIKey / pubchem_inchikey
        3. SMILES / final_smiles
        4. CAS
        5. compound_name / pubchem_iupac_name
    """
    # 1. 已有 CID
    if cid_col is not None:
        cid_existing = parse_existing_cid(row.get(cid_col, None))

        if cid_existing is not None:
            return {
                "CID": cid_existing,
                "CID_all": str(cid_existing),
                "query_source": "existing_pubchem_cid",
                "query_identifier": str(row.get(cid_col, "")).strip(),
                "query_status": "from_existing_cid",
                "inchikey_status": "",
                "smiles_status": "",
                "cas_status": "",
                "name_status": "",
            }

    inchikey_status = ""
    smiles_status = ""
    cas_status = ""
    name_status = ""

    # 2. InChIKey
    if inchikey_col is not None:
        inchikey_value = row.get(inchikey_col, None)

        if is_valid_text(inchikey_value):
            best_cid, all_cids, status = query_cid_by_namespace(
                "inchikey",
                inchikey_value
            )

            if best_cid is not None:
                return {
                    "CID": best_cid,
                    "CID_all": ",".join(map(str, all_cids)) if all_cids else "",
                    "query_source": "inchikey",
                    "query_identifier": str(inchikey_value).strip(),
                    "query_status": status,
                    "inchikey_status": status,
                    "smiles_status": "",
                    "cas_status": "",
                    "name_status": "",
                }

            inchikey_status = status
        else:
            inchikey_status = "no_inchikey"
    else:
        inchikey_status = "no_inchikey_col"

    # 3. SMILES
    if smiles_col is not None:
        smiles_value = row.get(smiles_col, None)

        if is_valid_text(smiles_value):
            best_cid, all_cids, status = query_cid_by_namespace(
                "smiles",
                smiles_value
            )

            if best_cid is not None:
                return {
                    "CID": best_cid,
                    "CID_all": ",".join(map(str, all_cids)) if all_cids else "",
                    "query_source": "smiles",
                    "query_identifier": str(smiles_value).strip(),
                    "query_status": status,
                    "inchikey_status": inchikey_status,
                    "smiles_status": status,
                    "cas_status": "",
                    "name_status": "",
                }

            smiles_status = status
        else:
            smiles_status = "no_smiles"
    else:
        smiles_status = "no_smiles_col"

    # 4. CAS
    if cas_col is not None:
        cas_value = row.get(cas_col, None)

        if is_valid_text(cas_value):
            best_cid, all_cids, status = query_cid_by_namespace(
                "name",
                cas_value
            )

            if best_cid is not None:
                return {
                    "CID": best_cid,
                    "CID_all": ",".join(map(str, all_cids)) if all_cids else "",
                    "query_source": "cas",
                    "query_identifier": str(cas_value).strip(),
                    "query_status": status,
                    "inchikey_status": inchikey_status,
                    "smiles_status": smiles_status,
                    "cas_status": status,
                    "name_status": "",
                }

            cas_status = status
        else:
            cas_status = "no_cas"
    else:
        cas_status = "no_cas_col"

    # 5. compound name
    if compound_name_col is not None:
        compound_name_value = row.get(compound_name_col, None)

        if is_valid_text(compound_name_value):
            best_cid, all_cids, status = query_cid_by_namespace(
                "name",
                compound_name_value
            )

            if best_cid is not None:
                return {
                    "CID": best_cid,
                    "CID_all": ",".join(map(str, all_cids)) if all_cids else "",
                    "query_source": "compound_name",
                    "query_identifier": str(compound_name_value).strip(),
                    "query_status": status,
                    "inchikey_status": inchikey_status,
                    "smiles_status": smiles_status,
                    "cas_status": cas_status,
                    "name_status": status,
                }

            name_status = status
        else:
            name_status = "no_compound_name"
    else:
        name_status = "no_compound_name_col"

    return {
        "CID": None,
        "CID_all": "",
        "query_source": "",
        "query_identifier": "",
        "query_status": "not_found_by_existing_cid_inchikey_smiles_cas_or_name",
        "inchikey_status": inchikey_status,
        "smiles_status": smiles_status,
        "cas_status": cas_status,
        "name_status": name_status,
    }


# =========================================================
# 6. 逐物质查询 CID
# =========================================================

results = []
query_cache = {}

for i, row in material_df.iterrows():
    material_id = row.get(material_index_col, i)

    compound_name_value = (
        row.get(compound_name_col, "")
        if compound_name_col is not None
        else ""
    )

    inchikey_value = (
        row.get(inchikey_col, "")
        if inchikey_col is not None
        else ""
    )

    smiles_value = (
        row.get(smiles_col, "")
        if smiles_col is not None
        else ""
    )

    cas_value = (
        row.get(cas_col, "")
        if cas_col is not None
        else ""
    )

    cid_value = (
        row.get(cid_col, "")
        if cid_col is not None
        else ""
    )

    cache_key = (
        str(cid_value).strip() if is_valid_text(cid_value) else "",
        str(inchikey_value).strip() if is_valid_text(inchikey_value) else "",
        str(smiles_value).strip() if is_valid_text(smiles_value) else "",
        str(cas_value).strip() if is_valid_text(cas_value) else "",
        str(compound_name_value).strip() if is_valid_text(compound_name_value) else "",
    )

    if cache_key in query_cache:
        query_result = query_cache[cache_key].copy()
    else:
        query_result = query_cid_for_material(row)
        query_cache[cache_key] = query_result.copy()

        if query_result["query_source"] != "existing_pubchem_cid":
            time.sleep(query_sleep)

    out_row = {
        material_index_col: material_id,
        "compound_name": compound_name_value,
        "inchikey": inchikey_value,
        "smiles": smiles_value,
        "cas": cas_value,
        "existing_pubchem_cid": cid_value,
    }

    # 表面张力流程中建议保留的元信息与诊断列
    for extra_col in [
        "original_material_index",
        "material_key",
        "formula",
        "SMILES",
        "final_smiles",
        "pubchem_cid",
        "pubchem_cid_for_Tb",
        "pubchem_iupac_name",
        "pubchem_molecular_formula",
        "pubchem_inchikey",
        "boiling_T_K",
        "T_min",
        "T_max",
        "T_range",
        "n_points",
        "phase",
        "RSQ_Surface_vs_T",
        "slope_Surface_vs_T",
        "intercept_Surface_vs_T",
        "RSQ_Surface_vs_invT",
        "RSQ_lnSurface_vs_T",
        "fit_status",
        "slope_direction_Surface_vs_T",
        "SurfaceTension_min_N_m",
        "SurfaceTension_max_N_m",
        "SurfaceTension_range_N_m",
    ]:
        if extra_col in material_df.columns and extra_col not in out_row:
            out_row[extra_col] = row.get(extra_col, "")

    out_row.update(query_result)
    results.append(out_row)

    if (i + 1) % 20 == 0 or (i + 1) == len(material_df):
        print(f"已处理 {i + 1}/{len(material_df)}")


map_df = pd.DataFrame(results)

print("\nCID 查询结果统计:")
print(map_df["query_status"].value_counts(dropna=False))

print("\n查询来源统计:")
print(map_df["query_source"].value_counts(dropna=False))


# =========================================================
# 7. 保存 CID 映射结果
# =========================================================

df_success = map_df[map_df["CID"].notna()].copy()
df_failed = map_df[map_df["CID"].isna()].copy()

valid_cids = (
    df_success["CID"]
    .dropna()
    .astype(int)
    .tolist()
)

seen = set()
valid_cids_unique = []

for cid in valid_cids:
    if cid not in seen:
        valid_cids_unique.append(cid)
        seen.add(cid)

df_unique_cids = pd.DataFrame({
    "CID": valid_cids_unique
})

summary = pd.DataFrame([
    {"item": "input_file", "value": str(input_file)},
    {"item": "sheet_name_used", "value": sheet_name},
    {"item": "material_count", "value": len(material_df)},
    {"item": "success_count", "value": len(df_success)},
    {"item": "failed_count", "value": len(df_failed)},
    {"item": "unique_cid_count", "value": len(valid_cids_unique)},
    {"item": "compound_name_col", "value": compound_name_col},
    {"item": "inchikey_col", "value": inchikey_col},
    {"item": "smiles_col", "value": smiles_col},
    {"item": "cas_col", "value": cas_col},
    {"item": "cid_col", "value": cid_col},
    {"item": "query_priority", "value": "existing_pubchem_cid -> inchikey -> SMILES -> cas -> compound_name"},
    {"item": "target_property", "value": "Surface tension liquid-gas"},
    {"item": "sdf_record_type", "value": "2d"},
])

with pd.ExcelWriter(mapping_output, engine="openpyxl") as writer:
    map_df.to_excel(writer, sheet_name="All_Query_Results", index=False)
    df_success.to_excel(writer, sheet_name="Success", index=False)
    df_failed.to_excel(writer, sheet_name="Failed", index=False)
    df_unique_cids.to_excel(writer, sheet_name="Unique_CIDs", index=False)
    summary.to_excel(writer, sheet_name="Summary", index=False)

    number_format = "0.0000000000"

    for sheet_name_out in writer.sheets:
        ws = writer.sheets[sheet_name_out]

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

            ws.column_dimensions[col_letter].width = min(max_length + 2, 45)

print("\n已保存 CID 映射结果:", mapping_output)


# =========================================================
# 8. 批量下载 2D SDF
# =========================================================

print(f"\n可下载 2D SDF 的唯一 CID 数量: {len(valid_cids_unique)}")

if len(valid_cids_unique) == 0:
    print("没有可下载的 CID，程序结束。")

else:
    if combined_sdf_file.exists():
        combined_sdf_file.unlink()

    for batch_idx, start in enumerate(
        range(0, len(valid_cids_unique), batch_size),
        start=1
    ):
        batch = valid_cids_unique[start:start + batch_size]
        cid_str = ",".join(map(str, batch))

        sdf_url = (
            f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/"
            f"compound/cid/{cid_str}/record/SDF/?record_type=2d"
        )

        success = False
        last_error = ""

        for attempt in range(1, 4):
            try:
                r = session.get(sdf_url, timeout=120)

                if r.status_code == 200:
                    out_file = Path(f"{sdf_prefix}_{batch_idx:02d}.sdf")

                    with open(out_file, "wb") as f:
                        f.write(r.content)

                    with open(combined_sdf_file, "ab") as f:
                        f.write(r.content)

                        if not r.content.endswith(b"\n"):
                            f.write(b"\n")

                    print(f"已保存: {out_file}  本批 CID 数: {len(batch)}")
                    success = True
                    break

                last_error = f"http_{r.status_code}"
                time.sleep(1.0 * attempt)

            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                time.sleep(1.0 * attempt)

        if not success:
            print(f"第 {batch_idx} 批下载失败: {last_error}")

        time.sleep(download_sleep)

    print("\n完成。输出文件：")
    print(f"1) {mapping_output}")
    print(f"2) {sdf_prefix}_01.sdf, {sdf_prefix}_02.sdf, ...")
    print(f"3) {combined_sdf_file}")