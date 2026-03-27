#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import time
import threading
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs.cache import MemoryCache, TreeCache
from litefs.session import Session
from litefs.handlers.request import parse_form


class TestMemoryCacheStress(unittest.TestCase):
    """测试 MemoryCache 压力"""

    def test_concurrent_puts(self):
        """测试并发 put 操作"""
        cache = MemoryCache(max_size=10000)
        num_threads = 10
        operations_per_thread = 1000
        errors = []
        
        def put_worker(thread_id):
            try:
                for i in range(operations_per_thread):
                    cache.put(f'thread{thread_id}_key{i}', f'thread{thread_id}_value{i}')
            except Exception as e:
                errors.append(e)
        
        start_time = time.time()
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=put_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        end_time = time.time()
        
        elapsed = end_time - start_time
        total_operations = num_threads * operations_per_thread
        ops_per_second = total_operations / elapsed
        
        print(f'\nMemoryCache concurrent puts: {total_operations} operations in {elapsed:.4f}s ({ops_per_second:.2f} ops/s)')
        
        self.assertEqual(len(errors), 0, f'发生错误: {errors}')
        self.assertLess(elapsed, 5.0, '并发 put 操作应该在 5 秒内完成')

    def test_concurrent_gets(self):
        """测试并发 get 操作"""
        cache = MemoryCache(max_size=10000)
        
        for i in range(10000):
            cache.put(f'key{i}', f'value{i}')
        
        num_threads = 10
        operations_per_thread = 1000
        errors = []
        
        def get_worker(thread_id):
            try:
                for i in range(operations_per_thread):
                    cache.get(f'key{i}')
            except Exception as e:
                errors.append(e)
        
        start_time = time.time()
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=get_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        end_time = time.time()
        
        elapsed = end_time - start_time
        total_operations = num_threads * operations_per_thread
        ops_per_second = total_operations / elapsed
        
        print(f'MemoryCache concurrent gets: {total_operations} operations in {elapsed:.4f}s ({ops_per_second:.2f} ops/s)')
        
        self.assertEqual(len(errors), 0, f'发生错误: {errors}')
        self.assertLess(elapsed, 2.0, '并发 get 操作应该在 2 秒内完成')

    def test_concurrent_mixed_operations(self):
        """测试并发混合操作"""
        cache = MemoryCache(max_size=10000)
        num_threads = 10
        operations_per_thread = 500
        errors = []
        
        def mixed_worker(thread_id):
            try:
                for i in range(operations_per_thread):
                    if i % 3 == 0:
                        cache.put(f'thread{thread_id}_key{i}', f'thread{thread_id}_value{i}')
                    elif i % 3 == 1:
                        cache.get(f'key{i % 1000}')
                    else:
                        cache.delete(f'key{i % 1000}')
            except Exception as e:
                errors.append(e)
        
        start_time = time.time()
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=mixed_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        end_time = time.time()
        
        elapsed = end_time - start_time
        total_operations = num_threads * operations_per_thread
        ops_per_second = total_operations / elapsed
        
        print(f'MemoryCache concurrent mixed: {total_operations} operations in {elapsed:.4f}s ({ops_per_second:.2f} ops/s)')
        
        self.assertEqual(len(errors), 0, f'发生错误: {errors}')
        self.assertLess(elapsed, 5.0, '并发混合操作应该在 5 秒内完成')


class TestTreeCacheStress(unittest.TestCase):
    """测试 TreeCache 压力"""

    def test_concurrent_puts(self):
        """测试并发 put 操作"""
        cache = TreeCache(clean_period=60, expiration_time=3600)
        num_threads = 5
        operations_per_thread = 500
        errors = []
        lock = threading.Lock()
        
        def put_worker(thread_id):
            try:
                for i in range(operations_per_thread):
                    with lock:
                        cache.put(f'/path/thread{thread_id}/key{i}', f'thread{thread_id}_value{i}')
            except Exception as e:
                errors.append(e)
        
        start_time = time.time()
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=put_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        end_time = time.time()
        
        elapsed = end_time - start_time
        total_operations = num_threads * operations_per_thread
        ops_per_second = total_operations / elapsed
        
        print(f'\nTreeCache concurrent puts: {total_operations} operations in {elapsed:.4f}s ({ops_per_second:.2f} ops/s)')
        
        self.assertEqual(len(errors), 0, f'发生错误: {errors}')
        self.assertLess(elapsed, 10.0, '并发 put 操作应该在 10 秒内完成')

    def test_concurrent_gets(self):
        """测试并发 get 操作"""
        cache = TreeCache(clean_period=60, expiration_time=3600)
        
        for i in range(10000):
            cache.put(f'/path/key{i}', f'value{i}')
        
        num_threads = 10
        operations_per_thread = 1000
        errors = []
        
        def get_worker(thread_id):
            try:
                for i in range(operations_per_thread):
                    cache.get(f'/path/key{i}')
            except Exception as e:
                errors.append(e)
        
        start_time = time.time()
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=get_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        end_time = time.time()
        
        elapsed = end_time - start_time
        total_operations = num_threads * operations_per_thread
        ops_per_second = total_operations / elapsed
        
        print(f'TreeCache concurrent gets: {total_operations} operations in {elapsed:.4f}s ({ops_per_second:.2f} ops/s)')
        
        self.assertEqual(len(errors), 0, f'发生错误: {errors}')
        self.assertLess(elapsed, 5.0, '并发 get 操作应该在 5 秒内完成')


class TestParseFormStress(unittest.TestCase):
    """测试 parse_form 压力"""

    def test_concurrent_parsing(self):
        """测试并发解析"""
        query_string = "name=test&age=25&tags[]=python&tags[]=django&user[name]=jerry&user[age]=30"
        num_threads = 10
        operations_per_thread = 1000
        errors = []
        
        def parse_worker(thread_id):
            try:
                for i in range(operations_per_thread):
                    parse_form(query_string)
            except Exception as e:
                errors.append(e)
        
        start_time = time.time()
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=parse_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        end_time = time.time()
        
        elapsed = end_time - start_time
        total_operations = num_threads * operations_per_thread
        ops_per_second = total_operations / elapsed
        
        print(f'\nparse_form concurrent: {total_operations} operations in {elapsed:.4f}s ({ops_per_second:.2f} ops/s)')
        
        self.assertEqual(len(errors), 0, f'发生错误: {errors}')
        self.assertLess(elapsed, 2.0, '并发解析应该在 2 秒内完成')


class TestSessionStress(unittest.TestCase):
    """测试 Session 压力"""

    def test_concurrent_session_creation(self):
        """测试并发会话创建"""
        num_threads = 10
        sessions_per_thread = 1000
        errors = []
        
        def create_worker(thread_id):
            try:
                for i in range(sessions_per_thread):
                    session = Session(f'session_{thread_id}_{i}')
                    session.data['key'] = 'value'
            except Exception as e:
                errors.append(e)
        
        start_time = time.time()
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=create_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        end_time = time.time()
        
        elapsed = end_time - start_time
        total_sessions = num_threads * sessions_per_thread
        sessions_per_second = total_sessions / elapsed
        
        print(f'\nSession concurrent creation: {total_sessions} sessions in {elapsed:.4f}s ({sessions_per_second:.2f} sessions/s)')
        
        self.assertEqual(len(errors), 0, f'发生错误: {errors}')
        self.assertLess(elapsed, 5.0, '并发会话创建应该在 5 秒内完成')

    def test_concurrent_session_access(self):
        """测试并发会话访问"""
        session = Session('test_session')
        
        for i in range(100):
            session.data[f'key{i}'] = f'value{i}'
        
        num_threads = 10
        operations_per_thread = 1000
        errors = []
        
        def access_worker(thread_id):
            try:
                for i in range(operations_per_thread):
                    _ = session.data['key50']
            except Exception as e:
                errors.append(e)
        
        start_time = time.time()
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=access_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        end_time = time.time()
        
        elapsed = end_time - start_time
        total_operations = num_threads * operations_per_thread
        ops_per_second = total_operations / elapsed
        
        print(f'Session concurrent access: {total_operations} operations in {elapsed:.4f}s ({ops_per_second:.2f} ops/s)')
        
        self.assertEqual(len(errors), 0, f'发生错误: {errors}')
        self.assertLess(elapsed, 1.0, '并发会话访问应该在 1 秒内完成')


class TestMemoryLeak(unittest.TestCase):
    """测试内存泄漏"""

    def test_memory_cache_no_leak(self):
        """测试 MemoryCache 无内存泄漏"""
        import gc
        import sys
        
        cache = MemoryCache(max_size=1000)
        
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        for i in range(10000):
            cache.put(f'key{i}', f'value{i}')
            if i % 100 == 0:
                gc.collect()
        
        gc.collect()
        final_objects = len(gc.get_objects())
        
        object_increase = final_objects - initial_objects
        print(f'\nMemoryCache object increase: {object_increase}')
        
        self.assertLess(object_increase, 5000, '对象增长应该在合理范围内')

    def test_tree_cache_no_leak(self):
        """测试 TreeCache 无内存泄漏"""
        import gc
        import sys
        
        cache = TreeCache(clean_period=60, expiration_time=3600)
        
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        for i in range(10000):
            cache.put(f'/path/key{i}', f'value{i}')
            if i % 100 == 0:
                gc.collect()
        
        gc.collect()
        final_objects = len(gc.get_objects())
        
        object_increase = final_objects - initial_objects
        print(f'TreeCache object increase: {object_increase}')
        
        self.assertLess(object_increase, 15000, '对象增长应该在合理范围内')


if __name__ == '__main__':
    unittest.main(verbosity=2)
