from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app, request
from datetime import timedelta, datetime
import uuid
import os
import shutil

main_bp = Blueprint('main', __name__, template_folder='templates')

# ------------------------------------------------------------
# SESSION SETTINGS
# ------------------------------------------------------------
@main_bp.before_request
def keep_session_alive():
    if request.endpoint == 'main.logout':
        return
    if "id" in session:
        session.permanent = True


# ------------------------------------------------------------
# MAIN ROUTE
# ------------------------------------------------------------
@main_bp.route('/', endpoint='root')
def index():
    """Main page - create an ID if doesn't exist"""
    if "id" not in session:
        session["id"] = str(uuid.uuid4())
        session.permanent = True
        current_app.logger.info(f"Sesion creada: {session['id']}")
    return render_template('index.html')


# ------------------------------------------------------------
# CLOSE SESSION
# ------------------------------------------------------------
def delete_user_folder(session_id):
    base = current_app.config.get("UPLOAD_FOLDER")
    if not base:
        current_app.logger.warning("UPLOAD_FOLDER no configurado")
        return

    folder = os.path.join(base, session_id)
    shutil.rmtree(folder, ignore_errors=True)


def delete_generated_maps(maps):
    base_dir = os.path.join(current_app.config.get("BASE_DIR"), "app", "static", "maps")
    for m in maps:
        file = os.path.join(base_dir, f"{m}.html")
        try:
            os.remove(file)
        except FileNotFoundError:
            pass
        except Exception as e:
            current_app.logger.warning(f"No se pudo borrar {file}: {e}")


@main_bp.route('/logout')
def logout():
    sid = session.get("id")
    maps = session.get("created_maps", [])

    if sid:
        delete_user_folder(sid)

    if maps:
        delete_generated_maps(maps)

    current_app.logger.info(f"Sesion cerrada: {sid}")
    session.clear()
    return redirect(url_for("main.root"))
