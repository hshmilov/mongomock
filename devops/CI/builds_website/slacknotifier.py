from slackclient import SlackClient


# pylint: disable=W0235
class SlackNotifierException(Exception):
    def __init__(self, message=''):
        super().__init__(message)


class SlackNotifier:
    def __init__(self, slack_token, default_channel):
        self.slack_token = slack_token
        self.default_channel = default_channel
        self.slack_client = SlackClient(slack_token)

    def __delete(self, channel, timestamp):
        result = self.slack_client.api_call(
            'chat.delete',
            channel=channel,
            ts=timestamp,
            as_user=True
        )

        if not result.get('ok'):
            raise SlackNotifierException(f'Error: {result}')

        return result

    def __post(self, channel, message, attachments, last_message):
        if last_message is None:
            result = self.slack_client.api_call(
                'chat.postMessage',
                channel=channel,
                text=message,
                as_user=True,
                attachments=attachments
            )
        else:
            message_channel, message_ts = last_message
            result = self.slack_client.api_call(
                'chat.update',
                channel=message_channel,
                text=message,
                as_user=True,
                attachments=attachments,
                ts=message_ts
            )

        if not result.get('ok'):
            raise SlackNotifierException(f'Error: {result}')

        return result

    def post_channel(self, message, channel=None, attachments=None, last_message=None):
        if not channel:
            channel = self.default_channel

        return self.__post(channel, message, attachments, last_message)

    def post_user(self, user, message, attachments=None, last_message=None):
        return self.__post(f'@{user}', message, attachments, last_message)

    def delete_message(self, channel, timestamp):
        return self.__delete(channel, timestamp)
