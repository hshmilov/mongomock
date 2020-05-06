package domain

import (
	"bandicoot/internal"
	"context"
	uuid "github.com/satori/go.uuid"
	"net"
)

// AdapterDevice is single instance that was detected by an adapter
type AdapterDevice struct {

	// Unique identification of device
	Id uuid.UUID
	// FetchCycle adapter device was fetch from
	FetchCycle int
	// PrettyID
	PrettyId string `db:"pretty_id"`
	// Time this adapter device was fetched from the connection
	FetchTime internal.Epoch `json:"fetch_time"`
	// When was has the adapter last seen this device
	LastSeen internal.Epoch `json:"last_seen"`
	Hostname *string
	// Name of the device
	Name *string
	Type *string

	// Management
	Domain        *string
	PartOfDomain  *bool `json:"part_of_domain"`
	Managed       *bool `json:"managed"`
	LastUsedUsers []string
	// Operating System of device
	OsId uuid.UUID
	Os   OperatingSystem

	// Agent Client version
	AgentVersion *string
	AgentName    *string
	AgentStatus  *string

	// Name of adapter that scanned this device
	AdapterName string `json:"adapter_name"`
	// The adapter id this device was fetched with
	AdapterId string `db:"adapter_id" json:"adapter_id"`
	Adapter   Adapter
	Client    AdapterClient

	// Software installed on device
	InstalledSoftware []InstalledSoftware

	// Tags associated with this device adapter
	Tags []Tag

	// Network interfaces that the device may have
	Interfaces []NetworkInterface `scan:"follow"`
	// Firewall Rules associated with this device
	FirewallRules []FirewallRule `db:"firewall_rules"`

	// Hardware details
	Model        *string `json:"model"`
	Manufacturer *string `json:"manufacturer"`
	Serial       *string `json:"serial"`
	Family       *string `json:"family"`
	BiosVersion  *string `json:"bios_version" db:"bios_version"`
	BiosSerial   *string `json:"bios_serial" db:"bios_serial"`

	// unique data collected by adapter on this device
	Data map[string]interface{}

	// Devices can be correlated together (i.e grouped)
	DeviceId uuid.UUID `json:"device_id"`
}

type FirewallRule struct {
	Name      string `bson:"name" json:"name"`
	Type      string `bson:"type" json:"type"`
	Source    string `bson:"source" json:"source"`
	Target    string `bson:"target" json:"target"`
	Protocol  string `bson:"protocol" json:"protocol"`
	Direction string `bson:"direction" json:"direction"`
	SrcPort   int    `bson:"from_port" json:"src_port"`
	DstPort   int    `bson:"to_port" json:"dst_port"`
}

type NetworkInterface struct {
	DeviceId uuid.UUID
	IpAddrs  []net.IP `pg:",array" json:"ip_addrs"`
	MacAddr  *string
}

type InstalledSoftware struct {
	Name         string
	Version      string
	RawVersion   string
	Architecture string
	Description  string
	Vendor       string
	Publisher    string
	CveCount     int    `bson:"cve_count" json:"cve_count"`
	SwLicense    string `bson:"sw_license" json:"sw_license"`
	Path         string
}

type AdapterDeviceRepo interface {
	InsertAdapterDevice(ctx context.Context, ad AdapterDevice) error
}
