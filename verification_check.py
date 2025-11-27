# verification_check.py
import os

print("="*70)
print("🔍 PRE-FLIGHT VERIFICATION")
print("="*70)

checks = {
    "routes/geographic_routes.py": False,
    "templates/prediction_geographic.html": False,
    "templates/prediction_geographic_results.html": False,
    "static/css/geographic_style.css": False,
    "static/js/geographic.js": False,
    "models/model.pkl": False,
    "models/encoders.pkl": False,
    "models/metadata.json": False,
}

print("\n📁 Checking files...")
for file_path, _ in checks.items():
    exists = os.path.exists(file_path)
    checks[file_path] = exists
    status = "✅" if exists else "❌"
    print(f"{status} {file_path}")

missing = [f for f, exists in checks.items() if not exists]

print("\n" + "="*70)
if missing:
    print("❌ MISSING FILES:")
    for f in missing:
        print(f"   • {f}")
    print("\n⚠️  Please add these files before testing!")
else:
    print("✅ ALL FILES PRESENT!")
    print("\n🚀 Ready to start the server!")
print("="*70)