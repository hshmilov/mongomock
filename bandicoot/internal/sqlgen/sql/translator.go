package sql

import (
	"bandicoot/internal"
	"bandicoot/internal/sqlgen"
	"context"
	"errors"
	"fmt"
	sq "github.com/Masterminds/squirrel"
	"github.com/iancoleman/strcase"
	"github.com/jinzhu/inflection"
	"github.com/modern-go/reflect2"
	errors2 "github.com/pkg/errors"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
	"github.com/spf13/cast"
	"github.com/vektah/gqlparser/v2/ast"
	"math/rand"
	"net"
	"strconv"
	"strings"
)

const letterBytes = "abcdefghijklmnopqrstuvwxyz"
const (
	letterIdxBits = 6                    // 6 bits to represent a letter index
	letterIdxMask = 1<<letterIdxBits - 1 // All 1-bits, as many as letterIdxBits
	letterIdxMax  = 63 / letterIdxBits   // # of letter indices fitting in 63 bits
)

type sqlFieldType string

const (
	Column            sqlFieldType = "Column"
	Json              sqlFieldType = "Json"
	Relation          sqlFieldType = "Relation"
	Aggregate         sqlFieldType = "Aggregate"
	ViewFunction      sqlFieldType = "ViewFunction"
	AggregateFunction sqlFieldType = "AggregateFunction"
	AggregateSelect   sqlFieldType = "AggregateSelect"
)

var (
	ErrFieldMissingDefinition = errors.New("field definition missing")
	ErrFieldTranslationFailed = errors.New("field translation failed")
)

type sqlField struct {
	Name   string
	Type   sqlFieldType
	Sql    sq.SelectBuilder
	Column sq.Sqlizer
}

func getSqlType(field *ast.FieldDefinition) sqlFieldType {
	if strings.HasSuffix(field.Name, strings.ToLower(string(Aggregate))) {
		return Aggregate
	}
	if field.Directives.ForName(sqlgen.DirectiveJsonPath) != nil {
		return Json
	}
	if field.Directives.ForName(sqlgen.DirectiveRelation) != nil {
		return Relation
	}
	if field.Directives.ForName(sqlgen.DirectiveViewFunction) != nil {
		return ViewFunction
	}
	return Column
}

type not []sq.Sqlizer

func (n not) ToSql() (string, []interface{}, error) {
	s, p, e := sq.Sqlizer(n).ToSql()
	return fmt.Sprintf("NOT %s", s), p, e
}

// generateTableName is the default table alias generator creating a random table name of n letters
func generateTableName(n int) string {
	sb := strings.Builder{}
	sb.Grow(n)
	// A src.Int63() generates 63 random bits, enough for letterIdxMax characters!
	for i, cache, remain := n-1, rand.Int63(), letterIdxMax; i >= 0; {
		if remain == 0 {
			cache, remain = rand.Int63(), letterIdxMax
		}
		if idx := int(cache & letterIdxMask); idx < len(letterBytes) {
			sb.WriteByte(letterBytes[idx])
			i--
		}
		cache >>= letterIdxBits
		remain--
	}
	// Quote so we don't create saved syntax words
	return sb.String()
}

type translator struct {
	// Context given to translator
	ctx context.Context
	// Logger translator will use
	log *zerolog.Logger
	// Save config
	config sqlgen.Config
	// Schema translator will execute with
	schema *ast.Schema
	// variables passed in the query
	variables map[string]interface{}
	// fragments passed in the query
	fragments ast.FragmentDefinitionList
}

func CreateTranslator(ctx context.Context, c sqlgen.Config, variables map[string]interface{}, fragments ast.FragmentDefinitionList, logger *zerolog.Logger) sqlgen.Translator {
	// If no logger is given use global logger
	if logger == nil {
		logger = &log.Logger
	}
	if c.GenerateTableName == nil {
		c.GenerateTableName = generateTableName
	}
	return translator{ctx, logger, c, c.Schema, variables, fragments}
}

// Translate graphql query from field (root) into an sql query.
func (s translator) Translate(field *ast.Field) (sqlgen.Result, error) {
	// Find the type of the field in the schema
	currentType := s.schema.Types[field.Definition.Type.Name()]
	args := field.ArgumentMap(s.variables)
	// Check if beforeClauses hook was set, if so call it
	if s.config.BeforeTranslation != nil {
		log.Trace().Str("field", field.Name).Msg("Called before clauses hook")
		s.config.BeforeTranslation(s.ctx, currentType, args)
	}
	// the table name has to be based on the field name in snake case i.e "usersDevices" -> "user_devices"
	tableName := strcase.ToSnake(field.Name)
	// Generate a random table alias, this is important if table is recurse i.e person -> friends -> friends
	abbrTableName := s.config.GenerateTableName(4)
	query := sq.StatementBuilder.PlaceholderFormat(sq.Dollar).Select().From(fmt.Sprintf("%s AS %s", tableName, abbrTableName))
	// Collect all fields of this field
	fields, err := s.collectFields(abbrTableName, currentType, field.SelectionSet)
	if err != nil {
		return sqlgen.Result{}, err
	}
	// go over collected fields and build the SQL query
	for _, f := range fields {
		s.log.Trace().Str("field", f.Name).Str("type", string(f.Type)).Msg("Adding field to query")
		switch f.Type {
		case Json:
			query = query.Column(sq.Alias(f.Column, f.Name))
		case Relation, Aggregate, ViewFunction:
			query = query.JoinClause(f.Sql)
			fallthrough
		case Column:
			query = query.Column(f.Column)

		}
	}
	// Add all clauses to the SQL query, where, order, limit, offset etc'
	query = s.addClauses(query, args, currentType, abbrTableName)
	sql, params, err := query.ToSql()
	if err != nil {
		s.log.Error().Err(err).Msg("Failed to build SQL query")
		return sqlgen.Result{}, err
	}
	s.log.Debug().Str("query", sql).Interface("params", params).Msg("Created query")
	return sqlgen.Result{Query: sql, Params: params}, nil
}

// Translate graphql aggregate query from field (root) into an sql query.
func (s translator) TranslateAggregate(field *ast.Field) (sqlgen.Result, error) {
	query, _ := s.buildAggregateQuery(field)
	sql, params, err := query.PlaceholderFormat(sq.Dollar).ToSql()
	if err != nil {
		s.log.Error().Err(err).Msg("Failed to scan struct")
		return sqlgen.Result{}, err
	}

	s.log.Debug().Str("query", sql).Interface("params", params).Msg("Created aggregate query")
	return sqlgen.Result{Query: sql, Params: params}, nil
}

// buildAggregateQuery builds an aggregation select based on the given ast.Field
func (s translator) buildAggregateQuery(field *ast.Field) (sq.SelectBuilder, string) {

	splitName := strings.Split(field.Name, "_")[0]
	// Find the type of the field in the schema
	currentType := s.schema.Types[strcase.ToCamel(inflection.Singular(splitName))]
	args := field.ArgumentMap(s.variables)
	// Check if beforeClauses hook was set, if so call it
	if s.config.BeforeTranslation != nil {
		log.Trace().Msg("Called before clauses hook")
		s.config.BeforeTranslation(s.ctx, currentType, args)
	}
	tableName := strcase.ToSnake(splitName)
	queryAgg := sq.StatementBuilder.PlaceholderFormat(sq.Question).Select()
	query := sq.StatementBuilder.PlaceholderFormat(sq.Question).Select()

	abbrTableName := s.config.GenerateTableName(4)
	queryAgg = queryAgg.From(fmt.Sprintf("%s AS %s", tableName, abbrTableName))
	// Check if distinct was used, if it was used we want to add ordering and pagination in outer query
	if argument := field.Arguments.ForName(sqlgen.DistinctOnClause); argument != nil {
		value, _ := argument.Value.Value(s.variables)
		distinctBy := internal.SnakeCaseAll(cast.ToStringSlice(value))
		queryAgg = queryAgg.Options(fmt.Sprintf("DISTINCT ON (%s)", strings.Join(distinctBy, ",")))
		queryAgg = queryAgg.GroupBy(distinctBy...).Columns(fmt.Sprintf("ARRAY[%s]::text[] as distinct", strings.Join(distinctBy, ",")))
	}
	if argument := field.Arguments.ForName(sqlgen.GroupByClause); argument != nil {
		value, _ := argument.Value.Value(s.variables)
		groupBy := internal.SnakeCaseAll(cast.ToStringSlice(value))
		for _, g := range groupBy {
			queryAgg = queryAgg.Column(fmt.Sprintf("%s.%s", abbrTableName, g))
		}
		// Add group by clause
		queryAgg = queryAgg.GroupBy(groupBy...).Column(fmt.Sprintf("ARRAY[%s]::text[] as group", strings.Join(groupBy, ",")))
		query = query.Column(fmt.Sprintf("%s.group", abbrTableName))
	}
	// wrap inner query with outer query
	fields, _ := s.collectAggregateFields(abbrTableName, field, field.SelectionSet)
	// go over collected fields and build the SQL query
	for _, f := range fields {
		s.log.Trace().Str("field", f.Name).Str("type", string(f.Type)).Msg("Adding field to query")
		switch f.Type {
		case AggregateSelect:
			query = query.Column(f.Column).JoinClause(f.Sql)
		case AggregateFunction:
			queryAgg = queryAgg.Column(f.Column)
			query = query.Column(sq.Alias(sq.Expr(fmt.Sprintf("%s.%s", abbrTableName, f.Name)), f.Name))
		}
	}
	queryAgg = s.addWhereClause(queryAgg, args, currentType, abbrTableName)
	query = query.FromSelect(queryAgg, abbrTableName)
	query = s.addOrderingClause(s.addPaginationClauses(query, args), args)
	return query, abbrTableName
}

// buildSqlField builds an sqlField based on the given ast.Field
func (s translator) buildSqlFields(tableName string, parentDefinition *ast.Definition, field *ast.Field) ([]sqlField, error) {

	// skip any fields that start with _ as they are private and shouldn't be added to the SQL query
	if strings.HasPrefix(field.Name, "_") {
		return nil, nil
	}
	// get the definition of the selection from the schema
	selDefinition := s.getDefinition(field)
	if selDefinition == nil {
		s.log.Error().Err(ErrFieldMissingDefinition).Str("field", field.Name)
		return nil, ErrFieldMissingDefinition
	}
	s.log.Trace().Str("field", field.Name).Str("definition", string(selDefinition.Kind)).Msg("Collecting field")
	columnName := fmt.Sprintf("%s.%s", tableName, strcase.ToSnake(field.Name))
	if selDefinition.IsLeafType() {
		return []sqlField{{
			Name:   field.Name,
			Type:   Column,
			Sql:    sq.SelectBuilder{},
			Column: sq.Alias(sq.Expr(columnName), strcase.ToSnake(field.Name)),
		}}, nil
	}
	// if selection is not a composite type we are in a problem
	if !selDefinition.IsCompositeType() {
		s.log.Error().Err(ErrFieldTranslationFailed).Str("field", field.Name).Msg("not composite type")
		return nil, ErrFieldTranslationFailed
	}
	selFieldDefinition := parentDefinition.Fields.ForName(field.Name)
	sqlType := getSqlType(selFieldDefinition)
	s.log.Trace().Str("field", field.Name).Str("type", string(sqlType)).Msg("Parsing sql type")

	if selDefinition.Kind == ast.Object {
		switch sqlType {
		case Json:
			return []sqlField{s.buildJson(field, tableName, strcase.ToSnake(field.Name))}, nil
		case Relation:
			return []sqlField{s.buildRelation(tableName, selDefinition, field, getFieldRelationDirective(selFieldDefinition))}, nil
		case Aggregate:
			f, err := s.buildRelationAggregate(tableName, field, getFieldRelationDirective(selFieldDefinition))
			return []sqlField{f}, err
		case ViewFunction:
			return []sqlField{s.buildViewFunction(tableName, selDefinition, field, getFieldViewFunction(selFieldDefinition))}, nil
		default:
			return nil, ErrFieldTranslationFailed
		}
	}
	// selection isn't an Object so it's either a union or an interface, we support unions if they Jsons
	if selDefinition.Kind == ast.Union && sqlType == Json {
		jsonpath := getFieldJsonPathDirective(selFieldDefinition)
		// Add dependent fields, depends is usually used for identifying the type of the json
		var fields []sqlField
		for _, depends := range jsonpath.depends {
			fields = append(fields, sqlField{
				Name:   depends,
				Type:   Column,
				Sql:    sq.SelectBuilder{},
				Column: sq.Alias(sq.Expr(fmt.Sprintf("%s.%s", tableName, strcase.ToSnake(depends))), strcase.ToSnake(depends)),
			})
		}
		return append(fields, s.buildJson(field, tableName, strcase.ToSnake(jsonpath.name))), nil
	}
	s.log.Error().Err(ErrFieldTranslationFailed).Str("field", field.Name)
	return nil, ErrFieldTranslationFailed
}

// collectFields iterates over all selections and builds sql fields accordingly
func (s translator) collectFields(
	tableName string,
	field *ast.Definition,
	selections ast.SelectionSet) ([]sqlField, error) {

	fields := make([]sqlField, 0, len(selections))
	for _, sel := range selections {
		switch sel := sel.(type) {
		case *ast.Field:
			f, err := s.buildSqlFields(tableName, field, sel)
			if err != nil {
				return nil, err
			}
			fields = append(fields, f...)

		case *ast.InlineFragment:
			s.log.Trace().Str("fragment", sel.TypeCondition).Msg("opening inline fragment")
			selDefinition, ok := s.schema.Types[sel.ObjectDefinition.Name]
			if !ok {
				s.log.Error().Err(ErrFieldTranslationFailed).Str("field", sel.ObjectDefinition.Name).Msg("Failed to find fragment")
				return nil, ErrFieldTranslationFailed
			}
			s.log.Trace().Str("fragment", sel.ObjectDefinition.Name).Str("definition", string(selDefinition.Kind)).Msg("Collecting inline fragment fields")
			f, err := s.collectFields(tableName, selDefinition, sel.SelectionSet)
			if err != nil {
				return nil, err
			}
			fields = append(fields, f...)

		case *ast.FragmentSpread:
			fragment := s.fragments.ForName(sel.Name)
			selDefinition, ok := s.schema.Types[fragment.TypeCondition]
			if !ok {
				s.log.Error().Err(ErrFieldTranslationFailed).Str("field", sel.ObjectDefinition.Name).Msg("Failed to find fragment spread")
				return nil, ErrFieldTranslationFailed
			}
			s.log.Trace().Str("fragment", sel.Name).Str("definition", string(selDefinition.Kind)).Msg("Collecting fragment spread fields")
			f, err := s.collectFields(tableName, selDefinition, fragment.SelectionSet)
			if err != nil {
				return nil, err
			}
			fields = append(fields, f...)
		}
	}
	return fields, nil
}

func (s translator) buildRelationAggregate(parentTableName string, selection *ast.Field, relation relation) (sqlField, error) {
	currentType, ok := s.schema.Types[selection.Definition.Type.Name()]
	if !ok {
		return sqlField{}, errors2.Errorf("Failed to build aggregate for %s, didn't find type %s", selection.Name, selection.Definition.Type.Name())
	}
	aggQuery, aggTableName := s.buildAggregateQuery(selection)
	// Add relation clause to aggregate
	aggQuery = aggQuery.Where(relation.buildRelationClause(parentTableName, aggTableName))
	// Add where clauses into the aggregate query
	aggQuery = s.addWhereClause(aggQuery, selection.ArgumentMap(s.variables), currentType, aggTableName)
	// Wrap the inner aggregate query with an outer query
	abbrTableName := s.config.GenerateTableName(4)
	query := sq.StatementBuilder.PlaceholderFormat(sq.Question).Select().FromSelect(aggQuery, abbrTableName)
	snakeName := strcase.ToSnake(selection.Name)
	query = query.Column(sq.Alias(sq.Expr(fmt.Sprintf("jsonb_agg(row_to_json(%s))", abbrTableName)), snakeName))
	query = query.Prefix("CROSS JOIN LATERAL (").Suffix(") " + abbrTableName)
	return sqlField{
		Name:   selection.Name,
		Type:   Aggregate,
		Sql:    query,
		Column: sq.Alias(sq.Expr(snakeName), snakeName),
	}, nil
}

func (s translator) buildViewFunction(
	parentTableName string,
	selectionDefinition *ast.Definition,
	selection *ast.Field,
	vf viewFunction) sqlField {

	abbrTableName := s.config.GenerateTableName(4)
	query := sq.StatementBuilder.PlaceholderFormat(sq.Question).Select()
	query = query.From(fmt.Sprintf("%s AS %s", vf.buildFunctionClause(parentTableName), abbrTableName))
	fields, _ := s.collectFields(abbrTableName, selectionDefinition, selection.SelectionSet)
	var mappings []string
	for _, f := range fields {
		var columnName string
		switch f.Type {
		case Relation:
			// unlike in base translate when adding rel columns we would like it to be part of the json_object
			query = query.JoinClause(f.Sql)
			columnName = strcase.ToSnake(f.Name)
		case Column:
			columnName = fmt.Sprintf("%s.%s", abbrTableName, strcase.ToSnake(f.Name))
		case Json:
			columnName, _, _ = f.Column.ToSql()
		}
		mappings = append(mappings, fmt.Sprintf("'%s'", strcase.ToSnake(f.Name)), columnName)
	}
	query = query.Column(sq.Alias(sq.Expr(fmt.Sprintf("COALESCE(jsonb_agg(jsonb_build_object(%s)), '[]')", strings.Join(mappings, ","))), strcase.ToSnake(selection.Name)))
	query = s.addClauses(query, selection.ArgumentMap(s.variables), selectionDefinition, abbrTableName)
	query = query.Prefix("LEFT JOIN LATERAL (").Suffix(") " + abbrTableName + " ON True")
	// column name and alias should be snake
	snakeName := strcase.ToSnake(selection.Name)
	return sqlField{
		Name:   selection.Name,
		Type:   ViewFunction,
		Sql:    query,
		Column: sq.Alias(sq.Expr(snakeName), snakeName),
	}

}

func (s translator) buildRelation(
	parentTableName string,
	selectionDefinition *ast.Definition,
	selection *ast.Field,
	rel relation) sqlField {

	s.log.Trace().Str("relation", rel.Name).Str("parent", parentTableName).Msg("building relation")
	abbrTableName := s.config.GenerateTableName(4)
	query := sq.StatementBuilder.PlaceholderFormat(sq.Question).Select().From(fmt.Sprintf("%s AS %s", rel.Name, abbrTableName))
	fields, _ := s.collectFields(abbrTableName, selectionDefinition, selection.SelectionSet)
	var mappings []string
	for _, f := range fields {
		var columnName string
		switch f.Type {
		case Relation:
			// unlike in base translate when adding rel columns we would like it to be part of the json_object
			query = query.JoinClause(f.Sql)
			columnName = strcase.ToSnake(f.Name)
		case Column:
			columnName = fmt.Sprintf("%s.%s", abbrTableName, strcase.ToSnake(f.Name))
		case Json:
			columnName, _, _ = f.Column.ToSql()
		}
		mappings = append(mappings, fmt.Sprintf("'%s'", strcase.ToSnake(f.Name)), columnName)
	}

	var buildObj string
	switch rel.relType {
	case sqlgen.OneToOne:
		buildObj = fmt.Sprintf("jsonb_build_object(%s)", strings.Join(mappings, ","))
	case sqlgen.OneToMany:
		buildObj = fmt.Sprintf("COALESCE(jsonb_agg(jsonb_build_object(%s)), '[]')", strings.Join(mappings, ","))
	case sqlgen.ManyToMany:
		buildObj = fmt.Sprintf("COALESCE(jsonb_agg(jsonb_build_object(%s)), '[]')", strings.Join(mappings, ","))
		m2mAbbrTableName := s.config.GenerateTableName(5)
		joinOn := make([]string, len(rel.joinOn))
		for i, on := range rel.joinOn {
			joinOn[i] = fmt.Sprintf("%[1]s.%[3]s = %[2]s.%[3]s", abbrTableName, m2mAbbrTableName, on)
		}
		query = query.LeftJoin(fmt.Sprintf("%s %s ON (%s) ",
			rel.manyToManyTable,
			abbrTableName,
			strings.Join(joinOn, " AND "),
		))
		m2mAbbrTableName, abbrTableName = abbrTableName, m2mAbbrTableName
		// Change from table name because mapping will use the m2mAbbrTableName
		query = query.From(fmt.Sprintf("%s AS %s", rel.Name, abbrTableName))
	default:
		buildObj = fmt.Sprintf("jsonb_build_object(%s)", strings.Join(mappings, ","))
	}
	// Add json object we built for relation as the main column of this query
	query = query.Column(sq.Alias(sq.Expr(buildObj), strcase.ToSnake(selection.Name)))
	// Add relation clause based on data given in the directive
	query = query.Where(rel.buildRelationClause(parentTableName, abbrTableName))

	query = s.addClauses(query, selection.ArgumentMap(s.variables), selectionDefinition, abbrTableName)
	query = query.Prefix("LEFT JOIN LATERAL (").Suffix(") " + abbrTableName + " ON True")
	// column name and alias should be snake
	snakeName := strcase.ToSnake(selection.Name)
	return sqlField{
		Name:   selection.Name,
		Type:   Relation,
		Sql:    query,
		Column: sq.Alias(sq.Expr(snakeName), snakeName),
	}
}

func (s translator) buildJson(parentSelection *ast.Field, abbrTableName, fieldName string) sqlField {
	mappings := s.buildJsonMapping(parentSelection, abbrTableName, fieldName)
	return sqlField{
		Name:   fieldName,
		Type:   Json,
		Sql:    sq.SelectBuilder{},
		Column: sq.Expr(fmt.Sprintf("jsonb_build_object(%s)", strings.Join(mappings, ","))),
	}
}

func (s translator) buildJsonMapping(parentSelection *ast.Field, abbrTableName string, fieldName string) []string {
	var mappings []string
	for _, selection := range parentSelection.SelectionSet {
		switch selection := selection.(type) {
		case *ast.Field:
			if selection.SelectionSet != nil {
				mappings = append(mappings, strcase.ToSnake(selection.Name))
				mappings = append(mappings, s.buildJsonMapping(selection, abbrTableName, fieldName)...)
			} else {
				mappings = append(mappings, strcase.ToSnake(selection.Name),
					fmt.Sprintf("%s->'%s'", fieldName, strcase.ToSnake(selection.Name)))
			}
		case *ast.FragmentSpread:
			fragmentSpread := s.fragments.ForName(selection.Name)
			for _, fragmentSelection := range fragmentSpread.SelectionSet {
				switch fragmentSelection := fragmentSelection.(type) {
				case *ast.Field:
					if fragmentSelection.SelectionSet != nil {
						mappings = append(mappings, fmt.Sprintf("'%s'", strcase.ToSnake(fragmentSelection.Name)))
						mappings = append(mappings, s.buildJsonMapping(fragmentSelection, abbrTableName, fieldName)...)
					} else {
						mappings = append(mappings, fmt.Sprintf(
							"'%s', %s.%s->'%s'",
							strcase.ToSnake(fragmentSelection.Name),
							abbrTableName,
							fieldName,
							strcase.ToSnake(fragmentSelection.Name)))
					}
				}
			}
		case *ast.InlineFragment:
			for _, fragmentSelection := range selection.SelectionSet {
				switch fragmentSelection := fragmentSelection.(type) {
				case *ast.Field:
					mappings = append(mappings, fmt.Sprintf(
						"'%s', %s.%s->'%s'",
						strcase.ToSnake(fragmentSelection.Name),
						abbrTableName,
						fieldName,
						strcase.ToSnake(fragmentSelection.Name)))
				}
			}
		}
	}
	return mappings
}

// addClauses is a syntactic sugar function for adding all clauses in 1 line, if you need more fine grained control use each function separately
func (s translator) addClauses(q sq.SelectBuilder, args map[string]interface{}, currentType *ast.Definition, abbrTableName string) sq.SelectBuilder {
	return s.addOrderingClause(s.addPaginationClauses(s.addWhereClause(q, args, currentType, abbrTableName), args), args)
}

func (s translator) addWhereClause(q sq.SelectBuilder, args map[string]interface{}, currentType *ast.Definition, abbrTableName string) sq.SelectBuilder {
	// Allow hook before clauses are added
	if s.config.BeforeClauses != nil {
		s.config.BeforeClauses(s.ctx, abbrTableName, currentType, args)
	}
	if where, ok := args[sqlgen.WhereClause]; ok {
		if whereMap, ok := where.(map[string]interface{}); ok {
			conditions := s.createConditions(whereMap, currentType, abbrTableName)
			if len(conditions) > 0 {
				q = q.Where(sq.And(conditions))
			}
		}
	}
	return q
}

func (s translator) addOrderingClause(q sq.SelectBuilder, args map[string]interface{}) sq.SelectBuilder {
	if orderBy, ok := args[sqlgen.OrderByClause]; ok {
		s.log.Trace().Interface(sqlgen.OrderByClause, orderBy).Msg("adding order by")
		if orderByArray, ok := orderBy.([]interface{}); ok {
			var orderClauses []string
			for _, clause := range orderByArray {
				orderClauses = append(orderClauses, sqlgen.GetOrderOperation(clause.(string)))
			}
			q = q.OrderBy(orderClauses...)
		} else if orderBySingle, ok := orderBy.(string); ok {
			q = q.OrderBy(sqlgen.GetOrderOperation(orderBySingle))
		}
	}
	return q
}

func (s translator) addPaginationClauses(query sq.SelectBuilder, args map[string]interface{}) sq.SelectBuilder {
	if offset, ok := args[sqlgen.OffsetClause]; ok && !reflect2.IsNil(offset) {
		s.log.Trace().Interface("offset", offset).Msg("adding offset")
		o, err := strconv.Atoi(cast.ToString(offset))
		if err != nil {
			o = 0
		}
		query = query.Offset(uint64(o))
	}
	if limit, ok := args[sqlgen.LimitClause]; ok && !reflect2.IsNil(limit) {
		s.log.Trace().Interface("limit", limit).Msg("adding limit")
		l, err := strconv.Atoi(cast.ToString(limit))
		if err != nil {
			l = 100
		}
		query = query.Limit(uint64(l))
	} else {
		query = query.Limit(100)
	}
	return query
}

func (s translator) createConditions(
	where map[string]interface{},
	currentType *ast.Definition,
	abbrTableName string) []sq.Sqlizer {

	var cond []sq.Sqlizer
	for k, v := range where {
		name, cmp := sqlgen.GetComparisonOperation(k)
		// Use dot notated name
		columnName := fmt.Sprintf("%s.%s", abbrTableName, name)
		s.log.Trace().Str("cmp", cmp).Str("name", name).Interface("value", v).Msg("adding condition")
		switch cmp {
		case sqlgen.OperationExpr:
			cond = append(cond, sq.Expr(fmt.Sprintf("%s %s", columnName, v)))
		case sqlgen.OperationExists:
			if cast.ToBool(v) {
				cond = append(cond, sq.Expr(fmt.Sprintf("%s IS NOT NULL", columnName)))
			} else {
				cond = append(cond, sq.Expr(fmt.Sprintf("%s IS NULL", columnName)))
			}
		case sqlgen.OperationNotEq:
			cond = append(cond, sq.NotEq{columnName: v})
		case sqlgen.OperationEq:
			cond = append(cond, sq.Eq{columnName: v})
		case sqlgen.OperationGt:
			cond = append(cond, sq.Gt{columnName: v})
		case sqlgen.OperationGte:
			cond = append(cond, sq.GtOrEq{columnName: v})
		case sqlgen.OperationLt:
			cond = append(cond, sq.Lt{columnName: v})
		case sqlgen.OperationLte:
			cond = append(cond, sq.LtOrEq{columnName: v})
		case sqlgen.OperationPrefix:
			cond = append(cond, sq.Like{columnName: fmt.Sprintf("%s%%", v)})
		case sqlgen.OperationSuffix:
			cond = append(cond, sq.Like{columnName: fmt.Sprintf("%%%s", v)})
		case sqlgen.OperationLike:
			cond = append(cond, sq.Like{columnName: v})
		case sqlgen.OperationNotLike:
			cond = append(cond, sq.NotLike{columnName: v})
		case sqlgen.OperationILike:
			cond = append(cond, sq.ILike{columnName: v})
		case sqlgen.OperationNotILike:
			cond = append(cond, sq.NotILike{columnName: v})
		case sqlgen.OperationIn:
			cond = append(cond, sq.Expr(fmt.Sprintf("%s =  ANY(?)", columnName), AnySlice{cast.ToSlice(v)}))
		case sqlgen.OperationNotIn:
			cond = append(cond, sq.Expr(fmt.Sprintf("%s =  ANY(?)", columnName), AnySlice{cast.ToSlice(v)}))
		case sqlgen.OperationContains:
			cond = append(cond, sq.Expr(fmt.Sprintf("%s @> ?", columnName), AnySlice{cast.ToSlice(v)}))
		case sqlgen.OperationContainedBy:
			cond = append(cond, sq.Expr(fmt.Sprintf("%s <@ ?", columnName), AnySlice{cast.ToSlice(v)}))
		case sqlgen.OperationOverlap:
			cond = append(cond, sq.Expr(fmt.Sprintf("%s && ?", columnName), AnySlice{cast.ToSlice(v)}))
		case sqlgen.OperationContainsRegex:
			cond = append(cond, sq.Like{fmt.Sprintf("arrayToText(%s)", columnName): fmt.Sprintf("%s", v)})
		case sqlgen.OperationInSubnet:
			_, ip, err := net.ParseCIDR(cast.ToString(v))
			if err != nil {
				log.Err(err).Interface("cidr", v).Msg("Failed to parse cidr")
			}
			cond = append(cond, sq.Expr(fmt.Sprintf("? >> any(%s)", columnName), ip))
		case sqlgen.OperationIPFamily:
			// This assumes family(inet[]) function exists, see functions.sql
			cond = append(cond, sq.Expr(fmt.Sprintf("? = any(family(%s))", columnName), cast.ToString(v)[1:]))
		case sqlgen.OperationDays:
			cond = append(cond, sq.Expr(fmt.Sprintf("%s >= round(extract('epoch' from (Now() - ? * interval '1 days')) * 1000)::bigint", columnName), v))
		case sqlgen.OperationLogicOr:
			v, ok := v.([]interface{})
			if !ok {
				return nil
			}
			cond = append(cond, sq.Or(s.createMultiConditions(v, currentType, abbrTableName)))
		case sqlgen.OperationLogicAnd:
			v, ok := v.([]interface{})
			if !ok {
				return nil
			}
			cond = append(cond, sq.And(s.createMultiConditions(v, currentType, abbrTableName)))
		case sqlgen.OperationLogicNot:
			v, ok := v.(map[string]interface{})
			if !ok {
				return nil
			}
			cond = append(cond, not(s.createConditions(v, currentType, abbrTableName)))
		case sqlgen.OperationBoolExp:
			v, ok := v.(map[string]interface{})
			if !ok {
				return nil
			}
			selectionDefinition := currentType.Fields.ForName(name)
			switch getSqlType(selectionDefinition) {
			case Json:
				directive := getFieldJsonPathDirective(selectionDefinition)
				expr, vars := createJsonPathCondition(directive.name, v)
				cond = append(cond, sq.Expr(expr, vars...))
			case Relation:
				cond = append(cond, s.createRelationCondition(v, getFieldRelationDirective(selectionDefinition), abbrTableName))
			}
		}
	}
	return cond
}

func (s translator) createRelationCondition(
	v map[string]interface{},
	rel relation,
	parentTableName string) sq.Sqlizer {

	abbrTableName := s.config.GenerateTableName(5)
	query := sq.StatementBuilder.PlaceholderFormat(sq.Question).Select()
	query = query.From(fmt.Sprintf("%s AS %s", rel.Name, abbrTableName)).Limit(1)
	query = query.Prefix("EXISTS (").Suffix(")")
	query = query.Column(sq.Expr("1"))
	query = query.Where(rel.buildRelationClause(parentTableName, abbrTableName))
	relType, ok := s.schema.Types[rel.NamedType]
	if !ok {
		return query
	}
	return s.addWhereClause(query, map[string]interface{}{sqlgen.WhereClause: v}, relType, abbrTableName)
}

func (s translator) createMultiConditions(
	whereClauses []interface{},
	currentType *ast.Definition,
	abbrTableName string) []sq.Sqlizer {
	var allClauses []sq.Sqlizer
	for _, where := range whereClauses {
		whereMap, ok := where.(map[string]interface{})
		if !ok {
			continue
		}
		allClauses = append(allClauses, sq.And(s.createConditions(whereMap, currentType, abbrTableName)))
	}
	return allClauses
}

func (s translator) getDefinition(selection *ast.Field) *ast.Definition {
	if selection.Definition.Type.NamedType == "" {
		return s.schema.Types[selection.Definition.Type.Elem.NamedType]
	}
	return s.schema.Types[selection.Definition.Type.NamedType]
}
