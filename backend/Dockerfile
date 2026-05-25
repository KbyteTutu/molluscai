FROM molluscai-base:v0.3

WORKDIR /app

COPY . .

# Remove stale celery beat schedule file to prevent auto-resume of old periodic tasks.
# This file persists across host reboots via volume mounts; clearing it at build time
# ensures no old schedules leak into containers.
RUN rm -f celerybeat-schedule celerybeat-schedule.db celerybeat-schedule.dat celerybeat.pid

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
