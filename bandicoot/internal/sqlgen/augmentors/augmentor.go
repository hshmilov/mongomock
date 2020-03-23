package augmentors

import (
	"bandicoot/internal/sqlgen"
	"fmt"
	"github.com/vektah/gqlparser/v2/ast"
)

const (
	typeID           = "ID"
	typeString       = "String"
	typeInt          = "Int"
	typeFloat        = "Float"
	typeBoolean      = "Boolean"
	typeDateTime     = "Time"
	typeEpoch        = "Epoch"
	typeUUID         = "UUID"
	typeNullDateTime = "NullDateTime"
	typeIP           = "IP"
	typeMacAddr      = "Mac"
)

// GetNamedType returns the name from an ast.FieldDefinition, if the definition is an array
// returns the inner element name
func getNamedType(f *ast.FieldDefinition) string {

	if f.Type.NamedType != "" {
		return f.Type.NamedType
	}
	if f.Type.Elem == nil {
		return ""
	}
	return f.Type.Elem.NamedType
}

type typeConfig struct {
	Where     string
	OrderBy   string
	Aggregate string
}

// newTypeConfig parses an ast.Definition returning typeConfig is the type has @generate_inputs directive
func newTypeConfig(t *ast.Definition) (*typeConfig, error) {
	// get directive definition
	def := t.Directives.ForName(sqlgen.DirectiveGenerateInputs)
	if def == nil {
		return nil, nil
	}
	// get where arg
	whereArg := def.Arguments.ForName(sqlgen.WhereClause)
	if whereArg == nil {
		return nil, fmt.Errorf("missing where argument for @%s", sqlgen.DirectiveGenerateInputs)
	}
	// get orderBy arg
	orderByArg := def.Arguments.ForName(sqlgen.OrderByClause)
	if orderByArg == nil {
		return nil, fmt.Errorf("missing orderBy argument for @%s", sqlgen.DirectiveGenerateInputs)
	}
	// get where value
	whereName, err := whereArg.Value.Value(nil)
	if err != nil {
		return nil, fmt.Errorf("failed to obtain value from where arg: %s", err.Error())
	}
	// get orderBy value
	orderByName, err := orderByArg.Value.Value(nil)
	if err != nil {
		return nil, fmt.Errorf("failed to obtain value from orderBy arg: %s", err.Error())
	}
	return &typeConfig{
		Where:   whereName.(string),
		OrderBy: orderByName.(string),
	}, nil
}

type Augmenter interface {
	// Field allows augmentation on a single field, usually used to add arguments to that field
	Field(s *ast.Schema, field *ast.FieldDefinition, parent *ast.Definition) error
	// Schema allows augmentation on the parse schema as a whole, if types needed to be added etc' this is the place
	// this function is called before field.
	Schema(s *ast.Schema) error
}
