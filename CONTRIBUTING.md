# 修改与贡献指南

## 目录

```text
zloop_addon/                 插件源码与安装说明
tests/test_connected_blender.py   Blender 网格行为测试
tests/test_package.py        独立 Python 打包测试
build_release.py             打包与 SHA-256 校验
tools/release_notes.py       从更新日志提取版本说明
tools/draw_feature_diagrams.py    功能示意图生成脚本
CHANGELOG.md                每个版本的变化
docs/                       历史、已知问题与维护流程
docs/images/                README 功能示意图（PNG 与 SVG）
.github/workflows/          提交验证与标签发布
```

## 修改步骤

1. 从 `main` 创建工作分支，先在 Issues 描述问题或功能需求。
2. 修改插件并增加对应行为验证，避免只测试属性是否存在。
3. 将面向用户的变化写入 `CHANGELOG.md` 的 `[Unreleased]`，同步相关说明和已知限制。
4. 运行打包检查，以及与修改相关的 Blender 行为测试。
5. 提交 Pull Request，说明解决的问题、变更后的行为和实际测试环境。

不要在文档中声称未进行的 Blender 版本或实际模型测试已通过。不要把已知无效控件写成可用功能。不要在更新过程中删除用户网格或不属于插件的缓存。

## 验证

```bash
python -m unittest discover -s tests -p "test_package.py" -v
python build_release.py
blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python tests/test_connected_blender.py
```

网格测试会删除独立后台场景中的对象，必须以 `--factory-startup` 在独立进程运行。每次测试结束应检查退出码，不能只根据输出包含“PASS”判断成功。

## 提交问题

使用 Issues 中的中文错误或功能模板。错误报告请附 Blender 版本、插件版本、模型的选择与模式、衰减设置、步骤和结果；涉及指围联动时，还应描述掌部连接和网格密度。

## 发布

按 [维护流程](docs/MAINTENANCE.md) 更新版本，检查发布说明，推送标签。安装包由构建脚本生成并通过 Releases 分发，Git 中保存源码与版本记录。
