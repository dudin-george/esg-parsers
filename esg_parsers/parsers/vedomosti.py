from .super_base import SuperBaseParser
import requests
from datetime import datetime
from typing import List, Dict
import time
import random
from models import NewsArticle, CompanyDateRange
import json

class VedomostiParser(SuperBaseParser):
    def __init__(self, company_range: CompanyDateRange):
        super().__init__(company_range)

        self.name = "Vedomosti"
        self.base_url = "https://www.vedomosti.ru"
        self.search_url = "https://api.vedomosti.ru/v2/documents/search"
        self.limit = 20
        self.current_offset = 0
        self.found_news_on_page = True
        self.max_retries = 5  # Максимальное количество повторных попыток
        
        # Добавляем случайный User-Agent, чтобы снизить вероятность блокировки
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
        ]

        self.search_params = {
            "query": self.company_range.company,
            "sort": "date",
            "material_types": "news",
            "date_from": self.company_range.start_date.strftime("%Y-%m-%d"),
            "date_to": self.company_range.end_date.strftime("%Y-%m-%d"),
            "limit": self.limit,
            "from": self.current_offset
        }

    def _parse_date(self, date_str: str) -> datetime:
        """Safely parse date string to datetime object"""
        try:
            # Если получена строка с полной датой и временем
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            # Если получена только дата
            else:
                return datetime.strptime(date_str[:10], "%Y-%m-%d")
        except Exception as e:
            print(f"Error parsing date {date_str}: {e}")
            return datetime.now()  # Fallback to current date
    
    def _make_request_with_retry(self, params):
        """Выполнение запроса с механизмом повторных попыток при ошибке 418"""
        headers = {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.vedomosti.ru/",
            "Origin": "https://www.vedomosti.ru",
            "Connection": "keep-alive"
        }
        
        # Начальная задержка перед повторной попыткой в секундах
        retry_delay = 2
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    self.search_url, 
                    params=params,
                    headers=headers,
                    timeout=15
                )
                
                # Если получили код 418 (I'm a teapot), сделаем повторную попытку
                if response.status_code == 418:
                    delay = retry_delay * (attempt + 1) + random.uniform(1, 3)  # Экспоненциальная задержка с случайной составляющей
                    print(f"Получен код 418 от Vedomosti. Повторная попытка через {delay:.2f} сек (attempt {attempt+1}/{self.max_retries})")
                    time.sleep(delay)
                    continue
                    
                # Если другая ошибка, просто вернем ответ
                return response
                
            except requests.RequestException as e:
                if attempt < self.max_retries - 1:  # Если это не последняя попытка
                    delay = retry_delay * (attempt + 1) + random.uniform(1, 3)
                    print(f"Ошибка соединения: {e}. Повторная попытка через {delay:.2f} сек")
                    time.sleep(delay)
                else:
                    raise  # Если все попытки исчерпаны, вызываем исключение
        
        # Если все попытки исчерпаны и мы всё еще получаем 418, создаем пустой ответ
        print(f"Все попытки исчерпаны, API продолжает возвращать 418. Пропускаем запрос.")
        return None

    def parse(self) -> List[NewsArticle]:
        news_list = []
        
        try:
            while self.found_news_on_page:
                try:
                    self.search_params["from"] = self.current_offset
                    
                    # Использование метода с повторными попытками
                    response = self._make_request_with_retry(self.search_params)
                    
                    # Проверка результата запроса
                    if response is None:
                        print("Не удалось получить ответ после всех попыток. Переходим к следующей странице.")
                        self.current_offset += self.limit
                        continue
                    
                    # Проверка на успешный ответ
                    if response.status_code != 200:
                        print(f"Error: Vedomosti returned status code {response.status_code}")
                        break
                        
                    # Проверяем, что ответ содержит JSON
                    if not response.text.strip():
                        print("Error: Empty response from Vedomosti")
                        break
                        
                    # Безопасный парсинг JSON
                    try:
                        resp = response.json()
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
                        print(f"Response content: {response.text[:100]}...")
                        break
                        
                    # Проверяем структуру ответа
                    if "found" not in resp or not isinstance(resp["found"], list):
                        print(f"Unexpected response format: 'found' key missing or not a list")
                        break
                        
                    # Обработка новостей
                    for item in resp["found"]:
                        try:
                            if "source" not in item or not item["source"]:
                                continue
                                
                            source = item["source"]
                            
                            # Проверяем необходимые поля
                            if not all(key in source for key in ["url", "title", "boxes", "published_at"]):
                                continue
                                
                            # Формируем объект новости
                            news_list.append(NewsArticle(
                                url=source["url"],
                                title=self.clean_text(source["title"]),
                                body=self.clean_text(source["boxes"]),
                                date=self._parse_date(source["published_at"]),
                                parser=self.name
                            ))
                        except Exception as e:
                            print(f"Error processing article: {e}")
                            continue
                    
                    # Если никаких новостей не найдено или это последняя страница
                    self.found_news_on_page = len(resp["found"]) > 0
                    
                    # Если стандартная пауза между запросами
                    delay = random.uniform(1, 2)  # Случайная пауза от 1 до 3 секунд
                    print(f"Получено {len(resp['found'])} новостей. Пауза {delay:.2f} сек перед следующим запросом.")
                    time.sleep(delay)
                    
                    # Увеличиваем смещение для следующей страницы
                    self.current_offset += self.limit
                    
                except requests.RequestException as e:
                    print(f"Request exception: {e}")
                    time.sleep(2)  # Подождем дольше в случае ошибки
                    break
                    
        except Exception as e:
            print(f"General exception in Vedomosti parser: {e}")
            
        return news_list
