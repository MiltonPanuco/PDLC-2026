import { useState, useEffect, useRef } from 'react';
import { arrayMove } from '@dnd-kit/sortable';
import type { DragEndEvent } from '@dnd-kit/core';
import { useConfirmModal } from './useConfirmModal';
import type { Audience, ConditionalRule, Instrumento } from '../types';
import * as svc from '../services/instruments.service';

export type LocalOpcion   = { id: number; texto: string; valor: number; orden: number };
export type EscalaOpcion  = { id: number; texto: string; valor: number };
export type LocalPregunta = {
    id: number;
    texto: string;
    tipo: 'cerrada' | 'abierta' | 'multiple' | 'escala';
    activa: boolean;
    opciones: LocalOpcion[];
    opcional?: boolean;
    permite_comentario?: boolean;
    reglas_condicionales?: ConditionalRule[];
};
export type LocalCategoria = { id: number; nombre: string; preguntas: LocalPregunta[] };

export const useInstrumento = () => {
    // ── List ──────────────────────────────────────────────────────────────────
    const [instrumentosList, setInstrumentosList] = useState<Instrumento[]>([]);
    const [selectedInstrumentoId, setSelectedInstrumentoId] = useState<number>(1);
    const [duplicating, setDuplicating]   = useState(false);
    const [createModalOpen, setCreateModalOpen] = useState(false);
    const [archivedList, setArchivedList] = useState<Instrumento[]>([]);
    const [showArchived, setShowArchived] = useState(false);
    const [archiveConfirmId, setArchiveConfirmId]   = useState<number | null>(null);
    const [deleteInstrumentoId, setDeleteInstrumentoId] = useState<number | null>(null);

    // ── Detail ────────────────────────────────────────────────────────────────
    const [loading, setLoading]       = useState(true);
    const [instrumento, setInstrumento] = useState<{ nombre: string; estado: 'borrador' | 'publicado' } | null>(null);
    const [categorias, setCategorias] = useState<LocalCategoria[]>([]);
    const [selectedCatId, setSelectedCatId] = useState<number>(0);
    const [filtro, setFiltro]         = useState<'activas' | 'todas'>('activas');
    const [editingCatId, setEditingCatId]     = useState<number | null>(null);
    const [editingCatNombre, setEditingCatNombre] = useState('');
    const [deleteCatId, setDeleteCatId]       = useState<number | null>(null);
    const [escalaOpciones, setEscalaOpciones] = useState<EscalaOpcion[]>([]);
    const [preguntaModal, setPreguntaModal]   = useState<{ open: boolean; pregunta: LocalPregunta | null }>({ open: false, pregunta: null });
    const [publishConfirmOpen, setPublishConfirmOpen] = useState(false);
    const [catPanelOpen, setCatPanelOpen]     = useState(false);

    // ── Escala sync on modal close ────────────────────────────────────────────
    const prevEscalaRef    = useRef<EscalaOpcion[]>([]);
    const escalaOpcionesRef = useRef<EscalaOpcion[]>([]);
    useEffect(() => { escalaOpcionesRef.current = escalaOpciones; }, [escalaOpciones]);

    useEffect(() => {
        if (preguntaModal.open) {
            prevEscalaRef.current = [...escalaOpcionesRef.current];
            return;
        }
        const prev = prevEscalaRef.current;
        const curr = escalaOpcionesRef.current;
        const deleted = prev.filter(p => !curr.some(c => c.id === p.id));
        const updated = curr.filter(c => { const p = prev.find(p => p.id === c.id); return p && (p.texto !== c.texto || p.valor !== c.valor); });
        const added   = curr.filter(c => !prev.some(p => p.id === c.id));
        (async () => {
            await Promise.all([
                ...deleted.map(o => svc.deleteOpcionRespuesta(o.id)),
                ...updated.map(o => svc.updateOpcionRespuesta(o.id, { texto: o.texto, valor: o.valor })),
            ]);
            const results = await Promise.all(added.map(o => svc.createOpcionRespuesta({ id_instrumento: selectedInstrumentoId, texto: o.texto, valor: o.valor, activa: true })));
            results.forEach((res, i) => {
                if ('data' in res) {
                    const tempId = added[i].id;
                    setEscalaOpciones(prev => prev.map(x => x.id === tempId ? { ...x, id: res.data.id } : x));
                }
            });
        })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [preguntaModal.open]);

    // ── Loaders ───────────────────────────────────────────────────────────────
    const loadInstrumentosList = async () => {
        const res = await svc.getInstrumentos();
        if ('data' in res) setInstrumentosList(res.data);
    };

    const loadInstrumento = async (id = selectedInstrumentoId) => {
        if (id < 1) { setLoading(false); return; }
        setLoading(true);
        const res = await svc.getInstrumento(id);
        if ('data' in res) {
            const { instrumento: inst, categorias: cats } = res.data;
            setInstrumento({ nombre: inst.nombre, estado: inst.estado });
            const mapped: LocalCategoria[] = cats.map(cat => ({
                id: cat.id, nombre: cat.nombre,
                preguntas: cat.preguntas.map(p => ({
                    id: p.id,
                    texto: p.texto,
                    tipo: p.tipo,
                    activa: p.activa,
                    opciones: p.opciones.map(o => ({ id: o.id, texto: o.texto, valor: o.valor, orden: o.orden })),
                    opcional: p.opcional,
                    permite_comentario: p.permite_comentario,
                    reglas_condicionales: p.reglas_condicionales,
                })),
            }));
            setCategorias(mapped);
            setEscalaOpciones(res.data.opciones.map(o => ({ id: o.id, texto: o.texto, valor: o.valor })));
            setSelectedCatId(prev => mapped.some(c => c.id === prev) ? prev : (mapped[0]?.id ?? 0));
        }
        setLoading(false);
    };

    const loadArchived = async () => {
        const res = await svc.getInstrumentosArchivados();
        if ('data' in res) setArchivedList(res.data);
    };

    useEffect(() => { loadInstrumentosList(); }, []);
    useEffect(() => { setSelectedCatId(0); loadInstrumento(selectedInstrumentoId); }, [selectedInstrumentoId]); // eslint-disable-line react-hooks/exhaustive-deps

    // ── Derived ───────────────────────────────────────────────────────────────
    const isPublished      = instrumento?.estado === 'publicado';
    const selectedCategoria = categorias.find(c => c.id === selectedCatId) ?? categorias[0];
    const preguntasFiltradas = selectedCategoria
        ? filtro === 'activas' ? selectedCategoria.preguntas.filter(p => p.activa) : selectedCategoria.preguntas
        : [];

    // ── Confirm modal ─────────────────────────────────────────────────────────
    const confirmModal = useConfirmModal(async (type, id) => {
        if (type === 'eliminar') {
            await svc.deletePregunta(id as number);
            setCategorias(prev => prev.map(cat => ({ ...cat, preguntas: cat.preguntas.filter(p => p.id !== id) })));
        } else {
            const res = await svc.togglePreguntaActiva(id as number);
            if ('data' in res) {
                const u = res.data;
                setCategorias(prev => prev.map(cat => ({ ...cat, preguntas: cat.preguntas.map(p => p.id === u.id ? { ...p, activa: u.activa } : p) })));
            }
        }
    });

    // ── Instrumento handlers ──────────────────────────────────────────────────
    const handleDuplicate = async (id: number) => {
        setDuplicating(true);
        const res = await svc.duplicateInstrumento(id);
        if ('data' in res) { await loadInstrumentosList(); setSelectedInstrumentoId(res.data.id); }
        setDuplicating(false);
    };

    const handleCreateInstrumento = async (data: { nombre: string; nivel: 'lic' | 'maestria' | 'doctorado'; audience: Audience }) => {
        const res = await svc.createInstrumento({ ...data, id_programa_academico: 2 });
        if ('data' in res) {
            await svc.createCategoria({ id_instrumento: res.data.id, nombre: 'General', orden: 1, activa: true });
            await loadInstrumentosList();
            setSelectedInstrumentoId(res.data.id);
        }
    };

    const handleDeleteInstrumento = async (id: number) => {
        await svc.deleteInstrumento(id);
        const next = instrumentosList.filter(i => i.id !== id);
        setInstrumentosList(next);
        if (selectedInstrumentoId === id) setSelectedInstrumentoId(next[0]?.id ?? 0);
        setDeleteInstrumentoId(null);
    };

    const handleArchiveInstrumento = async (id: number) => {
        await svc.archiveInstrumento(id);
        const res = await svc.getInstrumentos();
        if ('data' in res) {
            setInstrumentosList(res.data);
            if (selectedInstrumentoId === id) setSelectedInstrumentoId(res.data[0]?.id ?? 0);
        }
        setArchiveConfirmId(null);
    };

    const handleRestoreInstrumento = async (id: number) => {
        await svc.restoreInstrumento(id);
        await loadInstrumentosList();
        const res = await svc.getInstrumentosArchivados();
        if ('data' in res) setArchivedList(res.data);
    };

    const handlePublish = async () => {
        const res = await svc.publishInstrumento(selectedInstrumentoId);
        setPublishConfirmOpen(false);
        if ('data' in res) setInstrumento({ nombre: res.data.nombre, estado: res.data.estado });
        await loadInstrumentosList();
    };

    // ── Categoría handlers ────────────────────────────────────────────────────
    const handleAddCategoria = async () => {
        if (isPublished) return;
        const res = await svc.createCategoria({ id_instrumento: selectedInstrumentoId, nombre: 'Nueva categoría', orden: categorias.length + 1, activa: true });
        if ('data' in res) {
            setCategorias(prev => [...prev, { id: res.data.id, nombre: res.data.nombre, preguntas: [] }]);
            setSelectedCatId(res.data.id);
        }
    };

    const handleSaveCategoriaNombre = async (id: number) => {
        const trimmed = editingCatNombre.trim();
        if (trimmed && trimmed !== categorias.find(c => c.id === id)?.nombre) {
            const res = await svc.updateCategoria(id, { nombre: trimmed });
            if ('data' in res) setCategorias(prev => prev.map(c => c.id === id ? { ...c, nombre: res.data.nombre } : c));
        }
        setEditingCatId(null);
    };

    const handleDeleteCategoria = async (id: number) => {
        await svc.deleteCategoria(id);
        const remaining = categorias.filter(c => c.id !== id);
        setCategorias(remaining);
        if (selectedCatId === id) setSelectedCatId(remaining[0]?.id ?? 0);
        setDeleteCatId(null);
    };

    const handleDragEndCategorias = async (event: DragEndEvent) => {
        if (isPublished) return;
        const { active, over } = event;
        if (!over || active.id === over.id) return;
        const next = arrayMove(categorias, categorias.findIndex(c => c.id === active.id), categorias.findIndex(c => c.id === over.id));
        setCategorias(next);
        await svc.reorderCategorias(selectedInstrumentoId, next.map(c => c.id));
    };

    // ── Pregunta handlers ─────────────────────────────────────────────────────
    const handleSavePregunta = async (data: {
        texto: string;
        tipo: LocalPregunta['tipo'];
        activa: boolean;
        categoriaId: number;
        opciones: Array<{ texto: string; valor: number; orden: number }>;
        opcional?: boolean;
        permite_comentario?: boolean;
        reglas_condicionales?: ConditionalRule[];
    }) => {
        let preguntaId: number;
        const extras = {
            opcional: data.opcional ?? false,
            permite_comentario: data.permite_comentario ?? false,
            reglas_condicionales: data.reglas_condicionales ?? [],
        };
        if (preguntaModal.pregunta) {
            const res = await svc.updatePregunta(preguntaModal.pregunta.id, {
                texto: data.texto,
                activa: data.activa,
                tipo: data.tipo,
                ...extras,
            });
            if (!('data' in res)) return;
            preguntaId = res.data.id;
            setCategorias(prev => prev.map(cat => ({
                ...cat,
                preguntas: cat.preguntas.map(p => p.id === preguntaId
                    ? { ...p, texto: res.data.texto, tipo: data.tipo, activa: res.data.activa, ...extras }
                    : p),
            })));
        } else {
            const res = await svc.createPregunta({
                id_categoria: data.categoriaId,
                id_instrumento: selectedInstrumentoId,
                texto: data.texto,
                orden: 0,
                activa: data.activa,
                tipo: data.tipo,
                ...extras,
            });
            if (!('data' in res)) return;
            preguntaId = res.data.id;
            setCategorias(prev => prev.map(cat => cat.id === data.categoriaId
                ? { ...cat, preguntas: [...cat.preguntas, { id: preguntaId, texto: res.data.texto, tipo: data.tipo, activa: res.data.activa, opciones: [], ...extras }] }
                : cat));
        }
        if ((data.tipo === 'cerrada' || data.tipo === 'multiple') && data.opciones?.length) {
            const opRes = await svc.replaceOpcionesPregunta(preguntaId, data.opciones);
            if ('data' in opRes) setCategorias(prev => prev.map(cat => ({ ...cat, preguntas: cat.preguntas.map(p => p.id === preguntaId ? { ...p, opciones: opRes.data.map(o => ({ id: o.id, texto: o.texto, valor: o.valor, orden: o.orden })) } : p) })));
        } else {
            await svc.replaceOpcionesPregunta(preguntaId, []);
            setCategorias(prev => prev.map(cat => ({ ...cat, preguntas: cat.preguntas.map(p => p.id === preguntaId ? { ...p, opciones: [] } : p) })));
        }
        setPreguntaModal({ open: false, pregunta: null });
    };

    const handleDragEndPreguntas = async (event: DragEndEvent) => {
        if (isPublished) return;
        const { active, over } = event;
        if (!over || active.id === over.id) return;
        const cat = categorias.find(c => c.id === selectedCatId);
        if (!cat) return;
        const next = arrayMove(cat.preguntas, cat.preguntas.findIndex(p => p.id === active.id), cat.preguntas.findIndex(p => p.id === over.id));
        setCategorias(prev => prev.map(c => c.id === selectedCatId ? { ...c, preguntas: next } : c));
        await svc.reorderPreguntas(selectedCatId, next.map(p => p.id));
    };

    return {
        // list
        instrumentosList, selectedInstrumentoId, setSelectedInstrumentoId,
        duplicating, createModalOpen, setCreateModalOpen,
        archivedList, showArchived, setShowArchived, loadArchived,
        archiveConfirmId, setArchiveConfirmId,
        deleteInstrumentoId, setDeleteInstrumentoId,
        handleDuplicate, handleCreateInstrumento, handleDeleteInstrumento,
        handleArchiveInstrumento, handleRestoreInstrumento,
        // detail
        loading, instrumento, isPublished,
        categorias, selectedCatId, setSelectedCatId,
        selectedCategoria, preguntasFiltradas,
        filtro, setFiltro,
        editingCatId, setEditingCatId, editingCatNombre, setEditingCatNombre,
        deleteCatId, setDeleteCatId,
        escalaOpciones, setEscalaOpciones,
        preguntaModal, setPreguntaModal,
        publishConfirmOpen, setPublishConfirmOpen,
        catPanelOpen, setCatPanelOpen,
        confirmModal,
        handleAddCategoria, handleSaveCategoriaNombre, handleDeleteCategoria,
        handleDragEndCategorias, handleDragEndPreguntas,
        handleSavePregunta, handlePublish,
    };
};
