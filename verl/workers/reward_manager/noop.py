from __future__ import annotations

import torch

from verl import DataProto
from . import register


@register("noop")
class NoopRewardManager:
    """一个空奖励管理器，对所有样本返回 0 奖励。

    适用于仅做前向推理、无需评价场景，避免数据缺失 ground_truth 字段导致报错。"""

    def __init__(self, tokenizer, num_examine: int = 0, **kwargs):  # noqa: D401
        self.tokenizer = tokenizer  # 保留接口一致性
        self.num_examine = num_examine

    def __call__(self, data: DataProto, return_dict: bool = False):  # noqa: D401
        """直接返回零张量。"""
        reward_tensor = torch.zeros_like(data.batch["responses"], dtype=torch.float32)
        if return_dict:
            return {"reward_tensor": reward_tensor}
        return reward_tensor 