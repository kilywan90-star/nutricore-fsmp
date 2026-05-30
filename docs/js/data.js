/**
 * NutriCore FSMP — Data Layer
 * NMPA FSMP registry, diseases, surgeries, drug interactions
 */

// ===== Products (representative sample from 311-registry) =====
const FSMP_PRODUCTS = [
  // Complete Nutrition
  {reg:"TY20220001",name:"能全力(Nutrison)",mfr:"Nutricia 纽迪希亚",cat:"全营养",form:"液体",energy:100,protein:4.0,protSrc:"casein",osm:250,feat:["fiber"],price:85,unit:500},
  {reg:"TY20220002",name:"能全力高能(Nutrison Energy)",mfr:"Nutricia 纽迪希亚",cat:"全营养",form:"液体",energy:150,protein:6.0,protSrc:"casein",osm:320,feat:["fiber"],price:95,unit:500},
  {reg:"TY20220003",name:"能全力蛋白质强化(Nutrison Protein Plus)",mfr:"Nutricia 纽迪希亚",cat:"全营养",form:"液体",energy:125,protein:6.3,protSrc:"casein",osm:300,feat:["fiber","high_protein"],price:90,unit:500},
  {reg:"TY20220005",name:"安素(Ensure)",mfr:"Abbott 雅培",cat:"全营养",form:"粉状",energy:100,protein:3.8,protSrc:"casein+whey",osm:300,feat:[],price:70,unit:400},
  {reg:"TY20220006",name:"安素高蛋白(Ensure Plus)",mfr:"Abbott 雅培",cat:"全营养",form:"液体",energy:150,protein:6.0,protSrc:"casein+whey",osm:450,feat:["high_protein"],price:85,unit:220},
  {reg:"TY20220007",name:"瑞能(Supportan)",mfr:"Fresenius Kabi 费森尤斯卡比",cat:"全营养",form:"液体",energy:100,protein:4.0,protSrc:"casein",osm:290,feat:["immune_modulation","fish_oil"],price:120,unit:500},
  {reg:"TY20220008",name:"瑞素(Fresubin)",mfr:"Fresenius Kabi 费森尤斯卡比",cat:"全营养",form:"液体",energy:100,protein:3.8,protSrc:"casein",osm:250,feat:[],price:75,unit:500},
  {reg:"TY20220009",name:"瑞代(Fresubin Energy)",mfr:"Fresenius Kabi 费森尤斯卡比",cat:"全营养",form:"液体",energy:150,protein:5.6,protSrc:"casein",osm:380,feat:["high_energy"],price:85,unit:500},
  {reg:"TY20220010",name:"瑞先(Fresubin Fibre)",mfr:"Fresenius Kabi 费森尤斯卡比",cat:"全营养",form:"液体",energy:100,protein:3.8,protSrc:"casein",osm:250,feat:["fiber"],price:80,unit:500},
  {reg:"TY20220011",name:"力存(Enteral Nutrition)",mfr:"华瑞制药 SSPC",cat:"全营养",form:"液体",energy:100,protein:4.0,protSrc:"casein",osm:260,feat:[],price:65,unit:500},
  {reg:"TY20220013",name:"伊力佳(Impact)",mfr:"Nestle 雀巢健康科学",cat:"全营养",form:"液体",energy:100,protein:5.6,protSrc:"casein+whey",osm:310,feat:["immune_modulation","arginine","omega3"],price:140,unit:500},
  {reg:"TY20220014",name:"百普力(Peptamen)",mfr:"Nestle 雀巢健康科学",cat:"全营养",form:"液体",energy:100,protein:4.0,protSrc:"hydrolysate",osm:290,feat:["low_residue","high_mct"],price:130,unit:500},
  {reg:"TY20220015",name:"百普力高能(Peptamen AF)",mfr:"Nestle 雀巢健康科学",cat:"全营养",form:"液体",energy:150,protein:7.6,protSrc:"hydrolysate",osm:400,feat:["low_residue","high_mct","high_protein"],price:145,unit:500},
  {reg:"TY20220016",name:"速愈素(Oral Impact)",mfr:"Nestle 雀巢健康科学",cat:"全营养",form:"粉状",energy:100,protein:5.6,protSrc:"casein+whey",osm:400,feat:["immune_modulation","arginine","omega3"],price:160,unit:250},
  {reg:"TY20230012",name:"瑞能伤口愈合(Supportan Wound)",mfr:"Fresenius Kabi 费森尤斯卡比",cat:"全营养",form:"液体",energy:100,protein:6.5,protSrc:"casein+whey",osm:330,feat:["immune_modulation","high_protein"],price:160,unit:500},
  {reg:"TY20240018",name:"基畅(Ener-G)",mfr:"基立福(中国)",cat:"全营养",form:"液体",energy:100,protein:4.0,protSrc:"casein",osm:260,feat:["fiber"],price:58,unit:500},
  {reg:"TY20240021",name:"佰美乐(Baimeile)",mfr:"南京和美乐生物",cat:"全营养",form:"液体",energy:100,protein:4.0,protSrc:"casein+whey",osm:260,feat:["fiber"],price:52,unit:500},
  {reg:"TY20240024",name:"宜品术后营养(Post-OP)",mfr:"宜品营养",cat:"全营养",form:"液体",energy:130,protein:5.5,protSrc:"whey+casein",osm:310,feat:["fiber"],price:68,unit:500},
  {reg:"TY20250003",name:"卡乐畅全营养配方粉",mfr:"山东若尧特医食品有限公司",cat:"全营养",form:"粉状",energy:100,protein:4.0,protSrc:"casein",osm:280,feat:[],price:55,unit:400},
  {reg:"TY20250015",name:"力衡全全营养配方食品",mfr:"广州力衡临床营养品有限公司",cat:"全营养",form:"液体",energy:100,protein:4.0,protSrc:"casein",osm:270,feat:[],price:60,unit:500},
  {reg:"TY20250023",name:"每益乐®全营养配方食品",mfr:"汤臣倍健股份有限公司",cat:"全营养",form:"液体",energy:120,protein:4.5,protSrc:"whey+casein",osm:300,feat:["fiber"],price:78,unit:500},
  {reg:"TY20250028",name:"均适能®全营养配方食品",mfr:"广州白云山汉方现代药业有限公司",cat:"全营养",form:"液体",energy:100,protein:4.2,protSrc:"casein",osm:280,feat:[],price:65,unit:500},
  {reg:"TY20250040",name:"冬泽舒全全营养配方食品",mfr:"江苏冬泽特医食品有限公司",cat:"全营养",form:"粉状",energy:100,protein:4.5,protSrc:"whey+casein",osm:290,feat:["fiber"],price:58,unit:500},
  {reg:"TY20240020",name:"益力安(Elental)",mfr:"丽珠医药",cat:"全营养",form:"粉状",energy:100,protein:4.0,protSrc:"amino_acid",osm:290,feat:["elemental","low_residue","high_mct"],price:160,unit:500},

  // Specific Complete
  {reg:"TY20230001",name:"伊力佳糖尿病(Diben)",mfr:"Nestle 雀巢健康科学",cat:"特定全营养",form:"液体",energy:100,protein:4.3,protSrc:"casein",osm:280,feat:["diabetes","fiber"],price:110,unit:500},
  {reg:"TY20230002",name:"瑞代糖尿病(Fresubin Diab)",mfr:"Fresenius Kabi 费森尤斯卡比",cat:"特定全营养",form:"液体",energy:100,protein:4.2,protSrc:"casein",osm:290,feat:["diabetes","fiber"],price:100,unit:500},
  {reg:"TY20230003",name:"瑞高肾病(Nepro)",mfr:"Abbott 雅培",cat:"特定全营养",form:"液体",energy:200,protein:4.5,protSrc:"casein",osm:600,feat:["renal","high_energy","low_electrolyte"],price:130,unit:237},
  {reg:"TY20230004",name:"瑞高肾病HP(Nepro HP)",mfr:"Abbott 雅培",cat:"特定全营养",form:"液体",energy:200,protein:8.1,protSrc:"casein+whey",osm:680,feat:["renal","high_energy","high_protein","low_electrolyte"],price:145,unit:237},
  {reg:"TY20230005",name:"瑞高肝病(Hepatic Aid)",mfr:"Fresenius Kabi 费森尤斯卡比",cat:"特定全营养",form:"液体",energy:100,protein:4.0,protSrc:"amino_acid",osm:350,feat:["hepatic","high_bcaa"],price:170,unit:500},
  {reg:"TY20230009",name:"瑞能肿瘤(Supportan Tumor)",mfr:"Fresenius Kabi 费森尤斯卡比",cat:"特定全营养",form:"液体",energy:150,protein:6.5,protSrc:"casein+whey",osm:360,feat:["immune_modulation","high_protein","omega3"],price:155,unit:500},
  {reg:"TY20230010",name:"益力佳(Glucerna)",mfr:"Abbott 雅培",cat:"特定全营养",form:"液体",energy:100,protein:4.2,protSrc:"casein",osm:300,feat:["diabetes","fiber"],price:95,unit:400},
  {reg:"TY20230011",name:"肺病专用(Pulmocare)",mfr:"Abbott 雅培",cat:"特定全营养",form:"液体",energy:150,protein:5.6,protSrc:"casein",osm:400,feat:["low_carb","high_fat"],price:100,unit:237},
  {reg:"TY20240016",name:"松康餐-糖尿病型",mfr:"香颂国际",cat:"特定全营养",form:"液体",energy:90,protein:4.0,protSrc:"soy+whey",osm:260,feat:["diabetes","fiber"],price:50,unit:500},
  {reg:"TY20240015",name:"小唯源素(儿童1-10岁)",mfr:"亚宝药业",cat:"特定全营养",form:"粉状",energy:100,protein:2.8,protSrc:"whey",osm:240,feat:["pediatric"],price:65,unit:400},
  {reg:"TY20230013",name:"宜品特爱本佳(PKU)",mfr:"宜品营养",cat:"特定全营养",form:"粉状",energy:100,protein:3.5,protSrc:"amino_acid",osm:270,feat:["phe_free","newborn"],price:220,unit:400},
  {reg:"TY20260017",name:"瑞葆安®婴儿苯丙酮尿症配方",mfr:"内蒙古特康瑞营养食品有限责任公司",cat:"特定全营养",form:"粉状",energy:100,protein:3.5,protSrc:"amino_acid",osm:270,feat:["phe_free"],price:210,unit:400},

  // Modular - Protein
  {reg:"TY20241001",name:"蛋白粉组件(ProMod)",mfr:"Abbott 雅培",cat:"蛋白质组件",form:"粉状",energy:30,protein:28.0,protSrc:"whey",osm:100,feat:["protein_module"],price:120,unit:0},
  {reg:"TY20250001",name:"特易美®蛋白质组件配方食品",mfr:"重庆华森制药股份有限公司",cat:"蛋白质组件",form:"粉状",energy:30,protein:25.0,protSrc:"whey",osm:110,feat:["protein_module"],price:80,unit:0},
  {reg:"TY20250045",name:"麦优泰®蛋白质组件配方食品",mfr:"吉林麦孚营养科技有限公司",cat:"蛋白质组件",form:"粉状",energy:30,protein:26.0,protSrc:"whey",osm:105,feat:["protein_module"],price:75,unit:0},

  // Modular - Carb
  {reg:"TY20250002",name:"特咔力®碳水化合物组件配方粉",mfr:"时代特殊医学用途配方食品（深圳）有限公司",cat:"碳水化合物组件",form:"粉状",energy:380,protein:0,protSrc:"none",osm:200,feat:["carb_module"],price:50,unit:0},
  {reg:"TY20255001",name:"每立盈®碳水化合物组件配方食品",mfr:"美亚特医食品香港有限公司",cat:"碳水化合物组件",form:"液体",energy:200,protein:0,protSrc:"none",osm:260,feat:["carb_module"],price:60,unit:500},

  // Modular - Fat
  {reg:"TY20241002",name:"MCT油组件(MCT Oil)",mfr:"Nutricia 纽迪希亚",cat:"脂肪组件",form:"液体",energy:850,protein:0,protSrc:"none",osm:0,feat:["fat_module","high_mct"],price:180,unit:500},

  // Modular - Electrolyte
  {reg:"TY20250033",name:"冬泽乐宝电解质配方食品",mfr:"江苏冬泽特医食品有限公司",cat:"电解质配方",form:"液体",energy:20,protein:0,protSrc:"none",osm:260,feat:["electrolyte_module"],price:45,unit:500},
  {reg:"TY20260004",name:"卡焕®电解质配方食品",mfr:"玛士撒拉特医（泰州）生物科技有限公司",cat:"电解质配方",form:"液体",energy:20,protein:0,protSrc:"none",osm:250,feat:["electrolyte_module"],price:48,unit:500},

  // Incomplete / Starter
  {reg:"TY20240001",name:"瑞素肠内(Fresubin EN Starter)",mfr:"Fresenius Kabi 费森尤斯卡比",cat:"非全营养",form:"液体",energy:50,protein:2.0,protSrc:"casein",osm:180,feat:["low_osmolarity","starter"],price:50,unit:500},

  // Modular - Others
  {reg:"TY20241003",name:"膳食纤维组件(Benefiber)",mfr:"Nestle 雀巢健康科学",cat:"增稠组件",form:"粉状",energy:10,protein:0,protSrc:"none",osm:50,feat:["fiber_module"],price:60,unit:0},
  {reg:"TY20241004",name:"谷氨酰胺组件(Glutamine Plus)",mfr:"Fresenius Kabi 费森尤斯卡比",cat:"蛋白质组件",form:"粉状",energy:40,protein:10.0,protSrc:"amino_acid",osm:200,feat:["glutamine_module","immune_modulation"],price:200,unit:0},
  {reg:"TY20241005",name:"精氨酸组件(Arginine Module)",mfr:"Fresenius Kabi 费森尤斯卡比",cat:"蛋白质组件",form:"粉状",energy:40,protein:10.0,protSrc:"amino_acid",osm:250,feat:["arginine_module","immune_modulation"],price:180,unit:0},

  // Infant FSMP
  {reg:"TY20175001",name:"纽康特婴儿氨基酸配方粉",mfr:"SHS International Ltd",cat:"婴儿配方",form:"粉状",energy:100,protein:3.0,protSrc:"amino_acid",osm:260,feat:["hypoallergenic","amino_acid"],price:230,unit:400},
  {reg:"TY20175002",name:"雅培亲护婴儿乳蛋白部分水解配方粉",mfr:"Abbott Laboratories S.A.",cat:"婴儿配方",form:"粉状",energy:100,protein:2.5,protSrc:"hydrolysate",osm:220,feat:["partially_hydrolyzed"],price:180,unit:400},
  {reg:"TY20180001",name:"贝因美婴儿无乳糖配方食品",mfr:"杭州贝因美母婴营养品有限公司",cat:"婴儿配方",form:"粉状",energy:100,protein:2.5,protSrc:"casein",osm:230,feat:["lactose_free"],price:120,unit:400},
  {reg:"TY20185001",name:"纽贝瑞氨基酸代谢障碍配方食品",mfr:"SHS International Ltd",cat:"婴儿配方",form:"粉状",energy:100,protein:3.2,protSrc:"amino_acid",osm:250,feat:["metabolic_disorder"],price:260,unit:400},
];

// ===== Drug-Nutrient Interactions =====
const DRUG_INTERACTIONS = {
  "A02BC01": {drug:"奥美拉唑 (PPI)",class:"质子泵抑制剂",interactions:[
    {nutrient:"镁",type:"depletion",sev:"moderate",grade:"A",mech:"胃酸减少→TRPM6/7通道功能障碍→肠道镁吸收下降",rec:"长期使用者每6-12月监测血镁；柠檬酸镁吸收优于氧化镁",ref:"FDA 2011; Hess MW 2013 PMID:23313294; meta: PPI 1.43x低镁风险"},
    {nutrient:"维生素B12",type:"depletion",sev:"moderate",grade:"A",mech:"胃酸减少→食物结合B12释放障碍→内因子结合减少",rec:"每年监测B12+MMA；缺乏者口服B12 1000mcg/日或IM",ref:"Lam JR JAMA 2013 PMID:24327026; n=25956, OR 1.65"},
    {nutrient:"钙",type:"depletion",sev:"mild",grade:"B",mech:"胃酸减少→碳酸钙吸收障碍→PTH代偿升高",rec:"改用柠檬酸钙；长期使用者监测骨密度",ref:"Khalili H BMJ 2012 PMID:22290211; n=79900, 髋部骨折风险"},
    {nutrient:"铁(非血红素)",type:"depletion",sev:"mild",grade:"B",mech:"胃酸减少→非血红素铁Fe3+→Fe2+还原障碍",rec:"血红素铁(动物源)吸收不受影响；缺乏者补铁",ref:"Hutchinson C 2007 PMID:17635377"},
  ]},
  "A10BA02": {drug:"二甲双胍",class:"双胍类降糖药",interactions:[
    {nutrient:"维生素B12",type:"depletion",sev:"moderate",grade:"A",mech:"回肠B12-内因子复合物摄取障碍(钙依赖)；小肠细菌过度生长消耗B12",rec:"每年监测B12+MMA；剂量>1500mg/日或>3年者加强监测；口服B12补充",ref:"Aroda VR Diabetes Care 2016 PMID:27311490; DPP/DPPOS n=1750, 19%缺乏; de Jager BMJ 2010 PMID:20488943 RCT"},
    {nutrient:"辅酶Q10",type:"depletion",sev:"mild",grade:"C",mech:"线粒体复合体I抑制→可能影响CoQ10合成",rec:"疲劳/肌无力时考虑CoQ10 100-200mg/日",ref:"Madiraju AK Nature 2014 PMID:24898544"},
  ]},
  "B01AA03": {drug:"华法林",class:"维生素K拮抗剂",interactions:[
    {nutrient:"维生素K",type:"antagonism",sev:"severe",grade:"A",mech:"直接药效学拮抗—维生素K环氧化物还原酶被抑制→维生素K依赖凝血因子合成受阻",rec:"每日维生素K摄入保持恒定(90-120mcg/日)；切勿突然大量摄入绿叶蔬菜",ref:"Holbrook AM Arch Intern Med 2005 PMID:15851696; 系统综述"},
    {nutrient:"肠内营养(FSMP)",type:"interaction",sev:"moderate",grade:"B",mech:"FSMP含维生素K(尤其大豆蛋白配方)→INR波动；不同品牌K含量差异大",rec:"FSMP品牌/配方保持恒定；更换配方时监测INR",ref:"Dickerson RN Pharmacotherapy 2008 PMID:18294107"},
  ]},
  "C03CA01": {drug:"呋塞米 (袢利尿剂)",class:"袢利尿剂",interactions:[
    {nutrient:"钾",type:"depletion",sev:"moderate",grade:"A",mech:"抑制髓袢升支粗段Na-K-2Cl共转运体→肾钾排泄增加",rec:"监测K+；补充氯化钾或联用保钾利尿剂；目标K+ 4.0-5.0 mmol/L",ref:"Cohn JN 2000 PMID:10874278"},
    {nutrient:"镁",type:"depletion",sev:"moderate",grade:"B",mech:"远曲小管镁重吸收受抑→肾镁排泄增加",rec:"每3月监测Mg2+；<0.7mmol/L补充；低钾+低镁→先纠正镁",ref:"al-Ghamdi SM 1994 PMID:7845315"},
    {nutrient:"硫胺素(B1)",type:"depletion",sev:"mild",grade:"C",mech:"尿硫胺素排泄增加；CHF患者可能加重心肌能量代谢障碍",rec:"CHF+大剂量呋塞米(>80mg/日)者补充B1 100mg/日",ref:"Hanninen SA J Card Fail 2006 PMID:16385063"},
  ]},
  "H02AB06": {drug:"泼尼松龙 (糖皮质激素)",class:"糖皮质激素",interactions:[
    {nutrient:"钙",type:"depletion",sev:"moderate",grade:"A",mech:"肠钙吸收↓+肾钙排泄↑+RANKL激活→骨吸收↑→6月内快速骨丢失",rec:"钙1000-1200mg/日+D3 800-2000IU/日；>3月疗程者DEXA基线检查；高骨折风险加双膦酸盐",ref:"van Staa TP 2000 PMID:10841169; Buckley L Arthritis Rheumatol 2017 PMID:28685780 ACR Guideline"},
    {nutrient:"维生素D",type:"depletion",sev:"moderate",grade:"B",mech:"糖皮质激素诱导CYP3A4→24-羟化酶上调→25-OH D3加速分解",rec:"维持25-OH D >30 ng/mL；补充D3 800-2000IU/日",ref:"Skversky AL JCEM 2011 PMID:21917866"},
    {nutrient:"钾",type:"depletion",sev:"mild",grade:"B",mech:"盐皮质激素受体激活→远曲小管K+分泌增加(治疗剂量效应轻微)",rec:"富钾饮食；确诊低钾时补充",ref:"Schultheiss UT Steroids 2016"},
  ]},
  "C10AA01": {drug:"辛伐他汀 (他汀类)",class:"HMG-CoA还原酶抑制剂",interactions:[
    {nutrient:"辅酶Q10",type:"depletion",sev:"mild",grade:"B",mech:"HMG-CoA还原酶抑制→甲羟戊酸途径阻断→内源性CoQ10合成减少(共享生物合成通路)",rec:"他汀相关肌肉症状(SAMS)时补充CoQ10 100-200mg/日",ref:"Banach M Mayo Clin Proc 2015 meta SMD -0.44; Qu H JAHA 2018 meta"},
  ]},
  "J01GB03": {drug:"庆大霉素 (氨基糖苷类)",class:"氨基糖苷类抗生素",interactions:[
    {nutrient:"镁",type:"depletion",sev:"moderate",grade:"B",mech:"肾小管毒性→髓袢升支粗段Mg2+重吸收障碍→镁尿症",rec:"疗程中监测Mg2+(尤其>5天、老年、肾功能不全)",ref:"Shah GM 1988 PMID:3341422"},
  ]},
  "J04AC01": {drug:"异烟肼",class:"抗结核药",interactions:[
    {nutrient:"维生素B6",type:"depletion",sev:"moderate",grade:"A",mech:"与磷酸吡哆醛形成腙复合物→尿排泄增加；抑制吡哆醇磷酸激酶",rec:"WHO推荐常规补充B6 10-50mg/日",ref:"Snider DE Tubercle 1980 PMID:6269279; van der Watt 2011 PMID:21740651"},
  ]},
  "C09AA02": {drug:"依那普利 (ACEI)",class:"血管紧张素转化酶抑制剂",interactions:[
    {nutrient:"锌",type:"depletion",sev:"mild",grade:"C",mech:"含巯基ACEI(卡托普利)螯合锌→尿锌排泄增加",rec:"味觉障碍或皮炎时检查锌水平；低锌补充15-30mg/日",ref:"Golik A 1998 PMID:9520730"},
    {nutrient:"钾",type:"accumulation",sev:"moderate",grade:"A",mech:"醛固酮↓→远曲小管K+分泌↓→高钾风险(尤其肾功能不全)",rec:"基线+1周+每3-6月监测K+；避免补钾/保钾利尿剂/K+盐替代品",ref:"Palmer BF NEJM 2004 PMID:15342813"},
  ]},
  "H03AA01": {drug:"左甲状腺素钠",class:"甲状腺激素替代",interactions:[
    {nutrient:"钙/铁/大豆(FSMP)",type:"interaction",sev:"moderate",grade:"A",mech:"胃肠内结合/螯合左甲状腺素→吸收减少30-40%",rec:"空腹服用优甲乐；暂停EN前后各30min；避免大豆蛋白FSMP",ref:"Benvenga S Thyroid 2008 PMID:18341479"},
  ]},
  "J01MA02": {drug:"环丙沙星 (氟喹诺酮类)",class:"氟喹诺酮类抗生素",interactions:[
    {nutrient:"钙/镁/铁/锌(多价阳离子)",type:"interaction",sev:"moderate",grade:"A",mech:"螯合作用→抗生素吸收减少30-90%→治疗失败风险",rec:"FSMP/肠内喂养与抗生素间隔≥2h(前)或≥4h(后)",ref:"Lomaestro BM 1992 PMID:1613044; 吸收可下降90%"},
  ]},
};
