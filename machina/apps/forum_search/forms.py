"""
    Forum search forms
    ==================

    This module defines forms provided by the ``forum_search`` application.

"""

from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from machina.conf import settings
from machina.core.db.models import get_model
from machina.core.loading import get_class


if settings.SEARCH_ENGINE == 'postgres':
    from django.contrib.postgres.search import SearchQuery, SearchRank
    from django.db.models import F

Forum = get_model('forum', 'Forum')

Post = get_model('forum_conversation', 'Post')

PermissionHandler = get_class('forum_permission.handler', 'PermissionHandler')


class PostgresSearchForm(forms.Form):
    q = forms.CharField(required=False, label=_('Search'),
                        widget=forms.TextInput(attrs={'type': 'search'}))

    search_topics = forms.BooleanField(label=_('Search only in topic subjects'), required=False)

    search_poster_name = forms.CharField(
        label=_('Search for poster'),
        help_text=_('Enter a user name to limit the search to a specific user.'),
        max_length=255, required=False,
    )

    search_forums = forms.MultipleChoiceField(
        label=_('Search in specific forums'),
        help_text=_('Select the forums you wish to search in.'),
        required=False,
    )

    def __init__(self, request):
        user = request.user

        super().__init__(request.GET)

        # Update some fields
        self.fields['q'].label = _('Search for keywords')
        self.fields['q'].widget.attrs['placeholder'] = _('Keywords or phrase')
        self.fields['search_poster_name'].widget.attrs['placeholder'] = _('Poster name')

        self.allowed_forums = PermissionHandler().get_readable_forums(Forum.objects.all(), user)
        if self.allowed_forums:
            self.fields['search_forums'].choices = [
                (f.id, '{} {}'.format('-' * f.margin_level, f.name)) for f in self.allowed_forums
            ]
        else:
            # The user cannot view any single forum, the 'search_forums' field can be deleted
            del self.fields['search_forums']

    def no_query_found(self):
        return None

    def search(self):

        if not self.is_valid():
            return self.no_query_found()

        if not self.cleaned_data.get('q'):
            return self.no_query_found()

        if settings.SEARCH_ENGINE == 'postgres':
            query = SearchQuery(self.cleaned_data['q'])

            if self.cleaned_data['search_topics']:
                sqs = Post.objects.annotate(rank=SearchRank(F('search_vector_subject'), query))
                sqs = sqs.filter(search_vector_subject=query)
            else:
                sqs = Post.objects.annotate(rank=SearchRank(F('search_vector_all'), query))
                sqs = sqs.filter(search_vector_all=query)
            sqs = sqs.order_by('-rank')

        else:
            if self.cleaned_data['search_topics']:
                sqs = Post.objects.filter(subject__icontains=self.cleaned_data['q'])
            else:
                sqs = Post.objects.filter(
                    Q(subject__icontains=self.cleaned_data['q']) |
                    Q(content__icontains=self.cleaned_data['q'])
                )

        if self.cleaned_data['search_poster_name']:
            sqs = sqs.filter(
                Q(poster__username__icontains=self.cleaned_data['search_poster_name']) |
                Q(username=self.cleaned_data['search_poster_name'])
            )

        if 'search_forums' in self.cleaned_data and self.cleaned_data['search_forums']:
            sqs = sqs.filter(topic__forum__in=self.cleaned_data['search_forums'])
        else:
            forum_ids = self.allowed_forums.values_list('id', flat=True)
            sqs = sqs.filter(topic__forum__in=forum_ids) if forum_ids else None

        return sqs[:20000] if sqs else None  # without this split we can get 502 on some requests
