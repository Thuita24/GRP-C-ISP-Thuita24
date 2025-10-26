import requests
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json

class WeatherService:
    """
    Fetches climate data from Open-Meteo API (free, no API key needed)
    """
    
    BASE_URL = "https://archive-api.open-meteo.com/v1/archive"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    
    # Coordinates for major cotton-growing districts (sample - expand this)
    DISTRICT_COORDS = {
        "Guntur": {"lat": 16.3067, "lon": 80.4365},
        "Krishna": {"lat": 16.5, "lon": 80.5},
        "Kadapa": {"lat": 14.4673, "lon": 78.8242},
        # Add coordinates for all 454 districts
        # You can use a geocoding service to get these automatically
    }
    
    @staticmethod
    def get_district_coordinates(state, district):
        """
        Get lat/lon for a district. If not in cache, use geocoding API
        """
        key = f"{district}"
        if key in WeatherService.DISTRICT_COORDS:
            return WeatherService.DISTRICT_COORDS[key]
        else:
            # Fallback: Use Nominatim geocoding (free)
            return WeatherService._geocode_district(state, district)
    
    @staticmethod
    def _geocode_district(state, district):
        """
        Geocode district using Nominatim (backup method)
        """
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": f"{district}, {state}, India",
            "format": "json",
            "limit": 1
        }
        headers = {"User-Agent": "CottonYieldPredictor/1.0"}
        
        try:
            response = requests.get(url, params=params, headers=headers)
            data = response.json()
            if data:
                return {"lat": float(data[0]["lat"]), "lon": float(data[0]["lon"])}
        except:
            pass
        
        # Ultimate fallback: Use state capital coords
        return {"lat": 20.5937, "lon": 78.9629}  # Center of India
    
    @staticmethod
    def get_seasonal_climate(state, district, season, year):
        """
        Get climate averages for entire growing season
        """
        coords = WeatherService.get_district_coordinates(state, district)
        
        # Define season date ranges
        if season == "Kharif":
            start_date = f"{year}-06-01"
            end_date = f"{year}-10-31"
        else:  # Rabi
            start_date = f"{year}-10-01"
            end_date = f"{year+1}-03-31"
        
        params = {
            "latitude": coords["lat"],
            "longitude": coords["lon"],
            "start_date": start_date,
            "end_date": end_date,
            "daily": "temperature_2m_mean,dewpoint_2m_mean,precipitation_sum,shortwave_radiation_sum",
            "timezone": "Asia/Kolkata"
        }
        
        try:
            response = requests.get(WeatherService.BASE_URL, params=params)
            data = response.json()
            
            if "daily" in data:
                # Calculate seasonal averages
                climate_data = {
                    "temp_c_mean": sum(data["daily"]["temperature_2m_mean"]) / len(data["daily"]["temperature_2m_mean"]),
                    "dewpoint_c_mean": sum(data["daily"]["dewpoint_2m_mean"]) / len(data["daily"]["dewpoint_2m_mean"]),
                    "precip_mm_sum": sum(data["daily"]["precipitation_sum"]),
                    "precip_mm_mean": sum(data["daily"]["precipitation_sum"]) / len(data["daily"]["precipitation_sum"]),
                    "ssrd_MJm2_mean": sum(data["daily"]["shortwave_radiation_sum"]) / len(data["daily"]["shortwave_radiation_sum"])
                }
                return climate_data
        except Exception as e:
            print(f"Error fetching weather data: {e}")
            return None
    
    @staticmethod
    def get_forecast_seasonal_climate(state, district, season, year, planting_window="mid"):
        """
        Get forecasted climate for upcoming season
        Uses seasonal forecast + historical averages
        """
        coords = WeatherService.get_district_coordinates(state, district)
        
        # For future predictions, we'll use:
        # 1. Short-term forecast (if available)
        # 2. Historical average for that season as baseline
        # 3. Climate trend adjustment
        
        # Get historical average for this season/district (last 5 years)
        historical_avg = WeatherService._get_historical_baseline(
            state, district, season, year
        )
        
        return historical_avg
    
    @staticmethod
    def _get_historical_baseline(state, district, season, target_year):
        """
        Calculate 5-year historical average as forecast baseline
        """
        import sqlite3
        conn = sqlite3.connect('cotton_app.db')
        cursor = conn.cursor()
        
        query = '''
            SELECT AVG(temp_c_mean), AVG(dewpoint_c_mean), 
                   AVG(precip_mm_mean), AVG(precip_mm_sum), 
                   AVG(ssrd_MJm2_mean)
            FROM historical_yields
            WHERE state = ? AND district = ? AND season = ?
              AND year BETWEEN ? AND ?
        '''
        
        cursor.execute(query, (
            state, district, season, 
            target_year - 5, target_year - 1
        ))
        
        result = cursor.fetchone()
        conn.close()
        
        if result and result[0] is not None:
            return {
                "temp_c_mean": result[0],
                "dewpoint_c_mean": result[1],
                "precip_mm_mean": result[2],
                "precip_mm_sum": result[3],
                "ssrd_MJm2_mean": result[4],
                "source": "5-year historical average"
            }
        else:
            # Fallback to default values if no historical data
            return {
                "temp_c_mean": 28.0,
                "dewpoint_c_mean": 22.0,
                "precip_mm_mean": 5.0,
                "precip_mm_sum": 600.0,
                "ssrd_MJm2_mean": 18.0,
                "source": "default baseline"
            }