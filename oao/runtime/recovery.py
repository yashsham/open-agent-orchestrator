import logging
import asyncio
from typing import List, Dict, Any, Optional
from oao.runtime.persistence import RedisPersistenceAdapter
from oao.runtime.orchestrator import Orchestrator
from oao.policy.strict_policy import StrictPolicy
from oao.runtime.agent_factory import AgentFactory

logger = logging.getLogger(__name__)

class RecoveryManager:
    """
    Manages recovery of crashed executions.
    """
    def __init__(self):
        self.persistence = RedisPersistenceAdapter()

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
                # 1. Load Spec
                spec = self.persistence.load_execution_spec(execution_id)
                if not spec:
                    logger.warning(f"Skipping recovery for {execution_id}: No execution spec found.")
                    # If spec is missing, we can't recover. Identify as lost.
                    self.persistence.remove_active_execution(execution_id)
                    continue

                task = spec.get("task")
                framework = spec.get("framework", "langchain")
                
                logger.info(f"Recovering execution {execution_id} for task: {task[:50] if task else 'Unknown'}...")
                
                # 2. Re-instantiate components
                policy = StrictPolicy(
                    max_steps=spec.get("max_steps", 10),
                    max_tokens=spec.get("max_tokens", 4000)
                )
                
                orch = Orchestrator(policy=policy)
                # Note: AgentFactory relies on installed packages. 
                # If environment changed, this might fail.
                agent = AgentFactory.create_agent(framework)
                
                # 3. Determine resume point
                history = self.persistence.get_execution_history(execution_id)
                from_step = None
                
                if history:
                    # Find the last successfully saved step
                    # history contains steps [0, 1, 2...]
                    # We resume from the last saved state.
                    last_step_record = max(history, key=lambda s: s.get("step_number", 0))
                    from_step = last_step_record.get("step_number")
                    logger.info(f"Resuming {execution_id} from step {from_step}")
                else:
                    logger.info(f"Restarting {execution_id} from beginning (no history found)")

                # 4. Resume
                # We launch this as a background task so we don't block server startup
                asyncio.create_task(self._run_recovery(orch, agent, task, framework, execution_id, from_step))
                
            except Exception as e:
                logger.error(f"Failed to recover execution {execution_id}: {e}")

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
