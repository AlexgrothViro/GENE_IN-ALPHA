function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function deepMerge(base, patch) {
  const result = { ...base };
  Object.entries(patch).forEach(([key, value]) => {
    result[key] = isPlainObject(value) && isPlainObject(result[key])
      ? deepMerge(result[key], value)
      : value;
  });
  return result;
}

export function createStore(initial = {}) {
  let state = { ...initial };
  const subscribers = new Set();
  return {
    get: () => state,
    set(patch) {
      state = deepMerge(state, patch);
      subscribers.forEach((subscriber) => subscriber(state));
      return state;
    },
    subscribe(subscriber) {
      subscribers.add(subscriber);
      return () => subscribers.delete(subscriber);
    },
  };
}
