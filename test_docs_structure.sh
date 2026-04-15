#!/bin/bash
# 文档结构测试脚本

echo "=== Litefs 文档结构测试 ==="
echo ""

# 检查必要文件是否存在
echo "检查必要文件..."
files=(
    "README.md"
    "index.html"
    "_sidebar.md"
    "docs/README.md"
    "docs/DOCUMENTATION_UPDATE.md"
    "docs/source/getting-started.md"
    "docs/source/routing-guide.md"
    "docs/source/middleware-guide.md"
    "docs/source/cache-system.md"
    "docs/source/session-management.md"
    "docs/source/wsgi-deployment.md"
    "docs/source/asgi-deployment.md"
)

missing_files=0
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file"
    else
        echo "✗ $file (缺失)"
        ((missing_files++))
    fi
done

echo ""
if [ $missing_files -eq 0 ]; then
    echo "✓ 所有必要文件都存在"
else
    echo "✗ 缺失 $missing_files 个文件"
fi

# 检查 index.html 配置
echo ""
echo "检查 index.html 配置..."
if grep -q "loadSidebar: true" index.html; then
    echo "✓ 侧边栏已启用"
else
    echo "✗ 侧边栏未启用"
fi

if grep -q "homepage: 'README.md'" index.html; then
    echo "✓ 首页配置正确"
else
    echo "✗ 首页配置错误"
fi

if grep -q "search:" index.html; then
    echo "✓ 搜索功能已配置"
else
    echo "✗ 搜索功能未配置"
fi

# 检查 _sidebar.md
echo ""
echo "检查 _sidebar.md..."
if [ -f "_sidebar.md" ]; then
    sidebar_links=$(grep -c "\]" "_sidebar.md")
    echo "✓ 侧边栏包含 $sidebar_links 个链接"
else
    echo "✗ _sidebar.md 文件不存在"
fi

# 检查文档链接
echo ""
echo "检查文档链接..."
if grep -q "docs/README.md" README.md; then
    echo "✓ README.md 链接到 docs/README.md"
else
    echo "✗ README.md 未链接到 docs/README.md"
fi

# 总结
echo ""
echo "=== 测试完成 ==="
if [ $missing_files -eq 0 ]; then
    echo "✓ 文档结构完整"
    echo ""
    echo "下一步："
    echo "1. 运行 'docsify serve .' 本地测试文档"
    echo "2. 访问 http://localhost:8000 查看文档"
    echo "3. 提交更改并推送到 GitHub"
    echo "4. GitHub Pages 将自动更新"
else
    echo "✗ 文档结构不完整，请检查缺失的文件"
fi
