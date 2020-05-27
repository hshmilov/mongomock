package gql

//go:generate go run bandicoot/cmd/sqlgen
import (
	"bandicoot/internal"
	"bandicoot/internal/sqlgen"
	"bandicoot/internal/sqlgen/sql"
	"context"
	"github.com/99designs/gqlgen/graphql"
	"github.com/jackc/pgx/v4"
	"github.com/randallmlough/pgxscan"
	"github.com/rs/zerolog/log"
	"github.com/vektah/gqlparser/v2/ast"
	"time"
)

var translatorConfig = sqlgen.Config{
	Schema:            parsedSchema,
	BeforeClauses: nil,
	BeforeTranslation: func(ctx context.Context, tableName string, def *ast.Definition, args map[string]interface{}) {
		switch def.Name {
		case "User", "AdapterUser", "Device", "AdapterDevice", "Interfaces", "FirewallRules":
			if where, ok := args[sqlgen.WhereClause]; ok {
				if whereMap, ok := where.(map[string]interface{}); ok {
					// Inject fetch cycle
					if sqlgen.WhereClauseHasKey(whereMap, "fetchCycle") {
						return
					}
					whereMap["fetchCycle"] = map[string]interface{}{"eq": CurrentCycle}
				}
			} else {
				args[sqlgen.WhereClause] = map[string]interface{}{"fetchCycle": map[string]interface{}{"eq": CurrentCycle}}
			}
		}
	},
}

func executeTranslation(ctx context.Context) (sqlgen.Result, error) {
	fieldCtx, opCtx := graphql.GetFieldContext(ctx), graphql.GetOperationContext(ctx)
	start := time.Now()
	defer log.Ctx(ctx).Debug().TimeDiff("elapsed", time.Now(), start).Msg("Time took to translate query")
	return sql.CreateTranslator(ctx, translatorConfig, opCtx.Variables, opCtx.Doc.Fragments, nil).Translate(fieldCtx.Field.Field)
}

func executeAggregateQuery(ctx context.Context) (pgx.Rows, error) {
	fieldCtx, opCtx := graphql.GetFieldContext(ctx), graphql.GetOperationContext(ctx)
	start := time.Now()
	t, err := sql.CreateTranslator(ctx, translatorConfig, opCtx.Variables, opCtx.Doc.Fragments, nil).TranslateAggregate(fieldCtx.Field.Field)
	log.Debug().TimeDiff("elapsed", time.Now(), start).Msg("Time took to translate aggregate query")
	if err != nil {
		log.Error().Err(err).Msg("Failed to translate")
		return nil, err
	}
	rows, err := pgClient.Query(ctx, t.Query, t.Params...)
	if err != nil {
		log.Error().Err(err).Msg("Failed to execute query")
		return nil, err
	}
	log.Debug().
		TimeDiff("elapsed", time.Now(), start).
		Str("type", fieldCtx.Field.Name).
		Str("query", internal.TruncateString(t.Query, 120)).
		Interface("params", t.Params).
		Msg("Time took for aggregate query execution")
	return rows, err
}

type Resolver struct{}

func (r *Resolver) AdapterDevice() AdapterDeviceResolver {
	return &adapterDeviceResolver{r}
}

func (r *Resolver) AdapterUser() AdapterUserResolver {
	return &adapterUserResolver{r}
}

func (r *Resolver) Device() DeviceResolver {
	return &deviceResolver{r}
}

func (r *Resolver) User() UserResolver {
	return &userResolver{r}
}

func (r *Resolver) Query() QueryResolver {
	return &queryResolver{r}
}

type queryResolver struct{ *Resolver }



func (r *queryResolver) Users(ctx context.Context, _, _ *int, _ *UserBoolExp, _ []UserOrderBy) ([]User, error) {
	var dd []User
	t, err := executeTranslation(ctx)
	if err != nil {
		log.Err(err).Msg("Failed sql translation")
		return nil, err
	}
	rows, err := pgClient.Query(ctx, t.Query, t.Params...)
	if err != nil {
		log.Err(err).Str("query", t.Query).Interface("params", t.Params).Msg("Failed sql execution")
		return nil, err
	}
	start := time.Now()
	err = pgxscan.NewScanner(rows).Scan(&dd)
	if err != nil {
		log.Error().Err(err).Msg("Failed to execute scan on adapter device")
		return nil, err
	}
	log.Debug().TimeDiff("elapsed", time.Now(), start).Str("type", "User").Msg("Time took for query scanning")
	return dd, nil
}

func (r *queryResolver) AdapterUsers(ctx context.Context, _ *int, _ *int, _ *AdapterUserBoolExp, _ []AdapterUserOrderBy) ([]AdapterUser, error) {
	var dd []AdapterUser
	t, err := executeTranslation(ctx)
	if err != nil {
		log.Err(err).Msg("Failed sql translation")
		return nil, err
	}
	rows, err := pgClient.Query(ctx, t.Query, t.Params...)
	if err != nil {
		log.Err(err).Str("query", t.Query).Interface("params", t.Params).Msg("Failed sql execution")
		return nil, err
	}
	start := time.Now()
	err = pgxscan.NewScanner(rows).Scan(&dd)
	if err != nil {
		log.Error().Err(err).Msg("Failed to execute scan on adapter device")
		return nil, err
	}
	log.Debug().TimeDiff("elapsed", time.Now(), start).Str("type", "User").Msg("Time took for query scanning")
	return dd, nil
}

func (r *queryResolver) Devices(ctx context.Context, _ *int, _ *int, _ *DeviceBoolExp, _ []DeviceOrderBy) ([]Device, error) {
	var dd []Device
	t, err := executeTranslation(ctx)
	if err != nil {
		log.Err(err).Msg("Failed sql translation")
		return nil, err
	}
	rows, err := pgClient.Query(ctx, t.Query, t.Params...)
	if err != nil {
		log.Err(err).Str("query", t.Query).Interface("params", t.Params).Msg("Failed sql execution")
		return nil, err
	}
	start := time.Now()
	err = pgxscan.NewScanner(rows).Scan(&dd)
	if err != nil {
		log.Error().Err(err).Msg("Failed to execute scan on adapter device")
		return nil, err
	}
	log.Debug().
		TimeDiff("elapsed", time.Now(), start).
		Str("query", internal.TruncateString(t.Query, 120)).
		Interface("params", t.Params).
		Str("type", "Devices").
		Msg("Time took for query scanning")
	return dd, nil
}

func (r *queryResolver) AdapterDevices(ctx context.Context, _, _ *int, _ *AdapterDeviceBoolExp, _ []AdapterDeviceOrderBy) ([]AdapterDevice, error) {
	var dd []AdapterDevice
	t, err := executeTranslation(ctx)
	if err != nil {
		log.Err(err).Msg("Failed sql translation")
		return nil, err
	}
	rows, err := pgClient.Query(ctx, t.Query, t.Params...)
	if err != nil {
		log.Err(err).Str("query", t.Query).Interface("params", t.Params).Msg("Failed sql execution")
		return nil, err
	}
	start := time.Now()
	err = pgxscan.NewScanner(rows).Scan(&dd)
	if err != nil {
		log.Error().Err(err).Msg("Failed to execute scan on adapter device")
		return nil, err
	}
	log.Debug().TimeDiff("elapsed", time.Now(), start).Str("type", "AdapterDevices").Msg("Time took for query scanning")
	return dd, nil
}

func (r *queryResolver) AdapterDevicesAggregate(ctx context.Context, _, _ []AdapterDevicesAggregateColumns, _ []AggregateOrdering, _ *int, _ *int, _ *AdapterDeviceBoolExp) ([]AdapterDevicesAggregate, error) {
	rows, err := executeAggregateQuery(ctx)
	if err != nil {
		return nil, err
	}
	var aggregates []AdapterDevicesAggregate
	err = pgxscan.NewScanner(rows).Scan(&aggregates)
	if err != nil {
		log.Error().Err(err).Msg("Failed to execute scan")
		return nil, err
	}
	return aggregates, nil
}

func (r *queryResolver) DevicesAggregate(ctx context.Context, _, _ []DevicesAggregateColumns, _ []AggregateOrdering, _ *int, _ *int, _ *DeviceBoolExp) ([]DevicesAggregate, error) {
	rows, err := executeAggregateQuery(ctx)
	if err != nil {
		return nil, err
	}
	var aggregates []DevicesAggregate
	err = pgxscan.NewScanner(rows).Scan(&aggregates)
	if err != nil {
		log.Error().Err(err).Msg("Failed to execute scan")
		return nil, err
	}
	return aggregates, nil
}

func (r *queryResolver) UsersAggregate(ctx context.Context, _, _ []UsersAggregateColumns, _ []AggregateOrdering, _ *int, _ *int, _ *UserBoolExp) ([]UsersAggregate, error) {
	rows, err := executeAggregateQuery(ctx)
	if err != nil {
		return nil, err
	}
	var aggregates []UsersAggregate
	err = pgxscan.NewScanner(rows).Scan(&aggregates)
	if err != nil {
		log.Error().Err(err).Msg("Failed to execute scan")
		return nil, err
	}
	return aggregates, nil
}

func (r *queryResolver) AdapterUsersAggregate(ctx context.Context, _, _ []AdapterUsersAggregateColumns, _ []AggregateOrdering, _ *int, _ *int, _ *AdapterUserBoolExp) ([]AdapterUsersAggregate, error) {
	rows, err := executeAggregateQuery(ctx)
	if err != nil {
		return nil, err
	}
	var aggregates []AdapterUsersAggregate
	err = pgxscan.NewScanner(rows).Scan(&aggregates)
	if err != nil {
		log.Error().Err(err).Msg("Failed to execute scan")
		return nil, err
	}
	return aggregates, nil
}
