import { useState } from 'react';

export function useGenericFormModal<T extends { id: number }>() {
  const [open, setOpen] = useState(false);
  const [item, setItem] = useState<T | null>(null);

  const openNuevo = () => {
    setItem(null);
    setOpen(true);
  };

  const openEditar = (entity: T) => {
    setItem(entity);
    setOpen(true);
  };

  const close = () => {
    setOpen(false);
    setItem(null);
  };

  return { open, item, openNuevo, openEditar, close };
}
