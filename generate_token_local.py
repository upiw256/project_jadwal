import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def main():
    print("Memulai proses autentikasi (akan membuka browser)...")
    try:
        flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
        # open_browser=False mencegah error jika dijalankan di Docker (headless)
        # port=8080 dipakai agar kita tahu port yang harus diakses
        print("\n\n=== ACTION REQUIRED ===")
        print("Jika browser tidak terbuka otomatis, silakan BUKA LINK DI BAWAH INI di browser Anda:")
        creds = flow.run_local_server(port=8080, open_browser=False)
        
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
            
        print("\n✅ BERHASIL! File 'token.pickle' telah dibuat.")
        print("Sekarang Anda bisa menjalankan aplikasi di Docker, dan sistem tidak akan meminta buka browser lagi.")
    except Exception as e:
        print(f"\n❌ Terjadi kesalahan: {e}")

if __name__ == '__main__':
    main()
