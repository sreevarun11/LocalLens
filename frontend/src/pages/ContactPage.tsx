import React, { useState } from 'react';
import { Mail, MessageSquare, CheckCircle2, Send, MapPin } from 'lucide-react';
import { api } from '../services/api';

export const ContactPage: React.FC = () => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [category, setCategory] = useState('data_feedback');
  const [message, setMessage] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;
    setIsSubmitting(true);
    try {
      await api.submitFeedback({
        feedback_type: category,
        description: `From: ${name} (${email})\nCategory: ${category}\nMessage: ${message}`
      });
      setSubmitted(true);
    } catch {
      setSubmitted(true);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-10">
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-50 border border-teal-200 text-teal-800 text-xs font-semibold">
          <Mail className="w-3.5 h-3.5 text-teal-600" />
          <span>Contact & Support</span>
        </div>
        <h1 className="font-display font-bold text-3xl text-navy-900">
          Get in Touch
        </h1>
        <p className="text-xs text-slate-600 max-w-xl mx-auto">
          Have questions about neighborhood data coverage, report verification, or partnerships? Reach out to our engineering team.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
        {/* Contact Info Box */}
        <div className="md:col-span-5 bg-navy-900 text-white p-6 rounded-3xl space-y-6">
          <div>
            <h3 className="font-display font-bold text-lg text-white">LocalLens Headquarters</h3>
            <p className="text-xs text-slate-300 mt-1">
              Geospatial Evidence & Intelligence Systems
            </p>
          </div>

          <div className="space-y-4 text-xs text-slate-300">
            <div className="flex items-start gap-3">
              <Mail className="w-4 h-4 text-teal-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-white block">Email Support</span>
                <span>support@locallens.app</span>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <MapPin className="w-4 h-4 text-teal-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-white block">Operational Hub</span>
                <span>Bengaluru & Hyderabad, India</span>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <MessageSquare className="w-4 h-4 text-teal-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-white block">Response SLA</span>
                <span>Within 24 business hours</span>
              </div>
            </div>
          </div>
        </div>

        {/* Contact Form */}
        <div className="md:col-span-7 bg-white p-6 rounded-3xl border border-slate-200 shadow-xs">
          {submitted ? (
            <div className="p-8 text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center mx-auto">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <h3 className="font-display font-bold text-lg text-navy-900">Message Received</h3>
              <p className="text-xs text-slate-600 max-w-sm mx-auto">
                Thank you for contacting LocalLens. Our team will review your message and respond shortly.
              </p>
              <button
                type="button"
                onClick={() => {
                  setSubmitted(false);
                  setMessage('');
                }}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-xl text-xs font-semibold text-slate-700 transition-colors"
              >
                Send another message
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Your Name</label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Aditi Sharma"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-xs text-slate-900 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/10"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Email Address</label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="aditi@example.com"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-xs text-slate-900 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/10"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Category</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-xs text-slate-900 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/10 bg-white"
                >
                  <option value="data_feedback">Data Accuracy / Mapping Feedback</option>
                  <option value="report_support">Report Generation Support</option>
                  <option value="verification">Public Verification Inquiry</option>
                  <option value="business">Enterprise / Municipal Collaboration</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">Your Message</label>
                <textarea
                  required
                  rows={4}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Describe your inquiry, locality discrepancy, or feedback..."
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-xs text-slate-900 outline-none focus:border-teal-500 focus:ring-2 focus:ring-teal-500/10 resize-none"
                />
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-2.5 bg-navy-900 hover:bg-navy-800 text-white rounded-xl text-xs font-bold transition-colors flex items-center justify-center gap-2 cursor-pointer shadow-xs disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{isSubmitting ? 'Sending...' : 'Send Message'}</span>
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
