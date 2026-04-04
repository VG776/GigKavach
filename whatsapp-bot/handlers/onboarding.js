/**
 * handlers/onboarding.js
 * ─────────────────────────────────────────
 * Handles 7-step onboarding flow:
 * 1. Language selection
 * 2. Platform (Zomato/Swiggy)
 * 3. Shift (Morning/Day/Night/Flexible)
 * 4. UPI ID
 * 5. Pin codes (delivery zones)
 * 6. Plan selection (Basic/Plus/Pro)
 * 7. Completion + backend verification
 */

import SessionManager from '../services/session-manager.js';
import { getLocalizedMessage } from '../services/message-handler.js';
import axios from 'axios';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

/**
 * Handle onboarding step based on current state
 */
export async function handleOnboarding(phone, userInput, session) {
  const step = session.onboardingStep;

  switch (step) {
    case 'language':
      return handleLanguageSelection(phone, userInput, session);
    case 'platform':
      return handlePlatformSelection(phone, userInput, session);
    case 'shift':
      return handleShiftSelection(phone, userInput, session);
    case 'upi':
      return handleUPIEntry(phone, userInput, session);
    case 'pincode':
      return handlePincodeEntry(phone, userInput, session);
    case 'plan':
      return handlePlanSelection(phone, userInput, session);
    case 'complete':
      return getLocalizedMessage('onboarding_complete', session.language);
    default:
      return `⚠️ Invalid onboarding state. Type *JOIN* to start over.`;
  }
}

/**
 * Step 1: Language Selection
 */
function handleLanguageSelection(phone, input, session) {
  const langMap = {
    '1': 'en',
    '2': 'kn',
    '3': 'hi',
    '4': 'ta',
    '5': 'te',
  };

  const language = langMap[input];
  if (!language) {
    return getLocalizedMessage('welcome', session.language);
  }

  SessionManager.setLanguage(phone, language);
  SessionManager.nextStep(phone);

  return getLocalizedMessage('ask_platform', language);
}

/**
 * Step 2: Platform Selection (Zomato/Swiggy)
 */
function handlePlatformSelection(phone, input, session) {
  const platformMap = {
    '1': 'Zomato',
    '2': 'Swiggy',
  };

  const platform = platformMap[input];
  if (!platform) {
    return getLocalizedMessage('ask_platform', session.language);
  }

  SessionManager.updateTempData(phone, { platform });
  SessionManager.nextStep(phone);

  return getLocalizedMessage('ask_shift', session.language);
}

/**
 * Step 3: Shift Selection
 */
function handleShiftSelection(phone, input, session) {
  const shiftMap = {
    '1': 'Morning (6AM–2PM)',
    '2': 'Day (9AM–9PM)',
    '3': 'Night (6PM–2AM)',
    '4': 'Flexible',
  };

  const shift = shiftMap[input];
  if (!shift) {
    return getLocalizedMessage('ask_shift', session.language);
  }

  SessionManager.updateTempData(phone, { shift });
  SessionManager.nextStep(phone);

  return getLocalizedMessage('ask_upi', session.language);
}

/**
 * Step 4: UPI ID Entry
 */
function handleUPIEntry(phone, input, session) {
  // Validate UPI format (basic)
  const upiRegex = /^[a-zA-Z0-9._-]+@[a-zA-Z]{3,}$/;
  if (!upiRegex.test(input)) {
    const errorMsg = {
      'en': '⚠️ Invalid UPI format. Please use format like: yourname@upi or yourname@bankname',
      'hi': '⚠️ गलत UPI फॉर्मेट। कृपया yourname@upi जैसा फॉर्मेट दें।',
      'kn': '⚠️ गलत UPI फॉर्मेट। yourname@upi ರೀತಿ ಬಳಸಿ।',
      'ta': '⚠️ தவறான UPI வடிவம். yourname@upi போன்ற வடிவத்தைப் பயன்படுத்தவும்.',
      'te': '⚠️ తప్పు UPI ఫార్మ్యాట్. yourname@upi వంటి ఫార్మ్యాట్‌ను ఉపయోగించండి.',
    };
    return errorMsg[session.language] || errorMsg['en'];
  }

  SessionManager.updateTempData(phone, { upi: input });
  SessionManager.nextStep(phone);

  return getLocalizedMessage('ask_pincode', session.language);
}

/**
 * Step 5: Pincode Entry (up to 5 pin codes)
 */
function handlePincodeEntry(phone, input, session) {
  const pincodes = input
    .split(',')
    .map((p) => p.trim())
    .filter((p) => p.length === 6 && /^\d+$/.test(p));

  if (pincodes.length === 0 || pincodes.length > 5) {
    const errorMsg = {
      'en': '⚠️ Please provide 1-5 valid 6-digit pin codes, comma-separated.\nExample: 560047, 560034, 560001',
      'hi': '⚠️ कृपया 1-5 वैध 6-अंकीय पिन कोड दें, अल्पविराम से अलग।\nउदाहरण: 560047, 560034, 560001',
      'kn': '⚠️ कृपया 1-5 ಸಿದ್ಧ 6-ಅಂಕೆಯ ಪಿನ್ ಕೋಡ್ ಕಳುಹಿಸಿ, ಅರ್ಧವಿರಾಮ ಬಿಂದುವಿಂದ ಬೇರ್ಪಡಿಸಲಾಗಿದೆ।',
      'ta': '⚠️ தயவுசெய்து 1-5 செல்லுபடியான 6-இலக்க பின் குறியீடுகளை கொடுங்கள், கமா பிரிக்கப்பட்ட।',
      'te': '⚠️ దయచేసి 1-5 చెల్లుబాటు చేసిన 6-అంకెల పిన్ కోడ్‌లను కమా ద్వారా వేరు చేయించిన.',
    };
    return errorMsg[session.language] || errorMsg['en'];
  }

  SessionManager.updateTempData(phone, { pincodes });
  SessionManager.nextStep(phone);

  return getLocalizedMessage('ask_plan', session.language);
}

/**
 * Step 6: Plan Selection (Shield Basic/Plus/Pro)
 */
async function handlePlanSelection(phone, input, session) {
  const planMap = {
    '1': 'Shield Basic',
    '2': 'Shield Plus',
    '3': 'Shield Pro',
  };

  const plan = planMap[input];
  if (!plan) {
    return getLocalizedMessage('ask_plan', session.language);
  }

  SessionManager.updateTempData(phone, { plan });

  // ─────────────────────────────────────────────────────────────
  // Step 7: Send data to backend for worker registration
  // ─────────────────────────────────────────────────────────────

  const tempData = session.tempData;
  const workerData = {
    phone,
    platform: tempData.platform,
    shift: tempData.shift,
    upi: tempData.upi,
    pin_codes: tempData.pincodes.join(','),
    plan: plan.replace('Shield ', '').toLowerCase(), // 'basic', 'plus', 'pro'
    language: session.language,
  };

  try {
    const response = await axios.post(`${BACKEND_URL}/api/v1/register`, workerData);

    const backendWorker = response.data;

    // Mark session as complete and store worker data
    SessionManager.completeOnboarding(phone, backendWorker);
    SessionManager.registerWorker(phone, backendWorker);

    // Return completion message with plan name
    return getLocalizedMessage('onboarding_complete', session.language, { plan });
  } catch (error) {
    console.error(`❌ Backend registration failed for ${phone}:`, error.message);

    const errorMsg = {
      'en': `⚠️ Registration failed. Please try again or contact support.\nError: ${error.response?.data?.detail || error.message}`,
      'hi': `⚠️ रजिस्ट्रेशन विफल। कृपया फिर से प्रयास करें।`,
      'kn': `⚠️ ನೋಂದಾಯಿತರಾಗುವಿಕೆ ವಿಫಲವಾಯಿತು। ಮತ್ತೆ ಪ್ರಯತ್ನ ಮಾಡಿ।`,
      'ta': `⚠️ பதிவு தோல்வி. மீண்டும் முயற்சிக்கவும்.`,
      'te': `⚠️ రిజిస్ట్రేషన్ విఫలమైంది. మళ్లీ ప్రయత్నించండి.`,
    };

    return errorMsg[session.language] || errorMsg['en'];
  }
}
