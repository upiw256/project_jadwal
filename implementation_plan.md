# Implementation Plan: Google Calendar Integration

Add a feature to sync the school schedule with Google Calendar, including Google account authentication.

## User Review Required

> [!IMPORTANT]
> To use this feature, you will need a `client_secret.json` file from the [Google Cloud Console](https://console.cloud.google.com/).
> 1. Create a project in Google Cloud Console.
> 2. Enable "Google Calendar API".
> 3. Configure the OAuth Consent Screen (Internal or External).
> 4. Create "OAuth 2.0 Client IDs" for a "Web application" or "Desktop app".
> 5. Download the JSON and save it as `client_secret.json` in the `d:\project_jadwal` directory.

## Proposed Changes

### Dependencies

#### [MODIFY] [requirements.txt](file:///d:/project_jadwal/requirements.txt)
Add the following libraries:
- `google-auth`
- `google-auth-oauthlib`
- `google-auth-httplib2`
- `google-api-python-client`
- `python-dateutil`

### Application Logic

#### [MODIFY] [main.py](file:///d:/project_jadwal/main.py)
1. **Import Google Libraries**: Add imports for google-auth and google-api-client.
2. **Authentication Handler**: Implement a function to handle OAuth2 flow.
3. **Calendar Sync Function**:
   - Map "SENIN" - "JUMAT" to actual dates based on a user-selected "Start Week" date.
   - Parse the time strings (e.g., "07.10 - 07.50") into ISO format for Google Calendar.
   - Create events in the user's primary calendar.
4. **UI Integration**:
   - Add a date picker for selecting the Monday of the week to sync.
   - Add a "Sync to Google Calendar" button.
   - Show login prompts and sync progress.

## Verification Plan

### Automated Tests
- Verify code structure and dependency installation.

### Manual Verification
1. Run the app: `.\venv\Scripts\streamlit run main.py`
2. Upload a schedule PDF.
3. Select a teacher.
4. Select a "Start Week" date (a Monday).
5. Click "Sync to Google Calendar".
6. Follow the login prompt in the browser.
7. Verify events in Google Calendar.
