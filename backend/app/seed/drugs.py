"""
Seed data: 30 commonly used perioperative drugs with known nutrient interactions.
"""

from ..models.drug import Drug

MVP_DRUGS: list[Drug] = [
    # Antibiotics / Antimicrobials
    Drug(atc_code="J01GB03", generic_name="庆大霉素", drug_class="氨基糖苷类抗生素",
         indication="革兰阴性菌感染", administration_route="iv",
         depletes_nutrients=[{"nutrient": "镁", "mechanism": "肾小管毒性→镁排泄增加"}],
         requires_nutrient_monitoring=["镁"], interacts_with_enteral_formula=False),

    Drug(atc_code="J01MA02", generic_name="环丙沙星", drug_class="氟喹诺酮类",
         indication="广谱抗感染",
         food_interaction="take_on_empty",
         depletes_nutrients=[{"nutrient": "钙", "mechanism": "螯合钙离子，减少吸收"},
                             {"nutrient": "镁", "mechanism": "螯合镁离子"}],
         requires_nutrient_monitoring=["钙", "镁"],
         interacts_with_enteral_formula=True,
         interaction_notes="与含钙/镁/铁的肠内制剂间隔至少2小时"),

    Drug(atc_code="J04AC01", generic_name="异烟肼", drug_class="抗结核药",
         indication="结核病",
         depletes_nutrients=[{"nutrient": "维生素B6", "mechanism": "形成腙复合物增加B6排泄"}],
         requires_nutrient_monitoring=["维生素B6"],
         recommendation="常规补充B6 10-50mg/日"),

    Drug(atc_code="J01DD04", generic_name="头孢曲松", drug_class="三代头孢菌素",
         indication="社区获得性肺炎、腹腔感染",
         depletes_nutrients=[{"nutrient": "维生素K", "mechanism": "抑制肠道维生素K合成(含N-甲硫四氮唑侧链)"}],
         requires_nutrient_monitoring=["维生素K", "凝血功能"]),

    # GI medications
    Drug(atc_code="A02BC01", generic_name="奥美拉唑", drug_class="质子泵抑制剂(PPI)",
         indication="GERD、消化性溃疡、上消化道出血预防",
         depletes_nutrients=[
             {"nutrient": "镁", "mechanism": "胃酸减少→肠道镁吸收下降"},
             {"nutrient": "维生素B12", "mechanism": "胃酸减少→食物结合B12释放障碍"},
             {"nutrient": "钙", "mechanism": "胃酸减少→碳酸钙吸收障碍"},
         ],
         requires_nutrient_monitoring=["镁", "维生素B12", "钙/骨密度(长期)"]),

    Drug(atc_code="A03FA01", generic_name="甲氧氯普胺(胃复安)", drug_class="促胃动力药",
         indication="恶心呕吐、胃排空延迟",
         interacts_with_enteral_formula=False,
         recommendation="可改善EN耐受性，减少胃残余量"),

    # Cardiovascular
    Drug(atc_code="C03CA01", generic_name="呋塞米", drug_class="袢利尿剂",
         indication="水肿、心衰、高血压",
         depletes_nutrients=[
             {"nutrient": "钾", "mechanism": "抑制Na-K-2Cl共转运→肾钾排泄增加"},
             {"nutrient": "镁", "mechanism": "肾镁排泄增加"},
             {"nutrient": "硫胺素", "mechanism": "尿硫胺素排泄增加"},
         ],
         requires_nutrient_monitoring=["钾", "镁", "硫胺素(长期大剂量)"]),

    Drug(atc_code="C07AB02", generic_name="美托洛尔", drug_class="β受体阻滞剂",
         indication="高血压、心衰、冠心病",
         depletes_nutrients=[{"nutrient": "辅酶Q10", "mechanism": "可能抑制内源性CoQ10合成"}],
         requires_nutrient_monitoring=["辅酶Q10(长期)"]),

    Drug(atc_code="C09AA02", generic_name="依那普利", drug_class="ACEI",
         indication="高血压、心衰",
         depletes_nutrients=[{"nutrient": "锌", "mechanism": "巯基螯合锌→尿锌排泄增加"}],
         requires_nutrient_monitoring=["锌(出现缺乏症状时)"]),

    Drug(atc_code="C08CA01", generic_name="氨氯地平", drug_class="钙通道阻滞剂",
         indication="高血压",
         interacts_with_enteral_formula=False,
         recommendation="与含钙FSMP无相互作用(CCB作用于血管L型钙通道，非肠道钙吸收)"),

    Drug(atc_code="C10AA01", generic_name="辛伐他汀", drug_class="HMG-CoA还原酶抑制剂(他汀)",
         indication="高脂血症、ASCVD预防",
         depletes_nutrients=[{"nutrient": "辅酶Q10", "mechanism": "HMG-CoA还原酶抑制→CoQ10合成途径阻断"}],
         requires_nutrient_monitoring=["辅酶Q10(肌病症状时)"]),

    # Anticoagulants
    Drug(atc_code="B01AA03", generic_name="华法林", drug_class="维生素K拮抗剂",
         indication="房颤、深静脉血栓、肺栓塞抗凝",
         interacts_with_nutrient=[{"nutrient": "维生素K", "interaction": "直接药效学拮抗"},
                                  {"nutrient": "肠内营养", "interaction": "大豆油中的维生素K→INR波动"}],
         requires_nutrient_monitoring=["维生素K摄入稳定性", "INR"],
         interacts_with_enteral_formula=True,
         interaction_notes="FSMP中维生素K含量需稳定；避免大豆蛋白基础配方"),

    Drug(atc_code="B01AF01", generic_name="利伐沙班", drug_class="Xa因子抑制剂(DOAC)",
         indication="房颤抗凝、VTE预防/治疗",
         food_interaction="take_with_food",
         recommendation="15mg/20mg随餐服用增加生物利用度；与EN无相互作用"),

    # Analgesics
    Drug(atc_code="N02BE01", generic_name="对乙酰氨基酚", drug_class="解热镇痛药",
         indication="轻中度疼痛、发热",
         interacts_with_enteral_formula=False,
         depletes_nutrients=[{"nutrient": "谷胱甘肽", "mechanism": "代谢消耗谷胱甘肽(高剂量/长期)"}],
         requires_nutrient_monitoring=["肝功能(>4g/日)", "谷胱甘肽状态(NAC储备)"]),

    Drug(atc_code="M01AB05", generic_name="双氯芬酸", drug_class="NSAID",
         indication="术后疼痛、关节炎",
         food_interaction="take_with_food",
         depletes_nutrients=[{"nutrient": "铁", "mechanism": "胃肠道微量出血→铁丢失"},
                             {"nutrient": "叶酸", "mechanism": "肠黏膜损伤→吸收减少"}],
         requires_nutrient_monitoring=["铁蛋白(长期使用者)", "胃肠道耐受性"]),

    # Diabetes medications
    Drug(atc_code="A10BA02", generic_name="二甲双胍", drug_class="双胍类",
         indication="2型糖尿病一线治疗",
         depletes_nutrients=[{"nutrient": "维生素B12", "mechanism": "回肠B12-内因子复合物摄取障碍(钙依赖性)"}],
         requires_nutrient_monitoring=["维生素B12(每年)", "同型半胱氨酸"]),

    Drug(atc_code="A10BB01", generic_name="格列本脲", drug_class="磺脲类",
         indication="2型糖尿病",
         interacts_with_enteral_formula=True,
         interaction_notes="EN时需监测血糖；调整胰岛素/磺脲类剂量匹配EN输注速率"),

    # Corticosteroids
    Drug(atc_code="H02AB06", generic_name="泼尼松龙", drug_class="糖皮质激素",
         indication="炎症性疾病、免疫抑制、术后抗炎",
         depletes_nutrients=[
             {"nutrient": "钙", "mechanism": "肠钙吸收减少+肾钙排泄增加"},
             {"nutrient": "钾", "mechanism": "肾钾排泄增加(盐皮质激素效应)"},
         ],
         requires_nutrient_monitoring=["钙/维生素D(>3月者)", "钾", "骨密度"]),

    # Insulin
    Drug(atc_code="A10AD01", generic_name="胰岛素(常规)", drug_class="胰岛素",
         indication="1型/2型糖尿病血糖控制",
         interacts_with_enteral_formula=True,
         interaction_notes="EN输注期间需频繁监测血糖；胰岛素剂量需匹配EN输注速率和碳水化合物负荷",
         requires_nutrient_monitoring=["血糖(q4-6h EN期间)", "钾(胰岛素→细胞内钾转移)"]),

    # Thyroid
    Drug(atc_code="H03AA01", generic_name="左甲状腺素钠", drug_class="甲状腺激素替代",
         indication="甲减",
         food_interaction="take_on_empty",
         interacts_with_enteral_formula=True,
         interaction_notes="与含钙/铁/大豆的FSMP间隔至少4小时；EN暂停后30分钟给药再恢复EN"),

    # Anticonvulsants
    Drug(atc_code="N03AX09", generic_name="左乙拉西坦", drug_class="抗癫痫药",
         indication="癫痫部分性发作",
         interacts_with_enteral_formula=False,
         recommendation="与EN无显著相互作用"),

    # Sedatives
    Drug(atc_code="N05CD08", generic_name="咪达唑仑", drug_class="苯二氮卓类镇静药",
         indication="ICU镇静、术前用药",
         interacts_with_enteral_formula=False,
         recommendation="EN无需中断(IV给药)"),

    # Opioid analgesics
    Drug(atc_code="N02AA01", generic_name="吗啡", drug_class="阿片类镇痛药",
         indication="中重度疼痛",
         interacts_with_enteral_formula=True,
         interaction_notes="减慢胃肠蠕动→EN耐受性下降(腹胀/便秘/胃残余量增加)；需胃肠动力监测"),

    # Antiemetics
    Drug(atc_code="A04AA01", generic_name="昂丹司琼", drug_class="5-HT3受体拮抗剂",
         indication="术后恶心呕吐预防/治疗",
         interacts_with_enteral_formula=False,
         recommendation="可用于改善EN相关恶心，给药30分钟后评估EN耐受性"),

    # Vasopressors
    Drug(atc_code="C01CA24", generic_name="去甲肾上腺素", drug_class="儿茶酚胺类升压药",
         indication="感染性休克/低血压",
         interacts_with_enteral_formula=True,
         interaction_notes="休克状态下EN不推荐(肠道低灌注→非闭塞性肠缺血风险)；血流动力学稳定后尽早启动EN"),

    # H2 blockers
    Drug(atc_code="A02BA02", generic_name="雷尼替丁", drug_class="H2受体拮抗剂",
         indication="GERD、消化性溃疡、应激性溃疡预防",
         depletes_nutrients=[
             {"nutrient": "维生素B12", "mechanism": "胃酸减少→B12吸收减少(弱于PPI)"},
             {"nutrient": "铁", "mechanism": "胃酸减少→非血红素铁吸收减少"},
         ],
         requires_nutrient_monitoring=["维生素B12(长期)", "铁蛋白"]),

    # Laxatives
    Drug(atc_code="A06AD11", generic_name="乳果糖", drug_class="渗透性泻药",
         indication="便秘、肝性脑病",
         interacts_with_enteral_formula=True,
         interaction_notes="用于肠内营养相关便秘；肝性脑病时调节EN配方(限制芳香族氨基酸)"),

    # Calcium/Vitamin D (adjunctive)
    Drug(atc_code="A12AX01", generic_name="碳酸钙+维生素D3", drug_class="钙补充剂",
         indication="骨质疏松预防、长期激素使用者钙补充",
         interacts_with_enteral_formula=True,
         interaction_notes="与含磷酸盐的FSMP间隔2小时(磷酸钙沉淀风险)"),

    # Antifungal
    Drug(atc_code="J02AC01", generic_name="氟康唑", drug_class="三唑类抗真菌药",
         indication="念珠菌感染",
         interacts_with_enteral_formula=False,
         recommendation="与EN无显著相互作用"),
]


def get_mvp_drugs() -> list[Drug]:
    return MVP_DRUGS
