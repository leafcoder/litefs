#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs.config import Config, load_config, merge_configs


class TestConfig(unittest.TestCase):
    """测试 Config 类"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'config.json')
    
    def tearDown(self):
        """清理测试环境"""
        if os.path.exists(self.config_file):
            os.remove(self.config_file)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)
    
    def test_default_config(self):
        """测试默认配置"""
        config = Config()
        
        self.assertEqual(config.host, 'localhost')
        self.assertEqual(config.port, 9090)
        self.assertEqual(config.debug, False)
        self.assertEqual(config.default_page, 'index,index.html')
        self.assertEqual(config.log, './default.log')
        self.assertEqual(config.listen, 1024)
        self.assertEqual(config.max_request_size, 10485760)
        self.assertEqual(config.max_upload_size, 52428800)
    
    def test_code_config(self):
        """测试代码配置"""
        config = Config(
            host='0.0.0.0',
            port=8080,
            debug=True,
        )
        
        self.assertEqual(config.host, '0.0.0.0')
        self.assertEqual(config.port, 8080)
        self.assertEqual(config.debug, True)
    
    def test_json_config(self):
        """测试 JSON 配置文件"""
        config_data = {
            'host': '0.0.0.0',
            'port': 8080,
            'debug': True,
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f)
        
        config = Config(config_file=self.config_file)
        
        self.assertEqual(config.host, '0.0.0.0')
        self.assertEqual(config.port, 8080)
        self.assertEqual(config.debug, True)
    
    def test_yaml_config(self):
        """测试 YAML 配置文件"""
        try:
            import yaml
            
            yaml_file = os.path.join(self.temp_dir, 'config.yaml')
            config_data = """
host: 0.0.0.0
port: 8080
debug: true
"""
            
            with open(yaml_file, 'w', encoding='utf-8') as f:
                f.write(config_data)
            
            config = Config(config_file=yaml_file)
            
            self.assertEqual(config.host, '0.0.0.0')
            self.assertEqual(config.port, 8080)
            self.assertEqual(config.debug, True)
            
            os.remove(yaml_file)
        except ImportError:
            self.skipTest("PyYAML not installed")
    
    def test_toml_config(self):
        """测试 TOML 配置文件"""
        try:
            import tomli
            
            toml_file = os.path.join(self.temp_dir, 'config.toml')
            config_data = """
host = "0.0.0.0"
port = 8080
debug = true
"""
            
            with open(toml_file, 'w', encoding='utf-8') as f:
                f.write(config_data)
            
            config = Config(config_file=toml_file)
            
            self.assertEqual(config.host, '0.0.0.0')
            self.assertEqual(config.port, 8080)
            self.assertEqual(config.debug, True)
            
            os.remove(toml_file)
        except ImportError:
            self.skipTest("tomli not installed")
    
    def test_env_config(self):
        """测试环境变量配置"""
        os.environ['LITEFS_HOST'] = '0.0.0.0'
        os.environ['LITEFS_PORT'] = '8080'
        os.environ['LITEFS_DEBUG'] = 'true'
        
        try:
            config = Config()
            
            self.assertEqual(config.host, '0.0.0.0')
            self.assertEqual(config.port, 8080)
            self.assertEqual(config.debug, True)
        finally:
            del os.environ['LITEFS_HOST']
            del os.environ['LITEFS_PORT']
            del os.environ['LITEFS_DEBUG']
    
    def test_env_config_type_parsing(self):
        """测试环境变量类型解析"""
        os.environ['LITEFS_PORT'] = '8080'
        os.environ['LITEFS_DEBUG'] = 'true'
        os.environ['LITEFS_MAX_REQUEST_SIZE'] = '20971520'
        
        try:
            config = Config()
            
            self.assertIsInstance(config.port, int)
            self.assertEqual(config.port, 8080)
            
            self.assertIsInstance(config.debug, bool)
            self.assertEqual(config.debug, True)
            
            self.assertIsInstance(config.max_request_size, int)
            self.assertEqual(config.max_request_size, 20971520)
        finally:
            del os.environ['LITEFS_PORT']
            del os.environ['LITEFS_DEBUG']
            del os.environ['LITEFS_MAX_REQUEST_SIZE']
    
    def test_mixed_config(self):
        """测试混合配置（配置文件 + 环境变量 + 代码）"""
        config_data = {
            'host': '0.0.0.0',
            'port': 8080,
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f)
        
        os.environ['LITEFS_DEBUG'] = 'true'
        
        try:
            config = Config(
                config_file=self.config_file,
                port=9090,
            )
            
            self.assertEqual(config.host, '0.0.0.0')
            self.assertEqual(config.port, 9090)
            self.assertEqual(config.debug, True)
        finally:
            del os.environ['LITEFS_DEBUG']
    
    def test_config_priority(self):
        """测试配置优先级：代码 > 环境变量 > 配置文件 > 默认值"""
        config_data = {
            'host': '0.0.0.0',
            'port': 8080,
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f)
        
        os.environ['LITEFS_PORT'] = '9000'
        
        try:
            config = Config(
                config_file=self.config_file,
                port=9090,
            )
            
            self.assertEqual(config.host, '0.0.0.0')
            self.assertEqual(config.port, 9090)
        finally:
            del os.environ['LITEFS_PORT']
    
    def test_get_method(self):
        """测试 get 方法"""
        config = Config()
        
        self.assertEqual(config.get('host'), 'localhost')
        self.assertEqual(config.get('port'), 9090)
        self.assertEqual(config.get('unknown', 'default'), 'default')
    
    def test_set_method(self):
        """测试 set 方法"""
        config = Config()
        
        config.set('host', '0.0.0.0')
        config.set('port', 8080)
        
        self.assertEqual(config.host, '0.0.0.0')
        self.assertEqual(config.port, 8080)
    
    def test_set_invalid_key(self):
        """测试设置无效键"""
        config = Config()
        
        with self.assertRaises(ValueError):
            config.set('invalid_key', 'value')
    
    def test_update_method(self):
        """测试 update 方法"""
        config = Config()
        
        config.update(
            host='0.0.0.0',
            port=8080,
            debug=True,
        )
        
        self.assertEqual(config.host, '0.0.0.0')
        self.assertEqual(config.port, 8080)
        self.assertEqual(config.debug, True)
    
    def test_to_dict(self):
        """测试 to_dict 方法"""
        config = Config()
        
        config_dict = config.to_dict()
        
        self.assertIsInstance(config_dict, dict)
        self.assertEqual(config_dict['host'], 'localhost')
        self.assertEqual(config_dict['port'], 9090)
    
    def test_attribute_access(self):
        """测试属性访问"""
        config = Config()
        
        self.assertEqual(config.host, 'localhost')
        self.assertEqual(config.port, 9090)
        
        config.host = '0.0.0.0'
        config.port = 8080
        
        self.assertEqual(config.host, '0.0.0.0')
        self.assertEqual(config.port, 8080)
    
    def test_invalid_attribute_access(self):
        """测试无效属性访问"""
        config = Config()
        
        with self.assertRaises(AttributeError):
            _ = config.invalid_key
        
        with self.assertRaises(AttributeError):
            config.invalid_key = 'value'
    
    def test_contains(self):
        """测试 in 操作符"""
        config = Config()
        
        self.assertIn('host', config)
        self.assertIn('port', config)
        self.assertNotIn('invalid_key', config)
    
    def test_keys(self):
        """测试 keys 方法"""
        config = Config()
        
        keys = config.keys()
        
        self.assertIsInstance(keys, list)
        self.assertIn('host', keys)
        self.assertIn('port', keys)
    
    def test_values(self):
        """测试 values 方法"""
        config = Config()
        
        values = config.values()
        
        self.assertIsInstance(values, list)
        self.assertIn('localhost', values)
        self.assertIn(9090, values)
    
    def test_items(self):
        """测试 items 方法"""
        config = Config()
        
        items = config.items()
        
        self.assertIsInstance(items, list)
        self.assertIn(('host', 'localhost'), items)
        self.assertIn(('port', 9090), items)
    
    def test_repr(self):
        """测试 __repr__ 方法"""
        config = Config()
        
        repr_str = repr(config)
        
        self.assertIn('Config', repr_str)
        self.assertIn('host', repr_str)


class TestLoadConfig(unittest.TestCase):
    """测试 load_config 函数"""

    def test_load_config_without_file(self):
        """测试不使用配置文件加载配置"""
        config = load_config(
            host='0.0.0.0',
            port=8080,
        )
        
        self.assertEqual(config.host, '0.0.0.0')
        self.assertEqual(config.port, 8080)
    
    def test_load_config_with_file(self):
        """测试使用配置文件加载配置"""
        temp_dir = tempfile.mkdtemp()
        config_file = os.path.join(temp_dir, 'config.json')
        
        try:
            config_data = {
                'host': '0.0.0.0',
                'port': 8080,
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f)
            
            config = load_config(config_file=config_file)
            
            self.assertEqual(config.host, '0.0.0.0')
            self.assertEqual(config.port, 8080)
        finally:
            if os.path.exists(config_file):
                os.remove(config_file)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
    
    def test_load_config_with_env_prefix(self):
        """测试使用自定义环境变量前缀"""
        os.environ['CUSTOM_HOST'] = '0.0.0.0'
        os.environ['CUSTOM_PORT'] = '8080'
        
        try:
            config = load_config(env_prefix='CUSTOM_')
            
            self.assertEqual(config.host, '0.0.0.0')
            self.assertEqual(config.port, 8080)
        finally:
            del os.environ['CUSTOM_HOST']
            del os.environ['CUSTOM_PORT']


class TestMergeConfigs(unittest.TestCase):
    """测试 merge_configs 函数"""

    def test_merge_configs_with_config_objects(self):
        """测试合并 Config 对象"""
        config1 = Config()
        config1.update(host='0.0.0.0', port=8080)
        
        config2 = Config()
        config2.update(debug=True, port=9090)
        
        merged = merge_configs(config1, config2)
        
        self.assertEqual(merged.port, 9090)
        self.assertEqual(merged.debug, True)
    
    def test_merge_configs_with_dicts(self):
        """测试合并字典"""
        dict1 = {'host': '0.0.0.0', 'port': 8080}
        dict2 = {'debug': True, 'port': 9090}
        
        merged = merge_configs(dict1, dict2)
        
        self.assertEqual(merged.host, '0.0.0.0')
        self.assertEqual(merged.port, 9090)
        self.assertEqual(merged.debug, True)
    
    def test_merge_configs_mixed(self):
        """测试混合合并 Config 对象和字典"""
        config = Config()
        config.update(host='0.0.0.0', port=8080)
        dict_config = {'debug': True, 'port': 9090}
        
        merged = merge_configs(config, dict_config)
        
        self.assertEqual(merged.host, '0.0.0.0')
        self.assertEqual(merged.port, 9090)
        self.assertEqual(merged.debug, True)


if __name__ == '__main__':
    unittest.main()
