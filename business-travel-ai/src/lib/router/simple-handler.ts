import type { DomainResponse, DomainHandler } from "./types";

// ============================================================
// 简单回复域处理器
// 处理 chitchat / booking / query_restaurant / modify_plan 等静态话术
// ============================================================

export const handleSimple: DomainHandler = async (nluResult, _sessionId): Promise<DomainResponse> => {
  let reply: string;

  switch (nluResult.intent) {
    case "chitchat":
      reply = "您好！我是差序，您的商务出行助手。我可以帮您推荐餐厅、搜索休闲娱乐、查询交通航班等。请告诉我您的需求。";
      break;
    case "booking":
      reply = "预订功能即将上线。目前我可以帮您推荐餐厅，请告诉我城市、人数和偏好。";
      break;
    case "query_restaurant":
      reply = "餐厅查询功能即将上线。目前您可以直接描述需求，例如'帮我找个成都的川菜馆'。";
      break;
    case "modify_plan":
      reply = "好的，请告诉我新的需求，比如换个城市、调整预算或换个菜系。";
      break;
    default:
      reply = "抱歉，该功能正在开发中。目前我可以帮您推荐餐厅、搜索休闲娱乐和交通信息。";
      break;
  }

  return { reply };
};
