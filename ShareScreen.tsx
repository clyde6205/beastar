import React from 'react';
import { View, Text, Image, Pressable, StyleSheet, Share } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { referralQrUrl } from '../api/client';
import type { RootStackParamList } from '../navigation/AppNavigator';

type Props = NativeStackScreenProps<RootStackParamList, 'Share'>;

export default function ShareScreen({ route, navigation }: Props) {
  const { userId, videoUrl, generationJobId } = route.params;

  const handleShare = async () => {
    try {
      await Share.share({
        message: 'I just became a star on BeAstar! 🌟 #StarMe',
        url: videoUrl, // iOS uses `url`; Android falls back to `message`
      });
    } catch {
      // User cancelled the share sheet — nothing to do.
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>You're a star! 🌟</Text>

      {/* A real video player (expo-av) replaces this in production — kept
          as an Image placeholder here since wiring video playback isn't
          this screen's point; the share/QR loop is. */}
      <View style={styles.videoPlaceholder}>
        <Text style={styles.videoPlaceholderText}>Video preview</Text>
      </View>

      <Pressable style={styles.button} onPress={handleShare}>
        <Text style={styles.buttonText}>Share to TikTok, IG & more</Text>
      </Pressable>

      {/* The fantasy video is fun for a moment — this is what gives someone
          a reason to open the app again next week: pairing the fantasy
          with their real goal. */}
      <Pressable
        style={styles.dreamButton}
        onPress={() => navigation.navigate('CreateDreamThread', { userId, generationJobId })}
      >
        <Text style={styles.dreamButtonTitle}>What's your real big dream?</Text>
        <Text style={styles.dreamButtonSubtitle}>Start a thread and track your real progress toward it</Text>
      </Pressable>

      <Text style={styles.qrLabel}>Or share your star profile via QR code:</Text>
      <Image source={{ uri: referralQrUrl(userId) }} style={styles.qrImage} />

      <Text style={styles.disclosure}>AI-Generated · For Entertainment Purposes Only</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, alignItems: 'center', backgroundColor: '#0B0B12', paddingTop: 60 },
  title: { fontSize: 24, fontWeight: '700', color: '#F5C542', marginBottom: 20 },
  videoPlaceholder: {
    width: '100%', height: 320, borderRadius: 12, backgroundColor: '#1B1B26',
    justifyContent: 'center', alignItems: 'center', marginBottom: 24,
  },
  videoPlaceholderText: { color: '#666' },
  button: { backgroundColor: '#F5C542', borderRadius: 8, paddingVertical: 14, paddingHorizontal: 32, marginBottom: 16 },
  buttonText: { fontWeight: '700', color: '#0B0B12' },
  dreamButton: {
    width: '100%', backgroundColor: '#1B1B26', borderColor: '#F5C542', borderWidth: 1,
    borderRadius: 10, padding: 16, marginBottom: 24,
  },
  dreamButtonTitle: { color: '#F5C542', fontWeight: '700', fontSize: 15, marginBottom: 4, textAlign: 'center' },
  dreamButtonSubtitle: { color: '#A0A0B2', fontSize: 12, textAlign: 'center' },
  qrLabel: { color: '#A0A0B2', marginBottom: 12 },
  qrImage: { width: 180, height: 180, backgroundColor: '#fff', borderRadius: 8 },
  disclosure: { color: '#555', fontSize: 12, marginTop: 24 },
});
