document.addEventListener('DOMContentLoaded', function () {
    // LOGIN PAGE
    var loginBtn = document.getElementById('loginBtn');
    if (loginBtn) {
        loginBtn.addEventListener('click', function () {
            loginBtn.disabled = true;
            loginBtn.querySelector('.btn-text').textContent = I18n.t('connecting');
            setTimeout(function () {
                window.location.href = 'survey.html';
            }, 800);
        });
    }

    // SURVEY PAGE
    var surveyForm = document.getElementById('surveyForm');
    if (surveyForm) {
        surveyForm.addEventListener('submit', function (e) {
            e.preventDefault();

            var age = document.getElementById('age').value;
            var name = document.getElementById('name').value;
            var email = document.getElementById('email').value;
            var country = document.getElementById('country').value;

            if (!age || !name || !email || !country) {
                alert('Please fill in all fields.');
                return;
            }

            // Store survey data in localStorage for CSV collection
            var surveyData = {
                age: parseInt(age, 10),
                name: name.trim(),
                email: email.trim(),
                country: country,
                timestamp: new Date().toISOString()
            };
            try {
                localStorage.setItem('hotspot-survey', JSON.stringify(surveyData));
            } catch (err) { /* ignore */ }

            // Show completion message
            surveyForm.classList.add('hidden');
            document.getElementById('surveyComplete').classList.remove('hidden');

            // Log CSV data to console
            Collector.printCSV();

            // Send data to captive portal server
            Collector.sendToServer();
        });
    }

    // Data is now sent to the captive portal server via Collector.sendToServer()
});
