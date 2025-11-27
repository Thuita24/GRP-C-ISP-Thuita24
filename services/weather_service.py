# services/weather_service.py

import requests
from datetime import date, timedelta


class WeatherService:
    """
    Weather service for Kenyan cotton regions using Open-Meteo Historical API.

    It fetches multi-year daily data and aggregates it into:
    - average growing-season temperature
    - typical monthly rainfall
    - annual rainfall
    - average solar radiation
    - estimated dewpoint

    If the API fails, it falls back to static, literature-based values.
    """

    BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

    # Kenyan cotton regions: coordinates + default agronomic assumptions
    REGION_META = {
        "kenya_busia": {
            "name": "Kenya - Busia County",
            "lat": 0.4347,
            "lon": 34.2422,
            "soil_type": "Red",
            "irrigation": 15,
            "prev_yield": 1.8,
        },
        "kenya_bungoma": {
            "name": "Kenya - Bungoma County",
            "lat": 0.5692,
            "lon": 34.5584,
            "soil_type": "Red",
            "irrigation": 12,
            "prev_yield": 1.9,
        },
        "kenya_kakamega": {
            "name": "Kenya - Kakamega County",
            "lat": 0.2842,
            "lon": 34.7526,
            "soil_type": "Red",
            "irrigation": 10,
            "prev_yield": 2.0,
        },
        "kenya_homabay": {
            "name": "Kenya - Homa Bay County",
            "lat": -0.5273,
            "lon": 34.4571,
            "soil_type": "Red",
            "irrigation": 20,
            "prev_yield": 1.7,
        },
        "kenya_migori": {
            "name": "Kenya - Migori County",
            "lat": -1.0674,
            "lon": 34.4730,
            "soil_type": "Red",
            "irrigation": 18,
            "prev_yield": 1.8,
        },
        "kenya_siaya": {
            "name": "Kenya - Siaya County",
            "lat": 0.0607,
            "lon": 34.2885,
            "soil_type": "Red",
            "irrigation": 15,
            "prev_yield": 1.8,
        },
        "kenya_machakos": {
            "name": "Kenya - Machakos County",
            "lat": -1.5181,
            "lon": 37.2634,
            "soil_type": "Red",
            "irrigation": 35,
            "prev_yield": 1.3,
        },
        "kenya_makueni": {
            "name": "Kenya - Makueni County",
            "lat": -2.1943,
            "lon": 37.6140,
            "soil_type": "Red",
            "irrigation": 40,
            "prev_yield": 1.2,
        },
        "kenya_kitui": {
            "name": "Kenya - Kitui County",
            "lat": -1.3664,
            "lon": 38.0106,
            "soil_type": "Red",
            "irrigation": 60,
            "prev_yield": 1.0,
        },
        "kenya_baringo": {
            "name": "Kenya - Baringo County",
            "lat": 0.8552,
            "lon": 35.2698,
            "soil_type": "Black",
            "irrigation": 38,
            "prev_yield": 1.4,
        },
        "kenya_westpokot": {
            "name": "Kenya - West Pokot County",
            "lat": 1.3050,
            "lon": 35.2698,
            "soil_type": "Red",
            "irrigation": 32,
            "prev_yield": 1.5,
        },
        "kenya_kwale": {
            "name": "Kenya - Kwale County",
            "lat": -4.1730,
            "lon": 39.4521,
            "soil_type": "Laterite",
            "irrigation": 25,
            "prev_yield": 1.6,
        },
        "kenya_kilifi": {
            "name": "Kenya - Kilifi County",
            "lat": -3.5107,
            "lon": 39.9093,
            "soil_type": "Laterite",
            "irrigation": 28,
            "prev_yield": 1.5,
        },
    }

    # Static fallback examples (your original manual values)
    FALLBACK_EXAMPLES = {
        "kenya_busia": {
            "name": "Kenya - Busia County",
            "temp_c": "24", "dewpoint_c": "20", "precip_mm": "110", "solar_rad": "17",
            "annual_rain": "1300", "rain_cv": "18", "soil_type": "Red",
            "irrigation": "15", "prev_yield": "1.8"
        },
        "kenya_bungoma": {
            "name": "Kenya - Bungoma County",
            "temp_c": "23", "dewpoint_c": "19", "precip_mm": "120", "solar_rad": "17",
            "annual_rain": "1400", "rain_cv": "16", "soil_type": "Red",
            "irrigation": "12", "prev_yield": "1.9"
        },
        "kenya_kakamega": {
            "name": "Kenya - Kakamega County",
            "temp_c": "23", "dewpoint_c": "20", "precip_mm": "130", "solar_rad": "16",
            "annual_rain": "1500", "rain_cv": "15", "soil_type": "Red",
            "irrigation": "10", "prev_yield": "2.0"
        },
        "kenya_homabay": {
            "name": "Kenya - Homa Bay County",
            "temp_c": "25", "dewpoint_c": "20", "precip_mm": "90", "solar_rad": "18",
            "annual_rain": "1100", "rain_cv": "20", "soil_type": "Red",
            "irrigation": "20", "prev_yield": "1.7"
        },
        "kenya_migori": {
            "name": "Kenya - Migori County",
            "temp_c": "24", "dewpoint_c": "20", "precip_mm": "95", "solar_rad": "17",
            "annual_rain": "1200", "rain_cv": "18", "soil_type": "Red",
            "irrigation": "18", "prev_yield": "1.8"
        },
        "kenya_siaya": {
            "name": "Kenya - Siaya County",
            "temp_c": "24", "dewpoint_c": "21", "precip_mm": "100", "solar_rad": "17",
            "annual_rain": "1250", "rain_cv": "17", "soil_type": "Red",
            "irrigation": "15", "prev_yield": "1.8"
        },
        "kenya_machakos": {
            "name": "Kenya - Machakos County",
            "temp_c": "22", "dewpoint_c": "16", "precip_mm": "55", "solar_rad": "19",
            "annual_rain": "650", "rain_cv": "28", "soil_type": "Red",
            "irrigation": "35", "prev_yield": "1.3"
        },
        "kenya_makueni": {
            "name": "Kenya - Makueni County",
            "temp_c": "23", "dewpoint_c": "15", "precip_mm": "50", "solar_rad": "20",
            "annual_rain": "600", "rain_cv": "30", "soil_type": "Red",
            "irrigation": "40", "prev_yield": "1.2"
        },
        "kenya_kitui": {
            "name": "Kenya - Kitui County",
            "temp_c": "26", "dewpoint_c": "14", "precip_mm": "35", "solar_rad": "21",
            "annual_rain": "450", "rain_cv": "35", "soil_type": "Red",
            "irrigation": "60", "prev_yield": "1.0"
        },
        "kenya_baringo": {
            "name": "Kenya - Baringo County",
            "temp_c": "27", "dewpoint_c": "16", "precip_mm": "60", "solar_rad": "20",
            "annual_rain": "700", "rain_cv": "27", "soil_type": "Black",
            "irrigation": "38", "prev_yield": "1.4"
        },
        "kenya_westpokot": {
            "name": "Kenya - West Pokot County",
            "temp_c": "25", "dewpoint_c": "15", "precip_mm": "65", "solar_rad": "19",
            "annual_rain": "750", "rain_cv": "25", "soil_type": "Red",
            "irrigation": "32", "prev_yield": "1.5"
        },
        "kenya_kwale": {
            "name": "Kenya - Kwale County",
            "temp_c": "26", "dewpoint_c": "22", "precip_mm": "85", "solar_rad": "18",
            "annual_rain": "1000", "rain_cv": "22", "soil_type": "Laterite",
            "irrigation": "25", "prev_yield": "1.6"
        },
        "kenya_kilifi": {
            "name": "Kenya - Kilifi County",
            "temp_c": "27", "dewpoint_c": "23", "precip_mm": "80", "solar_rad": "19",
            "annual_rain": "950", "rain_cv": "24", "soil_type": "Laterite",
            "irrigation": "28", "prev_yield": "1.5"
        },
    }

    @classmethod
    def get_region_meta(cls, region_key: str) -> dict:
        if region_key not in cls.REGION_META:
            raise KeyError(f"Unknown region key: {region_key}")
        return cls.REGION_META[region_key]

    @classmethod
    def fetch_historical_climate(cls, region_key: str, years: int = 10) -> dict:
        """
        Fetch multi-year historical daily data from Open-Meteo and aggregate.

        Uses /v1/archive with daily variables:
        - temperature_2m_mean
        - precipitation_sum
        - shortwave_radiation_sum

        Returns a dict with numeric values.
        """
        meta = cls.get_region_meta(region_key)

        end_date = date.today() - timedelta(days=1)
        start_date = date(end_date.year - years + 1, 1, 1)

        params = {
            "latitude": meta["lat"],
            "longitude": meta["lon"],
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily": "temperature_2m_mean,precipitation_sum,shortwave_radiation_sum",
            "timezone": "Africa/Nairobi",
        }

        resp = requests.get(cls.BASE_URL, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        daily = data.get("daily", {})
        temps = daily.get("temperature_2m_mean", [])
        precips = daily.get("precipitation_sum", [])
        solar = daily.get("shortwave_radiation_sum", [])

        if not temps or not precips or not solar:
            raise ValueError("Incomplete climate data from Open-Meteo")

        avg_temp = sum(temps) / len(temps)
        total_precip = sum(precips)
        avg_solar = sum(solar) / len(solar)

        # Approximate long-term annual rainfall (mm/year) over the chosen period
        annual_rain = total_precip / float(years)
        monthly_rain = annual_rain / 12.0

        # Simple dewpoint estimate: a few degrees below air temperature
        dewpoint = avg_temp - 5.0

        return {
            "temp_c": round(avg_temp, 1),
            "dewpoint_c": round(dewpoint, 1),
            "precip_mm": round(monthly_rain, 1),   # typical monthly rainfall
            "solar_rad": round(avg_solar, 1),      # MJ/m² per day (approx)
            "annual_rain": round(annual_rain, 1),
            "rain_cv": 20.0,                       # default coefficient of variation
        }

    @classmethod
    def build_example_payload(cls, region_key: str) -> dict:
        """
        Build the form_data example dict expected by prediction_geographic.html.

        First tries Open-Meteo; if anything fails, falls back to static values.
        """
        # If the region key is unknown, fall back to Busia
        if region_key not in cls.REGION_META:
            region_key = "kenya_busia"

        meta = cls.REGION_META[region_key]

        try:
            climate = cls.fetch_historical_climate(region_key)
            temp_c = climate["temp_c"]
            dewpoint_c = climate["dewpoint_c"]
            precip_mm = climate["precip_mm"]
            solar_rad = climate["solar_rad"]
            annual_rain = climate["annual_rain"]
            rain_cv = climate["rain_cv"]
        except Exception as e:
            print(f"⚠  WeatherService: Falling back to static values for {region_key}: {e}")
            fallback = cls.FALLBACK_EXAMPLES[region_key]
            return fallback

        return {
            "name": meta["name"],
            "temp_c": str(temp_c),
            "dewpoint_c": str(dewpoint_c),
            "precip_mm": str(precip_mm),
            "solar_rad": str(solar_rad),
            "annual_rain": str(annual_rain),
            "rain_cv": str(rain_cv),
            "soil_type": meta["soil_type"],
            "irrigation": str(meta["irrigation"]),
            "prev_yield": str(meta["prev_yield"]),
        }