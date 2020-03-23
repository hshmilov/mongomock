package pg

import (
	"bandicoot/pkg/domain"
	"context"
	sq "github.com/Masterminds/squirrel"
	"github.com/rs/zerolog/log"
)

var insertTag = sq.Insert("tags").PlaceholderFormat(sq.Dollar).Columns("name", "level", "creator").Suffix("ON CONFLICT DO NOTHING")

func (p *Repo) FindTags(ctx context.Context, skip, limit int) ([]domain.Tag, error) {
	panic("implement me")
}

func (p *Repo) CreateTag(ctx context.Context, tag domain.Tag) error {
	// Insert Tag if it doesn't exist
	sql, args, err := insertTag.Values(tag.Name, tag.Level, tag.Creator).ToSql()
	if err != nil {
		log.Error().Err(err).Msg("Failed to build tag insert query")
		return err
	}
	_, err = p.pool.Exec(ctx, sql, args...)
	if err != nil {
		log.Error().Str("query", sql).Interface("args", args).Err(err).Msg("Failed to insert tag")
		return err
	}
	return nil
}
