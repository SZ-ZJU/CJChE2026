import os
import re
from pathlib import Path

import numpy as np

# =========================================================
# Mordred 与新版 numpy 兼容补丁
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
base_dir = Path(".")

# 前一步 PubChem 2D 下载脚本生成的总 SDF
combined_sdf_file = base_dir / "viscosity_pubchem_2d_all.sdf"

# 如果没有总 SDF，则自动读取批量 SDF
sdf_batch_pattern = "viscosity_pubchem_2d_batch_*.sdf"

# 前一步生成的 CID 映射表，里面应该有 98 个物质行
mapping_excel = base_dir / "viscosity_pubchem_cid_mapping_results.xlsx"
mapping_sheet = "All_Query_Results"

# 输出：唯一 CID 描述符，通常是 97 行
output_unique_csv = base_dir / "viscosity_descriptors_mordred_2d_unique_cid.csv"

# 输出：回填到原始物质后的描述符，应该是 98 行
output_csv = base_dir / "viscosity_descriptors_mordred_2d.csv"
output_excel = base_dir / "viscosity_descriptors_mordred_2d.xlsx"


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
    无法转成数值的 Descriptor Error / Missing 等对象记为 NaN。
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
    从 SDF 属性或表格字段中解析 CID。
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
        ]
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
    优先使用 viscosity_pubchem_2d_all.sdf。
    如果不存在，则读取 viscosity_pubchem_2d_batch_*.sdf。
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
    这个表应该是原始物质级别的 98 行。
    """
    if not mapping_file.exists():
        raise FileNotFoundError(
            f"没有找到 CID 映射文件: {mapping_file}\n"
            "这个版本需要 mapping 文件来把 97 个唯一 CID 描述符扩展回 98 个物质。"
        )

    xls = pd.ExcelFile(mapping_file)

    if mapping_sheet in xls.sheet_names:
        sheet = mapping_sheet
    elif "Success" in xls.sheet_names:
        sheet = "Success"
    else:
        sheet = xls.sheet_names[0]

    df_map = pd.read_excel(mapping_file, sheet_name=sheet)

    if "CID" not in df_map.columns:
        raise ValueError(
            f"映射表 {mapping_file} 的 {sheet} sheet 中没有 CID 列，无法回填描述符。"
        )

    df_map = df_map.copy()
    df_map["CID_int"] = df_map["CID"].apply(parse_cid_from_text)

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

print(f"\n成功读取 CID 映射表: {mapping_excel}")
print("映射表行数，也就是原始物质数:", len(df_mapping))
print("映射表有效 CID 数量:", df_mapping["CID_int"].notna().sum())
print("映射表唯一 CID 数量:", df_mapping["CID_int"].dropna().nunique())


# =========================================================
# 6. 从 SDF 提取唯一 CID 的 Mordred 2D 描述符
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

            # 保留 SDF 中常见 PubChem 属性
            for prop in [
                "PUBCHEM_COMPOUND_CID",
                "PUBCHEM_OPENEYE_CAN_SMILES",
                "PUBCHEM_OPENEYE_ISO_SMILES",
                "PUBCHEM_IUPAC_NAME",
                "PUBCHEM_MOLECULAR_FORMULA",
                "PUBCHEM_MOLECULAR_WEIGHT",
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
# 7. 唯一 CID 描述符表
# =========================================================
df_desc_unique = pd.DataFrame(results)

if len(df_desc_unique) == 0:
    raise ValueError("没有成功提取任何分子描述符，请检查 SDF 文件。")

df_desc_unique["CID_int"] = df_desc_unique["sdf_pubchem_cid"].apply(parse_cid_from_text)
df_desc_unique["CID_int"] = pd.to_numeric(df_desc_unique["CID_int"], errors="coerce")

# 如果同一个 CID 在 SDF 中重复出现，只保留第一条
df_desc_unique = (
    df_desc_unique
    .dropna(subset=["CID_int"])
    .drop_duplicates(subset=["CID_int"], keep="first")
    .reset_index(drop=True)
)

df_desc_unique["CID_int"] = df_desc_unique["CID_int"].astype(int)

print("\n唯一 CID 描述符行数:", len(df_desc_unique))


# =========================================================
# 8. 根据 mapping 把唯一 CID 描述符扩展回 98 个物质行
# =========================================================
df_mapping_valid = df_mapping.copy()

df_mapping_valid["CID_int"] = pd.to_numeric(
    df_mapping_valid["CID_int"],
    errors="coerce"
)

df_mapping_valid = df_mapping_valid.dropna(subset=["CID_int"]).copy()
df_mapping_valid["CID_int"] = df_mapping_valid["CID_int"].astype(int)

# 描述符列：从唯一 CID 表中排除 SDF 元信息列
unique_metadata_cols = [
    "source_sdf",
    "mol_index_in_file",
    "global_mol_index",
    "sdf_pubchem_cid",
    "CID_int",
    "canonical_smiles_from_sdf",
    "inchikey_from_rdkit",
    "PUBCHEM_COMPOUND_CID",
    "PUBCHEM_OPENEYE_CAN_SMILES",
    "PUBCHEM_OPENEYE_ISO_SMILES",
    "PUBCHEM_IUPAC_NAME",
    "PUBCHEM_MOLECULAR_FORMULA",
    "PUBCHEM_MOLECULAR_WEIGHT",
]

unique_metadata_cols = [
    c for c in unique_metadata_cols
    if c in df_desc_unique.columns
]

descriptor_cols = [
    c for c in df_desc_unique.columns
    if c not in unique_metadata_cols
]

# 只拿 CID + SDF元信息 + 描述符
df_desc_for_merge = df_desc_unique.copy()

df_expanded = df_mapping_valid.merge(
    df_desc_for_merge,
    on="CID_int",
    how="left",
    suffixes=("_mapping", "_sdf")
)

# 检查哪些物质没有匹配到 SDF 描述符
missing_desc_mask = df_expanded["sdf_pubchem_cid"].isna() if "sdf_pubchem_cid" in df_expanded.columns else pd.Series(False, index=df_expanded.index)

df_missing_desc = df_expanded.loc[missing_desc_mask].copy()

print("\n扩展回原始物质后的描述符行数:", len(df_expanded))
print("未匹配到 SDF 描述符的物质数:", len(df_missing_desc))


# =========================================================
# 9. 检查重复 CID 对应哪些物质
# =========================================================
df_duplicate_cid = (
    df_mapping_valid[df_mapping_valid["CID_int"].duplicated(keep=False)]
    .sort_values("CID_int")
    .copy()
)

print("\n重复 CID 对应的物质行数:", len(df_duplicate_cid))

if len(df_duplicate_cid) > 0:
    show_cols = [
        "CID_int",
        "original_material_index",
        "material_key",
        "compound_name",
        "cas",
        "inchikey",
        "smiles",
    ]
    show_cols = [c for c in show_cols if c in df_duplicate_cid.columns]
    print("\n重复 CID 对应物质:")
    print(df_duplicate_cid[show_cols].to_string(index=False))


# =========================================================
# 10. 调整列顺序
# =========================================================
metadata_cols = [
    "original_material_index",
    "material_key",
    "compound_name",
    "cas",
    "formula",
    "inchikey",
    "smiles",
    "SMILES",
    "final_smiles",
    "existing_pubchem_cid",
    "pubchem_cid",
    "CID",
    "CID_int",
    "query_source",
    "query_identifier",
    "query_status",
    "CID_all",
    "canonical_smiles_from_sdf",
    "inchikey_from_rdkit",
    "source_sdf",
    "mol_index_in_file",
    "global_mol_index",
    "sdf_pubchem_cid",
    "PUBCHEM_COMPOUND_CID",
    "PUBCHEM_IUPAC_NAME",
    "PUBCHEM_MOLECULAR_FORMULA",
    "PUBCHEM_MOLECULAR_WEIGHT",
    "PUBCHEM_OPENEYE_CAN_SMILES",
    "PUBCHEM_OPENEYE_ISO_SMILES",
    "boiling_T_K",
    "critical_T_K",
    "T_min",
    "T_max",
    "n_points",
    "phase",
]

metadata_cols = [
    c for c in metadata_cols
    if c in df_expanded.columns
]

remaining_cols = [
    c for c in df_expanded.columns
    if c not in metadata_cols
]

df_expanded = df_expanded[metadata_cols + remaining_cols]


# =========================================================
# 11. skipped 记录和运行信息
# =========================================================
df_skipped = pd.DataFrame(skipped_records)

run_info = pd.DataFrame([
    {"item": "base_dir", "value": str(base_dir)},
    {"item": "combined_sdf_file", "value": str(combined_sdf_file)},
    {"item": "sdf_batch_pattern", "value": sdf_batch_pattern},
    {"item": "sdf_files_count", "value": len(sdf_files)},
    {"item": "mapping_excel", "value": str(mapping_excel)},
    {"item": "mapping_sheet", "value": mapping_sheet},
    {"item": "mapping_rows_original_materials", "value": len(df_mapping)},
    {"item": "mapping_valid_cid_rows", "value": len(df_mapping_valid)},
    {"item": "unique_cid_descriptor_rows", "value": len(df_desc_unique)},
    {"item": "expanded_descriptor_rows", "value": len(df_expanded)},
    {"item": "missing_descriptor_rows", "value": len(df_missing_desc)},
    {"item": "duplicate_cid_rows", "value": len(df_duplicate_cid)},
    {"item": "mordred_ignore_3D", "value": True},
])


# =========================================================
# 12. 保存结果
# =========================================================
df_desc_unique.to_csv(
    output_unique_csv,
    index=False,
    encoding="utf-8-sig"
)

df_expanded.to_csv(
    output_csv,
    index=False,
    encoding="utf-8-sig"
)

with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
    # 这个 sheet 是最终后续使用的 98 行描述符表
    df_expanded.to_excel(
        writer,
        sheet_name="descriptors",
        index=False
    )

    # 这个 sheet 是 97 个唯一 CID 的描述符表
    df_desc_unique.to_excel(
        writer,
        sheet_name="descriptors_unique_cid",
        index=False
    )

    df_duplicate_cid.to_excel(
        writer,
        sheet_name="duplicate_cid_check",
        index=False
    )

    df_missing_desc.to_excel(
        writer,
        sheet_name="missing_descriptor",
        index=False
    )

    df_skipped.to_excel(
        writer,
        sheet_name="skipped",
        index=False
    )

    run_info.to_excel(
        writer,
        sheet_name="run_info",
        index=False
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

            ws.column_dimensions[col_letter].width = min(max_length + 2, 45)


print("\n描述符提取与回填完成。")
print(f"唯一 CID 描述符行数: {len(df_desc_unique)}")
print(f"最终物质级描述符行数: {len(df_expanded)}")
print(f"未匹配描述符行数: {len(df_missing_desc)}")
print(f"跳过记录数: {len(df_skipped)}")

print("\n输出文件:")
print(f"1) 唯一 CID 描述符 CSV: {output_unique_csv}")
print(f"2) 最终 98 行描述符 CSV: {output_csv}")
print(f"3) 最终 Excel: {output_excel}")

if len(df_expanded) != len(df_mapping_valid):
    print("\n警告：最终描述符行数和 mapping 有效 CID 行数不一致，请检查 missing_descriptor sheet。")
else:
    print("\n最终描述符行数与 mapping 有效 CID 行数一致。")