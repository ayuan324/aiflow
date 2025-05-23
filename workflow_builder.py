import streamlit as st
import json
import requests
from datetime import datetime
import graphviz
from typing import Dict, List, Any, Optional, Callable
import os
import uuid
from dataclasses import dataclass, field
from enum import Enum
import streamlit.components.v1 as components
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
import re

# 页面配置
st.set_page_config(
    page_title="AI工作流构建平台",
    page_icon="🤖",
    layout="wide"
)

# 节点类型定义
class NodeType(Enum):
    START = "start"
    END = "end"
    LLM = "llm"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    HTTP_REQUEST = "http_request"
    CODE = "code"
    CONDITION = "condition"
    TEXT_PROCESSING = "text_processing"
    VARIABLE = "variable"
    WEB_SEARCH = "web_search"
    DATA_TRANSFORM = "data_transform"
    LOOP = "loop"

# 节点执行状态
class NodeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

# 节点配置
NODE_CONFIGS = {
    NodeType.START: {
        "name": "开始",
        "icon": "▶️",
        "color": "#e0f2fe",
        "description": "工作流起点，接收用户输入",
        "executor": "execute_start_node",
        "inputs": [],
        "outputs": ["output"],
        "config_fields": {
            "input_type": {
                "type": "select",
                "label": "输入类型",
                "options": ["text", "json", "file"],
                "default": "text"
            },
            "prompt": {
                "type": "textarea",
                "label": "提示信息",
                "default": "请输入您的内容："
            }
        }
    },
    NodeType.END: {
        "name": "结束",
        "icon": "🏁",
        "color": "#d1fae5",
        "description": "工作流终点，输出最终结果",
        "executor": "execute_end_node",
        "inputs": ["input"],
        "outputs": [],
        "config_fields": {
            "output_format": {
                "type": "select",
                "label": "输出格式",
                "options": ["text", "json", "markdown"],
                "default": "text"
            }
        }
    },
    NodeType.LLM: {
        "name": "大语言模型",
        "icon": "🧠",
        "color": "#fef3c7",
        "description": "调用AI模型处理文本",
        "executor": "execute_llm_node",
        "inputs": ["prompt", "context"],
        "outputs": ["text", "tokens_used"],
        "config_fields": {
            "model": {
                "type": "select",
                "label": "模型",
                "options": ["gpt-3.5-turbo", "gpt-4", "claude-3", "deepseek-chat"],
                "default": "gpt-3.5-turbo"
            },
            "system_prompt": {
                "type": "textarea",
                "label": "系统提示词",
                "default": "你是一个有帮助的AI助手。"
            },
            "user_prompt_template": {
                "type": "textarea",
                "label": "用户提示词模板",
                "default": "{input}",
                "help": "使用 {变量名} 引用输入"
            },
            "temperature": {
                "type": "slider",
                "label": "温度",
                "min": 0.0,
                "max": 2.0,
                "default": 0.7,
                "step": 0.1
            },
            "max_tokens": {
                "type": "number",
                "label": "最大令牌数",
                "default": 1000,
                "min": 100,
                "max": 4000
            }
        }
    },
    NodeType.WEB_SEARCH: {
        "name": "网络搜索",
        "icon": "🔍",
        "color": "#e0e7ff",
        "description": "搜索互联网获取实时信息",
        "executor": "execute_web_search_node",
        "inputs": ["query"],
        "outputs": ["results", "urls"],
        "config_fields": {
            "search_engine": {
                "type": "select",
                "label": "搜索引擎",
                "options": ["google", "bing", "duckduckgo"],
                "default": "google"
            },
            "num_results": {
                "type": "number",
                "label": "结果数量",
                "default": 5,
                "min": 1,
                "max": 20
            },
            "search_type": {
                "type": "select",
                "label": "搜索类型",
                "options": ["general", "news", "scholar"],
                "default": "general"
            }
        }
    },
    NodeType.HTTP_REQUEST: {
        "name": "HTTP请求",
        "icon": "🌐",
        "color": "#fce7f3",
        "description": "调用外部API获取数据",
        "executor": "execute_http_request_node",
        "inputs": ["url", "params"],
        "outputs": ["response", "status_code"],
        "config_fields": {
            "method": {
                "type": "select",
                "label": "请求方法",
                "options": ["GET", "POST", "PUT", "DELETE"],
                "default": "GET"
            },
            "url_template": {
                "type": "text",
                "label": "URL模板",
                "default": "https://api.example.com/endpoint",
                "help": "可以使用 {变量名} 插入输入值"
            },
            "headers": {
                "type": "json",
                "label": "请求头",
                "default": {"Content-Type": "application/json"}
            },
            "timeout": {
                "type": "number",
                "label": "超时时间（秒）",
                "default": 30,
                "min": 1,
                "max": 300
            }
        }
    },
    NodeType.CODE: {
        "name": "代码执行",
        "icon": "💻",
        "color": "#f0f9ff",
        "description": "执行自定义Python代码处理数据",
        "executor": "execute_code_node",
        "inputs": ["input"],
        "outputs": ["output"],
        "config_fields": {
            "code": {
                "type": "code",
                "label": "Python代码",
                "default": """# 输入变量: input
# 返回结果赋值给: output

output = input.upper() if isinstance(input, str) else str(input)""",
                "language": "python"
            },
            "timeout": {
                "type": "number",
                "label": "超时时间（秒）",
                "default": 10,
                "min": 1,
                "max": 60
            }
        }
    },
    NodeType.CONDITION: {
        "name": "条件判断",
        "icon": "🔀",
        "color": "#fdf4ff",
        "description": "根据条件选择不同分支",
        "executor": "execute_condition_node",
        "inputs": ["input"],
        "outputs": ["true_output", "false_output"],
        "config_fields": {
            "condition_type": {
                "type": "select",
                "label": "条件类型",
                "options": ["expression", "contains", "regex", "comparison"],
                "default": "expression"
            },
            "condition": {
                "type": "text",
                "label": "条件表达式",
                "default": "len(str(input)) > 10",
                "help": "Python表达式，使用 input 变量"
            },
            "true_value": {
                "type": "text",
                "label": "条件为真时的输出",
                "default": "{input}"
            },
            "false_value": {
                "type": "text",
                "label": "条件为假时的输出",
                "default": ""
            }
        }
    },
    NodeType.TEXT_PROCESSING: {
        "name": "文本处理",
        "icon": "📝",
        "color": "#eff6ff",
        "description": "对文本进行各种处理操作",
        "executor": "execute_text_processing_node",
        "inputs": ["text"],
        "outputs": ["processed_text"],
        "config_fields": {
            "operation": {
                "type": "select",
                "label": "操作类型",
                "options": ["extract", "replace", "split", "join", "format"],
                "default": "extract"
            },
            "pattern": {
                "type": "text",
                "label": "模式/分隔符",
                "default": "",
                "help": "正则表达式或分隔符"
            },
            "template": {
                "type": "textarea",
                "label": "格式模板",
                "default": "{text}",
                "help": "用于format操作"
            }
        }
    },
    NodeType.DATA_TRANSFORM: {
        "name": "数据转换",
        "icon": "🔄",
        "color": "#f3e8ff",
        "description": "转换数据格式或结构",
        "executor": "execute_data_transform_node",
        "inputs": ["data"],
        "outputs": ["transformed_data"],
        "config_fields": {
            "transform_type": {
                "type": "select",
                "label": "转换类型",
                "options": ["json_to_text", "text_to_json", "extract_json", "merge"],
                "default": "json_to_text"
            },
            "json_path": {
                "type": "text",
                "label": "JSON路径",
                "default": "",
                "help": "例如: data.items[0].name"
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
    .workflow-canvas {
        min-height: 600px;
        background-color: #f9fafb;
        border: 2px solid #e5e7eb;
        border-radius: 12px;
        position: relative;
        overflow: hidden;
    }
    .node-config-panel {
        position: fixed;
        right: 0;
        top: 0;
        width: 400px;
        height: 100vh;
        background: white;
        box-shadow: -2px 0 10px rgba(0,0,0,0.1);
        padding: 20px;
        overflow-y: auto;
        z-index: 1000;
    }
    .execution-log {
        background-color: #1e1e1e;
        color: #d4d4d4;
        padding: 15px;
        border-radius: 8px;
        font-family: 'Monaco', 'Consolas', monospace;
        font-size: 12px;
        max-height: 400px;
        overflow-y: auto;
    }
    .node-status {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
    }
    .status-pending { background-color: #e5e7eb; color: #374151; }
    .status-running { background-color: #3b82f6; color: white; }
    .status-success { background-color: #10b981; color: white; }
    .status-failed { background-color: #ef4444; color: white; }
    .status-skipped { background-color: #6b7280; color: white; }
</style>
""", unsafe_allow_html=True)

# 初始化session state
if 'workflows' not in st.session_state:
    st.session_state.workflows = []
if 'current_workflow' not in st.session_state:
    st.session_state.current_workflow = None
if 'api_key' not in st.session_state:
    try:
        st.session_state.api_key = st.secrets["OPENROUTER_API_KEY"]
    except:
        st.session_state.api_key = ""
if 'selected_node' not in st.session_state:
    st.session_state.selected_node = None
if 'execution_state' not in st.session_state:
    st.session_state.execution_state = {}
if 'execution_log' not in st.session_state:
    st.session_state.execution_log = []
if 'node_outputs' not in st.session_state:
    st.session_state.node_outputs = {}

# 节点执行器函数
class WorkflowExecutor:
    def __init__(self, workflow: Dict[str, Any], api_key: str):
        self.workflow = workflow
        self.api_key = api_key
        self.node_outputs = {}
        self.execution_log = []
        
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.execution_log.append(log_entry)
        st.session_state.execution_log.append(log_entry)
    
    async def execute_start_node(self, node: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.log(f"开始节点 '{node['name']}' 执行")
        config = node.get('config', {})
        
        # 获取用户输入
        if 'user_input' in inputs:
            output = inputs['user_input']
        else:
            output = st.session_state.get('workflow_input', '')
        
        self.log(f"输入内容: {output[:100]}...")
        return {"output": output}
    
    async def execute_end_node(self, node: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.log(f"结束节点 '{node['name']}' 执行")
        input_value = inputs.get('input', '')
        config = node.get('config', {})
        
        # 格式化输出
        output_format = config.get('output_format', 'text')
        if output_format == 'json' and isinstance(input_value, str):
            try:
                input_value = json.loads(input_value)
            except:
                pass
        
        self.log(f"最终输出: {str(input_value)[:100]}...")
        return {"output": input_value}
    
    async def execute_llm_node(self, node: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.log(f"LLM节点 '{node['name']}' 开始执行")
        config = node.get('config', {})
        
        # 构建提示词
        system_prompt = config.get('system_prompt', '你是一个有帮助的AI助手。')
        user_prompt_template = config.get('user_prompt_template', '{input}')
        
        # 替换模板中的变量
        user_prompt = user_prompt_template
        for key, value in inputs.items():
            user_prompt = user_prompt.replace(f"{{{key}}}", str(value))
        
        # 调用API
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            model = config.get('model', 'gpt-3.5-turbo')
            # 映射模型名称到OpenRouter格式
            model_mapping = {
                'gpt-3.5-turbo': 'openai/gpt-3.5-turbo',
                'gpt-4': 'openai/gpt-4',
                'claude-3': 'anthropic/claude-3-sonnet',
                'deepseek-chat': 'deepseek/deepseek-chat'
            }
            model = model_mapping.get(model, model)
            
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": config.get('temperature', 0.7),
                "max_tokens": config.get('max_tokens', 1000)
            }
            
            self.log(f"调用模型: {model}")
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result['choices'][0]['message']['content']
                tokens = result.get('usage', {}).get('total_tokens', 0)
                self.log(f"LLM响应成功，使用tokens: {tokens}")
                return {"text": text, "tokens_used": tokens}
            else:
                raise Exception(f"API调用失败: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log(f"LLM节点执行失败: {str(e)}", "ERROR")
            raise e
    
    async def execute_web_search_node(self, node: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.log(f"网络搜索节点 '{node['name']}' 开始执行")
        config = node.get('config', {})
        query = inputs.get('query', '')
        
        # 模拟搜索结果（实际应用中应调用真实的搜索API）
        num_results = config.get('num_results', 5)
        search_type = config.get('search_type', 'general')
        
        self.log(f"搜索查询: {query}")
        self.log(f"搜索类型: {search_type}, 结果数: {num_results}")
        
        # 使用DuckDuckGo API进行实际搜索（免费且无需API密钥）
        try:
            search_url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
            response = requests.get(search_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = []
                urls = []
                
                # 处理即时回答
                if data.get('Abstract'):
                    results.append({
                        'title': 'Summary',
                        'snippet': data['Abstract'],
                        'url': data.get('AbstractURL', '')
                    })
                    urls.append(data.get('AbstractURL', ''))
                
                # 处理相关主题
                for topic in data.get('RelatedTopics', [])[:num_results]:
                    if isinstance(topic, dict) and 'Text' in topic:
                        results.append({
                            'title': topic.get('Text', '').split(' - ')[0][:50],
                            'snippet': topic.get('Text', ''),
                            'url': topic.get('FirstURL', '')
                        })
                        urls.append(topic.get('FirstURL', ''))
                
                # 如果没有结果，创建模拟数据
                if not results:
                    results = [
                        {
                            'title': f'Search result {i+1} for "{query}"',
                            'snippet': f'This is a simulated search result for the query "{query}". In production, this would contain real search results.',
                            'url': f'https://example.com/result{i+1}'
                        }
                        for i in range(min(3, num_results))
                    ]
                    urls = [r['url'] for r in results]
                
                self.log(f"搜索完成，找到 {len(results)} 个结果")
                return {"results": results, "urls": urls}
            else:
                raise Exception(f"搜索API调用失败: {response.status_code}")
                
        except Exception as e:
            self.log(f"搜索失败，返回模拟结果: {str(e)}", "WARNING")
            # 返回模拟结果
            results = [
                {
                    'title': f'Search result {i+1} for "{query}"',
                    'snippet': f'This is a simulated search result. Error: {str(e)}',
                    'url': f'https://example.com/result{i+1}'
                }
                for i in range(min(3, num_results))
            ]
            return {"results": results, "urls": [r['url'] for r in results]}
    
    async def execute_http_request_node(self, node: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.log(f"HTTP请求节点 '{node['name']}' 开始执行")
        config = node.get('config', {})
        
        # 构建URL
        url_template = config.get('url_template', '')
        url = url_template
        for key, value in inputs.items():
            url = url.replace(f"{{{key}}}", str(value))
        
        method = config.get('method', 'GET')
        headers = config.get('headers', {})
        timeout = config.get('timeout', 30)
        
        self.log(f"发送 {method} 请求到: {url}")
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                timeout=timeout,
                params=inputs.get('params', {})
            )
            
            self.log(f"响应状态码: {response.status_code}")
            
            # 尝试解析JSON
            try:
                response_data = response.json()
            except:
                response_data = response.text
            
            return {
                "response": response_data,
                "status_code": response.status_code
            }
        except Exception as e:
            self.log(f"HTTP请求失败: {str(e)}", "ERROR")
            raise e
    
    async def execute_code_node(self, node: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.log(f"代码执行节点 '{node['name']}' 开始执行")
        config = node.get('config', {})
        code = config.get('code', '')
        
        # 创建执行环境
        local_vars = {'input': inputs.get('input', '')}
        global_vars = {
            'json': json,
            're': re,
            'datetime': datetime,
            'str': str,
            'int': int,
            'float': float,
            'len': len,
            'list': list,
            'dict': dict
        }
        
        try:
            # 执行代码
            exec(code, global_vars, local_vars)
            output = local_vars.get('output', '')
            self.log(f"代码执行成功")
            return {"output": output}
        except Exception as e:
            self.log(f"代码执行失败: {str(e)}", "ERROR")
            raise e
    
    async def execute_condition_node(self, node: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.log(f"条件判断节点 '{node['name']}' 开始执行")
        config = node.get('config', {})
        
        input_value = inputs.get('input', '')
        condition = config.get('condition', 'True')
        
        # 创建执行环境
        local_vars = {'input': input_value}
        
        try:
            # 评估条件
            result = eval(condition, {"__builtins__": {}}, local_vars)
            self.log(f"条件 '{condition}' 评估结果: {result}")
            
            if result:
                output = config.get('true_value', '{input}').replace('{input}', str(input_value))
                return {"true_output": output, "false_output": None}
            else:
                output = config.get('false_value', '').replace('{input}', str(input_value))
                return {"true_output": None, "false_output": output}
        except Exception as e:
            self.log(f"条件评估失败: {str(e)}", "ERROR")
            raise e
    
    async def execute_text_processing_node(self, node: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.log(f"文本处理节点 '{node['name']}' 开始执行")
        config = node.get('config', {})
        
        text = str(inputs.get('text', ''))
        operation = config.get('operation', 'extract')
        pattern = config.get('pattern', '')
        
        try:
            if operation == 'extract':
                matches = re.findall(pattern, text) if pattern else [text]
                result = '\n'.join(matches)
            elif operation == 'replace':
                parts = pattern.split('|')
                if len(parts) == 2:
                    result = text.replace(parts[0], parts[1])
                else:
                    result = text
            elif operation == 'split':
                result = text.split(pattern or ' ')
            elif operation == 'join':
                if isinstance(text, list):
                    result = (pattern or ' ').join(text)
                else:
                    result = text
            elif operation == 'format':
                template = config.get('template', '{text}')
                result = template.replace('{text}', text)
            else:
                result = text
            
            self.log(f"文本处理完成: {operation}")
            return {"processed_text": result}
        except Exception as e:
            self.log(f"文本处理失败: {str(e)}", "ERROR")
            raise e
    
    async def execute_data_transform_node(self, node: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        self.log(f"数据转换节点 '{node['name']}' 开始执行")
        config = node.get('config', {})
        
        data = inputs.get('data', '')
        transform_type = config.get('transform_type', 'json_to_text')
        
        try:
            if transform_type == 'json_to_text':
                if isinstance(data, dict) or isinstance(data, list):
                    result = json.dumps(data, ensure_ascii=False, indent=2)
                else:
                    result = str(data)
            elif transform_type == 'text_to_json':
                if isinstance(data, str):
                    result = json.loads(data)
                else:
                    result = data
            elif transform_type == 'extract_json':
                # 从文本中提取JSON
                if isinstance(data, str):
                    json_match = re.search(r'\{.*\}|\[.*\]', data, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())
                    else:
                        result = {}
                else:
                    result = data
            else:
                result = data
            
            self.log(f"数据转换完成: {transform_type}")
            return {"transformed_data": result}
        except Exception as e:
            self.log(f"数据转换失败: {str(e)}", "ERROR")
            raise e
    
    async def execute_node(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个节点"""
        node_type = NodeType(node['type'])
        node_config = NODE_CONFIGS.get(node_type, {})
        
        # 收集输入
        inputs = {}
        for input_name in node_config.get('inputs', []):
            # 查找连接到此输入的节点输出
            for other_node in self.workflow['nodes']:
                for conn in other_node.get('connections', []):
                    if conn['target_node_id'] == node['id'] and conn.get('target_input') == input_name:
                        source_output = conn.get('source_output', 'output')
                        if other_node['id'] in self.node_outputs:
                            inputs[input_name] = self.node_outputs[other_node['id']].get(source_output)
                            break
        
        # 执行节点
        executor_name = node_config.get('executor', '')
        if hasattr(self, executor_name):
            executor = getattr(self, executor_name)
            outputs = await executor(node, inputs)
            self.node_outputs[node['id']] = outputs
            return outputs
        else:
            self.log(f"未找到节点类型 {node_type.value} 的执行器", "ERROR")
            raise Exception(f"未实现的节点类型: {node_type.value}")
    
    async def execute(self, user_input: str = "") -> Any:
        """执行整个工作流"""
        self.log("开始执行工作流", "INFO")
        st.session_state.node_outputs = {}
        
        # 设置初始输入
        if user_input:
            st.session_state.workflow_input = user_input
            
        # 初始化所有节点状态
        for node in self.workflow['nodes']:
            st.session_state.execution_state[node['id']] = NodeStatus.PENDING
        
        # 找到开始节点
        start_nodes = [n for n in self.workflow['nodes'] if n['type'] == 'start']
        if not start_nodes:
            self.log("未找到开始节点", "ERROR")
            raise Exception("工作流必须包含开始节点")
        
        # 使用拓扑排序确定执行顺序
        executed = set()
        to_execute = [start_nodes[0]['id']]
        
        while to_execute:
            node_id = to_execute.pop(0)
            if node_id in executed:
                continue
                
            node = next((n for n in self.workflow['nodes'] if n['id'] == node_id), None)
            if not node:
                continue
            
            # 检查所有依赖是否已执行
            dependencies_met = True
            for other_node in self.workflow['nodes']:
                for conn in other_node.get('connections', []):
                    if conn['target_node_id'] == node_id and other_node['id'] not in executed:
                        dependencies_met = False
                        break
                if not dependencies_met:
                    break
            
            if not dependencies_met:
                to_execute.append(node_id)
                continue
            
            # 执行节点
            try:
                st.session_state.execution_state[node_id] = NodeStatus.RUNNING
                outputs = await self.execute_node(node)
                st.session_state.execution_state[node_id] = NodeStatus.SUCCESS
                executed.add(node_id)
                
                # 添加下游节点到执行队列
                for conn in node.get('connections', []):
                    if conn['target_node_id'] not in executed:
                        to_execute.append(conn['target_node_id'])
                        
            except Exception as e:
                st.session_state.execution_state[node_id] = NodeStatus.FAILED
                self.log(f"节点 '{node['name']}' 执行失败: {str(e)}", "ERROR")
                raise e
        
        # 获取结束节点的输出
        end_nodes = [n for n in self.workflow['nodes'] if n['type'] == 'end']
        if end_nodes and end_nodes[0]['id'] in self.node_outputs:
            final_output = self.node_outputs[end_nodes[0]['id']].get('output')
            self.log(f"工作流执行完成", "INFO")
            return final_output
        else:
            self.log("未找到有效的输出", "WARNING")
            return None

# 增强的API调用函数
def call_openrouter_api(prompt: str, api_key: str) -> Dict[str, Any]:
    """调用 OpenRouter API 生成工作流结构"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 定义可用的节点类型及其使用场景
    node_types_description = """
可用的节点类型及其用途：
- start: 工作流起点，接收用户输入
- end: 工作流终点，输出最终结果
- llm: 调用大语言模型进行文本生成、分析、总结等
- web_search: 搜索互联网获取最新信息（用于需要实时数据的场景）
- http_request: 调用外部API获取数据（用于集成第三方服务）
- code: 执行Python代码进行数据处理、计算等
- condition: 条件判断，根据条件选择不同的执行路径
- text_processing: 文本处理，如提取、替换、分割等
- data_transform: 数据格式转换，如JSON和文本之间的转换

重要提示：
1. 如果用户需要搜索网络信息、获取最新数据，必须使用 web_search 节点
2. 如果需要调用外部服务或API，使用 http_request 节点
3. 需要复杂数据处理时，使用 code 节点
4. 每个节点的连接必须指定源输出端口和目标输入端口
"""
    
    system_prompt = f"""你是一个AI工作流设计专家。请根据用户的需求描述，生成一个结构化的工作流。

{node_types_description}

请返回JSON格式的工作流，严格遵循以下结构：
{{
    "name": "工作流名称",
    "description": "工作流描述",
    "nodes": [
        {{
            "id": "node_1",
            "type": "节点类型",
            "name": "节点名称",
            "description": "节点功能描述",
            "position": {{"x": 100, "y": 100}},
            "config": {{
                // 根据节点类型填充相应的配置
            }},
            "connections": [
                {{
                    "target_node_id": "目标节点ID",
                    "source_output": "源输出端口名",
                    "target_input": "目标输入端口名"
                }}
            ]
        }}
    ]
}}

节点位置规则：
- x坐标: 每个处理步骤增加200
- y坐标: 并行分支使用不同的y值

连接规则示例：
- LLM节点输出text连接到下一个节点的input: {{"source_output": "text", "target_input": "input"}}
- 搜索节点输出results连接到LLM的context: {{"source_output": "results", "target_input": "context"}}
"""
    
    # 添加更多上下文示例
    examples = """
示例1 - 网络搜索工作流：
用户需求："搜索最新的AI技术趋势"
应该包含：start → web_search → llm → end

示例2 - API集成工作流：
用户需求："获取天气信息并生成报告"
应该包含：start → http_request → data_transform → llm → end

示例3 - 条件处理工作流：
用户需求："根据输入长度选择不同的处理方式"
应该包含：start → condition → (分支1: text_processing) 或 (分支2: llm) → end
"""
    
    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": system_prompt + "\n\n" + examples},
            {"role": "user", "content": f"请为以下需求生成工作流结构：{prompt}\n\n请确保充分利用各种节点类型，特别是当用户需要搜索信息时使用web_search节点。"}
        ],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            # 提取JSON部分
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end != 0:
                workflow_json = json.loads(content[start:end])
                # 为每个节点生成唯一ID（如果没有）
                for i, node in enumerate(workflow_json['nodes']):
                    if 'id' not in node or not node['id']:
                        node['id'] = f"node_{i+1}"
                    if 'position' not in node:
                        node['position'] = {"x": 100 + i * 200, "y": 100}
                return {"success": True, "workflow": workflow_json}
            else:
                return {"success": False, "error": "无法解析工作流结构"}
        else:
            return {"success": False, "error": f"API调用失败: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# 创建交互式工作流编辑器
def create_workflow_editor_html(workflow: Dict[str, Any]) -> str:
    """创建增强的交互式工作流编辑器"""
    nodes_js = json.dumps(workflow['nodes'])
    node_configs_js = json.dumps({k.value: v for k, v in NODE_CONFIGS.items()})
    
    html = f"""
    <div style="display: flex; height: 700px;">
        <div id="workflow-editor" style="flex: 1; position: relative; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px;">
            <div style="position: absolute; top: 10px; left: 10px; z-index: 100;">
                <button onclick="addConnection()" style="padding: 8px 16px; background: #3b82f6; color: white; border: none; border-radius: 6px; cursor: pointer; margin-right: 10px;">
                    🔗 添加连接
                </button>
                <button onclick="deleteSelected()" style="padding: 8px 16px; background: #ef4444; color: white; border: none; border-radius: 6px; cursor: pointer;">
                    🗑️ 删除选中
                </button>
            </div>
            <svg id="workflow-svg" width="100%" height="100%" style="cursor: grab;">
                <defs>
                    <marker id="arrowhead" markerWidth="10" markerHeight="7" 
                            refX="10" refY="3.5" orient="auto">
                        <polygon points="0 0, 10 3.5, 0 7" fill="#6b7280" />
                    </marker>
                </defs>
            </svg>
        </div>
        <div id="config-panel" style="width: 0; background: white; box-shadow: -2px 0 10px rgba(0,0,0,0.1); transition: width 0.3s; overflow: hidden;">
            <div style="padding: 20px;">
                <h3 id="config-title">节点配置</h3>
                <div id="config-content"></div>
                <button onclick="closeConfigPanel()" style="margin-top: 20px; padding: 8px 16px; background: #6b7280; color: white; border: none; border-radius: 6px; cursor: pointer;">
                    关闭
                </button>
            </div>
        </div>
    </div>
    
    <script>
        let nodes = {nodes_js};
        const nodeConfigs = {node_configs_js};
        const svg = document.getElementById('workflow-svg');
        const svgNS = "http://www.w3.org/2000/svg";
        let selectedNode = null;
        let selectedConnection = null;
        let isConnecting = false;
        let connectionStart = null;
        let tempLine = null;
        
        // 节点端口定义
        const getNodePorts = (nodeType) => {{
            const config = nodeConfigs[nodeType];
            return {{
                inputs: config ? config.inputs : [],
                outputs: config ? config.outputs : []
            }};
        }};
        
        // 渲染节点
        function renderNodes() {{
            // 清除现有节点
            document.querySelectorAll('.node-group').forEach(g => g.remove());
            
            nodes.forEach(node => {{
                const g = document.createElementNS(svgNS, 'g');
                g.setAttribute('transform', `translate(${{node.position.x}}, ${{node.position.y}})`);
                g.setAttribute('class', 'node-group');
                g.setAttribute('data-node-id', node.id);
                g.style.cursor = 'grab';
                
                const config = nodeConfigs[node.type] || {{}};
                const ports = getNodePorts(node.type);
                
                // 节点背景
                const rect = document.createElementNS(svgNS, 'rect');
                rect.setAttribute('width', '200');
                rect.setAttribute('height', '100');
                rect.setAttribute('rx', '8');
                rect.setAttribute('fill', config.color || '#f0f0f0');
                rect.setAttribute('stroke', selectedNode === node.id ? '#3b82f6' : '#d1d5db');
                rect.setAttribute('stroke-width', selectedNode === node.id ? '3' : '2');
                
                // 节点标题背景
                const titleBg = document.createElementNS(svgNS, 'rect');
                titleBg.setAttribute('width', '200');
                titleBg.setAttribute('height', '30');
                titleBg.setAttribute('rx', '8');
                titleBg.setAttribute('fill', 'rgba(0,0,0,0.1)');
                
                // 节点图标和名称
                const text = document.createElementNS(svgNS, 'text');
                text.setAttribute('x', '100');
                text.setAttribute('y', '20');
                text.setAttribute('text-anchor', 'middle');
                text.setAttribute('font-size', '14');
                text.setAttribute('font-weight', 'bold');
                text.textContent = (config.icon || '📦') + ' ' + node.name;
                
                // 节点类型
                const typeText = document.createElementNS(svgNS, 'text');
                typeText.setAttribute('x', '100');
                typeText.setAttribute('y', '50');
                typeText.setAttribute('text-anchor', 'middle');
                typeText.setAttribute('font-size', '12');
                typeText.setAttribute('fill', '#6b7280');
                typeText.textContent = node.type;
                
                // 状态指示器
                const status = window.parent.streamlitExecutionState?.[node.id] || 'pending';
                const statusCircle = document.createElementNS(svgNS, 'circle');
                statusCircle.setAttribute('cx', '185');
                statusCircle.setAttribute('cy', '85');
                statusCircle.setAttribute('r', '5');
                const statusColors = {{
                    'pending': '#e5e7eb',
                    'running': '#3b82f6',
                    'success': '#10b981',
                    'failed': '#ef4444',
                    'skipped': '#6b7280'
                }};
                statusCircle.setAttribute('fill', statusColors[status]);
                
                // 输入端口
                ports.inputs.forEach((input, i) => {{
                    const y = 30 + (i + 1) * (70 / (ports.inputs.length + 1));
                    const port = document.createElementNS(svgNS, 'circle');
                    port.setAttribute('cx', '0');
                    port.setAttribute('cy', y);
                    port.setAttribute('r', '6');
                    port.setAttribute('fill', '#3b82f6');
                    port.setAttribute('stroke', 'white');
                    port.setAttribute('stroke-width', '2');
                    port.setAttribute('class', 'input-port');
                    port.setAttribute('data-port-name', input);
                    port.style.cursor = 'crosshair';
                    g.appendChild(port);
                    
                    // 端口标签
                    const label = document.createElementNS(svgNS, 'text');
                    label.setAttribute('x', '10');
                    label.setAttribute('y', y + 3);
                    label.setAttribute('font-size', '10');
                    label.setAttribute('fill', '#6b7280');
                    label.textContent = input;
                    g.appendChild(label);
                }});
                
                // 输出端口
                ports.outputs.forEach((output, i) => {{
                    const y = 30 + (i + 1) * (70 / (ports.outputs.length + 1));
                    const port = document.createElementNS(svgNS, 'circle');
                    port.setAttribute('cx', '200');
                    port.setAttribute('cy', y);
                    port.setAttribute('r', '6');
                    port.setAttribute('fill', '#10b981');
                    port.setAttribute('stroke', 'white');
                    port.setAttribute('stroke-width', '2');
                    port.setAttribute('class', 'output-port');
                    port.setAttribute('data-port-name', output);
                    port.style.cursor = 'crosshair';
                    g.appendChild(port);
                    
                    // 端口标签
                    const label = document.createElementNS(svgNS, 'text');
                    label.setAttribute('x', '190');
                    label.setAttribute('y', y + 3);
                    label.setAttribute('text-anchor', 'end');
                    label.setAttribute('font-size', '10');
                    label.setAttribute('fill', '#6b7280');
                    label.textContent = output;
                    g.appendChild(label);
                }});
                
                g.appendChild(rect);
                g.appendChild(titleBg);
                g.appendChild(text);
                g.appendChild(typeText);
                g.appendChild(statusCircle);
                
                // 事件处理
                let isDragging = false;
                let startX, startY;
                
                g.addEventListener('mousedown', (e) => {{
                    if (e.target.classList.contains('output-port')) {{
                        // 开始连接
                        isConnecting = true;
                        connectionStart = {{
                            nodeId: node.id,
                            port: e.target.getAttribute('data-port-name'),
                            x: node.position.x + 200,
                            y: node.position.y + parseFloat(e.target.getAttribute('cy'))
                        }};
                        e.stopPropagation();
                    }} else if (e.target.classList.contains('input-port')) {{
                        // 结束连接
                        if (isConnecting && connectionStart) {{
                            const targetNode = node.id;
                            const targetPort = e.target.getAttribute('data-port-name');
                            
                            // 添加连接
                            const sourceNode = nodes.find(n => n.id === connectionStart.nodeId);
                            if (sourceNode && sourceNode.id !== targetNode) {{
                                if (!sourceNode.connections) sourceNode.connections = [];
                                sourceNode.connections.push({{
                                    target_node_id: targetNode,
                                    source_output: connectionStart.port,
                                    target_input: targetPort
                                }});
                                renderConnections();
                                updateNodesInStreamlit();
                            }}
                            
                            isConnecting = false;
                            connectionStart = null;
                            if (tempLine) {{
                                tempLine.remove();
                                tempLine = null;
                            }}
                        }}
                        e.stopPropagation();
                    }} else {{
                        // 选中节点或开始拖拽
                        selectedNode = node.id;
                        renderNodes();
                        openConfigPanel(node);
                        
                        isDragging = true;
                        startX = e.clientX - node.position.x;
                        startY = e.clientY - node.position.y;
                        g.style.cursor = 'grabbing';
                    }}
                }});
                
                svg.addEventListener('mousemove', (e) => {{
                    if (isDragging && node.id === selectedNode) {{
                        node.position.x = e.clientX - svg.getBoundingClientRect().left - startX;
                        node.position.y = e.clientY - svg.getBoundingClientRect().top - startY;
                        g.setAttribute('transform', `translate(${{node.position.x}}, ${{node.position.y}})`);
                        renderConnections();
                    }} else if (isConnecting && connectionStart) {{
                        // 更新临时连接线
                        const endX = e.clientX - svg.getBoundingClientRect().left;
                        const endY = e.clientY - svg.getBoundingClientRect().top;
                        
                        if (tempLine) {{
                            tempLine.remove();
                        }}
                        
                        tempLine = document.createElementNS(svgNS, 'line');
                        tempLine.setAttribute('x1', connectionStart.x);
                        tempLine.setAttribute('y1', connectionStart.y);
                        tempLine.setAttribute('x2', endX);
                        tempLine.setAttribute('y2', endY);
                        tempLine.setAttribute('stroke', '#3b82f6');
                        tempLine.setAttribute('stroke-width', '2');
                        tempLine.setAttribute('stroke-dasharray', '5,5');
                        svg.appendChild(tempLine);
                    }}
                }});
                
                svg.addEventListener('mouseup', () => {{
                    if (isDragging && node.id === selectedNode) {{
                        isDragging = false;
                        g.style.cursor = 'grab';
                        updateNodesInStreamlit();
                    }}
                }});
                
                svg.appendChild(g);
            }});
        }}
        
        // 渲染连接线
        function renderConnections() {{
            document.querySelectorAll('.connection-line').forEach(line => line.remove());
            
            nodes.forEach(node => {{
                if (node.connections) {{
                    node.connections.forEach((conn, connIndex) => {{
                        const targetNode = nodes.find(n => n.id === conn.target_node_id);
                        if (targetNode) {{
                            const sourcePorts = getNodePorts(node.type);
                            const targetPorts = getNodePorts(targetNode.type);
                            
                            const sourcePortIndex = sourcePorts.outputs.indexOf(conn.source_output);
                            const targetPortIndex = targetPorts.inputs.indexOf(conn.target_input);
                            
                            if (sourcePortIndex >= 0 && targetPortIndex >= 0) {{
                                const startX = node.position.x + 200;
                                const startY = node.position.y + 30 + (sourcePortIndex + 1) * (70 / (sourcePorts.outputs.length + 1));
                                const endX = targetNode.position.x;
                                const endY = targetNode.position.y + 30 + (targetPortIndex + 1) * (70 / (targetPorts.inputs.length + 1));
                                
                                const path = document.createElementNS(svgNS, 'path');
                                const midX = (startX + endX) / 2;
                                const d = `M ${{startX}} ${{startY}} C ${{midX}} ${{startY}}, ${{midX}} ${{endY}}, ${{endX}} ${{endY}}`;
                                
                                path.setAttribute('d', d);
                                path.setAttribute('fill', 'none');
                                path.setAttribute('stroke', selectedConnection === `${{node.id}}-${{connIndex}}` ? '#3b82f6' : '#6b7280');
                                path.setAttribute('stroke-width', selectedConnection === `${{node.id}}-${{connIndex}}` ? '3' : '2');
                                path.setAttribute('marker-end', 'url(#arrowhead)');
                                path.setAttribute('class', 'connection-line');
                                path.setAttribute('data-connection', `${{node.id}}-${{connIndex}}`);
                                path.style.cursor = 'pointer';
                                
                                path.addEventListener('click', (e) => {{
                                    selectedConnection = `${{node.id}}-${{connIndex}}`;
                                    renderConnections();
                                    e.stopPropagation();
                                }});
                                
                                svg.insertBefore(path, svg.firstChild);
                            }}
                        }}
                    }});
                }}
            }});
        }}
        
        // 打开配置面板
        function openConfigPanel(node) {{
            const panel = document.getElementById('config-panel');
            const title = document.getElementById('config-title');
            const content = document.getElementById('config-content');
            
            panel.style.width = '400px';
            title.textContent = node.name + ' - 配置';
            
            const config = nodeConfigs[node.type] || {{}};
            let html = '<div style="margin-bottom: 20px;">';
            html += `<p><strong>类型:</strong> ${{node.type}}</p>`;
            html += `<p><strong>描述:</strong> ${{node.description}}</p>`;
            html += '</div>';
            
            if (config.config_fields) {{
                html += '<div>';
                for (const [fieldName, fieldConfig] of Object.entries(config.config_fields)) {{
                    const currentValue = node.config?.[fieldName] || fieldConfig.default || '';
                    html += `<div style="margin-bottom: 15px;">`;
                    html += `<label style="display: block; margin-bottom: 5px; font-weight: bold;">${{fieldConfig.label}}:</label>`;
                    
                    if (fieldConfig.type === 'text') {{
                        html += `<input type="text" value="${{currentValue}}" 
                                 onchange="updateNodeConfig('${{node.id}}', '${{fieldName}}', this.value)"
                                 style="width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 4px;">`;
                    }} else if (fieldConfig.type === 'textarea') {{
                        html += `<textarea rows="4" 
                                 onchange="updateNodeConfig('${{node.id}}', '${{fieldName}}', this.value)"
                                 style="width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 4px;">${{currentValue}}</textarea>`;
                    }} else if (fieldConfig.type === 'select') {{
                        html += `<select onchange="updateNodeConfig('${{node.id}}', '${{fieldName}}', this.value)"
                                 style="width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 4px;">`;
                        fieldConfig.options.forEach(option => {{
                            html += `<option value="${{option}}" ${{currentValue === option ? 'selected' : ''}}>${{option}}</option>`;
                        }});
                        html += '</select>';
                    }} else if (fieldConfig.type === 'number') {{
                        html += `<input type="number" value="${{currentValue}}" 
                                 min="${{fieldConfig.min || 0}}" max="${{fieldConfig.max || 9999}}"
                                 onchange="updateNodeConfig('${{node.id}}', '${{fieldName}}', parseFloat(this.value))"
                                 style="width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 4px;">`;
                    }}
                    
                    if (fieldConfig.help) {{
                        html += `<small style="color: #6b7280;">${{fieldConfig.help}}</small>`;
                    }}
                    html += '</div>';
                }}
                html += '</div>';
            }}
            
            content.innerHTML = html;
        }}
        
        // 关闭配置面板
        function closeConfigPanel() {{
            document.getElementById('config-panel').style.width = '0';
        }}
        
        // 更新节点配置
        function updateNodeConfig(nodeId, fieldName, value) {{
            const node = nodes.find(n => n.id === nodeId);
            if (node) {{
                if (!node.config) node.config = {{}};
                node.config[fieldName] = value;
                updateNodesInStreamlit();
            }}
        }}
        
        // 删除选中的节点或连接
        function deleteSelected() {{
            if (selectedNode) {{
                // 删除节点
                nodes = nodes.filter(n => n.id !== selectedNode);
                // 删除相关连接
                nodes.forEach(node => {{
                    if (node.connections) {{
                        node.connections = node.connections.filter(conn => conn.target_node_id !== selectedNode);
                    }}
                }});
                selectedNode = null;
                renderNodes();
                renderConnections();
                updateNodesInStreamlit();
                closeConfigPanel();
            }} else if (selectedConnection) {{
                // 删除连接
                const [nodeId, connIndex] = selectedConnection.split('-');
                const node = nodes.find(n => n.id === nodeId);
                if (node && node.connections) {{
                    node.connections.splice(parseInt(connIndex), 1);
                    selectedConnection = null;
                    renderConnections();
                    updateNodesInStreamlit();
                }}
            }}
        }}
        
        // 更新Streamlit中的节点数据
        function updateNodesInStreamlit() {{
            const event = new CustomEvent('workflowUpdate', {{ detail: {{ nodes: nodes }} }});
            window.dispatchEvent(event);
        }}
        
        // 监听执行状态更新
        window.addEventListener('executionStateUpdate', (e) => {{
            window.streamlitExecutionState = e.detail;
            renderNodes();
        }});
        
        // 初始渲染
        renderNodes();
        renderConnections();
        
        // 背景点击取消选择
        svg.addEventListener('click', (e) => {{
            if (e.target === svg) {{
                selectedNode = null;
                selectedConnection = null;
                renderNodes();
                renderConnections();
                closeConfigPanel();
            }}
        }});
        
        // 取消连接操作
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') {{
                if (isConnecting) {{
                    isConnecting = false;
                    connectionStart = null;
                    if (tempLine) {{
                        tempLine.remove();
                        tempLine = null;
                    }}
                }}
            }}
        }});
    </script>
    """
    
    return html

# 主界面
st.markdown('<h1 class="main-header">🤖 AI工作流构建平台</h1>', unsafe_allow_html=True)
st.markdown("### 构建可执行的AI工作流，自动化您的任务")

# 侧边栏
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
    st.header("📚 工作流模板")
    templates = {
        "网络搜索助手": "搜索网络上的最新信息并生成总结报告",
        "API数据处理": "调用外部API获取数据，处理后生成分析结果",
        "智能问答系统": "根据用户问题，搜索相关信息并生成准确回答",
        "内容创作工具": "根据主题搜索资料，生成高质量的文章或报告",
        "数据转换管道": "将输入数据进行格式转换和处理"
    }
    
    for name, desc in templates.items():
        if st.button(f"🎯 {name}", use_container_width=True, help=desc):
            st.session_state.template_prompt = desc
    
    st.divider()
    
    # 执行状态
    if st.session_state.execution_state:
        st.header("📊 执行状态")
        for node_id, status in st.session_state.execution_state.items():
            node = next((n for n in st.session_state.current_workflow['nodes'] if n['id'] == node_id), None) if st.session_state.current_workflow else None
            if node:
                status_color = {
                    NodeStatus.PENDING: "⚪",
                    NodeStatus.RUNNING: "🔵",
                    NodeStatus.SUCCESS: "🟢",
                    NodeStatus.FAILED: "🔴",
                    NodeStatus.SKIPPED: "⚫"
                }
                st.write(f"{status_color.get(status, '⚪')} {node['name']}")

# 主要内容区域
tab1, tab2, tab3, tab4 = st.tabs(["🚀 创建工作流", "✏️ 编辑工作流", "▶️ 执行工作流", "📚 我的工作流"])

# Tab1: 创建工作流
with tab1:
    st.subheader("使用自然语言描述您的需求")
    
    # 检查模板
    if 'template_prompt' in st.session_state:
        user_prompt = st.text_area(
            "描述您想要创建的工作流",
            value=st.session_state.template_prompt,
            height=100,
            placeholder="例如：搜索最新的AI技术趋势并生成分析报告..."
        )
        del st.session_state.template_prompt
    else:
        user_prompt = st.text_area(
            "描述您想要创建的工作流",
            height=100,
            placeholder="例如：搜索最新的AI技术趋势并生成分析报告..."
        )
    
    col1, col2 = st.columns([3, 1])
    with col1:
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
                        st.info("您可以在'编辑工作流'标签页中调整节点和连接")
                    else:
                        st.error(f"生成失败：{result['error']}")
    
    with col2:
        st.info("💡 **提示**：\n- 明确说明输入输出\n- 描述处理步骤\n- 提及数据来源")

# Tab2: 编辑工作流
with tab2:
    if st.session_state.current_workflow:
        st.subheader(f"📋 {st.session_state.current_workflow['name']}")
        st.caption(st.session_state.current_workflow['description'])
        
        # 工作流编辑器
        editor_html = create_workflow_editor_html(st.session_state.current_workflow)
        
        # 使用组件显示编辑器
        components.html(editor_html, height=750, scrolling=False)
        
        # JavaScript与Python通信
        workflow_update = components.html("""
        <script>
        window.addEventListener('workflowUpdate', (e) => {
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: e.detail
            }, '*');
        });
        </script>
        """, height=0)
        
        # 保存按钮
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("💾 保存工作流", type="primary"):
                workflow = st.session_state.current_workflow
                workflow['updated_at'] = datetime.now().isoformat()
                if workflow not in st.session_state.workflows:
                    workflow['created_at'] = datetime.now().isoformat()
                    st.session_state.workflows.append(workflow)
                st.success("工作流已保存！")
        
        with col2:
            if st.button("📥 导出JSON"):
                st.download_button(
                    label="下载工作流",
                    data=json.dumps(st.session_state.current_workflow, indent=2),
                    file_name=f"{st.session_state.current_workflow['name']}.json",
                    mime="application/json"
                )
        
        with col3:
            if st.button("🗑️ 清空工作流"):
                st.session_state.current_workflow = None
                st.session_state.execution_state = {}
                st.rerun()
    else:
        st.info("请先在'创建工作流'标签页生成一个工作流")

# Tab3: 执行工作流
with tab3:
    if st.session_state.current_workflow:
        st.subheader(f"▶️ 执行: {st.session_state.current_workflow['name']}")
        
        # 输入区域
        st.markdown("### 输入")
        user_input = st.text_area(
            "请提供工作流的输入内容",
            height=100,
            placeholder="输入您要处理的内容..."
        )
        
        # 执行按钮
        if st.button("🚀 开始执行", type="primary", use_container_width=True):
            if not user_input and st.session_state.current_workflow['nodes'][0]['type'] == 'start':
                st.error("请提供输入内容")
            else:
                # 清空之前的日志
                st.session_state.execution_log = []
                
                # 执行工作流
                executor = WorkflowExecutor(st.session_state.current_workflow, st.session_state.api_key)
                
                # 创建执行容器
                with st.container():
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown("### 执行日志")
                        log_container = st.empty()
                    
                    with col2:
                        st.markdown("### 输出结果")
                        result_container = st.empty()
                    
                    # 异步执行
                    try:
                        # 使用异步执行
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        # 更新日志显示
                        def update_log():
                            log_html = '<div class="execution-log">'
                            for log in st.session_state.execution_log[-20:]:  # 显示最新的20条
                                if "[ERROR]" in log:
                                    log_html += f'<div style="color: #ef4444;">{log}</div>'
                                elif "[WARNING]" in log:
                                    log_html += f'<div style="color: #f59e0b;">{log}</div>'
                                elif "[INFO]" in log:
                                    log_html += f'<div style="color: #10b981;">{log}</div>'
                                else:
                                    log_html += f'<div>{log}</div>'
                            log_html += '</div>'
                            log_container.markdown(log_html, unsafe_allow_html=True)
                        
                        # 开始执行
                        update_log()
                        result = loop.run_until_complete(executor.execute(user_input))
                        
                        # 显示最终结果
                        if result is not None:
                            result_container.success("执行成功！")
                            if isinstance(result, dict) or isinstance(result, list):
                                result_container.json(result)
                            else:
                                result_container.write(result)
                            
                            # 保存执行历史
                            if 'execution_history' not in st.session_state:
                                st.session_state.execution_history = []
                            st.session_state.execution_history.append({
                                'workflow_name': st.session_state.current_workflow['name'],
                                'input': user_input,
                                'output': result,
                                'timestamp': datetime.now().isoformat(),
                                'logs': st.session_state.execution_log.copy()
                            })
                        else:
                            result_container.warning("执行完成，但没有输出结果")
                        
                        # 最终日志更新
                        update_log()
                        
                    except Exception as e:
                        st.error(f"执行失败：{str(e)}")
                        update_log()
                
        # 显示节点输出
        if st.session_state.node_outputs:
            with st.expander("查看节点输出详情"):
                for node_id, outputs in st.session_state.node_outputs.items():
                    node = next((n for n in st.session_state.current_workflow['nodes'] if n['id'] == node_id), None)
                    if node:
                        st.write(f"**{node['name']}** ({node['type']})")
                        st.json(outputs)
                        st.divider()
    else:
        st.info("请先创建或选择一个工作流")

# Tab4: 我的工作流
with tab4:
    st.subheader("📚 已保存的工作流")
    
    if st.session_state.workflows:
        for idx, workflow in enumerate(st.session_state.workflows):
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"### {workflow['name']}")
                    st.caption(workflow['description'])
                    st.caption(f"创建时间: {workflow.get('created_at', 'Unknown')}")
                    st.caption(f"节点数: {len(workflow['nodes'])}")
                
                with col2:
                    if st.button("加载", key=f"load_{idx}"):
                        st.session_state.current_workflow = workflow.copy()
                        st.success("工作流已加载")
                        st.rerun()
                    
                    if st.button("删除", key=f"delete_{idx}"):
                        st.session_state.workflows.pop(idx)
                        st.rerun()
                
                st.divider()
    else:
        st.info("暂无保存的工作流")
    
    # 导入工作流
    st.subheader("📤 导入工作流")
    uploaded_file = st.file_uploader("选择工作流JSON文件", type=['json'])
    if uploaded_file:
        try:
            workflow = json.load(uploaded_file)
            st.session_state.current_workflow = workflow
            st.success("工作流导入成功！")
            st.rerun()
        except Exception as e:
            st.error(f"导入失败：{str(e)}")

# 页脚
st.divider()
st.markdown("""
<div style="text-align: center; color: #6b7280; font-size: 0.875rem;">
    AI工作流构建平台 - 可执行版本 | 支持实时搜索、API调用、智能处理
</div>
""", unsafe_allow_html=True)
