#!/usr/bin/python3
# NOTE!!! This monitor script only works for Intel Xeon E5/E7 series
# For scalable platforms (starts from skylake), no support yet. 
# To use this script, one needs to modify the 'cps' variable according to the CPU
import subprocess
import socket
import argparse
import os
from datetime import datetime

# Colorful output
class pfmon_color:
    red     ="\x1b[31m"
    green   ="\x1b[32m"
    yellow  ="\x1b[33m"
    blue    ="\x1b[34m"
    magenta ="\x1b[35m"
    cyan    ="\x1b[36m"
    reset   ="\x1b[0m"

# Parse input options
parser = argparse.ArgumentParser(description="A PMU Monitor.")
parser.add_argument('-i', '--interval', help='interval to read counters', type=int, default=30)
parser.add_argument('-p', '--pid', help='attach to a process by pid', type=int)
parser.add_argument('-c', '--command', help='following by a command or a program', nargs='+', default=[])
parser.add_argument('-v', '--verbose', help='verbose output', action='store_true', default=False)
parser.add_argument('-j', '--jobid', help='slurm job id', type=int)
opts = parser.parse_args()
#print(opts)

# If verbose, it will output to both stdout and file
verbose = opts.verbose
# The tool will read counters per intvl ms.
intvl = opts.interval*1000
# Number of cores per socket
cps = 12 # core_per_socket
#print("Number of CPU cores per socket: %d" % cps)

# This block use Linux command 'perf' to monitor PMU counters
events = ['instructions', 'cycles'] # Number of retired instructions, number of cycles (in real frequency)
events.extend(['L1-dcache-loads', 'L1-dcache-stores']) # load/store operations to L1D, a proxy indicator of memory access instructions
events.extend(['cache-references', 'cache-misses']) # LLC (demand by instructions, exclude prefetcher read/write)
for i in range(0, 2): 
    events.append('uncore_ha_%d/event=0x01,umask=0x03/' % i) # DRAM read requests, each request is 64 Bytes
for i in range(0, 2): 
    events.append('uncore_ha_%d/event=0x01,umask=0x0C/' % i) # DRAM write requests, each request is 64 Bytest
# The below two PCIe counters are not accurate due to PMU multiplexing.
# They are intend to be an indicator of IO + Network data volume
for i in range(0, cps):
    events.append('uncore_cbox_%d/event=0x35,umask=0x01,filter_tid=0x3F,filter_opc=0x1C8/' % i) # ItoM (Mem read from PCIe)
for i in range(0, cps):
    events.append('uncore_cbox_%d/event=0x35,umask=0x01,filter_opc=0x19E/' % i) # PCIeRdCur (Mem write to PCIe)
events.extend(['rFF24','r3F24']) # L2-all-request, L2-all-misses, including both instruction demand and prefetcher
events_str = ','.join(events)

# Construct perf command
if opts.pid is not None: # Monitor during a process (specified by PID)
    perf_cmd = 'perf stat -I %d -a -x, -e %s --pid %d' % (intvl, events_str, opts.pid)
else: # Monitor during a command (if not empty)
    perf_cmd = 'perf stat -I %d -a -x, -e %s %s' % (intvl, events_str, ' '.join(opts.command))

# The output file name
if opts.jobid is not None:
    fname = 'pfmon-%d-%s.dat' % (opts.jobid, socket.gethostname()) # slurm job id, hostname    
else:
    fname = 'pfmon-%s.dat' % (socket.gethostname()) # hostname
fw = open(fname, 'a') # append, not overwrite
if not fw: 
    print("Cannot open file %s, Exit." % fname)
    exit(-1)

# Log perf command
if verbose:
    print(pfmon_color.blue + perf_cmd + pfmon_color.reset)
fw.write(perf_cmd); fw.write('\n')

# Execute perf command
p = subprocess.Popen(perf_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1)
buf = []
# Print header
info_str = "Start at %s (UTC) on %s, Interval = %d seconds" % (datetime.utcnow(), socket.gethostname(), intvl//1000)
header_str = "YYYY-MM-DD HH:MM:SS.micros Insns(G)   Cycles(G)  MemIns(G)  LLC-Ref(G) LLC-Mis(G) DRAM-R(GB) DRAM-W(GB) PCIe-R(GB) PCIe-W(GB) L2req(G) L2miss(G)"
if verbose:
    print(pfmon_color.red + info_str + pfmon_color.reset)
fw.write(info_str); fw.write('\n')
if verbose:
    print(pfmon_color.green + header_str + pfmon_color.reset)
fw.write(header_str); fw.write('\n')

# Parse perf output
for line in p.stderr:
    #print(line)
    buf.append(float(line.decode('utf-8').strip().split(',')[1])) # Decode and store perf output
    if len(buf) == len(events):
        tt = datetime.utcnow()
        res = "%s %9.4e %9.4e %9.4e %9.4e %9.4e %9.4e %9.4e %9.4e %9.4e %9.4e %9.4e" % ( 
                tt, buf[0]*1e-9, buf[1]*1e-9, (buf[2]+buf[3])*1e-9,
                buf[4]*1e-9, buf[5]*1e-9, (buf[6]+buf[7])*64*1e-9, (buf[8]+buf[9])*64*1e-9,
                sum(buf[10:10+cps])*64*1e-9, sum(buf[10+cps:10+2*cps])*64*1e-9, buf[-2]*1e-9, buf[-1]*1e-9)
        fw.write(res) # Write to file
        fw.write('\n')
        if verbose: # Screen output with color
                print ("%s %s%9.4e %9.4e %s%9.4e %9.4e %9.4e %s%9.4e %9.4e %s%9.4e %9.4e %s%9.4e %9.4e %s " % ( 
                tt, pfmon_color.yellow, buf[0]*1e-9, buf[1]*1e-9, pfmon_color.cyan, (buf[2]+buf[3])*1e-9,
                buf[4]*1e-9, buf[5]*1e-9, pfmon_color.magenta, (buf[6]+buf[7])*64*1e-9, (buf[8]+buf[9])*64*1e-9,
                pfmon_color.blue, sum(buf[10:10+cps])*64*1e-9, sum(buf[10+cps:10+2*cps])*64*1e-9, pfmon_color.reset, buf[-2]*1e-9, buf[-1]*1e-9, pfmon_color.reset))
        buf = []
