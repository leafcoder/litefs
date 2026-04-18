"""pytest 配置"""

import pytest


def pytest_configure(config):
    """pytest 启动配置"""
    config.addinivalue_line("markers", "slow: 标记为慢速测试")
    config.addinivalue_line("markers", "benchmark: 性能测试")


def pytest_collection_modifyitems(config, items):
    """修改测试用例收集"""
    for item in items:
        if "benchmark" in item.keywords:
            item.add_marker(pytest.mark.slow)
