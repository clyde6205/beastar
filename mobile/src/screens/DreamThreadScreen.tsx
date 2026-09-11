import React, { useCallback, useEffect, useState } from 'react';
import { View, Text, FlatList, Pressable, StyleSheet, ActivityIndicator, Alert } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import {
  getDreamThread,
  followDreamThread,
  unfollowDreamThread,
  addEncouragement,
  NET_WORTH_BAND_LABELS,
  type DreamThread,
  type DreamUpdate,
} from '../api/client';
import type { RootStackParamList } from '../navigation/AppNavigator';

type Props = NativeStackScreenProps<RootStackParamList, 'DreamThread'>;

export default function DreamThreadScreen({ route, navigation }: Props) {
  const { userId, threadId } = route.params;
  const [thread, setThread] = useState<DreamThread | null>(null);
  const [loading, setLoading] = useState(true);
  const [isFollowing, setIsFollowing] = useState(false); // real state comes from a
  // dedicated "am I following" check once that endpoint exists server-side;
  // left as local-only state for now since the backend follow/unfollow
  // endpoints don't yet return the caller's current follow status.

  const load = useCallback(() => {
    setLoading(true);
    getDreamThread(threadId)
      .then(setThread)
      .finally(() => setLoading(false));
  }, [threadId]);

  useFocusEffect(load);

  const isOwnThread = thread?.user_id === userId;

  const toggleFollow = async () => {
    try {
      if (isFollowing) {
        await unfollowDreamThread(threadId, userId);
      } else {
        await followDreamThread(threadId, userId);
      }
      setIsFollowing(!isFollowing);
    } catch (err: any) {
      Alert.alert('Error', err?.response?.data?.detail ?? 'Try again.');
    }
  };

  const handleEncourage = async (updateId: string) => {
    try {
      await addEncouragement(updateId, userId);
      load();
    } catch (err: any) {
      if (err?.response?.status === 409) return; // already encouraged, silently ignore
      Alert.alert('Error', err?.response?.data?.detail ?? 'Try again.');
    }
  };

  if (loading || !thread) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator color="#F5C542" />
      </View>
    );
  }

  const renderUpdate = ({ item }: { item: DreamUpdate }) => (
    <View style={styles.updateCard}>
      <Text style={styles.updateCaption}>{item.caption}</Text>
      <Text style={styles.updateDate}>{new Date(item.created_at).toLocaleDateString()}</Text>
      <Pressable style={styles.encourageButton} onPress={() => handleEncourage(item.id)}>
        <Text style={styles.encourageButtonText}>👏 Encourage</Text>
      </Pressable>
    </View>
  );

  return (
    <View style={styles.container}>
      <FlatList
        ListHeaderComponent={
          <View>
            <Text style={styles.goalTitle}>{thread.goal_title}</Text>
            {thread.goal_description ? (
              <Text style={styles.goalDescription}>{thread.goal_description}</Text>
            ) : null}

            {thread.self_reported_net_worth && thread.self_reported_net_worth !== 'prefer_not_to_say' && (
              <View style={styles.netWorthBadge}>
                <Text style={styles.netWorthBadgeText}>
                  {NET_WORTH_BAND_LABELS[thread.self_reported_net_worth]} · Self-reported
                </Text>
              </View>
            )}

            <Text style={styles.statsLine}>
              {thread.update_count ?? 0} updates · {thread.follower_count ?? 0} following this journey
            </Text>

            {!isOwnThread && (
              <Pressable style={styles.followButton} onPress={toggleFollow}>
                <Text style={styles.followButtonText}>{isFollowing ? 'Following' : 'Follow this journey'}</Text>
              </Pressable>
            )}

            {isOwnThread && (
              <Pressable
                style={styles.followButton}
                onPress={() => navigation.navigate('PostDreamUpdate', { userId, threadId })}
              >
                <Text style={styles.followButtonText}>Post an update</Text>
              </Pressable>
            )}

            <Text style={styles.timelineLabel}>Timeline</Text>
          </View>
        }
        data={thread.updates ?? []}
        keyExtractor={(item) => item.id}
        renderItem={renderUpdate}
        ListEmptyComponent={<Text style={styles.emptyText}>No updates yet.</Text>}
        contentContainerStyle={styles.listContent}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0B0B12' },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0B0B12' },
  listContent: { padding: 20, paddingTop: 60 },
  goalTitle: { fontSize: 22, fontWeight: '700', color: '#F5C542', marginBottom: 8 },
  goalDescription: { color: '#CCCCCC', marginBottom: 12, lineHeight: 20 },
  netWorthBadge: {
    alignSelf: 'flex-start', backgroundColor: '#2A2A1A', borderColor: '#F5C542',
    borderWidth: 1, borderRadius: 6, paddingHorizontal: 10, paddingVertical: 4, marginBottom: 12,
  },
  netWorthBadgeText: { color: '#F5C542', fontSize: 12, fontWeight: '600' },
  statsLine: { color: '#888', fontSize: 13, marginBottom: 16 },
  followButton: { backgroundColor: '#1B1B26', borderColor: '#F5C542', borderWidth: 1, borderRadius: 8, paddingVertical: 12, marginBottom: 24 },
  followButtonText: { textAlign: 'center', color: '#F5C542', fontWeight: '700' },
  timelineLabel: { color: '#A0A0B2', fontWeight: '600', marginBottom: 12 },
  updateCard: { backgroundColor: '#1B1B26', borderRadius: 10, padding: 14, marginBottom: 12 },
  updateCaption: { color: '#FFFFFF', marginBottom: 6, lineHeight: 20 },
  updateDate: { color: '#666', fontSize: 12, marginBottom: 10 },
  encourageButton: { alignSelf: 'flex-start' },
  encourageButtonText: { color: '#F5C542', fontWeight: '600' },
  emptyText: { color: '#666', textAlign: 'center', marginTop: 20 },
});
