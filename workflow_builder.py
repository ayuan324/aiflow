import streamlit as st
import json
import requests
from datetime import datetime
import graphviz
from typing import Dict, List, Any
import os

# 页面配置
st.set_page_config(
    page_title="AI工作流构建平台",
    page_icon="🤖",
    layout="wide"
)

# 自定义样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1e3a8a;
        text-align: center;
        margin-bottom: 2rem;
    }
    .workflow-card {
        background-color: #f8fafc;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        margin-bottom: 1rem;
    }
    .node-box {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 8px;
        border: 2px solid #3b82f6;
        margin: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# 初始化session state
if 'workflows' not in st.session_state:
    st.session_state.workflows = []
if 'current_workflow' not in st.session_state:
    st.session_state.current_workflow = None
if 'api_key' not in st.session_state:
    # 尝试从Streamlit secrets获取API密钥
    try:
        st.session_state.api_key = st.secrets["OPENROUTER_API_KEY"]
    except:
        st.session_state.api_key = ""

# OpenRouter API 调用函数
def call_openrouter_api(prompt: str, api_key: str) -> Dict[str, Any]:
    """调用 OpenRouter API 生成工作流结构"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    system_prompt = """你是一个AI工作流设计专家。请根据用户的需求描述，生成一个结构化的工作流。
    
    请返回JSON格式的工作流，包含以下结构：
    {
        "name": "工作流名称",
        "description": "工作流描述",
        "nodes": [
            {
                "id": "节点ID",
                "type": "节点类型(input/llm/condition/output等)",
                "name": "节点名称",
                "description": "节点功能描述",
                "config": {
                    "prompt": "如果是LLM节点，这里是prompt模板",
                    "model": "使用的模型",
                    "other_params": "其他参数"
                },
                "connections": ["连接到的下一个节点ID"]
            }
        ]
    }
    
    节点类型包括：
    - input: 输入节点，接收用户输入
    - llm: 大语言模型节点，调用AI模型
    - condition: 条件判断节点
    - transform: 数据转换节点
    - output: 输出节点，返回结果
    """
    
    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请为以下需求生成工作流结构：{prompt}"}
        ],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            # 提取JSON部分
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != 0:
                workflow_json = json.loads(content[start:end])
                return {"success": True, "workflow": workflow_json}
            else:
                return {"success": False, "error": "无法解析工作流结构"}
        else:
            return {"success": False, "error": f"API调用失败: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# 生成工作流可视化
def create_workflow_visualization(workflow: Dict[str, Any]) -> graphviz.Digraph:
    """创建工作流的可视化图表"""
    dot = graphviz.Digraph(comment=workflow['name'])
    dot.attr(rankdir='TB')
    
    # 节点样式
    node_styles = {
        'input': {'shape': 'ellipse', 'style': 'filled', 'fillcolor': '#e0f2fe'},
        'llm': {'shape': 'box', 'style': 'filled', 'fillcolor': '#fef3c7'},
        'condition': {'shape': 'diamond', 'style': 'filled', 'fillcolor': '#fce7f3'},
        'transform': {'shape': 'box', 'style': 'filled', 'fillcolor': '#e0e7ff'},
        'output': {'shape': 'ellipse', 'style': 'filled', 'fillcolor': '#d1fae5'}
    }
    
    # 添加节点
    for node in workflow['nodes']:
        style = node_styles.get(node['type'], {'shape': 'box'})
        dot.node(node['id'], node['name'], **style)
    
    # 添加连接
    for node in workflow['nodes']:
        if 'connections' in node:
            for target in node['connections']:
                dot.edge(node['id'], target)
    
    return dot

# 主界面
st.markdown('<h1 class="main-header">🤖 AI工作流构建平台</h1>', unsafe_allow_html=True)
st.markdown("### 让每个人都能轻松构建AI应用")

# 侧边栏 - API配置
with st.sidebar:
    st.header("⚙️ 配置")
    api_key = st.text_input("OpenRouter API Key", 
                           value=st.session_state.api_key, 
                           type="password",
                           help="请输入您的OpenRouter API密钥")
    if api_key:
        st.session_state.api_key = api_key
        st.success("API密钥已配置")
    
    st.divider()
    
    # 预设模板
    st.header("📚 快速开始模板")
    templates = {
        "客服机器人": "创建一个智能客服机器人，能够理解用户问题并提供准确回答",
        "内容生成器": "构建一个根据主题自动生成文章的工作流",
        "数据分析助手": "设计一个分析用户数据并生成洞察报告的工作流",
        "翻译工作流": "创建多语言翻译工作流，支持中英日韩等语言"
    }
    
    for name, desc in templates.items():
        if st.button(f"🎯 {name}", use_container_width=True):
            st.session_state.template_prompt = desc

# 主要内容区域
tab1, tab2, tab3 = st.tabs(["🚀 创建工作流", "📊 我的工作流", "🛠️ 工作流编辑器"])

# Tab1: 创建工作流
with tab1:
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.subheader("描述您的需求")
        
        # 检查是否有模板被选中
        if 'template_prompt' in st.session_state:
            user_prompt = st.text_area(
                "请用自然语言描述您想要构建的AI应用",
                value=st.session_state.template_prompt,
                height=150,
                placeholder="例如：我想创建一个智能客服机器人，能够回答产品相关问题..."
            )
            del st.session_state.template_prompt
        else:
            user_prompt = st.text_area(
                "请用自然语言描述您想要构建的AI应用",
                height=150,
                placeholder="例如：我想创建一个智能客服机器人，能够回答产品相关问题..."
            )
        
        if st.button("🎨 生成工作流", type="primary", use_container_width=True):
            if not st.session_state.api_key:
                st.error("请先在侧边栏配置OpenRouter API密钥")
            elif not user_prompt:
                st.error("请输入您的需求描述")
            else:
                with st.spinner("正在生成工作流..."):
                    result = call_openrouter_api(user_prompt, st.session_state.api_key)
                    
                    if result['success']:
                        st.session_state.current_workflow = result['workflow']
                        st.success("工作流生成成功！")
                    else:
                        st.error(f"生成失败：{result['error']}")
    
    with col2:
        st.subheader("💡 使用提示")
        st.info("""
        **如何描述您的需求：**
        1. 明确说明应用的主要功能
        2. 描述输入和输出的形式
        3. 说明需要的处理步骤
        4. 提及特殊要求或条件
        
        **示例：**
        "创建一个简历优化助手，用户上传简历后，系统分析简历内容，根据目标岗位给出改进建议，并生成优化后的版本。"
        """)

# 显示生成的工作流
if st.session_state.current_workflow:
    st.divider()
    st.subheader("📋 生成的工作流")
    
    col1, col2 = st.columns([2, 3])
    
    with col1:
        st.markdown("#### 工作流信息")
        workflow = st.session_state.current_workflow
        st.markdown(f"**名称：** {workflow['name']}")
        st.markdown(f"**描述：** {workflow['description']}")
        
        st.markdown("#### 节点列表")
        for node in workflow['nodes']:
            with st.expander(f"{node['name']} ({node['type']})"):
                st.write(f"**描述：** {node['description']}")
                if 'config' in node and 'prompt' in node['config']:
                    st.write(f"**Prompt模板：**")
                    st.code(node['config']['prompt'])
        
        if st.button("💾 保存工作流", type="primary"):
            workflow['created_at'] = datetime.now().isoformat()
            st.session_state.workflows.append(workflow)
            st.success("工作流已保存！")
    
    with col2:
        st.markdown("#### 工作流可视化")
        try:
            graph = create_workflow_visualization(workflow)
            st.graphviz_chart(graph.source)
        except Exception as e:
            st.error(f"可视化失败：{str(e)}")

# Tab2: 我的工作流
with tab2:
    st.subheader("📚 已保存的工作流")
    
    if st.session_state.workflows:
        for idx, workflow in enumerate(st.session_state.workflows):
            with st.container():
                st.markdown(f"""
                <div class="workflow-card">
                    <h4>{workflow['name']}</h4>
                    <p>{workflow['description']}</p>
                    <small>创建时间：{workflow.get('created_at', 'Unknown')}</small>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns([1, 1, 1])
                with col1:
                    if st.button(f"查看", key=f"view_{idx}"):
                        st.session_state.current_workflow = workflow
                        st.rerun()
                with col2:
                    if st.button(f"编辑", key=f"edit_{idx}"):
                        st.session_state.editing_workflow = workflow
                        st.info("请前往工作流编辑器进行编辑")
                with col3:
                    if st.button(f"删除", key=f"delete_{idx}"):
                        st.session_state.workflows.pop(idx)
                        st.rerun()
    else:
        st.info("暂无保存的工作流，请先创建一个新的工作流。")

# Tab3: 工作流编辑器
with tab3:
    st.subheader("🛠️ 工作流编辑器")
    
    if 'editing_workflow' in st.session_state and st.session_state.editing_workflow:
        workflow = st.session_state.editing_workflow
        
        # 基本信息编辑
        col1, col2 = st.columns(2)
        with col1:
            workflow['name'] = st.text_input("工作流名称", value=workflow['name'])
        with col2:
            workflow['description'] = st.text_input("工作流描述", value=workflow['description'])
        
        st.divider()
        
        # 节点编辑
        st.markdown("### 节点管理")
        
        for i, node in enumerate(workflow['nodes']):
            with st.expander(f"节点 {i+1}: {node['name']}"):
                node['name'] = st.text_input(f"节点名称", value=node['name'], key=f"node_name_{i}")
                node['description'] = st.text_area(f"节点描述", value=node['description'], key=f"node_desc_{i}")
                
                if node['type'] == 'llm' and 'config' in node:
                    st.markdown("**LLM配置**")
                    if 'prompt' in node['config']:
                        node['config']['prompt'] = st.text_area(
                            "Prompt模板", 
                            value=node['config']['prompt'], 
                            key=f"node_prompt_{i}",
                            height=100
                        )
                    
                    model_options = [
                        "openai/gpt-3.5-turbo",
                        "openai/gpt-4",
                        "anthropic/claude-2",
                        "meta-llama/llama-2-70b-chat"
                    ]
                    current_model = node['config'].get('model', model_options[0])
                    node['config']['model'] = st.selectbox(
                        "选择模型",
                        options=model_options,
                        index=model_options.index(current_model) if current_model in model_options else 0,
                        key=f"node_model_{i}"
                    )
        
        # 保存更改
        if st.button("💾 保存更改", type="primary"):
            # 更新工作流
            for idx, w in enumerate(st.session_state.workflows):
                if w.get('created_at') == workflow.get('created_at'):
                    st.session_state.workflows[idx] = workflow
                    break
            st.success("工作流已更新！")
            del st.session_state.editing_workflow
    else:
        st.info('请从"我的工作流"中选择一个工作流进行编辑。')

# 页脚
st.divider()
st.markdown("""
<div style="text-align: center; color: #6b7280; font-size: 0.875rem;">
    基于 Streamlit 和 OpenRouter 构建 | MVP 版本
</div>
""", unsafe_allow_html=True)
