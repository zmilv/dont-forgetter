from celery import shared_task
from django.core.mail import send_mail


@shared_task()
def send_email(pk):
    # send_mail(f'Task {self.title}', self.date, '', [''])
    print(pk)
    return None


@shared_task()
def heartbeat():
    print('BEAT')
