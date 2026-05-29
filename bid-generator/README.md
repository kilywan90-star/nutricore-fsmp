# 智能标书生成工具
基于AI大模型的本地桌面端标书生成工具，完全本地化运行，数据不泄露，帮助企业快速生成高质量的投标文件，提高投标效率，降低废标风险。
## 核心功能
### 📑 招标文件智能解析
- 支持PDF、Word、Excel等多种格式招标文件上传
- 自动提取招标要求、资质条件、评分标准、截止日期等核心信息
- 结构化展示招标要求，自动识别风险条款和陷阱
### 📚 企业知识库管理
- 支持企业资质、过往标书、项目案例、人员简历、产品参数等资料批量上传
- 自动分类打标，建立语义索引
- 智能检索，生成标书时自动匹配最合适的内容
### 🤖 AI智能生成
- 一键生成完整标书，包含商务标、技术标、价格标
- 基于企业知识库内容生成，引用真实资料，避免虚假信息
- 支持动态模板，自动适配不同行业、不同类型的招标要求
- 多模型支持：Claude 3、GPT-4、文心一言、通义千问等
### ✅ 智能校验
- 自动检查标书是否完全响应招标要求，避免漏项
- 对照评分标准逐一核对，给出优化建议
- 自动识别错别字、前后不一致、格式错误等问题
- 合规性检查，避免违反招投标法规导致废标
### 📝 富文本编辑
- 功能强大的在线编辑器，支持格式排版、表格、图片等
- 实时协作，多人可以同时编辑不同章节
- 版本管理，支持历史版本对比和回滚
### 📤 导出交付
- 支持导出Word、PDF等标准格式
- 自动排版，格式完全符合招标要求
- 支持分包导出，自动生成商务标、技术标、价格标
## 技术栈
### 前端
- Electron：跨平台桌面应用框架
- React 18 + TypeScript：前端框架
- Ant Design：UI组件库
- Tiptap：富文本编辑器
- Vite：构建工具
### 后端
- Python 3.11
- FastAPI：高性能API框架
- LangChain：AI应用开发框架
- SQLite + ChromaDB：本地数据库 + 向量数据库
- PyPDF / python-docx：文件处理库
## 安装说明
### 环境要求
- Node.js 18+
- Python 3.11+
### 开发环境搭建
1. 克隆项目到本地
```bash
git clone <repository-url>
cd bid-generator
```
2. 安装前端依赖
```bash
npm install
```
3. 安装Python后端依赖
```bash
cd backend
pip install -r requirements.txt
cd ..
```
4. 启动开发服务
```bash
npm run electron:dev
```
### 打包生产版本
```bash
# Windows
npm run electron:build -- --win
# Mac
npm run electron:build -- --mac
# Linux
npm run electron:build -- --linux
```
## 使用说明
1. 首次启动后，先到系统设置页面配置您的AI API Key（支持Anthropic、OpenAI等）
2. 到知识库页面上传您企业的资质文件、过往标书、项目案例等资料，系统会自动建立索引
3. 新建项目，填写项目基本信息，上传招标文件，系统会自动解析招标要求
4. 点击一键生成，系统会基于招标要求和您的知识库内容自动生成完整标书
5. 在编辑器中调整和完善生成的内容
6. 使用智能校验功能检查标书是否存在问题
7. 导出为Word或PDF格式，即可用于投标
## 隐私说明
- 所有数据都保存在您的本地电脑上，不会上传到任何服务器
- 调用AI生成时，仅会将生成所需的内容发送到对应的AI服务商API，请确保您的API Key安全
- 建议定期备份数据目录，避免数据丢失
## 目录结构
```
bid-generator/
├── electron/                 # Electron主进程代码
│   ├── main.js              # 主进程入口
│   ├── preload.js           # 预加载脚本
│   └── server-manager.js    # 后端服务管理
├── frontend/                # React前端代码
│   ├── src/
│   │   ├── components/      # 公共组件
│   │   ├── pages/           # 页面组件
│   │   ├── services/        # API调用
│   │   └── store/           # 状态管理
│   └── index.html
├── backend/                 # Python后端代码
│   ├── main.py              # FastAPI入口
│   ├── api/                 # API路由
│   ├── core/                # 核心功能
│   └── db/                  # 数据库操作
├── package.json             # 项目配置
└── README.md                # 项目说明
```
## 许可证
MIT License
