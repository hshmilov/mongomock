package sql

import (
	"bandicoot/internal/sqlgen"
	"fmt"
	"github.com/rs/zerolog/log"
	"github.com/spf13/cast"
	"reflect"
	"strings"
)

// TODO: build this correctly instead of the random casting
func createJsonPathCondition(column string, v map[string]interface{}) (string, []interface{}) {
	var sb strings.Builder
	values := make([]interface{}, 0)
	// Double ? to escape ? in sql builder
	sb.WriteString(fmt.Sprintf("%s @?? format('$ ?? (", column))
	values = append(values, buildJsonFilter(&sb, v, "")...)
	// Close jsonpath
	sb.WriteString(")'")
	// Add values and sql cast them accordingly
	for i, val := range values {
		sb.WriteString(",")
		sqlTypeName := fieldSQLType(reflect.ValueOf(val))
		sb.WriteString(fmt.Sprintf("?::%s", sqlTypeName))
		switch val.(type) {
		case []interface{}:
			values[i] = AnySlice{cast.ToSlice(val)}
		}
	}
	// close format
	sb.WriteString(")::jsonpath")
	return sb.String(), values
}

func buildJsonFilter(sb *strings.Builder, v map[string]interface{}, parent string) []interface{} {

	args := make([]interface{}, 0)
	first := false
	for k, v := range v {
		name, cmp := sqlgen.GetComparisonOperation(k)
		log.Trace().Str("cmp", cmp).Str("name", name).Interface("value", v).Msg("adding condition")
		// if this isn't the first operation, add && to combine the conditions
		if first {
			sb.WriteString(" && ")
		} else {
			first = true
		}
		var formatter string
		switch reflect.TypeOf(v).Kind() {
		case reflect.String:
			formatter = "\"%I\""
		default:
			formatter = "%I"
		}
		if parent != "" {
			name = fmt.Sprintf("%s.%s", parent, name)
		}
		switch cmp {
		case sqlgen.OperationExists:
			sb.WriteString(fmt.Sprintf("exists(@.%s)", name))
		case sqlgen.OperationEq:
			sb.WriteString(fmt.Sprintf("@.%s == %s", name, formatter))
			args = append(args, v)
		case sqlgen.OperationNotEq:
			sb.WriteString(fmt.Sprintf("@.%s != %s", name, formatter))
			args = append(args, v)
		case sqlgen.OperationGte:
			sb.WriteString(fmt.Sprintf("@.%s >= %s", name, formatter))
			args = append(args, v)
		case sqlgen.OperationGt:
			sb.WriteString(fmt.Sprintf("@.%s > %s", name, formatter))
			args = append(args, v)
		case sqlgen.OperationLt:
			sb.WriteString(fmt.Sprintf("@.%s < %s", name, formatter))
			args = append(args, v)
		case sqlgen.OperationLte:
			sb.WriteString(fmt.Sprintf("@.%s <= %s", name, formatter))
			args = append(args, v)
		case sqlgen.OperationLike:
			sb.WriteString(fmt.Sprintf("@.%s like_regex \"%%s\"", name))
			args = append(args, v)
		case sqlgen.OperationILike:
			sb.WriteString(fmt.Sprintf("@.%s like_regex \"%%s\" flag \"i\"", name))
			args = append(args, v)
		case sqlgen.OperationIn:
			sb.WriteString(fmt.Sprintf("@.%s == %s[*]", name, formatter))
			args = append(args, v)
		case sqlgen.OperationNotIn:
			sb.WriteString(fmt.Sprintf("@.%s != %s[*]", name, formatter))
			args = append(args, v)
		case sqlgen.OperationLogicAnd:
			v, ok := v.([]interface{})
			if !ok {
				return nil
			}
			args = append(args, buildComplexFilter(sb, v, " && ", name)...)
		case sqlgen.OperationLogicOr:
			v, ok := v.([]interface{})
			if !ok {
				return nil
			}
			args = append(args, buildComplexFilter(sb, v, " || ", name)...)
		case sqlgen.OperationBoolExp:
			v, ok := v.(map[string]interface{})
			if !ok {
				return nil
			}
			args = append(args, buildJsonFilter(sb, v, name)...)
		default:
			log.Warn().Str("op", cmp).Msg("operation not supported")
		}
	}
	return args
}

func buildComplexFilter(sb *strings.Builder, values []interface{}, op, parent string) []interface{} {
	args := make([]interface{}, 0)
	if len(values) == 0 {
		return args
	}
	sb.WriteString("(")
	first := true
	for _, v := range values {
		vMap, ok := v.(map[string]interface{})
		if !ok {
			continue
		}
		if !first {
			sb.WriteString(op)
		} else {
			first = false
		}
		args = append(args, buildJsonFilter(sb, vMap, parent)...)
	}
	sb.WriteString(")")
	return args
}
