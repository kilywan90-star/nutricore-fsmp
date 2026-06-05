import { z } from "zod";
import { chatCompletionJSON } from "@/lib/llm/client";
import { buildRestaurantRecommendPrompt } from "@/lib/llm/prompts";
import type { SearchConstraints } from "@/types";
import type { DatabaseCandidate } from "./path-a-database";

export interface LLMRecommendation {
  name: string;
  reason: string;
  fromDBList: boolean;
}

const RecommendResponseSchema = z.object({
  recommendations: z.array(
    z.object({
      name: z.string(),
      reason: z.string(),
    })
  ),
});

export async function getLLMRecommendations(
  constraints: SearchConstraints,
  dbCandidates?: DatabaseCandidate[]
): Promise<LLMRecommendation[]> {
  try {
    const candidateNames = dbCandidates?.map((c) => c.restaurant.name) ?? [];

    const messages = buildRestaurantRecommendPrompt(constraints, candidateNames);
    const result = await chatCompletionJSON<z.infer<typeof RecommendResponseSchema>>(
      messages,
      { temperature: 0.3, maxTokens: 512, timeout: 10000 }
    );

    const parsed = RecommendResponseSchema.safeParse(result);
    if (!parsed.success) return [];

    return parsed.data.recommendations.map((r) => ({
      name: r.name,
      reason: r.reason,
      fromDBList: candidateNames.includes(r.name),
    }));
  } catch {
    return [];
  }
}
