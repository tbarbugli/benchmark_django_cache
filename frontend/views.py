from django.core.cache import cache
from django.http import HttpResponse
import os

def test_one_get(request):
    cache.get(os.urandom(15))
    return HttpResponse("Hello World!")

def test_multiple_gets(request):
    cache.get(os.urandom(15))
    cache.get(os.urandom(15))
    cache.get(os.urandom(15))
    cache.get(os.urandom(15))
    cache.get(os.urandom(15))
    cache.get(os.urandom(15))
    return HttpResponse("Hello World!")

def test_multiple_duplicated_gets(request):
    """
    test in memory cache
    """
    a = os.urandom(15)
    b = os.urandom(15)
    c = os.urandom(15)
    cache.get(a)
    cache.get(b)
    cache.get(c)
    cache.get(a)
    cache.get(b)
    cache.get(c)
    return HttpResponse("Hello World!")