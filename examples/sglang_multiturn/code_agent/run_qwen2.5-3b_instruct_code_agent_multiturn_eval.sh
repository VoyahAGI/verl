#!/usr/bin/env bash
# 仅进行 GRPO 前向推理 (无训练)，验证代码 Agent 工具调用，并记录轨迹
# 运行环境：4×GPU；请确保工作目录位于项目根目录

set -euo pipefail
set -x

################################################################################
# 1. 环境变量
################################################################################
# 关闭 tokenizers 的多进程警告
export TOKENIZERS_PARALLELISM=true
# 启用轨迹追踪，所有中间数据将保存到指定 HDFS 目录
export VERL_ENABLE_TRACKER=1
export VERL_TRACKER_HDFS_DIR=${VERL_TRACKER_HDFS_DIR:-"~/verl_traj"}
# 启用详细追踪日志，显示保存过程
export VERL_TRACKER_VERBOSE=${VERL_TRACKER_VERBOSE:-1}

# 显式指定 GPU
export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-"4,5,6,7"}
# 防止过多文件句柄导致错误
ulimit -n 65535

################################################################################
# 2. 路径与数据
################################################################################
PROJECT_DIR="$(pwd)"
CONFIG_PATH="$PROJECT_DIR/examples/sglang_multiturn/config"

# 只需要验证集即可 - 使用预处理后的数据
VAL_DATA="$HOME/data/code_agent/test.parquet"
# 工具配置
TOOL_CONFIG="$CONFIG_PATH/tool_config/code_agent_tool_config.yaml"

################################################################################
# 3. 运行前向推理
################################################################################
python3 -m verl.trainer.main_ppo \
    --config-path="$CONFIG_PATH" \
    --config-name='code_agent_multiturn_grpo' \
    algorithm.adv_estimator=grpo \
    data.train_batch_size=256 \
    data.val_batch_size=128 \
    data.max_prompt_length=4096 \
    data.max_response_length=3000 \
    data.filter_overlong_prompts=True \
    data.truncation='error' \
    data.return_raw_chat=True \
    data.train_files="$VAL_DATA" \
    data.val_files="$VAL_DATA" \
    actor_rollout_ref.model.path=/root/.cache/modelscope/hub/models/Qwen/Qwen2.5-0.5B-Instruct \
    actor_rollout_ref.model.use_remove_padding=True \
    actor_rollout_ref.rollout.name=sglang \
    actor_rollout_ref.rollout.gpu_memory_utilization=0.5 \
    actor_rollout_ref.rollout.n=4 \
    actor_rollout_ref.rollout.multi_turn.max_assistant_turns=5 \
    actor_rollout_ref.rollout.multi_turn.tool_config_path="$TOOL_CONFIG" \
    actor_rollout_ref.actor.ppo_micro_batch_size_per_gpu=8 \
    actor_rollout_ref.rollout.log_prob_micro_batch_size_per_gpu=8 \
    reward_model.reward_manager=noop \
    trainer.val_before_train=True \
    trainer.val_only=True \
    trainer.logger=['console'] \
    trainer.project_name='code_agent_forward_eval' \
    trainer.experiment_name='qwen2.5-0.5b-instruct-grpo-forward-eval' \
    trainer.validation_data_dir="$PROJECT_DIR/val_generations" \
    trainer.n_gpus_per_node=4 \
    trainer.nnodes=1 \
    trainer.save_freq=-1 \
    trainer.test_freq=-1 \
    trainer.total_epochs=1 "$@" 