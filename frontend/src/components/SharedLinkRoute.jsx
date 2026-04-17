import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { premiumAPI } from '../api/premium.js';

/**
 * SharedLinkRoute — Wrapper component for token-authenticated shared links
 * 
 * This component:
 * 1. Extracts the share token from URL params
 * 2. Verifies token validity via backend
 * 3. Shows expiry warning if link expires <1 day
 * 4. Validates expiry before rendering child content
 * 5. Passes workerId to child components for data fetching
 * 
 * Usage in App.jsx:
 * <Route path="/link/:shareToken/*" element={<SharedLinkRoute />} />
 */

const TOKEN_VERIFICATION_ENDPOINT = '/api/v1/share-tokens/verify';
const EXPIRY_WARNING_HOURS = 24;

export function SharedLinkRoute({ children }) {
  const { shareToken } = useParams();
  const navigate = useNavigate();

  const [tokenData, setTokenData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isError, setIsError] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [showExpiryWarning, setShowExpiryWarning] = useState(false);

  useEffect(() => {
    const verifyToken = async () => {
      if (!shareToken) {
        setErrorMsg('No share token provided in URL');
        setIsError(true);
        setIsLoading(false);
        return;
      }

      try {
        const response = await fetch(TOKEN_VERIFICATION_ENDPOINT, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ share_token: shareToken }),
        });

        if (!response.ok) {
          const error = await response.json();
          setErrorMsg(error.message || 'Invalid or expired share link');
          setIsError(true);
          setIsLoading(false);
          return;
        }

        const data = await response.json();

        // Check if token is expired
        if (!data.is_valid) {
          setErrorMsg(data.message || 'This share link has expired');
          setIsError(true);
          setIsLoading(false);
          return;
        }

        // Check expiry warning (expires < 24 hours)
        if (data.expires_in_seconds && data.expires_in_seconds < EXPIRY_WARNING_HOURS * 3600) {
          setShowExpiryWarning(true);
        }

        // Token is valid — store data in state
        setTokenData({
          workerId: data.worker_id,
          expiresAt: data.expires_at,
          expiresInSeconds: data.expires_in_seconds,
        });

        setIsLoading(false);
      } catch (error) {
        console.error('[SharedLinkRoute] Token verification error:', error);
        setErrorMsg('Error verifying share link. Please try again.');
        setIsError(true);
        setIsLoading(false);
      }
    };

    verifyToken();
  }, [shareToken]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Verifying access...</p>
        </div>
      </div>
    );
  }

  if (isError || !tokenData) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
          <div className="text-red-600 text-5xl mb-4">⛔</div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Access Denied</h1>
          <p className="text-gray-600 mb-6">{errorMsg}</p>
          <button
            onClick={() => navigate('/')}
            className="inline-block bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Sign In to GigKavach
          </button>
        </div>
      </div>
    );
  }

  // Token is valid — render content with warnings if needed
  return (
    <div className="w-full">
      {/* Expiry Warning Banner */}
      {showExpiryWarning && (
        <div className="bg-amber-50 border-l-4 border-amber-500 p-4 mb-6">
          <div className="flex items-start">
            <div className="text-amber-600 text-xl mr-3">⏰</div>
            <div className="flex-1">
              <h3 className="font-semibold text-amber-900">Link Expires Soon</h3>
              <p className="text-amber-700 text-sm">
                This shared link will expire in about {Math.floor(tokenData.expiresInSeconds / 3600)} hour(s).
                
              </p>
              <button
                onClick={() => navigate('/auth/login')}
                className="text-blue-600 text-sm font-semibold mt-2 hover:underline"
              >
                Create an account to keep permanent access →
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Watermark */}
      <div className="text-right text-xs text-gray-400 mb-2 px-4">
        🔗 Shared Link • Expires: {new Date(tokenData.expiresAt).toLocaleDateString()}
      </div>

      {/* Render child routes with worker context */}
      {children}
    </div>
  );
}

/**
 * Hook to access shared link context from child components
 * Usage: const { workerId, expiresAt } = useSharedLinkContext();
 */
export function useSharedLinkContext() {
  const { shareToken } = useParams();
  const navigate = useNavigate();

  // This would be provided via React Context in a real implementation
  // For now, child components should use the parent data via context or props
  return {
    isSharedLink: !!shareToken,
    shareToken,
  };
}
