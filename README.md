# Job Application Tracker

A personal application dashboard built with Python, Streamlit and SQLite. Tracks opportunities from research through interviews and final decisions, with a searchable pipeline and dated agenda.

## Features

- Application creation, editing and confirmed deletion
- Seven stages: Researching, Applied, Screening, Interview, Offer, Rejected and Withdrawn
- Company, role, location, work arrangement, compensation and listing URL
- Application dates, deadlines, interview dates and follow-up dates
- Priority levels, next steps and notes
- Search, combined filters and sorting by company, priority or deadline
- Dashboard metrics and a chart of current application stages
- Overdue, upcoming and complete agenda views
- Filtered CSV and JSON exports
- Optional fictional demonstration records

## Architecture

| Component | Responsibility |
| --- | --- |
| `app.py` | Streamlit dashboard, forms, agenda and charts |
| `tracker.py` | Validation, SQLite persistence, filtering and exports |
| `sample_applications.json` | Fictional demonstration opportunities |
| `tests/` | Storage, validation, agenda, export and dashboard tests |
| `.github/workflows/tests.yml` | Automated checks on pushes and pull requests |

## Runtime

Python 3.11 or later. Dependencies are declared in `requirements.txt`. The application entry point is `app.py`, served by Streamlit. The database defaults to `data/applications.db`; `TRACKER_DB` overrides this path. Runtime data is excluded from version control.

## Data model

Each opportunity has a numeric identifier, creation and update timestamps, company, role, current stage, priority, work arrangement, location, compensation, listing URL, four optional event dates, next step and notes. Required fields and enumerations are validated before database writes. Dates use ISO format, and database timestamps use UTC.

## Agenda behaviour

Application deadlines appear for Researching opportunities. Interviews and follow-ups appear for open opportunities. Offer, Rejected and Withdrawn records are excluded. The planning date controls overdue and upcoming calculations. Events remain scheduled until their date is cleared or updated. Reminders are displayed inside the dashboard; there are no background notifications or outgoing messages.

## Storage and access

A single-workspace application without built-in authentication or user isolation. Every visitor to the same running instance can access its records. SQLite persistence depends on the host's disk retention. No job listings are fetched and no applications are submitted. Demo companies and vacancies are fictional.

CSV exports neutralize common spreadsheet formula prefixes. JSON exports preserve original content. Current stage metrics describe the present pipeline rather than historical conversion rates.

## Validation

Automated checks cover creation, editing, deletion, persistence, invalid inputs, combined filters, agenda rules, CSV escaping and dashboard interactions. Tests use temporary databases.

## License

MIT. See [LICENSE](LICENSE).
