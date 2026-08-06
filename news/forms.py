"""
The forms that my website uses.

I use ModelForms because then django builds most of the form for me
from the model.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Article, CustomUser, Newsletter


class RegisterForm(UserCreationForm):
    """The form that a new person fills in to make an account."""

    email = forms.EmailField(
        required=True,
        help_text='We send the newsletters to this address.'
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'role', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        """Add a bootstrap-like css class to every input box."""
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            self.fields[field_name].widget.attrs['class'] = 'form-input'


class ArticleForm(forms.ModelForm):
    """The form a journalist uses to write or edit an article."""

    class Meta:
        model = Article
        fields = ['title', 'content', 'publisher']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'content': forms.Textarea(
                attrs={'class': 'form-input', 'rows': 12}
            ),
            'publisher': forms.Select(attrs={'class': 'form-input'}),
        }
        help_texts = {
            'publisher': 'Leave this empty if you are writing on your own.',
        }


class NewsletterForm(forms.ModelForm):
    """The form for making a newsletter out of some articles."""

    class Meta:
        model = Newsletter
        fields = ['title', 'description', 'publisher', 'articles']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(
                attrs={'class': 'form-input', 'rows': 6}
            ),
            'publisher': forms.Select(attrs={'class': 'form-input'}),
            'articles': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        """Only show approved articles in the list of choices."""
        super().__init__(*args, **kwargs)
        self.fields['articles'].queryset = Article.objects.filter(
            approved=True
        )


class SubscriptionForm(forms.ModelForm):
    """The form a reader uses to choose their subscriptions."""

    class Meta:
        model = CustomUser
        fields = ['subscriptions_publishers', 'subscriptions_journalists']
        widgets = {
            'subscriptions_publishers': forms.CheckboxSelectMultiple(),
            'subscriptions_journalists': forms.CheckboxSelectMultiple(),
        }
        labels = {
            'subscriptions_publishers': 'Publishers you follow',
            'subscriptions_journalists': 'Journalists you follow',
        }

    def __init__(self, *args, **kwargs):
        """Only let the reader pick users that are journalists."""
        super().__init__(*args, **kwargs)
        self.fields['subscriptions_journalists'].queryset = (
            CustomUser.objects.filter(role=CustomUser.JOURNALIST)
        )
