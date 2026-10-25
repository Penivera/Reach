'use client';

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { 
  ArrowLeftIcon, 
  PhoneIcon, 
  LockIcon, 
  PaperclipIcon, 
  MicrophoneIcon, 
  PaperPlaneRightIcon
} from "@phosphor-icons/react";
// import { getMessages, sendMessage } from "@/lib/chat";

// Mock data reflecting the UI design
const MOCK_MESSAGES = [
  { id: 1, type: "system", content: "Escrow Deposit Confirmed: ₦4,500 locked in Reach Trust Account. Provider has been notified to proceed." },
  { id: 2, type: "outbound", content: "Hello Mama Beatrice, is the rice still coming today?", time: "10:14 AM" },
  { id: 3, type: "inbound", content: "Yes! We are packing it now in the local bag. My son is loading it onto the motorcycle.", time: "10:16 AM" },
  { id: 4, type: "inbound", content: "Here is the picture of the bag before he takes off.", time: "10:17 AM" },
  { id: 5, type: "inbound", content: "[ 5kg Rice Sack Photo ]", isImage: true, time: "10:17 AM" },
];

export default function ChatScreen() {
  const [messages, setMessages] = useState(MOCK_MESSAGES);
  const [inputText, setInputText] = useState("");

  /* 
  // Polling setup for when you wire the real endpoints
  useEffect(() => {
    const interval = setInterval(() => {
      getMessages(conversationId).then(setMessages).catch(console.error);
    }, 3000);
    return () => clearInterval(interval);
  }, []);
  */

  const handleSend = async () => {
    if (!inputText.trim()) return;
    
    // Optimistic UI update
    const newMessage = {
      id: Date.now(),
      type: "outbound",
      content: inputText,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setMessages((prev) => [...prev, newMessage]);
    setInputText("");

    // await sendMessage(conversationId, inputText);
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white px-4 py-4 shadow-sm flex items-center justify-between z-10">
        <div className="flex items-center gap-3">
          <Link href="/chat">
            <ArrowLeftIcon className="w-6 h-6 text-gray-700" />
          </Link>
          <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center text-sm font-semibold text-orange-600">
            MB
          </div>
          <div>
            <h2 className="font-bold text-gray-900 leading-tight">Mama Beatrice</h2>
            <p className="text-xs text-gray-500">Active Job: 5kg Local Rice</p>
          </div>
        </div>
        <button className="p-2">
          <PhoneIcon className="w-5 h-5 text-gray-600" />
        </button>
      </div>

      {/* Escrow Banner (Phase 5 Integration Point) */}
      <div className="bg-teal-50 px-4 py-3 border-b border-teal-100">
        <div className="flex justify-between items-center mb-1">
          <div className="flex items-center gap-1.5 text-teal-700 font-semibold text-sm">
            <LockIcon className="w-4 h-4" /> Escrow Active
          </div>
          <span className="font-bold text-teal-700">₦4,500</span>
        </div>
        <p className="text-xs text-teal-800/70 mb-3">
          Funds held securely. Release payment ONLY after you receive and verify the item.
        </p>
        <div className="flex gap-3">
          <button className="flex-1 bg-teal-600 text-white text-sm font-semibold py-2 rounded-lg active:bg-teal-700 transition-colors">
            Release Escrow
          </button>
          <button className="flex-1 bg-white text-red-500 text-sm font-semibold py-2 rounded-lg border border-red-200 active:bg-red-50 transition-colors">
            Report Issue
          </button>
        </div>
      </div>

      {/* Message Feed */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => {
          if (msg.type === "system") {
            return (
              <div key={msg.id} className="border border-teal-300 border-dashed bg-teal-50/50 rounded-lg p-3 text-xs text-teal-700 text-center flex items-center justify-center gap-2 mx-4">
                <LockIcon className="w-3 h-3 flex-shrink-0" />
                <span>{msg.content}</span>
              </div>
            );
          }

          const isOutbound = msg.type === "outbound";
          return (
            <div key={msg.id} className={`flex flex-col ${isOutbound ? "items-end" : "items-start"}`}>
              <div 
                className={`max-w-[75%] rounded-2xl p-3 text-sm ${
                  msg.isImage 
                    ? "bg-gray-100 text-gray-500 min-h-[120px] min-w-[120px] flex items-center justify-center border border-gray-200" 
                    : isOutbound 
                      ? "bg-orange-500 text-white rounded-br-sm" 
                      : "bg-white text-gray-800 border border-gray-100 rounded-bl-sm shadow-sm"
                }`}
              >
                {msg.content}
              </div>
              <span className="text-[10px] text-gray-400 mt-1">{msg.time}</span>
            </div>
          );
        })}
      </div>

      {/* Input Area */}
      <div className="bg-white p-3 border-t border-gray-100 pb-safe">
        <div className="flex items-center gap-2">
          <button className="p-2 text-gray-400 hover:text-gray-600">
            <PaperclipIcon className="w-5 h-5" />
          </button>
          <div className="flex-1 bg-gray-100 rounded-full flex items-center px-4 py-2">
            <input 
              type="text" 
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Type a message..." 
              className="bg-transparent flex-1 focus:outline-none text-sm text-gray-800"
            />
            <button className="p-1 text-gray-400 ml-2">
              <MicrophoneIcon className="w-5 h-5" />
            </button>
          </div>
          <button 
            onClick={handleSend}
            className="w-10 h-10 bg-orange-500 rounded-full flex items-center justify-center flex-shrink-0 active:scale-95 transition-transform"
          >
            <PaperPlaneRightIcon className="w-5 h-5 text-white" />
          </button>
        </div>
      </div>
    </div>
  );
}