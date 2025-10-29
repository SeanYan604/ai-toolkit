#!/usr/bin/env python3
"""
检查目标图像和控制图像的尺寸是否按文件名完全一致
"""
import os
from pathlib import Path
from PIL import Image
from collections import defaultdict
import sys
from tqdm import tqdm

def get_image_files(folder_path):
    """获取文件夹中所有图像文件"""
    if not os.path.exists(folder_path):
        print(f"警告: 文件夹不存在: {folder_path}")
        return {}

    valid_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
    image_dict = {}

    for file_path in tqdm(Path(folder_path).glob('*')):
        if file_path.suffix.lower() in valid_extensions:
            # 使用不带扩展名的文件名作为 key
            base_name = file_path.stem
            try:
                with Image.open(file_path) as img:
                    image_dict[base_name] = {
                        'path': str(file_path),
                        'size': img.size,  # (width, height)
                        'mode': img.mode
                    }
            except Exception as e:
                print(f"错误: 无法读取图像 {file_path}: {e}")

    return image_dict

def check_consistency(target_folder, control_folders):
    """检查目标图像和控制图像的一致性"""
    print("=" * 80)
    print("图像尺寸一致性检查")
    print("=" * 80)
    print()

    # 加载目标图像
    print(f"📁 加载目标图像: {target_folder}")
    target_images = get_image_files(target_folder)
    print(f"   找到 {len(target_images)} 个图像")
    print()

    # 加载所有控制图像
    control_images_list = []
    for i, control_folder in enumerate(control_folders, 1):
        print(f"📁 加载控制图像 {i}: {control_folder}")
        control_images = get_image_files(control_folder)
        print(f"   找到 {len(control_images)} 个图像")
        control_images_list.append((control_folder, control_images))
        print()

    if len(target_images) == 0:
        print("❌ 错误: 目标文件夹中没有找到图像！")
        return False

    # 检查一致性
    print("=" * 80)
    print("检查结果")
    print("=" * 80)
    print()

    all_consistent = True
    missing_files = defaultdict(list)
    size_mismatches = []

    # 按文件名检查
    for base_name, target_info in sorted(target_images.items()):
        target_size = target_info['size']
        target_path = target_info['path']

        # 检查每个控制文件夹
        for control_folder, control_images in control_images_list:
            if base_name not in control_images:
                missing_files[control_folder].append(base_name)
                all_consistent = False
            else:
                control_info = control_images[base_name]
                control_size = control_info['size']
                control_path = control_info['path']

                if control_size != target_size:
                    size_mismatches.append({
                        'base_name': base_name,
                        'target_path': target_path,
                        'target_size': target_size,
                        'control_path': control_path,
                        'control_size': control_size,
                        'control_folder': control_folder
                    })
                    all_consistent = False

    # 报告结果
    if all_consistent:
        print("✅ 所有图像尺寸完全一致！")
        print(f"   共检查 {len(target_images)} 个图像")
        return True
    else:
        print("❌ 发现不一致的情况：")
        print()

        # 报告缺失的文件
        if missing_files:
            print("📋 缺失的控制图像:")
            for control_folder, missing_names in missing_files.items():
                print(f"\n   控制文件夹: {control_folder}")
                print(f"   缺失 {len(missing_names)} 个文件:")
                for name in missing_names[:10]:  # 只显示前 10 个
                    print(f"      - {name}")
                if len(missing_names) > 10:
                    print(f"      ... 还有 {len(missing_names) - 10} 个")
            print()

        # 报告尺寸不匹配
        if size_mismatches:
            print("📐 尺寸不匹配的图像:")
            print()
            for mismatch in size_mismatches[:20]:  # 只显示前 20 个
                print(f"   文件名: {mismatch['base_name']}")
                print(f"      目标: {mismatch['target_size']} - {mismatch['target_path']}")
                print(f"      控制: {mismatch['control_size']} - {mismatch['control_path']}")
                print()
            if len(size_mismatches) > 20:
                print(f"   ... 还有 {len(size_mismatches) - 20} 个不匹配")
            print()

            # 统计尺寸分布
            print("📊 尺寸统计:")
            size_counts = defaultdict(int)
            for base_name, info in target_images.items():
                size_counts[info['size']] += 1

            print(f"\n   目标图像尺寸分布:")
            for size, count in sorted(size_counts.items(), key=lambda x: -x[1]):
                print(f"      {size[0]}x{size[1]}: {count} 个")

            for control_folder, control_images in control_images_list:
                size_counts = defaultdict(int)
                for base_name, info in control_images.items():
                    size_counts[info['size']] += 1
                print(f"\n   控制图像尺寸分布 ({os.path.basename(control_folder)}):")
                for size, count in sorted(size_counts.items(), key=lambda x: -x[1]):
                    print(f"      {size[0]}x{size[1]}: {count} 个")

        return False

def main():
    # 配置路径 - 根据你的实际路径修改
    import argparse

    # parser = argparse.ArgumentParser(description='检查图像尺寸一致性')
    # parser.add_argument('target_folder', default="/root/autodl-fs/kontext_datasets/shadow_control_v2", help='目标图像文件夹路径')
    # parser.add_argument('control_folders', default="/root/autodl-fs/kontext_datasets/shadow_target_v2", help='控制图像文件夹路径（可以有多个）')

    # args = parser.parse_args()

    target_folder = "/root/autodl-fs/kontext_datasets/shadow_target_v2"
    control_folders = ["/root/autodl-fs/kontext_datasets/shadow_control_v2"]

    # 检查一致性
    is_consistent = check_consistency(target_folder, control_folders)

    print()
    print("=" * 80)
    if is_consistent:
        print("✅ 检查完成: 所有图像尺寸一致")
        sys.exit(0)
    else:
        print("❌ 检查完成: 发现不一致")
        print()
        print("建议:")
        print("  1. 使用 ImageMagick 统一调整尺寸:")
        print("     mogrify -resize 1024x1024! /path/to/images/*.png")
        print()
        print("  2. 或使用保持宽高比的方式:")
        print("     mogrify -resize 1024x1024 -background white -gravity center -extent 1024x1024 /path/to/images/*.png")
        sys.exit(1)

if __name__ == "__main__":
    main()
