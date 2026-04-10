#!/bin/bash
# Flutter 项目快速部署脚本 (中国环境优化版)
# 用于快速初始化并运行 Flutter 项目

set -e

PROJECT_DIR="${1:-.}"
cd "$PROJECT_DIR"

echo "🚀 Flutter 中国环境快速部署"
echo "================================"

# 设置镜像环境变量
export PUB_HOSTED_URL="https://pub.flutter-io.cn"
export FLUTTER_STORAGE_BASE_URL="https://storage.flutter-io.cn"

echo "✅ 已设置 Flutter 镜像环境变量"

# 检查 FVM
if command -v fvm &> /dev/null; then
    echo "✅ 检测到 FVM"
    
    # 检查是否已安装 Flutter
    if ! fvm list | grep -q "stable"; then
        echo "📦 安装 Flutter stable 版本..."
        fvm install stable
    fi
    
    # 检查项目是否已绑定版本
    if [ ! -f ".fvm/fvm_config.json" ] && [ ! -f ".fvmrc" ]; then
        echo "📌 绑定项目 Flutter 版本..."
        fvm use stable --force
    fi
    
    FLUTTER_CMD="fvm flutter"
else
    echo "⚠️  未检测到 FVM，使用系统 Flutter"
    FLUTTER_CMD="flutter"
fi

# 获取依赖
echo "📦 获取依赖..."
$FLUTTER_CMD pub get

# 检查设备
echo "📱 检测设备..."
DEVICES=$($FLUTTER_CMD devices --machine 2>/dev/null | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -z "$DEVICES" ]; then
    echo "⚠️  未检测到设备，请连接设备或启动模拟器"
    echo "   运行: $FLUTTER_CMD devices 查看可用设备"
    exit 1
fi

echo "✅ 检测到设备: $DEVICES"

# 运行项目
echo "🏃 启动应用..."
$FLUTTER_CMD run -d "$DEVICES"
