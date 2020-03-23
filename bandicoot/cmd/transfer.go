package cmd

import (
	"bandicoot/pkg"
	"bandicoot/pkg/infrastructure/persistence/mongo"
	"bandicoot/pkg/infrastructure/persistence/pg"
	"context"
	"fmt"
	"github.com/rs/zerolog/log"
	"github.com/spf13/cobra"
	"os"
	"os/signal"
)

var transferCmd = &cobra.Command{
	Use:   "transfer",
	Short: "Transfers data from mongo to postgres",
	Run:   transferData,
}

func transferData(_ *cobra.Command, _ []string) {
	ctx, cancel := context.WithCancel(context.Background())
	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt)
	defer ctx.Done()
	go func() {
		select {
		case <-c:
			cancel()
		case <-ctx.Done():
			log.Printf("Context done")
		}
	}()
	mgClient, err := mongo.NewMongoRepo(ctx, fmt.Sprintf("mongodb://%s:%d", mgHostname, mgPort), "ax_user", "ax_pass")
	if err != nil {
		log.Printf("Error: %v", err)
		return
	}
	pgClient, err := pg.NewPostgresRepo(ctx, pgHostName, pgPort, "postgres", "changeme")
	if err != nil {
		log.Printf("Error: %v", err)
		// return
	}
	if transferAdapters {
		err = pkg.TransferAdapters(ctx, mgClient, pgClient)
		if err != nil {
			log.Err(err).Msg("Failed to insert adapters")
			return
		}
	}

	if transferOS {
		err = pkg.TransferOS(ctx, mgClient, pgClient)
		if err != nil {
			log.Err(err).Msg("Failed to insert adapters")
			return
		}
	}

	if transferTags {
		err = pkg.TransferTags(ctx, mgClient, pgClient)
		if err != nil {
			log.Err(err).Msg("Failed to insert tags")
			return
		}
	}

	if transferDevices {
		err = pkg.TransferDevices(ctx, mgClient, pgClient,
			transferFetchCycle, int64(transferDeviceOffset), transferChunkLimit, int64(transferRateLimit))
		if err != nil {
			log.Err(err).Msg("Failed to insert devices")
			return
		}
	}

	if transferUsers {
		err = pkg.TransferUsers(ctx, mgClient, pgClient,
			transferFetchCycle, int64(transferDeviceOffset), transferChunkLimit, int64(transferRateLimit))
		if err != nil {
			log.Err(err).Msg("Failed to insert users")
			return
		}
	}
}
