package mongo

import (
	"context"
	"fmt"
	"github.com/rs/zerolog/log"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
	"go.mongodb.org/mongo-driver/mongo/readpref"
	"time"
)

// MongoRepo handles connection to a Mongo database repository
type Repo struct {
	client *mongo.Client
}

func NewMongoRepo(ctx context.Context, uri, username, password string) (*Repo, error) {
	ctxTimeout, _ := context.WithTimeout(ctx, 1*time.Second)
	client, err := mongo.Connect(
		ctxTimeout,
		options.Client().
			ApplyURI(uri).
			SetAuth(options.Credential{Username: username, Password: password}),
	)
	if err != nil {
		return nil, fmt.Errorf("couldn't Connect to mongo: %v", err)
	}
	log.Info().Str("uri", uri).Msg("Connected to Mongo")
	ctxTimeout, _ = context.WithTimeout(ctx, 2*time.Second)
	err = client.Ping(ctx, readpref.Primary())
	if err != nil {
		return nil, fmt.Errorf("mongo client ping failed: %v", err)
	}
	log.Info().Msg("Mongo ping was successful")
	return &Repo{client: client}, err
}
