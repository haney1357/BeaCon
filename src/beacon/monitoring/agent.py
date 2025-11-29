#!/usr/bin/python3
# Last Modified at Nov 23, 2025

"""@file agent.py
@brief  Execute monitoring agent
@author Haney Kang

@details
##
"""

import os
import logging
from time import sleep, time
from queue import Queue
from threading import Thread

from core.BPF import RobustBPF
from core.container import Container
from .ebpf.types import cast_data, Namespace_t, Event_t

from typing import Optional


class Monitoring(Thread):
    """@class Monitoring
    @brief Worker thread that loads eBPF, waits for a container, samples for a duration, and returns a snapshot.

    The eBPF program writes per-cgroup bitmaps of syscalls and capabilities into the `event` map.
    This thread waits for a container notification (to know which cgroup to read), then sleeps for
    the sampling window, and finally extracts/returns the event snapshot for that cgroup.

    @note Requires root privileges because BPF attach and kprobe/tracepoint operations need CAP_BPF/CAP_SYS_ADMIN.
    """

    def __init__(self, duration: int, input_queue: Queue, output_queue: Queue):
        """
        @param duration     Sampling window in seconds (time to wait before reading the map).
        @param input_queue  Queue where MonitoringAgent posts the target Container.
        @param output_queue Queue where this thread publishes the parsed snapshot (or None).
        """
        assert os.geteuid() == 0  # Should be root for correct monitoring
        super().__init__()
        self.bpf = RobustBPF(src_file=b"monitoring/ebpf/inst.c")
        self.duration = duration
        self.input_queue = input_queue
        self.output_queue = output_queue
        self._map_name = "event"

    def run(self):
        """
        @brief Thread main: wait for a Container, sample for `duration`, read BPF map, publish result.
        """
        sleep(self.duration)
        container: Container = self.input_queue.get()
        self.read_data(container)

    def read_data(self, container: Container):
        """
        @brief Read and publish one snapshot for the given container from the eBPF map.

        @param container  Target container (provides pid/cgroup info).
        """
        if not container.alive():
            self.output_queue.put(None)
            return

        namespace = container.namespace()
        if namespace is None:
            raise RuntimeError("Container is not working")
        table = cast_data(self.bpf[self._map_name])
        ev = table.get(Namespace_t(**namespace))

        self.output_queue.put(ev)


class MonitoringAgent:
    """@class MonitoringAgent
    @brief Orchestrates a single monitoring run.

    Each MonitoringAgent instance corresponds to ONE monitoring session.
    You MUST create a new instance per container run.
    """

    def __init__(self, duration: int):
        """
        @param duration Sampling window in seconds.

        @note Re-entrant safe: multiple __init__ calls after first are ignored.
        """
        self.input_queue: Queue = Queue()
        self.output_queue: Queue = Queue()
        self.thread = Monitoring(duration, self.input_queue, self.output_queue)
        self.duration = duration
        self._init_time = None
        self._notified = False

    def start(self):
        """@brief Start the monitoring worker thread.

        @throws RuntimeError if called more than once.
        """
        if self._init_time is not None:
            raise RuntimeError("Monitoring Agent has been already executed")

        self._init_time = time()
        self.thread.start()
        logging.info("[monitoring.agent] Monitoring Agent executed.")

    def notify(self, container: Container):
        """@brief Bind the monitoring to a specific container.

        @param container Target container instance (must be started).
        @throws RuntimeError if start() has not been called.
        """
        if self._init_time is None:
            raise RuntimeError("Monitoring Agent is not running")

        self._notified = True
        self.input_queue.put(container)

    def get_result_monitoring(self) -> Optional[Event_t]:
        """@brief Block until the worker thread finishes and return the snapshot.

        @return Event_t instance (with .syscalls()/.capabilities()) or None if container died.

        @throws RuntimeError if called before start() or before notify().
        """
        if self._init_time is None:
            raise RuntimeError("Monitoring Agent is not working")

        if not self._notified:
            raise RuntimeError("Container has not been notified")

        self.thread.join()
        logging.info(
            f"[monitoring.agent] Monitoring duration: {time() - self._init_time:.3f}s"
        )
        return self.output_queue.get()


if __name__ == "__main__":
    logging.basicConfig(filename="log", level=logging.INFO)

    if os.geteuid() != 0:
        print("Run as super user")
        exit(0)

    print("== Starting container test ==")

    container = Container(img="nginx")

    monitoring = MonitoringAgent(15)
    monitoring.start()
    container.start()
    monitoring.notify(container)
    ev = monitoring.get_result_monitoring()
    container.clean()

    if ev is None:
        print("[monitoring.agent] No data (container died?)")
    else:
        print(ev.syscalls())
        print(ev.capabilities())

    container = Container(img="nginx")

    monitoring = MonitoringAgent(15)
    monitoring.start()
    container.start()
    monitoring.notify(container)
    ev = monitoring.get_result_monitoring()
    container.clean()

    if ev is None:
        print("[monitoring.agent] No data (container died?)")
    else:
        print(ev.syscalls())
        print(ev.capabilities())
