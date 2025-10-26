import joblib
import numpy as np
import pandas as pd
import warnings

# Suppress scikit-learn version warnings (model still works fine)
warnings.filterwarnings('ignore', category=UserWarning)

print(" Testing New Cotton Yield Model v2.0")
print("=" * 60)

# Load new model
model = joblib.load('models/cotton_yield_model.pkl')

print(f"\n Model loaded successfully!")
print(f"   Model type: {type(model).__name__}")
print(f"   Features expected: {model.n_features_in_}")
print(f"   Number of trees: {model.n_estimators}")

# Feature names (must match training order)
feature_names = [
    'temp_c_mean',
    'dewpoint_c_mean',
    'precip_mm_mean',
    'precip_mm_sum',
    'ssrd_MJm2_mean',
    'year_index',
    'yield_lag1',
    'season_Rabi'
]

print(f"\n Expected features:")
for i, name in enumerate(feature_names, 1):
    print(f"   {i}. {name}")

# Test prediction with sample data (using DataFrame to avoid warnings)
print(f"\n Test Prediction:")
print(f"   Scenario: Kharif 2024, Moderate climate, Previous yield 2.5")

sample_data = pd.DataFrame([[
    25.5,  # temp_c_mean (°C)
    20.0,  # dewpoint_c_mean (°C)
    5.5,   # precip_mm_mean (mm/day)
    600,   # precip_mm_sum (mm total)
    18.5,  # ssrd_MJm2_mean (MJ/m²)
    24,    # year_index (2024 - 2000 = 24)
    2.5,   # yield_lag1 (previous year yield)
    0      # season_Rabi (0 = Kharif, 1 = Rabi)
]], columns=feature_names)

prediction = model.predict(sample_data)

print(f"\n Predicted Yield: {prediction[0]:.2f} bales/ha")

# Test multiple scenarios
print(f"\n Multiple Scenario Tests:")
print(f"{'Scenario':<25} {'Temp':>6} {'Rain':>6} {'Lag':>6} {'Prediction':>12}")
print("-" * 60)

scenarios = [
    ("Excellent conditions", 24.0, 700, 3.0, 0),
    ("Good conditions", 25.5, 600, 2.5, 0),
    ("Average conditions", 27.0, 500, 2.0, 0),
    ("Drought conditions", 29.0, 300, 1.5, 0),
    ("Rabi season (winter)", 22.0, 400, 2.8, 1),
]

for scenario_name, temp, rain, lag, season in scenarios:
    test_input = pd.DataFrame([[
        temp, 20.0, rain/120, rain, 18.5, 24, lag, season
    ]], columns=feature_names)
    
    pred = model.predict(test_input)[0]
    print(f"{scenario_name:<25} {temp:>6.1f} {rain:>6.0f} {lag:>6.1f} {pred:>12.2f}")

print("\n" + "=" * 60)
print(" Model testing complete - Ready for Flask integration!")