benchmark_django_cache
======================

A small django app to benchmark different cache backends.
You need gnuplot and imagemagik installed.

How the benchmark graph
==========================================

Start the webservers:

    cache_backend=django_memcached python manage.py run_gunicorn -b 127.0.0.1:8000
    cache_backend=keep_connection_memcached python manage.py run_gunicorn -b 127.0.0.1:8001
    cache_backend=redis python manage.py run_gunicorn -b 127.0.0.1:8002
    cache_backend=keep_connection_redis python manage.py run_gunicorn -b 127.0.0.1:8003

When you have the four webserver running start the benchmark and wait:

    python scripts/benchmark.py