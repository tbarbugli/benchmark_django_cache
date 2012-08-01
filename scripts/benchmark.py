import subprocess
import itertools

GNUPLOT_BEGIN = """
set terminal png
set grid y
set xlabel "Request"
set ylabel "Response Time (ms)"
"""

GNUPLOT_GRAPH = """
set output "benchmark_%(output)s.png"
set title "%(title)s"
plot %(plot_data)s

"""

GNUPLOT_SERIE = '"%(data_file)s" using 10 smooth sbezier with lines title "%(title)s"'

CONCURRENCIES = [20, 40, 80]

REQUESTS = 250

MEMCACHE_CLASSES = ('django_memcached', 'keep_connection_memcached')
REDIS_CLASSES = ('redis', 'keep_connection_redis')

benchmarks = {
    'Single get per request': {
        'view': 'test_one_get',
        'caches': MEMCACHE_CLASSES + REDIS_CLASSES
    },
    # 'Redis single get per request': {
    #     'view': 'test_one_get',
    #     'caches': REDIS_CLASSES
    # },
    'Multiple get per request': {
        'view': 'test_multiple_gets',
        'caches': MEMCACHE_CLASSES + REDIS_CLASSES
    },
    # 'Redis multiple get per request': {
    #     'view': 'test_multiple_gets',
    #     'caches': REDIS_CLASSES
    # },
    'Multiple get with duplicated calls per request': {
        'view': 'test_multiple_duplicated_gets',
        'caches': MEMCACHE_CLASSES + REDIS_CLASSES
    },
    # 'Redis multiple get with duplicated calls per request': {
    #     'view': 'test_multiple_duplicated_gets',
    #     'caches': REDIS_CLASSES
    # },
}

WEBSERVER_PORT = {
    'django_memcached': '8000',
    'keep_connection_memcached': '8001',
    'redis': '8002',
    'keep_connection_redis': '8003'
}

def run_ab(view, cache_class, url, concurrency):
    port = WEBSERVER_PORT[cache_class]
    title = '%s @ %s' % (cache_class, concurrency)
    url = "http://127.0.0.1:%s/%s/" % (port, url)
    tsv = '%s_%s_%s.tsv' % (view, cache_class, concurrency)
    subprocess.call(["ab", "-c", str(concurrency), '-n', str(REQUESTS), '-k', '-g', tsv, url])
    return GNUPLOT_SERIE % {'data_file': tsv, 'title': title}

def benchmark_view(title, bench, concurrency):
    view = bench['view']
    plot_data = []
    for cache_cls in bench['caches']:
        plot_data.append(run_ab(view, cache_cls, view, concurrency))
    plot_data = ', '.join(plot_data)
    output = '%s_%s' % (title.strip(), concurrency)
    graph_data = GNUPLOT_GRAPH % {
        'title': title, 'output': output, 'plot_data': plot_data
    }
    return graph_data

gnuplot = ""
gnuplot += GNUPLOT_BEGIN

for title, bench in benchmarks.items():
    for concurrency in CONCURRENCIES:
        gnuplot += benchmark_view(title, bench, concurrency)

with open('_benchmark.tpl', 'w') as fp:
    fp.write(gnuplot)

subprocess.call(["gnuplot", "_benchmark.tpl"])

import time
time.sleep(1)
subprocess.call(["convert", "benchmark*.png", "-gravity", "North", "-append", "-quality", "100", "result.png"])
