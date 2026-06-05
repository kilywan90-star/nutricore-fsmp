import { z } from "zod";

const envSchema = z.object({
  // 新版通用 LLM 配置 (推荐)
  LLM_API_KEY: z.string().min(1).optional(),
  LLM_BASE_URL: z.string().optional(),
  LLM_MODEL: z.string().optional(),
  // 旧版百炼配置 (向后兼容)
  DASHSCOPE_API_KEY: z.string().min(1).optional(),
  AMAP_API_KEY: z.string().optional(),
  PORT: z.coerce.number().default(3000),
});

function validateEnv() {
  const result = envSchema.safeParse(process.env);
  if (!result.success) {
    console.error("Environment validation failed:");
    for (const issue of result.error.issues) {
      console.error(`  - ${issue.path.join(".")}: ${issue.message}`);
    }
    throw new Error("Environment validation failed");
  }
  const apiKey = result.data.LLM_API_KEY || result.data.DASHSCOPE_API_KEY;
  if (!apiKey) {
    console.warn("[env] No LLM API key set, LLM features disabled (regex fallback active)");
  }
  if (!result.data.AMAP_API_KEY) {
    console.warn("[env] AMAP_API_KEY not set, map features will be disabled");
  }
  return { ...result.data, apiKey };
}

export const env = validateEnv();

// DeepSeek 默认配置
const DEEPSEEK_BASE_URL = "https://api.deepseek.com";
const DEEPSEEK_MODEL = "deepseek-chat";

// 百炼默认配置 (向后兼容)
const DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1";
const DASHSCOPE_MODEL = "qwen-plus";

// 根据配置自动选择:
// - 设置了 LLM_MODEL/LLM_BASE_URL → 使用自定义
// - 设置了 LLM_API_KEY (非百炼) → 默认按 DeepSeek 配置
// - 仅设置了 DASHSCOPE_API_KEY → 使用百炼配置

export function getLLMConfig(): { baseURL: string; model: string; apiKey: string } {
  const apiKey = env.apiKey || "";
  const model = env.LLM_MODEL || (env.LLM_API_KEY ? DEEPSEEK_MODEL : DASHSCOPE_MODEL);
  const baseURL = env.LLM_BASE_URL || (env.LLM_API_KEY ? DEEPSEEK_BASE_URL : DASHSCOPE_BASE_URL);
  return { baseURL, model, apiKey };
}

export function isLLMAvailable(): boolean {
  return !!env.apiKey;
}
