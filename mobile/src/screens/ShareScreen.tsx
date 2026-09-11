import React, { useState, useRef, useEffect } from 'react';
import { View, Text, Image, Pressable, StyleSheet, Share, ActivityIndicator } from 'react-native';
import { Video, AVPlaybackStatus, VideoRef } from 'expo-av';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { referralQrUrl } from '../api/client';
import type { RootStackParamList } from '../navigation/AppNavigator';

type Props = NativeStackScreenProps<RootStackParamList, 'Share'>;

export default function ShareScreen({ route, navigation }: Props) {
  const { userId, videoUrl, generationJobId } = route.params;
  const videoRef = useRef<VideoRef>(null);
  const [videoStatus, setVideoStatus] = useState<AVPlaybackStatus | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Handle video status updates
  const handleVideoStatusUpdate = (status: AVPlaybackStatus) => {
    setVideoStatus(status);
    setIsLoading(status.isLoading);
    
    if (status.error) {
      setError(status.error.message);
      setIsPlaying(false);
    } else if (status.isPlaying) {
      setIsPlaying(true);
      setError(null);
    } else if (status.didJustFinish) {
      setIsPlaying(false);
    }
  };

  // Toggle play/pause
  const togglePlayPause = async () => {
    if (!videoRef.current) return;
    
    if (isPlaying) {
      await videoRef.current.pauseAsync();
      setIsPlaying(false);
    } else {
      await videoRef.current.playAsync();
      setIsPlaying(true);
    }
  };

  // Replay video
  const replayVideo = async () => {
    if (!videoRef.current) return;
    
    await videoRef.current.replayAsync();
    setIsPlaying(true);
  };

  // Handle share
  const handleShare = async () => {
    try {
      await Share.share({
        message: 'I just became a star on BeAstar! \ud83c\udf1f #StarMe',
        url: videoUrl, // iOS uses `url`; Android falls back to `message`
      });
    } catch {
      // User cancelled the share sheet — nothing to do.
    }
  };

  // Auto-play when video is ready
  useEffect(() => {
    if (videoRef.current && !isLoading && !isPlaying && !error) {
      videoRef.current.playAsync().catch(() => {});
      setIsPlaying(true);
    }
  }, [isLoading, isPlaying, error]);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>You're a star! \ud83c\udf1f</Text>

      {/* Real video player with expo-av */}
      <View style={styles.videoContainer}>
        {error ? (
          <View style={[styles.videoPlaceholder, { justifyContent: 'center', alignItems: 'center' }]}>
            <Text style={styles.errorText}>Error: {error}</Text>
            <Pressable style={styles.retryButton} onPress={replayVideo}>
              <Text style={styles.retryButtonText}>Retry</Text>
            </Pressable>
          </View>
        ) : isLoading ? (
          <View style={[styles.videoPlaceholder, { justifyContent: 'center', alignItems: 'center' }]}>
            <ActivityIndicator size="large" color="#F5C542" />
            <Text style={styles.loadingText}>Loading video...</Text>
          </View>
        ) : (
          <>
            <Video
              ref={videoRef}
              source={{ uri: videoUrl }}
              rate={1.0}
              volume={1.0}
              isMuted={false}
              resizeMode="contain"
              shouldPlay={isPlaying}
              isLooping={false}
              useNativeControls={false}
              style={styles.video}
              onPlaybackStatusUpdate={handleVideoStatusUpdate}
              onLoadStart={() => setIsLoading(true)}
              onLoad={() => setIsLoading(false)}
              onError={(e) => setError(e.error.message)}
            />
            
            {/* Video controls overlay */}
            <View style={styles.videoControls}>
              {videoStatus?.didJustFinish && (
                <Pressable style={styles.replayButton} onPress={replayVideo}>
                  <Text style={styles.replayButtonText}>↻ Replay</Text>
                </Pressable>
              )}
              
              {!isPlaying && !videoStatus?.didJustFinish && !isLoading && (
                <Pressable style={styles.playButton} onPress={togglePlayPause}>
                  <Text style={styles.playButtonText}>▶ Play</Text>
                </Pressable>
              )}
              
              {isPlaying && !videoStatus?.didJustFinish && (
                <Pressable style={styles.pauseButton} onPress={togglePlayPause}>
                  <Text style={styles.pauseButtonText}>⏸ Pause</Text>
                </Pressable>
              )}
            </View>
          </>
        )}
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

      <Text style={styles.disclosure}>AI-Generated • For Entertainment Purposes Only</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, alignItems: 'center', backgroundColor: '#0B0B12', paddingTop: 60 },
  title: { fontSize: 24, fontWeight: '700', color: '#F5C542', marginBottom: 20 },
  videoContainer: {
    width: '100%',
    height: 320,
    borderRadius: 12,
    backgroundColor: '#1B1B26',
    marginBottom: 24,
    overflow: 'hidden',
    justifyContent: 'center',
    alignItems: 'center',
  },
  video: {
    width: '100%',
    height: '100%',
  },
  videoPlaceholder: {
    width: '100%',
    height: '100%',
  },
  videoControls: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
  },
  playButton: {
    backgroundColor: 'rgba(245, 197, 66, 0.9)',
    borderRadius: 50,
    padding: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  playButtonText: {
    color: '#0B0B12',
    fontWeight: 'bold',
  },
  pauseButton: {
    backgroundColor: 'rgba(245, 197, 66, 0.9)',
    borderRadius: 50,
    padding: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  pauseButtonText: {
    color: '#0B0B12',
    fontWeight: 'bold',
  },
  replayButton: {
    backgroundColor: 'rgba(245, 197, 66, 0.9)',
    borderRadius: 8,
    padding: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  replayButtonText: {
    color: '#0B0B12',
    fontWeight: 'bold',
  },
  retryButton: {
    backgroundColor: '#F5C542',
    borderRadius: 8,
    padding: 10,
    marginTop: 10,
  },
  retryButtonText: {
    color: '#0B0B12',
    fontWeight: 'bold',
  },
  loadingText: {
    color: '#A0A0B2',
    marginTop: 10,
  },
  errorText: {
    color: '#FF6B6B',
    textAlign: 'center',
    marginBottom: 10,
  },
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
