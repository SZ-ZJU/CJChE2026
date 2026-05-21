import pandas as pd
import numpy as np
import requests
import time
import re
from pathlib import Path
from urllib.parse import quote


# =========================================================
# 1. 输入输出文件
# =========================================================
input_file = Path("thermoml_vapor_pressure_Liquid_final_n8_T80_noSi_remove_two.xlsx")
input_sheet = "Final_Selected_Data"

output_file = Path("thermoml_vapor_pressure_Liquid_final_with_Tb.xlsx")


# =========================================================
# 2. PubChem 请求设置
# =========================================================
SLEEP_SECONDS = 0.25
TIMEOUT = 25
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


def request_json(url, timeout=TIMEOUT, max_retry=MAX_RETRY):
    """
    带重试的 JSON 请求。
    """
    last_error = None

    for attempt in range(max_retry):
        try:
            r = requests.get(url, timeout=timeout)

            if r.status_code == 200:
                return r.json(), "ok"

            if r.status_code == 404:
                return None, "not_found"

            last_error = f"http_{r.status_code}"

        except requests.exceptions.Timeout:
            last_error = "timeout"

        except Exception as e:
            last_error = f"error: {e}"

        time.sleep(1.0 + attempt)

    return None, last_error


def value_to_text(value):
    """
    将 PubChem PUG-View 里的 Value 字段尽量转成普通字符串。
    """
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, list):
        return " ; ".join(value_to_text(v) for v in value)

    if isinstance(value, dict):
        parts = []

        if "StringWithMarkup" in value:
            for item in value["StringWithMarkup"]:
                if isinstance(item, dict) and "String" in item:
                    parts.append(str(item["String"]))

        if "Number" in value:
            number = value.get("Number")
            unit = value.get("Unit", "")
            parts.append(f"{number} {unit}".strip())

        if "String" in value:
            parts.append(str(value["String"]))

        for k, v in value.items():
            if k in ["StringWithMarkup", "Number", "Unit", "String"]:
                continue
            if isinstance(v, (str, int, float)):
                parts.append(str(v))

        return " ; ".join([p for p in parts if p])

    return str(value)


def iter_sections(section):
    """
    递归遍历 PUG-View JSON 里的 Section。
    """
    if isinstance(section, dict):
        yield section

        for sub in section.get("Section", []):
            yield from iter_sections(sub)

    elif isinstance(section, list):
        for item in section:
            yield from iter_sections(item)


def collect_section_texts(record_json):
    """
    从 PUG-View JSON 中提取所有 section 和 information 文本。
    """
    if not record_json:
        return []

    record = record_json.get("Record", {})
    sections = record.get("Section", [])

    rows = []

    for sec in iter_sections(sections):
        toc_heading = sec.get("TOCHeading", "")
        description = sec.get("Description", "")

        for info in sec.get("Information", []):
            info_name = info.get("Name", "")
            info_description = info.get("Description", "")
            value_text = value_to_text(info.get("Value", None))

            rows.append({
                "toc_heading": toc_heading,
                "section_description": description,
                "info_name": info_name,
                "info_description": info_description,
                "value_text": value_text,
            })

    return rows


# =========================================================
# 4. 温度文本解析
# =========================================================
def c_to_k(c):
    return c + 273.15


def f_to_k(f):
    return (f - 32.0) * 5.0 / 9.0 + 273.15


def parse_temperature_values_from_text(text):
    """
    从字符串中提取温度值，统一转成 K。

    支持：
    78.3 °C
    351.4 K
    172.9 F
    78.1-78.5 °C
    """
    if not is_valid_value(text):
        return []

    s = str(text)
    s = s.replace("−", "-")
    s = s.replace("–", "-")
    s = s.replace("—", "-")
    s = s.replace(",", "")

    results = []
    used_spans = []

    range_patterns = [
        (
            re.compile(
                r"(-?\d+(?:\.\d+)?)\s*(?:-|to)\s*(-?\d+(?:\.\d+)?)\s*(?:°\s*)?(?:C|c|deg\s*C|Celsius)\b"
            ),
            "C"
        ),
        (
            re.compile(
                r"(-?\d+(?:\.\d+)?)\s*(?:-|to)\s*(-?\d+(?:\.\d+)?)\s*(?:°\s*)?(?:F|f|deg\s*F|Fahrenheit)\b"
            ),
            "F"
        ),
        (
            re.compile(
                r"(-?\d+(?:\.\d+)?)\s*(?:-|to)\s*(-?\d+(?:\.\d+)?)\s*(?:K|k|Kelvin)\b"
            ),
            "K"
        ),
    ]

    for pattern, unit in range_patterns:
        for m in pattern.finditer(s):
            v1 = float(m.group(1))
            v2 = float(m.group(2))
            v = (v1 + v2) / 2.0

            if unit == "C":
                value_K = c_to_k(v)
            elif unit == "F":
                value_K = f_to_k(v)
            else:
                value_K = v

            results.append({
                "value_K": value_K,
                "unit_detected": unit,
                "matched_text": m.group(0),
                "is_range": True,
            })

            used_spans.append(m.span())

    def inside_used_span(span):
        for a, b in used_spans:
            if span[0] >= a and span[1] <= b:
                return True
        return False

    single_patterns = [
        (
            re.compile(
                r"(?<![A-Za-z])(-?\d+(?:\.\d+)?)\s*(?:°\s*)?(?:C|c|deg\s*C|Celsius)\b"
            ),
            "C"
        ),
        (
            re.compile(
                r"(?<![A-Za-z])(-?\d+(?:\.\d+)?)\s*(?:°\s*)?(?:F|f|deg\s*F|Fahrenheit)\b"
            ),
            "F"
        ),
        (
            re.compile(
                r"(?<![A-Za-z])(-?\d+(?:\.\d+)?)\s*(?:K|k|Kelvin)\b"
            ),
            "K"
        ),
    ]

    for pattern, unit in single_patterns:
        for m in pattern.finditer(s):
            if inside_used_span(m.span()):
                continue

            v = float(m.group(1))

            if unit == "C":
                value_K = c_to_k(v)
            elif unit == "F":
                value_K = f_to_k(v)
            else:
                value_K = v

            results.append({
                "value_K": value_K,
                "unit_detected": unit,
                "matched_text": m.group(0),
                "is_range": False,
            })

    return results


def plausible_boiling_temperature(value_K):
    """
    粗略过滤明显不合理沸点。
    """
    if value_K is None or not np.isfinite(value_K):
        return False

    return 50.0 <= value_K <= 1000.0


# =========================================================
# 5. PubChem CID 查询
# =========================================================
def get_cid_by_namespace(namespace, query_value):
    """
    namespace 可为：
    name
    inchikey
    smiles
    """
    if not is_valid_value(query_value):
        return None, "empty_query"

    q = quote(str(query_value).strip())
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/{namespace}/{q}/cids/JSON"

    data, status = request_json(url)

    if status != "ok" or data is None:
        return None, status

    try:
        cids = data.get("IdentifierList", {}).get("CID", [])
        if len(cids) > 0:
            return int(cids[0]), "ok"
    except Exception as e:
        return None, f"parse_error: {e}"

    return None, "no_cid"


def get_pubchem_cid_for_material(row):
    """
    查询优先级：
    1. 已有 pubchem_cid
    2. inchikey
    3. cas
    4. compound_name
    5. SMILES / final_smiles / smiles
    """
    if "pubchem_cid" in row.index and is_valid_value(row["pubchem_cid"]):
        try:
            return int(float(row["pubchem_cid"])), "existing_pubchem_cid", "existing"
        except Exception:
            pass

    if "inchikey" in row.index and is_valid_value(row["inchikey"]):
        cid, status = get_cid_by_namespace("inchikey", row["inchikey"])
        if cid is not None:
            return cid, "inchikey", row["inchikey"]

    if "cas" in row.index and is_valid_value(row["cas"]):
        cid, status = get_cid_by_namespace("name", row["cas"])
        if cid is not None:
            return cid, "cas", row["cas"]

    if "compound_name" in row.index and is_valid_value(row["compound_name"]):
        cid, status = get_cid_by_namespace("name", row["compound_name"])
        if cid is not None:
            return cid, "compound_name", row["compound_name"]

    for smiles_col in ["SMILES", "final_smiles", "smiles"]:
        if smiles_col in row.index and is_valid_value(row[smiles_col]):
            cid, status = get_cid_by_namespace("smiles", row[smiles_col])
            if cid is not None:
                return cid, smiles_col, row[smiles_col]

    return None, "failed", None


# =========================================================
# 6. 从 PubChem PUG-View 读取沸点 Tb
# =========================================================
def get_pug_view_json_by_heading(cid, heading):
    h = quote(heading)
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON?heading={h}"

    data, status = request_json(url)

    return data, status


def extract_boiling_temperature_from_pubchem(cid):
    """
    从 PubChem PUG-View 中提取 Boiling Point。
    返回：
    boiling_T_K
    boiling_T_count
    boiling_T_min_K
    boiling_T_max_K
    boiling_T_raw_examples
    """
    headings = ["Boiling Point"]

    raw_rows = []

    for heading in headings:
        record_json, status = get_pug_view_json_by_heading(cid, heading)

        if status != "ok" or record_json is None:
            time.sleep(SLEEP_SECONDS)
            continue

        section_rows = collect_section_texts(record_json)

        for sec_row in section_rows:
            combined_text = " | ".join([
                str(sec_row.get("toc_heading", "")),
                str(sec_row.get("info_name", "")),
                str(sec_row.get("info_description", "")),
                str(sec_row.get("value_text", "")),
            ])

            combined_lower = combined_text.lower()

            if "boiling" not in combined_lower:
                continue

            temp_values = parse_temperature_values_from_text(sec_row.get("value_text", ""))

            for item in temp_values:
                value_K = item["value_K"]

                if not plausible_boiling_temperature(value_K):
                    continue

                raw_rows.append({
                    "cid": cid,
                    "prop_type": "boiling",
                    "heading_requested": heading,
                    "toc_heading": sec_row.get("toc_heading"),
                    "info_name": sec_row.get("info_name"),
                    "value_K": value_K,
                    "unit_detected": item["unit_detected"],
                    "matched_text": item["matched_text"],
                    "is_range": item["is_range"],
                    "raw_text": sec_row.get("value_text"),
                })

        time.sleep(SLEEP_SECONDS)

    if len(raw_rows) == 0:
        return {
            "boiling_T_K": None,
            "boiling_T_count": 0,
            "boiling_T_min_K": None,
            "boiling_T_max_K": None,
            "boiling_T_raw_examples": None,
        }, raw_rows

    values = [r["value_K"] for r in raw_rows]

    summary = {
        "boiling_T_K": float(np.median(values)),
        "boiling_T_count": len(values),
        "boiling_T_min_K": float(np.min(values)),
        "boiling_T_max_K": float(np.max(values)),
        "boiling_T_raw_examples": " ; ".join(
            [str(r["matched_text"]) for r in raw_rows[:5]]
        ),
    }

    return summary, raw_rows


# =========================================================
# 7. material_key
# =========================================================
def build_material_key(row):
    for col in ["material_key", "inchikey", "cas", "compound_name", "formula"]:
        if col in row.index and is_valid_value(row[col]):
            if col == "material_key":
                return str(row[col]).strip()
            return f"{col}:{str(row[col]).strip()}"

    return "unknown_material"


# =========================================================
# 8. 主程序
# =========================================================
def main():
    # ---------- 读取 vapor pressure 数据 ----------
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

    df_data = pd.read_excel(input_file, sheet_name=input_sheet)

    print("Vapor pressure 数据行数:", len(df_data))

    if "material_key" not in df_data.columns:
        df_data["material_key"] = df_data.apply(build_material_key, axis=1)

    # ---------- 从数据行中提取唯一物质 ----------
    material_cols = [
        "material_key",
        "compound_name",
        "cas",
        "formula",
        "inchikey",
        "inchi",
        "smiles",
        "SMILES",
        "final_smiles",
        "pubchem_cid",
        "pubchem_molecular_formula",
        "pubchem_iupac_name",
    ]

    material_cols = [c for c in material_cols if c in df_data.columns]

    df_material = (
        df_data[material_cols]
        .drop_duplicates(subset=["material_key"])
        .reset_index(drop=True)
    )

    print("唯一物质数:", len(df_material))

    result_rows = []
    all_raw_rows = []

    # ---------- 逐物质查询 Tb ----------
    for i, row in df_material.iterrows():
        if (i + 1) % 10 == 0 or (i + 1) == len(df_material):
            print(f"已处理 {i + 1}/{len(df_material)} 个物质")

        material_key = row.get("material_key")
        compound_name = row.get("compound_name", None)
        cas = row.get("cas", None)
        formula = row.get("formula", None)

        cid, query_used, query_value = get_pubchem_cid_for_material(row)

        base = row.to_dict()
        base["pubchem_cid_for_Tb"] = cid
        base["pubchem_query_used_for_Tb"] = query_used
        base["pubchem_query_value_for_Tb"] = query_value

        if cid is None:
            base["boiling_T_K"] = None
            base["boiling_T_count"] = 0
            base["boiling_T_min_K"] = None
            base["boiling_T_max_K"] = None
            base["boiling_T_raw_examples"] = None
            base["Tb_status"] = "cid_not_found"

            result_rows.append(base)
            continue

        boiling_summary, boiling_raw = extract_boiling_temperature_from_pubchem(cid)

        base.update({
            "boiling_T_K": boiling_summary["boiling_T_K"],
            "boiling_T_count": boiling_summary["boiling_T_count"],
            "boiling_T_min_K": boiling_summary["boiling_T_min_K"],
            "boiling_T_max_K": boiling_summary["boiling_T_max_K"],
            "boiling_T_raw_examples": boiling_summary["boiling_T_raw_examples"],
        })

        if boiling_summary["boiling_T_count"] > 0:
            base["Tb_status"] = "ok"
        else:
            base["Tb_status"] = "not_found_in_pug_view"

        for r in boiling_raw:
            r["material_key"] = material_key
            r["compound_name"] = compound_name
            r["cas"] = cas
            r["formula"] = formula
            all_raw_rows.append(r)

        result_rows.append(base)

        time.sleep(SLEEP_SECONDS)

    df_material_out = pd.DataFrame(result_rows)
    df_raw = pd.DataFrame(all_raw_rows)

    # ---------- 合并回 vapor pressure 数据 ----------
    merge_cols = [
        "material_key",
        "pubchem_cid_for_Tb",
        "pubchem_query_used_for_Tb",
        "pubchem_query_value_for_Tb",
        "boiling_T_K",
        "boiling_T_count",
        "boiling_T_min_K",
        "boiling_T_max_K",
        "boiling_T_raw_examples",
        "Tb_status",
    ]

    merge_cols = [c for c in merge_cols if c in df_material_out.columns]

    old_cols = [
        c for c in merge_cols
        if c != "material_key" and c in df_data.columns
    ]

    df_data_base = df_data.drop(columns=old_cols)

    df_data_out = df_data_base.merge(
        df_material_out[merge_cols],
        on="material_key",
        how="left"
    )

    # ---------- 统计 ----------
    failed = df_material_out[df_material_out["Tb_status"] != "ok"].copy()

    summary = pd.DataFrame([
        {"item": "input_file", "value": str(input_file)},
        {"item": "input_sheet", "value": input_sheet},
        {"item": "output_file", "value": str(output_file)},
        {"item": "data_rows", "value": len(df_data)},
        {"item": "unique_materials", "value": len(df_material_out)},
        {"item": "Tb_ok_materials", "value": int((df_material_out["Tb_status"] == "ok").sum())},
        {"item": "failed_or_not_found_materials", "value": len(failed)},
        {"item": "materials_with_boiling_T", "value": int(df_material_out["boiling_T_K"].notna().sum())},
    ])

    # ---------- 保存 ----------
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df_data_out.to_excel(writer, sheet_name="Data_with_Tb", index=False)
        df_material_out.to_excel(writer, sheet_name="Material_with_Tb", index=False)

        if len(df_raw) > 0:
            df_raw.to_excel(writer, sheet_name="PubChem_Raw_Tb_Values", index=False)
        else:
            pd.DataFrame({"message": ["No raw Tb values extracted"]}).to_excel(
                writer,
                sheet_name="PubChem_Raw_Tb_Values",
                index=False
            )

        failed.to_excel(writer, sheet_name="Failed_or_NotFound", index=False)
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

    print("\n查询结果统计:")
    print(df_material_out["Tb_status"].value_counts(dropna=False))

    print("\n沸点覆盖情况:")
    print("有沸点的物质数:", df_material_out["boiling_T_K"].notna().sum())
    print("总物质数:", len(df_material_out))


if __name__ == "__main__":
    main()