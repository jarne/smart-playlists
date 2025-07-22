import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv

# Load Spotify API credentials
load_dotenv()

SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv(
    "SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback"
)

MIN_ADDED_DATE = os.getenv("MIN_ADDED_DATE")

SCOPE = "playlist-modify-public playlist-read-private playlist-modify-private user-library-read"

sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope=SCOPE,
    )
)


def fetch_all_liked_tracks():
    tracks = []
    results = sp.current_user_saved_tracks(limit=50)
    print("Fetching liked tracks...")
    total_fetched = 0
    while True:
        print(f"Fetched {len(results['items'])} tracks in this batch.")
        for item in results["items"]:
            if not MIN_ADDED_DATE or item["added_at"] > MIN_ADDED_DATE:
                tracks.append(item)
                total_fetched += 1
            else:
                break
        if results["next"]:
            results = sp.next(results)
        else:
            break
    print(f"Total liked tracks fetched: {total_fetched}")
    return tracks


def get_or_create_playlist(user_id, playlist_name):
    results = sp.current_user_playlists(limit=50)
    while results:
        for playlist in results["items"]:
            if playlist["name"] == playlist_name:
                print(f"Found existing playlist: {playlist_name}")
                return playlist["id"]
        if results["next"]:
            results = sp.next(results)
        else:
            break
    # Create playlist if not found
    print(f"Creating new playlist: {playlist_name}")
    playlist = sp.user_playlist_create(user_id, playlist_name, public=False)
    return playlist["id"]


def main():
    print("Starting main process...")
    user_id = sp.me()["id"]
    print(f"Authenticated as user: {user_id}")
    liked_tracks = fetch_all_liked_tracks()

    # Group tracks by year-month of 'added_at'
    tracks_by_month = defaultdict(list)
    for item in liked_tracks:
        added_at = item["added_at"]
        dt = datetime.strptime(added_at, "%Y-%m-%dT%H:%M:%SZ")
        month_key = dt.strftime("%Y-%m")
        tracks_by_month[month_key].append(item["track"]["id"])
    print(f"Grouped tracks into {len(tracks_by_month)} months.")

    # For each month, create or get playlist and add tracks
    for month, track_ids in tracks_by_month.items():
        playlist_name = f"Liked Songs {month}"
        print(f"Processing month: {month} with {len(track_ids)} tracks.")
        playlist_id = get_or_create_playlist(user_id, playlist_name)

        # Get current tracks in playlist to avoid duplicates
        existing_tracks = set()
        results = sp.playlist_tracks(
            playlist_id, fields="items.track.id,next", additional_types=["track"]
        )
        existing_tracks.update(
            item["track"]["id"] for item in results["items"] if item["track"]
        )
        while results["next"]:
            results = sp.next(results)
            existing_tracks.update(
                item["track"]["id"] for item in results["items"] if item["track"]
            )
        print(
            f"Found {len(existing_tracks)} existing tracks in playlist '{playlist_name}'."
        )

        # Add only new tracks
        new_tracks = [tid for tid in track_ids if tid not in existing_tracks]
        print(f"Adding {len(new_tracks)} new tracks to playlist '{playlist_name}'.")
        for i in range(0, len(new_tracks), 100):
            sp.playlist_add_items(playlist_id, new_tracks[i : i + 100])
            print(
                f"Added tracks {i} to {i + min(100, len(new_tracks) - i)} to playlist '{playlist_name}'."
            )
    print("Main process completed.")


if __name__ == "__main__":
    main()
