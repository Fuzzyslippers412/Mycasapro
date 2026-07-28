package store

import (
	"net/mail"
	"strings"
)

const maxGuestEstimateTotalCents int64 = 100_000_000

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
