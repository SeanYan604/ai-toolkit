#!/usr/bin/env python3
"""
自动修复 Qwen Image Edit Plus 支持 batch_size > 1

问题：
  - use_raw_control_images=True 导致控制图像不经过 bucket 缩放
  - 不同样本的控制图像尺寸不同，无法合并成 batch

解决方案：
  - 添加对 match_target_res 的检查
  - 当 match_target_res=True 时，强制控制图像经过与 target 相同的 bucket 处理
  - 同时设置 control_tensor 和 control_tensor_list 以兼容 Qwen

使用方法：
  python fix_qwen_batch_support.py

恢复原始版本：
  python fix_qwen_batch_support.py --restore
"""

import os
import sys
import argparse
from datetime import datetime

# 要修改的文件
FILE_PATH = "toolkit/dataloader_mixins.py"
BACKUP_SUFFIX = ".qwen_batch_backup"


def backup_file():
    """备份原始文件"""
    if not os.path.exists(FILE_PATH):
        print(f"❌ 错误: 找不到文件 {FILE_PATH}")
        return False

    backup_path = FILE_PATH + BACKUP_SUFFIX
    if not os.path.exists(backup_path):
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 已备份到 {backup_path}")
    else:
        print(f"ℹ️  备份文件已存在: {backup_path}")
    return True


def restore_file():
    """从备份恢复原始文件"""
    backup_path = FILE_PATH + BACKUP_SUFFIX
    if not os.path.exists(backup_path):
        print(f"❌ 错误: 找不到备份文件 {backup_path}")
        return False

    with open(backup_path, 'r', encoding='utf-8') as f:
        content = f.read()
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 已从备份恢复: {FILE_PATH}")
    return True


def apply_fix():
    """应用修复"""
    if not backup_file():
        return False

    print(f"\n正在修复 {FILE_PATH}...")

    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    modifications = []

    # ============================================================
    # 修改 1: 让控制图像在 match_target_res 时经过 bucket 处理
    # ============================================================

    old_code_1 = """            elif not self.use_raw_control_images:
                w, h = img.size
                if self.flip_x:
                    # do a flip
                    img = img.transpose(Image.FLIP_LEFT_RIGHT)
                if self.flip_y:
                    # do a flip
                    img = img.transpose(Image.FLIP_TOP_BOTTOM)

                if self.dataset_config.buckets:
                    # scale and crop based on file item
                    img = img.resize((self.scale_to_width, self.scale_to_height), Image.BICUBIC)
                    # img = transforms.CenterCrop((self.crop_height, self.crop_width))(img)
                    # crop
                    img = img.crop((
                        self.crop_x,
                        self.crop_y,
                        self.crop_x + self.crop_width,
                        self.crop_y + self.crop_height
                    ))
                else:
                    raise Exception("Control images not supported for non-bucket datasets")"""

    new_code_1 = """            elif not self.use_raw_control_images:
                # 标准模型：经过 bucket 处理
                w, h = img.size
                if self.flip_x:
                    # do a flip
                    img = img.transpose(Image.FLIP_LEFT_RIGHT)
                if self.flip_y:
                    # do a flip
                    img = img.transpose(Image.FLIP_TOP_BOTTOM)

                if self.dataset_config.buckets:
                    # scale and crop based on file item
                    img = img.resize((self.scale_to_width, self.scale_to_height), Image.BICUBIC)
                    # img = transforms.CenterCrop((self.crop_height, self.crop_width))(img)
                    # crop
                    img = img.crop((
                        self.crop_x,
                        self.crop_y,
                        self.crop_x + self.crop_width,
                        self.crop_y + self.crop_height
                    ))
                else:
                    raise Exception("Control images not supported for non-bucket datasets")
            else:
                # use_raw_control_images=True (Qwen 等模型)
                # 检查是否需要对齐到 target 尺寸（通过 model_config.match_target_res）
                sd = self.dataset_config.__dict__.get('sd', None) if hasattr(self.dataset_config, '__dict__') else None
                should_match_target = False

                # 从 sd.model_config.model_kwargs 获取 match_target_res 配置
                if sd is not None and hasattr(sd, 'model_config'):
                    model_kwargs = getattr(sd.model_config, 'model_kwargs', {})
                    should_match_target = model_kwargs.get('match_target_res', False)

                if should_match_target and self.dataset_config.buckets:
                    # match_target_res=True: 强制经过 bucket 处理，与 target 完全对齐
                    w, h = img.size
                    if self.flip_x:
                        img = img.transpose(Image.FLIP_LEFT_RIGHT)
                    if self.flip_y:
                        img = img.transpose(Image.FLIP_TOP_BOTTOM)

                    # 使用与 target 完全相同的 bucket 参数
                    img = img.resize((self.scale_to_width, self.scale_to_height), Image.BICUBIC)
                    img = img.crop((
                        self.crop_x,
                        self.crop_y,
                        self.crop_x + self.crop_width,
                        self.crop_y + self.crop_height
                    ))
                # else: 保持原始尺寸（默认行为）"""

    if old_code_1 in content:
        content = content.replace(old_code_1, new_code_1)
        modifications.append("✓ 修改 1: 添加 match_target_res 控制的 bucket 处理逻辑")
    else:
        print("⚠️  警告: 未找到修改点 1 的预期代码，可能已被修改")
        print("   请手动检查 toolkit/dataloader_mixins.py 第 916-937 行")

    # ============================================================
    # 修改 2: 同时设置 control_tensor 和 control_tensor_list
    # ============================================================

    old_code_2 = """        if len(control_tensors) == 0:
            self.control_tensor = None
        elif len(control_tensors) == 1:
            self.control_tensor = control_tensors[0]
        elif self.use_raw_control_images:
            # just send the list of tensors as their shapes wont match
            self.control_tensor_list = control_tensors
        else:
            self.control_tensor = torch.stack(control_tensors, dim=0)"""

    new_code_2 = """        if len(control_tensors) == 0:
            self.control_tensor = None
            self.control_tensor_list = None
        elif len(control_tensors) == 1:
            self.control_tensor = control_tensors[0]
            # 重要：如果是 Qwen 等模型，也需要设置 list 格式
            # 因为 Qwen 的文本编码和 forward pass 都依赖 control_tensor_list
            if self.use_raw_control_images:
                self.control_tensor_list = control_tensors  # [tensor1]
            else:
                self.control_tensor_list = None
        elif self.use_raw_control_images:
            # 多个控制图像：尝试 stack，如果尺寸一致（match_target_res=True）则可以成功
            try:
                self.control_tensor = torch.stack(control_tensors, dim=0)
            except RuntimeError:
                # 尺寸不一致，无法 stack
                self.control_tensor = None
            # 总是设置 list 格式供 Qwen 等模型使用
            self.control_tensor_list = control_tensors
        else:
            self.control_tensor = torch.stack(control_tensors, dim=0)
            self.control_tensor_list = None"""

    if old_code_2 in content:
        content = content.replace(old_code_2, new_code_2)
        modifications.append("✓ 修改 2: 同时设置 control_tensor 和 control_tensor_list")
    else:
        print("⚠️  警告: 未找到修改点 2 的预期代码，可能已被修改")
        print("   请手动检查 toolkit/dataloader_mixins.py 第 947-955 行")

    # 检查是否有修改
    if content == original_content:
        print("\n❌ 没有进行任何修改，可能代码已经被修改过")
        print("   或者代码结构发生了变化")
        return False

    # 写入修改后的内容
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    print("\n" + "="*70)
    print("✅ 修复完成！")
    print("="*70)
    print("\n应用的修改:")
    for i, mod in enumerate(modifications, 1):
        print(f"  {i}. {mod}")

    print("\n现在可以在配置文件中使用:")
    print("""
  model:
    name_or_path: "Qwen/Qwen-Image-Edit-2509"
    arch: "qwen_image_edit_plus"
    model_kwargs:
      match_target_res: true  # 启用控制图像对齐

  train:
    batch_size: 2  # 或更大
    gradient_accumulation: 2
""")

    print(f"\n备份文件: {FILE_PATH}{BACKUP_SUFFIX}")
    print(f"恢复命令: python {sys.argv[0]} --restore")
    print("="*70)

    return True


def main():
    parser = argparse.ArgumentParser(
        description='修复 Qwen Image Edit Plus 支持 batch_size > 1',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 应用修复
  python fix_qwen_batch_support.py

  # 恢复原始版本
  python fix_qwen_batch_support.py --restore

说明:
  - 修复会自动备份原始文件
  - 可以在 upstream 更新后重新运行此脚本
  - 使用 --restore 可以恢复到修改前的状态
        """
    )

    parser.add_argument('--restore', action='store_true',
                       help='恢复原始文件（从备份）')

    args = parser.parse_args()

    print("="*70)
    print("Qwen Image Edit Plus - Batch Size > 1 支持修复工具")
    print("="*70)
    print()

    if args.restore:
        success = restore_file()
    else:
        print("此脚本将修改:")
        print(f"  - {FILE_PATH}")
        print()
        print("修改内容:")
        print("  1. 添加基于 match_target_res 的控制图像 bucket 处理")
        print("  2. 同时设置 control_tensor 和 control_tensor_list")
        print()

        success = apply_fix()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
