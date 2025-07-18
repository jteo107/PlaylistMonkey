import os
from flask import Flask,session,url_for,redirect,request
from dotenv import load_dotenv
load_dotenv()
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler


app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(64)

client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
redirect_uri = os.getenv('REDIRECT_URI')
scope = 'playlist-modify-public,playlist-modify-private,user-read-private,user-read-email, user-library-read,playlist-read-private'

cache_handler = FlaskSessionCacheHandler(session)
sp_oauth = SpotifyOAuth(client_id=client_id,
                        client_secret=client_secret,
                        redirect_uri=redirect_uri,
                        scope=scope,
                        cache_handler=cache_handler,
                        show_dialog=True)

sp = Spotify(auth_manager =sp_oauth)

@app.route('/')
def homepage():
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    return redirect(url_for('get_playlists'))

@app.route('/callback')
def callback():
    sp_oauth.get_access_token(request.args['code'])
    return redirect(url_for('get_playlists'))

@app.route('/get_playlists')
def get_playlists():
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    playlists = sp.current_user_playlists()
    playlists_info = [(pl['name'],pl['external_urls']['spotify']) for pl in playlists['items']]
    playlists_html = '<br>'.join(
        [f'<a href="{url}">{name}</a>' for name, url in playlists_info])
    
    return playlists_html

@app.route('/log_out')
def log_out():
    session.clear()
    return redirect(url_for('homepage'))


    

if __name__ == "__main__":
    app.run(debug=True, port = 8888)
