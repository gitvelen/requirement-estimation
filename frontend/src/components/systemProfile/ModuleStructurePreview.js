import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { normalizeModuleStructureNodes } from '../../utils/systemProfileModuleStructure';

const MAX_MODULE_DEPTH = 3;

const ROOT_STYLE = {
  display: 'grid',
  gap: 8,
  width: '100%',
};

const NODE_BODY_STYLE = {
  padding: 10,
  border: '1px solid #f0f0f0',
  borderRadius: 8,
  background: '#ffffff',
};

const NODE_HEADER_STYLE = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 8,
  alignItems: 'center',
};

const NODE_NAME_STYLE = {
  fontWeight: 600,
  color: '#262626',
};

const NODE_DESCRIPTION_STYLE = {
  color: '#8c8c8c',
  fontSize: 12,
  lineHeight: 1.5,
};

const TOGGLE_BUTTON_STYLE = {
  border: 'none',
  background: 'transparent',
  color: '#1677ff',
  cursor: 'pointer',
  padding: 0,
  fontSize: 12,
  lineHeight: 1.5,
};

const DEPTH_WARNING_STYLE = {
  color: '#faad14',
  fontSize: 12,
  lineHeight: 1.5,
};

const collectDefaultExpandedPaths = (nodes, prefix = 'root', depth = 1) => {
  if (!Array.isArray(nodes)) {
    return [];
  }

  return nodes.flatMap((node, index) => {
    const nodePath = `${prefix}-${index}`;
    const hasChildren = Array.isArray(node?.children) && node.children.length > 0;
    if (depth !== 1 || !hasChildren) {
      return [];
    }
    return [nodePath];
  });
};

const createNodeWrapperStyle = (depth) => ({
  marginLeft: Math.max(0, depth - 1) * 20,
  borderInlineStart: depth > 1 ? '4px solid #d9d9d9' : undefined,
  paddingInlineStart: depth > 1 ? 12 : 0,
});

const ModuleStructurePreview = ({ value }) => {
  const modules = useMemo(() => normalizeModuleStructureNodes(value), [value]);
  const defaultExpandedPathKeys = useMemo(() => collectDefaultExpandedPaths(modules), [modules]);
  const [expandedPaths, setExpandedPaths] = useState(() => new Set(defaultExpandedPathKeys));

  useEffect(() => {
    setExpandedPaths((previousPaths) => {
      if (
        previousPaths.size === defaultExpandedPathKeys.length
        && defaultExpandedPathKeys.every((pathKey) => previousPaths.has(pathKey))
      ) {
        return previousPaths;
      }
      return new Set(defaultExpandedPathKeys);
    });
  }, [defaultExpandedPathKeys]);

  const togglePath = useCallback((pathKey) => {
    setExpandedPaths((previousPaths) => {
      const nextPaths = new Set(previousPaths);
      if (nextPaths.has(pathKey)) {
        nextPaths.delete(pathKey);
      } else {
        nextPaths.add(pathKey);
      }
      return nextPaths;
    });
  }, []);

  const renderNodes = useCallback((nodes, depth = 1, prefix = 'root') => (
    <div style={ROOT_STYLE}>
      {nodes.map((node, index) => {
        const nodePath = `${prefix}-${index}`;
        const hasChildren = Array.isArray(node.children) && node.children.length > 0;
        const expanded = expandedPaths.has(nodePath);
        const depthLimitReached = depth >= MAX_MODULE_DEPTH;
        return (
          <div key={nodePath} style={createNodeWrapperStyle(depth)}>
            <div style={NODE_BODY_STYLE}>
              <div style={ROOT_STYLE}>
                <div style={NODE_HEADER_STYLE}>
                  <span style={NODE_NAME_STYLE}>{node.module_name}</span>
                  {hasChildren ? (
                    <button type="button" onClick={() => togglePath(nodePath)} style={TOGGLE_BUTTON_STYLE}>
                      {expanded ? `收起 ${node.module_name}` : `展开 ${node.module_name}`}
                    </button>
                  ) : null}
                </div>
                {node.description ? <div style={NODE_DESCRIPTION_STYLE}>{node.description}</div> : null}
                {hasChildren && expanded && depthLimitReached ? (
                  <div style={DEPTH_WARNING_STYLE}>超出展示深度</div>
                ) : null}
                {hasChildren && expanded && !depthLimitReached ? renderNodes(node.children, depth + 1, nodePath) : null}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  ), [expandedPaths, togglePath]);

  if (!modules.length) {
    return <span style={NODE_DESCRIPTION_STYLE}>—</span>;
  }

  return renderNodes(modules);
};

export default ModuleStructurePreview;
