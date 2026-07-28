package store

import "testing"

func TestNormalizeGuestEstimateInput(t *testing.T) {
	input, total, ok := normalizeGuestEstimateInput(CreateGuestEstimateInput{
		ContractorName: "  Morgan Lee  ", Email: " MORGAN@EXAMPLE.COM ", Summary: "  Replace the valve. ",
		LineItems: []GuestEstimateLineItemInput{{Label: " Labor ", AmountCents: 24000}, {Label: "Parts", AmountCents: 6500}},
	})
	if !ok || total != 30500 || input.ContractorName != "Morgan Lee" || input.Email != "morgan@example.com" || input.LineItems[0].Label != "Labor" {
		t.Fatalf("valid estimate was not normalized: ok=%v total=%d input=%+v", ok, total, input)
	}

	invalidCases := []CreateGuestEstimateInput{
		{ContractorName: "Morgan", Email: "not-an-email", Summary: "Work", LineItems: []GuestEstimateLineItemInput{{Label: "Labor", AmountCents: 100}}},
		{ContractorName: "Morgan", Email: "morgan@example.com", Summary: "Work", LineItems: []GuestEstimateLineItemInput{{Label: "Labor", AmountCents: maxGuestEstimateTotalCents + 1}}},
		{ContractorName: "Morgan", Email: "morgan@example.com", Summary: "Work", LineItems: []GuestEstimateLineItemInput{{Label: "Labor", AmountCents: maxGuestEstimateTotalCents}, {Label: "Parts", AmountCents: 1}}},
	}
	for index, invalid := range invalidCases {
		if _, _, ok := normalizeGuestEstimateInput(invalid); ok {
			t.Fatalf("invalid estimate case %d was accepted", index)
		}
	}
}
