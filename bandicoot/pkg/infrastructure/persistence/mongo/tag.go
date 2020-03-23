package mongo

import (
	"bandicoot/pkg/domain"
	"context"
	"errors"
	"github.com/rs/zerolog/log"
	"go.mongodb.org/mongo-driver/bson"
)

type tagsResult struct {
	Tags []string
}

func (m *Repo) FindTags(ctx context.Context, skip, limit int) ([]domain.Tag, error) {
	collection := m.client.Database("aggregator").Collection("devices_db")
	log.Info().Msg("Started finding all tags")
	cur, err := collection.Aggregate(ctx, []bson.M{
		{"$unwind": "$tags"},
		{"$group": bson.M{"_id": 0, "tags": bson.M{"$addToSet": "$tags.name"}}},
	})
	if err != nil {
		log.Error().Err(err).Msg("Failed to query tags")
		return nil, err
	}

	if !cur.Next(ctx) {
		return nil, errors.New("no tags found")
	}
	var result tagsResult
	err = cur.Decode(&result)
	if err != nil {
		log.Error().Err(err).Msg("Failed to decode tags")
		return nil, err
	}
	var tags []domain.Tag
	for _, t := range result.Tags {
		tags = append(tags, domain.Tag{
			Name:    t,
			Level:   domain.NONE,
			Creator: domain.AXONIUS,
		})
	}
	return tags, nil
}

func (m *Repo) CreateTag(ctx context.Context, t domain.Tag) error {
	return errors.New("not implemented")
}
