"""
All the urls of my API.

Everything in here already starts with /api/ because of the include()
in news_project/urls.py.
"""

from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from . import api_views

urlpatterns = [
    # you send your username and password here and you get a token back
    path('token/', obtain_auth_token, name='api_token'),

    # articles
    path('articles/', api_views.ArticleListCreateView.as_view(),
         name='api_article_list'),
    path('articles/subscribed/', api_views.SubscribedArticlesView.as_view(),
         name='api_subscribed_articles'),
    path('articles/<int:pk>/', api_views.ArticleDetailView.as_view(),
         name='api_article_detail'),
    path('articles/<int:article_id>/approve/',
         api_views.approve_article_api, name='api_approve_article'),

    # newsletters
    path('newsletters/', api_views.NewsletterListCreateView.as_view(),
         name='api_newsletter_list'),
    path('newsletters/<int:pk>/', api_views.NewsletterDetailView.as_view(),
         name='api_newsletter_detail'),

    # publishers and the logged in user
    path('publishers/', api_views.PublisherListView.as_view(),
         name='api_publisher_list'),
    path('me/', api_views.my_profile, name='api_my_profile'),

    # the endpoint my signal posts the approved articles to
    path('approved/', api_views.approved_articles_log,
         name='api_approved'),
]
