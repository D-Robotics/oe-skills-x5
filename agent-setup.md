# X5 Workspace Agent Setup

本文档供 Agent 使用。用户将包含本文件的资源目录放到任意位置后，按以下步骤初始化项目。

## 1. 定位资源目录

找到本文件所在目录的绝对路径，记为 RESOURCE_DIR。

## 2. 确认项目根目录

按以下顺序确认 PROJECT_ROOT：

1. 检查用户当前工作目录及其父目录，查找 AGENTS.md 或 CLAUDE.md。
2. 找到后，将其所在目录作为候选 PROJECT_ROOT，必须向用户确认。
3. 未找到时，将当前工作目录作为候选 PROJECT_ROOT，必须向用户确认。

未经确认不得继续安装。所有资源必须安装到已确认的 PROJECT_ROOT。

## 3. 确保 Agent 指令文件存在

检查 PROJECT_ROOT 下是否存在 AGENTS.md 或 CLAUDE.md：

- 已存在时直接使用。
- 都不存在时，Claude Code 创建 CLAUDE.md；其他 Agent 创建 AGENTS.md。
- 创建空文件即可；setup.sh 会注入 X5 路由规则。

## 4. 执行安装

```bash
bash "$RESOURCE_DIR/setup.sh" "$PROJECT_ROOT"
```

安装会：

- 在 PROJECT_ROOT 下创建 `.drobotics-x5/`。
- 铺设 docs、skills、platforms、scripts、X5.md、skill-index.json、VERSION。
- 记录 INSTALLED_REF（安装来源锚点；未用 `--ref` 时回退为 VERSION 值）。
- 跳过含 eval.json 的 test/ 目录。
- 向 CLAUDE.md 或 AGENTS.md 注入路由规则，且重复执行不会重复注入。

### 升级已安装的 workspace

```bash
bash "$RESOURCE_DIR/setup.sh" --update --ref v1.0.0 "$PROJECT_ROOT"
```

`--update` 先比较已安装 `.drobotics-x5/VERSION` 与资源 VERSION：相同则直接跳过（幂等）；不同则**重建** `.drobotics-x5/`（先删除再铺设，旧版残留文件会被清除，但用户在 `.drobotics-x5/` 内的本地修改也会被丢弃）。`--force` 在版本相同时强制重建。`--ref` 记录进 `INSTALLED_REF` 供安装器比对 registry。

## 5. 安装后检查

```bash
test -f "$PROJECT_ROOT/.drobotics-x5/X5.md"
test -f "$PROJECT_ROOT/.drobotics-x5/VERSION"
test -f "$PROJECT_ROOT/.drobotics-x5/INSTALLED_REF"
test -f "$PROJECT_ROOT/.drobotics-x5/skill-index.json"
test -f "$PROJECT_ROOT/.drobotics-x5/skills/x5-router/SKILL.md"
```

## 6. 初始化后的使用顺序

1. 阅读 `.drobotics-x5/X5.md`，了解工作区规则和内置 Skill 清单。
2. 以 `.drobotics-x5/skill-index.json` 查找具体 Skill 路径。
3. 请求属于 X5 范畴但尚未落到具体 Skill 时，先使用 `.drobotics-x5/skills/x5-router/SKILL.md`。
4. 给出或执行工具链命令、API、参数、版本门槛、流程或错误码前，使用官方文档 MCP 搜索 X5 手册并读取命中的页面正文。板端 X5 Python API 查询 `rdk-x` 手册；若没有官方页面明确支持所需结论，则报告阻塞。

## 7. 官方文档检索

Codex 环境使用 `mcp__rdk_docs__search_docs`，X5 OE 手册参数为 `manual="oe-x5"`、`source="docs"`；板端 X5 Python API 可用 `manual="rdk-x"`。对检索到的官方 URL 必须再调用 `mcp__rdk_docs__get_page` 读取正文。包内离线材料不作为命令、API 或版本门槛的官方证据。

## 8. 常见问题

- 如果 setup.sh 报找不到 x5/ 目录，确认资源目录结构完整。
- 如果 .drobotics-x5/ 已存在：直接重跑安装是覆盖式铺设（合并，不删旧文件）；升级请用 `--update`（重建式，先删后铺、无旧文件残留，但 `.drobotics-x5/` 内的本地修改会丢失）。
- 如果 MCP 服务不可用或没有匹配的官方页面，停止依赖该事实的工具链操作并报告阻塞；不要改用本地文档推断。
