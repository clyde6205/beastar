import React, { useCallback, useState } from 'react';
import { View, Text, FlatList, Pressable, StyleSheet, ActivityIndicator } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { getFollowedDreamFeed, getUserDreamThreads, type DreamUpdate, type DreamThread } from '../api/client';
import type { RootStackParamList } from '../navigation/AppNavigator';

type Props = NativeStackScreenProps<RootStackParamList, 'DreamFeed'>;

export default function DreamFeedScreen({ route, navigation }: Props) {
  const { userId } = route.params;
  const [feed, setFeed] = useState<DreamUpdate[]>([]);
  const [myThreads, setMyThreads] = useState<DreamThread[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([getFollowedDreamFeed(userId), getUserDreamThreads(userId)])
      .then(([followedFeed, threads]) => {
        setFeed(followedFeed);
        setMyThreads(threads);
      })
      .finally(() => setLoading(false));
  }, [userId]);

  useFocusEffect(load);

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator color="#F5C542" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        ListHeaderComponent={
          <View>
            <Text style={styles.sectionTitle}>Your dream threads</Text>
            {myThreads.length === 0 ? (
              <Pressable
                style={styles.startThreadButton}
                onPress={() => navigation.navigate('CreateDreamThread', { userId })}
              >
                <Text style={styles.startThreadButtonText}>+ Start your dream thread</Text>
              </Pressable>
            ) : (
              <FlatList
                horizontal
                data={myThreads}
                keyExtractor={(t) => t.id}
                showsHorizontalScrollIndicator={false}
                renderItem={({ item }) => (
                  <Pressable
                    style={styles.myThreadChip}
                    onPress={() => navigation.navigate('DreamThread', { userId, threadId: item.id })}
                  >
                    <Text style={styles.myThreadChipText}>{item.goal_title}</Text>
                  </Pressable>
                )}
              />
            )}

            <Text style={[styles.sectionTitle, { marginTop: 24 }]}>Threads you follow</Text>
          </View>
        }
        data={feed}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <Pressable
            style={styles.feedCard}
            onPress={() => navigation.navigate('DreamThread', { userId, threadId: item.thread_id })}
          >
            <Text style={styles.feedCaption}>{item.caption}</Text>
            <Text style={styles.feedDate}>{new Date(item.created_at).toLocaleDateString()}</Text>
          </Pressable>
        )}
        ListEmptyComponent={
          <Text style={styles.emptyText}>
            Follow someone's dream thread to see their updates here.
          </Text>
        }
        contentContainerStyle={styles.listContent}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0B0B12' },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0B0B12' },
  listContent: { padding: 20, paddingTop: 60 },
  sectionTitle: { color: '#FFFFFF', fontWeight: '700', fontSize: 16, marginBottom: 12 },
  startThreadButton: { backgroundColor: '#1B1B26', borderColor: '#F5C542', borderWidth: 1, borderRadius: 8, paddingVertical: 12, marginBottom: 8 },
  startThreadButtonText: { textAlign: 'center', color: '#F5C542', fontWeight: '700' },
  myThreadChip: { backgroundColor: '#1B1B26', borderRadius: 20, paddingHorizontal: 14, paddingVertical: 8, marginRight: 8 },
  myThreadChipText: { color: '#F5C542', fontSize: 13 },
  feedCard: { backgroundColor: '#1B1B26', borderRadius: 10, padding: 14, marginBottom: 12 },
  feedCaption: { color: '#FFFFFF', marginBottom: 6, lineHeight: 20 },
  feedDate: { color: '#666', fontSize: 12 },
  emptyText: { color: '#666', textAlign: 'center', marginTop: 20, lineHeight: 20 },
});
