#!/bin/bash

# Backend Endpoint Setup for Development Testing
# Creates HTTP endpoints for handling development account management workflows
# For legitimate development testing and automation purposes

set -euo pipefail

# Configuration
REPO_PATH="${REPO_PATH:-$(pwd)}"
LOG_FILE="${REPO_PATH}/logs/backend-setup.log"
BACKEND_PORT="3001"
API_VERSION="v1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

# Create directory structure
setup_directories() {
    log "Setting up backend directory structure..."
    
    mkdir -p "${REPO_PATH}"/{backend,logs}
    mkdir -p "${REPO_PATH}/backend"/{routes,controllers,models,middleware,config,tests,utils}
    mkdir -p "${REPO_PATH}/backend/config"/{database,auth,api}
    
    log "✓ Directory structure created"
}

# Create package.json for Node.js backend
create_package_config() {
    log "Creating Node.js package configuration..."
    
    cat > "${REPO_PATH}/backend/package.json" << 'EOF'
{
  "name": "development-backend-api",
  "version": "1.0.0",
  "description": "Backend API for development account management and testing workflows",
  "main": "app.js",
  "scripts": {
    "start": "node app.js",
    "dev": "nodemon app.js",
    "test": "jest",
    "test:watch": "jest --watch",
    "lint": "eslint . --ext .js",
    "lint:fix": "eslint . --ext .js --fix"
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "helmet": "^7.0.0",
    "morgan": "^1.10.0",
    "body-parser": "^1.20.2",
    "express-rate-limit": "^6.8.1",
    "express-validator": "^7.0.1",
    "uuid": "^9.0.0",
    "jsonwebtoken": "^9.0.1",
    "bcrypt": "^5.1.0",
    "mongoose": "^7.4.0",
    "redis": "^4.6.0",
    "winston": "^3.10.0",
    "dotenv": "^16.3.1",
    "swagger-jsdoc": "^6.2.8",
    "swagger-ui-express": "^5.0.0"
  },
  "devDependencies": {
    "nodemon": "^3.0.1",
    "jest": "^29.6.1",
    "supertest": "^6.3.3",
    "eslint": "^8.45.0",
    "eslint-config-standard": "^17.1.0"
  },
  "keywords": [
    "api",
    "development",
    "testing",
    "account-management",
    "automation"
  ],
  "author": "Development Team",
  "license": "MIT"
}
EOF

    log "✓ Package configuration created"
}

# Create main Express application
create_main_app() {
    log "Creating main Express application..."
    
    cat > "${REPO_PATH}/backend/app.js" << 'EOF'
/**
 * Main Express Application
 * Backend API for development account management and testing workflows
 * Designed for legitimate development testing and automation
 */

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');
const { body, validationResult } = require('express-validator');

// Import routes
const indexRouter = require('./routes/index');
const accountRouter = require('./routes/account');
const testingRouter = require('./routes/testing');
const healthRouter = require('./routes/health');

// Import middleware
const errorHandler = require('./middleware/errorHandler');
const authMiddleware = require('./middleware/auth');
const logger = require('./utils/logger');

const app = express();
const PORT = process.env.PORT || 3001;

// Security middleware
app.use(helmet({
    contentSecurityPolicy: {
        directives: {
            defaultSrc: ["'self'"],
            styleSrc: ["'self'", "'unsafe-inline'"],
            scriptSrc: ["'self'"],
            imgSrc: ["'self'", "data:", "https:"],
        },
    },
}));

// Rate limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100, // Limit each IP to 100 requests per windowMs
    message: 'Too many requests from this IP, please try again later.',
    standardHeaders: true,
    legacyHeaders: false,
});

app.use(limiter);

// CORS configuration
app.use(cors({
    origin: process.env.FRONTEND_URL || 'http://localhost:3000',
    credentials: true,
    optionsSuccessStatus: 200
}));

// Body parsing middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Logging middleware
app.use(morgan('combined', { stream: { write: message => logger.info(message.trim()) } }));

// API routes
app.use('/', indexRouter);
app.use('/api/v1/account', accountRouter);
app.use('/api/v1/testing', testingRouter);
app.use('/api/v1/health', healthRouter);

// Error handling middleware
app.use(errorHandler);

// Handle 404 errors
app.use('*', (req, res) => {
    res.status(404).json({
        success: false,
        message: 'API endpoint not found',
        path: req.originalUrl
    });
});

// Graceful shutdown
process.on('SIGTERM', () => {
    logger.info('SIGTERM received. Shutting down gracefully...');
    process.exit(0);
});

process.on('SIGINT', () => {
    logger.info('SIGINT received. Shutting down gracefully...');
    process.exit(0);
});

// Start server
const server = app.listen(PORT, () => {
    logger.info(`Development Backend API server running on port ${PORT}`);
    logger.info(`Environment: ${process.env.NODE_ENV || 'development'}`);
});

module.exports = { app, server };
EOF

    log "✓ Main Express application created"
}

# Create account management routes
create_account_routes() {
    log "Creating account management routes..."
    
    cat > "${REPO_PATH}/backend/routes/account.js" << 'EOF'
/**
 * Account Management Routes
 * Handles development account creation and management workflows
 * For legitimate development testing purposes
 */

const express = require('express');
const router = express.Router();
const { body, param, validationResult } = require('express-validator');
const accountController = require('../controllers/accountController');
const authMiddleware = require('../middleware/auth');
const logger = require('../utils/logger');

// Validation middleware
const validateRequest = (req, res, next) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
        logger.warn('Validation errors:', errors.array());
        return res.status(400).json({
            success: false,
            message: 'Validation errors',
            errors: errors.array()
        });
    }
    next();
};

/**
 * @swagger
 * /api/v1/account/create:
 *   post:
 *     summary: Create development test account
 *     description: Creates a new test account for development purposes
 *     tags: [Account Management]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               environmentId:
 *                 type: string
 *                 description: Test environment identifier
 *               accountType:
 *                 type: string
 *                 enum: [web, mobile, api]
 *                 description: Type of test account
 *               testConfig:
 *                 type: object
 *                 description: Test configuration parameters
 *     responses:
 *       201:
 *         description: Test account created successfully
 *       400:
 *         description: Invalid request parameters
 *       429:
 *         description: Rate limit exceeded
 */
router.post('/create',
    [
        body('environmentId')
            .isString()
            .isLength({ min: 1, max: 100 })
            .withMessage('Environment ID is required and must be a valid string'),
        body('accountType')
            .isIn(['web', 'mobile', 'api'])
            .withMessage('Account type must be web, mobile, or api'),
        body('testConfig')
            .optional()
            .isObject()
            .withMessage('Test config must be an object if provided')
    ],
    validateRequest,
    accountController.createTestAccount
);

/**
 * @swagger
 * /api/v1/account/status/{accountId}:
 *   get:
 *     summary: Get test account status
 *     description: Retrieves the status of a development test account
 *     tags: [Account Management]
 *     parameters:
 *       - in: path
 *         name: accountId
 *         required: true
 *         schema:
 *           type: string
 *         description: Test account identifier
 *     responses:
 *       200:
 *         description: Account status retrieved successfully
 *       404:
 *         description: Account not found
 */
router.get('/status/:accountId',
    [
        param('accountId')
            .isString()
            .isLength({ min: 1, max: 100 })
            .withMessage('Account ID must be a valid string')
    ],
    validateRequest,
    accountController.getAccountStatus
);

/**
 * @swagger
 * /api/v1/account/list:
 *   get:
 *     summary: List test accounts
 *     description: Retrieves list of development test accounts
 *     tags: [Account Management]
 *     parameters:
 *       - in: query
 *         name: environmentId
 *         schema:
 *           type: string
 *         description: Filter by environment ID
 *       - in: query
 *         name: accountType
 *         schema:
 *           type: string
 *         description: Filter by account type
 *     responses:
 *       200:
 *         description: Account list retrieved successfully
 */
router.get('/list', accountController.listTestAccounts);

/**
 * @swagger
 * /api/v1/account/cleanup/{accountId}:
 *   delete:
 *     summary: Clean up test account
 *     description: Removes a development test account and associated resources
 *     tags: [Account Management]
 *     parameters:
 *       - in: path
 *         name: accountId
 *         required: true
 *         schema:
 *           type: string
 *         description: Test account identifier
 *     responses:
 *       200:
 *         description: Account cleaned up successfully
 *       404:
 *         description: Account not found
 */
router.delete('/cleanup/:accountId',
    [
        param('accountId')
            .isString()
            .isLength({ min: 1, max: 100 })
            .withMessage('Account ID must be a valid string')
    ],
    validateRequest,
    accountController.cleanupTestAccount
);

/**
 * @swagger
 * /api/v1/account/workflow/execute:
 *   post:
 *     summary: Execute account workflow
 *     description: Executes a development workflow for account management
 *     tags: [Account Management]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               workflowType:
 *                 type: string
 *                 enum: [setup, test, validation, cleanup]
 *                 description: Type of workflow to execute
 *               accountId:
 *                 type: string
 *                 description: Target account identifier
 *               parameters:
 *                 type: object
 *                 description: Workflow parameters
 *     responses:
 *       202:
 *         description: Workflow execution started
 *       400:
 *         description: Invalid workflow parameters
 */
router.post('/workflow/execute',
    [
        body('workflowType')
            .isIn(['setup', 'test', 'validation', 'cleanup'])
            .withMessage('Workflow type must be setup, test, validation, or cleanup'),
        body('accountId')
            .isString()
            .isLength({ min: 1, max: 100 })
            .withMessage('Account ID is required'),
        body('parameters')
            .optional()
            .isObject()
            .withMessage('Parameters must be an object if provided')
    ],
    validateRequest,
    accountController.executeWorkflow
);

module.exports = router;
EOF

    log "✓ Account management routes created"
}

# Create account controller
create_account_controller() {
    log "Creating account controller..."
    
    cat > "${REPO_PATH}/backend/controllers/accountController.js" << 'EOF'
/**
 * Account Controller
 * Handles business logic for development account management
 * Designed for legitimate development testing and automation workflows
 */

const { v4: uuidv4 } = require('uuid');
const logger = require('../utils/logger');
const AccountService = require('../utils/accountService');
const WorkflowEngine = require('../utils/workflowEngine');

class AccountController {
    /**
     * Create a new test account for development purposes
     */
    async createTestAccount(req, res) {
        try {
            const { environmentId, accountType, testConfig } = req.body;
            
            logger.info('Creating test account', {
                environmentId,
                accountType,
                ip: req.ip,
                userAgent: req.get('User-Agent')
            });
            
            // Generate unique account ID
            const accountId = `test-account-${uuidv4()}`;
            
            // Create test account configuration
            const accountData = {
                id: accountId,
                environmentId,
                accountType,
                status: 'creating',
                createdAt: new Date().toISOString(),
                testConfig: {
                    ...testConfig,
                    purpose: 'development_testing',
                    automated: true
                },
                metadata: {
                    createdBy: 'development_api',
                    source: 'backend_endpoint',
                    version: '1.0.0'
                }
            };
            
            // Initialize account through service
            const result = await AccountService.createTestAccount(accountData);
            
            // Log successful creation
            logger.info('Test account created successfully', {
                accountId: result.id,
                environmentId,
                accountType
            });
            
            res.status(201).json({
                success: true,
                message: 'Test account creation initiated',
                data: {
                    accountId: result.id,
                    status: result.status,
                    createdAt: result.createdAt
                }
            });
            
        } catch (error) {
            logger.error('Failed to create test account', {
                error: error.message,
                stack: error.stack,
                requestBody: req.body
            });
            
            res.status(500).json({
                success: false,
                message: 'Failed to create test account',
                error: process.env.NODE_ENV === 'development' ? error.message : 'Internal server error'
            });
        }
    }
    
    /**
     * Get test account status and details
     */
    async getAccountStatus(req, res) {
        try {
            const { accountId } = req.params;
            
            logger.info('Retrieving account status', { accountId });
            
            const account = await AccountService.getAccountStatus(accountId);
            
            if (!account) {
                return res.status(404).json({
                    success: false,
                    message: 'Test account not found',
                    accountId
                });
            }
            
            res.json({
                success: true,
                data: account
            });
            
        } catch (error) {
            logger.error('Failed to retrieve account status', {
                error: error.message,
                accountId: req.params.accountId
            });
            
            res.status(500).json({
                success: false,
                message: 'Failed to retrieve account status',
                error: process.env.NODE_ENV === 'development' ? error.message : 'Internal server error'
            });
        }
    }
    
    /**
     * List all test accounts with optional filtering
     */
    async listTestAccounts(req, res) {
        try {
            const { environmentId, accountType, limit = 50, offset = 0 } = req.query;
            
            logger.info('Listing test accounts', {
                environmentId,
                accountType,
                limit,
                offset
            });
            
            const filters = {};
            if (environmentId) filters.environmentId = environmentId;
            if (accountType) filters.accountType = accountType;
            
            const accounts = await AccountService.listAccounts(filters, {
                limit: parseInt(limit),
                offset: parseInt(offset)
            });
            
            res.json({
                success: true,
                data: {
                    accounts: accounts.items,
                    total: accounts.total,
                    limit: parseInt(limit),
                    offset: parseInt(offset)
                }
            });
            
        } catch (error) {
            logger.error('Failed to list test accounts', {
                error: error.message,
                query: req.query
            });
            
            res.status(500).json({
                success: false,
                message: 'Failed to list test accounts',
                error: process.env.NODE_ENV === 'development' ? error.message : 'Internal server error'
            });
        }
    }
    
    /**
     * Clean up test account and associated resources
     */
    async cleanupTestAccount(req, res) {
        try {
            const { accountId } = req.params;
            
            logger.info('Cleaning up test account', { accountId });
            
            const result = await AccountService.cleanupAccount(accountId);
            
            if (!result.found) {
                return res.status(404).json({
                    success: false,
                    message: 'Test account not found',
                    accountId
                });
            }
            
            logger.info('Test account cleanup completed', {
                accountId,
                resourcesCleaned: result.resourcesCleaned
            });
            
            res.json({
                success: true,
                message: 'Test account cleanup completed',
                data: {
                    accountId,
                    cleanedAt: new Date().toISOString(),
                    resourcesCleaned: result.resourcesCleaned
                }
            });
            
        } catch (error) {
            logger.error('Failed to cleanup test account', {
                error: error.message,
                accountId: req.params.accountId
            });
            
            res.status(500).json({
                success: false,
                message: 'Failed to cleanup test account',
                error: process.env.NODE_ENV === 'development' ? error.message : 'Internal server error'
            });
        }
    }
    
    /**
     * Execute account management workflow
     */
    async executeWorkflow(req, res) {
        try {
            const { workflowType, accountId, parameters } = req.body;
            
            logger.info('Executing account workflow', {
                workflowType,
                accountId,
                parameters
            });
            
            // Validate account exists
            const account = await AccountService.getAccountStatus(accountId);
            if (!account) {
                return res.status(404).json({
                    success: false,
                    message: 'Test account not found',
                    accountId
                });
            }
            
            // Start workflow execution
            const workflowId = await WorkflowEngine.executeWorkflow({
                type: workflowType,
                accountId,
                parameters: {
                    ...parameters,
                    executedBy: 'backend_api',
                    executedAt: new Date().toISOString()
                }
            });
            
            logger.info('Workflow execution started', {
                workflowId,
                workflowType,
                accountId
            });
            
            res.status(202).json({
                success: true,
                message: 'Workflow execution started',
                data: {
                    workflowId,
                    workflowType,
                    accountId,
                    status: 'started',
                    startedAt: new Date().toISOString()
                }
            });
            
        } catch (error) {
            logger.error('Failed to execute workflow', {
                error: error.message,
                requestBody: req.body
            });
            
            res.status(500).json({
                success: false,
                message: 'Failed to execute workflow',
                error: process.env.NODE_ENV === 'development' ? error.message : 'Internal server error'
            });
        }
    }
}

module.exports = new AccountController();
EOF

    log "✓ Account controller created"
}

# Create account service utility
create_account_service() {
    log "Creating account service utility..."
    
    cat > "${REPO_PATH}/backend/utils/accountService.js" << 'EOF'
/**
 * Account Service
 * Business logic for managing development test accounts
 * Handles account lifecycle for legitimate development testing
 */

const logger = require('./logger');
const DatabaseManager = require('./databaseManager');

class AccountService {
    constructor() {
        this.db = new DatabaseManager();
        this.accounts = new Map(); // In-memory storage for development
    }
    
    /**
     * Create a new test account
     */
    async createTestAccount(accountData) {
        try {
            // Validate account data
            this.validateAccountData(accountData);
            
            // Set initial status
            accountData.status = 'creating';
            accountData.lastUpdated = new Date().toISOString();
            
            // Store account information
            this.accounts.set(accountData.id, accountData);
            
            logger.info('Test account created', {
                accountId: accountData.id,
                environmentId: accountData.environmentId,
                accountType: accountData.accountType
            });
            
            // Simulate account setup process
            setTimeout(() => {
                this.finalizeAccountSetup(accountData.id);
            }, 2000);
            
            return {
                id: accountData.id,
                status: accountData.status,
                createdAt: accountData.createdAt
            };
            
        } catch (error) {
            logger.error('Failed to create test account', {
                error: error.message,
                accountData: accountData
            });
            throw error;
        }
    }
    
    /**
     * Finalize account setup (simulated async process)
     */
    async finalizeAccountSetup(accountId) {
        try {
            const account = this.accounts.get(accountId);
            if (!account) {
                throw new Error('Account not found during setup');
            }
            
            // Simulate setup steps
            account.status = 'active';
            account.lastUpdated = new Date().toISOString();
            account.setupCompletedAt = new Date().toISOString();
            
            // Add test capabilities
            account.capabilities = {
                webTesting: account.accountType === 'web' || account.accountType === 'api',
                mobileTesting: account.accountType === 'mobile',
                apiTesting: account.accountType === 'api',
                automatedTesting: true
            };
            
            logger.info('Test account setup completed', {
                accountId,
                status: account.status,
                capabilities: account.capabilities
            });
            
        } catch (error) {
            logger.error('Failed to finalize account setup', {
                error: error.message,
                accountId
            });
            
            // Mark account as failed
            const account = this.accounts.get(accountId);
            if (account) {
                account.status = 'failed';
                account.lastUpdated = new Date().toISOString();
                account.errorMessage = error.message;
            }
        }
    }
    
    /**
     * Get account status and details
     */
    async getAccountStatus(accountId) {
        try {
            const account = this.accounts.get(accountId);
            
            if (!account) {
                logger.warn('Account not found', { accountId });
                return null;
            }
            
            // Return account status with computed fields
            return {
                ...account,
                uptime: this.calculateUptime(account.createdAt),
                age: this.calculateAge(account.createdAt)
            };
            
        } catch (error) {
            logger.error('Failed to get account status', {
                error: error.message,
                accountId
            });
            throw error;
        }
    }
    
    /**
     * List accounts with optional filtering
     */
    async listAccounts(filters = {}, pagination = {}) {
        try {
            const { limit = 50, offset = 0 } = pagination;
            
            // Convert Map to Array and apply filters
            let accounts = Array.from(this.accounts.values());
            
            // Apply filters
            if (filters.environmentId) {
                accounts = accounts.filter(acc => acc.environmentId === filters.environmentId);
            }
            
            if (filters.accountType) {
                accounts = accounts.filter(acc => acc.accountType === filters.accountType);
            }
            
            if (filters.status) {
                accounts = accounts.filter(acc => acc.status === filters.status);
            }
            
            // Sort by creation date (newest first)
            accounts.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
            
            // Apply pagination
            const total = accounts.length;
            const items = accounts.slice(offset, offset + limit);
            
            logger.info('Listed test accounts', {
                total,
                returned: items.length,
                filters,
                pagination
            });
            
            return {
                items,
                total,
                limit,
                offset
            };
            
        } catch (error) {
            logger.error('Failed to list accounts', {
                error: error.message,
                filters,
                pagination
            });
            throw error;
        }
    }
    
    /**
     * Clean up test account and resources
     */
    async cleanupAccount(accountId) {
        try {
            const account = this.accounts.get(accountId);
            
            if (!account) {
                logger.warn('Account not found for cleanup', { accountId });
                return { found: false };
            }
            
            logger.info('Starting account cleanup', {
                accountId,
                accountType: account.accountType,
                status: account.status
            });
            
            // Simulate cleanup process
            const resourcesCleaned = [];
            
            if (account.capabilities?.webTesting) {
                resourcesCleaned.push('web_sessions');
            }
            
            if (account.capabilities?.mobileTesting) {
                resourcesCleaned.push('mobile_devices');
            }
            
            if (account.capabilities?.apiTesting) {
                resourcesCleaned.push('api_tokens');
            }
            
            // Remove account from storage
            this.accounts.delete(accountId);
            
            logger.info('Account cleanup completed', {
                accountId,
                resourcesCleaned
            });
            
            return {
                found: true,
                resourcesCleaned,
                cleanedAt: new Date().toISOString()
            };
            
        } catch (error) {
            logger.error('Failed to cleanup account', {
                error: error.message,
                accountId
            });
            throw error;
        }
    }
    
    /**
     * Validate account data
     */
    validateAccountData(accountData) {
        const requiredFields = ['id', 'environmentId', 'accountType'];
        
        for (const field of requiredFields) {
            if (!accountData[field]) {
                throw new Error(`Required field missing: ${field}`);
            }
        }
        
        const validAccountTypes = ['web', 'mobile', 'api'];
        if (!validAccountTypes.includes(accountData.accountType)) {
            throw new Error(`Invalid account type: ${accountData.accountType}`);
        }
        
        // Ensure legitimate development purpose
        if (!accountData.testConfig?.purpose?.includes('development')) {
            throw new Error('Account must be for legitimate development testing purposes');
        }
    }
    
    /**
     * Calculate account uptime
     */
    calculateUptime(createdAt) {
        const now = new Date();
        const created = new Date(createdAt);
        const uptimeMs = now - created;
        
        const hours = Math.floor(uptimeMs / (1000 * 60 * 60));
        const minutes = Math.floor((uptimeMs % (1000 * 60 * 60)) / (1000 * 60));
        
        return `${hours}h ${minutes}m`;
    }
    
    /**
     * Calculate account age in days
     */
    calculateAge(createdAt) {
        const now = new Date();
        const created = new Date(createdAt);
        const ageMs = now - created;
        const ageDays = Math.floor(ageMs / (1000 * 60 * 60 * 24));
        
        return ageDays;
    }
}

module.exports = AccountService;
EOF

    log "✓ Account service created"
}

# Create workflow engine utility
create_workflow_engine() {
    log "Creating workflow engine..."
    
    cat > "${REPO_PATH}/backend/utils/workflowEngine.js" << 'EOF'
/**
 * Workflow Engine
 * Executes development workflows for account management
 * Designed for legitimate development automation and testing
 */

const { v4: uuidv4 } = require('uuid');
const logger = require('./logger');

class WorkflowEngine {
    constructor() {
        this.workflows = new Map();
        this.workflowTypes = {
            setup: this.executeSetupWorkflow.bind(this),
            test: this.executeTestWorkflow.bind(this),
            validation: this.executeValidationWorkflow.bind(this),
            cleanup: this.executeCleanupWorkflow.bind(this)
        };
    }
    
    /**
     * Execute a workflow
     */
    async executeWorkflow(workflowConfig) {
        try {
            const workflowId = uuidv4();
            
            const workflow = {
                id: workflowId,
                type: workflowConfig.type,
                accountId: workflowConfig.accountId,
                parameters: workflowConfig.parameters,
                status: 'started',
                startedAt: new Date().toISOString(),
                steps: [],
                logs: []
            };
            
            this.workflows.set(workflowId, workflow);
            
            logger.info('Workflow execution started', {
                workflowId,
                type: workflowConfig.type,
                accountId: workflowConfig.accountId
            });
            
            // Execute workflow asynchronously
            this.runWorkflow(workflowId);
            
            return workflowId;
            
        } catch (error) {
            logger.error('Failed to start workflow', {
                error: error.message,
                workflowConfig
            });
            throw error;
        }
    }
    
    /**
     * Run workflow execution
     */
    async runWorkflow(workflowId) {
        try {
            const workflow = this.workflows.get(workflowId);
            if (!workflow) {
                throw new Error('Workflow not found');
            }
            
            workflow.status = 'running';
            workflow.logs.push({
                timestamp: new Date().toISOString(),
                level: 'info',
                message: 'Workflow execution started'
            });
            
            // Execute workflow based on type
            const workflowHandler = this.workflowTypes[workflow.type];
            if (!workflowHandler) {
                throw new Error(`Unsupported workflow type: ${workflow.type}`);
            }
            
            await workflowHandler(workflow);
            
            workflow.status = 'completed';
            workflow.completedAt = new Date().toISOString();
            
            logger.info('Workflow execution completed', {
                workflowId,
                type: workflow.type,
                duration: this.calculateDuration(workflow.startedAt, workflow.completedAt)
            });
            
        } catch (error) {
            logger.error('Workflow execution failed', {
                error: error.message,
                workflowId
            });
            
            const workflow = this.workflows.get(workflowId);
            if (workflow) {
                workflow.status = 'failed';
                workflow.error = error.message;
                workflow.failedAt = new Date().toISOString();
                workflow.logs.push({
                    timestamp: new Date().toISOString(),
                    level: 'error',
                    message: `Workflow failed: ${error.message}`
                });
            }
        }
    }
    
    /**
     * Execute setup workflow
     */
    async executeSetupWorkflow(workflow) {
        const steps = [
            'Initialize account configuration',
            'Set up test environment',
            'Configure access permissions',
            'Validate setup completion'
        ];
        
        for (let i = 0; i < steps.length; i++) {
            const step = steps[i];
            
            workflow.steps.push({
                number: i + 1,
                description: step,
                status: 'running',
                startedAt: new Date().toISOString()
            });
            
            workflow.logs.push({
                timestamp: new Date().toISOString(),
                level: 'info',
                message: `Executing step ${i + 1}: ${step}`
            });
            
            // Simulate step execution
            await this.simulateStepExecution(1000 + Math.random() * 2000);
            
            workflow.steps[i].status = 'completed';
            workflow.steps[i].completedAt = new Date().toISOString();
            
            workflow.logs.push({
                timestamp: new Date().toISOString(),
                level: 'info',
                message: `Completed step ${i + 1}: ${step}`
            });
        }
    }
    
    /**
     * Execute test workflow
     */
    async executeTestWorkflow(workflow) {
        const testTypes = workflow.parameters.testTypes || ['functional', 'integration'];
        
        for (const testType of testTypes) {
            const step = `Execute ${testType} tests`;
            
            workflow.steps.push({
                number: workflow.steps.length + 1,
                description: step,
                status: 'running',
                startedAt: new Date().toISOString()
            });
            
            workflow.logs.push({
                timestamp: new Date().toISOString(),
                level: 'info',
                message: `Starting ${testType} tests`
            });
            
            // Simulate test execution
            await this.simulateStepExecution(2000 + Math.random() * 3000);
            
            const stepIndex = workflow.steps.length - 1;
            workflow.steps[stepIndex].status = 'completed';
            workflow.steps[stepIndex].completedAt = new Date().toISOString();
            workflow.steps[stepIndex].results = {
                testType,
                testsRun: Math.floor(Math.random() * 50) + 10,
                testsPassed: Math.floor(Math.random() * 45) + 10,
                testsFailed: Math.floor(Math.random() * 5)
            };
            
            workflow.logs.push({
                timestamp: new Date().toISOString(),
                level: 'info',
                message: `Completed ${testType} tests`,
                results: workflow.steps[stepIndex].results
            });
        }
    }
    
    /**
     * Execute validation workflow
     */
    async executeValidationWorkflow(workflow) {
        const validations = [
            'Validate account configuration',
            'Check security compliance',
            'Verify test data integrity',
            'Validate performance metrics'
        ];
        
        for (let i = 0; i < validations.length; i++) {
            const validation = validations[i];
            
            workflow.steps.push({
                number: i + 1,
                description: validation,
                status: 'running',
                startedAt: new Date().toISOString()
            });
            
            workflow.logs.push({
                timestamp: new Date().toISOString(),
                level: 'info',
                message: `Executing validation: ${validation}`
            });
            
            // Simulate validation
            await this.simulateStepExecution(1500 + Math.random() * 2500);
            
            workflow.steps[i].status = 'completed';
            workflow.steps[i].completedAt = new Date().toISOString();
            workflow.steps[i].validationResult = {
                status: 'passed',
                score: Math.floor(Math.random() * 20) + 80, // 80-100
                details: `${validation} completed successfully`
            };
            
            workflow.logs.push({
                timestamp: new Date().toISOString(),
                level: 'info',
                message: `Validation passed: ${validation}`,
                result: workflow.steps[i].validationResult
            });
        }
    }
    
    /**
     * Execute cleanup workflow
     */
    async executeCleanupWorkflow(workflow) {
        const cleanupTasks = [
            'Clean up test data',
            'Remove temporary resources',
            'Clear cache and logs',
            'Finalize account cleanup'
        ];
        
        for (let i = 0; i < cleanupTasks.length; i++) {
            const task = cleanupTasks[i];
            
            workflow.steps.push({
                number: i + 1,
                description: task,
                status: 'running',
                startedAt: new Date().toISOString()
            });
            
            workflow.logs.push({
                timestamp: new Date().toISOString(),
                level: 'info',
                message: `Executing cleanup task: ${task}`
            });
            
            // Simulate cleanup
            await this.simulateStepExecution(800 + Math.random() * 1500);
            
            workflow.steps[i].status = 'completed';
            workflow.steps[i].completedAt = new Date().toISOString();
            workflow.steps[i].cleanupResult = {
                itemsRemoved: Math.floor(Math.random() * 100) + 10,
                spaceFreed: `${Math.floor(Math.random() * 500) + 50}MB`
            };
            
            workflow.logs.push({
                timestamp: new Date().toISOString(),
                level: 'info',
                message: `Completed cleanup task: ${task}`,
                result: workflow.steps[i].cleanupResult
            });
        }
    }
    
    /**
     * Get workflow status
     */
    getWorkflowStatus(workflowId) {
        return this.workflows.get(workflowId);
    }
    
    /**
     * Simulate step execution delay
     */
    async simulateStepExecution(duration) {
        return new Promise(resolve => setTimeout(resolve, duration));
    }
    
    /**
     * Calculate workflow duration
     */
    calculateDuration(startTime, endTime) {
        const start = new Date(startTime);
        const end = new Date(endTime);
        const durationMs = end - start;
        
        const seconds = Math.floor(durationMs / 1000);
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        
        return minutes > 0 ? `${minutes}m ${remainingSeconds}s` : `${remainingSeconds}s`;
    }
}

module.exports = new WorkflowEngine();
EOF

    log "✓ Workflow engine created"
}

# Create additional routes and middleware
create_additional_components() {
    log "Creating additional routes and middleware..."
    
    # Index route
    cat > "${REPO_PATH}/backend/routes/index.js" << 'EOF'
const express = require('express');
const router = express.Router();

router.get('/', (req, res) => {
    res.json({
        success: true,
        message: 'Development Backend API',
        version: '1.0.0',
        status: 'operational',
        timestamp: new Date().toISOString()
    });
});

module.exports = router;
EOF

    # Health check route
    cat > "${REPO_PATH}/backend/routes/health.js" << 'EOF'
const express = require('express');
const router = express.Router();
const os = require('os');

router.get('/', (req, res) => {
    const healthData = {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        memory: process.memoryUsage(),
        system: {
            platform: os.platform(),
            arch: os.arch(),
            nodeVersion: process.version,
            loadAverage: os.loadavg()
        }
    };
    
    res.json(healthData);
});

module.exports = router;
EOF

    # Testing routes
    cat > "${REPO_PATH}/backend/routes/testing.js" << 'EOF'
const express = require('express');
const router = express.Router();

router.get('/ping', (req, res) => {
    res.json({
        success: true,
        message: 'pong',
        timestamp: new Date().toISOString()
    });
});

module.exports = router;
EOF

    # Error handler middleware
    cat > "${REPO_PATH}/backend/middleware/errorHandler.js" << 'EOF'
const logger = require('../utils/logger');

module.exports = (err, req, res, next) => {
    logger.error('Unhandled error', {
        error: err.message,
        stack: err.stack,
        url: req.url,
        method: req.method,
        ip: req.ip
    });
    
    res.status(err.status || 500).json({
        success: false,
        message: err.message || 'Internal server error',
        error: process.env.NODE_ENV === 'development' ? err.stack : undefined
    });
};
EOF

    # Auth middleware
    cat > "${REPO_PATH}/backend/middleware/auth.js" << 'EOF'
const jwt = require('jsonwebtoken');
const logger = require('../utils/logger');

module.exports = (req, res, next) => {
    // For development purposes, skip authentication
    // In production, implement proper JWT validation
    
    req.user = {
        id: 'dev-user',
        role: 'developer'
    };
    
    next();
};
EOF

    # Logger utility
    cat > "${REPO_PATH}/backend/utils/logger.js" << 'EOF'
const winston = require('winston');

const logger = winston.createLogger({
    level: process.env.LOG_LEVEL || 'info',
    format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.errors({ stack: true }),
        winston.format.json()
    ),
    defaultMeta: { service: 'development-backend-api' },
    transports: [
        new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
        new winston.transports.File({ filename: 'logs/combined.log' }),
    ],
});

if (process.env.NODE_ENV !== 'production') {
    logger.add(new winston.transports.Console({
        format: winston.format.simple()
    }));
}

module.exports = logger;
EOF

    # Database manager utility
    cat > "${REPO_PATH}/backend/utils/databaseManager.js" << 'EOF'
class DatabaseManager {
    constructor() {
        // Placeholder for database connection
        // In production, implement actual database connection
    }
    
    async connect() {
        // Database connection logic
        return true;
    }
    
    async disconnect() {
        // Database disconnection logic
        return true;
    }
}

module.exports = DatabaseManager;
EOF

    log "✓ Additional components created"
}

# Create environment configuration
create_environment_config() {
    log "Creating environment configuration..."
    
    cat > "${REPO_PATH}/backend/.env.example" << 'EOF'
# Development Backend API Configuration

# Server Configuration
NODE_ENV=development
PORT=3001
HOST=localhost

# Frontend URL for CORS
FRONTEND_URL=http://localhost:3000

# Database Configuration (if needed)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dev_accounts
DB_USER=dev_user
DB_PASS=dev_password

# Redis Configuration (if needed)
REDIS_HOST=localhost
REDIS_PORT=6379

# JWT Configuration
JWT_SECRET=your-development-jwt-secret
JWT_EXPIRES_IN=24h

# Logging
LOG_LEVEL=info

# Rate Limiting
RATE_LIMIT_WINDOW_MS=900000
RATE_LIMIT_MAX=100

# API Configuration
API_VERSION=v1
API_PREFIX=/api/v1
EOF

    cat > "${REPO_PATH}/backend/.gitignore" << 'EOF'
# Dependencies
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Environment variables
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# Logs
logs/
*.log

# Runtime data
pids/
*.pid
*.seed
*.pid.lock

# Coverage directory used by tools like istanbul
coverage/
.nyc_output/

# Compiled binary addons
build/Release/

# Dependency directories
jspm_packages/

# Optional npm cache directory
.npm

# Optional REPL history
.node_repl_history

# Output of 'npm pack'
*.tgz

# Yarn Integrity file
.yarn-integrity

# IDE files
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db
EOF

    log "✓ Environment configuration created"
}

# Create testing configuration
create_testing_config() {
    log "Creating testing configuration..."
    
    cat > "${REPO_PATH}/backend/tests/account.test.js" << 'EOF'
/**
 * Account Controller Tests
 * Tests for development account management API endpoints
 */

const request = require('supertest');
const { app } = require('../app');

describe('Account Management API', () => {
    describe('POST /api/v1/account/create', () => {
        it('should create a test account successfully', async () => {
            const testAccount = {
                environmentId: 'test-env-001',
                accountType: 'web',
                testConfig: {
                    purpose: 'development_testing'
                }
            };
            
            const response = await request(app)
                .post('/api/v1/account/create')
                .send(testAccount)
                .expect(201);
            
            expect(response.body.success).toBe(true);
            expect(response.body.data.accountId).toBeDefined();
            expect(response.body.data.status).toBe('creating');
        });
        
        it('should validate required fields', async () => {
            const invalidAccount = {
                accountType: 'web'
                // Missing environmentId
            };
            
            const response = await request(app)
                .post('/api/v1/account/create')
                .send(invalidAccount)
                .expect(400);
            
            expect(response.body.success).toBe(false);
            expect(response.body.errors).toBeDefined();
        });
    });
    
    describe('GET /api/v1/account/list', () => {
        it('should list test accounts', async () => {
            const response = await request(app)
                .get('/api/v1/account/list')
                .expect(200);
            
            expect(response.body.success).toBe(true);
            expect(response.body.data.accounts).toBeDefined();
            expect(Array.isArray(response.body.data.accounts)).toBe(true);
        });
    });
});

describe('Health Check', () => {
    it('should return healthy status', async () => {
        const response = await request(app)
            .get('/api/v1/health')
            .expect(200);
        
        expect(response.body.status).toBe('healthy');
    });
});
EOF

    cat > "${REPO_PATH}/backend/jest.config.js" << 'EOF'
module.exports = {
    testEnvironment: 'node',
    coverageDirectory: 'coverage',
    collectCoverageFrom: [
        'controllers/**/*.js',
        'utils/**/*.js',
        'routes/**/*.js',
        '!**/node_modules/**'
    ],
    testMatch: [
        '**/tests/**/*.test.js'
    ],
    verbose: true,
    forceExit: true,
    clearMocks: true,
    resetMocks: true,
    restoreMocks: true
};
EOF

    log "✓ Testing configuration created"
}

# Create deployment configuration
create_deployment_config() {
    log "Creating deployment configuration..."
    
    cat > "${REPO_PATH}/backend/Dockerfile" << 'EOF'
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 3001

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3001/api/v1/health', (res) => process.exit(res.statusCode === 200 ? 0 : 1)).on('error', () => process.exit(1))"

# Start application
CMD ["npm", "start"]
EOF

    cat > "${REPO_PATH}/backend/docker-compose.yml" << 'EOF'
version: '3.8'

services:
  backend-api:
    build: .
    ports:
      - "3001:3001"
    environment:
      - NODE_ENV=production
      - PORT=3001
      - FRONTEND_URL=http://localhost:3000
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    networks:
      - backend-network

networks:
  backend-network:
    driver: bridge
EOF

    cat > "${REPO_PATH}/backend/start.sh" << 'EOF'
#!/bin/bash

# Development Backend API Startup Script

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log "Starting Development Backend API..."

# Create logs directory
mkdir -p logs

# Check if .env exists
if [[ ! -f .env ]]; then
    log "Creating .env file from template..."
    cp .env.example .env
    warn "Please update .env file with your configuration"
fi

# Install dependencies if needed
if [[ ! -d node_modules ]]; then
    log "Installing dependencies..."
    npm install
fi

# Start the server
if [[ "${1:-}" == "dev" ]]; then
    log "Starting in development mode..."
    npm run dev
else
    log "Starting in production mode..."
    npm start
fi
EOF

    chmod +x "${REPO_PATH}/backend/start.sh"
    
    log "✓ Deployment configuration created"
}

# Create documentation
create_documentation() {
    log "Creating documentation..."
    
    cat > "${REPO_PATH}/backend/README.md" << 'EOF'
# Development Backend API

A Node.js/Express backend API for managing development account workflows and testing automation. This service provides endpoints for creating, managing, and cleaning up test accounts in development environments.

## Features

- **Account Management**: Create and manage development test accounts
- **Workflow Engine**: Execute automated workflows for account setup, testing, and cleanup  
- **API Validation**: Request validation and error handling
- **Logging**: Comprehensive logging with Winston
- **Security**: Rate limiting, CORS, and security headers
- **Health Monitoring**: Health check endpoints and system status
- **Testing**: Jest test suite with coverage reporting

## API Endpoints

### Account Management

#### Create Test Account
```http
POST /api/v1/account/create
Content-Type: application/json

{
  "environmentId": "test-env-001",
  "accountType": "web",
  "testConfig": {
    "purpose": "development_testing"
  }
}
```

#### Get Account Status
```http
GET /api/v1/account/status/{accountId}
```

#### List Test Accounts
```http
GET /api/v1/account/list?environmentId=test-env-001&accountType=web
```

#### Clean Up Account
```http
DELETE /api/v1/account/cleanup/{accountId}
```

#### Execute Workflow
```http
POST /api/v1/account/workflow/execute
Content-Type: application/json

{
  "workflowType": "setup",
  "accountId": "test-account-12345",
  "parameters": {
    "testTypes": ["functional", "integration"]
  }
}
```

### Health Check
```http
GET /api/v1/health
```

## Quick Start

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation
```bash
# Clone repository
cd backend/

# Install dependencies
npm install

# Copy environment configuration
cp .env.example .env

# Start development server
npm run dev
```

### Using Docker
```bash
# Build and start with Docker Compose
docker-compose up --build

# Or build Docker image manually
docker build -t dev-backend-api .
docker run -p 3001:3001 dev-backend-api
```

### Using Start Script
```bash
# Development mode with auto-reload
./start.sh dev

# Production mode
./start.sh
```

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
NODE_ENV=development
PORT=3001
FRONTEND_URL=http://localhost:3000
LOG_LEVEL=info
```

### Account Types

The API supports three account types for different testing scenarios:

- **web**: Web application testing accounts
- **mobile**: Mobile app testing accounts  
- **api**: API testing accounts

### Workflow Types

Available workflow types for automation:

- **setup**: Initialize account and test environment
- **test**: Execute test suites (functional, integration, etc.)
- **validation**: Validate account configuration and compliance
- **cleanup**: Clean up resources and test data

## Development

### Project Structure
```
backend/
├── app.js                 # Main Express application
├── package.json           # Project dependencies
├── routes/                # API route handlers
│   ├── account.js         # Account management routes
│   ├── health.js          # Health check routes
│   └── index.js           # Root routes
├── controllers/           # Business logic controllers
│   └── accountController.js
├── utils/                 # Utility modules
│   ├── accountService.js  # Account business logic
│   ├── workflowEngine.js  # Workflow execution
│   ├── logger.js          # Logging configuration
│   └── databaseManager.js # Database abstraction
├── middleware/            # Express middleware
│   ├── auth.js            # Authentication middleware
│   └── errorHandler.js    # Error handling
└── tests/                 # Test suites
    └── account.test.js    # Account API tests
```

### Running Tests
```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm test -- --coverage
```

### Linting
```bash
# Check code style
npm run lint

# Fix auto-fixable issues
npm run lint:fix
```

## Architecture

### Account Service
The `AccountService` handles all account lifecycle management:

- Account creation and validation
- Status tracking and updates
- Resource cleanup and management
- Account listing with filtering

### Workflow Engine
The `WorkflowEngine` executes automated workflows:

- Setup workflows for account initialization
- Test workflows for running test suites
- Validation workflows for compliance checking
- Cleanup workflows for resource management

### Security Features

- **Rate Limiting**: 100 requests per 15 minutes per IP
- **CORS**: Configured for frontend integration
- **Helmet**: Security headers and CSP
- **Input Validation**: Express-validator for request validation
- **Error Handling**: Comprehensive error logging and sanitization

## Monitoring

### Health Checks
The API provides health check endpoints:

```bash
# Check API health
curl http://localhost:3001/api/v1/health

# Check basic connectivity
curl http://localhost:3001/
```

### Logging
Logs are written to:
- `logs/combined.log` - All log levels
- `logs/error.log` - Error logs only
- Console - Development mode only

### Metrics
The health endpoint provides:
- System uptime and memory usage
- Platform and Node.js version information
- Load averages and system metrics

## Integration

### Frontend Integration
Configure CORS and API URL:
```javascript
// Frontend API client
const API_BASE_URL = 'http://localhost:3001/api/v1';
```

### Environment Integration
The API integrates with:
- Test environment provisioning systems
- Automation workflow engines
- Development dashboard interfaces

## Deployment

### Production Deployment
```bash
# Set production environment
export NODE_ENV=production

# Install production dependencies only
npm ci --only=production

# Start server
npm start
```

### Docker Deployment
```bash
# Build image
docker build -t dev-backend-api .

# Run container
docker run -d \
  -p 3001:3001 \
  --name dev-backend \
  -e NODE_ENV=production \
  dev-backend-api
```

## Troubleshooting

### Common Issues

1. **Port already in use**
   - Change PORT in `.env` file
   - Kill existing process: `lsof -ti:3001 | xargs kill`

2. **CORS errors**
   - Verify FRONTEND_URL in `.env`
   - Check browser console for specific CORS issues

3. **Account creation fails**
   - Check logs: `tail -f logs/error.log`
   - Verify request validation requirements

### Debug Mode
```bash
# Enable debug logging
export DEBUG=*
npm run dev
```

## Contributing

1. Follow existing code style and patterns
2. Add tests for new functionality
3. Update documentation as needed
4. Run linting before committing: `npm run lint`

## Security Considerations

- All endpoints validate input parameters
- Rate limiting prevents abuse
- Error messages don't expose sensitive information
- Accounts are created for development purposes only
- No production credentials or data should be used

This API is designed specifically for development and testing workflows. It should not be used with production data or in production environments without additional security measures.
EOF

    log "✓ Documentation created"
}

# Main installation function
main() {
    log "Setting up Backend Endpoint Setup for Development Testing..."
    log "This creates a comprehensive Node.js/Express API for development account management"
    
    # Check dependencies
    if ! command -v node &> /dev/null; then
        warn "Node.js not found. Please install Node.js 18+ first."
        exit 1
    fi
    
    if ! command -v npm &> /dev/null; then
        warn "npm not found. Please install npm first."
        exit 1
    fi
    
    # Run setup functions
    setup_directories
    create_package_config
    create_main_app
    create_account_routes
    create_account_controller
    create_account_service
    create_workflow_engine
    create_additional_components
    create_environment_config
    create_testing_config
    create_deployment_config
    create_documentation
    
    log "✅ Backend Endpoint Setup for Development Testing complete!"
    log ""
    log "🚀 Quick Start:"
    log "   cd ${REPO_PATH}/backend && ./start.sh dev"
    log ""
    log "🌐 API Endpoints:"
    log "   • Base URL: http://localhost:3001"
    log "   • Health Check: http://localhost:3001/api/v1/health"
    log "   • Create Account: POST /api/v1/account/create"
    log "   • List Accounts: GET /api/v1/account/list"
    log ""
    log "🔧 Development Commands:"
    log "   • Install deps: npm install"
    log "   • Start dev: npm run dev"
    log "   • Run tests: npm test"
    log "   • Lint code: npm run lint"
    log ""
    log "📋 Features:"
    log "   • Account Management - Create and manage test accounts"
    log "   • Workflow Engine - Execute automated development workflows"
    log "   • Input Validation - Comprehensive request validation"
    log "   • Security Features - Rate limiting, CORS, security headers"
    log "   • Health Monitoring - System status and metrics"
    log "   • Testing Suite - Jest tests with coverage reporting"
    log ""
    log "🐳 Docker Deployment:"
    log "   cd ${REPO_PATH}/backend && docker-compose up --build"
}

# Run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi