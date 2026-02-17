-- Agent Snapshots Table
-- Immutable audit trail of all agent invocations
--
-- This table implements complete provenance tracking:
-- - What was the input?
-- - What did the agent propose?
-- - What did policy decide?
-- - What tools were executed?
-- - What was the result?

CREATE TABLE IF NOT EXISTS agent_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,
    agent_version TEXT NOT NULL,
    request_id UUID NOT NULL,

    -- Input provenance
    input_hash TEXT NOT NULL,  -- SHA-256 of input envelope
    trusted_user_request TEXT,  -- T0 content
    untrusted_evidence_refs JSONB,  -- References only, not content
    request_context JSONB NOT NULL,  -- user_id, org_id, origin, auth

    -- Agent output
    output_hash TEXT NOT NULL,  -- SHA-256 of output envelope
    action_intents JSONB NOT NULL,  -- Proposed intents

    -- Policy decision
    policy_decision JSONB NOT NULL,  -- Policy evaluation result
    policy_agent_version TEXT,

    -- Tool executions (if any)
    tool_executions JSONB,  -- Array of {tool, operation, result, token_id}

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    runtime_seconds REAL,
    success BOOLEAN,
    error_message TEXT,

    -- Indexes for common queries
    CONSTRAINT fk_request FOREIGN KEY (request_id) REFERENCES agent_snapshots(request_id) ON DELETE CASCADE
);

-- Index for agent-based queries
CREATE INDEX IF NOT EXISTS idx_agent_snapshots_agent_id ON agent_snapshots(agent_id, created_at DESC);

-- Index for request-based queries
CREATE INDEX IF NOT EXISTS idx_agent_snapshots_request_id ON agent_snapshots(request_id);

-- Index for time-based queries
CREATE INDEX IF NOT EXISTS idx_agent_snapshots_created_at ON agent_snapshots(created_at DESC);

-- Index for error queries
CREATE INDEX IF NOT EXISTS idx_agent_snapshots_success ON agent_snapshots(success, created_at DESC);

-- GIN index for JSONB queries
CREATE INDEX IF NOT EXISTS idx_agent_snapshots_policy_decision ON agent_snapshots USING GIN (policy_decision);
CREATE INDEX IF NOT EXISTS idx_agent_snapshots_tool_executions ON agent_snapshots USING GIN (tool_executions);

-- Partial index for failed snapshots
CREATE INDEX IF NOT EXISTS idx_agent_snapshots_failures ON agent_snapshots(agent_id, created_at DESC) WHERE success = false;

-- Comments for documentation
COMMENT ON TABLE agent_snapshots IS 'Immutable audit trail of all agent invocations with complete provenance';
COMMENT ON COLUMN agent_snapshots.input_hash IS 'SHA-256 hash of input envelope for integrity verification';
COMMENT ON COLUMN agent_snapshots.output_hash IS 'SHA-256 hash of output envelope for integrity verification';
COMMENT ON COLUMN agent_snapshots.untrusted_evidence_refs IS 'References to evidence bundles (never actual content)';
COMMENT ON COLUMN agent_snapshots.policy_decision IS 'Complete policy evaluation result including all decisions';
COMMENT ON COLUMN agent_snapshots.tool_executions IS 'Array of tool executions with results and capability tokens used';

-- View for security audit
CREATE OR REPLACE VIEW agent_audit_trail AS
SELECT
    snapshot_id,
    agent_id,
    request_id,
    created_at,
    request_context->>'user_id' as user_id,
    request_context->>'origin' as origin,
    request_context->>'auth_strength' as auth_strength,
    policy_decision->>'decision' as policy_decision,
    policy_decision->>'risk_level' as risk_level,
    jsonb_array_length(COALESCE(tool_executions, '[]'::jsonb)) as tool_execution_count,
    success,
    error_message
FROM agent_snapshots
ORDER BY created_at DESC;

COMMENT ON VIEW agent_audit_trail IS 'Simplified view for security auditing';

-- Function to get snapshot by request_id
CREATE OR REPLACE FUNCTION get_agent_snapshot(p_request_id UUID)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'snapshot_id', snapshot_id,
        'agent_id', agent_id,
        'request_id', request_id,
        'input_hash', input_hash,
        'output_hash', output_hash,
        'trusted_user_request', trusted_user_request,
        'action_intents', action_intents,
        'policy_decision', policy_decision,
        'tool_executions', tool_executions,
        'created_at', created_at,
        'success', success,
        'error_message', error_message
    ) INTO result
    FROM agent_snapshots
    WHERE request_id = p_request_id;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Function to get agent execution history
CREATE OR REPLACE FUNCTION get_agent_history(p_agent_id TEXT, p_limit INT DEFAULT 100)
RETURNS TABLE (
    snapshot_id UUID,
    request_id UUID,
    created_at TIMESTAMPTZ,
    success BOOLEAN,
    policy_decision TEXT,
    risk_level TEXT,
    tool_count INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.snapshot_id,
        s.request_id,
        s.created_at,
        s.success,
        s.policy_decision->>'decision' as policy_decision,
        s.policy_decision->>'risk_level' as risk_level,
        jsonb_array_length(COALESCE(s.tool_executions, '[]'::jsonb)) as tool_count
    FROM agent_snapshots s
    WHERE s.agent_id = p_agent_id
    ORDER BY s.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Trigger to prevent updates (immutable audit trail)
CREATE OR REPLACE FUNCTION prevent_snapshot_updates()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Agent snapshots are immutable and cannot be updated';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER agent_snapshots_immutable
BEFORE UPDATE ON agent_snapshots
FOR EACH ROW
EXECUTE FUNCTION prevent_snapshot_updates();

-- Grant appropriate permissions
-- Agents can INSERT (create snapshots)
-- Security/audit roles can SELECT
-- NO ONE can UPDATE or DELETE (immutable)

-- Example permissions (adjust for your roles):
-- GRANT INSERT ON agent_snapshots TO agent_role;
-- GRANT SELECT ON agent_snapshots TO security_role;
-- GRANT SELECT ON agent_audit_trail TO audit_role;
