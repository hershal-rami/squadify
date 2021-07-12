from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, validators
from wtforms.fields.html5 import URLField


class NewSquadForm(FlaskForm):
    squad_name = StringField(validators=[validators.length(max=40), validators.input_required()])


class AddPlaylistForm(FlaskForm):
    user_name = StringField(validators=[validators.length(max=40), validators.input_required()])
    playlist_link = URLField(validators=[validators.length(max=200)])
    use_liked_songs = BooleanField()
