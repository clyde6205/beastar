import React, { useState } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet, Alert } from 'react-native';
import { useTranslation } from 'react-i18next';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { signup } from '../api/client';
import { useAuth } from '../context/AuthContext';
import type { RootStackParamList } from '../navigation/AppNavigator';

type Props = NativeStackScreenProps<RootStackParamList, 'Signup'>;

// Minimum age enforced client-side too, matching the backend's hard
// constraint (schema.sql: age_minimum CHECK) — this is UX, not the real
// gate. The backend rejects underage signups regardless of what the app
// sends, so this is purely to give a fast, friendly error instead of
// waiting on a round-trip to find out.
const MIN_AGE_YEARS = 13;

function meetsMinimumAge(dob: Date): boolean {
  const cutoff = new Date();
  cutoff.setFullYear(cutoff.getFullYear() - MIN_AGE_YEARS);
  return dob <= cutoff;
}

export default function SignupScreen({ navigation }: Props) {
  const { t } = useTranslation();
  const { setUserId } = useAuth();

  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [dobText, setDobText] = useState(''); // YYYY-MM-DD
  const [countryCode, setCountryCode] = useState('PH');
  const [referralCode, setReferralCode] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    const dob = new Date(dobText);
    if (Number.isNaN(dob.getTime())) {
      Alert.alert('Invalid date', 'Please enter your birth date as YYYY-MM-DD.');
      return;
    }
    if (!meetsMinimumAge(dob)) {
      Alert.alert('Age requirement', t('signup_underage'));
      return;
    }

    setSubmitting(true);
    try {
      const result = await signup({
        email: email.trim(),
        display_name: displayName.trim(),
        date_of_birth: dobText,
        country_code: countryCode.trim().toUpperCase(),
        referral_code_used: referralCode.trim() || undefined,
      });
      await setUserId(result.user_id);
      navigation.replace('VerifyFace', { userId: result.user_id });
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? 'Something went wrong. Please try again.';
      Alert.alert('Signup failed', detail);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Be the Star You Were Born to Be</Text>

      <TextInput
        style={styles.input}
        placeholder="Email"
        autoCapitalize="none"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        style={styles.input}
        placeholder="Display name"
        value={displayName}
        onChangeText={setDisplayName}
      />
      <TextInput
        style={styles.input}
        placeholder="Birth date (YYYY-MM-DD)"
        value={dobText}
        onChangeText={setDobText}
      />
      <TextInput
        style={styles.input}
        placeholder="Country code (e.g. PH)"
        autoCapitalize="characters"
        maxLength={2}
        value={countryCode}
        onChangeText={setCountryCode}
      />
      <TextInput
        style={styles.input}
        placeholder="Referral code (optional)"
        autoCapitalize="characters"
        value={referralCode}
        onChangeText={setReferralCode}
      />

      <Pressable style={styles.button} onPress={handleSubmit} disabled={submitting}>
        <Text style={styles.buttonText}>{submitting ? 'Creating account…' : 'Become a Star'}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, justifyContent: 'center', backgroundColor: '#0B0B12' },
  title: { fontSize: 24, fontWeight: '700', color: '#F5C542', marginBottom: 24, textAlign: 'center' },
  input: {
    backgroundColor: '#1B1B26',
    color: '#FFFFFF',
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginBottom: 12,
  },
  button: { backgroundColor: '#F5C542', borderRadius: 8, paddingVertical: 14, marginTop: 8 },
  buttonText: { textAlign: 'center', fontWeight: '700', color: '#0B0B12' },
});
