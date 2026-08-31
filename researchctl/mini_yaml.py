"""无第三方依赖的 YAML 子集解析器。

只支持本系统 fixture 使用的 YAML 结构：
- 嵌套 map（缩进）
- list of maps（"- " 前缀 + 子字段缩进）
- list of scalars
- 标量：字符串、数字、null、布尔
- 单双引号字符串

不支持：锚点/别名、多行块、流式嵌套、复杂转义。
"""
from __future__ import annotations

import re
from typing import Any, List, Tuple


def _parse_scalar(raw: str) -> Any:
    raw = raw.strip()
    if raw == "" or raw.lower() == "null" or raw == "~":
        return None
    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    # 数字（整数 / 浮点 / 带符号）
    if re.fullmatch(r"[-+]?\d+", raw):
        return int(raw)
    if re.fullmatch(r"[-+]?\d+\.\d+", raw):
        return float(raw)
    return raw


def _strip_comment(line: str) -> str:
    # 去掉行尾注释（不在引号内的 #）
    in_s = in_d = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_d:
            in_s = not in_s
        elif ch == '"' and not in_s:
            in_d = not in_d
        elif ch == "#" and not in_s and not in_d:
            return line[:i].rstrip()
    return line.rstrip()


def _lines(text: str) -> List[Tuple[int, str]]:
    out = []
    for line in text.split("\n"):
        s = _strip_comment(line)
        if not s.strip():
            continue
        indent = len(s) - len(s.lstrip(" "))
        out.append((indent, s.strip()))
    return out


class _Parser:
    def __init__(self, lines: List[Tuple[int, str]]):
        self.lines = lines
        self.i = 0

    def _peek(self) -> Tuple[int, str]:
        if self.i < len(self.lines):
            return self.lines[self.i]
        return (-1, "")

    def _consume(self) -> Tuple[int, str]:
        t = self.lines[self.i]
        self.i += 1
        return t

    def parse(self) -> Any:
        if not self.lines:
            return {}
        return self._block(self.lines[0][0])

    def _block(self, indent: int) -> Any:
        """解析缩进为 indent 的一个块（map 或 list）。"""
        # 判断类型：下一个非空行以 "- " 开头则为 list
        if self._peek()[0] == indent and self._peek()[1].startswith("- "):
            return self._list(indent)
        return self._map(indent)

    def _map(self, indent: int) -> dict:
        result = {}
        while self.i < len(self.lines):
            cur_indent, content = self._peek()
            if cur_indent != indent:
                break
            if content.startswith("- "):
                break
            self._consume()
            key, _, value_raw = content.partition(":")
            key = key.strip()
            value_raw = value_raw.strip()
            if value_raw == "":
                # 嵌套块或空值
                if self.i < len(self.lines) and self.lines[self.i][0] > indent:
                    result[key] = self._block(self.lines[self.i][0])
                else:
                    result[key] = None
            else:
                result[key] = _parse_scalar(value_raw)
        return result

    def _list(self, indent: int) -> list:
        result = []
        while self.i < len(self.lines):
            cur_indent, content = self._peek()
            if cur_indent != indent or not content.startswith("- "):
                break
            self._consume()
            item_raw = content[2:].strip()
            if item_raw == "":
                if self.i < len(self.lines) and self.lines[self.i][0] > indent:
                    result.append(self._block(self.lines[self.i][0]))
                else:
                    result.append(None)
            elif ":" in item_raw and not item_raw.startswith(('"', "'")):
                # list item 是 map 的第一行
                key, _, value_raw = item_raw.partition(":")
                key = key.strip()
                value_raw = value_raw.strip()
                item = {}
                if value_raw == "":
                    if self.i < len(self.lines) and self.lines[self.i][0] > indent:
                        item[key] = self._block(self.lines[self.i][0])
                    else:
                        item[key] = None
                else:
                    item[key] = _parse_scalar(value_raw)
                # 剩余子字段（同缩进 > indent 且非 list item）
                if self.i < len(self.lines) and self.lines[self.i][0] > indent:
                    sub = self._block(self.lines[self.i][0])
                    if isinstance(sub, dict):
                        item.update(sub)
                result.append(item)
            else:
                result.append(_parse_scalar(item_raw))
        return result


def load(text: str) -> Any:
    """解析 YAML 文本，返回 Python 对象。"""
    return _Parser(_lines(text)).parse()


def load_file(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return load(f.read())
