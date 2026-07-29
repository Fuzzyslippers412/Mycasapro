package notification

import (
	"fmt"
	"html"
	"strings"
	"time"
)

type Message struct {
	RecipientEmail string
	Subject        string
	TextBody       string
	HTMLBody       string
}

func WorkRequestInvitation(appName, recipientName, shareURL string, expiresAt time.Time) Message {
	appName = strings.TrimSpace(appName)
	if appName == "" {
		appName = "MyCasaPro"
	}
	recipientName = strings.TrimSpace(recipientName)
	greeting := "Hello,"
	if recipientName != "" {
		greeting = "Hello " + recipientName + ","
	}
	expiry := expiresAt.UTC().Format("Monday, January 2 at 3:04 PM MST")
	subject := "A homeowner invited you to review a repair"
	textBody := fmt.Sprintf(`%s

A homeowner shared a private repair request with you through %s. You can review the work, see the shared photos, and submit an estimate without creating an account.

Review the repair: %s

This private link expires %s. Do not forward it to anyone who should not see the repair details.

%s`, greeting, appName, shareURL, expiry, appName)
	htmlBody := fmt.Sprintf(`<!doctype html>
<html><body style="margin:0;background:#f3f0e8;color:#22251f;font-family:Arial,sans-serif">
<div style="max-width:620px;margin:0 auto;padding:36px 20px">
<div style="font-family:Georgia,serif;font-size:24px;font-weight:bold;margin-bottom:32px">%s</div>
<div style="background:#fff;border:1px solid #d4cec1;padding:32px">
<p style="margin:0 0 18px;font-size:16px">%s</p>
<h1 style="font-family:Georgia,serif;font-size:32px;font-weight:normal;line-height:1.1;margin:0 0 18px">Review a repair request</h1>
<p style="color:#64665d;line-height:1.65;margin:0 0 24px">A homeowner shared a private repair request with you. Review the work, see the shared photos, and submit an estimate without creating an account.</p>
<a href="%s" style="display:inline-block;background:#365747;color:#fff;text-decoration:none;padding:13px 18px;font-weight:bold">Review the repair</a>
<p style="color:#777970;font-size:13px;line-height:1.55;margin:24px 0 0">This private link expires %s. Do not forward it to anyone who should not see the repair details.</p>
</div></div></body></html>`, html.EscapeString(appName), html.EscapeString(greeting), html.EscapeString(shareURL), html.EscapeString(expiry))
	return Message{Subject: subject, TextBody: textBody, HTMLBody: htmlBody}
}
