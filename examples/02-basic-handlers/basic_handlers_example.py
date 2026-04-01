#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs import Litefs
from litefs.routing import get, post


# 导入站点中的处理函数
import importlib.util
import sys

def load_handler(module_name, file_path):
    """加载处理函数模块"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# 加载处理函数模块
json_module = load_handler('json_handler', os.path.join(os.path.dirname(__file__), 'site/json.py'))
json_complex_module = load_handler('json_complex_handler', os.path.join(os.path.dirname(__file__), 'site/json_complex.py'))
json_custom_header_module = load_handler('json_custom_header_handler', os.path.join(os.path.dirname(__file__), 'site/json_custom_header.py'))
json_error_module = load_handler('json_error_handler', os.path.join(os.path.dirname(__file__), 'site/json_error.py'))
json_html_module = load_handler('json_html_handler', os.path.join(os.path.dirname(__file__), 'site/json_html.py'))
html_module = load_handler('html_handler', os.path.join(os.path.dirname(__file__), 'site/html.py'))
text_module = load_handler('text_handler', os.path.join(os.path.dirname(__file__), 'site/text.py'))
form_module = load_handler('form_handler', os.path.join(os.path.dirname(__file__), 'site/form.py'))
error_module = load_handler('error_handler', os.path.join(os.path.dirname(__file__), 'site/error.py'))
generator_module = load_handler('generator_handler', os.path.join(os.path.dirname(__file__), 'site/generator.py'))
mixed_module = load_handler('mixed_handler', os.path.join(os.path.dirname(__file__), 'site/mixed.py'))
mixed_tuple_module = load_handler('mixed_tuple_handler', os.path.join(os.path.dirname(__file__), 'site/mixed_tuple.py'))
mixed_tuple_text_module = load_handler('mixed_tuple_text_handler', os.path.join(os.path.dirname(__file__), 'site/mixed_tuple_text.py'))


# 路由处理函数
@get('/json', name='json')
def json_route_handler(request):
    return json_module.handler(request)

@get('/json_complex', name='json_complex')
def json_complex_route_handler(request):
    return json_complex_module.handler(request)

@get('/json_custom_header', name='json_custom_header')
def json_custom_header_route_handler(request):
    return json_custom_header_module.handler(request)

@get('/json_error', name='json_error')
def json_error_route_handler(request):
    return json_error_module.handler(request)

@get('/json_html', name='json_html')
def json_html_route_handler(request):
    return json_html_module.handler(request)

@get('/html', name='html')
def html_route_handler(request):
    return html_module.handler(request)

@get('/text', name='text')
def text_route_handler(request):
    return text_module.handler(request)

@get('/form', name='form')
def form_get_route_handler(request):
    return form_module.handler(request)

@post('/form', name='form_post')
def form_post_route_handler(request):
    return form_module.handler(request)

@get('/error', name='error')
def error_route_handler(request):
    return error_module.handler(request)

@get('/generator', name='generator')
def generator_route_handler(request):
    return generator_module.handler(request)

@get('/mixed', name='mixed')
def mixed_route_handler(request):
    return mixed_module.handler(request)

@get('/mixed_tuple', name='mixed_tuple')
def mixed_tuple_route_handler(request):
    return mixed_tuple_module.handler(request)

@get('/mixed_tuple_text', name='mixed_tuple_text')
def mixed_tuple_text_route_handler(request):
    return mixed_tuple_text_module.handler(request)


def main():
    """基础处理器示例"""
    app = Litefs(
        host='0.0.0.0',
        port=8080,
        webroot='./site',
        debug=True
    )
    
    # 注册路由
    app.register_routes(__name__)
    
    print("=" * 60)
    print("Litefs Basic Handlers Example")
    print("=" * 60)
    print("可用的处理器:")
    print("  /json - JSON 响应")
    print("  /json_complex - 复杂 JSON 响应")
    print("  /json_custom_header - 自定义头的 JSON 响应")
    print("  /json_error - JSON 错误响应")
    print("  /json_html - JSON 和 HTML 混合响应")
    print("  /html - HTML 响应")
    print("  /text - 文本响应")
    print("  /form - 表单处理")
    print("  /error - 错误处理")
    print("  /generator - 生成器响应")
    print("  /mixed - 混合响应")
    print("  /mixed_tuple - 元组混合响应")
    print("  /mixed_tuple_text - 元组文本混合响应")
    print("=" * 60)
    print("注意: 所有处理器现在都使用新的路由系统")
    print("=" * 60)
    
    app.run(processes=4)


if __name__ == '__main__':
    main()
