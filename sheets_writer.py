import gspread
from google.oauth2.service_account import Credentials
from datetime import date
from youtube_pull import get_channel_stats, get_recent_shorts, CHANNELS

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_FILE = "service-account.json"
SHEET_ID = "1-FYOLM36b0ptEmt9Wviqub4_nwGX2JMCN7moWoEiHSQ"

TAB_MAP = {
    "podcast": "YouTube",
    "yuna": "Yuna YT",
    "brian": "Brian YT"
}


def get_client():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return gspread.authorize(creds)


def write_subs(client, tab_name, subs, sub_col=1):
    sheet = client.open_by_key(SHEET_ID).worksheet(tab_name)
    col_vals = sheet.col_values(sub_col)
    next_row = len(col_vals) + 1
    date_col = chr(ord('A') + sub_col)  # column right after subs
    sheet.update(f"A{next_row}:B{next_row}" if sub_col == 1 else f"E{next_row}:F{next_row}",
                 [[subs, date.today().strftime("%m/%d/%Y")]])


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

    # Podcast tab uses columns E:F (existing layout)
    podcast_stats = get_channel_stats(CHANNELS["podcast"])
    write_subs(client, TAB_MAP["podcast"], podcast_stats["subscribers"], sub_col=5)

    # Personal tabs use columns A:B (new layout)
    yuna_stats = get_channel_stats(CHANNELS["yuna"])
    write_subs(client, TAB_MAP["yuna"], yuna_stats["subscribers"], sub_col=1)

    brian_stats = get_channel_stats(CHANNELS["brian"])
    write_subs(client, TAB_MAP["brian"], brian_stats["subscribers"], sub_col=1)

    # Shorts only tracked for the podcast channel
    shorts = get_recent_shorts(CHANNELS["podcast"])
    write_shorts(client, shorts)

    print(f"Podcast: {podcast_stats['subscribers']} subs | Yuna: {yuna_stats['subscribers']} subs | Brian: {brian_stats['subscribers']} subs | {len(shorts)} shorts processed")