package sql

import (
	"net"
)

type translationTestCase struct {
	// Name of the translation test case
	name string
	// query to execute on the translation
	query string
	// variable to be passed to the translation, should be json type
	variables string
	// expected query to be produced from graphql query
	wantQuery string
	// expected args to be produced from graphql query
	wantParams []interface{}
	// schema path to load
	schema string
}

var translationTestCases = []translationTestCase{
	{
		"simpleTableQuery",
		`query {
				  adapterDevices {
					name
					hostname
					data
					adapterId
					osId
					id
				  }
				}`,
		"",
		"SELECT (sq1.name) AS name, (sq1.hostname) AS hostname, (sq1.data) AS data, (sq1.adapter_id) AS adapter_id, " +
			"(sq1.os_id) AS os_id, (sq1.id) AS id FROM adapter_devices AS sq1 LIMIT 100 OFFSET 0",
		nil,
		"../../../api/generated/augmented_schema.graphql",
	},

	{
		"checkLimitOffset",
		`query {
				  adapterDevices(limit:5, offset: 3) {
					name
					hostname
					data
					adapterId
					osId
					id
				  }
				}`,
		"",
		"SELECT (sq1.name) AS name, (sq1.hostname) AS hostname, (sq1.data) AS data, (sq1.adapter_id) AS adapter_id, " +
			"(sq1.os_id) AS os_id, (sq1.id) AS id FROM adapter_devices AS sq1 LIMIT 5 OFFSET 3",
		nil,
		"../../../api/generated/augmented_schema.graphql",
	},
	{
		"checkOffset",
		`query {
				  adapterDevices(offset: 300) {
					name
					hostname
					data
					adapterId
					osId
					id
				  }
				}`,
		"",
		"SELECT (sq1.name) AS name, (sq1.hostname) AS hostname, (sq1.data) AS data, (sq1.adapter_id) AS adapter_id, " +
			"(sq1.os_id) AS os_id, (sq1.id) AS id FROM adapter_devices AS sq1 LIMIT 100 OFFSET 300",
		nil,
		"../../../api/generated/augmented_schema.graphql",
	},
	{
		"oneToManyJoin",
		`query {
				  adapterDevices {
					name
					interfaces {
						macAddr
					}
				  }
				}`,
		"",
		"SELECT (sq1.name) AS name, (interfaces) AS interfaces FROM adapter_devices AS sq1 " +
			"LEFT JOIN LATERAL ( SELECT (COALESCE(jsonb_agg(jsonb_build_object('mac_addr',sq2.mac_addr)), '[]')) AS interfaces " +
			"FROM network_interfaces AS sq2 WHERE sq1.id = sq2.device_id AND sq1.fetch_cycle = sq2.fetch_cycle LIMIT 100 OFFSET 0 ) " +
			"sq2 ON True LIMIT 100 OFFSET 0",
		nil,
		"../../../api/generated/augmented_schema.graphql",
	},
	{
		"complexQuery",
		`query($where: device_bool_exp!) {
				  devices(
					limit: 10,
					offset: 0
					where: $where,
					orderBy: [adapterCount_DESC]
				  ) {
					adapterCount
					id
					adapterDevices {
					  hostname
					  name
					  interfaces {
						macAddr
						ipAddrs
					  }
					}
					tags {
					  name
					}
				}
			}`,
		`{"where": {
				 "OR": [
				  {"adapterNames": {"contains_regex": "%win%"}},
				  {"adapterDevices": {
					"OR": [
					  { "hostname": {"ilike": "%win%" }},
					  { "name": {"ilike": "%win%" }},
					  { "lastUsedUsers": {"contains_regex": "%win%"}},
					  { "os": {"type": {"ilike": "%win%"}}}
					]
				  }}
				]
			}}`,
		"SELECT (sq1.adapter_count) AS adapter_count, (sq1.id) AS id, (adapter_devices) AS adapter_devices, " +
			"(tags) AS tags FROM devices AS sq1 LEFT JOIN LATERAL ( SELECT " +
			"(COALESCE(jsonb_agg(jsonb_build_object('hostname',sq2.hostname,'name',sq2.name,'interfaces',interfaces)), '[]')) " +
			"AS adapter_devices FROM adapter_devices AS sq2 LEFT JOIN LATERAL ( SELECT " +
			"(COALESCE(jsonb_agg(jsonb_build_object('mac_addr',sq3.mac_addr,'ip_addrs',sq3.ip_addrs)), '[]')) AS interfaces " +
			"FROM network_interfaces AS sq3 WHERE sq2.id = sq3.device_id AND sq2.fetch_cycle = sq3.fetch_cycle LIMIT 100 OFFSET 0 )" +
			" sq3 ON True WHERE sq1.id = sq2.device_id AND sq1.fetch_cycle = sq2.fetch_cycle LIMIT 100 OFFSET 0 ) sq2 ON True " +
			"LEFT JOIN LATERAL ( SELECT (COALESCE(jsonb_agg(jsonb_build_object('name',sq4.name)), '[]')) AS tags " +
			"FROM device_tags(sq1.id,sq1.fetch_cycle) AS sq4 LIMIT 100 OFFSET 0 ) sq4 ON True WHERE (((arrayToText(sq1.adapter_names) LIKE $1) " +
			"OR (EXISTS ( SELECT 1 FROM adapter_devices AS sq5 WHERE sq1.id = sq5.device_id AND sq1.fetch_cycle = sq5.fetch_cycle AND (((sq5.hostname ILIKE $2) " +
			"OR (sq5.name ILIKE $3) OR (arrayToText(sq5.last_used_users) LIKE $4) OR (EXISTS ( SELECT 1 FROM operating_systems AS sq6 WHERE sq5.os_id = sq6.id " +
			"AND (sq6.type ILIKE $5) LIMIT 1 )))) LIMIT 1 )))) ORDER BY adapter_count DESC LIMIT 10 OFFSET 0",
		[]interface{}{"%win%", "%win%", "%win%", "%win%", "%win%"},
		"../../../api/generated/augmented_schema.graphql",
	},
	{
		"inlineFragmentJsonPath",
		`query {
				  adapterDevices(
					where: {
			  			interfaces: {ipAddrs: {ip_family: V4, in_subnet: "10.0.2.0/24"}}
						}) 
					{
					hostname
					adapterId
					interfaces {
					  ipAddrs
					}
					adapterData {
					  ... on ActiveDirectoryData {
						adCn
					  }
					}
				  }
				}`,
		"",
		"SELECT (sq1.hostname) AS hostname, (sq1.adapter_id) AS adapter_id, " +
			"(interfaces) AS interfaces, (sq1.adapter_id) AS adapter_id, (jsonb_build_object('ad_cn', sq1.data->'ad_cn')) AS data " +
			"FROM adapter_devices AS sq1 LEFT JOIN LATERAL ( SELECT (COALESCE(jsonb_agg(jsonb_build_object('ip_addrs',sq2.ip_addrs)), '[]')) AS interfaces " +
			"FROM network_interfaces AS sq2 WHERE sq1.id = sq2.device_id AND sq1.fetch_cycle = sq2.fetch_cycle LIMIT 100 OFFSET 0 ) sq2 ON True " +
			"WHERE (EXISTS ( SELECT 1 FROM network_interfaces AS sq3 WHERE sq1.id = sq3.device_id " +
			"AND sq1.fetch_cycle = sq3.fetch_cycle AND ($1 = any(family(sq3.ip_addrs)) AND $2 >> any(sq3.ip_addrs)) LIMIT 1 )) LIMIT 100 OFFSET 0",
		[]interface{}{"4", &net.IPNet{
			IP:   net.IP{10, 0, 2, 0},
			Mask: net.IPMask{255, 255, 255, 0},
		}},
		"../../../api/generated/augmented_schema.graphql",
	},
	{
		"simpleJsonPathQuery",
		`query {
				  adapterDevices(
					where: {
					  adapterData: { OR: [{ adCn: { like: "lol" } }, { adCn: { eq: "dd" } }] }
					}
				  ) {
					data
				  }
				}`,
		"",
		"SELECT (sq1.data) AS data FROM adapter_devices AS sq1 WHERE (data @? format('$ ? ((@.ad_cn like_regex \"%s\" || @.ad_cn == \"%I\"))',$1::text,$2::text)::jsonpath) LIMIT 100 OFFSET 0",
		[]interface{}{"lol", "dd"},
		"../../../api/generated/augmented_schema.graphql",
	},
}
