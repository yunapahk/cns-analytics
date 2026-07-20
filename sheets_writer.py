import gspread
from google.oauth2.service_account import Credentials
from datetime import date
from youtube_pull import get_channel_stats, get_recent_shorts

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_FILE = "service-account.json"
SHEET_ID = "1-FYOLM36b0ptEmt9Wviqub4_nwGX2JMCN7moWoEiHSQ"

def get_client():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return gspread.authorize(creds)

def write_subs(client, subs):
    sheet = client.open_by_key(SHEET_ID).worksheet("YouTube")
    col_e = sheet.col_values(5)
    next_row = len(col_e) + 1
    sheet.update(f"E{next_row}:F{next_row}", [[subs, date.today().strftime("%m/%d/%Y")]])

def write_shorts(client, shorts):
    sheet = client.open_by_key(SHEET_ID).worksheet("Shorts")
    existing = sheet.get_all_values()
    video_id_col = [row[4] if len(row) > 4 else "" for row in existing]

    for short in shorts:
        if short["video_id"] in video_id_col:
            row_num = video_id_col.index(short["video_id"]) + 1
            sheet.update(f"B{row_num}", [[short["views"]]])
        else:
            sheet.append_row([
                short["title"], short["views"], "", short["published"], short["video_id"]
            ])

if __name__ == "__main__":
    client = get_client()
    stats = get_channel_stats()
    write_subs(client, stats["subscribers"])
    shorts = get_recent_shorts()
    write_shorts(client, shorts)
    print(f"Updated subs: {stats['subscribers']}, processed {len(shorts)} shorts")