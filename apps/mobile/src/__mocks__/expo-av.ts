export const Audio = {
  Sound: {
    createAsync: jest.fn(async () => ({
      sound: {
        playAsync: jest.fn(async () => undefined),
        stopAsync: jest.fn(async () => undefined),
        unloadAsync: jest.fn(async () => undefined),
        setOnPlaybackStatusUpdate: jest.fn(),
      },
    })),
  },
};
