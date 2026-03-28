---
alwaysApply: false
globs: *.py
---
# Python 代码规范

## 1. 导入
头部导入，三部分：1)内部from...import 2)标准库与第三方from...import 3)必须直接import。每部分空一行，ASCII排序。

## 2. 代码长度
每行≤80字符。

## 3. 逗号
字典、参数、元组末尾加逗号。

## 4. 注释与文档
命名表达意图，重要逻辑解释"为什么"。公共代码含文档字符串"""，遵循PEP 257。

## 5. 命名
类名PascalCase，函数变量snake_case，常量UPPER_SNAKE_CASE，私有_前缀，特殊__包围。布尔用is_/has_/can_前缀。

## 6. 类型提示
优先使用类型提示，用typing或内置类型。

## 7. 字符串
优先f-string，复杂用.format()，避免%。连接用join()或f-string。

## 8. 比较
None用is/is not，值用==/!=。布尔直接用。

## 9. 异常
捕获具体异常，用except Exception:。记录信息，重抛用raise，异常链用raise...from...。

## 10. 函数
简短单一职责，参数≤5个。避免可变默认参数。顺序：位置、*args、关键字、**kwargs。

## 11. 推导式
优先列表推导式，大数据用生成器。

## 12. 上下文
用with处理文件和资源。

## 13. 常量
模块级，全大写下划线。

## 14. 日志
DEBUG/INFO/WARNING/ERROR/CRITICAL。不记录敏感信息。

## 15. 测试
test_开头或_test.py结尾，Test类，test_方法。独立快速，覆盖边界。

## 16. 组织
相关功能组织，单一职责。文件末尾空行，避免多余空行和行尾空格。

## 17. 其他
UTF-8。用flake8/pylint/black。避免过早优化，用适当数据结构。敏感信息用环境变量。输入验证，HTTPS，定期更新依赖。

参考：PEP 8、PEP 257、Google Python Style Guide
