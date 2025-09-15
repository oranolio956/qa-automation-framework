#!/usr/bin/env python3
"""
CAPTCHA Solving Integration
Production-ready CAPTCHA solving with multiple providers and queue management
"""

import os
import time
import random
import logging
import requests
import json
import asyncio
import base64
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import io
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CaptchaType(Enum):
    IMAGE = "image"
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    FUNCAPTCHA = "funcaptcha"
    TEXT = "text"
    GEETEST = "geetest"

class CaptchaProvider(Enum):
    TWOCAPTCHA = "2captcha"
    ANTICAPTCHA = "anticaptcha"
    CAPMONSTER = "capmonster"
    DEATHBYCAPTCHA = "deathbycaptcha"

@dataclass
class CaptchaTask:
    """CAPTCHA solving task"""
    task_id: str
    captcha_type: CaptchaType
    provider: CaptchaProvider
    image_data: Optional[str] = None  # Base64 encoded image
    site_key: Optional[str] = None  # For reCAPTCHA/hCAPTCHA
    page_url: Optional[str] = None  # Site URL for reCAPTCHA
    additional_data: Optional[Dict] = None
    created_at: datetime = None
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    solution: Optional[str] = None
    status: str = "pending"  # pending, processing, solved, failed
    cost: float = 0.0
    attempts: int = 0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.additional_data is None:
            self.additional_data = {}

class CaptchaSolverInterface:
    """Base interface for CAPTCHA solving services"""
    
    def __init__(self, api_key: str, config: Dict = None):
        self.api_key = api_key
        self.config = config or {}
        self.session = requests.Session()
        self.rate_limits = {'last_request': 0, 'min_interval': 3}  # 3 second minimum interval
        
    def _wait_for_rate_limit(self):
        """Respect rate limiting"""
        now = time.time()
        time_since_last = now - self.rate_limits['last_request']
        
        if time_since_last < self.rate_limits['min_interval']:
            sleep_time = self.rate_limits['min_interval'] - time_since_last
            time.sleep(sleep_time)
        
        self.rate_limits['last_request'] = time.time()
    
    async def submit_captcha(self, task: CaptchaTask) -> str:
        """Submit CAPTCHA for solving - returns task ID"""
        # Base implementation - should be overridden by specific providers
        import uuid
        provider_task_id = str(uuid.uuid4())
        
        task.submitted_at = datetime.now()
        task.status = "processing"
        
        logger.warning(f"Submit CAPTCHA not implemented for provider: {self.__class__.__name__}")
        
        # Return a fake task ID for base implementation
        return provider_task_id
    
    async def get_result(self, task_id: str, provider_task_id: str) -> Tuple[str, Optional[str]]:
        """Get CAPTCHA result - returns (status, solution)"""
        # Base implementation - should be overridden by specific providers
        logger.warning(f"Get result not implemented for provider: {self.__class__.__name__}")
        
        # Return failed status for base implementation
        return "failed", None
    
    async def report_good(self, provider_task_id: str) -> bool:
        """Report correct solution"""
        return True  # Default implementation
    
    async def report_bad(self, provider_task_id: str) -> bool:
        """Report incorrect solution"""  
        return True  # Default implementation
    
    def get_balance(self) -> float:
        """Get account balance"""
        # Base implementation - should be overridden by specific providers
        logger.warning(f"Get balance not implemented for provider: {self.__class__.__name__}")
        return 0.0

class TwoCaptchaProvider(CaptchaSolverInterface):
    """2captcha.com API integration"""
    
    BASE_URL = "http://2captcha.com"
    
    def __init__(self, api_key: str, config: Dict = None):
        super().__init__(api_key, config)
        self.session.timeout = 30
    
    async def submit_captcha(self, task: CaptchaTask) -> str:
        """Submit CAPTCHA to 2captcha"""
        try:
            self._wait_for_rate_limit()
            
            data = {
                'key': self.api_key,
                'method': self._get_method(task.captcha_type),
                'soft_id': self.config.get('soft_id', 4582),  # API partner ID
            }
            
            if task.captcha_type == CaptchaType.IMAGE:
                if not task.image_data:
                    raise ValueError("Image data required for image CAPTCHA")
                data['body'] = task.image_data
                
            elif task.captcha_type in [CaptchaType.RECAPTCHA_V2, CaptchaType.RECAPTCHA_V3]:
                if not task.site_key or not task.page_url:
                    raise ValueError("Site key and page URL required for reCAPTCHA")
                data.update({
                    'googlekey': task.site_key,
                    'pageurl': task.page_url
                })
                if task.captcha_type == CaptchaType.RECAPTCHA_V3:
                    data['version'] = 'v3'
                    data['min_score'] = task.additional_data.get('min_score', 0.3)
                    data['action'] = task.additional_data.get('action', 'submit')
                    
            elif task.captcha_type == CaptchaType.HCAPTCHA:
                if not task.site_key or not task.page_url:
                    raise ValueError("Site key and page URL required for hCAPTCHA")
                data.update({
                    'sitekey': task.site_key,
                    'pageurl': task.page_url
                })
            
            # Submit task
            response = self.session.post(f"{self.BASE_URL}/in.php", data=data)
            response.raise_for_status()
            
            result = response.text
            if result.startswith('OK|'):
                provider_task_id = result.split('|')[1]
                task.submitted_at = datetime.now()
                task.status = "processing"
                logger.info(f"Submitted CAPTCHA to 2captcha: {provider_task_id}")
                return provider_task_id
            else:
                raise Exception(f"2captcha submission failed: {result}")
                
        except Exception as e:
            logger.error(f"Failed to submit CAPTCHA to 2captcha: {e}")
            raise
    
    async def get_result(self, task_id: str, provider_task_id: str) -> Tuple[str, Optional[str]]:
        """Get result from 2captcha"""
        try:
            self._wait_for_rate_limit()
            
            params = {
                'key': self.api_key,
                'action': 'get',
                'id': provider_task_id
            }
            
            response = self.session.get(f"{self.BASE_URL}/res.php", params=params)
            response.raise_for_status()
            
            result = response.text
            
            if result == 'CAPCHA_NOT_READY':
                return "processing", None
            elif result.startswith('OK|'):
                solution = result.split('|', 1)[1]
                return "solved", solution
            else:
                logger.error(f"2captcha result error: {result}")
                return "failed", None
                
        except Exception as e:
            logger.error(f"Failed to get result from 2captcha: {e}")
            return "failed", None
    
    def _get_method(self, captcha_type: CaptchaType) -> str:
        """Get API method for CAPTCHA type"""
        mapping = {
            CaptchaType.IMAGE: 'base64',
            CaptchaType.RECAPTCHA_V2: 'userrecaptcha',
            CaptchaType.RECAPTCHA_V3: 'userrecaptcha',
            CaptchaType.HCAPTCHA: 'hcaptcha',
            CaptchaType.FUNCAPTCHA: 'funcaptcha',
            CaptchaType.GEETEST: 'geetest'
        }
        return mapping.get(captcha_type, 'base64')
    
    def get_balance(self) -> float:
        """Get 2captcha account balance"""
        try:
            params = {
                'key': self.api_key,
                'action': 'getbalance'
            }
            
            response = self.session.get(f"{self.BASE_URL}/res.php", params=params)
            response.raise_for_status()
            
            return float(response.text)
            
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return 0.0

class AntiCaptchaProvider(CaptchaSolverInterface):
    """Anti-Captcha.com API integration"""
    
    BASE_URL = "https://api.anti-captcha.com"
    
    async def submit_captcha(self, task: CaptchaTask) -> str:
        """Submit CAPTCHA to Anti-Captcha"""
        try:
            self._wait_for_rate_limit()
            
            # Build task object based on CAPTCHA type
            task_obj = self._build_task_object(task)
            
            data = {
                'clientKey': self.api_key,
                'task': task_obj,
                'softId': self.config.get('soft_id', 867)  # API partner ID
            }
            
            response = self.session.post(f"{self.BASE_URL}/createTask", json=data)
            response.raise_for_status()
            
            result = response.json()
            if result.get('errorId') == 0:
                provider_task_id = str(result['taskId'])
                task.submitted_at = datetime.now()
                task.status = "processing"
                logger.info(f"Submitted CAPTCHA to Anti-Captcha: {provider_task_id}")
                return provider_task_id
            else:
                raise Exception(f"Anti-Captcha submission failed: {result.get('errorDescription')}")
                
        except Exception as e:
            logger.error(f"Failed to submit CAPTCHA to Anti-Captcha: {e}")
            raise
    
    async def get_result(self, task_id: str, provider_task_id: str) -> Tuple[str, Optional[str]]:
        """Get result from Anti-Captcha"""
        try:
            self._wait_for_rate_limit()
            
            data = {
                'clientKey': self.api_key,
                'taskId': int(provider_task_id)
            }
            
            response = self.session.post(f"{self.BASE_URL}/getTaskResult", json=data)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('errorId') != 0:
                logger.error(f"Anti-Captcha result error: {result.get('errorDescription')}")
                return "failed", None
            
            if result.get('status') == 'processing':
                return "processing", None
            elif result.get('status') == 'ready':
                solution_data = result.get('solution', {})
                # Extract solution based on CAPTCHA type
                if 'gRecaptchaResponse' in solution_data:
                    solution = solution_data['gRecaptchaResponse']
                elif 'text' in solution_data:
                    solution = solution_data['text']
                elif 'token' in solution_data:
                    solution = solution_data['token']
                else:
                    solution = str(solution_data)
                
                return "solved", solution
            else:
                return "failed", None
                
        except Exception as e:
            logger.error(f"Failed to get result from Anti-Captcha: {e}")
            return "failed", None
    
    def _build_task_object(self, task: CaptchaTask) -> Dict:
        """Build Anti-Captcha task object"""
        if task.captcha_type == CaptchaType.IMAGE:
            return {
                'type': 'ImageToTextTask',
                'body': task.image_data,
                'phrase': task.additional_data.get('phrase', False),
                'case': task.additional_data.get('case', False),
                'numeric': task.additional_data.get('numeric', 0),
                'math': task.additional_data.get('math', False),
                'minLength': task.additional_data.get('min_length', 0),
                'maxLength': task.additional_data.get('max_length', 0)
            }
        elif task.captcha_type == CaptchaType.RECAPTCHA_V2:
            return {
                'type': 'NoCaptchaTaskProxyless',
                'websiteURL': task.page_url,
                'websiteKey': task.site_key
            }
        elif task.captcha_type == CaptchaType.RECAPTCHA_V3:
            return {
                'type': 'RecaptchaV3TaskProxyless',
                'websiteURL': task.page_url,
                'websiteKey': task.site_key,
                'minScore': task.additional_data.get('min_score', 0.3),
                'pageAction': task.additional_data.get('action', 'submit')
            }
        elif task.captcha_type == CaptchaType.HCAPTCHA:
            return {
                'type': 'HCaptchaTaskProxyless',
                'websiteURL': task.page_url,
                'websiteKey': task.site_key
            }
        else:
            raise ValueError(f"Unsupported CAPTCHA type: {task.captcha_type}")

class CapMonsterProvider(CaptchaSolverInterface):
    """CapMonster Cloud API integration"""
    
    BASE_URL = "https://api.capmonster.cloud"
    
    async def submit_captcha(self, task: CaptchaTask) -> str:
        """Submit CAPTCHA to CapMonster"""
        try:
            self._wait_for_rate_limit()
            
            task_obj = self._build_task_object(task)
            
            data = {
                'clientKey': self.api_key,
                'task': task_obj,
                'softId': self.config.get('soft_id', 74)
            }
            
            response = self.session.post(f"{self.BASE_URL}/createTask", json=data)
            response.raise_for_status()
            
            result = response.json()
            if result.get('errorId') == 0:
                provider_task_id = str(result['taskId'])
                task.submitted_at = datetime.now()
                task.status = "processing"
                logger.info(f"Submitted CAPTCHA to CapMonster: {provider_task_id}")
                return provider_task_id
            else:
                raise Exception(f"CapMonster submission failed: {result.get('errorDescription')}")
                
        except Exception as e:
            logger.error(f"Failed to submit CAPTCHA to CapMonster: {e}")
            raise
    
    async def get_result(self, task_id: str, provider_task_id: str) -> Tuple[str, Optional[str]]:
        """Get result from CapMonster"""
        try:
            self._wait_for_rate_limit()
            
            data = {
                'clientKey': self.api_key,
                'taskId': int(provider_task_id)
            }
            
            response = self.session.post(f"{self.BASE_URL}/getTaskResult", json=data)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('errorId') != 0:
                logger.error(f"CapMonster result error: {result.get('errorDescription')}")
                return "failed", None
            
            if result.get('status') == 'processing':
                return "processing", None
            elif result.get('status') == 'ready':
                solution_data = result.get('solution', {})
                solution = solution_data.get('gRecaptchaResponse') or solution_data.get('text') or str(solution_data)
                return "solved", solution
            else:
                return "failed", None
                
        except Exception as e:
            logger.error(f"Failed to get result from CapMonster: {e}")
            return "failed", None
    
    def _build_task_object(self, task: CaptchaTask) -> Dict:
        """Build CapMonster task object"""
        if task.captcha_type == CaptchaType.IMAGE:
            return {
                'type': 'ImageToTextTask',
                'body': task.image_data
            }
        elif task.captcha_type == CaptchaType.RECAPTCHA_V2:
            return {
                'type': 'NoCaptchaTaskProxyless',
                'websiteURL': task.page_url,
                'websiteKey': task.site_key
            }
        elif task.captcha_type == CaptchaType.RECAPTCHA_V3:
            return {
                'type': 'RecaptchaV3TaskProxyless',
                'websiteURL': task.page_url,
                'websiteKey': task.site_key,
                'minScore': task.additional_data.get('min_score', 0.3)
            }
        elif task.captcha_type == CaptchaType.HCAPTCHA:
            return {
                'type': 'HCaptchaTaskProxyless',
                'websiteURL': task.page_url,
                'websiteKey': task.site_key
            }
        else:
            raise ValueError(f"Unsupported CAPTCHA type: {task.captcha_type}")

class CaptchaSolver:
    """Main CAPTCHA solving service with provider failover"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.providers = {}
        self.active_tasks = {}
        self.provider_stats = {}
        
        # Initialize providers
        self._init_providers()
        
    def _init_providers(self):
        """Initialize CAPTCHA providers"""
        try:
            # 2captcha
            twocaptcha_key = self.config.get('twocaptcha_key', os.getenv('TWOCAPTCHA_API_KEY'))
            if twocaptcha_key:
                self.providers[CaptchaProvider.TWOCAPTCHA] = TwoCaptchaProvider(
                    twocaptcha_key, 
                    self.config.get('twocaptcha_config', {})
                )
            
            # Anti-Captcha
            anticaptcha_key = self.config.get('anticaptcha_key', os.getenv('ANTICAPTCHA_API_KEY'))
            if anticaptcha_key:
                self.providers[CaptchaProvider.ANTICAPTCHA] = AntiCaptchaProvider(
                    anticaptcha_key,
                    self.config.get('anticaptcha_config', {})
                )
            
            # CapMonster
            capmonster_key = self.config.get('capmonster_key', os.getenv('CAPMONSTER_API_KEY'))
            if capmonster_key:
                self.providers[CaptchaProvider.CAPMONSTER] = CapMonsterProvider(
                    capmonster_key,
                    self.config.get('capmonster_config', {})
                )
            
            # Initialize stats
            for provider in self.providers:
                self.provider_stats[provider] = {
                    'total_tasks': 0,
                    'successful_tasks': 0,
                    'failed_tasks': 0,
                    'avg_solve_time': 0,
                    'total_cost': 0.0,
                    'success_rate': 1.0
                }
            
            logger.info(f"Initialized {len(self.providers)} CAPTCHA providers")
            
        except Exception as e:
            logger.error(f"Failed to initialize CAPTCHA providers: {e}")
    
    async def solve_captcha(self, captcha_type: CaptchaType, image_data: str = None,
                          site_key: str = None, page_url: str = None,
                          additional_data: Dict = None, timeout: int = 300,
                          preferred_provider: CaptchaProvider = None) -> Optional[str]:
        """Solve CAPTCHA with automatic provider failover"""
        
        task_id = self._generate_task_id()
        
        # Create task
        task = CaptchaTask(
            task_id=task_id,
            captcha_type=captcha_type,
            provider=preferred_provider or self._select_best_provider(),
            image_data=image_data,
            site_key=site_key,
            page_url=page_url,
            additional_data=additional_data or {}
        )
        
        # Try providers in order of preference
        providers_to_try = self._get_provider_order(preferred_provider)
        
        for provider in providers_to_try:
            try:
                task.provider = provider
                solution = await self._solve_with_provider(task, timeout)
                
                if solution:
                    # Update success stats
                    stats = self.provider_stats[provider]
                    stats['successful_tasks'] += 1
                    stats['total_cost'] += self._get_task_cost(task)
                    
                    solve_time = (datetime.now() - task.created_at).total_seconds()
                    stats['avg_solve_time'] = (stats['avg_solve_time'] + solve_time) / 2
                    
                    logger.info(f"CAPTCHA solved by {provider.value} in {solve_time:.1f}s")
                    return solution
                
            except Exception as e:
                logger.warning(f"Provider {provider.value} failed: {e}")
                
                # Update failure stats
                stats = self.provider_stats[provider]
                stats['failed_tasks'] += 1
                
                continue
        
        logger.error(f"All CAPTCHA providers failed for task {task_id}")
        return None
    
    async def _solve_with_provider(self, task: CaptchaTask, timeout: int) -> Optional[str]:
        """Solve CAPTCHA with specific provider"""
        provider = self.providers[task.provider]
        
        try:
            # Submit task
            provider_task_id = await provider.submit_captcha(task)
            task.status = "processing"
            self.active_tasks[task.task_id] = (task, provider_task_id)
            
            # Poll for result
            start_time = time.time()
            poll_interval = 5  # Start with 5 second polls
            
            while time.time() - start_time < timeout:
                await asyncio.sleep(poll_interval)
                
                status, solution = await provider.get_result(task.task_id, provider_task_id)
                
                if status == "solved":
                    task.solution = solution
                    task.completed_at = datetime.now()
                    task.status = "solved"
                    
                    # Clean up
                    if task.task_id in self.active_tasks:
                        del self.active_tasks[task.task_id]
                    
                    return solution
                    
                elif status == "failed":
                    task.status = "failed"
                    if task.task_id in self.active_tasks:
                        del self.active_tasks[task.task_id]
                    return None
                
                # Increase poll interval gradually
                poll_interval = min(poll_interval * 1.1, 30)  # Max 30 seconds
            
            # Timeout
            task.status = "timeout"
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]
            
            logger.warning(f"CAPTCHA solving timed out after {timeout} seconds")
            return None
            
        except Exception as e:
            logger.error(f"Error solving CAPTCHA with {task.provider.value}: {e}")
            task.status = "failed"
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]
            return None
    
    def _select_best_provider(self) -> CaptchaProvider:
        """Select best provider based on performance metrics"""
        if not self.providers:
            raise ValueError("No CAPTCHA providers available")
        
        # Score providers
        best_provider = None
        best_score = -1
        
        for provider, stats in self.provider_stats.items():
            if provider not in self.providers:
                continue
                
            score = 0
            
            # Success rate (most important)
            if stats['total_tasks'] > 0:
                success_rate = stats['successful_tasks'] / stats['total_tasks']
                score += success_rate * 50
            else:
                score += 25  # Neutral score for untested providers
            
            # Speed (faster is better)
            if stats['avg_solve_time'] > 0:
                speed_score = max(0, 30 - (stats['avg_solve_time'] / 10))  # Penalty for slow solving
                score += speed_score
            else:
                score += 15  # Neutral speed score
            
            # Cost efficiency (lower cost is better) 
            if stats['total_cost'] > 0 and stats['successful_tasks'] > 0:
                avg_cost = stats['total_cost'] / stats['successful_tasks']
                cost_score = max(0, 20 - (avg_cost * 100))  # Penalty for high cost
                score += cost_score
            else:
                score += 10  # Neutral cost score
            
            if score > best_score:
                best_score = score
                best_provider = provider
        
        return best_provider or list(self.providers.keys())[0]
    
    def _get_provider_order(self, preferred: CaptchaProvider = None) -> List[CaptchaProvider]:
        """Get ordered list of providers to try"""
        available_providers = list(self.providers.keys())
        
        if preferred and preferred in available_providers:
            # Put preferred first
            ordered = [preferred]
            ordered.extend([p for p in available_providers if p != preferred])
            return ordered
        
        # Sort by performance
        return sorted(available_providers, key=lambda p: self._get_provider_score(p), reverse=True)
    
    def _get_provider_score(self, provider: CaptchaProvider) -> float:
        """Get performance score for provider"""
        stats = self.provider_stats[provider]
        
        if stats['total_tasks'] == 0:
            return 0.5  # Neutral score for untested providers
        
        success_rate = stats['successful_tasks'] / stats['total_tasks']
        return success_rate
    
    def _generate_task_id(self) -> str:
        """Generate unique task ID"""
        import uuid
        return str(uuid.uuid4())
    
    def _get_task_cost(self, task: CaptchaTask) -> float:
        """Get estimated cost for task"""
        # Cost estimates in USD
        cost_map = {
            CaptchaType.IMAGE: 0.001,
            CaptchaType.RECAPTCHA_V2: 0.002,
            CaptchaType.RECAPTCHA_V3: 0.002,
            CaptchaType.HCAPTCHA: 0.002,
            CaptchaType.FUNCAPTCHA: 0.002,
            CaptchaType.GEETEST: 0.002
        }
        
        return cost_map.get(task.captcha_type, 0.001)
    
    def get_provider_balances(self) -> Dict[str, float]:
        """Get balances for all providers"""
        balances = {}
        
        for provider_type, provider in self.providers.items():
            try:
                balance = provider.get_balance()
                balances[provider_type.value] = balance
            except Exception as e:
                logger.error(f"Failed to get balance for {provider_type.value}: {e}")
                balances[provider_type.value] = 0.0
        
        return balances
    
    def get_statistics(self) -> Dict:
        """Get comprehensive statistics"""
        stats = {
            'providers': {},
            'active_tasks': len(self.active_tasks),
            'balances': self.get_provider_balances(),
            'total_tasks_processed': sum(s['total_tasks'] for s in self.provider_stats.values()),
            'overall_success_rate': 0.0,
            'average_solve_time': 0.0,
            'total_cost': sum(s['total_cost'] for s in self.provider_stats.values())
        }
        
        # Calculate overall metrics
        total_tasks = stats['total_tasks_processed']
        total_successful = sum(s['successful_tasks'] for s in self.provider_stats.values())
        
        if total_tasks > 0:
            stats['overall_success_rate'] = total_successful / total_tasks
            
        if total_successful > 0:
            total_solve_time = sum(s['avg_solve_time'] * s['successful_tasks'] for s in self.provider_stats.values())
            stats['average_solve_time'] = total_solve_time / total_successful
        
        for provider, provider_stats in self.provider_stats.items():
            stats['providers'][provider.value] = dict(provider_stats)
            
            # Calculate success rate
            if provider_stats['total_tasks'] > 0:
                stats['providers'][provider.value]['success_rate'] = (
                    provider_stats['successful_tasks'] / provider_stats['total_tasks']
                )
        
        return stats
    
    async def check_all_balances(self) -> Dict[str, Dict[str, Union[float, bool]]]:
        """Check balances and status for all providers"""
        balance_report = {}
        
        for provider_type, provider in self.providers.items():
            try:
                balance = provider.get_balance()
                
                balance_report[provider_type.value] = {
                    'balance': balance,
                    'available': balance > 0.01,  # Consider available if > $0.01
                    'status': 'active' if balance > 0.01 else 'low_balance',
                    'last_checked': datetime.now().isoformat()
                }
                
            except Exception as e:
                balance_report[provider_type.value] = {
                    'balance': 0.0,
                    'available': False,
                    'status': 'error',
                    'error': str(e),
                    'last_checked': datetime.now().isoformat()
                }
                
                logger.error(f"Failed to check balance for {provider_type.value}: {e}")
        
        return balance_report
    
    async def get_cheapest_provider_for_task(self, captcha_type: CaptchaType) -> Optional[CaptchaProvider]:
        """Get the cheapest available provider for a specific CAPTCHA type"""
        available_providers = []
        
        for provider_type, provider in self.providers.items():
            try:
                balance = provider.get_balance()
                if balance > self._get_task_cost_for_provider(captcha_type, provider_type):
                    available_providers.append(provider_type)
            except Exception:
                continue
        
        if not available_providers:
            return None
        
        # Sort by estimated cost (cheapest first)
        costs = [(p, self._get_task_cost_for_provider(captcha_type, p)) for p in available_providers]
        costs.sort(key=lambda x: x[1])
        
        return costs[0][0] if costs else None
    
    def _get_task_cost_for_provider(self, captcha_type: CaptchaType, provider: CaptchaProvider) -> float:
        """Get estimated cost for specific provider and CAPTCHA type"""
        # Provider-specific cost adjustments
        base_cost = self._get_task_cost(None)  # Get base cost
        
        # Provider multipliers based on typical pricing
        provider_multipliers = {
            CaptchaProvider.TWOCAPTCHA: 1.0,     # Baseline
            CaptchaProvider.ANTICAPTCHA: 1.2,    # Slightly more expensive but reliable
            CaptchaProvider.CAPMONSTER: 0.8,     # Often cheaper
            CaptchaProvider.DEATHBYCAPTCHA: 1.1  # Middle range
        }
        
        multiplier = provider_multipliers.get(provider, 1.0)
        return base_cost * multiplier

# Global solver instance
_captcha_solver = None

def get_captcha_solver(config: Dict = None) -> CaptchaSolver:
    """Get global CAPTCHA solver instance"""
    global _captcha_solver
    if _captcha_solver is None:
        _captcha_solver = CaptchaSolver(config)
    return _captcha_solver

def get_all_provider_balances() -> Dict[str, float]:
    """Get balances from all configured CAPTCHA providers"""
    try:
        solver = get_captcha_solver()
        return solver.get_provider_balances()
    except Exception as e:
        logger.error(f"Failed to get provider balances: {e}")
        return {}

# Convenience functions
async def solve_image_captcha(image_data: str, timeout: int = 120) -> Optional[str]:
    """Solve image CAPTCHA"""
    solver = get_captcha_solver()
    return await solver.solve_captcha(
        CaptchaType.IMAGE,
        image_data=image_data,
        timeout=timeout
    )

async def solve_recaptcha_v2(site_key: str, page_url: str, timeout: int = 300) -> Optional[str]:
    """Solve reCAPTCHA v2"""
    solver = get_captcha_solver()
    return await solver.solve_captcha(
        CaptchaType.RECAPTCHA_V2,
        site_key=site_key,
        page_url=page_url,
        timeout=timeout
    )

async def solve_recaptcha_v3(site_key: str, page_url: str, action: str = "submit", 
                           min_score: float = 0.3, timeout: int = 300) -> Optional[str]:
    """Solve reCAPTCHA v3"""
    solver = get_captcha_solver()
    return await solver.solve_captcha(
        CaptchaType.RECAPTCHA_V3,
        site_key=site_key,
        page_url=page_url,
        additional_data={'action': action, 'min_score': min_score},
        timeout=timeout
    )

async def solve_hcaptcha(site_key: str, page_url: str, timeout: int = 300) -> Optional[str]:
    """Solve hCAPTCHA"""
    solver = get_captcha_solver()
    return await solver.solve_captcha(
        CaptchaType.HCAPTCHA,
        site_key=site_key,
        page_url=page_url,
        timeout=timeout
    )

def encode_image_file(image_path: str) -> str:
    """Encode image file to base64"""
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
        return base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to encode image file: {e}")
        return ""

if __name__ == "__main__":
    async def test_captcha_solver():
        """Test CAPTCHA solver functionality"""
        print("Testing CAPTCHA Solver...")
        
        # Initialize with test config
        config = {
            'twocaptcha_key': os.getenv('TWOCAPTCHA_API_KEY'),
            'anticaptcha_key': os.getenv('ANTICAPTCHA_API_KEY')
        }
        
        solver = CaptchaSolver(config)
        
        # Get statistics
        stats = solver.get_statistics()
        print(f"Solver statistics: {json.dumps(stats, indent=2)}")
        
        # Test image CAPTCHA (if you have test image)
        # test_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        # solution = await solver.solve_captcha(CaptchaType.IMAGE, image_data=test_image)
        # print(f"Image CAPTCHA solution: {solution}")
        
        print("CAPTCHA Solver test complete")
    
    # Run test
    asyncio.run(test_captcha_solver())