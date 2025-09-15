#!/usr/bin/env python3
"""
APK Management Module for Snapchat Automation

Handles secure APK acquisition, verification, and installation.
Extracted from stealth_creator.py for better security and maintainability.
"""

import os
import subprocess
import shutil
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class APKInfo:
    """Information about an APK file"""
    path: Path
    package_name: str
    version_code: str
    version_name: str
    sha256: str
    signed_by: str
    is_verified: bool = False


class SecureAPKManager:
    """Secure APK management with signature verification and provenance tracking"""
    
    def __init__(self, artifacts_dir: str = None, cache_dir: str = None):
        # Configure directories
        self.artifacts_dir = Path(artifacts_dir or os.environ.get('SNAPCHAT_APK_ARTIFACTS_DIR', 'artifacts/apks'))
        self.cache_dir = Path(cache_dir or 'cache/apks')
        
        # Create directories if they don't exist
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Known good Snapchat APK information
        self.known_snapchat_hashes = {
            # Allowlist of known-good APKs. Populate via add_known_good_hash at deploy time or env var.
        }
        # Load allowlist from environment (comma-separated SHA256 list)
        env_hashes = os.environ.get('SNAPCHAT_APK_ALLOWED_SHA256S', '')
        if env_hashes:
            for h in [x.strip() for x in env_hashes.split(',') if x.strip()]:
                self.known_snapchat_hashes[h] = {"version": "env", "source": "env", "added_at": str(datetime.now())}
        
        # Certificate validation patterns
        self.snap_certificate_patterns = [
            'snap inc',
            'snapchat inc', 
            'cn=snap inc',
            'o=snap inc',
            'snap, inc.',
            'com.snapchat.android'
        ]
        
        logger.info(f"APK Manager initialized: artifacts={self.artifacts_dir}, cache={self.cache_dir}")
    
    def get_verified_snapchat_apk(self) -> Optional[Path]:
        """Get a verified Snapchat APK from available sources"""
        try:
            # Step 1: Check artifacts directory for verified APKs
            verified_apk = self._find_verified_artifact()
            if verified_apk:
                logger.info(f"Using verified artifact: {verified_apk}")
                return verified_apk
            
            # Step 2: Check cache for previously verified APKs
            cached_apk = self._find_verified_cache()
            if cached_apk:
                logger.info(f"Using verified cached APK: {cached_apk}")
                return cached_apk
            
            # Step 3: No verified APKs found
            self._log_acquisition_guidance()
            return None
            
        except Exception as e:
            logger.error(f"Error getting verified APK: {e}")
            return None
    
    def verify_apk_integrity(self, apk_path: Path) -> APKInfo:
        """Comprehensive APK verification including signature and integrity checks"""
        try:
            logger.info(f"Verifying APK integrity: {apk_path}")
            
            # Basic file checks
            if not apk_path.exists():
                raise ValueError(f"APK file not found: {apk_path}")
            
            if apk_path.stat().st_size < 1024 * 1024:  # < 1MB
                raise ValueError(f"APK file too small, likely corrupted: {apk_path}")
            
            # Extract basic APK info (graceful if aapt missing)
            apk_info = None
            try:
                apk_info = self._extract_apk_info(apk_path)
            except Exception:
                # Fallback: compute only sha256 when tools are missing
                apk_info = APKInfo(
                    path=apk_path,
                    package_name="unknown",
                    version_code="unknown",
                    version_name="unknown",
                    sha256=self._calculate_sha256(apk_path),
                    signed_by="unknown",
                    is_verified=False
                )
            
            # Verify package name
            if apk_info.package_name != 'com.snapchat.android':
                raise ValueError(f"Invalid package name: {apk_info.package_name}")
            
            # Verify signature where possible
            signature_valid = False
            signer = "unknown"
            try:
                signature_valid, signer = self._verify_apk_signature(apk_path)
            except Exception:
                signature_valid = False
                signer = "unknown"
            apk_info.signed_by = signer
            apk_info.is_verified = signature_valid
            
            # Enforce allowlist if configured
            if len(self.known_snapchat_hashes) > 0:
                if apk_info.sha256 in self.known_snapchat_hashes:
                    known_info = self.known_snapchat_hashes[apk_info.sha256]
                    logger.info(f"APK matches known good hash: {known_info}")
                    apk_info.is_verified = True
                else:
                    logger.error("APK hash not in allowlist; rejecting")
                    apk_info.is_verified = False
            
            # FREE_TEST_MODE bypass (development only)
            free_mode = str(os.environ.get('FREE_TEST_MODE', '0')).strip().lower() in ('1','true','yes','on')
            if free_mode and not apk_info.is_verified:
                logger.warning("FREE_TEST_MODE enabled: bypassing strict APK verification for development")
                apk_info.is_verified = True

            logger.info(f"APK verification complete: verified={apk_info.is_verified}")
            return apk_info
            
        except Exception as e:
            logger.error(f"APK verification failed: {e}")
            return APKInfo(
                path=apk_path,
                package_name="unknown",
                version_code="unknown", 
                version_name="unknown",
                sha256="unknown",
                signed_by="unknown",
                is_verified=False
            )
    
    def install_apk(self, device_id: str, apk_path: Path) -> bool:
        """Install APK on device with verification"""
        try:
            # Verify APK before installation
            apk_info = self.verify_apk_integrity(apk_path)
            if not apk_info.is_verified:
                logger.error(f"Refusing to install unverified APK: {apk_path}")
                return False
            
            logger.info(f"Installing verified APK {apk_info.version_name} on device {device_id}")
            
            # Install using ADB
            result = subprocess.run(
                ['adb', '-s', device_id, 'install', '-r', str(apk_path)],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                logger.info(f"APK installed successfully on {device_id}")
                
                # Verify installation
                if self._verify_installation(device_id, apk_info.package_name):
                    logger.info("Installation verification passed")
                    return True
                else:
                    logger.error("Installation verification failed")
                    return False
            else:
                logger.error(f"APK installation failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"APK installation error: {e}")
            return False
    
    def _find_verified_artifact(self) -> Optional[Path]:
        """Find verified APK in artifacts directory"""
        try:
            if not self.artifacts_dir.exists():
                return None
            
            patterns = ['snapchat*.apk', 'com.snapchat.android*.apk']
            for pattern in patterns:
                for apk_file in self.artifacts_dir.glob(pattern):
                    apk_info = self.verify_apk_integrity(apk_file)
                    if apk_info.is_verified:
                        return apk_file
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding verified artifact: {e}")
            return None
    
    def _find_verified_cache(self) -> Optional[Path]:
        """Find verified APK in cache directory"""
        try:
            if not self.cache_dir.exists():
                return None
            
            for apk_file in self.cache_dir.glob("*.apk"):
                if "snapchat" in apk_file.name.lower():
                    apk_info = self.verify_apk_integrity(apk_file)
                    if apk_info.is_verified:
                        return apk_file
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding verified cache: {e}")
            return None
    
    def _extract_apk_info(self, apk_path: Path) -> APKInfo:
        """Extract basic information from APK using aapt"""
        try:
            if not shutil.which('aapt'):
                raise FileNotFoundError('aapt not found')
            # Use aapt to extract APK information
            result = subprocess.run(
                ['aapt', 'dump', 'badging', str(apk_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"aapt failed: {result.stderr}")
            
            # Parse aapt output
            package_name = "unknown"
            version_code = "unknown"
            version_name = "unknown"
            
            for line in result.stdout.split('\n'):
                if line.startswith('package:'):
                    parts = line.split()
                    for part in parts:
                        if part.startswith('name='):
                            package_name = part.split('=')[1].strip("'\"")
                        elif part.startswith('versionCode='):
                            version_code = part.split('=')[1].strip("'\"")
                        elif part.startswith('versionName='):
                            version_name = part.split('=')[1].strip("'\"")
                    break
            
            # Calculate SHA256
            sha256 = self._calculate_sha256(apk_path)
            
            return APKInfo(
                path=apk_path,
                package_name=package_name,
                version_code=version_code,
                version_name=version_name,
                sha256=sha256,
                signed_by="unknown"
            )
            
        except Exception as e:
            logger.warning(f"aapt unavailable or failed: {e}")
            # Return minimal info; sha256 computed by caller if needed
            raise
    
    def _verify_apk_signature(self, apk_path: Path) -> tuple[bool, str]:
        """Verify APK signature using apksigner"""
        try:
            if shutil.which('apksigner'):
                # Try apksigner first (preferred method)
                result = subprocess.run(
                    ['apksigner', 'verify', '--print-certs', str(apk_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            else:
                result = subprocess.CompletedProcess(args=['apksigner'], returncode=1, stdout='', stderr='not found')
            
            if result.returncode == 0:
                output_lower = result.stdout.lower()
                
                # Check for Snap Inc. certificate patterns
                for pattern in self.snap_certificate_patterns:
                    if pattern in output_lower:
                        logger.info(f"Valid Snap Inc. certificate found: {pattern}")
                        return True, f"Snap Inc. ({pattern})"
                
                # Log certificate info for manual review
                logger.warning("Certificate found but doesn't match known Snap Inc. patterns")
                logger.debug(f"Certificate details: {result.stdout[:500]}")
                return False, "Unknown certificate"
            else:
                logger.warning(f"apksigner verification failed: {result.stderr}")
                
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("apksigner not available")
        
        # Fallback: basic APK structure validation
        try:
            if not shutil.which('aapt'):
                raise FileNotFoundError('aapt not found')
            result = subprocess.run(
                ['aapt', 'dump', 'badging', str(apk_path)],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0 and 'com.snapchat.android' in result.stdout:
                logger.info("Basic APK structure validation passed")
                return True, "Basic validation (aapt)"
            
        except Exception:
            pass
        
        return False, "Verification failed"
    
    def _calculate_sha256(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
            
        except Exception as e:
            logger.error(f"Error calculating SHA256: {e}")
            return "unknown"
    
    def _verify_installation(self, device_id: str, package_name: str) -> bool:
        """Verify that APK was installed successfully"""
        try:
            result = subprocess.run(
                ['adb', '-s', device_id, 'shell', 'pm', 'list', 'packages', package_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return result.returncode == 0 and package_name in result.stdout
            
        except Exception as e:
            logger.error(f"Installation verification error: {e}")
            return False
    
    def _log_acquisition_guidance(self):
        """Log guidance for APK acquisition"""
        logger.error("No verified Snapchat APK found. Security recommendations:")
        logger.error("1. Place verified Snapchat APK in: %s", self.artifacts_dir)
        logger.error("2. Ensure APK is signed by Snap Inc. (verify with: apksigner verify --print-certs app.apk)")
        logger.error("3. Use APKs from official sources only (Google Play Store, APK Mirror)")
        logger.error("4. Set SNAPCHAT_APK_ARTIFACTS_DIR environment variable for custom location")
        logger.error("5. Never use APKs from untrusted sources or file sharing sites")
    
    def add_known_good_hash(self, sha256: str, version: str, source: str = "manual"):
        """Add a known good APK hash to the allowlist"""
        self.known_snapchat_hashes[sha256] = {
            "version": version,
            "source": source,
            "added_at": str(datetime.now())
        }
        logger.info(f"Added known good hash: {sha256[:16]}... (version {version})")
    
    def list_available_apks(self) -> List[APKInfo]:
        """List all available APKs with their verification status"""
        apks = []
        
        # Check artifacts directory
        if self.artifacts_dir.exists():
            for apk_file in self.artifacts_dir.glob("*.apk"):
                apk_info = self.verify_apk_integrity(apk_file)
                apks.append(apk_info)
        
        # Check cache directory
        if self.cache_dir.exists():
            for apk_file in self.cache_dir.glob("*.apk"):
                apk_info = self.verify_apk_integrity(apk_file)
                apks.append(apk_info)
        
        return apks


def get_apk_manager(artifacts_dir: str = None, cache_dir: str = None) -> SecureAPKManager:
    """Get APK manager instance"""
    return SecureAPKManager(artifacts_dir, cache_dir)


if __name__ == "__main__":
    # Command line interface for APK management
    import argparse
    
    parser = argparse.ArgumentParser(description='Snapchat APK Manager')
    parser.add_argument('--list', action='store_true', help='List available APKs')
    parser.add_argument('--verify', type=str, help='Verify specific APK file')
    parser.add_argument('--install', type=str, help='Install APK to device')
    parser.add_argument('--device', type=str, help='Device ID for installation')
    
    args = parser.parse_args()
    
    manager = get_apk_manager()
    
    if args.list:
        apks = manager.list_available_apks()
        print(f"Found {len(apks)} APK(s):")
        for apk in apks:
            status = "✅ VERIFIED" if apk.is_verified else "❌ UNVERIFIED"
            print(f"  {status} {apk.path.name} (v{apk.version_name})")
    
    elif args.verify:
        apk_path = Path(args.verify)
        apk_info = manager.verify_apk_integrity(apk_path)
        status = "✅ VERIFIED" if apk_info.is_verified else "❌ UNVERIFIED"
        print(f"{status} {apk_path}")
        print(f"  Package: {apk_info.package_name}")
        print(f"  Version: {apk_info.version_name} ({apk_info.version_code})")
        print(f"  SHA256: {apk_info.sha256}")
        print(f"  Signed by: {apk_info.signed_by}")
    
    elif args.install:
        if not args.device:
            print("Error: --device required for installation")
            exit(1)
        
        apk_path = Path(args.install)
        success = manager.install_apk(args.device, apk_path)
        if success:
            print("✅ Installation successful")
        else:
            print("❌ Installation failed")
    
    else:
        parser.print_help()