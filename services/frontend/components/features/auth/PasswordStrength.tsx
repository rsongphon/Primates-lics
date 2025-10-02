'use client';

import React from 'react';
import {
  calculatePasswordStrength,
  getPasswordStrengthColor,
  getPasswordStrengthTextColor,
  PasswordStrength as PasswordStrengthLevel,
} from '@/lib/validation';

interface PasswordStrengthProps {
  password: string;
  showFeedback?: boolean;
}

export function PasswordStrength({ password, showFeedback = true }: PasswordStrengthProps) {
  const result = calculatePasswordStrength(password);

  if (!password) {
    return null;
  }

  return (
    <div className="space-y-2">
      {/* Strength bar */}
      <div className="flex items-center space-x-2">
        <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${getPasswordStrengthColor(result.strength)}`}
            style={{ width: `${result.percentage}%` }}
          />
        </div>
        <span className={`text-sm font-medium ${getPasswordStrengthTextColor(result.strength)}`}>
          {result.label}
        </span>
      </div>

      {/* Feedback */}
      {showFeedback && result.feedback.length > 0 && (
        <ul className="text-xs text-gray-600 space-y-1">
          {result.feedback.map((item, index) => (
            <li key={index} className="flex items-start">
              <span className="mr-1">
                {result.strength === PasswordStrengthLevel.STRONG ? '✓' : '•'}
              </span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
