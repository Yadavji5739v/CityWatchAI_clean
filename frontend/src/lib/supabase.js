import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const supabase = supabaseUrl && supabaseAnonKey
  ? createClient(supabaseUrl, supabaseAnonKey)
  : null;

export async function signInWithSupabase(email, password) {
  if (!supabase) {
    throw new Error('Supabase is not configured. Add VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY to your frontend env file.');
  }

  const { data, error } = await supabase.auth.signInWithPassword({ email, password });

  if (error) {
    throw error;
  }

  if (data.session?.access_token) {
    localStorage.setItem('citywatch_token', data.session.access_token);
  }

  return data;
}

export async function signOutOfSupabase() {
  if (!supabase) return;
  await supabase.auth.signOut();
  localStorage.removeItem('citywatch_token');
}
