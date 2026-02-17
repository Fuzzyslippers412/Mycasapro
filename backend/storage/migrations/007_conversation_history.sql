-- Migration 007: Conversation History for Agent Chats
-- Creates tables for storing agent conversation history with messages
-- Author: Claude Sonnet 4.5
-- Date: 2026-01-31

-- ==================== CONVERSATIONS TABLE ====================

CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(50) UNIQUE NOT NULL,

    -- Agent and user identifiers
    agent_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL DEFAULT 'lamido',

    -- Conversation metadata
    title VARCHAR(500),
    context JSONB DEFAULT '{}',

    -- Status tracking
    status VARCHAR(20) NOT NULL DEFAULT 'active',

    -- Statistics
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    archived_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT conversations_status_check CHECK (status IN ('active', 'archived', 'deleted'))
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS ix_conversations_agent_id ON conversations(agent_id);
CREATE INDEX IF NOT EXISTS ix_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS ix_conversations_created_at ON conversations(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_conversations_status ON conversations(status);
CREATE INDEX IF NOT EXISTS ix_conversations_conversation_id ON conversations(conversation_id);

-- Composite index for agent+user queries
CREATE INDEX IF NOT EXISTS ix_conversations_agent_user ON conversations(agent_id, user_id, created_at DESC);


-- ==================== MESSAGES TABLE ====================

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(50) UNIQUE NOT NULL,

    -- Foreign key to conversation
    conversation_id VARCHAR(50) NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,

    -- Message content
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,

    -- Message metadata
    tokens INTEGER DEFAULT 0,
    model_used VARCHAR(100),
    latency_ms INTEGER,

    -- Tool usage tracking
    tool_calls JSONB DEFAULT '[]',
    tool_results JSONB DEFAULT '[]',

    -- Error tracking
    error TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT messages_role_check CHECK (role IN ('user', 'assistant', 'system'))
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS ix_messages_conversation_id ON messages(conversation_id, created_at ASC);
CREATE INDEX IF NOT EXISTS ix_messages_created_at ON messages(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_messages_role ON messages(role);
CREATE INDEX IF NOT EXISTS ix_messages_message_id ON messages(message_id);

-- Composite index for conversation history retrieval
CREATE INDEX IF NOT EXISTS ix_messages_conversation_order ON messages(conversation_id, created_at ASC, id ASC);


-- ==================== TRIGGERS ====================

-- Update conversation updated_at timestamp when messages are added
CREATE OR REPLACE FUNCTION update_conversation_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversations
    SET updated_at = NOW(),
        message_count = (
            SELECT COUNT(*)
            FROM messages
            WHERE conversation_id = NEW.conversation_id
            AND deleted_at IS NULL
        ),
        total_tokens = (
            SELECT COALESCE(SUM(tokens), 0)
            FROM messages
            WHERE conversation_id = NEW.conversation_id
            AND deleted_at IS NULL
        )
    WHERE conversation_id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER messages_update_conversation
AFTER INSERT ON messages
FOR EACH ROW
EXECUTE FUNCTION update_conversation_timestamp();


-- Auto-generate conversation title from first user message
CREATE OR REPLACE FUNCTION auto_generate_conversation_title()
RETURNS TRIGGER AS $$
BEGIN
    -- Only generate title if it's the first user message and no title exists
    IF NEW.role = 'user' THEN
        UPDATE conversations
        SET title = COALESCE(
            title,
            CASE
                WHEN LENGTH(NEW.content) > 100
                THEN SUBSTRING(NEW.content FROM 1 FOR 97) || '...'
                ELSE NEW.content
            END
        )
        WHERE conversation_id = NEW.conversation_id
        AND title IS NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER messages_auto_title
AFTER INSERT ON messages
FOR EACH ROW
EXECUTE FUNCTION auto_generate_conversation_title();


-- ==================== VIEWS ====================

-- Active conversations summary
CREATE OR REPLACE VIEW active_conversations AS
SELECT
    c.conversation_id,
    c.agent_id,
    c.user_id,
    c.title,
    c.message_count,
    c.total_tokens,
    c.created_at,
    c.updated_at,
    (
        SELECT content
        FROM messages
        WHERE conversation_id = c.conversation_id
        AND deleted_at IS NULL
        AND role = 'user'
        ORDER BY created_at DESC
        LIMIT 1
    ) as last_user_message,
    (
        SELECT created_at
        FROM messages
        WHERE conversation_id = c.conversation_id
        AND deleted_at IS NULL
        ORDER BY created_at DESC
        LIMIT 1
    ) as last_message_at
FROM conversations c
WHERE c.status = 'active'
ORDER BY c.updated_at DESC;


-- Agent conversation statistics
CREATE OR REPLACE VIEW agent_conversation_stats AS
SELECT
    agent_id,
    COUNT(*) as total_conversations,
    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_conversations,
    SUM(message_count) as total_messages,
    SUM(total_tokens) as total_tokens,
    MAX(updated_at) as last_activity
FROM conversations
GROUP BY agent_id;


-- User conversation history
CREATE OR REPLACE VIEW user_conversation_history AS
SELECT
    c.conversation_id,
    c.agent_id,
    c.title,
    c.message_count,
    c.created_at,
    c.updated_at,
    c.status,
    COUNT(m.id) as visible_messages
FROM conversations c
LEFT JOIN messages m ON c.conversation_id = m.conversation_id AND m.deleted_at IS NULL
GROUP BY c.conversation_id, c.agent_id, c.title, c.message_count, c.created_at, c.updated_at, c.status
ORDER BY c.updated_at DESC;


-- ==================== FUNCTIONS ====================

-- Get conversation history with pagination
CREATE OR REPLACE FUNCTION get_conversation_messages(
    p_conversation_id VARCHAR(50),
    p_limit INTEGER DEFAULT 100,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    message_id VARCHAR(50),
    role VARCHAR(20),
    content TEXT,
    tokens INTEGER,
    model_used VARCHAR(100),
    tool_calls JSONB,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.message_id,
        m.role,
        m.content,
        m.tokens,
        m.model_used,
        m.tool_calls,
        m.created_at
    FROM messages m
    WHERE m.conversation_id = p_conversation_id
    AND m.deleted_at IS NULL
    ORDER BY m.created_at ASC, m.id ASC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql;


-- Search conversations by content
CREATE OR REPLACE FUNCTION search_conversations(
    p_agent_id VARCHAR(50),
    p_user_id VARCHAR(50),
    p_search_term TEXT,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    conversation_id VARCHAR(50),
    title VARCHAR(500),
    message_count INTEGER,
    last_updated TIMESTAMPTZ,
    matching_messages BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.conversation_id,
        c.title,
        c.message_count,
        c.updated_at,
        COUNT(m.id) as matching_messages
    FROM conversations c
    JOIN messages m ON c.conversation_id = m.conversation_id
    WHERE c.agent_id = p_agent_id
    AND c.user_id = p_user_id
    AND c.status = 'active'
    AND m.deleted_at IS NULL
    AND m.content ILIKE '%' || p_search_term || '%'
    GROUP BY c.conversation_id, c.title, c.message_count, c.updated_at
    ORDER BY c.updated_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;


-- Archive old conversations
CREATE OR REPLACE FUNCTION archive_old_conversations(
    p_days_inactive INTEGER DEFAULT 90
)
RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    WITH archived AS (
        UPDATE conversations
        SET status = 'archived',
            archived_at = NOW()
        WHERE status = 'active'
        AND updated_at < NOW() - (p_days_inactive || ' days')::INTERVAL
        RETURNING *
    )
    SELECT COUNT(*) INTO archived_count FROM archived;

    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;


-- ==================== COMMENTS ====================

COMMENT ON TABLE conversations IS 'Agent conversation sessions with users';
COMMENT ON TABLE messages IS 'Individual messages within conversations';
COMMENT ON COLUMN conversations.conversation_id IS 'Unique identifier for the conversation';
COMMENT ON COLUMN conversations.agent_id IS 'ID of the agent participating in conversation';
COMMENT ON COLUMN conversations.context IS 'Additional metadata and context for the conversation';
COMMENT ON COLUMN messages.tool_calls IS 'JSON array of tool calls made during message generation';
COMMENT ON COLUMN messages.tool_results IS 'JSON array of results from tool executions';
COMMENT ON COLUMN messages.deleted_at IS 'Soft delete timestamp for GDPR compliance';
