"""
Temporal Worker for Anti-Bot Security Workflows
Production-ready worker configuration with enhanced error handling and monitoring
"""

import asyncio
import logging
from datetime import timedelta
from typing import Dict, Any
import os
from temporalio import worker, activity
from temporalio.client import Client
from temporalio.worker import UnsandboxedWorkflowRunner
from temporalio.common import RetryPolicy

# Import workflow and activity definitions
from workflow_definitions import (
    ComprehensiveSecurityAssessmentWorkflow,
    AdaptiveSecurityMonitoringWorkflow,
    ThreatResponseOrchestrationWorkflow,
    analyze_behavioral_patterns,
    analyze_biometric_patterns,
    query_fraud_intelligence,
    aggregate_risk_scores,
    determine_final_actions,
    store_assessment_data,
    capture_behavior_snapshot,
    detect_behavioral_anomalies,
    trigger_immediate_security_action,
    execute_immediate_block,
    send_security_alert,
    initiate_threat_investigation,
    share_threat_intelligence,
    execute_threat_remediation,
    execute_emergency_response,
    initiate_enhanced_verification,
    apply_security_challenge
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedTemporalWorker:
    """
    Enhanced Temporal worker with production-ready configuration
    """
    
    def __init__(self, temporal_server_url: str = None, namespace: str = "default"):
        self.temporal_server_url = temporal_server_url or os.getenv('TEMPORAL_SERVER_URL', 'localhost:7233')
        self.namespace = namespace
        self.client = None
        self.worker = None
        
    async def initialize(self) -> None:
        """Initialize Temporal client and worker"""
        try:
            logger.info(f"Connecting to Temporal server at {self.temporal_server_url}")
            
            # Create Temporal client
            self.client = await Client.connect(
                self.temporal_server_url,
                namespace=self.namespace
            )
            
            # Configure worker with production settings
            self.worker = worker.Worker(
                self.client,
                task_queue="antibot-security-queue",
                workflows=[
                    ComprehensiveSecurityAssessmentWorkflow,
                    AdaptiveSecurityMonitoringWorkflow,
                    ThreatResponseOrchestrationWorkflow
                ],
                activities=[
                    analyze_behavioral_patterns,
                    analyze_biometric_patterns,
                    query_fraud_intelligence,
                    aggregate_risk_scores,
                    determine_final_actions,
                    store_assessment_data,
                    capture_behavior_snapshot,
                    detect_behavioral_anomalies,
                    trigger_immediate_security_action,
                    execute_immediate_block,
                    send_security_alert,
                    initiate_threat_investigation,
                    share_threat_intelligence,
                    execute_threat_remediation,
                    execute_emergency_response,
                    initiate_enhanced_verification,
                    apply_security_challenge
                ],
                workflow_runner=UnsandboxedWorkflowRunner(),  # For development - use sandboxed in production
                max_concurrent_workflow_task_polls=10,
                max_concurrent_activity_task_polls=20,
                max_concurrent_local_activity_executions=50,
                max_heartbeat_throttle_interval=timedelta(seconds=30),
                default_heartbeat_throttle_interval=timedelta(seconds=5)
            )
            
            logger.info("Temporal worker initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Temporal worker: {e}")
            raise
    
    async def start(self) -> None:
        """Start the worker"""
        if not self.worker:
            raise RuntimeError("Worker not initialized. Call initialize() first.")
        
        logger.info("Starting Temporal worker...")
        await self.worker.run()
    
    async def shutdown(self) -> None:
        """Graceful shutdown"""
        try:
            if self.worker:
                logger.info("Shutting down Temporal worker...")
                # Worker shutdown is handled automatically when the context exits
                
            if self.client:
                await self.client.close()
                
            logger.info("Temporal worker shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during worker shutdown: {e}")


class WorkflowOrchestrator:
    """
    High-level orchestrator for triggering workflows
    """
    
    def __init__(self, temporal_client: Client):
        self.client = temporal_client
        
    async def start_security_assessment(self, request_data: Dict[str, Any]) -> str:
        """
        Start comprehensive security assessment workflow
        """
        try:
            from workflow_definitions import SecurityAssessmentRequest
            
            # Convert request data to workflow input
            assessment_request = SecurityAssessmentRequest(
                session_id=request_data['session_id'],
                device_fingerprint=request_data['device_fingerprint'],
                behavioral_data=request_data['behavioral_data'],
                tls_fingerprint=request_data.get('tls_fingerprint'),
                network_metadata=request_data.get('network_metadata')
            )
            
            # Start workflow
            workflow_handle = await self.client.start_workflow(
                ComprehensiveSecurityAssessmentWorkflow.run,
                assessment_request,
                id=f"security-assessment-{request_data['session_id']}-{int(asyncio.get_event_loop().time())}",
                task_queue="antibot-security-queue",
                execution_timeout=timedelta(minutes=10),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    backoff_coefficient=2.0,
                    maximum_attempts=3,
                    maximum_interval=timedelta(minutes=1)
                )
            )
            
            logger.info(f"Started security assessment workflow: {workflow_handle.id}")
            return workflow_handle.id
            
        except Exception as e:
            logger.error(f"Failed to start security assessment workflow: {e}")
            raise
    
    async def start_adaptive_monitoring(self, session_id: str, duration_minutes: int = 60) -> str:
        """
        Start adaptive security monitoring workflow
        """
        try:
            workflow_handle = await self.client.start_workflow(
                AdaptiveSecurityMonitoringWorkflow.run,
                session_id,
                duration_minutes,
                id=f"adaptive-monitoring-{session_id}-{int(asyncio.get_event_loop().time())}",
                task_queue="antibot-security-queue",
                execution_timeout=timedelta(minutes=duration_minutes + 10),
                cron_schedule="*/30 * * * * *"  # Check every 30 seconds
            )
            
            logger.info(f"Started adaptive monitoring workflow: {workflow_handle.id}")
            return workflow_handle.id
            
        except Exception as e:
            logger.error(f"Failed to start adaptive monitoring workflow: {e}")
            raise
    
    async def start_threat_response(self, threat_data: Dict[str, Any]) -> str:
        """
        Start threat response orchestration workflow
        """
        try:
            workflow_handle = await self.client.start_workflow(
                ThreatResponseOrchestrationWorkflow.run,
                threat_data,
                id=f"threat-response-{threat_data.get('session_id', 'unknown')}-{int(asyncio.get_event_loop().time())}",
                task_queue="antibot-security-queue",
                execution_timeout=timedelta(hours=1),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=2),
                    backoff_coefficient=2.0,
                    maximum_attempts=5,
                    maximum_interval=timedelta(minutes=5)
                )
            )
            
            logger.info(f"Started threat response workflow: {workflow_handle.id}")
            return workflow_handle.id
            
        except Exception as e:
            logger.error(f"Failed to start threat response workflow: {e}")
            raise
    
    async def get_workflow_result(self, workflow_id: str) -> Any:
        """
        Get workflow execution result
        """
        try:
            workflow_handle = self.client.get_workflow_handle(workflow_id)
            result = await workflow_handle.result()
            return result
            
        except Exception as e:
            logger.error(f"Failed to get workflow result for {workflow_id}: {e}")
            raise
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """
        Cancel running workflow
        """
        try:
            workflow_handle = self.client.get_workflow_handle(workflow_id)
            await workflow_handle.cancel()
            logger.info(f"Cancelled workflow: {workflow_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel workflow {workflow_id}: {e}")
            return False


class WorkerHealthMonitor:
    """
    Monitor worker health and performance metrics
    """
    
    def __init__(self, worker: EnhancedTemporalWorker):
        self.worker = worker
        self.metrics = {
            'workflows_executed': 0,
            'activities_executed': 0,
            'errors_count': 0,
            'avg_workflow_duration': 0.0,
            'last_health_check': None
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check
        """
        try:
            health_status = {
                'status': 'healthy',
                'temporal_connection': 'connected' if self.worker.client else 'disconnected',
                'worker_running': 'running' if self.worker.worker else 'stopped',
                'metrics': self.metrics,
                'timestamp': asyncio.get_event_loop().time()
            }
            
            # Test basic connectivity
            if self.worker.client:
                try:
                    # Attempt to list workflow executions to test connection
                    async for execution in self.worker.client.list_workflows():
                        break  # Just test that we can connect
                    health_status['temporal_connection'] = 'connected'
                except Exception as e:
                    health_status['temporal_connection'] = f'error: {str(e)}'
                    health_status['status'] = 'degraded'
            
            self.metrics['last_health_check'] = health_status['timestamp']
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': asyncio.get_event_loop().time()
            }
    
    def update_metrics(self, metric_type: str, value: Any = None) -> None:
        """
        Update performance metrics
        """
        try:
            if metric_type == 'workflow_executed':
                self.metrics['workflows_executed'] += 1
            elif metric_type == 'activity_executed':
                self.metrics['activities_executed'] += 1
            elif metric_type == 'error_occurred':
                self.metrics['errors_count'] += 1
            elif metric_type == 'workflow_duration' and value is not None:
                # Update running average
                current_avg = self.metrics['avg_workflow_duration']
                count = self.metrics['workflows_executed']
                self.metrics['avg_workflow_duration'] = (current_avg * (count - 1) + value) / count
                
        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")


async def main():
    """
    Main entry point for worker
    """
    # Configuration from environment
    temporal_server_url = os.getenv('TEMPORAL_SERVER_URL', 'localhost:7233')
    namespace = os.getenv('TEMPORAL_NAMESPACE', 'default')
    
    # Initialize worker
    worker_instance = EnhancedTemporalWorker(temporal_server_url, namespace)
    health_monitor = WorkerHealthMonitor(worker_instance)
    
    try:
        # Initialize and start worker
        await worker_instance.initialize()
        
        # Perform initial health check
        health_status = await health_monitor.health_check()
        logger.info(f"Initial health check: {health_status}")
        
        # Start worker (this blocks until shutdown)
        await worker_instance.start()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Worker failed with error: {e}")
        raise
    finally:
        # Graceful shutdown
        await worker_instance.shutdown()
        logger.info("Worker shutdown completed")


if __name__ == "__main__":
    # Run worker
    asyncio.run(main())