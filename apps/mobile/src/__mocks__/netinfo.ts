const listeners: Array<(state: { isConnected: boolean; isInternetReachable: boolean }) => void> = [];

const NetInfo = {
  addEventListener: jest.fn(
    (cb: (state: { isConnected: boolean; isInternetReachable: boolean }) => void) => {
      listeners.push(cb);
      return () => { const i = listeners.indexOf(cb); if (i !== -1) listeners.splice(i, 1); };
    },
  ),
  fetch: jest.fn(async () => ({ isConnected: true, isInternetReachable: true })),
  _emit: (state: { isConnected: boolean; isInternetReachable: boolean }) => {
    listeners.forEach((cb) => cb(state));
  },
};

export const useNetInfo = jest.fn(() => ({ isConnected: true, isInternetReachable: true }));

export default NetInfo;
