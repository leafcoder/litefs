#!/usr/bin/env python
# coding: utf-8

"""
公共 API 契约测试

校验 :mod:`litefs._stable` 注册表与实际代码的一致性：

1. 登记的符号必须真实存在（防止登记了不存在的符号）。
2. 模块已公开的符号必须被登记（防止新增公共 API 漏分级）。
3. 新增模块必须被分级（防止新模块游离于契约之外）。
4. 同一符号不得同时属于两个分级。
5. 废弃登记表与别名表指向的符号必须真实存在。
"""

import importlib
import pkgutil
import unittest

import litefs
from litefs import _stable


def resolve(module_name, symbol):
    """解析模块内的符号（支持 ``Class.attr`` 形式的点号路径）"""
    obj = importlib.import_module(module_name)
    for part in symbol.split("."):
        obj = getattr(obj, part)
    return obj


class TestApiRegistryIntegrity(unittest.TestCase):
    """注册表内部一致性"""

    def setUp(self):
        self.registries = (
            ("STABLE", _stable.STABLE),
            ("PROVISIONAL", _stable.PROVISIONAL),
        )

    def test_registry_not_empty(self):
        """注册表非空且分级规模合理"""
        self.assertGreater(len(_stable.STABLE), 0)
        self.assertGreater(len(_stable.PROVISIONAL), 0)
        self.assertGreater(len(_stable.stable_symbols()), 100)
        self.assertGreater(len(_stable.provisional_symbols()), 10)

    def test_no_symbol_in_both_tiers(self):
        """同一符号不得同时属于 Tier 1 与 Tier 2"""
        stable = set(_stable.stable_symbols())
        provisional = set(_stable.provisional_symbols())
        self.assertEqual(stable & provisional, set())

    def test_module_not_in_both_tiers(self):
        """同一模块不得同时出现在两个分级中"""
        overlap = set(_stable.STABLE) & set(_stable.PROVISIONAL)
        self.assertEqual(overlap, set())

    def test_registered_symbols_exist(self):
        """登记的符号在目标模块中必须真实存在"""
        missing = []
        for _, registry in self.registries:
            for module_name, symbols in registry.items():
                module = importlib.import_module(module_name)
                for symbol in symbols:
                    if not hasattr(module, symbol):
                        missing.append("%s:%s" % (module_name, symbol))
        self.assertEqual(missing, [])

    def test_no_duplicate_symbol_in_module(self):
        """同一模块内符号不得重复登记"""
        for _, registry in self.registries:
            for module_name, symbols in registry.items():
                self.assertEqual(
                    len(symbols),
                    len(set(symbols)),
                    "模块 %s 存在重复登记符号" % module_name,
                )


class TestApiSurfaceCoverage(unittest.TestCase):
    """注册表对实际公共面的覆盖度"""

    def test_no_unclassified_public_symbol(self):
        """模块已公开的符号必须被分级登记"""
        unclassified = []
        for registry in (_stable.STABLE, _stable.PROVISIONAL):
            for module_name, symbols in registry.items():
                registered = set(symbols)
                for public in _stable.public_symbols(module_name):
                    if public not in registered:
                        unclassified.append("%s:%s" % (module_name, public))
        self.assertEqual(unclassified, [])

    def test_every_module_is_classified(self):
        """包内每个模块都必须被分级登记"""
        registered = set(_stable.STABLE) | set(_stable.PROVISIONAL)
        exempt = set(_stable.EXEMPT_MODULES)
        discovered = set()
        for module_info in pkgutil.walk_packages(litefs.__path__, prefix="litefs."):
            discovered.add(module_info.name)
        unclassified = sorted(discovered - registered - exempt)
        self.assertEqual(unclassified, [])

    def test_registered_modules_exist(self):
        """登记的模块必须真实存在"""
        registered = set(_stable.STABLE) | set(_stable.PROVISIONAL)
        for module_name in sorted(registered):
            self.assertTrue(
                importlib.util.find_spec(module_name) is not None,
                "模块 %s 不存在" % module_name,
            )


class TestApiTierLookup(unittest.TestCase):
    """分级查询接口"""

    def test_tier_of_stable_symbol(self):
        """Tier 1 符号查询结果为 stable"""
        self.assertEqual(_stable.api_tier("litefs.config", "Config"), "stable")
        self.assertEqual(_stable.api_tier("litefs.routing", "Router"), "stable")

    def test_tier_of_provisional_symbol(self):
        """Tier 2 符号查询结果为 provisional"""
        self.assertEqual(_stable.api_tier("litefs.i18n", "Translator"), "provisional")
        self.assertEqual(_stable.api_tier("litefs.mail", "SMTPClient"), "provisional")

    def test_tier_of_unknown_symbol(self):
        """未登记符号查询结果为 internal"""
        self.assertEqual(_stable.api_tier("litefs.config", "NotExists"), "internal")
        self.assertEqual(_stable.api_tier("litefs.not.a.module", "X"), "internal")

    def test_qualified_symbols_sorted(self):
        """扁平清单按字典序排列"""
        symbols = _stable.stable_symbols()
        self.assertEqual(list(symbols), sorted(symbols))
        self.assertIn("litefs.config:Config", symbols)


class TestDeprecationRegistry(unittest.TestCase):
    """废弃登记表与别名表"""

    def test_deprecated_symbols_exist(self):
        """废弃登记表中的符号必须真实存在"""
        for qualified in _stable.DEPRECATED:
            module_name, symbol = qualified.split(":", 1)
            self.assertIsNotNone(
                resolve(module_name, symbol),
                "废弃符号 %s 不存在" % qualified,
            )

    def test_deprecated_entries_are_complete(self):
        """废弃条目必须填写完整信息"""
        for qualified, info in _stable.DEPRECATED.items():
            self.assertTrue(info.since, "%s 缺少 since" % qualified)
            self.assertTrue(info.removal, "%s 缺少 removal" % qualified)
            self.assertTrue(info.reason, "%s 缺少 reason" % qualified)

    def test_alias_targets_exist(self):
        """别名表指向的规范符号必须真实存在"""
        for qualified, target in _stable.ALIASES.items():
            module_name, symbol = qualified.split(":", 1)
            self.assertIsNotNone(
                resolve(module_name, symbol),
                "别名 %s 不存在" % qualified,
            )
            target_module, target_symbol = target.split(":", 1)
            self.assertIsNotNone(
                resolve(target_module, target_symbol),
                "别名目标 %s 不存在" % target,
            )

    def test_alias_targets_are_stable(self):
        """别名目标必须属于 Tier 1 冻结契约"""
        stable = set(_stable.stable_symbols())
        for target in _stable.ALIASES.values():
            self.assertIn(target, stable)


if __name__ == "__main__":
    unittest.main()
