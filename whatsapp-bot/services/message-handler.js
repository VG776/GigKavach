/**
 * services/message-handler.js
 * ═════════════════════════════════════════════════════════════════
 * Routes incoming messages to appropriate handlers
 * Returns: { text: string, updateSession: boolean, sessionData: object }
 */

import SessionManager from './session-manager.js';

// Backend API URL
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

// ═════════════════════════════════════════════════════════════════
// Utility: Generate Share Link Token
// ═════════════════════════════════════════════════════════════════

async function generateShareLink(workerId, page) {
  /**
   * Generate a shareable link for a worker to access their PWA data
   * @param {string} workerId - Worker ID from database
   * @param {string} page - Page type: 'profile', 'status', 'history'
   * @returns {Promise<string>} Full shareable URL or error message
   */
  try {
    const response = await fetch(`${BACKEND_URL}/api/v1/share-tokens/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        worker_id: workerId,
        expires_in_days: 7,
        max_uses: 50,
        reason: `WhatsApp share link for ${page} page`,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      console.error(`[SHARE_LINK_ERROR] Failed to generate token: ${error.message}`);
      return null;
    }

    const data = await response.json();
    // Construct full URL for frontend
    const frontendUrl = process.env.FRONTEND_URL || 'http://localhost:3000';
    const fullShareUrl = `${frontendUrl}/link/${data.share_token}/${page}`;
    
    console.log(`[SHARE_LINK_GENERATED] Worker: ${workerId}, Page: ${page}, URL: ${fullShareUrl}`);
    return fullShareUrl;
  } catch (error) {
    console.error('[SHARE_LINK_GENERATION_ERROR]', error);
    return null;
  }
}

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
    en: `📖 GigKavach Commands:\n\n*JOIN* - Start registration\n*PROFILE* - View your profile 📱\n*STATUS* - Current coverage & DCI 📊\n*HISTORY* - Transaction history 💰\n*SHIFT* - Update work hours\n*RENEW* - Renew policy\n*LANG* - Change language\n*APPEAL* - Contest a claim\n*HELP* - Show this menu`,
    hi: `📖 GigKavach आदेश:\n\n*JOIN* - पंजीकरण शुरू करें\n*PROFILE* - अपनी प्रोफ़ाइल देखें 📱\n*STATUS* - वर्तमान कवरेज 📊\n*HISTORY* - लेनदेन इतिहास 💰\n*SHIFT* - काम के घंटे अपडेट करें\n*RENEW* - पॉलिसी नवीनीकृत करें\n*LANG* - भाषा बदलें\n*APPEAL* - दावे का विरोध करें\n*HELP* - यह मेनू दिखाएं`,
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

    console.log(`[MESSAGE_ROUTE] Phone: ${phone}, Command: ${command}, Onboarded: ${session.isOnboarded}, Step: ${session.onboardingStep}`);

    // ─────────────────────────────────────────────────────────────
    // Global Commands (Available Anytime)
    // ─────────────────────────────────────────────────────────────

    // Handle JOIN as entry point for new users
    if (command === 'JOIN' || command === 'START') {
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
        // Check if looking for shareable link or status info
        // If user has saved worker_id, generate link; otherwise show text status
        if (session.worker_id) {
          const shareLink = await generateShareLink(session.worker_id, 'status');
          if (shareLink) {
            return {
              text: `📊 *Your Live Zone Status*\n\nClick here to view real-time DCI readings and zone disruption index:\n\n${shareLink}\n\n⏰ This link expires in 7 days.\n💡 Shows weather, air quality, heat, and social impact on your zone.`,
              updateSession: false,
            };
          }
        }
        
        // Fallback: Show text status
        const status = `✅ *Current Status*\n\nPlan: ${session.plan || 'Not set'}\nPlatform: ${session.platform || 'Not set'}\nShift: ${session.shift || 'Not set'}\n\nCoverage: Active ✅\n\nFor changes, type the respective command.`;
        return { text: status, updateSession: false };
      }

      if (command === 'PROFILE') {
        if (!session.worker_id) {
          return {
            text: `⚠️ Unable to generate link. Please contact support.\n\nType *HELP* for more options.`,
            updateSession: false,
          };
        }

        const profileLink = await generateShareLink(session.worker_id, 'profile');
        if (profileLink) {
          return {
            text: `📱 *Your GigKavach Profile*\n\nView your GigScore, zone info, and premium details:\n\n${profileLink}\n\n✨ Share this link with anyone you'd like to show your profile to.\n⏰ Link expires in 7 days.`,
            updateSession: false,
          };
        }

        return {
          text: `⚠️ Error generating profile link. Please try again later.`,
          updateSession: false,
        };
      }

      if (command === 'HISTORY') {
        if (!session.worker_id) {
          return {
            text: `⚠️ Unable to generate link. Please contact support.`,
            updateSession: false,
          };
        }

        const historyLink = await generateShareLink(session.worker_id, 'history');
        if (historyLink) {
          return {
            text: `💰 *Your Transaction History*\n\nView all your payouts and earnings:\n\n${historyLink}\n\n📊 Track your payments, discounts, and bonus hours.\n⏰ Link expires in 7 days.`,
            updateSession: false,
          };
        }

        return {
          text: `⚠️ Error generating history link. Please try again later.`,
          updateSession: false,
        };
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
        const selectedPlan = planMap[command.toLowerCase()];
        
        // Register worker with backend API
        try {
          const registrationResponse = await fetch(`${BACKEND_URL}/api/v1/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              phone_number: phone,
              platform: session.platform,
              zone: session.zone || 'India',  // Default zone
              shift: session.shift,
              plan_tier: command.toLowerCase(),  // 'basic', 'plus', 'pro'
              language: session.language || 'en',
              source: 'whatsapp_bot',
            }),
          });

          if (registrationResponse.ok) {
            const registrationData = await registrationResponse.json();
            const workerId = registrationData.worker?.id || registrationData.worker_id;
            
            if (workerId) {
              // Store worker_id in session for future share link generation
              SessionManager.updateSession(phone, {
                plan: selectedPlan,
                worker_id: workerId,  // ← KEY: Store the worker_id!
                isOnboarded: true,
                onboardingStep: 'complete',
              });
              
              console.log(`[ONBOARDING_COMPLETE] Worker registered: ${workerId}, Phone: ${phone}`);
              
              return {
                text: MESSAGES.onboarding_complete[session.language] || MESSAGES.onboarding_complete.en,
                updateSession: false,
              };
            }
          }
          
          // Fallback if registration fails
          console.error('[REGISTRATION_ERROR] Backend registration failed');
          SessionManager.updateSession(phone, {
            plan: selectedPlan,
            isOnboarded: true,
            onboardingStep: 'complete',
          });
          
          return {
            text: `✅ ${MESSAGES.onboarding_complete[session.language] || MESSAGES.onboarding_complete.en}\n\n⚠️ Note: Share links may not work yet. Please try again in a moment.`,
            updateSession: false,
          };
        } catch (error) {
          console.error('[REGISTRATION_EXCEPTION]', error);
          
          // Still mark as onboarded, but without worker_id
          SessionManager.updateSession(phone, {
            plan: selectedPlan,
            isOnboarded: true,
            onboardingStep: 'complete',
          });
          
          return {
            text: MESSAGES.onboarding_complete[session.language] || MESSAGES.onboarding_complete.en,
            updateSession: false,
          };
        }
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
