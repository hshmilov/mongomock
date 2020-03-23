package gql

import (
	"bandicoot/pkg/infrastructure/persistence/pg"
	"context"
	"github.com/rs/zerolog/log"
	"github.com/spf13/viper"
)

var pgClient *pg.Repo
var CurrentCycle = 0

func InitializeDatabase() error {
	log.Info().
		Int("port", viper.GetInt("pgPort")).
		Str("hostname", viper.GetString("pgHostname")).
		Msg("Connecting to postgres...")
	var err error
	pgClient, err = pg.NewPostgresRepo(context.Background(), viper.GetString("pgHostname"), viper.GetInt("pgPort"), "postgres", "changeme")
	if err != nil {
		log.Fatal().Err(err)
		return err
	}

	l, err := pgClient.GetLastLifecycle(context.Background())
	if err != nil {
		log.Warn().Err(err).Msg("Failed to fetch lifecycle")
		return nil
	}
	// update global currentCycle
	CurrentCycle = l
	return nil
}
