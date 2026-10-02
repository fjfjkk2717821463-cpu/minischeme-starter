"""打印：值 → 文本。

两种口径：

* ``to_write_string`` —— 顶层结果与 `write` 风格：字符串带引号，转义字符还原成 \\n \\t 写法。
* ``to_display_string`` —— `display` 风格：字符串不带引号，原样输出内容。
"""

from values import NIL, Pair, Procedure, Symbol


def to_write_string(value):
    """按 spec §8 的表格打印一个值。"""
    return _format(value, quoted_strings=True)


def to_display_string(value):
    """`display` 用的打印口径：字符串与它的内容一致，不带引号。"""
    return _format(value, quoted_strings=False)


def _format(value, quoted_strings):
    if value is None:
        return "()"  # 理论上不会走到：None 表示"无值"，由入口负责不打印
    if isinstance(value, bool):
        return "#t" if value else "#f"
    if isinstance(value, float):
        return _format_float(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Symbol):
        return value.name
    if isinstance(value, str):
        return _escape_string(value) if quoted_strings else value
    if value is NIL:
        return "()"
    if isinstance(value, Pair):
        return _format_pair(value, quoted_strings)
    if isinstance(value, Procedure):
        return "#<procedure>"
    return str(value)


def _format_pair(pair, quoted_strings):
    """点对链：真列表打印成 (1 2 3)，否则打印成 (1 . 2)。"""
    parts = []
    current = pair
    while isinstance(current, Pair):
        parts.append(_format(current.car, quoted_strings))
        current = current.cdr
    if current is NIL:
        return "(" + " ".join(parts) + ")"
    return "(" + " ".join(parts) + " . " + _format(current, quoted_strings) + ")"


def _format_float(value):
    if value != value:  # nan
        return "+nan.0"
    if value == float("inf"):
        return "+inf.0"
    if value == float("-inf"):
        return "-inf.0"
    text = repr(value)
    # 整数形式的浮点保留小数点，便于区分 0.5 与整数商这类易错点
    return text


def _escape_string(text):
    """字符串按写形式打印时，换行/制表/引号/反斜杠还原成转义写法。"""
    out = []
    for char in text:
        if char == "\\":
            out.append("\\\\")
        elif char == '"':
            out.append('\\"')
        elif char == "\n":
            out.append("\\n")
        elif char == "\t":
            out.append("\\t")
        elif char == "\r":
            out.append("\\r")
        else:
            out.append(char)
    return '"' + "".join(out) + '"'
