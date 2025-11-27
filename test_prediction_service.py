from services.prediction_service import PredictionService
import json

print("Testing Prediction Service")
print("=" * 70)

# Initialize service
service = PredictionService()

print("\n Prediction service initialized")
print(f"   Model loaded: {type(service.model).__name__}")
print(f"   Features: {len(service.feature_names)}")

# Test 1: Make a prediction for upcoming season
print("\n" + "=" * 70)
print("Test 1: Predict Yield for Upcoming Season")
print("=" * 70)

try:
    prediction = service.predict_yield(
        state="1. Andhra Pradesh",
        district="Anantapur",
        season="Kharif",
        year=2025
    )
    
    print(f"\nPrediction successful!")
    print(f"\nPREDICTED YIELD: {prediction['predicted_yield']} bales/ha")
    print(f"\nConfidence Interval:")
    print(f"   Lower bound: {prediction['confidence_interval']['lower']} bales/ha")
    print(f"   Upper bound: {prediction['confidence_interval']['upper']} bales/ha")
    
    print(f"\nClimate Conditions Used:")
    climate = prediction['input_data']['climate']
    print(f"   Temperature: {climate['temperature']}°C")
    print(f"   Total Rainfall: {climate['rainfall_total']} mm")
    print(f"   Avg Daily Rain: {climate['rainfall_avg']} mm/day")
    print(f"   Solar Radiation: {climate['solar_radiation']} MJ/m²")
    print(f"   Data Source: {climate['source']}")
    
    print(f"\nPrevious Year:")
    print(f"   2024 Yield: {prediction['input_data']['previous_year_yield']} bales/ha")
    
    print(f"\n Full Prediction Data:")
    print(json.dumps(prediction, indent=2))
    
except Exception as e:
    print(f"\n Prediction failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Multiple predictions
print("\n" + "=" * 70)
print(" Test 2: Multiple District Predictions")
print("=" * 70)

test_cases = [
    ("1. Andhra Pradesh", "Guntur", "Kharif", 2025),
    ("11. Maharashtra", "Akola", "Kharif", 2025),
    ("4. Gujarat", "Rajkot", "Rabi", 2025),
]

print(f"\n{'District':<20} {'Season':<10} {'Predicted Yield':<20} {'Confidence'}")
print("-" * 70)

for state, district, season, year in test_cases:
    try:
        pred = service.predict_yield(state, district, season, year)
        ci = pred['confidence_interval']
        print(f"{district:<20} {season:<10} {pred['predicted_yield']:<20} [{ci['lower']:.2f} - {ci['upper']:.2f}]")
    except Exception as e:
        print(f"{district:<20} {season:<10} ERROR: {str(e)[:30]}")

# Test 3: Get historical average for comparison
print("\n" + "=" * 70)
print(" Test 3: Compare with Historical Average")
print("=" * 70)

try:
    prediction = service.predict_yield("1. Andhra Pradesh", "Anantapur", "Kharif", 2025)
    historical_avg = service.get_district_average_yield("1. Andhra Pradesh", "Anantapur", "Kharif")
    
    print(f"\n   District: Anantapur, Andhra Pradesh (Kharif)")
    print(f"   Historical Average: {historical_avg:.2f} bales/ha")
    print(f"   2025 Prediction: {prediction['predicted_yield']} bales/ha")
    
    difference = prediction['predicted_yield'] - historical_avg
    percent_change = (difference / historical_avg) * 100
    
    print(f"\n   Difference: {difference:+.2f} bales/ha ({percent_change:+.1f}%)")
    
    if difference > 0:
        print(f"    Prediction is HIGHER than historical average")
    else:
        print(f"   Prediction is LOWER than historical average")
        
except Exception as e:
    print(f"\nComparison failed: {e}")

print("\n" + "=" * 70)
print("Prediction service testing complete!")
print("=" * 70)