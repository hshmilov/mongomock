package pg

import (
	"bandicoot/pkg/domain"
	"context"
	sq "github.com/Masterminds/squirrel"
	"github.com/rs/zerolog/log"
	uuid "github.com/satori/go.uuid"
)

// TODO: in general this is not very effective, we might consider A. using goroutines B. making it all in 1 transaction
func (p *Repo) InsertAdapterDevice(ctx context.Context, ad domain.AdapterDevice) error {
	err := p.insertAdapterDevice(ctx, ad)
	if err != nil {
		return err
	}
	// Insert all rules for this adapter device
	err = p.insertAdapterDeviceInterfaces(ctx, ad.Id, ad.FetchCycle, ad.Interfaces)
	if err != nil {
		return err
	}
	err = p.insertAdapterDeviceTags(ctx, ad.Id, ad.Tags)
	if err != nil {
		return err
	}
	// Insert all installed software
	err = p.insertInstalledSoftware(ctx, ad.InstalledSoftware)
	if err != nil {
		return err
	}
	// Insert all installed software for this adapter device
	err = p.insertAdapterDeviceSoftware(ctx, ad.Id, ad.FetchCycle, ad.InstalledSoftware)
	if err != nil {
		return err
	}
	// Insert all firewall rules
	err = p.insertFirewallRules(ctx, ad.FirewallRules)
	if err != nil {
		return err
	}
	// Insert all rules for this adapter device
	err = p.insertAdapterDeviceFirewallRules(ctx, ad.Id, ad.FetchCycle, ad.FirewallRules)
	if err != nil {
		return err
	}

	return nil
}

func(p *Repo) insertNetworkInterfacesVlans(ctx context.Context, deviceId uuid.UUID, fetchCycle int, interfaces []domain.NetworkInterfaceVlan) error {

	query := sq.Insert("network_interfaces_vlans").Columns(
		"device_id", "mac_addr", "fetch_cycle", "name", "tag_id", "tagged",
	).PlaceholderFormat(sq.Dollar).Suffix("ON CONFLICT DO NOTHING")

	for _, i := range interfaces {
		query = query.Values(deviceId, i.MacAddr, fetchCycle, i.MacAddr, i.Name, i.TagId, i.Tagged)
	}

	sql, args, err := query.ToSql()
	if err != nil {
		log.Error().Err(err).Msg("Failed to build adapter device interfaces insert query")
		return err
	}
	_, err = p.pool.Exec(ctx, sql, args...)
	if err != nil {
		log.Error().Err(err).Msg("Failed to insert adapter device interfaces")
		return err
	}

	return nil

}

func (p *Repo) insertAdapterDeviceInterfaces(ctx context.Context, deviceId uuid.UUID, fetchCycle int, interfaces []domain.NetworkInterface) error {
	if len(interfaces) == 0 {
		return nil
	}
	query := sq.Insert("network_interfaces").Columns(
		"device_id", "fetch_cycle", "ip_addrs", "mac_addr", "name",
		"subnets", "gateway", "admin_status", "operational_status", "port", "port_type", "mtu",
		).PlaceholderFormat(sq.Dollar).Suffix("ON CONFLICT DO NOTHING")


	for _, i := range interfaces {
		query = query.Values(deviceId, fetchCycle, i.IpAddrs, i.MacAddr, i.Name, i.Subnets,
			i.Gateway, i.AdminStatus, i.OperationalStatus, i.Port, i.PortType, i.Mtu)

		// insert interface vlans
		if len(i.Vlans) > 0 {
			err := p.insertNetworkInterfacesVlans(ctx, deviceId, fetchCycle, i.Vlans)
			if err != nil {
				return err
			}
		}
	}
	sql, args, err := query.ToSql()
	if err != nil {
		log.Error().Err(err).Msg("Failed to build adapter device interfaces insert query")
		return err
	}
	_, err = p.pool.Exec(ctx, sql, args...)
	if err != nil {
		log.Error().Err(err).Msg("Failed to insert adapter device interfaces")
		return err
	}

	return nil
}

func (p *Repo) insertAdapterDeviceFirewallRules(ctx context.Context, deviceId uuid.UUID, fetchCycle int, rules []domain.FirewallRule) error {
	if len(rules) == 0 {
		return nil
	}
	query := sq.Insert("adapter_device_firewall_rules").Columns("adapter_device_id", "fetch_cycle", "name").PlaceholderFormat(sq.Dollar).Suffix("ON CONFLICT DO NOTHING")
	for _, r := range rules {
		query = query.Values(deviceId, fetchCycle, r.Name)
	}
	sql, args, err := query.ToSql()
	if err != nil {
		log.Error().Err(err).Msg("Failed to build adapter device firewall rules insert query")
		return err
	}
	_, err = p.pool.Exec(ctx, sql, args...)
	if err != nil {
		log.Error().Err(err).Msg("Failed to insert adapter device rules")
		return err
	}
	return nil
}

func (p *Repo) insertFirewallRules(ctx context.Context, rules []domain.FirewallRule) error {

	if len(rules) == 0 {
		return nil
	}
	query := sq.Insert("firewall_rules").
		Columns("name", "type", "direction", "source", "target", "protocol", "dst_port", "src_port").
		PlaceholderFormat(sq.Dollar).Suffix("ON CONFLICT DO NOTHING")
	for _, r := range rules {
		query = query.Values(r.Name, r.Type, r.Direction, r.Source, r.Target, r.Protocol, r.DstPort, r.SrcPort)
	}
	sql, args, err := query.ToSql()
	if err != nil {
		log.Error().Err(err).Msg("Failed to build firewall_rules insert query")
		return err
	}
	_, err = p.pool.Exec(ctx, sql, args...)
	if err != nil {
		log.Error().Err(err).Msg("Failed to insert tags")
		return err
	}
	return nil
}

func (p *Repo) insertAdapterDeviceSoftware(ctx context.Context, deviceId uuid.UUID, fetchCycle int, software []domain.InstalledSoftware) error {
	if len(software) == 0 {
		return nil
	}
	query := sq.Insert("adapter_device_installed_software").Columns("adapter_device_id", "fetch_cycle", "name", "version").PlaceholderFormat(sq.Dollar).Suffix("ON CONFLICT DO NOTHING")
	for _, s := range software {
		query = query.Values(deviceId, fetchCycle, s.Name, s.Version)
	}
	sql, args, err := query.ToSql()
	if err != nil {
		log.Error().Err(err).Msg("Failed to build tags insert query")
		return err
	}
	_, err = p.pool.Exec(ctx, sql, args...)
	if err != nil {
		log.Error().Err(err).Msg("Failed to insert tags")
		return err
	}
	return nil
}

func (p *Repo) insertInstalledSoftware(ctx context.Context, software []domain.InstalledSoftware) error {

	if len(software) == 0 {
		return nil
	}
	query := sq.Insert("installed_software").
		Columns("name", "version", "raw_version", "description", "architecture", "publisher", "vendor", "sw_license", "cve_count").
		PlaceholderFormat(sq.Dollar).Suffix("ON CONFLICT DO NOTHING")
	for _, s := range software {
		query = query.Values(s.Name, s.Version, s.RawVersion, s.Description, s.Architecture, s.Publisher, s.Vendor, s.SwLicense, s.CveCount)
	}
	sql, args, err := query.ToSql()
	if err != nil {
		log.Error().Err(err).Msg("Failed to build installed_software insert query")
		return err
	}
	_, err = p.pool.Exec(ctx, sql, args...)
	if err != nil {
		log.Error().Err(err).Msg("Failed to insert installed software")
		return err
	}
	return nil

}

func (p *Repo) insertAdapterDeviceTags(ctx context.Context, deviceId uuid.UUID, tags []domain.Tag) error {
	if len(tags) == 0 {
		return nil
	}
	query := sq.Insert("adapter_device_tags").Columns("adapter_device_id", "name").PlaceholderFormat(sq.Dollar).Suffix("ON CONFLICT DO NOTHING")
	for _, t := range tags {
		query = query.Values(deviceId, t.Name)
	}
	sql, args, err := query.ToSql()
	if err != nil {
		log.Error().Err(err).Msg("Failed to build tags insert query")
		return err
	}
	_, err = p.pool.Exec(ctx, sql, args...)
	if err != nil {
		log.Error().Err(err).Msg("Failed to insert tags")
		return err
	}
	return nil
}

func (p *Repo) insertAdapterDevice(ctx context.Context, ad domain.AdapterDevice) error {
	q := sq.Insert("adapter_devices").Columns(
		"id", "fetch_cycle", "hostname", "name", "pretty_id",
		"last_seen", "domain", "managed", "part_of_domain",
		"agent_version", "agent_status", "agent_name",
		"os_id", "serial", "model", "family", "manufacturer",
		"bios_version", "bios_serial",
		"adapter_name", "adapter_id", "fetch_time",
		"data", "device_id", "last_used_users", "type").Values(
		ad.Id.String(), ad.FetchCycle, ad.Hostname, ad.Name, ad.PrettyId,
		ad.LastSeen, ad.Domain, ad.Managed, ad.PartOfDomain,
		ad.AgentVersion, ad.AgentStatus, ad.AgentName,
		ad.OsId, ad.Serial, ad.Model, ad.Family, ad.Manufacturer,
		ad.BiosVersion, ad.BiosSerial,
		ad.AdapterName, ad.AdapterId, ad.FetchTime,
		ad.Data, ad.DeviceId.String(), ad.LastUsedUsers, ad.Type).PlaceholderFormat(sq.Dollar).Suffix("ON CONFLICT DO NOTHING")
	sql, args, err := q.ToSql()
	if err != nil {
		log.Error().Err(err).Msg("Failed to build device insert query")
		return err
	}
	_, err = p.pool.Exec(ctx, sql, args...)
	if err != nil {
		log.Error().Str("query", sql).Interface("args", args).Err(err).Msg("Failed to insert device")
		return err
	}
	return nil
}
