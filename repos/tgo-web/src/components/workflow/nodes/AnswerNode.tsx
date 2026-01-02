/**
 * Answer Node Component
 * Response/Output point of a workflow
 */

import React, { memo } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { MessageSquare } from 'lucide-react';
import type { AnswerNodeData } from '@/types/workflow';
import NodeExecutionOverlay from '../overlays/NodeExecutionOverlay';

const AnswerNode: React.FC<NodeProps<AnswerNodeData>> = ({ id, data, selected }) => {
  const getOutputSummary = () => {
    switch (data.output_type) {
      case 'variable':
        return data.output_variable ? `→ ${data.output_variable}` : '未配置变量';
      case 'template':
        return '→ 文本模板';
      case 'structured':
        return `→ ${data.output_structure?.length || 0} 个字段`;
      default:
        return 'Workflow Output';
    }
  };

  return (
    <div
      className={`
        px-5 py-4 rounded-2xl bg-white dark:bg-gray-800 shadow-sm border
        flex items-center gap-4 min-w-[200px] transition-all duration-200 relative
        ${selected 
          ? 'border-blue-500 ring-4 ring-blue-500/10' 
          : 'border-gray-100 dark:border-gray-700 hover:shadow-md'
        }
      `}
    >
      <NodeExecutionOverlay nodeId={id} label={data.label || '回复'} />
      <div className="absolute left-0 top-4 bottom-4 w-1 bg-blue-500 rounded-r-full" />

      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-blue-500 !border-2 !border-white dark:!border-gray-800 !shadow-sm"
      />
      
      <div className="p-2.5 rounded-xl bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400">
        <MessageSquare className="w-6 h-6" />
      </div>
      
      <div className="min-w-0">
        <div className="text-sm font-bold text-gray-900 dark:text-gray-100">
          {data.label || '回复'}
        </div>
        <div className="text-[10px] text-blue-500 font-bold uppercase tracking-wider mt-0.5 truncate max-w-[120px]">
          {getOutputSummary()}
        </div>
      </div>
    </div>
  );
};

export default memo(AnswerNode);

