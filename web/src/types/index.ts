// ============================================================
// B: 核心领域类型定义
// ============================================================

import type { Node, Edge } from '@xyflow/react'

// ---- 基础标识 ----
export type ID = string

// ---- 节点状态机 ----
export type NodeStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed'

// ---- 图片/视频引用 ----
export interface ImageRef {
  id: ID
  url: string          // 生成结果 URL
  thumbnailUrl: string // 缩略图
  prompt: string       // 生成时使用的提示词
  model: string        // 模型名称
  createdAt: number
  /** 是否为尾帧 (用于视频节点间传递) */
  isTailFrame?: boolean
}

export interface VideoRef {
  id: ID
  url: string
  thumbnailUrl: string
  duration: number     // 秒
  prompt: string
  model: string
  createdAt: number
  /** 尾帧图片 (供下一段视频参考) */
  tailFrame?: ImageRef
}

// ---- 角色资产属性 ----
export interface CharacterAttributes {
  hairStyle: string
  clothing: string
  expression: string
  bodyType: string
}

// ---- 角色资产 ----
export interface CharacterAsset {
  id: ID
  type: 'character'
  name: string
  description: string           // 原始形象描述
  model: string                 // 生成模型
  mainImage: ImageRef | null    // 主造型图
  threeViewGrid: ImageRef | null // 九宫格三式图
  attributes: CharacterAttributes
  variants: {
    leftProfile: ImageRef | null   // 左侧胸像
    rightProfile: ImageRef | null  // 右侧全身像
    expressions: ImageRef[]        // 神态变体
  }
  createdAt: number
  updatedAt: number
}

// ---- 场景锚点 ----
export interface SceneAnchorSettings {
  lighting: string    // 光影: 暖调光影 | 丁达尔光线 | 柔和散射光 | ...
  colorTone: string   // 色调: 暖色调 | 冷色调 | 中性 | ...
  texture: string     // 质感: 细腻空气感 | 极简材质 | 电影质感 | ...
  mood: string        // 情绪: 温馨 | 悬疑 | 庄严 | 浪漫 | ...
}

// ---- 场景资产 ----
export interface SceneAsset {
  id: ID
  type: 'scene'
  name: string
  description: string            // 环境描述
  baseImage: ImageRef | null     // 空场景图
  anchorSettings: SceneAnchorSettings
  styledImage: ImageRef | null   // 风格化后的场景图
  createdAt: number
  updatedAt: number
}

// ---- 资产联合类型 ----
export type Asset = CharacterAsset | SceneAsset

// ---- 图片节点 ----
export interface ImageNodeData {
  label: string
  description: string
  nodeType: 'image'
  /** 'character' 生成角色 | 'scene' 生成场景 | 'style' 风格化 */
  purpose: 'character' | 'scene' | 'style'
  prompt: string
  model: string
  result: ImageRef | null
  status: NodeStatus
  /** 引用的角色/场景资产 ID */
  assetRefs: ID[]
}

// ---- 视频节点 ----
export interface VideoNodeData {
  label: string
  description: string
  nodeType: 'video'
  shotScript: string         // 分镜提示词
  characterRef: ID | null    // 角色资产引用
  sceneRef: ID | null        // 场景锚点引用
  previousFrameRef: ID | null // 上一段尾帧引用 (节点 ID)
  duration: number           // 时长 (默认 15s)
  result: VideoRef | null
  tailFrame: ImageRef | null // 本段尾帧
  status: NodeStatus
  order: number              // 分镜序号
}

// ---- 节点数据联合类型 ----
export type AppNodeData = ImageNodeData | VideoNodeData

// ---- 自定义节点类型 ----
export type AppNode = Node<AppNodeData, 'imageNode' | 'videoNode'>

// ---- 边类型 ----
export type EdgeType = 'character_ref' | 'scene_ref' | 'frame_continuity' | 'data_flow'

export interface AppEdgeData {
  edgeType: EdgeType
  label?: string
}

export type AppEdge = Edge<AppEdgeData>

// ---- 脚本分镜段 ----
export interface ScriptSegment {
  id: ID
  order: number
  script: string           // 该段分镜文本
  duration: number         // 预计时长
  characterRefs: ID[]      // 引用的角色 ID
  sceneRef: ID | null      // 引用的场景 ID
  parentSegmentId: ID | null // 上一段 ID，形成链式结构
  nodeId: ID | null        // 关联的画布节点 ID
}

// ---- 预设模板 ----
export interface StylePreset {
  id: ID
  name: string
  category: 'lighting' | 'colorTone' | 'texture'
  value: string
  description: string
}

// ---- 项目 ----
export interface Project {
  id: ID
  name: string
  description: string
  settings: {
    resolution: string      // 如 "1920x1080"
    frameRate: number       // 如 24
    defaultModel: string    // 如 "nano-pro"
    defaultDuration: number // 默认单段视频时长 (15s)
  }
  characters: CharacterAsset[]
  scenes: SceneAsset[]
  scriptSegments: ScriptSegment[]
  presets: StylePreset[]
  createdAt: number
  updatedAt: number
}

// ---- 生成管线上下文 ----
export interface GenerationContext {
  prompt: string
  model: string
  characterAssets: CharacterAsset[]
  sceneAssets: SceneAsset[]
  /** 尾帧图片 URL (视频生成时传入) */
  tailFrameUrl?: string
}

// ---- AI 模型适配器接口 ----
export interface AIModelAdapter {
  name: string
  generateImage(ctx: GenerationContext): Promise<ImageRef>
  generateVideo(ctx: GenerationContext): Promise<VideoRef>
}

// ---- 节点执行上下文 ----
export interface NodeExecutionContext {
  projectId: ID
  nodeId: ID
  assets: Asset[]
  previousTailFrame?: ImageRef
}

// ============================================================
// 预设数据
// ============================================================

export const LIGHTING_PRESETS: StylePreset[] = [
  { id: 'light-warm', name: '暖调光影', category: 'lighting', value: 'warm lighting, golden hour glow, soft shadows', description: '温馨温暖的光影氛围' },
  { id: 'light-tyndall', name: '丁达尔光线', category: 'lighting', value: 'tyndall effect, volumetric light rays, god rays', description: '可见光束穿透空间的戏剧效果' },
  { id: 'light-soft', name: '柔和散射光', category: 'lighting', value: 'soft diffused lighting, overcast light, gentle illumination', description: '均匀柔和的散射光' },
  { id: 'light-rim', name: '轮廓光', category: 'lighting', value: 'rim lighting, backlit, hair light, edge glow', description: '人物边缘发光突出立体感' },
  { id: 'light-neon', name: '霓虹冷光', category: 'lighting', value: 'neon lighting, cyberpunk glow, colored artificial light', description: '赛博朋克风格彩光' },
]

export const COLOR_TONE_PRESETS: StylePreset[] = [
  { id: 'tone-warm', name: '暖色调', category: 'colorTone', value: 'warm color tone, orange and amber hues, cozy atmosphere', description: '橙黄基调' },
  { id: 'tone-cool', name: '冷色调', category: 'colorTone', value: 'cool color tone, blue and teal hues, crisp atmosphere', description: '蓝青基调' },
  { id: 'tone-neutral', name: '中性色调', category: 'colorTone', value: 'neutral color tone, balanced colors, natural look', description: '自然中性' },
]

export const TEXTURE_PRESETS: StylePreset[] = [
  { id: 'tex-fine-air', name: '细腻空气感', category: 'texture', value: 'fine airy texture, ethereal atmosphere, delicate grain', description: '轻盈通透' },
  { id: 'tex-minimal', name: '极简材质', category: 'texture', value: 'minimalist materials, clean surfaces, modern simplicity', description: '简洁现代' },
  { id: 'tex-cinematic', name: '电影质感', category: 'texture', value: 'cinematic texture, film grain, anamorphic look', description: '电影般质感' },
]

export const DEFAULT_PROJECT_SETTINGS: Project['settings'] = {
  resolution: '1920x1080',
  frameRate: 24,
  defaultModel: 'nano-pro',
  defaultDuration: 15,
}

export const DEFAULT_SCENE_ANCHOR: SceneAnchorSettings = {
  lighting: '',
  colorTone: '',
  texture: '',
  mood: '',
}
