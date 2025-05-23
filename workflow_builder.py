import streamlit as st
import json
import requests
from datetime import datetime
import graphviz
from typing import Dict, List, Any, Optional
import os
import uuid
from dataclasses import dataclass, field
from enum import Enum
import streamlit.components.v1 as components

# 页面配置
st.set_page_config(
    page_title="AI工作流构建平台",
    page_icon="🤖",
    layout="wide"
)

# 节点类型定义（参考Dify）
class NodeType(Enum):
    START = "start"
    END = "end"
    LLM = "llm"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    HTTP_REQUEST = "http_request"
    CODE = "code"
    CONDITION = "condition"
    QUESTION_CLASSIFIER = "question_classifier"
    TEMPLATE = "template"
    VARIABLE = "variable"
    AGENT = "agent"
    TOOL = "tool"
    ITERATION = "iteration"
    PARAMETER_EXTRACTOR = "parameter_extractor"

# 节点配置
NODE_CONFIGS = {
    NodeType.START: {
        "name": "开始",
        "icon": "▶️",
        "color": "#e0f2fe",
        "description": "工作流起点，接收用户输入",
        "inputs": [],
        "outputs": ["query", "files"],
        "config_fields": {
            "input_fields": {
                "type": "list",
                "label": "输入字段",
                "items": ["text", "file", "number", "select", "date", "email"]
            }
        }
    },
    NodeType.END: {
        "name": "结束",
        "icon": "🏁",
        "color": "#d1fae5",
        "description": "工作流终点，输出最终结果",
        "inputs": ["output"],
        "outputs": [],
        "config_fields": {
            "output_type": {
                "type": "select",
                "label": "输出类型",
                "options": ["text", "json", "file", "stream"]
            }
        }
    },
    NodeType.LLM: {
        "name": "大语言模型",
        "icon": "🧠",
        "color": "#fef3c7",
        "description": "调用LLM处理文本",
        "inputs": ["prompt", "context"],
        "outputs": ["text", "usage"],
        "config_fields": {
            "model": {
                "type": "select",
                "label": "模型",
                "options": ["gpt-3.5-turbo", "gpt-4", "claude-3", "llama-2"]
            },
            "prompt_template": {
                "type": "textarea",
                "label": "提示词模板"
            },
            "temperature": {
                "type": "slider",
                "label": "温度",
                "min": 0,
                "max": 2,
                "default": 0.7
            },
            "max_tokens": {
                "type": "number",
                "label": "最大令牌数",
                "default": 1000
            }
        }
    },
    NodeType.KNOWLEDGE_RETRIEVAL: {
        "name": "知识库检索",
        "icon": "📚",
        "color": "#e0e7ff",
        "description": "从知识库中检索相关内容",
        "inputs": ["query"],
        "outputs": ["results", "citations"],
        "config_fields": {
            "knowledge_base": {
                "type": "select",
                "label": "知识库",
                "options": ["产品文档", "FAQ", "用户手册"]
            },
            "retrieval_mode": {
                "type": "select",
                "label": "检索模式",
                "options": ["semantic", "keyword", "hybrid"]
            },
            "top_k": {
                "type": "number",
                "label": "返回结果数",
                "default": 5
            }
        }
    },
    NodeType.HTTP_REQUEST: {
        "name": "HTTP请求",
        "icon": "🌐",
        "color": "#fce7f3",
        "description": "调用外部API",
        "inputs": ["url", "params", "body"],
        "outputs": ["response", "status"],
        "config_fields": {
            "method": {
                "type": "select",
                "label": "请求方法",
                "options": ["GET", "POST", "PUT", "DELETE"]
            },
            "url": {
                "type": "text",
                "label": "URL"
            },
            "headers": {
                "type": "json",
                "label": "请求头"
            },
            "timeout": {
                "type": "number",
                "label": "超时时间（秒）",
                "default": 30
            }
        }
    },
    NodeType.CODE: {
        "name": "代码执行",
        "icon": "💻",
        "color": "#f0f9ff",
        "description": "执行Python或JavaScript代码",
        "inputs": ["input"],
        "outputs": ["output"],
        "config_fields": {
            "language": {
                "type": "select",
                "label": "编程语言",
                "options": ["python", "javascript"]
            },
            "code": {
                "type": "code",
                "label": "代码"
            },
            "packages": {
                "type": "list",
                "label": "依赖包"
            }
        }
    },
    NodeType.CONDITION: {
        "name": "条件判断",
        "icon": "🔀",
        "color": "#fdf4ff",
        "description": "基于条件分支执行",
        "inputs": ["input"],
        "outputs": ["true_output", "false_output"],
        "config_fields": {
            "condition": {
                "type": "text",
                "label": "条件表达式"
            },
            "operator": {
                "type": "select",
                "label": "操作符",
                "options": ["==", "!=", ">", "<", ">=", "<=", "contains", "regex"]
            }
        }
    },
    NodeType.AGENT: {
        "name": "智能体",
        "icon": "🤖",
        "color": "#eff6ff",
        "description": "自主决策和执行任务",
        "inputs": ["task", "tools"],
        "outputs": ["result", "steps"],
        "config_fields": {
            "agent_type": {
                "type": "select",
                "label": "智能体类型",
                "options": ["ReAct", "OpenAI Functions", "AutoGPT"]
            },
            "available_tools": {
                "type": "multiselect",
                "label": "可用工具"
            },
            "max_iterations": {
                "type": "number",
                "label": "最大迭代次数",
                "default": 5
            }
        }
    }
}

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
        cursor: move;
        transition: all 0.3s ease;
    }
    .node-box:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .node-type-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 10px;
        margin-bottom: 20px;
    }
    .node-type-item {
        padding: 10px;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s;
    }
    .node-type-item:hover {
        background-color: #f3f4f6;
        border-color: #3b82f6;
    }
    .workflow-canvas {
        min-height: 500px;
        background-color: #f9fafb;
        border: 2px dashed #d1d5db;
        border-radius: 8px;
        padding: 20px;
        position: relative;
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
if 'editing_node' not in st.session_state:
    st.session_state.editing_node = None

# OpenRouter API 调用函数（增强版）
def call_openrouter_api(prompt: str, api_key: str) -> Dict[str, Any]:
    """调用 OpenRouter API 生成工作流结构"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 定义可用的节点类型
    node_types_description = "\n".join([
        f"- {node_type.value}: {config['description']}"
        for node_type, config in NODE_CONFIGS.items()
    ])
    
    system_prompt = f"""你是一个AI工作流设计专家。请根据用户的需求描述，生成一个结构化的工作流。

可用的节点类型：
{node_types_description}

请返回JSON格式的工作流，包含以下结构：
{{
    "name": "工作流名称",
    "description": "工作流描述",
    "nodes": [
        {{
            "id": "node_uuid",
            "type": "节点类型(使用上述类型之一)",
            "name": "节点名称",
            "description": "节点功能描述",
            "position": {{"x": 0, "y": 0}},
            "config": {{
                // 根据节点类型填充相应的配置
            }},
            "connections": [
                {{
                    "target_node_id": "目标节点ID",
                    "source_output": "源输出端口",
                    "target_input": "目标输入端口"
                }}
            ]
        }}
    ]
}}

注意：
1. 每个工作流必须有且仅有一个start节点和至少一个end节点
2. 节点之间的连接必须匹配输入输出端口
3. 节点位置应该合理分布，便于可视化
4. 根据实际需求选择合适的节点类型
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
                # 为每个节点生成唯一ID
                for node in workflow_json['nodes']:
                    if 'id' not in node or not node['id']:
                        node['id'] = str(uuid.uuid4())[:8]
                return {"success": True, "workflow": workflow_json}
            else:
                return {"success": False, "error": "无法解析工作流结构"}
        else:
            return {"success": False, "error": f"API调用失败: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# 创建交互式工作流编辑器的HTML/JavaScript
def create_interactive_editor(workflow: Dict[str, Any]) -> str:
    """创建交互式工作流编辑器"""
    nodes_js = json.dumps(workflow['nodes'])
    
    html = f"""
    <div id="workflow-editor" style="width: 100%; height: 600px; position: relative;">
        <svg id="workflow-svg" width="100%" height="100%" style="background: #f9fafb;">
            <defs>
                <marker id="arrowhead" markerWidth="10" markerHeight="7" 
                        refX="10" refY="3.5" orient="auto">
                    <polygon points="0 0, 10 3.5, 0 7" fill="#6b7280" />
                </marker>
            </defs>
        </svg>
    </div>
    
    <script>
        const nodes = {nodes_js};
        const svg = document.getElementById('workflow-svg');
        const svgNS = "http://www.w3.org/2000/svg";
        
        // 节点配置
        const nodeConfigs = {json.dumps({k.value: v for k, v in NODE_CONFIGS.items()})};
        
        // 渲染节点
        nodes.forEach(node => {{
            const g = document.createElementNS(svgNS, 'g');
            g.setAttribute('transform', `translate(${{node.position.x}}, ${{node.position.y}})`);
            g.setAttribute('class', 'node-group');
            g.setAttribute('data-node-id', node.id);
            
            // 节点背景
            const rect = document.createElementNS(svgNS, 'rect');
            rect.setAttribute('width', '180');
            rect.setAttribute('height', '80');
            rect.setAttribute('rx', '8');
            rect.setAttribute('fill', nodeConfigs[node.type].color);
            rect.setAttribute('stroke', '#3b82f6');
            rect.setAttribute('stroke-width', '2');
            rect.setAttribute('class', 'node-rect');
            
            // 节点图标和名称
            const text = document.createElementNS(svgNS, 'text');
            text.setAttribute('x', '90');
            text.setAttribute('y', '35');
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('font-size', '14');
            text.setAttribute('font-weight', 'bold');
            text.textContent = (nodeConfigs[node.type] ? nodeConfigs[node.type].icon : '📦') + ' ' + node.name;
            
            // 节点描述
            const desc = document.createElementNS(svgNS, 'text');
            desc.setAttribute('x', '90');
            desc.setAttribute('y', '55');
            desc.setAttribute('text-anchor', 'middle');
            desc.setAttribute('font-size', '12');
            desc.setAttribute('fill', '#6b7280');
            desc.textContent = node.type;
            
            g.appendChild(rect);
            g.appendChild(text);
            g.appendChild(desc);
            
            // 添加拖拽功能
            let isDragging = false;
            let startX, startY;
            
            g.addEventListener('mousedown', (e) => {{
                isDragging = true;
                startX = e.clientX - node.position.x;
                startY = e.clientY - node.position.y;
                g.style.cursor = 'grabbing';
            }});
            
            svg.addEventListener('mousemove', (e) => {{
                if (isDragging) {{
                    node.position.x = e.clientX - startX;
                    node.position.y = e.clientY - startY;
                    g.setAttribute('transform', `translate(${{node.position.x}}, ${{node.position.y}})`);
                    updateConnections();
                }}
            }});
            
            svg.addEventListener('mouseup', () => {{
                isDragging = false;
                g.style.cursor = 'grab';
            }});
            
            svg.appendChild(g);
        }});
        
        // 渲染连接线
        function updateConnections() {{
            // 清除旧连接线
            document.querySelectorAll('.connection-line').forEach(line => line.remove());
            
            nodes.forEach(node => {{
                if (node.connections) {{
                    node.connections.forEach(conn => {{
                        const targetNode = nodes.find(n => n.id === conn.target_node_id);
                        if (targetNode) {{
                            const line = document.createElementNS(svgNS, 'path');
                            const startX = node.position.x + 180;
                            const startY = node.position.y + 40;
                            const endX = targetNode.position.x;
                            const endY = targetNode.position.y + 40;
                            
                            // 贝塞尔曲线
                            const midX = (startX + endX) / 2;
                            const d = `M ${{startX}} ${{startY}} C ${{midX}} ${{startY}}, ${{midX}} ${{endY}}, ${{endX}} ${{endY}}`;
                            
                            line.setAttribute('d', d);
                            line.setAttribute('fill', 'none');
                            line.setAttribute('stroke', '#6b7280');
                            line.setAttribute('stroke-width', '2');
                            line.setAttribute('marker-end', 'url(#arrowhead)');
                            line.setAttribute('class', 'connection-line');
                            
                            svg.insertBefore(line, svg.firstChild);
                        }}
                    }});
                }}
            }});
        }}
        
        // 初始渲染连接线
        updateConnections();
        
        // 添加节点样式
        document.querySelectorAll('.node-group').forEach(g => {{
            g.style.cursor = 'grab';
            g.addEventListener('mouseenter', () => {{
                g.querySelector('.node-rect').setAttribute('filter', 'drop-shadow(0 4px 6px rgba(0, 0, 0, 0.1))');
            }});
            g.addEventListener('mouseleave', () => {{
                g.querySelector('.node-rect').removeAttribute('filter');
            }});
        }});
    </script>
    """
    
    return html

# 生成工作流可视化（静态版本，作为备用）
def create_workflow_visualization(workflow: Dict[str, Any]) -> graphviz.Digraph:
    """创建工作流的可视化图表"""
    dot = graphviz.Digraph(comment=workflow['name'])
    dot.attr(rankdir='TB', splines='ortho')
    
    # 添加节点
    for node in workflow['nodes']:
        try:
            node_type_enum = NodeType(node['type'])
            node_config = NODE_CONFIGS.get(node_type_enum, {})
        except ValueError:
            # 如果节点类型不在枚举中，使用默认配置
            node_config = {'icon': '📦', 'color': '#f0f0f0'}
        
        label = f"{node_config.get('icon', '')} {node['name']}\\n{node['type']}"
        
        dot.node(
            node['id'], 
            label,
            shape='box',
            style='filled,rounded',
            fillcolor=node_config.get('color', '#ffffff'),
            fontsize='12'
        )
    
    # 添加连接
    for node in workflow['nodes']:
        if 'connections' in node:
            for conn in node['connections']:
                dot.edge(
                    node['id'], 
                    conn['target_node_id'],
                    label=f"{conn.get('source_output', '')}→{conn.get('target_input', '')}"
                )
    
    return dot

# 主界面
st.markdown('<h1 class="main-header">🤖 AI工作流构建平台</h1>', unsafe_allow_html=True)
st.markdown("### 让每个人都能轻松构建AI应用")

# 侧边栏 - API配置和节点库
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
    
    # 节点库
    st.header("🧩 节点库")
    st.markdown("拖拽节点到画布上")
    
    for node_type, config in NODE_CONFIGS.items():
        st.markdown(f"""
        <div class="node-type-item">
            <div style="font-size: 24px;">{config['icon']}</div>
            <div style="font-weight: bold;">{config['name']}</div>
            <div style="font-size: 12px; color: #6b7280;">{config['description']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # 预设模板
    st.header("📚 快速开始模板")
    templates = {
        "客服机器人": "创建一个智能客服机器人，需要先从知识库检索相关信息，然后用LLM生成回答",
        "内容生成器": "构建一个根据主题自动生成文章的工作流，包括研究、大纲生成和内容创作",
        "数据分析助手": "设计一个分析用户数据的工作流，包括数据获取、处理、分析和报告生成",
        "API集成工作流": "创建一个调用外部API并处理返回数据的工作流",
        "智能体应用": "构建一个能够自主决策和执行任务的AI智能体"
    }
    
    for name, desc in templates.items():
        if st.button(f"🎯 {name}", use_container_width=True):
            st.session_state.template_prompt = desc

# 主要内容区域
tab1, tab2, tab3, tab4 = st.tabs(["🚀 创建工作流", "📊 我的工作流", "🛠️ 可视化编辑器", "📖 节点文档"])

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
        
        # 高级选项
        with st.expander("高级选项"):
            st.multiselect(
                "必须包含的节点类型",
                options=[config['name'] for config in NODE_CONFIGS.values()],
                key="required_nodes"
            )
            
            st.number_input(
                "最大节点数量",
                min_value=3,
                max_value=20,
                value=10,
                key="max_nodes"
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
        
        **节点类型说明：**
        - 🚀 **开始/结束**：定义工作流边界
        - 🧠 **LLM**：调用大语言模型
        - 📚 **知识库**：检索相关信息
        - 🌐 **HTTP**：调用外部API
        - 💻 **代码**：自定义处理逻辑
        - 🔀 **条件**：分支判断
        - 🤖 **智能体**：自主执行任务
        """)

# 显示生成的工作流
if st.session_state.current_workflow:
    st.divider()
    st.subheader("📋 生成的工作流")
    
    # 使用交互式编辑器
    st.markdown("#### 交互式工作流视图（可拖拽节点）")
    components.html(
        create_interactive_editor(st.session_state.current_workflow),
        height=650
    )
    
    # 节点详情
    st.markdown("#### 节点配置详情")
    workflow = st.session_state.current_workflow
    
    cols = st.columns(2)
    for i, node in enumerate(workflow['nodes']):
        with cols[i % 2]:
            # 安全获取节点配置
            try:
                node_type_enum = NodeType(node['type'])
                node_config = NODE_CONFIGS.get(node_type_enum, {})
                icon = node_config.get('icon', '📦')
            except ValueError:
                icon = '📦'
                
            with st.expander(f"{icon} {node['name']}"):
                st.write(f"**类型：** {node['type']}")
                st.write(f"**描述：** {node['description']}")
                
                if 'config' in node:
                    st.write("**配置：**")
                    for key, value in node['config'].items():
                        st.write(f"- {key}: {value}")
                
                if 'connections' in node and node['connections']:
                    st.write("**连接到：**")
                    for conn in node['connections']:
                        target = next((n for n in workflow['nodes'] if n['id'] == conn['target_node_id']), None)
                        if target:
                            st.write(f"- {target['name']} ({conn.get('source_output', 'output')} → {conn.get('target_input', 'input')})")
    
    # 保存按钮
    if st.button("💾 保存工作流", type="primary"):
        workflow['created_at'] = datetime.now().isoformat()
        st.session_state.workflows.append(workflow)
        st.success("工作流已保存！")

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
                    <p>节点数：{len(workflow['nodes'])}</p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                with col1:
                    if st.button(f"查看", key=f"view_{idx}"):
                        st.session_state.current_workflow = workflow
                        st.rerun()
                with col2:
                    if st.button(f"编辑", key=f"edit_{idx}"):
                        st.session_state.editing_workflow = workflow
                        st.info("请前往可视化编辑器进行编辑")
                with col3:
                    if st.button(f"导出", key=f"export_{idx}"):
                        st.download_button(
                            label="下载JSON",
                            data=json.dumps(workflow, indent=2),
                            file_name=f"{workflow['name']}.json",
                            mime="application/json"
                        )
                with col4:
                    if st.button(f"删除", key=f"delete_{idx}"):
                        st.session_state.workflows.pop(idx)
                        st.rerun()
    else:
        st.info("暂无保存的工作流，请先创建一个新的工作流。")

# Tab3: 可视化编辑器
with tab3:
    st.subheader("🛠️ 可视化工作流编辑器")
    
    if 'editing_workflow' in st.session_state and st.session_state.editing_workflow:
        workflow = st.session_state.editing_workflow
        
        # 基本信息编辑
        col1, col2 = st.columns(2)
        with col1:
            workflow['name'] = st.text_input("工作流名称", value=workflow['name'])
        with col2:
            workflow['description'] = st.text_input("工作流描述", value=workflow['description'])
        
        st.divider()
        
        # 显示交互式编辑器
        st.markdown("### 可视化编辑器")
        components.html(
            create_interactive_editor(workflow),
            height=650
        )
        
        # 节点编辑面板
        st.markdown("### 节点编辑")
        
        # 选择要编辑的节点
        node_names = [f"{node['name']} ({node['id']})" for node in workflow['nodes']]
        selected_node_idx = st.selectbox("选择节点", range(len(node_names)), format_func=lambda x: node_names[x])
        
        if selected_node_idx is not None:
            node = workflow['nodes'][selected_node_idx]
            col1, col2 = st.columns(2)
            
            with col1:
                node['name'] = st.text_input("节点名称", value=node['name'], key=f"edit_name_{node['id']}")
                node['description'] = st.text_area("节点描述", value=node['description'], key=f"edit_desc_{node['id']}")
            
            with col2:
                # 根据节点类型显示相应的配置字段
                try:
                    node_type_enum = NodeType(node['type'])
                    node_config = NODE_CONFIGS.get(node_type_enum, {})
                except ValueError:
                    # 如果节点类型不在枚举中，使用默认配置
                    st.warning(f"未知的节点类型: {node['type']}")
                    node_config = {}
                
                if 'config_fields' in node_config:
                    st.write("**节点配置**")
                    for field_name, field_config in node_config['config_fields'].items():
                        if field_config['type'] == 'text':
                            value = st.text_input(
                                field_config['label'],
                                value=node.get('config', {}).get(field_name, ''),
                                key=f"config_{node['id']}_{field_name}"
                            )
                        elif field_config['type'] == 'textarea':
                            value = st.text_area(
                                field_config['label'],
                                value=node.get('config', {}).get(field_name, ''),
                                key=f"config_{node['id']}_{field_name}"
                            )
                        elif field_config['type'] == 'select':
                            current = node.get('config', {}).get(field_name, field_config['options'][0])
                            value = st.selectbox(
                                field_config['label'],
                                options=field_config['options'],
                                index=field_config['options'].index(current) if current in field_config['options'] else 0,
                                key=f"config_{node['id']}_{field_name}"
                            )
                        elif field_config['type'] == 'number':
                            value = st.number_input(
                                field_config['label'],
                                value=node.get('config', {}).get(field_name, field_config.get('default', 0)),
                                key=f"config_{node['id']}_{field_name}"
                            )
                        elif field_config['type'] == 'slider':
                            value = st.slider(
                                field_config['label'],
                                min_value=field_config['min'],
                                max_value=field_config['max'],
                                value=node.get('config', {}).get(field_name, field_config['default']),
                                key=f"config_{node['id']}_{field_name}"
                            )
                        
                        # 更新节点配置
                        if 'config' not in node:
                            node['config'] = {}
                        node['config'][field_name] = value
        
        # 添加新节点
        st.markdown("### 添加新节点")
        col1, col2, col3 = st.columns(3)
        with col1:
            new_node_type = st.selectbox(
                "节点类型",
                options=[node_type.value for node_type in NodeType],
                format_func=lambda x: NODE_CONFIGS.get(NodeType(x), {'name': x})['name']
            )
        with col2:
            new_node_name = st.text_input("节点名称", value="新节点")
        with col3:
            if st.button("➕ 添加节点"):
                try:
                    node_type_enum = NodeType(new_node_type)
                    node_config = NODE_CONFIGS.get(node_type_enum, {})
                    description = node_config.get('description', '新节点')
                except ValueError:
                    description = '新节点'
                    
                new_node = {
                    "id": str(uuid.uuid4())[:8],
                    "type": new_node_type,
                    "name": new_node_name,
                    "description": description,
                    "position": {"x": 100, "y": len(workflow['nodes']) * 100},
                    "config": {},
                    "connections": []
                }
                workflow['nodes'].append(new_node)
                st.success(f"已添加节点：{new_node_name}")
                st.rerun()
        
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

# Tab4: 节点文档
with tab4:
    st.subheader("📖 节点类型文档")
    
    st.markdown("""
    本平台提供了丰富的节点类型，参考了Dify等领先平台的设计，让您能够构建强大的AI工作流。
    """)
    
    # 显示所有节点类型的详细文档
    for node_type, config in NODE_CONFIGS.items():
        with st.expander(f"{config['icon']} {config['name']} ({node_type.value})"):
            st.markdown(f"**描述：** {config['description']}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**输入端口：**")
                for input_port in config['inputs']:
                    st.write(f"- {input_port}")
            
            with col2:
                st.markdown("**输出端口：**")
                for output_port in config['outputs']:
                    st.write(f"- {output_port}")
            
            if 'config_fields' in config:
                st.markdown("**配置参数：**")
                for field_name, field_config in config['config_fields'].items():
                    st.write(f"- **{field_config['label']}** ({field_config['type']})")
                    if 'options' in field_config:
                        st.write(f"  可选值：{', '.join(field_config['options'])}")
            
            # 示例用法
            st.markdown("**示例用法：**")
            if node_type.value == "llm":
                st.code("""
                # LLM节点配置示例
                {
                    "model": "gpt-3.5-turbo",
                    "prompt_template": "请根据以下内容回答用户问题：\\n{context}\\n\\n用户问题：{query}",
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
                """, language="json")
            elif node_type.value == "http_request":
                st.code("""
                # HTTP请求节点配置示例
                {
                    "method": "POST",
                    "url": "https://api.example.com/data",
                    "headers": {
                        "Authorization": "Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    "timeout": 30
                }
                """, language="json")
            elif node_type.value == "code":
                st.code("""
                # 代码执行节点示例
                def process_data(input_data):
                    # 处理输入数据
                    result = input_data.upper()
                    return {"output": result}
                """, language="python")

# 页脚
st.divider()
st.markdown("""
<div style="text-align: center; color: #6b7280; font-size: 0.875rem;">
    基于 Streamlit 和 OpenRouter 构建 | 增强版本 | 支持交互式编辑
</div>
""", unsafe_allow_html=True)
