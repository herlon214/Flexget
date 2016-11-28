from __future__ import unicode_literals, division, absolute_import
from builtins import *  # noqa pylint: disable=unused-import, redefined-builtin

import logging

from flexget import plugin
from flexget.event import event
from flexget.config_schema import one_or_more
from flexget.plugin import PluginWarning
from flexget.utils.requests import Session as RequestSession, TimedLimiter
from requests.exceptions import RequestException

__name__ = 'rapidpush'
log = logging.getLogger(__name__)

RAPIDPUSH_URL = 'https://rapidpush.net/api'

requests = RequestSession(max_retries=3)
requests.add_domain_limiter(TimedLimiter('rapidpush.net', '5 seconds'))


class RapidpushNotifer(object):
    """
    Example::

      rapidpush:
        apikey: xxxxxxx (can also be a list of api keys)
        [category: category, default FlexGet]
        [title: title, default New release]
        [group: device group, default no group]
        [message: the message, default {{title}}]
        [channel: the broadcast notification channel, if provided it will be send to the channel subscribers instead of
            your devices, default no channel]
        [priority: 0 - 6 (6 = highest), default 2 (normal)]
    """
    schema = {
        'type': 'object',
        'properties': {
            'apikey': one_or_more({'type': 'string'}),
            'category': {'type': 'string', 'default': 'Flexget'},
            'title': {'type': 'string'},
            'group': {'type': 'string'},
            'channel': {'type': 'string'},
            'priority': {'type': 'integer', 'minimum': 0, 'maximum': 6},
            'message': {'type': 'string'},
            'file_template': {'type': 'string'}
        },
        'additionalProperties': False,
        'required': ['apikey']
    }

    def notify(self, apikey, title, message, category, group=None, channel=None, priority=None):
        wrapper = {}
        notification = {'title': title, 'message': message}
        if not isinstance(apikey, list):
            apikey = [apikey]

        if channel:
            wrapper['command'] = 'broadcast'
        else:
            wrapper['command'] = 'notify'
            notification['category'] = category
            if group:
                notification['group'] = group
            if priority:
                notification['priority'] = priority

        wrapper['data'] = notification
        for key in apikey:
            wrapper['apikey'] = key
            try:
                response = requests.post(RAPIDPUSH_URL, json=wrapper)
            except RequestException as e:
                raise PluginWarning(e.args[0])
            else:
                if response.json()['code'] > 400:
                    raise PluginWarning(response.json()['desc'])

    # Run last to make sure other outputs are successful before sending notification
    @plugin.priority(0)
    def on_task_output(self, task, config):
        notify_config = {
            'to': [{__name__: config}],
            'scope': 'entries',
            'what': 'accepted'
        }
        plugin.get_plugin_by_name('notify').instance.send_notification(task, notify_config)


@event('plugin.register')
def register_plugin():
    plugin.register(RapidpushNotifer, __name__, api_ver=2, groups=['notifiers'])
