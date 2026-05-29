// ============================================================
// AI 模型适配器 - Mock 实现
// ============================================================

import type { AIModelAdapter, GenerationContext, ImageRef, VideoRef } from '@/types'
import { v4 as uuid } from 'uuid'

// 模拟延迟
function delay(ms: number) {
  return new Promise((r) => setTimeout(r, ms))
}

// 模拟图片 URL (占位图)
function placeholderImage(text: string, color = '7c3aed'): string {
  return `https://placehold.co/600x400/${color}/white?text=${encodeURIComponent(text)}`
}

function placeholderVideo(text: string): string {
  return `https://placehold.co/1920x1080/1e1b4b/white?text=${encodeURIComponent(text)}`
}

class MockAdapter implements AIModelAdapter {
  name = 'mock-adapter'

  async generateImage(ctx: GenerationContext): Promise<ImageRef> {
    await delay(1500)

    let label = 'Generated Image'
    if (ctx.characterAssets.length > 0) {
      label = ctx.characterAssets[0].name
    } else if (ctx.sceneAssets.length > 0) {
      label = ctx.sceneAssets[0].name
    }

    const ref: ImageRef = {
      id: uuid(),
      url: placeholderImage(label),
      thumbnailUrl: placeholderImage(label + ' (thumb)', 'a78bfa'),
      prompt: ctx.prompt,
      model: ctx.model,
      createdAt: Date.now(),
    }
    return ref
  }

  async generateVideo(ctx: GenerationContext): Promise<VideoRef> {
    await delay(3000)

    const ref: VideoRef = {
      id: uuid(),
      url: placeholderVideo(ctx.prompt.slice(0, 30)),
      thumbnailUrl: placeholderImage('Video Thumbnail'),
      duration: 15,
      prompt: ctx.prompt,
      model: ctx.model,
      createdAt: Date.now(),
      tailFrame: {
        id: uuid(),
        url: placeholderImage('Tail Frame', 'f59e0b'),
        thumbnailUrl: placeholderImage('Tail Frame', 'f59e0b'),
        prompt: 'Tail frame from generated video',
        model: ctx.model,
        createdAt: Date.now(),
        isTailFrame: true,
      },
    }
    return ref
  }
}

// 适配器注册表
const adapters: Record<string, AIModelAdapter> = {
  'mock-adapter': new MockAdapter(),
}

export function getAdapter(model: string): AIModelAdapter {
  // 目前统一返回 mock，后续可按 model 名称分发
  return adapters['mock-adapter']
}

export { MockAdapter }
