import React from 'react';
import type { PayloadSystem, SystemMessageExtraItem } from '@/types';

interface SystemMessageProps {
  payload: PayloadSystem;
}

/**
 * 解析系统消息模板，将 {0}, {1} 等占位符替换为 extra 中的对应名称
 * @param template 模板字符串，如 "您已接入人工客服，客服{0} 将为您服务"
 * @param extra 额外信息数组，如 [{ uid: "xxx", name: "Administrator" }]
 * @returns 解析后的内容片段数组
 */
function parseSystemMessageContent(
  template: string,
  extra?: SystemMessageExtraItem[]
): React.ReactNode[] {
  if (!extra || extra.length === 0) {
    return [template];
  }

  const result: React.ReactNode[] = [];
  // 匹配 {0}, {1}, {2} 等占位符
  const regex = /\{(\d+)\}/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(template)) !== null) {
    // 添加占位符之前的普通文本
    if (match.index > lastIndex) {
      result.push(template.slice(lastIndex, match.index));
    }

    // 获取占位符索引
    const placeholderIndex = parseInt(match[1], 10);
    const extraItem = extra[placeholderIndex];

    if (extraItem?.name) {
      // 用高亮样式包裹名称
      result.push(
        <span
          key={`extra-${placeholderIndex}`}
          className="font-medium text-gray-600 dark:text-gray-300"
        >
          {extraItem.name}
        </span>
      );
    } else {
      // 如果没有找到对应的 extra，保留原占位符
      result.push(match[0]);
    }

    lastIndex = regex.lastIndex;
  }

  // 添加最后一段普通文本
  if (lastIndex < template.length) {
    result.push(template.slice(lastIndex));
  }

  return result;
}

/**
 * 系统消息组件
 * 显示类似微信的 "xxx加入群聊" 风格的系统通知
 */
const SystemMessage: React.FC<SystemMessageProps> = ({ payload }) => {
  const content = parseSystemMessageContent(payload.content, payload.extra);

  return (
    <div className="flex justify-center my-3">
      <div className="inline-flex items-center px-3 py-1.5 rounded-full bg-gray-100/80 dark:bg-gray-700/50 text-xs text-gray-500 dark:text-gray-400 max-w-[80%]">
        <span className="text-center leading-relaxed">
          {content}
        </span>
      </div>
    </div>
  );
};

export default SystemMessage;
