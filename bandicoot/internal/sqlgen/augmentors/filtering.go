package augmentors

import (
	"bandicoot/internal/sqlgen"
	"errors"
	"fmt"
	"github.com/iancoleman/strcase"
	"github.com/vektah/gqlparser/v2/ast"
	"log"
	"strings"
)

type Filters struct{}

func (f Filters) Field(s *ast.Schema, d *ast.FieldDefinition, parent *ast.Definition) error {
	namedType := getNamedType(d)
	//
	if strings.HasSuffix(namedType, "Aggregate") {
		brotherField := parent.Fields.ForName(strings.TrimSuffix(d.Name, "_aggregate"))
		namedType = getNamedType(brotherField)
	} else {
		// Get inner element type
		def := s.Types[namedType]
		if !def.IsCompositeType() {
			return nil
		}
	}

	d.Arguments = append(d.Arguments, &ast.ArgumentDefinition{
		Description: "filter the rows returned",
		Name:        sqlgen.WhereClause,
		Type:        &ast.Type{NamedType: fmt.Sprintf("%s_bool_exp", strcase.ToSnake(namedType)), NonNull: false},
	})
	return nil
}

func (f Filters) Schema(s *ast.Schema) error {
	boolExpressions := make(map[string]*ast.Definition)
	for _, t := range s.Types {
		tc, err := newTypeConfig(t)
		if err != nil {
			log.Fatal(err)
		}
		// no directive
		if tc == nil {
			continue
		}
		def := &ast.Definition{
			Kind:        ast.InputObject,
			Description: fmt.Sprintf("Boolean filter expression for %s", t.Name),
			Name:        tc.Where,
		}
		// Add to our boolExpressions so we can add fields later
		boolExpressions[t.Name] = def
		// We initially want to add all the bool expressions since they might point at one another recursively
		s.Types[tc.Where] = def
	}
	for typeName, boolExp := range boolExpressions {

		t, ok := s.Types[typeName]
		if !ok {
			log.Fatal("Failed to find type")
		}
		if t.Kind == ast.Union {
			for _, unionTypes := range t.Types {
				unionType := s.Types[unionTypes]
				for _, f := range unionType.Fields {
					wf, err := whereFields(f, boolExpressions, s)
					if err != nil {
						log.Fatal("Failed to build where fields")
					}
					boolExp.Fields = append(boolExp.Fields, wf...)
				}
			}
		} else {
			// Add each fields expressions to the boolExp
			for _, f := range t.Fields {
				wf, err := whereFields(f, boolExpressions, s)
				if err != nil {
					log.Fatal("Failed to build where fields")
				}
				boolExp.Fields = append(boolExp.Fields, wf...)
			}
		}

		// Finally add the logical expressions AND, OR, NOT
		for _, op := range []string{sqlgen.OperationLogicAnd, sqlgen.OperationLogicOr, sqlgen.OperationLogicNot} {
			boolExp.Fields = append(boolExp.Fields, &ast.FieldDefinition{
				Name: op,
				Type: &ast.Type{
					NamedType: "",
					Elem:      &ast.Type{NamedType: boolExp.Name, NonNull: true},
					NonNull:   false,
				},
			})
		}
	}
	return nil
}

// whereArrayField builds a where input for array types
func whereArrayField(field *ast.FieldDefinition, expMap map[string]*ast.Definition, _ *ast.Schema) ([]*ast.FieldDefinition, error) {
	namedType := getNamedType(field)
	switch namedType {
	case typeString:
		return expandWhereField(
			field.Name,
			fmt.Sprintf("[%s]", field.Type.Elem.NamedType),
			sqlgen.OperationContains,
			sqlgen.OperationContainedBy,
			sqlgen.OperationOverlap,
			sqlgen.OperationSize,
			sqlgen.OperationContainsRegex,
		), nil
	case typeInt, typeBoolean:
		return expandWhereField(
			field.Name,
			fmt.Sprintf("[%s]", field.Type.Elem.NamedType),
			sqlgen.OperationContains,
			sqlgen.OperationContainedBy,
			sqlgen.OperationOverlap,
			sqlgen.OperationSize,
		), nil
	case typeIP:
		return expandWhereField(
			field.Name,
			fmt.Sprintf("[%s]", field.Type.Elem.NamedType),
			sqlgen.OperationContains,
			sqlgen.OperationContainedBy,
			sqlgen.OperationOverlap,
			sqlgen.OperationSize,
			sqlgen.OperationInSubnet,
			sqlgen.OperationIPFamily,
		), nil
	default:
		if t, ok := expMap[namedType]; ok {
			return []*ast.FieldDefinition{
				{
					Description: fmt.Sprintf("filter by %s", field.Name),
					Name:        field.Name,
					Type: &ast.Type{
						NamedType: t.Name,
					},
				},
			}, nil
		}
		log.Printf("Unknown array type found %s", namedType)
		return nil, errors.New("unknown type")
	}
}

// whereFields builds a where input for types, if the field is an array will use whereArrayField instead.
func whereFields(field *ast.FieldDefinition, expMap map[string]*ast.Definition, s *ast.Schema) ([]*ast.FieldDefinition, error) {
	// check if field is a list
	if field.Type.Elem != nil {
		return whereArrayField(field, expMap, s)
	}
	namedType := getNamedType(field)
	switch namedType {
	case typeID, typeInt, typeFloat, typeUUID:
		return expandWhereField(
			field.Name,
			namedType,
			sqlgen.OperationExists,
			sqlgen.OperationEq,
			sqlgen.OperationNotEq,
			sqlgen.OperationIn,
			sqlgen.OperationNotIn,
			sqlgen.OperationGt,
			sqlgen.OperationGte,
			sqlgen.OperationLt,
			sqlgen.OperationLte,
		), nil
	case typeEpoch, typeDateTime, typeNullDateTime:
		return expandWhereField(
			field.Name,
			namedType,
			sqlgen.OperationExists,
			sqlgen.OperationEq,
			sqlgen.OperationNotEq,
			sqlgen.OperationIn,
			sqlgen.OperationNotIn,
			sqlgen.OperationGt,
			sqlgen.OperationGte,
			sqlgen.OperationLt,
			sqlgen.OperationLte,
			sqlgen.OperationDays,
		), nil
	case typeString:
		return expandWhereField(
			field.Name,
			namedType,
			sqlgen.OperationExists,
			sqlgen.OperationNot,
			sqlgen.OperationEq,
			sqlgen.OperationNotEq,
			sqlgen.OperationIn,
			sqlgen.OperationNotIn,
			sqlgen.OperationLike,
			sqlgen.OperationNotLike,
			sqlgen.OperationILike,
			sqlgen.OperationNotILike,
			sqlgen.OperationSuffix,
			sqlgen.OperationPrefix,
		), nil
	case typeBoolean:
		return expandWhereField(
			field.Name,
			namedType,
			sqlgen.OperationExists,
			sqlgen.OperationEq,
			sqlgen.OperationNotEq,
		), nil
	case typeMacAddr:
		return expandWhereField(
			field.Name,
			namedType,
			sqlgen.OperationExists,
			sqlgen.OperationEq,
			sqlgen.OperationNotEq,
			sqlgen.OperationIn,
			sqlgen.OperationNotIn,
		), nil
	default:
		if t, ok := expMap[namedType]; ok {
			return []*ast.FieldDefinition{
				{
					Description: fmt.Sprintf("filter by %s", field.Name),
					Name:        field.Name,
					Type: &ast.Type{
						NamedType: t.Name,
					},
				},
			}, nil
		}
		if k, ok := s.Types[namedType]; ok && k.Kind == ast.Enum {
			return expandWhereField(
				field.Name,
				namedType,
				sqlgen.OperationEq,
				sqlgen.OperationNotEq,
				sqlgen.OperationIn,
				sqlgen.OperationNotIn,
			), nil
		}
		log.Printf("Unknown type found %s for field %s", namedType, field.Name)
		return nil, nil
	}
}

func expandWhereField(field, typeName string, ops ...string) []*ast.FieldDefinition {
	fields := make([]*ast.FieldDefinition, 0, len(ops)+1)
	for _, o := range ops {

		f := ast.FieldDefinition{
			Description: fmt.Sprintf("%s comparison operator", o),
			Name:        fmt.Sprintf("%s_%s", field, o),
			Type:        &ast.Type{NamedType: typeName, NonNull: false},
		}
		// handle lists
		switch o {
		case sqlgen.OperationContainsRegex:
			f.Type = &ast.Type{NamedType: "String", NonNull: false}
		case sqlgen.OperationDays, sqlgen.OperationSize:
			f.Type = &ast.Type{NamedType: "Int", NonNull: false}
		case sqlgen.OperationIn, sqlgen.OperationNotIn:
			f.Type.NamedType = ""
			f.Type.Elem = &ast.Type{NamedType: typeName, NonNull: false}
		case sqlgen.OperationInSubnet:
			f.Type = &ast.Type{NamedType: "CIDR", NonNull: false}
		case sqlgen.OperationIPFamily:
			f.Type = &ast.Type{NamedType: "IPFamily", NonNull: false}
		// Handle null
		case sqlgen.OperationExists:
			f.Type = &ast.Type{NamedType: "Boolean", NonNull: false}
		}
		fields = append(fields, &f)
	}
	return fields
}
