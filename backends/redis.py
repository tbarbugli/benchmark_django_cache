
from django.core.cache.backends.base import BaseCache, MEMCACHE_MAX_KEY_LENGTH
from django.utils.encoding import smart_str
import pickle
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

from nydus.db.base import create_cluster

CLIENT_NAME = 'redis_cache'

#caching for setting up hashing clusters
cache_clusters = {}

class CacheClass(BaseCache):
    def __init__(self, server, params):
        BaseCache.__init__(self, params)
        self.server = server
        self.params = params
        self.loads = pickle.loads
        self.dumps = pickle.dumps
        
    def _parse_config(self, config):
        '''
        Takes 127.0.0.1:6379/0;127.0.0.1:6379/1;127.0.0.1:6379/2
        And returns something nydus gets, like
        {
           0: {'host': 127.0.0.1, 'port': 6379, 'db': 0},
           1: {'host': 127.0.0.1, 'port': 6379, 'db': 1},
           2: {'host': 127.0.0.1, 'port': 6379, 'db': 2},
        }
        '''
        servers = config.split(';')
        hosts = {}
        for count, server in enumerate(servers):
            #127.0.0.1:6379/0 -> dict(host, port, db)
            host_and_port, path = server.split('/')
            host, port = host_and_port.split(':')
            port = int(port)
            db = path.strip('/')
            server_info = dict(host=host, port=port)
            if db.isdigit():
                db = int(db)
                server_info['db'] = db
            server_info['fail_silently'] = False
            server_info['timeout'] = 2
            hosts[count] = server_info
        return hosts
    
    def _create_cluster(self, hosts):
        #create a consistent Hashing cluster
        logger.info('creating a cache cluster for hosts %s', hosts)
        cluster = create_cluster({
            'engine': 'nydus.db.backends.redis.Redis',
            'router': 'nydus.db.routers.keyvalue.ConsistentHashingRouter',
            'hosts': hosts,
        })
        return cluster
    
    def _get_or_create_cluster(self, hosts):
        key = tuple(hosts)
        cluster = cache_clusters.get(key)
        if not cluster:
            cluster = self._create_cluster(hosts)
            cache_clusters[key] = cluster
        return cluster
    
    @property
    def _cache(self):
        '''
        Get the redis connection
        '''
        client = getattr(self, '_client', None)
        if not client:
            #we cant use this
            server = self.server
            hosts = self._parse_config(server)
            hosts = getattr(settings, 'NYDUS_CACHE_HOSTS', None) or hosts
            client = self._get_or_create_cluster(hosts)
            self._client = client
        return client
    
    def add(self, key, value, timeout=0):
        key = self._clean_key(key)
        serialized_value = self._serialize_value(value)
        result = self._cache.setnx(key, serialized_value)
        if timeout:
            self._cache.expire(key, timeout)
        return result

    def get(self, key, default=None):
        key = self._clean_key(key)
        val = self._cache.get(key)
        if val is not None:
            val = self._deserialize_value(val)
        val = default if val is None else val
        return val

    def set(self, key, value, timeout=0):
        timeout = self._get_redis_timeout(timeout)
        key = self._clean_key(key)
        self._set(self._cache, key, value, timeout)

    def delete(self, key):
        key = self._clean_key(key)
        self._cache.delete(key)

    def get_many(self, keys):
        keys = self._clean_keys(keys)
        
        with self._cache.map() as redis:
            serialized_results = [(key, redis.get(key)) for key in keys]
        
        #return a dict of results
        results = {}
        for key, serialized in serialized_results:
            #converts the type of our EventualCommand
            serialized = serialized._wrapped
            if serialized is not None:
                result = self._deserialize_value(serialized)
                results[key] = result
            
        return results

    def set_many(self, data, timeout=0):
        timeout = self._get_redis_timeout(timeout)
        
        #see which data is safe to store
        safe_data = {}
        for key, value in data.items():
            key = self._clean_key(key)
            safe_data[key] = value
            
        #set all the values using a map
        with self._cache.map() as redis:
            results = []
            for key, value in safe_data.items():
                result = self._set(redis, key, value, timeout)
                results.append(result)

    def delete_many(self, keys):
        keys = self._clean_keys(keys)
        #delete all the values using a map
        with self._cache.map() as redis:
            for key in keys:
                redis.delete(key)

    def incr(self, key, delta=1):
        '''
        Raise a value Error if it doesnt exist to be more compatible with
        memcached
        '''
        val = self._cache.incr(key, delta)
        if val == 1:
            raise ValueError('Key %s not found' % key)

        return val

    def decr(self, key, delta=1):
        val = self._cache.decr(key, delta)
        if val == -1:
            raise ValueError('Key %s not found' % key)
        return val

    def clear(self):
        self._cache.flushall()

    def close(self, **kwargs):
        self._cache.disconnect()
        
    def _set(self, redis, key, value, timeout):
        serialized_value = self._serialize_value(value)
        if timeout:
            result = redis.setex(key, serialized_value, timeout)
        else:
            result = redis.set(key, serialized_value)
        return result
    
    def _get_redis_timeout(self, timeout):
        timeout = timeout or self.default_timeout
        timeout = int(timeout)
        return timeout
    
    def _clean_keys(self, keys):
        clean_keys = map(self._clean_key, keys)
        return clean_keys
    
    def _clean_key(self, key):
        clean = smart_str(key)
        #raise an error if this key is not compatible with memcached
        self.validate_key(key)
        return clean
    
    def _serialize_value(self, value):
        if isinstance(value, (int, long)):
            #don't serialize numbers, otherwise we can't increment them
            serialized_value = value
        else:
            serialized_value = self.dumps(value)
        return serialized_value
    
    def _deserialize_value(self, serialized_value):
        if serialized_value is None:
            value = serialized_value
        elif serialized_value.isdigit():
            value = int(serialized_value)
        else:
            value = self.loads(serialized_value)
        return value
    
    def validate_key(self, key):
        """
        Warn about keys that would not be portable to the memcached
        backend. This encourages (but does not force) writing backend-portable
        cache code.

        """
        message = None
        if len(key) > MEMCACHE_MAX_KEY_LENGTH:
            message = 'Cache key will cause errors if used with memcached: %s (longer than %s)' % (key, MEMCACHE_MAX_KEY_LENGTH)
                    
        for char in key:
            if ord(char) < 33 or ord(char) == 127:
                message = 'Cache key contains characters that will cause errors if used with memcached: %r' % key
        if message:
            raise ValueError(message)



