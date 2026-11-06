const slides = ['4.webp'];
let slideIndex = 0;
let slideFront = true;
let state = { user: '', today: '', role: 'MEMBER', canCreateTicket: false, canViewCfm: false, teamsConfigured: false, tickets: [], families: [], day: 'all', media: [] };
let leaderMedia = {};
let expandedTickets = {};

const api = (url, opt) => fetch(url, Object.assign({ headers: { 'Content-Type': 'application/json' } }, opt || {}))
  .then(async (response) => {
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || data.message || 'Request failed');
    }
    return response.json();
  });

const esc = (value) => String(value || '').replace(/[&<>'"]/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
}[char]));

const leaderName = (value) => {
  const name = String(value || '').trim();
  return !name || name === 'Leader Inbox' || name.toLowerCase() === 'thanhdat.le2@ttigroup.com.vn'
    ? 'Le Thanh Dat 1 (VN.MIL-PT-PRO-TOOL)' : name;
};

const badge = (status) => `<span class="badge ${status === 'CLOSED' || status.includes('COMPLETED') ? 'green' : status.includes('WAITING') ? 'amber' : status === 'READ' ? 'red' : 'gray'}">${esc(status)}</span>`;
