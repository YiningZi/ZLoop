# ZLA · ZLoop 环线工具

为 Blender 网格建模提供中文环线测量与周长调整。适合调整手指指围、管状网格截面等需要精确周长的局部位置。

当前插件版本：**2.2.0**。最低声明版本：**Blender 4.4**。网格回归测试已在 **4.4.3 / 5.1.1** 通过。

## 安装

1. 从 [Releases](https://github.com/YiningZi/ZLA/releases/latest) 下载 `ZLoop_Addon_2.2.0.zip`。GitHub 的“Source code”ZIP 是整个开发仓库，安装时应选择带 `ZLoop_Addon_` 前缀的插件包。
2. 在 Blender 的“编辑 → 偏好设置 → 插件”菜单选择“从磁盘安装”，选择该 ZIP 并启用插件。
3. 在 3D 视图按 **N**，打开 **ZLoop** 标签页。

更新时先禁用旧版，再安装新版并启用。插件使用同一个 `zloop_addon` 模块名。注册、注销会清理本插件的 RNA 类和 Scene 属性；这不能替代 Blender 对所有旧模块的加载管理。

## 使用

1. 选择网格物体，进入编辑模式，选择一条完整闭合环线。
2. 点击 **测量当前环线**，在 Blender 状态栏查看总长度、边数和平均边长。
3. 输入 **目标周长**，设置衰减参数，点击 **应用环线缩放**。需要撤销时按 **Ctrl + Z**。

面板始终显示；缩放需要处于网格编辑模式并选中有效闭合环线。当前版本每次调整一条环线。

## 局部影响控制

| 选项 | 行为 |
| --- | --- |
| 自动衰减 | 按环线转角、边长和相邻网格间距估算影响半径；属于局部几何启发式，不是曲面重建算法。 |
| 仅影响相连项 | 默认开启，沿网格连接计算比例编辑距离，避免仅因空间靠近就带动其他手指。 |
| 衰减半径 | 关闭自动衰减后手动设置影响范围。 |
| 衰减类型 | 选择平滑、球形、线性等 Blender 比例编辑曲线。 |

调整指围建议同时开启 **自动衰减** 和 **仅影响相连项**。手指通过掌部相连，过大的半径仍可能传到其他手指。

更多说明：[插件使用说明](zloop_addon/README_CN.md)、[已知限制与改进计划](docs/KNOWN_ISSUES.md)。

## 版本与维护

- [版本更新日志](CHANGELOG.md)：按版本记录新增、修复、行为变化及验证情况。
- [贡献与修改指南](CONTRIBUTING.md)：修改代码、运行验证与提交问题的方法。
- [维护与发布流程](docs/MAINTENANCE.md)：版本号、打包、标签和 Release 的管理。
- [历史版本记录](docs/VERSION_HISTORY.md)：原始 2.0.0、2.1.0 以及 2.2.0 的来源与归档范围。

## 本地构建

打包只使用 Python 标准库，不需要 Blender：

```bash
python build_release.py
python -m unittest discover -s tests -p "test_package.py" -v
```

安装包与校验文件输出到 `dist/`。脚本自动读取插件版本号，可在 Windows、Linux 和 macOS 上运行。

网格行为测试需要 Blender，且必须在独立后台进程执行：

```bash
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python tests/test_connected_blender.py
```

[GitHub Actions](https://github.com/YiningZi/ZLA/actions) 对代码提交运行打包检查及 Blender 4.4.3 / 5.1.1 网格测试。推送与插件版本一致的 `vX.Y.Z` 标签后，通过验证的安装包和该版本说明会发布到 Releases。
