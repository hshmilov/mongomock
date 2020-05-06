package mongo

import (
	"bandicoot/internal"
	"bandicoot/pkg/domain"
	"context"
	"crypto/md5"
	"github.com/rs/zerolog/log"
	"github.com/satori/go.uuid"
	"github.com/spf13/cast"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo/options"
	"net"
	"time"
)

const customData = "adapterdata"

// Keys removed from the data because they are redundant or normalized
var keysToRemove = []string{
	// Normalized
	"network_interfaces",
	"os",
	"name",
	"hostname",
	"last_seen",
	"fetch_time",
	"adapter_properties",
	"installed_software",
	"is_managed",
	"firewall_rules",
	"agent_version",
	"pretty_id",
	"domain",
	"is_part_of_domain",
	"bios_version",
	"bios_serial",
	"device_model",
	"device_model_family",
	"device_manufacturer",
	"last_used_users",
	"device_type",

	// Redundant
	"raw",
	"public_ips_raw",
	"agent_version_raw",
	"accurate_for_datetime",
	"first_fetch_time",
}

type aggregatedDevice struct {
	Id             primitive.ObjectID `bson:"_id" json:"_id"`
	InternalAxonId string             `bson:"internal_axon_id" json:"internal_axon_id"`
	Adapters       []adapter
	Tags           []tag `bson:"tags" json:"tags"`
}

type adapter struct {
	Name       string   `bson:"plugin_name" json:"name"`
	Properties []string `bson:"properties" json:"properties"`
	Data       bson.M
}

type tag struct {
	Name               string     `bson:"name" json:"name"`
	Type               string     `bson:"type"  json:"type"`
	AssociatedAdapters [][]string `bson:"associated_adapters" json:"associated_adapters"`
	Data               interface{}
}

type agentVersion struct {
	Name    string `bson:"adapter_name" json:"adapter_name"`
	Status  string `bson:"agent_status" json:"agent_status"`
	Version string `bson:"agent_version" json:"agent_version"`
}

type adapterData struct {
	// Base
	Hostname string
	Name     string             `bson:"name" json:"name"`
	LastSeen primitive.DateTime `bson:"last_seen" json:"last_seen"`
	PrettyId string             `bson:"pretty_id" json:"pretty_id"`

	// Management
	Domain            string
	PartOfDomain      bool                       `bson:"is_part_of_domain" json:"is_part_of_domain"`
	Managed           bool                       `bson:"is_managed" json:"is_managed"`
	InstalledSoftware []domain.InstalledSoftware `bson:"installed_software" json:"installed_software"`
	LastUsedUsers     []string                   `bson:"last_used_users" json:"last_used_users"`
	//LocalAdmins 	  []map[string]interface{} `bson:"local_admins" json:"local_admins"`
	//Users 			  []map[string]interface{} `bson:"device_users" json:"device_users"`

	// Adapter Client details
	FetchTime         primitive.DateTime `bson:"fetch_time" json:"fetch_time"`
	AdapterProperties []string           `bson:"adapter_properties" json:"adapter_properties"`
	AgentVersion      []agentVersion     `bson:"agent_versions" json:"agent_versions"`

	// Network Information
	Interfaces    []networkInterface    `bson:"network_interfaces" json:"network_interfaces"`
	FirewallRules []domain.FirewallRule `bson:"firewall_rules" json:"agent_version"`

	// Device details
	DeviceType   string `bson:"device_type" json:"device_type"`
	Os           domain.OperatingSystem
	Model        string `bson:"device_model" json:"device_model"`
	Manufacturer string `bson:"device_manufacturer" json:"device_manufacturer"`
	Serial       string `bson:"device_serial" json:"device_serial"`
	Family       string `bson:"device_model_family" json:"device_model_family"`
	BiosVersion  string `bson:"bios_version" json:"bios_version"`
	BiosSerial   string `bson:"bios_serial" json:"bios_serial"`

	// Hardware details (Processors, Hard drives, etc')
	//Processors 	      []domain.Processor `bson:"cpus" json:"cpus"`
}

type networkInterface struct {
	Mac string
	Ips []string
}

func (n networkInterface) convert() domain.NetworkInterface {
	var ips []net.IP
	for _, ip := range n.Ips {
		if ip == "" {
			continue
		}
		ips = append(ips, net.ParseIP(ip))
	}
	var mac *string
	if n.Mac != "" {
		mac = &n.Mac
	}
	return domain.NetworkInterface{IpAddrs: ips, MacAddr: mac}
}

func (m *Repo) CountDevices(ctx context.Context) int64 {
	collection := m.client.Database("aggregator").Collection("devices_db")
	count, err := collection.CountDocuments(ctx, bson.D{})
	if err != nil {
		log.Error().Err(err).Msg("Failed to count devices")
		return 0
	}
	return count
}

func (m *Repo) FindDevices(ctx context.Context, skip, limit int64) ([]domain.Device, error) {

	collection := m.client.Database("aggregator").Collection("devices_db")
	cur, err := collection.Find(ctx, bson.D{}, options.Find().SetLimit(limit).SetSkip(skip).SetProjection(bson.D{
		{"_id", 1},
		{"internal_axon_id", 1},
		{"adapters", 1},
		{"tags", 1},
	}))
	if err != nil {
		log.Error().Err(err).Msg("Failed to collect devices")
	}
	defer cur.Close(ctx)
	log.Info().Msg("Started finding correlated")
	var cDevices []domain.Device
	for cur.Next(ctx) {
		// Mongo returns aggregatedDevice this will be parsed into a correlatedDevice
		var aDevice aggregatedDevice
		err := cur.Decode(&aDevice)
		if err != nil {
			log.Printf("Failed to decode device: %s", err)
			continue
		}
		cDeviceId, err := uuid.FromString(aDevice.InternalAxonId)
		if err != nil {
			log.Fatal().Err(err).Msg("Failed to create axon id")
		}
		devices, err := m.parseDevices(cDeviceId, &aDevice)
		if err != nil {
			log.Error().Err(err).Msg("Failed to parse adapter devices")
			continue
		}

		cDevices = append(cDevices, domain.Device{
			Id:              cDeviceId,
			AdapterDevices:  devices,
			AdapterCount:    len(devices),
			CorrelationTime: time.Now().UTC(),
		})
	}
	if err := cur.Err(); err != nil {
		log.Fatal().Err(err).Msg("Cursor error")
	}
	return cDevices, nil
}

// Parse devices from an aggregated device
func (m *Repo) parseDevices(cDeviceId uuid.UUID, aDevice *aggregatedDevice) ([]domain.AdapterDevice, error) {

	tagToDevice := make(map[string][]domain.Tag)
	for _, tag := range aDevice.Tags {
		if tag.Type == customData {
			log.Trace().Str("device", cDeviceId.String()).Msg("Skipping custom data")
			continue
		}
		// Go over associated adapters and add tag for them
		for _, associatedAdapters := range tag.AssociatedAdapters {
			adapterId := cast.ToString(associatedAdapters[1])
			tagToDevice[adapterId] = append(tagToDevice[adapterId], domain.Tag{Name: tag.Name})
		}
	}

	var devices []domain.AdapterDevice
	for _, adapter := range aDevice.Adapters {
		// Remove old adapters
		if old, ok := adapter.Data["_old"]; ok && old.(bool) {
			log.Debug().Str("adapter", adapter.Name).Msg("Removed old adapter")
			continue
		}
		adapterDevice, err := m.parseAdapter(adapter)
		if err != nil {
			log.Err(err).Str("adapter", adapter.Name).Interface("data", adapter.Data).Msg("failed to parse adapter")
			continue
		}
		// Add tags to adapter device if it has any
		if id, ok := adapterDevice.Data["id"]; ok {
			adapterDevice.Tags = append([]domain.Tag(nil), tagToDevice[cast.ToString(id)]...)
		}
		adapterDevice.DeviceId = cDeviceId
		devices = append(devices, adapterDevice)
	}
	return devices, nil
}

// Extract from a single adapter it's device data, it's adapter data and tags associated with it
func (m *Repo) parseAdapter(adapter adapter) (domain.AdapterDevice, error) {
	var ad adapterData
	bsonBytes, _ := bson.Marshal(adapter.Data)
	err := bson.Unmarshal(bsonBytes, &ad)
	if err != nil {
		log.Warn().Err(err).Msg("failed to decode adapter data")
		return domain.AdapterDevice{}, err
	}

	var interfaces []domain.NetworkInterface
	for _, i := range ad.Interfaces {
		interfaces = append(interfaces, i.convert())
	}

	if adapter.Name == "active_directory_adapter" {
		adapter.Data["ad_account_expires"] = 0
	}

	// If adapter data has no os type
	osId := domain.GetOSId(domain.UnknownOs, domain.UnknownArchitecture, "")
	if ad.Os.Type != "" {
		osId = domain.GetOSId(ad.Os.Type, ad.Os.Architecture, ad.Os.Distribution)
	}

	adapterDeviceId := uuid.NewV4()
	if id, ok := adapter.Data["id"]; ok {
		hash := md5.Sum([]byte(cast.ToString(id)))
		adapterDeviceId, err = uuid.FromBytes(hash[:])
		if err != nil {
			log.Error().Err(err).Interface("id", id).Msg("Failed to hash adapter device id")
		}
	}

	var netInterfaces []domain.NetworkInterface
	for _, n := range ad.Interfaces {
		if n.Ips == nil {
			continue
		}
		cnvN := n.convert()
		cnvN.DeviceId = adapterDeviceId
		netInterfaces = append(netInterfaces, cnvN)
	}

	for _, s := range ad.InstalledSoftware {
		if s.Name == "" {
			continue
		}
	}
	// Pop keys that were parsed
	for _, key := range keysToRemove {
		delete(adapter.Data, key)
	}
	var a agentVersion
	if len(ad.AgentVersion) >= 1 {
		a = ad.AgentVersion[0]
	}

	return domain.AdapterDevice{
		Id:                adapterDeviceId,
		PrettyId:          ad.PrettyId,
		FetchTime:         internal.EpochFromTime(ad.FetchTime.Time()),
		LastSeen:          internal.EpochFromTime(ad.LastSeen.Time()),
		Hostname:          &ad.Hostname,
		Name:              &ad.Name,
		Domain:            &ad.Domain,
		PartOfDomain:      &ad.PartOfDomain,
		Managed:           &ad.Managed,
		LastUsedUsers:     ad.LastUsedUsers,
		OsId:              osId,
		Os:                ad.Os,
		AgentVersion:      &a.Version,
		AgentName:         &a.Name,
		AgentStatus:       &a.Status,
		AdapterName:       adapter.Name,
		AdapterId:         domain.GetAdapterTypeByName(adapter.Name),
		Adapter:           domain.Adapter{},
		Client:            domain.AdapterClient{},
		InstalledSoftware: ad.InstalledSoftware,
		Interfaces:        netInterfaces,
		FirewallRules:     ad.FirewallRules,
		Type:              &ad.DeviceType,
		Model:             &ad.Model,
		Manufacturer:      &ad.Manufacturer,
		Serial:            &ad.Serial,
		Family:            &ad.Family,
		BiosVersion:       &ad.BiosVersion,
		BiosSerial:        &ad.BiosSerial,
		Data:              adapter.Data,
		DeviceId:          uuid.UUID{},
	}, nil
}
