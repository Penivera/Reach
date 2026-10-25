"use client";

import { useEffect } from "react";
import { updateFcmToken } from "@/lib/users";

export function FcmInitializer() {
  useEffect(() => {
    // Check if notifications are supported and permitted
    if (typeof window !== "undefined" && "Notification" in window) {
      if (Notification.permission === "granted") {
        registerToken();
      } else if (Notification.permission !== "denied") {
        Notification.requestPermission().then((permission) => {
          if (permission === "granted") {
            registerToken();
          }
        });
      }
    }
  }, []);

  const registerToken = async () => {
    try {
      // Note: You will initialize your Firebase SDK here and get the token
      // const token = await getToken(messaging, { vapidKey: 'YOUR_PUBLIC_VAPID_KEY' });
      // 
      // if (token) {
      //   await updateFcmToken({ fcm_token: token });
      // }
    } catch (error) {
      console.error("FCM registration failed:", error);
    }
  };

  return null; // Invisible component just handling background sync
}