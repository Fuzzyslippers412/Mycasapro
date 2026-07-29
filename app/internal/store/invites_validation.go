package store

import (
	"net/mail"
	"strings"
)

const (
	maxGuestEstimateTotalCents int64 = 100_000_000
	maxEmailInvitesPerHour           = 20
)

func normalizeWorkRequestInviteInput(input CreateWorkRequestInviteInput) (CreateWorkRequestInviteInput, bool) {
	input.HomeownerUserID = strings.TrimSpace(input.HomeownerUserID)
	input.WorkRequestID = strings.TrimSpace(input.WorkRequestID)
	input.TokenHash = strings.TrimSpace(input.TokenHash)
	input.RecipientName = strings.TrimSpace(input.RecipientName)
	input.EmailSubject = strings.TrimSpace(input.EmailSubject)
	input.EmailTextBody = strings.TrimSpace(input.EmailTextBody)
	input.EmailHTMLBody = strings.TrimSpace(input.EmailHTMLBody)

	if input.HomeownerUserID == "" || input.WorkRequestID == "" || len(input.TokenHash) != 64 ||
		len(input.RecipientName) > 120 || len(input.EmailSubject) > 300 || len(input.EmailTextBody) > 100_000 || len(input.EmailHTMLBody) > 200_000 {
		return CreateWorkRequestInviteInput{}, false
	}
	if strings.TrimSpace(input.RecipientEmail) == "" {
		if input.EmailSubject != "" || input.EmailTextBody != "" || input.EmailHTMLBody != "" {
			return CreateWorkRequestInviteInput{}, false
		}
		input.RecipientEmail = ""
		return input, true
	}

	var emailOK bool
	input.RecipientEmail, emailOK = normalizeGuestEmail(input.RecipientEmail)
	if !emailOK || len(input.RecipientEmail) > 320 || input.EmailSubject == "" || input.EmailTextBody == "" || input.EmailHTMLBody == "" {
		return CreateWorkRequestInviteInput{}, false
	}
	return input, true
}

func normalizeGuestEmail(value string) (string, bool) {
	email := strings.ToLower(strings.TrimSpace(value))
	address, err := mail.ParseAddress(email)
	return email, err == nil && strings.EqualFold(address.Address, email) && strings.Contains(email, "@")
}

func normalizeGuestEstimateInput(input CreateGuestEstimateInput) (CreateGuestEstimateInput, int64, bool) {
	input.ContractorName = strings.TrimSpace(input.ContractorName)
	input.BusinessName = strings.TrimSpace(input.BusinessName)
	input.Summary = strings.TrimSpace(input.Summary)
	input.Notes = strings.TrimSpace(input.Notes)
	input.AvailableTiming = strings.TrimSpace(input.AvailableTiming)
	var emailOK bool
	input.Email, emailOK = normalizeGuestEmail(input.Email)
	if input.ContractorName == "" || len(input.ContractorName) > 120 || len(input.BusinessName) > 160 || !emailOK || len(input.Email) > 320 ||
		input.Summary == "" || len(input.Summary) > 5000 || len(input.Notes) > 5000 || len(input.AvailableTiming) > 500 ||
		len(input.LineItems) == 0 || len(input.LineItems) > 12 {
		return CreateGuestEstimateInput{}, 0, false
	}
	var total int64
	for index := range input.LineItems {
		input.LineItems[index].Label = strings.TrimSpace(input.LineItems[index].Label)
		item := input.LineItems[index]
		if item.Label == "" || len(item.Label) > 200 || item.AmountCents < 0 || item.AmountCents > maxGuestEstimateTotalCents || total > maxGuestEstimateTotalCents-item.AmountCents {
			return CreateGuestEstimateInput{}, 0, false
		}
		total += item.AmountCents
	}
	return input, total, true
}
