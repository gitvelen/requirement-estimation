import React from 'react';
import { Modal } from 'antd';

const ConfirmModal = ({
  open,
  title = '确认操作',
  content,
  okText = '确认',
  cancelText = '取消',
  onOk,
  onCancel,
  confirmLoading = false,
  danger = false,
  width,
}) => (
  <Modal
    open={open}
    title={title}
    okText={okText}
    cancelText={cancelText}
    onOk={onOk}
    onCancel={onCancel}
    confirmLoading={confirmLoading}
    okButtonProps={danger ? { danger: true } : undefined}
    width={width}
  >
    {typeof content === 'string' ? <p>{content}</p> : content}
  </Modal>
);

ConfirmModal.confirm = Modal.confirm;

export default ConfirmModal;
