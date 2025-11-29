# Precision Crop Management System

A complete AI-powered agricultural management platform with real-time monitoring, irrigation control, crop health assessment, and predictive analytics.

## Overview

This system provides farmers and agricultural managers with comprehensive tools to monitor and manage crop fields efficiently. Built with a modern web interface and robust backend, it enables data-driven decisions for better crop yields.

## Key Features

### 🌾 Dashboard Metrics
- **Soil Moisture**: Real-time average moisture levels across fields
- **Temperature**: Current ambient temperature monitoring
- **NPK Levels**: Nitrogen, Phosphorus, Potassium tracking
- **Crop Health**: AI-based health assessment with percentage scores

### 💧 Irrigation Control
- **Smart Field Selection**: Choose specific fields for irrigation
- **Customizable Parameters**: Adjustable duration (5-120 minutes) and water volume (100-5000 liters)
- **Automatic Updates**: Soil moisture automatically updates post-irrigation
- **Schedule Tracking**: View scheduled and completed irrigation records

### 🌾 Field Management
- **4 Pre-configured Fields**: Wheat, Corn, Soybeans, Rice
- **Individual Monitoring**: Track each field independently
- **Real-time Status**: Area, moisture, temperature, and health status
- **Historical Data**: Complete data storage for analysis

### 📊 Crop Yield Forecasting
- **7-Day Predictions**: Forecasted yields per field in kg/hectare
- **Interactive Charts**: Visual representation using Chart.js
- **Multi-field Comparison**: Compare yields across all fields
- **Data Trending**: Track yield patterns over time

### ⚠️ Alerts & Recommendations
- **Real-time Notifications**: Immediate alerts for critical issues
- **Priority System**: High, Medium, Low priority alerts
- **Actionable Recommendations**: Specific suggestions for each alert
- **Resolution Tracking**: Mark alerts as resolved

### 🌤️ Weather Forecasting
- **5-Day Forecast**: Complete weather prediction
- **Detailed Metrics**: Temperature range, humidity, precipitation
- **Optimal Planning**: Plan field operations based on weather
- **Real-time Updates**: Current condition descriptions

## Technology Stack

### Backend
- **Framework**: Flask 2.3.3
- **Database**: SQLite3
- **CORS**: Flask-CORS for cross-origin requests
- **Language**: Python 3.8+

### Frontend
- **HTML5**: Semantic markup
- **CSS3**: Modern styling with gradients and flexbox
- **JavaScript**: Vanilla JS with async/await
- **Charts**: Chart.js for data visualization
- **Responsive Design**: Mobile-friendly interface

## Project Structure

```
project-root/
├── app.py                    # Main Flask application
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── index.html             # Main frontend interface
├── start.sh               # Linux/Mac startup script
├── start.bat              # Windows startup script
├── templates/             # Template directory
│   └── new.html          # Alternative template
├── agriculture.db        # SQLite database (auto-created)
├── SETUP.md             # Setup instructions
└── README.md            # This file
```

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Quick Start

#### Linux/Mac
```bash
chmod +x start.sh
./start.sh
```

#### Windows
```bash
start.bat
```

#### Manual Installation
```bash
pip install -r requirements.txt
python app.py
```

### Access the Application
Open your browser and navigate to: `http://localhost:5000`

## Usage Guide

### Dashboard
1. **View Metrics**: See real-time data on the dashboard cards
2. **Monitor Fields**: Check individual field status in the overview
3. **Track Alerts**: Review active alerts and recommendations

### Irrigation Management
1. Select a field from the dropdown
2. Set irrigation duration (minutes)
3. Specify water volume (liters)
4. Click "Start Irrigation" to schedule

### Field Monitoring
- View all fields in the Field Overview section
- Check moisture, temperature, and health status
- Click individual field cards for detailed information

### Crop Yield
- Monitor the 7-day forecast chart
- Compare yields across different fields
- Plan harvest timing based on predictions

### Weather Planning
- Check 5-day weather forecast
- Plan outdoor operations accordingly
- Monitor precipitation for irrigation scheduling

## API Endpoints

### Core Endpoints

#### Dashboard
```
GET  /api/dashboard              # Get all dashboard metrics
```

#### Fields
```
GET  /api/fields                 # Get all fields
GET  /api/field/<field_id>       # Get specific field details
POST /api/field-update           # Update field data
```

#### Irrigation
```
POST /api/irrigation/start           # Start irrigation
GET  /api/irrigation/history/<field_id>  # Get history
```

#### NPK Management
```
GET  /api/npk-levels/<field_id>  # Get NPK history
POST /api/npk-levels/<field_id>  # Update NPK levels
```

#### Crop Yield
```
GET  /api/crop-yield-forecast    # Get yield predictions
```

#### Alerts
```
GET  /api/alerts                 # Get all active alerts
POST /api/alerts                 # Create new alert
PUT  /api/alerts/<alert_id>/resolve  # Resolve alert
```

#### Weather
```
GET  /api/weather                # Get weather forecast
POST /api/weather/update         # Update weather data
```

#### Analytics
```
GET  /api/analytics              # Get system analytics
GET  /api/health-check           # Check API health
```

## Database Schema

### Fields Table
Stores information about each farm field
```sql
- id (INTEGER PRIMARY KEY)
- name (TEXT UNIQUE)
- crop (TEXT)
- area_hectares (REAL)
- soil_moisture (REAL)
- temperature (REAL)
- health_status (TEXT)
- created_at (TIMESTAMP)
```

### NPK Levels Table
Tracks nutrient levels over time
```sql
- id (INTEGER PRIMARY KEY)
- field_id (FOREIGN KEY)
- nitrogen (REAL)
- phosphorus (REAL)
- potassium (REAL)
- recorded_at (TIMESTAMP)
```

### Irrigation Records Table
Logs all irrigation activities
```sql
- id (INTEGER PRIMARY KEY)
- field_id (FOREIGN KEY)
- duration_minutes (INTEGER)
- water_volume_liters (REAL)
- scheduled_time (TIMESTAMP)
- status (TEXT)
- created_at (TIMESTAMP)
```

### Crop Yield Forecast Table
Stores yield predictions
```sql
- id (INTEGER PRIMARY KEY)
- field_id (FOREIGN KEY)
- forecast_date (DATE)
- predicted_yield (REAL)
- created_at (TIMESTAMP)
```

### Alerts Table
Manages system alerts and notifications
```sql
- id (INTEGER PRIMARY KEY)
- field_id (FOREIGN KEY)
- alert_type (TEXT)
- message (TEXT)
- recommendation (TEXT)
- priority (TEXT)
- created_at (TIMESTAMP)
- resolved (INTEGER)
```

### Weather Table
Weather forecast data
```sql
- id (INTEGER PRIMARY KEY)
- forecast_date (DATE)
- condition (TEXT)
- min_temp (REAL)
- max_temp (REAL)
- humidity (REAL)
- precipitation (REAL)
- created_at (TIMESTAMP)
```

## Configuration

### Environment Variables
Create a `.env` file in the root directory:
```
FLASK_ENV=development
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///agriculture.db
CORS_ORIGINS=*
```

### Configuration File
Edit `config.py` to customize:
- Soil moisture thresholds
- Temperature limits
- NPK minimum levels
- Forecast periods
- Update intervals

## Troubleshooting

### Issue: Port 5000 Already in Use
```bash
# Linux/Mac
lsof -i :5000
kill -9 <PID>

# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### Issue: Database Errors
```bash
rm agriculture.db
python app.py
```

### Issue: CORS Errors
- Check Flask-CORS is installed: `pip install Flask-CORS`
- Verify CORS configuration in app.py
- Clear browser cache

### Issue: Chart Not Displaying
- Check browser console for JavaScript errors (F12)
- Verify Chart.js CDN is accessible
- Ensure API endpoints are returning valid data

## Performance Optimization

### For Production
1. **Use Production Server**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

2. **Enable Caching**
   ```python
   from flask_caching import Cache
   cache = Cache(app, config={'CACHE_TYPE': 'simple'})
   ```

3. **Database Optimization**
   - Add indexes to frequently queried columns
   - Consider PostgreSQL for large datasets
   - Implement database connection pooling

4. **Frontend Optimization**
   - Minify CSS and JavaScript
   - Enable gzip compression
   - Use CDN for static files

## Security Recommendations

1. **Change Secret Key** in production
2. **Enable HTTPS/SSL** for data encryption
3. **Implement Authentication** for user access control
4. **Use Environment Variables** for sensitive data
5. **Validate All Inputs** on both frontend and backend
6. **Enable CSRF Protection** in production
7. **Set Secure Cookie Flags** in production

## Monitoring & Maintenance

### Regular Tasks
- **Daily**: Monitor active alerts and crop health
- **Weekly**: Review yield forecasts and weather impacts
- **Monthly**: Analyze historical data trends
- **Quarterly**: Update weather forecasts and maintenance

### Logging
Enable detailed logging by modifying app.py:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## API Response Examples

### Dashboard Metrics
```json
{
  "soil_moisture": 72.5,
  "temperature": 24.3,
  "npk_levels": {
    "n": 68,
    "p": 45,
    "k": 72
  },
  "crop_health": 85.2
}
```

### Field Details
```json
{
  "id": 1,
  "name": "Field A - Wheat",
  "crop": "Wheat",
  "area": 15,
  "moisture": 75,
  "temperature": 23,
  "status": "Healthy",
  "npk": {
    "nitrogen": 68,
    "phosphorus": 45,
    "potassium": 72
  }
}
```

## Future Enhancements

1. **Machine Learning Models** for better predictions
2. **Mobile App** for iOS and Android
3. **Satellite Integration** for large-scale monitoring
4. **IoT Sensor Integration** for real-time data collection
5. **Advanced Analytics** with data export capabilities
6. **Multi-language Support** for global users
7. **Role-based Access Control** for team management
8. **Historical Analysis** and reporting features

## Contributing

To contribute to this project:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a pull request

## License

This project is provided for educational purposes.

## Support

For issues and questions:
1. Check the SETUP.md file
2. Review the troubleshooting section
3. Check API documentation above
4. Review browser console for errors (F12)

## Acknowledgments

Built with modern web technologies and agricultural best practices to support efficient farm management and sustainable crop production.

---

**Version**: 1.0.0  
**Last Updated**: November 2025  
**Status**: Production Ready
