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


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestOpenAPIGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestSwaggerUI))
    suite.addTests(loader.loadTestsFromTestCase(TestOpenAPI))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
