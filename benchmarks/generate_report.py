#!/usr/bin/env python3
"""
LiteFS 性能测试报告生成器
生成包含图表的 HTML 报告
"""
import json
from pathlib import Path
from datetime import datetime

def generate_html_report(data):
    """生成 HTML 报告"""
    
    # 按 RPS 排序
    sorted_data = sorted(data, key=lambda x: x['requests_per_sec'], reverse=True)
    
    # 生成表格行
    table_rows = ""
    for r in sorted_data:
        rps_color = "#2ecc71" if r['requests_per_sec'] > 10000 else "#f39c12" if r['requests_per_sec'] > 5000 else "#e74c3c"
        latency_color = "#2ecc71" if r['latency_p99_ms'] < 10 else "#f39c12" if r['latency_p99_ms'] < 20 else "#e74c3c"
        workers = r.get('workers', 1)
        badge = f"<span style='background:#3498db;color:white;padding:2px 8px;border-radius:12px;font-size:12px'>{workers}进程</span>"
        
        table_rows += f"""
        <tr>
            <td><strong>{r['name']}</strong>{badge if workers > 1 else ''}</td>
            <td style="color:{rps_color};font-weight:bold">{r['requests_per_sec']:,.2f}</td>
            <td>{r['latency_avg_ms']:.2f}ms</td>
            <td style="color:{latency_color};font-weight:bold">{r['latency_p99_ms']:.2f}ms</td>
            <td>{r['latency_max_ms']:.2f}ms</td>
            <td>{r['throughput_mb_per_sec']:.2f} MB/s</td>
            <td>{r['errors']:,}</td>
        </tr>
        """
    
    # 生成图表数据
    chart_labels = [f"'{r['name']}'" for r in sorted_data]
    chart_rps = [r['requests_per_sec'] for r in sorted_data]
    chart_latency = [r['latency_p99_ms'] for r in sorted_data]
    chart_throughput = [r['throughput_mb_per_sec'] for r in sorted_data]
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LiteFS 性能测试报告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            text-align: center;
            color: white;
            padding: 40px 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; font-size: 1.1em; }}
        .card {{
            background: white;
            border-radius: 16px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}
        .card h2 {{ 
            color: #2c3e50; 
            margin-bottom: 20px; 
            padding-bottom: 10px; 
            border-bottom: 2px solid #3498db;
        }}
        table {{ 
            width: 100%; 
            border-collapse: collapse; 
            margin-top: 15px;
        }}
        th, td {{ 
            padding: 12px 15px; 
            text-align: left; 
            border-bottom: 1px solid #ecf0f1; 
        }}
        th {{ 
            background: #3498db; 
            color: white; 
            font-weight: 600;
        }}
        tr:hover {{ background: #f8f9fa; }}
        .chart-container {{ 
            position: relative; 
            height: 400px; 
            margin: 20px 0;
        }}
        .stats {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 20px; 
            margin: 20px 0;
        }}
        .stat-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }}
        .stat-box .value {{ font-size: 2em; font-weight: bold; }}
        .stat-box .label {{ opacity: 0.9; margin-top: 5px; }}
        .highlight {{
            background: #fff3cd;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #ffc107;
            margin: 15px 0;
        }}
        .highlight h4 {{ color: #856404; margin-bottom: 10px; }}
        .tag {{
            display: inline-block;
            background: #e8f4f8;
            color: #3498db;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            margin: 3px;
        }}
        .footer {{
            text-align: center;
            color: rgba(255,255,255,0.7);
            padding: 20px;
            font-size: 14px;
        }}
        @media (max-width: 768px) {{
            .header h1 {{ font-size: 1.8em; }}
            table {{ font-size: 14px; }}
            th, td {{ padding: 8px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 LiteFS 性能测试报告</h1>
            <p>测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>测试环境: 4核 CPU | 50 并发连接 | 5 秒测试时长</p>
        </div>
        
        <div class="card">
            <h2>📊 性能概览</h2>
            <div class="stats">
                <div class="stat-box">
                    <div class="value">{max(r['requests_per_sec'] for r in sorted_data):,.0f}</div>
                    <div class="label">最高 RPS</div>
                </div>
                <div class="stat-box">
                    <div class="value">{min(r['latency_p99_ms'] for r in sorted_data):.2f}ms</div>
                    <div class="label">最低 P99 延迟</div>
                </div>
                <div class="stat-box">
                    <div class="value">{sum(r['workers'] for r in sorted_data)}</div>
                    <div class="label">测试场景数</div>
                </div>
                <div class="stat-box">
                    <div class="value">{max(r['requests_per_sec'] for r in sorted_data) / min(r['requests_per_sec'] for r in sorted_data):.1f}x</div>
                    <div class="label">性能差距</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>📈 RPS 性能对比</h2>
            <div class="chart-container">
                <canvas id="rpsChart"></canvas>
            </div>
        </div>
        
        <div class="card">
            <h2>⏱️ P99 延迟对比</h2>
            <div class="chart-container">
                <canvas id="latencyChart"></canvas>
            </div>
        </div>
        
        <div class="card">
            <h2>📋 详细测试结果</h2>
            <div class="highlight">
                <h4>💡 性能特点</h4>
                <ul style="margin-left: 20px; color: #856404;">
                    <li><strong>LiteFS-Asyncio</strong>: 原生异步支持，最高 RPS，最低 P99 延迟</li>
                    <li><strong>LiteFS-Greenlet</strong>: 协程切换开销低，稳定可靠</li>
                    <li><strong>多进程扩展</strong>: 可通过增加进程数线性提升吞吐量</li>
                </ul>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>服务器</th>
                        <th>RPS (req/s)</th>
                        <th>平均延迟</th>
                        <th>P99 延迟</th>
                        <th>最大延迟</th>
                        <th>吞吐量</th>
                        <th>错误数</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
        
        <div class="card">
            <h2>🏷️ 测试标签</h2>
            <div>
                <span class="tag">LiteFS</span>
                <span class="tag">Asyncio</span>
                <span class="tag">Greenlet</span>
                <span class="tag">WSGI</span>
                <span class="tag">ASGI</span>
                <span class="tag">FastAPI</span>
                <span class="tag">Gunicorn</span>
                <span class="tag">Uvicorn</span>
                <span class="tag">HTTP</span>
                <span class="tag">性能测试</span>
            </div>
        </div>
        
        <div class="footer">
            <p>Generated by LiteFS Benchmark Suite</p>
        </div>
    </div>
    
    <script>
        // RPS 图表
        new Chart(document.getElementById('rpsChart'), {{
            type: 'bar',
            data: {{
                labels: [{', '.join(chart_labels)}],
                datasets: [{{
                    label: 'Requests/sec',
                    data: {chart_rps},
                    backgroundColor: [
                        'rgba(46, 204, 113, 0.8)',
                        'rgba(52, 152, 219, 0.8)',
                        'rgba(155, 89, 182, 0.8)',
                        'rgba(241, 196, 15, 0.8)',
                        'rgba(231, 76, 60, 0.8)',
                        'rgba(26, 188, 156, 0.8)',
                        'rgba(52, 73, 94, 0.8)',
                        'rgba(230, 126, 34, 0.8)'
                    ],
                    borderColor: [
                        'rgba(46, 204, 113, 1)',
                        'rgba(52, 152, 219, 1)',
                        'rgba(155, 89, 182, 1)',
                        'rgba(241, 196, 15, 1)',
                        'rgba(231, 76, 60, 1)',
                        'rgba(26, 188, 156, 1)',
                        'rgba(52, 73, 94, 1)',
                        'rgba(230, 126, 34, 1)'
                    ],
                    borderWidth: 2,
                    borderRadius: 8
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return context.parsed.y.toLocaleString() + ' req/s';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{ display: true, text: 'Requests/sec' }},
                        grid: {{ color: 'rgba(0,0,0,0.1)' }}
                    }},
                    x: {{
                        grid: {{ display: false }},
                        ticks: {{ maxRotation: 45, minRotation: 45 }}
                    }}
                }}
            }}
        }});
        
        // 延迟图表
        new Chart(document.getElementById('latencyChart'), {{
            type: 'line',
            data: {{
                labels: [{', '.join(chart_labels)}],
                datasets: [{{
                    label: 'P99 Latency (ms)',
                    data: {chart_latency},
                    borderColor: 'rgba(231, 76, 60, 1)',
                    backgroundColor: 'rgba(231, 76, 60, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: 'rgba(231, 76, 60, 1)',
                    pointRadius: 6,
                    pointHoverRadius: 8
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return 'P99: ' + context.parsed.y.toFixed(2) + 'ms';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{ display: true, text: 'P99 Latency (ms)' }},
                        grid: {{ color: 'rgba(0,0,0,0.1)' }}
                    }},
                    x: {{
                        grid: {{ display: false }},
                        ticks: {{ maxRotation: 45, minRotation: 45 }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
'''
    return html

def main():
    # 读取测试数据
    data_path = Path(__file__).parent / 'results/latest/data.json'
    with open(data_path, 'r') as f:
        data = json.load(f)
    
    # 生成 HTML 报告
    html = generate_html_report(data)
    
    # 保存报告
    report_path = data_path.parent / 'report.html'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f'报告已生成: {report_path}')
    print(f'共 {len(data)} 条测试数据')
    
    # 打印汇总
    print('\n=== 测试汇总 ===')
    sorted_data = sorted(data, key=lambda x: x['requests_per_sec'], reverse=True)
    for r in sorted_data:
        print(f"{r['name']}: RPS={r['requests_per_sec']:,.2f}, P99={r['latency_p99_ms']:.2f}ms")

if __name__ == '__main__':
    main()
