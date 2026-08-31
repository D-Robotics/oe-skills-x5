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

- 在 PROJECT_ROOT 下创建 `.drobotics/`。
- 铺设 docs、skills、platforms、scripts、X5.md、skill-index.json、VERSION。
- 记录 INSTALLED_REF（安装来源锚点；未用 `--ref` 时回退为 VERSION 值）。
- 跳过含 eval.json 的 test/ 目录。
- 向 CLAUDE.md 或 AGENTS.md 注入路由规则，且重复执行不会重复注入。

### 升级已安装的 workspace

```bash
bash "$RESOURCE_DIR/setup.sh" --update --ref v1.0.0 "$PROJECT_ROOT"
```

`--update` 先比较已安装 `.drobotics/VERSION` 与资源 VERSION：相同则直接跳过（幂等）；不同则**重建** `.drobotics/`（先删除再铺设，旧版残留文件会被清除，但用户在 `.drobotics/` 内的本地修改也会被丢弃）。`--force` 在版本相同时强制重建。`--ref` 记录进 `INSTALLED_REF` 供安装器比对 registry。

## 5. 安装后检查

```bash
test -f "$PROJECT_ROOT/.drobotics/X5.md"
test -f "$PROJECT_ROOT/.drobotics/VERSION"
test -f "$PROJECT_ROOT/.drobotics/INSTALLED_REF"
test -f "$PROJECT_ROOT/.drobotics/skill-index.json"
test -f "$PROJECT_ROOT/.drobotics/skills/x5-router/SKILL.md"
test -f "$PROJECT_ROOT/.drobotics/scripts/search_local_docs.py"
```

## 6. 初始化后的使用顺序

1. 阅读 `.drobotics/X5.md`，了解工作区规则和内置 Skill 清单。
2. 以 `.drobotics/skill-index.json` 查找具体 Skill 路径。
3. 请求属于 X5 范畴但尚未落到具体 Skill 时，先使用 `.drobotics/skills/x5-router/SKILL.md`。
4. 对 API、参数、版本、流程或错误码不确定时，使用本地文档检索脚本。

## 7. 配置本地文档检索

X5 使用 `OE_DROBOTICS_DOC_ROOT`（兼容 `OE_X_SERIES_DOC_ROOT`）。未设置时检索脚本从项目及其父级工作区相对发现对应版本目录。无需配置网络文档服务。

```bash
python .drobotics/scripts/search_local_docs.py --query "X5 hb_mapper makertbin"
```

## 8. 常见问题

- 如果 setup.sh 报找不到 x5/ 目录，确认资源目录结构完整。
- 如果 .drobotics/ 已存在：直接重跑安装是覆盖式铺设（合并，不删旧文件）；升级请用 `--update`（重建式，先删后铺、无旧文件残留，但 `.drobotics/` 内的本地修改会丢失）。
- 如果找不到本地文档目录，设置 OE_DROBOTICS_DOC_ROOT 或使用 --root 指定文档根目录。
