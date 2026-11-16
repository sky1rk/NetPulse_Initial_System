/** Join conditional class names without pulling in an extra dependency. */
export function cx(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}
