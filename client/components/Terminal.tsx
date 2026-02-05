'use client';

import { useState, useRef, useEffect } from 'react';

interface Message {
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  evaluation?: RAGScore;
}

interface RAGScore {
  overall: number;
  breakdown: {
    retrieval: number;
    groundedness: number;
    coherence: number;
    attribution: number;
  };
  grade: string;
  details: {
    avg_similarity: number;
    top_similarity: number;
    source_diversity: number;
  };
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
  const currentEvaluationRef = useRef<RAGScore | null>(null);

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
          } else if (data.type === 'evaluation') {
            // Store evaluation data
            currentEvaluationRef.current = data.score;
            
            // Update the last assistant message with evaluation
            setMessages((prev) => {
              const newMessages = [...prev];
              const lastMessage = newMessages[newMessages.length - 1];
              
              if (lastMessage?.type === 'assistant') {
                lastMessage.evaluation = data.score;
              }
              
              return newMessages;
            });
          } else if (data.type === 'done') {
            // Streaming complete
            setIsStreaming(false);
            currentAssistantMessageRef.current = '';
            currentEvaluationRef.current = null;
          } else if (data.type === 'error') {
            addSystemMessage(`❌ Error: ${data.message}`);
            setIsStreaming(false);
            currentAssistantMessageRef.current = '';
            currentEvaluationRef.current = null;
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
      currentEvaluationRef.current = null;
    }

    setInput('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const getGradeColor = (grade: string) => {
    switch (grade) {
      case 'A': return 'text-green-400';
      case 'B': return 'text-blue-400';
      case 'C': return 'text-yellow-400';
      case 'D': return 'text-orange-400';
      case 'F': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'bg-green-500';
    if (score >= 70) return 'bg-blue-500';
    if (score >= 60) return 'bg-yellow-500';
    if (score >= 50) return 'bg-orange-500';
    return 'bg-red-500';
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
              <div className="space-y-3">
                <div className="flex gap-2">
                  <span className="text-blue-400 flex-shrink-0">🤖</span>
                  <div className="text-gray-300 whitespace-pre-wrap flex-1 break-words">
                    {msg.content}
                    {isStreaming && idx === messages.length - 1 && (
                      <span className="cursor-blink ml-1">▊</span>
                    )}
                  </div>
                </div>
                
                {/* RAG Quality Evaluation */}
                {msg.evaluation && (
                  <div className="ml-6 mt-3 p-3 bg-gray-800 border border-gray-700 rounded">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-gray-400 uppercase tracking-wide">
                        Response Quality
                      </span>
                      <div className="flex items-center gap-2">
                        <span className={`text-2xl font-bold ${getGradeColor(msg.evaluation.grade)}`}>
                          {msg.evaluation.grade}
                        </span>
                        <span className="text-gray-400 text-sm">
                          {msg.evaluation.overall}%
                        </span>
                      </div>
                    </div>
                    
                    {/* Score Breakdown */}
                    <div className="space-y-2 mt-3">
                      {Object.entries(msg.evaluation.breakdown).map(([key, value]) => (
                        <div key={key} className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className="text-gray-400 capitalize">{key}</span>
                            <span className="text-gray-300">{value}%</span>
                          </div>
                          <div className="w-full bg-gray-700 rounded-full h-1.5">
                            <div
                              className={`h-1.5 rounded-full transition-all duration-500 ${getScoreColor(value)}`}
                              style={{ width: `${value}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                    
                    {/* Details */}
                    <div className="mt-3 pt-3 border-t border-gray-700 grid grid-cols-3 gap-2 text-xs">
                      <div>
                        <div className="text-gray-500">Avg Similarity</div>
                        <div className="text-gray-300 font-medium">
                          {(msg.evaluation.details.avg_similarity * 100).toFixed(1)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-500">Top Match</div>
                        <div className="text-gray-300 font-medium">
                          {(msg.evaluation.details.top_similarity * 100).toFixed(1)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-500">Diversity</div>
                        <div className="text-gray-300 font-medium">
                          {(msg.evaluation.details.source_diversity * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>
                  </div>
                )}
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
          Press Enter to send 
        </div>
      </div>
    </div>
  );
}