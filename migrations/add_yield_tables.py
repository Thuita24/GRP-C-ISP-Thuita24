# This adds the necessary tables to your existing cotton_app.db

import sqlite3

def upgrade_database():
    conn = sqlite3.connect('cotton_app.db')
    cursor = conn.cursor()
    
    # Table 1: Historical Yields (from your merged dataset)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historical_yields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state TEXT NOT NULL,
            district TEXT NOT NULL,
            season TEXT NOT NULL,
            year INTEGER NOT NULL,
            actual_yield REAL NOT NULL,
            temp_c_mean REAL,
            dewpoint_c_mean REAL,
            precip_mm_mean REAL,
            precip_mm_sum REAL,
            ssrd_MJm2_mean REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(state, district, season, year)
        )
    ''')
    
    # Table 2: Prediction History (for logged-in farmers)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prediction_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            state TEXT NOT NULL,
            district TEXT NOT NULL,
            season TEXT NOT NULL,
            year INTEGER NOT NULL,
            predicted_yield REAL NOT NULL,
            climate_data TEXT,
            planting_window TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Table 3: Optimal Planting Recommendations
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS planting_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            state TEXT NOT NULL,
            district TEXT NOT NULL,
            season TEXT NOT NULL,
            year INTEGER NOT NULL,
            recommended_window TEXT NOT NULL,
            early_yield REAL,
            mid_yield REAL,
            late_yield REAL,
            confidence_level TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create indexes for faster queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_historical_state_district ON historical_yields(state, district)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_historical_year ON historical_yields(year)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_prediction_user ON prediction_history(user_id)')
    
    conn.commit()
    conn.close()
    print("Database tables created successfully!")

if __name__ == '__main__':
    upgrade_database()