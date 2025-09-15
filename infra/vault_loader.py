#!/usr/bin/env python3
"""
HashiCorp Vault Secrets Loader
Loads secrets from Vault and sets them as environment variables
"""

import os
import sys
import logging
from typing import Dict, Any, Optional

# Try to import hvac (HashiCorp Vault client)
try:
    import hvac
    VAULT_AVAILABLE = True
except ImportError:
    VAULT_AVAILABLE = False
    print("Warning: hvac library not available. Install with: pip install hvac")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VaultLoader:
    def __init__(self, vault_addr: Optional[str] = None, vault_token: Optional[str] = None):
        self.vault_addr = vault_addr or os.environ.get('VAULT_ADDRESS', 'http://localhost:8200')
        self.vault_token = vault_token or os.environ.get('VAULT_TOKEN')
        self.client = None
        
        if not self.vault_token:
            logger.warning("VAULT_TOKEN not provided. Using fallback configuration.")
        
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Vault client connection"""
        if not VAULT_AVAILABLE:
            logger.warning("Vault client not available, using environment fallback")
            return
        
        try:
            self.client = hvac.Client(url=self.vault_addr, token=self.vault_token)
            
            if self.client.is_authenticated():
                logger.info(f"Successfully authenticated with Vault at {self.vault_addr}")
            else:
                logger.warning("Vault authentication failed, using fallback")
                self.client = None
                
        except Exception as e:
            logger.error(f"Failed to connect to Vault: {e}")
            self.client = None
    
    def load_secrets(self, secret_path: str = 'p2p/creds') -> Dict[str, str]:
        """
        Load secrets from Vault and return as dictionary
        Falls back to environment variables if Vault is unavailable
        """
        secrets = {}
        
        if self.client:
            try:
                # Try KV v2 engine first
                response = self.client.secrets.kv.v2.read_secret_version(path=secret_path)
                if response and 'data' in response and 'data' in response['data']:
                    secrets = response['data']['data']
                    logger.info(f"Loaded {len(secrets)} secrets from Vault path: {secret_path}")
                else:
                    # Try KV v1 engine
                    response = self.client.secrets.kv.v1.read_secret(path=secret_path)
                    if response and 'data' in response:
                        secrets = response['data']
                        logger.info(f"Loaded {len(secrets)} secrets from Vault (KV v1) path: {secret_path}")
                        
            except Exception as e:
                logger.error(f"Failed to load secrets from Vault: {e}")
        
        # Fallback to environment variables with predefined keys
        if not secrets:
            logger.info("Using environment variable fallback for secrets")
            fallback_keys = [
                'CLOUD_API_TOKEN',
                'SMS_API_KEY',
                'TG_API_ID',
                'TG_API_HASH',
                'JWT_SECRET',
                'WEBHOOK_SECRET',
                'PAYMENT_PROVIDER_API_KEY',
                'REDIS_PASSWORD',
                'DATABASE_PASSWORD'
            ]
            
            for key in fallback_keys:
                value = os.environ.get(key)
                if value:
                    secrets[key] = value
        
        return secrets
    
    def set_environment_variables(self, secrets: Dict[str, str]) -> None:
        """Set secrets as environment variables"""
        for key, value in secrets.items():
            os.environ[key] = str(value)
            logger.debug(f"Set environment variable: {key}")
        
        logger.info(f"Set {len(secrets)} environment variables from secrets")
    
    def load_and_set(self, secret_path: str = 'p2p/creds') -> bool:
        """Load secrets from Vault and set as environment variables"""
        try:
            secrets = self.load_secrets(secret_path)
            if secrets:
                self.set_environment_variables(secrets)
                return True
            else:
                logger.warning("No secrets loaded")
                return False
                
        except Exception as e:
            logger.error(f"Failed to load and set secrets: {e}")
            return False

def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Load secrets from HashiCorp Vault')
    parser.add_argument('--vault-addr', help='Vault server address')
    parser.add_argument('--vault-token', help='Vault authentication token')
    parser.add_argument('--secret-path', default='p2p/creds', help='Path to secrets in Vault')
    parser.add_argument('--list-only', action='store_true', help='List loaded secrets without setting env vars')
    
    args = parser.parse_args()
    
    # Initialize loader
    loader = VaultLoader(vault_addr=args.vault_addr, vault_token=args.vault_token)
    
    # Load secrets
    secrets = loader.load_secrets(args.secret_path)
    
    if args.list_only:
        print("Loaded secrets:")
        for key in secrets.keys():
            print(f"  - {key}")
    else:
        # Set environment variables
        loader.set_environment_variables(secrets)
        print(f"Successfully loaded and set {len(secrets)} secrets as environment variables")
    
    return len(secrets) > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)