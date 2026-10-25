// "use client";

// import React, { createContext, useContext, useEffect, useState } from "react";
// import { getMyProfile } from "@/lib/users";
// import { User } from "@/types";
// import { ApiError } from "@/lib/api";
// import { logout as logoutRequest } from "@/lib/auth";

// type AuthContextType = {
//   user: User | null;
//   setUser: React.Dispatch<React.SetStateAction<User | null>>;
//   loading: boolean;
//   refresh: () => Promise<void>;
//   logout: () => Promise<void>;
// };

// const AuthContext = createContext<AuthContextType | undefined>(undefined);

// export function AuthProvider({ children }: { children: React.ReactNode }) {
//   const [user, setUser] = useState<User | null>(null);
//   const [loading, setLoading] = useState(true);

//   const refresh = async () => {
//     setLoading(true);
//     try {
//       const me = await getMyProfile();
//       setUser(me);
//     } catch (err) {
//       if (err instanceof ApiError && err.status === 401) {
//         setUser(null);
//         return;
//       }
//       throw err;
//     } finally {
//       setLoading(false);
//     }
//   };

//   useEffect(() => {
//     refresh();
//   }, []);

//   const logout = async () => {
//     try {
//       await logoutRequest();
//     } finally {
//       setUser(null);
//     }
//   };

//   return (
//     <AuthContext.Provider value={{ user, setUser, loading, refresh, logout }}>
//       {children}
//     </AuthContext.Provider>
//   );
// }

// export function useAuth() {
//   const ctx = useContext(AuthContext);
//   if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
//   return ctx;
// }

// export default AuthContext;


"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { getMyProfile } from "@/lib/users";
import { User } from "@/types";
import { ApiError } from "@/lib/api";
// Import the raw login request alongside logout
import { login as loginRequest, logout as logoutRequest } from "@/lib/auth"; 

type AuthContextType = {
  user: User | null;
  setUser: React.Dispatch<React.SetStateAction<User | null>>;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>; // Added login to types
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    setLoading(true);
    try {
      const me = await getMyProfile();
      setUser(me);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setUser(null);
        return;
      }
      throw err;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  // NEW: The login wrapper that hits the API, then updates global state
  const login = async (username: string, password: string) => {
    console.log("[AuthContext] 1. Initiating login...");
    const response = await loginRequest(username, password) as { message?: string };
    console.log("[AuthContext] 2. Backend response:", response);
    
    if (response && response.message === "Logged in") {
      console.log("[AuthContext] 3. Success! Setting dummy cookies for Next.js middleware...");
      // Setting both common names to ensure middleware catches it
      document.cookie = `token=httponly_session_active; path=/; max-age=604800; SameSite=Lax`;
      document.cookie = `access_token=httponly_session_active; path=/; max-age=604800; SameSite=Lax`;
    } else {
      console.warn("[AuthContext] 3. WARNING: Response did not match {message: 'Logged in'}", response);
    }

    console.log("[AuthContext] 4. Fetching user profile via refresh()...");
    await refresh(); 
    console.log("[AuthContext] 5. Login context flow complete!");
  };

  const logout = async () => {
    try {
      await logoutRequest();
    } finally {
      setUser(null);
    }
  };

  return (
    // Expose login to the provider
    <AuthContext.Provider value={{ user, setUser, loading, login, refresh, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}

export default AuthContext;