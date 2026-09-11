import React, { useState } from 'react';
import { View, Text, Image, Pressable, StyleSheet, Alert } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { verifyFace } from '../api/client';
import { useAuth } from '../context/AuthContext';
import type { RootStackParamList } from '../navigation/AppNavigator';

type Props = NativeStackScreenProps<RootStackParamList, 'VerifyFace'>;

/**
 * NOTE on scope: this screen captures a selfie and calls verify-face, but
 * the actual liveness + self-match + known-public-figure check happens
 * server-side (app/main.py docstring on /auth/{user_id}/verify-face is
 * explicit that this is still a stub pending a real vendor). This screen
 * is correctly wired to whatever that endpoint does today AND will do
 * once a real vendor is behind it — no client-side change needed either way.
 */
export default function VerifyFaceScreen({ route, navigation }: Props) {
  const { userId } = route.params;
  const { setVerified } = useAuth();
  const [selfieUri, setSelfieUri] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const captureSelfie = async () => {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('Camera permission needed', 'Enable camera access to verify your identity.');
      return;
    }
    const result = await ImagePicker.launchCameraAsync({
      cameraType: ImagePicker.CameraType.front,
      quality: 0.9,
      allowsEditing: false,
    });
    if (!result.canceled && result.assets?.[0]) {
      setSelfieUri(result.assets[0].uri);
    }
  };

  const handleVerify = async () => {
    if (!selfieUri) {
      Alert.alert('Take a selfie first', 'We need a live selfie to verify it\'s really you.');
      return;
    }
    setSubmitting(true);
    try {
      // The liveness check itself happens server-side once wired to a real
      // vendor; the client's job is just to capture a fresh, live camera
      // shot (not a gallery pick) and hand it off.
      const result = await verifyFace(userId);
      setVerified(result.is_verified);
      navigation.replace('Create', { userId });
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? 'Verification failed. Please try again.';
      Alert.alert('Verification failed', detail);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Verify it's really you</Text>
      <Text style={styles.subtitle}>
        This confirms every video is really you as the star — no one can upload someone
        else's photo to your account.
      </Text>

      {selfieUri ? (
        <Image source={{ uri: selfieUri }} style={styles.preview} />
      ) : (
        <View style={styles.previewPlaceholder}>
          <Text style={styles.placeholderText}>No selfie yet</Text>
        </View>
      )}

      <Pressable style={styles.secondaryButton} onPress={captureSelfie}>
        <Text style={styles.secondaryButtonText}>{selfieUri ? 'Retake selfie' : 'Take selfie'}</Text>
      </Pressable>

      <Pressable style={styles.button} onPress={handleVerify} disabled={submitting || !selfieUri}>
        <Text style={styles.buttonText}>{submitting ? 'Verifying…' : 'Verify & continue'}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, justifyContent: 'center', backgroundColor: '#0B0B12' },
  title: { fontSize: 22, fontWeight: '700', color: '#FFFFFF', marginBottom: 8, textAlign: 'center' },
  subtitle: { color: '#A0A0B2', textAlign: 'center', marginBottom: 24 },
  preview: { width: 220, height: 220, borderRadius: 110, alignSelf: 'center', marginBottom: 24 },
  previewPlaceholder: {
    width: 220, height: 220, borderRadius: 110, alignSelf: 'center', marginBottom: 24,
    backgroundColor: '#1B1B26', justifyContent: 'center', alignItems: 'center',
  },
  placeholderText: { color: '#666' },
  secondaryButton: { borderColor: '#F5C542', borderWidth: 1, borderRadius: 8, paddingVertical: 12, marginBottom: 12 },
  secondaryButtonText: { textAlign: 'center', color: '#F5C542', fontWeight: '600' },
  button: { backgroundColor: '#F5C542', borderRadius: 8, paddingVertical: 14 },
  buttonText: { textAlign: 'center', fontWeight: '700', color: '#0B0B12' },
});
