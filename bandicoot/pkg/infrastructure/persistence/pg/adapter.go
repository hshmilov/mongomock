package pg

import (
	"bandicoot/pkg/domain"
	"context"
	"errors"
	sq "github.com/Masterminds/squirrel"
	"github.com/rs/zerolog/log"
)

var insertAdapter = sq.Insert("adapters").PlaceholderFormat(sq.Dollar).Columns("id", "name", "properties").Suffix("ON CONFLICT DO NOTHING")

func (p *Repo) SaveAdapter(ctx context.Context, adapter domain.Adapter) error {
	// Insert Adapter if it doesn't exist
	sql, args, err := insertAdapter.Values(adapter.Id, adapter.Name, adapter.Properties).ToSql()
	if err != nil {
		log.Error().Err(err).Msg("Failed to build adapter insert query")
		return err
	}
	_, err = p.pool.Exec(ctx, sql, args...)
	if err != nil {
		log.Error().Str("query", sql).Interface("args", args).Err(err).Msg("Failed to insert adapter")
		return err
	}
	return nil
}

func (p *Repo) FindAdapters(ctx context.Context, skip, limit int64) ([]domain.Adapter, error) {
	return nil, errors.New("not implemented")
}

func (p *Repo) GetAdapter(ctx context.Context, id domain.AdapterType) (domain.Adapter, error) {
	return domain.Adapter{}, errors.New("not implemented")
}

func (p *Repo) DeleteAdapter(ctx context.Context, a domain.AdapterType) error {
	return errors.New("not implemented")
}
