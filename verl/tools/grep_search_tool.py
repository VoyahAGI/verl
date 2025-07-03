# Copyright 2023-2025 SGLang Team
# Copyright Amazon.com, Inc. or its affiliates.
# Copyright 2025 ModelBest Inc. and/or its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
from typing import Any, Optional, Tuple
from uuid import uuid4
import subprocess
from pathlib import Path

from .base_tool import BaseTool
from .schemas import OpenAIFunctionToolSchema

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("VERL_LOGGING_LEVEL", "WARN"))


class GrepSearchTool(BaseTool):
    """A demo tool for calculating the reward of geo3k.
    - `to_openai_function_tool_schema`: return the tool schema in OpenAI format.
    - `create`: create a tool instance for a trajectory.
    - `execute`: execute the tool.
    - `calc_reward`: calculate the reward respect to tool state.
    - `release`: release the tool instance.
    """

    def __init__(self, config: dict, tool_schema: OpenAIFunctionToolSchema):
        """
        _tool_schema = OpenAIFunctionToolSchema.model_validate({
            "type": "function",
            "function": {
                "name": "grep_search",
                "description": "A tool for searching the answer from the codebase",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The query to search the codebase",
                        },
                    },
                    "required": ["query"],
                },
            }
        })
        """
        super().__init__(config, tool_schema)
        self._instance_dict = {}

    def get_openai_tool_schema(self) -> OpenAIFunctionToolSchema:
        return self.tool_schema

    async def create(self, instance_id: Optional[str] = None, ground_truth: Optional[str] = None, **kwargs) -> str:
        if instance_id is None:
            instance_id = str(uuid4())
        self._instance_dict[instance_id] = {
            "response": "",
            "ground_truth": ground_truth,
            "reward": 0.0,
        }
        return instance_id, None

    async def execute(self, instance_id: str, parameters: dict[str, Any], **kwargs) -> Tuple[str, float, dict]:
        """执行代码检索并返回文本结果。

        Parameters
        ----------
        parameters : dict
            包含 `query` 字段的参数字典。
        """

        query = parameters.get("query", "")
        if not isinstance(query, str):
            query = str(query)

        search_root = Path(self.config.get("search_root", Path.cwd()))
        max_lines = int(self.config.get("max_lines", 20))

        cmd = ["rg", "-n", "--no-heading", "--color", "never", query, str(search_root)]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            output_lines = proc.stdout.splitlines()
        except FileNotFoundError:
            cmd = ["grep", "-R", "-n", query, str(search_root)]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            output_lines = proc.stdout.splitlines()
        except subprocess.TimeoutExpired:
            output_lines = ["<search timeout>"]

        sliced = output_lines[:max_lines]
        result_text = "\n".join(sliced) if sliced else "<no match>"

        # 记录结果，供调试或后续 calc_reward 使用
        self._instance_dict[instance_id]["response"] = result_text

        metrics = {
            "query": query,
            "total_matches": len(output_lines),
            "returned_lines": len(sliced),
        }

        return result_text, 0.0, metrics

    async def calc_reward(self, instance_id: str, **kwargs) -> float:
        # 本工具不计算奖励
        return 0.0

    async def release(self, instance_id: str, **kwargs) -> None:
        del self._instance_dict[instance_id]
