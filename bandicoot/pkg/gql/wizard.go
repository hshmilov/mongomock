package gql

import (
	"bandicoot/internal/sqlgen"
	"context"
	"errors"
	"fmt"
	"github.com/iancoleman/strcase"
	"github.com/rs/zerolog/log"
	"github.com/vektah/gqlparser/v2/ast"
	"strings"
)

func (r *queryResolver) WizardFilters(ctx context.Context, typeArg string) (*ObjectFilter, error) {

	inputObject, ok := parsedSchema.Types[fmt.Sprintf("%s_%s", typeArg, sqlgen.OperationBoolExp)]
	if !ok {
		return nil, errors.New(fmt.Sprintf("type input %s not found", typeArg))
	}
	object, ok := parsedSchema.Types[strcase.ToCamel(typeArg)]
	if !ok {
		return nil, errors.New(fmt.Sprintf("type %s not found", typeArg))
	}
	of := buildObjectFilter(parsedSchema, typeArg, object, inputObject)
	return &of, nil
}


func buildScalarFilter(fieldDef *ast.FieldDefinition, objDef, inputDef *ast.Definition) ScalarFilter {

	sFilter := ScalarFilter{
		Name:        fieldDef.Name,
		DisplayName: strcase.ToDelimited(fieldDef.Name,' '),
		Type:        string(objDef.Kind),
		Description: &fieldDef.Description,
		Operators:   make([]*Operator, len(inputDef.Fields)),
	}
	// iterate over all comparison filters
	for i, f := range inputDef.Fields {
		sFilter.Operators[i] = &Operator{
			Name: f.Name,
			Type: getTypeString(f.Type),
		}
	}
	return sFilter
}

func buildObjectFilter(s *ast.Schema, name string, objDef, inputDef *ast.Definition) ObjectFilter {
	obj := ObjectFilter{
		Name:        name,
		DisplayName: strcase.ToDelimited(name,' '),
		Type:        inputDef.Name,
		Description: &objDef.Description,
		Filters:     nil,
	}
	filters := make(map[string]Filter)
	for _, f := range inputDef.Fields {
		switch f.Name {
		case sqlgen.OperationLogicAnd, sqlgen.OperationLogicNot, sqlgen.OperationLogicOr:
			// We want a copy and not the actual object filter we are building in order to avoid
			// a recursive loop
			filters[f.Name] = ObjectFilter{
				Name:        f.Name,
				Type:        getTypeString(f.Type),
				Description: &f.Description,
				Filters:     nil,
			}
		default:
			innerFieldDef := objDef.Fields.ForName(f.Name)
			if innerFieldDef == nil  {
				log.Warn().Str("name", f.Name).Msg("Failed to find field type")
				continue
			}
			if strings.HasSuffix(f.Type.Name(), sqlgen.OperationBoolExp) {
				innerFieldObj := s.Types[sqlgen.GetNamedType(innerFieldDef)]
				if innerFieldObj.Kind != ast.Object {
					continue
				}
				filters[f.Name] = buildObjectFilter(s, f.Name, innerFieldObj, s.Types[f.Type.Name()])
			} else {
				filters[f.Name] = buildScalarFilter(innerFieldDef, s.Types[sqlgen.GetNamedType(innerFieldDef)], s.Types[f.Type.Name()])
			}
		}
	}
	obj.Filters = make([]Filter, len(filters))
	i := 0
	for _, v := range filters {
		obj.Filters [i] = v
		i++
	}
	return obj
}

func getTypeString(p *ast.Type) string {
	if p.Elem != nil {
		return fmt.Sprintf("[%s]",  p.Name())
	}
	return p.Name()
}