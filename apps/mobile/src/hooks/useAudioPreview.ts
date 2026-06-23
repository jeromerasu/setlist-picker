import { useCallback, useRef, useState } from "react";
import { Audio } from "expo-av";

interface UseAudioPreviewResult {
  isPlaying: boolean;
  play: (url: string) => Promise<void>;
  stop: () => Promise<void>;
}

export function useAudioPreview(): UseAudioPreviewResult {
  const [isPlaying, setIsPlaying] = useState(false);
  const soundRef = useRef<Audio.Sound | null>(null);

  const stop = useCallback(async () => {
    if (soundRef.current != null) {
      await soundRef.current.stopAsync();
      await soundRef.current.unloadAsync();
      soundRef.current = null;
    }
    setIsPlaying(false);
  }, []);

  const play = useCallback(
    async (url: string) => {
      await stop();
      const { sound } = await Audio.Sound.createAsync({ uri: url });
      soundRef.current = sound;
      setIsPlaying(true);
      await sound.playAsync();
      sound.setOnPlaybackStatusUpdate((status: Audio.PlaybackStatus) => {
        if (status.isLoaded && status.didJustFinish === true) {
          setIsPlaying(false);
        }
      });
    },
    [stop]
  );

  return { isPlaying, play, stop };
}
