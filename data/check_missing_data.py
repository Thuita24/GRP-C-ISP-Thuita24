import pandas as pd

df = pd.read_csv('data/merged_dataset.csv')

print(" Missing Data Analysis\n")
print(f"Total rows: {len(df)}")
print("\n Missing values per column:")
print(df.isnull().sum())

print("\n Missing percentage:")
for col in df.columns:
    missing_pct = (df[col].isnull().sum() / len(df)) * 100
    if missing_pct > 0:
        print(f"   {col}: {missing_pct:.2f}%")

# Check critical columns specifically
critical_cols = ['State', 'District', 'Season', 'HarvestYear', 'Yield_bales_per_ha',
                 'temp_c_mean', 'dewpoint_c_mean', 'precip_mm_mean', 
                 'precip_mm_sum', 'ssrd_MJm2_mean']

print("\n Rows with ANY missing critical data:")
missing_any = df[critical_cols].isnull().any(axis=1)
print(f"   {missing_any.sum()} rows ({(missing_any.sum()/len(df)*100):.1f}%)")

print("\n Complete rows (no missing data):")
complete_rows = df[critical_cols].dropna()
print(f"   {len(complete_rows)} rows ({(len(complete_rows)/len(df)*100):.1f}%)")

# Show which columns have the most missing data
print("\n Most problematic columns:")
missing_counts = df[critical_cols].isnull().sum().sort_values(ascending=False)
print(missing_counts[missing_counts > 0])