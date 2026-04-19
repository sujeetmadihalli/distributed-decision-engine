"""
Ray RLlib training script for the Decision Engine RL optimizer.

Trains a PPO agent that learns optimal routing decisions based on
telemetry features and LLM confidence scores.
"""

import ray
from ray.rllib.algorithms.ppo import PPOConfig
from ray.tune.registry import register_env
import os
import json
import logging

from src.rl.environment import DecisionEnv

logger = logging.getLogger(__name__)

CHECKPOINT_DIR = os.getenv("RL_CHECKPOINT_DIR", "checkpoints/rl")
TRAINING_ITERATIONS = int(os.getenv("RL_TRAINING_ITERATIONS", "50"))


def env_creator(env_config):
    return DecisionEnv(max_steps=env_config.get("max_steps", 200))


def train(num_iterations: int = TRAINING_ITERATIONS) -> str:
    ray.init(ignore_reinit_error=True, num_cpus=4)

    register_env("decision_env", env_creator)

    config = (
        PPOConfig()
        .environment("decision_env", env_config={"max_steps": 200})
        .framework("torch")
        .training(
            lr=3e-4,
            gamma=0.99,
            lambda_=0.95,
            clip_param=0.2,
            entropy_coeff=0.01,
            vf_loss_coeff=0.5,
            train_batch_size=2048,
            sgd_minibatch_size=256,
            num_sgd_iter=10,
        )
        .rollouts(
            num_rollout_workers=2,
            rollout_fragment_length=256,
        )
        .resources(num_gpus=0)
    )

    algo = config.build()

    best_reward = float("-inf")
    best_checkpoint = None
    history = []

    for i in range(num_iterations):
        result = algo.train()
        mean_reward = result["episode_reward_mean"]
        episode_len = result["episode_len_mean"]

        history.append({
            "iteration": i + 1,
            "mean_reward": round(mean_reward, 2),
            "episode_length": round(episode_len, 1),
            "timesteps_total": result["timesteps_total"],
        })

        logger.info(
            "Iteration %d/%d — reward: %.2f, length: %.1f, timesteps: %d",
            i + 1, num_iterations, mean_reward, episode_len, result["timesteps_total"],
        )

        if mean_reward > best_reward:
            best_reward = mean_reward
            os.makedirs(CHECKPOINT_DIR, exist_ok=True)
            best_checkpoint = algo.save(CHECKPOINT_DIR)
            logger.info("New best model saved: %.2f → %s", best_reward, best_checkpoint)

    algo.stop()

    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    with open(os.path.join(CHECKPOINT_DIR, "training_history.json"), "w") as f:
        json.dump({"best_reward": best_reward, "checkpoint": str(best_checkpoint), "history": history}, f, indent=2)

    ray.shutdown()
    return str(best_checkpoint)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    checkpoint = train()
    print(f"Training complete. Best checkpoint: {checkpoint}")


if __name__ == "__main__":
    main()
