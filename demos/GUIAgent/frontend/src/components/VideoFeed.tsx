import React, { useEffect, useRef, useState } from 'react';
import { Camera, CameraOff } from 'lucide-react';

const VideoFeed: React.FC = () => {
    const [status, setStatus] = useState<'connecting' | 'connected' | 'error'>('connecting');
    const imgRef = useRef<HTMLImageElement>(null);
    const wsRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        const connect = () => {
            const ws = new WebSocket('ws://localhost:8000/ws/video');
            wsRef.current = ws;

            ws.onopen = () => setStatus('connected');
            ws.onmessage = (event) => {
                if (imgRef.current) {
                    imgRef.current.src = `data:image/jpeg;base64,${event.data}`;
                }
            };
            ws.onclose = () => {
                setStatus('connecting');
                setTimeout(connect, 3000); // 重连
            };
            ws.onerror = () => setStatus('error');
        };

        connect();
        return () => wsRef.current?.close();
    }, []);

    return (
        <div className="relative w-full aspect-video bg-gray-900 rounded-lg overflow-hidden border border-gray-700">
            {status === 'connected' ? (
                <img ref={imgRef} className="w-full h-full object-contain" alt="Video feed" />
            ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-500">
                    {status === 'connecting' ? (
                        <div className="animate-pulse flex flex-col items-center">
                            <Camera className="w-12 h-12 mb-2" />
                            <span>正在连接视频流...</span>
                        </div>
                    ) : (
                        <div className="text-red-500 flex flex-col items-center">
                            <CameraOff className="w-12 h-12 mb-2" />
                            <span>无法连接到后端</span>
                        </div>
                    )}
                </div>
            )}
            <div className="absolute top-2 left-2 bg-black/50 px-2 py-1 rounded text-xs text-white flex items-center gap-1">
                <div className={`w-2 h-2 rounded-full ${status === 'connected' ? 'bg-green-500' : 'bg-red-500'}`} />
                Live Camera
            </div>
        </div>
    );
};

export default VideoFeed;
