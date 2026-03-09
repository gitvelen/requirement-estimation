export const normalizeModuleNode = (node) => {
  if (!node || typeof node !== 'object') {
    return null;
  }

  const moduleName = String(node.module_name ?? '').trim();
  if (!moduleName) {
    return null;
  }

  const childrenFromTree = Array.isArray(node.children)
    ? node.children.map((childNode) => normalizeModuleNode(childNode)).filter(Boolean)
    : [];

  const childrenFromFunctions = Array.isArray(node.functions)
    ? node.functions.map((functionItem) => {
      const functionName = String(functionItem?.name ?? functionItem ?? '').trim();
      if (!functionName) {
        return null;
      }
      return {
        module_name: functionName,
        description: String(functionItem?.desc ?? '').trim(),
        children: [],
      };
    }).filter(Boolean)
    : [];

  return {
    module_name: moduleName,
    description: String(node.description ?? '').trim(),
    children: [...childrenFromTree, ...childrenFromFunctions],
  };
};

export const normalizeModuleStructureNodes = (value) => {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => normalizeModuleNode(item)).filter(Boolean);
};

export const sanitizeModuleNode = (node) => {
  if (!node || typeof node !== 'object') {
    return null;
  }

  const moduleName = String(node.module_name ?? '').trim();
  const description = String(node.description ?? '').trim();
  const children = Array.isArray(node.children)
    ? node.children.map((childNode) => sanitizeModuleNode(childNode)).filter(Boolean)
    : [];

  if (!moduleName && !description && children.length === 0) {
    return null;
  }

  return {
    module_name: moduleName,
    description,
    children,
  };
};

export const sanitizeModuleStructureNodes = (value) => (
  normalizeModuleStructureNodes(value).map((item) => sanitizeModuleNode(item)).filter(Boolean)
);
