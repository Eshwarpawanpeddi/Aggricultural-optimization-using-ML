from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import sqlite3
import json
from functools import wraps
import os

app = Flask(__name__)
CORS(app)

DB_PATH = 'agriculture.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS fields
                 (id INTEGER PRIMARY KEY, name TEXT UNIQUE, crop TEXT, area_hectares REAL,
                  soil_moisture REAL, temperature REAL, health_status TEXT, created_at TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS npk_levels
                 (id INTEGER PRIMARY KEY, field_id INTEGER, nitrogen REAL, phosphorus REAL, potassium REAL,
                  recorded_at TIMESTAMP, FOREIGN KEY(field_id) REFERENCES fields(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS irrigation_records
                 (id INTEGER PRIMARY KEY, field_id INTEGER, duration_minutes INTEGER, water_volume_liters REAL,
                  scheduled_time TIMESTAMP, status TEXT, created_at TIMESTAMP,
                  FOREIGN KEY(field_id) REFERENCES fields(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS crop_yield_forecast
                 (id INTEGER PRIMARY KEY, field_id INTEGER, forecast_date DATE, predicted_yield REAL,
                  created_at TIMESTAMP, FOREIGN KEY(field_id) REFERENCES fields(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS alerts
                 (id INTEGER PRIMARY KEY, field_id INTEGER, alert_type TEXT, message TEXT, recommendation TEXT,
                  priority TEXT, created_at TIMESTAMP, resolved INTEGER DEFAULT 0,
                  FOREIGN KEY(field_id) REFERENCES fields(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS weather
                 (id INTEGER PRIMARY KEY, forecast_date DATE, condition TEXT, min_temp REAL, max_temp REAL,
                  humidity REAL, precipitation REAL, created_at TIMESTAMP)''')
    
    conn.commit()
    conn.close()

def seed_initial_data():
    conn = get_db()
    c = conn.cursor()
    
    try:
        fields_data = [
            ('Field A - Wheat', 'Wheat', 15, 75.0, 23.0, 'Healthy'),
            ('Field B - Corn', 'Corn', 20, 68.0, 25.0, 'Needs Water'),
            ('Field C - Soybeans', 'Soybeans', 12, 80.0, 22.0, 'Excellent'),
            ('Field D - Rice', 'Rice', 18, 85.0, 26.0, 'Optimal')
        ]
        
        for field in fields_data:
            try:
                c.execute('INSERT INTO fields (name, crop, area_hectares, soil_moisture, temperature, health_status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                         (*field, datetime.now()))
            except sqlite3.IntegrityError:
                pass
        
        c.execute('SELECT id FROM fields')
        field_ids = [row[0] for row in c.fetchall()]
        
        npk_data = [
            (field_ids[0], 68, 45, 72),
            (field_ids[1], 55, 35, 60),
            (field_ids[2], 70, 50, 75),
            (field_ids[3], 75, 55, 80)
        ]
        
        for npk in npk_data:
            try:
                c.execute('INSERT INTO npk_levels (field_id, nitrogen, phosphorus, potassium, recorded_at) VALUES (?, ?, ?, ?, ?)',
                         (*npk, datetime.now()))
            except:
                pass
        
        try:
            c.execute('INSERT INTO alerts (field_id, alert_type, message, recommendation, priority, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                     (field_ids[1], 'Nutrient Deficiency', 'Low Phosphorus in Field B', 'Apply phosphate fertilizer within 3 days', 'High', datetime.now()))
        except:
            pass
        
        try:
            c.execute('INSERT INTO alerts (field_id, alert_type, message, recommendation, priority, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                     (field_ids[0], 'Irrigation Scheduled', 'Irrigation Scheduled for Field A', 'Next irrigation: Today at 6:00 PM (2 hours remaining)', 'Medium', datetime.now()))
        except:
            pass
        
        weather_data = [
            (datetime.now().date(), 'Clear', 20, 28, 65, 0),
            ((datetime.now() + timedelta(days=1)).date(), 'Partly Cloudy', 19, 27, 70, 5),
            ((datetime.now() + timedelta(days=2)).date(), 'Clear', 21, 29, 60, 0),
            ((datetime.now() + timedelta(days=3)).date(), 'Clear', 20, 28, 65, 0),
            ((datetime.now() + timedelta(days=4)).date(), 'Clear', 22, 30, 55, 0)
        ]
        
        for weather in weather_data:
            try:
                c.execute('INSERT INTO weather (forecast_date, condition, min_temp, max_temp, humidity, precipitation, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                         (*weather, datetime.now()))
            except:
                pass
        
        conn.commit()
    except Exception as e:
        print(f"Seeding error: {e}")
    finally:
        conn.close()

init_db()
seed_initial_data()

@app.route('/')
def index():
    return render_template('new.html')

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT AVG(soil_moisture) as avg_moisture FROM fields')
    avg_moisture = c.fetchone()[0] or 72
    
    c.execute('SELECT AVG(temperature) as avg_temp FROM fields')
    avg_temp = c.fetchone()[0] or 24
    
    c.execute('SELECT nitrogen, phosphorus, potassium FROM npk_levels ORDER BY recorded_at DESC LIMIT 1')
    npk_row = c.fetchone()
    npk = {'n': npk_row[0], 'p': npk_row[1], 'k': npk_row[2]} if npk_row else {'n': 68, 'p': 45, 'k': 72}
    
    c.execute('SELECT COUNT(*) as healthy FROM fields WHERE health_status IN ("Healthy", "Excellent", "Optimal")')
    healthy_count = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM fields')
    total_fields = c.fetchone()[0]
    crop_health = (healthy_count / total_fields * 100) if total_fields > 0 else 85
    
    conn.close()
    
    return jsonify({
        'soil_moisture': round(avg_moisture, 1),
        'temperature': round(avg_temp, 1),
        'npk_levels': npk,
        'crop_health': round(crop_health, 1)
    })

@app.route('/api/fields', methods=['GET'])
def get_fields():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT id, name, area_hectares, soil_moisture, temperature, health_status FROM fields ORDER BY id')
    fields = c.fetchall()
    
    fields_list = []
    for field in fields:
        fields_list.append({
            'id': field['id'],
            'name': field['name'],
            'area': field['area_hectares'],
            'moisture': field['soil_moisture'],
            'temperature': field['temperature'],
            'status': field['health_status']
        })
    
    conn.close()
    return jsonify(fields_list)

@app.route('/api/field/<int:field_id>', methods=['GET'])
def get_field_detail(field_id):
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT id, name, crop, area_hectares, soil_moisture, temperature, health_status FROM fields WHERE id = ?', (field_id,))
    field = c.fetchone()
    
    if not field:
        conn.close()
        return jsonify({'error': 'Field not found'}), 404
    
    c.execute('SELECT nitrogen, phosphorus, potassium, recorded_at FROM npk_levels WHERE field_id = ? ORDER BY recorded_at DESC LIMIT 1', (field_id,))
    npk = c.fetchone()
    
    conn.close()
    
    return jsonify({
        'id': field['id'],
        'name': field['name'],
        'crop': field['crop'],
        'area': field['area_hectares'],
        'moisture': field['soil_moisture'],
        'temperature': field['temperature'],
        'status': field['health_status'],
        'npk': {
            'nitrogen': npk[0],
            'phosphorus': npk[1],
            'potassium': npk[2]
        } if npk else None
    })

@app.route('/api/irrigation/start', methods=['POST'])
def start_irrigation():
    data = request.json
    field_id = data.get('field_id')
    duration = data.get('duration', 30)
    water_volume = data.get('water_volume', 500)
    
    conn = get_db()
    c = conn.cursor()
    
    scheduled_time = datetime.now() + timedelta(minutes=2)
    
    c.execute('INSERT INTO irrigation_records (field_id, duration_minutes, water_volume_liters, scheduled_time, status, created_at) VALUES (?, ?, ?, ?, ?, ?)',
             (field_id, duration, water_volume, scheduled_time, 'Scheduled', datetime.now()))
    
    c.execute('UPDATE fields SET soil_moisture = soil_moisture + ? WHERE id = ?', (min(water_volume / 100, 15), field_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'status': 'success',
        'message': 'Irrigation started',
        'scheduled_time': scheduled_time.isoformat(),
        'duration': duration,
        'water_volume': water_volume
    })

@app.route('/api/irrigation/history/<int:field_id>', methods=['GET'])
def get_irrigation_history(field_id):
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT id, duration_minutes, water_volume_liters, scheduled_time, status, created_at FROM irrigation_records WHERE field_id = ? ORDER BY created_at DESC LIMIT 10',
             (field_id,))
    records = c.fetchall()
    
    conn.close()
    
    history = []
    for record in records:
        history.append({
            'id': record['id'],
            'duration': record['duration_minutes'],
            'water_volume': record['water_volume_liters'],
            'scheduled_time': record['scheduled_time'],
            'status': record['status'],
            'created_at': record['created_at']
        })
    
    return jsonify(history)

@app.route('/api/crop-yield-forecast', methods=['GET'])
def get_crop_yield_forecast():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''SELECT f.name, cyf.forecast_date, cyf.predicted_yield 
                 FROM crop_yield_forecast cyf 
                 JOIN fields f ON cyf.field_id = f.id 
                 ORDER BY cyf.forecast_date DESC LIMIT 28''')
    forecasts = c.fetchall()
    
    if not forecasts:
        c.execute('SELECT id, name FROM fields')
        fields = c.fetchall()
        
        for field in fields:
            for i in range(7):
                forecast_date = datetime.now().date() + timedelta(days=i)
                predicted_yield = 500 + (i * 20) + (field['id'] * 50)
                c.execute('INSERT INTO crop_yield_forecast (field_id, forecast_date, predicted_yield, created_at) VALUES (?, ?, ?, ?)',
                         (field['id'], forecast_date, predicted_yield, datetime.now()))
        
        conn.commit()
        
        c.execute('''SELECT f.name, cyf.forecast_date, cyf.predicted_yield 
                     FROM crop_yield_forecast cyf 
                     JOIN fields f ON cyf.field_id = f.id 
                     ORDER BY cyf.forecast_date DESC LIMIT 28''')
        forecasts = c.fetchall()
    
    conn.close()
    
    forecast_data = {}
    for forecast in forecasts:
        field_name = forecast[0]
        date = forecast[1]
        yield_value = forecast[2]
        
        if field_name not in forecast_data:
            forecast_data[field_name] = {'dates': [], 'yields': []}
        
        forecast_data[field_name]['dates'].append(date)
        forecast_data[field_name]['yields'].append(yield_value)
    
    return jsonify(forecast_data)

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''SELECT a.id, a.field_id, f.name, a.alert_type, a.message, a.recommendation, a.priority, a.created_at 
                 FROM alerts a 
                 JOIN fields f ON a.field_id = f.id 
                 WHERE a.resolved = 0 
                 ORDER BY a.priority DESC, a.created_at DESC''')
    alerts = c.fetchall()
    
    conn.close()
    
    alerts_list = []
    for alert in alerts:
        alerts_list.append({
            'id': alert['id'],
            'field_id': alert['field_id'],
            'field_name': alert['name'],
            'type': alert['alert_type'],
            'message': alert['message'],
            'recommendation': alert['recommendation'],
            'priority': alert['priority'],
            'created_at': alert['created_at']
        })
    
    return jsonify(alerts_list)

@app.route('/api/alerts/<int:alert_id>/resolve', methods=['PUT'])
def resolve_alert(alert_id):
    conn = get_db()
    c = conn.cursor()
    
    c.execute('UPDATE alerts SET resolved = 1 WHERE id = ?', (alert_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success', 'message': 'Alert resolved'})

@app.route('/api/alerts', methods=['POST'])
def create_alert():
    data = request.json
    field_id = data.get('field_id')
    alert_type = data.get('alert_type')
    message = data.get('message')
    recommendation = data.get('recommendation')
    priority = data.get('priority', 'Medium')
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('INSERT INTO alerts (field_id, alert_type, message, recommendation, priority, created_at) VALUES (?, ?, ?, ?, ?, ?)',
             (field_id, alert_type, message, recommendation, priority, datetime.now()))
    
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success', 'message': 'Alert created'}), 201

@app.route('/api/weather', methods=['GET'])
def get_weather():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT forecast_date, condition, min_temp, max_temp, humidity, precipitation FROM weather ORDER BY forecast_date LIMIT 5')
    weather_data = c.fetchall()
    
    conn.close()
    
    forecast = []
    for day in weather_data:
        forecast.append({
            'date': day['forecast_date'],
            'condition': day['condition'],
            'min_temp': day['min_temp'],
            'max_temp': day['max_temp'],
            'humidity': day['humidity'],
            'precipitation': day['precipitation']
        })
    
    return jsonify(forecast)

@app.route('/api/weather/update', methods=['POST'])
def update_weather():
    data = request.json
    forecast_date = data.get('forecast_date')
    condition = data.get('condition')
    min_temp = data.get('min_temp')
    max_temp = data.get('max_temp')
    humidity = data.get('humidity')
    precipitation = data.get('precipitation', 0)
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('UPDATE weather SET condition = ?, min_temp = ?, max_temp = ?, humidity = ?, precipitation = ? WHERE forecast_date = ?',
             (condition, min_temp, max_temp, humidity, precipitation, forecast_date))
    
    if c.rowcount == 0:
        c.execute('INSERT INTO weather (forecast_date, condition, min_temp, max_temp, humidity, precipitation, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                 (forecast_date, condition, min_temp, max_temp, humidity, precipitation, datetime.now()))
    
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success', 'message': 'Weather updated'})

@app.route('/api/npk-levels/<int:field_id>', methods=['GET'])
def get_npk_levels(field_id):
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT nitrogen, phosphorus, potassium, recorded_at FROM npk_levels WHERE field_id = ? ORDER BY recorded_at DESC LIMIT 10',
             (field_id,))
    npk_records = c.fetchall()
    
    conn.close()
    
    records = []
    for record in npk_records:
        records.append({
            'nitrogen': record['nitrogen'],
            'phosphorus': record['phosphorus'],
            'potassium': record['potassium'],
            'recorded_at': record['recorded_at']
        })
    
    return jsonify(records)

@app.route('/api/npk-levels/<int:field_id>', methods=['POST'])
def update_npk_levels(field_id):
    data = request.json
    nitrogen = data.get('nitrogen')
    phosphorus = data.get('phosphorus')
    potassium = data.get('potassium')
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('INSERT INTO npk_levels (field_id, nitrogen, phosphorus, potassium, recorded_at) VALUES (?, ?, ?, ?, ?)',
             (field_id, nitrogen, phosphorus, potassium, datetime.now()))
    
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success', 'message': 'NPK levels updated'}), 201

@app.route('/api/field-update', methods=['POST'])
def update_field():
    data = request.json
    field_id = data.get('field_id')
    soil_moisture = data.get('soil_moisture')
    temperature = data.get('temperature')
    health_status = data.get('health_status')
    
    conn = get_db()
    c = conn.cursor()
    
    update_fields = []
    update_values = []
    
    if soil_moisture is not None:
        update_fields.append('soil_moisture = ?')
        update_values.append(soil_moisture)
    
    if temperature is not None:
        update_fields.append('temperature = ?')
        update_values.append(temperature)
    
    if health_status is not None:
        update_fields.append('health_status = ?')
        update_values.append(health_status)
    
    if update_fields:
        update_values.append(field_id)
        query = f'UPDATE fields SET {", ".join(update_fields)} WHERE id = ?'
        c.execute(query, update_values)
        conn.commit()
    
    conn.close()
    
    return jsonify({'status': 'success', 'message': 'Field updated'})

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) as total FROM fields')
    total_fields = c.fetchone()[0]
    
    c.execute('SELECT AVG(soil_moisture) FROM fields')
    avg_moisture = c.fetchone()[0] or 0
    
    c.execute('SELECT COUNT(*) FROM irrigation_records WHERE status = "Scheduled"')
    scheduled_irrigations = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM alerts WHERE resolved = 0')
    active_alerts = c.fetchone()[0]
    
    c.execute('SELECT SUM(area_hectares) FROM fields')
    total_area = c.fetchone()[0] or 0
    
    c.execute('SELECT COUNT(DISTINCT alert_type) FROM alerts')
    alert_types = c.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'total_fields': total_fields,
        'average_moisture': round(avg_moisture, 2),
        'scheduled_irrigations': scheduled_irrigations,
        'active_alerts': active_alerts,
        'total_area_hectares': round(total_area, 2),
        'alert_types': alert_types
    })

@app.route('/api/health-check', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
