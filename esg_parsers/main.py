from parsers.forbes import ForbesParser
from parsers.vedomosti import VedomostiParser
from parsers.kommersant import KommersantParser
from datetime import datetime

if __name__ == "__main__":
    parser = KommersantParser("Whoosh", datetime(2024, 1, 1), datetime(2024, 2, 28))
    print(parser.parse()[:3])
