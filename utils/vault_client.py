#!/usr/bin/env python3
"""
HashiCorp Vault client utility with environment fallback.

Usage patterns:
- get_secret('JWT_SECRET', default='changeme')
- get_secret('TWILIO_AUTH_TOKEN', path='secret/twilio', field='auth_token')
- get_int('PORT', default=8000)
- get_bool('FEATURE_FLAG', default=False)

You can also provide a JSON mapping of names to Vault paths via VAULT_SECRET_MAPPINGS.
Example (env var VAULT_SECRET_MAPPINGS):
{
  "TWILIO_ACCOUNT_SID": {"path": "secret/twilio", "field": "account_sid"},
  "TWILIO_AUTH_TOKEN": {"path": "secret/twilio", "field": "auth_token"},
  "REDIS_URL": {"path": "secret/redis", "field": "url"}
}

Security notes:
- Never logs secret values.
- Respects *_FILE environment convention to read secrets from files (e.g., JWT_SECRET_FILE).
- Caches Vault reads with a short TTL to reduce overhead.
"""

from __future__ import annotations

import os
import json
import time
import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import hvac  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    hvac = None


class _VaultClient:
    def __init__(self) -> None:
        self.addr = os.getenv('VAULT_ADDR') or os.getenv('VAULT_ADDRESS') or 'http://localhost:8200'
        self.token = self._load_token()
        self.namespace = os.getenv('VAULT_NAMESPACE')
        self.mount_point = os.getenv('VAULT_MOUNT', 'secret')  # default KV v2 mount
        self.verify_tls = not (os.getenv('VAULT_SKIP_VERIFY', 'false').lower() in ('1', 'true', 'yes', 'on'))
        self._client = None
        self._enabled_checked = False
        self._enabled = False
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._ttl = int(os.getenv('VAULT_CACHE_TTL_SECONDS', '300'))
        self._mappings = self._load_mappings()
        self._initialize_client()

    def _load_token(self) -> Optional[str]:
        # Prefer file (e.g., Kubernetes secrets)
        token_file = os.getenv('VAULT_TOKEN_FILE', '/vault/secrets/token')
        try:
            if token_file and os.path.exists(token_file):
                with open(token_file, 'r') as f:
                    token = f.read().strip()
                    if token:
                        logger.debug('Loaded Vault token from file')
                        return token
        except Exception as e:
            logger.debug(f'Failed reading VAULT_TOKEN_FILE: {e}')
        # Fallback to env var
        token = os.getenv('VAULT_TOKEN')
        if token:
            logger.debug('Using Vault token from environment')
        return token

    def _load_mappings(self) -> Dict[str, Dict[str, str]]:
        raw = os.getenv('VAULT_SECRET_MAPPINGS', '')
        if not raw:
            return {}
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                # Normalize keys to upper-case env-var style
                return {str(k).upper(): v for k, v in data.items() if isinstance(v, dict)}
        except Exception as e:
            logger.warning(f'Invalid VAULT_SECRET_MAPPINGS JSON: {e}')
        return {}

    def _initialize_client(self) -> None:
        if hvac is None or not self.token:
            self._client = None
            self._enabled = False
            self._enabled_checked = True
            if hvac is None:
                logger.debug('hvac is not installed; Vault usage disabled')
            else:
                logger.debug('No Vault token; Vault usage disabled')
            return
        try:
            client = hvac.Client(url=self.addr, token=self.token, verify=self.verify_tls)
            if self.namespace:
                try:
                    client.adapter.namespace = self.namespace  # type: ignore[attr-defined]
                except Exception:
                    # Older hvac may not support namespace; ignore
                    pass
            self._client = client if client.is_authenticated() else None
            self._enabled = self._client is not None
            self._enabled_checked = True
            if self._enabled:
                logger.info(f'Vault client authenticated at {self.addr}')
            else:
                logger.warning('Vault authentication failed; falling back to environment')
        except Exception as e:
            logger.warning(f'Vault client initialization failed: {e}; falling back to environment')
            self._client = None
            self._enabled = False
            self._enabled_checked = True

    @property
    def enabled(self) -> bool:
        if not self._enabled_checked:
            self._initialize_client()
        return self._enabled

    def _cache_get(self, key: str) -> Optional[Any]:
        if self._ttl <= 0:
            return None
        entry = self._cache.get(key)
        if not entry:
            return None
        value, ts = entry
        if (time.time() - ts) < self._ttl:
            return value
        try:
            del self._cache[key]
        except Exception:
            pass
        return None

    def _cache_set(self, key: str, value: Any) -> None:
        if self._ttl > 0:
            self._cache[key] = (value, time.time())

    def _read_secret(self, path: str) -> Optional[Dict[str, Any]]:
        """Read a secret dict from Vault at the given path. Supports KV v2 then KV v1.
        Returns the dict of fields, or None on failure.
        """
        if not self.enabled or self._client is None:
            return None
        cache_key = f'kv:{path}'
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached  # type: ignore[return-value]
        try:
            # Try KV v2 first
            try:
                resp = self._client.secrets.kv.v2.read_secret_version(path=path, mount_point=self.mount_point)
                data = resp.get('data', {}).get('data', {}) if isinstance(resp, dict) else {}
                if data:
                    self._cache_set(cache_key, data)
                    return data
            except Exception:
                # Fall back to KV v1
                resp = self._client.secrets.kv.v1.read_secret(path=path, mount_point=self.mount_point)
                data = resp.get('data', {}) if isinstance(resp, dict) else {}
                if data:
                    self._cache_set(cache_key, data)
                    return data
        except Exception as e:
            logger.debug(f'Vault read failed for {path}: {e}')
        return None

    def _read_file_var(self, name: str) -> Optional[str]:
        file_var = os.getenv(f'{name}_FILE')
        if not file_var:
            return None
        try:
            if os.path.exists(file_var):
                with open(file_var, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            logger.debug(f'Failed to read {name}_FILE={file_var}: {e}')
        return None

    def get_secret(self, name: str, default: Optional[Any] = None, *, path: Optional[str] = None, field: Optional[str] = None, required: bool = False) -> Any:
        """Get a secret value by name with Vault and environment fallback.
        - name: env-var-like key (e.g., 'JWT_SECRET').
        - path/field: optional explicit Vault location.
        - If VAULT_SECRET_MAPPINGS contains an entry for name, it is used unless explicit path/field are provided.
        - Supports *_FILE convention for environment fallback.
        - Never logs the secret value.
        """
        # Explicit path overrides mapping
        vpath = path
        vfield = field
        if not vpath:
            mapping = self._mappings.get(name.upper())
            if mapping:
                vpath = mapping.get('path')
                vfield = mapping.get('field') or vfield
        # Try Vault first if configured for this key
        if self.enabled and vpath:
            data = self._read_secret(vpath)
            if data is not None:
                if vfield is None:
                    # If no field specified, return the whole dict
                    return data
                if vfield in data:
                    return data[vfield]
        # Fallback to environment
        file_value = self._read_file_var(name)
        if file_value is not None:
            return file_value
        env_val = os.getenv(name)
        if env_val is not None:
            return env_val
        if required and default is None:
            raise ValueError(f'Missing required secret: {name}')
        return default

    def get_int(self, name: str, default: Optional[int] = None, **kwargs) -> Optional[int]:
        val = self.get_secret(name, default=None, **kwargs)
        if val is None:
            return default
        try:
            return int(val)
        except Exception:
            logger.debug(f'Invalid int for {name}: {val!r}')
            return default

    def get_bool(self, name: str, default: bool = False, **kwargs) -> bool:
        val = self.get_secret(name, default=None, **kwargs)
        if val is None:
            return default
        if isinstance(val, bool):
            return val
        sval = str(val).strip().lower()
        if sval in ('1', 'true', 'yes', 'on'):  # truthy
            return True
        if sval in ('0', 'false', 'no', 'off'):  # falsy
            return False
        return default

    def get_json(self, name: str, default: Optional[Any] = None, **kwargs) -> Any:
        val = self.get_secret(name, default=None, **kwargs)
        if val is None:
            return default
        try:
            if isinstance(val, (dict, list)):
                return val
            return json.loads(str(val))
        except Exception:
            logger.debug(f'Invalid JSON for {name}')
            return default

    def reload_mappings(self) -> None:
        self._mappings = self._load_mappings()


_client = _VaultClient()


def get_secret(name: str, default: Optional[Any] = None, *, path: Optional[str] = None, field: Optional[str] = None, required: bool = False) -> Any:
    return _client.get_secret(name, default, path=path, field=field, required=required)


def get_int(name: str, default: Optional[int] = None, **kwargs) -> Optional[int]:
    return _client.get_int(name, default, **kwargs)


def get_bool(name: str, default: bool = False, **kwargs) -> bool:
    return _client.get_bool(name, default, **kwargs)


def get_json(name: str, default: Optional[Any] = None, **kwargs) -> Any:
    return _client.get_json(name, default, **kwargs)
