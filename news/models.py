"""
The models for my news application.

There are four models in here:
    CustomUser  - my own user model with a role (reader/editor/journalist)
    Publisher   - a newspaper/company that has editors and journalists
    Article     - a news article written by a journalist
    Newsletter  - a collection of articles put together by a journalist
"""

from django.contrib.auth.models import AbstractUser, Group
from django.db import models


class CustomUser(AbstractUser):
    """My own user model.

    I use AbstractUser so I still get the username, password and email
    fields from django, but I can add my own extra fields like the role
    and the subscriptions.
    """

    # These are the three roles that the task asked for.
    READER = 'reader'
    EDITOR = 'editor'
    JOURNALIST = 'journalist'

    ROLE_CHOICES = [
        (READER, 'Reader'),
        (EDITOR, 'Editor'),
        (JOURNALIST, 'Journalist'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=READER,
        help_text='The role decides which group the user is put into.'
    )

    # --- these two fields are only used by readers ---
    subscriptions_publishers = models.ManyToManyField(
        'Publisher',
        blank=True,
        related_name='subscribers',
        help_text='Publishers that this reader is subscribed to.'
    )
    subscriptions_journalists = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,  # if I follow you it does not mean you follow me
        related_name='followers',
        help_text='Journalists that this reader is subscribed to.'
    )

    # NOTE: the articles and newsletters that a journalist writes are not
    # written here as fields. They come from the ForeignKey in the Article
    # and Newsletter models (this is called a reverse relation). So I can
    # do journalist.articles.all() and journalist.newsletters.all().

    class Meta:
        """Nicer singular and plural names for the admin site."""

        verbose_name = 'user'
        verbose_name_plural = 'users'

    def __str__(self):
        """Show the username and the role in the admin site."""
        return f'{self.username} ({self.get_role_display()})'

    def is_reader(self):
        """Return True if this user is a reader."""
        return self.role == self.READER

    def is_editor(self):
        """Return True if this user is an editor."""
        return self.role == self.EDITOR

    def is_journalist(self):
        """Return True if this user is a journalist."""
        return self.role == self.JOURNALIST

    def save(self, *args, **kwargs):
        """Save the user and then put them in the correct group.

        The task also says that if the user is a journalist then the
        reader fields must be 'None', and the other way around. A
        ManyToManyField can not really be None, so the closest thing is
        to make it empty (clear it) for users who are not readers.
        """
        # first save the user normally so that it gets an id
        super().save(*args, **kwargs)

        # put the user in the group that matches their role
        group_name = self.role.capitalize()  # 'reader' -> 'Reader'
        group, created = Group.objects.get_or_create(name=group_name)
        self.groups.clear()      # remove any old group first
        self.groups.add(group)

        # a journalist or an editor is not allowed to have subscriptions
        if not self.is_reader():
            self.subscriptions_publishers.clear()
            self.subscriptions_journalists.clear()

    def get_reader_fields(self):
        """Return the subscriptions of a reader, or None for other roles.

        This is a small helper so that the templates and the tests can
        easily check the rule from the task: readers have subscriptions
        and everybody else gets None.
        """
        if self.is_reader():
            return {
                'publishers': self.subscriptions_publishers.all(),
                'journalists': self.subscriptions_journalists.all(),
            }
        return None

    def get_journalist_fields(self):
        """Return the articles/newsletters of a journalist, else None."""
        if self.is_journalist():
            return {
                'articles': self.articles.all(),
                'newsletters': self.newsletters.all(),
            }
        return None


class Publisher(models.Model):
    """A publisher is like a newspaper company.

    A publisher can have many editors and many journalists working for it.
    """

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    email = models.EmailField(blank=True)

    editors = models.ManyToManyField(
        CustomUser,
        blank=True,
        related_name='publishers_as_editor',
        limit_choices_to={'role': CustomUser.EDITOR},
    )
    journalists = models.ManyToManyField(
        CustomUser,
        blank=True,
        related_name='publishers_as_journalist',
        limit_choices_to={'role': CustomUser.JOURNALIST},
    )

    class Meta:
        """List publishers alphabetically by name."""

        ordering = ['name']

    def __str__(self):
        """Show the name of the publisher."""
        return self.name


class Article(models.Model):
    """A news article.

    An article is written by a journalist. It can belong to a publisher,
    or the publisher can be left empty which means the journalist wrote
    it independently (on their own).
    """

    title = models.CharField(max_length=250)
    content = models.TextField()
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='articles',
        limit_choices_to={'role': CustomUser.JOURNALIST},
    )
    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,      # blank means it is an independent article
        related_name='articles',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # an editor has to tick this box before readers can see the article
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_articles',
        limit_choices_to={'role': CustomUser.EDITOR},
    )

    class Meta:
        """Show the newest articles first."""

        ordering = ['-created_at']   # newest article first

    def __str__(self):
        """Show the title of the article."""
        return self.title

    def is_independent(self):
        """Return True if the article does not belong to a publisher."""
        return self.publisher is None


class Newsletter(models.Model):
    """A newsletter is a group of articles put together by a journalist."""

    title = models.CharField(max_length=250)
    description = models.TextField()
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='newsletters',
    )
    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='newsletters',
    )
    articles = models.ManyToManyField(
        Article,
        blank=True,
        related_name='newsletters',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Show the newest newsletters first."""

        ordering = ['-created_at']

    def __str__(self):
        """Show the title of the newsletter."""
        return self.title


class ApprovedArticleLog(models.Model):
    """This is where the /api/approved/ endpoint saves the articles.

    When an editor approves an article a signal sends a POST request to
    my own API endpoint /api/approved/. That endpoint saves a row in this
    table. This is how I 'share the article externally' but still keep
    everything inside my own project like the task asked.
    """

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name='approved_logs',
    )
    title = models.CharField(max_length=250)
    author_username = models.CharField(max_length=150)
    publisher_name = models.CharField(max_length=200, blank=True)
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Show the most recently shared articles first."""

        ordering = ['-shared_at']

    def __str__(self):
        """Show which article was logged."""
        return f'Approved: {self.title}'
