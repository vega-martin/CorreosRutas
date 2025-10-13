from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__, template_folder='templates')

@main_bp.route('/', endpoint='root')
def index():
    return render_template('index.html')