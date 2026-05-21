import xml.etree.ElementTree as ET
from pathlib import Path
import pandas as pd
import re
import numpy as np


# =========================
# 1. 修改这里：ThermoML 解压后的根目录
# =========================
ROOT_DIR = Path(r"D:\PyProjects\extend\real data\NIST\ThermoML.v2020-09-30")

# 是否只保留纯有机化合物
ONLY_PURE_ORGANIC = True

# SMILES 缺失时填什么
SMILES_MISSING_VALUE = "待定"

# 输出文件
OUT_ALL = "thermoml_vapor_pressure_all.xlsx"
OUT_VP = "thermoml_vapor_pressure_convertible_only.xlsx"
OUT_VP_BY_PHASE = "thermoml_vapor_pressure_by_phase.xlsx"


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
        "org_num": org_num
    }


def get_original_smiles(comp_elem):
    smiles_list = all_texts(comp_elem, "sSmiles")
    if smiles_list:
        return "; ".join(smiles_list)
    return SMILES_MISSING_VALUE


def extract_unit_from_property_name(prop_name):
    """
    从属性名中粗略提取单位。

    例如：
    Vapor pressure, kPa -> kPa
    Saturated vapor pressure, Pa ; Liquid -> Pa
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
# 3. Vapor pressure 判断与单位换算
# =========================
def normalize_unit_string(unit):
    if unit is None:
        return ""

    u = str(unit).strip().lower()
    u = u.replace(" ", "")
    u = u.replace("−", "-")
    u = u.replace("·", ".")
    u = u.replace("*", "")
    u = u.replace("^", "")
    u = u.replace("(", "")
    u = u.replace(")", "")
    u = u.replace("[", "")
    u = u.replace("]", "")

    # Unicode 兼容
    u = u.replace("μ", "u")

    return u


def is_pressure_unit(unit):
    """
    判断单位是否是常见压力单位。
    """
    u = normalize_unit_string(unit)

    pressure_units = {
        "pa", "pascal", "pascals",
        "kpa", "kilopascal", "kilopascals",
        "mpa", "megapascal", "megapascals",
        "bar",
        "mbar",
        "atm", "atmosphere", "atmospheres",
        "torr",
        "mmhg",
        "cmhg",
        "psi",
    }

    return u in pressure_units


def is_vapor_pressure_property(prop_name, unit=None):
    """
    识别 ThermoML 中的 vapor pressure 类属性。

    主要保留：
    - vapor pressure
    - vapour pressure
    - saturated vapor pressure
    - saturation pressure
    - sublimation pressure

    排除：
    - osmotic pressure
    - partial pressure
    - critical pressure
    - excess / coefficient / derivative 等非普通蒸气压属性
    """
    if not prop_name:
        return False

    s = str(prop_name).lower()

    good_words = [
        "vapor pressure",
        "vapour pressure",
        "saturated vapor pressure",
        "saturated vapour pressure",
        "saturation pressure",
        "sublimation pressure",
    ]

    if not any(w in s for w in good_words):
        return False

    bad_words = [
        "partial pressure",
        "osmotic pressure",
        "critical pressure",
        "excess",
        "coefficient",
        "derivative",
        "difference",
        "deviation",
        "standard deviation",
        "change in",
        "pressure drop",
    ]

    if any(w in s for w in bad_words):
        return False

    # 如果能识别出单位，则要求是压力单位；
    # 如果单位缺失，则暂时保留到 all 表中，后续 convertible 表会自动过滤。
    if unit is not None and str(unit).strip() != "":
        return is_pressure_unit(unit)

    return True


def convert_pressure_to_common_units(value, unit):
    """
    将 vapor pressure 转换为常用单位。

    返回：
    VaporPressure_Pa
    VaporPressure_kPa
    VaporPressure_bar
    VaporPressure_atm
    VaporPressure_mmHg
    lnP_kPa

    无法识别单位时返回 nan。
    """
    if value is None or not pd.notna(value):
        return np.nan, np.nan, np.nan, np.nan, np.nan, np.nan

    try:
        v = float(value)
    except Exception:
        return np.nan, np.nan, np.nan, np.nan, np.nan, np.nan

    u = normalize_unit_string(unit)

    p_kpa = np.nan

    if u in {"pa", "pascal", "pascals"}:
        p_kpa = v / 1000.0

    elif u in {"kpa", "kilopascal", "kilopascals"}:
        p_kpa = v

    elif u in {"mpa", "megapascal", "megapascals"}:
        p_kpa = v * 1000.0

    elif u == "bar":
        p_kpa = v * 100.0

    elif u == "mbar":
        p_kpa = v * 0.1

    elif u in {"atm", "atmosphere", "atmospheres"}:
        p_kpa = v * 101.325

    elif u == "torr":
        p_kpa = v * 0.133322368

    elif u == "mmhg":
        p_kpa = v * 0.133322368

    elif u == "cmhg":
        p_kpa = v * 1.33322368

    elif u == "psi":
        p_kpa = v * 6.89475729

    if not pd.notna(p_kpa):
        return np.nan, np.nan, np.nan, np.nan, np.nan, np.nan

    p_pa = p_kpa * 1000.0
    p_bar = p_kpa / 100.0
    p_atm = p_kpa / 101.325
    p_mmhg = p_kpa / 0.133322368

    if p_kpa > 0:
        ln_p_kpa = np.log(p_kpa)
    else:
        ln_p_kpa = np.nan

    return p_pa, p_kpa, p_bar, p_atm, p_mmhg, ln_p_kpa


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
    "B", "Si"
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
    "La", "Ce", "Nd", "U"
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
# 6. 提取单个 XML 文件
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
            "inchi": inchi
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
                    "inchi": None
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
                "is_vapor_pressure": is_vapor_pressure_property(prop_name, prop_unit),
            }

        vp_prop_numbers = [
            k for k, v in prop_defs.items()
            if v["is_vapor_pressure"]
        ]

        if not vp_prop_numbers:
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
                "org_num": reg.get("org_num")
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
                "org_num": reg.get("org_num")
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
                else:
                    base[cname] = val
                    base[f"{cname}_uncertainty"] = uncert

            # 属性值，可能一个 NumValues 中有多个 PropertyValue
            for pv in children(nv, "PropertyValue"):
                n_prop = first_text(pv, "nPropNumber")
                prop_info = prop_defs.get(str(n_prop))

                if prop_info is None:
                    continue

                if not prop_info["is_vapor_pressure"]:
                    continue

                row = dict(base)

                prop_value = to_float(first_text(pv, "nPropValue"))
                prop_uncert = to_float(first_text(pv, "nExpandUncertValue"))

                p_pa, p_kpa, p_bar, p_atm, p_mmhg, ln_p_kpa = convert_pressure_to_common_units(
                    prop_value,
                    prop_info["property_unit"]
                )

                row["property_name"] = prop_info["property_name"]
                row["property_unit"] = prop_info["property_unit"]
                row["phase"] = prop_info["phase"]
                row["method"] = prop_info["method"]

                row["property_value"] = prop_value
                row["property_uncertainty"] = prop_uncert

                row["is_vapor_pressure"] = prop_info["is_vapor_pressure"]

                row["VaporPressure_Pa"] = p_pa
                row["VaporPressure_kPa"] = p_kpa
                row["VaporPressure_bar"] = p_bar
                row["VaporPressure_atm"] = p_atm
                row["VaporPressure_mmHg"] = p_mmhg
                row["lnP_kPa"] = ln_p_kpa

                rows.append(row)

    return rows


# =========================
# 7. 扫描全部 XML
# =========================
def main():
    xml_files = list(ROOT_DIR.rglob("*.xml"))

    print(f"找到 XML 文件数量: {len(xml_files)}")

    all_rows = []

    for i, xml_path in enumerate(xml_files, start=1):
        if i % 500 == 0:
            print(f"已处理 {i}/{len(xml_files)} 个 XML 文件")

        rows = parse_one_xml(xml_path)
        all_rows.extend(rows)

    print(f"提取到 vapor pressure 类数据点数量: {len(all_rows)}")

    if not all_rows:
        print("没有提取到数据。请检查 ROOT_DIR 是否是解压后的目录，或者检查 vapor pressure 属性名匹配规则。")
        return

    df = pd.DataFrame(all_rows)

    # 确保 smiles 列存在，并把空值填成“待定”
    if "smiles" not in df.columns:
        df["smiles"] = SMILES_MISSING_VALUE
    df["smiles"] = df["smiles"].fillna(SMILES_MISSING_VALUE)
    df.loc[df["smiles"].astype(str).str.strip() == "", "smiles"] = SMILES_MISSING_VALUE

    if "component_smiles" not in df.columns:
        df["component_smiles"] = SMILES_MISSING_VALUE
    df["component_smiles"] = df["component_smiles"].fillna(SMILES_MISSING_VALUE)
    df.loc[df["component_smiles"].astype(str).str.strip() == "", "component_smiles"] = SMILES_MISSING_VALUE

    # 是否只保留纯有机化合物
    if ONLY_PURE_ORGANIC:
        df["elements"] = df["formula"].apply(lambda x: ",".join(sorted(parse_elements(x))))
        df["organic_filter_reason"] = df.apply(organic_filter_reason, axis=1)

        df_rejected = df[df["organic_filter_reason"] != "kept"].copy()
        df = df[df["organic_filter_reason"] == "kept"].copy()

        print(f"只保留纯有机化合物后，vapor pressure 类数据点数量: {len(df)}")
        print("被排除数据点数量:", len(df_rejected))
        print("\n排除原因统计：")
        print(df_rejected["organic_filter_reason"].value_counts())

    # 排序，方便检查
    sort_cols = [
        c for c in [
            "cas",
            "compound_name",
            "T_K",
            "VaporPressure_kPa",
            "property_name"
        ]
        if c in df.columns
    ]
    if sort_cols:
        df = df.sort_values(sort_cols, na_position="last")

    # 保存所有 vapor pressure 类属性
    df.to_excel(OUT_ALL, index=False)
    print(f"\n已保存全部 vapor pressure 类数据: {OUT_ALL}")
    print(f"vapor pressure 类数据点数量: {len(df)}")

    # 只保留可以完成压力单位换算的数据
    df_vp = df[
        (df["is_vapor_pressure"] == True)
        & df["VaporPressure_kPa"].notna()
    ].copy()

    df_vp.to_excel(OUT_VP, index=False)
    print(f"\n已保存可换算 vapor pressure 数据: {OUT_VP}")
    print(f"可换算 vapor pressure 数据点数量: {len(df_vp)}")

    # 按 phase 分 sheet
    save_by_phase_excel(df_vp, OUT_VP_BY_PHASE)

    # 简单统计
    smiles_valid = (
        df_vp["smiles"].notna()
        & (df_vp["smiles"].astype(str).str.strip() != SMILES_MISSING_VALUE)
    )

    print("\nSMILES 统计：")
    print("vapor pressure 数据点总数:", len(df_vp))
    print("有 XML 原始 SMILES 的数据点数:", int(smiles_valid.sum()))
    print("没有 XML 原始 SMILES 的数据点数:", int(len(df_vp) - smiles_valid.sum()))

    if "cas" in df_vp.columns:
        print("有 XML 原始 SMILES 的 CAS 数:", df_vp.loc[smiles_valid, "cas"].nunique())

    print("\n属性名统计：")
    print(df["property_name"].value_counts().head(50))

    print("\nvapor pressure 单位统计：")
    print(df_vp["property_unit"].value_counts().head(30))

    if "phase" in df_vp.columns:
        print("\nvapor pressure 相态统计：")
        print(df_vp["phase"].fillna("Unknown").value_counts())

    if "cas" in df_vp.columns:
        print("\n物质数量统计：")
        print("CAS 数:", df_vp["cas"].nunique())
        print("compound_name 数:", df_vp["compound_name"].nunique())

    if "T_K" in df_vp.columns:
        print("\n温度范围：")
        print("T_min:", df_vp["T_K"].min())
        print("T_max:", df_vp["T_K"].max())

    if "VaporPressure_kPa" in df_vp.columns:
        print("\n蒸气压范围，单位 kPa：")
        print("P_min:", df_vp["VaporPressure_kPa"].min())
        print("P_max:", df_vp["VaporPressure_kPa"].max())


if __name__ == "__main__":
    main()