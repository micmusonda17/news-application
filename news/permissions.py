"""
My own permission classes for the API.

DRF lets you write a class with a has_permission method that returns
True or False. I use these classes in api_views.py so that a reader can
not create articles and only an editor can approve them.
"""

from rest_framework import permissions


class IsJournalistOrReadOnly(permissions.BasePermission):
    """Everybody logged in can read, but only journalists can POST."""

    message = 'Only journalists are allowed to create articles.'

    def has_permission(self, request, view):
        # GET, HEAD and OPTIONS are 'safe methods' (just reading)
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        # for POST the user must be a journalist
        return request.user.is_authenticated and request.user.is_journalist()


class IsEditorOrAuthorOrReadOnly(permissions.BasePermission):
    """Rules for changing or deleting one article.

    Readers can only look. Editors can change or delete anything.
    Journalists can change or delete their own articles only.
    """

    message = 'You are not allowed to change this article.'

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_editor():
            return True
        if request.user.is_journalist() and obj.author == request.user:
            return True
        return False


class IsEditor(permissions.BasePermission):
    """Only an editor is allowed. I use this for approving articles."""

    message = 'Only an editor can approve an article.'

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_editor()


class IsReader(permissions.BasePermission):
    """Only a reader is allowed (used for the subscribed articles)."""

    message = 'Only a reader has subscriptions.'

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_reader()
