"""The urls for the normal website pages."""

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    # articles
    path('', views.article_list, name='article_list'),
    path('article/<int:article_id>/', views.article_detail,
         name='article_detail'),
    path('article/new/', views.article_create, name='article_create'),
    path('article/<int:article_id>/edit/', views.article_edit,
         name='article_edit'),
    path('article/<int:article_id>/delete/', views.article_delete,
         name='article_delete'),
    path('my-articles/', views.my_articles, name='my_articles'),

    # editor pages
    path('editor/', views.editor_dashboard, name='editor_dashboard'),
    path('editor/approve/<int:article_id>/', views.approve_article,
         name='approve_article'),

    # newsletters
    path('newsletters/', views.newsletter_list, name='newsletter_list'),
    path('newsletters/<int:newsletter_id>/', views.newsletter_detail,
         name='newsletter_detail'),
    path('newsletters/new/', views.newsletter_create,
         name='newsletter_create'),
    path('newsletters/<int:newsletter_id>/edit/', views.newsletter_edit,
         name='newsletter_edit'),
    path('newsletters/<int:newsletter_id>/delete/', views.newsletter_delete,
         name='newsletter_delete'),

    # readers
    path('subscriptions/', views.subscriptions, name='subscriptions'),
    path('my-feed/', views.my_feed, name='my_feed'),
    path('publishers/', views.publisher_list, name='publisher_list'),

    # log in and log out. Django already has views for these so I just
    # tell it which template to use.
    path('login/', auth_views.LoginView.as_view(
        template_name='news/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
]
