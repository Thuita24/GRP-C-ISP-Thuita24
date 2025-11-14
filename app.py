# app.py - Main Flask Application with Authentication, MFA, and Google Sign-In
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from functools import wraps
import re
from datetime import datetime
import qrcode
import io
import base64
from urllib.parse import urlencode
import requests
import json
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import pyotp
import secrets
from dotenv import load_dotenv
from routes.prediction_routes import prediction_bp
from routes.geographic_routes import geographic_bp

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = 'a1b2c3d4e5f6789012345abcdef67890123456789abcdef0123456789abcdef01'

# Register blueprints   
app.register_blueprint(prediction_bp)
app.register_blueprint(geographic_bp)

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', 'your-google-client-id-here')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', 'your-google-client-secret-here')
REDIRECT_URI = 'http://127.0.0.1:5000/auth/google/callback'

# Database setup
DATABASE = 'cotton_app.db'

def init_db():
    """Initialize the database with all required tables"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # ========================================================================
    # TABLE 1: USERS (with MFA and OAuth)
    # ========================================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            phone TEXT,
            location TEXT,
            bio TEXT,
            google_id TEXT UNIQUE,
            is_google_user BOOLEAN DEFAULT 0,
            mfa_enabled BOOLEAN DEFAULT 1,
            mfa_secret TEXT,
            backup_codes TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # ========================================================================
    # TABLE 2: PREDICTIONS (Old Model A - Keep for backward compatibility)
    # ========================================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            temperature REAL NOT NULL,
            rainfall REAL NOT NULL,
            humidity REAL NOT NULL,
            soil_ph REAL NOT NULL,
            nitrogen REAL NOT NULL,
            phosphorus REAL NOT NULL,
            potassium REAL NOT NULL,
            area REAL NOT NULL,
            predicted_yield REAL NOT NULL,
            expected_production REAL NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # ========================================================================
    # TABLE 3: GEOGRAPHIC PREDICTIONS (Model B - Main prediction table)
    # ========================================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS geographic_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            temp_c REAL NOT NULL,
            dewpoint_c REAL NOT NULL,
            precip_mm REAL NOT NULL,
            solar_rad REAL NOT NULL,
            annual_rain REAL NOT NULL,
            rain_cv REAL,
            soil_type TEXT NOT NULL,
            irrigation REAL NOT NULL,
            prev_yield REAL,
            predicted_yield REAL NOT NULL,
            confidence_lower REAL NOT NULL,
            confidence_upper REAL NOT NULL,
            rainfall_zone TEXT NOT NULL,
            location TEXT DEFAULT 'Unknown',
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # ========================================================================
    # TABLE 4: PLANTING RECOMMENDATIONS (Optimal planting time)
    # ========================================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS planting_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            location TEXT NOT NULL,
            annual_rain REAL NOT NULL,
            best_month TEXT NOT NULL,
            best_score REAL NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # ========================================================================
    # TABLE 5: MFA SESSIONS (Two-factor authentication)
    # ========================================================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mfa_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # ========================================================================
    # INDEXES for better query performance
    # ========================================================================
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_geographic_user ON geographic_predictions(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_geographic_date ON geographic_predictions(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_planting_user ON planting_recommendations(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_predictions_user ON predictions(user_id)')
   
    conn.commit()
    conn.close()
    
    print("✅ Database initialized successfully!")


def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    """Decorator to require login for certain routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def validate_email(email):
    """Simple email validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Password validation - at least 6 characters"""
    return len(password) >= 6

def generate_backup_codes(count=10):
    """Generate backup codes for MFA"""
    codes = [secrets.token_hex(4).upper() for _ in range(count)]
    return codes

def generate_qr_code(email, secret):
    """Generate QR code for MFA setup"""
    totp = pyotp.TOTP(secret)
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp.provisioning_uri(name=email, issuer_name='Cotton Prediction App'))
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    img_base64 = base64.b64encode(img_io.getvalue()).decode()
    
    return f"data:image/png;base64,{img_base64}"

def get_user_stats(user_id):
    """Get user statistics for dashboard and profile"""
    conn = get_db_connection()
    
    total_predictions = conn.execute(
        'SELECT COUNT(*) as count FROM predictions WHERE user_id = ?', 
        (user_id,)
    ).fetchone()['count']
    
    avg_yield = conn.execute(
        'SELECT AVG(predicted_yield) as avg FROM predictions WHERE user_id = ?', 
        (user_id,)
    ).fetchone()['avg']
    
    recent_predictions = conn.execute('''
        SELECT predicted_yield, area, date, expected_production
        FROM predictions 
        WHERE user_id = ? 
        ORDER BY date DESC 
        LIMIT 5
    ''', (user_id,)).fetchall()
    
    conn.close()
    
    return {
        'total_predictions': total_predictions,
        'avg_yield': round(avg_yield, 1) if avg_yield else 0,
        'recent_predictions': recent_predictions,
        'farms_count': 1
    }

def cotton_yield_prediction(temp, rainfall, humidity, ph, n, p, k, area):
    """Simple cotton yield prediction model"""
    base_yield = 60
    
    if 20 <= temp <= 30:
        temp_factor = 1.0
    else:
        temp_factor = max(0.5, 1 - abs(temp - 25) * 0.02)
    
    if 500 <= rainfall <= 1000:
        rain_factor = 1.0
    else:
        rain_factor = max(0.6, 1 - abs(rainfall - 750) * 0.0005)
    
    if 60 <= humidity <= 80:
        humidity_factor = 1.0
    else:
        humidity_factor = max(0.7, 1 - abs(humidity - 70) * 0.01)
    
    if 6.0 <= ph <= 7.5:
        ph_factor = 1.0
    else:
        ph_factor = max(0.6, 1 - abs(ph - 6.75) * 0.1)
    
    npk_factor = min(1.2, (n + p + k) / 15)
    
    yield_percentage = base_yield * temp_factor * rain_factor * humidity_factor * ph_factor * npk_factor
    yield_percentage = min(95, max(20, yield_percentage))
    
    kg_per_hectare = yield_percentage * 10
    total_production = kg_per_hectare * area
    
    return {
        'yield': round(yield_percentage, 1),
        'production': round(total_production, 1),
        'area': area
    }

# Google OAuth Routes
@app.route('/auth/google')
def auth_google():
    """Redirect user to Google OAuth"""
    google_auth_url = "https://accounts.google.com/o/oauth2/auth"
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': 'openid email profile',
        'response_type': 'code',
        'access_type': 'offline'
    }
    return redirect(f"{google_auth_url}?{urlencode(params)}")

@app.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    code = request.args.get('code')
    
    if not code:
        flash('Google authentication failed.', 'error')
        return redirect(url_for('login'))
    
    try:
        # Exchange code for token
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            'code': code,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'redirect_uri': REDIRECT_URI,
            'grant_type': 'authorization_code'
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_json = token_response.json()
        
        if 'error' in token_json:
            flash('Google authentication failed.', 'error')
            return redirect(url_for('login'))
        
        # Verify token and get user info
        id_token_jwt = token_json['id_token']
        idinfo = id_token.verify_oauth2_token(id_token_jwt, google_requests.Request(), GOOGLE_CLIENT_ID)
        
        google_id = idinfo['sub']
        email = idinfo['email']
        name = idinfo.get('name', email.split('@')[0])
        
        # Check if user exists
        conn = get_db_connection()
        user = conn.execute(
            'SELECT id, mfa_enabled, mfa_secret FROM users WHERE google_id = ? OR email = ?',
            (google_id, email)
        ).fetchone()
        
        if user:
            # Existing user
            user_id = user['id']
            mfa_enabled = user['mfa_enabled']
            mfa_secret = user['mfa_secret']
            
            # Update google_id if not set
            conn.execute(
                'UPDATE users SET google_id = ?, is_google_user = 1, last_login = CURRENT_TIMESTAMP WHERE id = ?',
                (google_id, user_id)
            )
            conn.commit()
        else:
            # New Google user - create with MFA automatically enabled
            mfa_secret = pyotp.random_base32()
            backup_codes = generate_backup_codes()
            backup_codes_str = ','.join(backup_codes)
            
            conn.execute('''
                INSERT INTO users (name, email, google_id, is_google_user, mfa_enabled, mfa_secret, backup_codes, last_login)
                VALUES (?, ?, ?, 1, 1, ?, ?, CURRENT_TIMESTAMP)
            ''', (name, email, google_id, mfa_secret, backup_codes_str))
            conn.commit()
            
            user_id = conn.lastrowid
            mfa_enabled = True
        
        conn.close()
        
        # Check if MFA is enabled and redirect appropriately
        if mfa_enabled and mfa_secret:
            # Redirect to MFA verification
            session['pending_user_id'] = user_id
            session['pending_email'] = email
            session['pending_name'] = name
            return redirect(url_for('verify_mfa'))
        else:
            # Should not happen for Google users (they have MFA enabled), but just in case
            session['user_id'] = user_id
            session['username'] = name
            session['email'] = email
            flash(f'Welcome, {name}!', 'success')
            return redirect(url_for('dashboard'))
    
    except Exception as e:
        flash('Google authentication failed. Please try again.', 'error')
        return redirect(url_for('login'))

# Routes
@app.route('/')
def home():
    """Home page"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handle user registration with automatic MFA"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip()
        location = request.form.get('location', '').strip()
        
        errors = []
        
        if not name or len(name) < 2:
            errors.append('Name must be at least 2 characters long.')
        
        if not validate_email(email):
            errors.append('Please enter a valid email address.')
        
        if not validate_password(password):
            errors.append('Password must be at least 6 characters long.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        if not location:
            errors.append('Please enter your farm location.')
        
        if not errors:
            conn = get_db_connection()
            existing_user = conn.execute(
                'SELECT id FROM users WHERE email = ?',
                (email,)
            ).fetchone()
            
            if existing_user:
                errors.append('Email already exists.')
            
            conn.close()
        
        if not errors:
            conn = get_db_connection()
            password_hash = generate_password_hash(password)
            
            # Generate MFA credentials automatically
            mfa_secret = pyotp.random_base32()
            backup_codes = generate_backup_codes()
            backup_codes_str = ','.join(backup_codes)
            
            try:
                cursor = conn.execute('''
                    INSERT INTO users (name, email, password_hash, phone, location, 
                                     mfa_enabled, mfa_secret, backup_codes)
                    VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                ''', (name, email, password_hash, phone, location, mfa_secret, backup_codes_str))
                conn.commit()
                
                user_id = cursor.lastrowid
                conn.close()
                
                # Redirect to MFA setup with the generated secret
                session['new_user_id'] = user_id
                session['new_user_email'] = email
                session['new_user_name'] = name
                session['mfa_secret'] = mfa_secret
                session['backup_codes'] = backup_codes
                
                flash('Account created! Please set up your Two-Factor Authentication.', 'success')
                return redirect(url_for('setup_mfa_new_user'))
            
            except sqlite3.Error as e:
                conn.close()
                errors.append('An error occurred while creating your account. Please try again.')
        
        for error in errors:
            flash(error, 'error')
    
    return render_template('signup.html')

@app.route('/setup-mfa-new-user')
def setup_mfa_new_user():
    """Setup MFA for newly registered user"""
    if 'new_user_id' not in session:
        flash('Session expired. Please sign up again.', 'error')
        return redirect(url_for('signup'))
    
    mfa_secret = session.get('mfa_secret')
    backup_codes = session.get('backup_codes', [])
    email = session.get('new_user_email')
    
    if not mfa_secret:
        flash('MFA setup failed. Please sign up again.', 'error')
        return redirect(url_for('signup'))
    
    # Generate QR code
    qr_code = generate_qr_code(email, mfa_secret)
    
    return render_template('setup_mfa_new_user.html', 
                         qr_code=qr_code, 
                         backup_codes=backup_codes)

@app.route('/verify-mfa-new-user', methods=['POST'])
def verify_mfa_new_user():
    """Verify MFA code for newly registered user"""
    if 'new_user_id' not in session:
        flash('Session expired. Please sign up again.', 'error')
        return redirect(url_for('signup'))
    
    token = request.form.get('token', '').strip()
    mfa_secret = session.get('mfa_secret')
    
    if not mfa_secret:
        flash('MFA setup failed. Please sign up again.', 'error')
        return redirect(url_for('signup'))
    
    # Verify token
    totp = pyotp.TOTP(mfa_secret)
    if not totp.verify(token):
        flash('Invalid authentication code. Please try again.', 'error')
        return redirect(url_for('setup_mfa_new_user'))
    
    # MFA verified! Complete the signup
    user_id = session['new_user_id']
    name = session['new_user_name']
    email = session['new_user_email']
    
    # Clear session data
    session.pop('new_user_id', None)
    session.pop('new_user_email', None)
    session.pop('new_user_name', None)
    session.pop('mfa_secret', None)
    session.pop('backup_codes', None)
    
    # Log user in
    session['user_id'] = user_id
    session['username'] = name
    session['email'] = email
    
    flash(f'Welcome, {name}! Your account is now set up with Two-Factor Authentication.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Please enter both email and password.', 'error')
            return render_template('login.html')
        
        conn = get_db_connection()
        user = conn.execute('''
            SELECT id, name, email, password_hash, mfa_enabled, mfa_secret
            FROM users 
            WHERE email = ? AND is_google_user = 0
        ''', (email,)).fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            user_id = user['id']
            
            # Update last login
            conn.execute(
                'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
                (user_id,)
            )
            conn.commit()
            conn.close()
            
            # Store pending user info for MFA verification
            session['pending_user_id'] = user_id
            session['pending_email'] = email
            session['pending_name'] = user['name']
            
            # Redirect to MFA verification (all users have MFA enabled)
            return redirect(url_for('verify_mfa'))
        else:
            flash('Invalid email or password.', 'error')
        
        conn.close()
    
    return render_template('login.html')

@app.route('/verify-mfa', methods=['GET', 'POST'])
def verify_mfa():
    """Verify MFA code during login"""
    if 'pending_user_id' not in session:
        flash('Session expired. Please log in again.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        token = request.form.get('token', '').strip()
        backup_code = request.form.get('backup_code', '').strip()
        
        user_id = session['pending_user_id']
        
        conn = get_db_connection()
        user = conn.execute(
            'SELECT name, email, mfa_secret, backup_codes FROM users WHERE id = ?',
            (user_id,)
        ).fetchone()
        
        verified = False
        
        # Check TOTP token
        if token:
            totp = pyotp.TOTP(user['mfa_secret'])
            if totp.verify(token):
                verified = True
        
        # Check backup code
        if not verified and backup_code:
            backup_codes = user['backup_codes'].split(',')
            if backup_code in backup_codes:
                # Remove used backup code
                backup_codes.remove(backup_code)
                conn.execute(
                    'UPDATE users SET backup_codes = ? WHERE id = ?',
                    (','.join(backup_codes), user_id)
                )
                verified = True
        
        if verified:
            # Update last login and complete session
            conn.execute(
                'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
                (user_id,)
            )
            conn.commit()
            conn.close()
            
            session.pop('pending_user_id', None)
            session.pop('pending_email', None)
            session.pop('pending_name', None)
            
            session['user_id'] = user_id
            session['username'] = user['name']
            session['email'] = user['email']
            
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            conn.close()
            flash('Invalid authentication code or backup code.', 'error')
            return redirect(url_for('verify_mfa'))
    
    return render_template('verify_mfa.html')

@app.route('/logout')
def logout():
    """Handle user logout"""
    username = session.get('username', 'User')
    session.clear()
    flash(f'Goodbye, {username}!', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard with real-time statistics"""
    conn = get_db_connection()
    
    # Get user info
    user = conn.execute('SELECT * FROM users WHERE id = ?', 
                       (session['user_id'],)).fetchone()
    
    # Get geographic predictions statistics
    stats = conn.execute('''
        SELECT 
            COUNT(*) as total_predictions,
            AVG(predicted_yield) as avg_yield,
            MAX(predicted_yield) as max_yield,
            MIN(predicted_yield) as min_yield,
            COUNT(DISTINCT location) as unique_locations
        FROM geographic_predictions 
        WHERE user_id = ?
    ''', (session['user_id'],)).fetchone()
    
    # Get recent predictions (last 5) WITH LOCATION
    recent_predictions = conn.execute('''
        SELECT 
            id,
            predicted_yield,
            location,
            rainfall_zone,
            date
        FROM geographic_predictions 
        WHERE user_id = ? 
        ORDER BY date DESC 
        LIMIT 5
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    
    # Prepare stats with defaults
    total_predictions = stats['total_predictions'] if stats else 0
    avg_yield = round(stats['avg_yield'], 1) if stats and stats['avg_yield'] else 0
    farms_count = stats['unique_locations'] if stats and stats['unique_locations'] else 0
    
    # If no predictions yet, show 0 for farms
    if total_predictions == 0:
        farms_count = 0
    elif farms_count == 0:
        farms_count = 1  # At least 1 if they made predictions but location wasn't tracked
    
    return render_template('dashboard.html',
                         user=user,
                         total_predictions=total_predictions,
                         avg_yield=avg_yield,
                         farms_count=farms_count,
                         recent_predictions=recent_predictions)

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    """Handle cotton prediction"""
    try:
        temperature = float(request.form.get('temperature'))
        rainfall = float(request.form.get('rainfall'))
        humidity = float(request.form.get('humidity'))
        soil_ph = float(request.form.get('soil_ph'))
        nitrogen = float(request.form.get('nitrogen'))
        phosphorus = float(request.form.get('phosphorus'))
        potassium = float(request.form.get('potassium'))
        area = float(request.form.get('area'))
        
        prediction_result = cotton_yield_prediction(
            temperature, rainfall, humidity, soil_ph,
            nitrogen, phosphorus, potassium, area
        )
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO predictions 
            (user_id, temperature, rainfall, humidity, soil_ph, nitrogen, 
             phosphorus, potassium, area, predicted_yield, expected_production)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], temperature, rainfall, humidity, soil_ph,
              nitrogen, phosphorus, potassium, area, 
              prediction_result['yield'], prediction_result['production']))
        conn.commit()
        conn.close()
        
        flash(f'Prediction completed! Expected yield: {prediction_result["yield"]}%', 'success')
        
        conn = get_db_connection()
        user = conn.execute(
            'SELECT name, email, location FROM users WHERE id = ?',
            (session['user_id'],)
        ).fetchone()
        conn.close()
        
        user_stats = get_user_stats(session['user_id'])
        
        return render_template('dashboard.html', 
                             user=user, 
                             prediction_result=prediction_result,
                             **user_stats)
        
    except (ValueError, TypeError):
        flash('Please enter valid numbers for all fields.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        location = request.form.get('location', '').strip()
        bio = request.form.get('bio', '').strip()
        
        if not name or not validate_email(email) or not location:
            flash('Please fill in all required fields correctly.', 'error')
        else:
            try:
                conn = get_db_connection()
                conn.execute('''
                    UPDATE users 
                    SET name = ?, email = ?, phone = ?, location = ?, bio = ?
                    WHERE id = ?
                ''', (name, email, phone, location, bio, session['user_id']))
                conn.commit()
                conn.close()
                
                session['username'] = name
                session['email'] = email
                
                flash('Profile updated successfully!', 'success')
            except sqlite3.IntegrityError:
                flash('Email already exists.', 'error')
    
    conn = get_db_connection()
    user = conn.execute('''
        SELECT name, email, phone, location, bio, mfa_enabled, created_date, last_login, is_google_user
        FROM users WHERE id = ?
    ''', (session['user_id'],)).fetchone()
    conn.close()
    
    user_stats = get_user_stats(session['user_id'])
    
    return render_template('profile.html', user=user, user_stats=user_stats)

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """Handle password change (only for non-Google users)"""
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_new_password = request.form.get('confirm_new_password')
    
    if not all([current_password, new_password, confirm_new_password]):
        flash('All password fields are required.', 'error')
        return redirect(url_for('profile'))
    
    if new_password != confirm_new_password:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('profile'))
    
    if not validate_password(new_password):
        flash('New password must be at least 6 characters long.', 'error')
        return redirect(url_for('profile'))
    
    conn = get_db_connection()
    user = conn.execute(
        'SELECT password_hash FROM users WHERE id = ?',
        (session['user_id'],)
    ).fetchone()
    
    if not user or not user['password_hash'] or not check_password_hash(user['password_hash'], current_password):
        flash('Current password is incorrect.', 'error')
        conn.close()
        return redirect(url_for('profile'))
    
    try:
        new_password_hash = generate_password_hash(new_password)
        conn.execute(
            'UPDATE users SET password_hash = ? WHERE id = ?',
            (new_password_hash, session['user_id'])
        )
        conn.commit()
        flash('Password updated successfully!', 'success')
    except Exception:
        flash('An error occurred. Please try again.', 'error')
    
    conn.close()
    return redirect(url_for('profile'))

@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    """Handle account deletion"""
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM predictions WHERE user_id = ?', (session['user_id'],))
        conn.execute('DELETE FROM users WHERE id = ?', (session['user_id'],))
        conn.commit()
        conn.close()
        
        session.clear()
        flash('Your account has been deleted successfully.', 'info')
        return redirect(url_for('home'))
    except Exception:
        flash('An error occurred while deleting your account.', 'error')
        return redirect(url_for('profile'))

@app.route('/prediction_history')
@login_required
def prediction_history():
    """View all user predictions"""
    conn = get_db_connection()
    predictions = conn.execute('''
        SELECT * FROM predictions 
        WHERE user_id = ? 
        ORDER BY date DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('prediction_history.html', predictions=predictions)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)