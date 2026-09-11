import React, { useState } from 'react';
import { View, Text, Image, Pressable, StyleSheet, FlatList, Alert } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { uploadSelfie, requestGeneration, type Resolution } from '../api/client';
import type { RootStackParamList } from '../navigation/AppNavigator';

type Props = NativeStackScreenProps<RootStackParamList, 'Create'>;

// Generic, non-IP scenario names — matches the `scenarios` table content
// rule from schema.sql/COMPLIANCE.md: no real celebrities, franchises, or
// branded venues.
const SCENARIOS = [
  { slug: 'red-carpet-arrival', name: 'Red Carpet Arrival' },
  { slug: 'award-stage-moment', name: 'Award Stage Moment' },
  { slug: 'sold-out-concert', name: 'Sold-Out Concert Headliner' },
  { slug: 'magazine-cover', name: 'Magazine Cover Shoot' },
  { slug: 'blockbuster-premiere', name: 'Blockbuster Premiere Walk' },
  { slug: 'talk-show-guest', name: 'Late Night Talk Show Guest' },
  { slug: 'fashion-runway', name: 'Fashion Runway' },
  { slug: 'championship-entrance', name: 'Championship Entrance' },
];

const RESOLUTIONS: Resolution[] = ['720p', '1080p', '4k'];

export default function CreateScreen({ route, navigation }: Props) {
  const { userId } = route.params;
  const [selectedScenario, setSelectedScenario] = useState(SCENARIOS[0].slug);
  const [selectedResolution, setSelectedResolution] = useState<Resolution>('720p');
  const [photoUri, setPhotoUri] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const pickPhoto = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('Photo access needed', 'Enable photo library access to pick a source image.');
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({ quality: 0.9 });
    if (!result.canceled && result.assets?.[0]) {
      setPhotoUri(result.assets[0].uri);
    }
  };

  const handleGenerate = async () => {
    if (!photoUri) {
      Alert.alert('Choose a photo', 'Pick the photo you want to become the star in.');
      return;
    }
    setSubmitting(true);
    try {
      const { image_url } = await uploadSelfie(userId, photoUri, 'image/jpeg');
      const job = await requestGeneration({
        user_id: userId,
        scenario_slug: selectedScenario,
        requested_resolution: selectedResolution,
        image_url,
      });
      navigation.navigate('GenerationStatus', { userId, jobId: job.job_id });
    } catch (err: any) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail ?? 'Generation request failed.';
      if (status === 403) {
        Alert.alert('Upgrade needed', detail);
      } else if (status === 429) {
        Alert.alert('Daily limit reached', detail);
      } else {
        Alert.alert('Error', detail);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Create your star moment</Text>

      <Pressable style={styles.photoPicker} onPress={pickPhoto}>
        {photoUri ? (
          <Image source={{ uri: photoUri }} style={styles.photoPreview} />
        ) : (
          <Text style={styles.photoPickerText}>Tap to choose a photo</Text>
        )}
      </Pressable>

      <Text style={styles.sectionLabel}>Scenario</Text>
      <FlatList
        horizontal
        data={SCENARIOS}
        keyExtractor={(item) => item.slug}
        showsHorizontalScrollIndicator={false}
        renderItem={({ item }) => (
          <Pressable
            style={[styles.chip, selectedScenario === item.slug && styles.chipSelected]}
            onPress={() => setSelectedScenario(item.slug)}
          >
            <Text style={[styles.chipText, selectedScenario === item.slug && styles.chipTextSelected]}>
              {item.name}
            </Text>
          </Pressable>
        )}
      />

      <Text style={styles.sectionLabel}>Resolution</Text>
      <View style={styles.resolutionRow}>
        {RESOLUTIONS.map((res) => (
          <Pressable
            key={res}
            style={[styles.chip, selectedResolution === res && styles.chipSelected]}
            onPress={() => setSelectedResolution(res)}
          >
            <Text style={[styles.chipText, selectedResolution === res && styles.chipTextSelected]}>
              {res}
            </Text>
          </Pressable>
        ))}
      </View>

      <Pressable style={styles.button} onPress={handleGenerate} disabled={submitting}>
        <Text style={styles.buttonText}>{submitting ? 'Starting…' : 'Generate my star moment'}</Text>
      </Pressable>

      <Text style={styles.disclosure}>AI-Generated · For Entertainment Purposes Only</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, backgroundColor: '#0B0B12' },
  title: { fontSize: 20, fontWeight: '700', color: '#FFFFFF', marginBottom: 16, marginTop: 40 },
  photoPicker: {
    height: 220, borderRadius: 12, backgroundColor: '#1B1B26',
    justifyContent: 'center', alignItems: 'center', marginBottom: 20, overflow: 'hidden',
  },
  photoPreview: { width: '100%', height: '100%' },
  photoPickerText: { color: '#888' },
  sectionLabel: { color: '#A0A0B2', fontWeight: '600', marginBottom: 8, marginTop: 8 },
  chip: {
    borderColor: '#333', borderWidth: 1, borderRadius: 20,
    paddingHorizontal: 14, paddingVertical: 8, marginRight: 8,
  },
  chipSelected: { backgroundColor: '#F5C542', borderColor: '#F5C542' },
  chipText: { color: '#CCCCCC' },
  chipTextSelected: { color: '#0B0B12', fontWeight: '700' },
  resolutionRow: { flexDirection: 'row', marginBottom: 20 },
  button: { backgroundColor: '#F5C542', borderRadius: 8, paddingVertical: 14, marginTop: 20 },
  buttonText: { textAlign: 'center', fontWeight: '700', color: '#0B0B12' },
  disclosure: { color: '#555', fontSize: 12, textAlign: 'center', marginTop: 12 },
});
