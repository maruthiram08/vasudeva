import React, { useState } from 'react';
import { ThumbsUp, ThumbsDown, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const DOWNVOTE_REASONS = [
    { id: 'story_inaccurate', label: 'Story is inaccurate or fabricated' },
    { id: 'facts_incorrect', label: 'Facts are incorrect' },
    { id: 'not_relevant', label: 'Story not relevant to my question' },
    { id: 'guidance_generic', label: 'Guidance too generic' },
    { id: 'missing_context', label: 'Missing important context' },
    { id: 'story_incomplete', label: 'Story is incomplete' },
    { id: 'tone_inappropriate', label: 'Language/tone not appropriate' },
    { id: 'other', label: 'Other (please specify)' },
];

export default function FeedbackButtons({
    question,
    guidance,
    story,
    onFeedbackSubmitted
}) {
    const [voted, setVoted] = useState(null); // 'upvote' or 'downvote'
    const [showDownvoteModal, setShowDownvoteModal] = useState(false);
    const [selectedReason, setSelectedReason] = useState('');
    const [detailedFeedback, setDetailedFeedback] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const handleUpvote = async () => {
        setVoted('upvote');
        await submitFeedback('upvote', null, null);
    };

    const handleDownvote = () => {
        // Don't set voted here - wait for modal submission
        setShowDownvoteModal(true);
    };

    const submitFeedback = async (vote, reason, details) => {
        setSubmitting(true);
        try {
            const { vasudevaAPI } = await import('../api');

            // Get or create session ID
            let sessionId = sessionStorage.getItem('vasudeva_session');
            if (!sessionId) {
                sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
                sessionStorage.setItem('vasudeva_session', sessionId);
            }

            await vasudevaAPI.submitFeedback({
                session_id: sessionId,
                question,
                guidance,
                story,
                vote,
                downvote_reason: reason,
                detailed_feedback: details,
                response_time_ms: null, // Could track this if needed
            });

            if (onFeedbackSubmitted) {
                onFeedbackSubmitted(vote);
            }
        } catch (error) {
            console.error('Failed to submit feedback:', error);
        } finally {
            setSubmitting(false);
        }
    };

    const handleDownvoteSubmit = async () => {
        if (!selectedReason) return;

        await submitFeedback('downvote', selectedReason, detailedFeedback);
        setVoted('downvote');  // Set voted AFTER submission
        setShowDownvoteModal(false);
    };

    if (voted) {
        return (
            <div className="flex items-center gap-2 text-sm text-gray-600">
                {voted === 'upvote' ? (
                    <>
                        <ThumbsUp className="w-4 h-4 text-green-600 fill-green-600" />
                        <span>Thank you for your feedback!</span>
                    </>
                ) : (
                    <>
                        <ThumbsDown className="w-4 h-4 text-orange-600 fill-orange-600" />
                        <span>Thank you for helping us improve!</span>
                    </>
                )}
            </div>
        );
    }

    return (
        <>
            <div className="flex items-center gap-3">
                <span className="text-sm text-gray-600">Was this helpful?</span>
                <button
                    onClick={handleUpvote}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-green-200 
                   hover:bg-green-50 hover:border-green-300 transition-colors text-sm text-gray-700"
                    disabled={submitting}
                >
                    <ThumbsUp className="w-4 h-4" />
                    <span>Helpful</span>
                </button>
                <button
                    onClick={handleDownvote}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-orange-200 
                   hover:bg-orange-50 hover:border-orange-300 transition-colors text-sm text-gray-700"
                    disabled={submitting}
                >
                    <ThumbsDown className="w-4 h-4" />
                    <span>Not Helpful</span>
                </button>
            </div>

            {/* Downvote Reason Modal */}
            <AnimatePresence>
                {showDownvoteModal && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
                        onClick={() => setShowDownvoteModal(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.9, opacity: 0 }}
                            className="bg-white rounded-2xl p-6 max-w-md w-full shadow-xl"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-lg font-semibold text-gray-900">What went wrong?</h3>
                                <button
                                    onClick={() => setShowDownvoteModal(false)}
                                    className="text-gray-400 hover:text-gray-600"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            <div className="space-y-2 mb-4">
                                {DOWNVOTE_REASONS.map((reason) => (
                                    <label
                                        key={reason.id}
                                        className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 
                             hover:bg-gray-50 cursor-pointer transition-colors"
                                    >
                                        <input
                                            type="radio"
                                            name="downvote_reason"
                                            value={reason.id}
                                            checked={selectedReason === reason.id}
                                            onChange={(e) => setSelectedReason(e.target.value)}
                                            className="w-4 h-4 text-orange-600"
                                        />
                                        <span className="text-sm text-gray-700">{reason.label}</span>
                                    </label>
                                ))}
                            </div>

                            {selectedReason === 'other' && (
                                <textarea
                                    value={detailedFeedback}
                                    onChange={(e) => setDetailedFeedback(e.target.value)}
                                    placeholder="Please tell us what went wrong..."
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-4 text-sm"
                                    rows="3"
                                />
                            )}

                            <button
                                onClick={handleDownvoteSubmit}
                                disabled={!selectedReason || submitting}
                                className="w-full bg-orange-600 text-white py-2 rounded-lg hover:bg-orange-700 
                         disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            >
                                {submitting ? 'Submitting...' : 'Submit Feedback'}
                            </button>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
}
