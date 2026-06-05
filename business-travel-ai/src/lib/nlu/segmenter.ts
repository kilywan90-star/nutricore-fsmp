// ============================================================
// 中文复合句分割器
// 将复合句拆分为独立的意图承载子句
// ============================================================

// 连接词/短语 (按长度降序匹配，避免部分匹配)
const CONJUNCTIONS = [
  "并且", "然后", "之后", "同时", "另外", "还要", "还得",
  "而且", "接着", "随后", "再", "并", "还", "及",
];

// 构建连接词正则: 用 | 连接所有连接词
const CONJUNCTION_RE = new RegExp(
  `[，、；。！？；\\n]|(?:${CONJUNCTIONS.map((c) => escapeRegex(c)).join("|")})`,
  "g"
);

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export interface SegmentationResult {
  segments: string[];
  wasCompound: boolean;
}

/**
 * 将复合中文句子拆分为独立子句
 *
 * Pass 1: 按标点和连接词分割
 * Pass 2: 过滤空片段，合并过短修饰片段
 */
export function segmentCompoundSentence(input: string): SegmentationResult {
  const trimmed = input.trim();
  if (!trimmed) {
    return { segments: [], wasCompound: false };
  }

  // Pass 1: 分割
  const rawParts = trimmed
    .split(CONJUNCTION_RE)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);

  // 如果只有1个片段，说明不是复合句
  if (rawParts.length <= 1) {
    return { segments: [trimmed], wasCompound: false };
  }

  // Pass 2: 合并过短片段 (< 2字且不是独立动词) 到前一个片段
  const merged: string[] = [];
  for (const part of rawParts) {
    if (part.length < 2 && merged.length > 0) {
      // 极短片段（如"的"、"了"）合并到前一个
      merged[merged.length - 1] += part;
    } else {
      merged.push(part);
    }
  }

  return {
    segments: merged,
    wasCompound: merged.length >= 2,
  };
}
