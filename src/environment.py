"""环境：变量绑定表 + 指向外层环境的指针。

这一层实现了词法作用域：查名字时先在当前帧找，找不到就顺着 parent 往外找；
closure 保存的正是"定义时的那一层环境"，所以函数认得自己出生地的变量。
"""

from errors import SchemeError


class Environment:
    """一帧绑定 + 一个外层环境（最外层为 None）。"""

    __slots__ = ("frame", "parent")

    def __init__(self, parent=None):
        self.frame = {}
        self.parent = parent

    def define(self, name, value):
        """在当前帧建立/覆盖绑定（define 用）。"""
        self.frame[name] = value

    def lookup(self, name):
        """顺着环境链查找名字，查不到就报错。"""
        env = self
        while env is not None:
            if name in env.frame:
                return env.frame[name]
            env = env.parent
        raise SchemeError("未定义的变量：%s" % name)

    def child(self):
        """新建一层以自己为外层环境的环境（调用函数/进入 let 时用）。"""
        return Environment(parent=self)
