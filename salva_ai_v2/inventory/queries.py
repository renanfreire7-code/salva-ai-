import unicodedata


def normalize(value):
    return "".join(c for c in unicodedata.normalize("NFKD",str(value).casefold()) if not unicodedata.combining(c)).strip()


def search_products(products, query):
    text=' '.join(normalize(query).split())
    def matches(product):
        name=' '.join(normalize(product['name']).split())
        words=name.split();tokens=text.split()
        cursor=0
        for token in tokens:
            while cursor<len(words) and not words[cursor].startswith(token):
                cursor+=1
            if cursor==len(words):
                prefixes=False;break
            cursor+=1
        else:
            prefixes=True
        initials=''.join(word[0] for word in words)
        return not text or text in name or text in (str(product['id']),f"{product['id']:03d}",normalize(product_label(product))) or prefixes or (' ' not in text and text in initials)
    return sorted((p for p in products if matches(p)),key=lambda p:(normalize(p['name']),p['id']))


def product_label(product):
    return f'{product["id"]:03d} - {product["name"]}'
