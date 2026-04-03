/**
 * UserProfile.jsx — User Profile Display Component
 * ───────────────────────────────────────────────
 * Displays current user information and profile.
 */

import React from 'react';
import { useAuth } from '../context/AuthContext';
import LogoutButton from './LogoutButton';

const UserProfile = () => {
  const { user, userProfile, isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return (
      <div className="p-4 bg-gray-100 rounded-lg">
        <p className="text-gray-600">Not logged in</p>
      </div>
    );
  }

  return (
    <div className="p-4 bg-white rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4">User Profile</h3>
      
      <div className="space-y-2">
        <div>
          <span className="font-medium">Email: </span>
          <span>{user?.email || 'N/A'}</span>
        </div>
        
        <div>
          <span className="font-medium">User ID: </span>
          <span className="text-sm text-gray-600">{user?.id || 'N/A'}</span>
        </div>
        
        {userProfile && (
          <>
            <div>
              <span className="font-medium">Full Name: </span>
              <span>{userProfile.full_name || 'Not set'}</span>
            </div>
            
            <div>
              <span className="font-medium">Role: </span>
              <span>{userProfile.role || 'user'}</span>
            </div>
          </>
        )}
        
        <div className="pt-4 border-t mt-4">
          <LogoutButton className="px-4 py-2 bg-red-100 rounded hover:bg-red-200" />
        </div>
      </div>
    </div>
  );
};

export default UserProfile;
