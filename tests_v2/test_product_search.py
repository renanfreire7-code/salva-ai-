import unittest
from salva_ai_v2.inventory.queries import search_products


class ProductSearchTest(unittest.TestCase):
    def setUp(self):
        self.products=[dict(id=1,name='Cerveja Heineken Latão'),dict(id=2,name='Caneca Holandesa Lisa'),dict(id=3,name='Água mineral')]

    def test_initials_and_ordered_word_prefixes(self):
        self.assertEqual([p['id'] for p in search_products(self.products,'cer hei')],[1])
        self.assertEqual([p['id'] for p in search_products(self.products,'  CHL  ')],[2,1])
        self.assertEqual([p['id'] for p in search_products(self.products,'a m')],[3])
        self.assertEqual([p['id'] for p in search_products(self.products,'001')],[1])
        self.assertEqual([p['id'] for p in search_products(self.products,'latao')],[1])

    def test_ambiguity_and_stable_order_do_not_select_arbitrarily(self):
        forward=search_products(self.products,'ch')
        backward=search_products(list(reversed(self.products)),'CH')
        self.assertEqual([p['id'] for p in forward],[2,1])
        self.assertEqual(forward,backward)
        self.assertEqual(search_products(self.products,"' OR 1=1 --"),[])
