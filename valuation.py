"""
This module calculates valuation of items using regex matching on title and description
"""
import re
from typing import TypedDict
from bs4_test import ListingDescription

#Class Definitions (AccOpt, AccCat, ItemValuationParams)

class AccessoryCategory(TypedDict):
    """
    A dictionary format representing search strings and their associated $ values
    """

    aliases: list[str]
    val: float
    multiplier: float

class AccOpt:
    def __init__ (self, aliases: list[str], val: float):
        self.aliases = aliases
        self.val = val
        self.regex = build_alias_regex(aliases)

    def get_alias_matches(self, search: str) -> list[str]:
        return self.regex.findall(search)

class AccCat:
    def __init__(self, name: str, options: list[AccOpt]):
        self.name = name
        self.acc_opts = options

    def get_all_aliases(self) -> list[str]:
        return [alias for option in self.acc_opts for alias in option.aliases]

    def get_accessory_value(self, alias: str) -> float:
        for opt in self.acc_opts:
            if alias in opt.aliases:
                return opt.val
        return 0

class ItemValuationParams:
    """
    Item valuation, including the items base value and value from any accessories 
    """
    def __init__(self,
                item_search_names: list[str],
                item_base_value: float,
                accessories: list[AccCat]):
        self.item_search_names = item_search_names
        self.item_base_value = item_base_value
        self.accessories = accessories

    def get_item_names(self) -> list[str]:
        """
        Get item names. Used as search engine input for this item
        """
        return self.item_search_names

    def get_base_value(self) -> float:
        """
        Get item base value (with no accessories)
        """
        return self.item_base_value

    def get_accessories(self) -> list[AccCat]:
        """
        Get item accessories
        """
        return self.accessories


# ListingValue Class
class ListingValue:
    """
    Represents the value of a listing; its accessory categories and their values
    """
    def __init__(self, listing: ListingDescription, value: float = 0.0):
        self.listing = listing
        self.value = value
        self.accs: dict[str, tuple[list[str], float]] = {}

    def set_value(self, value: float) -> None:
        self.value = value

    def add_accessory(self, category: str, matching_names: list[str], val: float) -> None:
        """
        Add an accessory of category. The matching names represent the accessory type,
        found by regex in listing. Val represents how much an accessory of this type is worth,
        based on the ItemValuationParams.
        """
        self.accs[category] = (matching_names, val)

    def delta_value(self) -> float:
        return self.get_price() - self.value
    def get_accs(self) -> dict[str, tuple[list[str], float]]:
        return self.accs
    def print_accs(self) -> None:
        for acc in self.accs:
            print(f"{acc}: {self.accs[acc]}, ", end="")
        if len(self.accs):
            print("")

    def get_price(self) -> float:
        return self.listing.price + self.listing.ship_price

    def get_title(self) -> str:
        return self.listing.title

    def get_url(self) -> str:
        return self.listing.url

    def get_condition(self) -> str:
        return self.listing.condition

    def get_value(self) -> float:
        return self.value
    def get_item_id(self) -> str:
        return self.listing.item_id
    def __str__(self) -> str:
        return (f"Item: {self.get_title():100.100}, "
                f"Delta Val: {self.delta_value()}, "
                f"Price: {self.get_price()}, "
                f"Value: {self.value}, "
                f"URL: {self.get_url()}")
# Utility Functions
def build_alias_regex(aliases: list[str]) -> re.Pattern[str]:
    """
    Given aliases for an accessory, builds regex pattern to match them
    """
    aliases_re = []
    for alias in aliases:
        permutations = [
                alias.replace(" ", r"\s*"),            # Replace space with optional whitespace
                alias.replace(" ", r"[\s-]?"),         # Replace space with SPACE or hyphen or none
                alias.replace("-", r"\s*"),            # Replace hyphen with optional whitespace
                ]
        aliases_re.extend(permutations)
    return re.compile(r"\b(" + "|".join(aliases_re) + r")\b", flags=re.IGNORECASE)

def create_accessory_categories(params: dict[str, list[AccessoryCategory]]) -> list[AccCat]:
    """
    Builds accessory categories from input dictionary
    """
    categories = []
    for name, options in params.items():
        acc_opts = [AccOpt(opt['aliases'], opt['val']) for opt in options]
        categories.append(AccCat(name, acc_opts))
    return categories

def calculate_listing_value_re(items: dict[str, ListingDescription],
                             val_params: ItemValuationParams,
                             condition_exclude: list[str] = ["Parts Only"],
                             min_value: int = 100,
                             printall: bool = False) -> list[ListingValue]:
    """
    Given a dictionary of itemIDs (str) and Listings, calculate item value based on input parameters
    """
    item_vals: list[ListingValue] = []
    for item in items.values():
        item_val = ListingValue(item)
        title = item.title
        desc = item.description
        value = val_params.item_base_value
        for category in val_params.accessories:
            for option in category.acc_opts:
                matches = option.get_alias_matches(title)
                matches += option.get_alias_matches(desc)
                if len(matches) > 0:
                    value += option.val
                    item_val.add_accessory(category.name, matches, option.val)
                    break # go to next accesory category
        item_val.set_value(value)
        item_vals.append(item_val)
    if printall:
        item_vals.sort(key=lambda item: item.delta_value(), reverse=True)
    for item_val in item_vals:
        if item_val.get_condition() in condition_exclude:
            continue
        if item_val.get_value() < min_value:
            continue
        if printall:
            print (f"Item: {item_val.get_title():100.100}, "
                   f"Delta Val: {item_val.delta_value()}, "
                   f"Price: {item_val.get_price()}, "
                   f"Value: {item_val.value}, "
                   f"URL: {item_val.get_url()}")
            item_val.print_accs()
    return item_vals
