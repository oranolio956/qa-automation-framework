#!/usr/bin/env python3
"""
Email Template Management System
Professional email template engine with variable substitution, versioning, and analytics
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import jinja2
import hashlib
import sqlite3
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TemplateType(Enum):
    WELCOME = "welcome"
    VERIFICATION = "verification"
    TRANSACTIONAL = "transactional"
    MARKETING = "marketing"
    NOTIFICATION = "notification"
    INVOICE = "invoice"
    REMINDER = "reminder"
    NEWSLETTER = "newsletter"

class TemplateStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"

@dataclass
class EmailTemplate:
    """Email template data structure"""
    id: str
    name: str
    template_type: TemplateType
    subject: str
    body_text: str
    body_html: Optional[str] = None
    variables: List[str] = None
    status: TemplateStatus = TemplateStatus.DRAFT
    version: str = "1.0.0"
    created_at: datetime = None
    updated_at: datetime = None
    created_by: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = None
    usage_count: int = 0
    last_used: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = self.created_at
        if self.variables is None:
            self.variables = self._extract_variables()
        if self.tags is None:
            self.tags = []
    
    def _extract_variables(self) -> List[str]:
        """Extract variables from template content"""
        import re
        variables = set()
        
        # Jinja2 variable pattern: {{ variable_name }}
        jinja_pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}'
        
        # Extract from subject
        variables.update(re.findall(jinja_pattern, self.subject))
        
        # Extract from text body
        variables.update(re.findall(jinja_pattern, self.body_text))
        
        # Extract from HTML body
        if self.body_html:
            variables.update(re.findall(jinja_pattern, self.body_html))
        
        return sorted(list(variables))
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            'id': self.id,
            'name': self.name,
            'template_type': self.template_type.value,
            'subject': self.subject,
            'body_text': self.body_text,
            'body_html': self.body_html,
            'variables': self.variables,
            'status': self.status.value,
            'version': self.version,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'created_by': self.created_by,
            'description': self.description,
            'tags': self.tags,
            'usage_count': self.usage_count,
            'last_used': self.last_used.isoformat() if self.last_used else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'EmailTemplate':
        """Create from dictionary"""
        template = cls(
            id=data['id'],
            name=data['name'],
            template_type=TemplateType(data['template_type']),
            subject=data['subject'],
            body_text=data['body_text'],
            body_html=data.get('body_html'),
            variables=data.get('variables', []),
            status=TemplateStatus(data.get('status', 'draft')),
            version=data.get('version', '1.0.0'),
            created_by=data.get('created_by'),
            description=data.get('description'),
            tags=data.get('tags', []),
            usage_count=data.get('usage_count', 0)
        )
        
        if data.get('created_at'):
            template.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            template.updated_at = datetime.fromisoformat(data['updated_at'])
        if data.get('last_used'):
            template.last_used = datetime.fromisoformat(data['last_used'])
        
        return template

@dataclass
class TemplateRenderResult:
    """Result of template rendering"""
    success: bool
    subject: Optional[str] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    error_message: Optional[str] = None
    missing_variables: List[str] = None
    render_time: float = 0.0
    
    def __post_init__(self):
        if self.missing_variables is None:
            self.missing_variables = []

@dataclass
class TemplateUsageStats:
    """Template usage statistics"""
    template_id: str
    total_uses: int
    last_30_days: int
    success_rate: float
    avg_render_time: float
    most_common_variables: Dict[str, int]
    error_count: int
    last_used: Optional[datetime]

class EmailTemplateManager:
    """Professional email template management system"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.templates = {}
        self.template_stats = {}
        
        # Database configuration
        self.db_path = self.config.get('db_path', 'email_templates.db')
        self.init_database()
        
        # Jinja2 environment
        self.jinja_env = jinja2.Environment(
            loader=jinja2.BaseLoader(),
            autoescape=jinja2.select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Load existing templates
        self.load_templates()
        
        logger.info(f"Email Template Manager initialized with {len(self.templates)} templates")
    
    def init_database(self):
        """Initialize SQLite database for template storage"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create templates table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    template_type TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body_text TEXT NOT NULL,
                    body_html TEXT,
                    variables TEXT,
                    status TEXT DEFAULT 'draft',
                    version TEXT DEFAULT '1.0.0',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by TEXT,
                    description TEXT,
                    tags TEXT,
                    usage_count INTEGER DEFAULT 0,
                    last_used TIMESTAMP
                )
            ''')
            
            # Create template usage table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS template_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_id TEXT NOT NULL,
                    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    variables_used TEXT,
                    render_time REAL,
                    success BOOLEAN,
                    error_message TEXT,
                    FOREIGN KEY (template_id) REFERENCES templates (id)
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_template_type ON templates(template_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_template_status ON templates(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_template ON template_usage(template_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_usage_date ON template_usage(used_at)')
            
            conn.commit()
            conn.close()
            
            logger.info("Template database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize template database: {e}")
            raise
    
    def load_templates(self):
        """Load templates from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM templates')
            rows = cursor.fetchall()
            
            columns = [description[0] for description in cursor.description]
            
            for row in rows:
                data = dict(zip(columns, row))
                
                # Parse JSON fields
                if data['variables']:
                    data['variables'] = json.loads(data['variables'])
                if data['tags']:
                    data['tags'] = json.loads(data['tags'])
                
                template = EmailTemplate.from_dict(data)
                self.templates[template.id] = template
            
            conn.close()
            
            logger.info(f"Loaded {len(self.templates)} templates from database")
            
        except Exception as e:
            logger.error(f"Failed to load templates: {e}")
    
    def create_template(self, template: EmailTemplate) -> bool:
        """Create new email template"""
        try:
            # Validate template
            if not template.id or not template.name:
                raise ValueError("Template ID and name are required")
            
            if template.id in self.templates:
                raise ValueError(f"Template {template.id} already exists")
            
            # Save to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO templates (
                    id, name, template_type, subject, body_text, body_html,
                    variables, status, version, created_at, updated_at,
                    created_by, description, tags, usage_count, last_used
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                template.id,
                template.name,
                template.template_type.value,
                template.subject,
                template.body_text,
                template.body_html,
                json.dumps(template.variables),
                template.status.value,
                template.version,
                template.created_at.isoformat(),
                template.updated_at.isoformat(),
                template.created_by,
                template.description,
                json.dumps(template.tags),
                template.usage_count,
                template.last_used.isoformat() if template.last_used else None
            ))
            
            conn.commit()
            conn.close()
            
            # Store in memory
            self.templates[template.id] = template
            
            logger.info(f"Created template: {template.id} - {template.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create template: {e}")
            return False
    
    def update_template(self, template_id: str, updates: Dict) -> bool:
        """Update existing template"""
        try:
            if template_id not in self.templates:
                raise ValueError(f"Template {template_id} not found")
            
            template = self.templates[template_id]
            
            # Update fields
            for field, value in updates.items():
                if hasattr(template, field):
                    setattr(template, field, value)
            
            # Update timestamp and variables
            template.updated_at = datetime.now()
            template.variables = template._extract_variables()
            
            # Save to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE templates SET
                    name=?, template_type=?, subject=?, body_text=?, body_html=?,
                    variables=?, status=?, version=?, updated_at=?,
                    description=?, tags=?
                WHERE id=?
            ''', (
                template.name,
                template.template_type.value,
                template.subject,
                template.body_text,
                template.body_html,
                json.dumps(template.variables),
                template.status.value,
                template.version,
                template.updated_at.isoformat(),
                template.description,
                json.dumps(template.tags),
                template_id
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated template: {template_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update template: {e}")
            return False
    
    def delete_template(self, template_id: str) -> bool:
        """Delete template"""
        try:
            if template_id not in self.templates:
                raise ValueError(f"Template {template_id} not found")
            
            # Delete from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM templates WHERE id=?', (template_id,))
            cursor.execute('DELETE FROM template_usage WHERE template_id=?', (template_id,))
            
            conn.commit()
            conn.close()
            
            # Remove from memory
            del self.templates[template_id]
            
            logger.info(f"Deleted template: {template_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete template: {e}")
            return False
    
    def get_template(self, template_id: str) -> Optional[EmailTemplate]:
        """Get template by ID"""
        return self.templates.get(template_id)
    
    def list_templates(self, template_type: TemplateType = None, 
                      status: TemplateStatus = None, tags: List[str] = None) -> List[EmailTemplate]:
        """List templates with optional filtering"""
        templates = list(self.templates.values())
        
        if template_type:
            templates = [t for t in templates if t.template_type == template_type]
        
        if status:
            templates = [t for t in templates if t.status == status]
        
        if tags:
            templates = [t for t in templates if any(tag in t.tags for tag in tags)]
        
        return sorted(templates, key=lambda t: t.updated_at, reverse=True)
    
    def render_template(self, template_id: str, variables: Dict = None) -> TemplateRenderResult:
        """Render template with variables"""
        start_time = datetime.now()
        
        try:
            if template_id not in self.templates:
                return TemplateRenderResult(
                    success=False,
                    error_message=f"Template {template_id} not found",
                    render_time=0.0
                )
            
            template = self.templates[template_id]
            variables = variables or {}
            
            # Check for missing required variables
            missing_vars = [var for var in template.variables if var not in variables]
            
            # Render subject
            subject_template = self.jinja_env.from_string(template.subject)
            subject = subject_template.render(**variables)
            
            # Render text body
            text_template = self.jinja_env.from_string(template.body_text)
            body_text = text_template.render(**variables)
            
            # Render HTML body if available
            body_html = None
            if template.body_html:
                html_template = self.jinja_env.from_string(template.body_html)
                body_html = html_template.render(**variables)
            
            # Calculate render time
            render_time = (datetime.now() - start_time).total_seconds()
            
            # Update usage statistics
            self._record_template_usage(template_id, variables, render_time, True)
            
            # Update template usage count
            template.usage_count += 1
            template.last_used = datetime.now()
            
            self._update_template_usage_in_db(template)
            
            result = TemplateRenderResult(
                success=True,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                missing_variables=missing_vars,
                render_time=render_time
            )
            
            logger.info(f"Rendered template {template_id} successfully (time: {render_time:.3f}s)")
            return result
            
        except Exception as e:
            render_time = (datetime.now() - start_time).total_seconds()
            
            # Record failed usage
            self._record_template_usage(template_id, variables, render_time, False, str(e))
            
            logger.error(f"Failed to render template {template_id}: {e}")
            
            return TemplateRenderResult(
                success=False,
                error_message=str(e),
                render_time=render_time
            )
    
    def _record_template_usage(self, template_id: str, variables: Dict, 
                              render_time: float, success: bool, error_message: str = None):
        """Record template usage for analytics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO template_usage (
                    template_id, variables_used, render_time, success, error_message
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                template_id,
                json.dumps(variables),
                render_time,
                success,
                error_message
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.warning(f"Failed to record template usage: {e}")
    
    def _update_template_usage_in_db(self, template: EmailTemplate):
        """Update template usage count in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE templates SET usage_count=?, last_used=? WHERE id=?
            ''', (
                template.usage_count,
                template.last_used.isoformat() if template.last_used else None,
                template.id
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.warning(f"Failed to update template usage in database: {e}")
    
    def get_template_usage_stats(self, template_id: str, days: int = 30) -> Optional[TemplateUsageStats]:
        """Get template usage statistics"""
        try:
            if template_id not in self.templates:
                return None
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get total usage
            cursor.execute('SELECT COUNT(*) FROM template_usage WHERE template_id=?', (template_id,))
            total_uses = cursor.fetchone()[0]
            
            # Get recent usage
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            cursor.execute('''
                SELECT COUNT(*) FROM template_usage 
                WHERE template_id=? AND used_at >= ?
            ''', (template_id, since_date))
            recent_uses = cursor.fetchone()[0]
            
            # Get success rate
            cursor.execute('''
                SELECT 
                    COUNT(CASE WHEN success = 1 THEN 1 END) as successes,
                    COUNT(*) as total,
                    AVG(render_time) as avg_render_time
                FROM template_usage WHERE template_id=?
            ''', (template_id,))
            
            result = cursor.fetchone()
            success_rate = result[0] / result[1] if result[1] > 0 else 0
            avg_render_time = result[2] or 0
            
            # Get error count
            cursor.execute('''
                SELECT COUNT(*) FROM template_usage 
                WHERE template_id=? AND success = 0
            ''', (template_id,))
            error_count = cursor.fetchone()[0]
            
            # Get most recent usage
            cursor.execute('''
                SELECT used_at FROM template_usage 
                WHERE template_id=? ORDER BY used_at DESC LIMIT 1
            ''', (template_id,))
            
            last_used_result = cursor.fetchone()
            last_used = datetime.fromisoformat(last_used_result[0]) if last_used_result else None
            
            # Get most common variables
            cursor.execute('''
                SELECT variables_used FROM template_usage 
                WHERE template_id=? AND success = 1
            ''', (template_id,))
            
            variable_usage = {}
            for (vars_json,) in cursor.fetchall():
                if vars_json:
                    variables = json.loads(vars_json)
                    for var_name in variables.keys():
                        variable_usage[var_name] = variable_usage.get(var_name, 0) + 1
            
            conn.close()
            
            return TemplateUsageStats(
                template_id=template_id,
                total_uses=total_uses,
                last_30_days=recent_uses,
                success_rate=success_rate,
                avg_render_time=avg_render_time,
                most_common_variables=variable_usage,
                error_count=error_count,
                last_used=last_used
            )
            
        except Exception as e:
            logger.error(f"Failed to get template usage stats: {e}")
            return None
    
    def export_templates(self, output_path: str, template_ids: List[str] = None) -> bool:
        """Export templates to JSON file"""
        try:
            templates_to_export = []
            
            if template_ids:
                for template_id in template_ids:
                    if template_id in self.templates:
                        templates_to_export.append(self.templates[template_id].to_dict())
            else:
                templates_to_export = [template.to_dict() for template in self.templates.values()]
            
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'version': '1.0.0',
                'templates': templates_to_export
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported {len(templates_to_export)} templates to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export templates: {e}")
            return False
    
    def import_templates(self, input_path: str, overwrite: bool = False) -> int:
        """Import templates from JSON file"""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            templates_imported = 0
            templates_data = import_data.get('templates', [])
            
            for template_data in templates_data:
                template = EmailTemplate.from_dict(template_data)
                
                if template.id in self.templates and not overwrite:
                    logger.warning(f"Template {template.id} already exists, skipping")
                    continue
                
                if self.create_template(template):
                    templates_imported += 1
            
            logger.info(f"Imported {templates_imported} templates from {input_path}")
            return templates_imported
            
        except Exception as e:
            logger.error(f"Failed to import templates: {e}")
            return 0
    
    def create_default_templates(self):
        """Create default business email templates"""
        default_templates = [
            {
                'id': 'welcome_business',
                'name': 'Business Welcome Email',
                'template_type': TemplateType.WELCOME,
                'subject': 'Welcome to {{ company_name }}, {{ user_name }}!',
                'body_text': '''Hello {{ user_name }},

Welcome to {{ company_name }}! We're excited to have you on board.

Your account has been successfully created with the email address: {{ user_email }}

Next steps:
1. Complete your profile setup
2. Explore our features
3. Contact support if you need any help

Best regards,
The {{ company_name }} Team

{{ company_address }}''',
                'body_html': '''<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .header { background: #007bff; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; }
        .button { background: #007bff; color: white; padding: 12px 20px; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Welcome to {{ company_name }}!</h1>
    </div>
    <div class="content">
        <h2>Hello {{ user_name }},</h2>
        <p>We're excited to have you on board. Your account has been successfully created.</p>
        
        <h3>Account Details:</h3>
        <ul>
            <li>Email: {{ user_email }}</li>
            <li>Account Type: Business</li>
        </ul>
        
        <h3>Next Steps:</h3>
        <ol>
            <li>Complete your profile setup</li>
            <li>Explore our features</li>
            <li>Contact support if you need help</li>
        </ol>
        
        <p><a href="{{ dashboard_url }}" class="button">Go to Dashboard</a></p>
        
        <p>Best regards,<br>The {{ company_name }} Team</p>
        <p><small>{{ company_address }}</small></p>
    </div>
</body>
</html>''',
                'description': 'Professional welcome email for new business customers',
                'tags': ['onboarding', 'business'],
                'status': TemplateStatus.ACTIVE
            },
            {
                'id': 'email_verification',
                'name': 'Email Verification',
                'template_type': TemplateType.VERIFICATION,
                'subject': 'Verify your email address - {{ verification_code }}',
                'body_text': '''Please verify your email address by entering this verification code:

{{ verification_code }}

This code expires in {{ expiry_minutes }} minutes.

If you didn't request this verification, please ignore this email.

Thank you,
{{ company_name }} Security Team''',
                'body_html': '''<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .code { background: #f8f9fa; border: 2px solid #007bff; padding: 20px; text-align: center; font-size: 24px; font-weight: bold; margin: 20px 0; border-radius: 8px; }
        .warning { background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; }
    </style>
</head>
<body>
    <h2>Email Verification Required</h2>
    <p>Please verify your email address by entering this verification code:</p>
    
    <div class="code">{{ verification_code }}</div>
    
    <div class="warning">
        <strong>Important:</strong> This code expires in {{ expiry_minutes }} minutes.
    </div>
    
    <p>If you didn't request this verification, please ignore this email.</p>
    
    <p>Thank you,<br>{{ company_name }} Security Team</p>
</body>
</html>''',
                'description': 'Email verification code template',
                'tags': ['verification', 'security'],
                'status': TemplateStatus.ACTIVE
            },
            {
                'id': 'invoice_notification',
                'name': 'Invoice Notification',
                'template_type': TemplateType.INVOICE,
                'subject': 'Invoice {{ invoice_number }} - {{ company_name }}',
                'body_text': '''Dear {{ customer_name }},

Your invoice is ready for payment.

Invoice Details:
- Invoice Number: {{ invoice_number }}
- Amount Due: {{ amount_due }}
- Due Date: {{ due_date }}

You can view and pay your invoice online at: {{ payment_url }}

Thank you for your business!

{{ company_name }}
{{ company_contact }}''',
                'body_html': '''<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .invoice-details { background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; }
        .amount { font-size: 18px; font-weight: bold; color: #007bff; }
        .button { background: #28a745; color: white; padding: 12px 20px; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <h2>Invoice Ready for Payment</h2>
    <p>Dear {{ customer_name }},</p>
    
    <div class="invoice-details">
        <h3>Invoice Details</h3>
        <table>
            <tr><td><strong>Invoice Number:</strong></td><td>{{ invoice_number }}</td></tr>
            <tr><td><strong>Amount Due:</strong></td><td class="amount">{{ amount_due }}</td></tr>
            <tr><td><strong>Due Date:</strong></td><td>{{ due_date }}</td></tr>
        </table>
    </div>
    
    <p><a href="{{ payment_url }}" class="button">View & Pay Invoice</a></p>
    
    <p>Thank you for your business!</p>
    
    <p>{{ company_name }}<br>{{ company_contact }}</p>
</body>
</html>''',
                'description': 'Professional invoice notification template',
                'tags': ['billing', 'invoice'],
                'status': TemplateStatus.ACTIVE
            }
        ]
        
        created_count = 0
        for template_data in default_templates:
            template = EmailTemplate(**template_data)
            if self.create_template(template):
                created_count += 1
        
        logger.info(f"Created {created_count} default templates")
        return created_count

# Global template manager instance
_template_manager = None

def get_template_manager(config: Dict = None) -> EmailTemplateManager:
    """Get global template manager instance"""
    global _template_manager
    if _template_manager is None:
        _template_manager = EmailTemplateManager(config)
    return _template_manager

if __name__ == "__main__":
    def test_template_manager():
        """Test template manager functionality"""
        print("Testing Email Template Manager...")
        
        # Initialize manager
        manager = get_template_manager({'db_path': 'test_templates.db'})
        
        # Create default templates
        created = manager.create_default_templates()
        print(f"Created {created} default templates")
        
        # List templates
        templates = manager.list_templates()
        print(f"Total templates: {len(templates)}")
        
        # Test template rendering
        variables = {
            'user_name': 'John Doe',
            'user_email': 'john@example.com',
            'company_name': 'Acme Corp',
            'company_address': '123 Business St, City, State 12345',
            'dashboard_url': 'https://app.acme.com/dashboard'
        }
        
        result = manager.render_template('welcome_business', variables)
        
        if result.success:
            print("\nTemplate rendering successful:")
            print(f"Subject: {result.subject}")
            print(f"Render time: {result.render_time:.3f}s")
            if result.missing_variables:
                print(f"Missing variables: {result.missing_variables}")
        else:
            print(f"Template rendering failed: {result.error_message}")
        
        # Get usage stats
        stats = manager.get_template_usage_stats('welcome_business')
        if stats:
            print(f"\nUsage stats:")
            print(f"Total uses: {stats.total_uses}")
            print(f"Success rate: {stats.success_rate:.2%}")
            print(f"Avg render time: {stats.avg_render_time:.3f}s")
        
        # Export templates
        if manager.export_templates('exported_templates.json'):
            print("Templates exported successfully")
        
        print("Template manager test complete!")
    
    # Run test
    test_template_manager()