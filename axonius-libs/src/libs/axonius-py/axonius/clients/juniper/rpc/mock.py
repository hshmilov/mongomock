# pylint: disable=C0301
# pylint: disable=C0302
INTERFACE_MOCK = \
    '''<rpc-reply xmlns:junos="http://xml.juniper.net/junos/12.1R1/junos">
    <interface-information xmlns="http://xml.juniper.net/junos/12.1R1/junos-interface" junos:style="normal">
        <physical-interface>
            <name>cbp0</name>
            <admin-status junos:format="Enabled">up</admin-status>
            <oper-status>up</oper-status>
            <local-index>130</local-index>
            <snmp-index>501</snmp-index>
            <if-type>Ethernet</if-type>
            <link-level-type>Ethernet</link-level-type>
            <mtu>1514</mtu>
            <if-device-flags>
                <ifdf-present/>
                <ifdf-running/>
            </if-device-flags>
            <if-config-flags>
                <iff-snmp-traps/>
            </if-config-flags>
            <link-type>Full-Duplex</link-type>
            <if-media-flags>
                <ifmf-none/>
            </if-media-flags>
            <current-physical-address junos:format="MAC 00:05:86:71:5d:11">00:05:86:71:5d:11</current-physical-address>
            <hardware-physical-address junos:format="MAC 00:05:86:71:5d:11">00:05:86:71:5d:11</hardware-physical-address>
            <interface-flapped junos:seconds="0">Never</interface-flapped>
            <traffic-statistics junos:style="brief">
                <input-packets>0</input-packets>
                <output-packets>0</output-packets>
            </traffic-statistics>
        </physical-interface>
        <physical-interface>
            <name>demux0</name>
            <admin-status junos:format="Enabled">up</admin-status>
            <oper-status>up</oper-status>
            <local-index>129</local-index>
            <snmp-index>502</snmp-index>
            <if-type>Software-Pseudo</if-type>
            <mtu>9192</mtu>
            <clocking>1</clocking>
            <if-device-flags>
                <ifdf-present/>
                <ifdf-running/>
            </if-device-flags>
            <if-config-flags>
                <iff-point-to-point/>
                <iff-snmp-traps/>
            </if-config-flags>
            <link-type>Full-Duplex</link-type>
            <if-media-flags>
                <ifmf-none/>
            </if-media-flags>
            <interface-flapped junos:seconds="0">Never</interface-flapped>
            <traffic-statistics junos:style="brief">
                <input-packets>0</input-packets>
                <output-packets>0</output-packets>
            </traffic-statistics>
        </physical-interface>
        <physical-interface>
            <name>dsc</name>
            <admin-status junos:format="Enabled">up</admin-status>
            <oper-status>up</oper-status>
            <local-index>5</local-index>
            <snmp-index>5</snmp-index>
            <if-type>Software-Pseudo</if-type>
            <mtu>Unlimited</mtu>
            <if-device-flags>
                <ifdf-present/>
                <ifdf-running/>
            </if-device-flags>
            <if-config-flags>
                <iff-point-to-point/>
                <iff-snmp-traps/>
            </if-config-flags>
            <if-media-flags>
                <ifmf-none/>
            </if-media-flags>
            <interface-flapped junos:seconds="0">Never</interface-flapped>
            <traffic-statistics junos:style="brief">
                <input-packets>0</input-packets>
                <output-packets>0</output-packets>
            </traffic-statistics>
        </physical-interface>
        <physical-interface>
            <name>em0</name>
            <admin-status junos:format="Enabled">up</admin-status>
            <oper-status>up</oper-status>
            <local-index>8</local-index>
            <snmp-index>17</snmp-index>
            <if-type>Ethernet</if-type>
            <link-level-type>Ethernet</link-level-type>
            <mtu>1514</mtu>
            <speed>1000mbps</speed>
            <if-device-flags>
                <ifdf-present/>
                <ifdf-running/>
            </if-device-flags>
            <if-config-flags>
                <iff-snmp-traps/>
            </if-config-flags>
            <link-type>Full-Duplex</link-type>
            <if-media-flags>
                <internal-flags>0x4</internal-flags>
            </if-media-flags>
            <current-physical-address junos:format="MAC 08:00:27:6e:23:6d">08:00:27:6e:23:6d</current-physical-address>
            <hardware-physical-address junos:format="MAC 08:00:27:6e:23:6d">08:00:27:6e:23:6d</hardware-physical-address>
            <interface-flapped junos:seconds="865248">2018-07-16 11:54:48 UTC (1w3d 00:20 ago)</interface-flapped>
            <traffic-statistics junos:style="brief">
                <input-packets>1145633</input-packets>
                <output-packets>232184</output-packets>
            </traffic-statistics>
            <logical-interface>
                <name>em0.0</name>
                <local-index>64</local-index>
                <snmp-index>18</snmp-index>
                <if-config-flags>
                    <iff-snmp-traps/>
                </if-config-flags>
                <encapsulation>ENET2</encapsulation>
                <traffic-statistics junos:style="brief">
                    <input-packets>798298</input-packets>
                    <output-packets>232159</output-packets>
                </traffic-statistics>
                <filter-information>
                </filter-information>
                <address-family>
                    <address-family-name>inet</address-family-name>
                    <mtu>1500</mtu>
                    <address-family-flags>
                        <ifff-sendbcast-pkt-to-re/>
                    </address-family-flags>
                    <interface-address>
                        <ifa-flags>
                            <ifaf-current-preferred/>
                            <ifaf-current-primary/>
                        </ifa-flags>
                        <ifa-destination>192.168.10/24</ifa-destination>
                        <ifa-local>192.168.10.201</ifa-local>
                        <ifa-broadcast>192.168.10.255</ifa-broadcast>
                    </interface-address>
                </address-family>
            </logical-interface>
        </physical-interface>
        <physical-interface>
            <name>em1</name>
            <admin-status junos:format="Enabled">up</admin-status>
            <oper-status>up</oper-status>
            <local-index>9</local-index>
            <snmp-index>23</snmp-index>
            <if-type>Ethernet</if-type>
            <link-level-type>Ethernet</link-level-type>
            <mtu>1514</mtu>
            <speed>1000mbps</speed>
            <if-device-flags>
                <ifdf-present/>
                <ifdf-running/>
            </if-device-flags>
            <if-config-flags>
                <iff-snmp-traps/>
            </if-config-flags>
            <link-type>Full-Duplex</link-type>
            <if-media-flags>
                <internal-flags>0x4</internal-flags>
            </if-media-flags>
            <current-physical-address junos:format="MAC 08:00:27:9b:28:c7">08:00:27:9b:28:c7</current-physical-address>
            <hardware-physical-address junos:format="MAC 08:00:27:9b:28:c7">08:00:27:9b:28:c7</hardware-physical-address>
            <interface-flapped junos:seconds="1276873">2018-07-11 17:34:23 UTC (2w0d 18:41 ago)</interface-flapped>
            <traffic-statistics junos:style="brief">
                <input-packets>564057</input-packets>
                <output-packets>2178</output-packets>
            </traffic-statistics>
            <logical-interface>
                <name>em1.0</name>
                <local-index>66</local-index>
                <snmp-index>24</snmp-index>
                <if-config-flags>
                    <iff-snmp-traps/>
                </if-config-flags>
                <encapsulation>ENET2</encapsulation>
                <traffic-statistics junos:style="brief">
                    <input-packets>564055</input-packets>
                    <output-packets>2178</output-packets>
                </traffic-statistics>
                <filter-information>
                </filter-information>
                <address-family>
                    <address-family-name>inet</address-family-name>
                    <mtu>1500</mtu>
                    <address-family-flags>
                        <ifff-is-primary/>
                        <ifff-sendbcast-pkt-to-re/>
                    </address-family-flags>
                    <interface-address>
                        <ifa-flags>
                            <ifaf-current-default/>
                            <ifaf-current-preferred/>
                            <ifaf-current-primary/>
                        </ifa-flags>
                        <ifa-destination>192.168.56/24</ifa-destination>
                        <ifa-local>192.168.56.2</ifa-local>
                        <ifa-broadcast>192.168.56.255</ifa-broadcast>
                    </interface-address>
                </address-family>
            </logical-interface>
        </physical-interface>
        <physical-interface>
            <name>gre</name>
            <admin-status junos:format="Enabled">up</admin-status>
            <oper-status>up</oper-status>
            <local-index>10</local-index>
            <snmp-index>8</snmp-index>
            <if-type>GRE</if-type>
            <link-level-type>GRE</link-level-type>
            <mtu>Unlimited</mtu>
            <speed>Unlimited</speed>
            <if-device-flags>
                <ifdf-present/>
                <ifdf-running/>
            </if-device-flags>
            <if-config-flags>
                <iff-point-to-point/>
                <iff-snmp-traps/>
            </if-config-flags>
            <traffic-statistics junos:style="brief">
                <input-packets>0</input-packets>
                <output-packets>0</output-packets>
            </traffic-statistics>
        </physical-interface>
        <physical-interface>
            <name>ipip</name>
            <admin-status junos:format="Enabled">up</admin-status>
            <oper-status>up</oper-status>
            <local-index>11</local-index>
            <snmp-index>9</snmp-index>
            <if-type>IPIP</if-type>
            <link-level-type>IP-over-IP</link-level-type>
            <mtu>Unlimited</mtu>
            <speed>Unlimited</speed>
            <if-device-flags>
                <ifdf-present/>
                <ifdf-running/>
            </if-device-flags>
            <if-config-flags>
                <iff-snmp-traps/>
            </if-config-flags>
            <traffic-statistics junos:style="brief">
                <input-packets>0</input-packets>
                <output-packets>0</output-packets>
            </traffic-statistics>
        </physical-interface>
        <physical-interface>
            <name>irb</name>
            <admin-status junos:format="Enabled">up</admin-status>
            <oper-status>up</oper-status>
            <local-index>133</local-index>
            <snmp-index>503</snmp-index>
            <if-type>Ethernet</if-type>
            <link-level-type>Ethernet</link-level-type>
            <mtu>1514</mtu>
            <if-device-flags>
                <ifdf-present/>
                <ifdf-running/>
            </if-device-flags>
            <if-config-flags>
                <iff-snmp-traps/>
            </if-config-flags>
            <link-type>Full-Duplex</link-type>
            <if-media-flags>
                <ifmf-none/>
            </if-media-flags>
            <current-physical-address junos:format="MAC 00:05:86:71:61:20">00:05:86:71:61:20</current-physical-address>
            <hardware-physical-address junos:format="MAC 00:05:86:71:61:20">00:05:86:71:61:20</hardware-physical-address>
            <interface-flapped junos:seconds="0">Never</interface-flapped>
            <traffic-statistics junos:style="brief">
                <input-packets>0</input-packets>
                <output-packets>0</output-packets>
            </traffic-statistics>
        </physical-interface>
        <physical-interface>
            <name>lo0</name>
            <admin-status junos:format="Enabled">up</admin-status>
            <oper-status>up</oper-status>
            <local-index>6</local-index>
            <snmp-index>6</snmp-index>
            <if-type>Loopback</if-type>
            <mtu>Unlimited</mtu>
            <if-device-flags>
                <ifdf-present/>
                <ifdf-running/>
                <ifdf-loopback/>
            </if-device-flags>
            <if-config-flags>
                <iff-snmp-traps/>
            </if-config-flags>
            <if-media-flags>
                <ifmf-none/>
            </if-media-flags>
            <interface-flapped junos:seconds="0">Never</interface-flapped>
            <traffic-statistics junos:style="brief">
                <input-packets>2892</input-packets>
                <output-packets>2892</output-packets>
            </traffic-statistics>
            <logical-interface>
                <name>lo0.16384</name>
                <local-index>67</local-index>
                <snmp-index>21</snmp-index>
                <if-config-flags>
                    <iff-snmp-traps/>
                </if-config-flags>
                <encapsulation>Unspecified</encapsulation>
                <traffic-statistics junos:style="brief">
                    <input-packets>0</input-packets>
                    <output-packets>0</output-packets>
                </traffic-statistics>
                <filter-information>
                </filter-information>
                <address-family>
                    <address-family-name>inet</address-family-name>
                    <mtu>Unlimited</mtu>
                    <address-family-flags>
                        <ifff-none/>
                    </address-family-flags>
                    <interface-address heading="Addresses">
                        <ifa-local>127.0.0.1</ifa-local>
                    </interface-address>
                </address-family>
            </logical-interface>
            <logical-interface>
                <name>lo0.16385</name>
                <local-index>68</local-index>
                <snmp-index>22</snmp-index>
                <if-config-flags>
                    <iff-snmp-traps/>
                </if-config-flags>
                <encapsulation>Unspecified</encapsulation>
                <traffic-statistics junos:style="brief">
                    <input-packets>2892</input-packets>
                    <output-packets>2892</output-packets>
                </traffic-statistics>
                <filter-information>
                </filter-information>
                <address-family>
                    <address-family-name>inet</address-family-name>
                    <mtu>Unlimited</mtu>
                    <address-family-flags>
                        <ifff-none/>
                    </address-family-flags>
                    <interface-address>
                        <ifa-flags>
                            <ifaf-current-default/>
                            <ifaf-current-primary/>
                        </ifa-flags>
                        <ifa-local>128.0.0.4</ifa-local>
                    </interface-address>
                </address-family>
                <address-family>
                    <address-family-name>inet6</address-family-name>
                    <mtu>Unlimited</mtu>
                    <address-family-flags>
                        <ifff-none/>
                    </address-family-flags>
                    <interface-address>
                        <ifa-flags>
                            <internal-flags>0x800</internal-flags>
                        </ifa-flags>
                        <ifa-local>fe80::a00:270f:fc6e:236d</ifa-local>
                        <interface-address>
                            <in6-addr-flags>
                                <ifaf-none/>
                            </in6-addr-flags>
                        </interface-address>
                    </interface-address>
                </address-family>
            </logical-interface>
        </physical-interface>
        <physical-interface>
            <name>lsi</name>
            <admin-status junos:format="Enabled">up</admin-status>
            <oper-status>up</oper-status>
            <local-index>4</local-index>
            <snmp-index>4</snmp-index>
            <if-type>Software-Pseudo</if-type>
            <link-level-type>LSI</link-level-type>
            <mtu>1496</mtu>
            <speed>Unlimited</speed>
            <if-device-flags>
                <ifdf-present/>
                <ifdf-running/>
            </if-device-flags>
            <if-config-flags>
            </if-config-flags>
            <if-media-flags>
                <ifmf-none/>
            </if-media-flags>
            <interface-flapped junos:seconds="0">Never</interface-flapped>
            <traffic-statistics junos:style="brief">
                <input-packets>0</input-packets>
                <output-packets>0</output-packets>
            </traffic-statistics>
        </physical-interface>
        <physical-interface>
            <name>mtun</name>
            <admin-status junos:format="Enabled">up</admin-status>
            <oper-status>up</oper-status>
            <local-index>128</local-index>
            <snmp-index>12</snmp-index>
            <if-type>Multicast-GRE</if-type>
            <link-level-type>GRE</link-level-type>
            <mtu>Unlimited</mtu>
            <speed>Unlimited</speed>
            <if-device-flags>
                <ifdf-present/>
                <ifdf-running/>
            </if-device-flags>
            <if-config-flags>
                <iff-snmp-traps/>
            </if-config-flags>
            <traffic-statistics junos:style="brief">
                <input-packets>0</input-packets>
                <output-packets>0</output-packets>
            </traffic-statistics>
        </physical-interface>
        <physical-interface>
            <name>pimd</name>
            <admin-status junos:format="Enabled">up</admin-status>
            <oper-status>up</oper-status>
            <local-index>26</local-index>
            <snmp-index>11</snmp-index>
            <if-type>PIMD</if-type>
            <link-level-type>PIM-Decapsulator</link-level-type>
            <mtu>Unlimited</mtu>
            <speed>Unlimited</speed>
            <if-device-flags>
                <ifdf-present/>
                <ifdf-running/>
            </if-device-flags>
            <if-config-flags>
            </if-config-flags>
            <traffic-statistics junos:style="brief">
                <input-packets>0</input-packets>
                <output-packets>0</output-packets>
            </traffic-statistics>
        </physical-interface>
        <physical-interface>
            <name>pime</name>
            <admin-status junos:format="Enabled">up</admin-status>
            <oper-status>up</oper-status>
            <local-index>25</local-index>
            <snmp-index>10</snmp-index>
            <if-type>PIME</if-type>
            <link-level-type>PIM-Encapsulator</link-level-type>
            <mtu>Unlimited</mtu>
            <speed>Unlimited</speed>
            <if-device-flags>
                <ifdf-present/>
                <ifdf-running/>
            </if-device-flags>
            <if-config-flags>
            </if-config-flags>
            <traffic-statistics junos:style="brief">
                <input-packets>0</input-packets>
                <output-packets>0</output-packets>
            </traffic-statistics>
        </physical-interface>
        <physical-interface>
            <name>pip0</name>
            <admin-status junos:format="Enabled">up</admin-status>
            <oper-status>up</oper-status>
            <local-index>131</local-index>
            <snmp-index>504</snmp-index>
            <if-type>Ethernet</if-type>
            <link-level-type>Ethernet</link-level-type>
            <mtu>1514</mtu>
            <if-device-flags>
                <ifdf-present/>
                <ifdf-running/>
            </if-device-flags>
            <if-config-flags>
                <iff-snmp-traps/>
            </if-config-flags>
            <link-type>Full-Duplex</link-type>
            <if-media-flags>
                <ifmf-none/>
            </if-media-flags>
            <current-physical-address junos:format="MAC 00:05:86:71:60:e0">00:05:86:71:60:e0</current-physical-address>
            <hardware-physical-address junos:format="MAC 00:05:86:71:60:e0">00:05:86:71:60:e0</hardware-physical-address>
            <interface-flapped junos:seconds="0">Never</interface-flapped>
            <traffic-statistics junos:style="brief">
                <input-packets>0</input-packets>
                <output-packets>0</output-packets>
            </traffic-statistics>
        </physical-interface>
        <physical-interface>
            <name>pp0</name>
            <admin-status junos:format="Enabled">up</admin-status>
            <oper-status>up</oper-status>
            <local-index>132</local-index>
            <snmp-index>505</snmp-index>
            <if-type>PPPoE</if-type>
            <link-level-type>PPPoE</link-level-type>
            <mtu>1532</mtu>
            <if-device-flags>
                <ifdf-present/>
                <ifdf-running/>
            </if-device-flags>
            <if-config-flags>
                <iff-point-to-point/>
                <iff-snmp-traps/>
            </if-config-flags>
            <link-type>Full-Duplex</link-type>
            <if-media-flags>
                <ifmf-none/>
            </if-media-flags>
        </physical-interface>
        <physical-interface>
            <name>tap</name>
            <admin-status junos:format="Enabled">up</admin-status>
            <oper-status>up</oper-status>
            <local-index>12</local-index>
            <snmp-index>7</snmp-index>
            <if-type>Software-Pseudo</if-type>
            <link-level-type>Interface-Specific</link-level-type>
            <mtu>Unlimited</mtu>
            <speed>Unlimited</speed>
            <if-device-flags>
                <ifdf-present/>
                <ifdf-running/>
            </if-device-flags>
            <if-config-flags>
                <iff-snmp-traps/>
            </if-config-flags>
            <if-media-flags>
                <ifmf-none/>
            </if-media-flags>
            <interface-flapped junos:seconds="0">Never</interface-flapped>
            <traffic-statistics junos:style="brief">
                <input-packets>0</input-packets>
                <output-packets>0</output-packets>
            </traffic-statistics>
        </physical-interface>
    </interface-information>
    <cli>
        <banner></banner>
    </cli>
</rpc-reply>
'''

VERSION_MOCK = '''<rpc-reply xmlns:junos="http://xml.juniper.net/junos/12.1R1/junos">
    <software-information>
        <host-name>juniper-R1</host-name>
        <product-model>olive</product-model>
        <product-name>olive</product-name>
        <package-information>
            <name>junos</name>
            <comment>JUNOS Base OS boot [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jbase</name>
            <comment>JUNOS Base OS Software Suite [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jkernel</name>
            <comment>JUNOS Kernel Software Suite [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jcrypto</name>
            <comment>JUNOS Crypto Software Suite [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jpfe-common</name>
            <comment>JUNOS Packet Forwarding Engine Support (M/T Common) [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jpfe</name>
            <comment>JUNOS Packet Forwarding Engine Support (M20/M40) [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jdocs</name>
            <comment>JUNOS Online Documentation [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jservices-voice</name>
            <comment>JUNOS Voice Services Container package [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jservices-bgf</name>
            <comment>JUNOS Border Gateway Function package [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jservices-aacl</name>
            <comment>JUNOS Services AACL Container package [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jservices-llpdf</name>
            <comment>JUNOS Services LL-PDF Container package [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jservices-ptsp</name>
            <comment>JUNOS Services PTSP Container package [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jservices-sfw</name>
            <comment>JUNOS Services Stateful Firewall [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jservices-nat</name>
            <comment>JUNOS Services NAT [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jservices-alg</name>
            <comment>JUNOS Services Application Level Gateways [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jservices-cpcd</name>
            <comment>JUNOS Services Captive Portal and Content Delivery Container package [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jservices-rpm</name>
            <comment>JUNOS Services RPM [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jservices-hcm</name>
            <comment>JUNOS Services HTTP Content Management package [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jservices-appid</name>
            <comment>JUNOS AppId Services [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jservices-idp</name>
            <comment>JUNOS IDP Services [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jservices-crypto-base</name>
            <comment>JUNOS Services Crypto [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jservices-ssl</name>
            <comment>JUNOS Services SSL [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jservices-ipsec</name>
            <comment>JUNOS Services IPSec [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jruntime</name>
            <comment>JUNOS Runtime Software Suite [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jroute</name>
            <comment>JUNOS Routing Software Suite [12.1R1.9]</comment>
        </package-information>
        <package-information>
            <name>jweb</name>
            <comment>JUNOS Web Management [12.1R1.9]</comment>
        </package-information>
    </software-information>
    <cli>
        <banner></banner>
    </cli>
</rpc-reply>'''
HARDWARE_MOCK = '''<rpc-reply xmlns:junos="http://xml.juniper.net/junos/12.1X46/junos">
    <chassis-inventory xmlns="http://xml.juniper.net/junos/12.1X46/junos-chassis">
        <chassis junos:style="inventory">
            <name>Chassis</name>
            <serial-number>aaf5fe5f9b88</serial-number>
            <description>FIREFLY-PERIMETER</description>
            <chassis-module>
                <name>Midplane</name>
            </chassis-module>
            <chassis-module>
                <name>System IO</name>
            </chassis-module>
            <chassis-module>
                <name>Routing Engine</name>
                <description>FIREFLY-PERIMETER RE</description>
            </chassis-module>
            <chassis-module>
                <name>FPC 0</name>
                <description>Virtual FPC</description>
                <chassis-sub-module>
                    <name>PIC 0</name>
                    <description>Virtual GE</description>
                </chassis-sub-module>
            </chassis-module>
            <chassis-module>
                <name>Power Supply 0</name>
            </chassis-module>
        </chassis>
    </chassis-inventory>
    <cli>
        <banner></banner>
    </cli>
</rpc-reply>'''

VLAN_MOCK = \
    '''<rpc-reply xmlns:junos="http://xml.juniper.net/junos/12.1R1/junos">
    <switching-interface-information junos:style="detail">
        <interface>
            <interface-name>em0.0</interface-name>
            <interface-id>67</interface-id>
            <interface-port-mode>Access</interface-port-mode>
            <interface-state>down</interface-state>
            <interface-ether-type>8100</interface-ether-type>
            <interface-vlan-member-list>
                <interface-vlan-member>
                    <interface-vlan-name>voice</interface-vlan-name>
                    <interface-vlan-member-tagid>1000</interface-vlan-member-tagid>
                    <interface-vlan-member-tagness>untagged</interface-vlan-member-tagness>
                    <blocking-status junos:emit="emit">unblocked</blocking-status>
                </interface-vlan-member>
            </interface-vlan-member-list>
            <interface-mac-count>0</interface-mac-count>
        </interface>
        <interface>
            <interface-name>ge-0/0/1.0</interface-name>
            <interface-id>68</interface-id>
            <interface-port-mode>Trunk</interface-port-mode>
            <interface-state>down</interface-state>
            <interface-ether-type>8100</interface-ether-type>
            <interface-vlan-member-list>
            </interface-vlan-member-list>
            <interface-mac-count>0</interface-mac-count>
        </interface>
        <interface>
            <interface-name>ge-0/0/2.0</interface-name>
            <interface-id>69</interface-id>
            <interface-port-mode>Trunk</interface-port-mode>
            <interface-state>down</interface-state>
            <interface-ether-type>8100</interface-ether-type>
            <interface-vlan-member-list>
                <interface-vlan-member>
                    <interface-vlan-name>network</interface-vlan-name>
                    <interface-vlan-member-tagid>3000</interface-vlan-member-tagid>
                    <interface-vlan-member-tagness>tagged</interface-vlan-member-tagness>
                    <blocking-status junos:emit="emit">unblocked</blocking-status>
                </interface-vlan-member>
                <interface-vlan-member>
                    <interface-vlan-name>office</interface-vlan-name>
                    <interface-vlan-member-tagid>200</interface-vlan-member-tagid>
                    <interface-vlan-member-tagness>tagged</interface-vlan-member-tagness>
                    <blocking-status junos:emit="emit">unblocked</blocking-status>
                </interface-vlan-member>
                <interface-vlan-member>
                    <interface-vlan-name>voice</interface-vlan-name>
                    <interface-vlan-member-tagid>1000</interface-vlan-member-tagid>
                    <interface-vlan-member-tagness>tagged</interface-vlan-member-tagness>
                    <blocking-status junos:emit="emit">unblocked</blocking-status>
                </interface-vlan-member>
            </interface-vlan-member-list>
            <interface-mac-count>0</interface-mac-count>
        </interface>
        <interface>
            <interface-name>ge-0/0/3.0</interface-name>
            <interface-id>70</interface-id>
            <interface-port-mode>Trunk</interface-port-mode>
            <interface-state>down</interface-state>
            <interface-ether-type>8100</interface-ether-type>
            <interface-vlan-member-list>
                <interface-vlan-member>
                    <interface-vlan-name>office</interface-vlan-name>
                    <interface-vlan-member-tagid>200</interface-vlan-member-tagid>
                    <interface-vlan-member-tagness>tagged</interface-vlan-member-tagness>
                    <blocking-status junos:emit="emit">unblocked</blocking-status>
                </interface-vlan-member>
                <interface-vlan-member>
                    <interface-vlan-name>voice</interface-vlan-name>
                    <interface-vlan-member-tagid>1000</interface-vlan-member-tagid>
                    <interface-vlan-member-tagness>tagged</interface-vlan-member-tagness>
                    <blocking-status junos:emit="emit">unblocked</blocking-status>
                </interface-vlan-member>
            </interface-vlan-member-list>
            <interface-mac-count>0</interface-mac-count>
        </interface>
    </switching-interface-information>
</rpc-reply>'''

VLAN_MOCK2 = '''
<rpc-reply xmlns:junos="http://xml.juniper.net/junos/12.1R1/junos">
    <l2ng-l2ald-iff-interface-information>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae0.0</l2iff-interface-name>
        <l2iff-interface-handle>0x9bb3a00</l2iff-interface-handle>
        <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
        <l2iff-interface-index>566</l2iff-interface-index>
        <l2iff-interface-generation>174</l2iff-interface-generation>
        <l2iff-interface-flags>UP</l2iff-interface-flags>
        <l2iff-interface-ifd-index>640</l2iff-interface-ifd-index>
        <l2iff-interface-rt-index>6</l2iff-interface-rt-index>
        <l2iff-interface-ifl-index>566</l2iff-interface-ifl-index>
        <l2iff-interface-af-value>50</l2iff-interface-af-value>
        <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae0.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9ba7b00</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>129</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>26</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>90</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>server</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>2</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>untagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae1.0</l2iff-interface-name>
        <l2iff-interface-handle>0x9bb3c80</l2iff-interface-handle>
        <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
        <l2iff-interface-index>567</l2iff-interface-index>
        <l2iff-interface-generation>175</l2iff-interface-generation>
        <l2iff-interface-flags>UP</l2iff-interface-flags>
        <l2iff-interface-ifd-index>641</l2iff-interface-ifd-index>
        <l2iff-interface-rt-index>6</l2iff-interface-rt-index>
        <l2iff-interface-ifl-index>567</l2iff-interface-ifl-index>
        <l2iff-interface-af-value>50</l2iff-interface-af-value>
        <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae1.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9ba7c00</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>130</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>26</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>90</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>server</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>3</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>untagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae10.0</l2iff-interface-name>
        <l2iff-interface-handle>0x9bb3e80</l2iff-interface-handle>
        <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
        <l2iff-interface-index>568</l2iff-interface-index>
        <l2iff-interface-generation>176</l2iff-interface-generation>
        <l2iff-interface-flags>UP</l2iff-interface-flags>
        <l2iff-interface-ifd-index>650</l2iff-interface-ifd-index>
        <l2iff-interface-rt-index>6</l2iff-interface-rt-index>
        <l2iff-interface-ifl-index>568</l2iff-interface-ifl-index>
        <l2iff-interface-af-value>50</l2iff-interface-af-value>
        <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>23</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae10.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9ba7d00</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>131</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>3</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>390</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>BACKUP</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>12</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae10.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9ba7e00</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>132</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>5</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>300</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>CAMERA1</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>12</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae10.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9ba7f00</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>133</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>6</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>301</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>CAMERA2</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>12</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae10.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfd000</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>134</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>7</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>302</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>CAMERA3</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>12</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae10.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfd100</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>135</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>8</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>16</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>INFRA</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>12</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae10.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfd200</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>136</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>9</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>420</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>LABEQUIP</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>12</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae10.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfd300</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>137</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>10</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>422</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>LABEQUIP-02</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>12</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae10.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfd400</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>138</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>423</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>LABEQUIP-03</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>12</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae10.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfd500</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>139</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>15</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>400</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>SERVERAUTO</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>12</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae10.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfd600</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>140</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>16</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>380</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>STORAGE</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>12</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae10.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfd700</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>141</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>17</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>370</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>UTILITY</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>12</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae10.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfd800</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>142</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>23</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>80</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>office</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>12</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae10.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfd900</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>143</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>24</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>100</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>production</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>19</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>12</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae10.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfda00</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>144</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>25</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>140</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>public</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>12</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae10.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfdb00</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>145</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>26</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>90</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>server</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>2</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>12</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae10.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfdc00</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>146</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>28</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>70</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>voice</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>12</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae11.0</l2iff-interface-name>
        <l2iff-interface-handle>0x9bf8100</l2iff-interface-handle>
        <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
        <l2iff-interface-index>569</l2iff-interface-index>
        <l2iff-interface-generation>177</l2iff-interface-generation>
        <l2iff-interface-flags>UP</l2iff-interface-flags>
        <l2iff-interface-ifd-index>651</l2iff-interface-ifd-index>
        <l2iff-interface-rt-index>6</l2iff-interface-rt-index>
        <l2iff-interface-ifl-index>569</l2iff-interface-ifl-index>
        <l2iff-interface-af-value>50</l2iff-interface-af-value>
        <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae11.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfdd00</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>147</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>26</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>90</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>server</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>13</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>untagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae12.0</l2iff-interface-name>
        <l2iff-interface-handle>0x9bf8380</l2iff-interface-handle>
        <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
        <l2iff-interface-index>570</l2iff-interface-index>
        <l2iff-interface-generation>178</l2iff-interface-generation>
        <l2iff-interface-flags>UP</l2iff-interface-flags>
        <l2iff-interface-ifd-index>652</l2iff-interface-ifd-index>
        <l2iff-interface-rt-index>6</l2iff-interface-rt-index>
        <l2iff-interface-ifl-index>570</l2iff-interface-ifl-index>
        <l2iff-interface-af-value>50</l2iff-interface-af-value>
        <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae12.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfde00</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>148</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>26</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>90</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>server</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>14</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>untagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae13.0</l2iff-interface-name>
        <l2iff-interface-handle>0x9bf8580</l2iff-interface-handle>
        <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
        <l2iff-interface-index>571</l2iff-interface-index>
        <l2iff-interface-generation>179</l2iff-interface-generation>
        <l2iff-interface-flags>UP</l2iff-interface-flags>
        <l2iff-interface-ifd-index>653</l2iff-interface-ifd-index>
        <l2iff-interface-rt-index>6</l2iff-interface-rt-index>
        <l2iff-interface-ifl-index>571</l2iff-interface-ifl-index>
        <l2iff-interface-af-value>50</l2iff-interface-af-value>
        <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae13.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfdf00</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>149</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>26</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>90</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>server</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>15</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>untagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae14.0</l2iff-interface-name>
        <l2iff-interface-handle>0x9bb3b00</l2iff-interface-handle>
        <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
        <l2iff-interface-index>572</l2iff-interface-index>
        <l2iff-interface-generation>180</l2iff-interface-generation>
        <l2iff-interface-flags>UP</l2iff-interface-flags>
        <l2iff-interface-ifd-index>654</l2iff-interface-ifd-index>
        <l2iff-interface-rt-index>6</l2iff-interface-rt-index>
        <l2iff-interface-ifl-index>572</l2iff-interface-ifl-index>
        <l2iff-interface-af-value>50</l2iff-interface-af-value>
        <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>59</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae14.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfa000</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>150</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>2</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>360</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>AV</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>16</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae14.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfa100</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>151</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>3</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>390</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>BACKUP</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>16</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae14.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfa200</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>152</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>350</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>BADGE</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>16</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae14.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfa300</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>153</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>5</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>300</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>CAMERA1</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>16</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae14.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfa400</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>154</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>6</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>301</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>CAMERA2</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>16</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae14.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfa500</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>155</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>7</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>302</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>CAMERA3</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>16</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae14.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfa600</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>156</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>8</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>16</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>INFRA</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>21</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>16</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae14.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfa700</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>157</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>9</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>420</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>LABEQUIP</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>16</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae14.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfa800</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>158</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>10</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>422</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>LABEQUIP-02</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>16</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae14.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfa900</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>159</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>423</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>LABEQUIP-03</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>16</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae14.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfaa00</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>160</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>15</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>400</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>SERVERAUTO</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>16</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae14.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfab00</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>161</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>16</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>380</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>STORAGE</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>16</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
      <l2ng-l2ald-iff-interface-entry junos:style="detail">
        <l2iff-interface-name>ae14.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x9bfac00</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>162</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>17</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-vlan-id>370</l2iff-interface-vlan-id>
        <l2iff-interface-vlan-name>UTILITY</l2iff-interface-vlan-name>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>294912</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>16</l2iff-interface-vstp-index>
        <l2iff-interface-vlan-member-stp-state>Forwarding</l2iff-interface-vlan-member-stp-state>
        <l2iff-interface-vlan-member-tagness>tagged</l2iff-interface-vlan-member-tagness>
        <l2iff-interface-rewrite-op/>
      </l2ng-l2ald-iff-interface-entry>
    </l2ng-l2ald-iff-interface-information>
</rpc-reply>
'''


VERSION_MOCK2 = '''<multi-routing-engine-results><multi-routing-engine-item><re-name>fpc0</re-name><software-information>
<host-name/>
<product-model>ex4300-24t</product-model>
<product-name>ex4300-24t</product-name>
<package-information>
<name>junos</name>
<comment>JUNOS EX  Software Suite [13.2X51-D21.1]</comment>
</package-information>
<package-information>
<name>fips-mode-powerpc</name>
<comment>JUNOS FIPS mode utilities [13.2X51-D21.1]</comment>
</package-information>
<package-information>
<name>jdocs-ex</name>
<comment>JUNOS Online Documentation [13.2X51-D21.1]</comment>
</package-information>
<package-information>
<name>junos-ex-4300</name>
<comment>JUNOS EX 4300 Software Suite [13.2X51-D21.1]</comment>
</package-information>
<package-information>
<name>jweb-ex</name>
<comment>JUNOS Web Management [13.2X51-D21.1]</comment>
</package-information>
<package-information>
<name>py-base-powerpc</name>
<comment>JUNOS py-base-powerpc [13.2X51-D21.1]</comment>
</package-information>
</software-information>
</multi-routing-engine-item><multi-routing-engine-item><re-name>fpc1</re-name><software-information>
<host-name/>
<product-model>ex4300-24t</product-model>
<product-name>ex4300-24t</product-name>
<package-information>
<name>junos</name>
<comment>JUNOS EX  Software Suite [13.2X51-D21.1]</comment>
</package-information>
<package-information>
<name>fips-mode-powerpc</name>
<comment>JUNOS FIPS mode utilities [13.2X51-D21.1]</comment>
</package-information>
<package-information>
<name>jdocs-ex</name>
<comment>JUNOS Online Documentation [13.2X51-D21.1]</comment>
</package-information>
<package-information>
<name>junos-ex-4300</name>
<comment>JUNOS EX 4300 Software Suite [13.2X51-D21.1]</comment>
</package-information>
<package-information>
<name>jweb-ex</name>
<comment>JUNOS Web Management [13.2X51-D21.1]</comment>
</package-information>
<package-information>
<name>py-base-powerpc</name>
<comment>JUNOS py-base-powerpc [13.2X51-D21.1]</comment>
</package-information>
</software-information>
</multi-routing-engine-item></multi-routing-engine-results>
'''

LLDP_MOCK = '''<rpc-reply xmlns:junos="http://xml.juniper.net/junos/13.3R6/junos">
    <lldp-neighbors-information junos:style="brief">
        <lldp-neighbor-information>
            <lldp-local-port-id>xe-0/1/1</lldp-local-port-id>
            <lldp-local-parent-interface-name>ae7</lldp-local-parent-interface-name>
            <lldp-remote-chassis-id-subtype>Mac address</lldp-remote-chassis-id-subtype>
            <lldp-remote-chassis-id>00:1c:73:ee:c0:46</lldp-remote-chassis-id>
            <lldp-remote-port-id-subtype>Interface name</lldp-remote-port-id-subtype>
            <lldp-remote-port-id>Ethernet3/29/1</lldp-remote-port-id>
            <lldp-remote-system-name>core01.sjc01</lldp-remote-system-name>
        </lldp-neighbor-information>
        <lldp-neighbor-information>
            <lldp-local-port-id>xe-0/3/3</lldp-local-port-id>
            <lldp-local-parent-interface-name>ae7</lldp-local-parent-interface-name>
            <lldp-remote-chassis-id-subtype>Mac address</lldp-remote-chassis-id-subtype>
            <lldp-remote-chassis-id>00:1c:73:ee:c0:46</lldp-remote-chassis-id>
            <lldp-remote-port-id-subtype>Interface name</lldp-remote-port-id-subtype>
            <lldp-remote-port-id>Ethernet3/29/2</lldp-remote-port-id>
            <lldp-remote-system-name>core01.sjc01</lldp-remote-system-name>
        </lldp-neighbor-information>
        <lldp-neighbor-information>
            <lldp-local-port-id>xe-2/0/5</lldp-local-port-id>
            <lldp-local-parent-interface-name>ae7</lldp-local-parent-interface-name>
            <lldp-remote-chassis-id-subtype>Mac address</lldp-remote-chassis-id-subtype>
            <lldp-remote-chassis-id>00:1c:73:ee:c0:46</lldp-remote-chassis-id>
            <lldp-remote-port-id-subtype>Interface name</lldp-remote-port-id-subtype>
            <lldp-remote-port-id>Ethernet3/29/3</lldp-remote-port-id>
            <lldp-remote-system-name>core01.sjc01</lldp-remote-system-name>
        </lldp-neighbor-information>
    </lldp-neighbors-information>
    <cli>
        <banner>{master}</banner>
    </cli>
</rpc-reply>'''

LLDP_MOCK2 = '''<rpc-reply xmlns:junos="http://xml.juniper.net/junos/13.3R6/junos">
    <lldp-neighbors-information junos:style="brief">
        <lldp-neighbor-information>
            <lldp-local-port-id>xe-0/1/1</lldp-local-port-id>
            <lldp-local-parent-interface-name>ae7</lldp-local-parent-interface-name>
            <lldp-remote-chassis-id-subtype>Mac address</lldp-remote-chassis-id-subtype>
            <lldp-remote-chassis-id>00:1c:73:ee:c1:46</lldp-remote-chassis-id>
            <lldp-remote-port-id-subtype>Interface name</lldp-remote-port-id-subtype>
            <lldp-remote-port-id>Ethernet3/42/1</lldp-remote-port-id>
            <lldp-remote-system-name>core01.sjc01</lldp-remote-system-name>
        </lldp-neighbor-information>
        <lldp-neighbor-information>
            <lldp-local-port-id>xe-2/0/5</lldp-local-port-id>
            <lldp-local-parent-interface-name>ae7</lldp-local-parent-interface-name>
            <lldp-remote-chassis-id-subtype>Mac address</lldp-remote-chassis-id-subtype>
            <lldp-remote-chassis-id>00:1c:73:ee:c0:46</lldp-remote-chassis-id>
            <lldp-remote-port-id-subtype>Interface name</lldp-remote-port-id-subtype>
            <lldp-remote-port-id>Ethernet3/29/3</lldp-remote-port-id>
            <lldp-remote-system-name>leaf42.sjc01</lldp-remote-system-name>
        </lldp-neighbor-information>
    </lldp-neighbors-information>
    <cli>
        <banner>{master}</banner>
    </cli>
</rpc-reply>'''

BASE_MAC_MOCK = '''
        <chassis-mac-information xmlns:junos="http://xml.juniper.net/junos/12.3R12/junos">
          <fpc-mac-information>
            <slot>0</slot>
            <mac-address>ec:13:db:04:b4:00</mac-address>
            <count>64</count>
          </fpc-mac-information>
        </chassis-mac-information>
'''


def mock_query_basic_info():
    return ('Juniper-R1', [
        ('interface list', INTERFACE_MOCK),
        ('hardware', HARDWARE_MOCK),
        ('version', VERSION_MOCK),
        ('vlans', VLAN_MOCK),
        ('base-mac', BASE_MAC_MOCK),
    ])
