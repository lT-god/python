from flask import Blueprint

user_blue = Blueprint('user', __name__)

from . import views

