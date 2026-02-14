
from flask import Blueprint, jsonify, current_app
import os

diagnostic_bp = Blueprint('diagnostic_bp', __name__)

@diagnostic_bp.route('/diagnostic/assets')
def check_assets():
    """
    Checks the physical size of static assets on the server.
    Returns a JSON report of file sizes.
    """
    static_folder = current_app.static_folder
    report = {
        "static_folder_path": static_folder,
        "files": {}
    }

    try:
        if not os.path.exists(static_folder):
            return jsonify({"error": f"Static folder not found at {static_folder}"}), 404

        for root, dirs, files in os.walk(static_folder):
            for file in files:
                if file.endswith(('.js', '.css', '.html')):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, static_folder)
                    try:
                        size = os.path.getsize(file_path)
                        report["files"][rel_path] = {
                            "size_bytes": size,
                            "status": "EMPTY" if size == 0 else "OK"
                        }
                    except Exception as e:
                        report["files"][rel_path] = {"error": str(e)}
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(report)
