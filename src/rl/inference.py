"""
RL inference — loads a trained checkpoint and provides action recommendations
that the orchestrator can use alongside (or instead of) the LLM decision.
"""

import numpy as np
import os
import logging

logger = logging.getLogger(__name__)

CHECKPOINT_DIR = os.getenv("RL_CHECKPOINT_DIR", "checkpoints/rl")
USE_RL = os.getenv("USE_RL", "false").lower() == "true"


from src.rl.environment import ACTION_MAP


class RLAdvisor:
    def __init__(self, checkpoint_path: str | None = None):
        self.algo = None
        self.enabled = USE_RL

        if not self.enabled:
            logger.info("RL advisor disabled (set USE_RL=true to enable)")
            return

        try:
            import ray
            from ray.rllib.algorithms.ppo import PPO
            from ray.tune.registry import register_env
            from src.rl.environment import DecisionEnv

            ray.init(ignore_reinit_error=True, num_cpus=1)
            register_env("decision_env", lambda cfg: DecisionEnv())

            path = checkpoint_path or self._find_latest_checkpoint()
            if path:
                self.algo = PPO.from_checkpoint(path)
                logger.info("RL advisor loaded from %s", path)
            else:
                logger.warning("No RL checkpoint found — advisor disabled")
                self.enabled = False
        except ImportError:
            logger.warning("Ray not installed — RL advisor disabled")
            self.enabled = False
        except Exception:
            logger.exception("Failed to load RL advisor")
            self.enabled = False

    def _find_latest_checkpoint(self) -> str | None:
        if not os.path.isdir(CHECKPOINT_DIR):
            return None
        checkpoints = [
            os.path.join(CHECKPOINT_DIR, d)
            for d in os.listdir(CHECKPOINT_DIR)
            if os.path.isdir(os.path.join(CHECKPOINT_DIR, d)) and d.startswith("checkpoint")
        ]
        return max(checkpoints, key=os.path.getmtime) if checkpoints else None

    def recommend(self, observation: dict) -> dict | None:
        if not self.enabled or not self.algo:
            return None

        try:
            obs = np.array([
                observation.get("severity", 0.5),
                observation.get("event_rate", 0.3),
                float(observation.get("is_burst", False)),
                observation.get("historical_matches", 0.0) / 10.0,
                observation.get("llm_confidence", 0.5),
                observation.get("payload_complexity", 0.3),
                observation.get("source_frequency", 0.3),
                observation.get("time_since_last", 0.5),
            ], dtype=np.float32)

            action = self.algo.compute_single_action(obs)
            return {
                "rl_action": ACTION_MAP[int(action)],
                "rl_action_id": int(action),
                "source": "rl_ppo_v1",
            }
        except Exception:
            logger.exception("RL inference failed")
            return None
