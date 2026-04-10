/**
 * AuthContext.jsx — Authentication State Management
 * ─────────────────────────────────────────────────
 * Provides authentication state and methods to the entire app.
 * Uses Supabase client for auth operations.
 */

import React, { createContext, useContext, useState, useEffect } from 'react';
import { supabase } from '../services/supabaseClient';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Fetch user profile from your backend or Supabase
  const fetchUserProfile = async (userId) => {
    try {
      // Option 1: Fetch from Supabase workers table
      const { data, error } = await supabase
        .from('workers')
        .select('*')
        .eq('id', userId)
        .single();
      
      if (error) {
        console.log('Profile fetch error (table may not exist):', error);
        // Return basic user info from auth user
        return null;
      }
      
      return data;
    } catch (error) {
      console.error('Error fetching profile:', error);
      return null;
    }
  };

  useEffect(() => {
    // Flag to prevent state updates after unmount
    let isMounted = true;
    let loadingTimeout; // Safety timeout to prevent infinite loading state

    // Check for existing session on mount
    const initializeAuth = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        
        if (isMounted) {
          setSession(session);
          setUser(session?.user ?? null);
          setIsAuthenticated(!!session);
          
          // Fetch user profile if session exists
          if (session?.user) {
            const profile = await fetchUserProfile(session.user.id);
            if (isMounted) {
              setUserProfile(profile);
            }
          }
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
        // Even on error, continue (allow access without profile)
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    // Safety timeout - ensure loading is cleared after 3 seconds
    loadingTimeout = setTimeout(() => {
      if (isMounted && loading) {
        console.warn('Auth loading timeout - clearing loading state');
        setLoading(false);
      }
    }, 3000);

    initializeAuth();

    // Listen for auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (_event, session) => {
        if (isMounted) {
          setSession(session);
          setUser(session?.user ?? null);
          setIsAuthenticated(!!session);
          
          // Fetch profile when auth state changes
          if (session?.user) {
            const profile = await fetchUserProfile(session.user.id);
            if (isMounted) {
              setUserProfile(profile);
            }
          } else {
            setUserProfile(null);
          }
          
          // Ensure loading is cleared when auth state changes
          if (isMounted) {
            setLoading(false);
          }
        }
      }
    );

    return () => {
      isMounted = false;
      if (subscription) {
        subscription.unsubscribe();
      }
      if (loadingTimeout) {
        clearTimeout(loadingTimeout);
      }
    };
  }, []);

  const login = async (email, password) => {
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) throw error;

      setUser(data.user);
      setSession(data.session);
      setIsAuthenticated(true);
      
      // Fetch user profile after successful login
      if (data.user) {
        const profile = await fetchUserProfile(data.user.id);
        setUserProfile(profile);
      }
      
      return { success: true, user: data.user };
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  const logout = async () => {
    try {
      // Sign out from Supabase
      const { error } = await supabase.auth.signOut();
      if (error) throw error;

      // Clear all local state
      setUser(null);
      setUserProfile(null);
      setSession(null);
      setIsAuthenticated(false);
      
      // Clear any local storage items related to auth
      localStorage.removeItem('sb-' + supabaseUrl + '-auth-token');
      
      return { success: true };
    } catch (error) {
      console.error('Logout error:', error);
      return { success: false, error: error.message };
    }
  };

  const updateProfile = async (updates) => {
    try {
      if (!user) throw new Error('No user logged in');
      
      const { data, error } = await supabase
        .from('workers')
        .update(updates)
        .eq('id', user.id)
        .select()
        .single();
      
      if (error) throw error;
      
      setUserProfile(data);
      return { success: true, profile: data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  const refreshSession = async () => {
    try {
      const { data, error } = await supabase.auth.refreshSession();
      if (error) throw error;

      setSession(data.session);
      setUser(data.user);
      setIsAuthenticated(!!data.session);
      
      if (data.user) {
        const profile = await fetchUserProfile(data.user.id);
        setUserProfile(profile);
      }
      
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  const getAccessToken = () => {
    return session?.access_token;
  };

  const value = {
    user,
    userProfile,
    session,
    isAuthenticated,
    loading,
    login,
    logout,
    refreshSession,
    updateProfile,
    getAccessToken,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
