/**
 * NutriCore FSMP — Application Controller
 * Navigation, assessment workflow, rendering, product search
 */

let currentStep = 1;
let sidebarOpen = false;

// ===== NAVIGATION =====
function navigateTo(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.querySelectorAll('.tab-item').forEach(t => t.classList.remove('active'));

  const pageEl = document.getElementById('page-' + page);
  if (pageEl) pageEl.classList.add('active');

  document.querySelectorAll(`.nav-item[data-page="${page}"], .tab-item[data-page="${page}"]`)
    .forEach(el => el.classList.add('active'));

  window.scrollTo({ top: 0, behavior: 'smooth' });

  if (page === 'products') renderProductTable();
  if (page === 'drugs') renderDrugInteractions();
  if (page === 'guidelines') renderGuidelines();
  if (page === 'dashboard') updateQuickDemo();

  if (sidebarOpen && window.innerWidth <= 768) toggleSidebar();
}

function toggleSidebar() {
  sidebarOpen = !sidebarOpen;
  document.getElementById('sidebar').classList.toggle('open', sidebarOpen);
  let overlay = document.querySelector('.sidebar-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    overlay.onclick = toggleSidebar;
    document.body.appendChild(overlay);
  }
  overlay.classList.toggle('show', sidebarOpen);
}

// ===== ASSESSMENT WORKFLOW =====
function goToStep(step) {
  currentStep = step;
  document.getElementById('step1').classList.toggle('hidden', step !== 1);
  document.getElementById('step2').classList.toggle('hidden', step !== 2);
  document.getElementById('step3').classList.add('hidden');

  document.querySelectorAll('.step').forEach((s, i) => {
    s.classList.remove('active', 'done');
    if (i + 1 < step) s.classList.add('done');
    if (i + 1 === step) s.classList.add('active');
  });
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function readFormData() {
  const get = id => document.getElementById(id)?.value || '';
  const sel = id => Array.from(document.getElementById(id)?.selectedOptions || []).map(o => o.value);
  return {
    age: +get('age') || 65,
    gender: get('gender'),
    height: +get('height') || 170,
    weight: +get('weight') || 58,
    disease: get('disease') || '2B92.0',
    surgery: get('surgery') || null,
    postOpDay: +get('postOpDay') || 0,
    weightLoss: +get('weightLoss') || 0,
    foodIntake: +get('foodIntake') || 0,
    giFunction: get('giFunction') || 'normal',
    swallow: get('swallow') || 'normal',
    renal: get('renal') || 'normal',
    liver: get('liver') || 'normal',
    comorbidities: sel('comorbidities'),
    medications: (get('medications') || '').split(',').map(s => s.trim()).filter(Boolean),
  };
}

function runAssessment() {
  const data = readFormData();
  if (data.weight <= 0 || data.height <= 0) {
    alert('请输入有效的体重和身高');
    return;
  }

  const nrs = scoreNRS2002(data);
  const pathway = determinePathway(data);
  const products = matchProducts(data, pathway);
  const interactions = checkInteractions(data.medications);

  document.getElementById('step1').classList.add('hidden');
  document.getElementById('step2').classList.add('hidden');
  document.getElementById('step3').classList.remove('hidden');

  document.querySelectorAll('.step').forEach(s => { s.classList.remove('active'); s.classList.add('done'); });
  document.querySelector('[data-step="3"]').classList.add('active');

  renderResults(nrs, pathway, products, interactions, data);
  document.getElementById('step3').scrollIntoView({ behavior: 'smooth' });
}

// ===== RENDER RESULTS =====
function renderResults(nrs, pathway, products, interactions, data) {
  const scoreClass = nrs.score >= 5 ? 'high' : nrs.score >= 3 ? 'medium' : 'low';
  const riskLabel = {high:'高风险',medium:'中等风险',low:'低风险'}[nrs.riskLevel];
  const routeColors = {ONS:['ons','#059669'],EN:['en','#d97706'],PN:['pn','#dc2626'],mixed:['mixed','#2563eb']};
  const [routeClass, routeColor] = routeColors[pathway.route] || ['ons','#059669'];

  const lossPct = data.weight > 0 ? (data.weightLoss / data.weight * 100) : 0;
  const refeedingWarn = lossPct > 10 ? `
    <div class="card" style="border-left:4px solid var(--color-danger)">
      <div class="card-header" style="color:var(--color-danger)">⚠ 再喂养综合征高风险</div>
      <div class="card-body">
        <p style="color:var(--color-danger);font-weight:600;margin-bottom:8px">患者3个月体重下降 ${lossPct.toFixed(0)}%，属再喂养综合征高风险(ESPEN 2025 Rec.31)</p>
        <p style="font-size:0.85rem;color:var(--color-text-secondary)">起始EN 10-15 kcal/kg/d (最大50%目标)，缓慢递增4-7天达目标。每日监测K⁺/PO₄/Mg²⁺。开始喂养前补充硫胺素200-300mg IV。</p>
      </div>
    </div>` : '';

  const html = `
    <!-- NRS2002 Score -->
    <div class="card">
      <div class="card-header"><h3>NRS 2002 营养风险筛查</h3><span class="badge badge-teal">ESPEN/CSPEN 2025</span></div>
      <div class="card-body">
        <div class="score-display">
          <div class="score-circle ${scoreClass}">${nrs.score}</div>
          <div class="score-info">
            <h3>${riskLabel} — ${nrs.triggers ? '需启动营养干预' : '暂不需常规干预'}</h3>
            <p>BMI: ${nrs.bmi} kg/m² | 患者${data.age}岁 ${data.gender==='male'?'男':'女'} ${data.weight}kg</p>
            <div class="score-breakdown">
              <span class="badge badge-yellow">营养受损: ${nrs.breakdown.nutrientScore}分</span>
              <span class="badge badge-yellow">疾病严重度: ${nrs.breakdown.diseaseScore}分</span>
              <span class="badge badge-yellow">年龄调整: ${nrs.breakdown.ageScore}分</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Nutrition Pathway -->
    <div class="card">
      <div class="card-header"><h3>营养支持路径</h3></div>
      <div class="card-body">
        <div class="pathway-banner ${routeClass}">
          <div class="pathway-route-label ${routeClass}">${pathway.route}</div>
          <div>
            <p style="font-weight:600;margin-bottom:4px">${pathway.rationale}</p>
            <p style="font-size:0.82rem;color:var(--color-text-secondary)">代谢应激水平: ${pathway.stress} | 基于ESPEN 2025 Rec.4/28/30</p>
          </div>
        </div>
        <div class="targets-row">
          <div class="target-card">
            <div class="target-value">${pathway.energy}</div>
            <div class="target-unit">kcal/日 目标能量</div>
          </div>
          <div class="target-card">
            <div class="target-value">${pathway.protein}</div>
            <div class="target-unit">g/日 目标蛋白质</div>
          </div>
          <div class="target-card">
            <div class="target-value">${pathway.fluid}</div>
            <div class="target-unit">ml/日 目标液体</div>
          </div>
        </div>
      </div>
    </div>

    ${refeedingWarn}

    <!-- FSMP Product Matches -->
    <div class="card">
      <div class="card-header"><h3>FSMP 产品智能匹配</h3><span class="badge badge-green">${products.length} 款匹配</span></div>
      <div class="card-body">
        ${products.map((m, i) => `
          <div class="product-result ${i === 0 ? 'best' : ''}">
            <div class="product-result-header">
              <div>
                <strong style="font-size:1rem">${m.product.name}</strong>
                <span style="color:var(--color-text-secondary);font-size:0.82rem;margin-left:8px">${m.product.mfr}</span>
                ${i === 0 ? '<span class="badge badge-green" style="margin-left:6px">★ 最佳匹配</span>' : ''}
              </div>
              <div class="product-score">${Math.round(m.score)}<span>/100</span></div>
            </div>
            <div class="product-meta">
              <span>⚡ ${m.product.energy} kcal/100ml</span>
              <span>💪 ${m.product.protein}g蛋白 (${m.product.protSrc})</span>
              <span>💧 ${m.product.osm} mOsm/L</span>
              <span>💰 ¥${m.product.price}/${m.product.unit}ml</span>
            </div>
            <div class="product-reasons">${m.reasons.map(r => `<span class="product-reason">${r}</span>`).join('')}</div>
            ${m.warnings.length ? m.warnings.map(w => `<div class="product-warning">⚠ ${w}</div>`).join('') : ''}
          </div>
        `).join('')}
      </div>
    </div>

    <!-- Drug-Nutrient Interactions -->
    <div class="card">
      <div class="card-header"><h3>药物-营养素相互作用</h3><span class="badge badge-blue">${interactions.length} 条</span></div>
      <div class="card-body">
        ${interactions.length === 0 ? '<p style="color:var(--color-text-secondary)">未检测到已知药物-营养素相互作用。</p>' :
          interactions.map(ix => `
            <div class="interaction-item ${ix.sev}">
              <div class="interaction-drug">${ix.drug} → ${ix.nutrient} <span class="badge ${ix.sev==='severe'?'badge-red':ix.sev==='moderate'?'badge-yellow':'badge-teal'}">${ix.sev==='severe'?'严重':ix.sev==='moderate'?'中度':'轻度'}</span> <span style="font-size:0.7rem;color:var(--color-text-muted)">证据: ${ix.grade}</span></div>
              <div class="interaction-mech">${ix.mech}</div>
              <div class="interaction-rec">💡 ${ix.rec}</div>
              <div style="font-size:0.7rem;color:var(--color-text-muted);margin-top:2px">📚 ${ix.ref}</div>
            </div>
          `).join('')
        }
      </div>
    </div>

    <!-- Monitoring Plan -->
    <div class="card">
      <div class="card-header"><h3>监测计划</h3></div>
      <div class="card-body">
        <ul class="monitoring-list">
          <li>每日：体重、出入量、生命体征</li>
          <li>第1-3天：K⁺, PO₄³⁻, Mg²⁺, 血糖 (每日检测)</li>
          <li>第4-7天：K⁺, PO₄³⁻, Mg²⁺, 血糖 (隔日)，肝功能、前白蛋白</li>
          <li>第7天：NRS2002复筛，前白蛋白，氮平衡评估</li>
          ${data.renal !== 'normal' ? '<li>每日：肾功能(BUN, Cr), 尿量</li>' : ''}
          ${data.liver !== 'normal' ? '<li>每周：肝功能全套, 凝血功能, 血氨</li>' : ''}
          ${pathway.route === 'EN' ? '<li>每4-6h：胃残余量(GRV)，>250ml暂停EN评估</li>' : ''}
          ${data.giFunction === 'impaired' ? '<li>每日：腹胀/腹泻评估，EN输注速率调整</li>' : ''}
        </ul>
      </div>
    </div>
  `;

  document.getElementById('resultsContainer').innerHTML = html;
}

// ===== PRODUCT TABLE =====
let productPage = 0;
const PAGE_SIZE = 15;

function renderProductTable(filter = '') {
  let products = FSMP_PRODUCTS;
  const catFilter = document.getElementById('productCategory')?.value || '';
  const searchText = (document.getElementById('productSearch')?.value || '').toLowerCase();

  if (catFilter) products = products.filter(p => p.cat.includes(catFilter) || (catFilter==='组件'&&p.cat.includes('组件')));
  if (searchText) products = products.filter(p => p.name.toLowerCase().includes(searchText) || p.mfr.toLowerCase().includes(searchText) || p.reg.toLowerCase().includes(searchText));

  document.getElementById('productCount').textContent = `共 ${products.length} 款产品`;
  const totalPages = Math.ceil(products.length / PAGE_SIZE);
  productPage = Math.min(productPage, totalPages - 1);

  const start = productPage * PAGE_SIZE;
  const pageProducts = products.slice(start, start + PAGE_SIZE);

  document.getElementById('productTableBody').innerHTML = pageProducts.map(p => `
    <tr>
      <td class="reg-number">国食注字${p.reg}</td>
      <td><strong>${p.name}</strong></td>
      <td>${p.mfr}</td>
      <td><span class="badge badge-teal">${p.cat}</span></td>
      <td>${p.form}</td>
    </tr>
  `).join('');

  let pagHTML = '';
  if (totalPages > 1) {
    pagHTML += `<button onclick="productPage=Math.max(0,productPage-1);renderProductTable()" ${productPage===0?'disabled':''}>←</button>`;
    for (let i = 0; i < totalPages; i++) {
      pagHTML += `<button class="${i===productPage?'active':''}" onclick="productPage=${i};renderProductTable()">${i+1}</button>`;
    }
    pagHTML += `<button onclick="productPage=Math.min(${totalPages-1},productPage+1);renderProductTable()" ${productPage===totalPages-1?'disabled':''}>→</button>`;
  }
  document.getElementById('productPagination').innerHTML = pagHTML;
}

// ===== DRUG INTERACTIONS PAGE =====
function renderDrugInteractions() {
  const entries = Object.entries(DRUG_INTERACTIONS);
  const html = entries.map(([atc, data]) => `
    <div class="card">
      <div class="card-header">
        <h3>${data.drug}</h3>
        <span class="badge badge-blue">${data.class}</span>
      </div>
      <div class="card-body">
        ${data.interactions.map(ix => `
          <div class="interaction-item ${ix.sev}">
            <div class="interaction-drug">
              → ${ix.nutrient}
              <span class="badge ${ix.sev==='severe'?'badge-red':ix.sev==='moderate'?'badge-yellow':'badge-teal'}">
                ${ix.sev==='severe'?'严重':ix.sev==='moderate'?'中度':'轻度'}
              </span>
              <span style="font-size:0.7rem;margin-left:6px">证据等级: ${ix.grade}</span>
            </div>
            <div class="interaction-mech">${ix.mech}</div>
            <div class="interaction-rec">💡 ${ix.rec}</div>
            <div style="font-size:0.7rem;color:var(--color-text-muted);margin-top:2px">📚 ${ix.ref}</div>
          </div>
        `).join('')}
      </div>
    </div>
  `).join('');
  document.getElementById('drugInteractionsContainer').innerHTML = html;
}

// ===== GUIDELINES PAGE =====
function renderGuidelines() {
  const guidelines = [
    {
      title:"ESPEN Guideline on Clinical Nutrition in Surgery — Update 2025",
      source:"Weimann A, Braga M, Carli F, et al. Clinical Nutrition, 2025;53:222-261",
      recs:[
        {text:"严重营养不良和/或高代谢风险患者应接受术前营养治疗，即使推迟手术(10-14天)",grade:"A",agree:"93%"},
        {text:"术后应尽早(数小时内)开始经口或管饲喂养，患者清醒+血流动力学稳定",grade:"A",agree:"96%"},
        {text:"口腔摄入<50%需求持续7天→24h内启动EN(尤其上消化道肿瘤术后)",grade:"A/B",agree:"92%"},
        {text:"食管切除术/全胃切除术/胰十二指肠切除术→营养不良或高代谢风险者考虑术中留置鼻肠管/空肠造口管",grade:"B",agree:"89%"},
        {text:"预防再喂养综合征：EN起始10-30mL/h，电解质稳定后谨慎递增(可能需5天达目标量)",grade:"GPP",agree:"95%"},
      ]
    },
    {
      title:"ERAS® Colorectal Surgery Guidelines 2025",
      source:"Gustafsson UO, Rockall TA, Wexner S, et al. Surgery, 2025;184:109397",
      recs:[
        {text:"所有患者强制进行营养筛查",grade:"A",agree:""},
        {text:"免疫营养推荐用于营养不良患者(2025新变化：针对性而非普适)",grade:"A",agree:""},
        {text:"碳水化合物负荷证据强度较前版减弱",grade:"B",agree:""},
        {text:"早期经口进食+口服营养补充剂(ONS)",grade:"A",agree:""},
        {text:"活动: POD1起≥3小时/日直至出院",grade:"A",agree:""},
      ]
    },
    {
      title:"CSPEN 成人患者营养不良诊断与应用指南 (2025版)",
      source:"中华医学杂志, 2025;105(13). 27个问题, 38条推荐意见",
      recs:[
        {text:"采用GLIM标准进行营养不良诊断(结合中国人群数据)",grade:"A",agree:""},
        {text:"入院24小时内使用NRS 2002完成营养风险筛查",grade:"A",agree:""},
        {text:"NRS 2002评分≥3分提示存在营养风险，需营养支持",grade:"A",agree:""},
        {text:"营养风险应作为诊断写入病历首页",grade:"GPP",agree:""},
        {text:"流程：营养筛查→评估及诊断→干预及监测 全程化管理",grade:"A",agree:""},
      ]
    },
    {
      title:"CSPEN 胰腺外科围手术期全程化营养管理指南 (2025版)",
      source:"18个问题, 23条推荐意见",
      recs:[
        {text:"术前7天营养'打底'+术后早期肠内营养+出院后30天延续管理",grade:"A",agree:""},
        {text:"首选肠内营养（鼻胃管/鼻肠管/胃造瘘/空肠造瘘）",grade:"A",agree:""},
        {text:"肠外营养适应证：胃肠道功能障碍、高分解代谢状态、肿瘤放化疗严重胃肠道反应",grade:"B",agree:""},
      ]
    }
  ];

  const html = guidelines.map(g => `
    <div class="guideline-card">
      <h3>${g.title}</h3>
      <div class="guideline-source">📄 ${g.source}</div>
      ${g.recs.map(r => `
        <div class="guideline-rec">
          <span class="guideline-grade grade-${r.grade}">${r.grade}</span>
          ${r.text}
          ${r.agree ? `<span style="font-size:0.75rem;color:var(--color-text-muted)">[共识: ${r.agree}]</span>` : ''}
        </div>
      `).join('')}
    </div>
  `).join('');
  document.getElementById('guidelinesContainer').innerHTML = html;
}

// ===== DASHBOARD QUICK DEMO =====
function updateQuickDemo() {
  const disease = document.getElementById('quickDisease')?.value || '2B92.0';
  const surgery = document.getElementById('quickSurgery')?.value || 'colorectal_resection';
  const intake = parseInt(document.getElementById('quickIntake')?.value || '50');

  const demoData = {
    age: 65, gender: 'male', height: 170, weight: 58,
    disease, surgery: surgery || null,
    postOpDay: surgery ? 3 : 0,
    weightLoss: 4, foodIntake: intake,
    giFunction: 'normal', swallow: 'normal', renal: 'normal', liver: 'normal',
    comorbidities: [], medications: []
  };

  const nrs = scoreNRS2002(demoData);
  const pathway = determinePathway(demoData);

  const scoreClass = nrs.score >= 5 ? 'high' : nrs.score >= 3 ? 'medium' : 'low';
  const riskLabel = nrs.riskLevel === 'high' ? '高风险 — 紧急干预' : nrs.riskLevel === 'medium' ? '中等风险 — 需干预' : '低风险 — 周复查';

  document.getElementById('quickScore').textContent = nrs.score;
  document.getElementById('quickScore').className = `score-badge ${scoreClass}`;
  document.getElementById('quickRisk').textContent = riskLabel;
  document.getElementById('quickRoute').textContent = `推荐通路: ${pathway.route} | 能量: ${pathway.energy}kcal | 蛋白: ${pathway.protein}g`;
}

// ===== INIT =====
document.addEventListener('DOMContentLoaded', () => {
  updateQuickDemo();

  // Close sidebar on desktop resize
  window.addEventListener('resize', () => {
    if (window.innerWidth > 768 && sidebarOpen) {
      sidebarOpen = false;
      document.getElementById('sidebar').classList.remove('open');
      const overlay = document.querySelector('.sidebar-overlay');
      if (overlay) overlay.classList.remove('show');
    }
  });
});
