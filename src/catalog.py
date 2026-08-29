"""
Mock product catalog — small, fake, deliberately simple.

Real integration would pull this from a merchant's actual inventory (this
is exactly what Track 1's "agent-readable catalog" direction is about).
For this prototype, a small hand-built catalog is enough to prove the
matching logic works — the matcher itself is what's real and reusable,
not the catalog data.
"""

CATALOG = [
    # footwear
    {"id": "f1", "category": "footwear", "attribute": "attr_1", "price": 1899, "name": "Running shoes — attr_1"},
    {"id": "f2", "category": "footwear", "attribute": "attr_2", "price": 2499, "name": "Running shoes — attr_2"},
    {"id": "f3", "category": "footwear", "attribute": "attr_2", "price": 3800, "name": "Trail shoes — attr_2"},
    {"id": "f4", "category": "footwear", "attribute": "attr_3", "price": 4200, "name": "Trail shoes — attr_3"},
    {"id": "f5", "category": "footwear", "attribute": "attr_4", "price": 5999, "name": "Premium sneakers — attr_4"},
    {"id": "f6", "category": "footwear", "attribute": "attr_5", "price": 7100, "name": "Premium sneakers — attr_5"},

    # electronics
    {"id": "e1", "category": "electronics", "attribute": "attr_1", "price": 1200, "name": "Wired earphones"},
    {"id": "e2", "category": "electronics", "attribute": "attr_2", "price": 2800, "name": "Bluetooth earbuds — basic"},
    {"id": "e3", "category": "electronics", "attribute": "attr_3", "price": 4500, "name": "Bluetooth earbuds — pro"},
    {"id": "e4", "category": "electronics", "attribute": "attr_4", "price": 6200, "name": "Smartwatch — basic"},
    {"id": "e5", "category": "electronics", "attribute": "attr_5", "price": 8900, "name": "Smartwatch — pro"},

    # groceries
    {"id": "g1", "category": "groceries", "attribute": "attr_1", "price": 450, "name": "Weekly staples pack"},
    {"id": "g2", "category": "groceries", "attribute": "attr_2", "price": 900, "name": "Family pack"},
    {"id": "g3", "category": "groceries", "attribute": "attr_3", "price": 1500, "name": "Premium organic pack"},

    # flights
    {"id": "fl1", "category": "flights", "attribute": "attr_1", "price": 3200, "name": "Economy — off-peak"},
    {"id": "fl2", "category": "flights", "attribute": "attr_2", "price": 4800, "name": "Economy — peak"},
    {"id": "fl3", "category": "flights", "attribute": "attr_3", "price": 6500, "name": "Economy flexible"},
    {"id": "fl4", "category": "flights", "attribute": "attr_4", "price": 9200, "name": "Premium economy"},

    # fashion
    {"id": "fa1", "category": "fashion", "attribute": "attr_1", "price": 999, "name": "Casual wear — basic"},
    {"id": "fa2", "category": "fashion", "attribute": "attr_2", "price": 2200, "name": "Casual wear — branded"},
    {"id": "fa3", "category": "fashion", "attribute": "attr_3", "price": 3800, "name": "Formal wear"},
    {"id": "fa4", "category": "fashion", "attribute": "attr_4", "price": 5500, "name": "Designer wear"},

    # home
    {"id": "h1", "category": "home", "attribute": "attr_1", "price": 800, "name": "Kitchen basics"},
    {"id": "h2", "category": "home", "attribute": "attr_2", "price": 2100, "name": "Home decor set"},
    {"id": "h3", "category": "home", "attribute": "attr_3", "price": 3900, "name": "Furniture — small"},
    {"id": "h4", "category": "home", "attribute": "attr_4", "price": 6800, "name": "Furniture — large"},
]
