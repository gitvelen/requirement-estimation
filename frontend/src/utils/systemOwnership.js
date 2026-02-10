const toTrimmedString = (value) => String(value ?? '').trim();

const normalizeStringList = (value) => {
  if (Array.isArray(value)) {
    return Array.from(new Set(value.map(toTrimmedString).filter(Boolean)));
  }

  const text = toTrimmedString(value);
  if (!text) {
    return [];
  }

  return Array.from(
    new Set(
      text
        .replace(/，/g, ',')
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean)
    )
  );
};

const getUserCandidates = (user) => {
  const userId = toTrimmedString(user?.id);
  const userNames = Array.from(
    new Set(
      [
        user?.username,
        user?.displayName,
        user?.display_name,
      ]
        .map(toTrimmedString)
        .filter(Boolean)
    )
  );

  return { userId, userNames };
};

export const resolveSystemOwnership = (system, user) => {
  const extra = typeof system?.extra === 'object' && system?.extra ? system.extra : {};

  const ownerId = toTrimmedString(extra.owner_id);
  const ownerUsername = toTrimmedString(extra.owner_username);
  const backupOwnerIds = normalizeStringList(extra.backup_owner_ids);
  const backupOwnerUsernames = normalizeStringList(extra.backup_owner_usernames);

  const { userId, userNames } = getUserCandidates(user);

  const isOwner = Boolean(
    (ownerId && userId && ownerId === userId)
    || (ownerUsername && userNames.includes(ownerUsername))
  );

  const isBackup = Boolean(
    (userId && backupOwnerIds.includes(userId))
    || backupOwnerUsernames.some((name) => userNames.includes(name))
  );

  return {
    isOwner,
    isBackup,
    canWrite: isOwner || isBackup,
  };
};

export const filterResponsibleSystems = (systems, user) => {
  const list = Array.isArray(systems) ? systems : [];
  return list.filter((system) => resolveSystemOwnership(system, user).canWrite);
};

