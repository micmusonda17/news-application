"""
The serializers turn my models into JSON for the API.

The task asked for serializers for Article, User, Newsletter and
Publisher, so all four are in this file.
"""

from rest_framework import serializers

from .models import (
    ApprovedArticleLog,
    Article,
    CustomUser,
    Newsletter,
    Publisher,
)


class UserSerializer(serializers.ModelSerializer):
    """Turns a user into JSON. I do not send the password out."""

    class Meta:
        """Serialise CustomUser without exposing the password."""

        model = CustomUser
        fields = [
            'id',
            'username',
            'email',
            'role',
            'subscriptions_publishers',
            'subscriptions_journalists',
        ]
        read_only_fields = ['id', 'role']


class PublisherSerializer(serializers.ModelSerializer):
    """Turns a publisher into JSON."""

    class Meta:
        """Serialise a publisher and the staff linked to it."""

        model = Publisher
        fields = [
            'id', 'name', 'description', 'email', 'editors', 'journalists'
        ]


class ArticleSerializer(serializers.ModelSerializer):
    """Turns an article into JSON.

    I added two extra read only fields so that the person using the API
    can see the name of the author and the publisher and not only their
    id numbers.
    """

    author_name = serializers.CharField(
        source='author.username', read_only=True
    )
    publisher_name = serializers.CharField(
        source='publisher.name', read_only=True, default=''
    )

    class Meta:
        """Serialise an article together with its author and publisher names."""

        model = Article
        fields = [
            'id',
            'title',
            'content',
            'author',
            'author_name',
            'publisher',
            'publisher_name',
            'created_at',
            'updated_at',
            'approved',
        ]
        # the author is filled in from the logged in user and only an
        # editor may change 'approved', so they are read only here
        read_only_fields = ['id', 'author', 'created_at', 'updated_at',
                            'approved']


class NewsletterSerializer(serializers.ModelSerializer):
    """Turns a newsletter into JSON."""

    author_name = serializers.CharField(
        source='author.username', read_only=True
    )

    class Meta:
        """Serialise a newsletter and the articles it contains."""

        model = Newsletter
        fields = [
            'id',
            'title',
            'description',
            'author',
            'author_name',
            'publisher',
            'articles',
            'created_at',
        ]
        read_only_fields = ['id', 'author', 'created_at']


class ApprovedArticleLogSerializer(serializers.ModelSerializer):
    """Used by the /api/approved/ endpoint that my signal posts to."""

    class Meta:
        """Serialise the log entry written when an article is approved."""

        model = ApprovedArticleLog
        fields = [
            'id',
            'article',
            'title',
            'author_username',
            'publisher_name',
            'shared_at',
        ]
        read_only_fields = ['id', 'shared_at']
