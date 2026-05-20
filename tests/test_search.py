import atexit
import json
import os
import tempfile
import unittest

TEST_DB = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
TEST_DB.close()
os.environ['INVENTORY_DATABASE_PATH'] = TEST_DB.name


@atexit.register
def cleanup_test_db():
    if os.path.exists(TEST_DB.name):
        os.remove(TEST_DB.name)

from app import app, db
from models import Bin, Part, SearchFeedback
from search import normalize_query, search_parts


class SearchTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        with app.app_context():
            db.drop_all()
            db.create_all()
            drawer = Bin(name='Drawer 1', shelf='Workbench', row='1', position='Top')
            wire_bin = Bin(name='Wire Rack', shelf='A', row='1', position='Left')
            wire = Part(
                part_number='WIR-ROSL-0001',
                name='Roslau Wire 1-Lb. Coils',
                category='Wire & Strings',
                description='Piano wire coils for restringing',
                quantity=3,
                min_threshold=2,
                locations=[wire_bin],
            )
            center_pins = Part(
                part_number='CEN-PINS-0002',
                name='Center Pins 2 Oz Pkg',
                category='Center Pins',
                description='Action center pins package',
                quantity=12,
                min_threshold=5,
                locations=[drawer],
            )
            felt = Part(
                part_number='FEL-BUSH-0003',
                name='English Key Bushing Cloth',
                category='Felt & Cloth',
                description='Cloth for key bushing repairs',
                quantity=1,
                min_threshold=3,
                locations=[drawer],
            )
            db.session.add_all([drawer, wire_bin, wire, center_pins, felt])
            db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_normalize_query(self):
        self.assertEqual(normalize_query(' Center Pins, 2 oz! '), 'center pins 2 oz')

    def test_part_number_exact_match_ranks_first(self):
        with app.app_context():
            parts = Part.query.all()
            results = search_parts('CEN-PINS-0002', parts)
        self.assertEqual(results[0].part.part_number, 'CEN-PINS-0002')

    def test_natural_language_queries_find_expected_parts(self):
        cases = {
            'wire coils': 'Roslau Wire 1-Lb. Coils',
            'center pins 2 oz': 'Center Pins 2 Oz Pkg',
            'felt for key bushings': 'English Key Bushing Cloth',
            'low stock felt parts': 'English Key Bushing Cloth',
        }
        with app.app_context():
            parts = Part.query.all()
            for query, expected_name in cases.items():
                results = search_parts(query, parts)
                self.assertTrue(results, query)
                self.assertEqual(results[0].part.name, expected_name, query)
            drawer_results = search_parts('stuff in drawer 1', parts)
            self.assertTrue(drawer_results)
            self.assertIn(
                'Drawer 1',
                [bin.name for bin in drawer_results[0].part.locations],
            )

    def test_feedback_boosts_corrected_part(self):
        with app.app_context():
            parts = Part.query.all()
            center_pins = Part.query.filter_by(name='Center Pins 2 Oz Pkg').one()
            feedback = SearchFeedback(
                query_text='stuff in drawer 1',
                normalized_query='stuff in drawer 1',
                candidate_part_ids=json.dumps([part.id for part in parts]),
                selected_part_id=center_pins.id,
                scorer_metadata='{}',
            )
            db.session.add(feedback)
            db.session.commit()
            results = search_parts('stuff in drawer 1', parts, [feedback])
        self.assertEqual(results[0].part.id, center_pins.id)

    def test_parts_route_search_and_feedback(self):
        with app.test_client() as client:
            response = client.get('/parts?q=wire+coils')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Correct match', response.data)

            with app.app_context():
                part = Part.query.filter_by(name='Roslau Wire 1-Lb. Coils').one()
            feedback = client.post('/search-feedback', data={
                'query': 'wire coils',
                'part_id': str(part.id),
                'candidate_ids': '[]',
                'scorer_metadata': '{}',
            })
            self.assertEqual(feedback.status_code, 302)
            with app.app_context():
                self.assertEqual(SearchFeedback.query.count(), 1)

    def test_no_query_parts_route_still_browses(self):
        with app.test_client() as client:
            response = client.get('/parts')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'Correct match', response.data)


if __name__ == '__main__':
    unittest.main()
