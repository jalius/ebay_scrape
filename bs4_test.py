from typing import Any
from datetime import datetime
from bs4 import BeautifulSoup

def is_float(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False

class ListingDescription:
    def __init__(self, item_id: str, title: str, condition: str, price: float, free_ship: bool, ship_price: float, bidding: bool, url: str, date: datetime):
        self.item_id = item_id
        self.title = title
        self.condition = condition
        self.price = price
        self.free_ship = free_ship
        self.ship_price = ship_price
        self.bidding = bidding
        self.url = url
        self.date = date
        self.description_url = f"https://vi.vipr.ebaydesc.com/itmdesc/{item_id}"
        self.description = ""
    def __str__(self) -> str:
        return str(self.serialize())
    def __repr__(self) -> str:
        return f"ebay listing: {self.item_id}"
    def serialize(self) -> dict[str, str|float|bool]:
        return {
            "item_id": self.item_id,
            "title": self.title,
            "condition": self.condition,
            "price": self.price,
            "free_ship": self.free_ship,
            "ship_price": self.ship_price,
            "bidding": self.bidding,
            "url": self.url,
            "date": self.date.isoformat(),  # Convert datetime to ISO 8601 format
            "description_url": self.description_url,
            "description": self.description
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> 'ListingDescription':
        return cls(
            data["item_id"],
            data["title"],
            data["condition"],
            data["price"],
            data["free_ship"],
            data["ship_price"],
            data["bidding"],
            data["url"],
            datetime.fromisoformat(data["date"])  # Convert ISO 8601 format to datetime
        )

def extract_item_details(html_content: str) -> dict[str, ListingDescription]:
    """
    Extracts details of all items found in the HTML content.

    Args:
    - html_content (str): The HTML content containing items.

    Returns:
    - list: A list of dictionaries containing details of each item.
    """

    extracted_data: dict[str, ListingDescription] = {}

    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        items = soup.select("#srp-river-results > ul > li.s-item")

        for item in items:
            # Extract item details using item.select_one() instead of item.find()
            title_elem = item.select_one('.s-item__title')
            if not title_elem:
                print("Invalid title_elem (.s-item__title)")
                print(item)
                continue
            title = title_elem.get_text()

            condition_elem = item.select_one('.s-item__subtitle>.SECONDARY_INFO')
            if not condition_elem:
                print("Invalid condition_elem (.s-item__subtitle>.SECONDARY_INFO)")
                print(item)
                continue
            condition = condition_elem.get_text() if condition_elem else ''

            bidding = item.select_one('.s-item__bids') is not None

            price_elem = item.select_one('.s-item__price')
            if not price_elem:
                print("Invalid price_elem (.s-item__price)")
                print(item)
                continue
            price_text = price_elem.get_text()
            price_cleaned = price_text.strip('$').replace(',', '')
            if not is_float(price_cleaned):
                print(f"Price text is not a number: {price_cleaned}")
                print(item)
                continue

            price = float(price_cleaned)

            shipping_elem = item.select_one('.s-item__logisticsCost')
            ship_price: float = 0.0
            free_ship = False
            if shipping_elem: # if 
                ship_text = shipping_elem.get_text()
                free_ship = item.select_one('.s-item__freeXDays') is not None or (ship_text == "Free shipping")
                if not free_ship:
                    ship_text = ship_text.strip('+$').replace(' shipping', '').replace(' shipping estimate', '')
                    ship_price = float(ship_text) if is_float(ship_text) else 0

            url_elem = item.select_one('.s-item__link')
            if not url_elem:
                print("Invalid url_elem (.s-item__link)")
                print(item)
                continue
            
            url_href = url_elem['href']

            if not isinstance(url_href, str):
                print("Invalid url_elem href attributes")
                print(url_href)
                continue

            url = url_href.split('?')[0]

            date_elem = item.select_one('.s-item__dynamic.s-item__listingDate')
            dt_fmt = "%b-%d %H:%M"
            if not date_elem:
                print("Invalid date_elem (.s-item__dynamic.s-item__listingDate)")
                print(item)
                continue
            dt_str = date_elem.get_text() if date_elem else ''
            date = datetime.strptime(dt_str, dt_fmt).replace(year=datetime.now().year) if dt_str else datetime.min
            item_id = url.split("/")[-1]
            if not item_id.isdigit():
                print(f"Invalid item_id {item_id}")
                print(item)
                continue
            # Append item details to extracted_data list
            extracted_data[item_id] = ListingDescription(item_id, title, condition, price, free_ship, ship_price, bidding, url, date)
 

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return {}

    return extracted_data


if __name__ == "__main__":
# Read HTML content from a file
    with open('laptop_search.html', 'r', encoding='utf-8') as file:
        html_content = file.read()

    # Assuming html_content contains your HTML content
    sorted_item_details = extract_item_details(html_content)
    print(sorted_item_details)
    for item in sorted_item_details:
        print(item)
    print (len(sorted_item_details))




