package httpapi

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"errors"
	"net/http"
	"net/mail"
	"strings"
	"time"

	"github.com/Fuzzyslippers412/Mycasapro/app/internal/domain"
	"github.com/Fuzzyslippers412/Mycasapro/app/internal/store"
	"golang.org/x/crypto/bcrypt"
)

const (
	sessionCookieName = "mycasapro_session"
	sessionTTL        = 30 * 24 * time.Hour
)

type principalContextKey struct{}

type authRequest struct {
	Email       string `json:"email"`
	Password    string `json:"password"`
	DisplayName string `json:"display_name"`
	Role        string `json:"role"`
}

func (s *Server) handleRegister(w http.ResponseWriter, r *http.Request) {
	var req authRequest
	if err := decodeJSON(r, &req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
		return
	}

	email := strings.ToLower(strings.TrimSpace(req.Email))
	displayName := strings.TrimSpace(req.DisplayName)
	role := domain.Role(strings.TrimSpace(req.Role))
	if !validEmail(email) || len(displayName) < 2 || len(displayName) > 80 || !validRegistrationRole(role) {
		writeError(w, http.StatusBadRequest, "invalid_account", "provide a valid name, email, and account type")
		return
	}
	if len(req.Password) < 10 || len(req.Password) > 128 {
		writeError(w, http.StatusBadRequest, "invalid_password", "password must be between 10 and 128 characters")
		return
	}

	passwordHash, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "registration_failed", "unable to secure account password")
		return
	}
	user, err := s.store.CreateUser(r.Context(), store.CreateUserInput{
		Email:        email,
		DisplayName:  displayName,
		Role:         role,
		PasswordHash: string(passwordHash),
	})
	if err != nil {
		switch {
		case errors.Is(err, store.ErrUserExists):
			writeError(w, http.StatusConflict, "account_exists", "an account already exists for this email")
		case errors.Is(err, store.ErrInvalidInput):
			writeError(w, http.StatusBadRequest, "invalid_account", "account details are invalid")
		default:
			writeError(w, http.StatusInternalServerError, "registration_failed", "unable to create account")
		}
		return
	}

	if err := s.startSession(w, r, user); err != nil {
		writeError(w, http.StatusInternalServerError, "session_failed", "account created but sign in failed")
		return
	}
	writeJSON(w, http.StatusCreated, map[string]any{"user": user})
}

func (s *Server) handleLogin(w http.ResponseWriter, r *http.Request) {
	var req authRequest
	if err := decodeJSON(r, &req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
		return
	}

	credentials, err := s.store.GetUserCredentialsByEmail(r.Context(), strings.ToLower(strings.TrimSpace(req.Email)))
	if err != nil || bcrypt.CompareHashAndPassword([]byte(credentials.PasswordHash), []byte(req.Password)) != nil {
		writeError(w, http.StatusUnauthorized, "invalid_credentials", "email or password is incorrect")
		return
	}
	if err := s.startSession(w, r, credentials.User); err != nil {
		writeError(w, http.StatusInternalServerError, "session_failed", "unable to start session")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"user": credentials.User})
}

func (s *Server) handleLogout(w http.ResponseWriter, r *http.Request) {
	if cookie, err := r.Cookie(sessionCookieName); err == nil && strings.TrimSpace(cookie.Value) != "" {
		_ = s.store.DeleteSession(r.Context(), hashSessionToken(cookie.Value))
	}
	http.SetCookie(w, &http.Cookie{
		Name:     sessionCookieName,
		Value:    "",
		Path:     "/",
		HttpOnly: true,
		Secure:   s.cfg.Env == "production",
		SameSite: http.SameSiteLaxMode,
		MaxAge:   -1,
		Expires:  time.Unix(0, 0),
	})
	w.WriteHeader(http.StatusNoContent)
}

func (s *Server) handleCurrentUser(w http.ResponseWriter, r *http.Request) {
	user, ok := currentUser(r.Context())
	if !ok {
		writeError(w, http.StatusUnauthorized, "authentication_required", "sign in to continue")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"user": user})
}

func (s *Server) startSession(w http.ResponseWriter, r *http.Request, user domain.User) error {
	tokenBytes := make([]byte, 32)
	if _, err := rand.Read(tokenBytes); err != nil {
		return err
	}
	rawToken := base64.RawURLEncoding.EncodeToString(tokenBytes)
	expiresAt := time.Now().UTC().Add(sessionTTL)
	if err := s.store.CreateSession(r.Context(), store.CreateSessionInput{
		UserID:    user.ID,
		TokenHash: hashSessionToken(rawToken),
		ExpiresAt: expiresAt,
	}); err != nil {
		return err
	}
	http.SetCookie(w, &http.Cookie{
		Name:     sessionCookieName,
		Value:    rawToken,
		Path:     "/",
		HttpOnly: true,
		Secure:   s.cfg.Env == "production",
		SameSite: http.SameSiteLaxMode,
		Expires:  expiresAt,
		MaxAge:   int(sessionTTL.Seconds()),
	})
	return nil
}

func (s *Server) withRequestPrincipal(r *http.Request) *http.Request {
	if _, ok := currentUser(r.Context()); ok {
		return r
	}
	cookie, err := r.Cookie(sessionCookieName)
	if err != nil || strings.TrimSpace(cookie.Value) == "" {
		return r
	}
	user, err := s.store.GetUserBySessionTokenHash(r.Context(), hashSessionToken(cookie.Value), time.Now().UTC())
	if err != nil {
		return r
	}
	return r.WithContext(context.WithValue(r.Context(), principalContextKey{}, user))
}

func (s *Server) authorizeScopedPath(w http.ResponseWriter, r *http.Request) bool {
	scope, actorID, scoped := scopedActorPath(r.URL.Path)
	if !scoped {
		return true
	}
	user, ok := currentUser(r.Context())
	if !ok {
		writeError(w, http.StatusUnauthorized, "authentication_required", "sign in to continue")
		return false
	}
	if user.ID != actorID {
		writeError(w, http.StatusForbidden, "forbidden", "this account cannot access the requested resource")
		return false
	}
	if scope == "homeowners" && user.Role != domain.RoleHomeowner {
		writeError(w, http.StatusForbidden, "forbidden", "a homeowner account is required")
		return false
	}
	if scope == "contractors" && !isContractorRole(user.Role) {
		writeError(w, http.StatusForbidden, "forbidden", "a contractor account is required")
		return false
	}
	return true
}

func currentUser(ctx context.Context) (domain.User, bool) {
	user, ok := ctx.Value(principalContextKey{}).(domain.User)
	return user, ok && user.ID != ""
}

func scopedActorPath(path string) (string, string, bool) {
	parts := strings.Split(strings.Trim(path, "/"), "/")
	if len(parts) < 4 || parts[0] != "api" || parts[1] != "v1" {
		return "", "", false
	}
	if parts[2] != "homeowners" && parts[2] != "contractors" {
		return "", "", false
	}
	actorID := strings.TrimSpace(parts[3])
	return parts[2], actorID, actorID != ""
}

func validEmail(value string) bool {
	address, err := mail.ParseAddress(value)
	return err == nil && strings.EqualFold(address.Address, value) && strings.Contains(value, "@")
}

func validRegistrationRole(role domain.Role) bool {
	return role == domain.RoleHomeowner || role == domain.RoleContractor
}

func isContractorRole(role domain.Role) bool {
	return role == domain.RoleContractor || role == domain.RoleContractorAdmin || role == domain.RoleCrewMember
}

func hashSessionToken(raw string) string {
	digest := sha256.Sum256([]byte(raw))
	return hex.EncodeToString(digest[:])
}
