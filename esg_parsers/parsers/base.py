from abc import ABC, abstractmethod
from typing import List, Dict
from datetime import datetime
from models import NewsArticle, CompanyDateRange

class BaseParser(ABC):
    def __init__(self, company_range: CompanyDateRange):
        self.company_range = company_range

    def clean_text(self, text: str) -> str:
        """Clean text by replacing non-breaking spaces and other problematic characters"""
        if not text:
            return ""
        # Replace non-breaking space with regular space
        return text.replace('\xa0', ' ')
        
    @abstractmethod
    def search_news(self) -> List[str]:
        """Получить список ссылок на новости за период."""
        pass

    @abstractmethod
    def parse_article(self, url: str) -> NewsArticle:
        """Извлечь данные из новости."""
        pass

    def parse(self) -> List[NewsArticle]:
        news_urls = self.search_news()
        articles = []
        for url in news_urls:
            try:
                article_data = self.parse_article(url)
                articles.append(article_data)
            except Exception as e:
                print(f"Ошибка парсинга {url}: {e}")
        return articles
