#!/usr/bin/python3
# Last Modified at Nov, 23, 2025

"""@file types.py
@brief  Define types and casting for eBPF c programs
@author Haney Kang
"""
from typing import Dict

from typing import NamedTuple


class Namespace_t(NamedTuple):
    cgroup: int
    user: int
    uts: int
    ipc: int
    mnt: int
    pid: int
    net: int


class Event_t:
    """@class Event_t
    @brief      Type defined class which contains event identifiers
                from monitoring.
    """

    def __init__(self, event):
        """
        Set the value in Event_t class.

        @param      event       Event data given from monitoring.
        """
        self.syslist = self.bit2idx(event.sys, 32)
        self.caplist = self.bit2idx(event.cap, 32)

    def bit2idx(self, bit_arr, bit_size):
        """
        Convert bitmap to index list.

        @param      bit_arr     Bit array for converting.
        @param      bit_size    A unit size of bit array.
        @return     idx_list    An index list of corresponding bitmap.
        """
        return list(
            filter(
                lambda bit_idx: bit_arr[(bit_idx // bit_size)] & 1 << bit_idx % 32,
                range(bit_size * len(bit_arr)),
            )
        )

    def syscalls(self):
        """
        Return index list of system call events.

        @return     idx_list    An index list of system call events.
        """
        return self.syslist

    def capabilities(self):
        """
        Return index list of capability events.

        @return     idx_list    An index list of capabilities events.
        """
        return self.caplist


def cast_data(data) -> Dict[Namespace_t, Event_t]:
    """
    Merge per-CPU values for each namespace key and return {bcc_ns: Event_t}.
    Assumes value layout matches struct sys_and_cap_t (sys[24], cap[2], seccomp_flag).

    @param      data        Raw data from eBPF
    """
    result = {}

    for (
        bcc_ns,
        per_cpu_events,
    ) in data.items():  # per_cpu_events: list[ctypes-struct] per CPU
        if not per_cpu_events:
            continue
        agg = per_cpu_events[0]
        for s in per_cpu_events[1:]:
            agg.seccomp_flag = agg.seccomp_flag or s.seccomp_flag
            for i in range(24):
                agg.sys[i] |= s.sys[i]
            for i in range(2):
                agg.cap[i] |= s.cap[i]
        ns_key = Namespace_t(
            **{name: getattr(bcc_ns, name) for name, _ in bcc_ns._fields_}
        )
        result[ns_key] = Event_t(agg)
    return result
