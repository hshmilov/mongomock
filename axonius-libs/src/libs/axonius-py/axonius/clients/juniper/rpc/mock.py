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
<l2ng-l2ald-iff-interface-information>
    <l2ng-l2ald-iff-interface-entry style="detail">
        <l2iff-interface-name>ae0.0</l2iff-interface-name>
        <l2iff-interface-handle>0x1d6e700</l2iff-interface-handle>
        <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
        <l2iff-interface-index>550</l2iff-interface-index>
        <l2iff-interface-generation>154</l2iff-interface-generation>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-ifd-index>640</l2iff-interface-ifd-index>
        <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
        <l2iff-interface-ifl-index>550</l2iff-interface-ifl-index>
        <l2iff-interface-af-value>50</l2iff-interface-af-value>
        <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>26</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
        <l2iff-interface-name>ae0.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x1d86000</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>129</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>7</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>21</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>1</l2iff-interface-vstp-index>
        <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
        <l2ng-l2ald-iff-interface-entry style="detail">
        <l2iff-interface-name>ae0.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x1d86100</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>130</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>8</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>1</l2iff-interface-vstp-index>
        <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
        <l2iff-interface-name>ae0.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x1d86200</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>131</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>9</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>1</l2iff-interface-vstp-index>
        <l2iff-interface-rewrite-op/>
        </l2ng-l2ald-iff-interface-entry>
        <l2ng-l2ald-iff-interface-entry style="detail">
        <l2iff-interface-name>ae0.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x1d86300</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>132</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>5</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>1</l2iff-interface-vstp-index>
        <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
        <l2iff-interface-name>ae1.0</l2iff-interface-name>
        <l2iff-interface-handle>0x1c4fc00</l2iff-interface-handle>
        <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
        <l2iff-interface-index>551</l2iff-interface-index>
        <l2iff-interface-generation>156</l2iff-interface-generation>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-ifd-index>641</l2iff-interface-ifd-index>
        <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
        <l2iff-interface-ifl-index>551</l2iff-interface-ifl-index>
        <l2iff-interface-af-value>50</l2iff-interface-af-value>
        <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>64</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
        <l2iff-interface-name>ae1.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x1d86900</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>133</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>6</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>2</l2iff-interface-vstp-index>
        <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
        <l2iff-interface-name>ae1.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x1d86a00</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>134</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>3</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>2</l2iff-interface-vstp-index>
        <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae1.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d86b00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>135</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>8</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>2</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae1.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d86c00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>136</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>10</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>19</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>2</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae1.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d86d00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>137</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>9</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>2</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae1.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d86e00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>138</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>4</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>2</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae1.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d86f00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>139</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>7</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>2</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae1.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d89000</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>140</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>6</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>2</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae1.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d89100</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>141</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>5</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>35</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>2</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae1.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d89200</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>142</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>2</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>2</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae14.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1c4fe00</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>552</l2iff-interface-index>
    <l2iff-interface-generation>157</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>654</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>552</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>141</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae14.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d89600</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>143</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>10</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>15</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae14.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d89700</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>144</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>3</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>15</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae14.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d89800</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>145</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>8</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>4</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>15</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae14.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d89900</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>146</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>10</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>9</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>15</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae14.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d89a00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>147</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>9</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>8</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>15</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae14.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d89b00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>148</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>11</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>15</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae14.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d89c00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>149</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>7</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>64</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>15</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae14.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d89d00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>150</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>6</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>15</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae14.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d89e00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>151</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>5</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>35</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>15</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae14.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d89f00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>152</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>2</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>15</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae15.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1d79b80</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>553</l2iff-interface-index>
    <l2iff-interface-generation>158</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>655</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>553</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>20</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae15.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d8a000</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>153</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>3</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>16</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae15.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d8a100</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>154</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>3</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>16</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae15.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d8a200</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>155</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>8</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>16</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae15.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d8a300</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>156</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>10</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>16</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae15.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d8a400</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>157</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>9</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>3</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>16</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae15.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d8a500</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>158</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>5</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>16</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae15.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d8a600</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>159</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>7</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>6</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>16</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae15.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d8a700</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>160</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>6</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>16</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae15.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d8a800</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>161</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>5</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>2</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>16</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae15.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d8a900</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>162</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>2</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>16</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae2.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1d79e00</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>554</l2iff-interface-index>
    <l2iff-interface-generation>159</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>642</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>554</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>23</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae2.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d8aa00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>163</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>7</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>21</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>3</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae2.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d8ab00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>164</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>9</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>3</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae2.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d8ac00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>165</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>2</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>3</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae22.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1d79d00</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>555</l2iff-interface-index>
    <l2iff-interface-generation>160</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>662</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>555</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>36</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae22.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d8ad00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>166</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>3</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>4</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>23</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae22.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d8ae00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>167</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>32</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>23</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae23.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1d8b080</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>556</l2iff-interface-index>
    <l2iff-interface-generation>161</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>663</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>556</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae23.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d8f700</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>168</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>5</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>1</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>24</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae3.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1d8b200</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>557</l2iff-interface-index>
    <l2iff-interface-generation>162</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>643</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>557</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>38</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae3.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d8f800</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>169</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>7</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>19</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>4</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae3.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d8f900</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>170</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>9</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>4</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae3.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d8fa00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>171</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>18</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>4</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae4.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1d8b100</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>558</l2iff-interface-index>
    <l2iff-interface-generation>163</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>644</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>558</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>24</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae4.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d8ff00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>172</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>7</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>21</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>5</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae4.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d91000</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>173</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>9</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>5</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae4.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d91100</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>174</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>3</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>5</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae5.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1d8b400</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>559</l2iff-interface-index>
    <l2iff-interface-generation>164</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>645</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>559</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>22</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae5.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d91400</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>175</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>4</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>6</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae5.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d91500</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>176</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>5</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>5</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>6</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae5.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d91600</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>177</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>7</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>8</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>6</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae5.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d91700</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>178</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>9</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>6</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae5.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d91800</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>179</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>10</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>6</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae5.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d91900</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>180</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>4</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>6</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae6.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1d8b580</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>560</l2iff-interface-index>
    <l2iff-interface-generation>165</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>646</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>560</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>5</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae6.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d91c00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>181</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>2</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>7</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae6.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d91d00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>182</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>5</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>7</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae6.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d91e00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>183</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>7</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>7</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae6.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1d91f00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>184</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>9</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>7</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae6.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1da3000</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>185</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>10</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>7</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae6.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1da3100</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>186</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>3</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>7</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae7.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1d8b700</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>561</l2iff-interface-index>
    <l2iff-interface-generation>166</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>647</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>561</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae7.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1da3400</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>187</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>9</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>1</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>8</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae7.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1da3500</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>188</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>1</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>8</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae8.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1d8b800</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>562</l2iff-interface-index>
    <l2iff-interface-generation>167</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>648</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>562</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>119</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae8.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1da3600</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>189</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>9</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>9</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae8.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1da3700</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>190</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>3</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>9</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae8.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1da3800</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>191</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>8</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>3</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>9</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae8.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1da3900</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>192</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>10</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>8</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>9</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae8.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1da3a00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>193</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>9</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>31</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>9</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae8.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1da3b00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>194</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>8</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>9</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae8.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1da3c00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>195</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>7</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>51</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>9</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae8.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1da3d00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>196</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>6</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>9</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae8.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1da3e00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>197</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>5</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>9</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>9</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ae8.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1da3f00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>198</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>2</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>2</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>9</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/10.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1daf100</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>579</l2iff-interface-index>
    <l2iff-interface-generation>186</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>680</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>579</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>2</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/10.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1da5800</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>199</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>9</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>2</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>35</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/11.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1daf480</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>580</l2iff-interface-index>
    <l2iff-interface-generation>187</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>681</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>580</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/11.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1da5900</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>200</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>36</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/12.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1daf600</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>581</l2iff-interface-index>
    <l2iff-interface-generation>188</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>682</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>581</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/12.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1da5a00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>201</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>37</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/13.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1daf380</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>582</l2iff-interface-index>
    <l2iff-interface-generation>189</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>683</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>582</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>3</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/13.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1da5b00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>202</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>3</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>38</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/14.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1daf780</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>583</l2iff-interface-index>
    <l2iff-interface-generation>190</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>684</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>583</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/14.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1da5c00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>203</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>39</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/15.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1daf800</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>584</l2iff-interface-index>
    <l2iff-interface-generation>191</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>685</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>584</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/15.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1da5d00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>204</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>40</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/16.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1daf980</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>585</l2iff-interface-index>
    <l2iff-interface-generation>192</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>686</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>585</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/16.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1da5e00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>205</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>3</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>41</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/16.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1da5f00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>206</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>8</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>41</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/16.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1db0000</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>207</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>10</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>41</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/17.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1dafb00</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>586</l2iff-interface-index>
    <l2iff-interface-generation>193</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>687</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>586</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/17.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1db0300</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>208</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>3</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>42</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/17.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1db0400</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>209</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>8</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>42</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/17.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1db0500</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>210</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>10</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>42</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/18.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1daf500</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>587</l2iff-interface-index>
    <l2iff-interface-generation>194</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>688</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>587</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/18.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1db0800</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>211</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>3</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>43</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/18.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1db0900</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>212</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>8</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>43</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/18.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1db0a00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>213</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>10</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>43</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/19.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1dafd00</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>588</l2iff-interface-index>
    <l2iff-interface-generation>195</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>689</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>588</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/19.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1db0b00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>214</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>3</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>44</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/19.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1db0c00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>215</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>8</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>44</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/19.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1db0d00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>216</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>10</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>44</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-1/0/20.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1dafe00</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>589</l2iff-interface-index>
    <l2iff-interface-generation>196</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>690</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>589</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
        <l2iff-interface-name>ge-1/0/20.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x1db0e00</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>217</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>3</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>45</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
        <l2iff-interface-name>ge-1/0/20.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x1db0f00</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>218</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>8</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>45</l2iff-interface-vstp-index>
        <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
        <l2iff-interface-name>ge-1/0/20.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x1db2000</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>219</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>10</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>45</l2iff-interface-vstp-index>
        <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
        <l2iff-interface-name>ge-1/0/23.0</l2iff-interface-name>
        <l2iff-interface-handle>0x1dc8080</l2iff-interface-handle>
        <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
        <l2iff-interface-index>591</l2iff-interface-index>
        <l2iff-interface-generation>198</l2iff-interface-generation>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-ifd-index>693</l2iff-interface-ifd-index>
        <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
        <l2iff-interface-ifl-index>591</l2iff-interface-ifl-index>
        <l2iff-interface-af-value>50</l2iff-interface-af-value>
        <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
        <l2iff-interface-name>ge-1/0/23.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x1db2500</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>220</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>5</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>48</l2iff-interface-vstp-index>
        <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
        <l2iff-interface-name>ge-0/0/5.0</l2iff-interface-name>
        <l2iff-interface-handle>0x1dc8580</l2iff-interface-handle>
        <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
        <l2iff-interface-index>601</l2iff-interface-index>
        <l2iff-interface-generation>208</l2iff-interface-generation>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-ifd-index>703</l2iff-interface-ifd-index>
        <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
        <l2iff-interface-ifl-index>601</l2iff-interface-ifl-index>
        <l2iff-interface-af-value>50</l2iff-interface-af-value>
        <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
        <l2iff-interface-name>ge-0/0/5.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x1db2800</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>221</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>7</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>58</l2iff-interface-vstp-index>
        <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
        <l2iff-interface-name>ge-0/0/9.0</l2iff-interface-name>
        <l2iff-interface-handle>0x1dc8800</l2iff-interface-handle>
        <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
        <l2iff-interface-index>604</l2iff-interface-index>
        <l2iff-interface-generation>211</l2iff-interface-generation>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-ifd-index>707</l2iff-interface-ifd-index>
        <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
        <l2iff-interface-ifl-index>604</l2iff-interface-ifl-index>
        <l2iff-interface-af-value>50</l2iff-interface-af-value>
        <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
        <l2iff-interface-name>ge-0/0/9.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x1db2c00</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>222</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>2</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>62</l2iff-interface-vstp-index>
        <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
        <l2iff-interface-name>ge-0/0/10.0</l2iff-interface-name>
        <l2iff-interface-handle>0x1dc8900</l2iff-interface-handle>
        <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
        <l2iff-interface-index>605</l2iff-interface-index>
        <l2iff-interface-generation>212</l2iff-interface-generation>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-ifd-index>708</l2iff-interface-ifd-index>
        <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
        <l2iff-interface-ifl-index>605</l2iff-interface-ifl-index>
        <l2iff-interface-af-value>50</l2iff-interface-af-value>
        <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>2</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
        <l2iff-interface-name>ge-0/0/10.0</l2iff-interface-name>
        <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
        <l2iff-interface-handle>0x1db2e00</l2iff-interface-handle>
        <l2iff-interface-index/>
        <l2iff-interface-generation>223</l2iff-interface-generation>
        <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
        <l2iff-interface-ifd-index/>
        <l2iff-interface-ifl-index/>
        <l2iff-interface-af-value/>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
        <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>2</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
        <l2iff-interface-vstp-index>63</l2iff-interface-vstp-index>
        <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
        <l2iff-interface-name>ge-0/0/11.0</l2iff-interface-name>
        <l2iff-interface-handle>0x1dc8a80</l2iff-interface-handle>
        <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
        <l2iff-interface-index>606</l2iff-interface-index>
        <l2iff-interface-generation>213</l2iff-interface-generation>
        <l2iff-interface-flags>UP,</l2iff-interface-flags>
        <l2iff-interface-ifd-index>709</l2iff-interface-ifd-index>
        <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
        <l2iff-interface-ifl-index>606</l2iff-interface-ifl-index>
        <l2iff-interface-af-value>50</l2iff-interface-af-value>
        <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
        <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
        <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
        <l2iff-interface-macs-learned>4</l2iff-interface-macs-learned>
        <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
        <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/11.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1db2f00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>224</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>4</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>64</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/12.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1dc8c00</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>607</l2iff-interface-index>
    <l2iff-interface-generation>214</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>710</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>607</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/12.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1dcb000</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>225</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>65</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/13.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1dc8d80</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>608</l2iff-interface-index>
    <l2iff-interface-generation>215</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>711</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>608</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/13.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1dcb100</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>226</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>66</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/14.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1dc8f00</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>609</l2iff-interface-index>
    <l2iff-interface-generation>216</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>712</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>609</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/14.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1dcb200</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>227</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>6</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>67</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/15.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1dc8e00</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>610</l2iff-interface-index>
    <l2iff-interface-generation>217</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>713</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>610</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/15.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1dcb300</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>228</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>5</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>68</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/16.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1dcc080</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>611</l2iff-interface-index>
    <l2iff-interface-generation>218</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>714</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>611</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>5</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/16.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1c39c00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>247</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>5</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>69</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/17.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1dc8f80</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>612</l2iff-interface-index>
    <l2iff-interface-generation>219</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>715</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>612</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/17.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1dcb500</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>230</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>70</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/18.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1dcc280</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>613</l2iff-interface-index>
    <l2iff-interface-generation>220</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>716</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>613</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/18.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1dcb600</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>231</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>71</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/19.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1dcc100</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>614</l2iff-interface-index>
    <l2iff-interface-generation>221</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>717</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>614</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>3</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/19.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1dcb700</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>232</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>3</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>72</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/20.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1dcc400</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>615</l2iff-interface-index>
    <l2iff-interface-generation>222</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>718</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>615</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>4</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/20.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1dcb800</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>233</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>73</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/20.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1dcb900</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>234</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>3</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>73</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/20.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1dcba00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>235</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>8</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>73</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/20.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1dcbb00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>236</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>10</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>73</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/20.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1dcbc00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>237</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>9</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>73</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/20.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1dcbd00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>238</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>73</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/20.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1dcbe00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>239</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>7</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>73</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/20.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1dcbf00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>240</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>6</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>73</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/20.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1dce000</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>241</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>5</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>73</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/20.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1dce100</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>242</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>2</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>73</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/21.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1dcc680</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>616</l2iff-interface-index>
    <l2iff-interface-generation>223</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>719</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>616</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>2</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/21.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1dce200</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>243</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>7</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>74</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/21.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1dce300</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>244</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>9</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>0</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>74</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/21.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1dce400</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>245</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>11</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>74</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/23.0</l2iff-interface-name>
    <l2iff-interface-handle>0x1dcc500</l2iff-interface-handle>
    <l2iff-interface-interface-type>IFF</l2iff-interface-interface-type>
    <l2iff-interface-index>618</l2iff-interface-index>
    <l2iff-interface-generation>225</l2iff-interface-generation>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-ifd-index>721</l2iff-interface-ifd-index>
    <l2iff-interface-rt-index>4</l2iff-interface-rt-index>
    <l2iff-interface-ifl-index>618</l2iff-interface-ifl-index>
    <l2iff-interface-af-value>50</l2iff-interface-af-value>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    </l2ng-l2ald-iff-interface-entry>
    <l2ng-l2ald-iff-interface-entry style="detail">
    <l2iff-interface-name>ge-0/0/23.0</l2iff-interface-name>
    <l2iff-interface-interface-type>IFBD (static)</l2iff-interface-interface-type>
    <l2iff-interface-handle>0x1dcea00</l2iff-interface-handle>
    <l2iff-interface-index/>
    <l2iff-interface-generation>246</l2iff-interface-generation>
    <l2iff-interface-trunk-vlan>0</l2iff-interface-trunk-vlan>
    <l2iff-interface-flags>UP,</l2iff-interface-flags>
    <l2iff-interface-rt-index>5</l2iff-interface-rt-index>
    <l2iff-interface-ifd-index/>
    <l2iff-interface-ifl-index/>
    <l2iff-interface-af-value/>
    <l2iff-interface-sequence-number>0</l2iff-interface-sequence-number>
    <l2iff-interface-mac-sequence-number>0</l2iff-interface-mac-sequence-number>
    <l2iff-interface-mac-limit>65535</l2iff-interface-mac-limit>
    <l2iff-interface-macs-learned>1</l2iff-interface-macs-learned>
    <l2iff-interface-config-smacs-learned>0</l2iff-interface-config-smacs-learned>
    <l2iff-interface-non-config-smacs-learned>0</l2iff-interface-non-config-smacs-learned>
    <l2iff-interface-vstp-index>76</l2iff-interface-vstp-index>
    <l2iff-interface-rewrite-op/>
    </l2ng-l2ald-iff-interface-entry>
</l2ng-l2ald-iff-interface-information>'''

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


def mock_query_basic_info():
    return [
        ('interface list', INTERFACE_MOCK),
        ('hardware', HARDWARE_MOCK),
        ('version', VERSION_MOCK),
        ('vlans', VLAN_MOCK),
    ]
