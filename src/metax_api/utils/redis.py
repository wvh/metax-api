from pickle import dumps as pickle_dumps, loads as pickle_loads
from random import choice as random_choice

from django.conf import settings
from redis.sentinel import Sentinel
from redis.exceptions import TimeoutError
from redis.sentinel import MasterNotFoundError

import logging
_logger = logging.getLogger(__name__)
d = logging.getLogger(__name__).debug

class RedisSentinelCache():

    def __init__(self, master_only=False):
        if not hasattr(settings, 'REDIS_SENTINEL'):
            raise Exception('Missing configuration from settings.py: REDIS_SENTINEL')
        if not settings.REDIS_SENTINEL.get('REDIS_SENTINEL_HOSTS', None):
            raise Exception('Missing configuration from settings.py for REDIS_SENTINEL: REDIS_SENTINEL_HOSTS')
        if not settings.REDIS_SENTINEL.get('REDIS_SENTINEL_SERVICE', None):
            raise Exception('Missing configuration from settings.py for REDIS_SENTINEL: REDIS_SENTINEL_SERVICE')
        if len(settings.REDIS_SENTINEL['REDIS_SENTINEL_HOSTS']) < 3:
            raise Exception('Invaling configuration in settings.py for REDIS_SENTINEL: REDIS_SENTINEL_HOSTS minimum number of hosts is 3')

        self._sentinel = Sentinel(settings.REDIS_SENTINEL['REDIS_SENTINEL_HOSTS'],
            socket_timeout=settings.REDIS_SENTINEL.get('SOCKET_TIMEOUT', 0.1))
        self._service_name = settings.REDIS_SENTINEL['REDIS_SENTINEL_SERVICE']
        self._DEBUG = settings.REDIS_SENTINEL.get('REDIS_SENTINEL_DEBUG', False)
        self._node_count = self._node_count()

        # always use master for read operations, for those times when you know you are going
        # to read the same key again from cache very soon
        self._read_from_master_only = master_only

    def set(self, key, value, **kwargs):
        if self._DEBUG:
            d('cache: set()...')
        pickled_data = pickle_dumps(value)
        master = self._get_master()

        try:
            master.set(key, pickled_data, **kwargs)
        except (TimeoutError, MasterNotFoundError):
            if self._DEBUG:
                d('cache: master timed out or not found. no write instances available. raising error')
            # no master available
            return

        if self._DEBUG:
            test = master.get(key)
            if test:
                d('cache: set() successful')
            else:
                d('cache: set() unsuccessful, could not get saved data?')

    def get(self, key, **kwargs):
        """
        Randomly select slave or master for reading. Fallback to master anyway in case of errors.

        Use of master can be forced by using the master_only flag in the constructor.
        """

        # todo allow reading from cache when master is down? could possibly serve stale data.
        # see redis.conf setting: slave-serve-stale-data
        if self._DEBUG:
            d('cache: get()...')

        if self._read_from_master_only:
            return self._get_from_master(key, **kwargs)
        else:
            if self._slave_chosen():
                try:
                    return self._get_from_slave(key, **kwargs)
                except TimeoutError:
                    pass
            # lady luck chose master, or read from slave had an error
            return self._get_from_master(key, **kwargs)

    def _get_from_slave(self, key, **kwargs):
        node = self._get_slave()
        try:
            res = node.get(key, **kwargs)
        except TimeoutError:
            if self._DEBUG:
                d('cache: slave.get() timed out, trying from master instead. fail-over in process?')
            # fail-over propbably happened, and the old slave is now a master
            # (in case there was only one slave). try master instead
            raise
        else:
            return pickle_loads(res) if res is not None else None

    def _get_from_master(self, key, **kwargs):
        master = self._get_master()
        try:
            res = master.get(key, **kwargs)
        except (TimeoutError, MasterNotFoundError):
            if self._DEBUG:
                d('cache: master timed out also. no read instances available. returning None')
            # uh oh, no master available either. either all redis instances have hit the bucket,
            # or there is a fail-over in process, and a new master will be in line in a moment
            return None
        return pickle_loads(res) if res is not None else None

    def _slave_chosen(self):
        return random_choice(range(0, self._node_count)) != 0

    def _get_master(self):
        if self._DEBUG:
            d('cache: getting master')
        return self._sentinel.master_for(self._service_name, socket_timeout=0.1)

    def _get_slave(self):
        if self._DEBUG:
            d('cache: getting slave')
        return self._sentinel.slave_for(self._service_name, socket_timeout=0.1)

    def _node_count(self):
        return len(self._sentinel.discover_slaves(self._service_name)) + 1 # +1 is master
