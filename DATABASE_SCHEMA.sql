-- =====================================================================================
-- SNAPCHAT AUTOMATION SYSTEM - PRODUCTION DATABASE SCHEMA
-- =====================================================================================
-- PostgreSQL Database: database_8zh9
-- Connection: postgresql://database_8zh9_user:yZHV8grbsfJgXXgxDPh2NBBkiFYilpKW@dpg-d33nhuodl3ps73917ejg-a.oregon-postgres.render.com/database_8zh9
-- Environment: Production
-- Created: September 15, 2025
-- =====================================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "citext";

-- =====================================================================================
-- CORE SYSTEM TABLES
-- =====================================================================================

-- System configuration and settings
CREATE TABLE IF NOT EXISTS system_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT,
    config_type VARCHAR(20) DEFAULT 'string',
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audit trail for all system operations
CREATE TABLE IF NOT EXISTS system_audit (
    id BIGSERIAL PRIMARY KEY,
    action_type VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(100),
    user_id VARCHAR(100),
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    session_id UUID
);

-- =====================================================================================
-- SNAPCHAT ACCOUNT MANAGEMENT
-- =====================================================================================

-- Snapchat account profiles and credentials
CREATE TABLE IF NOT EXISTS snapchat_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone_number VARCHAR(20) UNIQUE,
    display_name VARCHAR(50) NOT NULL,
    birth_date DATE NOT NULL,
    profile_picture_url TEXT,
    bio_text TEXT,
    
    -- Account status and verification
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'creating', 'active', 'suspended', 'banned', 'deleted')),
    is_verified BOOLEAN DEFAULT FALSE,
    verification_method VARCHAR(20),
    phone_verified BOOLEAN DEFAULT FALSE,
    email_verified BOOLEAN DEFAULT FALSE,
    
    -- Creation metadata
    creation_device_id UUID,
    creation_ip_address INET,
    creation_proxy_id UUID,
    creation_session_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Security and monitoring
    password_hash VARCHAR(255),
    last_login_at TIMESTAMP WITH TIME ZONE,
    login_count INTEGER DEFAULT 0,
    last_activity_at TIMESTAMP WITH TIME ZONE,
    security_flags JSONB DEFAULT '{}',
    
    -- Business logic
    assigned_to_order UUID,
    delivery_status VARCHAR(20) DEFAULT 'pending',
    quality_score INTEGER DEFAULT 0,
    trust_score DECIMAL(3,2) DEFAULT 0.0,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Account creation attempts and tracking
CREATE TABLE IF NOT EXISTS account_creation_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    snapchat_account_id UUID REFERENCES snapchat_accounts(id),
    attempt_number INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('started', 'in_progress', 'sms_verification', 'email_verification', 'completed', 'failed', 'abandoned')),
    
    -- Technical details
    device_id UUID NOT NULL,
    emulator_instance_id VARCHAR(100),
    proxy_used VARCHAR(100),
    anti_detection_profile_id UUID,
    
    -- Progress tracking
    steps_completed JSONB DEFAULT '[]',
    current_step VARCHAR(50),
    error_messages JSONB DEFAULT '[]',
    screenshots JSONB DEFAULT '[]',
    
    -- Timing
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    
    -- Verification details
    sms_verification_code VARCHAR(10),
    sms_verification_attempts INTEGER DEFAULT 0,
    email_verification_token VARCHAR(100),
    
    -- Results
    final_status VARCHAR(20),
    failure_reason TEXT,
    success_metrics JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================================================
-- ANDROID DEVICE FARM MANAGEMENT
-- =====================================================================================

-- Android emulator instances and configurations
CREATE TABLE IF NOT EXISTS android_devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_name VARCHAR(100) NOT NULL,
    device_id VARCHAR(50) UNIQUE NOT NULL,
    emulator_type VARCHAR(30) NOT NULL,
    
    -- Hardware specifications
    android_version VARCHAR(20) NOT NULL,
    api_level INTEGER NOT NULL,
    screen_resolution VARCHAR(20),
    ram_mb INTEGER,
    storage_gb INTEGER,
    cpu_cores INTEGER,
    
    -- Device fingerprint
    manufacturer VARCHAR(50),
    model VARCHAR(50),
    build_number VARCHAR(100),
    kernel_version VARCHAR(100),
    security_patch VARCHAR(20),
    device_fingerprint_hash VARCHAR(64),
    
    -- Deployment configuration
    fly_io_machine_id VARCHAR(100),
    fly_io_region VARCHAR(20),
    deployment_status VARCHAR(20) DEFAULT 'pending',
    
    -- Network configuration
    assigned_ip_address INET,
    proxy_configuration JSONB,
    vpn_configuration JSONB,
    
    -- Status and monitoring
    status VARCHAR(20) DEFAULT 'inactive' CHECK (status IN ('inactive', 'starting', 'active', 'busy', 'maintenance', 'error', 'terminated')),
    health_status VARCHAR(20) DEFAULT 'unknown',
    last_health_check TIMESTAMP WITH TIME ZONE,
    
    -- Usage tracking
    total_accounts_created INTEGER DEFAULT 0,
    successful_creations INTEGER DEFAULT 0,
    failed_creations INTEGER DEFAULT 0,
    current_session_id UUID,
    
    -- Performance metrics
    average_creation_time_seconds INTEGER,
    uptime_hours DECIMAL(10,2) DEFAULT 0,
    performance_score INTEGER DEFAULT 0,
    
    -- Maintenance
    last_maintenance_at TIMESTAMP WITH TIME ZONE,
    next_scheduled_maintenance TIMESTAMP WITH TIME ZONE,
    maintenance_notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Device session tracking for automation workflows
CREATE TABLE IF NOT EXISTS device_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID REFERENCES android_devices(id) NOT NULL,
    session_type VARCHAR(30) NOT NULL,
    
    -- Session details
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    
    -- Associated work
    snapchat_account_id UUID REFERENCES snapchat_accounts(id),
    telegram_order_id UUID,
    automation_workflow VARCHAR(50),
    
    -- Technical metrics
    screenshots_taken INTEGER DEFAULT 0,
    ui_interactions INTEGER DEFAULT 0,
    network_requests INTEGER DEFAULT 0,
    errors_encountered INTEGER DEFAULT 0,
    
    -- Results
    session_status VARCHAR(20) DEFAULT 'active',
    final_result VARCHAR(20),
    result_data JSONB DEFAULT '{}',
    
    -- Monitoring
    resource_usage JSONB DEFAULT '{}',
    performance_metrics JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================================================
-- ANTI-DETECTION AND SECURITY
-- =====================================================================================

-- Anti-detection profiles for stealth automation
CREATE TABLE IF NOT EXISTS anti_detection_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_name VARCHAR(100) NOT NULL,
    profile_type VARCHAR(30) NOT NULL,
    
    -- Behavioral patterns
    aggressiveness_level DECIMAL(3,2) DEFAULT 0.3,
    typing_pattern JSONB DEFAULT '{}',
    mouse_movement_pattern JSONB DEFAULT '{}',
    interaction_timing JSONB DEFAULT '{}',
    
    -- Technical fingerprint
    user_agent_pattern VARCHAR(500),
    screen_resolution VARCHAR(20),
    timezone VARCHAR(50),
    locale VARCHAR(10),
    language_preferences JSONB DEFAULT '[]',
    
    -- Hardware simulation
    device_fingerprint JSONB DEFAULT '{}',
    sensor_data JSONB DEFAULT '{}',
    network_characteristics JSONB DEFAULT '{}',
    
    -- Behavioral metrics
    trust_score DECIMAL(3,2) DEFAULT 0.0,
    success_rate DECIMAL(3,2) DEFAULT 0.0,
    detection_events INTEGER DEFAULT 0,
    
    -- Usage tracking
    times_used INTEGER DEFAULT 0,
    successful_sessions INTEGER DEFAULT 0,
    failed_sessions INTEGER DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,
    
    -- Maintenance
    is_active BOOLEAN DEFAULT TRUE,
    calibration_data JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Security events and threat detection
CREATE TABLE IF NOT EXISTS security_events (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    
    -- Event details
    source_component VARCHAR(50),
    description TEXT NOT NULL,
    raw_event_data JSONB,
    
    -- Context
    device_id UUID,
    account_id UUID,
    session_id UUID,
    ip_address INET,
    user_agent TEXT,
    
    -- Classification
    threat_category VARCHAR(30),
    is_automated_detection BOOLEAN DEFAULT FALSE,
    confidence_score DECIMAL(3,2),
    
    -- Response
    response_action VARCHAR(50),
    response_details JSONB,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(100),
    
    -- Metadata
    tags JSONB DEFAULT '[]',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================================================
-- TELEGRAM BOT AND ORDER MANAGEMENT
-- =====================================================================================

-- Telegram bot users and customer accounts
CREATE TABLE IF NOT EXISTS telegram_users (
    id BIGSERIAL PRIMARY KEY,
    telegram_user_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(100),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    
    -- Account details
    is_admin BOOLEAN DEFAULT FALSE,
    is_premium BOOLEAN DEFAULT FALSE,
    subscription_tier VARCHAR(20) DEFAULT 'free',
    subscription_expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Usage tracking
    total_orders INTEGER DEFAULT 0,
    successful_orders INTEGER DEFAULT 0,
    total_spent DECIMAL(10,2) DEFAULT 0.00,
    
    -- Limits and restrictions
    daily_order_limit INTEGER DEFAULT 5,
    orders_today INTEGER DEFAULT 0,
    last_order_date DATE,
    
    -- Engagement metrics
    first_interaction_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_interaction_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    total_interactions INTEGER DEFAULT 1,
    
    -- Status
    is_banned BOOLEAN DEFAULT FALSE,
    ban_reason TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Preferences
    preferred_language VARCHAR(10) DEFAULT 'en',
    notification_preferences JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Customer orders for Snapchat accounts
CREATE TABLE IF NOT EXISTS customer_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_number VARCHAR(20) UNIQUE NOT NULL,
    telegram_user_id BIGINT REFERENCES telegram_users(telegram_user_id) NOT NULL,
    
    -- Order details
    quantity INTEGER NOT NULL DEFAULT 1,
    order_type VARCHAR(30) DEFAULT 'snapchat_accounts',
    special_requirements TEXT,
    
    -- Pricing
    unit_price DECIMAL(8,2) NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Payment
    payment_status VARCHAR(20) DEFAULT 'pending' CHECK (payment_status IN ('pending', 'processing', 'completed', 'failed', 'refunded')),
    payment_method VARCHAR(30),
    payment_transaction_id VARCHAR(100),
    payment_completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Order status
    order_status VARCHAR(20) DEFAULT 'pending' CHECK (order_status IN ('pending', 'processing', 'in_creation', 'verification', 'completed', 'failed', 'cancelled')),
    progress_percentage INTEGER DEFAULT 0,
    
    -- Fulfillment
    accounts_requested INTEGER NOT NULL,
    accounts_created INTEGER DEFAULT 0,
    accounts_delivered INTEGER DEFAULT 0,
    delivery_method VARCHAR(20) DEFAULT 'telegram',
    delivery_completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Timing
    estimated_completion_time TIMESTAMP WITH TIME ZONE,
    actual_completion_time TIMESTAMP WITH TIME ZONE,
    
    -- Quality assurance
    quality_check_passed BOOLEAN,
    quality_check_notes TEXT,
    customer_satisfaction_score INTEGER,
    
    -- Tracking
    real_time_updates JSONB DEFAULT '[]',
    status_updates JSONB DEFAULT '[]',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Real-time order progress tracking
CREATE TABLE IF NOT EXISTS order_progress (
    id BIGSERIAL PRIMARY KEY,
    order_id UUID REFERENCES customer_orders(id) NOT NULL,
    
    -- Progress details
    step_name VARCHAR(100) NOT NULL,
    step_status VARCHAR(20) NOT NULL,
    progress_percentage INTEGER DEFAULT 0,
    
    -- Timing
    step_started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    step_completed_at TIMESTAMP WITH TIME ZONE,
    estimated_duration_seconds INTEGER,
    actual_duration_seconds INTEGER,
    
    -- Details
    step_description TEXT,
    technical_details JSONB DEFAULT '{}',
    error_details JSONB DEFAULT '{}',
    
    -- Associated resources
    device_id UUID,
    account_id UUID,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================================================
-- EXTERNAL SERVICES INTEGRATION
-- =====================================================================================

-- SMS verification service tracking
CREATE TABLE IF NOT EXISTS sms_verifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone_number VARCHAR(20) NOT NULL,
    verification_code VARCHAR(10),
    
    -- Service details
    sms_service_provider VARCHAR(30) NOT NULL,
    service_transaction_id VARCHAR(100),
    message_id VARCHAR(100),
    
    -- Status tracking
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'delivered', 'verified', 'failed', 'expired')),
    attempts_count INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    
    -- Associated records
    snapchat_account_id UUID REFERENCES snapchat_accounts(id),
    device_id UUID,
    order_id UUID REFERENCES customer_orders(id),
    
    -- Timing
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    verified_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Cost tracking
    cost_usd DECIMAL(6,4),
    service_response JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Email verification and integration
CREATE TABLE IF NOT EXISTS email_verifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_address VARCHAR(100) NOT NULL,
    verification_token VARCHAR(255),
    
    -- Service details
    email_service_provider VARCHAR(30) NOT NULL,
    service_account_id VARCHAR(100),
    inbox_id VARCHAR(100),
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'verified', 'failed', 'expired')),
    verification_link VARCHAR(500),
    
    -- Associated records
    snapchat_account_id UUID REFERENCES snapchat_accounts(id),
    order_id UUID REFERENCES customer_orders(id),
    
    -- Timing
    verification_email_sent_at TIMESTAMP WITH TIME ZONE,
    verification_completed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Service response
    service_response JSONB DEFAULT '{}',
    email_content TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Proxy and VPN service management
CREATE TABLE IF NOT EXISTS proxy_services (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_name VARCHAR(50) NOT NULL,
    service_type VARCHAR(20) NOT NULL CHECK (service_type IN ('residential', 'datacenter', 'mobile', 'vpn')),
    
    -- Connection details
    proxy_host VARCHAR(100) NOT NULL,
    proxy_port INTEGER NOT NULL,
    username VARCHAR(100),
    password_hash VARCHAR(255),
    
    -- Geographic data
    country_code VARCHAR(2),
    region VARCHAR(50),
    city VARCHAR(50),
    ip_range CIDR,
    
    -- Service configuration
    is_rotating BOOLEAN DEFAULT FALSE,
    rotation_interval_minutes INTEGER,
    max_concurrent_sessions INTEGER DEFAULT 1,
    
    -- Status and monitoring
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'maintenance', 'banned', 'error')),
    health_check_url VARCHAR(200),
    last_health_check TIMESTAMP WITH TIME ZONE,
    response_time_ms INTEGER,
    
    -- Usage tracking
    total_sessions INTEGER DEFAULT 0,
    successful_sessions INTEGER DEFAULT 0,
    failed_sessions INTEGER DEFAULT 0,
    data_usage_gb DECIMAL(10,2) DEFAULT 0.0,
    
    -- Costs and billing
    cost_per_gb DECIMAL(6,4),
    monthly_cost DECIMAL(8,2),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================================================
-- PERFORMANCE AND MONITORING
-- =====================================================================================

-- System performance metrics
CREATE TABLE IF NOT EXISTS performance_metrics (
    id BIGSERIAL PRIMARY KEY,
    metric_type VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    
    -- Metric values
    value_numeric DECIMAL(15,4),
    value_text VARCHAR(200),
    value_json JSONB,
    
    -- Context
    component VARCHAR(50),
    device_id UUID,
    session_id UUID,
    
    -- Timing
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    period_start TIMESTAMP WITH TIME ZONE,
    period_end TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    tags JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Resource usage tracking
CREATE TABLE IF NOT EXISTS resource_usage (
    id BIGSERIAL PRIMARY KEY,
    resource_type VARCHAR(30) NOT NULL,
    
    -- Usage metrics
    cpu_usage_percent DECIMAL(5,2),
    memory_usage_mb INTEGER,
    disk_usage_gb DECIMAL(8,2),
    network_in_mb DECIMAL(10,2),
    network_out_mb DECIMAL(10,2),
    
    -- Context
    device_id UUID,
    session_id UUID,
    component VARCHAR(50),
    
    -- Timing
    measurement_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    measurement_period_seconds INTEGER DEFAULT 60,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =====================================================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================================================

-- Primary performance indexes
CREATE INDEX IF NOT EXISTS idx_snapchat_accounts_status ON snapchat_accounts(status);
CREATE INDEX IF NOT EXISTS idx_snapchat_accounts_created_at ON snapchat_accounts(created_at);
CREATE INDEX IF NOT EXISTS idx_snapchat_accounts_assigned_order ON snapchat_accounts(assigned_to_order);

CREATE INDEX IF NOT EXISTS idx_android_devices_status ON android_devices(status);
CREATE INDEX IF NOT EXISTS idx_android_devices_fly_machine ON android_devices(fly_io_machine_id);

CREATE INDEX IF NOT EXISTS idx_customer_orders_telegram_user ON customer_orders(telegram_user_id);
CREATE INDEX IF NOT EXISTS idx_customer_orders_status ON customer_orders(order_status);
CREATE INDEX IF NOT EXISTS idx_customer_orders_created_at ON customer_orders(created_at);

CREATE INDEX IF NOT EXISTS idx_account_creation_attempts_device ON account_creation_attempts(device_id);
CREATE INDEX IF NOT EXISTS idx_account_creation_attempts_status ON account_creation_attempts(status);

CREATE INDEX IF NOT EXISTS idx_security_events_timestamp ON security_events(created_at);
CREATE INDEX IF NOT EXISTS idx_security_events_severity ON security_events(severity);

CREATE INDEX IF NOT EXISTS idx_sms_verifications_phone ON sms_verifications(phone_number);
CREATE INDEX IF NOT EXISTS idx_sms_verifications_status ON sms_verifications(status);

-- Composite indexes for complex queries
CREATE INDEX IF NOT EXISTS idx_orders_user_status ON customer_orders(telegram_user_id, order_status);
CREATE INDEX IF NOT EXISTS idx_accounts_status_created ON snapchat_accounts(status, created_at);
CREATE INDEX IF NOT EXISTS idx_device_sessions_device_status ON device_sessions(device_id, session_status);

-- =====================================================================================
-- FUNCTIONS AND TRIGGERS
-- =====================================================================================

-- Function to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update triggers to relevant tables
CREATE TRIGGER update_snapchat_accounts_updated_at BEFORE UPDATE ON snapchat_accounts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_android_devices_updated_at BEFORE UPDATE ON android_devices FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_customer_orders_updated_at BEFORE UPDATE ON customer_orders FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_telegram_users_updated_at BEFORE UPDATE ON telegram_users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to generate order numbers
CREATE OR REPLACE FUNCTION generate_order_number()
RETURNS TEXT AS $$
BEGIN
    RETURN 'SNAP-' || TO_CHAR(NOW(), 'YYYYMMDD') || '-' || LPAD(NEXTVAL('order_number_seq')::TEXT, 4, '0');
END;
$$ LANGUAGE plpgsql;

-- Create sequence for order numbers
CREATE SEQUENCE IF NOT EXISTS order_number_seq START 1;

-- =====================================================================================
-- INITIAL CONFIGURATION DATA
-- =====================================================================================

-- Insert default system configuration
INSERT INTO system_config (config_key, config_value, config_type, description) VALUES
('system_version', '1.0.0', 'string', 'Current system version'),
('max_daily_accounts', '100', 'integer', 'Maximum accounts that can be created per day'),
('default_account_price', '15.00', 'decimal', 'Default price per Snapchat account (USD)'),
('telegram_bot_enabled', 'true', 'boolean', 'Enable Telegram bot service'),
('anti_detection_enabled', 'true', 'boolean', 'Enable anti-detection measures'),
('sms_verification_timeout', '300', 'integer', 'SMS verification timeout in seconds'),
('device_pool_size', '10', 'integer', 'Number of Android devices in pool'),
('max_concurrent_creations', '5', 'integer', 'Maximum concurrent account creations'),
('quality_threshold', '85', 'integer', 'Minimum quality score for account delivery'),
('maintenance_mode', 'false', 'boolean', 'System maintenance mode flag')
ON CONFLICT (config_key) DO NOTHING;

-- =====================================================================================
-- VIEWS FOR COMMON QUERIES
-- =====================================================================================

-- Active orders summary view
CREATE OR REPLACE VIEW active_orders_summary AS
SELECT 
    co.id,
    co.order_number,
    tu.telegram_user_id,
    tu.username,
    co.quantity,
    co.accounts_created,
    co.order_status,
    co.progress_percentage,
    co.created_at,
    co.estimated_completion_time
FROM customer_orders co
JOIN telegram_users tu ON co.telegram_user_id = tu.telegram_user_id
WHERE co.order_status IN ('pending', 'processing', 'in_creation', 'verification');

-- Device utilization view
CREATE OR REPLACE VIEW device_utilization AS
SELECT 
    ad.id,
    ad.device_name,
    ad.status,
    ad.total_accounts_created,
    ad.successful_creations,
    ad.performance_score,
    CASE 
        WHEN ad.total_accounts_created > 0 
        THEN ROUND((ad.successful_creations::DECIMAL / ad.total_accounts_created) * 100, 2)
        ELSE 0
    END as success_rate,
    ad.uptime_hours,
    ad.last_health_check
FROM android_devices ad
ORDER BY ad.performance_score DESC;

-- System performance dashboard view
CREATE OR REPLACE VIEW system_dashboard AS
SELECT 
    (SELECT COUNT(*) FROM snapchat_accounts WHERE status = 'active') as active_accounts,
    (SELECT COUNT(*) FROM customer_orders WHERE order_status IN ('pending', 'processing', 'in_creation')) as active_orders,
    (SELECT COUNT(*) FROM android_devices WHERE status = 'active') as active_devices,
    (SELECT COUNT(*) FROM telegram_users WHERE is_active = true) as active_users,
    (SELECT AVG(performance_score) FROM android_devices WHERE status = 'active') as avg_device_performance,
    (SELECT SUM(total_spent) FROM telegram_users) as total_revenue,
    (SELECT COUNT(*) FROM security_events WHERE created_at > NOW() - INTERVAL '24 hours' AND severity IN ('high', 'critical')) as recent_security_alerts;

-- =====================================================================================
-- GRANTS AND PERMISSIONS
-- =====================================================================================

-- Grant appropriate permissions (adjust based on your user management needs)
GRANT USAGE ON SCHEMA public TO database_8zh9_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO database_8zh9_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO database_8zh9_user;

-- =====================================================================================
-- DATABASE INITIALIZATION COMPLETE
-- =====================================================================================

-- Insert a record to confirm database initialization
INSERT INTO system_audit (action_type, resource_type, details, timestamp) VALUES 
('system_initialization', 'database', '{"message": "Database schema initialized successfully", "version": "1.0.0", "tables_created": 20}', NOW());

-- Display initialization summary
SELECT 
    'Database initialization completed successfully' as status,
    NOW() as completed_at,
    (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE') as tables_created,
    (SELECT COUNT(*) FROM information_schema.views WHERE table_schema = 'public') as views_created;