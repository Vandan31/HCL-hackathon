/**
 * COMPONENT : ui (config)
 * PURPOSE   : Every value the UI may need to change live during the demo, in one file.
 * INPUTS    : none
 * OUTPUTS   : CONFIG object, imported by src/ui/*.js
 * DEPENDS ON: nothing
 * PANEL NOTE: All UI knobs live here, so a change in front of judges is a one-line edit plus a browser refresh.
 */

export const CONFIG = {
  // --- Backend connection -------------------------------------------------
  API_BASE: "",               // DEMO-KNOB: "" = same server that serves the UI; set "http://localhost:8000" if the API runs separately
  USE_MOCK: true,             // DEMO-KNOB: true until /api/ask is live (Harsh, comp/api); set false at integration
  MOCK_DELAY_MS: 700,         // DEMO-KNOB: fake network delay so loading states are visible when using the mock
  MOCK_FORCE_ERROR: null,     // DEMO-KNOB: null | "llm_unavailable" | "network" to click-test the error screens
  REQUEST_TIMEOUT_MS: 12000,  // DEMO-KNOB: PLAN §4.5 targets p95 < 5 s; 12 s leaves slack before we show an error

  // --- Voice (bonus; browser Web Speech API, free, no keys) ----------------
  ENABLE_VOICE_INPUT: true,   // DEMO-KNOB: false hides the mic if it misbehaves on stage
  ENABLE_VOICE_OUTPUT: true,  // DEMO-KNOB: false hides the "Listen" buttons
  AUTO_SPEAK_ANSWERS: false,  // DEMO-KNOB: true reads every answer aloud as soon as it arrives
  DEFAULT_MIC_LANG: "gu",     // DEMO-KNOB: mic language preselected for the demo (en | hi | gu)

  // --- Accessibility -------------------------------------------------------
  LARGE_TEXT_DEFAULT: false,  // DEMO-KNOB: start in large-text mode (for low-vision users or a far-away projector)

  // --- Content -------------------------------------------------------------
  DATA_AS_OF: "27 Oct 2026",  // DEMO-KNOB: date the scheme pages were collected; shown under every answer (PLAN §4.6)

  // DEMO-KNOB: clickable example questions; these follow the demo script in PLAN §9.1
  SAMPLE_QUESTIONS: [
    "મને ખેડૂત તરીકે કઈ સહાય મળી શકે?",
    "PM awas yojana ke liye kaunse documents chahiye?",
    "पीएम किसान में कितना पैसा मिलता है?",
    "Passport kaise banaye?",
  ],

  // WHY: speech recognition must be told the language before listening; it can't auto-detect.
  SPEECH_LANG: { en: "en-IN", hi: "hi-IN", gu: "gu-IN", hinglish: "en-IN" },

  // Shown on the language badge of each answer.
  LANG_LABELS: { en: "English", hi: "हिन्दी", gu: "ગુજરાતી", hinglish: "Hinglish" },

  // WHY: the words around an answer (Sources, Listen, disclaimer) must match the answer's language,
  // otherwise a Gujarati user still has to read English to use the result.
  STRINGS: {
    en: {
      sources: "Sources",
      openPage: "Open official page",
      listen: "Listen",
      refusedTitle: "Not in my documents",
      aiUnavailable: "AI summary is unavailable right now. These are the most relevant official passages:",
      disclaimer: "Information from official scheme pages as of {date}. The final decision rests with the department.",
    },
    hi: {
      sources: "स्रोत",
      openPage: "आधिकारिक पेज खोलें",
      listen: "सुनें",
      refusedTitle: "मेरे दस्तावेज़ों में नहीं है",
      aiUnavailable: "AI सारांश अभी उपलब्ध नहीं है। ये सबसे संबंधित आधिकारिक अंश हैं:",
      disclaimer: "जानकारी {date} तक के आधिकारिक योजना पेजों से। अंतिम निर्णय विभाग का होगा।",
    },
    gu: {
      sources: "સ્ત્રોત",
      openPage: "સત્તાવાર પેજ ખોલો",
      listen: "સાંભળો",
      refusedTitle: "મારા દસ્તાવેજોમાં નથી",
      aiUnavailable: "AI સારાંશ હાલમાં ઉપલબ્ધ નથી. આ સૌથી સંબંધિત સત્તાવાર અંશો છે:",
      disclaimer: "માહિતી {date} સુધીના સત્તાવાર યોજના પેજ પરથી. અંતિમ નિર્ણય વિભાગનો રહેશે.",
    },
    hinglish: {
      sources: "Sources",
      openPage: "Official page kholein",
      listen: "Suniye",
      refusedTitle: "Mere documents mein nahi hai",
      aiUnavailable: "AI summary abhi available nahi hai. Ye sabse relevant official passages hain:",
      disclaimer: "Jaankari {date} tak ke official scheme pages se. Antim faisla department ka hoga.",
    },
  },
};
