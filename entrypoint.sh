#!/bin/sh
set -e

# 首次启动时初始化持久化数据卷
# 等价于原 entrypoint.py 的逻辑

INSTALLED_LOCK="/data/INSTALLED.lock"

# 建立符号链接：/data 下的目标 -> /app 下的链接
symlink() {
    target="$1"
    link_path="$2"

    # 若链接路径是已存在的真实目录（非符号链接），先删除
    if [ -d "$link_path" ] && [ ! -L "$link_path" ]; then
        rm -rf "$link_path"
    fi

    # 若链接路径已存在（含符号链接），先删除
    if [ -e "$link_path" ] || [ -L "$link_path" ]; then
        rm -rf "$link_path"
    fi

    ln -s "$target" "$link_path"
}

# 首次启动：把 /app 下的配置复制到 /data 并建立符号链接
if [ ! -f "$INSTALLED_LOCK" ]; then
    # 需要复制并持久化的文件/文件夹
    for file in .env Config.toml Config; do
        src="/app/$file"
        dst="/data/$file"
        if [ -f "$src" ]; then
            cp -p "$src" "$dst"
        elif [ -d "$src" ]; then
            cp -rp "$src" "$dst"
        fi
        symlink "$dst" "$src"
    done

    # 需要动态创建并持久化的文件夹
    for file in Data; do
        src="/data/$file"
        dst="/app/$file"
        mkdir -p "$src"
        symlink "$src" "$dst"
    done

    # 修改 .env：把 HOST 改为 0.0.0.0
    sed -i 's/HOST="127.0.0.1"/HOST="0.0.0.0"/' /data/.env

    touch "$INSTALLED_LOCK"
fi

# 执行传入的命令
if [ "$#" -gt 0 ]; then
    exec "$@"
else
    exit 1
fi