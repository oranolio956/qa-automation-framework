-- Anti-Bot Security Framework Database Schema
-- Optimized for high-performance transactional workloads

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create custom types
CREATE TYPE risk_level AS ENUM ('low', 'medium', 'high', 'critical');
CREATE TYPE verification_status AS ENUM ('pending', 'sent', 'verified', 'failed', 'expired');
CREATE TYPE action_type AS ENUM ('allow', 'challenge', 'block', 'monitor');

-- Users and sessions table
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_user_id VARCHAR(255) UNIQUE NOT NULL,
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    total_sessions INTEGER DEFAULT 0,
    risk_profile JSONB DEFAULT '{}',
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Sessions table for tracking user sessions
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    external_session_id VARCHAR(255) UNIQUE NOT NULL,
    ip_address INET NOT NULL,
    user_agent TEXT,
    device_fingerprint JSONB DEFAULT '{}',
    geolocation JSONB DEFAULT '{}',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    page_views INTEGER DEFAULT 0,
    events_count INTEGER DEFAULT 0,
    final_risk_score DECIMAL(4,3),
    final_action action_type,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Risk assessments table (from data-processor)
CREATE TABLE risk_assessments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    risk_score DECIMAL(4,3) NOT NULL CHECK (risk_score >= 0 AND risk_score <= 1),
    risk_level risk_level NOT NULL,
    risk_factors JSONB DEFAULT '{}',
    model_version VARCHAR(50) NOT NULL,
    model_confidence DECIMAL(4,3) NOT NULL,
    processing_time_ms INTEGER,
    features_used JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- SMS verifications table (from data-processor)  
CREATE TABLE sms_verifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    message_id VARCHAR(255) UNIQUE NOT NULL,
    phone_number_hash VARCHAR(64) NOT NULL,
    verification_code_hash VARCHAR(64),
    status verification_status NOT NULL DEFAULT 'pending',
    provider VARCHAR(20) NOT NULL,
    provider_message_id VARCHAR(255),
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    delivered_at TIMESTAMP WITH TIME ZONE,
    verified_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    retry_count INTEGER DEFAULT 0,
    cost DECIMAL(10,4),
    failure_reason TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Challenge responses table
CREATE TABLE challenge_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    challenge_type VARCHAR(50) NOT NULL, -- 'captcha', 'sms', 'email', 'behavioral'
    challenge_data JSONB DEFAULT '{}',
    response_data JSONB DEFAULT '{}',
    is_successful BOOLEAN NOT NULL,
    response_time_ms INTEGER,
    attempts_count INTEGER DEFAULT 1,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Pattern recognition events
CREATE TABLE pattern_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pattern_type VARCHAR(100) NOT NULL,
    pattern_name VARCHAR(255) NOT NULL,
    anomaly_score DECIMAL(4,3) NOT NULL,
    affected_users_count INTEGER DEFAULT 0,
    affected_sessions UUID[] DEFAULT '{}',
    pattern_data JSONB DEFAULT '{}',
    confidence_level DECIMAL(4,3) NOT NULL,
    severity risk_level NOT NULL,
    detection_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    false_positive BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- System performance metrics
CREATE TABLE performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,6) NOT NULL,
    metric_unit VARCHAR(20),
    service_name VARCHAR(50) NOT NULL,
    instance_id VARCHAR(100),
    tags JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audit log table for compliance
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    session_id UUID REFERENCES sessions(session_id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(255),
    resource_id VARCHAR(255),
    result VARCHAR(50) NOT NULL, -- 'success', 'failure', 'error'
    ip_address INET,
    user_agent TEXT,
    request_id VARCHAR(100),
    processing_time_ms INTEGER,
    error_details TEXT,
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
-- Users indexes
CREATE INDEX idx_users_external_id ON users(external_user_id);
CREATE INDEX idx_users_last_seen ON users(last_seen_at DESC);
CREATE INDEX idx_users_verified ON users(is_verified) WHERE is_verified = TRUE;
CREATE INDEX idx_users_risk_profile ON users USING GIN(risk_profile);

-- Sessions indexes  
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_external_id ON sessions(external_session_id);
CREATE INDEX idx_sessions_ip ON sessions(ip_address);
CREATE INDEX idx_sessions_started ON sessions(started_at DESC);
CREATE INDEX idx_sessions_risk_score ON sessions(final_risk_score DESC) WHERE final_risk_score IS NOT NULL;
CREATE INDEX idx_sessions_fingerprint ON sessions USING GIN(device_fingerprint);

-- Risk assessments indexes
CREATE INDEX idx_risk_session_id ON risk_assessments(session_id);
CREATE INDEX idx_risk_user_id ON risk_assessments(user_id);
CREATE INDEX idx_risk_score ON risk_assessments(risk_score DESC);
CREATE INDEX idx_risk_level ON risk_assessments(risk_level);
CREATE INDEX idx_risk_created ON risk_assessments(created_at DESC);
CREATE INDEX idx_risk_model ON risk_assessments(model_version);
CREATE INDEX idx_risk_factors ON risk_assessments USING GIN(risk_factors);

-- SMS verifications indexes
CREATE INDEX idx_sms_message_id ON sms_verifications(message_id);
CREATE INDEX idx_sms_user_id ON sms_verifications(user_id);
CREATE INDEX idx_sms_session_id ON sms_verifications(session_id);
CREATE INDEX idx_sms_phone_hash ON sms_verifications(phone_number_hash);
CREATE INDEX idx_sms_status ON sms_verifications(status);
CREATE INDEX idx_sms_provider ON sms_verifications(provider);
CREATE INDEX idx_sms_sent_at ON sms_verifications(sent_at DESC);
CREATE INDEX idx_sms_expires_at ON sms_verifications(expires_at) WHERE expires_at IS NOT NULL;

-- Challenge responses indexes
CREATE INDEX idx_challenge_session_id ON challenge_responses(session_id);
CREATE INDEX idx_challenge_user_id ON challenge_responses(user_id);
CREATE INDEX idx_challenge_type ON challenge_responses(challenge_type);
CREATE INDEX idx_challenge_successful ON challenge_responses(is_successful);
CREATE INDEX idx_challenge_created ON challenge_responses(created_at DESC);
CREATE INDEX idx_challenge_ip ON challenge_responses(ip_address);

-- Pattern events indexes
CREATE INDEX idx_pattern_type ON pattern_events(pattern_type);
CREATE INDEX idx_pattern_severity ON pattern_events(severity);
CREATE INDEX idx_pattern_detection ON pattern_events(detection_time DESC);
CREATE INDEX idx_pattern_resolved ON pattern_events(resolved_at) WHERE resolved_at IS NOT NULL;
CREATE INDEX idx_pattern_score ON pattern_events(anomaly_score DESC);
CREATE INDEX idx_pattern_sessions ON pattern_events USING GIN(affected_sessions);

-- Performance metrics indexes
CREATE INDEX idx_metrics_name ON performance_metrics(metric_name);
CREATE INDEX idx_metrics_service ON performance_metrics(service_name);
CREATE INDEX idx_metrics_timestamp ON performance_metrics(timestamp DESC);
CREATE INDEX idx_metrics_tags ON performance_metrics USING GIN(tags);

-- Audit logs indexes  
CREATE INDEX idx_audit_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_session_id ON audit_logs(session_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_result ON audit_logs(result);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_ip ON audit_logs(ip_address);
CREATE INDEX idx_audit_resource ON audit_logs(resource, resource_id);

-- Partitioning for large tables (by month)
-- This helps with performance and data retention

-- Partition audit logs by month
SELECT partman.create_parent(
    p_parent_table => 'public.audit_logs',
    p_control => 'timestamp',
    p_type => 'range',
    p_interval => 'monthly'
);

-- Partition performance metrics by month
SELECT partman.create_parent(
    p_parent_table => 'public.performance_metrics', 
    p_control => 'timestamp',
    p_type => 'range',
    p_interval => 'monthly'
);

-- Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create function to calculate risk level from score
CREATE OR REPLACE FUNCTION calculate_risk_level(risk_score DECIMAL)
RETURNS risk_level AS $$
BEGIN
    IF risk_score >= 0.8 THEN
        RETURN 'critical';
    ELSIF risk_score >= 0.6 THEN
        RETURN 'high';
    ELSIF risk_score >= 0.3 THEN
        RETURN 'medium';
    ELSE
        RETURN 'low';
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Create trigger to auto-calculate risk level
CREATE OR REPLACE FUNCTION set_risk_level()
RETURNS TRIGGER AS $$
BEGIN
    NEW.risk_level = calculate_risk_level(NEW.risk_score);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER risk_level_trigger
    BEFORE INSERT OR UPDATE OF risk_score ON risk_assessments
    FOR EACH ROW
    EXECUTE FUNCTION set_risk_level();

-- Create materialized view for real-time statistics  
CREATE MATERIALIZED VIEW risk_statistics AS
SELECT 
    DATE_TRUNC('hour', created_at) as hour,
    risk_level,
    COUNT(*) as assessment_count,
    AVG(risk_score) as avg_risk_score,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY risk_score) as median_risk_score,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY risk_score) as p95_risk_score,
    COUNT(DISTINCT user_id) as unique_users,
    AVG(processing_time_ms) as avg_processing_time_ms
FROM risk_assessments 
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', created_at), risk_level
ORDER BY hour DESC, risk_level;

CREATE UNIQUE INDEX idx_risk_stats_hour_level ON risk_statistics(hour, risk_level);

-- Refresh materialized view every 5 minutes (to be set up with cron)
CREATE OR REPLACE FUNCTION refresh_risk_statistics()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY risk_statistics;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO antibot;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO antibot;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO antibot;