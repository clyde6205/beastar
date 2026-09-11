import React, { useState } from 'react';
import { View, Text, Image, Pressable, StyleSheet, Alert, ActivityIndicator } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import * as FileSystem from 'expo-file-system';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { verifyFace, uploadSelfie } from '../api/client';
import { useAuth } from '../context/AuthContext';
import type { RootStackParamList } from '../navigation/AppNavigator';

type Props = NativeStackScreenProps<RootStackParamList, 'VerifyFace'>;

/**
 * Face Verification Screen
 * 
 * This screen:
 * 1. Captures a selfie using the device camera
 * 2. Uploads it to the server for real face verification
 * 3. Server performs liveness detection, face matching, and known-public-figure check
 * 4. On success, user is marked as verified and can proceed to video generation
 */
export default function VerifyFaceScreen({ route, navigation }: Props) {
  const { userId } = route.params;
  const { setVerified } = useAuth();
  const [selfieUri, setSelfieUri] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

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
      base64: true,  // Get base64 for potential direct upload
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
    setUploading(true);
    setUploadProgress(0);
    
    try {
      // Step 1: Upload selfie to server for storage and safety check
      // This is CRITICAL: the server must receive the actual image for:
      // - Content safety check (moderation)
      // - Liveness detection
      // - Face matching
      // - Known public figure check
      
      const uploadResult = await uploadSelfie(userId, selfieUri, 
        (progress) => setUploadProgress(progress)
      );
      
      setUploading(false);
      
      // Step 2: Call face verification endpoint with the uploaded image URL
      // The server will perform the actual verification
      const verifyResult = await verifyFace(userId, uploadResult.image_url);
      
      if (verifyResult.is_verified) {
        setVerified(true);
        // Proceed to video creation
        navigation.replace('Create', { userId });
      } else {
        Alert.alert(
          'Verification failed',
          verifyResult.message || 'Face verification failed. Please try again with a clearer selfie.'
        );
      }
      
    } catch (err: any) {
      setUploading(false);
      const detail = err?.response?.data?.detail ?? 
        err?.message ?? 
        'Verification failed. Please try again.';
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

      {uploading ? (
        <View style={styles.progressContainer}>
          <ActivityIndicator size="large" color="#F5C542" />
          <Text style={styles.progressText}>Uploading: {uploadProgress}%</Text>
        </View>
      ) : selfieUri ? (
        <Image source={{ uri: selfieUri }} style={styles.preview} />
      ) : (
        <View style={styles.previewPlaceholder}>
          <Text style={styles.placeholderText}>No selfie yet</Text>
        </View>
      )}

      <Pressable 
        style={styles.secondaryButton} 
        onPress={captureSelfie}
        disabled={submitting || uploading}
      >
        <Text style={styles.secondaryButtonText}>
          {selfieUri ? 'Retake selfie' : 'Take selfie'}
        </Text>
      </Pressable>

      <Pressable 
        style={styles.button} 
        onPress={handleVerify} 
        disabled={submitting || uploading || !selfieUri}
      >
        <Text style={styles.buttonText}>
          {submitting ? (uploading ? 'Uploading...' : 'Verifying...') : 'Verify & continue'}
        </Text>
      </Pressable>

      <Text style={styles.note}>
        Note: We use advanced AI to verify this is a real, live photo of you.
        This helps keep BeAstar safe and prevents misuse.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { 
    flex: 1, 
    padding: 24, 
    justifyContent: 'center', 
    backgroundColor: '#0B0B12' 
  },
  title: { 
    fontSize: 22, 
    fontWeight: '700', 
    color: '#FFFFFF', 
    marginBottom: 8, 
    textAlign: 'center' 
  },
  subtitle: { 
    color: '#A0A0B2', 
    textAlign: 'center', 
    marginBottom: 24 
  },
  preview: { 
    width: 220, 
    height: 220, 
    borderRadius: 110, 
    alignSelf: 'center', 
    marginBottom: 24 
  },
  previewPlaceholder: {
    width: 220, 
    height: 220, 
    borderRadius: 110, 
    alignSelf: 'center', 
    marginBottom: 24,
    backgroundColor: '#1B1B26', 
    justifyContent: 'center', 
    alignItems: 'center',
  },
  placeholderText: { color: '#666' },
  progressContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
  },
  progressText: {
    color: '#A0A0B2',
    marginTop: 10,
  },
  secondaryButton: { 
    borderColor: '#F5C542', 
    borderWidth: 1, 
    borderRadius: 8, 
    paddingVertical: 12, 
    marginBottom: 12 
  },
  secondaryButtonText: { 
    textAlign: 'center', 
    color: '#F5C542', 
    fontWeight: '600' 
  },
  button: { 
    backgroundColor: '#F5C542', 
    borderRadius: 8, 
    paddingVertical: 14 
  },
  buttonText: { 
    textAlign: 'center', 
    fontWeight: '700', 
    color: '#0B0B12' 
  },
  note: {
    color: '#666',
    fontSize: 12,
    textAlign: 'center',
    marginTop: 24,
    paddingHorizontal: 20,
  },
});
