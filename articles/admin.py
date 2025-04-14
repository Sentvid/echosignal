import logging
from datetime import date, datetime, timedelta
from typing import Dict, Optional, Tuple, Type, Union

# Third-party observability libraries
from prometheus_client import Counter

# Django core imports
from django.contrib import admin, messages
from django.contrib.admin.options import ModelAdmin
from django.db.models import Count, Model, QuerySet
from django.forms import Form, forms
from django.http import HttpRequest
from django.shortcuts import render, redirect
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _ # For potential future i18n

# Local app imports
from .models import Article, Category, Tag
from articles.parsers.parser_manager import ParserManager

# --- Constants ---
STATUS_PUBLISHED: str = 'PUBLISHED' # Use constant for status comparison
ACTION_CREATE: str = 'create'
ACTION_UPDATE: str = 'update'

# --- Logger Setup ---
# Standard practice: Get a logger instance scoped to this module
logger = logging.getLogger(__name__)

# --- Prometheus Metrics Definitions ---
# Define metrics ONCE at the module level. Ensure names are descriptive and prefixed.
# Consider a dedicated metrics registry module in larger projects.

MODEL_SAVED_TOTAL = Counter(
    'echosignal_admin_model_saved_total',
    'Total number of models saved via Django admin.',
    ['model_name', 'action'] # Labels: model name, action type (create/update)
)

ARTICLES_PUBLISHED_TOTAL = Counter(
    'echosignal_admin_articles_published_total',
    'Total number of articles published via Django admin save or action.'
)

ADMIN_ACTIONS_EXECUTED_TOTAL = Counter(
    'echosignal_admin_actions_executed_total',
    'Total number of custom admin actions executed.',
    ['action_name'] # Label: name of the admin action executed
)


# --- Type Aliases ---
# Define a type alias for models managed by the count mixin
TaxonomyModel = Union[Category, Tag]

# --- Mixins for Reusable Admin Logic ---

class AdminObservabilityMixin:
    """
    Mixin providing standardized logging and metrics for model saving in the admin.

    Inheriting classes should call super().save_model() to trigger this logic.
    """

    def save_model(self, request: HttpRequest, obj: Model, form: Form, change: bool) -> None:
        """Logs save events and increments the model save counter."""
        action: str = ACTION_UPDATE if change else ACTION_CREATE
        model_name: str = obj._meta.model_name
        user_display: str = request.user.username if request.user.is_authenticated else 'AnonymousUser'

        # Log the attempt before saving
        logger.info(
            "Admin save attempt: User '%s' is trying to %s %s instance [PK: %s].",
            user_display, action, model_name, obj.pk or 'New',
            extra={'user': user_display, 'object_pk': obj.pk, 'action': action, 'model_name': model_name}
        )

        super().save_model(request, obj, form, change) # Call the next save_model in MRO

        # Log successful save (PK is guaranteed to exist now)
        logger.info(
            "Admin save success: User '%s' successfully %s %s instance [PK: %s].",
            user_display, action, model_name, obj.pk,
            extra={'user': user_display, 'object_pk': obj.pk, 'action': action, 'model_name': model_name}
        )
        # Increment Prometheus counter for model save operations
        MODEL_SAVED_TOTAL.labels(model_name=model_name, action=action).inc()


class ArticleCountAdminMixin:
    """
    Mixin for ModelAdmin classes (Category, Tag) needing an efficient article count display.

    Assumes the related name from the Article model is 'articles' (default for ManyToMany).
    Dynamically determines the annotation field name based on the related name.
    """
    # This mixin focuses on display/query optimization, not observability directly.

    def get_queryset(self, request: HttpRequest) -> QuerySet[TaxonomyModel]:
        """Annotates the queryset with the count of related articles."""
        queryset: QuerySet[TaxonomyModel] = super().get_queryset(request)
        # Dynamically get the related field name to be robust
        related_name: str
        model_class: Type[Model] = self.model # Get the model class (Category or Tag)
        if model_class == Category:
            related_name = Article.categories.field.related_name or 'articles'
        elif model_class == Tag:
            related_name = Article.tags.field.related_name or 'articles'
        else:
            # Should not happen with correct usage, but provides a fallback
            logger.warning("ArticleCountAdminMixin used on unexpected model: %s", model_class.__name__)
            related_name = 'articles' # Fallback, might fail if relation doesn't exist

        annotation_field: str = f'_{related_name}_count'
        annotation: Dict[str, Count] = {annotation_field: Count(related_name)}
        return queryset.annotate(**annotation)

    @admin.display(description=_('Articles')) # Use gettext_lazy for potential translation
    def article_count(self, obj: TaxonomyModel) -> int:
        """
        Returns the pre-calculated article count from the annotated queryset.
        Sets ordering dynamically based on the annotation field.
        """
        related_name: str
        if isinstance(obj, Category):
            related_name = Article.categories.field.related_name or 'articles'
        elif isinstance(obj, Tag):
            related_name = Article.tags.field.related_name or 'articles'
        else:
            return 0 # Should not be reached with correct model types

        count_attr: str = f'_{related_name}_count'
        # Set ordering on the admin instance for the list view
        self.ordering = (count_attr,)
        # Return the count, defaulting to 0 if the annotation attribute isn't present
        return getattr(obj, count_attr, 0)


# --- ModelAdmin Configurations ---

@admin.register(Category)
class CategoryAdmin(AdminObservabilityMixin, ArticleCountAdminMixin, admin.ModelAdmin):
    """Admin configuration for the Category model."""
    list_display: Tuple[str, ...] = ('name', 'slug', 'article_count')
    search_fields: Tuple[str, ...] = ('name',)
    prepopulated_fields: Dict[str, Tuple[str, ...]] = {'slug': ('name',)}
    # ordering is set dynamically by ArticleCountAdminMixin


@admin.register(Tag)
class TagAdmin(AdminObservabilityMixin, ArticleCountAdminMixin, admin.ModelAdmin):
    """Admin configuration for the Tag model."""
    list_display: Tuple[str, ...] = ('name', 'slug', 'article_count')
    search_fields: Tuple[str, ...] = ('name',)
    prepopulated_fields: Dict[str, Tuple[str, ...]] = {'slug': ('name',)}
    # ordering is set dynamically by ArticleCountAdminMixin


@admin.register(Article)
class ArticleAdmin(AdminObservabilityMixin, admin.ModelAdmin):
    """
    Admin configuration for the Article model with observability and workflow logic.
    """
    list_display: Tuple[str, ...] = (
        'title',
        'status',
        'display_publication_date',
        'display_published_at',
        'source_name',
        'was_added_recently',
        'added_by_user', # Display who added it
    )
    list_filter: Tuple[str, ...] = (
        'status',
        'categories',
        'tags',
        'publication_date',
        'published_at',
        'added_by', # Allow filtering by user who added
    )
    search_fields: Tuple[str, ...] = (
        'title',
        'summary',
        'full_text_content',
        'authors',
        'source_name',
        'original_url',
        'added_by__username', # Allow searching by username
        'published_by__username',
    )
    # Fields not directly editable in the form
    readonly_fields: Tuple[str, ...] = (
        'created_at',
        'updated_at',
        'published_at',
        'published_by', # Set automatically
    )
    # Use filter_horizontal for better UX with ManyToMany fields
    filter_horizontal: Tuple[str, ...] = ('categories', 'tags')
    # Organize the edit form logically using fieldsets
    fieldsets: Tuple[Tuple[Optional[str], Dict[str, Tuple[str, ...]]], ...] = (
        (None, { # Main content section
            'fields': ('title', 'summary', 'full_text_content')
        }),
        (_('Source & Metadata'), { # Source information section
            'fields': ('source_name', 'original_url', 'publication_date', 'authors')
        }),
        (_('Taxonomy'), { # Classification section
            'fields': ('categories', 'tags')
        }),
        (_('Status & Workflow'), { # Publication status section
            'fields': ('status',)
        }),
        (_('Tracking Information'), { # Audit fields, collapsed by default
            'fields': ('added_by', 'published_by', 'created_at', 'updated_at', 'published_at'),
            'classes': ('collapse',)
        }),
    )
    # Default sorting in the admin list view
    ordering: Tuple[str, ...] = ('-created_at',)
    # Add date drilldown navigation
    date_hierarchy: Optional[str] = 'created_at'
    # Improve performance for list view by selecting related users
    list_select_related: Tuple[str, ...] = ('added_by', 'published_by')

    # --- Custom Display Methods ---

    @admin.display(description=_('Added Recently'), boolean=True, ordering='created_at')
    def was_added_recently(self, obj: Article) -> bool:
        """Returns True if the article was added within the last 7 days."""
        # Ensure created_at is valid before comparison
        if isinstance(obj.created_at, datetime):
             return obj.created_at >= (timezone.now() - timedelta(days=7))
        logger.warning("Article [PK: %s] has invalid created_at type: %s", obj.pk, type(obj.created_at))
        return False

    @admin.display(description=_('Pub Date'), ordering='publication_date')
    def display_publication_date(self, obj: Article) -> str:
        """Formats the publication_date (Date) for display, handles None."""
        pub_date: Optional[date] = obj.publication_date
        return pub_date.strftime('%Y-%m-%d') if pub_date else '-'

    @admin.display(description=_('Published On'), ordering='published_at')
    def display_published_at(self, obj: Article) -> str:
        """Formats the published_at (DateTime) for display, handles None."""
        pub_at_dt: Optional[datetime] = obj.published_at
        return pub_at_dt.strftime('%Y-%m-%d %H:%M') if pub_at_dt else '-'

    @admin.display(description=_('Added By'), ordering='added_by')
    def added_by_user(self, obj: Article) -> str:
        """Returns the username of the user who added the article."""
        return obj.added_by.username if obj.added_by else '-'

    # --- Custom Save Logic ---

    def save_model(self, request: HttpRequest, obj: Article, form: Form, change: bool) -> None:
        """
        Overrides save_model to implement workflow logic and observability:
        - Automatically sets 'added_by' on creation if empty and user is authenticated.
        - Automatically sets 'published_by' when status changes to PUBLISHED if empty
          and user is authenticated.
        - Increments publish counter on status change to PUBLISHED.
        - Calls the observability mixin via super() for generic logging/metrics.
        """
        user_authenticated: bool = request.user.is_authenticated
        user_display: str = request.user.username if user_authenticated else 'AnonymousUser'
        action: str = ACTION_UPDATE if change else ACTION_CREATE

        # --- Article-specific workflow logic ---
        if action == ACTION_CREATE and not obj.added_by:
            if user_authenticated:
                obj.added_by = request.user
                logger.debug(
                    "Setting added_by to '%s' for new Article.", user_display,
                    extra={'user': user_display, 'object_pk': obj.pk, 'action': action}
                )
            else:
                 logger.warning(
                    "Cannot set added_by for new Article: User is anonymous.",
                    extra={'user': user_display, 'object_pk': obj.pk, 'action': action}
                 )

        status_changed_to_published: bool = (
            'status' in form.changed_data and obj.status == STATUS_PUBLISHED
        )

        if status_changed_to_published:
            if not obj.published_by: # Only set if not already set
                if user_authenticated:
                    obj.published_by = request.user
                    logger.debug(
                        "Setting published_by to '%s' for Article [PK: %s] on status change to PUBLISHED.",
                        user_display, obj.pk,
                        extra={'user': user_display, 'object_pk': obj.pk, 'action': action}
                    )
                else:
                    logger.warning(
                        "Cannot set published_by for Article [PK: %s]: User is anonymous during publish event.",
                        obj.pk, extra={'user': user_display, 'object_pk': obj.pk, 'action': action}
                    )
            # Increment Prometheus counter specifically for publishing events
            ARTICLES_PUBLISHED_TOTAL.inc()
            logger.info(
                "Article [PK: %s] status changed to PUBLISHED by user '%s'.",
                obj.pk, user_display,
                extra={'user': user_display, 'object_pk': obj.pk, 'action': action}
            )

        # --- Call the next save_model in MRO (triggers AdminObservabilityMixin) ---
        # This handles the generic logging and MODEL_SAVED_TOTAL counter increment.
        # It's crucial this is called AFTER the specific logic above.
        super().save_model(request, obj, form, change)

    # --- Optional: Custom Admin Actions ---
    # actions = ['make_published'] # Register actions here
    #
    # @admin.action(description=_("Mark selected articles as Published"))
    # def make_published(self, request: HttpRequest, queryset: QuerySet[Article]) -> None:
    #     """Admin action to publish selected articles."""
    #     action_name: str = 'make_published' # Use for logging/metrics
    #     user_authenticated: bool = request.user.is_authenticated
    #     user_display: str = request.user.username if user_authenticated else 'AnonymousUser'
    #     updated_count: int = 0
    #
    #     logger.info(
    #         "Admin action '%s' initiated by user '%s' for %d articles.",
    #         action_name, user_display, queryset.count(),
    #         extra={'user': user_display, 'action_name': action_name, 'queryset_count': queryset.count()}
    #     )
    #
    #     articles_to_update: List[Article] = []
    #     pks_published: List[int] = []
    #
    #     for article in queryset:
    #         if article.status != STATUS_PUBLISHED:
    #             article.status = STATUS_PUBLISHED
    #             article.published_at = timezone.now() # Set publication time
    #             if user_authenticated:
    #                 # Only set publisher if the user is logged in
    #                 article.published_by = request.user
    #             articles_to_update.append(article)
    #             pks_published.append(article.pk)
    #             updated_count += 1
    #
    #     if articles_to_update:
    #         # Use bulk_update for efficiency if many articles are selected
    #         Article.objects.bulk_update(
    #             articles_to_update,
    #             fields=['status', 'published_at', 'published_by', 'updated_at']
    #         )
    #         # Increment counters AFTER successful update
    #         ARTICLES_PUBLISHED_TOTAL.inc(updated_count)
    #         ADMIN_ACTIONS_EXECUTED_TOTAL.labels(action_name=action_name).inc(updated_count)
    #
    #     logger.info(
    #         "Admin action '%s' completed by user '%s'. %d articles published (PKs: %s).",
    #         action_name, user_display, updated_count, pks_published,
    #         extra={'user': user_display, 'action_name': action_name, 'updated_count': updated_count, 'pks': pks_published}
    #     )
    #     if updated_count > 0:
    #         self.message_user(request, _(f"{updated_count} articles successfully marked as Published."))
    #     else:
    #         self.message_user(request, _("No articles needed updating to Published status."), level=logging.WARNING)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('parse_urls/', self.admin_site.admin_view(self.parse_urls_view), name='parse_urls'),
        ]
        return custom_urls + urls
    
    def parse_urls_view(self, request: HttpRequest):
        """Представление для парсинга URL через админ-панель."""
        if request.method == 'POST':
            form = ParsingURLForm(request.POST)
            if form.is_valid():
                urls = form.cleaned_data['urls'].strip().split('\n')
                urls = [url.strip() for url in urls if url.strip()]
                
                if not urls:
                    self.message_user(request, "Не указаны URL для парсинга", level=messages.ERROR)
                    return redirect('admin:parse_urls')
                
                # Запускаем парсинг
                manager = ParserManager()
                results = manager.parse_multiple_urls(urls)
                
                # Формируем сообщение о результатах
                success_count = sum(1 for article in results.values() if article is not None)
                self.message_user(
                    request, 
                    f"Парсинг завершен. Успешно обработано: {success_count}/{len(urls)}",
                    level=messages.SUCCESS if success_count == len(urls) else messages.WARNING
                )
                
                # Формируем детальную информацию о результатах
                for url, article in results.items():
                    if article:
                        self.message_user(
                            request,
                            format_html('✅ <a href="{}">{}</a> -> <a href="{}">"{}"</a>', 
                                        url, url,
                                        f"/admin/articles/article/{article.id}/change/", 
                                        article.title),
                            level=messages.SUCCESS
                        )
                    else:
                        self.message_user(
                            request,
                            format_html('❌ <a href="{}">{}</a> -> Ошибка парсинга', url, url),
                            level=messages.ERROR
                        )
                
                return redirect('admin:articles_article_changelist')
        else:
            form = ParsingURLForm()
        
        context = {
            'title': 'Парсинг URL',
            'form': form,
            'opts': self.model._meta,
        }
        return render(request, 'admin/articles/article/parse_urls.html', context)
    
    def get_actions(self, request):
        """Добавляем ссылку на парсинг URL в админке."""
        actions = super().get_actions(request)
        actions['parse_urls_action'] = (
            self.parse_urls_action,
            'parse_urls_action',
            'Перейти к парсингу URL'
        )
        return actions
    
    def parse_urls_action(self, modeladmin, request, queryset):
        """Действие для перехода к парсингу URL."""
        return redirect('admin:parse_urls')
    
    parse_urls_action.short_description = "Перейти к парсингу URL"