import logging
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.core.paginator import Page

from articles.models import Article, Category, Tag
from articles.views import (
    article_list_view,
    VIEW_REQUESTS_TOTAL,
    VIEW_REQUEST_LATENCY_SECONDS,
    VIEW_ERRORS_TOTAL,
    PAGINATION_ERRORS_TOTAL
)

User = get_user_model()

# Disable logging below CRITICAL during tests for cleaner output
logging.disable(logging.CRITICAL)


class ArticleListViewTests(TestCase):
    """Tests for the article_list_view function."""

    @classmethod
    def setUpTestData(cls):
        """Set up data once for all tests in this class."""
        # Create user
        cls.user = User.objects.create_user(username='viewtester', password='password')
        
        # Create categories and tags
        cls.category1 = Category.objects.create(name="View Test Cat 1", slug="view-test-cat-1")
        cls.category2 = Category.objects.create(name="View Test Cat 2", slug="view-test-cat-2")
        cls.tag1 = Tag.objects.create(name="View Test Tag 1", slug="view-test-tag-1")
        cls.tag2 = Tag.objects.create(name="View Test Tag 2", slug="view-test-tag-2")
        
        # Create published articles
        for i in range(20):
            article = Article.objects.create(
                title=f"Published Article {i}",
                summary=f"Test summary {i}",
                status=Article.STATUS_PUBLISHED,
                added_by=cls.user,
                published_by=cls.user
            )
            article.categories.add(cls.category1 if i % 2 == 0 else cls.category2)
            article.tags.add(cls.tag1 if i < 10 else cls.tag2)
        
        # Create draft article
        cls.article_draft = Article.objects.create(
            title="Draft Article for View Test",
            summary="Test summary",
            status=Article.STATUS_DRAFT,
            added_by=cls.user
        )
        cls.article_draft.categories.add(cls.category2)
        cls.article_draft.tags.add(cls.tag2)

    def setUp(self):
        """Set up for each test."""
        self.client = Client()
        self.factory = RequestFactory()

    @patch('articles.views.VIEW_REQUESTS_TOTAL')
    @patch('articles.views.VIEW_REQUEST_LATENCY_SECONDS')
    def test_article_list_view_success(self, mock_latency, mock_requests):
        """Test that article list view works correctly with default parameters."""
        # Create request
        request = self.factory.get('/')
        request.user = self.user
        
        # Call the view
        response = article_list_view(request)
        
        # Assert basics
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'articles/article_list.html')
        
        # Assert context contains a page object with articles
        self.assertIn('page_obj', response.context)
        self.assertIsInstance(response.context['page_obj'], Page)
        
        # Assert only published articles are shown
        for article in response.context['page_obj'].object_list:
            self.assertEqual(article.status, Article.STATUS_PUBLISHED)
        
        # Draft article should not be in results
        all_titles = [article.title for article in response.context['page_obj'].object_list]
        self.assertNotIn(self.article_draft.title, all_titles)
        
        # Assert metrics were incremented
        mock_requests.labels.assert_called_once()
        mock_requests.labels().inc.assert_called_once()
        mock_latency.labels.assert_called_once()
        mock_latency.labels().observe.assert_called_once()

    @patch('articles.views.VIEW_REQUESTS_TOTAL')
    @patch('articles.views.VIEW_REQUEST_LATENCY_SECONDS')
    @patch('articles.views.PAGINATION_ERRORS_TOTAL')
    def test_article_list_pagination(self, mock_pagination_errors, mock_latency, mock_requests):
        """Test that pagination works correctly with various page parameters."""
        # Test page 1
        response1 = self.client.get('/?page=1')
        self.assertEqual(response1.status_code, 200)
        self.assertTrue(response1.context['page_obj'].has_next())
        self.assertFalse(response1.context['page_obj'].has_previous())
        
        # Test page 2
        response2 = self.client.get('/?page=2')
        self.assertEqual(response2.status_code, 200)
        
        # Test invalid page - should default to page 1
        response_invalid = self.client.get('/?page=abc')
        self.assertEqual(response_invalid.status_code, 200)
        self.assertEqual(response_invalid.context['page_obj'].number, 1)
        mock_pagination_errors.labels.assert_called_with(view='article_list', error_type='PageNotAnInteger')
        
        # Test out of range page - should go to last page
        response_outofrange = self.client.get('/?page=999')
        self.assertEqual(response_outofrange.status_code, 200)
        self.assertEqual(response_outofrange.context['page_obj'].number, response_outofrange.context['page_obj'].paginator.num_pages)
        mock_pagination_errors.labels.assert_called_with(view='article_list', error_type='EmptyPage')

    @patch('articles.views.VIEW_REQUESTS_TOTAL')
    @patch('articles.views.VIEW_REQUEST_LATENCY_SECONDS')
    @patch('articles.views.VIEW_ERRORS_TOTAL')
    @patch('articles.views.Article.objects.filter')
    def test_article_list_database_error(self, mock_filter, mock_errors, mock_latency, mock_requests):
        """Test that database errors are handled correctly."""
        # Setup mock to raise DatabaseError
        mock_filter.side_effect = DatabaseError("Test database error")
        
        # Need to override DEBUG setting during test
        with self.settings(DEBUG=False):
            response = self.client.get('/')
            self.assertEqual(response.status_code, 500)
            mock_errors.labels.assert_called_with(view='article_list', exception_type='DatabaseError')
            mock_errors.labels().inc.assert_called_once()

    @patch('articles.views.VIEW_REQUESTS_TOTAL')
    @patch('articles.views.VIEW_REQUEST_LATENCY_SECONDS')
    @patch('articles.views.VIEW_ERRORS_TOTAL')
    @patch('articles.views.render')
    def test_article_list_template_error(self, mock_render, mock_errors, mock_latency, mock_requests):
        """Test that template rendering errors are handled correctly."""
        # Setup mock to raise Exception during render
        mock_render.side_effect = Exception("Test template error")
        
        # Need to override DEBUG setting during test
        with self.settings(DEBUG=False):
            response = self.client.get('/')
            self.assertEqual(response.status_code, 500)
            mock_errors.labels.assert_called_with(view='article_list', exception_type='Exception')
            mock_errors.labels().inc.assert_called_once()
