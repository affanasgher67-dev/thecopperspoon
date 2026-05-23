from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any
import time

_MENU_CACHE: MenuCatalog | None = None
_CACHE_EXPIRY: float = 0
_CACHE_TTL: int = 300 # 5 minutes


def _default_menu_payload() -> dict[str, Any]:
    return {
        "restaurant": "The Copper Spoon",
        "currency": "$",
        "updated_at": "2026-04-20T21:30:00",
        "sections": [
            {
                "name": "Starters & Shared",
                "items": [
                    {
                        "name": "Beef Carpaccio",
                        "description": "Thinly sliced prime beef, arugula, capers, truffle oil",
                        "detailed_description": "Thinly sliced aged prime beef tenderloin, drizzled with white truffle oil. Served with wild baby arugula, brined caper berries, and shavings of 24-month aged Parmigiano-Reggiano.",
                        "price": 12.50,
                        "tags": ["refined", "signature"],
                        "highlight": True,
                        "image_url": "/static/beef_carpaccio.png",
                    },
                    {
                        "name": "Seared Scallops",
                        "description": "Cauliflower puree, brown butter, crispy sage",
                        "detailed_description": "Three jumbo Hokkaido scallops, pan-seared to a golden crust. Set atop a silky scorched cauliflower puree and finished with a nutty brown butter emulsion and flash-fried sage leaves.",
                        "price": 18.50,
                        "tags": ["seafood", "chef special"],
                        "image_url": "/static/scallops.png",
                    },
                    {
                        "name": "Truffle Fries",
                        "description": "House-cut fries, parmesan, truffle aioli",
                        "detailed_description": "Hand-cut Idaho potatoes tossed with white truffle oil, freshly grated Parmesan cheese, and chopped Italian parsley. Served with a side of garlic-truffle dipping sauce.",
                        "price": 8.50,
                        "tags": ["vegetarian", "classic"],
                        "image_url": "/static/truffle_fries.png",
                    },
                    {
                        "name": "Spicy Honey Wings",
                        "description": "Crispy glazed wings, chili honey, scallions",
                        "detailed_description": "Flash-fried chicken wings tossed in our signature fermented chili and organic honey glaze. Finished with sliced scallions and toasted sesame seeds.",
                        "price": 11.50,
                        "tags": ["house favorite", "spicy"],
                        "image_url": "/static/wings.png",
                    },
                    {
                        "name": "Truffle Mushroom Soup",
                        "description": "Wild mushroom medley, cream, truffle foam",
                        "detailed_description": "A velvety blend of roasted portobello, cremini, and porcini mushrooms. Infused with a touch of heavy cream and topped with an airy black truffle foam.",
                        "price": 9.50,
                        "tags": ["vegetarian", "comfort"],
                        "image_url": "/static/mushroom_soup.png",
                    },
                    {
                        "name": "Crispy Calamari",
                        "description": "Lemon aioli, chili salt, and herbs",
                        "detailed_description": "Our calamari is caught fresh and flash-fried to maintain tenderness. Served with a house-made charred lemon aioli and a sprinkle of Aleppo pepper.",
                        "price": 11.50,
                        "tags": ["house favorite", "shareable"],
                        "image_url": "/static/calamari.png",
                    },
                    {
                        "name": "Burrata Toast",
                        "description": "Tomato jam, basil oil, toasted sourdough",
                        "detailed_description": "Creamy burrata imported from Puglia, served on sourdough bread toasted with garlic oil. Finished with our signature 4-hour slow-cooked tomato jam.",
                        "price": 13.50,
                        "tags": ["vegetarian"],
                        "image_url": "/static/burrata.png",
                    },
                ],
            },
            {
                "name": "Artisanal Mains",
                "items": [
                    {
                        "name": "Lobster Ravioli",
                        "description": "Hand-made pasta, saffron cream sauce, fresh herbs",
                        "detailed_description": "Tender house-made pasta pockets generously filled with succulent Maine lobster meat and herbed ricotta. Bathed in a rich, saffron-infused lobster bisque reduction.",
                        "price": 34.00,
                        "tags": ["handmade", "premium"],
                        "highlight": True,
                        "image_url": "/static/lobster_ravioli.png",
                    },
                    {
                        "name": "Herb-Crusted Rack of Lamb",
                        "description": "Mint pea puree, roasted fingerling potatoes",
                        "detailed_description": "A full four-bone rack of lamb, crusted with a blend of Dijon, breadcrumbs, and fresh garden herbs. Served pink with a vibrant mint-infused pea puree.",
                        "price": 42.00,
                        "tags": ["chef special", "signature"],
                        "image_url": "/static/lamb.png",
                    },
                    {
                        "name": "Roasted Duck Breast",
                        "description": "Cherry balsamic, polenta, rosemary",
                        "detailed_description": "Maple Leaf Farms duck breast, pan-seared to a crisp skin and served medium. Accompanied by a tart cherry balsamic glaze and creamy stone-ground polenta.",
                        "price": 32.50,
                        "tags": ["premium", "classic"],
                        "image_url": "/static/duck.png",
                    },
                    {
                        "name": "Mushroom Tagliatelle",
                        "description": "Hand-made pasta, wild mushroom ragu, parmesan",
                        "detailed_description": "House-stretched pasta ribbons tossed in a rich ragu of braised wild mushrooms, garlic, and fresh herbs. Finished with 24-month aged Parmesan.",
                        "price": 26.50,
                        "tags": ["vegetarian", "handmade"],
                        "image_url": "/static/mushroom.png",
                    },
                    {
                        "name": "Pan-Seared Sea Bass",
                        "description": "Lemon butter, asparagus, micro greens",
                        "detailed_description": "Flaky Chilean sea bass seared to perfection. Accompanied by grilled asparagus spears and finished with a citrusy beurre blanc.",
                        "price": 38.00,
                        "tags": ["seafood", "light"],
                        "image_url": "/static/seabass.png",
                    },
                    {
                        "name": "Braised Short Rib",
                        "description": "Creamy mashed potatoes and rosemary jus",
                        "detailed_description": "Prime beef short rib slow-braised for 12 hours in red wine. Served over buttery Yukon Gold mashed potatoes and roasted baby carrots.",
                        "price": 31.50,
                        "tags": ["comfort", "slow-cooked"],
                        "image_url": "/static/signature.png",
                    },
                    {
                        "name": "Wood-Grilled Salmon",
                        "description": "Charred lemon, warm grain salad, dill yogurt",
                        "detailed_description": "Sustainable Atlantic salmon grilled over white oak. Served with a warm farro and quinoa salad and a cooling cucumber-dill yogurt sauce.",
                        "price": 28.50,
                        "tags": ["gluten-free", "healthy"],
                        "image_url": "/static/salmon.png",
                    },
                ],
            },
            {
                "name": "Indulgent Desserts",
                "items": [
                    {
                        "name": "Pistachio Panna Cotta",
                        "description": "Honey drizzle, toasted nuts, raspberry",
                        "detailed_description": "A silky, nutty custard made with Sicilian pistachios. Topped with a light honey drizzle, crushed roasted nuts, and a tart fresh raspberry coulis.",
                        "price": 11.00,
                        "tags": ["nutty", "creamy"],
                        "image_url": "/static/pistachio.png",
                    },
                    {
                        "name": "Vanilla Bean Creme Brulee",
                        "description": "Burnt sugar crust, seasonal berries",
                        "detailed_description": "Rich Madagascan vanilla bean custard with a crisp, hand-torched caramelized sugar topping. Served with seasonal berries.",
                        "price": 12.00,
                        "tags": ["classic", "sweet"],
                        "highlight": True,
                        "image_url": "/static/creme_brulee.png",
                    },
                    {
                        "name": "Olive Oil Cake",
                        "description": "Citrus glaze, whipped cream, thyme",
                        "detailed_description": "A moist, golden Mediterranean-style cake infused with premium extra virgin olive oil. Served with fresh whipped cream and candied citrus peel.",
                        "price": 10.50,
                        "tags": ["mediterranean", "light"],
                        "image_url": "/static/cake.png",
                    },
                    {
                        "name": "Chocolate Pot de Creme",
                        "description": "Dark chocolate custard, sea salt, whipped cream",
                        "detailed_description": "Rich, decadent dark chocolate custard topped with sea salt flakes and a vanilla bean whipped cream swirl.",
                        "price": 11.50,
                        "tags": ["rich", "decadent"],
                        "image_url": "/static/dessert.png",
                    },
                    {
                        "name": "Tiramisu",
                        "description": "Espresso-soaked ladyfingers, cocoa",
                        "detailed_description": "Traditional Italian dessert with layers of espresso-dipped ladyfingers and a light, airy mascarpone sabayon.",
                        "price": 11.50,
                        "tags": ["classic", "coffee"],
                        "image_url": "/static/tiramisu.png",
                    },
                    {
                        "name": "NY Cheesecake",
                        "description": "Graham cracker crust, berry compote",
                        "detailed_description": "Classic New York style cheesecake with a thick graham cracker base, served with a seasonal mixed berry compote.",
                        "price": 12.50,
                        "tags": ["classic", "rich"],
                        "image_url": "/static/cheesecake.png",
                    },
                ],
            },
            {
                "name": "Artisanal Beverages",
                "items": [
                    {
                        "name": "Smoked Peach Spritz",
                        "description": "Roasted peach, sparkling cider, rosemary",
                        "detailed_description": "A vibrant and smoky non-alcoholic spritz made with wood-roasted peach reduction, cold-pressed apple cider, and a sprig of charred rosemary.",
                        "price": 8.50,
                        "tags": ["refreshing", "craft"],
                        "image_url": "/static/spritz.png",
                    },
                    {
                        "name": "Hibiscus Iced Tea",
                        "description": "Cold-brewed hibiscus, agave, lime",
                        "detailed_description": "A tart and floral iced tea cold-brewed with organic hibiscus petals. Sweetened slightly with blue agave and finished with fresh lime juice.",
                        "price": 6.50,
                        "tags": ["light", "floral"],
                        "image_url": "/static/tea.png",
                    },
                    {
                        "name": "House Lemonade",
                        "description": "Freshly squeezed lemons, mint, cane sugar",
                        "detailed_description": "Simple and perfect. Hand-squeezed citrus with muddled garden mint and pure cane sugar syrup. Served over crushed ice.",
                        "price": 5.50,
                        "tags": ["classic", "fresh"],
                        "image_url": "/static/lemonade.png",
                    },
                    {
                        "name": "Espresso Martini",
                        "description": "Double espresso, coffee liqueur, vanilla",
                        "detailed_description": "A sophisticated pick-me-up. Hand-pulled double espresso shaken with premium coffee liqueur and a hint of vanilla bean. Finished with three espresso beans.",
                        "price": 14.50,
                        "tags": ["cocktail", "rich"],
                        "image_url": "/static/espresso_martini.png",
                    },
                    {
                        "name": "Old Fashioned",
                        "description": "Oak-aged bourbon, bitters, orange zest",
                        "detailed_description": "The timeless classic. Premium oak-aged bourbon stirred with aromatic bitters and a touch of cane sugar. Served over a single clear ice block with an orange twist.",
                        "price": 16.50,
                        "tags": ["classic", "cocktail"],
                        "image_url": "/static/old_fashioned.png",
                    },
                ],
            },
        ]
    }


# Fallback image mapping: item name -> static image path
MENU_IMAGE_MAP = {
    "Crispy Calamari": "/static/calamari.png",
    "Burrata Toast": "/static/burrata.png",
    "Truffle Fries": "/static/truffle_fries.png",
    "Spicy Honey Wings": "/static/wings.png",
    "Wood-Grilled Salmon": "/static/salmon.png",
    "Braised Short Rib": "/static/signature.png",
    "Mushroom Tagliatelle": "/static/mushroom.png",
    "Roasted Duck Breast": "/static/duck.png",
    "Wild Mushroom Risotto": "/static/risotto.png",
    "Olive Oil Cake": "/static/cake.png",
    "Chocolate Pot de Creme": "/static/dessert.png",
    "NY Cheesecake": "/static/cheesecake.png",
    "Tiramisu": "/static/tiramisu.png",
    "House Lemonade": "/static/lemonade.png",
    "Smoked Peach Spritz": "/static/spritz.png",
    "Hibiscus Iced Tea": "/static/tea.png",
    "Espresso Martini": "/static/espresso_martini.png",
}


@dataclass(frozen=True)
class MenuItem:
    name: str
    description: str
    detailed_description: str = ""
    price: float | None = None
    tags: tuple[str, ...] = ()
    highlight: bool = False
    out_of_stock: bool = False
    image_url: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MenuItem":
        name = str(payload.get("name", ""))
        # Use provided image_url, or fall back to the known image map
        image_url = payload.get("image_url") or MENU_IMAGE_MAP.get(name)
        return cls(
            name=name,
            description=str(payload.get("description", "")),
            detailed_description=str(payload.get("detailed_description", "")),
            price=float(payload["price"]) if payload.get("price") is not None else None,
            tags=tuple(str(tag) for tag in payload.get("tags", []) if str(tag).strip()),
            highlight=bool(payload.get("highlight", False)),
            out_of_stock=bool(payload.get("out_of_stock", False)),
            image_url=image_url,
        )

    def as_dict(self, currency: str = "$") -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "detailed_description": self.detailed_description,
            "price": self.price,
            "price_display": self.price_display(currency),
            "tags": list(self.tags),
            "highlight": self.highlight,
            "out_of_stock": self.out_of_stock,
            "image_url": self.image_url,
        }

    def price_display(self, currency: str = "$") -> str:
        if self.price is None:
            return ""
        if float(self.price).is_integer():
            return f"{currency}{int(self.price)}"
        return f"{currency}{self.price:.2f}"


@dataclass(frozen=True)
class MenuSection:
    name: str
    items: tuple[MenuItem, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MenuSection":
        items = tuple(MenuItem.from_dict(item) for item in payload.get("items", []))
        return cls(name=str(payload.get("name", "")), items=items)

    def as_dict(self, currency: str = "$") -> dict[str, Any]:
        return {
            "name": self.name,
            "items": [item.as_dict(currency=currency) for item in self.items],
        }


@dataclass(frozen=True)
class MenuCatalog:
    restaurant_name: str
    currency: str
    updated_at: str | None
    sections: tuple[MenuSection, ...]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "MenuCatalog":
        sections = tuple(MenuSection.from_dict(section) for section in payload.get("sections", []))
        return cls(
            restaurant_name=str(payload.get("restaurant", "The Copper Spoon")),
            currency=str(payload.get("currency", "$")),
            updated_at=str(payload["updated_at"]) if payload.get("updated_at") else None,
            sections=sections,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "restaurant": self.restaurant_name,
            "currency": self.currency,
            "updated_at": self.updated_at,
            "sections": [section.as_dict(currency=self.currency) for section in self.sections],
        }

    def highlight_items(self, limit: int = 6) -> list[str]:
        highlights: list[str] = []
        for section in self.sections:
            for item in section.items:
                if item.highlight or not highlights:
                    highlights.append(item.name)
                if len(highlights) >= limit:
                    return highlights[:limit]

        return highlights[:limit]

    def chat_context(self) -> str:
        highlights = self.highlight_items()
        section_lines = []
        out_of_stock_items = []
        for section in self.sections:
            section_items = ", ".join(item.name for item in section.items[:3])
            section_lines.append(f"- {section.name}: {section_items}")
            for item in section.items:
                if item.out_of_stock:
                    out_of_stock_items.append(item.name)

        highlight_line = "; ".join(highlights)
        out_of_stock_text = f"OUT OF STOCK (Do NOT recommend or order these under any circumstance!): {', '.join(out_of_stock_items)}" if out_of_stock_items else "All items are currently in stock."
        return (
            "Live menu data from Cloud Firestore.\n"
            f"Menu highlights: {highlight_line}.\n"
            "Use these names when making recommendations.\n"
            f"{out_of_stock_text}\n"
            + "\n".join(section_lines)
        )

    def search(self, query: str) -> list[dict[str, Any]]:
        """Search menu items by name, description, or tag."""
        query_lower = query.lower().strip()
        if not query_lower:
            return []

        results: list[dict[str, Any]] = []
        for section in self.sections:
            for item in section.items:
                if (
                    query_lower in item.name.lower()
                    or query_lower in item.description.lower()
                    or any(query_lower in tag.lower() for tag in item.tags)
                ):
                    result = item.as_dict(self.currency)
                    result["section"] = section.name
                    results.append(result)
        return results

    def filter_by_tag(self, tag: str) -> list[dict[str, Any]]:
        """Return all items matching a tag (e.g., 'vegetarian', 'gluten-free')."""
        tag_lower = tag.lower().strip()
        results: list[dict[str, Any]] = []
        for section in self.sections:
            for item in section.items:
                if any(tag_lower in t.lower() for t in item.tags):
                    result = item.as_dict(self.currency)
                    result["section"] = section.name
                    results.append(result)
        return results

    def price_range(
        self, min_price: float = 0, max_price: float = float("inf")
    ) -> list[dict[str, Any]]:
        """Return all items within a price range."""
        results: list[dict[str, Any]] = []
        for section in self.sections:
            for item in section.items:
                if item.price is not None and min_price <= item.price <= max_price:
                    result = item.as_dict(self.currency)
                    result["section"] = section.name
                    results.append(result)
        return results

    def all_tags(self) -> list[str]:
        """Return a sorted list of all unique tags across the menu."""
        tags: set[str] = set()
        for section in self.sections:
            for item in section.items:
                tags.update(item.tags)
        return sorted(tags)

    def find_item(self, name: str) -> "MenuItem | None":
        """Find a menu item by exact name (case-insensitive)."""
        target = name.strip().lower()
        for section in self.sections:
            for item in section.items:
                if item.name.lower() == target:
                    return item
        return None


def load_menu_catalog(db: Any = None) -> MenuCatalog:
    """Load menu catalog from Firestore (preferred) or default payload with caching."""
    global _MENU_CACHE, _CACHE_EXPIRY

    # Check cache first
    if _MENU_CACHE and time.time() < _CACHE_EXPIRY:
        return _MENU_CACHE

    # Backward-compatible local file mode: argument can be a file path or directory.
    if isinstance(db, (str, Path)):
        path = Path(db)
        menu_path = path / "menu.json" if path.is_dir() else path
        if menu_path.exists():
            payload = json.loads(menu_path.read_text(encoding="utf-8"))
            return MenuCatalog.from_payload(payload)

    if db is not None:
        try:
            # We store sections in 'menu_sections' collection
            sections_query = db.collection("menu_sections").stream()
            sections_data = []
            for doc in sections_query:
                sections_data.append(doc.to_dict())
            
            # Metadata in 'metadata/menu'
            meta_doc = db.collection("metadata").document("menu").get()
            meta = meta_doc.to_dict() if meta_doc.exists else {}
            
            if sections_data:
                payload = {
                    "restaurant": meta.get("restaurant", "The Copper Spoon"),
                    "currency": meta.get("currency", "$"),
                    "updated_at": meta.get("updated_at"),
                    "sections": sections_data
                }
                catalog = MenuCatalog.from_payload(payload)
                _MENU_CACHE = catalog
                _CACHE_EXPIRY = time.time() + _CACHE_TTL
                return catalog
        except Exception as e:
            print(f"Warning: Failed to load menu from Firestore: {e}")

    return MenuCatalog.from_payload(_default_menu_payload())

def update_menu_item_stock(db: Any, item_name: str, out_of_stock: bool) -> bool:
    """Update stock status directly in Firestore."""
    if db is None:
        return False

    try:
        # 1. Find the section containing the item
        sections_ref = db.collection("menu_sections")
        sections = sections_ref.stream()
        
        for doc in sections:
            section_data = doc.to_dict()
            items = section_data.get("items", [])
            found = False
            for item in items:
                if item.get("name") == item_name:
                    item["out_of_stock"] = out_of_stock
                    found = True
                    break
            
            if found:
                # Update the whole section document
                sections_ref.document(doc.id).set(section_data)
                
                # Invalidate cache
                global _MENU_CACHE, _CACHE_EXPIRY
                _MENU_CACHE = None
                _CACHE_EXPIRY = 0
                
                return True
                
    except Exception as e:
        print(f"Error updating stock in Firestore: {e}")
        
    return False


def add_menu_item(db: Any, section_name: str, item_data: dict[str, Any]) -> bool:
    """Add a new menu item to a section in Firestore."""
    if db is None:
        return False

    try:
        sections_ref = db.collection("menu_sections")
        # Find the target section by name
        target_doc_id = section_name.lower().replace(" ", "_").replace("&", "and")
        
        # Try to find by iterating (in case doc ID doesn't match exactly)
        target_doc = None
        for doc in sections_ref.stream():
            data = doc.to_dict()
            if data.get("name", "").lower() == section_name.lower():
                target_doc = doc
                break
        
        if target_doc is None:
            # Section not found — create it
            new_section = {"name": section_name, "items": [item_data]}
            sections_ref.document(target_doc_id).set(new_section)
        else:
            # Append to existing section
            section_data = target_doc.to_dict()
            items = section_data.get("items", [])
            
            # Prevent duplicates
            for existing in items:
                if existing.get("name", "").lower() == item_data.get("name", "").lower():
                    return False  # Item already exists
            
            items.append(item_data)
            section_data["items"] = items
            sections_ref.document(target_doc.id).set(section_data)

        # Invalidate cache
        global _MENU_CACHE, _CACHE_EXPIRY
        _MENU_CACHE = None
        _CACHE_EXPIRY = 0

        return True

    except Exception as e:
        print(f"Error adding menu item to Firestore: {e}")

    return False


def remove_menu_item(db: Any, item_name: str) -> bool:
    """Remove a menu item by name from Firestore and delete its uploaded image."""
    if db is None:
        return False

    try:
        sections_ref = db.collection("menu_sections")

        for doc in sections_ref.stream():
            section_data = doc.to_dict()
            items = section_data.get("items", [])
            original_len = len(items)

            image_url = None
            new_items = []
            for item in items:
                if item.get("name", "").lower() == item_name.lower():
                    image_url = item.get("image_url")
                else:
                    new_items.append(item)

            if len(new_items) < original_len:
                section_data["items"] = new_items
                sections_ref.document(doc.id).set(section_data)

                # Delete uploaded image if it exists in uploads folder
                if image_url and "/uploads/" in image_url:
                    try:
                        filename = image_url.split("/")[-1]
                        img_path = Path(__file__).resolve().parent / "static" / "uploads" / filename
                        if img_path.exists():
                            img_path.unlink()
                    except Exception:
                        pass

                global _MENU_CACHE, _CACHE_EXPIRY
                _MENU_CACHE = None
                _CACHE_EXPIRY = 0

                return True

    except Exception as e:
        print(f"Error removing menu item from Firestore: {e}")

    return False
