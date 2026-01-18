import VideoFeed from './components/VideoFeed';
import ChatPanel from './components/ChatPanel';
import ConnectionPanel from './components/ConnectionPanel';
import { Ghost } from 'lucide-react';

function App() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col p-4 md:p-8 gap-6">
      {/* Header */}
      <header className="flex items-center gap-3">
        <div className="bg-blue-600 p-2 rounded-lg">
          <Ghost className="w-8 h-8 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">USBHidToolkit :: GUIAgent</h1>
          <p className="text-gray-400 text-sm">视觉闭环物理桌面智能体</p>
        </div>
      </header>

      <main className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 overflow-hidden">
        {/* Left Side: Video and Config */}
        <div className="lg:col-span-2 flex flex-col gap-6 overflow-y-auto pr-2">
          <VideoFeed />
          <ConnectionPanel />
          <div className="bg-gray-800/50 p-6 rounded-lg border border-gray-700/50">
            <h2 className="text-lg font-semibold mb-3 flex items-center gap-2 text-blue-400">
               运行指南
            </h2>
            <ul className="space-y-2 text-sm text-gray-400 list-disc list-inside">
              <li>通过摄像头对准目标电脑屏幕。</li>
              <li>确保 USBHID 设备已插入目标电脑且可以通过网络访问。</li>
              <li>Agent 会根据摄像头画面观察鼠标位置，并自动计算位移。</li>
              <li>如果移动不准确，Agent 会在下一轮中自动修正。</li>
            </ul>
          </div>
        </div>

        {/* Right Side: Chat and Logs */}
        <div className="h-[600px] lg:h-auto">
          <ChatPanel />
        </div>
      </main>
      
      <footer className="text-center text-gray-600 text-xs py-2">
        Powered by USBHidToolkit & Vision LLM
      </footer>
    </div>
  );
}

export default App;
