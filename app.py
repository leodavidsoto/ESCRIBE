"""
ESCRIBE Flask application entry point for Railway deployment.
Re-exports the Flask app from Guion_expert.webapp.server for use with Procfile.
"""

import os
import sys
from pathlib import Path

# Ensure Guion_expert is importable
guion_expert_path = Path(__file__).parent / "Guion_expert"
webapp_path = guion_expert_path / "webapp"
for path in (guion_expert_path, webapp_path):
    path_str = str(path)
    if path_str in sys.path:
        sys.path.remove(path_str)
    sys.path.insert(0, path_str)

# Import and re-export the Flask app
try:
    from Guion_expert.webapp.server import app
except ImportError:
    # Fallback for when running from repo root
    from webapp.server import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
