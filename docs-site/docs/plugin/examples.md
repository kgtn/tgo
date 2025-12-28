---
id: examples
title: 完整示例
sidebar_position: 6
---

# 完整示例

本文档提供各可插点的完整插件实现示例，包含 Python 和 Node.js 两种语言版本。

## 示例一：CRM 客户信息插件

一个完整的访客面板插件，展示客户的 CRM 信息、订单记录和操作按钮。

### Python 实现

```python
#!/usr/bin/env python3
"""
TGO 插件示例 - CRM 客户信息
展示客户档案、订单记录、会员信息
通过 Unix Socket 与宿主程序通讯
"""
import os
import sys
import json
import socket
import struct
import signal
import logging
from datetime import datetime
from typing import Optional, Dict, Any

# 配置日志输出到 stderr
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


class TGOPlugin:
    """TGO 插件基类 - 客户端模式"""
    
    # TGO 宿主程序的 Socket 路径
    TGO_SOCKET_PATH = "/var/run/tgo/tgo.sock"
    
    def __init__(self, plugin_name: str, version: str = "1.0.0"):
        self.plugin_name = plugin_name
        self.version = version
        self.running = True
        self.sock = None
    
    def connect(self):
        """连接到 TGO 宿主程序"""
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.TGO_SOCKET_PATH)
        logger.info(f"已连接到 TGO: {self.TGO_SOCKET_PATH}")
    
    def disconnect(self):
        """断开连接"""
        if self.sock:
            self.sock.close()
            self.sock = None
    
    def recv_message(self) -> Optional[Dict[str, Any]]:
        """从 Socket 接收消息"""
        try:
            length_bytes = self._recv_exact(4)
            if not length_bytes:
                return None
            length = struct.unpack('>I', length_bytes)[0]
            json_bytes = self._recv_exact(length)
            if not json_bytes:
                return None
            return json.loads(json_bytes.decode('utf-8'))
        except Exception as e:
            logger.error(f"接收消息错误: {e}")
            return None
    
    def _recv_exact(self, n: int) -> Optional[bytes]:
        """精确接收 n 字节"""
        data = b''
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        return data
    
    def send_message(self, message: Dict[str, Any]):
        """向 Socket 发送消息"""
        json_bytes = json.dumps(message, ensure_ascii=False).encode('utf-8')
        length = struct.pack('>I', len(json_bytes))
        self.sock.sendall(length + json_bytes)
    
    def send_response(self, request_id: Any, result: Dict[str, Any]):
        """发送成功响应"""
        self.send_message({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        })
    
    def send_error(self, request_id: Any, code: int, message: str):
        """发送错误响应"""
        self.send_message({
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message}
        })
    
    def get_capabilities(self) -> list:
        """子类实现：返回插件能力声明"""
        raise NotImplementedError("子类必须实现 get_capabilities 方法")
    
    def register(self) -> bool:
        """向宿主注册插件"""
        self.send_message({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "register",
            "params": {
                "name": self.plugin_name,
                "version": self.version,
                "capabilities": self.get_capabilities()
            }
        })
        
        response = self.recv_message()
        if response and response.get("result", {}).get("success"):
            logger.info("插件注册成功")
            return True
        else:
            logger.error(f"插件注册失败: {response}")
            return False
    
    def run(self):
        """插件主循环"""
        # 信号处理
        def handle_signal(signum, frame):
            self.running = False
            self.disconnect()
            sys.exit(0)
        
        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)
        
        try:
            # 连接并注册
            self.connect()
            if not self.register():
                sys.exit(1)
            
            # 主循环
            while self.running:
                request = self.recv_message()
                if request is None:
                    logger.info("连接已断开")
                    break
                
                method = request.get("method")
                request_id = request.get("id")
                params = request.get("params", {})
                
                logger.debug(f"收到请求: {method}")
                
                # 处理 shutdown
                if method == "shutdown":
                    self.send_response(request_id, {"success": True})
                    break
                
                try:
                    handler = getattr(self, f"handle_{method.replace('/', '_')}", None)
                    if handler:
                        result = handler(params)
                        self.send_response(request_id, result)
                    else:
                        self.send_error(request_id, -32601, f"Method not found: {method}")
                except Exception as e:
                    logger.exception(f"处理请求时出错: {e}")
                    self.send_error(request_id, -32603, str(e))
        
        except ConnectionRefusedError:
            logger.error(f"无法连接到 TGO: {self.TGO_SOCKET_PATH}")
            sys.exit(1)
        finally:
            self.disconnect()


class CRMPlugin(TGOPlugin):
    """CRM 客户信息插件"""
    
    def __init__(self):
        super().__init__("crm-customer-info", "1.0.0")
    
    def get_capabilities(self) -> list:
        """返回插件能力声明"""
        return [
            {
                "type": "visitor_panel",
                "title": "客户档案",
                "icon": "user",
                "priority": 1
            },
            {
                "type": "visitor_panel",
                "title": "订单记录",
                "icon": "shopping-cart",
                "priority": 2
            },
            {
                "type": "chat_toolbar",
                "title": "CRM 操作",
                "icon": "database",
                "tooltip": "CRM 快捷操作"
            }
        ]
    
    def handle_visitor_panel_render(self, params: Dict) -> Dict:
        """渲染访客面板"""
        visitor = params.get("visitor", {})
        metadata = visitor.get("metadata", {})
        
        # 根据 metadata 中的 user_id 获取 CRM 数据
        user_id = metadata.get("user_id")
        
        if not user_id:
            return {
                "template": "empty",
                "data": {
                    "icon": "user-x",
                    "title": "未关联客户",
                    "description": "该访客尚未与 CRM 客户关联",
                    "action": {
                        "id": "link_customer",
                        "label": "关联客户"
                    }
                }
            }
        
        # 模拟从 CRM 获取客户数据
        customer = self._get_customer_data(user_id)
        
        # 返回组合模版
        return {
            "template": "group",
            "data": {
                "items": [
                    # 统计数据
                    {
                        "template": "stats",
                        "data": {
                            "items": [
                                {
                                    "label": "会话次数",
                                    "value": str(customer["session_count"]),
                                    "icon": "message-square"
                                },
                                {
                                    "label": "累计消费",
                                    "value": customer["total_spent"],
                                    "icon": "dollar-sign"
                                },
                                {
                                    "label": "满意度",
                                    "value": customer["satisfaction"],
                                    "icon": "smile",
                                    "color": "green"
                                }
                            ]
                        }
                    },
                    # 客户信息
                    {
                        "template": "key_value",
                        "data": {
                            "title": "客户信息",
                            "items": [
                                {
                                    "label": "客户ID",
                                    "value": customer["id"],
                                    "copyable": True
                                },
                                {
                                    "label": "姓名",
                                    "value": customer["name"]
                                },
                                {
                                    "label": "会员等级",
                                    "value": customer["vip_level"],
                                    "icon": "crown",
                                    "color": "#FFD700"
                                },
                                {
                                    "label": "注册时间",
                                    "value": customer["registered_at"],
                                    "type": "date"
                                },
                                {
                                    "label": "手机号",
                                    "value": customer["phone"],
                                    "copyable": True
                                }
                            ]
                        }
                    },
                    # 标签
                    {
                        "template": "text",
                        "data": {
                            "text": " ".join([f"#{tag}" for tag in customer["tags"]]),
                            "type": "info"
                        }
                    },
                    # 最近订单
                    {
                        "template": "table",
                        "data": {
                            "title": "最近订单",
                            "columns": [
                                {"key": "order_id", "label": "订单号"},
                                {"key": "amount", "label": "金额", "align": "right"},
                                {"key": "status", "label": "状态", "type": "badge"}
                            ],
                            "rows": customer["recent_orders"],
                            "row_click_action": "view_order"
                        }
                    },
                    # 操作按钮
                    {
                        "template": "action",
                        "data": {
                            "buttons": [
                                {
                                    "id": "view_in_crm",
                                    "label": "在 CRM 中查看",
                                    "icon": "external-link",
                                    "type": "primary"
                                },
                                {
                                    "id": "add_tag",
                                    "label": "添加标签",
                                    "icon": "tag",
                                    "type": "default"
                                }
                            ]
                        }
                    }
                ]
            }
        }
    
    def handle_visitor_panel_action(self, params: Dict) -> Dict:
        """处理访客面板按钮点击"""
        action_id = params.get("action_id")
        visitor_id = params.get("visitor_id")
        
        if action_id == "view_in_crm":
            # 返回打开链接动作
            return {
                "action": "open_url",
                "data": {
                    "url": f"https://crm.example.com/customers/{visitor_id}",
                    "target": "_blank"
                }
            }
        elif action_id == "link_customer":
            # 返回表单弹窗
            return {
                "action": "show_modal",
                "data": {
                    "title": "关联客户",
                    "template": "form",
                    "fields": [
                        {
                            "name": "customer_id",
                            "label": "客户ID",
                            "type": "text",
                            "required": True,
                            "placeholder": "请输入 CRM 客户ID"
                        }
                    ],
                    "submit_action": "do_link_customer"
                }
            }
        elif action_id == "add_tag":
            return {
                "action": "show_modal",
                "data": {
                    "title": "添加标签",
                    "template": "form",
                    "fields": [
                        {
                            "name": "tags",
                            "label": "标签",
                            "type": "checkbox",
                            "options": [
                                {"value": "vip", "label": "VIP客户"},
                                {"value": "enterprise", "label": "企业客户"},
                                {"value": "potential", "label": "潜在客户"},
                                {"value": "complaint", "label": "投诉客户"}
                            ]
                        }
                    ],
                    "submit_action": "do_add_tag"
                }
            }
        
        return {"success": True}
    
    def handle_chat_toolbar_action(self, params: Dict) -> Dict:
        """处理聊天工具栏按钮点击"""
        return {
            "action": "show_modal",
            "data": {
                "title": "CRM 操作",
                "template": "list",
                "items": [
                    {"id": "create_ticket", "text": "创建工单", "icon": "file-plus"},
                    {"id": "add_note", "text": "添加备注", "icon": "edit"},
                    {"id": "set_priority", "text": "设置优先级", "icon": "flag"},
                    {"id": "assign_agent", "text": "转接客服", "icon": "user-plus"}
                ],
                "searchable": False
            }
        }
    
    def handle_chat_toolbar_submit(self, params: Dict) -> Dict:
        """处理工具栏表单提交"""
        action_id = params.get("action_id")
        form_data = params.get("form_data", {})
        
        if action_id == "create_ticket":
            # 模拟创建工单
            ticket_id = "TK-" + datetime.now().strftime("%Y%m%d%H%M%S")
            return {
                "action": "notify",
                "data": {
                    "type": "success",
                    "message": f"工单创建成功！工单号: {ticket_id}"
                }
            }
        
        return {"success": True}
    
    def _get_customer_data(self, user_id: str) -> Dict:
        """模拟获取 CRM 客户数据"""
        # 实际场景中，这里应该调用 CRM API
        return {
            "id": user_id,
            "name": "张三",
            "phone": "138****1234",
            "email": "zhangsan@example.com",
            "vip_level": "黄金会员",
            "registered_at": "2023-06-15",
            "session_count": 23,
            "total_spent": "¥12,580",
            "satisfaction": "98%",
            "tags": ["VIP", "企业客户", "活跃"],
            "recent_orders": [
                {
                    "order_id": "ORD-2024001",
                    "amount": "¥299.00",
                    "status": {"text": "已完成", "color": "green"}
                },
                {
                    "order_id": "ORD-2024002",
                    "amount": "¥599.00",
                    "status": {"text": "待发货", "color": "orange"}
                },
                {
                    "order_id": "ORD-2024003",
                    "amount": "¥1,299.00",
                    "status": {"text": "已取消", "color": "gray"}
                }
            ]
        }


if __name__ == "__main__":
    plugin = CRMPlugin("crm-customer-info")
    plugin.run()
```

### Node.js 实现

```javascript
#!/usr/bin/env node
/**
 * TGO 插件示例 - CRM 客户信息
 * 插件作为客户端，连接到 TGO 宿主程序
 */
const net = require('net');

// TGO 宿主程序的 Socket 路径
const TGO_SOCKET_PATH = '/var/run/tgo/tgo.sock';

// 日志输出到 stderr
function log(level, message) {
  console.error(`[${level}] ${message}`);
}

class TGOPlugin {
  constructor(pluginName, version = '1.0.0') {
    this.pluginName = pluginName;
    this.version = version;
    this.running = true;
    this.client = null;
    this.buffer = Buffer.alloc(0);
    this.registered = false;
  }

  /**
   * 解析消息（长度前缀 + JSON）
   */
  parseMessages(buffer) {
    const messages = [];
    let offset = 0;
    
    while (offset + 4 <= buffer.length) {
      const length = buffer.readUInt32BE(offset);
      if (offset + 4 + length > buffer.length) break;
      
      const jsonStr = buffer.slice(offset + 4, offset + 4 + length).toString('utf-8');
      messages.push(JSON.parse(jsonStr));
      offset += 4 + length;
    }
    
    return { messages, remaining: buffer.slice(offset) };
  }

  /**
   * 序列化消息
   */
  serializeMessage(data) {
    const jsonBuffer = Buffer.from(JSON.stringify(data), 'utf-8');
    const lengthBuffer = Buffer.alloc(4);
    lengthBuffer.writeUInt32BE(jsonBuffer.length, 0);
    return Buffer.concat([lengthBuffer, jsonBuffer]);
  }

  sendMessage(message) {
    this.client.write(this.serializeMessage(message));
  }

  sendResponse(requestId, result) {
    this.sendMessage({ jsonrpc: '2.0', id: requestId, result });
  }

  sendError(requestId, code, message) {
    this.sendMessage({
      jsonrpc: '2.0',
      id: requestId,
      error: { code, message }
    });
  }

  /**
   * 子类实现：返回插件能力声明
   */
  getCapabilities() {
    throw new Error('子类必须实现 getCapabilities 方法');
  }

  /**
   * 注册插件
   */
  register() {
    this.sendMessage({
      jsonrpc: '2.0',
      id: 1,
      method: 'register',
      params: {
        name: this.pluginName,
        version: this.version,
        capabilities: this.getCapabilities()
      }
    });
  }

  run() {
    this.client = net.createConnection(TGO_SOCKET_PATH, () => {
      log('INFO', `已连接到 TGO: ${TGO_SOCKET_PATH}`);
      this.register();
    });

    this.client.on('data', async (data) => {
      this.buffer = Buffer.concat([this.buffer, data]);
      const { messages, remaining } = this.parseMessages(this.buffer);
      this.buffer = remaining;

      for (const message of messages) {
        // 处理注册响应
        if (!this.registered && message.result?.success) {
          log('INFO', '插件注册成功');
          this.registered = true;
          continue;
        }

        const { method, id, params = {} } = message;
        
        // 处理 shutdown
        if (method === 'shutdown') {
          this.sendResponse(id, { success: true });
          this.client.end();
          return;
        }

        // 处理业务请求
        if (method) {
          log('DEBUG', `收到请求: ${method}`);
          try {
            const handlerName = `handle_${method.replace(/\//g, '_')}`;
            if (typeof this[handlerName] === 'function') {
              const result = await this[handlerName](params);
              this.sendResponse(id, result);
            } else {
              this.sendError(id, -32601, `Method not found: ${method}`);
            }
          } catch (error) {
            log('ERROR', `处理请求时出错: ${error.message}`);
            this.sendError(id, -32603, error.message);
          }
        }
      }
    });

    this.client.on('error', (err) => {
      log('ERROR', `连接错误: ${err.message}`);
      process.exit(1);
    });

    this.client.on('close', () => {
      log('INFO', '连接已关闭');
      process.exit(0);
    });

    process.on('SIGTERM', () => {
      this.client.end();
      process.exit(0);
    });
  }
}

class CRMPlugin extends TGOPlugin {
  constructor() {
    super('crm-customer-info', '1.0.0');
  }

  getCapabilities() {
    return [
      {
        type: 'visitor_panel',
        title: '客户档案',
        icon: 'user',
        priority: 1
      },
      {
        type: 'visitor_panel',
        title: '订单记录',
        icon: 'shopping-cart',
        priority: 2
      },
      {
        type: 'chat_toolbar',
        title: 'CRM 操作',
        icon: 'database',
        tooltip: 'CRM 快捷操作'
      }
    ];
  }

  handle_shutdown(params) {
    this.running = false;
    setTimeout(() => process.exit(0), 100);
    return { success: true };
  }

  handle_ping(params) {
    return {
      pong: true,
      timestamp: Date.now()
    };
  }

  handle_visitor_panel_render(params) {
    const visitor = params.visitor || {};
    const metadata = visitor.metadata || {};
    const userId = metadata.user_id;

    if (!userId) {
      return {
        template: 'empty',
        data: {
          icon: 'user-x',
          title: '未关联客户',
          description: '该访客尚未与 CRM 客户关联',
          action: {
            id: 'link_customer',
            label: '关联客户'
          }
        }
      };
    }

    const customer = this._getCustomerData(userId);

    return {
      template: 'group',
      data: {
        items: [
          {
            template: 'stats',
            data: {
              items: [
                { label: '会话次数', value: String(customer.session_count), icon: 'message-square' },
                { label: '累计消费', value: customer.total_spent, icon: 'dollar-sign' },
                { label: '满意度', value: customer.satisfaction, icon: 'smile', color: 'green' }
              ]
            }
          },
          {
            template: 'key_value',
            data: {
              title: '客户信息',
              items: [
                { label: '客户ID', value: customer.id, copyable: true },
                { label: '姓名', value: customer.name },
                { label: '会员等级', value: customer.vip_level, icon: 'crown', color: '#FFD700' },
                { label: '注册时间', value: customer.registered_at, type: 'date' },
                { label: '手机号', value: customer.phone, copyable: true }
              ]
            }
          },
          {
            template: 'table',
            data: {
              title: '最近订单',
              columns: [
                { key: 'order_id', label: '订单号' },
                { key: 'amount', label: '金额', align: 'right' },
                { key: 'status', label: '状态', type: 'badge' }
              ],
              rows: customer.recent_orders
            }
          },
          {
            template: 'action',
            data: {
              buttons: [
                { id: 'view_in_crm', label: '在 CRM 中查看', icon: 'external-link', type: 'primary' },
                { id: 'add_tag', label: '添加标签', icon: 'tag', type: 'default' }
              ]
            }
          }
        ]
      }
    };
  }

  handle_chat_toolbar_action(params) {
    return {
      action: 'show_modal',
      data: {
        title: 'CRM 操作',
        template: 'list',
        items: [
          { id: 'create_ticket', text: '创建工单', icon: 'file-plus' },
          { id: 'add_note', text: '添加备注', icon: 'edit' },
          { id: 'set_priority', text: '设置优先级', icon: 'flag' },
          { id: 'assign_agent', text: '转接客服', icon: 'user-plus' }
        ]
      }
    };
  }

  _getCustomerData(userId) {
    return {
      id: userId,
      name: '张三',
      phone: '138****1234',
      vip_level: '黄金会员',
      registered_at: '2023-06-15',
      session_count: 23,
      total_spent: '¥12,580',
      satisfaction: '98%',
      tags: ['VIP', '企业客户'],
      recent_orders: [
        { order_id: 'ORD-2024001', amount: '¥299.00', status: { text: '已完成', color: 'green' } },
        { order_id: 'ORD-2024002', amount: '¥599.00', status: { text: '待发货', color: 'orange' } }
      ]
    };
  }
}

const plugin = new CRMPlugin('crm-customer-info');
plugin.run();
```

---

## 示例二：快捷回复插件

一个聊天工具栏插件，提供常用回复模板和 AI 辅助回复。

### Python 实现

:::tip 简化示例
以下示例使用函数式风格编写，实际应用中建议参考「示例一」使用 `TGOPlugin` 基类来处理 Socket 连接和消息收发。
:::

```python
#!/usr/bin/env python3
"""
TGO 插件示例 - 快捷回复
提供常用回复模板和 AI 辅助回复

注意：此为简化示例，省略了 Socket 连接代码
完整实现请参考示例一的 TGOPlugin 基类
"""

# 预设回复模板
QUICK_REPLIES = {
    "greeting": [
        {"id": "g1", "text": "您好！感谢您的咨询，请问有什么可以帮您？"},
        {"id": "g2", "text": "您好！很高兴为您服务，请问有什么问题需要帮助？"},
        {"id": "g3", "text": "欢迎咨询！请问您需要了解什么？"},
    ],
    "shipping": [
        {"id": "s1", "text": "订单一般在付款后 1-2 个工作日内发货。"},
        {"id": "s2", "text": "快递通常 3-5 个工作日送达，偏远地区可能稍慢。"},
        {"id": "s3", "text": "发货后会短信通知您物流单号，可在订单详情中查看。"},
    ],
    "return": [
        {"id": "r1", "text": "我们支持 7 天无理由退换货，商品需保持原包装。"},
        {"id": "r2", "text": "退货请先在订单中申请，客服审核后会提供退货地址。"},
        {"id": "r3", "text": "退款将在收到退货后 3-5 个工作日内原路返回。"},
    ],
    "ending": [
        {"id": "e1", "text": "感谢您的咨询！如有其他问题随时联系我们。"},
        {"id": "e2", "text": "祝您购物愉快！如有问题欢迎随时咨询。"},
        {"id": "e3", "text": "很高兴能帮到您，祝您生活愉快！"},
    ]
}

# 插件信息
PLUGIN_NAME = "quick-reply"
PLUGIN_VERSION = "1.0.0"
PLUGIN_CAPABILITIES = [
    {
        "type": "chat_toolbar",
        "title": "快捷回复",
        "icon": "zap",
        "tooltip": "选择常用回复模板",
        "shortcut": "Ctrl+Shift+R"
    },
    {
        "type": "chat_toolbar",
        "title": "AI 补全",
        "icon": "sparkles",
        "tooltip": "AI 辅助回复",
        "shortcut": "Ctrl+Shift+A"
    }
]

def handle_chat_toolbar_action(request):
    params = request.get("params", {})
    action_id = params.get("action_id", "quick_reply")
    
    if action_id == "ai_complete":
        # AI 补全 - 根据上下文生成回复
        context = params.get("context", {})
        input_text = context.get("input_text", "")
        last_messages = context.get("last_messages", [])
        
        # 这里应该调用 AI API，示例返回模拟结果
        suggestions = generate_ai_suggestions(last_messages, input_text)
        
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "action": "show_modal",
                "data": {
                    "title": "AI 建议回复",
                    "template": "list",
                    "items": suggestions,
                    "searchable": False
                }
            }
        }
    else:
        # 快捷回复 - 显示分类列表
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "action": "show_modal",
                "data": {
                    "title": "快捷回复",
                    "template": "tabs",
                    "items": [
                        {
                            "key": "greeting",
                            "label": "问候语",
                            "icon": "hand",
                            "content": {
                                "template": "list",
                                "data": {
                                    "items": QUICK_REPLIES["greeting"]
                                }
                            }
                        },
                        {
                            "key": "shipping",
                            "label": "发货物流",
                            "icon": "truck",
                            "content": {
                                "template": "list",
                                "data": {
                                    "items": QUICK_REPLIES["shipping"]
                                }
                            }
                        },
                        {
                            "key": "return",
                            "label": "退换货",
                            "icon": "refresh-ccw",
                            "content": {
                                "template": "list",
                                "data": {
                                    "items": QUICK_REPLIES["return"]
                                }
                            }
                        },
                        {
                            "key": "ending",
                            "label": "结束语",
                            "icon": "check-circle",
                            "content": {
                                "template": "list",
                                "data": {
                                    "items": QUICK_REPLIES["ending"]
                                }
                            }
                        }
                    ],
                    "default_tab": "greeting"
                }
            }
        }

def handle_chat_toolbar_select(request):
    """处理用户选择快捷回复"""
    params = request.get("params", {})
    selected_id = params.get("selected_id")
    
    # 查找选中的回复文本
    text = None
    for category, replies in QUICK_REPLIES.items():
        for reply in replies:
            if reply["id"] == selected_id:
                text = reply["text"]
                break
    
    if text:
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "action": "insert_text",
                "data": {
                    "text": text,
                    "replace": False
                }
            }
        }
    
    return {
        "jsonrpc": "2.0",
        "id": request["id"],
        "result": {"success": True}
    }

def generate_ai_suggestions(last_messages, input_text):
    """模拟 AI 生成回复建议"""
    # 实际场景应调用 LLM API
    last_visitor_msg = ""
    for msg in reversed(last_messages):
        if msg.get("role") == "visitor":
            last_visitor_msg = msg.get("content", "")
            break
    
    # 简单的关键词匹配模拟
    if "发货" in last_visitor_msg or "物流" in last_visitor_msg:
        return [
            {"id": "ai1", "text": "您的订单预计明天发货，发货后会短信通知您物流信息。"},
            {"id": "ai2", "text": "物流一般3-5天送达，您可以在订单详情中实时追踪。"},
        ]
    elif "退" in last_visitor_msg:
        return [
            {"id": "ai1", "text": "我们支持7天无理由退货，请在订单页面提交退货申请。"},
            {"id": "ai2", "text": "收到退货后我们会在3个工作日内完成退款。"},
        ]
    else:
        return [
            {"id": "ai1", "text": "感谢您的咨询！请问还有什么可以帮您的吗？"},
            {"id": "ai2", "text": "好的，我已经记录下来了，还有其他问题吗？"},
        ]

# 使用 TGOPlugin 基类运行（参考示例一）
# 以下为处理函数，需配合 TGOPlugin 基类使用
#
# class QuickReplyPlugin(TGOPlugin):
#     def __init__(self):
#         super().__init__(PLUGIN_NAME, PLUGIN_VERSION)
#     
#     def get_capabilities(self):
#         return PLUGIN_CAPABILITIES
#     
#     def handle_chat_toolbar_action(self, params):
#         return handle_chat_toolbar_action({"params": params})["result"]
#     
#     def handle_chat_toolbar_select(self, params):
#         return handle_chat_toolbar_select({"params": params})["result"]
#
# if __name__ == "__main__":
#     plugin = QuickReplyPlugin()
#     plugin.run()
```

---

## 示例三：第三方平台接入插件

接入自定义 IM 平台的完整示例。

### Python 实现

:::tip 简化示例
以下示例展示核心业务逻辑，Socket 连接处理请参考「示例一」的 `TGOPlugin` 基类。
:::

```python
#!/usr/bin/env python3
"""
TGO 插件示例 - 自定义 IM 平台接入
继承 TGOPlugin 基类实现（完整基类代码见示例一）
"""
import requests
from typing import Dict, Any

# 插件信息
PLUGIN_NAME = "custom-im-integration"
PLUGIN_VERSION = "1.0.0"
PLUGIN_CAPABILITIES = [
    {
        "type": "channel_integration",
        "channel_type": "custom_im",
        "name": "自定义IM",
        "icon": "message-circle"
    }
]

class CustomIMPlugin:
    """自定义 IM 平台接入插件（业务逻辑部分）"""
    
    def __init__(self):
        self.config = {}
    
    def handle_channel_integration_manifest(self, request: Dict) -> Dict:
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "channel_type": "custom_im",
                "name": "自定义IM平台",
                "icon": "message-circle",
                "description": "接入自定义 IM 平台，支持消息双向同步、已读回执等功能。",
                
                "config_schema": {
                    "type": "object",
                    "properties": {
                        "api_endpoint": {
                            "type": "string",
                            "title": "API 地址",
                            "description": "自定义 IM 平台的 API 接口地址",
                            "placeholder": "https://api.your-im.com"
                        },
                        "app_id": {
                            "type": "string",
                            "title": "应用 ID",
                            "description": "在 IM 平台创建的应用 ID"
                        },
                        "app_secret": {
                            "type": "string",
                            "title": "应用密钥",
                            "format": "password",
                            "description": "应用的密钥，请妥善保管"
                        },
                        "features": {
                            "type": "object",
                            "title": "功能配置",
                            "properties": {
                                "enable_typing": {
                                    "type": "boolean",
                                    "title": "正在输入提示",
                                    "default": True
                                },
                                "enable_read_receipt": {
                                    "type": "boolean",
                                    "title": "已读回执",
                                    "default": False
                                },
                                "auto_reply_offline": {
                                    "type": "boolean",
                                    "title": "离线自动回复",
                                    "default": True
                                }
                            }
                        }
                    },
                    "required": ["api_endpoint", "app_id", "app_secret"]
                },
                
                "setup_guide": """# 自定义 IM 平台接入指南

## 前置条件

1. 已注册自定义 IM 平台开发者账号
2. 已创建应用并获取 App ID 和 App Secret

## 接入步骤

### 步骤一：配置 Webhook

登录 IM 平台后台，将以下地址配置为消息回调地址：

```
https://your-tgo-domain.com/api/webhooks/custom-im
```

### 步骤二：填写配置

在上方表单中填写：
- **API 地址**：IM 平台提供的 API 接口地址
- **应用 ID**：创建应用时获取的 App ID
- **应用密钥**：创建应用时获取的 App Secret

### 步骤三：测试连接

保存配置后，点击「测试连接」按钮验证配置是否正确。

## 支持的消息类型

| 类型 | 发送 | 接收 |
|------|------|------|
| 文本消息 | ✅ | ✅ |
| 图片消息 | ✅ | ✅ |
| 文件消息 | ✅ | ✅ |
| 语音消息 | ❌ | ✅ |
| 视频消息 | ❌ | ✅ |

## 常见问题

**Q: 消息发送失败怎么办？**

A: 请检查 API 地址和密钥是否正确，确保网络可以访问 IM 平台。

**Q: 如何查看消息日志？**

A: 在 TGO 后台的「渠道管理」中可以查看消息收发日志。
""",
                
                "webhook_endpoint": "/api/webhooks/custom-im",
                
                "capabilities": {
                    "send_text": True,
                    "send_image": True,
                    "send_file": True,
                    "send_rich_card": False,
                    "receive_text": True,
                    "receive_image": True,
                    "receive_file": True,
                    "receive_voice": True,
                    "receive_video": True,
                    "typing_indicator": True,
                    "read_receipt": True
                }
            }
        }
    
    def handle_channel_integration_configure(self, request: Dict) -> Dict:
        """保存配置"""
        params = request.get("params", {})
        self.config = params.get("config", {})
        
        # 验证配置
        api_endpoint = self.config.get("api_endpoint", "")
        app_id = self.config.get("app_id", "")
        app_secret = self.config.get("app_secret", "")
        
        if not all([api_endpoint, app_id, app_secret]):
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "error": {
                    "code": -32602,
                    "message": "缺少必填配置项"
                }
            }
        
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {"success": True}
        }
    
    def handle_channel_integration_test_connection(self, request: Dict) -> Dict:
        """测试连接"""
        api_endpoint = self.config.get("api_endpoint", "")
        app_id = self.config.get("app_id", "")
        app_secret = self.config.get("app_secret", "")
        
        try:
            # 调用 IM 平台的测试接口
            response = requests.post(
                f"{api_endpoint}/api/test",
                json={"app_id": app_id},
                headers={"Authorization": f"Bearer {app_secret}"},
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "result": {
                        "success": True,
                        "message": "连接成功！"
                    }
                }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "result": {
                        "success": False,
                        "message": f"连接失败: {response.text}"
                    }
                }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "success": False,
                    "message": f"连接错误: {str(e)}"
                }
            }
    
    def handle_channel_integration_send_message(self, request: Dict) -> Dict:
        """发送消息到 IM 平台"""
        params = request.get("params", {})
        channel_id = params.get("channel_id")
        to = params.get("to", {})
        message = params.get("message", {})
        
        api_endpoint = self.config.get("api_endpoint", "")
        app_secret = self.config.get("app_secret", "")
        
        try:
            response = requests.post(
                f"{api_endpoint}/api/messages/send",
                json={
                    "to_user": to.get("id"),
                    "message_type": message.get("type", "text"),
                    "content": message.get("content")
                },
                headers={"Authorization": f"Bearer {app_secret}"},
                timeout=30
            )
            
            result = response.json()
            
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "success": True,
                    "message_id": result.get("message_id")
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "error": {
                    "code": -32000,
                    "message": f"发送失败: {str(e)}"
                }
            }
    
    def run(self):
        while self.running:
            request = read_request()
            if request is None:
                break
            
            method = request.get("method", "")
            handler_name = f"handle_{method.replace('/', '_')}"
            
            handler = getattr(self, handler_name, None)
            if handler:
                response = handler(request)
            elif method == "shutdown":
                self.running = False
                response = {
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "result": {"success": True}
                }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                }
            
            send_response(response)


if __name__ == "__main__":
    plugin = CustomIMPlugin()
    plugin.run()
```

---

## 示例四：iframe 应用插件

提供 iframe 应用 URL 的简单插件。

### Python 实现

```python
#!/usr/bin/env python3
"""
TGO 插件示例 - iframe 应用
在聊天界面右侧嵌入外部应用
"""
import sys
import json

def read_request():
    line = sys.stdin.readline()
    if not line:
        return None
    return json.loads(line.strip())

def send_response(response):
    print(json.dumps(response, ensure_ascii=False), flush=True)

def handle_initialize(request):
    return {
        "jsonrpc": "2.0",
        "id": request["id"],
        "result": {
            "name": "crm-iframe-app",
            "version": "1.0.0",
            "description": "CRM 系统嵌入应用",
            "capabilities": [
                {
                    "type": "sidebar_iframe",
                    "title": "CRM 系统",
                    "icon": "users",
                    "url": "https://crm.example.com/tgo-embed",
                    "width": 400
                },
                {
                    "type": "sidebar_iframe",
                    "title": "工单系统",
                    "icon": "ticket",
                    "url": "https://ticket.example.com/tgo-embed",
                    "width": 350
                }
            ]
        }
    }

def handle_sidebar_iframe_config(request):
    """返回 iframe 配置详情"""
    return {
        "jsonrpc": "2.0",
        "id": request["id"],
        "result": {
            "apps": [
                {
                    "id": "crm",
                    "url": "https://crm.example.com/tgo-embed",
                    "title": "CRM 系统",
                    "icon": "users",
                    "width": 400,
                    "min_width": 300,
                    "max_width": 600,
                    "allow_fullscreen": True,
                    "sandbox": "allow-scripts allow-same-origin allow-forms allow-popups",
                    "permissions": ["clipboard-read", "clipboard-write"]
                },
                {
                    "id": "ticket",
                    "url": "https://ticket.example.com/tgo-embed",
                    "title": "工单系统",
                    "icon": "ticket",
                    "width": 350,
                    "allow_fullscreen": True
                }
            ]
        }
    }

# 使用 TGOPlugin 基类运行（参考示例一）
# 以下为处理函数，需配合 TGOPlugin 基类使用
#
# class DataDashboardPlugin(TGOPlugin):
#     def __init__(self):
#         super().__init__("data-dashboard", "1.0.0")
#     
#     def get_capabilities(self):
#         return PLUGIN_CAPABILITIES
#     
#     def handle_sidebar_iframe_config(self, params):
#         return handle_sidebar_iframe_config({"params": params})["result"]
#
# if __name__ == "__main__":
#     plugin = DataDashboardPlugin()
#     plugin.run()
```

---

## 插件配置文件示例

### plugin.json

```json
{
  "name": "crm-customer-info",
  "version": "1.0.0",
  "description": "CRM 客户信息插件",
  "author": "Your Name",
  "homepage": "https://github.com/your-org/tgo-crm-plugin",
  "license": "MIT",
  
  "runtime": {
    "command": "python3",
    "args": ["main.py"],
    "working_directory": ".",
    "env": {
      "CRM_API_URL": "https://crm.example.com/api"
    }
  },
  
  "requirements": {
    "python": ">=3.8",
    "packages": ["requests>=2.28.0"]
  }
}
```

## 测试脚本

### test_server.py

模拟 TGO 宿主程序，用于测试插件：

```python
#!/usr/bin/env python3
"""模拟 TGO 宿主程序 - 测试插件"""
import os
import socket
import struct
import json

TGO_SOCKET_PATH = "/var/run/tgo/tgo.sock"

def send_message(conn, data):
    json_bytes = json.dumps(data).encode('utf-8')
    conn.sendall(struct.pack('>I', len(json_bytes)) + json_bytes)

def recv_message(conn):
    length_bytes = conn.recv(4)
    if not length_bytes:
        return None
    length = struct.unpack('>I', length_bytes)[0]
    return json.loads(conn.recv(length).decode('utf-8'))

# 准备 Socket
os.makedirs(os.path.dirname(TGO_SOCKET_PATH), exist_ok=True)
if os.path.exists(TGO_SOCKET_PATH):
    os.unlink(TGO_SOCKET_PATH)

server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(TGO_SOCKET_PATH)
server.listen(1)
print(f"[TGO 模拟] 监听: {TGO_SOCKET_PATH}")
print("[TGO 模拟] 请启动插件...")

conn, _ = server.accept()
print("[TGO 模拟] 插件已连接!")

# 接收 register 请求
request = recv_message(conn)
print(f"\n=== 收到 register ===")
print(json.dumps(request, indent=2, ensure_ascii=False))

# 返回注册成功
send_message(conn, {
    "jsonrpc": "2.0",
    "id": request["id"],
    "result": {"success": True, "plugin_id": "test_001"}
})

# 测试访客面板渲染
print("\n=== 发送 visitor_panel/render ===")
send_message(conn, {
    "jsonrpc": "2.0", "id": 2,
    "method": "visitor_panel/render",
    "params": {"visitor_id": "v_123", "visitor": {"name": "测试用户"}}
})
print(json.dumps(recv_message(conn), indent=2, ensure_ascii=False))

# 关闭
send_message(conn, {"jsonrpc": "2.0", "id": 99, "method": "shutdown"})
recv_message(conn)
conn.close()
server.close()
os.unlink(TGO_SOCKET_PATH)
print("\n[TGO 模拟] 测试完成!")
```

---

## 下一步

- [通讯协议](/plugin/protocol) - 深入了解协议细节
- [模版规范](/plugin/templates) - 了解所有 UI 模版类型
- [可插点详解](/plugin/extension-points) - 了解每个可插点的详细用法

