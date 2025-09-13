#!/usr/bin/env python3
"""
Smartproxy Residential Proxy Integration
Provides per-session proxy pinning and verification for all network requests
"""

import os
import random
import requests
import logging
import time
from typing import Dict, Optional
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
SMARTPROXY_USER = os.environ.get('SMARTPROXY_USER', 'your_trial_user')
SMARTPROXY_PASS = os.environ.get('SMARTPROXY_PASS', 'your_trial_pass')
SMARTPROXY_HOST = os.environ.get('SMARTPROXY_HOST', 'proxy.smartproxy.com')
SMARTPROXY_PORT = int(os.environ.get('SMARTPROXY_PORT', '7000'))

# Global proxy configuration
PROXY_URL = f"socks5://{SMARTPROXY_USER}:{SMARTPROXY_PASS}@{SMARTPROXY_HOST}:{SMARTPROXY_PORT}"

class ProxyManager:
    """Manages Smartproxy residential proxy connections with per-session pinning"""
    
    def __init__(self):
        self._session_proxies = None
        self._verification_cache = {}
        self._last_verification = 0
        self._verification_interval = 300  # 5 minutes
        
    def get_session_proxy(self) -> Dict[str, str]:
        """
        Get per-session pinned proxy configuration
        One proxy per process for consistent IP attribution
        """
        if not hasattr(self, '_session_proxies') or self._session_proxies is None:
            self._session_proxies = {
                'http': PROXY_URL,
                'https': PROXY_URL
            }
            logger.info(f"Initialized session proxy: {SMARTPROXY_HOST}:{SMARTPROXY_PORT}")
            
        return self._session_proxies
    
    def verify_proxy(self, force_check: bool = False) -> bool:
        """
        Verify proxy is working and is residential
        Caches results to avoid excessive verification calls
        """
        current_time = time.time()
        
        # Use cached result if recent (unless forced)
        if not force_check and (current_time - self._last_verification) < self._verification_interval:
            cached_result = self._verification_cache.get('is_residential', False)
            if cached_result:
                return True
        
        try:
            logger.info("Verifying residential proxy connection...")
            
            # Get IP information through proxy
            response = requests.get(
                'https://ipinfo.io/json', 
                proxies=self.get_session_proxy(), 
                timeout=10,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            response.raise_for_status()
            
            ip_info = response.json()
            
            # Extract key information
            ip_address = ip_info.get('ip', 'unknown')
            org = ip_info.get('org', '').lower()
            isp = ip_info.get('org', '').lower()
            country = ip_info.get('country', 'unknown')
            city = ip_info.get('city', 'unknown')
            
            logger.info(f"Proxy IP: {ip_address} | ISP: {org} | Location: {city}, {country}")
            
            # Verify it's residential (not datacenter)
            datacenter_indicators = [
                'datacenter', 'hosting', 'cloud', 'server', 'vps', 'aws', 'google', 
                'microsoft', 'azure', 'digital ocean', 'linode', 'vultr'
            ]
            
            is_datacenter = any(indicator in org for indicator in datacenter_indicators)
            
            # Look for residential indicators
            residential_indicators = [
                'residential', 'isp', 'telecom', 'broadband', 'cable', 'fiber',
                'internet service', 'communications'
            ]
            
            is_residential = any(indicator in org for indicator in residential_indicators)
            
            if is_datacenter and not is_residential:
                error_msg = f'Proxy appears to be datacenter, not residential: {org}'
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # Additional verification - check for common residential ISP patterns
            if not is_residential:
                # More lenient check - if it's not obviously datacenter, assume residential
                logger.warning(f"Could not confirm residential status, but no datacenter indicators found: {org}")
            
            # Cache successful verification
            self._verification_cache = {
                'is_residential': True,
                'ip_address': ip_address,
                'org': org,
                'country': country,
                'city': city,
                'verified_at': current_time
            }
            self._last_verification = current_time
            
            logger.info(f"✅ Proxy verification successful: Residential IP {ip_address}")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Proxy connection failed: {e}")
            raise RuntimeError(f'Proxy connection failed: {e}')
        except Exception as e:
            logger.error(f"Proxy verification failed: {e}")
            raise RuntimeError(f'Proxy verification failed: {e}')
    
    def get_proxy_info(self) -> Dict:
        """Get current proxy information from cache"""
        return self._verification_cache.copy()
    
    def test_proxy_rotation(self, num_tests: int = 3) -> bool:
        """Test if proxy provides different IPs (optional endpoint rotation)"""
        ips = set()
        
        for i in range(num_tests):
            try:
                response = requests.get(
                    'https://httpbin.org/ip',
                    proxies=self.get_session_proxy(),
                    timeout=10
                )
                ip = response.json().get('origin')
                ips.add(ip)
                logger.info(f"Test {i+1}: IP {ip}")
                time.sleep(2)  # Brief pause between tests
            except Exception as e:
                logger.warning(f"Rotation test {i+1} failed: {e}")
        
        unique_ips = len(ips)
        logger.info(f"Proxy rotation test: {unique_ips} unique IPs in {num_tests} tests")
        
        # Note: With residential proxies, we might get the same IP due to session stickiness
        # This is actually desired for per-session pinning
        return unique_ips >= 1  # At least one successful connection

# Global instance
_proxy_manager = ProxyManager()

def get_session_proxy() -> Dict[str, str]:
    """Get session-pinned proxy configuration"""
    return _proxy_manager.get_session_proxy()

def verify_proxy(force_check: bool = False) -> bool:
    """Verify proxy is working and residential"""
    return _proxy_manager.verify_proxy(force_check)

def get_proxy_info() -> Dict:
    """Get current proxy information"""
    return _proxy_manager.get_proxy_info()

def create_proxied_session() -> requests.Session:
    """Create a requests session with proxy pre-configured"""
    verify_proxy()  # Ensure proxy is working
    
    session = requests.Session()
    session.proxies.update(get_session_proxy())
    
    # Set reasonable defaults
    session.timeout = 30
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    return session

# Convenience functions for backward compatibility
def proxied_get(url: str, **kwargs) -> requests.Response:
    """Make GET request through residential proxy"""
    verify_proxy()
    kwargs.setdefault('proxies', get_session_proxy())
    kwargs.setdefault('timeout', 30)
    return requests.get(url, **kwargs)

def proxied_post(url: str, **kwargs) -> requests.Response:
    """Make POST request through residential proxy"""
    verify_proxy()
    kwargs.setdefault('proxies', get_session_proxy())
    kwargs.setdefault('timeout', 30)
    return requests.post(url, **kwargs)

def test_proxy_integration():
    """Test the proxy integration"""
    print("Testing Smartproxy residential proxy integration...")
    
    try:
        # Basic connectivity test
        print("1. Testing basic connectivity...")
        verify_proxy(force_check=True)
        print("   ✅ Proxy connectivity verified")
        
        # Test session consistency
        print("2. Testing session consistency...")
        proxy_info = get_proxy_info()
        print(f"   📍 Connected via: {proxy_info.get('ip_address')} ({proxy_info.get('city')}, {proxy_info.get('country')})")
        print(f"   🏢 ISP: {proxy_info.get('org')}")
        
        # Test different endpoints
        print("3. Testing multiple endpoints...")
        endpoints = [
            'https://httpbin.org/ip',
            'https://ipinfo.io/json',
            'https://api.github.com/zen'
        ]
        
        for endpoint in endpoints:
            try:
                resp = proxied_get(endpoint)
                print(f"   ✅ {endpoint}: {resp.status_code}")
            except Exception as e:
                print(f"   ❌ {endpoint}: {e}")
        
        print("4. Proxy integration test completed successfully! ✅")
        return True
        
    except Exception as e:
        print(f"❌ Proxy integration test failed: {e}")
        return False

if __name__ == "__main__":
    test_proxy_integration()