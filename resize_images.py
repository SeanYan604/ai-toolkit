#!/usr/bin/env python3
"""
批量调整图像尺寸，使控制图像和目标图像尺寸一致
"""
import os
from pathlib import Path
from PIL import Image
import argparse
from tqdm import tqdm
import shutil

def get_image_files(folder_path):
    """获取文件夹中所有图像文件"""
    valid_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
    image_files = []

    for file_path in Path(folder_path).glob('*'):
        if file_path.suffix.lower() in valid_extensions:
            image_files.append(file_path)

    return image_files

def resize_image(input_path, output_path, target_size, method='letterbox', bg_color=(255, 255, 255)):
    """
    调整图像尺寸

    Args:
        input_path: 输入图像路径
        output_path: 输出图像路径
        target_size: 目标尺寸 (width, height)
        method: 'stretch' (拉伸), 'letterbox' (保持宽高比+填充), 'crop' (裁剪)
        bg_color: 背景颜色 (R, G, B)
    """
    try:
        with Image.open(input_path) as img:
            # 转换为 RGB
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, bg_color)
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[3])
                else:
                    background.paste(img, mask=img.split()[1])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            if method == 'stretch':
                # 直接拉伸到目标尺寸
                resized = img.resize(target_size, Image.LANCZOS)

            elif method == 'letterbox':
                # 保持宽高比，添加边框
                img.thumbnail(target_size, Image.LANCZOS)

                # 创建目标尺寸的背景
                background = Image.new('RGB', target_size, bg_color)

                # 计算居中位置
                offset = ((target_size[0] - img.size[0]) // 2,
                         (target_size[1] - img.size[1]) // 2)

                background.paste(img, offset)
                resized = background

            elif method == 'crop':
                # 保持宽高比，裁剪中心
                img_ratio = img.size[0] / img.size[1]
                target_ratio = target_size[0] / target_size[1]

                if img_ratio > target_ratio:
                    # 图像更宽，裁剪左右
                    new_width = int(img.size[1] * target_ratio)
                    offset = (img.size[0] - new_width) // 2
                    img = img.crop((offset, 0, offset + new_width, img.size[1]))
                else:
                    # 图像更高，裁剪上下
                    new_height = int(img.size[0] / target_ratio)
                    offset = (img.size[1] - new_height) // 2
                    img = img.crop((0, offset, img.size[0], offset + new_height))

                resized = img.resize(target_size, Image.LANCZOS)

            else:
                raise ValueError(f"Unknown method: {method}")

            # 保存
            resized.save(output_path, quality=95)
            return True

    except Exception as e:
        print(f"错误: 无法处理 {input_path}: {e}")
        return False

def match_target_sizes(target_folder, control_folder, output_folder, method='letterbox', dry_run=False):
    """
    使控制图像的尺寸匹配目标图像

    Args:
        target_folder: 目标图像文件夹
        control_folder: 控制图像文件夹
        output_folder: 输出文件夹（调整后的控制图像）
        method: 调整方法
        dry_run: 仅显示将要执行的操作，不实际修改文件
    """
    print(f"目标图像文件夹: {target_folder}")
    print(f"控制图像文件夹: {control_folder}")
    print(f"输出文件夹: {output_folder}")
    print(f"调整方法: {method}")
    print(f"预览模式: {'是' if dry_run else '否'}")
    print()

    # 加载目标图像
    target_images = {}
    for file_path in get_image_files(target_folder):
        base_name = file_path.stem
        with Image.open(file_path) as img:
            target_images[base_name] = img.size

    print(f"找到 {len(target_images)} 个目标图像")

    # 加载控制图像
    control_images = {}
    for file_path in get_image_files(control_folder):
        base_name = file_path.stem
        control_images[base_name] = file_path

    print(f"找到 {len(control_images)} 个控制图像")
    print()

    if not dry_run:
        os.makedirs(output_folder, exist_ok=True)

    # 处理匹配的图像
    processed = 0
    skipped = 0
    errors = 0

    for base_name, target_size in tqdm(target_images.items(), desc="处理图像"):
        if base_name not in control_images:
            skipped += 1
            continue

        control_path = control_images[base_name]
        output_path = os.path.join(output_folder, control_path.name)

        if dry_run:
            with Image.open(control_path) as img:
                current_size = img.size
            if current_size != target_size:
                print(f"将调整: {base_name} 从 {current_size} 到 {target_size}")
            processed += 1
        else:
            if resize_image(control_path, output_path, target_size, method):
                processed += 1
            else:
                errors += 1

    print()
    print("=" * 80)
    print(f"处理完成: {processed} 个")
    print(f"跳过（未找到目标）: {skipped} 个")
    if errors > 0:
        print(f"错误: {errors} 个")
    print("=" * 80)

def resize_to_fixed_size(folder, output_folder, target_size, method='letterbox', dry_run=False):
    """
    将文件夹中所有图像调整到固定尺寸
    """
    print(f"输入文件夹: {folder}")
    print(f"输出文件夹: {output_folder}")
    print(f"目标尺寸: {target_size}")
    print(f"调整方法: {method}")
    print(f"预览模式: {'是' if dry_run else '否'}")
    print()

    image_files = get_image_files(folder)
    print(f"找到 {len(image_files)} 个图像")
    print()

    if not dry_run:
        os.makedirs(output_folder, exist_ok=True)

    processed = 0
    errors = 0

    for file_path in tqdm(image_files, desc="处理图像"):
        output_path = os.path.join(output_folder, file_path.name)

        if dry_run:
            with Image.open(file_path) as img:
                current_size = img.size
            if current_size != target_size:
                print(f"将调整: {file_path.name} 从 {current_size} 到 {target_size}")
            processed += 1
        else:
            if resize_image(file_path, output_path, target_size, method):
                processed += 1
            else:
                errors += 1

    print()
    print("=" * 80)
    print(f"处理完成: {processed} 个")
    if errors > 0:
        print(f"错误: {errors} 个")
    print("=" * 80)

def main():
    parser = argparse.ArgumentParser(
        description='批量调整图像尺寸',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使控制图像匹配目标图像尺寸
  python resize_images.py match /path/to/target /path/to/control /path/to/output

  # 将所有图像调整到 1024x1024
  python resize_images.py fixed /path/to/images /path/to/output 1024 1024

  # 预览模式（不实际修改）
  python resize_images.py match /path/to/target /path/to/control /path/to/output --dry-run

调整方法:
  stretch   - 直接拉伸（可能变形）
  letterbox - 保持宽高比，添加边框（推荐）
  crop      - 保持宽高比，裁剪中心
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='命令')

    # match 命令
    match_parser = subparsers.add_parser('match', help='使控制图像匹配目标图像尺寸')
    match_parser.add_argument('target_folder', help='目标图像文件夹')
    match_parser.add_argument('control_folder', help='控制图像文件夹')
    match_parser.add_argument('output_folder', help='输出文件夹')
    match_parser.add_argument('--method', choices=['stretch', 'letterbox', 'crop'],
                            default='letterbox', help='调整方法 (默认: letterbox)')
    match_parser.add_argument('--dry-run', action='store_true', help='预览模式，不实际修改文件')

    # fixed 命令
    fixed_parser = subparsers.add_parser('fixed', help='将所有图像调整到固定尺寸')
    fixed_parser.add_argument('folder', help='输入文件夹')
    fixed_parser.add_argument('output_folder', help='输出文件夹')
    fixed_parser.add_argument('width', type=int, help='目标宽度')
    fixed_parser.add_argument('height', type=int, help='目标高度')
    fixed_parser.add_argument('--method', choices=['stretch', 'letterbox', 'crop'],
                            default='letterbox', help='调整方法 (默认: letterbox)')
    fixed_parser.add_argument('--dry-run', action='store_true', help='预览模式，不实际修改文件')

    args = parser.parse_args()

    if args.command == 'match':
        match_target_sizes(
            args.target_folder,
            args.control_folder,
            args.output_folder,
            args.method,
            args.dry_run
        )
    elif args.command == 'fixed':
        resize_to_fixed_size(
            args.folder,
            args.output_folder,
            (args.width, args.height),
            args.method,
            args.dry_run
        )
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
