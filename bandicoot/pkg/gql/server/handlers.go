package server

import (
	"bandicoot/internal"
	"bandicoot/pkg/gql"
	"context"
	"github.com/99designs/gqlgen/graphql"
	"github.com/99designs/gqlgen/handler"
	"github.com/gin-gonic/gin"
	"net/http"
	"strconv"
)

// Defining the Graphql handler
func graphqlHandler() gin.HandlerFunc {
	// NewExecutableSchema and Config are in the generated.go file
	// Resolver is in the resolver.go file
	c := gql.Config{Resolvers: &gql.Resolver{}}
	c.Directives.Relation = func(ctx context.Context, obj interface{}, next graphql.Resolver, name string, fkName, relationFkName []string, relType string, manyToManyTable *string, joinOn []string) (interface{}, error) {
		return next(ctx)
	}
	c.Directives.Jsonpath = func(ctx context.Context, obj interface{}, next graphql.Resolver, name *string, depends []*string) (interface{}, error) {
		return next(ctx)
	}

	c.Directives.ViewFunction = func(ctx context.Context, obj interface{}, next graphql.Resolver, name *string, arguments []*string) (interface{}, error) {
		return next(ctx)
	}

	h := handler.GraphQL(gql.NewExecutableSchema(c))

	return func(c *gin.Context) {
		h.ServeHTTP(c.Writer, c.Request)
	}
}

// Defining the Playground handler
func playgroundHandler() gin.HandlerFunc {
	h := handler.Playground("GraphQL", "/query")

	return func(c *gin.Context) {
		h.ServeHTTP(c.Writer, c.Request)
	}
}

// New Cycle request handler
func transferHandler(c *gin.Context) {
	go func() {
		fetchTime, _ := strconv.Atoi(c.Query("fetchTime"))
		f, err := internal.EpochFromInt64(int64(fetchTime))
		if err != nil {
			c.String(http.StatusBadRequest, "Bad parameters %s", err)
		}
		startCycleTransfer(c, f)
	}()
	c.String(http.StatusAccepted, "Transfer Started")

}
