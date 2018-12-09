# Kunafa
A python script that uses PMU to monitor memory bandwidth, cache, and other performance metrics of a cluster.

## Why use it
Currently, cluster monitoring or job tracing focus on few metrics like CPU utilization and memory capacity usage, which are useful but not sufficient for in-depth analysis. 
We build this tool for cluster administrators to collect more useful information at near-zero overhead.

The tool reads the Performance Monitoring Unit (PMU) periodically, and calculates several node-wide performance metrics for each computing node:

1. Retired Instructions (Insns), the total instructions executed on the node. If there are 2 sockets and 12 cores for each, then this value is the sum of 24 cores.
2. Cycles (Cycles), the total active cycles on the node. IO wait leads to CPU stall while memory wait does not. So a 100% utilized core is not necessary to be running computation all the time. 
3. Memory Instructions (MemIns), the total instruction for memory access. This is the sum of read and write operations to the L1 data cache.
4. Last-level cache references (LLC-Ref), the references to LLC.
5. Last-level cache misses (LLC-Mis), the misses to LLC. *LLC-Mis/LLC-Ref=LLC Miss Rate*. Note that this value does not reflect the behavior of hardware prefetcher.
6. Main memory reads (DRAM-R), the data volume read from main memory.
7. Main memory writes (DRAM-W), the data volume write to main memory. 
8. PCIe-R, experimental feature
9. PCIe-W, experimental feature
10. Netif_rx, experimental feature
11. Netif_rcv_skb, experimental feature

From the memory bandwidth data, we have successfully identified the performance bottleneck of several scientific computing programs, and improve the scheduling strategy accordingly. 

## How to use
First, you need to open the file and change the ```cps``` variable to the exact number of cores per socket according to your system configuration.

Then, type ```sudo ./monitor.py -v``` to start, you may see output like this on the screen
```bash
Start at 2018-11-01 06:42:08.923980 (UTC) on ln43, Interval = 120 seconds
YYYY-MM-DD HH:MM:SS.micros Insns(G)   Cycles(G)  MemIns(G)  LLC-Ref(G) LLC-Mis(G) DRAM-R(GB) DRAM-W(GB) PCIe-R(GB) PCIe-W(GB) Netif_rx Netif_rcv_skb
2018-11-01 06:48:08.992751 1.7460e+04 8.9793e+03 7.2778e+03 1.0957e+02 1.1215e+01 2.2228e+03 9.8252e+02 6.0182e+02 2.7390e-02 5.2000e+01 5.2000e+01
2018-11-01 06:48:08.993091 1.6927e+04 8.9086e+03 7.1102e+03 1.1180e+02 1.2087e+01 2.3124e+03 1.0123e+03 6.1000e+02 1.3509e-02 6.0000e+00 6.0000e+00
```
The first line tells the monitor start time, node hostname, and sample interval is 120 seconds.
Meanwhile, the result is logged to a file.
Without the verbose option ```-v``` , no screen output.

For more information, try ```-h```.

For cluster monitoring, simply run this script on each computing node. 

## How it works
### PMU 
Performance Monitoring Units are hardware units on modern processors that help users to collect performance related data. For Intel Xeon E5/E7 processors, you may like to check [the manual](https://www.intel.com/content/www/us/en/processors/xeon/xeon-e5-e7-v4-uncore-performance-monitoring.html)

PMU is not architectural, so the available counters and their usage can be different for each CPU model. 

This script currently has no support for latest skylake processor, which has a significant change in PMU mechanism.

### Linux perf tool
```perf``` is a Linux command line tool for performance monitoring. We use perf to read interesting PMU counters. The overhead of reading PMU is very low, especially when we read in a low frequency (every 30 seconds).

Some PMU counters, e.g., memory controller counters, are system-wide (or node-wide), so you may need the ```sudo``` privilege to execute the command. Otherwise, an error would occur. 

## Who use it
This tool has been deployed on a cluster in TAMU-Q.
We are happy to have more users (and their complaints).

## How to contribute
This tool is originally developed by Xiongchao Tang and Nosayba El-Sayed from Qatar Computing Research Institute. 
There are a lot of improvements can be made. 

1. To use this tool on older or newer machines. It means he may need to modify the ```perf``` events according to the processor models.
2. To integrate this tool into existing cluster monitoring frameworks.
3. To simplify the deployment process. 
4. And anything can help

To contribute, you can folk your repository, or submit a pull request, or just post an issue. 
Please also read develop.md for information for development.


