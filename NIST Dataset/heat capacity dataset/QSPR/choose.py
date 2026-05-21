import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.impute import SimpleImputer
from mlxtend.feature_selection import SequentialFeatureSelector as SFS

# === 1. 读取数据 ===
df = pd.read_csv('describe_word_cleaned.csv')

# === 2. 划分特征与目标 ===
# 前面所有列是描述符，最后一列是目标值
X = df.iloc[:, :-1]
y = df.iloc[:, -1]

# === 3. 强制转成数值 ===
X = X.apply(pd.to_numeric, errors='coerce')
y = pd.to_numeric(y, errors='coerce')

# === 4. 只删除目标值缺失的样本 ===
valid_y_mask = ~y.isna()
X = X.loc[valid_y_mask].copy()
y = y.loc[valid_y_mask].copy()

print(f"目标值非缺失的样本数: {len(X)}")

# === 5. 对特征缺失值做均值填补，不删行 ===
imputer = SimpleImputer(strategy='mean')
X_imputed = pd.DataFrame(
    imputer.fit_transform(X),
    columns=X.columns,
    index=X.index
)

print(f"可用于筛选的样本数: {len(X_imputed)}")
print(f"初始描述符数量: {X_imputed.shape[1]}")

# === 6. 构建线性回归模型 ===
lr = LinearRegression()

# === 7. 前向选择 25 个最优特征 ===
sfs = SFS(
    lr,
    k_features=25,
    forward=True,
    floating=False,
    scoring='r2',
    cv=5,
    n_jobs=-1
)

sfs = sfs.fit(X_imputed, y)

# === 8. 获取选出的列名 ===
selected_features = list(sfs.k_feature_names_)
print("\nTop 25 descriptors selected:")
for feat in selected_features:
    print(feat)

# === 9. 保存筛选后的结果 ===
target_col = df.columns[-1]
df_selected = pd.concat([X_imputed[selected_features], y.rename(target_col)], axis=1)
df_selected.to_excel('selected_25_descriptors.xlsx', index=False)

print("\n已保存到: selected_25_descriptors.xlsx")