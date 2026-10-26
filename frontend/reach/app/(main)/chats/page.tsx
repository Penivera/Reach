'use client';

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { MagnifyingGlassIcon } from "@phosphor-icons/react";
// import { getMyConversations } from "@/lib/chat"; // Uncomment when integrating live API

// Temporary mock data to match the UI until the backend payload is enriched
const MOCK_CONVERSATIONS = [
  {
    id: 1,
    initials: "MB",
    name: "Mama Beatrice",
    time: "2m ago",
    status: "Escrow Active",
    statusColor: "text-teal-700 bg-teal-50",
    job: "5kg Rice",
    snippet: "He has arrived at your gate. Please sign off on the app when you verify...",
    unread: true,
    avatarColor: "bg-orange-100 text-orange-600",
  },
  {
    id: 2,
    initials: "AP",
    name: "Abiola (Plumber)",
    time: "2h ago",
    status: "Escrow Active",
    statusColor: "text-teal-700 bg-teal-50",
    job: "Pipe Leaks",
    snippet: "I will need to buy two additional PVC elbows from the market. I will send receipt...",
    unread: false,
    avatarColor: "bg-teal-100 text-teal-700",
  },
  {
    id: 3,
    initials: "KS",
    name: "Kemi (Stylist)",
    time: "Yesterday",
    status: "Completed",
    statusColor: "text-gray-500 bg-gray-100",
    job: "Hair Braiding",
    snippet: "Thank you for the tip! I look forward to braiding your hair next month...",
    unread: false,
    avatarColor: "bg-yellow-100 text-yellow-700",
  },
];

export default function ChatInbox() {
  const [searchQuery, setSearchQuery] = useState("");
  // const [conversations, setConversations] = useState([]);

  /* 
  useEffect(() => {
    getMyConversations().then(setConversations).catch(console.error);
  }, []);
  */

  const filteredChats = MOCK_CONVERSATIONS.filter((chat) =>
    chat.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    chat.job.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col pb-20">
      {/* Header */}
      <div className="bg-white px-4 pt-12 pb-4 shadow-sm sticky top-0 z-10">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Chats</h1>
          <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center text-sm font-semibold text-gray-600">
            UO
          </div>
        </div>

        {/* Search Bar */}
        <div className="relative">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search chats or listings..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-3 bg-white border border-gray-200 rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 transition-all"
          />
        </div>
      </div>

      {/* Chat List */}
      <div className="flex-1 px-4 pt-4 space-y-3">
        {filteredChats.map((chat) => (
          <Link href={`/chats/${chat.id}`} key={chat.id}>
            <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex gap-4 active:scale-[0.98] transition-transform">
              
              {/* Avatar */}
              <div className={`w-12 h-12 rounded-full shrink-0 flex items-center justify-center font-bold ${chat.avatarColor}`}>
                {chat.initials}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-start mb-1">
                  <h3 className="font-semibold text-gray-900 truncate">{chat.name}</h3>
                  <span className="text-xs text-gray-400 whitespace-nowrap ml-2">{chat.time}</span>
                </div>
                
                <div className="flex items-center gap-1.5 mb-1.5">
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${chat.statusColor}`}>
                    {chat.status}
                  </span>
                  <span className="text-xs text-gray-500 truncate">— {chat.job}</span>
                </div>

                <div className="flex justify-between items-center gap-2">
                  <p className="text-sm text-gray-600 truncate">{chat.snippet}</p>
                  {chat.unread && (
                    <div className="w-2 h-2 rounded-full bg-orange-500 shrink-0"></div>
                  )}
                </div>
              </div>

            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}