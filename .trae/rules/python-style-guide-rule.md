---
alwaysApply: false
globs: *.py
---
# 项目代码规范指南

## 1. 导入位置

* 模块必须在文件头部导入
* 禁止在函数或类方法内部导入，除非代码逻辑必需

## 2. 导入模块规范

模块应该在文件头部进行导入，除非代码逻辑需要，否则禁止在函数内部或类的方法中导入模块，无论是使用`from import` 还是`import`。

### 2.1 四部分结构（严格顺序）

1. Django项目模块（仅以from django开头）

    * 使用 from ... import ... 形式
    * 置于导入部分最前面
    * 禁止直接 import
    * 必须位于所有导入的最前面

2. 项目内部模块（apps/ 和 libs/ 下）

    * 使用 from ... import ... 形式
    * 包括相对导入（如 .models）和绝对导入
    * 禁止直接 import

3. 标准库与第三方模块

    * from datetime import ...等标准库与from celery import ...等第三方模块合并为同一部分
    * 使用 from ... import ... 形式
    * 内部无需空行分隔
    * 禁止直接 import

4. 必须直接导入的模块

    * 仅使用 import ... 形式（如 import json、import logging）

### 1.2 格式要求

* 每部分之间空一行
* 第1部分前不得有任何导入语句
* 各部分内按完整导入语句字符串ASCII顺序排列

### 1.3 示例

```python
from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import BalanceAlertLog, BalanceAlertThreshold
from core.utils import make_object_link

from datetime import datetime
from massadmin.massadmin import MassEditMixin

import json
```

### 1.4 换行

函数内部，每行代码长度应不超过80个字符，如果超过80个字符，请使用换行符进行换行。

```
from core.private.exceptions import (
    QcDataNotFound,
    QcDataCreationFailed, 
    QcDataUpdateFailed,
    QcDataDeleteFailed,
)
```

## 2. 代码长度规范

- 每行代码长度不应超过80个字符
- 长行需进行适当的换行处理
- 多行结构应保持良好的缩进和对齐

## 3. 逗号使用规范

- 在字典、参数列表、元组等结构的最后一个元素后面也要加上逗号
- 这样做有助于版本控制时减少diff，并提高代码可读性

### 3.1 示例

```python
# 正确示例
headers = [
    '样品编号', 
    '耗时',
]

# 函数参数示例
def send_email_message(
    subject='', 
    body='', 
    **kwargs,
):
```

## 4. 注释和文档字符串

### 4.1 注释规范

- 使用有意义的变量名和函数名，优先通过命名表达意图
- 重要逻辑处应添加注释，解释"为什么"而不是"是什么"
- 注释应与代码保持同步，过时的注释应及时删除
- 使用中文注释，保持简洁明了
- 行内注释应与代码至少间隔两个空格

```python
# 正确示例
# 由于历史原因，这里需要兼容旧版本的数据格式
result = process_legacy_data(data)

# 错误示例
# 处理数据
result = process_data(data)  # 处理数据（冗余）
```

### 4.2 文档字符串规范

- 所有公共模块、函数、类和方法都应包含文档字符串
- 使用三重双引号 `"""` 定义文档字符串
- 文档字符串的第一行应该是简洁的摘要，以句号结尾
- 如果文档字符串包含多行，第二行应为空行
- 遵循 PEP 257 规范

```python
# 函数文档字符串示例
def calculate_total(items, discount=0.0):
    """
    计算商品总价。

    根据商品列表和折扣率计算最终总价。

    Args:
        items: 商品列表，每个元素包含 'price' 和 'quantity'
        discount: 折扣率，范围 0.0-1.0，默认为 0.0

    Returns:
        计算后的总价（浮点数）

    Raises:
        ValueError: 当 discount 不在有效范围内时
    """
    if not 0.0 <= discount <= 1.0:
        raise ValueError('折扣率必须在 0.0 到 1.0 之间')
    # ... 实现代码 ...

# 类文档字符串示例
class UserProfile:
    """
    用户配置文件类。

    管理用户的个人资料信息，包括基本信息、偏好设置等。
    """

    def __init__(self, user_id):
        """
        初始化用户配置文件。

        Args:
            user_id: 用户唯一标识符
        """
        self.user_id = user_id
```

## 5. 命名规范

### 5.1 基本命名规则

- **类名**：使用 `PascalCase`（大驼峰命名法）
- **函数和变量名**：使用 `snake_case`（蛇形命名法）
- **常量**：使用 `UPPER_SNAKE_CASE`（全大写下划线分隔）
- **私有成员**：使用单下划线前缀 `_private_method`
- **特殊方法**：使用双下划线包围 `__special_method__`
- **避免使用**：单字母变量名（除了循环计数器 `i`, `j`, `k`）、容易混淆的字符（`l`, `O`, `I`）

### 5.2 命名示例

```python
# 类名
class UserProfile:
    pass

class DataProcessor:
    pass

# 函数和变量名
def calculate_total_price():
    pass

user_count = 100
is_valid = True

# 常量
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30
API_BASE_URL = 'https://api.example.com'

# 私有成员
class MyClass:
    def _internal_helper(self):
        """私有辅助方法"""
        pass

    def __str__(self):
        """特殊方法"""
        return 'MyClass'
```

### 5.3 命名约定

- 布尔值变量使用 `is_`、`has_`、`can_` 等前缀
- 返回布尔值的函数使用 `is_`、`has_`、`check_` 等前缀
- 事件处理方法使用 `on_` 前缀
- 获取器方法通常不需要 `get_` 前缀（属性访问器除外）

## 6. Django 模型规范

### 6.1 模型字段定义

- 模型字段定义应包含 `verbose_name` 和 `help_text`
- 使用 `gettext_lazy` 进行国际化
- 为外键字段设置 `related_name`
- 使用适当的字段类型和约束

```python
from django.db import models
from django.utils.translation import gettext_lazy as _

class User(models.Model):
    """用户模型"""
    
    name = models.CharField(
        max_length=100,
        verbose_name=_('姓名'),
        help_text=_('用户的真实姓名'),
    )
    email = models.EmailField(
        unique=True,
        verbose_name=_('邮箱'),
        help_text=_('用户邮箱地址，用于登录和接收通知'),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('创建时间'),
    )
    profile = models.OneToOneField(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name='user',
        verbose_name=_('用户资料'),
    )

    class Meta:
        verbose_name = _('用户')
        verbose_name_plural = _('用户')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
        ]
```

### 6.2 Meta 类规范

- Meta 类定义模型元数据，如 `verbose_name`、`verbose_name_plural` 和 `ordering`
- 使用 `db_table` 明确指定数据库表名（可选）
- 合理使用 `indexes` 和 `constraints` 优化查询性能

### 6.3 模型方法

- 实现 `__str__` 方法提供友好的字符串表示
- 使用 `@property` 定义计算属性
- 将业务逻辑封装在模型方法中

```python
class Order(models.Model):
    """订单模型"""
    
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self) -> str:
        return f'订单 #{self.id}'
    
    @property
    def final_amount(self) -> Decimal:
        """计算最终金额"""
        return self.total_amount - self.discount
    
    def apply_discount(self, discount_rate: float) -> None:
        """应用折扣"""
        if not 0.0 <= discount_rate <= 1.0:
            raise ValueError('折扣率必须在 0.0 到 1.0 之间')
        self.discount = self.total_amount * discount_rate
        self.save()
```

### 6.4 Django 视图规范

- 使用基于类的视图（CBV）处理复杂逻辑
- 使用函数视图处理简单场景
- 合理使用 Mixin 复用代码
- 使用 Django 的表单验证

```python
from django.views.generic import ListView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin

class UserListView(LoginRequiredMixin, ListView):
    """用户列表视图"""
    model = User
    template_name = 'users/list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset
```

### 6.5 Django 表单规范

- 使用 ModelForm 简化表单创建
- 在表单中定义验证逻辑
- 使用 `clean_<field>` 方法进行字段级验证
- 使用 `clean` 方法进行跨字段验证

```python
from django import forms
from django.core.exceptions import ValidationError

class UserForm(forms.ModelForm):
    """用户表单"""
    
    class Meta:
        model = User
        fields = ['name', 'email']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
    
    def clean_email(self):
        """验证邮箱"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('该邮箱已被使用')
        return email
```

### 6.6 Django 查询优化

- 使用 `select_related` 优化外键查询
- 使用 `prefetch_related` 优化多对多和反向外键查询
- 使用 `only` 和 `defer` 控制字段加载
- 避免 N+1 查询问题

```python
# 优化外键查询
users = User.objects.select_related('profile').all()

# 优化多对多查询
articles = Article.objects.prefetch_related('tags', 'author').all()

# 只加载需要的字段
users = User.objects.only('name', 'email')

# 避免 N+1 查询
orders = Order.objects.select_related('user').prefetch_related('items')
```

## 7. 类型提示（Type Hints）

### 7.1 基本使用

- 优先使用类型提示提高代码可读性和可维护性
- 使用 `typing` 模块提供的类型注解
- 对于简单类型，可以直接使用内置类型（Python 3.9+）

```python
from typing import List, Dict, Optional, Union, Tuple

# 函数类型提示
def process_items(items: List[str], count: int) -> Dict[str, int]:
    """
    处理项目列表。

    Args:
        items: 字符串列表
        count: 处理数量

    Returns:
        处理结果字典
    """
    return {'processed': len(items[:count])}

# 可选类型
def find_user(user_id: Optional[int] = None) -> Optional[Dict]:
    if user_id is None:
        return None
    return {'id': user_id}

# 联合类型
def parse_value(value: Union[str, int]) -> str:
    return str(value)

# 类属性类型提示
class User:
    name: str
    age: int
    email: Optional[str] = None
```

### 7.2 Django 相关类型提示

```python
from django.db import models
from django.http import HttpRequest, HttpResponse
from typing import Any

class MyModel(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self) -> str:
        return self.name

def my_view(request: HttpRequest) -> HttpResponse:
    # 视图函数类型提示
    return HttpResponse('OK')
```

## 8. 字符串格式化规范

### 8.1 推荐方式

- **优先使用 f-string**（Python 3.6+）
- 对于复杂格式化，使用 `.format()` 方法
- 避免使用 `%` 格式化（旧式格式化）

```python
# 推荐：f-string
name = 'John'
age = 30
message = f'用户 {name} 的年龄是 {age} 岁'

# 复杂格式化
user_info = f'用户信息：姓名={user.name}, 年龄={user.age}, 邮箱={user.email or "未设置"}'

# 多行 f-string
message = (
    f'用户 {name} 的信息：\n'
    f'  年龄：{age}\n'
    f'  状态：{"活跃" if is_active else "非活跃"}'
)

# 使用 .format() 处理复杂情况
template = '用户 {name} 在 {date:%Y-%m-%d} 执行了操作'
message = template.format(name=user.name, date=datetime.now())
```

### 8.2 字符串连接

- 避免使用 `+` 连接大量字符串，使用 `join()` 或 f-string
- 对于少量字符串，f-string 更清晰

```python
# 推荐
parts = ['a', 'b', 'c']
result = ''.join(parts)
# 或
result = f'{parts[0]}{parts[1]}{parts[2]}'

# 不推荐
result = parts[0] + parts[1] + parts[2]
```

## 9. 比较操作和布尔值规范

### 9.1 比较操作

- 使用 `is` 和 `is not` 比较 `None`，而不是 `==` 和 `!=`
- 使用 `==` 和 `!=` 比较值
- 对于布尔值，直接使用，不要与 `True`/`False` 比较

```python
# 正确示例
if value is None:
    pass

if value is not None:
    pass

if items:  # 检查列表是否非空
    pass

if not items:  # 检查列表是否为空
    pass

# 错误示例
if value == None:  # 不推荐
    pass

if items == []:  # 不推荐
    pass

if flag == True:  # 不推荐
    pass
```

### 9.2 布尔值检查

- 利用 Python 的真值测试，避免显式比较
- 空列表、空字典、空字符串、0、None 都是 False

```python
# 正确示例
if user_list:  # 列表非空
    process_users(user_list)

if not error_message:  # 字符串为空
    return success_response

if count:  # 数量大于 0
    process_items()

# 错误示例
if len(user_list) > 0:  # 不推荐
    process_users(user_list)

if error_message == '':  # 不推荐
    return success_response
```

## 10. 异常处理规范

### 10.1 基本规范

- 捕获具体的异常类型，避免使用裸露的 `except:`
- 使用 `except Exception:` 而不是 `except:`
- 记录异常信息，包含足够的上下文
- 重新抛出异常时使用 `raise`，不要使用 `raise e`

```python
# 正确示例
try:
    result = process_data(data)
except ValueError as e:
    logger.error(f'数据格式错误: {e}', extra={'data': data})
    raise
except KeyError as e:
    logger.error(f'缺少必需的键: {e}')
    return default_value
except Exception as e:
    logger.exception(f'处理数据时发生未知错误: {e}')
    raise

# 错误示例
try:
    result = process_data(data)
except:  # 不推荐：捕获所有异常包括系统退出
    pass

try:
    result = process_data(data)
except Exception as e:
    raise e  # 不推荐：会丢失原始异常堆栈
```

### 10.2 异常链

- 使用 `raise ... from ...` 保留异常链

```python
try:
    process_file(filename)
except FileNotFoundError as e:
    raise ProcessingError(f'无法处理文件: {filename}') from e
```

### 10.3 自定义异常

- 为模块定义自定义异常类，继承自 `Exception`

```python
class ValidationError(Exception):
    """数据验证错误"""
    pass

class ProcessingError(Exception):
    """数据处理错误"""
    pass
```

## 11. 函数和参数规范

### 11.1 函数设计原则

- 函数应该简短，专注于单一职责
- 函数参数不宜过多（建议不超过 5 个），过多时考虑使用字典或数据类
- 使用有意义的参数名
- 避免使用可变对象作为默认参数

```python
# 正确示例
def create_user(name: str, email: str, age: int = 18) -> User:
    """创建用户"""
    return User(name=name, email=email, age=age)

# 错误示例：可变对象作为默认参数
def add_item(item, items=[]):  # 不推荐
    items.append(item)
    return items

# 正确做法
def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```

### 11.2 参数顺序

- 位置参数
- `*args`
- 关键字参数（有默认值的参数）
- `**kwargs`

```python
def example_function(
    required_arg: str,
    *args: Any,
    optional_arg: str = 'default',
    **kwargs: Any,
) -> None:
    pass
```

## 12. 列表推导式和生成器表达式

### 12.1 使用场景

- 优先使用列表推导式代替简单的 `for` 循环
- 对于大数据集，使用生成器表达式节省内存
- 保持推导式简洁，复杂逻辑应使用普通循环

```python
# 列表推导式
squares = [x**2 for x in range(10)]
filtered_items = [item for item in items if item.is_valid()]

# 字典推导式
user_dict = {user.id: user.name for user in users}

# 集合推导式
unique_names = {user.name for user in users}

# 生成器表达式（节省内存）
large_sum = sum(x**2 for x in range(1000000))

# 复杂情况使用普通循环
results = []
for item in items:
    if item.is_valid():
        processed = complex_processing(item)
        if processed:
            results.append(processed)
```

## 13. 上下文管理器

### 13.1 文件操作

- 始终使用 `with` 语句处理文件操作
- 使用上下文管理器管理资源（数据库连接、锁等）

```python
# 文件操作
with open('file.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# 数据库操作
with transaction.atomic():
    user.save()
    profile.save()

# 自定义上下文管理器
from contextlib import contextmanager

@contextmanager
def temporary_config(config_dict):
    old_config = get_config()
    set_config(config_dict)
    try:
        yield
    finally:
        set_config(old_config)
```

## 14. 常量定义规范

### 14.1 常量组织

- 常量应定义在模块级别
- 使用全大写下划线分隔的命名
- 相关常量可以组织在类中

```python
# 模块级常量
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30
API_BASE_URL = 'https://api.example.com'

# 使用类组织相关常量
class Status:
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
```

## 15. 日志使用规范

### 15.1 日志级别

- 使用适当的日志级别：`DEBUG`、`INFO`、`WARNING`、`ERROR`、`CRITICAL`
- 记录关键操作和错误信息
- 使用结构化日志，包含上下文信息

```python
import logging

logger = logging.getLogger(__name__)

# 正确示例
logger.info('用户登录成功', extra={'user_id': user.id, 'ip': request.META.get('REMOTE_ADDR')})
logger.warning('API 响应时间较长', extra={'duration': duration, 'endpoint': endpoint})
logger.error('处理订单失败', extra={'order_id': order.id}, exc_info=True)

# 使用 f-string 格式化（Python 3.6+）
logger.info(f'处理了 {count} 条记录')
```

### 15.2 日志最佳实践

- 不要在日志中记录敏感信息（密码、令牌等）
- 使用适当的日志级别，避免过度记录
- 在生产环境中合理配置日志级别

## 16. 测试规范

### 16.1 测试文件组织

- 测试文件应以 `test_` 开头或 `_test.py` 结尾
- 测试类应以 `Test` 开头
- 测试方法应以 `test_` 开头
- 使用描述性的测试名称

```python
from django.test import TestCase

import unittest


class TestUserModel(TestCase):
    """用户模型测试"""

    def setUp(self):
        """测试前置设置"""
        self.user = User.objects.create(name='Test User')

    def test_user_creation(self):
        """测试用户创建"""
        self.assertIsNotNone(self.user.id)
        self.assertEqual(self.user.name, 'Test User')

    def test_user_str_representation(self):
        """测试用户字符串表示"""
        self.assertEqual(str(self.user), 'Test User')
```

### 16.2 测试最佳实践

- 每个测试应该独立，不依赖其他测试
- 使用 `setUp` 和 `tearDown` 方法管理测试数据
- 测试应该快速执行
- 覆盖正常情况和边界情况

## 17. 代码组织

### 17.1 模块组织

- 相关功能的代码应该组织在一起
- 遵循单一职责原则
- 保持模块简洁明了
- 每个文件最后添加一个空行
- 避免生成多余的空行
- 避免一行中只存在空格
- 避免每行代码最后以一个或多个空格结尾

### 17.2 文件结构

标准 Python 文件结构：

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模块文档字符串。

描述模块的主要功能和用途。
"""

# 1. 导入模块

import os
import sys


# 2. 模块级常量
DEFAULT_TIMEOUT = 30

# 3. 模块级变量
logger = logging.getLogger(__name__)

# 4. 类和函数定义
class MyClass:
    pass

def my_function():
    pass

# 5. 主程序入口（如果适用）
if __name__ == '__main__':
    main()
```

## 18. 其他最佳实践

### 18.1 文件编码

- Python 文件应使用 UTF-8 编码
- 文件开头可以添加编码声明：`# -*- coding: utf-8 -*-`

### 18.2 代码检查工具

- 使用 `flake8`、`pylint`、`black` 等工具检查代码风格
- 在提交代码前运行代码检查工具
- 配置 IDE 自动格式化代码

### 18.3 性能优化建议

- 避免过早优化，优先保证代码可读性
- 使用适当的数据结构（集合用于成员检查，字典用于键值查找）
- 对于大数据集，考虑使用生成器而不是列表
- 合理使用缓存（Django 的缓存框架）

### 18.4 安全规范

- 永远不要信任用户输入，始终进行验证和清理
- 使用 Django 的 CSRF 保护
- 避免 SQL 注入，使用 ORM 查询或参数化查询
- 不要在代码中硬编码敏感信息（密码、密钥等），使用环境变量或配置文件
- 使用 Django 的密码哈希功能，不要存储明文密码
- 使用 Django 的 `escape` 或模板自动转义防止 XSS 攻击
- 合理设置权限和访问控制

### 18.5 版本控制规范

- 提交信息应清晰描述变更内容
- 使用有意义的提交信息，遵循约定式提交（Conventional Commits）格式
- 每次提交应保持逻辑完整性，避免大而全的提交
- 提交前运行测试和代码检查工具

```bash
# 提交信息格式示例
feat: 添加用户登录功能
fix: 修复订单金额计算错误
docs: 更新 API 文档
refactor: 重构用户服务类
test: 添加用户模型单元测试
```

### 18.6 代码审查规范

- 代码审查应关注代码质量、可维护性和性能
- 审查时保持建设性的反馈
- 关注代码逻辑、错误处理、测试覆盖等方面
- 及时响应审查意见，积极讨论和改进

## 19. 参考资源

- [PEP 8 -- Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/)
- [PEP 257 -- Docstring Conventions](https://www.python.org/dev/peps/pep-0257/)
- [PEP 484 -- Type Hints](https://www.python.org/dev/peps/pep-0484/)
- [Django Coding Style](https://docs.djangoproject.com/en/stable/internals/contributing/writing-code/coding-style/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)