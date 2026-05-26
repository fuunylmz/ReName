import { Alert, Button, Card, Descriptions, Empty, Image, List, Popconfirm, Radio, Space, Table, Tag, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import { api, type MediaItem, type ParsedResult, type RenamePlan, type TmdbMatch } from '../api/client';

interface Props {
  item: MediaItem | null;
}

export function ReviewPage({ item }: Props) {
  const [parsed, setParsed] = useState<ParsedResult | null>(null);
  const [matches, setMatches] = useState<TmdbMatch[]>([]);
  const [plans, setPlans] = useState<RenamePlan[]>([]);
  const [operation, setOperation] = useState<'hardlink' | 'copy' | 'move'>('hardlink');
  const [loading, setLoading] = useState(false);
  const [llmOutput, setLlmOutput] = useState('');
  const [streamMessage, setStreamMessage] = useState('');
  const [showLlmOutput, setShowLlmOutput] = useState(true);

  async function loadRelated(id: number) {
    const [parsedResults, tmdbMatches, renamePlans] = await Promise.all([
      api.listParsedResults(id),
      api.listMatches(id),
      api.listRenamePlans(id),
    ]);
    setParsed(parsedResults[0] ?? null);
    setMatches(tmdbMatches);
    setPlans(renamePlans);
  }

  useEffect(() => {
    if (item) {
      loadRelated(item.id);
    }
  }, [item]);

  useEffect(() => {
    api.getSettings().then((settings) => {
      if (['hardlink', 'copy', 'move'].includes(settings.default_operation)) {
        setOperation(settings.default_operation as 'hardlink' | 'copy' | 'move');
      }
    });
  }, []);

  if (!item) {
    return <Empty description="请先在媒体扫描页面选择一个资源" />;
  }

  const currentItem = item;

  async function runParse() {
    setLoading(true);
    setLlmOutput('');
    setStreamMessage('');
    setShowLlmOutput(true);
    try {
      const response = await fetch(api.parseMediaItemStreamUrl(currentItem.id), { method: 'POST' });
      if (!response.ok || !response.body) {
        throw new Error('解析请求失败');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() ?? '';
        for (const rawEvent of events) {
          handleStreamEvent(rawEvent);
        }
      }
      if (buffer.trim()) {
        handleStreamEvent(buffer);
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : '解析失败');
    } finally {
      setLoading(false);
    }
  }

  function handleStreamEvent(rawEvent: string) {
    const lines = rawEvent.split('\n');
    const event = lines.find((line) => line.startsWith('event:'))?.replace('event:', '').trim();
    const dataText = lines
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.replace('data:', '').trim())
      .join('\n');
    if (!event || !dataText) return;

    const data = JSON.parse(dataText) as { content?: string; message?: string; raw_content?: string } | ParsedResult;
    if (event === 'delta' && 'content' in data && data.content) {
      setLlmOutput((previous) => previous + data.content);
      return;
    }
    if (event === 'result') {
      setParsed(data as ParsedResult);
      message.success('解析完成');
      return;
    }
    if (event === 'fallback' && 'message' in data) {
      setStreamMessage(data.message ?? '已使用规则解析');
      return;
    }
    if (event === 'start' && 'message' in data) {
      setStreamMessage(data.message ?? '开始调用 LLM');
      return;
    }
    if (event === 'error' && 'message' in data) {
      if (data.raw_content) setLlmOutput(data.raw_content);
      message.error(data.message ?? '解析失败');
    }
  }

  async function runMatch() {
    setLoading(true);
    try {
      const result = await api.matchMediaItem(currentItem.id);
      setMatches(result);
      message.success(result.length ? '匹配完成' : '没有返回候选，请检查 TMDB 设置');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '匹配失败');
    } finally {
      setLoading(false);
    }
  }

  async function selectMatch(matchId: number) {
    await api.selectMatch(currentItem.id, matchId);
    await loadRelated(currentItem.id);
    message.success('已选择匹配');
  }

  async function createPlan() {
    setLoading(true);
    try {
      const plan = await api.createRenamePlan(currentItem.id, operation);
      setPlans([plan, ...plans]);
      message.success('重命名计划已生成');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '生成失败');
    } finally {
      setLoading(false);
    }
  }

  async function executeLatestPlan() {
    if (!latestPlan) return;
    setLoading(true);
    try {
      const executedPlan = await api.executeRenamePlan(latestPlan.id);
      setPlans((previous) => previous.map((plan) => (plan.id === executedPlan.id ? executedPlan : plan)));
      message.success(operation === 'hardlink' ? '硬链接已创建' : '文件操作已完成');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '执行失败');
    } finally {
      setLoading(false);
    }
  }

  const latestPlan = plans[0];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Card title="资源信息">
        <Descriptions column={1} bordered size="small">
          <Descriptions.Item label="原始名称">{currentItem.raw_name}</Descriptions.Item>
          <Descriptions.Item label="路径">{currentItem.source_path}</Descriptions.Item>
          <Descriptions.Item label="视频文件">{currentItem.video_files.join('\n')}</Descriptions.Item>
        </Descriptions>
        <Space style={{ marginTop: 16 }}>
          <Button type="primary" loading={loading} onClick={runParse}>
            LLM / 规则解析
          </Button>
          <Button loading={loading} onClick={runMatch} disabled={!parsed}>
            查询 TMDB
          </Button>
        </Space>
      </Card>

      <Card title="解析结果">
        {streamMessage ? <Alert type="info" showIcon message={streamMessage} style={{ marginBottom: 16 }} /> : null}
        {llmOutput ? (
          <Card
            size="small"
            title="LLM 流式输出"
            extra={
              <Button size="small" type="link" onClick={() => setShowLlmOutput((value) => !value)}>
                {showLlmOutput ? '隐藏' : '展示'}
              </Button>
            }
            style={{ marginBottom: 16 }}
          >
            {showLlmOutput ? (
              <Typography.Paragraph style={{ whiteSpace: 'pre-wrap', marginBottom: 0 }}>
                {llmOutput}
              </Typography.Paragraph>
            ) : null}
          </Card>
        ) : null}
        {parsed ? (
          <Descriptions bordered size="small">
            <Descriptions.Item label="类型">{parsed.media_type}</Descriptions.Item>
            <Descriptions.Item label="标题">{parsed.title}</Descriptions.Item>
            <Descriptions.Item label="年份">{parsed.year ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="季号">{parsed.season ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="质量">{parsed.quality || '-'}</Descriptions.Item>
            <Descriptions.Item label="置信度">{Math.round(parsed.confidence * 100)}%</Descriptions.Item>
          </Descriptions>
        ) : (
          <Empty description="尚未解析" />
        )}
      </Card>

      <Card title="TMDB 候选">
        <List
          dataSource={matches}
          locale={{ emptyText: '暂无候选' }}
          renderItem={(match) => (
            <List.Item
              actions={[
                <Button key="select" type={match.selected ? 'primary' : 'default'} onClick={() => selectMatch(match.id)}>
                  {match.selected ? '已选择' : '选择'}
                </Button>,
              ]}
            >
              <List.Item.Meta
                avatar={
                  match.poster_path ? (
                    <Image
                      src={`https://image.tmdb.org/t/p/w185${match.poster_path}`}
                      width={72}
                      height={108}
                      style={{ objectFit: 'cover', borderRadius: 4 }}
                      preview={{ src: `https://image.tmdb.org/t/p/w500${match.poster_path}` }}
                    />
                  ) : (
                    <div
                      style={{
                        width: 72,
                        height: 108,
                        borderRadius: 4,
                        background: '#f0f0f0',
                        color: '#999',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 12,
                      }}
                    >
                      无海报
                    </div>
                  )
                }
                title={
                  <Space>
                    {match.title}
                    <Tag>{match.media_type}</Tag>
                    <Tag color="green">{Math.round(match.score * 100)}%</Tag>
                  </Space>
                }
                description={`${match.year ?? '-'} / TMDB ID: ${match.tmdb_id} / ${match.overview || '无简介'}`}
              />
            </List.Item>
          )}
        />
      </Card>

      <Card title="重命名预览">
        <Space style={{ marginBottom: 16 }}>
          <Radio.Group value={operation} onChange={(event) => setOperation(event.target.value)}>
            <Radio.Button value="hardlink">硬链接</Radio.Button>
            <Radio.Button value="copy">复制</Radio.Button>
            <Radio.Button value="move">移动</Radio.Button>
          </Radio.Group>
          <Button type="primary" loading={loading} onClick={createPlan}>
            生成预览
          </Button>
          <Popconfirm
            title="确认执行文件操作？"
            description={operation === 'hardlink' ? '将按预览路径创建硬链接，原文件不会被删除。' : '将按当前选择执行文件操作。'}
            okText="执行"
            cancelText="取消"
            onConfirm={executeLatestPlan}
            disabled={!latestPlan || latestPlan.status === 'completed'}
          >
            <Button danger loading={loading} disabled={!latestPlan || latestPlan.status === 'completed'}>
              {latestPlan?.status === 'completed' ? '已执行' : operation === 'hardlink' ? '执行硬链接' : '执行操作'}
            </Button>
          </Popconfirm>
        </Space>
        <Table
          rowKey="source"
          dataSource={latestPlan?.plan ?? []}
          columns={[
            {
              title: '原路径',
              dataIndex: 'source',
              ellipsis: true,
              render: (value: string) => <Typography.Text copyable>{value}</Typography.Text>,
            },
            {
              title: '目标路径',
              dataIndex: 'target',
              ellipsis: true,
              render: (value: string) => <Typography.Text copyable>{value}</Typography.Text>,
            },
          ]}
        />
      </Card>
    </Space>
  );
}
