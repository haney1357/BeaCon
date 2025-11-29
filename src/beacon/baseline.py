#!/usr/bin/python3
# Last Modified at Nov 25, 2025


import os
import json
from core.container import Container
from monitoring.agent import MonitoringAgent

if os.geteuid() != 0:
    print("Run as super user")
    exit(0)

done = list(map(lambda f: f[:-5], os.listdir("result")))

from pprint import pprint

with open("stable_args.json") as f:
    container_args = json.load(f)

for k, v in container_args.items():
    if k in done:
        continue
    container = Container(img=k, **v)
    monitoring = MonitoringAgent(60)
    monitoring.start()
    container.start()
    monitoring.notify(container)
    ev = monitoring.get_result_monitoring()
    container.clean()

    if ev is None:
        print(f"No data: {k}")
    else:
        #        print(ev.syscalls())
        #        print(ev.capabilities())
        with open(f"result/{k}.json", "w") as f:
            json.dump(ev.syscalls(), f, indent=4)
