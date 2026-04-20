import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Tabs, Table, Button, Space, message, Card, Tag, Typography, Popconfirm, Modal, Input, Row, Col, Form, InputNumber, Popover, Checkbox, AutoComplete, Select, Dropdown } from 'antd';
import { CheckOutlined, PlusOutlined, DeleteOutlined, ArrowLeftOutlined, HistoryOutlined, EditOutlined, DownOutlined } from '@ant-design/icons';
import axios from 'axios';
import ExpandableText from '../components/ExpandableText';
import usePermission from '../hooks/usePermission';
import { extractErrorMessage } from '../utils/errorMessage';

const { Text } = Typography;
const { TextArea } = Input;
const NON_SUBSTANTIVE_FIELDS = new Set(['序号']);
const REMARK_FIELDS = new Set(['备注', 'remark']);

const EditPage = () => {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const { isManager } = usePermission();
  const [form] = Form.useForm();

  const [systemsData, setSystemsData] = useState({});
  const [modifications, setModifications] = useState([]);
  const [confirmed, setConfirmed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [currentSystem, setCurrentSystem] = useState('');
  const [historyVisible, setHistoryVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingFeature, setEditingFeature] = useState(null);
  const [editingIndex, setEditingIndex] = useState(null);
  const [aiSystemAnalysis, setAiSystemAnalysis] = useState(null);
  const [targetSystemMode, setTargetSystemMode] = useState('unlimited');
  const [targetSystemDisplay, setTargetSystemDisplay] = useState('不限');
  const [addSystemVisible, setAddSystemVisible] = useState(false);
  const [addingSystem, setAddingSystem] = useState(false);
  const [mainSystemNames, setMainSystemNames] = useState([]);
  const [systemSuggestions, setSystemSuggestions] = useState([]);
  const [visibleColumns, setVisibleColumns] = useState([
    '业务描述',
    '输入',
    '输出',
    '依赖项',
    '备注'
  ]);
  const [renameVisible, setRenameVisible] = useState(false);
  const [newSystemName, setNewSystemName] = useState('');

  const [addSystemForm] = Form.useForm();

  const fetchEvaluationResult = useCallback(async (preferredSystem = '') => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/v1/requirement/result/${taskId}`);
      const {
        systems_data,
        modifications,
        confirmed,
        ai_system_analysis,
        target_system_mode,
        target_system_name,
        target_system_display,
      } = response.data.data;

      setSystemsData(systems_data);
      setModifications(modifications || []);
      setConfirmed(confirmed);
      setAiSystemAnalysis(ai_system_analysis || null);
      const normalizedTargetMode = String(target_system_mode || 'unlimited').trim().toLowerCase() || 'unlimited';
      setTargetSystemMode(normalizedTargetMode);
      setTargetSystemDisplay(
        target_system_display
        || (normalizedTargetMode === 'specific' ? (target_system_name || '') : '不限')
        || '不限'
      );

      // 设置默认选中系统（优先：preferredSystem > 原先选中 > 第一个系统）
      const systemNames = Object.keys(systems_data);
      setCurrentSystem((prev) => {
        const preferred = (preferredSystem || '').trim();
        if (preferred && systemNames.includes(preferred)) {
          return preferred;
        }
        if (prev && systemNames.includes(prev)) {
          return prev;
        }
        return systemNames[0] || '';
      });
    } catch (error) {
      console.error('获取评估结果失败:', error);
      message.error(error.response?.data?.detail || '获取评估结果失败');
      navigate('/tasks');
    } finally {
      setLoading(false);
    }
  }, [taskId, navigate]);

  // 加载评估结果
  useEffect(() => {
    fetchEvaluationResult();
  }, [fetchEvaluationResult]);

  const fetchMainSystems = useCallback(async () => {
    try {
      const response = await axios.get('/api/v1/system/systems');
      const systems = response.data?.data?.systems || [];
      const names = systems.map(s => s.name).filter(Boolean);
      setMainSystemNames(names);
    } catch (error) {
      console.warn('获取主系统清单失败:', error);
    }
  }, []);

  useEffect(() => {
    fetchMainSystems();
  }, [fetchMainSystems]);

  useEffect(() => {
    const candidateNames = (aiSystemAnalysis?.candidate_systems || []).map(item => item?.name).filter(Boolean);
    const merged = [...mainSystemNames, ...candidateNames];
    const uniq = Array.from(new Set(merged.map(s => (s || '').trim()).filter(Boolean)));
    setSystemSuggestions(uniq.map(name => ({ value: name })));
  }, [mainSystemNames, aiSystemAnalysis]);

  const normalizeListField = (value) => {
    if (Array.isArray(value)) {
      return value.join('、');
    }
    return value || '';
  };

  const normalizeFeatureForForm = (feature) => ({
    ...feature,
    输入: normalizeListField(feature['输入'] || feature['inputs']),
    输出: normalizeListField(feature['输出'] || feature['outputs']),
    依赖项: normalizeListField(feature['依赖项'] || feature['dependencies']),
  });

  const isSubstantiveField = (field) => {
    const normalized = String(field || '').trim();
    if (!normalized) {
      return false;
    }
    if (REMARK_FIELDS.has(normalized)) {
      return false;
    }
    if (NON_SUBSTANTIVE_FIELDS.has(normalized)) {
      return false;
    }
    return true;
  };

  const hasSubstantiveChanges = (changes) => (
    Object.keys(changes || {}).some((field) => isSubstantiveField(field))
  );

  const singleSystemLocked = targetSystemMode === 'specific';

  const blockSystemScopeMutation = useCallback(() => {
    if (!singleSystemLocked) {
      return false;
    }
    message.warning('具体系统任务已锁定，不允许修改系统范围');
    return true;
  }, [singleSystemLocked]);

  const triggerReevaluate = useCallback(async () => {
    await axios.post(`/api/v1/tasks/${taskId}/reevaluate`, { force: false });
  }, [taskId]);

  const renderRemark = (text) => {
    const raw = String(text || '').trim();
    if (!raw) {
      return <Text type="secondary">-</Text>;
    }
    return <ExpandableText value={raw} limit={50} withTooltip />;
  };

  // 打开编辑Modal
  const handleEdit = (feature, index) => {
    const normalized = normalizeFeatureForForm(feature);
    setEditingFeature({ ...normalized });
    setEditingIndex(index);
    form.setFieldsValue(normalized);
    setEditModalVisible(true);
  };

  // 保存编辑
  const handleEditSave = async () => {
    try {
      const values = await form.validateFields();
      const changes = {};
      Object.keys(values).forEach(key => {
        if (values[key] !== editingFeature[key]) {
          changes[key] = values[key];
        }
      });

      if (Object.keys(changes).length === 0) {
        message.info('没有修改');
        setEditModalVisible(false);
        return;
      }

      const isSubstantive = hasSubstantiveChanges(changes);

      const doSave = async (confirm) => {
        try {
          setSaving(true);
          await axios.put(`/api/v1/requirement/features/${taskId}`, {
            system: currentSystem,
            operation: 'update',
            feature_index: editingIndex,
            feature_data: changes,
            confirm,
          });
          if (isSubstantive) {
            await triggerReevaluate();
            message.success('保存成功，已触发AI重评估');
          } else {
            message.success('保存成功');
          }
          await fetchEvaluationResult(currentSystem);
          setEditModalVisible(false);
        } catch (saveError) {
          message.error(`保存失败: ${extractErrorMessage(saveError, '保存失败')}`);
          throw saveError;
        } finally {
          setSaving(false);
        }
      };

      if (isSubstantive) {
        Modal.confirm({
          title: '确认保存并触发重评估？',
          content: '本次修改将触发 AI 重新评估，是否继续？',
          okText: '确认',
          cancelText: '取消',
          onOk: () => doSave(true),
        });
      } else {
        await doSave(false);
      }
    } catch (error) {
      console.error('保存失败:', error);
      if (error.errorFields) {
        message.error('请检查输入');
      }
    }
  };

  // 删除功能点
  const handleDelete = async (index) => {
    try {
      setSaving(true);
      await axios.put(`/api/v1/requirement/features/${taskId}`, {
        system: currentSystem,
        operation: 'delete',
        feature_index: index,
        confirm: true,
      });
      await triggerReevaluate();
      await fetchEvaluationResult(currentSystem);
      message.success('删除成功，已触发AI重评估');
    } catch (error) {
      console.error('删除失败:', error);
      message.error(`删除失败: ${extractErrorMessage(error, '删除失败')}`);
    } finally {
      setSaving(false);
    }
  };

  // 添加新功能点
  const handleAdd = () => {
    setEditingFeature({
      序号: '',
      功能模块: '',
      功能点: '',
      业务描述: '',
      输入: '',
      输出: '',
      依赖项: '',
      预估人天: null,
    });
    setEditingIndex(null);
    form.resetFields();
    form.setFieldsValue({
      预估人天: null,
    });
    setEditModalVisible(true);
  };

  // 保存新功能点
  const handleAddSave = async () => {
    try {
      const values = await form.validateFields();
      const maxIndex = systemsData[currentSystem].length;
      const newFeature = {
        ...values,
        序号: `1.${maxIndex + 1}`,
      };
      if (isManager) {
        delete newFeature['预估人天'];
      } else if (values['预估人天'] !== null && values['预估人天'] !== undefined && values['预估人天'] !== '') {
        newFeature['预估人天'] = parseFloat(values['预估人天']) || 1;
      }

      const doSave = async () => {
        try {
          setSaving(true);
          await axios.put(`/api/v1/requirement/features/${taskId}`, {
            system: currentSystem,
            operation: 'add',
            feature_data: newFeature,
            confirm: true,
          });
          await triggerReevaluate();
          await fetchEvaluationResult(currentSystem);
          message.success('添加成功，已触发AI重评估');
          setEditModalVisible(false);
        } catch (saveError) {
          message.error(`添加失败: ${extractErrorMessage(saveError, '添加失败')}`);
          throw saveError;
        } finally {
          setSaving(false);
        }
      };

      Modal.confirm({
        title: '确认保存并触发重评估？',
        content: '新增功能点将触发 AI 重新评估，是否继续？',
        okText: '确认',
        cancelText: '取消',
        onOk: doSave,
      });
    } catch (error) {
      console.error('添加失败:', error);
      if (error.errorFields) {
        message.error('请检查输入');
      }
    }
  };

  // 保存功能点到知识库
  // （已移除）功能案例沉淀：当前版本仅维护系统知识库

  // 提交给管理员
  const handleConfirm = async () => {
    try {
      setLoading(true);
      await axios.post(`/api/v1/tasks/${taskId}/submit-to-admin`);

      message.success('已提交给管理员，等待分配专家');
      setConfirmed(true);

      Modal.success({
        title: '提交成功',
        content: `任务已提交给管理员，请等待分配专家`,
        okText: '返回列表',
        onOk: () => navigate('/tasks/my-tasks')
      });
    } catch (error) {
      console.error('确认失败:', error);
      message.error('提交失败: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  // 表格列配置
  const optionalColumns = {
    业务描述: {
      title: '业务描述',
      dataIndex: '业务描述',
      key: '业务描述',
      width: 300,
      render: (text) => <Text style={{ whiteSpace: 'pre-wrap' }}>{text || '-'}</Text>,
    },
    输入: {
      title: '输入',
      dataIndex: '输入',
      key: '输入',
      width: 180,
      render: (value) => {
        const display = Array.isArray(value) ? value.join('、') : (value || '-');
        return <Text style={{ whiteSpace: 'pre-wrap' }}>{display}</Text>;
      },
    },
    输出: {
      title: '输出',
      dataIndex: '输出',
      key: '输出',
      width: 180,
      render: (value) => {
        const display = Array.isArray(value) ? value.join('、') : (value || '-');
        return <Text style={{ whiteSpace: 'pre-wrap' }}>{display}</Text>;
      },
    },
    依赖项: {
      title: '依赖项',
      dataIndex: '依赖项',
      key: '依赖项',
      width: 180,
      render: (value) => {
        const display = Array.isArray(value) ? value.join('、') : (value || '-');
        return <Text style={{ whiteSpace: 'pre-wrap' }}>{display}</Text>;
      },
    },
    备注: {
      title: '备注',
      dataIndex: '备注',
      key: '备注',
      width: 160,
      render: (text) => renderRemark(text),
    },
  };

  const handleRenameSystem = async () => {
    if (blockSystemScopeMutation()) {
      return;
    }
    const nextName = newSystemName.trim();
    if (!nextName) {
      message.warning('请输入新的系统名称');
      return;
    }
    if (nextName === currentSystem) {
      message.info('新名称与原名称相同');
      return;
    }
    try {
      setSaving(true);
      await axios.put(`/api/v1/requirement/systems/${taskId}/${encodeURIComponent(currentSystem)}/rename`, {
        new_name: nextName,
        confirm: true,
      });
      await triggerReevaluate();
      setRenameVisible(false);
      setNewSystemName('');
      await fetchEvaluationResult(nextName);
      message.success('系统重命名成功，已触发AI重评估');
    } catch (error) {
      console.error('重命名失败:', error);
      message.error(extractErrorMessage(error, '重命名失败'));
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteSystem = async () => {
    if (blockSystemScopeMutation()) {
      return;
    }
    try {
      setSaving(true);
      await axios.delete(`/api/v1/requirement/systems/${taskId}/${encodeURIComponent(currentSystem)}?confirm=true`);
      await triggerReevaluate();
      await fetchEvaluationResult();
      message.success('系统已删除，已触发AI重评估');
    } catch (error) {
      console.error('删除系统失败:', error);
      message.error(extractErrorMessage(error, '删除系统失败'));
    } finally {
      setSaving(false);
    }
  };

  const handleRebreakdownSystem = async () => {
    if (blockSystemScopeMutation()) {
      return;
    }
    if (!currentSystem) {
      message.warning('请先选择系统');
      return;
    }
    try {
      setSaving(true);
      const matched = (aiSystemAnalysis?.selected_systems || []).find((item) => item?.name === currentSystem);
      const systemType = matched?.type || '主系统';
      const response = await axios.post(`/api/v1/requirement/systems/${taskId}/${encodeURIComponent(currentSystem)}/rebreakdown`, {
        system_type: systemType
      });
      const data = response.data?.data || {};
      await fetchEvaluationResult(currentSystem);
      if (data.breakdown_error) {
        message.error(`重新拆分失败：${data.breakdown_error}`);
      } else {
        message.success(`重新拆分完成：${data.old_features || 0} → ${data.new_features || 0} 个功能点`);
      }
    } catch (error) {
      console.error('重新拆分失败:', error);
      message.error(error.response?.data?.detail || '重新拆分失败');
    } finally {
      setSaving(false);
    }
  };

  const submitAddSystem = async (payload) => {
    if (blockSystemScopeMutation()) {
      return;
    }
    try {
      const name = (payload?.name || '').trim();
      if (!name) {
        message.warning('请输入系统名称');
        return;
      }
      const type = (payload?.type || '主系统').trim() || '主系统';

      setAddingSystem(true);
      const response = await axios.post(`/api/v1/requirement/systems/${taskId}`, {
        name,
        type,
        auto_breakdown: payload?.auto_breakdown !== false,
        confirm: true,
      });
      const data = response.data?.data || {};
      const finalName = data.final_system_name || name;
      const breakdownError = data.breakdown_error;

      setAddSystemVisible(false);
      addSystemForm.resetFields();

      await triggerReevaluate();
      await fetchEvaluationResult(finalName);

      if (breakdownError) {
        message.warning(`系统已新增，已触发AI重评估，但自动拆分失败：${breakdownError}`);
      } else {
        message.success(`系统已新增并完成自动拆分（${data.added_features || 0}个功能点），已触发AI重评估`);
      }
    } catch (error) {
      console.error('新增系统失败:', error);
      message.error(extractErrorMessage(error, '新增系统失败'));
    } finally {
      setAddingSystem(false);
    }
  };

  const openAddSystemModal = (prefillName = '') => {
    addSystemForm.setFieldsValue({
      name: (prefillName || '').trim(),
      type: '主系统',
      auto_breakdown: true,
    });
    setAddSystemVisible(true);
  };

  const openRebreakdownConfirm = () => {
    if (confirmed || !currentSystem || singleSystemLocked) {
      return;
    }
    Modal.confirm({
      title: '确定要重新拆分当前系统吗？',
      content: '该操作会覆盖当前系统下全部功能点，建议先查看修改历史。',
      okText: '确定',
      cancelText: '取消',
      onOk: handleRebreakdownSystem,
    });
  };

  const openDeleteSystemConfirm = () => {
    if (confirmed || !currentSystem || singleSystemLocked) {
      return;
    }
    Modal.confirm({
      title: '确定要删除当前系统吗？',
      content: '该系统下所有功能点将被移除。',
      okText: '确定',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: handleDeleteSystem,
    });
  };

  const systemActionMenuItems = [
    {
      key: 'add_system',
      label: '新增系统',
      disabled: confirmed || saving,
    },
    {
      key: 'rename_system',
      label: '重命名系统',
      disabled: confirmed || !currentSystem,
    },
    {
      key: 'rebreakdown_system',
      label: '重新拆分当前系统',
      disabled: confirmed || !currentSystem,
    },
    {
      key: 'delete_system',
      label: '删除当前系统',
      danger: true,
      disabled: confirmed || !currentSystem,
    },
  ];

  const handleSystemActionMenuClick = ({ key }) => {
    if (key === 'add_system') {
      openAddSystemModal();
      return;
    }
    if (key === 'rename_system') {
      setNewSystemName(currentSystem);
      setRenameVisible(true);
      return;
    }
    if (key === 'rebreakdown_system') {
      openRebreakdownConfirm();
      return;
    }
    if (key === 'delete_system') {
      openDeleteSystemConfirm();
    }
  };

  const columns = [
    {
      title: '序号',
      dataIndex: '序号',
      key: '序号',
      width: 80,
    },
    {
      title: '功能模块',
      dataIndex: '功能模块',
      key: '功能模块',
      width: 150,
      render: (value) => <Text style={{ whiteSpace: 'pre-wrap' }}>{value || '-'}</Text>,
    },
    {
      title: '功能点',
      dataIndex: '功能点',
      key: '功能点',
      width: 200,
      render: (value) => <Text style={{ whiteSpace: 'pre-wrap' }}>{value || '-'}</Text>,
    },
    {
      title: '预估人天',
      dataIndex: '预估人天',
      key: '预估人天',
      width: 100,
      render: (value) => <Text strong>{value ?? '-'}</Text>,
    },
    {
      title: '操作',
      key: 'action',
      width: 280,
      fixed: 'right',
      render: (_, record, index) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record, index)}
            disabled={confirmed}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个功能点吗？"
            onConfirm={() => handleDelete(index)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
              disabled={confirmed}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const resolvedColumns = [
    ...columns.slice(0, 3),
    ...visibleColumns.map((key) => optionalColumns[key]).filter(Boolean),
    columns[3],
    columns[4],
  ];


  if (loading) {
    return <Card loading={true}>加载中...</Card>;
  }

  return (
    <Card>
      {/* 顶部操作栏 */}
      <div style={{ marginBottom: 16 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/tasks')}>
            返回列表
          </Button>
        </Space>
      </div>

      {/* 操作按钮 */}
      <div style={{ marginBottom: 16 }}>
        <Space wrap>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleAdd}
            disabled={confirmed || saving}
          >
            添加功能点
          </Button>
          <Popover
            placement="bottom"
            content={(
              <Checkbox.Group
                value={visibleColumns}
                onChange={(values) => setVisibleColumns(values)}
                options={[
                  { label: '业务描述', value: '业务描述' },
                  { label: '输入', value: '输入' },
                  { label: '输出', value: '输出' },
                  { label: '依赖项', value: '依赖项' },
                  { label: '备注', value: '备注' },
                ]}
              />
            )}
            title="列设置"
          >
            <Button>列设置</Button>
          </Popover>
          {!singleSystemLocked && (
            <Dropdown
              menu={{
                items: systemActionMenuItems,
                onClick: handleSystemActionMenuClick,
              }}
              trigger={['click']}
            >
              <Button>
                系统操作 <DownOutlined />
              </Button>
            </Dropdown>
          )}
          <Button
            icon={<HistoryOutlined />}
            onClick={() => setHistoryVisible(true)}
          >
            修改历史
          </Button>
          {!confirmed && (
            <Popconfirm
              title="提交后将等待管理员分配专家，提交后无法继续编辑"
              onConfirm={handleConfirm}
              okText="提交"
              cancelText="取消"
            >
              <Button
                type="primary"
                icon={<CheckOutlined />}
                loading={loading}
                disabled={saving}
              >
                提交给管理员
              </Button>
            </Popconfirm>
          )}
        </Space>
      </div>

      {singleSystemLocked && (
        <div style={{ marginBottom: 16 }}>
          <Space wrap>
            <Tag color="blue">单系统锁定</Tag>
            <Text type="secondary">
              {`待评估系统：${targetSystemDisplay || '-'}。系统级新增、重命名、删除和重新拆分已禁用；功能点级编辑和重估仍可使用。`}
            </Text>
          </Space>
        </div>
      )}

      {/* 系统Tab页 */}
      <Tabs
        activeKey={currentSystem}
        onChange={setCurrentSystem}
        items={Object.keys(systemsData).map(system => ({
          label: system,
          key: system,
          children: (
            <Table
              columns={resolvedColumns}
              dataSource={systemsData[system]}
              rowKey={(record, index) => index}
              pagination={false}
              scroll={{ x: 1200 }}
            />
          ),
        }))}
      />

      {/* 编辑/添加Modal */}
      <Modal
        title={editingIndex === null ? '添加新功能点' : '编辑功能点'}
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        onOk={editingIndex === null ? handleAddSave : handleEditSave}
        confirmLoading={saving}
        width={600}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="功能模块"
                name="功能模块"
                rules={[{ required: true, message: '请输入功能模块' }]}
              >
                <Input placeholder="例如：账户管理" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="功能点"
                name="功能点"
                rules={[{ required: true, message: '请输入功能点' }]}
              >
                <Input placeholder="例如：开立个人账户" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            label="业务描述"
            name="业务描述"
            rules={[{ required: true, message: '请输入业务描述' }]}
          >
            <TextArea rows={4} placeholder="详细描述该功能点的业务需求..." />
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                label="输入"
                name="输入"
              >
                <TextArea rows={2} placeholder="输入项，多个用、或换行分隔" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="输出"
                name="输出"
              >
                <TextArea rows={2} placeholder="输出项，多个用、或换行分隔" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="依赖项"
                name="依赖项"
              >
                <TextArea rows={2} placeholder="依赖项，多个用、或换行分隔" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="预估人天"
                name="预估人天"
                rules={isManager ? [] : [
                  { required: true, message: '请输入预估人天' },
                  { type: 'number', min: 0.5, max: 5, message: '人天范围: 0.5-5' }
                ]}
              >
                <InputNumber
                  step={0.5}
                  min={0.5}
                  max={5}
                  disabled={isManager}
                  placeholder={isManager ? '项目经理角色只读' : '建议范围: 0.5-5'}
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      <Modal
        title="新增系统Tab（默认自动拆分）"
        open={addSystemVisible}
        onCancel={() => setAddSystemVisible(false)}
        onOk={async () => {
          const values = await addSystemForm.validateFields();
          await submitAddSystem(values);
        }}
        confirmLoading={addingSystem}
        okText="新增并拆分"
        cancelText="取消"
      >
        <Form
          form={addSystemForm}
          layout="vertical"
          initialValues={{ type: '主系统', auto_breakdown: true }}
        >
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                label="系统名称"
                name="name"
                rules={[{ required: true, message: '请输入系统名称' }]}
              >
                <AutoComplete
                  options={systemSuggestions}
                  placeholder="输入系统名称（可直接输入，也可从候选/系统清单提示中选择）"
                  filterOption={(inputValue, option) =>
                    (option?.value || '').toUpperCase().includes((inputValue || '').toUpperCase())
                  }
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item label="系统类型" name="type">
                <Select
                  options={[
                    { label: '主系统', value: '主系统' },
                    { label: '子系统', value: '子系统' },
                    { label: '上游系统', value: '上游系统' },
                    { label: '下游系统', value: '下游系统' },
                    { label: '配合系统', value: '配合系统' },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item label="拆分方式" name="auto_breakdown" valuePropName="checked">
                <Checkbox>新增后自动拆分功能点</Checkbox>
              </Form.Item>
            </Col>
          </Row>
          <Text type="secondary">
            提示：即使自动拆分失败，也会保留系统Tab，便于你手工补齐功能点。
          </Text>
        </Form>
      </Modal>

      <Modal
        title="重命名系统"
        open={renameVisible}
        onCancel={() => setRenameVisible(false)}
        onOk={handleRenameSystem}
        confirmLoading={saving}
        okText="保存"
        cancelText="取消"
      >
        <Form layout="vertical">
          <Form.Item label="新系统名称">
            <Input
              value={newSystemName}
              onChange={(e) => setNewSystemName(e.target.value)}
              placeholder="请输入新的系统名称"
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 修改历史Modal */}
      <Modal
        title="修改历史"
        open={historyVisible}
        onCancel={() => setHistoryVisible(false)}
        footer={[
          <Button key="close" onClick={() => setHistoryVisible(false)}>
            关闭
          </Button>
        ]}
        width={900}
      >
        <Table
          columns={[
            {
              title: '时间',
              dataIndex: 'timestamp',
              key: 'timestamp',
              width: 180,
            },
            {
              title: '操作',
              dataIndex: 'operation',
              key: 'operation',
              width: 80,
              render: (op) => {
                const opMap = {
                  add: '添加',
                  update: '修改',
                  delete: '删除',
                  add_system: '新增系统',
                  rebreakdown_system: '重新拆分',
                  rename_system: '重命名系统',
                  delete_system: '删除系统'
                };
                const colorMap = {
                  add: 'green',
                  update: 'blue',
                  delete: 'red',
                  add_system: 'geekblue',
                  rebreakdown_system: 'purple',
                  rename_system: 'orange',
                  delete_system: 'red'
                };
                return <Tag color={colorMap[op]}>{opMap[op]}</Tag>;
              },
            },
            {
              title: '系统',
              dataIndex: 'system',
              key: 'system',
              width: 150,
            },
            {
              title: '字段',
              dataIndex: 'field',
              key: 'field',
              width: 100,
              render: (field) => field || '-',
            },
            {
              title: '旧值',
              dataIndex: 'old_value',
              key: 'old_value',
              width: 150,
              render: (val) => val !== undefined ? String(val) : '-',
            },
            {
              title: '新值',
              dataIndex: 'new_value',
              key: 'new_value',
              width: 150,
              render: (val) => val !== undefined ? String(val) : '-',
            },
          ]}
          dataSource={modifications}
          rowKey="id"
          pagination={{ pageSize: 10 }}
          scroll={{ x: 900 }}
        />
      </Modal>
    </Card>
  );
};

export default EditPage;
