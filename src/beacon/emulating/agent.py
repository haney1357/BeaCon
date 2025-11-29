#!/usr/bin/python3
# Last Modified at Nov 24, 2025

"""@file agent.py
@brief Execute Emulating Agent
@author Haney Kang

@details
##
"""

import threading
import time
from typing import List

from emulating.types import ContainerSpec
from monitoring.agent import Monitoring

# from monitoring.types import Event_t

## base
import os
import json
from pprint import pprint

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STABLE_JSON = os.path.join(BASE_DIR, "stable_args.json")

with open(STABLE_JSON) as f:
    stable_args = json.load(f)


class KwargsGenerator:
    def __init__(self, image_name: str, mutation_level):
        if image_name not in stable_args:
            print(
                f"Unable to retrieve base args for container image {image_name}. Execution w/o base args"
            )
        self.base = stable_args.get(image_name, {})

    def __iter__(self):
        while True:
            yield self._mutate_once()

    def _mutate_once(self):
        pass


if __name__ == "__main__":
    kwargsGen = KwargsGenerator("nginx:latest", 10)
