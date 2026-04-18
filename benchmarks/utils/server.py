"""服务器管理工具 - 统一管理不同类型服务器的启动和停止"""

import subprocess
import time
import signal
import os
from typing import Optional, List
from dataclasses import dataclass
import psutil


@dataclass
class ServerConfig:
    """服务器配置"""
    cmd: List[str]           # 启动命令
    port: int                # 端口
    name: str                # 服务器名称
    wait_ready: int = 3     # 启动等待时间(秒)
    cwd: Optional[str] = None  # 工作目录


class ServerManager:
    """统一管理不同类型服务器的启动和停止"""

    def __init__(self, config: ServerConfig):
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.process_group: Optional[psutil.Process] = None

    def start(self) -> None:
        """启动服务器"""
        print(f"[{self.config.name}] 启动命令: {' '.join(self.config.cmd)}")

        self.process = subprocess.Popen(
            self.config.cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.config.cwd,
            preexec_fn=os.setsid  # 创建新进程组
        )

        # 等待服务器就绪
        time.sleep(self.config.wait_ready)

        # 检查进程是否还在运行
        if self.process.poll() is not None:
            stdout, stderr = self.process.communicate()
            raise RuntimeError(
                f"[{self.config.name}] 服务器启动失败\n"
                f"stdout: {stdout.decode()}\n"
                f"stderr: {stderr.decode()}"
            )

        print(f"[{self.config.name}] 服务器已启动 (PID: {self.process.pid})")

    def stop(self) -> None:
        """停止服务器"""
        if self.process is None:
            return

        try:
            # 终止整个进程组
            pgid = os.getpgid(self.process.pid)
            os.killpg(pgid, signal.SIGTERM)

            # 等待进程结束
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(pgid, signal.SIGKILL)
                self.process.wait()

            print(f"[{self.config.name}] 服务器已停止")
        except (ProcessLookupError, psutil.NoSuchProcess):
            print(f"[{self.config.name}] 服务器进程不存在")
        finally:
            self.process = None

    def is_running(self) -> bool:
        """检查服务器是否运行"""
        if self.process is None:
            return False
        return self.process.poll() is None

    def get_pid(self) -> Optional[int]:
        """获取服务器 PID"""
        return self.process.pid if self.process else None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


def kill_port(port: int) -> None:
    """强制终止占用指定端口的进程"""
    try:
        proc = psutil.Process()
        for child in proc.children(recursive=True):
            try:
                for conn in child.connections():
                    if conn.laddr.port == port:
                        os.kill(child.pid, signal.SIGTERM)
            except (psutil.NoSuchProcess, PermissionError):
                pass
    except Exception:
        pass

    # 使用 lsof 查找并终止
    try:
        subprocess.run(
            f"lsof -ti:{port} | xargs kill -9 2>/dev/null || true",
            shell=True,
            capture_output=True
        )
    except Exception:
        pass
