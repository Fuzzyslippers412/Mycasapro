# MyCasa Pro Sprint - Dashboard & Integration Fixes

## Current Issues
1. **Dashboard Status**: Shows "0/9 agents" when agents ARE working (LLM chat works)
2. **No Dashboard Customization**: Can't add/remove widgets
3. **Skills Not Integrated**: Janitor & Finance EdgeLab skills exist but not wired up
4. **System State**: "Running: False" even though everything works

## Tasks

### 1. Fix Agent Status Display (15 min)
- [ ] Update `/system/monitor` to reflect actual agent state (responding = active)
- [ ] Fix "running" state logic - if chat works, system is running

### 2. Dashboard Customization (30 min)
- [ ] Add widget manager to Settings > Dashboard
- [ ] Store widget preferences in localStorage + backend
- [ ] Available widgets: Status, Agents, Finance, Tasks, Projects, Calendar, Chat

### 3. Integrate Janitor Skill (20 min)
- [ ] Wire up Janitor's `full_audit()` to dashboard
- [ ] Add "Run Audit" button to System page
- [ ] Show audit results in dashboard widget

### 4. Integrate Finance EdgeLab (20 min)
- [ ] Wire up portfolio pipeline to Finance dashboard
- [ ] Add portfolio summary widget
- [ ] Connect to real yfinance data

### 5. Polish (15 min)
- [ ] Fix any remaining status indicators
- [ ] Test all features work end-to-end

## Execution Order
1. Fix status API first (everything depends on this)
2. Dashboard customization
3. Skills integration
4. Polish
