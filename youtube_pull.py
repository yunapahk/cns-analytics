import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = "UCDYiFfeMpXPcMZCoboIp5KQ"


def parse_duration_seconds(duration):
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def get_channel_stats():
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "statistics",
        "id": CHANNEL_ID,
        "key": API_KEY
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    stats = data["items"][0]["statistics"]
    return {
        "subscribers": int(stats.get("subscriberCount", 0)),
        "views": int(stats.get("viewCount", 0)),
        "videos": int(stats.get("videoCount", 0))
    }


def get_recent_shorts(max_results=15):
    search_url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "channelId": CHANNEL_ID,
        "order": "date",
        "maxResults": max_results,
        "type": "video",
        "key": API_KEY
    }
    resp = requests.get(search_url, params=params)
    resp.raise_for_status()
    video_ids = [item["id"]["videoId"] for item in resp.json()["items"]]

    videos_url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "contentDetails,statistics,snippet",
        "id": ",".join(video_ids),
        "key": API_KEY
    }
    resp = requests.get(videos_url, params=params)
    resp.raise_for_status()

    shorts = []
    for item in resp.json()["items"]:
        duration = item["contentDetails"]["duration"]
        if parse_duration_seconds(duration) <= 180:
            shorts.append({
                "video_id": item["id"],
                "title": item["snippet"]["title"],
                "views": int(item["statistics"].get("viewCount", 0)),
                "published": item["snippet"]["publishedAt"][:10]
            })
    return shorts


if __name__ == "__main__":
    stats = get_channel_stats()
    print(stats)
    shorts = get_recent_shorts()
    print(f"Found {len(shorts)} shorts")
    for s in shorts:
        print(s)