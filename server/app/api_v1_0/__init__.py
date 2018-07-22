from flask import Blueprint

api = Blueprint('api', __name__)
from . import (
    authentication,
    errors,
    heroes,
    clans,
    units,
    mines,
)
