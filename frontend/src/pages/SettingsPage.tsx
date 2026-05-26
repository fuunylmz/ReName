import { AutoComplete, Button, Card, Form, Input, Radio, Space, message } from 'antd';
import { useEffect, useState } from 'react';
import { api, type AppSettings, type LLMModel } from '../api/client';

const emptySettings: AppSettings = {
  tmdb_api_key: '',
  tmdb_language: 'zh-CN',
  llm_api_base_url: '',
  llm_api_key: '',
  llm_model: '',
  default_operation: 'hardlink',
  movie_library_path: '',
  tv_library_path: '',
  anime_library_path: '',
  download_paths: [],
};

export function SettingsPage() {
  const [form] = Form.useForm<AppSettings & { download_paths_text: string }>();
  const [loading, setLoading] = useState(false);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [llmModels, setLlmModels] = useState<LLMModel[]>([]);

  useEffect(() => {
    api.getSettings().then((settings) => {
      form.setFieldsValue({ ...settings, download_paths_text: settings.download_paths.join('\n') });
    });
  }, [form]);

  async function save() {
    setLoading(true);
    try {
      const values = form.getFieldsValue();
      await api.updateSettings({
        ...emptySettings,
        ...values,
        download_paths: values.download_paths_text?.split('\n').map((item) => item.trim()).filter(Boolean) ?? [],
      });
      message.success('设置已保存');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '保存失败');
    } finally {
      setLoading(false);
    }
  }

  async function fetchLLMModels() {
    const apiBaseUrl = form.getFieldValue('llm_api_base_url')?.trim();
    const apiKey = form.getFieldValue('llm_api_key')?.trim() ?? '';
    if (!apiBaseUrl) {
      message.warning('请先填写 LLM API Base URL');
      return;
    }

    setModelsLoading(true);
    try {
      const result = await api.listLLMModels(apiBaseUrl, apiKey);
      setLlmModels(result.models);
      if (result.models.length === 0) {
        message.warning('端点可访问，但没有返回模型');
      } else {
        message.success(`已获取 ${result.models.length} 个模型`);
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : '获取模型失败');
    } finally {
      setModelsLoading(false);
    }
  }

  return (
    <Card title="系统设置">
      <Form layout="vertical" form={form} initialValues={{ ...emptySettings, download_paths_text: '' }}>
        <Form.Item label="下载目录，每行一个" name="download_paths_text">
          <Input.TextArea rows={3} placeholder="D:\\Downloads" />
        </Form.Item>
        <Space style={{ width: '100%' }} align="start">
          <Form.Item label="电影媒体库目录" name="movie_library_path">
            <Input placeholder="D:\\Media\\Movies" style={{ width: 360 }} />
          </Form.Item>
          <Form.Item label="电视剧媒体库目录" name="tv_library_path">
            <Input placeholder="D:\\Media\\TV Shows" style={{ width: 360 }} />
          </Form.Item>
          <Form.Item label="动漫媒体库目录" name="anime_library_path">
            <Input placeholder="D:\\Media\\Anime" style={{ width: 360 }} />
          </Form.Item>
        </Space>
        <Space style={{ width: '100%' }} align="start">
          <Form.Item label="TMDB API Key" name="tmdb_api_key">
            <Input.Password style={{ width: 360 }} />
          </Form.Item>
          <Form.Item label="TMDB 语言" name="tmdb_language">
            <Input style={{ width: 180 }} />
          </Form.Item>
        </Space>
        <Space style={{ width: '100%' }} align="start">
          <Form.Item label="LLM API Base URL" name="llm_api_base_url">
            <Input placeholder="https://api.openai.com/v1" style={{ width: 360 }} />
          </Form.Item>
          <Form.Item label="LLM API Key" name="llm_api_key">
            <Input.Password style={{ width: 260 }} />
          </Form.Item>
          <Form.Item label="模型列表">
            <Button loading={modelsLoading} onClick={fetchLLMModels}>
              获取模型
            </Button>
          </Form.Item>
        </Space>
        <Form.Item label="LLM 模型" name="llm_model">
          <AutoComplete
            allowClear
            placeholder="可手动输入或点击获取模型后选择，例如 gpt-4o-mini"
            style={{ width: 420 }}
            options={llmModels.map((model) => ({
              label: model.owned_by ? `${model.id} / ${model.owned_by}` : model.id,
              value: model.id,
            }))}
            filterOption={(input, option) => String(option?.label ?? '').toLowerCase().includes(input.toLowerCase())}
            popupMatchSelectWidth={false}
          />
        </Form.Item>
        <Form.Item label="默认文件操作" name="default_operation">
          <Radio.Group>
            <Radio.Button value="hardlink">硬链接</Radio.Button>
            <Radio.Button value="copy">复制</Radio.Button>
            <Radio.Button value="move">移动</Radio.Button>
          </Radio.Group>
        </Form.Item>
        <Button type="primary" loading={loading} onClick={save}>
          保存设置
        </Button>
      </Form>
    </Card>
  );
}
