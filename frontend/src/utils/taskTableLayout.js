export const resolveActionColumnWidth = ({ isExpert, resolvedTab }) => {
  if (isExpert && resolvedTab === 'ongoing') {
    return 208;
  }
  return 148;
};
