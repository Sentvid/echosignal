"""URL configuration for the articles app."""

from django.urls import path
from . import views  # Import views from the same app directory

app_name = 'articles'

urlpatterns = [
    # Maps the root URL of the 'articles' app to the list view
    path('', views.article_list_view, name='article_list'),
    
    # --- Future URL Patterns ---
    # path('<slug:article_slug>/', views.article_detail_view, name='article_detail'),
    # path('category/<slug:category_slug>/', views.articles_by_category_view, name='articles_by_category'),
    # path('tag/<slug:tag_slug>/', views.articles_by_tag_view, name='articles_by_tag'),
] 