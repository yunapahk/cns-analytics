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
    Writes subscriber history to columns A:B.

    A = Subscribers
    B = Date
    """
    existing_subscribers = sheet.col_values(1)
    next_row = max(len(existing_subscribers) + 1, 2)

    sheet.update(
        range_name=f"A{next_row}:B{next_row}",
        values=[[
            subscribers,
            today_string(),
        ]],
    )


def upsert_content(
    sheet,
    content,
    title_col,
    views_col,
    date_col,
    video_id_col,
):
    """
    Adds new videos or Shorts when their video IDs are not present.

    Updates the title, views, and date when the video ID already exists.
    """

    video_id_col_number = gspread.utils.a1_to_rowcol(
        f"{video_id_col}1"
    )[1]

    existing_ids = sheet.col_values(video_id_col_number)

    updates = []

    for video in content:
        video_id = video["video_id"]

        if video_id in existing_ids:
            row_number = existing_ids.index(video_id) + 1
        else:
            row_number = max(len(existing_ids) + 1, 2)
            existing_ids.append(video_id)

        updates.append({
            "range": (
                f"{title_col}{row_number}:"
                f"{video_id_col}{row_number}"
            ),
            "values": [[
                video["title"],
                video["views"],
                today_string(),
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

    # A:B — subscriber history
    write_subscriber_snapshot(
        sheet,
        stats["subscribers"],
    )

    # E:H — regular videos
    # E = Title
    # F = Views
    # G = Date
    # H = Video ID
    upsert_content(
        sheet=sheet,
        content=content["videos"],
        title_col="E",
        views_col="F",
        date_col="G",
        video_id_col="H",
    )

    # I:L — Shorts
    # I = Title
    # J = Views
    # K = Date
    # L = Video ID
    upsert_content(
        sheet=sheet,
        content=content["shorts"],
        title_col="I",
        views_col="J",
        date_col="K",
        video_id_col="L",
    )

    return {
        "subscribers": stats["subscribers"],
        "videos_processed": len(content["videos"]),
        "shorts_processed": len(content["shorts"]),
    }


def write_podcast_subscribers(client, subscribers):
    """
    Keeps your existing podcast subscriber layout:

    E = Subscribers
    F = Date
    """
    sheet = client.open_by_key(SHEET_ID).worksheet(
        TAB_MAP["podcast"]
    )

    existing_values = sheet.col_values(5)
    next_row = max(len(existing_values) + 1, 2)

    sheet.update(
        range_name=f"E{next_row}:F{next_row}",
        values=[[
            subscribers,
            today_string(),
        ]],
    )


def write_podcast_shorts(client, shorts):
    """
    Keeps podcast Shorts in the separate Shorts tab.

    Existing layout:
    A = Title
    B = Views
    C = Last Checked
    D = Published
    E = Video ID
    """
    sheet = client.open_by_key(SHEET_ID).worksheet("Shorts")
    existing_rows = sheet.get_all_values()

    video_id_col = [
        row[4] if len(row) > 4 else ""
        for row in existing_rows
    ]

    updates = []

    for short in shorts:
        video_id = short["video_id"]

        if video_id in video_id_col:
            row_number = video_id_col.index(video_id) + 1

            updates.append({
                "range": f"A{row_number}:E{row_number}",
                "values": [[
                    short["title"],
                    short["views"],
                    today_string(),
                    short["published"],
                    video_id,
                ]],
            })
        else:
            sheet.append_row([
                short["title"],
                short["views"],
                today_string(),
                short["published"],
                video_id,
            ])

            video_id_col.append(video_id)

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