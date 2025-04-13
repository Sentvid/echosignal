import logging
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from articles.models import (
    Article,
    Category,
    Tag,
    SLUGS_GENERATED_TOTAL,
    ARTICLES_PUBLISHED_TOTAL,
    ARTICLES_SAVED_TOTAL,
)

# Get User model safely
User = get_user_model()

# Disable logging below CRITICAL during tests for cleaner output
logging.disable(logging.CRITICAL)


class CategoryModelTests(TestCase):
    """Tests for the Category model logic."""

    def test_slug_generation(self):
        """Test that slugs are automatically generated if not provided."""
        # Create without slug
        category = Category.objects.create(name="Test Category")
        self.assertEqual(category.slug, "test-category", "Slug should be auto-generated from name")

        # Create with explicit slug
        category_explicit = Category.objects.create(name="Another Category", slug="custom-slug")
        self.assertEqual(category_explicit.slug, "custom-slug", "Explicit slug should be preserved")

    def test_string_representation(self):
        """Test that the string representation is correct."""
        category = Category.objects.create(name="Test Category")
        self.assertEqual(str(category), "Test Category", "String representation should be the name")


class TagModelTests(TestCase):
    """Tests for the Tag model logic."""

    def test_slug_generation(self):
        """Test that slugs are automatically generated if not provided."""
        # Create without slug
        tag = Tag.objects.create(name="Test Tag")
        self.assertEqual(tag.slug, "test-tag", "Slug should be auto-generated from name")

        # Create with explicit slug
        tag_explicit = Tag.objects.create(name="Another Tag", slug="custom-slug")
        self.assertEqual(tag_explicit.slug, "custom-slug", "Explicit slug should be preserved")

    def test_string_representation(self):
        """Test that the string representation is correct."""
        tag = Tag.objects.create(name="Test Tag")
        self.assertEqual(str(tag), "Test Tag", "String representation should be the name")


class ArticleModelTests(TestCase):
    """Tests for the Article model logic."""

    @classmethod
    def setUpTestData(cls):
        """Set up data once for all tests in this class."""
        cls.user = User.objects.create_user(username='article_tester', password='password')
        cls.category = Category.objects.create(name="Test Category")
        cls.tag = Tag.objects.create(name="Test Tag")

    def test_article_creation(self):
        """Test basic article creation and relationships."""
        article = Article.objects.create(
            title="Test Article",
            summary="Test summary",
            status=Article.STATUS_DRAFT,
            added_by=self.user
        )
        article.categories.add(self.category)
        article.tags.add(self.tag)

        # Test relationships
        self.assertEqual(article.categories.count(), 1, "Article should have one category")
        self.assertEqual(article.tags.count(), 1, "Article should have one tag")
        self.assertEqual(article.categories.first(), self.category, "Article should be in the test category")
        self.assertEqual(article.tags.first(), self.tag, "Article should have the test tag")

    def test_published_at_logic(self):
        """Test that published_at is set when status changes to PUBLISHED."""
        # Create draft article
        article = Article.objects.create(
            title="Draft Article",
            summary="Test summary",
            status=Article.STATUS_DRAFT,
            added_by=self.user
        )
        self.assertIsNone(article.published_at, "published_at should be None for draft article")

        # Change to published
        article.status = Article.STATUS_PUBLISHED
        article.save()
        
        self.assertIsNotNone(article.published_at, "published_at should be set when published")
        self.assertLess(
            timezone.now() - article.published_at, 
            timedelta(seconds=5), 
            "published_at should be recent"
        )

    def test_string_representation(self):
        """Test that the string representation is correct."""
        article = Article.objects.create(
            title="Test Article",
            summary="Test summary",
            status=Article.STATUS_DRAFT
        )
        self.assertEqual(str(article), "Test Article", "String representation should be the title")

    @patch('articles.models.ARTICLES_PUBLISHED_TOTAL')
    def test_publishing_increments_counter(self, mock_counter):
        """Test that publishing an article increments the counter."""
        article = Article.objects.create(
            title="Test Counter Article",
            summary="Test summary",
            status=Article.STATUS_DRAFT
        )
        
        # Initial save shouldn't increment publish counter
        mock_counter.inc.assert_not_called()
        
        # Change to published
        article.status = Article.STATUS_PUBLISHED
        article.save()
        
        # Should increment counter once
        mock_counter.inc.assert_called_once()

    def test_original_status_tracking(self):
        """Test that _original_status is properly tracked."""
        article = Article.objects.create(
            title="Status Tracker Article", 
            summary="Test",
            status=Article.STATUS_DRAFT
        )
        self.assertEqual(article._original_status, Article.STATUS_DRAFT, 
                         "_original_status should match initial status")
        
        # Change status
        article.status = Article.STATUS_PENDING
        article.save()
        
        # After save, _original_status should be updated
        self.assertEqual(article._original_status, Article.STATUS_PENDING,
                         "_original_status should be updated after save") 