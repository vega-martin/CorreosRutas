from flask import Blueprint, request, current_app, redirect, url_for, session, jsonify, flash, render_template
from werkzeug.utils import secure_filename
from app.utils.socketClient import send_data_for_processing
import pandas as pd

options_bp = Blueprint('options', __name__, template_folder='templates')

@options_bp.route('/options')
def options():
    return render_template('options.html')