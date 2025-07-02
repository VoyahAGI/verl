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
import tempfile

import pandas as pd
from huggingface_hub import hf_hub_download
from huggingface_hub.utils import EntryNotFoundError

from verl.utils.hdfs_io import copy, makedirs

# 日志设置
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 系统提示词
DEFAULT_SYSTEM_CONTENT = "You are VCoder, a powerful agentic  AI coding assistant."
DEFAULT_USER_CONTENT_PREFIX = (
    "Answer the given question. You must conduct reasoning inside <think> and </think> "
    "first every time you get new information. After reasoning, if you find you lack "
    "some knowledge, you can call a search engine by <tool_call> query </tool_call> "
    "and it will return the top searched results between <tool_response> and "
    "</tool_response>. You can search as many times as your want. If you find no "
    "further external knowledge needed, you can directly provide the answer inside "
    "<answer> and </answer>, without detailed illustrations. For example, "
    "<answer> Beijing </answer>. Question: "
)

# 提取数据
# 处理SWE-Bench Lite数据集，得到训练用数据，包含repo， commit_id, issue
def process_single_row(row, current_split_name, row_index):
    """
    Process a single row of data for SearchR1-like format.

    Args:
        row: DataFrame row containing the original data
        current_split_name: Name of the current split (train/test)
        row_index: Index of the row in the DataFrame

    Returns:
        pd.Series: Processed row data in the required format
    """
    
    # Build complete extra_info structure
    extra_info = {
        "index": row_index,
        "need_tools_kwargs": True,
        "split": current_split_name,
    }

    return pd.Series(
        {
            "repo": row.get("repo"),
            "instance_id": row.get("instance_id"),
            "base_commit": row.get("commit_id"),
            "issue": row.get("problem_statement"),
            "extra_info": extra_info,
        }
    )

def main():
    local_save_dir = os.path.expanduser(args.local_dir)
    os.makedirs(local_save_dir, exist_ok=True)

    processed_files = []

    # Download and process files using temporary directory
    with tempfile.TemporaryDirectory() as tmp_download_dir:
        for split in ["dev", "test"]:
            parquet_filename = f"{split}.parquet"
            logger.info(f"Processing {split} split...")

            try:
                # Download Parquet file from HuggingFace
                logger.info(f"Downloading {parquet_filename} from {args.hf_repo_id}")
                local_parquet_filepath = hf_hub_download(
                    repo_id=args.hf_repo_id,
                    filename=parquet_filename,
                    repo_type="dataset",
                    local_dir=tmp_download_dir,
                    local_dir_use_symlinks=False,
                )

                # Load and process Parquet file
                df_raw = pd.read_parquet(local_parquet_filepath)
                logger.info(f"Loaded {len(df_raw)} rows from {parquet_filename}")

                def apply_process_row(row, split_name=split):
                    return process_single_row(row, current_split_name=split_name, row_index=row.name)

                df_processed = df_raw.apply(apply_process_row, axis=1)

                # Save processed DataFrame
                output_file_path = os.path.join(local_save_dir, f"{split}.parquet")
                df_processed.to_parquet(output_file_path, index=False)
                logger.info(f"Saved {len(df_processed)} processed rows to {output_file_path}")
                processed_files.append(output_file_path)

            except EntryNotFoundError:
                logger.warning(f"{parquet_filename} not found in repository {args.hf_repo_id}")
            except Exception as e:
                logger.error(f"Error processing {split} split: {e}")

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
