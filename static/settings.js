const DEFAULTS = {
  theme: 'light',
  fontsize: 'medium',
  font: 'sans',
  accent: 'blue',
  width: 'narrow',
  lang: 'en'
};

const T = {
  en: {
    settings: 'Settings',
    language: 'Language',
    theme: 'Theme', light: 'Light', dark: 'Dark',
    fontSize: 'Font Size', small: 'Small', medium: 'Medium', large: 'Large',
    font: 'Font', sans: 'Sans-serif', serif: 'Serif',
    accent: 'Accent Color', blue: 'Blue', green: 'Green', purple: 'Purple', orange: 'Orange',
    width: 'Content Width', narrow: 'Narrow', wide: 'Wide'
  },
  sr: {
    settings: 'Podešavanja',
    language: 'Jezik',
    theme: 'Tema', light: 'Svetla', dark: 'Tamna',
    fontSize: 'Veličina fonta', small: 'Mali', medium: 'Srednji', large: 'Veliki',
    font: 'Font', sans: 'Sans-serif', serif: 'Serif',
    accent: 'Boja akcenta', blue: 'Plava', green: 'Zelena', purple: 'Ljubičasta', orange: 'Narandžasta',
    width: 'Širina sadržaja', narrow: 'Uska', wide: 'Široka'
  }
};

function loadSettings() {
  const settings = {};
  for (const [key, def] of Object.entries(DEFAULTS)) {
    settings[key] = localStorage.getItem('school-' + key) || def;
  }
  return settings;
}

function applySettings(settings) {
  const html = document.documentElement;
  html.setAttribute('data-theme', settings.theme);
  html.setAttribute('data-fontsize', settings.fontsize);
  html.setAttribute('data-font', settings.font);
  html.setAttribute('data-accent', settings.accent);
  html.setAttribute('data-width', settings.width);
  html.setAttribute('data-lang', settings.lang);
  const tc = document.getElementById('meta-theme-color');
  if (tc) tc.content = settings.theme === 'dark' ? '#121218' : '#f7f7f5';
}

function saveSetting(key, value) {
  localStorage.setItem('school-' + key, value);
  if (key === 'lang') {
    document.cookie = 'school_lang=' + value + ';path=/;max-age=31536000';
    location.reload();
    return;
  }
  applySettings(loadSettings());
  updateActiveButtons();
}

function updateActiveButtons() {
  const settings = loadSettings();
  document.querySelectorAll('.setting-btn').forEach(btn => {
    btn.classList.toggle('active', settings[btn.dataset.key] === btn.dataset.value);
  });
}

function createSettingsPanel() {
  const settings = loadSettings();
  const t = T[settings.lang] || T.en;

  const isNewTopic = /^\/new-topic/.test(window.location.pathname);

  const addBtn = document.createElement('a');
  addBtn.href = '/new-topic';
  addBtn.className = 'fab-toggle fab-add';
  addBtn.setAttribute('aria-label', t.language === 'sr' ? 'Nova tema' : 'New Topic');
  addBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>';
  if (isNewTopic) addBtn.style.display = 'none';

  const gear = document.createElement('button');
  gear.className = 'fab-toggle fab-settings';
  gear.setAttribute('aria-label', t.settings);
  gear.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>';

  const panel = document.createElement('div');
  panel.className = 'settings-panel';
  panel.innerHTML = `
    <h3>${t.settings}</h3>
    <div class="setting-group">
      <label>${t.language}</label>
      <div class="setting-options">
        <button class="setting-btn" data-key="lang" data-value="en">English</button>
        <button class="setting-btn" data-key="lang" data-value="sr">Srpski</button>
      </div>
    </div>
    <div class="setting-group">
      <label>${t.theme}</label>
      <div class="setting-options">
        <button class="setting-btn" data-key="theme" data-value="light">${t.light}</button>
        <button class="setting-btn" data-key="theme" data-value="dark">${t.dark}</button>
      </div>
    </div>
    <div class="setting-group">
      <label>${t.fontSize}</label>
      <div class="setting-options">
        <button class="setting-btn" data-key="fontsize" data-value="small">${t.small}</button>
        <button class="setting-btn" data-key="fontsize" data-value="medium">${t.medium}</button>
        <button class="setting-btn" data-key="fontsize" data-value="large">${t.large}</button>
      </div>
    </div>
    <div class="setting-group">
      <label>${t.font}</label>
      <div class="setting-options">
        <button class="setting-btn" data-key="font" data-value="sans">${t.sans}</button>
        <button class="setting-btn" data-key="font" data-value="serif">${t.serif}</button>
      </div>
    </div>
    <div class="setting-group">
      <label>${t.accent}</label>
      <div class="setting-options">
        <button class="setting-btn" data-key="accent" data-value="blue">${t.blue}</button>
        <button class="setting-btn" data-key="accent" data-value="green">${t.green}</button>
        <button class="setting-btn" data-key="accent" data-value="purple">${t.purple}</button>
        <button class="setting-btn" data-key="accent" data-value="orange">${t.orange}</button>
      </div>
    </div>
    <div class="setting-group">
      <label>${t.width}</label>
      <div class="setting-options">
        <button class="setting-btn" data-key="width" data-value="narrow">${t.narrow}</button>
        <button class="setting-btn" data-key="width" data-value="wide">${t.wide}</button>
      </div>
    </div>
  `;

  panel.addEventListener('click', e => {
    const btn = e.target.closest('.setting-btn');
    if (btn) saveSetting(btn.dataset.key, btn.dataset.value);
  });

  gear.addEventListener('click', e => {
    e.stopPropagation();
    panel.classList.toggle('open');
  });

  document.addEventListener('click', e => {
    if (!panel.contains(e.target) && e.target !== gear) {
      panel.classList.remove('open');
    }
  });

  const mountTarget = document.querySelector('.chat-page') || document.body;
  mountTarget.appendChild(addBtn);
  mountTarget.appendChild(gear);
  mountTarget.appendChild(panel);
  updateActiveButtons();
}

document.addEventListener('DOMContentLoaded', () => {
  applySettings(loadSettings());
  createSettingsPanel();
});
