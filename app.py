#importing all the necessary modules
import spotipy
import time
import os
import zipfile

from spotipy.oauth2 import SpotifyOAuth
from youtubesearchpython import VideosSearch
from pytube import YouTube
from flask import Flask, request, url_for, session, redirect, render_template, send_from_directory

#creating the flask app
app = Flask(__name__)

#used for configuring the cookies of the user
app.config['SESSION_COOKIE_NAME'] = "Spotify Cookies"
app.secret_key = "sadasfjaoigsj31231f&##dfd"
TOKEN_INFO = "token_info"

if not os.path.exists('downloads'):
        os.makedirs('downloads')

#route for bringing the users to the index page
@app.route('/')
def index():
    return render_template("index.html")

#redirects the user to the spotify authorization page
@app.route('/login')
def login():
    auth_url = create_spotify_oauth().get_authorize_url()
    return redirect(auth_url)

#fetch the user's access token, if valid, brings it to the next page
@app.route('/redirect')
def redirect_page():
    session.clear()
    code = request.args.get('code')
    token_info = create_spotify_oauth().get_access_token(code)
    session[TOKEN_INFO] = token_info
    return redirect(url_for("display_playlist", external = True))

#display the user's current playlist to choose from
@app.route('/display_playlist')
def display_playlist():
    
    #checks if the user is logged in
    try:
        token_info = get_token()
    except:
        print("User not logged in")
        return redirect('/')

    #creates a variable that will be use to access the user's spotify data
    sp = spotipy.Spotify(auth=token_info['access_token'])
    
    #gets the user's current playlist
    current_playlist = sp.current_user_playlists() 
    
    #declaring variable to save the needed playlist_info
    playlists_info = {
        'name': [],
        'description': [],
        'image_url': [],
        'id': []
    } 
    
    #iterates through the current playlist to only save the necessary info
    for playlist in current_playlist['items']:
        name = playlist['name']
        description = playlist['description']
        image_url = playlist['images'][0]['url'] if playlist['images'] else None
        id = playlist['id']
        
        playlists_info['name'].append(name)
        playlists_info['description'].append(description)
        playlists_info['image_url'].append(image_url)
        playlists_info['id'].append(id)
    
    #saves the playlist info into the user's cookies so it can be used in other routes
    session['playlists_info'] = playlists_info
    
    #renders the display of the playlist that the user will interact with to choose playlist
    return render_template("display.html", playlists_info=playlists_info)

#downloads the selected playlist of the user into MP3
@app.route('/get_songs', methods=["GET", "POST"])
def get_songs():
    
    #checks if the user is logged in
    try:
        token_info = get_token()
    except:
        print("User not logged in")
        return redirect('/')
    
    #fetch the playlist info from the user's cookies
    playlists_info = session.get('playlists_info')
    if not playlists_info:
        return "No playlists info available"
    
    #declaring variable to access the user's spotify data using spotipy module
    sp = spotipy.Spotify(auth=token_info['access_token'])   
        
    #checks if the user selected a playlist 
    if not request.form.getlist("playlists[]"): 
        return ("Must select one playlist") 
        
    #declaring the necessary variables  
    songs = []  
    tracks = [] 
    video_names = []    
    video_links = []    
        
    #iterates through the user's current playlist
    for playlist in request.form.getlist("playlists[]"):
        
        #finds the user's selected playlist to download and fetch all of it's song tracks
        for i in range(len(playlists_info['name'])):
            if playlist == playlists_info['name'][i]:
                results = sp.playlist_tracks(playlists_info['id'][i])
                tracks = results['items']
                
                # Iterate through paginated results to retrieve all tracks
                while results['next']:
                    results = sp.next(results)
                    tracks.extend(results['items'])
                
            # Extract song names from the tracks
            for track in tracks:
                song_name = track['track']['name']
                artist_name = track['track']['artists'][0]['name']
                songs.append({'name': song_name, 'artist': artist_name})
    
    #used for creating the video names that will be use for searching
    for song in songs:
        video_names.append(song['name'] + " " + song['artist'])
    
    #saves all the youtube links of the selected songs
    for i in range(len(video_names)):
        video_links.append(search_youtube(video_names[i]))
        
    
    #create a code that will save all of my downloaded songs into a zip file
    downloads_folder = os.path.join(os.path.dirname(__file__), 'downloads')
    os.makedirs(downloads_folder, exist_ok=True)
    zip_file_path = os.path.join(downloads_folder, 'playlist.zip')
    with zipfile.ZipFile(zip_file_path, 'w') as zip_file:
        #write the full code of downloading the songs
        for video_link in video_links:
            yt = YouTube(video_link)
            yt.streams.filter(only_audio=True).first().download('downloads/')
            zip_file.write(f"downloads/{yt.title}.mp4")
    
    #delete all the mp4 files in the downloads folder
    for file in os.listdir('downloads/'):
        if file.endswith('.mp4'):
            os.remove(os.path.join('downloads/', file))
    
    #return the zip file to the user
    return send_from_directory('downloads/', 'playlist.zip', as_attachment=True)
    
#used for getting the user's spotify token
def get_token():
    
    token_info = session.get(TOKEN_INFO, None)
    
    #first check if the user is login to spotify
    if not token_info:
        redirect(url_for('login', external=False))
    
    #saves the current time to now variable
    now = int(time.time())
    
    #checks if the token is already expired, if yes, it will refresh a new one
    is_expired = token_info['expires_at'] - now < 60
    if(is_expired):
        spotify_oauth = create_spotify_oauth()
        token_info = spotify_oauth.refresh_access_token(token_info['refresh_token'])
    return token_info

#creates the spotify_oauth object that will be use for authorization
def create_spotify_oauth():
    return SpotifyOAuth(
        client_id= "194e08ad50f74d5a981aabf408b66763",
        client_secret= "edfb119f182142389c4ad4fab6a1b5f3",
        redirect_uri= url_for("redirect_page", _external= True),
        scope = "user-library-read playlist-modify-public playlist-modify-private"
    )
    
#used for fetching the youtube links of each songs
def search_youtube(video_name):
    
    video_search = VideosSearch(video_name, limit=1)
    result = video_search.result()
    
    return (result['result'][0]['link'])
    

if __name__ == "__main__":
    app.run()