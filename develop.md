# Document for new developers of Kunafa

## Start from here

The current version of Kunafa is developed on Xeon E5 v4, and has been successfully deployed on Xeon E5 v3. The network part only works for Infiniband, and is known not working for Cray Aries network.

PMU events are not architectural. Instead, they are micro-architectural, which means the available events and the meaning of events can change for different CPU models.
For example, the Home Agent (HA) is a per-socket component on Xeon E5 v4 (Broadwell), but becomes a per-core component on Scalable ( Skylake) processors.
Another example is the LLC becomes non-inclusive (some data in L2 are not in L3) from Skylake, while precedented processors have inclusive LLC (all data in L2 are also in L3).
In short words, PMU related code is **not** portable.

**You can only use the PMU after you decide and know your experiment platform!**

For information about the events and counters for a specific platform, please see Intel's manual.
Some examples are given below, you can search by their names and hopefully find a PDF.

* xeon-e5-v4-spec-update (cores, frequency, etc.)
* xeon-e5-e7-v4-uncore-performance-monitoring (Uncore PMU: LLC, CA, IMC, PCIe, QPI, etc.)
* Intel-64-ia-32-architectures-software-developer-manual (Core PMU: IPC, L1, L2, Branch, etc.)
* intel-xeon-phi-systemssoftwaredevelopersguide (for Xeon phi)

**Please read Intel's manuals and make sure you understand the architecture before starting to develop a PMU-based tool.**

## Introduction to Linux perf command

The Linux OS provides system calls to manipulate PMU.
However, the interface is difficult for beginners like me, so users usually use a higher-level tool, the **perf** command.
There is a detailed introduction website to Linux perf in [Brendan Gregg's Blog](http://www.brendangregg.com/overview.html)

You can just type ``perf -h`` for help.
When you try to check available events, you would like to use ``perf list``.
Please note that the listed events are not exhaustive.
You can use ``sudo perf list`` to see more available events, not only from the PMU, but also from the OS.
Again, the list given with sudo privilege is not exhaustive.
There are hundreds if not thousands of PMU events for latest Intel Xeon processors.

## Advanced perf usage

How to specify a PMU event given in Intel documents but not in perf list?
The answer is simple: *Just tell perf what you want*
An event is not listed doesn't mean it is unsupported by perf.

To check what PMU components your platform has, try the following two commands

``txc@bic05:~ $ ls /sys/devices
breakpoint   intel_cqm    pci0000:7f  software       uncore_cbox_10  uncore_cbox_3  uncore_cbox_8  uncore_imc_1  uncore_qpi_1    uncore_sbox_1
cpu          intel_pt     pci0000:80  system         uncore_cbox_11  uncore_cbox_4  uncore_cbox_9  uncore_imc_4  uncore_r2pcie   uncore_sbox_2
cstate_core  LNXSYSTM:00  pci0000:ff  tracepoint     uncore_cbox_12  uncore_cbox_5  uncore_ha_0    uncore_imc_5  uncore_r3qpi_0  uncore_sbox_3
cstate_pkg   msr          platform    uncore_cbox_0  uncore_cbox_13  uncore_cbox_6  uncore_ha_1    uncore_pcu    uncore_r3qpi_1  uncore_ubox
intel_bts    pci0000:00   pnp0        uncore_cbox_1  uncore_cbox_2   uncore_cbox_7  uncore_imc_0   uncore_qpi_0  uncore_sbox_0   virtual``
The above command tells where the PMU counters are.

``txc@bic05:~ $ ls /sys/bus/event_source/devices/uncore_cbox_0/format/
edge  event  filter_c6  filter_isoc  filter_link  filter_nc  filter_nid  filter_opc  filter_state  filter_tid  thresh  tid_en  umask``
This command tells the *fields* to specify.

For example, the event string for **memory read request count** is ``uncore_ha_0/event=0x01,umask=0x03/``,
and the event string for something about PCIe is ``uncore_cbox_0/event=0x35,umask=0x01,filter_tid=0x3F,filter_opc=0x1C8/``

## Monitoring infiniband traffic

A possible solution is to monitor the PCIe traffic from CPU side.
However, local IO traffic and CPU-GPU traffic also use PCIe so everything will mess up.

For Mellanox Infiniband, you can use **perfquery** for monitoring.
For example, ``perfquery -R; while true; do sleep %d; perfquery -x -r; done;`` performs periodic read and reset.
Please note that the perfquery command is originally 32-bit (yes it always overflows) so make sure you use ``-x`` option for its 64-bit version.

**please google perfquery and understand how it behaves when overflow/reset/error before using it!**

Also, note that perfquery is available on each HCA device.
It means that you can monitor the network from both *computing nodes* and *network switches*.
Actually, monitoring on switches is easier.
But make sure your driver version, since some old version will stop working after a certain number of queries.

## Some useful tools

PCM is a tool developed by Intel. [PCM](https://github.com/opcm/pcm)

pmu-tools provides a wrapper to Linux perf so that you can use an event name instead of an event code. [pmu-tools](https://github.com/andikleen/pmu-tools)

PAPI is a library that provides basic C/C++/Fortran APIs to access pmu. While perf and PCM are outside the program, PAPI can be used for intra-program fine-grained monitoring. [PAPI](https://bitbucket.org/icl/papi.git)

## Explanation for the current design

### Monitoring the memory bandwidth

The current version (2018.12.09) uses the *home agent* box to monitor the DRAM request count.
Then the number of DRAM request multiplies 64 Bytes/request is the *main memory access data volume*.
Now you get how to measure the memory bandwidth.

For Broadwell processors, there are two home agents per *socket*.
For Skylake processors, there is one home agent per *core*.
We do not have any implementation for Skylake yet.

### Monitoring the cache behavior

On our platform (Xeon E5 2680 v4), some cache events are different from our first intuition, so we give a caution list here.
We got those from trial and error.
Please read carefully if you don't want to exactly follow our mistakes.

* There are no events for *memory instructions*, so we use the sum of *L1-dcache-loads* and *L1-dcache-stores* as a proxy metric.
* While prefetching is enabled, the *cache-reference* and *cache-misses* only count the demand from instructions, ignoring prefetch demands. This can lead to strange cache miss rate.
* Prefetch can be turn-off in BIOS configuration, and most programs will slow down for 10% to 200%.
* The hardware prefetcher is in L2. However, the data can be prefetched into L2 or L3. Sometimes the L2 is busy so the processor thinks it better to put prefetched data in L3 and not to burden L2.
* The *cache-reference* and *cache-misses* are for LLC reads. In other words, you don't have a reference/hit/miss for a write.
* L1 and L2 hit/miss/ref are also supported, but in a quite massive manner, please go to the manual if you like.
* Some events are not working with hyperthreading. The manual should mark this in this case.
* The PMU counts are not exactly 100% accurate. Error less than 5% is acceptable, especially when multiplexing is enabled. You don't need to explicitly enable multiplexing, it is automatically enabled when selected events are more than hardware counters.
* It seems that PMU values are hardware metrics and not moved with processes. I.e., they will not be push or pop during the OS context switching. So you'd better pin processes to cores if you want to measure the per-process counters. For per-core and per-node monitoring, everything is fine.
* For IO and Network traffic, the data can pass directly from LLC to PCIe and no need to walk through main memory. Of course, it depends on LLC capacity and a lot of other things.
* The memory behavior of intra-node MPI communication highly depends on implementation.