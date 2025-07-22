import os
from flask import Flask,session,url_for,redirect,request
from dotenv import load_dotenv
load_dotenv()
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler
from flask import render_template
import re


app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(64)

client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
redirect_uri = os.getenv('REDIRECT_URI')
scope = (
    'user-top-read '
    'playlist-modify-public '
    'playlist-modify-private '
    'user-read-private '
    'user-read-email '
    'user-library-read '
    'playlist-read-private'
)

cache_handler = FlaskSessionCacheHandler(session)
sp_oauth = SpotifyOAuth(client_id=client_id,
                        client_secret=client_secret,
                        redirect_uri=redirect_uri,
                        scope=scope,
                        cache_handler=cache_handler,
                        show_dialog=True)

def getClient():
    token_info = cache_handler.get_cached_token()
    if not sp_oauth.validate_token(token_info):
        return None
    return Spotify(auth_manager=sp_oauth)

@app.route('/login')
def login():
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    return redirect(url_for('get_playlists'))

@app.route('/callback')
def callback():
    sp_oauth.get_access_token(request.args['code'])
    return redirect(url_for('dashboard'))

@app.route('/get_playlists')
def get_playlists():
    sp = getClient()
    if not sp:
        return redirect(url_for('login'))
    playlists = sp.current_user_playlists()
    playlists_info = [(pl['name'],pl['external_urls']['spotify']) for pl in playlists['items']]
    playlists_html = '<br>'.join(
        [f'<a href="{url}">{name}</a>' for name, url in playlists_info])
    
    return playlists_html

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/dashboard')
def dashboard():
    sp = getClient()
    if not sp:
        return redirect(url_for('login'))

    return render_template('dashboard.html')

@app.route('/top_artists')
def get_top_artists():
    sp = getClient()
    if not sp:
        return redirect(url_for('login'))
    top_artists = sp.current_user_top_artists(limit=50)
    user_top_artists = [(i + 1, artist['name'], artist['external_urls']['spotify']) for i, artist in enumerate(top_artists['items'])]
    artists_html = '<br>'.join(
        [f'{rank}. <a href="{url}">{name}</a>' for rank, name, url in user_top_artists])
    return artists_html

@app.route('/top_tracks')
def get_top_tracks():
    sp = getClient()
    if not sp:
        return redirect(url_for('login'))
    top_tracks = sp.current_user_top_tracks(limit=50)
    user_top_tracks = [(i + 1, track['name'], track['external_urls']['spotify']) for i, track in enumerate(top_tracks['items'])]
    tracks_html = '<br>'.join(
        [f'{rank}. <a href="{url}">{name}</a>' for rank, name, url in user_top_tracks])
    return tracks_html

@app.route('/organize_liked')
def organize_liked():
    sp = getClient()
    if not sp:
        return redirect(url_for('login'))
    return render_template('organizer.html')

@app.route('/perform_organize',methods = ['POST'])
def perform_organize():
    sp = getClient()
    if not sp:
        return redirect(url_for('login'))
    method = request.form.get('method')
    liked_tracks = getLiked()
    if not liked_tracks:
        return "No liked tracks found."
    match method:
        case 'artist':
            playlists = organize_by_artist(liked_tracks, sp)
        case 'genre':
            playlists = organize_by_genre(liked_tracks, sp)
        case 'decade':
            playlists = organize_by_year(liked_tracks, sp)
        case 'album':
            playlists = organize_by_album(liked_tracks, sp)
        case 'popularity':
            playlists = organize_by_popularity(liked_tracks, sp)
        case 'frequency':
            playlists = organize_by_frequency(sp)
        case 'top_artists':
            playlists = organize_by_top_artists(liked_tracks, sp)
        case 'top_songs':
            playlists = organize_by_top_songs(liked_tracks, sp)
    if not playlists:
        return "No playlists created."
    playlists_html = '<br>'.join(
        [f'<h1> All of your newly organized playlists!</h1>'] +
        [f'<a href="{playlist["external_urls"]["spotify"]}">{playlist["name"]}</a>' for playlist in playlists]
    )
    return playlists_html
    


def getLiked():
    sp = getClient()
    if not sp:
        return redirect(url_for('login'))
    liked_tracks = []
    limit = 50
    offset = 0
    while True:
        current_batch = sp.current_user_saved_tracks(limit=limit, offset=offset)
        if not current_batch['items']:
            break
        liked_tracks.extend(current_batch['items'])
        offset += limit
    return liked_tracks

def organize_by_artist(liked_tracks,sp):
    user_id = sp.current_user()['id']
    if not liked_tracks:
        return "Null"
    artists = {}
    for item in liked_tracks:
        track = item['track']
        artist_name = track['artists'][0]['name']
        if artist_name not in artists:
            artists[artist_name] = []
        artists[artist_name].append(track)

    playlists = []
    for artist, tracks in artists.items():
        safe_artist = re.sub(r'[^\w\s]', '', artist)
        playlist = sp.user_playlist_create(user_id, f"Your Essential {safe_artist} Playlist", public=True, collaborative=False, description=f"All of your favorite songs by {artist}")
        track_ids = [track['id'] for track in tracks if track['id']]
        for i in range(0, len(track_ids), 100):
            sp.playlist_add_items(playlist['id'], track_ids[i:i+100])
        playlists.append(playlist)
    return playlists

def organize_by_genre(liked_tracks,sp):
    user_id = sp.current_user()['id']
    if not liked_tracks:
        return "Null"
    genres = {}
    artist_cache = {}
    for item in liked_tracks:
        track = item['track']
        artist_id = track['artists'][0]['id']
        if artist_id in artist_cache:
            artist_data = artist_cache[artist_id]
        else:
            artist_data = sp.artist(artist_id)
            artist_cache[artist_id] = artist_data
        artist_genres = artist_data.get('genres', [])
        if not artist_genres:
            genre_name = "Miscellaneous"
        else:
            genre_name = artist_genres[0]
        
        if genre_name not in genres:
            genres[genre_name] = []
        genres[genre_name].append(track)
    playlists = []
    for genre,tracks in genres.items():
        playlist = sp.user_playlist_create(user_id, f"Your Essential {genre} Playlist", public=True, collaborative=False, description=f"All of your favorite {genre} songs")
        playlists.append(playlist)
        track_ids = [track['id'] for track in tracks if track['id']]
        for i in range(0, len(track_ids), 100):
            sp.playlist_add_items(playlist['id'], track_ids[i:i+100])
    return playlists

def organize_by_year(liked_tracks,sp):
    user_id = sp.current_user()['id']
    if not liked_tracks:
        return "Null"
    decades = {}
    for item in liked_tracks:
        track = item['track']
        temp_decade = track['album']['release_date'][:3]
        decade = temp_decade + '0s'
        if decade not in decades:
            decades[decade] = []
        decades[decade].append(track)
    playlists = []
    for decade, tracks in decades.items():
        playlist = sp.user_playlist_create(user_id, f"Your Essential {decade} Playlist", public=True, collaborative=False, description=f"All of your favorite songs from the {decade}")
        playlists.append(playlist)
        track_ids = [track['id'] for track in tracks if track['id']]
        for i in range(0, len(track_ids), 100):
            sp.playlist_add_items(playlist['id'], track_ids[i:i+100])

def organize_by_album(liked_tracks,sp):
    user_id = sp.current_user()['id']
    if not liked_tracks:
        return "Null"
    albums = {}
    for item in liked_tracks:
        track = item['track']
        album_name = track['album']['name']
        if album_name not in albums:
            albums[album_name] = []
        albums[album_name].append(track)
    playlists = []
    for album, tracks in albums.items():
        playlist = sp.user_playlist_create(user_id, f"Your Essential {album} Playlist", public=True, collaborative=False, description=f"All of your favorite songs from the album {album}")
        playlists.append(playlist)
        track_ids = [track['id'] for track in tracks if track['id']]
        for i in range(0, len(track_ids), 100):
            sp.playlist_add_items(playlist['id'], track_ids[i:i+100])

def organize_by_popularity(liked_tracks,sp):
    user_id = sp.current_user()['id']
    if not liked_tracks:
        return "Null"
    arr1 = []
    arr2 = []
    arr3 = []
    arr4 = []
    playlist1 = sp.user_playlist_create(user_id, "Your Mainstream Hits", public=True, collaborative=False, description="All of your favorite universally recognized bangers in one playlist!")
    playlist2 = sp.user_playlist_create(user_id, "Sleeper Picks", public=True, collaborative=False, description="Your favorite underrated gems!")
    playlist3 = sp.user_playlist_create(user_id, "Gatekeeping Much?", public=True, collaborative=False, description="Oh you kept these ones a secret, huh?")
    playlist4 = sp.user_playlist_create(user_id, "What is this?", public=True, collaborative=False, description="Where did you even find these????")
    playlists = []
    for item in liked_tracks:
        track = item['track']
        track_popularity = track['popularity']
        if track_popularity >= 80 and track_popularity <= 100:
            arr1.append(track['id'])
        elif track_popularity >= 50 and track_popularity < 80:
            arr2.append(track['id'])
        elif track_popularity >= 20 and track_popularity < 50:
            arr3.append(track['id'])
        else:
            arr4.append(track['id'])
    popularity_add_helper(sp, playlist1,arr1)
    popularity_add_helper(sp, playlist2,arr2)
    popularity_add_helper(sp, playlist3,arr3)
    popularity_add_helper(sp, playlist4,arr4)
    playlists.append(playlist1)
    playlists.append(playlist2)
    playlists.append(playlist3)
    playlists.append(playlist4)
    return playlists

def popularity_add_helper(sp, playlist, track_ids):
    if not track_ids:
        return "Null"
    
    playlist_id = playlist['id']
    
    for i in range(0, len(track_ids), 100):
        batch = track_ids[i:i+100]
        sp.playlist_add_items(playlist_id, batch)

def organize_by_frequency(sp):
    user_id = sp.current_user()['id']
    groups = playlist_grouper(sp, getLiked())
    if not groups:
        return "No liked tracks found."
    low_frequency = groups['low_frequency']
    medium_frequency = groups['medium_frequency']
    high_frequency = groups['high_frequency']
    playlist1 = sp.user_playlist_create(user_id, "Occasional Favorites", public=True, collaborative=False, description="Remember these songs? It's all coming back now, isn't it?")
    playlist2 = sp.user_playlist_create(user_id, "Regular Favorites", public=True, collaborative=False, description="Oh you love these ones, huh?")
    playlist3 = sp.user_playlist_create(user_id, "Your All-Time Favorites", public=True, collaborative=False, description="You're obsessed, and we don't blame you!")
    for track in low_frequency:
        sp.playlist_add_items(playlist1['id'], [track['track']['id']])
    for track in medium_frequency:
        sp.playlist_add_items(playlist2['id'], [track['track']['id']])
    for track in high_frequency:
        sp.playlist_add_items(playlist3['id'], [track['track']['id']])
    playlists = []
    playlists.append(playlist1)
    playlists.append(playlist2)
    playlists.append(playlist3)
    return playlists


def playlist_grouper(sp, liked_tracks):
    user_id = sp.current_user()['id']
    if not liked_tracks:
        return {
            'low_frequency': [],
            'medium_frequency': [],
            'high_frequency': []
        }
    short_ids = {t['id'] for t in sp.current_user_top_tracks(time_range='short_term', limit=50)['items']}
    medium_ids = {t['id'] for t in sp.current_user_top_tracks(time_range='medium_term', limit=50)['items']}
    long_ids = {t['id'] for t in sp.current_user_top_tracks(time_range='long_term', limit=50)['items']}

    grouped_playlists = {
        'low_frequency': [],
        'medium_frequency': [],
        'high_frequency': []
    }

    for track in liked_tracks:
        track_id = track['track']['id']
        freq_score = sum([
            track_id in short_ids,
            track_id in medium_ids,
            track_id in long_ids
        ])

        if freq_score == 1:
            grouped_playlists['low_frequency'].append(track)
        elif freq_score == 2:
            grouped_playlists['medium_frequency'].append(track)
        elif freq_score == 3:
            grouped_playlists['high_frequency'].append(track)

    return grouped_playlists

def organize_by_top_artists(liked_tracks, sp):
    user_id = sp.current_user()['id']
    if not liked_tracks:
        return "Null"
    top_artists = sp.current_user_top_artists(limit=20)
    artist_ids = {artist['id'] for artist in top_artists['items']}
    temp_artists = {}
    playlists = []
    for item in liked_tracks:
        track = item['track']
        if any(artist['id'] in artist_ids for artist in track['artists']):
            for artist in track['artists']:
                artist_name = track['artists'][0]['name']
                if artist_name not in temp_artists:
                    temp_artists[artist_name] = []
                temp_artists[artist_name].append(track)
    for artist, tracks in temp_artists.items():
        safe_artist = re.sub(r'[^\w\s]', '', artist)
        playlist = sp.user_playlist_create(user_id, f"Your Essential {safe_artist} Playlist", public=True, collaborative=False, description=f"All of your favorite songs by {artist}")
        playlists.append(playlist)
        track_ids = [track['id'] for track in tracks if track['id']]
        for i in range(0, len(track_ids), 100):
            sp.playlist_add_items(playlist['id'], track_ids[i:i+100])
    return playlists

def organize_by_top_songs(liked_tracks, sp):
    user_id = sp.current_user()['id']
    if not liked_tracks:
        return "Null"
    playlists = []
    short_term_tracks = sp.current_user_top_tracks(time_range='short_term', limit=50)
    medium_term_tracks = sp.current_user_top_tracks(time_range='medium_term', limit=50)
    long_term_tracks = sp.current_user_top_tracks(time_range='long_term', limit=50)
    short_term_playlist = sp.user_playlist_create(user_id, "Your Month-Long Favorites", public=True, collaborative=False, description="Your favorite songs from the past month! What have you been up to lately?")
    medium_term_playlist = sp.user_playlist_create(user_id, "Your Six-Month Favorites", public=True, collaborative=False, description="Your favorite songs from the past 6 months! Oh you really love these ones, huh?")
    long_term_playlist = sp.user_playlist_create(user_id, "Your Year-Long Favorites", public=True, collaborative=False, description="Your favorite songs from the past year! You're obsessed, and so are we!")
    liked_ids = set(
        track['track']['id'] for track in liked_tracks
        if track.get('track') and track['track'].get('id')
    )
    for track in short_term_tracks['items']:
        if track['id'] in liked_ids:
            sp.playlist_add_items(short_term_playlist['id'], [track['id']])
    for track in medium_term_tracks['items']:
        if track['id'] in liked_ids:
            sp.playlist_add_items(medium_term_playlist['id'], [track['id']])
    for track in long_term_tracks['items']:
        if track['id'] in liked_ids:
            sp.playlist_add_items(long_term_playlist['id'], [track['id']])
    playlists.append(short_term_playlist)
    playlists.append(medium_term_playlist)
    playlists.append(long_term_playlist)
    return playlists
        



@app.route('/log_out')
def log_out():
    session.clear()
    return redirect(url_for('home'))


    

if __name__ == "__main__":
    app.run(debug=True, port = 8888)
