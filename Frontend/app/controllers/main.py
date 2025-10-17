from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app, request
from datetime import timedelta, datetime
import uuid
import os
import shutil

main_bp = Blueprint('main', __name__, template_folder='templates')

# ------------------------------------------------------------
# SESSION SETTINGS
# ------------------------------------------------------------
@main_bp.before_app_request
def make_session_permanent():
    """Set the session as permanent and define its duration."""
    session.permanent = True
    current_app.permanent_session_lifetime = timedelta(minutes=5)

    now = datetime.now()
    last_activity = session.get("last_activity")

    if last_activity:
        elapsed = now - datetime.fromisoformat(last_activity)
        if elapsed > current_app.permanent_session_lifetime:
            sid = session.get("id")
            return redirect(url_for("main.logout", sid=sid))

    # Actualiza la marca de tiempo
    session["last_activity"] = now.isoformat()


# ------------------------------------------------------------
# MAIN ROUTE
# ------------------------------------------------------------
@main_bp.route('/', endpoint='root')
def index():
    """Main page - create an ID if doesn't exist"""
    if "id" not in session:
        session["id"] = str(uuid.uuid4())
        current_app.logger.info(f"Sesion creada: {session["id"]}")
    return render_template('index.html')


# ------------------------------------------------------------
# CLOSE SESSION
# ------------------------------------------------------------
@main_bp.route('/logout', methods=['GET'])
def logout():
    """Delete temp folder associated with the session and clear the session."""
    session_id = session.get("id") or request.args.get("sid")
    if session_id:
        base_upload = current_app.config.get("UPLOAD_FOLDER")
        user_folder = os.path.join(base_upload, session_id)

        if os.path.exists(user_folder):
            try:
                shutil.rmtree(user_folder)
                current_app.logger.info(f"Carpeta eliminada: {user_folder}")
            except Exception as e:
                current_app.logger.warning(f"No se pudo eliminar {user_folder}: {e}")

    session.clear()
    current_app.logger.info(f"Sesion cerrada: {session["id"]}")
    flash("Sesión cerrada correctamente.", "success")

    return redirect(url_for('main.root'))