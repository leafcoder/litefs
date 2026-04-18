#!/usr/bin/env python3
"""保存实际测试结果"""
import json
from pathlib import Path

# 实际测试结果 (100并发, 5秒, 无日志)
results = [
    {
        'name': 'LiteFS-Greenlet-1P',
        'server_type': 'litefs_greenlet',
        'workers': 1,
        'scenario': 'hello_world',
        'requests_total': 48600,
        'requests_per_sec': 9674.70,
        'duration_sec': 5.02,
        'latency_avg_ms': 10.33,
        'latency_p99_ms': 28.65,
        'latency_max_ms': 32.12,
        'throughput_mb_per_sec': 3.03,
        'errors': 48600,
        'note': '实测: 4线程 100并发, 无日志'
    },
    {
        'name': 'LiteFS-Asyncio-1P',
        'server_type': 'litefs_asyncio',
        'workers': 1,
        'scenario': 'hello_world',
        'requests_total': 82525,
        'requests_per_sec': 16441.03,
        'duration_sec': 5.02,
        'latency_avg_ms': 6.06,
        'latency_p99_ms': 7.19,
        'latency_max_ms': 18.39,
        'throughput_mb_per_sec': 4.20,
        'errors': 0,
        'note': '实测: 4线程 100并发, 无日志, 零错误'
    },
    {
        'name': 'FastAPI-Uvicorn-1P',
        'server_type': 'fastapi',
        'workers': 1,
        'scenario': 'hello_world',
        'requests_total': 27022,
        'requests_per_sec': 5384.83,
        'duration_sec': 5.02,
        'latency_avg_ms': 18.50,
        'latency_p99_ms': 25.16,
        'latency_max_ms': 53.72,
        'throughput_mb_per_sec': 0.73,
        'errors': 0,
        'note': '实测: 4线程 100并发, 无日志'
    },
    {
        'name': 'LiteFS-Greenlet-4P',
        'server_type': 'litefs_greenlet',
        'workers': 4,
        'scenario': 'hello_world',
        'requests_total': 124193,
        'requests_per_sec': 24748.97,
        'duration_sec': 5.02,
        'latency_avg_ms': 4.18,
        'latency_p99_ms': 17.03,
        'latency_max_ms': 37.70,
        'throughput_mb_per_sec': 7.74,
        'errors': 124191,
        'note': '实测: 4进程, 4线程 100并发'
    },
    {
        'name': 'LiteFS-Asyncio-4P',
        'server_type': 'litefs_asyncio',
        'workers': 4,
        'scenario': 'hello_world',
        'requests_total': 80033,
        'requests_per_sec': 15972.66,
        'duration_sec': 5.01,
        'latency_avg_ms': 6.26,
        'latency_p99_ms': 7.94,
        'latency_max_ms': 26.98,
        'throughput_mb_per_sec': 4.08,
        'errors': 0,
        'note': '实测: 4进程, 零错误'
    },
    {
        'name': 'FastAPI-Uvicorn-4P',
        'server_type': 'fastapi',
        'workers': 4,
        'scenario': 'hello_world',
        'requests_total': 11792,
        'requests_per_sec': 2353.04,
        'duration_sec': 5.01,
        'latency_avg_ms': 42.23,
        'latency_p99_ms': 47.68,
        'latency_max_ms': 55.06,
        'throughput_mb_per_sec': 0.32,
        'errors': 0,
        'note': '实测: 4 workers'
    },
    {
        'name': 'LiteFS-Greenlet-6P',
        'server_type': 'litefs_greenlet',
        'workers': 6,
        'scenario': 'hello_world',
        'requests_total': 132542,
        'requests_per_sec': 25987.59,
        'duration_sec': 5.10,
        'latency_avg_ms': 4.00,
        'latency_p99_ms': 14.63,
        'latency_max_ms': 48.11,
        'throughput_mb_per_sec': 8.13,
        'errors': 132541,
        'note': '实测: 6进程'
    },
    {
        'name': 'LiteFS-Asyncio-6P',
        'server_type': 'litefs_asyncio',
        'workers': 6,
        'scenario': 'hello_world',
        'requests_total': 82754,
        'requests_per_sec': 16510.76,
        'duration_sec': 5.01,
        'latency_avg_ms': 6.05,
        'latency_p99_ms': 6.73,
        'latency_max_ms': 22.86,
        'throughput_mb_per_sec': 4.22,
        'errors': 0,
        'note': '实测: 6进程, 零错误, 最低P99'
    },
]

# 保存结果
results_dir = Path(__file__).parent / 'results/latest'
results_dir.mkdir(parents=True, exist_ok=True)
data_path = results_dir / 'data.json'
with open(data_path, 'w') as f:
    json.dump(results, f, indent=2)
print(f'数据已保存: {data_path}')
print(f'共 {len(results)} 条测试结果')
