import React, { useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { useTheme } from '../hooks/useTheme';
import { useAuth } from '../hooks/useAuth';

const Layout: React.FC = () => {
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();
  const { user, logout } = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const navigation = [
    { name: 'Live Feeds', href: '/', icon: '📷' },
    { name: 'Detections', href: '/detections', icon: '🦅' },
    ...(user?.role === 'admin' ? [
      { name: 'Analytics', href: '/analytics', icon: '📊' },
      { name: 'Admin Panel', href: '/admin', icon: '🛡️' }
    ] : []),
  ];

  return (
    <div className="flex h-screen bg-gray-100 dark:bg-gray-900">
      {/* Mobile menu button */}
      <button
        onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
        className="lg:hidden fixed top-4 left-4 z-50 p-2 rounded-md bg-white dark:bg-gray-800 shadow-md"
      >
        <svg className="w-6 h-6 text-gray-800 dark:text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          {isMobileMenuOpen ? (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          ) : (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          )}
        </svg>
      </button>

      {/* Sidebar - Desktop */}
      <div className="hidden lg:block w-64 bg-white dark:bg-gray-800 shadow-md">
        <div className="p-4">
          <h1 className="text-2xl font-bold text-gray-800 dark:text-white">BirdCam</h1>
        </div>
        
        <nav className="mt-8">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center px-6 py-3 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors ${
                  isActive ? 'bg-blue-50 dark:bg-blue-900 text-blue-600 dark:text-blue-400 border-r-2 border-blue-600' : ''
                }`}
              >
                <span className="mr-3 text-xl">{item.icon}</span>
                <span className="font-medium">{item.name}</span>
              </Link>
            );
          })}
        </nav>

        {/* User info and actions */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 space-y-3">
          <div className="px-3 py-2 text-sm">
            <div className="text-gray-700 dark:text-gray-300">
              <span className="mr-2">👤</span>
              {user?.username}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 capitalize">
              {user?.role} account
            </div>
          </div>
          
          <button
            onClick={toggleTheme}
            className="flex items-center w-full px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
          >
            <span className="mr-3 text-xl">{theme === 'light' ? '🌙' : '☀️'}</span>
            <span className="font-medium">{theme === 'light' ? 'Dark Mode' : 'Light Mode'}</span>
          </button>
          
          <button
            onClick={logout}
            className="flex items-center w-full px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
          >
            <span className="mr-3 text-xl">🚪</span>
            <span className="font-medium">Logout</span>
          </button>
        </div>

      </div>

      {/* Sidebar - Mobile */}
      <div className={`lg:hidden fixed inset-0 z-40 flex ${isMobileMenuOpen ? '' : 'pointer-events-none'}`}>
        <div
          className={`fixed inset-0 bg-black bg-opacity-50 transition-opacity ${isMobileMenuOpen ? 'opacity-100' : 'opacity-0'}`}
          onClick={() => setIsMobileMenuOpen(false)}
        />
        <div className={`relative flex-1 flex flex-col max-w-xs w-full bg-white dark:bg-gray-800 shadow-xl transform transition-transform ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}`}>
          <div className="p-4 pt-16">
            <h1 className="text-2xl font-bold text-gray-800 dark:text-white">BirdCam</h1>
            </div>
          
          <nav className="mt-8">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={`flex items-center px-6 py-3 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors ${
                    isActive ? 'bg-blue-50 dark:bg-blue-900 text-blue-600 dark:text-blue-400 border-r-2 border-blue-600' : ''
                  }`}
                >
                  <span className="mr-3 text-xl">{item.icon}</span>
                  <span className="font-medium">{item.name}</span>
                </Link>
              );
            })}
          </nav>

          {/* User info and actions - Mobile */}
          <div className="p-4 border-t border-gray-200 dark:border-gray-700 space-y-3">
            <div className="px-3 py-2 text-sm">
              <div className="text-gray-700 dark:text-gray-300">
                <span className="mr-2">👤</span>
                {user?.username}
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400 capitalize">
                {user?.role} account
              </div>
            </div>
            
            <button
              onClick={toggleTheme}
              className="flex items-center w-full px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
            >
              <span className="mr-3 text-xl">{theme === 'light' ? '🌙' : '☀️'}</span>
              <span className="font-medium">{theme === 'light' ? 'Dark Mode' : 'Light Mode'}</span>
            </button>
            
            <button
              onClick={logout}
              className="flex items-center w-full px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
            >
              <span className="mr-3 text-xl">🚪</span>
              <span className="font-medium">Logout</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-white dark:bg-gray-800 shadow-sm">
          <div className="px-6 py-4 pl-16 lg:pl-6">
            <h2 className="text-xl font-semibold text-gray-800 dark:text-white">
              {navigation.find(item => item.href === location.pathname)?.name || 'BirdCam'}
            </h2>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-x-hidden overflow-y-auto bg-gray-100 dark:bg-gray-900 p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default Layout;