#!/usr/bin/python3

import json
import os
from typing import Any, Dict
from pprint import pprint
from util.container import Container
from time import sleep

from .container_pull import container_pull
from .get_official_list import get_official_list

images = get_official_list()

print(f"Pulling images...")
for image in images.keys():
    container_pull(image)

## Get exposed Ports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INFO_DST_JSON = os.path.join(BASE_DIR, "img_info.json")
ANALYSIS_JSON = os.path.join(BASE_DIR, "analysis.json")

if os.path.isfile(INFO_DST_JSON):
    with open(INFO_DST_JSON, 'r') as f:
        exposed_port_images = json.load(f)
else:
    exposed_port_images = {}

remained = set(images.keys()) - set(exposed_port_images.keys())
dead = []
test_args = [
    {"opts": [], "args": []}, 
    {"opts": ["-it"], "args": []}, 
    {"opts": ["-e", "MYSQL_ROOT_PASSWORD=my-secret-pw"], "args": []}, 
    {"opts": [], "args": ["/bin/bash"]}, 
    {"opts": ["-it"], "args": ["/bin/bash"]}, 
]
for image in remained:
    success = False
    for args in test_args:
        container = Container(image, args=args["args"], opts=args["opts"])
        container.start()
        sleep(20)
        if not container.isAlive():
            print(f"{image} dead")
            container.remove()
            continue
        inspect = container.inspect()
        if inspect is None:
            print(f"{image} inspection error")
            container.remove()
            continue

        if "ExposedPorts" not in inspect["Config"]:
            exposed = []
        else:
            exposed = [ {"port": exposed_str.split('/')[0], "proto": exposed_str.split('/')[1] } for exposed_str in inspect["Config"]["ExposedPorts"].keys()]

        exposed_port_images[image] = {
            "categories": images[image],
            "args": args["args"],
            "opts": args["opts"],
            "exposed-port": exposed,
        }
        container.remove()
        success = True
        break
    if not success:
        dead.append(image)

with open(INFO_DST_JSON, 'w') as f:
    json.dump(exposed_port_images, f, indent=4)

print(f"Not supported containers: {dead}")
print(f"Numbuer of supported containers: {len(exposed_port_images)}")
categories = set()
for img in exposed_port_images.keys():
    categories.update(exposed_port_images[img]["categories"])

print("Category\t\t\t # Category container # Category Exposed")
analysis = {}
for category in categories:
    category_imgs = list(filter(lambda img: category in exposed_port_images[img]["categories"], 
            exposed_port_images.keys()))
    category_imgs_exposed = list(filter(lambda img: exposed_port_images[img]["exposed-port"],
            category_imgs))
    print(category, len(category_imgs), len(category_imgs_exposed))
    analysis[category] = {"containers": category_imgs, "exposed_containers": category_imgs_exposed}

none_category_imgs = list(filter(lambda img: exposed_port_images[img]["categories"], exposed_port_images.keys()))
none_category_imgs_exposed = list(filter(lambda img: exposed_port_images[img]["exposed-port"],
        none_category_imgs))
analysis["None"] = {"containers": none_category_imgs, "exposed_containers": none_category_imgs_exposed}

from pprint import pprint
pprint(analysis)
with open(ANALYSIS_JSON, 'w') as f:
    json.dump(analysis, f, indent=4)


