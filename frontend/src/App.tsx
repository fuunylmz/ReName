import { DatabaseOutlined, SettingOutlined, ToolOutlined } from '@ant-design/icons';
import { Layout, Menu, Typography, theme } from 'antd';
import { useMemo, useState } from 'react';
import type { MediaItem } from './api/client';
import { MediaPage } from './pages/MediaPage';
import { ReviewPage } from './pages/ReviewPage';
import { SettingsPage } from './pages/SettingsPage';

const { Header, Content, Sider } = Layout;

type PageKey = 'media' | 'review' | 'settings';

export default function App() {
  const [page, setPage] = useState<PageKey>('media');
  const [selectedItem, setSelectedItem] = useState<MediaItem | null>(null);
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  const content = useMemo(() => {
    if (page === 'settings') return <SettingsPage />;
    if (page === 'review') return <ReviewPage item={selectedItem} />;
    return (
      <MediaPage
        onSelect={(item) => {
          setSelectedItem(item);
          setPage('review');
        }}
      />
    );
  }, [page, selectedItem]);

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider width={220}>
        <Typography.Title level={3} style={{ color: '#fff', padding: '20px 24px', margin: 0 }}>
          ReName
        </Typography.Title>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[page]}
          onClick={(event) => setPage(event.key as PageKey)}
          items={[
            { key: 'media', icon: <DatabaseOutlined />, label: '媒体扫描' },
            { key: 'review', icon: <ToolOutlined />, label: '识别与预览' },
            { key: 'settings', icon: <SettingOutlined />, label: '设置' },
          ]}
        />
      </Sider>
      <Layout>
        <Header style={{ background: colorBgContainer }}>
          <Typography.Text strong>BT 资源刮削与 Emby 命名转换工具</Typography.Text>
        </Header>
        <Content style={{ margin: 24, padding: 24, background: colorBgContainer, borderRadius: borderRadiusLG }}>
          {content}
        </Content>
      </Layout>
    </Layout>
  );
}
