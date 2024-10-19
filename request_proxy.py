"""
 main ebay search script
"""

# Standard Imports
import re
import asyncio
import functools
import json
import time
import code
import signal
import traceback
from typing import Any, TypedDict

# Third Party Imports
import requests
from bs4 import BeautifulSoup

# First Party Imports
from bs4_test import extract_item_details, ListingDescription
from async_proxy import make_multiple_requests
from valuation import (
    calculate_listing_value_re,
    create_accessory_categories,
    ListingValue,
    ItemValuationParams,
)
from send_email import send_email_self

PROXY = "brd.superproxy.io"
PORT = 22225
# shared IP proxy
USER_SHARED = "brd-customer-hl_be059f69-zone-datacenter_proxy1-country-us"
PASSWORD_SHARED = "SUH5JYHPEGJ2"
# FIXED IP proxy
USER = "brd-customer-hl_be059f69-zone-datacenter_proxy_usa"
PASSWORD = "11uaxe2c3s46"


class AccessoryCategory(TypedDict):
    """
    A dictionary format representing search strings and their associated $ values
    (For type annotation purposes)
    """

    aliases: list[str]
    val: float


def exit_to_repl(_: Any, frame: Any) -> None:
    """
    used to access the REPL on ctrl-c
    """
    # Start the interactive console
    locals_in_main = frame.f_back.f_locals
    items = locals_in_main["items"]
    laptop_valuation = locals_in_main["laptop_valuation"]
    # serialize_items(items, f"{sanitize_filename('new')}_items_{time_ms()}.json")
    calculate_listing_value_re(items, laptop_valuation, printall=True)
    code.interact(local=locals_in_main)


def benchmark(func: Any) -> Any:
    """
    Benchmark a function in ms using @benchmark decorator
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time_ms = (end_time - start_time) * 1000  # Convert to milliseconds
        print(
            f"Function '{func.__name__}' execution time: {execution_time_ms:.2f} milliseconds"
        )
        return result

    return wrapper


def time_ms() -> int:
    """
    Relative time in ms (integer)
    """
    return time.time_ns() // 1_000_000


def extract_country_from_response(response_json: str) -> str:
    """
    Extracts the country from the JSON HTTP response.

    Args:
    - response_json (str): JSON string containing the response data.

    Returns:
    - str: The country extracted from the response, or None if not found.
    """
    try:
        # Parse the JSON string
        response_data = json.loads(response_json)

        # Extract country from response data
        country: str = response_data.get("country")

        return country
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {str(e)}")
        return "JSONDecodeError"
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return "Exception"


def download_webpage_with_proxy(
    url: str,
    proxy: str,
    port: int,
    user: str,
    password: str,
    language: str = "en-US,en;q=0.5",
    use_proxy: bool = False,
) -> str:
    """
    Downloads a webpage using the provided proxy settings.

    Args:
    - url (str): The URL of the webpage to download.
    - proxy (str): The proxy server address.
    - port (int): The port number of the proxy server.
    - user (str): The username for proxy authentication.
    - password (str): The password for proxy authentication.
    - language (str): The language preference to include in the request headers.
    - use_proxy (bool): Use the provided proxy settings or just request using local network.
    Returns:
    - str: The content of the webpage if the request is successful, None otherwise.
    """
    timeout_sec = 10  # 10 seconds
    # Set up proxy configuration
    proxy_url = f"{proxy}:{port}"
    proxy_user = user
    proxy_pass = password

    proxies = {
        "http": f"http://{proxy_user}:{proxy_pass}@{proxy_url}",
        "https": f"https://{proxy_user}:{proxy_pass}@{proxy_url}",
    }

    # Request headers including Accept-Language
    headers = {"Accept-Language": language}

    try:
        if use_proxy:
            response = requests.get(
                url, proxies=proxies, headers=headers, timeout=timeout_sec
            )
        else:
            # Make request with proxy settings and headers
            response = requests.get(url, headers=headers, timeout=timeout_sec)

        # Check if request was successful (status code 200)
        if response.status_code == 200:
            return response.text
        print(f"Failed to fetch URL. Status code: {response.status_code}")
        return ""
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return ""


def desc_url_to_id(url: str) -> str:
    """
    url (str): an ebay listing url with ID at the end, ie: ebay.com/itm/XXXXXXXXX
    returns (str): listing ID, ie XXXXXXXXX
    """
    return url.split("/")[-1]


def item_desc_ready_callback(
    success: bool, url: str, body: str, items: dict[str, ListingDescription]
) -> None:
    """
    Item Description Loaded callback. Called from async MultiSessionRetriever
    Adds/Updates item.description field to ListingDescription
    """
    item_id = desc_url_to_id(url)
    item = items[item_id]
    # print (f"Item: {item.title}")
    if success:
        # print(f"Item Url: {url}, Body: {body[:100]}...")
        desc_soup = BeautifulSoup(body, "html.parser")
        desc_text = desc_soup.get_text() if desc_soup else ""
        item.description = desc_text
    else:
        # print(f"Failed getting description for: {item.title}")
        item.description = ""


def get_search_page(
    search: str, n: int, use_shared_proxy: bool = False
) -> dict[str, ListingDescription]:
    """
    Get items from the nth search page for given search term
    """
    url_ebaysearch = (
        f"https://www.ebay.com/sch/i.html?"
        f"_from=R20&_nkw={search}&_sacat=0&_sop=10&rt=nc&LH_BIN=1&_ipg=60&_pgn={n}"
    )
    if use_shared_proxy:
        webpage_content = download_webpage_with_proxy(
            url_ebaysearch, PROXY, PORT, USER_SHARED, PASSWORD_SHARED
        )
    else:
        webpage_content = download_webpage_with_proxy(
            url_ebaysearch, PROXY, PORT, USER, PASSWORD
        )
    if not webpage_content:
        print("Failed to download webpage.")
        return {}
    # Assuming webpage_content contains your HTML content
    sorted_item_details = extract_item_details(webpage_content)
    item_urls = []
    for item_id, item in sorted_item_details.items():
        if not item_id or not item_id.isdigit():
            print(f"item id is not a digit {item_id}")
            continue
    l = lambda success, url, body: item_desc_ready_callback(
        success, url, body, sorted_item_details
    )
    item_urls = [item.description_url for item in sorted_item_details.values()]
    if use_shared_proxy:
        asyncio.run(
            make_multiple_requests(
                item_urls, l, USER_SHARED, PASSWORD_SHARED, use_proxy=True
            )
        )
    else:
        asyncio.run(make_multiple_requests(item_urls, l, USER, PASSWORD))
        # ebay_description = download_webpage_with_proxy(url_ebay_desc, PROXY, PORT, USER, PASSWORD)
        # desc_soup = BeautifulSoup(ebay_description, 'html.parser')
        # print(desc_soup.get_text() if desc_soup else None)
    return sorted_item_details


def get_first_n_pages(search: str, n: int) -> dict[str, ListingDescription]:
    """
    Gets items from the first n search pages with search string
    """
    print(f"Get First {n} Pages for {search}")
    items = {}
    for i in range(n):
        items.update(get_search_page(search, i))
    return items


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for disk writes
    """
    # Define a regular expression pattern to match invalid characters
    invalid_chars = r'[\\/:"*?<>|]'
    # Replace invalid characters with underscores
    sanitized_filename = re.sub(invalid_chars, "_", filename)
    return sanitized_filename


def key_collision(d1: dict[Any, Any], d2: dict[Any, Any]) -> bool:
    """
    Check 2 dictionaries for any key collisions
    """
    return any(key in d2 for key in d1)


# Define item valuation parameters
params: dict[str, list[AccessoryCategory]] = {
    "SSD": [
        {"aliases": ["128 GB"], "val": 0},
        {"aliases": ["256 GB"], "val": 10},
        {"aliases": ["512 GB"], "val": 20},
        {"aliases": ["1 TB"], "val": 40},
    ],
    "RAM": [
        {"aliases": ["8 GB"], "val": 0},
        {"aliases": ["16 GB"], "val": 10},
        {"aliases": ["32 GB"], "val": 30},
        {"aliases": ["64 GB"], "val": 60},
    ],
    "CPU": [
        {
            "aliases": [
                "i7-1195G7",
                "i7-1180G7",
                "i7-1160G7",
                "i7-1165G7",
                "i7-1185G7",
                "i5-1130G7",
                "i5-1135G7",
                "i5-1140G7",
                "i5-1145G7",
                "i5-1155G7",
                "i5-11260H",
                "i5-11300H",
                "i5-11320H",
            ],
            "val": 125,
        },  # medium power 11th gen
        {
            "aliases": [
                "i7-1195G7",
                "i7-1180G7",
                "i7-1160G7",
                "i7-1165G7",
                "i7-1185G7",
                "i5-1130G7",
                "i5-1135G7",
                "i5-1140G7",
                "i5-1145G7",
                "i5-1155G7",
                "i5-11260H",
                "i5-11300H",
                "i5-11320H",
            ],
            "val": 125,
        },  # medium power 11th gen
        {
            "aliases": [
                "i7-11600H",
                "i7-11390H",
                "i7-11370H",
                "i7-11375H",
                "i5-11400H",
                "i5-11500H",
            ],
            "val": 200,
        },  # high power 11th gen
        {"aliases": ["i7-11800H", "i7-11850H"], "val": 250},
        {"aliases": ["i9-11900H", "i9-11950H", "i9-11980HK"], "val": 250},
        {
            "aliases": [
                "i7-11700",
                "i7-11700F",
                "i7-11700K",
                "i7-11700KF",
                "i7-11700T",
                "i5-11400",
                "i5-11400F",
                "i5-11400T",
                "i5-11500",
                "i5-11500T",
                "i5-11600",
                "i5-11600K",
                "i5-11600KF",
                "i5-11600T",
            ],
            "val": 200,
        },  # desktop 11th gen
        {
            "aliases": [
                "i3-1220P",
                "i3-1215U",
                "Pentium 8505",
                "Celeron 7305",
                "i3-1210U",
                "Pentium 8500",
                "Celeron 7300",
            ],
            "val": 10,
        },  # low power 12th gen
        {
            "aliases": [
                "i5-1235U",
                "i5-1245U",
                "i7-1255U",
                "i7-1265U",
                "i7-1260U",
                "i7-1250U",
                "i5-1240U",
                "i5-1230U",
            ],
            "val": 200,
        },  # mid power 12th gen
        {
            "aliases": ["i7-1280P", "i7-1270P", "i7-1260P", "i5-1250P", "i5-1240P"],
            "val": 200,
        },
        {
            "aliases": ["i5-12600HX", "i5-12600H", "i5-12500H", "i5-12450H"],
            "val": 225,
        },  # high power 12th gen
        {
            "aliases": [
                "i7-12850HX",
                "i7-12800HX",
                "i7-12800H",
                "i7-12700H",
                "i7-12650H",
            ],
            "val": 250,
        },
        {
            "aliases": ["i9-12950HX", "i9-12900HX", "i9-12900HK", "i9-12900H"],
            "val": 300,
        },
        {
            "aliases": ["i3-1315U", "i3-1305U", "Processor U300"],
            "val": 10,
        },  # low power 13th gen
        {
            "aliases": ["i7-1365U", "i7-1355U", "i5-1345U", "i5-1335U", "i5-1334U"],
            "val": 300,
        },  # medium power 13th gen
        {"aliases": ["i7-1370P", "i7-1360P", "i5-1350P", "i5-1340P"], "val": 300},
        {
            "aliases": [
                "i5-13600HX",
                "i5-13500HX",
                "i5-13450HX",
                "i5-13600H",
                "i5-13505H",
                "i5-13500H",
                "i5-13420H",
            ],
            "val": 350,
        },  # high power 13th gen
        {
            "aliases": [
                "i7-13850HX",
                "i7-13700HX",
                "i7-13650HX",
                "i7-13800H",
                "i7-13705H",
                "i7-13700H",
                "i7-13620H",
            ],
            "val": 375,
        },
        {
            "aliases": [
                "i9-13980HX",
                "i9-13950HX",
                "i9-13900HX",
                "i9-13900HK",
                "i9-13905H",
                "i9-13900H",
            ],
            "val": 400,
        },
    ],
    "GPU": [
        {
            "aliases": ["GTX 1050", "GTX 1050 Ti", "RX 560", "GTX 1630", "GTX 970"],
            "val": 100,
        },
        {
            "aliases": [
                "GTX 1060",
                "GTX 1650",
                "RX 6400",
                "RX 570",
                "GTX 980",
                "RX 6500",
                "RX 5500",
                "RX 580",
                "GTX 980Ti",
                "RX 590",
            ],
            "val": 150,
        },
        {"aliases": ["GTX 1070", "GTX 1660", "GTX 1080"], "val": 175},
        {
            "aliases": [
                "GTX 1660 Ti",
                "GTX 1660 Super",
                "GTX 1070 Ti",
                "RX 5600",
                "RX 5700",
                "GTX 1080 Ti",
            ],
            "val": 200,
        },
        {"aliases": ["RTX 3050", "RTX 2060", "RX 6600"], "val": 225},
        {"aliases": ["RTX 3060", "RTX 2070", "RX 5700"], "val": 250},
        {"aliases": ["RTX 2070 Super", "RX 6700"], "val": 300},
        {
            "aliases": [
                "RTX 2080",
                "RTX 4060",
                "RTX 2080 Super",
                "RTX 3060 Ti",
                "RX 7600",
                "RTX 2080 Ti",
                "RX 6800",
                "RX 6750",
                "RX 7700",
            ],
            "val": 300,
        },
        {
            "aliases": ["RTX 3070", "RTX 4060 Ti", "RTX 3070 Ti", "RX 6900", "RX 7800"],
            "val": 400,
        },
        {"aliases": ["RTX 3080", "RTX 4070", "RTX 3080 Ti", "RX 7900"], "val": 450},
        {
            "aliases": [
                "RTX 3090",
                "RTX 3090 Ti",
                "RTX 4070 Super",
                "RTX 4070 Ti",
                "RTX 4070 Ti Super",
            ],
            "val": 500,
        },
        {"aliases": ["RTX 4080", "RTX 4080 Super", "RTX4 4090"], "val": 500},
    ],
    "Damage": [
        {
            "aliases": [
                "Broken",
                "Cracked",
                "Damaged",
                "No Boot",
                "No Display",
                "Not Working",
                "For Parts",
                "For Repair",
                "Parts",
                "Repair",
                "No Screen",
            ],
            "val": -100,
        }
    ],
    "Missing": [
        {
            "aliases": [
                "No SSD",
                "No Battery",
                "No Drive",
                "No Batt",
                "Bad Battery",
                "Bad Batt",
                "No HD",
            ],
            "val": -50,
        },
        {"aliases": ["No Charger", "No OS"], "val": -10},
    ],
    "Replacement": [{"aliases": ["Motherboard", "Replacement"], "val": -400}],
}


def start_main_loop(
    items: dict[str, ListingDescription],
    laptop_valuation: ItemValuationParams,
    first_n_pages: int = 1,
) -> None:
    """
    Starts the main loop. Collects item ListingDescriptions and checks valuation.
    Notifies when an item has (price < value).
    Item value is calculated using regex matching of item title/description
    with calculate_listing_value_re().
    """
    # Create item valuation parameters

    items.update(get_first_n_pages("Laptop", first_n_pages))

    use_shared_proxy = False
    matched_items = {}
    while 1:
        new_items: dict[str, ListingDescription] = {}
        unique_items = {}
        flag_wait_503 = False
        while not key_collision(new_items, items) and not flag_wait_503:
            page_n = 1
            pre_len = len(items)
            for search in laptop_valuation.get_item_names():
                # print (f"Searching {search}, page {page_n}")
                search_results_items = get_search_page(search, page_n, use_shared_proxy)
                if len(search_results_items) == 0:
                    flag_wait_503 = True
                    break
                new_items.update(search_results_items)
            original_keys = set(items.keys())
            items.update(new_items)
            added_len = len(items) - pre_len
            if added_len == 0:
                continue
            unique_items.update(
                {key: value for key, value in items.items() if key not in original_keys}
            )
            # Print new items
            # item: ListingDescription
            # for key, item in unique_items.items():
            # print(f"New: {item.date}, {key}, {item.price + item.ship_price}, {item.title}")
            page_n += 1
        re_vals: list[ListingValue] = calculate_listing_value_re(
            items, laptop_valuation, condition_exclude=["Parts Only"]
        )

        item_value: ListingValue
        for item_value in re_vals:
            if item_value.get_value() > 100 and item_value.delta_value() < 50:
                if not item_value.get_item_id() in matched_items:
                    matched_items[item_value.get_item_id()] = item_value
                    subject = f"Deal: {item_value.get_title()}"
                    message = (
                        f"Item {item_value.get_title()}\n"
                        f"{item_value.get_url()}\n"
                        f"Delta Value: {item_value.delta_value()}, "
                        f"Price: {item_value.get_price()}\n\n"
                        f"{str(item_value.listing)}\n\n"
                        f"{item_value.get_accs()}"
                    )
                    send_email_self(subject, message)
                    print(item_value, "\a")

        if flag_wait_503 is True and use_shared_proxy:
            print("Wait 90s, Search Results Invalid on Shared Proxy")
            time.sleep(90)
        elif flag_wait_503 is True and not use_shared_proxy:
            print("Wait 15s, Requests failed, switching to shared proxy")
            time.sleep(15)
            use_shared_proxy = True
        else:
            print("Wait 45s, Requests succeeded")
            time.sleep(45)
            use_shared_proxy = False


def main() -> None:
    """
    Main Function: Executes the start_main_loop function which does the listing search
    continuously.
    """
    # Register the signal handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, exit_to_repl)

    # Example usage:
    url = "https://lumtest.com/myip.json"

    webpage_content = download_webpage_with_proxy(url, PROXY, PORT, USER, PASSWORD)
    country = extract_country_from_response(webpage_content)
    if webpage_content:
        print(webpage_content)
    else:
        print("Failed to download webpage.")
    if country:
        print(country)

    try:
        items: dict[str, ListingDescription] = {}
        search_names = ['Laptop 14"', 'Laptop 13"', "Laptop"]
        laptop_valuation = ItemValuationParams(
            search_names, 0, create_accessory_categories(params)
        )
        attempts = 0
        max_attempts = 10
        delay_s = 30
        while attempts < max_attempts:
            try:
                start_main_loop(items, laptop_valuation)
                return
            except Exception as e:
                exc_string = traceback.format_exc()
                subject = "Exceptional!"
                message = f"{exc_string}"
                send_email_self(subject, message)
                print(
                    f"Sleeping {delay_s} because attempt {attempts + 1} failed:",
                    exc_string,
                )
                print(str(e))
                attempts += 1
                time.sleep(delay_s)  # Delay before retrying
    except KeyboardInterrupt:
        # This block will not execute because KeyboardInterrupt is caught by the signal handler
        pass


if __name__ == "__main__":
    main()
