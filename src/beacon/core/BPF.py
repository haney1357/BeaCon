#!/usr/bin/python3
# Last Modified at Jul 25, 2025

"""@file BPF.py
@brief  Extension of BCC BPF with more robust cleanup support.
@author Haney Kang
"""

import os
from bcc import BPF
from bcc.libbcc import lib
from bcc.table import PerfEventArray

class RobustBPF(BPF):
    """
    @class RobustBPF
    @brief Extended BPF class with safe cleanup support for probes and perf buffers.

    @details
    This subclass adds a `cleanup()` method to detach and destroy all active probes, tracepoints,
    perf events, and ring buffers. This helps ensure clean shutdowns of eBPF programs and avoids
    lingering state in the kernel.
    """
    def cleanup(self):
        """
        @brief Safely detaches all active eBPF components and releases resources.

        @note
        Intended to be called before program termination to avoid stale state.
        """
        # Detach all kprobes
        for k, v in list(self.kprobe_fds.items()):
            self.detach_kprobe_event(k)

        #Detach all uprobes
        for k, v in list(self.uprobe_fds.items()):
            self.detach_uprobe_event(k)

        # Detach all tracepoints
        for k, v in list(self.tracepoint_fds.items()):
            self.detach_tracepoint(k)

        # Detach all raw tracepoints
        for k, v in list(self.raw_tracepoint_fds.items()):
            self.detach_raw_tracepoint(k)

        # Clean up perf ring buffers and perf events
        table_names = list(self.tables.keys())
        for table_name in table_names:
            if isinstance(self.tables[table_name], PerfEventArray):
                del self.tables[table_name]

        for (event_type, config) in list(self.open_perf_events.keys()):
            self.detach_perf_event(event_type, config)

        # Close trace file if opened
        if self.tracefile:
            self.tracefile.close()
            self.tracefile = None

        # Close function file descriptors
        for func_name, func in list(self.funcs.items()):
            try: 
                os.close(func.fd)
            except Exception: 
                # TODO
                pass

        # Destroy the BPF module if present
        if self.module:
            lib.bpf_module_destroy(self.module)
            self.module = None
