---
id: quickstart
title: 快速入门
sidebar_position: 2
---

# 快速入门

本指南将帮助你在 5 分钟内创建并运行第一个 TGO 插件。

## 前置条件

- 已安装 Python 3.8+ 或 Node.js 16+
- 了解 JSON 基本语法
- TGO 系统已部署运行

## 创建第一个插件

我们将创建一个简单的「访客面板」插件，在访客信息面板中显示客户的订单信息。

### 步骤 1：创建插件目录

```bash
mkdir my-first-plugin
cd my-first-plugin
```

### 步骤 2：编写插件代码

创建 `main.py` 文件：

```python
#!/usr/bin/env python3
"""
TGO 插件示例 - 访客订单信息
插件作为客户端，连接到 TGO 宿主程序的 Unix Socket
"""
import sys
import json
import socket
import struct
import signal

# 插件信息
PLUGIN_NAME = "visitor-orders"
PLUGIN_VERSION = "1.0.0"

# TGO 宿主程序的 Socket 路径
TGO_SOCKET_PATH = "/var/run/tgo/tgo.sock"


class TGOClient:
    """TGO 插件客户端"""
    
    def __init__(self, socket_path: str):
        self.socket_path = socket_path
        self.sock = None
        self.running = True
    
    def connect(self):
        """连接到 TGO 宿主程序"""
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_path)
        print(f"[INFO] 已连接到 TGO: {self.socket_path}", file=sys.stderr)
    
    def disconnect(self):
        """断开连接"""
        if self.sock:
            self.sock.close()
            self.sock = None
    
    def send_message(self, data: dict):
        """发送消息（长度前缀 + JSON）"""
        json_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
        length = struct.pack('>I', len(json_bytes))
        self.sock.sendall(length + json_bytes)
    
    def recv_message(self) -> dict:
        """接收消息"""
        length_bytes = self._recv_exact(4)
        if not length_bytes:
            return None
        length = struct.unpack('>I', length_bytes)[0]
        json_bytes = self._recv_exact(length)
        if not json_bytes:
            return None
        return json.loads(json_bytes.decode('utf-8'))
    
    def _recv_exact(self, n: int) -> bytes:
        """精确接收 n 字节"""
        data = b''
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        return data
    
    def register(self):
        """向宿主注册插件能力"""
        self.send_message({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "register",
            "params": {
                "name": PLUGIN_NAME,
                "version": PLUGIN_VERSION,
                "description": "显示访客的订单信息",
                "capabilities": [
                    {
                        "type": "visitor_panel",
                        "title": "客户订单",
                        "icon": "shopping-cart"
                    }
                ]
            }
        })
        
        # 等待注册响应
        response = self.recv_message()
        if response and response.get("result", {}).get("success"):
            print(f"[INFO] 插件注册成功", file=sys.stderr)
            return True
        else:
            print(f"[ERROR] 插件注册失败: {response}", file=sys.stderr)
            return False


def handle_visitor_panel_render(request):
    """处理访客面板渲染请求，返回 JSON-UI"""
    params = request.get("params", {})
    visitor_id = params.get("visitor_id")
    
    # 这里可以调用你的业务 API 获取真实数据
    orders = [
        {"order_id": "ORD-001", "amount": "¥299.00", "status": "已完成"},
        {"order_id": "ORD-002", "amount": "¥599.00", "status": "待发货"},
    ]
    
    # 返回 JSON-UI：包含表格和操作按钮
    return {
        "jsonrpc": "2.0",
        "id": request["id"],
        "result": {
            "template": "group",
            "data": {
                "items": [
                    {
                        "template": "table",
                        "data": {
                            "title": "最近订单",
                            "columns": [
                                {"key": "order_id", "label": "订单号"},
                                {"key": "amount", "label": "金额"},
                                {"key": "status", "label": "状态"}
                            ],
                            "rows": orders
                        }
                    },
                    {
                        "template": "action",
                        "data": {
                            "buttons": [
                                {"id": "view_all", "label": "查看全部订单", "type": "primary"}
                            ]
                        }
                    }
                ]
            }
        }
    }


def handle_visitor_panel_event(request):
    """处理访客面板事件，返回 JSON-ACTION"""
    params = request.get("params", {})
    action_id = params.get("action_id")
    visitor_id = params.get("visitor_id")
    
    if action_id == "view_all":
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "action": "open_url",
                "data": {
                    "url": f"https://crm.example.com/orders?visitor={visitor_id}",
                    "target": "_blank"
                }
            }
        }
    
    return {
        "jsonrpc": "2.0",
        "id": request["id"],
        "result": {"action": "noop", "data": {}}
    }


def handle_request(request: dict) -> dict:
    """路由请求到对应处理函数"""
    method = request.get("method")
    
    handlers = {
        "visitor_panel/render": handle_visitor_panel_render,
        "visitor_panel/event": handle_visitor_panel_event,
    }
    
    handler = handlers.get(method)
    if handler:
        return handler(request)
    
    return {
        "jsonrpc": "2.0",
        "id": request.get("id"),
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}"
        }
    }


def main():
    """插件主函数"""
    client = TGOClient(TGO_SOCKET_PATH)
    
    # 信号处理
    def cleanup(signum, frame):
        client.disconnect()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)
    
    try:
        # 连接到 TGO 宿主程序
        client.connect()
        
        # 注册插件
        if not client.register():
            sys.exit(1)
        
        # 主循环：等待并处理来自宿主的请求
        while client.running:
            request = client.recv_message()
            if request is None:
                print("[INFO] 连接已断开", file=sys.stderr)
                break
            
            method = request.get("method")
            print(f"[DEBUG] 收到请求: {method}", file=sys.stderr)
            
            # 处理 shutdown 请求
            if method == "shutdown":
                client.send_message({
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "result": {"success": True}
                })
                break
            
            # 处理业务请求
            response = handle_request(request)
            client.send_message(response)
    
    except ConnectionRefusedError:
        print(f"[ERROR] 无法连接到 TGO: {TGO_SOCKET_PATH}", file=sys.stderr)
        print("[ERROR] 请确保 TGO 服务已启动", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] 发生错误: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
```

### 步骤 3：测试插件

由于插件是客户端，需要先启动一个模拟的 TGO 宿主服务器进行测试。

#### 创建测试服务器

创建 `test_server.py` 模拟 TGO 宿主程序：

```python
#!/usr/bin/env python3
"""测试服务器 - 模拟 TGO 宿主程序"""
import os
import socket
import struct
import json

SOCKET_PATH = "/var/run/tgo/tgo.sock"

def recv_message(conn):
    """接收消息"""
    length_bytes = conn.recv(4)
    if not length_bytes:
        return None
    length = struct.unpack('>I', length_bytes)[0]
    json_bytes = conn.recv(length)
    return json.loads(json_bytes.decode('utf-8'))

def send_message(conn, data):
    """发送消息"""
    json_bytes = json.dumps(data).encode('utf-8')
    conn.sendall(struct.pack('>I', len(json_bytes)) + json_bytes)

# 准备 Socket
os.makedirs(os.path.dirname(SOCKET_PATH), exist_ok=True)
if os.path.exists(SOCKET_PATH):
    os.unlink(SOCKET_PATH)

server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind(SOCKET_PATH)
server.listen(1)
print(f"[TGO 模拟服务器] 监听: {SOCKET_PATH}")
print("[TGO 模拟服务器] 等待插件连接...")

conn, _ = server.accept()
print("[TGO 模拟服务器] 插件已连接!")

# 接收插件的 register 请求
request = recv_message(conn)
print(f"\n=== 收到 register 请求 ===")
print(json.dumps(request, indent=2, ensure_ascii=False))

# 返回注册成功
send_message(conn, {
    "jsonrpc": "2.0",
    "id": request["id"],
    "result": {"success": True, "plugin_id": "plugin_001", "host_version": "1.0.0"}
})
print("[TGO 模拟服务器] 已发送注册成功响应")

# 发送渲染请求
print("\n=== 发送 visitor_panel/render 请求 ===")
send_message(conn, {
    "jsonrpc": "2.0", "id": 2,
    "method": "visitor_panel/render",
    "params": {"visitor_id": "v_12345"}
})
response = recv_message(conn)
print("收到响应 (JSON-UI):")
print(json.dumps(response, indent=2, ensure_ascii=False))

# 发送事件请求
print("\n=== 发送 visitor_panel/event 请求 ===")
send_message(conn, {
    "jsonrpc": "2.0", "id": 3,
    "method": "visitor_panel/event",
    "params": {"action_id": "view_all", "visitor_id": "v_12345"}
})
response = recv_message(conn)
print("收到响应 (JSON-ACTION):")
print(json.dumps(response, indent=2, ensure_ascii=False))

# 发送 shutdown
print("\n=== 发送 shutdown 请求 ===")
send_message(conn, {"jsonrpc": "2.0", "id": 99, "method": "shutdown"})
response = recv_message(conn)
print("收到响应:", response)

conn.close()
server.close()
os.unlink(SOCKET_PATH)
print("\n[TGO 模拟服务器] 测试完成!")
```

#### 运行测试

**终端 1**：启动测试服务器

```bash
# 创建目录（需要权限）
sudo mkdir -p /var/run/tgo
sudo chown $USER /var/run/tgo

# 启动测试服务器
python3 test_server.py
```

**终端 2**：启动插件

```bash
python3 main.py
```

预期输出（JSON-ACTION）：

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "action": "open_url",
    "data": {
      "url": "https://crm.example.com/orders?visitor=v_12345",
      "target": "_blank"
    }
  }
}
```

### 步骤 4：部署插件

创建插件配置文件 `plugin.json`：

```json
{
  "name": "visitor-orders",
  "version": "1.0.0",
  "description": "显示访客的订单信息",
  "command": "python3",
  "args": ["main.py"],
  "working_directory": "/path/to/my-first-plugin"
}
```

部署插件到 TGO：

```bash
# 复制插件到 TGO 插件目录
cp -r my-first-plugin /path/to/tgo/plugins/

# TGO 会自动启动插件进程
# 插件启动后会自动连接到 TGO 并注册能力
./tgo.sh restart
```

:::tip 插件生命周期
1. TGO 启动时，会自动启动配置的插件进程
2. 插件进程启动后，自动连接到 TGO 的 Socket（`/var/run/tgo/tgo.sock`）
3. 插件发送 `register` 请求注册能力
4. TGO 收到注册后，插件即可接收业务请求
:::

## Node.js 版本

如果你更熟悉 JavaScript，可以使用 Node.js 开发：

创建 `main.js` 文件：

```javascript
#!/usr/bin/env node
/**
 * TGO 插件示例 - 访客订单信息 (Node.js 版本)
 * 插件作为客户端，连接到 TGO 宿主程序的 Unix Socket
 */
const net = require('net');

// 插件信息
const PLUGIN_NAME = 'visitor-orders';
const PLUGIN_VERSION = '1.0.0';

// TGO 宿主程序的 Socket 路径
const TGO_SOCKET_PATH = '/var/run/tgo/tgo.sock';

/**
 * 从 Buffer 读取消息
 */
function parseMessages(buffer) {
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
 * 序列化消息为 Buffer
 */
function serializeMessage(data) {
  const jsonBuffer = Buffer.from(JSON.stringify(data), 'utf-8');
  const lengthBuffer = Buffer.alloc(4);
  lengthBuffer.writeUInt32BE(jsonBuffer.length, 0);
  return Buffer.concat([lengthBuffer, jsonBuffer]);
}

function handleVisitorPanelRender(request) {
  const { visitor_id } = request.params || {};
  
  const orders = [
    { order_id: 'ORD-001', amount: '¥299.00', status: '已完成' },
    { order_id: 'ORD-002', amount: '¥599.00', status: '待发货' }
  ];
  
  return {
    jsonrpc: '2.0',
    id: request.id,
    result: {
      template: 'group',
      data: {
        items: [
          {
            template: 'table',
            data: {
              title: '最近订单',
              columns: [
                { key: 'order_id', label: '订单号' },
                { key: 'amount', label: '金额' },
                { key: 'status', label: '状态' }
              ],
              rows: orders
            }
          },
          {
            template: 'action',
            data: {
              buttons: [
                { id: 'view_all', label: '查看全部订单', type: 'primary' }
              ]
            }
          }
        ]
      }
    }
  };
}

function handleVisitorPanelEvent(request) {
  const { action_id, visitor_id } = request.params || {};
  
  if (action_id === 'view_all') {
    return {
      jsonrpc: '2.0',
      id: request.id,
      result: {
        action: 'open_url',
        data: {
          url: `https://crm.example.com/orders?visitor=${visitor_id}`,
          target: '_blank'
        }
      }
    };
  }
  
  return {
    jsonrpc: '2.0',
    id: request.id,
    result: { action: 'noop', data: {} }
  };
}

function handleRequest(request) {
  const { method } = request;
  
  switch (method) {
    case 'visitor_panel/render':
      return handleVisitorPanelRender(request);
    case 'visitor_panel/event':
      return handleVisitorPanelEvent(request);
    default:
      return {
        jsonrpc: '2.0',
        id: request.id,
        error: { code: -32601, message: `Method not found: ${method}` }
      };
  }
}

// 连接到 TGO 宿主程序
const client = net.createConnection(TGO_SOCKET_PATH, () => {
  console.error(`[INFO] 已连接到 TGO: ${TGO_SOCKET_PATH}`);
  
  // 发送 register 请求
  client.write(serializeMessage({
    jsonrpc: '2.0',
    id: 1,
    method: 'register',
    params: {
      name: PLUGIN_NAME,
      version: PLUGIN_VERSION,
      description: '显示访客的订单信息',
      capabilities: [
        {
          type: 'visitor_panel',
          title: '客户订单',
          icon: 'shopping-cart'
        }
      ]
    }
  }));
});

let buffer = Buffer.alloc(0);
let registered = false;

client.on('data', (data) => {
  buffer = Buffer.concat([buffer, data]);
  const { messages, remaining } = parseMessages(buffer);
  buffer = remaining;
  
  for (const message of messages) {
    // 处理注册响应
    if (!registered && message.result?.success) {
      console.error('[INFO] 插件注册成功');
      registered = true;
      continue;
    }
    
    // 处理 shutdown 请求
    if (message.method === 'shutdown') {
      client.write(serializeMessage({
        jsonrpc: '2.0',
        id: message.id,
        result: { success: true }
      }));
      client.end();
      return;
    }
    
    // 处理业务请求
    if (message.method) {
      console.error(`[DEBUG] 收到请求: ${message.method}`);
      const response = handleRequest(message);
      client.write(serializeMessage(response));
    }
  }
});

client.on('error', (err) => {
  console.error(`[ERROR] 连接错误: ${err.message}`);
  console.error('[ERROR] 请确保 TGO 服务已启动');
  process.exit(1);
});

client.on('close', () => {
  console.error('[INFO] 连接已关闭');
  process.exit(0);
});

// 优雅关闭
process.on('SIGTERM', () => {
  client.end();
  process.exit(0);
});
```

## 调试技巧

### 1. 日志输出

调试日志输出到 stderr（不影响 Socket 通讯）：

```python
import sys

def log(message):
    print(f"[DEBUG] {message}", file=sys.stderr)
```

```javascript
function log(message) {
  console.error(`[DEBUG] ${message}`);
}
```

### 2. 查看 Socket 状态

```bash
# 检查 TGO Socket 文件是否存在
ls -la /var/run/tgo/tgo.sock

# 使用 lsof 查看 Socket 连接
lsof -U | grep tgo.sock
```

### 3. 使用 netcat 测试

```bash
# 检查 Socket 是否可连接
nc -U /var/run/tgo/tgo.sock
```

## 项目结构建议

一个完整的插件项目结构：

```
my-plugin/
├── plugin.json          # 插件配置文件
├── main.py              # 入口文件
├── handlers/            # 请求处理器
│   ├── __init__.py
│   ├── visitor_panel.py
│   └── chat_toolbar.py
├── services/            # 业务逻辑
│   └── order_service.py
├── tests/               # 测试文件
│   └── test_plugin.py
└── README.md            # 插件说明
```

## 下一步

- [通讯协议](/plugin/protocol) - 深入了解 JSON-RPC 协议细节
- [可插点详解](/plugin/extension-points) - 了解每个可插点的具体用法
- [模版规范](/plugin/templates) - 学习如何定义 UI 模版
- [完整示例](/plugin/examples) - 查看更多实际应用案例

