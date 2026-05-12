import logging
from config.settings import settings

"""
实现逻辑，首先需要了解日志模块：
1. 主要三部分，level， streamhandler, formatter
2. 设置一个logger可以梳理成：
    - logger = logging.getLogger() 获取日志对象
    - level = xxx(debug,info) 在log中什么等级可以展示 -> logger.setLevel(level)
    - handler = logging.StreamHandler() 【输出6流】如果没设置就是sys.stderr -> logger.addHandler(xxx)
    - formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s") 格式,也是在stream流中规定 -> handler.add(formatter)
"""


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logger.setLevel(level)
    handler = logging.StreamHandler()
    handler.setLevel(level)
    formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger
