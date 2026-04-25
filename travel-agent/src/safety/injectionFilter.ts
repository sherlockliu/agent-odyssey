const INJECTION_PATTERNS = [
  /ignore\s+(previous|prior|all)\s+instructions/i,
  /you\s+are\s+now/i,
  /system\s+prompt/i,
  /<\|system\|>/i,
  /\[INST\]/i,
  /disregard\s+(all|previous|prior)\s+(instructions|rules)/i,
  /forget\s+(all|your)\s+(previous|prior)\s+(instructions|training)/i,
  /override\s+(safety|guidelines|constraints)/i,
  /act\s+as\s+(if\s+you\s+(are|were)|an?\s+)/i,
];

export function detectInjection(text: string): boolean {
  return INJECTION_PATTERNS.some(pattern => pattern.test(text));
}
