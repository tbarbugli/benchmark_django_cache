from redis import CacheClass as RedisCache

class CacheClass(RedisCache):
    def close(self, **kwargs):
        pass