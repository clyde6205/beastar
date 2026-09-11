import React, { useState } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet, Alert, ScrollView } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { createDreamThread, NET_WORTH_BAND_LABELS } from '../api/client';
import type { RootStackParamList } from '../navigation/AppNavigator';

type Props = NativeStackScreenProps<RootStackParamList, 'CreateDreamThread'>;

const NET_WORTH_OPTIONS = Object.keys(NET_WORTH_BAND_LABELS);

export default function CreateDreamThreadScreen({ route, navigation }: Props) {
  const { userId, generationJobId } = route.params;
  const [goalTitle, setGoalTitle] = useState('');
  const [goalDescription, setGoalDescription] = useState('');
  const [netWorthBand, setNetWorthBand] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleCreate = async () => {
    if (!goalTitle.trim()) {
      Alert.alert('Give it a title', 'e.g. "Start my own clothing brand" or "Buy my first property".');
      return;
    }
    setSubmitting(true);
    try {
      const thread = await createDreamThread({
        user_id: userId,
        goal_title: goalTitle.trim(),
        goal_description: goalDescription.trim() || undefined,
        starting_generation_job_id: generationJobId,
        self_reported_net_worth: netWorthBand ?? undefined,
      });
      navigation.replace('DreamThread', { userId, threadId: thread.id });
    } catch (err: any) {
      Alert.alert('Couldn\'t create thread', err?.response?.data?.detail ?? 'Try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>What's your big dream?</Text>
      <Text style={styles.subtitle}>
        This starts a thread you can post real updates to as you work toward it — not just
        today's video, but your actual progress over time.
      </Text>

      <TextInput
        style={styles.input}
        placeholder="Your goal (e.g. 'Launch my own business')"
        placeholderTextColor="#666"
        value={goalTitle}
        onChangeText={setGoalTitle}
        maxLength={100}
      />
      <TextInput
        style={[styles.input, styles.multiline]}
        placeholder="Say a bit more about your plan (optional)"
        placeholderTextColor="#666"
        value={goalDescription}
        onChangeText={setGoalDescription}
        multiline
        maxLength={500}
      />

      <Text style={styles.sectionLabel}>
        Already there? Share your net worth range (optional, shown as self-reported)
      </Text>
      <View style={styles.bandRow}>
        {NET_WORTH_OPTIONS.map((band) => (
          <Pressable
            key={band}
            style={[styles.chip, netWorthBand === band && styles.chipSelected]}
            onPress={() => setNetWorthBand(netWorthBand === band ? null : band)}
          >
            <Text style={[styles.chipText, netWorthBand === band && styles.chipTextSelected]}>
              {NET_WORTH_BAND_LABELS[band]}
            </Text>
          </Pressable>
        ))}
      </View>
      {netWorthBand && netWorthBand !== 'prefer_not_to_say' && (
        <Text style={styles.disclosureNote}>
          This will show as "Self-reported" — BeAstar doesn't verify net worth claims.
        </Text>
      )}

      <Pressable style={styles.button} onPress={handleCreate} disabled={submitting}>
        <Text style={styles.buttonText}>{submitting ? 'Starting…' : 'Start my dream thread'}</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 20, paddingTop: 60, backgroundColor: '#0B0B12', flexGrow: 1 },
  title: { fontSize: 22, fontWeight: '700', color: '#F5C542', marginBottom: 8 },
  subtitle: { color: '#A0A0B2', marginBottom: 24, lineHeight: 20 },
  input: {
    backgroundColor: '#1B1B26', color: '#FFFFFF', borderRadius: 8,
    paddingHorizontal: 14, paddingVertical: 12, marginBottom: 12,
  },
  multiline: { minHeight: 90, textAlignVertical: 'top' },
  sectionLabel: { color: '#A0A0B2', marginTop: 12, marginBottom: 10, lineHeight: 18 },
  bandRow: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: 8 },
  chip: {
    borderColor: '#333', borderWidth: 1, borderRadius: 20,
    paddingHorizontal: 12, paddingVertical: 8, marginRight: 8, marginBottom: 8,
  },
  chipSelected: { backgroundColor: '#F5C542', borderColor: '#F5C542' },
  chipText: { color: '#CCCCCC', fontSize: 13 },
  chipTextSelected: { color: '#0B0B12', fontWeight: '700' },
  disclosureNote: { color: '#666', fontSize: 12, marginBottom: 12 },
  button: { backgroundColor: '#F5C542', borderRadius: 8, paddingVertical: 14, marginTop: 20 },
  buttonText: { textAlign: 'center', fontWeight: '700', color: '#0B0B12' },
});
