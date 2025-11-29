#!/usr/bin/python3
# Last Modified at Nov 24, 2025

"""@file types.py
@brief Define type for container args and command
@author Haney Kang

@details
##
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ContainerSpec:
    image: str
    command: Optional[List[str]] = None
    env: Dict[str, str] = field(default_factory=dict)
    volumes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    ports: Dict[str, int] = field(default_factory=dict)  # "27017/tcp": 27017
    workdir: Optional[str] = None
    category: str = "generic"  # "db", "http", "os" 등
    metadata: Dict[str, Any] = field(default_factory=dict)
