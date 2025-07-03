# Copyright 2024 Bytedance Ltd. and/or its affiliates
# Copyright 2023-2024 VoyahAGI Team
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

import argparse
import logging
import os

import pandas as pd
from datasets import load_dataset

from verl.utils.hdfs_io import copy, makedirs

# 日志设置
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 系统提示词
DEFAULT_SYSTEM_CONTENT = (
    "You are VCoder, a powerful agentic AI coding assistant. You have access to the `grep_search` tool "
    "for searching the project codebase.\n\n"
    "RULES (follow strictly):\n"
    "1. First think step-by-step; every chunk of reasoning MUST be wrapped in <think> ... </think>.\n"
    "2. Before proposing any patch you MUST invoke `grep_search` at least once, using the syntax "
    "<grep_search> query </grep_search>.\n"
    "3. After each <grep_search> you will receive the result inside <tool_response> ... </tool_response>; "
    "analyse it inside <think> before doing anything else.\n"
    "4. When you are confident, output ONLY the final patch inside a single <diff_gen> ... </diff_gen> block, "
    "and nothing else outside these tags."
)
DEFAULT_USER_CONTENT_PREFIX = (
    "Fix the given code problem. Follow the RULES above. If you need to inspect the code, "
    "call the `grep_search` tool as instructed. "
    "When you have the solution, provide the patch inside <diff_gen>. "
    "\n\nProblem: "
)

# 提取数据
# 处理SWE-Bench Lite数据集，得到训练用数据，包含repo， commit_id, issue
def process_single_row(row, current_split_name, row_index):
    """
    Process a single row of data for SWE-Bench Lite format.

    Args:
        row: DataFrame row containing the original data
        current_split_name: Name of the current split (train/test)
        row_index: Index of the row in the DataFrame

    Returns:
        pd.Series: Processed row data in the required format
    """
    
    # Build complete extra_info structure
    # 注意：Parquet 不支持写入字段为空的 struct。如果 create_kwargs 为空 dict，
    # pyarrow 会推断为 "struct<create_kwargs: struct<>>"，进而报错：
    #   "Cannot write struct type 'create_kwargs' with no child field to Parquet." 
    # 因此为 create_kwargs 添加一个占位字段，保证至少含有一个子字段。
    extra_info = {
        "index": row_index,
        "need_tools_kwargs": True,
        "split": current_split_name,
        # 给 create_kwargs 添加占位字段，避免空结构体导致的 parquet 写入错误
        "tools_kwargs": {"grep_search": {"create_kwargs": {"__dummy": None}}},
    }

    # ------------------------ prompt 构造 ------------------------
    problem_statement = row.get("problem_statement", "")
    user_content = DEFAULT_USER_CONTENT_PREFIX + problem_statement

    prompt = [
        {"role": "system", "content": DEFAULT_SYSTEM_CONTENT},
        {"role": "user", "content": user_content},
    ]

    return pd.Series(
        {
            "data_source": "swe_bench_lite",
            "repo": row.get("repo"),
            "instance_id": row.get("instance_id"),
            "base_commit": row.get("base_commit"),
            "issue": problem_statement,
            "prompt": prompt,
            "extra_info": extra_info,
        }
    )

def main():
    local_save_dir = os.path.expanduser(args.local_dir)
    os.makedirs(local_save_dir, exist_ok=True)

    processed_files = []

    # Load dataset using datasets library
    try:
        logger.info(f"Loading dataset {args.hf_repo_id}")
        dataset = load_dataset(args.hf_repo_id)
        
        # Process available splits
        for split_name in dataset.keys():
            if split_name in ["dev", "test"]:  # Only process dev and test splits
                logger.info(f"Processing {split_name} split...")
                
                # Convert to DataFrame
                df_raw = dataset[split_name].to_pandas()
                logger.info(f"Loaded {len(df_raw)} rows from {split_name} split")

                def apply_process_row(row, split_name=split_name):
                    return process_single_row(row, current_split_name=split_name, row_index=row.name)

                df_processed = df_raw.apply(apply_process_row, axis=1)

                # Save processed DataFrame
                output_file_path = os.path.join(local_save_dir, f"{split_name}.parquet")
                df_processed.to_parquet(output_file_path, index=False)
                logger.info(f"Saved {len(df_processed)} processed rows to {output_file_path}")
                processed_files.append(output_file_path)

    except Exception as e:
        logger.error(f"Error loading dataset: {e}")
        return

    if not processed_files:
        logger.warning("No data was processed or saved")
        return

    logger.info(f"Successfully processed {len(processed_files)} files to {local_save_dir}")

    # Copy to HDFS if specified
    if args.hdfs_dir:
        try:
            makedirs(args.hdfs_dir)
            copy(src=local_save_dir, dst=args.hdfs_dir)
            logger.info(f"Successfully copied files to HDFS: {args.hdfs_dir}")
        except Exception as e:
            logger.error(f"Error copying files to HDFS: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download SWE-Bench Lite from HuggingFace, process, and save to Parquet.")
    parser.add_argument(
        "--hf_repo_id", default="princeton-nlp/SWE-bench_Lite", help="HuggingFace dataset repository ID."
    )
    parser.add_argument(
        "--local_dir",
        default="~/data/code_agent",
        help="Local directory to save the processed Parquet files.",
    )
    parser.add_argument("--hdfs_dir", default=None, help="Optional HDFS directory to copy the Parquet files to.")

    args = parser.parse_args()

    # System and user content configuration
    system_content = DEFAULT_SYSTEM_CONTENT
    user_content_prefix = DEFAULT_USER_CONTENT_PREFIX

    main()
