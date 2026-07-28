package store

import (
	"fmt"
	"slices"
	"strings"
	"time"

	"github.com/Fuzzyslippers412/Mycasapro/app/internal/domain"
)

func buildSyntheticTimeline(item domain.ProjectWorkspaceItem, estimates []domain.Estimate, appointments []domain.Appointment, invoices []domain.Invoice, messages []domain.ProjectMessage) []domain.ProjectTimelineEvent {
	events := make([]domain.ProjectTimelineEvent, 0, 3+len(estimates)*2+len(appointments)+len(invoices)*2+len(messages))

	if item.WorkRequest != nil {
		events = append(events, domain.ProjectTimelineEvent{
			ID:          item.WorkRequest.ID + "-opened",
			EventType:   "work_request_opened",
			Title:       "Repair request opened",
			Description: item.WorkRequest.Title,
			CreatedAt:   item.WorkRequest.CreatedAt,
		})
	}

	events = append(events, domain.ProjectTimelineEvent{
		ID:          item.Project.ID + "-created",
		EventType:   "project_created",
		Title:       "Project created",
		Description: "A contractor picked up the request and created a live project workspace.",
		CreatedAt:   item.Project.CreatedAt,
	})

	for _, estimate := range estimates {
		sentAt := estimate.CreatedAt
		if estimate.SentAt != nil {
			sentAt = *estimate.SentAt
		}

		events = append(events, domain.ProjectTimelineEvent{
			ID:          estimate.ID + "-sent",
			EventType:   "estimate_sent",
			Title:       "Estimate sent",
			Description: estimate.Summary + " · " + formatEstimateMoney(estimate.TotalAmountCents),
			CreatedAt:   sentAt,
		})

		if estimate.Status == domain.EstimateStatusApproved && estimate.DecidedAt != nil {
			events = append(events, domain.ProjectTimelineEvent{
				ID:          estimate.ID + "-approved",
				EventType:   "estimate_approved",
				Title:       "Estimate approved",
				Description: defaultEstimateDecisionDescription(estimate.Notes, "Homeowner approved the estimate and unlocked the next project step."),
				CreatedAt:   *estimate.DecidedAt,
			})
		}

		if estimate.Status == domain.EstimateStatusRejected && estimate.DecidedAt != nil {
			events = append(events, domain.ProjectTimelineEvent{
				ID:          estimate.ID + "-rejected",
				EventType:   "estimate_rejected",
				Title:       "Estimate declined",
				Description: defaultEstimateDecisionDescription(estimate.Notes, "Homeowner declined the estimate and the project needs a revised quote."),
				CreatedAt:   *estimate.DecidedAt,
			})
		}
	}

	for _, appointment := range appointments {
		events = append(events, domain.ProjectTimelineEvent{
			ID:          appointment.ID + "-scheduled",
			EventType:   "appointment_scheduled",
			Title:       appointment.Title,
			Description: appointmentWindowDescription(appointment),
			CreatedAt:   appointment.CreatedAt,
		})
	}

	for _, invoice := range invoices {
		events = append(events, domain.ProjectTimelineEvent{
			ID:          invoice.ID + "-issued",
			EventType:   "invoice_issued",
			Title:       "Invoice sent",
			Description: invoice.Summary + " · " + formatEstimateMoney(invoice.AmountCents),
			CreatedAt:   invoice.IssuedAt,
		})

		for _, payment := range invoice.Payments {
			events = append(events, domain.ProjectTimelineEvent{
				ID:          payment.ID + "-recorded",
				EventType:   "payment_recorded",
				Title:       "Payment recorded",
				Description: paymentTimelineDescription(payment),
				CreatedAt:   payment.PaidAt,
			})
		}

		if invoice.Status == domain.InvoiceStatusPaid && invoice.PaidAt != nil {
			events = append(events, domain.ProjectTimelineEvent{
				ID:          invoice.ID + "-paid",
				EventType:   "invoice_paid",
				Title:       "Invoice fully paid",
				Description: invoice.Summary + " is now settled in full.",
				CreatedAt:   *invoice.PaidAt,
			})
		}
	}

	for _, message := range messages {
		events = append(events, domain.ProjectTimelineEvent{
			ID:          message.ID + "-posted",
			EventType:   messageTimelineType(message),
			Title:       messageTimelineTitle(message),
			Description: timelineSnippet(message.Body),
			CreatedAt:   message.CreatedAt,
		})
	}

	events = append(events, domain.ProjectTimelineEvent{
		ID:          item.Project.ID + "-status",
		EventType:   "project_status",
		Title:       "Current status",
		Description: strings.ReplaceAll(string(item.Project.Status), "_", " "),
		CreatedAt:   inferProjectStatusTime(item, estimates),
	})

	slices.SortFunc(events, func(a, b domain.ProjectTimelineEvent) int {
		if compare := a.CreatedAt.Compare(b.CreatedAt); compare != 0 {
			return compare
		}
		return strings.Compare(a.ID, b.ID)
	})

	return events
}

func inferProjectStatusTime(item domain.ProjectWorkspaceItem, estimates []domain.Estimate) time.Time {
	if item.Project.Status == domain.ProjectStatusApproved {
		for _, estimate := range estimates {
			if estimate.Status == domain.EstimateStatusApproved && estimate.DecidedAt != nil {
				return *estimate.DecidedAt
			}
		}
	}
	return item.Project.CreatedAt
}

func defaultEstimateDecisionDescription(notes string, fallback string) string {
	notes = strings.TrimSpace(notes)
	if notes == "" {
		return fallback
	}
	return notes
}

func formatEstimateMoney(cents int64) string {
	return fmt.Sprintf("$%.2f", float64(cents)/100)
}

func paymentTimelineDescription(payment domain.Payment) string {
	base := "Homeowner payment recorded for " + formatEstimateMoney(payment.AmountCents) + "."
	if strings.TrimSpace(payment.Note) == "" {
		return base
	}
	return base + " " + strings.TrimSpace(payment.Note)
}

func messageTimelineType(message domain.ProjectMessage) string {
	if message.Visibility == domain.MessageVisibilityInternal {
		return "internal_note_added"
	}
	return "message_posted"
}

func messageTimelineTitle(message domain.ProjectMessage) string {
	if message.Visibility == domain.MessageVisibilityInternal {
		return "Internal note added"
	}
	return roleLabel(message.AuthorRole) + " posted an update"
}

func timelineSnippet(body string) string {
	body = strings.TrimSpace(body)
	runes := []rune(body)
	if len(runes) <= 120 {
		return body
	}
	return string(runes[:117]) + "..."
}

func roleLabel(role domain.Role) string {
	switch role {
	case domain.RoleHomeowner:
		return "Homeowner"
	case domain.RoleContractor, domain.RoleContractorAdmin, domain.RoleCrewMember:
		return "Contractor"
	default:
		return "User"
	}
}

func appointmentWindowDescription(appointment domain.Appointment) string {
	return fmt.Sprintf(
		"%s to %s",
		appointment.StartsAt.Local().Format("Jan 2, 3:04 PM"),
		appointment.EndsAt.Local().Format("Jan 2, 3:04 PM"),
	)
}
