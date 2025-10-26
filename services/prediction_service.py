import joblib
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime
from services.weather_service import WeatherService

class PredictionService:
    """
    Cotton yield prediction service
    Combines ML model, weather data, and historical yields
    """
    
    def __init__(self, model_path='models/cotton_yield_model.pkl', db_path='cotton_app.db'):
        """Initialize the prediction service"""
        self.model = joblib.load(model_path)
        self.db_path = db_path
        self.base_year = 2000
        
        # Feature names (must match training order)
        self.feature_names = [
            'temp_c_mean',
            'dewpoint_c_mean',
            'precip_mm_mean',
            'precip_mm_sum',
            'ssrd_MJm2_mean',
            'year_index',
            'yield_lag1',
            'season_Rabi'
        ]
    
    def get_last_year_yield(self, state, district, season, year):
        """
        Get previous year's yield for the same district and season
        Used as the yield_lag1 feature
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Try to get exact previous year
        cursor.execute("""
            SELECT actual_yield 
            FROM historical_yields 
            WHERE state = ? AND district = ? AND season = ? AND year = ?
        """, (state, district, season, year - 1))
        
        result = cursor.fetchone()
        
        if result:
            conn.close()
            return result[0]
        
        # Fallback: Get average of last 3 years
        cursor.execute("""
            SELECT AVG(actual_yield)
            FROM historical_yields 
            WHERE state = ? AND district = ? AND season = ? 
              AND year BETWEEN ? AND ?
            LIMIT 3
        """, (state, district, season, year - 3, year - 1))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            return result[0]
        
        # Final fallback: District-season average
        return self.get_district_average_yield(state, district, season)
    
    def get_district_average_yield(self, state, district, season):
        """Get historical average yield for a district-season"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT AVG(actual_yield)
            FROM historical_yields
            WHERE state = ? AND district = ? AND season = ?
        """, (state, district, season))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0]:
            return result[0]
        
        # Ultimate fallback: state-season average
        return self.get_state_average_yield(state, season)
    
    def get_state_average_yield(self, state, season):
        """Get historical average yield for a state-season"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT AVG(actual_yield)
            FROM historical_yields
            WHERE state = ? AND season = ?
        """, (state, season))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result and result[0] else 2.0  # Default fallback
    
    def predict_yield(self, state, district, season, year, climate_data=None):
        """
        Predict cotton yield for a given location, season, and year
        
        Parameters:
        - state: State name
        - district: District name
        - season: "Kharif" or "Rabi"
        - year: Year for prediction
        - climate_data: Optional dict with climate data. If None, will fetch from API
        
        Returns:
        - dict with prediction and metadata
        """
        
        # Get climate data if not provided
        if climate_data is None:
            climate_data = WeatherService.get_forecast_seasonal_climate(
                state, district, season, year
            )
        
        if not climate_data:
            raise ValueError("Could not retrieve climate data")
        
        # Get previous year's yield
        yield_lag1 = self.get_last_year_yield(state, district, season, year)
        
        # Calculate year_index
        year_index = year - self.base_year
        
        # Create season dummy (1 for Rabi, 0 for Kharif)
        season_rabi = 1 if season == "Rabi" else 0
        
        # Prepare feature vector
        features = pd.DataFrame([[
            climate_data['temp_c_mean'],
            climate_data['dewpoint_c_mean'],
            climate_data['precip_mm_mean'],
            climate_data['precip_mm_sum'],
            climate_data['ssrd_MJm2_mean'],
            year_index,
            yield_lag1,
            season_rabi
        ]], columns=self.feature_names)
        
        # Make prediction
        predicted_yield = self.model.predict(features)[0]
        
        # Calculate confidence interval (simple approach using model's estimators)
        predictions = np.array([tree.predict(features)[0] for tree in self.model.estimators_])
        std_dev = predictions.std()
        confidence_interval = (
            max(0, predicted_yield - 1.96 * std_dev),  # Lower bound (95% CI)
            predicted_yield + 1.96 * std_dev            # Upper bound
        )
        
        # Prepare result
        result = {
            'predicted_yield': round(predicted_yield, 2),
            'confidence_interval': {
                'lower': round(confidence_interval[0], 2),
                'upper': round(confidence_interval[1], 2)
            },
            'input_data': {
                'state': state,
                'district': district,
                'season': season,
                'year': year,
                'climate': {
                    'temperature': round(climate_data['temp_c_mean'], 2),
                    'dewpoint': round(climate_data['dewpoint_c_mean'], 2),
                    'rainfall_total': round(climate_data['precip_mm_sum'], 2),
                    'rainfall_avg': round(climate_data['precip_mm_mean'], 2),
                    'solar_radiation': round(climate_data['ssrd_MJm2_mean'], 2),
                    'source': climate_data.get('source', 'API')
                },
                'previous_year_yield': round(yield_lag1, 2)
            },
            'metadata': {
                'model_version': '2.0',
                'prediction_date': datetime.now().isoformat(),
                'base_year': self.base_year
            }
        }
        
        return result
    
    def save_prediction(self, user_id, prediction_result):
        """
        Save prediction to database for history tracking
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        import json
        
        cursor.execute("""
            INSERT INTO prediction_history 
            (user_id, state, district, season, year, predicted_yield, climate_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            user_id,
            prediction_result['input_data']['state'],
            prediction_result['input_data']['district'],
            prediction_result['input_data']['season'],
            prediction_result['input_data']['year'],
            prediction_result['predicted_yield'],
            json.dumps(prediction_result['input_data']['climate'])
        ))
        
        conn.commit()
        prediction_id = cursor.lastrowid
        conn.close()
        
        return prediction_id
    
    def get_user_predictions(self, user_id, limit=10):
        """
        Get user's prediction history
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, state, district, season, year, predicted_yield, created_at
            FROM prediction_history
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
        
        predictions = []
        for row in cursor.fetchall():
            predictions.append({
                'id': row[0],
                'state': row[1],
                'district': row[2],
                'season': row[3],
                'year': row[4],
                'predicted_yield': row[5],
                'created_at': row[6]
            })
        
        conn.close()
        return predictions