from services.prediction_service import PredictionService
from services.weather_service import WeatherService
import sqlite3
from datetime import datetime, timedelta

class PlantingOptimizer:
    """
    Analyzes optimal planting windows for cotton
    Compares yield predictions across different planting dates
    """
    
    def __init__(self):
        self.prediction_service = PredictionService()
        
        # Define planting windows for each season
        self.planting_windows = {
            "Kharif": {
                "early": {
                    "label": "Early June (1-15)",
                    "start": "06-01",
                    "end": "06-15",
                    "description": "Early monsoon planting"
                },
                "mid": {
                    "label": "Late June (16-30)",
                    "start": "06-16",
                    "end": "06-30",
                    "description": "Peak monsoon planting"
                },
                "late": {
                    "label": "Early July (1-15)",
                    "start": "07-01",
                    "end": "07-15",
                    "description": "Late monsoon planting"
                }
            },
            "Rabi": {
                "early": {
                    "label": "Early October (1-15)",
                    "start": "10-01",
                    "end": "10-15",
                    "description": "Early winter planting"
                },
                "mid": {
                    "label": "Late October (16-31)",
                    "start": "10-16",
                    "end": "10-31",
                    "description": "Peak winter planting"
                },
                "late": {
                    "label": "Early November (1-15)",
                    "start": "11-01",
                    "end": "11-15",
                    "description": "Late winter planting"
                }
            }
        }
    
    def find_optimal_planting_time(self, state, district, season, year):
        """
        Compare predicted yields across different planting windows
        and recommend the optimal timing
        
        Returns:
        - dict with predictions for each window and recommendation
        """
        
        if season not in self.planting_windows:
            raise ValueError(f"Invalid season: {season}. Must be 'Kharif' or 'Rabi'")
        
        windows = self.planting_windows[season]
        results = {}
        
        print(f"\n Analyzing optimal planting time for {district}, {state}")
        print(f"   Season: {season} {year}")
        print(f"   Testing {len(windows)} planting windows...\n")
        
        # Get predictions for each planting window
        for window_name, window_info in windows.items():
            try:
                # For now, we use the same climate data for all windows
                # In a more advanced version, you could adjust climate slightly
                # based on planting date
                prediction = self.prediction_service.predict_yield(
                    state=state,
                    district=district,
                    season=season,
                    year=year
                )
                
                # Add slight variation based on timing (simplified model)
                # Early planting: slight risk adjustment
                # Mid planting: optimal (no adjustment)
                # Late planting: stress factor adjustment
                adjustment_factors = {
                    "early": 0.97,  # 3% reduction (risk of early season stress)
                    "mid": 1.00,    # Optimal timing
                    "late": 0.95    # 5% reduction (shorter growing season)
                }
                
                adjusted_yield = prediction['predicted_yield'] * adjustment_factors[window_name]
                
                results[window_name] = {
                    'window': window_info['label'],
                    'dates': f"{window_info['start']} to {window_info['end']}",
                    'description': window_info['description'],
                    'predicted_yield': round(adjusted_yield, 2),
                    'confidence_interval': {
                        'lower': round(prediction['confidence_interval']['lower'] * adjustment_factors[window_name], 2),
                        'upper': round(prediction['confidence_interval']['upper'] * adjustment_factors[window_name], 2)
                    },
                    'adjustment_factor': adjustment_factors[window_name],
                    'climate': prediction['input_data']['climate']
                }
                
                print(f"    {window_info['label']}: {adjusted_yield:.2f} bales/ha")
                
            except Exception as e:
                print(f"    {window_info['label']}: Error - {e}")
                results[window_name] = None
        
        # Find the optimal window (highest predicted yield)
        valid_results = {k: v for k, v in results.items() if v is not None}
        
        if not valid_results:
            raise ValueError("Could not generate predictions for any planting window")
        
        optimal_window = max(valid_results.keys(), 
                            key=lambda k: valid_results[k]['predicted_yield'])
        
        optimal_yield = valid_results[optimal_window]['predicted_yield']
        
        # Calculate differences from optimal
        for window_name, result in valid_results.items():
            if result:
                diff = result['predicted_yield'] - optimal_yield
                result['difference_from_optimal'] = round(diff, 2)
                result['is_optimal'] = (window_name == optimal_window)
        
        # Generate recommendation text
        optimal_info = valid_results[optimal_window]
        recommendation = self._generate_recommendation(
            optimal_window, optimal_info, valid_results, season
        )
        
        # Calculate confidence level
        yield_range = optimal_yield - valid_results[optimal_window]['confidence_interval']['lower']
        confidence_level = "High" if yield_range < 0.5 else "Medium" if yield_range < 1.0 else "Low"
        
        return {
            'optimal_window': optimal_window,
            'optimal_window_info': optimal_info,
            'all_windows': valid_results,
            'recommendation': recommendation,
            'confidence_level': confidence_level,
            'metadata': {
                'state': state,
                'district': district,
                'season': season,
                'year': year,
                'analysis_date': datetime.now().isoformat()
            }
        }
    
    def _generate_recommendation(self, optimal_window, optimal_info, all_results, season):
        """Generate human-readable recommendation"""
        
        window_names = {
            "early": "early",
            "mid": "middle",
            "late": "late"
        }
        
        # Calculate yield differences
        yields = [r['predicted_yield'] for r in all_results.values()]
        max_yield = max(yields)
        min_yield = min(yields)
        yield_difference = max_yield - min_yield
        
        # Build recommendation
        recommendation = {
            'summary': f"Plant during {optimal_info['window']} for maximum yield",
            'optimal_period': optimal_info['window'],
            'dates': optimal_info['dates'],
            'expected_yield': optimal_info['predicted_yield'],
            'reasoning': []
        }
        
        # Add reasoning
        if optimal_window == "mid":
            recommendation['reasoning'].append(
                f"Mid-season planting ({optimal_info['dates']}) provides optimal growing conditions"
            )
        elif optimal_window == "early":
            recommendation['reasoning'].append(
                f"Early planting ({optimal_info['dates']}) recommended to maximize growing season"
            )
        else:
            recommendation['reasoning'].append(
                f"Late planting ({optimal_info['dates']}) shows best yield potential for this season"
            )
        
        # Add yield comparison
        if yield_difference > 0.3:
            recommendation['reasoning'].append(
                f"Significant yield difference ({yield_difference:.2f} bales/ha) between planting times - timing matters!"
            )
        else:
            recommendation['reasoning'].append(
                f"Small yield difference between windows - flexible planting schedule possible"
            )
        
        # Add climate consideration
        temp = optimal_info['climate']['temperature']
        rainfall = optimal_info['climate']['rainfall_total']
        
        if season == "Kharif":
            if rainfall > 500:
                recommendation['reasoning'].append(
                    f"Good rainfall forecast ({rainfall:.0f}mm) supports this planting window"
                )
            else:
                recommendation['reasoning'].append(
                    f"Lower rainfall forecast ({rainfall:.0f}mm) - ensure irrigation readiness"
                )
        else:  # Rabi
            if temp < 25:
                recommendation['reasoning'].append(
                    f"Favorable temperature ({temp:.1f}°C) for winter cotton"
                )
        
        return recommendation
    
    def save_recommendation(self, user_id, optimization_result):
        """Save planting recommendation to database"""
        conn = sqlite3.connect(self.prediction_service.db_path)
        cursor = conn.cursor()
        
        import json
        
        optimal = optimization_result['optimal_window_info']
        metadata = optimization_result['metadata']
        
        cursor.execute("""
            INSERT INTO planting_recommendations 
            (user_id, state, district, season, year, recommended_window,
             early_yield, mid_yield, late_yield, confidence_level, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            user_id,
            metadata['state'],
            metadata['district'],
            metadata['season'],
            metadata['year'],
            optimization_result['optimal_window'],
            optimization_result['all_windows']['early']['predicted_yield'] if 'early' in optimization_result['all_windows'] else None,
            optimization_result['all_windows']['mid']['predicted_yield'] if 'mid' in optimization_result['all_windows'] else None,
            optimization_result['all_windows']['late']['predicted_yield'] if 'late' in optimization_result['all_windows'] else None,
            optimization_result['confidence_level']
        ))
        
        conn.commit()
        recommendation_id = cursor.lastrowid
        conn.close()
        
        return recommendation_id