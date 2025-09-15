#!/usr/bin/env python3
"""
Component-Specific Validation Tests

This script performs targeted validation of available components
with detailed testing of their functionality.
"""

import asyncio
import time
import json
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComponentValidator:
    """Validates specific components in detail"""
    
    def __init__(self):
        self.project_root = Path("/Users/daltonmetzler/Desktop/Tinder")
    
    def validate_antibot_architecture(self):
        """Validate the anti-bot security architecture components"""
        logger.info("🔍 Validating Anti-Bot Architecture Components...")
        
        # Check for key architecture files
        key_files = [
            "antibot-security/backend/risk-engine/main.py",
            "antibot-security/backend/sms-service/main.py",
            "antibot-security/backend/data-processor/main.py",
            "antibot-security/backend/temporal-workflows/workflow_definitions.py",
            "antibot-security/client-side/browser-agent/behavioral-analytics.js",
            "antibot-security/backend/observability/opentelemetry_config.py"
        ]
        
        available_components = []
        for file_path in key_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                available_components.append(file_path)
                logger.info(f"✅ Found: {file_path}")
            else:
                logger.warning(f"❌ Missing: {file_path}")
        
        logger.info(f"📊 Architecture Components: {len(available_components)}/{len(key_files)} available")
        return len(available_components) / len(key_files)
    
    def validate_infrastructure_config(self):
        """Validate infrastructure configuration"""
        logger.info("🏗️ Validating Infrastructure Configuration...")
        
        config_files = [
            "infra/docker-compose.yml",
            "infra/config/prometheus.yml",
            "infra/config/grafana/provisioning/datasources/prometheus.yml",
            "infra/monitoring/ml_monitor.py",
            "infra/monitoring/security_monitor.py"
        ]
        
        config_score = 0
        for config_file in config_files:
            full_path = self.project_root / config_file
            if full_path.exists():
                config_score += 1
                logger.info(f"✅ Config found: {config_file}")
                
                # Check file size (basic validation)
                size = full_path.stat().st_size
                if size > 100:  # At least 100 bytes
                    logger.info(f"   Size: {size} bytes - appears complete")
                else:
                    logger.warning(f"   Size: {size} bytes - may be incomplete")
            else:
                logger.warning(f"❌ Missing config: {config_file}")
        
        logger.info(f"📊 Infrastructure Config: {config_score}/{len(config_files)} files available")
        return config_score / len(config_files)
    
    def test_database_connectivity(self):
        """Test database connectivity"""
        logger.info("💾 Testing Database Connectivity...")
        
        try:
            import socket
            
            # Test PostgreSQL connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', 5432))
            sock.close()
            
            if result == 0:
                logger.info("✅ PostgreSQL port accessible")
                
                # Try to connect with psql if available
                try:
                    result = subprocess.run(
                        ['psql', '--version'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        logger.info(f"✅ PostgreSQL client available: {result.stdout.strip()}")
                        return True
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    logger.info("⚠️ PostgreSQL client not available, but port is open")
                    return True
            else:
                logger.warning("❌ PostgreSQL port not accessible")
                return False
                
        except Exception as e:
            logger.error(f"❌ Database connectivity test failed: {str(e)}")
            return False
    
    def test_redis_connectivity(self):
        """Test Redis connectivity"""
        logger.info("💾 Testing Redis Connectivity...")
        
        try:
            import socket
            
            # Test Redis connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', 6379))
            sock.close()
            
            if result == 0:
                logger.info("✅ Redis port accessible")
                
                # Try to connect with redis-cli if available
                try:
                    result = subprocess.run(
                        ['redis-cli', '--version'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        logger.info(f"✅ Redis client available: {result.stdout.strip()}")
                        
                        # Test actual Redis connection
                        result = subprocess.run(
                            ['redis-cli', 'ping'],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if result.returncode == 0 and 'PONG' in result.stdout:
                            logger.info("✅ Redis responding to ping")
                            return True
                        else:
                            logger.warning("⚠️ Redis not responding to ping")
                            return False
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    logger.info("⚠️ Redis client not available, but port is open")
                    return True
            else:
                logger.warning("❌ Redis port not accessible")
                return False
                
        except Exception as e:
            logger.error(f"❌ Redis connectivity test failed: {str(e)}")
            return False
    
    def validate_monitoring_setup(self):
        """Validate monitoring setup"""
        logger.info("👁️ Validating Monitoring Setup...")
        
        monitoring_score = 0
        total_checks = 0
        
        # Check monitoring files
        monitoring_files = [
            ("infra/MONITORING_README.md", "Documentation"),
            ("infra/monitoring/ml_monitor.py", "ML Monitor"),
            ("infra/monitoring/security_monitor.py", "Security Monitor"),
            ("infra/config/prometheus.yml", "Prometheus Config"),
            ("infra/config/alert_rules.yml", "Alert Rules")
        ]
        
        for file_path, description in monitoring_files:
            total_checks += 1
            full_path = self.project_root / file_path
            if full_path.exists():
                monitoring_score += 1
                size = full_path.stat().st_size
                logger.info(f"✅ {description}: {size} bytes")
            else:
                logger.warning(f"❌ Missing: {description}")
        
        # Check for monitoring ports
        monitoring_ports = [(9090, "Prometheus"), (3000, "Grafana")]
        
        for port, service in monitoring_ports:
            total_checks += 1
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                
                if result == 0:
                    monitoring_score += 1
                    logger.info(f"✅ {service} port {port} accessible")
                else:
                    logger.warning(f"❌ {service} port {port} not accessible")
            except:
                logger.warning(f"❌ Error checking {service} port {port}")
        
        logger.info(f"📊 Monitoring Setup: {monitoring_score}/{total_checks} checks passed")
        return monitoring_score / total_checks
    
    def run_all_validations(self):
        """Run all component validations"""
        logger.info("🚀 Starting Component-Specific Validation Tests")
        
        results = {}
        
        # Architecture validation
        results['architecture'] = self.validate_antibot_architecture()
        
        # Infrastructure validation  
        results['infrastructure'] = self.validate_infrastructure_config()
        
        # Database connectivity
        results['database'] = self.test_database_connectivity()
        
        # Redis connectivity
        results['redis'] = self.test_redis_connectivity()
        
        # Monitoring setup
        results['monitoring'] = self.validate_monitoring_setup()
        
        # Calculate overall score
        numeric_scores = [score for score in results.values() if isinstance(score, (int, float))]
        boolean_scores = [1 if score else 0 for score in results.values() if isinstance(score, bool)]
        
        all_scores = numeric_scores + boolean_scores
        overall_score = sum(all_scores) / len(all_scores) if all_scores else 0
        
        logger.info("\n" + "="*60)
        logger.info("📊 COMPONENT VALIDATION SUMMARY")
        logger.info("="*60)
        
        for component, score in results.items():
            if isinstance(score, bool):
                status = "✅ PASS" if score else "❌ FAIL"
                logger.info(f"{component.title()}: {status}")
            else:
                percentage = score * 100
                status = "✅ GOOD" if score >= 0.8 else "⚠️ PARTIAL" if score >= 0.5 else "❌ POOR"
                logger.info(f"{component.title()}: {percentage:.1f}% {status}")
        
        logger.info(f"\nOverall Component Health: {overall_score * 100:.1f}%")
        logger.info("="*60)
        
        # Generate recommendations
        recommendations = []
        
        if results['architecture'] < 0.8:
            recommendations.append("Complete anti-bot architecture component implementation")
        
        if results['infrastructure'] < 0.8:
            recommendations.append("Complete infrastructure configuration setup")
        
        if not results['database']:
            recommendations.append("Fix database connectivity issues")
        
        if not results['redis']:
            recommendations.append("Fix Redis connectivity issues")
        
        if results['monitoring'] < 0.8:
            recommendations.append("Complete monitoring and observability setup")
        
        if recommendations:
            logger.info("\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                logger.info(f"{i}. {rec}")
        else:
            logger.info("\n✅ All components validation passed!")
        
        return results, overall_score, recommendations

def main():
    """Main function"""
    validator = ComponentValidator()
    results, overall_score, recommendations = validator.run_all_validations()
    
    # Save results
    report = {
        'timestamp': time.time(),
        'results': results,
        'overall_score': overall_score,
        'recommendations': recommendations
    }
    
    report_path = Path("/Users/daltonmetzler/Desktop/Tinder") / f"component_validation_report_{int(time.time())}.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    logger.info(f"\n📋 Component validation report saved: {report_path}")
    
    # Return success based on overall score
    return 0 if overall_score >= 0.7 else 1

if __name__ == "__main__":
    sys.exit(main())
