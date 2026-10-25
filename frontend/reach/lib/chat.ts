import { api } from "./api";

export interface Conversation {
  id: number;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  conversation_id: number;
  sender_id: number;
  content: string;
  is_read: boolean;
  created_at: string;
}

export async function getMyConversations(): Promise<Conversation[]> {
  return api<Conversation[]>("/conversations/");
}

export async function createConversation(userId: number): Promise<Conversation> {
  return api<Conversation>(`/conversations/${userId}`, { 
    method: "POST" 
  });
}

export async function getMessages(conversationId: number): Promise<Message[]> {
  return api<Message[]>(`/conversations/${conversationId}/messages`);
}

export async function sendMessage(conversationId: number, content: string): Promise<Message> {
  return api<Message>(`/conversations/${conversationId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export async function markAsRead(conversationId: number): Promise<string> {
  return api<string>(`/conversations/${conversationId}/messages/read`, { 
    method: "PATCH" 
  });
}