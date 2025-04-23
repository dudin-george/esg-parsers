import csv
from datetime import datetime
from pathlib import Path
from typing import List
from models import CompanyDateRange


def read_news_requests() -> List[CompanyDateRange]:
    """
    Reads request.csv file and returns filtered list of companies with date ranges
    for news monitoring.
    
    Returns:
        List of CompanyDateRange objects containing company name and date range
    """
    results = []
    csv_path = Path(__file__).parent.parent / 'data' / 'request.csv'
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            company, year, has_rating, source = row
            
            # Filter condition
            if has_rating.upper() == 'TRUE' and source == 'Новости':
                year = int('20' + year)
                results.append(CompanyDateRange(
                    company=company, 
                    start_date=datetime(year=year, month=1, day=1), 
                    end_date=datetime(year=year, month=12, day=31)))
    

    return results

