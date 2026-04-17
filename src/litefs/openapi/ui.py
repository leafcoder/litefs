#!/usr/bin/env python
# coding: utf-8

"""
Swagger UI 界面
"""


class SwaggerUI:
    """Swagger UI 界面生成器"""
    
    def __init__(self, docs_url: str = '/docs', openapi_url: str = '/openapi.json'):
        """
        初始化 Swagger UI
        
        Args:
            docs_url: 文档页面 URL
            openapi_url: OpenAPI JSON URL
        """
        self.docs_url = docs_url
        self.openapi_url = openapi_url
    
    def render_html(self, openapi_url: str = None) -> str:
        """
        渲染 Swagger UI HTML
        
        Args:
            openapi_url: OpenAPI JSON URL
            
        Returns:
            HTML 字符串
        """
        url = openapi_url or self.openapi_url
        
        return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>API Documentation</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
    <style>
        html {{
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }}
        *, *:before, *:after {{
            box-sizing: inherit;
        }}
        body {{
            margin: 0;
            padding: 0;
        }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {{
            const ui = SwaggerUIBundle({{
                url: "{url}",
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout"
            }});
            window.ui = ui;
        }};
    </script>
</body>
</html>'''
