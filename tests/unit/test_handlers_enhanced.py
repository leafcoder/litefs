#!/usr/bin/env python
# coding: utf-8

"""
增强请求处理器测试

覆盖 EnhancedRequestHandler 的属性委托、参数获取、表单验证与响应委托。
"""

import unittest
from unittest.mock import Mock

from litefs.validators import RequiredValidator
from litefs.handlers.enhanced import EnhancedRequestHandler


def make_request(**attrs):
    """构造声明了指定属性的底层请求 Mock"""
    request = Mock(spec=[])
    for key, value in attrs.items():
        setattr(request, key, value)
    return request


class TestEnhancedRequestHandlerProperties(unittest.TestCase):
    """属性委托"""

    def setUp(self):
        self.request = make_request(
            get={'q': 'search'}, post={'title': 'hello'}, files={'up': 'file'},
            body='raw-body', json={'key': 'value'}, session={'uid': 1},
            session_id='sid-001', environ={'REQUEST_METHOD': 'POST'},
            request_method='POST', content_type='application/json',
            content_length=64, path_info='/submit', query_string='q=search',
            request_uri='/submit?q=search', referer='http://example.com',
            cookie={'sid': 'sid-001'}, config={'debug': True},
        )
        self.handler = EnhancedRequestHandler(self.request)

    def test_query_and_post(self):
        """query 与 post 委托到底层请求"""
        self.assertEqual(self.handler.query, {'q': 'search'})
        self.assertEqual(self.handler.post, {'title': 'hello'})

    def test_files_body_json(self):
        """files/body/json 委托到底层请求"""
        self.assertEqual(self.handler.files, {'up': 'file'})
        self.assertEqual(self.handler.body, 'raw-body')
        self.assertEqual(self.handler.json, {'key': 'value'})

    def test_session_attributes(self):
        """session 与 session_id 委托"""
        self.assertEqual(self.handler.session, {'uid': 1})
        self.assertEqual(self.handler.session_id, 'sid-001')

    def test_request_environ_and_method(self):
        """environ 与 request_method 委托"""
        self.assertEqual(self.handler.environ, {'REQUEST_METHOD': 'POST'})
        self.assertEqual(self.handler.request_method, 'POST')

    def test_content_attributes(self):
        """content_type 与 content_length 委托"""
        self.assertEqual(self.handler.content_type, 'application/json')
        self.assertEqual(self.handler.content_length, 64)

    def test_path_and_uri_attributes(self):
        """路径相关属性委托"""
        self.assertEqual(self.handler.path_info, '/submit')
        self.assertEqual(self.handler.query_string, 'q=search')
        self.assertEqual(self.handler.request_uri, '/submit?q=search')
        self.assertEqual(self.handler.referer, 'http://example.com')

    def test_cookie_and_config(self):
        """cookie 与 config 委托"""
        self.assertEqual(self.handler.cookie, {'sid': 'sid-001'})
        self.assertEqual(self.handler.config, {'debug': True})


class TestEnhancedRequestHandlerGetters(unittest.TestCase):
    """单个参数获取方法"""

    def setUp(self):
        self.handler = EnhancedRequestHandler(make_request(
            get={'q': 'search'}, post={'title': 'hello'}, files={'up': 'file'},
        ))

    def test_get_query_param(self):
        """get_query_param 支持默认值"""
        self.assertEqual(self.handler.get_query_param('q'), 'search')
        self.assertIsNone(self.handler.get_query_param('missing'))
        self.assertEqual(self.handler.get_query_param('missing', 'fallback'), 'fallback')

    def test_get_post_param(self):
        """get_post_param 支持默认值"""
        self.assertEqual(self.handler.get_post_param('title'), 'hello')
        self.assertEqual(self.handler.get_post_param('missing', 0), 0)

    def test_get_file(self):
        """get_file 支持默认值"""
        self.assertEqual(self.handler.get_file('up'), 'file')
        self.assertIsNone(self.handler.get_file('missing'))


class TestEnhancedRequestHandlerValidation(unittest.TestCase):
    """表单验证方法"""

    def setUp(self):
        self.handler = EnhancedRequestHandler(make_request(
            get={'q': 'keyword'}, post={'title': 'hello'}, files={'doc': 'file'},
        ))

    def test_validate_query_success(self):
        """查询参数验证通过"""
        valid, errors = self.handler.validate_query({'q': [RequiredValidator()]})
        self.assertTrue(valid)
        self.assertEqual(errors, {})

    def test_validate_query_failure(self):
        """查询参数缺失时验证失败"""
        valid, errors = self.handler.validate_query({'missing': [RequiredValidator()]})
        self.assertFalse(valid)
        self.assertIn('missing', errors)

    def test_validate_post(self):
        """POST 参数验证"""
        valid, errors = self.handler.validate_post({'title': [RequiredValidator()]})
        self.assertTrue(valid)
        self.assertEqual(errors, {})

    def test_validate_files(self):
        """文件验证"""
        valid, errors = self.handler.validate_files({'doc': [RequiredValidator()]})
        self.assertTrue(valid)
        self.assertEqual(errors, {})

    def test_validate_all_combined(self):
        """validate_all 汇总各通道验证结果"""
        valid, errors = self.handler.validate_all(
            query_rules={'q': [RequiredValidator()]},
            post_rules={'title': [RequiredValidator()]},
            file_rules={'doc': [RequiredValidator()]},
        )
        self.assertTrue(valid)
        self.assertEqual(errors, {'query': {}, 'post': {}, 'files': {}})

    def test_validate_all_collects_errors_by_channel(self):
        """validate_all 按通道归集错误"""
        valid, errors = self.handler.validate_all(
            query_rules={'nope': [RequiredValidator()]},
            post_rules={'nada': [RequiredValidator()]},
        )
        self.assertFalse(valid)
        self.assertIn('query', errors)
        self.assertIn('post', errors)
        self.assertNotIn('files', errors)

    def test_validate_all_without_rules(self):
        """不传规则时验证通过"""
        valid, errors = self.handler.validate_all()
        self.assertTrue(valid)
        self.assertEqual(errors, {})

    def test_set_form_validator(self):
        """set_form_validator 保存验证器实例"""
        validator = Mock()
        self.handler.set_form_validator(validator)
        self.assertIs(self.handler._form_validator, validator)


class TestEnhancedRequestHandlerResponseDelegation(unittest.TestCase):
    """响应相关委托"""

    def test_start_response_delegates(self):
        """start_response 转发状态码与响应头"""
        request = make_request(start_response=Mock())
        handler = EnhancedRequestHandler(request)
        handler.start_response(201, [('Content-Type', 'text/html')])
        request.start_response.assert_called_once_with(201, [('Content-Type', 'text/html')])

    def test_set_cookie_delegates(self):
        """set_cookie 转发参数"""
        request = make_request(set_cookie=Mock())
        handler = EnhancedRequestHandler(request)
        handler.set_cookie('sid', 'abc', path='/', httponly=True)
        request.set_cookie.assert_called_once_with('sid', 'abc', path='/', httponly=True)


if __name__ == '__main__':
    unittest.main()
