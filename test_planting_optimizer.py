import warnings
warnings.filterwarnings('ignore', category=UserWarning)

from services.planting_optimizer import PlantingOptimizer
import json

print(" Testing Optimal Planting Time Optimizer")
print("=" * 70)

# Initialize optimizer
optimizer = PlantingOptimizer()

print("\n Planting optimizer initialized")

# Test 1: Find optimal planting time for Kharif season
print("\n" + "=" * 70)
print(" Test 1: Optimal Planting Time - Kharif Season")
print("=" * 70)

try:
    result = optimizer.find_optimal_planting_time(
        state="1. Andhra Pradesh",
        district="Anantapur",
        season="Kharif",
        year=2025
    )
    
    print(f"\n RECOMMENDATION:")
    print(f"   {result['recommendation']['summary']}")
    print(f"\n Optimal Planting Window:")
    print(f"   Period: {result['recommendation']['optimal_period']}")
    print(f"   Dates: {result['recommendation']['dates']}")
    print(f"   Expected Yield: {result['recommendation']['expected_yield']} bales/ha")
    print(f"   Confidence: {result['confidence_level']}")
    
    print(f"\n Reasoning:")
    for reason in result['recommendation']['reasoning']:
        print(f"   • {reason}")
    
    print(f"\n Comparison of All Planting Windows:")
    print(f"   {'Window':<25} {'Yield':<15} {'Difference':<15} {'Status'}")
    print(f"   {'-'*70}")
    
    for window_name, window_data in result['all_windows'].items():
        status = " OPTIMAL" if window_data['is_optimal'] else ""
        diff = window_data['difference_from_optimal']
        diff_str = f"{diff:+.2f}" if diff != 0 else "baseline"
        
        print(f"   {window_data['window']:<25} {window_data['predicted_yield']:<15.2f} {diff_str:<15} {status}")
    
except Exception as e:
    print(f"\n Optimization failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Rabi season
print("\n" + "=" * 70)
print(" Test 2: Optimal Planting Time - Rabi Season")
print("=" * 70)

try:
    result = optimizer.find_optimal_planting_time(
        state="4. Gujarat",
        district="Rajkot",
        season="Rabi",
        year=2025
    )
    
    print(f"\n RECOMMENDATION:")
    print(f"   {result['recommendation']['summary']}")
    print(f"\n📅 Best Window: {result['recommendation']['optimal_period']}")
    print(f"   Expected Yield: {result['recommendation']['expected_yield']} bales/ha")
    
    print(f"\nAll Windows:")
    for window_name, window_data in result['all_windows'].items():
         marker = "⭐" if window_data['is_optimal'] else "  "
         print(f"   {marker} {window_data['window']:<25} {window_data['predicted_yield']:.2f} bales/ha")
except Exception as e:
    print(f"\n Optimization failed: {e}")

# Test 3: Multiple districts comparison
print("\n" + "=" * 70)
print("Test 3: Compare Optimal Times Across Districts")
print("=" * 70)

test_districts = [
    ("1. Andhra Pradesh", "Anantapur", "Kharif"),
    ("1. Andhra Pradesh", "Guntur", "Kharif"),
    ("11. Maharashtra", "Akola", "Kharif"),
]

print(f"\n{'District':<20} {'Optimal Window':<25} {'Expected Yield'}")
print("-" * 70)

for state, district, season in test_districts:
    try:
        result = optimizer.find_optimal_planting_time(state, district, season, 2025)
        optimal = result['optimal_window_info']
        print(f"{district:<20} {optimal['window']:<25} {optimal['predicted_yield']:.2f} bales/ha")
    except Exception as e:
        print(f"{district:<20} ERROR: {str(e)[:40]}")

print("\n" + "=" * 70)
print(" Planting optimizer testing complete!")
print("=" * 70)