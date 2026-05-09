"""
ESCRIBE Flask application entry point for Railway deployment.
Re-exports the Flask app from Guion_expert.webapp.server for use with Procfile.
"""

import os
import sys
from pathlib import Path

# Ensure Guion_expert is importable
guion_expert_path = Path(__file__).parent / "Guion_expert"
if str(guion_expert_path) not in sys.path:
    sys.path.insert(0, str(guion_expert_path))

# Import and re-export the Flask app
from webapp.server import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
