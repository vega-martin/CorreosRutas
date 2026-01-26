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
    """Keep the current user session alive for active requests.

    This function is executed before every request handled by the
    `main_bp` blueprint. If a session identifier exists, the session
    is marked as permanent to refresh its lifetime.

    The logout endpoint is explicitly excluded to avoid extending
    the session during logout.

    Returns:
        None: Allows request processing to continue normally.
    """
    if request.endpoint == 'main.logout':
        return
    if "id" in session:
        session.permanent = True


# ------------------------------------------------------------
# MAIN ROUTE
# ------------------------------------------------------------
@main_bp.route('/', endpoint='root')
def index():
    """Render the main page and initialize a session if needed.

    If the user does not yet have a session identifier, a new UUID
    is generated and stored in the session. The session is marked
    as permanent and its creation is logged.

    Returns:
        flask.Response: Rendered HTML response for the main page.
    """
    if "id" not in session:
        session["id"] = str(uuid.uuid4())
        session.permanent = True
        current_app.logger.info(f"Session created: {session['id']}")
    return render_template('index.html')


# ------------------------------------------------------------
# CLOSE SESSION
# ------------------------------------------------------------
def delete_user_folder(session_id):
    """Delete the upload folder associated with a user session.

    This function removes the directory created for a specific
    session under the configured UPLOAD_FOLDER path. If the base
    upload directory is not configured, the operation is skipped
    and a warning is logged.

    Errors during deletion are ignored to prevent interruption
    of the logout flow.

    Args:
        session_id (str): Unique session identifier used as the
            folder name.
    """
    base = current_app.config.get("UPLOAD_FOLDER")
    if not base:
        current_app.logger.warning("UPLOAD_FOLDER not configurated")
        return

    folder = os.path.join(base, session_id)
    shutil.rmtree(folder, ignore_errors=True)


@main_bp.route('/logout')
def logout():
    """Terminate the current user session and clean up resources.

    This route deletes any server-side files associated with the
    user's session, logs the session closure, clears all session
    data, and redirects the user to the main page.

    Returns:
        flask.Response: Redirect response to the main route.
    """
    sid = session.get("id")

    if sid:
        delete_user_folder(sid)

    current_app.logger.info(f"Session closed: {sid}")
    session.clear()
    return redirect(url_for("main.root"))
