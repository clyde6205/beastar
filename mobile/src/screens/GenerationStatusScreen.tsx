import React, { useEffect, useState } from 'react';
import { View, Text, ActivityIndicator, StyleSheet, Alert } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { pollJobUntilDone } from '../api/client';
import type { RootStackParamList } from '../navigation/AppNavigator';

type Props = NativeStackScreenProps<RootStackParamList, 'GenerationStatus'>;

export default function GenerationStatusScreen({ route, navigation }: Props) {
  const { userId, jobId } = route.params;
  const [statusText, setStatusText] = useState('Your star moment is being created…');

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const job = await pollJobUntilDone(jobId);
        if (cancelled) return;

        if (job.status === 'complete' && job.output_url) {
          navigation.replace('Share', { userId, videoUrl: job.output_url });
        } else {
          setStatusText('This one didn\'t render — try a different photo or scenario.');
        }
      } catch {
        if (!cancelled) {
          setStatusText('Taking longer than usual — check back in your library shortly.');
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [jobId]);

  return (
    <View style={styles.container}>
      <ActivityIndicator size="large" color="#F5C542" />
      <Text style={styles.statusText}>{statusText}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0B0B12', padding: 24 },
  statusText: { color: '#CCCCCC', marginTop: 20, textAlign: 'center' },
});
