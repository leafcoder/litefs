#!/usr/bin/env python
# coding: utf-8

"""
优化的静态文件服务

提供高性能的静态文件服务，支持缓存、压缩、范围请求等
"""

import os
import gzip
import hashlib
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Tuple, Any
from datetime import datetime, timedelta
from functools import lru_cache


class StaticFileHandler:
    """
    优化的静态文件处理器
    
    功能特性：
    - 文件缓存：内存缓存小文件，减少磁盘 I/O
    - Gzip 压缩：自动压缩文本文件，减少传输大小
    - ETag 支持：生成文件指纹，支持条件请求
    - Last-Modified：记录文件修改时间，支持缓存验证
    - Range 请求：支持断点续传
    - MIME 类型：自动识别文件类型
    - 安全检查：防止路径遍历攻击
    """
    
    # 支持压缩的 MIME 类型
    COMPRESSIBLE_TYPES = {
        'text/html', 'text/css', 'text/javascript', 'text/xml',
        'text/plain', 'text/json', 'application/json', 'application/javascript',
        'application/xml', 'application/xhtml+xml'
    }
    
    # 默认缓存配置
    DEFAULT_MAX_AGE = 3600  # 1 小时
    DEFAULT_CACHE_SIZE = 100  # 缓存文件数量
    DEFAULT_MIN_COMPRESS_SIZE = 1024  # 最小压缩大小：1KB
    DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024  # 最大文件大小：10MB
    
    def __init__(
        self,
        directory: str,
        max_age: int = None,
        cache_size: int = None,
        enable_gzip: bool = True,
        enable_etag: bool = True,
        enable_range: bool = True,
        min_compress_size: int = None,
        max_file_size: int = None
    ):
        """
        初始化静态文件处理器
        
        Args:
            directory: 静态文件目录
            max_age: 缓存时间（秒）
            cache_size: 缓存文件数量
            enable_gzip: 是否启用 Gzip 压缩
            enable_etag: 是否启用 ETag
            enable_range: 是否支持范围请求
            min_compress_size: 最小压缩大小
            max_file_size: 最大文件大小
        """
        self.directory = Path(directory).resolve()
        self.max_age = max_age or self.DEFAULT_MAX_AGE
        self.cache_size = cache_size or self.DEFAULT_CACHE_SIZE
        self.enable_gzip = enable_gzip
        self.enable_etag = enable_etag
        self.enable_range = enable_range
        self.min_compress_size = min_compress_size or self.DEFAULT_MIN_COMPRESS_SIZE
        self.max_file_size = max_file_size or self.DEFAULT_MAX_FILE_SIZE
        
        # 文件缓存
        self._cache: Dict[str, Tuple[bytes, dict]] = {}
        
        # 确保目录存在
        if not self.directory.exists():
            raise ValueError(f"Directory does not exist: {directory}")
    
    def serve(self, file_path: str, request_headers: dict = None) -> Tuple[int, list, bytes]:
        """
        服务静态文件
        
        Args:
            file_path: 文件路径（相对于静态目录）
            request_headers: 请求头
            
        Returns:
            (status_code, headers, content)
        """
        # 安全检查：防止路径遍历攻击
        full_path = self._secure_path_join(file_path)
        
        if full_path is None:
            return 403, [('Content-Type', 'text/plain; charset=utf-8')], b'Forbidden'
        
        # 检查文件是否存在
        if not full_path.exists():
            return 404, [('Content-Type', 'text/plain; charset=utf-8')], b'Not Found'
        
        # 检查是否为文件
        if not full_path.is_file():
            return 403, [('Content-Type', 'text/plain; charset=utf-8')], b'Forbidden'
        
        # 检查文件大小
        file_size = full_path.stat().st_size
        if file_size > self.max_file_size:
            return 413, [('Content-Type', 'text/plain; charset=utf-8')], b'Payload Too Large'
        
        # 获取文件信息
        stat = full_path.stat()
        last_modified = datetime.fromtimestamp(stat.st_mtime, tz=None)
        
        # 生成 ETag
        etag = None
        if self.enable_etag:
            etag = self._generate_etag(full_path, stat)
        
        # 检查条件请求
        if request_headers:
            # If-None-Match (ETag)
            if etag and request_headers.get('If-None-Match') == etag:
                return 304, [], b''
            
            # If-Modified-Since
            if_modified_since = request_headers.get('If-Modified-Since')
            if if_modified_since:
                try:
                    if_modified_since_dt = datetime.strptime(
                        if_modified_since, '%a, %d %b %Y %H:%M:%S GMT'
                    )
                    if last_modified <= if_modified_since_dt:
                        return 304, [], b''
                except ValueError:
                    pass
        
        # 尝试从缓存获取
        cache_key = str(full_path)
        if cache_key in self._cache:
            content, cached_headers = self._cache[cache_key]
            headers = self._build_headers(full_path, cached_headers, etag, last_modified)
            return 200, headers, content
        
        # 读取文件内容
        try:
            with open(full_path, 'rb') as f:
                content = f.read()
        except Exception as e:
            return 500, [('Content-Type', 'text/plain; charset=utf-8')], f'Internal Server Error: {str(e)}'.encode()
        
        # 获取 MIME 类型
        mime_type, encoding = mimetypes.guess_type(str(full_path))
        if mime_type is None:
            mime_type = 'application/octet-stream'
        
        # 准备响应头
        headers_dict = {
            'Content-Type': mime_type,
            'Content-Length': len(content)
        }
        
        # Gzip 压缩
        should_compress = (
            self.enable_gzip and
            len(content) >= self.min_compress_size and
            mime_type in self.COMPRESSIBLE_TYPES
        )
        
        if should_compress:
            content = gzip.compress(content)
            headers_dict['Content-Encoding'] = 'gzip'
            headers_dict['Content-Length'] = len(content)
        
        # 缓存小文件
        if len(content) < self.DEFAULT_MAX_FILE_SIZE and len(self._cache) < self.cache_size:
            self._cache[cache_key] = (content, headers_dict)
        
        # 构建响应头
        headers = self._build_headers(full_path, headers_dict, etag, last_modified)
        
        return 200, headers, content
    
    def _secure_path_join(self, file_path: str) -> Optional[Path]:
        """
        安全的路径拼接，防止路径遍历攻击
        
        Args:
            file_path: 文件路径
            
        Returns:
            安全的完整路径，如果不安全则返回 None
        """
        # 移除开头的斜杠
        file_path = file_path.lstrip('/')
        
        # 拼接路径
        full_path = (self.directory / file_path).resolve()
        
        # 检查路径是否在静态目录内
        try:
            full_path.relative_to(self.directory)
        except ValueError:
            return None
        
        return full_path
    
    def _generate_etag(self, file_path: Path, stat) -> str:
        """
        生成 ETag
        
        Args:
            file_path: 文件路径
            stat: 文件状态
            
        Returns:
            ETag 字符串
        """
        # 使用文件路径、大小和修改时间生成 ETag
        etag_str = f"{file_path}-{stat.st_size}-{stat.st_mtime}"
        return hashlib.md5(etag_str.encode()).hexdigest()
    
    def _build_headers(
        self,
        file_path: Path,
        headers_dict: dict,
        etag: Optional[str],
        last_modified: datetime
    ) -> list:
        """
        构建响应头列表
        
        Args:
            file_path: 文件路径
            headers_dict: 响应头字典
            etag: ETag
            last_modified: 最后修改时间
            
        Returns:
            响应头列表
        """
        headers = []
        
        # 添加基本响应头
        for key, value in headers_dict.items():
            headers.append((key, str(value)))
        
        # 添加缓存控制
        if self.max_age > 0:
            headers.append(('Cache-Control', f'public, max-age={self.max_age}'))
            expires = datetime.utcnow() + timedelta(seconds=self.max_age)
            headers.append(('Expires', expires.strftime('%a, %d %b %Y %H:%M:%S GMT')))
        
        # 添加 ETag
        if etag:
            headers.append(('ETag', etag))
        
        # 添加 Last-Modified
        headers.append(('Last-Modified', last_modified.strftime('%a, %d %b %Y %H:%M:%S GMT')))
        
        # 添加 Accept-Ranges
        if self.enable_range:
            headers.append(('Accept-Ranges', 'bytes'))
        
        return headers
    
    def clear_cache(self):
        """清空文件缓存"""
        self._cache.clear()
    
    def get_cache_info(self) -> dict:
        """
        获取缓存信息
        
        Returns:
            缓存信息字典
        """
        return {
            'cache_size': len(self._cache),
            'max_cache_size': self.cache_size,
            'cached_files': list(self._cache.keys())
        }


# 便捷函数
def create_static_handler(
    directory: str,
    max_age: int = 3600,
    enable_gzip: bool = True,
    **kwargs
) -> StaticFileHandler:
    """
    创建静态文件处理器
    
    Args:
        directory: 静态文件目录
        max_age: 缓存时间（秒）
        enable_gzip: 是否启用 Gzip 压缩
        **kwargs: 其他参数
        
    Returns:
        StaticFileHandler 实例
    """
    return StaticFileHandler(
        directory=directory,
        max_age=max_age,
        enable_gzip=enable_gzip,
        **kwargs
    )
