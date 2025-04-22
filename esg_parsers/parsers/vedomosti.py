from .base import BaseParser
import requests
from datetime import datetime
from typing import List, Dict
import time

class VedomostiParser(BaseParser):
    def __init__(self, company: str, start_date: datetime, end_date: datetime):
        super().__init__(company, start_date, end_date)

        self.name = "Vedomosti"
        self.base_url = "https://www.vedomosti.ru"
        self.search_url = "https://api.vedomosti.ru/v2/documents/search"
        self.limit = 20
        self.current_offset = 0
        self.found_news_on_page = True

        self.search_params = {
            "query": self.company,
            "sort": "date",
            "material_types": "news",
            "date_from": self.start_date.strftime("%Y-%m-%d"),
            "date_to": self.end_date.strftime("%Y-%m-%d"),
            "limit": self.limit,
            "from": self.current_offset
        }

    def super_parse(self) -> List[Dict[str, str]]:
        news_list = []
        while self.found_news_on_page:
            self.search_params["from"] = self.current_offset
            resp = requests.get(self.search_url, params=self.search_params).json()

            for item in resp["found"]:
                news_list.append({
                    "url": item['source']["url"],
                    "title": self.clean_text(item['source']["title"]),
                    "body": self.clean_text(item['source']["boxes"]),
                    "date": item['source']["published_at"][:10],
                    "parser": self.name
                })
            
            self.found_news_on_page = len(resp["found"]) > 0
            self.current_offset += self.limit
            time.sleep(1)

        return news_list

    def search_news(self) -> List[str]:
        """Получить список ссылок на новости за период."""
        pass

    def parse_article(self, url: str) -> Dict[str, str]:
        """Извлечь данные из новости."""
        pass
