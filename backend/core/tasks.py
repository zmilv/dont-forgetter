from celery import shared_task
from core.models import Event
from datetime import datetime, timezone


@shared_task()
def send_email(pk):
    # send_mail(f'Task {self.title}', self.date, '', [''])
    print(pk)
    return None


@shared_task()
def heartbeat():
    print('HEARTBEAT')
    current_datetime = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')
    expired_events = Event.objects.filter(utc_datetime__lt=current_datetime)
    for event in expired_events:
        print(event.title)
