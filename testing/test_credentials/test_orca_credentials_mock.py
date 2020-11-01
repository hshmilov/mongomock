from json_file_adapter.service import FILE_NAME, USERS_DATA, DEVICES_DATA
from test_helpers.file_mock_credentials import FileForCredentialsMock
# pylint: disable=C0302,C0103
orca_json_file_mock_devices = {
    FILE_NAME: 'ORCA_MOCK',
    USERS_DATA: FileForCredentialsMock(USERS_DATA, ''),
    DEVICES_DATA: FileForCredentialsMock(DEVICES_DATA, '''{
    "devices": [
      {
        "client_used": "https://app.us.orcasecurity.io_1b83666b58fa2ec0e821505e809d7ae9",
        "plugin_type": "Adapter",
        "plugin_name": "orca_adapter",
        "plugin_unique_name": "orca_adapter_0",
        "type": "entitydata",
        "accurate_for_datetime": "2020-10-26 14:36:25",
        "quick_id": "orca_adapter_0!vm_506464807365_i-008e811c26290be21_Web-Nginx",
        "id": "device0",
        "name": "Web-Nginx",
        "cloud_provider": "AWS",
        "cloud_id": "i-008e811c26290be21",
        "failed_logins": [
          {
            "log_time": "2020-10-12 14:20:02",
            "source_ipv4": "89.139.22.73",
            "username": "ubuntu"
          },
          {
            "log_time": "2020-10-12 14:19:34",
            "source_ipv4": "89.139.22.73",
            "username": "ubuntu"
          }
        ],
        "successful_logins": [
          {
            "log_time": "2020-10-04 11:30:50",
            "source_ipv4": "89-139-22-73.bb.netvision.net.il",
            "logout_time": "2020-10-04 11:39:36",
            "username": "ec2-user"
          },
          {
            "log_time": "2020-09-01 20:36:52",
            "source_ipv4": "46-117-146-173.bb.netvision.net.il",
            "logout_time": "2020-09-01 20:40:02",
            "username": "ec2-user"
          },
          {
            "log_time": "2020-09-01 20:24:47",
            "source_ipv4": "46-117-146-173.bb.netvision.net.il",
            "logout_time": "2020-09-01 20:27:02",
            "username": "ec2-user"
          },
          {
            "log_time": "2019-12-10 14:55:49",
            "source_ipv4": "185.110.111.96",
            "logout_time": "2019-12-10 14:56:46",
            "username": "ec2-user"
          },
          {
            "log_time": "2019-09-10 07:26:10",
            "source_ipv4": "141.226.241.149",
            "logout_time": "2019-09-10 09:02:07",
            "username": "ec2-user"
          },
          {
            "log_time": "2019-09-08 20:09:10",
            "source_ipv4": "bzq-109-65-20-108.red.bezeqint.net",
            "logout_time": "2019-09-08 22:02:18",
            "username": "ec2-user"
          },
          {
            "log_time": "2019-09-08 14:51:09",
            "source_ipv4": "141.226.241.149",
            "logout_time": "2019-09-08 15:13:54",
            "username": "ec2-user"
          },
          {
            "log_time": "2019-09-08 13:02:23",
            "source_ipv4": "141.226.241.149",
            "logout_time": "2019-09-08 14:50:03",
            "username": "ec2-user"
          },
          {
            "log_time": "2019-09-08 12:51:51",
            "source_ipv4": "141.226.241.149",
            "logout_time": "2019-09-08 13:01:56",
            "username": "ec2-user"
          },
          {
            "log_time": "2019-09-08 10:16:58",
            "source_ipv4": "141.226.241.149",
            "logout_time": "2019-09-08 12:44:10",
            "username": "ec2-user"
          },
          {
            "log_time": "2019-09-08 07:49:45",
            "source_ipv4": "141.226.241.149",
            "logout_time": "2019-09-08 08:52:24",
            "username": "ec2-user"
          },
          {
            "log_time": "2019-09-08 07:13:54",
            "source_ipv4": "141.226.241.149",
            "logout_time": "2019-09-08 08:52:24",
            "username": "ec2-user"
          },
          {
            "log_time": "2019-09-08 07:12:41",
            "source_ipv4": "141.226.241.149",
            "logout_time": "2019-09-08 07:13:11",
            "username": "ec2-user"
          },
          {
            "log_time": "2019-06-11 19:46:02",
            "source_ipv4": "bzq-79-183-236-212.red.bezeqint.net",
            "logout_time": "2019-06-11 19:57:24",
            "username": "ec2-user"
          },
          {
            "log_time": "2019-06-11 19:45:52",
            "source_ipv4": "bzq-79-183-236-212.red.bezeqint.net",
            "username": "root"
          }
        ],
        "installed_software": [
          {
            "name": "cpio"
          },
          {
            "name": "rsync"
          },
          {
            "name": "yum-plugin-upgrade-helper"
          },
          {
            "name": "httpclient-4.2.3.jar"
          },
          {
            "name": "sed"
          },
          {
            "name": "pam_krb5"
          },
          {
            "name": "pam_ccreds"
          },
          {
            "name": "db4"
          },
          {
            "name": "libnih"
          },
          {
            "name": "lsof"
          },
          {
            "name": "python27-pygpgme"
          },
          {
            "name": "java-1.7.0-openjdk"
          },
          {
            "name": "joda-time-1.6.jar"
          },
          {
            "name": "bzip2"
          },
          {
            "name": "irqbalance"
          },
          {
            "name": "lvm2"
          },
          {
            "name": "copy-jdk-configs"
          },
          {
            "name": "system-release"
          },
          {
            "name": "libcgroup"
          },
          {
            "name": "perl-Pod-Perldoc"
          },
          {
            "name": "wsdl4j-1.6.1.jar"
          },
          {
            "name": "resources.jar"
          },
          {
            "name": "e2fsprogs-libs"
          },
          {
            "name": "perl-Error"
          },
          {
            "name": "libXi"
          },
          {
            "name": "rootfiles"
          },
          {
            "name": "python27-imaging"
          },
          {
            "name": "cracklib-dicts"
          },
          {
            "name": "rubygem20-psych"
          },
          {
            "name": "jaxb-api.jar"
          },
          {
            "name": "libcap-ng"
          },
          {
            "name": "authconfig"
          },
          {
            "name": "dracut"
          },
          {
            "name": "AWSJavaClientJmxSPI-external_release_1.9.jar"
          },
          {
            "name": "lvm2-libs"
          },
          {
            "name": "newt"
          },
          {
            "name": "libtasn1"
          },
          {
            "name": "groff-base"
          },
          {
            "name": "mdadm"
          },
          {
            "name": "xalan-j2-2.7.0.jar"
          },
          {
            "name": "perl-Time-Local"
          },
          {
            "name": "file"
          },
          {
            "name": "psacct"
          },
          {
            "name": "perl-Time-HiRes"
          },
          {
            "name": "hesiod"
          },
          {
            "name": "openssh-server"
          },
          {
            "name": "ttmkfdir"
          },
          {
            "name": "tmpwatch"
          },
          {
            "name": "device-mapper-event-libs"
          },
          {
            "name": "words"
          },
          {
            "name": "perl-Pod-Usage"
          },
          {
            "name": "libcurl"
          },
          {
            "name": "yum-metadata-parser"
          },
          {
            "name": "kmod-libs"
          },
          {
            "name": "p11-kit-trust"
          },
          {
            "name": "bash"
          },
          {
            "name": "libidn2"
          },
          {
            "name": "libXrender"
          },
          {
            "name": "python27-chardet"
          },
          {
            "name": "device-mapper-persistent-data"
          },
          {
            "name": "nspr"
          },
          {
            "name": "at"
          },
          {
            "name": "tar"
          },
          {
            "name": "grep"
          },
          {
            "name": "alsa-lib"
          },
          {
            "name": "pkgconfig"
          },
          {
            "name": "util-linux"
          },
          {
            "name": "gnupg2"
          },
          {
            "name": "dejavu-sans-fonts"
          },
          {
            "name": "libpwquality"
          },
          {
            "name": "gmp"
          },
          {
            "name": "dmraid"
          },
          {
            "name": "aws-amitools-ec2"
          },
          {
            "name": "US_export_policy.jar"
          },
          {
            "name": "gpm-libs"
          },
          {
            "name": "commons-logging-1.0.4.jar"
          },
          {
            "name": "generic-logos"
          },
          {
            "name": "python27-requests"
          },
          {
            "name": "libblkid"
          },
          {
            "name": "python27-rsa"
          },
          {
            "name": "python27-babel"
          },
          {
            "name": "rubygem20-rdoc"
          },
          {
            "name": "python27-pyxattr"
          },
          {
            "name": "libxml2-python27"
          },
          {
            "name": "wsdl4j.jar"
          },
          {
            "name": "service.jar"
          },
          {
            "name": "iproute"
          },
          {
            "name": "libgssglue"
          },
          {
            "name": "AWSS3JavaClient-external_release_1.9.jar"
          },
          {
            "name": "screen"
          },
          {
            "name": "perl-Digest-HMAC"
          },
          {
            "name": "commons-discovery-0.2.jar"
          },
          {
            "name": "python27-urlgrabber"
          },
          {
            "name": "xz-libs"
          },
          {
            "name": "libevent"
          },
          {
            "name": "log4j.jar"
          },
          {
            "name": "grub"
          },
          {
            "name": "rpcbind"
          },
          {
            "name": "libgpg-error"
          },
          {
            "name": "perl-podlators"
          },
          {
            "name": "xercesImpl.jar"
          },
          {
            "name": "libfontenc"
          },
          {
            "name": "libnghttp2"
          },
          {
            "name": "libudev"
          },
          {
            "name": "python27-ply"
          },
          {
            "name": "policycoreutils"
          },
          {
            "name": "diffutils"
          },
          {
            "name": "libSM"
          },
          {
            "name": "dhclient"
          },
          {
            "name": "ruby"
          },
          {
            "name": "perl-Filter"
          },
          {
            "name": "libicu"
          },
          {
            "name": "sysvinit"
          },
          {
            "name": "update-motd"
          },
          {
            "name": "rpm-libs"
          },
          {
            "name": "setup"
          },
          {
            "name": "sendmail"
          },
          {
            "name": "perl-threads"
          },
          {
            "name": "dnsns.jar"
          },
          {
            "name": "libverto"
          },
          {
            "name": "aws-apitools-common"
          },
          {
            "name": "jdom.jar"
          },
          {
            "name": "python27-markupsafe"
          },
          {
            "name": "setserial"
          },
          {
            "name": "db4-utils"
          },
          {
            "name": "commons-httpclient-3.1.jar"
          },
          {
            "name": "libssh2"
          },
          {
            "name": "libgcc72"
          },
          {
            "name": "readline"
          },
          {
            "name": "perl-constant"
          },
          {
            "name": "stax2-api-3.0.1.jar"
          },
          {
            "name": "xalan.jar"
          },
          {
            "name": "libXext"
          },
          {
            "name": "fontconfig"
          },
          {
            "name": "sqlite"
          },
          {
            "name": "mailcap"
          },
          {
            "name": "j2ee_mail.jar"
          },
          {
            "name": "python27-backports"
          },
          {
            "name": "serializer.jar"
          },
          {
            "name": "tzdata-java"
          },
          {
            "name": "perl-Carp"
          },
          {
            "name": "commons-codec-1.3.jar"
          },
          {
            "name": "AWSEC2JavaClient-1.9ux.jar"
          },
          {
            "name": "charsets.jar"
          },
          {
            "name": "bzip2-libs"
          },
          {
            "name": "jce.jar"
          },
          {
            "name": "python27-backports-ssl_match_hostname"
          },
          {
            "name": "rpm-build-libs"
          },
          {
            "name": "device-mapper-libs"
          },
          {
            "name": "bcprov-jdk15-145.jar"
          },
          {
            "name": "python27-libs"
          },
          {
            "name": "libpng"
          },
          {
            "name": "net-tools"
          },
          {
            "name": "jdom-1.0.jar"
          },
          {
            "name": "python27-ecdsa"
          },
          {
            "name": "nano"
          },
          {
            "name": "commons-codec-1.4.jar"
          },
          {
            "name": "quota-nls"
          },
          {
            "name": "gpgme"
          },
          {
            "name": "nss-softokn"
          },
          {
            "name": "glibc"
          },
          {
            "name": "libunwind"
          },
          {
            "name": "python27-jinja2"
          },
          {
            "name": "nss-util"
          },
          {
            "name": "httpcore-4.2.jar"
          },
          {
            "name": "libidn"
          },
          {
            "name": "libffi"
          },
          {
            "name": "dash"
          },
          {
            "name": "nss-softokn-freebl"
          },
          {
            "name": "python27-jsonpointer"
          },
          {
            "name": "gdisk"
          },
          {
            "name": "xorg-x11-fonts-Type1"
          },
          {
            "name": "gperftools-libs"
          },
          {
            "name": "git"
          },
          {
            "name": "wss4j-1.5.3.jar"
          },
          {
            "name": "perl-Storable"
          },
          {
            "name": "nfs-utils"
          },
          {
            "name": "python27-jmespath"
          },
          {
            "name": "gpg-pubkey"
          },
          {
            "name": "fontpackages-filesystem"
          },
          {
            "name": "python27-pycurl"
          },
          {
            "name": "perl-Digest"
          },
          {
            "name": "libjpeg-turbo"
          },
          {
            "name": "dejavu-serif-fonts"
          },
          {
            "name": "ethtool"
          },
          {
            "name": "perl-Text-ParseWords"
          },
          {
            "name": "ruby20"
          },
          {
            "name": "keyutils"
          },
          {
            "name": "cryptsetup"
          },
          {
            "name": "vim-enhanced"
          },
          {
            "name": "traceroute"
          },
          {
            "name": "rpm-python27"
          },
          {
            "name": "cloud-init"
          },
          {
            "name": "libX11-common"
          },
          {
            "name": "rt.jar"
          },
          {
            "name": "perl-Getopt-Long"
          },
          {
            "name": "initscripts"
          },
          {
            "name": "bc"
          },
          {
            "name": "kbd"
          },
          {
            "name": "libcom_err"
          },
          {
            "name": "yum-plugin-priorities"
          },
          {
            "name": "nss-tools"
          },
          {
            "name": "acpid"
          },
          {
            "name": "krb5-libs"
          },
          {
            "name": "gawk"
          },
          {
            "name": "checkpolicy"
          },
          {
            "name": "tcp_wrappers-libs"
          },
          {
            "name": "rubygem20-bigdecimal"
          },
          {
            "name": "groff"
          },
          {
            "name": "lcms2"
          },
          {
            "name": "stax-api-1.0.1.jar"
          },
          {
            "name": "openssh-clients"
          },
          {
            "name": "gdbm"
          },
          {
            "name": "audit"
          },
          {
            "name": "procmail"
          },
          {
            "name": "tcp_wrappers"
          },
          {
            "name": "sunjce_provider.jar"
          },
          {
            "name": "libX11"
          },
          {
            "name": "lua"
          },
          {
            "name": "cyrus-sasl-lib"
          },
          {
            "name": "glibc-common"
          },
          {
            "name": "ed"
          },
          {
            "name": "ec2-api-tools-1.7.3.0.jar"
          },
          {
            "name": "libXtst"
          },
          {
            "name": "EC2CltJavaClient-1.0.jar"
          },
          {
            "name": "wss4j-1.5.7.jar"
          },
          {
            "name": "python27-pystache"
          },
          {
            "name": "giflib"
          },
          {
            "name": "python27-daemon"
          },
          {
            "name": "cyrus-sasl"
          },
          {
            "name": "perl-libs"
          },
          {
            "name": "xorg-x11-font-utils"
          },
          {
            "name": "python27-iniparse"
          },
          {
            "name": "javapackages-tools"
          },
          {
            "name": "time"
          },
          {
            "name": "perl-threads-shared"
          },
          {
            "name": "python27-pyasn1"
          },
          {
            "name": "ec2-utils"
          },
          {
            "name": "rubygem20-json"
          },
          {
            "name": "AWSJavaCredentialInterfaces-1.0.jar"
          },
          {
            "name": "newt-python27"
          },
          {
            "name": "cyrus-sasl-plain"
          },
          {
            "name": "perl-macros"
          },
          {
            "name": "jackson-databind-2.3.2.jar"
          },
          {
            "name": "python27-lockfile"
          },
          {
            "name": "ec2-net-utils"
          },
          {
            "name": "xz"
          },
          {
            "name": "libxslt"
          },
          {
            "name": "perl-Encode"
          },
          {
            "name": "libXcomposite"
          },
          {
            "name": "upstart"
          },
          {
            "name": "crontabs"
          },
          {
            "name": "jaxb-impl-2.0.1.jar"
          },
          {
            "name": "sysfsutils"
          },
          {
            "name": "rhino.jar"
          },
          {
            "name": "perl"
          },
          {
            "name": "dmraid-events"
          },
          {
            "name": "xfire-all-1.2.6.jar"
          },
          {
            "name": "ruby20-irb"
          },
          {
            "name": "libXau"
          },
          {
            "name": "coreutils"
          },
          {
            "name": "pciutils-libs"
          },
          {
            "name": "jaxws-api.jar"
          },
          {
            "name": "AWSJavaClientRuntime-external_release_1.9.jar"
          },
          {
            "name": "vim-common"
          },
          {
            "name": "elfutils-libelf"
          },
          {
            "name": "zlib"
          },
          {
            "name": "fuse-libs"
          },
          {
            "name": "perl-Digest-SHA"
          },
          {
            "name": "expat"
          },
          {
            "name": "xmlsec-1.4.8.jar"
          },
          {
            "name": "libuuid"
          },
          {
            "name": "cryptsetup-libs"
          },
          {
            "name": "filesystem"
          },
          {
            "name": "perl-PathTools"
          },
          {
            "name": "libsepol"
          },
          {
            "name": "pcre"
          },
          {
            "name": "xfire-jsr181-api-1.0-M1.jar"
          },
          {
            "name": "freetype"
          },
          {
            "name": "httpclient-4.2.jar"
          },
          {
            "name": "epel-release"
          },
          {
            "name": "libsemanage"
          },
          {
            "name": "libuser"
          },
          {
            "name": "attr"
          },
          {
            "name": "p11-kit"
          },
          {
            "name": "xmlsecSamples-1.4.8.jar"
          },
          {
            "name": "aws-apitools-as"
          },
          {
            "name": "nss-pem"
          },
          {
            "name": "rubygems20"
          },
          {
            "name": "iptables"
          },
          {
            "name": "curl"
          },
          {
            "name": "libmount"
          },
          {
            "name": "HttpClientSslContrib-1.0.jar"
          },
          {
            "name": "perl-TermReadKey"
          },
          {
            "name": "woodstox-core-asl-4.0.5.jar"
          },
          {
            "name": "keyutils-libs"
          },
          {
            "name": "cronie-anacron"
          },
          {
            "name": "dbus-libs"
          },
          {
            "name": "commons-httpclient-3.0.jar"
          },
          {
            "name": "libselinux-utils"
          },
          {
            "name": "libcap"
          },
          {
            "name": "libselinux"
          },
          {
            "name": "xmlsecTests-1.4.8.jar"
          },
          {
            "name": "dbus"
          },
          {
            "name": "joda-time-2.3.jar"
          },
          {
            "name": "dump"
          },
          {
            "name": "cracklib"
          },
          {
            "name": "yum"
          },
          {
            "name": "libedit"
          },
          {
            "name": "procps"
          },
          {
            "name": "pm-utils"
          },
          {
            "name": "libxml2"
          },
          {
            "name": "libunistring"
          },
          {
            "name": "dhcp-common"
          },
          {
            "name": "nginx"
          },
          {
            "name": "device-mapper-event"
          },
          {
            "name": "nc"
          },
          {
            "name": "commons-discovery.jar"
          },
          {
            "name": "info"
          },
          {
            "name": "device-mapper"
          },
          {
            "name": "python27-setuptools"
          },
          {
            "name": "rmt"
          },
          {
            "name": "shared-mime-info"
          },
          {
            "name": "sysctl-defaults"
          },
          {
            "name": "numactl"
          },
          {
            "name": "xmlsec-1.4.2.jar"
          },
          {
            "name": "openssh"
          },
          {
            "name": "python27-paramiko"
          },
          {
            "name": "python27-jsonpatch"
          },
          {
            "name": "ncurses-libs"
          },
          {
            "name": "ntp"
          },
          {
            "name": "pam_passwdqc"
          },
          {
            "name": "bind-utils"
          },
          {
            "name": "perl-File-Temp"
          },
          {
            "name": "pinentry"
          },
          {
            "name": "popt"
          },
          {
            "name": "nss-sysinit"
          },
          {
            "name": "libss"
          },
          {
            "name": "aws-cfn-bootstrap"
          },
          {
            "name": "zipfs.jar"
          },
          {
            "name": "CliCommando-1.0.jar"
          },
          {
            "name": "python27-pyliblzma"
          },
          {
            "name": "ustr"
          },
          {
            "name": "mingetty"
          },
          {
            "name": "shadow-utils"
          },
          {
            "name": "logrotate"
          },
          {
            "name": "libnfsidmap"
          },
          {
            "name": "python27-PyYAML"
          },
          {
            "name": "binutils"
          },
          {
            "name": "python27-kitchen"
          },
          {
            "name": "sunpkcs11.jar"
          },
          {
            "name": "libpsl"
          },
          {
            "name": "python27-simplejson"
          },
          {
            "name": "libacl"
          },
          {
            "name": "jaxws-api-2.0.jar"
          },
          {
            "name": "libXfont"
          },
          {
            "name": "pth"
          },
          {
            "name": "XmlSchema-1.4.5.jar"
          },
          {
            "name": "perl-Exporter"
          },
          {
            "name": "libgcrypt"
          },
          {
            "name": "openldap"
          },
          {
            "name": "perl-Digest-MD5"
          },
          {
            "name": "acl"
          },
          {
            "name": "python27-pip"
          },
          {
            "name": "management-agent.jar"
          },
          {
            "name": "python27-configobj"
          },
          {
            "name": "commons-logging-adapters-1.1.1.jar"
          },
          {
            "name": "python27-botocore"
          },
          {
            "name": "hwdata"
          },
          {
            "name": "libpipeline"
          },
          {
            "name": "psmisc"
          },
          {
            "name": "jaxb-api-2.0.jar"
          },
          {
            "name": "dracut-modules-growroot"
          },
          {
            "name": "python27-crypto"
          },
          {
            "name": "aws-apitools-mon"
          },
          {
            "name": "grubby"
          },
          {
            "name": "kernel-4.14.77-70.59.amzn1.x86_64"
          },
          {
            "name": "vim-filesystem"
          },
          {
            "name": "commons-logging-api-1.1.1.jar"
          },
          {
            "name": "basesystem"
          },
          {
            "name": "ec2-hibinit-agent"
          },
          {
            "name": "man-db"
          },
          {
            "name": "man-pages"
          },
          {
            "name": "python27"
          },
          {
            "name": "slang"
          },
          {
            "name": "ruby20-libs"
          },
          {
            "name": "rsyslog"
          },
          {
            "name": "hibagent"
          },
          {
            "name": "wstx-asl-3.2.0.jar"
          },
          {
            "name": "glib2"
          },
          {
            "name": "vim-minimal"
          },
          {
            "name": "libaio"
          },
          {
            "name": "ncurses"
          },
          {
            "name": "unzip"
          },
          {
            "name": "python27-boto"
          },
          {
            "name": "jackson-core-2.3.2.jar"
          },
          {
            "name": "parted"
          },
          {
            "name": "ca-certificates"
          },
          {
            "name": "libtirpc"
          },
          {
            "name": "commons-cli-1.1.jar"
          },
          {
            "name": "audit-libs"
          },
          {
            "name": "python27-devel"
          },
          {
            "name": "amazon-ssm-agent"
          },
          {
            "name": "libassuan"
          },
          {
            "name": "perl-parent"
          },
          {
            "name": "aws-apitools-elb"
          },
          {
            "name": "make"
          },
          {
            "name": "perl-Scalar-List-Utils"
          },
          {
            "name": "quota"
          },
          {
            "name": "ncurses-base"
          },
          {
            "name": "python27-futures"
          },
          {
            "name": "fipscheck-lib"
          },
          {
            "name": "yum-utils"
          },
          {
            "name": "libstdc++72"
          },
          {
            "name": "perl-Pod-Escapes"
          },
          {
            "name": "chkconfig"
          },
          {
            "name": "kbd-misc"
          },
          {
            "name": "pciutils"
          },
          {
            "name": "libutempter"
          },
          {
            "name": "passwd"
          },
          {
            "name": "aws-apitools-ec2"
          },
          {
            "name": "xml-apis.jar"
          },
          {
            "name": "sudo"
          },
          {
            "name": "libyaml"
          },
          {
            "name": "perl-Socket"
          },
          {
            "name": "perl-Pod-Simple"
          },
          {
            "name": "EC2ConversionLib-1.0.jar"
          },
          {
            "name": "less"
          },
          {
            "name": "jaxb-impl.jar"
          },
          {
            "name": "libnl"
          },
          {
            "name": "openssl"
          },
          {
            "name": "hmaccalc"
          },
          {
            "name": "activation-1.1.jar"
          },
          {
            "name": "python27-virtualenv"
          },
          {
            "name": "python27-colorama"
          },
          {
            "name": "file-libs"
          },
          {
            "name": "route53.jar"
          },
          {
            "name": "fipscheck"
          },
          {
            "name": "perl-Git"
          },
          {
            "name": "ntpdate"
          },
          {
            "name": "zip"
          },
          {
            "name": "jpackage-utils"
          },
          {
            "name": "which"
          },
          {
            "name": "libattr"
          },
          {
            "name": "libICE"
          },
          {
            "name": "perl-File-Path"
          },
          {
            "name": "rpm"
          },
          {
            "name": "commons-lang-2.4.jar"
          },
          {
            "name": "aws-cli"
          },
          {
            "name": "iputils"
          },
          {
            "name": "BlockDeviceLib-1.0.jar"
          },
          {
            "name": "local_policy.jar"
          },
          {
            "name": "cloud-disk-utils"
          },
          {
            "name": "log4j-1.2.14.jar"
          },
          {
            "name": "ntsysv"
          },
          {
            "name": "libxcb"
          },
          {
            "name": "get_reference_source"
          },
          {
            "name": "kpartx"
          },
          {
            "name": "tzdata"
          },
          {
            "name": "dejavu-fonts-common"
          },
          {
            "name": "sgpio"
          },
          {
            "name": "python27-dateutil"
          },
          {
            "name": "localedata.jar"
          },
          {
            "name": "wget"
          },
          {
            "name": "pam"
          },
          {
            "name": "kmod"
          },
          {
            "name": "e2fsprogs"
          },
          {
            "name": "python27-urllib3"
          },
          {
            "name": "findutils"
          },
          {
            "name": "jsse.jar"
          },
          {
            "name": "python27-docutils"
          },
          {
            "name": "python27-six"
          },
          {
            "name": "udev"
          },
          {
            "name": "rng-tools"
          },
          {
            "name": "gzip"
          },
          {
            "name": "bind-libs"
          },
          {
            "name": "cronie"
          },
          {
            "name": "nss"
          },
          {
            "name": "libsysfs"
          },
          {
            "name": "perl-HTTP-Tiny"
          }
        ],
        "git_repos": [
          {
            "local_name": "git_repo",
            "path": "/home/ec2-user/git_repo",
            "size": 0
          }
        ],
        "orca_dbs": [
          {
            "db_path": "/etc/pki/nssdb/key4.db",
            "db_size": 11264,
            "last_accessed_time": "2018-10-23 04:29:21",
            "last_modified_time": "2018-10-23 04:29:21",
            "type": "sqlite3"
          },
          {
            "db_path": "/etc/pki/nssdb/cert9.db",
            "db_size": 9216,
            "last_accessed_time": "2018-10-23 04:29:21",
            "last_modified_time": "2018-10-23 04:29:21",
            "type": "sqlite3"
          }
        ],
        "software_cves": [
          {
            "cve_id": "CVE-2015-2716"
          },
          {
            "cve_id": "CVE-2019-11745"
          },
          {
            "cve_id": "CVE-2019-18218"
          },
          {
            "cve_id": "CVE-2019-5436"
          },
          {
            "cve_id": "CVE-2019-9924"
          },
          {
            "cve_id": "CVE-2018-11236"
          },
          {
            "cve_id": "CVE-2018-5729"
          },
          {
            "cve_id": "CVE-2018-16842"
          },
          {
            "cve_id": "CVE-2020-11080"
          },
          {
            "cve_id": "CVE-2020-8492"
          },
          {
            "cve_id": "CVE-2019-9516"
          },
          {
            "cve_id": "CVE-2019-9513"
          },
          {
            "cve_id": "CVE-2019-9511"
          },
          {
            "cve_id": "CVE-2019-8907"
          },
          {
            "cve_id": "CVE-2018-16839"
          },
          {
            "cve_id": "CVE-2018-14567"
          },
          {
            "cve_id": "CVE-2018-14404"
          },
          {
            "cve_id": "CVE-2017-18258"
          },
          {
            "cve_id": "CVE-2018-0739"
          },
          {
            "cve_id": "CVE-2016-5131"
          },
          {
            "cve_id": "CVE-2015-8035"
          },
          {
            "cve_id": "CVE-2017-16997"
          },
          {
            "cve_id": "CVE-2019-12749"
          },
          {
            "cve_id": "CVE-2019-16935"
          },
          {
            "cve_id": "CVE-2018-5407"
          },
          {
            "cve_id": "CVE-2020-8177"
          },
          {
            "cve_id": "CVE-2019-20907"
          },
          {
            "cve_id": "CVE-2020-10531"
          },
          {
            "cve_id": "CVE-2019-18348"
          },
          {
            "cve_id": "CVE-2019-12290"
          },
          {
            "cve_id": "CVE-2019-18224"
          },
          {
            "cve_id": "CVE-2019-5482"
          },
          {
            "cve_id": "CVE-2019-5481"
          },
          {
            "cve_id": "CVE-2019-1563"
          },
          {
            "cve_id": "CVE-2019-16056"
          },
          {
            "cve_id": "CVE-2019-11729"
          },
          {
            "cve_id": "CVE-2018-20852"
          },
          {
            "cve_id": "CVE-2019-12450"
          },
          {
            "cve_id": "CVE-2019-5435"
          },
          {
            "cve_id": "CVE-2018-12404"
          },
          {
            "cve_id": "CVE-2019-1559"
          },
          {
            "cve_id": "CVE-2019-8906"
          },
          {
            "cve_id": "CVE-2019-8905"
          },
          {
            "cve_id": "CVE-2019-8904"
          },
          {
            "cve_id": "CVE-2016-10739"
          },
          {
            "cve_id": "CVE-2018-20217"
          },
          {
            "cve_id": "CVE-2018-20483"
          },
          {
            "cve_id": "CVE-2018-16844"
          },
          {
            "cve_id": "CVE-2018-16843"
          },
          {
            "cve_id": "CVE-2018-16840"
          },
          {
            "cve_id": "CVE-2018-0734"
          },
          {
            "cve_id": "CVE-2018-14618"
          },
          {
            "cve_id": "CVE-2017-15412"
          },
          {
            "cve_id": "CVE-2018-0500"
          },
          {
            "cve_id": "CVE-2018-0495"
          },
          {
            "cve_id": "CVE-2018-11237"
          },
          {
            "cve_id": "CVE-2018-5730"
          },
          {
            "cve_id": "CVE-2018-6485"
          },
          {
            "cve_id": "CVE-2017-3735"
          },
          {
            "cve_id": "CVE-2019-9500"
          },
          {
            "cve_id": "CVE-2015-2716"
          },
          {
            "cve_id": "CVE-2019-11745"
          },
          {
            "cve_id": "CVE-2019-18218"
          },
          {
            "cve_id": "CVE-2019-11815"
          },
          {
            "cve_id": "CVE-2019-5436"
          },
          {
            "cve_id": "CVE-2019-9924"
          },
          {
            "cve_id": "CVE-2018-11236"
          },
          {
            "cve_id": "CVE-2018-20669"
          },
          {
            "cve_id": "CVE-2018-5729"
          },
          {
            "cve_id": "CVE-2018-16842"
          },
          {
            "cve_id": "CVE-2019-11599"
          },
          {
            "cve_id": "CVE-2020-11080"
          },
          {
            "cve_id": "CVE-2020-10711"
          },
          {
            "cve_id": "CVE-2020-8492"
          },
          {
            "cve_id": "CVE-2019-19332"
          },
          {
            "cve_id": "CVE-2019-20096"
          },
          {
            "cve_id": "CVE-2019-19462"
          },
          {
            "cve_id": "CVE-2019-19062"
          },
          {
            "cve_id": "CVE-2018-12207"
          },
          {
            "cve_id": "CVE-2019-11139"
          },
          {
            "cve_id": "CVE-2019-14821"
          },
          {
            "cve_id": "CVE-2019-15538"
          },
          {
            "cve_id": "CVE-2019-9513"
          },
          {
            "cve_id": "CVE-2019-9511"
          },
          {
            "cve_id": "CVE-2019-11479"
          },
          {
            "cve_id": "CVE-2019-11478"
          },
          {
            "cve_id": "CVE-2019-11477"
          },
          {
            "cve_id": "CVE-2019-3882"
          },
          {
            "cve_id": "CVE-2019-8980"
          },
          {
            "cve_id": "CVE-2019-8907"
          },
          {
            "cve_id": "CVE-2018-19407"
          },
          {
            "cve_id": "CVE-2018-16839"
          },
          {
            "cve_id": "CVE-2018-14567"
          },
          {
            "cve_id": "CVE-2018-14404"
          },
          {
            "cve_id": "CVE-2017-18258"
          },
          {
            "cve_id": "CVE-2018-0739"
          },
          {
            "cve_id": "CVE-2016-5131"
          },
          {
            "cve_id": "CVE-2015-8035"
          },
          {
            "cve_id": "CVE-2020-14386"
          },
          {
            "cve_id": "CVE-2018-16884"
          },
          {
            "cve_id": "CVE-2017-16997"
          },
          {
            "cve_id": "CVE-2019-12749"
          },
          {
            "cve_id": "CVE-2020-0543"
          },
          {
            "cve_id": "CVE-2019-11135"
          },
          {
            "cve_id": "CVE-2019-1125"
          },
          {
            "cve_id": "CVE-2019-11091"
          },
          {
            "cve_id": "CVE-2018-12130"
          },
          {
            "cve_id": "CVE-2018-12127"
          },
          {
            "cve_id": "CVE-2018-12126"
          },
          {
            "cve_id": "CVE-2019-16935"
          },
          {
            "cve_id": "CVE-2019-9213"
          },
          {
            "cve_id": "CVE-2019-6974"
          },
          {
            "cve_id": "CVE-2018-5407"
          },
          {
            "cve_id": "CVE-2020-10768"
          },
          {
            "cve_id": "CVE-2020-10767"
          },
          {
            "cve_id": "CVE-2020-10766"
          },
          {
            "cve_id": "CVE-2020-8177"
          },
          {
            "cve_id": "CVE-2020-1749"
          },
          {
            "cve_id": "CVE-2019-20907"
          },
          {
            "cve_id": "CVE-2020-10732"
          },
          {
            "cve_id": "CVE-2020-10757"
          },
          {
            "cve_id": "CVE-2020-10751"
          },
          {
            "cve_id": "CVE-2020-12826"
          },
          {
            "cve_id": "CVE-2020-12771"
          },
          {
            "cve_id": "CVE-2020-12770"
          },
          {
            "cve_id": "CVE-2020-12657"
          },
          {
            "cve_id": "CVE-2020-2732"
          },
          {
            "cve_id": "CVE-2020-10942"
          },
          {
            "cve_id": "CVE-2020-10531"
          },
          {
            "cve_id": "CVE-2020-8648"
          },
          {
            "cve_id": "CVE-2019-19768"
          },
          {
            "cve_id": "CVE-2019-19319"
          },
          {
            "cve_id": "CVE-2019-18348"
          },
          {
            "cve_id": "CVE-2019-12290"
          },
          {
            "cve_id": "CVE-2019-18224"
          },
          {
            "cve_id": "CVE-2019-14835"
          },
          {
            "cve_id": "CVE-2019-5482"
          },
          {
            "cve_id": "CVE-2019-5481"
          },
          {
            "cve_id": "CVE-2019-1563"
          },
          {
            "cve_id": "CVE-2019-16056"
          },
          {
            "cve_id": "CVE-2019-15918"
          },
          {
            "cve_id": "CVE-2019-15902"
          },
          {
            "cve_id": "CVE-2019-10142"
          },
          {
            "cve_id": "CVE-2019-11729"
          },
          {
            "cve_id": "CVE-2018-20852"
          },
          {
            "cve_id": "CVE-2019-12450"
          },
          {
            "cve_id": "CVE-2019-5435"
          },
          {
            "cve_id": "CVE-2019-11884"
          },
          {
            "cve_id": "CVE-2018-12404"
          },
          {
            "cve_id": "CVE-2019-3900"
          },
          {
            "cve_id": "CVE-2019-3460"
          },
          {
            "cve_id": "CVE-2019-3459"
          },
          {
            "cve_id": "CVE-2019-7222"
          },
          {
            "cve_id": "CVE-2019-7221"
          },
          {
            "cve_id": "CVE-2019-1559"
          },
          {
            "cve_id": "CVE-2019-8912"
          },
          {
            "cve_id": "CVE-2019-8906"
          },
          {
            "cve_id": "CVE-2019-8905"
          },
          {
            "cve_id": "CVE-2019-8904"
          },
          {
            "cve_id": "CVE-2019-7308"
          },
          {
            "cve_id": "CVE-2016-10739"
          },
          {
            "cve_id": "CVE-2019-5489"
          },
          {
            "cve_id": "CVE-2018-20217"
          },
          {
            "cve_id": "CVE-2018-20483"
          },
          {
            "cve_id": "CVE-2018-20169"
          },
          {
            "cve_id": "CVE-2018-16862"
          },
          {
            "cve_id": "CVE-2018-16840"
          },
          {
            "cve_id": "CVE-2018-0734"
          },
          {
            "cve_id": "CVE-2018-18710"
          },
          {
            "cve_id": "CVE-2018-14625"
          },
          {
            "cve_id": "CVE-2018-14618"
          },
          {
            "cve_id": "CVE-2017-15412"
          },
          {
            "cve_id": "CVE-2018-0500"
          },
          {
            "cve_id": "CVE-2018-0495"
          },
          {
            "cve_id": "CVE-2018-11237"
          },
          {
            "cve_id": "CVE-2018-5730"
          },
          {
            "cve_id": "CVE-2018-6485"
          },
          {
            "cve_id": "CVE-2017-3735"
          },
          {
            "cve_id": "CVE-2015-2716"
          },
          {
            "cve_id": "CVE-2019-11745"
          },
          {
            "cve_id": "CVE-2019-18218"
          },
          {
            "cve_id": "CVE-2019-5436"
          },
          {
            "cve_id": "CVE-2019-9924"
          },
          {
            "cve_id": "CVE-2018-11236"
          },
          {
            "cve_id": "CVE-2018-5729"
          },
          {
            "cve_id": "CVE-2018-16842"
          },
          {
            "cve_id": "CVE-2020-11080"
          },
          {
            "cve_id": "CVE-2020-8492"
          },
          {
            "cve_id": "CVE-2019-9513"
          },
          {
            "cve_id": "CVE-2019-9511"
          },
          {
            "cve_id": "CVE-2019-8907"
          },
          {
            "cve_id": "CVE-2018-16839"
          },
          {
            "cve_id": "CVE-2018-14567"
          },
          {
            "cve_id": "CVE-2018-14404"
          },
          {
            "cve_id": "CVE-2017-18258"
          },
          {
            "cve_id": "CVE-2018-0739"
          },
          {
            "cve_id": "CVE-2016-5131"
          },
          {
            "cve_id": "CVE-2015-8035"
          },
          {
            "cve_id": "CVE-2017-16997"
          },
          {
            "cve_id": "CVE-2019-12749"
          },
          {
            "cve_id": "CVE-2019-16935"
          },
          {
            "cve_id": "CVE-2018-5407"
          },
          {
            "cve_id": "CVE-2020-8177"
          },
          {
            "cve_id": "CVE-2019-20907"
          },
          {
            "cve_id": "CVE-2020-10531"
          },
          {
            "cve_id": "CVE-2019-18348"
          },
          {
            "cve_id": "CVE-2019-12290"
          },
          {
            "cve_id": "CVE-2019-18224"
          },
          {
            "cve_id": "CVE-2019-5482"
          },
          {
            "cve_id": "CVE-2019-5481"
          },
          {
            "cve_id": "CVE-2019-1563"
          },
          {
            "cve_id": "CVE-2019-16056"
          },
          {
            "cve_id": "CVE-2019-11729"
          },
          {
            "cve_id": "CVE-2018-20852"
          },
          {
            "cve_id": "CVE-2019-12450"
          },
          {
            "cve_id": "CVE-2019-5435"
          },
          {
            "cve_id": "CVE-2018-12404"
          },
          {
            "cve_id": "CVE-2019-1559"
          },
          {
            "cve_id": "CVE-2019-8906"
          },
          {
            "cve_id": "CVE-2019-8905"
          },
          {
            "cve_id": "CVE-2019-8904"
          },
          {
            "cve_id": "CVE-2016-10739"
          },
          {
            "cve_id": "CVE-2018-20217"
          },
          {
            "cve_id": "CVE-2018-20483"
          },
          {
            "cve_id": "CVE-2018-16840"
          },
          {
            "cve_id": "CVE-2018-0734"
          },
          {
            "cve_id": "CVE-2018-14618"
          },
          {
            "cve_id": "CVE-2017-15412"
          },
          {
            "cve_id": "CVE-2018-0500"
          },
          {
            "cve_id": "CVE-2018-0495"
          },
          {
            "cve_id": "CVE-2018-11237"
          },
          {
            "cve_id": "CVE-2018-5730"
          },
          {
            "cve_id": "CVE-2018-6485"
          },
          {
            "cve_id": "CVE-2017-3735"
          },
          {
            "cve_id": "CVE-2015-2716"
          },
          {
            "cve_id": "CVE-2019-11745"
          },
          {
            "cve_id": "CVE-2019-18218"
          },
          {
            "cve_id": "CVE-2019-5436"
          },
          {
            "cve_id": "CVE-2019-9924"
          },
          {
            "cve_id": "CVE-2018-11236"
          },
          {
            "cve_id": "CVE-2018-5729"
          },
          {
            "cve_id": "CVE-2018-16842"
          },
          {
            "cve_id": "CVE-2020-11080"
          },
          {
            "cve_id": "CVE-2020-8492"
          },
          {
            "cve_id": "CVE-2019-9513"
          },
          {
            "cve_id": "CVE-2019-9511"
          },
          {
            "cve_id": "CVE-2019-8907"
          },
          {
            "cve_id": "CVE-2018-16839"
          },
          {
            "cve_id": "CVE-2018-14567"
          },
          {
            "cve_id": "CVE-2018-14404"
          },
          {
            "cve_id": "CVE-2017-18258"
          },
          {
            "cve_id": "CVE-2018-0739"
          },
          {
            "cve_id": "CVE-2016-5131"
          },
          {
            "cve_id": "CVE-2015-8035"
          },
          {
            "cve_id": "CVE-2017-16997"
          },
          {
            "cve_id": "CVE-2019-6111"
          },
          {
            "cve_id": "CVE-2019-12749"
          },
          {
            "cve_id": "CVE-2018-20685"
          },
          {
            "cve_id": "CVE-2019-16935"
          },
          {
            "cve_id": "CVE-2018-5407"
          },
          {
            "cve_id": "CVE-2019-20907"
          },
          {
            "cve_id": "CVE-2020-10531"
          },
          {
            "cve_id": "CVE-2020-8177"
          },
          {
            "cve_id": "CVE-2019-18348"
          },
          {
            "cve_id": "CVE-2019-12290"
          },
          {
            "cve_id": "CVE-2019-18224"
          },
          {
            "cve_id": "CVE-2019-5482"
          },
          {
            "cve_id": "CVE-2019-5481"
          },
          {
            "cve_id": "CVE-2019-1563"
          },
          {
            "cve_id": "CVE-2019-16056"
          },
          {
            "cve_id": "CVE-2019-11729"
          },
          {
            "cve_id": "CVE-2018-20852"
          },
          {
            "cve_id": "CVE-2019-12450"
          },
          {
            "cve_id": "CVE-2019-5435"
          },
          {
            "cve_id": "CVE-2018-12404"
          },
          {
            "cve_id": "CVE-2019-1559"
          },
          {
            "cve_id": "CVE-2019-8906"
          },
          {
            "cve_id": "CVE-2019-8905"
          },
          {
            "cve_id": "CVE-2019-8904"
          },
          {
            "cve_id": "CVE-2019-6109"
          },
          {
            "cve_id": "CVE-2016-10739"
          },
          {
            "cve_id": "CVE-2018-20217"
          },
          {
            "cve_id": "CVE-2018-20483"
          },
          {
            "cve_id": "CVE-2018-16840"
          },
          {
            "cve_id": "CVE-2018-0734"
          },
          {
            "cve_id": "CVE-2018-14618"
          },
          {
            "cve_id": "CVE-2017-15412"
          },
          {
            "cve_id": "CVE-2018-0500"
          },
          {
            "cve_id": "CVE-2018-0495"
          },
          {
            "cve_id": "CVE-2018-11237"
          },
          {
            "cve_id": "CVE-2018-5730"
          },
          {
            "cve_id": "CVE-2018-6485"
          },
          {
            "cve_id": "CVE-2017-3735"
          },
          {
            "cve_id": "CVE-2015-2716"
          },
          {
            "cve_id": "CVE-2019-11745"
          },
          {
            "cve_id": "CVE-2019-18218"
          },
          {
            "cve_id": "CVE-2019-5436"
          },
          {
            "cve_id": "CVE-2019-9924"
          },
          {
            "cve_id": "CVE-2018-11236"
          },
          {
            "cve_id": "CVE-2018-5729"
          },
          {
            "cve_id": "CVE-2018-16842"
          },
          {
            "cve_id": "CVE-2020-11080"
          },
          {
            "cve_id": "CVE-2020-8492"
          },
          {
            "cve_id": "CVE-2019-9513"
          },
          {
            "cve_id": "CVE-2019-9511"
          },
          {
            "cve_id": "CVE-2019-8907"
          },
          {
            "cve_id": "CVE-2018-16839"
          },
          {
            "cve_id": "CVE-2018-14567"
          },
          {
            "cve_id": "CVE-2018-14404"
          },
          {
            "cve_id": "CVE-2017-18258"
          },
          {
            "cve_id": "CVE-2018-0739"
          },
          {
            "cve_id": "CVE-2016-5131"
          },
          {
            "cve_id": "CVE-2015-8035"
          },
          {
            "cve_id": "CVE-2017-16997"
          },
          {
            "cve_id": "CVE-2019-12749"
          },
          {
            "cve_id": "CVE-2019-16935"
          },
          {
            "cve_id": "CVE-2018-5407"
          },
          {
            "cve_id": "CVE-2020-8177"
          },
          {
            "cve_id": "CVE-2019-20907"
          },
          {
            "cve_id": "CVE-2020-10531"
          },
          {
            "cve_id": "CVE-2019-18348"
          },
          {
            "cve_id": "CVE-2019-12290"
          },
          {
            "cve_id": "CVE-2019-18224"
          },
          {
            "cve_id": "CVE-2019-5482"
          },
          {
            "cve_id": "CVE-2019-5481"
          },
          {
            "cve_id": "CVE-2019-1563"
          },
          {
            "cve_id": "CVE-2019-16056"
          },
          {
            "cve_id": "CVE-2019-11729"
          },
          {
            "cve_id": "CVE-2018-20852"
          },
          {
            "cve_id": "CVE-2019-12450"
          },
          {
            "cve_id": "CVE-2019-5435"
          },
          {
            "cve_id": "CVE-2019-8936"
          },
          {
            "cve_id": "CVE-2018-12404"
          },
          {
            "cve_id": "CVE-2019-1559"
          },
          {
            "cve_id": "CVE-2019-8906"
          },
          {
            "cve_id": "CVE-2019-8905"
          },
          {
            "cve_id": "CVE-2019-8904"
          },
          {
            "cve_id": "CVE-2016-10739"
          },
          {
            "cve_id": "CVE-2018-20217"
          },
          {
            "cve_id": "CVE-2018-20483"
          },
          {
            "cve_id": "CVE-2018-16840"
          },
          {
            "cve_id": "CVE-2018-0734"
          },
          {
            "cve_id": "CVE-2018-14618"
          },
          {
            "cve_id": "CVE-2017-15412"
          },
          {
            "cve_id": "CVE-2018-0500"
          },
          {
            "cve_id": "CVE-2018-0495"
          },
          {
            "cve_id": "CVE-2018-11237"
          },
          {
            "cve_id": "CVE-2018-5730"
          },
          {
            "cve_id": "CVE-2018-6485"
          },
          {
            "cve_id": "CVE-2017-3735"
          },
          {
            "cve_id": "CVE-2015-2716"
          },
          {
            "cve_id": "CVE-2019-11745"
          },
          {
            "cve_id": "CVE-2019-18218"
          },
          {
            "cve_id": "CVE-2019-5436"
          },
          {
            "cve_id": "CVE-2019-9924"
          },
          {
            "cve_id": "CVE-2018-11236"
          },
          {
            "cve_id": "CVE-2018-5729"
          },
          {
            "cve_id": "CVE-2018-16842"
          },
          {
            "cve_id": "CVE-2020-11080"
          },
          {
            "cve_id": "CVE-2020-8492"
          },
          {
            "cve_id": "CVE-2019-9516"
          },
          {
            "cve_id": "CVE-2019-9513"
          },
          {
            "cve_id": "CVE-2019-9511"
          },
          {
            "cve_id": "CVE-2019-8907"
          },
          {
            "cve_id": "CVE-2018-16839"
          },
          {
            "cve_id": "CVE-2018-14567"
          },
          {
            "cve_id": "CVE-2018-14404"
          },
          {
            "cve_id": "CVE-2017-18258"
          },
          {
            "cve_id": "CVE-2018-0739"
          },
          {
            "cve_id": "CVE-2016-5131"
          },
          {
            "cve_id": "CVE-2015-8035"
          },
          {
            "cve_id": "CVE-2017-16997"
          },
          {
            "cve_id": "CVE-2019-12749"
          },
          {
            "cve_id": "CVE-2019-16935"
          },
          {
            "cve_id": "CVE-2018-5407"
          },
          {
            "cve_id": "CVE-2020-8177"
          },
          {
            "cve_id": "CVE-2019-20907"
          },
          {
            "cve_id": "CVE-2020-10531"
          },
          {
            "cve_id": "CVE-2019-18348"
          },
          {
            "cve_id": "CVE-2019-12290"
          },
          {
            "cve_id": "CVE-2019-18224"
          },
          {
            "cve_id": "CVE-2019-5482"
          },
          {
            "cve_id": "CVE-2019-5481"
          },
          {
            "cve_id": "CVE-2019-1563"
          },
          {
            "cve_id": "CVE-2019-16056"
          },
          {
            "cve_id": "CVE-2019-11729"
          },
          {
            "cve_id": "CVE-2018-20852"
          },
          {
            "cve_id": "CVE-2019-12450"
          },
          {
            "cve_id": "CVE-2019-5435"
          },
          {
            "cve_id": "CVE-2018-12404"
          },
          {
            "cve_id": "CVE-2019-1559"
          },
          {
            "cve_id": "CVE-2019-8906"
          },
          {
            "cve_id": "CVE-2019-8905"
          },
          {
            "cve_id": "CVE-2019-8904"
          },
          {
            "cve_id": "CVE-2016-10739"
          },
          {
            "cve_id": "CVE-2018-20217"
          },
          {
            "cve_id": "CVE-2018-20483"
          },
          {
            "cve_id": "CVE-2018-16844"
          },
          {
            "cve_id": "CVE-2018-16843"
          },
          {
            "cve_id": "CVE-2018-16840"
          },
          {
            "cve_id": "CVE-2018-0734"
          },
          {
            "cve_id": "CVE-2018-14618"
          },
          {
            "cve_id": "CVE-2017-15412"
          },
          {
            "cve_id": "CVE-2018-0500"
          },
          {
            "cve_id": "CVE-2018-0495"
          },
          {
            "cve_id": "CVE-2018-11237"
          },
          {
            "cve_id": "CVE-2018-5730"
          },
          {
            "cve_id": "CVE-2018-6485"
          },
          {
            "cve_id": "CVE-2017-3735"
          }
        ],
        "alerts_data": [
          {
            "alert_type": "Web-service unpatched",
            "description": "The web-service nginx 1.12.1 that was found on the asset, was not patched for several months. This can lead to multiple security concerns, including potential remote code execution and denial of service",
            "details": "We have found that the web-service nginx 1.12.1 on the system was not patched for several months. It is important to keep the web-service up to date as it can be one of the main attack vectors into your system. Even if it is not possible to gain remote access to it, scenarios of denial of service and service downtime are likely to be applicable in such cases and so it is strongly advised to patch or update the service",
            "recommendation": "Patch the web-service nginx 1.12.1 or upgrade its version",
            "alert_labels": [
              "remote_code_execution",
              "internet_facing_service"
            ],
            "alert_state": {
              "alert_status": "in_progress",
              "alert_status_time": "2020-06-19 17:15:27",
              "alert_created_at": "2020-06-19 17:15:27",
              "alert_severity": "imminent compromise",
              "alert_last_seen": "2020-10-25 22:04:46",
              "alert_score": "2",
              "alert_high_since": "2020-06-19 17:15:27"
            },
            "alert_source": "nginx 1.12.1"
          },
          {
            "alert_type": "Service Vulnerability",
            "description": "The following vulnerabilities were found on Internet facing service: kernel 4.14.77",
            "details": "We have found vulnerabilities on Internet facing service: kernel 4.14.77",
            "recommendation": "Patch the listed packages",
            "alert_labels": [
              "denial_of_service",
              "remote_code_execution",
              "internet_facing_service"
            ],
            "alert_state": {
              "alert_status": "in_progress",
              "alert_status_time": "2020-03-15 22:28:14",
              "alert_created_at": "2020-03-15 22:28:14",
              "alert_severity": "hazardous",
              "alert_last_seen": "2020-10-25 22:04:46",
              "alert_score": "3",
              "alert_high_since": "2020-06-18 06:57:33"
            },
            "alert_source": "kernel (Internet facing)"
          },
          {
            "alert_type": "Service Vulnerability",
            "description": "The following vulnerabilities were found on service: sendmail 8.14.4",
            "details": "We have found vulnerabilities on service: sendmail 8.14.4",
            "recommendation": "Patch the listed packages",
            "alert_labels": [
              "remote_code_execution"
            ],
            "alert_state": {
              "alert_status": "in_progress",
              "alert_status_time": "2020-03-04 08:40:23",
              "alert_created_at": "2020-03-04 08:40:23",
              "alert_severity": "hazardous",
              "alert_last_seen": "2020-10-25 22:04:46",
              "alert_score": "3",
              "alert_high_since": "2020-06-18 06:57:33"
            },
            "alert_source": "sendmail"
          },
          {
            "alert_type": "Service Vulnerability",
            "description": "The following vulnerabilities were found on service: sshd 7.4p1",
            "details": "We have found vulnerabilities on service: sshd 7.4p1",
            "recommendation": "Patch the listed packages",
            "alert_labels": [
              "remote_code_execution"
            ],
            "alert_state": {
              "alert_status": "in_progress",
              "alert_status_time": "2020-03-04 08:40:23",
              "alert_created_at": "2020-03-04 08:40:23",
              "alert_severity": "hazardous",
              "alert_last_seen": "2020-10-25 22:04:46",
              "alert_score": "3",
              "alert_high_since": "2020-06-18 06:57:33"
            },
            "alert_source": "sshd"
          },
          {
            "alert_type": "Sensitive Info in Git Repository",
            "description": "The system contains a local git repository",
            "details": "We have found a local git repository which may hold sensitive code & secret keys",
            "recommendation": "Remove the repository from the system",
            "alert_state": {
              "alert_status": "in_progress",
              "alert_status_time": "2020-03-04 08:40:23",
              "alert_created_at": "2020-03-04 08:40:23",
              "alert_severity": "hazardous",
              "alert_last_seen": "2020-10-25 22:04:46",
              "alert_score": "3",
              "alert_high_since": "2020-03-04 08:40:23"
            }
          },
          {
            "alert_type": "Service Vulnerability",
            "description": "The following vulnerabilities were found on service: ntpd 4.2.8p12",
            "details": "We have found vulnerabilities on service: ntpd 4.2.8p12",
            "recommendation": "Patch the listed packages",
            "alert_labels": [
              "remote_code_execution"
            ],
            "alert_state": {
              "alert_status": "open",
              "alert_status_time": "2020-03-04 08:40:23",
              "alert_created_at": "2020-03-04 08:40:23",
              "alert_severity": "hazardous",
              "alert_last_seen": "2020-10-25 22:04:46",
              "alert_score": "3",
              "alert_high_since": "2020-06-18 06:57:33"
            },
            "alert_source": "ntpd"
          },
          {
            "alert_type": "Service Vulnerability",
            "description": "The following vulnerabilities were found on Internet facing service: nginx 1.12.1",
            "details": "We have found vulnerabilities on Internet facing service: nginx 1.12.1",
            "recommendation": "Patch the listed packages",
            "alert_labels": [
              "remote_code_execution",
              "internet_facing_service"
            ],
            "alert_state": {
              "alert_status": "open",
              "alert_status_time": "2020-03-04 08:40:23",
              "alert_created_at": "2020-03-04 08:40:23",
              "alert_severity": "hazardous",
              "alert_last_seen": "2020-10-25 22:04:46",
              "alert_score": "3",
              "alert_high_since": "2020-06-18 06:57:33"
            },
            "alert_source": "nginx (Internet facing)"
          }
        ],
        "asset_labels": [
          "internet_facing"
        ],
        "asset_state": "running",
        "tags": [
          {
            "tag_key": "Name",
            "tag_value": "Web-Nginx"
          }
        ],
        "asset_type": "vm",
        "first_seen": "2019-11-03 07:39:24",
        "last_seen": "2020-10-25 22:41:48",
        "asset_score": 2,
        "asset_severity": "imminent compromise",
        "asset_status": "exists",
        "status_time": "2019-11-03 07:39:24",
        "connected_devices": [],
        "fetch_time": "2020-10-26 14:36:20",
        "adapter_properties": [
          "Vulnerability_Assessment"
        ],
        "first_fetch_time": "2020-10-26 14:36:20",
        "pretty_id": "AX-31"
      }
    ],
    "fields": [
      "adapters",
      "adapter_list_length",
      "internal_axon_id",
      "name",
      "hostname",
      "description",
      "first_seen",
      "last_seen",
      "fetch_time",
      "first_fetch_time",
      "network_interfaces",
      "network_interfaces.name",
      "network_interfaces.mac",
      "network_interfaces.manufacturer",
      "network_interfaces.ips",
      "network_interfaces.ips_v4",
      "network_interfaces.ips_v6",
      "network_interfaces.subnets",
      "network_interfaces.vlan_list",
      "network_interfaces.vlan_list.name",
      "network_interfaces.vlan_list.tagid",
      "network_interfaces.vlan_list.tagness",
      "network_interfaces.operational_status",
      "network_interfaces.admin_status",
      "network_interfaces.speed",
      "network_interfaces.port_type",
      "network_interfaces.mtu",
      "network_interfaces.gateway",
      "network_interfaces.port",
      "network_interfaces.locations",
      "network_interfaces.location_id",
      "network_interfaces.facility_name",
      "network_interfaces.facility_id",
      "network_interfaces.region",
      "network_interfaces.zone",
      "network_interfaces.country",
      "network_interfaces.state",
      "network_interfaces.city",
      "network_interfaces.postal_code",
      "network_interfaces.street_address",
      "network_interfaces.full_address",
      "network_interfaces.latitude",
      "network_interfaces.longitude",
      "network_interfaces.ad_sitename",
      "network_interfaces.ad_sitecode",
      "network_interfaces.gsc_sitecode",
      "network_interfaces.talentlink_sitecode",
      "network_interfaces.site_criticality",
      "network_interfaces.site_function",
      "network_interfaces.security_level",
      "network_interfaces.comments",
      "os.type",
      "os.distribution",
      "os.type_distribution",
      "os.is_windows_server",
      "os.os_str",
      "os.bitness",
      "os.sp",
      "os.install_date",
      "os.kernel_version",
      "os.codename",
      "os.major",
      "os.minor",
      "os.build",
      "os.serial",
      "last_used_users",
      "last_used_users_ad_display_name_association",
      "last_used_users_mail_association",
      "last_used_users_organizational_unit_association",
      "last_used_users_description_association",
      "installed_software",
      "installed_software.name",
      "installed_software.version",
      "installed_software.name_version",
      "installed_software.major_version",
      "installed_software.major_minor_version",
      "installed_software.architecture",
      "installed_software.description",
      "installed_software.vendor",
      "installed_software.publisher",
      "installed_software.cve_count",
      "installed_software.sw_license",
      "installed_software.path",
      "installed_software.source",
      "software_cves",
      "software_cves.cve_id",
      "software_cves.software_name",
      "software_cves.software_version",
      "software_cves.software_vendor",
      "software_cves.cvss_version",
      "software_cves.cvss",
      "software_cves.cvss_str",
      "software_cves.cve_severity",
      "software_cves.cve_description",
      "software_cves.cve_synopsis",
      "security_patches",
      "security_patches.security_patch_id",
      "security_patches.installed_on",
      "security_patches.patch_description",
      "security_patches.classification",
      "security_patches.state",
      "security_patches.severity",
      "security_patches.bulletin_id",
      "connected_hardware",
      "connected_hardware.name",
      "connected_hardware.manufacturer",
      "connected_hardware.hw_id",
      "connected_devices",
      "connected_devices.remote_name",
      "connected_devices.local_ifaces",
      "connected_devices.local_ifaces.name",
      "connected_devices.local_ifaces.mac",
      "connected_devices.local_ifaces.manufacturer",
      "connected_devices.local_ifaces.ips",
      "connected_devices.local_ifaces.ips_v4",
      "connected_devices.local_ifaces.ips_v6",
      "connected_devices.local_ifaces.subnets",
      "connected_devices.local_ifaces.vlan_list",
      "connected_devices.local_ifaces.vlan_list.name",
      "connected_devices.local_ifaces.vlan_list.tagid",
      "connected_devices.local_ifaces.vlan_list.tagness",
      "connected_devices.local_ifaces.operational_status",
      "connected_devices.local_ifaces.admin_status",
      "connected_devices.local_ifaces.speed",
      "connected_devices.local_ifaces.port_type",
      "connected_devices.local_ifaces.mtu",
      "connected_devices.local_ifaces.gateway",
      "connected_devices.local_ifaces.port",
      "connected_devices.local_ifaces.locations",
      "connected_devices.local_ifaces.location_id",
      "connected_devices.local_ifaces.facility_name",
      "connected_devices.local_ifaces.facility_id",
      "connected_devices.local_ifaces.region",
      "connected_devices.local_ifaces.zone",
      "connected_devices.local_ifaces.country",
      "connected_devices.local_ifaces.state",
      "connected_devices.local_ifaces.city",
      "connected_devices.local_ifaces.postal_code",
      "connected_devices.local_ifaces.street_address",
      "connected_devices.local_ifaces.full_address",
      "connected_devices.local_ifaces.latitude",
      "connected_devices.local_ifaces.longitude",
      "connected_devices.local_ifaces.ad_sitename",
      "connected_devices.local_ifaces.ad_sitecode",
      "connected_devices.local_ifaces.gsc_sitecode",
      "connected_devices.local_ifaces.talentlink_sitecode",
      "connected_devices.local_ifaces.site_criticality",
      "connected_devices.local_ifaces.site_function",
      "connected_devices.local_ifaces.security_level",
      "connected_devices.local_ifaces.comments",
      "connected_devices.remote_ifaces",
      "connected_devices.remote_ifaces.name",
      "connected_devices.remote_ifaces.mac",
      "connected_devices.remote_ifaces.manufacturer",
      "connected_devices.remote_ifaces.ips",
      "connected_devices.remote_ifaces.ips_v4",
      "connected_devices.remote_ifaces.ips_v6",
      "connected_devices.remote_ifaces.subnets",
      "connected_devices.remote_ifaces.vlan_list",
      "connected_devices.remote_ifaces.vlan_list.name",
      "connected_devices.remote_ifaces.vlan_list.tagid",
      "connected_devices.remote_ifaces.vlan_list.tagness",
      "connected_devices.remote_ifaces.operational_status",
      "connected_devices.remote_ifaces.admin_status",
      "connected_devices.remote_ifaces.speed",
      "connected_devices.remote_ifaces.port_type",
      "connected_devices.remote_ifaces.mtu",
      "connected_devices.remote_ifaces.gateway",
      "connected_devices.remote_ifaces.port",
      "connected_devices.remote_ifaces.locations",
      "connected_devices.remote_ifaces.location_id",
      "connected_devices.remote_ifaces.facility_name",
      "connected_devices.remote_ifaces.facility_id",
      "connected_devices.remote_ifaces.region",
      "connected_devices.remote_ifaces.zone",
      "connected_devices.remote_ifaces.country",
      "connected_devices.remote_ifaces.state",
      "connected_devices.remote_ifaces.city",
      "connected_devices.remote_ifaces.postal_code",
      "connected_devices.remote_ifaces.street_address",
      "connected_devices.remote_ifaces.full_address",
      "connected_devices.remote_ifaces.latitude",
      "connected_devices.remote_ifaces.longitude",
      "connected_devices.remote_ifaces.ad_sitename",
      "connected_devices.remote_ifaces.ad_sitecode",
      "connected_devices.remote_ifaces.gsc_sitecode",
      "connected_devices.remote_ifaces.talentlink_sitecode",
      "connected_devices.remote_ifaces.site_criticality",
      "connected_devices.remote_ifaces.site_function",
      "connected_devices.remote_ifaces.security_level",
      "connected_devices.remote_ifaces.comments",
      "connected_devices.connection_type",
      "id",
      "part_of_domain",
      "domain",
      "users",
      "users.user_sid",
      "users.username",
      "users.last_use_date",
      "users.is_local",
      "users.is_disabled",
      "users.is_admin",
      "users.user_department",
      "users.password_max_age",
      "users.interpreter",
      "local_admins",
      "local_admins.admin_name",
      "local_admins.admin_type",
      "local_admins_users",
      "local_admins_groups",
      "pretty_id",
      "agent_versions",
      "agent_versions.adapter_name",
      "agent_versions.agent_version",
      "agent_versions.agent_status",
      "pc_type",
      "number_of_processes",
      "hard_drives",
      "hard_drives.path",
      "hard_drives.device",
      "hard_drives.file_system",
      "hard_drives.total_size",
      "hard_drives.free_size",
      "hard_drives.is_encrypted",
      "hard_drives.description",
      "hard_drives.serial_number",
      "cpus",
      "cpus.name",
      "cpus.manufacturer",
      "cpus.bitness",
      "cpus.family",
      "cpus.cores",
      "cpus.cores_thread",
      "cpus.load_percentage",
      "cpus.architecture",
      "cpus.ghz",
      "time_zone",
      "boot_time",
      "uptime",
      "device_manufacturer",
      "device_model",
      "device_serial",
      "bios_version",
      "bios_serial",
      "total_physical_memory",
      "free_physical_memory",
      "physical_memory_percentage",
      "total_number_of_physical_processors",
      "total_number_of_cores",
      "device_disabled",
      "device_managed_by",
      "organizational_unit",
      "tags",
      "tags.tag_key",
      "tags.tag_value",
      "cloud_provider",
      "cloud_id",
      "processes",
      "processes.name",
      "services",
      "services.name",
      "services.display_name",
      "services.state",
      "services.status",
      "services.start_name",
      "services.start_mode",
      "services.path_name",
      "services.description",
      "services.caption",
      "services.service_type",
      "shares",
      "shares.name",
      "shares.description",
      "shares.path",
      "shares.status",
      "adapter_properties",
      "uuid",
      "labels",
      "correlation_reasons",
      "has_notes",
      "hostname_preferred",
      "os.type_preferred",
      "os.distribution_preferred",
      "os.os_str_preferred",
      "os.bitness_preferred",
      "os.kernel_version_preferred",
      "os.build_preferred",
      "network_interfaces.mac_preferred",
      "network_interfaces.locations_preferred",
      "network_interfaces.ips_preferred",
      "device_model_preferred",
      "domain_preferred"
    ],
    "additional_schema": [
      {
        "filterable": true,
        "name": "asset_type",
        "title": "Asset Type",
        "type": "string"
      },
      {
        "filterable": true,
        "name": "asset_state",
        "title": "Asset State",
        "type": "string"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "asset_labels",
        "title": "Asset Labels",
        "type": "array"
      },
      {
        "filterable": true,
        "name": "asset_score",
        "title": "Asset Score",
        "type": "integer"
      },
      {
        "filterable": true,
        "name": "asset_severity",
        "title": "Asset Severity",
        "type": "string"
      },
      {
        "filterable": true,
        "name": "asset_status",
        "title": "Asset Status",
        "type": "string"
      },
      {
        "filterable": false,
        "format": "date-time",
        "name": "status_time",
        "title": "Status Time",
        "type": "string"
      },
      {
        "filterable": true,
        "items": {
          "items": [
            {
              "name": "alert_id",
              "title": "Alert Id",
              "type": "string"
            },
            {
              "name": "score",
              "title": "Score",
              "type": "integer"
            },
            {
              "name": "alert_type",
              "title": "Alert Type",
              "type": "string"
            },
            {
              "name": "description",
              "title": "Description",
              "type": "string"
            },
            {
              "name": "details",
              "title": "Details",
              "type": "string"
            },
            {
              "name": "recommendation",
              "title": "Recommendation",
              "type": "string"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "alert_labels",
              "title": "Alert Labels",
              "type": "array"
            },
            {
              "name": "alert_state.alert_status",
              "title": "Alert State: Status",
              "type": "string"
            },
            {
              "format": "date-time",
              "name": "alert_state.alert_status_time",
              "title": "Alert State: Status Time",
              "type": "string"
            },
            {
              "format": "date-time",
              "name": "alert_state.alert_created_at",
              "title": "Alert State: Created At",
              "type": "string"
            },
            {
              "name": "alert_state.alert_severity",
              "title": "Alert State: Severity",
              "type": "string"
            },
            {
              "format": "date-time",
              "name": "alert_state.alert_last_seen",
              "title": "Alert State: Last Seen",
              "type": "string"
            },
            {
              "name": "alert_state.alert_score",
              "title": "Alert State: Score",
              "type": "string"
            },
            {
              "name": "alert_state.alert_low_reason",
              "title": "Alert State: Low Reason",
              "type": "string"
            },
            {
              "format": "date-time",
              "name": "alert_state.alert_low_since",
              "title": "Alert State: low_since",
              "type": "string"
            },
            {
              "format": "date-time",
              "name": "alert_state.alert_high_since",
              "title": "Alert State: high_since",
              "type": "string"
            },
            {
              "name": "alert_source",
              "title": "Alert Source",
              "type": "string"
            }
          ],
          "type": "array"
        },
        "name": "alerts_data",
        "title": "Alerts Data",
        "type": "array"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "alerts_data.alert_id",
        "title": "Alerts Data: Alert Id",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "alerts_data.score",
        "title": "Alerts Data: Score",
        "type": "integer"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "alerts_data.alert_type",
        "title": "Alerts Data: Alert Type",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "alerts_data.description",
        "title": "Alerts Data: Description",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "alerts_data.details",
        "title": "Alerts Data: Details",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "alerts_data.recommendation",
        "title": "Alerts Data: Recommendation",
        "type": "string"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "alerts_data.alert_labels",
        "title": "Alerts Data: Alert Labels",
        "type": "array"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "alerts_data.alert_state.alert_status",
        "title": "Alerts Data: Alert State: Status",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": false,
        "format": "date-time",
        "name": "alerts_data.alert_state.alert_status_time",
        "title": "Alerts Data: Alert State: Status Time",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": false,
        "format": "date-time",
        "name": "alerts_data.alert_state.alert_created_at",
        "title": "Alerts Data: Alert State: Created At",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "alerts_data.alert_state.alert_severity",
        "title": "Alerts Data: Alert State: Severity",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": false,
        "format": "date-time",
        "name": "alerts_data.alert_state.alert_last_seen",
        "title": "Alerts Data: Alert State: Last Seen",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "alerts_data.alert_state.alert_score",
        "title": "Alerts Data: Alert State: Score",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "alerts_data.alert_state.alert_low_reason",
        "title": "Alerts Data: Alert State: Low Reason",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": false,
        "format": "date-time",
        "name": "alerts_data.alert_state.alert_low_since",
        "title": "Alerts Data: Alert State: low_since",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": false,
        "format": "date-time",
        "name": "alerts_data.alert_state.alert_high_since",
        "title": "Alerts Data: Alert State: high_since",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "alerts_data.alert_source",
        "title": "Alerts Data: Alert Source",
        "type": "string"
      },
      {
        "filterable": true,
        "items": {
          "items": [
            {
              "items": {
                "type": "string"
              },
              "name": "virus_names",
              "title": "Virus Names",
              "type": "array"
            },
            {
              "name": "file",
              "title": "File",
              "type": "string"
            },
            {
              "name": "md5",
              "title": "MD5",
              "type": "string"
            },
            {
              "name": "sha1",
              "title": "SHA1",
              "type": "string"
            },
            {
              "name": "sha256",
              "title": "SHA256",
              "type": "string"
            },
            {
              "format": "date-time",
              "name": "modification_time",
              "title": "Modification Time",
              "type": "string"
            }
          ],
          "type": "array"
        },
        "name": "malware_data",
        "title": "Malware Data",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "malware_data.virus_names",
        "title": "Malware Data: Virus Names",
        "type": "array"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "malware_data.file",
        "title": "Malware Data: File",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "malware_data.md5",
        "title": "Malware Data: MD5",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "malware_data.sha1",
        "title": "Malware Data: SHA1",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "malware_data.sha256",
        "title": "Malware Data: SHA256",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": false,
        "format": "date-time",
        "name": "malware_data.modification_time",
        "title": "Malware Data: Modification Time",
        "type": "string"
      },
      {
        "filterable": true,
        "items": {
          "items": [
            {
              "format": "date-time",
              "name": "log_time",
              "title": "Login Time",
              "type": "string"
            },
            {
              "format": "date-time",
              "name": "logout_time",
              "title": "Logout Time",
              "type": "string"
            },
            {
              "name": "source_ipv4",
              "title": "Source IPv4",
              "type": "string"
            },
            {
              "name": "username",
              "title": "Username",
              "type": "string"
            }
          ],
          "type": "array"
        },
        "name": "failed_logins",
        "title": "Failed Logins",
        "type": "array"
      },
      {
        "branched": true,
        "filterable": false,
        "format": "date-time",
        "name": "failed_logins.log_time",
        "title": "Failed Logins: Login Time",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": false,
        "format": "date-time",
        "name": "failed_logins.logout_time",
        "title": "Failed Logins: Logout Time",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "failed_logins.source_ipv4",
        "title": "Failed Logins: Source IPv4",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "failed_logins.username",
        "title": "Failed Logins: Username",
        "type": "string"
      },
      {
        "filterable": true,
        "items": {
          "items": [
            {
              "format": "date-time",
              "name": "log_time",
              "title": "Login Time",
              "type": "string"
            },
            {
              "format": "date-time",
              "name": "logout_time",
              "title": "Logout Time",
              "type": "string"
            },
            {
              "name": "source_ipv4",
              "title": "Source IPv4",
              "type": "string"
            },
            {
              "name": "username",
              "title": "Username",
              "type": "string"
            }
          ],
          "type": "array"
        },
        "name": "successful_logins",
        "title": "Successful Logins",
        "type": "array"
      },
      {
        "branched": true,
        "filterable": false,
        "format": "date-time",
        "name": "successful_logins.log_time",
        "title": "Successful Logins: Login Time",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": false,
        "format": "date-time",
        "name": "successful_logins.logout_time",
        "title": "Successful Logins: Logout Time",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "successful_logins.source_ipv4",
        "title": "Successful Logins: Source IPv4",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "successful_logins.username",
        "title": "Successful Logins: Username",
        "type": "string"
      },
      {
        "filterable": true,
        "items": {
          "items": [
            {
              "name": "category",
              "title": "Category",
              "type": "string"
            },
            {
              "name": "description",
              "title": "Description",
              "type": "string"
            },
            {
              "name": "os",
              "title": "OS",
              "type": "string"
            },
            {
              "name": "result",
              "title": "Result",
              "type": "string"
            },
            {
              "name": "scored",
              "title": "Scored",
              "type": "bool"
            },
            {
              "name": "subcategory",
              "title": "Subcategory",
              "type": "string"
            },
            {
              "name": "test_name",
              "title": "Test Name",
              "type": "string"
            },
            {
              "name": "version",
              "title": "Version",
              "type": "string"
            }
          ],
          "type": "array"
        },
        "name": "compliance_information",
        "title": "Compliance Infomation",
        "type": "array"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "compliance_information.category",
        "title": "Compliance Infomation: Category",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "compliance_information.description",
        "title": "Compliance Infomation: Description",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "compliance_information.os",
        "title": "Compliance Infomation: OS",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "compliance_information.result",
        "title": "Compliance Infomation: Result",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "compliance_information.scored",
        "title": "Compliance Infomation: Scored",
        "type": "bool"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "compliance_information.subcategory",
        "title": "Compliance Infomation: Subcategory",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "compliance_information.test_name",
        "title": "Compliance Infomation: Test Name",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "compliance_information.version",
        "title": "Compliance Infomation: Version",
        "type": "string"
      },
      {
        "filterable": true,
        "items": {
          "items": [
            {
              "name": "local_name",
              "title": "Local Name",
              "type": "string"
            },
            {
              "name": "path",
              "title": "Path",
              "type": "string"
            },
            {
              "name": "size",
              "title": "Size",
              "type": "integer"
            },
            {
              "name": "url",
              "title": "URL",
              "type": "string"
            }
          ],
          "type": "array"
        },
        "name": "git_repos",
        "title": "Git Repositories",
        "type": "array"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "git_repos.local_name",
        "title": "Git Repositories: Local Name",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "git_repos.path",
        "title": "Git Repositories: Path",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "git_repos.size",
        "title": "Git Repositories: Size",
        "type": "integer"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "git_repos.url",
        "title": "Git Repositories: URL",
        "type": "string"
      },
      {
        "filterable": true,
        "items": {
          "items": [
            {
              "name": "db_path",
              "title": "DB Path",
              "type": "string"
            },
            {
              "name": "db_size",
              "title": "DB Size",
              "type": "integer"
            },
            {
              "format": "date-time",
              "name": "last_accessed_time",
              "title": "Last Accessed Time",
              "type": "string"
            },
            {
              "format": "date-time",
              "name": "last_modified_time",
              "title": "Last Modified Time",
              "type": "string"
            },
            {
              "name": "type",
              "title": "Type",
              "type": "string"
            }
          ],
          "type": "array"
        },
        "name": "orca_dbs",
        "title": "Databases",
        "type": "array"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "orca_dbs.db_path",
        "title": "Databases: DB Path",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "orca_dbs.db_size",
        "title": "Databases: DB Size",
        "type": "integer"
      },
      {
        "branched": true,
        "filterable": false,
        "format": "date-time",
        "name": "orca_dbs.last_accessed_time",
        "title": "Databases: Last Accessed Time",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": false,
        "format": "date-time",
        "name": "orca_dbs.last_modified_time",
        "title": "Databases: Last Modified Time",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "orca_dbs.type",
        "title": "Databases: Type",
        "type": "string"
      },
      {
        "filterable": true,
        "name": "name",
        "title": "Asset Name",
        "type": "string"
      },
      {
        "filterable": false,
        "format": "date-time",
        "name": "first_seen",
        "title": "First Seen",
        "type": "string"
      },
      {
        "filterable": false,
        "format": "date-time",
        "name": "last_seen",
        "title": "Last Seen",
        "type": "string"
      },
      {
        "filterable": false,
        "format": "date-time",
        "name": "fetch_time",
        "title": "Fetch Time",
        "type": "string"
      },
      {
        "filterable": false,
        "format": "date-time",
        "name": "first_fetch_time",
        "title": "First Fetch Time",
        "type": "string"
      },
      {
        "filterable": true,
        "format": "table",
        "items": {
          "items": [
            {
              "name": "name",
              "title": "Software Name",
              "type": "string"
            },
            {
              "format": "version",
              "name": "version",
              "title": "Software Version",
              "type": "string"
            },
            {
              "name": "name_version",
              "title": "Software Name and Version",
              "type": "string"
            },
            {
              "name": "major_version",
              "title": "Major Software Version",
              "type": "string"
            },
            {
              "name": "major_minor_version",
              "title": "Major/Minor Software Version",
              "type": "string"
            },
            {
              "enum": [
                "x86",
                "x64",
                "MIPS",
                "Alpha",
                "PowerPC",
                "ARM",
                "ia64",
                "all",
                "i686"
              ],
              "name": "architecture",
              "title": "Software Architecture",
              "type": "string"
            },
            {
              "name": "description",
              "title": "Software Description",
              "type": "string"
            },
            {
              "name": "vendor",
              "title": "Software Vendor",
              "type": "string"
            },
            {
              "name": "publisher",
              "title": "Software Publisher",
              "type": "string"
            },
            {
              "name": "cve_count",
              "title": "CVE Count",
              "type": "string"
            },
            {
              "name": "sw_license",
              "title": "License",
              "type": "string"
            },
            {
              "name": "path",
              "title": "Software Path",
              "type": "string"
            },
            {
              "name": "source",
              "title": "Source",
              "type": "string"
            }
          ],
          "type": "array"
        },
        "name": "installed_software",
        "title": "Installed Software",
        "type": "array"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "installed_software.name",
        "title": "Installed Software: Software Name",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "format": "version",
        "name": "installed_software.version",
        "title": "Installed Software: Software Version",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "installed_software.name_version",
        "title": "Installed Software: Software Name and Version",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "installed_software.major_version",
        "title": "Installed Software: Major Software Version",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "installed_software.major_minor_version",
        "title": "Installed Software: Major/Minor Software Version",
        "type": "string"
      },
      {
        "branched": true,
        "enum": [
          "x86",
          "x64",
          "MIPS",
          "Alpha",
          "PowerPC",
          "ARM",
          "ia64",
          "all",
          "i686"
        ],
        "filterable": true,
        "name": "installed_software.architecture",
        "title": "Installed Software: Software Architecture",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "installed_software.description",
        "title": "Installed Software: Software Description",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "installed_software.vendor",
        "title": "Installed Software: Software Vendor",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "installed_software.publisher",
        "title": "Installed Software: Software Publisher",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "installed_software.cve_count",
        "title": "Installed Software: CVE Count",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "installed_software.sw_license",
        "title": "Installed Software: License",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "installed_software.path",
        "title": "Installed Software: Software Path",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "installed_software.source",
        "title": "Installed Software: Source",
        "type": "string"
      },
      {
        "filterable": true,
        "format": "table",
        "items": {
          "items": [
            {
              "name": "cve_id",
              "title": "CVE ID",
              "type": "string"
            },
            {
              "name": "software_name",
              "title": "Software Name",
              "type": "string"
            },
            {
              "format": "version",
              "name": "software_version",
              "title": "Software Version",
              "type": "string"
            },
            {
              "name": "software_vendor",
              "title": "Software Vendor",
              "type": "string"
            },
            {
              "enum": [
                "v2.0",
                "v3.0"
              ],
              "name": "cvss_version",
              "title": "CVSS Version",
              "type": "string"
            },
            {
              "name": "cvss",
              "title": "CVSS",
              "type": "number"
            },
            {
              "name": "cvss_str",
              "title": "CVSS String",
              "type": "string"
            },
            {
              "enum": [
                "NONE",
                "LOW",
                "MEDIUM",
                "HIGH",
                "CRITICAL"
              ],
              "name": "cve_severity",
              "title": "CVE Severity",
              "type": "string"
            },
            {
              "name": "cve_description",
              "title": "CVE Description",
              "type": "string"
            },
            {
              "name": "cve_synopsis",
              "title": "CVE Synopsis",
              "type": "string"
            }
          ],
          "type": "array"
        },
        "name": "software_cves",
        "title": "Vulnerable Software",
        "type": "array"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "software_cves.cve_id",
        "title": "Vulnerable Software: CVE ID",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "software_cves.software_name",
        "title": "Vulnerable Software: Software Name",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "format": "version",
        "name": "software_cves.software_version",
        "title": "Vulnerable Software: Software Version",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "software_cves.software_vendor",
        "title": "Vulnerable Software: Software Vendor",
        "type": "string"
      },
      {
        "branched": true,
        "enum": [
          "v2.0",
          "v3.0"
        ],
        "filterable": true,
        "name": "software_cves.cvss_version",
        "title": "Vulnerable Software: CVSS Version",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "software_cves.cvss",
        "title": "Vulnerable Software: CVSS",
        "type": "number"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "software_cves.cvss_str",
        "title": "Vulnerable Software: CVSS String",
        "type": "string"
      },
      {
        "branched": true,
        "enum": [
          "NONE",
          "LOW",
          "MEDIUM",
          "HIGH",
          "CRITICAL"
        ],
        "filterable": true,
        "name": "software_cves.cve_severity",
        "title": "Vulnerable Software: CVE Severity",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "software_cves.cve_description",
        "title": "Vulnerable Software: CVE Description",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "software_cves.cve_synopsis",
        "title": "Vulnerable Software: CVE Synopsis",
        "type": "string"
      },
      {
        "filterable": true,
        "format": "table",
        "items": {
          "items": [
            {
              "name": "remote_name",
              "title": "Remote Device Name",
              "type": "string"
            },
            {
              "items": {
                "items": [
                  {
                    "name": "name",
                    "title": "Iface Name",
                    "type": "string"
                  },
                  {
                    "name": "mac",
                    "title": "MAC",
                    "type": "string"
                  },
                  {
                    "name": "manufacturer",
                    "title": "Manufacturer",
                    "type": "string"
                  },
                  {
                    "format": "ip",
                    "items": {
                      "format": "ip",
                      "type": "string"
                    },
                    "name": "ips",
                    "title": "IPs",
                    "type": "array"
                  },
                  {
                    "format": "ip",
                    "items": {
                      "format": "ip",
                      "type": "string"
                    },
                    "name": "ips_v4",
                    "title": "IPv4s",
                    "type": "array"
                  },
                  {
                    "format": "ip",
                    "items": {
                      "format": "ip",
                      "type": "string"
                    },
                    "name": "ips_v6",
                    "title": "IPv6s",
                    "type": "array"
                  },
                  {
                    "description": "A list of subnets in ip format, that correspond the IPs",
                    "format": "subnet",
                    "items": {
                      "format": "subnet",
                      "type": "string"
                    },
                    "name": "subnets",
                    "title": "Subnets",
                    "type": "array"
                  },
                  {
                    "description": "A list of vlans in this interface",
                    "items": {
                      "items": [
                        {
                          "name": "name",
                          "title": "Vlan Name",
                          "type": "string"
                        },
                        {
                          "name": "tagid",
                          "title": "Tag ID",
                          "type": "integer"
                        },
                        {
                          "enum": [
                            "Tagged",
                            "Untagged"
                          ],
                          "name": "tagness",
                          "title": "Vlan Tagness",
                          "type": "string"
                        }
                      ],
                      "type": "array"
                    },
                    "name": "vlan_list",
                    "title": "Vlans",
                    "type": "array"
                  },
                  {
                    "branched": true,
                    "name": "vlan_list.name",
                    "title": "Vlans: Vlan Name",
                    "type": "string"
                  },
                  {
                    "branched": true,
                    "name": "vlan_list.tagid",
                    "title": "Vlans: Tag ID",
                    "type": "integer"
                  },
                  {
                    "branched": true,
                    "enum": [
                      "Tagged",
                      "Untagged"
                    ],
                    "name": "vlan_list.tagness",
                    "title": "Vlans: Vlan Tagness",
                    "type": "string"
                  },
                  {
                    "enum": [
                      "Up",
                      "Down",
                      "Testing",
                      "Unknown",
                      "Dormant",
                      "Nonpresent",
                      "LowerLayerDown"
                    ],
                    "name": "operational_status",
                    "title": "Operational Status",
                    "type": "string"
                  },
                  {
                    "enum": [
                      "Up",
                      "Down",
                      "Testing"
                    ],
                    "name": "admin_status",
                    "title": "Admin Status",
                    "type": "string"
                  },
                  {
                    "description": "Interface max speed per Second",
                    "name": "speed",
                    "title": "Interface Speed",
                    "type": "string"
                  },
                  {
                    "enum": [
                      "Access",
                      "Trunk"
                    ],
                    "name": "port_type",
                    "title": "Port Type",
                    "type": "string"
                  },
                  {
                    "description": "Interface Maximum transmission unit",
                    "name": "mtu",
                    "title": "MTU",
                    "type": "string"
                  },
                  {
                    "name": "gateway",
                    "title": "Gateway",
                    "type": "string"
                  },
                  {
                    "name": "port",
                    "title": "Port",
                    "type": "string"
                  },
                  {
                    "description": "Recognized Geo locations of the IPs",
                    "items": {
                      "type": "string"
                    },
                    "name": "locations",
                    "title": "Location Name",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "location_id",
                    "title": "Location ID",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "facility_name",
                    "title": "Facility Name",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "facility_id",
                    "title": "Facility ID",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "region",
                    "title": "Region",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "zone",
                    "title": "Zone",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "country",
                    "title": "Country",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "state",
                    "title": "State",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "city",
                    "title": "City",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "postal_code",
                    "title": "Postal Code",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "street_address",
                    "title": "Street Address",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "full_address",
                    "title": "Full Address",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "latitude",
                    "title": "Latitude",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "longitude",
                    "title": "Longitude",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "ad_sitename",
                    "title": "AD SiteName",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "ad_sitecode",
                    "title": "AD SiteCode",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "gsc_sitecode",
                    "title": "GSC SiteCode",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "talentlink_sitecode",
                    "title": "Talentlink SiteCode",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "site_criticality",
                    "title": "Site Criticality",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "site_function",
                    "title": "Site Function",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "security_level",
                    "title": "Security Level",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "comments",
                    "title": "Comments",
                    "type": "array"
                  }
                ],
                "type": "array"
              },
              "name": "local_ifaces",
              "title": "Local Interface",
              "type": "array"
            },
            {
              "branched": true,
              "name": "local_ifaces.name",
              "title": "Local Interface: Iface Name",
              "type": "string"
            },
            {
              "branched": true,
              "name": "local_ifaces.mac",
              "title": "Local Interface: MAC",
              "type": "string"
            },
            {
              "branched": true,
              "name": "local_ifaces.manufacturer",
              "title": "Local Interface: Manufacturer",
              "type": "string"
            },
            {
              "format": "ip",
              "items": {
                "format": "ip",
                "type": "string"
              },
              "name": "local_ifaces.ips",
              "title": "Local Interface: IPs",
              "type": "array"
            },
            {
              "format": "ip",
              "items": {
                "format": "ip",
                "type": "string"
              },
              "name": "local_ifaces.ips_v4",
              "title": "Local Interface: IPv4s",
              "type": "array"
            },
            {
              "format": "ip",
              "items": {
                "format": "ip",
                "type": "string"
              },
              "name": "local_ifaces.ips_v6",
              "title": "Local Interface: IPv6s",
              "type": "array"
            },
            {
              "description": "A list of subnets in ip format, that correspond the IPs",
              "format": "subnet",
              "items": {
                "format": "subnet",
                "type": "string"
              },
              "name": "local_ifaces.subnets",
              "title": "Local Interface: Subnets",
              "type": "array"
            },
            {
              "description": "A list of vlans in this interface",
              "items": {
                "items": [
                  {
                    "name": "name",
                    "title": "Vlan Name",
                    "type": "string"
                  },
                  {
                    "name": "tagid",
                    "title": "Tag ID",
                    "type": "integer"
                  },
                  {
                    "enum": [
                      "Tagged",
                      "Untagged"
                    ],
                    "name": "tagness",
                    "title": "Vlan Tagness",
                    "type": "string"
                  }
                ],
                "type": "array"
              },
              "name": "local_ifaces.vlan_list",
              "title": "Local Interface: Vlans",
              "type": "array"
            },
            {
              "branched": true,
              "name": "local_ifaces.vlan_list.name",
              "title": "Local Interface: Vlans: Vlan Name",
              "type": "string"
            },
            {
              "branched": true,
              "name": "local_ifaces.vlan_list.tagid",
              "title": "Local Interface: Vlans: Tag ID",
              "type": "integer"
            },
            {
              "branched": true,
              "enum": [
                "Tagged",
                "Untagged"
              ],
              "name": "local_ifaces.vlan_list.tagness",
              "title": "Local Interface: Vlans: Vlan Tagness",
              "type": "string"
            },
            {
              "branched": true,
              "enum": [
                "Up",
                "Down",
                "Testing",
                "Unknown",
                "Dormant",
                "Nonpresent",
                "LowerLayerDown"
              ],
              "name": "local_ifaces.operational_status",
              "title": "Local Interface: Operational Status",
              "type": "string"
            },
            {
              "branched": true,
              "enum": [
                "Up",
                "Down",
                "Testing"
              ],
              "name": "local_ifaces.admin_status",
              "title": "Local Interface: Admin Status",
              "type": "string"
            },
            {
              "branched": true,
              "description": "Interface max speed per Second",
              "name": "local_ifaces.speed",
              "title": "Local Interface: Interface Speed",
              "type": "string"
            },
            {
              "branched": true,
              "enum": [
                "Access",
                "Trunk"
              ],
              "name": "local_ifaces.port_type",
              "title": "Local Interface: Port Type",
              "type": "string"
            },
            {
              "branched": true,
              "description": "Interface Maximum transmission unit",
              "name": "local_ifaces.mtu",
              "title": "Local Interface: MTU",
              "type": "string"
            },
            {
              "branched": true,
              "name": "local_ifaces.gateway",
              "title": "Local Interface: Gateway",
              "type": "string"
            },
            {
              "branched": true,
              "name": "local_ifaces.port",
              "title": "Local Interface: Port",
              "type": "string"
            },
            {
              "description": "Recognized Geo locations of the IPs",
              "items": {
                "type": "string"
              },
              "name": "local_ifaces.locations",
              "title": "Local Interface: Location Name",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "local_ifaces.location_id",
              "title": "Local Interface: Location ID",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "local_ifaces.facility_name",
              "title": "Local Interface: Facility Name",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "local_ifaces.facility_id",
              "title": "Local Interface: Facility ID",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "local_ifaces.region",
              "title": "Local Interface: Region",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "local_ifaces.zone",
              "title": "Local Interface: Zone",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "local_ifaces.country",
              "title": "Local Interface: Country",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "local_ifaces.state",
              "title": "Local Interface: State",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "local_ifaces.city",
              "title": "Local Interface: City",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "local_ifaces.postal_code",
              "title": "Local Interface: Postal Code",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "local_ifaces.street_address",
              "title": "Local Interface: Street Address",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "local_ifaces.full_address",
              "title": "Local Interface: Full Address",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "local_ifaces.latitude",
              "title": "Local Interface: Latitude",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "local_ifaces.longitude",
              "title": "Local Interface: Longitude",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "local_ifaces.ad_sitename",
              "title": "Local Interface: AD SiteName",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "local_ifaces.ad_sitecode",
              "title": "Local Interface: AD SiteCode",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "local_ifaces.gsc_sitecode",
              "title": "Local Interface: GSC SiteCode",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "local_ifaces.talentlink_sitecode",
              "title": "Local Interface: Talentlink SiteCode",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "local_ifaces.site_criticality",
              "title": "Local Interface: Site Criticality",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "local_ifaces.site_function",
              "title": "Local Interface: Site Function",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "local_ifaces.security_level",
              "title": "Local Interface: Security Level",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "local_ifaces.comments",
              "title": "Local Interface: Comments",
              "type": "array"
            },
            {
              "items": {
                "items": [
                  {
                    "name": "name",
                    "title": "Iface Name",
                    "type": "string"
                  },
                  {
                    "name": "mac",
                    "title": "MAC",
                    "type": "string"
                  },
                  {
                    "name": "manufacturer",
                    "title": "Manufacturer",
                    "type": "string"
                  },
                  {
                    "format": "ip",
                    "items": {
                      "format": "ip",
                      "type": "string"
                    },
                    "name": "ips",
                    "title": "IPs",
                    "type": "array"
                  },
                  {
                    "format": "ip",
                    "items": {
                      "format": "ip",
                      "type": "string"
                    },
                    "name": "ips_v4",
                    "title": "IPv4s",
                    "type": "array"
                  },
                  {
                    "format": "ip",
                    "items": {
                      "format": "ip",
                      "type": "string"
                    },
                    "name": "ips_v6",
                    "title": "IPv6s",
                    "type": "array"
                  },
                  {
                    "description": "A list of subnets in ip format, that correspond the IPs",
                    "format": "subnet",
                    "items": {
                      "format": "subnet",
                      "type": "string"
                    },
                    "name": "subnets",
                    "title": "Subnets",
                    "type": "array"
                  },
                  {
                    "description": "A list of vlans in this interface",
                    "items": {
                      "items": [
                        {
                          "name": "name",
                          "title": "Vlan Name",
                          "type": "string"
                        },
                        {
                          "name": "tagid",
                          "title": "Tag ID",
                          "type": "integer"
                        },
                        {
                          "enum": [
                            "Tagged",
                            "Untagged"
                          ],
                          "name": "tagness",
                          "title": "Vlan Tagness",
                          "type": "string"
                        }
                      ],
                      "type": "array"
                    },
                    "name": "vlan_list",
                    "title": "Vlans",
                    "type": "array"
                  },
                  {
                    "branched": true,
                    "name": "vlan_list.name",
                    "title": "Vlans: Vlan Name",
                    "type": "string"
                  },
                  {
                    "branched": true,
                    "name": "vlan_list.tagid",
                    "title": "Vlans: Tag ID",
                    "type": "integer"
                  },
                  {
                    "branched": true,
                    "enum": [
                      "Tagged",
                      "Untagged"
                    ],
                    "name": "vlan_list.tagness",
                    "title": "Vlans: Vlan Tagness",
                    "type": "string"
                  },
                  {
                    "enum": [
                      "Up",
                      "Down",
                      "Testing",
                      "Unknown",
                      "Dormant",
                      "Nonpresent",
                      "LowerLayerDown"
                    ],
                    "name": "operational_status",
                    "title": "Operational Status",
                    "type": "string"
                  },
                  {
                    "enum": [
                      "Up",
                      "Down",
                      "Testing"
                    ],
                    "name": "admin_status",
                    "title": "Admin Status",
                    "type": "string"
                  },
                  {
                    "description": "Interface max speed per Second",
                    "name": "speed",
                    "title": "Interface Speed",
                    "type": "string"
                  },
                  {
                    "enum": [
                      "Access",
                      "Trunk"
                    ],
                    "name": "port_type",
                    "title": "Port Type",
                    "type": "string"
                  },
                  {
                    "description": "Interface Maximum transmission unit",
                    "name": "mtu",
                    "title": "MTU",
                    "type": "string"
                  },
                  {
                    "name": "gateway",
                    "title": "Gateway",
                    "type": "string"
                  },
                  {
                    "name": "port",
                    "title": "Port",
                    "type": "string"
                  },
                  {
                    "description": "Recognized Geo locations of the IPs",
                    "items": {
                      "type": "string"
                    },
                    "name": "locations",
                    "title": "Location Name",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "location_id",
                    "title": "Location ID",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "facility_name",
                    "title": "Facility Name",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "facility_id",
                    "title": "Facility ID",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "region",
                    "title": "Region",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "zone",
                    "title": "Zone",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "country",
                    "title": "Country",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "state",
                    "title": "State",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "city",
                    "title": "City",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "postal_code",
                    "title": "Postal Code",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "street_address",
                    "title": "Street Address",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "full_address",
                    "title": "Full Address",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "latitude",
                    "title": "Latitude",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "longitude",
                    "title": "Longitude",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "ad_sitename",
                    "title": "AD SiteName",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "ad_sitecode",
                    "title": "AD SiteCode",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "gsc_sitecode",
                    "title": "GSC SiteCode",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "talentlink_sitecode",
                    "title": "Talentlink SiteCode",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "site_criticality",
                    "title": "Site Criticality",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "site_function",
                    "title": "Site Function",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "security_level",
                    "title": "Security Level",
                    "type": "array"
                  },
                  {
                    "items": {
                      "type": "string"
                    },
                    "name": "comments",
                    "title": "Comments",
                    "type": "array"
                  }
                ],
                "type": "array"
              },
              "name": "remote_ifaces",
              "title": "Remote Device Iface",
              "type": "array"
            },
            {
              "branched": true,
              "name": "remote_ifaces.name",
              "title": "Remote Device Iface: Iface Name",
              "type": "string"
            },
            {
              "branched": true,
              "name": "remote_ifaces.mac",
              "title": "Remote Device Iface: MAC",
              "type": "string"
            },
            {
              "branched": true,
              "name": "remote_ifaces.manufacturer",
              "title": "Remote Device Iface: Manufacturer",
              "type": "string"
            },
            {
              "format": "ip",
              "items": {
                "format": "ip",
                "type": "string"
              },
              "name": "remote_ifaces.ips",
              "title": "Remote Device Iface: IPs",
              "type": "array"
            },
            {
              "format": "ip",
              "items": {
                "format": "ip",
                "type": "string"
              },
              "name": "remote_ifaces.ips_v4",
              "title": "Remote Device Iface: IPv4s",
              "type": "array"
            },
            {
              "format": "ip",
              "items": {
                "format": "ip",
                "type": "string"
              },
              "name": "remote_ifaces.ips_v6",
              "title": "Remote Device Iface: IPv6s",
              "type": "array"
            },
            {
              "description": "A list of subnets in ip format, that correspond the IPs",
              "format": "subnet",
              "items": {
                "format": "subnet",
                "type": "string"
              },
              "name": "remote_ifaces.subnets",
              "title": "Remote Device Iface: Subnets",
              "type": "array"
            },
            {
              "description": "A list of vlans in this interface",
              "items": {
                "items": [
                  {
                    "name": "name",
                    "title": "Vlan Name",
                    "type": "string"
                  },
                  {
                    "name": "tagid",
                    "title": "Tag ID",
                    "type": "integer"
                  },
                  {
                    "enum": [
                      "Tagged",
                      "Untagged"
                    ],
                    "name": "tagness",
                    "title": "Vlan Tagness",
                    "type": "string"
                  }
                ],
                "type": "array"
              },
              "name": "remote_ifaces.vlan_list",
              "title": "Remote Device Iface: Vlans",
              "type": "array"
            },
            {
              "branched": true,
              "name": "remote_ifaces.vlan_list.name",
              "title": "Remote Device Iface: Vlans: Vlan Name",
              "type": "string"
            },
            {
              "branched": true,
              "name": "remote_ifaces.vlan_list.tagid",
              "title": "Remote Device Iface: Vlans: Tag ID",
              "type": "integer"
            },
            {
              "branched": true,
              "enum": [
                "Tagged",
                "Untagged"
              ],
              "name": "remote_ifaces.vlan_list.tagness",
              "title": "Remote Device Iface: Vlans: Vlan Tagness",
              "type": "string"
            },
            {
              "branched": true,
              "enum": [
                "Up",
                "Down",
                "Testing",
                "Unknown",
                "Dormant",
                "Nonpresent",
                "LowerLayerDown"
              ],
              "name": "remote_ifaces.operational_status",
              "title": "Remote Device Iface: Operational Status",
              "type": "string"
            },
            {
              "branched": true,
              "enum": [
                "Up",
                "Down",
                "Testing"
              ],
              "name": "remote_ifaces.admin_status",
              "title": "Remote Device Iface: Admin Status",
              "type": "string"
            },
            {
              "branched": true,
              "description": "Interface max speed per Second",
              "name": "remote_ifaces.speed",
              "title": "Remote Device Iface: Interface Speed",
              "type": "string"
            },
            {
              "branched": true,
              "enum": [
                "Access",
                "Trunk"
              ],
              "name": "remote_ifaces.port_type",
              "title": "Remote Device Iface: Port Type",
              "type": "string"
            },
            {
              "branched": true,
              "description": "Interface Maximum transmission unit",
              "name": "remote_ifaces.mtu",
              "title": "Remote Device Iface: MTU",
              "type": "string"
            },
            {
              "branched": true,
              "name": "remote_ifaces.gateway",
              "title": "Remote Device Iface: Gateway",
              "type": "string"
            },
            {
              "branched": true,
              "name": "remote_ifaces.port",
              "title": "Remote Device Iface: Port",
              "type": "string"
            },
            {
              "description": "Recognized Geo locations of the IPs",
              "items": {
                "type": "string"
              },
              "name": "remote_ifaces.locations",
              "title": "Remote Device Iface: Location Name",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "remote_ifaces.location_id",
              "title": "Remote Device Iface: Location ID",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "remote_ifaces.facility_name",
              "title": "Remote Device Iface: Facility Name",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "remote_ifaces.facility_id",
              "title": "Remote Device Iface: Facility ID",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "remote_ifaces.region",
              "title": "Remote Device Iface: Region",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "remote_ifaces.zone",
              "title": "Remote Device Iface: Zone",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "remote_ifaces.country",
              "title": "Remote Device Iface: Country",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "remote_ifaces.state",
              "title": "Remote Device Iface: State",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "remote_ifaces.city",
              "title": "Remote Device Iface: City",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "remote_ifaces.postal_code",
              "title": "Remote Device Iface: Postal Code",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "remote_ifaces.street_address",
              "title": "Remote Device Iface: Street Address",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "remote_ifaces.full_address",
              "title": "Remote Device Iface: Full Address",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "remote_ifaces.latitude",
              "title": "Remote Device Iface: Latitude",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "remote_ifaces.longitude",
              "title": "Remote Device Iface: Longitude",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "remote_ifaces.ad_sitename",
              "title": "Remote Device Iface: AD SiteName",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "remote_ifaces.ad_sitecode",
              "title": "Remote Device Iface: AD SiteCode",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "remote_ifaces.gsc_sitecode",
              "title": "Remote Device Iface: GSC SiteCode",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "remote_ifaces.talentlink_sitecode",
              "title": "Remote Device Iface: Talentlink SiteCode",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "remote_ifaces.site_criticality",
              "title": "Remote Device Iface: Site Criticality",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "remote_ifaces.site_function",
              "title": "Remote Device Iface: Site Function",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "remote_ifaces.security_level",
              "title": "Remote Device Iface: Security Level",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "remote_ifaces.comments",
              "title": "Remote Device Iface: Comments",
              "type": "array"
            },
            {
              "enum": [
                "Direct",
                "Indirect"
              ],
              "name": "connection_type",
              "title": "Connection Type",
              "type": "string"
            }
          ],
          "type": "array"
        },
        "name": "connected_devices",
        "title": "Connected Devices",
        "type": "array"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "connected_devices.remote_name",
        "title": "Connected Devices: Remote Device Name",
        "type": "string"
      },
      {
        "filterable": true,
        "items": {
          "items": [
            {
              "name": "name",
              "title": "Iface Name",
              "type": "string"
            },
            {
              "name": "mac",
              "title": "MAC",
              "type": "string"
            },
            {
              "name": "manufacturer",
              "title": "Manufacturer",
              "type": "string"
            },
            {
              "format": "ip",
              "items": {
                "format": "ip",
                "type": "string"
              },
              "name": "ips",
              "title": "IPs",
              "type": "array"
            },
            {
              "format": "ip",
              "items": {
                "format": "ip",
                "type": "string"
              },
              "name": "ips_v4",
              "title": "IPv4s",
              "type": "array"
            },
            {
              "format": "ip",
              "items": {
                "format": "ip",
                "type": "string"
              },
              "name": "ips_v6",
              "title": "IPv6s",
              "type": "array"
            },
            {
              "description": "A list of subnets in ip format, that correspond the IPs",
              "format": "subnet",
              "items": {
                "format": "subnet",
                "type": "string"
              },
              "name": "subnets",
              "title": "Subnets",
              "type": "array"
            },
            {
              "description": "A list of vlans in this interface",
              "items": {
                "items": [
                  {
                    "name": "name",
                    "title": "Vlan Name",
                    "type": "string"
                  },
                  {
                    "name": "tagid",
                    "title": "Tag ID",
                    "type": "integer"
                  },
                  {
                    "enum": [
                      "Tagged",
                      "Untagged"
                    ],
                    "name": "tagness",
                    "title": "Vlan Tagness",
                    "type": "string"
                  }
                ],
                "type": "array"
              },
              "name": "vlan_list",
              "title": "Vlans",
              "type": "array"
            },
            {
              "branched": true,
              "name": "vlan_list.name",
              "title": "Vlans: Vlan Name",
              "type": "string"
            },
            {
              "branched": true,
              "name": "vlan_list.tagid",
              "title": "Vlans: Tag ID",
              "type": "integer"
            },
            {
              "branched": true,
              "enum": [
                "Tagged",
                "Untagged"
              ],
              "name": "vlan_list.tagness",
              "title": "Vlans: Vlan Tagness",
              "type": "string"
            },
            {
              "enum": [
                "Up",
                "Down",
                "Testing",
                "Unknown",
                "Dormant",
                "Nonpresent",
                "LowerLayerDown"
              ],
              "name": "operational_status",
              "title": "Operational Status",
              "type": "string"
            },
            {
              "enum": [
                "Up",
                "Down",
                "Testing"
              ],
              "name": "admin_status",
              "title": "Admin Status",
              "type": "string"
            },
            {
              "description": "Interface max speed per Second",
              "name": "speed",
              "title": "Interface Speed",
              "type": "string"
            },
            {
              "enum": [
                "Access",
                "Trunk"
              ],
              "name": "port_type",
              "title": "Port Type",
              "type": "string"
            },
            {
              "description": "Interface Maximum transmission unit",
              "name": "mtu",
              "title": "MTU",
              "type": "string"
            },
            {
              "name": "gateway",
              "title": "Gateway",
              "type": "string"
            },
            {
              "name": "port",
              "title": "Port",
              "type": "string"
            },
            {
              "description": "Recognized Geo locations of the IPs",
              "items": {
                "type": "string"
              },
              "name": "locations",
              "title": "Location Name",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "location_id",
              "title": "Location ID",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "facility_name",
              "title": "Facility Name",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "facility_id",
              "title": "Facility ID",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "region",
              "title": "Region",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "zone",
              "title": "Zone",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "country",
              "title": "Country",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "state",
              "title": "State",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "city",
              "title": "City",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "postal_code",
              "title": "Postal Code",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "street_address",
              "title": "Street Address",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "full_address",
              "title": "Full Address",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "latitude",
              "title": "Latitude",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "longitude",
              "title": "Longitude",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "ad_sitename",
              "title": "AD SiteName",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "ad_sitecode",
              "title": "AD SiteCode",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "gsc_sitecode",
              "title": "GSC SiteCode",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "talentlink_sitecode",
              "title": "Talentlink SiteCode",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "site_criticality",
              "title": "Site Criticality",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "site_function",
              "title": "Site Function",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "security_level",
              "title": "Security Level",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "comments",
              "title": "Comments",
              "type": "array"
            }
          ],
          "type": "array"
        },
        "name": "connected_devices.local_ifaces",
        "title": "Connected Devices: Local Interface",
        "type": "array"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "connected_devices.local_ifaces.name",
        "title": "Connected Devices: Local Interface: Iface Name",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "connected_devices.local_ifaces.mac",
        "title": "Connected Devices: Local Interface: MAC",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "connected_devices.local_ifaces.manufacturer",
        "title": "Connected Devices: Local Interface: Manufacturer",
        "type": "string"
      },
      {
        "filterable": true,
        "format": "ip",
        "items": {
          "format": "ip",
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.ips",
        "title": "Connected Devices: Local Interface: IPs",
        "type": "array"
      },
      {
        "filterable": true,
        "format": "ip",
        "items": {
          "format": "ip",
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.ips_v4",
        "title": "Connected Devices: Local Interface: IPv4s",
        "type": "array"
      },
      {
        "filterable": true,
        "format": "ip",
        "items": {
          "format": "ip",
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.ips_v6",
        "title": "Connected Devices: Local Interface: IPv6s",
        "type": "array"
      },
      {
        "description": "A list of subnets in ip format, that correspond the IPs",
        "filterable": true,
        "format": "subnet",
        "items": {
          "format": "subnet",
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.subnets",
        "title": "Connected Devices: Local Interface: Subnets",
        "type": "array"
      },
      {
        "description": "A list of vlans in this interface",
        "filterable": true,
        "items": {
          "items": [
            {
              "name": "name",
              "title": "Vlan Name",
              "type": "string"
            },
            {
              "name": "tagid",
              "title": "Tag ID",
              "type": "integer"
            },
            {
              "enum": [
                "Tagged",
                "Untagged"
              ],
              "name": "tagness",
              "title": "Vlan Tagness",
              "type": "string"
            }
          ],
          "type": "array"
        },
        "name": "connected_devices.local_ifaces.vlan_list",
        "title": "Connected Devices: Local Interface: Vlans",
        "type": "array"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "connected_devices.local_ifaces.vlan_list.name",
        "title": "Connected Devices: Local Interface: Vlans: Vlan Name",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "connected_devices.local_ifaces.vlan_list.tagid",
        "title": "Connected Devices: Local Interface: Vlans: Tag ID",
        "type": "integer"
      },
      {
        "branched": true,
        "enum": [
          "Tagged",
          "Untagged"
        ],
        "filterable": true,
        "name": "connected_devices.local_ifaces.vlan_list.tagness",
        "title": "Connected Devices: Local Interface: Vlans: Vlan Tagness",
        "type": "string"
      },
      {
        "branched": true,
        "enum": [
          "Up",
          "Down",
          "Testing",
          "Unknown",
          "Dormant",
          "Nonpresent",
          "LowerLayerDown"
        ],
        "filterable": true,
        "name": "connected_devices.local_ifaces.operational_status",
        "title": "Connected Devices: Local Interface: Operational Status",
        "type": "string"
      },
      {
        "branched": true,
        "enum": [
          "Up",
          "Down",
          "Testing"
        ],
        "filterable": true,
        "name": "connected_devices.local_ifaces.admin_status",
        "title": "Connected Devices: Local Interface: Admin Status",
        "type": "string"
      },
      {
        "branched": true,
        "description": "Interface max speed per Second",
        "filterable": true,
        "name": "connected_devices.local_ifaces.speed",
        "title": "Connected Devices: Local Interface: Interface Speed",
        "type": "string"
      },
      {
        "branched": true,
        "enum": [
          "Access",
          "Trunk"
        ],
        "filterable": true,
        "name": "connected_devices.local_ifaces.port_type",
        "title": "Connected Devices: Local Interface: Port Type",
        "type": "string"
      },
      {
        "branched": true,
        "description": "Interface Maximum transmission unit",
        "filterable": true,
        "name": "connected_devices.local_ifaces.mtu",
        "title": "Connected Devices: Local Interface: MTU",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "connected_devices.local_ifaces.gateway",
        "title": "Connected Devices: Local Interface: Gateway",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "connected_devices.local_ifaces.port",
        "title": "Connected Devices: Local Interface: Port",
        "type": "string"
      },
      {
        "description": "Recognized Geo locations of the IPs",
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.locations",
        "title": "Connected Devices: Local Interface: Location Name",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.location_id",
        "title": "Connected Devices: Local Interface: Location ID",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.facility_name",
        "title": "Connected Devices: Local Interface: Facility Name",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.facility_id",
        "title": "Connected Devices: Local Interface: Facility ID",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.region",
        "title": "Connected Devices: Local Interface: Region",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.zone",
        "title": "Connected Devices: Local Interface: Zone",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.country",
        "title": "Connected Devices: Local Interface: Country",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.state",
        "title": "Connected Devices: Local Interface: State",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.city",
        "title": "Connected Devices: Local Interface: City",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.postal_code",
        "title": "Connected Devices: Local Interface: Postal Code",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.street_address",
        "title": "Connected Devices: Local Interface: Street Address",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.full_address",
        "title": "Connected Devices: Local Interface: Full Address",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.latitude",
        "title": "Connected Devices: Local Interface: Latitude",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.longitude",
        "title": "Connected Devices: Local Interface: Longitude",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.ad_sitename",
        "title": "Connected Devices: Local Interface: AD SiteName",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.ad_sitecode",
        "title": "Connected Devices: Local Interface: AD SiteCode",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.gsc_sitecode",
        "title": "Connected Devices: Local Interface: GSC SiteCode",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.talentlink_sitecode",
        "title": "Connected Devices: Local Interface: Talentlink SiteCode",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.site_criticality",
        "title": "Connected Devices: Local Interface: Site Criticality",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.site_function",
        "title": "Connected Devices: Local Interface: Site Function",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.security_level",
        "title": "Connected Devices: Local Interface: Security Level",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.local_ifaces.comments",
        "title": "Connected Devices: Local Interface: Comments",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "items": [
            {
              "name": "name",
              "title": "Iface Name",
              "type": "string"
            },
            {
              "name": "mac",
              "title": "MAC",
              "type": "string"
            },
            {
              "name": "manufacturer",
              "title": "Manufacturer",
              "type": "string"
            },
            {
              "format": "ip",
              "items": {
                "format": "ip",
                "type": "string"
              },
              "name": "ips",
              "title": "IPs",
              "type": "array"
            },
            {
              "format": "ip",
              "items": {
                "format": "ip",
                "type": "string"
              },
              "name": "ips_v4",
              "title": "IPv4s",
              "type": "array"
            },
            {
              "format": "ip",
              "items": {
                "format": "ip",
                "type": "string"
              },
              "name": "ips_v6",
              "title": "IPv6s",
              "type": "array"
            },
            {
              "description": "A list of subnets in ip format, that correspond the IPs",
              "format": "subnet",
              "items": {
                "format": "subnet",
                "type": "string"
              },
              "name": "subnets",
              "title": "Subnets",
              "type": "array"
            },
            {
              "description": "A list of vlans in this interface",
              "items": {
                "items": [
                  {
                    "name": "name",
                    "title": "Vlan Name",
                    "type": "string"
                  },
                  {
                    "name": "tagid",
                    "title": "Tag ID",
                    "type": "integer"
                  },
                  {
                    "enum": [
                      "Tagged",
                      "Untagged"
                    ],
                    "name": "tagness",
                    "title": "Vlan Tagness",
                    "type": "string"
                  }
                ],
                "type": "array"
              },
              "name": "vlan_list",
              "title": "Vlans",
              "type": "array"
            },
            {
              "branched": true,
              "name": "vlan_list.name",
              "title": "Vlans: Vlan Name",
              "type": "string"
            },
            {
              "branched": true,
              "name": "vlan_list.tagid",
              "title": "Vlans: Tag ID",
              "type": "integer"
            },
            {
              "branched": true,
              "enum": [
                "Tagged",
                "Untagged"
              ],
              "name": "vlan_list.tagness",
              "title": "Vlans: Vlan Tagness",
              "type": "string"
            },
            {
              "enum": [
                "Up",
                "Down",
                "Testing",
                "Unknown",
                "Dormant",
                "Nonpresent",
                "LowerLayerDown"
              ],
              "name": "operational_status",
              "title": "Operational Status",
              "type": "string"
            },
            {
              "enum": [
                "Up",
                "Down",
                "Testing"
              ],
              "name": "admin_status",
              "title": "Admin Status",
              "type": "string"
            },
            {
              "description": "Interface max speed per Second",
              "name": "speed",
              "title": "Interface Speed",
              "type": "string"
            },
            {
              "enum": [
                "Access",
                "Trunk"
              ],
              "name": "port_type",
              "title": "Port Type",
              "type": "string"
            },
            {
              "description": "Interface Maximum transmission unit",
              "name": "mtu",
              "title": "MTU",
              "type": "string"
            },
            {
              "name": "gateway",
              "title": "Gateway",
              "type": "string"
            },
            {
              "name": "port",
              "title": "Port",
              "type": "string"
            },
            {
              "description": "Recognized Geo locations of the IPs",
              "items": {
                "type": "string"
              },
              "name": "locations",
              "title": "Location Name",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "location_id",
              "title": "Location ID",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "facility_name",
              "title": "Facility Name",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "facility_id",
              "title": "Facility ID",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "region",
              "title": "Region",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "zone",
              "title": "Zone",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "country",
              "title": "Country",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "state",
              "title": "State",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "city",
              "title": "City",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "postal_code",
              "title": "Postal Code",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "street_address",
              "title": "Street Address",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "full_address",
              "title": "Full Address",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "latitude",
              "title": "Latitude",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "longitude",
              "title": "Longitude",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "ad_sitename",
              "title": "AD SiteName",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "ad_sitecode",
              "title": "AD SiteCode",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "gsc_sitecode",
              "title": "GSC SiteCode",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "talentlink_sitecode",
              "title": "Talentlink SiteCode",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "site_criticality",
              "title": "Site Criticality",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "site_function",
              "title": "Site Function",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "security_level",
              "title": "Security Level",
              "type": "array"
            },
            {
              "items": {
                "type": "string"
              },
              "name": "comments",
              "title": "Comments",
              "type": "array"
            }
          ],
          "type": "array"
        },
        "name": "connected_devices.remote_ifaces",
        "title": "Connected Devices: Remote Device Iface",
        "type": "array"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "connected_devices.remote_ifaces.name",
        "title": "Connected Devices: Remote Device Iface: Iface Name",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "connected_devices.remote_ifaces.mac",
        "title": "Connected Devices: Remote Device Iface: MAC",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "connected_devices.remote_ifaces.manufacturer",
        "title": "Connected Devices: Remote Device Iface: Manufacturer",
        "type": "string"
      },
      {
        "filterable": true,
        "format": "ip",
        "items": {
          "format": "ip",
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.ips",
        "title": "Connected Devices: Remote Device Iface: IPs",
        "type": "array"
      },
      {
        "filterable": true,
        "format": "ip",
        "items": {
          "format": "ip",
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.ips_v4",
        "title": "Connected Devices: Remote Device Iface: IPv4s",
        "type": "array"
      },
      {
        "filterable": true,
        "format": "ip",
        "items": {
          "format": "ip",
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.ips_v6",
        "title": "Connected Devices: Remote Device Iface: IPv6s",
        "type": "array"
      },
      {
        "description": "A list of subnets in ip format, that correspond the IPs",
        "filterable": true,
        "format": "subnet",
        "items": {
          "format": "subnet",
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.subnets",
        "title": "Connected Devices: Remote Device Iface: Subnets",
        "type": "array"
      },
      {
        "description": "A list of vlans in this interface",
        "filterable": true,
        "items": {
          "items": [
            {
              "name": "name",
              "title": "Vlan Name",
              "type": "string"
            },
            {
              "name": "tagid",
              "title": "Tag ID",
              "type": "integer"
            },
            {
              "enum": [
                "Tagged",
                "Untagged"
              ],
              "name": "tagness",
              "title": "Vlan Tagness",
              "type": "string"
            }
          ],
          "type": "array"
        },
        "name": "connected_devices.remote_ifaces.vlan_list",
        "title": "Connected Devices: Remote Device Iface: Vlans",
        "type": "array"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "connected_devices.remote_ifaces.vlan_list.name",
        "title": "Connected Devices: Remote Device Iface: Vlans: Vlan Name",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "connected_devices.remote_ifaces.vlan_list.tagid",
        "title": "Connected Devices: Remote Device Iface: Vlans: Tag ID",
        "type": "integer"
      },
      {
        "branched": true,
        "enum": [
          "Tagged",
          "Untagged"
        ],
        "filterable": true,
        "name": "connected_devices.remote_ifaces.vlan_list.tagness",
        "title": "Connected Devices: Remote Device Iface: Vlans: Vlan Tagness",
        "type": "string"
      },
      {
        "branched": true,
        "enum": [
          "Up",
          "Down",
          "Testing",
          "Unknown",
          "Dormant",
          "Nonpresent",
          "LowerLayerDown"
        ],
        "filterable": true,
        "name": "connected_devices.remote_ifaces.operational_status",
        "title": "Connected Devices: Remote Device Iface: Operational Status",
        "type": "string"
      },
      {
        "branched": true,
        "enum": [
          "Up",
          "Down",
          "Testing"
        ],
        "filterable": true,
        "name": "connected_devices.remote_ifaces.admin_status",
        "title": "Connected Devices: Remote Device Iface: Admin Status",
        "type": "string"
      },
      {
        "branched": true,
        "description": "Interface max speed per Second",
        "filterable": true,
        "name": "connected_devices.remote_ifaces.speed",
        "title": "Connected Devices: Remote Device Iface: Interface Speed",
        "type": "string"
      },
      {
        "branched": true,
        "enum": [
          "Access",
          "Trunk"
        ],
        "filterable": true,
        "name": "connected_devices.remote_ifaces.port_type",
        "title": "Connected Devices: Remote Device Iface: Port Type",
        "type": "string"
      },
      {
        "branched": true,
        "description": "Interface Maximum transmission unit",
        "filterable": true,
        "name": "connected_devices.remote_ifaces.mtu",
        "title": "Connected Devices: Remote Device Iface: MTU",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "connected_devices.remote_ifaces.gateway",
        "title": "Connected Devices: Remote Device Iface: Gateway",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "connected_devices.remote_ifaces.port",
        "title": "Connected Devices: Remote Device Iface: Port",
        "type": "string"
      },
      {
        "description": "Recognized Geo locations of the IPs",
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.locations",
        "title": "Connected Devices: Remote Device Iface: Location Name",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.location_id",
        "title": "Connected Devices: Remote Device Iface: Location ID",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.facility_name",
        "title": "Connected Devices: Remote Device Iface: Facility Name",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.facility_id",
        "title": "Connected Devices: Remote Device Iface: Facility ID",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.region",
        "title": "Connected Devices: Remote Device Iface: Region",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.zone",
        "title": "Connected Devices: Remote Device Iface: Zone",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.country",
        "title": "Connected Devices: Remote Device Iface: Country",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.state",
        "title": "Connected Devices: Remote Device Iface: State",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.city",
        "title": "Connected Devices: Remote Device Iface: City",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.postal_code",
        "title": "Connected Devices: Remote Device Iface: Postal Code",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.street_address",
        "title": "Connected Devices: Remote Device Iface: Street Address",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.full_address",
        "title": "Connected Devices: Remote Device Iface: Full Address",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.latitude",
        "title": "Connected Devices: Remote Device Iface: Latitude",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.longitude",
        "title": "Connected Devices: Remote Device Iface: Longitude",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.ad_sitename",
        "title": "Connected Devices: Remote Device Iface: AD SiteName",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.ad_sitecode",
        "title": "Connected Devices: Remote Device Iface: AD SiteCode",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.gsc_sitecode",
        "title": "Connected Devices: Remote Device Iface: GSC SiteCode",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.talentlink_sitecode",
        "title": "Connected Devices: Remote Device Iface: Talentlink SiteCode",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.site_criticality",
        "title": "Connected Devices: Remote Device Iface: Site Criticality",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.site_function",
        "title": "Connected Devices: Remote Device Iface: Site Function",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.security_level",
        "title": "Connected Devices: Remote Device Iface: Security Level",
        "type": "array"
      },
      {
        "filterable": true,
        "items": {
          "type": "string"
        },
        "name": "connected_devices.remote_ifaces.comments",
        "title": "Connected Devices: Remote Device Iface: Comments",
        "type": "array"
      },
      {
        "branched": true,
        "enum": [
          "Direct",
          "Indirect"
        ],
        "filterable": true,
        "name": "connected_devices.connection_type",
        "title": "Connected Devices: Connection Type",
        "type": "string"
      },
      {
        "filterable": true,
        "name": "id",
        "title": "ID",
        "type": "string"
      },
      {
        "filterable": true,
        "items": {
          "items": [
            {
              "name": "tag_key",
              "title": "Tag Key",
              "type": "string"
            },
            {
              "name": "tag_value",
              "title": "Tag Value",
              "type": "string"
            }
          ],
          "type": "array"
        },
        "name": "tags",
        "title": "Adapter Tags",
        "type": "array"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "tags.tag_key",
        "title": "Adapter Tags: Tag Key",
        "type": "string"
      },
      {
        "branched": true,
        "filterable": true,
        "name": "tags.tag_value",
        "title": "Adapter Tags: Tag Value",
        "type": "string"
      },
      {
        "filterable": true,
        "name": "cloud_provider",
        "title": "Cloud Provider",
        "type": "string"
      },
      {
        "filterable": true,
        "name": "cloud_id",
        "title": "Cloud ID",
        "type": "string"
      },
      {
        "enum": [
          "Agent",
          "Endpoint_Protection_Platform",
          "Network",
          "Firewall",
          "Manager",
          "Vulnerability_Assessment",
          "Assets",
          "UserManagement",
          "Cloud_Provider",
          "Virtualization",
          "MDM"
        ],
        "filterable": true,
        "items": {
          "enum": [
            "Agent",
            "Endpoint_Protection_Platform",
            "Network",
            "Firewall",
            "Manager",
            "Vulnerability_Assessment",
            "Assets",
            "UserManagement",
            "Cloud_Provider",
            "Virtualization",
            "MDM"
          ],
          "type": "string"
        },
        "name": "adapter_properties",
        "title": "Adapter Properties",
        "type": "array"
      },
      {
        "filterable": true,
        "name": "adapter_count",
        "title": "Distinct Adapter Connections Count",
        "type": "number"
      }
    ],
    "raw_fields": []
    }''')
}
