import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")

CHANNELS = {
    "podcast": "UCDYiFfeMpXPcMZCoboIp5KQ",
    "yuna": "UCJe2Qttc2XCoIF1UUzooJeg",
    "brian": "UCQ7oLvBwGZshwx8e6vV4wwQ",
}


def parse_duration_seconds(duration):
    match = re.fullmatch(
        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
        duration,
    )

    if not match:
        return 0

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return hours * 3600 + minutes * 60 + seconds


def get_channel_stats(channel_id):
    url = "https://www.googleapis.com/youtube/v3/channels"

    params = {
        "part": "statistics",
        "id": channel_id,
        "key": API_KEY,
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()

    if not data.get("items"):
        raise ValueError(f"No YouTube channel found for ID: {channel_id}")

    stats = data["items"][0]["statistics"]

    return {
        "subscribers": int(stats.get("subscriberCount", 0)),
        "views": int(stats.get("viewCount", 0)),
        "videos": int(stats.get("videoCount", 0)),
    }


def get_recent_uploads(channel_id, max_results=50):
    """
    Returns recent uploads with video ID, title, views,
    publication date, duration, and duration in seconds.
    """
    search_url = "https://www.googleapis.com/youtube/v3/search"

    search_params = {
        "part": "snippet",
        "channelId": channel_id,
        "order": "date",
        "maxResults": min(max_results, 50),
        "type": "video",
        "key": API_KEY,
    }

    response = requests.get(
        search_url,
        params=search_params,
        timeout=30,
    )
    response.raise_for_status()

    search_items = response.json().get("items", [])

    video_ids = [
        item["id"]["videoId"]
        for item in search_items
        if item.get("id", {}).get("videoId")
    ]

    if not video_ids:
        return []

    videos_url = "https://www.googleapis.com/youtube/v3/videos"

    videos_params = {
        "part": "contentDetails,statistics,snippet",
        "id": ",".join(video_ids),
        "key": API_KEY,
    }

    response = requests.get(
        videos_url,
        params=videos_params,
        timeout=30,
    )
    response.raise_for_status()

    uploads = []

    for item in response.json().get("items", []):
        duration = item["contentDetails"]["duration"]
        duration_seconds = parse_duration_seconds(duration)

        uploads.append({
            "video_id": item["id"],
            "title": item["snippet"]["title"],
            "views": int(
                item.get("statistics", {}).get("viewCount", 0)
            ),
            "published": item["snippet"]["publishedAt"][:10],
            "duration": duration,
            "duration_seconds": duration_seconds,
        })

    return uploads


def get_recent_shorts(channel_id, max_results=50):
    uploads = get_recent_uploads(channel_id, max_results)

    return [
        video
        for video in uploads
        if video["duration_seconds"] <= 180
    ]


def get_recent_videos(channel_id, max_results=50):
    uploads = get_recent_uploads(channel_id, max_results)

    return [
        video
        for video in uploads
        if video["duration_seconds"] > 180
    ]


def get_recent_content(channel_id, max_results=50):
    """
    Retrieves uploads once, then splits them into videos and Shorts.

    This avoids making the same API requests twice.
    """
    uploads = get_recent_uploads(channel_id, max_results)

    return {
        "videos": [
            video
            for video in uploads
            if video["duration_seconds"] > 180
        ],
        "shorts": [
            video
            for video in uploads
            if video["duration_seconds"] <= 180
        ],
    }


if __name__ == "__main__":
    for name, channel_id in CHANNELS.items():
        stats = get_channel_stats(channel_id)
        content = get_recent_content(channel_id)

        print(
            f"{name}: "
            f"{stats['subscribers']} subscribers, "
            f"{len(content['videos'])} recent videos, "
            f"{len(content['shorts'])} recent Shorts"
        )