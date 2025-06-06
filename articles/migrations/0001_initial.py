# Generated by Django 5.0.14 on 2025-04-02 20:54

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='The unique name of the category.', max_length=100, unique=True, verbose_name='Category Name')),
                ('slug', models.SlugField(blank=True, help_text='URL-friendly identifier, auto-generated from name if blank.', max_length=110, unique=True, verbose_name='Slug')),
            ],
            options={
                'verbose_name': 'Category',
                'verbose_name_plural': 'Categories',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='The unique name of the tag.', max_length=100, unique=True, verbose_name='Tag Name')),
                ('slug', models.SlugField(blank=True, help_text='URL-friendly identifier, auto-generated from name if blank.', max_length=110, unique=True, verbose_name='Slug')),
            ],
            options={
                'verbose_name': 'Tag',
                'verbose_name_plural': 'Tags',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text='The main title of the article or research.', max_length=255, verbose_name='Title')),
                ('source_name', models.CharField(blank=True, help_text='Origin of the content (e.g., PubMed, Manual Input, Website Name).', max_length=150, verbose_name='Source Name')),
                ('original_url', models.URLField(blank=True, db_index=True, help_text='Unique URL to the original source, if available.', max_length=2000, null=True, unique=True, verbose_name='Original URL')),
                ('publication_date', models.DateField(blank=True, help_text='Date the original article was published.', null=True, verbose_name='Original Publication Date')),
                ('authors', models.CharField(blank=True, help_text='List of authors, comma-separated or as cited.', max_length=500, verbose_name='Authors')),
                ('summary', models.TextField(help_text='A brief summary or abstract of the content.', verbose_name='Summary / Abstract')),
                ('full_text_content', models.TextField(blank=True, help_text='Full text if added manually or parsed successfully.', null=True, verbose_name='Full Text Content')),
                ('status', models.CharField(choices=[('DRAFT', 'Draft'), ('PENDING', 'Pending Review'), ('PUBLISHED', 'Published'), ('REJECTED', 'Rejected')], db_index=True, default='DRAFT', help_text='Current workflow status of the article.', max_length=10, verbose_name='Status')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Updated At')),
                ('published_at', models.DateTimeField(blank=True, db_index=True, editable=False, help_text='Timestamp when the article was first published on this site.', null=True, verbose_name='Published At')),
                ('added_by', models.ForeignKey(blank=True, help_text='User who initially added this article.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='added_articles', to=settings.AUTH_USER_MODEL, verbose_name='Added By')),
                ('published_by', models.ForeignKey(blank=True, help_text='User who approved the publication.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='published_articles', to=settings.AUTH_USER_MODEL, verbose_name='Published By')),
                ('categories', models.ManyToManyField(blank=True, help_text='Select relevant categories.', related_name='articles', to='articles.category', verbose_name='Categories')),
                ('tags', models.ManyToManyField(blank=True, help_text='Select relevant tags/keywords.', related_name='articles', to='articles.tag', verbose_name='Tags')),
            ],
            options={
                'verbose_name': 'Article',
                'verbose_name_plural': 'Articles',
                'ordering': ['-published_at', '-created_at'],
                'indexes': [models.Index(fields=['status', '-published_at'], name='articles_status_pub_at_idx')],
            },
        ),
    ]
