package pkg

import (
	"bandicoot/pkg/domain"
	"context"
	"github.com/rs/zerolog/log"
	"time"
)

func TransferAdapters(ctx context.Context, srcRepo domain.AdapterRepository, dstRepo domain.AdapterRepository) error {
	log.Info().Msg("Finding all Adapters")
	adapters, err := srcRepo.FindAdapters(ctx, 0, -1)
	if err != nil {
		return err
	}
	log.Info().Int("count", len(adapters)).Msg("Adapters Found")
	for _, adapter := range adapters {
		log.Debug().Str("adapter", adapter.Name).Str("id", string(adapter.Id)).Msg("Inserting to adapters table")
		if err := dstRepo.SaveAdapter(ctx, adapter); err != nil {
			log.Warn().Str("adapter", adapter.Name).Msg("Failed to Insert")
		}
	}
	return nil
}

func TransferOS(ctx context.Context, srcRepo domain.OSRepository, dstRepo domain.OSRepository) error {
	log.Info().Msg("Finding all operating systems")
	oo, err := srcRepo.FindOperatingSystems(ctx, 0, -1)
	if err != nil {
		return err
	}
	log.Info().Int("count", len(oo)).Msg("operating systems Found")
	for _, o := range oo {
		log.Debug().Str("o", o.Type).Str("id", o.Id.String()).Msg("Inserting os to table")
		if err := dstRepo.SaveOperatingSystems(ctx, o); err != nil {
			log.Warn().Str("id", o.Id.String()).Msg("Failed to Insert os")
		}
	}
	return nil
}

func TransferTags(ctx context.Context, srcRepo domain.TagsRepository, dstRepo domain.TagsRepository) error {
	log.Info().Msg("Finding all tags")
	tags, err := srcRepo.FindTags(ctx, 0, -1)
	if err != nil {
		return err
	}
	for _, t := range tags {
		if err := dstRepo.CreateTag(ctx, t); err != nil {
			log.Warn().Str("tag", t.Name).Msg("Failed to Insert")
		}
	}
	return nil
}

func TransferDevices(
	ctx context.Context,
	srcRepo domain.DeviceRepository,
	dstRepo domain.AdapterDeviceRepo,
	fetchCycle int, offset, chunkLimit, rate int64) error {
	failedCount := 0
	count := srcRepo.CountDevices(ctx)
	log.Info().Int64("count", count).Msg("Finding correlated device count")
	start := time.Now()
	current := offset
	for {
		if current > count {
			break
		}
		cdcd, _ := srcRepo.FindDevices(ctx, current, chunkLimit)
		log.Info().Int64("count", count).Msg("Starting device insert into destination repo")
		for _, cd := range cdcd {
			for _, d := range cd.AdapterDevices {
				d.FetchCycle = fetchCycle
				err := dstRepo.InsertAdapterDevice(ctx, d)
				if err != nil {
					log.Error().Err(err).Msg("Failed to insert device")
					failedCount++
				}
			}
		}
		current += chunkLimit
		log.Info().Int64("count", current).Msg("Current device status")
		time.Sleep(time.Duration(rate) * time.Second)
	}
	elapsed := time.Since(start)
	log.Debug().Dur("elapsed", elapsed).Int("failed", failedCount).Msg("Transfer execution")
	return nil
}

func TransferUsers(
	ctx context.Context,
	srcRepo domain.UserRepository,
	dstRepo domain.AdapterUserRepo,
	fetchCycle int, offset, chunkLimit, rate int64) error {

	failedCount := 0
	count := srcRepo.CountUsers(ctx)
	log.Info().Int64("count", count).Msg("Current correlated user count")
	start := time.Now()
	current := offset
	for {
		if current > count {
			break
		}
		log.Info().Int64("count", count).Msg("Starting users insert into destination repo")
		cdcd, _ := srcRepo.FindUsers(ctx, current, chunkLimit)
		for _, cd := range cdcd {
			for _, d := range cd.AdapterUsers {
				d.FetchCycle = fetchCycle
				err := dstRepo.InsertAdapterUser(ctx, d)
				if err != nil {
					log.Trace().Err(err).Msg("Failed to insert user")
					failedCount++
					continue
				}
			}
		}
		current += chunkLimit
		log.Info().Int64("count", current).Int("failedCount", failedCount).Msg("Current user status")
		time.Sleep(time.Duration(rate) * time.Second)
	}
	elapsed := time.Since(start)
	log.Debug().Dur("elapsed", elapsed).Int("failed", failedCount).Msg("Transfer execution")
	return nil
}
