import { z } from "zod";
import { chatCompletionJSON } from "@/lib/llm/client";
import { buildIntentPrompt } from "@/lib/llm/prompts";
import type { ExtendedIntent } from "@/types";

const IntentSchema = z.object({
  intent: z.enum([
    "dining_recommend", "booking", "query_restaurant", "modify_plan", "chitchat",
    "entertainment_recommend", "flight_search", "train_search",
    "car_service", "pickup_service", "shopping_recommend",
    "trip_plan", "order_create", "order_pay", "order_list",
  ]),
  confidence: z.number().min(0).max(1),
});

export async function classifyIntent(
  userInput: string,
  historyContext?: string
): Promise<{ intent: ExtendedIntent; confidence: number } | null> {
  try {
    const messages = buildIntentPrompt(userInput, historyContext);
    const result = await chatCompletionJSON<z.infer<typeof IntentSchema>>(messages, {
      temperature: 0.1,
      maxTokens: 128,
      timeout: 5000,
    });
    const parsed = IntentSchema.safeParse(result);
    if (!parsed.success) return null;
    return { intent: parsed.data.intent, confidence: parsed.data.confidence };
  } catch {
    return null;
  }
}
