import React, { useState, useEffect, useRef } from 'react';
import { Send, Loader2, Cpu, MousePointer2, Keyboard, CheckCircle2 } from 'lucide-react';

interface LogEntry {
  thought: string;
  action: string;
  params: any;
  timestamp: string;
  step?: number;
}

const ChatPanel: React.FC = () => {
    const [goal, setGoal] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [logs, setLogs] = useState<LogEntry[]>([]);
    const wsRef = useRef<WebSocket | null>(null);

    // 初始化 WebSocket 连向 Agent 控制通道
    useEffect(() => {
        const ws = new WebSocket('ws://localhost:8000/ws/agent');
        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.status === 'step') {
                const stepData = msg.data;
                setLogs(prev => [{
                    thought: stepData.thought,
                    action: stepData.action || (stepData.status === 'finished' ? 'finish' : 'unknown'),
                    params: stepData.params || {},
                    timestamp: new Date().toLocaleTimeString(),
                    step: msg.step
                }, ...prev]);
            } else if (msg.status === 'completed') {
                setIsLoading(false);
            } else if (msg.status === 'error') {
                console.error("Agent WS error:", msg.message);
                setIsLoading(false);
            }
        };
        wsRef.current = ws;
        return () => ws.close();
    }, []);

    const handleSend = () => {
        if (!goal.trim() || !wsRef.current) return;
        
        setIsLoading(true);
        // 清理旧任务日志或标记新任务开始
        wsRef.current.send(JSON.stringify({ goal, max_steps: 10 }));
    };

    return (
        <div className="flex flex-col h-full bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
            {/* 1. 顶栏 */}
            <div className="p-3 border-b border-gray-700 bg-gray-900 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Cpu className="w-5 h-5 text-blue-400" />
                    <span className="font-semibold text-gray-200">GUIAgent 控制台</span>
                </div>
                {isLoading && (
                    <div className="flex items-center gap-2 text-blue-400 text-xs animate-pulse">
                        <Loader2 className="w-3 h-3 animate-spin" />
                        <span>自动运行中...</span>
                    </div>
                )}
            </div>

            {/* 2. 输入区移至顶部 */}
            <div className="p-4 bg-gray-900/30 border-b border-gray-700">
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={goal}
                        onChange={(e) => setGoal(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                        placeholder="输入您的目标并开始自动执行..."
                        className="flex-1 bg-gray-800 border border-gray-600 rounded px-3 py-2 text-white focus:outline-none focus:border-blue-500 text-sm"
                        disabled={isLoading}
                    />
                    <button
                        onClick={handleSend}
                        disabled={isLoading}
                        className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 text-white px-4 py-2 rounded transition-colors flex items-center gap-2"
                    >
                        {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                        <span className="text-sm font-medium">执行</span>
                    </button>
                </div>
            </div>

            {/* 3. 日志区 (固定高度/滚动, 最新在顶) */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 text-sm scrollbar-thin scrollbar-thumb-gray-600">
                {logs.length === 0 && !isLoading && (
                    <div className="text-gray-500 text-center mt-10">等待任务启动...</div>
                )}
                
                {logs.map((log, i) => (
                    <div key={i} className={`bg-gray-900 rounded p-3 border-l-4 ${log.action === 'finish' ? 'border-green-500' : 'border-blue-500 shadow-sm'}`}>
                        <div className="flex justify-between items-start mb-2">
                            <span className="text-[10px] bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded uppercase tracking-wider">
                                {log.step ? `Step ${log.step}` : 'Last Action'}
                            </span>
                            <span className="text-gray-500 text-[10px]">{log.timestamp}</span>
                        </div>
                        
                        <div className="text-gray-300 leading-relaxed mb-3">
                            <strong className="text-blue-400">思考:</strong> {log.thought}
                        </div>

                        <div className={`flex items-center gap-2 p-2 rounded text-xs ${log.action === 'finish' ? 'bg-green-900/20 text-green-400' : 'bg-blue-900/10 text-blue-300'}`}>
                            {log.action === 'move' && <MousePointer2 className="w-3.5 h-3.5" />}
                            {log.action === 'type' && <Keyboard className="w-3.5 h-3.5" />}
                            {log.action === 'finish' && <CheckCircle2 className="w-3.5 h-3.5" />}
                            <span className="font-mono">
                                {log.action.toUpperCase()} {log.action !== 'finish' && JSON.stringify(log.params)}
                            </span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default ChatPanel;
