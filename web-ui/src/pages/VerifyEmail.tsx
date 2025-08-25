import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { processingApi } from '../api/client';

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');
  const token = searchParams.get('token');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setMessage('Invalid verification link');
      return;
    }

    processingApi.post('/api/verify-email', { token })
      .then((response: { data: { message: string } }) => {
        setStatus('success');
        setMessage(response.data.message);
      })
      .catch((error: { response?: { data?: { error?: string } } }) => {
        setStatus('error');
        setMessage(error.response?.data?.error || 'Verification failed');
      });
  }, [token]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 text-center">
        {status === 'loading' && (
          <>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
            <p className="text-gray-600 dark:text-gray-400">Verifying your email...</p>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="rounded-full bg-green-100 dark:bg-green-900/50 p-3 mx-auto w-16 h-16 flex items-center justify-center">
              <svg className="h-8 w-8 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Email Verified!
            </h2>
            <p className="text-gray-600 dark:text-gray-400">{message}</p>
            <Link
              to="/login"
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Go to Login
            </Link>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="rounded-full bg-red-100 dark:bg-red-900/50 p-3 mx-auto w-16 h-16 flex items-center justify-center">
              <svg className="h-8 w-8 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Verification Failed
            </h2>
            <p className="text-gray-600 dark:text-gray-400">{message}</p>
            <div className="space-y-2">
              <Link
                to="/register"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                Back to Registration
              </Link>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                or request a new verification email
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}