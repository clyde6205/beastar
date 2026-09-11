import React, { useState } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet, Alert, Image } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { postDreamUpdate } from '../api/client';
import type { RootStackParamList } from '../navigation/AppNavigator';

type Props = NativeStackScreenProps<RootStackParamList, 'PostDreamUpdate'>;

export default function PostDreamUpdateScreen({ route, navigation }: Props) {
  const { userId, threadId } = route.params;
  const [caption, setCaption] = useState('');
  const [videoUri, setVideoUri] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const pickVideo = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('Access needed', 'Enable media library access to attach an update video.');
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Videos,
      quality: 1,
    });
    if (!result.canceled && result.assets?.[0]) {
      setVideoUri(result.assets[0].uri);
    }
  };

  const handlePost = async () => {
    if (!caption.trim()) {
      Alert.alert('Say something', 'Give a quick update on where things stand.');
      return;
    }
    setSubmitting(true);
    try {
      // NOTE: this passes the local video URI straight through as
      // video_url, which only works if your backend/storage layer accepts
      // a local file reference — in production, upload the video file to
      // storage first (same pattern as uploadSelfie in api/client.ts) and
      // pass the resulting storage URL here instead. Left as the direct
      // pass-through for now since a dedicated "update video" storage
      // endpoint wasn't part of this build yet.
      await postDreamUpdate(threadId, userId, caption.trim(), videoUri ?? undefined);
      Alert.alert(
        'Update submitted',
        'Your update is pending a quick review before it appears to your followers.'
      );
      navigation.goBack();
    } catch (err: any) {
      Alert.alert('Couldn\'t post update', err?.response?.data?.detail ?? 'Try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Post an update</Text>
      <Text style={styles.subtitle}>
        What's changed since your last post? Even a small step counts.
      </Text>

      <TextInput
        style={[styles.input, styles.multiline]}
        placeholder="What's the update?"
        placeholderTextColor="#666"
        value={caption}
        onChangeText={setCaption}
        multiline
        maxLength={280}
      />

      <Pressable style={styles.videoPicker} onPress={pickVideo}>
        {videoUri ? (
          <Text style={styles.videoPickerText}>Video attached ✓</Text>
        ) : (
          <Text style={styles.videoPickerText}>Attach a short video (optional)</Text>
        )}
      </Pressable>

      <Pressable style={styles.button} onPress={handlePost} disabled={submitting}>
        <Text style={styles.buttonText}>{submitting ? 'Posting…' : 'Post update'}</Text>
      </Pressable>

      <Text style={styles.moderationNote}>
        Updates are briefly reviewed before appearing to your followers.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, paddingTop: 60, backgroundColor: '#0B0B12' },
  title: { fontSize: 20, fontWeight: '700', color: '#FFFFFF', marginBottom: 6 },
  subtitle: { color: '#A0A0B2', marginBottom: 20 },
  input: {
    backgroundColor: '#1B1B26', color: '#FFFFFF', borderRadius: 8,
    paddingHorizontal: 14, paddingVertical: 12, marginBottom: 14,
  },
  multiline: { minHeight: 100, textAlignVertical: 'top' },
  videoPicker: {
    borderColor: '#333', borderWidth: 1, borderStyle: 'dashed', borderRadius: 8,
    paddingVertical: 18, alignItems: 'center', marginBottom: 20,
  },
  videoPickerText: { color: '#888' },
  button: { backgroundColor: '#F5C542', borderRadius: 8, paddingVertical: 14 },
  buttonText: { textAlign: 'center', fontWeight: '700', color: '#0B0B12' },
  moderationNote: { color: '#555', fontSize: 12, textAlign: 'center', marginTop: 14 },
});
