package augmentors

import (
	"bandicoot/internal"
	"bandicoot/internal/sqlgen"
	"fmt"
	"github.com/vektah/gqlparser/v2/ast"
	"strings"
)

var defaultActionTypes = []string{typeEpoch, typeInt, typeString, typeMacAddr, typeIP, typeUUID, typeFloat}

var aggFunctionTypes = map[string][]string{
	sqlgen.SumAggregate: {typeInt, typeFloat, typeEpoch},
	sqlgen.AverageAggregate: {typeInt, typeFloat, typeEpoch},
	sqlgen.MinAggregate: defaultActionTypes,
	sqlgen.MaxAggregate: defaultActionTypes,
	sqlgen.GroupByClause: defaultActionTypes,
}

type Aggregation struct{}

func (a Aggregation) Field(s *ast.Schema, field *ast.FieldDefinition, parent *ast.Definition) error {
	return nil
}

func (a Aggregation) Schema(s *ast.Schema) error {
	for _, t := range s.Types {
		// skip private types
		if strings.HasPrefix(t.Name, "__") {
			continue
		}
		for _, f := range t.Fields {
			if f.Type.Elem == nil {
				continue
			}

			if sqlGenSkip(f) {
				continue
			}
				aggregateArgs := buildArguments(s, f)
			if aggregateArgs == nil {
				continue
			}

			aggName := buildAggregate(s, f)
			t.Fields = append(t.Fields, &ast.FieldDefinition{
				Description: fmt.Sprintf("Returns aggregate of %s", f.Name),
				Name:        fmt.Sprintf("%s_aggregate", f.Name),
				Type:        &ast.Type{NamedType: "", Elem: &ast.Type{NamedType: aggName, NonNull: true}},
				Directives:  f.Directives,
				Arguments:   aggregateArgs,
			})

		}
	}
	return nil
}

func buildAggregate(s *ast.Schema, f *ast.FieldDefinition) string {
	aggregateInterface := s.Types["Aggregate"]
	aggName := fmt.Sprintf("%sAggregate", f.Name)
	aggDef := &ast.Definition{
		Kind:   ast.Object,
		Name:   fmt.Sprintf("%sAggregate", f.Name),
		Fields: make(ast.FieldList, len(aggregateInterface.Fields)),
	}
	s.Types[aggName] = aggDef
	for i, af := range aggregateInterface.Fields {
		aggDef.Fields[i] = &ast.FieldDefinition{
			Type:         af.Type,
			Name:         af.Name,
			DefaultValue: af.DefaultValue,
			Description:  af.Description,
			Directives:   af.Directives,
		}
		allowedTypes, ok := aggFunctionTypes[af.Name]
		if !ok {
			continue
		}
		aggColumnsName := fmt.Sprintf("%s_aggregate_%s_columns", f.Name, af.Name)
		cols := aggregateColumns(af.Name, s.Types[sqlgen.GetNamedType(f)].Fields, allowedTypes)
		if cols == nil {
			continue
		}
		s.Types[aggColumnsName] = &ast.Definition{
			Kind:       ast.Enum,
			Name:       aggColumnsName,
			EnumValues: cols,
		}
		aggDef.Fields[i].Arguments = ast.ArgumentDefinitionList{
			{
				Description: "Aggregate functions compute a single result value from a set of input values",
				Name:        "column",
				Type:        &ast.Type{NamedType: "", Elem: &ast.Type{NamedType: aggColumnsName, NonNull: true}, NonNull: true},
			},
		}
	}
	aggDef.Fields = append(aggDef.Fields, &ast.FieldDefinition{
		Description:  f.Description,
		Name:         f.Name,
		Arguments:    f.Arguments,
		DefaultValue: f.DefaultValue,
		Type:         &ast.Type{
			NamedType: "",
			Elem:      &ast.Type{
				NamedType: f.Type.Name(),
				Elem:      nil,
				NonNull:   false,
				Position:  nil,
			},
			NonNull:   false,
			Position:  nil,
		},
		Directives:   f.Directives,
		Position:     nil,
	})

	return aggName
}

// buildArguments add aggregation arguments to the field such as groupBy, Distinct and Ordering
func buildArguments(s *ast.Schema, f *ast.FieldDefinition) ast.ArgumentDefinitionList {

	typ, ok := s.Types[f.Type.Elem.NamedType]
	if !ok {
		fmt.Printf("failed to find type %s", f.Type.Elem.NamedType)
		return nil
	}

	// Aggregation is only allowed on composite types and jsonpath isn't supported!
	if !typ.IsCompositeType() || f.Directives.ForName(sqlgen.DirectiveJsonPath) != nil {
		return nil
	}

	allowedTypes, ok := aggFunctionTypes[sqlgen.GroupByClause]
	if !ok {
		return nil
	}
	aggregateColumnsDef := aggregateColumns(sqlgen.GroupByClause, s.Types[sqlgen.GetNamedType(f)].Fields, allowedTypes)
	if aggregateColumnsDef == nil {
		return nil
	}

	aggColumnsName := fmt.Sprintf("%s_aggregate_columns", f.Name)
	s.Types[aggColumnsName] = &ast.Definition{
		Kind:       ast.Enum,
		Name:       aggColumnsName,
		EnumValues: aggregateColumnsDef,
	}
	aggregateArgs := ast.ArgumentDefinitionList{
		{
			Description: "group by columns",
			Name:        sqlgen.GroupByClause,
			Type:        &ast.Type{NamedType: "", Elem: &ast.Type{NamedType: aggColumnsName, NonNull: true}, NonNull: false},
		},
		{
			Description: "distinct on columns",
			Name:        sqlgen.DistinctOnClause,
			Type:        &ast.Type{NamedType: "", Elem: &ast.Type{NamedType: aggColumnsName, NonNull: true}, NonNull: false},
		},
		{
			Description: "order by aggregation columns",
			Name:        sqlgen.OrderByClause,
			Type:        &ast.Type{NamedType: "", Elem: &ast.Type{NamedType: "AggregateOrdering", NonNull: true}, NonNull: false},
		},
	}
	return aggregateArgs
}

// aggregateColumns builds an enum of available aggregate columns based on the aggregate name
func aggregateColumns(aggregateName string, fields ast.FieldList, allowedTypes []string) []*ast.EnumValueDefinition {
	var enumFields []*ast.EnumValueDefinition
	for _, f := range fields {
		if !internal.StringInSlice(f.Type.NamedType, allowedTypes) {
			continue
		}
		enumFields = append(enumFields, &ast.EnumValueDefinition{
			Description: fmt.Sprintf("%s by %s", aggregateName, f.Name),
			Name: f.Name})
	}
	return enumFields
}
