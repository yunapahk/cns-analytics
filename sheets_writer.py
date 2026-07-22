import gspread
from datetime import date
from zoneinfo import ZoneInfo
import datetime as dt
from google.oauth2.service_account import Credentials

from youtube_pull import (
    CHANNELS,
    get_channel_stats,
    get_recent_content,
    get_recent_shorts,
)


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets"
]

SERVICE_ACCOUNT_FILE = "service-account.json"

SHEET_ID = "1-FYOLM36b0ptEmt9Wviqub4_nwGX2JMCN7moWoEiHSQ"

TAB_MAP = {
    "podcast": "YouTube",
    "yuna": "Yuna YT",
    "brian": "Brian YT",
}


def get_client():
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
    )

    return gspread.authorize(creds)


def today_string():
    pacific = ZoneInfo("America/Los_Angeles")
    return dt.datetime.now(pacific).strftime("%m/%d/%Y")


# =========================================================
# PODCAST YOUTUBE TAB
# =========================================================

def write_podcast_subscriber_snapshot(client, subscribers):
    """
    YouTube tab layout:

    E = Subscribers
    F = Date
    """
    sheet = client.open_by_key(SHEET_ID).worksheet(TAB_MAP["podcast"])
    dates = sheet.col_values(6)
    today = today_string()

    if len(dates) > 1 and dates[-1] == today:
        row_number = len(dates)
    else:
        row_number = len(dates) + 1

    sheet.update(
        range_name=f"E{row_number}:F{row_number}",
        values=[[subscribers, today]],
    )


# =========================================================
# PODCAST SHORTS TAB
# =========================================================

def write_podcast_shorts(client, shorts):
    """
    Shorts tab layout:

    A = Title
    B = Views
    C = Date checked
    D = Published date
    E = Video ID
    """
    sheet = client.open_by_key(SHEET_ID).worksheet("Shorts")

    existing_ids = sheet.col_values(5)
    today = today_string()

    updates = []

    for short in shorts:
        video_id = short["video_id"]

        if video_id in existing_ids:
            row_number = existing_ids.index(video_id) + 1
        else:
            row_number = max(len(existing_ids) + 1, 2)
            existing_ids.append(video_id)

        updates.append({
            "range": f"A{row_number}:E{row_number}",
            "values": [[
                short["title"],
                short["views"],
                today,
                short["published"],
                video_id,
            ]],
        })

    if updates:
        sheet.batch_update(updates)


# =========================================================
# PERSONAL CHANNEL SUBSCRIBERS
# =========================================================

def write_personal_subscriber_snapshot(sheet, subscribers):
    """
    Yuna YT / Brian YT layout:

    A = Subs
    B = Date
    """
    dates = sheet.col_values(2)
    today = today_string()

    if len(dates) > 1 and dates[-1] == today:
        row_number = len(dates)
    else:
        row_number = len(dates) + 1

    sheet.update(
        range_name=f"A{row_number}:B{row_number}",
        values=[[subscribers, today]],
    )


# =========================================================
# PERSONAL CHANNEL REGULAR VIDEOS
# =========================================================

def upsert_personal_videos(sheet, videos):
    """
    Yuna YT / Brian YT regular-video layout:

    D = Title
    E = Views
    F = Date
    G = Video ID
    """
    existing_ids = sheet.col_values(7)
    today = today_string()

    updates = []

    for video in videos:
        video_id = video["video_id"]

        if video_id in existing_ids:
            row_number = existing_ids.index(video_id) + 1
        else:
            row_number = max(len(existing_ids) + 1, 2)
            existing_ids.append(video_id)

        updates.append({
            "range": f"D{row_number}:G{row_number}",
            "values": [[
                video["title"],
                video["views"],
                today,
                video_id,
            ]],
        })

    if updates:
        sheet.batch_update(updates)


# =========================================================
# PERSONAL CHANNEL SHORTS
# =========================================================

def upsert_personal_shorts(sheet, shorts):
    """
    Yuna YT / Brian YT Shorts layout:

    I = Title
    J = Views
    K = Shorts
    L = Date
    M = Video ID
    """
    existing_ids = sheet.col_values(13)
    today = today_string()

    updates = []

    for short in shorts:
        video_id = short["video_id"]

        if video_id in existing_ids:
            row_number = existing_ids.index(video_id) + 1
        else:
            row_number = max(len(existing_ids) + 1, 2)
            existing_ids.append(video_id)

        updates.append({
            "range": f"I{row_number}:M{row_number}",
            "values": [[
                short["title"],
                short["views"],
                "Short",
                today,
                video_id,
            ]],
        })

    if updates:
        sheet.batch_update(updates)


# =========================================================
# PERSONAL CHANNEL MASTER FUNCTION
# =========================================================

def update_personal_youtube_tab(client, channel_key):
    """
    Updates either:
    - Yuna YT
    - Brian YT
    """
    sheet = client.open_by_key(SHEET_ID).worksheet(TAB_MAP[channel_key])

    channel_id = CHANNELS[channel_key]

    stats = get_channel_stats(channel_id)

    content = get_recent_content(channel_id, max_results=50)

    write_personal_subscriber_snapshot(sheet, stats["subscribers"])

    upsert_personal_videos(sheet, content["videos"])

    upsert_personal_shorts(sheet, content["shorts"])

    return {
        "subscribers": stats["subscribers"],
        "videos_processed": len(content["videos"]),
        "shorts_processed": len(content["shorts"]),
    }


# =========================================================
# RUN EVERYTHING (each section isolated so one failure
# doesn't stop the others)
# =========================================================

if __name__ == "__main__":
    client = get_client()

    results_summary = []

    # --- Podcast subs ---
    try:
        podcast_stats = get_channel_stats(CHANNELS["podcast"])
        write_podcast_subscriber_snapshot(client, podcast_stats["subscribers"])
        results_summary.append(f"Podcast: {podcast_stats['subscribers']} subs")
    except Exception as error:
        print(f"FAILED - Podcast subs: {error}")
        results_summary.append("Podcast: FAILED")

    # --- Podcast Shorts ---
    try:
        podcast_shorts = get_recent_shorts(CHANNELS["podcast"], max_results=50)
        write_podcast_shorts(client, podcast_shorts)
        results_summary.append(f"{len(podcast_shorts)} podcast Shorts processed")
    except Exception as error:
        print(f"FAILED - Podcast Shorts: {error}")
        results_summary.append("Podcast Shorts: FAILED")

    # --- Yuna YT ---
    try:
        yuna_results = update_personal_youtube_tab(client, "yuna")
        results_summary.append(
            f"Yuna: {yuna_results['subscribers']} subs, "
            f"{yuna_results['videos_processed']} videos, "
            f"{yuna_results['shorts_processed']} Shorts"
        )
    except Exception as error:
        print(f"FAILED - Yuna YT: {error}")
        results_summary.append("Yuna YT: FAILED")

    # --- Brian YT ---
    try:
        brian_results = update_personal_youtube_tab(client, "brian")
        results_summary.append(
            f"Brian: {brian_results['subscribers']} subs, "
            f"{brian_results['videos_processed']} videos, "
            f"{brian_results['shorts_processed']} Shorts"
        )
    except Exception as error:
        print(f"FAILED - Brian YT: {error}")
        results_summary.append("Brian YT: FAILED")

    print(" | ".join(results_summary))