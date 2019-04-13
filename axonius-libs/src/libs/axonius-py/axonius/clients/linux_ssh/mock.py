
# pylint: disable=wildcard-import,too-many-lines
from axonius.clients.linux_ssh.data import *


# pylint: disable=trailing-whitespace,line-too-long,
class LocalInfoMockMixin:
    RAW_DATA = None

    def shell_execute(self, execute_callback: Callable[[str], str] = None, password: str = None):
        self._raw_data = self.START_MAGIC + self.RAW_DATA + self.END_MAGIC


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
        '''Filesystem                    Type     1K-blocks      Used Available Use% Mounted on
udev                          devtmpfs   8051388         0   8051388   0% /dev
tmpfs                         tmpfs      1613668    116772   1496896   8% /run
/dev/mapper/schwartz--vg-root ext4     966459980 342465344 574831372  38% /
tmpfs                         tmpfs      8068328    110000   7958328   2% /dev/shm
tmpfs                         tmpfs         5120         4      5116   1% /run/lock
tmpfs                         tmpfs      8068328         0   8068328   0% /sys/fs/cgroup
/dev/nvme0n1p2                ext2        241965     90191    139282  40% /boot
/dev/nvme0n1p1                vfat        523248     21664    501584   5% /boot/efi
tmpfs                         tmpfs      1613664     11952   1601712   1% /run/user/1000'''


class VersionMock(LocalInfoMockMixin, VersionCommand):
    RAW_DATA = '''Linux schwartz 4.18.0-3-amd64 #1 SMP Debian 4.18.20-2 (2018-11-23) x86_64 GNU/Linux'''


class DebianDistroMock(LocalInfoMockMixin, DebianDistroCommand):
    RAW_DATA = \
        '''No LSB modules are available.
Distributor ID:	Debian
Description:	Debian GNU/Linux buster/sid
Release:	testing
Codename:	buster
'''


class FailDistroMock(LocalInfoMockMixin, DebianDistroCommand):
    RAW_DATA = 'fail'

    def shell_execute(self, execute_callback: Callable[[str], str] = None, password: str = None):
        self._raw_data = self.RAW_DATA


class MD5FilesCommandMock(LocalInfoMockMixin, MD5FilesCommand):
    RAW_DATA = \
        '''
md5sum: 'asdf qwer': No such file or directory
d41d8cd98f00b204e9800998ecf8427e  /tmp/a
md5sum: /tmp/cscope.25365: Is a directory
md5sum: /tmp/: Is a directory
f00d8cd98f00b204e9800998ecf8d16a  /tmp/asdgf
'''


class RedHatDistroMock(LocalInfoMockMixin, RedHatDistroCommand):
    RAW_DATA = \
        '''Red Hat Enterprise Linux Server release 6.10 (Santiago)'''


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


class RPMMock(LocalInfoMockMixin, RPMCommand):
    RAW_DATA = \
        '''ntpdate|4.2.6p5|x86_64|Utility to set the date and time via NTP|Red Hat, Inc.
grub2-common|2.02|noarch|grub2 common layout|Red Hat, Inc.
alsa-firmware|1.0.28|noarch|Firmware for several ALSA-supported sound cards|Red Hat, Inc.
setup|2.8.71|noarch|A set of system configuration and setup files|Red Hat, Inc.
teamd|1.27|x86_64|Team network device control daemon|Red Hat, Inc.
dbus-python|1.1.1|x86_64|D-Bus Python Bindings|Red Hat, Inc.
grub2-pc-modules|2.02|noarch|Modules used to build custom grub images|Red Hat, Inc.
python-firewall|0.5.3|noarch|Python2 bindings for firewalld|Red Hat, Inc.
emacs-filesystem|24.3|noarch|Emacs filesystem layout|Red Hat, Inc.
plymouth-core-libs|0.8.9|x86_64|Plymouth core libraries|Red Hat, Inc.
firewalld-filesystem|0.5.3|noarch|Firewalld directory layout and rpm macros|Red Hat, Inc.
plymouth|0.8.9|x86_64|Graphical Boot Animation and Logger|Red Hat, Inc.
glibc-common|2.17|x86_64|Common binaries and locale data for glibc|Red Hat, Inc.
python-pycurl|7.19.0|x86_64|A Python interface to libcurl|Red Hat, Inc.
glibc|2.17|x86_64|The GNU libc libraries|Red Hat, Inc.
mariadb-libs|5.5.60|x86_64|The shared libraries required for MariaDB/MySQL clients|Red Hat, Inc.
nss-util|3.36.0|x86_64|Network Security Services Utilities Library|Red Hat, Inc.
gnupg2|2.0.22|x86_64|Utility for secure communication and data storage|Red Hat, Inc.
ncurses-libs|5.9|x86_64|Ncurses libraries|Red Hat, Inc.
rpm-python|4.11.3|x86_64|Python bindings for apps which will manipulate RPM packages|Red Hat, Inc.
libsepol|2.5|x86_64|SELinux binary policy manipulation library|Red Hat, Inc.
gpgme|1.3.2|x86_64|GnuPG Made Easy - high level crypto API|Red Hat, Inc.
libselinux|2.5|x86_64|SELinux library and simple utilities|Red Hat, Inc.'''


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


class HardwareMock(LocalInfoMockMixin, HardwareCommand):
    RAW_DATA = \
        '''
        # dmidecode 3.2
Getting SMBIOS data from sysfs.
SMBIOS 3.0.0 present.
Table at 0x000E0000.

Handle 0x0000, DMI type 0, 24 bytes
BIOS Information
	Vendor: Dell Inc.
	Version: 1.6.3
	Release Date: 11/04/2018
	Address: 0xF0000
	Runtime Size: 64 kB
	ROM Size: 16 MB
	Characteristics:
		PCI is supported
		PNP is supported
		BIOS is upgradeable
		BIOS shadowing is allowed
		Boot from CD is supported
		Selectable boot is supported
		EDD is supported
		Japanese floppy for NEC 9800 1.2 MB is supported (int 13h)
		5.25"/1.2 MB floppy services are supported (int 13h)
		3.5"/720 kB floppy services are supported (int 13h)
		3.5"/2.88 MB floppy services are supported (int 13h)
		Print screen service is supported (int 5h)
		8042 keyboard services are supported (int 9h)
		Serial services are supported (int 14h)
		Printer services are supported (int 17h)
		ACPI is supported
		USB legacy is supported
		Smart battery is supported
		BIOS boot specification is supported
		Function key-initiated network boot is supported
		Targeted content distribution is supported
		UEFI is supported
	BIOS Revision: 1.6

Handle 0x0001, DMI type 1, 27 bytes
System Information
	Manufacturer: Dell Inc.
	Product Name: XPS 13 9370
	Version: Not Specified
	Serial Number: 9T1MZM2
	UUID: 4c4c4544-0054-3110-804d-b9c04f5a4d32
	Wake-up Type: Power Switch
	SKU Number: 07E6
	Family: XPS

Handle 0x0002, DMI type 2, 15 bytes
Base Board Information
	Manufacturer: Dell Inc.
	Product Name: 0F6P3V
	Version: A00
	Serial Number: /9T1MZM2/CN1296382N004C/
	Asset Tag: Not Specified
	Features:
		Board is a hosting board
		Board is replaceable
	Location In Chassis: Not Specified
	Chassis Handle: 0x0003
	Type: Motherboard
	Contained Object Handles: 0

Handle 0x0003, DMI type 3, 22 bytes
Chassis Information
	Manufacturer: Dell Inc.
	Type: Notebook
	Lock: Not Present
	Version: Not Specified
	Serial Number: 9T1MZM2
	Asset Tag: Not Specified
	Boot-up State: Safe
	Power Supply State: Safe
	Thermal State: Safe
	Security Status: None
	OEM Information: 0x00000000
	Height: Unspecified
	Number Of Power Cords: 1
	Contained Elements: 0
	SKU Number: Notebook

Handle 0x0004, DMI type 8, 9 bytes
Port Connector Information
	Internal Reference Designator: JUSB1
	Internal Connector Type: None
	External Reference Designator: USB1
	External Connector Type: Access Bus (USB)
	Port Type: USB

Handle 0x0005, DMI type 8, 9 bytes
Port Connector Information
	Internal Reference Designator: JUSB2
	Internal Connector Type: None
	External Reference Designator: USB2
	External Connector Type: Access Bus (USB)
	Port Type: USB

Handle 0x0006, DMI type 8, 9 bytes
Port Connector Information
	Internal Reference Designator: JSD1
	Internal Connector Type: None
	External Reference Designator: Cardreader
	External Connector Type: Other
	Port Type: None

Handle 0x0007, DMI type 8, 9 bytes
Port Connector Information
	Internal Reference Designator: JHP1
	Internal Connector Type: None
	External Reference Designator: Audio Jack
	External Connector Type: Mini Jack (headphones)
	Port Type: Audio Port

Handle 0x0008, DMI type 8, 9 bytes
Port Connector Information
	Internal Reference Designator: JTypeC
	Internal Connector Type: None
	External Reference Designator: USB3
	External Connector Type: Access Bus (USB)
	Port Type: USB

Handle 0x0009, DMI type 8, 9 bytes
Port Connector Information
	Internal Reference Designator: JeDP1 - eDP
	Internal Connector Type: None
	External Reference Designator: Not Specified
	External Connector Type: None
	Port Type: Other

Handle 0x000A, DMI type 8, 9 bytes
Port Connector Information
	Internal Reference Designator: JNGFF1 - WLAN/BT/Wigig CONN
	Internal Connector Type: None
	External Reference Designator: Not Specified
	External Connector Type: None
	Port Type: Other

Handle 0x000B, DMI type 8, 9 bytes
Port Connector Information
	Internal Reference Designator: JNGFF2 - HDD
	Internal Connector Type: None
	External Reference Designator: Not Specified
	External Connector Type: None
	Port Type: Other

Handle 0x000C, DMI type 8, 9 bytes
Port Connector Information
	Internal Reference Designator: JKBTP1 - Keyboard
	Internal Connector Type: None
	External Reference Designator: Not Specified
	External Connector Type: None
	Port Type: Keyboard Port

Handle 0x000D, DMI type 8, 9 bytes
Port Connector Information
	Internal Reference Designator: JFAN1 - CPU FAN
	Internal Connector Type: None
	External Reference Designator: Not Specified
	External Connector Type: None
	Port Type: Other

Handle 0x000E, DMI type 8, 9 bytes
Port Connector Information
	Internal Reference Designator: JSPK1 - Speaker
	Internal Connector Type: Mini Jack (headphones)
	External Reference Designator: Not Specified
	External Connector Type: None
	Port Type: Audio Port

Handle 0x000F, DMI type 8, 9 bytes
Port Connector Information
	Internal Reference Designator: JXDP1 - CPU XDP Port
	Internal Connector Type: None
	External Reference Designator: Not Specified
	External Connector Type: None
	Port Type: Other

Handle 0x0010, DMI type 8, 9 bytes
Port Connector Information
	Internal Reference Designator: JAPS1 - Automatic Power
	Internal Connector Type: None
	External Reference Designator: Not Specified
	External Connector Type: None
	Port Type: Other

Handle 0x0011, DMI type 8, 9 bytes
Port Connector Information
	Internal Reference Designator: JLPDE1 - 80 PORT
	Internal Connector Type: None
	External Reference Designator: Not Specified
	External Connector Type: None
	Port Type: Other

Handle 0x0012, DMI type 8, 9 bytes
Port Connector Information
	Internal Reference Designator: JDEG1 - Debug PORT
	Internal Connector Type: None
	External Reference Designator: Not Specified
	External Connector Type: None
	Port Type: Other

Handle 0x0013, DMI type 8, 9 bytes
Port Connector Information
	Internal Reference Designator: JRTC1 - RTC
	Internal Connector Type: None
	External Reference Designator: Not Specified
	External Connector Type: None
	Port Type: Other

Handle 0x0014, DMI type 9, 17 bytes
System Slot Information
	Designation: Slot1
	Type: x1 PCI Express
	Current Usage: In Use
	Length: Long
	ID: 0
	Characteristics:
		3.3 V is provided
		Opening is shared
		PME signal is supported
	Bus Address: 0000:00:1c.0

Handle 0x0015, DMI type 9, 17 bytes
System Slot Information
	Designation: Slot2
	Type: x1 PCI Express
	Current Usage: Available
	Length: Short
	ID: 1
	Characteristics:
		3.3 V is provided
		Opening is shared
		PME signal is supported
	Bus Address: 0000:00:1c.1

Handle 0x0016, DMI type 9, 17 bytes
System Slot Information
	Designation: Slot3
	Type: x1 PCI Express
	Current Usage: In Use
	Length: Short
	ID: 2
	Characteristics:
		3.3 V is provided
		Opening is shared
		PME signal is supported
	Bus Address: 0000:00:1c.2

Handle 0x0017, DMI type 9, 17 bytes
System Slot Information
	Designation: Slot4
	Type: x1 PCI Express
	Current Usage: Available
	Length: Short
	ID: 3
	Characteristics:
		3.3 V is provided
		Opening is shared
		PME signal is supported
	Bus Address: 0000:00:1c.3

Handle 0x001C, DMI type 9, 17 bytes
System Slot Information
	Designation: Slot9
	Type: x1 PCI Express
	Current Usage: In Use
	Length: Short
	ID: 8
	Characteristics:
		3.3 V is provided
		Opening is shared
		PME signal is supported
	Bus Address: 0000:00:1d.0

Handle 0x001D, DMI type 9, 17 bytes
System Slot Information
	Designation: Slot10
	Type: x1 PCI Express
	Current Usage: Available
	Length: Short
	ID: 9
	Characteristics:
		3.3 V is provided
		Opening is shared
		PME signal is supported
	Bus Address: 0000:00:1d.1

Handle 0x001E, DMI type 9, 17 bytes
System Slot Information
	Designation: Slot11
	Type: x1 PCI Express
	Current Usage: Available
	Length: Short
	ID: 10
	Characteristics:
		3.3 V is provided
		Opening is shared
		PME signal is supported
	Bus Address: 0000:00:1d.2

Handle 0x001F, DMI type 9, 17 bytes
System Slot Information
	Designation: Slot12
	Type: x1 PCI Express
	Current Usage: Available
	Length: Short
	ID: 11
	Characteristics:
		3.3 V is provided
		Opening is shared
		PME signal is supported
	Bus Address: 0000:00:1d.3

Handle 0x0020, DMI type 10, 6 bytes
On Board Device Information
	Type: Video
	Status: Enabled
	Description: "Intel HD Graphics"

Handle 0x0021, DMI type 11, 5 bytes
OEM Strings
	String 1: Dell System
	String 2: 1[07E6]
	String 3: 3[1.0]
	String 4: 12[www.dell.com]
	String 5: 14[1]
	String 6: 15[0]
	String 7: 27[21347312330]

Handle 0x0022, DMI type 12, 5 bytes
System Configuration Options
	Option 1: Default string

Handle 0x0023, DMI type 15, 35 bytes
System Event Log
	Area Length: 4 bytes
	Header Start Offset: 0x0000
	Header Length: 2 bytes
	Data Start Offset: 0x0002
	Access Method: Indexed I/O, one 16-bit index port, one 8-bit data port
	Access Address: Index 0x046A, Data 0x046C
	Status: Invalid, Not Full
	Change Token: 0x00000000
	Header Format: No Header
	Supported Log Type Descriptors: 6
	Descriptor 1: End of log
	Data Format 1: OEM-specific
	Descriptor 2: End of log
	Data Format 2: OEM-specific
	Descriptor 3: End of log
	Data Format 3: OEM-specific
	Descriptor 4: End of log
	Data Format 4: OEM-specific
	Descriptor 5: End of log
	Data Format 5: OEM-specific
	Descriptor 6: End of log
	Data Format 6: OEM-specific

Handle 0x0024, DMI type 21, 7 bytes
Built-in Pointing Device
	Type: Touch Pad
	Interface: Bus Mouse
	Buttons: 2

Handle 0x0029, DMI type 25, 9 bytes
	System Power Controls
	Next Scheduled Power-on: *-* 00:00:00

Handle 0x002A, DMI type 32, 20 bytes
System Boot Information
	Status: No errors detected

Handle 0x002B, DMI type 34, 11 bytes
Management Device
	Description: LM78-1
	Type: LM78
	Address: 0x00000000
	Address Type: I/O Port

Handle 0x002D, DMI type 36, 16 bytes
Management Device Threshold Data
	Lower Non-critical Threshold: 1
	Upper Non-critical Threshold: 2
	Lower Critical Threshold: 3
	Upper Critical Threshold: 4
	Lower Non-recoverable Threshold: 5
	Upper Non-recoverable Threshold: 6

Handle 0x002F, DMI type 36, 16 bytes
Management Device Threshold Data
	Lower Non-critical Threshold: 1
	Upper Non-critical Threshold: 2
	Lower Critical Threshold: 3
	Upper Critical Threshold: 4
	Lower Non-recoverable Threshold: 5
	Upper Non-recoverable Threshold: 6

Handle 0x0031, DMI type 36, 16 bytes
Management Device Threshold Data

Handle 0x0037, DMI type 41, 11 bytes
Onboard Device
	Reference Designation:  Onboard IGD
	Type: Video
	Status: Enabled
	Type Instance: 1
	Bus Address: 0000:00:02.0

Handle 0x0038, DMI type 41, 11 bytes
Onboard Device
	Reference Designation:  Onboard LAN
	Type: Ethernet
	Status: Enabled
	Type Instance: 1
	Bus Address: 0000:00:19.0

Handle 0x0039, DMI type 41, 11 bytes
Onboard Device
	Reference Designation:  Onboard 1394
	Type: Other
	Status: Enabled
	Type Instance: 1
	Bus Address: 0000:03:1c.2

Handle 0x003A, DMI type 248, 9 bytes
OEM-specific Type
	Header and Data:
		F8 09 3A 00 00 00 00 00 01
	Strings:
		BDF_RV_0520

Handle 0x003B, DMI type 255, 8 bytes
OEM-specific Type
	Header and Data:
		FF 08 3B 00 01 02 00 00
	Strings:
		_SIDUSaL3N11zIiI
		07E6
		_SIDAvf90w7wKZiZ
		DELL

Handle 0x003C, DMI type 16, 23 bytes
Physical Memory Array
	Location: System Board Or Motherboard
	Use: System Memory
	Error Correction Type: None
	Maximum Capacity: 16 GB
	Error Information Handle: Not Provided
	Number Of Devices: 2

Handle 0x003D, DMI type 17, 40 bytes
Memory Device
	Array Handle: 0x003C
	Error Information Handle: Not Provided
	Total Width: 64 bits
	Data Width: 64 bits
	Size: 8192 MB
	Form Factor: Row Of Chips
	Set: None
	Locator: System Board Memory
	Bank Locator: Not Specified
	Type: LPDDR3
	Type Detail: Synchronous Unbuffered (Unregistered)
	Speed: 2133 MT/s
	Manufacturer: SK Hynix
	Serial Number: Not Specified
	Asset Tag: Not Specified
	Part Number: H9CCNNNCLGALAR-NVD
	Rank: 2
	Configured Memory Speed: 2133 MT/s
	Minimum Voltage: 1.25 V
	Maximum Voltage: 1.25 V
	Configured Voltage: 1.2 V

Handle 0x003E, DMI type 17, 40 bytes
Memory Device
	Array Handle: 0x003C
	Error Information Handle: Not Provided
	Total Width: 64 bits
	Data Width: 64 bits
	Size: 8192 MB
	Form Factor: Row Of Chips
	Set: None
	Locator: System Board Memory
	Bank Locator: Not Specified
	Type: LPDDR3
	Type Detail: Synchronous Unbuffered (Unregistered)
	Speed: 2133 MT/s
	Manufacturer: SK Hynix
	Serial Number: Not Specified
	Asset Tag: Not Specified
	Part Number: H9CCNNNCLGALAR-NVD
	Rank: 2
	Configured Memory Speed: 2133 MT/s
	Minimum Voltage: 1.25 V
	Maximum Voltage: 1.25 V
	Configured Voltage: 1.2 V

Handle 0x003F, DMI type 19, 31 bytes
Memory Array Mapped Address
	Starting Address: 0x00000000000
	Ending Address: 0x003FFFFFFFF
	Range Size: 16 GB
	Physical Array Handle: 0x003C
	Partition Width: 2

Handle 0x0040, DMI type 7, 19 bytes
Cache Information
	Socket Designation: L1 Cache
	Configuration: Enabled, Not Socketed, Level 1
	Operational Mode: Write Back
	Location: Internal
	Installed Size: 256 kB
	Maximum Size: 256 kB
	Supported SRAM Types:
		Synchronous
	Installed SRAM Type: Synchronous
	Speed: Unknown
	Error Correction Type: Parity
	System Type: Unified
	Associativity: 8-way Set-associative

Handle 0x0041, DMI type 7, 19 bytes
Cache Information
	Socket Designation: L2 Cache
	Configuration: Enabled, Not Socketed, Level 2
	Operational Mode: Write Back
	Location: Internal
	Installed Size: 1024 kB
	Maximum Size: 1024 kB
	Supported SRAM Types:
		Synchronous
	Installed SRAM Type: Synchronous
	Speed: Unknown
	Error Correction Type: Single-bit ECC
	System Type: Unified
	Associativity: 4-way Set-associative

Handle 0x0042, DMI type 7, 19 bytes
Cache Information
	Socket Designation: L3 Cache
	Configuration: Enabled, Not Socketed, Level 3
	Operational Mode: Write Back
	Location: Internal
	Installed Size: 8192 kB
	Maximum Size: 8192 kB
	Supported SRAM Types:
		Synchronous
	Installed SRAM Type: Synchronous
	Speed: Unknown
	Error Correction Type: Multi-bit ECC
	System Type: Unified
	Associativity: 16-way Set-associative

Handle 0x0043, DMI type 4, 48 bytes
Processor Information
	Socket Designation: U3E1
	Type: Central Processor
	Family: Core i7
	Manufacturer: Intel(R) Corporation
	ID: EA 06 08 00 FF FB EB BF
	Signature: Type 0, Family 6, Model 142, Stepping 10
	Flags:
		FPU (Floating-point unit on-chip)
		VME (Virtual mode extension)
		DE (Debugging extension)
		PSE (Page size extension)
		TSC (Time stamp counter)
		MSR (Model specific registers)
		PAE (Physical address extension)
		MCE (Machine check exception)
		CX8 (CMPXCHG8 instruction supported)
		APIC (On-chip APIC hardware supported)
		SEP (Fast system call)
		MTRR (Memory type range registers)
		PGE (Page global enable)
		MCA (Machine check architecture)
		CMOV (Conditional move instruction supported)
		PAT (Page attribute table)
		PSE-36 (36-bit page size extension)
		CLFSH (CLFLUSH instruction supported)
		DS (Debug store)
		ACPI (ACPI supported)
		MMX (MMX technology supported)
		FXSR (FXSAVE and FXSTOR instructions supported)
		SSE (Streaming SIMD extensions)
		SSE2 (Streaming SIMD extensions 2)
		SS (Self-snoop)
		HTT (Multi-threading)
		TM (Thermal monitor supported)
		PBE (Pending break enabled)
	Version: Intel(R) Core(TM) i7-8550U CPU @ 1.80GHz
	Voltage: 1.1 V
	External Clock: 100 MHz
	Max Speed: 1800 MHz
	Current Speed: 3700 MHz
	Status: Populated, Enabled
	Upgrade: Socket BGA1356
	L1 Cache Handle: 0x0040
	L2 Cache Handle: 0x0041
	L3 Cache Handle: 0x0042
	Serial Number: To Be Filled By O.E.M.
	Asset Tag: To Be Filled By O.E.M.
	Part Number: To Be Filled By O.E.M.
	Core Count: 4
	Core Enabled: 4
	Thread Count: 8
	Characteristics:
		64-bit capable
		Multi-Core
		Hardware Thread
		Execute Protection
		Enhanced Virtualization
		Power/Performance Control

Handle 0x0044, DMI type 20, 35 bytes
Memory Device Mapped Address
	Starting Address: 0x00000000000
	Ending Address: 0x001FFFFFFFF
	Range Size: 8 GB
	Physical Device Handle: 0x003D
	Memory Array Mapped Address Handle: 0x003F
	Partition Row Position: 1
	Interleave Position: 1
	Interleaved Data Depth: 1

Handle 0x0045, DMI type 20, 35 bytes
Memory Device Mapped Address
	Starting Address: 0x00200000000
	Ending Address: 0x003FFFFFFFF
	Range Size: 8 GB
	Physical Device Handle: 0x003E
	Memory Array Mapped Address Handle: 0x003F
	Partition Row Position: 1
	Interleave Position: 2
	Interleaved Data Depth: 1

Handle 0x0300, DMI type 126, 22 bytes
Inactive

Handle 0x1600, DMI type 22, 26 bytes
Portable Battery
	Location: Sys. Battery Bay
	Manufacturer: SMP
	Manufacture Date: 01/26/2018
	Serial Number: 035A
	Name: DELL G8VCF6C
	Design Capacity: 51990 mWh
	Design Voltage: 7600 mV
	SBDS Version: 1.0
	Maximum Error: 6%
	SBDS Chemistry: LiP
	OEM-specific Information: 0x00000801

Handle 0x1604, DMI type 43, 31 bytes
TPM Device
	Vendor ID:
	Specification Version: 2.0	Firmware Revision: 7.2
	Description: NUVOTON	Characteristics:
		Family configurable via platform software support
	OEM-specific Information: 0x00000000

Handle 0x1B00, DMI type 27, 15 bytes
Cooling Device
	Temperature Probe Handle: 0x1C00
	Type: Chip Fan
	Status: OK
	OEM-specific Information: 0x0000DD00
	Nominal Speed: 6000 rpm
	Description: CPU Fan

Handle 0x1C00, DMI type 28, 22 bytes
Temperature Probe
	Description: CPU Probe
	Location: Motherboard
	Status: OK
	Maximum Value: 127.0 deg C
	Minimum Value: -127.0 deg C
	Resolution: 1.000 deg C
	Tolerance: Unknown
	Accuracy: Unknown
	OEM-specific Information: 0x0000DC00
	Nominal Value: 10.0 deg C

Handle 0x1C01, DMI type 28, 22 bytes
Temperature Probe
	Description: True Ambient
	Location: Motherboard
	Status: OK
	Maximum Value: 127.0 deg C
	Minimum Value: -127.0 deg C
	Resolution: 1.000 deg C
	Tolerance: Unknown
	Accuracy: Unknown
	OEM-specific Information: 0x0000DC01
	Nominal Value: 10.0 deg C

Handle 0x1C02, DMI type 28, 22 bytes
Temperature Probe
	Description: Memory Module
	Location: Motherboard
	Status: OK
	Maximum Value: 127.0 deg C
	Minimum Value: -127.0 deg C
	Resolution: 1.000 deg C
	Tolerance: Unknown
	Accuracy: Unknown
	OEM-specific Information: 0x0000DC02
	Nominal Value: 10.0 deg C

Handle 0x1C03, DMI type 28, 22 bytes
Temperature Probe
	Description: Other Probe
	Location: Processor
	Status: OK
	Maximum Value: 127.0 deg C
	Minimum Value: -127.0 deg C
	Resolution: 1.000 deg C
	Tolerance: Unknown
	Accuracy: Unknown
	OEM-specific Information: 0x0000DC03
	Nominal Value: 10.0 deg C

Handle 0xB100, DMI type 177, 12 bytes
OEM-specific Type
	Header and Data:
		B1 0C 00 B1 1A 00 00 00 00 00 00 00

Handle 0xB200, DMI type 178, 84 bytes
OEM-specific Type
	Header and Data:
		B2 54 00 B2 3D 00 0C 00 3C 00 0A 00 3B 00 0B 00
		0A 01 12 00 52 00 20 00 42 00 18 00 48 00 14 00
		50 00 13 00 10 00 FF 00 11 00 FF 00 12 00 FF 00
		13 00 FF 00 14 00 FF 00 1E 00 FF 00 1F 00 FF 00
		20 00 FF 00 21 00 FF 00 22 00 FF 00 50 01 26 00
		44 00 16 00
	Strings:


Handle 0xD000, DMI type 208, 16 bytes
OEM-specific Type
	Header and Data:
		D0 10 00 D0 03 0A FE 00 E6 07 01 02 00 00 00 00
	Strings:
		20180222
		20180320

Handle 0xD800, DMI type 216, 9 bytes
OEM-specific Type
	Header and Data:
		D8 09 00 D8 01 02 01 88 00
	Strings:
		"Intel Corp."
		"1049"

Handle 0xD900, DMI type 217, 8 bytes
OEM-specific Type
	Header and Data:
		D9 08 00 D9 01 02 01 03
	Strings:
		US-101
		Proprietary

Handle 0xDA00, DMI type 218, 251 bytes
OEM-specific Type
	Header and Data:
		DA FB 00 DA B2 00 04 FF 1F B6 40 1E 00 1E 00 00
		00 22 00 22 00 01 00 23 00 23 00 00 00 28 00 28
		00 00 00 29 00 29 00 01 00 2A 00 2A 00 02 00 2B
		00 2B 00 FF FF 2C 00 2C 00 FF FF 42 00 42 00 01
		00 43 00 43 00 00 00 50 00 50 00 01 00 5C 00 5C
		00 01 00 5D 00 5D 00 00 00 7D 00 7D 00 FF FF 93
		00 93 00 01 00 94 00 94 00 00 00 9B 00 9B 00 01
		00 9C 00 9C 00 00 00 9F 00 9F 00 00 00 A0 00 A0
		00 01 00 A1 00 A1 00 00 00 A3 00 A3 00 01 00 D1
		00 D1 00 01 00 D2 00 D2 00 00 00 EA 00 EA 00 00
		00 EB 00 EB 00 01 00 EC 00 EC 00 02 00 ED 00 ED
		00 00 00 F0 00 F0 00 01 00 09 01 09 01 00 00 0E
		01 0E 01 01 00 0F 01 0F 01 00 00 1B 01 1B 01 00
		00 1C 01 1C 01 01 00 2B 01 2B 01 01 00 2C 01 2C
		01 00 00 2D 01 2D 01 01 00 2E 01 2E 01 00 00 35
		01 35 01 FF 00 FF FF FF FF 00 00

Handle 0xDA01, DMI type 218, 251 bytes
OEM-specific Type
	Header and Data:
		DA FB 01 DA B2 00 04 FF 1F B6 40 38 01 38 01 01
		00 39 01 39 01 02 00 40 01 40 01 00 00 41 01 41
		01 01 00 44 01 44 01 00 00 45 01 45 01 01 00 4A
		01 4A 01 00 00 4B 01 4B 01 01 00 4C 01 4C 01 01
		00 4D 01 4D 01 00 00 52 01 52 01 01 00 53 01 53
		01 00 00 75 01 75 01 02 00 76 01 76 01 01 00 7F
		01 7F 01 00 00 80 01 80 01 01 00 81 01 81 01 00
		00 82 01 82 01 01 00 89 01 89 01 00 00 8A 01 8A
		01 01 00 93 01 93 01 00 00 94 01 94 01 01 00 9B
		01 9B 01 00 00 9C 01 9C 01 01 00 DE 01 DE 01 00
		00 DF 01 DF 01 01 00 E1 01 E1 01 00 00 E8 01 E8
		01 00 00 E9 01 E9 01 01 00 EA 01 EA 01 00 00 EB
		01 EB 01 01 00 02 02 02 02 00 00 03 02 03 02 01
		00 04 02 04 02 00 00 05 02 05 02 01 00 2D 02 2D
		02 01 00 2E 02 2E 02 00 00 32 02 32 02 02 00 33
		02 33 02 01 00 FF FF FF FF 00 00

Handle 0xDA02, DMI type 218, 251 bytes
OEM-specific Type
	Header and Data:
		DA FB 02 DA B2 00 04 FF 1F B6 40 4A 02 4A 02 01
		00 4B 02 4B 02 01 00 4C 02 4C 02 00 00 64 02 64
		02 01 00 65 02 65 02 00 00 66 02 66 02 01 00 67
		02 67 02 00 00 68 02 68 02 01 00 69 02 69 02 00
		00 6C 02 6C 02 01 00 6D 02 6D 02 00 00 6E 02 6E
		02 00 00 85 02 85 02 01 00 86 02 86 02 00 00 94
		02 94 02 01 00 95 02 95 02 00 00 A7 02 A7 02 01
		00 A8 02 A8 02 00 00 BD 02 BD 02 01 00 BE 02 BE
		02 00 00 CD 02 CD 02 01 00 D8 02 D8 02 FF FF D9
		02 D9 02 FF FF DA 02 DA 02 FF FF DB 02 DB 02 FF
		FF DC 02 DC 02 FF FF DD 02 DD 02 FF FF DE 02 DE
		02 FF FF DF 02 DF 02 FF FF E3 02 E3 02 01 00 E4
		02 E4 02 00 00 E5 02 E5 02 01 00 EB 02 EB 02 06
		00 F6 02 F6 02 08 00 12 03 12 03 03 00 13 03 13
		03 01 00 14 03 14 03 00 00 15 03 15 03 01 00 16
		03 16 03 00 00 FF FF FF FF 00 00

Handle 0xDA03, DMI type 218, 251 bytes
OEM-specific Type
	Header and Data:
		DA FB 03 DA B2 00 04 FF 1F B6 40 17 03 17 03 01
		00 18 03 18 03 00 00 19 03 19 03 01 00 1A 03 1A
		03 00 00 1B 03 1B 03 01 00 1C 03 1C 03 00 00 1D
		03 1D 03 01 00 1E 03 1E 03 00 00 1F 03 1F 03 01
		00 20 03 20 03 00 00 25 03 25 03 01 00 26 03 26
		03 01 00 29 03 29 03 01 00 2A 03 2A 03 00 00 2B
		03 2B 03 01 00 2C 03 2C 03 00 00 38 03 38 03 01
		00 39 03 39 03 00 00 41 03 41 03 03 00 42 03 42
		03 04 00 43 03 43 03 05 00 46 03 46 03 01 00 47
		03 47 03 02 00 48 03 48 03 05 00 49 03 49 03 FF
		FF 4A 03 4A 03 FF FF 4D 03 4D 03 01 00 4E 03 4E
		03 00 00 4F 03 4F 03 01 00 50 03 50 03 00 00 57
		03 57 03 00 00 58 03 58 03 01 00 5D 03 5D 03 01
		00 5E 03 5E 03 00 00 5F 03 5F 03 01 00 60 03 60
		03 00 00 61 03 61 03 01 00 62 03 62 03 00 00 66
		03 66 03 00 00 FF FF FF FF 00 00

Handle 0xDA04, DMI type 218, 251 bytes
OEM-specific Type
	Header and Data:
		DA FB 04 DA B2 00 04 FF 1F B6 40 67 03 67 03 01
		00 69 03 69 03 00 00 6A 03 6A 03 01 00 6B 03 6B
		03 02 00 6C 03 6C 03 00 00 6D 03 6D 03 01 00 6E
		03 6E 03 FF FF 74 03 74 03 00 00 75 03 75 03 01
		00 78 03 78 03 01 00 79 03 79 03 00 00 A2 03 A2
		03 01 00 A3 03 A3 03 00 00 A6 03 A6 03 01 00 A7
		03 A7 03 00 00 BE 03 BE 03 FF FF C1 03 C1 03 02
		00 C2 03 C2 03 03 00 C3 03 C3 03 04 00 C5 03 C5
		03 01 00 C6 03 C6 03 00 00 C7 03 C7 03 01 00 C8
		03 C8 03 02 00 C9 03 C9 03 01 00 CA 03 CA 03 00
		00 CB 03 CB 03 FF FF D3 03 D3 03 FF FF D4 03 D4
		03 01 00 D5 03 D5 03 00 00 D6 03 D6 03 01 00 D7
		03 D7 03 00 00 F6 03 F6 03 01 00 F7 03 F7 03 00
		00 FE 03 FE 03 01 00 FF 03 FF 03 00 00 01 04 01
		04 01 00 02 04 02 04 00 00 03 04 03 04 01 00 04
		04 04 04 00 00 FF FF FF FF 00 00

Handle 0xDA05, DMI type 218, 251 bytes
OEM-specific Type
	Header and Data:
		DA FB 05 DA B2 00 04 FF 1F B6 40 1E 04 1E 04 01
		00 1F 04 1F 04 00 00 20 04 20 04 FF FF 2B 04 2B
		04 FF FF 31 04 31 04 FF FF 32 04 32 04 01 00 33
		04 33 04 00 00 36 04 36 04 01 00 37 04 37 04 00
		00 38 04 38 04 01 00 39 04 39 04 00 00 3A 04 3A
		04 01 00 3B 04 3B 04 00 00 40 04 40 04 01 00 41
		04 41 04 00 00 42 04 42 04 01 00 43 04 43 04 00
		00 44 04 44 04 01 00 45 04 45 04 00 00 46 04 46
		04 01 00 47 04 47 04 00 00 4B 04 4B 04 01 00 4C
		04 4C 04 00 00 4D 04 4D 04 00 00 4E 04 4E 04 01
		00 4F 04 4F 04 02 00 51 04 51 04 FF FF 52 04 52
		04 FF FF 61 04 61 04 01 00 62 04 62 04 00 00 7D
		04 7D 04 01 00 7E 04 7E 04 00 00 7F 04 7F 04 02
		00 80 04 80 04 01 00 81 04 81 04 00 00 85 04 85
		04 01 00 86 04 86 04 00 00 87 04 87 04 01 00 88
		04 88 04 00 00 FF FF FF FF 00 00

Handle 0xDA06, DMI type 218, 185 bytes
OEM-specific Type
	Header and Data:
		DA B9 06 DA B2 00 04 FF 1F B6 40 8C 04 8C 04 01
		00 8D 04 8D 04 00 00 98 04 98 04 FF FF 99 04 99
		04 00 00 9A 04 9A 04 01 00 9B 04 9B 04 02 00 9C
		04 9C 04 01 00 9D 04 9D 04 00 00 9E 04 9E 04 01
		00 9F 04 9F 04 00 00 A0 04 A0 04 01 00 A1 04 A1
		04 00 00 A2 04 A2 04 01 00 A3 04 A3 04 00 00 E6
		04 E6 04 01 00 E7 04 E7 04 00 00 EC 04 EC 04 01
		00 ED 04 ED 04 00 00 00 05 00 05 FF FF 4A 40 4A
		40 01 00 4B 40 4B 40 00 00 4C 40 4C 40 FF FF 0C
		80 0C 80 00 00 0D 80 0D 80 00 00 0E 80 0E 80 01
		00 0F 80 0F 80 FF FF 12 80 12 80 FF FF 04 A0 04
		A0 01 00 FF FF FF FF 00 00

Handle 0xDC00, DMI type 220, 22 bytes
OEM-specific Type
	Header and Data:
		DC 16 00 DC 00 F1 00 00 02 F1 00 00 00 00 00 00
		00 00 00 00 00 00

Handle 0xDC01, DMI type 220, 22 bytes
OEM-specific Type
	Header and Data:
		DC 16 01 DC 10 F1 00 00 12 F1 00 00 00 00 00 00
		00 00 00 00 00 00

Handle 0xDC02, DMI type 220, 22 bytes
OEM-specific Type
	Header and Data:
		DC 16 02 DC 20 F1 00 00 22 F1 00 00 00 00 00 00
		00 00 00 00 00 00

Handle 0xDC03, DMI type 220, 22 bytes
OEM-specific Type
	Header and Data:
		DC 16 03 DC 30 F1 00 00 32 F1 00 00 00 00 00 00
		00 00 00 00 00 00

Handle 0xDD00, DMI type 221, 19 bytes
OEM-specific Type
	Header and Data:
		DD 13 00 DD 02 01 00 00 F6 01 F6 00 00 00 00 00
		00 00 00

Handle 0xDE00, DMI type 222, 16 bytes
OEM-specific Type
	Header and Data:
		DE 10 00 DE 01 04 00 00 18 11 30 20 55 01 00 00

Handle 0xF025, DMI type 218, 77 bytes
OEM-specific Type
	Header and Data:
		DA 4D 25 F0 B2 00 04 FF 1F B6 40 00 F1 00 F1 01
		00 02 F1 02 F1 01 00 10 F1 10 F1 01 00 12 F1 12
		F1 01 00 20 F1 20 F1 01 00 22 F1 22 F1 01 00 30
		F1 30 F1 01 00 32 F1 32 F1 01 00 00 F6 00 F6 01
		00 01 F6 01 F6 01 00 FF FF FF FF 00 00

Handle 0xF026, DMI type 130, 20 bytes
OEM-specific Type
	Header and Data:
		82 14 26 F0 24 41 4D 54 00 00 00 00 00 A5 AF 02
		C0 00 00 00

Handle 0xF027, DMI type 131, 64 bytes
OEM-specific Type
	Header and Data:
		83 40 27 F0 31 00 00 00 0B 00 00 00 00 00 0A 00
		F8 00 4E 9D 00 00 00 00 01 00 00 00 08 00 0B 00
		B6 0D 37 00 00 00 00 00 FE 00 FF FF 00 00 00 00
		00 00 00 00 22 00 00 00 76 50 72 6F 00 00 00 00

Handle 0xF028, DMI type 205, 26 bytes
OEM-specific Type
	Header and Data:
		CD 1A 28 F0 03 01 00 02 07 02 00 00 02 00 00 00
		00 96 00 03 00 00 05 00 00 00
	Strings:
		Reference Code - CPU
		uCode Version
		TXT ACM version

Handle 0xF029, DMI type 205, 26 bytes
OEM-specific Type
	Header and Data:
		CD 1A 29 F0 03 01 00 02 07 02 00 00 02 00 0B 00
		00 0A 00 03 04 0B 08 37 B6 0D
	Strings:
		Reference Code - ME 11.0
		MEBx version
		ME Firmware Version
		Corporate SKU

Handle 0xF02A, DMI type 205, 75 bytes
OEM-specific Type
	Header and Data:
		CD 4B 2A F0 0A 01 00 02 07 02 00 00 02 03 FF FF
		FF FF FF 04 00 FF FF FF 21 00 05 00 FF FF FF 21
		00 06 00 FF FF FF FF FF 07 00 3E 00 00 00 00 08
		00 34 00 00 00 00 09 00 0B 00 00 00 00 0A 00 3E
		00 00 00 00 0B 00 34 00 00 00 00
	Strings:
		Reference Code - SKL PCH
		PCH-CRID Status
		Disabled
		PCH-CRID Original Value
		PCH-CRID New Value
		OPROM - RST - RAID
		SKL PCH H Bx Hsio Version
		SKL PCH H Dx Hsio Version
		KBL PCH H Ax Hsio Version
		SKL PCH LP Bx Hsio Version
		SKL PCH LP Cx Hsio Version

Handle 0xF02B, DMI type 205, 54 bytes
OEM-specific Type
	Header and Data:
		CD 36 2B F0 07 01 00 02 07 02 00 00 02 00 02 07
		02 00 00 03 00 02 07 02 00 00 04 05 FF FF FF FF
		FF 06 00 FF FF FF 08 00 07 00 FF FF FF 08 00 08
		00 FF FF FF FF FF
	Strings:
		Reference Code - SA - System Agent
		Reference Code - MRC
		SA - PCIe Version
		SA-CRID Status
		Disabled
		SA-CRID Original Value
		SA-CRID New Value
		OPROM - VBIOS

Handle 0xF02C, DMI type 205, 103 bytes
OEM-specific Type
	Header and Data:
		CD 67 2C F0 0E 01 00 00 00 00 00 00 02 00 FF FF
		FF FF FF 03 04 FF FF FF FF FF 05 06 FF FF FF FF
		FF 07 08 FF FF FF FF FF 09 00 00 00 00 00 00 0A
		00 FF FF FF FF FF 0B 00 FF FF 00 00 00 0C 00 00
		09 00 69 10 0D 00 02 00 00 63 0E 0E 00 FF FF FF
		FF FF 0F 00 FF FF FF FF FF 10 11 01 03 03 01 00
		12 00 00 07 03 00 00
	Strings:
		Lan Phy Version
		Sensor Firmware Version
		Debug Mode Status
		Disabled
		Performance Mode Status
		Disabled
		Debug Use USB(Disabled:Serial)
		Disabled
		ICC Overclocking Version
		UNDI Version
		EC FW Version
		GOP Version
		BIOS Guard Version
		Base EC FW Version
		EC-EC Protocol Version
		Royal Park Version
		BP1.3.3.0_RP01
		Platform Version

Handle 0xF039, DMI type 136, 6 bytes
OEM-specific Type
	Header and Data:
		88 06 39 F0 00 00

Handle 0xF03A, DMI type 14, 20 bytes
Group Associations
	Name: Firmware Version Info
	Items: 5
		0xF028 (OEM-specific)
		0xF029 (OEM-specific)
		0xF02A (OEM-specific)
		0xF02B (OEM-specific)
		0xF02C (OEM-specific)

Handle 0xF03C, DMI type 13, 22 bytes
BIOS Language Information
	Language Description Format: Long
	Installable Languages: 2
		en|US|iso8859-1
		<BAD INDEX>
	Currently Installed Language: en|US|iso8859-1

Handle 0xF03D, DMI type 14, 8 bytes
Group Associations
	Name: $MEI
	Items: 1
		0x0000 (OEM-specific)

Handle 0xF03E, DMI type 203, 81 bytes
OEM-specific Type
	Header and Data:
		CB 51 3E F0 01 03 01 45 02 00 A0 06 83 10 80 30
		00 00 00 00 40 68 00 01 1F 00 00 C9 0B C0 47 02
		FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
		FF FF FF FF FF FF FF FF 03 00 00 00 80 00 00 00
		00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
		00
	Strings:
		MEI1
		MEI2
		MEI3

Handle 0xF03F, DMI type 127, 4 bytes
End Of Table
        '''


class MockCommandExecutor(CommandExecutor):
    # XXX: this is code duplication of ALL_COMMNADS from CommandExecutor
    ALL_COMMANDS = [
        HostnameMock(),
        IfaceMock(),
        HDMock(),

        # Distro command assume that version command already finished
        ConcateCommands([
            VersionMock(),
            ConcateCommands([
                DebianDistroMock(),
                RedHatDistroMock()
            ], should_stop_on_first_success=True),
        ]),
        MemMock(),

        # DPKG is debian only if failed try RPM
        ConcateCommands([
            DPKGMock(),
        ], should_stop_on_first_success=True),
        UsersMock(),
    ]

    def __init__(self):
        super().__init__(lambda x: x, None)


class ConcatCommandFailMockExecutor(MockCommandExecutor):
    ALL_COMMANDS = [
        VersionMock(),
        ConcateCommands([
            FailDistroMock(),
            RedHatDistroMock()
        ], should_stop_on_first_success=True),
    ]


class ConcatCommandSuccessMockExecutor(MockCommandExecutor):
    ALL_COMMANDS = [
        VersionMock(),
        ConcateCommands([
            RedHatDistroMock(),
            FailDistroMock()
        ], should_stop_on_first_success=True),
    ]
