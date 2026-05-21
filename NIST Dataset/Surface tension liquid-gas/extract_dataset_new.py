# -*- coding: utf-8 -*-
"""
从 NIST ThermoML XML 数据中提取纯化合物液态 Surface tension liquid-gas 数据。

目标性质：
    Surface tension liquid-gas, N/m

主要输出：
    1. thermoml_surface_tension_liquid_gas_all.xlsx
       - 提取到的全部 Surface tension liquid-gas 数据

    2. thermoml_surface_tension_liquid_gas_pure_organic_liquid.xlsx
       - 经过纯有机单组分 + 液态/液-气界面 + 可换算单位筛选后的数据

    3. thermoml_surface_tension_liquid_gas_by_phase.xlsx
       - 按 phase 分 sheet 保存的 Surface tension 数据

依赖：
    pip install pandas openpyxl numpy
"""

import xml.etree.ElementTree as ET
from pathlib import Path
import pandas as pd
import re
import numpy as np


# =========================
# 1. 路径与筛选配置
# =========================

ROOT_DIR = Path(r"D:\PyProjects\extend\real data\NIST\ThermoML.v2020-09-30")

# 如果只想扫描这三个 DOI 前缀文件夹，保持如下设置。
# 如果想扫描 ROOT_DIR 下全部 XML，把 TARGET_SUBFOLDERS 改成 None。
TARGET_SUBFOLDERS = [
    "10.1021",
    "10.1016",
    "10.1007",
]

# 是否只保留单组分数据
ONLY_SINGLE_COMPONENT = True

# 是否只保留纯有机化合物
ONLY_PURE_ORGANIC = True

# 是否只保留液态 / 液-气界面相关数据
ONLY_LIQUID_PHASE = True

# 对 Surface tension liquid-gas 而言，属性名本身已经说明是液-气界面。
# 因此如果 phase 缺失，可以保留。
# 如果你想更严格，只保留 phase 明确含 Liquid 的数据，把它改成 False。
KEEP_UNKNOWN_PHASE_IN_LIQUID_FILTER = True

# SMILES 缺失时填什么
SMILES_MISSING_VALUE = "待定"

# 目标性质名称
TARGET_PROPERTY_NAMES = {
    "Surface tension liquid-gas, N/m",
}

# 输出文件
OUT_ALL = "thermoml_surface_tension_liquid_gas_all.xlsx"
OUT_FILTERED = "thermoml_surface_tension_liquid_gas_pure_organic_liquid.xlsx"
OUT_BY_PHASE = "thermoml_surface_tension_liquid_gas_by_phase.xlsx"


# =========================
# 2. XML 工具函数
# =========================

def strip_ns(tag):
    return tag.split("}", 1)[-1] if "}" in tag else tag


def children(elem, name=None):
    if elem is None:
        return []

    out = []
    for c in list(elem):
        if name is None or strip_ns(c.tag) == name:
            out.append(c)

    return out


def first_child(elem, name):
    cs = children(elem, name)
    return cs[0] if cs else None


def text(elem):
    if elem is None or elem.text is None:
        return None

    s = elem.text.strip()
    return s if s else None


def first_text(elem, tag_name):
    if elem is None:
        return None

    for x in elem.iter():
        if strip_ns(x.tag) == tag_name:
            return text(x)

    return None


def all_texts(elem, tag_name):
    vals = []

    if elem is None:
        return vals

    for x in elem.iter():
        if strip_ns(x.tag) == tag_name:
            v = text(x)
            if v is not None:
                vals.append(v)

    return vals


def to_float(x):
    if x is None:
        return None

    try:
        return float(str(x).replace(",", "").strip())
    except Exception:
        return None


def cas_digits_to_hyphen(cas_digits):
    if cas_digits is None:
        return None

    s = re.sub(r"\D", "", str(cas_digits))

    if len(s) < 3:
        return s

    return f"{s[:-3]}-{s[-3:-1]}-{s[-1]}"


def get_regnum(elem):
    """
    提取 RegNum 中的 CAS 和 nOrgNum。
    """

    if elem is None:
        return {}

    reg = first_child(elem, "RegNum")

    if reg is None:
        for x in elem.iter():
            if strip_ns(x.tag) == "RegNum":
                reg = x
                break

    if reg is None:
        return {}

    cas_raw = first_text(reg, "nCASRNum")
    org_num = first_text(reg, "nOrgNum")

    return {
        "cas_raw": cas_raw,
        "cas": cas_digits_to_hyphen(cas_raw),
        "org_num": org_num,
    }


def get_original_smiles(comp_elem):
    smiles_list = all_texts(comp_elem, "sSmiles")

    if smiles_list:
        return "; ".join(smiles_list)

    return SMILES_MISSING_VALUE


def extract_unit_from_property_name(prop_name):
    """
    从属性名中提取单位。

    例如：
        Surface tension liquid-gas, N/m -> N/m
    """

    if not prop_name:
        return None

    s = str(prop_name).strip()

    if "," in s:
        unit = s.split(",", 1)[1].strip()
        unit = unit.split(";")[0].strip()
        return unit

    return None


# =========================
# 3. Surface tension 判断与单位换算
# =========================

def normalize_unit_string(unit):
    if unit is None:
        return ""

    u = str(unit).strip().lower()
    u = u.replace(" ", "")
    u = u.replace("−", "-")
    u = u.replace("–", "-")
    u = u.replace("·", ".")
    u = u.replace("*", ".")
    u = u.replace("^", "")
    u = u.replace("(", "")
    u = u.replace(")", "")
    u = u.replace("[", "")
    u = u.replace("]", "")
    u = u.replace("μ", "u")

    return u


def is_surface_tension_unit(unit):
    """
    判断是否是常见表面张力单位。

    ThermoML 中目标性质通常是 N/m。
    这里额外兼容：
        mN/m
        dyn/cm
        dyne/cm
        erg/cm2
        J/m2
        mJ/m2

    换算关系：
        1 mN/m = 0.001 N/m
        1 dyn/cm = 0.001 N/m
        1 erg/cm2 = 0.001 N/m
        1 J/m2 = 1 N/m
    """

    u = normalize_unit_string(unit)

    surface_units = {
        "n/m",
        "nm-1",
        "n.m-1",
        "newton/meter",
        "newton/metre",
        "newtonpermeter",
        "newtonpermetre",

        "mn/m",
        "mnm-1",
        "mn.m-1",
        "millinewton/meter",
        "millinewton/metre",
        "millinewtonpermeter",
        "millinewtonpermetre",

        "dyn/cm",
        "dyne/cm",
        "dynes/cm",
        "dyncm-1",
        "dynecm-1",

        "erg/cm2",
        "ergcm-2",
        "erg/cm^2",

        "j/m2",
        "jm-2",
        "j/m^2",
        "mj/m2",
        "mjm-2",
        "mj/m^2",
    }

    return u in surface_units


def is_surface_tension_property(prop_name, unit=None):
    """
    识别 Surface tension liquid-gas 属性。

    主要匹配：
        Surface tension liquid-gas, N/m

    也允许轻微写法差异：
        - 属性名中包含 surface tension
        - 且包含 liquid-gas / liquid gas / liquid-gas interface
    """

    if not prop_name:
        return False

    s = str(prop_name).strip()
    s_low = s.lower()

    if s in TARGET_PROPERTY_NAMES:
        pass
    elif (
        "surface tension" in s_low
        and (
            "liquid-gas" in s_low
            or "liquid gas" in s_low
            or "liquid-gas interface" in s_low
            or "liquid-vapor" in s_low
            or "liquid vapour" in s_low
            or "liquid-vapour" in s_low
            or "liquid vapor" in s_low
        )
    ):
        pass
    else:
        return False

    if unit is not None and str(unit).strip() != "":
        return is_surface_tension_unit(unit)

    return True


def convert_surface_tension_to_N_m(value, unit):
    """
    将表面张力转换为 N/m。

    返回：
        SurfaceTension_N_m
    """

    if value is None or not pd.notna(value):
        return np.nan

    try:
        v = float(value)
    except Exception:
        return np.nan

    u = normalize_unit_string(unit)

    # N/m
    if u in {
        "n/m",
        "nm-1",
        "n.m-1",
        "newton/meter",
        "newton/metre",
        "newtonpermeter",
        "newtonpermetre",
        "j/m2",
        "jm-2",
        "j/m^2",
    }:
        return v

    # mN/m = 0.001 N/m
    if u in {
        "mn/m",
        "mnm-1",
        "mn.m-1",
        "millinewton/meter",
        "millinewton/metre",
        "millinewtonpermeter",
        "millinewtonpermetre",
        "mj/m2",
        "mjm-2",
        "mj/m^2",
    }:
        return v * 0.001

    # dyn/cm = 0.001 N/m
    if u in {
        "dyn/cm",
        "dyne/cm",
        "dynes/cm",
        "dyncm-1",
        "dynecm-1",
        "erg/cm2",
        "ergcm-2",
        "erg/cm^2",
    }:
        return v * 0.001

    return np.nan


def get_phase_from_property(prop_elem):
    if prop_elem is None:
        return None

    phase = first_text(prop_elem, "ePropPhase")
    if phase is not None:
        return phase

    phase = first_text(prop_elem, "ePhase")
    return phase


def get_method_from_property(prop_elem):
    if prop_elem is None:
        return None

    method = first_text(prop_elem, "eMethodName")
    if method is not None:
        return method

    method = first_text(prop_elem, "sMethodName")
    return method


def get_property_name(prop_elem):
    return first_text(prop_elem, "ePropName")


def get_variable_name(var_elem):
    if var_elem is None:
        return None

    priority_tags = [
        "eTemperature",
        "ePressure",
        "eComponentComposition",
        "eSolventComposition",
        "eMiscVariable",
        "eTime",
    ]

    for tag in priority_tags:
        v = first_text(var_elem, tag)
        if v is not None:
            return v

    var_type = first_child(first_child(var_elem, "VariableID"), "VariableType")
    if var_type is not None:
        for x in var_type.iter():
            v = text(x)
            if v is not None:
                return v

    return None


def get_constraint_name(cons_elem):
    if cons_elem is None:
        return None

    priority_tags = [
        "eTemperature",
        "ePressure",
        "eComponentComposition",
        "eSolventComposition",
        "eMiscConstraint",
    ]

    for tag in priority_tags:
        v = first_text(cons_elem, tag)
        if v is not None:
            return v

    return None


# =========================
# 4. 纯有机化合物筛选函数
# =========================

def parse_elements(formula):
    if pd.isna(formula):
        return set()

    formula = str(formula).strip()

    if formula == "":
        return set()

    formula = formula.replace(" ", "")
    formula = formula.replace("·", ".")
    formula = formula.replace("-", "")

    elements = re.findall(r"[A-Z][a-z]?", formula)
    return set(elements)


allowed_organic_elements = {
    "C", "H", "O", "N", "S", "P",
    "F", "Cl", "Br", "I",
    "B", "Si",
}

excluded_elements = {
    "Li", "Na", "K", "Rb", "Cs",
    "Be", "Mg", "Ca", "Sr", "Ba",
    "Al", "Ga", "In", "Tl",
    "Sn", "Pb",
    "Ti", "Zr", "Hf",
    "V", "Nb", "Ta",
    "Cr", "Mo", "W",
    "Mn", "Re",
    "Fe", "Co", "Ni", "Cu", "Zn",
    "Ag", "Cd", "Hg",
    "Pt", "Pd", "Au",
    "As", "Sb", "Bi",
    "Se", "Te",
    "La", "Ce", "Nd", "U",
}


def organic_filter_reason(row):
    try:
        n_comp = int(row.get("n_components"))
    except Exception:
        return "invalid_n_components"

    if n_comp != 1:
        return "not_single_component"

    formula = row.get("formula", None)
    elements = parse_elements(formula)

    if not elements:
        return "missing_formula"

    if "C" not in elements:
        return "no_carbon"

    excluded = elements & excluded_elements
    if excluded:
        return "contains_excluded_element_" + "_".join(sorted(excluded))

    unallowed = elements - allowed_organic_elements
    if unallowed:
        return "contains_unallowed_element_" + "_".join(sorted(unallowed))

    return "kept"


def is_liquid_phase_value(phase):
    """
    判断 phase 是否适合 Surface tension liquid-gas。

    对 surface tension liquid-gas：
    - phase 明确包含 Liquid：保留
    - phase 缺失：按配置决定，默认保留，因为性质名已经说明 liquid-gas
    """

    if phase is None or pd.isna(phase):
        return KEEP_UNKNOWN_PHASE_IN_LIQUID_FILTER

    s = str(phase).strip().lower()

    if s == "":
        return KEEP_UNKNOWN_PHASE_IN_LIQUID_FILTER

    if "liquid" in s:
        return True

    if "liquid-gas" in s or "liquid gas" in s:
        return True

    if "liquid-vapor" in s or "liquid vapor" in s:
        return True

    if "liquid-vapour" in s or "liquid vapour" in s:
        return True

    return False


# =========================
# 5. Excel sheet 工具函数
# =========================

def safe_sheet_name(name):
    if pd.isna(name) or str(name).strip() == "":
        name = "Unknown"

    name = str(name).strip()
    name = re.sub(r"[\[\]\:\*\?\/\\]", "_", name)
    name = name[:31]

    return name if name else "Unknown"


def make_unique_sheet_name(base_name, used_names):
    base_name = safe_sheet_name(base_name)

    if base_name not in used_names:
        used_names.add(base_name)
        return base_name

    for i in range(1, 1000):
        suffix = f"_{i}"
        candidate = base_name[:31 - len(suffix)] + suffix

        if candidate not in used_names:
            used_names.add(candidate)
            return candidate

    raise ValueError("sheet 名重复过多，无法自动命名。")


def save_by_phase_excel(df, output_file):
    if "phase" not in df.columns:
        raise ValueError("表中没有 phase 列，无法按相态划分。")

    df = df.copy()
    df["phase_clean"] = df["phase"].fillna("Unknown").astype(str).str.strip()
    df.loc[df["phase_clean"] == "", "phase_clean"] = "Unknown"

    used_sheet_names = set()

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        all_sheet = make_unique_sheet_name("All", used_sheet_names)
        df.to_excel(writer, sheet_name=all_sheet, index=False)

        for phase, group in df.groupby("phase_clean"):
            sheet_name = make_unique_sheet_name(phase, used_sheet_names)
            group.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"已保存按相态划分的文件: {output_file}")
    print("\n各 phase 数据量：")
    print(df["phase_clean"].value_counts())


# =========================
# 6. XML 文件扫描函数
# =========================

def find_xml_files():
    """
    根据 TARGET_SUBFOLDERS 扫描 XML 文件。
    """

    if TARGET_SUBFOLDERS is None:
        xml_files = sorted(ROOT_DIR.rglob("*.xml"))
        return xml_files

    xml_files = []

    for folder in TARGET_SUBFOLDERS:
        folder_path = ROOT_DIR / folder

        if not folder_path.exists():
            print(f"[警告] 文件夹不存在: {folder_path}")
            continue

        xml_files.extend(sorted(folder_path.rglob("*.xml")))

    return xml_files


# =========================
# 7. 提取单个 XML 文件
# =========================

def parse_one_xml(xml_path):
    rows = []

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        print(f"[解析失败] {xml_path}: {e}")
        return rows

    # ---------- citation ----------
    citation = first_child(root, "Citation")
    title = first_text(citation, "sTitle")
    doi = first_text(citation, "sDOI")
    year = first_text(citation, "yrPubYr")
    journal = first_text(citation, "sPubName")

    # ---------- compounds ----------
    compound_map_by_cas = {}
    compound_map_by_org = {}

    for comp in children(root, "Compound"):
        reg = get_regnum(comp)

        common_names = all_texts(comp, "sCommonName")
        name = common_names[0] if common_names else None

        formula = first_text(comp, "sFormulaMolec")
        inchikey = first_text(comp, "sStandardInChIKey")
        inchi = first_text(comp, "sStandardInChI")
        smiles = get_original_smiles(comp)

        info = {
            "name": name,
            "formula": formula,
            "cas": reg.get("cas"),
            "cas_raw": reg.get("cas_raw"),
            "org_num": reg.get("org_num"),
            "smiles": smiles,
            "inchikey": inchikey,
            "inchi": inchi,
        }

        if reg.get("cas_raw") is not None:
            compound_map_by_cas[str(reg["cas_raw"])] = info

        if reg.get("org_num") is not None:
            compound_map_by_org[str(reg["org_num"])] = info

    # ---------- PureOrMixtureData ----------
    datasets = children(root, "PureOrMixtureData")

    for dataset_index, ds in enumerate(datasets, start=1):

        # 组件列表
        components = []

        for c in children(ds, "Component"):
            reg = get_regnum(c)

            info = None

            if reg.get("cas_raw") is not None:
                info = compound_map_by_cas.get(str(reg["cas_raw"]))

            if info is None and reg.get("org_num") is not None:
                info = compound_map_by_org.get(str(reg["org_num"]))

            if info is None:
                info = {
                    "name": None,
                    "formula": None,
                    "cas": reg.get("cas"),
                    "cas_raw": reg.get("cas_raw"),
                    "org_num": reg.get("org_num"),
                    "smiles": SMILES_MISSING_VALUE,
                    "inchikey": None,
                    "inchi": None,
                }

            components.append(info)

        component_names = " + ".join([c.get("name") or "" for c in components])
        component_cas = " + ".join([c.get("cas") or "" for c in components])
        component_formulas = " + ".join([c.get("formula") or "" for c in components])
        component_smiles = " + ".join([c.get("smiles") or SMILES_MISSING_VALUE for c in components])

        # ---------- 属性定义：nPropNumber -> 信息 ----------
        prop_defs = {}

        for prop in children(ds, "Property"):
            n_prop = first_text(prop, "nPropNumber")
            prop_name = get_property_name(prop)
            prop_unit = extract_unit_from_property_name(prop_name)

            if n_prop is None:
                continue

            prop_defs[str(n_prop)] = {
                "property_name": prop_name,
                "property_unit": prop_unit,
                "phase": get_phase_from_property(prop),
                "method": get_method_from_property(prop),
                "is_surface_tension": is_surface_tension_property(prop_name, prop_unit),
            }

        surface_prop_numbers = [
            k for k, v in prop_defs.items()
            if v["is_surface_tension"]
        ]

        if not surface_prop_numbers:
            continue

        # ---------- 变量定义：nVarNumber -> 信息 ----------
        var_defs = {}

        for var in children(ds, "Variable"):
            n_var = first_text(var, "nVarNumber")
            var_name = get_variable_name(var)
            reg = get_regnum(var)

            if n_var is None:
                continue

            var_defs[str(n_var)] = {
                "variable_name": var_name,
                "var_phase": first_text(var, "eVarPhase"),
                "cas": reg.get("cas"),
                "cas_raw": reg.get("cas_raw"),
                "org_num": reg.get("org_num"),
            }

        # ---------- 约束定义：nConstraintNumber -> 信息 ----------
        cons_defs = {}

        for cons in children(ds, "Constraint"):
            n_cons = first_text(cons, "nConstraintNumber")
            cons_name = get_constraint_name(cons)
            reg = get_regnum(cons)

            if n_cons is None:
                continue

            cons_defs[str(n_cons)] = {
                "constraint_name": cons_name,
                "cons_phase": first_text(cons, "eConstraintPhase"),
                "cas": reg.get("cas"),
                "cas_raw": reg.get("cas_raw"),
                "org_num": reg.get("org_num"),
            }

        # ---------- 数值点 ----------
        for nv in children(ds, "NumValues"):

            base = {
                "source_file": str(xml_path),
                "doi": doi,
                "title": title,
                "year": year,
                "journal": journal,
                "dataset_index": dataset_index,
                "n_components": len(components),
                "components": component_names,
                "component_cas": component_cas,
                "component_formulas": component_formulas,
                "component_smiles": component_smiles,
            }

            # 单组分时额外给出便于建模的字段
            if len(components) == 1:
                base["compound_name"] = components[0].get("name")
                base["formula"] = components[0].get("formula")
                base["cas"] = components[0].get("cas")
                base["smiles"] = components[0].get("smiles") or SMILES_MISSING_VALUE
                base["inchikey"] = components[0].get("inchikey")
                base["inchi"] = components[0].get("inchi")
            else:
                base["compound_name"] = None
                base["formula"] = None
                base["cas"] = None
                base["smiles"] = SMILES_MISSING_VALUE
                base["inchikey"] = None
                base["inchi"] = None

            # 变量值，例如温度、压力、组成
            for vv in children(nv, "VariableValue"):
                n_var = first_text(vv, "nVarNumber")
                val = to_float(first_text(vv, "nVarValue"))
                uncert = to_float(first_text(vv, "nExpandUncertValue"))

                vdef = var_defs.get(str(n_var), {})
                vname = vdef.get("variable_name") or f"Variable_{n_var}"

                base[vname] = val
                base[f"{vname}_uncertainty"] = uncert

                low = vname.lower()

                if "temperature" in low:
                    base["T_K"] = val
                    base["T_uncertainty"] = uncert

                elif "pressure" in low:
                    base["P_kPa"] = val
                    base["P_uncertainty"] = uncert

                elif "mole fraction" in low:
                    cas_or_org = vdef.get("cas") or vdef.get("org_num") or "unknown"
                    base[f"x_{cas_or_org}"] = val

                elif "mass fraction" in low:
                    cas_or_org = vdef.get("cas") or vdef.get("org_num") or "unknown"
                    base[f"w_{cas_or_org}"] = val

                elif "molality" in low:
                    cas_or_org = vdef.get("cas") or vdef.get("org_num") or "unknown"
                    base[f"molality_{cas_or_org}"] = val

            # 约束值，例如固定温度、固定压力
            for cv in children(nv, "ConstraintValue"):
                n_cons = first_text(cv, "nConstraintNumber")
                val = to_float(first_text(cv, "nConstraintValue"))
                uncert = to_float(first_text(cv, "nExpandUncertValue"))

                cdef = cons_defs.get(str(n_cons), {})
                cname = cdef.get("constraint_name") or f"Constraint_{n_cons}"

                low = cname.lower()

                if "temperature" in low and "T_K" not in base:
                    base["T_K"] = val
                    base["T_uncertainty"] = uncert

                elif "pressure" in low and "P_kPa" not in base:
                    base["P_kPa"] = val
                    base["P_uncertainty"] = uncert

                elif "mole fraction" in low:
                    cas_or_org = cdef.get("cas") or cdef.get("org_num") or "unknown"
                    base[f"x_{cas_or_org}"] = val

                elif "mass fraction" in low:
                    cas_or_org = cdef.get("cas") or cdef.get("org_num") or "unknown"
                    base[f"w_{cas_or_org}"] = val

                elif "molality" in low:
                    cas_or_org = cdef.get("cas") or cdef.get("org_num") or "unknown"
                    base[f"molality_{cas_or_org}"] = val

                else:
                    base[cname] = val
                    base[f"{cname}_uncertainty"] = uncert

            # 属性值，可能一个 NumValues 中有多个 PropertyValue
            for pv in children(nv, "PropertyValue"):
                n_prop = first_text(pv, "nPropNumber")
                prop_info = prop_defs.get(str(n_prop))

                if prop_info is None:
                    continue

                if not prop_info["is_surface_tension"]:
                    continue

                row = dict(base)

                prop_value = to_float(first_text(pv, "nPropValue"))
                prop_uncert = to_float(first_text(pv, "nExpandUncertValue"))

                surface_tension_N_m = convert_surface_tension_to_N_m(
                    prop_value,
                    prop_info["property_unit"],
                )

                row["property_name"] = prop_info["property_name"]
                row["property_unit"] = prop_info["property_unit"]
                row["phase"] = prop_info["phase"]
                row["method"] = prop_info["method"]

                row["property_value"] = prop_value
                row["property_uncertainty"] = prop_uncert

                row["is_surface_tension"] = prop_info["is_surface_tension"]
                row["SurfaceTension_N_m"] = surface_tension_N_m

                rows.append(row)

    return rows


# =========================
# 8. 主程序
# =========================

def main():
    xml_files = find_xml_files()

    print(f"找到 XML 文件数量: {len(xml_files)}")

    all_rows = []

    for i, xml_path in enumerate(xml_files, start=1):
        if i % 500 == 0 or i == 1 or i == len(xml_files):
            print(f"已处理 {i}/{len(xml_files)} 个 XML 文件")

        rows = parse_one_xml(xml_path)
        all_rows.extend(rows)

    print(f"\n提取到 Surface tension liquid-gas 类数据点数量: {len(all_rows)}")

    if not all_rows:
        print("没有提取到数据。请检查 ROOT_DIR、TARGET_SUBFOLDERS 或 Surface tension 属性名匹配规则。")
        return

    df_all = pd.DataFrame(all_rows)

    # 确保 smiles 列存在，并把空值填成“待定”
    if "smiles" not in df_all.columns:
        df_all["smiles"] = SMILES_MISSING_VALUE

    df_all["smiles"] = df_all["smiles"].fillna(SMILES_MISSING_VALUE)
    df_all.loc[df_all["smiles"].astype(str).str.strip() == "", "smiles"] = SMILES_MISSING_VALUE

    if "component_smiles" not in df_all.columns:
        df_all["component_smiles"] = SMILES_MISSING_VALUE

    df_all["component_smiles"] = df_all["component_smiles"].fillna(SMILES_MISSING_VALUE)
    df_all.loc[df_all["component_smiles"].astype(str).str.strip() == "", "component_smiles"] = SMILES_MISSING_VALUE

    # 保存全部 Surface tension 数据
    df_all.to_excel(OUT_ALL, index=False)
    print(f"\n已保存全部 Surface tension liquid-gas 数据: {OUT_ALL}")
    print(f"全部 Surface tension liquid-gas 数据点数量: {len(df_all)}")

    # 按 phase 分 sheet 保存，便于检查相态
    save_by_phase_excel(df_all, OUT_BY_PHASE)

    # =========================
    # 过滤：纯化合物 / 纯有机 / 液态或液-气界面 / 单位可换算 / 有温度
    # =========================

    df = df_all.copy()

    if ONLY_SINGLE_COMPONENT:
        before = len(df)
        df = df[df["n_components"] == 1].copy()
        print(f"\n只保留单组分后数据点数量: {len(df)}，排除: {before - len(df)}")

    if ONLY_PURE_ORGANIC:
        df["elements"] = df["formula"].apply(lambda x: ",".join(sorted(parse_elements(x))))
        df["organic_filter_reason"] = df.apply(organic_filter_reason, axis=1)

        df_rejected = df[df["organic_filter_reason"] != "kept"].copy()
        df = df[df["organic_filter_reason"] == "kept"].copy()

        print(f"\n只保留纯有机化合物后数据点数量: {len(df)}")
        print("被排除数据点数量:", len(df_rejected))

        if len(df_rejected) > 0:
            print("\n排除原因统计：")
            print(df_rejected["organic_filter_reason"].value_counts())

    if ONLY_LIQUID_PHASE:
        before = len(df)
        df["is_liquid_phase"] = df["phase"].apply(is_liquid_phase_value)
        df = df[df["is_liquid_phase"] == True].copy()
        print(f"\n只保留液态或液-气界面 phase 后数据点数量: {len(df)}，排除: {before - len(df)}")

    before = len(df)
    df = df[df["SurfaceTension_N_m"].notna()].copy()
    print(f"\n只保留可换算为 N/m 的数据后数据点数量: {len(df)}，排除: {before - len(df)}")

    before = len(df)
    df = df[df["T_K"].notna()].copy()
    print(f"\n只保留存在温度 T_K 的数据后数据点数量: {len(df)}，排除: {before - len(df)}")

    # 删除非正表面张力
    before = len(df)
    df = df[df["SurfaceTension_N_m"] > 0].copy()
    print(f"\n删除 SurfaceTension_N_m <= 0 的数据点数量: {before - len(df)}")

    # 排序，方便检查
    sort_cols = [
        c for c in [
            "cas",
            "compound_name",
            "T_K",
            "SurfaceTension_N_m",
            "property_name",
        ]
        if c in df.columns
    ]

    if sort_cols:
        df = df.sort_values(sort_cols, na_position="last")

    # 保存筛选后的数据
    df.to_excel(OUT_FILTERED, index=False)
    print(f"\n已保存筛选后的纯有机单组分 Surface tension liquid-gas 数据: {OUT_FILTERED}")
    print(f"筛选后数据点数量: {len(df)}")

    # =========================
    # 简单统计
    # =========================

    print("\n属性名统计：")
    print(df_all["property_name"].value_counts().head(50))

    print("\nSurface tension 单位统计：")
    print(df_all["property_unit"].fillna("Unknown").value_counts().head(30))

    if "phase" in df_all.columns:
        print("\n全部 Surface tension 相态统计：")
        print(df_all["phase"].fillna("Unknown").value_counts())

    if "phase" in df.columns:
        print("\n筛选后 Surface tension 相态统计：")
        print(df["phase"].fillna("Unknown").value_counts())

    smiles_valid = (
        df["smiles"].notna()
        & (df["smiles"].astype(str).str.strip() != SMILES_MISSING_VALUE)
    )

    print("\nSMILES 统计：")
    print("筛选后数据点总数:", len(df))
    print("有 XML 原始 SMILES 的数据点数:", int(smiles_valid.sum()))
    print("没有 XML 原始 SMILES 的数据点数:", int(len(df) - smiles_valid.sum()))

    if "cas" in df.columns:
        print("\n物质数量统计：")
        print("CAS 数:", df["cas"].nunique())
        print("compound_name 数:", df["compound_name"].nunique())
        print("InChIKey 数:", df["inchikey"].nunique())

    if "T_K" in df.columns:
        print("\n温度范围：")
        print("T_min:", df["T_K"].min())
        print("T_max:", df["T_K"].max())

    if "SurfaceTension_N_m" in df.columns:
        print("\nSurface tension 范围，单位 N/m：")
        print("SurfaceTension_min:", df["SurfaceTension_N_m"].min())
        print("SurfaceTension_max:", df["SurfaceTension_N_m"].max())

    # 每个物质的数据点数预览
    if "inchikey" in df.columns:
        material_count = (
            df.groupby(["inchikey", "compound_name", "formula"], dropna=False)
            .agg(
                n_points=("SurfaceTension_N_m", "count"),
                T_min=("T_K", "min"),
                T_max=("T_K", "max"),
                surface_tension_min=("SurfaceTension_N_m", "min"),
                surface_tension_max=("SurfaceTension_N_m", "max"),
                n_doi=("doi", "nunique"),
            )
            .reset_index()
        )
        material_count["T_range"] = material_count["T_max"] - material_count["T_min"]
        material_count = material_count.sort_values(
            ["n_points", "T_range"],
            ascending=[False, False],
        )

        print("\n每个物质数据点数最多的前 30 个：")
        print(material_count.head(30).to_string(index=False))


if __name__ == "__main__":
    main()