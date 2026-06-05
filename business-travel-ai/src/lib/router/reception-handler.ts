import type { DomainResponse, DomainHandler } from "./types";
import type { NLUResult, ContentCard } from "@/types";
import { isReceptionIntent, parseReceptionInput, planReception } from "@/lib/reception/planner";
import { toContentCards } from "./domain-router";

export const handleReception: DomainHandler = async (nluResult, sessionId): Promise<DomainResponse> => {
  const slots = nluResult.slots as Record<string, unknown>;

  const plan = parseReceptionInput(
    nluResult.intent + " " + JSON.stringify(slots),
    slots as import("@/types").ExtendedNLUSlots
  );

  // Use directly the NLU slots instead of parsing from intent string
  plan.city = (slots.city as string) || (slots.arrivalCity as string) || "成都";
  plan.guestProfile = (slots.guestProfile as string) || plan.guestProfile;
  plan.guestCount = (slots.guestCount as number) || plan.guestCount;
  plan.budget = (slots.budgetPerPerson as number) || (slots.budgetMax as number) || plan.budget;
  plan.date = (slots.date as string) || (slots.departureDate as string) || plan.date;
  plan.meetingTime = (slots.meetingTime as string) || plan.meetingTime;
  plan.meetingLocation = (slots.meetingLocation as string) || plan.meetingLocation;

  const { reply, timeline } = await planReception(plan, sessionId);

  const allCards: ContentCard[] = [];
  for (const t of timeline) {
    allCards.push(...t.cards);
  }

  return {
    reply,
    data: timeline,
  };
};
