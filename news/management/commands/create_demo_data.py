"""
A command that fills the database with some demo data.

I made this so that I do not have to type everything in by hand every
time I want to test my website.

Run it like this:      python manage.py create_demo_data
"""

from django.core.management.base import BaseCommand

from news.models import Article, CustomUser, Newsletter, Publisher


class Command(BaseCommand):
    """Creates a publisher, three users and a few articles."""

    help = 'Adds some demo data so the website is not empty.'

    def handle(self, *args, **options):
        """This method runs when I type the command in the terminal."""
        # 1. the publisher
        publisher, created = Publisher.objects.get_or_create(
            name='The Daily Star',
            defaults={
                'description': 'A demo publisher for my capstone project.',
                'email': 'info@dailystar.example.com',
            },
        )

        # 2. the users (password for all of them is Password123!)
        journalist = self.make_user('journalist1', 'journalist')
        editor = self.make_user('editor1', 'editor')
        reader = self.make_user('reader1', 'reader')

        publisher.journalists.add(journalist)
        publisher.editors.add(editor)

        # the reader follows the publisher and the journalist
        reader.subscriptions_publishers.add(publisher)
        reader.subscriptions_journalists.add(journalist)

        # 3. some articles
        article1, created = Article.objects.get_or_create(
            title='The city opens a new library',
            defaults={
                'content': 'The new library opened its doors today. It '
                           'has more than ten thousand books inside.',
                'author': journalist,
                'publisher': publisher,
                'approved': True,
            },
        )
        Article.objects.get_or_create(
            title='Local team wins the cup',
            defaults={
                'content': 'The local football team won the cup after a '
                           'very exciting final match.',
                'author': journalist,
                'publisher': publisher,
                'approved': False,
            },
        )

        # 4. one newsletter
        newsletter, created = Newsletter.objects.get_or_create(
            title='This week in our city',
            defaults={
                'description': 'A short newsletter with the best stories '
                               'of the week.',
                'author': journalist,
                'publisher': publisher,
            },
        )
        newsletter.articles.add(article1)

        self.stdout.write(self.style.SUCCESS(
            'Demo data was created.\n'
            'Users: journalist1, editor1, reader1\n'
            'The password for all of them is: Password123!'
        ))

    def make_user(self, username, role):
        """Make one user with the given role if it does not exist yet.

        If the user is already there I still make sure that the role is
        the correct one, because otherwise a user that was made earlier
        (for example with createsuperuser) would keep the wrong role and
        then the wrong menu shows up on the website.
        """
        user = CustomUser.objects.filter(username=username).first()
        if user:
            if user.role != role:
                user.role = role
                user.save()   # saving also fixes the group
            return user

        user = CustomUser.objects.create_user(
            username=username,
            email=f'{username}@example.com',
            password='Password123!',
            role=role,
        )
        return user
