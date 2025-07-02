#!/bin/bash

# 设置用户路径变量
USER_HOME=${HOME}
WORKSPACE_DIR=$(pwd)
CACHE_DIR="${USER_HOME}/.cache/modelscope"
VERL_DIR="${WORKSPACE_DIR}/verl"
CURRENT_USER=${USER:-$(whoami)}
CONTAINER_NAME="sglang_voyah_${CURRENT_USER}"

# 检查必要的目录是否存在
if [ ! -d "${CACHE_DIR}" ]; then
    echo "创建缓存目录: ${CACHE_DIR}"
    mkdir -p "${CACHE_DIR}"
fi

if [ ! -d "${VERL_DIR}" ]; then
    echo "警告: VERL目录不存在: ${VERL_DIR}"
    echo "是否继续? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 检查容器是否已经存在
if docker ps -a --format '{{.Names}}' | grep -Eq "^${CONTAINER_NAME}$"; then
    echo "容器 '${CONTAINER_NAME}' 已存在。"
    echo "是否删除并重新创建? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "正在删除旧容器..."
        docker stop "${CONTAINER_NAME}" && docker rm "${CONTAINER_NAME}"
        echo "旧容器已删除。"
    else
        echo "操作取消。"
        exit 0
    fi
fi

echo "启动 SGLang Docker 容器..."
echo "用户目录: ${USER_HOME}"
echo "工作空间: ${WORKSPACE_DIR}"
echo "缓存目录: ${CACHE_DIR}"
echo "VERL目录: ${VERL_DIR}"

docker run -d \
    -it \
    --shm-size 32g \
    --gpus all \
    -v "${CACHE_DIR}:/root/.cache/modelscope" \
    -v "${VERL_DIR}:/home/verl" \
    --ipc=host \
    --network=host \
    --privileged \
    --name "${CONTAINER_NAME}" \
    m.daocloud.io/docker.io/lmsysorg/sglang:dev \
    /bin/zsh

# 检查容器是否启动成功
if [ $? -eq 0 ]; then
    echo "容器 '${CONTAINER_NAME}' 启动成功！"
    echo "使用以下命令进入容器："
    echo "docker exec -it ${CONTAINER_NAME} /bin/zsh"
else
    echo "容器启动失败！"
    exit 1
fi
