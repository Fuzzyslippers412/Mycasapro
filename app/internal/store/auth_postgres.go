package store

import (
	"context"
	"database/sql"
	"errors"
	"strings"
	"time"

	"github.com/Fuzzyslippers412/Mycasapro/app/internal/domain"
	"github.com/jackc/pgx/v5/pgconn"
)

func (s *PostgresStore) CreateUser(ctx context.Context, input CreateUserInput) (domain.User, error) {
	email := strings.ToLower(strings.TrimSpace(input.Email))
	displayName := strings.TrimSpace(input.DisplayName)
	passwordHash := strings.TrimSpace(input.PasswordHash)
	if email == "" || displayName == "" || passwordHash == "" || !isRegistrationRole(input.Role) {
		return domain.User{}, ErrInvalidInput
	}

	user := domain.User{
		ID:          newID("usr"),
		Email:       email,
		DisplayName: displayName,
		Role:        input.Role,
		CreatedAt:   time.Now().UTC(),
	}
	_, err := s.db.ExecContext(ctx, `
		insert into users (id, email, display_name, role, password_hash, created_at)
		values ($1,$2,$3,$4,$5,$6)
	`, user.ID, user.Email, user.DisplayName, string(user.Role), passwordHash, user.CreatedAt)
	if err != nil {
		var pgErr *pgconn.PgError
		if errors.As(err, &pgErr) && pgErr.Code == "23505" {
			return domain.User{}, ErrUserExists
		}
		return domain.User{}, err
	}
	return user, nil
}

func (s *PostgresStore) GetUserByID(ctx context.Context, userID string) (domain.User, error) {
	return scanAuthUser(s.db.QueryRowContext(ctx, `
		select id, email, display_name, role, created_at
		from users
		where id = $1 and password_hash is not null
	`, strings.TrimSpace(userID)))
}

func (s *PostgresStore) GetUserCredentialsByEmail(ctx context.Context, email string) (UserCredentials, error) {
	var credentials UserCredentials
	var role string
	err := s.db.QueryRowContext(ctx, `
		select id, email, display_name, role, created_at, password_hash
		from users
		where lower(email) = lower($1) and password_hash is not null
	`, strings.TrimSpace(email)).Scan(
		&credentials.User.ID,
		&credentials.User.Email,
		&credentials.User.DisplayName,
		&role,
		&credentials.User.CreatedAt,
		&credentials.PasswordHash,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return UserCredentials{}, ErrUserNotFound
	}
	if err != nil {
		return UserCredentials{}, err
	}
	credentials.User.Role = domain.Role(role)
	return credentials, nil
}

func (s *PostgresStore) CreateSession(ctx context.Context, input CreateSessionInput) error {
	if strings.TrimSpace(input.UserID) == "" || strings.TrimSpace(input.TokenHash) == "" || input.ExpiresAt.IsZero() {
		return ErrInvalidInput
	}
	_, err := s.db.ExecContext(ctx, `
		insert into sessions (id, user_id, token_hash, expires_at, created_at)
		values ($1,$2,$3,$4,$5)
	`, newID("ses"), strings.TrimSpace(input.UserID), strings.TrimSpace(input.TokenHash), input.ExpiresAt.UTC(), time.Now().UTC())
	return err
}

func (s *PostgresStore) GetUserBySessionTokenHash(ctx context.Context, tokenHash string, now time.Time) (domain.User, error) {
	return scanAuthUser(s.db.QueryRowContext(ctx, `
		select u.id, u.email, u.display_name, u.role, u.created_at
		from sessions s
		join users u on u.id = s.user_id
		where s.token_hash = $1 and s.expires_at > $2 and u.password_hash is not null
	`, strings.TrimSpace(tokenHash), now.UTC()))
}

func (s *PostgresStore) DeleteSession(ctx context.Context, tokenHash string) error {
	_, err := s.db.ExecContext(ctx, `delete from sessions where token_hash = $1`, strings.TrimSpace(tokenHash))
	return err
}

func scanAuthUser(scanner interface{ Scan(...any) error }) (domain.User, error) {
	var user domain.User
	var role string
	err := scanner.Scan(&user.ID, &user.Email, &user.DisplayName, &role, &user.CreatedAt)
	if errors.Is(err, sql.ErrNoRows) {
		return domain.User{}, ErrUserNotFound
	}
	if err != nil {
		return domain.User{}, err
	}
	user.Role = domain.Role(role)
	return user, nil
}
