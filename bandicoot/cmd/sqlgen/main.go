package main

import (
	"bandicoot/internal/sqlgen/augmentors"
	"fmt"
	"github.com/99designs/gqlgen/api"
	"github.com/99designs/gqlgen/codegen/config"
	"github.com/99designs/gqlgen/plugin/modelgen"
	"github.com/99designs/gqlgen/plugin/resolvergen"
	"github.com/iancoleman/strcase"
	"os"
)

// Defining mutation function
func mutateHook(b *modelgen.ModelBuild) *modelgen.ModelBuild {
	for _, model := range b.Models {
		for _, field := range model.Fields {
			if field.Name == "data" && model.Name == "AdapterDevice" {
				field.Type = config.MapType
			}
			field.Tag = ` json:"` + strcase.ToSnake(field.Name) + `"`
		}
	}

	return b
}

// TODO: make this get argument of input output and gqlgen yml
func main() {
	augmentors.Generate("../../api/schema/", "../../api/generated/augmented_schema.graphql",
		[]augmentors.Augmenter{augmentors.Pagination{}, augmentors.Filters{}, augmentors.Ordering{}, augmentors.Aggregation{}})

	cfg, err := config.LoadConfig("../../pkg/gql/gqlgen.yml")
	if err != nil {
		fmt.Fprintln(os.Stderr, "failed to load config", err.Error())
		os.Exit(2)
	}

	// Attaching the mutation function onto modelgen plugin
	p := modelgen.Plugin{
		MutateHook: mutateHook,
	}

	err = api.Generate(cfg,
		api.NoPlugins(),
		api.AddPlugin(&p),
		api.AddPlugin(resolvergen.New()),
	)
	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		os.Exit(3)
	}
}
