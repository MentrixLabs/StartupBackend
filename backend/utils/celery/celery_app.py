from celery import Celery
from celery.schedules import crontab

celery = Celery(
    "report_tasks",
    broker="redis://localhost:6379/0",   
    backend="redis://localhost:6379/0",
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Moscow',
    enable_utc=True,
    include=["utils.tasks.generate_report"]
)

celery.conf.beat_schedule = {
    'generate-daily-report': {
        'task': 'utils.tasks.generate_report.generate_daily_reports',
        'schedule': crontab(minute='*/1'),
    },
}