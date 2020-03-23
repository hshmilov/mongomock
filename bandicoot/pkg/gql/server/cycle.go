package server

import (
	"bandicoot/internal"
	"bandicoot/pkg"
	"bandicoot/pkg/gql"
	"bandicoot/pkg/infrastructure/persistence/mongo"
	"bandicoot/pkg/infrastructure/persistence/pg"
	"context"
	"fmt"
	sq "github.com/Masterminds/squirrel"
	"github.com/randallmlough/pgxscan"
	"github.com/rs/zerolog/log"
	"github.com/spf13/viper"
)

// startCycleTransfer executes a cycle transfer from mongodb to postgres
func startCycleTransfer(ctx context.Context, fetchTime internal.Epoch) {
	// Connect to mongo and postgres
	mgClient, err := mongo.NewMongoRepo(ctx, fmt.Sprintf("mongodb://%s:%d",
		viper.GetString("mgHostname"), viper.GetInt("mgPort")), "ax_user", "ax_pass")
	if err != nil {
		log.Error().Err(err).Msg("Failed to connect to mongodb")
		return
	}
	pgClient, err := pg.NewPostgresRepo(ctx, viper.GetString("pgHostname"), viper.GetInt("pgPort"), "postgres", "changeme")
	if err != nil {
		log.Error().Err(err).Msg("Failed to connect to postgres")
		return
	}
	// Make sure to close the client
	defer pgClient.Close()

	id := createCycle(ctx, pgClient, fetchTime)
	if id == -1 {
		log.Error().Err(err).Msg("Failed to create new cycle")
		return
	}
	log.Info().Int("cycle", id).Msg("created lifecycle")
	err = addCyclePartitions(ctx, pgClient, id)
	if err != nil {
		log.Error().Err(err).Msg("Failed to create new cycle partition tables")
		return
	}

	log.Info().Int("cycle", id).Msg("Starting transfer")
	err = transferCycle(ctx, mgClient, pgClient, id)
	if err != nil {
		log.Error().Err(err).Msg("Failed Transfer")
		return
	}
	log.Info().Int("cycle", id).Msg("pruning partitions")
	err = prunePartitions(ctx, pgClient, id)
	if err != nil {
		log.Error().Err(err).Msg("Failed pruning")
		return
	}
	// Update current cycle
	gql.CurrentCycle = id
}

// createCycle adds a new lifecycle to the database
func createCycle(ctx context.Context, client pg.Pgx, fetchTime internal.Epoch) int {
	sql, _ := sq.Select("add_lifecycle(?)").PlaceholderFormat(sq.Dollar).MustSql()
	rows, err := client.Query(ctx, sql, fetchTime)
	if err != nil {
		return -1
	}
	var fetchCycle int
	err = pgxscan.NewScanner(rows).Scan(&fetchCycle)
	if err != nil {
		log.Error().Err(err).Msg("Failed to execute scan on adapter device")
		return -1
	}
	return fetchCycle
}

// addCyclePartitions adds partitions to the database
func addCyclePartitions(ctx context.Context, client pg.Pgx, cycleId int) error {
	q, _ := sq.Select("add_cycle_partitions(?)").PlaceholderFormat(sq.Dollar).MustSql()
	err := client.Exec(ctx, q, cycleId)
	if err != nil {
		return err
	}
	return nil
}

// transferCycle does the actual transfer from mongodb to postgres
func transferCycle(ctx context.Context, mgClient *mongo.Repo, pgClient *pg.Repo, cycleId int) error {

	err := pkg.TransferAdapters(ctx, mgClient, pgClient)
	if err != nil {
		log.Err(err).Msg("Failed to transfer adapters")
		return err
	}
	err = pkg.TransferOS(ctx, mgClient, pgClient)
	if err != nil {
		log.Err(err).Msg("Failed to transfer operating systems")
		return err
	}

	log.Info().Int("cycle", cycleId).Msg("Finished to transfer adapters")
	err = pkg.TransferDevices(ctx, mgClient, pgClient, cycleId, 0, 5000, 5)
	if err != nil {
		log.Err(err).Msg("Failed to transfer devices")
		return err
	}
	log.Info().Int("cycle", cycleId).Msg("Finished to transfer devices")
	err = pkg.TransferUsers(ctx, mgClient, pgClient, cycleId, 0, 5000, 5)
	if err != nil {
		log.Err(err).Msg("Failed to transfer users")
		return err
	}
	log.Info().Int("cycle", cycleId).Msg("Finished to transfer users")
	return nil
}

// prunePartitions removes all partitions up to given cycle id (including)
func prunePartitions(ctx context.Context, client pg.Pgx, cycleId int) error {
	q, _ := sq.Select("prune_partitions(?)").PlaceholderFormat(sq.Dollar).MustSql()
	log.Info().Int("cycle", cycleId).Msgf("deleting partitions up to %d",
		cycleId-viper.GetInt("partitionCut"))
	err := client.Exec(ctx, q, cycleId-viper.GetInt("partitionCut"))
	if err != nil {
		return err
	}
	return nil
}
