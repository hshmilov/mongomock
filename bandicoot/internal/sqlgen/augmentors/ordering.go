package augmentors

import (
	"bandicoot/internal/sqlgen"
	"fmt"
	"github.com/iancoleman/strcase"
	"github.com/vektah/gqlparser/v2/ast"
	"log"
	"strings"
)

type Ordering struct{}

func (o Ordering) Field(s *ast.Schema, d *ast.FieldDefinition, p *ast.Definition) error {
	// Ordering is only supported in top level query for now.
	if p.Name != "Query" || d.Type == nil || d.Type.Elem == nil {
		return nil
	}
	namedType := d.Type.NamedType
	if namedType == "" {
		namedType = d.Type.Elem.NamedType
	}
	// Get inner element type
	def := s.Types[namedType]
	if !def.IsCompositeType() {
		return nil
	}
	if strings.HasSuffix(namedType, "Aggregate") {
		return nil
	}

	orderByInput := fmt.Sprintf("%s_order_by", strcase.ToSnake(namedType))
	if _, ok := s.Types[orderByInput]; !ok {
		log.Printf("Not adding order by argument %s to %s", orderByInput, d.Name)
		return nil
	}
	d.Arguments = append(d.Arguments, &ast.ArgumentDefinition{
		Description: "sort the rows by one or more columns",
		Name:        sqlgen.OrderByClause,
		Type: &ast.Type{
			NamedType: "",
			Elem:      &ast.Type{NamedType: orderByInput, NonNull: true},
			NonNull:   false},
	})
	return nil
}

func (o Ordering) Schema(s *ast.Schema) error {

	orderByExpressions := make(map[string]*ast.Definition)
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
			Kind:        ast.Enum,
			Description: fmt.Sprintf("Order for %s", t.Name),
			Name:        tc.OrderBy,
		}
		// Add to our boolExpressions so we can add fields later
		orderByExpressions[t.Name] = def
		// We initially want to add all the bool expressions since they might point at one another recursively
		s.Types[tc.OrderBy] = def
	}
	for typeName, orderExp := range orderByExpressions {
		t, ok := s.Types[typeName]
		if !ok {
			log.Fatal("Failed to find type")
		}
		// Add each fields expressions to the boolExp
		for _, f := range t.Fields {
			of := orderByFields(f)
			if of == nil {
				continue
			}
			orderExp.EnumValues = append(orderExp.EnumValues, of...)
		}
		// We delete after ranging because not fields are supported in ordering
		if len(orderExp.EnumValues) == 0 {
			delete(s.Types, orderExp.Name)
		}
	}

	return nil
}

// orderByFields builds returns enum value definitions based on field type.
func orderByFields(field *ast.FieldDefinition) []*ast.EnumValueDefinition {
	switch field.Type.NamedType {
	case typeID, typeInt, typeDateTime, typeNullDateTime, typeString, typeEpoch:
		return []*ast.EnumValueDefinition{
			{
				Description: fmt.Sprintf("Order by %s in an ascending order", field.Name),
				Name:        fmt.Sprintf("%s_ASC", field.Name),
			},
			{
				Description: fmt.Sprintf("Order by %s in a descending order", field.Name),
				Name:        fmt.Sprintf("%s_DESC", field.Name),
			},
		}
	}
	return nil
}
