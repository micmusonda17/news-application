"""
The views for the normal website (not the API).

I used function based views because I find them easier to read.
Every view that changes something checks the role of the user first so
that a reader can not do the work of a journalist or an editor.
"""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    ArticleForm,
    NewsletterForm,
    RegisterForm,
    SubscriptionForm,
)
from .models import Article, Newsletter, Publisher


# ---------------------------------------------------------------------
# Small helper functions
# ---------------------------------------------------------------------

def check_role(user, allowed_roles):
    """Stop the user if their role is not in the allowed list.

    I call this at the top of the views that must be protected. If the
    role is wrong django shows the 403 Forbidden page.
    """
    if user.role not in allowed_roles:
        raise PermissionDenied(
            'You do not have permission to open this page.'
        )


# ---------------------------------------------------------------------
# Sign up and log in
# ---------------------------------------------------------------------

def register(request):
    """Let a new person make an account and choose their role."""
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # log the new user in straight away
            login(request, user)
            messages.success(
                request,
                f'Welcome {user.username}, your account was created.'
            )
            return redirect('article_list')
    else:
        form = RegisterForm()

    return render(request, 'news/register.html', {'form': form})


# ---------------------------------------------------------------------
# Articles
# ---------------------------------------------------------------------

def article_list(request):
    """Show all the approved articles on the home page."""
    articles = Article.objects.filter(approved=True)

    # if somebody typed something in the search box, filter the list
    search = request.GET.get('search', '')
    if search:
        articles = articles.filter(title__icontains=search)

    context = {
        'articles': articles,
        'search': search,
    }
    return render(request, 'news/article_list.html', context)


@login_required
def article_detail(request, article_id):
    """Show one single article."""
    article = get_object_or_404(Article, id=article_id)

    # an article that is not approved yet may only be seen by the
    # journalist who wrote it or by an editor
    if not article.approved:
        if request.user != article.author and not request.user.is_editor():
            raise PermissionDenied('This article is not approved yet.')

    return render(request, 'news/article_detail.html', {'article': article})


@login_required
def article_create(request):
    """Let a journalist write a new article."""
    check_role(request.user, ['journalist'])

    if request.method == 'POST':
        form = ArticleForm(request.POST)
        if form.is_valid():
            article = form.save(commit=False)
            # the author is always the person that is logged in
            article.author = request.user
            article.save()
            messages.success(
                request,
                'Your article was saved. An editor has to approve it.'
            )
            return redirect('my_articles')
    else:
        form = ArticleForm()

    context = {'form': form, 'page_title': 'Write a new article'}
    return render(request, 'news/article_form.html', context)


@login_required
def article_edit(request, article_id):
    """Let a journalist or an editor change an article."""
    article = get_object_or_404(Article, id=article_id)
    check_role(request.user, ['journalist', 'editor'])

    # a journalist may only edit their own articles
    if request.user.is_journalist() and article.author != request.user:
        raise PermissionDenied('You can only edit your own articles.')

    if request.method == 'POST':
        form = ArticleForm(request.POST, instance=article)
        if form.is_valid():
            form.save()
            messages.success(request, 'The article was updated.')
            return redirect('article_detail', article_id=article.id)
    else:
        form = ArticleForm(instance=article)

    context = {'form': form, 'page_title': 'Edit the article'}
    return render(request, 'news/article_form.html', context)


@login_required
def article_delete(request, article_id):
    """Let a journalist or an editor delete an article."""
    article = get_object_or_404(Article, id=article_id)
    check_role(request.user, ['journalist', 'editor'])

    if request.user.is_journalist() and article.author != request.user:
        raise PermissionDenied('You can only delete your own articles.')

    if request.method == 'POST':
        article.delete()
        messages.success(request, 'The article was deleted.')
        return redirect('article_list')

    # if it is a GET request I show a page asking "are you sure?"
    context = {'object': article, 'object_type': 'article'}
    return render(request, 'news/confirm_delete.html', context)


@login_required
def my_articles(request):
    """Show a journalist the articles that they wrote."""
    check_role(request.user, ['journalist'])
    articles = request.user.articles.all()
    return render(request, 'news/my_articles.html', {'articles': articles})


# ---------------------------------------------------------------------
# The editor pages
# ---------------------------------------------------------------------

@login_required
def editor_dashboard(request):
    """Show the editor all the articles that still need approving."""
    check_role(request.user, ['editor'])

    waiting_articles = Article.objects.filter(approved=False)
    context = {'articles': waiting_articles}
    return render(request, 'news/editor_dashboard.html', context)


@login_required
def approve_article(request, article_id):
    """The editor clicks a button here to approve an article.

    When I save the article with approved=True my signal in signals.py
    wakes up and it emails the subscribers and posts the article to the
    /api/approved/ endpoint.
    """
    check_role(request.user, ['editor'])
    article = get_object_or_404(Article, id=article_id)

    if request.method == 'POST':
        if article.approved:
            messages.info(request, 'That article was already approved.')
        else:
            article.approved = True
            article.approved_by = request.user
            article.save()   # <-- this is what starts the signal
            messages.success(
                request,
                f'"{article.title}" is approved and was sent to the '
                f'subscribers.'
            )
        return redirect('editor_dashboard')

    # GET request just shows the article with an approve button
    return render(request, 'news/approve_article.html', {'article': article})


# ---------------------------------------------------------------------
# Newsletters
# ---------------------------------------------------------------------

def newsletter_list(request):
    """Show all the newsletters."""
    newsletters = Newsletter.objects.all()
    context = {'newsletters': newsletters}
    return render(request, 'news/newsletter_list.html', context)


@login_required
def newsletter_detail(request, newsletter_id):
    """Show one newsletter and the articles inside it."""
    newsletter = get_object_or_404(Newsletter, id=newsletter_id)
    context = {'newsletter': newsletter}
    return render(request, 'news/newsletter_detail.html', context)


@login_required
def newsletter_create(request):
    """Let a journalist make a new newsletter."""
    check_role(request.user, ['journalist'])

    if request.method == 'POST':
        form = NewsletterForm(request.POST)
        if form.is_valid():
            newsletter = form.save(commit=False)
            newsletter.author = request.user
            newsletter.save()
            # save_m2m is needed because I used commit=False above
            form.save_m2m()
            messages.success(request, 'The newsletter was created.')
            return redirect('newsletter_list')
    else:
        form = NewsletterForm()

    context = {'form': form, 'page_title': 'Create a newsletter'}
    return render(request, 'news/newsletter_form.html', context)


@login_required
def newsletter_edit(request, newsletter_id):
    """Let a journalist or an editor change a newsletter."""
    newsletter = get_object_or_404(Newsletter, id=newsletter_id)
    check_role(request.user, ['journalist', 'editor'])

    if request.user.is_journalist() and newsletter.author != request.user:
        raise PermissionDenied('You can only edit your own newsletters.')

    if request.method == 'POST':
        form = NewsletterForm(request.POST, instance=newsletter)
        if form.is_valid():
            form.save()
            messages.success(request, 'The newsletter was updated.')
            return redirect('newsletter_detail', newsletter_id=newsletter.id)
    else:
        form = NewsletterForm(instance=newsletter)

    context = {'form': form, 'page_title': 'Edit the newsletter'}
    return render(request, 'news/newsletter_form.html', context)


@login_required
def newsletter_delete(request, newsletter_id):
    """Let a journalist or an editor delete a newsletter."""
    newsletter = get_object_or_404(Newsletter, id=newsletter_id)
    check_role(request.user, ['journalist', 'editor'])

    if request.user.is_journalist() and newsletter.author != request.user:
        raise PermissionDenied('You can only delete your own newsletters.')

    if request.method == 'POST':
        newsletter.delete()
        messages.success(request, 'The newsletter was deleted.')
        return redirect('newsletter_list')

    context = {'object': newsletter, 'object_type': 'newsletter'}
    return render(request, 'news/confirm_delete.html', context)


# ---------------------------------------------------------------------
# Subscriptions (readers only)
# ---------------------------------------------------------------------

@login_required
def subscriptions(request):
    """Let a reader choose which publishers/journalists to follow."""
    check_role(request.user, ['reader'])

    if request.method == 'POST':
        form = SubscriptionForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your subscriptions were saved.')
            return redirect('subscriptions')
    else:
        form = SubscriptionForm(instance=request.user)

    context = {'form': form}
    return render(request, 'news/subscriptions.html', context)


@login_required
def my_feed(request):
    """Show a reader only the articles from the people they follow."""
    check_role(request.user, ['reader'])

    # get the articles from the publishers and journalists I follow
    articles = Article.objects.filter(approved=True).filter(
        publisher__in=request.user.subscriptions_publishers.all()
    ) | Article.objects.filter(approved=True).filter(
        author__in=request.user.subscriptions_journalists.all()
    )
    # distinct() removes an article that appears twice in the list
    articles = articles.distinct()

    return render(request, 'news/my_feed.html', {'articles': articles})


def publisher_list(request):
    """Show all the publishers and how many articles they have."""
    publishers = Publisher.objects.all()
    return render(
        request, 'news/publisher_list.html', {'publishers': publishers}
    )
