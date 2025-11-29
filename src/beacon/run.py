#!/usr/bin/python3
# Last Modified at Aug 10, 2025

"""@file run.py
@brief  Running BeaCon with configuration
@author Haney Kang
"""
# run_monitoring.py     
# USAGE: ./run.py <duration> <period> <container_img>

import sys
import os
import sched
import time
import logging

from util.BPF import RobustBPF
from util.container import Container
from inst.types import cast_data, Namespace_t

def arg_intp(argv):
    if os.geteuid() != 0:
        print("%s: Permission Error" % (argv[0]))
        exit(1)

    if len(argv) < 4 :
        print("Usage: %s <duration> <period> <container_img>" % (argv[0]))
        exit(1)
    
    try:
        duration = int(argv[1])
        period = int(argv[2])
        if duration < period: raise ValueError
    except ValueError:
        print("Usage: %s <duration> <period> <container_img>" % (argv[0]))
        print("Invalid value of <duration> and <period>")
        exit(1)

    return duration, period, argv[3]

def read_data(init_time, data, container):
    print("-- %f elasped --" % (time.time() - init_time))

    if not container.isAlive(): return

    ns = Namespace_t(**container.namespace())

    ev = cast_data(data)[ns]
    print(ev.syslist)

def count_data(data, container):
    if not container.isAlive(): return

    ns = Namespace_t(**container.namespace())
    syslist = cast_data(data)[ns].syslist
    caplist = cast_data(data)[ns].caplist

    print(len(syslist), len(caplist))

if __name__ == "__main__":
    logging.basicConfig(filename='log', level=logging.INFO)

#    load_config(
    duration, period, img_name = arg_intp(sys.argv)
    
    b = RobustBPF(src_file = "./inst/monitor.c")
    data = b['event']

    if len(sys.argv) > 5:
        opt_num = int(sys.argv[4])
        container = Container(img_name, opts = sys.argv[5:5 + opt_num], args = sys.argv[5+opt_num:])
    else:
        container = Container(img_name)

    # Global scheduler for time sequential operation
    s = sched.scheduler(time.time, time.sleep)

    # Basis init time
    init_time = time.time()
    
    # Monitoring operation registration
    for delay in range(period, duration + 1, period):
        s.enter(delay, 0, read_data, argument=(init_time, data, container,))

    # Container operation registration
    s.enter(0, 0, container.start)
    s.enter(duration, 1, count_data, argument=(data, container,))
    s.enter(duration, 2, container.terminate)

    s.run()
