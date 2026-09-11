/**
 * BeAstar mobile — Auth context
 * ================================
 * Holds the signed-in user's id/verification/tier state so screens don't
 * each re-implement session loading. Backed by the userId persisted in
 * SecureStore via api/client.ts.
 */

import React, { createContext, useContext, useEffect, useState } from 'react';

import { getSavedUserId, saveSession, clearSession } from '../api/client';

interface AuthState {
  userId: string | null;
  isLoading: boolean;
  isVerified: boolean;
  setUserId: (id: string) => Promise<void>;
  setVerified: (verified: boolean) => void;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [userId, setUserIdState] = useState<string | null>(null);
  const [isVerified, setIsVerified] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const saved = await getSavedUserId();
      setUserIdState(saved);
      setIsLoading(false);
    })();
  }, []);

  const setUserId = async (id: string) => {
    await saveSession(id);
    setUserIdState(id);
  };

  const signOut = async () => {
    await clearSession();
    setUserIdState(null);
    setIsVerified(false);
  };

  return (
    <AuthContext.Provider
      value={{ userId, isLoading, isVerified, setUserId, setVerified: setIsVerified, signOut }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
