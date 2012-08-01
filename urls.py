from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    url(r'^test_one_get/$', 'frontend.views.test_one_get'),
    url(r'^test_multiple_gets/$', 'frontend.views.test_multiple_gets'),
    url(r'^test_multiple_duplicated_gets/$', 'frontend.views.test_multiple_duplicated_gets'),
)
