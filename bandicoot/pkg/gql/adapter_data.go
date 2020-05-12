package gql

import (
	"bandicoot/pkg/domain"
	"context"
	"errors"
	"fmt"
	jsoniter "github.com/json-iterator/go"
)

type adapterDeviceResolver struct{ *Resolver }

func (r *adapterDeviceResolver) AdapterData(ctx context.Context, obj *AdapterDevice, where *AdapterDataBoolExp) (AdapterData, error) {
	jsonBody, err := jsoniter.Marshal(obj.Data)
	if err != nil {
		return nil, err
	}
	switch domain.AdapterType(obj.AdapterID) {
	case domain.AdapterTypeActiveDirectory:
		var result ActiveDirectoryData
		if err := jsoniter.Unmarshal(jsonBody, &result); err != nil {
			return nil, err
		}
		return result, nil
	case domain.AdapterTypeCrowdStrike:
		var result CrowdStrikeData
		if err := jsoniter.Unmarshal(jsonBody, &result); err != nil {
			return nil, err
		}
		return result, nil
	default:
		return nil, errors.New(fmt.Sprintf("adapter type not found %s", obj.AdapterID))
	}
}

type adapterUserResolver struct{ *Resolver }

func (r *adapterUserResolver) AdapterData(ctx context.Context, obj *AdapterUser, where *AdapterDataBoolExp) (AdapterData, error) {
	jsonBody, err := jsoniter.Marshal(obj.Data)
	if err != nil {
		return nil, err
	}
	switch domain.AdapterType(obj.AdapterID) {
	case domain.AdapterTypeActiveDirectory:
		var result ActiveDirectoryData
		if err := jsoniter.Unmarshal(jsonBody, &result); err != nil {
			return nil, err
		}
		return result, nil
	case domain.AdapterTypeCrowdStrike:
		var result CrowdStrikeData
		if err := jsoniter.Unmarshal(jsonBody, &result); err != nil {
			return nil, err
		}
		return result, nil
	default:
		return nil, errors.New(fmt.Sprintf("adapter type not found %s", obj.AdapterID))
	}
}
