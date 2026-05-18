#!/usr/bin/env python
# coding: utf-8

"""
Radix Tree 实现，用于高效路由匹配

Radix Tree (基数树) 是一种压缩的 Trie 树，特别适合用于路由匹配
时间复杂度: O(k)，其中 k 是路径的长度
空间复杂度: O(n * k)，其中 n 是路由数量，k 是平均路径长度
"""


class RadixNode:
    """
    Radix Tree 节点
    """
    
    def __init__(self):
        self.children = {}
        self.routes = []  # 支持多个路由（不同方法）
        self.param_names = []
        self.is_static = False
        self.has_params = False
        self.has_wildcard = False


class RadixTree:
    """
    Radix Tree 路由树
    
    支持:
    - 静态路径匹配
    - 路径参数匹配 (如 /user/{id})
    - 通配符匹配 (如 /static/{file_path:path})
    """
    
    def __init__(self):
        self.root = RadixNode()
        self.named_routes = {}
    
    def insert(self, path: str, route):
        """
        插入路由到树中
        
        Args:
            path: 路由路径
            route: Route 对象
        """
        node = self.root
        
        # 解析路径段
        segments = self._parse_path(path)
        
        for segment in segments:
            # 处理静态段
            if not segment.startswith('{'):
                if segment not in node.children:
                    node.children[segment] = RadixNode()
                    node.children[segment].is_static = True
                node = node.children[segment]
                continue
            
            # 处理参数段
            param_name = segment[1:-1]  # 去掉花括号
            
            # 检查是否为通配符
            is_wildcard = False
            if ':' in param_name:
                param_name, param_type = param_name.split(':', 1)
                if param_type == 'path':
                    is_wildcard = True
                    node.has_wildcard = True
            
            node.has_params = True
            
            # 查找已存在的参数节点
            param_key = f':{param_name}'
            if param_key not in node.children:
                node.children[param_key] = RadixNode()
                node.children[param_key].param_names = [param_name]
                node.children[param_key].has_wildcard = is_wildcard
            node = node.children[param_key]
        
        # 在叶子节点存储路由信息（支持多个方法）
        node.routes.append(route)
        node.param_names = route.param_names
    
    def find(self, path: str, method: str = None):
        """
        在树中查找匹配的路由
        
        Args:
            path: 请求路径
            method: HTTP 方法（可选）
            
        Returns:
            匹配的 Route 对象列表，失败返回 None
        """
        node = self.root
        params = {}
        segments = self._parse_path(path)
        segment_count = len(segments)
        
        for i, segment in enumerate(segments):
            # 尝试匹配静态段（快速路径）
            static_child = node.children.get(segment)
            if static_child and static_child.is_static:
                node = static_child
                continue
            
            # 尝试匹配参数段
            found_param = False
            
            # 优先匹配普通参数
            for key, child in node.children.items():
                if key.startswith(':') and not child.has_wildcard:
                    # 普通参数，必须是非斜杠字符
                    if '/' not in segment:
                        param_name = key[1:]
                        params[param_name] = segment
                        node = child
                        found_param = True
                        break
            
            # 如果没有匹配普通参数，尝试匹配通配符
            if not found_param:
                for key, child in node.children.items():
                    if key.startswith(':') and child.has_wildcard:
                        # 通配符参数，匹配剩余路径
                        remaining = '/'.join(segments[i:])
                        param_name = key[1:]
                        params[param_name] = remaining
                        node = child
                        found_param = True
                        break
            
            if not found_param:
                return None
            
            # 如果匹配了通配符，直接跳出循环（匹配剩余所有路径段）
            if found_param and node.has_wildcard:
                break
        
        # 检查是否找到路由
        if not node.routes:
            return None
        
        # 处理方法匹配
        if method:
            method = method.upper()
            # 优先匹配精确方法
            for route in node.routes:
                if method in route.methods:
                    return route, params
            # 没有匹配的方法
            return None
        
        # 没有指定方法，返回第一个路由
        return node.routes[0], params
    
    def _parse_path(self, path: str):
        """
        解析路径为段列表
        
        Args:
            path: 路径字符串
            
        Returns:
            路径段列表
        """
        if not path:
            return []
        
        # 移除前导斜杠
        if path.startswith('/'):
            path = path[1:]
        
        # 移除尾部斜杠
        if path.endswith('/'):
            path = path[:-1]
        
        if not path:
            return []
        
        return path.split('/')
    
    def add_named_route(self, name: str, route):
        """
        添加命名路由
        
        Args:
            name: 路由名称
            route: Route 对象
        """
        self.named_routes[name] = route
    
    def get_named_route(self, name: str):
        """
        获取命名路由
        
        Args:
            name: 路由名称
            
        Returns:
            Route 对象，失败返回 None
        """
        return self.named_routes.get(name)

