import React, { useState, useEffect, useRef } from 'react';
import { vasudevaAPI } from './api';
import {
  Sparkles,
  Send,
  BookOpen,
  Heart,
  Loader2,
  CheckCircle2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Mic,
  MicOff,
  Users,
  Target,
  Zap,
  Award
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import FeedbackButtons from './components/FeedbackButtons';

function App() {
  const [problem, setProblem] = useState('');
  const [guidance, setGuidance] = useState(null);
  const [loading, setLoading] = useState(false);
  const [storyLoading, setStoryLoading] = useState(false);  // NEW: Story loading state
  const [error, setError] = useState(null);
  const [showSources, setShowSources] = useState(false);
  const [apiStatus, setApiStatus] = useState('checking');
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(true);
  const recognitionRef = useRef(null);

  // Check API health on mount
  useEffect(() => {
    checkAPIHealth();
    initializeSpeechRecognition();
  }, []);

  const initializeSpeechRecognition = () => {
    // Check if browser supports Speech Recognition
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setSpeechSupported(false);
      console.warn('Speech recognition not supported in this browser');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setIsListening(true);
      setError(null);
    };

    recognition.onresult = (event) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript + ' ';
        } else {
          interimTranscript += transcript;
        }
      }

      // Update the problem field with interim or final transcript
      if (finalTranscript) {
        setProblem(prev => prev + finalTranscript);
      } else if (interimTranscript) {
        // Show interim results without updating state permanently
        setProblem(prev => prev + interimTranscript);
      }
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      setIsListening(false);

      if (event.error === 'no-speech') {
        setError('No speech detected. Please try again.');
      } else if (event.error === 'not-allowed') {
        setError('Microphone access denied. Please allow microphone access.');
      } else {
        setError(`Speech recognition error: ${event.error}`);
      }
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;
  };

  const toggleListening = () => {
    if (!speechSupported) {
      setError('Speech recognition is not supported in your browser. Please use Chrome, Edge, or Safari.');
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
    } else {
      try {
        recognitionRef.current?.start();
      } catch (err) {
        console.error('Error starting speech recognition:', err);
        setError('Could not start speech recognition. Please try again.');
      }
    }
  };

  const checkAPIHealth = async () => {
    try {
      await vasudevaAPI.checkHealth();
      setApiStatus('online');
    } catch (err) {
      setApiStatus('offline');
      setError('Cannot connect to Vasudeva. Please ensure the backend is running.');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!problem.trim()) {
      setError('Please describe your problem');
      return;
    }

    if (problem.trim().length < 10) {
      setError('Please provide more details (at least 10 characters)');
      return;
    }

    setLoading(true);
    setError(null);
    setGuidance(null);
    setStoryLoading(false);

    try {
      // Step 1: Load guidance FAST (3-5s, no story)
      const guidanceResult = await vasudevaAPI.getGuidance(problem, false);
      setGuidance(guidanceResult);
      setLoading(false);

      // Step 2: Load story SLOWLY in background (30-40s with fact-checking)
      setStoryLoading(true);
      try {
        const storyResult = await vasudevaAPI.getStory(problem);
        if (storyResult.story) {
          // Update guidance with story
          setGuidance(prev => ({
            ...prev,
            story: storyResult.story
          }));
        }
      } catch (storyErr) {
        console.error('Story loading failed:', storyErr);
        // Story failed, but guidance already loaded - graceful degradation
      } finally {
        setStoryLoading(false);
      }
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        'Failed to get guidance. Please try again.'
      );
      setLoading(false);
    }
  };

  const handleReset = () => {
    setProblem('');
    setGuidance(null);
    setError(null);
    setShowSources(false);
  };

  return (
    <div className="min-h-screen py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <div className="flex items-center justify-center mb-4">
            <Sparkles className="w-12 h-12 text-orange-500 animate-pulse-slow" />
          </div>
          <h1 className="text-5xl md:text-6xl font-display font-bold text-transparent bg-clip-text wisdom-gradient mb-4">
            Vasudeva
          </h1>
          <p className="text-xl text-gray-600 font-light">
            Ancient Wisdom for Modern Problems
          </p>

          {/* Status indicator */}
          <div className="mt-4 flex items-center justify-center gap-2">
            {apiStatus === 'online' ? (
              <>
                <CheckCircle2 className="w-4 h-4 text-green-500" />
                <span className="text-sm text-green-600">Connected</span>
              </>
            ) : apiStatus === 'offline' ? (
              <>
                <AlertCircle className="w-4 h-4 text-red-500" />
                <span className="text-sm text-red-600">Offline</span>
              </>
            ) : (
              <>
                <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
                <span className="text-sm text-gray-500">Connecting...</span>
              </>
            )}
          </div>
        </motion.div>

        {/* Main Card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
          className="glass-card rounded-2xl p-8 mb-8"
        >
          {!guidance ? (
            /* Input Form */
            <form onSubmit={handleSubmit}>
              <div className="mb-6">
                <label
                  htmlFor="problem"
                  className="block text-lg font-medium text-gray-700 mb-3 flex items-center gap-2"
                >
                  <Heart className="w-5 h-5 text-orange-500" />
                  What's troubling you?
                </label>

                <div className="relative">
                  <textarea
                    id="problem"
                    rows="6"
                    className="w-full px-4 py-3 pr-16 border-2 border-orange-200 rounded-xl 
                             focus:ring-2 focus:ring-orange-500 focus:border-transparent
                             placeholder-gray-400 text-gray-800 resize-none
                             transition-all duration-200"
                    placeholder="Share your problem, worry, or question here. Vasudeva will guide you with wisdom from sacred texts..."
                    value={problem}
                    onChange={(e) => setProblem(e.target.value)}
                    disabled={loading || apiStatus === 'offline'}
                  />

                  {/* Voice Input Button */}
                  <button
                    type="button"
                    onClick={toggleListening}
                    disabled={loading || apiStatus === 'offline'}
                    className={`absolute right-3 bottom-3 p-3 rounded-full transition-all duration-200
                              ${isListening
                        ? 'bg-red-500 hover:bg-red-600 animate-pulse'
                        : 'bg-orange-500 hover:bg-orange-600'
                      } text-white shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed`}
                    title={isListening ? 'Stop recording' : 'Click to speak'}
                  >
                    {isListening ? (
                      <MicOff className="w-5 h-5" />
                    ) : (
                      <Mic className="w-5 h-5" />
                    )}
                  </button>
                </div>

                <div className="flex items-center justify-between mt-2">
                  <p className="text-sm text-gray-500">
                    {problem.length} characters (minimum 10 required)
                  </p>
                  {speechSupported && (
                    <p className="text-xs text-orange-600 flex items-center gap-1">
                      <Mic className="w-3 h-3" />
                      {isListening ? 'Listening...' : 'Click mic to speak'}
                    </p>
                  )}
                </div>

                {/* Voice Recording Indicator */}
                {isListening && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex gap-1">
                        {[0, 1, 2, 3].map((i) => (
                          <motion.div
                            key={i}
                            animate={{
                              height: ['12px', '24px', '12px'],
                            }}
                            transition={{
                              duration: 0.8,
                              repeat: Infinity,
                              delay: i * 0.1,
                            }}
                            className="w-1 bg-red-500 rounded-full"
                          />
                        ))}
                      </div>
                      <p className="text-sm text-red-700 font-medium">
                        🎤 Listening... Speak your question to Vasudeva
                      </p>
                    </div>
                  </motion.div>
                )}
              </div>

              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3"
                >
                  <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                  <p className="text-red-700">{error}</p>
                </motion.div>
              )}

              {/* Loading Animation */}
              {loading && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="mb-6 p-8 bg-gradient-to-br from-orange-50 to-amber-50 rounded-xl border-2 border-orange-200 relative overflow-hidden"
                >
                  {/* Shimmer effect background */}
                  <div className="absolute inset-0 animate-shimmer" />

                  <div className="relative flex flex-col items-center gap-6">
                    {/* Multiple Book Pages Stacked */}
                    <div className="relative w-32 h-32">
                      {/* Book pages layered effect */}
                      {[0, 1, 2].map((index) => (
                        <motion.div
                          key={index}
                          animate={{
                            rotateY: [0, 180, 360],
                            x: [0, 10, 0],
                            opacity: [0.4, 1, 0.4]
                          }}
                          transition={{
                            duration: 2.5,
                            repeat: Infinity,
                            ease: "easeInOut",
                            delay: index * 0.3
                          }}
                          className="absolute inset-0 flex items-center justify-center"
                          style={{ zIndex: 3 - index }}
                        >
                          <div className={`opacity-${100 - (index * 20)}`}>
                            <BookOpen className={`w-${24 - (index * 2)} h-${24 - (index * 2)} text-orange-${500 - (index * 100)}`} />
                          </div>
                        </motion.div>
                      ))}

                      {/* Sparkles around books */}
                      {[
                        { top: -2, right: -2, delay: 0 },
                        { bottom: -2, left: -2, delay: 0.5 },
                        { top: -2, left: -2, delay: 1 },
                        { bottom: -2, right: -2, delay: 1.5 }
                      ].map((pos, i) => (
                        <motion.div
                          key={i}
                          animate={{
                            scale: [1, 1.3, 1],
                            opacity: [0.4, 1, 0.4],
                            rotate: [0, 180, 360]
                          }}
                          transition={{
                            duration: 2,
                            repeat: Infinity,
                            delay: pos.delay
                          }}
                          className="absolute"
                          style={pos}
                        >
                          <Sparkles className="w-5 h-5 text-amber-400" />
                        </motion.div>
                      ))}
                    </div>

                    {/* Loading Text */}
                    <div className="text-center space-y-3">
                      <motion.div
                        animate={{
                          opacity: [0.7, 1, 0.7]
                        }}
                        transition={{
                          duration: 1.5,
                          repeat: Infinity,
                        }}
                      >
                        <h3 className="text-lg font-semibold text-orange-700 mb-1 flex items-center justify-center gap-2">
                          <BookOpen className="w-5 h-5" />
                          Vasudeva is consulting the ancient texts...
                        </h3>
                      </motion.div>

                      <motion.div
                        animate={{
                          opacity: [0.6, 0.9, 0.6]
                        }}
                        transition={{
                          duration: 2,
                          repeat: Infinity,
                        }}
                        className="bg-orange-100/50 rounded-lg p-3 border border-orange-200"
                      >
                        <p className="text-sm text-orange-600 italic leading-relaxed">
                          Vasudeva is busy addressing millions like you..
                          <br />
                          <span className="text-orange-700 font-medium">Please be patient 🙏</span>
                        </p>
                      </motion.div>

                      {/* Page numbers flipping */}
                      <div className="flex items-center justify-center gap-2 text-xs text-orange-500">
                        <span>Page</span>
                        <motion.span
                          animate={{
                            opacity: [0, 1, 0]
                          }}
                          transition={{
                            duration: 1,
                            repeat: Infinity,
                          }}
                          className="font-mono font-bold"
                        >
                          {Math.floor(Math.random() * 999) + 1}
                        </motion.span>
                      </div>

                      {/* Animated dots */}
                      <div className="flex justify-center gap-1.5">
                        {[0, 1, 2, 3, 4].map((i) => (
                          <motion.div
                            key={i}
                            animate={{
                              scale: [1, 1.5, 1],
                              opacity: [0.3, 1, 0.3],
                            }}
                            transition={{
                              duration: 1.5,
                              repeat: Infinity,
                              delay: i * 0.15,
                            }}
                            className="w-1.5 h-1.5 bg-orange-500 rounded-full"
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}

              <button
                type="submit"
                disabled={loading || apiStatus === 'offline'}
                className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Seeking wisdom...
                  </>
                ) : (
                  <>
                    <Send className="w-5 h-5" />
                    Ask Vasudeva
                  </>
                )}
              </button>
            </form>
          ) : (
            /* Guidance Display */
            <AnimatePresence mode="wait">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
              >
                {/* Your Problem */}
                <div className="mb-6 pb-6 border-b border-orange-100">
                  <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
                    Your Question
                  </h3>
                  <p className="text-gray-700 italic">"{guidance.problem}"</p>
                </div>



                {/* Guidance - SHOWN FIRST (Loads Fast ~5s) */}
                <div className="mb-6">
                  <h3 className="text-lg font-semibold text-orange-600 mb-4 flex items-center gap-2">
                    <Sparkles className="w-5 h-5" />
                    Vasudeva's Guidance
                  </h3>
                  <div className="bg-gradient-to-r from-orange-50 to-amber-50 rounded-xl p-6 border-l-4 border-orange-500">
                    <p className="text-gray-800 leading-relaxed text-lg">
                      {guidance.guidance}
                    </p>
                  </div>
                </div>

                {/* Story sections below load asynchronously */}
                {/* Story Skeleton Loading */}
                {storyLoading && !guidance.story && (
                  <div className="mb-6">
                    <h3 className="text-lg font-semibold text-purple-600 mb-4 flex items-center gap-2">
                      <BookOpen className="w-5 h-5" />
                      A Story from the Sacred Texts
                    </h3>

                    <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-200 animate-pulse">
                      {/* Skeleton Header */}
                      <div className="pb-4 mb-4 border-b border-purple-200">
                        <div className="flex items-start gap-2 mb-3">
                          <div className="w-5 h-5 bg-purple-300 rounded-full"></div>
                          <div className="flex-1">
                            <div className="h-5 bg-purple-300 rounded w-2/3 mb-2"></div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-4 h-4 bg-purple-300 rounded"></div>
                          <div className="h-4 bg-purple-300 rounded w-1/2"></div>
                        </div>
                      </div>

                      {/* Skeleton Content - 3 paragraphs */}
                      <div className="space-y-3">
                        <div className="space-y-2">
                          <div className="h-4 bg-purple-200 rounded w-full"></div>
                          <div className="h-4 bg-purple-200 rounded w-full"></div>
                          <div className="h-4 bg-purple-200 rounded w-4/5"></div>
                        </div>
                        <div className="space-y-2">
                          <div className="h-4 bg-purple-200 rounded w-full"></div>
                          <div className="h-4 bg-purple-200 rounded w-full"></div>
                          <div className="h-4 bg-purple-200 rounded w-3/4"></div>
                        </div>
                        <div className="space-y-2">
                          <div className="h-4 bg-purple-200 rounded w-full"></div>
                          <div className="h-4 bg-purple-200 rounded w-5/6"></div>
                        </div>
                      </div>

                      {/* Finding text */}
                      <div className="mt-4 flex items-center justify-center gap-2 text-purple-600 text-sm">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Finding a relevant story...</span>
                      </div>
                    </div>
                  </div>
                )}

                {guidance.story && guidance.story.narrative && (
                  <div className="mb-6">
                    <h3 className="text-lg font-semibold text-purple-600 mb-4 flex items-center gap-2">
                      <BookOpen className="w-5 h-5" />
                      A Story from the Sacred Texts
                    </h3>

                    <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 border-2 border-purple-200">
                      {/* Story Title & Source Header */}
                      <div className="pb-4 mb-4 border-b border-purple-200">
                        {/* Story Title */}
                        <div className="flex items-start gap-2 mb-3">
                          <Users className="w-5 h-5 text-purple-600 flex-shrink-0 mt-0.5" />
                          <h4 className="text-base font-bold text-purple-800">
                            {guidance.story.title || guidance.story.character || 'Sacred Story'}
                          </h4>
                        </div>

                        {/* Detailed Source */}
                        <div className="flex items-center gap-2">
                          <BookOpen className="w-4 h-4 text-purple-600 flex-shrink-0" />
                          <span className="text-sm text-purple-700 font-medium">
                            {guidance.story.source}
                          </span>
                        </div>
                      </div>

                      {/* Narrative Story */}
                      <div className="prose prose-purple max-w-none">
                        <p className="text-gray-800 leading-relaxed whitespace-pre-line">
                          {guidance.story.narrative}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Sources */}
                {guidance.sources && guidance.sources.length > 0 && (
                  <div className="mb-6">
                    <button
                      onClick={() => setShowSources(!showSources)}
                      className="flex items-center gap-2 text-orange-600 hover:text-orange-700 
                               font-medium transition-colors mb-3"
                    >
                      <BookOpen className="w-5 h-5" />
                      View Sacred Wisdom Sources ({guidance.sources.length})
                      {showSources ? (
                        <ChevronUp className="w-4 h-4" />
                      ) : (
                        <ChevronDown className="w-4 h-4" />
                      )}
                    </button>

                    <AnimatePresence>
                      {showSources && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          className="space-y-3"
                        >
                          {guidance.sources.map((source, idx) => (
                            <div
                              key={idx}
                              className="bg-white/50 rounded-lg p-4 border border-orange-100"
                            >
                              <div className="flex items-start gap-3">
                                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-orange-500 
                                               text-white text-sm flex items-center justify-center font-medium">
                                  {source.relevance_rank}
                                </span>
                                <div className="flex-1">
                                  <p className="text-gray-700 text-sm leading-relaxed mb-2">
                                    {source.text}
                                  </p>
                                  {source.metadata && (
                                    <p className="text-xs text-gray-500">
                                      Source: {source.metadata.source || 'Wisdom Text'}
                                      {source.metadata.page && ` - Page ${source.metadata.page}`}
                                    </p>
                                  )}
                                </div>
                              </div>
                            </div>
                          ))}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )}

                {/* Feedback Section */}
                <div className="mt-6 pt-6 border-t border-gray-200">
                  <FeedbackButtons
                    question={guidance.problem}
                    guidance={guidance.guidance}
                    story={guidance.story}
                    onFeedbackSubmitted={(vote) => console.log('Feedback submitted:', vote)}
                  />
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3 pt-6 border-t border-orange-100">
                  <button
                    onClick={handleReset}
                    className="flex-1 px-6 py-3 bg-white border-2 border-orange-300 
                             text-orange-600 font-medium rounded-lg hover:bg-orange-50
                             transition-colors"
                  >
                    Ask Another Question
                  </button>
                </div>
              </motion.div>
            </AnimatePresence>
          )}
        </motion.div>

        {/* Footer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-center text-gray-600"
        >
          <p className="text-sm">
            Powered by ancient wisdom and modern AI
          </p>
          <p className="text-xs mt-2 text-gray-500">
            Guidance is based on timeless teachings. Always trust your own judgment.
          </p>
        </motion.div>
      </div>
    </div>
  );
}

export default App;

