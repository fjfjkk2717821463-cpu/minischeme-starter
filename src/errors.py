"""解释器统一使用的异常类型。

把错误收敛到一个类，入口只负责把它翻译成一条人类可读的提示；
模块内部（词法／语法／求值）只管抛出，不关心怎么打印。
"""


class SchemeError(Exception):
    """mini-Scheme 运行期错误（词法、语法或求值错误）。"""

    def __init__(self, message, line=None, column=None):
        if line is not None:
            message = "第 %d 行第 %d 列：%s" % (line, column, message)
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column
