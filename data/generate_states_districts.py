import sqlite3
import json

def generate_states_districts_json():
    """
    Extract states and districts from historical_yields table
    """
    conn = sqlite3.connect('cotton_app.db')
    cursor = conn.cursor()
    
    print("Extracting states and districts from database...")
    
    # Get all states and their districts
    cursor.execute("""
        SELECT DISTINCT state, district 
        FROM historical_yields 
        ORDER BY state, district
    """)
    
    results = cursor.fetchall()
    
    # Organize by state
    states_dict = {}
    for state, district in results:
        if state not in states_dict:
            states_dict[state] = []
        if district not in states_dict[state]:
            states_dict[state].append(district)
    
    # Create the JSON structure
    states_data = []
    for state in sorted(states_dict.keys()):
        states_data.append({
            "name": state,
            "districts": sorted(states_dict[state])
        })
    
    output = {
        "states": states_data,
        "seasons": ["Kharif", "Rabi"],
        "planting_windows": {
            "Kharif": {
                "early": {"start": "06-01", "end": "06-15", "label": "Early June"},
                "mid": {"start": "06-16", "end": "06-30", "label": "Late June"},
                "late": {"start": "07-01", "end": "07-15", "label": "Early July"}
            },
            "Rabi": {
                "early": {"start": "10-01", "end": "10-15", "label": "Early October"},
                "mid": {"start": "10-16", "end": "10-31", "label": "Late October"},
                "late": {"start": "11-01", "end": "11-15", "label": "Early November"}
            }
        }
    }
    
    # Save to JSON file
    with open('data/states_districts.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    conn.close()
    
    print(f"\n Generated states_districts.json")
    print(f"   Total states: {len(states_data)}")
    print(f"   Total districts: {sum(len(s['districts']) for s in states_data)}")
    print(f"\n Sample states:")
    for state in states_data[:5]:
        print(f"   {state['name']}: {len(state['districts'])} districts")

if __name__ == '__main__':
    generate_states_districts_json()