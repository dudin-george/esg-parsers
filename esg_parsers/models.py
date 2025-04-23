from typing import List, NamedTuple
from datetime import datetime

class CompanyDateRange(NamedTuple):
    company: str
    start_date: datetime
    end_date: datetime

class NewsArticle(NamedTuple):
    url: str
    title: str  
    body: str
    date: datetime  
    parser: str