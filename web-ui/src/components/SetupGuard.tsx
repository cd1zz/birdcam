import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { api } from '../api/client';

interface SetupGuardProps {
  children: React.ReactNode;
}

const SetupGuard: React.FC<SetupGuardProps> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isChecking, setIsChecking] = useState(true);
  const [, setSetupRequired] = useState(false);

  useEffect(() => {
    const checkSetup = async () => {
      try {
        const response = await api.get('/api/setup/status');
        const { setup_required } = response.data;
        
        setSetupRequired(setup_required);
        
        // If setup is required and we're not already on the setup page, redirect
        if (setup_required && location.pathname !== '/setup') {
          navigate('/setup', { replace: true });
        } 
        // If setup is not required and we're on the setup page, redirect to login
        else if (!setup_required && location.pathname === '/setup') {
          navigate('/login', { replace: true });
        }
      } catch (error) {
        console.error('Failed to check setup status:', error);
        // In case of error, allow normal flow
      } finally {
        setIsChecking(false);
      }
    };

    checkSetup();
  }, [navigate, location.pathname]);

  // Show loading screen while checking
  if (isChecking) {
    return (
      <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Checking system status...</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};

export default SetupGuard;