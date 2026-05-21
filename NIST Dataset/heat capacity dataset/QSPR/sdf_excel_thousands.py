import os
import numpy as np
import pandas as pd
from tqdm import tqdm
from rdkit import Chem
from mordred import Calculator, descriptors

# =========================================
# 1. 路径设置：直接指定你现在这两个 SDF 文件
# =========================================
sdf_files = [
    r"D:\PyProjects\extend\real data\NIST\heat capacity dataset\QSPR\pubchem_2d_all.sdf"
]

output_csv = r"D:\PyProjects\extend\real data\NIST\heat capacity dataset\QSPR\descriptors_mordred_combined_oldstyle.csv"
output_excel = r"D:\PyProjects\extend\real data\NIST\heat capacity dataset\QSPR\descriptors_mordred_combined_oldstyle.xlsx"

# =========================================
# 2. 初始化 Mordred（全部描述符，忽略3D）
# =========================================
calc = Calculator(descriptors, ignore_3D=True)

# =========================================
# 3. 工具函数
# =========================================
def clean_mordred_value(v):
    """
    将 Mordred 输出尽量清洗成适合表格存储的值
    """
    if v is None:
        return np.nan

    if isinstance(v, (int, float, np.integer, np.floating, bool, np.bool_)):
        return v

    try:
        return float(v)
    except Exception:
        return np.nan

# =========================================
# 4. 主循环
# =========================================
results = []
skipped_files = []

print(f"📂 共指定 {len(sdf_files)} 个 SDF 文件，开始提取分子描述符...\n")

for sdf_file in sdf_files:
    if not os.path.exists(sdf_file):
        print(f"⚠️ 文件不存在: {sdf_file}")
        skipped_files.append(f"{sdf_file} - File not found")
        continue

    if os.path.getsize(sdf_file) == 0:
        print(f"⚠️ 空文件: {sdf_file}")
        skipped_files.append(f"{sdf_file} - Empty file")
        continue

    file = os.path.basename(sdf_file)

    try:
        suppl = Chem.SDMolSupplier(sdf_file, removeHs=False)
    except Exception as e:
        print(f"❌ 无法打开 SDF 文件: {file}, 原因: {e}")
        skipped_files.append(f"{file} - Open failed: {e}")
        continue

    mol_count = 0
    valid_count = 0

    for i, mol in enumerate(tqdm(suppl, desc=file), start=1):
        mol_count += 1

        if mol is None:
            print(f"⚠️ 无法解析结构: {file}, 分子序号 {i}")
            skipped_files.append(f"{file} - Molecule {i} RDKit parse failed")
            continue

        try:
            desc = calc(mol)
            desc_dict = desc.asdict()

            # 清洗描述符值
            desc_dict = {k: clean_mordred_value(v) for k, v in desc_dict.items()}

            if desc_dict:
                # 旧版风格：主要保留描述符 + filename
                # 因为一个 SDF 里有多个分子，所以 filename 加上分子序号
                desc_dict["filename"] = f"{file}_mol{i}"
                results.append(desc_dict)
                valid_count += 1
            else:
                print(f"⚠️ 无描述符输出: {file}, 分子序号 {i}")
                skipped_files.append(f"{file} - Molecule {i} No descriptors")

        except Exception as e:
            print(f"❌ Error extracting from {file}, 分子序号 {i}: {e}")
            skipped_files.append(f"{file} - Molecule {i} Exception: {e}")

    print(f"✅ {file}：共扫描 {mol_count} 个分子，成功提取 {valid_count} 个")

# =========================================
# 5. 转 DataFrame 并保存
# =========================================
df = pd.DataFrame(results)
df.to_csv(output_csv, index=False)

with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
    df.to_excel(writer, sheet_name="descriptors", index=False)

    skipped_df = pd.DataFrame({"skipped": skipped_files})
    skipped_df.to_excel(writer, sheet_name="skipped", index=False)

# =========================================
# 6. 日志输出
# =========================================
print(f"\n✅ 描述符提取完成，共处理 {len(results)} 个分子。")
print(f"📄 CSV 保存至：{output_csv}")
print(f"📄 Excel 保存至：{output_excel}")

if skipped_files:
    print(f"\n⚠️ 跳过 {len(skipped_files)} 条记录：")
    for f in skipped_files[:20]:
        print(f" - {f}")
    if len(skipped_files) > 20:
        print(" ... （其余跳过记录已写入 Excel 的 skipped sheet）")
else:
    print("✅ 所有分子均处理成功，无跳过文件。")

# =========================================================
# 环境示例
# conda activate mordred-env
# python "D:\PyProjects\extend\real data\QSPR_2D_structure\sdf_excel_thousands.py"
# =========================================================