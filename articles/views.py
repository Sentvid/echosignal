from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView

from .models import Article, Category, Tag


class ArticleListView(ListView):
    """List view for Articles."""
    model = Article
    template_name = 'articles/article_list.html'
    context_object_name = 'articles'
    paginate_by = 10
    
    def get_queryset(self):
        """Return only published articles."""
        queryset = Article.objects.filter(status=Article.STATUS_PUBLISHED)
        return queryset.select_related('added_by', 'published_by').prefetch_related('categories', 'tags')
    
    def get_context_data(self, **kwargs):
        """Add categories and tags to context."""
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['tags'] = Tag.objects.all()
        return context


class ArticleDetailView(DetailView):
    """Detail view for a single Article."""
    model = Article
    template_name = 'articles/article_detail.html'
    context_object_name = 'article'
    
    def get_queryset(self):
        """Optimize queries with select_related and prefetch_related."""
        return Article.objects.select_related(
            'added_by', 'published_by'
        ).prefetch_related('categories', 'tags')


class CategoryArticlesView(ListView):
    """List articles in a specific category."""
    model = Article
    template_name = 'articles/category_articles.html'
    context_object_name = 'articles'
    paginate_by = 10
    
    def get_queryset(self):
        """Return only published articles in the specified category."""
        category_slug = self.kwargs.get('slug')
        category = get_object_or_404(Category, slug=category_slug)
        
        return Article.objects.filter(
            status=Article.STATUS_PUBLISHED, 
            categories=category
        ).select_related('added_by', 'published_by').prefetch_related('categories', 'tags')
    
    def get_context_data(self, **kwargs):
        """Add category to context."""
        context = super().get_context_data(**kwargs)
        context['category'] = get_object_or_404(Category, slug=self.kwargs.get('slug'))
        return context


class TagArticlesView(ListView):
    """List articles with a specific tag."""
    model = Article
    template_name = 'articles/tag_articles.html'
    context_object_name = 'articles'
    paginate_by = 10
    
    def get_queryset(self):
        """Return only published articles with the specified tag."""
        tag_slug = self.kwargs.get('slug')
        tag = get_object_or_404(Tag, slug=tag_slug)
        
        return Article.objects.filter(
            status=Article.STATUS_PUBLISHED, 
            tags=tag
        ).select_related('added_by', 'published_by').prefetch_related('categories', 'tags')
    
    def get_context_data(self, **kwargs):
        """Add tag to context."""
        context = super().get_context_data(**kwargs)
        context['tag'] = get_object_or_404(Tag, slug=self.kwargs.get('slug'))
        return context
