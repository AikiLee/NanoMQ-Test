"""
target:
load_json(path: str | Path) -> dict
load_yaml(path: str | Path) -> dict
"""

import json
from pathlib import Path
from typing import Any
import yaml


def load_json(path: str | Path) -> dict[str, Any]:
    """
    从json文件中加载数据，

    Args:
        path (str | Path): _description_

    Raises:
        ValueError: _description_

    Returns:
        dict[str, Any]: _description_
    """
    file_path = Path(path)
    try:
        with file_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON file: {file_path}") from e


def load_yaml(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)

    with file_path.open("r", encoding="utf-8") as file:
        # 这里yaml.safe_load对于空文件会返回None，最好做处理，返回空json
        data = yaml.safe_load(file)
    return data or {}
