import unicodedata


def normalize(value):
    return "".join(c for c in unicodedata.normalize("NFKD",str(value).casefold()) if not unicodedata.combining(c)).strip()


def search_products(products, query):
    text = normalize(query)
    return [p for p in products if not text or text in normalize(p["name"]) or text == str(p["id"]) or text == f'{p["id"]:03d}']

