# -*- coding: utf-8 -*-
"""
Surface tension liquid-gas:
PubChem 2D SDF -> Mordred 2D molecular descriptors

输入：
    1. surface_tension_pubchem_2d_all.sdf
       或者：
       surface_tension_pubchem_2d_batch_*.sdf

    2. surface_tension_pubchem_cid_mapping_results.xlsx
       sheet = All_Query_Results

输出：
    1. surface_tension_descriptors_mordred_2d.csv
    2. surface_tension_descriptors_mordred_2d.xlsx

功能：
    1. 读取前一步 PubChem 下载得到的 2D SDF 文件
    2. 用 RDKit 读取分子结构
    3. 用 Mordred 计算全部 2D 描述符，ignore_3D=True
    4. 根据 PubChem CID 合并前一步的物质映射表
    5. 输出描述符矩阵，可作为后续 QSPR 模型输入
"""

import os
import re
from pathlib import Path

import numpy as np

# =========================================================
# 0. Mordred 与新版 numpy 兼容补丁
# 有些 Mordred 版本会 from numpy import product
# 新版 numpy 中可能没有 product，因此这里补一个别名
# =========================================================

if not hasattr(np, "product"):
    np.product = np.prod

import pandas as pd
from tqdm import tqdm

from rdkit import Chem
from rdkit.Chem import inchi

from mordred import Calculator, descriptors


# =========================================================
# 1. 路径设置
# =========================================================

# 当前脚本所在文件夹
base_dir = Path(".")

# PubChem 下载脚本生成的总 SDF 文件
combined_sdf_file = base_dir / "surface_tension_pubchem_2d_all.sdf"

# 如果没有总 SDF，则自动读取批量 SDF
sdf_batch_pattern = "surface_tension_pubchem_2d_batch_*.sdf"

# PubChem CID 映射文件，来自前一步结构下载脚本
mapping_excel = base_dir / "surface_tension_pubchem_cid_mapping_results.xlsx"
mapping_sheet = "All_Query_Results"

# 输出文件
output_csv = base_dir / "surface_tension_descriptors_mordred_2d.csv"
output_excel = base_dir / "surface_tension_descriptors_mordred_2d.xlsx"


# =========================================================
# 2. 初始化 Mordred：全部 2D 描述符，忽略 3D
# =========================================================

calc = Calculator(descriptors, ignore_3D=True)


# =========================================================
# 3. 工具函数
# =========================================================

def clean_mordred_value(v):
    """
    将 Mordred 输出清洗成适合表格存储的数值。
    Descriptor Error / Missing 等无法转数值的对象记为 NaN。
    """
    if v is None:
        return np.nan

    if isinstance(v, (int, float, np.integer, np.floating, bool, np.bool_)):
        return v

    try:
        return float(v)
    except Exception:
        return np.nan


def parse_cid_from_text(x):
    """
    从 SDF 属性或表格字段中解析 PubChem CID。
    """
    if x is None:
        return np.nan

    s = str(x).strip()

    if s == "" or s.lower() in ["nan", "none", "null"]:
        return np.nan

    try:
        f = float(s)
        if np.isfinite(f):
            return int(f)
    except Exception:
        pass

    m = re.search(r"\d+", s)

    if m:
        return int(m.group(0))

    return np.nan


def get_mol_prop(mol, prop_names):
    """
    从 RDKit mol 中按候选属性名读取属性。
    """
    for name in prop_names:
        if mol.HasProp(name):
            value = mol.GetProp(name)

            if value is not None and str(value).strip() != "":
                return str(value).strip()

    return ""


def get_pubchem_cid_from_mol(mol):
    """
    PubChem SDF 通常包含 PUBCHEM_COMPOUND_CID。
    """
    cid_value = get_mol_prop(
        mol,
        [
            "PUBCHEM_COMPOUND_CID",
            "PUBCHEM_CID",
            "CID",
            "cid",
        ],
    )

    return parse_cid_from_text(cid_value)


def safe_mol_to_smiles(mol):
    try:
        return Chem.MolToSmiles(mol, isomericSmiles=True)
    except Exception:
        return ""


def safe_mol_to_inchikey(mol):
    try:
        return inchi.MolToInchiKey(mol)
    except Exception:
        return ""


def find_sdf_files():
    """
    优先使用 surface_tension_pubchem_2d_all.sdf。
    如果不存在，则读取 surface_tension_pubchem_2d_batch_*.sdf。
    """
    if combined_sdf_file.exists() and combined_sdf_file.stat().st_size > 0:
        return [combined_sdf_file]

    batch_files = sorted(base_dir.glob(sdf_batch_pattern))

    batch_files = [
        f for f in batch_files
        if f.exists() and f.stat().st_size > 0
    ]

    return batch_files


def load_pubchem_mapping(mapping_file):
    """
    读取前一步 PubChem CID 映射结果。
    若文件不存在，则返回空表，不影响描述符提取。
    """
    if not mapping_file.exists():
        print(f"未找到 CID 映射文件: {mapping_file}")
        print("将只输出 SDF 中可解析的信息。")
        return pd.DataFrame()

    xls = pd.ExcelFile(mapping_file)

    if mapping_sheet in xls.sheet_names:
        sheet = mapping_sheet
    elif "Success" in xls.sheet_names:
        sheet = "Success"
    else:
        sheet = xls.sheet_names[0]

    df_map = pd.read_excel(mapping_file, sheet_name=sheet)

    if "CID" not in df_map.columns:
        print(f"映射表 {mapping_file} 中没有 CID 列，将不做映射合并。")
        return pd.DataFrame()

    df_map = df_map.copy()
    df_map["CID_int"] = df_map["CID"].apply(parse_cid_from_text)

    df_map = df_map.dropna(subset=["CID_int"]).copy()
    df_map["CID_int"] = df_map["CID_int"].astype(int)

    # 同一个 CID 可能对应多个来源，只保留第一条
    df_map = df_map.drop_duplicates(subset=["CID_int"], keep="first")

    return df_map


# =========================================================
# 4. 读取 SDF 文件列表
# =========================================================

sdf_files = find_sdf_files()

if len(sdf_files) == 0:
    raise FileNotFoundError(
        f"没有找到可用 SDF 文件。\n"
        f"请确认存在: {combined_sdf_file}\n"
        f"或存在批量文件: {sdf_batch_pattern}"
    )

print(f"共找到 {len(sdf_files)} 个 SDF 文件:")
for f in sdf_files:
    print(" -", f)


# =========================================================
# 5. 读取 CID 映射表
# =========================================================

df_mapping = load_pubchem_mapping(mapping_excel)

if len(df_mapping) > 0:
    print(f"\n成功读取 CID 映射表: {mapping_excel}")
    print(f"映射表有效 CID 数量: {df_mapping['CID_int'].nunique()}")
else:
    print("\n没有可用 CID 映射表，后续只保存描述符和 SDF 元信息。")


# =========================================================
# 6. 主循环：提取 Mordred 2D 描述符
# =========================================================

results = []
skipped_records = []

global_mol_index = 0

print("\n开始提取 Mordred 2D 描述符...\n")

for sdf_file in sdf_files:
    if not sdf_file.exists():
        skipped_records.append({
            "source_sdf": str(sdf_file),
            "mol_index_in_file": None,
            "reason": "SDF file not found",
        })
        continue

    if sdf_file.stat().st_size == 0:
        skipped_records.append({
            "source_sdf": str(sdf_file),
            "mol_index_in_file": None,
            "reason": "Empty SDF file",
        })
        continue

    file_name = sdf_file.name

    try:
        suppl = Chem.SDMolSupplier(str(sdf_file), removeHs=False)
    except Exception as e:
        skipped_records.append({
            "source_sdf": str(sdf_file),
            "mol_index_in_file": None,
            "reason": f"Open failed: {type(e).__name__}: {e}",
        })
        continue

    mol_count = 0
    valid_count = 0

    for mol_index_in_file, mol in enumerate(tqdm(suppl, desc=file_name), start=1):
        mol_count += 1
        global_mol_index += 1

        if mol is None:
            skipped_records.append({
                "source_sdf": str(sdf_file),
                "mol_index_in_file": mol_index_in_file,
                "global_mol_index": global_mol_index,
                "reason": "RDKit parse failed",
            })
            continue

        try:
            cid = get_pubchem_cid_from_mol(mol)
            smiles = safe_mol_to_smiles(mol)
            inchikey_from_rdkit = safe_mol_to_inchikey(mol)

            desc = calc(mol)
            desc_dict = desc.asdict()

            clean_desc = {
                str(k): clean_mordred_value(v)
                for k, v in desc_dict.items()
            }

            row = {
                "source_sdf": file_name,
                "mol_index_in_file": mol_index_in_file,
                "global_mol_index": global_mol_index,
                "sdf_pubchem_cid": cid,
                "canonical_smiles_from_sdf": smiles,
                "inchikey_from_rdkit": inchikey_from_rdkit,
            }

            # 保留 SDF 中常见的 PubChem 属性，方便追溯
            for prop in [
                "PUBCHEM_COMPOUND_CID",
                "PUBCHEM_OPENEYE_CAN_SMILES",
                "PUBCHEM_OPENEYE_ISO_SMILES",
                "PUBCHEM_IUPAC_NAME",
                "PUBCHEM_MOLECULAR_FORMULA",
                "PUBCHEM_MOLECULAR_WEIGHT",
                "PUBCHEM_EXACT_MASS",
                "PUBCHEM_MONOISOTOPIC_WEIGHT",
                "PUBCHEM_TOTAL_CHARGE",
            ]:
                if mol.HasProp(prop):
                    row[prop] = mol.GetProp(prop)

            row.update(clean_desc)

            results.append(row)
            valid_count += 1

        except Exception as e:
            skipped_records.append({
                "source_sdf": str(sdf_file),
                "mol_index_in_file": mol_index_in_file,
                "global_mol_index": global_mol_index,
                "reason": f"Descriptor extraction failed: {type(e).__name__}: {e}",
            })

    print(f"{file_name}: 共扫描 {mol_count} 个分子，成功提取 {valid_count} 个。")


# =========================================================
# 7. 转 DataFrame
# =========================================================

df_desc = pd.DataFrame(results)

if len(df_desc) == 0:
    raise ValueError("没有成功提取任何分子描述符，请检查 SDF 文件。")

df_desc["CID_int"] = df_desc["sdf_pubchem_cid"].apply(parse_cid_from_text)
df_desc["CID_int"] = pd.to_numeric(df_desc["CID_int"], errors="coerce")


# =========================================================
# 8. 合并 CID 映射信息
# =========================================================

if len(df_mapping) > 0:
    df_desc["CID_int_for_merge"] = df_desc["CID_int"]

    df_mapping_merge = df_mapping.copy()
    df_mapping_merge["CID_int_for_merge"] = df_mapping_merge["CID_int"]

    df_desc = df_desc.merge(
        df_mapping_merge,
        on="CID_int_for_merge",
        how="left",
        suffixes=("", "_mapping"),
    )

    df_desc = df_desc.drop(columns=["CID_int_for_merge"])

    print("\n已根据 CID 合并表面张力 PubChem 查询映射信息。")
else:
    print("\n未合并映射信息。")


# =========================================================
# 9. 调整列顺序
# =========================================================

metadata_cols = [
    "source_sdf",
    "mol_index_in_file",
    "global_mol_index",
    "sdf_pubchem_cid",
    "CID_int",
    "CID",
    "CID_all",

    "compound_name",
    "cas",
    "formula",
    "inchikey",
    "smiles",
    "SMILES",
    "final_smiles",
    "existing_pubchem_cid",

    "query_source",
    "query_identifier",
    "query_status",
    "inchikey_status",
    "smiles_status",
    "cas_status",
    "name_status",

    "canonical_smiles_from_sdf",
    "inchikey_from_rdkit",

    "PUBCHEM_COMPOUND_CID",
    "PUBCHEM_IUPAC_NAME",
    "PUBCHEM_MOLECULAR_FORMULA",
    "PUBCHEM_MOLECULAR_WEIGHT",
    "PUBCHEM_EXACT_MASS",
    "PUBCHEM_MONOISOTOPIC_WEIGHT",
    "PUBCHEM_TOTAL_CHARGE",
    "PUBCHEM_OPENEYE_CAN_SMILES",
    "PUBCHEM_OPENEYE_ISO_SMILES",

    "material_key",
    "original_material_index",

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
]

metadata_cols = [
    c for c in metadata_cols
    if c in df_desc.columns
]

descriptor_cols = [
    c for c in df_desc.columns
    if c not in metadata_cols
]

df_desc = df_desc[metadata_cols + descriptor_cols]


# =========================================================
# 10. skipped 记录和运行信息
# =========================================================

df_skipped = pd.DataFrame(skipped_records)

run_info = pd.DataFrame([
    {"item": "base_dir", "value": str(base_dir)},
    {"item": "combined_sdf_file", "value": str(combined_sdf_file)},
    {"item": "sdf_batch_pattern", "value": sdf_batch_pattern},
    {"item": "sdf_files_count", "value": len(sdf_files)},
    {"item": "mapping_excel", "value": str(mapping_excel)},
    {"item": "mapping_sheet", "value": mapping_sheet},
    {"item": "n_descriptor_rows", "value": len(df_desc)},
    {"item": "n_unique_cid_in_descriptors", "value": int(df_desc["CID_int"].nunique()) if "CID_int" in df_desc.columns else np.nan},
    {"item": "n_skipped_records", "value": len(df_skipped)},
    {"item": "mordred_ignore_3D", "value": True},
    {"item": "target_property", "value": "Surface tension liquid-gas"},
    {"item": "descriptor_tool", "value": "Mordred 2D descriptors"},
])


# =========================================================
# 11. 保存结果
# =========================================================

df_desc.to_csv(
    output_csv,
    index=False,
    encoding="utf-8-sig",
)

with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
    df_desc.to_excel(
        writer,
        sheet_name="descriptors",
        index=False,
    )

    df_skipped.to_excel(
        writer,
        sheet_name="skipped",
        index=False,
    )

    run_info.to_excel(
        writer,
        sheet_name="run_info",
        index=False,
    )

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

            ws.column_dimensions[col_letter].width = min(max_length + 2, 40)


print("\n描述符提取完成。")
print(f"成功处理分子数: {len(df_desc)}")
print(f"跳过记录数: {len(df_skipped)}")
print(f"CSV 保存至: {output_csv}")
print(f"Excel 保存至: {output_excel}")

if len(df_skipped) > 0:
    print("\n前 20 条跳过记录:")
    print(df_skipped.head(20).to_string(index=False))
else:
    print("所有分子均处理成功，无跳过记录。")


# =========================================================
# 环境示例
# =========================================================
# conda activate mordred-env
# python surface_sdf_to_mordred_descriptors.py