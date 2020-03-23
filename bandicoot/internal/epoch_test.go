package internal

import (
	"github.com/stretchr/testify/assert"
	"testing"
	"time"
)

func TestEpochFromInt64(t *testing.T) {
	_, err := EpochFromInt64(1577677261898)
	assert.Nil(t, err)
	// Epoch from int64 is only numbers that are 13 digits
	_, err = EpochFromInt64(15776772618984)
	assert.Error(t, err)
	_, err = EpochFromInt64(0)
	assert.Nil(t, err)
	// Negative epoch!
	e, err := EpochFromInt64(-11644473600000)
	assert.Nil(t, err)
	ct := time.Unix(int64(e/1000), int64(e%1000))
	assert.Equal(t, ct.UTC().Format(time.RFC3339), "1601-01-01T00:00:00Z")
}

func TestEpochFromTime(t *testing.T) {
	ct := time.Now()
	e := EpochFromTime(ct)
	expectedTime := ct.Unix() + int64(ct.Nanosecond()/1e6)
	assert.Equal(t, int64(e), expectedTime)

	ct = time.Unix(253402293599, 1*1e6)
	e = EpochFromTime(ct)
	assert.Equal(t, int64(e), int64(253402293600))
}
