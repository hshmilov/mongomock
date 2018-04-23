export const pluginMeta = {
		active_directory_adapter: {
			title: 'Active Directory',
			description: 'Active Directory (AD) is a directory service for Windows domain networks that ' +
			'authenticate and authorizes all users and computers.'
		},
		gotoassist_adapter: {
			title: 'GoToAssist',
			description: 'GoToAssist is a cloud-based toolset for IT and customer support teams an includes ' +
			'remote support, IT monitoring and service desk management. '
		},
		airwatch_adapter: {
			title: 'VMWare Airwatch',
			description: 'AirWatch provides of enterprise mobility management (EMM) software and standalone ' +
			'management systems for content, applications, and email.'
		},
		aws_adapter: {
			title: 'Amazon Elastic',
			description: 'Amazon Elastic Compute Cloud (Amazon EC2) provides scalable computing capacity in ' +
			'the Amazon Web Services (AWS) cloud.'
		},
		jamf_adapter: {
			title: 'Jamf Pro',
			description: 'Jamf Pro is an enterprise mobility management (EMM) tool that provides unified ' +
			'endpoint management for Apple devices.'
		},
		carbonblack_adapter: {
			title: 'CarbonBlack',
			description: 'The Cb Predictive Security Cloud collects and analyzes endpoint data to make ' +
			'predictions about, and protect against attacks.'
		},
		epo_adapter: {
			title: 'McAfee ePO',
			description: 'McAfee ePolicy Orchestrator (ePO) is a security management platform that provides ' +
			'real-time monitoring of security solutions.'
		},
		puppet_adapter: {
			title: 'Puppet',
			description: 'Puppet is an open-source software configuration management tool.'
		},
		qualys_adapter: {
			title: 'Qualys Cloud Platform',
			description: 'The Qualys Cloud Platform monitors customers\' global security and compliance ' +
			'posture using sensors.'
		},
		qualys_scans_adapter: {
			title: 'Qualys Cloud Platform - Scanner',
			description: 'The Qualys Cloud Platform monitors customers\' global security and compliance ' +
			'posture using sensors.'
		},
		nexpose_adapter: {
			title: 'Rapid7 Nexpose',
			description: 'Rapid7 Nexpose is a vulnerability management solution, including discovery, ' +
			'detection, verification, risk classification, impact analysis, reporting and mitigation.'
		},
		sentinelone_adapter: {
			title: 'SentinelOne',
			description: 'SentinelOne is an endpoint protection software including prevention, ' +
			'detection, and response.'
		},
		splunk_nexpose_adapter: {
			title: 'Splunk <> Rapid7 Nexpose',
			description: 'The Splunk adapter for Rapid7 Nexpose leverages controls from Splunk instances ' +
			'that receive alerts from Rapid7 Nexpose.'
		},
		splunk_symantec_adapter: {
			title: 'Splunk <> Symantec Endpoint Protection Manager',
			description: 'The Splunk adapter for Symantec Endpoint Protection Manager leverages controls ' +
			'from Splunk instances that receive alerts from Symantec Endpoint Protection Manager.'
		},
		symantec_adapter: {
			title: 'Symantec Endpoint Protection Manager',
			description: 'Symantec Endpoint Protection Manager manages events, policies, and registration ' +
			'for the client computers that connect to customer networks.'
		},
		nessus_adapter: {
			title: 'Tenable Nessus',
			description: 'Tenable Nessus is a vulnerability scanning platform for auditors and security analysts.'
		},
		esx_adapter: {
			title: 'VMware ESXi',
			description: 'VMware ESXi is an entreprise-class, type-1 hypervisor for deploying and serving virtual computers. '
		},
		cisco_adapter: {
			title: 'Cisco CSR',
			description: 'Cisco Cloud Services Router (CSR) provides routing, security, and network management with multitenancy.'
		},
		eset_adapter: {
			title: 'ESET Endpoint Security',
			description: 'ESET Endpoint Security is an anti-malware suite for Windows with web filter,' +
			' firewall, and USB drive and botnet protection.'
		},
		traiana_lab_machines_adapter: {
			title: 'Traiana Lab Machines',
			description: 'Traiana Lab Machines is a propriatery adapter for Traiana, which queries for ' +
			'new devices from the lab machines inventory.'
		},
		fortigate_adapter: {
			title: 'Fortinet FortiGate',
			description: 'FortiGate Next-Generation firewall provides high performance, multilayered ' +
			'validated security and visibility for end-to-end protection across the entire enterprise network.'
		},
		qcore_adapter: {
			title: 'Qcore adapter',
			description: 'Qcore medical pumps adapter (Saphire+ 14.5)'
		},
		sccm_adapter: {
			title: 'Microsoft SCCM',
			description: 'Microsoft System Center Configuration Manager (SCCM) uses on-premises ' +
			'Configuration Manager or Microsoft Exchange to manage PCs, servers and devices.'
		},
		desktop_central_adapter: {
			title: 'ManageEngine Desktop Central',
			description: 'Desktop Central is a Desktop Management and Mobile Device Management Software ' +
			'for managing desktops in LAN and across WAN and mobile devices from a central location'
		},
		forcepoint_csv_adapter: {
			title: 'Forcepoint Web Security Endpoint',
			description: 'Forcepoint Web Security Endpoint enables end-users to authenticate and receive ' +
			'policy enforcement via the Forcepoint Web Security Cloud cloud infrastructure.'
		},
		csv_adapter: {
			title: 'CSV Serials',
			description: 'The Serials CSV Adapter is able to import .csv files with inventory information ' +
			'including the serial number of a device and supplemental device data.'
		},
		mobileiron_adapter: {
			title: 'MobileIron EMM',
			description: 'The MobileIron EMM platform enables global enterprises to secure and manage ' +
			'modern operating systems in a world of mixed-use mobile devices and desktops.'
		},
		minerva_adapter: {
			title: 'Minerva Labs Endpoint Malware Vaccination',
			description: 'Minerva Labs Endpoint Malware Vaccination enables incident response teams to ' +
			'immunize endpoints to neutralize attacks. This solution simulates infection markers, ' +
			'rather than creating them, to contain outbreaks that bypass AV tools.'
		},
		juniper_adapter: {
			title: 'Juniper Junos Space',
			description: 'Junos Space Network Management Platform simplifies and automates management of ' +
			'Juniper’s switching, routing, and security devices.'
		},
		bomgar_adapter: {
			title: 'Bomgar Remote Support',
			description: 'Bomgar Remote Support allows support technicians to remotely connect to end-user ' +
			'systems through firewalls from their computer or mobile device.'
		},
		bigfix_adapter: {
			title: 'IBM Bigfix',
			description: 'IBM BigFix provides remote control, patch management, software distribution, ' +
			'operating system deployment, network access protection and hardware and software inventory functionality.'
		},
		ensilo_adapter: {
			title: 'enSilo Endpoint Protection',
			description: 'enSilo comprehensively secures the endpoint pre- and post-infection. ' +
			'enSilo automates and orchestrates detection, prevention and real-time response against ' +
			'advanced malware and ransomware without burdening cybersecurity staff.'
		},
		secdo_adapter: {
			title: 'Secdo Endpoint Protection',
			description: 'The SECDO Next Generation IR platform automates endpoint forensic analysis ' +
			'and cyber investigations for security teams.'
		},
		openstack_adapter: {
			title: 'OpenStack',
			description: 'OpenStack is an open source software for creating private and public clouds.'
		},
		chef_adapter: {
			title: 'Chef',
			description: 'Continuous automation for building, deploying, and managing infrastructure, ' +
			'compliance, and applications in modern, legacy, and hybrid environments.'
		},
	    cisco_prime_adapter: {
		    title: 'Cisco Prime',
            description: 'Cisco network management software suite.'
	    },
	    observeit_csv_adapter: {
		    title: 'ObserveIT',
		    description: 'ObserveIT provides insider threat security solutions, including employee monitoring, ' +
			'user activity monitoring, behavioral analytics, policy enforcement, and digital forensics.'
        },
        service_now_adapter: {
        	title: 'ServiceNow',
			description: 'ServiceNow provides service management software as a service,' +
			' including IT services management (ITSM), IT operations management (ITOM) and IT business management (ITBM).'
		},
		general_info: {
			title: 'General Info',
			description: ''
		},
		json_file_adapter: {
		    title: 'Adapter title',
		    description: 'Adapter description'
        },
}
