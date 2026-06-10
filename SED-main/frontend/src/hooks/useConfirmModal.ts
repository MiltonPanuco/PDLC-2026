import { useState } from 'react';

type Entidad = {
    id: number;
    activo?: boolean;
    activa?: boolean;
};

type ModalType = 'activar' | 'desactivar' | 'eliminar';

export const useConfirmModal = (
    onConfirmed: (type: ModalType, id: number) => void,
    alarmasActivas: boolean = true
) => {
    const [state, setState] = useState<{ open: boolean; type: ModalType; entidad: Entidad | null }>({
        open: false,
        type: 'desactivar',
        entidad: null,
    });

    const openToggle = (entidad: Entidad) => {
        const estaActivo = entidad.activo ?? entidad.activa ?? false;
        const type = estaActivo ? 'desactivar' : 'activar';

        // Si alarmas están desactivadas, ejecuta directo sin modal
        if (!alarmasActivas) {
            onConfirmed(type, entidad.id);
            return;
        }

        setState({ open: true, type, entidad });
    };

    const openEliminar = (entidad: Entidad) => {
        // Eliminar siempre muestra el modal
        setState({ open: true, type: 'eliminar', entidad });
    };

    const close = () => setState(prev => ({ ...prev, open: false }));

    const confirm = () => {
        if (!state.entidad) return;
        onConfirmed(state.type, state.entidad.id);
        close();
    };

    return { ...state, openToggle, openEliminar, close, confirm };
};