from flask_wtf import FlaskForm
from wtforms import StringField
import wtforms.validators as validator

class SquadForm(FlaskForm):
    squad_name = StringField("Squad Name:", validators=[validator.InputRequired(), Length(min=1, max=100)])

class PlaylistForm(FlaskForm):
    user_name = StringField("User Name:", validators=[validator.InputRequired(), Length(min=1, max=100)])
    playlist_link = StringField("Playlist Link:", validators=validator.InputRequired(), Length(min=1))