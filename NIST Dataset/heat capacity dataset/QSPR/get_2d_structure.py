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
input_file = Path("Cp_dataset_selected_by_two_k_with_interpolation.xlsx")
sheet_name = "Sheet1_selected"

# 每个物质 8 行温度点
n_points_per_material = 8

# 输出文件
mapping_output = Path("pubchem_name_inchikey_to_cid_results.xlsx")
sdf_prefix = "pubchem_2d_batch"
combined_sdf_file = Path("pubchem_2d_all.sdf")

# 批量下载 SDF 的 batch size
batch_size = 100

# PubChem 请求间隔，避免过快
query_sleep = 0.25
download_sleep = 0.5


# =========================================================
# 2. 自动识别列名
# =========================================================
def normalize_colname(name):
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


# 你可以根据实际 Excel 列名，在这里补充候选名称
compound_name_candidates = [
    "compound_name",
    "Compound Name",
    "compound name",
    "name",
    "Name",
    "material_name",
    "material_key",
]

inchikey_candidates = [
    "inchikey",
    "InChIKey",
    "InChI Key",
    "inchi_key",
    "standard_inchikey",
    "pubchem_inchikey",
]


# =========================================================
# 3. 读取 Sheet1_selected，并整理成每个物质一行
# =========================================================
df = pd.read_excel(input_file, sheet_name=sheet_name)

print("原始 Sheet1_selected 行数:", len(df))
print("原始列名:")
print(list(df.columns))

compound_name_col = find_column(df, compound_name_candidates)
inchikey_col = find_column(df, inchikey_candidates)

print("\n识别到的 compound_name 列:", compound_name_col)
print("识别到的 inchikey 列:", inchikey_col)

if compound_name_col is None and inchikey_col is None:
    raise ValueError(
        "没有找到 compound_name 或 inchikey 相关列。\n"
        "请检查 Sheet1_selected 中的列名，或者在 candidate 列表中补充真实列名。"
    )

# 每个物质只保留一行
# 优先用 original_material_index 分组；否则默认每 8 行一个物质
if "original_material_index" in df.columns:
    material_df = (
        df.groupby("original_material_index", sort=False)
        .first()
        .reset_index()
    )
    material_index_col = "original_material_index"
else:
    if len(df) % n_points_per_material != 0:
        raise ValueError(
            f"Sheet1_selected 行数 {len(df)} 不能被 {n_points_per_material} 整除，"
            "且没有 original_material_index 列，无法确定每个物质。"
        )

    material_df = df.iloc[::n_points_per_material].copy().reset_index(drop=True)
    material_df.insert(0, "material_index", np.arange(len(material_df)))
    material_index_col = "material_index"

print("\n物质数量:", len(material_df))


# =========================================================
# 4. PubChem 查询函数
# =========================================================
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0"
})


def query_cid_by_namespace(namespace, identifier, timeout=20, max_retry=3):
    """
    使用 PubChem PUG REST 查询 CID。

    namespace 可选:
    - inchikey
    - name

    返回:
    best_cid, all_cids, status
    """
    if identifier is None or pd.isna(identifier):
        return None, [], "empty_identifier"

    identifier = str(identifier).strip()

    if identifier == "":
        return None, [], "empty_identifier"

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

            elif r.status_code == 404:
                return None, [], "not_found"

            elif r.status_code in [429, 500, 502, 503, 504]:
                last_status = f"http_{r.status_code}"
                time.sleep(1.0 * attempt)

            else:
                return None, [], f"http_{r.status_code}"

        except Exception as e:
            last_status = f"exception: {type(e).__name__}"
            time.sleep(1.0 * attempt)

    return None, [], f"failed_after_retry_{last_status}"


def query_cid_for_material(row):
    """
    优先用 InChIKey 查 CID。
    如果失败，再用 compound_name 查 CID。
    """
    inchikey_value = None
    compound_name_value = None

    if inchikey_col is not None:
        inchikey_value = row.get(inchikey_col, None)

    if compound_name_col is not None:
        compound_name_value = row.get(compound_name_col, None)

    # 1. 优先 InChIKey
    if inchikey_value is not None and not pd.isna(inchikey_value) and str(inchikey_value).strip() != "":
        best_cid, all_cids, status = query_cid_by_namespace("inchikey", inchikey_value)

        if best_cid is not None:
            return {
                "CID": best_cid,
                "CID_all": ",".join(map(str, all_cids)) if all_cids else "",
                "query_source": "inchikey",
                "query_identifier": str(inchikey_value).strip(),
                "query_status": status,
                "inchikey_status": status,
                "name_status": "",
            }

        inchikey_status = status
    else:
        inchikey_status = "no_inchikey"

    # 2. InChIKey 失败后，用 compound_name
    if compound_name_value is not None and not pd.isna(compound_name_value) and str(compound_name_value).strip() != "":
        best_cid, all_cids, status = query_cid_by_namespace("name", compound_name_value)

        if best_cid is not None:
            return {
                "CID": best_cid,
                "CID_all": ",".join(map(str, all_cids)) if all_cids else "",
                "query_source": "compound_name",
                "query_identifier": str(compound_name_value).strip(),
                "query_status": status,
                "inchikey_status": inchikey_status,
                "name_status": status,
            }

        name_status = status
    else:
        name_status = "no_compound_name"

    return {
        "CID": None,
        "CID_all": "",
        "query_source": "",
        "query_identifier": "",
        "query_status": "not_found_by_inchikey_or_name",
        "inchikey_status": inchikey_status,
        "name_status": name_status,
    }


# =========================================================
# 5. 逐物质查询 CID
# =========================================================
results = []

# 简单缓存：相同 InChIKey 或名称不重复请求
query_cache = {}

for i, row in material_df.iterrows():
    material_id = row[material_index_col]

    compound_name_value = row.get(compound_name_col, "") if compound_name_col is not None else ""
    inchikey_value = row.get(inchikey_col, "") if inchikey_col is not None else ""

    cache_key = (
        str(inchikey_value).strip() if not pd.isna(inchikey_value) else "",
        str(compound_name_value).strip() if not pd.isna(compound_name_value) else "",
    )

    if cache_key in query_cache:
        query_result = query_cache[cache_key].copy()
    else:
        query_result = query_cid_for_material(row)
        query_cache[cache_key] = query_result.copy()
        time.sleep(query_sleep)

    out_row = {
        material_index_col: material_id,
        "compound_name": compound_name_value,
        "inchikey": inchikey_value,
    }

    # 额外保留一些常见信息列，方便检查
    for extra_col in [
        "original_material_index",
        "cas",
        "formula",
        "SMILES",
        "smiles",
        "pubchem_cid",
        "material_key",
        "phase",
        "boiling_T_K",
        "critical_T_K",
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
# 6. 保存 CID 映射结果
# =========================================================
df_success = map_df[map_df["CID"].notna()].copy()
df_failed = map_df[map_df["CID"].isna()].copy()

# 去重 CID，但保留顺序
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

with pd.ExcelWriter(mapping_output, engine="openpyxl") as writer:
    map_df.to_excel(writer, sheet_name="All_Query_Results", index=False)
    df_success.to_excel(writer, sheet_name="Success", index=False)
    df_failed.to_excel(writer, sheet_name="Failed", index=False)
    df_unique_cids.to_excel(writer, sheet_name="Unique_CIDs", index=False)

    summary = pd.DataFrame([
        {"item": "input_file", "value": str(input_file)},
        {"item": "sheet_name", "value": sheet_name},
        {"item": "material_count", "value": len(material_df)},
        {"item": "success_count", "value": len(df_success)},
        {"item": "failed_count", "value": len(df_failed)},
        {"item": "unique_cid_count", "value": len(valid_cids_unique)},
        {"item": "compound_name_col", "value": compound_name_col},
        {"item": "inchikey_col", "value": inchikey_col},
    ])
    summary.to_excel(writer, sheet_name="Summary", index=False)

print("\n已保存 CID 映射结果:", mapping_output)


# =========================================================
# 7. 批量下载 2D SDF
# =========================================================
print(f"\n可下载 2D SDF 的唯一 CID 数量: {len(valid_cids_unique)}")

if len(valid_cids_unique) == 0:
    print("没有可下载的 CID，程序结束。")
else:
    # 如果已存在 combined 文件，先删除
    if combined_sdf_file.exists():
        combined_sdf_file.unlink()

    for batch_idx, start in enumerate(range(0, len(valid_cids_unique), batch_size), start=1):
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

                    # 同时写入总 SDF 文件
                    with open(combined_sdf_file, "ab") as f:
                        f.write(r.content)
                        if not r.content.endswith(b"\n"):
                            f.write(b"\n")

                    print(f"已保存: {out_file}  本批 CID 数: {len(batch)}")

                    success = True
                    break

                else:
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