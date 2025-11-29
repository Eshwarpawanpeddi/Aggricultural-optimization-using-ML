# Precision Crop Management System - Setup Guide

## Project Structure

```
project-root/
├── app.py                 (Backend Flask application)
├── requirements.txt       (Python dependencies)
├── index.html            (Frontend HTML with integrated API calls)
├── templates/
│   └── new.html          (Alternative template)
└── agriculture.db        (SQLite database - auto-created)
```

## Installation & Setup

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Directory Setup
Create a `templates` folder and place HTML files:
```bash
mkdir templates
```

### 3. Run the Backend Server
```bash
python app.py
```

The server will start at: `http://localhost:5000`

### 4. Access Frontend
Open in browser: `http://localhost:5000/`

## Features Implemented

### Dashboard Metrics
- Real-time Soil Moisture monitoring
- Temperature tracking
- NPK Levels (Nitrogen, Phosphorus, Potassium)
- Crop Health Assessment
- All metrics update every 30 seconds

### Irrigation Control System
- Field selection dropdown
- Customizable irrigation duration (5-120 minutes)
- Water volume adjustment (100-5000 liters)
- Automatic soil moisture updates after irrigation
- Scheduled irrigation tracking

### Field Management
- 4 Pre-configured fields (Wheat, Corn, Soybeans, Rice)
- Individual field monitoring
- Area, moisture, temperature, and health status tracking
- Field-specific data storage

### Crop Yield Forecasting
- 7-day forecast per field
- Interactive line chart visualization
- Predictive yield data in kg/hectare
- Multi-field comparison

### Alerts & Recommendations
- Real-time alert system
- Priority-based alert display (High, Medium, Low)
- Actionable recommendations for each alert
- Alert resolution tracking
- Auto-generated alerts for nutrient deficiencies and irrigation schedules

### Weather Forecasting
- 5-day weather forecast
- Temperature range (min/max)
- Humidity levels
- Precipitation data
- Condition descriptions

## API Endpoints

### Dashboard
- `GET /api/dashboard` - Get all dashboard metrics
- `POST /api/field-update` - Update field data

### Fields Management
- `GET /api/fields` - Get all fields
- `GET /api/field/<field_id>` - Get specific field details

### Irrigation
- `POST /api/irrigation/start` - Start irrigation for a field
- `GET /api/irrigation/history/<field_id>` - Get irrigation history

### NPK Levels
- `GET /api/npk-levels/<field_id>` - Get NPK history
- `POST /api/npk-levels/<field_id>` - Update NPK levels

### Crop Yield
- `GET /api/crop-yield-forecast` - Get yield predictions

### Alerts
- `GET /api/alerts` - Get all active alerts
- `POST /api/alerts` - Create new alert
- `PUT /api/alerts/<alert_id>/resolve` - Mark alert as resolved

### Weather
- `GET /api/weather` - Get weather forecast
- `POST /api/weather/update` - Update weather data

### Analytics
- `GET /api/analytics` - Get system analytics
- `GET /api/health-check` - Check API health

## Database Schema

### fields table
```sql
id, name, crop, area_hectares, soil_moisture, temperature, health_status, created_at
```

### npk_levels table
```sql
id, field_id, nitrogen, phosphorus, potassium, recorded_at
```

### irrigation_records table
```sql
id, field_id, duration_minutes, water_volume_liters, scheduled_time, status, created_at
```

### crop_yield_forecast table
```sql
id, field_id, forecast_date, predicted_yield, created_at
```

### alerts table
```sql
id, field_id, alert_type, message, recommendation, priority, created_at, resolved
```

### weather table
```sql
id, forecast_date, condition, min_temp, max_temp, humidity, precipitation, created_at
```

## Default Data

System initializes with:
- 4 fields: Wheat (Field A), Corn (Field B), Soybeans (Field C), Rice (Field D)
- Sample NPK levels for each field
- Initial weather forecast for 5 days
- Pre-loaded alerts for demonstration

## Browser Compatibility

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Responsive design for mobile devices

## Configuration Options

### Database
To use a different database path, modify in app.py:
```python
DB_PATH = 'agriculture.db'
```

### Server Port
To change Flask server port, modify:
```python
app.run(debug=True, host='0.0.0.0', port=5000)
```

### CORS Settings
Frontend and backend can run on different ports due to CORS configuration.

## Troubleshooting

### Database Already Exists
Delete `agriculture.db` to reset:
```bash
rm agriculture.db
python app.py
```

### Port Already in Use
Change port in app.py or kill existing process:
```bash
lsof -i :5000
kill -9 <PID>
```

### CORS Errors
Ensure Flask-CORS is installed:
```bash
pip install Flask-CORS
```

### Frontend Not Loading Data
1. Check API server is running on port 5000
2. Open browser console for errors (F12)
3. Verify CORS settings in app.py

## Production Deployment

For production:
1. Set `debug=False` in app.py
2. Use production WSGI server (Gunicorn, uWSGI)
3. Set up reverse proxy (Nginx, Apache)
4. Use environment variables for configuration
5. Implement authentication/authorization
6. Use PostgreSQL instead of SQLite
7. Enable HTTPS/SSL

## License
Educational Project
