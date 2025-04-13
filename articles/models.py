# /echosignal_project/articles/models.py

import logging
from typing import List, Tuple, Optional, Type # For type hinting

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
# Removed unused ObjectDoesNotExist import

# --- Prometheus Metrics Integration (Optional) ---
PROMETHEUS_ENABLED: bool = False
try:
    from prometheus_client import Counter # Removed unused Histogram import for now
    # Define metrics: Initialized once when models.py is loaded.
    SLUGS_GENERATED_TOTAL = Counter(
        'articles_slugs_generated_total',
        'Total number of slugs automatically generated.',
        ['model_name'] # Label to distinguish between Category and Tag slugs
    )
    ARTICLES_SAVED_TOTAL = Counter(
        'articles_saved_total',
        'Total number of Article model saves.',
        ['status', 'is_new'] # Labels for status and whether it was a new instance
    )
    ARTICLES_PUBLISHED_TOTAL = Counter(
        'articles_published_total',
        'Total number of articles transitioned to PUBLISHED status.'
    )
    PROMETHEUS_ENABLED = True
except ImportError:
    # Define dummy metrics if prometheus-client is not installed
    class DummyCounter:
        def inc(self, *args: object, **kwargs: object) -> None: pass
        def labels(self, *args: object, **kwargs: object) -> 'DummyCounter': return self

    SLUGS_GENERATED_TOTAL = DummyCounter()
    ARTICLES_SAVED_TOTAL = DummyCounter()
    ARTICLES_PUBLISHED_TOTAL = DummyCounter()

# --- Logger Setup ---
logger = logging.getLogger(__name__) # Logger for this module


# --- Mixins ---

class SlugMixin(models.Model):
    """
    Abstract mixin for models needing automatic slug generation from 'name'.
    Requires 'name' (CharField) and 'slug' (SlugField) fields in the child model.
    """
    # Type placeholders for fields expected in inheriting model
    name: models.CharField
    slug: models.SlugField

    def save(self, *args: object, **kwargs: object) -> None:
        """Generates slug from name if slug is not already set."""
        model_name: str = self.__class__.__name__
        if not self.slug and self.name:
            # Ensure slug fits max_length defined in the child model's field
            max_len: int = self._meta.get_field('slug').max_length
            generated_slug: str = slugify(self.name)[:max_len]
            self.slug = generated_slug
            logger.debug(f"Generated slug '{generated_slug}' for {model_name} '{self.name}'")
            if PROMETHEUS_ENABLED:
                SLUGS_GENERATED_TOTAL.labels(model_name=model_name).inc()
        super().save(*args, **kwargs)

    class Meta:
        abstract = True


# --- Models ---

class Category(SlugMixin, models.Model):
    """Represents a category for classifying articles."""
    name = models.CharField(
        verbose_name="Category Name",
        max_length=100,
        unique=True,
        help_text="The unique name of the category."
    )
    slug = models.SlugField(
        verbose_name="Slug",
        max_length=110,
        unique=True,
        blank=True,
        help_text="URL-friendly identifier, auto-generated from name if blank."
    )

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering: List[str] = ['name']


class Tag(SlugMixin, models.Model):
    """Represents a tag for keyword-based classification of articles."""
    name = models.CharField(
        verbose_name="Tag Name",
        max_length=100,
        unique=True,
        help_text="The unique name of the tag."
    )
    slug = models.SlugField(
        verbose_name="Slug",
        max_length=110,
        unique=True,
        blank=True,
        help_text="URL-friendly identifier, auto-generated from name if blank."
    )

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering: List[str] = ['name']


class Article(models.Model):
    """Represents a single research article or content piece."""

    # --- Status Choices (Constants) ---
    STATUS_DRAFT: str = 'DRAFT'
    STATUS_PENDING: str = 'PENDING'
    STATUS_PUBLISHED: str = 'PUBLISHED'
    STATUS_REJECTED: str = 'REJECTED'

    STATUS_CHOICES: List[Tuple[str, str]] = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_PENDING, 'Pending Review'),
        (STATUS_PUBLISHED, 'Published'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    # --- Core Fields ---
    title = models.CharField(verbose_name="Title", max_length=255, help_text="The main title of the article or research.")
    source_name = models.CharField(verbose_name="Source Name", max_length=150, blank=True, help_text="Origin of the content (e.g., PubMed, Manual Input, Website Name).")
    original_url = models.URLField(verbose_name="Original URL", max_length=2000, blank=True, null=True, unique=True, db_index=True, help_text="Unique URL to the original source, if available.")
    publication_date = models.DateField(verbose_name="Original Publication Date", blank=True, null=True, help_text="Date the original article was published.")
    authors = models.CharField(verbose_name="Authors", max_length=500, blank=True, help_text="List of authors, comma-separated or as cited.")
    summary = models.TextField(verbose_name="Summary / Abstract", help_text="A brief summary or abstract of the content.")
    full_text_content = models.TextField(verbose_name="Full Text Content", blank=True, null=True, help_text="Full text if added manually or parsed successfully.")

    # --- Relationships ---
    categories = models.ManyToManyField(Category, verbose_name="Categories", related_name='articles', blank=True, help_text="Select relevant categories.")
    tags = models.ManyToManyField(Tag, verbose_name="Tags", related_name='articles', blank=True, help_text="Select relevant tags/keywords.")

    # --- Status and Workflow ---
    status = models.CharField(verbose_name="Status", max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True, help_text="Current workflow status of the article.")

    # --- Tracking Fields ---
    added_by = models.ForeignKey(User, verbose_name="Added By", related_name='added_articles', on_delete=models.SET_NULL, null=True, blank=True, help_text="User who initially added this article.")
    published_by = models.ForeignKey(User, verbose_name="Published By", related_name='published_articles', on_delete=models.SET_NULL, null=True, blank=True, help_text="User who approved the publication.")
    created_at = models.DateTimeField(verbose_name="Created At", auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(verbose_name="Last Updated At", auto_now=True, editable=False)
    published_at = models.DateTimeField(verbose_name="Published At", blank=True, null=True, db_index=True, editable=False, help_text="Timestamp when the article was first published on this site.")

    # Internal state tracking for save method logic
    _original_status: Optional[str] = None

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Store original status on model instance initialization."""
        super().__init__(*args, **kwargs)
        # Store the initial status when the model instance is loaded or created
        self._original_status = self.status

    def save(self, *args: object, **kwargs: object) -> None:
        """
        Overrides save to:
        1. Automatically set 'published_at' timestamp when status transitions to 'PUBLISHED'.
        2. Log events and increment Prometheus counters.
        3. Avoids extra DB query by using internal state (_original_status).
        """
        is_new: bool = self.pk is None
        current_status: str = self.status
        original_status: Optional[str] = self._original_status # Status when instance was loaded

        logger.debug(f"Saving Article PK={self.pk}, Title='{self.title[:50]}...', Status={current_status}, OriginalStatus={original_status}")

        # --- Handle published_at logic ---
        # Check if status is changing *to* PUBLISHED from a different state
        is_publishing_now: bool = (
            current_status == self.STATUS_PUBLISHED and
            original_status != self.STATUS_PUBLISHED
        )

        if is_publishing_now and not self.published_at:
            # Only set published_at if it's not already set (handles edge cases)
            self.published_at = timezone.now()
            logger.info(f"Article PK={self.pk} Title='{self.title[:50]}...' transitioning to PUBLISHED. Setting published_at={self.published_at}")
            if PROMETHEUS_ENABLED:
                ARTICLES_PUBLISHED_TOTAL.inc()
        # Optional: Handle unpublishing - current logic leaves published_at intact
        # elif current_status != self.STATUS_PUBLISHED and original_status == self.STATUS_PUBLISHED:
        #     logger.info(f"Article PK={self.pk} Title='{self.title[:50]}...' unpublished. Keeping published_at={self.published_at}")
        #     # self.published_at = None # Uncomment to clear timestamp

        # --- Save the instance ---
        super().save(*args, **kwargs)

        # --- Update internal state and metrics AFTER successful save ---
        # Update the internal state to reflect the newly saved status
        self._original_status = current_status
        if PROMETHEUS_ENABLED:
            ARTICLES_SAVED_TOTAL.labels(status=current_status, is_new=is_new).inc()

        logger.debug(f"Successfully saved Article PK={self.pk}")


    def __str__(self) -> str:
        return str(self.title)

    class Meta:
        verbose_name = "Article"
        verbose_name_plural = "Articles"
        ordering: List[str] = ['-published_at', '-created_at']
        indexes: List[models.Index] = [
            # Explicitly naming the index is good practice
            models.Index(fields=['status', '-published_at'], name='articles_status_pub_at_idx'),
        ]