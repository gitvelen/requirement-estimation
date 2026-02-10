import useAuth from './useAuth';

const usePermission = () => {
  const { user, activeRole, setActiveRole } = useAuth();
  const roles = user?.roles || [];

  const normalizedActiveRole = activeRole || '';

  const hasRole = (role) => roles.includes(role);
  const hasAnyRole = (roleList = []) => roleList.some((role) => roles.includes(role));
  const isActiveRole = (role) => normalizedActiveRole === role;

  return {
    roles,
    activeRole: normalizedActiveRole,
    setActiveRole,
    hasRole,
    hasAnyRole,
    isActiveRole,
    isAdmin: isActiveRole('admin'),
    isManager: isActiveRole('manager'),
    isExpert: isActiveRole('expert'),
    isViewer: isActiveRole('viewer'),
  };
};

export default usePermission;
