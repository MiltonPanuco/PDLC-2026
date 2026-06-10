import { useState } from 'react';

type Docente = {
    id: number;
    nombre: string;
    paterno: string;
    materno: string;
    imagen?: string;
} | null;

export const useDocenteFormModal = () => {
    const [state, setState] = useState<{ open: boolean; docente: Docente }>({
        open: false,
        docente: null,
    });

    const openNuevo = () => setState({ open: true, docente: null });
    const openEditar = (docente: NonNullable<Docente>) => setState({ open: true, docente });
    const close = () => setState({ open: false, docente: null });

    return { ...state, openNuevo, openEditar, close };
};