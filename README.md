# ESG News Parser

A specialized tool for collecting and analyzing ESG (Environmental, Social, and Governance) related news from Russian media sources.

## Overview

This tool automatically scrapes, parses, and processes news articles from major Russian news sources (Vedomosti, Kommersant, Forbes) based on company names and date ranges. It's designed to help researchers and analysts gather ESG-related news for analysis.

## Why Use This Tool

- **Automated Data Collection**: Eliminates manual searching and copying of news articles
- **Structured Output**: Provides consistent TSV (Tab-Separated Values) format for further analysis
- **Multi-source Coverage**: Pulls data from multiple reputable news sources
- **Configurable Searches**: Search by company name and date range
- **Concurrency**: Efficiently processes multiple searches in parallel

## Installation

### Prerequisites

- Python 3.8 or higher
- pip or poetry (for dependency management)

### Setup

1. Clone the repository:
   ```
   git clone <repository-url>
   cd esg-parsers
   ```

2. Install dependencies using Poetry:
   ```
   poetry install
   ```

   Or with pip:
   ```
   pip install -r requirements.txt
   ```

## How to Use

### Step 1: Configure Search Requests

Create or edit the `esg_parsers/data/request.csv` file with the following format:
```
CompanyName,YY,TRUE,Новости
```

For example:
```
Газпром,22,TRUE,Новости
Роснефть,23,TRUE,Новости
```

The fields represent:
- Company name
- Year (two-digit format)
- Whether to include in search (must be TRUE)
- Source type (must be "Новости")

### Step 2: Run the Parser

Execute the main script:

```
python -m esg_parsers.main
```

### Step 3: Access Results

After processing completes, the script will output the location of the results file. Results are saved in:
- Temporary files during processing: `esg_parsers/data/parse_run_TIMESTAMP/`
- Final merged output: `esg_parsers/data/news_TIMESTAMP.csv`

### Output Format

The output files use **Tab-Separated Values (TSV)** format rather than regular CSV. This is important to know when importing the data into other tools:

- When importing into Excel or other spreadsheet software, select "Tab" as the delimiter
- When using pandas, specify `sep='\t'` in the `read_csv` function
- The file extension remains `.csv` for backward compatibility, but the content format is TSV

This format was chosen to avoid conflicts with semicolons that might appear in article content.

## How It Works

1. **Request Reading**: The tool reads company and date range information from the request.csv file
2. **Concurrent Processing**: Multiple parsers run simultaneously for different company/source combinations
3. **Source-specific Parsing**: Each news source has a custom parser that navigates the source's structure
4. **Data Collection**: Articles are collected, cleaned, and stored in a structured format
5. **Results Merging**: All temporary results are combined into a single TSV output file

## Configuration Options

- **Concurrency**: Modify `max_workers` parameter when initializing the Scraper (default: 3)
- **Date Ranges**: By default, the tool searches for the entire year specified in request.csv
- **News Sources**: Currently supports Vedomosti, Kommersant, and Forbes

## Troubleshooting

- **Rate Limiting**: If you encounter HTTP 418 errors, the script will automatically retry with increasing delays
- **Empty Results**: Verify company spelling matches exactly how it appears in news sources
- **Parse Errors**: Check the console output for specific error messages during parsing

## Adding New Sources

To add a new news source parser:
1. Create a new parser class in `esg_parsers/parsers/` inheriting from BaseParser or SuperBaseParser
2. Implement the required methods (search_news, parse_article or parse)
3. Register the parser in the Scraper class

## License

[Your License Information]