import { z } from "zod";
import { chatCompletionJSON } from "@/lib/llm/client";
import { buildSlotExtractionPrompt } from "@/lib/llm/prompts";
import type { ExtendedIntent, ExtendedNLUSlots } from "@/types";

const NLUSlotsSchema = z.object({
  // 基础槽位
  city: z.string().optional(),
  date: z.string().optional(),
  time: z.string().optional(),
  guestCount: z.number().int().positive().optional(),
  budgetPerPerson: z.number().int().positive().optional(),
  budgetMax: z.number().int().positive().optional(),
  cuisine: z.string().optional(),
  privacy: z.enum(["L1", "L2", "L3", "L4"]).optional(),
  scene: z.string().optional(),
  guestProfile: z.string().optional(),
  dietaryRestrictions: z.array(z.string()).optional(),
  // 交通槽位
  departureCity: z.string().optional(),
  arrivalCity: z.string().optional(),
  transportType: z.enum(["flight", "train", "private_car"]).optional(),
  seatClass: z.enum(["economy", "business", "first", "second", "vip"]).optional(),
  departureDate: z.string().optional(),
  returnDate: z.string().optional(),
  passengerCount: z.number().int().positive().optional(),
  routeNumber: z.string().optional(),
  // 娱乐槽位
  entertainmentType: z.enum(["bath", "massage", "ktv", "dance_hall", "business_shopping"]).optional(),
  entertainmentScene: z.string().optional(),
  // 购物槽位
  shoppingType: z.string().optional(),
  shoppingBudget: z.number().int().positive().optional(),
  // 接驳槽位
  pickupLocation: z.enum(["airport", "station", "hotel", "custom"]).optional(),
  pickupAddress: z.string().optional(),
  // 会议/行程
  meetingTime: z.string().optional(),
  meetingLocation: z.string().optional(),
  purpose: z.string().optional(),
  tripDays: z.number().int().positive().optional(),
  orderNumber: z.string().optional(),
});

export async function extractSlots(
  userInput: string,
  intent: ExtendedIntent
): Promise<ExtendedNLUSlots | null> {
  try {
    const messages = buildSlotExtractionPrompt(userInput, intent);
    const result = await chatCompletionJSON<z.infer<typeof NLUSlotsSchema>>(messages, {
      temperature: 0.1,
      maxTokens: 256,
      timeout: 8000,
    });
    const parsed = NLUSlotsSchema.safeParse(result);
    if (!parsed.success) return null;
    return parsed.data;
  } catch {
    return null;
  }
}
