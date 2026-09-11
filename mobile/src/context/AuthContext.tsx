/**
 * BeAstar mobile — Auth context
 * ================================
 * Holds the signed-in user's id/verification/tier state so screens don't
 * each re-implement session loading. Backed by the userId persisted in
 * SecureStore via api/client.ts.
 */

import React, { createContext, useContext, useEffect, useState } from 'react';
import * as SecureStore from 'expo-secure-store';

import { getSavedUserId, saveSession, clearSession } from '../api/client';

// SecureStore keys
const USER_ID_KEY = 'beastar_user_id';
const VERIFIED_KEY = 'beastar_verified';

interface AuthState {
  userId: string | null;
  isLoading: boolean;
  isVerified: boolean;
  setUserId: (id: string) => Promise<void>;
  setVerified: (verified: boolean) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [userId, setUserIdState] = useState<string | null>(null);
  const [isVerified, setIsVerified] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const savedUserId = await getSavedUserId();
      const savedVerified = await SecureStore.getItemAsync(VERIFIED_KEY);
      
      setUserIdState(savedUserId);
      setIsVerified(savedVerified === 'true');
      setIsLoading(false);
    })();
  }, []);

  const setUserId = async (id: string) => {
    await saveSession(id);
    setUserIdState(id);
  };

  const setVerified = async (verified: boolean) => {
    setIsVerified(verified);
    if (verified) {
      await SecureStore.setItemAsync(VERIFIED_KEY, 'true');
    } else {
      await SecureStore.deleteItemAsync(VERIFIED_KEY);
    }
  };

  const signOut = async () => {
    await clearSession();
    await SecureStore.deleteItemAsync(VERIFIED_KEY);
    setUserIdState(null);
    setIsVerified(false);
  };

  return (
    <AuthContext.Provider
      value={{ userId, isLoading, isVerified, setUserId, setVerified, signOut }}
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
