#!/usr/bin/env python
# coding: utf-8

"""
OpenAPI 文档自动生成单元测试
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class TestOpenAPIGenerator(unittest.TestCase):
    """OpenAPI 生成器测试"""
    
    def test_generator_initialization(self):
        """测试生成器初始化"""
        from litefs.openapi.generator import OpenAPIGenerator
        
        generator = OpenAPIGenerator('Test API', '1.0.0', 'Test Description')
        
        self.assertEqual(generator.title, 'Test API')
        self.assertEqual(generator.version, '1.0.0')
        self.assertEqual(generator.description, 'Test Description')
    
    def test_add_tag(self):
        """测试添加标签"""
        from litefs.openapi.generator import OpenAPIGenerator
        
        generator = OpenAPIGenerator()
        generator.add_tag('users', '用户管理')
        
        self.assertEqual(len(generator._tags), 1)
        self.assertEqual(generator._tags[0]['name'], 'users')
        self.assertEqual(generator._tags[0]['description'], '用户管理')
    
    def test_add_server(self):
        """测试添加服务器"""
        from litefs.openapi.generator import OpenAPIGenerator
        
        generator = OpenAPIGenerator()
        generator.add_server('http://localhost:8080', '开发服务器')
        
        self.assertEqual(len(generator._servers), 1)
        self.assertEqual(generator._servers[0]['url'], 'http://localhost:8080')
    
    def test_add_security_scheme(self):
        """测试添加安全方案"""
        from litefs.openapi.generator import OpenAPIGenerator
        
        generator = OpenAPIGenerator()
        generator.add_security_scheme('bearerAuth', {
            'type': 'http',
            'scheme': 'bearer',
        })
        
        self.assertIn('bearerAuth', generator._security_schemes)
    
    def test_type_schema_conversion(self):
        """测试类型转换"""
        from litefs.openapi.generator import OpenAPIGenerator
        
        generator = OpenAPIGenerator()
        
        self.assertEqual(generator._get_type_schema(str), {'type': 'string'})
        self.assertEqual(generator._get_type_schema(int), {'type': 'integer'})
        self.assertEqual(generator._get_type_schema(float), {'type': 'number'})
        self.assertEqual(generator._get_type_schema(bool), {'type': 'boolean'})
        self.assertEqual(generator._get_type_schema(list), {'type': 'array', 'items': {'type': 'string'}})
        self.assertEqual(generator._get_type_schema(dict), {'type': 'object'})
    
    def test_generate_spec(self):
        """测试生成 OpenAPI 规范"""
        from litefs.openapi.generator import OpenAPIGenerator
        from litefs.routing.router import Router
        
        generator = OpenAPIGenerator('Test API', '1.0.0')
        
        router = Router()
        router.add_get('/users', lambda r: {'users': []}, 'list_users')
        
        spec = generator.generate(router)
        
        self.assertEqual(spec['openapi'], '3.0.0')
        self.assertEqual(spec['info']['title'], 'Test API')
        self.assertIn('paths', spec)
        self.assertIn('/users', spec['paths'])


class TestSwaggerUI(unittest.TestCase):
    """Swagger UI 测试"""
    
    def test_ui_initialization(self):
        """测试 UI 初始化"""
        from litefs.openapi.ui import SwaggerUI
        
        ui = SwaggerUI('/docs', '/openapi.json')
        
        self.assertEqual(ui.docs_url, '/docs')
        self.assertEqual(ui.openapi_url, '/openapi.json')
    
    def test_render_html(self):
        """测试渲染 HTML"""
        from litefs.openapi.ui import SwaggerUI
        
        ui = SwaggerUI()
        html = ui.render_html('/openapi.json')
        
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('swagger-ui', html)
        self.assertIn('/openapi.json', html)


class TestOpenAPI(unittest.TestCase):
    """OpenAPI 集成测试"""
    
    def test_openapi_initialization(self):
        """测试 OpenAPI 初始化"""
        from litefs.openapi import OpenAPI
        
        openapi = OpenAPI(
            title='Test API',
            version='1.0.0',
            description='Test Description',
        )
        
        self.assertEqual(openapi.title, 'Test API')
        self.assertEqual(openapi.version, '1.0.0')
    
    def test_doc_decorator(self):
        """测试文档装饰器"""
        from litefs.openapi import OpenAPI
        
        openapi = OpenAPI()
        
        @openapi.doc(
            summary='获取用户列表',
            tags=['users'],
        )
        def get_users(request):
            return {'users': []}
        
        self.assertTrue(hasattr(get_users, '_openapi_doc'))
        self.assertEqual(get_users._openapi_doc['summary'], '获取用户列表')
        self.assertEqual(get_users._openapi_doc['tags'], ['users'])
    
    def test_schema_decorator(self):
        """测试 Schema 装饰器"""
        from litefs.openapi import OpenAPI
        
        openapi = OpenAPI()
        
        @openapi.schema('User')
        class User:
            id: int
            name: str
        
        self.assertIn('User', openapi._generator._schemas)
    
    def test_add_tag(self):
        """测试添加标签"""
        from litefs.openapi import OpenAPI
        
        openapi = OpenAPI()
        openapi.add_tag('users', '用户管理')
        
        self.assertEqual(len(openapi._generator._tags), 1)
    
    def test_add_server(self):
        """测试添加服务器"""
        from litefs.openapi import OpenAPI
        
        openapi = OpenAPI()
        openapi.add_server('http://localhost:8080', '开发服务器')
        
        self.assertEqual(len(openapi._generator._servers), 1)


class TestSignatureInference(unittest.TestCase):
    """基于 handler 签名的参数推断（0.13-⭐2）"""

    def setUp(self):
        from litefs.openapi.generator import OpenAPIGenerator
        from litefs.routing.router import Router

        self.generator = OpenAPIGenerator('Test API', '1.0.0')
        self.router = Router()

    def _generate(self, path, handler, doc_info=None):
        """注册路由并生成该路径的规范片段"""
        self.router.add_get(path, handler, 'test_handler')
        route = self.router.routes[-1]
        if doc_info is not None:
            handler._openapi_doc = doc_info
        return self.generator._generate_path_item(route)

    def test_query_params_inferred_with_defaults(self):
        """带默认值的签名参数推断为非必填 query 参数"""
        def handler(request, page: int = 1, q: str = ''):
            return {}

        spec = self._generate('/items', handler)
        params = spec['get']['parameters']

        by_name = {p['name']: p for p in params}
        self.assertEqual(by_name['page']['in'], 'query')
        self.assertEqual(by_name['page']['schema'], {'type': 'integer'})
        self.assertFalse(by_name['page']['required'])
        self.assertEqual(by_name['q']['schema'], {'type': 'string'})
        self.assertFalse(by_name['q']['required'])

    def test_required_query_param_without_default(self):
        """无默认值的签名参数推断为必填 query 参数"""
        def handler(request, keyword: str):
            return {}

        spec = self._generate('/search', handler)
        params = spec['get']['parameters']
        by_name = {p['name']: p for p in params}
        self.assertTrue(by_name['keyword']['required'])
        self.assertEqual(by_name['keyword']['schema'], {'type': 'string'})

    def test_path_param_schema_from_annotation(self):
        """路径参数类型取自签名注解而非硬编码 string"""
        def handler(request, user_id: int):
            return {}

        spec = self._generate('/users/{user_id}', handler)
        params = spec['get']['parameters']
        by_name = {p['name']: p for p in params}
        self.assertEqual(by_name['user_id']['in'], 'path')
        self.assertEqual(by_name['user_id']['schema'], {'type': 'integer'})
        self.assertTrue(by_name['user_id']['required'])

    def test_body_param_inferred_from_reserved_name(self):
        """data/body/payload 参数推断为 requestBody"""
        def handler(request, data: dict):
            return {}

        spec = self._generate('/items', handler)
        body = spec['get']['requestBody']
        self.assertEqual(
            body['content']['application/json']['schema'], {'type': 'object'},
        )

    def test_doc_parameters_take_precedence(self):
        """显式文档参数优先，签名推断不产生重复参数"""
        def handler(request, page: int = 1):
            return {}

        doc_info = {
            'parameters': [{
                'name': 'page', 'in': 'query', 'required': True,
                'schema': {'type': 'integer'}, 'description': '页码',
            }],
        }
        spec = self._generate('/items', handler, doc_info)
        params = spec['get']['parameters']
        page_params = [p for p in params if p['name'] == 'page']
        self.assertEqual(len(page_params), 1)
        self.assertEqual(page_params[0]['description'], '页码')

    def test_var_args_skipped(self):
        """*args 与 **kwargs 不参与推断"""
        def handler(request, *args, **kwargs):
            return {}

        spec = self._generate('/items', handler)
        self.assertNotIn('parameters', spec['get'])

    def test_lambda_handler_no_params(self):
        """lambda 处理器仅含 request 参数时不产出参数"""
        spec = self._generate('/users', lambda r: {'users': []})
        self.assertNotIn('parameters', spec['get'])

    def test_unannotated_param_defaults_to_string(self):
        """未注解参数回退为 string 类型 query 参数"""
        def handler(request, page=1):
            return {}

        spec = self._generate('/items', handler)
        params = spec['get']['parameters']
        self.assertEqual(params[0]['schema'], {'type': 'string'})


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestOpenAPIGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestSwaggerUI))
    suite.addTests(loader.loadTestsFromTestCase(TestOpenAPI))
    suite.addTests(loader.loadTestsFromTestCase(TestSignatureInference))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
