package augmentors

import (
	"bandicoot/internal/sqlgen"
	"fmt"
	"github.com/iancoleman/strcase"
	"github.com/vektah/gqlparser/v2/ast"
	"log"
	"strings"
)

type Filters struct{}

func (f Filters) Field(s *ast.Schema, d *ast.FieldDefinition, parent *ast.Definition) error {
	namedType := sqlgen.GetNamedType(d)
	//
	if strings.HasSuffix(namedType, "Aggregate") {
		brotherField := parent.Fields.ForName(strings.TrimSuffix(d.Name, "_aggregate"))
		namedType = sqlgen.GetNamedType(brotherField)
	} else {
		// Get inner element type
		def := s.Types[namedType]
		if !def.IsCompositeType() {
			return nil
		}
	}
	// Skip adding argument if input wasn't created
	filterInput := fmt.Sprintf("%s_bool_exp", strcase.ToSnake(namedType))
	if _, ok := s.Types[filterInput]; !ok {
		log.Printf("Not adding filter by argument %s to %s", filterInput, d.Name)
		return nil
	}

	d.Arguments = append(d.Arguments, &ast.ArgumentDefinition{
		Description: "filter the rows returned",
		Name:        sqlgen.WhereClause,
		Type:        &ast.Type{NamedType: fmt.Sprintf("%s_bool_exp", strcase.ToSnake(namedType)), NonNull: false},
	})
	return nil
}

func (f Filters) Schema(s *ast.Schema) error {
	// create all expected bool expressions before going building clauses so there won't be
	// recursive execution, when some bool expressions expect others that weren't added to the schema yet
	boolExpressions := make(map[string]*ast.Definition)
	for _, t := range s.Types {
		tc, err := newTypeConfig(t)
		if err != nil {
			return err
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

	for typeName, boolExpDef := range boolExpressions {
		t, ok := s.Types[typeName]
		if !ok {
			log.Fatal("Failed to find type")
		}
		if t.Kind == ast.Union {
			for _, unionTypes := range t.Types {
				unionType := s.Types[unionTypes]
				addComparatorFields(unionType, boolExpDef, boolExpressions, s)
			}
		} else {
			addComparatorFields(t, boolExpDef, boolExpressions, s)
		}

		// Finally add the logical expressions AND, OR, NOT
		for _, op := range []string{sqlgen.OperationLogicAnd, sqlgen.OperationLogicOr, sqlgen.OperationLogicNot} {
			boolExpDef.Fields = append(boolExpDef.Fields, &ast.FieldDefinition{
				Name: op,
				Type: &ast.Type{
					NamedType: "",
					Elem:      &ast.Type{NamedType: boolExpDef.Name, NonNull: true},
					NonNull:   false,
				},
			})
		}
	}
	return nil
}

func addComparatorFields(field *ast.Definition, boolExpDef *ast.Definition,
	expMap map[string]*ast.Definition, s *ast.Schema) {
	// Add each fields expressions to the boolExp
	for _, f := range field.Fields {
		namedType := sqlgen.GetNamedType(f)

		if be, ok := expMap[namedType]; ok {
			boolExpDef.Fields = append(boolExpDef.Fields, &ast.FieldDefinition{
				Description: fmt.Sprintf("filter by %s", f.Name),
				Name: f.Name,
				Type: &ast.Type{NamedType: be.Name},
			})
			continue
		}
		// Check if type is an Enum, if so we need to create a comperator for it.
		if k, ok := s.Types[namedType]; ok && k.Kind == ast.Enum {
			addEnumComparator(s, namedType)
		}

		typeDefName := fmt.Sprintf("%sComparator", namedType)
		if f.Type.Elem != nil {
			typeDefName = fmt.Sprintf("%sArrayComparator", namedType)
		}
		typeDef, ok := s.Types[typeDefName]
		if !ok {
			fmt.Printf("Failed to find type %s \n", typeDefName)
			continue
		}
		boolExpDef.Fields = append(boolExpDef.Fields, &ast.FieldDefinition{
			Description: fmt.Sprintf("filter by %s", f.Name),
			Name: f.Name,
			Type: &ast.Type{NamedType: typeDef.Name},
		})
	}

}

func addEnumComparator(s *ast.Schema, name string) {
	def := &ast.Definition{
		Kind:        ast.InputObject,
		Description: fmt.Sprintf("Enum filter expression for %s", name),
		Name:        fmt.Sprintf("%sComparator", name),
		Fields: ast.FieldList{
			{

				Name: sqlgen.OperationEq,
				Description: fmt.Sprintf("%s comparison operator", sqlgen.OperationEq),
				Type: &ast.Type{
					NamedType: name,
				},
			},
			{
				Name: sqlgen.OperationNotEq,
				Description: fmt.Sprintf("%s comparison operator", sqlgen.OperationNotEq),
				Type: &ast.Type{
					NamedType: name,
				},
			},
			{
				Name: sqlgen.OperationIn,
				Description: fmt.Sprintf("%s comparison operator", sqlgen.OperationIn),
				Type: &ast.Type{
					NamedType: "",
					Elem: &ast.Type{NamedType: name, NonNull: false},
				},
			},
			{
				Name: sqlgen.OperationNotIn,
				Description: fmt.Sprintf("%s comparison operator", sqlgen.OperationNotIn),
				Type: &ast.Type{
					NamedType: "",
					Elem: &ast.Type{NamedType: name, NonNull: false},
				},
			},
		},
	}
	// add definition to schema
	s.Types[fmt.Sprintf("%sComparator", name)] = def
}