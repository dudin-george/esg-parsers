from .base import BaseParser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict
import time

class ForbesParser(BaseParser):
    def __init__(self, company: str, start_date: datetime, end_date: datetime):
        super().__init__(company, start_date, end_date)

        self.name = "Forbes"
        self.base_url = "https://www.forbes.ru/"
        self.search_url = "https://www.forbes.ru/api/pub/search"
        self.offset_limit = 8
        self.current_offset = 0
        self.found_news_on_page = True

        self.search_params = {
            "list[offset]": self.current_offset,
            "list[limit]": self.offset_limit,
            "search[term]": self.company,
            "search[type]": "news",
            "search[sort]": "date_asc", 
            "search[start]": int(self.start_date.timestamp()),
            "search[end]": int(self.end_date.timestamp())
        }


    def super_parse(self) -> List[Dict[str, str]]:
        news_list = []
        while self.found_news_on_page:
            self.search_params["list[offset]"] = self.current_offset
            resp = requests.get(self.search_url, params=self.search_params).json()

            for item in resp["results"]:
                news_list.append({
                    "url": self.base_url + item["url_alias"],
                    "title": self.clean_text(item["title"]),
                    "body": self.clean_text(item["body"]),
                    "date": datetime.fromtimestamp(item["time"]).strftime("%Y-%m-%d"),
                    "parser": self.name
                })
            
            self.found_news_on_page = len(resp['results']) > 0
            self.current_offset += self.offset_limit
            time.sleep(1)

        return news_list
    
    def search_news(self) -> List[str]:
        """Получить список ссылок на новости за период."""
        pass

    def parse_article(self) -> Dict[str, str]:
        """Извлечь данные из новости."""
        pass


