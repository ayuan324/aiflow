# AI工作流构建平台

基于 Streamlit 和 OpenRouter 的低代码 AI 工作流构建平台，让每个人都能轻松构建AI应用。

🔗 [在线演示](https://your-app-name.streamlit.app)

## 功能特点

- 🚀 **自然语言生成工作流** - 只需描述需求，自动生成工作流结构
- 📊 **可视化编辑器** - 直观的工作流可视化和编辑界面
- 🎯 **预设模板库** - 提供常用场景的快速模板
- 🔧 **灵活配置** - 支持多种LLM模型和节点类型

## 本地运行

1. 克隆仓库
```bash
git clone https://github.com/yourusername/ai-workflow-builder.git
cd ai-workflow-builder
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置API密钥
创建 `.streamlit/secrets.toml` 文件：
```toml
OPENROUTER_API_KEY = "your-api-key-here"
```

4. 运行应用
```bash
streamlit run workflow_builder.py
```

## 部署到 Streamlit Cloud

1. Fork 这个仓库到您的 GitHub
2. 登录 [Streamlit Cloud](https://streamlit.io/cloud)
3. 点击 "New app"
4. 选择您的仓库和分支
5. 在 Advanced settings 中配置 Secrets：
   - 添加 `OPENROUTER_API_KEY = "your-api-key"`
6. 点击 Deploy

## 使用指南

### 创建工作流
1. 在主页面描述您的需求
2. 或选择预设模板快速开始
3. 点击"生成工作流"按钮
4. 查看生成的工作流结构和可视化图

### 编辑工作流
1. 在"我的工作流"标签查看已保存的工作流
2. 点击"编辑"进入编辑器
3. 修改节点配置、Prompt模板等
4. 保存更改

## 技术栈

- **前端**: Streamlit
- **LLM API**: OpenRouter
- **可视化**: Graphviz
- **语言**: Python 3.8+

## 获取 OpenRouter API Key

1. 访问 [OpenRouter](https://openrouter.ai/)
2. 注册账号
3. 在 Dashboard 中创建 API Key
4. 复制 Key 到应用配置中

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
