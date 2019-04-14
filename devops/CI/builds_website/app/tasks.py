import os

import Crypto.Random

from celery import Celery
from celery.utils import cached_property

from buildsmanager import BuildsManager
from slacknotifier import SlackNotifier

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis'),
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis')

celery = Celery('tasks', broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)


class MyTask(celery.Task):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__initialized = False

    def init(self):
        if not self.__initialized:
            self.__initialized = True
            Crypto.Random.atfork()

    @cached_property
    def bm(self):
        self.init()
        return BuildsManager()

    @cached_property
    def st(self):
        self.init()
        return SlackNotifier()

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        self.st.post_exception(
            f'Exception while handling task id {task_id}',
            str(einfo),
            {
                'args': str(args),
                'kwargs': str(kwargs)
            }
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)


@celery.task(base=MyTask, bind=True)
def add_instances(self: MyTask, *args, **kwargs):
    return self.bm.add_instances(*args, **kwargs)


@celery.task(base=MyTask, bind=True)
def stop_instance(self: MyTask, *args, **kwargs):
    return self.bm.stop_instance(*args, **kwargs)


@celery.task(base=MyTask, bind=True)
def start_instance(self: MyTask, *args, **kwargs):
    return self.bm.start_instance(*args, **kwargs)


@celery.task(base=MyTask, bind=True)
def terminate_instance(self: MyTask, *args, **kwargs):
    return self.bm.terminate_instance(*args, **kwargs)


@celery.task(base=MyTask, bind=True)
def terminate_group(self: MyTask, *args, **kwargs):
    return self.bm.terminate_group(*args, **kwargs)
