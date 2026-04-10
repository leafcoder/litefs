#!/usr/bin/env python3
"""
Flutter 中国镜像配置脚本
自动配置 Flutter/Dart 包管理镜像以加速下载
"""

import os
import sys
import platform
from pathlib import Path


MIRRORS = {
    "pub": "https://pub.flutter-io.cn",
    "storage": "https://storage.flutter-io.cn",
}

GRADLE_MIRROR = "https://mirrors.cloud.tencent.com/gradle/gradle-8.10.2-all.zip"

MAVEN_MIRRORS = [
    'maven { url = uri("https://storage.flutter-io.cn/download.flutter.io") }',
    'maven { url = uri("https://maven.aliyun.com/repository/google") }',
    'maven { url = uri("https://maven.aliyun.com/repository/public") }',
    'maven { url = uri("https://maven.aliyun.com/repository/gradle-plugin") }',
]


def get_shell_config_path() -> Path:
    """获取 shell 配置文件路径"""
    shell = os.environ.get("SHELL", "/bin/zsh")
    if "zsh" in shell:
        return Path.home() / ".zshrc"
    elif "bash" in shell:
        return Path.home() / ".bash_profile"
    return Path.home() / ".profile"


def check_mirror_config() -> dict:
    """检查当前镜像配置状态"""
    result = {
        "pub_url": os.environ.get("PUB_HOSTED_URL", ""),
        "storage_url": os.environ.get("FLUTTER_STORAGE_BASE_URL", ""),
        "shell_configured": False,
    }
    
    shell_config = get_shell_config_path()
    if shell_config.exists():
        content = shell_config.read_text()
        result["shell_configured"] = "PUB_HOSTED_URL" in content and "pub.flutter-io.cn" in content
    
    return result


def configure_shell_mirrors(backup: bool = True) -> bool:
    """配置 shell 环境变量镜像"""
    shell_config = get_shell_config_path()
    
    if backup and shell_config.exists():
        backup_path = shell_config.with_suffix(".rc.backup")
        if not backup_path.exists():
            import shutil
            shutil.copy(shell_config, backup_path)
            print(f"✅ 已备份配置文件到: {backup_path}")
    
    mirror_config = f'''
# Flutter 中国镜像 (由 flutter-china-deploy 自动配置)
export PUB_HOSTED_URL={MIRRORS["pub"]}
export FLUTTER_STORAGE_BASE_URL={MIRRORS["storage"]}
'''
    
    if shell_config.exists():
        content = shell_config.read_text()
        if "PUB_HOSTED_URL" in content:
            print("⚠️  检测到已有镜像配置，跳过写入")
            return True
    
    with open(shell_config, "a") as f:
        f.write(mirror_config)
    
    print(f"✅ 已写入镜像配置到: {shell_config}")
    print(f"   请运行: source {shell_config}")
    return True


def configure_gradle_wrapper(project_path: Path) -> bool:
    """配置 Gradle Wrapper 使用国内镜像"""
    gradle_wrapper_props = project_path / "android" / "gradle" / "wrapper" / "gradle-wrapper.properties"
    
    if not gradle_wrapper_props.exists():
        print(f"⚠️  未找到 gradle-wrapper.properties: {gradle_wrapper_props}")
        return False
    
    content = gradle_wrapper_props.read_text()
    
    if "mirrors.cloud.tencent.com/gradle" in content:
        print("✅ Gradle Wrapper 已配置腾讯云镜像")
        return True
    
    lines = content.split("\n")
    new_lines = []
    for line in lines:
        if line.startswith("distributionUrl="):
            line = f"distributionUrl=https\\://mirrors.cloud.tencent.com/gradle/gradle-8.10.2-all.zip"
            print("✅ 已更新 Gradle 下载地址为腾讯云镜像")
        new_lines.append(line)
    
    gradle_wrapper_props.write_text("\n".join(new_lines))
    return True


def configure_maven_repos(project_path: Path) -> bool:
    """配置 Maven 仓库镜像"""
    settings_gradle = project_path / "android" / "settings.gradle.kts"
    build_gradle = project_path / "android" / "build.gradle.kts"
    
    maven_config = """
    repositories {
        maven { url = uri("https://storage.flutter-io.cn/download.flutter.io") }
        maven { url = uri("https://maven.aliyun.com/repository/google") }
        maven { url = uri("https://maven.aliyun.com/repository/public") }
        maven { url = uri("https://maven.aliyun.com/repository/gradle-plugin") }
        google()
        mavenCentral()
    }
"""
    
    results = []
    
    for gradle_file in [settings_gradle, build_gradle]:
        if not gradle_file.exists():
            continue
        
        content = gradle_file.read_text()
        
        if "maven.aliyun.com" in content:
            print(f"✅ {gradle_file.name} 已配置阿里云镜像")
            results.append(True)
            continue
        
        if "repositories {" in content:
            print(f"⚠️  {gradle_file.name} 已有 repositories 配置，请手动添加镜像")
            results.append(False)
        else:
            print(f"⚠️  {gradle_file.name} 未找到 repositories 块，请手动配置")
            results.append(False)
    
    return any(results)


def configure_gradle_properties(project_path: Path) -> bool:
    """配置 gradle.properties 优化编译"""
    gradle_props = project_path / "android" / "gradle.properties"
    
    optimizations = {
        "kotlin.compiler.execution.strategy": "in-process",
        "org.gradle.daemon": "false",
        "android.useAndroidX": "true",
        "android.enableJetifier": "true",
    }
    
    if not gradle_props.exists():
        gradle_props.parent.mkdir(parents=True, exist_ok=True)
        content = ""
    else:
        content = gradle_props.read_text()
    
    lines = content.split("\n") if content else []
    existing_keys = {line.split("=")[0].strip() for line in lines if "=" in line}
    
    added = []
    for key, value in optimizations.items():
        if key not in existing_keys:
            lines.append(f"{key}={value}")
            added.append(key)
    
    if added:
        gradle_props.write_text("\n".join(lines))
        print(f"✅ 已添加 Gradle 优化配置: {', '.join(added)}")
    else:
        print("✅ Gradle 优化配置已存在")
    
    return True


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Flutter 中国镜像配置工具")
    parser.add_argument("--project", type=str, help="Flutter 项目路径")
    parser.add_argument("--check", action="store_true", help="检查当前配置状态")
    parser.add_argument("--shell", action="store_true", help="配置 Shell 环境变量")
    parser.add_argument("--gradle", action="store_true", help="配置 Gradle 镜像")
    parser.add_argument("--all", action="store_true", help="执行所有配置")
    
    args = parser.parse_args()
    
    if args.check:
        status = check_mirror_config()
        print("📊 当前镜像配置状态:")
        print(f"   PUB_HOSTED_URL: {status['pub_url'] or '未配置'}")
        print(f"   FLUTTER_STORAGE_BASE_URL: {status['storage_url'] or '未配置'}")
        print(f"   Shell 配置文件: {'已配置' if status['shell_configured'] else '未配置'}")
        return 0
    
    if args.all or args.shell:
        configure_shell_mirrors()
    
    if args.project:
        project_path = Path(args.project).resolve()
        
        if not (project_path / "pubspec.yaml").exists():
            print(f"❌ 未找到 Flutter 项目: {project_path}")
            return 1
        
        if args.all or args.gradle:
            configure_gradle_wrapper(project_path)
            configure_maven_repos(project_path)
            configure_gradle_properties(project_path)
    
    print("\n🎉 配置完成！请重启终端或运行 source 命令使环境变量生效。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
