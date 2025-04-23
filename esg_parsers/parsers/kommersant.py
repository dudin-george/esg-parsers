from .base import BaseParser
import requests
from datetime import datetime
from typing import List, Dict
import time
from bs4 import BeautifulSoup
import json
from models import NewsArticle, CompanyDateRange

class KommersantParser(BaseParser):
    def __init__(self, company_range: CompanyDateRange):
        super().__init__(company_range)

        self.name = "Kommersant"
        self.base_url = "https://www.kommersant.ru"
        self.search_url = "https://www.kommersant.ru/search/results"
        self.current_page = 1
        self.found_news_on_page = True

        self.search_params = {
            "search_query": self.company_range.company,
            "sort_type": 0,
            "search_full": 1,
            "time_range": 2,
            "dateStart": self.company_range.start_date.strftime("%Y-%m-%d"),
            "dateEnd": self.company_range.end_date.strftime("%Y-%m-%d"),
            "stamp": int(time.time() * 1000),
            "page": self.current_page 
        }


    def super_parse(self) -> List[NewsArticle]:
        """Придется парсить новость за новостью"""
        pass

    def search_news(self) -> List[str]:        
        news_urls = []
        while self.found_news_on_page:
            self.search_params["page"] = self.current_page
            
            # First request to get redirect URL
            resp = requests.get(self.search_url, params=self.search_params)
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Extract redirect URL from link
            redirect_link = soup.find("a")["href"]
            if not redirect_link:
                break
                
            # Follow redirect to get actual results
            resp = requests.get(self.base_url + redirect_link)
            soup = BeautifulSoup(resp.text, "html.parser")

            # Find all links matching the pattern /doc/XXXXXXX?query=Company
            links = soup.find_all("a", href=lambda x: x and "doc" in x and "query=" + self.company_range.company in x)
            
            for link in links:
                news_urls.append(self.base_url + link["href"])
            
            self.found_news_on_page = len(links) > 0
            self.current_page += 1
            time.sleep(0.5)
            
        return list(set(news_urls))


    def parse_article(self, url: str) -> NewsArticle:
        """Извлечь данные из новости."""
        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Get article title
        title_elem = soup.find("h1", {"class": "doc_header__name"})
        title = title_elem.text.strip() if title_elem else ""

        # Get article body
        body_elem = soup.find("div", {"class": "doc__body"})
        body = ""
        if body_elem:
            paragraphs = body_elem.find_all("p")
            body = " ".join([p.text for p in paragraphs])

        # Get article date
        date_elem = soup.find("time", {"class": "doc_header__publish_time"})
        date = date_elem.get("datetime", "")[:10] if date_elem else ""

        return NewsArticle(
            url=url,
            title=self.clean_text(title),
            body=self.clean_text(body),
            date=date,
            parser=self.name
        )
