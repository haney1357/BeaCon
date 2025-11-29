#!/usr/bin/python3

import json
import requests
import os
from typing import Any, Dict, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_URL = "https://hub.docker.com/v2/repositories/library/?page_size=100&ordering=pull_count"
TAG_URL = "https://hub.docker.com/v2/repositories/library/{}/tags?page_size=100"
OS = "linux"
"""
`dpkg --print-architecture`
"""
ARCH = "amd64"
DST_JSON = "categories.json"
NOT_SUPPORTED_DST_JSON = "not_supported_imgs.json"

def get_official_list() -> Dict[str, Any]:
	"""
	Get list of official containers images
	"""
	if os.path.isfile(os.path.join(BASE_DIR, DST_JSON)) and \
		os.path.isfile(os.path.join(BASE_DIR, NOT_SUPPORTED_DST_JSON)):
		with open(os.path.join(BASE_DIR, DST_JSON), 'r') as f:
			images_final = json.load(f)
	else:
		while True: # Loop for failure
			images = {}
			count_list = []
			url = REPO_URL
			while True: # Page iteration
				response = requests.get(url)
				if response.status_code != 200:
					continue
				response_body = response.json()
				url = response_body["next"]
				count_list.append(response_body["count"])
				images.update({elem["name"]: [category["slug"] for category in elem["categories"]]
					for elem in response_body["results"]})

				if url is None:
					break

			count_flag = True
			count = None
# Check consistency of 'count' field
			for count_elem in count_list:
				if count is None:
					count = count_elem
				elif count != count_elem:
					count_flag = False

		images_final = {}
		not_supported = []
		for image in images.keys(): # Per container image
			print(f"Inspecting {image} image")
			tag = None
			url = TAG_URL
# Find newest tag supporting OS (linux) and architecture (amd64).
			while True: # Per tag page
				response = requests.get(url.format(image))
				if response.status_code != 200:
					continue
				response_body = response.json()
				url = response_body["next"]
				results = response_body["results"]
				for result in results:
					for tag_img in result["images"]:
						if tag_img["architecture"] == ARCH and (tag_img["os"] == OS or tag_img["os"] == ""):
							tag = result["name"]
							break
					if tag:
						break
				if tag:
					break
				if url is None:
					break
			if not tag:
				not_supported.append(image)
			else:
				images_final[f"{image}:{tag}"] = images[image]

		with open(os.path.join(BASE_DIR, DST_JSON), 'w') as f:
			json.dump(images_final, f)

		with open(os.path.join(BASE_DIR, NOT_SUPPORTED_DST_JSON), 'w') as f:
			json.dump(not_supported, f)
	return images_final

