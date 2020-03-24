"""
This file provide basic memory monitoring functions to easily know how much memory does the current process consume.
"""
import os

PROC_STATUS = '/proc/%d/status' % os.getpid()

SCALE = {'kB': 1024.0, 'mB': 1024.0 * 1024.0, 'KB': 1024.0, 'MB': 1024.0 * 1024.0}


def _VmB(vmKey):
    """
    Private
    """
    # pylint: disable=global-statement
    global PROC_STATUS, SCALE
    # get pseudo file  /proc/<pid>/status
    try:
        t = open(PROC_STATUS)
        v = t.read()
        t.close()
    except BaseException:
        return 0.0  # non-Linux?
     # get VmKey line e.g. 'VmRSS:  9999  kB\n ...'
    i = v.index(vmKey)
    v = v[i:].split(None, 3)  # whitespace
    if len(v) < 3:
        return 0.0  # invalid format?
     # convert Vm value to bytes
    return float(v[1]) * SCALE[v[2]]


def memory(since=0.0):
    """
    Return memory usage in bytes.
    """
    return _VmB('VmSize:') - since


def resident(since=0.0):
    """
    Return resident memory usage in bytes.
    """
    return _VmB('VmRSS:') - since


def stacksize(since=0.0):
    """
    Return stack size in bytes.
    """
    return _VmB('VmStk:') - since
