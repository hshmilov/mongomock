package domain

import (
	uuid "github.com/satori/go.uuid"
	"github.com/stretchr/testify/assert"
	"testing"
)

func TestGetOSId(t *testing.T) {
	assert.NotEqual(t, GetOSId(Windows, X86, "").String(), uuid.Nil)
	assert.NotEqual(t, GetOSId(Windows, UnknownArchitecture, "").String(), uuid.Nil)
	assert.Equal(t, GetOSId(Linux, X64, "").String(), GetOSId(Linux, X64, "").String())
	assert.NotEqual(t, GetOSId(Linux, X64, "").String(), GetOSId(Linux, X86, "").String())
	assert.NotEqual(t, GetOSId(Linux, X64, "Fedora").String(), GetOSId(Linux, X64, "Ubuntu").String())

	assert.Equal(t, GetOSId(UnknownOs, UnknownArchitecture, "").String(), "41d22eb3-f27e-471b-4341-770e585fa787")
	assert.Equal(t, GetOSId(UnknownOs, X64, "").String(), "e3b8bb35-4318-4af6-8092-3949327505e1")
	assert.Equal(t, GetOSId(UnknownOs, X86, "").String(), "1139e3d1-d78f-996c-ae0d-bebeb1cea544")
}
