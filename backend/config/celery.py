"""Celery application.

A bare app for now — the worker and beat services start idle. Real tasks
(parsing, assessment recompute, notifications) are added in M3/M4.
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("aquageo")
# Settings are read from Django with the CELERY_ namespace.
app.config_from_object("django.conf:settings", namespace="CELERY")
# Auto-discover tasks.py modules across installed apps (none yet).
app.autodiscover_tasks()
