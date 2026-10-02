"""求值器：表达式 → 值（解释器的心脏）。

两个互相递归的函数：

* ``evaluate(expr, env)``：符号去环境查值；数字/布尔/字符串原样返回；
  括号表达式先看是不是特殊形式（§4），否则是函数调用——先求值操作符和
  全部实参，再交给 apply。
* ``apply_procedure(proc, args)``：内置过程直接调用；用户函数新建一层环境
  把实参绑到形参上（外层指向函数**定义时**的环境），再回到 evaluate 求值函数体。
"""

from errors import SchemeError
from printer import to_write_string
from values import (NIL, Closure, Pair, Primitive, is_pair, is_symbol, is_true,
                    list_to_python)


def evaluate(expr, env):
    """求值一个表达式。"""
    if is_symbol(expr):
        return env.lookup(expr.name)
    if isinstance(expr, Pair):
        return _evaluate_combination(expr, env)
    if expr is NIL:
        raise SchemeError("空表 () 不是一个可以求值的表达式")
    # 数字、布尔、字符串是自求值的基本值
    return expr


def apply_procedure(proc, args):
    """调用一个过程。"""
    if isinstance(proc, Primitive):
        return proc.func(args)
    if isinstance(proc, Closure):
        return _apply_closure(proc, args)
    raise SchemeError("%s 不是一个可以调用的过程" % to_write_string(proc))


# --------------------------------------------------------------------------
# 函数调用
# --------------------------------------------------------------------------

def _evaluate_combination(expr, env):
    operator = expr.car
    operands = _to_python_list(expr.cdr, "函数调用要写成 (操作符 参数...)")

    if is_symbol(operator):
        name = operator.name
        if name in _SPECIAL_FORMS:
            return _SPECIAL_FORMS[name](operands, env)
        # define 的第二种写法 `(define (f x) ...)` 由 _define 处理
        proc = env.lookup(name)
    else:
        proc = evaluate(operator, env)

    args = [evaluate(operand, env) for operand in operands]
    return apply_procedure(proc, args)


def _apply_closure(closure, args):
    if len(args) != len(closure.params):
        raise SchemeError("%s 需要 %d 个参数，收到 %d 个"
                          % (closure.name, len(closure.params), len(args)))
    call_env = closure.env.child()  # 外层是定义时的环境 → 词法作用域
    for name, value in zip(closure.params, args):
        call_env.define(name, value)
    return _evaluate_body(closure.body, call_env)


# --------------------------------------------------------------------------
# 特殊形式
# --------------------------------------------------------------------------

def _sf_quote(operands, env):
    _check_arity("quote", operands, 1)
    return operands[0]


def _sf_if(operands, env):
    if not 2 <= len(operands) <= 3:
        raise SchemeError("if 需要 2 或 3 个部分（测试 真分支 假分支?），收到 %d 个"
                          % len(operands))
    if is_true(evaluate(operands[0], env)):
        return evaluate(operands[1], env)
    if len(operands) == 3:
        return evaluate(operands[2], env)
    return None


def _sf_cond(operands, env):
    for clause in operands:
        if not is_pair(clause):
            raise SchemeError("cond 的子句必须是 (测试 表达式...) 的形式")
        tests = _to_python_list(clause, "cond 的子句必须是 (测试 表达式...) 的形式")
        if not tests:
            raise SchemeError("cond 的子句不能是空的")
        test = tests[0]
        if is_symbol(test) and test.name == "else":
            value = True
        else:
            value = evaluate(test, env)
        if is_true(value):
            if len(tests) == 1:
                return value  # 子句里没有表达式时，返回测试值本身
            return _evaluate_body(tests[1:], env)
    return None


def _sf_and(operands, env):
    result = True
    for operand in operands:
        result = evaluate(operand, env)
        if result is False:  # 短路：后面的表达式不再执行
            return False
    return result


def _sf_or(operands, env):
    for operand in operands:
        result = evaluate(operand, env)
        if result is not False:
            return result
    return False


def _sf_define(operands, env):
    if len(operands) < 2:
        raise SchemeError("define 需要至少 2 个部分：名字 与 表达式")
    target = operands[0]

    # 简写 `(define (f 参数...) 体...)`，等价于下面的 lambda 写法
    if is_pair(target):
        name = target.car
        if not is_symbol(name):
            raise SchemeError("define 的函数名必须是符号")
        params = _check_parameters(_parameter_names(target.cdr, "define"))
        closure = Closure(params, operands[1:], env, name.name)
        env.define(name.name, closure)
        return name

    if not is_symbol(target):
        raise SchemeError("define 的第一个部分必须是符号或 (函数名 参数...)")
    if len(operands) != 2:
        raise SchemeError("define 的普通写法只能跟一个表达式："
                          "(define 名字 表达式)")
    value = evaluate(operands[1], env)  # 先求值右侧，再绑定
    env.define(target.name, value)
    return target  # define 的结果是被定义的符号名（顶层会打印出来）


def _sf_lambda(operands, env):
    if len(operands) < 2:
        raise SchemeError("lambda 需要形参表和至少一个函数体表达式")
    params = _check_parameters(_parameter_names(operands[0], "lambda"))
    return Closure(params, operands[1:], env)


def _sf_let(operands, env):
    if len(operands) < 2:
        raise SchemeError("let 需要绑定表和至少一个函数体表达式")
    bindings = operands[0]
    names = []
    values = []
    while isinstance(bindings, Pair):
        binding = _to_python_list(bindings.car, "let 的每个绑定都要写成 (名字 表达式)")
        if len(binding) != 2 or not is_symbol(binding[0]):
            raise SchemeError("let 的每个绑定都要写成 (名字 表达式)")
        names.append(binding[0].name)
        # 并行绑定：所有绑定表达式都在外层环境求值，绑定之间互相看不见
        values.append(evaluate(binding[1], env))
        bindings = bindings.cdr
    if bindings is not NIL:
        raise SchemeError("let 的绑定表必须是一个真列表")

    body_env = env.child()
    for name, value in zip(names, values):
        body_env.define(name, value)
    return _evaluate_body(operands[1:], body_env)


def _sf_begin(operands, env):
    return _evaluate_body(operands, env)


_SPECIAL_FORMS = {
    "quote": _sf_quote,
    "if": _sf_if,
    "cond": _sf_cond,
    "and": _sf_and,
    "or": _sf_or,
    "define": _sf_define,
    "lambda": _sf_lambda,
    "let": _sf_let,
    "begin": _sf_begin,
}

# 所有特殊形式的名字：它们长得像函数调用，但求值顺序各不相同
SPECIAL_FORM_NAMES = tuple(_SPECIAL_FORMS)


# --------------------------------------------------------------------------
# 公共小工具
# --------------------------------------------------------------------------

def _evaluate_body(expressions, env):
    """按 begin 语义依次求值，返回最后一个的结果（空体返回 None）。"""
    result = None
    for expression in expressions:
        result = evaluate(expression, env)
    return result


def _check_arity(name, operands, count):
    if len(operands) != count:
        raise SchemeError("%s 需要 %d 个部分，收到 %d 个" % (name, count, len(operands)))


def _parameter_names(formals, form_name):
    """把形参表（点对链）转成形参名（字符串）列表，元素必须是符号。"""
    values = _to_python_list(formals, "%s 的形参表必须是括号列表" % form_name)
    for value in values:
        if not is_symbol(value):
            raise SchemeError("%s 的形参只能是符号" % form_name)
    return [value.name for value in values]


def _check_parameters(params):
    """形参不能重名，否则调用时必然互相覆盖。"""
    seen = set()
    for param in params:
        if param in seen:
            raise SchemeError("lambda/define 的形参重复了：%s" % param)
        seen.add(param)
    return params


def make_global_environment(write):
    """建好装着内置过程的全局环境。"""
    from primitives import make_standard_environment
    return make_standard_environment(write)


def _to_python_list(value, message):
    """点对链 → Python 列表；不是真列表时给出 SchemeError。"""
    try:
        return list_to_python(value)
    except TypeError:
        raise SchemeError(message)


__all__ = ["SPECIAL_FORM_NAMES", "apply_procedure", "evaluate",
           "make_global_environment"]
