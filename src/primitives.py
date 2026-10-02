"""内置过程库：spec §5 的全部标准函数，装进初始环境。

只负责"给定已求值的实参，算出结果"；参数什么时候求值由 evaluator 决定。
唯一的副作用出口是 display / newline，它们通过构造时传入的 write 输出。
"""

from environment import Environment
from errors import SchemeError
from printer import to_display_string, to_write_string
from values import (NIL, Pair, Primitive, is_boolean, is_list, is_number,
                    is_procedure, is_string, is_symbol, list_to_python,
                    make_list)


def make_standard_environment(write):
    """建立装着全部内置过程的全局环境。write 是输出文本的回调。"""
    env = Environment()
    for name, func in _build_table(write).items():
        env.define(name, Primitive(name, func))
    return env


def _build_table(write):
    """过程名 → 实现函数（参数已经求值好，以 Python 列表传入）。"""
    table = {
        "+": _add,
        "-": _subtract,
        "*": _multiply,
        "/": _divide,
        "modulo": _modulo,
        "quotient": _quotient,
        "expt": _expt,
        "abs": _abs,
        "=": lambda args: _chain("=", args, _numeric_eq),
        "<": lambda args: _chain("<", args, lambda a, b: _compare(a, b) < 0),
        ">": lambda args: _chain(">", args, lambda a, b: _compare(a, b) > 0),
        "<=": lambda args: _chain("<=", args, lambda a, b: _compare(a, b) <= 0),
        ">=": lambda args: _chain(">=", args, lambda a, b: _compare(a, b) >= 0),
        "not": _not,
        "cons": _cons,
        "car": _car,
        "cdr": _cdr,
        "list": _list,
        "length": _length,
        "append": _append,
        "null?": lambda args: _unary("null?", args) is NIL,
        "pair?": lambda args: isinstance(_unary("pair?", args), Pair),
        "list?": lambda args: is_list(_unary("list?", args)),
        "number?": lambda args: is_number(_unary("number?", args)),
        "boolean?": lambda args: is_boolean(_unary("boolean?", args)),
        "symbol?": lambda args: is_symbol(_unary("symbol?", args)),
        "string?": lambda args: is_string(_unary("string?", args)),
        "procedure?": lambda args: is_procedure(_unary("procedure?", args)),
        "zero?": lambda args: _check_number("zero?", _unary("zero?", args)) == 0,
        "even?": lambda args: _integer_predicate("even?", args, lambda n: n % 2 == 0),
        "odd?": lambda args: _integer_predicate("odd?", args, lambda n: n % 2 != 0),
        "eq?": lambda args: _eq(*_binary("eq?", args)),
        "equal?": lambda args: _equal(*_binary("equal?", args)),
        "display": lambda args: _display(write, _unary("display", args)),
        "newline": lambda args: _newline(args, write),
    }
    return table


# --------------------------------------------------------------------------
# 参数个数与类型的小工具
# --------------------------------------------------------------------------

def _at_least(name, args, count):
    if len(args) < count:
        raise SchemeError("%s 至少需要 %d 个参数，收到 %d 个" % (name, count, len(args)))
    return args


def _unary(name, args):
    if len(args) != 1:
        raise SchemeError("%s 只接受 1 个参数，收到 %d 个" % (name, len(args)))
    return args[0]


def _binary(name, args):
    if len(args) != 2:
        raise SchemeError("%s 只接受 2 个参数，收到 %d 个" % (name, len(args)))
    return args[0], args[1]


def _check_number(name, value):
    if not is_number(value):
        raise SchemeError("%s 的参数必须是数字，收到 %s" % (name, to_write_string(value)))
    return value


def _check_integer(name, value):
    _check_number(name, value)
    if isinstance(value, float) and not value.is_integer():
        raise SchemeError("%s 的参数必须是整数，收到 %s" % (name, to_write_string(value)))
    return int(value)


# --------------------------------------------------------------------------
# 算术
# --------------------------------------------------------------------------

def _add(args):
    total = 0
    for value in args:
        total += _check_number("+", value)
    return total


def _subtract(args):
    _at_least("-", args, 1)
    first = _check_number("-", args[0])
    if len(args) == 1:
        return -first
    total = first
    for value in args[1:]:
        total -= _check_number("-", value)
    return total


def _multiply(args):
    product = 1
    for value in args:
        product *= _check_number("*", value)
    return product


def _divide(args):
    _at_least("/", args, 1)
    values = [_check_number("/", value) for value in args]
    if len(values) == 1:
        if values[0] == 0:
            raise SchemeError("/ 不能除以 0")
        return 1 / values[0]  # 单参数求倒数，结果按浮点给
    if all(isinstance(value, int) for value in values):
        result = values[0]
        for divisor in values[1:]:
            if divisor == 0:
                raise SchemeError("/ 不能除以 0")
            result = _truncating_division(result, divisor)
        return result
    result = float(values[0])
    for divisor in values[1:]:
        if divisor == 0:
            raise SchemeError("/ 不能除以 0")
        result = result / float(divisor)
    return result


def _truncating_division(dividend, divisor):
    """整数相除，商向零截断：7/2 = 3，-7/2 = -3。"""
    quotient = abs(dividend) // abs(divisor)
    return quotient if (dividend < 0) == (divisor < 0) else -quotient


def _modulo(args):
    a, b = _binary("modulo", args)
    a = _check_integer("modulo", a)
    b = _check_integer("modulo", b)
    if b == 0:
        raise SchemeError("modulo 的第二个参数不能是 0")
    return a % b


def _quotient(args):
    a, b = _binary("quotient", args)
    a = _check_integer("quotient", a)
    b = _check_integer("quotient", b)
    if b == 0:
        raise SchemeError("quotient 的第二个参数不能是 0")
    return _truncating_division(a, b)


def _expt(args):
    base, exponent = _binary("expt", args)
    base = _check_number("expt", base)
    exponent = _check_number("expt", exponent)
    if isinstance(base, int) and isinstance(exponent, int) and exponent >= 0:
        return base ** exponent
    return float(base) ** float(exponent)


def _abs(args):
    return abs(_check_number("abs", _unary("abs", args)))


# --------------------------------------------------------------------------
# 比较
# --------------------------------------------------------------------------

def _chain(name, args, compare):
    """链式比较：相邻两两都成立才返回 #t。"""
    for value in args:
        if not (is_number(value) or is_symbol(value) or is_string(value)):
            raise SchemeError("%s 只支持数字、符号与字符串，收到 %s"
                              % (name, to_write_string(value)))
    for left, right in zip(args, args[1:]):
        if not compare(left, right):
            return False
    return True


def _numeric_eq(a, b):
    _check_comparable(a, b, "=")
    return a == b


def _compare(a, b):
    """返回 a 与 b 的大小关系（<0 小、0 相等、>0 大）。"""
    _check_comparable(a, b, "比较")
    if is_symbol(a):
        a, b = a.name, b.name
    return (a > b) - (a < b)


def _check_comparable(a, b, name):
    if is_number(a) and is_number(b):
        return
    if is_symbol(a) and is_symbol(b):
        return
    if is_string(a) and is_string(b):
        return
    raise SchemeError("%s 的两个参数类型必须一致（同为数字/符号/字符串），收到 %s 与 %s"
                      % (name, to_write_string(a), to_write_string(b)))


# --------------------------------------------------------------------------
# 布尔
# --------------------------------------------------------------------------

def _not(args):
    return _unary("not", args) is False


# --------------------------------------------------------------------------
# 列表
# --------------------------------------------------------------------------

def _cons(args):
    first, second = _binary("cons", args)
    return Pair(first, second)


def _car(args):
    value = _unary("car", args)
    if not isinstance(value, Pair):
        raise SchemeError("car 只能作用于非空点对，收到 %s" % to_write_string(value))
    return value.car


def _cdr(args):
    value = _unary("cdr", args)
    if not isinstance(value, Pair):
        raise SchemeError("cdr 只能作用于非空点对，收到 %s" % to_write_string(value))
    return value.cdr


def _list(args):
    return make_list(args)


def _length(args):
    value = _unary("length", args)
    count = 0
    while isinstance(value, Pair):
        count += 1
        value = value.cdr
    if value is not NIL:
        raise SchemeError("length 只接受真列表")
    return count


def _append(args):
    """拼接若干列表：前面各项必须都是真列表，最后一项可以作为链尾。"""
    if not args:
        return NIL
    tail = args[-1]
    items = []
    for value in args[:-1]:
        if not is_list(value):
            raise SchemeError("append 的最后一个参数之外的参数都必须是列表")
        items.extend(list_to_python(value))
    return make_list(items, tail)


# --------------------------------------------------------------------------
# 谓词
# --------------------------------------------------------------------------

def _integer_predicate(name, args, predicate):
    return predicate(_check_integer(name, _unary(name, args)))


def _eq(a, b):
    """符号、数字、布尔按值比较；复合数据按同一性。"""
    if a is b:
        return True
    if is_boolean(a) or is_boolean(b):
        return False
    if is_number(a) and is_number(b):
        return a == b
    if is_symbol(a) and is_symbol(b):
        return a.name == b.name
    if is_string(a) and is_string(b):
        return a == b
    return False


def _equal(a, b):
    """结构相等：逐层比较，先比类型再比值。"""
    if is_boolean(a) or is_boolean(b):
        return is_boolean(a) and is_boolean(b) and a == b
    if is_number(a) and is_number(b):
        return a == b
    if is_symbol(a) or is_symbol(b):
        return is_symbol(a) and is_symbol(b) and a.name == b.name
    if is_string(a) or is_string(b):
        return is_string(a) and is_string(b) and a == b
    if a is NIL or b is NIL:
        return a is b
    if isinstance(a, Pair) and isinstance(b, Pair):
        return _equal(a.car, b.car) and _equal(a.cdr, b.cdr)
    return a is b


def _display(write, value):
    write(to_display_string(value))
    return None


def _newline(args, write):
    if args:
        raise SchemeError("newline 不接受参数，收到 %d 个" % len(args))
    write("\n")
    return None
