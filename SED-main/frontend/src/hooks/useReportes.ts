import { useState, useEffect } from 'react';
import * as evaluationService from '../services/evaluation.service';
import type { ReporteDocente, ReporteDetalle } from '../services/evaluation.service';
import { PERIODOS, GRUPOS } from '../services/mockData';

export const ACTIVE_PERIODO_ID = PERIODOS.find(p => p.activo)?.id ?? 7;

export const GRUPOS_PERIODO = [
    { id: undefined as number | undefined, nombre: 'Todos los grupos' },
    ...GRUPOS
        .filter(g => g.id_periodo === ACTIVE_PERIODO_ID)
        .sort((a, b) => a.id - b.id)
        .map(g => ({ id: g.id as number | undefined, nombre: g.nombre })),
];

export function useReportes() {
    const [periodoId] = useState<number>(ACTIVE_PERIODO_ID);
    const [grupoId, setGrupoId] = useState<number | undefined>(undefined);
    const [search, setSearch] = useState('');
    const [reportes, setReportes] = useState<ReporteDocente[]>([]);

    // Reporte abierto en el panel derecho
    const [selectedId, setSelectedId] = useState<number | null>(null);
    const [detalle, setDetalle] = useState<ReporteDetalle | null>(null);
    const [loadingDetalle, setLoadingDetalle] = useState(false);

    // IDs ya enviados
    const [sentIds, setSentIds] = useState<Set<number>>(new Set());

    // Selección múltiple para envío personalizado
    const [checkedIds, setCheckedIds] = useState<Set<number>>(new Set());

    // Modales
    const [emailModalId, setEmailModalId] = useState<number | null>(null);
    const [bulkModalOpen, setBulkModalOpen] = useState(false);
    const [selectionModalOpen, setSelectionModalOpen] = useState(false);

    // Responsivo: mostrar panel derecho en móvil
    const [showDetailPanel, setShowDetailPanel] = useState(false);

    useEffect(() => {
        evaluationService.getReportesDocentes(periodoId, grupoId)
            .then(res => { if ('data' in res) setReportes(res.data); })
            .catch(() => setReportes([]));
    }, [periodoId, grupoId]);

    useEffect(() => {
        if (selectedId === null) { setDetalle(null); return; }
        setLoadingDetalle(true);
        setDetalle(null);
        evaluationService.getReporteDetalle(selectedId)
            .then(res => {
                if ('data' in res) setDetalle(res.data);
                setLoadingDetalle(false);
            })
            .catch(() => setLoadingDetalle(false));
    }, [selectedId]);

    const filtered = reportes.filter(r =>
        r.docenteNombre.toLowerCase().includes(search.toLowerCase()) ||
        r.ua.toLowerCase().includes(search.toLowerCase())
    );

    const selected = reportes.find(r => r.id === selectedId) ?? null;
    const pending = filtered.filter(r => !sentIds.has(r.id));
    const checkedReportes = filtered.filter(r => checkedIds.has(r.id));

    const handleSent = (id: number) =>
        setSentIds(prev => new Set([...prev, id]));

    const handleBulkSent = (ids: number[]) => {
        setSentIds(prev => new Set([...prev, ...ids]));
        setCheckedIds(new Set());
    };

    const toggleCheck = (id: number) => {
        setCheckedIds(prev => {
            const next = new Set(prev);
            next.has(id) ? next.delete(id) : next.add(id);
            return next;
        });
    };

    const toggleAllChecked = () => {
        if (checkedIds.size === filtered.length) {
            setCheckedIds(new Set());
        } else {
            setCheckedIds(new Set(filtered.map(r => r.id)));
        }
    };

    const emailDocente = emailModalId !== null
        ? (reportes.find(x => x.id === emailModalId) ?? null)
        : null;

    const handleSelectRow = (id: number) => {
        setSelectedId(id);
        setShowDetailPanel(true);
    };

    return {
        periodoId,
        grupoId, setGrupoId,
        search, setSearch,
        filtered,
        selected,
        detalle,
        loadingDetalle,
        sentIds,
        pending,
        checkedIds, checkedReportes,
        toggleCheck, toggleAllChecked,
        emailModalId, setEmailModalId,
        emailDocente,
        bulkModalOpen, setBulkModalOpen,
        selectionModalOpen, setSelectionModalOpen,
        handleSent,
        handleBulkSent,
        selectedId,
        handleSelectRow,
        showDetailPanel, setShowDetailPanel,
    };
}