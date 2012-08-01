import string
from random import choice
from django.core.cache import cache
from django.http import HttpResponse

def random_str():
    chars = string.letters + string.digits
    return ''.join([choice(chars) for i in xrange(15)])

def test_one_get(request):
    cache.get(random_str())
    return HttpResponse("Hello World!")

def test_multiple_gets(request):
    cache.get(random_str())
    cache.get(random_str())
    cache.get(random_str())
    cache.get(random_str())
    cache.get(random_str())
    cache.get(random_str())
    return HttpResponse("Hello World!")

def test_multiple_duplicated_gets(request):
    """
    test in memory cache
    """
    a = random_str()
    b = random_str()
    c = random_str()
    cache.get(a)
    cache.get(b)
    cache.get(c)
    cache.get(a)
    cache.get(b)
    cache.get(c)
    return HttpResponse("Hello World!")