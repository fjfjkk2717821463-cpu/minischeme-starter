"""mini-Scheme 的数据类型。

这里只定义"值长什么样"，不做词法、语法、求值或打印。

值的对应关系：

    Scheme 值            Python 表示
    -------------------------------------------------
    整数                  int
    浮点                  float
    布尔 #t / #f          bool
    符号 foo              Symbol（**不是** str 子类，避免和字符串混淆）
    字符串 "abc"          str
    点对 (a . b)          Pair
    空表 ()               NIL（单例，所以 (eq? '() '()) 为真）
    过程 #<procedure>     Primitive / Closure
    无值（不打印）        None
"""


class Symbol:
    """符号：一个名字，例如 foo、x1、+。

    刻意不继承 str：否则 `(equal? 'a "a")` 会因为 Python 的字符串相等而误判为真。
    """

    __slots__ = ("name",)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "Symbol(%r)" % (self.name,)

    def __eq__(self, other):
        return isinstance(other, Symbol) and other.name == self.name

    def __hash__(self):
        return hash(("symbol", self.name))


class Pair:
    """点对：car 与 cdr 两项的组合；列表就是首尾相接的点对链。"""

    __slots__ = ("car", "cdr")

    def __init__(self, car, cdr):
        self.car = car
        self.cdr = cdr

    def __repr__(self):
        return "Pair(%r, %r)" % (self.car, self.cdr)


class _Nil:
    """空表 () 的类型；全局只有 NIL 这一个实例。"""

    __slots__ = ()

    def __repr__(self):
        return "NIL"


NIL = _Nil()


class Procedure:
    """所有过程的公共基类，只用来做 `procedure?` 判断。"""

    __slots__ = ("name",)

    def __init__(self, name):
        self.name = name


class Primitive(Procedure):
    """内置过程：一个 Python 函数 + 一个用于报错的名字。"""

    __slots__ = ("func",)

    def __init__(self, name, func):
        super().__init__(name)
        self.func = func


class Closure(Procedure):
    """用户函数：记住形参、函数体和**定义时**的环境（词法作用域）。"""

    __slots__ = ("params", "body", "env")

    def __init__(self, params, body, env, name="lambda"):
        super().__init__(name)
        self.params = params
        self.body = body
        self.env = env


# --------------------------------------------------------------------------
# 类型判断小工具（Python 的 bool 是 int 的子类，所以判断数字时必须先排除布尔）
# --------------------------------------------------------------------------

def is_boolean(value):
    return isinstance(value, bool)


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_string(value):
    return isinstance(value, str)


def is_symbol(value):
    return isinstance(value, Symbol)


def is_pair(value):
    return isinstance(value, Pair)


def is_null(value):
    return value is NIL


def is_procedure(value):
    return isinstance(value, Procedure)


def is_true(value):
    """只有 #f 是假，0、()、"" 都是真。"""
    return value is not False


def is_list(value):
    """是否为"真列表"：点对链以 () 结尾。"""
    while isinstance(value, Pair):
        value = value.cdr
    return value is NIL


def make_list(items, tail=NIL):
    """把 Python 列表打包成点对链，tail 作为链尾（默认空表）。"""
    result = tail
    for item in reversed(items):
        result = Pair(item, result)
    return result


def list_to_python(value):
    """点对链 → Python 列表；不是真列表时抛错。"""
    items = []
    while isinstance(value, Pair):
        items.append(value.car)
        value = value.cdr
    if value is not NIL:
        raise TypeError("不是真列表")
    return items
