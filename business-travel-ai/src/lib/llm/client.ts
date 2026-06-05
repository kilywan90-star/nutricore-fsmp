import OpenAI from "openai";
import type { ChatCompletionMessageParam } from "openai/resources/chat/completions";
import { getLLMConfig } from "@/lib/env";

export class LLMError extends Error {
  code: "timeout" | "api_error" | "parse_error";
  constructor(message: string, code: "timeout" | "api_error" | "parse_error") {
    super(message);
    this.name = "LLMError";
    this.code = code;
  }
}

let _client: OpenAI | null = null;
let _config: ReturnType<typeof getLLMConfig> | null = null;

function getClient(): OpenAI {
  const config = getLLMConfig();
  if (!config.apiKey) {
    throw new LLMError("LLM_API_KEY not set, LLM features disabled", "api_error");
  }
  if (!_client || _config?.apiKey !== config.apiKey || _config?.baseURL !== config.baseURL) {
    _client = new OpenAI({
      apiKey: config.apiKey,
      baseURL: config.baseURL,
    });
    _config = config;
  }
  return _client;
}

export const isLLMAvailable = (): boolean => {
  const config = getLLMConfig();
  return !!config.apiKey;
};

export interface ChatOptions {
  temperature?: number;
  maxTokens?: number;
  timeout?: number;
}

export async function chatCompletion(
  messages: ChatCompletionMessageParam[],
  options: ChatOptions = {}
): Promise<string> {
  const client = getClient();
  const { temperature = 0.3, maxTokens = 1024, timeout = 8000 } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  try {
    const config = getLLMConfig();
    const response = await client.chat.completions.create(
      {
        model: config.model,
        messages,
        temperature,
        max_tokens: maxTokens,
      },
      { signal: controller.signal }
    );
    const content = response.choices[0]?.message?.content;
    if (!content) {
      throw new LLMError("Empty response from LLM", "api_error");
    }
    return content;
  } catch (err) {
    if (err instanceof LLMError) throw err;
    if (err instanceof Error && err.name === "AbortError") {
      throw new LLMError(`LLM request timed out after ${timeout}ms`, "timeout");
    }
    throw new LLMError(
      `LLM API error: ${err instanceof Error ? err.message : String(err)}`,
      "api_error"
    );
  } finally {
    clearTimeout(timer);
  }
}

export async function chatCompletionJSON<T>(
  messages: ChatCompletionMessageParam[],
  options: ChatOptions = {}
): Promise<T> {
  const client = getClient();
  const { temperature = 0.3, maxTokens = 1024, timeout = 8000 } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  try {
    const config = getLLMConfig();
    const response = await client.chat.completions.create(
      {
        model: config.model,
        messages,
        temperature,
        max_tokens: maxTokens,
        response_format: { type: "json_object" },
      },
      { signal: controller.signal }
    );
    const content = response.choices[0]?.message?.content;
    if (!content) {
      throw new LLMError("Empty response from LLM", "api_error");
    }
    try {
      return JSON.parse(content) as T;
    } catch (parseErr) {
      console.error("[LLM] JSON parse failed. Raw content (first 500 chars):", content.substring(0, 500));
      throw parseErr;
    }
  } catch (err) {
    if (err instanceof LLMError) throw err;
    if (err instanceof SyntaxError) {
      throw new LLMError("Failed to parse LLM JSON response", "parse_error");
    }
    if (err instanceof Error && err.name === "AbortError") {
      throw new LLMError(`LLM request timed out after ${timeout}ms`, "timeout");
    }
    throw new LLMError(
      `LLM API error: ${err instanceof Error ? err.message : String(err)}`,
      "api_error"
    );
  } finally {
    clearTimeout(timer);
  }
}
