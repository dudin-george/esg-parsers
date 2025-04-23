from scraper import Scraper 

if __name__ == "__main__":
    scraper = Scraper(max_workers=3)
    output_file = scraper.process()
    print(f"Parsing complete! Results saved to: {output_file}")
