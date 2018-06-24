export const pluginMeta = {
    tenable_security_center_adapter: {
        title: 'Tenable Security Center',
        description: 'SecurityCenter consolidates and evaluates vulnerability data across your organization, prioritizing security risks and providing a clear view of your security posture.'
    },
    active_directory_adapter: {
        title: 'Active Directory',
        description: 'Active Directory (AD) is a directory service for Windows domain networks that authenticates and authorizes all users and computers.'
    },
    gotoassist_adapter: {
        title: 'GoToAssist',
        description: 'GoToAssist is a cloud-based toolset for IT and customer support teams an includes remote support, IT monitoring and service desk management.'
    },
    airwatch_adapter: {
        title: 'VMWare Airwatch',
        description: 'VMWare AirWatch provides of enterprise mobility management (EMM) software and standalone management systems for content, applications, and email.'
    },
    fireeye_hx_adapter: {
        title: 'FireEye Endpoint Security (HX)',
        description: 'FireEye Endpoint Security (HX)  proactively inspects, analyzes, and contains known and unknown threats at any endpoint.'
    },
    aws_adapter: {
        title: 'Amazon Elastic',
        description: 'Amazon Elastic Compute Cloud (EC2) provides scalable computing capacity in the Amazon Web Services (AWS) cloud.'
    },
    jamf_adapter: {
        title: 'Jamf Pro',
        description: 'Jamf Pro is an enterprise mobility management (EMM) tool that provides unified endpoint management for Apple devices.'
    },
    carbonblack_defense_adapter: {
        title: 'Carbon Black Cb Defense',
        description: 'Carbon Black Cb Defense includes next-generation antivirus + EDR in a cloud-delivered platform to stop commodity malware, advanced malware, non-malware attacks, and ransomware.'
    },
    carbonblack_protection_adapter: {
        title: 'Carbon Black Cb Protection',
        description: 'Carbon Black Cb Protection includes application control and critical infrastructure protection for critical systems and fixed-function devices in highly regulated environments.'
    },
    carbonblack_response_adapter: {
        title: 'Carbon Black Cb Response',
        description: 'Carbon Black Cb Response includes scalable, real-time EDR with unfiltered visibility for security operations centers and incident response teams.'
    },
    epo_adapter: {
        title: 'McAfee ePO',
        description: 'McAfee ePolicy Orchestrator (ePO) is a security management platform that provides real-time monitoring of security solutions.'
    },
    kaseya_adapter: {
        title: 'Kaseya VSA',
        description: 'Kaseya VSA is a remote monitoring and management solution for remote control, discovery, patch management, and monitoring.'
    },
    puppet_adapter: {
        title: 'Puppet',
        description: 'Puppet is an open-source software configuration management tool.'
    },
    qualys_adapter: {
        title: 'Qualys Cloud Agent',
        description: 'Qualys Cloud Agents scan assets like dynamic IP client machines, remote/roaming users, static and ephemeral cloud instances, and systems sensitive to external scanning.'
    },
    qualys_scans_adapter: {
        title: 'Qualys Cloud Platform',
        description: 'Qualys Cloud Platform monitors customers\' global security and compliance posture using sensors.'
    },
    nexpose_adapter: {
        title: 'Rapid7 Nexpose',
        description: 'Rapid7 Nexpose is a vulnerability management solution, including discovery, detection, verification, risk classification, impact analysis, reporting and mitigation.'
    },
    sentinelone_adapter: {
        title: 'SentinelOne',
        description: 'SentinelOne is an endpoint protection solution including prevention, detection, and response.'
    },
    splunk_nexpose_adapter: {
        title: 'Splunk <> Rapid7 Nexpose',
        description: 'The Splunk adapter for Rapid7 Nexpose leverages data from Splunk instances that receive alerts from Rapid7 Nexpose.'
    },
    splunk_symantec_adapter: {
        title: 'Splunk <> Symantec Endpoint Protection Manager',
        description: 'The Splunk adapter for Symantec Endpoint Protection Manager leverages data from Splunk instances that receive alerts from Symantec Endpoint Protection Manager.'
    },
    symantec_adapter: {
        title: 'Symantec Endpoint Protection Manager',
        description: 'Symantec Endpoint Protection Manager manages events, policies, and registration for the client computers that connect to customer networks.'
    },
    nessus_adapter: {
        title: 'Tenable Nessus',
        description: 'Tenable Nessus is a vulnerability scanning platform for auditors and security analysts.'
    },
    nessus_csv_adapter: {
        title: 'Tenable Nessus CSV File',
        description: 'Tenable Nessus CSV File '
    },
    esx_adapter: {
        title: 'VMware ESXi',
        description: 'VMware ESXi is an enterprise-class, type-1 hypervisor for deploying and serving virtual computers. '
    },
    cisco_adapter: {
        title: 'Cisco',
        description: 'The Cisco Adapter connects to Cisco switches and routers.'
    },
    eset_adapter: {
        title: 'ESET Endpoint Security',
        description: 'ESET Endpoint Security is an anti-malware suite for Windows with web filter, firewall, and USB drive and botnet protection.'
    },
    traiana_lab_machines_adapter: {
        title: 'Traiana Lab Machines',
        description: 'Traiana Lab Machines is a propriatery adapter for Traiana, which queries for new devices from the lab machines inventory.'
    },
    fortigate_adapter: {
        title: 'Fortinet FortiGate',
        description: 'Fortniet FortiGate Next-Generation firewall provides high performance, multilayered validated security and visibility for end-to-end protection across the entire enterprise network'
    },
    qcore_adapter: {
        title: 'Qcore',
        description: 'Qcore medical pumps adapter (Saphire+ 14.5)'
    },
    sccm_adapter: {
        title: 'Microsoft SCCM',
        description: 'Microsoft System Center Configuration Manager (SCCM) uses on-premises Configuration Manager or Microsoft Exchange to manage PCs, servers, and devices. '
    },
    desktop_central_adapter: {
        title: 'ManageEngine Desktop Central',
        description: 'ManageEngine Desktop Central is a desktop management and mobile device management software for managing desktops in LAN and across WAN and mobile devices from a central location.'
    },
    forcepoint_csv_adapter: {
        title: 'Forcepoint Web Security Endpoint',
        description: 'Forcepoint Web Security Endpoint enables end-users to authenticate and receive policy enforcement via the Forcepoint Web Security Cloud infrastructure.'
    },
    csv_adapter: {
        title: 'CSV Serials',
        description: 'The CSV Serials Adapter is able to import .csv files with inventory information including the serial number of a device and supplemental device data.'
    },
    mobileiron_adapter: {
        title: 'MobileIron EMM',
        description: 'The MobileIron EMM platform enables enterprises to secure and manage modern operating systems in a world of mixed-use mobile devices and desktops.'
    },
    minerva_adapter: {
        title: 'Minerva Labs Endpoint Malware Vaccination',
        description: 'Minerva Labs Endpoint Malware Vaccination simulates infection markers, rather than creating them, to contain outbreaks that bypass AV tools.'
    },
    juniper_adapter: {
        title: 'Juniper Junos Space',
        description: 'Juniper Junos Space Network Management Platform automates management of Juniper’s switching, routing, and security devices.'
    },
	junos_adapter: {
		title: 'Juniper Junos',
		description: 'The Juniper Junos Adapter connects to Juniper switches and routers.'
	},
    bomgar_adapter: {
        title: 'Bomgar Remote Support',
        description: 'Bomgar Remote Support allows support technicians to remotely connect to end-user systems through firewalls from their computer or mobile devices.'
    },
    bigfix_adapter: {
        title: 'IBM Bigfix',
        description: 'IBM BigFix provides remote control, patch management, software distribution, operating system deployment, network access protection and hardware and software inventory functionality.'
    },
    ensilo_adapter: {
        title: 'enSilo Endpoint Protection',
        description: 'enSilo Endpoint Protection automates and orchestrates detection, prevention and response against advanced malware and ransomware.'
    },
    secdo_adapter: {
        title: 'Secdo Endpoint Protection',
        description: 'The SECDO Next Generation IR Platform automates endpoint forensic analysis and cyber investigations for security teams.'
    },
    openstack_adapter: {
        title: 'OpenStack',
        description: 'OpenStack is an open source software solution for creating private and public clouds.'
    },
    infoblox_adapter: {
        title: 'Infoblox DDI',
        description: 'Infoblox DDI consolidates DNS, DHCP, IP address management, and other core network services into a single platform, managed from a common console.'
    },
    chef_adapter: {
        title: 'Chef',
        description: 'Chef provides continuous automation for building, deploying, and managing infrastructure, compliance, and applications in modern, legacy, and hybrid environments.'
    },
    cisco_prime_adapter: {
        title: 'Cisco Prime',
        description: 'Cisco Prime is a network management software suite consisting of different software applications by Cisco Systems.'
    },
    observeit_csv_adapter: {
        title: 'ObserveIT',
        description: 'ObserveIT provides insider threat security solutions, including employee monitoring, user activity monitoring, behavioral analytics, policy enforcement, and digital forensics.'
    },
    blackberry_uem_adapter: {
        title: 'Blackberry UEM',
        description: 'BlackBerry Unified Endpoint Manager (UEM) delivers endpoint management and policy control for devices and apps on-premise or in the cloud.'
    },
    oracle_vm_adapter: {
        title: 'OracleVM',
        descriptions: 'Oracle\'s server virtualization products support x86 and SPARC architectures and a variety of workloads such as Linux, Windows and Oracle Solaris.'
    },
    cisco_meraki_adapter: {
        title: 'Cisco Meraki',
        description: 'Cisco Meraki solutions include wireless, switching, security, EMM, communications, and security cameras, all centrally managed from the web.'
    },
    service_now_adapter: {
        title: 'ServiceNow',
        description: 'ServiceNow provides service management software as a service, including IT services management (ITSM), IT operations management (ITOM) and IT business management (ITBM).'
    },
    general_info: {
        title: 'WMI Info',
        description: ''
    },
    pm_status: {
        title: 'PM Status',
        description: ''
    },
    softlayer_adapter: {
        title: 'IBM Cloud',
        description: 'IBM\'s cloud computing platform combines platform as a service (PaaS) with infrastructure as a service (IaaS) and cloud services.'
    },
    json_file_adapter: {
        title: 'JSON File',
        description: 'The JSON File Adapter processes files containing JSON formatted devices.'
    },
    stresstest_scanner_adapter: {
        title: 'Test adapter for scanners',
        description: 'Stresstest can be configured with any amount of devices and it creates that number of random devices.'
    },
    hyper_v_adapter: {
        title: 'Microsoft HyperV',
        description: 'Microsoft Hyper-V is a native hypervisor; it can create virtual machines on x86-64 systems running Windows.'
    },
    symantec_altiris_adapter: {
        title: 'Symantec Altiris',
        description: 'The Symantec Asset Management Suite enables organizations to take control, uncover savings, and ensure compliance of IT assets, by giving a picture of assets throughout their lifecycle.'
    },
    azure_adapter: {
        title: 'Microsoft Azure',
        description: 'Microsoft Azure is a cloud computing service created by Microsoft for building, testing, deploying, and managing applications and services through a global network of Microsoft-managed data centers.'
    },
    okta_adapter: {
        title: 'Okta',
        description: 'Okta provides cloud software that helps companies manage their employees\' passwords, by providing a “single sign-on” experience.'
    }
}
