"""This file registers my models on the django admin site."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    ApprovedArticleLog,
    Article,
    CustomUser,
    Newsletter,
    Publisher,
)


class CustomUserAdmin(UserAdmin):
    """Admin page for my custom user so I can also see the role."""

    list_display = ('username', 'email', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser')

    # I copy the normal fieldsets and add my own extra section
    fieldsets = UserAdmin.fieldsets + (
        ('Role and subscriptions', {
            'fields': (
                'role',
                'subscriptions_publishers',
                'subscriptions_journalists',
            )
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role', {'fields': ('role',)}),
    )


class ArticleAdmin(admin.ModelAdmin):
    """Admin page for the articles."""

    list_display = ('title', 'author', 'publisher', 'approved', 'created_at')
    list_filter = ('approved', 'publisher')
    search_fields = ('title', 'content')


class NewsletterAdmin(admin.ModelAdmin):
    """Admin page for the newsletters."""

    list_display = ('title', 'author', 'created_at')
    search_fields = ('title', 'description')


class PublisherAdmin(admin.ModelAdmin):
    """Admin page for the publishers."""

    list_display = ('name', 'email')
    search_fields = ('name',)


class ApprovedArticleLogAdmin(admin.ModelAdmin):
    """Admin page so I can see what my API endpoint saved."""

    list_display = ('title', 'author_username', 'publisher_name', 'shared_at')


# register everything so it shows up in /admin/
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Publisher, PublisherAdmin)
admin.site.register(Article, ArticleAdmin)
admin.site.register(Newsletter, NewsletterAdmin)
admin.site.register(ApprovedArticleLog, ApprovedArticleLogAdmin)
