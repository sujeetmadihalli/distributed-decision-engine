"""
Custom Gymnasium environment for the Decision Engine.

The RL agent observes telemetry features + LLM confidence, selects an action
(escalate, auto-resolve, scale-up, ignore), and gets rewarded based on
simulated outcome quality.
"""

import gymnasium as gym
import numpy as np
from gymnasium import spaces


ACTION_MAP = {
    0: "escalate_to_maintenance",
    1: "auto_resolve",
    2: "scale_up",
    3: "ignore",
}

REVERSE_ACTION_MAP = {v: k for k, v in ACTION_MAP.items()}


class DecisionEnv(gym.Env):
    """
    Observation space (8 floats):
        [0] severity          — 0.0 (low) to 1.0 (critical)
        [1] event_rate         — normalized events/sec in window
        [2] is_burst           — 0.0 or 1.0
        [3] historical_matches — normalized count of similar past events
        [4] llm_confidence     — 0.0 to 1.0 from orchestrator
        [5] payload_complexity — normalized count of payload keys
        [6] source_frequency   — how often this source sends events (normalized)
        [7] time_since_last    — seconds since last event from same source (normalized)

    Action space: Discrete(4) — see ACTION_MAP

    Reward:
        Correct escalation of critical event:  +10
        Correct auto-resolve of benign event:  +5
        Correct scale-up for burst:            +8
        Correct ignore of noise:               +3
        Wrong action (missed critical):        -15
        Wrong action (false escalation):       -5
        Efficiency bonus (fast resolution):    +2
    """

    metadata = {"render_modes": ["human"]}

    def __init__(self, max_steps: int = 200):
        super().__init__()
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(8,), dtype=np.float32)
        self.action_space = spaces.Discrete(4)
        self.max_steps = max_steps
        self.current_step = 0
        self.state = None
        self._rng = np.random.default_rng()

    def _generate_event(self) -> np.ndarray:
        scenario = self._rng.choice(["critical", "burst", "benign", "noise"], p=[0.15, 0.20, 0.40, 0.25])

        if scenario == "critical":
            return np.array([
                self._rng.uniform(0.7, 1.0),   # severity
                self._rng.uniform(0.3, 0.8),    # event_rate
                float(self._rng.random() > 0.5),  # is_burst
                self._rng.uniform(0.0, 0.3),    # historical_matches (novel)
                self._rng.uniform(0.6, 0.95),   # llm_confidence
                self._rng.uniform(0.4, 0.9),    # payload_complexity
                self._rng.uniform(0.3, 0.7),    # source_frequency
                self._rng.uniform(0.0, 0.3),    # time_since_last (recent)
            ], dtype=np.float32)
        elif scenario == "burst":
            return np.array([
                self._rng.uniform(0.3, 0.6),
                self._rng.uniform(0.7, 1.0),    # high event rate
                1.0,                             # is_burst = True
                self._rng.uniform(0.2, 0.6),
                self._rng.uniform(0.5, 0.8),
                self._rng.uniform(0.3, 0.6),
                self._rng.uniform(0.6, 1.0),    # frequent source
                self._rng.uniform(0.0, 0.1),    # very recent
            ], dtype=np.float32)
        elif scenario == "benign":
            return np.array([
                self._rng.uniform(0.1, 0.4),
                self._rng.uniform(0.1, 0.4),
                0.0,
                self._rng.uniform(0.5, 1.0),    # many historical matches (known issue)
                self._rng.uniform(0.7, 0.95),
                self._rng.uniform(0.1, 0.4),
                self._rng.uniform(0.2, 0.5),
                self._rng.uniform(0.3, 0.8),
            ], dtype=np.float32)
        else:  # noise
            return np.array([
                self._rng.uniform(0.0, 0.2),
                self._rng.uniform(0.0, 0.2),
                0.0,
                self._rng.uniform(0.0, 0.2),
                self._rng.uniform(0.1, 0.4),    # low LLM confidence
                self._rng.uniform(0.0, 0.2),
                self._rng.uniform(0.0, 0.3),
                self._rng.uniform(0.5, 1.0),    # long time since last
            ], dtype=np.float32)

    def _compute_reward(self, action: int, state: np.ndarray) -> float:
        severity = state[0]
        event_rate = state[1]
        is_burst = state[2]
        historical = state[3]
        llm_conf = state[4]

        is_critical = severity > 0.6
        is_burst_event = is_burst > 0.5
        is_benign = severity < 0.4 and historical > 0.5 and llm_conf > 0.6
        is_noise = severity < 0.2 and llm_conf < 0.4

        action_name = ACTION_MAP[action]

        if action_name == "escalate_to_maintenance":
            if is_critical:
                return 10.0
            elif is_benign:
                return -5.0  # false escalation wastes human time
            else:
                return 1.0   # cautious but unnecessary
        elif action_name == "auto_resolve":
            if is_benign:
                return 5.0 + 2.0  # correct + efficiency bonus
            elif is_critical:
                return -15.0  # missed a critical event
            else:
                return 0.0
        elif action_name == "scale_up":
            if is_burst_event:
                return 8.0
            elif is_critical:
                return 3.0   # not wrong, just not ideal
            else:
                return -3.0  # unnecessary scaling costs money
        elif action_name == "ignore":
            if is_noise:
                return 3.0
            elif is_critical:
                return -15.0  # ignored a real problem
            elif is_burst_event:
                return -8.0
            else:
                return 0.0

        return 0.0

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        self.current_step = 0
        self.state = self._generate_event()
        return self.state, {}

    def step(self, action: int):
        reward = self._compute_reward(action, self.state)
        self.current_step += 1
        self.state = self._generate_event()
        terminated = self.current_step >= self.max_steps
        return self.state, reward, terminated, False, {
            "action_taken": ACTION_MAP[action],
            "step": self.current_step,
        }
