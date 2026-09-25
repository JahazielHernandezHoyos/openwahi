import { isEmailAllowed, getAllowedEmails } from '@/lib/email-whitelist';

describe('Email Whitelist', () => {
  const originalEnv = process.env.NEXT_PUBLIC_ALLOWED_EMAILS;

  afterEach(() => {
    // Restore original env
    process.env.NEXT_PUBLIC_ALLOWED_EMAILS = originalEnv;
  });

  describe('isEmailAllowed', () => {
    it('should allow email when it is in the whitelist', () => {
      process.env.NEXT_PUBLIC_ALLOWED_EMAILS = 'admin@example.com,test@example.com';

      expect(isEmailAllowed('admin@example.com')).toBe(true);
      expect(isEmailAllowed('test@example.com')).toBe(true);
    });

    it('should be case insensitive', () => {
      process.env.NEXT_PUBLIC_ALLOWED_EMAILS = 'admin@example.com';

      expect(isEmailAllowed('ADMIN@EXAMPLE.COM')).toBe(true);
      expect(isEmailAllowed('Admin@Example.com')).toBe(true);
    });

    it('should reject email when it is not in the whitelist', () => {
      process.env.NEXT_PUBLIC_ALLOWED_EMAILS = 'admin@example.com';

      expect(isEmailAllowed('unauthorized@example.com')).toBe(false);
      expect(isEmailAllowed('attacker@example.net')).toBe(false);
    });

    it('should allow all emails when whitelist is empty', () => {
      process.env.NEXT_PUBLIC_ALLOWED_EMAILS = '';

      expect(isEmailAllowed('anyone@example.com')).toBe(true);
      expect(isEmailAllowed('test@test.com')).toBe(true);
    });

    it('should allow all emails when whitelist is not defined', () => {
      delete process.env.NEXT_PUBLIC_ALLOWED_EMAILS;

      expect(isEmailAllowed('anyone@example.com')).toBe(true);
    });

    it('should reject null or undefined email', () => {
      process.env.NEXT_PUBLIC_ALLOWED_EMAILS = 'admin@example.com';

      expect(isEmailAllowed(null)).toBe(false);
      expect(isEmailAllowed(undefined)).toBe(false);
    });

    it('should handle whitespace in email list', () => {
      process.env.NEXT_PUBLIC_ALLOWED_EMAILS = ' admin@example.com , test@example.com , ops@example.com ';

      expect(isEmailAllowed('admin@example.com')).toBe(true);
      expect(isEmailAllowed('test@example.com')).toBe(true);
      expect(isEmailAllowed('ops@example.com')).toBe(true);
    });
  });

  describe('getAllowedEmails', () => {
    it('should return list of allowed emails', () => {
      process.env.NEXT_PUBLIC_ALLOWED_EMAILS = 'admin@example.com,test@example.com';

      const emails = getAllowedEmails();
      expect(emails).toEqual(['admin@example.com', 'test@example.com']);
    });

    it('should return empty array when no whitelist is configured', () => {
      process.env.NEXT_PUBLIC_ALLOWED_EMAILS = '';

      expect(getAllowedEmails()).toEqual([]);
    });

    it('should trim whitespace from emails', () => {
      process.env.NEXT_PUBLIC_ALLOWED_EMAILS = ' email1@test.com , email2@test.com ';

      const emails = getAllowedEmails();
      expect(emails).toEqual(['email1@test.com', 'email2@test.com']);
    });
  });
});
