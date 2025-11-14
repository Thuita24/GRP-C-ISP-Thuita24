from services.weather_service import WeatherService
import json

print(" Testing Weather Service")
print("=" * 60)

# Test 1: Geocoding - Get coordinates for a district
print("\n Test 1: Get District Coordinates")
coords = WeatherService.get_district_coordinates("Andhra Pradesh", "Anantapur")
print(f"   Anantapur coordinates: {coords}")

# Test 2: Fetch historical climate data
print("\n Test 2: Fetch Historical Climate Data")
print("   Fetching Anantapur Kharif 2023 climate data...")
try:
    climate = WeatherService.get_seasonal_climate(
        state="Andhra Pradesh",
        district="Anantapur",
        season="Kharif",
        year=2023
    )
    
    if climate:
        print(f"    Successfully retrieved climate data!")
        print(f"\n   Climate Data:")
        print(f"   - Temperature: {climate['temp_c_mean']:.2f}°C")
        print(f"   - Dewpoint: {climate['dewpoint_c_mean']:.2f}°C")
        print(f"   - Total Rainfall: {climate['precip_mm_sum']:.2f} mm")
        print(f"   - Avg Daily Rain: {climate['precip_mm_mean']:.2f} mm/day")
        print(f"   - Solar Radiation: {climate['ssrd_MJm2_mean']:.2f} MJ/m²")
        print(f"   - Source: {climate.get('source', 'Open-Meteo API')}")
    else:
        print("    No climate data returned")
        
except Exception as e:
    print(f"    Error: {e}")

# Test 3: Test forecast method (for upcoming season)
print("\n Test 3: Get Forecast Climate Data")
print("   Getting forecast for Anantapur Kharif 2025...")
try:
    forecast = WeatherService.get_forecast_seasonal_climate(
        state="Andhra Pradesh",
        district="Anantapur",
        season="Kharif",
        year=2025
    )
    
    if forecast:
        print(f"    Successfully retrieved forecast!")
        print(f"\n   Forecast Data:")
        print(f"   - Temperature: {forecast['temp_c_mean']:.2f}°C")
        print(f"   - Total Rainfall: {forecast['precip_mm_sum']:.2f} mm")
        print(f"   - Source: {forecast.get('source', 'Unknown')}")
    else:
        print("   No forecast data returned")
        
except Exception as e:
    print(f"    Error: {e}")

# Test 4: Test multiple districts
print("\nTest 4: Test Multiple Districts")
test_districts = [
    ("Andhra Pradesh", "Guntur"),
    ("Maharashtra", "Akola"),
    ("Gujarat", "Rajkot"),
]

for state, district in test_districts:
    try:
        coords = WeatherService.get_district_coordinates(state, district)
        print(f"   {district}, {state}: {coords['lat']:.2f}, {coords['lon']:.2f}")
    except Exception as e:
        print(f"    {district}, {state}: {e}")

print("\n" + "=" * 60)
print("Weather service testing complete!")