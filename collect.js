var Collector = (function () {

    // ============================================================
    // CONFIGURATION — Change this to the IP of the captive portal
    // server that will receive the survey data.
    // ============================================================
    var SERVER_URL = 'http://127.0.0.1:8080/collect';

    function getOS() {
        var ua = navigator.userAgent;
        if (/Windows NT 10/.test(ua)) return 'Windows 10';
        if (/Windows NT 6.3/.test(ua)) return 'Windows 8.1';
        if (/Windows NT 6.2/.test(ua)) return 'Windows 8';
        if (/Windows NT 6.1/.test(ua)) return 'Windows 7';
        if (/Mac OS X/.test(ua)) return 'macOS';
        if (/Android/.test(ua)) return 'Android';
        if (/iPhone|iPad|iPod/.test(ua)) return 'iOS';
        if (/Linux/.test(ua)) return 'Linux';
        return 'Unknown';
    }

    function getManufacturer() {
        var ua = navigator.userAgent;
        if (/Windows/.test(ua)) return 'Microsoft';
        if (/Mac OS X|Macintosh/.test(ua)) return 'Apple';
        if (/Android/.test(ua)) {
            var match = ua.match(/Android; ([^;)]+)/);
            if (match) return match[1].trim();
            return 'Google';
        }
        if (/iPhone|iPad|iPod/.test(ua)) return 'Apple';
        if (/Linux/.test(ua)) return 'Linux';
        return 'Unknown';
    }

    function getAge(age) {
        var n = parseInt(age, 10);
        if (isNaN(n)) return null;
        return n;
    }

    function getOSLanguage() {
        return navigator.language || navigator.userLanguage || null;
    }

    function getMAC() {
        // MAC address cannot be obtained from browser JavaScript
        return null;
    }

    function getEmail() {
        var surveyData = {};
        try {
            var stored = localStorage.getItem('hotspot-survey');
            if (stored) {
                surveyData = JSON.parse(stored);
            }
        } catch (e) { /* ignore */ }
        return surveyData.email || null;
    }

    function collectAll() {
        var surveyData = {};
        try {
            var stored = localStorage.getItem('hotspot-survey');
            if (stored) {
                surveyData = JSON.parse(stored);
            }
        } catch (e) { /* ignore */ }

        var age = surveyData.age || null;
        var name = surveyData.name || null;
        var country = surveyData.country || null;

        return {
            timestamp: new Date().toISOString(),
            mac: getMAC(),
            manufacturer: getManufacturer(),
            name: name,
            os: getOS(),
            osLanguage: getOSLanguage(),
            age: age ? getAge(age) : null,
            email: getEmail(),
            country: country
        };
    }

    function toCSV(data) {
        // InfluxDB-compatible CSV format
        // Tags: country, name, manufacturer, os, osLanguage
        // Fields: age (long), mac (string), email (string)

        var lines = [];

        // Annotation rows for InfluxDB
        lines.push('#datatype,dateTime:RFC3339,tag,tag,tag,tag,tag,long,string,string');
        lines.push('#group,false,true,true,true,true,true,false,false,false');
        lines.push('#default,_result,,,,,,,,,');
        lines.push(',result,table,_time,country,name,manufacturer,os,osLanguage,age,mac,email');

        // Data row
        var values = [
            '',                    // result
            '0',                   // table
            data.timestamp,        // _time
            data.country || '',    // country (tag)
            data.name || '',       // name (tag)
            data.manufacturer || '', // manufacturer (tag)
            data.os || '',         // os (tag)
            data.osLanguage || '', // osLanguage (tag)
            data.age !== null ? data.age : '',       // age (field)
            data.mac || '',        // mac (field)
            data.email || ''       // email (field)
        ];

        function escapeCSV(val) {
            if (val === null || val === undefined) return '';
            var s = String(val);
            if (s.indexOf(',') !== -1 || s.indexOf('"') !== -1 || s.indexOf('\n') !== -1) {
                return '"' + s.replace(/"/g, '""') + '"';
            }
            return s;
        }

        lines.push(values.map(escapeCSV).join(','));
        return lines.join('\n') + '\n';
    }

    function sendToServer() {
        var data = collectAll();
        var csv = toCSV(data);

        fetch(SERVER_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'text/csv'
            },
            body: csv
        })
        .then(function(response) {
            if (!response.ok) {
                throw new Error('Server returned status ' + response.status);
            }
            console.log('Data sent to server successfully');
        })
        .catch(function(error) {
            console.error('Failed to send data to server:', error);
        });
    }

    function printCSV() {
        var data = collectAll();
        var csv = toCSV(data);
        console.log('=== HOTSPOT DATA CSV (InfluxDB format) ===');
        console.log(csv);
        console.log('============================================');
        return csv;
    }

    return {
        collectAll: collectAll,
        toCSV: toCSV,
        sendToServer: sendToServer,
        printCSV: printCSV
    };
})();
