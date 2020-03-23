package domain

import (
	"context"
	"crypto/md5"
	"fmt"
	uuid "github.com/satori/go.uuid"
)

const (
	UnknownOs = "Unknown"
	Windows   = "Windows"
	Linux     = "Linux"
	OsX       = "macOS"
	FreeBSD   = "FreeBSD"
	VMWare    = "VMWare"
	IOS       = "iOS"
	Cisco     = "Cisco"
	Android   = "Android"
)

const (
	UnknownArchitecture = 0
	X64                 = 64
	X86                 = 86
)

type OperatingSystem struct {
	// Id is a unique combination from Type + Distribution and Architecture
	// All of them as null will result in the Unknown operating system
	Id            uuid.UUID
	Type          string
	Distribution  string
	Architecture  int
	ServicePack   string
	KernelVersion string
	CodeName      string
	Major         int
	Minor         int
	Build         string
	RawName       string
}

func GetOSId(osType string, arch int, distribution string) uuid.UUID {
	md := md5.New()
	_, err := md.Write([]byte(fmt.Sprintf("%s:%d:%s", osType, arch, distribution)))
	if err != nil {
		return uuid.Nil
	}
	return uuid.FromBytesOrNil(md.Sum(nil))
}

type OSRepository interface {
	FindOperatingSystems(ctx context.Context, skip, limit int64) ([]OperatingSystem, error)
	SaveOperatingSystems(ctx context.Context, a OperatingSystem) error
}
