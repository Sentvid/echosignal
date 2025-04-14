"""
Команда Django для парсинга URL и извлечения данных.
"""
import logging
from typing import Any, List, Optional

from django.core.management.base import BaseCommand, CommandError

from articles.models import Article
from articles.parsers.parser_manager import ParserManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Команда для парсинга URL и извлечения данных.
    Использование: python manage.py parse_urls <url1> <url2> ...
    """
    
    help = 'Парсинг URL и извлечение данных для статей'
    
    def add_arguments(self, parser):
        """Добавляет аргументы командной строки."""
        parser.add_argument('urls', nargs='+', type=str, help='URLs для парсинга')
    
    def handle(self, *args, **options):
        """Обрабатывает команду."""
        urls = options['urls']
        self.stdout.write(self.style.SUCCESS(f'Начинаем парсинг {len(urls)} URL...'))
        
        manager = ParserManager()
        results = manager.parse_multiple_urls(urls)
        
        # Выводим результаты
        success_count = sum(1 for article in results.values() if article is not None)
        self.stdout.write(self.style.SUCCESS(f'Парсинг завершен. Успешно: {success_count}/{len(urls)}'))
        
        for url, article in results.items():
            if article:
                self.stdout.write(self.style.SUCCESS(
                    f'✅ {url} -> {article.title} (ID: {article.id})'
                ))
            else:
                self.stdout.write(self.style.ERROR(
                    f'❌ {url} -> Ошибка парсинга'
                )) 