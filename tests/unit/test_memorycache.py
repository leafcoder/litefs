#-*- coding: utf-8 -*-

import unittest
from litefs import MemoryCache

class MemoryCacheTest(unittest.TestCase):

    def setUp(self):
        self.max_size = 100
        self.cache_key = 'test_key'
        self.cache_value = 'test_val'

    def test_put(self):
        cache = MemoryCache(max_size=self.max_size)
        for i in range(self.max_size):
            cache.put('%s-%d' % (self.cache_key, i), self.cache_value)
        self.assertEqual(len(cache), self.max_size)

    def test_delete(self):
        cache = MemoryCache(max_size=self.max_size)
        size = len(cache)
        cache.put(self.cache_key, self.cache_value)
        cache.delete(self.cache_key)
        self.assertEqual(len(cache), size)

    def test_out_of_max_size(self):
        cache = MemoryCache(max_size=self.max_size)
        for i in range(1000):
            cache.put('%s-%d' % (self.cache_key, i), self.cache_value)
        self.assertEqual(len(cache), self.max_size)
        for i in range(900):
            cache_key = '%s-%d' % (self.cache_key, i)
            self.assertIsNone(cache.get(cache_key))

if __name__ == '__main__':
    unittest.main()