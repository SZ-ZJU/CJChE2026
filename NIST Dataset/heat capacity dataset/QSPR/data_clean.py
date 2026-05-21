import pandas as pd
from sklearn.feature_selection import VarianceThreshold

# 读取数据
df = pd.read_csv("descriptors_mordred_combined_oldstyle.csv")

print("原始形状:", df.shape)

# 1. 删除缺失值比例大于 30% 的列
df = df.loc[:, df.isnull().mean() < 0.3]
print("删高缺失列后:", df.shape)

# 2. 删除包含非数字内容的列
def is_float_column(series):
    try:
        pd.to_numeric(series.dropna())
        return True
    except:
        return False

numeric_cols = [col for col in df.columns if is_float_column(df[col])]
df = df[numeric_cols]
print("删非数字列后:", df.shape)

# 3. 全部转成数值型
df = df.apply(pd.to_numeric, errors="coerce")

# 4. 删除方差为 0 的列（所有值都一样的列）
selector = VarianceThreshold(threshold=0.0)
selector.fit(df)

selected_cols = df.columns[selector.get_support()]
df_clean = df[selected_cols]

print("删零方差列后:", df_clean.shape)

# 5. 不删行，直接保存
df_clean.to_csv("describe_word_cleaned.csv", index=False)

print("已保存: describe_word_cleaned.csv")