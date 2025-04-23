from abc import ABC, abstractmethod
from typing import List, Dict
from datetime import datetime
from models import NewsArticle, CompanyDateRange

class SuperBaseParser(ABC):
    def __init__(self, company_range: CompanyDateRange):
        self.company_range = company_range

    def clean_text(self, text: str) -> str:
        """Clean text by replacing non-breaking spaces and other problematic characters"""
        if not text:
            return ""
        # Replace non-breaking space with regular space
        return text.replace('\xa0', ' ')

    @abstractmethod
    def parse(self) -> List[NewsArticle]:
        """Получить список ссылок на новости + сами новости за период."""
        pass
