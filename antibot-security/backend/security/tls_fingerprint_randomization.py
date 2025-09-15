"""
Advanced TLS Fingerprint Randomization System
Production-ready TLS fingerprint randomization with JA4/JA3 evasion capabilities
Implements per-session cryptographic fingerprint variation for enhanced security
"""

import asyncio
import random
import secrets
import hashlib
import json
import time
import statistics
import math
from typing import Dict, List, Optional, Tuple, Any, Union, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import ssl
import socket
import struct
from contextlib import asynccontextmanager
from collections import defaultdict, deque

# OpenSSL/cryptography imports for advanced TLS manipulation
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, ec, ed25519
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography import x509
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

# Logging and telemetry
import logging
from ..observability.telemetry_integration import trace_database_operation

logger = logging.getLogger(__name__)


class TLSVersion(Enum):
    TLS_1_0 = "TLS 1.0"
    TLS_1_1 = "TLS 1.1" 
    TLS_1_2 = "TLS 1.2"
    TLS_1_3 = "TLS 1.3"


class CipherSuiteFamily(Enum):
    AES_GCM = "AES_GCM"
    AES_CBC = "AES_CBC"
    CHACHA20_POLY1305 = "CHACHA20_POLY1305"
    ECDHE_RSA = "ECDHE_RSA"
    ECDHE_ECDSA = "ECDHE_ECDSA"
    DHE_RSA = "DHE_RSA"


class ECCurve(Enum):
    P256 = "secp256r1"
    P384 = "secp384r1"
    P521 = "secp521r1"
    X25519 = "x25519"
    X448 = "x448"


@dataclass
class TLSFingerprint:
    """Comprehensive TLS fingerprint structure"""
    ja3_hash: str                           # JA3 fingerprint hash
    ja4_hash: str                           # JA4 fingerprint hash (newer)
    tls_version: TLSVersion
    cipher_suites: List[str]
    extensions: List[str]
    elliptic_curves: List[ECCurve]
    signature_algorithms: List[str]
    compression_methods: List[str]
    alpn_protocols: List[str]
    session_ticket: bool
    sni_enabled: bool
    ocsp_stapling: bool
    certificate_transparency: bool
    grease_values: List[int]               # GREASE randomization values
    key_share_groups: List[str]            # TLS 1.3 key share groups
    psk_modes: List[str]                   # Pre-shared key modes
    supported_versions: List[TLSVersion]
    record_size_limit: Optional[int]
    padding_extension: Optional[int]
    timestamp: datetime
    entropy_sources: Dict[str, float]      # Sources of randomization


@dataclass
class RandomizationProfile:
    """Profile defining randomization behavior"""
    profile_id: str
    name: str
    description: str
    randomization_level: str               # low, medium, high, extreme
    maintain_compatibility: bool
    target_applications: List[str]         # Browser types to mimic
    update_frequency: timedelta
    constraints: Dict[str, Any]
    success_rate: float
    detection_resistance: float


@dataclass
class FingerprintRotationConfig:
    """Configuration for fingerprint rotation"""
    rotation_interval: timedelta
    session_based_rotation: bool
    ip_based_rotation: bool
    time_based_jitter: timedelta
    preserve_session_affinity: bool
    entropy_refresh_rate: float


class TLSFingerprintRandomizer:
    """
    Advanced TLS fingerprint randomization engine
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Randomization profiles
        self.profiles = self._initialize_profiles()
        self.current_profile = self.profiles["balanced"]
        
        # Fingerprint cache and rotation
        self.fingerprint_cache: Dict[str, TLSFingerprint] = {}
        self.rotation_config = self._initialize_rotation_config()
        
        # Cipher suite and extension databases
        self.cipher_suites = self._initialize_cipher_suites()
        self.tls_extensions = self._initialize_tls_extensions()
        self.signature_algorithms = self._initialize_signature_algorithms()
        
        # Entropy sources
        self.entropy_pool = EntropyPool()
        
        # Enhanced browser fingerprint templates with dynamics
        self.browser_templates = self._initialize_browser_templates()
        self.mobile_templates = self._initialize_mobile_templates()
        self.browser_market_share = self._initialize_browser_market_data()
        self.version_evolution_tracker = BrowserVersionEvolution()
        
        # Enhanced statistics and monitoring
        self.generation_stats = {
            "total_generated": 0,
            "successful_connections": 0,
            "detection_events": 0,
            "profile_usage": {},
            "entropy_consumption": 0.0,
            "quality_distribution": deque(maxlen=1000),
            "detection_rate": deque(maxlen=100),
            "browser_success_rates": defaultdict(lambda: deque(maxlen=50)),
            "geographic_performance": defaultdict(lambda: deque(maxlen=30)),
            "adaptive_improvements": 0,
            "ml_recommendations": 0
        }
        
        # Advanced fingerprinting components
        self.cipher_suite_mapper = EnhancedCipherSuiteMapper()
        self.extension_correlator = ExtensionCorrelationAnalyzer()
        self.detection_predictor = FingerprintDetectionPredictor()
        self.quality_analyzer = FingerprintQualityAnalyzer()
        
        logger.info("TLS Fingerprint Randomizer initialized")
    
    def _initialize_profiles(self) -> Dict[str, RandomizationProfile]:
        """Initialize randomization profiles for different use cases"""
        return {
            "stealth": RandomizationProfile(
                profile_id="stealth",
                name="Maximum Stealth",
                description="Maximum randomization for stealth operations",
                randomization_level="extreme",
                maintain_compatibility=False,
                target_applications=["custom", "research"],
                update_frequency=timedelta(minutes=5),
                constraints={"min_cipher_suites": 8, "max_extensions": 20},
                success_rate=0.7,
                detection_resistance=0.95
            ),
            
            "balanced": RandomizationProfile(
                profile_id="balanced",
                name="Balanced Security",
                description="Balance between security and compatibility",
                randomization_level="medium",
                maintain_compatibility=True,
                target_applications=["chrome", "firefox", "safari"],
                update_frequency=timedelta(hours=1),
                constraints={"min_cipher_suites": 6, "max_extensions": 15},
                success_rate=0.92,
                detection_resistance=0.85
            ),
            
            "compatibility": RandomizationProfile(
                profile_id="compatibility",
                name="Maximum Compatibility",
                description="Minimal randomization for maximum compatibility",
                randomization_level="low",
                maintain_compatibility=True,
                target_applications=["chrome", "edge", "firefox"],
                update_frequency=timedelta(hours=6),
                constraints={"min_cipher_suites": 4, "max_extensions": 10},
                success_rate=0.98,
                detection_resistance=0.65
            ),
            
            "browser_mimic": RandomizationProfile(
                profile_id="browser_mimic",
                name="Browser Mimicry",
                description="Closely mimic real browser fingerprints",
                randomization_level="medium",
                maintain_compatibility=True,
                target_applications=["chrome", "firefox", "safari", "edge"],
                update_frequency=timedelta(hours=2),
                constraints={"mimic_accuracy": 0.9, "template_based": True},
                success_rate=0.95,
                detection_resistance=0.88
            )
        }
    
    def _initialize_rotation_config(self) -> FingerprintRotationConfig:
        """Initialize fingerprint rotation configuration"""
        return FingerprintRotationConfig(
            rotation_interval=timedelta(hours=1),
            session_based_rotation=True,
            ip_based_rotation=True,
            time_based_jitter=timedelta(minutes=15),
            preserve_session_affinity=True,
            entropy_refresh_rate=0.1
        )
    
    def _initialize_cipher_suites(self) -> Dict[TLSVersion, List[str]]:
        """Initialize cipher suite database organized by TLS version"""
        return {
            TLSVersion.TLS_1_2: [
                # ECDHE-RSA cipher suites
                "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384",
                "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256",
                "TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA384",
                "TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA256",
                "TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA",
                "TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA",
                
                # ECDHE-ECDSA cipher suites
                "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
                "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
                "TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA384",
                "TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA256",
                
                # ChaCha20-Poly1305 cipher suites
                "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256",
                "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256",
                
                # DHE cipher suites (less preferred but sometimes needed)
                "TLS_DHE_RSA_WITH_AES_256_GCM_SHA384",
                "TLS_DHE_RSA_WITH_AES_128_GCM_SHA256",
                
                # RSA cipher suites (for compatibility)
                "TLS_RSA_WITH_AES_256_GCM_SHA384",
                "TLS_RSA_WITH_AES_128_GCM_SHA256",
            ],
            
            TLSVersion.TLS_1_3: [
                # TLS 1.3 cipher suites (simplified in TLS 1.3)
                "TLS_AES_256_GCM_SHA384",
                "TLS_AES_128_GCM_SHA256",
                "TLS_CHACHA20_POLY1305_SHA256",
                "TLS_AES_128_CCM_SHA256",
                "TLS_AES_128_CCM_8_SHA256"
            ]
        }
    
    def _initialize_tls_extensions(self) -> Dict[str, Dict[str, Any]]:
        """Initialize TLS extensions database with parameters"""
        return {
            # Core extensions
            "server_name": {
                "id": 0,
                "required": True,
                "parameters": {"hostname": True},
                "compatibility": "universal"
            },
            
            "supported_groups": {
                "id": 10,
                "required": True,
                "parameters": {"curves": ["x25519", "secp256r1", "secp384r1", "secp521r1"]},
                "compatibility": "universal"
            },
            
            "ec_point_formats": {
                "id": 11,
                "required": False,
                "parameters": {"formats": ["uncompressed"]},
                "compatibility": "high"
            },
            
            "signature_algorithms": {
                "id": 13,
                "required": True,
                "parameters": {"algorithms": ["rsa_pss_rsae_sha256", "ecdsa_secp256r1_sha256"]},
                "compatibility": "universal"
            },
            
            "application_layer_protocol_negotiation": {
                "id": 16,
                "required": False,
                "parameters": {"protocols": ["h2", "http/1.1"]},
                "compatibility": "high"
            },
            
            "signed_certificate_timestamp": {
                "id": 18,
                "required": False,
                "parameters": {},
                "compatibility": "medium"
            },
            
            "padding": {
                "id": 21,
                "required": False,
                "parameters": {"length": "random"},
                "compatibility": "medium"
            },
            
            "extended_master_secret": {
                "id": 23,
                "required": False,
                "parameters": {},
                "compatibility": "high"
            },
            
            "session_ticket": {
                "id": 35,
                "required": False,
                "parameters": {},
                "compatibility": "high"
            },
            
            # TLS 1.3 specific extensions
            "supported_versions": {
                "id": 43,
                "required": True,
                "parameters": {"versions": ["TLS 1.3", "TLS 1.2"]},
                "compatibility": "tls13"
            },
            
            "cookie": {
                "id": 44,
                "required": False,
                "parameters": {},
                "compatibility": "tls13"
            },
            
            "psk_key_exchange_modes": {
                "id": 45,
                "required": False,
                "parameters": {"modes": ["psk_dhe_ke"]},
                "compatibility": "tls13"
            },
            
            "key_share": {
                "id": 51,
                "required": True,
                "parameters": {"groups": ["x25519", "secp256r1"]},
                "compatibility": "tls13"
            },
            
            # GREASE extensions for randomization
            "grease_0a0a": {"id": 0x0a0a, "required": False, "parameters": {}, "grease": True},
            "grease_1a1a": {"id": 0x1a1a, "required": False, "parameters": {}, "grease": True},
            "grease_2a2a": {"id": 0x2a2a, "required": False, "parameters": {}, "grease": True},
            
            # Additional modern extensions
            "status_request": {
                "id": 5,
                "required": False,
                "parameters": {"responder_id_list": []},
                "compatibility": "high"
            },
            
            "record_size_limit": {
                "id": 28,
                "required": False,
                "parameters": {"limit": 16384},
                "compatibility": "medium"
            },
            
            "compress_certificate": {
                "id": 27,
                "required": False,
                "parameters": {"algorithms": ["brotli", "zlib"]},
                "compatibility": "low"
            }
        }
    
    def _initialize_signature_algorithms(self) -> List[str]:
        """Initialize signature algorithms database"""
        return [
            # RSA-PSS signatures (preferred)
            "rsa_pss_rsae_sha256",
            "rsa_pss_rsae_sha384", 
            "rsa_pss_rsae_sha512",
            "rsa_pss_pss_sha256",
            "rsa_pss_pss_sha384",
            "rsa_pss_pss_sha512",
            
            # ECDSA signatures
            "ecdsa_secp256r1_sha256",
            "ecdsa_secp384r1_sha384",
            "ecdsa_secp521r1_sha512",
            
            # EdDSA signatures
            "ed25519",
            "ed448",
            
            # Legacy signatures (for compatibility)
            "rsa_pkcs1_sha256",
            "rsa_pkcs1_sha384",
            "rsa_pkcs1_sha512",
            "ecdsa_sha1",  # Deprecated but sometimes needed
            "rsa_pkcs1_sha1"  # Deprecated but sometimes needed
        ]
    
    def _initialize_browser_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize enhanced browser fingerprint templates with market data"""
        return {
            "chrome_latest": {
                "user_agent_hint": "Chrome/119",
                "tls_version": TLSVersion.TLS_1_3,
                "cipher_suites": [
                    "TLS_AES_128_GCM_SHA256",
                    "TLS_AES_256_GCM_SHA384", 
                    "TLS_CHACHA20_POLY1305_SHA256",
                    "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
                    "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256"
                ],
                "extensions": [
                    "server_name", "supported_groups", "signature_algorithms",
                    "application_layer_protocol_negotiation", "status_request",
                    "supported_versions", "key_share", "psk_key_exchange_modes",
                    "extended_master_secret", "compress_certificate"
                ],
                "supported_groups": [ECCurve.X25519, ECCurve.P256, ECCurve.P384],
                "signature_algorithms": [
                    "ecdsa_secp256r1_sha256", "rsa_pss_rsae_sha256",
                    "rsa_pkcs1_sha256", "ecdsa_secp384r1_sha384"
                ],
                "alpn_protocols": ["h2", "http/1.1"],
                "compress_certificate": True
            },
            
            "firefox_latest": {
                "user_agent_hint": "Firefox/119",
                "tls_version": TLSVersion.TLS_1_3,
                "cipher_suites": [
                    "TLS_AES_128_GCM_SHA256",
                    "TLS_CHACHA20_POLY1305_SHA256",
                    "TLS_AES_256_GCM_SHA384",
                    "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
                    "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256"
                ],
                "extensions": [
                    "server_name", "supported_groups", "signature_algorithms",
                    "application_layer_protocol_negotiation", "status_request",
                    "supported_versions", "key_share", "extended_master_secret",
                    "signed_certificate_timestamp"
                ],
                "supported_groups": [ECCurve.X25519, ECCurve.P256, ECCurve.P384, ECCurve.P521],
                "signature_algorithms": [
                    "ecdsa_secp256r1_sha256", "ecdsa_secp384r1_sha384", 
                    "rsa_pss_rsae_sha256", "rsa_pss_rsae_sha384"
                ],
                "alpn_protocols": ["h2", "http/1.1"],
                "record_size_limit": 16385  # Firefox uses 16385 instead of 16384
            },
            
            "safari_latest": {
                "user_agent_hint": "Safari/17.1",
                "tls_version": TLSVersion.TLS_1_3,
                "cipher_suites": [
                    "TLS_AES_128_GCM_SHA256",
                    "TLS_AES_256_GCM_SHA384",
                    "TLS_CHACHA20_POLY1305_SHA256",
                    "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
                    "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256"
                ],
                "extensions": [
                    "server_name", "supported_groups", "signature_algorithms",
                    "application_layer_protocol_negotiation", "status_request", 
                    "supported_versions", "key_share", "extended_master_secret"
                ],
                "supported_groups": [ECCurve.X25519, ECCurve.P256, ECCurve.P384],
                "signature_algorithms": [
                    "ecdsa_secp256r1_sha256", "rsa_pss_rsae_sha256",
                    "ecdsa_secp384r1_sha384", "rsa_pss_rsae_sha384"
                ],
                "alpn_protocols": ["h2", "http/1.1"]
            }
        }
    
    async def generate_randomized_fingerprint(self, 
                                           session_id: str,
                                           profile: Optional[str] = None,
                                           constraints: Optional[Dict[str, Any]] = None) -> TLSFingerprint:
        """
        Generate a randomized TLS fingerprint based on profile and constraints
        """
        start_time = time.time()
        
        try:
            # Select randomization profile
            active_profile = self.profiles.get(profile, self.current_profile)
            logger.debug(f"Generating fingerprint with profile: {active_profile.name}")
            
            # Check cache for existing fingerprint
            cache_key = f"{session_id}:{active_profile.profile_id}"
            if cache_key in self.fingerprint_cache:
                cached = self.fingerprint_cache[cache_key]
                if self._is_fingerprint_valid(cached, active_profile):
                    logger.debug(f"Returning cached fingerprint for session {session_id}")
                    return cached
            
            # Generate new fingerprint
            fingerprint = await self._generate_new_fingerprint(
                session_id, active_profile, constraints or {}
            )
            
            # Cache the fingerprint
            self.fingerprint_cache[cache_key] = fingerprint
            
            # Update statistics
            self.generation_stats["total_generated"] += 1
            self.generation_stats["profile_usage"][active_profile.profile_id] = \
                self.generation_stats["profile_usage"].get(active_profile.profile_id, 0) + 1
            
            generation_time = (time.time() - start_time) * 1000
            logger.info(f"Generated TLS fingerprint in {generation_time:.2f}ms")
            
            return fingerprint
            
        except Exception as e:
            logger.error(f"Failed to generate TLS fingerprint: {e}")
            # Return a basic fallback fingerprint
            return await self._generate_fallback_fingerprint(session_id)
    
    async def _generate_new_fingerprint(self,
                                      session_id: str,
                                      profile: RandomizationProfile,
                                      constraints: Dict[str, Any]) -> TLSFingerprint:
        """Generate a new TLS fingerprint from scratch"""
        
        # Refresh entropy pool
        await self.entropy_pool.refresh_entropy()
        
        # Select TLS version based on profile
        tls_version = self._select_tls_version(profile)
        
        # Generate cipher suites
        cipher_suites = self._generate_cipher_suites(tls_version, profile, constraints)
        
        # Generate extensions
        extensions = self._generate_extensions(tls_version, profile, constraints)
        
        # Generate elliptic curves
        elliptic_curves = self._generate_elliptic_curves(profile, constraints)
        
        # Generate signature algorithms
        signature_algorithms = self._generate_signature_algorithms(profile, constraints)
        
        # Generate GREASE values
        grease_values = self._generate_grease_values(profile)
        
        # Additional TLS 1.3 specific parameters
        key_share_groups = self._generate_key_share_groups(elliptic_curves, tls_version)
        psk_modes = self._generate_psk_modes(tls_version, profile)
        
        # Protocol configuration
        alpn_protocols = self._generate_alpn_protocols(profile, constraints)
        compression_methods = self._generate_compression_methods(profile)
        
        # Feature flags
        session_ticket = self._should_include_session_ticket(profile)
        sni_enabled = True  # Always enable SNI for modern compatibility
        ocsp_stapling = self._should_include_ocsp_stapling(profile)
        certificate_transparency = self._should_include_cert_transparency(profile)
        
        # Optional parameters
        record_size_limit = self._generate_record_size_limit(profile)
        padding_extension = self._generate_padding_extension(profile)
        
        # Create fingerprint object
        fingerprint = TLSFingerprint(
            ja3_hash="",  # Will be calculated
            ja4_hash="",  # Will be calculated
            tls_version=tls_version,
            cipher_suites=cipher_suites,
            extensions=extensions,
            elliptic_curves=elliptic_curves,
            signature_algorithms=signature_algorithms,
            compression_methods=compression_methods,
            alpn_protocols=alpn_protocols,
            session_ticket=session_ticket,
            sni_enabled=sni_enabled,
            ocsp_stapling=ocsp_stapling,
            certificate_transparency=certificate_transparency,
            grease_values=grease_values,
            key_share_groups=key_share_groups,
            psk_modes=psk_modes,
            supported_versions=[tls_version],
            record_size_limit=record_size_limit,
            padding_extension=padding_extension,
            timestamp=datetime.now(),
            entropy_sources=self.entropy_pool.get_entropy_sources()
        )
        
        # Calculate JA3 and JA4 hashes
        fingerprint.ja3_hash = self._calculate_ja3_hash(fingerprint)
        fingerprint.ja4_hash = self._calculate_ja4_hash(fingerprint)
        
        logger.debug(f"Generated fingerprint - JA3: {fingerprint.ja3_hash[:16]}...")
        
        return fingerprint
    
    def _select_tls_version(self, profile: RandomizationProfile) -> TLSVersion:
        """Select TLS version based on profile preferences"""
        if profile.profile_id == "browser_mimic":
            # Use the most common version for browsers
            return TLSVersion.TLS_1_3
        elif profile.randomization_level == "extreme":
            # Random selection with bias toward newer versions
            versions = [TLSVersion.TLS_1_2, TLSVersion.TLS_1_3]
            weights = [0.3, 0.7]
            return self.entropy_pool.weighted_choice(versions, weights)
        else:
            # Default to TLS 1.3 for security
            return TLSVersion.TLS_1_3
    
    def _generate_cipher_suites(self, 
                               tls_version: TLSVersion, 
                               profile: RandomizationProfile,
                               constraints: Dict[str, Any]) -> List[str]:
        """Generate cipher suite list based on version and profile"""
        available_suites = self.cipher_suites.get(tls_version, [])
        
        if profile.profile_id == "browser_mimic":
            # Use browser template if available
            template = self._select_browser_template(profile)
            if template and "cipher_suites" in template:
                base_suites = template["cipher_suites"]
            else:
                base_suites = available_suites[:6]  # Conservative selection
        else:
            base_suites = available_suites
        
        # Apply profile constraints
        min_suites = constraints.get("min_cipher_suites", profile.constraints.get("min_cipher_suites", 4))
        max_suites = constraints.get("max_cipher_suites", profile.constraints.get("max_cipher_suites", 12))
        
        if profile.randomization_level == "extreme":
            # Extreme randomization
            num_suites = self.entropy_pool.randint(min_suites, min(max_suites, len(base_suites)))
            selected = self.entropy_pool.sample(base_suites, num_suites)
            
            # Add some randomization to order
            self.entropy_pool.shuffle(selected)
            return selected
            
        elif profile.randomization_level == "medium":
            # Balanced selection
            num_suites = min(8, len(base_suites))
            selected = base_suites[:num_suites]
            
            # Minor randomization of order
            if len(selected) > 4:
                # Swap some positions
                for _ in range(2):
                    i, j = self.entropy_pool.sample(range(len(selected)), 2)
                    selected[i], selected[j] = selected[j], selected[i]
            
            return selected
            
        else:
            # Low randomization - use standard order
            return base_suites[:min(6, len(base_suites))]
    
    def _generate_extensions(self,
                           tls_version: TLSVersion,
                           profile: RandomizationProfile,
                           constraints: Dict[str, Any]) -> List[str]:
        """Generate TLS extensions list"""
        
        if profile.profile_id == "browser_mimic":
            template = self._select_browser_template(profile)
            if template and "extensions" in template:
                return template["extensions"].copy()
        
        # Start with required extensions
        extensions = []
        
        # Add required extensions based on TLS version
        required_extensions = [
            "server_name",
            "supported_groups", 
            "signature_algorithms"
        ]
        
        if tls_version == TLSVersion.TLS_1_3:
            required_extensions.extend([
                "supported_versions",
                "key_share"
            ])
        
        extensions.extend(required_extensions)
        
        # Add optional extensions based on profile
        optional_extensions = [
            "application_layer_protocol_negotiation",
            "status_request",
            "extended_master_secret",
            "session_ticket",
            "signed_certificate_timestamp",
            "padding"
        ]
        
        if tls_version == TLSVersion.TLS_1_3:
            optional_extensions.extend([
                "psk_key_exchange_modes",
                "record_size_limit"
            ])
        
        # Select optional extensions based on randomization level
        if profile.randomization_level == "extreme":
            # Random selection of optional extensions
            num_optional = self.entropy_pool.randint(2, min(8, len(optional_extensions)))
            selected_optional = self.entropy_pool.sample(optional_extensions, num_optional)
            extensions.extend(selected_optional)
            
            # Add some GREASE extensions
            if self.entropy_pool.random() < 0.7:
                grease_ext = self.entropy_pool.choice([
                    "grease_0a0a", "grease_1a1a", "grease_2a2a"
                ])
                extensions.append(grease_ext)
                
        elif profile.randomization_level == "medium":
            # Standard selection with some variation
            standard_optional = [
                "application_layer_protocol_negotiation",
                "status_request",
                "extended_master_secret"
            ]
            extensions.extend(standard_optional)
            
            # Sometimes add additional extensions
            if self.entropy_pool.random() < 0.5:
                extra = self.entropy_pool.choice([
                    "signed_certificate_timestamp",
                    "session_ticket"
                ])
                extensions.append(extra)
                
        else:
            # Conservative selection for compatibility
            extensions.extend([
                "application_layer_protocol_negotiation",
                "extended_master_secret"
            ])
        
        # Remove duplicates while preserving order
        unique_extensions = []
        seen = set()
        for ext in extensions:
            if ext not in seen:
                unique_extensions.append(ext)
                seen.add(ext)
        
        return unique_extensions
    
    def _generate_elliptic_curves(self,
                                profile: RandomizationProfile,
                                constraints: Dict[str, Any]) -> List[ECCurve]:
        """Generate supported elliptic curves list"""
        
        if profile.profile_id == "browser_mimic":
            template = self._select_browser_template(profile)
            if template and "supported_groups" in template:
                return template["supported_groups"].copy()
        
        # Standard secure curves
        standard_curves = [ECCurve.X25519, ECCurve.P256, ECCurve.P384]
        
        if profile.randomization_level == "extreme":
            # Include all available curves with randomization
            all_curves = list(ECCurve)
            num_curves = self.entropy_pool.randint(2, min(5, len(all_curves)))
            selected = self.entropy_pool.sample(all_curves, num_curves)
            
            # Ensure X25519 or P256 is included for compatibility
            if not any(curve in [ECCurve.X25519, ECCurve.P256] for curve in selected):
                selected[0] = ECCurve.X25519
            
            return selected
            
        elif profile.randomization_level == "medium":
            # Standard curves with some variation
            curves = standard_curves.copy()
            
            # Sometimes add P521 for variation
            if self.entropy_pool.random() < 0.3:
                curves.append(ECCurve.P521)
            
            # Minor reordering
            if len(curves) > 2 and self.entropy_pool.random() < 0.4:
                curves[1], curves[2] = curves[2], curves[1]
            
            return curves
            
        else:
            # Conservative selection
            return standard_curves[:2]  # Just X25519 and P256
    
    def _generate_signature_algorithms(self,
                                     profile: RandomizationProfile,
                                     constraints: Dict[str, Any]) -> List[str]:
        """Generate signature algorithms list"""
        
        if profile.profile_id == "browser_mimic":
            template = self._select_browser_template(profile)
            if template and "signature_algorithms" in template:
                return template["signature_algorithms"].copy()
        
        # Preferred modern algorithms
        preferred = [
            "ecdsa_secp256r1_sha256",
            "rsa_pss_rsae_sha256",
            "ecdsa_secp384r1_sha384",
            "rsa_pss_rsae_sha384"
        ]
        
        if profile.randomization_level == "extreme":
            # Include more algorithms including some legacy ones
            all_algorithms = self.signature_algorithms.copy()
            num_algorithms = self.entropy_pool.randint(4, min(10, len(all_algorithms)))
            selected = self.entropy_pool.sample(all_algorithms, num_algorithms)
            
            # Ensure at least one ECDSA and one RSA-PSS algorithm
            has_ecdsa = any("ecdsa" in alg for alg in selected)
            has_rsa_pss = any("rsa_pss" in alg for alg in selected)
            
            if not has_ecdsa:
                selected[0] = "ecdsa_secp256r1_sha256"
            if not has_rsa_pss:
                selected[1] = "rsa_pss_rsae_sha256"
            
            return selected
            
        elif profile.randomization_level == "medium":
            # Standard selection with minor variations
            algorithms = preferred.copy()
            
            # Sometimes add EdDSA
            if self.entropy_pool.random() < 0.3:
                algorithms.append("ed25519")
            
            # Sometimes include legacy for compatibility
            if profile.maintain_compatibility and self.entropy_pool.random() < 0.2:
                algorithms.append("rsa_pkcs1_sha256")
            
            return algorithms
            
        else:
            # Conservative selection
            return preferred[:3]
    
    def _generate_grease_values(self, profile: RandomizationProfile) -> List[int]:
        """Generate GREASE values for randomization"""
        if profile.randomization_level in ["medium", "extreme"]:
            # GREASE values follow pattern 0xXaXa where X is 0-f
            grease_patterns = [0x0a0a, 0x1a1a, 0x2a2a, 0x3a3a, 0x4a4a, 0x5a5a, 
                             0x6a6a, 0x7a7a, 0x8a8a, 0x9a9a, 0xaaaa, 0xbaba,
                             0xcaca, 0xdada, 0xeaea, 0xfafa]
            
            num_grease = self.entropy_pool.randint(1, 4)
            return self.entropy_pool.sample(grease_patterns, num_grease)
        
        return []
    
    def _generate_key_share_groups(self, 
                                 elliptic_curves: List[ECCurve],
                                 tls_version: TLSVersion) -> List[str]:
        """Generate key share groups for TLS 1.3"""
        if tls_version != TLSVersion.TLS_1_3:
            return []
        
        # Convert elliptic curves to key share group names
        curve_map = {
            ECCurve.X25519: "x25519",
            ECCurve.P256: "secp256r1",
            ECCurve.P384: "secp384r1",
            ECCurve.P521: "secp521r1",
            ECCurve.X448: "x448"
        }
        
        groups = []
        for curve in elliptic_curves[:2]:  # Usually just send key shares for first 2 curves
            if curve in curve_map:
                groups.append(curve_map[curve])
        
        return groups
    
    def _generate_psk_modes(self,
                          tls_version: TLSVersion,
                          profile: RandomizationProfile) -> List[str]:
        """Generate PSK key exchange modes for TLS 1.3"""
        if tls_version != TLSVersion.TLS_1_3:
            return []
        
        if profile.randomization_level == "extreme":
            modes = ["psk_ke", "psk_dhe_ke"]
            return self.entropy_pool.sample(modes, self.entropy_pool.randint(1, len(modes)))
        else:
            return ["psk_dhe_ke"]  # Standard mode
    
    def _generate_alpn_protocols(self,
                               profile: RandomizationProfile,
                               constraints: Dict[str, Any]) -> List[str]:
        """Generate ALPN protocol list"""
        
        if profile.profile_id == "browser_mimic":
            template = self._select_browser_template(profile)
            if template and "alpn_protocols" in template:
                return template["alpn_protocols"].copy()
        
        # Standard protocols
        standard_protocols = ["h2", "http/1.1"]
        
        if profile.randomization_level == "extreme":
            # Include additional protocols
            all_protocols = ["h2", "http/1.1", "spdy/3.1", "h2c"]
            num_protocols = self.entropy_pool.randint(1, min(3, len(all_protocols)))
            selected = self.entropy_pool.sample(all_protocols, num_protocols)
            
            # Ensure http/1.1 is included for compatibility
            if "http/1.1" not in selected:
                selected.append("http/1.1")
            
            return selected
        
        return standard_protocols
    
    def _generate_compression_methods(self, profile: RandomizationProfile) -> List[str]:
        """Generate compression methods list"""
        # TLS compression is generally disabled due to security issues (CRIME attack)
        # But we might include it for specific profiles
        if profile.randomization_level == "extreme" and self.entropy_pool.random() < 0.1:
            return ["null", "deflate"]
        
        return ["null"]  # Standard - no compression
    
    def _should_include_session_ticket(self, profile: RandomizationProfile) -> bool:
        """Determine if session ticket extension should be included"""
        if profile.randomization_level == "extreme":
            return self.entropy_pool.random() < 0.8
        elif profile.randomization_level == "medium":
            return self.entropy_pool.random() < 0.6
        else:
            return True  # Usually enabled for performance
    
    def _should_include_ocsp_stapling(self, profile: RandomizationProfile) -> bool:
        """Determine if OCSP stapling should be enabled"""
        return self.entropy_pool.random() < 0.7  # Most clients support this
    
    def _should_include_cert_transparency(self, profile: RandomizationProfile) -> bool:
        """Determine if Certificate Transparency should be enabled"""
        if profile.profile_id == "browser_mimic":
            return self.entropy_pool.random() < 0.8  # Most browsers support CT
        
        return self.entropy_pool.random() < 0.5
    
    def _generate_record_size_limit(self, profile: RandomizationProfile) -> Optional[int]:
        """Generate record size limit extension value"""
        if profile.randomization_level == "extreme":
            # Random size within reasonable bounds
            sizes = [4096, 8192, 16384, 16385]  # 16385 is Firefox-specific
            return self.entropy_pool.choice(sizes)
        elif profile.randomization_level == "medium":
            return 16384  # Standard size
        
        return None  # No limit specified
    
    def _generate_padding_extension(self, profile: RandomizationProfile) -> Optional[int]:
        """Generate padding extension length"""
        if profile.randomization_level in ["medium", "extreme"]:
            # Random padding to obscure ClientHello size
            return self.entropy_pool.randint(0, 255)
        
        return None
    
    def _select_browser_template(self, profile: RandomizationProfile) -> Optional[Dict[str, Any]]:
        """Select browser template for mimicry"""
        if profile.profile_id != "browser_mimic":
            return None
        
        templates = list(self.browser_templates.keys())
        return self.browser_templates[self.entropy_pool.choice(templates)]
    
    def _calculate_ja3_hash(self, fingerprint: TLSFingerprint) -> str:
        """Calculate JA3 fingerprint hash"""
        # JA3 format: SSLVersion,Cipher,SSLExtension,EllipticCurve,EllipticCurvePointFormat
        
        # Convert TLS version to number
        version_map = {
            TLSVersion.TLS_1_0: "769",
            TLSVersion.TLS_1_1: "770", 
            TLSVersion.TLS_1_2: "771",
            TLSVersion.TLS_1_3: "772"
        }
        
        ssl_version = version_map.get(fingerprint.tls_version, "771")
        
        # Convert cipher suites to numbers using enhanced mapping
        cipher_numbers = []
        for cipher in fingerprint.cipher_suites:
            # Use the enhanced cipher suite mapper for accurate conversion
            cipher_id = self.cipher_suite_mapper.get_cipher_id(cipher)
            if cipher_id:
                cipher_numbers.append(str(cipher_id))
            else:
                # Fallback to hash-based approach for unknown ciphers
                cipher_hash = hashlib.md5(cipher.encode()).hexdigest()[:4]
                cipher_numbers.append(str(int(cipher_hash, 16) % 65536))
        
        # Convert extensions to numbers
        extension_numbers = []
        for ext in fingerprint.extensions:
            if ext in self.tls_extensions:
                extension_numbers.append(str(self.tls_extensions[ext]["id"]))
        
        # Convert elliptic curves to numbers
        curve_numbers = []
        curve_map = {ECCurve.P256: "23", ECCurve.P384: "24", ECCurve.P521: "25", 
                    ECCurve.X25519: "29", ECCurve.X448: "30"}
        for curve in fingerprint.elliptic_curves:
            if curve in curve_map:
                curve_numbers.append(curve_map[curve])
        
        # Point formats (usually just uncompressed)
        point_formats = ["0"]  # 0 = uncompressed
        
        # Build JA3 string
        ja3_string = f"{ssl_version}," + \
                    "-".join(cipher_numbers) + "," + \
                    "-".join(extension_numbers) + "," + \
                    "-".join(curve_numbers) + "," + \
                    "-".join(point_formats)
        
        # Calculate MD5 hash
        return hashlib.md5(ja3_string.encode()).hexdigest()
    
    def _calculate_ja4_hash(self, fingerprint: TLSFingerprint) -> str:
        """Calculate JA4 fingerprint hash (newer format)"""
        # JA4 is more complex and includes more fields
        # This is a simplified implementation
        
        # Protocol version
        version_map = {
            TLSVersion.TLS_1_0: "10",
            TLSVersion.TLS_1_1: "11",
            TLSVersion.TLS_1_2: "12", 
            TLSVersion.TLS_1_3: "13"
        }
        version = version_map.get(fingerprint.tls_version, "12")
        
        # SNI flag
        sni = "d" if fingerprint.sni_enabled else "i"  # d=domain, i=ip
        
        # Number of cipher suites
        cipher_count = f"{len(fingerprint.cipher_suites):02x}"
        
        # Number of extensions
        ext_count = f"{len(fingerprint.extensions):02x}"
        
        # ALPN protocol
        alpn = fingerprint.alpn_protocols[0] if fingerprint.alpn_protocols else "00"
        if alpn == "http/1.1":
            alpn = "h1"
        elif alpn == "h2":
            alpn = "h2"
        
        # Build JA4 string (first part)
        ja4_a = f"t{version}{sni}{cipher_count}{ext_count}{alpn}"
        
        # Hash cipher suites and extensions for JA4_b and JA4_c
        cipher_hash = hashlib.sha256(",".join(sorted(fingerprint.cipher_suites)).encode()).hexdigest()[:12]
        ext_hash = hashlib.sha256(",".join(sorted(fingerprint.extensions)).encode()).hexdigest()[:12]
        
        ja4_full = f"{ja4_a}_{cipher_hash}_{ext_hash}"
        
        return ja4_full
    
    def _is_fingerprint_valid(self, fingerprint: TLSFingerprint, profile: RandomizationProfile) -> bool:
        """Check if cached fingerprint is still valid"""
        age = datetime.now() - fingerprint.timestamp
        return age < profile.update_frequency
    
    async def _generate_fallback_fingerprint(self, session_id: str) -> TLSFingerprint:
        """Generate a basic fallback fingerprint when main generation fails"""
        return TLSFingerprint(
            ja3_hash="fallback_" + hashlib.md5(session_id.encode()).hexdigest()[:16],
            ja4_hash="fallback_ja4",
            tls_version=TLSVersion.TLS_1_2,
            cipher_suites=["TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256"],
            extensions=["server_name", "supported_groups", "signature_algorithms"],
            elliptic_curves=[ECCurve.P256],
            signature_algorithms=["ecdsa_secp256r1_sha256"],
            compression_methods=["null"],
            alpn_protocols=["http/1.1"],
            session_ticket=True,
            sni_enabled=True,
            ocsp_stapling=False,
            certificate_transparency=False,
            grease_values=[],
            key_share_groups=[],
            psk_modes=[],
            supported_versions=[TLSVersion.TLS_1_2],
            record_size_limit=None,
            padding_extension=None,
            timestamp=datetime.now(),
            entropy_sources={}
        )
    
    # Public API methods
    
    async def set_profile(self, profile_id: str) -> bool:
        """Set the active randomization profile"""
        if profile_id in self.profiles:
            self.current_profile = self.profiles[profile_id]
            logger.info(f"Switched to profile: {self.current_profile.name}")
            return True
        
        logger.error(f"Unknown profile: {profile_id}")
        return False
    
    async def create_custom_profile(self, 
                                  profile_id: str,
                                  config: Dict[str, Any]) -> bool:
        """Create a custom randomization profile"""
        try:
            profile = RandomizationProfile(
                profile_id=profile_id,
                name=config.get("name", profile_id),
                description=config.get("description", "Custom profile"),
                randomization_level=config.get("randomization_level", "medium"),
                maintain_compatibility=config.get("maintain_compatibility", True),
                target_applications=config.get("target_applications", ["chrome"]),
                update_frequency=timedelta(seconds=config.get("update_frequency_seconds", 3600)),
                constraints=config.get("constraints", {}),
                success_rate=config.get("success_rate", 0.85),
                detection_resistance=config.get("detection_resistance", 0.75)
            )
            
            self.profiles[profile_id] = profile
            logger.info(f"Created custom profile: {profile.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create custom profile: {e}")
            return False
    
    async def get_fingerprint_for_session(self, session_id: str, **kwargs) -> TLSFingerprint:
        """Get or generate fingerprint for a specific session"""
        return await self.generate_randomized_fingerprint(session_id, **kwargs)
    
    async def invalidate_session_fingerprint(self, session_id: str) -> bool:
        """Invalidate cached fingerprint for a session"""
        keys_to_remove = [key for key in self.fingerprint_cache.keys() if key.startswith(f"{session_id}:")]
        
        for key in keys_to_remove:
            del self.fingerprint_cache[key]
        
        logger.debug(f"Invalidated {len(keys_to_remove)} cached fingerprints for session {session_id}")
        return len(keys_to_remove) > 0
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get randomization statistics"""
        return {
            **self.generation_stats,
            "cache_size": len(self.fingerprint_cache),
            "entropy_level": await self.entropy_pool.get_entropy_level(),
            "active_profile": self.current_profile.name,
            "profiles_available": list(self.profiles.keys())
        }
    
    async def cleanup_expired_fingerprints(self) -> int:
        """Clean up expired fingerprints from cache"""
        expired_keys = []
        
        for key, fingerprint in self.fingerprint_cache.items():
            profile_id = key.split(":")[1] if ":" in key else "balanced"
            profile = self.profiles.get(profile_id, self.current_profile)
            
            if not self._is_fingerprint_valid(fingerprint, profile):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.fingerprint_cache[key]
        
        logger.debug(f"Cleaned up {len(expired_keys)} expired fingerprints")
        return len(expired_keys)


class EntropyPool:
    """
    High-quality entropy pool for cryptographically secure randomization
    """
    
    def __init__(self):
        self.entropy_sources = {
            "system_random": 0.0,
            "secrets_module": 0.0,
            "timing_jitter": 0.0,
            "system_state": 0.0
        }
        
        # Initialize with system entropy
        self.random_gen = random.SystemRandom()
        
    async def refresh_entropy(self) -> None:
        """Refresh entropy from various sources"""
        try:
            # System random entropy
            self.entropy_sources["system_random"] = self.random_gen.random()
            
            # Cryptographically secure entropy
            self.entropy_sources["secrets_module"] = secrets.randbits(32) / (2**32)
            
            # Timing jitter entropy
            start = time.perf_counter()
            for _ in range(100):
                _ = hashlib.md5(b"entropy").hexdigest()
            timing = time.perf_counter() - start
            self.entropy_sources["timing_jitter"] = (timing * 1000000) % 1.0
            
            # System state entropy (memory, process info, etc.)
            import os
            import psutil
            pid = os.getpid()
            process = psutil.Process(pid)
            memory_percent = process.memory_percent()
            self.entropy_sources["system_state"] = (memory_percent * 17) % 1.0
            
        except Exception:
            # Fallback to basic entropy
            self.entropy_sources = {k: self.random_gen.random() for k in self.entropy_sources}
    
    def random(self) -> float:
        """Generate cryptographically secure random float"""
        return secrets.randbits(32) / (2**32)
    
    def randint(self, a: int, b: int) -> int:
        """Generate cryptographically secure random integer"""
        return secrets.randbelow(b - a + 1) + a
    
    def choice(self, sequence: List[Any]) -> Any:
        """Choose random element from sequence"""
        return sequence[secrets.randbelow(len(sequence))]
    
    def sample(self, population: List[Any], k: int) -> List[Any]:
        """Sample k elements from population without replacement"""
        if k > len(population):
            k = len(population)
        
        result = []
        remaining = population.copy()
        
        for _ in range(k):
            index = secrets.randbelow(len(remaining))
            result.append(remaining.pop(index))
        
        return result
    
    def shuffle(self, sequence: List[Any]) -> None:
        """Shuffle sequence in place using secure randomness"""
        for i in range(len(sequence) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            sequence[i], sequence[j] = sequence[j], sequence[i]
    
    def weighted_choice(self, choices: List[Any], weights: List[float]) -> Any:
        """Choose element based on weights"""
        total = sum(weights)
        r = self.random() * total
        
        cumulative = 0
        for choice, weight in zip(choices, weights):
            cumulative += weight
            if r <= cumulative:
                return choice
        
        return choices[-1]  # Fallback
    
    async def get_entropy_level(self) -> float:
        """Get current entropy level (0.0 to 1.0)"""
        # Calculate entropy based on source diversity and quality
        source_count = len([s for s in self.entropy_sources.values() if s > 0])
        max_sources = len(self.entropy_sources)
        
        return min(1.0, source_count / max_sources)
    
    def get_entropy_sources(self) -> Dict[str, float]:
        """Get current entropy source information"""
        return self.entropy_sources.copy()


# Global instance for easy access
_tls_randomizer: Optional[TLSFingerprintRandomizer] = None


def get_tls_randomizer() -> TLSFingerprintRandomizer:
    """Get global TLS randomizer instance"""
    global _tls_randomizer
    if not _tls_randomizer:
        _tls_randomizer = TLSFingerprintRandomizer()
    return _tls_randomizer


async def randomize_tls_fingerprint(session_id: str, 
                                  profile: Optional[str] = None,
                                  **kwargs) -> TLSFingerprint:
    """Convenience function to generate randomized TLS fingerprint"""
    randomizer = get_tls_randomizer()
    return await randomizer.generate_randomized_fingerprint(
        session_id=session_id, 
        profile=profile,
        **kwargs
    )


# Usage example and testing
if __name__ == "__main__":
    async def demo():
        """Demo the TLS fingerprint randomizer"""
        randomizer = TLSFingerprintRandomizer()
        
        # Generate fingerprints with different profiles
        profiles = ["stealth", "balanced", "compatibility", "browser_mimic"]
        
        for profile in profiles:
            print(f"\n=== Profile: {profile} ===")
            fingerprint = await randomizer.generate_randomized_fingerprint(
                session_id="demo_session",
                profile=profile
            )
            
            print(f"JA3: {fingerprint.ja3_hash}")
            print(f"JA4: {fingerprint.ja4_hash}")
            print(f"TLS Version: {fingerprint.tls_version.value}")
            print(f"Cipher Suites: {len(fingerprint.cipher_suites)}")
            print(f"Extensions: {len(fingerprint.extensions)}")
            print(f"Curves: {[c.value for c in fingerprint.elliptic_curves]}")
        
        # Show statistics
        stats = await randomizer.get_statistics()
        print(f"\n=== Statistics ===")
        print(json.dumps(stats, indent=2, default=str))
    
    # Run demo
    asyncio.run(demo())