"""词法分析：程序文本 → 词（token）序列。

只管把字符切成一串有类型的词，不认识任何语法结构。
"""

from errors import SchemeError
from values import Symbol

# 词的种类
LPAREN = "lparen"
RPAREN = "rparen"
QUOTE = "quote"
INTEGER = "integer"
FLOAT = "float"
BOOLEAN = "boolean"
STRING = "string"
SYMBOL = "symbol"
EOF = "eof"

# 分隔符：出现这些字符就说明当前这个"零件"结束了
_DELIMITERS = set("()'\"; \t\r\n\f\v")

# 字符串里的转义写法
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}


class Token:
    """一个词：种类、原始文本、以及出错时用于定位的行列号。"""

    __slots__ = ("kind", "text", "line", "column")

    def __init__(self, kind, text, line, column):
        self.kind = kind
        self.text = text
        self.line = line
        self.column = column

    def __repr__(self):
        return "Token(%s, %r)" % (self.kind, self.text)


def tokenize(source):
    """把整段程序文本切成词的列表（末尾一定有一个 EOF 词）。"""
    tokens = []
    i = 0
    line = 1
    column = 1
    length = len(source)

    while i < length:
        char = source[i]

        # 空白：换行要单独记账，用于定位
        if char in " \t\r\f\v":
            i += 1
            column += 1
            continue
        if char == "\n":
            i += 1
            line += 1
            column = 1
            continue

        # 注释：; 到行尾全部忽略
        if char == ";":
            while i < length and source[i] != "\n":
                i += 1
            continue

        start_line, start_column = line, column

        if char == "(":
            tokens.append(Token(LPAREN, char, start_line, start_column))
            i += 1
            column += 1
            continue
        if char == ")":
            tokens.append(Token(RPAREN, char, start_line, start_column))
            i += 1
            column += 1
            continue
        if char == "'":
            tokens.append(Token(QUOTE, char, start_line, start_column))
            i += 1
            column += 1
            continue

        # 字符串字面量："..."，支持 \n \t \" \\
        if char == '"':
            i += 1
            column += 1
            chars = []
            while True:
                if i >= length:
                    raise SchemeError("字符串缺少收尾的双引号", start_line, start_column)
                current = source[i]
                if current == '"':
                    i += 1
                    column += 1
                    break
                if current == "\\":
                    if i + 1 >= length:
                        raise SchemeError("转义符后面没有字符", line, column)
                    escaped = source[i + 1]
                    if escaped not in _ESCAPES:
                        raise SchemeError("不支持的转义 \\%s" % escaped, line, column)
                    chars.append(_ESCAPES[escaped])
                    i += 2
                    column += 2
                    continue
                if current == "\n":
                    chars.append(current)
                    i += 1
                    line += 1
                    column = 1
                    continue
                chars.append(current)
                i += 1
                column += 1
            tokens.append(Token(STRING, "".join(chars), start_line, start_column))
            continue

        # 其它零件：一直读到分隔符为止
        start = i
        while i < length and source[i] not in _DELIMITERS:
            i += 1
            column += 1
        text = source[start:i]
        tokens.append(Token(_classify(text, start_line, start_column), text,
                            start_line, start_column))

    tokens.append(Token(EOF, "", line, column))
    return tokens


def _classify(text, line, column):
    """给一个原子（符号/数字/布尔）贴上种类标签。"""
    if text == "#t" or text == "#f":
        return BOOLEAN
    if _is_integer(text):
        return INTEGER
    if _is_float(text):
        return FLOAT
    return SYMBOL


def _is_integer(text):
    body = text[1:] if text[:1] in "+-" else text
    return body.isdigit()


def _is_float(text):
    body = text[1:] if text[:1] in "+-" else text
    if body.count(".") != 1:
        return False
    head, _, tail = body.partition(".")
    if not head.isdigit() and head != "":
        return False
    return tail.isdigit()


def to_value(token):
    """把词翻译成它代表的值（布尔/数字/符号），供语法分析使用。"""
    if token.kind == BOOLEAN:
        return token.text == "#t"
    if token.kind == INTEGER:
        return int(token.text)
    if token.kind == FLOAT:
        return float(token.text)
    if token.kind == SYMBOL:
        return Symbol(token.text)
    raise SchemeError("这里不该出现 %r 这样的零件" % token.text,
                      token.line, token.column)
