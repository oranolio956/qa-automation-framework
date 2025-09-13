# Telegram Bot Deployment Guide

Complete guide to deploy the Tinder Account Services Telegram bot in production.

## 🚀 Quick Deployment

### 1. Prerequisites Setup

**System Requirements:**
- Ubuntu 20.04+ or CentOS 8+
- Docker & Docker Compose
- Domain name with SSL certificate
- PostgreSQL 12+
- Redis 6+

**Get Required Tokens:**
1. **Telegram Bot Token**: Message @BotFather on Telegram
2. **Stripe Keys**: Sign up at stripe.com
3. **Telegram Payment Token**: Contact @BotSupport for payment provider token

### 2. Clone and Configure

```bash
# Clone the project
git clone <your-repo>
cd automation/telegram_bot

# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Required Environment Variables:**
```env
# Bot Configuration
TELEGRAM_BOT_TOKEN=8163343176:AAGnfDmoyeL7NSU0nLfLMqEohWxL5hZA6_0
ADMIN_USER_IDS=123456789,987654321

# Payment Configuration  
PAYMENT_PROVIDER_TOKEN=your_telegram_payment_token
STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key

# Database Configuration
DATABASE_URL=postgresql://tinder_user:secure_password@localhost:5432/tinder_bot
REDIS_URL=redis://localhost:6379/0

# Webhook Configuration
WEBHOOK_SECRET=your_secure_webhook_secret_key
WEBHOOK_URL=https://yourdomain.com/webhook
```

### 3. Database Setup

**Option A: Docker (Recommended)**
```bash
# Start database services
docker-compose up -d postgres redis

# Wait for services to be ready
docker-compose logs -f postgres redis
```

**Option B: Manual Installation**
```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Create database
sudo -u postgres createuser tinder_user
sudo -u postgres createdb tinder_bot -O tinder_user
sudo -u postgres psql -c "ALTER USER tinder_user WITH PASSWORD 'secure_password';"

# Install Redis
sudo apt install redis-server
sudo systemctl enable redis-server
```

### 4. Test Configuration

```bash
# Install dependencies
pip install -r requirements.txt

# Run configuration tests
python test_bot.py
```

Expected output:
```
🧪 Starting Telegram Bot System Tests
============================================================
🔧 Testing configuration...
✅ Configuration validation passed
✅ Loaded 4 service packages
✅ Pricing calculation works: 5x starter pack = $142.46 ($7.49 discount)

💾 Testing database models...
✅ Database connection successful
✅ User management works: Test User
✅ Order management works: Order ORD1234567890 created

🧪 Test Results: 7/7 passed
🎉 All tests passed! Bot system is ready.
```

### 5. Deploy Bot

**Development (Polling):**
```bash
python run_bot.py polling
```

**Production (Webhook):**
```bash
# Start webhook server
docker-compose --profile webhook up -d

# Set webhook URL
curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://yourdomain.com/webhook/telegram"}'
```

## 🔐 Production Security Checklist

### SSL Certificate Setup
```bash
# Using Certbot for Let's Encrypt
sudo apt install certbot
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates to docker volume
sudo cp /etc/letsencrypt/live/yourdomain.com/* ./ssl/
```

### Nginx Configuration
```nginx
# /etc/nginx/sites-available/tinder-bot
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    
    location /webhook/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /admin/ {
        proxy_pass http://127.0.0.1:8000;
        # Add IP whitelist for admin endpoints
        allow 1.2.3.4;  # Your IP
        deny all;
    }
    
    location /health {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

### Environment Security
```bash
# Secure environment file
chmod 600 .env
chown root:root .env

# Use Docker secrets in production
echo "your_db_password" | docker secret create db_password -
echo "your_stripe_key" | docker secret create stripe_key -
```

### Database Security
```bash
# Create read-only user for analytics
sudo -u postgres psql tinder_bot -c "
CREATE USER analytics WITH PASSWORD 'analytics_password';
GRANT CONNECT ON DATABASE tinder_bot TO analytics;
GRANT USAGE ON SCHEMA public TO analytics;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics;
"
```

## 📊 Monitoring Setup

### Health Checks
```bash
# Add to crontab
*/5 * * * * curl -f http://localhost:8000/health || echo "Bot health check failed" | mail -s "Bot Alert" admin@yourdomain.com
```

### Log Management
```bash
# Setup log rotation
sudo tee /etc/logrotate.d/tinder-bot << EOF
/var/log/tinder-bot/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    create 0644 root root
}
EOF
```

### Error Tracking (Sentry)
```python
# Add to .env
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

## 🚨 Backup Strategy

### Database Backups
```bash
#!/bin/bash
# /opt/backup-tinder-bot.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups/tinder-bot"
mkdir -p $BACKUP_DIR

# Database backup
pg_dump -h localhost -U tinder_user tinder_bot | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Redis backup
cp /var/lib/redis/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Environment backup
cp /opt/tinder-bot/.env $BACKUP_DIR/env_$DATE

# Clean old backups (keep 7 days)
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.rdb" -mtime +7 -delete
```

Add to crontab:
```bash
0 2 * * * /opt/backup-tinder-bot.sh
```

## 🔄 Update Deployment

### Zero-Downtime Updates
```bash
#!/bin/bash
# update-bot.sh

echo "🔄 Starting bot update..."

# Pull latest changes
git pull origin main

# Build new image
docker-compose build

# Rolling update
docker-compose --profile webhook up -d --no-deps bot_webhook

# Health check
sleep 10
if curl -f http://localhost:8000/health; then
    echo "✅ Update successful"
else
    echo "❌ Update failed, rolling back"
    docker-compose --profile webhook rollback
    exit 1
fi
```

## 📈 Scaling for High Volume

### Database Optimization
```sql
-- Create indexes for performance
CREATE INDEX CONCURRENTLY idx_orders_user_status ON orders(user_id, status);
CREATE INDEX CONCURRENTLY idx_orders_created_status ON orders(created_at, status);
CREATE INDEX CONCURRENTLY idx_payments_status_created ON payments(status, created_at);
CREATE INDEX CONCURRENTLY idx_analytics_event_date ON analytics(event_type, created_at);

-- Analyze tables regularly
ANALYZE users, orders, payments, analytics;
```

### Redis Configuration
```bash
# /etc/redis/redis.conf
maxmemory 1gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### Bot Scaling (Multiple Instances)
```yaml
# docker-compose.scale.yml
version: '3.8'
services:
  bot_webhook:
    deploy:
      replicas: 3
    environment:
      - WORKER_ID={{.Task.Slot}}
```

Run with:
```bash
docker-compose -f docker-compose.yml -f docker-compose.scale.yml --profile webhook up -d
```

## 🔍 Troubleshooting

### Common Issues

**Bot Not Responding:**
```bash
# Check bot status
docker-compose logs bot_webhook

# Verify webhook
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo"

# Reset webhook if needed
curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/deleteWebhook"
```

**Database Connection Issues:**
```bash
# Check database connectivity
docker-compose exec postgres psql -U tinder_user -d tinder_bot -c "SELECT 1;"

# Check database permissions
docker-compose exec postgres psql -U tinder_user -d tinder_bot -c "\dt"
```

**Payment Processing Issues:**
```bash
# Check Stripe webhook events
curl https://api.stripe.com/v1/webhook_endpoints \
  -u sk_test_your_stripe_key:

# Test payment webhook
curl -X POST http://localhost:8000/webhook/stripe \
  -H "Content-Type: application/json" \
  -d '{"test": "webhook"}'
```

### Performance Monitoring
```bash
# Monitor database connections
docker-compose exec postgres psql -U tinder_user -d tinder_bot -c "SELECT count(*) FROM pg_stat_activity;"

# Monitor Redis memory usage
docker-compose exec redis redis-cli info memory

# Monitor bot response times
tail -f /var/log/tinder-bot/access.log | grep -E "(webhook|admin)"
```

## 🎯 Production Optimization

### Database Performance
```sql
-- Partition large tables
CREATE TABLE orders_2024 PARTITION OF orders
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

-- Set up automatic vacuum
ALTER TABLE orders SET (autovacuum_vacuum_scale_factor = 0.1);
ALTER TABLE analytics SET (autovacuum_vacuum_scale_factor = 0.05);
```

### Application Performance
```python
# Connection pooling settings (in config.py)
DATABASE_POOL_MIN = 5
DATABASE_POOL_MAX = 20
REDIS_POOL_MAX = 30

# Rate limiting configuration
RATE_LIMIT_REDIS_KEY_PREFIX = "rate_limit:"
RATE_LIMIT_WINDOW_SIZE = 60  # seconds
```

### Caching Strategy
```python
# Cache expensive operations
@cached(ttl=300)  # 5 minutes
async def get_user_stats(user_id: int):
    # Expensive database query
    pass

@cached(ttl=3600)  # 1 hour  
async def get_package_popularity():
    # Analytics query
    pass
```

## 📞 Production Support

### Monitoring Dashboard URLs
- Health Check: `https://yourdomain.com/health`
- Admin Panel: `https://yourdomain.com/admin/stats` 
- Webhook Status: `https://api.telegram.org/bot$TOKEN/getWebhookInfo`

### Emergency Contacts
- Bot Admin: Configure in `ADMIN_USER_IDS`
- Technical Support: Your DevOps team
- Payment Issues: Stripe dashboard alerts

### Support Procedures
1. **Bot Down**: Check logs, restart services, verify webhook
2. **Database Issues**: Check connections, run backups, scale if needed  
3. **Payment Failures**: Check Stripe dashboard, verify webhook signatures
4. **High Load**: Scale bot instances, optimize database queries

---

## 🎉 Deployment Complete!

Your Telegram bot is now ready for production with:
- ✅ Secure payment processing
- ✅ Automated order management  
- ✅ Real-time delivery tracking
- ✅ Comprehensive admin panel
- ✅ Monitoring and backup systems
- ✅ Scalable architecture

**Bot URL**: https://t.me/buytinderadds

Monitor your bot performance and scale as needed! 🚀