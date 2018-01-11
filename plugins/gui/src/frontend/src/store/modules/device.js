/* eslint-disable no-undef */
import { REQUEST_API } from '../actions'
import { UPDATE_ADAPTERS, adapterStaticData, adapter } from './adapter'

export const RESTART_DEVICES = 'RESTART_DEVICES'
export const FETCH_DEVICES = 'FETCH_DEVICES'
export const UPDATE_DEVICES = 'UPDATE_DEVICES'
export const FETCH_UNIQUE_FIELDS = 'FETCH_UNIQUE_FIELDS'
export const UPDATE_UNIQUE_FIELDS = 'UPDATE_UNIQUE_FIELDS'
export const FETCH_DEVICE = 'FETCH_DEVICE'
export const UPDATE_DEVICE = 'UPDATE_DEVICE'

export const FETCH_TAGS = 'FETCH_TAGS'
export const UPDATE_TAGS = 'UPDATE_TAGS'
export const CREATE_DEVICE_TAGS = 'CREATE_DEVICE_TAGS'
export const ADD_DEVICE_TAGS = 'ADD_DEVICE_TAGS'
export const DELETE_DEVICE_TAGS = 'DELETE_DEVICE_TAGS'
export const REMOVE_DEVICE_TAGS = 'REMOVE_DEVICE_TAGS'
export const SELECT_FIELDS = 'SELECT_FIELDS'

export const decomposeFieldPath = (data, fieldPath) => {
	/*
		Find ultimate value of data, matching given field path, by recursively drilling into the dictionary,
		until path exhausted or reached undefined.
		Arrays along the way will be traversed so that final value is the list of all found values
	 */
	if (!data) { return '' }
	if (typeof(data) === 'string' || (Array.isArray(data) && (!data.length || typeof(data[0]) === 'string'))) {
		return data
	}
	if (Array.isArray(data)) {
		let aggregatedValues = []
		data.forEach((item) => {
			let foundValue = decomposeFieldPath(item, fieldPath)
			if (!foundValue) { return }
			if (Array.isArray(foundValue)) {
				aggregatedValues = aggregatedValues.concat(foundValue)
			} else {
				aggregatedValues.push(foundValue)
			}
		})
		return aggregatedValues
	}
	if (fieldPath.indexOf('.') === -1) { return decomposeFieldPath(data[fieldPath], '') }
	let firstPointIndex = fieldPath.indexOf('.')
	return decomposeFieldPath(data[fieldPath.substring(0, firstPointIndex)], fieldPath.substring(firstPointIndex + 1))
}

export const findValues = (field, data) => {
	let value = []
	field.path.split(',').forEach((currentPath) => {
		value = value.concat(decomposeFieldPath({ ...data }, currentPath))
	})
	if ((!field.type || field.type.indexOf('list') === -1) && Array.isArray(value)) {
		return (value.length > 0) ? value[0] : ''
	} else if (Array.isArray(value)) {
		return Array.from(new Set(value))
	}
	return value
}

export const processDevice = (device, fields) => {
	if (!device.adapters || !device.adapters.length) { return }
	let processedDevice = { id: device['internal_axon_id']}
	fields.common.forEach((field) => {
		if (!field.selected) { return }
		let value = findValues(field, device)
		if (value) { processedDevice[field.path] = value }
	})
	device.adapters.forEach((adapter) => {
		if (!fields.unique[adapter.plugin_name]) { return }
		fields.unique[adapter.plugin_name].forEach((field) => {
			if (!field.selected) { return }
			let currentValue = adapter
			let keys = field.path.split('.').splice(1)
			let keysIndex = 0
			while (currentValue && keysIndex < keys.length) {
				currentValue = currentValue[keys[keysIndex]]
				keysIndex++
			}
			processedDevice[field.path] = currentValue
		})
	})
	if (device['tags']) {
		processedDevice['tags.tagname'] = device['tags'].filter((tag) => {
			return tag.tagvalue !== undefined && tag.tagvalue !== ''
		}).map((tag) => {
			return tag.tagname
		})
		processedDevice['tags.tagname'] = processedDevice['tags.tagname'].filter((tag, index, self) => {
			return self.indexOf(tag) === index
		})
	}
	return processedDevice
}

export const device = {
	state: {
		/* Devices according to some query performed by user, updating by request */
		deviceList: {fetching: false, data: [], error: ''},

		/* Currently selected devices, without censoring */
		deviceDetails: {fetching: false, data: {}, error: ''},

		/* Configurations specific for devices */
		fields: {
			common: [
				{path: 'internal_axon_id', name: '', hidden: true, selected: true},
				{
					path: 'adapters.plugin_name', name: 'Adapters', selected: true, type: 'image-list', control: 'multiple-select',
					options: []
				},
				{path: 'adapters.data.pretty_id', name: 'Axonius Name', selected: false, control: 'text'},
				{path: 'adapters.data.hostname', name: 'Host Name', selected: true, control: 'text'},
				{path: 'adapters.data.name', name: 'Asset Name', selected: true, control: 'text'},
				{
					path: 'adapters.data.network_interfaces.IP',
					name: 'IPs',
					selected: true,
					type: 'list',
					control: 'text'
				},
				{
					path: 'adapters.data.network_interfaces.MAC',
					name: 'MACs',
					selected: false,
					type: 'list',
					control: 'text'
				},
				{path: 'adapters.data.OS.type', name: 'OS', selected: true, control: 'text'},
				{path: 'adapters.data.OS.distribution', name: 'OS Version', selected: false, control: 'text'},
				{path: 'adapters.data.OS.bitness', name: 'OS Bitness', selected: false, control: 'text'},
				{path: 'tags.tagname', name: 'Tags', selected: true, type: 'tag-list', control: 'multiple-select', options: []},
				{path: 'tags.tagvalue', selected: true, hidden: true}
			],
			unique: {
				'ad_adapter': [
					{path:"adapters.data.raw.AXON_DNS_ADDR",name:"Active Directory.AXON_DNS_ADDR",control:"text"},
					{path:"adapters.data.raw.AXON_DOMAIN_NAME",name:"Active Directory.AXON_DOMAIN_NAME",control:"text"},
					{path:"adapters.data.raw.accountExpires",name:"Active Directory.accountExpires",control:"text"},
					{path:"adapters.data.raw.badPasswordTime",name:"Active Directory.badPasswordTime",control:"text"},
					{path:"adapters.data.raw.badPwdCount",name:"Active Directory.badPwdCount",control:"number"},
					{path:"adapters.data.raw.cn",name:"Active Directory.cn",control:"text"},
					{path:"adapters.data.raw.codePage",name:"Active Directory.codePage",control:"number"},
					{path:"adapters.data.raw.countryCode",name:"Active Directory.countryCode",control:"number"},
					{path:"adapters.data.raw.dNSHostName",name:"Active Directory.dNSHostName",control:"text"},
					{path:"adapters.data.raw.distinguishedName",name:"Active Directory.distinguishedName",control:"text"},
					{path:"adapters.data.raw.instanceType",name:"Active Directory.instanceType",control:"number"},
					{path:"adapters.data.raw.isCriticalSystemObject",name:"Active Directory.isCriticalSystemObject",control:"bool"},
					{path:"adapters.data.raw.lastLogoff",name:"Active Directory.lastLogoff",control:"text"},
					{path:"adapters.data.raw.lastLogon",name:"Active Directory.lastLogon",control:"text"},
					{path:"adapters.data.raw.lastLogonTimestamp",name:"Active Directory.lastLogonTimestamp",control:"text"},
					{path:"adapters.data.raw.localPolicyFlags",name:"Active Directory.localPolicyFlags",control:"number"},
					{path:"adapters.data.raw.logonCount",name:"Active Directory.logonCount",control:"number"},
					{path:"adapters.data.raw.msDS-SupportedEncryptionTypes",name:"Active Directory.msDS-SupportedEncryptionTypes",control:"number"},
					{path:"adapters.data.raw.name",name:"Active Directory.name",control:"text"},
					{path:"adapters.data.raw.objectCategory",name:"Active Directory.objectCategory",control:"text"},
					{path:"adapters.data.raw.objectGUID",name:"Active Directory.objectGUID",control:"text"},
					{path:"adapters.data.raw.objectSid",name:"Active Directory.objectSid",control:"text"},
					{path:"adapters.data.raw.operatingSystem",name:"Active Directory.operatingSystem",control:"text"},
					{path:"adapters.data.raw.operatingSystemVersion",name:"Active Directory.operatingSystemVersion",control:"text"},
					{path:"adapters.data.raw.primaryGroupID",name:"Active Directory.primaryGroupID",control:"number"},
					{path:"adapters.data.raw.pwdLastSet",name:"Active Directory.pwdLastSet",control:"text"},
					{path:"adapters.data.raw.sAMAccountName",name:"Active Directory.sAMAccountName",control:"text"},
					{path:"adapters.data.raw.sAMAccountType",name:"Active Directory.sAMAccountType",control:"number"},
					{path:"adapters.data.raw.uSNChanged",name:"Active Directory.uSNChanged",control:"number"},
					{path:"adapters.data.raw.uSNCreated",name:"Active Directory.uSNCreated",control:"number"},
					{path:"adapters.data.raw.userAccountControl",name:"Active Directory.userAccountControl",control:"number"},
					{path:"adapters.data.raw.whenChanged",name:"Active Directory.whenChanged",control:"text"},
					{path:"adapters.data.raw.whenCreated",name:"Active Directory.whenCreated",conrtol:"text"}
				],
				'aws_adapter': [
					{path:"adapters.data.raw.AmiLaunchIndex",name:"Amazon Elastic.AmiLaunchIndex",control:"number"},
					{path:"adapters.data.raw.Architecture",name:"Amazon Elastic.Architecture",control:"text"},
					{path:"adapters.data.raw.ClientToken",name:"Amazon Elastic.ClientToken",control:"text"},
					{path:"adapters.data.raw.DescribedImage.Architecture",name:"Amazon Elastic.DescribedImage.Architecture",control:"text"},
					{path:"adapters.data.raw.DescribedImage.CreationDate",name:"Amazon Elastic.DescribedImage.CreationDate",control:"text"},
					{path:"adapters.data.raw.DescribedImage.Description",name:"Amazon Elastic.DescribedImage.Description",control:"text"},
					{path:"adapters.data.raw.DescribedImage.Hypervisor",name:"Amazon Elastic.DescribedImage.Hypervisor",control:"text"},
					{path:"adapters.data.raw.DescribedImage.ImageId",name:"Amazon Elastic.DescribedImage.ImageId",control:"text"},
					{path:"adapters.data.raw.DescribedImage.ImageLocation",name:"Amazon Elastic.DescribedImage.ImageLocation",control:"text"},
					{path:"adapters.data.raw.DescribedImage.ImageType",name:"Amazon Elastic.DescribedImage.ImageType",control:"text"},
					{path:"adapters.data.raw.DescribedImage.Name",name:"Amazon Elastic.DescribedImage.Name",control:"text"},
					{path:"adapters.data.raw.DescribedImage.OwnerId",name:"Amazon Elastic.DescribedImage.OwnerId",control:"text"},
					{path:"adapters.data.raw.DescribedImage.Public",name:"Amazon Elastic.DescribedImage.Public",control:"bool"},
					{path:"adapters.data.raw.DescribedImage.RootDeviceName",name:"Amazon Elastic.DescribedImage.RootDeviceName",control:"text"},
					{path:"adapters.data.raw.DescribedImage.RootDeviceType",name:"Amazon Elastic.DescribedImage.RootDeviceType",control:"text"},
					{path:"adapters.data.raw.DescribedImage.State",name:"Amazon Elastic.DescribedImage.State",control:"text"},
					{path:"adapters.data.raw.DescribedImage.VirtualizationType",name:"Amazon Elastic.DescribedImage.VirtualizationType",control:"text"},
					{path:"adapters.data.raw.EbsOptimized",name:"Amazon Elastic.EbsOptimized",control:"bool"},
					{path:"adapters.data.raw.Hypervisor",name:"Amazon Elastic.Hypervisor",control:"text"},
					{path:"adapters.data.raw.ImageId",name:"Amazon Elastic.ImageId",control:"text"},
					{path:"adapters.data.raw.InstanceId",name:"Amazon Elastic.InstanceId",control:"text"},
					{path:"adapters.data.raw.InstanceType",name:"Amazon Elastic.InstanceType",control:"text"},
					{path:"adapters.data.raw.KeyName",name:"Amazon Elastic.KeyName",control:"text"},
					{path:"adapters.data.raw.LaunchTime",name:"Amazon Elastic.LaunchTime",control:"text"},
					{path:"adapters.data.raw.Monitoring.State",name:"Amazon Elastic.Monitoring.State",control:"text"},
					{path:"adapters.data.raw.Placement.AvailabilityZone",name:"Amazon Elastic.Placement.AvailabilityZone",control:"text"},
					{path:"adapters.data.raw.Placement.GroupName",name:"Amazon Elastic.Placement.GroupName",control:"text"},
					{path:"adapters.data.raw.Placement.Tenancy",name:"Amazon Elastic.Placement.Tenancy",control:"text"},
					{path:"adapters.data.raw.PrivateDnsName",name:"Amazon Elastic.PrivateDnsName",control:"text"},
					{path:"adapters.data.raw.PublicDnsName",name:"Amazon Elastic.PublicDnsName",control:"text"},
					{path:"adapters.data.raw.RootDeviceName",name:"Amazon Elastic.RootDeviceName",control:"text"},
					{path:"adapters.data.raw.RootDeviceType",name:"Amazon Elastic.RootDeviceType",control:"text"},
					{path:"adapters.data.raw.State.Code",name:"Amazon Elastic.State.Code",control:"number"},
					{path:"adapters.data.raw.State.Name",name:"Amazon Elastic.State.Name",control:"text"},
					{path:"adapters.data.raw.StateReason.Code",name:"Amazon Elastic.StateReason.Code",control:"text"},
					{path:"adapters.data.raw.StateReason.Message",name:"Amazon Elastic.StateReason.Message",control:"text"},
					{path:"adapters.data.raw.StateTransitionReason",name:"Amazon Elastic.StateTransitionReason",control:"text"},
					{path:"adapters.data.raw.VirtualizationType",name:"Amazon Elastic.VirtualizationType",control:"text"}
				],
				'esx_adapter': [
					{path:"adapters.data.raw.config.annotation",name:"ESX.config.annotation",control:"text"},
					{path:"adapters.data.raw.config.cpuReservation",name:"ESX.config.cpuReservation",control:"number"},
					{path:"adapters.data.raw.config.guestFullName",name:"ESX.config.guestFullName",control:"text"},
					{path:"adapters.data.raw.config.guestId",name:"ESX.config.guestId",control:"text"},
					{path:"adapters.data.raw.config.installBootRequired",name:"ESX.config.installBootRequired",control:"bool"},
					{path:"adapters.data.raw.config.instanceUuid",name:"ESX.config.instanceUuid",control:"text"},
					{path:"adapters.data.raw.config.memoryReservation",name:"ESX.config.memoryReservation",control:"number"},
					{path:"adapters.data.raw.config.memorySizeMB",name:"ESX.config.memorySizeMB",control:"number"},
					{path:"adapters.data.raw.config.name",name:"ESX.config.name",control:"text"},
					{path:"adapters.data.raw.config.numCpu",name:"ESX.config.numCpu",control:"number"},
					{path:"adapters.data.raw.config.numEthernetCards",name:"ESX.config.numEthernetCards",control:"number"},
					{path:"adapters.data.raw.config.numVirtualDisks",name:"ESX.config.numVirtualDisks",control:"number"},
					{path:"adapters.data.raw.config.template",name:"ESX.config.template",control:"bool"},
					{path:"adapters.data.raw.config.uuid",name:"ESX.config.uuid",control:"text"},
					{path:"adapters.data.raw.config.vmPathName",name:"ESX.config.vmPathName",control:"text"},
					{path:"adapters.data.raw.guest.toolsRunningStatus",name:"ESX.guest.toolsRunningStatus",control:"text"},
					{path:"adapters.data.raw.guest.toolsStatus",name:"ESX.guest.toolsStatus",control:"text"},
					{path:"adapters.data.raw.guest.toolsVersionStatus",name:"ESX.guest.toolsVersionStatus",control:"text"},
					{path:"adapters.data.raw.quickStats.balloonedMemory",name:"ESX.quickStats.balloonedMemory",control:"number"},
					{path:"adapters.data.raw.quickStats.compressedMemory",name:"ESX.quickStats.compressedMemory",control:"number"},
					{path:"adapters.data.raw.quickStats.consumedOverheadMemory",name:"ESX.quickStats.consumedOverheadMemory",control:"number"},
					{path:"adapters.data.raw.quickStats.distributedCpuEntitlement",name:"ESX.quickStats.distributedCpuEntitlement",control:"number"},
					{path:"adapters.data.raw.quickStats.distributedMemoryEntitlement",name:"ESX.quickStats.distributedMemoryEntitlement",control:"number"},
					{path:"adapters.data.raw.quickStats.ftLatencyStatus",name:"ESX.quickStats.ftLatencyStatus",control:"text"},
					{path:"adapters.data.raw.quickStats.ftLogBandwidth",name:"ESX.quickStats.ftLogBandwidth",control:"number"},
					{path:"adapters.data.raw.quickStats.ftSecondaryLatency",name:"ESX.quickStats.ftSecondaryLatency",control:"number"},
					{path:"adapters.data.raw.quickStats.guestHeartbeatStatus",name:"ESX.quickStats.guestHeartbeatStatus",control:"text"},
					{path:"adapters.data.raw.quickStats.guestMemoryUsage",name:"ESX.quickStats.guestMemoryUsage",control:"number"},
					{path:"adapters.data.raw.quickStats.hostMemoryUsage",name:"ESX.quickStats.hostMemoryUsage",control:"number"},
					{path:"adapters.data.raw.quickStats.overallCpuDemand",name:"ESX.quickStats.overallCpuDemand",control:"number"},
					{path:"adapters.data.raw.quickStats.overallCpuUsage",name:"ESX.quickStats.overallCpuUsage",control:"number"},
					{path:"adapters.data.raw.quickStats.privateMemory",name:"ESX.quickStats.privateMemory",control:"number"},
					{path:"adapters.data.raw.quickStats.sharedMemory",name:"ESX.quickStats.sharedMemory",control:"number"},
					{path:"adapters.data.raw.quickStats.staticCpuEntitlement",name:"ESX.quickStats.staticCpuEntitlement",control:"number"},
					{path:"adapters.data.raw.quickStats.staticMemoryEntitlement",name:"ESX.quickStats.staticMemoryEntitlement",control:"number"},
					{path:"adapters.data.raw.quickStats.swappedMemory",name:"ESX.quickStats.swappedMemory",control:"number"},
					{path:"adapters.data.raw.quickStats.uptimeSeconds",name:"ESX.quickStats.uptimeSeconds",control:"number"},
					{path:"adapters.data.raw.runtime.bootTime",name:"ESX.runtime.bootTime",control:"text"},
					{path:"adapters.data.raw.runtime.connectionState",name:"ESX.runtime.connectionState",control:"text"},
					{path:"adapters.data.raw.runtime.consolidationNeeded",name:"ESX.runtime.consolidationNeeded",control:"bool"},
					{path:"adapters.data.raw.runtime.faultToleranceState",name:"ESX.runtime.faultToleranceState",control:"text"},
					{path:"adapters.data.raw.runtime.maxCpuUsage",name:"ESX.runtime.maxCpuUsage",control:"number"},
					{path:"adapters.data.raw.runtime.maxMemoryUsage",name:"ESX.runtime.maxMemoryUsage",control:"number"},
					{path:"adapters.data.raw.runtime.numMksConnections",name:"ESX.runtime.numMksConnections",control:"number"},
					{path:"adapters.data.raw.runtime.onlineStandby",name:"ESX.runtime.onlineStandby",control:"bool"},
					{path:"adapters.data.raw.runtime.powerState",name:"ESX.runtime.powerState",control:"text"},
					{path:"adapters.data.raw.runtime.recordReplayState",name:"ESX.runtime.recordReplayState",control:"text"},
					{path:"adapters.data.raw.runtime.suspendInterval",name:"ESX.runtime.suspendInterval",control:"number"},
					{path:"adapters.data.raw.runtime.toolsInstallerMounted",name:"ESX.runtime.toolsInstallerMounted",control:"bool"},
					{path:"adapters.data.raw.storage.committed",name:"ESX.storage.committed",control:"number"},
					{path:"adapters.data.raw.storage.timestamp",name:"ESX.storage.timestamp",control:"text"},
					{path:"adapters.data.raw.storage.uncommitted",name:"ESX.storage.uncommitted",control:"number"},
					{path:"adapters.data.raw.storage.unshared",name:"ESX.storage.unshared",control:"number"}
				],
				"splunk_symantec_adapter": [
					{conrtol: "text",path: "adapters.data.raw._id",name:"splunk_symantec._id"},
					{conrtol: "text",path: "adapters.data.raw.host.category",name:"splunk_symantec.host.category"},
					{conrtol: "text",path: "adapters.data.raw.host.engine",name:"splunk_symantec.host.engine"},
					{conrtol: "text",path: "adapters.data.raw.host.level",name:"splunk_symantec.host.level"},
					{conrtol: "text",path: "adapters.data.raw.host.name",name:"splunk_symantec.host.name"},
					{conrtol: "text",path: "adapters.data.raw.host.network_raw",name:"splunk_symantec.host.network_raw"},
					{conrtol: "text",path: "adapters.data.raw.host.os",name:"splunk_symantec.host.os"},
					{conrtol: "text",path: "adapters.data.raw.host.raw",name:"splunk_symantec.host.raw"},
					{conrtol: "text",path: "adapters.data.raw.host.timestamp",name:"splunk_symantec.host.timestamp"},
					{conrtol: "text",path: "adapters.data.raw.host.type",name:"splunk_symantec.host.type"},
					{conrtol: "text",path: "adapters.data.raw.host.windows_version_info",name:"splunk_symantec.host.windows_version_info"},
					{conrtol: "text",path: "adapters.data.raw.name",name:"splunk_symantec.name"},
					{conrtol: "text",path: "adapters.data.raw.host.device",name:"splunk_symantec.host.device"},
					{conrtol: "text",path: "adapters.data.raw.host.domain",name:"splunk_symantec.host.domain"},
					{conrtol: "text",path: "adapters.data.raw.host.level",name:"splunk_symantec.host.level"},
					{conrtol: "text",path: "adapters.data.raw.host.local ips",name:"splunk_symantec.host.local ips"},
					{conrtol: "text",path: "adapters.data.raw.host.local mac",name:"splunk_symantec.host.local mac"},
					{conrtol: "text",path: "adapters.data.raw.host.name",name:"splunk_symantec.host.name"},
					{conrtol: "text",path: "adapters.data.raw.host.raw",name:"splunk_symantec.host.raw"},
					{conrtol: "text",path: "adapters.data.raw.host.remote ips",name:"splunk_symantec.host.remote ips"},
					{conrtol: "text",path: "adapters.data.raw.host.remote mac",name:"splunk_symantec.host.remote mac"},
					{conrtol: "text",path: "adapters.data.raw.host.timestamp",name:"splunk_symantec.host.timestamp"},
					{conrtol: "text",path: "adapters.data.raw.host.type",name:"splunk_symantec.host.type"},
					{conrtol: "text",path: "adapters.data.raw.host.user",name:"splunk_symantec.host.user"}
        ],
				"splunk_nexpose_adapter": [
					{conrtol: "text",path: "adapters.data.raw.asset_group_accounts",name:"splunk_nexpose.asset_group_accounts"},
					{conrtol: "text",path: "adapters.data.raw.asset_id",name:"splunk_nexpose.asset_id"},
					{conrtol: "text",path: "adapters.data.raw.critical_vulnerabilities",name:"splunk_nexpose.critical_vulnerabilities"},
					{conrtol: "text",path: "adapters.data.raw.description",name:"splunk_nexpose.description"},
					{conrtol: "text",path: "adapters.data.raw.dest",name:"splunk_nexpose.dest"},
					{conrtol: "text",path: "adapters.data.raw.enabled",name:"splunk_nexpose.enabled"},
					{conrtol: "text",path: "adapters.data.raw.exploits",name:"splunk_nexpose.exploits"},
					{conrtol: "text",path: "adapters.data.raw.family",name:"splunk_nexpose.family"},
					{conrtol: "text",path: "adapters.data.raw.hostname",name:"splunk_nexpose.hostname"},
					{conrtol: "text",path: "adapters.data.raw.installed_software",name:"splunk_nexpose.installed_software"},
					{conrtol: "text",path: "adapters.data.raw.ip",name:"splunk_nexpose.ip"},
					{conrtol: "text",path: "adapters.data.raw.last_discovered",name:"splunk_nexpose.last_discovered"},
					{conrtol: "text",path: "adapters.data.raw.last_scan_finished",name:"splunk_nexpose.last_scan_finished"},
					{conrtol: "text",path: "adapters.data.raw.mac",name:"splunk_nexpose.mac"},
					{conrtol: "text",path: "adapters.data.raw.malware_kits",name:"splunk_nexpose.malware_kits"},
					{conrtol: "text",path: "adapters.data.raw.moderate_vulnerabilities",name:"splunk_nexpose.moderate_vulnerabilities"},
					{conrtol: "text",path: "adapters.data.raw.os",name:"splunk_nexpose.os"},
					{conrtol: "text",path: "adapters.data.raw.pci_status",name:"splunk_nexpose.pci_status"},
					{conrtol: "text",path: "adapters.data.raw.protocols",name:"splunk_nexpose.protocols"},
					{conrtol: "text",path: "adapters.data.raw.riskscore",name:"splunk_nexpose.riskscore"},
					{conrtol: "text",path: "adapters.data.raw.services",name:"splunk_nexpose.services"},
					{conrtol: "text",path: "adapters.data.raw.severe_vulnerabilities",name:"splunk_nexpose.severe_vulnerabilities"},
					{conrtol: "text",path: "adapters.data.raw.site_id",name:"splunk_nexpose.site_id"},
					{conrtol: "text",path: "adapters.data.raw.site_name",name:"splunk_nexpose.site_name"},
					{conrtol: "text",path: "adapters.data.raw.timestamp",name:"splunk_nexpose.timestamp"},
					{conrtol: "text",path: "adapters.data.raw.vendor_product",name:"splunk_nexpose.vendor_product"},
					{conrtol: "text",path: "adapters.data.raw.version",name:"splunk_nexpose.version"},
					{conrtol: "text",path: "adapters.data.raw.vulnerabilities",name:"splunk_nexpose.vulnerabilities"},
					{conrtol: "text",path: "adapters.data.raw.vulnerability_instances",name:"splunk_nexpose.vulnerability_instances"}
        ],
				"sentinelone_adapter": [
					{control: "text",path: "adapters.data.raw.agent_version",name:"SentinelOne.agent_version"},
					{control: "bool",path: "adapters.data.raw.configuration.learning_mode",name:"SentinelOne.configuration.learning_mode"},
					{control: "text",path: "adapters.data.raw.configuration.mitigation_mode",name:"SentinelOne.configuration.mitigation_mode"},
					{control: "text",path: "adapters.data.raw.configuration.mitigation_mode_suspicious",name:"SentinelOne.configuration.mitigation_mode_suspicious"},
					{control: "text",path: "adapters.data.raw.configuration.research_data",name:"SentinelOne.configuration.research_data"},
					{control: "bool",path: "adapters.data.raw.encrypted_applications",name:"SentinelOne.encrypted_applications"},
					{control: "text",path: "adapters.data.raw.external_ip",name:"SentinelOne.external_ip"},
					{control: "text",path: "adapters.data.raw.group_id",name:"SentinelOne.group_id"},
					{control: "text",path: "adapters.data.raw.group_ip",name:"SentinelOne.group_ip"},
					{control: "number",path: "adapters.data.raw.hardware_information.core_count",name:"SentinelOne.hardware_information.core_count"},
					{control: "number",path: "adapters.data.raw.hardware_information.cpu_count",name:"SentinelOne.hardware_information.cpu_count"},
					{control: "text",path: "adapters.data.raw.hardware_information.cpu_id",name:"SentinelOne.hardware_information.cpu_id"},
					{control: "text",path: "adapters.data.raw.hardware_information.machine_type",name:"SentinelOne.hardware_information.machine_type"},
					{control: "text",path: "adapters.data.raw.hardware_information.model_name",name:"SentinelOne.hardware_information.model_name"},
					{control: "number",path: "adapters.data.raw.hardware_information.total_memory",name:"SentinelOne.hardware_information.total_memory"},
					{control: "text",path: "adapters.data.raw.id",name:"SentinelOne.id"},
					{control: "bool",path: "adapters.data.raw.is_active",name:"SentinelOne.is_active"},
					{control: "bool",path: "adapters.data.raw.is_decommissioned",name:"SentinelOne.is_decommissioned"},
					{control: "bool",path: "adapters.data.raw.is_pending_uninstall",name:"SentinelOne.is_pending_uninstall"},
					{control: "bool",path: "adapters.data.raw.is_uninstalled",name:"SentinelOne.is_uninstalled"},
					{control: "bool",path: "adapters.data.raw.is_up_to_date",name:"SentinelOne.is_up_to_date"},
					{control: "text",path: "adapters.data.raw.last_active_date",name:"SentinelOne.last_active_date"},
					{control: "text",path: "adapters.data.raw.last_logged_in_user_name",name:"SentinelOne.last_logged_in_user_name"},
					{control: "text",path: "adapters.data.raw.meta_data.created_at",name:"SentinelOne.meta_data.created_at"},
					{control: "text",path: "adapters.data.raw.meta_data.updated_at",name:"SentinelOne.meta_data.updated_at"},
					{control: "text",path: "adapters.data.raw.network_information.computer_name",name:"SentinelOne.network_information.computer_name"},
					{control: "text",path: "adapters.data.raw.network_information.domain",name:"SentinelOne.network_information.domain"},
					{control: "text",path: "adapters.data.raw.network_status",name:"SentinelOne.network_status"},
					{control: "text",path: "adapters.data.raw.registered_at",name:"SentinelOne.registered_at"},
					{control: "number",path: "adapters.data.raw.scan_status.status",name:"SentinelOne.scan_status.status"},
					{control: "text",path: "adapters.data.raw.software_information.os_arch",name:"SentinelOne.software_information.os_arch"},
					{control: "text",path: "adapters.data.raw.software_information.os_name",name:"SentinelOne.software_information.os_name"},
					{control: "text",path: "adapters.data.raw.software_information.os_revision",name:"SentinelOne.software_information.os_revision"},
					{control: "text",path: "adapters.data.raw.software_information.os_start_time",name:"SentinelOne.software_information.os_start_time"},
					{control: "number",path: "adapters.data.raw.software_information.os_type",name:"SentinelOne.software_information.os_type"},
					{control: "number",path: "adapters.data.raw.threat_count",name:"SentinelOne.threat_count"},
					{control: "text",path: "adapters.data.raw.uuid",name:"SentinelOne.uuid"}
				],
				"symantec_adapter": [
					{control: "text",path: "adapters.data.raw.agentId",name:"Symantec.agentId"},
					{control: "number",path: "adapters.data.raw.agentTimeStamp",name:"Symantec.agentTimeStamp"},
					{control: "text",path: "adapters.data.raw.agentType",name:"Symantec.agentType"},
					{control: "number",path: "adapters.data.raw.agentUsn",name:"Symantec.agentUsn"},
					{control: "text",path: "adapters.data.raw.agentVersion",name:"Symantec.agentVersion"},
					{control: "number",path: "adapters.data.raw.apOnOff",name:"Symantec.apOnOff"},
					{control: "text",path: "adapters.data.raw.attributeExtension",name:"Symantec.attributeExtension"},
					{control: "number",path: "adapters.data.raw.avEngineOnOff",name:"Symantec.avEngineOnOff"},
					{control: "number",path: "adapters.data.raw.bashStatus",name:"Symantec.bashStatus"},
					{control: "text",path: "adapters.data.raw.biosVersion",name:"Symantec.biosVersion"},
					{control: "number",path: "adapters.data.raw.bwf",name:"Symantec.bwf"},
					{control: "number",path: "adapters.data.raw.cidsBrowserFfOnOff",name:"Symantec.cidsBrowserFfOnOff"},
					{control: "number",path: "adapters.data.raw.cidsBrowserIeOnOff",name:"Symantec.cidsBrowserIeOnOff"},
					{control: "number",path: "adapters.data.raw.cidsDrvMulfCode",name:"Symantec.cidsDrvMulfCode"},
					{control: "number",path: "adapters.data.raw.cidsDrvOnOff",name:"Symantec.cidsDrvOnOff"},
					{control: "number",path: "adapters.data.raw.cidsSilentMode",name:"Symantec.cidsSilentMode"},
					{control: "text",path: "adapters.data.raw.computerDescription",name:"Symantec.computerDescription"},
					{control: "text",path: "adapters.data.raw.computerName",name:"Symantec.computerName"},
					{control: "number",path: "adapters.data.raw.computerTimeStamp",name:"Symantec.computerTimeStamp"},
					{control: "number",path: "adapters.data.raw.computerUsn",name:"Symantec.computerUsn"},
					{control: "number",path: "adapters.data.raw.contentUpdate",name:"Symantec.contentUpdate"},
					{control: "number",path: "adapters.data.raw.creationTime",name:"Symantec.creationTime"},
					{control: "text",path: "adapters.data.raw.currentClientId",name:"Symantec.currentClientId"},
					{control: "number",path: "adapters.data.raw.daOnOff",name:"Symantec.daOnOff"},
					{control: "number",path: "adapters.data.raw.deleted",name:"Symantec.deleted"},
					{control: "text",path: "adapters.data.raw.department",name:"Symantec.department"},
					{control: "text",path: "adapters.data.raw.deploymentStatus",name:"Symantec.deploymentStatus"},
					{control: "text",path: "adapters.data.raw.description",name:"Symantec.description"},
					{control: "text",path: "adapters.data.raw.dhcpServer",name:"Symantec.dhcpServer"},
					{control: "text",path: "adapters.data.raw.domainOrWorkgroup",name:"Symantec.domainOrWorkgroup"},
					{control: "number",path: "adapters.data.raw.edrStatus",name:"Symantec.edrStatus"},
					{control: "number",path: "adapters.data.raw.elamOnOff",name:"Symantec.elamOnOff"},
					{control: "text",path: "adapters.data.raw.email",name:"Symantec.email"},
					{control: "text",path: "adapters.data.raw.employeeNumber",name:"Symantec.employeeNumber"},
					{control: "text",path: "adapters.data.raw.employeeStatus",name:"Symantec.employeeStatus"},
					{control: "number",path: "adapters.data.raw.fbwf",name:"Symantec.fbwf"},
					{control: "number",path: "adapters.data.raw.firewallOnOff",name:"Symantec.firewallOnOff"},
					{control: "number",path: "adapters.data.raw.freeDisk",name:"Symantec.freeDisk"},
					{control: "number",path: "adapters.data.raw.freeMem",name:"Symantec.freeMem"},
					{control: "text",path: "adapters.data.raw.fullName",name:"Symantec.fullName"},
					{control: "text",path: "adapters.data.raw.group.domain.id",name:"Symantec.group.domain.id"},
					{control: "text",path: "adapters.data.raw.group.domain.name",name:"Symantec.group.domain.name"},
					{control: "text",path: "adapters.data.raw.group.id",name:"Symantec.group.id"},
					{control: "text",path: "adapters.data.raw.group.name",name:"Symantec.group.name"},
					{control: "bool",path: "adapters.data.raw.groupUpdateProvider",name:"Symantec.groupUpdateProvider"},
					{control: "text",path: "adapters.data.raw.hardwareKey",name:"Symantec.hardwareKey"},
					{control: "text",path: "adapters.data.raw.homePhone",name:"Symantec.homePhone"},
					{control: "text",path: "adapters.data.raw.hypervisorVendorId",name:"Symantec.hypervisorVendorId"},
					{control: "text",path: "adapters.data.raw.idsChecksum",name:"Symantec.idsChecksum"},
					{control: "text",path: "adapters.data.raw.idsSerialNo",name:"Symantec.idsSerialNo"},
					{control: "text",path: "adapters.data.raw.idsVersion",name:"Symantec.idsVersion"},
					{control: "number",path: "adapters.data.raw.infected",name:"Symantec.infected"},
					{control: "text",path: "adapters.data.raw.installType",name:"Symantec.installType"},
					{control: "number",path: "adapters.data.raw.isGrace",name:"Symantec.isGrace"},
					{control: "number",path: "adapters.data.raw.isNpvdiClient",name:"Symantec.isNpvdiClient"},
					{control: "text",path: "adapters.data.raw.jobTitle",name:"Symantec.jobTitle"},
					{control: "text",path: "adapters.data.raw.kernel",name:"Symantec.kernel"},
					{control: "text",path: "adapters.data.raw.lastConnectedIpAddr",name:"Symantec.lastConnectedIpAddr"},
					{control: "number",path: "adapters.data.raw.lastDeploymentTime",name:"Symantec.lastDeploymentTime"},
					{control: "number",path: "adapters.data.raw.lastDownloadTime",name:"Symantec.lastDownloadTime"},
					{control: "number",path: "adapters.data.raw.lastHeuristicThreatTime",name:"Symantec.lastHeuristicThreatTime"},
					{control: "number",path: "adapters.data.raw.lastScanTime",name:"Symantec.lastScanTime"},
					{control: "text",path: "adapters.data.raw.lastServerId",name:"Symantec.lastServerId"},
					{control: "text",path: "adapters.data.raw.lastServerName",name:"Symantec.lastServerName"},
					{control: "text",path: "adapters.data.raw.lastSiteId",name:"Symantec.lastSiteId"},
					{control: "text",path: "adapters.data.raw.lastSiteName",name:"Symantec.lastSiteName"},
					{control: "number",path: "adapters.data.raw.lastUpdateTime",name:"Symantec.lastUpdateTime"},
					{control: "number",path: "adapters.data.raw.lastVirusTime",name:"Symantec.lastVirusTime"},
					{control: "number",path: "adapters.data.raw.licenseExpiry",name:"Symantec.licenseExpiry"},
					{control: "number",path: "adapters.data.raw.licenseStatus",name:"Symantec.licenseStatus"},
					{control: "number",path: "adapters.data.raw.logicalCpus",name:"Symantec.logicalCpus"},
					{control: "text",path: "adapters.data.raw.loginDomain",name:"Symantec.loginDomain"},
					{control: "text",path: "adapters.data.raw.logonUserName",name:"Symantec.logonUserName"},
					{control: "number",path: "adapters.data.raw.majorVersion",name:"Symantec.majorVersion"},
					{control: "number",path: "adapters.data.raw.memory",name:"Symantec.memory"},
					{control: "number",path: "adapters.data.raw.minorVersion",name:"Symantec.minorVersion"},
					{control: "text",path: "adapters.data.raw.mobilePhone",name:"Symantec.mobilePhone"},
					{control: "text",path: "adapters.data.raw.officePhone",name:"Symantec.officePhone"},
					{control: "number",path: "adapters.data.raw.onlineStatus",name:"Symantec.onlineStatus"},
					{control: "text",path: "adapters.data.raw.operatingSystem",name:"Symantec.operatingSystem"},
					{control: "text",path: "adapters.data.raw.osBitness",name:"Symantec.osBitness"},
					{control: "number",path: "adapters.data.raw.osElamStatus",name:"Symantec.osElamStatus"},
					{control: "number",path: "adapters.data.raw.osFlavorNumber",name:"Symantec.osFlavorNumber"},
					{control: "text",path: "adapters.data.raw.osFunction",name:"Symantec.osFunction"},
					{control: "number",path: "adapters.data.raw.osMajor",name:"Symantec.osMajor"},
					{control: "number",path: "adapters.data.raw.osMinor",name:"Symantec.osMinor"},
					{control: "text",path: "adapters.data.raw.osName",name:"Symantec.osName"},
					{control: "text",path: "adapters.data.raw.osServicePack",name:"Symantec.osServicePack"},
					{control: "text",path: "adapters.data.raw.osVersion",name:"Symantec.osVersion"},
					{control: "text",path: "adapters.data.raw.osbitness",name:"Symantec.osbitness"},
					{control: "number",path: "adapters.data.raw.osflavorNumber",name:"Symantec.osflavorNumber"},
					{control: "text",path: "adapters.data.raw.osfunction",name:"Symantec.osfunction"},
					{control: "number",path: "adapters.data.raw.osmajor",name:"Symantec.osmajor"},
					{control: "number",path: "adapters.data.raw.osminor",name:"Symantec.osminor"},
					{control: "text",path: "adapters.data.raw.osname",name:"Symantec.osname"},
					{control: "text",path: "adapters.data.raw.osservicePack",name:"Symantec.osservicePack"},
					{control: "text",path: "adapters.data.raw.osversion",name:"Symantec.osversion"},
					{control: "text",path: "adapters.data.raw.patternIdx",name:"Symantec.patternIdx"},
					{control: "number",path: "adapters.data.raw.pepOnOff",name:"Symantec.pepOnOff"},
					{control: "number",path: "adapters.data.raw.physicalCpus",name:"Symantec.physicalCpus"},
					{control: "number",path: "adapters.data.raw.processorClock",name:"Symantec.processorClock"},
					{control: "text",path: "adapters.data.raw.processorType",name:"Symantec.processorType"},
					{control: "text",path: "adapters.data.raw.profileChecksum",name:"Symantec.profileChecksum"},
					{control: "text",path: "adapters.data.raw.profileSerialNo",name:"Symantec.profileSerialNo"},
					{control: "text",path: "adapters.data.raw.profileVersion",name:"Symantec.profileVersion"},
					{control: "number",path: "adapters.data.raw.ptpOnOff",name:"Symantec.ptpOnOff"},
					{control: "text",path: "adapters.data.raw.publicKey",name:"Symantec.publicKey"},
					{control: "text",path: "adapters.data.raw.quarantineDesc",name:"Symantec.quarantineDesc"},
					{control: "text",path: "adapters.data.raw.rebootReason",name:"Symantec.rebootReason"},
					{control: "number",path: "adapters.data.raw.rebootRequired",name:"Symantec.rebootRequired"},
					{control: "text",path: "adapters.data.raw.serialNumber",name:"Symantec.serialNumber"},
					{control: "number",path: "adapters.data.raw.tamperOnOff",name:"Symantec.tamperOnOff"},
					{control: "number",path: "adapters.data.raw.timeZone",name:"Symantec.timeZone"},
					{control: "number",path: "adapters.data.raw.totalDiskSpace",name:"Symantec.totalDiskSpace"},
					{control: "text",path: "adapters.data.raw.tpmDevice",name:"Symantec.tpmDevice"},
					{control: "text",path: "adapters.data.raw.uniqueId",name:"Symantec.uniqueId"},
					{control: "text",path: "adapters.data.raw.uuid",name:"Symantec.uuid"},
					{control: "number",path: "adapters.data.raw.uwf",name:"Symantec.uwf"},
					{control: "text",path: "adapters.data.raw.virtualizationPlatform",name:"Symantec.virtualizationPlatform"},
					{control: "number",path: "adapters.data.raw.vsicStatus",name:"Symantec.vsicStatus"},
					{control: "text",path: "adapters.data.raw.worstInfectionIdx",name:"Symantec.worstInfectionIdx"}
				],
				"qualys_adapter": [
					{control: "text",path: "adapters.data.raw.address",name:"Qualys.address"},
					{control: "text",path: "adapters.data.raw.agentInfo.activatedModule",name:"Qualys.agentInfo.activatedModule"},
					{control: "text",path: "adapters.data.raw.agentInfo.activationKey.activationId",name:"Qualys.agentInfo.activationKey.activationId"},
					{control: "text",path: "adapters.data.raw.agentInfo.activationKey.title",name:"Qualys.agentInfo.activationKey.title"},
					{control: "number",path: "adapters.data.raw.agentInfo.agentConfiguration.id",name:"Qualys.agentInfo.agentConfiguration.id"},
					{control: "text",path: "adapters.data.raw.agentInfo.agentConfiguration.name",name:"Qualys.agentInfo.agentConfiguration.name"},
					{control: "text",path: "adapters.data.raw.agentInfo.agentId",name:"Qualys.agentInfo.agentId"},
					{control: "text",path: "adapters.data.raw.agentInfo.agentVersion",name:"Qualys.agentInfo.agentVersion"},
					{control: "text",path: "adapters.data.raw.agentInfo.chirpStatus",name:"Qualys.agentInfo.chirpStatus"},
					{control: "text",path: "adapters.data.raw.agentInfo.connectedFrom",name:"Qualys.agentInfo.connectedFrom"},
					{control: "text",path: "adapters.data.raw.agentInfo.lastCheckedIn",name:"Qualys.agentInfo.lastCheckedIn"},
					{control: "text",path: "adapters.data.raw.agentInfo.location",name:"Qualys.agentInfo.location"},
					{control: "text",path: "adapters.data.raw.agentInfo.locationGeoLatitude",name:"Qualys.agentInfo.locationGeoLatitude"},
					{control: "text",path: "adapters.data.raw.agentInfo.locationGeoLongtitude",name:"Qualys.agentInfo.locationGeoLongtitude"},
					{control: "text",path: "adapters.data.raw.agentInfo.platform",name:"Qualys.agentInfo.platform"},
					{control: "text",path: "adapters.data.raw.agentInfo.status",name:"Qualys.agentInfo.status"},
					{control: "text",path: "adapters.data.raw.created",name:"Qualys.created"},
					{control: "number",path: "adapters.data.raw.id",name:"Qualys.id"},
					{control: "text",path: "adapters.data.raw.lastLoggedOnUser",name:"Qualys.lastLoggedOnUser"},
					{control: "text",path: "adapters.data.raw.lastSystemBoot",name:"Qualys.lastSystemBoot"},
					{control: "text",path: "adapters.data.raw.modified",name:"Qualys.modified"},
					{control: "text",path: "adapters.data.raw.name",name:"Qualys.name"},
					{control: "text",path: "adapters.data.raw.os",name:"Qualys.os"},
					{control: "text",path: "adapters.data.raw.timezone",name:"Qualys.timezone"},
					{control: "number",path: "adapters.data.raw.totalMemory",name:"Qualys.totalMemory"},
					{control: "text",path: "adapters.data.raw.trackingMethod",name:"Qualys.trackingMethod"},
					{control: "text",path: "adapters.data.raw.type",name:"Qualys.type"}
        ],
				"jamf_adapter": [
					{control: "text", path: "adapters.data.raw.Activation_Lock_Enabled", name: "Jamf.Activation_Lock_Enabled"},
					{control: "text", path: "adapters.data.raw.AirPlay_Password", name: "Jamf.AirPlay_Password"},
					{control: "text", path: "adapters.data.raw.App_Analytics_Enabled", name: "Jamf.App_Analytics_Enabled"},
					{control: "text", path: "adapters.data.raw.AppleCare_ID", name: "Jamf.AppleCare_ID"},
					{control: "text", path: "adapters.data.raw.Applications", name: "Jamf.Applications"},
					{control: "text", path: "adapters.data.raw.Asset_Tag", name: "Jamf.Asset_Tag"},
					{control: "text", path: "adapters.data.raw.Available_Space_MB", name: "Jamf.Available_Space_MB"},
					{control: "text", path: "adapters.data.raw.Battery_Level", name: "Jamf.Battery_Level"},
					{control: "text", path: "adapters.data.raw.Block_Encryption_Capability", name: "Jamf.Block_Encryption_Capability"},
					{control: "text", path: "adapters.data.raw.Bluetooth_Low_Energy_Capability", name: "Jamf.Bluetooth_Low_Energy_Capability"},
					{control: "text", path: "adapters.data.raw.Bluetooth_MAC_Address", name: "Jamf.Bluetooth_MAC_Address"},
					{control: "text", path: "adapters.data.raw.Building", name: "Jamf.Building"},
					{control: "text", path: "adapters.data.raw.Capacity_MB", name: "Jamf.Capacity_MB"},
					{control: "text", path: "adapters.data.raw.Configuration_Profiles.Configuration_Profile", name: "Jamf.Configuration_Profiles.Configuration_Profile"},
					{control: "text", path: "adapters.data.raw.Data_Protection", name: "Jamf.Data_Protection"},
					{control: "text", path: "adapters.data.raw.Date_Lost_Mode_Enabled", name: "Jamf.Date_Lost_Mode_Enabled"},
					{control: "text", path: "adapters.data.raw.Department", name: "Jamf.Department"},
					{control: "text", path: "adapters.data.raw.Device_ID", name: "Jamf.Device_ID"},
					{control: "text", path: "adapters.data.raw.Device_Locator_Service_Enabled", name: "Jamf.Device_Locator_Service_Enabled"},
					{control: "text", path: "adapters.data.raw.Device_Ownership_Type", name: "Jamf.Device_Ownership_Type"},
					{control: "text", path: "adapters.data.raw.Device_Phone_Number", name: "Jamf.Device_Phone_Number"},
					{control: "text", path: "adapters.data.raw.Diagnostic_and_Usage_Reporting_Enabled", name: "Jamf.Diagnostic_and_Usage_Reporting_Enabled"},
					{control: "text", path: "adapters.data.raw.Display_Name", name: "Jamf.Display_Name"},
					{control: "text", path: "adapters.data.raw.Do_Not_Disturb_Enabled", name: "Jamf.Do_Not_Disturb_Enabled"},
					{control: "text", path: "adapters.data.raw.Email_Address", name: "Jamf.Email_Address"},
					{control: "text", path: "adapters.data.raw.Exchange_Device_ID", name: "Jamf.Exchange_Device_ID"},
					{control: "text", path: "adapters.data.raw.File_Encryption_Capability", name: "Jamf.File_Encryption_Capability"},
					{control: "text", path: "adapters.data.raw.Full_Name", name: "Jamf.Full_Name"},
					{control: "text", path: "adapters.data.raw.Hardware_Encryption", name: "Jamf.Hardware_Encryption"},
					{control: "text", path: "adapters.data.raw.IP_Address", name: "Jamf.IP_Address"},
					{control: "text", path: "adapters.data.raw.JSS_Mobile_Device_ID", name: "Jamf.JSS_Mobile_Device_ID"},
					{control: "text", path: "adapters.data.raw.Jailbreak_Detected", name: "Jamf.Jailbreak_Detected"},
					{control: "text", path: "adapters.data.raw.Languages", name: "Jamf.Languages"},
					{control: "text", path: "adapters.data.raw.Last_Backup", name: "Jamf.Last_Backup"},
					{control: "text", path: "adapters.data.raw.Last_Enrollment", name: "Jamf.Last_Enrollment"},
					{control: "text", path: "adapters.data.raw.Last_Inventory_Update", name: "Jamf.Last_Inventory_Update"},
					{control: "text", path: "adapters.data.raw.Last_iCloud_Backup", name: "Jamf.Last_iCloud_Backup"},
					{control: "text", path: "adapters.data.raw.Lease_Expiration", name: "Jamf.Lease_Expiration"},
					{control: "text", path: "adapters.data.raw.Life_Expectancy", name: "Jamf.Life_Expectancy"},
					{control: "text", path: "adapters.data.raw.Locales", name: "Jamf.Locales"},
					{control: "text", path: "adapters.data.raw.Location_Services_for_Self_Service_Mobile", name: "Jamf.Location_Services_for_Self_Service_Mobile"},
					{control: "text", path: "adapters.data.raw.Lost_Mode_Enabled", name: "Jamf.Lost_Mode_Enabled"},
					{control: "text", path: "adapters.data.raw.Managed", name: "Jamf.Managed"},
					{control: "text", path: "adapters.data.raw.Mobile_Device_Group.Mobile_Device_Group_Membership.Group", name: "Jamf.Mobile_Device_Group.Mobile_Device_Group_Membership.Group"},
					{control: "text", path: "adapters.data.raw.Model", name: "Jamf.Model"},
					{control: "text", path: "adapters.data.raw.Model_Identifier", name: "Jamf.Model_Identifier"},
					{control: "text", path: "adapters.data.raw.Model_Number", name: "Jamf.Model_Number"},
					{control: "text", path: "adapters.data.raw.Modem_Firmware_Version", name: "Jamf.Modem_Firmware_Version"},
					{control: "text", path: "adapters.data.raw.PO_Date", name: "Jamf.PO_Date"},
					{control: "text", path: "adapters.data.raw.PO_Number", name: "Jamf.PO_Number"},
					{control: "text", path: "adapters.data.raw.Passcode_Compliance", name: "Jamf.Passcode_Compliance"},
					{control: "text", path: "adapters.data.raw.Position", name: "Jamf.Position"},
					{control: "text", path: "adapters.data.raw.Provisioning_Profiles", name: "Jamf.Provisioning_Profiles"},
					{control: "text", path: "adapters.data.raw.Purchase_Price", name: "Jamf.Purchase_Price"},
					{control: "text", path: "adapters.data.raw.Purchased_or_Leased", name: "Jamf.Purchased_or_Leased"},
					{control: "text", path: "adapters.data.raw.Purchasing_Account", name: "Jamf.Purchasing_Account"},
					{control: "text", path: "adapters.data.raw.Purchasing_Contact", name: "Jamf.Purchasing_Contact"},
					{control: "text", path: "adapters.data.raw.Roaming", name: "Jamf.Roaming"},
					{control: "text", path: "adapters.data.raw.Room", name: "Jamf.Room"},
					{control: "text", path: "adapters.data.raw.Serial_Number", name: "Jamf.Serial_Number"},
					{control: "text", path: "adapters.data.raw.Shared_iPad", name: "Jamf.Shared_iPad"},
					{control: "text", path: "adapters.data.raw.Supervised", name: "Jamf.Supervised"},
					{control: "text", path: "adapters.data.raw.Synced_to_Computer", name: "Jamf.Synced_to_Computer"},
					{control: "text", path: "adapters.data.raw.Tethered", name: "Jamf.Tethered"},
					{control: "text", path: "adapters.data.raw.UDID", name: "Jamf.UDID"},
					{control: "text", path: "adapters.data.raw.Used_Space_Percentage", name: "Jamf.Used_Space_Percentage"},
					{control: "text", path: "adapters.data.raw.User_Phone_Number", name: "Jamf.User_Phone_Number"},
					{control: "text", path: "adapters.data.raw.Username", name: "Jamf.Username"},
					{control: "text", path: "adapters.data.raw.Vendor", name: "Jamf.Vendor"},
					{control: "text", path: "adapters.data.raw.Voice_Roaming_Enabled", name: "Jamf.Voice_Roaming_Enabled"},
					{control: "text", path: "adapters.data.raw.Warranty_Expiration", name: "Jamf.Warranty_Expiration"},
					{control: "text", path: "adapters.data.raw.Wi_Fi_MAC_Address", name: "Jamf.Wi_Fi_MAC_Address"},
					{control: "text", path: "adapters.data.raw.iCloud_Backup_Enabled", name: "Jamf.iCloud_Backup_Enabled"},
					{control: "text", path: "adapters.data.raw.iOS_Build", name: "Jamf.iOS_Build"},
					{control: "text", path: "adapters.data.raw.iOS_Version", name: "Jamf.iOS_Version"},
					{control: "text", path: "adapters.data.raw.iTunes_Store_Account", name: "Jamf.iTunes_Store_Account"},
					{control: "text", path: "adapters.data.raw.id", name: "Jamf.id"},
					{control: "text", path: "adapters.data.raw.name", name: "Jamf.name"},
					{control: "text", path: "adapters.data.raw.udid", name: "Jamf.udid"}
				]
			}
		},
		tagList: {fetching: false, data: [], error: ''}
	},
	getters: {},
	mutations: {
		[ RESTART_DEVICES ] (state) {
			state.deviceList.data = []
		},
		[ UPDATE_DEVICES ] (state, payload) {
			/* Freshly fetched devices are added to currently stored devices */
			state.deviceList.fetching = payload.fetching
			state.deviceList.error = payload.error
			if (payload.data) {
				let processedData = []
				payload.data.forEach((device) => {
					processedData.push(processDevice(device, state.fields))
				})
				state.deviceList.data = [...state.deviceList.data, ...processedData]
			}
		},
		[ UPDATE_DEVICE ] (state, payload) {
			state.deviceDetails.fetching = payload.fetching
			state.deviceDetails.error = payload.error
			if (payload.data) {
				state.deviceDetails.data = {
					"adapters.plugin_name": payload.data.adapters.map((adapter) => {
						return adapter.plugin_name
					}),
					"tags.tagname": payload.data.tags.filter((tag) => {
						return tag.tagvalue !== undefined && tag.tagvalue !== ''
					}).map((tag) => {
						return tag.tagname
					}),
					"adapters.data.raw": payload.data.adapters.reduce((map, adapter) => {
						map[adapter.plugin_name] = adapter.data.raw
						return map
					}, {})
				}
			}
		},
		[ UPDATE_UNIQUE_FIELDS ] (state, payload) {
			if (payload.data) {
				state.fields.unique = {}
				Object.keys(payload.data).forEach(function (pluginName) {
					state.fields.unique[pluginName] = []
					payload.data[pluginName].forEach((field) => {
						let fieldName = field.path.split('.').splice(3).join('.')
						state.fields.unique[pluginName].push({
							path: field.path,
							name: `${adapterStaticData[pluginName].name}.${fieldName}`,
							control: field.control
						})
					})
				})
			}
		},
		[ UPDATE_TAGS ] (state, payload) {
			state.tagList.fetching = payload.fetching
			state.tagList.error = payload.error
			if (payload.data) {
				state.tagList.data = payload.data.map(function (tag) {
					return {name: tag, path: tag}
				})
				state.fields.common.forEach(function (field) {
					if (field.path === 'tags.tagname') {
						field.options = state.tagList.data
					}
				})
			}
		},
		[ ADD_DEVICE_TAGS ] (state, payload) {
			state.deviceList.data = [ ...state.deviceList.data ]
			state.deviceList.data.forEach(function (device) {
				if (payload.devices.indexOf(device['id']) > -1) {
					if (!device['tags.tagname']) { device['tags.tagname'] = [] }
					payload.tags.forEach((tag) => {
						if (device['tags.tagname'].indexOf(tag) !== -1) { return }
						device['tags.tagname'].push(tag)
					})
				}
			})
			let tags = state.tagList.data.map((tag) => {
				return tag.path
			})
			payload.tags.forEach(function (tag) {
				if (tags.indexOf(tag) === -1) {
					state.tagList.data.push({name: tag, path: tag})
				}
			})
		},
		[ REMOVE_DEVICE_TAGS ] (state, payload) {
			state.deviceList.data = [ ...state.deviceList.data ]
			state.deviceList.data.forEach((device) => {
				if (payload.devices.indexOf(device['id']) > -1) {
					if (!device['tags.tagname']) { return }
					device['tags.tagname'] = device['tags.tagname'].filter((tag) => {
						return payload.tags.indexOf(tag) === -1
					})
				}
			})
		},
		[ SELECT_FIELDS ] (state, payload) {
			state.fields.common.forEach((field) => {
				field.selected = payload.indexOf(field.path) > -1
			})
			Object.values(state.fields.unique).forEach((pluginFields) => {
				pluginFields.forEach((field) => {
					field.selected = payload.indexOf(field.path) > -1
				})
			})
		},
		[ UPDATE_ADAPTERS ] (state, payload) {
			if (!payload.data) { return }
			state.fields.common.forEach((field) => {
				if (field.path !== 'adapters.plugin_name') { return }
				field.options = []
				let used = new Set()
				payload.data.forEach((adapter) => {
					if (used.has(adapter.plugin_name)) { return }
					let name = adapter.plugin_name
					if (adapterStaticData[adapter.plugin_name]) {
						name = adapterStaticData[adapter.plugin_name].name
					}
					field.options.push({name: name, path: adapter.plugin_name})
					used.add(adapter.plugin_name)
				})
			})
		}
	},
	actions: {
		[ FETCH_DEVICES ] ({dispatch, commit}, payload) {
			/* Fetch list of devices for requested page and filtering */
			if (!payload.skip) { payload.skip = 0 }
			/* Getting first page - empty table */
			if (payload.skip === 0) { commit(RESTART_DEVICES) }
			let param = `?limit=${payload.limit}&skip=${payload.skip}`
			if (payload.fields && payload.fields.length) {
				commit(SELECT_FIELDS, payload.fields)
				param += `&fields=${payload.fields}`
			}
			if (payload.filter && Object.keys(payload.filter).length) {
				param += `&filter=${payload.filter}`
			}
			dispatch(REQUEST_API, {
				rule: `/api/devices${param}`,
				type: UPDATE_DEVICES
			})
		},
		[ FETCH_DEVICE ] ({dispatch}, deviceId) {
			if (!deviceId) { return }
			dispatch(REQUEST_API, {
				rule: `/api/devices/${deviceId}`,
				type: UPDATE_DEVICE
			})
		},
		[ FETCH_UNIQUE_FIELDS ] ({dispatch}) {
			dispatch(REQUEST_API, {
				rule: `/api/devices/fields`,
				type: UPDATE_UNIQUE_FIELDS
			})
		},
		[ FETCH_TAGS ] ({dispatch}) {
			dispatch(REQUEST_API, {
				rule: `/api/devices/tags`,
				type: UPDATE_TAGS
			})
		},
		[ CREATE_DEVICE_TAGS ] ({dispatch, commit}, payload) {
			if (!payload || !payload.devices || !payload.devices.length || !payload.tags || !payload.tags.length) {
				return
			}
			commit(ADD_DEVICE_TAGS, payload)
			payload.devices.forEach(function (device) {
				dispatch(REQUEST_API, {
					rule: `/api/devices/${device}`,
					method: 'POST',
					data: {tags: payload.tags}
				})
			})
		},
		[ DELETE_DEVICE_TAGS ] ({dispatch, commit}, payload) {
			if (!payload || !payload.devices || !payload.devices.length || !payload.tags || !payload.tags.length) {
				return
			}
			commit(REMOVE_DEVICE_TAGS, payload)
			payload.devices.forEach(function (device) {
				dispatch(REQUEST_API, {
					rule: `/api/devices/${device}/tags`,
					method: 'DELETE',
					data: {tags: payload.tags}
				})
			})
		}
	}
}