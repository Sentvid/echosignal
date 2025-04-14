"""
Парсер для извлечения данных из статей CNBC, особенно о исследованиях Cigna.
"""
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

from django.utils import timezone

from articles.parsers.base_parser import BaseParser

logger = logging.getLogger(__name__)


class CnbcParser(BaseParser):
    """Парсер для извлечения данных о одиночестве из статей CNBC."""
    
    def __init__(self, url: str):
        """
        Инициализация парсера для CNBC.
        
        Args:
            url: URL статьи
        """
        super().__init__(url)
        self.source_name = "CNBC"
    
    def extract_title(self) -> str:
        """Извлекает заголовок статьи."""
        try:
            # Ищем заголовок в нескольких возможных местах
            title_element = self.soup.find('h1')
            if title_element:
                return title_element.text.strip()
            
            # Альтернативный поиск по классу или ID
            title_element = self.soup.find(['h1', 'h2'], class_=re.compile(r'title|headline', re.I))
            if title_element:
                return title_element.text.strip()
            
            return "CNBC Article about Loneliness"
        except Exception as e:
            logger.error(f"Ошибка при извлечении заголовка: {e}")
            return "CNBC Article about Loneliness"
    
    def extract_publication_date(self) -> Optional[datetime.date]:
        """Извлекает дату публикации."""
        try:
            # Ищем элементы с датой
            date_element = self.soup.find(['time', 'span', 'div'], attrs={'data-testid': 'publish-date'})
            if date_element:
                date_text = date_element.text.strip()
                # Пытаемся разобрать дату в формате "Mon DD YYYY"
                return datetime.strptime(date_text, '%b %d %Y').date()
            
            # Альтернативный поиск
            for elem in self.soup.find_all(['time', 'span', 'p']):
                if 'published' in elem.text.lower() or 'updated' in elem.text.lower():
                    # Ищем дату в формате "Published/Updated Mon DD YYYY"
                    date_match = re.search(r'(Published|Updated):?\s+([A-Za-z]{3}\s+\d{1,2},?\s+\d{4})', elem.text)
                    if date_match:
                        date_str = date_match.group(2)
                        return datetime.strptime(date_str, '%b %d, %Y').date()
            
            # Если не удалось найти дату, возвращаем текущую
            return timezone.now().date()
        except Exception as e:
            logger.error(f"Ошибка при извлечении даты публикации: {e}")
            return timezone.now().date()
    
    def extract_author(self) -> str:
        """Извлекает автора статьи."""
        try:
            # Ищем элемент с автором
            author_element = self.soup.find(['span', 'div', 'a'], class_=re.compile(r'author|byline', re.I))
            if author_element:
                return author_element.text.strip()
            
            # Альтернативный поиск
            for elem in self.soup.find_all(['p', 'span', 'div']):
                if 'by ' in elem.text.lower():
                    author_match = re.search(r'[bB]y\s+([A-Za-z\s\.]+)', elem.text)
                    if author_match:
                        return author_match.group(1).strip()
            
            return "CNBC Staff"
        except Exception as e:
            logger.error(f"Ошибка при извлечении автора: {e}")
            return "CNBC Staff"
    
    def extract_statistics(self) -> List[str]:
        """Извлекает статистические данные о одиночестве из статьи."""
        statistics = []
        try:
            # Ищем параграфы и списки с числовыми данными
            for element in self.soup.find_all(['p', 'li']):
                text = element.text.strip()
                # Ищем текст с процентами и ключевыми словами о одиночестве
                if re.search(r'\d+%', text) and re.search(r'lone|isolat|disconnect|social', text, re.I):
                    statistics.append(text)
                # Ищем предложения с цифрами и ключевыми словами
                elif re.search(r'\d+', text) and re.search(r'Cigna|survey|study|report', text, re.I) and re.search(r'lone|isolat|disconnect|social', text, re.I):
                    statistics.append(text)
            
            return statistics
        except Exception as e:
            logger.error(f"Ошибка при извлечении статистики: {e}")
            return []
    
    def extract_content(self) -> str:
        """Извлекает основной контент статьи."""
        try:
            # Ищем основной контейнер контента
            content_container = self.soup.find('div', class_=re.compile(r'article-body|content|main', re.I))
            
            if content_container:
                # Извлекаем все параграфы из основного контейнера
                paragraphs = content_container.find_all(['p', 'h2', 'h3', 'blockquote'])
                content = "\n\n".join([p.text.strip() for p in paragraphs if p.text.strip()])
                return content
            
            # Запасной вариант - извлекаем все параграфы статьи
            paragraphs = []
            for p in self.soup.find_all('p'):
                text = p.text.strip()
                if len(text) > 30:  # Исключаем короткие текстовые фрагменты
                    paragraphs.append(text)
            
            return "\n\n".join(paragraphs)
        except Exception as e:
            logger.error(f"Ошибка при извлечении контента: {e}")
            return ""
    
    def create_summary(self, statistics: List[str], content: str) -> str:
        """
        Создает краткое описание статьи на основе статистики и контента.
        
        Args:
            statistics: Список извлеченных статистических данных
            content: Полный текст статьи
            
        Returns:
            str: Краткое описание
        """
        # Если есть статистика, используем её для резюме
        if statistics:
            selected_stats = statistics[:3]  # Берем не больше 3 статистических данных
            summary = "Основные статистические данные из исследования Cigna о одиночестве:\n\n"
            summary += "\n".join([f"• {stat}" for stat in selected_stats])
            return summary
        
        # Если нет статистики, формируем резюме из первых предложений статьи
        if content:
            # Разделяем текст на предложения
            sentences = re.split(r'(?<=[.!?])\s+', content)
            # Берем первые 2-3 предложения для резюме
            relevant_sentences = []
            for sentence in sentences[:5]:
                if re.search(r'lone|isolat|disconnect|social|Cigna|health', sentence, re.I):
                    relevant_sentences.append(sentence)
                if len(relevant_sentences) >= 3:
                    break
            
            if relevant_sentences:
                return " ".join(relevant_sentences)
        
        # Запасной вариант
        return "Статья CNBC об исследовании Cigna о состоянии одиночества и его влиянии на здоровье."
    
    def parse(self) -> Dict[str, Any]:
        """
        Парсит контент статьи CNBC.
        
        Returns:
            Dict[str, Any]: Словарь с извлеченными данными
        """
        if not self.soup and not self.fetch_content():
            logger.error("Не удалось получить контент страницы")
            return {}
        
        title = self.extract_title()
        publication_date = self.extract_publication_date()
        author = self.extract_author()
        statistics = self.extract_statistics()
        content = self.extract_content()
        summary = self.create_summary(statistics, content)
        
        # Определяем теги на основе содержимого
        tags = ['loneliness', 'health', 'Cigna', 'survey']
        if re.search(r'gen ?z', content, re.I):
            tags.append('Gen Z')
        if re.search(r'millennials', content, re.I):
            tags.append('millennials')
        if re.search(r'social media', content, re.I):
            tags.append('social media')
        if re.search(r'mental health', content, re.I):
            tags.append('mental health')
        
        # Формируем результат
        result = {
            'title': title,
            'summary': summary,
            'source_name': self.source_name,
            'original_url': self.url,
            'publication_date': publication_date,
            'authors': author,
            'full_text_content': content,
            'categories': ['Health Research', 'Corporate Studies'],
            'tags': tags,
        }
        
        return result 