import { useEffect, useState, FormEvent } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { CheckCircle2, ShieldCheck } from 'lucide-react';
import Button from '../components/Button';
import Card from '../components/Card';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { isSupabaseConfigured } from '../lib/supabase';

export default function AuthPage({ mode = 'login' }: { mode?: 'login' | 'signup' }) {
  const { isAuthenticated, loading, signInWithEmail, signUpWithEmail, profile } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [status, setStatus] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isAuthenticated && !loading) {
      navigate(profile?.onboarding_completed ? '/home' : '/onboarding', { replace: true });
    }
  }, [isAuthenticated, loading, navigate, profile]);

  if (isAuthenticated && !loading) {
    return <Navigate to={profile?.onboarding_completed ? '/home' : '/onboarding'} replace />;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!isSupabaseConfigured) return;

    const normalizedEmail = email.trim();

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
      setStatus(t('auth_invalid_email'));
      return;
    }
    if (mode === 'signup' && !fullName.trim()) {
      setStatus(t('auth_name_required'));
      return;
    }
    if (!password) {
      setStatus(t('auth_password_required'));
      return;
    }
    if (mode === 'signup' && password !== confirmPassword) {
      setStatus(t('auth_password_mismatch'));
      return;
    }

    setSubmitting(true);
    setStatus('');
    try {
      if (mode === 'signup') {
        const result = await signUpWithEmail(fullName, normalizedEmail, password);
        if (result.error) {
          setStatus(t('auth_signup_error'));
        } else if (result.requiresEmailConfirmation) {
          setStatus(t('auth_confirmation_required'));
        } else {
          navigate('/onboarding', { replace: true });
        }
      } else {
        const result = await signInWithEmail(normalizedEmail, password);
        if (result.error) {
          const message = result.error.message.toLowerCase();
          setStatus(message.includes('invalid login credentials') || message.includes('invalid_credentials')
            ? t('auth_invalid_credentials')
            : t('auth_login_error'));
        } else {
          navigate(result.profile?.onboarding_completed ? '/home' : '/onboarding', { replace: true });
        }
      }
    } catch (error) {
      if (import.meta.env.DEV) console.error('Authentication request failed:', error);
      setStatus(mode === 'signup' ? t('auth_signup_error') : t('auth_login_error'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-lg space-y-5 py-6">
      <Card>
        <div className="flex items-center gap-2 text-leaf-700">
          <ShieldCheck size={20} />
          <span className="font-bold">{mode === 'signup' ? t('create_account') : t('login_button')}</span>
        </div>
        <h1 className="mt-3 text-2xl font-extrabold text-gray-800">
          {mode === 'signup' ? t('auth_signup_title') : t('auth_login_title')}
        </h1>
        <p className="mt-2 text-sm text-gray-600">{t('auth_intro')}</p>

        <form className="mt-5 space-y-4" onSubmit={(event) => void handleSubmit(event)}>
          {mode === 'signup' ? (
            <div>
              <label htmlFor="auth-full-name" className="mb-2 block text-sm font-semibold text-gray-700">{t('full_name')}</label>
              <input
                id="auth-full-name"
                type="text"
                autoComplete="name"
                required
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                className="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-800 outline-none focus:border-leaf-500"
              />
            </div>
          ) : null}
          <div>
            <label htmlFor="auth-email" className="mb-2 block text-sm font-semibold text-gray-700">{t('email_label')}</label>
            <input
              id="auth-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-800 outline-none focus:border-leaf-500"
            />
          </div>
          <div>
            <label htmlFor="auth-password" className="mb-2 block text-sm font-semibold text-gray-700">{t('password_label')}</label>
            <input
              id="auth-password"
              type="password"
              autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-800 outline-none focus:border-leaf-500"
            />
          </div>
          {mode === 'signup' ? (
            <div>
              <label htmlFor="auth-confirm-password" className="mb-2 block text-sm font-semibold text-gray-700">{t('confirm_password_label')}</label>
              <input
                id="auth-confirm-password"
                type="password"
                autoComplete="new-password"
                required
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                className="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-base text-gray-800 outline-none focus:border-leaf-500"
              />
            </div>
          ) : null}

          <Button type="submit" disabled={submitting || !isSupabaseConfigured}>
            {submitting ? t('please_wait') : mode === 'signup' ? t('create_account') : t('login_button')}
          </Button>
        </form>

        {!isSupabaseConfigured && (
          <div role="alert" className="mt-4 rounded-2xl bg-amber-50 px-3 py-2 text-sm text-amber-800">
            {t('auth_setup_required')}
          </div>
        )}

        {status && (
          <div className="mt-4 flex items-center gap-2 rounded-2xl bg-amber-50 px-3 py-2 text-sm text-amber-800">
            <CheckCircle2 size={16} />
            {status}
          </div>
        )}

        <p className="mt-5 text-sm text-gray-600">
          {mode === 'signup' ? t('auth_have_account') : t('auth_no_account')}{' '}
          <Link className="font-semibold text-leaf-700 underline" to={mode === 'signup' ? '/login' : '/signup'}>
            {mode === 'signup' ? t('login_button') : t('create_account')}
          </Link>
        </p>
      </Card>
    </div>
  );
}
