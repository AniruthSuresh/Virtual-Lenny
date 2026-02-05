'use client';

import { useState, useRef, useEffect } from 'react';

interface Message {
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

export default function Terminal() {
  const [messages, setMessages] = useState<Message[]>([
    {
      type: 'system',
      content: '🚀 Connected to Virtual Lenny. Ask me anything about product management!',
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const currentAssistantMessageRef = useRef('');

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Connect to WebSocket on mount
  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    const wsUrl = process.env.NEXT_PUBLIC_WEBSOCKET_URL;
    
    if (!wsUrl) {
      addSystemMessage('❌ WebSocket URL not configured');
      return;
    }

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setIsConnected(true);
        addSystemMessage('✅ Connected to backend');
      };

      ws.onclose = () => {
        setIsConnected(false);
        addSystemMessage('⚠️ Disconnected from backend');
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        addSystemMessage('❌ Connection error');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'chunk') {
            // Accumulate streaming chunks
            currentAssistantMessageRef.current += data.content;
            
            // Update the last message (assistant's response)
            setMessages((prev) => {
              const newMessages = [...prev];
              const lastMessage = newMessages[newMessages.length - 1];
              
              if (lastMessage?.type === 'assistant') {
                // Update existing assistant message
                lastMessage.content = currentAssistantMessageRef.current;
              } else {
                // Create new assistant message
                newMessages.push({
                  type: 'assistant',
                  content: currentAssistantMessageRef.current,
                  timestamp: new Date()
                });
              }
              
              return newMessages;
            });
          } else if (data.type === 'done') {
            // Streaming complete
            setIsStreaming(false);
            currentAssistantMessageRef.current = '';
          } else if (data.type === 'error') {
            addSystemMessage(`❌ Error: ${data.message}`);
            setIsStreaming(false);
            currentAssistantMessageRef.current = '';
          }
        } catch (error) {
          console.error('Failed to parse message:', error);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Failed to connect:', error);
      addSystemMessage('❌ Failed to connect');
    }
  };

  const addSystemMessage = (content: string) => {
    setMessages((prev) => [
      ...prev,
      { type: 'system', content, timestamp: new Date() }
    ]);
  };

  const sendMessage = () => {
    if (!input.trim() || !isConnected || isStreaming) return;

    // Add user message
    setMessages((prev) => [
      ...prev,
      { type: 'user', content: input, timestamp: new Date() }
    ]);

    // Send to WebSocket
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ message: input }));
      setIsStreaming(true);
      currentAssistantMessageRef.current = '';
    }

    setInput('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="bg-gray-900 rounded-lg shadow-2xl border border-gray-800 overflow-hidden">
      {/* Terminal Header */}
      <div className="bg-gray-800 px-4 py-3 flex items-center justify-between border-b border-gray-700">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
          </div>
          <span className="ml-4 text-sm text-gray-400 font-mono">
            virtual-lenny-terminal
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
          <span className="text-xs text-gray-400">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Messages Area */}
      <div className="h-[500px] overflow-y-auto p-4 space-y-4 font-mono text-sm terminal-scrollbar">
        {messages.map((msg, idx) => (
          <div key={idx} className="animate-fade-in">
            {msg.type === 'user' && (
              <div className="flex gap-2">
                <span className="text-green-400 flex-shrink-0">❯</span>
                <span className="text-white break-words">{msg.content}</span>
              </div>
            )}
            
            {msg.type === 'assistant' && (
              <div className="flex gap-2">
                <span className="text-blue-400 flex-shrink-0">🤖</span>
                <div className="text-gray-300 whitespace-pre-wrap flex-1 break-words">
                  {msg.content}
                  {isStreaming && idx === messages.length - 1 && (
                    <span className="cursor-blink ml-1">▊</span>
                  )}
                </div>
              </div>
            )}
            
            {msg.type === 'system' && (
              <div className="text-yellow-400 italic">
                {msg.content}
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="bg-gray-800 border-t border-gray-700 p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={
              isConnected 
                ? "Ask me about product management..." 
                : "Connecting..."
            }
            disabled={!isConnected || isStreaming}
            className="flex-1 bg-gray-900 text-white px-4 py-2 rounded border border-gray-700 focus:border-blue-500 focus:outline-none font-mono disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <button
            onClick={sendMessage}
            disabled={!isConnected || isStreaming || !input.trim()}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white rounded font-medium transition-colors"
          >
            {isStreaming ? 'Thinking...' : 'Send'}
          </button>
        </div>
        <div className="mt-2 text-xs text-gray-500 text-center">
          Press Enter to send • Shift+Enter for new line
        </div>
      </div>
    </div>
  );
}