/**
 * Daňová evidencia - Hlavný JavaScript
 * Obsahuje: témy, hustota, formátovanie dátumu v status bare, pomocné funkcie
 */

(function() {
    'use strict';

    // ==================== INICIALIZÁCIA ====================
    document.addEventListener('DOMContentLoaded', function() {
        initTheme();
        initDensity();
        initStatusBarDate();
        initTooltips();
        loadAndApplySettings();
    });

    // ==================== NAČÍTANIE NASTAVENÍ ZO SERVERA ====================
    function loadAndApplySettings() {
        fetch('/api/zobrazenie')
            .then(function(r) { return r.json(); })
            .then(function(z) {
                if (!z) return;
                // Téma
                if (z.tema) {
                    setTheme(z.tema);
                }
                // Hustota
                if (z.hustota) {
                    setDensity(z.hustota);
                }
                // Písmo
                if (z.font_family) {
                    document.documentElement.style.setProperty('--font-family-base', z.font_family);
                }
                if (z.font_size) {
                    document.documentElement.style.fontSize = z.font_size + 'px';
                }
            })
            .catch(function(e) { console.error('Chyba pri načítaní nastavení:', e); });
    }

    // ==================== TÉMA (LIGHT/DARK) ====================
    function initTheme() {
        // Necháme na loadAndApplySettings, ktoré načíta zo servera
    }

    window.setTheme = function(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('de_theme', theme);

        // Aktualizovať ikonu tlačidla ak existuje
        const themeBtn = document.getElementById('themeToggleBtn');
        if (themeBtn) {
            const icon = themeBtn.querySelector('i');
            if (icon) {
                icon.className = theme === 'dark' ? 'bi bi-sun' : 'bi bi-moon';
            }
        }
    };

    window.toggleTheme = function() {
        const current = document.documentElement.getAttribute('data-theme') || 'light';
        const next = current === 'light' ? 'dark' : 'light';
        setTheme(next);
        // Uložiť na server
        saveSetting('tema', next);
    };

    // ==================== HUSTOTA (COMPACT/NORMAL/COMFORTABLE) ====================
    function initDensity() {
        // Necháme na loadAndApplySettings
    }

    window.setDensity = function(density) {
        document.documentElement.setAttribute('data-density', density);
        localStorage.setItem('de_density', density);
    };

    window.changeDensity = function(density) {
        setDensity(density);
        saveSetting('hustota', density);
    };

    // ==================== ULOŽENIE NASTAVENIA NA SERVER ====================
    function saveSetting(key, value) {
        var data = {};
        data[key] = value;
        fetch('/api/zobrazenie', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        }).catch(function(e) { console.error('Chyba pri ukladaní nastavenia:', e); });
    }

    window.saveZobrazenieSettings = function(data) {
        fetch('/api/zobrazenie', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        }).then(function(r) { return r.json(); })
          .then(function() {
              // Aplikovať okamžite
              if (data.tema) setTheme(data.tema);
              if (data.hustota) setDensity(data.hustota);
              if (data.font_family) {
                  document.documentElement.style.setProperty('--font-family-base', data.font_family);
              }
              if (data.font_size) {
                  document.documentElement.style.fontSize = data.font_size + 'px';
              }
          })
          .catch(function(e) { console.error('Chyba pri ukladaní nastavení:', e); });
    };

    // ==================== STATUS BAR DÁTUM ====================
    function initStatusBarDate() {
        const datePicker = document.getElementById('statusBarDatePicker');
        const dateDisplay = document.getElementById('statusBarDateDisplay');

        if (!datePicker || !dateDisplay) return;

        // Nájsť span pre hodnotu dátumu
        const dateValueSpan = dateDisplay.querySelector('.date-value') || dateDisplay;

        // Formátovať dátum podľa nastavení
        function formatDateBySettings(isoDate) {
            if (!isoDate) return '';
            var parts = isoDate.split('-');
            if (parts.length !== 3) return isoDate;

            var year = parseInt(parts[0], 10);
            var month = parseInt(parts[1], 10);
            var day = parseInt(parts[2], 10);

            // Načítať formát zo servera cez data atribút alebo fallback
            var fmt = document.documentElement.getAttribute('data-date-format') || 'sk';

            if (fmt === 'iso') {
                return isoDate;
            } else if (fmt === 'eu') {
                return pad(day) + '. ' + pad(month) + '. ' + year;
            } else if (fmt === 'us') {
                return pad(month) + '/' + pad(day) + '/' + year;
            } else if (fmt === 'sk_long') {
                var mesiace = ['', 'január', 'február', 'marec', 'apríl', 'máj', 'jún',
                               'júl', 'august', 'september', 'október', 'november', 'december'];
                return day + '. ' + mesiace[month] + ' ' + year;
            } else {
                // sk
                var mesiace = ['', 'jan', 'feb', 'mar', 'apr', 'máj', 'jún',
                               'júl', 'aug', 'sep', 'okt', 'nov', 'dec'];
                return day + '. ' + mesiace[month] + ' ' + year;
            }
        }

        function pad(n) {
            return n < 10 ? '0' + n : String(n);
        }

        // Aktualizovať zobrazenie pri zmene
        datePicker.addEventListener('change', function() {
            dateValueSpan.textContent = formatDateBySettings(this.value);
        });

        // Inicializovať zobrazenie
        dateValueSpan.textContent = formatDateBySettings(datePicker.value);
    }

    // ==================== TOOLTIPS ====================
    function initTooltips() {
        // Bootstrap tooltips (ak sú použité)
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
            tooltipTriggerList.forEach(function(el) {
                new bootstrap.Tooltip(el);
            });
        }
    }

    // ==================== POMOCNÉ FUNKCIE ====================

    /**
     * Formátuje sumu v slovenskom formáte
     */
    window.formatSlovakAmount = function(amount, currency) {
        currency = currency || 'EUR';
        if (amount === null || amount === undefined) amount = 0;

        var num = parseFloat(amount);
        var text = num.toLocaleString('sk-SK', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });

        return text + ' ' + currency;
    };

    /**
     * Formátuje dátum do slovenského formátu
     */
    window.formatSlovakDate = function(dateStr) {
        if (!dateStr) return '';

        var d;
        if (typeof dateStr === 'string') {
            var parts = dateStr.split('-');
            if (parts.length === 3) {
                d = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
            } else {
                d = new Date(dateStr);
            }
        } else {
            d = dateStr;
        }

        if (isNaN(d.getTime())) return String(dateStr);

        var mesiace = ['jan', 'feb', 'mar', 'apr', 'máj', 'jún',
                       'júl', 'aug', 'sep', 'okt', 'nov', 'dec'];

        return d.getDate() + '. ' + mesiace[d.getMonth()] + ' ' + d.getFullYear();
    };

    /**
     * Formátuje dátum do dlhého slovenského formátu
     */
    window.formatSlovakDateLong = function(dateStr) {
        if (!dateStr) return '';

        var d;
        if (typeof dateStr === 'string') {
            var parts = dateStr.split('-');
            if (parts.length === 3) {
                d = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
            } else {
                d = new Date(dateStr);
            }
        } else {
            d = dateStr;
        }

        if (isNaN(d.getTime())) return String(dateStr);

        var mesiace = ['január', 'február', 'marec', 'apríl', 'máj', 'jún',
                       'júl', 'august', 'september', 'október', 'november', 'december'];

        return d.getDate() + '. ' + mesiace[d.getMonth()] + ' ' + d.getFullYear();
    };

    /**
     * Skopíruje text do schránky
     */
    window.copyToClipboard = function(text) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).catch(function(err) {
                console.error('Chyba pri kopírovaní:', err);
            });
        } else {
            // Fallback
            var textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
        }
    };

    /**
     * Zobrazí potvrdzovací dialóg
     */
    window.confirmAction = function(message) {
        return confirm(message);
    };

})();
