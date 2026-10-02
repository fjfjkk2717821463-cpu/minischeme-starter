"""语法分析：词序列 → 表达式（嵌套的数据结构）。

表达式树直接用 values.py 里的值与点对表示：
`(+ 1 2)` 读成 Pair(Symbol("+"), Pair(1, Pair(2, NIL)))；
`'x` 读成 Pair(Symbol("quote"), Pair(Symbol("x"), NIL))。
"""

from errors import SchemeError
from tokenizer import (BOOLEAN, EOF, FLOAT, INTEGER, LPAREN, QUOTE, RPAREN,
                       STRING, SYMBOL, tokenize, to_value)
from values import NIL, Symbol, make_list

QUOTE_SYMBOL = Symbol("quote")


def parse(source):
    """把一段程序文本读成表达式列表（每个顶层表达式一项）。"""
    return Reader(tokenize(source)).read_all()


class Reader:
    """按顺序消费词序列，每次读出一个完整的表达式。"""

    def __init__(self, tokens):
        self.tokens = tokens
        self.position = 0

    # -- 对外的两个方法 ----------------------------------------------------

    def read_all(self):
        expressions = []
        while self.peek().kind != EOF:
            expressions.append(self.read_expression())
        return expressions

    def read_expression(self):
        token = self.peek()
        if token.kind == LPAREN:
            return self.read_list()
        if token.kind == RPAREN:
            raise SchemeError("多出来的右括号 )", token.line, token.column)
        if token.kind == QUOTE:
            self.advance()
            return make_list([QUOTE_SYMBOL, self.read_expression()])
        if token.kind == STRING:
            self.advance()
            return token.text
        if token.kind in (INTEGER, FLOAT, BOOLEAN):
            self.advance()
            return to_value(token)
        if token.kind == SYMBOL:
            self.advance()
            return to_value(token)
        if token.kind == EOF:
            raise SchemeError("表达式没写完就到了文件结尾", token.line, token.column)
        raise SchemeError("无法识别的零件 %r" % token.text, token.line, token.column)

    # -- 内部实现 ----------------------------------------------------------

    def read_list(self):
        open_token = self.advance()  # 吃掉左括号
        items = []
        tail = NIL
        while True:
            token = self.peek()
            if token.kind == EOF:
                raise SchemeError("括号没有闭合", open_token.line, open_token.column)
            if token.kind == RPAREN:
                self.advance()
                return make_list(items, tail)
            # 点对写法：`(1 . 2)`
            if token.kind == SYMBOL and token.text == ".":
                if not items:
                    raise SchemeError("点号 . 前面缺少元素",
                                      token.line, token.column)
                self.advance()
                tail = self.read_expression()
                self.expect(RPAREN, "点号 . 后面只能再接一个表达式，并以 ) 收尾")
                return make_list(items, tail)
            items.append(self.read_expression())

    def expect(self, kind, message):
        token = self.peek()
        if token.kind != kind:
            raise SchemeError(message, token.line, token.column)
        self.advance()
        return True

    def peek(self):
        return self.tokens[self.position]

    def advance(self):
        token = self.tokens[self.position]
        self.position += 1
        return token
