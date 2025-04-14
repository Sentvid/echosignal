"""
Парсер для извлечения данных с сайта rootsofloneliness.com
"""
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

from django.utils import timezone

from articles.parsers.base_parser import BaseParser

logger = logging.getLogger(__name__)


class RootsOfLonelinessParser(BaseParser):
    """Парсер для извлечения статистики одиночества с сайта RootsOfLoneliness."""
    
    def __init__(self, url: str = "https://www.rootsofloneliness.com/loneliness-statistics"):
        """
        Инициализация парсера для RootsOfLoneliness.
        
        Args:
            url: URL страницы со статистикой
        """
        super().__init__(url)
        self.source_name = "Roots Of Loneliness"
    
    def extract_title(self) -> str:
        """Извлекает заголовок статьи."""
        try:
            title_element = self.soup.find('h1')
            if title_element:
                return title_element.text.strip()
            return "Loneliness Statistics"
        except Exception as e:
            logger.error(f"Ошибка при извлечении заголовка: {e}")
            return "Loneliness Statistics"
    
    def extract_publication_date(self) -> Optional[datetime.date]:
        """Извлекает дату публикации."""
        try:
            # Ищем дату в формате "Updated: Month Day, Year"
            date_text = None
            for element in self.soup.find_all(['p', 'div', 'span']):
                if 'updated' in element.text.lower():
                    date_text = element.text
                    break
                    
            if date_text:
                # Извлекаем дату регулярным выражением
                date_match = re.search(r'Updated: ([A-Za-z]+ \d+, \d{4})', date_text)
                if date_match:
                    date_str = date_match.group(1)
                    return datetime.strptime(date_str, '%B %d, %Y').date()
            
            # Если не удалось найти дату, возвращаем текущую дату
            return timezone.now().date()
        except Exception as e:
            logger.error(f"Ошибка при извлечении даты публикации: {e}")
            return timezone.now().date()
    
    def extract_statistics(self) -> List[str]:
        """Извлекает статистические данные о одиночестве."""
        statistics = []
        try:
            # Ищем все маркированные списки и параграфы с цифрами
            for element in self.soup.find_all(['li', 'p']):
                text = element.text.strip()
                # Ищем текст, содержащий проценты или числовые данные
                if re.search(r'\d+%|\d+ percent|\d+ in \d+', text):
                    statistics.append(text)
            
            return statistics
        except Exception as e:
            logger.error(f"Ошибка при извлечении статистики: {e}")
            return []
    
    def extract_content(self) -> str:
        """Извлекает основной контент статьи."""
        try:
            # Попытка найти основной контейнер контента
            content_container = self.soup.find('article') or self.soup.find('div', class_=re.compile(r'content|main|article'))
            
            if content_container:
                # Извлекаем текст из всех параграфов и заголовков
                content_elements = content_container.find_all(['p', 'h2', 'h3', 'ul', 'ol'])
                content = "\n\n".join([elem.text.strip() for elem in content_elements if elem.text.strip()])
                return content
            
            # Запасной вариант, если не удалось найти контейнер
            body_text = []
            for paragraph in self.soup.find_all('p'):
                text = paragraph.text.strip()
                if text and len(text) > 50:  # Исключаем короткие параграфы
                    body_text.append(text)
            
            return "\n\n".join(body_text)
        except Exception as e:
            logger.error(f"Ошибка при извлечении контента: {e}")
            return ""
    
    def create_summary(self, statistics: List[str]) -> str:
        """Создает краткое описание на основе статистики."""
        if not statistics:
            return "Статистические данные об одиночестве и социальных связях."
        
        # Берем до 5 статистических данных для резюме
        selected_stats = statistics[:5]
        summary = "Ключевые статистические данные об одиночестве:\n\n"
        summary += "\n".join([f"• {stat}" for stat in selected_stats])
        
        return summary
    
    def parse(self) -> Dict[str, Any]:
        """
        Парсит контент страницы статистики одиночества.
        
        Returns:
            Dict[str, Any]: Словарь с извлеченными данными
        """
        if not self.soup and not self.fetch_content():
            logger.error("Не удалось получить контент страницы")
            return {}
        
        title = self.extract_title()
        publication_date = self.extract_publication_date()
        statistics = self.extract_statistics()
        full_content = self.extract_content()
        summary = self.create_summary(statistics)
        
        # Формируем результат
        result = {
            'title': title,
            'summary': summary,
            'source_name': self.source_name,
            'original_url': self.url,
            'publication_date': publication_date,
            'authors': 'Roots Of Loneliness Team',
            'full_text_content': full_content,
            'categories': ['Statistics', 'Loneliness Research'],
            'tags': ['loneliness', 'statistics', 'social isolation', 'mental health'],
        }
        
        return result 