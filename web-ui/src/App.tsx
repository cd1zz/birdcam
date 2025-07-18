import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from './contexts/ThemeContext';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import SetupGuard from './components/SetupGuard';
import Layout from './components/Layout';
import Login from './pages/Login';
import Setup from './pages/Setup';
import LiveFeeds from './pages/LiveFeeds';
import Detections from './pages/Detections';
import Analytics from './pages/Analytics';
import Settings from './pages/Settings';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <Router>
          <AuthProvider>
            <SetupGuard>
              <Routes>
                <Route path="/setup" element={<Setup />} />
                <Route path="/login" element={<Login />} />
                <Route path="/" element={
                  <ProtectedRoute>
                    <Layout />
                  </ProtectedRoute>
                }>
                <Route index element={<LiveFeeds />} />
                <Route path="detections" element={<Detections />} />
                <Route path="analytics" element={
                  <ProtectedRoute requireAdmin>
                    <Analytics />
                  </ProtectedRoute>
                } />
                <Route path="settings" element={
                  <ProtectedRoute requireAdmin>
                    <Settings />
                  </ProtectedRoute>
                } />
              </Route>
            </Routes>
            </SetupGuard>
          </AuthProvider>
        </Router>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export default App;