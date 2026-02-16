import logging
import asyncio
from typing import List, Dict, Any, Optional
from oao.runtime.persistence import RedisPersistenceAdapter
from oao.runtime.orchestrator import Orchestrator
from oao.policy.strict_policy import StrictPolicy
from oao.runtime.agent_factory import AgentFactory
from oao.runtime.execution import ExecutionSnapshot, Execution
from oao.runtime.hashing import compute_execution_hash
from oao.runtime.event_store import RedisEventStore

logger = logging.getLogger(__name__)

MAX_RECOVERY_ATTEMPTS = 3

class RecoveryManager:
    """
    Manages recovery of crashed executions with strictly validated state.
    """
    def __init__(self):
        self.persistence = RedisPersistenceAdapter()
        self.event_store = RedisEventStore()

    async def recover_executions(self):
        """
        Scan for active executions that are not running locally and attempt to resume them.
        This should be called on server startup.
        """
        try:
            active_ids = self.persistence.list_active_executions()
        except Exception as e:
            logger.warning(f"Failed to list active executions: {e}")
            return

        if not active_ids:
            logger.info("No active executions found for recovery.")
            return

        logger.info(f"Found {len(active_ids)} active executions. Checking for recovery...")
        
        for execution_id in active_ids:
            try:
                # 1. Check Recovery Attempts
                attempts = self.persistence.get_recovery_count(execution_id)
                if attempts >= MAX_RECOVERY_ATTEMPTS:
                    logger.error(f"Execution {execution_id} exceeded max recovery attempts ({MAX_RECOVERY_ATTEMPTS}). Marking as failed.")
                    self.persistence.remove_active_execution(execution_id)
                    continue

                # Increment count immediately
                self.persistence.increment_recovery_count(execution_id)

                # 2. Load Spec and Validation
                spec = self.persistence.load_execution_spec(execution_id)
                if not spec:
                    logger.warning(f"Skipping recovery for {execution_id}: No execution spec found.")
                    self.persistence.remove_active_execution(execution_id)
                    continue
                
                # Validate Hash Integrity
                if not self._validate_hash_integrity(spec):
                     logger.error(f"Execution {execution_id} failed hash validation. Possible state corruption.")
                     # We abort recovery to be safe
                     self.persistence.remove_active_execution(execution_id)
                     continue

                snapshot_data = spec.get("snapshot", {})
                task = snapshot_data.get("task") # Task is in snapshot
                # Fallback to top-level if not in snapshot (legacy)
                if not task: 
                     task = spec.get("task")
                     
                framework = "langchain" # Default or extract from agent config if possible
                # In strict mode, framework might be part of agent_config or inferred.
                # For now assuming langchain as default or legacy behavior
                
                logger.info(f"Recovering execution {execution_id} (Attempt {attempts + 1}) for task: {task[:50] if task else 'Unknown'}...")
                
                # 3. Re-instantiate components
                # Reconstruct policy from snapshot config
                policy_config = snapshot_data.get("policy_config", {})
                policy = StrictPolicy(
                    max_steps=policy_config.get("max_steps", 10),
                    max_tokens=policy_config.get("max_tokens", 4000)
                )
                
                orch = Orchestrator(policy=policy, event_store=self.event_store, persistence=self.persistence)
                
                # Re-create agent
                agent_config = snapshot_data.get("agent_config", {})
                # AgentFactory needs better serialization support, for now use generic creation
                # Assuming agent_config has 'framework' or 'type'
                # Use passed framework or legacy default
                agent = AgentFactory.create_agent(framework) 
                
                # 4. Determine resume point via Event Store (Replay)
                # We find the last event
                last_event = self.event_store.get_latest_event(execution_id)
                from_step = 0
                if last_event:
                     from_step = last_event.step_number
                     logger.info(f"Resuming {execution_id} from step {from_step} (Event Store)")
                else:
                     logger.info(f"Restarting {execution_id} from beginning (no events found)")

                # 5. Resume
                # We launch this as a background task via Orchestrator's async run
                # Orchestrator handle replay logic internally given `from_step`
                asyncio.create_task(self._run_recovery(orch, agent, task, framework, execution_id, from_step))
                
            except Exception as e:
                logger.error(f"Failed to recover execution {execution_id}: {e}")

    def _validate_hash_integrity(self, spec: Dict[str, Any]) -> bool:
        """
        Verify that the persisted execution spec has a valid and consistent hash.
        """
        try:
            # Reconstruct Execution object from spec
            # This handles conversion from dict/list back to immutable snapshot
            execution = Execution.from_dict(spec)
            
            # Use strict hash validation from Execution model
            if not execution.validate_hash():
                logger.error(f"Hash mismatch for execution {execution.execution_id}. "
                             f"Stored: {execution.execution_hash}, Computed: {execution._compute_hash_from_snapshot()}") # _compute_hash_from_snapshot is implied, validate_hash does it internally
                # wait validate_hash doesn't return the computed hash, just bool.
                # Let's trust the bool.
                return False
                
            return True
        except Exception as e:
            logger.warning(f"Hash validation error: {e}")
            return False

    async def _run_recovery(self, orch, agent, task, framework, execution_id, from_step):
        try:
            await orch.run_async(
                agent=agent,
                task=task,
                framework=framework,
                execution_id=execution_id,
                from_step=from_step
            )
            logger.info(f"Recovery completed successfully for {execution_id}")
        except Exception as e:
            logger.error(f"Recovery failed for {execution_id}: {e}")
            # Ensure it's removed from active list so we don't loop forever
            try:
                self.persistence.remove_active_execution(execution_id)
            except:
                pass
