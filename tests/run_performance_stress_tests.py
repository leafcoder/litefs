#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

if __name__ == '__main__':
    loader = unittest.TestLoader()
    
    print("=" * 60)
    print("Litefs 性能测试和压力测试")
    print("=" * 60)
    
    print("\n运行性能测试...")
    print("-" * 60)
    start_dir = os.path.join(os.path.dirname(__file__), 'performance')
    suite = loader.discover(start_dir, pattern='test_*.py')
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n运行压力测试...")
    print("-" * 60)
    start_dir = os.path.join(os.path.dirname(__file__), 'stress')
    suite = loader.discover(start_dir, pattern='test_*.py')
    runner = unittest.TextTestRunner(verbosity=2)
    result_stress = runner.run(suite)
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"性能测试: {result.testsRun} 个测试, {len(result.failures)} 个失败, {len(result.errors)} 个错误")
    print(f"压力测试: {result_stress.testsRun} 个测试, {len(result_stress.failures)} 个失败, {len(result_stress.errors)} 个错误")
    
    if result.wasSuccessful() and result_stress.wasSuccessful():
        print("\n✅ 所有测试通过!")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败!")
        sys.exit(1)
