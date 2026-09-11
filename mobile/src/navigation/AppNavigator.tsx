import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import { useAuth } from '../context/AuthContext';
import SignupScreen from '../screens/SignupScreen';
import VerifyFaceScreen from '../screens/VerifyFaceScreen';
import CreateScreen from '../screens/CreateScreen';
import GenerationStatusScreen from '../screens/GenerationStatusScreen';
import ShareScreen from '../screens/ShareScreen';
import LeaderboardScreen from '../screens/LeaderboardScreen';
import CreateDreamThreadScreen from '../screens/CreateDreamThreadScreen';
import DreamThreadScreen from '../screens/DreamThreadScreen';
import PostDreamUpdateScreen from '../screens/PostDreamUpdateScreen';
import DreamFeedScreen from '../screens/DreamFeedScreen';

export type RootStackParamList = {
  Signup: undefined;
  VerifyFace: { userId: string };
  Create: { userId: string };
  GenerationStatus: { userId: string; jobId: string };
  Share: { userId: string; videoUrl: string; generationJobId?: string };
  Leaderboard: undefined;
  CreateDreamThread: { userId: string; generationJobId?: string };
  DreamThread: { userId: string; threadId: string };
  PostDreamUpdate: { userId: string; threadId: string };
  DreamFeed: { userId: string };
};

const Stack = createNativeStackNavigator<RootStackParamList>();

const screenOptions = {
  headerStyle: { backgroundColor: '#0B0B12' },
  headerTintColor: '#F5C542',
  headerTitleStyle: { fontWeight: '700' as const },
};

export default function AppNavigator() {
  const { userId, isLoading } = useAuth();

  if (isLoading) {
    // A splash screen component replaces this in production — kept minimal
    // here since the loading-state UI isn't the point of this scaffold.
    return null;
  }

  return (
    <NavigationContainer>
      <Stack.Navigator
        initialRouteName={userId ? 'Create' : 'Signup'}
        screenOptions={screenOptions}
      >
        <Stack.Screen name="Signup" component={SignupScreen} options={{ title: 'Join BeAstar' }} />
        <Stack.Screen
          name="VerifyFace"
          component={VerifyFaceScreen}
          initialParams={userId ? { userId } : undefined}
          options={{ title: 'Verify' }}
        />
        <Stack.Screen
          name="Create"
          component={CreateScreen}
          initialParams={userId ? { userId } : undefined}
          options={{ title: 'Create' }}
        />
        <Stack.Screen name="GenerationStatus" component={GenerationStatusScreen} options={{ title: 'Rendering' }} />
        <Stack.Screen name="Share" component={ShareScreen} options={{ title: 'Share' }} />
        <Stack.Screen name="Leaderboard" component={LeaderboardScreen} options={{ title: 'Leaderboard' }} />
        <Stack.Screen name="CreateDreamThread" component={CreateDreamThreadScreen} options={{ title: 'Your Big Dream' }} />
        <Stack.Screen name="DreamThread" component={DreamThreadScreen} options={{ title: 'Dream Thread' }} />
        <Stack.Screen name="PostDreamUpdate" component={PostDreamUpdateScreen} options={{ title: 'Post Update' }} />
        <Stack.Screen name="DreamFeed" component={DreamFeedScreen} options={{ title: 'Dream Feed' }} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}
