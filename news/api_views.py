"""
The views for my RESTful API.

I used the generic views from django rest framework because they already
do most of the work for a list, a detail, a create, an update and a
delete.
"""

from rest_framework import generics, status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import (
    ApprovedArticleLog,
    Article,
    Newsletter,
    Publisher,
)
from .permissions import (
    IsEditor,
    IsEditorOrAuthorOrReadOnly,
    IsJournalistOrReadOnly,
    IsReader,
)
from .serializers import (
    ApprovedArticleLogSerializer,
    ArticleSerializer,
    NewsletterSerializer,
    PublisherSerializer,
    UserSerializer,
)


class ArticleListCreateView(generics.ListCreateAPIView):
    """GET /api/articles/  -> all the approved articles.

    POST /api/articles/ -> a journalist writes a new article.
    """

    serializer_class = ArticleSerializer
    permission_classes = [IsJournalistOrReadOnly]

    def get_queryset(self):
        """Readers only see approved articles.

        A journalist also sees their own articles that are still waiting
        and an editor sees everything, because they have to work with
        them.
        """
        user = self.request.user
        if user.is_editor():
            return Article.objects.all()
        if user.is_journalist():
            # approved articles plus my own ones
            return Article.objects.filter(approved=True) | \
                Article.objects.filter(author=user)
        return Article.objects.filter(approved=True)

    def perform_create(self, serializer):
        """Set the author to the journalist that is logged in."""
        serializer.save(author=self.request.user)


class ArticleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET / PUT / DELETE for one single article."""

    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [IsEditorOrAuthorOrReadOnly]


class SubscribedArticlesView(generics.ListAPIView):
    """GET /api/articles/subscribed/

    This returns only the articles from the publishers and the
    journalists that the reader is subscribed to.
    """

    serializer_class = ArticleSerializer
    permission_classes = [IsReader]

    def get_queryset(self):
        """Filter the articles by the subscriptions of the reader."""
        reader = self.request.user

        from_publishers = Article.objects.filter(
            approved=True,
            publisher__in=reader.subscriptions_publishers.all(),
        )
        from_journalists = Article.objects.filter(
            approved=True,
            author__in=reader.subscriptions_journalists.all(),
        )

        # join the two lists together and take out the duplicates
        return (from_publishers | from_journalists).distinct()


@api_view(['POST'])
@permission_classes([IsEditor])
def approve_article_api(request, article_id):
    """POST /api/articles/<id>/approve/  (only an editor may do this).

    Saving the article with approved=True makes my signal run, which
    emails the subscribers and posts to /api/approved/.
    """
    try:
        article = Article.objects.get(id=article_id)
    except Article.DoesNotExist:
        return Response(
            {'error': 'That article does not exist.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if article.approved:
        return Response(
            {'message': 'This article was already approved.'},
            status=status.HTTP_200_OK,
        )

    article.approved = True
    article.approved_by = request.user
    article.save()

    serializer = ArticleSerializer(article)
    return Response(serializer.data, status=status.HTTP_200_OK)


class NewsletterListCreateView(generics.ListCreateAPIView):
    """GET and POST for newsletters."""

    queryset = Newsletter.objects.all()
    serializer_class = NewsletterSerializer
    permission_classes = [IsJournalistOrReadOnly]

    def perform_create(self, serializer):
        """The author is the journalist who is logged in."""
        serializer.save(author=self.request.user)


class NewsletterDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET / PUT / DELETE for one newsletter."""

    queryset = Newsletter.objects.all()
    serializer_class = NewsletterSerializer
    permission_classes = [IsEditorOrAuthorOrReadOnly]


class PublisherListView(generics.ListAPIView):
    """GET /api/publishers/ -> a list of all the publishers."""

    queryset = Publisher.objects.all()
    serializer_class = PublisherSerializer
    permission_classes = [IsAuthenticated]


@api_view(['GET'])
def my_profile(request):
    """GET /api/me/ -> shows the details of the logged in user."""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['GET', 'POST'])
@authentication_classes([])   # the signal has no token, so no auth here
@permission_classes([AllowAny])
def approved_articles_log(request):
    """/api/approved/ -- this is the endpoint my signal posts to.

    POST saves the approved article in the ApprovedArticleLog table.
    GET shows everything that has been logged so far. This is how I
    'share' an approved article outside the website while still keeping
    everything inside my own project.
    """
    if request.method == 'POST':
        serializer = ApprovedArticleLogSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,
                            status=status.HTTP_201_CREATED)
        # the data was not correct so I send back the errors
        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)

    # this part runs for a GET request
    logs = ApprovedArticleLog.objects.all()
    serializer = ApprovedArticleLogSerializer(logs, many=True)
    return Response(serializer.data)
