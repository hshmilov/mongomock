package mongo

import (
	"bandicoot/internal"
	"bandicoot/pkg/domain"
	"context"
	"crypto/md5"
	"github.com/rs/zerolog/log"
	uuid "github.com/satori/go.uuid"
	"github.com/spf13/cast"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo/options"
	"time"
)

// Keys removed from the data because they are redundant or normalized
var userKeysToRemove = []string{
	// Normalized
	"account_expires",
	// Adapter redundancies
	"ad_account_expires",
	// Redundant
	"raw",
	"public_ips_raw",
	"agent_version_raw",
	"accurate_for_datetime",
	"first_fetch_time",
	"_old",
}

type aggregatedUser struct {
	Id             primitive.ObjectID `bson:"_id" json:"_id"`
	InternalAxonId string             `bson:"internal_axon_id" json:"internal_axon_id"`
	Adapters       []adapter
	Tags           []tag `bson:"tags" json:"tags"`
}

type userData struct {
	FetchTime primitive.DateTime `bson:"fetch_time" json:"fetch_time"`
	LastSeen  primitive.DateTime `bson:"last_seen" json:"last_seen"`

	DisplayName string `bson:"display_name" json:"display_name"`
	Description string
	Domain      string
	UserSID     string `bson:"user_sid" json:"user_sid"`
	Mail        string

	Admin          *bool `bson:"is_admin" json:"is_admin"`
	Local          *bool `bson:"is_local" json:"is_local"`
	DelegatedAdmin *bool `bson:"is_delegated_admin" json:"is_delegated_admin"`
	MFAEnforced    *bool `bson:"is_mfa_enforced" json:"is_mfa_enforced"`
	MFAEnrolled    *bool `bson:"is_mfa_enrolled" json:"is_mfa_enrolled"`
	Suspended      *bool `bson:"is_suspended" json:"is_suspended"`
	Locked         *bool `bson:"is_locked" json:"is_locked"`
	Disabled       *bool `bson:"is_disabled" json:"is_disabled" bson:"account_disabled"`

	CreationDate       primitive.DateTime `bson:"user_creation_date" json:"user_creation_date"`
	LastLogon          primitive.DateTime `bson:"last_logon" json:"last_logon"`
	LastLogoff         primitive.DateTime `bson:"last_logoff" json:"last_logoff"`
	AccountExpires     primitive.DateTime `bson:"account_expires" json:"account_expires"`
	LastBadLogon       primitive.DateTime `bson:"last_bad_logon" json:"last_bad_logon"`
	LastPasswordChange primitive.DateTime `bson:"last_password_change" json:"last_password_change"`
	LogonCount         int                `bson:"logon_count" json:"logon_count"`
	Status             string             `bson:"user_status" json:"user_status"`

	PasswordExpirationDate primitive.DateTime `bson:"password_expiration_date" json:"password_expiration_date"`
	PasswordExpires        bool               `bson:"password_never_expires" json:"password_never_expires"`
	PasswordRequired       bool               `bson:"password_not_required" json:"password_not_required"`

	FirstName string `bson:"first_name" json:"first_name"`
	LastName  string `bson:"last_name" json:"last_name"`
	Username  string `bson:"username" json:"username"`

	OrganizationalUnits []string `bson:"organizational_unit" json:"organizational_unit"`
	Groups              []string

	// Personal details
	City            string `bson:"user_city" json:"user_city"`
	Title           string `bson:"user_title" json:"user_title"`
	Department      string `bson:"user_department" json:"user_department"`
	Manager         string `bson:"user_manager" json:"user_manager"`
	Country         string `bson:"user_country" json:"user_country"`
	TelephoneNumber string `bson:"user_telephone_number" json:"user_telephone_number"`
	Image           string

	Apps []domain.Application `bson:"user_apps" json:"user_apps"`
}

func (m *Repo) CountUsers(ctx context.Context) int64 {
	collection := m.client.Database("aggregator").Collection("users_db")
	count, err := collection.CountDocuments(ctx, bson.D{})
	if err != nil {
		log.Error().Err(err).Msg("Failed to count devices")
		return 0
	}
	return count
}

func (m *Repo) FindUsers(ctx context.Context, skip, limit int64) ([]domain.User, error) {

	collection := m.client.Database("aggregator").Collection("users_db")
	cur, err := collection.Find(ctx, bson.D{}, options.Find().SetLimit(limit).SetSkip(skip).SetProjection(bson.D{
		{"_id", 1},
		{"internal_axon_id", 1},
		{"adapters", 1},
		{"tags", 1},
	}))
	if err != nil {
		log.Error().Err(err).Msg("Failed to collect users")
	}
	defer cur.Close(ctx)
	log.Info().Msg("Started finding correlated")
	var cUsers []domain.User
	for cur.Next(ctx) {
		// Mongo returns aggregatedDevice this will be parsed into a correlatedDevice
		var aUser aggregatedUser
		err := cur.Decode(&aUser)
		if err != nil {
			log.Printf("Failed to decode user: %s", err)
			continue
		}
		cUserId, err := uuid.FromString(aUser.InternalAxonId)
		if err != nil {
			log.Fatal().Err(err).Msg("Failed to create axon id")
		}
		users, err := m.parseUsers(cUserId, &aUser)
		if err != nil {
			log.Error().Err(err).Str("id", cUserId.String()).Msg("Failed to parse adapter devices")
			continue
		}

		cUsers = append(cUsers, domain.User{
			Id:              cUserId,
			AdapterUsers:    users,
			AdapterCount:    len(users),
			CorrelationTime: time.Now().UTC(),
		})
	}
	if err := cur.Err(); err != nil {
		log.Fatal().Err(err).Msg("Cursor error")
	}
	return cUsers, nil
}

// Parse devices from an aggregated device
func (m *Repo) parseUsers(cUserId uuid.UUID, aDevice *aggregatedUser) ([]domain.AdapterUser, error) {

	tagToDevice := make(map[string][]domain.Tag)
	for _, tag := range aDevice.Tags {
		if tag.Type == customData {
			log.Debug().Str("user", cUserId.String()).Msg("Skipping custom data")
			continue
		}
		// Go over associated adapters and add tag for them
		for _, associatedAdapters := range tag.AssociatedAdapters {
			adapterId := cast.ToString(associatedAdapters[1])
			tagToDevice[adapterId] = append(tagToDevice[adapterId], domain.Tag{Name: tag.Name})
		}
	}

	var users []domain.AdapterUser
	check := make(map[string]bool)
	for _, adapter := range aDevice.Adapters {
		adapterUser, err := m.parseUser(adapter)
		if err != nil {
			log.Err(err).Str("adapter", adapter.Name).Interface("data", adapter.Data).Msg("failed to parse adapter")
			continue
		}
		// Remove duplicates of same adapter
		if found := check[adapterUser.AdapterName]; found {
			log.Info().Str("adapter", adapter.Name).Msg("removed duplicate adapter")
			continue
		}
		// Add tags to adapter device if it has any
		if id, ok := adapterUser.Data["id"]; ok {
			adapterUser.Tags = append([]domain.Tag(nil), tagToDevice[cast.ToString(id)]...)
		}
		adapterUser.UserId = cUserId
		users = append(users, adapterUser)
		check[adapterUser.AdapterName] = true
	}
	return users, nil
}

// Extract from a single adapter it's device data, it's adapter data and tags associated with it
func (m *Repo) parseUser(adapter adapter) (domain.AdapterUser, error) {
	var ud userData
	bsonBytes, _ := bson.Marshal(adapter.Data)
	err := bson.Unmarshal(bsonBytes, &ud)
	if err != nil {
		log.Error().Err(err).Msg("Failed to decode adapter data")
		return domain.AdapterUser{}, err
	}

	adapterUserId := uuid.NewV4()
	if id, ok := adapter.Data["id"]; ok {
		hash := md5.Sum([]byte(cast.ToString(id)))
		adapterUserId, err = uuid.FromBytes(hash[:])
		if err != nil {
			log.Error().Err(err).Interface("id", id).Msg("Failed to hash adapter device id")
		}
	}

	// Pop keys that were parsed
	for _, key := range userKeysToRemove {
		delete(adapter.Data, key)
	}

	passwordExpires := !ud.PasswordExpires
	passwordRequired := !ud.PasswordRequired

	// TODO: support account expires
	return domain.AdapterUser{
		Id:                     adapterUserId,
		AdapterName:            adapter.Name,
		AdapterId:              domain.GetAdapterTypeByName(adapter.Name),
		Adapter:                domain.Adapter{},
		Client:                 domain.AdapterClient{},
		FetchTime:              internal.EpochFromTime(ud.FetchTime.Time()),
		LastSeen:               internal.EpochFromTime(ud.LastSeen.Time()),
		DisplayName:            ud.DisplayName,
		Description:            ud.Description,
		Domain:                 ud.Domain,
		UserSID:                ud.UserSID,
		Mail:                   ud.Mail,
		Admin:                  ud.Admin,
		Local:                  ud.Local,
		DelegatedAdmin:         ud.DelegatedAdmin,
		MFAEnforced:            ud.MFAEnforced,
		MFAEnrolled:            ud.MFAEnrolled,
		Suspended:              ud.Suspended,
		Locked:                 ud.Locked,
		Disabled:               ud.Disabled,
		CreationDate:           internal.EpochFromTime(ud.CreationDate.Time()),
		LastLogon:              internal.EpochFromTime(ud.LastLogon.Time()),
		LastLogoff:             internal.EpochFromTime(ud.LastLogoff.Time()),
		AccountExpires:         0,
		LastBadLogon:           internal.EpochFromTime(ud.LastBadLogon.Time()),
		LastPasswordChange:     internal.EpochFromTime(ud.LastPasswordChange.Time()),
		LogonCount:             ud.LogonCount,
		Status:                 ud.Status,
		PasswordExpirationDate: internal.EpochFromTime(ud.PasswordExpirationDate.Time()),
		PasswordRequired:       &passwordExpires,
		PasswordExpires:        &passwordRequired,
		FirstName:              ud.FirstName,
		LastName:               ud.LastName,
		Username:               ud.Username,
		OrganizationalUnits:    ud.OrganizationalUnits,
		Groups:                 ud.Groups,
		City:                   ud.City,
		Title:                  ud.Title,
		Department:             ud.Department,
		Manager:                ud.Manager,
		Country:                ud.Country,
		TelephoneNumber:        ud.TelephoneNumber,
		Data:                   adapter.Data,
		UserId:                 uuid.UUID{},
	}, nil
}
