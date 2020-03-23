package augmentors

import (
	"bandicoot/internal/sqlgen"
	"github.com/vektah/gqlparser/v2/ast"
)

type Pagination struct{}

// Pagination adds to list composite types limit and offset to allow for pagination
func (p Pagination) Field(s *ast.Schema, d *ast.FieldDefinition, _ *ast.Definition) error {
	if d.Type == nil || d.Type.Elem == nil {
		return nil
	}
	// Get inner element type
	def := s.Types[d.Type.Elem.Name()]
	if !def.IsCompositeType() {
		return nil
	}
	d.Arguments = append(d.Arguments, &ast.ArgumentDefinition{
		Description:  "limit the number of rows returned.",
		Name:         sqlgen.LimitClause,
		Type:         &ast.Type{NamedType: typeInt, NonNull: false},
		DefaultValue: &ast.Value{Raw: "100", Kind: ast.IntValue},
	}, &ast.ArgumentDefinition{
		Description:  "skip the first n rows.",
		Name:         sqlgen.OffsetClause,
		Type:         &ast.Type{NamedType: typeInt, NonNull: false},
		DefaultValue: &ast.Value{Raw: "0", Kind: ast.IntValue},
	})
	return nil
}

//
func (p Pagination) Schema(_ *ast.Schema) error {
	return nil
}
