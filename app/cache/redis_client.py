import redis

from .. import conf

redis_connection_pool = None


def setup_redis_connection_pool():
	global redis_connection_pool
	redis_connection_pool = redis.ConnectionPool.from_url(
		url=conf.REDIS_URL,
		decode_responses=False
	)


def get_redis_connection():
	if redis_connection_pool is None:
		# Assuming Gunicorn has not been initialized, use environment variable.
		setup_redis_connection_pool()
	return redis.StrictRedis(
		connection_pool=redis_connection_pool,
		charset='utf-8',
		decode_responses=False
	)
