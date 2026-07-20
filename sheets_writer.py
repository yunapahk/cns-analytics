import gspread
from datetime import date
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
    return date.today().strftime("%m/%d/%Y")


def write_subscriber_snapshot(sheet, subscribers):
    """
    Personal channel layout:

    A = Subscribers
    B = Date

    If today's row already exists, update it instead of
    creating duplicate rows.
    """
    dates = sheet.col_values(2)
    today = today_string()

    if today in dates:
        row_number = dates.index(today) + 1
    else:
        row_number = max(len(dates) + 1, 2)

    sheet.update(
        range_name=f"A{row_number}:B{row_number}",
        values=[[
            subscribers,
            today,
        ]],
    )


def upsert_regular_videos(sheet, videos):
    """
    Regular-video layout:

    E = Title
    F = Views
    G = Date checked
    H = Video ID
    """
    existing_ids = sheet.col_values(8)  # Column H
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
            "range": f"E{row_number}:H{row_number}",
            "values": [[
                video["title"],
                video["views"],
                today,
                video_id,
            ]],
        })

    if updates:
        sheet.batch_update(updates)


def upsert_shorts(sheet, shorts):
    """
    Shorts layout matching your current sheet:

    J = Title
    K = Views
    L = Shorts
    M = Date checked
    N = Video ID

    Column L receives the label "Short".
    """
    existing_ids = sheet.col_values(14)  # Column N
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
            "range": f"J{row_number}:N{row_number}",
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


def update_personal_channel(client, channel_key):
    channel_id = CHANNELS[channel_key]
    tab_name = TAB_MAP[channel_key]

    spreadsheet = client.open_by_key(SHEET_ID)
    sheet = spreadsheet.worksheet(tab_name)

    stats = get_channel_stats(channel_id)

    content = get_recent_content(
        channel_id,
        max_results=50,
    )

    # A:B
    write_subscriber_snapshot(
        sheet,
        stats["subscribers"],
    )

    # E:H
    upsert_regular_videos(
        sheet,
        content["videos"],
    )

    # J:N
    upsert_shorts(
        sheet,
        content["shorts"],
    )

    return {
        "subscribers": stats["subscribers"],
        "videos_processed": len(content["videos"]),
        "shorts_processed": len(content["shorts"]),
    }


def write_podcast_subscribers(client, subscribers):
    """
    Keeps the podcast subscriber layout:

    E = Subscribers
    F = Date
    """
    sheet = client.open_by_key(SHEET_ID).worksheet(
        TAB_MAP["podcast"]
    )

    dates = sheet.col_values(6)
    today = today_string()

    if today in dates:
        row_number = dates.index(today) + 1
    else:
        row_number = max(len(dates) + 1, 2)

    sheet.update(
        range_name=f"E{row_number}:F{row_number}",
        values=[[
            subscribers,
            today,
        ]],
    )


def write_podcast_shorts(client, shorts):
    """
    Keeps podcast Shorts in the dedicated Shorts tab.

    A = Title
    B = Views
    C = Last checked
    D = Published
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


if __name__ == "__main__":
    client = get_client()

    # Podcast channel
    podcast_stats = get_channel_stats(
        CHANNELS["podcast"]
    )

    podcast_shorts = get_recent_shorts(
        CHANNELS["podcast"],
        max_results=50,
    )

    write_podcast_subscribers(
        client,
        podcast_stats["subscribers"],
    )

    write_podcast_shorts(
        client,
        podcast_shorts,
    )

    # Yuna channel
    yuna_results = update_personal_channel(
        client,
        "yuna",
    )

    # Brian channel
    brian_results = update_personal_channel(
        client,
        "brian",
    )

    print(
        f"Podcast: {podcast_stats['subscribers']} subs | "
        f"Yuna: {yuna_results['subscribers']} subs, "
        f"{yuna_results['videos_processed']} videos, "
        f"{yuna_results['shorts_processed']} Shorts | "
        f"Brian: {brian_results['subscribers']} subs, "
        f"{brian_results['videos_processed']} videos, "
        f"{brian_results['shorts_processed']} Shorts | "
        f"{len(podcast_shorts)} podcast Shorts processed"
    )