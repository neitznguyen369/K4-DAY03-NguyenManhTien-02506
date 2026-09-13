const input = document.querySelector('#questionInput');
const runButton = document.querySelector('#runButton');
const timeline = document.querySelector('#timeline');
const counter = document.querySelector('#stepCounter');
const state = document.querySelector('#runState');
const timer = document.querySelector('#runTimer');
const providerName = document.querySelector('#providerName');
const mcpStatus = document.querySelector('#mcpStatus');

const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
const pretty = (value) => escapeHtml(JSON.stringify(value, null, 2));

async function loadHealth() {
  try {
    const response = await fetch('/api/health', { cache:'no-store' });
    const data = await response.json();
    providerName.textContent = data.provider.replace('Provider', '');
    mcpStatus.textContent = data.mcp?.status === 'online' ? `MCP online · ${data.mcp.tools} tools` : 'MCP offline';
  } catch { providerName.textContent = 'offline'; mcpStatus.textContent = 'MCP offline'; }
}

function renderTrace(question, trace) {
  const action = trace.find((item) => item.action_type === 'TOOL_EXECUTION');
  const answer = trace.find((item) => item.action_type === 'FINAL_ANSWER');
  const thought = action?.thought || answer?.thought || 'Đang phân loại yêu cầu và kiểm tra xem có cần dữ liệu trực tiếp hay không.';
  const cards = [
    { type:'thought', number:'01', title:'Thought', tag:'REASONING', body:thought },
    action ? { type:'action', number:'02', title:'Action', tag:'PROPOSED TOOL', body:`${action.tool_name} được chọn để xử lý yêu cầu.`, data:action.arguments } : { type:'action', number:'02', title:'Action', tag:'NO TOOL', body:'Không cần gọi tool. Agent chọn trả lời trực tiếp từ kiến thức chung.' },
    action ? { type:'observation', number:'03', title:'Observation', tag:'MCP RESULT', body:`MCP trả về trạng thái ${action.observation?.status || 'UNKNOWN'}.`, data:action.observation } : { type:'observation', number:'03', title:'Observation', tag:'SKIPPED', body:'Không có Observation vì không phát sinh tool call.' },
    { type:'answer', number:'04', title:'Final answer', tag:'DELIVERED', body:answer?.output || 'Agent chưa tạo được câu trả lời.' }
  ];
  timeline.className = 'timeline';
  timeline.innerHTML = cards.map((card, index) => `<article class="trace-card ${card.type}" style="animation-delay:${index * 110}ms"><span class="trace-number">${card.number}</span><h3 class="trace-title">${card.title}</h3><span class="trace-tag">${card.tag}</span><div class="trace-body">${escapeHtml(card.body)}${card.data ? `<pre>${pretty(card.data)}</pre>` : ''}</div></article>`).join('');
  counter.textContent = `${cards.length} / 4 steps`;
}

async function runAgent() {
  const question = input.value.trim();
  if (!question) { input.focus(); return; }
  runButton.disabled = true; state.textContent = 'THINKING'; state.style.color = '#d4a928'; timer.textContent = 'Following the agent...';
  timeline.className = 'timeline empty-state'; timeline.innerHTML = '<div class="empty-orbit">✦</div><p>Agent đang phân tích câu hỏi...</p>'; counter.textContent = 'running';
  const started = performance.now();
  try { const response = await fetch('/api/chat', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({ question }) }); const data = await response.json(); if (!response.ok) throw new Error(data.error || 'Request failed'); renderTrace(question, data.trace || []); state.textContent = 'COMPLETE'; state.style.color = '#1e7257'; timer.textContent = `${Math.round(performance.now() - started)} ms · trace captured`; } catch (error) { timeline.className = 'timeline empty-state'; timeline.innerHTML = `<p>Không thể chạy agent: ${escapeHtml(error.message)}</p>`; state.textContent = 'ERROR'; state.style.color = '#c6574b'; timer.textContent = 'Request failed'; } finally { runButton.disabled = false; }
}

runButton.addEventListener('click', runAgent);
input.addEventListener('keydown', (event) => { if (event.key === 'Enter') runAgent(); });
document.querySelectorAll('[data-question]').forEach((button) => button.addEventListener('click', () => { input.value = button.dataset.question; runAgent(); }));
loadHealth();
setInterval(loadHealth, 3000);