# 超声语音报告填充系统

## 启动方式

### 1. 安装后端依赖
```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置 API Key
编辑 `backend/.env`，填入 DeepSeek API Key:
```
DEEPSEEK_API_KEY=你的key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
```

### 3. 启动后端
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. 打开模拟页面
浏览器打开根目录下的 `mock_pacs.html`

### 5. 安装 Chrome 插件 (可选)
1. 打开 `chrome://extensions/`
2. 开启"开发者模式"
3. 点击"加载已解压的扩展程序"
4. 选择 `extension/` 文件夹

插件会自动在 PACS 页面右侧注入语音助手侧边栏。

## API 接口

```
POST /api/v1/analyze-voice?exam_part=breast
POST /api/v1/analyze-voice?exam_part=abdominal
```

支持的科室: `breast` (乳腺), `abdominal` (腹部肝胆)

## 新增科室

1. 在 `backend/app/templates/` 下创建 `xxx.py`
2. 定义 Schema + Few-Shot
3. 在 `__init__.py` 的 TEMPLATE_REGISTRY 中注册
4. 在 `mock_pacs.html` 添加对应 input 字段
