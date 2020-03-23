package sql

import (
	"bandicoot/internal/sqlgen"
	"fmt"
	"github.com/iancoleman/strcase"
	"github.com/spf13/cast"
	"github.com/vektah/gqlparser/v2/ast"
	"strings"
)

type relation struct {
	NamedType       string
	Name            string
	fkNames         []string
	relationFkNames []string
	relType         string
	manyToManyTable string
	joinOn          []string
}

func (r relation) buildRelationClause(tableName string, relationTableName string) string {
	clauses := make([]string, 0)
	for i, fkName := range r.fkNames {

		clauses = append(clauses, fmt.Sprintf("%s.%s = %s.%s", tableName,
			strcase.ToSnake(fkName), relationTableName, strcase.ToSnake(r.relationFkNames[i])))
	}
	return strings.Join(clauses, " AND ")
}


type viewFunction struct {
	name      string
	arguments []string
}

func (v viewFunction) buildFunctionClause(relationTableName string) string {
	arguments := make([]string, len(v.arguments))
	for i, a := range v.arguments {
		arguments[i] = relationTableName + "." + a
	}
	return fmt.Sprintf("%s(%s)", v.name, strings.Join(arguments, ","))
}

type jsonPath struct {
	name    string
	depends []string
}

// TODO: this code looks like garbage fix it.. seriously..
func getFieldRelationDirective(selectionDefinition *ast.FieldDefinition) relation {
	relDirective := selectionDefinition.Directives.ForName(sqlgen.DirectiveRelation)
	if relDirective == nil {
		return relation{}
	}
	tableName := strings.Trim(relDirective.Arguments[0].Value.String(), "\"")
	fkNames, _ := relDirective.Arguments[1].Value.Value(nil)
	relationFkNames, _ := relDirective.Arguments[2].Value.Value(nil)
	relType := strings.Trim(relDirective.Arguments[3].Value.String(), "\"")
	manyToManyTableName := ""
	var joinOn []string
	if len(relDirective.Arguments) >= 6 {
		manyToManyTableName = strings.Trim(relDirective.Arguments[4].Value.String(), "\"")
		value, _ := relDirective.Arguments[5].Value.Value(nil)
		joinOn = cast.ToStringSlice(value)
	}

	return relation{
		selectionDefinition.Type.Name(),
		tableName,
		cast.ToStringSlice(fkNames),
		cast.ToStringSlice(relationFkNames),
		relType,
		manyToManyTableName, joinOn}
}

func getFieldViewFunction(selectionDefinition *ast.FieldDefinition) viewFunction {

	directive := selectionDefinition.Directives.ForName(sqlgen.DirectiveViewFunction)
	if directive == nil {
		return viewFunction{}
	}
	name := strings.Trim(directive.Arguments[0].Value.String(), "\"")
	arguments, _ := directive.Arguments[1].Value.Value(nil)
	return viewFunction{
		name:      name,
		arguments: cast.ToStringSlice(arguments),
	}
}

func getFieldJsonPathDirective(selectionDefinition *ast.FieldDefinition) jsonPath {

	directive := selectionDefinition.Directives.ForName(sqlgen.DirectiveJsonPath)
	if directive == nil {
		return jsonPath{}
	}
	name := strings.Trim(directive.Arguments[0].Value.String(), "\"")
	depends, _ := directive.Arguments[1].Value.Value(nil)
	return jsonPath{
		name:    name,
		depends: cast.ToStringSlice(depends),
	}
}
