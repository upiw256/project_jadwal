import os
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import timedelta
import streamlit as st

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def get_calendar_service():
    """Handles Google OAuth and returns service."""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('client_secret.json'):
                st.error("File 'client_secret.json' tidak ditemukan.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('calendar', 'v3', credentials=creds)

def sync_to_google_calendar(events_data, start_monday, num_weeks=1):
    """Syncs multiple weeks of schedule."""
    service = get_calendar_service()
    if not service: return False
    
    # Auto-delete existing events first
    with st.spinner(f"Membersihkan jadwal lama..."):
        delete_from_google_calendar(start_monday, "System", num_weeks=num_weeks, show_ui=False)
    
    day_map = {"SENIN": 0, "SELASA": 1, "RABU": 2, "KAMIS": 3, "JUMAT": 4, "SABTU": 5}
    progress_bar = st.progress(0, text="Memulai sinkronisasi massal...")
    
    total_inserts = len(events_data) * num_weeks
    current_count = 0
    
    teacher_name = st.session_state.get('pilihan_nama', 'Unknown')
    
    try:
        for week in range(num_weeks):
            week_monday = start_monday + timedelta(weeks=week)
            for ev in events_data:
                days_to_add = day_map.get(ev['hari'], 0)
                event_date = week_monday + timedelta(days=days_to_add)
                
                times = ev['waktu'].split('-')
                start_t = times[0].strip().replace('.', ':')
                end_t = times[1].strip().replace('.', ':')
                if len(start_t.split(':')[0]) == 1: start_t = "0" + start_t
                if len(end_t.split(':')[0]) == 1: end_t = "0" + end_t

                start_iso = f"{event_date.strftime('%Y-%m-%d')}T{start_t}:00"
                end_iso = f"{event_date.strftime('%Y-%m-%d')}T{end_t}:00"
                
                event_body = {
                    'summary': f"Mengajar: {ev['kelas']}",
                    'description': f"Guru: {teacher_name}\nMata Pelajaran: {ev['mapel']}\nHari: {ev['hari']}\nJam Ke: {ev['jam_ke_clean']}",
                    'start': {'dateTime': start_iso, 'timeZone': 'Asia/Jakarta'},
                    'end': {'dateTime': end_iso, 'timeZone': 'Asia/Jakarta'},
                }
                service.events().insert(calendarId='primary', body=event_body).execute()
                current_count += 1
                if current_count % 10 == 0:
                    progress_bar.progress(current_count / total_inserts, text=f"Syncing {current_count}/{total_inserts}...")
        
        st.success(f"✅ Berhasil sinkronisasi {total_inserts} jadwal untuk {num_weeks} minggu.")
        return True
    except Exception as e:
        st.error(f"Gagal: {e}")
        return False

def delete_from_google_calendar(start_monday, teacher_name, num_weeks=1, show_ui=True):
    """Deletes 'Mengajar:' events in the range."""
    service = get_calendar_service()
    if not service: return False
    
    time_min = start_monday.strftime('%Y-%m-%dT00:00:00+07:00')
    time_max = (start_monday + timedelta(weeks=num_weeks)).strftime('%Y-%m-%dT00:00:00+07:00')
    
    if show_ui: progress_bar = st.progress(0, text="Mencari event...")
    
    try:
        events = []
        page_token = None
        while True:
            res = service.events().list(calendarId='primary', timeMin=time_min, timeMax=time_max,
                                      singleEvents=True, orderBy='startTime', pageToken=page_token).execute()
            events.extend(res.get('items', []))
            page_token = res.get('nextPageToken')
            if not page_token: break
            
        deleted_count = 0
        for i, event in enumerate(events):
            if "Mengajar:" in event.get('summary', ''):
                service.events().delete(calendarId='primary', eventId=event['id']).execute()
                deleted_count += 1
            if show_ui: progress_bar.progress((i + 1) / len(events), text=f"Menghapus {i+1}/{len(events)}...")
            
        if show_ui and deleted_count > 0:
            st.success(f"🗑️ Berhasil menghapus {deleted_count} event.")
        return True
    except Exception as e:
        if show_ui: st.error(f"Error: {e}")
        return False
