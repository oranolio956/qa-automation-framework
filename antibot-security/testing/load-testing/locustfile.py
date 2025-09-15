"""
Comprehensive Load Testing for Anti-Bot Security Framework
Simulates realistic user behavior and bot attacks for performance validation
"""

import json
import random
import time
import hashlib
from typing import Dict, List, Any
from locust import HttpUser, task, between, events
from locust.contrib.fasthttp import FastHttpUser
import numpy as np
import faker

fake = faker.Faker()

class BehavioralDataGenerator:
    """Generate realistic behavioral data for testing"""
    
    def __init__(self):
        self.session_id = self.generate_session_id()
        self.start_time = time.time() * 1000
        self.event_count = 0
        
    def generate_session_id(self) -> str:
        """Generate unique session ID"""
        timestamp = str(int(time.time() * 1000))
        random_part = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
        return f"{timestamp}-{random_part}"
    
    def generate_device_fingerprint(self) -> Dict[str, Any]:
        """Generate realistic device fingerprint"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ]
        
        languages = ["en-US", "en-GB", "fr-FR", "de-DE", "es-ES", "ja-JP", "zh-CN"]
        platforms = ["Win32", "MacIntel", "Linux x86_64", "iPhone", "Android"]
        
        fingerprint = {
            "hash": hashlib.sha256(f"{self.session_id}_{random.random()}".encode()).hexdigest(),
            "userAgent": random.choice(user_agents),
            "language": random.choice(languages),
            "platform": random.choice(platforms),
            "screen": {
                "width": random.choice([1920, 1366, 1536, 1440, 1280]),
                "height": random.choice([1080, 768, 864, 900, 720]),
                "colorDepth": random.choice([24, 32]),
                "pixelDepth": random.choice([24, 32])
            },
            "timezone": {
                "offset": random.choice([-480, -420, -360, -300, -240, -180, 0, 60, 120, 180, 240, 300, 480, 540]),
                "timezone": random.choice(["America/New_York", "Europe/London", "Asia/Tokyo", "Australia/Sydney"])
            },
            "webgl": {
                "vendor": "WebKit",
                "renderer": "WebKit WebGL",
                "version": "WebGL 1.0"
            } if random.random() > 0.1 else None,
            "canvas": {
                "hash": hashlib.sha256(f"canvas_{random.random()}".encode()).hexdigest()[:32]
            } if random.random() > 0.05 else None
        }
        
        return fingerprint
    
    def generate_human_mouse_events(self, duration_ms: float = 5000) -> List[Dict[str, Any]]:
        """Generate realistic human mouse movement events"""
        events = []
        current_time = self.start_time
        x, y = random.randint(100, 800), random.randint(100, 600)
        
        # Natural mouse movement pattern
        num_events = random.randint(20, 80)
        for i in range(num_events):
            if i > 0:
                # Natural movement with some randomness
                dx = random.gauss(0, 50)
                dy = random.gauss(0, 30)
                x = max(0, min(1920, x + dx))
                y = max(0, min(1080, y + dy))
                
                # Human-like timing variation
                time_delta = random.uniform(16, 100)  # 16-100ms between events
                current_time += time_delta
                
                # Calculate velocity (pixels per ms)
                velocity = np.sqrt(dx*dx + dy*dy) / time_delta if time_delta > 0 else 0
                
                event = {
                    "type": "mouse",
                    "subtype": "mousemove",
                    "timestamp": current_time,
                    "x": x,
                    "y": y,
                    "velocity": velocity,
                    "sessionId": self.session_id,
                    "pageUrl": "https://example.com/test",
                    "referrer": "https://google.com"
                }
                events.append(event)
        
        # Add some clicks
        for _ in range(random.randint(1, 5)):
            click_time = current_time + random.uniform(500, 2000)
            events.append({
                "type": "mouse",
                "subtype": "click",
                "timestamp": click_time,
                "x": x + random.randint(-50, 50),
                "y": y + random.randint(-30, 30),
                "button": 0,
                "sessionId": self.session_id,
                "pageUrl": "https://example.com/test",
                "referrer": "https://google.com"
            })
        
        return events
    
    def generate_bot_mouse_events(self) -> List[Dict[str, Any]]:
        """Generate bot-like mouse movement patterns"""
        events = []
        current_time = self.start_time
        
        # Bot patterns: either no movement or very regular movement
        if random.random() < 0.3:  # 30% chance of no mouse events
            return events
        
        # Regular, robotic movement
        x, y = 100, 100
        for i in range(random.randint(50, 200)):
            # Very regular movement pattern
            x += 10
            y += 5 if i % 10 == 0 else 0
            current_time += 16.67  # Exactly 60fps
            
            event = {
                "type": "mouse",
                "subtype": "mousemove",
                "timestamp": current_time,
                "x": x,
                "y": y,
                "velocity": 600,  # Unrealistically consistent speed
                "sessionId": self.session_id,
                "pageUrl": "https://example.com/test",
                "referrer": ""
            }
            events.append(event)
        
        return events
    
    def generate_human_keyboard_events(self) -> List[Dict[str, Any]]:
        """Generate realistic human typing patterns"""
        events = []
        current_time = self.start_time + 1000
        
        # Simulate typing a sentence
        text = fake.sentence()
        for i, char in enumerate(text[:20]):  # Limit for testing
            # Human-like typing rhythm with variation
            dwell_time = random.gauss(120, 40)  # Average 120ms with variation
            dwell_time = max(50, dwell_time)  # Minimum 50ms
            
            current_time += dwell_time
            
            events.append({
                "type": "keyboard",
                "subtype": "keydown",
                "timestamp": current_time,
                "key": char,
                "code": f"Key{char.upper()}" if char.isalpha() else "Space",
                "dwellTime": dwell_time,
                "sessionId": self.session_id,
                "pageUrl": "https://example.com/test"
            })
        
        return events
    
    def generate_bot_keyboard_events(self) -> List[Dict[str, Any]]:
        """Generate bot-like typing patterns"""
        events = []
        current_time = self.start_time + 500
        
        if random.random() < 0.4:  # 40% chance of no keyboard events
            return events
        
        # Very fast, regular typing
        text = "automated_input_string"
        for char in text:
            dwell_time = 20  # Unrealistically fast and consistent
            current_time += dwell_time
            
            events.append({
                "type": "keyboard",
                "subtype": "keydown",
                "timestamp": current_time,
                "key": char,
                "code": f"Key{char.upper()}" if char.isalpha() else "Underscore",
                "dwellTime": dwell_time,
                "sessionId": self.session_id,
                "pageUrl": "https://example.com/test"
            })
        
        return events
    
    def generate_scroll_events(self) -> List[Dict[str, Any]]:
        """Generate scroll behavior events"""
        events = []
        current_time = self.start_time + 2000
        
        scroll_y = 0
        for _ in range(random.randint(5, 20)):
            scroll_delta = random.randint(50, 200)
            scroll_y += scroll_delta
            current_time += random.uniform(200, 800)
            
            events.append({
                "type": "scroll",
                "timestamp": current_time,
                "scrollX": 0,
                "scrollY": scroll_y,
                "deltaY": scroll_delta,
                "scrollSpeed": scroll_delta / 100,
                "direction": "down",
                "sessionId": self.session_id,
                "pageUrl": "https://example.com/test"
            })
        
        return events

class HumanUser(FastHttpUser):
    """Simulate realistic human user behavior"""
    wait_time = between(1, 5)
    weight = 80  # 80% of traffic should be human-like
    
    def on_start(self):
        """Initialize user session"""
        self.generator = BehavioralDataGenerator()
        self.request_count = 0
    
    @task(3)
    def normal_browsing_session(self):
        """Simulate normal browsing with realistic behavioral data"""
        self.request_count += 1
        
        # Generate realistic behavioral data
        mouse_events = self.generator.generate_human_mouse_events()
        keyboard_events = self.generator.generate_human_keyboard_events()
        scroll_events = self.generator.generate_scroll_events()
        
        all_events = mouse_events + keyboard_events + scroll_events
        all_events.sort(key=lambda x: x['timestamp'])
        
        payload = {
            "sessionId": self.generator.session_id,
            "deviceFingerprint": self.generator.generate_device_fingerprint(),
            "tlsFingerprint": {
                "supportedProtocols": ["TLS 1.2", "TLS 1.3"],
                "timestamp": time.time() * 1000
            },
            "events": all_events,
            "metadata": {
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "timestamp": time.time() * 1000,
                "sessionDuration": time.time() * 1000 - self.generator.start_time,
                "timeSinceLastActivity": random.uniform(100, 2000),
                "performanceMetrics": {
                    "eventCollectionTime": random.uniform(0.5, 2.0),
                    "dataTransmissionTime": random.uniform(10, 50),
                    "totalEvents": len(all_events)
                }
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-Session-ID": self.generator.session_id,
            "User-Agent": payload["metadata"]["userAgent"]
        }
        
        with self.client.post(
            "/api/v1/behavioral-data",
            json=payload,
            headers=headers,
            catch_response=True,
            name="human_behavior_analysis"
        ) as response:
            if response.status_code == 200:
                result = response.json()
                risk_score = result.get("riskScore", 1.0)
                
                # Log human sessions with high risk scores (potential false positives)
                if risk_score > 0.5:
                    print(f"High risk score {risk_score:.3f} for human user - potential false positive")
                
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")
    
    @task(1)
    def health_check(self):
        """Periodic health check"""
        with self.client.get("/api/v1/health", name="health_check") as response:
            if response.status_code != 200:
                response.failure(f"Health check failed: {response.status_code}")

class BotUser(FastHttpUser):
    """Simulate bot behavior patterns"""
    wait_time = between(0.1, 1)  # Much faster than humans
    weight = 20  # 20% of traffic should be bot-like
    
    def on_start(self):
        """Initialize bot session"""
        self.generator = BehavioralDataGenerator()
        self.request_count = 0
    
    @task(5)
    def automated_requests(self):
        """Simulate bot-like automated requests"""
        self.request_count += 1
        
        # Generate bot-like behavioral data
        mouse_events = self.generator.generate_bot_mouse_events()
        keyboard_events = self.generator.generate_bot_keyboard_events()
        
        all_events = mouse_events + keyboard_events
        all_events.sort(key=lambda x: x['timestamp'])
        
        # Bot characteristics
        bot_user_agents = [
            "curl/7.68.0",
            "python-requests/2.28.1",
            "Go-http-client/1.1",
            "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        ]
        
        payload = {
            "sessionId": self.generator.session_id,
            "deviceFingerprint": None if random.random() < 0.3 else self.generator.generate_device_fingerprint(),
            "events": all_events,
            "metadata": {
                "userAgent": random.choice(bot_user_agents),
                "timestamp": time.time() * 1000,
                "sessionDuration": random.uniform(1000, 5000),  # Very short sessions
                "performanceMetrics": {
                    "eventCollectionTime": 0,  # No collection time for bots
                    "dataTransmissionTime": random.uniform(1, 5),
                    "totalEvents": len(all_events)
                }
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-Session-ID": self.generator.session_id,
            "User-Agent": payload["metadata"]["userAgent"]
        }
        
        with self.client.post(
            "/api/v1/behavioral-data",
            json=payload,
            headers=headers,
            catch_response=True,
            name="bot_behavior_analysis"
        ) as response:
            if response.status_code == 200:
                result = response.json()
                risk_score = result.get("riskScore", 0.0)
                
                # Log bots with low risk scores (potential false negatives)
                if risk_score < 0.7:
                    print(f"Low risk score {risk_score:.3f} for bot - potential false negative")
                
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")
    
    @task(2)
    def rapid_fire_requests(self):
        """Simulate rapid-fire bot requests"""
        for _ in range(random.randint(5, 15)):
            minimal_payload = {
                "sessionId": self.generator.session_id,
                "events": [],
                "metadata": {
                    "userAgent": "automated-scanner/1.0",
                    "timestamp": time.time() * 1000,
                    "performanceMetrics": {
                        "totalEvents": 0
                    }
                }
            }
            
            with self.client.post(
                "/api/v1/behavioral-data",
                json=minimal_payload,
                name="rapid_fire_bot",
                catch_response=True
            ) as response:
                if response.status_code == 429:  # Rate limited
                    response.success()  # This is expected behavior
                elif response.status_code == 200:
                    result = response.json()
                    if result.get("riskScore", 0) < 0.8:
                        response.failure("Bot not detected in rapid fire scenario")
                    else:
                        response.success()

class AttackUser(FastHttpUser):
    """Simulate coordinated attack patterns"""
    wait_time = between(0.01, 0.1)  # Very aggressive timing
    weight = 5  # Small percentage for attack simulation
    
    def on_start(self):
        """Initialize attack session"""
        self.generator = BehavioralDataGenerator()
        self.attack_ip = fake.ipv4()
    
    @task
    def coordinated_attack(self):
        """Simulate coordinated bot attack"""
        # Generate multiple rapid requests from "same IP"
        for _ in range(random.randint(10, 30)):
            attack_payload = {
                "sessionId": f"attack_{random.randint(1000, 9999)}",
                "events": [],
                "metadata": {
                    "userAgent": "AttackBot/1.0",
                    "timestamp": time.time() * 1000,
                    "sourceIP": self.attack_ip
                }
            }
            
            with self.client.post(
                "/api/v1/behavioral-data",
                json=attack_payload,
                name="coordinated_attack",
                catch_response=True
            ) as response:
                if response.status_code in [429, 403]:  # Rate limited or blocked
                    response.success()  # Expected
                    break
                elif response.status_code == 200:
                    result = response.json()
                    actions = result.get("actions", [])
                    if any(action.get("type") in ["block", "challenge"] for action in actions):
                        response.success()
                    else:
                        response.failure("Attack not properly detected")

# Event handlers for performance metrics
@events.request.add_listener
def my_request_handler(request_type, name, response_time, response_length, response, context, exception, start_time, url, **kwargs):
    """Custom request handler for detailed metrics"""
    if exception:
        print(f"Request failed: {name} - {exception}")
    elif response and hasattr(response, 'status_code'):
        if name == "human_behavior_analysis" and response_time > 100:
            print(f"Slow human request: {response_time}ms (SLA: <100ms)")
        elif name == "bot_behavior_analysis" and response_time > 100:
            print(f"Slow bot detection: {response_time}ms (SLA: <100ms)")

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize test metrics"""
    print("Starting Anti-Bot Security Load Test")
    print(f"Target: {environment.host}")
    print("Test scenarios:")
    print("- 80% Human-like behavior (should get low risk scores)")
    print("- 20% Bot-like behavior (should get high risk scores)")
    print("- 5% Attack patterns (should be blocked/challenged)")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Final test results"""
    print("\nLoad Test Complete")
    print("Review metrics for:")
    print("- Response times <100ms")
    print("- Accurate bot detection")
    print("- Proper rate limiting")
    print("- System stability under load")