package sql

import (
	"bandicoot/internal"
	"bandicoot/internal/sqlgen"
	"errors"
	"fmt"
	sq "github.com/Masterminds/squirrel"
	"github.com/iancoleman/strcase"
	"github.com/spf13/cast"
	"github.com/vektah/gqlparser/v2/ast"
	"strings"
)

func (s translator) collectAggregateFields(
	tableName string,
	parentField *ast.Field,
	selections ast.SelectionSet) ([]sqlField, error) {

	fields := make([]sqlField, 0, len(selections))
	for _, sel := range selections {
		switch sel := sel.(type) {
		case *ast.Field:
			// skip any fields that start with _ as they are private and shouldn't be added to the SQL query
			if strings.HasPrefix(sel.Name, "_") {
				continue
			}
			switch sel.Name {
			case sqlgen.SumAggregate, sqlgen.AverageAggregate, sqlgen.MinAggregate, sqlgen.MaxAggregate:
				argument := sel.Arguments.ForName("column")
				value, _ := argument.Value.Value(s.variables)
				sumBy := internal.SnakeCaseAll(cast.ToStringSlice(value))
				var sums []string
				for _, s := range sumBy {
					sums = append(sums, fmt.Sprintf("'%s'", strcase.ToSnake(s)), fmt.Sprintf("%s(%s.%s)", sel.Name, tableName, strcase.ToSnake(s)))
				}
				fields = append(fields, sqlField{
					Name:   sel.Name,
					Type:   AggregateFunction,
					Sql:    sq.SelectBuilder{},
					Column: sq.Alias(sq.Expr(fmt.Sprintf("jsonb_build_object(%s)", strings.Join(sums, ","))), strcase.ToSnake(sel.Name)),
				})
			case sqlgen.CountAggregate:
				fields = append(fields, sqlField{
					Name:   sel.Name,
					Type:   AggregateFunction,
					Sql:    sq.SelectBuilder{},
					Column: sq.Alias(sq.Expr("Count(*)"), strcase.ToSnake(sel.Name)),
				})
			case strings.TrimSuffix(parentField.Name, "_aggregate"):
				// TODO: make this more readable you git
				selDef, ok := s.schema.Types[sel.Definition.Type.Name()]
				if !ok {
					continue
				}
				var groupBy []string
				v := parentField.Arguments.ForName(sqlgen.GroupByClause)
				if v != nil {
					iv, _ := v.Value.Value(s.variables)
					groupBy = cast.ToStringSlice(iv)
				}
				arg := parentField.Arguments.ForName(sqlgen.WhereClause)
				if arg != nil {
					sel.Arguments = append(sel.Arguments, arg)
				}
				f, _ := s.buildAggregateSelect(tableName, selDef, sel, groupBy)
				fields = append(fields, f)
			}
		default:
			s.log.Err(errors.New("only common fields are allowed, no inline / fragments"))
		}
	}
	return fields, nil
}


func (s translator) buildAggregateSelect(parentTableName string, selectionDef *ast.Definition, selection *ast.Field, groupBy []string) (sqlField, error) {
	rel := relation{
		NamedType:       "",
		Name:            strcase.ToSnake(selection.Name),
		fkNames:         groupBy,
		relationFkNames: groupBy,
		relType:         sqlgen.OneToMany,
		manyToManyTable: "",
		joinOn:          nil,
	}
	query := s.buildRelation(parentTableName, selectionDef, selection, rel)
	return sqlField{
		Name:   selection.Name,
		Type:   AggregateSelect,
		Sql:    query.Sql,
		Column: query.Column,
	}, nil
}