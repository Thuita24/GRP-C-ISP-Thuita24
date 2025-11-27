import pandas as pd

# Load the CSV
df = pd.read_csv('data/merged_dataset.csv')

print(f" Before: {df['District'].isna().sum()} missing districts out of {len(df)} rows")

# THIS ONE LINE FIXES EVERYTHING:
df['District'] = df['District'].ffill()

print(f" After: {df['District'].isna().sum()} missing districts")

# Save the fixed file
df.to_csv('data/merged_dataset.csv', index=False)

print("\n Done! Districts filled successfully.")
print("\nFirst 20 rows:")
print(df[['State', 'District', 'Season', 'HarvestYear']].head(20))