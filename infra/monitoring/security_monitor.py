"""
Comprehensive Security Event Detection and Monitoring System
Real-time bot detection, threat intelligence integration, and automated incident response
"""

import asyncio
import json
import logging
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
import pandas as pd
import redis.asyncio as redis
from elasticsearch import AsyncElasticsearch
import aiohttp
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, push_to_gateway
from collections import defaultdict, deque
import uuid
import asyncio
from contextlib import asynccontextmanager
import signal
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ThreatLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class EventType(Enum):
    BOT_DETECTION = "bot_detection"
    ANOMALY_DETECTED = "anomaly_detected"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    THREAT_INTELLIGENCE_MATCH = "threat_intelligence_match"
    AUTOMATED_ATTACK = "automated_attack"
    FRAUD_ATTEMPT = "fraud_attempt"
    DATA_EXFILTRATION = "data_exfiltration"

@dataclass
class SecurityEvent:
    """Security event data structure"""
    id: str
    event_type: EventType
    threat_level: ThreatLevel
    timestamp: datetime
    source_ip: str
    user_agent: Optional[str]
    session_id: Optional[str]
    risk_score: float
    confidence: float
    details: Dict[str, Any]
    raw_data: Dict[str, Any]
    indicators: List[str]
    mitigation_actions: List[str]
    
class ThreatIntelligence:
    """Threat intelligence integration and management"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.threat_feeds = {
            'malicious_ips': set(),
            'known_bots': set(),
            'suspicious_user_agents': set(),
            'tor_exit_nodes': set(),
            'vpn_providers': set(),
            'datacenter_ranges': set()
        }
        self.last_update = {}
        
    async def initialize(self):
        """Initialize threat intelligence feeds"""
        try:
            # Load cached threat intelligence
            await self._load_cached_feeds()
            
            # Schedule periodic updates
            asyncio.create_task(self._update_feeds_periodically())
            
            logger.info("Threat intelligence initialized")
        except Exception as e:
            logger.error(f"Failed to initialize threat intelligence: {e}")
    
    async def _load_cached_feeds(self):
        """Load cached threat intelligence from Redis"""
        try:
            for feed_name in self.threat_feeds.keys():
                cached_data = await self.redis_client.smembers(f"threat_intel:{feed_name}")
                if cached_data:
                    self.threat_feeds[feed_name] = set(cached_data)
                    logger.info(f"Loaded {len(cached_data)} entries for {feed_name}")
        except Exception as e:
            logger.warning(f"Failed to load cached feeds: {e}")
    
    async def _update_feeds_periodically(self):
        """Periodically update threat intelligence feeds"""
        while True:
            try:
                await asyncio.sleep(3600)  # Update every hour
                await self._update_all_feeds()
            except Exception as e:
                logger.error(f"Feed update error: {e}")
                await asyncio.sleep(300)  # Retry in 5 minutes on error
    
    async def _update_all_feeds(self):
        """Update all threat intelligence feeds"""
        # Update malicious IPs from threat feeds
        await self._update_malicious_ips()
        
        # Update known bot signatures
        await self._update_bot_signatures()
        
        # Update Tor exit nodes
        await self._update_tor_nodes()
        
        # Update datacenter IP ranges
        await self._update_datacenter_ranges()
    
    async def _update_malicious_ips(self):
        """Update malicious IP addresses from threat feeds"""
        try:
            # Example sources - replace with actual threat intel APIs
            sources = [
                'https://feodotracker.abuse.ch/downloads/ipblocklist.txt',
                'https://reputation.alienvault.com/reputation.data'
            ]
            
            new_ips = set()
            async with aiohttp.ClientSession() as session:
                for source in sources:
                    try:
                        async with session.get(source, timeout=30) as response:
                            if response.status == 200:
                                content = await response.text()
                                # Parse IP addresses (implementation depends on format)
                                ips = self._parse_ip_list(content)
                                new_ips.update(ips)
                    except Exception as e:
                        logger.warning(f"Failed to fetch from {source}: {e}")
            
            if new_ips:
                self.threat_feeds['malicious_ips'].update(new_ips)
                # Cache in Redis
                await self.redis_client.delete('threat_intel:malicious_ips')
                if new_ips:
                    await self.redis_client.sadd('threat_intel:malicious_ips', *new_ips)
                    await self.redis_client.expire('threat_intel:malicious_ips', 86400)
                
                logger.info(f"Updated {len(new_ips)} malicious IPs")
                
        except Exception as e:
            logger.error(f"Failed to update malicious IPs: {e}")
    
    async def _update_bot_signatures(self):
        """Update known bot user agent signatures"""
        try:
            # Common bot signatures
            bot_signatures = [
                'bot', 'crawler', 'spider', 'scraper', 'automation',
                'selenium', 'phantomjs', 'headless', 'python-requests',
                'curl', 'wget', 'postman', 'insomnia'
            ]
            
            self.threat_feeds['known_bots'].update(bot_signatures)
            await self.redis_client.delete('threat_intel:known_bots')
            await self.redis_client.sadd('threat_intel:known_bots', *bot_signatures)
            await self.redis_client.expire('threat_intel:known_bots', 86400)
            
            logger.info(f"Updated {len(bot_signatures)} bot signatures")
            
        except Exception as e:
            logger.error(f"Failed to update bot signatures: {e}")
    
    async def _update_tor_nodes(self):
        """Update Tor exit node list"""
        try:
            url = 'https://check.torproject.org/torbulkexitlist'
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        content = await response.text()
                        tor_nodes = set(content.strip().split('\n'))
                        
                        self.threat_feeds['tor_exit_nodes'] = tor_nodes
                        await self.redis_client.delete('threat_intel:tor_exit_nodes')
                        if tor_nodes:
                            await self.redis_client.sadd('threat_intel:tor_exit_nodes', *tor_nodes)
                            await self.redis_client.expire('threat_intel:tor_exit_nodes', 86400)
                        
                        logger.info(f"Updated {len(tor_nodes)} Tor exit nodes")
                        
        except Exception as e:
            logger.error(f"Failed to update Tor nodes: {e}")
    
    async def _update_datacenter_ranges(self):
        """Update datacenter IP ranges"""
        try:
            # Common datacenter providers and cloud services
            datacenter_providers = [
                'amazonaws.com', 'googleusercontent.com', 'microsoftonline.com',
                'digitalocean.com', 'linode.com', 'vultr.com', 'ovh.net'
            ]
            
            self.threat_feeds['datacenter_ranges'].update(datacenter_providers)
            await self.redis_client.delete('threat_intel:datacenter_ranges')
            await self.redis_client.sadd('threat_intel:datacenter_ranges', *datacenter_providers)
            await self.redis_client.expire('threat_intel:datacenter_ranges', 86400)
            
            logger.info(f"Updated datacenter provider list")
            
        except Exception as e:
            logger.error(f"Failed to update datacenter ranges: {e}")
    
    def _parse_ip_list(self, content: str) -> List[str]:
        """Parse IP addresses from threat feed content"""
        import re
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        return re.findall(ip_pattern, content)
    
    async def check_threat_indicators(self, ip: str, user_agent: str = None) -> Tuple[bool, List[str]]:
        """Check if IP or user agent matches threat indicators"""
        indicators = []
        
        # Check malicious IPs
        if ip in self.threat_feeds['malicious_ips']:
            indicators.append(f"Malicious IP: {ip}")
        
        # Check Tor exit nodes
        if ip in self.threat_feeds['tor_exit_nodes']:
            indicators.append(f"Tor exit node: {ip}")
        
        # Check user agent for bot signatures
        if user_agent:
            user_agent_lower = user_agent.lower()
            for bot_sig in self.threat_feeds['known_bots']:
                if bot_sig in user_agent_lower:
                    indicators.append(f"Bot signature detected: {bot_sig}")
                    break
        
        return len(indicators) > 0, indicators

class SecurityEventDetector:
    """Advanced security event detection using multiple techniques"""
    
    def __init__(self, redis_client: redis.Redis, elasticsearch_client: AsyncElasticsearch):
        self.redis_client = redis_client
        self.elasticsearch = elasticsearch_client
        self.threat_intel = ThreatIntelligence(redis_client)
        
        # Detection parameters
        self.rate_limit_thresholds = {
            'per_ip_per_minute': 60,
            'per_session_per_minute': 10,
            'per_endpoint_per_minute': 100
        }
        
        # Anomaly detection parameters
        self.anomaly_windows = {
            'short_term': deque(maxlen=1000),    # Last 1000 events
            'medium_term': deque(maxlen=10000),  # Last 10000 events
            'long_term': deque(maxlen=100000)    # Last 100000 events
        }
        
        # Pattern detection
        self.pattern_cache = defaultdict(lambda: defaultdict(int))
        self.suspicious_patterns = {
            'rapid_user_agent_changes': 5,
            'geolocation_jumping': 3,
            'consistent_timing_intervals': 0.95,
            'identical_request_sequences': 10
        }
        
        # Metrics
        self.metrics = {
            'events_detected': Counter('security_events_detected_total', 'Total security events detected', ['event_type', 'threat_level']),
            'threat_intel_matches': Counter('threat_intelligence_matches_total', 'Threat intelligence matches', ['indicator_type']),
            'false_positives': Counter('security_false_positives_total', 'False positive detections', ['event_type']),
            'processing_time': Histogram('security_event_processing_seconds', 'Security event processing time'),
            'active_threats': Gauge('security_active_threats', 'Currently active threat count', ['threat_level'])
        }
    
    async def initialize(self):
        """Initialize the security event detector"""
        try:
            await self.threat_intel.initialize()
            logger.info("Security event detector initialized")
        except Exception as e:
            logger.error(f"Failed to initialize security detector: {e}")
            raise
    
    async def analyze_request(self, request_data: Dict[str, Any]) -> Optional[SecurityEvent]:
        """Analyze a single request for security threats"""
        start_time = time.time()
        
        try:
            # Extract key information
            ip = request_data.get('source_ip', 'unknown')
            user_agent = request_data.get('user_agent', '')
            session_id = request_data.get('session_id', '')
            endpoint = request_data.get('endpoint', '')
            timestamp = datetime.fromisoformat(request_data.get('timestamp', datetime.now().isoformat()))
            risk_score = request_data.get('risk_score', 0.0)
            
            # Initialize detection results
            threat_indicators = []
            threat_level = ThreatLevel.LOW
            event_type = None
            confidence = 0.0
            
            # 1. Check threat intelligence
            is_threat, intel_indicators = await self.threat_intel.check_threat_indicators(ip, user_agent)
            if is_threat:
                threat_indicators.extend(intel_indicators)
                threat_level = ThreatLevel.HIGH
                event_type = EventType.THREAT_INTELLIGENCE_MATCH
                confidence = 0.9
                
                # Update metrics
                for indicator in intel_indicators:
                    indicator_type = indicator.split(':')[0]
                    self.metrics['threat_intel_matches'].labels(indicator_type=indicator_type).inc()
            
            # 2. Rate limiting check
            rate_violations = await self._check_rate_limits(ip, session_id, endpoint)
            if rate_violations:
                threat_indicators.extend(rate_violations)
                threat_level = max(threat_level, ThreatLevel.MEDIUM)
                event_type = event_type or EventType.RATE_LIMIT_EXCEEDED
                confidence = max(confidence, 0.7)
            
            # 3. Behavioral anomaly detection
            anomaly_score = await self._detect_behavioral_anomalies(request_data)
            if anomaly_score > 0.8:
                threat_indicators.append(f"Behavioral anomaly detected (score: {anomaly_score:.3f})")
                threat_level = max(threat_level, ThreatLevel.HIGH)
                event_type = event_type or EventType.ANOMALY_DETECTED
                confidence = max(confidence, anomaly_score)
            
            # 4. Pattern analysis
            suspicious_patterns = await self._analyze_request_patterns(ip, session_id, request_data)
            if suspicious_patterns:
                threat_indicators.extend(suspicious_patterns)
                threat_level = max(threat_level, ThreatLevel.MEDIUM)
                event_type = event_type or EventType.SUSPICIOUS_PATTERN
                confidence = max(confidence, 0.6)
            
            # 5. ML model predictions
            if risk_score > 0.8:
                threat_indicators.append(f"High ML risk score: {risk_score:.3f}")
                threat_level = max(threat_level, ThreatLevel.HIGH)
                event_type = event_type or EventType.BOT_DETECTION
                confidence = max(confidence, risk_score)
            elif risk_score > 0.6:
                threat_indicators.append(f"Medium ML risk score: {risk_score:.3f}")
                threat_level = max(threat_level, ThreatLevel.MEDIUM)
                event_type = event_type or EventType.BOT_DETECTION
                confidence = max(confidence, risk_score * 0.8)
            
            # Create security event if threats detected
            if threat_indicators:
                event = SecurityEvent(
                    id=str(uuid.uuid4()),
                    event_type=event_type,
                    threat_level=threat_level,
                    timestamp=timestamp,
                    source_ip=ip,
                    user_agent=user_agent,
                    session_id=session_id,
                    risk_score=risk_score,
                    confidence=confidence,
                    details={
                        'endpoint': endpoint,
                        'request_method': request_data.get('method', 'unknown'),
                        'response_code': request_data.get('response_code', 0),
                        'request_size': request_data.get('request_size', 0),
                        'response_size': request_data.get('response_size', 0),
                        'processing_time': request_data.get('processing_time', 0)
                    },
                    raw_data=request_data,
                    indicators=threat_indicators,
                    mitigation_actions=self._determine_mitigation_actions(threat_level, event_type)
                )
                
                # Update metrics
                self.metrics['events_detected'].labels(
                    event_type=event_type.value,
                    threat_level=threat_level.value
                ).inc()
                
                # Store event for analysis
                await self._store_security_event(event)
                
                processing_time = time.time() - start_time
                self.metrics['processing_time'].observe(processing_time)
                
                logger.warning(f"Security event detected: {event_type.value} - {threat_level.value} - IP: {ip}")
                return event
            
        except Exception as e:
            logger.error(f"Error analyzing request: {e}")
            
        return None
    
    async def _check_rate_limits(self, ip: str, session_id: str, endpoint: str) -> List[str]:
        """Check various rate limiting scenarios"""
        violations = []
        current_time = int(time.time())
        
        try:
            # Check IP rate limit
            ip_key = f"rate_limit:ip:{ip}:{current_time // 60}"
            ip_count = await self.redis_client.incr(ip_key)
            await self.redis_client.expire(ip_key, 60)
            
            if ip_count > self.rate_limit_thresholds['per_ip_per_minute']:
                violations.append(f"IP rate limit exceeded: {ip_count} requests/minute")
            
            # Check session rate limit
            if session_id:
                session_key = f"rate_limit:session:{session_id}:{current_time // 60}"
                session_count = await self.redis_client.incr(session_key)
                await self.redis_client.expire(session_key, 60)
                
                if session_count > self.rate_limit_thresholds['per_session_per_minute']:
                    violations.append(f"Session rate limit exceeded: {session_count} requests/minute")
            
            # Check endpoint rate limit
            endpoint_key = f"rate_limit:endpoint:{endpoint}:{current_time // 60}"
            endpoint_count = await self.redis_client.incr(endpoint_key)
            await self.redis_client.expire(endpoint_key, 60)
            
            if endpoint_count > self.rate_limit_thresholds['per_endpoint_per_minute']:
                violations.append(f"Endpoint rate limit exceeded: {endpoint_count} requests/minute")
                
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
        
        return violations
    
    async def _detect_behavioral_anomalies(self, request_data: Dict[str, Any]) -> float:
        """Detect behavioral anomalies using statistical methods"""
        try:
            # Extract features for anomaly detection
            features = {
                'request_size': request_data.get('request_size', 0),
                'processing_time': request_data.get('processing_time', 0),
                'hour_of_day': datetime.now().hour,
                'day_of_week': datetime.now().weekday(),
                'user_agent_length': len(request_data.get('user_agent', '')),
                'has_referer': 1 if request_data.get('referer') else 0
            }
            
            # Simple anomaly scoring (in practice, use more sophisticated methods)
            anomaly_score = 0.0
            
            # Check for unusual request sizes
            if features['request_size'] > 1000000:  # >1MB
                anomaly_score += 0.3
            
            # Check for unusual processing times
            if features['processing_time'] > 5000:  # >5 seconds
                anomaly_score += 0.2
            
            # Check for unusual timing patterns
            if features['hour_of_day'] < 6 or features['hour_of_day'] > 23:  # Night hours
                anomaly_score += 0.1
            
            # Check for missing typical headers
            if not request_data.get('referer') and not request_data.get('user_agent'):
                anomaly_score += 0.4
            
            return min(1.0, anomaly_score)
            
        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")
            return 0.0
    
    async def _analyze_request_patterns(self, ip: str, session_id: str, request_data: Dict[str, Any]) -> List[str]:
        """Analyze request patterns for suspicious behavior"""
        suspicious_patterns = []
        
        try:
            # Track user agent changes per IP
            user_agent = request_data.get('user_agent', '')
            ua_key = f"pattern:ua_changes:{ip}"
            
            if user_agent:
                await self.redis_client.sadd(ua_key, user_agent)
                await self.redis_client.expire(ua_key, 3600)  # 1 hour
                
                ua_count = await self.redis_client.scard(ua_key)
                if ua_count > self.suspicious_patterns['rapid_user_agent_changes']:
                    suspicious_patterns.append(f"Rapid user agent changes: {ua_count} different UAs")
            
            # Track request timing patterns
            if session_id:
                timing_key = f"pattern:timing:{session_id}"
                current_time = time.time()
                
                await self.redis_client.lpush(timing_key, str(current_time))
                await self.redis_client.ltrim(timing_key, 0, 99)  # Keep last 100
                await self.redis_client.expire(timing_key, 1800)  # 30 minutes
                
                # Analyze timing consistency
                timestamps = await self.redis_client.lrange(timing_key, 0, -1)
                if len(timestamps) >= 10:
                    intervals = []
                    for i in range(len(timestamps) - 1):
                        interval = float(timestamps[i]) - float(timestamps[i + 1])
                        intervals.append(interval)
                    
                    if intervals:
                        cv = np.std(intervals) / np.mean(intervals) if np.mean(intervals) > 0 else 0
                        consistency = 1 - cv
                        
                        if consistency > self.suspicious_patterns['consistent_timing_intervals']:
                            suspicious_patterns.append(f"Highly consistent request timing: {consistency:.3f}")
            
        except Exception as e:
            logger.error(f"Pattern analysis error: {e}")
        
        return suspicious_patterns
    
    def _determine_mitigation_actions(self, threat_level: ThreatLevel, event_type: EventType) -> List[str]:
        """Determine appropriate mitigation actions"""
        actions = []
        
        if threat_level == ThreatLevel.CRITICAL:
            actions.extend([
                "Block IP immediately",
                "Invalidate all sessions from IP",
                "Add IP to permanent blacklist",
                "Alert security team immediately",
                "Initiate incident response"
            ])
        elif threat_level == ThreatLevel.HIGH:
            actions.extend([
                "Rate limit IP aggressively",
                "Require additional verification",
                "Monitor all requests closely",
                "Alert security team",
                "Consider temporary IP block"
            ])
        elif threat_level == ThreatLevel.MEDIUM:
            actions.extend([
                "Increase monitoring",
                "Apply moderate rate limiting",
                "Log all activities",
                "Consider CAPTCHA challenge"
            ])
        else:  # LOW
            actions.extend([
                "Log for analysis",
                "Continue monitoring"
            ])
        
        # Event-specific actions
        if event_type == EventType.BOT_DETECTION:
            actions.append("Deploy anti-bot challenge")
        elif event_type == EventType.THREAT_INTELLIGENCE_MATCH:
            actions.append("Cross-reference with additional threat feeds")
        elif event_type == EventType.RATE_LIMIT_EXCEEDED:
            actions.append("Implement progressive rate limiting")
        
        return actions
    
    async def _store_security_event(self, event: SecurityEvent):
        """Store security event in Elasticsearch for analysis"""
        try:
            doc = {
                '@timestamp': event.timestamp.isoformat(),
                'event_id': event.id,
                'event_type': event.event_type.value,
                'threat_level': event.threat_level.value,
                'source_ip': event.source_ip,
                'user_agent': event.user_agent,
                'session_id': event.session_id,
                'risk_score': event.risk_score,
                'confidence': event.confidence,
                'details': event.details,
                'indicators': event.indicators,
                'mitigation_actions': event.mitigation_actions,
                'raw_data': event.raw_data
            }
            
            # Index in Elasticsearch with daily indices
            index_name = f"security-events-{event.timestamp.strftime('%Y.%m.%d')}"
            await self.elasticsearch.index(index=index_name, body=doc)
            
            # Also cache in Redis for quick access
            await self.redis_client.lpush(
                f"security_events:{event.threat_level.value}",
                json.dumps(asdict(event), default=str)
            )
            await self.redis_client.ltrim(f"security_events:{event.threat_level.value}", 0, 999)
            await self.redis_client.expire(f"security_events:{event.threat_level.value}", 86400)
            
        except Exception as e:
            logger.error(f"Failed to store security event: {e}")

class SecurityMonitorService:
    """Main security monitoring service orchestrator"""
    
    def __init__(self):
        self.redis_client = None
        self.elasticsearch_client = None
        self.event_detector = None
        self.running = False
        self.tasks = []
    
    async def initialize(self):
        """Initialize the monitoring service"""
        try:
            # Initialize connections
            self.redis_client = await redis.from_url(
                "redis://redis:6379", 
                decode_responses=True
            )
            
            self.elasticsearch_client = AsyncElasticsearch([
                {'host': 'elasticsearch', 'port': 9200}
            ])
            
            # Initialize event detector
            self.event_detector = SecurityEventDetector(
                self.redis_client, 
                self.elasticsearch_client
            )
            await self.event_detector.initialize()
            
            logger.info("Security monitoring service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize monitoring service: {e}")
            raise
    
    async def start_monitoring(self):
        """Start the monitoring process"""
        try:
            self.running = True
            
            # Start event processing task
            self.tasks.append(asyncio.create_task(self._process_events_loop()))
            
            # Start metrics reporting task
            self.tasks.append(asyncio.create_task(self._report_metrics_loop()))
            
            # Start housekeeping task
            self.tasks.append(asyncio.create_task(self._housekeeping_loop()))
            
            logger.info("Security monitoring started")
            
            # Wait for tasks
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
        finally:
            await self.shutdown()
    
    async def _process_events_loop(self):
        """Main event processing loop"""
        while self.running:
            try:
                # Process incoming requests from Redis streams
                streams = await self.redis_client.xread(
                    {'security_events_stream': '$'},
                    count=10,
                    block=1000
                )
                
                for stream_name, messages in streams:
                    for message_id, fields in messages:
                        try:
                            request_data = json.loads(fields.get('data', '{}'))
                            
                            # Analyze request for security threats
                            security_event = await self.event_detector.analyze_request(request_data)
                            
                            if security_event:
                                # Handle the security event
                                await self._handle_security_event(security_event)
                            
                            # Acknowledge message processing
                            await self.redis_client.xack('security_events_stream', 'security_monitor_group', message_id)
                            
                        except Exception as e:
                            logger.error(f"Error processing message {message_id}: {e}")
                
            except Exception as e:
                logger.error(f"Event processing loop error: {e}")
                await asyncio.sleep(5)
    
    async def _handle_security_event(self, event: SecurityEvent):
        """Handle detected security event"""
        try:
            logger.warning(f"Handling security event: {event.event_type.value} - {event.threat_level.value}")
            
            # Execute mitigation actions
            for action in event.mitigation_actions:
                await self._execute_mitigation_action(action, event)
            
            # Send alerts based on threat level
            if event.threat_level in [ThreatLevel.CRITICAL, ThreatLevel.HIGH]:
                await self._send_security_alert(event)
            
            # Update threat counters
            threat_key = f"active_threats:{event.threat_level.value}"
            await self.redis_client.incr(threat_key)
            await self.redis_client.expire(threat_key, 3600)  # 1 hour
            
        except Exception as e:
            logger.error(f"Error handling security event: {e}")
    
    async def _execute_mitigation_action(self, action: str, event: SecurityEvent):
        """Execute specific mitigation action"""
        try:
            if "Block IP" in action:
                await self._block_ip(event.source_ip)
            elif "Rate limit" in action:
                await self._apply_rate_limit(event.source_ip)
            elif "Alert" in action:
                await self._send_alert(event)
            elif "Log" in action:
                logger.info(f"Mitigation logged: {action} for event {event.id}")
            
        except Exception as e:
            logger.error(f"Error executing mitigation action '{action}': {e}")
    
    async def _block_ip(self, ip: str):
        """Block an IP address"""
        try:
            await self.redis_client.sadd('blocked_ips', ip)
            await self.redis_client.expire('blocked_ips', 86400)  # 24 hours
            logger.warning(f"IP blocked: {ip}")
        except Exception as e:
            logger.error(f"Failed to block IP {ip}: {e}")
    
    async def _apply_rate_limit(self, ip: str):
        """Apply aggressive rate limiting to an IP"""
        try:
            await self.redis_client.setex(f'rate_limited:{ip}', 3600, '1')  # 1 hour
            logger.info(f"Rate limit applied to IP: {ip}")
        except Exception as e:
            logger.error(f"Failed to apply rate limit to IP {ip}: {e}")
    
    async def _send_security_alert(self, event: SecurityEvent):
        """Send security alert through configured channels"""
        try:
            alert_payload = {
                'event_id': event.id,
                'event_type': event.event_type.value,
                'threat_level': event.threat_level.value,
                'source_ip': event.source_ip,
                'timestamp': event.timestamp.isoformat(),
                'confidence': event.confidence,
                'indicators': event.indicators,
                'mitigation_actions': event.mitigation_actions
            }
            
            # Send to alert webhook
            webhook_url = os.getenv('ALERT_WEBHOOK_URL')
            if webhook_url:
                async with aiohttp.ClientSession() as session:
                    await session.post(webhook_url, json=alert_payload)
            
            # Send to Slack
            slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
            if slack_webhook:
                slack_payload = {
                    'text': f"🚨 Security Alert: {event.event_type.value}",
                    'attachments': [{
                        'color': 'danger' if event.threat_level == ThreatLevel.CRITICAL else 'warning',
                        'fields': [
                            {'title': 'Threat Level', 'value': event.threat_level.value.upper(), 'short': True},
                            {'title': 'Source IP', 'value': event.source_ip, 'short': True},
                            {'title': 'Confidence', 'value': f"{event.confidence:.2f}", 'short': True},
                            {'title': 'Indicators', 'value': '\n'.join(event.indicators[:5]), 'short': False}
                        ]
                    }]
                }
                
                async with aiohttp.ClientSession() as session:
                    await session.post(slack_webhook, json=slack_payload)
            
        except Exception as e:
            logger.error(f"Failed to send security alert: {e}")
    
    async def _send_alert(self, event: SecurityEvent):
        """Send general alert"""
        await self._send_security_alert(event)
    
    async def _report_metrics_loop(self):
        """Report metrics to Prometheus pushgateway"""
        while self.running:
            try:
                await asyncio.sleep(30)  # Report every 30 seconds
                
                # Push metrics to Prometheus
                gateway = os.getenv('PROMETHEUS_PUSHGATEWAY_URL', 'prometheus:9091')
                registry = CollectorRegistry()
                
                # Add current metrics to registry
                for metric in self.event_detector.metrics.values():
                    registry.register(metric)
                
                # Push to gateway
                push_to_gateway(gateway, job='security-monitor', registry=registry)
                
            except Exception as e:
                logger.error(f"Metrics reporting error: {e}")
                await asyncio.sleep(60)
    
    async def _housekeeping_loop(self):
        """Periodic housekeeping tasks"""
        while self.running:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                # Clean up old events
                await self._cleanup_old_events()
                
                # Update threat counters
                await self._update_threat_metrics()
                
            except Exception as e:
                logger.error(f"Housekeeping error: {e}")
    
    async def _cleanup_old_events(self):
        """Clean up old events and data"""
        try:
            # Clean up old rate limit keys
            pattern = "rate_limit:*"
            keys = await self.redis_client.keys(pattern)
            if keys:
                expired_keys = []
                for key in keys:
                    ttl = await self.redis_client.ttl(key)
                    if ttl == -1:  # No expiry set
                        expired_keys.append(key)
                
                if expired_keys:
                    await self.redis_client.delete(*expired_keys)
                    logger.info(f"Cleaned up {len(expired_keys)} expired rate limit keys")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    async def _update_threat_metrics(self):
        """Update threat level metrics"""
        try:
            for threat_level in ThreatLevel:
                threat_key = f"active_threats:{threat_level.value}"
                count = await self.redis_client.get(threat_key) or 0
                self.event_detector.metrics['active_threats'].labels(
                    threat_level=threat_level.value
                ).set(int(count))
                
        except Exception as e:
            logger.error(f"Threat metrics update error: {e}")
    
    async def shutdown(self):
        """Shutdown the monitoring service"""
        logger.info("Shutting down security monitoring service")
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Close connections
        if self.redis_client:
            await self.redis_client.close()
        
        if self.elasticsearch_client:
            await self.elasticsearch_client.close()

# Import required modules
import os

async def main():
    """Main entry point"""
    service = SecurityMonitorService()
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        asyncio.create_task(service.shutdown())
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        await service.initialize()
        await service.start_monitoring()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Service error: {e}")
    finally:
        await service.shutdown()

if __name__ == "__main__":
    asyncio.run(main())