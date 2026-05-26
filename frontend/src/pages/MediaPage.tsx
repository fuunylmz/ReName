import { Button, Card, Input, Space, Table, Tag, message } from 'antd';
import { useEffect, useState } from 'react';
import { api, type MediaItem } from '../api/client';

interface Props {
  onSelect: (item: MediaItem) => void;
}

export function MediaPage({ onSelect }: Props) {
  const [items, setItems] = useState<MediaItem[]>([]);
  const [path, setPath] = useState('');
  const [loading, setLoading] = useState(false);

  async function load() {
    setItems(await api.listMediaItems());
  }

  useEffect(() => {
    load();
  }, []);

  async function scan() {
    if (!path.trim()) {
      message.warning('请输入扫描目录');
      return;
    }
    setLoading(true);
    try {
      await api.scan(path.trim());
      await load();
      message.success('扫描完成');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '扫描失败');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card title="媒体扫描">
      <Space.Compact style={{ width: '100%', marginBottom: 16 }}>
        <Input value={path} onChange={(event) => setPath(event.target.value)} placeholder="输入 BT 下载目录" />
        <Button type="primary" loading={loading} onClick={scan}>
          扫描
        </Button>
      </Space.Compact>
      <Table
        rowKey="id"
        dataSource={items}
        columns={[
          { title: '原始名称', dataIndex: 'raw_name' },
          { title: '类型', dataIndex: 'media_type', render: (value) => <Tag>{value}</Tag> },
          { title: '状态', dataIndex: 'status', render: (value) => <Tag color="blue">{value}</Tag> },
          { title: '文件数', dataIndex: 'file_count' },
          { title: '路径', dataIndex: 'source_path', ellipsis: true },
          {
            title: '操作',
            render: (_, record) => (
              <Button type="link" onClick={() => onSelect(record)}>
                处理
              </Button>
            ),
          },
        ]}
      />
    </Card>
  );
}
