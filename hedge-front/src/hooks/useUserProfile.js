import { useCallback, useEffect, useState } from 'react';

export const DEFAULT_USER_PROFILE = {
  name: '사용자',
  email: '',
};

const PROFILE_STORAGE_KEY = 'hm_profile';
export const PROFILE_UPDATED_EVENT = 'hm_profile_updated';

const legacyValue = (codes) => codes.map((code) => String.fromCharCode(code)).join('');
const LEGACY_PLACEHOLDER_NAMES = new Set([
  legacyValue([72, 101, 100, 103, 101, 77, 97, 116, 101, 32, 85, 115, 101, 114]),
]);
const LEGACY_PLACEHOLDER_EMAILS = new Set([
  legacyValue([117, 115, 101, 114, 64, 104, 101, 100, 103, 101, 109, 97, 116, 101, 46, 105, 111]),
]);

const normalizeProfile = (value = {}) => ({
  name: typeof value.name === 'string'
    && value.name.trim()
    && !LEGACY_PLACEHOLDER_NAMES.has(value.name.trim())
    ? value.name.trim()
    : DEFAULT_USER_PROFILE.name,
  email: typeof value.email === 'string'
    && value.email.trim()
    && !LEGACY_PLACEHOLDER_EMAILS.has(value.email.trim())
    ? value.email.trim()
    : DEFAULT_USER_PROFILE.email,
});

const readStoredProfile = () => {
  try {
    const stored = localStorage.getItem(PROFILE_STORAGE_KEY);
    return stored ? normalizeProfile(JSON.parse(stored)) : DEFAULT_USER_PROFILE;
  } catch {
    return DEFAULT_USER_PROFILE;
  }
};

const writeStoredProfile = (profile) => {
  const nextProfile = normalizeProfile(profile);
  localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(nextProfile));
  window.dispatchEvent(new CustomEvent(PROFILE_UPDATED_EVENT, { detail: nextProfile }));
  return nextProfile;
};

export const useUserProfile = () => {
  const [profile, setProfile] = useState(readStoredProfile);

  useEffect(() => {
    const refreshProfile = () => setProfile(readStoredProfile());
    const handleStorage = (event) => {
      if (event.key === PROFILE_STORAGE_KEY) refreshProfile();
    };

    window.addEventListener(PROFILE_UPDATED_EVENT, refreshProfile);
    window.addEventListener('storage', handleStorage);
    return () => {
      window.removeEventListener(PROFILE_UPDATED_EVENT, refreshProfile);
      window.removeEventListener('storage', handleStorage);
    };
  }, []);

  const saveProfile = useCallback((updates) => {
    const nextProfile = writeStoredProfile({
      ...readStoredProfile(),
      ...updates,
    });
    setProfile(nextProfile);
  }, []);

  return { profile, saveProfile };
};
