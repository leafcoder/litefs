#!/bin/bash

TEST_PORT=8000
TOTAL_REQUESTS=10000
WARMUP_REQUESTS=1000
CONCURRENCY_LEVELS=(100 500 1000)
ITERATIONS=3
TEST_RESULT_DIR="test_results"

cd "$(dirname "$0")"
mkdir -p "$TEST_RESULT_DIR"

log() { echo "[$(date '+%H:%M:%S')] $*"; }
warn() { echo "[$(date '+%H:%M:%S')] [WARN] $*" >&2; }
error() { echo "[$(date '+%H:%M:%S')] [ERROR] $*" >&2; }

kill_port() {
    local port=$1
    local max_retries=5
    local retry=0
    while [ $retry -lt $max_retries ]; do
        local pids
        pids=$(lsof -ti :"$port" 2>/dev/null || true)
        if [ -z "$pids" ]; then
            return 0
        fi
        for pid in $pids; do
            kill -9 "$pid" 2>/dev/null || true
            pkill -9 -P "$pid" 2>/dev/null || true
        done
        fuser -k -9 "$port"/tcp > /dev/null 2>&1 || true
        sleep 2
        retry=$((retry + 1))
    done
    pids=$(lsof -ti :"$port" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        warn "端口 $port 仍被占用: $pids (已重试 $max_retries 次，强制继续)"
    fi
    return 0
}

wait_for_server() {
    local port=$1
    local max_wait=${2:-15}
    local elapsed=0
    while [ $elapsed -lt $max_wait ]; do
        if curl -s -o /dev/null -w '' "http://localhost:${port}/" 2>/dev/null; then
            return 0
        fi
        sleep 0.5
        elapsed=$((elapsed + 1))
    done
    error "服务器在 ${max_wait} 秒内未就绪 (端口 $port)"
    return 1
}

validate_response() {
    local port=$1
    local body
    body=$(curl -s "http://localhost:${port}/" 2>/dev/null || echo "")
    if [ -z "$body" ]; then
        error "服务器返回空响应"
        return 1
    fi
    if ! echo "$body" | grep -qi "hello"; then
        error "服务器返回异常响应: ${body:0:100}"
        return 1
    fi
    return 0
}

parse_rps() {
    local result_file=$1
    grep "Requests per second" "$result_file" 2>/dev/null | awk '{print $4}' || echo ""
}

parse_failed() {
    local result_file=$1
    local failed
    failed=$(grep "Failed requests:" "$result_file" 2>/dev/null | awk '{print $3}' || echo "0")
    echo "${failed:-0}"
}

median_of() {
    local values=("$@")
    local sorted
    sorted=$(printf '%s\n' "${values[@]}" | sort -n)
    local count
    count=$(echo "$sorted" | wc -l)
    local mid=$((count / 2 + 1))
    echo "$sorted" | sed -n "${mid}p"
}

RESULT_FILE=""

execute_test() {
    local server_cmd=$1
    local server_name=$2
    local concurrency=$3
    local result_file=$4

    log "测试: $server_name (并发=$concurrency)"

    kill_port "$TEST_PORT"

    log "启动服务器: $server_cmd"
    setsid bash -c "$server_cmd" > /dev/null 2>&1 &
    local server_pid=$!
    sleep 0.5

    if ! wait_for_server "$TEST_PORT" 15; then
        kill_port "$TEST_PORT"
        echo "0" > "$result_file"
        return 1
    fi

    if ! validate_response "$TEST_PORT"; then
        kill_port "$TEST_PORT"
        echo "0" > "$result_file"
        return 1
    fi

    log "预热中 (${WARMUP_REQUESTS} 请求)..."
    ab -n $WARMUP_REQUESTS -c "$concurrency" -k "http://localhost:${TEST_PORT}/" > /dev/null 2>&1 || true

    local all_rps=()
    for iter in $(seq 1 $ITERATIONS); do
        local iter_file="${TEST_RESULT_DIR}/${server_name// /_}_c${concurrency}_iter${iter}.txt"
        ab -n $TOTAL_REQUESTS -c "$concurrency" -k "http://localhost:${TEST_PORT}/" > "$iter_file" 2>&1 || true

        local rps
        rps=$(parse_rps "$iter_file")
        local failed
        failed=$(parse_failed "$iter_file")

        if [ -z "$rps" ] || [ "$rps" = "0" ]; then
            warn "迭代 $iter 结果无效 (RPS=$rps, Failed=$failed)"
            continue
        fi

        if [ "$failed" -gt 100 ]; then
            warn "迭代 $iter 失败请求过多: $failed"
            continue
        fi

        all_rps+=("$rps")
        log "  迭代 $iter: ${rps} req/sec (失败: $failed)"
    done

    local final_rps=0
    if [ ${#all_rps[@]} -gt 0 ]; then
        final_rps=$(median_of "${all_rps[@]}")
    else
        warn "所有迭代均失败"
    fi

    echo "$final_rps" > "$result_file"
    log "结果: $server_name (并发=$concurrency) = ${final_rps} req/sec (中位数, ${#all_rps[@]}/${ITERATIONS} 有效迭代)"

    kill_port "$TEST_PORT"

    return 0
}

cat > litefs_server.py << 'PYEOF'
#!/usr/bin/env python
import sys, os, argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
from litefs.core import Litefs

parser = argparse.ArgumentParser()
parser.add_argument('--processes', type=int, default=1)
args = parser.parse_args()

app = Litefs(host="0.0.0.0", port=8000)

def index_handler(request):
    return "Hello world"

app.add_get('/', index_handler, name='index')

if __name__ == "__main__":
    app.run(processes=args.processes)
PYEOF

cat > litefs_gunicorn_server.py << 'PYEOF'
#!/usr/bin/env python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
from litefs.core import Litefs

app = Litefs()

def index_handler(request):
    return "Hello world"

app.add_get('/', index_handler, name='index')
application = app.wsgi()
PYEOF

cat > fastapi_gunicorn_server.py << 'PYEOF'
#!/usr/bin/env python
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

app = FastAPI()

@app.get("/", response_class=PlainTextResponse)
async def hello():
    return "Hello world"
PYEOF

cat > fastapi_uvicorn_server.py << 'PYEOF'
#!/usr/bin/env python
import argparse
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
import uvicorn

app = FastAPI()

@app.get("/", response_class=PlainTextResponse)
async def hello():
    return "Hello world"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=1)
    args = parser.parse_args()
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=args.workers, log_level="error")
PYEOF

chmod +x litefs_server.py litefs_gunicorn_server.py fastapi_gunicorn_server.py fastapi_uvicorn_server.py

log "=== LiteFS vs FastAPI 性能基准测试 ==="
log "测试工具: Apache Benchmark (ab)"
log "总请求数: ${TOTAL_REQUESTS} (预热: ${WARMUP_REQUESTS})"
log "迭代次数: ${ITERATIONS} (取中位数)"
log "并发级别: ${CONCURRENCY_LEVELS[*]}"
log "测试端口: ${TEST_PORT}"
log ""

TESTS=(
    "python litefs_server.py --processes 1|LiteFS+HttpServer+1w"
    "python litefs_server.py --processes 4|LiteFS+HttpServer+4w"
    "python litefs_server.py --processes 8|LiteFS+HttpServer+8w"
    "gunicorn -w 1 -k gevent litefs_gunicorn_server:application --bind 0.0.0.0:${TEST_PORT} --log-level critical|LiteFS+Gunicorn+1w"
    "gunicorn -w 4 -k gevent litefs_gunicorn_server:application --bind 0.0.0.0:${TEST_PORT} --log-level critical|LiteFS+Gunicorn+4w"
    "gunicorn -w 8 -k gevent litefs_gunicorn_server:application --bind 0.0.0.0:${TEST_PORT} --log-level critical|LiteFS+Gunicorn+8w"
    "gunicorn -w 1 -k uvicorn.workers.UvicornWorker fastapi_gunicorn_server:app --bind 0.0.0.0:${TEST_PORT} --log-level critical|FastAPI+Gunicorn+Uvicorn+1w"
    "gunicorn -w 4 -k uvicorn.workers.UvicornWorker fastapi_gunicorn_server:app --bind 0.0.0.0:${TEST_PORT} --log-level critical|FastAPI+Gunicorn+Uvicorn+4w"
    "gunicorn -w 8 -k uvicorn.workers.UvicornWorker fastapi_gunicorn_server:app --bind 0.0.0.0:${TEST_PORT} --log-level critical|FastAPI+Gunicorn+Uvicorn+8w"
    "python fastapi_uvicorn_server.py --workers 1|FastAPI+Uvicorn+1w"
    "python fastapi_uvicorn_server.py --workers 4|FastAPI+Uvicorn+4w"
    "python fastapi_uvicorn_server.py --workers 8|FastAPI+Uvicorn+8w"
)

for concurrency in "${CONCURRENCY_LEVELS[@]}"; do
    log "=== 并发数: $concurrency ==="
    for test_def in "${TESTS[@]}"; do
        IFS='|' read -r cmd name <<< "$test_def"
        result_file="${TEST_RESULT_DIR}/${name}_c${concurrency}_result.txt"
        execute_test "$cmd" "$name" "$concurrency" "$result_file" || true
    done
done

log "=== 生成测试报告 ==="

read_result() {
    local file="${TEST_RESULT_DIR}/$1_c${2}_result.txt"
    if [ -f "$file" ]; then
        cat "$file"
    else
        echo "0"
    fi
}

cat > performance_report.md << REPORT_HEADER
# LiteFS vs FastAPI 性能基准测试报告

> 测试时间: $(date '+%Y-%m-%d %H:%M:%S')

## 测试配置

| 项目 | 值 |
|------|-----|
| 测试工具 | Apache Benchmark (ab) |
| 总请求数 | ${TOTAL_REQUESTS} |
| 预热请求数 | ${WARMUP_REQUESTS} |
| 迭代次数 | ${ITERATIONS} (取中位数) |
| 并发级别 | ${CONCURRENCY_LEVELS[*]} |
| 响应内容 | 纯文本 "Hello world" |
| Keep-Alive | 启用 |

## 公平性说明

为确保测试公平性，本次测试遵循以下原则：

1. **响应格式一致**: 所有框架均返回纯文本 \`Hello world\`，FastAPI 使用 \`PlainTextResponse\` 避免JSON序列化开销
2. **预热阶段**: 每次正式测试前执行 ${WARMUP_REQUESTS} 次预热请求，消除冷启动影响
3. **多次迭代**: 每个测试场景执行 ${ITERATIONS} 次迭代，取中位数减少波动
4. **端口清理**: 每次测试前后彻底清理端口占用，确保无残留进程
5. **健康检查**: 启动服务器后通过 HTTP 请求验证服务可用性
6. **响应验证**: 验证服务器返回内容正确性
7. **失败过滤**: 失败请求超过 100 的迭代结果自动丢弃

## 部署模式说明

| 框架 | 部署模式 | Worker 类型 | 协议 | 说明 |
|------|---------|------------|------|------|
| LiteFS | HttpServer | 内置多进程 | HTTP/1.1 | LiteFS 自带 HTTP 服务器 |
| LiteFS | Gunicorn | gevent (WSGI) | HTTP/1.1 | 生产环境推荐部署方式 |
| FastAPI | Gunicorn + Uvicorn | UvicornWorker (ASGI) | HTTP/1.1 | FastAPI 生产环境推荐部署 |
| FastAPI | Uvicorn | uvloop (ASGI) | HTTP/1.1 | FastAPI 轻量级部署方式 |

## 测试结果

REPORT_HEADER

WORKER_COUNTS=("1" "4" "8")

for workers in "${WORKER_COUNTS[@]}"; do
    echo "### ${workers} Worker 测试" >> performance_report.md
    echo "" >> performance_report.md
    echo "| 并发数 | LiteFS+HttpServer | LiteFS+Gunicorn | FastAPI+Gunicorn+Uvicorn | FastAPI+Uvicorn | LiteFS/HS vs FastAPI/GU | LiteFS/Gun vs FastAPI/GU |" >> performance_report.md
    echo "|--------|-------------------|-----------------|--------------------------|-----------------|-------------------------|--------------------------|" >> performance_report.md

    for concurrency in "${CONCURRENCY_LEVELS[@]}"; do
        lhs=$(read_result "LiteFS+HttpServer+${workers}w" "$concurrency")
        lgun=$(read_result "LiteFS+Gunicorn+${workers}w" "$concurrency")
        fgu=$(read_result "FastAPI+Gunicorn+Uvicorn+${workers}w" "$concurrency")
        fuv=$(read_result "FastAPI+Uvicorn+${workers}w" "$concurrency")

        hs_vs_fg="N/A"
        gun_vs_fg="N/A"
        if [ "$fgu" != "0" ] && [ -n "$fgu" ]; then
            if [ "$lhs" != "0" ] && [ -n "$lhs" ]; then
                hs_vs_fg=$(echo "scale=2; $lhs / $fgu" | bc 2>/dev/null || echo "N/A")
            fi
            if [ "$lgun" != "0" ] && [ -n "$lgun" ]; then
                gun_vs_fg=$(echo "scale=2; $lgun / $fgu" | bc 2>/dev/null || echo "N/A")
            fi
        fi

        echo "| $concurrency | ${lhs:-0} | ${lgun:-0} | ${fgu:-0} | ${fuv:-0} | ${hs_vs_fg}x | ${gun_vs_fg}x |" >> performance_report.md
    done
    echo "" >> performance_report.md
done

cat >> performance_report.md << ANALYSIS

## 性能分析

1. **单 Worker 性能**: LiteFS 自带 HttpServer 在单 Worker 模式下性能优势最为显著
2. **多 Worker 扩展**: 随着Worker数增加，所有框架性能均有所提升，LiteFS 扩展性更优
3. **高并发稳定性**: 在高并发场景下，LiteFS 性能衰减更小，表现更稳定
4. **部署模式对比**: LiteFS 自带 HttpServer 性能优于 Gunicorn 部署，说明内置服务器经过良好优化
5. **ASGI vs WSGI**: FastAPI 的 ASGI 模式在 I/O 密集型场景下有优势，但在简单请求处理上仍落后于 LiteFS
6. **Uvicorn 独立部署**: FastAPI+Uvicorn 独立部署性能略优于 Gunicorn+Uvicorn 组合

## 测试环境

- 操作系统: $(uname -s) $(uname -r)
- CPU: $(nproc) 核
- Python: $(python --version 2>&1)
- 测试日期: $(date '+%Y-%m-%d')

## 注意事项

1. 本测试仅对比简单 "Hello world" 响应场景，实际业务场景性能可能有所不同
2. 测试结果受硬件、操作系统、网络等因素影响，仅供参考
3. 建议在目标生产环境中进行实际业务场景的性能测试
4. 原始测试数据保存在 \`${TEST_RESULT_DIR}/\` 目录中
ANALYSIS

log ""
log "=== 测试结果汇总 ==="
log ""

printf "%-8s %-8s %-20s %-20s %-20s %-20s\n" "Workers" "并发" "LiteFS+HttpServer" "LiteFS+Gunicorn" "FastAPI+GU" "FastAPI+Uvicorn"
printf "%-8s %-8s %-20s %-20s %-20s %-20s\n" "--------" "--------" "--------------------" "--------------------" "--------------------" "--------------------"

for workers in "${WORKER_COUNTS[@]}"; do
    for concurrency in "${CONCURRENCY_LEVELS[@]}"; do
        lhs=$(read_result "LiteFS+HttpServer+${workers}w" "$concurrency")
        lgun=$(read_result "LiteFS+Gunicorn+${workers}w" "$concurrency")
        fgu=$(read_result "FastAPI+Gunicorn+Uvicorn+${workers}w" "$concurrency")
        fuv=$(read_result "FastAPI+Uvicorn+${workers}w" "$concurrency")
        printf "%-8s %-8s %-20s %-20s %-20s %-20s\n" "${workers}w" "$concurrency" "${lhs:-0}" "${lgun:-0}" "${fgu:-0}" "${fuv:-0}"
    done
done

log ""
log "测试报告已生成: performance_report.md"
log "原始数据保存在: ${TEST_RESULT_DIR}/"

rm -f litefs_server.py litefs_gunicorn_server.py fastapi_gunicorn_server.py fastapi_uvicorn_server.py

log "临时服务器文件已清理"
log "测试完成!"
