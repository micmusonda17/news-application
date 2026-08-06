"""
All my signals live in this file.

There are two things happening here:

1. After the migrations run I create the three groups (Reader, Editor,
   Journalist) and I give each group the permissions that the task asked
   for.

2. When an editor approves an article I:
       - send an email to everybody who is subscribed to the journalist
         or to the publisher, and
       - send a POST request to my own API endpoint /api/approved/ so
         that the approved article is 'shared' outside the website.
"""

import requests

from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.db.models.signals import post_migrate, post_save, pre_save
from django.dispatch import receiver

from .models import Article, Newsletter


# ---------------------------------------------------------------------
# 1. Create the groups and give them their permissions
# ---------------------------------------------------------------------

@receiver(post_migrate)
def create_groups_and_permissions(sender, **kwargs):
    """Create the three groups after the database tables are made.

    I use post_migrate because the permissions only exist in the
    database after the migrations have run.
    """
    # only run this for my own app, not for every app in the project
    if sender.name != 'news':
        return

    # get the content types so I can find the correct permissions
    article_type = ContentType.objects.get_for_model(Article)
    newsletter_type = ContentType.objects.get_for_model(Newsletter)

    def get_permission(action, model_name, content_type):
        """Small helper to fetch one permission like 'add_article'."""
        return Permission.objects.get(
            codename=f'{action}_{model_name}',
            content_type=content_type,
        )

    # This dictionary says which actions each group is allowed to do.
    # It comes straight from the instructions in the task.
    permissions_for_group = {
        'Reader': ['view'],
        'Editor': ['view', 'change', 'delete'],
        'Journalist': ['add', 'view', 'change', 'delete'],
    }

    for group_name, actions in permissions_for_group.items():
        group, created = Group.objects.get_or_create(name=group_name)
        for action in actions:
            group.permissions.add(
                get_permission(action, 'article', article_type)
            )
            group.permissions.add(
                get_permission(action, 'newsletter', newsletter_type)
            )
        group.save()


# ---------------------------------------------------------------------
# 2. What happens when an article gets approved
# ---------------------------------------------------------------------

@receiver(pre_save, sender=Article)
def remember_old_approved_value(sender, instance, **kwargs):
    """Remember if the article was already approved before we saved it.

    I need this because post_save can not tell me what the value used to
    be. Without this check the email would be sent every single time
    somebody saves an already approved article.
    """
    if instance.pk:
        # the article already exists, so get the old version from the db
        old_article = Article.objects.filter(pk=instance.pk).first()
        instance.was_approved_before = (
            old_article.approved if old_article else False
        )
    else:
        # brand new article, so it was definitely not approved before
        instance.was_approved_before = False


@receiver(post_save, sender=Article)
def article_approved(sender, instance, created, **kwargs):
    """Run after an article is saved.

    If the article has just been changed from not approved to approved
    then I send the emails and the POST request.
    """
    was_approved_before = getattr(instance, 'was_approved_before', False)

    # only carry on if the article changed from False to True
    if not instance.approved or was_approved_before:
        return

    send_article_to_subscribers(instance)
    post_article_to_api(instance)


def get_subscriber_emails(article):
    """Make a list of the email addresses that must get the article.

    Everybody who subscribed to the journalist gets the email, and if
    the article belongs to a publisher then the people who subscribed to
    that publisher get it as well.
    """
    emails = []

    # people who subscribed to the journalist that wrote the article
    for reader in article.author.followers.all():
        if reader.email:
            emails.append(reader.email)

    # people who subscribed to the publisher of the article
    if article.publisher:
        for reader in article.publisher.subscribers.all():
            if reader.email:
                emails.append(reader.email)

    # remove any duplicates (a reader could follow both)
    unique_emails = list(set(emails))
    return unique_emails


def send_article_to_subscribers(article):
    """Send the approved article by email to all the subscribers."""
    emails = get_subscriber_emails(article)

    if not emails:
        # nobody is subscribed so there is nothing to do
        return

    subject = f'New article: {article.title}'
    publisher_name = (
        article.publisher.name if article.publisher else 'Independent'
    )
    message = (
        f'Hello\n\n'
        f'A new article has been published on our news site.\n\n'
        f'Title: {article.title}\n'
        f'Author: {article.author.username}\n'
        f'Publisher: {publisher_name}\n\n'
        f'{article.content}\n\n'
        f'Thank you for subscribing.'
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=emails,
            fail_silently=False,
        )
    except Exception as error:
        # I do not want the website to crash if the email server is down
        print(f'Could not send the email: {error}')


def post_article_to_api(article):
    """Send the approved article to my own API with a POST request.

    The task said to use the requests module to POST the article to my
    own endpoint (/api/approved/). That endpoint then saves it in the
    ApprovedArticleLog table.
    """
    url = f'{settings.SITE_URL}/api/approved/'
    data = {
        'article': article.id,
        'title': article.title,
        'author_username': article.author.username,
        'publisher_name': (
            article.publisher.name if article.publisher else ''
        ),
    }

    try:
        response = requests.post(url, json=data, timeout=5)
        print(f'Posted article to the API. Status: {response.status_code}')
    except requests.exceptions.RequestException as error:
        # this happens if the server is not running, so I just print it
        print(f'Could not post the article to the API: {error}')
