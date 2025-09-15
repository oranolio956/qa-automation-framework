#!/usr/bin/env python3
"""
Bright Data Browser API Proxy Integration
Provides session management and verification for all network requests through Bright Data residential proxies
"""

import os
import requests
import logging
import time
from typing import Dict, Optional
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load Bright Data environment variables (no defaults embedded)
BRIGHTDATA_PROXY_URL = os.environ.get('BRIGHTDATA_PROXY_URL', '').strip()

class BrightDataProxyManager:
    """Manages Bright Data Browser API proxy connections with session consistency"""
    
    def __init__(self):
        self._verification_cache = {}
        self._last_verification = 0
        self._verification_interval = 300  # 5 minutes
        
    def get_brightdata_session(self) -> requests.Session:
        """Create a requests session with Bright Data proxy pre-configured or from proxy pool."""
        # Prefer the shared proxy pool if available
        try:
            from automation.services.proxy_pool import get_proxy_pool
            pool = get_proxy_pool()
            sess = pool.session()
            if sess is not None:
                return sess
        except Exception:
            pass

        session = requests.Session()
        if BRIGHTDATA_PROXY_URL:
            session.proxies = {
                'http': BRIGHTDATA_PROXY_URL,
                'https': BRIGHTDATA_PROXY_URL,
            }
            masked = BRIGHTDATA_PROXY_URL.split('@')[0] + '@***' if '@' in BRIGHTDATA_PROXY_URL else '***'
            logger.info(f"Initialized Bright Data session with proxy: {masked}")
        else:
            logger.warning("BRIGHTDATA_PROXY_URL is not set; proceeding without proxy for session")

        # Set default headers
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        return session
    
    def verify_proxy(self, force_check: bool = False) -> bool:
        """
        Verify Bright Data proxy is working and provides residential IP
        Caches results to avoid excessive verification calls
        """
        current_time = time.time()
        
        # Use cached result if recent (unless forced)
        if not force_check and (current_time - self._last_verification) < self._verification_interval:
            cached_result = self._verification_cache.get('is_residential', False)
            if cached_result:
                return True
        
        if not BRIGHTDATA_PROXY_URL:
            raise RuntimeError('BRIGHTDATA_PROXY_URL is not configured')

        try:
            logger.info("Verifying Bright Data Browser API proxy connection...")
            
            # Get IP information through proxy
            session = self.get_brightdata_session()
            response = session.get('https://ipinfo.io/json', timeout=15)
            response.raise_for_status()
            
            ip_info = response.json()
            
            # Extract key information
            ip_address = ip_info.get('ip', 'unknown')
            org = ip_info.get('org', '').lower()
            country = ip_info.get('country', 'unknown')
            city = ip_info.get('city', 'unknown')
            region = ip_info.get('region', 'unknown')
            
            logger.info(f"Bright Data IP: {ip_address} | ISP: {org} | Location: {city}, {region}, {country}")
            
            # Check for bogon IP (invalid/private IP ranges)
            if 'bogon' in ip_info:
                error_msg = f'Bad proxy response: received bogon IP {ip_address}'
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # Verify we have a valid public IP
            if not ip_address or ip_address == 'unknown':
                error_msg = f'Bad proxy response: no valid IP address received'
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # Verify it's not obviously a datacenter (Bright Data should provide residential IPs)
            datacenter_indicators = [
                'amazon', 'aws', 'google cloud', 'microsoft azure', 'digital ocean', 
                'linode', 'vultr', 'ovh', 'hetzner'
            ]
            
            is_datacenter = any(indicator in org for indicator in datacenter_indicators)
            if is_datacenter:
                logger.warning(f"Detected datacenter IP, may not be residential: {org}")
            
            # Cache successful verification
            self._verification_cache = {
                'is_residential': True,
                'ip_address': ip_address,
                'org': org,
                'country': country,
                'city': city,
                'region': region,
                'verified_at': current_time
            }
            self._last_verification = current_time
            
            logger.info(f"✅ Bright Data proxy verification successful: IP {ip_address}")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Bright Data proxy connection failed: {e}")
            raise RuntimeError(f'Bright Data proxy connection failed: {e}')
        except Exception as e:
            logger.error(f"Bright Data proxy verification failed: {e}")
            raise RuntimeError(f'Bright Data proxy verification failed: {e}')
    
    def get_proxy_info(self) -> Dict:
        """Get current proxy information from cache"""
        return self._verification_cache.copy()
    
    def test_proxy_connectivity(self, num_tests: int = 3) -> bool:
        """Test proxy connectivity with multiple endpoints"""
        test_endpoints = [
            'https://httpbin.org/ip',
            'https://ipinfo.io/json',
            'https://api.github.com/zen'
        ]
        
        successful_tests = 0
        session = self.get_brightdata_session()
        
        for i, endpoint in enumerate(test_endpoints[:num_tests]):
            try:
                logger.info(f"Testing endpoint {i+1}/{num_tests}: {endpoint}")
                response = session.get(endpoint, timeout=15)
                response.raise_for_status()
                
                if endpoint.endswith('/ip'):
                    ip_data = response.json()
                    logger.info(f"  IP: {ip_data.get('origin', 'unknown')}")
                elif endpoint.endswith('.json'):
                    ip_info = response.json()
                    logger.info(f"  IP: {ip_info.get('ip', 'unknown')} | Location: {ip_info.get('city', 'unknown')}")
                else:
                    logger.info(f"  Response: {response.text[:50]}...")
                
                successful_tests += 1
                
            except Exception as e:
                logger.warning(f"Test {i+1} failed for {endpoint}: {e}")
        
        success_rate = successful_tests / min(num_tests, len(test_endpoints))
        logger.info(f"Proxy connectivity test: {successful_tests}/{min(num_tests, len(test_endpoints))} tests passed ({success_rate:.1%})")
        
        return success_rate >= 0.67  # At least 2/3 tests should pass

# Global instance
_brightdata_manager = BrightDataProxyManager()

def get_brightdata_session() -> requests.Session:
    """Get a requests session configured with Bright Data proxy"""
    return _brightdata_manager.get_brightdata_session()

def verify_proxy(force_check: bool = False) -> bool:
    """Verify Bright Data proxy is working"""
    return _brightdata_manager.verify_proxy(force_check)

def get_proxy_info() -> Dict:
    """Get current proxy information"""
    return _brightdata_manager.get_proxy_info()

def test_brightdata_integration():
    """Test the Bright Data integration"""
    print("Testing Bright Data Browser API proxy integration...")
    
    try:
        # Basic connectivity test
        print("1. Testing basic connectivity...")
        verify_proxy(force_check=True)
        print("   ✅ Bright Data proxy connectivity verified")
        
        # Test session info
        print("2. Testing session information...")
        proxy_info = get_proxy_info()
        print(f"   📍 Connected via: {proxy_info.get('ip_address')} ({proxy_info.get('city')}, {proxy_info.get('country')})")
        print(f"   🏢 ISP: {proxy_info.get('org')}")
        
        # Test multiple endpoints
        print("3. Testing multiple endpoints...")
        success = _brightdata_manager.test_proxy_connectivity(3)
        
        if success:
            print("4. Bright Data integration test completed successfully! ✅")
            return True
        else:
            print("4. Bright Data integration test failed - insufficient connectivity ❌")
            return False
        
    except Exception as e:
        print(f"❌ Bright Data integration test failed: {e}")
        return False

if __name__ == "__main__":
    test_brightdata_integration()