import React from 'react';
import { Table } from 'antd';
import Empty from './Empty';

const DataTable = ({ pagination, locale, ...rest }) => {
  const resolvedPagination = pagination === undefined ? { pageSize: 10 } : pagination;
  const mergedLocale = locale ? { ...locale } : {};
  if (!mergedLocale.emptyText) {
    mergedLocale.emptyText = <Empty />;
  }

  return (
    <Table
      {...rest}
      pagination={resolvedPagination}
      locale={mergedLocale}
    />
  );
};

export default DataTable;
