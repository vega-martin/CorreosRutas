from flask import Blueprint, request, redirect, url_for, session
from werkzeug.utils import secure_filename
import os

subidaArchivos = Blueprint('subidaArchivos', __name__, template_folder='templates')