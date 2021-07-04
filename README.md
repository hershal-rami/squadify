# Squadify
PARTY TIME!!!

## Running in Development
1. Run MongoDB with a database and collection named `squads`
2. `poetry install`
3. Modify `assets/tailwind.config.js` and set `purge.enabled: false`
4. In `assets`, run `npm install && npm run build`
5. In the Spotify dashboard, get the client ID and secret, and set the direct URI to `http://127.0.0.1:5000`
6. Set the environment variables `SPOTIPY_CLIENT_ID`, `SPOTIPY_CLIENT_SECRET`, and `SPOTIPY_REDIRECT_URI="http://127.0.0.1:5000"`
7. `FLASK_ENV=development FLASK_APP=squadify poetry run flask run`
