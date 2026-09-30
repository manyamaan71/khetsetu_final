import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { Session, User } from '@supabase/supabase-js';
import { FarmerProfile, PreferredLanguage } from '../types';
import { supabase } from '../lib/supabase';

interface AuthContextValue {
  session: Session | null;
  user: User | null;
  profile: FarmerProfile | null;
  loading: boolean;
  isAuthenticated: boolean;
  signUpWithEmail: (fullName: string, email: string, password: string) => Promise<{
    error: { message: string } | null;
    requiresEmailConfirmation: boolean;
    profile: FarmerProfile | null;
  }>;
  signInWithEmail: (email: string, password: string) => Promise<{
    error: { message: string } | null;
    profile: FarmerProfile | null;
  }>;
  updateProfile: (updates: Partial<FarmerProfile>) => Promise<FarmerProfile | null>;
  refreshProfile: (userId?: string) => Promise<FarmerProfile | null>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function logAuthError(error: unknown) {
  if (import.meta.env.DEV) console.error('Supabase authentication error:', error);
}

function logProfileSaveError(error: unknown) {
  if (!import.meta.env.DEV) return;

  const details = error as { code?: string; message?: string; details?: string; hint?: string };
  console.error('Farmer profile save error:', error);
  console.error('Supabase error code:', details?.code);
  console.error('Supabase error message:', details?.message);
  console.error('Supabase error details:', details?.details);
  console.error('Supabase error hint:', details?.hint);
}

function optionalText(value: string | null | undefined): string | null {
  const trimmed = value?.trim() ?? '';
  return trimmed || null;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<FarmerProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const profileRequestId = useRef(0);

  const fetchProfile = useCallback(async (userId: string) => {
    const requestId = ++profileRequestId.current;
    if (!supabase || !userId) {
      setProfile(null);
      return null;
    }

    const { data, error } = await supabase
      .from('farmer_profiles')
      .select('*')
      .eq('user_id', userId)
      .maybeSingle();

    if (error) throw error;
    if (requestId !== profileRequestId.current) return null;

    const nextProfile = data as FarmerProfile | null;
    setProfile(nextProfile);
    return nextProfile;
  }, []);

  useEffect(() => {
    let active = true;
    const client = supabase;
    if (!client) {
      setLoading(false);
      return;
    }

    const loadSession = async () => {
      try {
        const { data, error } = await client.auth.getSession();
        if (error) throw error;
        if (!active) return;

        setSession(data.session);
        setUser(data.session?.user ?? null);
        if (data.session?.user.id) {
          await fetchProfile(data.session.user.id);
        } else {
          profileRequestId.current += 1;
          setProfile(null);
        }
      } catch (error) {
        logAuthError(error);
        setSession(null);
        setUser(null);
        setProfile(null);
      } finally {
        if (active) setLoading(false);
      }
    };

    const { data: authListener } = client.auth.onAuthStateChange((_event, nextSession) => {
      if (!active) return;
      setSession(nextSession);
      setUser(nextSession?.user ?? null);
      setProfile(null);
      if (!nextSession?.user.id) {
        profileRequestId.current += 1;
        setLoading(false);
        return;
      }

      setLoading(true);
      window.setTimeout(() => {
        void fetchProfile(nextSession.user.id)
          .catch((error: unknown) => {
            logProfileSaveError(error);
            setProfile(null);
          })
          .finally(() => { if (active) setLoading(false); });
      }, 0);
    });

    void loadSession();
    return () => {
      active = false;
      authListener.subscription.unsubscribe();
    };
  }, [fetchProfile]);

  const refreshProfile = useCallback(async (userId?: string) => {
    if (!supabase) return null;
    const { data: { user: currentUser }, error } = await supabase.auth.getUser();
    if (error) throw error;
    if (!currentUser || (userId && userId !== currentUser.id)) return null;
    return fetchProfile(currentUser.id);
  }, [fetchProfile]);

  const signUpWithEmail = useCallback(async (fullName: string, email: string, password: string) => {
    if (!supabase) {
      return { error: { message: 'Supabase is not configured.' }, requiresEmailConfirmation: false, profile: null };
    }

    const { data, error } = await supabase.auth.signUp({
      email: email.trim().toLowerCase(),
      password,
      options: { data: { full_name: fullName.trim() } },
    });
    if (error) {
      logAuthError(error);
      return { error: { message: error.message }, requiresEmailConfirmation: false, profile: null };
    }

    if (data.session && data.user) {
      setSession(data.session);
      setUser(data.user);
      const savedProfile = await fetchProfile(data.user.id);
      return { error: null, requiresEmailConfirmation: false, profile: savedProfile };
    }

    return { error: null, requiresEmailConfirmation: Boolean(data.user), profile: null };
  }, [fetchProfile]);

  const signInWithEmail = useCallback(async (email: string, password: string) => {
    if (!supabase) return { error: { message: 'Supabase is not configured.' }, profile: null };

    const { data, error } = await supabase.auth.signInWithPassword({
      email: email.trim().toLowerCase(),
      password,
    });
    if (error) {
      logAuthError(error);
      return { error: { message: error.message }, profile: null };
    }

    setSession(data.session);
    setUser(data.user);
    const savedProfile = await fetchProfile(data.user.id);
    return { error: null, profile: savedProfile };
  }, [fetchProfile]);

  const updateProfile = useCallback(async (updates: Partial<FarmerProfile>) => {
    if (!supabase) throw new Error('Supabase is not configured.');

    let userResult;
    try {
      userResult = await supabase.auth.getUser();
    } catch (error) {
      logProfileSaveError(error);
      throw error;
    }

    const { data: { user: currentUser }, error: userError } = userResult;
    if (userError || !currentUser) {
      logProfileSaveError(userError ?? new Error('No authenticated Supabase user.'));
      throw new Error('AUTH_REQUIRED');
    }

    const profileFields = {
      full_name: updates.full_name?.trim() ?? profile?.full_name ?? currentUser.user_metadata.full_name ?? '',
      preferred_language: updates.preferred_language ?? profile?.preferred_language ?? 'en',
      state: updates.state === undefined ? profile?.state ?? null : optionalText(updates.state),
      district: updates.district === undefined ? profile?.district ?? null : optionalText(updates.district),
      taluk: updates.taluk === undefined ? profile?.taluk ?? null : optionalText(updates.taluk),
      village: updates.village === undefined ? profile?.village ?? null : optionalText(updates.village),
      crops: updates.crops === undefined ? profile?.crops ?? [] : updates.crops ?? [],
      farm_size: updates.farm_size === undefined ? profile?.farm_size ?? null : updates.farm_size,
      onboarding_completed: updates.onboarding_completed ?? profile?.onboarding_completed ?? false,
    };

    try {
      const { data: existingProfile, error: lookupError } = await supabase
        .from('farmer_profiles')
        .select('user_id')
        .eq('user_id', currentUser.id)
        .maybeSingle();
      if (lookupError) throw lookupError;

      const result = existingProfile
        ? await supabase
            .from('farmer_profiles')
            .update(profileFields)
            .eq('user_id', currentUser.id)
            .select('*')
            .single()
        : await supabase
            .from('farmer_profiles')
            .insert({ user_id: currentUser.id, ...profileFields })
            .select('*')
            .single();
      if (result.error) throw result.error;

      const savedProfile = result.data as FarmerProfile;
      setProfile(savedProfile);
      return savedProfile;
    } catch (error) {
      logProfileSaveError(error);
      throw error;
    }
  }, [profile]);

  const signOut = useCallback(async () => {
    if (!supabase) return;
    const { error } = await supabase.auth.signOut();
    if (error) {
      logAuthError(error);
      throw error;
    }
    profileRequestId.current += 1;
    setSession(null);
    setUser(null);
    setProfile(null);
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    session,
    user,
    profile,
    loading,
    isAuthenticated: Boolean(session && user),
    signUpWithEmail,
    signInWithEmail,
    updateProfile,
    refreshProfile,
    signOut,
  }), [profile, session, user, loading, signUpWithEmail, signInWithEmail, updateProfile, refreshProfile, signOut]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
}

export function usePreferredLanguage(): PreferredLanguage {
  const { profile } = useAuth();
  return profile?.preferred_language ?? 'en';
}