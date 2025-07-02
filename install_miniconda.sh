#!/bin/bash

# Miniconda 安装脚本
# 适用于 Linux x86_64 系统

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的信息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否已安装 Miniconda
check_existing_conda() {
    if command -v conda &> /dev/null; then
        print_warning "检测到系统中已安装 Conda"
        conda --version
        read -p "是否继续安装？这可能会覆盖现有安装 (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "安装已取消"
            exit 0
        fi
    fi
}

# 下载 Miniconda
download_miniconda() {
    print_info "开始下载 Miniconda..."
    
    # Miniconda 最新版本的下载链接
    MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
    INSTALL_SCRIPT="Miniconda3-latest-Linux-x86_64.sh"
    
    # 检查是否已存在安装文件
    if [ -f "$INSTALL_SCRIPT" ]; then
        print_warning "发现已存在的安装文件: $INSTALL_SCRIPT"
        read -p "是否重新下载？(y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -f "$INSTALL_SCRIPT"
        else
            print_info "使用现有的安装文件"
            return 0
        fi
    fi
    
    # 下载安装文件
    if command -v wget &> /dev/null; then
        wget "$MINICONDA_URL" -O "$INSTALL_SCRIPT"
    elif command -v curl &> /dev/null; then
        curl -L "$MINICONDA_URL" -o "$INSTALL_SCRIPT"
    else
        print_error "未找到 wget 或 curl，无法下载文件"
        print_info "请手动安装 wget 或 curl："
        print_info "  Ubuntu/Debian: sudo apt-get install wget"
        print_info "  CentOS/RHEL: sudo yum install wget"
        exit 1
    fi
    
    print_success "Miniconda 下载完成"
}

# 安装 Miniconda
install_miniconda() {
    print_info "开始安装 Miniconda..."
    
    INSTALL_SCRIPT="Miniconda3-latest-Linux-x86_64.sh"
    
    # 设置默认安装路径
    DEFAULT_INSTALL_PATH="$HOME/miniconda3"
    
    print_info "默认安装路径: $DEFAULT_INSTALL_PATH"
    read -p "是否使用默认路径？(Y/n): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        read -p "请输入安装路径: " INSTALL_PATH
        if [ -z "$INSTALL_PATH" ]; then
            INSTALL_PATH="$DEFAULT_INSTALL_PATH"
        fi
    else
        INSTALL_PATH="$DEFAULT_INSTALL_PATH"
    fi
    
    # 执行安装
    chmod +x "$INSTALL_SCRIPT"
    bash "$INSTALL_SCRIPT" -b -p "$INSTALL_PATH"
    
    print_success "Miniconda 安装完成"
    
    # 初始化 Conda
    print_info "正在初始化 Conda..."
    "$INSTALL_PATH/bin/conda" init bash
    
    # 清理安装文件
    read -p "是否删除安装文件？(Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        rm -f "$INSTALL_SCRIPT"
        print_success "安装文件已删除"
    fi
}

# 配置 Conda
configure_conda() {
    print_info "配置 Conda 环境..."
    
    # 添加 conda-forge 频道
    "$HOME/miniconda3/bin/conda" config --add channels conda-forge
    
    # 设置频道优先级
    "$HOME/miniconda3/bin/conda" config --set channel_priority strict
    
    # 更新 conda
    "$HOME/miniconda3/bin/conda" update -n base -c defaults conda -y
    
    print_success "Conda 配置完成"
}

# 验证安装
verify_installation() {
    print_info "验证安装..."
    
    # 重新加载 shell 配置
    source "$HOME/.bashrc" 2>/dev/null || true
    
    # 检查 conda 命令
    if "$HOME/miniconda3/bin/conda" --version &> /dev/null; then
        print_success "Miniconda 安装验证成功"
        "$HOME/miniconda3/bin/conda" --version
        "$HOME/miniconda3/bin/conda" info --envs
    else
        print_error "安装验证失败"
        exit 1
    fi
}

# 显示后续步骤
show_next_steps() {
    print_success "安装完成！"
    echo
    print_info "下一步操作："
    echo "1. 重新打开终端或运行: source ~/.bashrc"
    echo "2. 验证安装: conda --version"
    echo "3. 创建新环境: conda create -n myenv python=3.9"
    echo "4. 激活环境: conda activate myenv"
    echo
    print_info "常用 Conda 命令："
    echo "  conda list                 # 列出已安装的包"
    echo "  conda env list             # 列出所有环境"
    echo "  conda install package_name # 安装包"
    echo "  conda remove package_name  # 删除包"
    echo "  conda deactivate           # 退出当前环境"
}

# 主函数
main() {
    print_info "开始安装 Miniconda..."
    echo
    
    check_existing_conda
    download_miniconda
    install_miniconda
    configure_conda
    verify_installation
    show_next_steps
}

# 运行主函数
main "$@"
