from pathlib import Path
import os
import sys
import shutil

# 需要的常量

# 这里写需要复制的文件和文件夹
# 也就是运行前已经存在 需要持久化的文件夹
PENDING_COPY = [
        '.env',
        'Config.toml',
        'Config',
    ]

# 这里写需要创建的文件夹
# 也就是运行前不存在 需要动态创建持久化的文件夹
PENDING_CREATE = [
    'Data'
]

# 后处理函数全都是输入原始内容 输出新内容
# 输入输出类型都是字符串
# 我懒得写协议了 自己注意点就好
PENDING_MODIFY = {
    '.env': lambda x: x.replace("HOST=\"127.0.0.1\"", "HOST=\"0.0.0.0\"")
}

# ---下面的一般不用动---

installed = Path('/data/INSTALLED.lock')

# 用来创建符号链接的函数
def symlink(target: Path, link_path: Path):

    if link_path.exists() and link_path.is_dir() and not link_path.is_symlink():
        shutil.rmtree(link_path)

    if link_path.exists() or link_path.is_symlink():
        link_path.unlink()

    link_path.symlink_to(target, target_is_directory=target.is_dir() if target.exists() else False)

# 如果没安装过
if not installed.exists(): 
    for file in PENDING_COPY:
        src = Path('/app/') / file
        dst = Path('/data/') / file
        if src.is_file():
            shutil.copy2(src, dst)
        elif src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)

        symlink(dst, src)

    for file in PENDING_CREATE:
        src = Path('/data/') / file
        dst = Path('/app/') / file

        Path(src).mkdir(parents=True, exist_ok=True)

        symlink(dst, src)

    for file in PENDING_MODIFY.keys():
        src = Path('/data/') / file

        with open(src, "r+") as f:
            nfc = PENDING_MODIFY[file](f.read())
            
        with open(src, "w") as f:
            f.write(nfc)

    open(installed, "w").close()

# 执行
if len(sys.argv) > 1:
    os.execvp(sys.argv[1], args=sys.argv[1:])
else:
    exit(1)