# HEARTBEAT.md - Proactive Check Tasks

*This file tells your agent what to check proactively, 2-4 times per day.*

---

## How This Works

Your agent will read this file during heartbeat polls and rotate through the checks below. It won't run all checks every time — that would be wasteful. Instead, it tracks what was last checked and picks what's due.

**Heartbeat prompt:** "Read HEARTBEAT.md if it exists. Follow it strictly. Do not infer or repeat old tasks. If nothing needs attention, reply HEARTBEAT_OK."

---

## Checks to Rotate Through

### High Frequency (Every 4-6 hours)
- [ ] **Email inbox** - Any urgent unread messages?
- [ ] **Security system** - Any alerts or unusual activity?
- [ ] **Weather** - Any alerts relevant to the house? (freeze, storm, heat)

### Medium Frequency (Every 12-24 hours)
- [ ] **Calendar** - Events in next 24-48h that need prep?
- [ ] **Bills due** - Anything due in next 7 days?
- [ ] **Maintenance tasks** - Any overdue or coming due?

### Low Frequency (Weekly)
- [ ] **Portfolio check** - Any positions moved >5%?
- [ ] **Subscription audit** - Any renewals coming up?
- [ ] **Home readings** - Water, gas, electric trends normal?

---

## Quiet Hours

**Do NOT notify unless CRITICAL during:**
- **Start:** 23:00 (11 PM)
- **End:** 08:00 (8 AM)

Critical = Security breach, water leak, fire alarm, power outage

---

## When to Reach Out

**Notify immediately:**
- Security incident (alarm, camera motion, door opened)
- Water/gas leak detected
- Power outage
- Critical bill overdue (>7 days)
- Emergency maintenance needed (no heat in winter, AC in summer, etc.)

**Batch for next check-in:**
- Non-urgent maintenance reminders
- Upcoming appointments (24-48h notice)
- Bills due in 3-7 days
- General recommendations

**Stay silent (HEARTBEAT_OK):**
- Everything is normal
- Nothing new since last check
- Just checked <30 minutes ago
- Late night + nothing critical

---

## Memory Maintenance

**Every few days (during a heartbeat):**
1. Read recent `memory/YYYY-MM-DD.md` files (last 7 days)
2. Identify significant events, decisions, lessons
3. Update `MEMORY.md` with distilled learnings
4. Remove outdated info from MEMORY.md

Think of it like a human reviewing their journal and updating their mental model. Daily files are raw notes; MEMORY.md is curated wisdom.

---

## State Tracking

Track your checks in `memory/heartbeat-state.json`:

```json
{
  "lastChecks": {
    "email": 1703275200,
    "calendar": 1703260800,
    "weather": 1703270000,
    "bills": 1703180000,
    "maintenance": 1703100000,
    "security": 1703275200,
    "portfolio": 1703150000
  },
  "lastConsolidation": 1703000000
}
```

---

## Custom Checks for This Household

*Add household-specific checks here:*

- [ ] [e.g., "Check pool pH levels (test kit in garage)"]
- [ ] [e.g., "Monitor garden soil moisture sensors"]
- [ ] [e.g., "Check basement sump pump status"]
- [ ] [Add your own]

---

*The goal: Be helpful without being annoying. Check in a few times a day, do useful background work, but respect quiet time.*
