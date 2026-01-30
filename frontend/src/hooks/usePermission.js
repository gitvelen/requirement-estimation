import useAuth from './useAuth';

const usePermission = () => {
  const { user } = useAuth();
  const roles = user?.roles || [];

  const hasRole = (role) => roles.includes(role);
  const hasAnyRole = (roleList = []) => roleList.some((role) => roles.includes(role));

  return {
    roles,
    hasRole,
    hasAnyRole,
    isAdmin: hasRole('admin'),
    isManager: hasRole('manager'),
    isExpert: hasRole('expert'),
  };
};

export default usePermission;
