import React, { createContext, useContext, useState, ReactNode } from 'react';

export type UserRole = 'police' | 'judge' | 'forensics';

interface RoleContextType {
  role: UserRole;
  setRole: (role: UserRole) => void;
  canUpload: boolean;
  canViewMetadata: boolean;
  canSendPublicAlert: boolean;
}

const RoleContext = createContext<RoleContextType | undefined>(undefined);

export const RoleProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [role, setRole] = useState<UserRole>(() => {
    const savedRole = localStorage.getItem('role');
    return (savedRole as UserRole) || 'police';
  });

  const canUpload = role === 'police';
  const canViewMetadata = role === 'forensics';
  const canSendPublicAlert = role === 'police';

  return (
    <RoleContext.Provider value={{ role, setRole, canUpload, canViewMetadata, canSendPublicAlert }}>
      {children}
    </RoleContext.Provider>
  );
};

export const useRole = () => {
  const context = useContext(RoleContext);
  if (!context) {
    throw new Error('useRole must be used within a RoleProvider');
  }
  return context;
};