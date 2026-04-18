"""测试报告生成工具 - 生成 JSON 和 HTML 图表报告"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


@dataclass
class TestReport:
    """测试报告"""
    timestamp: str
    duration: int
    connections: int
    threads: int
    results: List[Dict[str, Any]]

    def to_json(self, filepath: str) -> None:
        """保存为 JSON 文件"""
        data = asdict(self)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"JSON 报告已保存: {filepath}")

    @classmethod
    def from_results(cls, results: List[Dict], duration: int, connections: int, threads: int) -> 'TestReport':
        """从测试结果创建报告"""
        return cls(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            duration=duration,
            connections=connections,
            threads=threads,
            results=results,
        )


def create_comparison_chart(results: List[Dict], scenario: str = "hello_world") -> go.Figure:
    """创建性能对比图表"""
    df = pd.DataFrame(results)
    df = df[df['scenario'] == scenario].copy()

    # 创建子图
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["每秒请求数 (RPS)", "平均延迟 (ms)", "P99 延迟 (ms)", "吞吐量 (MB/s)"],
        specs=[[{"type": "bar"}, {"type": "bar"}],
               [{"type": "bar"}, {"type": "bar"}]]
    )

    # 按 RPS 排序
    df = df.sort_values('requests_per_sec', ascending=False)

    colors = px.colors.qualitative.Set2[:len(df)]

    # RPS 对比
    fig.add_trace(
        go.Bar(x=df['name'], y=df['requests_per_sec'], marker_color=colors, name="RPS"),
        row=1, col=1
    )

    # 平均延迟
    fig.add_trace(
        go.Bar(x=df['name'], y=df['latency_avg_ms'], marker_color=colors, name="延迟 AVG"),
        row=1, col=2
    )

    # P99 延迟
    fig.add_trace(
        go.Bar(x=df['name'], y=df['latency_p99_ms'], marker_color=colors, name="延迟 P99"),
        row=2, col=1
    )

    # 吞吐量
    fig.add_trace(
        go.Bar(x=df['name'], y=df['throughput_mb_s'], marker_color=colors, name="吞吐量"),
        row=2, col=2
    )

    fig.update_layout(
        title_text=f"性能测试对比 - {scenario.replace('_', ' ').title()}",
        showlegend=False,
        height=800,
        font=dict(size=10),
    )

    return fig


def create_latency_distribution_chart(results: List[Dict], scenario: str = "hello_world") -> go.Figure:
    """创建延迟分布图表"""
    df = pd.DataFrame(results)
    df = df[df['scenario'] == scenario].copy()

    fig = go.Figure()

    percentiles = ['p50', 'p75', 'p90', 'p99']
    labels = ['P50', 'P75', 'P90', 'P99']
    colors = px.colors.sequential.Viridis[:4]

    for i, (pct, label) in enumerate(zip(percentiles, labels)):
        col_name = f'latency_{pct}_ms'
        if col_name in df.columns:
            fig.add_trace(go.Bar(
                name=label,
                x=df['name'],
                y=df[col_name],
                marker_color=colors[i],
            ))

    fig.update_layout(
        title="延迟分布对比 (ms)",
        barmode='group',
        height=500,
        yaxis_title="延迟 (ms)",
        font=dict(size=10),
    )

    return fig


def create_worker_scaling_chart(results: List[Dict], scenario: str = "hello_world") -> go.Figure:
    """创建多进程扩展性图表"""
    df = pd.DataFrame(results)
    df = df[df['scenario'] == scenario].copy()

    fig = go.Figure()

    for server_type in df['server_type'].unique():
        server_df = df[df['server_type'] == server_type].sort_values('workers')
        fig.add_trace(go.Scatter(
            x=server_df['workers'],
            y=server_df['requests_per_sec'],
            mode='lines+markers',
            name=server_type,
            marker=dict(size=10),
        ))

    fig.update_layout(
        title="多进程扩展性对比",
        xaxis_title="进程数",
        yaxis_title="每秒请求数 (RPS)",
        height=500,
    )

    return fig


def generate_html_report(results: List[Dict], duration: int, connections: int, threads: int, output_dir: str) -> str:
    """生成完整的 HTML 报告"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 创建图表
    fig_rps = create_comparison_chart(results, "hello_world")
    fig_sql = create_comparison_chart(results, "sql_query")
    fig_latency = create_latency_distribution_chart(results, "hello_world")
    fig_scaling = create_worker_scaling_chart(results, "hello_world")

    # 转换为 HTML
    rps_html = fig_rps.to_html(full_html=False, include_plotlyjs='cdn')
    sql_html = fig_sql.to_html(full_html=False, include_plotlyjs=False)
    latency_html = fig_latency.to_html(full_html=False, include_plotlyjs=False)
    scaling_html = fig_scaling.to_html(full_html=False, include_plotlyjs=False)

    # 生成数据表格
    df = pd.DataFrame(results)
    table_html = df.to_html(classes='data-table', index=False, escape=False)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LiteFS 性能测试报告</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px; border-radius: 10px; margin-bottom: 30px; }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header .meta {{ opacity: 0.9; font-size: 0.9em; }}
        .card {{ background: white; border-radius: 10px; padding: 25px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .card h2 {{ color: #667eea; margin-bottom: 20px; border-bottom: 2px solid #667eea; padding-bottom: 10px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .stat {{ background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .stat .value {{ font-size: 2em; font-weight: bold; color: #667eea; }}
        .stat .label {{ color: #666; font-size: 0.9em; }}
        .chart-container {{ margin: 20px 0; }}
        table.data-table {{ width: 100%; border-collapse: collapse; font-size: 0.85em; }}
        table.data-table th {{ background: #667eea; color: white; padding: 12px; text-align: left; }}
        table.data-table td {{ padding: 10px; border-bottom: 1px solid #eee; }}
        table.data-table tr:hover {{ background: #f8f8ff; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.8em; font-weight: bold; }}
        .badge-success {{ background: #d4edda; color: #155724; }}
        .badge-warning {{ background: #fff3cd; color: #856404; }}
        .badge-danger {{ background: #f8d7da; color: #721c24; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>LiteFS 性能测试报告</h1>
            <div class="meta">生成时间: {timestamp} | 测试时长: {duration}s | 并发连接: {connections} | 线程数: {threads}</div>
        </div>

        <div class="stats">
            <div class="stat">
                <div class="value">{len(results)}</div>
                <div class="label">测试场景数</div>
            </div>
            <div class="stat">
                <div class="value">{df['total_requests'].sum():,}</div>
                <div class="label">总请求数</div>
            </div>
            <div class="stat">
                <div class="value">{df['requests_per_sec'].max():,.0f}</div>
                <div class="label">最高 RPS</div>
            </div>
            <div class="stat">
                <div class="value">{df[df['scenario']=='hello_world']['requests_per_sec'].mean():,.0f}</div>
                <div class="label">平均 RPS</div>
            </div>
        </div>

        <div class="card">
            <h2>Hello World 性能对比</h2>
            <div class="chart-container">{rps_html}</div>
        </div>

        <div class="card">
            <h2>SQL 查询性能对比</h2>
            <div class="chart-container">{sql_html}</div>
        </div>

        <div class="card">
            <h2>延迟分布对比</h2>
            <div class="chart-container">{latency_html}</div>
        </div>

        <div class="card">
            <h2>多进程扩展性</h2>
            <div class="chart-container">{scaling_html}</div>
        </div>

        <div class="card">
            <h2>详细测试数据</h2>
            {table_html}
        </div>

        <div class="footer">
            <p>LiteFS 性能测试套件 | Powered by wrk + Plotly</p>
        </div>
    </div>
</body>
</html>"""

    output_path = os.path.join(output_dir, "report.html")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"HTML 报告已保存: {output_path}")
    return output_path


def print_summary(results: List[Dict]) -> None:
    """打印测试摘要"""
    df = pd.DataFrame(results)

    print("\n" + "="*80)
    print("性能测试摘要")
    print("="*80)

    # Hello World 测试结果
    hello_df = df[df['scenario'] == 'hello_world'].sort_values('requests_per_sec', ascending=False)
    print("\n📊 Hello World 性能测试 (按 RPS 排序)")
    print("-"*80)
    print(f"{'服务器':<30} {'进程':<6} {'RPS':<12} {'延迟 AVG':<12} {'P99':<12} {'错误率':<10}")
    print("-"*80)

    for _, row in hello_df.iterrows():
        errors = f"{row['errors_percent']:.2f}%"
        badge = "✅" if row['errors_percent'] < 1 else "⚠️"
        print(f"{row['name']:<30} {row['workers']:<6} {row['requests_per_sec']:<12.0f} {row['latency_avg_ms']:<12.2f} {row['latency_p99_ms']:<12.2f} {errors:<10} {badge}")

    # SQL 查询测试结果
    sql_df = df[df['scenario'] == 'sql_query'].sort_values('requests_per_sec', ascending=False)
    print("\n📊 SQL 查询性能测试 (按 RPS 排序)")
    print("-"*80)
    print(f"{'服务器':<30} {'进程':<6} {'RPS':<12} {'延迟 AVG':<12} {'P99':<12} {'错误率':<10}")
    print("-"*80)

    for _, row in sql_df.iterrows():
        errors = f"{row['errors_percent']:.2f}%"
        badge = "✅" if row['errors_percent'] < 1 else "⚠️"
        print(f"{row['name']:<30} {row['workers']:<6} {row['requests_per_sec']:<12.0f} {row['latency_avg_ms']:<12.2f} {row['latency_p99_ms']:<12.2f} {errors:<10} {badge}")

    print("\n" + "="*80)
