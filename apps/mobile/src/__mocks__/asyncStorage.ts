const _store: Record<string, string> = {};

const AsyncStorage = {
  getItem: jest.fn(async (key: string) => _store[key] ?? null),
  setItem: jest.fn(async (key: string, val: string) => { _store[key] = val; }),
  removeItem: jest.fn(async (key: string) => { delete _store[key]; }),
  clear: jest.fn(async () => { Object.keys(_store).forEach((k) => { delete _store[k]; }); }),
  _store,
};

export default AsyncStorage;
