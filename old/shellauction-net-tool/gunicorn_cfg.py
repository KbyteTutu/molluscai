# gunicorn_config.py
workers = 4
bind = '0.0.0.0:8080'
worker_class = 'sync'
timeout = 30
