package pg

import (
	"context"
	"fmt"
	"github.com/jackc/pgx/v4"
	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/rs/zerolog/log"
)

type Repo struct {
	pool *pgxpool.Pool
}

func NewPostgresRepo(ctx context.Context, hostname string, port int, username, password string) (*Repo, error) {
	pgxConfig, err := pgxpool.ParseConfig(fmt.Sprintf("postgres://%s:%s@%s:%d/axonius", username, password, hostname, port))
	if err != nil {
		log.Error().Err(err).Msg("Failed to create configuration")
		return nil, err
	}
	pgxConfig.AfterConnect = afterConnect
	pool, err := pgxpool.ConnectConfig(ctx, pgxConfig)
	if err != nil {
		log.Error().Err(err).Msg("Failed to connect")
		return nil, err
	}
	return &Repo{pool: pool}, nil
}

func afterConnect(_ context.Context, conn *pgx.Conn) error {
	//conn.ConnInfo().RegisterDataType(pgtype.DataType{
	//	Value: &satori.UUID{},
	//	Name:  "uuid",
	//	OID:   2950,
	//})
	return nil
}

func (p *Repo) Close() {
	p.pool.Close()
}

type Pgx interface {
	Query(ctx context.Context, query string, args ...interface{}) (pgx.Rows, error)
	Exec(ctx context.Context, query string, args ...interface{}) error
}

func (p *Repo) Query(ctx context.Context, query string, args ...interface{}) (pgx.Rows, error) {
	rows, err := p.pool.Query(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	return rows, nil
}

func (p *Repo) Exec(ctx context.Context, query string, args ...interface{}) error {
	_, err := p.pool.Exec(ctx, query, args...)
	return err
}
