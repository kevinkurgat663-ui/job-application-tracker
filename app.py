"""Job Application Tracker dashboard."""
import json
import os
from collections import Counter
from datetime import date
from pathlib import Path
import streamlit as st
from tracker import Store, STATUSES, PRIORITIES, MODES, FIELDS, agenda, filter_records, export_csv

st.set_page_config(page_title='Job Application Tracker', page_icon='💼', layout='wide')
st.markdown('''<style>
[data-testid="stMetric"] {background: #eef3f9; border: 1px solid #dce4ef; padding: 18px; border-radius: 12px;}
.block-container {padding-top: 2rem;} h1 {letter-spacing: -1px;}
</style>''', unsafe_allow_html=True)
store = Store(os.environ.get('TRACKER_DB', 'data/applications.db'))
with st.sidebar:
    st.title('Career Desk')
    st.caption('Your applications, organised.')
    today = st.date_input('Planning date', date.today(), help='Used for due dates and upcoming events. Defaults to the server’s local date; adjust for your timezone.')
    if st.button('Load fictional demo data', key='load_demo'):
        if store.seed(json.loads(Path(__file__).with_name('sample_applications.json').read_text())):
            st.rerun()
        else:
            st.info('Demo data is available only when the tracker is empty.')
    st.divider()
    st.caption('Dates and reminders are tracked here. No applications are submitted and no emails or notifications are sent.')

st.title('Job Application Tracker')
st.caption('A clear view of your search, from first interest to final decision.')
if 'flash' in st.session_state:
    st.success(st.session_state.pop('flash'))
records = store.all()
events = agenda(records, today)
metrics = st.columns(4)
metrics[0].metric('Opportunities', len(records))
metrics[1].metric('Active applications', sum(r['status'] in ('Applied', 'Screening', 'Interview') for r in records))
metrics[2].metric('Interviews', sum(r['status'] == 'Interview' for r in records))
metrics[3].metric('Due or overdue', sum(e['days'] <= 0 for e in events))
pipeline, new, edit, schedule, insights = st.tabs(['Applications', 'Add application', 'Edit application', 'Agenda', 'Insights'])

def application_form(prefix, current=None):
    current = current or dict.fromkeys(FIELDS, '')
    values = {}
    with st.form(prefix):
        left, right = st.columns(2)
        with left:
            values['company'] = st.text_input('Company *', current['company'], key=prefix+'_company')
            values['role'] = st.text_input('Role *', current['role'], key=prefix+'_role')
            values['status'] = st.selectbox('Stage', STATUSES, index=STATUSES.index(current['status']) if current['status'] else 0, key=prefix+'_status')
            values['priority'] = st.selectbox('Priority', PRIORITIES, index=PRIORITIES.index(current['priority']) if current['priority'] else 1, key=prefix+'_priority')
            values['location'] = st.text_input('Location', current['location'], key=prefix+'_location')
            values['work_mode'] = st.selectbox('Work arrangement', MODES, index=MODES.index(current['work_mode']) if current['work_mode'] else 0, key=prefix+'_work_mode')
            values['salary'] = st.text_input('Compensation', current['salary'], placeholder='For example: AUD 90,000/year', key=prefix+'_salary')
        with right:
            values['job_url'] = st.text_input('Job listing URL', current['job_url'], key=prefix+'_job_url')
            for field, label in [('applied_date', 'Applied date'), ('deadline', 'Application deadline'), ('follow_up', 'Follow-up date'), ('interview_date', 'Interview date')]:
                parsed = date.fromisoformat(current[field]) if current[field] else None
                value = st.date_input(label, value=parsed, key=prefix+'_'+field)
                values[field] = value.isoformat() if value else ''
            values['next_step'] = st.text_input('Next step', current['next_step'], key=prefix+'_next_step')
        values['notes'] = st.text_area('Notes', current['notes'], key=prefix+'_notes')
        submitted = st.form_submit_button('Save application' if prefix == 'new' else 'Save changes', type='primary')
    if submitted:
        try:
            store.save(values, current.get('id'))
            st.session_state['flash'] = 'Application saved.'
            st.rerun()
        except ValueError as error:
            st.error(str(error))

with pipeline:
    st.subheader('Application pipeline')
    search = st.text_input('Search companies, roles and notes', key='search')
    a, b, c = st.columns(3)
    statuses = a.multiselect('Stages', STATUSES)
    priorities = b.multiselect('Priorities', PRIORITIES)
    mode = c.selectbox('Work arrangement filter', ('All',) + MODES)
    matching = filter_records(records, search, statuses, priorities, mode)
    order = st.selectbox('Sort by', ['Newest', 'Company', 'Priority', 'Deadline'])
    if order == 'Company':
        matching.sort(key=lambda r: r['company'].casefold())
    elif order == 'Priority':
        matching.sort(key=lambda r: PRIORITIES.index(r['priority']))
    elif order == 'Deadline':
        matching.sort(key=lambda r: r['deadline'] or '9999-12-31')
    st.caption(f'{len(matching)} matching opportunities. Exports reflect the current filters and order.')
    if matching:
        st.dataframe([{'ID': r['id'], 'Company': r['company'], 'Role': r['role'], 'Stage': r['status'], 'Priority': r['priority'], 'Location': r['location'], 'Work arrangement': r['work_mode'], 'Deadline': r['deadline'], 'Follow-up': r['follow_up'], 'Next step': r['next_step']} for r in matching], hide_index=True, width='stretch')
        x, y = st.columns(2)
        x.download_button('Export CSV', export_csv(matching), 'applications.csv', 'text/csv')
        y.download_button('Export JSON', json.dumps(matching, indent=2, ensure_ascii=False), 'applications.json', 'application/json')
    else:
        st.info('No matching applications. Add an opportunity or adjust the filters.')
with new:
    st.subheader('Add an opportunity')
    application_form('new')
with edit:
    if records:
        selected = st.selectbox('Select application', [r['id'] for r in records], format_func=lambda key: next(f"{r['company']} · {r['role']} (#{key})" for r in records if r['id'] == key))
        record = next(r for r in records if r['id'] == selected)
        application_form('edit_'+str(selected), record)
        if record['job_url']:
            st.link_button('Open job listing', record['job_url'])
        st.caption('Created: '+record['created_at'][:10]+' · Updated: '+record['updated_at'][:10]+' (UTC)')
        confirmed = st.checkbox('Permanently delete this application', key='delete_confirm_'+str(selected))
        if st.button('Delete application', disabled=not confirmed):
            store.delete(selected)
            st.session_state['flash'] = 'Application deleted.'
            st.rerun()
    else:
        st.info('Add an application to edit its details.')
with schedule:
    st.subheader('Deadlines, interviews and follow-ups')
    window = st.selectbox('Show events', ['Due or overdue', 'Next 7 days', 'Next 30 days', 'All'])
    limits = {'Next 7 days': 7, 'Next 30 days': 30}
    visible = [e for e in events if window == 'All' or (e['days'] <= 0 if window == 'Due or overdue' else 0 <= e['days'] <= limits[window])]
    if visible:
        st.dataframe([{'Date': e['date'], 'Timing': 'Overdue' if e['days'] < 0 else 'Today' if e['days'] == 0 else f"In {e['days']} days", 'Company': e['company'], 'Role': e['role'], 'Event': e['event'], 'Next step': e['next_step']} for e in visible], hide_index=True, width='stretch')
    else:
        st.info('No events in this view.')
    st.caption('Application deadlines appear for Researching opportunities. Follow-ups and interviews appear for open applications. Offer, Rejected and Withdrawn records are excluded. Clear or change an event date after completing it.')
with insights:
    if records:
        st.subheader('Opportunities by current stage')
        counts = Counter(r['status'] for r in records)
        st.bar_chart(dict(Stage=list(STATUSES), Opportunities=[counts[s] for s in STATUSES]), x='Stage', y='Opportunities')
        applied = sum(bool(r['applied_date']) for r in records)
        offers = sum(r['status'] == 'Offer' for r in records)
        st.metric('Recorded offers', offers)
        st.caption(f'{applied} opportunities have an applied date recorded. Stage counts describe current status, not historical conversion rates.')
    else:
        st.info('Insights appear after the first application is saved.')
