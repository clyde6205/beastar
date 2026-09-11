import React, { useEffect, useState } from 'react';
import { View, Text, FlatList, StyleSheet, ActivityIndicator } from 'react-native';

import { getLeaderboard, type LeaderboardEntry } from '../api/client';

export default function LeaderboardScreen() {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getLeaderboard()
      .then(setEntries)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator color="#F5C542" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Global Leaderboard</Text>
      <FlatList
        data={entries}
        keyExtractor={(item) => item.user_id}
        renderItem={({ item, index }) => (
          <View style={styles.row}>
            <Text style={styles.rank}>#{index + 1}</Text>
            <View style={styles.rowMain}>
              <Text style={styles.name}>{item.display_name}</Text>
              <Text style={styles.meta}>
                {item.country_code} · {item.videos_created} videos · {item.successful_referrals} referrals
              </Text>
            </View>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0B0B12', paddingTop: 60, paddingHorizontal: 20 },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0B0B12' },
  title: { fontSize: 22, fontWeight: '700', color: '#FFFFFF', marginBottom: 16 },
  row: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, borderBottomColor: '#1B1B26', borderBottomWidth: 1 },
  rank: { width: 40, color: '#F5C542', fontWeight: '700' },
  rowMain: { flex: 1 },
  name: { color: '#FFFFFF', fontWeight: '600' },
  meta: { color: '#888', fontSize: 12, marginTop: 2 },
});
