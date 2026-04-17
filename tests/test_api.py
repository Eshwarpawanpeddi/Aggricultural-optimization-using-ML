import unittest

from app import app


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_dashboard_endpoint_returns_metrics(self):
        response = self.client.get('/api/dashboard')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn('soil_moisture', payload)
        self.assertIn('npk_levels', payload)

    def test_irrigation_validation_returns_400(self):
        response = self.client.post('/api/irrigation/start', json={
            'field_id': 1,
            'duration': 2,
            'water_volume': 50
        })
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertEqual(payload['error']['code'], 'VALIDATION_ERROR')

    def test_irrigation_success_returns_201(self):
        response = self.client.post('/api/irrigation/start', json={
            'field_id': 1,
            'duration': 30,
            'water_volume': 500
        })
        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        self.assertEqual(payload['status'], 'success')

    def test_fields_pagination(self):
        response = self.client.get('/api/fields?page=1&per_page=2')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn('data', payload)
        self.assertEqual(payload['pagination']['page'], 1)

    def test_index_uses_external_js(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'/static/app.js', response.data)


if __name__ == '__main__':
    unittest.main()
