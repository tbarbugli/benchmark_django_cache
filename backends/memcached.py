from django.core.cache.backends.memcached import CacheClass as MemcachedCache

class CacheClass(MemcachedCache):
    def close(self, **kwargs):
        pass