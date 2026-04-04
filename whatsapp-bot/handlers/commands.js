/**
 * handlers/commands.js
 * ─────────────────────────────────────────
 * Handles worker commands:
 * - STATUS: Show current zone DCI & coverage
 * - RENEW: Renew policy for next week
 * - SHIFT: Update working hours
 * - APPEAL: Contest a fraud decision
 */

import SessionManager from '../services/session-manager.js';
import { getLocalizedMessage } from '../services/message-handler.js';
import axios from 'axios';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function handleCommand(phone, command, session) {
  switch (command) {
    case 'STATUS':
      return await handleStatus(phone, session);
    case 'RENEW':
      return await handleRenew(phone, session);
    case 'SHIFT':
      return await handleShift(phone, session);
    case 'APPEAL':
      return await handleAppeal(phone, session);
    default:
      return `⚠️ Unknown command: ${command}`;
  }
}

/**
 * STATUS command: Show current DCI score and coverage
 */
async function handleStatus(phone, session) {
  try {
    const worker = SessionManager.getUser(phone);
    if (!worker) {
      return getLocalizedMessage('already_onboarded', session.language);
    }

    // Get current DCI score from backend
    const pinCode = worker.pin_codes.split(',')[0]; // Get first pin code
    const dciResponse = await axios.get(`${BACKEND_URL}/dci/${pinCode}`);

    const dciData = dciResponse.data.current || {};
    const dci = dciData.total_score || 0;
    const severity =
      dci >= 85
        ? 'Critical'
        : dci >= 65
          ? 'Moderate'
          : dci >= 50
            ? 'Low'
            : 'None';

    return getLocalizedMessage('status_response', session.language, {
      pin_code: pinCode,
      dci: Math.round(dci),
      severity,
      plan: worker.plan || 'Basic',
      shift: worker.shift || 'Day',
    });
  } catch (error) {
    console.error(`Failed to fetch DCI for ${phone}:`, error.message);
    return `⚠️ Could not fetch zone status. Try again later.`;
  }
}

/**
 * RENEW command: Renew policy for next week
 */
async function handleRenew(phone, session) {
  try {
    const worker = SessionManager.getUser(phone);
    if (!worker) {
      return getLocalizedMessage('already_onboarded', session.language);
    }

    // Call backend to renew policy
    const response = await axios.patch(`${BACKEND_URL}/api/v1/policy/${worker.policy_id}`, {
      action: 'renew',
    });

    const renewMsg = {
      'en': `✅ Your policy has been renewed!\n\nPlan: ${worker.plan}\nNext renewal: Next Sunday\nType HELP for more commands.`,
      'hi': `✅ आपकी पॉलिसी नवीनीकृत हो गई है!\n\nप्लान: ${worker.plan}\nअगली नवीनीकरण: अगले रविवार`,
      'kn': `✅ ನಿಮ್ಮ ಪಾಲಿಸಿ ನವೀಕರಣ ಹೊಂದಿದೆ!\n\nಯೋಜನೆ: ${worker.plan}`,
      'ta': `✅ உங்கள் கொள்கை புதுப்பிக்கப்பட்டுவிட்டது!\n\nதிட்டம்: ${worker.plan}`,
      'te': `✅ మీ పాలసీ నవీకరించబడింది!\n\nప్లాన్: ${worker.plan}`,
    };

    return renewMsg[session.language] || renewMsg['en'];
  } catch (error) {
    console.error(`Renew failed for ${phone}:`, error.message);
    return `⚠️ Could not renew your policy. Contact support.`;
  }
}

/**
 * SHIFT command: Update working hours
 */
async function handleShift(phone, session) {
  const shiftMsg = {
    'en': `Update your working hours:\n1️⃣ Morning (6AM–2PM)\n2️⃣ Day (9AM–9PM)\n3️⃣ Night (6PM–2AM)\n4️⃣ Flexible`,
    'hi': `अपने काम के घंटे अपडेट करें:\n1️⃣ सुबह (6AM–2PM)\n2️⃣ दिन (9AM–9PM)\n3️⃣ रात (6PM–2AM)\n4️⃣ कभी भी`,
    'kn': `ನಿಮ್ಮ ಕೆಲಸದ ಸಮಯ ಅಪ್‌ಡೇಟ್ ಮಾಡಿ:\n1️⃣ ಬೆಳಿಗ್ಗೆ\n2️⃣ ಹಗಲು\n3️⃣ ರಾತ್ರಿ\n4️⃣ ಯಾವುದಾದರೂ ಸಮಯ`,
    'ta': `உங்கள் வேலை நேரத்தை அপ்டেட் செய்யுங்கள்:\n1️⃣ காலை\n2️⃣ பகல்\n3️⃣ இரவு\n4️⃣ நெகிழ்வான`,
    'te': `మీ పని సమయాన్ని అప్‌డేట్ చేయండి:\n1️⃣ ఉదయం\n2️⃣ పగలు\n3️⃣ రాత్రి\n4️⃣ ఎప్పుడైనా`,
  };

  // Store that user is in shift update mode
  SessionManager.updateSession(phone, { commandState: 'awaiting_shift' });

  return shiftMsg[session.language] || shiftMsg['en'];
}

/**
 * APPEAL command: Contest a fraud decision
 */
async function handleAppeal(phone, session) {
  try {
    const worker = SessionManager.getUser(phone);
    if (!worker) {
      return getLocalizedMessage('already_onboarded', session.language);
    }

    const appealMsg = {
      'en': `📋 Appeal Process:\n\nYou have 48 hours to contest a fraud decision.\n\n1. Describe what happened during the disruption\n2. Share any additional context (screenshots, etc)\n3. Our team will review within 24 hours\n\nReply with your appeal details:`,
      'hi': `📋 अपील प्रक्रिया:\n\nआपके पास धोखाधड़ी के फैसले को चुनौती देने के लिए 48 घंटे हैं।\n\nअपनी अपील विवरण के साथ जवाब दें:`,
      'kn': `📋 ಅಪೀಲ್ ಪ್ರಕ್ರಿಯೆ:\n\nನಿಮ್ಮ ಅಪೀಲ್ ವಿವರಾಂಶಗಳೊಂದಿಗೆ ಜವಾಬು ನೀಡಿ:`,
      'ta': `📋 மேல்முறையீட்டு செயல்முறை:\n\nআপনার আবেদন বিবরণ সহ উত্তর দিন:`,
      'te': `📋 అప్పీల్ ప్రక్రియ:\n\nమీ అప్పీల్ వివరాలతో సమాధానం ఇవ్వండి:`,
    };

    // Store that user is filing an appeal
    SessionManager.updateSession(phone, { commandState: 'filing_appeal' });

    return appealMsg[session.language] || appealMsg['en'];
  } catch (error) {
    console.error(`Appeal failed for ${phone}:`, error.message);
    return `⚠️ Could not process appeal. Contact support.`;
  }
}
