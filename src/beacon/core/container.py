#!/usr/bin/python3
# Last modified at Nov 23, 2025

"""@file container.py
@brief  Wrapper for container operations using Docker Library.
@author Haney Kang

@details
Provides a class to manage the lifecycle and properties of a container instance via docker-py library.
"""

import os
import docker
import logging
from threading import Thread, Lock, Event
from typing import Optional, Dict, Any

from core.wrapper import lsns

client = docker.APIClient()


class DockerEventLoop(Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self._subscribers = {}
        self._lock = Lock()

    def subscribe_start(self, cid: str, callback):
        with self._lock:
            self._subscribers[cid] = callback

    def run(self):
        for event in client.events(decode=True):
            if event.get("Type") != "container":
                continue
            if event.get("Action") != "start":
                continue

            cid = event.get("id")
            if not cid:
                continue

            with self._lock:
                callback = self._subscribers.get(cid)
            if callback:
                callback()


event_loop = DockerEventLoop()
event_loop.start()


class Container:
    """
    @class Container
    @brief Represents a Docker container and provides control over its lifecycle.
    """

    def __init__(
        self,
        img: str,
        **kwargs: Optional[Dict[str, Any]],
    ):
        """
        @brief Initializes and prepares the container configuration, create the container.

        @param opts Options passed to Docker engine.
        @param args Arguments passed to the command inside the container.
        """
        self.img = img
        self.pid = -1
        self.ns = None
        self.container_id = client.create_container(self.img, **kwargs)["Id"]
        self._ready = Event()
        logging.info(
            f"[core.container] Creating container.\n\tImage: {self.img}, ID: {self.container_id}"
        )
        event_loop.subscribe_start(self.container_id, self._on_container_started)

    def start(self):
        """
        @brief Starts the container.
        """
        client.start(self.container_id)

        logging.info(
            f"[core.container] Starting container.\n\t Image: {self.img}, ID: {self.container_id}"
        )

    def inspect(self) -> Dict[str, Any]:
        """
        @brief Retrieve container property information.

        @return Dictionary with container inspection info, or None on error.
        """
        return client.inspect_container(self.container_id)

    def alive(self) -> bool:
        """
        @brief Checks if the container is currently running.

        @return True if running, False otherwise.
        """
        inspection = self.inspect()
        return inspection and inspection.get("State", {}).get("Status") == "running"

    def _on_container_started(self):
        info = client.inspect_container(self.container_id)
        state = info.get("State", {})
        pid = state.get("Pid", 0)
        if not pid:
            return

        self.pid = pid
        self.ns = lsns(pid)
        self._ready.set()

    def wait_until_ready(self, timeout=None):
        if not self._ready.wait(timeout=timeout):
            self.pid = 0

    def get_pid(self) -> int:
        """
        @brief Retrieves the PID of the container's main process.

        @return Integer PID or 0 if unavailable.
        """
        if self.pid == 0:
            return 0
        elif self.pid == -1:
            self.wait_until_ready(5)
        return self.pid

    def namespace(self) -> Optional[Dict[str, str]]:
        """
        @brief Gets the namespace object of the container.

        @return Namespace object or None on failure.
        """
        if self.ns is not None:
            return self.ns

        if self.pid == 0:
            return None

        self.wait_until_ready(5)
        if self.pid == 0 or self.ns is None:
            return None

        return self.ns

    def clean(self):
        client.remove_container(self.container_id, force=True)


if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Run as super user")
        exit(0)

    print("== Starting container test ==")

    container = container = Container(
        img="alpine", command=["sleep", "5"]  # Light image  # Long enough for testing
    )

    # Assign UUID-based container name
    container.start()

    # Check PID is valid
    pid = container.get_pid()
    assert pid > 0, "PID should be greater than 0"
    print(f"✅ PID: {pid}")

    # Check namespace info is not None
    ns = container.namespace()
    assert ns is not None, "Namespace info should not be None"
    print(f"✅ Namespace: {ns}")

    # Cleanup
    container.clean()

    print("== Test passed ==")
