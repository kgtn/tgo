import { formatSystemMessageContent, type SystemMessageExtra } from '../../types/chat'
import { SystemMessageWrapper, SystemMessageInner } from './messageStyles'

export type SystemMessageProps = {
  content: string
  extra?: SystemMessageExtra[]
}

export default function SystemMessage({ content, extra }: SystemMessageProps) {
  const formattedContent = formatSystemMessageContent(content, extra)
  
  return (
    <SystemMessageWrapper>
      <SystemMessageInner>
        {formattedContent}
      </SystemMessageInner>
    </SystemMessageWrapper>
  )
}

