/* eslint-disable no-undef */
import { REQUEST_API } from '../actions'
import { UPDATE_ADAPTERS, adapterStaticData } from './adapter'
import merge from 'deepmerge'

export const RESTART_DEVICES = 'RESTART_DEVICES'
export const FETCH_DEVICES = 'FETCH_DEVICES'
export const UPDATE_DEVICES = 'UPDATE_DEVICES'
export const FETCH_DEVICES_COUNT = 'FETCH_DEVICES_COUNT'
export const UPDATE_DEVICES_COUNT = 'UPDATE_DEVICES_COUNT'
export const FETCH_UNIQUE_FIELDS = 'FETCH_UNIQUE_FIELDS'
export const UPDATE_UNIQUE_FIELDS = 'UPDATE_UNIQUE_FIELDS'
export const FETCH_DEVICE = 'FETCH_DEVICE'
export const UPDATE_DEVICE = 'UPDATE_DEVICE'
export const SELECT_DEVICE_PAGE = 'SELECT_DEVICE_PAGE'
export const UPDATE_DEVICE_FILTER = 'UPDATE_DEVICE_FILTER'

export const FETCH_TAGS = 'FETCH_TAGS'
export const UPDATE_TAGS = 'UPDATE_TAGS'
export const CREATE_DEVICE_TAGS = 'CREATE_DEVICE_TAGS'
export const ADD_DEVICE_TAGS = 'ADD_DEVICE_TAGS'
export const DELETE_DEVICE_TAGS = 'DELETE_DEVICE_TAGS'
export const REMOVE_DEVICE_TAGS = 'REMOVE_DEVICE_TAGS'
export const SELECT_FIELDS = 'SELECT_FIELDS'


export const decomposeFieldPath = (data, fieldPath) => {
	/*
		Find ultimate value of controls, matching given field path, by recursively drilling into the dictionary,
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
		value = value.concat(decomposeFieldPath({...data}, currentPath))
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
	let processedDevice = {id: device['internal_axon_id']}
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
		device['tags'].filter((tag) => {
			return tag.tagname.includes('FIELD')
		}).forEach((tag) => {
			processedDevice[tag.tagvalue.fieldname] = tag.tagvalue.fieldvalue
		})
		processedDevice['tags.tagname'] = device['tags'].filter((tag) => {
			return tag.tagtype === 'label' && tag.tagvalue
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
		/* Devices according to current filter performed by user, updating by request */
		deviceList: {fetching: false, data: [], error: ''},

		deviceSelectedPage: 0,

		/* Number of devices according to current filter performed by user */
		deviceCount: {fetching: false, data: 0, error: ''},

		/* Currently selected devices, without censoring */
		deviceDetails: {fetching: false, data: {}, error: ''},

		/* All fields parsed in the system - at least one adapter parses the field */
		deviceFields: {
			fetching: false, data: {
				'name': 'data',
				'items': [
					{
						'title': 'Axonius Name',
						'name': 'pretty_id',
						'type': 'string'
					},
					{
						'title': 'ID',
						'name': 'id',
						'type': 'string'
					},
					{
						'title': 'Asset Name',
						'name': 'name',
						'type': 'string'
					},
					{
						'title': 'Host Name',
						'format': 'hostname',
						'name': 'hostname',
						'type': 'string'
					},
					{
						'name': 'os',
						'items': [
							{
								'title': 'OS Type',
								'enum': [
									'Windows',
									'Linux',
									'OS X',
									'iOS',
									'Android'
								],
								'name': 'type',
								'type': 'string'
							},
							{
								'title': 'OS Distribution',
								'name': 'distribution',
								'type': 'string'
							},
							{
								'title': 'OS Bitness',
								'enum': [
									32,
									64
								],
								'name': 'bitness',
								'type': 'number'
							},
							{
								'title': 'OS Major',
								'name': 'major',
								'type': 'string'
							},
							{
								'title': 'OS Minor',
								'name': 'minor',
								'type': 'string'
							}
						],
						'type': 'array'
					},
					{
						'items': {
							'items': [
								{
									'title': 'MAC',
									'name': 'mac',
									'type': 'string'
								},
								{
									'title': 'IP',
									'items': {
										'type': 'string'
									},
									'name': 'ips',
									'type': 'array'
								}
							],
							'type': 'array'
						},
						'name': 'network_interfaces',
						'title': 'Network Interface',
						'type': 'array'
					},
					{
						'title': 'Last Seen',
						'name': 'last_seen',
						'type': 'string',
						'format': 'date-time'
					},
					{
						'title': 'VM Tools Status',
						'name': 'vm_tools_status',
						'type': 'string'
					},
					{
						'title': 'Resolve Status',
						'name': 'dns_resolve_status',
						'type': 'string'
					},
					{
						'title': 'Power State',
						'name': 'power_state',
						'type': 'string'
					},
					{
						'title': 'Physical Path',
						'name': 'vm_physical_path',
						'type': 'string'
					}
				],
				'type': 'array',
				'required': ['pretty_id', 'name', 'hostname', 'os', 'network_interfaces']
			}, error: ''
		},

		/* Configurations specific for devices */
		fields: {
			common: [
				{path: 'internal_axon_id', name: '', hidden: true, selected: true},
				{
					path: 'adapters.plugin_name',
					name: 'Adapters',
					selected: true,
					type: 'image-list',
					control: 'multiple-select',
					options: []
				},
				{path: 'adapters.data.pretty_id', name: 'Axonius Name', selected: false, control: 'text'},
				{path: 'adapters.data.hostname', name: 'Host Name', selected: true, control: 'text'},
				{path: 'adapters.data.name', name: 'Asset Name', selected: true, control: 'text'},
				{
					path: 'adapters.data.network_interfaces.ips',
					name: 'IPs',
					selected: true,
					type: 'list',
					control: 'text'
				},
				{
					path: 'adapters.data.network_interfaces.mac',
					name: 'MACs',
					selected: false,
					type: 'list',
					control: 'text'
				},
				{path: 'adapters.data.os.type', name: 'OS', selected: true, control: 'text'},
				{path: 'adapters.data.os.distribution', name: 'OS Version', selected: false, control: 'text'},
				{path: 'adapters.data.os.bitness', name: 'OS Bitness', selected: false, control: 'text'},
				{
					path: 'tags.tagname',
					name: 'Tags',
					selected: true,
					type: 'tag-list',
					control: 'multiple-select',
					options: []
				},
				{path: 'tags.tagvalue', selected: true, hidden: true},
				{path: 'last_used_user', selected: false, name: 'Last User Logged'}
			],
			unique: {
				'traiana_lab_machines_adapter': [
					{path: 'adapters.data.raw.owner', name: 'Traiana Lab Machines.owner', control: 'text'},
					{path: 'adapters.data.raw.termination', name: 'Traiana Lab Machines.termination', control: 'text'},
					{path: 'adapters.data.raw.comments', name: 'Traiana Lab Machines.comments', control: 'text'},
					{path: 'adapters.data.raw.os', name: 'Traiana Lab Machines.os', control: 'text'},
					{path: 'adapters.data.raw.ownerFull', name: 'Traiana Lab Machines.ownerFull', control: 'text'},
					{path: 'adapters.data.raw.purpose', name: 'Traiana Lab Machines.purpose', control: 'text'},
					{path: 'adapters.data.raw.usage', name: 'Traiana Lab Machines.usage', control: 'text'},
					{path: 'adapters.data.raw.ip', name: 'Traiana Lab Machines.ip', control: 'text'},
					{path: 'adapters.data.raw.updateUser', name: 'Traiana Lab Machines.updateUser', control: 'text'},
					{path: 'adapters.data.raw.team', name: 'Traiana Lab Machines.team', control: 'text'},
					{path: 'adapters.data.raw.ilo', name: 'Traiana Lab Machines.ilo', control: 'text'},
					{path: 'adapters.data.raw.delete', name: 'Traiana Lab Machines.delete', control: 'text'},
					{path: 'adapters.data.raw.nameLink', name: 'Traiana Lab Machines.nameLink', control: 'text'},
					{path: 'adapters.data.raw.name', name: 'Traiana Lab Machines.name', control: 'text'},
					{path: 'adapters.data.raw.location', name: 'Traiana Lab Machines.location', control: 'text'},
					{path: 'adapters.data.raw.model', name: 'Traiana Lab Machines.model', control: 'text'},
					{path: 'adapters.data.raw.id', name: 'Traiana Lab Machines.id', control: 'text'},
					{path: 'adapters.data.raw.creation', name: 'Traiana Lab Machines.creation', control: 'text'}
				],
				'cisco_adapter': [
					{path: 'adapters.data.raw.ip_address', name: 'Cisco.ip_address', control: 'text'},
					{path: 'adapters.data.raw.mac_address', name: 'Cisco.mac_address', control: 'text'}
				],
				'ad_adapter': [
					{path: 'adapters.data.raw.AXON_DNS_ADDR', name: 'Active Directory.AXON_DNS_ADDR', control: 'text'},
					{
						path: 'adapters.data.raw.AXON_DOMAIN_NAME',
						name: 'Active Directory.AXON_DOMAIN_NAME',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.accountExpires',
						name: 'Active Directory.accountExpires',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.badPasswordTime',
						name: 'Active Directory.badPasswordTime',
						control: 'text'
					},
					{path: 'adapters.data.raw.badPwdCount', name: 'Active Directory.badPwdCount', control: 'number'},
					{path: 'adapters.data.raw.cn', name: 'Active Directory.cn', control: 'text'},
					{path: 'adapters.data.raw.codePage', name: 'Active Directory.codePage', control: 'number'},
					{path: 'adapters.data.raw.countryCode', name: 'Active Directory.countryCode', control: 'number'},
					{path: 'adapters.data.raw.dNSHostName', name: 'Active Directory.dNSHostName', control: 'text'},
					{
						path: 'adapters.data.raw.distinguishedName',
						name: 'Active Directory.distinguishedName',
						control: 'text'
					},
					{path: 'adapters.data.raw.instanceType', name: 'Active Directory.instanceType', control: 'number'},
					{
						path: 'adapters.data.raw.isCriticalSystemObject',
						name: 'Active Directory.isCriticalSystemObject',
						control: 'bool'
					},
					{path: 'adapters.data.raw.lastLogoff', name: 'Active Directory.lastLogoff', control: 'text'},
					{path: 'adapters.data.raw.lastLogon', name: 'Active Directory.lastLogon', control: 'text'},
					{
						path: 'adapters.data.raw.lastLogonTimestamp',
						name: 'Active Directory.lastLogonTimestamp',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.localPolicyFlags',
						name: 'Active Directory.localPolicyFlags',
						control: 'number'
					},
					{path: 'adapters.data.raw.logonCount', name: 'Active Directory.logonCount', control: 'number'},
					{
						path: 'adapters.data.raw.msDS-SupportedEncryptionTypes',
						name: 'Active Directory.msDS-SupportedEncryptionTypes',
						control: 'number'
					},
					{path: 'adapters.data.raw.name', name: 'Active Directory.name', control: 'text'},
					{
						path: 'adapters.data.raw.objectCategory',
						name: 'Active Directory.objectCategory',
						control: 'text'
					},
					{path: 'adapters.data.raw.objectGUID', name: 'Active Directory.objectGUID', control: 'text'},
					{path: 'adapters.data.raw.objectSid', name: 'Active Directory.objectSid', control: 'text'},
					{
						path: 'adapters.data.raw.operatingSystem',
						name: 'Active Directory.operatingSystem',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.operatingSystemVersion',
						name: 'Active Directory.operatingSystemVersion',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.primaryGroupID',
						name: 'Active Directory.primaryGroupID',
						control: 'number'
					},
					{path: 'adapters.data.raw.pwdLastSet', name: 'Active Directory.pwdLastSet', control: 'text'},
					{
						path: 'adapters.data.raw.sAMAccountName',
						name: 'Active Directory.sAMAccountName',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.sAMAccountType',
						name: 'Active Directory.sAMAccountType',
						control: 'number'
					},
					{path: 'adapters.data.raw.uSNChanged', name: 'Active Directory.uSNChanged', control: 'number'},
					{path: 'adapters.data.raw.uSNCreated', name: 'Active Directory.uSNCreated', control: 'number'},
					{
						path: 'adapters.data.raw.userAccountControl',
						name: 'Active Directory.userAccountControl',
						control: 'number'
					},
					{path: 'adapters.data.raw.whenChanged', name: 'Active Directory.whenChanged', control: 'text'},
					{path: 'adapters.data.raw.whenCreated', name: 'Active Directory.whenCreated', conrtol: 'text'}
				],
				'aws_adapter': [
					{
						path: 'adapters.data.raw.AmiLaunchIndex',
						name: 'Amazon Elastic.AmiLaunchIndex',
						control: 'number'
					},
					{path: 'adapters.data.raw.Architecture', name: 'Amazon Elastic.Architecture', control: 'text'},
					{path: 'adapters.data.raw.ClientToken', name: 'Amazon Elastic.ClientToken', control: 'text'},
					{
						path: 'adapters.data.raw.DescribedImage.Architecture',
						name: 'Amazon Elastic.DescribedImage.Architecture',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.DescribedImage.CreationDate',
						name: 'Amazon Elastic.DescribedImage.CreationDate',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.DescribedImage.Description',
						name: 'Amazon Elastic.DescribedImage.Description',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.DescribedImage.Hypervisor',
						name: 'Amazon Elastic.DescribedImage.Hypervisor',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.DescribedImage.ImageId',
						name: 'Amazon Elastic.DescribedImage.ImageId',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.DescribedImage.ImageLocation',
						name: 'Amazon Elastic.DescribedImage.ImageLocation',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.DescribedImage.ImageType',
						name: 'Amazon Elastic.DescribedImage.ImageType',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.DescribedImage.Name',
						name: 'Amazon Elastic.DescribedImage.Name',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.DescribedImage.OwnerId',
						name: 'Amazon Elastic.DescribedImage.OwnerId',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.DescribedImage.Public',
						name: 'Amazon Elastic.DescribedImage.Public',
						control: 'bool'
					},
					{
						path: 'adapters.data.raw.DescribedImage.RootDeviceName',
						name: 'Amazon Elastic.DescribedImage.RootDeviceName',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.DescribedImage.RootDeviceType',
						name: 'Amazon Elastic.DescribedImage.RootDeviceType',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.DescribedImage.State',
						name: 'Amazon Elastic.DescribedImage.State',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.DescribedImage.VirtualizationType',
						name: 'Amazon Elastic.DescribedImage.VirtualizationType',
						control: 'text'
					},
					{path: 'adapters.data.raw.EbsOptimized', name: 'Amazon Elastic.EbsOptimized', control: 'bool'},
					{path: 'adapters.data.raw.Hypervisor', name: 'Amazon Elastic.Hypervisor', control: 'text'},
					{path: 'adapters.data.raw.ImageId', name: 'Amazon Elastic.ImageId', control: 'text'},
					{path: 'adapters.data.raw.InstanceId', name: 'Amazon Elastic.InstanceId', control: 'text'},
					{path: 'adapters.data.raw.InstanceType', name: 'Amazon Elastic.InstanceType', control: 'text'},
					{path: 'adapters.data.raw.KeyName', name: 'Amazon Elastic.KeyName', control: 'text'},
					{path: 'adapters.data.raw.LaunchTime', name: 'Amazon Elastic.LaunchTime', control: 'text'},
					{
						path: 'adapters.data.raw.Monitoring.State',
						name: 'Amazon Elastic.Monitoring.State',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.Placement.AvailabilityZone',
						name: 'Amazon Elastic.Placement.AvailabilityZone',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.Placement.GroupName',
						name: 'Amazon Elastic.Placement.GroupName',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.Placement.Tenancy',
						name: 'Amazon Elastic.Placement.Tenancy',
						control: 'text'
					},
					{path: 'adapters.data.raw.PrivateDnsName', name: 'Amazon Elastic.PrivateDnsName', control: 'text'},
					{path: 'adapters.data.raw.PublicDnsName', name: 'Amazon Elastic.PublicDnsName', control: 'text'},
					{path: 'adapters.data.raw.RootDeviceName', name: 'Amazon Elastic.RootDeviceName', control: 'text'},
					{path: 'adapters.data.raw.RootDeviceType', name: 'Amazon Elastic.RootDeviceType', control: 'text'},
					{path: 'adapters.data.raw.State.Code', name: 'Amazon Elastic.State.Code', control: 'number'},
					{path: 'adapters.data.raw.State.Name', name: 'Amazon Elastic.State.Name', control: 'text'},
					{
						path: 'adapters.data.raw.StateReason.Code',
						name: 'Amazon Elastic.StateReason.Code',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.StateReason.Message',
						name: 'Amazon Elastic.StateReason.Message',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.StateTransitionReason',
						name: 'Amazon Elastic.StateTransitionReason',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.VirtualizationType',
						name: 'Amazon Elastic.VirtualizationType',
						control: 'text'
					}
				],
				'esx_adapter': [
					{path: 'adapters.data.raw.config.annotation', name: 'ESX.config.annotation', control: 'text'},
					{
						path: 'adapters.data.raw.config.cpuReservation',
						name: 'ESX.config.cpuReservation',
						control: 'number'
					},
					{path: 'adapters.data.raw.config.guestFullName', name: 'ESX.config.guestFullName', control: 'text'},
					{path: 'adapters.data.raw.config.guestId', name: 'ESX.config.guestId', control: 'text'},
					{
						path: 'adapters.data.raw.config.installBootRequired',
						name: 'ESX.config.installBootRequired',
						control: 'bool'
					},
					{path: 'adapters.data.raw.config.instanceUuid', name: 'ESX.config.instanceUuid', control: 'text'},
					{
						path: 'adapters.data.raw.config.memoryReservation',
						name: 'ESX.config.memoryReservation',
						control: 'number'
					},
					{path: 'adapters.data.raw.config.memorySizeMB', name: 'ESX.config.memorySizeMB', control: 'number'},
					{path: 'adapters.data.raw.config.name', name: 'ESX.config.name', control: 'text'},
					{path: 'adapters.data.raw.config.numCpu', name: 'ESX.config.numCpu', control: 'number'},
					{
						path: 'adapters.data.raw.config.numEthernetCards',
						name: 'ESX.config.numEthernetCards',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.config.numVirtualDisks',
						name: 'ESX.config.numVirtualDisks',
						control: 'number'
					},
					{path: 'adapters.data.raw.config.template', name: 'ESX.config.template', control: 'bool'},
					{path: 'adapters.data.raw.config.uuid', name: 'ESX.config.uuid', control: 'text'},
					{path: 'adapters.data.raw.config.vmPathName', name: 'ESX.config.vmPathName', control: 'text'},
					{
						path: 'adapters.data.raw.guest.toolsRunningStatus',
						name: 'ESX.guest.toolsRunningStatus',
						control: 'text'
					},
					{path: 'adapters.data.raw.guest.toolsStatus', name: 'ESX.guest.toolsStatus', control: 'text'},
					{
						path: 'adapters.data.raw.guest.toolsVersionStatus',
						name: 'ESX.guest.toolsVersionStatus',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.quickStats.balloonedMemory',
						name: 'ESX.quickStats.balloonedMemory',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.quickStats.compressedMemory',
						name: 'ESX.quickStats.compressedMemory',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.quickStats.consumedOverheadMemory',
						name: 'ESX.quickStats.consumedOverheadMemory',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.quickStats.distributedCpuEntitlement',
						name: 'ESX.quickStats.distributedCpuEntitlement',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.quickStats.distributedMemoryEntitlement',
						name: 'ESX.quickStats.distributedMemoryEntitlement',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.quickStats.ftLatencyStatus',
						name: 'ESX.quickStats.ftLatencyStatus',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.quickStats.ftLogBandwidth',
						name: 'ESX.quickStats.ftLogBandwidth',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.quickStats.ftSecondaryLatency',
						name: 'ESX.quickStats.ftSecondaryLatency',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.quickStats.guestHeartbeatStatus',
						name: 'ESX.quickStats.guestHeartbeatStatus',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.quickStats.guestMemoryUsage',
						name: 'ESX.quickStats.guestMemoryUsage',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.quickStats.hostMemoryUsage',
						name: 'ESX.quickStats.hostMemoryUsage',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.quickStats.overallCpuDemand',
						name: 'ESX.quickStats.overallCpuDemand',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.quickStats.overallCpuUsage',
						name: 'ESX.quickStats.overallCpuUsage',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.quickStats.privateMemory',
						name: 'ESX.quickStats.privateMemory',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.quickStats.sharedMemory',
						name: 'ESX.quickStats.sharedMemory',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.quickStats.staticCpuEntitlement',
						name: 'ESX.quickStats.staticCpuEntitlement',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.quickStats.staticMemoryEntitlement',
						name: 'ESX.quickStats.staticMemoryEntitlement',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.quickStats.swappedMemory',
						name: 'ESX.quickStats.swappedMemory',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.quickStats.uptimeSeconds',
						name: 'ESX.quickStats.uptimeSeconds',
						control: 'number'
					},
					{path: 'adapters.data.raw.runtime.bootTime', name: 'ESX.runtime.bootTime', control: 'text'},
					{
						path: 'adapters.data.raw.runtime.connectionState',
						name: 'ESX.runtime.connectionState',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.runtime.consolidationNeeded',
						name: 'ESX.runtime.consolidationNeeded',
						control: 'bool'
					},
					{
						path: 'adapters.data.raw.runtime.faultToleranceState',
						name: 'ESX.runtime.faultToleranceState',
						control: 'text'
					},
					{path: 'adapters.data.raw.runtime.maxCpuUsage', name: 'ESX.runtime.maxCpuUsage', control: 'number'},
					{
						path: 'adapters.data.raw.runtime.maxMemoryUsage',
						name: 'ESX.runtime.maxMemoryUsage',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.runtime.numMksConnections',
						name: 'ESX.runtime.numMksConnections',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.runtime.onlineStandby',
						name: 'ESX.runtime.onlineStandby',
						control: 'bool'
					},
					{path: 'adapters.data.raw.runtime.powerState', name: 'ESX.runtime.powerState', control: 'text'},
					{
						path: 'adapters.data.raw.runtime.recordReplayState',
						name: 'ESX.runtime.recordReplayState',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.runtime.suspendInterval',
						name: 'ESX.runtime.suspendInterval',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.runtime.toolsInstallerMounted',
						name: 'ESX.runtime.toolsInstallerMounted',
						control: 'bool'
					},
					{path: 'adapters.data.raw.storage.committed', name: 'ESX.storage.committed', control: 'number'},
					{path: 'adapters.data.raw.storage.timestamp', name: 'ESX.storage.timestamp', control: 'text'},
					{path: 'adapters.data.raw.storage.uncommitted', name: 'ESX.storage.uncommitted', control: 'number'},
					{path: 'adapters.data.raw.storage.unshared', name: 'ESX.storage.unshared', control: 'number'}
				],
				'jamf_adapter': [
					{path: 'adapters.data.raw.id', name: 'Jamf.id', control: 'text'},
					{path: 'adapters.data.raw.name', name: 'Jamf.name', control: 'text'},
					{path: 'adapters.data.raw.mac_address', name: 'Jamf.mac_address', control: 'text'},
					{path: 'adapters.data.raw.alt_mac_address', name: 'Jamf.alt_mac_address', control: 'text'},
					{path: 'adapters.data.raw.ip_address', name: 'Jamf.ip_address', control: 'text'},
					{path: 'adapters.data.raw.last_reported_ip', name: 'Jamf.last_reported_ip', control: 'text'},
					{path: 'adapters.data.raw.serial_number', name: 'Jamf.serial_number', control: 'text'},
					{path: 'adapters.data.raw.udid', name: 'Jamf.udid', control: 'text'},
					{path: 'adapters.data.raw.jamf_version', name: 'Jamf.jamf_version', control: 'text'},
					{path: 'adapters.data.raw.platform', name: 'Jamf.platform', control: 'text'},
					{path: 'adapters.data.raw.barcode_1', name: 'Jamf.barcode_1', control: 'text'},
					{path: 'adapters.data.raw.barcode_2', name: 'Jamf.barcode_2', control: 'text'},
					{path: 'adapters.data.raw.asset_tag', name: 'Jamf.asset_tag', control: 'text'},
					{path: 'adapters.data.raw.managed', name: 'Jamf.managed', control: 'text'},
					{path: 'adapters.data.raw.management_username', name: 'Jamf.management_username', control: 'text'},
					{path: 'adapters.data.raw.mdm_capable', name: 'Jamf.mdm_capable', control: 'text'},
					{path: 'adapters.data.raw.mdm_capable_user', name: 'Jamf.mdm_capable_user', control: 'text'},
					{path: 'adapters.data.raw.report_date', name: 'Jamf.report_date', control: 'text'},
					{path: 'adapters.data.raw.report_date_epoch', name: 'Jamf.report_date_epoch', control: 'text'},
					{path: 'adapters.data.raw.report_date_utc', name: 'Jamf.report_date_utc', control: 'text'},
					{path: 'adapters.data.raw.last_contact_time', name: 'Jamf.last_contact_time', control: 'text'},
					{
						path: 'adapters.data.raw.last_contact_time_epoch',
						name: 'Jamf.last_contact_time_epoch',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.last_contact_time_utc',
						name: 'Jamf.last_contact_time_utc',
						control: 'text'
					},
					{path: 'adapters.data.raw.initial_entry_date', name: 'Jamf.initial_entry_date', control: 'text'},
					{
						path: 'adapters.data.raw.initial_entry_date_epoch',
						name: 'Jamf.initial_entry_date_epoch',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.initial_entry_date_utc',
						name: 'Jamf.initial_entry_date_utc',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.last_cloud_backup_date_epoch',
						name: 'Jamf.last_cloud_backup_date_epoch',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.last_cloud_backup_date_utc',
						name: 'Jamf.last_cloud_backup_date_utc',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.last_enrolled_date_epoch',
						name: 'Jamf.last_enrolled_date_epoch',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.last_enrolled_date_utc',
						name: 'Jamf.last_enrolled_date_utc',
						control: 'text'
					},
					{path: 'adapters.data.raw.distribution_point', name: 'Jamf.distribution_point', control: 'text'},
					{path: 'adapters.data.raw.sus', name: 'Jamf.sus', control: 'text'},
					{path: 'adapters.data.raw.netboot_server', name: 'Jamf.netboot_server', control: 'text'},
					{
						path: 'adapters.data.raw.itunes_store_account_is_active',
						name: 'Jamf.itunes_store_account_is_active',
						control: 'text'
					}
				],
				'epo_adapter': [
					{
						path: 'adapters.data.raw.EPOBranchNode_DOT__DOT_NodeName',
						name: 'Epo.EPOBranchNode_NodeName',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOBranchNode_DOT__DOT_NodeTextPath',
						name: 'Epo.EPOBranchNode_NodeTextPath',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOBranchNode_DOT__DOT_NodeTextPath2',
						name: 'Epo.EPOBranchNode_NodeTextPath2',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOBranchNode_DOT__DOT_Notes',
						name: 'Epo.EPOBranchNode_Notes',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerLdapProperties_DOT__DOT_LdapOrgUnit',
						name: 'Epo.EPOComputerLdapProperties_LdapOrgUnit',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_CPUSerialNum',
						name: 'Epo.EPOComputerProperties_CPUSerialNum',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_CPUSpeed',
						name: 'Epo.EPOComputerProperties_CPUSpeed',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_CPUType',
						name: 'Epo.EPOComputerProperties_CPUType',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_ComputerName',
						name: 'Epo.EPOComputerProperties_ComputerName',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_DefaultLangID',
						name: 'Epo.EPOComputerProperties_DefaultLangID',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_Description',
						name: 'Epo.EPOComputerProperties_Description',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_DomainName',
						name: 'Epo.EPOComputerProperties_DomainName',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_FreeDiskSpace',
						name: 'Epo.EPOComputerProperties_FreeDiskSpace',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_FreeMemory',
						name: 'Epo.EPOComputerProperties_FreeMemory',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_IPHostName',
						name: 'Epo.EPOComputerProperties_IPHostName',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_IPSubnet',
						name: 'Epo.EPOComputerProperties_IPSubnet',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_IPSubnetMask',
						name: 'Epo.EPOComputerProperties_IPSubnetMask',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_IPV4x',
						name: 'Epo.EPOComputerProperties_IPV4x',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_IPV6',
						name: 'Epo.EPOComputerProperties_IPV6',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_IPXAddress',
						name: 'Epo.EPOComputerProperties_IPXAddress',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_IsPortable',
						name: 'Epo.EPOComputerProperties_IsPortable',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_ManagementType',
						name: 'Epo.EPOComputerProperties_ManagementType',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_NetAddress',
						name: 'Epo.EPOComputerProperties_NetAddress',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_NumOfCPU',
						name: 'Epo.EPOComputerProperties_NumOfCPU',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_OSBitMode',
						name: 'Epo.EPOComputerProperties_OSBitMode',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT__OSBuildNum',
						name: 'Epo.EPOComputerProperties_OSBuildNum',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_OSOEMID',
						name: 'Epo.EPOComputerProperties_OSOEMID',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_OSPlatform',
						name: 'Epo.EPOComputerProperties_OSPlatform',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_OSServicePackVer',
						name: 'Epo.EPOComputerProperties_OSServicePackVer',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_OSType',
						name: 'Epo.EPOComputerProperties_OSType',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_OSVersion',
						name: 'Epo.EPOComputerProperties_OSVersion',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_SubnetAddress',
						name: 'Epo.EPOComputerProperties_SubnetAddress',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_SubnetMask',
						name: 'Epo.EPOComputerProperties_SubnetMask',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_SystemDescription',
						name: 'Epo.EPOComputerProperties_SystemDescription',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_SysvolFreeSpace',
						name: 'Epo.EPOComputerProperties_SysvolFreeSpace',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_SysvolTotalSpace',
						name: 'Epo.EPOComputerProperties_SysvolTotalSpace',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_TimeZone',
						name: 'Epo.EPOComputerProperties_TimeZone',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_TotalDiskSpace',
						name: 'Epo.EPOComputerProperties_TotalDiskSpace',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT__TotalPhysicalMemory',
						name: 'Epo.EPOComputerProperties_TotalPhysicalMemory',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_UserName',
						name: 'Epo.EPOComputerProperties_UserName',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_UserProperty1',
						name: 'Epo.EPOComputerProperties_UserProperty1',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_UserProperty2',
						name: 'Epo.EPOComputerProperties_UserProperty2',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_UserProperty3',
						name: 'Epo.EPOComputerProperties_UserProperty3',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_UserProperty4',
						name: 'Epo.EPOComputerProperties_UserProperty4',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOComputerProperties_DOT__DOT_Vdi',
						name: 'Epo.EPOComputerProperties_Vdi',
						control: 'number'
					},
					{
						path: 'adapters.data.raw.EPOLeafNode_DOT__DOT_AgentGUID',
						name: 'Epo.EPOLeafNode_AgentGUID',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOLeafNode_DOT__DOT_AgentVersion',
						name: 'Epo.EPOLeafNode_AgentVersion',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOLeafNode_DOT__DOT_ExcludedTags',
						name: 'Epo.EPOLeafNode_ExcludedTags',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOLeafNode_DOT__DOT_LastCommSecure',
						name: 'Epo.EPOLeafNode_LastCommSecure',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOLeafNode_DOT__DOT_LastUpdate',
						name: 'Epo.EPOLeafNode_LastUpdate',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOLeafNode_DOT__DOT_ManagedState',
						name: 'Epo.EPOLeafNode_ManagedState',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOLeafNode_DOT__DOT_NodeName',
						name: 'Epo.EPOLeafNode_NodeName',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOLeafNode_DOT__DOT_ResortEnabled',
						name: 'Epo.EPOLeafNode_ResortEnabled',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOLeafNode_DOT__DOT_SequenceErrorCount',
						name: 'Epo.EPOLeafNode_SequenceErrorCount',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOLeafNode_DOT__DOT_SequenceErrorCountLastUpdate',
						name: 'Epo.EPOLeafNode_SequenceErrorCountLastUpdate',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOLeafNode_DOT__DOT_ServerKeyHash',
						name: 'Epo.EPOLeafNode_ServerKeyHash',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOLeafNode_DOT__DOT_Tags',
						name: 'Epo.EPOLeafNode_Tags',
						control: 'text'
					},
					{
						path: 'adapters.data.raw.EPOLeafNode_DOT__DOT_TransferSiteListsID',
						name: 'Epo.EPOLeafNode_TransferSiteListsID',
						control: 'text'
					},
					{path: 'adapters.data.raw.EPOLeafNode_DOT__DOT_os', name: 'Epo.EPOLeafNode_os', control: 'text'},
					{
						path: 'adapters.data.raw.EPOProductPropertyProducts_DOT__DOT_Products',
						name: 'Epo.EPOProductPropertyProducts_Products',
						control: 'text'
					}
				],
				'puppet_adapter': [
					{path: 'adapters.data.raw.hostname', name: 'Epo.hostname', control: 'text'},
					{path: 'adapters.data.raw.operatingsystem', name: 'Epo.operatingsystem', control: 'text'},
					{path: 'adapters.data.raw.architecture', name: 'Epo.architecture', control: 'text'},
					{path: 'adapters.data.raw.kernel', name: 'Epo.kernel', control: 'text'},
					{path: 'adapters.data.raw.certname', name: 'Epo.certname', control: 'text'},
				],
				"qualys_scans_adapter": [
					{control: "text",path: "adapters.data.raw.DNS", name: "QualysScans.DNS"},
					{control: "text",path: "adapters.data.raw.ID", name: "QualysScans.ID"},
					{control: "text",path: "adapters.data.raw.IP", name: "QualysScans.IP"},
					{control: "text",path: "adapters.data.raw.LAST_COMPLIANCE_SCAN_DATETIME", name: "QualysScans.LAST_COMPLIANCE_SCAN_DATETIME"},
					{control: "text",path: "adapters.data.raw.LAST_VM_SCANNED_DATE", name: "QualysScans.LAST_VM_SCANNED_DATE"},
					{control: "text",path: "adapters.data.raw.LAST_VM_SCANNED_DURATION", name: "QualysScans.LAST_VM_SCANNED_DURATION"},
					{control: "text",path: "adapters.data.raw.LAST_VULN_SCAN_DATETIME", name: "QualysScans.LAST_VULN_SCAN_DATETIME"},
					{control: "text",path: "adapters.data.raw.NETBIOS", name: "QualysScans.NETBIOS"},
					{control: "text",path: "adapters.data.raw.OS", name: "QualysScans.OS"},
					{control: "text",path: "adapters.data.raw.TAGS", name: "QualysScans.TAGS"},
					{control: "text",path: "adapters.data.raw.TRACKING_METHOD", name: "QualysScans.TRACKING_METHOD"}
    			]
			}
		},

		tagList: {fetching: false, data: [], error: ''},

		deviceFilter: ''
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
		[ UPDATE_DEVICES_COUNT ] (state, payload) {
			state.deviceCount.fetching = payload.fetching
			state.deviceCount.error = payload.error
			if (payload.data !== undefined) {
				state.deviceCount.data = payload.data
			}
		},
		[ UPDATE_DEVICE ] (state, payload) {
			state.deviceDetails.fetching = payload.fetching
			state.deviceDetails.error = payload.error
			if (payload.data) {
				let adapterDatas = payload.data.adapters.map((adapter) => {
					let requiredData = {}
					state.deviceFields.data.required.forEach((field) => {
						if (adapter.data[field]) {
							requiredData[field] = adapter.data[field]
						}
					})
					return requiredData
				})
				state.deviceDetails.data = {
					...payload.data,
					data: merge.all(adapterDatas),
					tags: payload.data.tags.filter((tag) => {
						return tag.tagtype === 'label' && tag.tagvalue
					}),
					dataTags: payload.data.tags.filter((tag) => {
						return tag.tagtype === 'data' && tag.tagvalue
					})
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
				state.tagList.data = payload.data.map((tag) => {
					return {name: tag, path: tag}
				})
				state.fields.common.forEach((field) => {
					if (field.path === 'tags.tagname') {
						field.options = state.tagList.data
					}
				})
			}
		},
		[ ADD_DEVICE_TAGS ] (state, payload) {
			state.deviceList.data = [...state.deviceList.data]
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
			payload.tags.forEach((tag) => {
				if (tags.indexOf(tag) === -1) {
					state.tagList.data.push({name: tag, path: tag})
				}
			})
			state.fields.common.forEach((field) => {
				if (field.path === 'tags.tagname') {
					field.options = state.tagList.data
				}
			})
			if (state.deviceDetails.data && state.deviceDetails.data.internal_axon_id
				&& payload.devices.includes(state.deviceDetails.data.internal_axon_id)) {
				state.deviceList.data = { ...state.deviceDetails.data,
					tags: Array.from(new Set([ ...state.deviceDetails.data.tags,
						...payload.tags
					]))
				}
			}
		},
		[ REMOVE_DEVICE_TAGS ] (state, payload) {
			state.deviceList.data = [...state.deviceList.data]
			state.deviceList.data.forEach((device) => {
				if (payload.devices.indexOf(device['id']) > -1) {
					if (!device['tags.tagname']) { return }
					device['tags.tagname'] = device['tags.tagname'].filter((tag) => {
						return payload.tags.indexOf(tag) === -1
					})
				}
			})
			state.tagList.data = state.tagList.data.filter((tag) => {
				if (!payload.tags.includes(tag.path)) { return true }
				let exists = false
				state.deviceList.data.forEach((device) => {
					if (!device['tags.tagname']) { return }
					device['tags.tagname'].forEach((deviceTag) => {
						if (deviceTag === tag.path) {
							exists = true
						}
					})
				})
				return exists

			})
			state.fields.common.forEach((field) => {
				if (field.path === 'tags.tagname') {
					field.options = state.tagList.data
				}
			})
			if (state.deviceDetails.data && state.deviceDetails.data.internal_axon_id
				&& payload.devices.includes(state.deviceDetails.data.internal_axon_id)
				&& state.deviceDetails.data.tags) {

				state.deviceDetails.data = { ...state.deviceDetails.data,
					tags: state.deviceDetails.data.tags.filter((tag) => {
						return !payload.tags.includes(tag.tagname)
					})
				}
			}
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
		},
		[ SELECT_DEVICE_PAGE ] (state, pageNumber) {
			state.deviceSelectedPage = pageNumber
		},
		[ UPDATE_DEVICE_FILTER ] (state, newFilter) {
			state.deviceFilter = newFilter
		}
	},
	actions: {
		[ FETCH_DEVICES ] ({dispatch, commit}, payload) {
			/* Fetch list of devices for requested page and filtering */
			if (!payload.skip) { payload.skip = 0 }
			if (!payload.limit) { payload.limit = 0 }
			/* Getting first page - empty table */
			if (payload.skip === 0) { commit(RESTART_DEVICES) }
			let param = `?limit=${payload.limit}&skip=${payload.skip}`
			if (payload.fields && payload.fields.length) {
				commit(SELECT_FIELDS, payload.fields)
				param += `&fields=${payload.fields}`
			}
			if (payload.filter && payload.filter.length) {
				param += `&filter=${payload.filter}`
			}
			dispatch(REQUEST_API, {
				rule: `/api/devices${param}`,
				type: UPDATE_DEVICES
			})
		},
		[ FETCH_DEVICES_COUNT ] ({dispatch}, payload) {
			let param = ''
			if (payload && payload.filter && Object.keys(payload.filter).length) {
				param = `?filter=${payload.filter}`
			}
			dispatch(REQUEST_API, {
				rule: `/api/devices/count${param}`,
				type: UPDATE_DEVICES_COUNT
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
			return dispatch(REQUEST_API, {
				rule: `/api/devices/tags`,
				method: 'POST',
				data: payload
			}).then(() => commit(ADD_DEVICE_TAGS, payload))
		},
		[ DELETE_DEVICE_TAGS ] ({dispatch, commit}, payload) {
			if (!payload || !payload.devices || !payload.devices.length || !payload.tags || !payload.tags.length) {
				return
			}
			return dispatch(REQUEST_API, {
				rule: `/api/devices/tags`,
				method: 'DELETE',
				data: payload
			}).then(() => commit(REMOVE_DEVICE_TAGS, payload))
		}
	}
}