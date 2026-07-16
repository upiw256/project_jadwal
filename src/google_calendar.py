import json
import os
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from datetime import timedelta
import streamlit as st

from src.oauth_config import get_redirect_uri

SCOPES = ['https://www.googleapis.com/auth/calendar.events']
TOKEN_PATH = 'token.pickle'
CLIENT_SECRET_PATH = 'client_secret.json'

# Redirect URI harus sama persis dengan yang ada di Google Cloud Console.
# Untuk deployment publik, pastikan URL publik yang dipakai sama persis dengan
# yang didaftarkan di Google Cloud Console, termasuk trailing slash.
REDIRECT_URI = get_redirect_uri()


def _save_creds(creds):
    with open(TOKEN_PATH, 'wb') as token:
        pickle.dump(creds, token)


def get_calendar_service():
    """Mengembalikan service Google Calendar. Jika belum login, tampilkan tombol login."""
    creds = None

    # 1. Coba load token yang sudah ada
    if os.path.exists(TOKEN_PATH) and os.path.isfile(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)

    # 2. Refresh jika expired
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_creds(creds)
        except Exception:
            creds = None

    # 3. Jika sudah valid, langsung kembalikan service
    if creds and creds.valid:
        return build('calendar', 'v3', credentials=creds)

    # 4. Belum ada token — mulai flow OAuth Web
    if not os.path.exists(CLIENT_SECRET_PATH):
        st.error("❌ File 'client_secret.json' tidak ditemukan di server.")
        return None

    # Tampilkan tombol login
    _show_login_button()
    return None


def _show_login_button():
    """Tampilkan tombol login Google di UI Streamlit."""
    if not os.path.exists(CLIENT_SECRET_PATH):
        st.error("❌ File 'client_secret.json' tidak ditemukan.")
        return

    with open(CLIENT_SECRET_PATH, 'r', encoding='utf-8') as f:
        secret_data = json.load(f)

    # Show client info for debugging redirect_uri mismatches
    client_type = 'web' if 'web' in secret_data else ('installed' if 'installed' in secret_data else None)
    client_info = secret_data.get(client_type, {}) if client_type else {}
    client_id = client_info.get('client_id')
    client_redirects = client_info.get('redirect_uris')

    st.caption(f"Client type in JSON: {client_type}")
    if client_id:
        st.caption(f"Client ID in JSON: {client_id}")
    if client_redirects:
        st.caption("Redirect URIs in client_secret.json:")
        for r in client_redirects:
            st.caption(f" - {r}")

    if client_type != 'web':
        st.error(
            "❌ client_secret.json tidak berisi kredensial tipe 'web'. "
            "Jika Anda menerima 'redirect_uri_mismatch', buat OAuth Client ID baru dengan tipe 'Web application' di Google Cloud Console dan unduh JSON baru."
        )
        return

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_PATH,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    # Parse the auth_url to extract the redirect_uri param for debugging
    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(auth_url)
        q = parse_qs(parsed.query)
        sent_redirect = q.get('redirect_uri', [None])[0]
        if sent_redirect:
            st.caption(f"redirect_uri sent to Google: {sent_redirect}")
    except Exception:
        pass

    with open('oauth_state.json', 'w', encoding='utf-8') as f:
        json.dump({
            'state': state,
            'code_verifier': getattr(flow, 'code_verifier', None)
        }, f)

    st.warning("⚠️ Belum login ke Google. Klik tombol di bawah untuk otorisasi akses Google Calendar.")
    st.caption(f"Redirect URI yang dipakai: {REDIRECT_URI}")
    st.caption("Pastikan URI ini sudah didaftarkan di Google Cloud Console persis sama, termasuk trailing slash.")
    st.link_button("🔐 Login dengan Google", auth_url, use_container_width=True)


def is_logged_in():
    """Cek apakah token sudah ada dan valid, atau menangkap callback login."""
    # Tangkap callback URL dari Google jika ada
    query_params = st.query_params
    auth_code = query_params.get("code")
    
    if auth_code:
        try:
            import json
            saved_state = None
            code_verifier = None
            if os.path.exists('oauth_state.json'):
                with open('oauth_state.json', 'r') as f:
                    data = json.load(f)
                    saved_state = data.get('state')
                    code_verifier = data.get('code_verifier')

            flow = Flow.from_client_secrets_file(
                CLIENT_SECRET_PATH,
                scopes=SCOPES,
                redirect_uri=REDIRECT_URI,
                state=saved_state
            )
            if code_verifier:
                flow.code_verifier = code_verifier

            flow.fetch_token(code=auth_code)
            _save_creds(flow.credentials)
            st.query_params.clear()
            if os.path.exists('oauth_state.json'):
                os.remove('oauth_state.json')
            st.success("✅ Login Google berhasil! Silakan lanjutkan.")
            return True
        except Exception as e:
            st.error(f"❌ Gagal tukar token: {e}")
            return False

    if not os.path.exists(TOKEN_PATH) or not os.path.isfile(TOKEN_PATH):
        return False
    try:
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
        if creds and creds.valid:
            return True
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _save_creds(creds)
            return True
    except Exception:
        pass
    return False


def logout_google():
    """Hapus token (logout)."""
    if os.path.exists(TOKEN_PATH):
        os.remove(TOKEN_PATH)


def sync_to_google_calendar(events_data, start_monday, num_weeks=1):
    """Syncs multiple weeks of schedule."""
    service = get_calendar_service()
    if not service:
        return False

    teacher_name = st.session_state.get('pilihan_nama', 'Unknown')

    with st.spinner("Membersihkan jadwal lama..."):
        delete_from_google_calendar(start_monday, teacher_name, num_weeks=num_weeks, show_ui=False)

    day_map = {"SENIN": 0, "SELASA": 1, "RABU": 2, "KAMIS": 3, "JUMAT": 4, "SABTU": 5}
    progress_bar = st.progress(0, text="Memulai sinkronisasi massal...")

    total_inserts = len(events_data) * num_weeks
    current_count = 0

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
    if not service:
        return False

    time_min = start_monday.strftime('%Y-%m-%dT00:00:00+07:00')
    time_max = (start_monday + timedelta(weeks=num_weeks)).strftime('%Y-%m-%dT00:00:00+07:00')

    if show_ui:
        progress_bar = st.progress(0, text="Mencari event...")

    try:
        events = []
        page_token = None
        while True:
            res = service.events().list(
                calendarId='primary', timeMin=time_min, timeMax=time_max,
                singleEvents=True, orderBy='startTime', pageToken=page_token
            ).execute()
            events.extend(res.get('items', []))
            page_token = res.get('nextPageToken')
            if not page_token:
                break

        deleted_count = 0
        for i, event in enumerate(events):
            if "Mengajar:" in event.get('summary', ''):
                desc = event.get('description', '')
                if desc and f"Guru: {teacher_name}" in desc:
                    service.events().delete(calendarId='primary', eventId=event['id']).execute()
                    deleted_count += 1
            if show_ui and events:
                progress_bar.progress((i + 1) / len(events), text=f"Memeriksa {i+1}/{len(events)}...")

        if show_ui and deleted_count > 0:
            st.success(f"🗑️ Berhasil menghapus {deleted_count} event.")
        return True
    except Exception as e:
        if show_ui:
            st.error(f"Error: {e}")
        return False
