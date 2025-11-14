from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
import sqlite3
from datetime import datetime
import numpy as np
import joblib
import json

# Add at the top of geographic_routes.py (after imports)

def get_month_name(month_num):
    """Convert month number to name"""
    months = ['January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']
    return months[month_num - 1]


def get_kenya_season(month):
    """Get Kenya season name from month"""
    if month in [3, 4, 5]:
        return 'Long Rains'
    elif month in [10, 11, 12]:
        return 'Short Rains'
    elif month in [1, 2, 6, 7, 8, 9]:
        return 'Dry Season'
    else:
        return 'Transition'


def get_kenya_monthly_rainfall_pattern():
    """
    Kenya's typical monthly rainfall distribution
    Returns percentage of annual rainfall per month
    Based on bimodal pattern: Long rains (Mar-May) and Short rains (Oct-Dec)
    """
    return {
        1: 0.04,   # January - Dry
        2: 0.04,   # February - Dry
        3: 0.12,   # March - Long rains start
        4: 0.16,   # April - Long rains peak ⭐
        5: 0.13,   # May - Long rains end
        6: 0.05,   # June - Dry
        7: 0.04,   # July - Dry (coolest month)
        8: 0.04,   # August - Dry
        9: 0.06,   # September - Transition
        10: 0.11,  # October - Short rains start
        11: 0.14,  # November - Short rains peak ⭐
        12: 0.07   # December - Short rains end
    }


def adjust_climate_for_planting_month(base_data, planting_month):
    """
    Adjust climate parameters based on planting month
    Simulates what weather conditions will be during cotton growth
    
    Args:
        base_data: dict with location characteristics
        planting_month: int (1-12)
    
    Returns:
        dict with adjusted climate for that planting month
    """
    adjusted = base_data.copy()
    annual_rain = base_data['annual_rain']
    
    # Get Kenya rainfall pattern
    rainfall_pattern = get_kenya_monthly_rainfall_pattern()
    
    # Calculate rainfall for next 4 months after planting (critical growing period)
    growing_months = [(planting_month + i - 1) % 12 + 1 for i in range(4)]
    growing_season_rain = sum(annual_rain * rainfall_pattern[m] for m in growing_months)
    
    # Adjust parameters based on planting month
    adjusted['precip_mm'] = growing_season_rain / 4  # Average monthly during growth
    
    # Temperature varies by month in Kenya
    temp_variation = {
        1: 0, 2: 1, 3: 1, 4: 0, 5: -1, 6: -2,  # Jan-Jun
        7: -2, 8: -1, 9: 0, 10: 1, 11: 1, 12: 0  # Jul-Dec
    }
    adjusted['temp_c'] = base_data['temp_c'] + temp_variation.get(planting_month, 0)
    
    # Solar radiation (cloudier during rainy seasons)
    if planting_month in [3, 4, 5, 10, 11, 12]:  # Rainy seasons
        adjusted['solar_rad'] = base_data.get('solar_rad', 17) - 1
    else:  # Dry seasons
        adjusted['solar_rad'] = base_data.get('solar_rad', 17) + 1
    
    # Dewpoint adjusts with rainfall
    adjusted['dewpoint_c'] = adjusted['temp_c'] - (5 if growing_season_rain > 300 else 8)
    
    return adjusted

geographic_bp = Blueprint('geographic', __name__, url_prefix='/geographic')

# Database setup
DATABASE = 'cotton_app.db'

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Load Model B (Geographic)
try:
    model = joblib.load('models/model.pkl')
    encoders = joblib.load('models/encoders.pkl')
    
    with open('models/metadata.json', 'r') as f:
        metadata = json.load(f)
    
    soil_encoder = encoders['soil_encoder']
    soil_classes = list(encoders['soil_classes'])
    
    # Safely get model metrics
    try:
        MODEL_R2 = metadata['performance_metrics']['model_b_geographic']['test_r2']
        MODEL_RMSE = metadata['performance_metrics']['model_b_geographic']['test_rmse']
    except (KeyError, TypeError):
        MODEL_R2 = 0.621
        MODEL_RMSE = 0.772
        print("⚠️  Using default model metrics")
    
    print("✅ Geographic Model (Model B) loaded successfully")
    print(f"   R² Score: {MODEL_R2:.4f}")
    
except Exception as e:
    print(f"❌ Error loading geographic model: {e}")
    model = None
    soil_classes = ['Red', 'Black', 'Alluvial', 'Laterite', 'Mixed']
    MODEL_R2 = 0.621
    MODEL_RMSE = 0.772

def prepare_features(data):
    """Prepare features for Model B prediction"""
    
    temp = float(data['temp_c'])
    dewpoint = float(data['dewpoint_c'])
    precip = float(data['precip_mm'])
    solar = float(data['solar_rad'])
    annual_rain = float(data['annual_rain'])
    irrigation = float(data['irrigation'])
    soil_type = data['soil_type']
    
    # Optional inputs with defaults
    rain_cv = float(data.get('rain_cv', 20))
    prev_yield = float(data.get('prev_yield', 1.5))
    
    # Calculate seasonal rainfall
    kharif_rain = annual_rain * 0.7
    rabi_rain = annual_rain * 0.3
    
    # Encode soil type
    soil_encoded = soil_encoder.transform([soil_type])[0]
    
    # Year index
    year_index = datetime.now().year - 2000
    
    # Interaction features
    temp_rain_interaction = (temp * annual_rain) / 1000
    rain_irrigation_ratio = annual_rain / (irrigation + 1)
    
    # Feature vector
    features = [
        temp, dewpoint, precip, solar,
        annual_rain, kharif_rain, rabi_rain, rain_cv,
        soil_encoded, irrigation,
        year_index, prev_yield,
        0,  # season removed
        temp_rain_interaction, rain_irrigation_ratio
    ]
    
    return np.array(features).reshape(1, -1)

def get_rainfall_zone(annual_rain):
    """Categorize rainfall zone"""
    if annual_rain < 500:
        return "Arid"
    elif annual_rain < 750:
        return "Semi-arid"
    elif annual_rain < 1200:
        return "Sub-humid"
    else:
        return "Humid"

def generate_recommendations(inputs, prediction):
    """Generate recommendations"""
    recommendations = []
    
    annual_rain = float(inputs['annual_rain'])
    irrigation = float(inputs['irrigation'])
    soil_type = inputs['soil_type']
    temp = float(inputs['temp_c'])
    
    # Rainfall
    if annual_rain < 600:
        recommendations.append({
            'type': 'warning',
            'icon': '⚠️',
            'text': 'Low rainfall zone. Irrigation is critical for cotton success.'
        })
    elif annual_rain > 1500:
        recommendations.append({
            'type': 'info',
            'icon': '💧',
            'text': 'High rainfall zone. Ensure proper drainage to prevent waterlogging.'
        })
    else:
        recommendations.append({
            'type': 'success',
            'icon': '✓',
            'text': 'Rainfall levels are suitable for cotton cultivation.'
        })
    
    # Irrigation
    if irrigation < 30 and annual_rain < 800:
        potential_increase = prediction * 0.15
        recommendations.append({
            'type': 'info',
            'icon': '💡',
            'text': f'Consider irrigation to 50%. Could improve yield by ~15% (est. {prediction + potential_increase:.1f} bales/ha)'
        })
    
    # Soil
    soil_tips = {
        'Black': 'Black cotton soil is excellent. Maintain pH 7.0-8.5.',
        'Red': 'Red soil: Add organic matter. Maintain pH 6.5-7.5.',
        'Alluvial': 'Alluvial soil is well-suited with good fertility management.',
        'Laterite': 'Laterite needs organic amendments. Monitor pH (6.0-7.0).',
        'Mixed': 'Mixed soil: Test pH and adjust based on type.'
    }
    
    if soil_type in soil_tips:
        recommendations.append({
            'type': 'info',
            'icon': '🌱',
            'text': soil_tips[soil_type]
        })
    
    # Temperature
    if temp > 32:
        recommendations.append({
            'type': 'warning',
            'icon': '🌡️',
            'text': 'High temperatures. Ensure adequate irrigation and heat-tolerant varieties.'
        })
    
    recommendations.append({
        'type': 'info',
        'icon': '🐛',
        'text': 'Monitor for bollworms during flowering and boll formation.'
    })
    
    return recommendations

# ROUTES

@geographic_bp.route('/predict-form')
@login_required
def predict_form():
    """Show geographic prediction form"""
    return render_template('prediction_geographic.html', 
                         soil_types=soil_classes,
                         model_r2=MODEL_R2)

@geographic_bp.route('/predict', methods=['POST'])
@login_required
def predict():
    """Handle geographic prediction"""
    try:
        data = request.form.to_dict()
        
        # Validate required fields
        required = ['temp_c', 'dewpoint_c', 'precip_mm', 'solar_rad', 
                   'annual_rain', 'soil_type', 'irrigation']
        
        for field in required:
            if field not in data or data[field] == '':
                flash(f'{field.replace("_", " ").title()} is required.', 'error')
                return redirect(url_for('geographic.predict_form'))
        
        # Prepare features
        X = prepare_features(data)
        
        # Predict
        prediction = model.predict(X)[0]
        
        # Confidence interval
        confidence_lower = max(0, prediction - (MODEL_RMSE * 1.96))
        confidence_upper = prediction + (MODEL_RMSE * 1.96)
        prediction = max(0, prediction)
        
        # Rainfall zone
        rainfall_zone = get_rainfall_zone(float(data['annual_rain']))
        
        # Get location name from form data
        location = data.get('location', 'Unknown Location')
        
        # Recommendations
        recommendations = generate_recommendations(data, prediction)
        
        # Save to database WITH LOCATION
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO geographic_predictions 
            (user_id, temp_c, dewpoint_c, precip_mm, solar_rad, annual_rain, 
             rain_cv, soil_type, irrigation, prev_yield, predicted_yield, 
             confidence_lower, confidence_upper, rainfall_zone, location, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            session['user_id'],
            data['temp_c'], data['dewpoint_c'], data['precip_mm'], data['solar_rad'],
            data['annual_rain'], data.get('rain_cv', 20), data['soil_type'],
            data['irrigation'], data.get('prev_yield', 1.5),
            round(prediction, 2), round(confidence_lower, 2), 
            round(confidence_upper, 2), rainfall_zone, location
        ))
        conn.commit()
        conn.close()
        
        # User-friendly result 
        result = {
            'prediction': round(prediction, 2),
            'confidence_lower': round(confidence_lower, 2),
            'confidence_upper': round(confidence_upper, 2),
            'rainfall_zone': rainfall_zone,
            'location': location,
            'inputs': data,
            'recommendations': recommendations
        }
        
        return render_template('prediction_geographic_results.html', result=result)
        
    except Exception as e:
        flash(f'Prediction error: {str(e)}', 'error')
        return redirect(url_for('geographic.predict_form'))

@geographic_bp.route('/history')
@login_required
def history():
    """View geographic prediction history"""
    conn = get_db_connection()
    predictions = conn.execute('''
        SELECT * FROM geographic_predictions 
        WHERE user_id = ? 
        ORDER BY date DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('prediction_geographic_history.html', predictions=predictions)

@geographic_bp.route('/about')
def about():
    """About geographic model"""
    return render_template('about_geographic_model.html', metadata=metadata)

@geographic_bp.route('/examples/<example_name>')
@login_required
def load_example(example_name):
    """Load pre-filled examples for different regions"""
    examples = {
        # ===================================================================
        # KENYA - WESTERN REGION (Humid, Best for Cotton)
        # ===================================================================
        'kenya_busia': {
            'name': 'Kenya - Busia County',
            'temp_c': '24', 'dewpoint_c': '20', 'precip_mm': '110', 'solar_rad': '17',
            'annual_rain': '1300', 'rain_cv': '18', 'soil_type': 'Red',
            'irrigation': '15', 'prev_yield': '1.8'
        },
        'kenya_bungoma': {
            'name': 'Kenya - Bungoma County',
            'temp_c': '23', 'dewpoint_c': '19', 'precip_mm': '120', 'solar_rad': '17',
            'annual_rain': '1400', 'rain_cv': '16', 'soil_type': 'Red',
            'irrigation': '12', 'prev_yield': '1.9'
        },
        'kenya_kakamega': {
            'name': 'Kenya - Kakamega County',
            'temp_c': '23', 'dewpoint_c': '20', 'precip_mm': '130', 'solar_rad': '16',
            'annual_rain': '1500', 'rain_cv': '15', 'soil_type': 'Red',
            'irrigation': '10', 'prev_yield': '2.0'
        },
        
        # ===================================================================
        # KENYA - NYANZA REGION (Sub-humid)
        # ===================================================================
        'kenya_homabay': {
            'name': 'Kenya - Homa Bay County',
            'temp_c': '25', 'dewpoint_c': '20', 'precip_mm': '90', 'solar_rad': '18',
            'annual_rain': '1100', 'rain_cv': '20', 'soil_type': 'Red',
            'irrigation': '20', 'prev_yield': '1.7'
        },
        'kenya_migori': {
            'name': 'Kenya - Migori County',
            'temp_c': '24', 'dewpoint_c': '20', 'precip_mm': '95', 'solar_rad': '17',
            'annual_rain': '1200', 'rain_cv': '18', 'soil_type': 'Red',
            'irrigation': '18', 'prev_yield': '1.8'
        },
        'kenya_siaya': {
            'name': 'Kenya - Siaya County',
            'temp_c': '24', 'dewpoint_c': '21', 'precip_mm': '100', 'solar_rad': '17',
            'annual_rain': '1250', 'rain_cv': '17', 'soil_type': 'Red',
            'irrigation': '15', 'prev_yield': '1.8'
        },
        
        # ===================================================================
        # KENYA - EASTERN REGION (Semi-arid to Arid)
        # ===================================================================
        'kenya_machakos': {
            'name': 'Kenya - Machakos County',
            'temp_c': '22', 'dewpoint_c': '16', 'precip_mm': '55', 'solar_rad': '19',
            'annual_rain': '650', 'rain_cv': '28', 'soil_type': 'Red',
            'irrigation': '35', 'prev_yield': '1.3'
        },
        'kenya_makueni': {
            'name': 'Kenya - Makueni County',
            'temp_c': '23', 'dewpoint_c': '15', 'precip_mm': '50', 'solar_rad': '20',
            'annual_rain': '600', 'rain_cv': '30', 'soil_type': 'Red',
            'irrigation': '40', 'prev_yield': '1.2'
        },
        'kenya_kitui': {
            'name': 'Kenya - Kitui County',
            'temp_c': '26', 'dewpoint_c': '14', 'precip_mm': '35', 'solar_rad': '21',
            'annual_rain': '450', 'rain_cv': '35', 'soil_type': 'Red',
            'irrigation': '60', 'prev_yield': '1.0'
        },
        
        # ===================================================================
        # KENYA - RIFT VALLEY REGION (Semi-arid)
        # ===================================================================
        'kenya_baringo': {
            'name': 'Kenya - Baringo County',
            'temp_c': '27', 'dewpoint_c': '16', 'precip_mm': '60', 'solar_rad': '20',
            'annual_rain': '700', 'rain_cv': '27', 'soil_type': 'Black',
            'irrigation': '38', 'prev_yield': '1.4'
        },
        'kenya_westpokot': {
            'name': 'Kenya - West Pokot County',
            'temp_c': '25', 'dewpoint_c': '15', 'precip_mm': '65', 'solar_rad': '19',
            'annual_rain': '750', 'rain_cv': '25', 'soil_type': 'Red',
            'irrigation': '32', 'prev_yield': '1.5'
        },
        
        # ===================================================================
        # KENYA - COAST REGION (Sub-humid)
        # ===================================================================
        'kenya_kwale': {
            'name': 'Kenya - Kwale County',
            'temp_c': '26', 'dewpoint_c': '22', 'precip_mm': '85', 'solar_rad': '18',
            'annual_rain': '1000', 'rain_cv': '22', 'soil_type': 'Laterite',
            'irrigation': '25', 'prev_yield': '1.6'
        },
        'kenya_kilifi': {
            'name': 'Kenya - Kilifi County',
            'temp_c': '27', 'dewpoint_c': '23', 'precip_mm': '80', 'solar_rad': '19',
            'annual_rain': '950', 'rain_cv': '24', 'soil_type': 'Laterite',
            'irrigation': '28', 'prev_yield': '1.5'
        },
    }
    
    example = examples.get(example_name, examples['kenya_busia'])
    
    return render_template('prediction_geographic.html',
                         soil_types=soil_classes,
                         model_r2=MODEL_R2,
                         form_data=example,
                         example_name=example['name'])
        

@geographic_bp.route('/optimal-planting-form')
@login_required
def optimal_planting_form():
    """Show optimal planting time form"""
    return render_template('optimal_planting_form.html',  # ← CHANGED THIS LINE
                         soil_types=soil_classes)

@geographic_bp.route('/optimal-planting', methods=['POST'])
@login_required
def optimal_planting():
    """
    Predict optimal planting time using YIELD predictions
    Uses the existing geographic model (transfer learning from India to Kenya)
    """
    try:
        data = request.form.to_dict()
        
        # Get base location characteristics
        location_data = {
            'temp_c': float(data.get('temp_c', 24)),
            'dewpoint_c': float(data.get('dewpoint_c', 20)),
            'precip_mm': float(data.get('precip_mm', 100)),
            'solar_rad': float(data.get('solar_rad', 17)),
            'annual_rain': float(data.get('annual_rain', 1000)),
            'rain_cv': float(data.get('rain_cv', 20)),
            'soil_type': data.get('soil_type', 'Red'),
            'irrigation': float(data.get('irrigation', 20)),
            'prev_yield': float(data.get('prev_yield', 1.5)),
            'location': data.get('location', 'Unknown Location')
        }
        
        print(f"\n{'='*60}")
        print(f"🌾 PREDICTING OPTIMAL PLANTING TIME FOR: {location_data['location']}")
        print(f"{'='*60}")
        
        # Predict yield for each planting month
        monthly_predictions = []
        
        for month in range(1, 13):
            # Adjust climate based on planting month
            monthly_climate = adjust_climate_for_planting_month(location_data, month)
            
            # Prepare features for the model
            X = prepare_features(monthly_climate)
            
            # Predict yield using existing geographic model
            predicted_yield = model.predict(X)[0]
            predicted_yield = max(0, predicted_yield)  # Ensure non-negative
            
            monthly_predictions.append({
                'month': get_month_name(month),
                'month_num': month,
                'predicted_yield': round(predicted_yield, 2),
                'season': get_kenya_season(month)
            })
            
            print(f"  {get_month_name(month):12} ({get_kenya_season(month):12}): {predicted_yield:.2f} bales/ha")
        
        # Sort by predicted yield (highest first)
        monthly_predictions.sort(key=lambda x: x['predicted_yield'], reverse=True)
        
        # Get top 3 months
        best_months = monthly_predictions[:3]
        
        print(f"\n🏆 TOP 3 PLANTING MONTHS:")
        for i, month in enumerate(best_months, 1):
            print(f"  {i}. {month['month']:12} - {month['predicted_yield']} bales/ha ({month['season']})")
        print(f"{'='*60}\n")
        
        # Generate yield-based recommendations
        recommendations = []
        
        # Best month recommendation
        recommendations.append({
            'type': 'success',
            'icon': '🏆',
            'text': f'Best planting month: {best_months[0]["month"]} (Predicted yield: {best_months[0]["predicted_yield"]} bales/ha)'
        })
        
        # Alternative months
        if len(best_months) > 1:
            alt_months = ', '.join([
                f'{m["month"]} ({m["predicted_yield"]} bales/ha)' 
                for m in best_months[1:]
            ])
            recommendations.append({
                'type': 'info',
                'icon': '📅',
                'text': f'Alternative planting months: {alt_months}'
            })
        
        # Yield difference warning
        if best_months[0]['predicted_yield'] - best_months[-1]['predicted_yield'] > 0.5:
            yield_diff = best_months[0]['predicted_yield'] - best_months[-1]['predicted_yield']
            recommendations.append({
                'type': 'warning',
                'icon': '⚠️',
                'text': f'Planting in {best_months[0]["month"]} increases yield by {yield_diff:.1f} bales/ha compared to {best_months[-1]["month"]}'
            })
        
        # Season-based advice
        if best_months[0]['season'] == 'Long Rains':
            recommendations.append({
                'type': 'info',
                'icon': '🌳',
                'text': 'Long rains season (March-May) is Kenya\'s main cotton planting period with reliable rainfall'
            })
        elif best_months[0]['season'] == 'Short Rains':
            recommendations.append({
                'type': 'info',
                'icon': '🌱',
                'text': 'Short rains season (October-December) offers a secondary planting window'
            })
        
        # Rainfall-based advice
        if location_data['annual_rain'] < 600:
            recommendations.append({
                'type': 'warning',
                'icon': '💧',
                'text': f'Low rainfall area ({location_data["annual_rain"]}mm). Ensure irrigation is available, especially during flowering stage'
            })
        elif location_data['annual_rain'] > 1200:
            recommendations.append({
                'type': 'info',
                'icon': '☔',
                'text': f'High rainfall area ({location_data["annual_rain"]}mm). Good drainage is essential to prevent waterlogging'
            })
        
        # Save to database
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO planting_recommendations 
            (user_id, location, annual_rain, best_month, best_score, date)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            session['user_id'],
            location_data['location'],
            location_data['annual_rain'],
            best_months[0]['month'],
            best_months[0]['predicted_yield']  # This is now a YIELD prediction!
        ))
        conn.commit()
        conn.close()
        
        # Prepare result
        result = {
            'location': location_data['location'],
            'annual_rain': location_data['annual_rain'],
            'monthly_predictions': monthly_predictions,  # All 12 months
            'best_months': best_months,  # Top 3
            'recommendations': recommendations
        }
        
        return render_template('optimal_planting_results.html', result=result)
        
    except Exception as e:
        print(f"❌ Error in optimal planting: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Calculation error: {str(e)}', 'error')
        return redirect(url_for('geographic.optimal_planting_form'))