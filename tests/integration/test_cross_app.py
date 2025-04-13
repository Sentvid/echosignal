"""
Integration tests for testing cross-application functionality in the EchoSignal project.
"""
import logging
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

# Disable logging below CRITICAL during tests for cleaner output
logging.disable(logging.CRITICAL)


class ArticleIntegrationTest(TestCase):
    """Test integration aspects of Article functionality."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up data once for all tests in this class."""
        # Create admin user
        cls.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpassword'
        )
        
        # Create normal user
        cls.normal_user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='userpassword'
        )
        
    def setUp(self):
        """Set up before each test."""
        self.client = Client()
    
    def test_admin_login(self):
        """Test that admin user can log in to admin site."""
        response = self.client.post(
            '/admin/login/',
            {
                'username': 'admin',
                'password': 'adminpassword',
            }
        )
        self.assertEqual(response.status_code, 302, "Admin login should redirect")
        
    def test_article_admin_access(self):
        """Test admin page access to article admin."""
        # Login first
        self.client.login(username='admin', password='adminpassword')
        
        # Access article admin
        response = self.client.get('/admin/articles/article/')
        self.assertEqual(response.status_code, 200, "Should be able to access article admin")
        
    def test_normal_user_admin_login_rejected(self):
        """Test normal user cannot log in to admin site."""
        response = self.client.post(
            '/admin/login/',
            {
                'username': 'user',
                'password': 'userpassword',
            }
        )
        # Should redirect to login page again with error
        self.assertEqual(response.status_code, 200, "Normal user should not be able to log into admin")
        self.assertContains(response, "Please enter the correct username and password") 