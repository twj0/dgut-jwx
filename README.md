# 东莞理工学院教务系统选课工具

自动化选课工具，用于东莞理工学院教务系统（jwx.dgut.edu.cn）。

## 前置要求

### 1. Cookie 配置

**重要**: 本项目需要有效的教务系统 Cookie 才能运行。

在项目根目录创建 `cookie.json`、`cookie.jsonc` 或 `cookie.jsonl` 文件，格式如下：

```jsonc
[
    {
        "name": "bzb_jsxsd",
        "value": "YOUR_SESSION_ID_HERE",
        "domain": "jwx.dgut.edu.cn",
        "hostOnly": true,
        "path": "/",
        "secure": false,
        "httpOnly": true,
        "sameSite": null,
        "session": true
    }
]
```

#### 如何获取 Cookie？

1. **使用浏览器开发者工具**:
   - 登录教务系统 https://jwx.dgut.edu.cn
   - 按 F12 打开开发者工具
   - 切换到 "应用程序/Application" 或 "存储/Storage" 标签
   - 找到 Cookies → jwx.dgut.edu.cn
   - 复制 `bzb_jsxsd` 的值

2. **使用浏览器扩展** (推荐):
   - Firefox: [Cookie Quick Manager](https://addons.mozilla.org/zh-CN/firefox/addon/cookie-quick-manager/)
   - Chrome: [EditThisCookie](https://chrome.google.com/webstore/detail/editthiscookie/)
   - 导出为 JSON 格式

3. **简化格式** (仅需 session ID):
   ```json
   {
       "bzb_jsxsd": "YOUR_SESSION_ID_HERE"
   }
   ```

⚠️ **安全提示**:
- Cookie 文件已添加到 `.gitignore`，不会被提交到 Git
- 不要分享你的 Cookie，它等同于你的登录凭证
- Cookie 会过期，需要定期更新

### 2. Python 环境

本项目使用 `uv` 进行包管理：

```bash
# 安装 uv (如果还没有)
pip install uv

# 安装依赖
uv sync

# 运行脚本
uv run python script/xxx.py
```

## 项目结构

```
jwx/
├── cookie.jsonc              # Cookie 配置 (需自行创建，不提交到 Git)
├── README.md                 # 本文件
├── pyproject.toml            # 项目配置
├── .gitignore                # Git 忽略规则
│
├── script/                   # 脚本目录
│   └── network/              # 网络分析脚本
│       └── analyze_har.py    # HAR 文件分析工具
│
├── docs/                     # 文档目录
│   └── developer/
│       └── network/          # 网络分析文档
│           ├── API分析报告.md
│           ├── 技术实现文档.md
│           └── har_analysis.json
│
├── developer/                # 开发资源
│   └── network/              # 网络抓包文件
│       ├── README.txt
│       └── *.har             # HAR 抓包文件
│
└── reference/                # 参考代码
    └── repo/                 # 参考仓库
```

`src/jwx/` 为主代码（模块化 CLI），后续油猴脚本放在 `userscript/`。

## 使用说明

### 1. 分析网络请求

```bash
uv run python script/network/analyze_har.py
```

### 2. 查看文档

- [API 分析报告](docs/developer/network/API分析报告.md) - 选课 API 概览
- [技术实现文档](docs/developer/network/技术实现文档.md) - 详细字段说明和代码示例

### 3. CLI（当前推荐）

先准备好 `cookie.jsonc`（或设置环境变量 `JWX_COOKIE`），然后使用：

```bash
# 列出课程（默认 TSV：课程名/老师/学分/剩余/kcid/jx0404id）
uv run jwx courses list --length 10

# 按关键词筛选（服务端筛选）
uv run jwx courses list --kcxx 英语 --length 50

# 选择指定课程（需要 kcid + jx0404id）
uv run jwx select --kcid <KCID> --jx0404id <JX0404ID>

# 定时选课：到点后开始重试（间隔 0.5s，最多 120 次）
uv run jwx schedule select --at "2026-03-13 08:00:00" --attempts 120 --kcid <KCID> --jx0404id <JX0404ID>

# 自动选课：从列表里挑第一个满足条件的课程并选（默认 max-xf=1.0, min-seats=1）
uv run jwx auto --kcxx 通识 --length 50

# 定时自动选课：到点后循环“拉列表→挑候选→尝试选课”
uv run jwx schedule auto --at "2026-03-13 08:00:00" --kcxx 通识 --attempts 120 --interval 0.5
```

## 功能特性

- ✅ 课程列表查询（支持分页）
- ✅ 课程筛选（按学分、剩余人数、时间冲突）
- ✅ 自动选课
- ✅ 学分限制检查
- ⚠️ **禁用退选功能**（安全考虑）

## 安全约束

### 学分限制
- 总学分限制: 3 学分
- 当前已选: 2 学分
- **只能选择 1 学分的课程**

### 危险操作
- ❌ 退选课程 - 已禁用
- ❌ 批量操作 - 需谨慎使用
- ❌ 绕过冲突检查 - 禁止

## 开发指南

### 添加新功能

1. 在 `script/` 目录下创建脚本
2. 使用 `uv run python script/your_script.py` 运行
3. 更新文档

### 网络抓包

1. 使用浏览器开发者工具（F12）
2. 切换到 "网络/Network" 标签
3. 执行操作（如选课）
4. 右键 → "保存所有为 HAR"
5. 将 HAR 文件放到 `developer/network/` 目录
6. 运行分析脚本

## 常见问题

### Q: Cookie 过期怎么办？
A: 重新登录教务系统，按照上述步骤重新获取 Cookie。

### Q: 选课失败？
A: 检查：
1. Cookie 是否有效
2. 课程是否还有名额
3. 学分是否超限
4. 是否有时间冲突

### Q: 如何查看已选课程？
A: 访问 https://jwx.dgut.edu.cn/xsxkjg/comeXkjglb

## 免责声明

本工具仅供学习和研究使用。使用本工具时：
- 请遵守学校选课规定
- 不要进行恶意操作
- 不要频繁请求导致服务器压力
- 使用者需自行承担使用风险

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
