package internal

import (
	"errors"
	"math"
	"time"
)

type Epoch int64

func EpochFromTime(t time.Time) Epoch {
	return Epoch(t.Unix() * 1000 + int64(t.Nanosecond() / 1e6))
}

func EpochFromInt64(t int64) (Epoch, error) {
	if (int)(math.Log10(float64(t))+1) <= 13 {
		return Epoch(t), nil
	}

	return 0, errors.New("epoch must be an int in milliseconds")
}