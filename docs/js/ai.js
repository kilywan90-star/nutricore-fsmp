/**
 * NutriCore FSMP — AI Enhancement Module
 * DeepSeek-powered NL→Structured parsing + Clinical explanation generation
 */

const AI_CONFIG = {
  endpoint: 'https://api.deepseek.com/v1/chat/completions',
  apiKey: 'sk-707a90a4206b45e9962d606d7a6434f3',
  model: 'deepseek-chat',
  enabled: true,
};

/** Generic LLM call with retry */
async function callLLM(systemPrompt, userMessage, temperature = 0.3) {
  if (!AI_CONFIG.enabled) return null;
  try {
    const resp = await fetch(AI_CONFIG.endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${AI_CONFIG.apiKey}`,
      },
      body: JSON.stringify({
        model: AI_CONFIG.model,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userMessage },
        ],
        temperature,
        max_tokens: 2048,
        stream: false,
      }),
    });
    if (!resp.ok) {
      console.error(`AI API error: ${resp.status}`);
      return null;
    }
    const data = await resp.json();
    return data.choices?.[0]?.message?.content || null;
  } catch (e) {
    console.error('AI call failed:', e.message);
    return null;
  }
}

/**
 * P0: Natural Language Clinical Note → Structured Assessment Data
 * Accepts free-text clinical notes and extracts structured fields for the engine.
 */
const NL_PARSER_PROMPT = `你是一位临床营养专家。从病历文本中提取以下结构化信息。只返回JSON，不要任何解释。

提取规则：
- age: 年龄(整数)
- gender: male或female
- height: 身高cm(如果有数值)
- weight: 当前体重kg(如果有数值)
- weightLoss: 近期体重下降kg(如果有)
- weightLossPeriod: 下降发生在几个月内
- foodIntake: 0=正常/25=减少25%/50=减少50%/75=减少75%/90=几乎禁食(根据描述推断)
- diseaseCode: ICD-11疾病编码，从下列选择：
  2B92.0=结直肠癌, 2B72.0=胃癌, 2C13.0=胰腺癌, 2C22.0=食管癌, 2C17.0=肝癌,
  5A11=2型糖尿病, CB01=COPD, 1C00=脓毒症, 8B20=脑卒中, 5C50=肝硬化
  如果疾病不在列表中，选择最接近的
- surgeryCode: 手术编码，从下列选择(无手术则为null)：
  colorectal_resection=结直肠癌根治术, gastrectomy_subtotal=胃大部切除术,
  total_gastrectomy=全胃切除术, pancreaticoduodenectomy=胰十二指肠切除术,
  esophagectomy=食管癌根治术, liver_resection_major=大范围肝切除术,
  cholecystectomy=腹腔镜胆囊切除术, cytoreductive_surgery=肿瘤细胞减灭术
- postOpDay: 术后天数(整数，无手术则为0)
- giFunction: normal=正常/impaired=受损/non_functional=无功能
- swallow: normal=正常/impaired=受损/unsafe=不安全
- renal: normal=正常/impaired=不全/dialysis=透析
- liver: normal=正常/impaired=不全/failure=衰竭
- comorbidities: 合并症列表，从[diabetes,hypertension,copd,ckd]选择
- medications: 药品ATC编码列表，从下列选择：
  A02BC01=奥美拉唑/PPI, A10BA02=二甲双胍, B01AA03=华法林, C03CA01=呋塞米,
  H02AB06=泼尼松龙/激素, C10AA01=他汀/辛伐他汀, J01GB03=庆大霉素,
  J04AC01=异烟肼, C09AA02=依那普利/ACEI, H03AA01=左甲状腺素, J01MA02=环丙沙星
- alb: 血清白蛋白g/L(如果有数值)
- narrative: 用1-2句中文概括患者核心营养问题

JSON示例:
{
  "age": 65, "gender": "male", "height": 170, "weight": 58,
  "weightLoss": 8, "weightLossPeriod": 1, "foodIntake": 75,
  "diseaseCode": "2B72.0", "surgeryCode": "total_gastrectomy",
  "postOpDay": 21, "giFunction": "impaired", "swallow": "normal",
  "renal": "normal", "liver": "normal", "comorbidities": ["diabetes"],
  "medications": ["A02BC01"], "alb": 28,
  "narrative": "胃癌术后3周，进食困难导致体重急剧下降，存在高营养风险"
}`;

async function parseClinicalNote(noteText) {
  const jsonStr = await callLLM(NL_PARSER_PROMPT, noteText, 0.1);
  if (!jsonStr) return null;
  try {
    // Extract JSON from possible markdown code block
    const match = jsonStr.match(/\{[\s\S]*\}/);
    if (!match) return null;
    return JSON.parse(match[0]);
  } catch (e) {
    console.error('Failed to parse AI response:', e);
    return null;
  }
}

/**
 * P1: Generate Clinical Explanation
 * Takes structured assessment results → professional clinical note
 */
const EXPLANATION_PROMPT = `你是一位资深临床营养师。基于患者的营养评估结果，撰写一段专业的临床营养方案说明(300-500字)。

要求：
1. 用中文，面向临床医护人员(医生/营养师/药师)
2. 引用相关指南(ESPEN 2025/CSPEN 2025)
3. 解释为什么给出这个评分和推荐
4. 说明能量和蛋白质目标的依据
5. 指出药物-营养素相互作用的关键注意事项
6. 如果存在再喂养风险，重点强调
7. 语气专业但不过于学术化

不要给免责声明。直接写方案说明。`;

async function generateExplanation(assessmentData) {
  const input = JSON.stringify(assessmentData, null, 2);
  return await callLLM(EXPLANATION_PROMPT, input, 0.5);
}

/**
 * P2: Generate Patient Education
 * Translates professional plan → patient-friendly language
 */
const PATIENT_EDU_PROMPT = `你是一位善于沟通的临床营养师。将以下营养方案用通俗易懂的中文解释给患者/家属(200-300字)。

要求：
- 用"您"称呼，语气温暖
- 避免医学术语，用日常比喻解释(比如"蛋白质像砖头帮您修复伤口")
- 告诉患者每天具体怎么吃、喝多少营养液
- 提醒注意事项
- 结尾给一句鼓励`;

async function generatePatientEducation(assessmentData) {
  const input = JSON.stringify(assessmentData, null, 2);
  return await callLLM(PATIENT_EDU_PROMPT, input, 0.7);
}
