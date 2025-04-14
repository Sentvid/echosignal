"""
Базовый класс парсера, от которого наследуются все специфические парсеры.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

import requests
from bs4 import BeautifulSoup
from django.utils.text import slugify

from articles.models import Article, Category, Tag

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """Базовый класс для всех парсеров."""
    
    def __init__(self, url: str):
        """
        Инициализация парсера.
        
        Args:
            url: URL источника для парсинга
        """
        self.url = url
        self.soup = None
        self.content = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }

    def fetch_content(self) -> bool:
        """
        Получает HTML-контент страницы.
        
        Returns:
            bool: True если успешно, False в противном случае
        """
        try:
            response = requests.get(self.url, headers=self.headers, timeout=10)
            response.raise_for_status()
            self.content = response.text
            self.soup = BeautifulSoup(self.content, 'lxml')
            return True
        except Exception as e:
            logger.error(f"Ошибка при получении контента: {e}")
            return False
    
    @abstractmethod
    def parse(self) -> Dict[str, Any]:
        """
        Парсит контент и возвращает извлеченные данные.
        
        Returns:
            Dict[str, Any]: Словарь с извлеченными данными
        """
        pass
    
    def save_to_db(self, data: Dict[str, Any]) -> Optional[Article]:
        """
        Сохраняет извлеченные данные в базу данных.
        
        Args:
            data: Данные для сохранения
            
        Returns:
            Optional[Article]: Созданный объект Article или None в случае ошибки
        """
        try:
            # Создаем или получаем категории
            categories = []
            if 'categories' in data and data['categories']:
                for cat_name in data['categories']:
                    slug = slugify(cat_name)
                    category, _ = Category.objects.get_or_create(
                        slug=slug,
                        defaults={'name': cat_name}
                    )
                    categories.append(category)
            
            # Создаем или получаем теги
            tags = []
            if 'tags' in data and data['tags']:
                for tag_name in data['tags']:
                    slug = slugify(tag_name)
                    tag, _ = Tag.objects.get_or_create(
                        slug=slug,
                        defaults={'name': tag_name}
                    )
                    tags.append(tag)
            
            # Проверяем существование статьи с таким же URL
            existing_article = Article.objects.filter(original_url=data['original_url']).first()
            if existing_article:
                logger.info(f"Статья с URL {data['original_url']} уже существует")
                return existing_article
            
            # Создаем статью
            article = Article.objects.create(
                title=data['title'],
                summary=data['summary'],
                source_name=data.get('source_name', ''),
                original_url=data['original_url'],
                publication_date=data.get('publication_date'),
                authors=data.get('authors', ''),
                full_text_content=data.get('full_text_content', ''),
                status=Article.STATUS_DRAFT
            )
            
            # Добавляем категории и теги
            if categories:
                article.categories.add(*categories)
            
            if tags:
                article.tags.add(*tags)
            
            article.save()
            logger.info(f"Статья '{article.title}' успешно сохранена")
            return article
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении данных: {e}")
            return None 