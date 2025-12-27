"use client";

import { useField } from "formik";

/**
 * Custom hook for handling form input changes in Formik forms.
 *
 * This hook automatically sets the field as "touched" when its value changes,
 * enabling immediate validation feedback after the first user interaction.
 *
 * @example
 * ```tsx
 * function MyField({ name }: { name: string }) {
 *   const [field] = useField(name);
 *   const onChange = useFormInputCallback(name);
 *
 *   return (
 *     <input
 *       name={name}
 *       value={field.value}
 *       onChange={onChange}
 *     />
 *   );
 * }
 * ```
 *
 * @example
 * ```tsx
 * // With callback
 * function MySelect({ name, onValueChange }: Props) {
 *   const [field] = useField(name);
 *   const onChange = useFormInputCallback(name, onValueChange);
 *
 *   return (
 *     <Select value={field.value} onValueChange={onChange} />
 *   );
 * }
 * ```
 */
export function useFormInputCallback<T = any>(
  name: string,
  f?: (event: T) => void
) {
  const [, , helpers] = useField<T>(name);
  return (eventOrValue: T | React.ChangeEvent<HTMLInputElement>) => {
    helpers.setTouched(true);
    f?.(eventOrValue as T);
    // Handle both DOM events and direct values (e.g., from Switch components)
    if (
      eventOrValue &&
      typeof eventOrValue === "object" &&
      "target" in eventOrValue
    ) {
      // DOM event - extract value from target
      const target = eventOrValue.target as HTMLInputElement;
      helpers.setValue(
        target.type === "checkbox" ? (target.checked as T) : (target.value as T)
      );
    } else {
      // Direct value (boolean, string, etc.)
      helpers.setValue(eventOrValue as T);
    }
  };
}
