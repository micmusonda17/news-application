"""
My unit tests for the news application.

I test the models, the groups and permissions, the website views and
most of all the REST API, like the task asked. I use mock so that the
tests do not really try to send a POST request to the internet when an
article is approved.

Run the tests with:      python manage.py test
"""

from unittest.mock import patch

import requests

from django.contrib.auth.models import Group
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import (
    ApprovedArticleLog,
    Article,
    CustomUser,
    Newsletter,
    Publisher,
)


class BaseTestData(TestCase):
    """I put the users and articles that every test needs in here.

    The other test classes inherit from this one so that I do not have
    to write the same setUp over and over again.
    """

    def setUp(self):
        """Make the users, the publisher and two articles."""
        # My signal uses requests.post to talk to my own API. While the
        # tests run there is no server listening, so I replace
        # requests.post with a fake one (a mock). self.fake_post then
        # remembers if it was called and with what.
        self.post_patcher = patch('news.signals.requests.post')
        self.fake_post = self.post_patcher.start()
        self.addCleanup(self.post_patcher.stop)

        self.publisher = Publisher.objects.create(
            name='Daily Star',
            description='A test publisher.',
        )

        self.journalist = CustomUser.objects.create_user(
            username='john_journalist',
            email='john@example.com',
            password='TestPass123!',
            role=CustomUser.JOURNALIST,
        )
        self.other_journalist = CustomUser.objects.create_user(
            username='sara_journalist',
            email='sara@example.com',
            password='TestPass123!',
            role=CustomUser.JOURNALIST,
        )
        self.editor = CustomUser.objects.create_user(
            username='emma_editor',
            email='emma@example.com',
            password='TestPass123!',
            role=CustomUser.EDITOR,
        )
        self.reader = CustomUser.objects.create_user(
            username='rick_reader',
            email='rick@example.com',
            password='TestPass123!',
            role=CustomUser.READER,
        )

        # the publisher employs the first journalist and the editor
        self.publisher.journalists.add(self.journalist)
        self.publisher.editors.add(self.editor)

        # the reader follows the publisher only (not sara)
        self.reader.subscriptions_publishers.add(self.publisher)

        # one approved article from the publisher
        self.approved_article = Article.objects.create(
            title='Approved publisher article',
            content='This one is already approved.',
            author=self.journalist,
            publisher=self.publisher,
            approved=True,
        )
        # one article that is still waiting for an editor
        self.waiting_article = Article.objects.create(
            title='Waiting article',
            content='This one still needs approving.',
            author=self.journalist,
            publisher=self.publisher,
            approved=False,
        )
        # an independent article by the journalist nobody follows
        self.independent_article = Article.objects.create(
            title='Independent article',
            content='Written without a publisher.',
            author=self.other_journalist,
            approved=True,
        )


class ModelTests(BaseTestData):
    """Tests for the models and for the groups and permissions."""

    def test_user_is_put_in_the_correct_group(self):
        """When a user is saved they must land in the right group."""
        self.assertTrue(
            self.journalist.groups.filter(name='Journalist').exists()
        )
        self.assertTrue(self.editor.groups.filter(name='Editor').exists())
        self.assertTrue(self.reader.groups.filter(name='Reader').exists())

    def test_groups_have_the_correct_permissions(self):
        """Check the permissions that the task asked for."""
        reader_group = Group.objects.get(name='Reader')
        editor_group = Group.objects.get(name='Editor')
        journalist_group = Group.objects.get(name='Journalist')

        reader_permissions = [
            p.codename for p in reader_group.permissions.all()
        ]
        editor_permissions = [
            p.codename for p in editor_group.permissions.all()
        ]
        journalist_permissions = [
            p.codename for p in journalist_group.permissions.all()
        ]

        # a reader may only view
        self.assertIn('view_article', reader_permissions)
        self.assertNotIn('add_article', reader_permissions)
        self.assertNotIn('delete_article', reader_permissions)

        # an editor may view, change and delete but not add
        self.assertIn('change_article', editor_permissions)
        self.assertIn('delete_article', editor_permissions)
        self.assertNotIn('add_article', editor_permissions)

        # a journalist may do everything
        self.assertIn('add_article', journalist_permissions)
        self.assertIn('change_newsletter', journalist_permissions)

    def test_journalist_has_no_reader_fields(self):
        """A journalist must get None for the reader fields."""
        self.assertIsNone(self.journalist.get_reader_fields())
        self.assertIsNotNone(self.journalist.get_journalist_fields())

    def test_reader_has_no_journalist_fields(self):
        """A reader must get None for the journalist fields."""
        self.assertIsNone(self.reader.get_journalist_fields())
        self.assertIsNotNone(self.reader.get_reader_fields())

    def test_subscriptions_are_cleared_for_a_journalist(self):
        """If somebody becomes a journalist their subscriptions go away."""
        self.reader.subscriptions_journalists.add(self.journalist)
        self.assertEqual(self.reader.subscriptions_journalists.count(), 1)

        # now change the reader into a journalist
        self.reader.role = CustomUser.JOURNALIST
        self.reader.save()

        self.assertEqual(self.reader.subscriptions_journalists.count(), 0)
        self.assertEqual(self.reader.subscriptions_publishers.count(), 0)

    def test_string_methods(self):
        """The __str__ methods must show something readable."""
        self.assertEqual(str(self.publisher), 'Daily Star')
        self.assertEqual(str(self.approved_article),
                         'Approved publisher article')
        self.assertIn('john_journalist', str(self.journalist))

    def test_independent_article(self):
        """An article with no publisher is an independent article."""
        self.assertTrue(self.independent_article.is_independent())
        self.assertFalse(self.approved_article.is_independent())


class SignalTests(BaseTestData):
    """Tests for what happens when an editor approves an article."""

    def test_email_is_sent_to_subscribers(self):
        """The subscribers of the publisher must get an email."""
        mail.outbox = []   # empty the test inbox first

        self.waiting_article.approved = True
        self.waiting_article.save()

        # one email must have been sent to the reader
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Waiting article', mail.outbox[0].subject)
        self.assertIn('rick@example.com', mail.outbox[0].to)

    def test_post_request_is_sent_to_my_api(self):
        """The signal must POST the article to /api/approved/."""
        self.fake_post.reset_mock()

        self.waiting_article.approved = True
        self.waiting_article.save()

        # requests.post must have been called one time
        self.assertTrue(self.fake_post.called)
        self.assertEqual(self.fake_post.call_count, 1)

        # check the url and the data that were sent
        called_url = self.fake_post.call_args[0][0]
        called_data = self.fake_post.call_args[1]['json']
        self.assertIn('/api/approved/', called_url)
        self.assertEqual(called_data['title'], 'Waiting article')

    def test_nothing_happens_when_article_is_saved_again(self):
        """An already approved article must not send the email twice."""
        self.waiting_article.approved = True
        self.waiting_article.save()
        mail.outbox = []
        self.fake_post.reset_mock()

        # save it one more time without changing the approved field
        self.waiting_article.title = 'A new title'
        self.waiting_article.save()

        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(self.fake_post.called)

    def test_no_email_when_there_are_no_subscribers(self):
        """If nobody is subscribed then no email must be sent."""
        mail.outbox = []
        lonely_article = Article.objects.create(
            title='Nobody follows me',
            content='No subscribers here.',
            author=self.other_journalist,
        )
        lonely_article.approved = True
        lonely_article.save()

        self.assertEqual(len(mail.outbox), 0)

    def test_the_website_does_not_crash_if_the_api_is_down(self):
        """Approving must still work even if the POST request fails."""
        # make the fake requests.post throw the error you would get if
        # the server was not running
        self.fake_post.side_effect = requests.exceptions.ConnectionError(
            'no server'
        )

        # this must not raise an error
        self.waiting_article.approved = True
        self.waiting_article.save()

        self.waiting_article.refresh_from_db()
        self.assertTrue(self.waiting_article.approved)


class WebsiteViewTests(BaseTestData):
    """Tests for the normal pages of the website."""

    def test_home_page_only_shows_approved_articles(self):
        """The waiting article must not be on the home page."""
        response = self.client.get(reverse('article_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Approved publisher article')
        self.assertNotContains(response, 'Waiting article')

    def test_reader_can_not_open_the_editor_dashboard(self):
        """A reader must get a 403 Forbidden on the editor page."""
        self.client.login(username='rick_reader', password='TestPass123!')
        response = self.client.get(reverse('editor_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_editor_can_open_the_editor_dashboard(self):
        """An editor must be able to see the articles waiting."""
        self.client.login(username='emma_editor', password='TestPass123!')
        response = self.client.get(reverse('editor_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Waiting article')

    def test_reader_can_not_write_an_article(self):
        """A reader is not allowed on the write article page."""
        self.client.login(username='rick_reader', password='TestPass123!')
        response = self.client.get(reverse('article_create'))
        self.assertEqual(response.status_code, 403)

    def test_journalist_can_write_an_article(self):
        """A journalist can post the form and the article is saved."""
        self.client.login(username='john_journalist',
                          password='TestPass123!')
        response = self.client.post(reverse('article_create'), {
            'title': 'My brand new article',
            'content': 'Some content for the article.',
            'publisher': self.publisher.id,
        })
        self.assertEqual(response.status_code, 302)   # it redirected
        self.assertTrue(
            Article.objects.filter(title='My brand new article').exists()
        )
        # a new article must not be approved yet
        new_article = Article.objects.get(title='My brand new article')
        self.assertFalse(new_article.approved)

    def test_editor_can_approve_an_article_from_the_website(self):
        """Clicking approve must set approved to True."""
        self.client.login(username='emma_editor', password='TestPass123!')
        url = reverse('approve_article', args=[self.waiting_article.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.waiting_article.refresh_from_db()
        self.assertTrue(self.waiting_article.approved)
        self.assertEqual(self.waiting_article.approved_by, self.editor)

    def test_a_journalist_can_not_edit_somebody_elses_article(self):
        """Sara must not be able to edit the article John wrote."""
        self.client.login(username='sara_journalist',
                          password='TestPass123!')
        url = reverse('article_edit', args=[self.approved_article.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_you_must_log_in_to_see_your_feed(self):
        """A visitor that is not logged in gets sent to the login page."""
        response = self.client.get(reverse('my_feed'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_reader_feed_only_shows_subscribed_articles(self):
        """The feed must only have articles from the publisher I follow."""
        self.client.login(username='rick_reader', password='TestPass123!')
        response = self.client.get(reverse('my_feed'))
        self.assertContains(response, 'Approved publisher article')
        self.assertNotContains(response, 'Independent article')

    def test_register_page_makes_a_new_user(self):
        """Somebody can make an account and pick a role."""
        response = self.client.post(reverse('register'), {
            'username': 'new_person',
            'email': 'new@example.com',
            'role': 'reader',
            'password1': 'SuperSecret123!',
            'password2': 'SuperSecret123!',
        })
        self.assertEqual(response.status_code, 302)
        new_user = CustomUser.objects.get(username='new_person')
        self.assertEqual(new_user.role, 'reader')
        self.assertTrue(new_user.groups.filter(name='Reader').exists())


class ApiTests(APITestCase, BaseTestData):
    """Tests for the REST API.

    APITestCase gives me self.client with the extra API helpers like
    credentials() for the token.
    """

    def login_with_token(self, user):
        """Small helper that makes a token and puts it in the header."""
        token, created = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        return token

    # ----------------------- authentication -----------------------

    def test_you_can_get_a_token_with_the_correct_password(self):
        """POST /api/token/ must give back a token."""
        response = self.client.post(reverse('api_token'), {
            'username': 'rick_reader',
            'password': 'TestPass123!',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_you_can_not_get_a_token_with_the_wrong_password(self):
        """A wrong password must fail with 400."""
        response = self.client.post(reverse('api_token'), {
            'username': 'rick_reader',
            'password': 'ThisIsWrong',
        })
        self.assertEqual(response.status_code,
                         status.HTTP_400_BAD_REQUEST)

    def test_articles_need_a_token(self):
        """Without a token the API must say 401 Unauthorized."""
        response = self.client.get(reverse('api_article_list'))
        self.assertEqual(response.status_code,
                         status.HTTP_401_UNAUTHORIZED)

    # ----------------------- reading articles -----------------------

    def test_reader_only_sees_approved_articles(self):
        """GET /api/articles/ must not show the waiting article."""
        self.login_with_token(self.reader)
        response = self.client.get(reverse('api_article_list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [article['title'] for article in response.data]
        self.assertIn('Approved publisher article', titles)
        self.assertNotIn('Waiting article', titles)

    def test_editor_sees_every_article(self):
        """An editor also sees the articles that are still waiting."""
        self.login_with_token(self.editor)
        response = self.client.get(reverse('api_article_list'))

        titles = [article['title'] for article in response.data]
        self.assertIn('Waiting article', titles)

    def test_get_one_article(self):
        """GET /api/articles/<id>/ must return that one article."""
        self.login_with_token(self.reader)
        url = reverse('api_article_detail',
                      args=[self.approved_article.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'],
                         'Approved publisher article')
        self.assertEqual(response.data['author_name'], 'john_journalist')

    def test_get_an_article_that_does_not_exist(self):
        """Asking for article 999 must give a 404."""
        self.login_with_token(self.reader)
        response = self.client.get(
            reverse('api_article_detail', args=[999])
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ----------------------- subscribed articles -----------------------

    def test_subscribed_endpoint_only_returns_my_subscriptions(self):
        """The reader follows the publisher, not sara."""
        self.login_with_token(self.reader)
        response = self.client.get(reverse('api_subscribed_articles'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [article['title'] for article in response.data]
        self.assertIn('Approved publisher article', titles)
        self.assertNotIn('Independent article', titles)

    def test_subscribed_endpoint_after_following_a_journalist(self):
        """After following sara her article must show up."""
        self.reader.subscriptions_journalists.add(self.other_journalist)
        self.login_with_token(self.reader)
        response = self.client.get(reverse('api_subscribed_articles'))

        titles = [article['title'] for article in response.data]
        self.assertIn('Independent article', titles)

    def test_journalist_can_not_use_the_subscribed_endpoint(self):
        """Only readers have subscriptions, so this must be 403."""
        self.login_with_token(self.journalist)
        response = self.client.get(reverse('api_subscribed_articles'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ----------------------- creating articles -----------------------

    def test_journalist_can_create_an_article(self):
        """POST /api/articles/ works for a journalist."""
        self.login_with_token(self.journalist)
        response = self.client.post(reverse('api_article_list'), {
            'title': 'An article from the API',
            'content': 'I made this with a POST request.',
            'publisher': self.publisher.id,
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['author_name'], 'john_journalist')
        # a new article must not be approved automatically
        self.assertFalse(response.data['approved'])

    def test_reader_can_not_create_an_article(self):
        """POST /api/articles/ must be 403 for a reader."""
        self.login_with_token(self.reader)
        response = self.client.post(reverse('api_article_list'), {
            'title': 'A reader should not do this',
            'content': 'This must fail.',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_creating_an_article_without_a_title_fails(self):
        """An empty title must give a 400 with an error message."""
        self.login_with_token(self.journalist)
        response = self.client.post(reverse('api_article_list'), {
            'title': '',
            'content': 'No title here.',
        })
        self.assertEqual(response.status_code,
                         status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)

    # ----------------------- updating and deleting -----------------------

    def test_journalist_can_update_their_own_article(self):
        """PUT /api/articles/<id>/ works on my own article."""
        self.login_with_token(self.journalist)
        url = reverse('api_article_detail', args=[self.approved_article.id])
        response = self.client.put(url, {
            'title': 'The title I changed',
            'content': 'New content.',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.approved_article.refresh_from_db()
        self.assertEqual(self.approved_article.title,
                         'The title I changed')

    def test_journalist_can_not_update_somebody_elses_article(self):
        """Sara must get 403 when she tries to change John's article."""
        self.login_with_token(self.other_journalist)
        url = reverse('api_article_detail', args=[self.approved_article.id])
        response = self.client.put(url, {
            'title': 'Sara was here',
            'content': 'This must not work.',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_editor_can_delete_an_article(self):
        """DELETE /api/articles/<id>/ works for an editor."""
        self.login_with_token(self.editor)
        url = reverse('api_article_detail', args=[self.approved_article.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code,
                         status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Article.objects.filter(id=self.approved_article.id).exists()
        )

    def test_reader_can_not_delete_an_article(self):
        """A reader must get 403 when trying to delete."""
        self.login_with_token(self.reader)
        url = reverse('api_article_detail', args=[self.approved_article.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ----------------------- approving through the API -----------------

    def test_editor_can_approve_through_the_api(self):
        """POST /api/articles/<id>/approve/ works for an editor."""
        self.fake_post.reset_mock()
        self.login_with_token(self.editor)
        url = reverse('api_approve_article',
                      args=[self.waiting_article.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.waiting_article.refresh_from_db()
        self.assertTrue(self.waiting_article.approved)
        # the signal must have posted to my API as well
        self.assertTrue(self.fake_post.called)

    def test_journalist_can_not_approve_an_article(self):
        """Only an editor may approve, so this must be 403."""
        self.login_with_token(self.journalist)
        url = reverse('api_approve_article',
                      args=[self.waiting_article.id])
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.waiting_article.refresh_from_db()
        self.assertFalse(self.waiting_article.approved)

    # ----------------------- newsletters -----------------------

    def test_reader_can_see_the_newsletters(self):
        """GET /api/newsletters/ must work for a reader."""
        newsletter = Newsletter.objects.create(
            title='The weekly news',
            description='All the news of the week.',
            author=self.journalist,
        )
        newsletter.articles.add(self.approved_article)

        self.login_with_token(self.reader)
        response = self.client.get(reverse('api_newsletter_list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'The weekly news')

    def test_journalist_can_create_a_newsletter(self):
        """POST /api/newsletters/ works for a journalist."""
        self.login_with_token(self.journalist)
        response = self.client.post(reverse('api_newsletter_list'), {
            'title': 'My newsletter',
            'description': 'Made with the API.',
            'articles': [self.approved_article.id],
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['author_name'], 'john_journalist')

    def test_reader_can_not_create_a_newsletter(self):
        """A reader must get 403 when posting a newsletter."""
        self.login_with_token(self.reader)
        response = self.client.post(reverse('api_newsletter_list'), {
            'title': 'Not allowed',
            'description': 'This must fail.',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_editor_can_delete_a_newsletter(self):
        """An editor may delete any newsletter."""
        newsletter = Newsletter.objects.create(
            title='Delete me',
            description='This newsletter will be deleted.',
            author=self.journalist,
        )
        self.login_with_token(self.editor)
        url = reverse('api_newsletter_detail', args=[newsletter.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code,
                         status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Newsletter.objects.filter(id=newsletter.id).exists()
        )

    # ----------------------- the approved log endpoint -----------------

    def test_the_approved_endpoint_saves_the_article(self):
        """A POST to /api/approved/ must save a row in the log table."""
        response = self.client.post(reverse('api_approved'), {
            'article': self.approved_article.id,
            'title': self.approved_article.title,
            'author_username': 'john_journalist',
            'publisher_name': 'Daily Star',
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ApprovedArticleLog.objects.count(), 1)
        self.assertEqual(
            ApprovedArticleLog.objects.first().title,
            'Approved publisher article'
        )

    def test_the_approved_endpoint_says_no_to_bad_data(self):
        """Posting rubbish must give a 400 error."""
        response = self.client.post(reverse('api_approved'), {
            'article': 999,      # this article does not exist
            'title': 'Nothing',
            'author_username': 'nobody',
        })
        self.assertEqual(response.status_code,
                         status.HTTP_400_BAD_REQUEST)

    # ----------------------- the profile endpoint -----------------------

    def test_me_endpoint_shows_my_details(self):
        """GET /api/me/ must show the user that owns the token."""
        self.login_with_token(self.reader)
        response = self.client.get(reverse('api_my_profile'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'rick_reader')
        self.assertEqual(response.data['role'], 'reader')
