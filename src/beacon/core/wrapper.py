#!/usr/bin/python3
# Last modified at Nov 01, 2025

"""@file wrapper.py
@brief      Wrapper module for running bash commands
@author Haney Kang
"""

import os
import logging
import json
import subprocess
from typing import List, Dict, Optional


# @deprecated
def run_cmd(comm: List[str], timeout: Optional[int] = None) -> int:
    """
    @brief Run a shell command with optional timeout.

    @param  comm    List of command elements (e.g., ["ls", "-l"])
    @param  timeout Timeout in seconds before killing the command.
    @return int     Return code of the command. -1 on error, -2 on timeout.
    """
    if not comm:
        logging.warning("[core.wrapper] run_cmd() received empty command.")
        return 0

    comm = list(map(os.path.expandvars, comm))

    try:
        proc = subprocess.run(
            comm,
            timeout=timeout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
    except subprocess.TimeoutExpired:
        logging.error(f"[core.wrapper] Timeout while running command: {' '.join(comm)}")
        return -2
    except Exception as e:
        logging.error(
            f"[core.wrapper] Unknown error while running command: {' '.join(comm)}\n{e}"
        )
        return -1

    if proc.returncode != 0:
        logging.error(
            f"[core.wrapper] Command failed: {' '.join(comm)}\nStderr: {proc.stderr.strip()}"
        )
    return proc.returncode


def lsns(pid: int) -> Optional[Dict[str, str]]:
    """
    @brief Run `lsns` on a specific PID to retrieve namespace information.

    @param      pid     Process ID to inspect.
    @return     dict    A dictionary of {namespace_type: namespace_id} or None on failure.
    @throws     Exception if the user is not root.
    """
    if os.geteuid() != 0:
        raise PermissionError("`lsns` requires root privileges to work properly.")

    try:
        proc = subprocess.run(
            ["lsns", "-Jno", "TYPE,NS", "-p", str(pid)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        if proc.returncode != 0:
            logging.warning(
                f"[core.wrapper] lsns failed for pid={pid}: {proc.stderr.strip()}"
            )
            return None

        namespaces = json.loads(proc.stdout).get("namespaces", [])
        return {ns["type"]: ns["ns"] for ns in namespaces}
    except Exception:
        logging.warning(
            f"[core.wrapper] No namespace info found for pid={pid} (likely nonexistent)"
        )
        return None


if __name__ == "__main__":
    from pprint import pprint

    print("== Testing lsns() on current process ==")
    try:
        current_pid = os.getpid()
        ns_info = lsns(current_pid)
        if ns_info is not None:
            print(f"✅ Namespaces for PID {current_pid}:")
            pprint(ns_info)
        else:
            print(f"❌ Failed to retrieve namespaces for PID {current_pid}")
    except Exception as e:
        print(f"❌ Exception occurred: {e}")

    print("\n== Testing lsns() on invalid PID ==")
    try:
        invalid_pid = 999999  # assuming this PID doesn't exist
        ns_info = lsns(invalid_pid)
        if ns_info is None:
            print(f"✅ Properly handled invalid PID {invalid_pid}")
        else:
            print(f"❌ Unexpected result for invalid PID {invalid_pid}:")
            pprint(ns_info)
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
