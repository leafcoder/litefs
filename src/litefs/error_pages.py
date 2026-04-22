#!/usr/bin/env python
# coding: utf-8

"""
错误页面处理器

提供美观的错误页面渲染和自定义错误页面支持
"""

import os
from pathlib import Path
from typing import Dict, Optional, Tuple


class ErrorPageRenderer:
    """
    错误页面渲染器
    
    支持默认错误页面和自定义错误页面
    """

    DEFAULT_ERROR_TEMPLATES = {
        400: """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>400 - Bad Request</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .error-container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            padding: 60px 40px;
            text-align: center;
            max-width: 500px;
            width: 100%;
        }
        .error-code {
            font-size: 120px;
            font-weight: bold;
            color: #667eea;
            line-height: 1;
            margin-bottom: 20px;
        }
        .error-title {
            font-size: 28px;
            color: #333;
            margin-bottom: 15px;
        }
        .error-message {
            font-size: 16px;
            color: #666;
            line-height: 1.6;
            margin-bottom: 30px;
        }
        .error-detail {
            background: #f7f7f7;
            padding: 15px;
            border-radius: 8px;
            font-size: 14px;
            color: #888;
            margin-bottom: 30px;
        }
        .btn-home {
            display: inline-block;
            padding: 12px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 25px;
            font-weight: 500;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn-home:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-code">400</div>
        <h1 class="error-title">Bad Request</h1>
        <p class="error-message">
            The server could not understand your request. Please check the request format.
        </p>
        <div class="error-detail">
            {{ERROR_MESSAGE}}400 Bad Request<br>
            {{ERROR_DETAIL}}The client sent a malformed request
        </div>
        <a href="/" class="btn-home">Back to Home</a>
    </div>
</body>
</html>
        """,
        403: """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>403 - Forbidden</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .error-container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            padding: 60px 40px;
            text-align: center;
            max-width: 500px;
            width: 100%;
        }
        .error-icon {
            font-size: 80px;
            margin-bottom: 20px;
        }
        .error-code {
            font-size: 120px;
            font-weight: bold;
            color: #f5576c;
            line-height: 1;
            margin-bottom: 20px;
        }
        .error-title {
            font-size: 28px;
            color: #333;
            margin-bottom: 15px;
        }
        .error-message {
            font-size: 16px;
            color: #666;
            line-height: 1.6;
            margin-bottom: 30px;
        }
        .error-detail {
            background: #f7f7f7;
            padding: 15px;
            border-radius: 8px;
            font-size: 14px;
            color: #888;
            margin-bottom: 30px;
        }
        .btn-home {
            display: inline-block;
            padding: 12px 30px;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            text-decoration: none;
            border-radius: 25px;
            font-weight: 500;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn-home:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(245, 87, 108, 0.4);
        }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-icon">🔒</div>
        <div class="error-code">403</div>
        <h1 class="error-title">Forbidden</h1>
        <p class="error-message">
            You do not have permission to access this page. If you believe this is an error, please contact the administrator.
        </p>
        <div class="error-detail">
            {{ERROR_MESSAGE}}403 Forbidden<br>
            {{ERROR_DETAIL}}The server refused to process this request
        </div>
        <a href="/" class="btn-home">Back to Home</a>
    </div>
</body>
</html>
        """,
        404: """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>404 - Not Found</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .error-container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            padding: 60px 40px;
            text-align: center;
            max-width: 500px;
            width: 100%;
        }
        .error-icon {
            font-size: 80px;
            margin-bottom: 20px;
        }
        .error-code {
            font-size: 120px;
            font-weight: bold;
            color: #4facfe;
            line-height: 1;
            margin-bottom: 20px;
        }
        .error-title {
            font-size: 28px;
            color: #333;
            margin-bottom: 15px;
        }
        .error-message {
            font-size: 16px;
            color: #666;
            line-height: 1.6;
            margin-bottom: 30px;
        }
        .error-detail {
            background: #f7f7f7;
            padding: 15px;
            border-radius: 8px;
            font-size: 14px;
            color: #888;
            margin-bottom: 30px;
        }
        .btn-home {
            display: inline-block;
            padding: 12px 30px;
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            text-decoration: none;
            border-radius: 25px;
            font-weight: 500;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn-home:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(79, 172, 254, 0.4);
        }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-icon">🔍</div>
        <div class="error-code">404</div>
        <h1 class="error-title">Not Found</h1>
        <p class="error-message">
            Sorry, the page you are looking for does not exist or has been removed.
        </p>
        <div class="error-detail">
            {{ERROR_MESSAGE}}404 Not Found<br>
            {{ERROR_DETAIL}}The server could not find the requested resource
        </div>
        <a href="/" class="btn-home">Back to Home</a>
    </div>
</body>
</html>
        """,
        500: """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>500 - Internal Server Error</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .error-container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            padding: 60px 40px;
            text-align: center;
            max-width: 500px;
            width: 100%;
        }
        .error-icon {
            font-size: 80px;
            margin-bottom: 20px;
        }
        .error-code {
            font-size: 120px;
            font-weight: bold;
            color: #fa709a;
            line-height: 1;
            margin-bottom: 20px;
        }
        .error-title {
            font-size: 28px;
            color: #333;
            margin-bottom: 15px;
        }
        .error-message {
            font-size: 16px;
            color: #666;
            line-height: 1.6;
            margin-bottom: 30px;
        }
        .error-detail {
            background: #f7f7f7;
            padding: 15px;
            border-radius: 8px;
            font-size: 14px;
            color: #888;
            margin-bottom: 30px;
        }
        .btn-home {
            display: inline-block;
            padding: 12px 30px;
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
            color: white;
            text-decoration: none;
            border-radius: 25px;
            font-weight: 500;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn-home:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(250, 112, 154, 0.4);
        }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-icon">⚠️</div>
        <div class="error-code">500</div>
        <h1 class="error-title">Internal Server Error</h1>
        <p class="error-message">
            The server encountered an unexpected condition and could not complete your request. Please try again later.
        </p>
        <div class="error-detail">
            {{ERROR_MESSAGE}}500 Internal Server Error<br>
            {{ERROR_DETAIL}}The server encountered an unexpected condition
        </div>
        <a href="/" class="btn-home">Back to Home</a>
    </div>
</body>
</html>
        """,
        502: """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>502 - Bad Gateway</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .error-container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            padding: 60px 40px;
            text-align: center;
            max-width: 500px;
            width: 100%;
        }
        .error-icon {
            font-size: 80px;
            margin-bottom: 20px;
        }
        .error-code {
            font-size: 120px;
            font-weight: bold;
            color: #a8edea;
            line-height: 1;
            margin-bottom: 20px;
        }
        .error-title {
            font-size: 28px;
            color: #333;
            margin-bottom: 15px;
        }
        .error-message {
            font-size: 16px;
            color: #666;
            line-height: 1.6;
            margin-bottom: 30px;
        }
        .error-detail {
            background: #f7f7f7;
            padding: 15px;
            border-radius: 8px;
            font-size: 14px;
            color: #888;
            margin-bottom: 30px;
        }
        .btn-home {
            display: inline-block;
            padding: 12px 30px;
            background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
            color: white;
            text-decoration: none;
            border-radius: 25px;
            font-weight: 500;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn-home:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(168, 237, 234, 0.4);
        }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-icon">🌐</div>
        <div class="error-code">502</div>
        <h1 class="error-title">Bad Gateway</h1>
        <p class="error-message">
            The server, acting as a gateway or proxy, received an invalid response from the upstream server.
        </p>
        <div class="error-detail">
            {{ERROR_MESSAGE}}502 Bad Gateway<br>
            {{ERROR_DETAIL}}The upstream server returned an invalid response
        </div>
        <a href="/" class="btn-home">Back to Home</a>
    </div>
</body>
</html>
        """,
        503: """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>503 - Service Unavailable</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .error-container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            padding: 60px 40px;
            text-align: center;
            max-width: 500px;
            width: 100%;
        }
        .error-icon {
            font-size: 80px;
            margin-bottom: 20px;
        }
        .error-code {
            font-size: 120px;
            font-weight: bold;
            color: #ff9a9e;
            line-height: 1;
            margin-bottom: 20px;
        }
        .error-title {
            font-size: 28px;
            color: #333;
            margin-bottom: 15px;
        }
        .error-message {
            font-size: 16px;
            color: #666;
            line-height: 1.6;
            margin-bottom: 30px;
        }
        .error-detail {
            background: #f7f7f7;
            padding: 15px;
            border-radius: 8px;
            font-size: 14px;
            color: #888;
            margin-bottom: 30px;
        }
        .btn-home {
            display: inline-block;
            padding: 12px 30px;
            background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
            color: white;
            text-decoration: none;
            border-radius: 25px;
            font-weight: 500;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn-home:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(255, 154, 158, 0.4);
        }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-icon">🔧</div>
        <div class="error-code">503</div>
        <h1 class="error-title">Service Unavailable</h1>
        <p class="error-message">
            The server is currently unable to handle the request, possibly due to maintenance or overload. Please try again later.
        </p>
        <div class="error-detail">
            {{ERROR_MESSAGE}}503 Service Unavailable<br>
            {{ERROR_DETAIL}}The server is temporarily unable to handle the request
        </div>
        <a href="/" class="btn-home">Back to Home</a>
    </div>
</body>
</html>
        """,
        504: """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>504 - Gateway Timeout</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #fbc2eb 0%, #a6c1ee 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .error-container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            padding: 60px 40px;
            text-align: center;
            max-width: 500px;
            width: 100%;
        }
        .error-icon {
            font-size: 80px;
            margin-bottom: 20px;
        }
        .error-code {
            font-size: 120px;
            font-weight: bold;
            color: #fbc2eb;
            line-height: 1;
            margin-bottom: 20px;
        }
        .error-title {
            font-size: 28px;
            color: #333;
            margin-bottom: 15px;
        }
        .error-message {
            font-size: 16px;
            color: #666;
            line-height: 1.6;
            margin-bottom: 30px;
        }
        .error-detail {
            background: #f7f7f7;
            padding: 15px;
            border-radius: 8px;
            font-size: 14px;
            color: #888;
            margin-bottom: 30px;
        }
        .btn-home {
            display: inline-block;
            padding: 12px 30px;
            background: linear-gradient(135deg, #fbc2eb 0%, #a6c1ee 100%);
            color: white;
            text-decoration: none;
            border-radius: 25px;
            font-weight: 500;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn-home:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(251, 194, 235, 0.4);
        }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-icon">⏱️</div>
        <div class="error-code">504</div>
        <h1 class="error-title">Gateway Timeout</h1>
        <p class="error-message">
            The server, acting as a gateway or proxy, did not receive a timely response from the upstream server.
        </p>
        <div class="error-detail">
            {{ERROR_MESSAGE}}504 Gateway Timeout<br>
            {{ERROR_DETAIL}}The upstream server response timed out
        </div>
        <a href="/" class="btn-home">Back to Home</a>
    </div>
</body>
</html>
        """,
    }

    def __init__(self, custom_error_dir: Optional[str] = None):
        """
        初始化错误页面渲染器
        
        Args:
            custom_error_dir: 自定义错误页面目录路径
        """
        self._custom_error_dir = custom_error_dir
        self._custom_templates: Dict[int, str] = {}
        
        if custom_error_dir:
            self._load_custom_templates()

    def _load_custom_templates(self):
        """加载自定义错误页面模板"""
        if not self._custom_error_dir:
            return

        error_dir = Path(self._custom_error_dir)
        if not error_dir.exists():
            return

        for error_code in [400, 403, 404, 500, 502, 503, 504]:
            template_file = error_dir / f"{error_code}.html"
            if template_file.exists():
                with open(template_file, 'r', encoding='utf-8') as f:
                    self._custom_templates[error_code] = f.read()

    def render_error_page(
        self,
        status_code: int,
        message: Optional[str] = None,
        detail: Optional[str] = None
    ) -> str:
        """
        渲染错误页面
        
        Args:
            status_code: HTTP 状态码
            message: 自定义错误消息
            detail: 自定义错误详情
        
        Returns:
            HTML 错误页面
        """
        if status_code in self._custom_templates:
            template = self._custom_templates[status_code]
        elif status_code in self.DEFAULT_ERROR_TEMPLATES:
            template = self.DEFAULT_ERROR_TEMPLATES[status_code]
        else:
            template = self.DEFAULT_ERROR_TEMPLATES[500]

        if message:
            template = template.replace("{{ERROR_MESSAGE}}", f"{message}<br>")
        else:
            template = template.replace("{{ERROR_MESSAGE}}", "")
        if detail:
            template = template.replace("{{ERROR_DETAIL}}", f"{detail}<br>")
        else:
            template = template.replace("{{ERROR_DETAIL}}", "")

        return template

    def get_error_page(
        self,
        status_code: int,
        message: Optional[str] = None,
        detail: Optional[str] = None
    ) -> Tuple[int, str, str]:
        """
        获取错误页面
        
        Args:
            status_code: HTTP 状态码
            message: 自定义错误消息
            detail: 自定义错误详情
        
        Returns:
            (状态码, 内容类型, HTML 内容)
        """
        content = self.render_error_page(status_code, message, detail)
        return status_code, "text/html; charset=utf-8", content


__all__ = [
    "ErrorPageRenderer",
]
