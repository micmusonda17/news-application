"""
The main url file for the project.

It sends normal pages to news/urls.py and it sends anything that starts
with api/ to news/api_urls.py.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # the API urls
    path('api/', include('news.api_urls')),
    # the normal website pages
    path('', include('news.urls')),
]
