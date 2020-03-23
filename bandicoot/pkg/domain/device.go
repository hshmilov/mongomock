package domain

import (
	"bandicoot/internal"
	"context"
	uuid "github.com/satori/go.uuid"
	"time"
)

// Device is a unification of many devices that were retrieved by many adapters
// and correlated into a single device
type Device struct {
	Id              uuid.UUID
	CorrelationTime time.Time
	Hostnames       []string
	LastSeen        internal.Epoch
	AdapterCount    int `db:"adapter_count"`
	// Foreign keys one-many
	AdapterDevices []AdapterDevice
}

type DeviceRepository interface {
	CountDevices(ctx context.Context) int64
	FindDevices(ctx context.Context, skip, limit int64) ([]Device, error)
}
