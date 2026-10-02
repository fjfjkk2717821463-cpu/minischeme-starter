#!/usr/bin/env python3
"""解释器入口：读文件或标准输入 → 逐条求值 → 逐行打印结果。

用法：

    python3 src/main.py file1.scm [file2.scm ...]
    python3 src/main.py < program.scm

多个文件共享同一个全局环境；求值结果为"无值"（如 display、newline）时不打印。
"""

import os
import sys
import threading

# 让 `python3 src/main.py` 在任何工作目录下都能 import 同目录的兄弟模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from errors import SchemeError                    # noqa: E402
from evaluator import evaluate                    # noqa: E402
from evaluator import make_global_environment     # noqa: E402
from printer import to_write_string               # noqa: E402
from reader import parse                          # noqa: E402

# Scheme 的递归全靠 Python 的调用栈实现，一层 Scheme 调用大约要吃掉几层
# Python 帧。默认上限（1000 层）太浅，这里把深度和线程栈都放宽。
RECURSION_LIMIT = 100000
STACK_SIZE = 256 * 1024 * 1024


def run(sources, write):
    """按顺序求值每一段程序文本里的所有顶层表达式，结果逐行打印。"""
    env = make_global_environment(write)
    for source in sources:
        for expression in parse(source):
            value = evaluate(expression, env)
            if value is not None:  # 无值不打印
                write(to_write_string(value) + "\n")


def read_sources(paths):
    """读取命令行给出的文件；没有文件时读标准输入。"""
    if not paths:
        return [sys.stdin.read()]
    sources = []
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                sources.append(handle.read())
        except OSError as error:
            raise SchemeError("读不了文件 %s：%s" % (path, error.strerror))
    return sources


def main(argv):
    paths = [arg for arg in argv if arg != "--"]
    exit_code = {"value": 0}

    def worker():
        try:
            sources = read_sources(paths)
            run(sources, sys.stdout.write)
        except SchemeError as error:
            sys.stdout.flush()
            print("mini-Scheme 错误：%s" % error, file=sys.stderr)
            exit_code["value"] = 1
        except RecursionError:
            sys.stdout.flush()
            print("mini-Scheme 错误：递归太深（超过 %d 层）" % RECURSION_LIMIT,
                  file=sys.stderr)
            exit_code["value"] = 1

    # 在自带大栈的线程里求值，深递归的程序才不会撞上解释器的栈上限
    sys.setrecursionlimit(RECURSION_LIMIT)
    try:
        threading.stack_size(STACK_SIZE)
    except (ValueError, RuntimeError):
        pass  # 平台不支持自定义栈大小时退回默认值
    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    sys.stdout.flush()
    return exit_code["value"]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
