#!/usr/bin/env python
# coding: utf-8

"""
错误页面渲染器

内部拆分模块：由 litefs.error_pages 再导出，不构成公共 API。
"""

from pathlib import Path
from typing import Dict, Optional, Tuple

from .templates_4xx import DEFAULT_ERROR_TEMPLATES_4XX
from .templates_5xx import DEFAULT_ERROR_TEMPLATES_5XX

# 合并后键序与拆分前保持一致：400, 403, 404, 500, 502, 503, 504
DEFAULT_ERROR_TEMPLATES = {**DEFAULT_ERROR_TEMPLATES_4XX, **DEFAULT_ERROR_TEMPLATES_5XX}


class ErrorPageRenderer:
    """
    错误页面渲染器

    支持默认错误页面和自定义错误页面
    """

    # 向后兼容：保持 ErrorPageRenderer.DEFAULT_ERROR_TEMPLATES 类属性可用
    DEFAULT_ERROR_TEMPLATES = DEFAULT_ERROR_TEMPLATES

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
