import os
import json
import csv
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Union
import concurrent.futures
from tqdm import tqdm
import threading
from models import NewsArticle, CompanyDateRange
from utils.csv import read_news_requests
from parsers.forbes import ForbesParser
from parsers.vedomosti import VedomostiParser
from parsers.kommersant import KommersantParser


class Scraper:
    """
    Scraper class that coordinates the parsing process:
    - Reads requests from CSV
    - Runs appropriate parsers for each company
    - Stores results in temporary files
    - Merges results from all parsers
    """
    
    def __init__(self, max_workers: int = 3):
        """
        Initialize the scraper
        
        Args:
            max_workers: Maximum number of concurrent parser workers
        """
        self.max_workers = max_workers
        self.parsers = {
            "Forbes": ForbesParser,
            "Vedomosti": VedomostiParser,
            "Kommersant": KommersantParser
        }
        self.temp_dir = None
        self._progress_lock = threading.Lock()
        
    def read_requests(self) -> List[CompanyDateRange]:
        """
        Read news requests from CSV file
        
        Returns:
            List of CompanyDateRange objects
        """
        return read_news_requests()
    
    def _run_parser(self, parser_name: str, company_range: CompanyDateRange) -> List[NewsArticle]:
        """
        Run a specific parser for a company
        
        Args:
            parser_name: Name of the parser to use
            company_range: Company and date range to parse
            
        Returns:
            List of parsed news articles
        """
        parser_class = self.parsers.get(parser_name)
        if not parser_class:
            print(f"Parser {parser_name} not implemented")
            return []
            
        parser = parser_class(company_range)
        return parser.parse()
    
    def _format_date(self, date_obj: Union[datetime, str]) -> str:
        """Safely format a date object or string to a string format"""
        if isinstance(date_obj, datetime):
            return date_obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(date_obj, str):
            # If it's already a string, return as is
            return date_obj
        return str(date_obj)  # Fallback
    
    def _escape_text_for_csv(self, text: str) -> str:
        """
        Обработка текста для безопасного хранения в CSV
        - Удаляет символы, которые могут вызвать проблемы с CSV
        """
        if not text:
            return ""
        
        # Заменяем опасные для CSV символы
        # Это дополнительная защита, т.к. csv.writer должен экранировать
        # символы сам, но иногда он не справляется с некоторыми случаями
        text = text.replace('\r\n', ' ').replace('\n', ' ')
        
        return text

    def _save_temp_results(self, articles: List[NewsArticle], company_range: CompanyDateRange, parser_name: str) -> str:
        """
        Save parsed results to a temporary CSV file
        
        Args:
            articles: List of parsed articles
            company_range: Company and date range information
            parser_name: Parser name
            
        Returns:
            Path to the saved temporary file
        """
        if not self.temp_dir:
            # Create a timestamped folder in data directory for this parse run
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.temp_dir = os.path.join(data_dir, f"parse_run_{timestamp}")
            os.makedirs(self.temp_dir, exist_ok=True)
        
        # Safely get dates as strings    
        start_date_str = self._format_date(company_range.start_date)
        end_date_str = self._format_date(company_range.end_date)
        
        filename = f"{company_range.company}_{parser_name}_{start_date_str}_{end_date_str}.csv"
        # Clean filename from problematic characters
        filename = filename.replace(':', '_').replace(' ', '_')
        filepath = os.path.join(self.temp_dir, filename)
        
        try:
            with open(filepath, "w", encoding="utf-8", newline='') as f:
                # Настраиваем CSV writer с правильными параметрами для экранирования
                writer = csv.writer(
                    f, 
                    delimiter='\t',  # Используем табуляцию вместо точки с запятой
                    quotechar='"',  # Используем двойные кавычки для экранирования
                    quoting=csv.QUOTE_ALL  # Всегда экранировать все поля
                )
                
                # Write header - добавляем столбец keyword
                writer.writerow(['link', 'pubdate', 'article_body', 'title', 'parser', 'keyword'])
                
                # Write data
                company_name = company_range.company if hasattr(company_range, 'company') else str(company_range)
                for article in articles:
                    # Safely format date
                    pubdate = self._format_date(article.date)
                    
                    # Обрабатываем текст перед сохранением
                    title = self._escape_text_for_csv(article.title)
                    body = self._escape_text_for_csv(article.body)
                    
                    writer.writerow([
                        article.url,
                        pubdate,
                        body,
                        title,
                        article.parser,
                        company_name  # Добавляем название компании в столбец keyword
                    ])
                
            return filepath
        except Exception as e:
            print(f"Error saving results to {filepath}: {e}")
            # Create an empty file to avoid further errors
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("Error during parsing")
            return filepath

    def run_parsers(self, requests: List[CompanyDateRange] = None) -> List[str]:
        """
        Run all parsers for the given requests
        
        Args:
            requests: List of company/date range requests. If None, reads from CSV.
            
        Returns:
            List of temporary file paths
        """
        if requests is None:
            requests = self.read_requests()
            
        temp_files = []
        temp_files_lock = threading.Lock()
        
        # Calculate total number of parsing tasks
        total_tasks = len(requests) * len(self.parsers)
        print(f"Starting {total_tasks} parsing tasks...")
        
        # Set up progress bar
        progress = tqdm(total=total_tasks, desc="Parsing articles")
        
        def process_parser_result(company_range, parser_name, future):
            """Process the result of a parser task and update progress"""
            try:
                articles = future.result()
                company_name = company_range.company if hasattr(company_range, 'company') else str(company_range)
                status_msg = f"{company_name} ({parser_name}): "
                
                if articles:
                    temp_path = self._save_temp_results(articles, company_range, parser_name)
                    with temp_files_lock:
                        temp_files.append(temp_path)
                    status_msg += f"{len(articles)} articles"
                else:
                    status_msg += "0 articles"
                
                # Update progress
                with self._progress_lock:
                    progress.update(1)
                    progress.set_description_str(status_msg)
                    
            except Exception as e:
                company_name = company_range.company if hasattr(company_range, 'company') else str(company_range)
                error_msg = f"Error processing {company_name} with {parser_name}: {str(e)}"
                with self._progress_lock:
                    progress.write(error_msg)
                    progress.update(1)
        
        # Use ThreadPoolExecutor for parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Dictionary to track futures
            future_to_task = {}
            
            # Submit all tasks to the executor
            for company_range in requests:
                for parser_name in self.parsers:
                    future = executor.submit(self._run_parser, parser_name, company_range)
                    future_to_task[future] = (company_range, parser_name)
            
            # Process futures as they complete
            for future in concurrent.futures.as_completed(future_to_task):
                company_range, parser_name = future_to_task[future]
                process_parser_result(company_range, parser_name, future)
                
        # Close progress bar
        progress.close()
        
        print(f"Completed parsing. Generated {len(temp_files)} temporary files.")
        return temp_files
    
    def merge_results(self, temp_files: List[str]) -> str:
        """
        Merge all temporary CSV files into a single consolidated CSV file
        
        Args:
            temp_files: List of temporary file paths
            
        Returns:
            Path to the consolidated output file
        """
        if not self.temp_dir:
            raise ValueError("No temporary directory exists. Run parsers first.")
            
        # Create merged results file in the same temp directory
        merged_file = os.path.join(self.temp_dir, "merged_results.csv")
        
        # Count total files for progress tracking
        total_files = len(temp_files)
        print(f"Merging {total_files} result files...")
        
        # Track overall stats
        total_articles = 0
        
        # Create merged CSV with headers
        with open(merged_file, 'w', encoding='utf-8', newline='') as outfile:
            # Настраиваем CSV writer с правильными параметрами для экранирования
            writer = csv.writer(
                outfile, 
                delimiter='\t',  # Используем табуляцию вместо точки с запятой
                quotechar='"',  # Используем двойные кавычки для экранирования
                quoting=csv.QUOTE_ALL  # Всегда экранировать все поля
            )
            
            # Write header - включая столбец keyword
            writer.writerow(['link', 'pubdate', 'article_body', 'title', 'parser', 'keyword'])
            
            # Use a simpler progress bar for file merging
            pbar = tqdm(temp_files, total=total_files, desc="Merging files")
            
            # Process each file
            for temp_file in pbar:
                try:
                    filename = os.path.basename(temp_file)
                    pbar.set_description(f"Processing {filename}")
                    
                    # Skip empty or error files
                    if os.path.getsize(temp_file) < 10:  # Too small to be valid
                        pbar.write(f"Skipping likely invalid file: {temp_file}")
                        continue
                    
                    with open(temp_file, 'r', encoding='utf-8', newline='') as infile:
                        # Настраиваем CSV reader с теми же параметрами
                        reader = csv.reader(
                            infile, 
                            delimiter='\t',  # Используем табуляцию вместо точки с запятой
                            quotechar='"',
                            quoting=csv.QUOTE_ALL
                        )
                        
                        # Safely skip header - handle case where file may be empty or corrupted
                        try:
                            next(reader, None)
                        except Exception as e:
                            pbar.write(f"Error reading header in {temp_file}: {e}")
                            continue
                        
                        # Write all rows
                        file_articles = 0
                        for row in reader:
                            try:
                                # If row has all expected columns (теперь ожидаем 6 колонок с keyword)
                                if len(row) >= 6:
                                    writer.writerow(row)
                                    file_articles += 1
                                # Если нет keyword в исходном файле (для совместимости со старыми файлами)
                                elif len(row) == 5:
                                    # Добавляем пустой keyword
                                    row.append("")
                                    writer.writerow(row)
                                    file_articles += 1
                                # Если меньше 5 колонок, пропускаем строку
                                else:
                                    pbar.write(f"Skipping row with insufficient columns: {row}")
                            except Exception as e:
                                pbar.write(f"Error writing row: {str(e)[:100]}")
                                continue
                        
                        total_articles += file_articles
                        pbar.set_postfix(articles=file_articles)
                        
                except Exception as e:
                    pbar.write(f"Error processing {temp_file}: {e}")
        
        # Report statistics
        print(f"Successfully merged {total_articles} articles from {total_files} files into {merged_file}")
        return merged_file
        
    def process(self, output_dir: str = None) -> str:
        """
        Execute the complete scraping process:
        1. Read requests
        2. Run parsers
        3. Merge results
        
        Args:
            output_dir: Directory to save the output file (unused, keeping for compatibility)
            
        Returns:
            Path to the saved output file
        """
        requests = self.read_requests()
        temp_files = self.run_parsers(requests)
        output_file = self.merge_results(temp_files)
        
        print(f"All parsing tasks completed. Results saved to: {output_file}")
        return output_file
