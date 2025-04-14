"""
Менеджер парсеров для управления процессом извлечения данных из различных источников.
"""
import logging
from typing import Dict, Any, List, Optional, Type

from articles.models import Article
from articles.parsers.base_parser import BaseParser
from articles.parsers.roots_of_loneliness_parser import RootsOfLonelinessParser
from articles.parsers.cnbc_parser import CnbcParser

logger = logging.getLogger(__name__)


class ParserManager:
    """Менеджер для управления парсерами и процессом извлечения данных."""
    
    def __init__(self):
        """Инициализация менеджера парсеров."""
        # Словарь зарегистрированных парсеров (url_pattern: parser_class)
        self.parsers: Dict[str, Type[BaseParser]] = {
            "rootsofloneliness.com": RootsOfLonelinessParser,
            "cnbc.com": CnbcParser,
            # Другие парсеры будут добавлены здесь
        }
    
    def get_parser_for_url(self, url: str) -> Optional[BaseParser]:
        """
        Находит подходящий парсер для заданного URL.
        
        Args:
            url: URL источника
            
        Returns:
            Optional[BaseParser]: Подходящий парсер или None
        """
        for domain, parser_class in self.parsers.items():
            if domain in url:
                return parser_class(url)
        
        logger.warning(f"Не найден парсер для URL: {url}")
        return None
    
    def parse_url(self, url: str) -> Optional[Article]:
        """
        Парсит указанный URL, извлекает данные и сохраняет их в базу данных.
        
        Args:
            url: URL для парсинга
            
        Returns:
            Optional[Article]: Созданный объект Article или None в случае ошибки
        """
        parser = self.get_parser_for_url(url)
        if not parser:
            return None
        
        # Получаем данные
        data = parser.parse()
        if not data:
            logger.error(f"Не удалось получить данные с URL: {url}")
            return None
        
        # Сохраняем в базу данных
        article = parser.save_to_db(data)
        return article
    
    def parse_multiple_urls(self, urls: List[str]) -> Dict[str, Optional[Article]]:
        """
        Парсит несколько URL и сохраняет результаты.
        
        Args:
            urls: Список URL для парсинга
            
        Returns:
            Dict[str, Optional[Article]]: Словарь {url: созданная_статья}
        """
        results = {}
        for url in urls:
            try:
                article = self.parse_url(url)
                results[url] = article
            except Exception as e:
                logger.error(f"Ошибка при парсинге URL {url}: {e}")
                results[url] = None
        
        return results 