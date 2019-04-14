import traceback

from retrying import retry

from buildsmanager import BuildsManager
from slacknotifier import SlackNotifier


@retry(stop_max_attempt_number=3, wait_fixed=5000)
def update(bm: BuildsManager):
    bm.update_instances_realtime()


def main():
    print('Initialized real time daemon')
    bm = BuildsManager()
    st = SlackNotifier()
    while True:
        try:
            update(bm)
        except Exception:
            exc = traceback.format_exc()
            print(f'Exception in rt_daemon.py: {str(exc)}')
            st.post_exception(
                'Exception while updating instances realtime',
                str(exc)
            )
            raise


if __name__ == '__main__':
    exit(main())
