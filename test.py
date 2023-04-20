import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import requests
import json
import api_info
from flask import Flask, request, jsonify, render_template, url_for
from flask_caching import Cache
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
import os.path
import webbrowser


AUTH_URL = 'https://accounts.spotify.com/api/token'

auth_response = requests.post(AUTH_URL, {
    'grant_type': 'client_credentials',
    'client_id': api_info.client_id,
    'client_secret': api_info.client_secret
})

auth_response_data = auth_response.json()

token = auth_response_data['access_token']

headers = {
    'Authorization': 'Bearer {token}'.format(token=token)
}

BASE_URL = 'https://api.spotify.com/v1/'

cache = Cache(config={'CACHE_TYPE': 'simple'})

taylor_albums = ["Midnights", "Red (Taylor's Version)", "Fearless (Taylor's Version)", "evermore", "folklore", "Lover", "reputation", "1989", "Speak Now", "Taylor Swift"]


class Node:
    def __init__(self, date, left=None, right=None):
        self.date = date
        self.left = left
        self.right = right


class BinarySearchTree:
    def __init__(self):
        self.root = None
    
    def insert(self, date):
        if self.root is None:
            self.root = Node(date)
        else:
            self._insert(date, self.root)

    def _insert(self, date, node):
        if date < node.date:
            if node.left is None:
                node.left = Node(date)
            else:
                self._insert(date, node.left)
        elif date > node.date:
            if node.right is None:
                node.right = Node(date)
            else:
                self._insert(date, node.right)
        else:
            raise ValueError("Date already exists in the tree")
        

# Load dates with openers from JSON file
with open("ErasTourDict.json", "r") as f:
        dates = json.load(f)

# Create cache file
cache_file = "cache.json"
if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            cache = json.load(f)
else:
    cache = {}

import spotipy
from spotipy.oauth2 import SpotifyOAuth

def create_playlist(concert_date, openers, fav_song, token):
    # Authenticate with Spotify
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=api_info.client_id,
                                                   client_secret=api_info.client_secret,
                                                   redirect_uri="http://localhost:3000",
                                                   scope=["playlist-modify-private",
                                                          "playlist-modify-public"]))
    
    # Create playlist
    playlist_name = f"Taylor Swift: The Eras Tour {concert_date}"
    playlist_description = "Playlist for Taylor Swift's The Eras Tour"
    playlist = sp.user_playlist_create(user=sp.me()["id"],
                                        name=playlist_name,
                                        public=True,
                                        description=playlist_description)
    
    # Add songs by openers
    for opener in openers:
        if opener not in cache:
            # Get three most popular songs by opener
            results = sp.search(q=opener, type="artist")
            if len(results["artists"]["items"]) == 0:
                print(f"Could not find {opener}")
                continue
            artist_id = results["artists"]["items"][0]["id"]
            top_tracks = sp.artist_top_tracks(artist_id=artist_id, country="US")
            tracks = [track["uri"] for track in top_tracks["tracks"][:3]]
            cache[opener] = tracks
        else:
            tracks = cache[opener]
        sp.playlist_add_items(playlist_id=playlist["id"], items=tracks)

    # Add songs similar

    # Get all of Taylor Swift's songs
    albums = sp.artist_albums("06HL4z0CvFAxyc27GXpf02", album_type="album", country='US', limit=50)['items']
    searchable_albums = []
    tv_albums = []
    for album in albums:
         for title in taylor_albums:
              if album['name'] == title:
                   searchable_albums.append(album['uri'])
    tv_albums = searchable_albums[1:]

    all_tracks = []
    for album in tv_albums:
        tracks = sp.album_tracks(album)["items"]
        all_tracks.extend(tracks)

    # Get audio features for all of Taylor Swift's songs
    audio_features = []
    for i in range(0, len(all_tracks), 50):
        batch = all_tracks[i:i + 50]
        audio_features.extend(sp.audio_features([t["id"] for t in batch]))

    # Find songs with similar danceability to user's favorite song
    results = sp.search(q=f"track:{fav_song} artist:Taylor Swift", type="track", limit=1)
    track_id = results["tracks"]["items"][0]["id"]
    fav_song_features = sp.audio_features(track_id)[0]
    playlist_tracks = []
    song_duration = []
    for track in all_tracks:
        track_features = next((f for f in audio_features if f["id"] == track["id"]), None)
        if track_features and abs(track_features["valence"] - fav_song_features["valence"]) <= 0.03:
                    if track["uri"] not in playlist_tracks:
                        playlist_tracks.append(track["uri"])
                        if len(playlist_tracks) == 30:
                            sp.user_playlist_add_tracks(user=sp.current_user()["id"], playlist_id=playlist["id"], tracks=playlist_tracks)


    # Save Cache
    with open(cache_file, "w") as f:
        json.dump(cache, f)

    # Return playlist
    return playlist

app = Flask(__name__)

@app.route("/")
def index():
    return """
    <form method="POST" action="/create_playlist">
        <label for="concert_date">Concert Date:</label>
        <input type="text" id="concert_date" name="concert_date"><br><br>
        <label for="fav_song">Favorite Taylor Swift Song:</label>
        <input type="text" id="fav_song" name="fav_song"><br><br>
        <input type="submit" value="Create Playlist">
    </form>
    """

@app.route("/create_playlist", methods=["POST"])
def create_playlist_route():
    concert_date = request.form["concert_date"]
    fav_song = request.form["fav_song"]

    # Search for concert date in binary search tree
    bst = BinarySearchTree()
    for date in dates.keys():
        bst.insert(date)
    node = bst.root
    while node is not None:
        if concert_date < node.date:
            node = node.left
        elif concert_date > node.date:
            node = node.right
        else:
            openers = dates[node.date]["openers"]
            access_token = token
            playlist = create_playlist(concert_date=concert_date, openers=openers, fav_song=fav_song, token=token)
            # Open playlist, lyrics, and music video in new tabs
            playlist_url = playlist["external_urls"]["spotify"]
            lyrics_url = "https://www.azlyrics.com/t/taylorswift.html"
            anti_hero_url = "https://www.youtube.com/watch?v=b1kbLwvqugk"
            webbrowser.open_new_tab(playlist_url)
            webbrowser.open_new_tab(lyrics_url)
            webbrowser.open_new_tab(anti_hero_url)

            return "Playlist created!"

if __name__ == '__main__':
    app.run()