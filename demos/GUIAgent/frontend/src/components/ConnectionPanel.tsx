import React, { useState } from 'react';
import axios from 'axios';
import { Network, CheckCircle, XCircle } from 'lucide-react';

const ConnectionPanel: React.FC = () => {
    const [host, setHost] = useState('192.168.2.239');
    const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');

    const handleConnect = async () => {
        try {
            await axios.post('http://localhost:8000/connect', { host });
            setStatus('success');
        } catch (error) {
            setStatus('error');
        }
    };

    return (
        <div className="bg-gray-800 p-4 rounded-lg border border-gray-700 flex items-center justify-between">
            <div className="flex items-center gap-4">
                <Network className="w-6 h-6 text-gray-400" />
                <div>
                    <div className="text-xs text-gray-500 uppercase font-bold">USBHID Device Host</div>
                    <input
                        type="text"
                        value={host}
                        onChange={(e) => setHost(e.target.value)}
                        className="bg-transparent border-b border-gray-600 focus:border-blue-500 outline-none text-white text-lg font-mono"
                    />
                </div>
            </div>
            <button
                onClick={handleConnect}
                className={`px-4 py-2 rounded font-semibold transition-colors flex items-center gap-2 ${
                    status === 'success' ? 'bg-green-600' : 'bg-gray-700 hover:bg-gray-600'
                }`}
            >
                {status === 'success' ? <CheckCircle className="w-5 h-5" /> : null}
                {status === 'error' ? <XCircle className="w-5 h-5 text-red-500" /> : null}
                {status === 'success' ? '已连接' : '连接硬件'}
            </button>
        </div>
    );
};

export default ConnectionPanel;
