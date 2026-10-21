#!/usr/bin/env python
# coding: utf-8

"""
翻译文件编译工具（.po -> .mo）

纯标准库实现，无需安装 gettext 工具链（msgfmt / pybabel）。

用法::

    python compile_messages.py                     # 编译全部 locale
    python compile_messages.py --locale zh_CN     # 仅编译指定 locale
    python compile_messages.py --locale zh_CN --check   # 只校验，不写文件

目录结构遵循 gettext 约定::

    locales/
    ├── zh_CN/
    │   └── LC_MESSAGES/
    │       ├── messages.po   # 可编辑的翻译源文件
    │       └── messages.mo   # 编译产物（运行时加载）
    └── en/
        └── LC_MESSAGES/
            └── messages.mo
"""

import argparse
import os
import struct
import sys
from typing import Dict, List, Optional, Tuple

# .mo 文件魔数（小端）
MO_MAGIC = 0x950412de

# 缺省头部信息：缺少 Content-Type 时 gettext 会按 ASCII 解码，
# 导致中文译文抛出 UnicodeDecodeError，因此必须写入。
DEFAULT_HEADER = (
    "Content-Type: text/plain; charset=UTF-8\n"
    "Content-Transfer-Encoding: 8bit\n"
    "Plural-Forms: nplurals=2; plural=(n != 1);\n"
)

# 单字符转义表
_ESCAPES = {
    'n': '\n',
    't': '\t',
    'r': '\r',
    'a': '\a',
    'b': '\b',
    'f': '\f',
    'v': '\v',
    '"': '"',
    '\\': '\\',
}


def unescape(text: str) -> str:
    """
    解析 .po 文件中的字符串转义

    Args:
        text: 已去掉引号的原始字符串内容

    Returns:
        转义后的字符串
    """
    result: List[str] = []
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char != '\\':
            result.append(char)
            index += 1
            continue

        index += 1
        if index >= length:
            result.append('\\')
            break

        marker = text[index]
        if marker in _ESCAPES:
            result.append(_ESCAPES[marker])
            index += 1
        elif marker in ('x', 'X'):
            index += 1
            start = index
            while index < length and index - start < 2 and text[index] in '0123456789abcdefABCDEF':
                index += 1
            result.append(chr(int(text[start:index], 16)))
        elif marker in '01234567':
            start = index
            while index < length and index - start < 3 and text[index] in '01234567':
                index += 1
            result.append(chr(int(text[start:index], 8)))
        else:
            result.append(marker)
            index += 1

    return ''.join(result)


def _extract_string(line: str) -> str:
    """
    提取一行中双引号包裹的字符串内容

    Args:
        line: .po 文件中的一行

    Returns:
        引号内的原始内容
    """
    start = line.find('"')
    end = line.rfind('"')
    if start < 0 or end <= start:
        return ''
    return line[start + 1:end]


def parse_po(content: str) -> Dict[str, str]:
    """
    解析 .po 文件内容

    Args:
        content: .po 文件文本

    Returns:
        翻译表，键为 msgid，值为 msgstr；
        复数条目的键为 ``单数\\x00复数``，值为以 ``\\x00`` 分隔的各形式
    """
    catalog: Dict[str, str] = {}
    msgid: Optional[str] = None
    msgid_plural: Optional[str] = None
    msgstr = ''
    msgstr_plural: Dict[int, str] = {}
    state: Optional[str] = None
    plural_index = 0

    def flush() -> None:
        """把当前累积的条目写入翻译表"""
        nonlocal msgid, msgid_plural, msgstr, msgstr_plural
        if msgid is None:
            return
        if msgid_plural is not None:
            forms = [
                msgstr_plural.get(index, '')
                for index in range(max(msgstr_plural) + 1)
            ] if msgstr_plural else ['']
            catalog[msgid + '\x00' + msgid_plural] = '\x00'.join(forms)
        else:
            catalog[msgid] = msgstr
        msgid = None
        msgid_plural = None
        msgstr = ''
        msgstr_plural = {}

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue

        if line.startswith('"'):
            # 上一条字符串的续行
            chunk = unescape(_extract_string(line))
            if state == 'id':
                msgid += chunk
            elif state == 'id_plural':
                msgid_plural += chunk
            elif state == 'str':
                msgstr += chunk
            elif state == 'str_plural':
                msgstr_plural[plural_index] += chunk
            continue

        if line.startswith('msgid_plural'):
            msgid_plural = unescape(_extract_string(line))
            state = 'id_plural'
            continue

        if line.startswith('msgid'):
            flush()
            msgid = unescape(_extract_string(line))
            state = 'id'
            continue

        if line.startswith('msgstr['):
            plural_index = int(line[line.index('[') + 1:line.index(']')])
            msgstr_plural[plural_index] = unescape(_extract_string(line))
            state = 'str_plural'
            continue

        if line.startswith('msgstr'):
            msgstr = unescape(_extract_string(line))
            state = 'str'
            continue

    flush()

    if '' not in catalog:
        catalog[''] = DEFAULT_HEADER

    return catalog


def build_mo(catalog: Dict[str, str]) -> bytes:
    """
    构建 .mo 二进制内容

    Args:
        catalog: 翻译表

    Returns:
        .mo 文件字节内容
    """
    keys = sorted(catalog.keys())
    offsets: List[Tuple[int, int, int, int]] = []
    original = b''
    translated = b''

    for key in keys:
        key_bytes = key.encode('utf-8')
        value_bytes = catalog[key].encode('utf-8')
        offsets.append((len(original), len(key_bytes), len(translated), len(value_bytes)))
        original += key_bytes + b'\x00'
        translated += value_bytes + b'\x00'

    key_start = 7 * 4 + 16 * len(keys)
    value_start = key_start + len(original)

    key_offsets: List[int] = []
    value_offsets: List[int] = []
    for key_offset, key_len, value_offset, value_len in offsets:
        key_offsets.extend([key_len, key_offset + key_start])
        value_offsets.extend([value_len, value_offset + value_start])

    output = struct.pack(
        "Iiiiiii",
        MO_MAGIC,
        0,
        len(keys),
        7 * 4,
        7 * 4 + len(keys) * 8,
        0,
        0,
    )
    output += struct.pack("i" * len(key_offsets), *key_offsets)
    output += struct.pack("i" * len(value_offsets), *value_offsets)
    output += original
    output += translated
    return output


def compile_locale(locale_dir: str, domain: str = 'messages', check_only: bool = False) -> str:
    """
    编译单个 locale 目录

    Args:
        locale_dir: locale 目录（含 LC_MESSAGES 子目录）
        domain: 翻译域（文件名主干）
        check_only: 仅校验 .po 是否可解析，不写文件

    Returns:
        生成的 .mo 文件路径；check_only 为 True 时返回 .po 路径
    """
    messages_dir = os.path.join(locale_dir, 'LC_MESSAGES')
    po_path = os.path.join(messages_dir, domain + '.po')
    mo_path = os.path.join(messages_dir, domain + '.mo')

    if not os.path.exists(po_path):
        raise FileNotFoundError(f'未找到翻译源文件: {po_path}')

    with open(po_path, 'r', encoding='utf-8') as fp:
        content = fp.read()

    catalog = parse_po(content)
    if len(catalog) <= 1:
        raise ValueError(f'翻译源文件没有可用条目: {po_path}')

    if check_only:
        print(f'[CHECK] {po_path} 解析成功，共 {len(catalog) - 1} 条译文')
        return po_path

    os.makedirs(messages_dir, exist_ok=True)
    with open(mo_path, 'wb') as fp:
        fp.write(build_mo(catalog))

    print(f'[OK] {po_path} -> {mo_path}（{len(catalog) - 1} 条译文）')
    return mo_path


def main(argv: Optional[List[str]] = None) -> int:
    """
    命令行入口

    Args:
        argv: 参数列表，None 时读取进程参数

    Returns:
        退出码：0 全部成功，1 存在失败
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description='翻译文件编译工具（.po -> .mo）')
    parser.add_argument(
        '--locales-dir',
        default=os.path.join(base_dir, 'locales'),
        help='翻译文件根目录（默认: ./locales）',
    )
    parser.add_argument('--locale', default=None, help='仅编译指定 locale')
    parser.add_argument('--domain', default='messages', help='翻译域（默认: messages）')
    parser.add_argument('--check', action='store_true', help='仅校验，不写文件')
    args = parser.parse_args(argv)

    if not os.path.isdir(args.locales_dir):
        print(f'[FAIL] 翻译目录不存在: {args.locales_dir}', file=sys.stderr)
        return 1

    locales = [args.locale] if args.locale else sorted(
        name for name in os.listdir(args.locales_dir)
        if os.path.isdir(os.path.join(args.locales_dir, name))
    )

    if not locales:
        print(f'[FAIL] {args.locales_dir} 下没有任何 locale 目录', file=sys.stderr)
        return 1

    failed = False
    for locale in locales:
        locale_dir = os.path.join(args.locales_dir, locale)
        try:
            compile_locale(locale_dir, domain=args.domain, check_only=args.check)
        except Exception as exc:  # noqa: BLE001 - 命令行工具需要汇总所有错误
            print(f'[FAIL] {locale}: {exc}', file=sys.stderr)
            failed = True

    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
