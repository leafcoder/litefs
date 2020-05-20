#-*- coding: utf-8 -*-

import unittest
from litefs import TreeCache

class TestTreeCache(unittest.TestCase):

    def setUp(self):
        self.cache = TreeCache(clean_period=60, expiration_time=3600)

    def test_put(self):
        caches = {
            'k_int': 1,
            'k_str': 'hello',
            'k_float': .5
        }
        cache = TreeCache(clean_period=60, expiration_time=3600)
        for k, v in caches.items():
            cache.put(k, v)
        self.assertEqual(len(cache), len(caches))

    def test_delete(self):
        cache = self.cache
        cache_key = 'delete_key'
        cache.put(cache_key, 'delete me')
        size_before_delete = len(cache)
        cache.delete(cache_key)
        size_after_delete = len(cache)
        self.assertEqual(size_before_delete, size_after_delete + 1)

if __name__ == '__main__':
    unittest.main()
