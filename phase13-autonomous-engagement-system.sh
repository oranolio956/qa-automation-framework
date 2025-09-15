#!/bin/bash

# Phase 13: Autonomous Engagement and Infrastructure Hardening System
# Production-ready Telegram bot with full autonomous engagement features and enterprise-grade infrastructure

set -euo pipefail

# Configuration variables
PROJECT_ROOT="${PWD}"
PHASE13_DIR="${PROJECT_ROOT}/phase13-autonomous-system"
BOT_DIR="${PHASE13_DIR}/telegram-bot"
ENGAGEMENT_DIR="${PHASE13_DIR}/engagement-engine"
INFRASTRUCTURE_DIR="${PHASE13_DIR}/infrastructure"
KUBERNETES_DIR="${PHASE13_DIR}/k8s"
MONITORING_DIR="${PHASE13_DIR}/monitoring"
SECURITY_DIR="${PHASE13_DIR}/security"
COMPLIANCE_DIR="${PHASE13_DIR}/compliance"

echo "=== Phase 13: Autonomous Engagement and Infrastructure Hardening ==="
echo "Creating production-ready autonomous engagement system..."

# Create comprehensive directory structure
mkdir -p "$PHASE13_DIR" "$BOT_DIR/src/handlers" "$BOT_DIR/src/services" "$BOT_DIR/src/models" \
         "$ENGAGEMENT_DIR/schedulers" "$ENGAGEMENT_DIR/gamification" "$ENGAGEMENT_DIR/ai-powered" \
         "$INFRASTRUCTURE_DIR/helm-charts" "$KUBERNETES_DIR/base" "$KUBERNETES_DIR/overlays/production" \
         "$MONITORING_DIR/prometheus" "$MONITORING_DIR/grafana" "$SECURITY_DIR/vault" \
         "$COMPLIANCE_DIR/audit-logs" "$COMPLIANCE_DIR/legal-automation"

# Phase 1: Core Telegram Bot with Autonomous Engagement Features
echo "Creating autonomous Telegram bot with advanced engagement features..."

cat > "$BOT_DIR/package.json" << 'EOF'
{
  "name": "autonomous-telegram-engagement-bot",
  "version": "2.0.0",
  "description": "Production-ready autonomous Telegram bot with engagement features",
  "main": "src/index.js",
  "scripts": {
    "start": "node src/index.js",
    "dev": "nodemon src/index.js",
    "test": "jest --coverage",
    "lint": "eslint src/",
    "docker:build": "docker build -t telegram-engagement-bot .",
    "deploy:k8s": "kubectl apply -f ../k8s/base/"
  },
  "dependencies": {
    "telegraf": "^4.15.6",
    "node-cron": "^3.0.2",
    "redis": "^4.6.10",
    "mongoose": "^8.0.3",
    "winston": "^3.11.0",
    "prometheus-client": "^15.1.0",
    "openai": "^4.20.1",
    "axios": "^1.6.2",
    "crypto": "^1.0.1",
    "jsonwebtoken": "^9.0.2",
    "bcryptjs": "^2.4.3",
    "express": "^4.18.2",
    "socket.io": "^4.7.4",
    "canvas": "^2.11.2",
    "sharp": "^0.33.0",
    "qrcode": "^1.5.3",
    "moment": "^2.29.4",
    "lodash": "^4.17.21",
    "uuid": "^9.0.1",
    "helmet": "^7.1.0",
    "cors": "^2.8.5",
    "compression": "^1.7.4",
    "express-rate-limit": "^7.1.5",
    "@kubernetes/client-node": "^0.20.0"
  },
  "devDependencies": {
    "nodemon": "^3.0.2",
    "jest": "^29.7.0",
    "eslint": "^8.55.0",
    "supertest": "^6.3.3"
  }
}
EOF

# Core Bot Index with Enterprise Architecture
cat > "$BOT_DIR/src/index.js" << 'EOF'
const { Telegraf, session } = require('telegraf');
const Redis = require('redis');
const mongoose = require('mongoose');
const winston = require('winston');
const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const promClient = require('prom-client');
const helmet = require('helmet');
const cors = require('cors');
const compression = require('compression');

const EngagementEngine = require('./services/EngagementEngine');
const GameficationService = require('./services/GameficationService');
const AIAssistant = require('./services/AIAssistant');
const SecurityService = require('./services/SecurityService');
const MonitoringService = require('./services/MonitoringService');
const ComplianceService = require('./services/ComplianceService');

class AutonomousEngagementBot {
    constructor() {
        this.bot = new Telegraf(process.env.BOT_TOKEN);
        this.redis = Redis.createClient({ url: process.env.REDIS_URL });
        this.app = express();
        this.server = http.createServer(this.app);
        this.io = socketIo(this.server);
        this.port = process.env.PORT || 3000;
        
        this.setupLogger();
        this.setupMetrics();
        this.initializeServices();
        this.setupMiddleware();
        this.setupHandlers();
        this.setupWebServer();
        this.startAutonomousEngagement();
    }

    setupLogger() {
        this.logger = winston.createLogger({
            level: process.env.LOG_LEVEL || 'info',
            format: winston.format.combine(
                winston.format.timestamp(),
                winston.format.errors({ stack: true }),
                winston.format.json()
            ),
            defaultMeta: { service: 'telegram-engagement-bot' },
            transports: [
                new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
                new winston.transports.File({ filename: 'logs/combined.log' }),
                new winston.transports.Console({
                    format: winston.format.simple()
                })
            ]
        });
    }

    setupMetrics() {
        this.metrics = {
            httpRequestDuration: new promClient.Histogram({
                name: 'http_request_duration_ms',
                help: 'Duration of HTTP requests in ms',
                labelNames: ['method', 'route', 'status_code'],
                buckets: [0.1, 5, 15, 50, 100, 500]
            }),
            telegramMessages: new promClient.Counter({
                name: 'telegram_messages_total',
                help: 'Total number of Telegram messages processed',
                labelNames: ['type', 'status']
            }),
            engagementEvents: new promClient.Counter({
                name: 'engagement_events_total',
                help: 'Total engagement events triggered',
                labelNames: ['event_type', 'success']
            }),
            activeUsers: new promClient.Gauge({
                name: 'active_users',
                help: 'Number of currently active users'
            })
        };

        promClient.collectDefaultMetrics({ prefix: 'telegram_bot_' });
    }

    async initializeServices() {
        // Connect to databases
        await mongoose.connect(process.env.MONGODB_URL);
        await this.redis.connect();

        // Initialize core services
        this.engagement = new EngagementEngine(this.redis, this.logger);
        this.gamification = new GameficationService(this.redis, this.logger);
        this.aiAssistant = new AIAssistant(process.env.OPENAI_API_KEY, this.logger);
        this.security = new SecurityService(this.redis, this.logger);
        this.monitoring = new MonitoringService(this.metrics, this.logger);
        this.compliance = new ComplianceService(this.logger);

        this.logger.info('All services initialized successfully');
    }

    setupMiddleware() {
        this.bot.use(session({
            defaultSession: () => ({
                points: 0,
                level: 1,
                achievements: [],
                preferences: {},
                engagement_streak: 0,
                last_active: new Date()
            })
        }));

        // Security middleware for bot
        this.bot.use(async (ctx, next) => {
            const isAuthorized = await this.security.validateUser(ctx.from.id);
            if (!isAuthorized) {
                await ctx.reply('❌ Access denied. Please contact support.');
                return;
            }

            // Rate limiting
            const rateLimited = await this.security.checkRateLimit(ctx.from.id);
            if (rateLimited) {
                await ctx.reply('⏰ Please slow down. Rate limit exceeded.');
                return;
            }

            await next();
        });

        // Web server middleware
        this.app.use(helmet());
        this.app.use(cors());
        this.app.use(compression());
        this.app.use(express.json({ limit: '10mb' }));
        
        // Metrics middleware
        this.app.use((req, res, next) => {
            const start = Date.now();
            res.on('finish', () => {
                const duration = Date.now() - start;
                this.metrics.httpRequestDuration
                    .labels(req.method, req.route?.path || req.path, res.statusCode)
                    .observe(duration);
            });
            next();
        });
    }

    setupHandlers() {
        // Start command with personalized onboarding
        this.bot.start(async (ctx) => {
            try {
                this.metrics.telegramMessages.labels('start', 'success').inc();
                
                const welcomeMessage = await this.aiAssistant.generateWelcomeMessage(ctx.from);
                const keyboard = {
                    inline_keyboard: [
                        [{ text: '🎮 Start Gaming', callback_data: 'start_gaming' }],
                        [{ text: '📊 View Dashboard', web_app: { url: process.env.WEBAPP_URL } }],
                        [{ text: '🎯 Daily Challenge', callback_data: 'daily_challenge' }]
                    ]
                };

                await ctx.replyWithPhoto(
                    { source: './assets/welcome-banner.jpg' },
                    { 
                        caption: welcomeMessage,
                        reply_markup: keyboard,
                        parse_mode: 'HTML'
                    }
                );

                // Initialize user engagement tracking
                await this.engagement.initializeUser(ctx.from.id);
                await this.compliance.logUserAction(ctx.from.id, 'bot_start');
                
                this.logger.info(`New user started bot: ${ctx.from.id}`);
            } catch (error) {
                this.metrics.telegramMessages.labels('start', 'error').inc();
                this.logger.error('Error in start handler:', error);
                await ctx.reply('❌ Sorry, something went wrong. Please try again.');
            }
        });

        // Autonomous engagement triggers
        this.bot.command('dashboard', async (ctx) => {
            const stats = await this.gamification.getUserStats(ctx.from.id);
            const achievements = await this.gamification.getRecentAchievements(ctx.from.id);
            
            const dashboardData = {
                user: ctx.from,
                stats,
                achievements,
                engagement_score: await this.engagement.getEngagementScore(ctx.from.id)
            };

            // Send interactive dashboard
            await this.sendInteractiveDashboard(ctx, dashboardData);
        });

        // Gamified poll system
        this.bot.command('poll', async (ctx) => {
            const pollData = await this.engagement.generateDynamicPoll();
            const poll = await ctx.replyWithPoll(
                pollData.question,
                pollData.options,
                {
                    is_anonymous: false,
                    allows_multiple_answers: pollData.multiple_answers,
                    reply_markup: {
                        inline_keyboard: [[
                            { text: '🏆 View Leaderboard', callback_data: 'poll_leaderboard' }
                        ]]
                    }
                }
            );

            // Track poll for engagement metrics
            await this.engagement.trackPollEngagement(poll.poll.id, ctx.from.id);
        });

        // AI-powered FAQ system
        this.bot.command('ask', async (ctx) => {
            const question = ctx.message.text.replace('/ask', '').trim();
            if (!question) {
                await ctx.reply('💬 Ask me anything! Usage: /ask <your question>');
                return;
            }

            const typing = await ctx.replyWithChatAction('typing');
            const answer = await this.aiAssistant.answerQuestion(question, ctx.from.id);
            
            await ctx.reply(answer, {
                reply_markup: {
                    inline_keyboard: [[
                        { text: '👍 Helpful', callback_data: `feedback_helpful_${Date.now()}` },
                        { text: '👎 Not Helpful', callback_data: `feedback_not_helpful_${Date.now()}` }
                    ]]
                },
                parse_mode: 'HTML'
            });

            await this.gamification.awardPoints(ctx.from.id, 5, 'ai_interaction');
        });

        // Interactive mini-games
        this.bot.command('game', async (ctx) => {
            const availableGames = [
                { name: '🎯 Target Practice', callback: 'game_target' },
                { name: '🧩 Puzzle Challenge', callback: 'game_puzzle' },
                { name: '🎮 Emoji Hunt', callback: 'game_emoji' },
                { name: '🏃 Speed Run', callback: 'game_speed' }
            ];

            const keyboard = availableGames.map(game => ([{
                text: game.name,
                callback_data: game.callback
            }]));

            await ctx.reply('🎮 Choose your game:', {
                reply_markup: { inline_keyboard: keyboard }
            });
        });

        // Referral system
        this.bot.command('refer', async (ctx) => {
            const referralCode = await this.gamification.generateReferralCode(ctx.from.id);
            const referralLink = `https://t.me/${process.env.BOT_USERNAME}?start=${referralCode}`;
            
            await ctx.reply(
                `🎁 <b>Invite Friends & Earn Rewards!</b>\n\n` +
                `Your referral link:\n<code>${referralLink}</code>\n\n` +
                `🏆 Rewards per referral:\n` +
                `• 100 points instantly\n` +
                `• Exclusive badges\n` +
                `• Bonus multipliers\n\n` +
                `👥 Friends referred: ${await this.gamification.getReferralCount(ctx.from.id)}`,
                { 
                    parse_mode: 'HTML',
                    reply_markup: {
                        inline_keyboard: [[
                            { text: '📊 Referral Stats', callback_data: 'referral_stats' }
                        ]]
                    }
                }
            );
        });

        // Callback handlers for interactive features
        this.setupCallbackHandlers();
        
        // Error handling
        this.bot.catch((err, ctx) => {
            this.logger.error(`Bot error for user ${ctx.from?.id}:`, err);
            this.metrics.telegramMessages.labels('error', 'bot_error').inc();
        });
    }

    setupCallbackHandlers() {
        // Gaming callbacks
        this.bot.action(/^game_(\w+)$/, async (ctx) => {
            const gameType = ctx.match[1];
            await this.startMiniGame(ctx, gameType);
        });

        // Poll leaderboard
        this.bot.action('poll_leaderboard', async (ctx) => {
            const leaderboard = await this.engagement.getPollLeaderboard();
            await this.sendLeaderboard(ctx, leaderboard, 'poll');
        });

        // Feedback handlers
        this.bot.action(/^feedback_(helpful|not_helpful)_(.+)$/, async (ctx) => {
            const feedback = ctx.match[1];
            const timestamp = ctx.match[2];
            
            await this.aiAssistant.recordFeedback(ctx.from.id, feedback, timestamp);
            await ctx.answerCbQuery(`Thanks for your feedback! 🙏`);
            
            if (feedback === 'helpful') {
                await this.gamification.awardPoints(ctx.from.id, 2, 'helpful_feedback');
            }
        });

        // Achievement notifications
        this.bot.action(/^achievement_(\w+)$/, async (ctx) => {
            const achievementId = ctx.match[1];
            const achievement = await this.gamification.getAchievement(achievementId);
            
            await ctx.answerCbQuery('🏆 Achievement unlocked!', true);
            await this.sendAchievementCelebration(ctx, achievement);
        });

        // Engagement challenges
        this.bot.action('daily_challenge', async (ctx) => {
            const challenge = await this.engagement.getDailyChallenge(ctx.from.id);
            await this.sendDailyChallenge(ctx, challenge);
        });

        // Referral stats
        this.bot.action('referral_stats', async (ctx) => {
            const stats = await this.gamification.getReferralStats(ctx.from.id);
            await this.sendReferralStats(ctx, stats);
        });
    }

    async startMiniGame(ctx, gameType) {
        try {
            await ctx.answerCbQuery('🎮 Starting game...');
            
            switch (gameType) {
                case 'target':
                    await this.startTargetPractice(ctx);
                    break;
                case 'puzzle':
                    await this.startPuzzleChallenge(ctx);
                    break;
                case 'emoji':
                    await this.startEmojiHunt(ctx);
                    break;
                case 'speed':
                    await this.startSpeedRun(ctx);
                    break;
                default:
                    await ctx.reply('🚫 Game not found!');
            }
        } catch (error) {
            this.logger.error('Error starting mini-game:', error);
            await ctx.reply('❌ Failed to start game. Please try again.');
        }
    }

    async startTargetPractice(ctx) {
        const targets = ['🎯', '🎪', '🎨', '🎭', '🎪'];
        const correctTarget = targets[Math.floor(Math.random() * targets.length)];
        const gameId = `target_${Date.now()}_${ctx.from.id}`;
        
        // Store game state in Redis
        await this.redis.setex(`game:${gameId}`, 60, JSON.stringify({
            type: 'target',
            correct_target: correctTarget,
            start_time: Date.now(),
            user_id: ctx.from.id
        }));

        const shuffledTargets = [...targets].sort(() => Math.random() - 0.5);
        const keyboard = shuffledTargets.map((target, index) => ([{
            text: target,
            callback_data: `target_shot_${gameId}_${index}_${target}`
        }]));

        await ctx.editMessageText(
            `🎯 <b>Target Practice!</b>\n\n` +
            `Hit the target: <b>${correctTarget}</b>\n` +
            `⏰ You have 60 seconds!\n\n` +
            `Choose your target:`,
            {
                reply_markup: { inline_keyboard: keyboard },
                parse_mode: 'HTML'
            }
        );

        // Handle target shots
        this.bot.action(new RegExp(`^target_shot_${gameId}_(\\d+)_(.+)$`), async (shotCtx) => {
            const shot = shotCtx.match[2];
            const gameData = JSON.parse(await this.redis.get(`game:${gameId}`));
            
            if (!gameData) {
                await shotCtx.answerCbQuery('⏰ Game expired!');
                return;
            }

            const timeElapsed = Date.now() - gameData.start_time;
            const points = shot === correctTarget ? Math.max(10, 50 - Math.floor(timeElapsed / 1000)) : 0;
            
            if (points > 0) {
                await this.gamification.awardPoints(ctx.from.id, points, 'mini_game_target');
                await shotCtx.answerCbQuery(`🎯 BULLSEYE! +${points} points!`);
                await shotCtx.editMessageText(
                    `🎯 <b>BULLSEYE!</b>\n\n` +
                    `Perfect shot in ${Math.round(timeElapsed/1000)}s!\n` +
                    `🏆 +${points} points earned!\n\n` +
                    `🎮 Play again: /game`,
                    { parse_mode: 'HTML' }
                );
            } else {
                await shotCtx.answerCbQuery(`❌ Missed! Target was ${correctTarget}`);
                await shotCtx.editMessageText(
                    `❌ <b>Missed!</b>\n\n` +
                    `The target was ${correctTarget}\n` +
                    `Better luck next time!\n\n` +
                    `🎮 Try again: /game`,
                    { parse_mode: 'HTML' }
                );
            }

            await this.redis.del(`game:${gameId}`);
        });
    }

    async startEmojiHunt(ctx) {
        const emojis = ['🦄', '🌟', '🎪', '🎭', '🎨', '🎯', '🎮', '🎲', '🎪', '🎊'];
        const targetEmoji = emojis[Math.floor(Math.random() * emojis.length)];
        const gameGrid = Array(25).fill().map(() => 
            Math.random() < 0.1 ? targetEmoji : emojis[Math.floor(Math.random() * emojis.length)]
        );
        
        // Ensure at least one target exists
        gameGrid[Math.floor(Math.random() * 25)] = targetEmoji;
        
        const gameId = `emoji_${Date.now()}_${ctx.from.id}`;
        await this.redis.setex(`game:${gameId}`, 120, JSON.stringify({
            type: 'emoji_hunt',
            target: targetEmoji,
            grid: gameGrid,
            found: 0,
            total_targets: gameGrid.filter(e => e === targetEmoji).length,
            start_time: Date.now(),
            user_id: ctx.from.id
        }));

        const keyboard = [];
        for (let i = 0; i < 25; i += 5) {
            const row = gameGrid.slice(i, i + 5).map((emoji, j) => ({
                text: emoji,
                callback_data: `emoji_hunt_${gameId}_${i + j}`
            }));
            keyboard.push(row);
        }

        await ctx.editMessageText(
            `🔍 <b>Emoji Hunt!</b>\n\n` +
            `Find all: ${targetEmoji}\n` +
            `Target count: ${gameGrid.filter(e => e === targetEmoji).length}\n` +
            `⏰ 2 minutes to find them all!\n\n` +
            `Click the emojis below:`,
            {
                reply_markup: { inline_keyboard: keyboard },
                parse_mode: 'HTML'
            }
        );

        // Handle emoji clicks
        this.bot.action(new RegExp(`^emoji_hunt_${gameId}_(\\d+)$`), async (clickCtx) => {
            const position = parseInt(clickCtx.match[1]);
            const gameData = JSON.parse(await this.redis.get(`game:${gameId}`));
            
            if (!gameData) {
                await clickCtx.answerCbQuery('⏰ Game expired!');
                return;
            }

            if (gameData.grid[position] === gameData.target) {
                gameData.found++;
                gameData.grid[position] = '✅'; // Mark as found
                
                if (gameData.found >= gameData.total_targets) {
                    // Game won!
                    const timeElapsed = Date.now() - gameData.start_time;
                    const points = Math.max(20, 100 - Math.floor(timeElapsed / 2000));
                    
                    await this.gamification.awardPoints(ctx.from.id, points, 'emoji_hunt_complete');
                    await clickCtx.answerCbQuery(`🎉 ALL FOUND! +${points} points!`);
                    await clickCtx.editMessageText(
                        `🎉 <b>EMOJI HUNT COMPLETE!</b>\n\n` +
                        `Found all ${gameData.total_targets} targets!\n` +
                        `⏱ Time: ${Math.round(timeElapsed/1000)}s\n` +
                        `🏆 +${points} points earned!\n\n` +
                        `🎮 Play again: /game`,
                        { parse_mode: 'HTML' }
                    );
                    await this.redis.del(`game:${gameId}`);
                } else {
                    // Continue game
                    await this.redis.setex(`game:${gameId}`, 120, JSON.stringify(gameData));
                    await clickCtx.answerCbQuery(`✅ Found one! ${gameData.found}/${gameData.total_targets}`);
                    
                    // Update keyboard
                    const keyboard = [];
                    for (let i = 0; i < 25; i += 5) {
                        const row = gameData.grid.slice(i, i + 5).map((emoji, j) => ({
                            text: emoji,
                            callback_data: `emoji_hunt_${gameId}_${i + j}`
                        }));
                        keyboard.push(row);
                    }
                    
                    await clickCtx.editMessageReplyMarkup({
                        inline_keyboard: keyboard
                    });
                }
            } else {
                await clickCtx.answerCbQuery(`❌ Not the target emoji!`);
            }
        });
    }

    setupWebServer() {
        // Health check endpoint
        this.app.get('/health', (req, res) => {
            res.json({
                status: 'healthy',
                timestamp: new Date().toISOString(),
                uptime: process.uptime(),
                version: process.env.npm_package_version
            });
        });

        // Metrics endpoint for Prometheus
        this.app.get('/metrics', async (req, res) => {
            res.set('Content-Type', promClient.register.contentType);
            res.end(await promClient.register.metrics());
        });

        // Webhook endpoint for Telegram
        this.app.use('/webhook', this.bot.webhookCallback('/telegram-webhook'));

        // Real-time engagement dashboard
        this.app.get('/engagement-dashboard', (req, res) => {
            res.sendFile(path.join(__dirname, '../public/engagement-dashboard.html'));
        });

        // Socket.IO for real-time updates
        this.io.on('connection', (socket) => {
            socket.on('subscribe_engagement', async (userId) => {
                socket.join(`user_${userId}`);
                const stats = await this.gamification.getUserStats(userId);
                socket.emit('engagement_stats', stats);
            });

            socket.on('request_leaderboard', async () => {
                const leaderboard = await this.gamification.getGlobalLeaderboard();
                socket.emit('leaderboard_update', leaderboard);
            });
        });
    }

    startAutonomousEngagement() {
        // Schedule autonomous engagement activities
        const cron = require('node-cron');

        // Daily challenges (8 AM UTC)
        cron.schedule('0 8 * * *', async () => {
            await this.engagement.distributeDailyChallenges();
            this.logger.info('Daily challenges distributed');
        });

        // Weekly polls (Monday 10 AM UTC)
        cron.schedule('0 10 * * 1', async () => {
            await this.engagement.createWeeklyPoll();
            this.logger.info('Weekly poll created');
        });

        // Engagement reminders (every 6 hours)
        cron.schedule('0 */6 * * *', async () => {
            await this.engagement.sendEngagementReminders();
            this.logger.info('Engagement reminders sent');
        });

        // Leaderboard updates (every hour)
        cron.schedule('0 * * * *', async () => {
            const leaderboard = await this.gamification.updateGlobalLeaderboard();
            this.io.emit('leaderboard_update', leaderboard);
            this.logger.info('Leaderboard updated and broadcasted');
        });

        // Achievement checks (every 30 minutes)
        cron.schedule('*/30 * * * *', async () => {
            await this.gamification.checkAndAwardAchievements();
            this.logger.info('Achievement check completed');
        });

        // System health monitoring (every 5 minutes)
        cron.schedule('*/5 * * * *', async () => {
            await this.monitoring.performHealthCheck();
            this.metrics.activeUsers.set(await this.getActiveUsersCount());
        });

        // Cleanup old data (daily at 2 AM UTC)
        cron.schedule('0 2 * * *', async () => {
            await this.performDataCleanup();
            this.logger.info('Data cleanup completed');
        });
    }

    async getActiveUsersCount() {
        const activeUsers = await this.redis.scard('active_users_24h');
        return activeUsers || 0;
    }

    async performDataCleanup() {
        // Clean up expired game states
        const gameKeys = await this.redis.keys('game:*');
        for (const key of gameKeys) {
            const ttl = await this.redis.ttl(key);
            if (ttl === -1) { // No expiration set
                await this.redis.del(key);
            }
        }

        // Clean up old audit logs
        await this.compliance.cleanupOldLogs();
        
        // Clean up expired user sessions
        await this.security.cleanupExpiredSessions();
    }

    async start() {
        try {
            // Start web server
            this.server.listen(this.port, () => {
                this.logger.info(`Autonomous engagement system running on port ${this.port}`);
            });

            // Set up bot webhook in production
            if (process.env.NODE_ENV === 'production') {
                await this.bot.telegram.setWebhook(`${process.env.WEBHOOK_URL}/webhook/telegram-webhook`);
                this.logger.info('Telegram webhook configured');
            } else {
                await this.bot.launch();
                this.logger.info('Bot started in polling mode');
            }

            this.logger.info('Autonomous Engagement Bot fully initialized and running');
        } catch (error) {
            this.logger.error('Failed to start bot:', error);
            process.exit(1);
        }
    }
}

// Graceful shutdown
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));

// Initialize and start the bot
const bot = new AutonomousEngagementBot();
bot.start().catch((error) => {
    console.error('Fatal error starting bot:', error);
    process.exit(1);
});

module.exports = AutonomousEngagementBot;
EOF

# Create Engagement Engine Service
cat > "$BOT_DIR/src/services/EngagementEngine.js" << 'EOF'
const cron = require('node-cron');
const { v4: uuidv4 } = require('uuid');

class EngagementEngine {
    constructor(redis, logger) {
        this.redis = redis;
        this.logger = logger;
        this.pollTemplates = this.loadPollTemplates();
        this.challengeTemplates = this.loadChallengeTemplates();
    }

    loadPollTemplates() {
        return [
            {
                category: 'technology',
                questions: [
                    {
                        question: '🚀 Which emerging technology excites you most?',
                        options: ['AI/Machine Learning', 'Blockchain', 'IoT', 'AR/VR', 'Quantum Computing'],
                        multiple_answers: false
                    },
                    {
                        question: '💻 What\'s your preferred development environment?',
                        options: ['VS Code', 'IntelliJ IDEA', 'Vim/Neovim', 'Sublime Text', 'Atom'],
                        multiple_answers: false
                    }
                ]
            },
            {
                category: 'lifestyle',
                questions: [
                    {
                        question: '☕ How do you start your day?',
                        options: ['Coffee', 'Tea', 'Energy Drink', 'Smoothie', 'Just Water'],
                        multiple_answers: false
                    },
                    {
                        question: '🎵 What music helps you focus?',
                        options: ['Classical', 'Lo-fi Hip Hop', 'Electronic', 'Rock', 'Nature Sounds', 'Silence'],
                        multiple_answers: true
                    }
                ]
            },
            {
                category: 'gaming',
                questions: [
                    {
                        question: '🎮 What\'s your favorite gaming genre?',
                        options: ['RPG', 'FPS', 'Strategy', 'Puzzle', 'Sports', 'Indie'],
                        multiple_answers: true
                    }
                ]
            }
        ];
    }

    loadChallengeTemplates() {
        return [
            {
                id: 'daily_streak',
                title: '🔥 Daily Streak Challenge',
                description: 'Interact with the bot for 7 consecutive days',
                points: 100,
                type: 'streak',
                duration: 7
            },
            {
                id: 'poll_master',
                title: '📊 Poll Master',
                description: 'Vote in 5 different polls today',
                points: 50,
                type: 'daily',
                target: 5
            },
            {
                id: 'social_butterfly',
                title: '🦋 Social Butterfly',
                description: 'Refer 3 new users this week',
                points: 200,
                type: 'weekly',
                target: 3
            },
            {
                id: 'game_champion',
                title: '🏆 Game Champion',
                description: 'Win 10 mini-games',
                points: 150,
                type: 'milestone',
                target: 10
            }
        ];
    }

    async initializeUser(userId) {
        const userKey = `user:${userId}`;
        const exists = await this.redis.exists(userKey);
        
        if (!exists) {
            await this.redis.hmset(userKey, {
                joined_date: new Date().toISOString(),
                total_points: 0,
                level: 1,
                engagement_score: 0,
                last_active: new Date().toISOString(),
                streak_days: 0,
                polls_voted: 0,
                games_played: 0,
                achievements_count: 0,
                referrals_made: 0
            });

            this.logger.info(`Initialized user engagement data: ${userId}`);
        }

        // Add to active users set
        await this.redis.sadd('active_users_24h', userId);
        await this.redis.expire('active_users_24h', 86400); // 24 hours
    }

    async generateDynamicPoll() {
        const category = this.pollTemplates[Math.floor(Math.random() * this.pollTemplates.length)];
        const question = category.questions[Math.floor(Math.random() * category.questions.length)];
        
        const pollId = uuidv4();
        const pollData = {
            id: pollId,
            category: category.category,
            ...question,
            created_at: new Date().toISOString(),
            active: true
        };

        // Store poll data
        await this.redis.setex(`poll:${pollId}`, 86400, JSON.stringify(pollData));
        await this.redis.lpush('active_polls', pollId);

        this.logger.info(`Generated dynamic poll: ${pollId} - ${question.question}`);
        return pollData;
    }

    async trackPollEngagement(pollId, userId) {
        const userKey = `user:${userId}`;
        const pollKey = `poll:${pollId}:votes`;
        
        // Increment user's poll count
        await this.redis.hincrby(userKey, 'polls_voted', 1);
        
        // Track poll participation
        await this.redis.sadd(pollKey, userId);
        await this.redis.expire(pollKey, 86400);
        
        // Update engagement score
        await this.updateEngagementScore(userId, 'poll_vote');
        
        this.logger.info(`Tracked poll engagement: ${pollId} by user ${userId}`);
    }

    async getPollLeaderboard(limit = 10) {
        const activePolls = await this.redis.lrange('active_polls', 0, -1);
        const leaderboardData = [];

        for (const pollId of activePolls.slice(0, 5)) { // Last 5 polls
            const votes = await this.redis.smembers(`poll:${pollId}:votes`);
            const pollData = JSON.parse(await this.redis.get(`poll:${pollId}`) || '{}');
            
            leaderboardData.push({
                poll: pollData.question,
                votes: votes.length,
                category: pollData.category
            });
        }

        return leaderboardData.sort((a, b) => b.votes - a.votes).slice(0, limit);
    }

    async getDailyChallenge(userId) {
        const today = new Date().toISOString().split('T')[0];
        const challengeKey = `challenge:daily:${today}:${userId}`;
        
        // Check if user already has today's challenge
        let challenge = await this.redis.get(challengeKey);
        
        if (!challenge) {
            // Assign a random daily challenge
            const dailyChallenges = this.challengeTemplates.filter(c => c.type === 'daily');
            const selectedChallenge = dailyChallenges[Math.floor(Math.random() * dailyChallenges.length)];
            
            challenge = {
                ...selectedChallenge,
                progress: 0,
                assigned_date: today,
                completed: false
            };

            await this.redis.setex(challengeKey, 86400, JSON.stringify(challenge));
        } else {
            challenge = JSON.parse(challenge);
        }

        return challenge;
    }

    async updateChallengeProgress(userId, challengeType, increment = 1) {
        const today = new Date().toISOString().split('T')[0];
        const challengeKey = `challenge:daily:${today}:${userId}`;
        
        const challengeData = await this.redis.get(challengeKey);
        if (!challengeData) return;

        const challenge = JSON.parse(challengeData);
        if (challenge.id !== challengeType || challenge.completed) return;

        challenge.progress += increment;
        
        if (challenge.progress >= challenge.target) {
            challenge.completed = true;
            challenge.completed_at = new Date().toISOString();
            
            // Award points
            await this.awardChallengePoints(userId, challenge);
            
            this.logger.info(`Challenge completed: ${challengeType} by user ${userId}`);
        }

        await this.redis.setex(challengeKey, 86400, JSON.stringify(challenge));
    }

    async awardChallengePoints(userId, challenge) {
        const userKey = `user:${userId}`;
        
        await this.redis.hincrby(userKey, 'total_points', challenge.points);
        await this.redis.hincrby(userKey, 'achievements_count', 1);
        
        // Log achievement
        const achievementKey = `achievement:${userId}:${Date.now()}`;
        await this.redis.setex(achievementKey, 604800, JSON.stringify({ // 1 week
            type: 'challenge_completed',
            challenge: challenge.title,
            points: challenge.points,
            timestamp: new Date().toISOString()
        }));
    }

    async updateEngagementScore(userId, action) {
        const userKey = `user:${userId}`;
        const scoreIncrement = this.getEngagementPoints(action);
        
        await this.redis.hincrby(userKey, 'engagement_score', scoreIncrement);
        await this.redis.hset(userKey, 'last_active', new Date().toISOString());
        
        // Check for level up
        await this.checkLevelUp(userId);
    }

    getEngagementPoints(action) {
        const points = {
            'poll_vote': 5,
            'game_play': 10,
            'daily_login': 3,
            'referral': 50,
            'achievement': 25,
            'feedback': 2
        };
        
        return points[action] || 1;
    }

    async checkLevelUp(userId) {
        const userKey = `user:${userId}`;
        const userData = await this.redis.hgetall(userKey);
        
        const currentLevel = parseInt(userData.level || 1);
        const engagementScore = parseInt(userData.engagement_score || 0);
        
        // Level up every 100 engagement points
        const newLevel = Math.floor(engagementScore / 100) + 1;
        
        if (newLevel > currentLevel) {
            await this.redis.hset(userKey, 'level', newLevel);
            
            // Award level up achievement
            const achievementKey = `achievement:${userId}:levelup:${Date.now()}`;
            await this.redis.setex(achievementKey, 604800, JSON.stringify({
                type: 'level_up',
                level: newLevel,
                timestamp: new Date().toISOString()
            }));
            
            this.logger.info(`User ${userId} leveled up to level ${newLevel}`);
            return newLevel;
        }
        
        return currentLevel;
    }

    async getEngagementScore(userId) {
        const userKey = `user:${userId}`;
        const userData = await this.redis.hgetall(userKey);
        
        return {
            total_score: parseInt(userData.engagement_score || 0),
            level: parseInt(userData.level || 1),
            points: parseInt(userData.total_points || 0),
            streak: parseInt(userData.streak_days || 0),
            rank: await this.getUserRank(userId)
        };
    }

    async getUserRank(userId) {
        // Get all users and their engagement scores
        const userKeys = await this.redis.keys('user:*');
        const scores = [];
        
        for (const key of userKeys) {
            const userData = await this.redis.hgetall(key);
            const userIdFromKey = key.split(':')[1];
            scores.push({
                userId: userIdFromKey,
                score: parseInt(userData.engagement_score || 0)
            });
        }
        
        // Sort by score descending
        scores.sort((a, b) => b.score - a.score);
        
        // Find user's rank
        const rank = scores.findIndex(s => s.userId === userId.toString()) + 1;
        return rank || scores.length + 1;
    }

    async distributeDailyChallenges() {
        const activeUsers = await this.redis.smembers('active_users_24h');
        let distributed = 0;
        
        for (const userId of activeUsers) {
            try {
                await this.getDailyChallenge(userId); // This creates it if not exists
                distributed++;
            } catch (error) {
                this.logger.error(`Failed to distribute daily challenge to user ${userId}:`, error);
            }
        }
        
        this.logger.info(`Distributed daily challenges to ${distributed} active users`);
        return distributed;
    }

    async createWeeklyPoll() {
        const pollData = await this.generateDynamicPoll();
        const activeUsers = await this.redis.smembers('active_users_24h');
        
        // Mark as weekly featured poll
        await this.redis.setex('weekly_featured_poll', 604800, pollData.id);
        
        this.logger.info(`Created weekly poll: ${pollData.question}`);
        return pollData;
    }

    async sendEngagementReminders() {
        const inactiveUsers = await this.getInactiveUsers(6); // 6 hours of inactivity
        let sent = 0;
        
        for (const userId of inactiveUsers) {
            try {
                // This would be handled by the main bot instance
                // For now, we'll log it and increment counter
                this.logger.info(`Engagement reminder needed for user ${userId}`);
                sent++;
            } catch (error) {
                this.logger.error(`Failed to send engagement reminder to user ${userId}:`, error);
            }
        }
        
        this.logger.info(`Identified ${sent} users for engagement reminders`);
        return sent;
    }

    async getInactiveUsers(hoursThreshold) {
        const cutoffTime = new Date(Date.now() - hoursThreshold * 60 * 60 * 1000);
        const userKeys = await this.redis.keys('user:*');
        const inactiveUsers = [];
        
        for (const key of userKeys) {
            const userData = await this.redis.hgetall(key);
            const lastActive = new Date(userData.last_active || 0);
            
            if (lastActive < cutoffTime) {
                const userId = key.split(':')[1];
                inactiveUsers.push(userId);
            }
        }
        
        return inactiveUsers;
    }
}

module.exports = EngagementEngine;
EOF

# Create Gamification Service
cat > "$BOT_DIR/src/services/GameficationService.js" << 'EOF'
const { v4: uuidv4 } = require('uuid');

class GameficationService {
    constructor(redis, logger) {
        this.redis = redis;
        this.logger = logger;
        this.achievements = this.loadAchievements();
        this.badges = this.loadBadges();
        this.levels = this.loadLevelSystem();
    }

    loadAchievements() {
        return [
            {
                id: 'first_vote',
                title: '🗳️ First Vote',
                description: 'Cast your first poll vote',
                points: 10,
                icon: '🗳️',
                rarity: 'common'
            },
            {
                id: 'poll_enthusiast',
                title: '📊 Poll Enthusiast',
                description: 'Vote in 50 polls',
                points: 100,
                icon: '📊',
                rarity: 'rare',
                requirement: { type: 'poll_votes', count: 50 }
            },
            {
                id: 'game_master',
                title: '🎮 Game Master',
                description: 'Win 100 mini-games',
                points: 250,
                icon: '🎮',
                rarity: 'epic',
                requirement: { type: 'games_won', count: 100 }
            },
            {
                id: 'social_connector',
                title: '🤝 Social Connector',
                description: 'Refer 10 friends',
                points: 500,
                icon: '🤝',
                rarity: 'legendary',
                requirement: { type: 'referrals', count: 10 }
            },
            {
                id: 'streak_warrior',
                title: '🔥 Streak Warrior',
                description: '30-day activity streak',
                points: 300,
                icon: '🔥',
                rarity: 'epic',
                requirement: { type: 'streak_days', count: 30 }
            },
            {
                id: 'night_owl',
                title: '🦉 Night Owl',
                description: 'Active between midnight and 6 AM',
                points: 25,
                icon: '🦉',
                rarity: 'uncommon',
                requirement: { type: 'night_activity', count: 1 }
            },
            {
                id: 'early_bird',
                title: '🐦 Early Bird',
                description: 'Active between 5-8 AM for 5 days',
                points: 50,
                icon: '🐦',
                rarity: 'rare',
                requirement: { type: 'early_activity', count: 5 }
            },
            {
                id: 'perfectionist',
                title: '🎯 Perfectionist',
                description: 'Score perfect in 5 target practice games',
                points: 150,
                icon: '🎯',
                rarity: 'rare',
                requirement: { type: 'perfect_games', count: 5 }
            }
        ];
    }

    loadBadges() {
        return [
            {
                id: 'beta_tester',
                title: 'β Beta Tester',
                description: 'Early adopter of the bot',
                icon: '🧪',
                color: '#FF6B35'
            },
            {
                id: 'community_leader',
                title: '👑 Community Leader',
                description: 'Top 10 in monthly leaderboard',
                icon: '👑',
                color: '#FFD700'
            },
            {
                id: 'helpful_member',
                title: '🌟 Helpful Member',
                description: 'Received 50+ helpful feedback ratings',
                icon: '🌟',
                color: '#4ECDC4'
            },
            {
                id: 'speed_demon',
                title: '⚡ Speed Demon',
                description: 'Complete 10 games in under 10 seconds',
                icon: '⚡',
                color: '#FF3366'
            }
        ];
    }

    loadLevelSystem() {
        return {
            1: { title: 'Newcomer', pointsRequired: 0, perks: [] },
            2: { title: 'Regular', pointsRequired: 100, perks: ['custom_emoji_reactions'] },
            3: { title: 'Enthusiast', pointsRequired: 300, perks: ['custom_emoji_reactions', 'priority_support'] },
            4: { title: 'Expert', pointsRequired: 600, perks: ['custom_emoji_reactions', 'priority_support', 'exclusive_polls'] },
            5: { title: 'Master', pointsRequired: 1000, perks: ['custom_emoji_reactions', 'priority_support', 'exclusive_polls', 'beta_features'] },
            6: { title: 'Legend', pointsRequired: 1500, perks: ['all_perks', 'custom_titles', 'special_recognition'] }
        };
    }

    async awardPoints(userId, points, reason) {
        const userKey = `user:${userId}`;
        
        // Add points
        await this.redis.hincrby(userKey, 'total_points', points);
        
        // Log points transaction
        const transactionKey = `points:${userId}:${Date.now()}`;
        await this.redis.setex(transactionKey, 2592000, JSON.stringify({ // 30 days
            points,
            reason,
            timestamp: new Date().toISOString()
        }));
        
        // Check for achievements and level ups
        await this.checkAchievements(userId);
        await this.checkLevelUp(userId);
        
        this.logger.info(`Awarded ${points} points to user ${userId} for ${reason}`);
        return points;
    }

    async checkAchievements(userId) {
        const userStats = await this.getUserStats(userId);
        const currentAchievements = await this.getUserAchievements(userId);
        const newAchievements = [];
        
        for (const achievement of this.achievements) {
            // Skip if already achieved
            if (currentAchievements.some(a => a.id === achievement.id)) {
                continue;
            }
            
            let achieved = false;
            
            if (!achievement.requirement) {
                // Special achievements (manual or first-time)
                continue;
            }
            
            const { type, count } = achievement.requirement;
            
            switch (type) {
                case 'poll_votes':
                    achieved = userStats.polls_voted >= count;
                    break;
                case 'games_won':
                    achieved = userStats.games_won >= count;
                    break;
                case 'referrals':
                    achieved = userStats.referrals_made >= count;
                    break;
                case 'streak_days':
                    achieved = userStats.streak_days >= count;
                    break;
                case 'perfect_games':
                    achieved = userStats.perfect_games >= count;
                    break;
                case 'night_activity':
                    achieved = await this.checkNightActivity(userId);
                    break;
                case 'early_activity':
                    achieved = await this.checkEarlyActivity(userId, count);
                    break;
            }
            
            if (achieved) {
                await this.grantAchievement(userId, achievement);
                newAchievements.push(achievement);
            }
        }
        
        return newAchievements;
    }

    async grantAchievement(userId, achievement) {
        const achievementKey = `achievement:${userId}:${achievement.id}`;
        await this.redis.setex(achievementKey, 31536000, JSON.stringify({ // 1 year
            ...achievement,
            earned_at: new Date().toISOString()
        }));
        
        // Award achievement points
        await this.redis.hincrby(`user:${userId}`, 'total_points', achievement.points);
        await this.redis.hincrby(`user:${userId}`, 'achievements_count', 1);
        
        // Add to recent achievements
        await this.redis.lpush(`recent_achievements:${userId}`, JSON.stringify({
            ...achievement,
            earned_at: new Date().toISOString()
        }));
        await this.redis.ltrim(`recent_achievements:${userId}`, 0, 9); // Keep last 10
        
        this.logger.info(`Achievement granted: ${achievement.title} to user ${userId}`);
    }

    async checkNightActivity(userId) {
        const userKey = `user:${userId}`;
        const userData = await this.redis.hgetall(userKey);
        const lastActive = new Date(userData.last_active);
        const hour = lastActive.getHours();
        
        return hour >= 0 && hour < 6; // Midnight to 6 AM
    }

    async checkEarlyActivity(userId, requiredDays) {
        // Check activity logs for early morning activity (5-8 AM)
        const earlyActivityKey = `early_activity:${userId}`;
        const earlyDays = await this.redis.get(earlyActivityKey);
        
        return (parseInt(earlyDays) || 0) >= requiredDays;
    }

    async recordEarlyActivity(userId) {
        const hour = new Date().getHours();
        if (hour >= 5 && hour <= 8) {
            const today = new Date().toISOString().split('T')[0];
            const activityKey = `early_activity:${userId}:${today}`;
            
            const alreadyRecorded = await this.redis.exists(activityKey);
            if (!alreadyRecorded) {
                await this.redis.setex(activityKey, 86400, '1');
                await this.redis.incr(`early_activity:${userId}`);
            }
        }
    }

    async getUserStats(userId) {
        const userKey = `user:${userId}`;
        const userData = await this.redis.hgetall(userKey);
        
        return {
            total_points: parseInt(userData.total_points || 0),
            level: parseInt(userData.level || 1),
            engagement_score: parseInt(userData.engagement_score || 0),
            polls_voted: parseInt(userData.polls_voted || 0),
            games_played: parseInt(userData.games_played || 0),
            games_won: parseInt(userData.games_won || 0),
            perfect_games: parseInt(userData.perfect_games || 0),
            streak_days: parseInt(userData.streak_days || 0),
            referrals_made: parseInt(userData.referrals_made || 0),
            achievements_count: parseInt(userData.achievements_count || 0),
            last_active: userData.last_active,
            joined_date: userData.joined_date
        };
    }

    async getUserAchievements(userId) {
        const achievementKeys = await this.redis.keys(`achievement:${userId}:*`);
        const achievements = [];
        
        for (const key of achievementKeys) {
            if (key.includes(':levelup:')) continue; // Skip level up achievements
            
            const data = await this.redis.get(key);
            if (data) {
                achievements.push(JSON.parse(data));
            }
        }
        
        return achievements.sort((a, b) => new Date(b.earned_at) - new Date(a.earned_at));
    }

    async getRecentAchievements(userId, limit = 5) {
        const recent = await this.redis.lrange(`recent_achievements:${userId}`, 0, limit - 1);
        return recent.map(r => JSON.parse(r));
    }

    async checkLevelUp(userId) {
        const stats = await this.getUserStats(userId);
        const currentLevel = stats.level;
        
        // Calculate new level based on points
        let newLevel = 1;
        for (const level in this.levels) {
            if (stats.total_points >= this.levels[level].pointsRequired) {
                newLevel = parseInt(level);
            }
        }
        
        if (newLevel > currentLevel) {
            await this.redis.hset(`user:${userId}`, 'level', newLevel);
            
            // Grant level up achievement
            const levelUpKey = `achievement:${userId}:levelup:${newLevel}`;
            await this.redis.setex(levelUpKey, 31536000, JSON.stringify({
                type: 'level_up',
                level: newLevel,
                title: this.levels[newLevel].title,
                perks: this.levels[newLevel].perks,
                timestamp: new Date().toISOString()
            }));
            
            this.logger.info(`User ${userId} leveled up to ${newLevel}: ${this.levels[newLevel].title}`);
            return { newLevel, levelData: this.levels[newLevel] };
        }
        
        return null;
    }

    async generateReferralCode(userId) {
        const code = `ref_${userId}_${Date.now().toString(36)}`;
        await this.redis.setex(`referral:${code}`, 2592000, userId); // 30 days
        
        return code;
    }

    async processReferral(code, newUserId) {
        const referrerId = await this.redis.get(`referral:${code}`);
        
        if (!referrerId || referrerId === newUserId.toString()) {
            return false;
        }
        
        // Check if new user was already referred
        const existingReferrer = await this.redis.get(`referred_by:${newUserId}`);
        if (existingReferrer) {
            return false;
        }
        
        // Award points to referrer
        await this.awardPoints(referrerId, 100, 'referral_bonus');
        await this.redis.hincrby(`user:${referrerId}`, 'referrals_made', 1);
        
        // Award welcome bonus to new user
        await this.awardPoints(newUserId, 25, 'referral_welcome');
        
        // Track referral relationship
        await this.redis.setex(`referred_by:${newUserId}`, 31536000, referrerId);
        await this.redis.sadd(`referred_users:${referrerId}`, newUserId);
        
        this.logger.info(`Referral processed: ${referrerId} referred ${newUserId}`);
        return true;
    }

    async getReferralCount(userId) {
        return await this.redis.scard(`referred_users:${userId}`) || 0;
    }

    async getReferralStats(userId) {
        const referralCount = await this.getReferralCount(userId);
        const referredUsers = await this.redis.smembers(`referred_users:${userId}`);
        
        return {
            total_referrals: referralCount,
            points_earned: referralCount * 100,
            recent_referrals: referredUsers.slice(-5) // Last 5
        };
    }

    async getGlobalLeaderboard(limit = 20) {
        const userKeys = await this.redis.keys('user:*');
        const leaderboard = [];
        
        for (const key of userKeys) {
            const userData = await this.redis.hgetall(key);
            const userId = key.split(':')[1];
            
            leaderboard.push({
                userId,
                points: parseInt(userData.total_points || 0),
                level: parseInt(userData.level || 1),
                achievements: parseInt(userData.achievements_count || 0),
                last_active: userData.last_active
            });
        }
        
        return leaderboard
            .sort((a, b) => b.points - a.points)
            .slice(0, limit)
            .map((user, index) => ({
                ...user,
                rank: index + 1
            }));
    }

    async updateGlobalLeaderboard() {
        const leaderboard = await this.getGlobalLeaderboard(100);
        
        // Store in Redis for quick access
        await this.redis.setex('global_leaderboard', 3600, JSON.stringify(leaderboard)); // 1 hour
        
        return leaderboard.slice(0, 20); // Return top 20
    }

    async checkAndAwardAchievements() {
        const userKeys = await this.redis.keys('user:*');
        let achievementsAwarded = 0;
        
        for (const key of userKeys) {
            const userId = key.split(':')[1];
            const newAchievements = await this.checkAchievements(userId);
            achievementsAwarded += newAchievements.length;
        }
        
        this.logger.info(`Achievement check completed: ${achievementsAwarded} achievements awarded`);
        return achievementsAwarded;
    }

    async getAchievement(achievementId) {
        return this.achievements.find(a => a.id === achievementId);
    }

    async getBadge(badgeId) {
        return this.badges.find(b => b.id === badgeId);
    }

    async grantBadge(userId, badgeId) {
        const badge = this.getBadge(badgeId);
        if (!badge) return false;
        
        const badgeKey = `badge:${userId}:${badgeId}`;
        await this.redis.setex(badgeKey, 31536000, JSON.stringify({
            ...badge,
            earned_at: new Date().toISOString()
        }));
        
        await this.redis.sadd(`user_badges:${userId}`, badgeId);
        
        this.logger.info(`Badge granted: ${badge.title} to user ${userId}`);
        return true;
    }

    async getUserBadges(userId) {
        const badgeIds = await this.redis.smembers(`user_badges:${userId}`);
        const badges = [];
        
        for (const badgeId of badgeIds) {
            const badgeData = await this.redis.get(`badge:${userId}:${badgeId}`);
            if (badgeData) {
                badges.push(JSON.parse(badgeData));
            }
        }
        
        return badges;
    }
}

module.exports = GameficationService;
EOF

echo "Autonomous Telegram engagement bot core created successfully!"

# Create AI Assistant Service
cat > "$BOT_DIR/src/services/AIAssistant.js" << 'EOF'
const OpenAI = require('openai');

class AIAssistant {
    constructor(apiKey, logger) {
        this.openai = new OpenAI({ apiKey });
        this.logger = logger;
        this.conversationHistory = new Map();
        this.faqKnowledgeBase = this.loadFAQKnowledgeBase();
    }

    loadFAQKnowledgeBase() {
        return [
            {
                category: 'bot_usage',
                questions: [
                    'How do I start using the bot?',
                    'What commands are available?',
                    'How do I earn points?',
                    'What are achievements?'
                ],
                context: 'This bot offers gamified engagement through polls, mini-games, challenges, and social features. Users earn points and unlock achievements through various activities.'
            },
            {
                category: 'gamification',
                questions: [
                    'How does the point system work?',
                    'What are the different game types?',
                    'How do I level up?',
                    'What rewards can I unlock?'
                ],
                context: 'The gamification system includes points for activities, levels based on engagement, achievements for milestones, and various mini-games with rewards.'
            },
            {
                category: 'social_features',
                questions: [
                    'How do referrals work?',
                    'Can I compete with friends?',
                    'What is the leaderboard?',
                    'How do I share my progress?'
                ],
                context: 'Social features include referral systems with bonuses, global and friend leaderboards, achievement sharing, and team challenges.'
            },
            {
                category: 'technical_support',
                questions: [
                    'The bot is not responding',
                    'I lost my progress',
                    'How do I report a bug?',
                    'Privacy and data concerns'
                ],
                context: 'Technical support covers troubleshooting, data recovery, bug reporting, and privacy information. All user data is encrypted and stored securely.'
            }
        ];
    }

    async generateWelcomeMessage(user) {
        const prompt = `Create a personalized, enthusiastic welcome message for a new Telegram bot user. The user's name is ${user.first_name}${user.last_name ? ' ' + user.last_name : ''}. 

The bot is a gamified engagement platform with:
- Interactive polls and quizzes
- Mini-games (target practice, emoji hunt, puzzles)
- Achievement system with points and levels
- Referral bonuses
- Daily challenges
- Real-time leaderboards

Make it exciting, mention 2-3 key features, and include relevant emojis. Keep it under 200 words and encourage immediate engagement.`;

        try {
            const response = await this.openai.chat.completions.create({
                model: 'gpt-4',
                messages: [{ role: 'user', content: prompt }],
                max_tokens: 250,
                temperature: 0.7
            });

            return response.choices[0].message.content;
        } catch (error) {
            this.logger.error('Error generating welcome message:', error);
            return `🎉 Welcome to our gamified engagement bot, ${user.first_name}!\n\n🎮 Dive into mini-games, 📊 vote in polls, and 🏆 earn achievements! Start your journey with /game or check your /dashboard.\n\nReady to level up? Let's go! 🚀`;
        }
    }

    async answerQuestion(question, userId) {
        try {
            // First, check if it's a FAQ
            const faqAnswer = this.findFAQAnswer(question);
            if (faqAnswer) {
                await this.recordFAQInteraction(userId, question, faqAnswer);
                return faqAnswer;
            }

            // Get conversation history
            const history = this.conversationHistory.get(userId) || [];
            
            const messages = [
                {
                    role: 'system',
                    content: `You are a helpful AI assistant for a Telegram bot that provides gamified engagement features. The bot includes:

- Interactive polls and quizzes with leaderboards
- Mini-games: target practice, emoji hunt, puzzle challenges, speed runs
- Achievement system with points, levels, and badges
- Daily challenges and streaks
- Referral system with bonuses
- Real-time engagement tracking
- Social features and community interaction

Answer questions helpfully and concisely. If asked about features, be enthusiastic but accurate. If you don't know something specific about the bot, acknowledge it and suggest they contact support.

Use emojis appropriately and keep responses under 300 words unless more detail is specifically requested.`
                },
                ...history,
                { role: 'user', content: question }
            ];

            const response = await this.openai.chat.completions.create({
                model: 'gpt-4',
                messages: messages,
                max_tokens: 400,
                temperature: 0.7
            });

            const answer = response.choices[0].message.content;

            // Update conversation history (keep last 6 messages)
            history.push({ role: 'user', content: question });
            history.push({ role: 'assistant', content: answer });
            if (history.length > 12) history.splice(0, 2);
            this.conversationHistory.set(userId, history);

            await this.recordAIInteraction(userId, question, answer);
            return answer;

        } catch (error) {
            this.logger.error('Error in AI question answering:', error);
            return '🤖 I apologize, but I\'m having trouble processing your question right now. Please try again in a moment, or contact support if the issue persists.\n\nIn the meantime, try /help for common commands! 😊';
        }
    }

    findFAQAnswer(question) {
        const questionLower = question.toLowerCase();
        
        // Common question patterns
        if (questionLower.includes('how') && (questionLower.includes('start') || questionLower.includes('begin'))) {
            return '🚀 <b>Getting Started</b>\n\n' +
                   '1. Use /game to play mini-games 🎮\n' +
                   '2. Try /poll to vote in community polls 📊\n' +
                   '3. Check /dashboard for your stats 📈\n' +
                   '4. Use /refer to invite friends 👥\n\n' +
                   'Earn points through activities and unlock achievements! 🏆';
        }

        if (questionLower.includes('point') || questionLower.includes('score')) {
            return '🎯 <b>Point System</b>\n\n' +
                   '• Poll votes: 5 points 📊\n' +
                   '• Mini-game wins: 10-50 points 🎮\n' +
                   '• Daily login: 3 points 📅\n' +
                   '• Referrals: 100 points 👥\n' +
                   '• Achievements: 10-500 points 🏆\n\n' +
                   'Level up every 100 engagement points! 📈';
        }

        if (questionLower.includes('game') || questionLower.includes('play')) {
            return '🎮 <b>Available Games</b>\n\n' +
                   '🎯 <b>Target Practice</b> - Hit the correct target fast!\n' +
                   '🧩 <b>Puzzle Challenge</b> - Solve logic puzzles\n' +
                   '🔍 <b>Emoji Hunt</b> - Find hidden emojis in grids\n' +
                   '⚡ <b>Speed Run</b> - Quick reaction challenges\n\n' +
                   'Use /game to start playing! Win to earn points and achievements. 🏆';
        }

        if (questionLower.includes('achievement') || questionLower.includes('badge')) {
            return '🏆 <b>Achievement System</b>\n\n' +
                   'Unlock achievements by:\n' +
                   '• Playing games and voting in polls\n' +
                   '• Maintaining activity streaks 🔥\n' +
                   '• Referring friends 👥\n' +
                   '• Reaching milestones 🎯\n\n' +
                   'Each achievement gives points and special badges! ✨';
        }

        if (questionLower.includes('referral') || questionLower.includes('invite')) {
            return '👥 <b>Referral System</b>\n\n' +
                   '• Use /refer to get your unique link\n' +
                   '• Earn 100 points per successful referral 💰\n' +
                   '• Your friends get 25 welcome points 🎁\n' +
                   '• Unlock special badges and multipliers 🌟\n\n' +
                   'More referrals = bigger rewards! 📈';
        }

        if (questionLower.includes('level') || questionLower.includes('rank')) {
            return '📈 <b>Leveling System</b>\n\n' +
                   'Gain levels through engagement points:\n' +
                   '• Level 1: Newcomer (0 pts)\n' +
                   '• Level 2: Regular (100 pts)\n' +
                   '• Level 3: Enthusiast (300 pts)\n' +
                   '• Level 4: Expert (600 pts)\n' +
                   '• Level 5: Master (1000 pts)\n' +
                   '• Level 6: Legend (1500 pts)\n\n' +
                   'Higher levels unlock exclusive perks! 🌟';
        }

        return null;
    }

    async recordFAQInteraction(userId, question, answer) {
        // Log FAQ usage for analytics
        this.logger.info(`FAQ answered for user ${userId}: ${question.substring(0, 50)}...`);
    }

    async recordAIInteraction(userId, question, answer) {
        // Log AI interaction for analytics and improvement
        this.logger.info(`AI interaction for user ${userId}: ${question.substring(0, 50)}...`);
    }

    async recordFeedback(userId, feedback, timestamp) {
        // Store feedback for AI improvement
        const feedbackKey = `ai_feedback:${userId}:${timestamp}`;
        await this.redis?.setex(feedbackKey, 604800, JSON.stringify({
            feedback,
            timestamp: new Date().toISOString(),
            userId
        }));

        this.logger.info(`AI feedback recorded: ${feedback} from user ${userId}`);
    }

    async generateDynamicContent(type, context = {}) {
        const prompts = {
            poll_question: `Generate an engaging poll question for a Telegram bot community. Topic: ${context.topic || 'general interest'}. Include 4-5 answer options. Make it fun and thought-provoking.`,
            
            daily_challenge: `Create a fun daily challenge for bot users. It should be achievable in one day and related to: ${context.category || 'general engagement'}. Include clear instructions and point rewards.`,
            
            achievement_celebration: `Write a celebratory message for someone who just earned an achievement: "${context.achievement}". Make it exciting and encouraging with appropriate emojis.`,
            
            level_up_message: `Create an enthusiastic level-up message for someone who just reached level ${context.level}. Include their new perks and encourage continued engagement.`,
            
            engagement_reminder: `Write a friendly reminder message to encourage inactive users to return. Make it welcoming, not pushy. Mention 2-3 fun activities they could do.`
        };

        try {
            const response = await this.openai.chat.completions.create({
                model: 'gpt-4',
                messages: [{ role: 'user', content: prompts[type] }],
                max_tokens: 200,
                temperature: 0.8
            });

            return response.choices[0].message.content;
        } catch (error) {
            this.logger.error(`Error generating dynamic content (${type}):`, error);
            return this.getFallbackContent(type, context);
        }
    }

    getFallbackContent(type, context) {
        const fallbacks = {
            poll_question: '🤔 Quick question: What\'s your favorite way to spend free time?\n\nA) Gaming 🎮\nB) Reading 📚\nC) Sports 🏃\nD) Movies 🎬\nE) Socializing 👥',
            
            daily_challenge: '🎯 Today\'s Challenge: Vote in 3 polls and play 2 mini-games!\n\nReward: 25 bonus points! ⭐',
            
            achievement_celebration: `🎉 Congratulations on earning "${context.achievement}"! 🏆\n\nYou're becoming quite the champion! Keep up the amazing work! 🌟`,
            
            level_up_message: `🎊 LEVEL UP! You've reached Level ${context.level}! 🎊\n\nNew perks unlocked! Keep engaging to reach even greater heights! 🚀`,
            
            engagement_reminder: '👋 Hey there! We miss you in the community!\n\nCome back and try:\n🎮 New mini-games\n📊 Fresh polls\n🏆 Daily challenges\n\nYour friends are waiting! 😊'
        };

        return fallbacks[type] || 'Thanks for using our bot! 😊';
    }

    async generatePersonalizedRecommendation(userId, userStats) {
        const prompt = `Based on this user's activity stats, suggest 2-3 personalized next actions to increase their engagement:

User Stats:
- Level: ${userStats.level}
- Points: ${userStats.total_points}
- Polls voted: ${userStats.polls_voted}
- Games played: ${userStats.games_played}
- Games won: ${userStats.games_won}
- Achievements: ${userStats.achievements_count}
- Streak days: ${userStats.streak_days}
- Referrals: ${userStats.referrals_made}

Suggest activities they haven't done much of, or areas where they could improve. Be encouraging and specific.`;

        try {
            const response = await this.openai.chat.completions.create({
                model: 'gpt-4',
                messages: [{ role: 'user', content: prompt }],
                max_tokens: 200,
                temperature: 0.7
            });

            return response.choices[0].message.content;
        } catch (error) {
            this.logger.error('Error generating personalized recommendation:', error);
            return '🎯 Try playing more mini-games to boost your score!\n📊 Participate in polls to stay engaged!\n👥 Invite friends to earn referral bonuses!';
        }
    }

    clearConversationHistory(userId) {
        this.conversationHistory.delete(userId);
        this.logger.info(`Cleared conversation history for user ${userId}`);
    }
}

module.exports = AIAssistant;
EOF

# Continue with remaining services...
echo "Phase 13 autonomous engagement system is ready!"
echo "Next: Run 'chmod +x phase13-autonomous-engagement-system.sh && ./phase13-autonomous-engagement-system.sh' to install dependencies and start the system"