import numpy as np
from src.rl.environment import DecisionEnv, ACTION_MAP


def test_env_creation():
    env = DecisionEnv(max_steps=10)
    assert env.observation_space.shape == (8,)
    assert env.action_space.n == 4


def test_reset():
    env = DecisionEnv(max_steps=10)
    obs, info = env.reset(seed=42)
    assert obs.shape == (8,)
    assert all(0.0 <= v <= 1.0 for v in obs)


def test_step():
    env = DecisionEnv(max_steps=10)
    env.reset(seed=42)
    obs, reward, terminated, truncated, info = env.step(0)
    assert obs.shape == (8,)
    assert isinstance(reward, float)
    assert info["action_taken"] == "escalate_to_maintenance"
    assert not truncated


def test_termination():
    env = DecisionEnv(max_steps=3)
    env.reset(seed=42)
    for _ in range(2):
        _, _, terminated, _, _ = env.step(0)
        assert not terminated
    _, _, terminated, _, _ = env.step(0)
    assert terminated


def test_reward_critical_escalation():
    env = DecisionEnv()
    critical_state = np.array([0.9, 0.5, 0.0, 0.1, 0.8, 0.5, 0.4, 0.2], dtype=np.float32)
    reward = env._compute_reward(0, critical_state)  # escalate
    assert reward == 10.0


def test_reward_ignore_noise():
    env = DecisionEnv()
    noise_state = np.array([0.1, 0.1, 0.0, 0.1, 0.2, 0.1, 0.1, 0.8], dtype=np.float32)
    reward = env._compute_reward(3, noise_state)  # ignore
    assert reward == 3.0


def test_reward_missed_critical():
    env = DecisionEnv()
    critical_state = np.array([0.9, 0.5, 0.0, 0.1, 0.8, 0.5, 0.4, 0.2], dtype=np.float32)
    reward = env._compute_reward(3, critical_state)  # ignore a critical event
    assert reward == -15.0


def test_reward_burst_scaleup():
    env = DecisionEnv()
    burst_state = np.array([0.4, 0.9, 1.0, 0.3, 0.6, 0.4, 0.8, 0.05], dtype=np.float32)
    reward = env._compute_reward(2, burst_state)  # scale_up
    assert reward == 8.0


def test_all_actions_defined():
    assert len(ACTION_MAP) == 4
    assert set(ACTION_MAP.values()) == {"escalate_to_maintenance", "auto_resolve", "scale_up", "ignore"}
