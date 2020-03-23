package mongo

import (
	"bandicoot/pkg/domain"
	"context"
	"github.com/rs/zerolog/log"
	"go.mongodb.org/mongo-driver/bson"
)

func (m *Repo) FindAdapters(ctx context.Context, skip, limit int64) ([]domain.Adapter, error) {

	adapters, err := m.actualFindAdapters(ctx, "devices_db")
	if err != nil {
		return nil, err
	}
	userAdapters, err := m.actualFindAdapters(ctx, "users_db")
	if err != nil {
		return nil, err
	}
	adapters = append(adapters, userAdapters...)
	return adapters, nil
}

func (m *Repo) actualFindAdapters(ctx context.Context, collectionName string) ([]domain.Adapter, error) {

	collection := m.client.Database("aggregator").Collection(collectionName)
	results, err := collection.Distinct(ctx, "adapters.plugin_name", bson.M{})
	if err != nil {
		return nil, err
	}
	log.Info().Msg("Started finding adapters")
	var adapters []domain.Adapter
	for _, adapterName := range results {
		cur, err := collection.Aggregate(ctx, []bson.M{
			{"$unwind": "$adapters"},
			{"$match": bson.M{"adapters.plugin_name": bson.M{"$eq": adapterName}}},
			{"$project": bson.M{
				"plugin_name": "$adapters.plugin_name",
				"properties":  "$adapters.data.adapter_properties",
			}},
			{"$limit": 1},
		})
		if err != nil {
			log.Warn().Interface("adapter", adapterName).Msg("Failed finding adapter")
			continue
		}
		var adapterData adapter
		if !cur.Next(ctx) {
			log.Warn().Interface("adapter", adapterName).Msg("Failed finding adapter")
			continue
		}
		err = cur.Decode(&adapterData)
		if err != nil {
			log.Error().Err(err).Msg("Failed to decode adapter")
			cur.Close(ctx)
			continue
		}
		log.Debug().Interface("adapter", adapterName).Msg("Decoded adapter")
		adapters = append(adapters, domain.Adapter{
			Id:         domain.GetAdapterTypeByName(adapterData.Name),
			Name:       adapterData.Name,
			Properties: adapterData.Properties,
		})
	}
	return adapters, nil
}

func (m *Repo) GetAdapter(ctx context.Context, a domain.AdapterType) (domain.Adapter, error) {
	return domain.Adapter{}, nil
}

func (m *Repo) SaveAdapter(ctx context.Context, a domain.Adapter) error {
	return nil
}

func (m *Repo) DeleteAdapter(ctx context.Context, a domain.AdapterType) error {
	return nil
}
