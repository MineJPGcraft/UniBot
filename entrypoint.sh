#!/bin/sh
set -e

# 让 /app 下的配置始终指向持久化卷 /data。
#
# 镜像里的 .env / Config.toml / Config / Data 都是真实文件/目录，
# 使用已有 /data 卷重建容器时，/app 会恢复成镜像默认值。
# 因此不能只在“首次安装”时建立软链接，否则重建后用户配置会全部丢失。

# 仅在 /data 中不存在目标时，从镜像复制默认配置（绝不覆盖已有配置）
copy_default() {
    name="$1"
    src="/app/$name"
    dst="/data/$name"

    if [ -e "$dst" ] || [ -L "$dst" ]; then
        return 0
    fi
    if [ ! -e "$src" ]; then
        return 0
    fi

    if [ -d "$src" ] && [ ! -L "$src" ]; then
        cp -rp "$src" "$dst"
    else
        cp -p "$src" "$dst"
    fi
}

# 确保 /app/<name> 是指向 /data/<name> 的软链接
link_to_data() {
    name="$1"
    dst="/data/$name"
    path="/app/$name"

    if [ -L "$path" ] && [ "$(readlink "$path")" = "$dst" ]; then
        return 0
    fi

    if [ -e "$path" ] || [ -L "$path" ]; then
        rm -rf "$path"
    fi

    ln -s "$dst" "$path"
}

# Data 只持久化，不复制镜像默认值；若 /data/Data 缺失而 /app/Data 有内容，
# 先把它迁到 /data，避免误删运行时生成的数据。
if [ ! -e /data/Data ] && [ ! -L /data/Data ] && [ -d /app/Data ] && [ ! -L /app/Data ]; then
    cp -rp /app/Data /data/Data
fi
mkdir -p /data/Data

for name in .env Config.toml Config; do
    copy_default "$name"
    link_to_data "$name"
done

link_to_data "Data"

# 容器内必须监听 0.0.0.0 才能通过 Docker 端口映射访问
if [ -f /data/.env ]; then
    sed -i 's/^HOST="127.0.0.1"/HOST="0.0.0.0"/' /data/.env
fi

# 执行传入的命令
if [ "$#" -gt 0 ]; then
    exec "$@"
else
    exit 1
fi
