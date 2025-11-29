#!/usr/bin/python3
# Last Modified at Nov 25, 2025

import os
import json
from event_nametable import syscalls

from pprint import pprint

""" Code for compare LLM result and BeaCon's result """

with open("stable_args.json") as f:
    container_args = json.load(f)

containers = list(
    map(lambda k: k.split(":"), list(container_args.keys()))
)  # List[List[name, tag], ...]

LLM_path = "../../../prompt2seccomp/result/syscalls/"
dyn_path = "./result/"

line = (
    ","
    + ",".join(list(map(lambda x: str(x), list(syscalls.keys()))))
    + ",TP,FP,FN,TN\n"
)

line_no = 2
for name, tag in containers:
    with open(f"{LLM_path}{name}__trial1") as f:
        llm_body = json.load(f)  # List of syscall names
    with open(f"{dyn_path}{name}:{tag}.json") as f:
        dyn_body = json.load(f)  # List of numbers

    line += f"{name}:{tag},"
    for num, sys in syscalls.items():
        if sys in llm_body:  # In LLM query
            if num in dyn_body:  # # In dyn => TP
                line += "TP,"
            else:  # Not in dyn => FP
                line += "FP,"
        else:  # Not in LLM query
            if num in dyn_body:  # # In dyn => FN
                line += "FN,"
            else:  # Not in dyn => TN
                line += "TN,"
    line += f"=COUNTIF(B{line_no}:MJ{line_no},MK1),"
    line += f"=COUNTIF(B{line_no}:MJ{line_no},ML1),"
    line += f"=COUNTIF(B{line_no}:MJ{line_no},MM1),"
    line += f"=COUNTIF(B{line_no}:MJ{line_no},MN1),"
    line += "\n"
    line_no += 1

with open("analysis.csv", "w") as f:
    f.write(line)
