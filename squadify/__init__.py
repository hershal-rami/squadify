__version__ = "0.1.0"

import os
from flask import Flask, render_template, session, request, redirect
from flask_session import Session
import spotipy
import uuid
from flask_mongoengine import MongoEngine
import mongoengine as me
import string

app = Flask(__name__)

app.config['SECRET_KEY'] = os.urandom(64)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
Session(app)

caches_folder = './.spotify_caches/'
if not os.path.exists(caches_folder):
    os.makedirs(caches_folder)

def session_cache_path():
    return caches_folder + session.get('uuid')

app.config['MONGODB_SETTINGS'] = {
    'db': 'squads',
    'host': 'localhost',
    'port': 27017
}
db = MongoEngine()
db.init_app(app)

class Squad(me.Document):
    user = me.StringField()
    squad_name = me.StringField()
    squad_id = me.StringField()
    playlists = me.ListField()

@app.route("/")
def homepage():
    if not session.get('uuid'):
        # Step 1. Visitor is unknown, give random ID
        session['uuid'] = str(uuid.uuid4())

    cache_handler = spotipy.cache_handler.CacheFileHandler(cache_path=session_cache_path())
    auth_manager = spotipy.oauth2.SpotifyOAuth(scope='playlist-modify-public',
                                                cache_handler=cache_handler, 
                                                show_dialog=True,
                                                redirect_uri="http://localhost:5000")

    if request.args.get("code"):
        # Step 3. Being redirected from Spotify auth page
        auth_manager.get_access_token(request.args.get("code"))
        return redirect('/')

    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        # Step 2. Display sign in link when no token
        auth_url = auth_manager.get_authorize_url()
        return render_template("index.html", logged_in=False, auth_url=auth_url)

    # Step 4. Signed in, display data
    return render_template("index.html", logged_in=True)

@app.route('/sign_out')
def sign_out():
    try:
        # Remove the CACHE file (.cache-test) so that a new user can authorize.
        os.remove(session_cache_path())
        session.clear()
    except OSError as e:
        print ("Error: %s - %s." % (e.filename, e.strerror))
    return redirect('/')

@app.route("/about")
def view_about():
    cache_handler = spotipy.cache_handler.CacheFileHandler(cache_path=session_cache_path())
    auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler)
    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        return redirect('/')
    return render_template("about.html", logged_in=True)

# Viewing existing squads
@app.route("/squads")
def view_squads():
    cache_handler = spotipy.cache_handler.CacheFileHandler(cache_path=session_cache_path())
    auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler)
    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        return redirect('/')
    sp = spotipy.Spotify(auth_manager=auth_manager)
    return render_template("squads.html", logged_in=True, squads_list=Squad.objects(user="sp.me()['id']"))

# Viewing specific squad's playlists
@app.route("/squads/<uuid:squad_id>")
def view_squad(squad_id):
    cache_handler = spotipy.cache_handler.CacheFileHandler(cache_path=session_cache_path())
    auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler)
    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        return redirect('/')
    
    squad = Squad.objects(squad_id=squad_id).first()
    return render_template("squad.html", logged_in=True, squad=squad)

#class SquadForm(FlaskForm):
#    squad_name = StringField('Squad Name:')

# Create new squad
@app.route("/api/new", methods=["GET", "POST"])
def new_squad():
    cache_handler = spotipy.cache_handler.CacheFileHandler(cache_path=session_cache_path())
    auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler)
    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        return redirect('/')
 
    squad_form = SquadForm()

    '''    if squad_form.validate_on_submit():
        squad_name = squad_form.squad_name.data
        #generate an id, get user id, make playlists empty
        id = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
        while id 

        return redirect(url_for('add_to_squad',))'''

    return "Hello, World!"

# Add playlist to existing squad
@app.route("/api/add", methods=["GET", "POST"])
def add_to_squad(squad):
    return "Hello, World!"

# Public new playlist for squad
@app.route("/api/finish", methods=["GET", "POST"])
def finish_squad():
    return "Hello, World!"