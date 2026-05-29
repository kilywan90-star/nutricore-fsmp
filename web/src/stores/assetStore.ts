// ============================================================
// C2: 资产库状态管理 (角色 + 场景)
// ============================================================

import { create } from 'zustand'
import type {
  CharacterAsset,
  SceneAsset,
  CharacterAttributes,
  SceneAnchorSettings,
  StylePreset,
} from '@/types'
import {
  LIGHTING_PRESETS,
  COLOR_TONE_PRESETS,
  TEXTURE_PRESETS,
  DEFAULT_SCENE_ANCHOR,
} from '@/types'
import { v4 as uuid } from 'uuid'

interface AssetState {
  // 预设
  lightingPresets: StylePreset[]
  colorTonePresets: StylePreset[]
  texturePresets: StylePreset[]

  // 角色操作
  addCharacter: (name: string, description: string, model: string) => CharacterAsset
  updateCharacter: (id: string, updates: Partial<CharacterAsset>) => void
  removeCharacter: (id: string) => void
  getCharacter: (id: string) => CharacterAsset | undefined
  setCharacterMainImage: (id: string, imageRef: CharacterAsset['mainImage']) => void
  setCharacterThreeView: (id: string, imageRef: CharacterAsset['threeViewGrid']) => void

  // 场景操作
  addScene: (name: string, description: string) => SceneAsset
  updateScene: (id: string, updates: Partial<SceneAsset>) => void
  removeScene: (id: string) => void
  getScene: (id: string) => SceneAsset | undefined
  setSceneBaseImage: (id: string, imageRef: SceneAsset['baseImage']) => void
  setSceneStyledImage: (id: string, imageRef: SceneAsset['styledImage']) => void
  updateSceneAnchor: (id: string, anchor: Partial<SceneAnchorSettings>) => void
}

export const useAssetStore = create<AssetState>((set, get) => ({
  lightingPresets: LIGHTING_PRESETS,
  colorTonePresets: COLOR_TONE_PRESETS,
  texturePresets: TEXTURE_PRESETS,

  // ---- 角色 ----

  addCharacter: (name, description, model) => {
    const character: CharacterAsset = {
      id: uuid(),
      type: 'character',
      name,
      description,
      model,
      mainImage: null,
      threeViewGrid: null,
      attributes: {
        hairStyle: '',
        clothing: '',
        expression: '',
        bodyType: '',
      },
      variants: {
        leftProfile: null,
        rightProfile: null,
        expressions: [],
      },
      createdAt: Date.now(),
      updatedAt: Date.now(),
    }
    // 通过 projectStore 更新 (在调用层处理)
    return character
  },

  updateCharacter: (id, updates) => {
    // 由调用方通过 projectStore 更新 projects 中的 characters 数组
    // 此方法为便利方法，实际操作在 projectStore 层
  },
  removeCharacter: () => {},
  getCharacter: () => undefined,
  setCharacterMainImage: () => {},
  setCharacterThreeView: () => {},

  // ---- 场景 ----

  addScene: (name, description) => {
    const scene: SceneAsset = {
      id: uuid(),
      type: 'scene',
      name,
      description,
      baseImage: null,
      anchorSettings: { ...DEFAULT_SCENE_ANCHOR },
      styledImage: null,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    }
    return scene
  },

  updateScene: () => {},
  removeScene: () => {},
  getScene: () => undefined,
  setSceneBaseImage: () => {},
  setSceneStyledImage: () => {},
  updateSceneAnchor: () => {},
}))
