import React, { useState, useEffect } from 'react';
import { Sprout, ShoppingBag, MessageSquare, ShieldCheck, Database, Layers } from 'lucide-react';
import ChatWindow from './components/ChatWindow';
import MandiPriceWidget from './components/MandiPriceWidget';
import { checkHealth } from './api/client';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' or 'prices' for mobile toggle
  const [isBackendOnline, setIsBackendOnline] = useState(true);

  useEffect(() => {
    const verifyBackend = async () => {
      const online = await checkHealth();
      setIsBackendOnline(online);
    };
    verifyBackend();
    const interval = setInterval(verifyBackend, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-screen h-full flex flex-col bg-[#051a10] text-slate-100 font-['Inter',sans-serif] overflow-hidden">
      {/* Top Navigation Header (shrink-0) */}
      <header className="shrink-0 z-50 bg-emerald-950/80 backdrop-blur-md border-b border-emerald-800/40 px-4 md:px-8 py-3.5 shadow-xl">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          {/* Brand Logo & Name */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-emerald-400 to-emerald-700 p-0.5 shadow-lg shadow-emerald-600/30">
              <div className="w-full h-full bg-emerald-950 rounded-[14px] flex items-center justify-center text-emerald-400">
                <Sprout className="w-6 h-6" />
              </div>
            </div>
            <div>
              <h1 className="font-bold text-lg md:text-xl text-white tracking-tight flex items-center gap-2">
                KrishiRAG
                <span className="text-[10px] font-semibold bg-emerald-900/80 text-emerald-300 border border-emerald-700/50 px-2 py-0.5 rounded-full uppercase tracking-wider">
                  v1.0
                </span>
              </h1>
              <p className="text-xs text-emerald-400/80 font-medium">Farmer Query Advisory & Live Mandi Intelligence</p>
            </div>
          </div>

        </div>
      </header>

      {/* Mobile Tab Switcher (shrink-0) */}
      <div className="shrink-0 lg:hidden bg-emerald-950/60 p-2 border-b border-emerald-900/40 flex justify-center gap-2">
        <button
          onClick={() => setActiveTab('chat')}
          className={`flex-1 py-2 px-4 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
            activeTab === 'chat'
              ? 'bg-emerald-600 text-white shadow-md'
              : 'bg-emerald-950/40 text-emerald-300 hover:bg-emerald-900/40'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          Advisory Chat
        </button>
        <button
          onClick={() => setActiveTab('prices')}
          className={`flex-1 py-2 px-4 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
            activeTab === 'prices'
              ? 'bg-emerald-600 text-white shadow-md'
              : 'bg-emerald-950/40 text-emerald-300 hover:bg-emerald-900/40'
          }`}
        >
          <ShoppingBag className="w-4 h-4" />
          Live Mandi Rates
        </button>
      </div>

      {/* Main Content Area (flex-1 min-h-0 overflow-hidden) */}
      <main className="flex-1 min-h-0 h-full max-w-7xl w-full mx-auto p-3 sm:p-4 md:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 overflow-hidden">
        {/* Chat Window Column */}
        <div className={`lg:col-span-7 xl:col-span-8 h-full min-h-0 flex flex-col overflow-hidden ${activeTab === 'chat' ? 'flex' : 'hidden lg:flex'}`}>
          <ChatWindow />
        </div>

        {/* Mandi Price Sidebar Widget Column */}
        <div className={`lg:col-span-5 xl:col-span-4 h-full min-h-0 flex flex-col overflow-hidden ${activeTab === 'prices' ? 'flex' : 'hidden lg:flex'}`}>
          <MandiPriceWidget />
        </div>
      </main>
    </div>
  );
}
