#!/usr/bin/env python
# coding: utf-8

"""
ASGI 集成测试

通过直接调用 Litefs.asgi() 返回的 ASGI application 测试完整的请求生命周期，
覆盖路由匹配、请求体解析、响应序列化、异步处理器等核心功能。
"""

import asyncio
import json
import pytest

from litefs.core import Litefs
from litefs.exceptions import HttpError


# ==================== 辅助工具 ====================


def make_scope(
    method='GET',
    path='/',
    query_string=b'',
    headers=None,
    http_version='1.1',
):
    """构建 ASGI scope 字典"""
    scope = {
        'type': 'http',
        'method': method,
        'path': path,
        'query_string': query_string,
        'server': ('localhost', 8000),
        'client': ('127.0.0.1', 12345),
        'http_version': http_version,
        'headers': headers or [],
    }
    return scope


def make_receive(body=b'', more_body=False):
    """构建 ASGI receive callable"""
    called = False

    async def receive():
        nonlocal called
        if not called:
            called = True
            return {'type': 'http.request', 'body': body, 'more_body': more_body}
        return {'type': 'http.disconnect'}

    return receive


class SendCollector:
    """收集 ASGI send 调用的响应消息"""

    def __init__(self):
        self.messages = []

    async def __call__(self, message):
        self.messages.append(message)

    @property
    def status(self):
        """获取响应状态码"""
        for msg in self.messages:
            if msg.get('type') == 'http.response.start':
                return msg['status']
        return None

    @property
    def headers(self):
        """获取响应头（转换为 dict）"""
        for msg in self.messages:
            if msg.get('type') == 'http.response.start':
                return {k.decode('utf-8'): v.decode('utf-8') for k, v in msg.get('headers', [])}
        return {}

    @property
    def body(self):
        """获取响应体（bytes）"""
        for msg in self.messages:
            if msg.get('type') == 'http.response.body':
                return msg.get('body', b'')
        return b''

    @property
    def body_json(self):
        """获取响应体（解析为 JSON）"""
        return json.loads(self.body)


@pytest.fixture
def app():
    """创建带有测试路由的 Litefs 应用"""
    app = Litefs()

    @app.add_get('/', name='index')
    def index_handler(request):
        return 'Hello World'

    @app.add_get('/json', name='json_response')
    def json_handler(request):
        return {'message': 'hello', 'status': 'ok'}

    @app.add_get('/user/{id}', name='user_detail')
    def user_detail_handler(request, id):
        return {'user_id': id}

    @app.add_get('/post/{user_id}/{post_id}', name='user_post')
    def user_post_handler(request, user_id, post_id):
        return {'user_id': user_id, 'post_id': post_id}

    @app.add_post('/echo', name='echo')
    def echo_handler(request):
        return {'method': 'POST', 'data': request.data}

    @app.add_put('/resource/{id}', name='update_resource')
    def update_handler(request, id):
        return {'method': 'PUT', 'id': id}

    @app.add_delete('/resource/{id}', name='delete_resource')
    def delete_handler(request, id):
        return {'method': 'DELETE', 'id': id}

    @app.add_get('/bytes', name='bytes_response')
    def bytes_handler(request):
        return b'\x00\x01\x02\x03'

    @app.add_get('/tuple', name='tuple_response')
    def tuple_handler(request):
        return {'status': 'created', 'id': 42}

    @app.add_get('/start-response', name='start_response_test')
    def start_response_handler(request):
        request.start_response(201, [('Content-Type', 'text/plain')])
        return 'Created via start_response'

    @app.add_get('/async-handler', name='async_handler')
    async def async_handler(request):
        await asyncio.sleep(0)
        return {'async': True}

    @app.add_get('/error', name='error_handler')
    def error_handler(request):
        raise ValueError("test error")

    @app.add_get('/http-error', name='http_error_handler')
    def http_error_handler(request):
        raise HttpError(403, "Forbidden")

    @app.add_get('/headers', name='headers_echo')
    def headers_echo_handler(request):
        return {'x_custom': request.headers.get('x-custom', '')}

    return app


@pytest.fixture
def asgi_app(app):
    """返回 ASGI application callable"""
    return app.asgi()


async def invoke(asgi_app, scope, receive=None):
    """调用 ASGI application 并返回 SendCollector"""
    if receive is None:
        receive = make_receive()
    sender = SendCollector()
    await asgi_app(scope, receive, sender)
    return sender


# ==================== 测试类 ====================


class TestASGIIntegrationBasicMethods:
    """基本 HTTP 方法测试"""

    @pytest.mark.asyncio
    async def test_get_request(self, asgi_app):
        resp = await invoke(asgi_app, make_scope('GET', '/'))
        assert resp.status == 200
        assert b'Hello World' in resp.body

    @pytest.mark.asyncio
    async def test_post_request(self, asgi_app):
        body = b'key=value'
        scope = make_scope(
            'POST', '/echo',
            headers=[(b'content-type', b'application/x-www-form-urlencoded')],
        )
        resp = await invoke(asgi_app, scope, make_receive(body))
        assert resp.status == 200
        data = resp.body_json
        assert data['method'] == 'POST'
        assert data['data'] == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_put_request(self, asgi_app):
        scope = make_scope('PUT', '/resource/42')
        resp = await invoke(asgi_app, scope)
        assert resp.status == 200
        data = resp.body_json
        assert data['method'] == 'PUT'
        assert data['id'] == '42'

    @pytest.mark.asyncio
    async def test_delete_request(self, asgi_app):
        scope = make_scope('DELETE', '/resource/42')
        resp = await invoke(asgi_app, scope)
        assert resp.status == 200
        data = resp.body_json
        assert data['method'] == 'DELETE'
        assert data['id'] == '42'


class TestASGIIntegrationRouteMatching:
    """路由匹配与路径参数测试"""

    @pytest.mark.asyncio
    async def test_static_path(self, asgi_app):
        resp = await invoke(asgi_app, make_scope('GET', '/json'))
        assert resp.status == 200
        data = resp.body_json
        assert data['message'] == 'hello'

    @pytest.mark.asyncio
    async def test_single_path_parameter(self, asgi_app):
        resp = await invoke(asgi_app, make_scope('GET', '/user/123'))
        assert resp.status == 200
        data = resp.body_json
        assert data['user_id'] == '123'

    @pytest.mark.asyncio
    async def test_multiple_path_parameters(self, asgi_app):
        resp = await invoke(asgi_app, make_scope('GET', '/post/5/99'))
        assert resp.status == 200
        data = resp.body_json
        assert data['user_id'] == '5'
        assert data['post_id'] == '99'

    @pytest.mark.asyncio
    async def test_404_unmatched_route(self, asgi_app):
        resp = await invoke(asgi_app, make_scope('GET', '/nonexistent'))
        assert resp.status == 404

    @pytest.mark.asyncio
    async def test_query_string(self, asgi_app):
        resp = await invoke(asgi_app, make_scope('GET', '/', query_string=b'foo=bar'))
        assert resp.status == 200


class TestASGIIntegrationResponseTypes:
    """响应类型测试"""

    @pytest.mark.asyncio
    async def test_string_response_is_html(self, asgi_app):
        resp = await invoke(asgi_app, make_scope('GET', '/'))
        assert 'text/html' in resp.headers.get('Content-Type', '')

    @pytest.mark.asyncio
    async def test_dict_response_is_json(self, asgi_app):
        resp = await invoke(asgi_app, make_scope('GET', '/json'))
        assert 'application/json' in resp.headers.get('Content-Type', '')
        data = resp.body_json
        assert data['message'] == 'hello'

    @pytest.mark.asyncio
    async def test_bytes_response_is_octet_stream(self, asgi_app):
        resp = await invoke(asgi_app, make_scope('GET', '/bytes'))
        assert 'application/octet-stream' in resp.headers.get('Content-Type', '')
        assert resp.body == b'\x00\x01\x02\x03'

    @pytest.mark.asyncio
    async def test_custom_status_dict_response(self, asgi_app):
        """测试 dict 返回值自动序列化为 JSON"""
        resp = await invoke(asgi_app, make_scope('GET', '/tuple'))
        assert resp.status == 200
        data = resp.body_json
        assert data['status'] == 'created'
        assert data['id'] == 42

    @pytest.mark.asyncio
    async def test_start_response_without_session(self, asgi_app):
        """测试 start_response 在未加载会话时不崩溃"""
        resp = await invoke(asgi_app, make_scope('GET', '/start-response'))
        assert resp.status == 201
        assert b'Created via start_response' in resp.body


class TestASGIIntegrationRequestBody:
    """请求体解析测试"""

    @pytest.mark.asyncio
    async def test_json_body(self, asgi_app):
        body = json.dumps({'name': 'test'}).encode('utf-8')
        scope = make_scope(
            'POST', '/echo',
            headers=[
                (b'content-type', b'application/json'),
            ],
        )
        resp = await invoke(asgi_app, scope, make_receive(body))
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_urlencoded_form_body(self, asgi_app):
        body = b'username=alice&password=secret'
        scope = make_scope(
            'POST', '/echo',
            headers=[(b'content-type', b'application/x-www-form-urlencoded')],
        )
        resp = await invoke(asgi_app, scope, make_receive(body))
        assert resp.status == 200
        data = resp.body_json
        assert data['data']['username'] == 'alice'
        assert data['data']['password'] == 'secret'

    @pytest.mark.asyncio
    async def test_multipart_form_body(self, asgi_app):
        boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
        body = (
            f'------WebKitFormBoundary7MA4YWxkTrZu0gW\r\n'
            f'Content-Disposition: form-data; name="field1"\r\n'
            f'\r\n'
            f'value1\r\n'
            f'------WebKitFormBoundary7MA4YWxkTrZu0gW\r\n'
            f'Content-Disposition: form-data; name="file1"; filename="test.txt"\r\n'
            f'Content-Type: text/plain\r\n'
            f'\r\n'
            f'file content\r\n'
            f'------WebKitFormBoundary7MA4YWxkTrZu0gW--\r\n'
        ).encode('utf-8')
        scope = make_scope(
            'POST', '/echo',
            headers=[
                (b'content-type', f'multipart/form-data; boundary={boundary}'.encode()),
            ],
        )
        resp = await invoke(asgi_app, scope, make_receive(body))
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_chunked_body(self, asgi_app):
        """测试分多次接收的请求体"""
        body = b'key=value'
        scope = make_scope(
            'POST', '/echo',
            headers=[(b'content-type', b'application/x-www-form-urlencoded')],
        )
        # 第一次发送部分 body，第二次发送剩余
        chunk1 = body[:4]
        chunk2 = body[4:]
        call_count = 0

        async def receive():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {'type': 'http.request', 'body': chunk1, 'more_body': True}
            return {'type': 'http.request', 'body': chunk2, 'more_body': False}

        resp = await invoke(asgi_app, scope, receive)
        assert resp.status == 200
        data = resp.body_json
        assert data['data'] == {'key': 'value'}


class TestASGIIntegrationAsyncHandlers:
    """异步处理器测试"""

    @pytest.mark.asyncio
    async def test_async_handler(self, asgi_app):
        resp = await invoke(asgi_app, make_scope('GET', '/async-handler'))
        assert resp.status == 200
        data = resp.body_json
        assert data['async'] is True


class TestASGIIntegrationErrorHandling:
    """错误处理测试"""

    @pytest.mark.asyncio
    async def test_handler_exception_returns_500(self, asgi_app):
        resp = await invoke(asgi_app, make_scope('GET', '/error'))
        assert resp.status == 500

    @pytest.mark.asyncio
    async def test_http_error_returns_correct_status(self, asgi_app):
        resp = await invoke(asgi_app, make_scope('GET', '/http-error'))
        assert resp.status == 403

    @pytest.mark.asyncio
    async def test_unmatched_route_returns_404(self, asgi_app):
        resp = await invoke(asgi_app, make_scope('GET', '/does-not-exist'))
        assert resp.status == 404


class TestASGIIntegrationNonHTTPScope:
    """非 HTTP scope 测试"""

    @pytest.mark.asyncio
    async def test_websocket_scope_ignored(self, asgi_app):
        scope = {'type': 'websocket', 'path': '/'}
        sender = SendCollector()
        await asgi_app(scope, make_receive(), sender)
        assert len(sender.messages) == 0

    @pytest.mark.asyncio
    async def test_lifespan_scope_ignored(self, asgi_app):
        scope = {'type': 'lifespan'}
        sender = SendCollector()
        await asgi_app(scope, make_receive(), sender)
        assert len(sender.messages) == 0


class TestASGIIntegrationHeaders:
    """请求头与响应头测试"""

    @pytest.mark.asyncio
    async def test_request_headers_accessible(self, asgi_app):
        scope = make_scope(
            'GET', '/headers',
            headers=[(b'x-custom', b'my-value')],
        )
        resp = await invoke(asgi_app, scope)
        assert resp.status == 200
        data = resp.body_json
        assert data['x_custom'] == 'my-value'

    @pytest.mark.asyncio
    async def test_response_has_server_header(self, asgi_app):
        resp = await invoke(asgi_app, make_scope('GET', '/'))
        assert 'Server' in resp.headers

    @pytest.mark.asyncio
    async def test_json_response_has_content_type(self, asgi_app):
        resp = await invoke(asgi_app, make_scope('GET', '/json'))
        ct = resp.headers.get('Content-Type', '')
        assert 'application/json' in ct


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
