#-*- coding: utf-8 -*-

import unittest
from litefs import parse_form, make_form

class FormTest(unittest.TestCase):

    def test_make_form(self):
        # test case 1
        test_environ = {
            'QUERY_STRING': 'name=tom&name=tom&cn_name=%E6%B1%A4%E5%A7%86',
            'POST_CONTENT': 'name=jerry&cn_name=%E6%9D%B0%E7%91%9E'
        }
        self.assertEqual(
            make_form(test_environ),
            {
                'name': ['tom', 'tom', 'jerry'],
                'cn_name': ['汤姆', '杰瑞']
            }
        )
        # test case 2
        test_environ = {
            'QUERY_STRING': 'name=tom',
            'POST_CONTENT': 'name=tom&name=tom'
        }
        self.assertEqual(
            make_form(test_environ), { 'name': ['tom', 'tom', 'tom'] })
        # test case 3
        test_environ = {
            'QUERY_STRING': 'name=tom'
        }
        self.assertEqual(make_form(test_environ), { 'name': 'tom' })
        # test case 4
        test_environ = {
            'QUERY_STRING': '',
            'POST_CONTENT': 'name=jerry'
        }
        self.assertEqual(make_form(test_environ), { 'name': 'jerry' })
        with self.assertRaises(KeyError):
            # test case 5
            test_environ = {
                'POST_CONTENT': 'name=jerry'
            }
            make_form(test_environ)

    def test_parse_form(self):
        pass

if __name__ == '__main__':
    unittest.main()