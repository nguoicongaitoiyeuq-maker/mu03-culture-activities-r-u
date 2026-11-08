const slides = ['4.webp'];
let slideIndex = 0;
let slideFront = true;
let state = { user: '', today: '', role: 'MEMBER', canCreateTicket: false, canViewCfm: false, canViewData: false, teamsConfigured: false, tickets: [], dashboardTickets: [], families: [], day: 'all', media: [] };
const CFM_EMAILS = new Set([
  'thanhphat.duong@ttigroup.com.vn',
  'trunghieu.ho@ttigroup.com.vn',
  'thebao.vo@ttigroup.com.vn',
  'son.le@ttigroup.com.vn',
  'catnhan.le@ttigroup.com.vn',
  'tuannhu.le01@ttigroup.com.vn',
  'minhquan.pham1@ttigroup.com.vn',
  'hailam.hoang@ttigroup.com.vn',
  'thanhdat.le2@ttigroup.com.vn',
  'hongthai.vu@ttigroup.com.vn',
  'khachieu.nguyen01@ttigroup.com.vn'
]);
let leaderMedia = {};
let expandedTickets = {};

const api = (url, opt) => {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  return fetch(url, Object.assign({ headers: { 'Content-Type': 'application/json' }, signal: controller.signal }, opt || {}))
    .then(async (response) => {
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || data.message || 'Request failed');
      }
      return response.json();
    })
    .catch((error) => {
      if (error.name === 'AbortError') throw new Error('Request timed out. Please retry.');
      throw error;
    })
    .finally(() => clearTimeout(timeout));
};

const esc = (value) => String(value || '').replace(/[&<>'"]/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
}[char]));

const leaderName = (value) => {
  const name = String(value || '').trim();
  return !name || name === 'Leader Inbox' || name.toLowerCase() === 'thanhdat.le2@ttigroup.com.vn'
    ? 'Le Thanh Dat 1 (VN.MIL-PT-PRO-TOOL)' : name;
};

const badge = (status) => `<span class="badge ${status === 'CLOSED' || status.includes('COMPLETED') ? 'green' : status.includes('WAITING') ? 'amber' : status === 'READ' ? 'red' : 'gray'}">${esc(status)}</span>`;
