import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

class DashboardTests(unittest.TestCase):
    def test_application_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'TRACKER_DB':tmp+'/test.db'}):
            app=AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py')).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.metric[0].value,'0')
            app.text_input(key='new_company').set_value('Test Company')
            app.text_input(key='new_role').set_value('Backend Engineer')
            next(b for b in app.button if b.label=='Save application').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.metric[0].value,'1')
            app.text_input(key='edit_1_role').set_value('Platform Engineer')
            next(b for b in app.button if b.label=='Save changes').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.text_input(key='edit_1_role').value,'Platform Engineer')
            app.text_input(key='search').set_value('No match').run()
            self.assertTrue(any('No matching applications' in i.value for i in app.info))
            app.text_input(key='search').set_value('').run()
            app.checkbox(key='delete_confirm_1').check().run()
            next(b for b in app.button if b.label=='Delete application').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.metric[0].value,'0')
            app.button(key='load_demo').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.metric[0].value,'3')
