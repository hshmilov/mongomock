package sql

import (
	"errors"
	"fmt"
	"github.com/jackc/pgtype"
	"github.com/modern-go/reflect2"
	"github.com/spf13/cast"
	"net"
	"reflect"
)

//nolint
const (
	// Date / Time
	pgTypeTimestamp   = "timestamp"           // Timestamp without a time zone
	pgTypeTimestampTz = "timestamptz"         // Timestamp with a time zone
	pgTypeDate        = "date"                // Date
	pgTypeTime        = "time"                // Time without a time zone
	pgTypeTimeTz      = "time with time zone" // Time with a time zone
	pgTypeInterval    = "interval"            // Time Interval

	// Network Addresses
	pgTypeInet    = "inet"    // IPv4 or IPv6 hosts and networks
	pgTypeCidr    = "cidr"    // IPv4 or IPv6 networks
	pgTypeMacaddr = "macaddr" // MAC adresses

	// Boolean
	pgTypeBoolean = "boolean"

	// Numeric Types

	// Floating Point Types
	pgTypeReal            = "real"             // 4 byte floating point (6 digit precision)
	pgTypeDoublePrecision = "double precision" // 8 byte floating point (15 digit precision)

	// Integer Types
	pgTypeSmallint = "smallint" // 2 byte integer
	pgTypeInteger  = "integer"  // 4 byte integer
	pgTypeBigint   = "bigint"   // 8 byte integer

	// Character Types
	pgTypeVarchar = "varchar" // variable length string with limit
	pgTypeChar    = "char"    // fixed length string (blank padded)
	pgTypeText    = "text"    // variable length string without limit

	// JSON Types
	pgTypeJSON  = "json"  // text representation of json data
	pgTypeJSONB = "jsonb" // binary representation of json data

	// Binary Data Types
	pgTypeBytea = "bytea" // binary string
)

func fieldSQLType(val reflect.Value) string {
	switch val.Kind() {
	case reflect.Slice, reflect.Array:
		if val.Len() == 0 {
			return "text[]"
		}
		return fmt.Sprintf("%s[]", sqlType(reflect.ValueOf(val.Index(0).Interface())))
	default:
		return sqlType(val)
	}
}

func sqlType(val reflect.Value) string {
	switch val.Kind() {
	case reflect.Int8, reflect.Uint8, reflect.Int16:
		return pgTypeSmallint
	case reflect.Uint16, reflect.Int32:
		return pgTypeInteger
	case reflect.Uint32, reflect.Int64, reflect.Int:
		return pgTypeBigint
	case reflect.Uint, reflect.Uint64:
		// Unsigned bigint is not supported - use bigint.
		return pgTypeBigint
	case reflect.Float32:
		return pgTypeReal
	case reflect.Float64:
		return pgTypeDoublePrecision
	case reflect.Bool:
		return pgTypeBoolean
	case reflect.String:
		return pgTypeText
	case reflect2.TypeOf(net.IPNet{}).Kind():
		return pgTypeInet
	case reflect2.TypeOf(net.HardwareAddr{}).Kind():
		return pgTypeMacaddr
	case reflect.Map, reflect.Struct:
		return pgTypeJSONB
	case reflect.Array, reflect.Slice:
		if val.Elem().Kind() == reflect.Uint8 {
			return pgTypeBytea
		}
		return pgTypeJSONB
	default:
		return val.Kind().String()
	}
}

type AnySlice struct {
	Value []interface{}
}

// TODO: improve this and support EncodeBinary
func (a AnySlice) EncodeText(ci *pgtype.ConnInfo, buf []byte) (newBuf []byte, err error) {
	if 0 == len(a.Value) {
		return []byte("{}"), nil
	}
	t := reflect2.TypeOf(a.Value[0])
	switch t.Kind() { // type of the slice element
	case reflect.Int, reflect.Int32, reflect.Int64:
		// Handle int case
		arr := pgtype.Int8Array{}
		vv := convertToInt8(cast.ToSlice(a.Value))
		err = arr.Set(vv)
		return arr.EncodeText(ci, buf)
	case reflect.Int8, reflect.Int16:
		// Handle int case
		arr := pgtype.Int2Array{}
		vv := convertToInt2(cast.ToSlice(a.Value))
		err = arr.Set(vv)
		return arr.EncodeText(ci, buf)
	case reflect.String:
		arr := pgtype.TextArray{}
		_ = arr.Set(cast.ToStringSlice(a.Value))
		return arr.EncodeText(ci, buf)
	default:
		return nil, errors.New("unsupported slice type")
	}
}

func convertToInt2(v []interface{}) []int16 {
	d := make([]int16, len(v))
	for i, f := range v {
		d[i] = cast.ToInt16(f)
	}
	return d
}

func convertToInt8(v []interface{}) []int64 {
	d := make([]int64, len(v))
	for i, f := range v {
		d[i] = cast.ToInt64(f)
	}
	return d
}
