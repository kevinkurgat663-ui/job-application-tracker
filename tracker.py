"""Application validation, durable storage, filtering and exports."""
import csv
import io
import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

STATUSES = ('Researching', 'Applied', 'Screening', 'Interview', 'Offer', 'Rejected', 'Withdrawn')
PRIORITIES = ('High', 'Medium', 'Low')
MODES = ('Remote', 'Hybrid', 'On-site')
CLOSED = {'Offer', 'Rejected', 'Withdrawn'}
FIELDS = ('company', 'role', 'status', 'priority', 'location', 'work_mode', 'job_url', 'salary', 'applied_date', 'deadline', 'follow_up', 'interview_date', 'next_step', 'notes')
DATE_FIELDS = ('applied_date', 'deadline', 'follow_up', 'interview_date')

def validate(values):
    record = {key: str(values.get(key, '') or '').strip() for key in FIELDS}
    for key in ('company', 'role'):
        if not record[key]:
            raise ValueError(f'{key.title()} is required.')
    for key, options in (('status', STATUSES), ('priority', PRIORITIES), ('work_mode', MODES)):
        if record[key] not in options:
            raise ValueError(f'Invalid {key.replace("_", " ")}.')
    for key in DATE_FIELDS:
        if record[key]:
            try:
                parsed = date.fromisoformat(record[key])
                if parsed.isoformat() != record[key]:
                    raise ValueError()
            except ValueError:
                raise ValueError(f'{key.replace("_", " ").title()} must be YYYY-MM-DD.') from None
    if record['job_url']:
        url = urlsplit(record['job_url'])
        if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password:
            raise ValueError('Job URL must be a valid HTTP or HTTPS link without credentials.')
    return record

class Store:
    def __init__(self, path='data/applications.db'):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS applications (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, payload TEXT NOT NULL)')
    def connect(self):
        return sqlite3.connect(self.path, timeout=15)
    def save(self, values, application_id=None):
        record = validate(values)
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as db:
            if application_id is None:
                return db.execute('INSERT INTO applications(created_at,updated_at,payload) VALUES(?,?,?)', (now, now, json.dumps(record))).lastrowid
            cursor = db.execute('UPDATE applications SET updated_at=?,payload=? WHERE id=?', (now, json.dumps(record), application_id))
            if cursor.rowcount == 0:
                raise ValueError('Application no longer exists. Refresh the page.')
            return application_id
    def all(self):
        with self.connect() as db:
            return [dict(json.loads(payload), id=key, created_at=created, updated_at=updated) for key, created, updated, payload in db.execute('SELECT id,created_at,updated_at,payload FROM applications ORDER BY id DESC')]
    def delete(self, application_id):
        with self.connect() as db:
            db.execute('DELETE FROM applications WHERE id=?', (application_id,))
    def seed(self, records):
        clean = [validate(record) for record in records]
        with self.connect() as db:
            if db.execute('SELECT COUNT(*) FROM applications').fetchone()[0]:
                return False
            now = datetime.now(timezone.utc).isoformat()
            db.executemany('INSERT INTO applications(created_at,updated_at,payload) VALUES(?,?,?)', [(now, now, json.dumps(record)) for record in clean])
            return True

def filter_records(records, search='', statuses=(), priorities=(), mode='All'):
    return [r for r in records if (not search or search.casefold() in ' '.join(str(r.get(k, '')) for k in FIELDS).casefold()) and (not statuses or r['status'] in statuses) and (not priorities or r['priority'] in priorities) and (mode == 'All' or r['work_mode'] == mode)]

def agenda(records, today):
    events = []
    for r in records:
        if r['status'] in CLOSED:
            continue
        kinds = [('follow_up', 'Follow-up'), ('interview_date', 'Interview')]
        if r['status'] == 'Researching':
            kinds.append(('deadline', 'Application deadline'))
        for field, label in kinds:
            if r[field]:
                delta = (date.fromisoformat(r[field]) - today).days
                events.append(dict(id=r['id'], company=r['company'], role=r['role'], event=label, date=r[field], days=delta, next_step=r['next_step']))
    return sorted(events, key=lambda e: (e['date'], e['company']))

def export_csv(records):
    out = io.StringIO(newline='')
    columns = ('id',) + FIELDS + ('created_at', 'updated_at')
    writer = csv.DictWriter(out, fieldnames=columns)
    writer.writeheader()
    for record in records:
        row = {k: record.get(k, '') for k in columns}
        for key, value in row.items():
            if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
                row[key] = "'" + value
        writer.writerow(row)
    return out.getvalue()
