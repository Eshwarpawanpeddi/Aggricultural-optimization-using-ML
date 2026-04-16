from contextlib import contextmanager
from datetime import datetime, timedelta
from functools import wraps
import logging
import os
from queue import Empty, Queue
import sqlite3

from flask import Flask, g, jsonify, render_template, request
from flask_cors import CORS

from config import config

app = Flask(__name__, template_folder='.', static_folder='static')
app.config.from_object(config['development'])

logging.basicConfig(
    level=getattr(logging, os.environ.get('LOG_LEVEL', 'INFO').upper(), logging.INFO),
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)
logger = logging.getLogger(__name__)

CORS(app, origins=app.config.get('CORS_ORIGINS', ['*']))

DB_PATH = app.config.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///agriculture.db').replace('sqlite:///', '')
DB_POOL_SIZE = int(app.config.get('DB_POOL_SIZE', 5))
DB_CONNECTION_TIMEOUT = float(app.config.get('DB_CONNECTION_TIMEOUT', 5.0))


class APIError(Exception):
    def __init__(self, message, status_code=400, code='BAD_REQUEST', details=None):
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details
        super().__init__(message)


class SQLiteConnectionPool:
    def __init__(self, db_path, pool_size=5, timeout=5.0):
        self.db_path = db_path
        self.pool_size = max(1, int(pool_size))
        self.timeout = timeout
        self._pool = Queue(maxsize=self.pool_size)
        self._connections_created = 0

    def _create_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=self.timeout, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        self._connections_created += 1
        return conn

    def get_connection(self):
        try:
            return self._pool.get_nowait()
        except Empty:
            if self._connections_created < self.pool_size:
                return self._create_connection()

            try:
                return self._pool.get(timeout=self.timeout)
            except Empty as err:
                raise APIError('Database connection timeout', 503, 'DB_CONNECTION_TIMEOUT') from err

    def return_connection(self, conn):
        if conn is None:
            return
        try:
            self._pool.put_nowait(conn)
        except Exception:
            conn.close()

    def close_all(self):
        while True:
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Empty:
                break


pool = SQLiteConnectionPool(DB_PATH, DB_POOL_SIZE, DB_CONNECTION_TIMEOUT)


@contextmanager
def db_cursor(commit=False):
    conn = pool.get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        if commit:
            conn.commit()
    except APIError:
        conn.rollback()
        raise
    except sqlite3.Error as err:
        conn.rollback()
        logger.exception('Database error')
        raise APIError('Database operation failed', 500, 'DATABASE_ERROR', str(err)) from err
    finally:
        cursor.close()
        pool.return_connection(conn)


def fetch_one(query, params=()):
    with db_cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchone()


def fetch_all(query, params=()):
    with db_cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()


def execute_write(query, params=()):
    with db_cursor(commit=True) as cursor:
        cursor.execute(query, params)
        return cursor.lastrowid, cursor.rowcount


def parse_int(value, field_name, minimum=None, maximum=None):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise APIError(f'{field_name} must be an integer', 400, 'VALIDATION_ERROR')

    if minimum is not None and parsed < minimum:
        raise APIError(f'{field_name} must be >= {minimum}', 400, 'VALIDATION_ERROR')
    if maximum is not None and parsed > maximum:
        raise APIError(f'{field_name} must be <= {maximum}', 400, 'VALIDATION_ERROR')
    return parsed


def parse_float(value, field_name, minimum=None, maximum=None):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise APIError(f'{field_name} must be a number', 400, 'VALIDATION_ERROR')

    if minimum is not None and parsed < minimum:
        raise APIError(f'{field_name} must be >= {minimum}', 400, 'VALIDATION_ERROR')
    if maximum is not None and parsed > maximum:
        raise APIError(f'{field_name} must be <= {maximum}', 400, 'VALIDATION_ERROR')
    return parsed


def parse_date(value, field_name):
    if not value:
        raise APIError(f'{field_name} is required', 400, 'VALIDATION_ERROR')
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        raise APIError(f'{field_name} must be in YYYY-MM-DD format', 400, 'VALIDATION_ERROR')


def validate_payload(schema):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                raise APIError('Content-Type must be application/json', 415, 'UNSUPPORTED_MEDIA_TYPE')

            data = request.get_json(silent=True)
            if not isinstance(data, dict):
                raise APIError('Invalid JSON body', 400, 'INVALID_JSON')

            validated = {}
            for field, rules in schema.items():
                required = rules.get('required', False)
                if field not in data:
                    if required:
                        raise APIError(f'{field} is required', 400, 'VALIDATION_ERROR')
                    continue

                value = data.get(field)
                expected_type = rules.get('type')

                if expected_type == int:
                    value = parse_int(value, field, rules.get('min'), rules.get('max'))
                elif expected_type == float:
                    value = parse_float(value, field, rules.get('min'), rules.get('max'))
                elif expected_type == str:
                    if not isinstance(value, str) or not value.strip():
                        raise APIError(f'{field} must be a non-empty string', 400, 'VALIDATION_ERROR')
                    value = value.strip()
                elif expected_type == 'date':
                    value = parse_date(value, field)
                else:
                    raise APIError('Internal configuration error', 500, 'SERVER_CONFIG_ERROR')

                allowed = rules.get('allowed')
                if allowed and value not in allowed:
                    raise APIError(
                        f"{field} must be one of: {', '.join(map(str, allowed))}",
                        400,
                        'VALIDATION_ERROR'
                    )

                validated[field] = value

            g.validated_data = validated
            return func(*args, **kwargs)

        return wrapper

    return decorator


def get_pagination_params(default_per_page=10):
    page_raw = request.args.get('page')
    per_page_raw = request.args.get('per_page')
    if page_raw is None and per_page_raw is None:
        return None

    page = parse_int(page_raw or 1, 'page', 1)
    max_per_page = int(app.config.get('API_MAX_PAGE_SIZE', 100))
    per_page = parse_int(per_page_raw or default_per_page, 'per_page', 1, max_per_page)
    return page, per_page, (page - 1) * per_page


def paginated_response(items, total, page, per_page):
    return {
        'data': items,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': (total + per_page - 1) // per_page
        }
    }


def ensure_field_exists(field_id):
    field = fetch_one('SELECT id FROM fields WHERE id = ?', (field_id,))
    if not field:
        raise APIError('Field not found', 404, 'NOT_FOUND')


def row_to_field_summary(row):
    return {
        'id': row['id'],
        'name': row['name'],
        'area': row['area_hectares'],
        'moisture': row['soil_moisture'],
        'temperature': row['temperature'],
        'status': row['health_status']
    }


def init_db():
    with db_cursor(commit=True) as cursor:
        cursor.execute('''CREATE TABLE IF NOT EXISTS fields
                 (id INTEGER PRIMARY KEY, name TEXT UNIQUE, crop TEXT, area_hectares REAL,
                  soil_moisture REAL, temperature REAL, health_status TEXT, created_at TIMESTAMP)''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS npk_levels
                 (id INTEGER PRIMARY KEY, field_id INTEGER, nitrogen REAL, phosphorus REAL, potassium REAL,
                  recorded_at TIMESTAMP, FOREIGN KEY(field_id) REFERENCES fields(id))''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS irrigation_records
                 (id INTEGER PRIMARY KEY, field_id INTEGER, duration_minutes INTEGER, water_volume_liters REAL,
                  scheduled_time TIMESTAMP, status TEXT, created_at TIMESTAMP,
                  FOREIGN KEY(field_id) REFERENCES fields(id))''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS crop_yield_forecast
                 (id INTEGER PRIMARY KEY, field_id INTEGER, forecast_date DATE, predicted_yield REAL,
                  created_at TIMESTAMP, FOREIGN KEY(field_id) REFERENCES fields(id))''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS alerts
                 (id INTEGER PRIMARY KEY, field_id INTEGER, alert_type TEXT, message TEXT, recommendation TEXT,
                  priority TEXT, created_at TIMESTAMP, resolved INTEGER DEFAULT 0,
                  FOREIGN KEY(field_id) REFERENCES fields(id))''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS weather
                 (id INTEGER PRIMARY KEY, forecast_date DATE, condition TEXT, min_temp REAL, max_temp REAL,
                  humidity REAL, precipitation REAL, created_at TIMESTAMP)''')


def seed_initial_data():
    fields_data = [
        ('Field A - Wheat', 'Wheat', 15, 75.0, 23.0, 'Healthy'),
        ('Field B - Corn', 'Corn', 20, 68.0, 25.0, 'Needs Water'),
        ('Field C - Soybeans', 'Soybeans', 12, 80.0, 22.0, 'Excellent'),
        ('Field D - Rice', 'Rice', 18, 85.0, 26.0, 'Optimal')
    ]

    with db_cursor(commit=True) as cursor:
        for field in fields_data:
            try:
                cursor.execute(
                    'INSERT INTO fields (name, crop, area_hectares, soil_moisture, temperature, health_status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (*field, datetime.now())
                )
            except sqlite3.IntegrityError:
                logger.debug('Field already seeded: %s', field[0])

        cursor.execute('SELECT id FROM fields ORDER BY id')
        field_ids = [row[0] for row in cursor.fetchall()]

        if field_ids:
            npk_data = [
                (field_ids[0], 68, 45, 72),
                (field_ids[1], 55, 35, 60),
                (field_ids[2], 70, 50, 75),
                (field_ids[3], 75, 55, 80)
            ]

            for npk in npk_data:
                cursor.execute(
                    'INSERT INTO npk_levels (field_id, nitrogen, phosphorus, potassium, recorded_at) VALUES (?, ?, ?, ?, ?)',
                    (*npk, datetime.now())
                )

            cursor.execute(
                'INSERT INTO alerts (field_id, alert_type, message, recommendation, priority, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                (field_ids[1], 'Nutrient Deficiency', 'Low Phosphorus in Field B', 'Apply phosphate fertilizer within 3 days', 'High', datetime.now())
            )
            cursor.execute(
                'INSERT INTO alerts (field_id, alert_type, message, recommendation, priority, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                (field_ids[0], 'Irrigation Scheduled', 'Irrigation Scheduled for Field A', 'Next irrigation: Today at 6:00 PM (2 hours remaining)', 'Medium', datetime.now())
            )

        weather_data = [
            (datetime.now().date(), 'Clear', 20, 28, 65, 0),
            ((datetime.now() + timedelta(days=1)).date(), 'Partly Cloudy', 19, 27, 70, 5),
            ((datetime.now() + timedelta(days=2)).date(), 'Clear', 21, 29, 60, 0),
            ((datetime.now() + timedelta(days=3)).date(), 'Clear', 20, 28, 65, 0),
            ((datetime.now() + timedelta(days=4)).date(), 'Clear', 22, 30, 55, 0)
        ]

        for weather in weather_data:
            cursor.execute(
                'INSERT INTO weather (forecast_date, condition, min_temp, max_temp, humidity, precipitation, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (*weather, datetime.now())
            )


init_db()
try:
    existing_fields = fetch_one('SELECT COUNT(*) AS count FROM fields')
    if existing_fields and existing_fields['count'] == 0:
        seed_initial_data()
except APIError:
    logger.exception('Failed during startup seed check')


@app.errorhandler(APIError)
def handle_api_error(error):
    payload = {
        'error': {
            'code': error.code,
            'message': error.message
        }
    }
    if error.details:
        payload['error']['details'] = error.details
    return jsonify(payload), error.status_code


@app.errorhandler(404)
def handle_404(_error):
    return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Resource not found'}}), 404


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    logger.exception('Unhandled application error')
    return jsonify({'error': {'code': 'INTERNAL_SERVER_ERROR', 'message': 'An unexpected error occurred'}}), 500


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    dashboard = fetch_one('''
        SELECT
            COALESCE(AVG(soil_moisture), 72) AS avg_moisture,
            COALESCE(AVG(temperature), 24) AS avg_temp,
            COALESCE(SUM(CASE WHEN health_status IN ('Healthy', 'Excellent', 'Optimal') THEN 1 ELSE 0 END), 0) AS healthy_count,
            COUNT(*) AS total_fields
        FROM fields
    ''')

    npk_row = fetch_one('SELECT nitrogen, phosphorus, potassium FROM npk_levels ORDER BY recorded_at DESC LIMIT 1')

    total_fields = dashboard['total_fields'] or 0
    crop_health = (dashboard['healthy_count'] / total_fields * 100) if total_fields > 0 else 85

    return jsonify({
        'soil_moisture': round(dashboard['avg_moisture'], 1),
        'temperature': round(dashboard['avg_temp'], 1),
        'npk_levels': {
            'n': npk_row['nitrogen'] if npk_row else 68,
            'p': npk_row['phosphorus'] if npk_row else 45,
            'k': npk_row['potassium'] if npk_row else 72,
        },
        'crop_health': round(crop_health, 1)
    })


@app.route('/api/fields', methods=['GET'])
def get_fields():
    pagination = get_pagination_params(default_per_page=app.config.get('API_DEFAULT_PAGE_SIZE', 10))

    if pagination:
        page, per_page, offset = pagination
        total_row = fetch_one('SELECT COUNT(*) AS total FROM fields')
        rows = fetch_all(
            'SELECT id, name, area_hectares, soil_moisture, temperature, health_status FROM fields ORDER BY id LIMIT ? OFFSET ?',
            (per_page, offset)
        )
        items = [row_to_field_summary(row) for row in rows]
        return jsonify(paginated_response(items, total_row['total'], page, per_page))

    rows = fetch_all('SELECT id, name, area_hectares, soil_moisture, temperature, health_status FROM fields ORDER BY id')
    return jsonify([row_to_field_summary(row) for row in rows])


@app.route('/api/field/<int:field_id>', methods=['GET'])
def get_field_detail(field_id):
    row = fetch_one('''
        SELECT f.id, f.name, f.crop, f.area_hectares, f.soil_moisture, f.temperature, f.health_status,
               n.nitrogen, n.phosphorus, n.potassium
        FROM fields f
        LEFT JOIN npk_levels n
          ON n.id = (
              SELECT id FROM npk_levels
              WHERE field_id = f.id
              ORDER BY recorded_at DESC
              LIMIT 1
          )
        WHERE f.id = ?
    ''', (field_id,))

    if not row:
        raise APIError('Field not found', 404, 'NOT_FOUND')

    return jsonify({
        'id': row['id'],
        'name': row['name'],
        'crop': row['crop'],
        'area': row['area_hectares'],
        'moisture': row['soil_moisture'],
        'temperature': row['temperature'],
        'status': row['health_status'],
        'npk': {
            'nitrogen': row['nitrogen'],
            'phosphorus': row['phosphorus'],
            'potassium': row['potassium']
        } if row['nitrogen'] is not None else None
    })


@app.route('/api/irrigation/start', methods=['POST'])
@validate_payload({
    'field_id': {'type': int, 'required': True, 'min': 1},
    'duration': {'type': int, 'required': True, 'min': 5, 'max': 120},
    'water_volume': {'type': float, 'required': True, 'min': 100, 'max': 5000}
})
def start_irrigation():
    data = g.validated_data
    field_id = data['field_id']
    duration = data['duration']
    water_volume = data['water_volume']

    ensure_field_exists(field_id)
    scheduled_time = datetime.now() + timedelta(minutes=2)
    moisture_increase = min(water_volume / 100, 15)

    with db_cursor(commit=True) as cursor:
        cursor.execute(
            'INSERT INTO irrigation_records (field_id, duration_minutes, water_volume_liters, scheduled_time, status, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            (field_id, duration, water_volume, scheduled_time, 'Scheduled', datetime.now())
        )
        cursor.execute(
            'UPDATE fields SET soil_moisture = CASE WHEN soil_moisture + ? > 100 THEN 100 ELSE soil_moisture + ? END WHERE id = ?',
            (moisture_increase, moisture_increase, field_id)
        )

    return jsonify({
        'status': 'success',
        'message': 'Irrigation started',
        'scheduled_time': scheduled_time.isoformat(),
        'duration': duration,
        'water_volume': water_volume
    }), 201


@app.route('/api/irrigation/history/<int:field_id>', methods=['GET'])
def get_irrigation_history(field_id):
    ensure_field_exists(field_id)
    pagination = get_pagination_params(default_per_page=10)

    if pagination:
        page, per_page, offset = pagination
        total_row = fetch_one('SELECT COUNT(*) AS total FROM irrigation_records WHERE field_id = ?', (field_id,))
        records = fetch_all(
            'SELECT id, duration_minutes, water_volume_liters, scheduled_time, status, created_at FROM irrigation_records WHERE field_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?',
            (field_id, per_page, offset)
        )
        data = [{
            'id': r['id'],
            'duration': r['duration_minutes'],
            'water_volume': r['water_volume_liters'],
            'scheduled_time': r['scheduled_time'],
            'status': r['status'],
            'created_at': r['created_at']
        } for r in records]
        return jsonify(paginated_response(data, total_row['total'], page, per_page))

    records = fetch_all(
        'SELECT id, duration_minutes, water_volume_liters, scheduled_time, status, created_at FROM irrigation_records WHERE field_id = ? ORDER BY created_at DESC LIMIT 10',
        (field_id,)
    )

    return jsonify([{
        'id': record['id'],
        'duration': record['duration_minutes'],
        'water_volume': record['water_volume_liters'],
        'scheduled_time': record['scheduled_time'],
        'status': record['status'],
        'created_at': record['created_at']
    } for record in records])


@app.route('/api/crop-yield-forecast', methods=['GET'])
def get_crop_yield_forecast():
    forecasts = fetch_all('''
        SELECT f.name, cyf.forecast_date, cyf.predicted_yield
        FROM crop_yield_forecast cyf
        JOIN fields f ON cyf.field_id = f.id
        ORDER BY cyf.forecast_date DESC
        LIMIT 28
    ''')

    if not forecasts:
        with db_cursor(commit=True) as cursor:
            cursor.execute('SELECT id FROM fields ORDER BY id')
            fields = cursor.fetchall()

            for field in fields:
                for i in range(7):
                    forecast_date = datetime.now().date() + timedelta(days=i)
                    predicted_yield = 500 + (i * 20) + (field['id'] * 50)
                    cursor.execute(
                        'INSERT INTO crop_yield_forecast (field_id, forecast_date, predicted_yield, created_at) VALUES (?, ?, ?, ?)',
                        (field['id'], forecast_date, predicted_yield, datetime.now())
                    )

        forecasts = fetch_all('''
            SELECT f.name, cyf.forecast_date, cyf.predicted_yield
            FROM crop_yield_forecast cyf
            JOIN fields f ON cyf.field_id = f.id
            ORDER BY cyf.forecast_date DESC
            LIMIT 28
        ''')

    forecast_data = {}
    for forecast in forecasts:
        field_name = forecast['name']
        if field_name not in forecast_data:
            forecast_data[field_name] = {'dates': [], 'yields': []}
        forecast_data[field_name]['dates'].append(forecast['forecast_date'])
        forecast_data[field_name]['yields'].append(forecast['predicted_yield'])

    return jsonify(forecast_data)


@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    pagination = get_pagination_params(default_per_page=10)

    total_query = '''
        SELECT COUNT(*) AS total
        FROM alerts a
        JOIN fields f ON a.field_id = f.id
        WHERE a.resolved = 0
    '''
    list_query = '''
        SELECT a.id, a.field_id, f.name, a.alert_type, a.message, a.recommendation, a.priority, a.created_at
        FROM alerts a
        JOIN fields f ON a.field_id = f.id
        WHERE a.resolved = 0
        ORDER BY a.priority DESC, a.created_at DESC
    '''

    if pagination:
        page, per_page, offset = pagination
        total_row = fetch_one(total_query)
        alerts = fetch_all(
            list_query + ' LIMIT ? OFFSET ?',
            (per_page, offset)
        )
        data = [{
            'id': alert['id'],
            'field_id': alert['field_id'],
            'field_name': alert['name'],
            'type': alert['alert_type'],
            'message': alert['message'],
            'recommendation': alert['recommendation'],
            'priority': alert['priority'],
            'created_at': alert['created_at']
        } for alert in alerts]
        return jsonify(paginated_response(data, total_row['total'], page, per_page))

    alerts = fetch_all(list_query)

    return jsonify([{
        'id': alert['id'],
        'field_id': alert['field_id'],
        'field_name': alert['name'],
        'type': alert['alert_type'],
        'message': alert['message'],
        'recommendation': alert['recommendation'],
        'priority': alert['priority'],
        'created_at': alert['created_at']
    } for alert in alerts])


@app.route('/api/alerts/<int:alert_id>/resolve', methods=['PUT'])
def resolve_alert(alert_id):
    _id, rowcount = execute_write('UPDATE alerts SET resolved = 1 WHERE id = ?', (alert_id,))
    if rowcount == 0:
        raise APIError('Alert not found', 404, 'NOT_FOUND')
    return jsonify({'status': 'success', 'message': 'Alert resolved'})


@app.route('/api/alerts', methods=['POST'])
@validate_payload({
    'field_id': {'type': int, 'required': True, 'min': 1},
    'alert_type': {'type': str, 'required': True},
    'message': {'type': str, 'required': True},
    'recommendation': {'type': str, 'required': True},
    'priority': {'type': str, 'required': False, 'allowed': ['Low', 'Medium', 'High']}
})
def create_alert():
    data = g.validated_data
    ensure_field_exists(data['field_id'])
    priority = data.get('priority', 'Medium')

    execute_write(
        'INSERT INTO alerts (field_id, alert_type, message, recommendation, priority, created_at) VALUES (?, ?, ?, ?, ?, ?)',
        (data['field_id'], data['alert_type'], data['message'], data['recommendation'], priority, datetime.now())
    )

    return jsonify({'status': 'success', 'message': 'Alert created'}), 201


@app.route('/api/weather', methods=['GET'])
def get_weather():
    weather_data = fetch_all(
        'SELECT forecast_date, condition, min_temp, max_temp, humidity, precipitation FROM weather ORDER BY forecast_date LIMIT ?',
        (app.config.get('WEATHER_FORECAST_DAYS', 5),)
    )

    return jsonify([{
        'date': day['forecast_date'],
        'condition': day['condition'],
        'min_temp': day['min_temp'],
        'max_temp': day['max_temp'],
        'humidity': day['humidity'],
        'precipitation': day['precipitation']
    } for day in weather_data])


@app.route('/api/weather/update', methods=['POST'])
@validate_payload({
    'forecast_date': {'type': 'date', 'required': True},
    'condition': {'type': str, 'required': True},
    'min_temp': {'type': float, 'required': True, 'min': -50, 'max': 70},
    'max_temp': {'type': float, 'required': True, 'min': -50, 'max': 70},
    'humidity': {'type': float, 'required': True, 'min': 0, 'max': 100},
    'precipitation': {'type': float, 'required': False, 'min': 0}
})
def update_weather():
    data = g.validated_data
    precipitation = data.get('precipitation', 0.0)

    with db_cursor(commit=True) as cursor:
        cursor.execute(
            'UPDATE weather SET condition = ?, min_temp = ?, max_temp = ?, humidity = ?, precipitation = ? WHERE forecast_date = ?',
            (data['condition'], data['min_temp'], data['max_temp'], data['humidity'], precipitation, data['forecast_date'])
        )

        if cursor.rowcount == 0:
            cursor.execute(
                'INSERT INTO weather (forecast_date, condition, min_temp, max_temp, humidity, precipitation, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (data['forecast_date'], data['condition'], data['min_temp'], data['max_temp'], data['humidity'], precipitation, datetime.now())
            )

    return jsonify({'status': 'success', 'message': 'Weather updated'})


@app.route('/api/npk-levels/<int:field_id>', methods=['GET'])
def get_npk_levels(field_id):
    ensure_field_exists(field_id)
    pagination = get_pagination_params(default_per_page=10)

    if pagination:
        page, per_page, offset = pagination
        total_row = fetch_one('SELECT COUNT(*) AS total FROM npk_levels WHERE field_id = ?', (field_id,))
        npk_records = fetch_all(
            'SELECT nitrogen, phosphorus, potassium, recorded_at FROM npk_levels WHERE field_id = ? ORDER BY recorded_at DESC LIMIT ? OFFSET ?',
            (field_id, per_page, offset)
        )
        data = [{
            'nitrogen': record['nitrogen'],
            'phosphorus': record['phosphorus'],
            'potassium': record['potassium'],
            'recorded_at': record['recorded_at']
        } for record in npk_records]
        return jsonify(paginated_response(data, total_row['total'], page, per_page))

    npk_records = fetch_all(
        'SELECT nitrogen, phosphorus, potassium, recorded_at FROM npk_levels WHERE field_id = ? ORDER BY recorded_at DESC LIMIT 10',
        (field_id,)
    )

    return jsonify([{
        'nitrogen': record['nitrogen'],
        'phosphorus': record['phosphorus'],
        'potassium': record['potassium'],
        'recorded_at': record['recorded_at']
    } for record in npk_records])


@app.route('/api/npk-levels/<int:field_id>', methods=['POST'])
@validate_payload({
    'nitrogen': {'type': float, 'required': True, 'min': 0},
    'phosphorus': {'type': float, 'required': True, 'min': 0},
    'potassium': {'type': float, 'required': True, 'min': 0}
})
def update_npk_levels(field_id):
    ensure_field_exists(field_id)
    data = g.validated_data

    execute_write(
        'INSERT INTO npk_levels (field_id, nitrogen, phosphorus, potassium, recorded_at) VALUES (?, ?, ?, ?, ?)',
        (field_id, data['nitrogen'], data['phosphorus'], data['potassium'], datetime.now())
    )

    return jsonify({'status': 'success', 'message': 'NPK levels updated'}), 201


@app.route('/api/field-update', methods=['POST'])
@validate_payload({
    'field_id': {'type': int, 'required': True, 'min': 1},
    'soil_moisture': {'type': float, 'required': False, 'min': 0, 'max': 100},
    'temperature': {'type': float, 'required': False, 'min': -50, 'max': 70},
    'health_status': {'type': str, 'required': False}
})
def update_field():
    data = g.validated_data
    field_id = data['field_id']
    ensure_field_exists(field_id)

    soil_moisture = data.get('soil_moisture')
    temperature = data.get('temperature')
    health_status = data.get('health_status')

    if soil_moisture is None and temperature is None and health_status is None:
        raise APIError('At least one field value must be provided', 400, 'VALIDATION_ERROR')

    execute_write(
        '''
        UPDATE fields
        SET soil_moisture = COALESCE(?, soil_moisture),
            temperature = COALESCE(?, temperature),
            health_status = COALESCE(?, health_status)
        WHERE id = ?
        ''',
        (soil_moisture, temperature, health_status, field_id)
    )

    return jsonify({'status': 'success', 'message': 'Field updated'})


@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    data = fetch_one('''
        SELECT
            COUNT(*) AS total_fields,
            COALESCE(AVG(soil_moisture), 0) AS avg_moisture,
            COALESCE(SUM(area_hectares), 0) AS total_area
        FROM fields
    ''')
    scheduled_irrigations = fetch_one('SELECT COUNT(*) AS total FROM irrigation_records WHERE status = ?', ('Scheduled',))
    active_alerts = fetch_one('SELECT COUNT(*) AS total FROM alerts WHERE resolved = 0')
    alert_types = fetch_one('SELECT COUNT(DISTINCT alert_type) AS total FROM alerts')

    return jsonify({
        'total_fields': data['total_fields'],
        'average_moisture': round(data['avg_moisture'], 2),
        'scheduled_irrigations': scheduled_irrigations['total'],
        'active_alerts': active_alerts['total'],
        'total_area_hectares': round(data['total_area'], 2),
        'alert_types': alert_types['total']
    })


@app.route('/api/health-check', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})


if __name__ == '__main__':
    app.run(
        debug=app.config['DEBUG'],
        host='0.0.0.0',
        port=5000
    )
