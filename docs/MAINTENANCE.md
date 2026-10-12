# 维护与发布流程

## 日常维护

- Git 提交记录代码变化，`CHANGELOG.md` 记录用户可感知的版本变化。
- 处理问题时先复现，再修改，再运行对应验证；不要先宣称问题已修复。
- 插件默认模块名保持 `zloop_addon`，兼容更新安装。
- 注册/注销新增属性、类、定时器或回调时，必须同时实现清理与重复注册验证。
- 整理仓库或文档可沿用当前插件版本；改变插件行为时增加版本号。
- 工作流依赖使用已核验的固定提交；更新运行时依赖后重新验证 Actions，避免保留弃用配置。

## 版本编号

- 修复已有功能：增加补丁号，例如 `2.2.1`。
- 兼容地增加功能：增加次版本，例如 `2.3.0`。
- 不兼容地改变接口或工作方式：增加主版本。

每个发布版本都需同步 `zloop_addon/__init__.py` 中的 `bl_info["version"]`、根 README、插件中文说明和 `CHANGELOG.md`。`vX.Y.Z` 标签必须对应相同源码版本，不能把不同源码发布成相同版本。

## 本地发布检查

```bash
python -m unittest discover -s tests -p "test_package.py" -v
python tools/release_notes.py --version 2.2.0 --output dist/release-notes.md
python build_release.py
```

然后运行 Blender 网格测试。打开 `dist/release-notes.md` 审阅中文变化说明，核对 `dist/SHA256SUMS.txt` 和 ZIP 内容。

## GitHub 发布

1. 把 `[Unreleased]` 中的条目移入 `## [X.Y.Z] - YYYY-MM-DD`，使用香港时区的发布日期。
2. 更新版本号和说明，将通过验证的源码合入 `main`。
3. 创建并推送标签，例如：

```bash
git tag -a v2.2.1 -m "ZLoop 2.2.1"
git push origin v2.2.1
```

GitHub Actions 会验证标签与元数据、提取对应版本说明、构建安装包，并运行 Blender 4.4.3 / 5.1.1 网格测试。全部通过后创建 Release，附上版本 ZIP 和 `SHA256SUMS.txt`。

工作流使用 GitHub 自动提供的令牌，不需要把个人令牌放进仓库。普通检查仅申请读取仓库权限，发布任务申请 `contents: write`。若组织策略关闭 Actions 或禁止其创建 Release，需先由仓库管理员调整相应设置。

发布失败时先检查 Actions 日志并修复问题。已经对外发布的标签与安装包保持不变；新修复使用新版本。需要回退时使用旧 Release 的安装包，在 Blender 中禁用当前插件后安装旧包。

## 验证记录

每次 Release 的说明应写明测试使用的 Blender 版本、自动化测试范围、实际模型验证结果和剩余限制。不能用语法检查替代插件加载或网格变形验证。
