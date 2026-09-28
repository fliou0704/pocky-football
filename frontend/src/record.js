export function formatRecord({ wins, losses, ties }) {
  return ties ? `${wins}-${losses}-${ties}` : `${wins}-${losses}`;
}
