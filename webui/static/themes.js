/* Atlas — Theme Manager
   6 主题系统: midnight, phosphor, violet, ember, frost, rose */

const AtlasThemes = (() => {
  const THEME_COLORS = {
    midnight: '#4a7ab5', phosphor: '#7ccf7c',
    violet: '#9b7df0', ember: '#e87a5a',
    frost: '#60c8e8', rose: '#dc78b0',
  };

  function apply(name) {
    document.documentElement.setAttribute('data-theme', name);
    localStorage.setItem('atlas-theme', name);
    document.querySelectorAll('.theme-dot').forEach(d =>
      d.classList.toggle('active', d.dataset.theme === name)
    );
    const label = name.charAt(0).toUpperCase() + name.slice(1);
    const tag = document.getElementById('versionTag');
    if (tag) tag.textContent = `Atlas · ${label}`;
    return name;
  }

  function getStored() {
    return localStorage.getItem('atlas-theme') || 'midnight';
  }

  return { apply, getStored, THEME_COLORS };
})();
