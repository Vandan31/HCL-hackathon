/**
 * COMPONENT : ui (config)
 * PURPOSE   : Every value the UI may need to change live during the demo, and every word the page shows, in one file.
 * INPUTS    : none
 * OUTPUTS   : CONFIG object, imported by src/ui/*.js
 * DEPENDS ON: nothing
 * PANEL NOTE: All UI knobs and all UI text live here, so a change or a translation fix in front of judges is a
 *             one-line edit plus a browser refresh.
 */

export const CONFIG = {
  // --- Backend connection -------------------------------------------------
  API_BASE: "http://127.0.0.1:8000",  // DEMO-KNOB: Harsh's API (src/api/main.py, uvicorn). "" = same server as the UI
  // DEMO-KNOB: where eligibility questions go. "" = the UI dev server (src/ui/dev_server.py), which runs Vaidehi's
  // real rules engine; Harsh's /api/eligibility is still a MOCK. Set to API_BASE once he wires it to next_question.
  ELIGIBILITY_BASE: "",
  USE_MOCK: false,            // DEMO-KNOB: false = real answers from Harsh's API; true = the in-browser mock (offline UI work)
                              // (/api/eligibility always goes to API_BASE: src/ui/dev_server.py serves it until comp/api does)
  MOCK_DELAY_MS: 700,         // DEMO-KNOB: fake network delay so loading states are visible when using the mock
  MOCK_FORCE_ERROR: null,     // DEMO-KNOB: null | "llm_unavailable" | "network" to click-test the error screens
  REQUEST_TIMEOUT_MS: 12000,  // DEMO-KNOB: PLAN §4.5 targets p95 < 5 s; 12 s leaves slack before we show an error

  // --- Language -------------------------------------------------------------
  UI_LANGUAGES: ["en", "hi", "gu"],  // DEMO-KNOB: choices in the language dropdowns (opening page + header), in this order
  REMEMBER_LANGUAGE: false,   // DEMO-KNOB: true skips the picker on return visits (remembers the last choice on this device)

  // --- Landing page decoration (Three.js, loaded only on the language page) ---------------------------
  ENABLE_3D_LANDING: true,    // DEMO-KNOB: false = plain landing page (also used automatically if WebGL fails)
  LANDING_GLYPH_COUNT: 70,    // DEMO-KNOB: how many syllables float behind the card (fewer = lighter on old phones)
  // DEMO-KNOB: the syllables that float, a mix of the three languages (drawn by the browser, so conjuncts like
  // क्ष and જ્ઞ render correctly).
  LANDING_GLYPHS: [
    "A", "B", "K", "M", "P", "R", "S", "Ya", "Ka", "Ma",
    "अ", "आ", "क", "ख", "ग", "म", "न", "प", "र", "स", "ह", "क्ष", "श्र", "यो", "जा",
    "અ", "આ", "ક", "ખ", "ગ", "મ", "ન", "પ", "ર", "સ", "હ", "જ્ઞ", "યો", "જ",
  ],

  // --- Voice (bonus; browser Web Speech API, free, no keys) ----------------
  ENABLE_VOICE_INPUT: true,   // DEMO-KNOB: false hides the mic if it misbehaves on stage
  MIC_START_TIMEOUT_MS: 8000, // DEMO-KNOB: if the mic hasn't started capturing by then, stop and explain why
  VOICE_AUTO_SEND: false,     // DEMO-KNOB: true sends a spoken question as soon as it is recognised (no button press)
  ENABLE_VOICE_OUTPUT: true,  // DEMO-KNOB: false hides the "Listen" buttons
  AUTO_SPEAK_ANSWERS: false,  // DEMO-KNOB: true reads every answer aloud as soon as it arrives
  AUTO_SPEAK_SPOKEN_QUESTIONS: true, // DEMO-KNOB: a question asked with the mic gets its answer read aloud (typed ones: Listen)
  USE_INDIC_TTS: true,        // DEMO-KNOB: read answers with the team's IndicTTS service (src/tts); false = browser voice only
  TTS_BASE: "http://127.0.0.1:5600",   // DEMO-KNOB: where src/tts/server.py runs
  TTS_TIMEOUT_MS: 15000,      // DEMO-KNOB: max wait for ONE sentence (~2-6 s measured on a laptop CPU); then the browser voice
  TTS_MIN_CHUNK_CHARS: 40,    // DEMO-KNOB: sentences shorter than this are joined to the previous one (fewer pauses)
  // (the mic listens in the page language; the dropdown beside it switches the whole page)

  // --- Eligibility checklist (bonus) ----------------------------------------
  ENABLE_ELIGIBILITY: true,   // DEMO-KNOB: false hides the "Check if I'm eligible" buttons
  // (follow-up questions are asked in the language picked on the opening page)

  // --- Accessibility -------------------------------------------------------
  LARGE_TEXT_DEFAULT: false,  // DEMO-KNOB: start in large-text mode (for low-vision users or a far-away projector)

  // --- Content -------------------------------------------------------------
  DATA_AS_OF: "2026-10-27",   // DEMO-KNOB: date the scheme pages were collected (YYYY-MM-DD); shown under every answer
                              // in the page language, e.g. "27 ઑક્ટો, 2026" (PLAN §4.6)

  // DEMO-KNOB: clickable example questions for each page language; they follow the demo script in PLAN §9.1
  SAMPLE_QUESTIONS: {
    en: [
      "What help can I get as a farmer?",
      "Which documents do I need for PM Awas Yojana?",
      "How much money does PM-Kisan give?",
      "How do I get a passport?",
    ],
    hi: [
      "किसान के रूप में मुझे क्या सहायता मिल सकती है?",
      "पीएम आवास योजना के लिए कौन से दस्तावेज़ चाहिए?",
      "PM awas yojana ke liye kaunse documents chahiye?",
      "पासपोर्ट कैसे बनवाएँ?",
    ],
    // DEMO-KNOB: Gujarati demo: 3 questions the documents answer + 1 out of scope (passport), which the
    // system refuses. All 4 real answers are recorded in the API's offline cache (served with OFFLINE_MODE=true).
    gu: [
      "મારી પાસે ઉંમર સાબિત કરવાનો કોઈ દસ્તાવેજ નથી. શું હું તેમ છતાં વિધવા પેન્શન માટે અરજી કરી શકું?",
      "હું ગુજરાતની અનુસૂચિત જાતિ (SC)ની મહિલા છું. મારા માટે કઈ લોન વધુ સારી છે, મહિલા સમૃદ્ધિ યોજના કે નાના ધંધા માટેની લોન?",
      "મારી એક જોડિયા બહેન છે અને કોઈ ભાઈ નથી. શું અમે સિંગલ ગર્લ ચાઇલ્ડ શિષ્યવૃત્તિ માટે અરજી કરી શકીએ?",
      "પાસપોર્ટ કેવી રીતે બનાવવો?",
    ],
  },

  // WHY: speech recognition must be told the language before listening; it can't auto-detect.
  SPEECH_LANG: { en: "en-IN", hi: "hi-IN", gu: "gu-IN", hinglish: "en-IN", mr: "mr-IN", ta: "ta-IN" },

  // Language names, each written in its own script so anyone can find theirs. Used on the picker,
  // the mic menu and the badge that shows which language an answer is in.
  // mr / ta: the API can answer in Marathi and Tamil too (Harsh, 2026-10-27), so the answer badge must name them.
  LANG_LABELS: { en: "English", hi: "हिन्दी", gu: "ગુજરાતી", hinglish: "Hinglish", mr: "मराठी", ta: "தமிழ்" },

  // WHY: every word on the page comes from here, in the language picked on the opening page, so a
  // Gujarati user never has to read English to use the app. Answers themselves come back in the
  // language the question was asked in (the brief requires that), so a Hinglish question gets a Hinglish answer.
  STRINGS: {
    en: {
      appName: "Yojana Saathi",
      continue: "Continue",
      tagline: "Ask about government schemes, certificates and subsidies.",
      changeLanguage: "Change language",
      largeText: "Large text",
      examples: "Example questions",
      tryAsking: "Try asking:",
      conversation: "Conversation",
      micLanguage: "Language for the page and your voice",
      speakQuestion: "Speak your question",
      yourQuestion: "Your question",
      placeholder: "Type your question…",
      listening: "Listening… speak now",
      micAsk: "Please allow the microphone (look for the prompt near the address bar).",
      micStarting: "Starting the microphone…",
      ask: "Ask",
      thinking: "Searching the scheme documents",
      detectedLanguage: "Language of this answer",
      sources: "Sources",
      openPage: "Open official page",
      machineTranslation: "Machine translation",
      translationMissing: "Translation not available",
      newTab: "opens in a new tab",
      listen: "Listen",
      preparingAudio: "Preparing audio…",
      stopAudio: "Stop",
      refusedTitle: "Not in my documents",
      aiUnavailable: "AI summary is unavailable right now. These are the most relevant official passages:",
      disclaimer: "Information from official scheme pages as of {date}. The final decision rests with the department.",
      checkEligibility: "Check if I'm eligible for {scheme}",
      eligibilityTitle: "Eligibility check",
      ok: "OK",
      status: { met: "Meets", not_met: "Doesn't meet", unknown: "Verify at office" },
      verdict: {
        likely_eligible: "You look eligible. The department makes the final decision.",
        not_eligible: "You don't seem to meet at least one rule of this scheme.",
        need_more_info: "Some points need to be checked at the office.",
      },
      noChecklist: "An eligibility checklist isn't available for this scheme yet.",
      pill: { mock: "Mock data", live: "Live", offline: "Offline mode", aiDown: "AI summary down", unreachable: "Server unreachable" },
      errors: {
        timeout: "The server took too long to answer. Please try again.",
        network: "Can't reach the server. Check the connection and try again.",
        server: "Something went wrong on the server. Please try again.",
        empty_query: "Please type or say a question.",
        micDenied: "Microphone is blocked. Click the lock icon in the address bar, allow the microphone and try again, or type your question.",
        micFailed: "Couldn't hear that. Please try again or type your question.",
        micNoDevice: "No microphone found. Plug one in or type your question.",
        micNetwork: "Voice input in this browser needs the internet. Please type your question.",
        micNoSpeech: "I didn't hear anything. Tap the mic and speak again.",
        micUnsupported: "This browser can't take voice input. Please use Chrome or Edge, or type your question.",
        micTimeout: "The microphone didn't start. Check that no other app is using it, then try again.",
        micLanguage: "Voice input isn't available for this language here. Please type your question.",
        noVoice: "No {lang} voice is installed in this browser.",
        noTts: "This browser can't read text aloud.",
      },
    },
    hi: {
      appName: "योजना साथी",
      continue: "आगे बढ़ें",
      tagline: "सरकारी योजनाओं, प्रमाण पत्रों और सब्सिडी के बारे में पूछें।",
      changeLanguage: "भाषा बदलें",
      largeText: "बड़े अक्षर",
      examples: "उदाहरण सवाल",
      tryAsking: "ऐसे पूछकर देखें:",
      conversation: "बातचीत",
      micLanguage: "पेज और आवाज़ की भाषा",
      speakQuestion: "अपना सवाल बोलें",
      yourQuestion: "आपका सवाल",
      placeholder: "अपना सवाल लिखें…",
      listening: "सुन रहे हैं… अब बोलें",
      micAsk: "कृपया माइक्रोफ़ोन की अनुमति दें (एड्रेस बार के पास संदेश देखें)।",
      micStarting: "माइक्रोफ़ोन शुरू हो रहा है…",
      ask: "पूछें",
      thinking: "योजना दस्तावेज़ों में खोज रहे हैं",
      detectedLanguage: "इस जवाब की भाषा",
      sources: "स्रोत",
      openPage: "आधिकारिक पेज खोलें",
      machineTranslation: "मशीनी अनुवाद",
      translationMissing: "अनुवाद उपलब्ध नहीं",
      newTab: "नए टैब में खुलता है",
      listen: "सुनें",
      preparingAudio: "आवाज़ तैयार हो रही है…",
      stopAudio: "रोकें",
      refusedTitle: "मेरे दस्तावेज़ों में नहीं है",
      aiUnavailable: "AI सारांश अभी उपलब्ध नहीं है। ये सबसे संबंधित आधिकारिक अंश हैं:",
      disclaimer: "जानकारी {date} तक के आधिकारिक योजना पेजों से। अंतिम निर्णय विभाग का होगा।",
      checkEligibility: "क्या मैं {scheme} के लिए पात्र हूँ? जाँचें",
      eligibilityTitle: "पात्रता जाँच",
      ok: "ठीक है",
      status: { met: "पूरी", not_met: "पूरी नहीं", unknown: "कार्यालय में जाँचें" },
      verdict: {
        likely_eligible: "आप पात्र लगते हैं। अंतिम निर्णय विभाग का होगा।",
        not_eligible: "आप इस योजना की कम से कम एक शर्त पूरी नहीं करते।",
        need_more_info: "कुछ बातें कार्यालय में जाँचनी होंगी।",
      },
      noChecklist: "इस योजना के लिए पात्रता जाँच अभी उपलब्ध नहीं है।",
      pill: { mock: "नमूना डेटा", live: "चालू", offline: "ऑफ़लाइन मोड", aiDown: "AI सारांश बंद", unreachable: "सर्वर से संपर्क नहीं" },
      errors: {
        timeout: "सर्वर ने जवाब देने में बहुत समय लिया। कृपया फिर से कोशिश करें।",
        network: "सर्वर से संपर्क नहीं हो पा रहा। कनेक्शन जाँचकर फिर कोशिश करें।",
        server: "सर्वर पर कुछ गड़बड़ हुई। कृपया फिर से कोशिश करें।",
        empty_query: "कृपया अपना सवाल लिखें या बोलें।",
        micDenied: "माइक्रोफ़ोन बंद है। एड्रेस बार में ताले के निशान पर क्लिक करके माइक्रोफ़ोन की अनुमति दें और फिर कोशिश करें, या सवाल लिखें।",
        micFailed: "आवाज़ सुनाई नहीं दी। फिर से कोशिश करें या सवाल लिखें।",
        micNoDevice: "कोई माइक्रोफ़ोन नहीं मिला। माइक लगाएँ या सवाल लिखें।",
        micNetwork: "इस ब्राउज़र में बोलकर पूछने के लिए इंटरनेट चाहिए। कृपया सवाल लिखें।",
        micNoSpeech: "कुछ सुनाई नहीं दिया। माइक दबाकर फिर से बोलें।",
        micUnsupported: "यह ब्राउज़र आवाज़ नहीं ले सकता। Chrome या Edge इस्तेमाल करें, या सवाल लिखें।",
        micTimeout: "माइक्रोफ़ोन शुरू नहीं हुआ। देखें कि कोई दूसरा ऐप इसे तो नहीं चला रहा, फिर कोशिश करें।",
        micLanguage: "इस भाषा में यहाँ बोलकर पूछना उपलब्ध नहीं है। कृपया सवाल लिखें।",
        noVoice: "इस ब्राउज़र में {lang} आवाज़ इंस्टॉल नहीं है।",
        noTts: "यह ब्राउज़र पढ़कर नहीं सुना सकता।",
      },
    },
    gu: {
      appName: "યોજના સાથી",
      continue: "આગળ વધો",
      tagline: "સરકારી યોજનાઓ, પ્રમાણપત્રો અને સબસિડી વિશે પૂછો.",
      changeLanguage: "ભાષા બદલો",
      largeText: "મોટા અક્ષર",
      examples: "ઉદાહરણ પ્રશ્નો",
      tryAsking: "આ રીતે પૂછી જુઓ:",
      conversation: "વાતચીત",
      micLanguage: "પેજ અને અવાજની ભાષા",
      speakQuestion: "તમારો પ્રશ્ન બોલો",
      yourQuestion: "તમારો પ્રશ્ન",
      placeholder: "તમારો પ્રશ્ન લખો…",
      listening: "સાંભળી રહ્યા છીએ… હવે બોલો",
      micAsk: "કૃપા કરીને માઇક્રોફોનની પરવાનગી આપો (એડ્રેસ બાર પાસે સંદેશ જુઓ).",
      micStarting: "માઇક્રોફોન શરૂ થઈ રહ્યો છે…",
      ask: "પૂછો",
      thinking: "યોજના દસ્તાવેજોમાં શોધી રહ્યા છીએ",
      detectedLanguage: "આ જવાબની ભાષા",
      sources: "સ્ત્રોત",
      openPage: "સત્તાવાર પેજ ખોલો",
      machineTranslation: "મશીન અનુવાદ",
      translationMissing: "અનુવાદ ઉપલબ્ધ નથી",
      newTab: "નવા ટેબમાં ખૂલે છે",
      listen: "સાંભળો",
      preparingAudio: "અવાજ તૈયાર થઈ રહ્યો છે…",
      stopAudio: "બંધ કરો",
      refusedTitle: "મારા દસ્તાવેજોમાં નથી",
      aiUnavailable: "AI સારાંશ હાલમાં ઉપલબ્ધ નથી. આ સૌથી સંબંધિત સત્તાવાર અંશો છે:",
      disclaimer: "માહિતી {date} સુધીના સત્તાવાર યોજના પેજ પરથી. અંતિમ નિર્ણય વિભાગનો રહેશે.",
      checkEligibility: "શું હું {scheme} માટે પાત્ર છું? તપાસો",
      eligibilityTitle: "પાત્રતા તપાસ",
      ok: "બરાબર",
      status: { met: "પૂરી", not_met: "પૂરી નથી", unknown: "કચેરીમાં તપાસો" },
      verdict: {
        likely_eligible: "તમે પાત્ર લાગો છો. અંતિમ નિર્ણય વિભાગનો રહેશે.",
        not_eligible: "તમે આ યોજનાની ઓછામાં ઓછી એક શરત પૂરી કરતા નથી.",
        need_more_info: "કેટલીક બાબતો કચેરીમાં તપાસવી પડશે.",
      },
      noChecklist: "આ યોજના માટે પાત્રતા તપાસ હજી ઉપલબ્ધ નથી.",
      pill: { mock: "નમૂના ડેટા", live: "ચાલુ", offline: "ઑફલાઇન મોડ", aiDown: "AI સારાંશ બંધ", unreachable: "સર્વર સાથે સંપર્ક નથી" },
      errors: {
        timeout: "સર્વરે જવાબ આપવામાં ઘણો સમય લીધો. કૃપા કરીને ફરી પ્રયાસ કરો.",
        network: "સર્વર સાથે સંપર્ક થઈ શકતો નથી. કનેક્શન તપાસીને ફરી પ્રયાસ કરો.",
        server: "સર્વર પર કંઈક ખોટું થયું. કૃપા કરીને ફરી પ્રયાસ કરો.",
        empty_query: "કૃપા કરીને તમારો પ્રશ્ન લખો અથવા બોલો.",
        micDenied: "માઇક્રોફોન બંધ છે. એડ્રેસ બારમાં તાળાના ચિહ્ન પર ક્લિક કરી માઇક્રોફોનની પરવાનગી આપો અને ફરી પ્રયાસ કરો, અથવા પ્રશ્ન લખો.",
        micFailed: "અવાજ સંભળાયો નહીં. ફરી પ્રયાસ કરો અથવા પ્રશ્ન લખો.",
        micNoDevice: "કોઈ માઇક્રોફોન મળ્યો નથી. માઇક જોડો અથવા પ્રશ્ન લખો.",
        micNetwork: "આ બ્રાઉઝરમાં બોલીને પૂછવા માટે ઇન્ટરનેટ જોઈએ. કૃપા કરીને પ્રશ્ન લખો.",
        micNoSpeech: "કંઈ સંભળાયું નહીં. માઇક દબાવીને ફરી બોલો.",
        micUnsupported: "આ બ્રાઉઝર અવાજ લઈ શકતું નથી. Chrome અથવા Edge વાપરો, અથવા પ્રશ્ન લખો.",
        micTimeout: "માઇક્રોફોન શરૂ થયો નહીં. બીજી કોઈ એપ તેને વાપરતી નથી ને તે જુઓ, પછી ફરી પ્રયાસ કરો.",
        micLanguage: "આ ભાષામાં અહીં બોલીને પૂછવાનું ઉપલબ્ધ નથી. કૃપા કરીને પ્રશ્ન લખો.",
        noVoice: "આ બ્રાઉઝરમાં {lang} અવાજ ઇન્સ્ટોલ નથી.",
        noTts: "આ બ્રાઉઝર વાંચીને સંભળાવી શકતું નથી.",
      },
    },
  },
};
