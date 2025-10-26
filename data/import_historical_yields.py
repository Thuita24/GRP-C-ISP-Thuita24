import pandas as pd
import sqlite3
from pathlib import Path
import os

def import_merged_dataset(csv_filename='merged_dataset.csv'):
    """
    Import your merged climate + yield dataset into the database
    Updated for your actual column names: State, District, Season, HarvestYear
    """
    # Get the correct paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, csv_filename)
    db_path = os.path.join(os.path.dirname(current_dir), 'cotton_app.db')
    
    print(f" CSV file: {csv_path}")
    print(f" Database: {db_path}")
    
    # Check if CSV exists
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        print(f"   Please place your merged dataset CSV in the 'data' folder")
        return
    
    print("\n Loading merged dataset...")
    try:
        df = pd.read_csv(csv_path)
        print(f"Loaded {len(df)} rows")
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return
    
    # Display dataset info
    print(f"\n Dataset Info:")
    print(f"   Columns: {list(df.columns)}")
    print(f"   Shape: {df.shape}")
    print(f"   Years: {df['HarvestYear'].min()} - {df['HarvestYear'].max()}")
    
    # Clean and prepare data - use actual column names
    print("\n Cleaning data...")
    df['State'] = df['State'].str.strip()
    df['District'] = df['District'].str.strip()
    df['Season'] = df['Season'].str.strip()
    
    # Rename columns to match database schema
    df_renamed = df.rename(columns={
        'State': 'state',
        'District': 'district',
        'Season': 'season',
        'HarvestYear': 'year'
    })
    
    # Check for required columns (after renaming)
    required_columns = [
        'state', 'district', 'season', 'year', 
        'Yield_bales_per_ha',
        'temp_c_mean', 'dewpoint_c_mean', 
        'precip_mm_mean', 'precip_mm_sum', 'ssrd_MJm2_mean'
    ]
    
    missing_columns = [col for col in required_columns if col not in df_renamed.columns]
    if missing_columns:
        print(f" Warning: Missing columns: {missing_columns}")
        print(f"   Available columns: {list(df_renamed.columns)}")
        print("\n   Please check your CSV column names match exactly.")
        return
    
    # Select and rename columns
    df_import = df_renamed[required_columns].copy()
    df_import.rename(columns={'Yield_bales_per_ha': 'actual_yield'}, inplace=True)
    
    # Remove any rows with missing critical data
    initial_count = len(df_import)
    df_import = df_import.dropna(subset=['state', 'district', 'season', 'year', 'actual_yield'])
    final_count = len(df_import)
    
    if initial_count != final_count:
        print(f" Removed {initial_count - final_count} rows with missing critical data")
    
    # Display statistics
    print(f"\n Data Summary:")
    print(f"   Total records: {len(df_import)}")
    print(f"   Unique states: {df_import['state'].nunique()}")
    print(f"   Unique districts: {df_import['district'].nunique()}")
    print(f"   Years covered: {df_import['year'].min()} - {df_import['year'].max()}")
    print(f"   Seasons: {df_import['season'].unique().tolist()}")
    print(f"\n   Yield statistics:")
    print(f"   - Mean: {df_import['actual_yield'].mean():.2f} bales/ha")
    print(f"   - Min: {df_import['actual_yield'].min():.2f} bales/ha")
    print(f"   - Max: {df_import['actual_yield'].max():.2f} bales/ha")
    
    # Sample of data
    print(f"\nSample records:")
    print(df_import.head(3).to_string(index=False))
    
    # Connect to database and import
    print(f"\n Importing to database...")
    try:
        conn = sqlite3.connect(db_path)
        
        # Import to database (replace existing data)
        df_import.to_sql('historical_yields', conn, if_exists='replace', index=False)
        
        # Verify import
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM historical_yields")
        count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f" Successfully imported {count} records to historical_yields table!")
        print(f"\n Import complete! Your database is ready for predictions.")
        
    except Exception as e:
        print(f" Error importing to database: {e}")
        return

if __name__ == '__main__':
    import_merged_dataset()