package gql

import (
	"context"
	"fmt"
	"github.com/99designs/gqlgen/graphql"
	"github.com/iancoleman/strcase"
	json "github.com/json-iterator/go"
	"github.com/rs/zerolog/log"
	uuid "github.com/satori/go.uuid"
	"reflect"
	"strings"
	"time"
)

type deviceResolver struct{ *Resolver }

type userResolver struct{ *Resolver }

var mappingConversions = map[string]string{
	"adapterCount":   "adapter_list_length",
	"adapterNames":   "adapters",
	"adapterDevices": "specific_data.data",
	"adapterUsers":   "specific_data.data",
	"interfaces":     "network_interfaces",
	"macAddr":        "mac",
	"ipAddrs":        "ips",
	"tags":           "label_details",
	"id":             "internal_axon_id",
	"admin": 		  "is_admin",
	"local": 		  "is_local",
	"delegatedAdmin": "is_delegated_admin",
	"mfaEnforced": 	  "is_mfa_enforced",
	"mfaEnrolled": 	  "is_mfa_enrolled",
	"suspended": 	  "is_suspended",
	"locked": 		  "is_locked",
	"disabled": 	  "is_disabled",
}

var pathFolding = map[string]string{
	"label_details.name": "label_details",
}

// compatibility
func (d deviceResolver) CompatibilityAPI(ctx context.Context, obj *Device) (map[string]interface{}, error) {
	return createCompatibility(graphql.GetFieldContext(ctx), graphql.GetOperationContext(ctx), obj)
}

func (d userResolver) CompatibilityAPI(ctx context.Context, obj *User) (map[string]interface{}, error) {
	return createCompatibility(graphql.GetFieldContext(ctx), graphql.GetOperationContext(ctx), obj)
}

func createCompatibility(f *graphql.FieldContext, op *graphql.OperationContext, obj interface{}) (map[string]interface{}, error) {
	start := time.Now()
	defer log.Debug().TimeDiff("elapsed", time.Now(), start).Msg("Time took to build compatibility API")
	fields := graphql.CollectFields(op, f.Parent.Parent.Field.Selections, nil)
	data, _ := json.ConfigFastest.Marshal(obj)
	return buildCompatibility(createFieldMappings(op, fields), json.Get(data)), nil

}

func buildDetails(m map[string]interface{}) map[string]interface{} {
	cm := make(map[string]interface{})
	for k, v := range m {
		// Check if this key is path folded
		if f, ok := pathFolding[k]; ok {
			cm[f] = v
			continue
		}
		switch v := v.(type) {
		case []interface{}:
			// remove duplicates and make it as main key
			cm[fmt.Sprintf("%s_details", k)] = v
			cm[k] = removeDuplicatesFromSlice(v)
		default:
			cm[k] = v
		}
	}
	return cm
}

func createFieldMappings(opCtx *graphql.OperationContext, fields []graphql.CollectedField) map[string]string {
	mappings := make(map[string]string)
	for _, f := range fields {
		if strings.HasPrefix(f.Name, "_") {
			continue
		}
		mName, ok := mappingConversions[f.Name]
		if !ok {
			mName = strcase.ToSnake(f.Name)
		}
		if f.SelectionSet != nil {
			for k, v := range createFieldMappings(opCtx, graphql.CollectFields(opCtx, f.Selections, nil)) {
				mappings[strings.Join([]string{strcase.ToSnake(f.Name), k}, ".")] = strings.Join([]string{mName, v}, ".")
			}
		} else {
			mappings[strcase.ToSnake(f.Name)] = mName
		}
	}
	return mappings
}

func buildCompatibilityField(originalPath []string, parentValue json.Any) interface{} {
	switch parentValue.ValueType() {
	case json.StringValue:
		_, err := uuid.FromString(parentValue.ToString())
		if err == nil {
			return strings.ReplaceAll(parentValue.ToString(), "-", "")
		}
		fallthrough
	case json.NumberValue, json.BoolValue:
		return parentValue.GetInterface()
	case json.NilValue:
		return nil
	case json.ArrayValue:
		values := make([]interface{}, parentValue.Size())
		for i := 0; i < parentValue.Size(); i++ {
			value := parentValue.Get(i)
			values[i] = buildCompatibilityField(originalPath, value)
		}
		return values
	case json.ObjectValue:
		return buildCompatibilityField(originalPath[1:], parentValue.Get(originalPath[0]))
	}
	return nil
}

func buildCompatibility(m map[string]string, parentValue json.Any) map[string]interface{} {
	mappings := make(map[string]interface{})
	for k, v := range m {
		mappings[v] = buildCompatibilityField(strings.Split(k, "."), parentValue)
	}
	return buildDetails(mappings)
}

// Removes duplicates from slice, also removes nil and empty strings
func removeDuplicatesFromSlice(sl []interface{}) []interface{} {
	var result []interface{}
	hadInnerArray := false
	for _, i := range sl {
		if i == nil {
			continue
		}
		// try type string if empty string remove
		if s, ok := i.(*string); ok && *s == "" {
			continue
		}
		exists := false
		for _, j := range result {
			if reflect.DeepEqual(i, j) {
				exists = true
				break
			}
		}
		if exists {
			continue
		}
		switch i := i.(type) {
		case []interface{}:
			hadInnerArray = true
			result = append(result, i...)
		default:
			result = append(result, i)
		}
	}
	if !hadInnerArray {
		return result
	}
	return removeDuplicatesFromSlice(result)
}
