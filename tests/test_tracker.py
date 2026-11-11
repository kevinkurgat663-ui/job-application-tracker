import csv
import io
import tempfile
import unittest
from datetime import date
from pathlib import Path
from tracker import Store, FIELDS, agenda, filter_records, export_csv

def example(**changes):
    row = dict.fromkeys(FIELDS, '')
    row.update(company='Example', role='Engineer', status='Applied', priority='High', work_mode='Remote')
    return dict(row, **changes)

class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'app.db'
        self.store = Store(self.path)
    def test_persistent_create_update_delete(self):
        key = self.store.save(example(notes="Unicode: café\nO'Brien"))
        self.assertEqual(Store(self.path).all()[0]['notes'], "Unicode: café\nO'Brien")
        self.store.save(example(status='Interview'), key)
        self.assertEqual(self.store.all()[0]['status'], 'Interview')
        self.store.delete(key)
        self.assertEqual(self.store.all(), [])
        with self.assertRaises(ValueError): self.store.save(example(), key)
    def test_validation(self):
        for changes in [dict(company=' '),dict(role=''),dict(status='Unknown'),dict(priority='Critical'),dict(work_mode='Anywhere'),dict(deadline='2026-02-30'),dict(applied_date='20261111'),dict(job_url='javascript:alert(1)'),dict(job_url='https://user:password@example.com')]:
            with self.subTest(changes=changes), self.assertRaises(ValueError): self.store.save(example(**changes))
        self.assertEqual(self.store.all(), [])
    def test_filters(self):
        records=[example(company='Alpha'),example(company='Beta',status='Researching',priority='Low',work_mode='Hybrid')]
        self.assertEqual(len(filter_records(records,'ALPHA',['Applied'],['High'],'Remote')),1)
        self.assertEqual(filter_records(records,statuses=['Interview']),[])
    def test_agenda(self):
        records=[dict(example(status='Researching',deadline='2026-11-11'),id=1),dict(example(deadline='2026-11-10',follow_up='2026-11-10',interview_date='2026-11-12'),id=2),dict(example(status='Rejected',follow_up='2026-11-09'),id=3)]
        events=agenda(records,date(2026,11,11))
        self.assertEqual([e['days'] for e in events],[-1,0,1])
        self.assertEqual([e['event'] for e in events],['Follow-up','Application deadline','Interview'])
    def test_seed(self):
        with self.assertRaises(ValueError): self.store.seed([example(),example(company='')])
        self.assertEqual(self.store.all(),[])
        self.assertTrue(self.store.seed([example()]))
        self.assertFalse(self.store.seed([example()]))
        self.assertEqual(len(self.store.all()),1)
    def test_csv(self):
        row=next(csv.DictReader(io.StringIO(export_csv([example(company='  =SUM(1,2)',notes='One, two\nThree')]))))
        self.assertEqual(row['company'],"'  =SUM(1,2)")
        self.assertEqual(row['notes'],'One, two\nThree')
