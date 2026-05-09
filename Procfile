web: gunicorn --workers 4 --threads 2 --worker-class sync --timeout 120 --bind 0.0.0.0:$PORT app:app
worker: python -m celery -A master_orchestrator worker --loglevel=info
