from .super_base import SuperBaseParser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict
import time
from models import NewsArticle, CompanyDateRange

class ForbesParser(SuperBaseParser):
    def __init__(self, company_range: CompanyDateRange):
        super().__init__(company_range)

        self.name = "Forbes"
        self.base_url = "https://www.forbes.ru/"
        self.search_url = "https://www.forbes.ru/api/pub/search"
        self.offset_limit = 8
        self.current_offset = 0
        self.found_news_on_page = True

        self.search_params = {
            "list[offset]": self.current_offset,
            "list[limit]": self.offset_limit,
            "search[term]": self.company_range.company,
            "search[type]": "news",
            "search[sort]": "date_asc", 
            "search[start]": int(self.company_range.start_date.timestamp()),
            "search[end]": int(self.company_range.end_date.timestamp())
        }


    def parse(self) -> List[NewsArticle]:
        news_list = []
        while self.found_news_on_page:
            self.search_params["list[offset]"] = self.current_offset
            resp = requests.get(self.search_url, params=self.search_params).json()

            for item in resp["results"]:
                news_list.append(NewsArticle(
                    url=self.base_url + item["url_alias"],
                    title=self.clean_text(item["title"]),
                    body=self.clean_text(item["body"]),
                    date=datetime.fromtimestamp(item["time"]).strftime("%Y-%m-%d"),
                    parser=self.name
                ))
            
            self.found_news_on_page = len(resp['results']) > 0
            self.current_offset += self.offset_limit
            time.sleep(0.5)

        return news_list


