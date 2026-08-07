Запуск celery 

celery -A utils.celery.celery_worker.celery worker --loglevel=info --pool=solo

Запуск celery beat

celery -A utils.celery.celery_app beat --loglevel=info