'use client'

import ReactMarkdown from 'react-markdown'
import { Message } from '@/app/chat/page'
import { Bot, User, Download } from 'lucide-react'

interface MessageBubbleProps {
  message: Message
}

function getStoredToken(): string {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('nanobot_token') || ''
  }
  return ''
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const isFile = message.type === 'file'

  return (
    <div
      className={`flex items-start gap-3 message-enter ${
        isUser ? 'flex-row-reverse' : ''
      }`}
    >
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
          isUser
            ? 'bg-nano-accent'
            : 'bg-nano-accent/20'
        }`}
      >
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-nano-accent" />
        )}
      </div>

      {/* Message bubble */}
      <div
        className={`max-w-[70%] px-4 py-3 rounded-2xl ${
          isUser
            ? 'bg-nano-accent text-white rounded-tr-none'
            : 'bg-nano-card border border-nano-border text-nano-text rounded-tl-none'
        }`}
      >
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="markdown-content text-sm">
            <ReactMarkdown>{message.content}</ReactMarkdown>
            
            {/* File download button */}
            {isFile && message.download_url && message.filename && (
              <a
                href={`http://localhost:8765${message.download_url}?token=${getStoredToken()}`}
                download={message.filename}
                className="mt-3 flex items-center gap-2 w-full px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors text-sm font-medium"
              >
                <Download className="w-4 h-4" />
                Download {message.filename}
              </a>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
