from flask import Blueprint, current_app,session, redirect, url_for, render_template
import requests, os

index_bp = Blueprint('index', __name__, template_folder='templates')




# ------------------------------------------------------------
# ENDPOINTS
# ------------------------------------------------------------

@index_bp.route('/visualize_data')
def visualize_data():
    uploaded = session.get('uploaded_files', {})
    api_url = current_app.config.get("API_URL")
    data = {"id": session.get("id")}

    response = requests.post(f"{api_url}/get_fichero_unificado", data=data)
    save_path=""

    if response.status_code == 200:
        upload_dir = current_app.config.get("UPLOAD_FOLDER")
        save_path = os.path.join(upload_dir, session.get("id"), "Fichero_E.csv")
        with open(save_path, "wb") as f:
            f.write(response.content)
        uploaded["E"] = save_path
        current_app.logger.info("Se ha descargado el fichero unificado")
    else:
        current_app.logger.error("Error:", response.text)

    if not os.path.exists(save_path):
        return redirect(url_for('main.root'))

    return render_template('options.html')