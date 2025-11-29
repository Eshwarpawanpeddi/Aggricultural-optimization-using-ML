import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///agriculture.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    JSON_SORT_KEYS = False
    
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    IRRIGATION_UPDATE_INTERVAL = 30000
    ALERT_CHECK_INTERVAL = 30000
    
    SOIL_MOISTURE_THRESHOLD_LOW = 40
    SOIL_MOISTURE_THRESHOLD_HIGH = 85
    SOIL_MOISTURE_THRESHOLD_OPTIMAL_MIN = 60
    SOIL_MOISTURE_THRESHOLD_OPTIMAL_MAX = 75
    
    TEMPERATURE_MIN = 15
    TEMPERATURE_MAX = 35
    
    NPK_NITROGEN_MIN = 50
    NPK_PHOSPHORUS_MIN = 30
    NPK_POTASSIUM_MIN = 50
    
    CROP_YIELD_FORECAST_DAYS = 7
    WEATHER_FORECAST_DAYS = 5
    
    DEBUG = os.environ.get('DEBUG', False)
    TESTING = False


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
