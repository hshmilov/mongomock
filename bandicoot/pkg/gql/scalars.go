package gql

import (
	"bandicoot/internal"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/99designs/gqlgen/graphql"
	uuid "github.com/satori/go.uuid"
	"github.com/spf13/cast"
	"io"
	"log"
	"net"
	"strconv"
)

type Epoch int64

func MarshalEpochScalar(b internal.Epoch) graphql.Marshaler {
	return graphql.WriterFunc(func(w io.Writer) {
		_, _ = w.Write([]byte(strconv.Itoa(int(b))))
	})
}

func UnmarshalEpochScalar(v interface{}) (internal.Epoch, error) {
	var val int64
	var err error
	switch v := v.(type) {
	case json.Number:
		val, err = v.Int64()
	default:
		val, err = cast.ToInt64E(v)
	}
	if err != nil {
		return 0, errors.New(fmt.Sprintf("epoch must be of type Int, got %T ", v))
	}
	return internal.EpochFromInt64(val)
}

func MarshalUUIDScalar(u uuid.UUID) graphql.Marshaler {
	return graphql.WriterFunc(func(w io.Writer) {
		_, err := w.Write([]byte(strconv.Quote(u.String())))
		if err != nil {
			log.Fatal(err)
		}
	})
}

func UnmarshalUUIDScalar(v interface{}) (uuid.UUID, error) {
	switch v := v.(type) {
	case []byte:
		return uuid.FromBytes(v)
	case string:
		return uuid.FromString(v)
	default:
		return uuid.UUID{}, fmt.Errorf("%T is not a valid uuid", v)
	}
}

func MarshalIPScalar(u net.IP) graphql.Marshaler {
	return graphql.WriterFunc(func(w io.Writer) {
		_, err := w.Write([]byte(strconv.Quote(u.String())))
		if err != nil {
			log.Fatal(err)
		}
	})
}

func UnmarshalIPScalar(v interface{}) (net.IP, error) {
	switch v := v.(type) {
	case string:
		ip := net.ParseIP(v)
		if ip == nil {
			return net.IP{}, fmt.Errorf("%s is not a valid ip address", v)
		}
		return ip, nil
	default:
		return net.IP{}, fmt.Errorf("%T is not a valid ip address", v)
	}
}

func MarshalCIDRScalar(u net.IPNet) graphql.Marshaler {
	return graphql.WriterFunc(func(w io.Writer) {
		_, err := w.Write([]byte(strconv.Quote(u.String())))
		if err != nil {
			log.Fatal(err)
		}
	})
}

func UnmarshalCIDRScalar(v interface{}) (net.IPNet, error) {
	switch v := v.(type) {
	case string:
		_, inet, err := net.ParseCIDR(v)
		if err != nil {
			return net.IPNet{}, err
		}
		return *inet, err
	default:
		return net.IPNet{}, fmt.Errorf("%T is not a valid ip cidr", v)
	}
}

func MarshalMacScalar(u string) graphql.Marshaler {
	return graphql.WriterFunc(func(w io.Writer) {
		_, err := w.Write([]byte(strconv.Quote(u)))
		if err != nil {
			log.Fatal(err)
		}
	})
}

func UnmarshalMacScalar(v interface{}) (string, error) {
	switch v := v.(type) {
	case string:
		hw, err := net.ParseMAC(v)
		if err != nil {
			return "", err
		}
		return hw.String(), nil
	default:
		return "", fmt.Errorf("%T is not a valid ip address", v)
	}
}
