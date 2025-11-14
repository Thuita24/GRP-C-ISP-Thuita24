from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from services.prediction_service import PredictionService
from services.planting_optimizer import PlantingOptimizer
import json

# Create blueprint
prediction_bp = Blueprint('prediction', __name__)

# Initialize services
prediction_service = PredictionService()
planting_optimizer = PlantingOptimizer()

# Helper function to check if user is logged in
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@prediction_bp.route('/predict', methods=['GET'])
@login_required
def predict_form():
    """Display the prediction form"""
    # Load states and districts data
    try:
        with open('data/states_districts.json', 'r') as f:
            location_data = json.load(f)
    except Exception as e:
        location_data = {'states': [], 'seasons': ['Kharif', 'Rabi']}
    
    return render_template('prediction_form.html', 
                         states=location_data.get('states', []),
                         seasons=location_data.get('seasons', []))


@prediction_bp.route('/predict', methods=['POST'])
@login_required
def predict_yield():
    """Make a yield prediction"""
    try:
        # Get form data
        state = request.form.get('state')
        district = request.form.get('district')
        season = request.form.get('season')
        year = int(request.form.get('year', 2025))
        
        # Validate inputs
        if not all([state, district, season]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Make prediction
        prediction = prediction_service.predict_yield(
            state=state,
            district=district,
            season=season,
            year=year
        )
        
        # Save to database
        user_id = session.get('user_id')
        prediction_id = prediction_service.save_prediction(user_id, prediction)
        prediction['prediction_id'] = prediction_id
        
        # Return as JSON for AJAX or render template
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(prediction)
        else:
            return render_template('prediction_result.html', prediction=prediction)
        
    except Exception as e:
        print(f"Prediction error: {e}")
        import traceback
        traceback.print_exc()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': str(e)}), 500
        else:
            return render_template('error.html', error=str(e)), 500


@prediction_bp.route('/optimal-planting', methods=['GET'])
@login_required
def optimal_planting_form():
    """Display the optimal planting time form"""
    # Load states and districts data
    try:
        with open('data/states_districts.json', 'r') as f:
            location_data = json.load(f)
    except Exception as e:
        location_data = {'states': [], 'seasons': ['Kharif', 'Rabi']}
    
    return render_template('optimal_planting_form.html',
                         states=location_data.get('states', []),
                         seasons=location_data.get('seasons', []))


@prediction_bp.route('/optimal-planting', methods=['POST'])
@login_required
def find_optimal_planting():
    """Find optimal planting time"""
    try:
        # Get form data
        state = request.form.get('state')
        district = request.form.get('district')
        season = request.form.get('season')
        year = int(request.form.get('year', 2025))
        
        # Validate inputs
        if not all([state, district, season]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Find optimal planting time
        result = planting_optimizer.find_optimal_planting_time(
            state=state,
            district=district,
            season=season,
            year=year
        )
        
        # Save to database
        user_id = session.get('user_id')
        recommendation_id = planting_optimizer.save_recommendation(user_id, result)
        result['recommendation_id'] = recommendation_id
        
        # Return as JSON for AJAX or render template
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(result)
        else:
            return render_template('optimal_planting_result.html', result=result)
        
    except Exception as e:
        print(f"Optimization error: {e}")
        import traceback
        traceback.print_exc()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': str(e)}), 500
        else:
            return render_template('error.html', error=str(e)), 500


@prediction_bp.route('/prediction-history')
@login_required
def prediction_history():
    """View user's prediction history"""
    try:
        user_id = session.get('user_id')
        predictions = prediction_service.get_user_predictions(user_id, limit=20)
        
        return render_template('prediction_history.html', predictions=predictions)
        
    except Exception as e:
        print(f"History error: {e}")
        return render_template('error.html', error=str(e)), 500


@prediction_bp.route('/api/districts/<state>')
def get_districts(state):
    """API endpoint to get districts for a state (for cascading dropdown)"""
    try:
        with open('data/states_districts.json', 'r') as f:
            location_data = json.load(f)
        
        # Find the state
        for state_obj in location_data['states']:
            if state_obj['name'] == state:
                return jsonify({'districts': state_obj['districts']})
        
        return jsonify({'districts': []})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500