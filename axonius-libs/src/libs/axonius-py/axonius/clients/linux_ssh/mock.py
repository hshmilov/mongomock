from axonius.clients.linux_ssh.data import (DistroCommand, HDCommand,
                                            HostnameCommand, IfaceCommand,
                                            MemCommand, VersionCommand,
                                            DPKGCommand, UsersCommand)


# pylint: disable=trailing-whitespace,line-too-long,
class LocalInfoMockMixin:
    RAW_DATA = None

    def __init__(self, client_id):
        super().__init__(client_id, self.RAW_DATA)


class HostnameMock(LocalInfoMockMixin, HostnameCommand):
    RAW_DATA = 'ip-10-0-2-26'


class IfaceMock(LocalInfoMockMixin, IfaceCommand):
    RAW_DATA = \
        '''1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet6 ::1/128 scope host 
       valid_lft forever preferred_lft forever
2: wlp2s0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default qlen 1000
    link/ether 9c:b6:d0:89:a2:21 brd ff:ff:ff:ff:ff:ff
    inet 192.168.11.18/24 brd 192.168.11.255 scope global dynamic noprefixroute wlp2s0
       valid_lft 593439sec preferred_lft 593439sec
    inet6 fe80::a708:d737:661a:7eca/64 scope link noprefixroute 
       valid_lft forever preferred_lft forever
3: br-1272e8efd44d: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default 
    link/ether 02:42:ed:5b:69:21 brd ff:ff:ff:ff:ff:ff
    inet 171.17.0.1/16 brd 171.17.255.255 scope global br-1272e8efd44d
       valid_lft forever preferred_lft forever
    inet6 fe80::42:edff:fe5b:6921/64 scope link 
       valid_lft forever preferred_lft forever
4: docker0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN group default 
    link/ether 02:42:ac:a5:c0:d1 brd ff:ff:ff:ff:ff:ff
    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
       valid_lft forever preferred_lft forever
    inet6 fe80::42:acff:fea5:c0d1/64 scope link 
       valid_lft forever preferred_lft forever
5: virbr0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN group default qlen 1000
    link/ether 52:54:00:f7:eb:f0 brd ff:ff:ff:ff:ff:ff
    inet 192.168.122.1/24 brd 192.168.122.255 scope global virbr0
       valid_lft forever preferred_lft forever
6: virbr0-nic: <BROADCAST,MULTICAST> mtu 1500 qdisc pfifo_fast master virbr0 state DOWN group default qlen 1000
    link/ether 52:54:00:f7:eb:f0 brd ff:ff:ff:ff:ff:ff
169: veth0e392c6@if168: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master br-1272e8efd44d state UP group default 
    link/ether 1a:1c:c8:02:ba:ba brd ff:ff:ff:ff:ff:ff link-netnsid 0
    inet6 fe80::181c:c8ff:fe02:baba/64 scope link 
       valid_lft forever preferred_lft forever
171: veth62a4919@if170: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master br-1272e8efd44d state UP group default 
    link/ether de:cb:76:46:f1:da brd ff:ff:ff:ff:ff:ff link-netnsid 1
    inet6 fe80::dccb:76ff:fe46:f1da/64 scope link 
       valid_lft forever preferred_lft forever
173: veth3e745c8@if172: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master br-1272e8efd44d state UP group default 
    link/ether ee:e6:60:fd:c5:45 brd ff:ff:ff:ff:ff:ff link-netnsid 2
    inet6 fe80::ece6:60ff:fefd:c545/64 scope link 
       valid_lft forever preferred_lft forever
175: veth629784a@if174: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master br-1272e8efd44d state UP group default 
    link/ether 36:94:fc:6a:76:dd brd ff:ff:ff:ff:ff:ff link-netnsid 3
    inet6 fe80::3494:fcff:fe6a:76dd/64 scope link 
       valid_lft forever preferred_lft forever
177: vethc9bba02@if176: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master br-1272e8efd44d state UP group default 
    link/ether ba:a5:93:72:74:01 brd ff:ff:ff:ff:ff:ff link-netnsid 4
    inet6 fe80::b8a5:93ff:fe72:7401/64 scope link 
       valid_lft forever preferred_lft forever
179: veth76ae783@if178: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master br-1272e8efd44d state UP group default 
    link/ether 0e:cc:77:6d:25:a4 brd ff:ff:ff:ff:ff:ff link-netnsid 5
    inet6 fe80::ccc:77ff:fe6d:25a4/64 scope link 
       valid_lft forever preferred_lft forever
181: veth72a8481@if180: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master br-1272e8efd44d state UP group default 
    link/ether be:36:99:d3:1b:c5 brd ff:ff:ff:ff:ff:ff link-netnsid 6
    inet6 fe80::bc36:99ff:fed3:1bc5/64 scope link 
       valid_lft forever preferred_lft forever
183: veth76b395f@if182: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master br-1272e8efd44d state UP group default 
    link/ether 66:ba:53:5c:f2:ec brd ff:ff:ff:ff:ff:ff link-netnsid 7
    inet6 fe80::64ba:53ff:fe5c:f2ec/64 scope link 
       valid_lft forever preferred_lft forever
185: vethbc02c13@if184: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master br-1272e8efd44d state UP group default 
    link/ether 46:24:af:ef:a1:be brd ff:ff:ff:ff:ff:ff link-netnsid 8
    inet6 fe80::4424:afff:feef:a1be/64 scope link 
       valid_lft forever preferred_lft forever
200: enx1065300854a4: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc pfifo_fast state DOWN group default qlen 1000
    link/ether 10:65:30:08:54:a4 brd ff:ff:ff:ff:ff:ff
214: veth245c75e@if213: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue master br-1272e8efd44d state UP group default 
    link/ether 32:93:c3:39:00:5c brd ff:ff:ff:ff:ff:ff link-netnsid 9
    inet6 fe80::3093:c3ff:fe39:5c/64 scope link 
       valid_lft forever preferred_lft forever

'''


class HDMock(LocalInfoMockMixin, HDCommand):
    RAW_DATA = \
        '''Filesystem                    Type     1K-blocks     Avail Mounted on
udev                          devtmpfs   8052604   8052604 /dev
tmpfs                         tmpfs      1613840   1602864 /run
/dev/mapper/schwartz--vg-root ext4     966459980 687188796 /
tmpfs                         tmpfs      8069188   7958760 /dev/shm
tmpfs                         tmpfs         5120      5116 /run/lock
tmpfs                         tmpfs      8069188   8069188 /sys/fs/cgroup
/dev/nvme0n1p2                ext2        241965    140280 /boot
/dev/nvme0n1p1                vfat        523248    501584 /boot/efi
tmpfs                         tmpfs      1613836   1603052 /run/user/1000
'''


class VersionMock(LocalInfoMockMixin, VersionCommand):
    RAW_DATA = '''Linux schwartz 4.18.0-3-amd64 #1 SMP Debian 4.18.20-2 (2018-11-23) x86_64 GNU/Linux'''


class DistroMock(LocalInfoMockMixin, DistroCommand):
    RAW_DATA = \
        '''No LSB modules are available.
Distributor ID:	Debian
Description:	Debian GNU/Linux buster/sid
Release:	testing
Codename:	buster
'''


class MemMock(LocalInfoMockMixin, MemCommand):
    RAW_DATA = \
        '''
MemTotal:       16138376 kB
MemFree:          395340 kB
MemAvailable:    7541676 kB
Buffers:         1134104 kB
Cached:          5573980 kB
SwapCached:           68 kB
Active:          8516488 kB
Inactive:        5342492 kB
Active(anon):    6168832 kB
Inactive(anon):  1552612 kB
Active(file):    2347656 kB
Inactive(file):  3789880 kB
Unevictable:         116 kB
Mlocked:             116 kB
SwapTotal:      16486396 kB
SwapFree:       16483068 kB
Dirty:              1828 kB
Writeback:             0 kB
AnonPages:       6214108 kB
Mapped:           899516 kB
Shmem:            570552 kB
Slab:            1592784 kB
SReclaimable:    1345904 kB
SUnreclaim:       246880 kB
KernelStack:       61136 kB
PageTables:        72144 kB
NFS_Unstable:          0 kB
Bounce:                0 kB
WritebackTmp:          0 kB
CommitLimit:    24555584 kB
Committed_AS:   34505916 kB
VmallocTotal:   34359738367 kB
VmallocUsed:           0 kB
VmallocChunk:          0 kB
HardwareCorrupted:     0 kB
AnonHugePages:   1282048 kB
ShmemHugePages:        0 kB
ShmemPmdMapped:        0 kB
HugePages_Total:       0
HugePages_Free:        0
HugePages_Rsvd:        0
HugePages_Surp:        0
Hugepagesize:       2048 kB
Hugetlb:               0 kB
DirectMap4k:      517072 kB
DirectMap2M:    14919680 kB
DirectMap1G:     1048576 kB
'''


class DPKGMock(LocalInfoMockMixin, DPKGCommand):
    RAW_DATA = \
        '''Desired=Unknown/Install/Remove/Purge/Hold
| Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/trig-aWait/Trig-pend
|/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)
||/ Name                                                        Version                               Architecture Description
+++-===========================================================-=====================================-============-===================================================================================
ii  accountsservice                                             0.6.45-1                              amd64        query and manipulate user account information
ii  acl                                                         2.2.52-3+b1                           amd64        Access control list utilities
ii  adduser                                                     3.118                                 all          add and remove users and groups
ii  adwaita-icon-theme                                          3.30.0-1                              all          default icon theme of GNOME
ii  aeson-pretty                                                0.8.7-3                               amd64        JSON pretty-printing tool
ii  aisleriot                                                   1:3.22.7-1                            amd64        GNOME solitaire card game collection
ii  alsa-utils                                                  1.1.7-1                               amd64        Utilities for configuring and using ALSA
ii  anacron                                                     2.3-26                                amd64        cron-like program that doesn't go by time
ii  apache2-bin                                                 2.4.37-1                              amd64        Apache HTTP Server (modules and other binary files)
ii  apg                                                         2.2.3.dfsg.1-5                        amd64        Automated Password Generator - Standalone version
ii  apparmor                                                    2.13.1-3+b1                           amd64        user-space parser utility for AppArmor
'''


class UsersMock(LocalInfoMockMixin, UsersCommand):
    RAW_DATA = \
        '''root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin
sync:x:4:65534:sync:/bin:/bin/sync
games:x:5:60:games:/usr/games:/usr/sbin/nologin
man:x:6:12:man:/var/cache/man:/usr/sbin/nologin
lp:x:7:7:lp:/var/spool/lpd:/usr/sbin/nologin
mail:x:8:8:mail:/var/mail:/usr/sbin/nologin
news:x:9:9:news:/var/spool/news:/usr/sbin/nologin
uucp:x:10:10:uucp:/var/spool/uucp:/usr/sbin/nologin
proxy:x:13:13:proxy:/bin:/usr/sbin/nologin
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
backup:x:34:34:backup:/var/backups:/usr/sbin/nologin
list:x:38:38:Mailing List Manager:/var/list:/usr/sbin/nologin
irc:x:39:39:ircd:/var/run/ircd:/usr/sbin/nologin
gnats:x:41:41:Gnats Bug-Reporting System (admin):/var/lib/gnats:/usr/sbin/nologin
nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin
_apt:x:100:65534::/nonexistent:/usr/sbin/nologin
systemd-network:x:101:102:systemd Network Management,,,:/run/systemd/netif:/usr/sbin/nologin
systemd-resolve:x:102:103:systemd Resolver,,,:/run/systemd/resolve:/usr/sbin/nologin
dnsmasq:x:103:65534:dnsmasq,,,:/var/lib/misc:/usr/sbin/nologin
avahi-autoipd:x:104:107:Avahi autoip daemon,,,:/var/lib/avahi-autoipd:/usr/sbin/nologin
messagebus:x:105:108::/nonexistent:/usr/sbin/nologin
usbmux:x:106:46:usbmux daemon,,,:/var/lib/usbmux:/usr/sbin/nologin
rtkit:x:107:112:RealtimeKit,,,:/proc:/usr/sbin/nologin
geoclue:x:108:115::/var/lib/geoclue:/usr/sbin/nologin
sshd:x:109:65534::/run/sshd:/usr/sbin/nologin
colord:x:110:117:colord colour management daemon,,,:/var/lib/colord:/usr/sbin/nologin
saned:x:111:118::/var/lib/saned:/usr/sbin/nologin
speech-dispatcher:x:112:29:Speech Dispatcher,,,:/var/run/speech-dispatcher:/bin/false
avahi:x:113:119:Avahi mDNS daemon,,,:/var/run/avahi-daemon:/usr/sbin/nologin
pulse:x:114:120:PulseAudio daemon,,,:/var/run/pulse:/usr/sbin/nologin
hplip:x:115:7:HPLIP system user,,,:/var/run/hplip:/bin/false
Debian-gdm:x:116:122:Gnome Display Manager:/var/lib/gdm3:/bin/false
user:x:1000:1000:user,,,:/home/user:/bin/bash
libvirt-qemu:x:64055:124:Libvirt Qemu,,,:/var/lib/libvirt:/usr/sbin/nologin
Debian-exim:x:117:127::/var/spool/exim4:/usr/sbin/nologin
strongswan:x:118:65534::/var/lib/strongswan:/usr/sbin/nologin
uuidd:x:119:128::/run/uuidd:/usr/sbin/nologin
systemd-coredump:x:997:997:systemd Core Dumper:/:/sbin/nologin
debian-tor:x:120:130::/var/lib/tor:/bin/false
festival:x:121:29::/nonexistent:/usr/sbin/nologin
systemd-timesync:x:122:131:systemd Time Synchronization,,,:/run/systemd:/usr/sbin/nologin
'''
