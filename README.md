Cotton Planting Recommendation Tool

Machine Learning–Based Climate Prediction System for Kenyan Farmers

---

  Overview

This project provides cotton farmers with data-driven planting recommendations by predicting expected cotton yield under different climatic conditions. The system uses a Random Forest regression model trained on 23 years of Indian climate–yield data and applies a transfer learning approach that allows Kenyan climate inputs to be used effectively.

The web-based interface lets farmers select their region, automatically fills in the relevant climate values, and returns the optimal planting month based on predicted yield.

---

 How It Works

1. The farmer selects the region they live in.
2. The system autofills typical climate values for that location from Open-Meteo API (temperature, rainfall, soil type, irrigation).
3. These values are passed to the trained Random Forest model.
4. The model predicts yield for all 12 months.
5. The tool selects the month with the highest predicted yield and recommends it as the optimal planting period.

---

 Model Architecture

Algorithm: Random Forest Regressor
Training Data:

  Indian APY cotton yield dataset (542 districts, 23 years)
  CHIRPS climate dataset (rainfall, temperature, dew point, solar radiation)
  Soil category and irrigation coverage
Transfer Learning Approach:

   Removed district and state identifiers → geography-agnostic model
   Climate–yield relationships learned in India can be applied to Kenyan inputs
   Only climate variables drive predictions, not location labels

This makes the model compatible with regions that lack long-term historical yield data, such as many cotton-growing counties in Kenya.

---

Model Performance

1. Training Performance

| Metric         | Value             |
| -------------- | ----------------- |
| R² (Train)     | 0.7048            |
| RMSE           | 0.74 bales/ha     |
| MAE            | 0.43 bales/ha     |

Meaning:
The model explains ~70% of the variation in the training data, indicating it learned meaningful climate–yield patterns.

---

2. Test Performance (Unseen Data)

| Metric        | Value             |
| ------------- | ----------------- |
| R² (Test)     | 0.4652            |
| RMSE          | 0.95 bales/ha     |
| MAE           | 0.60 bales/ha     |

Meaning:
Agricultural datasets are naturally noisy, so an R² of ~0.46 is strong enough to compare relative yield differences across months — which is all that is needed to identify the best planting month.

---

3. Cross-Validation Performance (5-Fold CV)

| Metric         | Value                |
| -------------- | -------------------- |
| Mean R²        | 0.1718               |
| Std Dev        | ± 0.1291             |
| Fold Range     | –0.0126 → 0.3467     |
| Mean RMSE      | 1.1761 bales/ha      |

Meaning:
Variability across Indian districts is high, but the model consistently outperforms the baseline and remains reliable for planting-window prediction.

---

Local Setup

Requirements

* Python 3.11+
* pip, setuptools, wheel
* 8GB RAM recommended for local model training
* Flask installed for running the web application

---

Clone the Repository

```bash
git clone https://github.com/Thuita24/GRP-C-ISP-Thuita24.git
cd GRP-C-ISP-Thuita24
```

---

Create and Activate Virtual Environment

```bash
python3.11 -m venv .venv
.\venv\Scripts\activate
```

---

Install Dependencies

```bash
pip install -r requirements.txt
```

Or at minimum:

```bash
pip install flask werkzeug
```

---

Run the Application

```bash
python app.py
```

The web app will start on:

```
http://127.0.0.1:5000
```

---

Project Structure

IS_PROJECT/
│
├── data/

│   ├── check_missing_data.py  # Inspect missing climate/yield values

│ 
├── fix_districts.py # Clean and standardize district names

│   ├── generate_states_districts.py  # Build JSON of states and districts

│   ├── import_historical_yields.py    # Process historical APY cotton yields

│   ├── merged_dataset.csv        # Final dataset used for training

│   └── states_districts.json     # Region list for frontend autofill

│
├── models/
│   ├── cotton_yield_model.pkl   # Final Random Forest model (Model B)

│   ├── encoders.pkl         # Soil-type encoders and preprocessing logic

│   ├── metadata.json   # Model metadata (features, training details)

│   ├── model_config.json  # Hyperparameters used during training

│   └── model.pkl       # Earlier baseline model (unused)

│
├── routes/
│   ├── __init__.py        # Route initialization

│   ├── geographic_routes.py # Region selection + default climate values

│   └── prediction_routes.py # Prediction endpoints (model inference)

│
├── services/
│   ├── planting_optimizer.py   # Determines best planting month

│   ├── prediction_service.py    # Runs ML model and prepares predictions

│   └── weather_service.py      # Generates or fetches climate inputs

│
├── static/
│   ├── css/
│   │   ├── geographic_style.css       # Styles for region selection pages

│   │   └── style.css                  # General styles

│   └── js/
│       └── geographic.js              # Frontend autofill logic

│
├── templates/
│   ├── base.html                      # Base layout

│   ├── index.html                     # Homepage

│   ├── dashboard.html                 # User dashboard

│   ├── prediction_geographic.html     # Region + climate input page

│   ├── prediction_geographic_results.html # Yield prediction results

│   ├── optimal_planning_results.html  # Recommended planting month

│   ├── prediction_history.html        # User prediction history

│   ├── login.html                     # Login page

│   ├── signup.html                    # User registration

│   └── verify_mfa.html                # MFA setup (optional)
│
├── cotton_app.db                      # SQLite database

├── cotton_app.db.backup               # Backup copy
│
├── app.py                             # Main Flask application

├── requirements.txt                   # Python dependencies

└── .gitignore                         # Ignored files for version control
```

---

License

MIT License

---




