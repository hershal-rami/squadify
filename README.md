# Squadify
PARTY TIME!!!

## Running In Development
1. Run MongoDB with a database and collection named `squads`
2. `poetry install --no-dev`
3. In `css`, run `npm install && npm run dev`
4. In the Spotify dashboard, get the client ID and secret, and set the redirect URI to `http://127.0.0.1:5000`
5. Set the environment variables `SPOTIPY_CLIENT_ID`, `SPOTIPY_CLIENT_SECRET`, and `SPOTIPY_REDIRECT_URI="http://127.0.0.1:5000"`
6. Enter the virtualenv. For instance `poetry shell`.
7. `FLASK_ENV=development FLASK_APP=squadify flask run`

## Running In Production
1. Run MongoDB with a database called `squadify` containing two collections named `squads` and `tokens`
2. `poetry install`
3. In `css`, run `npm install && npm run prod`
4. In the Spotify dashboard, get the client ID and secret, and set the redirect URI
5. Set the environment variables `SPOTIPY_CLIENT_ID`, `SPOTIPY_CLIENT_SECRET`, and `SPOTIPY_REDIRECT_URI`
6. `poetry run gunicorn squadify:app`
