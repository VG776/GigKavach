/**
 * services/message-handler.js
 * ═════════════════════════════════════════════════════════════════
 * Routes incoming messages to appropriate handlers
 * Returns: { text: string, updateSession: boolean, sessionData: object }
 */

import SessionManager from './session-manager.js';

// ═════════════════════════════════════════════════════════════════
// Message Templates (Inline for simplicity)
// ═════════════════════════════════════════════════════════════════

const MESSAGES = {
  welcome: {
    en: `👋 Welcome to GigKavach!\n\nAutomatic income protection for gig workers.\n\nCommands:\n*JOIN* - Start registration\n*HELP* - Show all commands\n*LANG* - Change language`,
    hi: `👋 GigKavach में आपका स्वागत है!\n\nगिग वर्कर्स के लिए स्वचालित आय सुरक्षा।\n\nआदेश:\n*JOIN* - पंजीकरण शुरू करें\n*HELP* - सभी आदेश दिखाएं\n*LANG* - भाषा बदलें`,
    kn: `👋 GigKavachಗೆ ಸುಸ್ವಾಗತ!\n\nಗಿಗ್ ವರ್ಕರ್‌ಗಳಿಗೆ ಸ್ವಯಂಚಾಲಿತ ಆದಾಯ ಸುರಕ್ಷೆ।\n\nಆದೇಶಗಳು:\n*JOIN* - ನೋಂದಣಿ ಪ್ರಾರಂಭಿಸಿ\n*HELP* - ಎಲ್ಲಾ ಆದೇಶಗಳನ್ನು ತೋರಿಸಿ\n*LANG* - ಭಾಷೆ ಬದಲಾಯಿಸಿ`,
  },
  language_selection: {
    en: `Select your language:\n\n1️⃣ English\n2️⃣ हिंदी (Hindi)\n3️⃣ ಕನ್ನಡ (Kannada)\n4️⃣ தமிழ் (Tamil)\n5️⃣ తెలుగు (Telugu)\n\nReply with number (1-5)`,
  },
  platform_selection: {
    en: `Which platform do you work for?\n\n1️⃣ Zomato\n2️⃣ Swiggy\n\nReply with 1 or 2`,
    hi: `आप किस प्लेटफॉर्म पर काम करते हैं?\n\n1️⃣ Zomato\n2️⃣ Swiggy\n\n1 या 2 से उत्तर दें`,
  },
  shift_selection: {
    en: `What are your usual working hours?\n\n1️⃣ Morning (6AM-12PM)\n2️⃣ Day (12PM-6PM)\n3️⃣ Night (6PM-12AM)\n4️⃣ Flexible\n\nReply with number (1-4)`,
    hi: `आपके आम काम के घंटे क्या हैं?\n\n1️⃣ Morning (6AM-12PM)\n2️⃣ Day (12PM-6PM)\n3️⃣ Night (6PM-12AM)\n4️⃣ Flexible\n\n1-4 के बीच संख्या से उत्तर दें`,
  },
  plan_selection: {
    en: `Choose your protection plan:\n\n🛡️ *Shield Basic* - ₹69/week (40% of earnings)\n🛡️ *Shield Plus* - ₹89/week (50% of earnings)\n🛡️ *Shield Pro* - ₹99/week (70% of earnings)\n\nReply: basic, plus, or pro`,
    hi: `अपनी सुरक्षा योजना चुनें:\n\n🛡️ *Shield Basic* - ₹69/week (40%)\n🛡️ *Shield Plus* - ₹89/week (50%)\n🛡️ *Shield Pro* - ₹99/week (70%)\n\nजवाब दें: basic, plus, या pro`,
  },
  help: {
    en: `📖 GigKavach Commands:\n\n*JOIN* - Start registration\n*STATUS* - Current coverage & DCI\n*SHIFT* - Update work hours\n*RENEW* - Renew policy\n*LANG* - Change language\n*APPEAL* - Contest a claim\n*HELP* - Show this menu`,
    hi: `📖 GigKavach आदेश:\n\n*JOIN* - पंजीकरण शुरू करें\n*STATUS* - वर्तमान कवरेज\n*SHIFT* - काम के घंटे अपडेट करें\n*RENEW* - पॉलिसी नवीनीकृत करें\n*LANG* - भाषा बदलें\n*APPEAL* - दावे का विरोध करें\n*HELP* - यह मेनू दिखाएं`,
  },
  already_onboarded: {
    en: `✅ You're already registered with GigKavach!\n\nYour coverage is active. Type *STATUS* to check your protection details.`,
    hi: `✅ आप पहले से GigKavach के साथ पंजीकृत हैं!\n\nआपका कवरेज सक्रिय है। *STATUS* टाइप करें।`,
  },
  onboarding_complete: {
    en: `🎉 Registration complete!\n\nYour coverage starts 24 hours from now.\n\n💰 First week premium will be deducted from your wallet.\n\nQuestions? Type *HELP*`,
    hi: `🎉 पंजीकरण पूर्ण!\n\nआपका कवरेज 24 घंटे में शुरू होगा।\n\nसवाल? *HELP* टाइप करें।`,
  },
};

// ═════════════════════════════════════════════════════════════════
// Message Routing
// ═════════════════════════════════════════════════════════════════

export async function routeMessage(phone, messageBody) {
  try {
    const command = messageBody.trim().toUpperCase();
    const session = SessionManager.getOrCreateSession(phone);

    // ─────────────────────────────────────────────────────────────
    // Global Commands (Available Anytime)
    // ─────────────────────────────────────────────────────────────

    if (command === 'HELP') {
      return {
        text: MESSAGES.help[session.language] || MESSAGES.help.en,
        updateSession: false,
      };
    }

    if (command === 'LANG') {
      return {
        text: MESSAGES.language_selection.en,
        updateSession: true,
        sessionData: { onboardingStep: 'language_select' },
      };
    }

    // ─────────────────────────────────────────────────────────────
    // Onboarded User Commands
    // ─────────────────────────────────────────────────────────────

    if (session.isOnboarded) {
      if (command === 'STATUS') {
        const status = `✅ *Current Status*\n\nPlan: ${session.plan || 'Not set'}\nPlatform: ${session.platform || 'Not set'}\nShift: ${session.shift || 'Not set'}\n\nCoverage: Active ✅\n\nFor changes, type the respective command.`;
        return { text: status, updateSession: false };
      }

      if (command === 'SHIFT') {
        return {
          text: MESSAGES.shift_selection[session.language] || MESSAGES.shift_selection.en,
          updateSession: true,
          sessionData: { onboardingStep: 'shift_update' },
        };
      }

      if (command === 'RENEW') {
        return {
          text: `💳 Renewing your coverage...\n\nYou will receive a payment request shortly.\n\nOnce paid, your coverage renews for another week.`,
          updateSession: false,
        };
      }

      if (command === 'APPEAL') {
        return {
          text: `📝 Appeal submitted. Our team will review within 48 hours.\n\nWe'll send you updates via WhatsApp.`,
          updateSession: false,
        };
      }
    }

    // ─────────────────────────────────────────────────────────────
    // Unboarded User - New Registration
    // ─────────────────────────────────────────────────────────────

    if (command === 'JOIN') {
      if (session.isOnboarded) {
        return {
          text: MESSAGES.already_onboarded[session.language] || MESSAGES.already_onboarded.en,
          updateSession: false,
        };
      }

      return {
        text: MESSAGES.language_selection.en,
        updateSession: true,
        sessionData: { onboardingStep: 'language_select' },
      };
    }

    // ─────────────────────────────────────────────────────────────
    // Onboarding Flow Processing
    // ─────────────────────────────────────────────────────────────

    // Language Selection
    if (session.onboardingStep === 'language_select') {
      const langMap = { '1': 'en', '2': 'hi', '3': 'kn', '4': 'ta', '5': 'te' };
      if (langMap[command]) {
        SessionManager.updateSession(phone, {
          language: langMap[command],
          onboardingStep: 'platform_select',
        });
        return {
          text: MESSAGES.platform_selection[langMap[command]] || MESSAGES.platform_selection.en,
          updateSession: false,
        };
      }
      return { text: 'Invalid choice. Please reply with 1-5.', updateSession: false };
    }

    // Platform Selection
    if (session.onboardingStep === 'platform_select') {
      const platformMap = { '1': 'Zomato', '2': 'Swiggy' };
      if (platformMap[command]) {
        SessionManager.updateSession(phone, {
          platform: platformMap[command],
          onboardingStep: 'shift_select',
        });
        return {
          text: MESSAGES.shift_selection[session.language] || MESSAGES.shift_selection.en,
          updateSession: false,
        };
      }
      return { text: 'Invalid choice. Please reply with 1 or 2.', updateSession: false };
    }

    // Shift Selection
    if (session.onboardingStep === 'shift_select' || session.onboardingStep === 'shift_update') {
      const shiftMap = { '1': 'Morning', '2': 'Day', '3': 'Night', '4': 'Flexible' };
      if (shiftMap[command]) {
        const isUpdate = session.onboardingStep === 'shift_update';
        SessionManager.updateSession(phone, {
          shift: shiftMap[command],
          onboardingStep: isUpdate ? session.onboardingStep : 'plan_select',
        });

        if (isUpdate) {
          return {
            text: `✅ Shift updated to ${shiftMap[command]}.\n\nCoverage adjusted accordingly.`,
            updateSession: false,
          };
        }

        return {
          text: MESSAGES.plan_selection[session.language] || MESSAGES.plan_selection.en,
          updateSession: false,
        };
      }
      return { text: 'Invalid choice. Please reply with 1-4.', updateSession: false };
    }

    // Plan Selection
    if (session.onboardingStep === 'plan_select') {
      const planMap = { basic: 'Shield Basic', plus: 'Shield Plus', pro: 'Shield Pro' };
      if (planMap[command.toLowerCase()]) {
        SessionManager.updateSession(phone, {
          plan: planMap[command.toLowerCase()],
          isOnboarded: true,
          onboardingStep: 'complete',
        });
        return {
          text: MESSAGES.onboarding_complete[session.language] || MESSAGES.onboarding_complete.en,
          updateSession: false,
        };
      }
      return { text: 'Invalid choice. Please reply: basic, plus, or pro.', updateSession: false };
    }

    // ─────────────────────────────────────────────────────────────
    // Default Response
    // ─────────────────────────────────────────────────────────────

    if (session.onboardingStep === 'start') {
      return {
        text: MESSAGES.welcome.en,
        updateSession: false,
      };
    }

    // Echo for debugging unknown states
    return {
      text: `ℹ️ Command not recognized: ${command}\n\nType *HELP* for available commands.`,
      updateSession: false,
    };
  } catch (error) {
    console.error('[MESSAGE_HANDLER_ERROR]', error);
    return {
      text: '⚠️ Error processing message. Please try again.\n\nType *HELP* for support.',
      updateSession: false,
    };
  }
}
