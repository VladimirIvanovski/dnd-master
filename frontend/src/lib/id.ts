let counter = 0;

export function uid(prefix = "id") {
  counter += 1;
  return `${prefix}-${Date.now()}-${counter}`;
}
