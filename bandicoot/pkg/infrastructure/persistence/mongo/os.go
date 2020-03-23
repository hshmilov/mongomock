package mongo

import (
	"bandicoot/pkg/domain"
	"context"
	"github.com/rs/zerolog/log"
	"go.mongodb.org/mongo-driver/bson"
)

type os struct {
	Type          string
	Distribution  string
	Bitness       int
	ServicePack   string
	KernelVersion string `bson:"kernel_version" json:"kernel_version"`
	CodeName      string `bson:"code_name" json:"code_name"`
	Major         int
	Minor         int
	Build         string
	RawName       string `bson:"os_str" json:"os_str"`
}

func (m *Repo) FindOperatingSystems(ctx context.Context, skip, limit int64) ([]domain.OperatingSystem, error) {
	collection := m.client.Database("aggregator").Collection("devices_db")
	results, err := collection.Distinct(ctx, "adapters.data.os", bson.M{})
	if err != nil {
		return nil, err
	}
	log.Info().Msg("Started parsing operating systems")
	var oss []domain.OperatingSystem
	for _, data := range results {
		var mOs os
		_, b, err := bson.MarshalValue(data)
		if err != nil {
			log.Error().Err(err).Msg("Failed to marshal data")
		}
		err = bson.Unmarshal(b, &mOs)
		if err != nil {
			log.Error().Err(err).Msg("Failed to decode")
			continue
		}
		if mOs.Type == "" {
			log.Debug().Interface("data", data).Msg("os missing type skipping")
			continue
		}

		//v, err := semver.ParseTolerant(mOs.Build)
		//if err != nil {
		//	log.Debug().Err(err).Str("build", mOs.Build).Msg("Failed to parse semantic version")
		//} else {
		//	mOs.Minor = int(v.Minor)
		//	mOs.Major = int(v.Major)
		//	mOs.Build = strings.Join(v.Build, "")
		//}

		oss = append(oss, domain.OperatingSystem{
			Id:            domain.GetOSId(mOs.Type, mOs.Bitness, mOs.Distribution),
			Type:          mOs.Type,
			Distribution:  mOs.Distribution,
			Architecture:  mOs.Bitness,
			ServicePack:   mOs.ServicePack,
			KernelVersion: mOs.KernelVersion,
			CodeName:      mOs.CodeName,
			Major:         mOs.Major,
			Minor:         mOs.Minor,
			Build:         mOs.Build,
			RawName:       mOs.RawName,
		})

	}
	return oss, nil
}

func (m *Repo) SaveOperatingSystems(ctx context.Context, a domain.OperatingSystem) error {
	panic("not implemented")
}
