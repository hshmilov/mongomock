package pg

import (
	"bandicoot/pkg/domain"
	"context"
	sq "github.com/Masterminds/squirrel"
	"github.com/rs/zerolog/log"
)

func (p *Repo) InsertAdapterUser(ctx context.Context, ud domain.AdapterUser) error {
	q := sq.Insert("adapter_users").Columns(
		"id", "fetch_cycle", "adapter_name", "adapter_id", "user_id",
		"data", "last_seen", "fetch_time", "display_name", "description", "domain", "user_sid",
		"mail", "admin", "local", "delegated_admin", "mfa_enforced", "mfa_enrolled", "suspended", "locked", "disabled",
		"creation_date", "last_logon", "last_logoff", "account_expires", "last_bad_logon", "last_password_change",
		"logon_count", "status", "password_expiration_date", "password_expires",
		"password_required", "first_name", "last_name", "username", "organizational_units", "groups").Values(
		ud.Id.String(), ud.FetchCycle, ud.AdapterName, ud.AdapterId, ud.UserId,
		ud.Data, ud.LastSeen, ud.FetchTime, ud.DisplayName, ud.Description, ud.Domain, ud.UserSID,
		ud.Mail, ud.Admin, ud.Local, ud.DelegatedAdmin, ud.MFAEnforced, ud.MFAEnrolled, ud.Suspended,
		ud.Locked, ud.Disabled, ud.CreationDate, ud.LastLogon, ud.LastLogoff, ud.AccountExpires, ud.LastBadLogon,
		ud.LastPasswordChange, ud.LogonCount, ud.Status, ud.PasswordExpirationDate, ud.PasswordExpires,
		ud.PasswordRequired, ud.FirstName, ud.LastName, ud.Username, ud.OrganizationalUnits, ud.Groups,
	).PlaceholderFormat(sq.Dollar).Suffix("ON CONFLICT DO NOTHING")

	sql, args, err := q.ToSql()
	if err != nil {
		log.Error().Err(err).Msg("Failed to build adapter user insert query")
		return err
	}
	_, err = p.pool.Exec(ctx, sql, args...)
	if err != nil {
		log.Trace().Str("query", sql).Interface("args", args).Err(err).Msg("Failed to insert user")
		return err
	}
	return nil
}
