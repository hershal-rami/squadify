# Squadify
PARTY TIME!!!

## Running in Development
1. Run MongoDB with a database and collection named `squads`
2. `poetry install --no-dev`
3. In `assets`, run `npm install && npm run dev`
4. In the Spotify dashboard, get the client ID and secret, and set the redirect URI to `http://127.0.0.1:5000`
5. Set the environment variables `SPOTIPY_CLIENT_ID`, `SPOTIPY_CLIENT_SECRET`, and `SPOTIPY_REDIRECT_URI="http://127.0.0.1:5000"`
6. Enter the virtualenv. For instance `poetry shell`.
7. `FLASK_ENV=development FLASK_APP=squadify flask run`

## Running in Release
1. Run MongoDB with a database and collection named `squads`
2. `poetry install`
3. In `assets`, run `npm install && npm run release`
4. In the Spotify dashboard, get the client ID and secret, and set the redirect URI to `http://127.0.0.1:5000`
5. Set the environment variables `SPOTIPY_CLIENT_ID`, `SPOTIPY_CLIENT_SECRET`, and `SPOTIPY_REDIRECT_URI="http://127.0.0.1:5000"`
6. `poetry run gunicorn squadify:app`
