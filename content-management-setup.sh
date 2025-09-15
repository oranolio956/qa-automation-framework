#!/bin/bash

# Content Management and A/B Testing Setup
# Deploys content management services for Android app testing and optimization

set -e

# Configuration
CONTENT_DIR="$HOME/ContentManagement"
SERVICES_DIR="$CONTENT_DIR/services"
CONFIG_DIR="$CONTENT_DIR/config"
TEMPLATES_DIR="$CONTENT_DIR/templates"
ANALYTICS_DIR="$CONTENT_DIR/analytics"

# Default ports
CONTENT_PROCESSOR_PORT="5000"
ANALYTICS_SERVICE_PORT="5001"
AB_TESTING_PORT="5002"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
    echo -e "${BLUE}[SECTION]${NC} $1"
}

check_prerequisites() {
    log_section "Checking Prerequisites"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Please install Docker first"
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 not found. Install Python3 first"
        exit 1
    fi
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        log_error "Node.js not found. Install Node.js first"
        exit 1
    fi
    
    # Check jq
    if ! command -v jq &> /dev/null; then
        log_warn "jq not found. Installing..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y jq
        elif command -v brew &> /dev/null; then
            brew install jq
        else
            log_error "Cannot install jq automatically. Please install manually"
            exit 1
        fi
    fi
    
    log_info "Prerequisites check completed"
}

setup_content_management_structure() {
    log_section "Setting Up Content Management Structure"
    
    # Create directory structure
    mkdir -p "$CONTENT_DIR"/{services,config,templates,analytics,data,reports}
    mkdir -p "$SERVICES_DIR"/{content-processor,ab-testing,analytics}
    
    log_info "Content management directory structure created at $CONTENT_DIR"
}

create_content_processor_service() {
    log_section "Creating Content Processing Service"
    
    # Create Flask-based content processor
    cat > "$SERVICES_DIR/content-processor/app.py" << 'EOF'
#!/usr/bin/env python3
"""
Content Processing Service
Handles content variations, localization, and A/B testing content generation
"""

import os
import json
import re
import random
import hashlib
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import nltk
from textblob import TextBlob

app = Flask(__name__)
CORS(app)

class ContentProcessor:
    """Content processing and variation generation"""
    
    def __init__(self):
        self.variation_strategies = {
            'synonyms': self.generate_synonym_variations,
            'tone': self.generate_tone_variations,
            'length': self.generate_length_variations,
            'cta': self.generate_cta_variations,
            'personalization': self.generate_personalized_variations
        }
    
    def process_content(self, content, strategy='synonyms', count=3):
        """Generate content variations using specified strategy"""
        if strategy not in self.variation_strategies:
            return {'error': f'Unknown strategy: {strategy}'}
        
        try:
            variations = self.variation_strategies[strategy](content, count)
            return {
                'original': content,
                'strategy': strategy,
                'variations': variations,
                'count': len(variations),
                'generated_at': datetime.now().isoformat()
            }
        except Exception as e:
            return {'error': str(e)}
    
    def generate_synonym_variations(self, content, count=3):
        """Generate variations using synonyms"""
        variations = []
        
        try:
            blob = TextBlob(content)
            words = blob.words
            
            for i in range(count):
                new_content = content
                # Replace 1-2 words with synonyms
                words_to_replace = random.sample(list(words), min(2, len(words)))
                
                for word in words_to_replace:
                    synonyms = word.synsets
                    if synonyms:
                        # Get synonyms from first synset
                        synonym_words = [lemma.name().replace('_', ' ') for lemma in synonyms[0].lemmas()]
                        if synonym_words and synonym_words[0].lower() != word.lower():
                            new_content = new_content.replace(str(word), synonym_words[0], 1)
                
                if new_content != content:
                    variations.append(new_content)
            
            # If no variations generated, create simple alternatives
            if not variations:
                variations = [
                    content.replace('!', '.'),
                    content.replace('.', '!'),
                    content.title()
                ]
                
        except Exception as e:
            # Fallback variations
            variations = [
                f"✨ {content}",
                f"{content} 🚀",
                content.upper() if content != content.upper() else content.lower()
            ]
        
        return variations[:count]
    
    def generate_tone_variations(self, content, count=3):
        """Generate variations with different tones"""
        tone_variations = [
            f"🎉 {content}",  # Enthusiastic
            f"Discover: {content}",  # Curious
            f"Pro tip: {content}",  # Professional
            f"Hey! {content}",  # Casual
            f"Important: {content}"  # Urgent
        ]
        
        return random.sample(tone_variations, min(count, len(tone_variations)))
    
    def generate_length_variations(self, content, count=3):
        """Generate variations with different lengths"""
        variations = []
        
        # Short version
        words = content.split()
        if len(words) > 3:
            short_version = ' '.join(words[:len(words)//2]) + '...'
            variations.append(short_version)
        
        # Extended version
        extended = f"{content} Learn more about this amazing feature!"
        variations.append(extended)
        
        # Bullet point version
        bullet_version = f"• {content}"
        variations.append(bullet_version)
        
        return variations[:count]
    
    def generate_cta_variations(self, content, count=3):
        """Generate call-to-action variations"""
        cta_templates = [
            f"{content} - Try now!",
            f"{content} - Get started today!",
            f"{content} - Join thousands of users!",
            f"{content} - Download free!",
            f"{content} - Start your journey!"
        ]
        
        return random.sample(cta_templates, min(count, len(cta_templates)))
    
    def generate_personalized_variations(self, content, count=3):
        """Generate personalized variations"""
        personal_templates = [
            f"Just for you: {content}",
            f"Your personalized {content.lower()}",
            f"Recommended: {content}",
            f"Based on your activity: {content}"
        ]
        
        return random.sample(personal_templates, min(count, len(personal_templates)))
    
    def analyze_content(self, content):
        """Analyze content characteristics"""
        blob = TextBlob(content)
        
        analysis = {
            'length': len(content),
            'word_count': len(content.split()),
            'sentiment': {
                'polarity': blob.sentiment.polarity,
                'subjectivity': blob.sentiment.subjectivity
            },
            'readability': self.calculate_readability(content),
            'has_emoji': bool(re.search(r'[\U0001f600-\U0001f64f]', content)),
            'has_punctuation': bool(re.search(r'[!?.]', content)),
            'language': str(blob.detect_language()) if hasattr(blob, 'detect_language') else 'en'
        }
        
        return analysis
    
    def calculate_readability(self, content):
        """Calculate simple readability score"""
        words = content.split()
        sentences = re.split(r'[.!?]+', content)
        
        if len(sentences) == 0 or len(words) == 0:
            return 0
        
        avg_words_per_sentence = len(words) / max(len(sentences), 1)
        
        # Simple readability score (lower is easier)
        score = avg_words_per_sentence * 2
        return min(100, max(0, 100 - score))

processor = ContentProcessor()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'content-processor',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/process', methods=['POST'])
def process_content():
    """Process content and generate variations"""
    data = request.get_json()
    
    if not data or 'content' not in data:
        return jsonify({'error': 'Missing content parameter'}), 400
    
    content = data['content']
    strategy = data.get('strategy', 'synonyms')
    count = data.get('count', 3)
    
    result = processor.process_content(content, strategy, count)
    
    if 'error' in result:
        return jsonify(result), 400
    
    return jsonify(result)

@app.route('/analyze', methods=['POST'])
def analyze_content():
    """Analyze content characteristics"""
    data = request.get_json()
    
    if not data or 'content' not in data:
        return jsonify({'error': 'Missing content parameter'}), 400
    
    content = data['content']
    analysis = processor.analyze_content(content)
    
    return jsonify({
        'content': content,
        'analysis': analysis,
        'analyzed_at': datetime.now().isoformat()
    })

@app.route('/batch', methods=['POST'])
def batch_process():
    """Process multiple content items"""
    data = request.get_json()
    
    if not data or 'items' not in data:
        return jsonify({'error': 'Missing items parameter'}), 400
    
    items = data['items']
    strategy = data.get('strategy', 'synonyms')
    count = data.get('count', 3)
    
    results = []
    for item in items:
        if isinstance(item, dict) and 'content' in item:
            content = item['content']
            item_strategy = item.get('strategy', strategy)
            item_count = item.get('count', count)
        else:
            content = str(item)
            item_strategy = strategy
            item_count = count
        
        result = processor.process_content(content, item_strategy, item_count)
        results.append(result)
    
    return jsonify({
        'results': results,
        'processed_count': len(results),
        'processed_at': datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
EOF

    # Create requirements file for content processor
    cat > "$SERVICES_DIR/content-processor/requirements.txt" << 'EOF'
flask==2.3.3
flask-cors==4.0.0
nltk==3.8.1
textblob==0.17.1
requests==2.31.0
python-dotenv==1.0.0
EOF

    # Create Dockerfile for content processor
    cat > "$SERVICES_DIR/content-processor/Dockerfile" << 'EOF'
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('brown'); nltk.download('wordnet')"

COPY app.py .

EXPOSE 5000

CMD ["python", "app.py"]
EOF

    log_info "Content processing service created"
}

create_ab_testing_service() {
    log_section "Creating A/B Testing Service"
    
    # Create A/B testing service
    cat > "$SERVICES_DIR/ab-testing/server.js" << 'EOF'
/**
 * A/B Testing Service
 * Manages experiment configurations, user assignments, and result tracking
 */

const express = require('express');
const cors = require('cors');
const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');

const app = express();
app.use(cors());
app.use(express.json());

const PORT = process.env.PORT || 5002;
const DATA_DIR = path.join(__dirname, 'data');

class ABTestingManager {
    constructor() {
        this.experiments = new Map();
        this.userAssignments = new Map();
        this.results = new Map();
        this.loadData();
    }
    
    async loadData() {
        try {
            await fs.mkdir(DATA_DIR, { recursive: true });
            
            // Load experiments
            try {
                const experimentsData = await fs.readFile(path.join(DATA_DIR, 'experiments.json'), 'utf8');
                const experiments = JSON.parse(experimentsData);
                this.experiments = new Map(Object.entries(experiments));
            } catch (error) {
                console.log('No existing experiments found, starting fresh');
            }
            
            // Load user assignments
            try {
                const assignmentsData = await fs.readFile(path.join(DATA_DIR, 'assignments.json'), 'utf8');
                const assignments = JSON.parse(assignmentsData);
                this.userAssignments = new Map(Object.entries(assignments));
            } catch (error) {
                console.log('No existing assignments found, starting fresh');
            }
            
            // Load results
            try {
                const resultsData = await fs.readFile(path.join(DATA_DIR, 'results.json'), 'utf8');
                const results = JSON.parse(resultsData);
                this.results = new Map(Object.entries(results));
            } catch (error) {
                console.log('No existing results found, starting fresh');
            }
            
        } catch (error) {
            console.error('Error loading data:', error);
        }
    }
    
    async saveData() {
        try {
            await fs.writeFile(
                path.join(DATA_DIR, 'experiments.json'), 
                JSON.stringify(Object.fromEntries(this.experiments), null, 2)
            );
            
            await fs.writeFile(
                path.join(DATA_DIR, 'assignments.json'), 
                JSON.stringify(Object.fromEntries(this.userAssignments), null, 2)
            );
            
            await fs.writeFile(
                path.join(DATA_DIR, 'results.json'), 
                JSON.stringify(Object.fromEntries(this.results), null, 2)
            );
        } catch (error) {
            console.error('Error saving data:', error);
        }
    }
    
    createExperiment(config) {
        const experiment = {
            id: config.id || this.generateId(),
            name: config.name,
            description: config.description || '',
            variants: config.variants || [],
            traffic: config.traffic || 1.0,
            status: 'active',
            created_at: new Date().toISOString(),
            metrics: config.metrics || ['conversion_rate'],
            target_audience: config.target_audience || 'all'
        };
        
        this.experiments.set(experiment.id, experiment);
        this.results.set(experiment.id, {
            experiment_id: experiment.id,
            variant_results: {},
            started_at: new Date().toISOString()
        });
        
        this.saveData();
        return experiment;
    }
    
    assignUserToVariant(experimentId, userId) {
        const experiment = this.experiments.get(experimentId);
        if (!experiment || experiment.status !== 'active') {
            return null;
        }
        
        // Check if user already assigned
        const assignmentKey = `${experimentId}:${userId}`;
        if (this.userAssignments.has(assignmentKey)) {
            return this.userAssignments.get(assignmentKey);
        }
        
        // Assign user to variant based on hash
        const hash = crypto.createHash('md5').update(assignmentKey).digest('hex');
        const hashValue = parseInt(hash.substr(0, 8), 16);
        const variant = experiment.variants[hashValue % experiment.variants.length];
        
        const assignment = {
            user_id: userId,
            experiment_id: experimentId,
            variant: variant.id,
            assigned_at: new Date().toISOString()
        };
        
        this.userAssignments.set(assignmentKey, assignment);
        this.saveData();
        
        return assignment;
    }
    
    trackEvent(experimentId, userId, event, value = 1) {
        const assignment = this.getUserAssignment(experimentId, userId);
        if (!assignment) {
            return null;
        }
        
        const results = this.results.get(experimentId);
        if (!results.variant_results[assignment.variant]) {
            results.variant_results[assignment.variant] = {
                users: new Set(),
                events: {}
            };
        }
        
        const variantResult = results.variant_results[assignment.variant];
        variantResult.users.add(userId);
        
        if (!variantResult.events[event]) {
            variantResult.events[event] = [];
        }
        
        variantResult.events[event].push({
            user_id: userId,
            value: value,
            timestamp: new Date().toISOString()
        });
        
        // Convert Set to Array for JSON serialization
        variantResult.users = Array.from(variantResult.users);
        
        this.results.set(experimentId, results);
        this.saveData();
        
        return { success: true, event, value };
    }
    
    getUserAssignment(experimentId, userId) {
        const assignmentKey = `${experimentId}:${userId}`;
        return this.userAssignments.get(assignmentKey);
    }
    
    getExperimentResults(experimentId) {
        const experiment = this.experiments.get(experimentId);
        const results = this.results.get(experimentId);
        
        if (!experiment || !results) {
            return null;
        }
        
        const analysis = {
            experiment: experiment,
            results: results,
            summary: {}
        };
        
        // Calculate summary statistics
        for (const [variantId, variantResult] of Object.entries(results.variant_results)) {
            const userCount = Array.isArray(variantResult.users) ? variantResult.users.length : 0;
            const eventCounts = {};
            
            for (const [event, eventList] of Object.entries(variantResult.events || {})) {
                eventCounts[event] = {
                    count: eventList.length,
                    total_value: eventList.reduce((sum, e) => sum + e.value, 0),
                    conversion_rate: userCount > 0 ? (eventList.length / userCount) : 0
                };
            }
            
            analysis.summary[variantId] = {
                users: userCount,
                events: eventCounts
            };
        }
        
        return analysis;
    }
    
    generateId() {
        return crypto.randomBytes(8).toString('hex');
    }
}

const abManager = new ABTestingManager();

// Health check
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        service: 'ab-testing',
        timestamp: new Date().toISOString()
    });
});

// Create experiment
app.post('/experiments', (req, res) => {
    try {
        const experiment = abManager.createExperiment(req.body);
        res.json(experiment);
    } catch (error) {
        res.status(400).json({ error: error.message });
    }
});

// List experiments
app.get('/experiments', (req, res) => {
    const experiments = Array.from(abManager.experiments.values());
    res.json(experiments);
});

// Get specific experiment
app.get('/experiments/:id', (req, res) => {
    const experiment = abManager.experiments.get(req.params.id);
    if (!experiment) {
        return res.status(404).json({ error: 'Experiment not found' });
    }
    res.json(experiment);
});

// Assign user to variant
app.post('/experiments/:id/assign', (req, res) => {
    const { user_id } = req.body;
    if (!user_id) {
        return res.status(400).json({ error: 'user_id required' });
    }
    
    const assignment = abManager.assignUserToVariant(req.params.id, user_id);
    if (!assignment) {
        return res.status(404).json({ error: 'Experiment not found or inactive' });
    }
    
    res.json(assignment);
});

// Track event
app.post('/experiments/:id/track', (req, res) => {
    const { user_id, event, value } = req.body;
    if (!user_id || !event) {
        return res.status(400).json({ error: 'user_id and event required' });
    }
    
    const result = abManager.trackEvent(req.params.id, user_id, event, value);
    if (!result) {
        return res.status(404).json({ error: 'User not assigned to experiment' });
    }
    
    res.json(result);
});

// Get experiment results
app.get('/experiments/:id/results', (req, res) => {
    const results = abManager.getExperimentResults(req.params.id);
    if (!results) {
        return res.status(404).json({ error: 'Experiment not found' });
    }
    
    res.json(results);
});

// Get user assignment
app.get('/experiments/:id/users/:userId', (req, res) => {
    const assignment = abManager.getUserAssignment(req.params.id, req.params.userId);
    if (!assignment) {
        return res.status(404).json({ error: 'User not assigned to experiment' });
    }
    
    res.json(assignment);
});

app.listen(PORT, () => {
    console.log(`A/B Testing Service running on port ${PORT}`);
});
EOF

    # Create package.json for A/B testing service
    cat > "$SERVICES_DIR/ab-testing/package.json" << 'EOF'
{
  "name": "ab-testing-service",
  "version": "1.0.0",
  "description": "A/B Testing service for content management",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5"
  },
  "devDependencies": {
    "nodemon": "^3.0.1"
  }
}
EOF

    # Create Dockerfile for A/B testing service
    cat > "$SERVICES_DIR/ab-testing/Dockerfile" << 'EOF'
FROM node:18-slim

WORKDIR /app

COPY package*.json ./
RUN npm install --production

COPY server.js .

EXPOSE 5002

CMD ["npm", "start"]
EOF

    log_info "A/B testing service created"
}

create_analytics_service() {
    log_section "Creating Analytics Service"
    
    # Create analytics service
    cat > "$SERVICES_DIR/analytics/analytics.py" << 'EOF'
#!/usr/bin/env python3
"""
Analytics Service
Collects, processes, and reports on content performance and A/B test results
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import statistics

app = Flask(__name__)
CORS(app)

class AnalyticsManager:
    """Analytics data collection and processing"""
    
    def __init__(self, db_path='analytics.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                user_id TEXT,
                experiment_id TEXT,
                variant_id TEXT,
                content_id TEXT,
                event_data TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Content performance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id TEXT NOT NULL,
                content_type TEXT,
                impressions INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                conversions INTEGER DEFAULT 0,
                engagement_time REAL DEFAULT 0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                experiment_id TEXT,
                variant_id TEXT,
                start_time DATETIME,
                end_time DATETIME,
                actions INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def track_event(self, event_type, user_id=None, experiment_id=None, variant_id=None, 
                   content_id=None, event_data=None):
        """Track an analytics event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO events (event_type, user_id, experiment_id, variant_id, content_id, event_data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (event_type, user_id, experiment_id, variant_id, content_id, json.dumps(event_data)))
        
        conn.commit()
        event_id = cursor.lastrowid
        conn.close()
        
        return event_id
    
    def update_content_performance(self, content_id, content_type=None, 
                                 impressions=0, clicks=0, conversions=0, engagement_time=0):
        """Update content performance metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if content exists
        cursor.execute('SELECT id FROM content_performance WHERE content_id = ?', (content_id,))
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute('''
                UPDATE content_performance 
                SET impressions = impressions + ?, clicks = clicks + ?, 
                    conversions = conversions + ?, engagement_time = engagement_time + ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE content_id = ?
            ''', (impressions, clicks, conversions, engagement_time, content_id))
        else:
            cursor.execute('''
                INSERT INTO content_performance 
                (content_id, content_type, impressions, clicks, conversions, engagement_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (content_id, content_type, impressions, clicks, conversions, engagement_time))
        
        conn.commit()
        conn.close()
    
    def get_content_analytics(self, content_id=None, days=30):
        """Get content performance analytics"""
        conn = sqlite3.connect(self.db_path)
        
        if content_id:
            query = '''
                SELECT * FROM content_performance 
                WHERE content_id = ? AND last_updated >= datetime('now', '-{} days')
            '''.format(days)
            df = pd.read_sql_query(query, conn, params=(content_id,))
        else:
            query = '''
                SELECT * FROM content_performance 
                WHERE last_updated >= datetime('now', '-{} days')
            '''.format(days)
            df = pd.read_sql_query(query, conn)
        
        conn.close()
        
        if df.empty:
            return {}
        
        # Calculate metrics
        analytics = {
            'total_impressions': int(df['impressions'].sum()),
            'total_clicks': int(df['clicks'].sum()),
            'total_conversions': int(df['conversions'].sum()),
            'avg_engagement_time': float(df['engagement_time'].mean()) if len(df) > 0 else 0,
            'click_through_rate': float(df['clicks'].sum() / df['impressions'].sum()) if df['impressions'].sum() > 0 else 0,
            'conversion_rate': float(df['conversions'].sum() / df['clicks'].sum()) if df['clicks'].sum() > 0 else 0,
            'content_count': len(df)
        }
        
        if content_id:
            analytics['content_id'] = content_id
            if len(df) > 0:
                analytics['content_type'] = df.iloc[0]['content_type']
        
        return analytics
    
    def get_experiment_analytics(self, experiment_id, days=30):
        """Get A/B test experiment analytics"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT variant_id, event_type, COUNT(*) as count
            FROM events 
            WHERE experiment_id = ? AND timestamp >= datetime('now', '-{} days')
            GROUP BY variant_id, event_type
        '''.format(days)
        
        df = pd.read_sql_query(query, conn, params=(experiment_id,))
        conn.close()
        
        if df.empty:
            return {'experiment_id': experiment_id, 'variants': {}}
        
        # Group by variant
        analytics = {'experiment_id': experiment_id, 'variants': {}}
        
        for variant_id in df['variant_id'].unique():
            if pd.isna(variant_id):
                continue
                
            variant_data = df[df['variant_id'] == variant_id]
            variant_analytics = {}
            
            for _, row in variant_data.iterrows():
                variant_analytics[row['event_type']] = int(row['count'])
            
            analytics['variants'][variant_id] = variant_analytics
        
        return analytics
    
    def get_user_analytics(self, user_id, days=30):
        """Get user-specific analytics"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT event_type, COUNT(*) as count
            FROM events 
            WHERE user_id = ? AND timestamp >= datetime('now', '-{} days')
            GROUP BY event_type
        '''.format(days)
        
        df = pd.read_sql_query(query, conn, params=(user_id,))
        conn.close()
        
        if df.empty:
            return {'user_id': user_id, 'events': {}}
        
        events = {}
        for _, row in df.iterrows():
            events[row['event_type']] = int(row['count'])
        
        return {'user_id': user_id, 'events': events}
    
    def generate_report(self, report_type='summary', days=7):
        """Generate analytics report"""
        conn = sqlite3.connect(self.db_path)
        
        report = {
            'report_type': report_type,
            'period_days': days,
            'generated_at': datetime.now().isoformat()
        }
        
        if report_type == 'summary':
            # Overall summary
            events_query = '''
                SELECT event_type, COUNT(*) as count
                FROM events 
                WHERE timestamp >= datetime('now', '-{} days')
                GROUP BY event_type
            '''.format(days)
            
            events_df = pd.read_sql_query(events_query, conn)
            report['total_events'] = {}
            
            for _, row in events_df.iterrows():
                report['total_events'][row['event_type']] = int(row['count'])
            
            # Content performance summary
            content_query = '''
                SELECT AVG(impressions) as avg_impressions, AVG(clicks) as avg_clicks,
                       AVG(conversions) as avg_conversions, COUNT(*) as content_count
                FROM content_performance 
                WHERE last_updated >= datetime('now', '-{} days')
            '''.format(days)
            
            content_df = pd.read_sql_query(content_query, conn)
            if not content_df.empty and content_df.iloc[0]['content_count'] > 0:
                row = content_df.iloc[0]
                report['content_summary'] = {
                    'avg_impressions': float(row['avg_impressions'] or 0),
                    'avg_clicks': float(row['avg_clicks'] or 0),
                    'avg_conversions': float(row['avg_conversions'] or 0),
                    'active_content_count': int(row['content_count'])
                }
        
        conn.close()
        return report

analytics = AnalyticsManager()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'analytics',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/track', methods=['POST'])
def track_event():
    """Track an analytics event"""
    data = request.get_json()
    
    if not data or 'event_type' not in data:
        return jsonify({'error': 'event_type required'}), 400
    
    event_id = analytics.track_event(
        event_type=data['event_type'],
        user_id=data.get('user_id'),
        experiment_id=data.get('experiment_id'),
        variant_id=data.get('variant_id'),
        content_id=data.get('content_id'),
        event_data=data.get('event_data')
    )
    
    return jsonify({'event_id': event_id, 'status': 'tracked'})

@app.route('/content/<content_id>/performance', methods=['POST'])
def update_content_performance():
    """Update content performance metrics"""
    content_id = request.view_args['content_id']
    data = request.get_json()
    
    analytics.update_content_performance(
        content_id=content_id,
        content_type=data.get('content_type'),
        impressions=data.get('impressions', 0),
        clicks=data.get('clicks', 0),
        conversions=data.get('conversions', 0),
        engagement_time=data.get('engagement_time', 0)
    )
    
    return jsonify({'status': 'updated', 'content_id': content_id})

@app.route('/content/<content_id>/analytics', methods=['GET'])
def get_content_analytics():
    """Get content analytics"""
    content_id = request.view_args['content_id']
    days = request.args.get('days', 30, type=int)
    
    result = analytics.get_content_analytics(content_id, days)
    return jsonify(result)

@app.route('/experiments/<experiment_id>/analytics', methods=['GET'])
def get_experiment_analytics():
    """Get experiment analytics"""
    experiment_id = request.view_args['experiment_id']
    days = request.args.get('days', 30, type=int)
    
    result = analytics.get_experiment_analytics(experiment_id, days)
    return jsonify(result)

@app.route('/users/<user_id>/analytics', methods=['GET'])
def get_user_analytics():
    """Get user analytics"""
    user_id = request.view_args['user_id']
    days = request.args.get('days', 30, type=int)
    
    result = analytics.get_user_analytics(user_id, days)
    return jsonify(result)

@app.route('/reports/<report_type>', methods=['GET'])
def generate_report():
    """Generate analytics report"""
    report_type = request.view_args['report_type']
    days = request.args.get('days', 7, type=int)
    
    report = analytics.generate_report(report_type, days)
    return jsonify(report)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
EOF

    # Create requirements for analytics service
    cat > "$SERVICES_DIR/analytics/requirements.txt" << 'EOF'
flask==2.3.3
flask-cors==4.0.0
pandas==2.1.3
sqlite3
python-dotenv==1.0.0
EOF

    log_info "Analytics service created"
}

create_docker_compose() {
    log_section "Creating Docker Compose Configuration"
    
    cat > "$CONTENT_DIR/docker-compose.yml" << 'EOF'
version: '3.8'

services:
  content-processor:
    build: ./services/content-processor
    container_name: content-processor
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
    volumes:
      - ./data/content:/app/data
    restart: unless-stopped
    networks:
      - content-network

  ab-testing:
    build: ./services/ab-testing
    container_name: ab-testing
    ports:
      - "5002:5002"
    volumes:
      - ./data/ab-testing:/app/data
    restart: unless-stopped
    networks:
      - content-network

  analytics:
    build:
      context: ./services/analytics
      dockerfile_inline: |
        FROM python:3.9-slim
        WORKDIR /app
        COPY requirements.txt .
        RUN pip install --no-cache-dir -r requirements.txt
        COPY analytics.py .
        EXPOSE 5001
        CMD ["python", "analytics.py"]
    container_name: analytics
    ports:
      - "5001:5001"
    environment:
      - FLASK_ENV=production
    volumes:
      - ./data/analytics:/app/data
    restart: unless-stopped
    networks:
      - content-network

  nginx:
    image: nginx:alpine
    container_name: content-nginx
    ports:
      - "8080:80"
    volumes:
      - ./config/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./web:/usr/share/nginx/html:ro
    depends_on:
      - content-processor
      - ab-testing
      - analytics
    restart: unless-stopped
    networks:
      - content-network

networks:
  content-network:
    driver: bridge

volumes:
  content-data:
  ab-testing-data:
  analytics-data:
EOF

    log_info "Docker Compose configuration created"
}

create_management_tools() {
    log_section "Creating Content Management Tools"
    
    # Content management CLI tool
    cat > "$CONTENT_DIR/content-manager.py" << 'EOF'
#!/usr/bin/env python3
"""
Content Management CLI Tool
Command-line interface for managing content variations and A/B tests
"""

import argparse
import requests
import json
import sys
from datetime import datetime

class ContentManager:
    """Content management operations"""
    
    def __init__(self, base_url='http://localhost'):
        self.content_processor_url = f"{base_url}:5000"
        self.ab_testing_url = f"{base_url}:5002"
        self.analytics_url = f"{base_url}:5001"
    
    def generate_variations(self, content, strategy='synonyms', count=3):
        """Generate content variations"""
        try:
            response = requests.post(
                f"{self.content_processor_url}/process",
                json={
                    'content': content,
                    'strategy': strategy,
                    'count': count
                }
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {'error': f'Failed to generate variations: {e}'}
    
    def analyze_content(self, content):
        """Analyze content characteristics"""
        try:
            response = requests.post(
                f"{self.content_processor_url}/analyze",
                json={'content': content}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {'error': f'Failed to analyze content: {e}'}
    
    def create_experiment(self, name, variants, description=''):
        """Create A/B test experiment"""
        try:
            experiment_data = {
                'name': name,
                'description': description,
                'variants': [
                    {'id': f'variant_{i}', 'content': variant}
                    for i, variant in enumerate(variants)
                ],
                'metrics': ['click', 'conversion', 'engagement']
            }
            
            response = requests.post(
                f"{self.ab_testing_url}/experiments",
                json=experiment_data
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {'error': f'Failed to create experiment: {e}'}
    
    def get_experiment_results(self, experiment_id):
        """Get experiment results"""
        try:
            response = requests.get(f"{self.ab_testing_url}/experiments/{experiment_id}/results")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {'error': f'Failed to get results: {e}'}
    
    def assign_user_to_experiment(self, experiment_id, user_id):
        """Assign user to experiment variant"""
        try:
            response = requests.post(
                f"{self.ab_testing_url}/experiments/{experiment_id}/assign",
                json={'user_id': user_id}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {'error': f'Failed to assign user: {e}'}
    
    def track_event(self, experiment_id, user_id, event_type, value=1):
        """Track experiment event"""
        try:
            response = requests.post(
                f"{self.ab_testing_url}/experiments/{experiment_id}/track",
                json={
                    'user_id': user_id,
                    'event': event_type,
                    'value': value
                }
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {'error': f'Failed to track event: {e}'}

def main():
    parser = argparse.ArgumentParser(description='Content Management CLI')
    parser.add_argument('--base-url', default='http://localhost', help='Base URL for services')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Generate variations command
    variations_parser = subparsers.add_parser('generate', help='Generate content variations')
    variations_parser.add_argument('content', help='Content to generate variations for')
    variations_parser.add_argument('--strategy', default='synonyms', 
                                 choices=['synonyms', 'tone', 'length', 'cta', 'personalization'],
                                 help='Variation strategy')
    variations_parser.add_argument('--count', type=int, default=3, help='Number of variations')
    
    # Analyze content command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze content')
    analyze_parser.add_argument('content', help='Content to analyze')
    
    # Create experiment command
    experiment_parser = subparsers.add_parser('experiment', help='Create A/B test experiment')
    experiment_parser.add_argument('name', help='Experiment name')
    experiment_parser.add_argument('variants', nargs='+', help='Variant contents')
    experiment_parser.add_argument('--description', default='', help='Experiment description')
    
    # Get results command
    results_parser = subparsers.add_parser('results', help='Get experiment results')
    results_parser.add_argument('experiment_id', help='Experiment ID')
    
    # Assign user command
    assign_parser = subparsers.add_parser('assign', help='Assign user to experiment')
    assign_parser.add_argument('experiment_id', help='Experiment ID')
    assign_parser.add_argument('user_id', help='User ID')
    
    # Track event command
    track_parser = subparsers.add_parser('track', help='Track experiment event')
    track_parser.add_argument('experiment_id', help='Experiment ID')
    track_parser.add_argument('user_id', help='User ID')
    track_parser.add_argument('event_type', help='Event type (click, conversion, etc.)')
    track_parser.add_argument('--value', type=float, default=1.0, help='Event value')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    manager = ContentManager(args.base_url)
    
    if args.command == 'generate':
        result = manager.generate_variations(args.content, args.strategy, args.count)
        if 'error' in result:
            print(f"Error: {result['error']}")
            sys.exit(1)
        
        print(f"Original: {result['original']}")
        print(f"Strategy: {result['strategy']}")
        print("Variations:")
        for i, variation in enumerate(result['variations'], 1):
            print(f"  {i}. {variation}")
    
    elif args.command == 'analyze':
        result = manager.analyze_content(args.content)
        if 'error' in result:
            print(f"Error: {result['error']}")
            sys.exit(1)
        
        analysis = result['analysis']
        print(f"Content: {result['content']}")
        print(f"Length: {analysis['length']} characters, {analysis['word_count']} words")
        print(f"Sentiment: {analysis['sentiment']['polarity']:.2f} polarity, {analysis['sentiment']['subjectivity']:.2f} subjectivity")
        print(f"Readability: {analysis['readability']:.1f}/100")
        print(f"Has emoji: {analysis['has_emoji']}")
        print(f"Language: {analysis['language']}")
    
    elif args.command == 'experiment':
        result = manager.create_experiment(args.name, args.variants, args.description)
        if 'error' in result:
            print(f"Error: {result['error']}")
            sys.exit(1)
        
        print(f"Experiment created: {result['id']}")
        print(f"Name: {result['name']}")
        print(f"Variants: {len(result['variants'])}")
        print(f"Status: {result['status']}")
    
    elif args.command == 'results':
        result = manager.get_experiment_results(args.experiment_id)
        if 'error' in result:
            print(f"Error: {result['error']}")
            sys.exit(1)
        
        experiment = result['experiment']
        summary = result['summary']
        
        print(f"Experiment: {experiment['name']} ({args.experiment_id})")
        print(f"Status: {experiment['status']}")
        print("\nResults by variant:")
        
        for variant_id, stats in summary.items():
            print(f"  {variant_id}:")
            print(f"    Users: {stats['users']}")
            print(f"    Events: {stats['events']}")
    
    elif args.command == 'assign':
        result = manager.assign_user_to_experiment(args.experiment_id, args.user_id)
        if 'error' in result:
            print(f"Error: {result['error']}")
            sys.exit(1)
        
        print(f"User {args.user_id} assigned to variant: {result['variant']}")
    
    elif args.command == 'track':
        result = manager.track_event(args.experiment_id, args.user_id, args.event_type, args.value)
        if 'error' in result:
            print(f"Error: {result['error']}")
            sys.exit(1)
        
        print(f"Event tracked: {result['event']} (value: {result['value']})")

if __name__ == '__main__':
    main()
EOF

    chmod +x "$CONTENT_DIR/content-manager.py"
    
    # Web dashboard configuration
    cat > "$CONFIG_DIR/nginx.conf" << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream content_processor {
        server content-processor:5000;
    }
    
    upstream ab_testing {
        server ab-testing:5002;
    }
    
    upstream analytics {
        server analytics:5001;
    }
    
    server {
        listen 80;
        
        location / {
            root /usr/share/nginx/html;
            index index.html;
        }
        
        location /api/content/ {
            proxy_pass http://content_processor/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
        
        location /api/experiments/ {
            proxy_pass http://ab_testing/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
        
        location /api/analytics/ {
            proxy_pass http://analytics/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
EOF

    log_info "Content management tools created"
}

create_web_dashboard() {
    log_section "Creating Web Dashboard"
    
    mkdir -p "$CONTENT_DIR/web"
    
    # Simple web dashboard
    cat > "$CONTENT_DIR/web/index.html" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Content Management Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        .header h1 {
            color: #2c3e50;
            margin-bottom: 10px;
        }
        
        .services-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .service-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .service-card h3 {
            color: #34495e;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
        }
        
        .service-card .status {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-left: 10px;
        }
        
        .status.online { background: #27ae60; }
        .status.offline { background: #e74c3c; }
        
        .service-card p {
            color: #7f8c8d;
            margin-bottom: 15px;
        }
        
        .btn {
            background: #3498db;
            color: white;
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            margin-right: 10px;
        }
        
        .btn:hover {
            background: #2980b9;
        }
        
        .btn.success { background: #27ae60; }
        .btn.warning { background: #f39c12; }
        
        .content-form {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        .form-group {
            margin-bottom: 15px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
        }
        
        .form-group input, .form-group select, .form-group textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        
        .form-group textarea {
            height: 100px;
            resize: vertical;
        }
        
        .results {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-top: 20px;
        }
        
        .variation-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 10px;
            border-left: 3px solid #3498db;
        }
        
        .loading {
            text-align: center;
            padding: 20px;
            color: #7f8c8d;
        }
        
        .error {
            background: #fee;
            color: #c0392b;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Content Management Dashboard</h1>
            <p>Manage content variations and A/B tests for your Android applications</p>
        </div>
        
        <div class="services-grid">
            <div class="service-card">
                <h3>Content Processor <span class="status" id="content-status"></span></h3>
                <p>Generate content variations using different strategies like synonyms, tone, and length adjustments.</p>
                <button class="btn" onclick="testService('content')">Test Service</button>
            </div>
            
            <div class="service-card">
                <h3>A/B Testing <span class="status" id="ab-status"></span></h3>
                <p>Create and manage A/B test experiments with variant assignments and result tracking.</p>
                <button class="btn" onclick="testService('ab')">Test Service</button>
            </div>
            
            <div class="service-card">
                <h3>Analytics <span class="status" id="analytics-status"></span></h3>
                <p>Track content performance, user engagement, and experiment results with detailed analytics.</p>
                <button class="btn" onclick="testService('analytics')">Test Service</button>
            </div>
        </div>
        
        <div class="content-form">
            <h3>Generate Content Variations</h3>
            <div class="form-group">
                <label for="content-input">Content:</label>
                <textarea id="content-input" placeholder="Enter your content here..."></textarea>
            </div>
            
            <div class="form-group">
                <label for="strategy-select">Strategy:</label>
                <select id="strategy-select">
                    <option value="synonyms">Synonyms</option>
                    <option value="tone">Tone Variations</option>
                    <option value="length">Length Variations</option>
                    <option value="cta">Call-to-Action</option>
                    <option value="personalization">Personalization</option>
                </select>
            </div>
            
            <div class="form-group">
                <label for="count-input">Number of Variations:</label>
                <input type="number" id="count-input" value="3" min="1" max="10">
            </div>
            
            <button class="btn success" onclick="generateVariations()">Generate Variations</button>
            <button class="btn warning" onclick="analyzeContent()">Analyze Content</button>
        </div>
        
        <div id="results" class="results" style="display: none;">
            <h3>Results</h3>
            <div id="results-content"></div>
        </div>
    </div>
    
    <script>
        // Check service status on load
        document.addEventListener('DOMContentLoaded', function() {
            checkServiceStatus();
        });
        
        async function checkServiceStatus() {
            const services = [
                { id: 'content-status', url: '/api/content/health' },
                { id: 'ab-status', url: '/api/experiments/health' },
                { id: 'analytics-status', url: '/api/analytics/health' }
            ];
            
            for (const service of services) {
                try {
                    const response = await fetch(service.url);
                    const statusElement = document.getElementById(service.id);
                    
                    if (response.ok) {
                        statusElement.className = 'status online';
                    } else {
                        statusElement.className = 'status offline';
                    }
                } catch (error) {
                    document.getElementById(service.id).className = 'status offline';
                }
            }
        }
        
        async function testService(service) {
            const urls = {
                content: '/api/content/health',
                ab: '/api/experiments/health',
                analytics: '/api/analytics/health'
            };
            
            try {
                const response = await fetch(urls[service]);
                const data = await response.json();
                alert(`${service} service: ${JSON.stringify(data, null, 2)}`);
            } catch (error) {
                alert(`${service} service error: ${error.message}`);
            }
        }
        
        async function generateVariations() {
            const content = document.getElementById('content-input').value;
            const strategy = document.getElementById('strategy-select').value;
            const count = parseInt(document.getElementById('count-input').value);
            
            if (!content.trim()) {
                alert('Please enter some content to generate variations');
                return;
            }
            
            showLoading();
            
            try {
                const response = await fetch('/api/content/process', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        content: content,
                        strategy: strategy,
                        count: count
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    displayVariations(data);
                } else {
                    showError(data.error || 'Failed to generate variations');
                }
            } catch (error) {
                showError(`Network error: ${error.message}`);
            }
        }
        
        async function analyzeContent() {
            const content = document.getElementById('content-input').value;
            
            if (!content.trim()) {
                alert('Please enter some content to analyze');
                return;
            }
            
            showLoading();
            
            try {
                const response = await fetch('/api/content/analyze', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ content: content })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    displayAnalysis(data);
                } else {
                    showError(data.error || 'Failed to analyze content');
                }
            } catch (error) {
                showError(`Network error: ${error.message}`);
            }
        }
        
        function showLoading() {
            const resultsDiv = document.getElementById('results');
            const resultsContent = document.getElementById('results-content');
            
            resultsDiv.style.display = 'block';
            resultsContent.innerHTML = '<div class="loading">Processing...</div>';
        }
        
        function showError(message) {
            const resultsContent = document.getElementById('results-content');
            resultsContent.innerHTML = `<div class="error">${message}</div>`;
        }
        
        function displayVariations(data) {
            const resultsContent = document.getElementById('results-content');
            
            let html = `
                <h4>Original Content:</h4>
                <div class="variation-item">${data.original}</div>
                
                <h4>Generated Variations (${data.strategy}):</h4>
            `;
            
            data.variations.forEach((variation, index) => {
                html += `<div class="variation-item">${index + 1}. ${variation}</div>`;
            });
            
            resultsContent.innerHTML = html;
        }
        
        function displayAnalysis(data) {
            const resultsContent = document.getElementById('results-content');
            const analysis = data.analysis;
            
            const html = `
                <h4>Content Analysis:</h4>
                <div class="variation-item">
                    <strong>Content:</strong> ${data.content}<br>
                    <strong>Length:</strong> ${analysis.length} characters, ${analysis.word_count} words<br>
                    <strong>Sentiment:</strong> ${analysis.sentiment.polarity.toFixed(2)} polarity, ${analysis.sentiment.subjectivity.toFixed(2)} subjectivity<br>
                    <strong>Readability Score:</strong> ${analysis.readability.toFixed(1)}/100<br>
                    <strong>Has Emoji:</strong> ${analysis.has_emoji ? 'Yes' : 'No'}<br>
                    <strong>Language:</strong> ${analysis.language}
                </div>
            `;
            
            resultsContent.innerHTML = html;
        }
    </script>
</body>
</html>
EOF

    log_info "Web dashboard created"
}

create_example_scripts() {
    log_section "Creating Example Usage Scripts"
    
    # Example usage script
    cat > "$CONTENT_DIR/example-usage.sh" << 'EOF'
#!/bin/bash

# Content Management Example Usage
# Demonstrates how to use the content management system

CONTENT_MANAGER="./content-manager.py"
BASE_URL="http://localhost"

echo "Content Management System Demo"
echo "============================="

# Example content
EXAMPLE_CONTENT="Download our amazing app and discover new features!"

echo -e "\n1. Generating content variations..."
echo "Original: $EXAMPLE_CONTENT"

python3 "$CONTENT_MANAGER" --base-url "$BASE_URL" generate "$EXAMPLE_CONTENT" --strategy synonyms --count 3

echo -e "\n2. Analyzing content..."
python3 "$CONTENT_MANAGER" --base-url "$BASE_URL" analyze "$EXAMPLE_CONTENT"

echo -e "\n3. Creating A/B test experiment..."
EXPERIMENT_NAME="App Download CTA Test"
VARIANT1="Download our amazing app and discover new features!"
VARIANT2="Get our incredible app and explore amazing features!"
VARIANT3="Try our fantastic app and find exciting features!"

python3 "$CONTENT_MANAGER" --base-url "$BASE_URL" experiment "$EXPERIMENT_NAME" "$VARIANT1" "$VARIANT2" "$VARIANT3" --description "Testing different CTA variations"

echo -e "\nDemo completed! Check the web dashboard at http://localhost:8080"
EOF

    chmod +x "$CONTENT_DIR/example-usage.sh"
    
    # API examples
    cat > "$CONTENT_DIR/api-examples.sh" << 'EOF'
#!/bin/bash

# API Usage Examples
# Direct API calls to content management services

BASE_URL="http://localhost"

echo "Content Management API Examples"
echo "==============================="

echo -e "\n1. Health checks..."
echo "Content Processor:"
curl -s "$BASE_URL:5000/health" | jq .

echo -e "\nA/B Testing:"
curl -s "$BASE_URL:5002/health" | jq .

echo -e "\nAnalytics:"
curl -s "$BASE_URL:5001/health" | jq .

echo -e "\n2. Generate content variations..."
curl -s -X POST "$BASE_URL:5000/process" \
  -H "Content-Type: application/json" \
  -d '{"content":"Join thousands of happy users!", "strategy":"tone", "count":3}' | jq .

echo -e "\n3. Analyze content..."
curl -s -X POST "$BASE_URL:5000/analyze" \
  -H "Content-Type: application/json" \
  -d '{"content":"Download now and save 50%!"}' | jq .

echo -e "\n4. Create experiment..."
curl -s -X POST "$BASE_URL:5002/experiments" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Button Text Test",
    "description": "Testing different button texts",
    "variants": [
      {"id": "control", "content": "Download Now"},
      {"id": "variant_a", "content": "Get Started"},
      {"id": "variant_b", "content": "Try Free"}
    ]
  }' | jq .

echo -e "\nAPI examples completed!"
EOF

    chmod +x "$CONTENT_DIR/api-examples.sh"
    
    log_info "Example scripts created"
}

create_startup_script() {
    log_section "Creating Startup Script"
    
    cat > "$CONTENT_DIR/start-services.sh" << 'EOF'
#!/bin/bash

# Content Management Services Startup Script
# Starts all content management services

CONTENT_DIR="$HOME/ContentManagement"
cd "$CONTENT_DIR"

echo "Starting Content Management Services"
echo "==================================="

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Start services with Docker Compose
echo "Starting services with Docker Compose..."
docker-compose up -d

# Wait for services to start
echo "Waiting for services to start..."
sleep 10

# Check service health
echo "Checking service health..."

check_service() {
    local name="$1"
    local url="$2"
    
    if curl -s "$url" >/dev/null 2>&1; then
        echo "✓ $name is running"
    else
        echo "✗ $name is not responding"
    fi
}

check_service "Content Processor" "http://localhost:5000/health"
check_service "A/B Testing" "http://localhost:5002/health"
check_service "Analytics" "http://localhost:5001/health"
check_service "Web Dashboard" "http://localhost:8080"

echo
echo "Services started successfully!"
echo
echo "Available endpoints:"
echo "• Content Processor: http://localhost:5000"
echo "• A/B Testing: http://localhost:5002"
echo "• Analytics: http://localhost:5001"
echo "• Web Dashboard: http://localhost:8080"
echo
echo "CLI tool: ./content-manager.py --help"
echo "Example usage: ./example-usage.sh"
EOF

    chmod +x "$CONTENT_DIR/start-services.sh"
    
    # Stop services script
    cat > "$CONTENT_DIR/stop-services.sh" << 'EOF'
#!/bin/bash

# Stop Content Management Services

CONTENT_DIR="$HOME/ContentManagement"
cd "$CONTENT_DIR"

echo "Stopping Content Management Services..."
docker-compose down

echo "Services stopped."
EOF

    chmod +x "$CONTENT_DIR/stop-services.sh"
    
    log_info "Startup scripts created"
}

verify_installation() {
    log_section "Verifying Installation"
    
    echo "Content Management System Status:"
    echo "────────────────────────────────────"
    
    # Check directory structure
    if [[ -d "$CONTENT_DIR" ]]; then
        echo "✓ Content management directory: $CONTENT_DIR"
    else
        echo "✗ Content management directory missing"
    fi
    
    # Check services
    local services=(
        "services/content-processor/app.py"
        "services/ab-testing/server.js"
        "services/analytics/analytics.py"
    )
    
    for service in "${services[@]}"; do
        if [[ -f "$CONTENT_DIR/$service" ]]; then
            echo "✓ Service: $service"
        else
            echo "✗ Service missing: $service"
        fi
    done
    
    # Check tools
    if [[ -f "$CONTENT_DIR/content-manager.py" ]]; then
        echo "✓ CLI tool: content-manager.py"
    else
        echo "✗ CLI tool missing"
    fi
    
    # Check Docker Compose
    if [[ -f "$CONTENT_DIR/docker-compose.yml" ]]; then
        echo "✓ Docker Compose configuration"
    else
        echo "✗ Docker Compose configuration missing"
    fi
    
    # Check web dashboard
    if [[ -f "$CONTENT_DIR/web/index.html" ]]; then
        echo "✓ Web dashboard"
    else
        echo "✗ Web dashboard missing"
    fi
    
    echo "────────────────────────────────────"
    
    log_info "Installation verification completed"
}

main() {
    log_info "Starting Content Management Setup"
    echo
    
    check_prerequisites
    setup_content_management_structure
    create_content_processor_service
    create_ab_testing_service
    create_analytics_service
    create_docker_compose
    create_management_tools
    create_web_dashboard
    create_example_scripts
    create_startup_script
    verify_installation
    
    echo
    log_info "Content Management setup completed successfully!"
    echo
    echo "Installation directory: $CONTENT_DIR"
    echo
    echo "Quick start:"
    echo "1. cd $CONTENT_DIR"
    echo "2. ./start-services.sh"
    echo "3. Open http://localhost:8080 in your browser"
    echo "4. Try: ./example-usage.sh"
    echo
    echo "Services:"
    echo "• Content Processor: http://localhost:5000"
    echo "• A/B Testing: http://localhost:5002" 
    echo "• Analytics: http://localhost:5001"
    echo "• Web Dashboard: http://localhost:8080"
}

main "$@"