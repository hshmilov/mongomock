package domain

import (
	"bandicoot/internal"
	"context"
	uuid "github.com/satori/go.uuid"
	"time"
)

type User struct {
	Id              uuid.UUID
	CorrelationTime time.Time
	Usernames       []string
	LastSeen        internal.Epoch
	AdapterCount    int `db:"adapter_count"`
	// Foreign keys one-many
	AdapterUsers []AdapterUser
}

type AdapterUser struct {
	Id          uuid.UUID
	FetchCycle  int
	AdapterId   string
	AdapterName string
	Adapter     Adapter
	Client      AdapterClient
	FetchTime   internal.Epoch
	LastSeen    internal.Epoch
	DisplayName string
	Description string
	Domain      string
	UserSID     string
	Mail        string

	Admin          *bool
	Local          *bool
	DelegatedAdmin *bool
	MFAEnforced    *bool
	MFAEnrolled    *bool
	Suspended      *bool
	Locked         *bool
	Disabled       *bool

	CreationDate       internal.Epoch
	LastLogon          internal.Epoch
	LastLogoff         internal.Epoch
	AccountExpires     internal.Epoch
	LastBadLogon       internal.Epoch
	LastPasswordChange internal.Epoch
	LogonCount         int
	Status             string

	PasswordExpirationDate internal.Epoch
	PasswordExpires        *bool
	PasswordRequired       *bool

	FirstName string
	LastName  string
	Username  string

	OrganizationalUnits []string
	Groups              []string

	// Personal details
	City            string
	Title           string
	Department      string
	Manager         string
	Country         string
	TelephoneNumber string
	Image           []byte

	Apps []Application
	// Adapter specific data
	Data map[string]interface{}

	UserId uuid.UUID
	Tags   []Tag
}

type Application struct {
	Name  string
	Links []string
}

type AdapterUserRepo interface {
	InsertAdapterUser(ctx context.Context, ad AdapterUser) error
}

type UserRepository interface {
	CountUsers(ctx context.Context) int64
	FindUsers(ctx context.Context, skip, limit int64) ([]User, error)
}
