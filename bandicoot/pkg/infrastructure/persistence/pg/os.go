package pg

import (
	"bandicoot/pkg/domain"
	"context"
	sq "github.com/Masterminds/squirrel"
	"github.com/rs/zerolog/log"
)

var insertOS = sq.Insert("operating_systems").PlaceholderFormat(sq.Dollar).Columns("id", "type", "distribution",
	"architecture", "service_pack", "kernel_version", "code_name", "major", "minor", "build", "raw_name").
	Suffix("ON CONFLICT DO NOTHING")

func (p *Repo) FindOperatingSystems(ctx context.Context, skip, limit int64) ([]domain.OperatingSystem, error) {
	panic("not implemented")
}

func (p *Repo) SaveOperatingSystems(ctx context.Context, os domain.OperatingSystem) error {
	// Insert Tag if it doesn't exist
	sql, args, err := insertOS.Values(os.Id, os.Type, os.Distribution, os.Architecture, os.ServicePack,
		os.KernelVersion, os.CodeName, os.Major, os.Minor, os.Build, os.RawName).ToSql()
	if err != nil {
		log.Error().Err(err).Msg("Failed to build os insert query")
		return err
	}
	_, err = p.pool.Exec(ctx, sql, args...)
	if err != nil {
		log.Error().Str("query", sql).Interface("args", args).Err(err).Msg("Failed to insert os")
		return err
	}
	return nil
}
