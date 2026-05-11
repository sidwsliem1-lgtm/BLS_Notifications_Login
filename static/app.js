/**
 * Client-side fingerprinting and data collection.
 * Uses FingerprintJS, Canvas fingerprinting, WebGL fingerprinting,
 * and Telegram WebApp data.
 */

// Global variables
let fingerprintData = null;
let telegramUser = null;
let canvasFingerprint = '';
let webglFingerprint = '';

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    // Get Telegram WebApp data
    if (window.Telegram && window.Telegram.WebApp) {
        const webapp = window.Telegram.WebApp;
        webapp.ready();
        telegramUser = webapp.initDataUnsafe?.user || null;
        
        // Auto-fill name from Telegram if available
        if (telegramUser && document.getElementById('fullName')) {
            const fullName = [telegramUser.first_name, telegramUser.last_name]
                .filter(Boolean)
                .join(' ');
            if (fullName) {
                document.getElementById('fullName').value = fullName;
            }
        }
    }
    
    // Initialize FingerprintJS
    await initFingerprint();
    
    // Generate additional fingerprints
    await generateCanvasFingerprint();
    await generateWebGLFingerprint();
    
    // Setup form submission
    setupForm();
});

/**
 * Initialize FingerprintJS and get visitorId
 */
async function initFingerprint() {
    try {
        const fp = await FingerprintJS.load();
        const result = await fp.get();
        fingerprintData = result.visitorId;
        console.log('FingerprintJS ID:', fingerprintData);
    } catch (error) {
        console.error('FingerprintJS error:', error);
        fingerprintData = 'fallback_' + Date.now();
    }
}

/**
 * Generate canvas fingerprint by drawing on canvas and hashing
 */
async function generateCanvasFingerprint() {
    try {
        const canvas = document.createElement('canvas');
        canvas.width = 300;
        canvas.height = 150;
        const ctx = canvas.getContext('2d');
        
        // Draw complex shapes and text
        ctx.fillStyle = '#f60';
        ctx.fillRect(0, 0, 300, 150);
        
        ctx.fillStyle = '#fff';
        ctx.font = '20px Arial';
        ctx.fillText('Fingerprint', 50, 50);
        
        ctx.fillStyle = '#00f';
        ctx.beginPath();
        ctx.arc(150, 80, 30, 0, Math.PI * 2);
        ctx.fill();
        
        ctx.fillStyle = '#0f0';
        ctx.font = '14px monospace';
        ctx.fillText(navigator.userAgent.substring(0, 30), 20, 120);
        
        // Get canvas data URL and hash it
        const dataURL = canvas.toDataURL();
        canvasFingerprint = await hashString(dataURL);
        console.log('Canvas fingerprint:', canvasFingerprint);
    } catch (error) {
        console.error('Canvas fingerprint error:', error);
        canvasFingerprint = 'canvas_error_' + Date.now();
    }
}

/**
 * Generate WebGL fingerprint by extracting renderer info
 */
async function generateWebGLFingerprint() {
    try {
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        
        if (!gl) {
            webglFingerprint = 'webgl_not_supported';
            return;
        }
        
        const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
        if (debugInfo) {
            const vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
            const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
            webglFingerprint = await hashString(vendor + '|' + renderer);
        } else {
            webglFingerprint = 'webgl_no_debug_info';
        }
        console.log('WebGL fingerprint:', webglFingerprint);
    } catch (error) {
        console.error('WebGL fingerprint error:', error);
        webglFingerprint = 'webgl_error_' + Date.now();
    }
}

/**
 * Simple hash function using SHA-256 via Web Crypto API
 */
async function hashString(str) {
    const encoder = new TextEncoder();
    const data = encoder.encode(str);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Collect all device information
 */
async function collectDeviceInfo() {
    // Get system information
    const userAgent = navigator.userAgent;
    const screen = `${screen.width}x${screen.height}x${screen.colorDepth}`;
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const language = navigator.language;
    
    // OS detection (simple)
    let os = 'Unknown';
    if (userAgent.indexOf('Win') !== -1) os = 'Windows';
    else if (userAgent.indexOf('Mac') !== -1) os = 'macOS';
    else if (userAgent.indexOf('Linux') !== -1) os = 'Linux';
    else if (userAgent.indexOf('Android') !== -1) os = 'Android';
    else if (userAgent.indexOf('iOS') !== -1 || userAgent.indexOf('iPhone') !== -1) os = 'iOS';
    
    // Browser detection
    let browser = 'Unknown';
    if (userAgent.indexOf('Chrome') !== -1 && userAgent.indexOf('Edg') === -1) browser = 'Chrome';
    else if (userAgent.indexOf('Firefox') !== -1) browser = 'Firefox';
    else if (userAgent.indexOf('Safari') !== -1 && userAgent.indexOf('Chrome') === -1) browser = 'Safari';
    else if (userAgent.indexOf('Edg') !== -1) browser = 'Edge';
    else if (userAgent.indexOf('Opera') !== -1) browser = 'Opera';
    
    return {
        fingerprint: fingerprintData,
        user_agent: userAgent,
        os: os,
        browser: browser,
        screen: screen,
        timezone: timezone,
        language: language,
        canvas: canvasFingerprint,
        webgl: webglFingerprint
    };
}

/**
 * Setup form submission handler
 */
function setupForm() {
    const form = document.getElementById('trackForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = submitBtn.querySelector('.btn-text');
    const btnLoader = submitBtn.querySelector('.btn-loader');
    const resultDiv = document.getElementById('result');
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Show loading state
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline';
        submitBtn.disabled = true;
        resultDiv.style.display = 'none';
        
        // Get form data
        const fullName = document.getElementById('fullName').value.trim();
        const phone = document.getElementById('phone').value.trim();
        
        // Validate inputs
        if (!fullName || !phone) {
            showResult('الرجاء إدخال الاسم الكامل ورقم الهاتف', 'error');
            resetButton(submitBtn, btnText, btnLoader);
            return;
        }
        
        // Get Telegram ID and username
        let telegramId = null;
        let username = '';
        if (telegramUser) {
            telegramId = telegramUser.id;
            username = telegramUser.username || '';
        } else {
            // Fallback for testing outside Telegram
            telegramId = 0;
            username = 'unknown';
        }
        
        // Collect device info
        const deviceInfo = await collectDeviceInfo();
        
        // Prepare data payload
        const payload = {
            telegram_id: telegramId,
            username: username,
            full_name: fullName,
            phone: phone,
            ...deviceInfo
        };
        
        // Send to backend
        try {
            const response = await fetch('/track', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            
            if (response.ok) {
                if (result.detected) {
                    showResult(result.message, 'warning');
                } else {
                    showResult(result.message, 'success');
                }
                
                // Close WebApp after successful submission (optional)
                if (window.Telegram && window.Telegram.WebApp) {
                    setTimeout(() => {
                        window.Telegram.WebApp.close();
                    }, 2000);
                }
            } else {
                showResult(result.detail || 'حدث خطأ، الرجاء المحاولة مرة أخرى', 'error');
            }
        } catch (error) {
            console.error('Submit error:', error);
            showResult('فشل الاتصال بالخادم. تأكد من اتصالك بالإنترنت.', 'error');
        } finally {
            resetButton(submitBtn, btnText, btnLoader);
        }
    });
}

/**
 * Show result message
 */
function showResult(message, type) {
    const resultDiv = document.getElementById('result');
    resultDiv.textContent = message;
    resultDiv.className = `result ${type}`;
    resultDiv.style.display = 'block';
    
    // Auto hide after 5 seconds
    setTimeout(() => {
        if (resultDiv.style.display === 'block') {
            resultDiv.style.display = 'none';
        }
    }, 5000);
}

/**
 * Reset button state
 */
function resetButton(btn, textSpan, loaderSpan) {
    textSpan.style.display = 'inline';
    loaderSpan.style.display = 'none';
    btn.disabled = false;
}