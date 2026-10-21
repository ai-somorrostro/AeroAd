var I18n = (function () {
    var currentLang = 'en';
    var supportedLangs = ['en', 'fr', 'es', 'ru'];

    function detectLanguage() {
        var browserLangs = navigator.languages || [navigator.language || navigator.userLanguage];
        for (var i = 0; i < browserLangs.length; i++) {
            var code = browserLangs[i].toLowerCase().split('-')[0];
            if (supportedLangs.indexOf(code) !== -1) {
                return code;
            }
        }
        return 'en';
    }

    function getStoredLang() {
        try {
            var stored = localStorage.getItem('hotspot-lang');
            if (stored && supportedLangs.indexOf(stored) !== -1) {
                return stored;
            }
        } catch (e) { /* localStorage not available */ }
        return null;
    }

    function setStoredLang(lang) {
        try {
            localStorage.setItem('hotspot-lang', lang);
        } catch (e) { /* localStorage not available */ }
    }

    function t(key) {
        if (TRANSLATIONS[currentLang] && TRANSLATIONS[currentLang][key]) {
            return TRANSLATIONS[currentLang][key];
        }
        if (TRANSLATIONS['en'][key]) {
            return TRANSLATIONS['en'][key];
        }
        return key;
    }

    function applyTranslations() {
        // Apply data-i18n attributes
        var elements = document.querySelectorAll('[data-i18n]');
        for (var i = 0; i < elements.length; i++) {
            var el = elements[i];
            var key = el.getAttribute('data-i18n');
            el.innerHTML = t(key);
        }

        // Apply data-i18n-placeholder attributes
        var placeholders = document.querySelectorAll('[data-i18n-placeholder]');
        for (var i = 0; i < placeholders.length; i++) {
            var el = placeholders[i];
            var key = el.getAttribute('data-i18n-placeholder');
            el.setAttribute('placeholder', t(key));
        }

        // Apply data-i18n-value attributes
        var values = document.querySelectorAll('[data-i18n-value]');
        for (var i = 0; i < values.length; i++) {
            var el = values[i];
            var key = el.getAttribute('data-i18n-value');
            el.setAttribute('value', t(key));
        }

        // Update select options with data-i18n-option attributes
        var options = document.querySelectorAll('[data-i18n-option]');
        for (var i = 0; i < options.length; i++) {
            var el = options[i];
            var key = el.getAttribute('data-i18n-option');
            el.textContent = t(key);
        }

        // Update language dropdown labels
        var langLabels = document.querySelectorAll('.lang-option-label');
        for (var i = 0; i < langLabels.length; i++) {
            var el = langLabels[i];
            var lang = el.getAttribute('data-lang');
            if (TRANSLATIONS[lang]) {
                el.textContent = TRANSLATIONS[lang].langName;
            }
        }

        // Update active state in dropdown
        var currentLabels = document.querySelectorAll('.lang-current-label');
        for (var i = 0; i < currentLabels.length; i++) {
            if (TRANSLATIONS[currentLang]) {
                currentLabels[i].textContent = TRANSLATIONS[currentLang].langName;
            }
        }

        var dropdownItems = document.querySelectorAll('.lang-dropdown-item');
        for (var i = 0; i < dropdownItems.length; i++) {
            dropdownItems[i].classList.remove('active');
            if (dropdownItems[i].getAttribute('data-lang') === currentLang) {
                dropdownItems[i].classList.add('active');
            }
        }

        // Set page lang attribute
        document.documentElement.lang = currentLang;
    }

    function switchLang(lang) {
        if (supportedLangs.indexOf(lang) === -1) return;
        currentLang = lang;
        setStoredLang(lang);
        applyTranslations();
    }

    function init() {
        currentLang = getStoredLang() || detectLanguage();
        applyTranslations();

        // Bind language switcher clicks
        var items = document.querySelectorAll('.lang-dropdown-item');
        for (var i = 0; i < items.length; i++) {
            (function (item) {
                item.addEventListener('click', function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    var lang = item.getAttribute('data-lang');
                    switchLang(lang);
                    closeDropdown();
                });
            })(items[i]);
        }

        // Toggle dropdown on button click
        var toggles = document.querySelectorAll('.lang-toggle');
        for (var i = 0; i < toggles.length; i++) {
            toggles[i].addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                var dd = this.parentNode.querySelector('.lang-dropdown');
                if (dd) {
                    dd.classList.toggle('open');
                }
            });
        }

        // Close dropdown when clicking outside
        document.addEventListener('click', closeDropdown);
    }

    function closeDropdown() {
        var dropdowns = document.querySelectorAll('.lang-dropdown.open');
        for (var i = 0; i < dropdowns.length; i++) {
            dropdowns[i].classList.remove('open');
        }
    }

    return {
        init: init,
        switchLang: switchLang,
        t: t
    };
})();

document.addEventListener('DOMContentLoaded', I18n.init);
