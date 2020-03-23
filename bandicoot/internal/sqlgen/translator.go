package sqlgen

import (
	"context"
	"fmt"
	"github.com/iancoleman/strcase"
	"github.com/rs/zerolog"
	"github.com/vektah/gqlparser/v2/ast"
	"strings"
)

// List of directives
const (
	DirectiveGenerateInputs = "generateInputs"
	DirectiveJsonPath       = "jsonpath"
	DirectiveRelation       = "relation"
	DirectiveViewFunction   = "viewFunction"
)

const (
	ManyToMany = "MANY_TO_MANY"
	OneToOne   = "ONE_TO_ONE"
	OneToMany  = "ONE_TO_MANY"
)

// List of supported clauses
const (
	OrderByClause    = "orderBy"
	WhereClause      = "where"
	OffsetClause     = "offset"
	LimitClause      = "limit"
	GroupByClause    = "groupBy"
	DistinctOnClause = "distinctOn"
)

// List of supported aggregate functions
const (
	SumAggregate     = "sum"
	CountAggregate   = "count"
	AverageAggregate = "avg"
	MinAggregate     = "min"
	MaxAggregate     = "max"
)

// List of common filters supported by translators
const (
	// Common filters
	OperationExists = "exists"
	OperationNot    = "not"
	OperationIn     = "in"
	OperationNotIn  = "not_in"
	OperationEq     = "eq"
	OperationNotEq  = "neq"
	OperationGt     = "gt"
	OperationGte    = "gte"
	OperationLt     = "lt"
	OperationLte    = "lte"
	// Text Operators
	OperationLike     = "like"
	OperationNotLike  = "not_like"
	OperationILike    = "ilike"
	OperationNotILike = "not_ilike"
	OperationPrefix   = "prefix"
	OperationSuffix   = "suffix"
	// Logical filters
	OperationLogicAnd = "AND"
	OperationLogicOr  = "OR"
	OperationLogicNot = "NOT"
	// Array filters
	OperationContains      = "contains"
	OperationContainedBy   = "contained_by"
	OperationOverlap       = "overlap"
	OperationSize          = "size"
	OperationContainsRegex = "contains_regex"
	// Object filters
	OperationBoolExp = "bool_exp"
	// Time filters
	OperationDays = "days"
	// IP filters
	OperationInSubnet = "in_subnet"
	OperationIPFamily = "ip_family"

	// Allows to insert an SQL expr, this is mostly used internally, and it isn't exported
	OperationExpr = "expr"
)

// TranslatorFactory allows for creation of many types of translators
type TranslatorFactory func(ctx context.Context, c Config, variables map[string]interface{}, fragments ast.FragmentDefinitionList, logger *zerolog.Logger) Translator

// Config is the configuration struct for creating a Translator.
type Config struct {
	// Type of translator we want to create (SQL, CQL, InfluxQL, etc')
	//Type TranslatorType
	// GraphQL schema
	Schema *ast.Schema
	// Table name generator
	GenerateTableName func(int) string
	// This method hook allows to modify the argument map before translation will occur
	BeforeTranslation func(context.Context, *ast.Definition, map[string]interface{})
	// This method allows to modify argument map before clauses are added
	BeforeClauses func(context.Context, string, *ast.Definition, map[string]interface{})
}

type Translator interface {
	Translate(field *ast.Field) (Result, error)
	TranslateAggregate(field *ast.Field) (Result, error)
}

type Result struct {
	Query  string
	Params []interface{}
}

// GetComparisonOperation finds the name of the field and logical operator type
func GetComparisonOperation(op string) (string, string) {
	if op == OperationLogicAnd {
		return "", OperationLogicAnd
	}
	if op == OperationLogicNot {
		return "", OperationLogicNot
	}
	if op == OperationLogicOr {
		return "", OperationLogicOr
	}

	s := strings.SplitN(op, "_", 2)
	if len(s) == 1 {
		return op, OperationBoolExp
	}
	return strcase.ToSnake(s[0]), s[1]
}

// GetOrderOperation
func GetOrderOperation(op string) string {
	s := strings.Split(op, "_")
	return fmt.Sprintf("%s %s", strcase.ToSnake(s[0]), s[1])
}

// WhereClauseHasKey checks if given key exists in a common where clause (bool_exp)
func WhereClauseHasKey(m map[string]interface{}, key string) bool {
	for k, v := range m {
		name, cmp := GetComparisonOperation(k)
		if name == key {
			return true
		}
		switch cmp {
		case OperationLogicAnd, OperationLogicOr, OperationLogicNot:
			values, ok := v.([]interface{})
			if !ok {
				continue
			}
			for _, value := range values {
				if mv, ok := value.(map[string]interface{}); ok && WhereClauseHasKey(mv, key) {
					return true
				}
			}
		default:
			continue
		}
	}
	return false
}
